"""P1 — Betweenness (Opatrný 1979). The ONLY per-problem math.

Ordering problem (certificate = a total order, feasible space = n!). Given
betweenness constraints, each `(a, b, c)` meaning "b lies strictly between a and
c", find a linear order satisfying all of them. Instances are generated from a
planted order π*, so a satisfying order exists (cost 0).

Verdict (measured by best_classical.py): a 2^n·poly subset DP over the placed set
exists ⇒ ordering problem COLLAPSES structurally.
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
    "id": "p1_betweenness",
    "name": "Betweenness",
    "citation": "Opatrný, 'Total Ordering Problem', SIAM J. Comput. 8(1):111–114, 1979",
    "hardness_assumption": "none — a 2^n·poly subset DP over the placed set exists",
    "best_classical_source": "subset DP over the placed prefix (2^n·poly)",
    "mechanism": "structural",
    "notes": "ordering (n!); collapses via 2^n placed-prefix DP (was predicted SURVIVES in the draft)",
}


@dataclass(frozen=True)
class Instance:
    n: int
    # each triple (a, b, c): "b strictly between a and c"
    triples: Tuple[Tuple[int, int, int], ...]


def generate(n: int, seed: int) -> Instance:
    rng = random.Random(seed * 2000 + n)
    perm = list(range(n))
    rng.shuffle(perm)  # planted order π*
    pos = [0] * n
    for p in range(n):
        pos[perm[p]] = p
    m = 2 * n  # number of constraints
    triples: List[Tuple[int, int, int]] = []
    seen: set[Tuple[int, int, int]] = set()
    attempts = 0
    while len(triples) < m and attempts < 50 * m:
        attempts += 1
        b = rng.randrange(n)
        a = rng.randrange(n)
        c = rng.randrange(n)
        if len({a, b, c}) != 3:
            continue
        # keep only constraints π* actually satisfies (b strictly between a,c)
        lo, hi = (pos[a], pos[c]) if pos[a] < pos[c] else (pos[c], pos[a])
        if not (lo < pos[b] < hi):
            continue
        key = (a, b, c) if a < c else (c, b, a)
        if key in seen:
            continue
        seen.add(key)
        triples.append((a, b, c))
    return Instance(n=n, triples=tuple(triples))


def cost(candidate: Tuple[int, ...], instance: Instance) -> float:
    """``candidate`` is a permutation of range(n) (element at each position).
    Cost = number of violated betweenness constraints."""
    n = instance.n
    pos = [0] * n
    for p in range(len(candidate)):
        pos[candidate[p]] = p
    viol = 0
    for a, b, c in instance.triples:
        lo, hi = (pos[a], pos[c]) if pos[a] < pos[c] else (pos[c], pos[a])
        if not (lo < pos[b] < hi):
            viol += 1
    return float(viol)


def enumerate(n: int) -> Iterable[Tuple[int, ...]]:
    return enumerate_space(n, KIND)


def to_qubo(instance: Instance) -> QUBO:
    """One-hot position vars x_{e,p} (element e at position p), index e*n+p:
    permutation one-hot penalties + a per-triple degree-2 coupling proxy. Used
    only for the FT resource estimate + hardware appendix."""
    n = instance.n
    linear: dict[int, float] = {}
    quadratic: dict[Tuple[int, int], float] = {}

    def idx(e: int, p: int) -> int:
        return e * n + p

    def add_quad(x: int, y: int, w: float) -> None:
        key = (x, y) if x < y else (y, x)
        quadratic[key] = quadratic.get(key, 0.0) + w

    for e in range(n):
        for p in range(n):
            linear[idx(e, p)] = linear.get(idx(e, p), 0.0) - 1.0
            for q in range(p + 1, n):
                add_quad(idx(e, p), idx(e, q), 2.0)  # one position per element
    for p in range(n):
        for e in range(n):
            for f in range(e + 1, n):
                add_quad(idx(e, p), idx(f, p), 2.0)  # one element per position
    # per-triple coupling proxy (degree-2 reward on the middle vs endpoints)
    for a, b, c in instance.triples:
        for p in range(n):
            add_quad(idx(b, p), idx(a, p), 0.5)
            add_quad(idx(b, p), idx(c, p), 0.5)

    return QUBO(linear=linear, quadratic=quadratic, num_vars=n * n, num_ancillas=0, degree=2)
