#!/usr/bin/env python3
"""Stage 5 / Phase 0 -- the stone-wall teleport-flip KILL-GATE.

The cheapest experiment that can kill the stone-wall-virus epic (epic §7 step 1). It strips
the virus to its bare cross-block transmission bond and asks one falsifiable question:

  Across a WIDE stone wall separating two small HEALTHY genealogy blocks, does a
  constant-depth TELEPORT-routed infection bond keep the cross-block entanglement witness
  alive where an O(distance) SWAP-routed bond has decohered it?

Setup (epic §1 thesis): two W12 blocks (per-block witness ~0.30, ample headroom -- unlike the
M4 W24 line at ~0.03 with none), one generation, one A->B infection CX, measured cross-block
transmission witness under swap-routing vs teleport-routing, over a block-separation d-sweep.
STRICT flip required: teleport clears the 2sigma null while swap is buried (Q1). PASS -> proceed
to P1; STOP -> the epic's quantum headline (D) is refuted and must be re-scoped before build.

CROSS-BLOCK WITNESS (revised Q-P0.1 -- the original bonded two-point <X_{A_tail} X_{B_head}> is
IDENTICALLY ZERO for a GHZ genealogy and cannot show the flip; a GHZ has no low-weight
off-diagonal signal). The genuine, classical-surrogate-free transmission witness is
    signal = <X^{2W}> - <X^{W}>_A * <X^{W}>_B
  = 1 for one connected genealogy across the wall, = 0 for two separate healthy blocks, -> 0 for
a measure-and-resend (classical) infector. It IS a 2W-body parity (the fragile many-body regime),
which is exactly the epic's headroom test: 2xW12 per-block ~0.30 vs the dead single W24 line.

HONESTY (central, carried from S3): _swap_cx and _teleport_cx implement the SAME logical CX.
On a noiseless statevector they give identical states => identical signal => Delta(signal) = 0
BY CONSTRUCTION (AC-P0.4). The difference is DEPTH, and depth only converts to a witness gap
under DECOHERENCE -- i.e. on hardware. The noiseless --sim run validates the pipeline + the
logical_depth split ONLY; the flip signal lives on hardware. Do NOT report sim Delta=0 as a null.

Provenance (CD-1: copied, not imported):
  * _swap_cx / _teleport_cx           ported from stage3_teleport.py
  * xbasis_witness_from_counts, _x_string_op, apply_self_replication, _sim_thetas
                                      ported from stage4_qalife.py
  * qrng_thetas, gated_chain, run_counts, the run/JSON/CLI skeleton
                                      ported from stage4_scale.py

Usage:
    cd artificial-life/code
    # A) noiseless sim: pipeline + logical_depth split + AC-P0.4 (Delta=0 by construction)
    python stage5_fliptest.py --sim --width 3 --separations 2,4 --routing both \\
        --shots 8192 --repeats 3 --name p0_sim
    # B) hardware flip-test: the real d-sweep (the kill-gate)
    python stage5_fliptest.py --no-sim --backend '' --width 12 --separations 2,48 \\
        --routing both --shots 8192 --repeats 3 --name p0_hw
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
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
# P0 is unitary-only (no damping bath) -> statevector, NOT density_matrix.
SIM = AerSimulator(method="statevector")
QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"

# --- reuse the submission pipeline + QRNG client (same probe as stage4) --------
for _cand in ("code", os.path.join("old", "code"), os.path.join("new", "code")):
    _p = os.path.normpath(os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", _cand))
    if os.path.exists(os.path.join(_p, "pipeline_common.py")):
        sys.path.insert(0, _p)
        break
try:
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402
except Exception:
    _stub = types.ModuleType("pipeline_common")
    for _a in ("connect", "run_sampler"):
        setattr(_stub, _a, lambda *x, **k: None)
    _stub.timestamp = lambda: "sim"
    sys.modules["pipeline_common"] = _stub
    from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

from qrng_client import QRNGClient, QRNGUnavailable  # noqa: E402


# ---------------------------------------------------------------------------
# Routing primitives -- ported verbatim from stage3_teleport.py (CD-1)
# ---------------------------------------------------------------------------
def _swap_cx(qc: QuantumCircuit, lo: int, hi: int) -> None:
    """Long-range CNOT(lo -> hi), lo < hi, via a SWAP ladder (O(distance) depth).
    ported verbatim from stage3_teleport.py:315.
    Carry lo's state up to hi-1, CX onto hi, then reverse every SWAP so the register
    permutation is the identity and only the long-range CX remains. Cost ~ 2*(hi-lo) SWAPs.
    The precious genealogical state at `lo` is physically dragged across the wall -> the
    decoherence the teleport arm avoids."""
    for p in range(lo, hi - 1):
        qc.swap(p, p + 1)
    qc.cx(hi - 1, hi)
    for p in range(hi - 1, lo, -1):
        qc.swap(p - 1, p)


def _teleport_cx(qc: QuantumCircuit, ctrl: int, tgt: int, a1: int, a2: int,
                 tel: Any, k: int, feedforward: bool = True) -> None:
    """Long-range CNOT(ctrl -> tgt) via one Bell pair + two mid-circuit measures + feed-fwd.
    ported verbatim from stage3_teleport.py:330.
    Ancillas a1 (staged near ctrl) / a2 (staged near tgt); tel[2k], tel[2k+1] hold the
    outcomes. Logically applies CX(ctrl, tgt) at CONSTANT depth; ctrl/tgt are never moved.
    feedforward=True  : X/Z corrections -> valid CX for all four outcomes (dynamic circuit).
    feedforward=False : HERALDED -- only the tel==00 branch is the correct CX; the caller
                        post-selects it (--herald noise filter)."""
    qc.h(a1)
    qc.cx(a1, a2)                       # Bell pair spans the wall
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


# ---------------------------------------------------------------------------
# Witness helpers -- ported verbatim from stage4_qalife.py (CD-1)
# ---------------------------------------------------------------------------
def apply_self_replication(qc: QuantumCircuit, parent_geno: int, child_geno: int) -> None:
    """Partial sigma_z clone: CNOT(parent -> child), child blank |0>. Exact <sigma_z> copy
    (eta=1, the paper's bare-CNOT clone). ported verbatim from stage4_qalife.py:69."""
    qc.cx(parent_geno, child_geno)


def _x_string_op(nq: int, qubits: list[int]) -> SparsePauliOp:
    """ported verbatim from stage4_qalife.py:361."""
    label = ["I"] * nq
    for q in qubits:
        label[nq - 1 - q] = "X"            # SparsePauliOp label is qubit n-1 .. 0
    return SparsePauliOp("".join(label))


def xbasis_witness_from_counts(counts: dict[str, int], qubits: list[int]) -> tuple[float, float]:
    """From X-basis counts (H applied before Z-readout): return (joint, separable) where
    joint = <prod_i x_i> (the entanglement witness) and separable = prod_i <x_i> (the
    factorized null a classical device gives). joint - separable is the entanglement signal.
    ported verbatim from stage4_qalife.py:385.
    NB: `qubits` are indices into the measured CLASSICAL register 'c' (bit position q reads
    bits[-(q+1)]), which here is NOT the physical qubit index (the wall is not measured)."""
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


def x_parity(counts: dict[str, int], qubits: list[int]) -> float:
    """<prod_i X_i> (the joint X-parity) over classical-register indices `qubits`, from
    X-basis counts. Convenience wrapper over xbasis_witness_from_counts (joint element)."""
    return xbasis_witness_from_counts(counts, qubits)[0]


def _sim_thetas(width: int, seed: int, mut_scale: float = 1.0) -> list[float]:
    """PRNG mutation angles for --sim ONLY (hardware draws certified Q-EaaS, CD-7 fail-closed).
    ported verbatim from stage4_qalife.py:522."""
    rng = random.Random(seed)
    return [mut_scale * rng.uniform(0, math.pi) for _ in range(width)]


# ---------------------------------------------------------------------------
# Mutation angles from the certified Q-EaaS stream (CD-7 fail-closed on hardware)
# ---------------------------------------------------------------------------
def qrng_thetas(client: QRNGClient, width: int, mut_scale: float, repeat: int,
                provenance: list[dict[str, Any]] | None = None) -> list[float]:
    """`width` mutation angles in [0, mut_scale*pi) from certified quantum entropy (CD-7).
    ported from stage4_scale.py:75; extended to append each fetch's {request_id, receipt}
    to `provenance` (CD-7 parity -- P0's one-generation genealogy uses the fixed founder/
    clone prefix, so these angles are carried for provenance/parity with M4, not applied).
    Fail-closed: QRNGUnavailable propagates."""
    need = 4 * width
    flat = bytearray()
    while len(flat) < need:
        resp = client.fetch(size=32, fmt="hex")        # raises QRNGUnavailable -> abort
        flat.extend(bytes.fromhex(resp.data))
        if provenance is not None:
            provenance.append({"request_id": resp.request_id, "receipt": resp.receipt})
    out = []
    for k in range(width):
        u = int.from_bytes(bytes(flat[4 * k:4 * k + 4]), "big")
        out.append(mut_scale * math.pi * (u / 2 ** 32))
    return out


# ---------------------------------------------------------------------------
# chain-quality gate (Month-3 fix, CD-6 fail-closed; ported from stage4_scale.py:157,
# extended to also RETURN the live-calibration stats for the JSON chain_stats)
# ---------------------------------------------------------------------------
def gated_chain(backend: Any, nq: int, args: argparse.Namespace) -> tuple[list[int], dict[str, Any]]:
    from layout import best_chain
    try:
        qubit_list, qstats = best_chain(backend, nq)
    except RuntimeError as exc:
        print(f"[P0 ABORT] no clean chain of {nq} qubits: {exc}. Try a smaller far --separations.")
        raise SystemExit(1)
    print(f"Auto qubit chain (live calib): {qstats}")
    if not args.allow_bad_chain:
        bad = []
        tq, ro = qstats.get("twoq_err_max"), qstats.get("readout_max")
        if tq is not None and tq > args.max_twoq_err:
            bad.append(f"twoq_err_max {tq:.4f} > {args.max_twoq_err}")
        if ro is not None and ro > args.max_readout_err:
            bad.append(f"readout_max {ro:.4f} > {args.max_readout_err}")
        if bad:
            print(f"[P0 ABORT] chain-quality gate failed: {'; '.join(bad)}. "
                  f"Pin a cleaner --backend or bypass with --allow-bad-chain.")
            raise SystemExit(1)
    return qubit_list, qstats


# ---------------------------------------------------------------------------
# P0 core: the two-block flip circuit
# ---------------------------------------------------------------------------
def build_flip_circuit(width: int, d: int, routing: str, feedforward: bool,
                       thetas: list[float]) -> tuple[QuantumCircuit, int]:
    """Two W-blocks split by a d-wide stone wall, one A->B infection bond routed by `routing`.

    Physical line (single QuantumRegister of length 2*width + d):
      block A  = q[0 : width]                 (A_tail = q[width-1])
      wall     = q[width : width+d]           (d idle spacers = the "unused couplers")
      block B  = q[width+d : 2*width+d]       (B_head = q[width+d])

    Genealogy (one generation): founder ry(pi/2) on A[0], then a clone (CNOT) chain within
    each block -> per-block GHZ (per-block witness ~0.30 on hw = the headroom the thesis needs).
    `thetas` are carried for CD-7 provenance parity with M4 but NOT applied here: P0's one
    generation uses the fixed founder + clone prefix (the M4 W-witness prefix), no mutation.

    Infection bond A_tail -> B_head:
      swap     -> _swap_cx  (O(distance) ladder; drags A_tail's state across the wall)
      teleport -> _teleport_cx over a 2-ancilla corridor flanking the wall (a1 next to A_tail,
                  a2 next to B_head; S3 placement, stage3_teleport.py:466). Needs d >= 2.
    The bond seeds B's founder COHERENTLY from A -> one connected GHZ across the wall. A
    measure-and-resend infector would collapse it (signal -> 0): the honesty invariant (CD-4).

    Only the 2*width data loci (A u B) are measured (X basis: H then Z-read); wall/corridor
    qubits are not. Returns (qc, qc.depth()); depth is the D-crossover evidence (teleport ~flat,
    swap ~ d)."""
    n_q = 2 * width + d
    qr = QuantumRegister(n_q, "q")
    creg = ClassicalRegister(2 * width, "c")
    a_tail = width - 1
    b_head = width + d

    if routing == "teleport":
        tel = ClassicalRegister(2, "tel")
        # tel added BEFORE c so 'c' is the most-significant (leftmost) register in the
        # counts key "<c> <tel>" -- matches stage4_scale.run_counts key split exactly.
        qc = QuantumCircuit(qr, tel, creg)
    else:
        tel = None
        qc = QuantumCircuit(qr, creg)

    # --- block A genealogy: founder on the equator, then the clone chain -> GHZ over A ----
    qc.ry(math.pi / 2, 0)
    for i in range(1, width):
        apply_self_replication(qc, i - 1, i)

    # --- infection bond A_tail -> B_head, routed per arm --------------------------------
    if routing == "swap":
        _swap_cx(qc, lo=a_tail, hi=b_head)
    elif routing == "teleport":
        if d < 2:
            raise ValueError(f"teleport corridor needs a >=2-wide wall (d>=2); got d={d}")
        a1 = width            # first wall qubit, adjacent to A_tail (= a_tail + 1)
        a2 = b_head - 1       # last wall qubit, adjacent to B_head
        _teleport_cx(qc, ctrl=a_tail, tgt=b_head, a1=a1, a2=a2, tel=tel, k=0,
                     feedforward=feedforward)
        qc.reset([a1, a2])
    else:
        raise ValueError(f"unknown routing {routing!r}")

    # --- block B genealogy seeded from the coherently-transmitted B_head -> GHZ over B ----
    for j in range(1, width):
        apply_self_replication(qc, b_head + j - 1, b_head + j)

    # --- X-basis witness readout on the 2*width data loci (A then B) into 'c' -----------
    data_qubits = list(range(0, width)) + list(range(b_head, b_head + width))
    for m, q in enumerate(data_qubits):
        qc.h(q)
        qc.measure(q, creg[m])
    return qc, qc.depth()


def build_block_circuit(width: int) -> QuantumCircuit:
    """A single STANDALONE W-block genealogy (founder + clone chain), X-basis readout. Its
    <X^{W}> is the per-block headroom sanity (AC-P0.1): 1.0 on noiseless sim, ~0.30 on hw at
    W12. Distinct from the per-block parity INSIDE the connected flip circuit (which is ~0,
    since a connected block is only half of a larger GHZ)."""
    qr = QuantumRegister(width, "q")
    creg = ClassicalRegister(width, "c")
    qc = QuantumCircuit(qr, creg)
    qc.ry(math.pi / 2, 0)
    for i in range(1, width):
        apply_self_replication(qc, i - 1, i)
    for q in range(width):
        qc.h(q)
        qc.measure(q, creg[q])
    return qc


def run_block_witness(width: int, phys: list[int], args: argparse.Namespace,
                      backend: Any) -> float:
    """Standalone per-block <X^{W}> headroom sanity on the block's real physical qubits
    (AC-P0.1). Averaged over repeats; not heralded (no teleport here)."""
    vals = []
    for _ in range(args.repeats):
        qc = build_block_circuit(width)
        counts, _ = run_counts(qc, args.shots, args, backend, phys, herald=False)
        vals.append(x_parity(counts, list(range(width))))
    return float(np.mean(vals))


def witness_ideal_crossblock(width: int, d: int, span: str) -> float:
    """Noiseless ideal cross-block witness on the routing-INDEPENDENT logical map (no wall, no
    routing ancillas, no measurement), for AC-P0.4. The founder + clone chains + the direct
    infection CX make ONE connected GHZ across A u B. `d` is irrelevant to the ideal logical
    state (the wall is physical only).

    span="full" (headline, revised Q-P0.1): the CONNECTED-GHZ witness
        signal = <X^{2W}> - <X^{W}>_A * <X^{W}>_B  =  1.0 (connected) / 0.0 (two separate blocks).
        A GHZ has NO low-weight off-diagonal signal (any X-string lighter than the full 2W set
        maps GHZ out of its support -> 0), so this full-parity-minus-per-block-product IS the
        genuine cross-block transmission witness. Reads 1.0 here.
    span="bond" (degenerate diagnostic, retained): the two-point <X_{A_tail} X_{B_head}>, which
        is identically 0 for the GHZ (kept only for comparison; do NOT use as the headline)."""
    nq = 2 * width
    qc = QuantumCircuit(nq)
    qc.ry(math.pi / 2, 0)
    for i in range(1, width):
        qc.cx(i - 1, i)                       # block A clone chain
    qc.cx(width - 1, width)                    # infection bond A_tail -> B_head (direct)
    for j in range(1, width):
        qc.cx(width + j - 1, width + j)        # block B clone chain
    state = Statevector.from_instruction(qc)

    def ev(qs: list[int]) -> float:
        return float(np.real(state.expectation_value(_x_string_op(nq, qs))))

    if span == "full":
        A = list(range(0, width))
        B = list(range(width, nq))
        return ev(list(range(nq))) - ev(A) * ev(B)
    return ev([width - 1, width])              # "bond": degenerate two-point (== 0 for GHZ)


# ---------------------------------------------------------------------------
# Dispatch: sim (statevector Aer) or Heron-r2 -- ported from stage4_scale.py:182,
# extended with optional heralded post-selection on the 'tel' register (--herald)
# ---------------------------------------------------------------------------
def run_counts(qc: QuantumCircuit, shots: int, args: argparse.Namespace, backend: Any,
               qubit_list: list[int], herald: bool) -> tuple[dict[str, int], float | None]:
    """Return (counts over 'c', herald_frac). With a 'tel' register present the raw key is
    "<c> <tel>" (space separated; 'c' leftmost). herald=True keeps only the tel==00 subset
    (the clean teleport branch) then collapses onto 'c'; herald_frac = kept/total. Otherwise
    tel is summed out. herald_frac is None when there is no 'tel' register."""
    has_tel = any(reg.name == "tel" for reg in qc.cregs)
    if args.sim:
        raw = SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    else:
        init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                          initial_layout=init)
        isa = pm.run(qc)
        raw_meas, _jobs, _qs = run_sampler(backend, isa, shots)
        raw = {}
        for s in raw_meas:                     # run_sampler returns per-shot classical strings
            raw[s] = raw.get(s, 0) + 1

    total = sum(raw.values()) or 1
    counts: dict[str, int] = {}
    kept = 0
    for key, cnt in raw.items():
        parts = key.split()
        c = parts[0]                            # 'c' is the leftmost register
        tel = parts[1] if len(parts) > 1 else None
        if herald and has_tel:
            if tel is None or tel.replace(" ", "") != "00":
                continue                        # drop the noisy/incorrect teleport branches
            kept += cnt
        counts[c] = counts.get(c, 0) + cnt
    herald_frac = (kept / total) if (herald and has_tel) else None
    return counts, herald_frac


# ---------------------------------------------------------------------------
# One arm (swap or teleport) at one separation d, aggregated over repeats
# ---------------------------------------------------------------------------
def run_arm(width: int, d: int, routing: str, args: argparse.Namespace, backend: Any,
            qubit_list: list[int], thetas_for) -> dict[str, Any]:
    a_tail_c = width - 1                         # A_tail classical-register index
    b_head_c = width                             # B_head classical-register index (first B)
    block_a_idx = list(range(0, width))
    block_b_idx = list(range(width, 2 * width))
    full_idx = list(range(2 * width))

    def witness(counts: dict[str, int]) -> tuple[float, float, float, float]:
        """Return (joint, sep, per_block_A, per_block_B) for the chosen span.
        span="full" (headline, revised Q-P0.1): the CONNECTED-GHZ witness --
            joint = <X^{2W}>, sep = <X^{W}>_A * <X^{W}>_B  => signal 1 connected / 0 separate.
            A GHZ has no lighter off-diagonal witness, so this per-block-product-nulled full
            parity is the genuine cross-block transmission signal (CD-4, no classical surrogate).
        span="bond": degenerate two-point <X_{A_tail} X_{B_head}> (== 0 for GHZ; diagnostic)."""
        pA = x_parity(counts, block_a_idx)
        pB = x_parity(counts, block_b_idx)
        if args.witness_span == "full":
            joint = x_parity(counts, full_idx)
            sep = pA * pB
        else:                                    # "bond" (degenerate diagnostic)
            joint, sep = xbasis_witness_from_counts(counts, [a_tail_c, b_head_c])
        return joint, sep, pA, pB

    joints, seps, signals = [], [], []
    herald_fracs = []
    logical_depth = 0
    herald = args.herald and routing == "teleport"
    for r in range(args.repeats):
        thetas = thetas_for(width, r)
        qc, logical_depth = build_flip_circuit(width, d, routing, feedforward=True, thetas=thetas)
        counts, hfrac = run_counts(qc, args.shots, args, backend, qubit_list, herald)
        joint, sep, _pA, _pB = witness(counts)
        joints.append(joint)
        seps.append(sep)
        signals.append(joint - sep)
        if hfrac is not None:
            herald_fracs.append(hfrac)

    signal_mean = float(np.mean(signals))
    std = float(np.std(signals))
    sigma = math.sqrt(std ** 2 + 1.0 / args.shots)   # repeat spread + shot-noise floor
    out: dict[str, Any] = {
        "witness_joint_mean": float(np.mean(joints)),
        "separable_mean": float(np.mean(seps)),
        "signal_mean": signal_mean,
        "signal_sigma": sigma,
        "clears_2sigma": bool(signal_mean > args.k * sigma),
        "logical_depth": int(logical_depth),
        "ancillas": 2 if routing == "teleport" else 0,
    }
    if routing == "teleport":
        out["herald_frac"] = float(np.mean(herald_fracs)) if herald_fracs else None
    return out


# ---------------------------------------------------------------------------
# Verification of a saved P0 run (reproducibility gate for the pivot decision)
# ---------------------------------------------------------------------------
def verify_run(path: str) -> int:
    """Re-derive the kill-gate verdict from a saved run JSON and confirm it matches what was
    written -- the reproducibility gate the P1 swap-routed pivot rests on. Recomputes, per d,
    clears_2sigma (signal_mean > k*sigma) and strict_flip (teleport clears AND swap buried),
    then the verdict (PASS iff any far-d strict_flip), and checks each against the stored value.
    Prints the swap-vs-teleport pattern per d. Returns 0 if fully consistent, else 1."""
    with open(path) as f:
        run = json.load(f)
    meta = run.get("meta", {})
    k = float(meta.get("k", 2.0))
    seps = [rec["d"] for rec in run["dsweep"]]
    far = [d for d in seps if d != min(seps)] if seps else []
    print(f"=== VERIFY {os.path.basename(path)} ===")
    print(f"  backend={meta.get('backend')} sim={meta.get('sim')} width={meta.get('width')} "
          f"span={meta.get('witness_span')} k={k}")
    ok = True
    recomputed_flip: list[int] = []
    for rec in run["dsweep"]:
        d = rec["d"]
        line = [f"  d={d:3}"]
        clears: dict[str, bool] = {}
        for name, arm in rec["arms"].items():
            sig, sg = arm["signal_mean"], arm["signal_sigma"]
            c = sig > k * sg
            clears[name] = c
            if c != arm.get("clears_2sigma"):
                ok = False
                line.append(f"[{name} clears MISMATCH stored={arm.get('clears_2sigma')} recomputed={c}]")
            line.append(f"{name}={sig:+.3f}+-{sg:.3f} {'clears' if c else 'buried'}")
        strict = clears.get("teleport", False) and not clears.get("swap", True)
        if "swap" in clears and "teleport" in clears and strict != rec.get("strict_flip"):
            ok = False
            line.append(f"[strict_flip MISMATCH stored={rec.get('strict_flip')} recomputed={strict}]")
        if d in far and strict:
            recomputed_flip.append(d)
        print("  ".join(line))
    verdict = "PASS" if recomputed_flip else "STOP"
    stored_verdict = run.get("kill_gate", {}).get("verdict")
    if verdict != stored_verdict:
        ok = False
        print(f"  [VERDICT MISMATCH stored={stored_verdict} recomputed={verdict}]")
    print(f"  recomputed verdict: {verdict}  (stored: {stored_verdict})  flip_at={recomputed_flip or 'none'}")
    print(f"  VERIFICATION: {'CONSISTENT' if ok else 'INCONSISTENT'}")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Stage 5 / P0 -- stone-wall teleport-flip kill-gate")
    ap.add_argument("--verify", type=str, default=None,
                    help="path to a saved run JSON: re-derive + confirm the kill-gate verdict, then exit")
    ap.add_argument("--sim", action="store_true", help="noiseless statevector Aer instead of hardware")
    ap.add_argument("--no-sim", dest="sim", action="store_false")
    ap.set_defaults(sim=True)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--width", type=int, default=12, help="individuals per block (12 on hw)")
    ap.add_argument("--separations", type=str, default="2,48",
                    help="comma list of block separations d (Q4); first = adjacent control "
                         "(teleport needs a >=2-wide wall for its corridor)")
    ap.add_argument("--routing", choices=["swap", "teleport", "both"], default="both",
                    help="how the A->B infection CX is routed; both = matched flip pair")
    ap.add_argument("--witness-span", dest="witness_span", choices=["full", "bond"], default="full",
                    help="full = connected-GHZ witness <X^2W> - <X^W>_A*<X^W>_B (headline, revised "
                         "Q-P0.1); bond = degenerate two-point <X_A_tail X_B_head> (==0 for GHZ, diagnostic)")
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--repeats", type=int, default=3, help="repeats for sigma error bars")
    ap.add_argument("--k", type=float, default=2.0, help="witness must beat null by k*sigma")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=0.10)
    ap.add_argument("--max-twoq-err", dest="max_twoq_err", type=float, default=0.05)
    ap.add_argument("--max-readout-err", dest="max_readout_err", type=float, default=0.15)
    ap.add_argument("--allow-bad-chain", dest="allow_bad_chain", action="store_true", default=False)
    ap.add_argument("--sv-max-qubits", dest="sv_max_qubits", type=int, default=26,
                    help="noiseless-sim qubit cap; abort if 2*width+max(d) exceeds it")
    ap.add_argument("--herald", action="store_true", default=False,
                    help="teleport-only heralded post-select tel==00 (noise-filter cross-check)")
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=None)
    ap.add_argument("--name", type=str, default="stonewall_p0")
    args = ap.parse_args()

    if args.verify:
        raise SystemExit(verify_run(args.verify))

    separations = [int(x) for x in args.separations.split(",") if x.strip()]
    if not separations:
        print("[P0 ABORT] --separations is empty."); raise SystemExit(2)
    arms = ["swap", "teleport"] if args.routing == "both" else [args.routing]
    if "teleport" in arms and min(separations) < 2:
        print("[P0 ABORT] the teleport corridor needs a >=2-wide wall (d>=2); the smallest "
              "separation is <2. Use --separations 2,48 (d=2 is the teleport-predicted-lose "
              "control) or --routing swap.")
        raise SystemExit(2)

    # --- sv guard (noiseless sim only) -----------------------------------------
    if args.sim:
        need = 2 * args.width + max(separations)
        if need > args.sv_max_qubits:
            print(f"[P0 ABORT] noiseless sim needs {need} qubits (2*width+max(d)) > "
                  f"--sv-max-qubits {args.sv_max_qubits}. Reduce --width/--separations.")
            raise SystemExit(1)

    # --- certified entropy (fail-closed on hardware; sim may PRNG-fallback) -----
    provenance: list[dict[str, Any]] = []
    client = None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    qrng_url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
    if api_key:
        client = QRNGClient(qrng_url, api_key)
        try:
            h = client.health()
            print(f"Q-EaaS  : {qrng_url}  health: {h.status}")
            if h.status != "ok" and not args.sim:
                print("[P0 ABORT] Q-EaaS not ok (fail-closed on hardware)."); raise SystemExit(1)
        except QRNGUnavailable as exc:
            if not args.sim:
                print(f"[P0 ABORT] Q-EaaS unavailable (fail-closed on hardware): {exc}")
                raise SystemExit(1)
            client = None
    elif not args.sim:
        print("[P0 ABORT] QEAAS_API_KEY not set (fail-closed on hardware)."); raise SystemExit(1)

    def thetas_for(width: int, repeat: int) -> list[float]:
        if client is not None:
            return qrng_thetas(client, width, args.mut_scale, repeat, provenance)
        print("[P0] sim entropy fallback: _sim_thetas (PRNG, sim-only, labelled).")
        return _sim_thetas(width, 1000 * repeat + width, mut_scale=args.mut_scale)

    # --- backend ---------------------------------------------------------------
    backend = None
    backend_name = "statevector_sim"
    if not args.sim:
        backend = connect(args.backend)
        backend_name = backend.name
        print(f"Backend : {backend.name}  ({backend.num_qubits} qubits)")

    print(f"=== Stage 5 / P0 flip-test: width={args.width} separations={separations} "
          f"routing={args.routing} on {backend_name} ===")

    dsweep: list[dict[str, Any]] = []
    for d in separations:
        L = 2 * args.width + d
        if not args.sim:
            qubit_list, qstats = gated_chain(backend, L, args)
        else:
            qubit_list, qstats = list(range(L)), {}
        # whole-chain gate is conservative -> bounds each block (CD-6, Q-P0.2); record the
        # aggregate stats under both blocks (per-block raw recompute is optional, not required).
        block_stats = {"twoq_err_max": qstats.get("twoq_err_max"),
                       "readout_max": qstats.get("readout_max")}
        # standalone per-block <X^W> headroom sanity on each block's real physical qubits
        # (AC-P0.1): chain[0:W] = block A, chain[W+d:2W+d] = block B.
        chain_a = qubit_list[0:args.width]
        chain_b = qubit_list[args.width + d:2 * args.width + d]
        per_block_witness = {
            "block_a": run_block_witness(args.width, chain_a, args, backend),
            "block_b": run_block_witness(args.width, chain_b, args, backend),
        }
        print(f"  d={d:3} per-block <X^W> headroom: A={per_block_witness['block_a']:+.3f} "
              f"B={per_block_witness['block_b']:+.3f}")
        arm_results: dict[str, Any] = {}
        for routing in arms:
            res = run_arm(args.width, d, routing, args, backend, qubit_list, thetas_for)
            arm_results[routing] = res
            print(f"  d={d:3} {routing:9}: signal={res['signal_mean']:+.3f}"
                  f"+-{res['signal_sigma']:.3f}  depth={res['logical_depth']:4}  "
                  f"{'CLEARS 2sigma' if res['clears_2sigma'] else 'buried'}")

        strict_flip = False
        if "swap" in arm_results and "teleport" in arm_results:
            strict_flip = (arm_results["teleport"]["clears_2sigma"]
                           and not arm_results["swap"]["clears_2sigma"])
        dsweep.append({
            "d": d,
            "chain": qubit_list,
            "chain_stats": {"block_a": dict(block_stats), "block_b": dict(block_stats)},
            "per_block_witness": per_block_witness,
            "arms": arm_results,
            "strict_flip": bool(strict_flip),
            "control": bool(d == min(separations)),
        })

    # --- kill-gate verdict (AC-P0.3, Q1) ---------------------------------------
    far = [d for d in separations if d != min(separations)]
    flip_at = [rec["d"] for rec in dsweep if rec["d"] in far and rec["strict_flip"]]
    verdict = "PASS" if flip_at else "STOP"

    # --- AC-P0.4: noiseless cross-block GHZ witness (=1) ------------------------
    witness_ideal = None
    if args.sim:
        witness_ideal = witness_ideal_crossblock(args.width, separations[0], args.witness_span)
        print(f"  witness_ideal (noiseless cross-block GHZ, span={args.witness_span}): "
              f"{witness_ideal:.9f}  (AC-P0.4 expects 1.0)")

    result: dict[str, Any] = {
        "meta": {
            "stage": 5, "phase": "P0", "model": "stonewall_virus_fliptest",
            "backend": backend_name, "sim": args.sim,
            "width": args.width, "blocks": 2, "generations": 1,
            "separations": separations, "routing": args.routing,
            "witness_span": args.witness_span, "shots": args.shots, "repeats": args.repeats,
            "k": args.k, "herald": args.herald,
            "max_twoq_err": args.max_twoq_err, "max_readout_err": args.max_readout_err,
            "mut_scale": args.mut_scale, "qrng_url": qrng_url,
            "entropy_provenance": provenance,
        },
        "dsweep": dsweep,
        "witness_ideal": witness_ideal,
        "kill_gate": {
            "flip_at": flip_at,
            "verdict": verdict,
            "note": "PASS -> proceed to P1; STOP -> re-scope epic headline (D) before build "
                    "(epic §7). STRICT flip = teleport clears 2sigma AND swap buried (Q1).",
        },
    }

    print("\n" + "=" * 60)
    print(f"  KILL-GATE VERDICT: {verdict}   (strict flip at far d: {flip_at or 'none'})")
    if verdict == "STOP":
        print("  STOP is a real, honorable outcome (epic §7). Do NOT loosen the strict metric,")
        print("  fish with --repeats, or cherry-pick a d to manufacture a PASS.")
    if args.sim:
        print("  (sim: Delta(signal)=0 between arms is BY CONSTRUCTION -- swap/teleport are the")
        print("   same logical map. The flip signal lives on HARDWARE, not here.)")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tag = timestamp() if not args.sim else "sim"
    out = os.path.join(OUTPUT_DIR, f"{args.name}_fliptest_{backend_name}_{tag}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  -> {out}")


def _read_env_key(name: str) -> str | None:
    """ported verbatim from stage4_scale.py:355."""
    for envp in (os.path.join(_HERE, "..", ".env"), os.path.join(_HERE, ".env")):
        p = os.path.normpath(envp)
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    if line.strip().startswith(f"{name}="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None


if __name__ == "__main__":
    main()
