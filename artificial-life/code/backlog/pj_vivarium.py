#!/usr/bin/env python3
"""PJ2 solo-vivarium driver -- one enriched proto-viral organism living in a habitat (ONE run).

Runs the three arms (``barren`` / ``vivarium`` / ``germ_coupled``) as ONE measured circuit each
(time = circuit depth; measured once at the terminal step -- NO per-frame job sweep, the defining
lock, AC-PJ2.3). The certified numbers are the single measured endpoint: the genealogy witness
``<X^W>`` (germ loci in X) + the separable null, plus the diagonal life story (body occupancy, food
remaining, energy, population -- all Z-basis, classically surrogate-able, CD-4). The animation for
the demo is reconstructed from STATEVECTOR SNAPSHOTS of the identical circuit prefix at each step
(sim-only, labelled -- the same "simulation artifact" pattern as pj1_spectacle.py).

Design (OQ-5): a NEW file. Imports the shared MODEL from ``pj_qalife`` and REUSES PJ0's driver infra
BY IMPORT (``gated_chain``, ``qrng_thetas``, ``connect``/``run_sampler``/``timestamp``, ``OUTPUT_DIR``)
-- ``pj_run_qalife.py`` / ``pj1_run_arena.py`` stay byte-stable. Selective DD is re-implemented here
(``schedule_vivarium_selective_dd``) for the vivarium layout's germ line (same forced deviation PJ1
documented). Sim uses a statevector Aer backend (the vivarium is unitary except the diagonal
consume/select gates).

Verification (CD-7): ``--selftest`` lives in ``pj_qalife.py``; here it's ``--sim`` + ``--dump-circuit``.
The developer runs the live W12 hardware (OQ-4).

Usage:
    cd artificial-life/code
    python pj_vivarium.py --width 4 --track 5 --steps 6              # sim, all three arms (one run each)
    python pj_vivarium.py --dump-circuit --draw-only --width 4 --track 5
    python pj_vivarium.py --backend <heron> --width 12 --track 6 --steps 4 --shots 8192
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
from typing import Any

from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import pj_qalife as pj
import qalife as q4

from pj_run_qalife import (          # noqa: E402  -- reuse PJ0 infra, no edit (Q5)
    OUTPUT_DIR, connect, gated_chain, qrng_thetas, run_sampler, timestamp,
)
from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- study parameters -------------------------------------------------------
TRACK = 6                            # unary habitat/body sites (OQ-2)
TRAITS = pj.VIV_TRAITS               # classical genes: role/repl/life
FOOD_SITES = pj.VIV_FOOD_SITES       # feeding stations (always wired; seeded unless barren)
STEPS_SIM = 6                        # life-cycle steps in sim (the depth = time)
STEPS_HW = 4                         # few steps on HW (one run; save QC time, R2/OQ-4)
HOP = pj.VIV_HOP
STARVE = pj.VIV_STARVE
ARMS = ("barren", "vivarium", "germ_coupled")
K = 2.0                              # significance multiplier (CD-5)
MUT_SCALE = 0.0                      # faithful clean GHZ (CD-6) -> isolate the biology
SELECTIVE_DD = True
QEAAS_URL = os.environ.get("QEAAS_API_URL", "https://api.qeaas.eu")

VIV_SIM = AerSimulator(method="statevector")
_SV_MAX_QUBITS = 27                  # statevector feasibility cap (movie snapshots + sim counts)


# ---------------------------------------------------------------------------
# Measured build -- witness loci in X, everything else in Z (ONE circuit).
# ---------------------------------------------------------------------------
def build_measured_vivarium(width: int, steps: int, thetas: list[float], *, interaction: str,
                            track: int = TRACK, traits: int = TRAITS, hard_select: bool = False,
                            gate_repl: bool = False, annotate: bool = False) -> QuantumCircuit:
    """Build the vivarium life cycle, rotate the germ loci into X (witness), leave body/food/energy
    in Z (the diagonal story), add a classical register, measure all -- one circuit."""
    qc = pj.build_vivarium(width, steps, thetas, track=track, traits=traits,
                           interaction=interaction, hard_select=hard_select, gate_repl=gate_repl,
                           annotate=annotate)
    pj._bar(qc, annotate, "X-basis (witness)")
    qc = pj.viv_to_witness_basis(qc, width, track=track, traits=traits)
    n_data = qc.num_qubits
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    qc.measure(range(n_data), creg)
    return qc


def _marginal_p1(counts: dict[str, int], q: int, total: int) -> float:
    return sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total


def reduce_counts(counts: dict[str, int], width: int, *, track: int, traits: int) -> dict[str, Any]:
    """Measured endpoint observables from ONE counts dict: witness + the diagonal life story."""
    total = sum(counts.values()) or 1
    n_food = len(pj.viv_food_sites(track))
    joint, sep = q4.xbasis_witness_from_counts(counts, pj.viv_witness_qubits(width, track, traits))
    occ = [_marginal_p1(counts, pj.viv_body_q(j, width, track, traits), total) for j in range(track)]
    food = [_marginal_p1(counts, pj.viv_food_q(j, width, track, traits), total) for j in range(track)]
    energy = [_marginal_p1(counts, pj.viv_energy_q(i, width, track, traits), total)
              for i in range(n_food)]
    return {
        "witness_joint": joint,
        "separable_null": sep,
        "entanglement_signal": joint - sep,
        "occupancy": occ,
        "food_remaining": food,
        "energy": energy,
        "alive": sum(occ),
    }


# ---------------------------------------------------------------------------
# Sim-only movie: statevector snapshot of the SAME circuit prefix at each step.
# ---------------------------------------------------------------------------
def sim_snapshots(width: int, steps: int, thetas: list[float], *, interaction: str, track: int,
                  traits: int, hard_select: bool, gate_repl: bool) -> list[dict[str, Any]] | None:
    """Reconstruct the trajectory (the demo movie) from exact statevectors of the circuit at each
    step prefix t=0..steps. Returns per-step body occupancy / food / energy / witness_sim / alive.
    Sim-only (statevector); None if the register is too large."""
    n_food = len(pj.viv_food_sites(track))
    n_data = pj.viv_segment_len(width, track, traits, n_food, hard_select=hard_select)
    if n_data > _SV_MAX_QUBITS:
        return None
    from qiskit.quantum_info import SparsePauliOp

    w_op = SparsePauliOp.from_sparse_list(
        [("X" * width, pj.viv_witness_qubits(width, track, traits), 1.0)], num_qubits=n_data)

    frames: list[dict[str, Any]] = []
    for t in range(steps + 1):
        qc = pj.build_vivarium(width, t, thetas, track=track, traits=traits,
                               interaction=interaction, hard_select=hard_select, gate_repl=gate_repl)
        qc.save_statevector()                                 # Aer C++ statevector (fast)
        sv = VIV_SIM.run(transpile(qc, VIV_SIM)).result().get_statevector()
        probs = sv.probabilities_dict()

        def _p1(q: int) -> float:
            return sum(p for bits, p in probs.items() if bits[-(q + 1)] == "1")

        occ = [_p1(pj.viv_body_q(j, width, track, traits)) for j in range(track)]
        food = [_p1(pj.viv_food_q(j, width, track, traits)) for j in range(track)]
        energy = [_p1(pj.viv_energy_q(i, width, track, traits)) for i in range(n_food)]
        w_sim = float(sv.expectation_value(w_op).real)
        frames.append({
            "t": t,
            "body": [round(x, 4) for x in occ],
            "food": [round(x, 4) for x in food],
            "energy": [round(x, 4) for x in energy],
            "witness_sim": round(w_sim, 4),
            "alive": round(sum(occ), 4),
        })
    return frames


# ---------------------------------------------------------------------------
# Selective DD on the germ line only (AC-PJ2.10) -- vivarium analogue of PJ0's pass.
# ---------------------------------------------------------------------------
def schedule_vivarium_selective_dd(qc: QuantumCircuit, backend: Any, width: int, *,
                                   track: int = TRACK, traits: int = TRAITS) -> QuantumCircuit:
    """Transpile + schedule with DD padded on the germ (witness) physical qubits only; body/habitat/
    energy DD-free (the Weismann barrier). Returns the submit-ready circuit."""
    from qiskit.circuit.library import XGate
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    routed = pm.run(qc)

    germ_virtual = pj.viv_witness_qubits(width, track, traits)
    germ_physical: list[int] = []
    if routed.layout is not None:
        v2p = routed.layout.final_index_layout()
        germ_physical = [v2p[v] for v in germ_virtual if v < len(v2p)]

    durations = getattr(backend.target, "durations", lambda: None)()
    passes = [ALAPScheduleAnalysis(durations=durations),
              PadDynamicalDecoupling(durations=durations, dd_sequence=[XGate(), XGate()],
                                     qubits=germ_physical or None)]
    return PassManager(passes).run(routed)


def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------------------
# One arm = ONE measured circuit (no frame sweep) + the sim movie.
# ---------------------------------------------------------------------------
def run_arm(interaction: str, *, width: int, track: int, traits: int, steps: int,
            thetas: list[float], hard_select: bool, gate_repl: bool, shots: int, sim: bool,
            backend: Any) -> dict[str, Any]:
    """One measured circuit for the arm (the certified endpoint) + the sim-reconstructed movie."""
    qc = build_measured_vivarium(width, steps, thetas, interaction=interaction, track=track,
                                 traits=traits, hard_select=hard_select, gate_repl=gate_repl)
    if sim:
        counts = VIV_SIM.run(transpile(qc, VIV_SIM), shots=shots).result().get_counts()
    else:
        if SELECTIVE_DD:
            submit_qc = schedule_vivarium_selective_dd(qc, backend, width, track=track, traits=traits)
        else:
            submit_qc = generate_preset_pass_manager(optimization_level=3, backend=backend).run(qc)
        raw_meas, _jobs, _qs = run_sampler(backend, submit_qc, shots)
        counts = {}
        for s in raw_meas:
            counts[s] = counts.get(s, 0) + 1

    endpoint = reduce_counts(counts, width, track=track, traits=traits)
    endpoint["steps"] = steps
    endpoint["sim_frames"] = sim_snapshots(width, steps, thetas, interaction=interaction,
                                           track=track, traits=traits, hard_select=hard_select,
                                           gate_repl=gate_repl)
    return endpoint


def dump_circuits(width: int, track: int, traits: int, thetas: list[float], *, steps: int,
                  hard_select: bool, gate_repl: bool) -> None:
    for arm in ARMS:
        pj.print_vivarium_report(width, steps, thetas, track=track, traits=traits,
                                 interaction=arm, hard_select=hard_select, gate_repl=gate_repl)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ2 solo-vivarium driver -- one proto-viral organism in a habitat (one run); "
                    "banks the witness endpoint + the diagonal life story + the sim movie.")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the statevector Aer sim")
    ap.add_argument("--width", type=int, default=4, help="germ width W (12 HW anchor)")
    ap.add_argument("--track", type=int, default=TRACK, help="unary habitat/body sites")
    ap.add_argument("--traits", type=int, default=TRAITS, help="classical gene qubits (role/repl/life)")
    ap.add_argument("--interaction", choices=list(ARMS), default=None,
                    help="run one arm; default = run all three arms")
    ap.add_argument("--steps", type=int, default=None,
                    help="life-cycle steps (default: STEPS_SIM sim / STEPS_HW hardware)")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--hard-select", dest="hard_select", action="store_true",
                    help="append the optional static fitness comparator (contrast)")
    ap.add_argument("--gate-repl", dest="gate_repl", action="store_true",
                    help="route budding through the witness clone (measured-cost variant)")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated vivarium circuits (all arms) then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT run")
    ap.add_argument("--name", type=str, default="pj2_vivarium")
    args = ap.parse_args()
    sim = args.backend is None
    steps = args.steps if args.steps is not None else (STEPS_SIM if sim else STEPS_HW)
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
                print("[PJ2 ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not sim:
                print(f"[PJ2 ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not sim:
        print("[PJ2 ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    thetas = (qrng_thetas(client, args.width, MUT_SCALE, 0) if client is not None
              else q4._sim_thetas(args.width, args.width, mut_scale=MUT_SCALE))

    if args.dump_circuit:
        dump_circuits(args.width, args.track, args.traits, thetas, steps=steps,
                      hard_select=args.hard_select, gate_repl=args.gate_repl)
        if args.draw_only:
            raise SystemExit(0)

    backend = None
    backend_name = "statevector_sim"
    if not sim:
        backend = connect(args.backend)
        backend_name = backend.name
        nq = pj.viv_segment_len(args.width, args.track, args.traits,
                                len(pj.viv_food_sites(args.track)), hard_select=args.hard_select)
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits); vivarium needs {nq}")
        gated_chain(backend, nq)                       # chain-quality gate (CD-5); aborts if bad

    print(f"=== PJ2 vivarium: W={args.width} track={args.track} steps={steps} arms={arms} "
          f"on {backend_name} ===")
    arms_out: dict[str, Any] = {}
    sigma = math.sqrt(1.0 / args.shots)
    for arm in arms:
        res = run_arm(arm, width=args.width, track=args.track, traits=args.traits, steps=steps,
                      thetas=thetas, hard_select=args.hard_select, gate_repl=args.gate_repl,
                      shots=args.shots, sim=sim, backend=backend)
        res["survives"] = bool(res["entanglement_signal"] > K * sigma)
        arms_out[arm] = res
        print(f"  {arm:13} witness={res['witness_joint']:+.3f}  sep_null={res['separable_null']:+.3f}"
              f"  signal={res['entanglement_signal']:+.3f}  alive={res['alive']:.2f}  "
              f"food_left={sum(res['food_remaining']):.2f}  {'SURVIVES' if res['survives'] else 'at-null'}")

    result: dict[str, Any] = {
        "meta": {
            "stage": "PJ2", "model": "germsoma_vivarium", "backend": backend_name,
            "width": args.width, "track": args.track, "traits": args.traits,
            "food_sites": list(pj.viv_food_sites(args.track)), "steps": steps,
            "hop": HOP, "starve": STARVE, "arms": list(arms), "shots": args.shots,
            "sim": sim, "mut_scale": MUT_SCALE, "k": K, "selective_dd": SELECTIVE_DD,
            "hard_select": args.hard_select, "gate_repl": args.gate_repl,
            "one_run_no_frames": True, "calibration": None, "t1_band": None,
        },
        "arms": arms_out,
    }

    os.makedirs(os.path.join(OUTPUT_DIR, "pj2"), exist_ok=True)
    tag = timestamp() if not sim else "sim"
    out = os.path.join(OUTPUT_DIR, "pj2", f"{args.name}_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
