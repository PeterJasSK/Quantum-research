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

# --- Run on real quantum hardware instead (Quantum Inspire 2) ---------------
# The call above runs on the LOCAL ideal simulator (free, offline, no noise).
# To run the SAME circuit on Quantum Inspire's cloud, log in once with
#     qi login              (see ../../quantumCredentialsApi.py)
# and install the plugin:
#     pip install qiskit-quantuminspire
# then comment out the run_and_save call above and uncomment the block below:
#
# from _common import run_live_and_save
# run_live_and_save(qc, "01_coin_flip", "01 — Quantum Coin Flip",
#                   backend_name="QX emulator")   # QI cloud simulator, no queue
#                   # backend_name="Starmon-7"    # real superconducting hardware
#                   # backend_name="Spin-2+"      # real spin-qubit hardware
