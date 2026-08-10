#!/usr/bin/env python3
"""
walk_check.py — Quantum Galton Board: the P2 offline correctness gate.

No network, no QPU, no aer (OQ-2.5): runs in the minimal environment so the
root-free ideal arm's physics is verifiable without an IBM account. Exits
non-zero on any breach; prints a one-line PASS per check otherwise.

Checks:
  AC-2.1  One builder drives all three arms — dispatch-only difference. Asserted
          structurally: arms.run_arm dispatches over exactly {ideal,noisy,hw} and
          builds walk.build_walk once (hw/noisy are not executed here).
  AC-2.2  build_walk + Statevector vs an INDEPENDENT numpy position-space
          Hadamard-walk recursion: total-variation distance < TOL for steps 2..8,
          and twin-horn bimodality for steps >= 3.
  OQ-2.2  hw get_bitstrings() endianness round-trips through decode_counts with no
          reversal (a synthetic MSB-first string decodes to the expected bin).

This carries a LOCAL, self-contained Hadamard-walk recursion purely to satisfy
AC-2.2 offline; P3 owns the shared, importable analytic references (plan §3).
"""

from __future__ import annotations

import sys

import numpy as np
from qiskit.quantum_info import Statevector

import arms
from walk import build_walk
from walk_spec import decode_counts

TOL = 1e-6


def analytic_hadamard_walk(steps: int) -> dict[int, float]:
    """Independent position-space Hadamard walk (symmetric coin (|0>+i|1>)/sqrt2).

    Textbook line DTQW: positions -n..n, shift |x,0>->|x-1,0>, |x,1>->|x+1,1>,
    Hadamard coin each step. Returns {position: probability} over the same-parity
    reachable positions -n..n (step 2). This is a different frame from
    build_walk's incremental Galton construction, so agreement to TOL is a real
    cross-check, not a tautology.
    """
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


def ideal_histogram(steps: int) -> dict[int, float]:
    """build_walk + exact Statevector -> {position: probability}."""
    qc = build_walk(steps)
    unitary = qc.remove_final_measurements(inplace=False)
    probs = Statevector.from_instruction(unitary).probabilities_dict()
    counts = {bits: p for bits, p in probs.items()}
    return decode_counts(counts, steps)


def _tv(a: dict[int, float], b: dict[int, float]) -> float:
    return 0.5 * sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in set(a) | set(b))


def _is_twin_horn(hist: dict[int, float]) -> bool:
    """Two symmetric off-centre horns above the tails (and above any centre bin)."""
    positions = sorted(hist)
    peak = max(hist.values())
    # symmetric about 0
    if any(abs(hist[p] - hist.get(-p, 0.0)) > 1e-9 for p in positions):
        return False
    # global maximum is off-centre (horns, not a single central hump)
    argmax = [p for p in positions if hist[p] >= peak - 1e-12]
    if not all(abs(p) >= 1 for p in argmax):
        return False
    # the boundary tails sit below the horns (amplitude spread inward)
    if not (hist[positions[0]] < peak and hist[positions[-1]] < peak):
        return False
    # for even n the central bin exists and must be a valley below the horns
    if 0 in hist and not hist[0] < peak:
        return False
    return True


def check_dispatch() -> None:
    """AC-2.1: exactly three arms, one builder, dispatch-only difference."""
    assert set(arms._ARMS) == {"ideal", "noisy", "hw"}, arms._ARMS
    assert all(callable(fn) for fn in arms._ARMS.values())
    # run_arm builds build_walk once and hands it to the arm; verify the symbol
    # it uses is walk.build_walk (no per-arm circuit logic).
    assert arms.build_walk is build_walk
    print("PASS AC-2.1 dispatch: one build_walk, arms = ideal|noisy|hw")


def check_physics() -> None:
    """AC-2.2: ideal walk matches the analytic recursion; twin horns."""
    for steps in range(2, 9):
        ideal = ideal_histogram(steps)
        ref = analytic_hadamard_walk(steps)
        tv = _tv(ideal, ref)
        assert tv < TOL, f"steps={steps} TV={tv:.3e} >= TOL={TOL:.0e}"
        total = sum(ideal.values())
        assert abs(total - 1.0) < TOL, f"steps={steps} prob sum {total} != 1"
        if steps >= 3:
            assert _is_twin_horn(ideal), f"steps={steps} not twin-horn: {ideal}"
    print(f"PASS AC-2.2 physics: TV < {TOL:.0e} steps 2..8, twin horns steps>=3")


def check_endianness() -> None:
    """OQ-2.2: MSB-first get_bitstrings() decodes with no reversal."""
    # 2-step walk: 4 qubits (coin=0, bins 0..2 = qubits 1..3). Put the walker in
    # bin 2 (qubit index 3) -> MSB-first string '1000'. decode_counts must read
    # qubit i as bits[-(i+1)], so bin 2 -> position 2*2-2 = +2.
    decoded = decode_counts({"1000": 1}, steps=2)
    assert decoded == {2: 1.0}, decoded
    # bin 0 (qubit index 1) set -> '0010' -> position 2*0-2 = -2
    decoded = decode_counts({"0010": 1}, steps=2)
    assert decoded == {-2: 1.0}, decoded
    print("PASS OQ-2.2 endianness: MSB-first get_bitstrings round-trips, no reversal")


def main() -> int:
    try:
        check_dispatch()
        check_physics()
        check_endianness()
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("walk_check: all offline gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
