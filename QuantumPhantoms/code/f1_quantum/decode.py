"""F1 decode — measured bits -> TumorParams (plan §4, AC-4).

Pure bitstring parsing; no qiskit. The property register layout is fixed and
shared with circuit.py:

    prop qubit:  0  1 | 2  3 | 4  5 | 6  7  8
    field:       size | type | margn|   lobe
    bit role:   MSB LSB MSB LSB MSB LSB MSB .. LSB

One measured 9-bit property word -> one tile. A tile index within a field is the
big-endian value of its bits (MSB first, matching rulebook.amp_tree_angles' tree).

Register-to-bitstring convention: circuit.py measures prop qubit i into classical
bit i, so a qiskit counts/memory string `s` (char 0 = highest clbit) is reversed
once (`s[::-1]`) to index bits by qubit. `bits_to_params` takes that already-
reversed, qubit-indexed bit list.

Spare codes are remapped by nearest published frequency (Q3): margin's 4th code ->
the most common margin; the 3 spare lobe codes (5..7) -> the most common lobe.
"""

from __future__ import annotations

from common.datamodel import LOBES, MARGINS, TYPES, TumorParams
from f1_quantum.rulebook import Rulebook

# Field slices within the 9-qubit property register (qubit indices).
_SIZE = (0, 1)
_TYPE = (2, 3)
_MARGIN = (4, 5)
_LOBE = (6, 7, 8)


def _val(bits: list[int], idx: tuple[int, ...]) -> int:
    """Big-endian value of the bits at `idx` (first index = MSB)."""
    v = 0
    for i in idx:
        v = (v << 1) | (bits[i] & 1)
    return v


def _str_to_bits(s: str, n_qubits: int) -> list[int]:
    """qiskit counts/memory key -> qubit-indexed bit list (bits[i] = qubit i)."""
    clean = s.replace(" ", "")
    rev = clean[::-1]  # now rev[i] = clbit i = qubit i
    return [int(rev[i]) for i in range(n_qubits)]


def bits_to_params(
    bits: list[int],
    rulebook: Rulebook,
    *,
    lineage_id: str,
    generation: int,
    shot_index: int,
) -> TumorParams:
    """Decode one 9-bit property word into a TumorParams (spare codes remapped)."""
    size_i = _val(bits, _SIZE)
    type_i = _val(bits, _TYPE)
    margin_i = _val(bits, _MARGIN)
    lobe_i = _val(bits, _LOBE)

    size_mm = rulebook.size_mm()[size_i]
    nodule_type = TYPES[type_i]

    # margin: 4 codes, only 3 valid -> spare code 3 remaps to most common margin.
    if margin_i < len(MARGINS):
        margin = MARGINS[margin_i]
    else:
        margin = _most_common_margin(rulebook, nodule_type)

    # lobe: 8 codes, only 5 valid -> spare codes 5..7 remap to most common lobe.
    if lobe_i < len(LOBES):
        lobe = LOBES[lobe_i]
    else:
        lobe = _most_common_lobe(rulebook)

    return TumorParams(
        size_mm=size_mm,
        type=nodule_type,
        margin=margin,
        lobe=lobe,
        lineage_id=lineage_id,
        generation=generation,
        shot_index=shot_index,
    )


def _most_common_margin(rulebook: Rulebook, nodule_type: str) -> str:
    probs = rulebook.margin_given_type[nodule_type]
    return MARGINS[max(range(len(MARGINS)), key=lambda i: probs[i])]


def _most_common_lobe(rulebook: Rulebook) -> str:
    return max(rulebook.lobe_freqs, key=rulebook.lobe_freqs.get)


def decode_memory(
    memory: list[str],
    rulebook: Rulebook,
    *,
    generation: int,
    shot_start: int,
    lineage_prefix: str,
    n_qubits: int = 9,
) -> list[TumorParams]:
    """Decode a run's per-shot property words (one independent tile per shot)."""
    out: list[TumorParams] = []
    for k, s in enumerate(memory):
        bits = _str_to_bits(s, n_qubits)
        shot = shot_start + k
        out.append(
            bits_to_params(
                bits,
                rulebook,
                lineage_id=f"{lineage_prefix}{shot}",
                generation=generation,
                shot_index=shot,
            )
        )
    return out
