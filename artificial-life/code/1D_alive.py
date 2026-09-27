#!/usr/bin/env python3
"""PJ2.2b 1D-LINE vivarium driver -- a walking occupancy field + germ witness (DEPTH SCAN).

The 1D sibling of ``2D_alive.py`` (the square-lattice driver). Identical honest model and data
contract; the ONLY difference is the substrate: the organism is a unary occupancy field on a
length-L CHAIN that WALKS (an excitation-conserving rxx+ryy quantum walk between linear neighbours
i-1 / i+1) instead of a 2D grid. The single quantum claim is the germ-line genealogical witness
<X^W>. Three modes (solo / replicate / duo) x two arms (isolated germ line / coupled = the
soma->germ wound).

Same defining lock as 2D: CERTIFIED FRAMES VIA A DEPTH SCAN. On hardware each generation
d in {0..gens-1} is its OWN measured circuit with d walk layers, measured once for occupancy (Z)
+ germ witness (X) with a separable-null control -- NO interpolation on the certified path. Sim
shares the same depth-scan code path on a statevector Aer backend.

Design: imports the shared MODEL from ``pj_qalife`` (``build_line_vivarium`` + the ``line_*``
helpers, the 1D parallel of the ``lat_*`` lattice section) and REUSES PJ0's driver infra BY
IMPORT (``gated_chain``, ``qrng_thetas``, ``connect`` / ``run_sampler`` / ``timestamp``,
``OUTPUT_DIR``). Selective DD on the germ line only, re-used from the lattice pattern.

Usage:
    cd artificial-life/code
    python 1D_alive.py --length 9 --gens 6 --repeats 1            # sim, all 3 modes x 2 arms
    python 1D_alive.py --length 16 --movement-only --gens 6       # sim, L=16 solo (just the movement)
    python 1D_alive.py --dump-circuit --draw-only --length 9 --mode solo
    python 1D_alive.py --backend <heron> --length 9 --mode solo --gens 6 --shots 8192
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import statistics
from typing import Any

from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

import pj_qalife as pj
import qalife as q4

from pj_run_qalife import (          # noqa: E402  -- reuse PJ0 infra, no edit
    OUTPUT_DIR, connect, gated_chain, qrng_thetas, run_sampler, timestamp,
)
from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- study parameters -------------------------------------------------------
LENGTH = 9                           # chain length L (9 cells == the 3x3 qubit budget)
WIDTH = 3                            # germ width W (the witness set)
GENS = 6                            # generations 0..5 (the depth axis)
MODES = ("solo", "replicate", "duo")
ARMS = ("isolated", "coupled")
HOP = pj.LINE_HOP                    # isotropic quantum-walk hop angle
K = 2.0                             # significance multiplier (k=2 headline, k=3 reported)
MUT_SCALE = 0.0                     # faithful clean GHZ -> isolate the walk's witness cost
SELECTIVE_DD = True
REPEATS = 1
QEAAS_URL = os.environ.get("QEAAS_API_URL", "https://api.qeaas.eu")

LINE_SIM = AerSimulator(method="statevector")
_SV_MAX_QUBITS = 27                  # statevector feasibility cap


# ---------------------------------------------------------------------------
# Measured build -- germ loci in X (witness), body cells in Z (occupancy). ONE circuit.
# ---------------------------------------------------------------------------
def active_witness_qubits(width: int, length: int, mode: str, gens: int) -> list[int]:
    """The germ loci carrying the joint <X^W> at THIS depth. For replicate the daughter germ line
    does not exist until the clone at gen LINE_REP_GEN, so before then the witness is the parent
    block only (H-ing the still-|0> daughter germ would inject random X-parity and null the joint)."""
    if mode == "replicate" and gens < pj.LINE_REP_GEN:
        return [pj.line_witness_q(0, k, width, length) for k in range(width)]
    return pj.line_witness_qubits(width, length, mode)


def build_measured_line(width: int, length: int, gens: int, thetas: list[float], *, mode: str,
                        arm: str, start: int = 0, hop: float = HOP,
                        pokes: list[tuple[int, int, float]] | None = None) -> QuantumCircuit:
    """Build the walk to depth `gens`, rotate the ACTIVE germ loci into X (witness), leave the body
    cells in Z (occupancy), add a classical register, measure all -- one circuit per certified frame."""
    qc = pj.build_line_vivarium(width, length, gens, thetas, mode=mode, arm=arm, start=start,
                                hop=hop, pokes=pokes)
    for q in active_witness_qubits(width, length, mode, gens):
        qc.h(q)                                                   # X-basis readout on the germ only
    n_data = qc.num_qubits
    creg = ClassicalRegister(n_data, "c")
    qc.add_register(creg)
    qc.measure(range(n_data), creg)
    return qc


def _marginal_p1(counts: dict[str, int], q: int, total: int) -> float:
    return sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total


def reduce_counts(counts: dict[str, int], width: int, length: int, *, mode: str,
                  gens: int) -> dict[str, Any]:
    """Measured observables from ONE counts dict: the germ witness + the 1D occupancy field."""
    total = sum(counts.values()) or 1
    joint, sep = q4.xbasis_witness_from_counts(counts,
                                               active_witness_qubits(width, length, mode, gens))
    fields: list[list[float]] = []
    for o in range(pj.line_n_organisms(mode)):
        occ = [round(_marginal_p1(counts, pj.line_body_q(o, i, width, length), total), 4)
               for i in range(length)]
        fields.append(occ)
    overlap = 0.0
    if mode == "duo":
        overlap = sum(min(fields[0][i], fields[1][i]) for i in range(length))
    return {"witness_joint": joint, "separable_null": sep, "fields": fields,
            "overlap": round(float(overlap), 4)}


# ---------------------------------------------------------------------------
# Selective DD on the germ line only -- 1D analogue of the lattice pass.
# ---------------------------------------------------------------------------
def schedule_line_selective_dd(qc: QuantumCircuit, backend: Any, width: int, length: int, *,
                               mode: str) -> QuantumCircuit:
    """Transpile + schedule with DD padded on the germ (witness) physical qubits only; body/chain
    DD-free (the Weismann barrier). Returns the submit-ready circuit."""
    from qiskit.circuit.library import XGate
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    routed = pm.run(qc)

    germ_virtual = pj.line_witness_qubits(width, length, mode)
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
# The certified depth scan -- one measured circuit per (mode, arm, gen, repeat).
# ---------------------------------------------------------------------------
def _run_counts(qc: QuantumCircuit, *, sim: bool, backend: Any, shots: int, width: int, length: int,
                mode: str) -> dict[str, int]:
    if sim:
        return LINE_SIM.run(transpile(qc, LINE_SIM), shots=shots).result().get_counts()
    if SELECTIVE_DD:
        submit_qc = schedule_line_selective_dd(qc, backend, width, length, mode=mode)
    else:
        submit_qc = generate_preset_pass_manager(optimization_level=3, backend=backend).run(qc)
    raw_meas, _jobs, _qs = run_sampler(backend, submit_qc, shots)
    counts: dict[str, int] = {}
    for s in raw_meas:
        counts[s] = counts.get(s, 0) + 1
    return counts


def depth_scan(width: int, length: int, gens: int, thetas: list[float], *, mode: str, arm: str,
               start: int, hop: float, sim: bool, backend: Any, shots: int, repeats: int,
               pokes: list[tuple[int, int, float]] | None = None) -> list[dict[str, Any]]:
    """The honest frames: for d in range(gens) build a circuit with d walk layers, measure it once
    per repeat, reduce -> one certified frame {gen, fields, w, w_sigma, sep, survives, overlap, n}."""
    sigma_shot = math.sqrt(1.0 / shots)
    frames: list[dict[str, Any]] = []
    for d in range(gens):
        qc = build_measured_line(width, length, d, thetas, mode=mode, arm=arm, start=start,
                                 hop=hop, pokes=pokes)
        joints: list[float] = []
        reduced: dict[str, Any] = {}
        for _rep in range(max(1, repeats)):
            counts = _run_counts(qc, sim=sim, backend=backend, shots=shots, width=width,
                                 length=length, mode=mode)
            reduced = reduce_counts(counts, width, length, mode=mode, gens=d)
            joints.append(reduced["witness_joint"])
        w = statistics.fmean(joints)
        spread = statistics.pstdev(joints) if len(joints) > 1 else 0.0
        w_sigma = math.sqrt(spread ** 2 + sigma_shot ** 2)
        fields = reduced["fields"]
        n_alive = sum(1 for f in fields if sum(f) > 0.05)
        frames.append({
            "gen": d,
            "fields": fields,
            "w": round(float(w), 4),
            "w_sigma": round(float(w_sigma), 4),
            "sep": round(float(reduced["separable_null"]), 4),
            "overlap": reduced["overlap"],
            "n": n_alive,
            "survives": bool(w - reduced["separable_null"] > K * w_sigma),
        })
    return frames


# ---------------------------------------------------------------------------
# QRNG-certified environment (start cell + hop), fail-closed on hardware.
# ---------------------------------------------------------------------------
def qrng_environment(client: QRNGClient | None, length: int, sim: bool) -> tuple[int, float]:
    """Draw the start cell + hop angle from certified quantum entropy (fixed per run). Sim may fall
    back to deterministic defaults; hardware is fail-closed (QRNGUnavailable propagates)."""
    if client is None:
        return 0, HOP
    try:
        resp = client.fetch(size=32, fmt="hex")
    except QRNGUnavailable:
        if sim:
            return 0, HOP                                          # sim PRNG-fallback
        raise                                                     # fail-closed on hardware
    raw = bytes.fromhex(resp.data)
    start = int.from_bytes(raw[0:4], "big") % length
    hop = 0.45 + 0.30 * (int.from_bytes(raw[4:8], "big") / 2 ** 32)   # isotropic angle in [0.45,0.75)
    return start, round(hop, 4)


def _read_env_key(name: str) -> str | None:
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


def dump_circuits(width: int, length: int, gens: int, thetas: list[float], *, modes: tuple[str, ...],
                  arms: tuple[str, ...]) -> None:
    for mode in modes:
        for arm in arms:
            pj.print_line_report(width, length, gens, thetas, mode=mode, arm=arm)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PJ2.2b 1D-line vivarium driver -- a walking occupancy field + germ witness; "
                    "banks the certified depth-scan frames (the 1D sibling of 2D_alive.py).")
    ap.add_argument("--backend", type=str, default=None,
                    help="hardware backend name; omit to run on the statevector Aer sim")
    ap.add_argument("--length", type=int, default=LENGTH, help="chain length L (line cells)")
    ap.add_argument("--width", type=int, default=WIDTH, help="germ width W (the witness set)")
    ap.add_argument("--mode", choices=list(MODES), default=None,
                    help="run one mode; default = run all three (solo when --movement-only)")
    ap.add_argument("--arm", choices=list(ARMS), default='isolated',
                    help="run one arm; default = both")
    ap.add_argument("--gens", type=int, default=GENS, help="generations (depth scan 0..gens-1); "
                    "more = more movement + deeper (push until the witness finally falls)")
    ap.add_argument("--hop", type=float, default=None,
                    help="walk hop angle = movement per generation; overrides the QRNG value. "
                         "bigger = the field travels farther each step (default ~0.45-0.75 QRNG / 0.6)")
    ap.add_argument("--start", type=int, default=None,
                    help="force the seed cell (default: QRNG-drawn) -- e.g. 0 to start at one end")
    ap.add_argument("--repeats", type=int, default=REPEATS, help="repeats for sigma")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--movement-only", dest="movement_only", action="store_true",
                    help="force mode=solo (the long-chain 'just the movement' run)")
    ap.add_argument("--dump-circuit", dest="dump_circuit", action="store_true",
                    help="print the annotated line circuits then run")
    ap.add_argument("--draw-only", dest="draw_only", action="store_true",
                    help="with --dump-circuit: draw and exit, do NOT run")
    ap.add_argument("--poke", action="append", default=None, metavar="SPEC",
                    help="sudden perturbation that SETS a cell's occupancy; REPEATABLE. Each SPEC is "
                         "'N', 'N:POS' or 'N:POS:AMP' (gen : cell : target 0..1). Repeat for pokes at "
                         "different gens; reuse the same gen for several spots set at once. "
                         "e.g. --poke 5:3:0.01 (set cell 3 to 1%% at gen 5)")
    ap.add_argument("--poke-position", dest="poke_position", type=int, default=None,
                    help="default cell for a bare '--poke N' (default: chain centre)")
    ap.add_argument("--poke-amp", dest="poke_amp", type=float, default=1.0,
                    help="default target 0..1 for pokes without :AMP (1.0 = set to 100%%; 0.01 = 1%%)")
    ap.add_argument("--name", type=str, default="pj2_line")
    args = ap.parse_args()
    sim = args.backend is None
    modes = ("solo",) if args.movement_only else ((args.mode,) if args.mode else MODES)
    arms = (args.arm,) if args.arm else ARMS

    # --- pokes (sudden perturbations): repeatable --poke N|N:POS|N:POS:AMP -----------------------
    default_pos = args.poke_position if args.poke_position is not None else args.length // 2
    pokes: list[tuple[int, int, float]] = []
    for spec in (args.poke or []):
        parts = spec.strip().split(":")
        g = int(parts[0])
        p = int(parts[1]) if len(parts) > 1 and parts[1] != "" else default_pos
        a = float(parts[2]) if len(parts) > 2 and parts[2] != "" else args.poke_amp
        if not 0 <= g <= args.gens:
            print(f"[PJ2.2b ABORT] --poke gen {g} out of range 0..{args.gens}"); raise SystemExit(1)
        pokes.append((g, max(0, min(args.length - 1, p)), max(0.0, min(1.0, a))))

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
                print("[PJ2.2b ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not sim:
                print(f"[PJ2.2b ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not sim:
        print("[PJ2.2b ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    thetas = (qrng_thetas(client, args.width, MUT_SCALE, 0) if client is not None
              else q4._sim_thetas(args.width, args.width, mut_scale=MUT_SCALE))
    start, hop = qrng_environment(client, args.length, sim)
    if args.hop is not None:                                       # force the movement rate
        hop = args.hop
    if args.start is not None:                                     # force the seed cell
        start = args.start % args.length

    if args.dump_circuit:
        dump_circuits(args.width, args.length, args.gens, thetas, modes=modes, arms=arms)
        if args.draw_only:
            raise SystemExit(0)

    backend = None
    backend_name = "statevector_sim"
    if not sim:
        backend = connect(args.backend)
        backend_name = backend.name
        nq = max(pj.line_segment_len(args.width, args.length, m) for m in modes)
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits); line needs {nq}")
        gated_chain(backend, nq)                       # chain-quality gate; aborts if bad
    else:
        nq = max(pj.line_segment_len(args.width, args.length, m) for m in modes)
        if nq > _SV_MAX_QUBITS:
            print(f"[PJ2.2b ABORT] {nq} qubits > sim cap {_SV_MAX_QUBITS} "
                  f"(long-chain replicate/duo are out of scope; use --movement-only).")
            raise SystemExit(1)

    poke_str = (" pokes=" + ",".join(f"g{g}@c{p}(a{a})" for g, p, a in pokes)) if pokes else ""
    print(f"=== PJ2.2b line: W={args.width} L={args.length} gens={args.gens} "
          f"modes={modes} arms={arms} start={start} hop={hop}{poke_str} on {backend_name} ===")

    scenarios: dict[str, Any] = {}
    endpoint: dict[str, Any] = {}
    for mode in modes:
        scenarios[mode] = {}
        endpoint[mode] = {}
        for arm in arms:
            frames = depth_scan(args.width, args.length, args.gens, thetas, mode=mode, arm=arm,
                                start=start, hop=hop, sim=sim, backend=backend, shots=args.shots,
                                repeats=args.repeats, pokes=pokes)
            scenarios[mode][arm] = frames
            last = frames[-1]
            endpoint[mode][arm] = {"w": last["w"], "survives": last["survives"]}
            depth = q4.entanglement_depth([f["w"] for f in frames], [f["sep"] for f in frames],
                                          [f["w_sigma"] for f in frames], k=K)
            print(f"  {mode:10} {arm:9} witness[0..{args.gens - 1}]="
                  f"{[f['w'] for f in frames]}  collapse@gen>{depth}  "
                  f"{'SURVIVES' if last['survives'] else 'at-null'}")

    result: dict[str, Any] = {
        "meta": {
            "stage": "PJ2.2b", "model": "line_vivarium", "backend": backend_name,
            "length": args.length, "width": args.width, "gens": args.gens,
            "modes": list(modes), "arms": list(arms), "shots": args.shots, "sim": sim,
            "k": K, "hop": hop, "start": start, "mut_scale": MUT_SCALE,
            "selective_dd": SELECTIVE_DD, "repeats": args.repeats,
            "certified_frames": True, "calibration": None,
            "pokes": [{"gen": g, "pos": p, "amp": round(a, 4)} for g, p, a in pokes],
        },
        "scenarios": scenarios,
        "endpoint": endpoint,
    }

    os.makedirs(os.path.join(OUTPUT_DIR, "pj2_line"), exist_ok=True)
    tag = timestamp() if not sim else "sim"
    out = os.path.join(OUTPUT_DIR, "pj2_line", f"{args.name}_L{args.length}_"
                       f"{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
