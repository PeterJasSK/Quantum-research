#!/usr/bin/env python3
"""
pipeline_common.py — shared submission pipeline forked from
ErrorDetectionVSRawBits/qrng_bell_pairs.py (D1). Do not edit the original;
Stage A / Stage B / calibration scripts import from here.
"""

from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime
from typing import Any, Callable

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ===========================================================================
# CONFIG
# ===========================================================================
SHOTS_PER_JOB: int = 50_000
OUTPUT_DIR: str = "qrng_output"
HERON_R2_CANDIDATES: list[str] = ["ibm_kingston", "ibm_fez", "ibm_marrakesh"]
PAYG_USD_PER_SEC: float = 1.60
# ===========================================================================


def connect(name: str | None) -> Any:
    """Live QiskitRuntimeService connection; explicit backend or least-busy Heron r2."""
    service = QiskitRuntimeService()
    if name:
        return service.backend(name)
    return service.least_busy(operational=True, simulator=False, min_num_qubits=100,
                               filters=lambda b: b.name in HERON_R2_CANDIDATES)


def qpu_seconds(job: Any) -> float:
    try:
        return float(job.metrics()["usage"]["quantum_seconds"])
    except Exception:
        try:
            return float(job.usage())
        except Exception:
            return float("nan")


def _safe(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception as e:
        return {"_error": str(e)}


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def run_sampler(backend: Any, isa: Any, shots: int,
                 shots_per_job: int = SHOTS_PER_JOB) -> tuple[list[str], list[dict[str, Any]], float]:
    """Chunked SamplerV2 run loop, identical structure to qrng_bell_pairs.py:186-204."""
    sampler = Sampler(mode=backend)
    raw_meas: list[str] = []
    jobs_meta: list[dict[str, Any]] = []
    total_qs = 0.0
    remaining, ci = shots, 0
    while remaining > 0:
        chunk = min(shots_per_job, remaining)
        ci += 1
        job = sampler.run([isa], shots=chunk)
        print(f"  job {ci}: {job.job_id()} ({chunk:,} shots) ...", end="", flush=True)
        res = job.result()
        bs = res[0].data.c.get_bitstrings()
        raw_meas.extend(bs)
        qs = qpu_seconds(job)
        total_qs += 0.0 if math.isnan(qs) else qs
        jobs_meta.append({
            "job_id": job.job_id(), "shots": chunk, "quantum_seconds": qs,
            "metrics": _safe(job.metrics),
            "result_metadata": _safe(lambda: res.metadata),
            "pub_metadata": _safe(lambda: res[0].metadata),
        })
        print(f" done (qpu {qs:.2f}s)")
        remaining -= chunk
    return raw_meas, jobs_meta, total_qs


def write_raw_json(stem: str, run_meta: dict[str, Any], jobs_meta: list[dict[str, Any]],
                    raw_meas: list[str], calib: dict[str, Any] | None) -> str:
    """Writes stem + '_raw.json' with run metadata, jobs, raw measurements, and calibration snapshot."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_path = stem + "_raw.json"
    raw = {
        "run": run_meta,
        "calibration": calib,
        "jobs": jobs_meta,
        "raw_measurements": raw_meas,
    }
    with open(raw_path, "w") as f:
        json.dump(raw, f, default=str)
    return raw_path


def write_processed_txt(stem: str, stream: str) -> str:
    proc_path = stem + "_processed.txt"
    with open(proc_path, "w") as f:
        f.write("bits:" + stream + "\n")
    return proc_path
