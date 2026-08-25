#!/usr/bin/env python3
"""Stage 4 (QDEP: the FULL Alvarez-Rodriguez 2018 quantum-artificial-life model, at scale).

Month 4 re-targets the study. Months 1-3 collapsed 2018 to a single temporal clone
lineage measuring C(g) -- a depth benchmark of no scientific value, and a model missing
two of the four biomimetic operators. Stage 4 rebuilds the WHOLE model faithfully and
lays it out as a *population line* so it can scale to the largest healthy line a
156-qubit Heron-r2 sustains (the hardware driver is ``stage4_scale.py``).

The EXACT 2018 operators (Sci. Rep. 8:14793, 2018), reproduced here:

  * individual = 2 qubits: genotype g (inherited <sigma_z>) + phenotype p (lifetime).
  * self-replication  = CNOT partial sigma_z-clone, applied TWICE: g_parent->g_child
    (blank) then g_child->p_child (blank). Exact <sigma_z> copy, eta = 1 (NO
    contraction -- the Months 1-3 ``eta=0.9`` was a stand-in; the paper's cloning is a
    bare CNOT and the degradation comes from AGING, not lossy cloning).
  * mutation          = u3(theta,0,0) = Ry(theta) on the genotype.
  * death / aging     = dissipation toward the |0> dark state (Lindblad sigma=|0><1|).
    TWO faithful implementations, switchable via --death:
      - 'damping' : true amplitude damping via a bath ancilla (CRY + CX + discard).
        Keeps the CNOT-entangled phenotype; the paper's ACTUAL model. Needs a bath
        qubit + density-matrix sim. On 2017 ibmqx4 this was impossible, so the paper
        substituted sigma_y rotations -- we can now do the real channel.
      - 'unitary' : the paper's sigma_y-rotation stand-in, on a PRODUCT-STATE phenotype
        (prepared from the genotype's diagonal <sigma_z>) so the unitary actually drives
        it to the dark state. Cheap (2 qubits/individual, pure statevector), scalable;
        drops the phenotype's inheritance-entanglement.
  * interaction  U_I  = SWAP of the two phenotype qubits of the interacting pair (each
    individual's phenotype ends reflecting the OPPOSITE genotype -- predation/exchange).

This file is self-contained (CD-1: operators copied, not imported) and hits NOTHING on
hardware. ``--selftest`` verifies every operator against the paper's exact values; only
after it passes does ``stage4_scale.py`` run the model live.

Usage:
    cd artificial-life/code
    python stage4_qalife.py --selftest
    python stage4_qalife.py --sim --width 4 --steps 6 --interaction both --death both
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import random
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import DensityMatrix, SparsePauliOp, Statevector

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# ---- fixed physics constants (the EXACT 2018 model) --------------------------
AGING_DELTA = math.pi / 8      # per-time-step aging angle (paper: u3(pi/8,0,0))
DAMP_GAMMA = 0.18              # per-time-step amplitude-damping probability (aging rate)
ALIVE_THRESH = 0.80            # phenotype <sigma_z> >= this => at the |0> dark state => DEAD


# ---------------------------------------------------------------------------
# The four EXACT 2018 operators
# ---------------------------------------------------------------------------
def apply_self_replication(qc: QuantumCircuit, parent_geno: int, child_geno: int) -> None:
    """Partial sigma_z clone: CNOT(parent_geno -> child_geno), child_geno blank |0>.
    cos t|0>+sin t|1> parent, |0> blank -> cos t|00>+sin t|11>, so <sigma_z>_child ==
    <sigma_z>_parent exactly (eta = 1, the paper's bare CNOT clone)."""
    qc.cx(parent_geno, child_geno)


def apply_mutation(qc: QuantumCircuit, geno: int, theta: float) -> None:
    """Mutation u3(theta,0,0) = Ry(theta) on the genotype."""
    qc.ry(theta, geno)


def apply_phenotype_clone(qc: QuantumCircuit, geno: int, pheno: int) -> None:
    """Second partial clone: CNOT(geno -> pheno), pheno blank |0> (damping arm)."""
    qc.cx(geno, pheno)


def apply_aging_damping(qc: QuantumCircuit, pheno: int, bath: int, age: int,
                        gamma: float = DAMP_GAMMA) -> None:
    """True amplitude damping of the phenotype toward |0> (Lindblad sigma=|0><1|).
    Effective damping over `age` steps: g_eff = 1-(1-gamma)^age, applied as one block:
      CRY(2*asin(sqrt(g_eff)), pheno->bath) ; CX(bath->pheno) ; then bath is discarded/reset.
    Traces to the amplitude-damping channel; drives |1> population -> |0> (death)."""
    if age <= 0:
        return
    g_eff = 1.0 - (1.0 - gamma) ** age
    qc.cry(2.0 * math.asin(math.sqrt(min(1.0, g_eff))), pheno, bath)
    qc.cx(bath, pheno)
    qc.reset(bath)                      # discard the bath so it can be reused


def apply_interaction(qc: QuantumCircuit, pheno_a: int, pheno_b: int) -> None:
    """Interaction U_I: SWAP the two phenotype qubits (the paper's Table-1 exchange)."""
    qc.swap(pheno_a, pheno_b)


# ---------------------------------------------------------------------------
# Long-range interaction routing (Phase-2b): SWAP vs teleport.
# _swap_cx / _teleport_cx copied verbatim from stage3_teleport.py (CD-1: copied,
# not imported). S4's long-range interaction is a phenotype SWAP; we realize it as
# three routed CNOTs so the same primitive that routed the S3 clone bond routes it.
# ---------------------------------------------------------------------------
def _swap_cx(qc: QuantumCircuit, lo: int, hi: int) -> None:
    """Long-range CNOT(lo -> hi), lo < hi, via a SWAP ladder (O(distance) depth).
    Verbatim from stage3_teleport.py:315 (QuantumLife research_qtree_swaplr.py:173)."""
    for p in range(lo, hi - 1):
        qc.swap(p, p + 1)
    qc.cx(hi - 1, hi)
    for p in range(hi - 1, lo, -1):
        qc.swap(p - 1, p)


def _teleport_cx(qc: QuantumCircuit, ctrl: int, tgt: int, a1: int, a2: int,
                 tel: Any, k: int, feedforward: bool = True) -> None:
    """Long-range CNOT(ctrl -> tgt) via one Bell pair + two mid-circuit measures +
    classical feed-forward -> valid CX at CONSTANT depth, ctrl/tgt never made neighbours.
    Verbatim from stage3_teleport.py:330 (QuantumLife research_qtree_teleport.py:201).
    Ancillas a1 (near ctrl) / a2 (near tgt); tel[2k], tel[2k+1] hold the outcomes."""
    qc.h(a1)
    qc.cx(a1, a2)                       # Bell pair spans the register
    qc.cx(ctrl, a1)                     # inject control's parity
    qc.measure(a1, tel[2 * k])
    if feedforward:
        with qc.if_test((tel[2 * k], 1)):   # feed-forward X
            qc.x(a2)
    qc.cx(a2, tgt)                      # a2 acts as the control next to tgt
    qc.h(a2)
    qc.measure(a2, tel[2 * k + 1])
    if feedforward:
        with qc.if_test((tel[2 * k + 1], 1)):  # feed-forward Z
            qc.z(ctrl)


def apply_interaction_teleport(qc: QuantumCircuit, pheno_a: int, pheno_b: int,
                               a1: int, a2: int, tel: Any, kbase: int,
                               feedforward: bool = True) -> None:
    """Interaction U_I realized as a teleport-routed SWAP: SWAP(a,b) = CX(a,b) CX(b,a)
    CX(a,b), each long-range CNOT teleported at constant depth over the shared corridor
    (a1, a2). The corridor is reset between CNOTs so one ancilla pair serves the bond.
    Consumes tel[2*kbase .. 2*kbase+5] (2 outcomes per CNOT)."""
    _teleport_cx(qc, pheno_a, pheno_b, a1, a2, tel, kbase + 0, feedforward)
    qc.reset([a1, a2])
    _teleport_cx(qc, pheno_b, pheno_a, a1, a2, tel, kbase + 1, feedforward)
    qc.reset([a1, a2])
    _teleport_cx(qc, pheno_a, pheno_b, a1, a2, tel, kbase + 2, feedforward)


def _longrange_bonds(width: int, interaction: str) -> list[tuple[int, int]]:
    """The (k, j) phenotype pairs the long-range interaction sweep swaps, each once
    (j = k + width//2 > k). Used to size the teleport corridor ancillas + tel register."""
    bonds: list[tuple[int, int]] = []
    for k in range(width):
        j = interaction_partner(k, width, interaction)
        if j is not None and j > k:
            bonds.append((k, j))
    return bonds


# ---------------------------------------------------------------------------
# Layout: individual k = offspring of k-1; the line IS the genealogy
# ---------------------------------------------------------------------------
def geno_q(k: int) -> int:
    return 2 * k


def pheno_q(k: int) -> int:
    return 2 * k + 1


def bath_q(width: int) -> int:
    """Single shared bath ancilla (reused with reset), only for the damping arm."""
    return 2 * width


def interaction_partner(k: int, width: int, mode: str) -> int | None:
    """'nn' = adjacent (k-1); 'longrange' = k + width//2 (distant -> routing/teleport
    relevant at scale). None if no valid partner (avoids double-applying the SWAP)."""
    if mode == "none":
        return None
    if mode == "nn":
        return k - 1 if k >= 1 else None
    if mode == "longrange":
        j = k + width // 2
        return j if (width // 2 >= 1 and j < width) else None
    raise ValueError(f"unknown interaction mode {mode!r}")


def _z_geno_chain(width: int, thetas: list[float], founder_equator: bool) -> list[float]:
    """Analytic genotype <sigma_z> along the line (founder equator=0; CNOT copy eta=1;
    mutation Ry(theta): <sigma_z> -> cos(theta)*<sigma_z>). Used to prepare the unitary
    arm's product-state phenotype and for the classical surrogate."""
    z = [0.0] * width
    for k in range(width):
        base = 0.0 if (k == 0 and founder_equator) else (1.0 if k == 0 else z[k - 1])
        z[k] = math.cos(thetas[k]) * base
    return z


def _bar(qc: QuantumCircuit, annotate: bool, label: str) -> None:
    """Labeled barrier for circuit analysis (--dump-circuit); no-op otherwise."""
    if annotate:
        try:
            qc.barrier(label=label)
        except TypeError:                        # older qiskit: barrier without label
            qc.barrier()


def build_population(width: int, steps: int, thetas: list[float], interaction: str,
                     death: str = "unitary", founder_equator: bool = True,
                     delta: float = AGING_DELTA, gamma: float = DAMP_GAMMA,
                     measure: bool = False, annotate: bool = False,
                     routing: str = "swap", feedforward: bool = True) -> QuantumCircuit:
    """Full-model population line of `width` individuals after `steps` life-cycle steps.
    Individual k born at step k (age_k = max(0, steps-k)). death in {'unitary','damping'}.
    `annotate` inserts labeled barriers per Darwinian operator (for --dump-circuit).
    `routing` selects how the long-range interaction SWAP is realized on the chip:
    'swap' = plain SWAP (transpiler routes an O(distance) ladder); 'teleport' = each SWAP
    teleport-routed at constant depth (+2 corridor ancillas + a 'tel' feed-forward register
    per long-range bond). Teleport only applies to interaction='longrange'."""
    n_data = 2 * width + (1 if death == "damping" else 0)  # +1 shared bath (damping only)
    use_teleport = (routing == "teleport" and interaction == "longrange")

    tel = None
    if use_teleport:
        bonds = _longrange_bonds(width, interaction)
        n_anc = 2 * len(bonds)                    # 2 corridor ancillas per teleported bond
        anc_base = n_data
        qr = QuantumRegister(n_data + n_anc, "q")
        regs: list[Any] = [qr]
        if bonds:
            tel = ClassicalRegister(2 * 3 * len(bonds), "tel")  # 3 CNOTs/SWAP, 2 bits each
            regs.append(tel)
        if measure:
            regs.append(ClassicalRegister(n_data + n_anc, "c"))
        qc = QuantumCircuit(*regs)
    else:
        nq = n_data
        qc = QuantumCircuit(nq, nq if measure else 0)

    if death == "unitary":
        # product-state phenotype: <sigma_z> = genotype value, aged toward |0> (angle->0)
        z_geno = _z_geno_chain(width, thetas, founder_equator)
        # still build the genotype line (for a faithful genealogy + interaction on genotypes)
        for k in range(width):
            if k == 0:
                if founder_equator:
                    qc.ry(math.pi / 2, geno_q(0))     # FOUNDER: seed the ancestral genotype
            else:
                apply_self_replication(qc, geno_q(k - 1), geno_q(k))  # SELF-REPLICATION
            apply_mutation(qc, geno_q(k), thetas[k])                  # MUTATION
            # phenotype prepared as an aged product state (DEATH folded into the prep angle)
            age = max(0, steps - k)
            angle0 = math.acos(max(-1.0, min(1.0, z_geno[k])))   # Ry angle: <sigma_z>=cos(angle)
            aged = max(0.0, angle0 - delta * age)                # aging drives angle -> 0 (dark)
            qc.ry(aged, pheno_q(k))                               # PHENOTYPE + DEATH(age)
            _bar(qc, annotate, f"ind{k}")
    else:  # damping
        bath = bath_q(width)
        for k in range(width):
            if k == 0:
                if founder_equator:
                    qc.ry(math.pi / 2, geno_q(0))                     # FOUNDER
            else:
                apply_self_replication(qc, geno_q(k - 1), geno_q(k))  # SELF-REPLICATION
            apply_mutation(qc, geno_q(k), thetas[k])                  # MUTATION
            apply_phenotype_clone(qc, geno_q(k), pheno_q(k))          # PHENOTYPE (2nd clone)
            age = max(0, steps - k)
            apply_aging_damping(qc, pheno_q(k), bath, age, gamma)     # DEATH (amplitude damping)
            _bar(qc, annotate, f"ind{k}")

    # interaction sweep (phenotype exchange), after the line is built
    did_interaction = False
    if use_teleport:
        bonds = _longrange_bonds(width, interaction)
        anc_base = n_data
        for i, (k, j) in enumerate(bonds):
            apply_interaction_teleport(qc, pheno_q(k), pheno_q(j),           # INTERACTION,
                                       a1=anc_base + 2 * i, a2=anc_base + 2 * i + 1,  # teleport-
                                       tel=tel, kbase=3 * i, feedforward=feedforward)  # routed
            did_interaction = True
    else:
        for k in range(width):
            j = interaction_partner(k, width, interaction)
            if j is not None:
                apply_interaction(qc, pheno_q(k), pheno_q(j))         # INTERACTION (predation)
                did_interaction = True
    if did_interaction:
        _bar(qc, annotate, "interaction")

    if measure:
        qc.measure(range(qc.num_qubits), range(qc.num_qubits))
    return qc


# ---------------------------------------------------------------------------
# Observables + metrics
# ---------------------------------------------------------------------------
def _z_expectation(qc: QuantumCircuit, qubit: int, dm: bool = False) -> float:
    """<sigma_z> of `qubit` on the noiseless (pure or density-matrix) state of `qc`."""
    state = DensityMatrix.from_instruction(qc) if dm else Statevector.from_instruction(qc)
    probs = state.probabilities([qubit])
    return float(probs[0] - probs[1])


def phenotype_z_ideal(width: int, steps: int, thetas: list[float], interaction: str,
                      death: str, **kw) -> list[float]:
    """Ideal phenotype <sigma_z> vector (statevector for unitary, density-matrix for damping)."""
    qc = build_population(width, steps, thetas, interaction, death=death, measure=False, **kw)
    use_dm = (death == "damping")
    return [_z_expectation(qc, pheno_q(k), dm=use_dm) for k in range(width)]


def phenotype_z_from_counts(counts: dict[str, int], width: int) -> list[float]:
    """Phenotype <sigma_z> per individual from counts (little-endian bitstrings)."""
    total = sum(counts.values()) or 1
    out = []
    for k in range(width):
        q = pheno_q(k)
        p1 = sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total
        out.append(1.0 - 2.0 * p1)
    return out


def alive_mask(pheno_z: list[float], thresh: float = ALIVE_THRESH) -> list[bool]:
    """Alive = phenotype NOT at the |0> dark state (<sigma_z> < thresh)."""
    return [z < thresh for z in pheno_z]


def alive_population(pheno_z: list[float], thresh: float = ALIVE_THRESH) -> int:
    return sum(alive_mask(pheno_z, thresh))


def deepest_surviving_lineage(pheno_z: list[float], thresh: float = ALIVE_THRESH) -> int:
    """Largest k* s.t. individuals 0..k* are ALL alive (unbroken line). -1 if founder dead."""
    kstar = -1
    for k, a in enumerate(alive_mask(pheno_z, thresh)):
        if not a:
            break
        kstar = k
    return kstar


# ---------------------------------------------------------------------------
# Genealogical entanglement witness  <sigma_x ... sigma_x>  (the QUANTUM headline)
# ---------------------------------------------------------------------------
# The CNOT-clone chain entangles the genotype line into a GHZ-like state: the founder |+>
# spread across generations gives (|0..0>+|1..1>)/sqrt2, whose <X^{otimes n}> = 1. A
# separable / measure-and-resend state factorizes: <X^{otimes n}> = prod_i <X>_i ~ 0. So the
# joint X-parity over the genealogy is a genuine entanglement witness with NO classical
# surrogate -- exactly the 2018 paper's "entanglement spreads throughout generations". The
# deepest generation g whose witness beats the separable null is the genealogical
# entanglement depth: the Month-4 headline, the real improvement over the 2018 base.
def _x_string_op(nq: int, qubits: list[int]) -> SparsePauliOp:
    label = ["I"] * nq
    for q in qubits:
        label[nq - 1 - q] = "X"            # SparsePauliOp label is qubit n-1 .. 0
    return SparsePauliOp("".join(label))


def witness_ideal_by_gen(width: int, steps: int, thetas: list[float], interaction: str,
                         death: str = "unitary", **kw) -> list[float]:
    """Ideal genealogical witness <X^{otimes(g+1)}> over the genotype line, for every
    generation depth g. Each depth is its OWN width-(g+1) genealogy (a prefix of a GHZ is
    mixed and reads 0 -- the witness only lives on the full entangled set), so we build a
    fresh sub-population per g. As g grows, mutation + aging + (on HW) noise shrink it."""
    out = []
    for g in range(width):
        w = g + 1
        qc = build_population(w, steps, thetas[:w], interaction, death=death, measure=False, **kw)
        state = DensityMatrix.from_instruction(qc) if death == "damping" \
            else Statevector.from_instruction(qc)
        op = _x_string_op(qc.num_qubits, [geno_q(k) for k in range(w)])
        out.append(float(np.real(state.expectation_value(op))))
    return out


def xbasis_witness_from_counts(counts: dict[str, int], qubits: list[int]) -> tuple[float, float]:
    """From X-basis counts (H applied before Z-readout): return (joint, separable) where
    joint = <prod_i x_i> (the entanglement witness) and separable = prod_i <x_i> (the
    factorized null a classical device gives). joint - separable is the entanglement signal."""
    total = sum(counts.values()) or 1
    joint = 0.0
    per = [0.0] * len(qubits)
    for bits, c in counts.items():
        prod = 1
        for i, q in enumerate(qubits):
            s = 1 - 2 * (bits[-(q + 1)] == "1")
            prod *= s
            per[i] += s * c
        joint += prod * c
    joint /= total
    per = [p / total for p in per]
    sep = 1.0
    for p in per:
        sep *= p
    return joint, sep


def entanglement_depth(witness_by_gen: list[float], sep_by_gen: list[float],
                       sigma: list[float], k: float = 2.0) -> int:
    """Deepest generation g whose witness beats the separable null by k*sigma. -1 if none."""
    depth = -1
    for g in range(len(witness_by_gen)):
        if witness_by_gen[g] - sep_by_gen[g] > k * sigma[g]:
            depth = g
        else:
            break
    return depth


def classical_surrogate_z(width: int, steps: int, thetas: list[float], interaction: str,
                          death: str = "unitary", founder_equator: bool = True,
                          delta: float = AGING_DELTA, gamma: float = DAMP_GAMMA) -> list[float]:
    """Separable null MATCHED to the arm's death channel: classical genotype copy, phenotype
    tracks genotype <sigma_z>, aging applied classically (unitary tilt OR diagonal amplitude
    damping), interaction swaps phenotype values. No entanglement (analytic).

    NB: because CNOT-copy, amplitude-damping, and phenotype-SWAP all act ONLY on the diagonal,
    the matched classical surrogate reproduces the quantum phenotype <sigma_z> EXACTLY -- i.e.
    the alive-count / deepest-lineage metrics are CLASSICAL observables (Delta ~ 0). A genuine
    quantum-life claim needs the off-diagonal genealogical entanglement witness (<sigma_x ...>),
    not this diagonal metric. See RUNLOG_MONTH4 'the entanglement witness' note."""
    z_geno = _z_geno_chain(width, thetas, founder_equator)
    z_pheno = []
    for k in range(width):
        age = max(0, steps - k)
        z0 = z_geno[k]
        if death == "damping":
            p1 = (1.0 - z0) / 2.0                       # |1> population
            p1 *= (1.0 - gamma) ** age                  # classical amplitude damping toward |0>
            z_pheno.append(1.0 - 2.0 * p1)
        else:
            angle = max(0.0, math.acos(max(-1.0, min(1.0, z0))) - delta * age)
            z_pheno.append(math.cos(angle))
    for k in range(width):
        j = interaction_partner(k, width, interaction)
        if j is not None and j > k:
            z_pheno[k], z_pheno[j] = z_pheno[j], z_pheno[k]
    return z_pheno


# ---------------------------------------------------------------------------
# Self-test: every operator against the paper's EXACT values
# ---------------------------------------------------------------------------
def selftest() -> bool:
    ok = True

    # A. self-replication: CNOT copies <sigma_z> exactly (eta = 1)
    for a in (0.3, 0.7, 1.2, math.pi / 3):
        qc = QuantumCircuit(2)
        qc.ry(2 * a, 0)
        apply_self_replication(qc, 0, 1)
        if abs(_z_expectation(qc, 1) - math.cos(2 * a)) > 1e-9:
            print(f"  [FAIL] self-replication a={a}"); ok = False
    print("  self-replication: CNOT copies <sigma_z> exactly (eta=1)  OK")

    # B. interaction U_I = phenotype SWAP: each pheno reflects the OPPOSITE genotype
    t1, t2 = math.pi / 8, 3 * math.pi / 8
    qc = QuantumCircuit(4)
    qc.ry(2 * t1, 0); qc.cx(0, 1)
    qc.ry(2 * t2, 2); qc.cx(2, 3)
    apply_interaction(qc, 1, 3)
    if abs(_z_expectation(qc, 1) - math.cos(2 * t2)) > 1e-9 or \
       abs(_z_expectation(qc, 3) - math.cos(2 * t1)) > 1e-9:
        print("  [FAIL] interaction SWAP"); ok = False
    else:
        print("  interaction: U_I swaps phenotypes (each reflects opposite genotype)  OK")

    # C1. aging (unitary, product-state phenotype): monotone -> dark state |0> (<sigma_z>->+1)
    zc = []
    for steps in range(0, 9):
        pz = phenotype_z_ideal(1, steps, [math.pi / 2], "none", death="unitary")
        zc.append(pz[0])
    if any(zc[i + 1] < zc[i] - 1e-9 for i in range(len(zc) - 1)) or zc[-1] < 0.9:
        print(f"  [FAIL] unitary aging not monotone->dark: {[round(z,3) for z in zc]}"); ok = False
    else:
        print("  aging(unitary): product phenotype -> |0> dark state monotonically  OK")

    # C2. aging (damping, entangled phenotype): monotone -> dark state via amplitude damping
    zd = []
    for steps in range(0, 22):
        pz = phenotype_z_ideal(1, steps, [math.pi / 2], "none", death="damping")
        zd.append(pz[0])
    if any(zd[i + 1] < zd[i] - 1e-6 for i in range(len(zd) - 1)) or zd[-1] < 0.9:
        print(f"  [FAIL] damping aging not monotone->dark: {[round(z,3) for z in zd]}"); ok = False
    else:
        print("  aging(damping): entangled phenotype -> |0> dark state via amplitude damping  OK")

    # E. genealogical entanglement witness: clean GHZ prefix -> <X^n> = 1 (no mutation/aging)
    w = witness_ideal_by_gen(4, 0, [0.0, 0.0, 0.0, 0.0], "none", death="unitary")
    if any(abs(wg - 1.0) > 1e-9 for wg in w):
        print(f"  [FAIL] witness GHZ prefix != 1: {[round(x,3) for x in w]}"); ok = False
    else:
        print("  witness: GHZ genealogy <X^n> = 1 at every generation depth  OK")
    # separable null on a product X-eigenstate: joint == separable (no entanglement signal)
    fake = {"0000": 250, "0101": 250, "1010": 250, "1111": 250}   # independent bits
    j, s = xbasis_witness_from_counts(fake, [0, 1])
    if abs(j - s) > 1e-9:
        print(f"  [FAIL] separable witness joint({j:.3f}) != sep({s:.3f})"); ok = False
    else:
        print("  witness: separable state gives joint == product (zero entanglement signal)  OK")

    # D. metrics
    if alive_population([0.0] * 5) != 5:
        print("  [FAIL] alive_population"); ok = False
    if deepest_surviving_lineage([0.0, 0.0, 0.95, 0.0, 0.0]) != 1:
        print("  [FAIL] deepest_lineage"); ok = False
    print("  metrics: alive-population + deepest-lineage  OK")

    print(f"\n  SELFTEST {'PASS' if ok else 'FAIL'}")
    return ok


def _sim_thetas(width: int, seed: int, mut_scale: float = 1.0) -> list[float]:
    """PRNG mutation angles for --sim/--selftest ONLY. Hardware draws from certified Q-EaaS
    (CD-7 fail-closed) in stage4_scale."""
    rng = random.Random(seed)
    return [mut_scale * rng.uniform(0, math.pi) for _ in range(width)]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 4 -- the full 2018 model (sim + selftest)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--interaction", choices=["none", "nn", "longrange", "both"], default="both")
    ap.add_argument("--death", choices=["unitary", "damping", "both"], default="both")
    ap.add_argument("--delta", type=float, default=AGING_DELTA)
    ap.add_argument("--gamma", type=float, default=DAMP_GAMMA)
    ap.add_argument("--alive-thresh", dest="alive_thresh", type=float, default=ALIVE_THRESH)
    ap.add_argument("--no-founder-equator", dest="founder_equator", action="store_false", default=True)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="qalife_s4_sim")
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(0 if selftest() else 1)
    if not args.sim:
        print("nothing to do: pass --selftest or --sim"); raise SystemExit(1)

    thetas = _sim_thetas(args.width, args.seed)
    inter_arms = ["nn", "longrange"] if args.interaction == "both" else [args.interaction]
    death_arms = ["unitary", "damping"] if args.death == "both" else [args.death]

    result: dict[str, Any] = {
        "meta": {"stage": 4, "model": "AlvarezRodriguez2018_full", "width": args.width,
                 "steps": args.steps, "delta": args.delta, "gamma": args.gamma,
                 "alive_thresh": args.alive_thresh, "founder_equator": args.founder_equator,
                 "seed": args.seed, "sim": True,
                 "operators": "CNOT-clone / Ry-mutation / {damping|unitary}-death / SWAP-interaction"},
        "arms": {},
    }

    print(f"=== Stage 4 full-model sim: width={args.width} steps={args.steps} "
          f"interaction={args.interaction} death={args.death} ===")
    for death in death_arms:
        for inter in inter_arms:
            pz = phenotype_z_ideal(args.width, args.steps, thetas, inter, death=death,
                                   founder_equator=args.founder_equator, delta=args.delta,
                                   gamma=args.gamma)
            cz = classical_surrogate_z(args.width, args.steps, thetas, inter, death=death,
                                       founder_equator=args.founder_equator, delta=args.delta,
                                       gamma=args.gamma)
            key = f"{death}/{inter}"
            result["arms"][key] = {
                "pheno_z": pz, "classical_z": cz,
                "alive_population": alive_population(pz, args.alive_thresh),
                "deepest_lineage": deepest_surviving_lineage(pz, args.alive_thresh),
                "classical_alive": alive_population(cz, args.alive_thresh),
                "classical_deepest": deepest_surviving_lineage(cz, args.alive_thresh),
            }
            r = result["arms"][key]
            print(f"  [{key:18}] quantum alive={r['alive_population']}/{args.width} "
                  f"deepest={r['deepest_lineage']}  | classical alive={r['classical_alive']} "
                  f"deepest={r['classical_deepest']}")
            print(f"      pheno <sigma_z>: " + ", ".join(f"{z:+.2f}" for z in pz))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, f"{args.name}_w{args.width}_s{args.steps}_sim.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
