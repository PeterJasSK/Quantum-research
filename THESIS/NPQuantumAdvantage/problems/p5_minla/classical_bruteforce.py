"""P5 classical_bruteforce — exhaustive over all n! arrangements (AC-T1.3).

Run: python -m problems.p5_minla.classical_bruteforce --n 7 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p5_minla import instance

if __name__ == "__main__":
    _drivers.classical_main(instance)
