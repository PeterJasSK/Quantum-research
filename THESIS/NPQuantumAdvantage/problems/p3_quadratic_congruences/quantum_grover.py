"""P3 quantum_grover — Grover/Dürr–Høyer query count over the 2^n x-space (AC-T1.4).

Subset problem: `--statevector` runs a real small-n Aer amplification demo of the
solution state above the 1/2^n floor. Note (see verdict.md): the genuine quantum
win for this problem is Shor's factoring, not Grover.

Run: python -m problems.p3_quadratic_congruences.quantum_grover --n 10 --seed 7 --statevector
"""
from __future__ import annotations

from problems import _drivers
from problems.p3_quadratic_congruences import instance

if __name__ == "__main__":
    _drivers.quantum_main(instance)
