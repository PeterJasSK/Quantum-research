#!/usr/bin/env python3
"""
analytics.py — Quantum Galton Board: the shared closed-form baselines (P3, epic §4).

Two closed-form ``{position: probability}`` distributions the three arms are
compared against, in the same signed-lattice frame the arms emit (positions
``-n..+n`` step 2, one-hot line encoding, OQ-1):

  analytic_hadamard_walk(steps)  — the ideal BALLISTIC reference: the symmetric
      Hadamard DTQW (coin (|0>+i|1>)/sqrt2, OQ-4). Same recursion carried locally
      by P2's walk_check.py (walk_check.py:37); P3 is now the canonical owner
      (OQ-3.6). metrics_check.py pins this against build_walk + Statevector to TOL,
      so both copies stay tied to the P2 physics.
  binomial_reference(steps)      — the classical DIFFUSIVE baseline: a fair-coin
      Galton board, B(n, 1/2), C(n, j)/2^n at position 2j - n. sigma^2 = n so the
      variance exponent a = 1 (diffusive).

Pure, no I/O, stdlib + numpy only (no new dependency; epic §9 / plan §4). Both
return sparse int-keyed histograms, so every metric in metrics.py consumes a
reference and a measured run identically.
"""

from __future__ import annotations

import math

import numpy as np


def analytic_hadamard_walk(steps: int) -> dict[int, float]:
    """Ideal ballistic reference: symmetric-coin Hadamard DTQW (§7).

    Textbook position-space line DTQW: positions -n..n, shift |x,0>->|x-1,0>,
    |x,1>->|x+1,1>, Hadamard coin each step, symmetric initial coin
    (|0>+i|1>)/sqrt2. Returns {position: probability} over the same-parity
    reachable positions -n..n (step 2). This mirrors walk_check.analytic_hadamard_walk
    (walk_check.py:37) verbatim so metrics_check.py can cross-check both against
    build_walk + Statevector.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps
    width = 2 * n + 1
    off = n
    amp = np.zeros((width, 2), dtype=complex)
    amp[off, 0] = 1.0 / np.sqrt(2)
    amp[off, 1] = 1j / np.sqrt(2)
    had = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    for _ in range(n):
        amp = amp @ had.T
        new = np.zeros_like(amp)
        new[:-1, 0] = amp[1:, 0]     # coin |0>: x -> x-1
        new[1:, 1] = amp[:-1, 1]     # coin |1>: x -> x+1
        amp = new
    prob = (np.abs(amp) ** 2).sum(axis=1)
    return {int(x): float(prob[off + x])
            for x in range(-n, n + 1) if (x + n) % 2 == 0}


def binomial_reference(steps: int) -> dict[int, float]:
    """Classical diffusive baseline: B(n, 1/2) in the signed-position frame (§7).

    p(bin j) = C(n, j) / 2^n at position 2j - n for j = 0..n. Exact via
    math.comb, then normalised (the C(n,j) already sum to 2^n, so normalisation
    is a defensive no-op that also absorbs float rounding). sigma^2 = n -> the
    variance growth exponent a = 1 (diffusive), the counterpoint to the walk's
    a = 2 (ballistic).
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps
    weights = {2 * j - n: math.comb(n, j) for j in range(n + 1)}
    total = float(sum(weights.values()))   # == 2**n
    return {pos: w / total for pos, w in weights.items()}


if __name__ == "__main__":
    # smoke: both baselines sum to 1 and sit in the same signed frame.
    for s in (3, 4):
        h = analytic_hadamard_walk(s)
        b = binomial_reference(s)
        print(f"steps={s} walk sum={sum(h.values()):.6f} "
              f"binomial sum={sum(b.values()):.6f}")
        print("  walk    :", {k: round(v, 4) for k, v in h.items()})
        print("  binomial:", {k: round(v, 4) for k, v in b.items()})
