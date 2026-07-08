#!/usr/bin/env python3
"""
qrng_noise_hadamard.py   —  Strategy 1 of 2  (all-Hadamard "system noise")

Puts an H on every healthy qubit and measures. 1 random bit per healthy qubit
per shot. Reads live calibration and drops dead / noisy qubits automatically.

USAGE
    python qrng_noise_hadamard.py [shots] [backend]
      shots   : how many shots to run. If omitted, uses the number needed for ~1M bits.
      backend : e.g. ibm_fez. If omitted, auto-picks the least-busy Heron r2.

OUTPUT  (two timestamped files in OUTPUT_DIR/)
    noise_<backend>_<YYYYMMDD-HHMMSS>_raw.json       full IBM result + all metadata
    noise_<backend>_<YYYYMMDD-HHMMSS>_processed.txt  "bits:1010..."
"""

import json
import math
import os
import sys
import time
from datetime import datetime

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ===========================================================================
# CONFIG
# ===========================================================================
STRATEGY = "noise"
TARGET_BITS = 1_000_000          # reference target for the "shots needed" calc
SHOTS_PER_JOB = 50_000           # jobs are chunked to this size
OUTPUT_DIR = "qrng_output"
BACKEND_NAME = None
HERON_R2_CANDIDATES = ["ibm_kingston", "ibm_fez", "ibm_marrakesh"]
PAYG_USD_PER_SEC = 1.60          # for the cost line; Open plan is free

MAX_READOUT_ERROR = 0.05
MAX_SX_ERROR      = 1e-3
MIN_T1_US         = 30.0
MIN_T2_US         = 30.0
# ===========================================================================


def connect(name):
    service = QiskitRuntimeService()
    if name:
        return service.backend(name)
    return service.least_busy(operational=True, simulator=False, min_num_qubits=100,
                              filters=lambda b: b.name in HERON_R2_CANDIDATES)


def qubit_is_good(props, q):
    try:
        if q in props.faulty_qubits():
            return False
        if props.readout_error(q) > MAX_READOUT_ERROR:
            return False
        if props.t1(q) * 1e6 < MIN_T1_US:
            return False
        if props.t2(q) * 1e6 < MIN_T2_US:
            return False
        if props.gate_error("sx", q) > MAX_SX_ERROR:
            return False
    except Exception:
        return False
    return True


def select_qubits(backend):
    props = backend.properties()
    good = [q for q in range(backend.num_qubits) if qubit_is_good(props, q)]
    print(f"Healthy qubits : {len(good)} / {backend.num_qubits}")
    return good


def build_circuit(good):
    n = len(good)
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(qr)
    qc.measure(qr, cr)
    return qc


def process(bitstrings):
    """One bit per qubit per shot. Reverse so index i == classical bit i."""
    return "".join(s[::-1] for s in bitstrings)


def qpu_seconds(job):
    try:
        return float(job.metrics()["usage"]["quantum_seconds"])
    except Exception:
        try:
            return float(job.usage())
        except Exception:
            return float("nan")


def _safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"_error": str(e)}


def main():
    shots_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    name = sys.argv[2] if len(sys.argv) > 2 else BACKEND_NAME

    backend = connect(name)
    print(f"Backend : {backend.name}  ({backend.num_qubits} qubits, {backend.processor_type})")

    good = select_qubits(backend)
    if not good:
        print("No healthy qubits — try another backend."); return
    bits_per_shot = len(good)

    shots_for_1M = math.ceil(TARGET_BITS / bits_per_shot)
    print(f"Bits/shot = {bits_per_shot}  ->  NOISE needs {shots_for_1M:,} shots "
          f"for {TARGET_BITS:,} bits")

    shots = shots_arg if shots_arg else shots_for_1M
    print(f"Running {shots:,} shots ...")

    qc = build_circuit(good)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                      initial_layout=good)
    isa = pm.run(qc)

    sampler = Sampler(mode=backend)
    raw_meas, jobs_meta, total_qs = [], [], 0.0
    t0, remaining, ci = time.time(), shots, 0
    while remaining > 0:
        chunk = min(SHOTS_PER_JOB, remaining); ci += 1
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

    stream = process(raw_meas)
    nbits = len(stream)
    ones = stream.count("1")
    bias = abs(ones / nbits - 0.5) if nbits else 0.0
    wall = time.time() - t0
    usd = total_qs * PAYG_USD_PER_SEC

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = os.path.join(OUTPUT_DIR, f"{STRATEGY}_{backend.name}_{ts}")
    raw_path, proc_path = stem + "_raw.json", stem + "_processed.txt"

    raw = {
        "run": {
            "strategy": STRATEGY, "backend": backend.name,
            "processor_type": str(backend.processor_type), "timestamp": ts,
            "shots": shots, "bits_per_shot": bits_per_shot,
            "qubits_used": good, "n_qubits_used": len(good),
            "total_bits": nbits, "bias": bias,
            "quantum_seconds": total_qs, "wall_seconds": wall,
            "payg_usd": usd, "shots_for_1M_bits": shots_for_1M,
        },
        "jobs": jobs_meta,
        "raw_measurements": raw_meas,     # exactly as IBM returned, one string per shot
    }
    with open(raw_path, "w") as f:
        json.dump(raw, f, default=str)
    with open(proc_path, "w") as f:
        f.write("bits:" + stream + "\n")

    print("\n--- DONE ---")
    print(f"Bits           : {nbits:,}   bias {bias:.4f}")
    print(f"QPU seconds    : {total_qs:.2f}   (~${usd:.2f} PAYG; free on Open plan)")
    print(f"Shots for 1M   : {shots_for_1M:,}")
    print(f"Raw       -> {raw_path}")
    print(f"Processed -> {proc_path}")


if __name__ == "__main__":
    main()