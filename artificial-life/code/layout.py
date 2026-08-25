#!/usr/bin/env python3
"""
layout.py — pick a low-error, SWAP-free qubit chain from a backend's LIVE
calibration (free metadata, no QPU cost).

qtree.py entangles an OPEN chain: cx(i, i+1) for i in 0..n-2. For that to map
without SWAPs, physical qubit_list[i] and qubit_list[i+1] must be coupled. So we
need a length-n simple path through the coupling graph, avoiding dead qubits and
minimising 2-qubit + readout + sx error along it.

Calibration drifts daily -- re-pick before every real run rather than hardcoding
a stale list.
"""

from __future__ import annotations

import time
from typing import Any

# qubits with a broken single-qubit gate or hopeless readout: never use
DEAD_SX = 0.5
DEAD_RO = 0.25
# two-qubit edges worse than this are unusable (dead/1.0-error gates); never walk them
DEAD_EDGE = 0.10


def _pull(backend: Any):
    tgt = backend.target
    nq = backend.num_qubits
    two = [g for g in ("cz", "ecr", "cx") if g in tgt.operation_names]
    edge: dict[frozenset, float] = {}
    for g in two:
        for qargs, props in tgt[g].items():
            if not qargs or len(qargs) != 2:
                continue
            e = getattr(props, "error", None)
            if e is None:
                continue
            k = frozenset(qargs)
            if k not in edge or e < edge[k]:
                edge[k] = e

    def one(name, q):
        try:
            return getattr(tgt[name][(q,)], "error", None)
        except Exception:
            return None

    ro = {q: (one("measure", q) or 0.0) for q in range(nq)}
    sx = {q: (one("sx", q) or 0.0) for q in range(nq)}
    return nq, edge, ro, sx


def best_chain(backend: Any, n: int, time_budget: float = 40.0
               ) -> tuple[list[int], dict]:
    """Return (qubit_list of length n, stats). Raises if no length-n chain."""
    nq, edge, ro, sx = _pull(backend)
    dead = {q for q in range(nq) if sx[q] >= DEAD_SX or ro[q] >= DEAD_RO}

    adj: dict[int, set] = {q: set() for q in range(nq)}
    for k in edge:
        a, b = tuple(k)
        if a in dead or b in dead:
            continue
        if edge[k] >= DEAD_EDGE:          # skip dead/1.0-error 2q gates entirely
            continue
        adj[a].add(b)
        adj[b].add(a)

    pen = lambda q: ro[q] + sx[q]
    ecost = lambda a, b: edge[frozenset((a, b))] + 0.5 * (pen(a) + pen(b))
    live = [q for q in range(nq) if q not in dead]

    longest: list[int] = []          # longest chain seen (for the failure diagnostic)
    best_chain_n: list[int] = []      # cheapest length-n chain found so far
    best_cost = float("inf")
    t_end = time.time() + time_budget

    import sys
    sys.setrecursionlimit(10000)

    def dfs(cur, used, path, cost):
        nonlocal longest, best_chain_n, best_cost
        if time.time() > t_end:
            return
        if len(path) > len(longest):
            longest = path[:]
        if cost >= best_cost:            # branch-and-bound: can't beat the incumbent n-chain
            return
        if len(path) >= n:
            best_chain_n, best_cost = path[:n], cost
            return
        for nb in sorted((x for x in adj[cur] if x not in used),
                         key=lambda x: ecost(cur, x)):
            used.add(nb); path.append(nb)
            dfs(nb, used, path, cost + ecost(cur, nb))
            path.pop(); used.discard(nb)
            if time.time() > t_end:
                return

    # search from every live seed, cheapest-readout first; keep the min-cost n-chain
    for seed in sorted(live, key=pen):
        if time.time() > t_end:
            break
        dfs(seed, {seed}, [seed], 0.0)

    if not best_chain_n:
        raise RuntimeError(
            f"no clean SWAP-free chain of {n} qubits on {backend.name} "
            f"(longest found {len(longest)}; edges >= {DEAD_EDGE} 2q-err pruned); "
            f"dead={sorted(dead)}. Lower genome N_SLOTS so N_BITS <= {len(longest)}, "
            f"or pin a better-calibrated --backend.")

    chain = best_chain_n[:n]
    e2 = [edge[frozenset((chain[i], chain[i + 1]))] for i in range(n - 1)]
    stats = {
        "dead_avoided": sorted(dead),
        "twoq_err_mean": round(sum(e2) / len(e2), 5),
        "twoq_err_max": round(max(e2), 5),
        "readout_max": round(max(ro[q] for q in chain), 5),
        "sx_max": round(max(sx[q] for q in chain), 6),
    }
    return chain, stats
