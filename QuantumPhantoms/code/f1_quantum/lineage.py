"""F1 lineage — the one quantum division, decoded into sibling pairs (epic §5, AC-6).

The division circuit itself lives in circuit.build_sibling_pair_circuit (controlled-copy
+ Ry(theta_mut), full-genotype per Q2). This module owns the division's semantics on the
decode side: one measured 18-bit word -> a parent tile (generation 0) and a daughter tile
(generation 1) sharing a `lineage_id`, so F3 can draw the "gen 1 of ∞" badge.

This is the MVP's single generation only — no loop, no selection (that is F4).
"""

from __future__ import annotations

from f1_quantum.backend import flatten_counts
from common.datamodel import TumorParams
from f1_quantum.decode import _str_to_bits, bits_to_params
from f1_quantum.circuit import N_PROP
from f1_quantum.rulebook import Rulebook

# Mutation rotation applied to each copied daughter qubit (radians). Small so daughters
# stay strongly correlated to the parent (shared ancestry) with a little drift.
DEFAULT_THETA_MUT = 0.3


def decode_pairs(
    counts: dict[str, int],
    rulebook: Rulebook,
    *,
    n_pairs: int,
    shot_start: int,
    lineage_prefix: str = "pair",
) -> list[TumorParams]:
    """Decode the first `n_pairs` shots of a sibling-circuit run into 2*n_pairs tiles.

    The 18-bit word is `daughter(9) parent(9)` low-to-high: bits[0:9] = parent,
    bits[9:18] = daughter (circuit.build_sibling_pair_circuit measures parent into the
    low half of register `c`). Each pair shares one `lineage_id`.
    """
    out: list[TumorParams] = []
    words = flatten_counts(counts)[:n_pairs]
    for k, word in enumerate(words):
        bits = _str_to_bits(word, 2 * N_PROP)
        parent_bits = bits[:N_PROP]
        daughter_bits = bits[N_PROP:]
        lineage_id = f"{lineage_prefix}{shot_start + k}"
        out.append(
            bits_to_params(
                parent_bits, rulebook,
                lineage_id=lineage_id, generation=0, shot_index=shot_start + k,
            )
        )
        out.append(
            bits_to_params(
                daughter_bits, rulebook,
                lineage_id=lineage_id, generation=1, shot_index=shot_start + k,
            )
        )
    return out
