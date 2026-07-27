"""Jain's fairness index (P4, AC-5) and polarization index (plan-8, OQ8-1)."""
from __future__ import annotations

from typing import Sequence


def jains_index(values: Sequence[float]) -> float:
    """`(sum(x))**2 / (n * sum(x**2))`. Returns `1.0` for the all-zero
    vector (no traffic = trivially fair, plan-4 Design) so an idle poll
    never divides by zero."""
    n = len(values)
    if n == 0:
        return 1.0
    total = sum(values)
    if total == 0:
        return 1.0
    sum_sq = sum(v * v for v in values)
    return (total**2) / (n * sum_sq)


def polarization_index(values: Sequence[float]) -> float:
    """`max(values) / mean(values)` (OQ8-1) -- scale-free (epic s3.4). `1.0`
    for the empty or all-zero vector, mirroring `jains_index`'s guard."""
    n = len(values)
    if n == 0:
        return 1.0
    total = sum(values)
    if total == 0:
        return 1.0
    mean = total / n
    return max(values) / mean
