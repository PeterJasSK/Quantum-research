"""P3 classical_bruteforce — exhaustive over all 2^n values of x (AC-T1.3).

Run: python -m problems.p3_quadratic_congruences.classical_bruteforce --n 10 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p3_quadratic_congruences import instance

if __name__ == "__main__":
    _drivers.classical_main(instance)
