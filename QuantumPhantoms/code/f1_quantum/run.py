"""F1 entrypoint — roll a certified quantum cohort, write the artifacts F2 consumes.

Usage (the only path /implement-feature runs):
    python QuantumPhantoms/code/run.py --backend aer --tiles 12 --pairs 2

HARD RULE (plan header): the implementer never runs hardware. `--backend ibm`/`auto` is
wired for Peter to run himself; it is announced with a banner and relies solely on a
pre-existing saved IBM account — no token is read or stored by this code.

Outputs under QuantumPhantoms/research_runs/<run>/ :
    cohort_params.json  — list[TumorParams]   (the Sampler output contract, for F2)
    quantum_run.json    — QuantumRun          (provenance: backend, job id, CHSH value)
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import time

from f1_quantum.backend import get_backend
from f1_quantum.rulebook import Rulebook
from f1_quantum.sampler import PRNGSampler, QRNGSampler

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.normpath(os.path.join(_HERE, "..", "..", "research_runs"))


def _parse_args():
    ap = argparse.ArgumentParser(description="F1 quantum roll — certified tumor cohort.")
    ap.add_argument("--backend", default="aer",
                    help="'aer'/'' = AerSimulator (default), 'auto' = least_busy, or a name like 'ibm_heron' (HUMAN-RUN).")
    ap.add_argument("--sampler", choices=("qrng", "prng"), default="qrng",
                    help="qrng = quantum pipeline (default); prng = classical baseline.")
    ap.add_argument("--tiles", type=int, default=12, help="cohort size (epic default 12).")
    ap.add_argument("--pairs", type=int, default=2, help="number of sibling pairs among the tiles.")
    ap.add_argument("--shots", type=int, default=4096, help="shots for the tumor/sibling circuits.")
    ap.add_argument("--chsh-shots", type=int, default=4096, help="shots per CHSH setting.")
    ap.add_argument("--theta-mut", type=float, default=0.3, help="division mutation angle (radians).")
    ap.add_argument("--seed", type=int, default=0, help="PRNG seed (prng sampler only).")
    return ap.parse_args()


def _build_sampler(args, backend):
    if args.sampler == "prng":
        return PRNGSampler(n_tiles=args.tiles, n_pairs=args.pairs, seed=args.seed)
    return QRNGSampler(
        n_tiles=args.tiles, n_pairs=args.pairs, shots=args.shots,
        chsh_shots=args.chsh_shots, backend=backend, theta_mut=args.theta_mut,
    )


def _run_name(args, backend) -> str:
    if backend is None:
        blabel = "prng" if args.sampler == "prng" else "aer"
    else:
        blabel = backend.name
    return f"{args.sampler}_{blabel}_{time.strftime('%Y%m%d-%H%M%S')}"


def _write_artifacts(run_dir: str, tiles, run) -> tuple[str, str]:
    os.makedirs(run_dir, exist_ok=True)
    cohort_path = os.path.join(run_dir, "cohort_params.json")
    run_path = os.path.join(run_dir, "quantum_run.json")
    with open(cohort_path, "w") as f:
        json.dump([t.to_dict() for t in tiles], f, indent=2, default=str)
    with open(run_path, "w") as f:
        json.dump(run.to_dict(), f, indent=2, default=str)
    return cohort_path, run_path


def _print_summary(tiles, run):
    print("\n  #  gen  lineage     size   type          margin      lobe")
    print("  " + "-" * 62)
    for t in tiles:
        print(f"  {t.shot_index:<2} {t.generation:^3}  {t.lineage_id:<10}  "
              f"{t.size_mm:>5.1f}  {t.type:<12}  {t.margin:<10}  {t.lobe}")
    s = run.chsh_value
    if isinstance(s, float) and math.isnan(s):
        print(f"\n  backend : {run.backend_name}   CHSH : n/a (classical baseline)")
    else:
        verdict = "> 2  genuine quantum roll" if s > 2.0 else "<= 2  (noise/sim artifact)"
        print(f"\n  backend : {run.backend_name}   CHSH S = {s:.3f}   {verdict}")
    print("  honest label: tumor PARAMETERS are quantum; the IMAGE (F2) is a classical rendering.")


def main():
    args = _parse_args()

    if args.backend not in ("", "aer", "sim"):
        print("=" * 68)
        print("  HUMAN-RUN HARDWARE PATH — submitting a real quantum job.")
        print("  This should be run by Peter, not by automated implementation.")
        print("  Uses a pre-existing saved IBM account; no token is read by this code.")
        print("=" * 68)

    rulebook = Rulebook()
    min_q = 18  # sibling circuit is the widest (2 x 9 property qubits)
    backend = get_backend(args.backend, min_qubits=min_q)

    sampler = _build_sampler(args, backend)
    tiles = sampler.draw(rulebook)
    run = sampler.last_run

    run_dir = os.path.join(OUTPUT_BASE, _run_name(args, backend))
    cohort_path, run_path = _write_artifacts(run_dir, tiles, run)

    _print_summary(tiles, run)
    print(f"\n  wrote {len(tiles)} tiles -> {cohort_path}")
    print(f"  wrote provenance     -> {run_path}")


if __name__ == "__main__":
    main()
