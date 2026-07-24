#!/usr/bin/env python3
"""
stage_b_yield.py — S0.5 (AC-8, AC-9). Mid-circuit measure-reset depth-sweep
circuit: prepare (H) -> measure -> reset -> re-prepare -> measure, repeated
k times per qubit per shot, for k in the depth sweep (D5, D7).

Run the S0.3 measure-reset probe (calibration_snapshot.py) first to confirm
the device supports mid-circuit reset before running this sweep.

USAGE
    python stage_b_yield.py [shots] [backend] [--qubits q,q,...] [--depths k,k,...]
      shots   : shots per depth. If omitted, defaults to PROBE_DEFAULT_SHOTS.
      backend : e.g. ibm_fez. If omitted, auto-picks the least-busy Heron r2.
      --qubits: subset to sweep (default: 3 lowest-readout-error non-faulty
                qubits from the live snapshot, per Q5; the real top-5 subset
                is passed in after EPIC 1's Stage A evaluation).
      --depths: comma-separated k values (default "1,2,4,8", D5).

OUTPUT  (two timestamped files in qrng_output/)
    stageb_<backend>_<ts>_raw.json        per-depth raw results + (qubit, depth,
                                           creg-slot) layout + calibration snapshot
    stageb_<backend>_<ts>_processed.txt   "bits:1010..." (aggregate stream, D3)
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from calibration_snapshot import read_snapshot
from pipeline_common import OUTPUT_DIR, connect, run_sampler, timestamp, write_processed_txt

STRATEGY = "stageb"
DEFAULT_SHOTS = 200
DEFAULT_DEPTHS = [1, 2, 4, 8]
DEFAULT_SUBSET_SIZE = 3


def default_qubits(backend: Any, calib: dict[str, dict[str, float | None]]) -> list[int]:
    """Q5 default: 3 lowest-readout-error non-faulty qubits from the snapshot."""
    props = backend.properties()
    faulty = set(props.faulty_qubits())
    candidates = [
        (info["readout_error"], int(q))
        for q, info in calib.items()
        if int(q) not in faulty and isinstance(info.get("readout_error"), (int, float))
    ]
    candidates.sort()
    return [q for _, q in candidates[:DEFAULT_SUBSET_SIZE]]


def build_circuit(qubit_list: list[int], depth: int) -> QuantumCircuit:
    """Rep-major slot layout: slot = rep * n_qubits + qubit_index (interleaved per-qubit
    within each rep, AC-9)."""
    n = len(qubit_list)
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n * depth, "c")
    qc = QuantumCircuit(qr, cr)
    for rep in range(depth):
        for i in range(n):
            qc.h(i)
            qc.measure(i, rep * n + i)
            qc.reset(i)
    return qc


def process(bitstrings: list[str]) -> str:
    return "".join(s[::-1] for s in bitstrings)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shots", nargs="?", type=int, default=None)
    parser.add_argument("backend", nargs="?", type=str, default=None)
    parser.add_argument("--qubits", type=str, default=None)
    parser.add_argument("--depths", type=str, default="1,2,4,8")
    args = parser.parse_args()

    shots = args.shots if args.shots else DEFAULT_SHOTS
    depths = [int(k) for k in args.depths.split(",") if k]

    backend = connect(args.backend)
    print(f"Backend : {backend.name}  ({backend.num_qubits} qubits, {backend.processor_type})")

    calib = read_snapshot(backend)

    if args.qubits:
        qubit_list = [int(q) for q in args.qubits.split(",") if q]
    else:
        qubit_list = default_qubits(backend, calib)
    if not qubit_list:
        print("No qubits selected for Stage B sweep — pass --qubits explicitly.")
        return
    print(f"Qubit subset ({len(qubit_list)}): {qubit_list}")
    print(f"Depth sweep: {depths}  ->  bits/shot at max depth = "
          f"{len(qubit_list) * max(depths)} (D7)")

    ts = timestamp()
    stem = f"{OUTPUT_DIR}/{STRATEGY}_{backend.name}_{ts}"

    depth_results: list[dict[str, Any]] = []
    aggregate_stream_parts: list[str] = []
    total_qs_all = 0.0
    t0 = time.time()

    for depth in depths:
        print(f"\n--- depth k={depth} ---")
        qc = build_circuit(qubit_list, depth)
        pm = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                           initial_layout=qubit_list)
        isa = pm.run(qc)

        raw_meas, jobs_meta, total_qs = run_sampler(backend, isa, shots)
        total_qs_all += total_qs
        stream = process(raw_meas)
        aggregate_stream_parts.append(stream)

        depth_results.append({
            "depth": depth,
            "creg_size": len(qubit_list) * depth,
            "qubit_list": qubit_list,
            "slot_layout": "rep_major: slot = rep * n_qubits + qubit_index",
            "n_qubits": len(qubit_list),
            "shots": shots,
            "total_bits": len(stream),
            "quantum_seconds": total_qs,
            "jobs": jobs_meta,
            "raw_measurements": raw_meas,
        })

    wall = time.time() - t0
    aggregate_stream = "".join(aggregate_stream_parts)

    raw_path = stem + "_raw.json"
    with open(raw_path, "w") as f:
        json.dump({
            "run": {
                "strategy": STRATEGY, "backend": backend.name,
                "processor_type": str(backend.processor_type), "timestamp": ts,
                "qubit_list": qubit_list, "depths": depths, "shots_per_depth": shots,
                "quantum_seconds": total_qs_all, "wall_seconds": wall,
            },
            "calibration": calib,
            "depths": depth_results,
        }, f, default=str)
    proc_path = write_processed_txt(stem, aggregate_stream)

    print("\n--- DONE ---")
    print(f"Total bits (all depths) : {len(aggregate_stream):,}")
    print(f"QPU seconds              : {total_qs_all:.2f}")
    print(f"Raw       -> {raw_path}")
    print(f"Processed -> {proc_path}")


if __name__ == "__main__":
    main()
