#!/usr/bin/env python3
"""
metrics_check.py — Quantum Galton Board: the P3 offline correctness gate (epic §3.6).

No network, no QPU, aer-free (mirrors walk_check.py): the metric functions are
checked against the closed-form analytic references (ideal Hadamard walk =
ballistic, binomial = diffusive) with no I/O and no sweep on disk, plus the shared
analytic walk is pinned to the P2 physics (build_walk + Statevector). Exits
non-zero on any breach; prints one PASS line per check otherwise.

Checks (plan §8):
  AC-3.1  variance_exponent a ~ 2 for the ideal walk, a == 1 for the binomial.
  AC-3.2  tv_distance / hellinger: 0 on identical, symmetric, range [0,1], > 0 on
          ideal-vs-binomial.
  AC-3.3  horn_contrast: strongly positive for the twin-horn ideal walk, markedly
          lower (negative) for the diffusive binomial hump.
  AC-3.4  entropy: >= 0, 0 for a delta histogram, and — physically — LARGER for the
          wider ballistic walk than the binomial at matched depth (see the note in
          check_entropy: this corrects the plan §2 AC-3.4 heuristic, which stated
          the ordering backwards).
  AC-3.5  crossover_depth: no knee on a pure-ballistic sweep, a knee inside range on
          a synthetic ideal->binomial morph, and reproducible (identical on re-run).
  pin     analytics.analytic_hadamard_walk == build_walk + Statevector to TOL, so the
          shared reference stays tied to P2 (OQ-3.6).

The metric functions are asserted over the ASYMPTOTIC depth window (8..20): small-n
transients make the ballistic exponent and horn sign noisy (the physics only settles
once the horns separate), so the gate checks the regime the metrics are meant to
describe. The reference pin uses cheap small steps (2..8), matching walk_check.py.
"""

from __future__ import annotations

import sys

from qiskit.quantum_info import Statevector

import analytics
import metrics
from walk import build_walk
from walk_spec import decode_counts

TOL = 1e-6
EXP_TOL = 0.05                       # ideal exponent |a - 2| tolerance over 8..20
CHECK_DEPTHS = list(range(8, 21))    # asymptotic window: horns separated, a ~ 2
MORPH_DEPTHS = list(range(8, 30, 2)) # synthetic ideal->binomial morph sweep


def _ideal_histogram(steps: int) -> dict[int, float]:
    """build_walk + exact Statevector -> {position: probability} (pins the reference)."""
    qc = build_walk(steps)
    unitary = qc.remove_final_measurements(inplace=False)
    probs = Statevector.from_instruction(unitary).probabilities_dict()
    return decode_counts({bits: p for bits, p in probs.items()}, steps)


def _blend(steps: int, w: float) -> dict[int, float]:
    """Linear ideal->binomial mixture at weight w (0 = ballistic, 1 = diffusive)."""
    a = analytics.analytic_hadamard_walk(steps)
    b = analytics.binomial_reference(steps)
    keys = set(a) | set(b)
    return {k: (1.0 - w) * a.get(k, 0.0) + w * b.get(k, 0.0) for k in keys}


def check_exponent() -> None:
    """AC-3.1: variance exponent ~ 2 (ballistic ideal), == 1 (diffusive binomial)."""
    vi = [metrics.variance(analytics.analytic_hadamard_walk(n)) for n in CHECK_DEPTHS]
    vb = [metrics.variance(analytics.binomial_reference(n)) for n in CHECK_DEPTHS]
    ai = metrics.variance_exponent(CHECK_DEPTHS, vi)
    ab = metrics.variance_exponent(CHECK_DEPTHS, vb)
    assert abs(ai["a"] - 2.0) < EXP_TOL, f"ideal a={ai['a']:.4f} not ~2 (tol {EXP_TOL})"
    assert abs(ab["a"] - 1.0) < TOL, f"binomial a={ab['a']:.6f} not ~1"
    assert ai["r2"] > 0.99 and ab["r2"] > 0.99, (ai["r2"], ab["r2"])
    print(f"PASS AC-3.1 exponent: ideal a={ai['a']:.3f}~2, binomial a={ab['a']:.3f}~1")


def check_distances() -> None:
    """AC-3.2: tv/hellinger = 0 on identical, symmetric, range [0,1], > 0 on differing."""
    p = analytics.analytic_hadamard_walk(12)
    q = analytics.binomial_reference(12)
    for d in (metrics.tv_distance, metrics.hellinger):
        assert d(p, p) < TOL, f"{d.__name__}(p,p) != 0"
        assert abs(d(p, q) - d(q, p)) < TOL, f"{d.__name__} not symmetric"
        val = d(p, q)
        assert 0.0 <= val <= 1.0, f"{d.__name__}={val} out of [0,1]"
        assert val > TOL, f"{d.__name__}(ideal,binomial)={val} not > 0"
    print("PASS AC-3.2 distances: tv/hellinger zero-on-equal, symmetric, [0,1], >0 on diff")


def check_contrast() -> None:
    """AC-3.3: horn_contrast strongly positive (ideal), markedly lower (binomial)."""
    ideal = [metrics.horn_contrast(analytics.analytic_hadamard_walk(n)) for n in CHECK_DEPTHS]
    binom = [metrics.horn_contrast(analytics.binomial_reference(n)) for n in CHECK_DEPTHS]
    for n, ci, cb in zip(CHECK_DEPTHS, ideal, binom):
        assert ci > 0.0, f"ideal horn_contrast n={n} = {ci} not > 0"
        assert cb < ci, f"binomial contrast n={n} ({cb}) not below ideal ({ci})"
    mean_gap = sum(ideal) / len(ideal) - sum(binom) / len(binom)
    assert mean_gap > 0.3, f"ideal-binomial contrast gap {mean_gap:.3f} not markedly positive"
    print(f"PASS AC-3.3 contrast: ideal horns > 0, binomial hump markedly lower (gap {mean_gap:.2f})")


def check_entropy() -> None:
    """AC-3.4: entropy >= 0, 0 for a delta, and higher for the wider ballistic walk.

    NOTE — deviation from plan §2 AC-3.4. The plan's heuristic said entropy is
    "larger for the diffusive hump than for the twin-horn walk". That is backwards:
    the ballistic Hadamard walk spreads over ~[-n/sqrt2, +n/sqrt2] with a broad
    oscillatory plateau between the horns, so it has HIGHER Shannon entropy than the
    binomial, which concentrates within ~sqrt(n) of the centre. Verified at every
    matched depth (e.g. n=16: ideal 3.414 bits vs binomial 3.047 bits). The gate
    asserts the physically-correct ordering; the plan hedged this check as "heuristic
    sanity, not a hard physics law".
    """
    assert metrics.entropy({0: 1.0}) < TOL, "delta entropy != 0"
    for n in CHECK_DEPTHS:
        ei = metrics.entropy(analytics.analytic_hadamard_walk(n))
        eb = metrics.entropy(analytics.binomial_reference(n))
        assert ei >= 0.0 and eb >= 0.0, f"negative entropy n={n}"
        assert ei > eb, f"n={n} ballistic entropy {ei:.3f} not > binomial {eb:.3f}"
    print("PASS AC-3.4 entropy: >= 0, 0 for delta, ballistic (wider) > binomial at matched depth")


def check_knee() -> None:
    """AC-3.5: no knee on a ballistic sweep, a reproducible knee on an ideal->binomial morph."""
    # pure-ballistic sweep: a_local stays ~2, never crosses down through 1.5 -> no knee
    vi = [metrics.variance(analytics.analytic_hadamard_walk(n)) for n in CHECK_DEPTHS]
    ci = [metrics.horn_contrast(analytics.analytic_hadamard_walk(n)) for n in CHECK_DEPTHS]
    ballistic = metrics.crossover_depth(CHECK_DEPTHS, vi, ci)
    assert ballistic["knee_depth"] is None, f"ballistic sweep spuriously found a knee: {ballistic}"

    # synthetic morph: weight ramps 0 (ballistic) -> 1 (diffusive) across the sweep
    ws = [i / (len(MORPH_DEPTHS) - 1) for i in range(len(MORPH_DEPTHS))]
    hs = [_blend(n, w) for n, w in zip(MORPH_DEPTHS, ws)]
    vv = [metrics.variance(h) for h in hs]
    cc = [metrics.horn_contrast(h) for h in hs]
    knee = metrics.crossover_depth(MORPH_DEPTHS, vv, cc)
    kd = knee["knee_depth"]
    assert kd is not None, "morph sweep found no knee"
    assert MORPH_DEPTHS[0] <= kd <= MORPH_DEPTHS[-1], f"knee {kd} outside swept range"
    # reproducibility: identical on a second call over the same series
    again = metrics.crossover_depth(MORPH_DEPTHS, vv, cc)
    assert again == knee, "crossover_depth not reproducible"
    print(f"PASS AC-3.5 knee: none on ballistic, knee at depth {kd:.2f} on morph, reproducible")


def check_reference() -> None:
    """OQ-3.6: shared analytic_hadamard_walk == build_walk + Statevector to TOL (pins P2)."""
    for steps in range(2, 9):
        shared = analytics.analytic_hadamard_walk(steps)
        physical = _ideal_histogram(steps)
        tv = metrics.tv_distance(shared, physical)
        assert tv < TOL, f"steps={steps} shared-vs-build_walk TV={tv:.3e} >= TOL"
    print(f"PASS pin: analytics.analytic_hadamard_walk == build_walk+Statevector, TV < {TOL:.0e} steps 2..8")


def main() -> int:
    try:
        check_exponent()
        check_distances()
        check_contrast()
        check_entropy()
        check_knee()
        check_reference()
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("metrics_check: all offline gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
