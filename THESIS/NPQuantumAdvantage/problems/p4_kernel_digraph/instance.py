"""P4 — Kernel of a Digraph (Chvátal 1973 TR). The ONLY per-problem math. THE STAR.

Subset-search problem (certificate = a vertex subset S, feasible space = 2^n).
A *kernel* of a digraph is a set S that is both **independent** (no arc between two
members) and **absorbing/dominating** (every vertex outside S has an arc into S).
Grover over the 2^n subsets costs 2^{n/2}.

Verdict (MEASURED by best_classical.py — the borderline case): the independence
constraint pulls the best-classical exponent toward 0.288 (collapse), the
absorption/domination constraint toward 0.598 (survive). The exact exponent of the
branch-and-reduce solver decides which side of the √2 line this lands on — recorded
honestly, UNKNOWN if within eps of 0.5.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from framework.bruteforce import enumerate_space

from problems._drivers import QUBO

KIND = "subset"
SEARCH_SPACE_EXPR = "2^n"

META = {
    "id": "p4_kernel_digraph",
    "name": "Kernel of a Digraph",
    "citation": "Chvátal, tech report CRM-300, Univ. de Montréal, 1973 "
    "(technical report, not a journal); see also Fraenkel, Discrete Appl. Math. 3:257–262, 1981",
    "hardness_assumption": "measured — branch-and-reduce exact exponent vs the √2 line",
    "best_classical_source": "branch-on-vertex exact independent-and-absorbing-set solver (measured base)",
    "mechanism": "measure-and-conquer",
    "notes": "the star / borderline: independence pulls c→0.288, domination pulls c→0.598; measured c decides",
}


@dataclass(frozen=True)
class Instance:
    n: int
    arcs: Tuple[Tuple[int, int], ...]
    adj_masks: Tuple[int, ...]  # undirected neighbour mask (for independence)
    out_masks: Tuple[int, ...]  # out-neighbour mask (for absorption)


def generate(n: int, seed: int) -> Instance:
    rng = random.Random(seed * 4000 + n)
    arcs: List[Tuple[int, int]] = []
    adj = [0] * n
    out = [0] * n
    for u in range(n):
        for v in range(n):
            if u != v and rng.random() < 0.22:  # moderate density → kernels usually exist
                arcs.append((u, v))
                out[u] |= 1 << v
                adj[u] |= 1 << v
                adj[v] |= 1 << u
    return Instance(n=n, arcs=tuple(arcs), adj_masks=tuple(adj), out_masks=tuple(out))


def cost(candidate: int, instance: Instance) -> float:
    """``candidate`` is the subset bitmask S. Cost = independence violations
    (arcs inside S) + absorption violations (vertices outside S with no arc into S).
    Minimum 0 == a kernel."""
    s = candidate
    n = instance.n
    adj = instance.adj_masks
    out = instance.out_masks
    indep_viol = 0
    for v in range(n):
        if (s >> v) & 1:
            indep_viol += bin(adj[v] & s).count("1")
    indep_viol //= 2  # each intra-set edge counted from both endpoints
    absorb_viol = 0
    for w in range(n):
        if not ((s >> w) & 1):
            if out[w] & s == 0:  # w has no arc into S
                absorb_viol += 1
    return float(indep_viol + absorb_viol)


def enumerate(n: int) -> Iterable[int]:
    return enumerate_space(n, KIND)


def to_qubo(instance: Instance) -> QUBO:
    """Membership vars x_v (index v): independence penalty on intra-set arcs
    (quadratic) + a per-vertex absorption penalty proxy (linear). Sparse/local —
    the best hardware fit (drives the deferred appendix). Resource estimate only."""
    n = instance.n
    linear = {v: 1.0 for v in range(n)}  # absorption bias proxy
    quadratic: dict[Tuple[int, int], float] = {}
    for u, v in instance.arcs:
        key = (u, v) if u < v else (v, u)
        quadratic[key] = quadratic.get(key, 0.0) + 2.0  # independence penalty
    return QUBO(linear=linear, quadratic=quadratic, num_vars=n, num_ancillas=0, degree=2)
