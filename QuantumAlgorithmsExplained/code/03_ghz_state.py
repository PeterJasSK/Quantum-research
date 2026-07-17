#!/usr/bin/env python3
"""
03 — GHZ State  (entangling three or more qubits)

THE IDEA
    The GHZ state generalises the Bell pair to N qubits:
        (|000> + |111>) / sqrt(2)
    All qubits are locked together — measure one and you instantly know the
    rest. GHZ states are used in quantum error correction, metrology and
    tests of quantum mechanics against "hidden variable" theories.

HOW TO BUILD IT
    H on q0, then a chain of CNOTs spreading the flip to every other qubit.

CIRCUIT (3 qubits)
    q0: |0> --[H]--*--*--[measure]
                   |  |
    q1: |0> -------X--|--[measure]
                      |
    q2: |0> ----------X--[measure]

EXPECT
    ~50% "000" and ~50% "111", nothing else.
"""
from qiskit import QuantumCircuit
from _common import run_and_save

N = 3
qc = QuantumCircuit(N, N)
qc.h(0)
for q in range(1, N):
    qc.cx(0, q)         # spread the entanglement from q0 to all others
qc.measure(range(N), range(N))

run_and_save(qc, "03_ghz_state", "03 — GHZ State (3-qubit entanglement)",
             note="All three qubits agree: only 000 and 111 appear.")
