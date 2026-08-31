#!/usr/bin/env python3
"""Critical Quantum Life — F5: hardware batch runs (scaled, manual).

The thesis-scale hardware result. Scales genome width (W=8, Q3), runs generations in
HARDWARE BATCHES on a pinned Heron backend (Q1), persists inherited state between jobs (F4),
pokes between batches, and assembles the three thesis artefacts: the criticality figure (F2),
the poke-and-recover trace (across a persisted batch boundary), and the witness-vs-surrogate
panel (F3). It reports the closed-loop-minus-yoked adaptation gap at the scaled width.

F5 writes NO new science — it composes F0's loop, F4's persistence/poke, F2's metrics, F3's
certification, and the stage4_scale/layout/pipeline_common hardware plumbing.

MANUAL SUBMISSION BOUNDARY (epic §3/§6 — LAW).
------------------------------------------------
`emit` writes files (transpiled QPY circuits + a submit bundle) and STOPS. F5 NEVER auto-submits
to a real backend as a side effect. Only the user runs circuits on QC and drops the counts /
run-JSONs into research_runs/. The ONLY unattended run path is `sim` (the Aer sign-check).

The honest manual model (why the schedule is predetermined).
------------------------------------------------------------
Closed-loop adaptation needs each generation's OUTCOME to set the next generation's mut_scale.
Manual hardware cannot round-trip per generation. So for each batch the mut_scale *schedule* is
PREDETERMINED by the sim sign-check run (run_closed_loop on Aer), the QRNG angles are drawn on
that fixed schedule (entropy provenance recorded), and the WITNESS is measured on hardware on
that trajectory. Adaptation across the *batch boundary* is real (F4 persists the ingested
outcome state and updates mut_scale before the next batch) — that is where the interactive poke
lives. Within a batch the trajectory is sim-predicted; the witness is hardware-measured.

Q4 (resolved): all three arms are hardware-calibrated, but the SURROGATE has no quantum circuit
in this codebase (it is the classical measure-and-resend null, cl.surrogate_readout). So the
surrogate null band is DERIVED FROM THE HARDWARE closed-arm shots at report time (not reused from
sim) — HW-calibrated, no new circuit, respecting F5's "call F2/F3, do not redefine" scope.

Run (sim-scaffold, no QC — the DRAFT-first-defer deliverable):
    cd THESIS/CriticalQuantumLife/code
    python hardware_batches.py sim --batches 2 --generations 8 --width 8 \\
        --poke flip_expected@boundary --name cql_f5

Run (manual hardware, needs a pinned --backend + QEAAS_API_KEY):
    python hardware_batches.py emit --backend ibm_torino --batch 0 --width 8 --name cql_f5
    # user submits the emitted QPY circuits by hand, drops counts into research_runs/
    python hardware_batches.py ingest --bundle ../research_runs/cql_f5_batch0_closed_*_submit.json \\
        --counts <gen0.json> <gen1.json> ...
    python hardware_batches.py poke --resume ../research_runs/sess_XXXX_state.json --poke flip_expected
    python hardware_batches.py report --session sess_XXXX --name cql_f5
"""
from __future__ import annotations

import argparse
import functools
import glob
import json
import math
import os
import sys
from typing import Any

import numpy as np

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl                        # F0 engine + run-JSON schema (reused)
import session as sess                          # F4 poke + inter-batch persistence (reused)
import criticality as crit                      # F2 metric suite (reused)
import certify                                  # F3 certification (reused)
import draft_gate                               # F1 surprise_drop (reused for the adaptation gap)

if cl._AL not in sys.path:
    sys.path.insert(0, cl._AL)
import stage4_qalife as q4                       # geno_q + witness (reused)
import stage4_scale as s4s                       # gated_chain / run_counts / pipeline_common hooks
import layout                                    # best_chain + live-calibration stats

# pipeline_common is resolved onto sys.path by stage4_scale's import hook; single-source it here
# (real timestamp on hardware so batch files do not overwrite — plan §9).
try:
    from pipeline_common import connect, run_sampler, timestamp  # noqa: F401
except ImportError:                              # pragma: no cover - stubbed like stage4_scale
    connect = getattr(s4s, "connect", None)
    run_sampler = getattr(s4s, "run_sampler", None)
    timestamp = getattr(s4s, "timestamp", cl.timestamp)

from qiskit import qpy
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

# ---- F5 defaults (epic Q3 W=8; §11 resolved) --------------------------------
NAME_DEFAULT = "cql_f5"
WIDTH_DEFAULT = 8
GENS_DEFAULT = 8            # per batch
BATCHES_DEFAULT = 2        # Q2: 2 x 8 = 16 gens (alpha reported INDICATIVE, < F2's 30-gen floor)
SHOTS_DEFAULT = 8192
MAX_TWOQ_ERR = 0.05        # s4s.gated_chain fail-closed thresholds (2q err)
MAX_READOUT_ERR = 0.15     # readout err
K_BAND = 3.0               # certify null-band k (POC ±0.047 at 4096 shots)
CERT_FRAC = 0.8
ALPHA_MIN_GENS = 30        # F2's clean-alpha floor (Q2 caveat)


# ---------------------------------------------------------------------------
# args helpers (mirror draft_gate's F0-default fill so gated_chain / certify / F0 all get knobs)
# ---------------------------------------------------------------------------
def _ensure_qeaas_key() -> bool:
    """Load QEAAS_API_KEY into os.environ if unset, scanning a WIDER path than cl._read_env_key
    (which only checks code/.env and ../.env): also THESIS/.env (two levels up) and the repo root.
    Never prints the value. Returns True if a key is available after the scan."""
    if os.environ.get("QEAAS_API_KEY"):
        return True
    candidates = ("../../.env", "../../../.env", "../.env", ".env")   # THESIS/.env, repo root, ...
    for rel in candidates:
        path = os.path.normpath(os.path.join(_HERE, rel))
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("QEAAS_API_KEY="):
                    os.environ["QEAAS_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return True
    return bool(os.environ.get("QEAAS_API_KEY"))


def _fill_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """Populate every F0 / gated_chain / certify knob the reused code reads, if absent."""
    defaults = (
        ("shots", SHOTS_DEFAULT), ("death", "unitary"), ("interaction", "nn"),
        ("nbins", 10), ("mut_scale", cl.DEFAULT_MUT), ("delta", q4.AGING_DELTA),
        ("gamma", q4.DAMP_GAMMA), ("qrng_url", cl.QEAAS_URL_DEFAULT),
        ("poke_gen", None), ("width", WIDTH_DEFAULT), ("seed", 100),
        ("name", NAME_DEFAULT), ("generations", GENS_DEFAULT),
        ("allow_bad_chain", False), ("max_twoq_err", MAX_TWOQ_ERR),
        ("max_readout_err", MAX_READOUT_ERR), ("k", K_BAND), ("cert_frac", CERT_FRAC),
        ("quantum_run", None), ("surrogate_run", None),
    )
    for name, val in defaults:
        if not hasattr(args, name):
            setattr(args, name, val)
    return args


def _f0_args(args: argparse.Namespace, generations: int, sim: bool) -> argparse.Namespace:
    """A fresh F0-shaped Namespace for run_closed_loop / run_yoked at this batch length."""
    ns = argparse.Namespace(
        width=args.width, generations=generations, shots=args.shots, seed=args.seed,
        name=args.name, mut_scale=args.mut_scale, poke_gen=args.poke_gen, death=args.death,
        interaction=args.interaction, nbins=args.nbins, delta=args.delta, gamma=args.gamma,
        sim=sim, qrng_url=args.qrng_url,
    )
    return ns


# ---------------------------------------------------------------------------
# Fail-closed calibration gate (AC-F5.1) — best_chain gives the stats gated_chain discards
# ---------------------------------------------------------------------------
def gated_chain_with_stats(backend: Any, nq: int,
                           args: argparse.Namespace) -> tuple[list[int], dict[str, Any]]:
    """Pick a clean SWAP-free chain of nq qubits on `backend` and enforce the 2q/readout
    fail-closed gate. Returns (chain, calibration). Unlike s4s.gated_chain (which returns only
    the chain), we call layout.best_chain directly so the live-calibration stats reach the
    submit bundle (AC-F5.1). Fail-closed: a bad chain aborts unless --allow-bad-chain."""
    chain, stats = layout.best_chain(backend, nq)
    twoq_max = float(stats.get("twoq_err_max", 0.0))
    readout_max = float(stats.get("readout_max", 0.0))
    breaches: list[str] = []
    if twoq_max > args.max_twoq_err:
        breaches.append(f"twoq_err_max {twoq_max:.4f} > {args.max_twoq_err}")
    if readout_max > args.max_readout_err:
        breaches.append(f"readout_max {readout_max:.4f} > {args.max_readout_err}")
    if breaches and not args.allow_bad_chain:
        print(f"[ABORT] calibration gate failed (fail-closed): {'; '.join(breaches)}")
        print("        a bad chain sinks the witness below the surrogate null -> false negative.")
        print("        pass --allow-bad-chain to override (NOT for thesis runs).")
        raise SystemExit(1)
    calibration = {
        "twoq_err_mean": float(stats.get("twoq_err_mean", 0.0)),
        "twoq_err_max": twoq_max,
        "readout_max": readout_max,
        "sx_max": float(stats.get("sx_max", 0.0)),
        "dead_avoided": stats.get("dead_avoided"),
        "gated": not breaches,
        "max_twoq_err": args.max_twoq_err,
        "max_readout_err": args.max_readout_err,
    }
    if breaches:
        calibration["gate_override"] = breaches
    return chain, calibration


# ---------------------------------------------------------------------------
# emit (AC-F5.1) — transpile a batch's circuits, dump QPY + the submit bundle. STOPS (no submit).
# ---------------------------------------------------------------------------
def _batch_schedule(args: argparse.Namespace, sim_state: dict[str, Any],
                    generations: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Sim-predict this batch's trajectory (mut_scale schedule + poke flags) via F0's closed
    loop on Aer. Returns (sim_run, stimulation) — the schedule the HW circuits are baked on and
    the sign-check evidence (§5/§7)."""
    batch_args = _f0_args(args, generations, sim=True)
    resume = dict(sim_state)
    if getattr(args, "_pending_poke", None):
        resume["pending_poke"] = args._pending_poke
    # The schedule prediction is NOISELESS; F0's density_matrix sim caps at 15 qubits, so swap in
    # statevector (same fix as run_session_sim) so W=8 (16 qubits) predicts its schedule.
    orig_sim = cl.SIM
    if not getattr(args, "density_matrix", False):
        cl.SIM = AerSimulator()
    try:
        sim_run, stim = cl.run_closed_loop(batch_args, client=None, resume_state=resume)
    finally:
        cl.SIM = orig_sim
    return sim_run, stim


def emit_batch(backend: Any, backend_name: str, arm: str, batch: int,
               sim_state: dict[str, Any], session_id: str, resume_state_path: str | None,
               args: argparse.Namespace) -> str:
    """Emit ONE arm's batch: QRNG angles on the sim-predicted mut_scale schedule, transpiled to
    the gated chain, dumped as QPY, plus the §4 submit bundle. Prints manual-submit steps and
    stops. arm in {"closed","yoked"} (surrogate is derived from HW shots at report time, Q4)."""
    generations = args.generations
    sim_run, stim = _batch_schedule(args, sim_state, generations)
    schedule = [s["mut_scale_used"] for s in stim]
    poke_flags = [bool(r["poke"]) for r in sim_run["generations"]]
    global_gens = [int(r["gen"]) for r in sim_run["generations"]]
    if arm == "yoked":                            # non-contingent: same energy, shuffled schedule
        import random
        random.Random(args.seed + 777).shuffle(schedule)
        poke_flags = [(args.poke_gen is not None and g == args.poke_gen) for g in global_gens]

    client = cl.make_client(_f0_args(args, generations, sim=False))   # fail-closed QRNG on HW
    provenance: list[dict[str, Any]] = []
    steps = args.width
    circuits: list[str] = []
    chain: list[int] | None = None
    calibration: dict[str, Any] = {}

    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    for i, g in enumerate(global_gens):
        repeat = g + (10000 if arm == "yoked" else 0)
        thetas = cl.draw_thetas(client, args.width, schedule[i], repeat, provenance, args.seed)
        qc, _geno = cl.build_generation(args.width, steps, thetas, poke_flags[i], args.death,
                                        args.interaction, args.delta, args.gamma)
        if chain is None:                         # all gens share width -> same qubit count
            chain, calibration = gated_chain_with_stats(backend, qc.num_qubits, args)
        init = chain if len(chain) == qc.num_qubits else None
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                          initial_layout=init)
        isa = pm.run(qc)
        cname = f"{args.name}_batch{batch}_{arm}_gen{g}.qpy"
        with open(os.path.join(cl.OUTPUT_DIR, cname), "wb") as fh:
            qpy.dump([isa], fh)
        circuits.append(cname)

    bundle = {
        "session_id": session_id,
        "batch": batch,
        "arm": arm,
        "backend": backend_name,
        "width": args.width,
        "shots": args.shots,
        "generations_in_batch": generations,
        "global_gens": global_gens,
        "chain": chain,
        "calibration": calibration,               # AC-F5.1 live 2q/readout err
        "circuits": circuits,
        "geno_qubits": [q4.geno_q(k) for k in range(args.width)],
        "resume_state": resume_state_path,        # F4 inherited state this batch continues
        "poke_before_batch": (args._pending_poke if getattr(args, "_pending_poke", None)
                              else None),
        "entropy_source": "prng" if client is None else "qrng",
        "entropy_provenance": provenance,         # QRNG request_id / receipt (plan §9)
        "sim_signcheck": _signcheck(sim_run, args),
    }
    bpath = os.path.join(cl.OUTPUT_DIR,
                         f"{args.name}_batch{batch}_{arm}_{backend_name}_submit.json")
    with open(bpath, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)

    print(f"[emit] arm={arm} batch={batch} backend={backend_name}: "
          f"{len(circuits)} QPY circuits + bundle written")
    print(f"       chain={chain}  cal(twoq_max={calibration['twoq_err_max']:.4f} "
          f"readout_max={calibration['readout_max']:.4f} gated={calibration['gated']})")
    print(f"  -> {bpath}")
    print("  MANUAL: submit each QPY on QC by hand, save per-gen counts JSON, then:")
    print(f"    python hardware_batches.py ingest --bundle {os.path.basename(bpath)} "
          f"--counts <gen0.json> <gen1.json> ...")
    return bpath


# ---------------------------------------------------------------------------
# ingest (AC-F5.1) — user-submitted counts -> F0 batch run-JSON + updated F4 state
# ---------------------------------------------------------------------------
def _load_counts(path: str) -> dict[str, int]:
    """Accept a raw {bitstring: n} counts map, or an object with a 'counts' key."""
    with open(path) as fh:
        obj = json.load(fh)
    if isinstance(obj, dict) and "counts" in obj:
        obj = obj["counts"]
    return {str(k): int(v) for k, v in obj.items()}


def ingest_batch(bundle_path: str, counts_paths: list[str],
                 args: argparse.Namespace) -> tuple[str, str]:
    """Read the user's per-generation counts, push them through F0's observable pipeline
    (witness -> surprise -> entropy -> sigma) into an F0 batch run-JSON with meta.calibration,
    and update + persist the F4 session state for the next batch. Returns (run_path, state_path)."""
    with open(bundle_path) as fh:
        bundle = json.load(fh)
    width = int(bundle["width"])
    shots = int(bundle["shots"])
    arm = bundle["arm"]
    geno = bundle["geno_qubits"]
    if len(counts_paths) != len(bundle["circuits"]):
        print(f"[ABORT] {len(counts_paths)} counts files for {len(bundle['circuits'])} circuits")
        raise SystemExit(1)

    # resume the arm's persisted classical state (running_dist/recent/active_hist/mut_scale)
    state = _load_state_for(bundle["session_id"], arm, bundle.get("resume_state"))
    dist: dict[str, float] = dict(state["running_dist"])
    recent: list[float] = list(state["recent"])
    active_hist: list[bool] = list(state["active_hist"])
    base_mut = args.mut_scale
    mut_scale = float(state["mut_scale"])
    gens: list[dict[str, Any]] = []
    poke_events = list(bundle.get("poke_before_batch") and
                       [{"at_generation": bundle["global_gens"][0], **bundle["poke_before_batch"]}]
                       or [])

    for i, cpath in enumerate(counts_paths):
        g = int(bundle["global_gens"][i])
        counts = _load_counts(cpath)
        joint, sep, wsig = cl.witness_gen(counts, geno, shots)
        key = cl.outcome_key(joint - sep, args.nbins)
        cl.update_running_dist(dist, key, cl.DECAY)
        surprise = cl.surprise_nll(dist, key, args.nbins)
        entropy = cl.pop_entropy(dist)
        surprising = cl.is_surprising(surprise, recent)
        active_hist.append(surprising)
        sigma = cl.running_sigma(active_hist)
        gens.append(cl._row(g, key, surprise, joint, sep, wsig, entropy, surprising,
                            sigma, bool(cl_poke(bundle, i)), shots))
        recent.append(surprise)
        mut_scale = base_mut if surprising else max(mut_scale * 0.7, cl.MUT_FLOOR)

    meta = _hw_meta(bundle, arm, gens)
    run = {"meta": meta, "generations": gens}
    run_path = _write_hw_run(run, args, arm, bundle["backend"])

    final_state = {
        "generation": int(bundle["global_gens"][-1]) + 1,
        "running_dist": dict(dist), "mut_scale": mut_scale,
        "recent": list(recent), "active_hist": [bool(a) for a in active_hist],
    }
    state_path = _save_state_for(bundle["session_id"], arm, final_state, meta, poke_events)
    print(f"[ingest] arm={arm} batch={bundle['batch']}: {len(gens)} gens -> {run_path}")
    print(f"  -> state {state_path}")
    return run_path, state_path


def cl_poke(bundle: dict[str, Any], i: int) -> bool:
    """Whether generation i of this batch carried the interactive poke (first gen only)."""
    return bool(bundle.get("poke_before_batch")) and i == 0


def _hw_meta(bundle: dict[str, Any], arm: str, gens: list[dict[str, Any]]) -> dict[str, Any]:
    """F0-schema meta for a hardware batch run-JSON (sim=False, calibration populated)."""
    return {
        "project": "critical-quantum-life", "study": "critical-quantum-life",
        "arm": arm, "backend": bundle["backend"], "sim": False, "timestamp": timestamp(),
        "seed": None, "width": int(bundle["width"]),
        "generations": len(gens), "shots": int(bundle["shots"]),
        "mut_scale": None, "nbins": None, "death": None, "interaction": None,
        "poke_gen": (gens[0]["gen"] if bundle.get("poke_before_batch") else None),
        "poke_events": (bundle.get("poke_before_batch") and
                        [{"at_generation": gens[0]["gen"], **bundle["poke_before_batch"]}] or []),
        "entropy_source": bundle.get("entropy_source"),
        "entropy_provenance": bundle.get("entropy_provenance", []),
        "calibration": bundle.get("calibration"),      # AC-F5.1
        "session_id": bundle["session_id"],
        "batch": bundle["batch"],
        "outcome_model": "witness-bin (Option A)",
    }


def _write_hw_run(run: dict[str, Any], args: argparse.Namespace,
                  arm: str, backend: str) -> str:
    """Write a hardware batch run-JSON with a REAL timestamp (not F0's 'sim' stub)."""
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    fname = f"{args.name}_{arm}_{backend}_b{run['meta']['batch']}_{timestamp()}_run.json"
    path = os.path.join(cl.OUTPUT_DIR, fname)
    with open(path, "w") as fh:
        json.dump(run, fh, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# Per-arm session state (closed and yoked persist independently across batches)
# ---------------------------------------------------------------------------
def _state_path(session_id: str, arm: str) -> str:
    return os.path.join(cl.OUTPUT_DIR, f"{session_id}_{arm}_state.json")


def _seed_state() -> dict[str, Any]:
    return {"generation": 0, "running_dist": {}, "mut_scale": cl.DEFAULT_MUT,
            "recent": [], "active_hist": []}


def _load_state_for(session_id: str, arm: str,
                    fallback_path: str | None) -> dict[str, Any]:
    for p in (_state_path(session_id, arm), fallback_path):
        if p and os.path.exists(p):
            with open(p) as fh:
                payload = json.load(fh)
            return payload.get("state", payload)
    return _seed_state()


def _consume_pending_poke(session_id: str, arm: str,
                          resume: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Load an arm's persisted carry-over state + any queued interactive poke, then CLEAR the
    queued poke from the file (it is about to be baked into this batch). Returns (state, poke).
    Falls back to the F4 single state file, then to a fresh seed state (batch 0)."""
    for p in (_state_path(session_id, arm), os.path.join(cl.OUTPUT_DIR, f"{session_id}_state.json"),
              resume):
        if not p or not os.path.exists(p):
            continue
        with open(p) as fh:
            payload = json.load(fh)
        state = payload.get("state", payload)
        pending = payload.get("pending_poke")
        if pending is not None:                   # consume: do not re-apply on the next batch
            payload["pending_poke"] = None
            with open(p, "w") as fh:
                json.dump(payload, fh, indent=2, default=str)
        return state, pending
    return _seed_state(), None


def _save_state_for(session_id: str, arm: str, state: dict[str, Any],
                    meta: dict[str, Any], poke_events: list[dict[str, Any]]) -> str:
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = _state_path(session_id, arm)
    payload = {"session_id": session_id, "arm": arm, "meta": meta,
               "state": state, "poke_log": poke_events}
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# sim scaffold (DRAFT-first-defer, Q4) — the whole batched/persisted/poked pipeline on Aer
# ---------------------------------------------------------------------------
def _signcheck(run: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Cheap GO-like read on a sim run: does the witness clear the analytic null, does surprise
    fall? (Not the full F3 certification — that is build_report's job.)"""
    band = args.k / math.sqrt(max(1, args.shots))
    gens = run["generations"]
    above = sum(1 for r in gens if r["witness_signal"] > band)
    return {"null_band": band, "gens_above_band": above, "gens_total": len(gens),
            "frac_above_band": (above / len(gens)) if gens else 0.0,
            "surprise_drop": draft_gate.surprise_drop(gens)}


def run_session_sim(args: argparse.Namespace) -> dict[str, Any]:
    """Run the F5 shape on Aer: a Session (F4) of `batches` closed batches with a poke at the
    boundary (persistence proof), plus total-span yoked + surrogate controls, then build_report.
    This is the sim sign-check gating any QC spend."""
    # F0's simulator is density_matrix (capped ~15 qubits, chosen so a noise_model can be layered).
    # The sign-check is NOISELESS (real noise only lands on hardware), so swap in statevector to
    # let W=8 (16 qubits) actually simulate. --density-matrix forces F0's default (W<=7 only).
    orig_sim = cl.SIM
    if not getattr(args, "density_matrix", False):
        cl.SIM = AerSimulator()                   # automatic -> statevector for these circuits
    try:
        return _run_session_sim(args)
    finally:
        cl.SIM = orig_sim


def _run_session_sim(args: argparse.Namespace) -> dict[str, Any]:
    kind, when = sess._parse_poke_spec(args.poke)
    f4_args = _f0_args(args, args.generations, sim=True)
    f4_args.batches = args.batches
    session = sess.Session(f4_args)
    print(f"=== CQL F5 sim-scaffold {session.session_id}: {args.batches} batches x "
          f"{args.generations} gens, W={args.width}, poke={kind}@{when} ===")

    closed_runs: list[dict[str, Any]] = []
    poke_global: int | None = None
    for b in range(args.batches):
        if kind is not None and when == "boundary" and b == 1:
            session.poke(kind)
            poke_global = session.state["generation"]
        elif kind is not None and isinstance(when, int) and session.state["generation"] == when:
            session.poke(kind)
            poke_global = session.state["generation"]
        run = session.run_batch(args.generations)
        run["meta"]["backend"] = "sim"
        path = _write_hw_run({**run, "meta": {**run["meta"], "batch": b}}, args, "closed", "sim")
        print(f"  batch {b}: gens {run['generations'][0]['gen']}.."
              f"{run['generations'][-1]['gen']}  -> {path}")
        closed_runs.append(run)
    state_path = session.save()
    print(f"  -> session state {state_path}")

    total = args.generations * args.batches
    total_args = _f0_args(args, total, sim=True)
    total_args.poke_gen = poke_global
    _closed_full, stim = cl.run_closed_loop(total_args, client=None)
    yoked = cl.run_yoked(total_args, stim, client=None)
    yoked["meta"]["session_id"] = session.session_id
    _write_hw_run({**yoked, "meta": {**yoked["meta"], "batch": 0}}, args, "yoked", "sim")

    report = build_report_from(closed_runs, yoked, args, session.session_id, "sim", poke_global)
    _print_signcheck_verdict(report, args)
    return report


# ---------------------------------------------------------------------------
# poke between batches (AC-F5.2) — queue an interactive poke onto a persisted state
# ---------------------------------------------------------------------------
def poke_between(session_id: str, kind: str, params: dict[str, Any],
                 args: argparse.Namespace) -> str:
    """Queue an interactive poke to be applied on the FIRST generation of the NEXT emitted batch,
    for both HW arms' persisted states. Records it; emits no circuits (F4 semantics)."""
    if kind not in sess.POKE_KINDS:
        raise SystemExit(f"[ABORT] poke kind {kind!r} not in {sess.POKE_KINDS}")
    # HW arms persist per-arm state files (after ingest); a sim session persists F4's single
    # {session_id}_state.json. Poke whichever exist so the queue lands on the live population.
    candidates = [_state_path(session_id, "closed"), _state_path(session_id, "yoked"),
                  os.path.join(cl.OUTPUT_DIR, f"{session_id}_state.json")]
    written: list[str] = []
    for p in candidates:
        if not os.path.exists(p):
            continue
        with open(p) as fh:
            payload = json.load(fh)
        payload["pending_poke"] = {"kind": kind, "params": params}
        gen = payload.get("state", {}).get("generation", 0)
        payload.setdefault("poke_log", []).append(
            {"at_generation": gen, "kind": kind, "params": params})
        with open(p, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
        written.append(p)
    print(f"[poke] queued {kind}{params or ''} onto {len(written)} arm state(s) for {session_id}")
    for w in written:
        print(f"  -> {w}")
    return session_id


# ---------------------------------------------------------------------------
# build_report (AC-F5.3) — adaptation gap + F2 metrics + tau + F3 sigma-margin at W
# ---------------------------------------------------------------------------
def _merge_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Concatenate per-batch runs (sorted by first gen) into one run for F2/F3 (proves the
    persisted population is one continuous trajectory across the batch boundaries)."""
    ordered = sorted(runs, key=lambda r: r["generations"][0]["gen"])
    gens = [g for r in ordered for g in r["generations"]]
    meta = dict(ordered[-1]["meta"])
    meta["generations"] = len(gens)
    poked = [g["gen"] for g in gens if g.get("poke")]
    meta["poke_gen"] = poked[0] if poked else meta.get("poke_gen")
    return {"meta": meta, "generations": gens}


def _surrogate_from_shots(qgens: list[dict[str, Any]], width: int, seed: int) -> dict[str, Any]:
    """Q4: derive the classical measure-and-resend surrogate from the HARDWARE closed-arm shots
    (not sim). Per gen, cl.surrogate_readout at that gen's shot count -> the HW-calibrated null."""
    rng = np.random.default_rng(seed + 555)
    sgens: list[dict[str, Any]] = []
    for r in qgens:
        joint, sep, wsig = cl.surrogate_readout(rng, width, int(r["shots"]))
        sgens.append(cl._row(r["gen"], "0", 0.0, joint, sep, wsig, 0.0, False, None,
                             bool(r.get("poke")), int(r["shots"])))
    return {"meta": {"arm": "surrogate", "width": width, "source": "hw_closed_shots"},
            "generations": sgens}


def build_report_from(closed_runs: list[dict[str, Any]], yoked: dict[str, Any],
                      args: argparse.Namespace, session_id: str, backend: str,
                      poke_global: int | None) -> dict[str, Any]:
    """Assemble the F5 report dict (§4) from in-memory runs and write it."""
    closed = _merge_runs(closed_runs)
    cgens, ygens = closed["generations"], yoked["generations"]
    closed_drop = draft_gate.surprise_drop(cgens)
    yoked_drop = draft_gate.surprise_drop(ygens)

    criticality = crit.analyze(closed)
    total_gens = len(cgens)
    criticality["alpha_underpowered"] = total_gens < ALPHA_MIN_GENS   # Q2 caveat
    tau_block = criticality["relaxation_tau"]

    surrogate = _surrogate_from_shots(cgens, args.width, args.seed)
    cert_args = argparse.Namespace(shots=args.shots, k=args.k, cert_frac=args.cert_frac,
                                   quantum_run=f"{session_id}_closed", surrogate_run=None)
    certification = certify.certify(closed, surrogate, cert_args)

    report = {
        "session_id": session_id, "width": args.width, "backend": backend,
        "generations_total": total_gens, "poke_gen": poke_global,
        "adaptation_gap": {"closed_drop": closed_drop, "yoked_drop": yoked_drop,
                           "gap": closed_drop - yoked_drop},         # AC-F5.3
        "criticality": criticality,                                   # F2 block (AC-F5.3)
        "relaxation_tau": {"tau": tau_block.get("tau"),
                           "poke_gen": tau_block.get("poke_gen"),
                           "r2": tau_block.get("r2")},                # AC-F5.3
        "certification": certification,                              # F3 sigma-margin (AC-F5.3)
    }
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, f"{args.name}_report.json")
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"  -> report {path}")
    return report


def build_report(session_id: str, args: argparse.Namespace) -> dict[str, Any]:
    """Load a session's batch run-JSONs from research_runs/ and assemble the report (CLI path)."""
    # A session id (seed+name) is stable across DIFFERENT runs (e.g. a W=8 sim sign-check and a
    # later W=6 HW run share it). Scope the report to ONE coherent (backend, width): the target is
    # the NEWEST closed run's, so sim and hardware runs never merge into one figure.
    paths = sorted(glob.glob(os.path.join(cl.OUTPUT_DIR, "*_run.json")), key=os.path.getmtime)
    matched: list[tuple[dict[str, Any], float]] = []
    for p in paths:
        with open(p) as fh:
            run = json.load(fh)
        if run.get("meta", {}).get("session_id") == session_id:
            matched.append((run, os.path.getmtime(p)))
    if not matched:
        print(f"[ABORT] no run-JSONs for session {session_id} in {cl.OUTPUT_DIR}")
        raise SystemExit(1)
    newest_closed = next((r for r, _ in reversed(matched) if r["meta"].get("arm") == "closed"), None)
    if newest_closed is None:
        print(f"[ABORT] no closed-arm run-JSONs for session {session_id}")
        raise SystemExit(1)
    backend = newest_closed["meta"].get("backend", "unknown")
    tgt_width = newest_closed["meta"].get("width")
    closed_runs, yoked_runs = [], []
    for run, _mt in matched:
        m = run["meta"]
        if m.get("backend") != backend or m.get("width") != tgt_width:
            continue                              # drop stale runs from a different backend/width
        arm = m.get("arm")
        (closed_runs if arm == "closed" else yoked_runs if arm == "yoked" else []).append(run)
    if not yoked_runs:
        print(f"[ABORT] no yoked-arm run-JSONs for session {session_id} at {backend}/W{tgt_width} "
              f"(need the adaptation gap)")
        raise SystemExit(1)
    print(f"[report] session {session_id}: backend={backend} width={tgt_width}  "
          f"closed_batches={len(closed_runs)} yoked_batches={len(yoked_runs)}")
    args.width = tgt_width                        # honor the scoped run's width (not the CLI default)
    poked = [g["gen"] for r in closed_runs for g in r["generations"] if g.get("poke")]
    return build_report_from(closed_runs, _merge_runs(yoked_runs), args, session_id, backend,
                             poked[0] if poked else None)


def _print_signcheck_verdict(report: dict[str, Any], args: argparse.Namespace) -> None:
    c = report["certification"]["certification"]
    gap = report["adaptation_gap"]
    crit_block = report["criticality"]
    sig = crit_block["sigma"]["mean"]
    print("\n=== F5 sim sign-check (GO/no-go before any QC spend) ===")
    print(f"  adaptation gap: closed_drop={gap['closed_drop']:+.3f} "
          f"yoked_drop={gap['yoked_drop']:+.3f}  gap={gap['gap']:+.3f}  (want > 0)")
    print(f"  witness above null: {c['gens_above_band']}/{c['gens_total']} "
          f"({c['frac_above_band']:.2f} >= {c['cert_frac']}?)  band ±{c['null_band']:.3f}  "
          f"certified={c['certified']}")
    print(f"  sigma mean={sig if sig is None else round(sig, 3)} (want -> 1)   "
          f"alpha={crit_block['avalanche_alpha'].get('alpha')} "
          f"(indicative, {report['generations_total']}<{ALPHA_MIN_GENS} gens)"
          if crit_block["alpha_underpowered"] else "")
    tau = report["relaxation_tau"]["tau"]
    print(f"  post-poke tau={tau if tau is None else round(tau, 3)} at poke_gen="
          f"{report['relaxation_tau']['poke_gen']}")
    go = gap["gap"] > 0 and c["certified"]
    print(f"\n  SIGN-CHECK: {'GO (mechanism present on sim; safe to submit HW)' if go else 'NO-GO (fix before QC)'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _add_common(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--width", type=int, default=WIDTH_DEFAULT)
    ap.add_argument("--generations", type=int, default=GENS_DEFAULT, help="generations per batch")
    ap.add_argument("--shots", type=int, default=SHOTS_DEFAULT)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default=NAME_DEFAULT)
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=cl.DEFAULT_MUT)
    ap.add_argument("--nbins", type=int, default=10)
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--interaction", choices=["none", "nn"], default="nn")
    ap.add_argument("--delta", type=float, default=q4.AGING_DELTA)
    ap.add_argument("--gamma", type=float, default=q4.DAMP_GAMMA)
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=None)
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=cl.QEAAS_URL_DEFAULT)
    ap.add_argument("--k", type=float, default=K_BAND)
    ap.add_argument("--cert-frac", dest="cert_frac", type=float, default=CERT_FRAC)
    ap.add_argument("--max-twoq-err", dest="max_twoq_err", type=float, default=MAX_TWOQ_ERR)
    ap.add_argument("--max-readout-err", dest="max_readout_err", type=float, default=MAX_READOUT_ERR)
    ap.add_argument("--allow-bad-chain", dest="allow_bad_chain", action="store_true")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F5 — hardware batch runs (scaled, manual)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sim", help="sim-scaffold the whole batched/persisted/poked session (Aer)")
    _add_common(ps)
    ps.add_argument("--batches", type=int, default=BATCHES_DEFAULT)
    ps.add_argument("--poke", type=str, default="flip_expected@boundary")
    ps.add_argument("--density-matrix", dest="density_matrix", action="store_true",
                    help="force F0's density_matrix sim (W<=7 only); default statevector for W=8")

    pe = sub.add_parser("emit", help="emit a batch's QPY circuits + submit bundle (needs --backend)")
    _add_common(pe)
    pe.add_argument("--backend", type=str, required=True, help="pinned Heron device (Q1)")
    pe.add_argument("--batch", type=int, required=True)
    pe.add_argument("--arm", choices=["closed", "yoked", "both"], default="both")
    pe.add_argument("--resume", type=str, default=None, help="prior session state to continue")

    pi = sub.add_parser("ingest", help="ingest user-submitted counts -> batch run-JSON + state")
    _add_common(pi)
    pi.add_argument("--bundle", type=str, required=True)
    pi.add_argument("--counts", type=str, nargs="+", required=True, help="per-gen counts JSONs")

    pp = sub.add_parser("poke", help="queue an interactive poke onto a persisted session state")
    _add_common(pp)
    pp.add_argument("--session", type=str, required=True, help="session id (sess_XXXX)")
    pp.add_argument("--poke", type=str, required=True, help="'<kind>' or '<kind>@<when>'")

    pr = sub.add_parser("report", help="assemble the F5 report from a session's run-JSONs")
    _add_common(pr)
    pr.add_argument("--session", type=str, required=True, help="session id (sess_XXXX)")

    args = _fill_defaults(ap.parse_args())

    if args.cmd == "sim":
        run_session_sim(args)
    elif args.cmd == "emit":
        if connect is None:
            print("[ABORT] pipeline_common.connect unavailable (no IBM plumbing on path)")
            raise SystemExit(1)
        if not _ensure_qeaas_key():
            print("[ABORT] QEAAS_API_KEY not found (checked env, THESIS/.env, repo-root .env)")
            raise SystemExit(1)
        try:
            backend = connect(args.backend)
        except Exception as exc:                  # noqa: BLE001 - manual tool: fail clean, not a trace
            print(f"[ABORT] could not connect to backend {args.backend!r}: {exc}")
            print("        set up your IBM account (QiskitRuntimeService) and pin a live Heron.")
            raise SystemExit(1)
        session_id = sess.new_session_id(args.seed, args.name)
        arms = ("closed", "yoked") if args.arm == "both" else (args.arm,)
        for arm in arms:
            # Continue THIS arm's persisted population (auto — no --resume needed) and apply any
            # poke queued between batches; consume it so it fires once.
            state, pending = _consume_pending_poke(session_id, arm, args.resume)
            args._pending_poke = pending
            state_path = (_state_path(session_id, arm)
                          if os.path.exists(_state_path(session_id, arm)) else args.resume)
            emit_batch(backend, args.backend, arm, args.batch, state, session_id,
                       state_path, args)
    elif args.cmd == "ingest":
        ingest_batch(args.bundle, args.counts, args)
    elif args.cmd == "poke":
        kind, _when = sess._parse_poke_spec(args.poke if "@" in args.poke
                                            else f"{args.poke}@boundary")
        poke_between(args.session, kind, {}, args)
    elif args.cmd == "report":
        build_report(args.session, args)


if __name__ == "__main__":
    main()
