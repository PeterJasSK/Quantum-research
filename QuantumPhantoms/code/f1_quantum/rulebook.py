"""F1 rulebook — published lung-nodule statistics → gate angles (epic §4, parent §2.2/§2.3).

Every probability below is a **hand-set literal from published, citable aggregates**
(Fleischner Society size thresholds; LIDC-IDRI / LUNA16 distribution summaries).
Nothing here is fitted to a patient dataset — that is what keeps the generator
non-QML (parent §2.3). Edit the numbers, not the shape.

The angle math is pure-Python (math only, no qiskit): `amp_tree_angles(probs)`
turns a categorical distribution over 2^n outcomes into the binary-tree of `Ry`
angles that `circuit.py` applies to an n-qubit register. Conditionals (type|size,
margin|type) are returned as one tree per parent basis state so `circuit.py` can
apply them as uniformly-controlled rotations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from common.datamodel import LOBES, MARGINS, TYPES

# Size bands (mm). 4 bands -> 2 qubits. Fleischner 2017 reporting thresholds
# (<6 / 6-8 / >8 mm) split into 4 render bands; frequencies follow the small-nodule
# skew of LIDC-IDRI aggregates. Representative mm used for rendering per band.
SIZE_BANDS = (
    ("<6mm", 4.0, 0.55),
    ("6-8mm", 7.0, 0.25),
    ("8-20mm", 13.0, 0.15),
    (">20mm", 26.0, 0.05),
)

# P(type | size band). Rows align to SIZE_BANDS order; columns to datamodel.TYPES
# (solid, part-solid, ground-glass, calcified). Larger nodules skew solid.
TYPE_GIVEN_SIZE = {
    "<6mm": (0.55, 0.08, 0.30, 0.07),
    "6-8mm": (0.62, 0.12, 0.21, 0.05),
    "8-20mm": (0.70, 0.14, 0.12, 0.04),
    ">20mm": (0.80, 0.10, 0.07, 0.03),
}

# P(margin | type). Columns align to datamodel.MARGINS (smooth, lobulated, spiculated).
# Solid lesions carry more spiculation; ground-glass skews smooth.
MARGIN_GIVEN_TYPE = {
    "solid": (0.40, 0.33, 0.27),
    "part-solid": (0.45, 0.35, 0.20),
    "ground-glass": (0.70, 0.22, 0.08),
    "calcified": (0.80, 0.15, 0.05),
}

# P(lobe). Upper-lobe predominance for pulmonary nodules. Order = datamodel.LOBES
# (RUL, RML, RLL, LUL, LLL). 5 outcomes -> 3 qubits (8 codes, 3 spare; remapped in decode).
LOBE_FREQS = {
    "RUL": 0.34,
    "RML": 0.11,
    "RLL": 0.22,
    "LUL": 0.21,
    "LLL": 0.12,
}

SOURCE_CITATIONS = (
    "MacMahon H. et al., Fleischner Society 2017 guidelines, Radiology 284(1):228-243.",
    "Armato SG. et al., The LIDC-IDRI database, Med. Phys. 38(2):915-931 (2011).",
    "Setio AAA. et al., LUNA16 nodule analysis challenge, Med. Image Anal. 42:1-13 (2017).",
)


@dataclass
class Rulebook:
    """Published nodule statistics + representative render sizes (epic §4)."""

    size_bands: tuple = SIZE_BANDS
    type_given_size: dict = field(default_factory=lambda: dict(TYPE_GIVEN_SIZE))
    margin_given_type: dict = field(default_factory=lambda: dict(MARGIN_GIVEN_TYPE))
    lobe_freqs: dict = field(default_factory=lambda: dict(LOBE_FREQS))
    source_citations: tuple = SOURCE_CITATIONS

    def size_labels(self) -> list[str]:
        return [b[0] for b in self.size_bands]

    def size_probs(self) -> list[float]:
        return [b[2] for b in self.size_bands]

    def size_mm(self) -> list[float]:
        return [b[1] for b in self.size_bands]


def _normalize(probs) -> list[float]:
    probs = [max(0.0, float(p)) for p in probs]
    total = sum(probs)
    if total <= 0:
        raise ValueError("distribution sums to zero")
    return [p / total for p in probs]


def _pad_pow2(probs: list[float]) -> list[float]:
    """Pad a distribution up to the next power of two with zero-probability slots
    (the spare register codes; remapped at decode time)."""
    n = 1
    while n < len(probs):
        n <<= 1
    return probs + [0.0] * (n - len(probs))


def amp_tree_angles(probs) -> list[float]:
    """Binary-tree `Ry` angles for amplitude-encoding `probs` over `log2(len)` qubits.

    Returns angles in the fixed order `circuit.py` consumes them: breadth-first over
    the split tree, MSB qubit first. Node angle = `2*acos(sqrt(P(left-subtree)))`;
    a node with zero mass yields angle 0. `len(probs)` must be a power of two
    (use `_pad_pow2` first).
    """
    probs = _normalize(_pad_pow2(list(probs)))
    n = len(probs)
    if n & (n - 1):
        raise ValueError("len(probs) must be a power of two")

    angles: list[float] = []
    width = n
    # Walk levels from the whole array down to pairs; each level = one qubit.
    while width > 1:
        half = width // 2
        for start in range(0, n, width):
            block = probs[start:start + width]
            left = sum(block[:half])
            total = sum(block)
            if total <= 0:
                angles.append(0.0)
            else:
                ratio = min(1.0, max(0.0, left / total))
                angles.append(2.0 * math.acos(math.sqrt(ratio)))
        width = half
    return angles


def angles_from_rulebook(rulebook: Rulebook) -> dict:
    """All gate angles for the property register (plan §4, AC-1).

    Shape (each value is an angle-tree or a list of trees, one per parent state):
      - "size":             tree over 4 size bands            (2 qubits)
      - "type_given_size":  4 trees (one per size band)       (2 qubits, uniformly-controlled)
      - "margin_given_type":4 trees (one per type)            (2 qubits, uniformly-controlled)
      - "lobe":             tree over 5 lobes padded to 8     (3 qubits)
    """
    size = amp_tree_angles(rulebook.size_probs())

    type_given_size = [
        amp_tree_angles(rulebook.type_given_size[label])
        for label in rulebook.size_labels()
    ]

    # margin has 3 categories -> padded to 4 (one spare code, remapped in decode).
    margin_given_type = [
        amp_tree_angles(rulebook.margin_given_type[t]) for t in TYPES
    ]

    lobe = amp_tree_angles([rulebook.lobe_freqs[l] for l in LOBES])

    return {
        "size": size,
        "type_given_size": type_given_size,
        "margin_given_type": margin_given_type,
        "lobe": lobe,
    }
