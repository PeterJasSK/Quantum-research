"""ROLL: today's stage B. Published nodule statistics -> a shallow circuit -> tumour parameters, with a CHSH pair.

    rulebook   Fleischner / LIDC statistics (size, type | size, margin | type, lobe) as Ry angle trees
    circuit    9 property qubits per tumour; a sibling pair = parent + mutated daughter (2 x 9 qubits); 4 CHSH settings
    decode     one shot = one tumour (one shot per sibling pair)
    roll()     all of it as ONE job on the run's backend: cohort_params.json + quantum_run.json
CHSH S is a job-level statistic (one Bell test over 4 settings), never a per-tumour value. S <= 2: the draw is
rejected, no cohort file is written, no retry (section C stops the run).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from common import quantum as Q, runio
from common.datamodel import LOBES, MARGINS, TYPES, QuantumRun, TumorParams
from common.runio import Ctx

TILES = 12                    # tumours in the cohort
PAIRS = 2                     # sibling pairs among them
DRY_TILES, DRY_PAIRS = 4, 1   # dry run: a small cohort (tests the pipeline, not the patients)
DRY_MAX_MM = 7.0              # dry run: larger rolled sizes are cut to this (growth time)
CHSH_SHOTS = 2048             # shots per CHSH setting


# ============================================================================================== rulebook: published nodule statistics -> Ry angle trees
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


# ============================================================================================== CHSH: settings and the job-level S
# Optimal CHSH angle settings (radians), as ry rotations applied before Z measurement.
# a in {a0, a1} on the first qubit, b in {b0, b1} on the second.
CHSH_SETTINGS = {
    "a0": 0.0,
    "a1": math.pi / 2,
    "b0": math.pi / 4,
    "b1": -math.pi / 4,
}

# The four (a, b) pairs and their signs in S. circuit.py applies ry(-theta) on each
# qubit before Z-measurement; with these angles S -> +2*sqrt(2) on a noiseless pair
# (matches study-ideas/QuantumAlgorithmsExplained/code/11_chsh.py).
CHSH_PAIRS = (("a0", "b0"), ("a0", "b1"), ("a1", "b0"), ("a1", "b1"))
CHSH_SIGNS = (1.0, 1.0, 1.0, -1.0)


def correlator(counts: dict[str, int]) -> float:
    """E = (agree - disagree)/total for a 2-qubit setting's counts.

    `counts` keys are 2-char bitstrings ("00".."11"); agree = "00" + "11".
    Extra classical bits (if the key is longer) are ignored by taking the last 2.
    """
    agree = disagree = 0
    for bitstring, n in counts.items():
        two = bitstring.replace(" ", "")[-2:]
        if two in ("00", "11"):
            agree += n
        else:
            disagree += n
    total = agree + disagree
    if total == 0:
        return 0.0
    return (agree - disagree) / total


def chsh_value(counts_by_pair: dict[tuple[str, str], dict[str, int]]) -> float:
    """S from the four settings' counts.

    `counts_by_pair` maps each (a, b) in CHSH_PAIRS to that setting's counts dict.
    S = E(a0,b0) + E(a0,b1) + E(a1,b0) - E(a1,b1).
    """
    return sum(
        sign * correlator(counts_by_pair[pair])
        for pair, sign in zip(CHSH_PAIRS, CHSH_SIGNS)
    )


# ============================================================================================== circuits: 9 property qubits, one division, the 4 CHSH settings
# Field slices within the 9-qubit property register (qubit indices; first = MSB).
SIZE_Q = (0, 1)
TYPE_Q = (2, 3)
MARGIN_Q = (4, 5)
LOBE_Q = (6, 7, 8)
N_PROP = 9


def _apply_tree(qc, qubits, tree, *, base, fixed_controls=(), fixed_value=0):
    """Apply a breadth-first `Ry` angle tree to a register, optionally conditioned.

    `qubits`/`fixed_controls` are integer offsets into the circuit's qubit list,
    added to `base`. `qubits[0]` is the MSB. When `fixed_controls` is non-empty,
    every rotation is additionally controlled on those parent qubits being in the
    big-endian state `fixed_value` (this is how type|size and margin|type condition).
    """
    tq = [base + q for q in qubits]
    fc = [base + q for q in fixed_controls]
    nfixed = len(fc)
    k = len(tq)
    pos = 0
    for level in range(k):
        target = tq[level]
        controls = fc + tq[:level]
        for c in range(1 << level):
            theta = tree[pos]
            pos += 1
            if not controls:
                qc.ry(theta, target)
                continue
            flips = []
            for m in range(nfixed):
                if not ((fixed_value >> (nfixed - 1 - m)) & 1):
                    flips.append(fc[m])
            for m in range(level):
                if not ((c >> (level - 1 - m)) & 1):
                    flips.append(tq[m])
            for q in flips:
                qc.x(q)
            qc.mcry(theta, controls, target)
            for q in flips:
                qc.x(q)


def _encode_properties(qc, angles, base=0):
    """Encode the rulebook Bayesian network onto the 9 property qubits at `base`."""
    _apply_tree(qc, SIZE_Q, angles["size"], base=base)
    for j in range(4):
        _apply_tree(qc, TYPE_Q, angles["type_given_size"][j],
                    base=base, fixed_controls=SIZE_Q, fixed_value=j)
    for j in range(4):
        _apply_tree(qc, MARGIN_Q, angles["margin_given_type"][j],
                    base=base, fixed_controls=TYPE_Q, fixed_value=j)
    _apply_tree(qc, LOBE_Q, angles["lobe"], base=base)


def build_tumor_circuit(angles: dict) -> QuantumCircuit:
    """Independent single-nodule circuit: one measured shot -> one tile (AC-2)."""
    prop = QuantumRegister(N_PROP, "prop")
    creg = ClassicalRegister(N_PROP, "c")
    qc = QuantumCircuit(prop, creg)
    _encode_properties(qc, angles, base=0)
    qc.measure(prop, creg)
    return qc


def build_sibling_pair_circuit(angles: dict, theta_mut: float) -> QuantumCircuit:
    """Division circuit: parent genotype -> controlled-copy + Ry(theta_mut) -> daughter.

    One measured shot -> one sibling pair (parent gen 0, daughter gen 1) correlated
    by shared ancestry (epic §5, AC-6). Full-genotype copy (Q2): every property qubit
    is copied, then mutated.
    """
    parent = QuantumRegister(N_PROP, "parent")
    daughter = QuantumRegister(N_PROP, "daughter")
    # One 18-bit register so both the Aer and SamplerV2 paths read via `.data.c`.
    # Low 9 bits (c0..c8) = parent word; high 9 bits (c9..c17) = daughter word.
    creg = ClassicalRegister(2 * N_PROP, "c")
    qc = QuantumCircuit(parent, daughter, creg)

    _encode_properties(qc, angles, base=0)  # parent occupies qubits 0..8
    for i in range(N_PROP):
        qc.cx(parent[i], daughter[i])        # controlled-copy (clone in Z basis)
        qc.ry(theta_mut, daughter[i])        # mutation

    qc.measure(parent, creg[:N_PROP])
    qc.measure(daughter, creg[N_PROP:])
    return qc


def build_chsh_circuits() -> dict[tuple[str, str], QuantumCircuit]:
    """The 4 CHSH setting circuits (AC-5). Bell pair h+cx, ry(-theta) per qubit, Z-measure."""
    out: dict[tuple[str, str], QuantumCircuit] = {}
    for a_key, b_key in CHSH_PAIRS:
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.ry(-CHSH_SETTINGS[a_key], 0)
        qc.ry(-CHSH_SETTINGS[b_key], 1)
        qc.measure([0, 1], [0, 1])
        out[(a_key, b_key)] = qc
    return out


# ============================================================================================== decode: measured bits -> TumorParams
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


# ============================================================================================== lineage: one quantum division -> parent + daughter
def flatten_counts(counts: dict[str, int]) -> list[str]:
    """Expand a counts dict into a flat list of per-shot bitstrings.

    Lets F1 treat each shot as one independent draw (one tile / one pair) without
    depending on a per-shot memory API. Order is by key; length == total shots.
    """
    out: list[str] = []
    for key, n in counts.items():
        out.extend([key] * int(n))
    return out


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


# ============================================================================================== the job
def rulebook_json(rb: Rulebook) -> dict:
    return {"size": dict(zip(rb.size_labels(), rb.size_probs())), "size_mm": dict(zip(rb.size_labels(), rb.size_mm())),
            "type_given_size": rb.type_given_size, "margin_given_type": rb.margin_given_type, "lobe": rb.lobe_freqs,
            "types": list(TYPES), "sources": list(rb.source_citations)}


def roll(ctx: Ctx) -> float:
    """Roll the cohort on the run's backend. Returns the CHSH value S."""
    rb = Rulebook()
    runio.save_json(ctx.path("rulebook.json"), rulebook_json(rb))
    ang = angles_from_rulebook(rb)
    n_tiles, n_pairs = (TILES, PAIRS) if ctx.live else (DRY_TILES, DRY_PAIRS)
    n_indep = n_tiles - 2 * n_pairs
    jobs = [("tumor", build_tumor_circuit(ang), n_indep), ("pairs", build_sibling_pair_circuit(ang, DEFAULT_THETA_MUT), n_pairs)]
    jobs += [(f"chsh_{a}_{b}", qc, CHSH_SHOTS) for (a, b), qc in build_chsh_circuits().items()]
    bits, info = Q.execute(ctx, "roll", [qc for _, qc, _ in jobs], [sh for _, _, sh in jobs], opt=3, scalable=False)
    words = {n: ["".join(str(v) for v in row[::-1]) for row in bt] for (n, _, _), bt in zip(jobs, bits)}
    counts = {n: {} for n in words}
    for n, ws in words.items():
        for w in ws:
            counts[n][w] = counts[n].get(w, 0) + 1
    S = chsh_value({tuple(n.split("_")[1:3]): counts[n] for n in counts if n.startswith("chsh_")})
    tiles = decode_memory(words["tumor"][:n_indep], rb, generation=0, shot_start=0, lineage_prefix="tile", n_qubits=9)
    tiles += decode_pairs(dict(_count(words["pairs"][:n_pairs])), rb, n_pairs=n_pairs, shot_start=n_indep, lineage_prefix="pair")
    if not ctx.live:
        for t in tiles:
            t.size_mm = min(t.size_mm, DRY_MAX_MM)
    run = QuantumRun(backend_name=info["label"] if not ctx.live else info["backend"], job_id=info["job_id"], chsh_value=S,
                     chsh_settings=dict(CHSH_SETTINGS), raw_bits=words["tumor"][:n_indep] + words["pairs"][:n_pairs],
                     shot_indices=[t.shot_index for t in tiles])
    runio.save_json(ctx.path("quantum_run.json"), run.to_dict())
    if S > 2:
        runio.save_json(ctx.path("cohort_params.json"), [t.to_dict() for t in tiles])
        Q.log(f"cohort rolled ({info['label']}): CHSH S = {S:.3f}, {len(tiles)} tumours: "
              + ", ".join(f"{t.type[:5]} {t.size_mm:.0f}mm {t.lobe}" for t in tiles))
    return S


def _count(ws: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for w in ws:
        out[w] = out.get(w, 0) + 1
    return out
