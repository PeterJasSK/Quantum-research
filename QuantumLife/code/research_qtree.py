#!/usr/bin/env python3
"""
research_qtree.py -- RESEARCH fork of qtree.py.

Same growth circuit as the art project, but instrumented for a measurable
question instead of a pretty picture:

    Does the hardware entangling chain (CX + controlled-Rx between neighbours)
    imprint spatial structure on the measured genome that the classical,
    NO-entanglement surrogate (--sim) cannot reproduce?

The art viewer only ever saw a per-qubit diversity number, which is blind to
correlation between qubits. This fork adds the quantity that actually sees
entanglement:

    two-point connected correlation   C(d) = <b_i b_{i+d}> - <b_i><b_{i+d}>
    normalised                         c(d) = C(d) / C(0)
    integrated correlation length      xi   = sum_{d>=1} c(d)

and repeats each run --repeats times with deterministic seeds so the numbers
carry a mean +/- std and can be fed to a two-sample test (sim vs hardware)
later.

Nothing here touches the original qtree.py, its runs/ folder, or the web
viewer. Output goes to QuantumLife/research_runs/.

See QuantumLife/research/STUDY_ENTANGLEMENT_CORRELATION.md for the full study
design, hypotheses, and expected outcomes.

USAGE
    # classical baseline (no entanglement), 5 seeded repeats
    python research_qtree.py --sim --generations 14 --shots 4096 \
        --seed 100 --repeats 5 --name baseline

    # hardware, matched settings and seeds
    python research_qtree.py --generations 14 --shots 4096 \
        --seed 100 --repeats 5 --layers 2 --name hw

OPTIONS  (superset of qtree.py)
    --seed N          base RNG seed. Repeat r uses seed N+r, so sim and hw runs
                      launched with the same --seed see the SAME environment
                      schedule -> a paired comparison.
    --repeats R       independent seeded runs (default 1). Enables statistics.
    --corr-dmax D     max separation d for C(d) (default 30, capped at n-1).
    ... plus every option from qtree.py (--generations --shots --layers
        --backend --sim --qubits --no-auto-qubits --name).

OUTPUT
    research_runs/<TAG>_<backend|sim>_seed<K>_<ts>_run.json   per-repeat, with a
        "correlation" block per generation (C(d), c(d), C0, xi).
    research_runs/<TAG>_<backend|sim>_<ts>_summary.json       aggregate across
        repeats: mean/std of diversity, C0 and xi per generation.
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
_HERE = os.path.dirname(os.path.abspath(__file__))
_CALIB_CODE = os.path.normpath(
    os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG", "code")
)
sys.path.insert(0, _CALIB_CODE)
from pipeline_common import connect, run_sampler, timestamp  # noqa: E402

from genome import GENOME_SPEC, decode_field  # noqa: E402  (local, same dir)

# separate folder so the art project's runs/ is untouched
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# growth / evolution knobs (kept identical to qtree.py so results transfer) ----
CHARACTER_LR = 0.18   # how hard belief reinforces the growth habit it measured
WIGGLE = 0.05         # organic per-generation jitter in belief
MUT_SCALE = 0.30      # self-mutation Rx kick from previous generation's bits
CROSS_ANGLE = 0.7     # controlled-Rx neighbour correlation angle
WIND_SCALE = 0.4      # wind gust -> Rx on angle bits
LIGHT_SCALE = 0.5     # phototropism, steady lean toward the light side
SEASON_SCALE = 0.9    # season -> Ry on length/fork bits
FORK_BIAS = 0.3
LEAF_BIAS = 0.45
THETA_LO, THETA_HI = 0.08, math.pi - 0.08


# ---------------------------------------------------------------------------
# per-run environment schedule (seeded per repeat)
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


# ---------------------------------------------------------------------------
# circuit  (identical topology to qtree.py)
# ---------------------------------------------------------------------------
def build_circuit(theta: list[float], kick: list[float], env: dict,
                  layers: int, spec: dict) -> QuantumCircuit:
    n = spec["n_bits"]
    sb, ns = spec["slot_bits"], spec["n_slots"]
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)

    for i in range(n):
        qc.ry(theta[i], i)

    for _ in range(max(1, layers)):
        for i in range(n - 1):
            qc.cx(i, i + 1)
        for i in range(n - 1):
            qc.crx(CROSS_ANGLE, i, i + 1)

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

    qc.measure(range(n), range(n))
    return qc


# ---------------------------------------------------------------------------
# statistics
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
    """Connected two-point correlation of the measured bit chain.

        C(d) = mean_i [ <b_i b_{i+d}> - <b_i><b_{i+d}> ]        (open chain)
        c(d) = C(d) / C(0)                                       (normalised)
        xi   = sum_{d>=1} c(d)                                   (integrated length)

    C(d)==0 for all d>0 is the signature of independent (product-state /
    classical surrogate) qubits. A nonzero, distance-decaying C(d) is the
    fingerprint of the entangling chain (up to what device noise leaves intact).

    Returns C(0..dmax), c(0..dmax), and xi. Uses numpy; the raw shot matrix
    stays local and never leaves this function."""
    dmax = min(dmax, n - 1)
    # (shots x n) matrix of 0/1
    M = np.frombuffer("".join(fields).encode(), dtype=np.uint8).reshape(len(fields), n)
    M = (M - ord("0")).astype(np.float64)          # '0'->0.0, '1'->1.0
    p = M.mean(axis=0)                              # per-qubit P(bit=1)
    C0 = float(np.mean(p * (1.0 - p)))             # C(d=0) = mean variance
    C = [C0]
    for d in range(1, dmax + 1):
        joint = (M[:, : n - d] * M[:, d:]).mean(axis=0)   # <b_i b_{i+d}>
        conn = joint - p[: n - d] * p[d:]                 # connected, per i
        C.append(float(conn.mean()))
    c = [ci / C0 if C0 > 1e-12 else 0.0 for ci in C]
    xi = float(sum(c[1:]))                          # integrated correlation length
    return {"C": [round(x, 6) for x in C],
            "c": [round(x, 6) for x in c],
            "C0": round(C0, 6),
            "xi": round(xi, 5),
            "dmax": dmax}


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
def run_sim(theta, kick, env, n, shots, spec):
    """Classical surrogate. NO entanglement -> expect C(d)~0 for d>0 (the null
    model this whole study tests hardware against)."""
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
    out = ["".join("1" if random.random() < sm[i] else "0" for i in range(n))
           for _ in range(shots)]
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
def run_once(args, seed, backend, backend_name, calib, qubit_list, spec, n):
    random.seed(seed)
    env_sched, env_meta = build_env(args.generations)

    theta = [math.pi / 2] * n
    kick = [0.0] * n
    generations: list[dict[str, Any]] = []
    total_qs = 0.0

    for g in range(args.generations):
        env = env_sched[g]
        qc = build_circuit(theta, kick, env, args.layers, spec)
        depth = qc.depth()
        if args.sim:
            fields, qs = run_sim(theta, kick, env, n, args.shots, spec)
        else:
            fields, qs = run_hw(backend, qc, qubit_list, args.shots)
        total_qs += qs

        p, modal, samples, diversity = field_stats(fields, n)
        corr = two_point_correlation(fields, n, args.corr_dmax)
        generations.append({
            "gen": g,
            "logical_depth": depth,
            "shots": args.shots,
            "bits": modal,
            "samples": samples,
            "p": [round(x, 5) for x in p],
            "diversity": round(diversity, 5),
            "correlation": corr,
            "env": env,
            "quantum_seconds": qs,
        })
        print(f"  seed {seed} gen {g:2d}  div {diversity:.3f}  "
              f"C0 {corr['C0']:.4f}  xi {corr['xi']:+.3f}  qpu {qs:.2f}s")
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
                "backend": backend_name,
                "sim": args.sim,
                "timestamp": ts,
                "seed": seed,
                "n_qubits": n,
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
    ap.add_argument("--generations", type=int, default=14)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--qubits", type=str, default=None)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--no-auto-qubits", action="store_true")
    ap.add_argument("--seed", type=int, default=0,
                    help="base seed; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=1,
                    help="independent seeded runs for statistics")
    ap.add_argument("--corr-dmax", type=int, default=30,
                    help="max separation d for the C(d) correlation metric")
    ap.add_argument("--name", type=str, default="study")
    args = ap.parse_args()

    spec = GENOME_SPEC
    n = spec["n_bits"]
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
        print("Backend : classical surrogate (--sim, no entanglement, no cost)")

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

    # -- repeats --------------------------------------------------------------
    per_run = []
    run_files = []
    for r in range(args.repeats):
        seed = args.seed + r
        print(f"\n=== repeat {r+1}/{args.repeats}  (seed {seed}) ===")
        gens, path = run_once(args, seed, backend, backend_name, calib,
                              qubit_list, spec, n)
        per_run.append(gens)
        run_files.append(os.path.basename(path))

    # -- aggregate across repeats, per generation -----------------------------
    G = args.generations
    summary = []
    for g in range(G):
        divs = np.array([per_run[r][g]["diversity"] for r in range(args.repeats)])
        c0s = np.array([per_run[r][g]["correlation"]["C0"] for r in range(args.repeats)])
        xis = np.array([per_run[r][g]["correlation"]["xi"] for r in range(args.repeats)])
        # mean normalised c(d) curve across repeats
        cmat = np.array([per_run[r][g]["correlation"]["c"] for r in range(args.repeats)])
        summary.append({
            "gen": g,
            "diversity_mean": round(float(divs.mean()), 5),
            "diversity_std": round(float(divs.std(ddof=0)), 5),
            "C0_mean": round(float(c0s.mean()), 6),
            "C0_std": round(float(c0s.std(ddof=0)), 6),
            "xi_mean": round(float(xis.mean()), 5),
            "xi_std": round(float(xis.std(ddof=0)), 5),
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
    print(f"Repeats      : {args.repeats}  (seeds {args.seed}..{args.seed+args.repeats-1})")
    xi_all = np.array([s["xi_mean"] for s in summary])
    print(f"xi over gens : mean {xi_all.mean():+.3f}  (near 0 => no correlation)")
    print(f"Summary file : {sum_path}")
    print("Compare a --sim summary against a hardware summary at the same "
          "--seed/--repeats to test the hypothesis.")


if __name__ == "__main__":
    main()
