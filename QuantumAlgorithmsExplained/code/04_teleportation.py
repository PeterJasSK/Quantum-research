#!/usr/bin/env python3
"""
04 — Quantum Teleportation  (moving a state with entanglement + 2 classical bits)

THE IDEA
    Teleportation moves the *state* of one qubit onto another qubit without
    physically sending the qubit — using a shared Bell pair plus two classical
    bits. It does NOT copy (the no-cloning theorem forbids that): the original
    is destroyed in the process.

    Players: q0 = the secret "message" qubit (Alice), q1+q2 = a Bell pair
    shared by Alice(q1) and Bob(q2).

STEPS
    1. Prepare a nontrivial secret state on q0 (here Ry(theta)|0>).
    2. Make the Bell pair on q1,q2.
    3. Alice entangles q0 with q1 and measures in the Bell basis
       (CX q0->q1, H q0).
    4. Bob corrects his qubit with an X and/or Z depending on Alice's 2 bits.
       Here we use the "deferred measurement" trick: the corrections are done
       as quantum-controlled gates (CX q1->q2, CZ q0->q2) so the whole thing
       stays a clean circuit the simulator can run.

HOW WE VERIFY
    If Bob's qubit q2 really became the secret state, then undoing the prep
    (Ry(-theta)) on q2 must send it back to |0>. So a correct teleport gives
    q2 = "0" essentially 100% of the time.

EXPECT
    Measuring q2 -> ~100% "0"  (proof the state arrived intact).
"""
import numpy as np
from qiskit import QuantumCircuit
from _common import run_and_save

theta = 2 * np.pi / 3          # the secret angle defining q0's state

qc = QuantumCircuit(3, 1)      # measure only Bob's qubit (q2)

# 1. secret message state on q0
qc.ry(theta, 0)

# 2. Bell pair on q1,q2
qc.h(1)
qc.cx(1, 2)

# 3. Alice's Bell-basis measurement (as gates)
qc.cx(0, 1)
qc.h(0)

# 4. Bob's corrections (deferred = quantum-controlled)
qc.cx(1, 2)                    # X correction
qc.cz(0, 2)                    # Z correction

# verify: undo the prep on q2 -> should land on |0>
qc.ry(-theta, 2)
qc.measure(2, 0)

run_and_save(qc, "04_teleportation", "04 — Quantum Teleportation",
             note="q2 returns to 0 ~100% -> the secret state arrived intact.")
