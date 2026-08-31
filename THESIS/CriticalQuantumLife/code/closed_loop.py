#!/usr/bin/env python3
"""Critical Quantum Life — F0: the closed-loop engine + core observable suite.

Forks the recreated 2018 quantum-artificial-life engine (../../../artificial-life/code/
stage4_qalife.py) into a CLOSED-LOOP engine: each generation the quantum genome (a GHZ
genealogy) is measured, gets feedback CONTINGENT on its own outcome (predictable when the
outcome was expected, high-entropy / QRNG-seeded when it was surprising), and reorganizes
across generations to minimize its own surprise (Friston free-energy / DishBrain, Kagan 2022).
It also ships the YOKED-CONTROL runner (same stimulation, feedback decoupled from outcomes)
and the observable logger that writes the one run-JSON schema every other ticket reads.

Option A — witness-as-outcome (developer-selected).
--------------------------------------------------
The genome is a GHZ genealogy (founder |+> + CNOT clone chain), which the entanglement
witness <X^{⊗W}> requires. A GHZ's single-qubit marginals are maximally mixed, so local
mutation Ry(theta) leaves phenotype <sigma_z> / alive-mask / alive-count INVARIANT —
information lives only in the JOINT witness. So the per-generation OUTCOME is the discretized
witness (as the POC did: it keyed feedback on the witness scalar), NOT an alive-mask.
Criticality therefore lives in the surprise-AVALANCHE process (Beggs & Plenz 2003): `active`
= a generation whose surprise beats the running median; F2 fits avalanche alpha and the
branching sigma -> 1 of that process. See plan §4/§7/§12.

The three honesty gates (epic law) — F0 produces their raw material, does not judge them:
  1. adaptation : closed-loop surprise falls where the yoked control's does not  (F1)
  2. criticality: the surprise-avalanche process sits at the edge of chaos (sigma≈1)  (F2)
  3. quantum    : witness_signal stays above the classical surrogate null            (F3)

Reuses (imported, NOT reimplemented): stage4_qalife genome + <X^{⊗W}> witness, qrng_client.

Run (sim):
    cd THESIS/CriticalQuantumLife/code
    python closed_loop.py --arm both --generations 15 --width 4 --seed 100 --name cql_f0
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import os
import random
import statistics
import sys
from typing import Any

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
_AL = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "artificial-life", "code"))
if _AL not in sys.path:
    sys.path.insert(0, _AL)

import stage4_qalife as q4                     # genome primitives + <X^{⊗W}> witness (reused)
from qrng_client import QRNGClient, QRNGUnavailable  # noqa: F401  (QRNGUnavailable used on HW, F5)

SIM = AerSimulator(method="density_matrix")    # Q4: density_matrix so F5 can layer a noise_model
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))
QEAAS_URL_DEFAULT = "https://api.qeaas.eu/"

# ---- closed-loop constants (plan §7; resolved Q2/Q3) -------------------------
DECAY = 0.8              # Q2: exponential decay of the running outcome distribution
MUT_FLOOR = 0.01         # lower bound on mut_scale when tightening (avoid collapse to 0)
LAPLACE_ALPHA = 0.1      # smoothing per bin for surprise = -log P(bin)
SIG_WINDOW = 6           # generations in the coarse running-sigma window (F2 supersedes)
DEFAULT_MUT = 0.60       # explore ("full") mutation scale — tuned so the witness actually moves


def timestamp() -> str:
    """Stub; F5 swaps in pipeline_common.timestamp for real hardware run tags."""
    return "sim"


def _read_env_key(name: str) -> str | None:
    """Scan ../.env then ./.env for NAME=... (ported from stage4_scale.py)."""
    for rel in ("../.env", ".env"):
        path = os.path.normpath(os.path.join(_HERE, rel))
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{name}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------------------
# Entropy source (QRNG on hardware, labelled PRNG fallback on sim)
# ---------------------------------------------------------------------------
def make_client(args: argparse.Namespace) -> QRNGClient | None:
    """Return None on --sim (PRNG fallback). On hardware build a fail-closed client."""
    if args.sim:
        return None
    api_key = os.environ.get("QEAAS_API_KEY") or _read_env_key("QEAAS_API_KEY")
    url = args.qrng_url or os.environ.get("QEAAS_API_URL") or QEAAS_URL_DEFAULT
    if not api_key:
        print("[ABORT] hardware run needs QEAAS_API_KEY (fail-closed)")
        raise SystemExit(1)
    client = QRNGClient(url, api_key)
    if client.health().status != "ok":
        print("[ABORT] QRNG health not 'ok' (fail-closed)")
        raise SystemExit(1)
    return client


def draw_thetas(client: QRNGClient | None, width: int, mut_scale: float,
                repeat: int, provenance: list[dict[str, Any]], seed: int) -> list[float]:
    """`width` mutation angles at the given mut_scale. QRNG block-fetch on hardware
    (theta_k = mut_scale*pi*(u32/2**32)); labelled PRNG fallback on sim."""
    if client is None:
        return q4._sim_thetas(width, seed * 1000 + repeat, mut_scale)
    need = 4 * width
    buf = bytearray()
    while len(buf) < need:
        resp = client.fetch(size=32, fmt="hex")
        buf.extend(bytes.fromhex(resp.data))
        provenance.append({"request_id": resp.request_id, "receipt": resp.receipt})
    thetas: list[float] = []
    for k in range(width):
        u32 = int.from_bytes(buf[4 * k:4 * k + 4], "big")
        thetas.append(mut_scale * math.pi * (u32 / 2 ** 32))
    return thetas


# ---------------------------------------------------------------------------
# Outcome / running distribution / surprise (Option A — witness-as-outcome)
# ---------------------------------------------------------------------------
def witness_gen(counts: dict[str, int], geno_qubits: list[int],
                shots: int) -> tuple[float, float, float]:
    """(joint, separable, shot-floor sigma) of <X^{⊗W}> over the genotype qubits.
    Reuses q4.xbasis_witness_from_counts (X-basis: H applied before Z-readout)."""
    joint, sep = q4.xbasis_witness_from_counts(counts, geno_qubits)
    return joint, sep, math.sqrt(1.0 / max(1, shots))


def surrogate_readout(rng: np.random.Generator, width: int,
                      shots: int) -> tuple[float, float, float]:
    """F3 measure-and-resend readout (the classical null). Each shot collapses every genome
    qubit to an independent classical bit, so the X-basis parity <X^{⊗W}> averages to 0 — a
    classical population CANNOT forge the genealogical witness. Mirrors
    proof_of_concept/classical_life.witness_classical. Returns (joint, separable, shot-floor
    sigma) with the SAME signature as witness_gen so the closed loop is provably identical."""
    signs = rng.integers(0, 2, size=(shots, width)) * 2 - 1     # ±1, independent per qubit
    joint = float(np.prod(signs, axis=1).mean())                 # <X^{⊗W}> per shot, averaged
    sep = float(np.prod(signs.mean(axis=0)))                     # factorized null (product of marginals)
    return joint, sep, math.sqrt(1.0 / max(1, shots))


def outcome_key(witness_signal: float, nbins: int) -> str:
    """Discretize the witness signal (joint-separable) in [-1,1] into `nbins` bins."""
    b = int(round((max(-1.0, min(1.0, witness_signal)) + 1.0) / 2.0 * (nbins - 1)))
    return str(max(0, min(nbins - 1, b)))


def update_running_dist(dist: dict[str, float], key: str, decay: float) -> None:
    """Exponentially-decayed running frequency of witness-bin outcomes (in place)."""
    for k in list(dist):
        dist[k] *= decay
    dist[key] = dist.get(key, 0.0) + (1.0 - decay)


def surprise_nll(dist: dict[str, float], key: str, nbins: int) -> float:
    """-log P(observed bin) under the running distribution, Laplace-smoothed (AC-F0.3)."""
    total = sum(dist.values())
    p = (dist.get(key, 0.0) + LAPLACE_ALPHA) / (total + LAPLACE_ALPHA * nbins)
    return -math.log(p)


def is_surprising(surprise: float, recent: list[float]) -> bool:
    """Surprising = surprise above the running median of prior surprises (Q2)."""
    if not recent:
        return False
    return surprise > statistics.median(recent)


def pop_entropy(dist: dict[str, float]) -> float:
    """Shannon entropy of the running witness-bin distribution."""
    total = sum(dist.values()) or 1.0
    h = 0.0
    for v in dist.values():
        p = v / total
        if p > 0:
            h -= p * math.log(p)
    return h


def running_sigma(active_hist: list[bool]) -> float | None:
    """COARSE branching of the surprise-activity process: active-count in the recent half
    over the prior half of a SIG_WINDOW window. None until the window fills. F2 supersedes."""
    if len(active_hist) < SIG_WINDOW:
        return None
    half = SIG_WINDOW // 2
    window = active_hist[-SIG_WINDOW:]
    prev = sum(window[:half])
    now = sum(window[half:])
    return (now / prev) if prev > 0 else None


# ---------------------------------------------------------------------------
# Circuit builder + runner
# ---------------------------------------------------------------------------
def build_generation(width: int, steps: int, thetas: list[float], poke: bool,
                     death: str, interaction: str, delta: float, gamma: float):
    """One generation's GHZ genealogy (founder |+> ⇒ the witness's GHZ), measured in the
    X basis on the genotype qubits. poke adds the POC coherence scramble on the founder."""
    qc = q4.build_population(width, steps, thetas, interaction, death=death,
                             founder_equator=True, delta=delta, gamma=gamma, measure=False)
    geno = [q4.geno_q(k) for k in range(width)]
    if poke:
        qc.ry(math.pi / 2, q4.geno_q(0))    # POKE: scramble the founder -> witness dips
    qc.h(geno)                              # rotate X -> Z so counts give <X^{⊗W}>
    qc.measure_all()
    return qc, geno


def run_counts(qc, shots: int, backend: Any) -> dict[str, int]:
    """Sim path (F0). F5 wires the hardware sampler; backend is always None here."""
    if backend is None:
        return SIM.run(transpile(qc, SIM), shots=shots).result().get_counts()
    raise NotImplementedError("hardware backend is F5 (hardware_batches.py)")


def _meta(args: argparse.Namespace, arm: str, backend: Any,
          entropy_source: str, provenance: list[dict[str, Any]],
          poke_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if poke_events is None:                  # F1 readability: scripted single poke = one-element list
        poke_events = ([{"at_generation": args.poke_gen, "kind": "scripted", "params": {}}]
                       if args.poke_gen is not None else [])
    return {
        "project": "critical-quantum-life",
        "study": "critical-quantum-life",
        "arm": arm,
        "backend": "sim" if backend is None else str(backend),
        "sim": backend is None,
        "timestamp": timestamp(),
        "seed": args.seed,
        "width": args.width,
        "generations": args.generations,
        "shots": args.shots,
        "mut_scale": args.mut_scale,
        "nbins": args.nbins,
        "death": args.death,
        "interaction": args.interaction,
        "poke_gen": args.poke_gen,           # kept readable for F1 (scripted single poke)
        "poke_events": poke_events,          # F4: full ordered poke list (Q1)
        "entropy_source": entropy_source,
        "entropy_provenance": provenance,
        "calibration": None,
        "outcome_model": "witness-bin (Option A)",
    }


def _row(gen: int, key: str, surprise: float, joint: float, sep: float, wsig: float,
         entropy: float, active: bool, sigma: float | None, poke: bool, shots: int) -> dict[str, Any]:
    return {
        "gen": gen,
        "outcome": key,
        "surprise": surprise,
        "witness_joint": joint,
        "witness_separable": sep,
        "witness_signal": joint - sep,
        "witness_sigma": wsig,
        "entropy": entropy,
        "active": active,
        "sigma": sigma,
        "poke": poke,
        "shots": shots,
    }


def run_closed_loop(args: argparse.Namespace, client: QRNGClient | None,
                    backend: Any = None, surrogate: bool = False,
                    resume_state: dict[str, Any] | None = None,
                    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The closed loop: measure witness -> surprise -> contingent feedback on mut_scale ->
    next generation. Returns (run_dict, stimulation) — stimulation feeds the yoked arm.
    run_dict carries a private "final_state" key (stripped by write_run) that F4 persists.

    surrogate (F3 hook, Q2): run the IDENTICAL loop but swap ONLY the readout — a classical
    measure-and-resend collapse (surrogate_readout) instead of the entangled witness. Every
    other step (surprise, contingent feedback, selection) is unchanged, so the resulting null
    band is a valid control (arm='surrogate', witness_signal ≈ 0).

    resume_state (F4 hook): continue the SAME population instead of starting at gen 0. Seeds
    dist/recent/active_hist/mut_scale from a persisted state and offsets the generation counter
    so `draw_thetas` rebuilds the ongoing genealogy (thetas are deterministic in seed+gen — no
    genome snapshot is carried). An optional resume_state["pending_poke"] = {kind, params} is
    an interactive F4 poke applied on the FIRST generation of this batch:
      * inject_stimulus -> POC ry(pi/2) coherence prod on the founder (witness dips)
      * flip_expected   -> invert the contingency (expected<->surprising) for that gen
      * alter_selection -> scale the explore-pressure baseline (params["factor"], default 2.0)
    The scripted --poke-gen (F1 non-interactive gate) is unchanged: it scrambles AND flips."""
    dist: dict[str, float] = dict(resume_state["running_dist"]) if resume_state else {}
    recent: list[float] = list(resume_state["recent"]) if resume_state else []
    active_hist: list[bool] = list(resume_state["active_hist"]) if resume_state else []
    gens: list[dict[str, Any]] = []
    stimulation: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    poke_events: list[dict[str, Any]] = []
    sur_rng = np.random.default_rng(args.seed + 555) if surrogate else None
    base_mut = args.mut_scale                # explore magnitude (alter_selection may shift it)
    mut_scale = resume_state["mut_scale"] if resume_state else args.mut_scale
    start_gen = resume_state["generation"] if resume_state else 0
    pending = resume_state.get("pending_poke") if resume_state else None
    steps = args.width                       # aging gradient along the line (not a CLI knob)
    for i in range(args.generations):
        g = start_gen + i                    # GLOBAL generation index (thetas keyed on it)
        scramble = False                     # inject_stimulus / scripted: POC ry(pi/2) prod
        flip = False                         # flip_expected / scripted: invert the contingency
        if pending is not None and i == 0:   # interactive F4 poke on the FIRST gen of this batch
            kind = pending["kind"]
            params = dict(pending.get("params", {}))
            if kind == "inject_stimulus":
                scramble = True
            elif kind == "flip_expected":
                flip = True
            elif kind == "alter_selection":
                factor = float(params.get("factor", 2.0))
                base_mut *= factor           # persistent shift of the explore-pressure baseline
                mut_scale *= factor
            poke_events.append({"at_generation": g, "kind": kind, "params": params})
        if args.poke_gen is not None and g == args.poke_gen:   # scripted F1 poke (scramble + flip)
            scramble = True
            flip = True
            poke_events.append({"at_generation": g, "kind": "scripted", "params": {}})
        poke = scramble or flip
        thetas = draw_thetas(client, args.width, mut_scale, g, provenance, args.seed)
        qc, geno = build_generation(args.width, steps, thetas, scramble, args.death,
                                    args.interaction, args.delta, args.gamma)
        if surrogate:                        # swap ONLY the readout (Q1/Q2) — loop otherwise identical
            joint, sep, wsig = surrogate_readout(sur_rng, args.width, args.shots)
        else:
            counts = run_counts(qc, args.shots, backend)
            joint, sep, wsig = witness_gen(counts, geno, args.shots)
        key = outcome_key(joint - sep, args.nbins)
        update_running_dist(dist, key, DECAY)
        surprise = surprise_nll(dist, key, args.nbins)
        entropy = pop_entropy(dist)
        surprising = is_surprising(surprise, recent)
        if flip:
            surprising = not surprising      # poke inverts the contingency for this generation
        active_hist.append(surprising)
        sigma = running_sigma(active_hist)
        gens.append(_row(g, key, surprise, joint, sep, wsig, entropy, surprising,
                         sigma, poke, args.shots))
        stimulation.append({"gen": g, "mut_scale_used": mut_scale,
                            "expected": (not surprising),
                            "feedback_kind": "high-entropy" if surprising else "predictable"})
        # contingent feedback for the NEXT generation (Q3)
        mut_scale = base_mut if surprising else max(mut_scale * 0.7, MUT_FLOOR)
        recent.append(surprise)
    entropy_source = "prng" if client is None else "qrng"
    arm = "surrogate" if surrogate else "closed"
    final_state = {                          # F4: the real carry-over state (plan §4/§7, Q_STATE)
        "generation": start_gen + args.generations,
        "running_dist": dict(dist),
        "mut_scale": mut_scale,
        "recent": list(recent),
        "active_hist": [bool(a) for a in active_hist],
    }
    run = {"meta": _meta(args, arm, backend, entropy_source, provenance, poke_events),
           "generations": gens, "stimulation": stimulation, "final_state": final_state}
    return run, stimulation


def run_yoked(args: argparse.Namespace, stimulation: list[dict[str, Any]],
              client: QRNGClient | None, backend: Any = None) -> dict[str, Any]:
    """Yoked control (Q5): replay the SAME multiset of mut_scale events the closed arm used,
    seed-shuffled and DECOUPLED from this arm's outcomes. Same stimulation energy, zero
    contingency -> its surprise should NOT fall. Surprise is still logged against its own dist."""
    schedule = [s["mut_scale_used"] for s in stimulation]
    random.Random(args.seed + 777).shuffle(schedule)
    dist: dict[str, float] = {}
    recent: list[float] = []
    active_hist: list[bool] = []
    gens: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    steps = args.width
    for g in range(args.generations):
        mut_scale = schedule[g]              # non-contingent: from the shuffled schedule, not this arm's outcome
        thetas = draw_thetas(client, args.width, mut_scale, g + 10000, provenance, args.seed)
        poke = (args.poke_gen is not None and g == args.poke_gen)
        qc, geno = build_generation(args.width, steps, thetas, poke, args.death,
                                    args.interaction, args.delta, args.gamma)
        counts = run_counts(qc, args.shots, backend)
        joint, sep, wsig = witness_gen(counts, geno, args.shots)
        key = outcome_key(joint - sep, args.nbins)
        update_running_dist(dist, key, DECAY)
        surprise = surprise_nll(dist, key, args.nbins)
        entropy = pop_entropy(dist)
        surprising = is_surprising(surprise, recent)
        if poke:
            surprising = not surprising
        active_hist.append(surprising)
        sigma = running_sigma(active_hist)
        gens.append(_row(g, key, surprise, joint, sep, wsig, entropy, surprising,
                         sigma, poke, args.shots))
        recent.append(surprise)
    entropy_source = "prng" if client is None else "qrng"
    return {"meta": _meta(args, "yoked", backend, entropy_source, provenance),
            "generations": gens}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_run(run: dict[str, Any], args: argparse.Namespace) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    arm = run["meta"]["arm"]
    backend = run["meta"]["backend"]
    fname = f"{args.name}_{arm}_{backend}_seed{args.seed}_{timestamp()}_run.json"
    path = os.path.join(OUTPUT_DIR, fname)
    disk = {k: v for k, v in run.items() if k != "final_state"}   # F4 carry-over lives in the state file
    with open(path, "w") as f:
        json.dump(disk, f, indent=2, default=str)
    return path


def _print_table(run: dict[str, Any]) -> None:
    print(f"  arm={run['meta']['arm']:6}  gen  outcome  surprise  witness  entropy  active  sigma")
    for r in run["generations"]:
        sig = "  -  " if r["sigma"] is None else f"{r['sigma']:4.2f}"
        note = " <-- POKE" if r["poke"] else ""
        print(f"        {r['gen']:15d}  {r['outcome']:>4}  {r['surprise']:7.3f}  "
              f"{r['witness_signal']:+.3f}  {r['entropy']:6.3f}  {str(r['active']):>5}  {sig}{note}")


def _surprise_drop(run: dict[str, Any], win: int = 3) -> float:
    s = [r["surprise"] for r in run["generations"]]
    if len(s) < 2 * win:
        return s[0] - s[-1]
    return statistics.fmean(s[:win]) - statistics.fmean(s[-win:])


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F0 — closed-loop engine + observable suite")
    ap.add_argument("--generations", type=int, default=15)
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="cql_f0")
    ap.add_argument("--arm", choices=["closed", "yoked", "both"], default="both")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=DEFAULT_MUT)
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=None)
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--interaction", choices=["none", "nn"], default="nn")
    ap.add_argument("--nbins", type=int, default=10)
    ap.add_argument("--delta", type=float, default=q4.AGING_DELTA)
    ap.add_argument("--gamma", type=float, default=q4.DAMP_GAMMA)
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=QEAAS_URL_DEFAULT)
    args = ap.parse_args()

    client = make_client(args)
    print(f"=== CQL F0 closed-loop: width={args.width} generations={args.generations} "
          f"death={args.death} mut_scale={args.mut_scale} nbins={args.nbins} "
          f"arm={args.arm} sim={args.sim} ===")

    closed = yoked = None
    stimulation: list[dict[str, Any]] = []
    if args.arm in ("closed", "both"):
        closed, stimulation = run_closed_loop(args, client)
        _print_table(closed)
        print(f"  -> {write_run(closed, args)}")
    if args.arm in ("yoked", "both"):
        if not stimulation:                  # yoked alone: derive a stimulation trace first
            _, stimulation = run_closed_loop(args, client)
        yoked = run_yoked(args, stimulation, client)
        _print_table(yoked)
        print(f"  -> {write_run(yoked, args)}")

    if closed and yoked:
        cd, yd = _surprise_drop(closed), _surprise_drop(yoked)
        print(f"\n  surprise drop (early-late): closed={cd:+.3f}  yoked={yd:+.3f}  "
              f"gap={cd - yd:+.3f}  (F1 judges the adaptation gate)")


if __name__ == "__main__":
    main()
