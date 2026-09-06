"""P4 classical_bruteforce — exhaustive over all 2^n subsets (AC-T1.3).

Run: python -m problems.p4_kernel_digraph.classical_bruteforce --n 10 --seed 7
"""
from __future__ import annotations

from problems import _drivers
from problems.p4_kernel_digraph import instance

if __name__ == "__main__":
    _drivers.classical_main(instance)
