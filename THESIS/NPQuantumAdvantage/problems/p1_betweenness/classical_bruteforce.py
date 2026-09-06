"""P1 classical_bruteforce — exhaustive over all n! orders (AC-T1.3).

Run: python -m problems.p1_betweenness.classical_bruteforce --n 6 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p1_betweenness import instance

if __name__ == "__main__":
    _drivers.classical_main(instance)
