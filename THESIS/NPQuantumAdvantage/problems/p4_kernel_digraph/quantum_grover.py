"""P4 quantum_grover — Grover/Dürr–Høyer query count over the 2^n subset space (AC-T1.4).

Subset problem: `--statevector` runs a real small-n Aer amplification demo of the
kernel state(s) above the 1/2^n floor. The sparse/local QUBO makes P4 the best
hardware fit (deferred appendix).

Run: python -m problems.p4_kernel_digraph.quantum_grover --n 10 --seed 7 --statevector
"""
from __future__ import annotations

from problems import _drivers
from problems.p4_kernel_digraph import instance

if __name__ == "__main__":
    _drivers.quantum_main(instance)
