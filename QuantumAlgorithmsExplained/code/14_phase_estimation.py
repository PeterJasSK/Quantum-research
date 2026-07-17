#!/usr/bin/env python3
"""
14 — Quantum Phase Estimation (QPE)  (read the "phase" hidden in a gate)

WHAT IT DOES
    Many quantum gates act on their special "eigenstates" by only adding a
    phase:  U|psi> = e^{2*pi*i*phase} |psi>.  QPE estimates that unknown
    `phase` to n bits of precision. It is the engine inside Shor's factoring
    algorithm and quantum chemistry energy calculations.

THE SETUP HERE
    U = the T gate, whose eigenstate |1> satisfies  T|1> = e^{i*pi/4}|1>.
    That phase is pi/4 = 2*pi*(1/8), so phase = 1/8 = 0.001 in binary.
    With 3 counting qubits we can represent 1/8 exactly, so QPE should return
    the integer 1 (binary 001), meaning phase = 1/8.

HOW IT WORKS
    1. Counting register (3 qubits) into superposition with H.
    2. Controlled-U^(2^j): counting qubit j applies U to the eigenstate 2^j
       times, writing the phase into the counting qubits via kick-back.
    3. Inverse QFT turns those phases into a plain binary number.
    4. Measure the counting register -> the phase as an integer / 2^n.

EXPECT
    Counting register -> "001" (=1), i.e. estimated phase 1/8 = 0.125.
"""
import numpy as np
from qiskit import QuantumCircuit
from _common import run_and_save

n = 3                           # counting qubits -> 3 bits of precision
phase_gate_angle = np.pi / 4    # T gate: eigenvalue phase = 1/8

qc = QuantumCircuit(n + 1, n)
eig = n                         # eigenstate qubit index

# eigenstate |1> of the T gate
qc.x(eig)

# counting register into superposition
qc.h(range(n))

# controlled-U^(2^j): apply the phase 2^j times from counting qubit j
for j in range(n):
    qc.cp(phase_gate_angle * (2 ** j), j, eig)

# inverse QFT on the counting register (no final swaps here; instead we
# reverse the classical bit mapping below so the printed bitstring reads as
# the natural binary fraction 0.001 = 1/8)
for j in reversed(range(n)):
    for k in reversed(range(j + 1, n)):
        qc.cp(-np.pi / (2 ** (k - j)), k, j)
    qc.h(j)

# reversed mapping: qubit j -> classical bit (n-1-j)
qc.measure(range(n), list(reversed(range(n))))

run_and_save(qc, "14_phase_estimation", "14 — Quantum Phase Estimation (T gate)",
             note="Reads 001 = 1/8 = 0.125, the exact phase of the T gate.")
