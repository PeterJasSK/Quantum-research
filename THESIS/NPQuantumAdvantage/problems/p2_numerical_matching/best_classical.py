"""P2 best_classical — the hunt: O(2^n·n) bitmask assignment DP (AC-T1.5).

Assign X[0..n-1] in order; DP state = subset of Y-indices already consumed.
``dp[mask]`` is reachable iff some feasible partial assignment uses exactly the
Y-indices in ``mask`` for the first ``popcount(mask)`` X's. Feasibility is the
existence of a full mask (all Y used) that is reachable. This is a 2^{O(n)}
classical algorithm ⇒ classify_ordering ⇒ COLLAPSE (structural).

``work`` counts (state, transition) pairs examined — the empirical proxy whose
fit diagnoses the DP's n-exponent (~1.0; the mere existence decides the verdict).

Run: python -m problems.p2_numerical_matching.best_classical --seed 7
"""
from __future__ import annotations

from typing import Tuple

from problems import _drivers
from problems.p2_numerical_matching import instance
from problems.p2_numerical_matching.instance import Instance


def algorithm(inst: Instance) -> Tuple[bool, int]:
    """Return (feasible?, work_units). Bitmask assignment DP."""
    n = inst.n
    X, Y, T = inst.X, inst.Y, inst.T
    full = (1 << n) - 1
    reachable = [False] * (1 << n)
    reachable[0] = True
    work = 0
    for mask in range(1 << n):
        if not reachable[mask]:
            continue
        i = bin(mask).count("1")  # next X index to place
        if i == n:
            continue
        for j in range(n):
            if mask & (1 << j):
                continue
            work += 1  # one (state, transition) examined
            if X[i] + Y[j] == T[i]:
                reachable[mask | (1 << j)] = True
    return reachable[full], max(work, 1)


if __name__ == "__main__":
    _drivers.hunt_main(instance, algorithm)
