"""P1 quantum_grover — Dürr–Høyer query count over the n! order space (AC-T1.4).

Ordering problem: query-count scaling IS the theorem; no statevector demo (OQ-5).

Run: python -m problems.p1_betweenness.quantum_grover --n 6 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p1_betweenness import instance

if __name__ == "__main__":
    _drivers.quantum_main(instance)
