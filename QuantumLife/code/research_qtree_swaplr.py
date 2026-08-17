#!/usr/bin/env python3
"""
research_qtree_swaplr.py -- SWAP-LADDER long-range counterpart to
research_qtree_teleport.py. This is the honest, depth-costly baseline the
teleport route is meant to BEAT.

Both files apply the EXACT same long-range bond: a CNOT between slot i's angle
qubit and a distant slot j's angle qubit (slot-distance --bond-dist), on top of
the same brick-wall neighbour chain. They differ only in HOW the long-range CX
is realised:

    teleport (research_qtree_teleport.py)
        1 Bell pair + 2 mid-circuit measures + feed-forward X/Z.
        ~constant depth, needs 2 ancillas per bond, needs a dynamic circuit.

    SWAP ladder (THIS FILE)
        walk slot i's qubit down the chain with SWAPs until it is physically
        adjacent to slot j, apply CX, then walk it back:
            for p in i .. j-1:  SWAP(p, p+1)      # carry i's state to j-1
            CX(j-1, j)
            for p in j-1 .. i+1: SWAP(p-1, p)     # restore every qubit
        No ancillas, no dynamic circuit, no feed-forward -- but the bond costs
        ~2*(j-i) SWAPs, i.e. O(qubit-distance) depth. At a 36-qubit separation
        that is ~72 SWAPs (~216 CX after decomposition) PER BOND PER GENERATION,
        which on Heron r2 largely decoheres before measurement.

The SWAP ladder up-then-down is a net identity permutation, so the genome
register is restored and exactly one long-range CX is applied -- logically
identical to the teleported bond, just deep. Same C(d) metric, same "bonds"
block (c_at_d at the exact bonded qubits), so the two output files diff cleanly:

    HYPOTHESIS: teleport keeps c_at_d above noise where the SWAP ladder has
    decohered it to ~0, at a fraction of the depth. If instead SWAP wins or ties,
    that bounds how much feed-forward latency costs on current hardware.

Classical --sim is the shared honest null (no entanglement, no long-range term);
--sim-longrange gives the same non-physical preview as the teleport file so the
two can be A/B'd off-hardware for plumbing/visual checks.

Nothing here touches qtree.py, the neighbour-chain forks, runs/, or the viewer.
Output goes to QuantumLife/research_runs/.

USAGE
    # honest classical null (shared baseline with the teleport file)
    python research_qtree_swaplr.py --sim \
        --generations 8 --shots 4096 --seed 100 --repeats 3 --name swap_null

    # hardware, SWAP-ladder long-range bonds (the deep alternative)
    python research_qtree_swaplr.py \
        --generations 8 --shots 4096 --seed 100 --repeats 3 --layers 1 \
        --bond-dist 6 --anchors 0,3,6 --name swap_L1_hw

Then diff swap_L1_hw vs tel_L1_hw summaries at matched --seed/--bond-dist.

OPTIONS  identical to research_qtree_teleport.py MINUS nothing:
    --bond-dist D / --anchors i,j,.. / --entangler / --sim-longrange / --seed
    --repeats / --corr-dmax / --generations --shots --layers --backend --sim
    --qubits --no-auto-qubits --name.

OUTPUT
    research_runs/<TAG>_<backend|sim>_seed<K>_<ts>_run.json  and _summary.json,
    same schema as the teleport file (variant="swap-longrange", no ancillas),
    so a single reader can load both and overlay c_at_d vs depth.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# --- reuse the Calibration study's submission pipeline without editing it -----
# pipeline_common.py has moved between layouts; try each known location.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in ("code", os.path.join("old", "code"), os.path.join("new", "code")):
    _p = os.path.normpath(
        os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", _cand))
    if os.path.exists(os.path.join(_p, "pipeline_common.py")):
        sys.path.insert(0, _p)
        break
from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

from genome import GENOME_SPEC, decode_field  # noqa: E402  (local, same dir)

OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# growth / evolution knobs (identical to every other fork -> results transfer)
CHARACTER_LR = 0.18
WIGGLE = 0.05
MUT_SCALE = 0.30
CROSS_ANGLE = 0.7
WIND_SCALE = 0.4
LIGHT_SCALE = 0.5
SEASON_SCALE = 0.9
FORK_BIAS = 0.3
LEAF_BIAS = 0.45
THETA_LO, THETA_HI = 0.08, math.pi - 0.08


# ---------------------------------------------------------------------------
# per-run environment schedule (seeded per repeat) -- identical to the forks
# ---------------------------------------------------------------------------
def build_env(generations: int) -> tuple[list[dict], dict]:
    period = random.randint(6, 12)
    phase = random.uniform(0, 2 * math.pi)
    wind_period = random.randint(4, 9)
    wind_phase = random.uniform(0, 2 * math.pi)
    wind_prevail = random.uniform(-0.08, 0.08)
    light_side = random.choice([-1.0, 1.0])
    light_str = random.uniform(0.15, 0.35)

    env = []
    for g in range(generations):
        season = 0.5 + 0.5 * math.sin(2 * math.pi * g / period + phase)
        gust = (wind_prevail
                + 0.3 * math.sin(2 * math.pi * g / wind_period + wind_phase)
                + random.uniform(-0.07, 0.07))
        angle_bias = WIND_SCALE * gust + LIGHT_SCALE * light_side * light_str
        season_bias = SEASON_SCALE * (2 * season - 1)
        env.append({
            "season": round(season, 4),
            "wind": round(gust, 4),
            "light_side": light_side,
            "angle_bias": round(angle_bias, 4),
            "season_bias": round(season_bias, 4),
        })
    meta = {"period": period, "phase": round(phase, 4),
            "wind_period": wind_period, "wind_phase": round(wind_phase, 4),
            "wind_prevail": round(wind_prevail, 4),
            "light_side": light_side, "light_str": round(light_str, 4)}
    return env, meta


def resolve_bonds(anchors: list[int], dist: int, n_slots: int) -> list[tuple[int, int]]:
    """Each anchor slot s bonds to slot s+dist; drop pairs off the register."""
    bonds = []
    for s in anchors:
        t = s + dist
        if 0 <= s < n_slots and 0 <= t < n_slots and s != t:
            bonds.append((s, t))
    return bonds


# ---------------------------------------------------------------------------
# circuit  (base = brick-wall neighbour chain + SWAP-ladder long-range bonds)
# ---------------------------------------------------------------------------
def _entangle(qc: QuantumCircuit, n: int, mode: str) -> None:
    if mode == "serial":
        for i in range(n - 1):
            qc.cx(i, i + 1)
        for i in range(n - 1):
            qc.crx(CROSS_ANGLE, i, i + 1)
        return
    for i in range(0, n - 1, 2):
        qc.cx(i, i + 1)
    for i in range(1, n - 1, 2):
        qc.cx(i, i + 1)
    for i in range(0, n - 1, 2):
        qc.crx(CROSS_ANGLE, i, i + 1)
    for i in range(1, n - 1, 2):
        qc.crx(CROSS_ANGLE, i, i + 1)


def _swap_cx(qc, lo, hi) -> None:
    """Long-range CNOT(lo -> hi) with lo < hi via a SWAP ladder.

    Carry lo's state up to hi-1, CX onto hi, then reverse every SWAP so the
    register permutation is the identity and only the long-range CX remains.
    Cost ~ 2*(hi-lo) SWAPs -> O(distance) depth (the point of the baseline)."""
    for p in range(lo, hi - 1):
        qc.swap(p, p + 1)
    qc.cx(hi - 1, hi)
    for p in range(hi - 1, lo, -1):
        qc.swap(p - 1, p)


def build_circuit(theta, kick, env, layers, spec, entangler,
                  bonds) -> QuantumCircuit:
    n = spec["n_bits"]
    sb, ns = spec["slot_bits"], spec["n_slots"]
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)

    for i in range(n):
        qc.ry(theta[i], i)

    for _ in range(max(1, layers)):
        _entangle(qc, n, entangler)

    # long-range CX via SWAP ladder between distant slots' angle bits
    for (si, sj) in bonds:
        qi, qj = si * sb, sj * sb
        lo, hi = (qi, qj) if qi < qj else (qj, qi)
        _swap_cx(qc, lo, hi)

    ab, sbias = env["angle_bias"], env["season_bias"]
    for s in range(ns):
        base = s * sb
        qc.rx(ab, base + 0)
        qc.rx(ab, base + 1)
        qc.ry(sbias, base + 2)
        qc.ry(sbias, base + 3)
        qc.ry(sbias, base + 4)
        qc.ry(FORK_BIAS, base + 4)
        qc.ry(LEAF_BIAS, base + 5)

    for i in range(n):
        if kick[i]:
            qc.rx(kick[i], i)

    qc.measure(qr, cr)
    return qc


# ---------------------------------------------------------------------------
# statistics  (identical to the teleport fork -> numbers directly comparable)
# ---------------------------------------------------------------------------
def _binH(x: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def field_stats(fields: list[str], n: int):
    shots = len(fields)
    p = [sum(1 for f in fields if f[i] == "1") / shots for i in range(n)]
    counts = Counter(fields)
    modal = counts.most_common(1)[0][0]
    samples = [b for b, _ in counts.most_common() if b != modal][:4]
    diversity = sum(_binH(pi) for pi in p) / n
    return p, modal, samples, diversity


def two_point_correlation(fields: list[str], n: int, dmax: int) -> dict:
    dmax = min(dmax, n - 1)
    M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(len(fields), n)
    M = (M - ord("0")).astype(np.float64)
    p = M.mean(axis=0)
    C0 = float(np.mean(p * (1.0 - p)))
    C = [C0]
    for d in range(1, dmax + 1):
        joint = (M[:, : n - d] * M[:, d:]).mean(axis=0)
        conn = joint - p[: n - d] * p[d:]
        C.append(float(conn.mean()))
    c = [ci / C0 if C0 > 1e-12 else 0.0 for ci in C]
    xi = float(sum(c[1:]))
    return {"C": [round(x, 6) for x in C],
            "c": [round(x, 6) for x in c],
            "C0": round(C0, 6),
            "xi": round(xi, 5),
            "dmax": dmax}


def bond_correlations(fields, n, bonds, sb) -> list[dict]:
    """Connected correlation between each pair's bonded angle qubits -- the
    long-range term, at the exact qubits (same definition as the teleport fork)."""
    if not bonds:
        return []
    M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(len(fields), n)
    M = (M - ord("0")).astype(np.float64)
    p = M.mean(axis=0)
    C0 = float(np.mean(p * (1.0 - p)))
    out = []
    for (si, sj) in bonds:
        qi, qj = si * sb, sj * sb
        joint = float((M[:, qi] * M[:, qj]).mean())
        conn = joint - p[qi] * p[qj]
        out.append({
            "i": si, "j": sj, "d_qubits": abs(qj - qi),
            "C_ij": round(conn, 6),
            "c_at_d": round(conn / C0, 6) if C0 > 1e-12 else 0.0,
        })
    return out


def next_belief(theta: list[float], p: list[float], n: int):
    theta_next, kick_next = [], []
    for i in range(n):
        drift = CHARACTER_LR * (2 * p[i] - 1)
        wig = random.uniform(-WIGGLE, WIGGLE)
        t = min(THETA_HI, max(THETA_LO, theta[i] + drift + wig))
        theta_next.append(t)
        kick_next.append(MUT_SCALE * (2 * p[i] - 1))
    return theta_next, kick_next


# ---------------------------------------------------------------------------
# runners
# ---------------------------------------------------------------------------
def run_sim(theta, kick, env, n, shots, spec, bonds, sim_longrange):
    """Shared honest null with the teleport fork; --sim-longrange gives the same
    non-physical preview (source angle parity copied into target)."""
    sb = spec["slot_bits"]
    base = []
    for i in range(n):
        a = theta[i] + kick[i]
        local = i % sb
        if local in (0, 1):
            a += env["angle_bias"] * 0.5
        if local == 4:
            a += FORK_BIAS
        if local == 5:
            a += LEAF_BIAS
        p1 = math.sin(a / 2) ** 2
        if local in (2, 3, 4):
            p1 += 0.25 * env["season_bias"]
        base.append(min(0.98, max(0.02, p1)))
    sm = [0.7 * base[i] + 0.15 * base[(i - 1) % n] + 0.15 * base[(i + 1) % n]
          for i in range(n)]
    out = []
    for _ in range(shots):
        bits = ["1" if random.random() < sm[i] else "0" for i in range(n)]
        if sim_longrange:
            for (si, sj) in bonds:
                qi, qj = si * sb, sj * sb
                if random.random() < 0.85:
                    bits[qj] = bits[qi]
        out.append("".join(bits))
    return out, 0.0


def run_hw(backend, qc, qubit_list, shots):
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=qubit_list)
    isa = pm.run(qc)
    raw_meas, _jobs, qs = run_sampler(backend, isa, shots)
    return [s[::-1] for s in raw_meas], qs


# ---------------------------------------------------------------------------
# one full growth run at one seed
# ---------------------------------------------------------------------------
def run_once(args, seed, backend, backend_name, calib, qubit_list, spec, n, bonds):
    random.seed(seed)
    env_sched, env_meta = build_env(args.generations)
    sb = spec["slot_bits"]

    theta = [math.pi / 2] * n
    kick = [0.0] * n
    generations: list[dict[str, Any]] = []
    total_qs = 0.0

    for g in range(args.generations):
        env = env_sched[g]
        qc = build_circuit(theta, kick, env, args.layers, spec,
                           args.entangler, bonds)
        depth = qc.depth()
        if args.sim:
            fields, qs = run_sim(theta, kick, env, n, args.shots, spec,
                                 bonds, args.sim_longrange)
        else:
            fields, qs = run_hw(backend, qc, qubit_list, args.shots)
        total_qs += qs

        p, modal, samples, diversity = field_stats(fields, n)
        corr = two_point_correlation(fields, n, args.corr_dmax)
        bcorr = bond_correlations(fields, n, bonds, sb)
        generations.append({
            "gen": g,
            "logical_depth": depth,
            "ancillas": 0,
            "shots": args.shots,
            "bits": modal,
            "samples": samples,
            "p": [round(x, 5) for x in p],
            "diversity": round(diversity, 5),
            "correlation": corr,
            "bonds": bcorr,
            "env": env,
            "quantum_seconds": qs,
        })
        bstr = " ".join(f"{b['i']}->{b['j']}:{b['c_at_d']:+.3f}" for b in bcorr)
        print(f"  seed {seed} gen {g:2d}  depth {depth:4d}  div {diversity:.3f}  "
              f"C0 {corr['C0']:.4f}  xi {corr['xi']:+.3f}  qpu {qs:.2f}s"
              + (f"  |  bond c(d): {bstr}" if bstr else ""))
        theta, kick = next_belief(theta, p, n)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    out_path = os.path.join(
        OUTPUT_DIR, f"{args.name}_{backend_name}_seed{seed}_{ts}_run.json")
    with open(out_path, "w") as f:
        json.dump({
            "meta": {
                "project": "QuantumTree-Research",
                "study": "entanglement-correlation",
                "variant": "swap-longrange",
                "long_range": "swap",
                "entangler": args.entangler,
                "bond_dist": args.bond_dist,
                "bonds": [list(b) for b in bonds],
                "sim_longrange": args.sim_longrange,
                "backend": backend_name,
                "sim": args.sim,
                "timestamp": ts,
                "seed": seed,
                "n_qubits": n,
                "n_ancillas": 0,
                "qubit_list": qubit_list,
                "layers": args.layers,
                "generations": args.generations,
                "shots": args.shots,
                "corr_dmax": args.corr_dmax,
                "genome_spec": spec,
                "environment": env_meta,
                "evolution": {
                    "character_lr": CHARACTER_LR, "wiggle": WIGGLE,
                    "mut_scale": MUT_SCALE, "cross_angle": CROSS_ANGLE,
                    "wind_scale": WIND_SCALE, "light_scale": LIGHT_SCALE,
                    "season_scale": SEASON_SCALE,
                },
                "total_quantum_seconds": total_qs,
                "calibration": calib,
            },
            "generations": generations,
        }, f, default=str)
    print(f"  -> {out_path}")
    return generations, out_path


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=8)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--qubits", type=str, default=None)
    ap.add_argument("--layers", type=int, default=1)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--sim-longrange", action="store_true",
                    help="ONLY with --sim: non-physical preview (never a baseline)")
    ap.add_argument("--no-auto-qubits", action="store_true")
    ap.add_argument("--entangler", choices=["brickwall", "serial"],
                    default="brickwall",
                    help="local neighbour layout; brickwall is ~50x shallower")
    ap.add_argument("--bond-dist", type=int, default=6,
                    help="slot-distance of each long-range bond (qubit dist = D*slot_bits)")
    ap.add_argument("--anchors", type=str, default="0,3,6",
                    help="source slots; each s bonds to slot s+bond_dist")
    ap.add_argument("--seed", type=int, default=0,
                    help="base seed; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--corr-dmax", type=int, default=60,
                    help="max separation d for C(d); must cover the bond distance")
    ap.add_argument("--name", type=str, default="study_swap")
    args = ap.parse_args()

    spec = GENOME_SPEC
    n = spec["n_bits"]
    ns = spec["n_slots"]

    anchors = [int(a) for a in args.anchors.split(",") if a.strip() != ""]
    bonds = resolve_bonds(anchors, args.bond_dist, ns)
    if not bonds:
        print(f"No valid bonds: anchors {anchors} + dist {args.bond_dist} "
              f"all fall outside {ns} slots.")
        sys.exit(1)
    if args.sim_longrange and not args.sim:
        print("--sim-longrange only applies with --sim; ignoring on hardware.")
        args.sim_longrange = False

    explicit = ([int(q) for q in args.qubits.split(",") if q]
                if args.qubits else None)

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
    else:
        mode = "PREVIEW (non-physical long-range)" if args.sim_longrange else "honest null"
        print(f"Backend : classical surrogate (--sim, {mode})")

    swaps = sum(2 * abs(sj - si) * spec["slot_bits"] for (si, sj) in bonds)
    print(f"Entangler: {args.entangler}   bonds (slot i->j): {bonds}   "
          f"qubit dist: {args.bond_dist * spec['slot_bits']}   "
          f"~SWAPs/gen: {swaps} (the depth cost teleport avoids)")

    if explicit is not None:
        qubit_list = explicit
    elif args.sim or args.no_auto_qubits:
        qubit_list = list(range(n))
    else:
        from layout import best_chain
        qubit_list, qstats = best_chain(backend, n)
        print(f"Auto qubit chain (live calib): {qstats}")
    if len(qubit_list) != n:
        print(f"genome is {n} qubits but {len(qubit_list)} given; must match.")
        sys.exit(1)

    per_run = []
    run_files = []
    for r in range(args.repeats):
        seed = args.seed + r
        print(f"\n=== repeat {r+1}/{args.repeats}  (seed {seed}) ===")
        gens, path = run_once(args, seed, backend, backend_name, calib,
                              qubit_list, spec, n, bonds)
        per_run.append(gens)
        run_files.append(os.path.basename(path))

    G = args.generations
    summary = []
    for g in range(G):
        divs = np.array([per_run[r][g]["diversity"] for r in range(args.repeats)])
        c0s = np.array([per_run[r][g]["correlation"]["C0"] for r in range(args.repeats)])
        xis = np.array([per_run[r][g]["correlation"]["xi"] for r in range(args.repeats)])
        depths = np.array([per_run[r][g]["logical_depth"] for r in range(args.repeats)])
        cmat = np.array([per_run[r][g]["correlation"]["c"] for r in range(args.repeats)])
        bond_means = []
        for bi in range(len(bonds)):
            vals = [per_run[r][g]["bonds"][bi]["c_at_d"] for r in range(args.repeats)]
            bond_means.append(round(float(np.mean(vals)), 6))
        summary.append({
            "gen": g,
            "diversity_mean": round(float(divs.mean()), 5),
            "diversity_std": round(float(divs.std(ddof=0)), 5),
            "C0_mean": round(float(c0s.mean()), 6),
            "C0_std": round(float(c0s.std(ddof=0)), 6),
            "xi_mean": round(float(xis.mean()), 5),
            "xi_std": round(float(xis.std(ddof=0)), 5),
            "logical_depth_mean": round(float(depths.mean()), 1),
            "bond_c_at_d_mean": bond_means,
            "c_mean": [round(x, 6) for x in cmat.mean(axis=0).tolist()],
        })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    sum_path = os.path.join(OUTPUT_DIR, f"{args.name}_{backend_name}_{ts}_summary.json")
    with open(sum_path, "w") as f:
        json.dump({
            "meta": {
                "project": "QuantumTree-Research",
                "study": "entanglement-correlation",
                "variant": "swap-longrange",
                "long_range": "swap",
                "entangler": args.entangler,
                "bond_dist": args.bond_dist,
                "bonds": [list(b) for b in bonds],
                "sim_longrange": args.sim_longrange,
                "backend": backend_name,
                "sim": args.sim,
                "base_seed": args.seed,
                "repeats": args.repeats,
                "layers": args.layers,
                "generations": G,
                "shots": args.shots,
                "corr_dmax": args.corr_dmax,
                "run_files": run_files,
            },
            "per_generation": summary,
        }, f, default=str)

    print("\n--- DONE ---")
    print(f"Long-range   : SWAP ladder  bonds {bonds}  (qubit dist {args.bond_dist*spec['slot_bits']})")
    print(f"Repeats      : {args.repeats}  (seeds {args.seed}..{args.seed+args.repeats-1})")
    depth_all = np.array([s["logical_depth_mean"] for s in summary])
    bond_all = np.array([s["bond_c_at_d_mean"] for s in summary])
    print(f"logical depth: mean {depth_all.mean():.0f}  (grows with bond distance)")
    print(f"bond c(d)    : mean {bond_all.mean():+.3f} over gens/bonds")
    print(f"Summary file : {sum_path}")
    print("Diff against research_qtree_teleport.py at matched --seed/--bond-dist: "
          "teleport should hold c(d) above noise at far lower depth.")


if __name__ == "__main__":
    main()
