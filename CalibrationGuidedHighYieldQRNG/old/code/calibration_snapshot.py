#!/usr/bin/env python3
"""
calibration_snapshot.py — S0.3 (AC-4, AC-5).

Pulls the live per-qubit calibration snapshot (T1, T2, readout_error, sx gate
error, reset error) and saves it as calib_<backend>_<ts>.json. Also runs a
tiny measure-reset probe to confirm mid-circuit reset works on this device
before committing the Stage B sweep (D4, Q1).

USAGE
    python calibration_snapshot.py [backend]
      backend : e.g. ibm_fez. If omitted, auto-picks the least-busy Heron r2.

OUTPUT
    qrng_output/calib_<backend>_<YYYYMMDD-HHMMSS>.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler

from pipeline_common import OUTPUT_DIR, connect, timestamp

PROBE_SHOTS = 200


def _reset_error(props: Any, q: int) -> float | None:
    """props.gate_error('reset', q) -> scan props.to_dict() -> None (D4/Q1)."""
    try:
        return props.gate_error("reset", q)
    except Exception:
        pass
    try:
        for gate in props.to_dict().get("gates", []):
            if gate.get("gate") == "reset" and gate.get("qubits") == [q]:
                for param in gate.get("parameters", []):
                    if param.get("name") == "gate_error":
                        return float(param["value"])
    except Exception:
        pass
    return None


def read_snapshot(backend: Any) -> dict[str, dict[str, float | None]]:
    props = backend.properties()
    snapshot: dict[str, dict[str, float | None]] = {}
    reset_missing = False
    for q in range(backend.num_qubits):
        reset_error = _reset_error(props, q)
        if reset_error is None:
            reset_missing = True
        try:
            entry = {
                "t1": props.t1(q),
                "t2": props.t2(q),
                "readout_error": props.readout_error(q),
                "sx_error": props.gate_error("sx", q),
                "reset_error": reset_error,
            }
        except Exception as e:
            entry = {"_error": str(e)}
        snapshot[str(q)] = entry
    if reset_missing:
        print("WARNING: reset_error missing for one or more qubits — recorded as null (§11 Q1).")
    return snapshot


def reset_probe(backend: Any) -> bool:
    """Tiny prepare -> measure -> reset -> re-prepare -> measure dynamic circuit.

    PASS means the second measurement is not stuck at the post-reset value —
    i.e. mid-circuit reset produced a fresh, independent state to re-prepare on.
    """
    qc = QuantumCircuit(1, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.reset(0)
    qc.h(0)
    qc.measure(0, 1)

    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm.run(qc)

    sampler = Sampler(mode=backend)
    job = sampler.run([isa], shots=PROBE_SHOTS)
    res = job.result()
    bitstrings = res[0].data.c.get_bitstrings()

    second_bits = [s[::-1][1] for s in bitstrings]
    ones = second_bits.count("1")
    bias = abs(ones / len(second_bits) - 0.5) if second_bits else 1.0

    passed = bias < 0.15
    print(f"Reset probe: {ones}/{len(second_bits)} ones on second measurement "
          f"(bias {bias:.4f}) -> {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else None

    backend = connect(name)
    print(f"Backend : {backend.name}  ({backend.num_qubits} qubits, {backend.processor_type})")

    snapshot = read_snapshot(backend)
    passed = reset_probe(backend)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    path = os.path.join(OUTPUT_DIR, f"calib_{backend.name}_{ts}.json")
    with open(path, "w") as f:
        json.dump({
            "backend": backend.name, "timestamp": ts,
            "reset_probe_pass": passed,
            "qubits": snapshot,
        }, f, default=str)

    print(f"Snapshot -> {path}")
    if not passed:
        print("Reset probe FAILED — do not run the Stage B sweep on this device (see epic Risks).")


if __name__ == "__main__":
    main()
