#!/usr/bin/env python3
"""Stage 3 (QDEP: Break the SWAP ceiling of an Inherited-Entanglement Genealogy).

S3 asks the follow-on question the epic reserved for last (plan §1): **does
teleport-routing the inheritance bond buy coherent generations that SWAP-routing
cannot, on the same chip?**

The mechanism (qdep-1 Stage 3, QDEP §6.4): a long-range entangling gate routed by a
**SWAP ladder** costs depth that *grows with the routed distance* -- depth spent out of
exactly the coherence budget ``g*`` measures. Replace the SWAP ladder with a
**teleported CNOT** (one Bell pair + two mid-circuit measures + classical feed-forward)
and the gate lands at **constant depth**, at the honest cost of ancilla qubits and
feed-forward latency (QDEP §6.4, AC-S3.3). The headline is **Δg\\*** =
``g*(teleport) - g*(swap)`` at matched settings (M5), evidenced by ``logical_depth`` per
routing (M6) -- teleport ~ constant, swap ∝ routed distance.

S3 changes exactly one thing vs S2: **how the inheritance (clone) bond's CX is routed on
the chip** -- SWAP ladder vs teleported constant-depth CNOT. Everything else (the frozen
S0 physics, the S1/S2 temporal machinery, the certified fail-closed Q-EaaS schedule, the
ideal-clone confound curve, the G-sweep) is the S2 code, copied verbatim (CD-1 parity).

**The one honest asymmetry (plan §7, §9).** Δg\\* is a **decoherence effect**. On a
*noiseless* statevector a SWAP ladder and a teleported CNOT are logically identical maps,
so they produce **identical** ``C(g)`` and **Δg\\* = 0 by construction**. The noiseless
``--sim`` run validates the *pipeline* and the *logical_depth* claim (M6) only; the Δg\\*
*signal* (M5) requires real Heron-r2 hardware or a noisy simulator (``--noise-model``).
This mirrors S2's "ideal ≡ quantum under ``--sim``" caveat and must be carried into S4.

Provenance (CD-1 -- copied verbatim, not imported):
  * everything inherited from ``artificial-life/code/stage2_scale.py`` (operators, temporal
    correlation, Q-EaaS schedule, classical surrogate, ideal-clone confound curve, g*, the
    per-generation aggregation and the G-sweep skeleton) is copied verbatim from S2, which
    in turn copied it from S0/S1 (CD-1 parity, no import).
  * ``_swap_cx`` copied verbatim from ``QuantumLife/code/research_qtree_swaplr.py:173``.
  * ``_teleport_cx`` copied verbatim from ``QuantumLife/code/research_qtree_teleport.py:201``.
  * ``resolve_bonds`` is the temporal re-aim of ``research_qtree_teleport.py:166`` (spatial
    slot pairs -> which generation bonds are routed long-range).
  * the ``pipeline_common`` sys.path probe + stub fallback ported from ``stage2_scale.py``
    (CD-2, CD-9).

Usage:
    cd artificial-life/code
    python stage3_teleport.py --gmin 2 --gmax 4 --bond-dist 3 --routing both \\
        --shots 8192 --seed 100 --repeats 8 --name qdep_s3
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
# known location (ported from stage2_scale.py). Under --sim we never call the
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
# separate research_runs dir, sibling of code/ (ported idiom, S0/S1/S2)
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"      # Q5: no localhost fallback

# offset between the independent lineages pooled by --width (Q4); coprime with any
# realistic seed so the classical surrogate streams stay disjoint.
_WIDTH_SEED_STEP = 100003

# AC-S3.3 honesty invariant: teleport is not a free bypass. Recorded in run.json and
# printed on every teleport arm.
ROUTING_COST = ("constant-depth long-range interaction at the cost of ancillas and "
                "classical feed-forward latency; not a free bypass")

# ---- fixed physics constants (copied verbatim from stage0_reproduce.py, CD-1) ----
ETA = 0.9                       # per-generation <sigma_z> contraction from U_M (Q1)
PHI = math.acos(ETA)            # clone Ry angle: eta = cos(phi)
PHENO_BASIS = 0.0               # phenotype-map basis; 0 => pheno tracks genotype exactly (Q2)
UNIT_TOL = 0.03                 # operator-equivalence L1 tolerance

M_THETA_SPEC = "[[cos t, sin t], [sin t, -cos t]]"
U_M_SPEC = f"Ry(phi={PHI:.4f}) on fresh ancilla + CX(parent->ancilla); eta=cos(phi)={ETA}"


# ---------------------------------------------------------------------------
# Operators (copied verbatim from stage2_scale.py / stage0_reproduce.py, CD-1)
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

    ``alpha >= 1.0`` -> the bare ``CX`` (S1 full projection, byte-identical);
    ``alpha < 1.0``  -> a controlled partial rotation ``CRY(alpha*pi)`` (weak peek).
    With PHENO_BASIS = 0 the ancilla starts aligned so the phenotype tracks the genotype.
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
# Temporal correlation (§7, CD-3) -- copied verbatim from stage2_scale.py.
# ---------------------------------------------------------------------------
def temporal_correlation(traits_by_shot: list[str], gmax: int) -> dict:
    """Connected two-point correlation of the per-shot lineage record, anchored at T_0.

        C(g) = <T_0 T_g> - <T_0><T_g>        (Q2: anchored at generation 0)
        C(0) = Var(T_0)                       (falls out of the anchored form)
        c(g) = C(g) / C(0)                    (normalised)

    ``traits_by_shot`` is a list of ``G+1``-bit strings ``T_0 T_1 ... T_G`` -- one row
    per shot, one column per generation. Raw shot matrix stays local.
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
# copied verbatim from stage2_scale.py.
# ---------------------------------------------------------------------------
def _mutation_schedule(client: QRNGClient, n_slots: int, mut_scale: float
                       ) -> tuple[list[float], list[dict]]:
    """Draw one mutation angle per generation from certified Q-EaaS bytes.

    Fetch 32-byte blocks until ``4 * n_slots`` bytes are in hand, decode hex, and derive
    ``theta_g = mut_scale * (u32 / 2**32)`` from a disjoint 4-byte slice per generation.
    Both arms of a repeat consume the SAME ``theta_seq`` at matched positions (CD-4).
    Fail-closed: ``QRNGUnavailable`` propagates and aborts the run (CD-7).
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
# Quantum arm base circuit -- one dynamic lineage (§5), copied verbatim from
# stage2_scale.py. USED UNCHANGED by the shared ideal-clone confound arm (M4),
# which is routing-independent (CD-4/CD-6). The routed variant is
# build_lineage_routed below.
# ---------------------------------------------------------------------------
def build_lineage_quantum(theta_seq: list[float], n_slots: int,
                          pheno_coupling: float = 1.0) -> QuantumCircuit:
    """One dynamic circuit descending the whole lineage; read T_g per generation.

    Registers: genotype chain ``q[0..n_slots-1]`` + one fresh phenotype ancilla
    ``p[g]`` per generation + classical ``c(n_slots)``. At ``pheno_coupling=1.0`` the
    circuit is byte-identical to S1's.
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
        phenotype_map(qc, genotype=g, pheno_ancilla=n_slots + g,
                      pheno_coupling=pheno_coupling)
        qc.measure(n_slots + g, cr[g])                      # mid-circuit trait readout
    return qc


# ---------------------------------------------------------------------------
# Routing primitives -- ported verbatim (CD-1). S3's single delta is HOW the
# inheritance (clone) CX is routed on the chip.
# ---------------------------------------------------------------------------
def _swap_cx(qc, lo, hi) -> None:
    """Long-range CNOT(lo -> hi) with lo < hi via a SWAP ladder.

    ported verbatim from QuantumLife/code/research_qtree_swaplr.py:173.

    Carry lo's state up to hi-1, CX onto hi, then reverse every SWAP so the
    register permutation is the identity and only the long-range CX remains.
    Cost ~ 2*(hi-lo) SWAPs -> O(distance) depth (the point of the baseline)."""
    for p in range(lo, hi - 1):
        qc.swap(p, p + 1)
    qc.cx(hi - 1, hi)
    for p in range(hi - 1, lo, -1):
        qc.swap(p - 1, p)


def _teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True) -> None:
    """Long-range CNOT(ctrl -> tgt) via one Bell pair + two mid-circuit measures.

    ported verbatim from QuantumLife/code/research_qtree_teleport.py:201.

    Ancillas a1 (staged near ctrl) and a2 (staged near tgt); tel[2k], tel[2k+1]
    hold the outcomes. Logically applies CX(ctrl, tgt) at constant depth; ctrl
    and tgt are never made physical neighbours.

    feedforward=True  : apply the X/Z Pauli corrections -> valid CX for ALL four
                        outcomes (the dynamic-circuit long-range gate).
    feedforward=False : skip corrections (HERALDED teleport). Only the tel==00
                        branch is the correct CX; the caller post-selects it.
                        The two branches are physically distinct paths, so on
                        noisy hardware the tel==00 subset traversed fewer/cleaner
                        operations -> a valid noise filter (see --herald)."""
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


def resolve_bonds(anchors: str, n_slots: int) -> list[int]:
    """Which generation clone-bonds are routed long-range (temporal re-aim, CD-1).

    Temporal adaptation of QuantumLife/code/research_qtree_teleport.py:166: there the
    helper returned spatial ``(slot, slot+dist)`` pairs; here it returns the set of
    generations ``g`` (1 <= g <= n_slots-1) whose clone bond ``CX(g-1 -> g)`` is routed
    long-range. ``"all"`` -> every generation bond; a comma list -> those generations,
    clamped to ``[1, n_slots-1]``.
    """
    lo, hi = 1, n_slots - 1
    if hi < lo:
        return []
    if anchors.strip().lower() == "all":
        return list(range(lo, hi + 1))
    out: list[int] = []
    for tok in anchors.split(","):
        tok = tok.strip()
        if not tok:
            continue
        g = int(tok)
        if lo <= g <= hi and g not in out:
            out.append(g)
    return sorted(out)


# ---------------------------------------------------------------------------
# S3 core delta: route the clone CX across a physical span (§6.6 / §7).
# ---------------------------------------------------------------------------
def apply_clone_routed(qc: QuantumCircuit, parent: int, ancilla: int, routing: str,
                       corridor: tuple[int, int] | None, tel: Any, k: int,
                       feedforward: bool, phi: float = PHI) -> int:
    """Wrap S2's ``apply_clone``: local ``Ry(phi)`` then route the parity CX (§6.6).

    ``routing``:
      * ``"direct"``   -> plain ``qc.cx(parent, ancilla)`` (the S2 baseline; ``bond_dist=1``
        reproduces S2 byte-for-byte -- the §8-D sanity control).
      * ``"swap"``     -> ``_swap_cx`` (O(distance) SWAP ladder baseline, AC-S3.1).
      * ``"teleport"`` -> ``_teleport_cx`` (constant depth + 2 ancillas/bond, AC-S3.1/3.3).

    ``corridor`` holds ``(a1, a2)`` (the two spacer qubits used as teleport ancillas).
    Returns the running teleport-bond counter ``k`` (advanced only on a teleport bond).
    """
    qc.ry(phi, ancilla)                       # local clone Ry -- unchanged from apply_clone
    if routing == "direct":
        qc.cx(parent, ancilla)
    elif routing == "swap":
        _swap_cx(qc, lo=parent, hi=ancilla)
    elif routing == "teleport":
        assert corridor is not None, "teleport routing needs a 2-qubit corridor"
        _teleport_cx(qc, ctrl=parent, tgt=ancilla, a1=corridor[0], a2=corridor[1],
                     tel=tel, k=k, feedforward=feedforward)
        k += 1
    else:
        raise ValueError(f"unknown routing {routing!r}")
    return k


def build_lineage_routed(theta_seq: list[float], n_slots: int, pheno_coupling: float,
                         bond_dist: int, routing: str, anchors: str,
                         feedforward: bool = True
                         ) -> tuple[QuantumCircuit, int, int]:
    """S2's ``build_lineage_quantum`` with the clone step swapped for ``apply_clone_routed``.

    Genotype qubits are strided by ``bond_dist`` so consecutive generations sit a physical
    span apart; the ``bond_dist - 1`` intervening qubits are idle spacers the SWAP ladder
    traverses (swap arm) or the teleport Bell-pair ancillas occupy (teleport arm). One
    phenotype ancilla per generation follows the strided spine; a ``tel`` classical register
    of width ``2*num_teleport_bonds`` holds the feed-forward / heralding outcomes.

    Returns ``(qc, logical_depth=qc.depth(), num_teleport_bonds)``. At ``bond_dist=1`` /
    ``routing="direct"`` the circuit is byte-identical to ``build_lineage_quantum`` (§8-D).
    """
    routed_gens = set(resolve_bonds(anchors, n_slots))
    # teleport needs 2 corridor ancillas -> bond_dist >= 3; at bond_dist <= 1 the routing
    # collapses to the direct S2 baseline (the parity control), so no teleport bonds exist.
    teleporting = (routing == "teleport" and bond_dist >= 3)
    num_teleport_bonds = len(routed_gens) if teleporting else 0

    spine_len = (n_slots - 1) * bond_dist + 1          # genotype spine + spacer corridor
    n_q = spine_len + n_slots                          # + one phenotype ancilla per gen
    qr = QuantumRegister(n_q, "q")
    cr = ClassicalRegister(n_slots, "c")
    tel = ClassicalRegister(2 * num_teleport_bonds, "tel") if num_teleport_bonds else None
    regs: list[Any] = [qr, cr] + ([tel] if tel is not None else [])
    qc = QuantumCircuit(*regs)

    def geno(g: int) -> int:
        return g * bond_dist

    def pheno(g: int) -> int:
        return spine_len + g

    k = 0
    for g in range(n_slots):
        if g == 0:
            qc.append(m_gate(theta_seq[0]), [geno(0)])          # genotype 0: |0> then mutate
        else:
            # per-generation routing: direct baseline unless this bond is routed long-range
            if bond_dist <= 1 or g not in routed_gens:
                gen_routing, corridor = "direct", None
            elif routing == "teleport" and teleporting:
                # a1 staged near parent, a2 staged near child (§6.6)
                corridor = ((g - 1) * bond_dist + 1, g * bond_dist - 1)
                gen_routing = "teleport"
            else:
                gen_routing, corridor = "swap", None
            k = apply_clone_routed(qc, parent=geno(g - 1), ancilla=geno(g),
                                   routing=gen_routing, corridor=corridor, tel=tel, k=k,
                                   feedforward=feedforward)
            qc.append(m_gate(theta_seq[g]), [geno(g)])          # mutate the child
        phenotype_map(qc, genotype=geno(g), pheno_ancilla=pheno(g),
                      pheno_coupling=pheno_coupling)
        qc.measure(pheno(g), cr[g])                             # mid-circuit trait readout
    return qc, qc.depth(), num_teleport_bonds


# ---------------------------------------------------------------------------
# Noisy Aer backend factory (Q7) -- lazy so an unset --noise-model keeps the
# statevector path and adds no import cost.
# ---------------------------------------------------------------------------
_NOISY_CACHE: dict[str, Any] = {}


def _get_noisy_backend(name: str) -> Any:
    """Build (once) a noisy Aer backend from a Fake Heron device (Q7)."""
    if name in _NOISY_CACHE:
        return _NOISY_CACHE[name]
    import qiskit_ibm_runtime.fake_provider as fp
    alias = {                                   # narrative "Heron" -> a concrete Fake device
        "fake_heron": "FakeFez", "heron": "FakeFez", "fake_heron_r2": "FakeFez",
        "fake_torino": "FakeTorino", "torino": "FakeTorino",
    }
    cls_name = alias.get(name.strip().lower(), name.strip())
    if not cls_name.startswith("Fake"):
        cls_name = "Fake" + cls_name[:1].upper() + cls_name[1:]
    fake = getattr(fp, cls_name)()
    backend = AerSimulator.from_backend(fake)
    _NOISY_CACHE[name] = backend
    return backend


# ---------------------------------------------------------------------------
# Hardware sampler that also reads the 'tel' register (heralded teleport) --
# ported from QuantumLife/code/research_qtree_teleport.py:415 (run_hw).
# ---------------------------------------------------------------------------
def _run_sampler_tel(backend: Any, isa: Any, shots: int) -> tuple[list[str], list[str]]:
    """SamplerV2 loop reading BOTH cregs: 'c' (genome, reversed) and 'tel' (NOT reversed).

    Mirrors QuantumLife run_hw so heralded shots can be post-selected. tel bit order is
    carried verbatim (not reversed) -- the post-select mask only checks all-zeros (plan §9).
    """
    from pipeline_common import Sampler, SHOTS_PER_JOB, qpu_seconds
    sampler = Sampler(mode=backend)
    genome: list[str] = []
    tel: list[str] = []
    remaining, ci = shots, 0
    while remaining > 0:
        chunk = min(SHOTS_PER_JOB, remaining)
        ci += 1
        job = sampler.run([isa], shots=chunk)
        print(f"  job {ci}: {job.job_id()} ({chunk:,} shots) ...", end="", flush=True)
        res = job.result()
        genome.extend(s[::-1] for s in res[0].data.c.get_bitstrings())
        tel.extend(res[0].data.tel.get_bitstrings())      # tel NOT reversed (plan §9)
        qs = qpu_seconds(job)
        print(f" done (qpu {0.0 if qs != qs else qs:.2f}s)")
        remaining -= chunk
    return genome, tel


def sample_quantum_arm(qc: QuantumCircuit, shots: int, args: argparse.Namespace,
                       backend: Any, qubit_list: list[int], force_sim: bool = False,
                       want_tel: bool = False) -> Any:
    """Dispatch the lineage circuit: --sim statevector/noisy Aer, or Heron-r2 hardware.

    ``force_sim`` pins the noiseless statevector path (the ideal confound arm, M4). Extends
    S2 in two ways: (a) under ``--sim`` with ``--noise-model`` set (and not ``force_sim``)
    the run targets a noisy Aer backend so a Δg* signal appears without QPU (Q7); (b) when
    ``want_tel`` (heralded teleport) it also reads the ``tel`` register and returns
    ``(fields, tel)``. Qiskit's little-endian count key is ``c[G]...c[0]``; reversing gives
    ``c[0]...c[G]``. With a ``tel`` register present, get_counts keys are ``"<tel> <c>"``
    (leftmost = last-registered = tel; rightmost = c) -- confirmed empirically.
    """
    if args.sim or force_sim:
        sim_backend = SIM
        if getattr(args, "noise_model", None) and not force_sim:
            sim_backend = _get_noisy_backend(args.noise_model)
        counts = sim_backend.run(transpile(qc, sim_backend), shots=shots).result().get_counts()
        fields: list[str] = []
        tels: list[str] = []
        for bitstr, cnt in counts.items():
            parts = bitstr.split()
            rec = parts[-1][::-1]                       # 'c' register (rightmost), reversed
            fields.extend([rec] * cnt)
            if want_tel:
                tel = parts[0] if len(parts) > 1 else ""  # 'tel' register, NOT reversed
                tels.extend([tel] * cnt)
        return (fields, tels) if want_tel else fields
    # hardware: preset pass manager + sampler. Pin the layout only when the chain matches
    # the circuit width, else let opt-3 route (teleport ancillas exceed the chain, §6).
    init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=init)
    isa = pm.run(qc)
    if want_tel:                                        # mirror teleport run_hw @415
        return _run_sampler_tel(backend, isa, shots)
    raw_meas, _jobs, _qs = run_sampler(backend, isa, shots)
    return [s[::-1] for s in raw_meas]                  # register 'c', reversed


# ---------------------------------------------------------------------------
# Classical surrogate arm -- measure-and-resend (§7, AC-S2.1, Q3); routing-
# independent (CD-4). Copied verbatim from stage2_scale.py.
# ---------------------------------------------------------------------------
def run_classical_surrogate(theta_seq: list[float], n_slots: int, shots: int,
                            seed: int) -> list[str]:
    """Measure-and-resend null: per generation, re-prepare a SEPARABLE child from the
    parent's classically-communicated trait bit (Q3: <sigma_z>_child = eta*(1-2*bit)),
    then apply the same ``m_gate(theta_g)`` and re-measure. Shared across routings.
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
# Ideal cross-check helpers -- kept verbatim from stage2_scale.py.
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
    """Exact-statevector <sigma_z>_p per generation (S0 _z_expectation_statevector)."""
    out: list[float] = []
    for g in range(n_slots):
        qc = _build_generation_nomeasure(g, theta_seq)
        out.append(_z_expectation_statevector(qc, qubit=g + 1))
    return out


# ---------------------------------------------------------------------------
# Ideal-clone confound CURVE (M4, AC-S2.2/CD-6) -- routing-independent (CD-4),
# copied verbatim from stage2_scale.py (uses the UNROUTED build_lineage_quantum).
# ---------------------------------------------------------------------------
def run_ideal_correlation(theta_seq: list[float], n_slots: int, args: argparse.Namespace,
                          gmax: int, width: int = 1) -> tuple[list[float], dict]:
    """Noiseless exact-clone confound curve (M4, AC-S2.2), shared across both routings.

    Builds the same UNROUTED ``build_lineage_quantum`` circuit (routing is irrelevant to
    the noiseless confound, CD-4), samples it on the statevector sim (``force_sim=True``)
    so it runs noiselessly even under ``--no-sim``/``--noise-model``, and computes the
    per-generation trait <sigma_z> and full ``temporal_correlation`` C(g).
    """
    qc = build_lineage_quantum(theta_seq, n_slots, args.pheno_coupling)
    ideal_qubits = list(range(2 * n_slots))
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
# Per-(arm, repeat, G) run -- ported stage2_scale.run_once; S3 branches the two
# routed quantum arms through build_lineage_routed and stamps the routing meta.
# ---------------------------------------------------------------------------
def run_once(args: argparse.Namespace, seed: int, arm: str, G: int,
             theta_seq_full: list[float], provenance_full: list[dict],
             backend: Any, backend_name: str, calib: Any,
             qubit_list: list[int]) -> tuple[dict, str]:
    """Run one arm at one seed at one G; build/write the §4 run.json; return (run, path).

    ``arm`` is one of ``quantum_swap`` / ``quantum_teleport`` / ``classical`` / ``ideal``.
    """
    random.seed(seed)
    theta_seq = theta_seq_full[:G + 1]           # nested-schedule slice (CD-4, §7)
    provenance = provenance_full[:G + 1]
    n_slots = G + 1
    width = max(1, args.width)
    corr_cap = args.corr_gmax if args.corr_gmax is not None else G
    gmax = min(corr_cap, n_slots - 1)

    # routing meta defaults (absent/None on classical/ideal, §4)
    routing: str | None = None
    logical_depth: int | None = None
    num_teleport_bonds = 0
    herald_frac: float | None = None

    # the ideal confound arm is always run on the statevector sim (M4, force_sim)
    if arm == "ideal":
        run_backend, run_sim = "sim", True
    else:
        run_backend, run_sim = backend_name, bool(args.sim)

    if arm == "ideal":
        traits, corr = run_ideal_correlation(theta_seq, n_slots, args, gmax, width)
        gens = [{"gen": g, "trait_sigmaz": round(traits[g], 6),
                 "shots": args.shots * width} for g in range(n_slots)]
        print(f"  seed {seed} [           ideal]  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")
    elif arm in ("quantum_swap", "quantum_teleport"):
        routing = arm.split("_", 1)[1]                  # "swap" | "teleport"
        want_tel = bool(args.herald) and routing == "teleport"
        feedforward = not args.herald                   # herald drops feed-forward (§6)
        fields: list[str] = []
        kept_total = 0
        n_total = 0
        for w in range(width):                          # parallel INDEPENDENT lineages (Q4)
            qc, logical_depth, num_teleport_bonds = build_lineage_routed(
                theta_seq, n_slots, args.pheno_coupling, args.bond_dist, routing,
                args.anchors, feedforward=feedforward)
            out = sample_quantum_arm(qc, args.shots, args, backend, qubit_list,
                                     want_tel=want_tel)
            if want_tel:
                f, tel = out
                kept = [ff for ff, t in zip(f, tel) if set(t) <= {"0"}]  # post-select tel==00
                n_total += len(f)
                kept_total += len(kept)
                fields += (kept if kept else f)         # never zero-out the record
            else:
                fields += out
        if want_tel:
            herald_frac = round(kept_total / n_total, 4) if n_total else 0.0
            if kept_total < 200:
                print(f"  seed {seed} [{arm:>16}]  HERALD kept only {kept_total}/{n_total} "
                      f"shots -- too few; use fewer --anchors or more --shots.")
        M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(
            len(fields), n_slots)
        p = ((M - ord("0")).astype(np.float64)).mean(axis=0)   # P(bit=1) per generation
        gens = [{"gen": g, "trait_sigmaz": round(1.0 - 2.0 * float(p[g]), 6),
                 "shots": args.shots * width} for g in range(n_slots)]
        corr = temporal_correlation(fields, gmax)
        print(f"  seed {seed} [{arm:>16}]  depth {logical_depth:>4}  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")
    elif arm == "classical":
        fields = []
        for w in range(width):
            fields += run_classical_surrogate(
                theta_seq, n_slots, args.shots, seed + _WIDTH_SEED_STEP * w)
        M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(
            len(fields), n_slots)
        p = ((M - ord("0")).astype(np.float64)).mean(axis=0)
        gens = [{"gen": g, "trait_sigmaz": round(1.0 - 2.0 * float(p[g]), 6),
                 "shots": args.shots * width} for g in range(n_slots)]
        corr = temporal_correlation(fields, gmax)
        print(f"  seed {seed} [{arm:>16}]  C0 {corr['C0']:.4f}  "
              f"c(1..{gmax}): {', '.join(f'{v:+.2f}' for v in corr['c'][1:])}")
    else:
        raise ValueError(f"unknown arm {arm!r}")

    is_quantum = arm in ("quantum_swap", "quantum_teleport")
    run = {
        "meta": {
            "project": "artificial-life",
            "study": "coherence-depth-genealogy",
            "arm": arm,                               # quantum_swap|quantum_teleport|classical|ideal
            "routing": routing,                       # swap|teleport (None on classical/ideal)
            "backend": run_backend,
            "sim": run_sim,
            "timestamp": timestamp(),
            "seed": seed,
            "generations": G,                         # this run's G (varies across the sweep)
            "shots": args.shots,
            "width": width,
            "pheno_coupling": args.pheno_coupling,
            "mut_scale": args.mut_scale,
            "corr_gmax": gmax,
            # --- S3 routing meta (§4) ---
            "bond_dist": args.bond_dist,
            "anchors": args.anchors,
            "logical_depth": logical_depth,           # qc.depth() (M6; None on classical/ideal)
            "ancillas": (2 * num_teleport_bonds) if is_quantum else None,  # AC-S3.3
            "herald": bool(args.herald) if is_quantum else False,
            "herald_frac": herald_frac,
            "routing_cost": ROUTING_COST if routing == "teleport" else None,  # AC-S3.3 honesty
            "noise_model": args.noise_model,
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
# g* (CD-5) -- copied verbatim from stage2_scale.py.
# ---------------------------------------------------------------------------
def compute_gstar(per_gen_Cq: list[float], per_gen_Ccl: list[float],
                  sigma: list[float], k: int) -> int:
    """g* = max g s.t. |C_q(g) - C_cl(g)| > k*sigma(g); else 1 (falsification, §5)."""
    gstar = 1
    for g in range(1, min(len(per_gen_Cq), len(per_gen_Ccl), len(sigma))):
        s = sigma[g]
        if s > 1e-12 and abs(per_gen_Cq[g] - per_gen_Ccl[g]) > k * s:
            gstar = g
    return gstar


# ---------------------------------------------------------------------------
# Per-G aggregation (M3/M5) -- S3 splits the quantum arm into the two routings,
# computes g* per routing vs the SHARED classical surrogate, and Δg* (M5).
# ---------------------------------------------------------------------------
def _aggregate_per_generation(corr_by_arm: dict[str, list[list[float]]], n_slots: int,
                              stat_arms: list[str]) -> tuple[list[dict], dict, dict]:
    """Aggregate raw C(g) over repeats into per-gen mean/std, per-routing g*, and Δg*.

    ``mat`` is shape ``(repeats x n_slots)`` per arm; ``mean/std(ddof=0)`` over axis 0.
    Per routing R in {swap, teleport}: ``sigma[g] = sqrt(std_R^2 + std_classical^2)`` and
    ``g*_R = compute_gstar(C_R, C_classical, sigma, k)`` (same classical surrogate,
    routing-independent, CD-4). ``delta_gstar[k] = g*_teleport - g*_swap`` (M5), or None
    when either routing / the classical arm is absent.
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

    gstar: dict[str, dict] = {}
    for routing, akey in (("swap", "quantum_swap"), ("teleport", "quantum_teleport")):
        if akey in means and "classical" in means:
            sigma = [math.sqrt(float(stds[akey][g]) ** 2 + float(stds["classical"][g]) ** 2)
                     for g in range(n_slots)]
            Cq = means[akey].tolist()
            Ccl = means["classical"].tolist()
            gstar[routing] = {"k2": compute_gstar(Cq, Ccl, sigma, 2),
                              "k3": compute_gstar(Cq, Ccl, sigma, 3)}
        else:
            gstar[routing] = {"k2": None, "k3": None}

    delta_gstar: dict[str, int | None] = {}
    for kk in ("k2", "k3"):
        t, s = gstar["teleport"][kk], gstar["swap"][kk]
        delta_gstar[kk] = (t - s) if (t is not None and s is not None) else None
    return per_generation, gstar, delta_gstar


# ---------------------------------------------------------------------------
# main -- ported stage2_scale.main; S3 adds the routing flags, the two routed
# quantum arms, and the Δg* / logical_depth aggregation.
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
    ap = argparse.ArgumentParser(description="QDEP Stage 3 -- break the SWAP ceiling: "
                                             "teleport-vs-SWAP routing of the inheritance "
                                             "bond, Δg* (M5) and logical_depth (M6).")
    ap.add_argument("--gmin", type=int, default=2, help="smallest G in the sweep (>=2)")
    ap.add_argument("--gmax", type=int, default=4,
                    help="largest G in the sweep (routed spine is heavy; sim stays small, §7)")
    ap.add_argument("--width", type=int, default=1,
                    help="parallel INDEPENDENT lineages pooled for tighter sigma (Q4; off=1)")
    ap.add_argument("--pheno-coupling", dest="pheno_coupling", type=float, default=0.5,
                    help="genotype->phenotype readout strength in (0,1] (Q1; 1.0 = S1 parity)")
    ap.add_argument("--sv-max-qubits", dest="sv_max_qubits", type=int, default=26,
                    help="statevector qubit ceiling; abort if the routed/ideal circuit exceeds it")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=100, help="base; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=8, help="sigma for g* (CD-5)")
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--corr-gmax", dest="corr_gmax", type=int, default=None,
                    help="max g for C(g) per G (default = that G)")
    ap.add_argument("--k", type=int, default=2, help="sigma multiplier (k=3 also reported)")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.1,
                    help="max mutation angle per generation, radians")
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=None,
                    help="Q-EaaS base URL (Q5); default env QEAAS_API_URL else "
                         f"{QEAAS_URL_DEFAULT}")
    # --- S3 routing flags (§6) ---
    ap.add_argument("--routing", choices=["swap", "teleport", "both"], default="both",
                    help="how the clone CX is routed; both runs the matched pair for Δg*")
    ap.add_argument("--bond-dist", dest="bond_dist", type=int, default=3,
                    help="physical routing span of each routed inheritance bond (1 = S2 baseline)")
    ap.add_argument("--anchors", type=str, default="all",
                    help="which generation bonds are routed long-range (all or a comma list)")
    ap.add_argument("--herald", action="store_true", default=False,
                    help="teleport-only heralded post-selection (tel==00); small-scale filter (§9)")
    ap.add_argument("--noise-model", dest="noise_model", type=str, default=None,
                    help="noisy Aer backend (e.g. fake_heron) so --sim shows a Δg* signal (Q7)")
    ap.add_argument("--name", type=str, default="qdep_s3")
    args = ap.parse_args()

    if args.gmin < 2:
        print(f"[S3 ABORT] --gmin {args.gmin} < 2: the g>=1 correlation domain is trivial "
              "below G=2 (C(0) is the anchor). Use --gmin >= 2.")
        raise SystemExit(1)
    if args.gmax < args.gmin:
        print(f"[S3 ABORT] --gmax {args.gmax} < --gmin {args.gmin}.")
        raise SystemExit(1)
    if not (0.0 < args.pheno_coupling <= 1.0):
        print(f"[S3 ABORT] --pheno-coupling {args.pheno_coupling} not in (0, 1] (Q1).")
        raise SystemExit(1)
    if args.bond_dist < 1:
        print(f"[S3 ABORT] --bond-dist {args.bond_dist} < 1.")
        raise SystemExit(1)
    wants_teleport = args.routing in ("teleport", "both")
    if wants_teleport and 1 < args.bond_dist < 3:
        print(f"[S3 ABORT] teleport routing needs a 2-qubit corridor -> --bond-dist >= 3 "
              f"(got {args.bond_dist}). Use --bond-dist 1 for the S2 direct baseline, or >= 3 "
              f"for a genuine long-range teleport bond.")
        raise SystemExit(1)
    if args.herald and not wants_teleport:
        print("[S3 ABORT] --herald applies only to the teleport arm "
              "(use --routing teleport or both).")
        raise SystemExit(1)

    n_slots_max = args.gmax + 1                  # largest lineage in the sweep

    # qubit budget (§7): the routed spine is much heavier than S2's 2*(G+1). The ideal
    # confound curve (M4) always runs on the statevector sim (2*n_slots_max qubits); the
    # routed quantum arms need the statevector too ONLY under noiseless --sim (a noisy
    # --noise-model runs on the device coupling map, not the statevector).
    n_q_routed = (n_slots_max - 1) * args.bond_dist + 1 + n_slots_max
    n_q_ideal = 2 * n_slots_max
    need_sv = n_q_ideal
    if args.sim and not args.noise_model:
        need_sv = max(need_sv, n_q_routed)
    if need_sv > args.sv_max_qubits:
        print(f"[S3 ABORT] --gmax {args.gmax} / --bond-dist {args.bond_dist} needs {need_sv} "
              f"statevector qubits > --sv-max-qubits {args.sv_max_qubits} (routed spine "
              f"{n_q_routed}, mandatory ideal confound {n_q_ideal}, §7/§9). Reduce --gmax or "
              f"--bond-dist, use --noise-model (device-bounded), or raise --sv-max-qubits.")
        raise SystemExit(1)

    if args.routing == "both":
        q_arms = ["quantum_swap", "quantum_teleport"]
    else:
        q_arms = [f"quantum_{args.routing}"]
    arms = q_arms + ["classical", "ideal"]

    # --- certified Q-EaaS client (CD-7, fail-closed) -------------------------
    api_key = _read_env_key("QEAAS_API_KEY")
    if not api_key:
        print("[S3 ABORT] QEAAS_API_KEY not set (env or artificial-life/.env) -- "
              "S3 is fail-closed on entropy provenance (CD-7). No PRNG fallback.")
        raise SystemExit(1)
    qrng_url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
    client = QRNGClient(qrng_url, api_key)
    print(f"Q-EaaS  : {qrng_url}  (fail-closed, no PRNG fallback)")

    # --- backend / qubit layout (sized for the largest routed G) -------------
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
        try:
            qubit_list, qstats = best_chain(backend, n_q_routed)
        except RuntimeError as exc:               # no SWAP-free chain for the strided spine (§9)
            print(f"[S3 ABORT] no length-{n_q_routed} SWAP-free chain on {backend_name}: {exc} "
                  f"Reduce --bond-dist or --gmax.")
            raise SystemExit(1)
        print(f"Auto qubit chain (live calib): {qstats}")
        print("Note: teleport adds ancillas beyond the chain; the transpiler routes them "
              "(initial_layout left unpinned when it exceeds the chain, §6).")
    else:
        if args.noise_model:
            print(f"Backend : noisy Aer from {args.noise_model} (--sim + --noise-model, Q7)")
        else:
            print("Backend : statevector sim (--sim, CD-9; Δg*=0 by construction, §7)")
        qubit_list = list(range(n_q_routed))

    # herald statistics (mirror teleport main @627): kept ~ 0.25**num_bonds
    if args.herald:
        nb = len(resolve_bonds(args.anchors, n_slots_max)) if args.bond_dist >= 3 else 0
        exp_frac = 0.25 ** nb
        print(f"Herald   : ON (no feed-forward, post-select tel==00). num_bonds@G={args.gmax} "
              f"= {nb}. Expected kept ~{exp_frac * 100:.2f}% -> "
              f"~{int(args.shots * exp_frac)} of {args.shots} shots/gen.")
        if exp_frac * args.shots < 200:
            print("           WARNING: <200 shots survive/gen -> noisy C(g). "
                  "Reduce --anchors or raise --shots.")

    print(f"Sweep   : G in [{args.gmin}..{args.gmax}]  arms={arms}  routing={args.routing}  "
          f"bond_dist={args.bond_dist}  anchors={args.anchors}  "
          f"pheno_coupling={args.pheno_coupling}  width={args.width}  repeats={args.repeats}")

    # --- fetch the full gmax schedule ONCE per repeat; slice per G (CD-4, §7) --
    schedules: list[tuple[list[float], list[dict]]] = []
    for r in range(args.repeats):
        try:
            theta_full, prov_full = _mutation_schedule(client, n_slots_max, args.mut_scale)
        except QRNGUnavailable as exc:      # fail-closed (CD-7)
            print(f"[S3 ABORT] Q-EaaS unavailable: {exc} -- no PRNG fallback (CD-7).")
            raise SystemExit(1)
        schedules.append((theta_full, prov_full))

    # --- sweep loop: g*(G) per routing + Δg*, error bars over --repeats -------
    run_files: list[str] = []
    sweep: list[dict] = []
    for G in range(args.gmin, args.gmax + 1):
        n_slots = G + 1
        print(f"\n=== G = {G}  ({n_slots} generation slots) ===")
        corr_by_arm: dict[str, list[list[float]]] = {a: [] for a in arms}
        depth_by_arm: dict[str, list[int]] = {a: [] for a in q_arms}
        for r in range(args.repeats):
            seed = args.seed + r
            theta_full, prov_full = schedules[r]
            print(f"  -- repeat {r + 1}/{args.repeats}  (seed {seed}) --")
            for arm in arms:
                run, path = run_once(args, seed, arm, G, theta_full, prov_full,
                                     backend, backend_name, calib, qubit_list)
                run_files.append(os.path.basename(path))
                corr_by_arm[arm].append(run["correlation_temporal"]["C"])
                if arm in depth_by_arm and run["meta"]["logical_depth"] is not None:
                    depth_by_arm[arm].append(run["meta"]["logical_depth"])

        stat_arms = [a for a in ("quantum_swap", "quantum_teleport", "classical", "ideal")
                     if a in corr_by_arm and corr_by_arm[a] and corr_by_arm[a][0]]
        per_generation, gstar, delta_gstar = _aggregate_per_generation(
            corr_by_arm, n_slots, stat_arms)
        logical_depth = {
            "swap": (round(float(np.mean(depth_by_arm["quantum_swap"])))
                     if depth_by_arm.get("quantum_swap") else None),
            "teleport": (round(float(np.mean(depth_by_arm["quantum_teleport"])))
                         if depth_by_arm.get("quantum_teleport") else None),
        }
        sweep.append({"G": G, "per_generation": per_generation, "gstar": gstar,
                      "delta_gstar": delta_gstar, "logical_depth": logical_depth})
        print(f"  logical_depth(G={G}) : swap={logical_depth['swap']}  "
              f"teleport={logical_depth['teleport']}")
        if delta_gstar["k2"] is not None:
            print(f"  g*(G={G}) : swap k2={gstar['swap']['k2']} k3={gstar['swap']['k3']}  "
                  f"teleport k2={gstar['teleport']['k2']} k3={gstar['teleport']['k3']}  "
                  f"Δg* k2={delta_gstar['k2']} k3={delta_gstar['k3']}")
        else:
            print(f"  g*(G={G}) : Δg* needs both routings + the classical arm "
                  "(--routing both).")

    # --- summary.json: sweep[] + top-level = largest-G entry (§4 back-compat) --
    top = sweep[-1] if sweep else {
        "per_generation": [], "gstar": {"swap": {"k2": None, "k3": None},
                                        "teleport": {"k2": None, "k3": None}},
        "delta_gstar": {"k2": None, "k3": None}}
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
                # --- S3 routing meta (§4) ---
                "bond_dist": args.bond_dist,
                "anchors": args.anchors,
                "routing": args.routing,
                "herald": bool(args.herald),
                "noise_model": args.noise_model,
                "routing_cost": ROUTING_COST,
                "run_files": run_files,
            },
            "sweep": sweep,
            "per_generation": top["per_generation"],
            "gstar": top["gstar"],
            "delta_gstar": top["delta_gstar"],
        }, f, indent=2, default=str)

    # --- report --------------------------------------------------------------
    print("\n--- DONE (sweep) ---")
    print("    G   depth(swap)  depth(tel)   Δg*(k2)  Δg*(k3)")
    for entry in sweep:
        ld = entry["logical_depth"]
        dg = entry["delta_gstar"]
        ds = ld["swap"] if ld["swap"] is not None else "-"
        dt = ld["teleport"] if ld["teleport"] is not None else "-"
        d2 = dg["k2"] if dg["k2"] is not None else "-"
        d3 = dg["k3"] if dg["k3"] is not None else "-"
        print(f"  {entry['G']:>3}   {str(ds):>10}   {str(dt):>9}   "
              f"{str(d2):>6}   {str(d3):>6}")
    if top["delta_gstar"]["k2"] is not None:
        print(f"\nHeadline Δg* @ G={args.gmax} (k=2) = {top['delta_gstar']['k2']}    "
              f"(k=3) = {top['delta_gstar']['k3']}   [teleport - swap, M5]")
        if not args.sim or args.noise_model:
            pass
        else:
            print("NOTE: noiseless --sim -> Δg* = 0 BY CONSTRUCTION (swap and teleport are the "
                  "same logical map; only decoherence separates them). Source the Δg* signal "
                  "from --noise-model or Heron-r2 hardware (§7).")
    else:
        print("\nHeadline Δg*: needs both routings + the classical arm (--routing both).")
    print(f"Routing cost (AC-S3.3): {ROUTING_COST}")
    print(f"Summary file : {sum_path}")


if __name__ == "__main__":
    main()
