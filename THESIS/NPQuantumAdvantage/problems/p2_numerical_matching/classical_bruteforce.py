"""P2 classical_bruteforce — exhaustive over all n! assignments (AC-T1.3).

Run: python -m problems.p2_numerical_matching.classical_bruteforce --n 6 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p2_numerical_matching import instance

if __name__ == "__main__":
    _drivers.classical_main(instance)
