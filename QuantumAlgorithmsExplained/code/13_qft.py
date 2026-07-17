#!/usr/bin/env python3
"""
13 — Quantum Fourier Transform (QFT)  (the workhorse behind Shor & phase estimation)

WHAT IT IS
    The QFT is the quantum version of the discrete Fourier transform. It maps
    amplitudes into the "frequency" domain and is the key subroutine inside
    phase estimation and Shor's factoring algorithm. On n qubits it needs only
    ~n^2 gates, versus n*2^n operations for the classical FFT on the same
    amplitudes — an exponential saving in gate count.

    Measuring right after a QFT just gives noise, so instead we demonstrate the
    two properties that make it useful:
      * it is a REAL unitary transform (built from H + controlled phase gates),
      * it is perfectly INVERTIBLE (QFT then inverse-QFT = identity).

THIS DEMO  (round trip)
    Encode the number 5 = binary 101 into 3 qubits, apply QFT, then inverse
    QFT, and measure. If our QFT is correct the value comes back untouched.

EXPECT
    Measuring -> "101" with certainty (5 recovered).
"""
import numpy as np
from qiskit import QuantumCircuit
from _common import run_and_save

n = 3


def qft(circ, qubits):
    """Textbook QFT: H then controlled phase rotations, on the given qubits."""
    m = len(qubits)
    for j in range(m):
        circ.h(qubits[j])
        for k in range(j + 1, m):
            angle = np.pi / (2 ** (k - j))
            circ.cp(angle, qubits[k], qubits[j])
    # reverse the qubit order (standard QFT convention)
    for i in range(m // 2):
        circ.swap(qubits[i], qubits[m - 1 - i])


def iqft(circ, qubits):
    """Inverse QFT = mirror image with negated phases."""
    m = len(qubits)
    for i in range(m // 2):
        circ.swap(qubits[i], qubits[m - 1 - i])
    for j in reversed(range(m)):
        for k in reversed(range(j + 1, m)):
            angle = -np.pi / (2 ** (k - j))
            circ.cp(angle, qubits[k], qubits[j])
        circ.h(qubits[j])


qc = QuantumCircuit(n, n)

# encode 5 = 101  ->  set q0 and q2
qc.x(0)
qc.x(2)

qc.barrier()
qft(qc, list(range(n)))         # into "frequency" domain
qc.barrier()
iqft(qc, list(range(n)))        # back again
qc.barrier()

qc.measure(range(n), range(n))

run_and_save(qc, "13_qft", "13 — QFT round trip (encode 5, QFT, inverse QFT)",
             note="QFT then inverse-QFT recovers the input 101 exactly.")
