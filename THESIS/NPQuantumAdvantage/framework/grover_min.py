"""AC-T0.2 — the ideal Dürr–Høyer / Grover query-count engine (no statevector).

This is the Python SOURCE OF TRUTH the vendored JS mirror (``web/lib/grover_count.js``)
parities against. Keep the integer/float arithmetic simple and portable (plain
``math``, no numpy) so JavaScript reproduces it byte-for-byte.

The theorem (undeniable half of the epic)
-----------------------------------------
Grover search over a size-``N`` space with ``M`` marked items costs
``k = floor((pi/4)*sqrt(N/M))`` oracle calls; Dürr–Høyer (1996) minimum-finding
costs ``O(sqrt(N))`` calls. BBBV (1997) proves ``Omega(sqrt(N))`` is optimal in
the query model — a QUADRATIC speedup over the classical ``N``, unconditional.

Claim discipline (four qualifiers, no exceptions):
    query model . over brute force . quadratic . NOT wall-clock.

The c_dh intercept is NOT a result
----------------------------------
Dürr–Høyer prove an upper bound of ``<= 22.5*sqrt(N)`` expected oracle calls.
The ``c_dh = 1.3`` default here is the illustrative practical constant matching
the POC — it shifts the *intercept* of the log-log line, never the *slope*.
ONLY the exponent (0.5) is the scientific claim; ``c_dh`` is exposed precisely so
the intercept is never mistaken for a result.
"""
from __future__ import annotations

from math import factorial, floor, pi, sqrt
from typing import Literal

KIND = Literal["subset", "ordering"]
MODE = Literal["search", "min"]


def search_space_size(n: int, kind: KIND) -> int:
    """Feasible search-space size ``|S|``: ``2**n`` (subset) or ``n!`` (ordering)."""
    if kind == "subset":
        return 2 ** n
    if kind == "ordering":
        return factorial(n)
    raise ValueError(f"unknown kind {kind!r}; expected 'subset' or 'ordering'")


def grover_iterations(N: int, M: int) -> int:
    """Exact optimal Grover iteration count for ``M`` marked items in a space of
    size ``N`` — one iteration == one oracle call.

    ``k = floor((pi/4)*sqrt(N/max(M,1)))``, returned as ``max(k, 1)`` for
    ``M >= 1`` (at least one query is needed), ``0`` for ``M == 0`` (nothing to
    find).
    """
    if M <= 0:
        return 0
    k = floor((pi / 4) * sqrt(N / M))
    return max(k, 1)


def durr_hoyer_expected_queries(N: int, *, c_dh: float = 1.3) -> float:
    """Expected total oracle calls for quantum minimum-finding over ``N`` items,
    modelled as ``c_dh * sqrt(N)``.

    Dürr–Høyer (1996) prove an upper bound ``<= 22.5*sqrt(N)``; ``c_dh = 1.3`` is
    the illustrative practical constant matching the POC. Only the exponent (0.5)
    is the claim — ``c_dh`` moves the intercept, never the slope.
    """
    return c_dh * sqrt(N)


def expected_queries(n: int, kind: KIND, marked: int = 1, mode: MODE = "min") -> float:
    """Single entry point every ``quantum_grover.py`` calls.

    Dispatches over ``search_space_size(n, kind)``:
      - ``mode="search"`` -> :func:`grover_iterations` (find any of ``marked``),
      - ``mode="min"``    -> :func:`durr_hoyer_expected_queries` (minimum-finding).
    """
    N = search_space_size(n, kind)
    if mode == "search":
        return float(grover_iterations(N, marked))
    if mode == "min":
        return durr_hoyer_expected_queries(N)
    raise ValueError(f"unknown mode {mode!r}; expected 'search' or 'min'")
