"""M13 pair_layer, M14 pauli_estimator and the R3 runners: Pauli-channel learning with a sister memory (L1'-L).

Each selected pair (founder f, sister s) is a Bell pair; the channel acts on the founder halves; a Bell measurement
of every pair then reads which Pauli hit each founder, so ONE shot gives a sample of every Pauli eigenvalue at once.

`programmed` channel (R3-LADDER, R3-CHIP64): a hidden full-weight Pauli P and a hidden sign s. Each circuit instance
applies a random Pauli string Q, uniform over the strings with <Q, P> = s, so the channel has eigenvalue (-1)^s on P
and 0 on every other non-identity Pauli. The learner estimates lambda(P) = mean of (-1)^<P, Q_measured>; with noise
it is (-1)^s r^n, r = per-pair signal. Fitted per-qubit sample overhead = 1 / r^2, against the memoryless bound
(2 per qubit [verify, gap G3]). Pairs are selected by forecast signal (plan X9: a few bad pairs kill a full-weight
Pauli). No memoryless arm is run: the limit is a theorem, an arm would be an illustration (X10).

Hypothesis test (R3-TEST): the task of Seif et al. 2408.03376 Sec. III. Alice draws a uniform non-identity Pauli P
on n founders, a sign, and a fair coin: the channel is fully depolarising (every eigenvalue 0) or has eigenvalue
+-1/3 on P and 0 elsewhere. Bob measures, is then told P (not the sign) and names the channel. Without a quantum
memory p_success <= 1/2 + 0.43 M 2^-n for M measurements (their Eq. 4, from Chen et al. PRL 132, 180805) [verify].
With the sister memory Bob estimates lambda(P) and answers "+-1/3" when |lambda| > F / 6, F = the same estimate on
circuits without a channel (their SPAM-robust variant; those shots count in M).
As in their experiment the channel is emulated: one pool of circuits, each with one uniform random Pauli string
inserted, is measured once; every trial picks half of the pool (uniformly for the depolarising channel; commuting
with P with probability 2/3 or 1/3 otherwise). The pool runs on the largest size; a smaller n reads the first n
pairs of the same shots. Two limits to state with the result: trials share one measured pool (not independent),
and the shots of one circuit share one inserted Pauli, while the bound counts independent channel uses.

`intrinsic` channel (R3-INTRINSIC): founders are ring qubits with a dangling sister; the channel is the ring's own
CZ brick applied twice (ideally the identity) under a random Pauli twirl. The measured per-pair Pauli rates are the
noise model that R6's certificate needs (gap G4); it is close to the identity, so it is a calibration, not a
separation (X8). Written to <run>/qhard/intrinsic_noise.json.
"""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

PAULI_XZ = {"I": (0, 0), "X": (1, 0), "Y": (1, 1), "Z": (0, 1)}
LETTERS = "IXYZ"
SHOTS_DIV = 400               # R3-TEST: shots per pool circuit = --shots / SHOTS_DIV, at least MIN_POOL_SHOTS
MIN_POOL_SHOTS = 10           # 10 shots per inserted Pauli at the default 4000 shots (and in a dry run)


def _anti(p: str, q: str) -> int:
    (px, pz), (qx, qz) = PAULI_XZ[p], PAULI_XZ[q]
    return (px * qz + pz * qx) & 1


def coset_string(hidden: str, sign: int, g: np.random.Generator) -> str:
    """Uniform Pauli string Q with <Q, hidden> = sign (mod 2)."""
    q = [LETTERS[int(v)] for v in g.integers(0, 4, len(hidden))]
    if sum(_anti(h, c) for h, c in zip(hidden, q)) % 2 != sign:
        i = int(g.integers(len(hidden)))
        flip = next(c for c in "XYZ" if c != hidden[i])            # anticommutes with hidden[i]
        xz = tuple(a ^ b for a, b in zip(PAULI_XZ[q[i]], PAULI_XZ[flip]))
        q[i] = next(k for k, v in PAULI_XZ.items() if v == xz)
    return "".join(q)


def pair_layer(pairs: list[list[int]], applied: str, name: str) -> QuantumCircuit:
    """M13 (programmed channel). Qubit 2i = founder of pair i, 2i + 1 = its sister; clbit k = qubit k."""
    n = len(pairs)
    qc = QuantumCircuit(2 * n, 2 * n, name=name)
    for i in range(n):
        qc.h(2 * i)
        qc.cx(2 * i, 2 * i + 1)
    qc.barrier()
    for i, c in enumerate(applied):
        if c != "I":
            getattr(qc, c.lower())(2 * i)
    qc.barrier()
    for i in range(n):
        qc.cx(2 * i, 2 * i + 1)
        qc.h(2 * i)
    qc.measure(range(2 * n), range(2 * n))
    qc.metadata = {"layout": [int(q) for p in pairs for q in p], "applied": applied}
    return qc


def measured_paulis(bits: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Bell readout -> (x, z) of the Pauli seen on each founder: x = sister bit, z = founder bit."""
    return bits[:, 1:2 * n:2], bits[:, 0:2 * n:2]


def pauli_estimator(bits: list[np.ndarray], n: int, pauli: str) -> tuple[float, float, int]:
    """M14. Eigenvalue estimate of `pauli` (one letter per pair) +- sigma over every shot of every instance."""
    px = np.array([PAULI_XZ[c][0] for c in pauli], dtype=np.uint8)
    pz = np.array([PAULI_XZ[c][1] for c in pauli], dtype=np.uint8)
    vals = []
    for bt in bits:
        qx, qz = measured_paulis(bt, n)
        vals.append(1.0 - 2.0 * (((qz * px) + (qx * pz)).sum(1) & 1))
    v = np.concatenate(vals)
    lam = float(v.mean())
    return lam, math.sqrt(max(1 - lam * lam, 1e-12) / len(v)), len(v)


def efl_bound(n: int, m: int) -> float:
    """Success bound of every learner without a quantum memory, M measurements, n >= 4 (2408.03376 Eq. 4)."""
    return min(1.0, 0.5 + 0.43 * m / 2.0 ** n)


def _run_test(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    tiles = QH.tile_layout(tg, "pair")
    cert = (runio.load_json(ctx.run_dir / "certificate.json") or {}).get("pairs")
    if cert:                                                        # Bell map of this run: its certified pairs, best S first
        good = {tuple(p["qubits"]) for p in cert if p["certified"]}
        tiles = [t for t in tiles if tuple(t["qubits"]) in good]
    sizes = sorted(n for n in cfg["pairs"] if n <= len(tiles))      # sizes the chip cannot hold are left out
    if not sizes:
        raise QH.NoLayout(f"only {len(tiles)} disjoint {'certified ' if cert else ''}pairs on {tg.name}, "
                          f"{min(cfg['pairs'])} asked")
    n_max, K, T = sizes[-1], cfg["pool"], cfg["trials"]
    pairs = [t["qubits"] for t in tiles[:n_max]]
    g = Q.rng(ctx, name, "test")
    pool = ["".join(LETTERS[int(v)] for v in g.integers(0, 4, n_max)) for _ in range(K)]
    s = max(MIN_POOL_SHOTS, ctx.shots // SHOTS_DIV)
    half = K // 2
    circuits = [pair_layer(pairs, q, f"test_{k:03d}") for k, q in enumerate(pool)] + [pair_layer(pairs, "I" * n_max, "test_cal")]
    bits, info = Q.execute(ctx, name, circuits, [s] * K + [half * s])
    s, cal_shots = len(bits[0]), len(bits[-1])                      # after the spend guard
    M = half * s + cal_shots
    qx, qz = measured_paulis(np.concatenate(bits[:K]), n_max)       # (K s, n_max)
    cx, cz = measured_paulis(bits[-1], n_max)
    ax = np.array([[PAULI_XZ[c][0] for c in q] for q in pool], dtype=np.uint8)
    az = np.array([[PAULI_XZ[c][1] for c in q] for q in pool], dtype=np.uint8)
    rows = []
    for n in sizes:
        wins = {"depolarising": [], "pauli": []}
        fs = []
        for _ in range(T):
            while True:
                P = g.integers(0, 4, n)
                if P.any():
                    break
            px = np.array([PAULI_XZ[LETTERS[int(v)]][0] for v in P], dtype=np.uint8)
            pz = np.array([PAULI_XZ[LETTERS[int(v)]][1] for v in P], dtype=np.uint8)
            anti = ((az[:, :n] @ px) + (ax[:, :n] @ pz)) & 1        # Alice: does the inserted Pauli anticommute with P
            kind = "pauli" if g.integers(2) else "depolarising"
            if kind == "depolarising":
                sel = g.choice(K, half, replace=False)
            else:
                lam = (1 if g.integers(2) else -1) / 3
                com, ant = np.flatnonzero(anti == 0), np.flatnonzero(anti == 1)
                n_c = int(np.clip(g.binomial(half, (1 + lam) / 2), half - len(ant), len(com)))
                sel = np.concatenate([g.choice(com, n_c, replace=False), g.choice(ant, half - n_c, replace=False)])
            per = (1.0 - 2.0 * (((qz[:, :n] @ px) + (qx[:, :n] @ pz)) & 1)).reshape(K, s).mean(1)
            est = float(per[sel].mean())                                             # Bob: lambda(P) from his shots
            F = float((1.0 - 2.0 * (((cz[:, :n] @ px) + (cx[:, :n] @ pz)) & 1)).mean())    # no channel: SPAM factor
            fs.append(F)
            wins[kind].append((abs(est) > max(F, 0.0) / 6) == (kind == "pauli"))
        w = wins["depolarising"] + wins["pauli"]
        ps = float(np.mean(w))
        rows.append({"n": n, "success": ps, "sigma": Q.binom_sigma(ps, T), "bound": efl_bound(n, M), "trials": T,
                     "success_depolarising": float(np.mean(wins["depolarising"])) if wins["depolarising"] else None,
                     "success_pauli": float(np.mean(wins["pauli"])) if wins["pauli"] else None,
                     "spam_factor_mean": float(np.mean(fs)), "threshold_mean": float(np.mean(fs)) / 6})
        r = rows[-1]
        r["passed"] = bool(n >= 4 and r["bound"] < 1 and r["success"] - 3 * r["sigma"] > r["bound"])
    Q.save(ctx, name, {"sizes": sizes, "pool": K, "shots_per_circuit": s, "calibration_shots": cal_shots,
                       "measurements_M": M, "pairs_available": len(tiles), "pairs": pairs,
                       "pairs_S": [t.get("S") for t in tiles[:n_max]],
                       "pairs_from": "Bell map of this run (certified pairs, best S first)" if cert else "calibration forecast",
                       "info": info, "rows": rows})
    ok = [r for r in rows if r["passed"]]
    top = ok[-1] if ok else rows[-1]
    return [Q.claim(ctx, name, cfg | {"bound": top["bound"]}, top["success"], top["sigma"], bool(ok), info["label"],
                    f"n = {top['n']} pairs ({2 * top['n']} qubits), M = {M} measurements ({cal_shots} of them without a "
                    f"channel), {T} trials on one pool of {K} circuits x {s} shots; all sizes: "
                    + ", ".join(f"n={r['n']}: {r['success']:.3f} vs {r['bound']:.3f}" for r in rows)
                    + "; trials share the pool; one inserted Pauli per circuit")]


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    if cfg["channel"] == "intrinsic":
        return _run_intrinsic(ctx, name, cfg)
    if cfg["channel"] == "test":
        return _run_test(ctx, name, cfg)
    tg = Q.session(ctx).target
    sizes = sorted(cfg["pairs"])
    tiles = QH.tile_layout(tg, "pair")
    if len(tiles) < sizes[-1]:
        raise QH.NoLayout(f"only {len(tiles)} disjoint pairs on {tg.name}, {sizes[-1]} asked (X7: at most 64)")
    g = Q.rng(ctx, name, "pairs")
    K = cfg["instances"]
    circuits, meta = [], []
    for n in sizes:
        pairs = [t["qubits"] for t in tiles[:n]]
        hidden = "".join("XYZ"[int(v)] for v in g.integers(0, 3, n))
        sign = int(g.integers(2))
        for k in range(K):
            circuits.append(pair_layer(pairs, coset_string(hidden, sign, g), f"pairs_n{n}_{k:02d}"))
        meta.append({"n": n, "hidden": hidden, "sign": sign, "forecast_r": float(np.median([t["r"] for t in tiles[:n]]))})
    shots = max(100, ctx.shots // 4)
    bits, info = Q.execute(ctx, name, circuits, shots)
    plan = {"sizes": sizes, "instances": K, "pairs_available": len(tiles), "info": info,
            "forecast": [{k: m[k] for k in ("n", "forecast_r")} for m in meta]}
    rows = []
    for j, m in enumerate(meta):
        lam, sig, nshots = pauli_estimator(bits[j * K:(j + 1) * K], m["n"], m["hidden"])
        rows.append({"n": m["n"], "lambda": lam, "sigma": sig, "shots": nshots, "hidden_sign": m["sign"],
                     "sign_recovered": (lam < 0) == bool(m["sign"]), "z": abs(lam) / sig})
    use = [r for r in rows if abs(r["lambda"]) > 2 * r["sigma"]]
    over, over_sig = float("nan"), float("nan")
    if use:
        nn = np.array([r["n"] for r in use], float)
        ln = np.array([math.log(abs(r["lambda"])) for r in use])
        sl = np.array([r["sigma"] / abs(r["lambda"]) for r in use])
        a = float((nn * ln).sum() / (nn * nn).sum())                       # ln r, least squares through the origin
        a_sig = float(math.sqrt(((nn * sl) ** 2).sum()) / (nn * nn).sum())
        over, over_sig = math.exp(-2 * a), 2 * math.exp(-2 * a) * a_sig
    top = rows[-1]
    Q.save(ctx, name, plan | {"rows": rows, "overhead_per_qubit": over, "overhead_sigma": over_sig})
    ok = bool(use) and over + 3 * over_sig < cfg["bound"]
    if name == "R3-CHIP64":
        ok = ok and top["sign_recovered"] and top["z"] >= 5
    return [Q.claim(ctx, name, cfg, over if use else None, over_sig if use else None, ok, info["label"],
                     f"sizes {sizes} pairs, {K} random instances each; largest size: lambda = {top['lambda']:+.4f} +- "
                     f"{top['sigma']:.4f} ({top['z']:.1f} sigma, hidden sign {'recovered' if top['sign_recovered'] else 'NOT recovered'}); "
                     f"pairs selected by forecast signal; the memoryless bound is a theorem [verify], no baseline arm run")]


def _run_intrinsic(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    lay = QH.ring_layout(tg, cfg["ring"], n_anc=cfg["pairs"])
    ring, anc = lay["ring"], lay["ancillas"]
    if not anc:
        raise QH.NoLayout(f"the {cfg['ring']}-ring on {tg.name} has no dangling sister qubits")
    n, m = len(ring), len(anc)
    pos = {q: k for k, q in enumerate(ring)}
    g = Q.rng(ctx, name, "intrinsic")
    circuits = []
    for k in range(cfg["instances"]):
        tw = [LETTERS[int(v)] for v in g.integers(0, 4, n)]
        qc = QuantumCircuit(n + m, 2 * m, name=f"intrinsic_{k:02d}")
        for j, a in enumerate(anc):
            qc.h(pos[a["data"]])
            qc.cx(pos[a["data"]], n + j)
        for rep in range(2):                                    # twirl, CZ brick, CZ brick, the same twirl again
            for q, c in enumerate(tw):
                if c != "I":
                    getattr(qc, c.lower())(q)
            if rep == 0:
                for _ in range(2):
                    qc.barrier()
                    for i in range(0, n, 2):
                        qc.cz(i, (i + 1) % n)
        for j, a in enumerate(anc):
            qc.cx(pos[a["data"]], n + j)
            qc.h(pos[a["data"]])
            qc.measure(pos[a["data"]], 2 * j)
            qc.measure(n + j, 2 * j + 1)
        qc.metadata = {"layout": [int(q) for q in ring] + [int(a["ancilla"]) for a in anc]}
        circuits.append(qc)
    bits, info = Q.execute(ctx, name, circuits, max(100, ctx.shots // 4))
    plan = {"ring": ring, "pairs": anc, "instances": len(circuits), "info": info}
    allb = np.concatenate(bits)
    qx, qz = measured_paulis(allb, m)
    rates = {"I": ((qx == 0) & (qz == 0)).mean(0), "X": ((qx == 1) & (qz == 0)).mean(0),
             "Y": ((qx == 1) & (qz == 1)).mean(0), "Z": ((qx == 0) & (qz == 1)).mean(0)}
    p_id = float(rates["I"].mean())
    over = 1.0 / max(p_id, 1e-9) ** 2
    model = {"per_pair_pauli_rates": {k: v.tolist() for k, v in rates.items()}, "mean_identity_rate": p_id,
             "includes": "Bell preparation and readout of the pair (SPAM) + two CZ bricks; not separated",
             "error_per_cz_brick_upper": (1 - p_id) / 2, "label": info["label"], "source": name}
    runio.save_json(ctx.path("qhard", "intrinsic_noise.json"), model)
    Q.save(ctx, name, plan | {"model": model})
    c = Q.claim(ctx, name, cfg | {"witness": "mean no-error rate per founder over two twirled CZ bricks (Bell readout)"},
                p_id, Q.binom_sigma(p_id, len(allb) * m), True, info["label"],
                 f"{m} founder / sister pairs on the {n}-ring; mean no-error rate per pair {p_id:.4f} (per-qubit overhead "
                 f"{over:.2f}); close to the identity, so a noise model for R6 (gap G4), not a separation (X8)")
    c["claim_level"] = "calibration (noise model for R6)"
    return [c]
