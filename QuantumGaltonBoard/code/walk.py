#!/usr/bin/env python3
"""
walk.py — Quantum Galton Board: the frozen discrete-time quantum-walk builder.

`build_walk(steps, coin, encoding)` is P2's single circuit builder (epic §4);
every arm in arms.py consumes its output unchanged (AC-2.1). It replaces P1's
2-bin placeholder (`galton.build_reference_walk`) with the real coin+shift DTQW
under the one-hot line encoding frozen in walk_spec.py (OQ-1).

Construction — the incremental Galton frame (OQ-2.3)
----------------------------------------------------
Register: coin = qubit 0; position bins 0..n = qubits 1..n+1 (one-hot: exactly
one position qubit carries the walker per basis component). This is the contract
`walk_spec.decode_counts` decodes (`walk_spec.py:56`) and must not drift.

A standard line DTQW shifts position by +/-1 each step and would need 2n+1 bins.
We instead work in the Galton-board frame where the bin index counts *right*
moves: at step k the walker over bins 0..k represents positions 2*j-k, so a
right move (coin |1>) is `j -> j+1` and a left move (coin |0>) is `j -> j`
(the position still drops by 1 because the frame's origin shifts with k). At the
final step this is exactly `bin_to_position = 2*j - n` (walk_spec.py:34). This
frame is a shear of the textbook Hadamard walk, so the measured position
histogram equals the analytic walk to machine precision — verified in
walk_check.py (TV < 1e-6, AC-2.2) against an independent position-space
recursion. Because at step k the walker never occupies a bin above k, the
top-down CSWAP ladder never pushes amplitude past bin n: no boundary truncation,
probability is conserved (OQ-2.3 adequacy).

Per step (repeated `steps` times):
  1. COIN  : H on the coin qubit (fixed Hadamard, OQ-4).
  2. SHIFT : coin-controlled increment of the one-hot walker — a top-down ladder
             of CSWAP(coin, bin j, bin j+1) that moves the excitation one bin up
             when the coin is |1> and leaves it in place when the coin is |0>.
             Top-down (high j first) so each excitation advances exactly one bin.

The walker starts localised at bin 0 (X on qubit 1) with the coin in the
symmetric state (|0> + i|1>)/sqrt(2) (H then S), the canonical initial coin that
yields the symmetric twin-horn Hadamard walk.

Frozen at P2 and consumed by P3 (metrics) and P4 (sweep). Only `"hadamard"` /
`"one_hot_line"` are accepted in v1 (OQ-4 / OQ-1); other values raise
NotImplementedError (biased/DFT coins are P6 future work).
"""

from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister

import pipeline


def build_walk(steps: int, coin: str = "hadamard",
               encoding: str = "one_hot_line") -> QuantumCircuit:
    """Build the `steps`-step one-hot-line Hadamard DTQW on `steps + 2` qubits.

    Returns a QuantumCircuit with a QuantumRegister "q" (coin at index 0,
    position bins 0..n at indices 1..n+1), a ClassicalRegister "c" (via
    pipeline.classical_register, epic §3.3), and a final measure(qr, cr). The
    ideal position histogram of this circuit equals the analytic Hadamard walk
    to TOL (AC-2.2, checked offline in walk_check.py).
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if coin != "hadamard":
        raise NotImplementedError(
            f"build_walk v1 supports only the Hadamard coin (OQ-4); got {coin!r}")
    if encoding != "one_hot_line":
        raise NotImplementedError(
            f"build_walk v1 supports only one_hot_line (OQ-1); got {encoding!r}")

    n = steps
    n_qubits = n + 2
    qr = QuantumRegister(n_qubits, "q")
    cr = pipeline.classical_register(n_qubits)   # named "c" (epic §3.3 / A.2)
    qc = QuantumCircuit(qr, cr)

    coin_q = 0
    bin0 = 1                       # position bin 0 -> qubit index 1

    # localise the walker at bin 0 and prepare the symmetric coin (|0>+i|1>)/sqrt2
    qc.x(qr[bin0])
    qc.h(qr[coin_q])
    qc.s(qr[coin_q])

    for k in range(n):
        qc.h(qr[coin_q])
        # coin-controlled increment: top-down CSWAP ladder over the reachable
        # bins. After k steps the walker occupies bins 0..k, so ladder j = k..0
        # covers every occupied bin and pushes at most to bin k+1 (<= n): no
        # amplitude is lost off the top of the register (OQ-2.3).
        for j in range(min(k, n - 1), -1, -1):
            qc.cswap(qr[coin_q], qr[bin0 + j], qr[bin0 + j + 1])

    qc.measure(qr, cr)
    return qc
