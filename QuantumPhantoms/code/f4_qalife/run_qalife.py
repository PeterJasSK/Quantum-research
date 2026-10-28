"""F4 entrypoint — run the Mode-A living-process loop, write the artifacts F2 consumes.

Usage (run from QuantumPhantoms/code/, `python -m`, like the F1/F2/F3 entrypoints):
    python -m f4_qalife.run_qalife --backend aer --founders 4 --generations 3 --survivors 1

The output dir is a drop-in replacement for an F1 run dir — feed it straight to F2/F3:
    python -m f2_imaging.build_tiles --run research_runs/qalife_aer_<ts>
    python -m f3_web.build_web       --run research_runs/qalife_aer_<ts>

HARD RULE (plan header): the implementer never runs hardware. `--backend ibm`/`auto` is
wired for Peter to run himself; it relies solely on a pre-existing saved IBM account — no
token is read or stored by this code.

Outputs under QuantumPhantoms/research_runs/<run>/ :
    cohort_params.json  — list[TumorParams]     (the Sampler output contract, for F2)
    quantum_run.json    — QuantumRun            (provenance: backend, job id, CHSH value)
    witness.json        — list[GenerationRecord](per-generation entanglement witness)
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import time

from f1_quantum.backend import get_backend
from f1_quantum.lineage import DEFAULT_THETA_MUT
from f1_quantum.rulebook import Rulebook
from f4_qalife.sampler import QALifeSampler

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.normpath(os.path.join(_HERE, "..", "..", "research_runs"))

# Division circuit is the widest: parent(9) + daughter(9) + fate(2).
MIN_QUBITS = 2 * 9 + 2


def _parse_args():
    ap = argparse.ArgumentParser(description="F4 Mode-A living-process loop — evolved cohort.")
    ap.add_argument("--backend", default="aer",
                    help="'aer'/'' = AerSimulator (default), 'auto' = least_busy, or a name like 'ibm_heron' (HUMAN-RUN).")
    ap.add_argument("--founders", type=int, default=4, help="independent founder lineages.")
    ap.add_argument("--generations", type=int, default=3, help="generations per lineage (0..G-1).")
    ap.add_argument("--survivors", type=int, default=1, help="cells kept per lineage per generation.")
    ap.add_argument("--offspring", type=int, default=4, help="candidates measured per lineage per generation (>= survivors).")
    ap.add_argument("--theta-mut", type=float, default=DEFAULT_THETA_MUT, help="division mutation angle (radians).")
    ap.add_argument("--phase", type=float, default=0.0, help="P2 fate phase dial (radians) — the interference knob.")
    ap.add_argument("--shots", type=int, default=4096, help="(reserved) shots; offspring drives candidate count.")
    ap.add_argument("--witness-shots", type=int, default=4096, help="shots per witness basis job.")
    ap.add_argument("--chsh-shots", type=int, default=4096, help="shots per CHSH setting.")
    return ap.parse_args()


def _run_name(args, backend) -> str:
    blabel = "aer" if backend is None else backend.name
    return f"qalife_{blabel}_{time.strftime('%Y%m%d-%H%M%S')}"


def _write_artifacts(run_dir: str, tiles, run, records) -> tuple[str, str, str]:
    os.makedirs(run_dir, exist_ok=True)
    cohort_path = os.path.join(run_dir, "cohort_params.json")
    run_path = os.path.join(run_dir, "quantum_run.json")
    witness_path = os.path.join(run_dir, "witness.json")
    with open(cohort_path, "w") as f:
        json.dump([t.to_dict() for t in tiles], f, indent=2, default=str)
    with open(run_path, "w") as f:
        json.dump(run.to_dict(), f, indent=2, default=str)
    with open(witness_path, "w") as f:
        json.dump([r.to_dict() for r in records], f, indent=2, default=str)
    return cohort_path, run_path, witness_path


def _print_summary(tiles, run, records):
    print("\n  #  gen  lineage     size   type          margin      lobe")
    print("  " + "-" * 62)
    for t in tiles:
        print(f"  {t.shot_index:<2} {t.generation:^3}  {t.lineage_id:<10}  "
              f"{t.size_mm:>5.1f}  {t.type:<12}  {t.margin:<10}  {t.lobe}")

    print("\n  generation  cells  survivors   W = <XX>+<ZZ>   verdict")
    print("  " + "-" * 60)
    for r in records:
        verdict = "entangled (> 1)" if r.witness_value > 1.0 else "separable (<= 1)"
        print(f"  {r.generation:^10}  {r.n_cells:^5}  {r.survivors:^9}   "
              f"{r.witness_value:>6.3f}  (XX {r.xx:+.3f}, ZZ {r.zz:+.3f})   {verdict}")

    s = run.chsh_value
    if isinstance(s, float) and math.isnan(s):
        print(f"\n  backend : {run.backend_name}   CHSH : n/a")
    else:
        verdict = "> 2  genuine quantum roll" if s > 2.0 else "<= 2  (noise/sim artifact)"
        print(f"\n  backend : {run.backend_name}   CHSH S = {s:.3f}   {verdict}")
    print("  honest label: Mode A — quantum WITHIN a generation, classical genealogy;")
    print("                tumor PARAMETERS are quantum; the IMAGE (F2) is a classical rendering.")


def main():
    args = _parse_args()

    if args.backend not in ("", "aer", "sim"):
        print("=" * 68)
        print("  HUMAN-RUN HARDWARE PATH — submitting real quantum jobs.")
        print("  This should be run by Peter, not by automated implementation.")
        print("  Uses a pre-existing saved IBM account; no token is read by this code.")
        print("=" * 68)

    rulebook = Rulebook()
    backend = get_backend(args.backend, min_qubits=MIN_QUBITS)

    sampler = QALifeSampler(
        founders=args.founders, generations=args.generations, survivors=args.survivors,
        offspring=args.offspring, theta_mut=args.theta_mut, phase=args.phase,
        shots=args.shots, witness_shots=args.witness_shots, chsh_shots=args.chsh_shots,
        backend=backend,
    )
    tiles = sampler.draw(rulebook)
    run = sampler.last_run
    records = sampler.generation_records

    run_dir = os.path.join(OUTPUT_BASE, _run_name(args, backend))
    cohort_path, run_path, witness_path = _write_artifacts(run_dir, tiles, run, records)

    _print_summary(tiles, run, records)
    print(f"\n  wrote {len(tiles)} tiles -> {cohort_path}")
    print(f"  wrote provenance     -> {run_path}")
    print(f"  wrote witness        -> {witness_path}")


if __name__ == "__main__":
    main()
