#!/usr/bin/env python3
"""
12 — Grover's Search  (find a needle in an unsorted haystack, quadratically faster)

THE PROBLEM
    You have an unstructured search space of N = 2^n items and a way to
    recognise the one you want (an oracle that says "yes/no"). Find it.

    Classically you check items one by one: ~N/2 tries on average, N worst
    case. Grover finds it in about sqrt(N) tries — a quadratic speedup. For
    huge N that is enormous.

THE TRICK  (amplitude amplification)
    Start in equal superposition of all items. Repeat ~ (pi/4)*sqrt(N) times:
        1. ORACLE flips the sign (phase) of the target item only.
        2. DIFFUSER reflects all amplitudes about their average.
    Each round rotates probability toward the target. After the right number
    of rounds, measuring almost always yields the answer.

THIS DEMO
    n = 3  (N = 8 items). Target = "101". Optimal rounds = floor(pi/4*sqrt(8))
    = 2. Expect "101" with high probability (~95%+).
"""
import numpy as np
from qiskit import QuantumCircuit
from _common import run_and_save

n = 3
target = "101"                  # measured as q2 q1 q0  (left to right)

qc = QuantumCircuit(n, n)


def ccz(circ):
    """Phase-flip the all-ones state |111> (CCZ on 3 qubits)."""
    circ.h(2)
    circ.ccx(0, 1, 2)
    circ.h(2)


def oracle(circ):
    # turn the target into all-ones by X'ing the qubits that should be 0,
    # phase-flip |111>, then undo the X's -> only the target got flipped
    for i, bit in enumerate(reversed(target)):   # i = qubit index
        if bit == "0":
            circ.x(i)
    ccz(circ)
    for i, bit in enumerate(reversed(target)):
        if bit == "0":
            circ.x(i)


def diffuser(circ):
    circ.h(range(n)); circ.x(range(n))
    ccz(circ)
    circ.x(range(n)); circ.h(range(n))


# equal superposition over all 8 items
qc.h(range(n))

rounds = int(np.floor(np.pi / 4 * np.sqrt(2 ** n)))   # = 2
for _ in range(rounds):
    oracle(qc)
    diffuser(qc)

qc.measure(range(n), range(n))

run_and_save(qc, "12_grover", "12 — Grover's Search (target=101)",
             note=f"{rounds} rounds amplify the target; 101 dominates the histogram.")
