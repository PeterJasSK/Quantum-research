"""AC-T0.5 — the √2 classifier (two branches).

The spine of the whole epic in code. Grover's subset exponent is fixed at 0.5
(base ``2^0.5 = sqrt(2)``), so for subset problems:

    SURVIVES  <=>  best-known-classical exponent c > 0.5
    COLLAPSES <=>  c <= 0.5   (a classical algorithm already runs at/below 2^{n/2})

For ordering/assignment problems the quantum cost is
``sqrt(n!) = 2^{0.5*log2(n!)}`` — its n-exponent GROWS, so it is asymptotically
above ``2^{c*n}`` for ANY finite ``c``. Hence an ordering problem COLLAPSES the
moment any ``2^{O(n)}`` classical algorithm exists (essentially always: a
Held–Karp / bitmask DP); it survives only if the best known is ``Theta(n!)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

Mechanism = Literal["structural", "measure-and-conquer", "algebraic"]


class Verdict(Enum):
    """Where a problem lands relative to the √2 line."""

    SURVIVES = "SURVIVES"
    COLLAPSES = "COLLAPSES"
    UNKNOWN = "UNKNOWN"


@dataclass
class ClassifyResult:
    """A verdict plus its distance to the line and a caller-filled mechanism slot."""

    verdict: Verdict
    margin_to_line: Optional[float]  # c - 0.5 (subset); None for ordering
    mechanism: Optional[Mechanism] = None


def classify_subset(c_classical: float, *, eps: float = 1e-6) -> ClassifyResult:
    """Subset branch: SURVIVES if ``c > 0.5 + eps``, COLLAPSES if
    ``c < 0.5 - eps``, else UNKNOWN (on the line within tolerance).

    ``margin_to_line = c_classical - 0.5``.
    """
    margin = c_classical - 0.5
    if c_classical > 0.5 + eps:
        verdict = Verdict.SURVIVES
    elif c_classical < 0.5 - eps:
        verdict = Verdict.COLLAPSES
    else:
        verdict = Verdict.UNKNOWN
    return ClassifyResult(verdict=verdict, margin_to_line=margin)


def classify_ordering(
    has_subexp_classical: bool,
    classical_n_exponent: Optional[float] = None,
) -> ClassifyResult:
    """Ordering branch: COLLAPSES if a ``2^{O(n)}`` classical algorithm exists
    (``has_subexp_classical`` True — i.e. any Held–Karp / bitmask DP), because
    ``sqrt(n!) > 2^{c*n}`` for any finite ``c``. Otherwise the best known is
    ``Theta(n!)`` and the verdict is UNKNOWN (survivor only under an explicit
    "no sub-factorial algorithm" assumption the caller must state).

    ``classical_n_exponent`` is diagnostic (the constant of the ``2^{O(n)}`` DP,
    e.g. 1.0 for Held–Karp); it does not change the branch — the mere existence
    of the DP decides.
    """
    if has_subexp_classical:
        return ClassifyResult(
            verdict=Verdict.COLLAPSES,
            margin_to_line=None,
            mechanism="structural",
        )
    return ClassifyResult(verdict=Verdict.UNKNOWN, margin_to_line=None)
