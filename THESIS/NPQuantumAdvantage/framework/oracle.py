"""AC-T0.1 — the single oracle-call counter.

The whole epic measures quantum advantage in the *query model*: the cost of a
search is the number of times the cost/verifier oracle is evaluated, nothing
else. This module is the one place that count is kept, so classical and quantum
arms of every problem share an identical, auditable tally.

Contract
--------
- Exactly ONE increment per cost/verifier evaluation.
- Both files of every problem (``classical_bruteforce.py`` /
  ``quantum_grover.py``) share ONE ``OracleCounter`` instance per run.
- ``.reset()`` zeroes it between ``n`` points in a sweep.

Claim discipline: the count is the advantage number (query model . over brute
force . quadratic . NOT wall-clock). No wall-clock timing lives here.
"""
from __future__ import annotations

import functools
from typing import Callable, TypeVar

T = TypeVar("T")


class OracleCounter:
    """A tally of cost-oracle evaluations.

    Wrap any ``cost(candidate) -> float`` with :meth:`wrap` (or the module-level
    :func:`counted` decorator) so every call bumps :attr:`count` by exactly one
    and forwards args/result unchanged.
    """

    def __init__(self) -> None:
        self.count: int = 0

    def reset(self) -> None:
        """Zero the tally (call between ``n`` points in a sweep)."""
        self.count = 0

    def wrap(self, fn: Callable[..., T]) -> Callable[..., T]:
        """Return a wrapper that increments :attr:`count` once per call and
        forwards ``*args`` / ``**kwargs`` and the return value unchanged."""

        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> T:
            self.count += 1
            return fn(*args, **kwargs)

        return wrapper


def counted(counter: OracleCounter) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator form of :meth:`OracleCounter.wrap` for module-level oracles.

    Example::

        c = OracleCounter()

        @counted(c)
        def cost(x: int) -> float:
            ...
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        return counter.wrap(fn)

    return decorator
