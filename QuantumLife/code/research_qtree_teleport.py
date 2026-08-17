#!/usr/bin/env python3
"""
research_qtree_teleport.py -- TELEPORT-BOND research fork of research_qtree.py.

The neighbour-chain forks (research_qtree.py / research_qtree_brickwall.py) can
only imprint LOCAL structure: bond (i,i+1) means a genome slot resembles its
immediate neighbour and nothing further. Their own conclusion admits the
resulting nearest-neighbour C(1) "cannot yet be told apart from coherent-error /
crosstalk", because crosstalk ALSO only couples physical neighbours.

This fork adds a LONG-RANGE bond that crosstalk physically cannot fake: it
entangles a genome slot i with a DISTANT slot j (slot-distance --bond-dist)
through a teleported CNOT --

    Bell pair on two ancillas (a1 near slot i, a2 near slot j)
        H(a1); CX(a1, a2)
    inject slot i's parity into a1, teleport it to a2
        CX(q_i, a1); measure a1 -> m1;  if m1: X(a2)
    a2 now acts as a control adjacent to slot j
        CX(a2, q_j)
    disentangle the ancilla, feed its outcome back onto slot i
        H(a2); measure a2 -> m2;  if m2: Z(q_i)

This is the textbook long-range CNOT via ONE Bell pair + two mid-circuit
measurements + classical feed-forward (a dynamic circuit). Logically it applies
CX(q_i, q_j) at ~constant depth regardless of how far apart i and j are; on the
chip the two bonded qubits are NEVER physical neighbours, so any measured
correlation at their separation is a signature crosstalk cannot reproduce.

    q_i = slot i's angle bit (i*slot_bits + 0) -- the branch "character" qubit.

The base circuit (belief encode + local brick-wall neighbour bonds + env bias +
mutation kicks) is unchanged, so this is research_qtree_brickwall.py PLUS the
teleported long-range bonds. The C(d) metric is identical and directly
comparable; a new "bonds" block reports c(d) exactly at each teleport distance.

Baseline / honest alternative: research_qtree_swaplr.py applies the SAME
long-range CX with a SWAP ladder instead of teleportation -- correct but
O(distance) deep. Teleportation is meant to beat it at equal correlation, lower
depth. And the classical --sim surrogate remains the null (no entanglement, no
long-range term) unless --sim-longrange is passed for a non-physical preview.

Nothing here touches qtree.py, the neighbour-chain forks, runs/, or the viewer.
Output goes to QuantumLife/research_runs/.

USAGE  (see the bottom of the file / research/RUNBOOK for full recipes)
    # non-physical local PREVIEW of the intended long-range trees (no hardware)
    python research_qtree_teleport.py --sim --sim-longrange \
        --generations 8 --shots 4096 --seed 100 --repeats 3 \
        --bond-dist 6 --anchors 0,3,6 --name tel_preview

    # honest classical null (no long-range term) -- the statistical baseline
    python research_qtree_teleport.py --sim \
        --generations 8 --shots 4096 --seed 100 --repeats 3 --name tel_null

    # hardware, teleported long-range bonds (dynamic circuit)
    python research_qtree_teleport.py \
        --generations 8 --shots 4096 --seed 100 --repeats 3 --layers 1 \
        --bond-dist 6 --anchors 0,3,6 --name tel_L1_hw

OPTIONS  (superset of research_qtree_brickwall.py)
    --bond-dist D     slot-distance of each teleport bond (default 6). Qubit
                      distance is D*slot_bits. Sweep this to find the crossover.
    --anchors i,j,..  source slots for the bonds (default 0,3,6). Each anchor s
                      bonds to slot s+D; anchors with s+D >= n_slots are dropped.
    --entangler {brickwall,serial}   local neighbour layout (default brickwall).
    --sim-longrange   ONLY with --sim: inject the bond correlation classically so
                      the preview trees show the intended long-range structure.
                      NON-PHYSICAL -- never a scientific baseline; excluded from
                      the honest null. Ignored on hardware.
    ... plus every option from research_qtree_brickwall.py (--seed --repeats
        --corr-dmax --generations --shots --layers --backend --sim --qubits
        --no-auto-qubits --name).

OUTPUT
    research_runs/<TAG>_<backend|sim>_seed<K>_<ts>_run.json   per-repeat; each
        generation carries the "correlation" block (C/c/C0/xi) PLUS a "bonds"
        block: [{i, j, d_qubits, c_at_d}] -- the normalised correlation measured
        exactly at each teleport distance, and "ancillas"/"logical_depth".
    research_runs/<TAG>_<backend|sim>_<ts>_summary.json       aggregate across
        repeats: mean/std diversity, C0, xi, mean depth, and mean c_at_d per bond.
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
from pipeline_common import (connect, run_sampler, timestamp,  # noqa: E402
                            qpu_seconds, Sampler, SHOTS_PER_JOB)

from genome import GENOME_SPEC, decode_field  # noqa: E402  (local, same dir)

# separate folder so the art project's runs/ is untouched
OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))

# growth / evolution knobs (identical to the neighbour-chain forks -> results transfer)
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


# ---------------------------------------------------------------------------
# bonds: which slot pairs get a long-range teleport link
# ---------------------------------------------------------------------------
def resolve_bonds(anchors: list[int], dist: int, n_slots: int) -> list[tuple[int, int]]:
    """Each anchor slot s bonds to slot s+dist; drop pairs off the register."""
    bonds = []
    for s in anchors:
        t = s + dist
        if 0 <= s < n_slots and 0 <= t < n_slots and s != t:
            bonds.append((s, t))
    return bonds


# ---------------------------------------------------------------------------
# circuit  (base = brick-wall neighbour chain + teleported long-range bonds)
# ---------------------------------------------------------------------------
def _entangle(qc: QuantumCircuit, n: int, mode: str) -> None:
    """One CX sweep + one CRX sweep over every open-chain neighbour bond.

    serial     : bonds 0..n-2 in order (adjacent gates share a qubit -> ~n-1 deep).
    brickwall  : even bonds together, then odd bonds together -> depth 2 per sweep.
    Same bonds either way; brick-wall is ~50x shallower and is the default."""
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


def _teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True) -> None:
    """Long-range CNOT(ctrl -> tgt) via one Bell pair + two mid-circuit measures.

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


def build_circuit(theta, kick, env, layers, spec, entangler,
                  bonds, herald=False) -> QuantumCircuit:
    n = spec["n_bits"]
    sb, ns = spec["slot_bits"], spec["n_slots"]
    nb = len(bonds)
    qr = QuantumRegister(n, "q")
    anc = QuantumRegister(2 * nb, "a") if nb else None
    cr = ClassicalRegister(n, "c")             # genome -- the only creg run_sampler reads
    tel = ClassicalRegister(2 * nb, "tel") if nb else None  # feed-forward scratch
    regs = [qr] + ([anc] if anc else []) + [cr] + ([tel] if tel else [])
    qc = QuantumCircuit(*regs)

    # 1. belief encode
    for i in range(n):
        qc.ry(theta[i], i)

    # 2. local correlation -- `layers` neighbour entangling layers
    for _ in range(max(1, layers)):
        _entangle(qc, n, entangler)

    # 3. long-range correlation -- teleported CX between distant slots' angle bits
    for k, (si, sj) in enumerate(bonds):
        qi, qj = si * sb, sj * sb          # angle bit 0 = the branch "character"
        a1, a2 = anc[2 * k], anc[2 * k + 1]
        _teleport_cx(qc, qr[qi], qr[qj], a1, a2, tel, k,
                     feedforward=not herald)

    # 4. environment bias per slot
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

    # 5. self-mutation kicks
    for i in range(n):
        if kick[i]:
            qc.rx(kick[i], i)

    # 6. collapse the genome (only "c" is fetched downstream)
    qc.measure(qr, cr)
    return qc


# ---------------------------------------------------------------------------
# statistics  (identical to the neighbour-chain forks -> numbers comparable)
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
    """Connected two-point correlation of the measured genome chain.

        C(d) = mean_i [ <b_i b_{i+d}> - <b_i><b_{i+d}> ]   c(d)=C(d)/C(0)
        xi   = sum_{d>=1} c(d)

    C(d)==0 for d>0 is the independent-qubit (surrogate) null. The neighbour
    chain lifts only small d; the headline of THIS fork is a nonzero c(d) at the
    teleport distance d = D*slot_bits, where the chain term has already decayed
    to ~0 and crosstalk cannot reach."""
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
    """Direct connected correlation between the two bonded angle qubits of each
    pair -- the crosstalk-immune long-range term, measured at the exact qubits."""
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
def run_sim(theta, kick, env, n, shots, spec, bonds, sim_longrange, herald):
    """Classical surrogate. Default = the honest null: NO entanglement, so
    C(d)~0 for d>0 and c_at_d~0 at every bond. With --sim-longrange it also
    copies each source slot's angle parity into its target slot (NON-PHYSICAL)
    so the preview trees show the long-range structure the hardware is meant to
    grow -- never use that mode as a statistical baseline.

    With --herald it also emits per-shot tel bits (uniform random, as the real
    ancilla outcomes are) and, in the preview, applies the echo ONLY on the
    tel==00 branch -- exactly what heralded teleport does. Post-selecting tel==00
    then recovers the clean correlation, while the NULL stays ~0 (the echo never
    fired), demonstrating the herald does not fabricate signal."""
    sb = spec["slot_bits"]
    nb = len(bonds)
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
    tel_out = [] if herald else None
    for _ in range(shots):
        bits = ["1" if random.random() < sm[i] else "0" for i in range(n)]
        if herald:
            telbits = ["1" if random.random() < 0.5 else "0" for _ in range(2 * nb)]
            clean = all(t == "0" for t in telbits)   # tel==00 branch
            if sim_longrange and clean:              # echo only on the clean branch
                for (si, sj) in bonds:
                    qi, qj = si * sb, sj * sb
                    if random.random() < 0.85:
                        bits[qj] = bits[qi]
            tel_out.append("".join(telbits))
        elif sim_longrange:
            for (si, sj) in bonds:           # copy source angle parity -> target
                qi, qj = si * sb, sj * sb
                if random.random() < 0.85:   # imperfect echo, mimics link fidelity
                    bits[qj] = bits[qi]
        out.append("".join(bits))
    return out, tel_out, 0.0


def run_hw(backend, qc, qubit_list, shots, want_tel):
    """Chunked SamplerV2 loop reading BOTH cregs: 'c' (genome) and, when
    heralding, 'tel' (feed-forward outcomes) so shots can be post-selected.
    Mirrors pipeline_common.run_sampler but returns the tel register too."""
    # ancillas mean qc has more qubits than the auto chain; only pin the layout
    # when it matches exactly, else let opt-level-3 route the dynamic circuit.
    init = qubit_list if (qubit_list and len(qubit_list) == qc.num_qubits) else None
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                      initial_layout=init)
    isa = pm.run(qc)
    sampler = Sampler(mode=backend)
    genome, tel = [], ([] if want_tel else None)
    total_qs = 0.0
    remaining, ci = shots, 0
    while remaining > 0:
        chunk = min(SHOTS_PER_JOB, remaining)
        ci += 1
        job = sampler.run([isa], shots=chunk)
        print(f"  job {ci}: {job.job_id()} ({chunk:,} shots) ...", end="", flush=True)
        res = job.result()
        genome.extend(s[::-1] for s in res[0].data.c.get_bitstrings())
        if want_tel:
            tel.extend(res[0].data.tel.get_bitstrings())
        qs = qpu_seconds(job)
        total_qs += 0.0 if math.isnan(qs) else qs
        print(f" done (qpu {qs:.2f}s)")
        remaining -= chunk
    return genome, tel, total_qs


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
                           args.entangler, bonds, herald=args.herald)
        depth = qc.depth()
        n_anc = 2 * len(bonds)
        if args.sim:
            fields, tel, qs = run_sim(theta, kick, env, n, args.shots, spec,
                                      bonds, args.sim_longrange, args.herald)
        else:
            fields, tel, qs = run_hw(backend, qc, qubit_list, args.shots,
                                     want_tel=args.herald)
        total_qs += qs

        # heralded post-selection: keep only the tel==00 (correctly-teleported)
        # branch. Uses ancilla outcomes ONLY -- never the genome bits -- so it is
        # a valid noise filter, not selection bias on the measured quantity.
        n_total = len(fields)
        if args.herald and tel is not None:
            kept = [f for f, t in zip(fields, tel) if set(t) <= {"0"}]
            herald_frac = round(len(kept) / n_total, 4) if n_total else 0.0
            if len(kept) < 32:
                print(f"  seed {seed} gen {g:2d}  HERALD kept only {len(kept)}"
                      f"/{n_total} shots -- too few; use fewer bonds or more shots.")
            fields_used = kept if kept else fields
        else:
            herald_frac = 1.0
            fields_used = fields

        p, modal, samples, diversity = field_stats(fields_used, n)
        corr = two_point_correlation(fields_used, n, args.corr_dmax)
        bcorr = bond_correlations(fields_used, n, bonds, sb)
        generations.append({
            "gen": g,
            "logical_depth": depth,
            "ancillas": n_anc,
            "shots": args.shots,
            "herald": args.herald,
            "herald_kept": len(fields_used) if args.herald else n_total,
            "herald_frac": herald_frac,
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
        hstr = f"  herald {herald_frac*100:.1f}% kept" if args.herald else ""
        print(f"  seed {seed} gen {g:2d}  depth {depth:4d}  div {diversity:.3f}  "
              f"C0 {corr['C0']:.4f}  xi {corr['xi']:+.3f}  qpu {qs:.2f}s{hstr}"
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
                "variant": "teleport-longrange",
                "long_range": "teleport",
                "entangler": args.entangler,
                "bond_dist": args.bond_dist,
                "bonds": [list(b) for b in bonds],
                "sim_longrange": args.sim_longrange,
                "herald": args.herald,
                "backend": backend_name,
                "sim": args.sim,
                "timestamp": ts,
                "seed": seed,
                "n_qubits": n,
                "n_ancillas": 2 * len(bonds),
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
                    help="ONLY with --sim: non-physical preview of the "
                         "long-range structure (never a baseline)")
    ap.add_argument("--herald", action="store_true",
                    help="heralded teleport: drop feed-forward, post-select the "
                         "tel==00 branch (valid noise filter). Keeps ~4^-nbonds "
                         "of shots -- use 1-2 bonds and raise --shots.")
    ap.add_argument("--no-auto-qubits", action="store_true")
    ap.add_argument("--entangler", choices=["brickwall", "serial"],
                    default="brickwall",
                    help="local neighbour layout; brickwall is ~50x shallower")
    ap.add_argument("--bond-dist", type=int, default=6,
                    help="slot-distance of each teleport bond (qubit dist = D*slot_bits)")
    ap.add_argument("--anchors", type=str, default="0,3,6",
                    help="source slots; each s bonds to slot s+bond_dist")
    ap.add_argument("--seed", type=int, default=0,
                    help="base seed; repeat r uses seed+r")
    ap.add_argument("--repeats", type=int, default=1,
                    help="independent seeded runs for statistics")
    ap.add_argument("--corr-dmax", type=int, default=60,
                    help="max separation d for C(d); must cover the bond distance")
    ap.add_argument("--name", type=str, default="study_tel")
    args = ap.parse_args()

    spec = GENOME_SPEC
    n = spec["n_bits"]
    ns = spec["n_slots"]

    anchors = [int(a) for a in args.anchors.split(",") if a.strip() != ""]
    bonds = resolve_bonds(anchors, args.bond_dist, ns)
    if not bonds:
        print(f"No valid bonds: anchors {anchors} + dist {args.bond_dist} "
              f"all fall outside {ns} slots. Nothing long-range to teleport.")
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

    print(f"Entangler: {args.entangler}   bonds (slot i->j): {bonds}   "
          f"qubit dist: {args.bond_dist * spec['slot_bits']}   "
          f"ancillas: {2 * len(bonds)}")
    if args.herald:
        exp_frac = 0.25 ** len(bonds)
        print(f"Herald   : ON (no feed-forward, post-select tel==00). "
              f"Expected kept ~{exp_frac*100:.2f}% -> ~{int(args.shots*exp_frac)} "
              f"of {args.shots} shots/gen.")
        if exp_frac * args.shots < 200:
            print("           WARNING: <200 shots survive/gen -> noisy c(d). "
                  "Reduce bonds (--anchors) or raise --shots.")

    if explicit is not None:
        qubit_list = explicit
    elif args.sim or args.no_auto_qubits:
        qubit_list = list(range(n))
    else:
        from layout import best_chain
        qubit_list, qstats = best_chain(backend, n)
        print(f"Auto qubit chain (live calib): {qstats}")
        print("Note: teleport adds ancillas beyond the chain; the transpiler "
              "routes them (initial_layout left unpinned).")

    # -- repeats --------------------------------------------------------------
    per_run = []
    run_files = []
    for r in range(args.repeats):
        seed = args.seed + r
        print(f"\n=== repeat {r+1}/{args.repeats}  (seed {seed}) ===")
        gens, path = run_once(args, seed, backend, backend_name, calib,
                              qubit_list, spec, n, bonds)
        per_run.append(gens)
        run_files.append(os.path.basename(path))

    # -- aggregate across repeats, per generation -----------------------------
    G = args.generations
    summary = []
    for g in range(G):
        divs = np.array([per_run[r][g]["diversity"] for r in range(args.repeats)])
        c0s = np.array([per_run[r][g]["correlation"]["C0"] for r in range(args.repeats)])
        xis = np.array([per_run[r][g]["correlation"]["xi"] for r in range(args.repeats)])
        depths = np.array([per_run[r][g]["logical_depth"] for r in range(args.repeats)])
        cmat = np.array([per_run[r][g]["correlation"]["c"] for r in range(args.repeats)])
        # mean c_at_d per bond, in the fixed bond order
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
                "variant": "teleport-longrange",
                "long_range": "teleport",
                "entangler": args.entangler,
                "bond_dist": args.bond_dist,
                "bonds": [list(b) for b in bonds],
                "sim_longrange": args.sim_longrange,
                "herald": args.herald,
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
    print(f"Long-range   : teleport  bonds {bonds}  (qubit dist {args.bond_dist*spec['slot_bits']})")
    print(f"Repeats      : {args.repeats}  (seeds {args.seed}..{args.seed+args.repeats-1})")
    depth_all = np.array([s["logical_depth_mean"] for s in summary])
    bond_all = np.array([s["bond_c_at_d_mean"] for s in summary])  # G x nbonds
    print(f"logical depth: mean {depth_all.mean():.0f}  (teleport bond is ~constant depth)")
    print(f"bond c(d)    : mean {bond_all.mean():+.3f} over gens/bonds "
          f"(near 0 => no long-range signal above noise)")
    print(f"Summary file : {sum_path}")
    print("Compare against research_qtree_swaplr.py (same bonds, SWAP ladder) at "
          "matched --seed/--bond-dist, and against the --sim null.")


if __name__ == "__main__":
    main()
