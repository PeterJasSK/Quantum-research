"""P5 — Minimum Linear Arrangement (MinLA). The ONLY per-problem math.

Ordering problem (certificate = a vertex ordering, feasible space = n!). Given a
graph, place the vertices on a line (a permutation) minimising the total edge
stretch Σ_{(u,v)∈E} |pos(u) − pos(v)|.

Verdict (measured by best_classical.py): the O*(2^n) Bellman–Held–Karp DP (sum of
prefix cuts) is a 2^{O(n)} classical algorithm ⇒ ordering problem COLLAPSES
structurally.
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
    "id": "p5_minla",
    "name": "Minimum Linear Arrangement",
    "citation": "Garey, Johnson, Stockmeyer, 'Some Simplified NP-Complete Graph "
    "Problems', Theoret. Comput. Sci. 1(3):237–267, 1976",
    "hardness_assumption": "none — best known is the O*(2^n) Bellman–Held–Karp DP",
    "best_classical_source": "Bellman–Held–Karp prefix-cut DP, O*(2^n)",
    "mechanism": "structural",
    "notes": "ordering (n!); total cost = Σ prefix cuts ⇒ 2^n cut DP collapses it",
}


@dataclass(frozen=True)
class Instance:
    n: int
    edges: Tuple[Tuple[int, int], ...]


def generate(n: int, seed: int) -> Instance:
    rng = random.Random(seed * 3000 + n)
    edges: List[Tuple[int, int]] = []
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < 0.35:  # sparse random graph
                edges.append((u, v))
    if not edges:  # guarantee at least one edge so cost is non-trivial
        edges.append((0, n - 1))
    return Instance(n=n, edges=tuple(edges))


def cost(candidate: Tuple[int, ...], instance: Instance) -> float:
    """``candidate`` is a permutation of range(n) (vertex at each position).
    Cost = total edge stretch Σ |pos(u) − pos(v)|."""
    n = instance.n
    pos = [0] * n
    for p in range(len(candidate)):
        pos[candidate[p]] = p
    return float(sum(abs(pos[u] - pos[v]) for u, v in instance.edges))


def enumerate(n: int) -> Iterable[Tuple[int, ...]]:
    return enumerate_space(n, KIND)


def to_qubo(instance: Instance) -> QUBO:
    """One-hot position vars x_{v,p} (index v*n+p): permutation one-hot penalties
    + tabulated |p−q| edge couplings. Resource estimate / hardware appendix only."""
    n = instance.n
    linear: dict[int, float] = {}
    quadratic: dict[Tuple[int, int], float] = {}

    def idx(v: int, p: int) -> int:
        return v * n + p

    def add_quad(x: int, y: int, w: float) -> None:
        key = (x, y) if x < y else (y, x)
        quadratic[key] = quadratic.get(key, 0.0) + w

    for v in range(n):
        for p in range(n):
            linear[idx(v, p)] = linear.get(idx(v, p), 0.0) - 1.0
            for q in range(p + 1, n):
                add_quad(idx(v, p), idx(v, q), 2.0)
    for p in range(n):
        for v in range(n):
            for w in range(v + 1, n):
                add_quad(idx(v, p), idx(w, p), 2.0)
    for u, v in instance.edges:
        for p in range(n):
            for q in range(n):
                if p != q:
                    add_quad(idx(u, p), idx(v, q), float(abs(p - q)))

    return QUBO(linear=linear, quadratic=quadratic, num_vars=n * n, num_ancillas=0, degree=2)
