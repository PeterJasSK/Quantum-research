#!/usr/bin/env python3
"""
07 — Superdense Coding  (send 2 classical bits by transmitting 1 qubit)

THE IDEA
    Teleportation (lesson 04) moves a qubit's state using 2 classical bits.
    Superdense coding is the mirror image: using a pre-shared Bell pair, Alice
    packs TWO classical bits into ONE qubit and sends only that qubit to Bob.
    It's the textbook proof that entanglement doubles a channel's capacity.

THE PLAYERS
    A Bell pair is shared ahead of time: Alice holds q0, Bob holds q1.

HOW IT WORKS
    Alice encodes her 2 bits by acting on HER qubit only:
        bits "00" -> do nothing (I)
        bits "01" -> X
        bits "10" -> Z
        bits "11" -> Z then X
    She ships q0 to Bob. Bob undoes the Bell entangling (CX then H) and
    measures both qubits — recovering Alice's 2 bits exactly.

THIS DEMO
    Alice sends the message "10". Bob should read "10" with certainty.

CIRCUIT
    q0: |0>─[H]─■─[ Alice's Z/X ]─■─[H]─[measure]
               │                 │
    q1: |0>────X─────────────────X──────[measure]
"""
from qiskit import QuantumCircuit
from _common import run_and_save

message = "10"                  # the 2 bits Alice wants to send

qc = QuantumCircuit(2, 2)

# shared Bell pair (created before Alice/Bob separate)
qc.h(0)
qc.cx(0, 1)

# --- Alice encodes 2 bits onto her qubit q0 ---
# (roles chosen so Bob's measured bitstring reads back exactly the message)
if message[0] == "1":
    qc.x(0)
if message[1] == "1":
    qc.z(0)

# --- Bob decodes (reverse the Bell circuit) ---
qc.cx(0, 1)
qc.h(0)
qc.measure([0, 1], [0, 1])

run_and_save(qc, "07_superdense_coding", "07 — Superdense Coding (send '10')",
             note="One transmitted qubit carries 2 classical bits: reads back 10.")
