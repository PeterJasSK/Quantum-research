"""P1 best_classical — the hunt: 2^n placed-prefix DP (AC-T1.5).

Insert elements left to right; the state is the set already placed. A constraint
`(a, b, c)` ("b between a and c") is decided the moment its **middle** b is
inserted: it is satisfied iff exactly one of {a, c} is already placed (so b lands
strictly between them in insertion order), violated otherwise. This makes the
contribution a function of (mask, b) only — path-independent — so

    dp[mask ∪ {e}] = min over e of  dp[mask] + viol(mask, e)

is an exact minimum-violation DP in O(2^n · (n + m)). Its existence ⇒
classify_ordering ⇒ COLLAPSE (structural).

``work`` counts (state, transition) pairs — the empirical DP-size proxy.

Run: python -m problems.p1_betweenness.best_classical --seed 7
"""
from __future__ import annotations

from typing import List, Tuple

from problems import _drivers
from problems.p1_betweenness import instance
from problems.p1_betweenness.instance import Instance


def algorithm(inst: Instance) -> Tuple[int, int]:
    """Return (min_violations, work_units) via the placed-prefix DP."""
    n = inst.n
    # constraints indexed by their middle element b
    by_middle: List[List[Tuple[int, int]]] = [[] for _ in range(n)]
    for a, b, c in inst.triples:
        by_middle[b].append((a, c))

    INF = float("inf")
    dp = [INF] * (1 << n)
    dp[0] = 0
    work = 0
    for mask in range(1 << n):
        if dp[mask] == INF:
            continue
        for e in range(n):
            if mask & (1 << e):
                continue
            work += 1
            add = 0
            for a, c in by_middle[e]:
                in_a = (mask >> a) & 1
                in_c = (mask >> c) & 1
                if in_a + in_c != 1:  # b=e not strictly between a and c
                    add += 1
            nxt = mask | (1 << e)
            if dp[mask] + add < dp[nxt]:
                dp[nxt] = dp[mask] + add
    return int(dp[(1 << n) - 1]), max(work, 1)


if __name__ == "__main__":
    _drivers.hunt_main(instance, algorithm)
