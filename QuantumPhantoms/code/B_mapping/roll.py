"""ROLL: stage B's draw. Published nodule statistics + bits of the run's pool -> tumour parameters.

    rulebook   Fleischner / LIDC statistics: size, type | size, margin | type, lobe
    draw       BITS pool bits per property, mapped by inverse CDF on the rulebook probabilities (4 properties per
               tumour). A sibling pair = a parent and a daughter that copies each property of the parent and
               redraws it with probability P_MUT.
    roll()     the whole cohort from ONE draw of the pool (label "roll"): cohort_params.json + quantum_run.json
No circuit and no job here: the bits come from section C's Bell map (common.runio.draw_bits). Without a pool there
is no cohort. The cohort's claim level is L0 (provenance): the sibling pair is a classical copy with mutation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from common import quantum as Q, runio
from common.datamodel import LOBES, MARGINS, TYPES, QuantumRun, TumorParams
from common.runio import Ctx

TILES = 12                    # tumours in the cohort
PAIRS = 2                     # sibling pairs among them
DRY_TILES, DRY_PAIRS = 4, 1   # dry run: a small cohort (tests the pipeline, not the patients)
DRY_MAX_MM = 7.0              # dry run: larger rolled sizes are cut to this (growth time)


# ============================================================================================== rulebook: published nodule statistics
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


# ============================================================================================== decode: a measured 9-bit property word -> TumorParams
# Not used by roll(). Used by from_words() for B circuits that sample property words (B-IQP, B_mapping/iqp.py).
# Field slices within the 9-bit word (first index = MSB of the field).
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


# ============================================================================================== draw: pool bits -> TumorParams by inverse CDF
BITS = 16                     # pool bits per property: inverse CDF at a resolution of 2^-16
PROPS = 4                     # size, type, margin, lobe
DEFAULT_THETA_MUT = 0.3       # mutation angle of the former division circuit (radians)
P_MUT = 1 - math.cos(DEFAULT_THETA_MUT / 2) ** 4      # a 2-qubit property of that circuit changed with this probability (0.044)


def _pick(u: float, probs) -> int:
    """Inverse CDF: the outcome whose cumulative interval holds u in [0, 1)."""
    c = np.cumsum(_normalize(probs))
    return int(min(np.searchsorted(c, u, side="right"), len(c) - 1))


def draw_tumour(bits, rulebook: Rulebook, *, lineage_id: str, generation: int, shot_index: int,
                parent: TumorParams | None = None) -> TumorParams:
    """PROPS x BITS pool bits -> one tumour. With `parent`: a daughter, each property copied from the parent unless
    its draw u falls below P_MUT; then u / P_MUT (uniform again) redraws it from the rulebook."""
    w = np.asarray(bits, dtype=np.int64).reshape(PROPS, BITS)
    u = (w * (1 << np.arange(BITS - 1, -1, -1))).sum(1) / 2.0 ** BITS

    def pick(k: int, probs, old: int | None) -> int:
        if old is None:
            return _pick(u[k], probs)
        return _pick(u[k] / P_MUT, probs) if u[k] < P_MUT else old

    labels = rulebook.size_labels()
    old = (None,) * PROPS if parent is None else (rulebook.size_mm().index(parent.size_mm), TYPES.index(parent.type),
                                                   MARGINS.index(parent.margin), LOBES.index(parent.lobe))
    si = pick(0, rulebook.size_probs(), old[0])
    ti = pick(1, rulebook.type_given_size[labels[si]], old[1])
    mi = pick(2, rulebook.margin_given_type[TYPES[ti]], old[2])
    li = pick(3, [rulebook.lobe_freqs[lobe] for lobe in LOBES], old[3])
    return TumorParams(size_mm=rulebook.size_mm()[si], type=TYPES[ti], margin=MARGINS[mi], lobe=LOBES[li],
                       lineage_id=lineage_id, generation=generation, shot_index=shot_index)


# ============================================================================================== the draw of the cohort
def rulebook_json(rb: Rulebook) -> dict:
    return {"size": dict(zip(rb.size_labels(), rb.size_probs())), "size_mm": dict(zip(rb.size_labels(), rb.size_mm())),
            "type_given_size": rb.type_given_size, "margin_given_type": rb.margin_given_type, "lobe": rb.lobe_freqs,
            "types": list(TYPES), "sources": list(rb.source_citations)}


def roll(ctx: Ctx) -> None:
    """Draw the cohort from the run's bit pool. quantum_run.json keeps its fields: job_id and chsh_value are the
    Bell-map job and its pooled S, raw_bits the pool bits spent per shot (a sibling pair shares one shot)."""
    rb = Rulebook()
    runio.save_json(ctx.path("rulebook.json"), rulebook_json(rb))
    n_tiles, n_pairs = (TILES, PAIRS) if ctx.live else (DRY_TILES, DRY_PAIRS)
    n_indep = n_tiles - 2 * n_pairs
    W = PROPS * BITS
    try:
        bits = runio.draw_bits(ctx, "roll", n_tiles * W)
    except RuntimeError as e:
        Q.log(f"roll: {e}: no cohort")
        raise SystemExit(7) from e
    word = [bits[k * W:(k + 1) * W] for k in range(n_tiles)]
    text = ["".join(str(int(v)) for v in w) for w in word]
    tiles = [draw_tumour(word[k], rb, lineage_id=f"tile{k}", generation=0, shot_index=k) for k in range(n_indep)]
    raw = text[:n_indep]
    for j in range(n_pairs):
        k, shot = n_indep + 2 * j, n_indep + j
        parent = draw_tumour(word[k], rb, lineage_id=f"pair{shot}", generation=0, shot_index=shot)
        tiles += [parent, draw_tumour(word[k + 1], rb, lineage_id=f"pair{shot}", generation=1, shot_index=shot,
                                      parent=parent)]
        raw.append(text[k] + text[k + 1])
    _save(ctx, tiles, raw, f"drawn from {n_tiles * W} pool bits")


def from_words(ctx: Ctx, words, source: str) -> None:
    """CIRCUIT = "B-IQP": the cohort decoded from sampled 9-bit property words (bits_to_params), one tumour per
    word, each its own lineage (no sibling pairs). Replaces the cohort roll() drew from the pool; still L0."""
    rb = Rulebook()
    tiles = [bits_to_params([int(v) for v in w], rb, lineage_id=f"tile{k}", generation=0, shot_index=k)
             for k, w in enumerate(words)]
    _save(ctx, tiles, ["".join(str(int(v)) for v in w) for w in words], f"decoded from {len(tiles)} sampled words of {source}")


def _save(ctx: Ctx, tiles: list[TumorParams], raw: list[str], how: str) -> None:
    if not ctx.live:
        for t in tiles:
            t.size_mm = min(t.size_mm, DRY_MAX_MM)
    cert = runio.load_json(ctx.run_dir / "certificate.json")
    run = QuantumRun(backend_name=cert["backend"], job_id=cert["job_id"], chsh_value=cert["chsh_S"],
                     chsh_settings=cert["chsh_settings"], raw_bits=raw, shot_indices=[t.shot_index for t in tiles])
    runio.save_json(ctx.path("quantum_run.json"), run.to_dict())
    runio.save_json(ctx.path("cohort_params.json"), [t.to_dict() for t in tiles])
    Q.log(f"cohort {how} ({cert['label']}): {len(tiles)} tumours: "
          + ", ".join(f"{t.type[:5]} {t.size_mm:.0f}mm {t.lobe}" for t in tiles))
