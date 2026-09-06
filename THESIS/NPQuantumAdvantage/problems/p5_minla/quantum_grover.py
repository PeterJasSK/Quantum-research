"""P5 quantum_grover — Dürr–Høyer query count over the n! arrangement space (AC-T1.4).

Ordering problem: query-count scaling IS the theorem; no statevector demo (OQ-5).

Run: python -m problems.p5_minla.quantum_grover --n 7 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p5_minla import instance

if __name__ == "__main__":
    _drivers.quantum_main(instance)
