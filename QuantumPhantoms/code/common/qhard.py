"""Shared Q-HARD building blocks (plans/qhard-*.md): GF(2) algebra, chip layouts, the ring skeleton.

GF(2)      rank / nullspace / left_nullspace / solve on small dense uint8 matrices (row vectors).
Layouts    M1 ring_layout, M9 tile_layout. Rings are boundaries of connected sets of heavy-hex hexagons (XOR of
           their edges, kept when it is one simple cycle): n = 12, 20, 24, 28, ... Tiles are disjoint stars (a
           degree-3 qubit + its 3 neighbours), pairs (maximum matching), hexagons or 20-rings, ranked by calibration
           error on the pruned graph (common.allocate.prune). When the run has a Bell map (section C), its measured
           S per coupler is added to every ranking (bell_deficit) and the pairs it measured come first, best S first.
Ring       M2 skeleton, M3 cut_entropy, M7 acceptance_model. A skeleton is data:
               {"n", "depth", "oneq": [depth][n] of 0 | 1 | None, "bonds": [depth] of [(i, j)], "seed"}
           Layer k (1..depth) = one-qubit gates (0: sqrt-X, 1: S sqrt-X; None: no gate) then the CZ brick on even or
           odd bonds (periodic); an H layer comes first. depth 2 with cluster=True is the cyclic cluster state.
           Slot t (0..depth) is the moment after layer t. Paulis are (x, z) bit vectors; signs are never tracked
           here (builders take them from a stabilizer simulation).
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit

from common import allocate as A, targets as T
from common.quantum import Refused, log


# ============================================================================================== GF(2)
def _reduce(M: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Reduced row echelon form and its pivot columns."""
    A = (np.array(M, dtype=np.uint8) & 1).copy()
    rows, cols = A.shape
    piv, r = [], 0
    for c in range(cols):
        if r >= rows:
            break
        hit = np.flatnonzero(A[r:, c])
        if len(hit) == 0:
            continue
        p = r + int(hit[0])
        if p != r:
            A[[r, p]] = A[[p, r]]
        mask = A[:, c].astype(bool)
        mask[r] = False
        A[mask] ^= A[r]
        piv.append(c)
        r += 1
    return A, piv


def rank(M: np.ndarray) -> int:
    M = np.atleast_2d(M)
    if M.size == 0:
        return 0
    return len(_reduce(M)[1])


def nullspace(M: np.ndarray) -> np.ndarray:
    """Basis (rows) of {v : M v = 0}."""
    M = np.atleast_2d(np.array(M, dtype=np.uint8) & 1)
    cols = M.shape[1]
    A, piv = _reduce(M)
    free = [c for c in range(cols) if c not in piv]
    out = np.zeros((len(free), cols), dtype=np.uint8)
    for k, f in enumerate(free):
        out[k, f] = 1
        for r, p in enumerate(piv):
            out[k, p] = A[r, f]
    return out


def left_nullspace(M: np.ndarray) -> np.ndarray:
    """Basis (rows) of {c : c M = 0}: the row combinations that vanish."""
    return nullspace(np.atleast_2d(M).T)


def solve(M: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """One c with c M = b (row combination of the rows of M), or None."""
    M = np.atleast_2d(np.array(M, dtype=np.uint8) & 1)
    b = np.array(b, dtype=np.uint8) & 1
    rows = M.shape[0]
    aug = np.concatenate([M.T, b[:, None]], axis=1)          # unknown c: M^T c = b
    A, piv = _reduce(aug)
    if rows in piv:                                           # pivot in the augmented column: inconsistent
        return None
    c = np.zeros(rows, dtype=np.uint8)
    for r, p in enumerate(piv):
        c[p] = A[r, rows]
    return c


# ============================================================================================== layouts
MAX_FACES = 9
MAX_SETS = 60000


class NoLayout(Refused):
    pass


def _edge(i: int, j: int) -> tuple[int, int]:
    return (i, j) if i < j else (j, i)


def order_cycle(edges) -> list[int] | None:
    """Nodes along the cycle, or None if `edges` is not one simple cycle."""
    g = nx.Graph(list(edges))
    if g.number_of_nodes() == 0 or any(d != 2 for _, d in g.degree()) or not nx.is_connected(g):
        return None
    start = min(g.nodes)
    out, prev, cur = [start], None, start
    while True:
        nxt = [x for x in g[cur] if x != prev]
        nxt = min(nxt) if prev is None else nxt[0]
        if nxt == start:
            break
        out.append(nxt)
        prev, cur = cur, nxt
    return out


def faces(g: nx.Graph, size: int = 12) -> list[frozenset]:
    """Hexagon faces (12-cycles of heavy-hex) as edge sets."""
    out = []
    for cyc in nx.minimum_cycle_basis(g):
        if len(cyc) != size:
            continue
        sub = g.subgraph(cyc)
        es = frozenset(_edge(*e) for e in sub.edges)
        if len(es) == size and order_cycle(es) is not None:
            out.append(es)
    return sorted(out, key=lambda f: sorted(f))


def _face_sets(fs: list[frozenset], max_faces: int):
    """Connected sets of faces (two faces are adjacent when they share an edge), smallest first."""
    adj = {i: {j for j in range(len(fs)) if j != i and fs[i] & fs[j]} for i in range(len(fs))}
    seen = {frozenset([i]) for i in range(len(fs))}
    layer = sorted(seen, key=sorted)
    count = 0
    while layer:
        nxt = set()
        for s in layer:
            count += 1
            yield s
            if count >= MAX_SETS:
                return
            if len(s) >= max_faces:
                continue
            for i in s:
                for j in adj[i]:
                    if j not in s:
                        t = s | {j}
                        if t not in seen:
                            seen.add(t)
                            nxt.add(t)
        layer = sorted(nxt, key=sorted)


RELAXED = {"readout_gt": 0.2, "e2q_gt": 0.1}    # only unusable qubits / couplers; used when the pruned chip has no ring
TSIRELSON = 2 * math.sqrt(2)


def bell_deficit(tg: T.Target, edges) -> float:
    """Sum over couplers of (2 sqrt 2 - S) from the run's Bell map (tg.meta["pair_map"], section C). A coupler the
    map did not measure counts as the map's median, so it neither helps nor hurts. 0 without a map: the ranking is
    then calibration only."""
    pm = tg.meta.get("pair_map") or {}
    if not pm:
        return 0.0
    med = float(np.median(list(pm.values())))
    return float(sum(TSIRELSON - pm.get(_edge(int(a), int(b)), med) for a, b in edges))


def ring_cost(tg: T.Target, ring: list[int], rank_by: str = "cz") -> dict:
    n = len(ring)
    cz = float(np.mean([tg.edge_err(ring[k], ring[(k + 1) % n]) for k in range(n)]))
    ro = float(np.mean([tg.ro(q) for q in ring]))
    bell = bell_deficit(tg, [(ring[k], ring[(k + 1) % n]) for k in range(n)])
    return {"mean_cz": cz, "mean_ro": ro, "bell_deficit": bell, "score": cz + (ro if rank_by == "cz+ro" else 0.0) + bell}


def rings(tg: T.Target, n: int, rank_by: str = "cz", max_faces: int = MAX_FACES) -> list[dict]:
    """Every n-cycle that is the boundary of a connected hexagon set, best first. On the pruned graph; when that
    leaves no ring (live calibrations do this: one pruned qubit removes a hexagon), on the RELAXED graph, marked."""
    strict = A.prune(tg)[0]
    out = _rings_on(tg, strict, n, rank_by, max_faces)
    if not out:                # a ring needs every one of its qubits, a tree does not: fewest pruned qubits, then cost
        g = tg.graph.copy()
        g.remove_edges_from([e for e in g.edges if tg.edge_err(*e) > RELAXED["e2q_gt"]])
        g.remove_nodes_from([q for q in g.nodes if tg.ro(q) > RELAXED["readout_gt"] or tg.e1q[q] >= A.PRUNE["sx_ge"]])
        out = [r | {"relaxed": True, "pruned_qubits": [q for q in r["ring"] if q not in strict]}
               for r in _rings_on(tg, g, n, "cz+ro", max_faces)]
        out.sort(key=lambda r: (len(r["pruned_qubits"]), r["score"], r["ring"]))
        if out:
            log(f"no {n}-ring on the pruned {tg.name}: {len(out)} rings ranked by pruned qubits, then CZ + readout error; "
                f"best holds pruned {out[0]['pruned_qubits']}")
    return out


def _rings_on(tg: T.Target, g: nx.Graph, n: int, rank_by: str, max_faces: int) -> list[dict]:
    fs = faces(g)
    found: dict[frozenset, list[int]] = {}
    need = max(1, (n - 4 + 7) // 8)                       # tree-like unions give n = 8k + 4: fewer faces cannot reach n
    for s in _face_sets(fs, max_faces):
        if len(s) < min(need, max_faces) - 2:
            continue
        bd: set = set()
        for i in s:
            bd ^= fs[i]
        if len(bd) != n:
            continue
        key = frozenset(bd)
        if key in found:
            continue
        cyc = order_cycle(bd)
        if cyc is not None:
            found[key] = cyc
    out = [{"ring": c, **ring_cost(tg, c, rank_by)} for c in found.values()]
    return sorted(out, key=lambda r: (r["score"], r["ring"]))


def ring_layout(tg: T.Target, n: int, rank_by: str = "cz", n_anc: int = 0, exclude=()) -> dict:
    """M1. Best n-ring + up to n_anc dangling ancillas (off-ring neighbours of degree-3 ring qubits)."""
    cands = [r for r in rings(tg, n, rank_by) if not set(r["ring"]) & set(exclude)]
    if not cands:
        raise NoLayout(f"no {n}-ring on {tg.name} (heavy-hex rings have n = 12, 20, 24, 28, ... step 4)")
    best = cands[0]
    ring = best["ring"]
    on = set(ring)
    g, _ = A.prune(tg)
    anc: dict[int, tuple[float, int]] = {}
    for q in ring:
        for a in (g[q] if q in g else ()):                 # a relaxed ring may hold pruned qubits: no ancilla there
            if a in on:
                continue
            cost = tg.edge_err(q, a) + tg.ro(a)
            if a not in anc or cost < anc[a][0]:
                anc[a] = (cost, q)
    picked = sorted((cost, a, q) for a, (cost, q) in anc.items())
    used_data, ancillas = set(), []
    for cost, a, q in picked:                              # one ancilla per ring qubit
        if q in used_data or len(ancillas) >= n_anc:
            continue
        used_data.add(q)
        ancillas.append({"ancilla": int(a), "data": int(q), "cost": float(cost)})
    return {"backend": tg.name, "n": n, "ring": [int(q) for q in ring], "ancillas": ancillas,
            "max_ancillas": len({q for _, q in anc.values()}), "mean_cz": best["mean_cz"], "mean_ro": best["mean_ro"],
            "rank_by": rank_by, "n_candidates": len(cands), "relaxed": best.get("relaxed", False)}


# ---------------------------------------------------------------------------------------------- M9 tiles
def _pack(cands: list[dict], seed: int, restarts: int = 40) -> list[dict]:
    """Randomised greedy disjoint packing: most tiles first, then lowest summed cost."""
    rs = np.random.default_rng(seed)
    best: list[dict] = []
    for r in range(restarts):
        jitter = np.ones(len(cands)) if r == 0 else rs.uniform(0.6, 1.6, len(cands))
        used, pick = set(), []
        for k in np.argsort([c["cost"] * j for c, j in zip(cands, jitter)], kind="stable"):
            c = cands[int(k)]
            if used.isdisjoint(c["qubits"]):
                used |= set(c["qubits"])
                pick.append(c)
        if (len(pick), -sum(c["cost"] for c in pick)) > (len(best), -sum(c["cost"] for c in best)):
            best = pick
    return sorted(best, key=lambda c: (c["cost"], c["qubits"]))


def pair_signal(tg: T.Target, a: int, b: int) -> float:
    """Desk forecast of the per-pair Bell signal: (1 - 2 e_ro)^2 (1 - 16/15 e_cz)^2 (2 CZ, 2 readouts)."""
    return (1 - 2 * tg.ro(a)) * (1 - 2 * tg.ro(b)) * (1 - 16 / 15 * tg.edge_err(a, b)) ** 2


def tile_layout(tg: T.Target, shape: str, max_tiles: int | None = None, seed: int = 0, rank_by: str = "cz+ro",
                exclude=()) -> list[dict]:
    """M9. Disjoint tiles ranked by summed CZ + readout error. shape: star4 | pair | path3 | path4 | hexagon | ring20."""
    g, _ = A.prune(tg)
    if exclude:
        g = g.subgraph([q for q in g.nodes if q not in set(exclude)]).copy()
    if shape == "star4":
        cands = []
        for c in g.nodes:
            nb = sorted(g[c])
            if len(nb) != 3:
                continue
            cost = sum(tg.edge_err(c, x) for x in nb) + sum(tg.ro(x) for x in nb) + bell_deficit(tg, [(c, x) for x in nb])
            cands.append({"shape": shape, "centre": int(c), "outputs": [int(x) for x in nb],
                          "qubits": [int(c)] + [int(x) for x in nb], "cost": float(cost)})
        tiles = _pack(cands, seed)
    elif shape == "pair":
        tiles, used = [], set(exclude)
        pm = tg.meta.get("pair_map") or {}
        for (a, b), S in sorted(pm.items(), key=lambda kv: (-kv[1], kv[0])):   # measured pairs first, best S first
            if a in used or b in used or S <= 2.0:              # a coupler measured without a violation is not a tile
                continue
            used |= {a, b}
            tiles.append({"shape": shape, "qubits": [a, b], "r": float(pair_signal(tg, a, b)), "S": float(S),
                          "cost": float(1 - S / TSIRELSON)})
        h = nx.Graph()                                      # then the couplers the map did not reach, by calibration
        for a, b in g.edges:
            if a not in used and b not in used and _edge(a, b) not in pm:
                h.add_edge(a, b, w=pair_signal(tg, a, b))
        m = nx.max_weight_matching(h, maxcardinality=True, weight="w")
        tiles += sorted(({"shape": shape, "qubits": [int(min(e)), int(max(e))], "r": float(h[e[0]][e[1]]["w"]),
                          "S": None, "cost": float(1 - h[e[0]][e[1]]["w"])} for e in m),
                        key=lambda c: (c["cost"], c["qubits"]))
    elif shape in ("path3", "path4"):                       # simple paths, in path order (QCAND: B-KS, B-MSQ)
        k, cands = int(shape[-1]), []
        stack = [[q] for q in sorted(g.nodes)]
        while stack:
            p = stack.pop()
            if len(p) == k:
                if p[0] < p[-1]:                            # each path once
                    es = list(zip(p, p[1:]))
                    cost = sum(tg.edge_err(a, b) for a, b in es) + sum(tg.ro(q) for q in p) + bell_deficit(tg, es)
                    cands.append({"shape": shape, "qubits": [int(q) for q in p], "cost": float(cost)})
                continue
            stack += [p + [w] for w in g[p[-1]] if w not in p]
        tiles = _pack(cands, seed)
    elif shape in ("hexagon", "ring20"):
        n = 12 if shape == "hexagon" else 20
        cands = [{"shape": shape, "qubits": r["ring"],
                  "cost": r["mean_cz"] + (r["mean_ro"] if rank_by == "cz+ro" else 0) + r["bell_deficit"],
                  "mean_cz": r["mean_cz"], "mean_ro": r["mean_ro"], "relaxed": r.get("relaxed", False)}
                 for r in rings(tg, n, rank_by, max_faces=2) if not set(r["ring"]) & set(exclude)]
        tiles = _pack(cands, seed)
    else:
        raise ValueError(f"unknown tile shape {shape!r}")
    if not tiles:
        raise NoLayout(f"no {shape} tile on {tg.name}")
    return tiles[:max_tiles] if max_tiles else tiles


# ============================================================================================== ring
ONEQ_SETS = ("sx_ssx",)                      # X4: uniform random 1q Cliffords reach min entropy 13 at depth 32
KAPPA = 2.2                                  # M7: effective loss per CZ = kappa x mean CZ error (one-point fit)
FIT_POINT = {"n_cz": 2644, "accept": 3.83e-4, "mean_cz": 0.00134, "source": "2607.25941 v3 abstract [verify]"}


def skeleton(n: int, depth: int, oneq_set: str = "sx_ssx", seed: int = 0, cluster: bool = False) -> dict:
    """M2."""
    if n % 2:
        raise ValueError("ring size must be even (brickwork on a ring)")
    if oneq_set not in ONEQ_SETS:
        raise ValueError(f"oneq_set {oneq_set!r} refused: only {ONEQ_SETS} (plan X4)")
    g = np.random.default_rng(seed)
    oneq, bonds = [], []
    for k in range(depth):
        oneq.append([None] * n if cluster else [int(v) for v in g.integers(0, 2, n)])
        bonds.append([(i, (i + 1) % n) for i in range(k % 2, n, 2)])
    return {"n": n, "depth": depth, "oneq": oneq, "bonds": bonds, "seed": seed,
            "oneq_set": None if cluster else oneq_set, "cluster": cluster}


def n_cz(sk: dict) -> int:
    return sum(len(b) for b in sk["bonds"])


# ---------------------------------------------------------------------------------------------- Pauli propagation
def _oneq(x: np.ndarray, z: np.ndarray, gates: list, inverse: bool) -> None:
    """Conjugation by sqrt-X: (x, z) -> (x ^ z, z); by S: (x, z) -> (x, z ^ x). Gate 1 = S after sqrt-X."""
    for q, gate in enumerate(gates):
        if gate is None:
            continue
        if gate == 1 and inverse:
            z[..., q] ^= x[..., q]
        x[..., q] ^= z[..., q]
        if gate == 1 and not inverse:
            z[..., q] ^= x[..., q]


def _cz(x: np.ndarray, z: np.ndarray, bonds: list) -> None:
    for i, j in bonds:
        z[..., j] ^= x[..., i]
        z[..., i] ^= x[..., j]


def forward(sk: dict, x: np.ndarray, z: np.ndarray, t_from: int, t_to: int | None = None):
    """Pauli at slot t_from -> the same operator at slot t_to (default: the end). In place; returns (x, z)."""
    for k in range(t_from, sk["depth"] if t_to is None else t_to):
        _oneq(x, z, sk["oneq"][k], False)
        _cz(x, z, sk["bonds"][k])
    return x, z


def backward_layer(sk: dict, x: np.ndarray, z: np.ndarray, t: int):
    """Pauli at slot t -> slot t - 1 (through layer t, t >= 1). In place."""
    _cz(x, z, sk["bonds"][t - 1])
    _oneq(x, z, sk["oneq"][t - 1], True)
    return x, z


def stabilizers(sk: dict) -> tuple[np.ndarray, np.ndarray]:
    """Generators (x, z), one per row, of the stabilizer group of the final skeleton state (X_i at slot 0)."""
    n = sk["n"]
    x, z = np.eye(n, dtype=np.uint8), np.zeros((n, n), dtype=np.uint8)
    return forward(sk, x, z, 0)


# ---------------------------------------------------------------------------------------------- M3
def subset_entropy(sx: np.ndarray, sz: np.ndarray, subset) -> int:
    sub = list(subset)
    return rank(np.concatenate([sx[:, sub], sz[:, sub]], axis=1)) - len(sub)


def cut_entropy(sk: dict, n_random: int = 300, seed: int = 0) -> dict:
    """M3. Min half-arc entropy and min over random balanced bipartitions (go rule for R6b: both >= 27)."""
    n = sk["n"]
    sx, sz = stabilizers(sk)
    half = n // 2
    arcs = [subset_entropy(sx, sz, [(s + k) % n for k in range(half)]) for s in range(n)]
    g = np.random.default_rng(seed)
    rnd = [subset_entropy(sx, sz, g.permutation(n)[:half]) for _ in range(n_random)]
    return {"n": n, "depth": sk["depth"], "min_half_arc": int(min(arcs)), "max_half_arc": int(max(arcs)),
            "min_random_bipartition": int(min(rnd)) if rnd else None, "n_random": n_random,
            "method": "GF(2) rank of the restricted stabilizer matrix minus the subset size"}


# ---------------------------------------------------------------------------------------------- circuit
def circuit(sk: dict, layout: list[int], ancillas: list[dict] | None = None, insertions: dict | None = None,
            t_sites=(), basis: str | None = None, name: str = "ring") -> QuantumCircuit:
    """The ring circuit on `layout` (ring order). Optional parts, all unitary with terminal readout:
    ancillas     [{"ancilla": phys, "data": phys}]; ancilla k is circuit qubit n + k and is measured into clbit n + k
    insertions   {ancilla index k: [slots]}: CZ(ancilla, its data qubit) at those slots (H on the ancilla first / last)
    t_sites      [(ring index, slot)]: T gates
    basis        per-qubit Pauli string for the data readout ("X", "Y", "Z" or "I" = Z); default all Z
    """
    n = sk["n"]
    anc = ancillas or []
    ins = insertions or {}
    pos = {q: k for k, q in enumerate(layout)}
    qc = QuantumCircuit(n + len(anc), n + len(anc), name=name)
    ts: dict[int, list[int]] = {}
    for q, slot in t_sites:
        ts.setdefault(int(slot), []).append(int(q))

    def slot_ops(t: int) -> None:
        for k, slots in ins.items():
            if t in slots:
                qc.cz(n + int(k), pos[anc[int(k)]["data"]])
        for q in ts.get(t, []):
            qc.t(q)

    qc.h(range(n))
    for k in ins:
        qc.h(n + int(k))
    slot_ops(0)
    for d in range(sk["depth"]):
        for q, gate in enumerate(sk["oneq"][d]):
            if gate is None:
                continue
            qc.sx(q)
            if gate == 1:
                qc.s(q)
        for i, j in sk["bonds"][d]:
            qc.cz(i, j)
        if sk.get("barrier"):                      # keeps a repeated CZ layer from being cancelled by the compiler
            qc.barrier(range(n))
        slot_ops(d + 1)
    for k in ins:
        qc.h(n + int(k))
    for q, p in enumerate(basis or "Z" * n):
        if p == "X":
            qc.h(q)
        elif p == "Y":
            qc.sdg(q)
            qc.h(q)
    qc.measure(range(n + len(anc)), range(n + len(anc)))
    qc.metadata = {"layout": [int(q) for q in layout] + [int(a["ancilla"]) for a in anc], "n_data": n,
                   "basis": basis or "Z" * n}
    return qc


# ---------------------------------------------------------------------------------------------- M7
def acceptance_model(tg: T.Target, ring: list[int], n_cz_total: int, kappa: float = KAPPA) -> dict:
    """M7 desk model (a one-point fit, nothing more): acceptance = exp(-kappa e_cz N_CZ); raw fidelity of the
    accepted samples = exp(-0.07 kappa e_cz N_CZ) (1 - e_ro)^n."""
    n = len(ring)
    e_cz = float(np.mean([tg.edge_err(ring[k], ring[(k + 1) % n]) for k in range(n)]))
    e_ro = float(np.mean([tg.ro(q) for q in ring]))
    lam = kappa * e_cz
    return {"backend": tg.name, "n_cz": int(n_cz_total), "mean_cz": e_cz, "mean_ro": e_ro, "kappa": kappa,
            "loss_per_cz": lam, "acceptance": math.exp(-lam * n_cz_total),
            "raw_fidelity_accepted": math.exp(-0.07 * lam * n_cz_total) * (1 - e_ro) ** n,
            "fit_point": FIT_POINT, "rigour": "desk estimate"}


# ============================================================================================== classical cost ledger
# Exact tensor-network contraction sweeps a temporal boundary across SPACE: its width is the number of two-qubit gates
# crossing the cut (CZ has operator Schmidt rank 2), whatever the one-qubit gates and the T count are.
# Manabe, Gu, Pan, arXiv 2608.13110: open chain width ceil(d/2), ring width d (or d/2 sliced, same cost), time
# O(n d 2^W); they contracted IBM's 70-qubit, depth-70 chain (468 T) in 37 minutes on 32 GPU nodes.
FLOPS_LOG2_DAY = 67           # one day on 1024 H100 GPUs (1.81 PFLOP/s), 2608.13110 Sec. 6.4
FLOPS_LOG2_HARD = 73          # ~1e22 operations per amplitude: the figure the Nighthawk RCS claim stands on (2609.28657)
RAW_KAPPA = 2.5               # raw (no post-selection) fidelity ~ exp(-RAW_KAPPA e_cz N_CZ); one-point fit to
#                               2607.25941 v3 on ibm_boston: acceptance 3.83e-4 x fidelity 0.38 at 2,644 CZ, e_cz 0.134 %


def sweep_width(n: int, weights: dict[tuple[int, int], int]) -> int:
    """Heuristic min over sweep orders of the max number of two-qubit gates crossing the sweep front. An UPPER bound
    on the adversary's best width: the true classical cost can only be lower."""
    g = nx.Graph()
    g.add_nodes_from(range(n))
    for (i, j), w in weights.items():
        g.add_edge(i, j, w=w)
    orders = [list(nx.bfs_tree(g, s).nodes) for s in g.nodes]
    try:
        f = nx.fiedler_vector(g, weight=None, seed=1)
        orders.append([int(v) for v in np.argsort(f)])
    except Exception:
        pass
    best = None
    for order in orders:
        if len(order) < n:
            continue
        inside, cut, worst = set(), 0, 0
        for v in order[:-1]:
            for u in g[v]:
                cut += -g[v][u]["w"] if u in inside else g[v][u]["w"]
            inside.add(v)
            worst = max(worst, cut)
        best = worst if best is None else min(best, worst)
    return int(best or 0)


def classical_cost(sk: dict, t_gates: int) -> dict:
    """log2 of the cheapest known exact method for one amplitude of this skeleton with t T gates."""
    w: dict[tuple[int, int], int] = {}
    for layer in sk["bonds"]:
        for i, j in layer:
            w[_edge(i, j)] = w.get(_edge(i, j), 0) + 1
    n, d = sk["n"], max(sk["depth"], 1)
    width = sweep_width(n, w)
    methods = {"tensor_network_sweep": width + math.log2(n * d), "statevector": float(n),
               "stabilizer_decomposition": 0.228 * t_gates + math.log2(n * d)}
    binding = min(methods, key=methods.get)
    return {"sweep_width": width, "log2_cost": methods, "binding": binding, "log2_cost_min": methods[binding],
            "hard": bool(methods[binding] >= FLOPS_LOG2_HARD), "threshold_log2": FLOPS_LOG2_HARD,
            "one_day_log2": FLOPS_LOG2_DAY,
            "note": "upper bounds on the classical cost from known exact methods (2608.13110 sweep; 2^(0.228 t) "
                    "stabilizer decomposition); approximate / noisy-circuit methods are not counted"}


# ============================================================================================== 2-D patch (band)
def edge_layers(edges: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Greedy proper edge colouring: each colour is one parallel CZ layer (3 on heavy-hex, 4 on a square lattice)."""
    col: dict[tuple[int, int], int] = {}
    used: dict[int, set[int]] = {}
    for e in sorted(_edge(*x) for x in edges):
        c = 0
        while c in used.setdefault(e[0], set()) or c in used.setdefault(e[1], set()):
            c += 1
        col[e] = c
        used[e[0]].add(c)
        used[e[1]].add(c)
    return [[e for e, c in col.items() if c == k] for k in range(max(col.values()) + 1)]


def region(tg: T.Target, n: int) -> dict:
    """Region picker by the Bell map (QCAND). n below the pruned chip: the connected n-qubit patch (grown from every
    centre of the largest component, common.allocate.patch) with the lowest summed CZ + readout error + Bell deficit.
    n at or above it: every pruned qubit that keeps a coupler (the region may then be disconnected).
    -> {nodes (BFS order from the centre), edges [(a, b) physical], whole_chip}."""
    g, _ = A.prune(tg)
    live = [q for q in g.nodes if g.degree(q) > 0]
    if n >= len(live):
        nodes, whole = sorted(live), True
    else:
        comp = max(nx.connected_components(g), key=len)
        if n > len(comp):
            raise NoLayout(f"no connected {n}-qubit region on {tg.name} (largest component {len(comp)})")
        best = None
        for c in sorted(comp):
            p = A.patch(g, tg, n, centre=c)
            cost = (sum(tg.edge_err(a, b) for a, b in p["edges"]) + sum(tg.ro(q) for q in p["nodes"])
                    + bell_deficit(tg, p["edges"]))
            if best is None or cost < best[0]:
                best = (cost, c, p["nodes"])
        nodes, whole = list(nx.bfs_tree(g.subgraph(best[2]), best[1]).nodes), False
    edges = sorted(_edge(int(a), int(b)) for a, b in g.subgraph(nodes).edges)
    return {"nodes": [int(q) for q in nodes], "edges": edges, "whole_chip": whole}


def graph_circuit(nodes: list[int], edges, basis: dict | None = None, name: str = "graph") -> QuantumCircuit:
    """Graph state on `nodes` (H on every qubit, CZ on every edge, one colour class per layer) and a per-qubit readout:
    basis[physical qubit] = "X" | "Y" | "Z" (default) or an angle theta = the axis at theta from Z in the X-Z plane."""
    pos = {q: k for k, q in enumerate(nodes)}
    qc = QuantumCircuit(len(nodes), len(nodes), name=name)
    qc.h(range(len(nodes)))
    for layer in edge_layers(list(edges)) if edges else ():
        for a, b in layer:
            qc.cz(pos[a], pos[b])
    for q, p in (basis or {}).items():
        if p == "X":
            qc.h(pos[q])
        elif p == "Y":
            qc.sdg(pos[q])
            qc.h(pos[q])
        elif p != "Z":
            qc.ry(-float(p), pos[q])
    qc.measure(range(len(nodes)), range(len(nodes)))
    qc.metadata = {"layout": [int(q) for q in nodes]}
    return qc


def patch_layout(tg: T.Target, n: int, width: int) -> dict:
    """Connected n-qubit patch (a BFS ball of the pruned coupling graph) that reaches sweep width `width` with the
    fewest error-weighted CZ: N_CZ = edges x ceil(width / cutwidth). On heavy-hex the cutwidth is ~4, on a ring 2."""
    g, _ = A.prune(tg)
    best = None
    for s in sorted(g.nodes):
        nodes = list(nx.bfs_tree(g, s).nodes)[:n]
        if len(nodes) < n:
            continue
        pos = {q: k for k, q in enumerate(nodes)}
        edges = [_edge(pos[a], pos[b]) for a, b in g.subgraph(nodes).edges]
        cw = sweep_width(n, {e: 1 for e in edges})
        if cw < 2:
            continue
        per_bond = math.ceil(width / cw)
        n_cz = len(edges) * per_bond
        e_cz = float(np.mean([tg.edge_err(nodes[i], nodes[j]) for i, j in edges]))
        e_ro = float(np.mean([tg.ro(q) for q in nodes]))
        fid = math.exp(-RAW_KAPPA * e_cz * n_cz)
        if best is None or fid > best["predicted_raw_fidelity"]:
            best = {"nodes": [int(q) for q in nodes], "edges": edges, "cutwidth": cw, "cz_per_bond": per_bond,
                    "n_cz": n_cz, "mean_cz": e_cz, "mean_ro": e_ro, "predicted_raw_fidelity": fid,
                    "predicted_with_readout": fid * (1 - e_ro) ** n}
    if best is None:
        raise NoLayout(f"no connected {n}-qubit patch on {tg.name}")
    return best | {"backend": tg.name, "n": n, "width_target": width, "rigour": "desk estimate (one-point fit)"}


def patch_skeleton(patch: dict, seed: int = 0) -> dict:
    """Brickwork on the patch: H layer, then per layer random {sqrt-X, S sqrt-X} and one colour class of CZs."""
    layers = edge_layers(patch["edges"])
    depth = len(layers) * patch["cz_per_bond"]
    g = np.random.default_rng(seed)
    return {"n": patch["n"], "depth": depth, "seed": seed, "oneq_set": "sx_ssx", "cluster": False,
            "oneq": [[int(v) for v in g.integers(0, 2, patch["n"])] for _ in range(depth)],
            "bonds": [layers[k % len(layers)] for k in range(depth)]}
