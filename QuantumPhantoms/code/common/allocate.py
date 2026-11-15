"""D-SCALE region allocation from calibration (AC-2): pruning, path / BFS tree / patch builders, buffered composite.


Re-derives the QALife `best_chain` idea (artificial-life; idea only, no code): rank physical qubits and couplers by
their calibration and build the region from the cheapest ones. Pruning follows the Nighthawk-RCS rule
(arXiv 2609.28657): drop qubits with readout > 0.06 or sx error >= 0.5 and couplers with 2q error > 0.02.

Only the qubits a region uses are gated. This removes PJ0's "107-qubit wall" (its gate checked a 2W chain when only
the W germ qubits needed one). Regions of different families sit at graph distance >= 2 (>= 1 idle buffer qubit).

Exit 4 with the largest feasible size when an explicit request cannot be met. Presets are fitted instead (the
allocator shrinks them to the pruned graph and records `fitted`).
"""
from __future__ import annotations

import sys
import time

import networkx as nx
import numpy as np

from common import targets as T

PRUNE = {"readout_gt": 0.06, "sx_ge": 0.5, "e2q_gt": 0.02, "source": "Nighthawk-RCS rule, arXiv 2609.28657",
         # added after live job dbj0ddd6p51s73cjqak0 (ibm_kingston q29 read p(1) = 0.16 inside a GHZ tree while passing
         # the three error gates): coherence gate, relative to the device so it works across Heron r2/r3 and Nighthawk
         "t1_lt_median_frac": 0.25, "t2_lt_median_frac": 0.25, "t_min_us": 20.0}
PATH_TIME_BOX_S = 40.0


class Infeasible(Exception):
    def __init__(self, what: str, requested: int, largest: int):
        super().__init__(f"{what}: requested {requested}, largest feasible {largest}")
        self.what, self.requested, self.largest = what, requested, largest


# ---------------------------------------------------------------------------------------------- pruning / costs
def node_cost(tg: T.Target, q: int) -> float:
    return tg.ro(q) + tg.e1q[q]


def edge_cost(tg: T.Target, i: int, j: int) -> float:
    """e2q + 0.5 (ro + sx of both ends)."""
    return tg.edge_err(i, j) + 0.5 * (node_cost(tg, i) + node_cost(tg, j))


def _median_finite(vals) -> float:
    v = [x for x in vals if np.isfinite(x) and x > 0]
    return float(np.median(v)) if v else float("inf")


def short_coherence(tg: T.Target, q: int) -> bool:
    """T1 or T2 below max(t_min, frac x device median): a qubit that decays inside one shallow circuit."""
    key = ("t1t2", tg.name)
    if key not in _MEDIANS:
        _MEDIANS[key] = (_median_finite(tg.t1.values()), _median_finite(tg.t2.values()))
    m1, m2 = _MEDIANS[key]
    tmin = PRUNE["t_min_us"] * 1e-6
    t1, t2 = tg.t1.get(q, np.inf), tg.t2.get(q, np.inf)
    return bool((np.isfinite(m1) and t1 < max(tmin, PRUNE["t1_lt_median_frac"] * m1))
                or (np.isfinite(m2) and t2 < max(tmin, PRUNE["t2_lt_median_frac"] * m2)))


_MEDIANS: dict = {}


def prune(tg: T.Target) -> tuple[nx.Graph, dict]:
    g = tg.graph.copy()
    bad_q = sorted(q for q in g.nodes if tg.ro(q) > PRUNE["readout_gt"] or tg.e1q[q] >= PRUNE["sx_ge"]
                   or short_coherence(tg, q))
    bad_e = sorted(e for e in g.edges if tg.edge_err(*e) > PRUNE["e2q_gt"])
    g.remove_edges_from(bad_e)
    g.remove_nodes_from(bad_q)
    return g, {"qubits": bad_q, "edges": [list(e) for e in bad_e],
               "short_coherence": [q for q in bad_q if short_coherence(tg, q)],
               "thresholds": {k: v for k, v in PRUNE.items()}, "kept_qubits": g.number_of_nodes(),
               "kept_edges": g.number_of_edges()}


def available(g: nx.Graph, used: set[int], full: nx.Graph | None = None) -> nx.Graph:
    """Graph minus used qubits and their neighbours (the buffer that keeps regions at distance >= 2). Neighbours are
    taken in `full` (the unpruned coupling graph): a pruned coupler is still a physical coupler."""
    full = g if full is None else full
    block = set(used)
    for q in used:
        if q in full:
            block |= set(full[q])
    return g.subgraph([n for n in g.nodes if n not in block]).copy()


# ---------------------------------------------------------------------------------------------- builders
def path(g: nx.Graph, tg: T.Target, n: int, time_box: float = PATH_TIME_BOX_S) -> dict:
    """Cheapest simple path of n qubits by branch-and-bound (cost = sum of edge costs), time-boxed."""
    if n == 1:
        q = min(g.nodes, key=lambda x: (node_cost(tg, x), x)) if g.number_of_nodes() else None
        if q is None:
            raise Infeasible("path", n, 0)
        return {"nodes": [q], "edges": [], "cost": node_cost(tg, q), "complete_search": True}
    ec = {}
    for i, j in g.edges:
        ec[(i, j)] = ec[(j, i)] = edge_cost(tg, i, j)
    if not ec:
        raise Infeasible("path", n, 1 if g.number_of_nodes() else 0)
    cmin = min(ec.values())
    nb = {v: sorted(g[v], key=lambda w: (ec[(v, w)], w)) for v in g.nodes}
    best = {"cost": np.inf, "nodes": None}
    longest = [1]
    t0 = time.monotonic()
    timed_out = [False]

    def dfs(p: list[int], seen: set[int], cost: float) -> None:
        if timed_out[0]:
            return
        if len(p) > longest[0]:
            longest[0] = len(p)
        if len(p) == n:
            if cost < best["cost"]:
                best["cost"], best["nodes"] = cost, list(p)
            return
        if cost + (n - len(p)) * cmin >= best["cost"]:
            return
        if time.monotonic() - t0 > time_box:
            timed_out[0] = True
            return
        for w in nb[p[-1]]:
            if w not in seen:
                seen.add(w)
                p.append(w)
                dfs(p, seen, cost + ec[(p[-2], w)])
                p.pop()
                seen.remove(w)

    lim = sys.getrecursionlimit()
    sys.setrecursionlimit(max(lim, 10 * n + 1000))
    try:
        for s in sorted(g.nodes, key=lambda x: (node_cost(tg, x), x)):
            dfs([s], {s}, 0.0)
            if timed_out[0]:
                break
    finally:
        sys.setrecursionlimit(lim)
    if best["nodes"] is None:
        raise Infeasible("path", n, longest[0])
    nodes = best["nodes"]
    return {"nodes": nodes, "edges": [[a, b] for a, b in zip(nodes, nodes[1:])], "cost": float(best["cost"]),
            "complete_search": not timed_out[0]}


def bfs_tree(g: nx.Graph, tg: T.Target, n: int, root: int | None = None, by_cost: bool = False) -> dict:
    """Minimum-depth spanning tree on n qubits: whole BFS shells first, the cheapest nodes of the last shell, each
    node hung from its cheapest parent in the previous shell. Root = the node giving the smallest depth (ties: cost);
    by_cost: the root giving the cheapest tree (sum of edge costs = CZ + readout + sx errors), ties: depth."""
    comps = list(nx.connected_components(g))
    big = max((len(c) for c in comps), default=0)
    if n > big:
        raise Infeasible("bfs_tree", n, big)
    roots = [root] if root is not None else sorted(g.nodes)
    best = None
    for r in roots:
        dist = nx.single_source_shortest_path_length(g, r)
        if len(dist) < n:
            continue
        order = sorted(dist, key=lambda v: (dist[v], node_cost(tg, v), v))[:n]
        depth = dist[order[-1]]
        cost = sum(node_cost(tg, v) for v in order)
        inset = set(order)
        edges = []
        for v in order[1:]:
            par = min((u for u in g[v] if u in inset and dist[u] == dist[v] - 1), key=lambda u: (edge_cost(tg, u, v), u))
            edges.append([par, v])
        key = (sum(edge_cost(tg, a, b) for a, b in edges), depth, r) if by_cost else (depth, cost, r)
        if best is None or key < best[0]:
            best = (key, r, order, dist, edges)
    if best is None:
        raise Infeasible("bfs_tree", n, big)
    _, r, order, dist, edges = best
    return {"nodes": order, "edges": edges, "root": r, "depth": int(dist[order[-1]]),
            "cost": float(sum(edge_cost(tg, a, b) for a, b in edges))}


def patch(g: nx.Graph, tg: T.Target, n: int, centre: int | None = None) -> dict:
    """Connected patch of n qubits grown from the centre, shell by shell, cheapest first."""
    if g.number_of_nodes() == 0:
        raise Infeasible("patch", n, 0)
    comp = max(nx.connected_components(g), key=len)
    if n > len(comp):
        raise Infeasible("patch", n, len(comp))
    h = g.subgraph(comp)
    if centre is None:
        ecc = nx.eccentricity(h)
        centre = min(h.nodes, key=lambda v: (ecc[v], node_cost(tg, v), v))
    dist = nx.single_source_shortest_path_length(h, centre)
    region = [centre]
    inset = {centre}
    while len(region) < n:
        front = {w for v in region for w in h[v] if w not in inset}
        w = min(front, key=lambda x: (dist[x], node_cost(tg, x) + min(edge_cost(tg, x, v) for v in h[x] if v in inset), x))
        region.append(w)
        inset.add(w)
    sub = h.subgraph(region)
    return {"nodes": sorted(region), "edges": [sorted(e) for e in sub.edges], "centre": centre}


def free_qubits(g: nx.Graph, tg: T.Target, n: int) -> dict:
    """n cheapest qubits, pairwise non-adjacent (soma: no 2q gates at all; any n on an all-to-all target)."""
    a2a = bool(tg.meta.get("all_to_all"))
    chosen: list[int] = []
    for q in sorted(g.nodes, key=lambda x: (node_cost(tg, x), x)):
        if a2a or all(q not in g[c] for c in chosen):
            chosen.append(q)
            if len(chosen) == n:
                break
    if len(chosen) < n:
        raise Infeasible("free_qubits", n, len(chosen))
    return {"nodes": sorted(chosen), "edges": []}


def check_ancillas(g: nx.Graph, tg: T.Target, tree: dict, k: int, used: set[int]) -> list[dict]:
    """Big-Cats parity checks: a non-tree qubit a adjacent to two tree qubits i, j measures Z_i Z_j at the end.
    Picks up to k disjoint ancillas, cheapest first; each check uses 2 CX (i->a, j->a)."""
    tset = set(tree["nodes"])
    cands = []
    for a in g.nodes:
        if a in tset or a in used:
            continue
        nbt = sorted((v for v in g[a] if v in tset), key=lambda v: (edge_cost(tg, a, v), v))
        if len(nbt) >= 2:
            cands.append((edge_cost(tg, a, nbt[0]) + edge_cost(tg, a, nbt[1]), a, nbt[:2]))
    out, taken = [], set()
    for cost, a, (i, j) in sorted(cands):
        if a in taken or i in taken or j in taken:
            continue
        out.append({"ancilla": a, "pair": [i, j]})
        taken |= {a}
        if len(out) == k:
            break
    return out


def _tree_with_checks(avail: nx.Graph, tg: T.Target, build, n: int, k: int, within, g_pruned: nx.Graph,
                      used: set[int]) -> dict:
    """Tree of n certified qubits + up to k parity-check ancillas. Grows the tree on n + k qubits, takes outside
    ancillas first (adjacent to two tree qubits), then turns tree leaves that touch a second tree qubit into
    ancillas, and trims the costliest unused leaves back to n."""
    m = min(n + k, max((len(c) for c in nx.connected_components(avail)), default=0))
    if m < n:
        raise Infeasible("bfs_tree", n, m)
    tree = build(m)
    zone = available(g_pruned, used, nx.Graph() if tg.meta.get("all_to_all") else tg.graph)  # ancillas sit outside other regions' buffers
    if within is not None:
        zone = zone.subgraph([q for q in within if q in zone]).copy()
    chk = check_ancillas(zone, tg, tree, k, used)
    nodes = list(tree["nodes"])
    par = {c: p for p, c in tree["edges"]}
    children = {v: [c for c, p in par.items() if p == v] for v in nodes}
    pairs_q = {q for c in chk for q in c["pair"]}
    taken = {c["ancilla"] for c in chk}
    for leaf in sorted((v for v in nodes if not children[v] and v != tree["root"]),
                       key=lambda v: (node_cost(tg, v), v)):
        if len(chk) >= k or len(nodes) - 1 < n:
            break
        if leaf in pairs_q:
            continue
        other = sorted((j for j in avail[leaf] if j in nodes and j != par[leaf] and j not in taken),
                       key=lambda j: (edge_cost(tg, leaf, j), j))
        if not other:
            continue
        chk.append({"ancilla": leaf, "pair": [par[leaf], other[0]]})
        taken.add(leaf)
        pairs_q |= {par[leaf], other[0]}
        nodes.remove(leaf)
        children[par[leaf]].remove(leaf)
        del par[leaf]
    while len(nodes) > n:                                 # trim surplus leaves, costliest first
        leaves = [v for v in nodes if not children[v] and v != tree["root"] and v not in pairs_q]
        if not leaves:
            break
        v = max(leaves, key=lambda x: (node_cost(tg, x), x))
        nodes.remove(v)
        children[par[v]].remove(v)
        del par[v]
    dist = nx.single_source_shortest_path_length(avail.subgraph(nodes), tree["root"])
    return {"nodes": nodes, "edges": [[p, c] for c, p in par.items()], "root": tree["root"],
            "depth": int(max(dist.values())), "checks": chk[:k]}


# ---------------------------------------------------------------------------------------------- regions
def _region(name: str, family: str, role: str, nodes, edges, **extra) -> dict:
    return {"name": name, "family": family, "role": role, "qubits": [int(q) for q in nodes],
            "edges": [[int(a), int(b)] for a, b in edges]} | extra


def min_region_distance(g_full: nx.Graph, regions: dict) -> int:
    """Smallest graph distance between qubits of different region groups (spine+checks count as one group)."""
    group = {}
    for name, r in regions.items():
        if r["role"] == "buffer":
            continue
        gname = r.get("group", name)
        for q in r["qubits"]:
            group[q] = gname
    best = 10 ** 9
    names = sorted(set(group.values()))
    for a in names:
        src = [q for q, gname in group.items() if gname == a]
        dist = nx.multi_source_dijkstra_path_length(g_full, src)
        for q, gname in group.items():
            if gname != a and q in dist:
                best = min(best, dist[q])
    return best if best < 10 ** 9 else -1


def allocate(requests: list[dict], tg: T.Target, fit: bool = True) -> dict:
    """Allocate requests in order, each in the pruned graph minus earlier regions and their buffer.

    request: {name, family, kind: bfs_tree|path|patch|free, n, role, checks?: k, root?, by_cost?, centre?, within?}
    fit=True shrinks a request to the largest feasible size (recorded); fit=False raises Infeasible."""
    g_pruned, pinfo = prune(tg)
    used: set[int] = set()
    regions: dict[str, dict] = {}
    fitted = []
    for rq in requests:
        if rq.get("lattice") == "grid" and tg.meta.get("all_to_all"):
            # all-to-all target (helios-class): lattice families run on a virtual 7 x 14 grid embedding
            g_grid = virtual_grid(tg)
            avail = available(g_grid, used)
        else:
            # all-to-all: no coupler graph, so no neighbour buffer exists or is needed (regions only stay disjoint)
            avail = available(g_pruned, used, nx.Graph() if tg.meta.get("all_to_all") else tg.graph)
        if rq.get("within") is not None:
            avail = avail.subgraph([q for q in rq["within"] if q in avail]).copy()
        n = int(rq["n"])
        build = {"bfs_tree": lambda m: bfs_tree(avail, tg, m, rq.get("root"), bool(rq.get("by_cost"))),
                 "path": lambda m: path(avail, tg, m),
                 "patch": lambda m: patch(avail, tg, m, rq.get("centre")),
                 "free": lambda m: free_qubits(avail, tg, m)}[rq["kind"]]
        k = int(rq.get("checks", 0))
        if k and rq["kind"] == "bfs_tree":
            build0 = build
            build = lambda m: _tree_with_checks(avail, tg, build0, m, k, rq.get("within"), g_pruned, used)
        try:
            res = build(n)
        except Infeasible as e:
            if fit and rq.get("optional") and e.largest < rq.get("min_n", 1):
                fitted.append({"region": rq["name"], "requested": n, "got": 0})     # optional region dropped
                continue
            if not fit or e.largest < rq.get("min_n", 1):
                raise Infeasible(f"{rq['name']} ({rq['kind']})", n, e.largest) from None
            fitted.append({"region": rq["name"], "requested": n, "got": e.largest})
            n = e.largest
            res = build(n)
        reg = _region(rq["name"], rq["family"], rq["role"], res["nodes"], res["edges"],
                      **{k: res[k] for k in ("root", "depth", "centre") if k in res})
        if rq.get("group"):
            reg["group"] = rq["group"]
        regions[rq["name"]] = reg
        used |= set(res["nodes"])
        if k:
            chk = res["checks"]
            if len(chk) < k:
                fitted.append({"region": rq["name"] + ":checks", "requested": k, "got": len(chk)})
            regions[rq["name"] + "_checks"] = _region(
                rq["name"] + "_checks", rq["family"], "check", [c["ancilla"] for c in chk],
                [[i, c["ancilla"]] for c in chk for i in c["pair"]], checks=chk, group=rq.get("group", rq["name"]))
            regions[rq["name"]]["group"] = rq.get("group", rq["name"])
            used |= {c["ancilla"] for c in chk}
    n_used = len(used)
    buf = sorted({w for q in used for w in tg.graph[q] if w not in used})
    regions["buffer"] = _region("buffer", "-", "buffer", buf, [])
    return {"target": tg.name, "target_label": tg.label, "calibration_snapshot": tg.calibration,
            "pruned": pinfo, "regions": regions, "n_used": n_used, "fitted": fitted,
            "min_region_distance": (None if tg.meta.get("all_to_all") else min_region_distance(tg.graph, regions))}


def virtual_grid(tg: T.Target, ncol: int = 14) -> nx.Graph:
    """Square-lattice embedding (q = ncol * r + c) for lattice families on an all-to-all target."""
    g = nx.Graph()
    g.add_nodes_from(range(tg.n_qubits))
    for q in range(tg.n_qubits):
        if q % ncol < ncol - 1 and q + 1 < tg.n_qubits:
            g.add_edge(q, q + 1)
        if q + ncol < tg.n_qubits:
            g.add_edge(q, q + ncol)
    return g


# ---------------------------------------------------------------------------------------------- composite
def nighthawk_rows(rows) -> list[int]:
    """Nighthawk is a 12-row x 10-column square grid, qubit q = 10 * row + col."""
    return [10 * r + c for r in rows for c in range(10)]


def composite_requests(budget: int, tg: T.Target) -> list[dict]:
    """Plan §4 composite: spine + QCA + PMD with physical buffers."""
    from D_quantum_growth import pmd_bank

    L = pmd_bank.DEFAULT_PROCESS["L"]
    if tg.name == "nighthawk" and budget == 120:
        return [
            {"name": "spine", "family": "ghz-spine", "kind": "bfs_tree", "n": 36, "role": "certified", "checks": 4,
             "within": nighthawk_rows(range(0, 4)), "min_n": 6},
            {"name": "qca", "family": "ch-qca", "kind": "patch", "n": 50, "role": "active",
             "within": nighthawk_rows(range(5, 10)), "min_n": 6},
            {"name": "pmd0", "family": "pmd-bank", "kind": "path", "n": L + 1, "role": "active",
             "within": nighthawk_rows([11]), "min_n": 3},
        ]
    spine, checks, qca = {40: (14, 2, 12), 100: (48, 4, 30), 120: (60, 4, 40)}[budget]
    return [
        {"name": "spine", "family": "ghz-spine", "kind": "bfs_tree", "n": spine, "role": "certified",
         "checks": checks, "min_n": 6},
        {"name": "qca", "family": "ch-qca", "kind": "patch", "n": qca, "role": "active", "min_n": 6},
        {"name": "pmd0", "family": "pmd-bank", "kind": "path", "n": L + 1, "role": "active", "min_n": 3},
    ]


def composite(budget: int, target: str) -> dict:
    """Spine + QCA + PMD on one chip with physical buffers."""
    tg = T.get(target)
    out = allocate(composite_requests(budget, tg), tg)
    out |= {"budget": budget, "recipe": "composite"}
    return out
