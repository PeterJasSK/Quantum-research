#!/usr/bin/env python3
"""
09 — Quantum Half-Adder  (reversible arithmetic + the Toffoli gate)

THE IDEA
    Real computation needs arithmetic. This lesson builds the simplest adder:
    a HALF-ADDER that adds two single bits a + b and outputs a 2-bit result
    (sum, carry). It introduces the **Toffoli / CCX** gate (controlled-
    controlled-NOT) — the reversible AND — which is a core building block of
    quantum oracles, including Grover's (lesson 12).

THE LOGIC
    sum   = a XOR b     -> two CNOTs onto a fresh "sum" qubit
    carry = a AND b     -> one Toffoli onto a fresh "carry" qubit

    Everything is reversible (no information is thrown away), which every
    quantum gate must be.

THIS DEMO
    Compute 1 + 1. Expect sum = 0, carry = 1  (binary 10 = decimal 2).

CIRCUIT (q0=a, q1=b, q2=sum, q3=carry)
    q0(a):    ─■────■──────
    q1(b):    ─│─■──■──────
    q2(sum):  ─X─X──│──[measure -> c0]
    q3(carry):─────CCX─[measure -> c1]
"""
from qiskit import QuantumCircuit
from _common import run_and_save

a, b = 1, 1                     # the two input bits we add

qc = QuantumCircuit(4, 2)       # q0=a q1=b q2=sum q3=carry ; c0=sum c1=carry

# load the inputs
if a:
    qc.x(0)
if b:
    qc.x(1)

# sum = a XOR b  (onto q2)
qc.cx(0, 2)
qc.cx(1, 2)

# carry = a AND b  (Toffoli onto q3)
qc.ccx(0, 1, 3)

qc.measure(2, 0)                # sum   -> classical bit 0
qc.measure(3, 1)                # carry -> classical bit 1

run_and_save(qc, "09_quantum_adder", "09 — Quantum Half-Adder (1 + 1)",
             note="Reads carry=1 sum=0 (bitstring '10' = 2): 1+1=2.")
