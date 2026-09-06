"""P2 — Numerical Matching with Target Sums. The ONLY per-problem math.

Assignment problem (certificate = a bijection X↔Y, feasible space = n!). Given
n numbers ``X``, n numbers ``Y`` and n target sums ``T``, find a permutation σ
with ``X[i] + Y[σ(i)] == T[i]`` for all i. A planted σ* guarantees the optimum
is 0 (feasible), so brute force finds it and the hunt's DP is exact.

Verdict (measured by best_classical.py): the O(2^n·n) bitmask assignment DP is a
2^{O(n)} classical algorithm ⇒ ordering/assignment problem COLLAPSES structurally
(√(n!) Grover is asymptotically above any 2^{c·n} DP).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from framework.bruteforce import enumerate_space

from problems._drivers import QUBO

KIND = "ordering"
SEARCH_SPACE_EXPR = "n!"

META = {
    "id": "p2_numerical_matching",
    "name": "Numerical Matching with Target Sums",
    "citation": "Garey & Johnson, Computers and Intractability, 1979 [SP17] "
    "(strongly NP-complete; no 1978 journal primary confirmed — cite the book)",
    "hardness_assumption": "none — best known is an O(2^n·n) bitmask assignment DP",
    "best_classical_source": "bitmask assignment DP (Bellman/Held–Karp style), O(2^n·n)",
    "mechanism": "structural",
    "notes": "assignment (n!); target penalty (Σ s·x − B)² reuses the number-partitioning form",
}


@dataclass(frozen=True)
class Instance:
    n: int
    X: Tuple[int, ...]
    Y: Tuple[int, ...]
    T: Tuple[int, ...]


def generate(n: int, seed: int) -> Instance:
    rng = random.Random(seed * 1000 + n)
    X = [rng.randint(1, 4 * n) for _ in range(n)]
    Y = [rng.randint(1, 4 * n) for _ in range(n)]
    sigma = list(range(n))
    rng.shuffle(sigma)  # planted feasible assignment σ*
    T = [X[i] + Y[sigma[i]] for i in range(n)]
    return Instance(n=n, X=tuple(X), Y=tuple(Y), T=tuple(T))


def cost(candidate: Tuple[int, ...], instance: Instance) -> float:
    """``candidate`` is a permutation of range(n): y-index assigned to each x.
    Cost = number of pairs whose sum misses its target (0 == perfect matching)."""
    X, Y, T = instance.X, instance.Y, instance.T
    return float(sum(1 for i in range(len(candidate)) if X[i] + Y[candidate[i]] != T[i]))


def enumerate(n: int) -> Iterable[Tuple[int, ...]]:
    return enumerate_space(n, KIND)


def to_qubo(instance: Instance) -> QUBO:
    """Assignment vars z_{i,j} (index i*n+j). Row/col one-hot penalties + the
    per-i sum-to-target penalty (Σ_j z_{i,j}(X_i+Y_j) − T_i)² — the
    number-partitioning penalty form. Coefficients are illustrative (unit
    penalty weight); used only for the FT resource estimate + hardware appendix.
    """
    n = instance.n
    X, Y, T = instance.X, instance.Y, instance.T
    linear: dict[int, float] = {}
    quadratic: dict[Tuple[int, int], float] = {}

    def idx(i: int, j: int) -> int:
        return i * n + j

    def add_lin(v: int, w: float) -> None:
        linear[v] = linear.get(v, 0.0) + w

    def add_quad(a: int, b: int, w: float) -> None:
        key = (a, b) if a < b else (b, a)
        quadratic[key] = quadratic.get(key, 0.0) + w

    # row one-hot (Σ_j z_ij − 1)^2 and col one-hot (Σ_i z_ij − 1)^2
    for i in range(n):
        for j in range(n):
            add_lin(idx(i, j), -1.0)
            for k in range(j + 1, n):
                add_quad(idx(i, j), idx(i, k), 2.0)
    for j in range(n):
        for i in range(n):
            add_lin(idx(i, j), -1.0)
            for k in range(i + 1, n):
                add_quad(idx(i, j), idx(k, j), 2.0)
    # target penalty (Σ_j z_ij (X_i+Y_j) − T_i)^2 per row
    for i in range(n):
        coeff = [X[i] + Y[j] for j in range(n)]
        for j in range(n):
            add_lin(idx(i, j), coeff[j] * coeff[j] - 2.0 * T[i] * coeff[j])
            for k in range(j + 1, n):
                add_quad(idx(i, j), idx(i, k), 2.0 * coeff[j] * coeff[k])

    return QUBO(linear=linear, quadratic=quadratic, num_vars=n * n, num_ancillas=0, degree=2)
