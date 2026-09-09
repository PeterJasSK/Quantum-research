#!/usr/bin/env python3
"""Critical Quantum Life — F8: the Quantum Sandpile (dynamic-circuit builder + runner).

The self-organized (self-TUNED) counterpart to the HAND-tuned absorbing-state / directed-
percolation transitions of arXiv:2512.07966 (30 qubits) and IBM arXiv:2509.18259 (100 qubits).
Those experiments locate criticality by externally tuning the measurement rate p; the Sandpile
adds the ONE thing they lack — a drive-when-quiet feedback loop (slow drive + fast dissipation,
Dickman-Munoz-Vespignani-Zapperi 1998, cond-mat/9712115) — so the processor SELF-ORGANIZES to
that critical point with no fine-tuning. That self-tuning is the entire identity of the project,
and it is the study that fixes the failed Run-1 criticality gate (sigma=0.44) BY DESIGN.

This is a GENUINELY NEW dynamic-circuit builder (plan section 1: F0's `build_generation` emits one
static GHZ-genealogy circuit with terminal `measure_all()` and a unitary death stand-in; there are
ZERO `if_test` / mid-circuit `measure` / `reset` primitives elsewhere in code/). The Sandpile is a
monitored circuit turned into a sandpile: grains = quanta of activity (a site in a non-|0> /
measured-1 state), toppling = measurement-induced relaxation toward |0> (the absorbing/"dead"
state), and the pile self-parks at the critical slope.

One time-step on a W-site chain (one qubit per site), assembled as a dynamic circuit:
  1. SPREAD      one brick-wall layer of 2-qubit XX+YY hopping gates -> activity spreads to
                 neighbours (the branching term).
  2. DISSIPATE   mid-circuit `measure` EVERY site into that step's classical register, then a
                 feed-forward conditional `reset` toward |0> on the sites the (fixed) relaxation
                 mask selects (fast, non-tuned dissipation). Sites left un-reset carry their
                 excitation forward -> partial dissipation, so avalanches can last many steps.
  3. DRIVE-WHEN-QUIET (the SOC trick) read global activity A = popcount of this step's register;
                 if A == 0 (the pile went flat) inject exactly ONE grain (feed-forward X on one
                 site, gated by `if_test((creg, 0))`); else nothing. NO measurement rate is set by
                 hand -- the system chooses its own operating point.
  mode="closed" gates the grain on quiescence (the SOC rule). mode="yoked" (AC-F8.3) injects on a
  precomputed random schedule at the SAME average rate but at random times regardless of
  quiescence -- the control that proves "self-organized": the drive-when-quiet rule self-tunes to
  criticality; the yoked random drive does not.

Extraction: each Aer shot is one independent stochastic SOC trajectory of T steps (memory=True),
so `trajectories` is the real DP substrate (avalanches, branching sigma) and `steps` is the
shot-ensemble summary (per-site mean occupation, mean active-count A, grain-fire fraction).

Reuses (imported, NOT reimplemented): `layout.best_chain` (F5 chain picker), `certify` null band
(F3), `criticality` alpha/sigma fits (F2) -- the last two via sandpile_analysis.

Run (Aer dynamic sim):
    cd THESIS/CriticalQuantumLife/code
    python sandpile.py --width 12 --steps 60 --mode closed --shots 2048 --seed 100
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import os
import sys
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl                          # OUTPUT_DIR + run-JSON idioms (reused)

# Aer with a dynamic-circuit-capable method (if_test + mid-circuit measure + reset). Automatic
# picks statevector for the small widths the Aer go/no-go uses; hardware carries the real cost.
SIM = AerSimulator()

# ---- sandpile constants (plan section 4/9; Dickman "slow drive + fast dissipation") ----------
SPREAD_THETA = 1.20        # brick-wall XX+YY hopping angle (the branching strength), fixed
RELAX_P = 0.35             # relaxation strength: fraction of active sites that topple (reset) per
#                            step. FIXED hyperparameter (fast dissipation), NOT the SOC knob -- the
#                            self-organization comes from drive-when-quiet, not from tuning this
#                            (it is the 180-min tier's robustness-sweep axis, plan section 5).
GRAIN_SIZE = 1             # grains injected per quiescent step (robustness-sweep axis)


def _relax_mask(width: int, steps: int, seed: int) -> np.ndarray:
    """Deterministic per-step, per-site toppling mask at rate RELAX_P (fast dissipation). Fixed at
    build time so the circuit is reproducible; masked-in active sites reset toward |0>."""
    rng = np.random.default_rng(seed + 4242)
    return rng.random((steps, width)) < RELAX_P


def _drive_sites(width: int, steps: int, seed: int) -> list[int]:
    """One random drive site per step (the grain lands here IF the step drives)."""
    rng = np.random.default_rng(seed + 909)
    return [int(rng.integers(0, width)) for _ in range(steps)]


def yoked_schedule(steps: int, rate: float, seed: int) -> list[int]:
    """AC-F8.3 matched-rate random injection times: the yoked control injects grains at the same
    average `rate` as the closed loop but at RANDOM steps regardless of quiescence. `rate` is the
    closed loop's measured drive fraction (grain-fire steps / total), so the energy matches."""
    rng = np.random.default_rng(seed + 313)
    return [t for t in range(steps) if rng.random() < rate]


# ---------------------------------------------------------------------------
# The dynamic-circuit builder (AC-F8.1)
# ---------------------------------------------------------------------------
def build_step(qc: QuantumCircuit, qr: QuantumRegister, creg: ClassicalRegister,
               drive_site: int, relax: np.ndarray, mode: str,
               yoked_fire: bool) -> None:
    """Append ONE time-step (spread -> dissipate -> drive-when-quiet) to `qc`, recording this
    step's per-site activity into `creg`. `relax` is this step's W-length toppling mask.

    mode="closed": drive is gated on quiescence via `if_test((creg, 0))` (the SOC rule).
    mode="yoked" : drive fires unconditionally iff `yoked_fire` (precomputed matched-rate schedule).
    """
    width = len(qr)
    # 1. SPREAD -- one brick-wall layer of XX+YY hopping (even pairs, then odd pairs).
    for start in (0, 1):
        for a in range(start, width - 1, 2):
            qc.rxx(SPREAD_THETA, qr[a], qr[a + 1])
            qc.ryy(SPREAD_THETA, qr[a], qr[a + 1])
    # 2. DISSIPATE -- mid-circuit measure every site, then feed-forward conditional reset toward
    #    |0> on the toppling sites (fast, fixed dissipation).
    for i in range(width):
        qc.measure(qr[i], creg[i])
    for i in range(width):
        if relax[i]:
            with qc.if_test((creg[i], 1)):        # feed-forward: an active site topples to |0>
                qc.reset(qr[i])
    # 3. DRIVE-WHEN-QUIET -- inject GRAIN_SIZE grain(s) as mass on DISTINCT sites (contiguous block
    #    from drive_site, wrapping). Repeated X on ONE site cancels (X*X = I), so grains must land on
    #    separate qubits to actually add activity mass.
    grain_sites = [(drive_site + d) % width for d in range(min(GRAIN_SIZE, width))]
    if mode == "closed":
        with qc.if_test((creg, 0)):               # A == 0 (whole register quiescent) -> seed grains
            for q in grain_sites:
                qc.x(qr[q])
    elif mode == "yoked":
        if yoked_fire:                            # non-contingent: fires on the schedule, not on A
            for q in grain_sites:
                qc.x(qr[q])
    else:
        raise ValueError(f"unknown mode {mode!r} (expected 'closed' or 'yoked')")


def build_trajectory(width: int, steps: int, mode: str, seed: int,
                     drive_rate: float | None = None,
                     init: str = "cold") -> tuple[QuantumCircuit, list[int]]:
    """Assemble the full T-step dynamic circuit (one ClassicalRegister per step so the per-step,
    per-site activity survives to the counts). Returns (circuit, drive_sites). For mode="yoked" a
    `drive_rate` (the closed loop's measured drive fraction) is required to match the injection
    energy; the yoked schedule is baked in at build time (AC-F8.3).

    init selects the SOC basin (the both-sides convergence test, Dickman et al.: a self-organized
    critical point is an ATTRACTOR reached from either side):
      * "cold" -- the empty/absorbing start (all |0>); the pile climbs UP from below as drive-when-
        quiet seeds it. The frozen basin.
      * "hot"  -- the saturated/chaotic start (all sites active, X on every qubit); fast dissipation
        pulls it DOWN from above. The chaotic basin. If cold and hot converge to the SAME steady
        density/sigma under the identical drive-when-quiet rule, the set-point is self-organized,
        not an artefact of the initial condition.
    """
    qr = QuantumRegister(width, "s")
    cregs = [ClassicalRegister(width, f"c{t}") for t in range(steps)]
    qc = QuantumCircuit(qr, *cregs)
    if init == "hot":                             # chaotic-side basin: start saturated
        for i in range(width):
            qc.x(qr[i])
    elif init != "cold":
        raise ValueError(f"unknown init {init!r} (expected 'cold' or 'hot')")
    relax = _relax_mask(width, steps, seed)
    drive_sites = _drive_sites(width, steps, seed)
    fire = set()
    if mode == "yoked":
        if drive_rate is None:
            raise ValueError("yoked mode needs drive_rate (the closed loop's measured drive fraction)")
        fire = set(yoked_schedule(steps, drive_rate, seed))
    for t in range(steps):
        build_step(qc, qr, cregs[t], drive_sites[t], relax[t], mode, yoked_fire=(t in fire))
    return qc, drive_sites


# ---------------------------------------------------------------------------
# Runner + extraction (AC-F8.2)
# ---------------------------------------------------------------------------
def _parse_memory(memory: list[str], width: int, steps: int) -> np.ndarray:
    """(shots, steps) array of per-shot per-step active-count A. Aer `get_memory` joins the
    per-step ClassicalRegisters with spaces, LAST register first, so tokens are reversed to
    chronological order; within a token the rightmost char is clbit 0."""
    out = np.zeros((len(memory), steps), dtype=np.int32)
    for s, rec in enumerate(memory):
        tokens = rec.split()[::-1]                # chronological c0, c1, ... c_{T-1}
        for t, tok in enumerate(tokens[:steps]):
            out[s, t] = tok.count("1")
    return out


def _parse_sites(memory: list[str], width: int, steps: int) -> np.ndarray:
    """(steps, width) shot-mean per-site occupation, chronological; site i = bit at position
    width-1-i within the step token."""
    acc = np.zeros((steps, width), dtype=float)
    for rec in memory:
        tokens = rec.split()[::-1]
        for t, tok in enumerate(tokens[:steps]):
            tok = tok.rjust(width, "0")
            for i in range(width):
                if tok[width - 1 - i] == "1":
                    acc[t, i] += 1.0
    return acc / max(1, len(memory))


def run_trajectory(width: int, steps: int, mode: str, backend: Any, seed: int,
                   shots: int = 2048, drive_rate: float | None = None,
                   chain: list[int] | None = None,
                   calibration: dict[str, Any] | None = None,
                   init: str = "cold") -> dict[str, Any]:
    """Run one Sandpile trajectory circuit on Aer (backend=None). Returns the plan-section-4 run
    dict: per-step ensemble series + the per-shot A-trajectories (the DP substrate) + the injected-
    grain events. `init` selects the SOC basin ('cold' empty | 'hot' saturated) for the both-sides
    convergence test."""
    qc, drive_sites = build_trajectory(width, steps, mode, seed, drive_rate, init)
    if backend is None:
        res = SIM.run(transpile(qc, SIM), shots=shots, memory=True).result()
        memory = res.get_memory()
    else:
        raise NotImplementedError("hardware backend is sandpile_batches.py (emit -> manual submit)")
    return assemble_run(memory, width, steps, mode, seed, shots, drive_sites,
                        drive_rate, chain, calibration, backend, init)


def assemble_run(memory: list[str], width: int, steps: int, mode: str, seed: int,
                 shots: int, drive_sites: list[int], drive_rate: float | None,
                 chain: list[int] | None, calibration: dict[str, Any] | None,
                 backend: Any, init: str = "cold") -> dict[str, Any]:
    """Build the run dict from per-shot memory (shared by the Aer path and the hardware ingest)."""
    traj = _parse_memory(memory, width, steps)            # (shots, steps) A per shot
    sites = _parse_sites(memory, width, steps)            # (steps, width) mean occupation
    A_mean = traj.mean(axis=0)                             # ensemble mean active-count per step
    quiescent_frac = (traj == 0).mean(axis=0)             # fraction of shots quiescent per step
    grain_fire = quiescent_frac if mode == "closed" else _yoked_fire_series(steps, drive_rate, seed)
    steps_out: list[dict[str, Any]] = []
    for t in range(steps):
        steps_out.append({
            "t": t,
            "activity_sites": [round(float(x), 4) for x in sites[t]],   # shot-mean occupation
            "A": float(A_mean[t]),                          # expected active-site count
            "density": float(A_mean[t] / width),
            "grain_injected": bool(grain_fire[t] > 0.5) if mode == "yoked" else float(grain_fire[t]),
            "grain_site": int(drive_sites[t]),
        })
    return {
        "meta": {
            "project": "critical-quantum-life", "study": "quantum-sandpile",
            "arm": mode, "init": init, "backend": "sim" if backend is None else str(backend),
            "sim": backend is None, "width": width, "steps": steps, "shots": shots,
            "seed": seed, "spread_theta": SPREAD_THETA, "relax_p": RELAX_P,
            "grain_size": GRAIN_SIZE, "drive_rate_target": drive_rate,
            "drive_fraction": float((traj == 0).any(axis=0).mean()) if mode == "closed"
            else (len(yoked_schedule(steps, drive_rate or 0.0, seed)) / max(1, steps)),
            "chain": chain, "calibration": calibration,
        },
        "steps": steps_out,
        "trajectories": traj.tolist(),                     # per-shot A-series (DP substrate)
    }


def _yoked_fire_series(steps: int, drive_rate: float | None, seed: int) -> np.ndarray:
    fire = set(yoked_schedule(steps, drive_rate or 0.0, seed))
    return np.array([1.0 if t in fire else 0.0 for t in range(steps)])


def measured_drive_rate(closed_run: dict[str, Any]) -> float:
    """The closed loop's realised drive fraction (quiescent steps / total), used to size the yoked
    control's matched injection energy (AC-F8.3)."""
    traj = np.array(closed_run["trajectories"], dtype=int)
    if traj.size == 0:
        return 0.0
    quiescent_steps = (traj == 0).any(axis=0)              # a step that drove in >=1 shot
    return float(quiescent_steps.mean())


# ---------------------------------------------------------------------------
# Cluster witness (AC-F8.5) -- certification layer, NOT the headline (plan section 9 risk)
# ---------------------------------------------------------------------------
def build_cluster_witness(width: int, steps: int, seed: int,
                          cluster: list[int]) -> QuantumCircuit:
    """Warm the pile to its steady state with `steps` closed steps, then rotate the active CLUSTER
    (a contiguous sub-block, Q2 -- the full-chain product died at W=32) into the X basis and measure
    it. Counts give the cluster witness <X^{cluster}> for the F3 null-band certification."""
    qr = QuantumRegister(width, "s")
    warm = [ClassicalRegister(width, f"c{t}") for t in range(steps)]
    wit = ClassicalRegister(len(cluster), "w")
    qc = QuantumCircuit(qr, *warm, wit)
    relax = _relax_mask(width, steps, seed)
    drive_sites = _drive_sites(width, steps, seed)
    for t in range(steps):
        build_step(qc, qr, warm[t], drive_sites[t], relax[t], "closed", yoked_fire=False)
    for j, q in enumerate(cluster):                        # X-basis readout on the cluster
        qc.h(qr[q])
        qc.measure(qr[q], wit[j])
    return qc


def witness_trajectory(width: int, steps: int, seed: int, cluster: list[int],
                       backend: Any, shots: int = 4096) -> tuple[float, float]:
    """(joint <X^{cluster}>, separable prod<X_i>) at the self-organized steady state. The witness
    register is the LAST classical register, so it is the FIRST token of each memory record."""
    qc = build_cluster_witness(width, steps, seed, cluster)
    if backend is not None:
        raise NotImplementedError("hardware witness is sandpile_batches.py")
    memory = SIM.run(transpile(qc, SIM), shots=shots, memory=True).result().get_memory()
    k = len(cluster)
    signs = np.ones((len(memory), k), dtype=int)
    for s, rec in enumerate(memory):
        tok = rec.split()[0].rjust(k, "0")                 # witness register is last-created -> first
        for j in range(k):
            if tok[k - 1 - j] == "1":
                signs[s, j] = -1
    joint = float(np.prod(signs, axis=1).mean())
    sep = float(np.prod(signs.mean(axis=0)))
    return joint, sep


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_run(run: dict[str, Any], name: str) -> str:
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    m = run["meta"]
    fname = (f"{name}_{m['arm']}_{m.get('init', 'cold')}_{m['backend']}"
             f"_W{m['width']}_T{m['steps']}_seed{m['seed']}_run.json")
    path = os.path.join(cl.OUTPUT_DIR, fname)
    with open(path, "w") as f:
        json.dump(run, f, indent=2, default=str)
    return path


def _print_trace(run: dict[str, Any]) -> None:
    m = run["meta"]
    print(f"  arm={m['arm']:6} W={m['width']} steps={m['steps']} drive_frac={m['drive_fraction']:.3f}")
    print("    t   A    density  grain")
    for s in run["steps"]:
        g = s["grain_injected"]
        gs = f"{g:.2f}" if isinstance(g, float) else str(g)
        print(f"    {s['t']:3d}  {s['A']:4.1f}  {s['density']:6.3f}  {gs}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F8 — Quantum Sandpile trajectory (Aer dynamic sim)")
    ap.add_argument("--width", type=int, default=12)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--mode", choices=["closed", "yoked", "both"], default="both")
    ap.add_argument("--init", choices=["cold", "hot"], default="cold",
                    help="SOC basin: cold (empty start) | hot (saturated/chaotic start)")
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="sandpile")
    args = ap.parse_args()

    print(f"=== CQL F8 Sandpile: W={args.width} steps={args.steps} shots={args.shots} "
          f"seed={args.seed} init={args.init} theta={SPREAD_THETA} relax_p={RELAX_P} ===")
    closed = run_trajectory(args.width, args.steps, "closed", None, args.seed, args.shots,
                            init=args.init)
    _print_trace(closed)
    print(f"  -> {write_run(closed, args.name)}")
    if args.mode in ("yoked", "both"):
        rate = measured_drive_rate(closed)
        yoked = run_trajectory(args.width, args.steps, "yoked", None, args.seed, args.shots,
                               drive_rate=rate)
        _print_trace(yoked)
        print(f"  -> {write_run(yoked, args.name)}")
        cd = float(np.mean([s["density"] for s in closed["steps"][args.steps // 2:]]))
        yd = float(np.mean([s["density"] for s in yoked["steps"][args.steps // 2:]]))
        print(f"\n  steady-state density: closed={cd:.3f}  yoked={yd:.3f}  "
              f"(closed should self-park nonzero; yoked drifts — the decisive contrast)")


if __name__ == "__main__":
    main()
