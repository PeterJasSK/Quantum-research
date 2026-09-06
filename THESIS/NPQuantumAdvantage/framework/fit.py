"""AC-T0.4 — the exponent fitter (keeps the two axes distinct).

Two numbers come out of one sweep, and conflating them was the flaw the epic §6
spine corrects:

  * ``slope_vs_logspace`` — THEOREM axis. Least-squares slope of ``log2(calls)``
    vs ``log2(|S|)``. Expect ~1.0 classical / ~0.5 quantum for EVERY problem
    regardless of type. This is the quadratic query speedup, proven by counting.
  * ``exponent_in_n`` — VERDICT axis. Slope of ``log2(calls)`` vs ``n``, i.e. the
    ``c`` in ``2^{c*n}``. A clean constant for subset problems; for ORDERING
    problems it is diagnostic only, since the true n-exponent grows
    (``0.5*log2(n!)/n ~ 0.5*log2 n``). Reading it as a constant there triggers a
    warning.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from math import log2
from typing import List

import numpy as np

from .grover_min import KIND


@dataclass
class FitResult:
    """Both-axes fit of a single arm's oracle-call sweep."""

    slope_vs_logspace: float  # theorem axis: log2(calls) vs log2(|S|)
    r2_vs_logspace: float
    exponent_in_n: float      # verdict axis: log2(calls) vs n (c in 2^{c*n})
    r2_in_n: float


def _fit_line(x: List[float], y: List[float]) -> tuple[float, float]:
    """Return (slope, R^2) of a degree-1 least-squares fit of ``y`` on ``x``."""
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    slope, intercept = np.polyfit(xa, ya, 1)
    pred = slope * xa + intercept
    ss_res = float(np.sum((ya - pred) ** 2))
    ss_tot = float(np.sum((ya - ya.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(slope), r2


def fit(
    ns: List[int],
    calls: List[float],
    space_sizes: List[int],
    *,
    kind: KIND = "subset",
) -> FitResult:
    """Fit both axes for one arm.

    ``kind`` (OQ-1: added beyond the epic's bare signature so the AC-T0.4 warning
    is possible) drives the ordering-diagnostic warning: when ``kind=="ordering"``
    the ``exponent_in_n`` field is a growing quantity, not a constant, so reading
    it as ``c`` is flagged via :func:`warnings.warn`.
    """
    log_calls = [log2(c) for c in calls]
    log_space = [log2(s) for s in space_sizes]

    slope_vs_logspace, r2_vs_logspace = _fit_line(log_space, log_calls)
    exponent_in_n, r2_in_n = _fit_line([float(n) for n in ns], log_calls)

    if kind == "ordering":
        warnings.warn(
            "fit(): exponent_in_n is DIAGNOSTIC ONLY for ordering problems — the "
            "true n-exponent of sqrt(n!) grows (~0.5*log2 n) and is not the "
            "constant c of a 2^{c*n} law. Use slope_vs_logspace (theorem axis) "
            "and classify_ordering() for the verdict.",
            stacklevel=2,
        )

    return FitResult(
        slope_vs_logspace=slope_vs_logspace,
        r2_vs_logspace=r2_vs_logspace,
        exponent_in_n=exponent_in_n,
        r2_in_n=r2_in_n,
    )
