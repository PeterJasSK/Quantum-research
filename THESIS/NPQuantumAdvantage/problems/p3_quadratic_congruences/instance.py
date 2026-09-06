"""P3 — Quadratic Congruences (Manders–Adleman 1978). The ONLY per-problem math.

Subset-search problem over the bits of x: given (a, b, c), decide whether there
exists x < c with x² ≡ a (mod b). The certificate is the n-bit integer x, so the
feasible space is 2^n and Grover costs 2^{n/2}.

Verdict (measured by best_classical.py): factoring b + Tonelli–Shanks + CRT solves
it in time that does NOT scale like 2^{c·n} in the search-space bit-count n — the
classical exponent c ≪ 0.5 ⇒ COLLAPSE (algebraic). The genuine quantum win here is
Shor's factoring, not Grover — the "where Grover does NOT win" exemplar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sympy import nextprime

from framework.bruteforce import enumerate_space
from framework.resources import quadratization_ancillas

from problems._drivers import QUBO

KIND = "subset"
SEARCH_SPACE_EXPR = "2^n"

META = {
    "id": "p3_quadratic_congruences",
    "name": "Quadratic Congruences",
    "citation": "Manders & Adleman, 'NP-Complete Decision Problems for Binary "
    "Quadratics', J. Comput. Syst. Sci. 16(2):168–184, 1978",
    "hardness_assumption": "none — sub-exponential (factor b + Tonelli–Shanks + CRT)",
    "best_classical_source": "factor b → Tonelli–Shanks per prime power → CRT (sub-exponential)",
    "mechanism": "algebraic",
    "notes": "the real quantum win is Shor (factoring), not Grover; c ≪ 0.5, algebraic collapse",
}


@dataclass(frozen=True)
class Instance:
    n: int
    a: int
    b: int
    c: int
    x_star: int


def generate(n: int, seed: int) -> Instance:
    # b = p·q with p,q primes near 2^{n/2}, seeded deterministically off (seed, n)
    base = 1 << ((n + 1) // 2)
    p = int(nextprime(base + (seed * 7 + n) % base))
    q = int(nextprime(p + 1 + (seed * 13 + n) % base))
    b = p * q
    span = 1 << n
    c = max(2, (3 * span) // 4)  # a real "x < c" constraint (not vacuous)
    x_star = (seed * 2654435761 + 1) % c  # planted solution < c
    a = (x_star * x_star) % b
    return Instance(n=n, a=a, b=b, c=c, x_star=x_star)


def cost(candidate: int, instance: Instance) -> float:
    """``candidate`` is the integer x (0..2^n−1). Cost = (x² ≢ a mod b) + (x ≥ c),
    minimum 0 at a solution below c."""
    x = candidate
    viol = 0
    if (x * x - instance.a) % instance.b != 0:
        viol += 1
    if x >= instance.c:
        viol += 1
    return float(viol)


def enumerate(n: int) -> Iterable[int]:
    return enumerate_space(n, KIND)


def to_qubo(instance: Instance) -> QUBO:
    """HUBO: x = Σ 2^i x_i; penalty (x² − a − b·t)² is quartic ⇒ quadratization
    ancillas (framework.resources.quadratization_ancillas). Returned as a QUBO
    dataclass with degree=4; used for the FT resource estimate only (P3 is the
    algebraic-collapse case that pays the quadratization overhead even in FT)."""
    n = instance.n
    linear = {i: float(1 << i) for i in range(n)}  # bit weights (token map)
    quadratic: dict[tuple[int, int], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            quadratic[(i, j)] = float((1 << i) * (1 << j))
    n_terms = n * n
    ancillas = quadratization_ancillas(4, n_terms)
    return QUBO(linear=linear, quadratic=quadratic, num_vars=n, num_ancillas=ancillas, degree=4)
