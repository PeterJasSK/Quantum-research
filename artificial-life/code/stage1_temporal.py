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
def build_lineage_quantum(theta_seq: list[float], n_slots: int) -> QuantumCircuit:
    """One dynamic circuit descending the whole lineage; read T_g per generation.

    Registers: genotype chain ``q[0..n_slots-1]`` + one fresh phenotype ancilla
    ``p[g]`` per generation + classical ``c(n_slots)``. Per generation g:
    ``apply_clone`` the parent (S0 U_M), mutate with ``m_gate(theta_g)``, ``phenotype_map``
    into the fresh ancilla, and mid-circuit ``measure`` it into ``c[g]``. A shot's record
    is ``T_0...T_G``. Feed-forward is not needed for S1 readout (it enters at S3 teleport);
    only the dynamic ClassicalRegister scaffolding is borrowed from the teleport fork.
    """
    geno = QuantumRegister(n_slots, "q")
    phen = QuantumRegister(n_slots, "p")
    cr = ClassicalRegister(n_slots, "c")
    qc = QuantumCircuit(geno, phen, cr)
    # integer indices: geno[g] = g, phen[g] = n_slots + g (declaration order)
    for g in range(n_slots):
        if g == 0:
            qc.append(m_gate(theta_seq[0]), [0])            # genotype 0: |0> then mutate
        else:
            apply_clone(qc, parent=g - 1, ancilla=g)        # coherent clone parent->child
            qc.append(m_gate(theta_seq[g]), [g])            # mutate the child
        phenotype_map(qc, genotype=g, pheno_ancilla=n_slots + g)
        qc.measure(n_slots + g, cr[g])                      # mid-circuit trait readout
    return qc


def sample_quantum_arm(qc: QuantumCircuit, shots: int, args: argparse.Namespace,
                       backend: Any, qubit_list: list[int]) -> list[str]:
    """Dispatch the quantum lineage circuit: --sim statevector or Heron-r2 run_hw.

    Returns one ``T_0...T_G`` string per shot. Qiskit's little-endian count key is
    ``c[G]...c[0]``; reversing gives ``c[0]...c[G]`` so column g maps to generation g.
    """
    if args.sim:
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
# Classical surrogate arm -- measure-and-resend (§7, AC-S1.2, Q3)
# ---------------------------------------------------------------------------
def run_classical_surrogate(theta_seq: list[float], n_slots: int, shots: int,
                            seed: int) -> list[str]:
    """Measure-and-resend null: per generation, re-prepare a SEPARABLE child from the
    parent's classically-communicated trait bit (Q3: <sigma_z>_child = eta*(1-2*bit)),
    then apply the same ``m_gate(theta_g)`` and re-measure.

    Matched to the quantum arm on everything except coherence: same theta_seq, same eta,
    same per-generation readout. Because each child is re-prepared from ONLY the previous
    trait bit (a Markov-order-1 chain), the T_0-T_g correlation decays faster than the
    coherent arm -- the gap is g\\* (M3). Produces one ``T_0...T_G`` string per shot.

    The single-qubit trait algebra: M(theta) sigma_z M(theta) = cos(2t) sigma_z +
    sin(2t) sigma_x, and a separably re-prepped Ry child has <sigma_x> = sqrt(1-z^2) >= 0.
    """
    rng = random.Random(seed)
    fields: list[str] = []
    for _ in range(shots):
        bits: list[str] = []
        prev_bit = 0
        for g in range(n_slots):
            if g == 0:
                z_pre, x_pre = 1.0, 0.0                      # genotype 0 from |0>
            else:
                z_pre = ETA * (1.0 - 2.0 * prev_bit)         # eta-contraction via classical bit
                x_pre = math.sqrt(max(0.0, 1.0 - z_pre * z_pre))
            th = theta_seq[g]
            z_after = math.cos(2 * th) * z_pre + math.sin(2 * th) * x_pre
            p1 = (1.0 - z_after) / 2.0                       # P(T_g = 1)
            b = 1 if rng.random() < p1 else 0
            bits.append(str(b))
            prev_bit = b
        fields.append("".join(bits))
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

    if arm == "ideal":
        ideal = run_ideal(theta_seq, n_slots)
        gens = [{"gen": g, "trait_sigmaz": round(ideal[g], 6), "shots": 0}
                for g in range(n_slots)]
        corr = {"C": [], "c": [], "C0": 0.0, "gmax": gmax}   # bits absent -> no C(g)
        print(f"  seed {seed} [ideal]  trait_sigmaz: "
              f"{', '.join(f'{v:+.3f}' for v in ideal)}")
    else:
        if arm == "quantum":
            qc = build_lineage_quantum(theta_seq, n_slots)
            fields = sample_quantum_arm(qc, args.shots, args, backend, qubit_list)
        elif arm == "classical":
            fields = run_classical_surrogate(theta_seq, n_slots, args.shots, seed)
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

    # --- backend / qubit layout ----------------------------------------------
    n_q = 2 * n_slots                            # genotype chain + phenotype ancillas
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
                corr_by_arm[arm].append(run["correlation_temporal"]["C"])

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
