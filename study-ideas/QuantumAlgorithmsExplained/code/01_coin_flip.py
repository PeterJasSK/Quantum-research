#!/usr/bin/env python3
"""
01 — Quantum Coin Flip  (superposition with one Hadamard gate)

THE IDEA
    A classical bit is 0 or 1. A qubit can be in a "superposition" of both.
    The Hadamard gate H turns the definite state |0> into an equal mix:
        H|0> = (|0> + |1>) / sqrt(2)
    Measuring it collapses the mix to 0 or 1 with 50/50 probability.
    This is the "hello world" of quantum computing and a true random coin.

CIRCUIT (1 qubit)
    q: |0> --[H]--[measure]

EXPECT
    ~50% "0" and ~50% "1".
"""
from qiskit import QuantumCircuit
from _common import run_and_save

qc = QuantumCircuit(1, 1)
qc.h(0)                 # put the qubit into equal superposition
qc.measure(0, 0)        # collapse -> a random classical bit

run_and_save(qc, "01_coin_flip", "01 — Quantum Coin Flip",
             note="One H gate gives a fair 50/50 random bit.")
