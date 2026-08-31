#!/usr/bin/env python3
"""User-side QC submission helper for F5 (NOT part of the no-auto-submit harness).

hardware_batches.py `emit` writes QPY circuits + a submit bundle and STOPS. This script is the
thing YOU run by hand to put those circuits on the backend and save per-generation counts JSON in
exactly the shape `hardware_batches.py ingest` expects ({bitstring: count}). It is deliberately a
separate file so F5 never submits as a side effect.

Run:
    cd THESIS/CriticalQuantumLife/code
    python submit_batch.py --bundle ../research_runs/cql_f5_batch0_closed_ibm_kingston_submit.json \\
        --shots 8192 --out-prefix ../research_runs/b0_closed_gen

Then feed the printed counts files to `hardware_batches.py ingest` (it prints the exact command).
"""
from __future__ import annotations

import argparse
import functools
import json
import os

from qiskit import qpy
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

print = functools.partial(print, flush=True)


def _counts_from_pub(pub_result) -> dict[str, int]:
    """Extract {bitstring: count} from a SamplerV2 pub result, whatever the classical register is
    named (measure_all -> 'meas'; some flows -> 'c')."""
    data = pub_result.data
    names = list(data.keys()) if hasattr(data, "keys") else [n for n in vars(data)]
    if not names:
        raise SystemExit("[ABORT] no classical register in the result data")
    reg = names[0]
    return {str(k): int(v) for k, v in data[reg].get_counts().items()}


def main() -> None:
    ap = argparse.ArgumentParser(description="F5 user-side QC submission helper")
    ap.add_argument("--bundle", required=True, help="a *_submit.json bundle from emit")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--out-prefix", required=True,
                    help="counts written to <prefix>0.json .. <prefix>N.json in gen order")
    ap.add_argument("--backend", default=None, help="override the bundle's backend")
    args = ap.parse_args()

    with open(args.bundle) as fh:
        bundle = json.load(fh)
    backend_name = args.backend or bundle["backend"]
    here = os.path.dirname(os.path.abspath(args.bundle))
    circuits = bundle["circuits"]
    gens = bundle["global_gens"]
    print(f"=== submit {bundle['arm']} batch {bundle['batch']} on {backend_name}: "
          f"{len(circuits)} circuits x {args.shots} shots ===")

    service = QiskitRuntimeService()
    backend = service.backend(backend_name)
    sampler = SamplerV2(mode=backend)

    written: list[str] = []
    for i, cname in enumerate(circuits):
        with open(os.path.join(here, cname), "rb") as fh:
            qc = qpy.load(fh)[0]                   # one ISA circuit per file
        print(f"  gen {gens[i]}: submitting {cname} ...")
        job = sampler.run([qc], shots=args.shots)
        print(f"    job {job.job_id()} -> waiting")
        counts = _counts_from_pub(job.result()[0])
        out = f"{args.out_prefix}{i}.json"
        with open(out, "w") as fh:
            json.dump(counts, fh)
        written.append(out)
        print(f"    -> {out}  ({len(counts)} distinct bitstrings)")

    print("\n  DONE. Ingest with:")
    joined = " ".join(written)
    print(f"    python hardware_batches.py ingest --bundle {args.bundle} \\")
    print(f"      --counts {joined} \\")
    print(f"      --width {bundle['width']} --shots {args.shots} --name "
          f"{os.path.basename(args.bundle).split('_batch')[0]}")


if __name__ == "__main__":
    main()
