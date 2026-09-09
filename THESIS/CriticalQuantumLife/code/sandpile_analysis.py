#!/usr/bin/env python3
"""Critical Quantum Life — F8: directed-percolation analysis over the Sandpile activity series.

Reads `research_runs/sandpile_*.json` (sandpile.py output) and turns the per-step / per-shot
activity into the directed-percolation (DP) order parameter, IN THE FIELD'S OWN LANGUAGE, so it is
directly comparable to arXiv:2512.07966 / 2509.18259:

  AC-F8.4  activity density self-parks at a nonzero steady value; avalanche size distribution
           P(S) ~ S^-alpha with alpha ~ 1.5; branching sigma -> 1.
  AC-F8.5  quantum certification at the self-organized steady state: the cluster witness
           <X^{cluster}> sits above the classical measure-and-resend null (F3 null band).
  AC-F8.3  the decisive contrast: drive-when-quiet (closed) self-tunes to criticality; the matched
           yoked random drive does not.

Substrate. Each Aer shot is one independent stochastic SOC trajectory of A(t) (the active-site
count), stored in run["trajectories"] = (shots x steps). Avalanches and branching are pooled over
shots on that substrate; the density order parameter is the shot-ensemble mean A(t)/W. This adapts
the F2 suite (`criticality._fit_xmin` for the Clauset alpha, `criticality.estimate_sigma` for the
bootstrap CI) to the site-activity process instead of F0's surprise-avalanche process.

DP reference exponents (Dickman et al. 1998; Henkel-Hinrichsen-Lubeck; the 2512.07966 baseline):
alpha ~ 1.5 (mean-field / 1+1d avalanche size), z ~ 1.58 (dynamic), reported for the 180-min
finite-size-scaling tier. A single subcritical run does NOT establish SOC (honesty gate, plan
section 7).

Run:
    cd THESIS/CriticalQuantumLife/code
    python sandpile_analysis.py --closed ../research_runs/sandpile_closed_*_run.json \\
        --yoked ../research_runs/sandpile_yoked_*_run.json
"""
from __future__ import annotations

import argparse
import functools
import glob
import json
import math
import os
import sys
from typing import Any

import numpy as np

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl                          # OUTPUT_DIR + surrogate readout (reused)
import criticality as crit                        # F2: _fit_xmin / fit_powerlaw / estimate_sigma
import certify                                     # F3: null_band (reused)

BURN_FRAC = 0.5            # fraction of steps discarded as transient before the steady-state read
MIN_A_FOR_BRANCH = 1       # only count branching on steps with active mass (A >= this)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_run(pattern: str) -> dict[str, Any]:
    """Accept an exact path or a glob; return the newest matching sandpile run-JSON."""
    if os.path.exists(pattern):
        path = pattern
    else:
        matches = sorted(glob.glob(pattern), key=os.path.getmtime)
        if not matches:
            print(f"[ABORT] no sandpile run-JSON matches: {pattern}")
            raise SystemExit(1)
        path = matches[-1]
    with open(path) as f:
        run = json.load(f)
    run["_path"] = path
    return run


def _traj(run: dict[str, Any]) -> np.ndarray:
    """(shots x steps) per-shot active-count matrix."""
    return np.array(run.get("trajectories", []), dtype=float)


def _steady_slice(steps: int) -> slice:
    return slice(int(math.ceil(steps * BURN_FRAC)), steps)


# ---------------------------------------------------------------------------
# AC-F8.4a — activity density self-parks
# ---------------------------------------------------------------------------
def activity_density(run: dict[str, Any]) -> dict[str, Any]:
    """Steady-state activity density rho = <A(t)>/W over the post-burn-in window, with its
    across-shot std. Nonzero-steady rho is the DP order parameter above the absorbing state."""
    traj = _traj(run)
    width = int(run["meta"]["width"])
    steps = int(run["meta"]["steps"])
    if traj.size == 0:
        return {"density": None, "density_std": None, "width": width, "nonzero_steady": False}
    steady = traj[:, _steady_slice(steps)] / width           # (shots x steady_steps)
    per_shot = steady.mean(axis=1)                            # each shot's steady density
    rho = float(per_shot.mean())
    return {
        "density": rho,
        "density_std": float(per_shot.std()),
        "density_series": [float(x) for x in (traj.mean(axis=0) / width)],
        "width": width,
        "nonzero_steady": bool(rho > 0.5 / width),           # above the single-grain floor
    }


# ---------------------------------------------------------------------------
# AC-F8.4b — branching sigma -> 1 (adapts criticality.estimate_sigma)
# ---------------------------------------------------------------------------
def branching_sigma(run: dict[str, Any]) -> dict[str, Any]:
    """Branching ratio sigma of the site-activity process: A(t+1)/A(t) pooled over the post-burn-in
    window and all shots (only steps with A(t) >= MIN_A_FOR_BRANCH). sigma -> 1 is the critical
    point (each active grain triggers on average one more). Wraps the branching ratios into F2's
    `estimate_sigma` so the bootstrap 95% CI is single-sourced with the rest of the project."""
    traj = _traj(run)
    steps = int(run["meta"]["steps"])
    if traj.shape[0] == 0:
        return {"mean": None, "ci95": None, "n_gen": 0}
    lo = int(math.ceil(steps * BURN_FRAC))
    ratios: list[float] = []
    for shot in traj:
        for t in range(lo, steps - 1):
            if shot[t] >= MIN_A_FOR_BRANCH:
                ratios.append(float(shot[t + 1] / shot[t]))
    gens = [{"sigma": r} for r in ratios]                    # adapt F2's estimator (reads g["sigma"])
    return crit.estimate_sigma(gens)


# ---------------------------------------------------------------------------
# AC-F8.4c — avalanches + power-law alpha (reuses criticality._fit_xmin via fit_powerlaw)
# ---------------------------------------------------------------------------
def avalanches(run: dict[str, Any]) -> list[float]:
    """Avalanche sizes on the site-activity process: per shot, a maximal contiguous run of active
    steps (A > 0) between quiescences (A == 0); size S = integrated activity (sum of A over the
    run). Pooled over all shots. Mirrors F2's `collect_avalanches` excursion logic, read on A."""
    traj = _traj(run)
    sizes: list[float] = []
    for shot in traj:
        excess = 0.0
        in_av = False
        for a in shot:
            if a > 0:
                in_av = True
                excess += float(a)
            elif in_av:
                sizes.append(excess)
                excess = 0.0
                in_av = False
        if in_av and excess > 0.0:
            sizes.append(excess)
    return sizes


def fit_alpha(sizes: list[float]) -> dict[str, Any]:
    """Clauset MLE + KS power-law fit (reuses `criticality.fit_powerlaw` / `_fit_xmin`). Target
    alpha ~ 1.5. Below F2's MIN_AVALANCHES the fit is reported WITH a warning, never nulled."""
    return crit.fit_powerlaw(sizes)


# ---------------------------------------------------------------------------
# AC-F8.5 — quantum certification at the steady state (reuses F3 null band)
# ---------------------------------------------------------------------------
def certify_steady_state(joint: float, sep: float, shots: int,
                         cluster: list[int], k: float = certify.K_BAND) -> dict[str, Any]:
    """Cluster-witness certification at the self-organized steady state (AC-F8.5). `joint`/`sep`
    come from sandpile.witness_trajectory (or a hardware witness ingest). The classical measure-
    and-resend null band is F3's k/sqrt(shots); certified iff the witness sits ABOVE it. Reported
    as margin-above-null (the certification layer), NOT the headline (plan section 9 risk)."""
    band = certify.null_band(shots, None, k)
    signal = joint - sep
    return {
        "cluster": cluster, "cluster_size": len(cluster),
        "witness_joint": float(joint), "witness_separable": float(sep),
        "witness_signal": float(signal),
        "null_band": float(band), "k": k, "shots": int(shots),
        "margin": float(signal - band),
        "certified": bool(signal > band),
    }


# ---------------------------------------------------------------------------
# AC-F8.3 — the decisive closed-vs-yoked contrast
# ---------------------------------------------------------------------------
def compare_closed_vs_yoked(closed: dict[str, Any], yoked: dict[str, Any]) -> dict[str, Any]:
    """The whole claim (AC-F8.3): drive-when-quiet self-tunes to criticality; the matched-rate
    yoked random drive does not. Contrast the steady density, branching sigma, and avalanche
    power-law between the two arms. `self_organized` = closed parks nonzero-steady AND its sigma is
    closer to 1 than the yoked arm's (the yoked drive fails to self-tune)."""
    c_rho = activity_density(closed)
    y_rho = activity_density(yoked)
    c_sig = branching_sigma(closed)
    y_sig = branching_sigma(yoked)
    c_alpha = fit_alpha(avalanches(closed))
    y_alpha = fit_alpha(avalanches(yoked))

    def _dist1(sig: dict[str, Any]) -> float:
        return abs((sig.get("mean") if sig.get("mean") is not None else 0.0) - 1.0)

    closer = _dist1(c_sig) <= _dist1(y_sig)
    return {
        "closed": {"density": c_rho, "sigma": c_sig, "alpha": c_alpha},
        "yoked": {"density": y_rho, "sigma": y_sig, "alpha": y_alpha},
        "density_gap": (None if c_rho["density"] is None or y_rho["density"] is None
                        else float(c_rho["density"] - y_rho["density"])),
        "closed_self_parks": bool(c_rho["nonzero_steady"]),
        "closed_sigma_nearer_one": bool(closer),
        "self_organized": bool(c_rho["nonzero_steady"] and closer),
    }


# ---------------------------------------------------------------------------
# Both-basins convergence — the load-bearing SELF-organization test
# ---------------------------------------------------------------------------
RHO_REL_TOL = 0.25        # cold/hot steady densities within 25% (relative) = same set-point
SIGMA_ABS_TOL = 0.20      # cold/hot branching sigma within this = same critical regime


def convergence(cold: dict[str, Any], hot: dict[str, Any]) -> dict[str, Any]:
    """The both-basins SOC test (Dickman et al.: a self-organized critical point is an ATTRACTOR
    reached from EITHER side). Under the IDENTICAL drive-when-quiet rule, does the cold basin (empty
    start, climbs up) and the hot basin (saturated start, relaxes down) converge to the SAME steady
    density and branching sigma? Convergence is what distinguishes a genuinely SELF-organized set-
    point from a density that merely depends on the initial condition. `converged` = densities agree
    within RHO_REL_TOL AND sigmas within SIGMA_ABS_TOL. Reports the per-basin transient direction so
    a reviewer can see cold rose and hot fell into the same point (not both stuck at their start)."""
    c_rho = activity_density(cold)
    h_rho = activity_density(hot)
    c_sig = branching_sigma(cold)
    h_sig = branching_sigma(hot)
    cr, hr = c_rho["density"], h_rho["density"]
    cs, hs = c_sig["mean"], h_sig["mean"]
    density_ok = (cr is not None and hr is not None
                  and abs(cr - hr) <= RHO_REL_TOL * max(cr, hr, 1e-9))
    sigma_ok = (cs is not None and hs is not None and abs(cs - hs) <= SIGMA_ABS_TOL)

    def _direction(run: dict[str, Any]) -> str:
        traj = _traj(run)
        if traj.size == 0:
            return "flat"
        series = traj.mean(axis=0)
        head = float(series[: max(1, len(series) // 4)].mean())
        tail = float(series[-max(1, len(series) // 4):].mean())
        return "rose" if tail > head + 0.5 else "fell" if tail < head - 0.5 else "flat"

    return {
        "cold": {"density": cr, "sigma": cs, "transient": _direction(cold)},
        "hot": {"density": hr, "sigma": hs, "transient": _direction(hot)},
        "density_abs_diff": (None if cr is None or hr is None else float(abs(cr - hr))),
        "sigma_abs_diff": (None if cs is None or hs is None else float(abs(cs - hs))),
        "rho_rel_tol": RHO_REL_TOL, "sigma_abs_tol": SIGMA_ABS_TOL,
        "density_converged": bool(density_ok),
        "sigma_converged": bool(sigma_ok),
        "converged": bool(density_ok and sigma_ok),
    }


# ---------------------------------------------------------------------------
# 180-min tier — finite-size scaling (DP universality)
# ---------------------------------------------------------------------------
def finite_size_scaling(runs_by_width: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """DP finite-size scaling across widths (180-min tier, plan section 5). Collect the steady
    density, branching sigma and avalanche alpha per width; report the density trend and the alpha
    spread. The FULL universality claim (extracted z ~ 1.58, order-parameter beta) needs the
    180-min run actually executed with >= 5 seeds + error mitigation -- this returns the per-width
    table + an honest `universality_ready` flag, not an inflated exponent from thin data."""
    rows: list[dict[str, Any]] = []
    for w in sorted(runs_by_width):
        run = runs_by_width[w]
        rho = activity_density(run)
        sig = branching_sigma(run)
        alpha = fit_alpha(avalanches(run))
        rows.append({
            "width": w, "density": rho["density"], "sigma": sig["mean"],
            "alpha": alpha["alpha"], "n_avalanches": alpha["n_avalanches"],
        })
    widths = [r["width"] for r in rows]
    dens = [r["density"] for r in rows if r["density"] is not None]
    ready = len(rows) >= 3 and all(r["n_avalanches"] >= crit.MIN_AVALANCHES for r in rows)
    return {
        "per_width": rows,
        "widths": widths,
        "density_trend": (float(dens[-1] - dens[0]) if len(dens) >= 2 else None),
        "dp_reference": {"alpha": 1.5, "z": 1.58},
        "universality_ready": bool(ready),
        "note": ("finite-size scaling has enough avalanche statistics to attempt DP exponents"
                 if ready else
                 "insufficient statistics for a universality claim — needs the 180-min tier "
                 "(3 widths, >=5 seeds, error mitigation) actually executed"),
    }


# ---------------------------------------------------------------------------
# Assemble + write
# ---------------------------------------------------------------------------
def analyze_arm(run: dict[str, Any]) -> dict[str, Any]:
    """The DP order-parameter block for one arm (density + sigma + avalanche alpha)."""
    return {
        "density": activity_density(run),
        "sigma": branching_sigma(run),
        "avalanche_alpha": fit_alpha(avalanches(run)),
    }


def write_report(report: dict[str, Any], name: str) -> str:
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, f"{name}_sandpile_report.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def _fmt(x: float | None, w: int = 6, p: int = 3) -> str:
    return "  -  " if x is None else f"{x:{w}.{p}f}"


def _print_contrast(contrast: dict[str, Any]) -> None:
    c, y = contrast["closed"], contrast["yoked"]
    print("            density   sigma    alpha   n_av")
    for label, arm in (("closed", c), ("yoked ", y)):
        print(f"  {label}    {_fmt(arm['density']['density'])}  {_fmt(arm['sigma']['mean'])}  "
              f"{_fmt(arm['alpha']['alpha'])}  {arm['alpha']['n_avalanches']:5d}")
    print(f"\n  density gap (closed-yoked): {_fmt(contrast['density_gap'])}")
    print(f"  closed self-parks nonzero : {contrast['closed_self_parks']}")
    print(f"  closed sigma nearer 1     : {contrast['closed_sigma_nearer_one']}")
    print(f"\n  SELF-ORGANIZED (AC-F8.3): {'YES' if contrast['self_organized'] else 'NO'}"
          "  (drive-when-quiet self-tunes; yoked does not)")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F8 — Sandpile directed-percolation analysis")
    ap.add_argument("--closed", type=str, required=True, help="closed-arm sandpile run-JSON (glob ok)")
    ap.add_argument("--yoked", type=str, default=None, help="yoked-arm sandpile run-JSON (glob ok)")
    ap.add_argument("--name", type=str, default="sandpile")
    args = ap.parse_args()

    closed = load_run(args.closed)
    print(f"=== CQL F8 Sandpile DP analysis: W={closed['meta']['width']} "
          f"steps={closed['meta']['steps']} backend={closed['meta']['backend']} ===")
    report: dict[str, Any] = {"closed_run": closed["_path"], "closed": analyze_arm(closed)}
    if args.yoked:
        yoked = load_run(args.yoked)
        report["yoked_run"] = yoked["_path"]
        report["contrast"] = compare_closed_vs_yoked(closed, yoked)
        _print_contrast(report["contrast"])
    else:
        c = report["closed"]
        print(f"  density={_fmt(c['density']['density'])}  sigma={_fmt(c['sigma']['mean'])}  "
              f"alpha={_fmt(c['avalanche_alpha']['alpha'])} (n={c['avalanche_alpha']['n_avalanches']})")
    print(f"\n  -> {write_report(report, args.name)}")


if __name__ == "__main__":
    main()
