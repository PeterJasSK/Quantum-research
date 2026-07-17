#!/usr/bin/env python3
"""
02 — Bell State  (entanglement of two qubits)

THE IDEA
    Entanglement links two qubits so their measurements are correlated no
    matter how far apart they are. The Bell state |Phi+> is:
        (|00> + |11>) / sqrt(2)
    You never see 01 or 10 — the two qubits always agree. This "spooky"
    correlation is the raw resource behind teleportation and many protocols.

HOW TO BUILD IT
    1. H on qubit 0  -> (|0>+|1>)/sqrt2 on q0, q1 still |0>
    2. CNOT(0->1)    -> flips q1 only when q0 is 1, linking them

CIRCUIT (2 qubits)
    q0: |0> --[H]--*--[measure]
                   |
    q1: |0> -------X--[measure]

EXPECT
    ~50% "00" and ~50% "11", almost never "01" or "10".
"""
from qiskit import QuantumCircuit
from _common import run_and_save

qc = QuantumCircuit(2, 2)
qc.h(0)                 # superpose the control qubit
qc.cx(0, 1)             # entangle: copy q0's "flip" onto q1
qc.measure([0, 1], [0, 1])

run_and_save(qc, "02_bell_state", "02 — Bell State (entanglement)",
             note="Qubits always agree: only 00 and 11 appear.")
