#!/usr/bin/env python3
"""
stage_a_selection.py — S0.4 (AC-6, AC-7). Forks
ErrorDetectionVSRawBits/qrng_noise_hadamard.py: H on every selected qubit
(whole chip by default), measure. This is also the naive baseline
(1 bit/qubit/shot, no selection) when --select all is used (D7).

USAGE
    python stage_a_selection.py [shots] [backend] [--select all|good|list:q,q,...]
      shots   : how many shots to run. If omitted, uses the number needed for ~1M bits.
      backend : e.g. ibm_fez. If omitted, auto-picks the least-busy Heron r2.
      --select: qubit set (D2). Default "all".

OUTPUT  (two timestamped files in qrng_output/)
    stagea_<backend>_<ts>_raw.json        full IBM result + qubits_used + calibration snapshot
    stagea_<backend>_<ts>_processed.txt   "bits:1010..." (aggregate stream, D3)
"""

from __future__ import annotations

import argparse
import math
import time
from typing import Any

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from calibration_snapshot import read_snapshot
from pipeline_common import (
    OUTPUT_DIR, connect, run_sampler, timestamp, write_processed_txt, write_raw_json,
)

STRATEGY = "stagea"
TARGET_BITS = 1_000_000

MAX_READOUT_ERROR = 0.05
MAX_SX_ERROR = 1e-3
MIN_T1_US = 30.0
MIN_T2_US = 30.0


def qubit_is_good(props: Any, q: int) -> bool:
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


def select_qubits(backend: Any, mode: str) -> list[int]:
    """D2: 'all' (default, baseline) / 'good' (qubit_is_good thresholds) / 'list:q,q,...'."""
    props = backend.properties()
    faulty = set(props.faulty_qubits())

    if mode == "all":
        selected = [q for q in range(backend.num_qubits) if q not in faulty]
    elif mode == "good":
        selected = [q for q in range(backend.num_qubits) if qubit_is_good(props, q)]
    elif mode.startswith("list:"):
        requested = [int(q) for q in mode[len("list:"):].split(",") if q]
        selected = [q for q in requested if q not in faulty]
        dropped = [q for q in requested if q in faulty]
        if dropped:
            print(f"Dropping faulty qubits from requested list: {dropped}")
    else:
        raise ValueError(f"Unknown --select mode: {mode!r}")

    print(f"Selected qubits ({mode}): {len(selected)} / {backend.num_qubits}")
    return selected


def build_circuit(selected: list[int]) -> QuantumCircuit:
    n = len(selected)
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(qr)
    qc.measure(qr, cr)
    return qc


def process(bitstrings: list[str]) -> str:
    """One bit per qubit per shot. Reverse so index i == classical bit i."""
    return "".join(s[::-1] for s in bitstrings)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shots", nargs="?", type=int, default=None)
    parser.add_argument("backend", nargs="?", type=str, default=None)
    parser.add_argument("--select", type=str, default="all")
    args = parser.parse_args()

    backend = connect(args.backend)
    print(f"Backend : {backend.name}  ({backend.num_qubits} qubits, {backend.processor_type})")

    selected = select_qubits(backend, args.select)
    if not selected:
        print("No qubits selected — try another mode or backend.")
        return
    bits_per_shot = len(selected)

    shots_for_1M = math.ceil(TARGET_BITS / bits_per_shot)
    print(f"Bits/shot = {bits_per_shot}  ->  needs {shots_for_1M:,} shots "
          f"for {TARGET_BITS:,} bits (D7: max parallel, Hadamard-only)")

    shots = args.shots if args.shots else shots_for_1M
    print(f"Running {shots:,} shots ...")

    calib = read_snapshot(backend)

    qc = build_circuit(selected)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                       initial_layout=selected)
    isa = pm.run(qc)

    t0 = time.time()
    raw_meas, jobs_meta, total_qs = run_sampler(backend, isa, shots)
    wall = time.time() - t0

    stream = process(raw_meas)
    nbits = len(stream)
    ones = stream.count("1")
    bias = abs(ones / nbits - 0.5) if nbits else 0.0

    ts = timestamp()
    stem = f"{OUTPUT_DIR}/{STRATEGY}_{backend.name}_{ts}"

    run_meta = {
        "strategy": STRATEGY, "backend": backend.name,
        "processor_type": str(backend.processor_type), "timestamp": ts,
        "select_mode": args.select, "shots": shots, "bits_per_shot": bits_per_shot,
        "qubits_used": selected, "n_qubits_used": len(selected),
        "total_bits": nbits, "bias": bias,
        "quantum_seconds": total_qs, "wall_seconds": wall,
        "shots_for_1M_bits": shots_for_1M,
    }
    raw_path = write_raw_json(stem, run_meta, jobs_meta, raw_meas, calib)
    proc_path = write_processed_txt(stem, stream)

    print("\n--- DONE ---")
    print(f"Bits           : {nbits:,}   bias {bias:.4f}")
    print(f"QPU seconds    : {total_qs:.2f}")
    print(f"Shots for 1M   : {shots_for_1M:,}")
    print(f"Raw       -> {raw_path}")
    print(f"Processed -> {proc_path}")


if __name__ == "__main__":
    main()
