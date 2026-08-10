#!/usr/bin/env python3
"""
scaffold_check.py — Quantum Galton Board: offline correctness gate.

No network, no QPU. Runs the ideal 2-step path in-process and asserts the frozen
contract holds. This is the AC-1.1 + AC-1.3 verification mechanism (epic §3.6);
there is no pytest suite. Exits non-zero on any breach.

Checks:
  * run.json exists and has every required top-level + meta key (§7);
  * the embedded walk_spec equals WALK_SPEC verbatim;
  * position_histogram sums to 1 +/- 1e-6;
  * the reference circuit's classical register is named "c" (epic §3.3);
  * meta carries a qubit_list key (null for sim; best_chain result for hw).
"""

from __future__ import annotations

import json
import sys

import config
import galton
import pipeline
from walk_spec import WALK_SPEC

STEPS = 2


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    cfg = config.load(argparse_seed())
    out_path, payload = galton.run_ideal(STEPS, cfg, sim=True)

    # the written file must exist and round-trip
    try:
        with open(out_path) as f:
            on_disk = json.load(f)
    except OSError as exc:
        _fail(f"run.json not written: {exc}")

    # required top-level keys
    for key in pipeline.REQUIRED_RUN_KEYS:
        if key not in on_disk:
            _fail(f"run.json missing top-level key {key!r}")

    meta = on_disk["meta"]
    for key in pipeline.REQUIRED_META_KEYS:
        if key not in meta:
            _fail(f"run.json meta missing key {key!r}")

    # walk_spec embedded verbatim
    if meta["walk_spec"] != WALK_SPEC:
        _fail(f"embedded walk_spec != WALK_SPEC\n  got {meta['walk_spec']}\n  want {WALK_SPEC}")

    # position_histogram normalised
    total = sum(float(v) for v in on_disk["position_histogram"].values())
    if abs(total - 1.0) > 1e-6:
        _fail(f"position_histogram sums to {total}, not 1 +/- 1e-6")

    # qubit_list key present (null for sim)
    if "qubit_list" not in meta:
        _fail("meta.qubit_list key absent")

    # classical register named "c"
    qc = galton.build_reference_walk(STEPS)
    creg_names = [creg.name for creg in qc.cregs]
    if "c" not in creg_names:
        _fail(f"classical register not named 'c' (found {creg_names})")

    print(f"OK: {out_path}")
    print(f"  keys ok, walk_spec verbatim, histogram sum={total:.6f}, creg 'c' present")
    sys.exit(0)


def argparse_seed():
    # deterministic in-process run; reuse config defaults / env, fixed seed
    class _A:
        backend = None
        shots = None
        seed = 100
        n_max = None
    return _A()


if __name__ == "__main__":
    main()
