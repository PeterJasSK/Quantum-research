#!/usr/bin/env python3
"""

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
hardware. ``run_qalife.py`` runs the model live.

Usage:
    cd artificial-life/code
    python qalife.py --sim --width 4 --steps 6 --death both
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import random
from typing import Any

from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix, Statevector

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# ---- fixed physics constants (the EXACT 2018 model) --------------------------
AGING_DELTA = math.pi / 8      # per-time-step aging angle (paper: u3(pi/8,0,0))
DAMP_GAMMA = 0.18              # per-time-step amplitude-damping probability (aging rate)
ALIVE_THRESH = 0.80            # phenotype <sigma_z> >= this => at the |0> dark state => DEAD


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
    """'nn' = adjacent (k-1); 'longrange' = k + width//2 (distant partner, relevant at
    scale). None if no valid partner (avoids double-applying the SWAP)."""
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
                     measure: bool = False, annotate: bool = False) -> QuantumCircuit:
    """Full-model population line of `width` individuals after `steps` life-cycle steps.
    Individual k born at step k (age_k = max(0, steps-k)). death in {'unitary','damping'}.
    The long-range interaction SWAP is left plain -- the transpiler routes it as an
    O(distance) SWAP ladder. `annotate` inserts labeled barriers per Darwinian operator
    (for --dump-circuit)."""
    n_data = 2 * width + (1 if death == "damping" else 0)  # +1 shared bath (damping only)
    qc = QuantumCircuit(n_data, n_data if measure else 0)

    # genotype line + phenotype-with-death, one individual per step. g_k = 2k, p_k = 2k+1.
    z_geno = _z_geno_chain(width, thetas, founder_equator) if death == "unitary" else None
    bath = bath_q(width) if death == "damping" else None
    for k in range(width):
        g, p = geno_q(k), pheno_q(k)
        # FOUNDER (k=0, seed ancestral genotype on the equator) or SELF-REPLICATION
        # (k>0, partial sigma_z clone = bare CNOT, eta=1: <sigma_z>_child == <sigma_z>_parent)
        if k == 0:
            if founder_equator:
                qc.ry(math.pi / 2, g)
        else:
            qc.cx(geno_q(k - 1), g)
        qc.ry(thetas[k], g)                                      # MUTATION u3(theta,0,0) = Ry(theta)

        age = max(0, steps - k)
        if death == "unitary":
            # product-state phenotype: <sigma_z> = genotype value, aged toward |0> (angle->0)
            angle0 = math.acos(max(-1.0, min(1.0, z_geno[k])))   # Ry angle: <sigma_z>=cos(angle)
            aged = max(0.0, angle0 - delta * age)                # aging drives angle -> 0 (dark)
            qc.ry(aged, p)                                        # PHENOTYPE + DEATH(age)
        else:
            qc.cx(g, p)                                          # PHENOTYPE: 2nd partial clone (CNOT)
            # DEATH: true amplitude damping toward |0> (Lindblad sigma=|0><1|). Effective damping
            # over `age` steps g_eff = 1-(1-gamma)^age, one block via a shared bath ancilla.
            if age > 0:
                g_eff = 1.0 - (1.0 - gamma) ** age
                qc.cry(2.0 * math.asin(math.sqrt(min(1.0, g_eff))), p, bath)
                qc.cx(bath, p)
                qc.reset(bath)                                   # discard bath so it can be reused
        _bar(qc, annotate, f"ind{k}")

    # INTERACTION sweep (predation): U_I = SWAP the two phenotype qubits of each pair, once
    did_interaction = False
    for k in range(width):
        j = interaction_partner(k, width, interaction)
        if j is not None:
            qc.swap(pheno_q(k), pheno_q(j))
            did_interaction = True
    if did_interaction:
        _bar(qc, annotate, "interaction")

    if measure:
        qc.measure(range(qc.num_qubits), range(qc.num_qubits))
    return qc


# ---------------------------------------------------------------------------
# Observables + metrics
# ---------------------------------------------------------------------------
def phenotype_z_ideal(width: int, steps: int, thetas: list[float], interaction: str,
                      death: str, **kw) -> list[float]:
    """Ideal phenotype <sigma_z> per individual from the noiseless state (statevector for
    unitary, density-matrix for damping)."""
    qc = build_population(width, steps, thetas, interaction, death=death, measure=False, **kw)
    state = (DensityMatrix if death == "damping" else Statevector).from_instruction(qc)
    z = []
    for k in range(width):
        p = state.probabilities([pheno_q(k)])
        z.append(float(p[0] - p[1]))
    return z


def phenotype_z_from_counts(counts: dict[str, int], width: int) -> list[float]:
    """Phenotype <sigma_z> per individual from counts (little-endian bitstrings)."""
    total = sum(counts.values()) or 1
    out = []
    for k in range(width):
        q = pheno_q(k)
        p1 = sum(c for bits, c in counts.items() if bits[-(q + 1)] == "1") / total
        out.append(1.0 - 2.0 * p1)
    return out


def alive_population(pheno_z: list[float], thresh: float = ALIVE_THRESH) -> int:
    """Count alive individuals: phenotype NOT at the |0> dark state (<sigma_z> < thresh)."""
    return sum(1 for z in pheno_z if z < thresh)


def deepest_surviving_lineage(pheno_z: list[float], thresh: float = ALIVE_THRESH) -> int:
    """Largest k* s.t. individuals 0..k* are ALL alive (unbroken line). -1 if founder dead."""
    kstar = -1
    for k, z in enumerate(pheno_z):
        if z >= thresh:                 # dead -> line broken
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
# deepest width whose witness beats the separable null is the genealogical entanglement
# depth: the Month-4 headline, the real improvement over the 2018 base.
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


def _sim_thetas(width: int, seed: int, mut_scale: float = 1.0) -> list[float]:
    """PRNG mutation angles for --sim ONLY. Hardware draws from certified Q-EaaS
    (CD-7 fail-closed) in run_qalife."""
    rng = random.Random(seed)
    return [mut_scale * rng.uniform(0, math.pi) for _ in range(width)]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 4 -- the full 2018 model (sim)")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--death", choices=["unitary", "damping", "both"], default="both")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="qalife_s4_sim")
    args = ap.parse_args()

    if not args.sim:
        print("nothing to do: pass --sim"); raise SystemExit(1)

    thetas = _sim_thetas(args.width, args.seed)
    inter_arms = ["nn", "longrange"]                    # both interaction topologies
    death_arms = ["unitary", "damping"] if args.death == "both" else [args.death]

    result: dict[str, Any] = {
        "meta": {"stage": 4, "model": "AlvarezRodriguez2018_full", "width": args.width,
                 "steps": args.steps, "delta": AGING_DELTA, "gamma": DAMP_GAMMA,
                 "alive_thresh": ALIVE_THRESH, "founder_equator": True,
                 "seed": args.seed, "sim": True,
                 "operators": "CNOT-clone / Ry-mutation / {damping|unitary}-death / SWAP-interaction"},
        "arms": {},
    }

    print(f"=== Stage 4 full-model sim: width={args.width} steps={args.steps} "
          f"death={args.death} ===")
    for death in death_arms:
        for inter in inter_arms:
            pz = phenotype_z_ideal(args.width, args.steps, thetas, inter, death=death)
            cz = classical_surrogate_z(args.width, args.steps, thetas, inter, death=death)
            key = f"{death}/{inter}"
            result["arms"][key] = {
                "pheno_z": pz, "classical_z": cz,
                "alive_population": alive_population(pz),
                "deepest_lineage": deepest_surviving_lineage(pz),
                "classical_alive": alive_population(cz),
                "classical_deepest": deepest_surviving_lineage(cz),
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
