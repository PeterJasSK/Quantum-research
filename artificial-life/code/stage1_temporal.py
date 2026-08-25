#!/usr/bin/env python3
"""Stage 1 (QDEP: Coherence Depth of an Inherited-Entanglement Genealogy).

S1 re-aims the *trusted* QuantumLife correlation machinery from spatial ``c(d)``
(across qubits, one generation) to this study's **temporal** ``C(g)`` (across
generations, one lineage) -- same connected-correlation arithmetic, orthogonal
axis (CD-3). It proves three things and gates S2:

  1. **temporal C(g)** -- ``two_point_correlation`` re-indexed so ``M[:, g]`` is the
     phenotype trait ``T_g`` at generation g, correlated with ``T_0`` across shots;
  2. **the measure-and-resend classical surrogate arm** (CD-4/AC-S1.2) -- the honest
     separable null the coherent arm must beat;
  3. **small-scale g\\*** (M3, k=2 headline / k=3 reported) with sigma from ``--repeats``.

It wires the certified Q-EaaS entropy stream for the per-generation mutation angles
from here on (CD-7) and is **fail-closed**: a ``QRNGUnavailable`` aborts the run, it
never falls back to PRNG (else the M7 provenance claim is a lie).

Provenance (CD-1 -- copied verbatim, not imported):
  * S0 operators/physics ``m_theta_matrix``/``m_gate``/``apply_clone``/``phenotype_map``/
    ``_z_expectation_statevector`` + constants ``ETA/PHI/PHENO_BASIS/UNIT_TOL`` are copied
    from ``artificial-life/code/stage0_reproduce.py`` (Q1: strict CD-1 parity, no import).
  * ``temporal_correlation`` ported from ``QuantumLife/code/research_qtree.py``'s
    ``two_point_correlation`` (§7, re-indexed to generation g).
  * ``run_once``/``main`` aggregation skeleton ported from ``research_qtree.py``.
  * the dynamic-circuit ``ClassicalRegister`` + mid-circuit readout + ``run_hw`` dispatch
    ported from ``research_qtree_teleport.py`` (the teleport bond itself is S3, not here).
  * the ``pipeline_common`` sys.path probe + stub fallback ported from
    ``research_qtree_teleport.py`` / ``sim_ideal_sign.py`` (CD-2, CD-9).

Usage:
    cd artificial-life/code
    python stage1_temporal.py --generations 8 --shots 4096 --seed 100 --repeats 5 \\
        --arm both --name qdep_s1
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
from qiskit import (ClassicalRegister, QuantumCircuit, QuantumRegister,
                    transpile)
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# --- reuse the Calibration study's submission pipeline without editing it -----
# CD-2: pipeline_common stays external. It has moved between layouts; probe each
# known location (ported from research_qtree_teleport.py). Under --sim we never
# call the backend hooks, but the real import is preferred when present so the
# hardware path Just Works; on a backend-less box we fall back to the stub
# (ported from sim_ideal_sign.py) so this file stays importable in --sim.
for _cand in ("code", os.path.join("old", "code"), os.path.join("new", "code")):
    _p = os.path.normpath(
        os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", _cand))
    if os.path.exists(os.path.join(_p, "pipeline_common.py")):
        sys.path.insert(0, _p)
        break
try:  # real pipeline_common (needs qiskit_ibm_runtime for the hardware path)
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402
except Exception:  # stub fallback -- keeps --sim importable without the backend layer
    _stub = types.ModuleType("pipeline_common")
    for _a in ("connect", "run_sampler", "qpu_seconds"):
        setattr(_stub, _a, lambda *x, **k: None)
    _stub.timestamp = lambda: "sim"
    _stub.Sampler = None
    _stub.SHOTS_PER_JOB = 10 ** 9
    sys.modules["pipeline_common"] = _stub
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402  (local, same dir)

SIM = AerSimulator(method="statevector")
# separate research_runs dir, sibling of code/ (ported idiom, S0/teleport)
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"      # Q5: no localhost fallback

# ---- fixed physics constants (copied verbatim from stage0_reproduce.py, CD-1) ----
ETA = 0.9                       # per-generation <sigma_z> contraction from U_M (Q1)
PHI = math.acos(ETA)            # clone Ry angle: eta = cos(phi)
PHENO_BASIS = 0.0               # phenotype-map basis; 0 => pheno tracks genotype exactly (Q2)
UNIT_TOL = 0.03                 # operator-equivalence L1 tolerance
TRAIT_BASIS_DEFAULT = math.pi / 4   # off-diagonal trait readout (see SETUP-FIX note below)

# --- SETUP-FIX (2026-08-19) -------------------------------------------------
# The original S1 build had two coupled faults that forced the coherent (quantum)
# arm to be *physically identical* to the measure-and-resend surrogate, pinning
# g*=1 regardless of parameters:
#   (1) it mid-circuit-measured a CX-copied phenotype ancilla every generation,
#       which is a proxy Z-measurement of the genotype -- collapsing the lineage
#       into a classical Z-basis Markov chain BEFORE it seeded the next child;
#   (2) it read the trait as diagonal <sigma_z> (PHENO_BASIS=0), and a Z
#       correlation down a copy chain is classically reproducible by one bit.
# Fix: (a) DEFER all measurement to the circuit end (the clone chain stays
# unitary; no per-generation projection); (b) read the trait in an OFF-DIAGONAL
# basis (TRAIT_BASIS), where the coherent clone carries correlation a classical
# resend cannot. The surrogate is the same circuit with an honest per-generation
# measure-and-resend (collapse + re-prep) in the SAME basis, so the two arms
# differ only in coherence. NOTE: with the Ry+CX clone (a classical copier that
# does not propagate coherence to children) the ideal quantum advantage is only
# ~1 generation deep; a coherence-propagating cloner is required for a deep g*
# (design decision, tracked in the epic).

M_THETA_SPEC = "[[cos t, sin t], [sin t, -cos t]]"
U_M_SPEC = f"Ry(phi={PHI:.4f}) on fresh ancilla + CX(parent->ancilla); eta=cos(phi)={ETA}"


# ---------------------------------------------------------------------------
# Operators (copied verbatim from stage0_reproduce.py, CD-1 -- do NOT import)
# ---------------------------------------------------------------------------
def m_theta_matrix(theta: float) -> np.ndarray:
    """The paper's mutation matrix M(theta) = [[cos t, sin t], [sin t, -cos t]]."""
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, s], [s, -c]], dtype=complex)


def m_gate(theta: float) -> UnitaryGate:
    """Build M(theta) as a unitary gate; assert unitarity (a real involution)."""
    mat = m_theta_matrix(theta)
    assert np.allclose(mat @ mat.conj().T, np.eye(2), atol=1e-12), "M(theta) not unitary"
    assert np.allclose(mat @ mat, np.eye(2), atol=1e-12), "M(theta) not an involution"
    return UnitaryGate(mat, label="M")


def apply_clone(qc: QuantumCircuit, parent: int, ancilla: int, phi: float = PHI) -> None:
    """Approximate clone U_M: fixed Ry(phi) on the fresh ancilla, then CX(parent->ancilla).

    The offspring ancilla inherits <sigma_z> at contraction eta = cos(phi).
    """
    qc.ry(phi, ancilla)
    qc.cx(parent, ancilla)


def phenotype_map(qc: QuantumCircuit, genotype: int, pheno_ancilla: int) -> None:
    """Genotype->phenotype ancilla map (CD-3): fixed Ry(basis) + CX.

    With PHENO_BASIS = 0 the phenotype exactly tracks the genotype's <sigma_z>.
    """
    qc.ry(PHENO_BASIS, pheno_ancilla)
    qc.cx(genotype, pheno_ancilla)


def _z_expectation_statevector(qc: QuantumCircuit, qubit: int) -> float:
    """Exact <sigma_z> of ``qubit`` from the noiseless statevector (no shot noise)."""
    n = qc.num_qubits
    label = ["I"] * n
    label[n - 1 - qubit] = "Z"   # qiskit Pauli label is qubit (n-1)..0, left to right
    op = SparsePauliOp("".join(label))
    return float(np.real(Statevector(qc).expectation_value(op)))


# ---------------------------------------------------------------------------
# Temporal correlation (§7, CD-3) -- ported from research_qtree.two_point_correlation,
# re-indexed to generation g and anchored at T_0 (Q2).
# ---------------------------------------------------------------------------
def temporal_correlation(traits_by_shot: list[str], gmax: int) -> dict:
    """Connected two-point correlation of the per-shot lineage record, anchored at T_0.

        C(g) = <T_0 T_g> - <T_0><T_g>        (Q2: anchored at generation 0)
        C(0) = Var(T_0)                       (falls out of the anchored form)
        c(g) = C(g) / C(0)                    (normalised)

    ``traits_by_shot`` is a list of ``G+1``-bit strings ``T_0 T_1 ... T_G`` -- one row
    per shot, one column per generation (the temporal re-aim of QuantumLife's spatial
    per-qubit matrix). ``C(g)~0`` for g>0 is the signature of a memoryless / separable
    (classical surrogate) lineage; a distance-decaying C(g) is the coherent fingerprint.

    The normalised c(g) is invariant to the affine <sigma_z> = 1 - 2*bit rescaling, so
    the bit-based correlation is faithful (§7). Raw shot matrix stays local.
    """
    width = len(traits_by_shot[0])
    gmax = min(gmax, width - 1)
    # (shots x width) matrix of 0/1
    M = np.frombuffer("".join(traits_by_shot).encode(), dtype=np.uint8).reshape(
        len(traits_by_shot), width)
    M = (M - ord("0")).astype(np.float64)          # '0'->0.0, '1'->1.0
    p = M.mean(axis=0)                              # per-generation P(bit=1)
    t0 = M[:, 0]                                    # anchor column T_0
    C = []
    for g in range(0, gmax + 1):
        joint = float((t0 * M[:, g]).mean())        # <T_0 T_g>
        C.append(joint - float(p[0]) * float(p[g]))  # connected, anchored at T_0
    C0 = C[0]                                       # == Var(T_0)
    c = [ci / C0 if C0 > 1e-12 else 0.0 for ci in C]
    return {"C": [round(x, 6) for x in C],
            "c": [round(x, 6) for x in c],
            "C0": round(C0, 6),
            "gmax": gmax}


# ---------------------------------------------------------------------------
# Certified Q-EaaS mutation schedule (CD-7, §7 byte->angle map)
# ---------------------------------------------------------------------------
def _mutation_schedule(client: QRNGClient, n_slots: int, mut_scale: float
                       ) -> tuple[list[float], list[dict]]:
    """Draw one mutation angle per generation from certified Q-EaaS bytes.

    Fetch 32-byte blocks (API: 32 <= size <= 4096) until ``4 * n_slots`` bytes are in
    hand, decode ``resp.data`` hex, and derive ``theta_g = mut_scale * (u32 / 2**32)``
    from a disjoint 4-byte slice per generation (uniform in [0, mut_scale), matching S0's
    ``random.uniform(0, mut_scale)`` magnitude so the lifetime decay stays monotone).

    Returns ``(theta_seq, entropy_provenance)``; both arms of a repeat consume the SAME
    ``theta_seq`` at matched positions (CD-4). Fail-closed: ``QRNGUnavailable`` propagates
    and aborts the run (CD-7) -- never a silent PRNG fallback.
    """
    need = 4 * n_slots
    blocks: list[tuple[Any, bytes]] = []
    flat = bytearray()
    owner: list[int] = []            # response index that produced each byte
    while len(flat) < need:
        resp = client.fetch(size=32, fmt="hex")   # raises QRNGUnavailable -> abort
        raw = bytes.fromhex(resp.data)
        idx = len(blocks)
        blocks.append((resp, raw))
        flat.extend(raw)
        owner.extend([idx] * len(raw))

    theta_seq: list[float] = []
    provenance: list[dict] = []
    for g in range(n_slots):
        off = 4 * g
        u = int.from_bytes(bytes(flat[off:off + 4]), "big")
        theta = mut_scale * (u / 2 ** 32)
        resp = blocks[owner[off]][0]
        theta_seq.append(theta)
        provenance.append({
            "gen": g,
            "source": "qeaas",
            "request_id": resp.request_id,
            "receipt": resp.receipt,               # nullable, opaque dotted token
            "entropy_epoch": resp.entropy_epoch,
            "timestamp": resp.timestamp,
            "angle_rad": round(theta, 8),
        })
    return theta_seq, provenance


# ---------------------------------------------------------------------------
# Quantum arm -- one dynamic lineage circuit (§5, mid-circuit readout per generation)
# ---------------------------------------------------------------------------
def build_lineage_quantum(theta_seq: list[float], n_slots: int,
                          trait_basis: float) -> QuantumCircuit:
    """Coherent lineage, DEFERRED measurement, off-diagonal trait readout (SETUP-FIX).

    Registers: genotype chain ``q[0..n_slots-1]`` + classical ``c(n_slots)``. The whole
    lineage is built UNITARILY -- per generation g: ``apply_clone`` the parent (S0 U_M),
    then mutate with ``m_gate(theta_g)``. NO mid-circuit measurement: every genotype stays
    coherent and alive so it can seed its child and still be read at the end. Only after the
    full lineage is built do we rotate every genotype into the trait basis (``Ry(-basis)``,
    so ``measure`` reports ``<O> = cos(basis) sigma_z + sin(basis) sigma_x``) and measure all
    at once. Column g of a shot record is ``T_g``. Deferred + off-diagonal is the whole fix:
    Z-diagonal readout of a copy chain is classically reproducible; this is not.
    """
    geno = QuantumRegister(n_slots, "q")
    cr = ClassicalRegister(n_slots, "c")
    qc = QuantumCircuit(geno, cr)
    qc.append(m_gate(theta_seq[0]), [0])                    # genotype 0: |0> then mutate
    for g in range(1, n_slots):
        apply_clone(qc, parent=g - 1, ancilla=g)           # coherent clone parent->child
        qc.append(m_gate(theta_seq[g]), [g])               # mutate the child
    qc.barrier()
    for g in range(n_slots):                               # deferred trait-basis readout
        if abs(trait_basis) > 1e-12:
            qc.ry(-trait_basis, g)
        qc.measure(g, cr[g])
    return qc


def build_lineage_quantum_midcircuit(theta_seq: list[float], n_slots: int,
                                     trait_basis: float) -> QuantumCircuit:
    """Coherent lineage, MID-CIRCUIT readout -- the original CD-3 intent (--readout midcircuit).

    Same unitary spine as ``build_lineage_quantum`` (S0 ``apply_clone`` + ``m_gate``), but each
    generation's trait is read the instant it is no longer needed: right AFTER it has cloned its
    child, generation ``g`` is rotated into the trait basis and measured into ``c[g]``, while the
    rest of the lineage is still being built. This is many measurements in one shot, one lineage
    per shot (CD-3), interleaved with subsequent gates on later generations.

    Coherence is preserved exactly as in the deferred arm: the clone ``CX(g-1 -> g)`` consumes the
    still-coherent parent BEFORE the parent is measured, and no gate ever touches ``g`` again after
    its measurement, so measuring it early rather than at the end leaves the joint outcome
    distribution unchanged in a noiseless sim (measurement commutes with disjoint-qubit gates).
    Deferred and mid-circuit are therefore identical under ``--sim`` (pipeline check); they diverge
    ONLY on hardware, by the mid-circuit measurement error + the earlier idle-then-read schedule.
    That divergence -- does mid-circuit c(g) track deferred c(g) within sigma? -- is the experiment.

    NOTE the ONE difference from ``build_lineage_classical``: the classical surrogate measures AND
    re-prepares each genotype (``Ry(+basis)``) BEFORE cloning, breaking coherence into the child;
    here the clone fires first and there is no re-prep, so the child is seeded coherently. Same
    measurement count, opposite coherence -- exactly the coherent/classical contrast, now with the
    quantum arm read mid-circuit instead of deferred.
    """
    geno = QuantumRegister(n_slots, "q")
    cr = ClassicalRegister(n_slots, "c")
    qc = QuantumCircuit(geno, cr)

    def read_trait(g: int) -> None:                        # mid-circuit trait-basis readout of q[g]
        if abs(trait_basis) > 1e-12:
            qc.ry(-trait_basis, g)
        qc.measure(g, cr[g])

    qc.append(m_gate(theta_seq[0]), [0])                    # genotype 0: |0> then mutate
    for g in range(1, n_slots):
        apply_clone(qc, parent=g - 1, ancilla=g)           # clone from the still-coherent parent
        qc.append(m_gate(theta_seq[g]), [g])               # mutate the child
        read_trait(g - 1)                                  # parent consumed -> read it mid-circuit
    read_trait(n_slots - 1)                                # last generation is never a parent
    return qc


def sample_quantum_arm(qc: QuantumCircuit, shots: int, args: argparse.Namespace,
                       backend: Any, qubit_list: list[int]) -> tuple[list[str], float | None]:
    """Dispatch the quantum lineage circuit: --sim statevector or Heron-r2 run_hw.

    Returns ``(fields, qpu_seconds)``: one ``T_0...T_G`` string per shot, and the QPU time
    the job billed (``None`` under --sim). Qiskit's little-endian count key is ``c[G]...c[0]``;
    reversing gives ``c[0]...c[G]`` so column g maps to generation g. QPU time is recorded so the
    deferred-vs-midcircuit feed-forward latency delta is measurable (1b Record).
    """
    if args.sim:
        counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
        fields: list[str] = []
        for bitstr, cnt in counts.items():
            rec = bitstr.replace(" ", "")[::-1]             # c[0..G]
            fields.extend([rec] * cnt)
        return fields, None
    # hardware: preset pass manager + sampler (ported research_qtree.run_hw). Pin the
    # layout only when the chain matches the circuit width, else let opt-3 route.
    init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=init)
    isa = pm.run(qc)
    raw_meas, _jobs, qpu_s = run_sampler(backend, isa, shots)
    return [s[::-1] for s in raw_meas], qpu_s               # register 'c', reversed


# ---------------------------------------------------------------------------
# Classical surrogate arm -- measure-and-resend (§7, AC-S1.2, Q3)
# ---------------------------------------------------------------------------
def build_lineage_classical(theta_seq: list[float], n_slots: int,
                            trait_basis: float) -> QuantumCircuit:
    """Measure-and-resend surrogate as a circuit (SETUP-FIX): same clone+mutate ops as the
    quantum arm, but after each genotype is formed it is MEASURED in the trait basis and the
    outcome re-prepared as a separable trait eigenstate before it seeds the child.

    ``Ry(-basis); measure -> c[g]; Ry(+basis)`` collapses the genotype to a definite trait
    value (an entanglement-breaking step) and rotates that classical value back into the
    lineage frame -- an honest classical broadcast of one bit per generation. Everything else
    (theta_seq, eta, trait basis, readout) is identical to the quantum arm; the ONLY
    difference is that coherence is destroyed each generation. Column g is ``T_g``.
    """
    geno = QuantumRegister(n_slots, "q")
    cr = ClassicalRegister(n_slots, "c")
    qc = QuantumCircuit(geno, cr)
    qc.append(m_gate(theta_seq[0]), [0])
    for g in range(n_slots):
        if g > 0:
            apply_clone(qc, parent=g - 1, ancilla=g)
            qc.append(m_gate(theta_seq[g]), [g])
        if abs(trait_basis) > 1e-12:                        # measure genotype g in trait basis
            qc.ry(-trait_basis, g)
        qc.measure(g, cr[g])                                # record T_g AND collapse (resend)
        if abs(trait_basis) > 1e-12:
            qc.ry(trait_basis, g)                           # re-prep separable trait eigenstate
    return qc


def sample_circuit(qc: QuantumCircuit, shots: int) -> list[str]:
    """Statevector-sim a measurement circuit; return one ``T_0...T_G`` record per shot.

    Qiskit's little-endian count key is ``c[G]...c[0]``; reversing gives ``c[0]...c[G]`` so
    column g maps to generation g. Used for the classical surrogate (always sim: it is a
    classical null and never consumes QPU time).
    """
    counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    fields: list[str] = []
    for bitstr, cnt in counts.items():
        fields.extend([bitstr.replace(" ", "")[::-1]] * cnt)
    return fields


# ---------------------------------------------------------------------------
# Ideal cross-check arm (§6.7, Q6 -- off by default; full confound curve is S2)
# ---------------------------------------------------------------------------
def _build_generation_nomeasure(gen: int, theta_seq: list[float]) -> QuantumCircuit:
    """S0's per-generation lineage circuit (no measurement) for exact <sigma_z>_p."""
    n = gen + 2
    qc = QuantumCircuit(n)
    qc.append(m_gate(theta_seq[0]), [0])
    for i in range(1, gen + 1):
        apply_clone(qc, parent=i - 1, ancilla=i)
        qc.append(m_gate(theta_seq[i]), [i])
    phenotype_map(qc, genotype=gen, pheno_ancilla=gen + 1)
    return qc


def run_ideal(theta_seq: list[float], n_slots: int) -> list[float]:
    """Exact-statevector <sigma_z>_p per generation (S0 _z_expectation_statevector).

    A ``meta.arm="ideal"`` sanity run only -- the confound *curve* (M4) is S2.
    """
    out: list[float] = []
    for g in range(n_slots):
        qc = _build_generation_nomeasure(g, theta_seq)
        out.append(_z_expectation_statevector(qc, qubit=g + 1))
    return out


# ---------------------------------------------------------------------------
# Per-(arm, repeat) run -- ported research_qtree.run_once skeleton
# ---------------------------------------------------------------------------
def run_once(args: argparse.Namespace, seed: int, arm: str, theta_seq: list[float],
             provenance: list[dict], backend: Any, backend_name: str,
             calib: Any, qubit_list: list[int]) -> tuple[dict, str]:
    """Run one arm at one seed; build/write the §4 run.json; return (run_dict, path)."""
    random.seed(seed)
    n_slots = len(theta_seq)
    gmax = min(args.corr_gmax, n_slots - 1)
    readout = getattr(args, "readout", "deferred")
    qpu_s: float | None = None

    if arm == "ideal":
        ideal = run_ideal(theta_seq, n_slots)
        gens = [{"gen": g, "trait_sigmaz": round(ideal[g], 6), "shots": 0}
                for g in range(n_slots)]
        corr = {"C": [], "c": [], "C0": 0.0, "gmax": gmax}   # bits absent -> no C(g)
        print(f"  seed {seed} [ideal]  trait_sigmaz: "
              f"{', '.join(f'{v:+.3f}' for v in ideal)}")
    else:
        if arm == "quantum":
            if readout == "midcircuit":
                qc = build_lineage_quantum_midcircuit(theta_seq, n_slots, args.trait_basis)
            else:
                qc = build_lineage_quantum(theta_seq, n_slots, args.trait_basis)
            fields, qpu_s = sample_quantum_arm(qc, args.shots, args, backend, qubit_list)
        elif arm == "classical":
            qc = build_lineage_classical(theta_seq, n_slots, args.trait_basis)
            fields = sample_circuit(qc, args.shots)          # always sim (classical null)
        else:
            raise ValueError(f"unknown arm {arm!r}")
        M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(
            len(fields), n_slots)
        p = ((M - ord("0")).astype(np.float64)).mean(axis=0)   # P(bit=1) per generation
        gens = [{"gen": g, "trait_sigmaz": round(1.0 - 2.0 * float(p[g]), 6),
                 "shots": args.shots} for g in range(n_slots)]
        corr = temporal_correlation(fields, gmax)
        print(f"  seed {seed} [{arm:>9}]  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")

    run = {
        "meta": {
            "project": "artificial-life",
            "study": "coherence-depth-genealogy",
            "arm": arm,
            "backend": backend_name,
            "sim": bool(args.sim),
            "timestamp": timestamp(),
            "seed": seed,
            "generations": args.generations,
            "shots": args.shots,
            "mut_scale": args.mut_scale,
            "corr_gmax": args.corr_gmax,
            "readout": (readout if arm == "quantum" else "na"),
            "num_measurements_per_shot": (0 if arm == "ideal" else n_slots),
            "mid_circuit_measurements": (
                (n_slots - 1) if (arm == "quantum" and readout == "midcircuit") else 0),
            "qpu_seconds": qpu_s,
            "operators": {"M_theta": M_THETA_SPEC, "U_M": U_M_SPEC},
            "entropy_provenance": provenance,
            "calibration": calib,
        },
        "generations": gens,
        "correlation_temporal": corr,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    out_path = os.path.join(
        OUTPUT_DIR, f"{args.name}_{arm}_{backend_name}_seed{seed}_{ts}_run.json")
    with open(out_path, "w") as f:
        json.dump(run, f, indent=2, default=str)
    print(f"  -> {out_path}")
    return run, out_path


# ---------------------------------------------------------------------------
# g* (CD-5)
# ---------------------------------------------------------------------------
def compute_gstar(per_gen_Cq: list[float], per_gen_Ccl: list[float],
                  sigma: list[float], k: int) -> int:
    """g* = max g s.t. |C_q(g) - C_cl(g)| > k*sigma(g); else 1 (falsification, §5).

    Domain is g>=1: g=0 is C(0)=Var(T_0), the normalisation anchor (raw variances
    differ between arms by construction), so it is excluded -- the plan's floor of
    g*=1 (§7) is only consistent with a domain that starts at generation 1.
    """
    gstar = 1
    for g in range(1, min(len(per_gen_Cq), len(per_gen_Ccl), len(sigma))):
        s = sigma[g]
        if s > 1e-12 and abs(per_gen_Cq[g] - per_gen_Ccl[g]) > k * s:
            gstar = g
    return gstar


# ---------------------------------------------------------------------------
# main -- ported research_qtree.main (backend dispatch + repeats/aggregation loop)
# ---------------------------------------------------------------------------
def _read_env_key(name: str) -> str | None:
    """Return ``name`` from the environment, else parse ``artificial-life/.env``."""
    val = os.environ.get(name)
    if val:
        return val
    env_path = os.path.normpath(os.path.join(_HERE, "..", ".env"))
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, raw = line.partition("=")
                if key.strip() == name:
                    return raw.strip().strip('"').strip("'")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="QDEP Stage 1 -- temporal C(g), "
                                             "measure-and-resend surrogate, small-scale g*.")
    ap.add_argument("--generations", type=int, default=8, help="lineage depth G")
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100, help="base; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=5, help="sigma for g* (CD-5)")
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--arm", choices=["quantum", "classical", "both", "ideal"],
                    default="both")
    ap.add_argument("--corr-gmax", dest="corr_gmax", type=int, default=None,
                    help="max g for C(g) (default = --generations)")
    ap.add_argument("--k", type=int, default=2, help="sigma multiplier (k=3 also reported)")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.1,
                    help="max mutation angle per generation, radians (Q4)")
    ap.add_argument("--trait-basis", dest="trait_basis", type=float,
                    default=TRAIT_BASIS_DEFAULT,
                    help="trait readout basis in radians (SETUP-FIX): 0=diagonal sigma_z "
                         "(classically clonable, g*=1), pi/4=off-diagonal (default, real gap)")
    ap.add_argument("--readout", choices=["deferred", "midcircuit"], default="deferred",
                    help="quantum-arm trait readout (1b experiment): 'deferred' = month-1 fix, "
                         "all traits measured at circuit end, lineage stays coherent; 'midcircuit' "
                         "= read T_g per generation mid-circuit (many measures/shot, one lineage/"
                         "shot, CD-3 intent). Identical under --sim; diverge only on hardware by "
                         "mid-circuit readout error. Ignored for classical/ideal arms.")
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=None,
                    help="Q-EaaS base URL (Q5); default env QEAAS_API_URL else "
                         f"{QEAAS_URL_DEFAULT}")
    ap.add_argument("--name", type=str, default="qdep_s1")
    args = ap.parse_args()

    n_slots = args.generations + 1              # generation slots T_0..T_G
    if args.corr_gmax is None:
        args.corr_gmax = args.generations
    arms = ["quantum", "classical"] if args.arm == "both" else [args.arm]

    # --- certified Q-EaaS client (CD-7, fail-closed) -------------------------
    api_key = _read_env_key("QEAAS_API_KEY")
    if not api_key:
        print("[S1 ABORT] QEAAS_API_KEY not set (env or artificial-life/.env) -- "
              "S1 is fail-closed on entropy provenance (CD-7). No PRNG fallback.")
        raise SystemExit(1)
    qrng_url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
    client = QRNGClient(qrng_url, api_key)
    print(f"Q-EaaS  : {qrng_url}  (fail-closed, no PRNG fallback)")
    try:  # fast /health probe up front -- abort clearly instead of blocking on fetch
        h = client.health()
    except QRNGUnavailable as exc:
        print(f"[S1 ABORT] Q-EaaS health check failed: {exc} -- no PRNG fallback (CD-7).")
        raise SystemExit(1)
    print(f"          health: {h.status} / entropy {h.quantum_entropy_level} / "
          f"pool {h.pool_bytes_remaining} bytes")
    if h.status != "ok":
        print(f"[S1 ABORT] Q-EaaS status {h.status!r} (entropy {h.quantum_entropy_level!r}).")
        raise SystemExit(1)

    # --- backend / qubit layout ----------------------------------------------
    n_q = n_slots                                # genotype chain only (deferred readout, SETUP-FIX)
    backend = None
    backend_name = "sim"
    calib = None
    if not args.sim:
        backend = connect(args.backend)
        backend_name = backend.name
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits)")
        try:
            from calibration_snapshot import read_snapshot
            calib = read_snapshot(backend)
        except Exception as e:
            calib = {"_error": str(e)}
        from layout import best_chain
        qubit_list, qstats = best_chain(backend, n_q)
        print(f"Auto qubit chain (live calib): {qstats}")
    else:
        print("Backend : statevector sim (--sim, CD-9)")
        qubit_list = list(range(n_q))

    # --- repeats: shared theta_seq per repeat, both arms (CD-4) ---------------
    corr_by_arm: dict[str, list[list[float]]] = {a: [] for a in arms}
    run_files: list[str] = []
    for r in range(args.repeats):
        seed = args.seed + r
        print(f"\n=== repeat {r + 1}/{args.repeats}  (seed {seed}) ===")
        try:
            theta_seq, provenance = _mutation_schedule(client, n_slots, args.mut_scale)
        except QRNGUnavailable as exc:      # fail-closed (CD-7)
            print(f"[S1 ABORT] Q-EaaS unavailable: {exc} -- no PRNG fallback (CD-7).")
            raise SystemExit(1)
        for arm in arms:
            run, path = run_once(args, seed, arm, theta_seq, provenance,
                                 backend, backend_name, calib, qubit_list)
            run_files.append(os.path.basename(path))
            if arm in corr_by_arm:
                # aggregate NORMALIZED c(g) (SETUP-FIX): raw C(g) sits at the C0 shot-noise
                # floor and is degenerate between arms; the signal lives in c(g)=C(g)/C0.
                corr_by_arm[arm].append(run["correlation_temporal"]["c"])

    # --- aggregate C(g) mean/std per arm across repeats -----------------------
    stat_arms = [a for a in ("quantum", "classical", "ideal") if a in corr_by_arm
                 and corr_by_arm[a] and corr_by_arm[a][0]]
    per_generation: list[dict] = []
    means: dict[str, np.ndarray] = {}
    stds: dict[str, np.ndarray] = {}
    for a in stat_arms:
        mat = np.array(corr_by_arm[a])            # (repeats x n_slots)
        means[a] = mat.mean(axis=0)
        stds[a] = mat.std(axis=0, ddof=0)
    for g in range(n_slots):
        per_generation.append({
            "gen": g,
            "C_g_mean": {a: round(float(means[a][g]), 6) for a in stat_arms},
            "C_g_std": {a: round(float(stds[a][g]), 6) for a in stat_arms},
        })

    # --- g* (CD-5): k=2 headline, k=3 reported -------------------------------
    if "quantum" in means and "classical" in means:
        sigma = [math.sqrt(float(stds["quantum"][g]) ** 2 + float(stds["classical"][g]) ** 2)
                 for g in range(n_slots)]
        Cq = means["quantum"].tolist()
        Ccl = means["classical"].tolist()
        gstar = {"k2": compute_gstar(Cq, Ccl, sigma, 2),
                 "k3": compute_gstar(Cq, Ccl, sigma, 3)}
    else:
        gstar = {"k2": None, "k3": None}

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    sum_path = os.path.join(OUTPUT_DIR, f"{args.name}_{backend_name}_{ts}_summary.json")
    with open(sum_path, "w") as f:
        json.dump({
            "meta": {
                "project": "artificial-life",
                "study": "coherence-depth-genealogy",
                "backend": backend_name,
                "sim": bool(args.sim),
                "base_seed": args.seed,
                "repeats": args.repeats,
                "generations": args.generations,
                "shots": args.shots,
                "corr_gmax": args.corr_gmax,
                "readout": args.readout,
                "k": args.k,
                "run_files": run_files,
            },
            "per_generation": per_generation,
            "gstar": gstar,
        }, f, indent=2, default=str)

    # --- report --------------------------------------------------------------
    print("\n--- DONE ---")
    if stat_arms:
        print("  g     " + "   ".join(f"C_{a[:4]}" for a in stat_arms))
        for g in range(n_slots):
            cells = "   ".join(f"{means[a][g]:+.4f}" for a in stat_arms)
            print(f"  {g:>3}   {cells}")
    if gstar["k2"] is not None:
        print(f"\ng* (k=2) = {gstar['k2']}    g* (k=3) = {gstar['k3']}")
    else:
        print("\ng*: needs both quantum and classical arms (--arm both).")
    print(f"Summary file : {sum_path}")


if __name__ == "__main__":
    main()
