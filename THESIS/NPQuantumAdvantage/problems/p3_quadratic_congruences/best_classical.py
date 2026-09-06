"""P3 best_classical — the hunt: factor b + Tonelli–Shanks + CRT (AC-T1.5).

The algebraic structure kills the search: instead of scanning 2^n values of x we
factor b, take modular square roots of a modulo each prime power (Tonelli–Shanks),
combine by CRT, and check whether any root is < c. Its cost is governed by
factoring b (sub-exponential in the *bit-length* of b), NOT by 2^n — so the fitted
classical exponent c in 2^{c·n} is ≪ 0.5 ⇒ classify_subset ⇒ COLLAPSE (algebraic).

Uses `sympy` (OQ-3: an existing, vetted number-theory implementation preferred over
a hand-rolled one). ``work`` counts the modular operations the algebraic solver
performs — the empirical proxy whose slope in n stays far below 0.5.

Run: python -m problems.p3_quadratic_congruences.best_classical --seed 7
"""
from __future__ import annotations

from typing import Tuple

from sympy import factorint
from sympy.ntheory.residue_ntheory import sqrt_mod

from problems import _drivers
from problems.p3_quadratic_congruences import instance
from problems.p3_quadratic_congruences.instance import Instance


def algorithm(inst: Instance) -> Tuple[bool, int]:
    """Return (feasible?, work_units) via the algebraic solver."""
    a, b, c, n = inst.a, inst.b, inst.c, inst.n
    work = 0

    factors = factorint(b)
    work += sum(factors.values()) + len(factors) + b.bit_length()  # factoring proxy

    roots = sqrt_mod(a, b, all_roots=True)
    if roots is None:
        roots = []
    span = 1 << n
    feasible = False
    for r in roots:
        x = r % b
        while x < span:  # lift by +b into the [0, 2^n) window
            work += 1
            if x < c and (x * x - a) % b == 0:
                feasible = True
                break
            x += b
        if feasible:
            break
    return feasible, max(work, 1)


if __name__ == "__main__":
    _drivers.hunt_main(instance, algorithm)
