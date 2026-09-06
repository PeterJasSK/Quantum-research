"""P4 best_classical — the hunt: branch-on-vertex exact kernel solver (AC-T1.5).

The star / borderline case. We search for the minimum-violation independent-and-
absorbing set by branch-and-bound: each vertex is included or excluded, inclusion
allowed only when it keeps the set independent (hard constraint); the objective is
the number of unabsorbed outside vertices. The measured base of the recursion-node
count is the best-classical exponent c (fitted over the n-sweep). classify_subset
then places it against the √2 line — SURVIVES if c > 0.5, COLLAPSES if c < 0.5,
UNKNOWN within eps.

OQ-3: a hand-rolled branch-and-reduce is used here because no drop-in library exact
solver for the independent-and-absorbing (kernel) set was available; the base is
measured empirically and reported honestly.

``work`` == recursion nodes.

Run: python -m problems.p4_kernel_digraph.best_classical --seed 7
"""
from __future__ import annotations

from typing import List, Tuple

from problems import _drivers
from problems.p4_kernel_digraph import instance
from problems.p4_kernel_digraph.instance import Instance


def algorithm(inst: Instance) -> Tuple[int, int]:
    """Return (min_violations, recursion_nodes)."""
    n = inst.n
    adj = inst.adj_masks
    out = inst.out_masks
    best = [n + 1]
    nodes = [0]

    def absorb_viol(s: int) -> int:
        v = 0
        for w in range(n):
            if not ((s >> w) & 1) and (out[w] & s) == 0:
                v += 1
        return v

    def rec(i: int, s: int) -> None:
        nodes[0] += 1
        if i == n:
            val = absorb_viol(s)
            if val < best[0]:
                best[0] = val
            return
        # exclude vertex i
        rec(i + 1, s)
        # include vertex i iff it keeps S independent
        if (adj[i] & s) == 0:
            rec(i + 1, s | (1 << i))

    rec(0, 0)
    return best[0], max(nodes[0], 1)


if __name__ == "__main__":
    _drivers.hunt_main(instance, algorithm)
