"""F4 progression — one lineage grown as a clonal mass over generations (longitudinal arm).

This is the parent plan's §5.2.5 "generation -> growth snapshot / baseline->follow-up"
longitudinal pair, at smallest scale: ONE tumour latched to ONE spot, grown by the baked-in
QALife processes. Each generation every living cell divides (P1: controlled-copy + Ry(theta_mut))
and commits a fate (P2), the classical host keeps the fittest daughter, and the daughter is
ADDED to the mass (clonal accumulation) — so the lesion visibly enlarges generation by
generation. Daughters are placed hugging their parent (golden-angle spiral) so siblings stay
spatially contiguous (lineage -> spatial contiguity).

Pure quantum/data here (reuses f4_qalife.loop circuit builders + the within-generation witness);
the CT compositing + timeline page live in grow.py. Honest label unchanged: quantum within a
generation, classical genealogy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from common.datamodel import GenerationRecord, TumorParams
from f1_quantum.backend import flatten_counts, run_counts
from f1_quantum.certify import chsh_value
from f1_quantum.circuit import N_PROP, _encode_properties, build_chsh_circuits
from f1_quantum.decode import _str_to_bits, bits_to_params
from f1_quantum.lineage import DEFAULT_THETA_MUT
from f1_quantum.rulebook import Rulebook, angles_from_rulebook
from f4_qalife import fitness
from f4_qalife.loop import _decode_candidate, _fate_prep, build_division_circuit, build_founder_circuit
from f4_qalife.witness import cross_generation_witness, witness_value

GOLDEN_ANGLE = 2.399963229728653  # radians; spreads daughters evenly as the mass grows


@dataclass
class PlacedCell:
    """One clone in the growing mass: its tumour params + fate + spatial offset (mm)."""

    cell: TumorParams
    fate: str
    geno_bits: list[int]
    word: str
    dx_mm: float
    dy_mm: float
    born_gen: int


@dataclass
class GrowthFrame:
    """A snapshot of the whole mass at one generation + that generation's witness."""

    generation: int
    cells: list[PlacedCell]
    record: GenerationRecord
    process: str = ""              # human label of what the QALife loop did this generation
    mode: str = "A"                # "B" = coherent genealogy (entangled), "A" = measure-restart
    cross_pairs: list = field(default_factory=list)  # Mode-B founder<->daughter witnesses

    def diameter_mm(self) -> float:
        """Approx overall mass diameter: 2*(farthest clone centre + its radius)."""
        reach = 0.0
        for pc in self.cells:
            d = math.hypot(pc.dx_mm, pc.dy_mm) + pc.cell.size_mm / 2.0
            reach = max(reach, d)
        return 2.0 * reach


def _best(words, rulebook, generation):
    cands = [_decode_candidate(w, rulebook, "grow", generation, k) for k, w in enumerate(words)]
    return fitness.select(cands, 1)[0]


def _witness_record(generation, n_cells, theta_mut, phase, shots, backend) -> GenerationRecord:
    w, xx, zz = witness_value(theta_mut, shots, backend)
    return GenerationRecord(
        generation=generation, n_cells=n_cells, survivors=n_cells,
        witness_value=w, xx=xx, zz=zz, phase=phase,
    )


def coherent_core_qubits(coherent_cells: int) -> int:
    """Qubit width of the Mode-B coherent-core circuit (founder + daughters + fates)."""
    return coherent_cells * N_PROP + coherent_cells * 2


def build_coherent_core_circuit(angles: dict, k: int, theta_mut: float, phase: float) -> QuantumCircuit:
    """Mode-B coherent genealogy (P3): founder + (k-1) daughters kept ENTANGLED in one circuit.

    The founder genotype is encoded, then each daughter is a coherent controlled-copy +
    Ry(theta_mut) of the founder register — NO measurement between parent and daughter, so the
    whole family stays in one joint entangled state until the final measurement. Decoding one
    shot yields a family whose genotypes are jointly sampled from the entangled state (a
    classically-hard object; no PRNG genealogy reproduces the joint distribution). Width grows
    with k (k=2 -> 20q genotype + fates; deeper k collapses on Heron — kept shallow by default).
    """
    geno = [QuantumRegister(N_PROP, f"cell{i}") for i in range(k)]
    fate = [QuantumRegister(2, f"fate{i}") for i in range(k)]
    c = ClassicalRegister(k * N_PROP + k * 2, "c")  # [geno0..genoK-1][fate0..fateK-1]
    qc = QuantumCircuit(*geno, *fate, c)

    _encode_properties(qc, angles, base=0)          # founder = cell0 (qubits 0..8)
    base_daughter = N_PROP
    for d in range(1, k):
        for i in range(N_PROP):
            qc.cx(geno[0][i], geno[d][i])           # coherent copy — founder stays entangled
            qc.ry(theta_mut, geno[d][i])            # mutation
    for i in range(k):
        _fate_prep(qc, fate[i][0], fate[i][1], phase)

    for i in range(k):
        qc.measure(geno[i], c[i * N_PROP:(i + 1) * N_PROP])
    foff = k * N_PROP
    for i in range(k):
        qc.measure(fate[i], c[foff + i * 2: foff + i * 2 + 2])
    return qc


def _decode_core_shot(word: str, rulebook: Rulebook, k: int, shot_start: int) -> list[dict]:
    """Decode one coherent-core shot into k families cells (founder + coherent daughters)."""
    bits = _str_to_bits(word, k * N_PROP + k * 2)
    foff = k * N_PROP
    out = []
    for i in range(k):
        geno = bits[i * N_PROP:(i + 1) * N_PROP]
        fbits = bits[foff + i * 2], bits[foff + i * 2 + 1]
        cell = bits_to_params(
            geno, rulebook, lineage_id="grow", generation=0 if i == 0 else 1,
            shot_index=shot_start + i,
        )
        out.append({
            "cell": cell, "fate": fitness.decode_fate(*fbits),
            "geno_bits": geno, "word": word,
            "score": fitness.score(cell.size_mm, fitness.decode_fate(*fbits)),
        })
    return out


def run_coherent_core(rulebook, angles, k, theta_mut, phase, shots, backend, shot_start):
    """Run the coherent-core circuit, pick the fittest sampled family, certify it.

    Returns (core_cells, w_cross, cross_pairs). `core_cells` are k candidate dicts
    (index 0 = founder, 1.. = coherent daughters) from ONE joint entangled measurement.
    """
    words = flatten_counts(run_counts(build_coherent_core_circuit(angles, k, theta_mut, phase), shots, backend))
    families = [_decode_core_shot(w, rulebook, k, shot_start) for w in words[:shots]]
    best = max(families, key=lambda fam: sum(c["score"] for c in fam))  # fittest realized family
    w_cross, pairs = cross_generation_witness(k, theta_mut, shots, backend)
    return best, w_cross, pairs


def grow_lineage(
    rulebook: Rulebook,
    *,
    generations: int = 4,
    offspring: int = 4,
    theta_mut: float = DEFAULT_THETA_MUT,
    phase: float = 0.0,
    witness_shots: int = 4096,
    max_cells: int = 16,
    coherent_cells: int = 2,
    backend=None,
) -> tuple[list[GrowthFrame], list[str], float]:
    """Grow one lineage. Returns (frames, raw_bits, chsh_value).

    Generation 0 = founder (rulebook genotype, quantum). Each later generation: every current
    clone divides (P1) + commits a fate (P2); host keeps the fittest daughter and ADDS it to
    the mass (clonal accumulation). Population ~doubles per generation up to `max_cells`.
    """
    angles = angles_from_rulebook(rulebook)
    raw: list[str] = []
    shot = 0
    k = max(1, min(coherent_cells, max_cells))

    # ---- Mode B coherent core: founder + (k-1) daughters kept ENTANGLED, one joint shot ----
    if k >= 2:
        core, w_cross, cross_pairs = run_coherent_core(
            rulebook, angles, k, theta_mut, phase, witness_shots, backend, shot)
        shot += k
        raw.extend(c["word"] for c in core)
        founder = PlacedCell(core[0]["cell"], core[0]["fate"], core[0]["geno_bits"], core[0]["word"], 0.0, 0.0, 0)
        pop: list[PlacedCell] = [founder]
        pack_c = 0.55 * max(founder.cell.size_mm / 2.0, 2.5)  # tight: clones overlap into one mass

        frames = [
            GrowthFrame(
                0, list(pop),
                _witness_record(0, 1, theta_mut, phase, witness_shots, backend),
                process="Founder — genotype prepared coherently on the device (Mode B core).",
                mode="B",
            )
        ]
        cell_counter = 1
        for cd in core[1:]:
            idx = cell_counter
            cell_counter += 1
            r = pack_c * math.sqrt(idx)
            ang = GOLDEN_ANGLE * idx
            pop.append(PlacedCell(cd["cell"], cd["fate"], cd["geno_bits"], cd["word"],
                                  r * math.cos(ang), r * math.sin(ang), 1))
        rec1 = GenerationRecord(generation=1, n_cells=k, survivors=k,
                                witness_value=w_cross, xx=float("nan"), zz=float("nan"), phase=phase)
        frames.append(GrowthFrame(
            1, list(pop), rec1,
            process=(f"Coherent genealogy (Mode B, P3): founder↔{k-1} daughter"
                     f"{'s' if k > 2 else ''} kept ENTANGLED (never measured between), "
                     f"certified W_cross={w_cross:.3f} — no classical genealogy reproduces this joint state."),
            mode="B", cross_pairs=cross_pairs))
        start_gen = 2
    else:
        # k < 2 — pure Mode A founder (no coherent core).
        fwords = flatten_counts(run_counts(build_founder_circuit(angles, phase), offspring, backend))[:offspring]
        fb = _best(fwords, rulebook, 0)
        fb["cell"].shot_index = shot
        shot += 1
        raw.append(fb["word"])
        founder = PlacedCell(fb["cell"], fb["fate"], fb["geno_bits"], fb["word"], 0.0, 0.0, 0)
        pop = [founder]
        pack_c = 0.55 * max(founder.cell.size_mm / 2.0, 2.5)
        frames = [GrowthFrame(
            0, list(pop),
            _witness_record(0, 1, theta_mut, phase, witness_shots, backend),
            process="Founder — genotype rolled from the rulebook (quantum state prep).", mode="A")]
        cell_counter = 1
        start_gen = 1

    # ---- Mode A accumulation for the remaining (deep) generations ----
    for g in range(start_gen, generations):
        new: list[PlacedCell] = []
        for parent in list(pop):
            if len(pop) + len(new) >= max_cells:
                break
            dwords = flatten_counts(
                run_counts(build_division_circuit(parent.geno_bits, theta_mut, phase), offspring, backend)
            )[:offspring]
            db = _best(dwords, rulebook, g)
            db["cell"].shot_index = shot
            shot += 1
            raw.append(db["word"])
            idx = cell_counter               # global clone index (founder = 0)
            cell_counter += 1
            r = pack_c * math.sqrt(idx)
            ang = GOLDEN_ANGLE * idx
            new.append(
                PlacedCell(
                    db["cell"], db["fate"], db["geno_bits"], db["word"],
                    r * math.cos(ang), r * math.sin(ang), g,
                )
            )
        pop = pop + new
        births = len(new)
        frames.append(
            GrowthFrame(
                g, list(pop),
                _witness_record(g, len(pop), theta_mut, phase, witness_shots, backend),
                process=(f"Division ×{births} (Mode A: measure-restart, P1 copy + Ry(θ_mut)) + "
                         f"fate (P2, phase dial) → {len(pop)} clones."),
                mode="A",
            )
        )

    chsh_circuits = build_chsh_circuits()
    s = chsh_value({pair: run_counts(qc, witness_shots, backend) for pair, qc in chsh_circuits.items()})
    return frames, raw, s
