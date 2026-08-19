#!/usr/bin/env python3
"""Stage 2 (QDEP: Coherence Depth of an Inherited-Entanglement Genealogy).

S2 takes the banked S1 spine and does two things, in order (plan §1):

  1. **Confronts the S1 collapse (the back-action confound).** S1 came out g\\*=1
     because the phenotype map is a full ``CX`` that fully projects the genotype's
     Z component every generation, re-collapsing the coherent lineage toward the
     measure-and-resend surrogate. S2 makes that coupling **tunable** via
     ``--pheno-coupling alpha`` (Q1): ``alpha=1`` recovers S1's full projection
     (byte-identical), ``alpha<1`` reads the trait as a weak peek, leaving more
     genotype coherence to carry across generations.
  2. **Scales G to find the ceiling.** It **sweeps** generations G across
     ``[--gmin .. --gmax]`` in one invocation, computing g\\*(G) at each point, with
     the **ideal-clone confound curve mandatory** (M4, AC-S2.2): a noiseless
     exact-clone ``C(g)`` run alongside every G so approximate-cloning decay is
     separated from hardware decoherence.

Governing rule (QDEP §1, AC-S2.1): **noise is not a fitness function.** Selection is
absent (population = 1, CD-8), every mutation stays tied to a signed Q-EaaS receipt
(M7, fail-closed on ``QRNGUnavailable``), and "bigger" means *more coherent generations
under control*, never more entropy dressed as biology.

The structural delta vs S1: S1 runs a single G; S2 sweeps G, promotes the **ideal arm
to a first-class C(g) confound curve** (M4, forced onto the statevector sim even under
``--no-sim``), and exposes ``--pheno-coupling`` (Q1) and ``--width`` (Q4, off by default).
Everything else -- operators, correlation math, surrogate, Q-EaaS schedule, g\\* rule --
is the S1 code, copied verbatim (CD-1).

Provenance (CD-1 -- copied verbatim, not imported):
  * S0 operators/physics ``m_theta_matrix``/``m_gate``/``apply_clone``/``phenotype_map``/
    ``_z_expectation_statevector`` + constants ``ETA/PHI/PHENO_BASIS/UNIT_TOL`` are copied
    from ``artificial-life/code/stage0_reproduce.py`` (CD-1 parity, no import).
  * ``temporal_correlation``/``_mutation_schedule``/``build_lineage_quantum``/
    ``sample_quantum_arm``/``run_classical_surrogate``/``run_ideal``/``run_once``/
    ``compute_gstar``/``main`` skeleton copied from ``artificial-life/code/stage1_temporal.py``.
  * the ideal-reference-on-statevector pattern from ``QuantumLife/code/sim_ideal_sign.py``,
    the per-generation mean/std-over-repeats aggregation + summary writer from
    ``QuantumLife/code/research_qtree.py`` (S1 already ports these; S2 extends to a per-G sweep).
  * the ``pipeline_common`` sys.path probe + stub fallback ported from ``stage1_temporal.py`` (CD-2, CD-9).

Usage:
    cd artificial-life/code
    python stage2_scale.py --gmin 2 --gmax 12 --shots 8192 --seed 100 --repeats 8 \\
        --arm both --name qdep_s2
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
# known location (ported from stage1_temporal.py). Under --sim we never call the
# backend hooks, but the real import is preferred when present so the hardware
# path Just Works; on a backend-less box we fall back to the stub so this file
# stays importable in --sim.
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
# separate research_runs dir, sibling of code/ (ported idiom, S0/S1)
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"      # Q5: no localhost fallback

# offset between the independent lineages pooled by --width (Q4); coprime with any
# realistic seed so the classical surrogate streams stay disjoint.
_WIDTH_SEED_STEP = 100003

# ---- fixed physics constants (copied verbatim from stage0_reproduce.py, CD-1) ----
ETA = 0.9                       # per-generation <sigma_z> contraction from U_M (Q1)
PHI = math.acos(ETA)            # clone Ry angle: eta = cos(phi)
PHENO_BASIS = 0.0               # phenotype-map basis; 0 => pheno tracks genotype exactly (Q2)
UNIT_TOL = 0.03                 # operator-equivalence L1 tolerance

M_THETA_SPEC = "[[cos t, sin t], [sin t, -cos t]]"
U_M_SPEC = f"Ry(phi={PHI:.4f}) on fresh ancilla + CX(parent->ancilla); eta=cos(phi)={ETA}"
TRAIT_BASIS_DEFAULT = math.pi / 4   # off-diagonal trait readout (SETUP-FIX, see note below)

# --- SETUP-FIX (2026-08-19) -------------------------------------------------
# Same fix as stage1_temporal.py, propagated here. The original S2 quantum arm
# mid-circuit-measured a phenotype ancilla every generation (a proxy Z-measure
# that collapsed the lineage into a classical Markov chain) and read the trait
# diagonal -- so the coherent arm was physically identical to the surrogate and
# g* pinned at 1. Fix: (a) DEFER all readout to circuit end (chain stays
# unitary); (b) read the trait OFF-DIAGONAL (TRAIT_BASIS). The surrogate is the
# same circuit with an honest per-generation measure-and-resend in the SAME
# basis. g* aggregation is over the NORMALIZED c(g), not raw C(g). The old
# --pheno-coupling "weak peek" is now moot (no mid-circuit peek at all) and is
# retained only as a stamped no-op for provenance parity.


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


def phenotype_map(qc: QuantumCircuit, genotype: int, pheno_ancilla: int,
                  pheno_coupling: float = 1.0) -> None:
    """Genotype->phenotype ancilla map (CD-3), with the S2 tunable coupling (Q1).

    S1's map is a fixed ``Ry(basis)`` + full ``CX``: measuring the phenotype ancilla each
    generation fully projects the genotype's <sigma_z>, re-collapsing the coherent lineage
    (this is exactly why S1 got g\\*=1). S2 scales the genotype->phenotype coupling with
    ``pheno_coupling`` in (0, 1]:

      * ``alpha >= 1.0`` -> the bare ``CX`` -- S1's full projection, **byte-identical** (plan §6).
      * ``alpha < 1.0``  -> a controlled partial rotation ``CRY(alpha*pi)`` -- a *weak peek*
        that leaves more genotype coherence to carry to the next generation (plan §7).

    With PHENO_BASIS = 0 the ancilla starts aligned so the phenotype tracks the genotype.
    The readout ``T_g`` is still a {0,1} bit but a weaker peek -- its <sigma_z> estimate has
    more variance, hence the larger ``--shots`` at scale (Q6).
    """
    qc.ry(PHENO_BASIS, pheno_ancilla)
    if pheno_coupling >= 1.0:
        qc.cx(genotype, pheno_ancilla)                     # S1 full projection (byte-identical)
    else:
        qc.cry(pheno_coupling * math.pi, genotype, pheno_ancilla)   # weak peek (Q1)


def _z_expectation_statevector(qc: QuantumCircuit, qubit: int) -> float:
    """Exact <sigma_z> of ``qubit`` from the noiseless statevector (no shot noise)."""
    n = qc.num_qubits
    label = ["I"] * n
    label[n - 1 - qubit] = "Z"   # qiskit Pauli label is qubit (n-1)..0, left to right
    op = SparsePauliOp("".join(label))
    return float(np.real(Statevector(qc).expectation_value(op)))


# ---------------------------------------------------------------------------
# Temporal correlation (§7, CD-3) -- copied verbatim from stage1_temporal.py.
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
# copied verbatim from stage1_temporal.py.
# ---------------------------------------------------------------------------
def _mutation_schedule(client: QRNGClient, n_slots: int, mut_scale: float
                       ) -> tuple[list[float], list[dict]]:
    """Draw one mutation angle per generation from certified Q-EaaS bytes.

    Fetch 32-byte blocks (API: 32 <= size <= 4096) until ``4 * n_slots`` bytes are in
    hand, decode ``resp.data`` hex, and derive ``theta_g = mut_scale * (u32 / 2**32)``
    from a disjoint 4-byte slice per generation (uniform in [0, mut_scale), matching S0's
    ``random.uniform(0, mut_scale)`` magnitude so the lifetime decay stays monotone).

    Returns ``(theta_seq, entropy_provenance)``; both arms of a repeat consume the SAME
    ``theta_seq`` at matched positions (CD-4). S2 fetches once for ``gmax`` and slices per G
    (§7), so smaller-G lineages are exact prefixes. Fail-closed: ``QRNGUnavailable``
    propagates and aborts the run (CD-7) -- never a silent PRNG fallback.
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
# copied from stage1_temporal.py; S2 adds the --pheno-coupling knob (Q1).
# ---------------------------------------------------------------------------
def build_lineage_quantum(theta_seq: list[float], n_slots: int,
                          trait_basis: float = TRAIT_BASIS_DEFAULT) -> QuantumCircuit:
    """Coherent lineage, DEFERRED measurement, off-diagonal trait readout (SETUP-FIX).

    Registers: genotype chain ``q[0..n_slots-1]`` + classical ``c(n_slots)``. The whole
    lineage is built UNITARILY (per generation: ``apply_clone`` the parent, mutate with
    ``m_gate(theta_g)``). NO mid-circuit measurement -- every genotype stays coherent so it
    can seed its child and still be read at the end. Only then is each genotype rotated into
    the trait basis (``Ry(-basis)`` so ``measure`` reports ``cos(basis) Z + sin(basis) X``)
    and measured. Column g of a shot record is ``T_g``. Identical to stage1_temporal.py's
    fixed builder.
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


def sample_quantum_arm(qc: QuantumCircuit, shots: int, args: argparse.Namespace,
                       backend: Any, qubit_list: list[int],
                       force_sim: bool = False) -> list[str]:
    """Dispatch the quantum lineage circuit: --sim statevector or Heron-r2 run_hw.

    ``force_sim`` pins the statevector path even under ``--no-sim`` -- used by the ideal
    confound arm (M4), which must be the *same circuit* run noiselessly alongside the
    decohered hardware quantum arm. Returns one ``T_0...T_G`` string per shot. Qiskit's
    little-endian count key is ``c[G]...c[0]``; reversing gives ``c[0]...c[G]`` so column g
    maps to generation g.
    """
    if args.sim or force_sim:
        counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
        fields: list[str] = []
        for bitstr, cnt in counts.items():
            rec = bitstr.replace(" ", "")[::-1]             # c[0..G]
            fields.extend([rec] * cnt)
        return fields
    # hardware: preset pass manager + sampler (ported research_qtree.run_hw). Pin the
    # layout only when the chain matches the circuit width, else let opt-3 route.
    init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=init)
    isa = pm.run(qc)
    raw_meas, _jobs, _qs = run_sampler(backend, isa, shots)
    return [s[::-1] for s in raw_meas]                       # register 'c', reversed


# ---------------------------------------------------------------------------
# Classical surrogate arm -- measure-and-resend (§7, AC-S2.1, Q3)
# copied verbatim from stage1_temporal.py.
# ---------------------------------------------------------------------------
def build_lineage_classical(theta_seq: list[float], n_slots: int,
                            trait_basis: float = TRAIT_BASIS_DEFAULT) -> QuantumCircuit:
    """Measure-and-resend surrogate as a circuit (SETUP-FIX): same clone+mutate ops as the
    quantum arm, but after each genotype is formed it is MEASURED in the trait basis and the
    outcome re-prepared as a separable trait eigenstate before it seeds the child
    (``Ry(-basis); measure->c[g]; Ry(+basis)`` -- an entanglement-breaking classical
    broadcast of one bit per generation). Everything else matches the quantum arm; only
    coherence is destroyed. Identical to stage1_temporal.py's fixed surrogate.
    """
    geno = QuantumRegister(n_slots, "q")
    cr = ClassicalRegister(n_slots, "c")
    qc = QuantumCircuit(geno, cr)
    qc.append(m_gate(theta_seq[0]), [0])
    for g in range(n_slots):
        if g > 0:
            apply_clone(qc, parent=g - 1, ancilla=g)
            qc.append(m_gate(theta_seq[g]), [g])
        if abs(trait_basis) > 1e-12:
            qc.ry(-trait_basis, g)
        qc.measure(g, cr[g])                                # record T_g AND collapse (resend)
        if abs(trait_basis) > 1e-12:
            qc.ry(trait_basis, g)                           # re-prep separable trait eigenstate
    return qc


def sample_circuit(qc: QuantumCircuit, shots: int) -> list[str]:
    """Statevector-sim a measurement circuit; one ``T_0...T_G`` record per shot (reversed to
    c[0..G]). Used for the classical surrogate (always sim -- a classical null, no QPU)."""
    counts = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    fields: list[str] = []
    for bitstr, cnt in counts.items():
        fields.extend([bitstr.replace(" ", "")[::-1]] * cnt)
    return fields


# ---------------------------------------------------------------------------
# Ideal cross-check helpers -- kept verbatim from stage1_temporal.py for the
# S1-style per-gen sanity print (CD-1 parity). The first-class confound *curve*
# (M4) is run_ideal_correlation below.
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

    Thin S1-parity wrapper for a sanity print; the confound *curve* (M4) is
    ``run_ideal_correlation`` (the sampled C(g) apples-to-apples with the hardware arms).
    """
    out: list[float] = []
    for g in range(n_slots):
        qc = _build_generation_nomeasure(g, theta_seq)
        out.append(_z_expectation_statevector(qc, qubit=g + 1))
    return out


# ---------------------------------------------------------------------------
# Ideal-clone confound CURVE (M4, AC-S2.2) -- the key S2 promotion of run_ideal.
# ---------------------------------------------------------------------------
def run_ideal_correlation(theta_seq: list[float], n_slots: int, args: argparse.Namespace,
                          gmax: int, width: int = 1) -> tuple[list[float], dict]:
    """Noiseless exact-clone confound curve (M4, AC-S2.2).

    Builds the **same** ``build_lineage_quantum`` circuit as the quantum arm (same
    ``--pheno-coupling``), samples it on the statevector sim (``force_sim=True``) so it runs
    noiselessly **even under --no-sim**, and computes the per-generation trait <sigma_z> and
    the full ``temporal_correlation`` C(g) with the identical arithmetic used for the two
    hardware arms -- apples-to-apples. On a hardware run its C(g) sits above the decohered
    quantum arm's; the quantum-minus-ideal gap is the hardware decoherence, the ideal decay
    alone is approximate-cloning (plan §7).
    """
    qc = build_lineage_quantum(theta_seq, n_slots, args.trait_basis)
    ideal_qubits = list(range(n_slots))
    fields: list[str] = []
    for w in range(max(1, width)):
        fields += sample_quantum_arm(qc, args.shots, args, backend=None,
                                     qubit_list=ideal_qubits, force_sim=True)
    M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(
        len(fields), n_slots)
    p = ((M - ord("0")).astype(np.float64)).mean(axis=0)
    traits = [round(1.0 - 2.0 * float(p[g]), 6) for g in range(n_slots)]
    corr = temporal_correlation(fields, gmax)
    return traits, corr


# ---------------------------------------------------------------------------
# Per-(arm, repeat, G) run -- ported stage1_temporal.run_once; S2 threads G,
# slices the schedule, routes the ideal arm through the confound curve, and
# stamps meta.pheno_coupling + the G{G} filename token (§4/§6).
# ---------------------------------------------------------------------------
def run_once(args: argparse.Namespace, seed: int, arm: str, G: int,
             theta_seq_full: list[float], provenance_full: list[dict],
             backend: Any, backend_name: str, calib: Any,
             qubit_list: list[int]) -> tuple[dict, str]:
    """Run one arm at one seed at one G; build/write the §4 run.json; return (run, path)."""
    random.seed(seed)
    theta_seq = theta_seq_full[:G + 1]           # nested-schedule slice (CD-4, §7)
    provenance = provenance_full[:G + 1]
    n_slots = G + 1
    width = max(1, args.width)
    corr_cap = args.corr_gmax if args.corr_gmax is not None else G
    gmax = min(corr_cap, n_slots - 1)

    # the ideal confound arm is always run on the statevector sim (M4, force_sim)
    if arm == "ideal":
        run_backend, run_sim = "sim", True
    else:
        run_backend, run_sim = backend_name, bool(args.sim)

    if arm == "ideal":
        traits, corr = run_ideal_correlation(theta_seq, n_slots, args, gmax, width)
        gens = [{"gen": g, "trait_sigmaz": round(traits[g], 6),
                 "shots": args.shots * width} for g in range(n_slots)]
        print(f"  seed {seed} [    ideal]  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")
    else:
        fields: list[str] = []
        for w in range(width):                    # parallel INDEPENDENT lineages (Q4)
            if arm == "quantum":
                qc = build_lineage_quantum(theta_seq, n_slots, args.trait_basis)
                fields += sample_quantum_arm(qc, args.shots, args, backend, qubit_list)
            elif arm == "classical":
                qc = build_lineage_classical(theta_seq, n_slots, args.trait_basis)
                fields += sample_circuit(qc, args.shots)     # always sim (classical null)
            else:
                raise ValueError(f"unknown arm {arm!r}")
        M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(
            len(fields), n_slots)
        p = ((M - ord("0")).astype(np.float64)).mean(axis=0)   # P(bit=1) per generation
        gens = [{"gen": g, "trait_sigmaz": round(1.0 - 2.0 * float(p[g]), 6),
                 "shots": args.shots * width} for g in range(n_slots)]
        corr = temporal_correlation(fields, gmax)
        print(f"  seed {seed} [{arm:>9}]  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")

    run = {
        "meta": {
            "project": "artificial-life",
            "study": "coherence-depth-genealogy",
            "arm": arm,
            "backend": run_backend,
            "sim": run_sim,
            "timestamp": timestamp(),
            "seed": seed,
            "generations": G,                     # this run's G (varies across the sweep)
            "shots": args.shots,
            "width": width,
            "pheno_coupling": args.pheno_coupling,
            "trait_basis": args.trait_basis,
            "mut_scale": args.mut_scale,
            "corr_gmax": gmax,
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
        OUTPUT_DIR,
        f"{args.name}_{arm}_G{G}_{run_backend}_seed{seed}_{ts}_run.json")
    with open(out_path, "w") as f:
        json.dump(run, f, indent=2, default=str)
    print(f"  -> {out_path}")
    return run, out_path


# ---------------------------------------------------------------------------
# g* (CD-5) -- copied verbatim from stage1_temporal.py.
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
# Per-G aggregation (M3/AC-S2.4) -- factored from stage1_temporal.main so the
# sweep can call it once per G.
# ---------------------------------------------------------------------------
def _aggregate_per_generation(corr_by_arm: dict[str, list[list[float]]], n_slots: int,
                              stat_arms: list[str]) -> tuple[list[dict], dict]:
    """Aggregate raw C(g) arrays over repeats into per-gen mean/std and g* (k=2/k=3).

    ``mat`` is shape ``(repeats x n_slots)`` per arm; ``mean/std(ddof=0)`` over axis 0.
    ``sigma[g] = sqrt(std_q^2 + std_cl^2)``; g* needs both quantum and classical arms
    (else ``{None, None}``). Aggregation is over the **raw** C(g) arrays (matches S1).
    """
    means: dict[str, np.ndarray] = {}
    stds: dict[str, np.ndarray] = {}
    for a in stat_arms:
        mat = np.array(corr_by_arm[a])            # (repeats x n_slots)
        means[a] = mat.mean(axis=0)
        stds[a] = mat.std(axis=0, ddof=0)
    per_generation: list[dict] = []
    for g in range(n_slots):
        per_generation.append({
            "gen": g,
            "C_g_mean": {a: round(float(means[a][g]), 6) for a in stat_arms},
            "C_g_std": {a: round(float(stds[a][g]), 6) for a in stat_arms},
        })
    if "quantum" in means and "classical" in means:
        sigma = [math.sqrt(float(stds["quantum"][g]) ** 2 + float(stds["classical"][g]) ** 2)
                 for g in range(n_slots)]
        Cq = means["quantum"].tolist()
        Ccl = means["classical"].tolist()
        gstar = {"k2": compute_gstar(Cq, Ccl, sigma, 2),
                 "k3": compute_gstar(Cq, Ccl, sigma, 3)}
    else:
        gstar = {"k2": None, "k3": None}
    return per_generation, gstar


# ---------------------------------------------------------------------------
# main -- ported stage1_temporal.main; S2 adds the G sweep + confound curve.
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
    ap = argparse.ArgumentParser(description="QDEP Stage 2 -- G-sweep g*, ideal-clone "
                                             "confound curve (M4), tunable phenotype coupling.")
    ap.add_argument("--gmin", type=int, default=2, help="smallest G in the sweep (>=2)")
    ap.add_argument("--gmax", type=int, default=12,
                    help="largest G in the sweep (sim default 12 = 26 statevector qubits, Q6)")
    ap.add_argument("--width", type=int, default=1,
                    help="parallel INDEPENDENT lineages pooled for tighter sigma (Q4; off=1)")
    ap.add_argument("--pheno-coupling", dest="pheno_coupling", type=float, default=0.5,
                    help="[no-op since SETUP-FIX] retained for provenance parity; "
                         "readout is now deferred, not a mid-circuit peek")
    ap.add_argument("--trait-basis", dest="trait_basis", type=float,
                    default=TRAIT_BASIS_DEFAULT,
                    help="trait readout basis in radians (SETUP-FIX): 0=diagonal sigma_z "
                         "(classically clonable, g*=1), pi/4=off-diagonal (default, real gap)")
    ap.add_argument("--sv-max-qubits", dest="sv_max_qubits", type=int, default=26,
                    help="statevector qubit ceiling; abort if 2*(gmax+1) exceeds it (Q6)")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=100, help="base; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=8, help="sigma for g* (CD-5)")
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--arm", choices=["quantum", "classical", "both", "ideal"],
                    default="both", help="ideal is always run for M4 regardless")
    ap.add_argument("--corr-gmax", dest="corr_gmax", type=int, default=None,
                    help="max g for C(g) per G (default = that G)")
    ap.add_argument("--k", type=int, default=2, help="sigma multiplier (k=3 also reported)")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.1,
                    help="max mutation angle per generation, radians")
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=None,
                    help="Q-EaaS base URL (Q5); default env QEAAS_API_URL else "
                         f"{QEAAS_URL_DEFAULT}")
    ap.add_argument("--name", type=str, default="qdep_s2")
    args = ap.parse_args()

    if args.gmin < 2:
        print(f"[S2 ABORT] --gmin {args.gmin} < 2: the g>=1 correlation domain is trivial "
              "below G=2 (C(0) is the anchor). Use --gmin >= 2.")
        raise SystemExit(1)
    if args.gmax < args.gmin:
        print(f"[S2 ABORT] --gmax {args.gmax} < --gmin {args.gmin}.")
        raise SystemExit(1)
    if not (0.0 < args.pheno_coupling <= 1.0):
        print(f"[S2 ABORT] --pheno-coupling {args.pheno_coupling} not in (0, 1] (Q1).")
        raise SystemExit(1)

    n_slots_max = args.gmax + 1                  # largest lineage in the sweep
    n_q = n_slots_max                            # genotype chain only (deferred readout, SETUP-FIX)

    # The ideal confound curve (M4, AC-S2.2) is MANDATORY at every G and is computed on
    # the statevector sim regardless of --sim, so the qubit ceiling always bites (§9).
    if n_q > args.sv_max_qubits:
        print(f"[S2 ABORT] --gmax {args.gmax} needs {n_q} statevector qubits > "
              f"--sv-max-qubits {args.sv_max_qubits}. The ideal-clone confound curve "
              f"(M4, AC-S2.2) is computed on the statevector sim and is mandatory at every G. "
              f"Reduce --gmax (<= {args.sv_max_qubits - 1}) or raise --sv-max-qubits.")
        raise SystemExit(1)

    base_arms = ["quantum", "classical"] if args.arm == "both" else [args.arm]
    arms = list(base_arms) + (["ideal"] if "ideal" not in base_arms else [])

    # --- certified Q-EaaS client (CD-7, fail-closed) -------------------------
    api_key = _read_env_key("QEAAS_API_KEY")
    if not api_key:
        print("[S2 ABORT] QEAAS_API_KEY not set (env or artificial-life/.env) -- "
              "S2 is fail-closed on entropy provenance (CD-7). No PRNG fallback.")
        raise SystemExit(1)
    qrng_url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
    client = QRNGClient(qrng_url, api_key)
    print(f"Q-EaaS  : {qrng_url}  (fail-closed, no PRNG fallback)")
    try:  # fast /health probe up front -- abort clearly instead of blocking on fetch
        h = client.health()
    except QRNGUnavailable as exc:
        print(f"[S2 ABORT] Q-EaaS health check failed: {exc} -- no PRNG fallback (CD-7).")
        raise SystemExit(1)
    print(f"          health: {h.status} / entropy {h.quantum_entropy_level} / "
          f"pool {h.pool_bytes_remaining} bytes")
    if h.status != "ok":
        print(f"[S2 ABORT] Q-EaaS status {h.status!r} (entropy {h.quantum_entropy_level!r}).")
        raise SystemExit(1)

    # --- backend / qubit layout (sized for the largest G) --------------------
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

    print(f"Sweep   : G in [{args.gmin}..{args.gmax}]  arms={arms}  "
          f"pheno_coupling={args.pheno_coupling}  width={args.width}  repeats={args.repeats}")

    # --- fetch the full gmax schedule ONCE per repeat; slice per G (CD-4, §7) --
    schedules: list[tuple[list[float], list[dict]]] = []
    for r in range(args.repeats):
        try:
            theta_full, prov_full = _mutation_schedule(client, n_slots_max, args.mut_scale)
        except QRNGUnavailable as exc:      # fail-closed (CD-7)
            print(f"[S2 ABORT] Q-EaaS unavailable: {exc} -- no PRNG fallback (CD-7).")
            raise SystemExit(1)
        schedules.append((theta_full, prov_full))

    # --- sweep loop: one g*(G) per G, error bars over --repeats ---------------
    run_files: list[str] = []
    sweep: list[dict] = []
    for G in range(args.gmin, args.gmax + 1):
        n_slots = G + 1
        print(f"\n=== G = {G}  ({n_slots} generation slots) ===")
        corr_by_arm: dict[str, list[list[float]]] = {a: [] for a in arms}
        for r in range(args.repeats):
            seed = args.seed + r
            theta_full, prov_full = schedules[r]
            print(f"  -- repeat {r + 1}/{args.repeats}  (seed {seed}) --")
            for arm in arms:
                run, path = run_once(args, seed, arm, G, theta_full, prov_full,
                                     backend, backend_name, calib, qubit_list)
                run_files.append(os.path.basename(path))
                # aggregate NORMALIZED c(g) (SETUP-FIX): raw C(g) is at the C0 noise floor
                corr_by_arm[arm].append(run["correlation_temporal"]["c"])

        stat_arms = [a for a in ("quantum", "classical", "ideal")
                     if a in corr_by_arm and corr_by_arm[a] and corr_by_arm[a][0]]
        per_generation, gstar = _aggregate_per_generation(corr_by_arm, n_slots, stat_arms)
        sweep.append({"G": G, "per_generation": per_generation, "gstar": gstar})
        if gstar["k2"] is not None:
            print(f"  g*(G={G}) : k2={gstar['k2']}  k3={gstar['k3']}")
        else:
            print(f"  g*(G={G}) : needs both quantum and classical arms (--arm both).")

    # --- summary.json: sweep[] + top-level = largest-G entry (§4 back-compat) --
    top = sweep[-1] if sweep else {"per_generation": [], "gstar": {"k2": None, "k3": None}}
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
                "gmin": args.gmin,
                "gmax": args.gmax,
                "shots": args.shots,
                "corr_gmax": args.corr_gmax,
                "k": args.k,
                "pheno_coupling": args.pheno_coupling,
                "width": args.width,
                "run_files": run_files,
            },
            "sweep": sweep,
            "per_generation": top["per_generation"],
            "gstar": top["gstar"],
        }, f, indent=2, default=str)

    # --- report --------------------------------------------------------------
    print("\n--- DONE (sweep) ---")
    print("    G   g*(k2)  g*(k3)")
    for entry in sweep:
        gs = entry["gstar"]
        k2 = gs["k2"] if gs["k2"] is not None else "-"
        k3 = gs["k3"] if gs["k3"] is not None else "-"
        print(f"  {entry['G']:>3}   {str(k2):>5}   {str(k3):>5}")
    if top["gstar"]["k2"] is not None:
        print(f"\nHeadline g* @ G={args.gmax} (k=2) = {top['gstar']['k2']}    "
              f"(k=3) = {top['gstar']['k3']}")
    else:
        print("\nHeadline g*: needs both quantum and classical arms (--arm both).")
    print(f"Summary file : {sum_path}")


if __name__ == "__main__":
    main()
