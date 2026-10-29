"""Spot-checked CHSH rounds on Aer (target #4). The only C module that imports qiskit.

One shot = one round. Each round is a hidden test round with probability q (uniform settings
(x, y) ∈ {0,1}²) or a generation round at the fixed setting (0, 0). The 4 setting circuits run
once each with shots = number of rounds at that setting and memory=True; per-shot outcomes are
then put back into round order. Circuits are transpiled to FakeMarrakesh in both sim modes.

|Φ⁺⟩, measurement angle θ in the X–Z plane (ry(−θ) then Z): E(θa, θb) = cos(θa − θb).
Alice θ ∈ {0, π/2}, Bob θ ∈ {π/4, −π/4} ⇒ ideal S = 2√2. `classical=True` measures every setting
in Z (S = 2 ideally) and exists only to exercise the fail path.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit

from C_certificate.src.entropy import SETTINGS
from shared.simbackend import circuit_hash, make_simulator, transpile_heron

ALICE = (0.0, math.pi / 2)
BOB = (math.pi / 4, -math.pi / 4)


def setting_circuit(x: int, y: int, classical: bool = False) -> QuantumCircuit:
    qc = QuantumCircuit(2, 2, name=f"chsh_{x}{y}{'_classical' if classical else ''}")
    qc.h(0)
    qc.cx(0, 1)
    if not classical:
        qc.ry(-ALICE[x], 0)
        qc.ry(-BOB[y], 1)
    qc.measure([0, 1], [0, 1])
    return qc


def make_schedule(n: int, q: float, gen: np.random.Generator) -> dict:
    """Hidden test-round mask + settings; generation rounds sit at (0, 0)."""
    test = (gen.random(n) < q).astype(np.uint8)
    x = np.where(test == 1, gen.integers(0, 2, n), 0).astype(np.uint8)
    y = np.where(test == 1, gen.integers(0, 2, n), 0).astype(np.uint8)
    return {"test": test, "x": x, "y": y}


def run_rounds(mode: str, schedule: dict, base_seed: int, classical: bool = False) -> dict:
    """Run the schedule. Setting k (00, 01, 10, 11) uses Aer seed base_seed + k and transpile seed base_seed.

    Returns a, b (uint8 per round), the 4 transpiled circuit hashes, and counts keyed "xy ab"
    (test and generation rounds pooled).
    """
    x, y = schedule["x"], schedule["y"]
    a = np.zeros(x.size, dtype=np.uint8)
    b = np.zeros(x.size, dtype=np.uint8)
    hashes, counts = [], {}
    for k, (sx, sy) in enumerate(SETTINGS):
        tqc = transpile_heron(setting_circuit(sx, sy, classical), seed=base_seed)
        hashes.append(circuit_hash(tqc))
        idx = np.flatnonzero((x == sx) & (y == sy))
        if idx.size == 0:
            continue
        memory = make_simulator(mode, seed=base_seed + k).run(tqc, shots=int(idx.size), memory=True) \
            .result().get_memory()
        bits = np.array([[int(s[-1]), int(s[-2])] for s in memory], dtype=np.uint8)  # clbit 0 is rightmost
        a[idx], b[idx] = bits[:, 0], bits[:, 1]
        for (ai, bi), c in zip(*np.unique(bits, axis=0, return_counts=True)):
            counts[f"{sx}{sy} {ai}{bi}"] = int(c)
    return {"a": a, "b": b, "circuit_hashes": hashes, "counts": dict(sorted(counts.items()))}
