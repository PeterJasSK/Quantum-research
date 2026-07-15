#!/usr/bin/env python3
"""
qtree.py — Quantum Tree: a hardware-grown tree you watch come to life. Pure-fun
project, no paper, no metrics, no target.

One generation = one growth step = one real hardware circuit on Heron r2, using
a 108-qubit register (18 branch-slots x 6 bits) laid out as a SWAP-free chain
(a full 120-qubit simple path does not exist on Heron's heavy-hex). The chip
does real work every generation:

    1. belief encode : Ry(theta_i) on all 108 qubits  (the tree's growth belief)
    2. correlation   : `--layers` entangling layers (CX open chain + controlled-
                       Rx between neighbouring qubits) -- this is what makes near
                       branches RESEMBLE each other, i.e. natural clustering
                       instead of white-noise jitter. More layers = more
                       correlated + more of the chip used.
    3. environment   : classical bias angles injected as rotations --
                         wind + light -> Rx on the angle bits  (branches lean)
                         season       -> Ry on length/fork bits (good year =
                                          longer, more forks; dry year = sparse)
    4. self-mutation : Rx(kick_i) from the PREVIOUS generation's measured bits
    5. measure       : collapse all 120 -> one field of branch decisions/shot

Between generations the belief REINFORCES what it measured (CHARACTER_LR) plus a
small organic wiggle: the tree's branching "character" crystallises as it
matures, but individual branches stay noisy. Environment is regenerated randomly
per run (wind direction/gusts, a season cycle, a light side), so every run grows
a different, natural-looking tree. On hardware the device's own noise is the
final source of uniqueness.

Every generation records one representative measured field + a few alternates
(shimmer), per-qubit statistics, and that generation's environment, to
runs/<name>_run.json -- which web/quantum_tree.html replays as a tree growing
from a seed.

USAGE
    # local test, zero cost -- classical surrogate (NO true entanglement; just
    # proves the pipeline + feeds the viewer). 120 qubits can't be statevector-
    # simulated, so --sim samples per-qubit belief with neighbour smoothing:
    python qtree.py --sim --generations 14 --shots 2048

    # real hardware (real entanglement -> real correlation):
    python qtree.py --generations 14 --shots 2048 --backend ibm_fez
    python qtree.py --generations 14 --shots 2048          # auto least-busy Heron r2

OPTIONS
    --generations G   growth steps (tree depth)                  (default 14)
    --shots S         shots per generation                       (default 2048)
    --layers L        correlation entangling layers -> raise for
                      MORE correlated, more chip used            (default 3)
    --qubits a,b,..   physical qubits (default 0..N-1, N=120 from genome spec)
    --backend NAME    e.g. ibm_fez; omit to auto-pick least-busy Heron r2
    --sim             classical surrogate, no IBM cost, no entanglement
    --seed N          seed the per-run environment RNG (omit = different tree
                      every run)
    --name TAG        output filename tag                         (default "tree")

OUTPUT
    runs/<TAG>_<backend|sim>_<ts>_run.json   full growth, fed to the web viewer
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

OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "runs"))

# growth / evolution knobs -----------------------------------------------------
CHARACTER_LR = 0.18   # how hard belief reinforces the growth habit it measured
WIGGLE = 0.05         # organic per-generation jitter in belief
MUT_SCALE = 0.30      # self-mutation Rx kick from previous generation's bits
CROSS_ANGLE = 0.7     # controlled-Rx neighbour correlation angle
# environment strengths (how hard each factor bends the growth)
WIND_SCALE = 0.9      # wind gust -> Rx on angle bits
LIGHT_SCALE = 0.5     # phototropism, steady lean toward the light side
SEASON_SCALE = 0.9    # season -> Ry on length/fork bits
# constant growth biases (steady Ry toward |1>): branch more, leaf more, and --
# together with MAXDEPTH-only termination in the viewer -- rarely die.
FORK_BIAS = 0.3       # gentle push on the fork bit (viewer spaces forks out)
LEAF_BIAS = 0.45      # push the leaf bit ON  -> plenty of green leaf clusters
THETA_LO, THETA_HI = 0.08, math.pi - 0.08


# ---------------------------------------------------------------------------
# per-run environment schedule (random per run + a season cycle)
# ---------------------------------------------------------------------------
def build_env(generations: int) -> tuple[list[dict], dict]:
    period = random.randint(6, 12)                 # length of a season cycle
    phase = random.uniform(0, 2 * math.pi)
    wind_period = random.randint(4, 9)             # how fast the wind swings
    wind_phase = random.uniform(0, 2 * math.pi)
    wind_prevail = random.uniform(-0.2, 0.2)       # tiny prevailing drift only
    light_side = random.choice([-1.0, 1.0])        # sun is to the left / right
    light_str = random.uniform(0.15, 0.35)         # gentle steady lean to light

    env = []
    for g in range(generations):
        season = 0.5 + 0.5 * math.sin(2 * math.pi * g / period + phase)  # 0 dry..1 good
        # wind SWINGS around zero -> gusts both directions, no permanent lean
        gust = (wind_prevail
                + 0.6 * math.sin(2 * math.pi * g / wind_period + wind_phase)
                + random.uniform(-0.15, 0.15))
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
# circuit
# ---------------------------------------------------------------------------
def build_circuit(theta: list[float], kick: list[float], env: dict,
                  layers: int, spec: dict) -> QuantumCircuit:
    n = spec["n_bits"]
    sb, ns = spec["slot_bits"], spec["n_slots"]
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")   # name 'c' required by pipeline_common.run_sampler
    qc = QuantumCircuit(qr, cr)

    # 1. belief encode
    for i in range(n):
        qc.ry(theta[i], i)

    # 2. correlation -- neighbour entangling OPEN chain, repeated `layers` times.
    # Open (no wrap) so it maps to a physical qubit chain with zero SWAPs; see
    # layout.best_chain, which picks such a chain from live calibration.
    for _ in range(max(1, layers)):
        for i in range(n - 1):
            qc.cx(i, i + 1)
        for i in range(n - 1):
            qc.crx(CROSS_ANGLE, i, i + 1)

    # 3. environment bias per slot
    ab, sbias = env["angle_bias"], env["season_bias"]
    for s in range(ns):
        base = s * sb
        qc.rx(ab, base + 0)          # wind + light on the two angle bits
        qc.rx(ab, base + 1)
        qc.ry(sbias, base + 2)       # season on length bits + fork bit
        qc.ry(sbias, base + 3)
        qc.ry(sbias, base + 4)
        qc.ry(FORK_BIAS, base + 4)   # steady push: branch more
        qc.ry(LEAF_BIAS, base + 5)   # steady push: more green leaves

    # 4. self-mutation kicks (from previous generation's measured bits)
    for i in range(n):
        if kick[i]:
            qc.rx(kick[i], i)

    # 5. collapse
    qc.measure(range(n), range(n))
    return qc


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------
def _binH(x: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def field_stats(fields: list[str], n: int) -> tuple[list[float], str, list[str], float]:
    """fields: genome-ordered bitstrings. Returns (per-qubit p, representative
    field, up-to-4 alternate fields for shimmer, diversity).

    diversity = mean per-qubit binary entropy -> bounded in [0,1] and stays
    meaningful at 120 qubits (unlike whole-string entropy, which pins at max)."""
    shots = len(fields)
    p = [sum(1 for f in fields if f[i] == "1") / shots for i in range(n)]
    counts = Counter(fields)
    modal = counts.most_common(1)[0][0]
    samples = [b for b, _ in counts.most_common() if b != modal][:4]
    diversity = sum(_binH(pi) for pi in p) / n
    return p, modal, samples, diversity


def next_belief(theta: list[float], p: list[float], n: int
                ) -> tuple[list[float], list[float]]:
    """Reinforce the measured growth habit (character crystallises), plus a
    small organic wiggle. Returns (theta_next, kick_next)."""
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
def run_sim(theta: list[float], kick: list[float], env: dict, n: int,
            shots: int, spec: dict) -> tuple[list[str], float]:
    """Classical surrogate -- 108 qubits can't be statevector-simulated. Samples
    each qubit from its belief+bias probability, with light neighbour smoothing
    to fake the correlation. NO true entanglement; pipeline/viewer test only."""
    sb = spec["slot_bits"]
    base = []
    for i in range(n):
        a = theta[i] + kick[i]
        local = i % sb
        if local in (0, 1):
            a += env["angle_bias"] * 0.5       # wind/light lean on angle bits
        if local == 4:
            a += FORK_BIAS                     # branch more
        if local == 5:
            a += LEAF_BIAS                     # more green leaves
        p1 = math.sin(a / 2) ** 2
        if local in (2, 3, 4):                 # season push on length/fork bits
            p1 += 0.25 * env["season_bias"]
        base.append(min(0.98, max(0.02, p1)))
    sm = [0.7 * base[i] + 0.15 * base[(i - 1) % n] + 0.15 * base[(i + 1) % n]
          for i in range(n)]
    out = ["".join("1" if random.random() < sm[i] else "0" for i in range(n))
           for _ in range(shots)]
    return out, 0.0


def run_hw(backend: Any, qc: QuantumCircuit, qubit_list: list[int], shots: int
           ) -> tuple[list[str], float]:
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=qubit_list)
    isa = pm.run(qc)
    raw_meas, _jobs, qs = run_sampler(backend, isa, shots)
    # qiskit creg strings are MSB-first; reverse so index i == qubit i == gene i
    return [s[::-1] for s in raw_meas], qs


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=14)
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--qubits", type=str, default=None)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--backend", type=str, default=None)
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--no-auto-qubits", action="store_true",
                    help="disable live-calibration chain picking (use 0..N-1)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--name", type=str, default="tree")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

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

    # pick the physical qubit chain
    if explicit is not None:
        qubit_list = explicit
    elif args.sim or args.no_auto_qubits:
        qubit_list = list(range(n))
    else:
        # auto: longest low-error SWAP-free chain from LIVE calibration (free)
        from layout import best_chain
        qubit_list, qstats = best_chain(backend, n)
        print(f"Auto qubit chain (live calib): {qstats}")
        print(f"  qubits: {qubit_list}")
    if len(qubit_list) != n:
        print(f"genome is {n} qubits but {len(qubit_list)} given; must match.")
        sys.exit(1)

    env_sched, env_meta = build_env(args.generations)

    # seed belief: every gene a full coin (max superposition) -> the tree's
    # character is undecided at the seed, then crystallises as it grows.
    theta = [math.pi / 2] * n
    kick = [0.0] * n

    generations: list[dict[str, Any]] = []
    total_qs = 0.0

    for g in range(args.generations):
        env = env_sched[g]
        qc = build_circuit(theta, kick, env, args.layers, spec)
        depth = qc.depth()
        print(f"\n--- growth step {g}  (logical depth {depth}, "
              f"season {env['season']:.2f}, wind {env['wind']:+.2f}) ---")
        if args.sim:
            fields, qs = run_sim(theta, kick, env, n, args.shots, spec)
        else:
            fields, qs = run_hw(backend, qc, qubit_list, args.shots)
        total_qs += qs

        p, modal, samples, diversity = field_stats(fields, n)
        generations.append({
            "gen": g,
            "theta": [round(t, 5) for t in theta],
            "logical_depth": depth,
            "shots": args.shots,
            "bits": modal,             # representative measured field this step
            "samples": samples,        # alternates -> viewer shimmer
            "p": [round(x, 5) for x in p],
            "diversity": round(diversity, 5),
            "env": env,
            "quantum_seconds": qs,
        })
        n_leaf = sum(1 for s in range(spec["n_slots"])
                     if modal[s * spec["slot_bits"] + 5] == "1")
        print(f"  diversity {diversity:.3f}  leaf-slots {n_leaf}/{spec['n_slots']}"
              f"  qpu {qs:.2f}s")

        theta, kick = next_belief(theta, p, n)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = timestamp()
    out_path = os.path.join(OUTPUT_DIR, f"{args.name}_{backend_name}_{ts}_run.json")
    with open(out_path, "w") as f:
        json.dump({
            "meta": {
                "project": "QuantumTree",
                "backend": backend_name,
                "sim": args.sim,
                "timestamp": ts,
                "n_qubits": n,
                "qubit_list": qubit_list,
                "layers": args.layers,
                "generations": args.generations,
                "shots": args.shots,
                "seed": args.seed,
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

    print("\n--- DONE ---")
    print(f"Growth steps : {args.generations}")
    print(f"QPU seconds  : {total_qs:.2f}")
    print(f"Run file     : {out_path}")
    print("Load that file in QuantumLife/web/quantum_tree.html to watch it grow.")


if __name__ == "__main__":
    main()
