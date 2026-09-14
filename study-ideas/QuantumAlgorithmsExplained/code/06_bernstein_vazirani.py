#!/usr/bin/env python3
"""
06 — Bernstein–Vazirani  (find a hidden bitstring in ONE query)

THE PROBLEM
    A black box computes  f(x) = s . x (mod 2)  = dot product of your input x
    with a SECRET bitstring s. Find s.

    Classically you need n queries: feed 100..0, 010..0, ... to read s one bit
    at a time. Quantumly, ONE query reveals all of s at once.

THE TRICK
    Same "phase kick-back" idea as Deutsch–Jozsa. Superpose all inputs, apply
    the oracle (a CNOT from input qubit i to the ancilla wherever s_i = 1),
    then H again. The interference deposits s directly into the measurement.

    Here the secret is s = 1011 (read right-to-left as qubits q0..q3).

EXPECT
    Measuring the input register returns the secret string with certainty.
"""
from qiskit import QuantumCircuit
from _common import run_and_save

secret = "1011"                 # the hidden string we will recover
n = len(secret)

qc = QuantumCircuit(n + 1, n)

# ancilla in |->
qc.x(n)
qc.h(n)

# superpose inputs
for q in range(n):
    qc.h(q)

# oracle f(x)=s.x : CNOT input->ancilla where the secret bit is 1
# secret[::-1] so bit i lines up with qubit i
for i, bit in enumerate(secret[::-1]):
    if bit == "1":
        qc.cx(i, n)

# interfere
for q in range(n):
    qc.h(q)

qc.measure(range(n), range(n))

run_and_save(qc, "06_bernstein_vazirani", "06 — Bernstein-Vazirani (secret=1011)",
             note="Single query returns the hidden string 1011 with certainty.")
