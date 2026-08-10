#!/usr/bin/env python3
"""
pipeline.py — Quantum Galton Board: reuse wiring for the Heron r2 submission
path + the frozen run.json / summary.json writers.

Reuse-not-copy (epic §3.3): the IBM submission pipeline is imported from the
CalibrationGuidedHighYieldQRNG study, never reimplemented. This module bootstraps
that import (mirroring QuantumLife/code/qtree.py:80-86) and re-exports
connect / run_sampler / timestamp so the rest of the package imports them from
here.

Import-path note (plan OQ-1.1): the epic and QuantumLife's own qtree.py resolve
`../../CalibrationGuidedHighYieldQRNG/code`, but that directory no longer exists
on disk -- the calibration study was reorganised and pipeline_common.py now lives
under `old/code/`. We try `.../code` first (the documented location) then
`.../old/code`, and raise a clear error naming both if neither has
pipeline_common.py. (Epic §3.3 / Appendix A.1 still need this correction.)

The classical register that run_sampler reads MUST be named "c" -- run_sampler
calls res[0].data.c.get_bitstrings(). classical_register() below enforces that.
"""

from __future__ import annotations

import json
import os
import sys

from qiskit import ClassicalRegister

_HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve_calib_code() -> str:
    """Locate the calibration study's code dir containing pipeline_common.py."""
    candidates = [
        os.path.normpath(os.path.join(
            _HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", "code")),
        os.path.normpath(os.path.join(
            _HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", "old", "code")),
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "pipeline_common.py")):
            return path
    raise ModuleNotFoundError(
        "pipeline_common.py not found. Tried:\n  "
        + "\n  ".join(candidates)
        + "\nReuse-not-copy (epic §3.3) requires the calibration study's "
        "submission pipeline; check the CalibrationGuidedHighYieldQRNG layout.")


_CALIB_CODE = _resolve_calib_code()
sys.path.insert(0, _CALIB_CODE)
from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

# output directories mirror the QuantumLife runs/ + research_runs/ split
RUNS_DIR = os.path.normpath(os.path.join(_HERE, "..", "runs"))
RESEARCH_RUNS_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# --- frozen schema constants (consumed by scaffold_check + P2/P3/P4) ---------
REQUIRED_RUN_KEYS = [
    "meta", "counts", "position_histogram", "quantum_seconds", "jobs_meta",
]
REQUIRED_META_KEYS = [
    "project", "arm", "backend", "sim", "timestamp", "steps",
    "n_position_qubits", "n_qubits", "qubit_list", "coin", "shots", "seed",
    "walk_spec", "chain_stats", "calibration",
]

__all__ = [
    "connect", "run_sampler", "timestamp", "classical_register",
    "write_run", "write_summary", "RUNS_DIR", "RESEARCH_RUNS_DIR",
    "REQUIRED_RUN_KEYS", "REQUIRED_META_KEYS",
]


def classical_register(width: int) -> ClassicalRegister:
    """A ClassicalRegister named "c" -- required by pipeline_common.run_sampler
    (it reads res[0].data.c.get_bitstrings()); epic §3.3 / Appendix A.2."""
    return ClassicalRegister(width, "c")


def write_run(meta: dict, counts: dict[str, int],
              position_histogram: dict[int, float], quantum_seconds: float,
              jobs_meta: object = None, out_dir: str = RUNS_DIR) -> str:
    """Write one frozen run.json for a single (arm, steps) run; return its path.

    Filename mirrors the QuantumLife research driver:
    ``<arm>_<backend>_steps<n>_seed<seed>_<ts>_run.json``. `meta` must already
    carry WALK_SPEC embedded verbatim under "walk_spec" and a "timestamp".
    """
    os.makedirs(out_dir, exist_ok=True)
    ts = meta["timestamp"]
    stem = (f"{meta['arm']}_{meta['backend']}_steps{meta['steps']}"
            f"_seed{meta['seed']}_{ts}")
    out_path = os.path.join(out_dir, f"{stem}_run.json")
    payload = {
        "meta": meta,
        "counts": counts,
        # JSON object keys are strings; positions are ints -> stringify keys
        "position_histogram": {str(pos): p for pos, p in position_histogram.items()},
        "quantum_seconds": quantum_seconds,
        "jobs_meta": jobs_meta,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, default=str)
    return out_path


def write_summary(meta: dict, per_depth: list[dict],
                  out_dir: str = RESEARCH_RUNS_DIR) -> str:
    """Write one frozen summary.json for a sweep; return its path.

    P1 defines the schema and this writer; P4 populates per_depth across the
    sweep. Filename: ``<arm>_<backend>_<ts>_summary.json`` (same stem as the
    per-run files minus the seed segment).
    """
    os.makedirs(out_dir, exist_ok=True)
    ts = meta["timestamp"]
    stem = f"{meta['arm']}_{meta['backend']}_{ts}"
    out_path = os.path.join(out_dir, f"{stem}_summary.json")
    with open(out_path, "w") as f:
        json.dump({"meta": meta, "per_depth": per_depth}, f, default=str)
    return out_path
