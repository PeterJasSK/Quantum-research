"""AC-T0.3 — the generic exhaustive-search template.

Generalises the POC's ``brute_force(n)`` (which counted every ``verify()`` call)
into a ``cost``-through-a-counter minimiser. The classical call count must equal
``|S|`` EXACTLY — that is the ``log2`` intercept the theorem axis relies on
(slope 1.0 classical).
"""
from __future__ import annotations

from itertools import permutations
from typing import Callable, Iterable, Iterator, Tuple, TypeVar

from .grover_min import KIND
from .oracle import OracleCounter

C = TypeVar("C")


def brute_force_min(
    candidates: Iterable[C],
    cost: Callable[[C], float],
    counter: OracleCounter,
) -> Tuple[C, float, int]:
    """Exhaustive minimiser. Evaluates ``cost`` through ``counter`` for every
    candidate and returns ``(argmin, min_cost, counter.count)``.

    ``counter`` is NOT reset here — the caller resets between sweep points so the
    tally reflects exactly the evaluations of this run.
    """
    counted_cost = counter.wrap(cost)
    best_candidate: C | None = None
    best_cost = float("inf")
    for candidate in candidates:
        value = counted_cost(candidate)
        if value < best_cost:
            best_cost = value
            best_candidate = candidate
    if best_candidate is None:
        raise ValueError("brute_force_min: empty candidate space")
    return best_candidate, best_cost, counter.count


def enumerate_space(n: int, kind: KIND) -> Iterator[object]:
    """Yield every candidate: all ``2**n`` int bitmasks (subset) or all ``n!``
    permutations of ``range(n)`` (ordering). Yields exactly ``|S|`` candidates.
    """
    if kind == "subset":
        return iter(range(1 << n))
    if kind == "ordering":
        return permutations(range(n))
    raise ValueError(f"unknown kind {kind!r}; expected 'subset' or 'ordering'")
