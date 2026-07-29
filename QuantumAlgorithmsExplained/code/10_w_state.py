#!/usr/bin/env python3
"""
10 — W State  (a different, more robust flavour of entanglement)

THE IDEA
    Lesson 03's GHZ state (|000>+|111>) is "all or nothing" — measure one
    qubit and the whole state collapses. The W state is the other famous
    3-qubit entangled class:
        |W> = (|001> + |010> + |100>) / sqrt(3)
    exactly ONE qubit is |1>, but which one is undecided. Its key property:
    if you lose (trace out) one qubit, the other two STAY entangled. That
    robustness makes W states useful for quantum memory and networking.

    GHZ and W cannot be turned into each other by local operations — they are
    genuinely different kinds of 3-way entanglement.

HOW TO BUILD IT
    Put the single excitation on q0, then use controlled Ry rotations to
    "share" it down the chain with exactly the right amplitudes so all three
    positions end up equally likely.

THIS DEMO
    Expect measuring -> "001", "010", "100" each about 1/3, and NOTHING else.
"""
import numpy as np
from qiskit import QuantumCircuit
from _common import run_and_save

n = 3
qc = QuantumCircuit(n, n)

# --- W-state preparation: controlled-Ry ladder ---
qc.x(0)                         # one excitation to start
for i in range(1, n):
    theta = 2 * np.arccos(np.sqrt(1 / (n - i + 1)))
    qc.cry(theta, i - 1, i)     # split amplitude onto the next qubit
    qc.cx(i, i - 1)             # move the excitation across

qc.measure(range(n), range(n))

run_and_save(qc, "10_w_state", "10 — W State (3-qubit, single excitation)",
             note="Only 001/010/100 appear, each ~1/3: one shared excitation.")

# --- Run on real quantum hardware instead (Quantum Inspire 2) ---------------
# The call above runs on the LOCAL ideal simulator (free, offline, no noise).
# To run the SAME circuit on Quantum Inspire's cloud, log in once with
#     qi login              (see ../../quantumCredentialsApi.py)
# and install the plugin:
#     pip install qiskit-quantuminspire
# then comment out the run_and_save call above and uncomment the block below:
#
# from _common import run_live_and_save
# run_live_and_save(qc, "10_w_state", "10 — W State (3-qubit, single excitation)",
#                   backend_name="QX emulator")   # QI cloud simulator, no queue
#                   # backend_name="Starmon-7"    # real superconducting hardware
#                   # backend_name="Spin-2+"      # real spin-qubit hardware
