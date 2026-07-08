#!/usr/bin/env python3
"""
qrng_bell_pairs.py   —  Strategy 2 of 2  (Bell-pair QRNG)

Builds as many Bell pairs |Phi+> = (|00>+|11>)/sqrt(2) as the chip's healthy,
low-error couplers allow (greedy lowest-error matching, no shared qubit).
1 random bit per pair per shot. Forbidden states 01/10 are handled by POLICY.

USAGE
    python qrng_bell_pairs.py [shots] [backend]
      shots   : how many shots to run. If omitted, uses the number needed for ~1M bits.
      backend : e.g. ibm_fez. If omitted, auto-picks the least-busy Heron r2.

OUTPUT  (two timestamped files in OUTPUT_DIR/)
    bell_<backend>_<YYYYMMDD-HHMMSS>_raw.json       full IBM result + all metadata
    bell_<backend>_<YYYYMMDD-HHMMSS>_processed.txt  "bits:1010..."
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
STRATEGY = "bell"
TARGET_BITS = 1_000_000
SHOTS_PER_JOB = 50_000
OUTPUT_DIR = "qrng_output"
BACKEND_NAME = None
HERON_R2_CANDIDATES = ["ibm_kingston", "ibm_fez", "ibm_marrakesh"]
POLICY = "discard"               # "include" (01->1,10->0) or "discard"
PAYG_USD_PER_SEC = 1.60

MAX_READOUT_ERROR = 0.05
MAX_SX_ERROR      = 1e-3
MAX_CZ_ERROR      = 0.02
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


def cz_error(props, a, b):
    for pair in ([a, b], [b, a]):
        try:
            return props.gate_error("cz", pair)
        except Exception:
            continue
    return None


def select_pairs(backend):
    props = backend.properties()
    good = {q for q in range(backend.num_qubits) if qubit_is_good(props, q)}
    print(f"Healthy qubits : {len(good)} / {backend.num_qubits}")

    seen, cand = set(), []
    for a, b in backend.coupling_map.get_edges():
        key = frozenset((a, b))
        if key in seen or a not in good or b not in good:
            continue
        seen.add(key)
        e = cz_error(props, a, b)
        if e is not None and e <= MAX_CZ_ERROR:
            cand.append((e, a, b))

    cand.sort()
    used, pairs = set(), []
    for e, a, b in cand:
        if a not in used and b not in used:
            pairs.append((a, b))
            used.update((a, b))
    print(f"Bell pairs     : {len(pairs)}  (from {len(cand)} healthy couplers)")
    return pairs


def build_circuit(pairs):
    n = 2 * len(pairs)
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    for k in range(len(pairs)):
        ctrl, targ = 2 * k, 2 * k + 1
        qc.h(ctrl)
        qc.cx(ctrl, targ)
    qc.measure(qr, cr)
    layout = [q for pr in pairs for q in pr]
    return qc, layout


def process(bitstrings, n_pairs, policy):
    """Decode shots into bits. Returns (stream, forbidden, total_pairs)."""
    bits, forbidden, total = [], 0, 0
    for s in bitstrings:
        r = s[::-1]
        for k in range(n_pairs):
            o = r[2 * k] + r[2 * k + 1]
            total += 1
            if o == "00":
                bits.append("0")
            elif o == "11":
                bits.append("1")
            else:
                forbidden += 1
                if policy == "include":
                    bits.append("1" if o == "01" else "0")
                # discard policy contributes nothing
    return "".join(bits), forbidden, total


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

    pairs = select_pairs(backend)
    if not pairs:
        print("No healthy couplers — try another backend."); return

    # include policy => exactly 1 bit per pair per shot
    bits_per_shot = len(pairs)
    shots_for_1M = math.ceil(TARGET_BITS / bits_per_shot)
    print(f"Bits/shot = {bits_per_shot}  ->  BELL needs {shots_for_1M:,} shots "
          f"for {TARGET_BITS:,} bits  (policy={POLICY})")

    shots = shots_arg if shots_arg else shots_for_1M
    print(f"Running {shots:,} shots ...")

    qc, layout = build_circuit(pairs)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                      initial_layout=layout)
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

    stream, forbidden, pair_total = process(raw_meas, len(pairs), POLICY)
    nbits = len(stream)
    ones = stream.count("1")
    bias = abs(ones / nbits - 0.5) if nbits else 0.0
    forbidden_rate = forbidden / pair_total if pair_total else 0.0
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
            "policy": POLICY, "shots": shots, "bits_per_shot": bits_per_shot,
            "pairs_used": pairs, "n_pairs_used": len(pairs),
            "total_bits": nbits, "bias": bias,
            "forbidden": forbidden, "forbidden_rate": forbidden_rate,
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
    print(f"Forbidden 01/10: {forbidden_rate*100:.2f} %")
    print(f"QPU seconds    : {total_qs:.2f}   (~${usd:.2f} PAYG; free on Open plan)")
    print(f"Shots for 1M   : {shots_for_1M:,}")
    print(f"Raw       -> {raw_path}")
    print(f"Processed -> {proc_path}")


if __name__ == "__main__":
    main()