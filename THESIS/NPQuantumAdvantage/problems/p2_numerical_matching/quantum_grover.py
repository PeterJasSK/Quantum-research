"""P2 quantum_grover — Dürr–Høyer query count over the n! assignment space (AC-T1.4).

Ordering problem: the query-count scaling IS the theorem; no statevector demo
(permutation-Grover is out of scope, OQ-5).

Run: python -m problems.p2_numerical_matching.quantum_grover --n 6 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p2_numerical_matching import instance

if __name__ == "__main__":
    _drivers.quantum_main(instance)
