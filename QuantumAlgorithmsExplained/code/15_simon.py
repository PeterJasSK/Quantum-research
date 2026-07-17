#!/usr/bin/env python3
"""
15 — Simon's Algorithm  (the first EXPONENTIAL quantum speedup)

THE PROBLEM
    A black box f is 2-to-1 with a hidden period s: f(x) = f(y) exactly when
    y = x XOR s. Find the secret string s.

    Classically you must keep evaluating f and wait for a collision
    (two inputs giving the same output). That takes about sqrt(2^n) = 2^(n/2)
    queries — exponential. Simon's algorithm needs only about n quantum
    queries, then a little linear algebra. This exponential gap is what
    inspired Shor's factoring algorithm.

HOW IT WORKS
    1. Two registers of n qubits: input + output.
    2. H on the input register, run the oracle once, H on the input again.
    3. Measuring the input register yields a random string z that is
       GUARANTEED to satisfy the equation  z . s = 0 (mod 2).
    4. Collect ~n independent such z, solve the linear system -> s.

THIS DEMO
    n = 2, secret period s = "11". Every measured z must satisfy z . s = 0,
    so the ONLY strings that can appear are "00" and "11" (00.11=0, 11.11=0).
    "01" and "10" are forbidden. From {11} we solve and recover s = 11.

EXPECT
    Input register -> only "00" and "11" (each ~50%). No "01"/"10".
"""
from qiskit import QuantumCircuit
from _common import run_and_save

n = 2
s = "11"                        # hidden period we will recover

qc = QuantumCircuit(2 * n, n)   # measure only the n input qubits

# superpose the input register
qc.h(range(n))
qc.barrier()

# ---- Simon oracle for period s ------------------------------------
# copy input -> output
for i in range(n):
    qc.cx(i, n + i)
# imprint the period: from the first set bit of s, XOR into every set position
s_bits = s[::-1]                # s_bits[i] is the bit for qubit i
first = s_bits.index("1")
for i in range(n):
    if s_bits[i] == "1":
        qc.cx(first, n + i)
qc.barrier()

# interfere the input register back
qc.h(range(n))
qc.measure(range(n), range(n))

run_and_save(qc, "15_simon", "15 — Simon's Algorithm (period s=11)",
             note="Only 00 and 11 appear (z.s=0). Solving gives s=11.")
