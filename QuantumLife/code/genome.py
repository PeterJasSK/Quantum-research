#!/usr/bin/env python3
"""
genome.py — the canonical bits -> branch-decision contract for Quantum Tree.

A generation measures an N-qubit register laid out as N_SLOTS branch-slots of
SLOT_BITS bits each. One shot = one full field of branch decisions for that
growth step; the web viewer walks these fields generation by generation to grow
a tree from a seed.

Layout per slot (SLOT_BITS = 6):
    bit 0,1 -> angle_raw  0..3   bend of this branch relative to its parent
    bit 2,3 -> length_raw 0..3   segment length
    bit 4   -> fork              1 = split into two child branches
    bit 5   -> leaf              1 = grow a green leaf cluster here (the branch
                                 KEEPS growing; branches only stop at the
                                 viewer's MAXDEPTH). Biased ON in qtree.py.

Default register is N_SLOTS * SLOT_BITS = 18 * 6 = 108 qubits -> the longest
low-error SWAP-free chain that actually fits on a 156-qubit Heron r2 (a full
120-qubit simple path does not exist on its heavy-hex lattice).

GENOME_SPEC is embedded verbatim into run.json so the viewer decodes the same
way (it keeps a JS mirror in web/quantum_tree.html -- keep the two in sync by
hand if you edit here).
"""

from __future__ import annotations

SLOT_BITS = 6
N_SLOTS = 18
N_BITS = SLOT_BITS * N_SLOTS   # 108

GENOME_SPEC: dict = {
    "n_bits": N_BITS,
    "slot_bits": SLOT_BITS,
    "n_slots": N_SLOTS,
    # field name -> local bit indices inside a slot (MSB first)
    "slot_fields": {
        "angle":  {"bits": [0, 1]},   # 0..3
        "length": {"bits": [2, 3]},   # 0..3
        "fork":   {"bits": [4]},      # flag
        "leaf":   {"bits": [5]},      # flag
    },
}


def _int(bits: str, idxs: list[int]) -> int:
    v = 0
    for i in idxs:
        v = (v << 1) | (1 if i < len(bits) and bits[i] == "1" else 0)
    return v


def decode_slot(slot_bits: str) -> dict:
    """A single 6-bit slot -> one branch decision."""
    angle_raw = _int(slot_bits, [0, 1])
    length_raw = _int(slot_bits, [2, 3])
    return {
        "bend":   angle_raw / 3.0 * 2.0 - 1.0,     # -1..+1 (left..right)
        "length": 0.4 + length_raw / 3.0 * 0.6,    # 0.4..1.0
        "fork":   1 if (len(slot_bits) > 4 and slot_bits[4] == "1") else 0,
        "leaf":   1 if (len(slot_bits) > 5 and slot_bits[5] == "1") else 0,
    }


def decode_field(bits: str, spec: dict = GENOME_SPEC) -> list[dict]:
    """A full N_BITS shot -> list of N_SLOTS branch decisions (the reference
    decoder; the web viewer mirrors this exactly)."""
    sb, ns = spec["slot_bits"], spec["n_slots"]
    return [decode_slot(bits[s * sb:(s + 1) * sb]) for s in range(ns)]


if __name__ == "__main__":
    print("n_bits", N_BITS, "n_slots", N_SLOTS, "slot_bits", SLOT_BITS)
    for b in ("0" * N_BITS, "1" * N_BITS):
        print(b[:12], "...", decode_slot(b[:SLOT_BITS]))
