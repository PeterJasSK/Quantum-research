#!/usr/bin/env python3
"""
05 — Deutsch–Jozsa  (first algorithm with a quantum speedup)

THE PROBLEM
    You are given a black-box function f on n input bits that is PROMISED to
    be either:
        constant  — same output (all 0 or all 1) for every input, or
        balanced  — output 0 for exactly half the inputs and 1 for the rest.
    Question: which one is it?

    Classically, in the worst case you must test just over half the inputs
    (2^(n-1) + 1 of them) to be sure. Deutsch–Jozsa answers it with a SINGLE
    query to the function. Exponential separation for this promise problem.

THE TRICK
    Put all inputs into superposition with H gates, run f once inside a
    "phase oracle", then H again. Interference makes the answer readable in
    one shot:
        measure all-zeros ("000...")  -> f is CONSTANT
        measure anything else         -> f is BALANCED

    Here we build a BALANCED oracle for n=3 (f(x) = x0 XOR x1 XOR x2), so we
    expect a non-zero string with certainty.

CIRCUIT (n input qubits + 1 ancilla in |->)
    inputs: H ... [oracle] ... H  measure
    ancilla: X,H (kick-back phase)
"""
from qiskit import QuantumCircuit
from _common import run_and_save

n = 3
qc = QuantumCircuit(n + 1, n)

# ancilla (last qubit) prepared in |-> so the oracle "kicks back" a phase
qc.x(n)
qc.h(n)

# superpose all inputs
for q in range(n):
    qc.h(q)

# balanced oracle: f(x) = x0 XOR x1 XOR x2  (CNOT each input onto ancilla)
for q in range(n):
    qc.cx(q, n)

# interfere back
for q in range(n):
    qc.h(q)

qc.measure(range(n), range(n))

run_and_save(qc, "05_deutsch_jozsa", "05 — Deutsch-Jozsa (balanced oracle)",
             note="Non-zero string with certainty => the function is BALANCED.")
