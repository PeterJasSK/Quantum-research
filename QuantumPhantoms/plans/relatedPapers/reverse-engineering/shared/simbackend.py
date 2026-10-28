"""Simulator factory: AerSimulator ideal and FakeMarrakesh (Heron r2) noise. Simulation only.

Both modes run circuits transpiled to the FakeMarrakesh target (heavy-hex, CZ basis), so gate
counts and depth are identical across modes and only the noise differs.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import uuid
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit, qasm3, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

REFERENCE_FAKE = "FakeMarrakesh"
SIM_LABELS = {
    "ideal": "simulated: ideal",
    "heron": "simulated: Heron-class noise (FakeMarrakesh)",
}


@lru_cache(maxsize=1)
def fake_backend() -> FakeMarrakesh:
    return FakeMarrakesh()


@lru_cache(maxsize=1)
def _noisy_sim() -> AerSimulator:
    return AerSimulator.from_backend(fake_backend())


def sim_label(mode: str) -> str:
    return SIM_LABELS[mode]


def make_simulator(mode: str, *, seed: int | None = None) -> AerSimulator:
    if mode == "ideal":
        sim = AerSimulator()
    elif mode == "heron":
        sim = _noisy_sim()
    else:
        raise ValueError(f"mode must be 'ideal' or 'heron', got {mode!r}")
    if seed is not None:
        sim.set_options(seed_simulator=seed)
    return sim


def transpile_heron(circ: QuantumCircuit, *, seed: int, optimization_level: int = 1) -> QuantumCircuit:
    return transpile(circ, backend=fake_backend(), optimization_level=optimization_level,
                     seed_transpiler=seed)


def circuit_hash(circ: QuantumCircuit) -> str:
    """sha256 of the OpenQASM 3 text (QPY bytes embed version metadata and are not stable)."""
    return hashlib.sha256(qasm3.dumps(circ).encode("utf-8")).hexdigest()


def run_counts(circ: QuantumCircuit, mode: str, shots: int, seed: int,
               job_id: str | None = None) -> tuple[dict, str, str]:
    """Transpile to FakeMarrakesh, run on the chosen simulator. Returns (counts, transpiled_hash, job_id)."""
    tqc = transpile_heron(circ, seed=seed)
    result = make_simulator(mode, seed=seed).run(tqc, shots=shots).result()
    return dict(result.get_counts()), circuit_hash(tqc), job_id or f"sim-{uuid.uuid4()}"


def calibration_snapshot() -> dict:
    b = fake_backend()
    props = Path(b.dirname) / b.props_filename
    return {
        "fake_backend": REFERENCE_FAKE,
        "qiskit_ibm_runtime_version": md.version("qiskit-ibm-runtime"),
        "props_sha256": hashlib.sha256(props.read_bytes()).hexdigest(),
        "last_update_date": json.loads(props.read_text())["last_update_date"],
    }
