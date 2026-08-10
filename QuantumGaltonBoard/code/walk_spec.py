#!/usr/bin/env python3
"""
walk_spec.py — Quantum Galton Board: the frozen position/coin decode contract.

This is the DTQW analogue of QuantumLife's genome.py:GENOME_SPEC -- a static
decode contract embedded verbatim into every run.json and hand-mirrored by the
P5 JS viewer. Unlike GENOME_SPEC (a fixed 108-qubit register) the walk register
grows with depth, so WALK_SPEC encodes the decode *rule* and each run.json
records the concrete `steps` / `n_position_qubits`.

Encoding: one-hot line (epic OQ-1). An n-step walk uses n+1 position qubits (one
qubit per reachable bin) + 1 coin qubit = n+2 qubits. Coin qubit is index 0;
position qubits are indices 1..n+1. Bitstrings are little-endian (qubit 0 is the
rightmost character), matching pipeline_common.run_sampler's get_bitstrings().

WALK_SPEC is frozen at P1. Any later change is an epic-level amendment (P5's JS
mirror is kept in sync by hand), not a plan edit.
"""

from __future__ import annotations

WALK_SPEC: dict = {
    "encoding": "one_hot_line",   # OQ-1
    "coin": "hadamard",           # OQ-4
    "coin_qubit": 0,              # coin qubit index in the register (LSB, rightmost bit)
    "position_qubits": "1..n+1", # one-hot bins; qubit j set == amplitude at bin j
    # bin index -> signed lattice position for an n-step walk
    "bin_to_position": "pos = 2*bin - n",   # bins 0..n  ->  positions -n..+n (step 2)
    "bitstring_order": "little",  # how run_sampler bitstrings map to qubit indices
    "version": 1,
}


def bin_to_position(bin_index: int, steps: int) -> int:
    """One-hot bin index (0..n) -> signed lattice position (-n..+n, step 2)."""
    return 2 * bin_index - steps


def decode_counts(counts: dict[str, int], steps: int,
                  spec: dict = WALK_SPEC) -> dict[int, float]:
    """Raw measured bitstring counts -> normalised {position: probability}.

    One-hot decode: position qubit j (register index 1+j) set to '1' means the
    walker occupies bin j at lattice position 2*j - steps. Bitstrings are
    little-endian, so register index i is character ``bits[-(i+1)]``. The coin
    qubit (index 0) is ignored for the position histogram. For a clean one-hot
    state exactly one position qubit is set per shot, so the returned
    probabilities sum to 1.
    """
    if spec.get("encoding") != "one_hot_line":
        raise ValueError(f"decode_counts only supports one_hot_line; got {spec.get('encoding')!r}")
    total = sum(counts.values())
    if total == 0:
        return {}
    hist: dict[int, int] = {}
    for bits, c in counts.items():
        for j in range(steps + 1):
            reg_index = 1 + j                       # position qubit for bin j
            if bits[-(reg_index + 1)] == "1":       # little-endian character
                pos = bin_to_position(j, steps)
                hist[pos] = hist.get(pos, 0) + c
    return {pos: hist[pos] / total for pos in sorted(hist)}


if __name__ == "__main__":
    # self-test mirrors genome.py's __main__ smoke: decode a clean 2-step one-hot
    # superposition of bin 0 (pos -2) and bin 2 (pos +2).
    demo = {"0010": 2048, "1001": 2048}   # coin/position bits, little-endian, 4 qubits
    h = decode_counts(demo, steps=2)
    print("WALK_SPEC:", WALK_SPEC)
    print("decode:", h, "sum=", round(sum(h.values()), 6))
