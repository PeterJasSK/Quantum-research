r"""P5 best_classical — the hunt: O*(2^n) Bellman–Held–Karp prefix-cut DP (AC-T1.5).

The total linear-arrangement cost equals the sum over prefixes of the cut size:
    Σ_{(u,v)∈E} |pos(u)−pos(v)| = Σ_{k=1}^{n-1} cut(P_k),
where P_k is the set of the first k placed vertices and cut(S) = #edges with
exactly one endpoint in S. So

    dp[mask] = cut(mask) + min over v∈mask of dp[mask \ {v}]

(cut(mask) counted for |mask| = 1..n-1) is an exact O*(2^n) DP. Its existence ⇒
classify_ordering ⇒ COLLAPSE (structural).

``work`` counts (state, transition) pairs — the empirical DP-size proxy.

Run: python -m problems.p5_minla.best_classical --seed 7
"""
from __future__ import annotations

from typing import List, Tuple

from problems import _drivers
from problems.p5_minla import instance
from problems.p5_minla.instance import Instance


def _cut(mask: int, adj: List[int], n: int) -> int:
    """#edges with exactly one endpoint inside ``mask``."""
    total = 0
    for v in range(n):
        if mask & (1 << v):
            total += bin(adj[v] & ~mask).count("1")  # neighbours outside mask
    return total


def algorithm(inst: Instance) -> Tuple[int, int]:
    """Return (min_total_stretch, work_units) via the prefix-cut DP."""
    n = inst.n
    adj = [0] * n
    for u, v in inst.edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u

    INF = float("inf")
    dp = [INF] * (1 << n)
    dp[0] = 0
    full = (1 << n) - 1
    work = 0
    for mask in range(1, 1 << n):
        size = bin(mask).count("1")
        cut = 0 if size == n else _cut(mask, adj, n)
        best = INF
        for v in range(n):
            if mask & (1 << v):
                work += 1
                prev = dp[mask ^ (1 << v)]
                if prev + cut < best:
                    best = prev + cut
        dp[mask] = best
    return int(dp[full]), max(work, 1)


if __name__ == "__main__":
    _drivers.hunt_main(instance, algorithm)
