#!/usr/bin/env python3
"""PJ1 arena driver -- two germ/soma organisms colliding in one environment (build + sim + live).

Runs the three arms of the collision (``none`` / ``soma_soma`` / ``germ_routed``) over a sweep of
animation frames, banking -- per arm, per frame -- the body occupancy (Z-basis on the unary body
tracks), the JOINT genealogy witness ``<X^{2W}>`` + the separable joint null + the per-lineage
witnesses + the A|B bipartite-cut witness (X-basis on both germ lines, co-measured in ONE circuit),
and the sim-only contact entropy S(rho_bodyA) (statevector). The banked JSON is exactly the shape the
wave-bars renderer (``analysis/pj1_render.py``) consumes (AC-PJ1.7).

Design (OQ-5): this is a NEW file. It imports the shared arena MODEL from ``pj_qalife`` and REUSES
PJ0's driver infra BY IMPORT (``gated_chain``, ``qrng_thetas``, ``connect``/``run_sampler``/
``timestamp``, ``OUTPUT_DIR``, the QRNG client) -- so ``pj_run_qalife.py`` stays byte-stable and PJ0
is easily recreatable. Two deliberate departures from PJ0's driver, both forced + documented:
  * SELECTIVE DD is re-implemented here (``schedule_arena_selective_dd``) because PJ0's
    ``schedule_with_selective_dd`` derives its DD target internally from ``pj.witness_qubits(width,
    has_bath)`` (PJ0 layout, ONE organism) and cannot target the arena's two germ lines under the
    different arena layout without editing PJ0 (forbidden, Q5). The pass is otherwise identical.
  * SIM uses a statevector Aer backend (not PJ0's density_matrix ``SIM``): the arena is fully unitary
    (no bath, no damping -- CD-8), so statevector is exact and does not double the qubit budget.

Verification (CD-7): ``--selftest`` lives in ``pj_qalife.py``; here it's ``--sim`` + ``--dump-circuit``
+ ``--scan-coupling`` + one live run. No test framework.

Usage:
    cd artificial-life/code
    python pj1_run_arena.py --width 4 --track 5 --frames 24              # sim, all three arms
    python pj1_run_arena.py --scan-coupling --width 4 --track 5          # locate the phi regime
    python pj1_run_arena.py --dump-circuit --draw-only --width 4 --track 5
    python pj1_run_arena.py --backend <heron> --width 12 --track 6 --frames 6 --shots 8192
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import pj_qalife as pj
import qalife as q4

# Reuse PJ0's driver infra by import -- NO edit to pj_run_qalife.py (Q5). gated_chain enforces the
# chain-quality gate (CD-5) using PJ0's thresholds internally.
from pj_run_qalife import (          # noqa: E402
    OUTPUT_DIR, connect, gated_chain, qrng_thetas, run_sampler, timestamp,
)
from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- study parameters -------------------------------------------------------
ORGANISMS = 2                        # PJ1: two organisms (L=2 only, §3)
TRACK = 6                            # unary body-track sites/organism (OQ-1)
TRAITS = 1                           # idle trait qubit (rung-5 hook, §3)
FRAMES_SIM = 36                      # smooth demo resolution (sim)
FRAMES_HW = 6                        # few measured frames on HW, near the collision (OQ-2/Q3)
STEPS_HW = 0                         # arena germ ignores steps (clean GHZ); kept for API parity
COUPLING = pj.DEFAULT_COUPLING       # (theta_walk, phi_collision); driver scans phi (I1a)
ARMS = ("none", "soma_soma", "germ_routed")
K = 2.0                              # significance multiplier (CD-5)
MUT_SCALE = 0.0                      # faithful clean GHZ by default (CD-6) -> isolate the collision
SELECTIVE_DD = True
QEAAS_URL = os.environ.get("QEAAS_API_URL", "https://api.qeaas.eu")

# Arena is fully unitary -> statevector is exact and lighter than density_matrix (see module docstring).
ARENA_SIM = AerSimulator(method="statevector")
_SV_MAX_QUBITS = 26                  # statevector feasibility cap (contact entropy + sim counts)


# ---------------------------------------------------------------------------
# Measured arena build -- witness = both germ lines in X, bodies in Z (one circuit).
# ---------------------------------------------------------------------------
def build_measured_arena(width: int, steps: int, thetas: list[float], *, interaction: str,
                         frame: int, organisms: int = ORGANISMS, track: int = TRACK,
                         traits: int = TRAITS, coupling: tuple[float, float] = COUPLING,
                         coll_site: int | None = None,
                         annotate: bool = False) -> QuantumCircuit:
    """Build the arena at `frame`, rotate BOTH germ lines into X (joint witness), leave bodies in Z
    (occupancy), add a classical register, measure all. One circuit yields witness + occupancy."""
    qc = pj.build_arena(width, steps, thetas, organisms=organisms, track=track, traits=traits,
                        interaction=interaction, frame=frame, coupling=coupling,
                        coll_site=coll_site, annotate=annotate)
    pj._bar(qc, annotate, "X-basis (witness)")
    qc = pj.arena_to_witness_basis(qc, width, organisms=organisms, track=track, traits=traits)
    n_data = qc.num_qubits
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    qc.measure(range(n_data), creg)
    return qc


def _marginal_p1(counts: dict[str, int], q: int, total: int) -> float:
    """P(qubit q == 1) from measured counts (little-endian bitstrings, as in PJ0)."""
    return sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total


def reduce_frame(counts: dict[str, int], width: int, *, organisms: int, track: int,
                 traits: int) -> dict[str, Any]:
    """All per-frame observables from ONE counts dict:
      * occ                  : [ [P(site) org0], [P(site) org1] ]  (Z-basis occupancy)
      * witness_joint        : <X^{2W}> over both germ lines
      * separable_joint_null : product of single-qubit <X> over all germ qubits (must sit ~0)
      * witness_per_lineage  : [ <X^W>_A, <X^W>_B ]
      * witness_cut_AB       : <X^{2W}> - <X^W>_A * <X^W>_B  (the A|B bipartite-cut certificate)
      * entanglement_signal  : witness_joint - separable_joint_null
    """
    total = sum(counts.values()) or 1
    occ = [[_marginal_p1(counts, pj.body_q(o, j, width, track, traits), total)
            for j in range(track)] for o in range(organisms)]

    all_germ = pj.arena_witness_qubits(width, organisms, track, traits)
    joint, sep = q4.xbasis_witness_from_counts(counts, all_germ)

    per_lineage: list[float] = []
    for o in range(organisms):
        qs = [pj.germ_q(o, k, width, track, traits) for k in range(width)]
        per_lineage.append(q4.xbasis_witness_from_counts(counts, qs)[0])

    a_cut, b_cut = pj.bipartite_cut_qubits(width, organisms, track, traits)
    wa = q4.xbasis_witness_from_counts(counts, a_cut)[0]
    wb = q4.xbasis_witness_from_counts(counts, b_cut)[0]
    witness_cut_ab = joint - wa * wb                 # A|B correlation beyond the lineage product

    return {
        "occ": occ,
        "witness_joint": joint,
        "separable_joint_null": sep,
        "witness_per_lineage": per_lineage,
        "witness_cut_AB": witness_cut_ab,
        "entanglement_signal": joint - sep,
    }


# ---------------------------------------------------------------------------
# Sim-only contact meter -- S(rho_bodyA) from the statevector (OQ-4, labelled sim-only).
# ---------------------------------------------------------------------------
def contact_entropy_sim(width: int, thetas: list[float], *, interaction: str, frame: int,
                        organisms: int = ORGANISMS, track: int = TRACK, traits: int = TRAITS,
                        coupling: tuple[float, float] = COUPLING,
                        coll_site: int | None = None) -> float | None:
    """Von-Neumann entropy S(rho_bodyA) of organism-0's body register from the exact statevector of
    the unmeasured arena. The entanglement "contact" reading (rises on overlap when the coupling is
    on). Returns None when the register is too large for a statevector (sim-only, no HW estimator)."""
    n_data = organisms * pj.arena_segment_len(width, track, traits)
    if n_data > _SV_MAX_QUBITS:
        return None
    from qiskit.quantum_info import Statevector, entropy, partial_trace
    qc = pj.build_arena(width, 0, thetas, organisms=organisms, track=track, traits=traits,
                        interaction=interaction, frame=frame, coupling=coupling, coll_site=coll_site)
    sv = Statevector.from_instruction(qc)
    keep = set(pj.body_site_qubits(0, width, track, traits))
    trace_out = [q for q in range(n_data) if q not in keep]
    rho = partial_trace(sv, trace_out)
    return float(entropy(rho, base=2))


# ---------------------------------------------------------------------------
# Selective DD on BOTH germ lines (AC-PJ1.8) -- arena analogue of PJ0's pass.
# Re-implemented here because PJ0's schedule_with_selective_dd targets ONE germ line under the PJ0
# layout and cannot be pointed at the arena's two germ lines without editing PJ0 (Q5).
# ---------------------------------------------------------------------------
def schedule_arena_selective_dd(qc: QuantumCircuit, backend: Any, width: int, *,
                                organisms: int = ORGANISMS, track: int = TRACK,
                                traits: int = TRAITS) -> QuantumCircuit:
    """Transpile + schedule with DD padded on the genotype physical qubits of BOTH organisms only
    (bodies DD-free = the Weismann barrier, cross-organism). Returns the submit-ready circuit."""
    from qiskit.circuit.library import XGate
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    routed = pm.run(qc)

    germ_virtual = pj.arena_witness_qubits(width, organisms, track, traits)  # BOTH germ lines
    germ_physical: list[int] = []
    if routed.layout is not None:
        v2p = routed.layout.final_index_layout()
        germ_physical = [v2p[v] for v in germ_virtual if v < len(v2p)]

    durations = getattr(backend.target, "durations", lambda: None)()
    passes = [ALAPScheduleAnalysis(durations=durations),
              PadDynamicalDecoupling(durations=durations, dd_sequence=[XGate(), XGate()],
                                     qubits=germ_physical or None)]
    return PassManager(passes).run(routed)


# ---------------------------------------------------------------------------
# Certified entropy (fail-closed on hardware) -- reuse PJ0's env probe pattern.
# ---------------------------------------------------------------------------
def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _qrng_coll_site(client: QRNGClient | None, track: int) -> int | None:
    """QRNG-chosen collision site (a PROVENANCE claim, not a computational one -- M5/CD-6). None in
    sim without a client (couple all aligned sites)."""
    if client is None:
        return None
    resp = client.fetch(size=32, fmt="hex")
    return int.from_bytes(bytes.fromhex(resp.data)[:4], "big") % track


# ---------------------------------------------------------------------------
# One arm: sweep frames, bank the per-frame observables.
# ---------------------------------------------------------------------------
def run_arm(interaction: str, *, width: int, track: int, traits: int, frames: int,
            thetas: list[float], coupling: tuple[float, float], coll_site: int | None,
            shots: int, sim: bool, backend: Any) -> list[dict[str, Any]]:
    """Run every frame 0..frames-1 for one arm; return the frames[] list (renderer contract)."""
    out: list[dict[str, Any]] = []
    for t in range(frames):
        qc = build_measured_arena(width, STEPS_HW, thetas, interaction=interaction, frame=t,
                                  organisms=ORGANISMS, track=track, traits=traits,
                                  coupling=coupling, coll_site=coll_site)
        if sim:
            counts = ARENA_SIM.run(transpile(qc, ARENA_SIM), shots=shots).result().get_counts()
        else:
            if SELECTIVE_DD:
                submit_qc = schedule_arena_selective_dd(qc, backend, width, organisms=ORGANISMS,
                                                        track=track, traits=traits)
            else:
                submit_qc = generate_preset_pass_manager(optimization_level=3,
                                                         backend=backend).run(qc)
            raw_meas, _jobs, _qs = run_sampler(backend, submit_qc, shots)
            counts = {}
            for s in raw_meas:
                counts[s] = counts.get(s, 0) + 1

        frame = reduce_frame(counts, width, organisms=ORGANISMS, track=track, traits=traits)
        frame["t"] = t
        frame["contact_entropy_sim"] = contact_entropy_sim(
            width, thetas, interaction=interaction, frame=t, organisms=ORGANISMS,
            track=track, traits=traits, coupling=coupling, coll_site=coll_site)
        out.append(frame)
    return out


# ---------------------------------------------------------------------------
# Coupling-strength sim-scan (I1a) -- locate the macroscopic-entanglement phi regime.
# ---------------------------------------------------------------------------
def scan_coupling(width: int, track: int, traits: int, thetas: list[float], *,
                  frame: int, shots: int, points: int = 9) -> None:
    """Sweep phi over [0, pi] in the soma_soma arm (sim), print joint witness + cut witness vs phi."""
    theta = COUPLING[0]
    print(f"=== PJ1 coupling sim-scan (soma_soma, W={width}, track={track}, frame={frame}) ===")
    print("   phi        witness_joint   witness_cut_AB   sep_null   contact_S")
    for phi in np.linspace(0.0, math.pi, points):
        qc = build_measured_arena(width, STEPS_HW, thetas, interaction="soma_soma", frame=frame,
                                  track=track, traits=traits, coupling=(theta, float(phi)))
        counts = ARENA_SIM.run(transpile(qc, ARENA_SIM), shots=shots).result().get_counts()
        r = reduce_frame(counts, width, organisms=ORGANISMS, track=track, traits=traits)
        cs = contact_entropy_sim(width, thetas, interaction="soma_soma", frame=frame, track=track,
                                 traits=traits, coupling=(theta, float(phi)))
        cs_s = f"{cs:.3f}" if cs is not None else "  n/a"
        print(f"  {phi:5.3f}      {r['witness_joint']:+.4f}         {r['witness_cut_AB']:+.4f}"
              f"       {r['separable_joint_null']:+.3f}     {cs_s}")


# ---------------------------------------------------------------------------
# Dump the arena circuits (per arm) -- static structure for the record.
# ---------------------------------------------------------------------------
def dump_circuits(width: int, track: int, traits: int, thetas: list[float], *, frame: int) -> None:
    for arm in ARMS:
        pj.print_arena_report(width, STEPS_HW, thetas, organisms=ORGANISMS, track=track,
                              traits=traits, interaction=arm, frame=frame)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ1 arena driver -- two germ/soma organisms colliding (sim or hardware); "
                    "banks the joint witness + A|B cut + occupancy per frame per arm.")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the statevector Aer sim")
    ap.add_argument("--width", type=int, default=12, help="germ width W/organism (12 anchor)")
    ap.add_argument("--track", type=int, default=TRACK, help="unary body-track sites/organism")
    ap.add_argument("--traits", type=int, default=TRAITS, help="trait qubits/organism (idle hook)")
    ap.add_argument("--interaction", choices=list(ARMS), default=None,
                    help="run one arm; default = run all three arms")
    ap.add_argument("--frames", type=int, default=None,
                    help="frames to sweep (default: FRAMES_SIM sim / FRAMES_HW hardware)")
    ap.add_argument("--steps", type=int, default=STEPS_HW, help="parity only (arena germ is clean)")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--scan-coupling", dest="scan_coupling", action="store_true",
                    help="sim-scan phi (I1a) to locate the macroscopic regime, then exit")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated arena circuits (all arms) then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT run")
    ap.add_argument("--name", type=str, default="pj1_arena")
    args = ap.parse_args()
    sim = args.backend is None
    frames = args.frames if args.frames is not None else (FRAMES_SIM if sim else FRAMES_HW)
    arms = (args.interaction,) if args.interaction else ARMS

    # --- certified entropy (fail-closed on hardware; sim may PRNG-fallback) ---
    client = None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    qrng_url = os.environ.get("QEAAS_API_URL") or QEAAS_URL
    if api_key:
        client = QRNGClient(qrng_url, api_key)
        try:
            h = client.health()
            print(f"Q-EaaS  : {qrng_url}  health: {h.status}")
            if h.status != "ok" and not sim:
                print("[PJ1 ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not sim:
                print(f"[PJ1 ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not sim:
        print("[PJ1 ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    thetas = (qrng_thetas(client, args.width, MUT_SCALE, 0) if client is not None
              else q4._sim_thetas(args.width, args.width, mut_scale=MUT_SCALE))

    # --- scan / dump modes -----------------------------------------------------
    if args.scan_coupling:
        scan_coupling(args.width, args.track, args.traits, thetas,
                      frame=max(1, frames // 2), shots=args.shots)
        raise SystemExit(0)
    if args.dump_circuit:
        dump_circuits(args.width, args.track, args.traits, thetas, frame=max(1, frames // 2))
        if args.draw_only:
            raise SystemExit(0)

    # --- backend + chain gate --------------------------------------------------
    backend = None
    backend_name = "statevector_sim"
    coll_site = None
    if not sim:
        backend = connect(args.backend)
        backend_name = backend.name
        nq = ORGANISMS * pj.arena_segment_len(args.width, args.track, args.traits)
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits); arena needs {nq}")
        gated_chain(backend, nq)                       # chain-quality gate (CD-5); aborts if bad
        coll_site = _qrng_coll_site(client, args.track)

    # --- run every arm ---------------------------------------------------------
    print(f"=== PJ1 arena: W={args.width} track={args.track} organisms={ORGANISMS} "
          f"frames={frames} arms={arms} on {backend_name} ===")
    arm_frames: dict[str, list[dict[str, Any]]] = {}
    by_width: dict[str, Any] = {}
    for arm in arms:
        fr = run_arm(arm, width=args.width, track=args.track, traits=args.traits, frames=frames,
                     thetas=thetas, coupling=COUPLING, coll_site=coll_site, shots=args.shots,
                     sim=sim, backend=backend)
        arm_frames[arm] = fr
        # summary: the peak-overlap frame (max product-occupancy) and its witness.
        def _overlap(f: dict[str, Any]) -> float:
            a, b = f["occ"]
            return sum(x * y for x, y in zip(a, b))
        peak = max(fr, key=_overlap) if fr else None
        if peak is not None:
            sig = peak["entanglement_signal"]
            sigma = math.sqrt(1.0 / args.shots)
            print(f"  {arm:12} peak-overlap frame t={peak['t']:2}  "
                  f"witness_joint={peak['witness_joint']:+.3f}  "
                  f"cut_AB={peak['witness_cut_AB']:+.3f}  "
                  f"sep_null={peak['separable_joint_null']:+.3f}  "
                  f"signal={sig:+.3f}  {'SURVIVES' if sig > K * sigma else 'at-null'}")
            by_width_key = arm
            by_width[by_width_key] = {
                "peak_frame": peak["t"], "witness_joint": peak["witness_joint"],
                "witness_cut_AB": peak["witness_cut_AB"],
                "separable_joint_null": peak["separable_joint_null"],
                "entanglement_signal": sig, "survives": bool(sig > K * sigma),
            }

    result: dict[str, Any] = {
        "meta": {
            "stage": "PJ1", "model": "germsoma_arena", "backend": backend_name,
            "width": args.width, "organisms": ORGANISMS, "track": args.track,
            "traits": args.traits, "coupling": list(COUPLING), "coll_site": coll_site,
            "frames": frames, "arms": list(arms), "steps": args.steps, "shots": args.shots,
            "sim": sim, "mut_scale": MUT_SCALE, "k": K, "selective_dd": SELECTIVE_DD,
            "L": args.track, "calibration": None, "t1_band": None,
        },
        "arms": arm_frames,
        "by_arm": by_width,
    }

    os.makedirs(os.path.join(OUTPUT_DIR, "pj1"), exist_ok=True)
    tag = timestamp() if not sim else "sim"
    out = os.path.join(OUTPUT_DIR, "pj1", f"{args.name}_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
