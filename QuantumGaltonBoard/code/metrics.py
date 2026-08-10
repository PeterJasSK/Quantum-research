#!/usr/bin/env python3
"""
metrics.py — Quantum Galton Board: the frozen analysis interface (P3, epic §4).

Pure functions over ``{position: probability}`` histograms and per-depth series.
No I/O, no globals, no run.json loading (that is P4). Python is the source of
truth (epic §3.6 LOCKED); P5 vendors a JS mirror validated by the parity gate,
so every definition here is kept simple and fully specified.

The four metrics (epic §4) and the single defended knee:
  M1  variance growth exponent  — mean, variance, variance_exponent          (AC-3.1)
  M2  distribution distance      — tv_distance, hellinger                     (AC-3.2)
  M3  horn contrast              — horn_contrast                              (AC-3.3)
  M4  output entropy             — entropy                                    (AC-3.4)
  knee ballistic->diffusive      — local_variance_exponent, crossover_depth   (AC-3.5)

All metric functions take INT-keyed histograms (dict[int, float]) normalised to
sum 1. to_int_hist bridges the string-keyed run.json position_histogram form
(pipeline.py:101 / arms.py:96) so P4 can feed loaded runs directly; the offline
gate feeds analytics.py output (already int-keyed).

Sparse-safe: histograms are sparse (only occupied positions appear,
walk_spec.py:56), so every metric treats a missing position as probability 0 and
pairwise distances use the union of supports. stdlib + numpy only (plan §4).
"""

from __future__ import annotations

import math

import numpy as np


def to_int_hist(hist: dict) -> dict[int, float]:
    """String- or int-keyed histogram -> int-keyed {position: probability}.

    The run.json position_histogram stringifies its keys on write
    (pipeline.py:101); this re-``int()``s them so the metric functions consume a
    loaded run and an analytics.py reference identically.
    """
    return {int(k): float(v) for k, v in hist.items()}


# --- M1: variance growth exponent (AC-3.1) --------------------------------

def mean(hist: dict[int, float]) -> float:
    """First moment: Sum p(x) * x."""
    return sum(p * x for x, p in hist.items())


def variance(hist: dict[int, float]) -> float:
    """Second central moment: Sum p(x) * x^2 - mean^2.

    The explicit mean subtraction keeps it honest for the noisy/hw arms whose
    mean may drift off 0 (the symmetric ideal walk has mean ~ 0).
    """
    m = mean(hist)
    second = sum(p * x * x for x, p in hist.items())
    return second - m * m


def variance_exponent(depths: list[int],
                      variances: list[float]) -> dict[str, float]:
    """Least-squares log-log fit of sigma^2 ~ t^a -> {"a", "b", "r2"} (AC-3.1).

    Degree-1 numpy.polyfit on (log depths, log variances): slope ``a`` is the
    growth exponent (a->2 ballistic, a->1 diffusive), ``b`` the intercept, ``r2``
    the coefficient of determination of the log-log fit. Depths with a
    non-positive variance (a delta / zero-variance depth) are dropped before the
    log, never fed to log as a silent nan. Requires >= 2 usable points; raises
    ValueError otherwise (plan §10).
    """
    if len(depths) != len(variances):
        raise ValueError("depths and variances must be the same length")
    if len(depths) < 2:
        raise ValueError("variance_exponent needs >= 2 (depth, variance) points")
    pts = [(t, v) for t, v in zip(depths, variances) if t > 0 and v > 0.0]
    if len(pts) < 2:
        raise ValueError(
            "variance_exponent needs >= 2 points with positive depth and variance "
            f"after dropping non-positive variances; got {len(pts)}")
    log_t = np.log(np.array([t for t, _ in pts], dtype=float))
    log_v = np.log(np.array([v for _, v in pts], dtype=float))
    a, b = np.polyfit(log_t, log_v, 1)
    pred = a * log_t + b
    ss_res = float(np.sum((log_v - pred) ** 2))
    ss_tot = float(np.sum((log_v - log_v.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0
    return {"a": float(a), "b": float(b), "r2": r2}


# --- M2: distribution distance (AC-3.2) -----------------------------------

def tv_distance(p: dict[int, float], q: dict[int, float]) -> float:
    """Total-variation distance: 0.5 * Sum_{x in supp(p) U supp(q)} |p(x)-q(x)|.

    Range [0, 1], symmetric, 0 iff p == q. Support is the union; a position
    absent from one dict contributes with value 0 (sparse-safe).
    """
    support = set(p) | set(q)
    return 0.5 * sum(abs(p.get(x, 0.0) - q.get(x, 0.0)) for x in support)


def hellinger(p: dict[int, float], q: dict[int, float]) -> float:
    """Hellinger distance: (1/sqrt2) * sqrt(Sum_x (sqrt p(x) - sqrt q(x))^2).

    Range [0, 1], symmetric, 0 iff p == q. Union support, missing = 0.
    """
    support = set(p) | set(q)
    total = sum((math.sqrt(p.get(x, 0.0)) - math.sqrt(q.get(x, 0.0))) ** 2
                for x in support)
    return math.sqrt(total) / math.sqrt(2.0)


# --- M3: horn contrast / peak-splitting visibility (AC-3.3) ---------------

def horn_contrast(hist: dict[int, float]) -> float:
    """(P_horn - P_centre) / (P_horn + P_centre): the collapse-curve sample (AC-3.3).

    P_centre is the central band, P_horn the max probability over the remaining
    off-centre positions. Parity of the walk is read from the histogram support
    (all positions satisfy pos ≡ n (mod 2) since pos = 2*bin - n), so the centre
    band is:
      even n : position 0                         -> P_centre = hist.get(0)
      odd  n : positions +/-1                      -> P_centre = mean(hist[-1], hist[1])
    (OQ-3.3). Ballistic twin horns -> strongly positive; a diffusive central hump
    -> P_centre dominates -> negative / -> 0. That monotone sign flip is what
    makes the per-depth series a clean collapse curve. Returns 0.0 on an
    empty/degenerate histogram.
    """
    if not hist:
        return 0.0
    parity = next(iter(hist)) % 2       # every position shares the walk's parity
    if parity == 0:
        centre_positions = {0}
        p_centre = hist.get(0, 0.0)
    else:
        centre_positions = {-1, 1}
        p_centre = 0.5 * (hist.get(-1, 0.0) + hist.get(1, 0.0))
    off_centre = [v for x, v in hist.items() if x not in centre_positions]
    p_horn = max(off_centre) if off_centre else 0.0
    denom = p_horn + p_centre
    if denom == 0.0:
        return 0.0
    return (p_horn - p_centre) / denom


# --- M4: output entropy (AC-3.4) ------------------------------------------

def entropy(hist: dict[int, float], base: float = 2.0) -> float:
    """Shannon entropy -Sum_{x: p>0} p * log_base(p), in bits by default (AC-3.4).

    0 * log0 == 0 (occupied positions only). Raw (un-normalised) bits (OQ-3.4); a
    log_base(n+1)-normalised view is a P4/P6 presentation choice, not returned
    here. >= 0; 0 for a delta histogram.
    """
    log_base = math.log(base)
    return -sum(p * math.log(p) / log_base for p in hist.values() if p > 0.0)


# --- The crossover / knee extractor (AC-3.5) — the single defended metric --

def local_variance_exponent(
        depths: list[int], variances: list[float],
        window: int = 3) -> list[tuple[int, float]]:
    """Sliding log-log fit -> [(t, a_local(t)), ...] (AC-3.5, OQ-3.2).

    For each depth t, fit log sigma^2 = a*log t + b over the ``window`` depths
    centred on t (forward/backward 2-point at the sweep ends, where the centred
    window is clipped to the array bounds). Non-positive variances / depths inside
    a window are dropped before the log; a window with < 2 usable points raises
    ValueError (never a silent nan slope, plan §10).
    """
    if len(depths) != len(variances):
        raise ValueError("depths and variances must be the same length")
    if len(depths) < 2:
        raise ValueError("local_variance_exponent needs >= 2 points")
    half = window // 2
    out: list[tuple[int, float]] = []
    for i, t in enumerate(depths):
        lo = max(0, i - half)
        hi = min(len(depths), i + half + 1)
        pts = [(depths[k], variances[k]) for k in range(lo, hi)
               if depths[k] > 0 and variances[k] > 0.0]
        if len(pts) < 2:
            raise ValueError(
                f"local_variance_exponent: < 2 usable points in the window at "
                f"depth {t} (non-positive variance?)")
        log_t = np.log(np.array([p[0] for p in pts], dtype=float))
        log_v = np.log(np.array([p[1] for p in pts], dtype=float))
        a, _ = np.polyfit(log_t, log_v, 1)
        out.append((int(t), float(a)))
    return out


def _first_downcross(xs: list[float], ys: list[float],
                     level: float) -> float | None:
    """First x where the (x, y) polyline crosses DOWN through ``level``.

    Scans consecutive pairs; on the first pair with y_i >= level > y_{i+1}
    returns the linearly-interpolated x. None if no downward crossing occurs.
    """
    for i in range(len(ys) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y0 >= level > y1:
            x0, x1 = xs[i], xs[i + 1]
            frac = (y0 - level) / (y0 - y1)
            return x0 + frac * (x1 - x0)
    return None


def crossover_depth(
        depths: list[int], variances: list[float], contrasts: list[float],
        *, midpoint: float = 1.5) -> dict[str, float | None]:
    """Ballistic->diffusive knee depth from M1 (defended) + M3 (corroborating) (AC-3.5).

    1. Primary knee: the linearly-interpolated depth at which the LOCAL variance
       exponent a_local(t) first crosses DOWN through ``midpoint`` (1.5 = midway
       between ballistic 2 and diffusive 1). None if a_local never falls to the
       midpoint across the sweep (no collapse observed in range — an honest
       result, not an error).
    2. Contrast knee: the depth at which ``contrasts`` first drops below half its
       sweep maximum (the "randomness-shape half-life", source §Thesis),
       interpolated between bracketing depths; None if it never does.
    Returns {"knee_depth", "exponent_knee", "contrast_knee", "rule"}. The reported
    knee_depth IS the exponent crossing (OQ-3.1: epic §3.1 names the exponent
    crossover the defended metric; horn contrast is the headline visual but noisier
    near collapse, so it corroborates). Pure function of the three series — no
    randomness, no I/O — so re-running on the same series yields an identical knee.
    """
    if not (len(depths) == len(variances) == len(contrasts)):
        raise ValueError("depths, variances and contrasts must be the same length")
    locals_ = local_variance_exponent(depths, variances)
    a_depths = [float(t) for t, _ in locals_]
    a_values = [a for _, a in locals_]
    exponent_knee = _first_downcross(a_depths, a_values, midpoint)

    contrast_knee: float | None = None
    if contrasts:
        threshold = 0.5 * max(contrasts)
        contrast_knee = _first_downcross(
            [float(t) for t in depths], list(contrasts), threshold)

    return {
        "knee_depth": exponent_knee,
        "exponent_knee": exponent_knee,
        "contrast_knee": contrast_knee,
        "rule": "a_local crosses 1.5; contrast half-max corroborates",
    }
