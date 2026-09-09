#!/usr/bin/env python3
"""Stage 0 (QDEP: Coherence Depth of an Inherited-Entanglement Genealogy).

S0 is the toolchain-proving checkpoint. It rebuilds the Alvarez-Rodriguez et al.
(2018) single-lineage "quantum biomimetic" result with the *exact* operators, runs
it on a noiseless statevector simulator, and shows the phenotype "lifetime"
observable ``<sigma_z>_p`` decaying across generations in agreement with the ideal
model (metric M1). No correlation metric, no surrogate arm, no QRNG, no hardware --
those are S1+ (see epic-qdep-coherence-depth-genealogy.md).

It fixes three things the rest of the epic depends on and must not re-derive:
  1. the mutation operator ``M(theta)`` and the approximate-clone unitary ``U_M``;
  2. the genotype->phenotype ancilla map producing the trait ``<sigma_z>_p`` (CD-3);
  3. the ``research_runs/*.json`` output shape for ``meta.arm = "ideal"`` (epic §4).

Operators (epic §10 / QDEP §6.1, resolved plan §7, §11):
  * Mutation ``M(theta) = [[cos t, sin t], [sin t, -cos t]]`` -- a real symmetric
    reflection (M(t)^2 = I), a single-qubit gate on the offspring genotype.
  * Approximate clone ``U_M`` -- the 2018 biomimetic 1->2 partial clone: a fixed
    ``Ry(phi)`` on a fresh ancilla followed by ``CX(parent -> ancilla)``, phi fixed so
    the offspring inherits ``<sigma_z>`` at a fixed contraction ``eta = cos(phi) < 1``
    per generation (Q1: accept this fixed-eta stand-in as S0's "exact operator").
  * Phenotype map ``<sigma_z>_p`` -- a fixed ``Ry(basis)`` + ``CX(genotype -> pheno
    ancilla)`` so the phenotype ancilla's ``<sigma_z>`` tracks the genotype's (Q2).

Provenance: statevector + ``pipeline_common``-stub pattern ported from
``QuantumLife/code/sim_ideal_sign.py``; OUTPUT_DIR / writer idioms ported from
``QuantumLife/code/research_qtree_teleport.py`` (CD-1, CD-2).

Usage:
    cd artificial-life/code
    python stage0_reproduce.py --generations 6 --shots 4096 --seed 100 --name qdep_s0
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import random
import sys
import types
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator

print = functools.partial(print, flush=True)

# --- pipeline_common stub (CD-2) -------------------------------------------
# S0 never calls a backend, but we keep the stub + sys.path parity with S1+ so
# the file matches the hardware stages' import surface. Ported from
# QuantumLife/code/sim_ideal_sign.py lines 10-15.
_stub = types.ModuleType("pipeline_common")
for _a in ("connect", "run_sampler", "qpu_seconds"):
    setattr(_stub, _a, lambda *x, **k: None)
_stub.timestamp = lambda: "sim"
_stub.Sampler = None
_stub.SHOTS_PER_JOB = 10 ** 9
sys.modules["pipeline_common"] = _stub
from pipeline_common import timestamp  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
# separate research_runs dir, sibling of code/ (ported idiom, teleport line 114)
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

SIM = AerSimulator(method="statevector")

# ---- fixed physics constants (frozen here, reused unchanged by S1-S4) ------
ETA = 0.9                       # per-generation <sigma_z> contraction from U_M (Q1)
PHI = math.acos(ETA)            # clone Ry angle: eta = cos(phi)
PHENO_BASIS = 0.0               # phenotype-map basis rotation; 0 => pheno tracks genotype exactly (Q2)
UNIT_TOL = 0.03                 # operator-equivalence L1 tolerance (ported from sim_ideal_sign)

M_THETA_SPEC = "[[cos t, sin t], [sin t, -cos t]]"
U_M_SPEC = f"Ry(phi={PHI:.4f}) on fresh ancilla + CX(parent->ancilla); eta=cos(phi)={ETA}"


# ---------------------------------------------------------------------------
# Operators (plan §7 -- the physics S0 fixes)
# ---------------------------------------------------------------------------
def m_theta_matrix(theta: float) -> np.ndarray:
    """The paper's mutation matrix M(theta) = [[cos t, sin t], [sin t, -cos t]]."""
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, s], [s, -c]], dtype=complex)


def m_gate(theta: float) -> UnitaryGate:
    """Build M(theta) as a unitary gate; assert unitarity (it is a real involution)."""
    mat = m_theta_matrix(theta)
    assert np.allclose(mat @ mat.conj().T, np.eye(2), atol=1e-12), "M(theta) not unitary"
    assert np.allclose(mat @ mat, np.eye(2), atol=1e-12), "M(theta) not an involution"
    return UnitaryGate(mat, label="M")


def apply_clone(qc: QuantumCircuit, parent: int, ancilla: int, phi: float = PHI) -> None:
    """Approximate clone U_M: fixed Ry(phi) on the fresh ancilla, then CX(parent->ancilla).

    The offspring ancilla inherits <sigma_z> at contraction eta = cos(phi): after the
    CX the ancilla's <sigma_z> = cos(phi) * <sigma_z>_parent (no-cloning => variation).
    """
    qc.ry(phi, ancilla)
    qc.cx(parent, ancilla)


def phenotype_map(qc: QuantumCircuit, genotype: int, pheno_ancilla: int) -> None:
    """Genotype->phenotype ancilla map (CD-3, QDEP §5): fixed Ry(basis) + CX.

    <sigma_z> on ``pheno_ancilla`` is the trait. With PHENO_BASIS = 0 the phenotype
    exactly tracks the genotype's <sigma_z> -- the "lifetime" observable.
    """
    qc.ry(PHENO_BASIS, pheno_ancilla)
    qc.cx(genotype, pheno_ancilla)


# ---------------------------------------------------------------------------
# Lineage circuit (single linear lineage, population = 1 -- CD-8)
# ---------------------------------------------------------------------------
def build_generation(gen: int, theta_seq: list[float], measure: bool) -> QuantumCircuit:
    """Circuit reconstructing the lineage state at generation ``gen``.

    Register: genotype chain q[0..gen] (each cloned from its parent) + one phenotype
    ancilla q[gen+1]. Genotype 0 starts in |0> and is mutated by M(theta_0); each
    subsequent genotype is the U_M clone of its parent, then mutated. The phenotype
    ancilla reads the final genotype. Generations are built sequentially, one small
    circuit each (<= gen+2 qubits) -- no qubit-budget concern at S0 (plan §9).
    """
    n = gen + 2
    pheno = gen + 1
    qc = QuantumCircuit(n, 1) if measure else QuantumCircuit(n)

    # generation 0 genotype: |0> then mutate
    qc.append(m_gate(theta_seq[0]), [0])
    # descend the lineage: clone parent -> child, then mutate the child
    for i in range(1, gen + 1):
        apply_clone(qc, parent=i - 1, ancilla=i)
        qc.append(m_gate(theta_seq[i]), [i])
    # derive the phenotype from the final genotype
    phenotype_map(qc, genotype=gen, pheno_ancilla=pheno)

    if measure:
        qc.measure(pheno, 0)
    return qc


def _z_expectation_statevector(qc: QuantumCircuit, qubit: int) -> float:
    """Exact <sigma_z> of ``qubit`` from the noiseless statevector (no shot noise)."""
    n = qc.num_qubits
    label = ["I"] * n
    label[n - 1 - qubit] = "Z"   # qiskit Pauli label is qubit (n-1)..0, left to right
    op = SparsePauliOp("".join(label))
    return float(np.real(Statevector(qc).expectation_value(op)))


def ideal_sigmaz(theta_seq: list[float]) -> list[float]:
    """Closed-form-equivalent ideal <sigma_z>_p per generation via exact statevector.

    This is the noiseless reference the shot-sampled run is scored against (M1).
    """
    out: list[float] = []
    for g in range(len(theta_seq)):
        qc = build_generation(g, theta_seq, measure=False)
        out.append(_z_expectation_statevector(qc, qubit=g + 1))
    return out


# ---------------------------------------------------------------------------
# Unit test -- operator logical-equivalence (ported pattern, tol 0.03)
# ---------------------------------------------------------------------------
def unit_test() -> bool:
    """Verify M(theta) matches the paper matrix and U_M reproduces eta-contraction.

    Ported from ``sim_ideal_sign.unit_test``: grid over theta, worst-case L1 < 0.03.
    Returns True iff both operators pass (the S0 gate; caller aborts on False).
    """
    print("=== S0 unit test: exact operators vs their defined forms ===")
    grid = [0.0, math.pi / 2, math.pi, 0.7, 2.3, 0.1]

    # A. M(theta) gate matrix == paper matrix
    worst_m = 0.0
    for t in grid:
        got = np.asarray(m_gate(t).to_matrix())
        ref = m_theta_matrix(t)
        worst_m = max(worst_m, float(np.abs(got - ref).sum()))
    print(f"  worst L1(M_gate, paper matrix)     = {worst_m:.4f}")

    # B. U_M partial clone: offspring <sigma_z> == eta * parent <sigma_z>
    #    Prepare a parent at Ry(a) (=> <sigma_z>_parent = cos a), clone, read ancilla.
    worst_c = 0.0
    for a in grid:
        qc = QuantumCircuit(2)
        qc.ry(a, 0)                        # parent prep, <sigma_z>_parent = cos(a)
        apply_clone(qc, parent=0, ancilla=1)
        got = _z_expectation_statevector(qc, qubit=1)
        expected = ETA * math.cos(a)
        worst_c = max(worst_c, abs(got - expected))
    print(f"  worst L1(U_M ancilla z, eta*parent) = {worst_c:.4f}")

    ok_m = worst_m < UNIT_TOL
    ok_c = worst_c < UNIT_TOL
    print(f"  => M(theta) {'== paper matrix (equivalent)' if ok_m else 'DIFFERS !!'}")
    print(f"  => U_M      {'== partial-clone (equivalent)' if ok_c else 'DIFFERS !!'}")
    return ok_m and ok_c


# ---------------------------------------------------------------------------
# Sampled run loop
# ---------------------------------------------------------------------------
def _sampled_sigmaz(qc: QuantumCircuit, shots: int) -> float:
    """Estimate <sigma_z>_p from measurement counts of the single phenotype bit."""
    counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    n0 = counts.get("0", 0)
    n1 = counts.get("1", 0)
    tot = n0 + n1
    return (n0 - n1) / tot if tot else 0.0


def ideal_lifetime(args: argparse.Namespace) -> dict[str, Any]:
    """Run the single lineage over the generations; return the run.json dict (§4)."""
    random.seed(args.seed)
    # small random mutation schedule (Q4, ~0.1 rad); positive magnitude keeps the
    # lifetime decay monotone (the additive x-mixing term stays same-signed).
    theta_seq = [random.uniform(0.0, args.mut_scale) for _ in range(args.generations)]

    ideal = ideal_sigmaz(theta_seq)
    gens: list[dict[str, Any]] = []
    print(f"\n=== ideal lifetime: {args.generations} gens, {args.shots} shots, "
          f"eta={ETA} ===")
    print("  gen   trait_sigmaz   ideal     |diff|    3*stderr   fidelity")
    for g in range(args.generations):
        qc = build_generation(g, theta_seq, measure=True)
        sampled = _sampled_sigmaz(qc, args.shots)
        ideal_g = ideal[g]
        diff = abs(sampled - ideal_g)
        stderr = math.sqrt(max(0.0, 1.0 - ideal_g * ideal_g) / args.shots)
        fidelity = 1.0 - diff / 2.0     # <sigma_z> in [-1, 1] => max diff 2
        gate = "ok" if diff <= 3.0 * stderr else "OVER"
        print(f"  {g:>3}   {sampled:+.4f}      {ideal_g:+.4f}  {diff:.4f}   "
              f"{3 * stderr:.4f}  {fidelity:.4f} [{gate}]")
        gens.append({
            "gen": g,
            "trait_sigmaz": sampled,
            "fidelity_vs_ideal": fidelity,
            "shots": args.shots,
        })

    # lifetime-decay eyeball: successive ratios ~ constant eta (AC-S0.3)
    ratios = [gens[g]["trait_sigmaz"] / gens[g - 1]["trait_sigmaz"]
              for g in range(1, len(gens))
              if abs(gens[g - 1]["trait_sigmaz"]) > 1e-6]
    if ratios:
        print(f"  successive <sigma_z>_p ratios (~eta): "
              f"{', '.join(f'{r:.3f}' for r in ratios)}")

    return {
        "meta": {
            "project": "artificial-life",
            "study": "coherence-depth-genealogy",
            "arm": "ideal",
            "backend": "sim",
            "sim": True,
            "timestamp": timestamp(),
            "seed": args.seed,
            "generations": args.generations,
            "shots": args.shots,
            "mut_scale": args.mut_scale,
            "operators": {"M_theta": M_THETA_SPEC, "U_M": U_M_SPEC},
            "calibration": None,
        },
        "generations": gens,
    }


def write_run(run: dict[str, Any], args: argparse.Namespace) -> str:
    """Dump the run to research_runs/<name>_sim_seed<seed>_<ts>_run.json (ported idiom)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    out_path = os.path.join(
        OUTPUT_DIR, f"{args.name}_sim_seed{args.seed}_{ts}_run.json")
    with open(out_path, "w") as f:
        json.dump(run, f, indent=2)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 0 -- reproduce the 2018 "
                                             "single-lineage lifetime in noiseless sim.")
    ap.add_argument("--generations", type=int, default=6)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="qdep_s0")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.1,
                    help="max mutation angle per generation, radians (Q4 default 0.1)")
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True,
                    help="S0 is sim-only; kept for parity with hardware stages")
    args = ap.parse_args()

    if not unit_test():
        print("\n[S0 GATE FAILED] operators do not match their defined forms -- "
              "do not proceed to S1.")
        raise SystemExit(1)

    run = ideal_lifetime(args)
    path = write_run(run, args)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
