"""F4 Mode-A hybrid loop (plan §4, AC-2/AC-3/AC-4).

The living-process core. Each generation is a SEPARATE constant-depth quantum job
(measure-and-restart = Mode A; survives the coherence-depth wall). Per generation,
per lineage:

    quantum : prep parent genotype -> divide (P1) -> daughter fate (P2) -> measure
    host    : decode candidates -> classical fitness -> keep top `survivors` ->
              seed generation g+1 from the best survivor's MEASURED bits (Z basis)

Generation 0 is the founder: the genotype is encoded straight from the rulebook
(reusing f1_quantum.circuit._encode_properties) with no division; `offspring` shots
give `offspring` founder candidates. Generations > 0 seed the parent from the previous
survivor's measured genotype via X gates (AC-3) and apply the P1 division.

Reuses F1 verbatim: `_encode_properties` (genotype), `bits_to_params`/`_str_to_bits`
(decode), `N_PROP` (register width). No edits to f1_quantum. Honest label: quantum
within a generation, classical genealogy.
"""

from __future__ import annotations

import math

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from common.datamodel import GenerationRecord, TumorParams
from f1_quantum.backend import flatten_counts, run_counts
from f1_quantum.circuit import N_PROP, _encode_properties
from f1_quantum.decode import _str_to_bits, bits_to_params
from f1_quantum.lineage import DEFAULT_THETA_MUT
from f1_quantum.rulebook import Rulebook, angles_from_rulebook
from f4_qalife import fitness
from f4_qalife.witness import witness_value

# P2 fate: f0 carries a Ramsey interferometer (h - rz(phase) - h) so the phase dial is
# observable in the Z measurement; f1 is a static equal spread. fate = (f0<<1)|f1, so
# phase sweeps the fate mix from proliferative/quiescent (phase 0) toward necrotic.
THETA_FATE = math.pi / 2


def _fate_prep(qc: QuantumCircuit, f0, f1, phase: float) -> None:
    """P2 fate sub-register: superposition over fates + phase dial (AC-4)."""
    qc.h(f0)
    qc.rz(phase, f0)   # interference knob — biases P(fate) before measurement commits it
    qc.h(f0)
    qc.ry(THETA_FATE, f1)


def build_founder_circuit(angles: dict, phase: float) -> QuantumCircuit:
    """Generation-0 founder: rulebook genotype (9q) + fate (2q), one shot = one cell."""
    prop = QuantumRegister(N_PROP, "prop")
    fate = QuantumRegister(2, "fate")
    c = ClassicalRegister(N_PROP + 2, "c")  # low 9 = genotype, high 2 = fate (backend reads `c`)
    qc = QuantumCircuit(prop, fate, c)
    _encode_properties(qc, angles, base=0)
    _fate_prep(qc, fate[0], fate[1], phase)
    qc.measure(prop, c[:N_PROP])
    qc.measure(fate, c[N_PROP:])
    return qc


def build_division_circuit(parent_bits: list[int], theta_mut: float, phase: float) -> QuantumCircuit:
    """Generation>0: seed parent from survivor bits (Z basis), divide (P1), fate (P2).

    The recorded candidate is the DAUGHTER (the offspring) — parent is a known seed.
    """
    parent = QuantumRegister(N_PROP, "parent")
    daughter = QuantumRegister(N_PROP, "daughter")
    fate = QuantumRegister(2, "fate")
    c = ClassicalRegister(N_PROP + 2, "c")
    qc = QuantumCircuit(parent, daughter, fate, c)
    for i, b in enumerate(parent_bits):
        if b:
            qc.x(parent[i])                 # measure-and-restart seed (AC-3)
    for i in range(N_PROP):
        qc.cx(parent[i], daughter[i])       # P1 controlled-copy
        qc.ry(theta_mut, daughter[i])       # P1 mutation
    _fate_prep(qc, fate[0], fate[1], phase)
    qc.measure(daughter, c[:N_PROP])        # record the offspring
    qc.measure(fate, c[N_PROP:])
    return qc


def _decode_candidate(word: str, rulebook: Rulebook, lineage_id: str,
                      generation: int, order: int) -> dict:
    """One measured 11-bit word -> candidate dict (cell, fate, raw genotype bits, score)."""
    bits = _str_to_bits(word, N_PROP + 2)
    geno_bits = bits[:N_PROP]
    fate = fitness.decode_fate(bits[N_PROP], bits[N_PROP + 1])
    cell = bits_to_params(
        geno_bits, rulebook,
        lineage_id=lineage_id, generation=generation, shot_index=-1,  # assigned on survival
    )
    return {
        "cell": cell,
        "fate": fate,
        "geno_bits": geno_bits,
        "word": word,
        "order": order,
        "score": fitness.score(cell.size_mm, fate),
    }


def run_mode_a(
    rulebook: Rulebook,
    *,
    founders: int = 4,
    generations: int = 3,
    survivors: int = 1,
    offspring: int = 4,
    theta_mut: float = DEFAULT_THETA_MUT,
    phase: float = 0.0,
    shots: int = 4096,          # kept for signature parity; offspring drives candidate count
    witness_shots: int = 4096,
    backend=None,
) -> tuple[list[TumorParams], list[GenerationRecord], list[str]]:
    """Run the Mode-A loop. Returns (cells, generation_records, raw_survivor_words).

    Cohort size = founders * generations * survivors (default 4*3*1 = 12 tiles).
    """
    if offspring < survivors:
        raise ValueError("offspring must be >= survivors (nothing to select from)")

    angles = angles_from_rulebook(rulebook)
    cells: list[TumorParams] = []
    records: list[GenerationRecord] = []
    raw_bits: list[str] = []
    parent_bits: dict[str, list[int]] = {}  # lineage_id -> best survivor's genotype bits
    shot = 0

    for g in range(generations):
        gen_survivors = 0
        for f in range(founders):
            lineage_id = f"ql{f}"
            if g == 0:
                qc = build_founder_circuit(angles, phase)
            else:
                qc = build_division_circuit(parent_bits[lineage_id], theta_mut, phase)

            counts = run_counts(qc, offspring, backend)
            words = flatten_counts(counts)[:offspring]
            candidates = [
                _decode_candidate(w, rulebook, lineage_id, g, k)
                for k, w in enumerate(words)
            ]
            kept = fitness.select(candidates, survivors)

            for cand in kept:
                cand["cell"].shot_index = shot
                cells.append(cand["cell"])
                raw_bits.append(cand["word"])
                shot += 1
                gen_survivors += 1

            # seed generation g+1 from the single best survivor (top-ranked) of this lineage
            parent_bits[lineage_id] = kept[0]["geno_bits"]

        w_val, xx, zz = witness_value(theta_mut, witness_shots, backend)
        records.append(
            GenerationRecord(
                generation=g,
                n_cells=founders * offspring,
                survivors=gen_survivors,
                witness_value=w_val,
                xx=xx,
                zz=zz,
                phase=phase,
            )
        )

    return cells, records, raw_bits
