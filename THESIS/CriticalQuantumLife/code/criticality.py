#!/usr/bin/env python3
"""Critical Quantum Life — F2: the criticality metric suite.

Post-processing over F0's `research_runs/*.json`. Turns the coarse F1 signal ("sigma
trends toward 1") into a DEFENSIBLE criticality claim by estimating five numbers and
writing them back into the run-JSON under a `"criticality"` key (in-place, Q2):

  AC-F2.1  branching parameter sigma, mean + bootstrap 95% CI (target -> 1)
  AC-F2.2  avalanche size-distribution exponent alpha (P(S) ~ S^-alpha), MLE + KS
           goodness-of-fit (Clauset-Shalizi-Newman), target alpha ~ 1.5
  AC-F2.3  Shannon-entropy plateau test (lively plateau vs H->0 collapse)
  AC-F2.4  order-parameter susceptibility peak (locates the critical point)
  AC-F2.5  post-poke relaxation time constant tau (exp return-to-set-point)

Substrate — the surprise-AVALANCHE process (Option A, F0).
---------------------------------------------------------
F0's genome is a GHZ genealogy: local mutation leaves the alive-mask / alive-count
INVARIANT (information lives only in the joint witness), so there is NO alive-count
series to build avalanches from. F0 therefore defines `active` = a generation whose
surprise beats the running median, and its docstring mandates that "F2 fits avalanche
alpha and the branching sigma -> 1 of THAT [surprise-avalanche] process". So here the
avalanche substrate is the surprise-activity process: an avalanche is a contiguous run
of `active` generations; its size S is the integrated surprise-excess above baseline
(the resolved-Q1 "excursion above the running baseline; size = integrated excess",
read on surprise instead of a non-existent alive count). The order parameter for the
susceptibility (AC-F2.4) is likewise the activity indicator.

Metric definitions cite Beggs & Plenz 2003 (sigma~1, alpha~1.5, neuronal avalanches)
and Bak-Tang-Wiesenfeld 1987 (self-organized criticality). alpha is fit by MLE +
KS-minimized xmin (Clauset method), NOT a naive log-log line.

F2 defines no circuits and renames nothing — it reads F0's one schema and adds a
sibling block. Width-agnostic: runs identically on F1's W=4 sim runs and F5's W=8
hardware runs.

Run:
    cd THESIS/CriticalQuantumLife/code
    python criticality.py --runs ../research_runs/cql_f1_closed_*_run.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from typing import Any

import numpy as np

try:  # Q3: scipy for the tau exponential fit, numpy fallback if absent
    from scipy.optimize import curve_fit
    _HAVE_SCIPY = True
except Exception:  # pragma: no cover - minimal F0 env without scipy
    _HAVE_SCIPY = False

# ---- criticality constants (plan §7) ----------------------------------------
BOOT_RESAMPLES = 2000        # bootstrap resamples for the sigma CI
GOF_RESAMPLES = 500          # semiparametric bootstrap for the alpha goodness-of-fit p
MIN_AVALANCHES = 20          # below this, alpha is reported WITH a warning (Q4), never nulled
MIN_TAIL = 4                 # smallest power-law tail we will attempt an MLE on
H_DEAD = 0.35                # entropy floor: late-window mean at/under this = collapse (dead)
SLOPE_EPS = 0.02             # |late-window entropy slope| under this counts as a plateau
SUSC_WINDOW = 4              # sliding-window width for the susceptibility variance
LATE_FRAC = 1.0 / 3.0        # fraction of the run treated as the "late window"
FLAT_VAR = 1e-6              # post-poke variance under this = observable is flat (tau fallback)
_RNG_SEED = 12345            # fixed so the bootstrap CIs are reproducible run-to-run


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_runs(paths: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """Read F0 run-JSONs; return (path, run_dict) pairs. Globs are expanded."""
    out: list[tuple[str, dict[str, Any]]] = []
    for pat in paths:
        matches = sorted(glob.glob(pat)) or [pat]
        for path in matches:
            with open(path) as f:
                out.append((path, json.load(f)))
    return out


# ---------------------------------------------------------------------------
# AC-F2.1 — branching parameter sigma + bootstrap CI
# ---------------------------------------------------------------------------
def estimate_sigma(gens: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean of the per-generation branching ratio `sigma` (F0's surprise-activity
    branching, alive(g)/alive(g-1) on the active process) with a bootstrap 95% CI.
    F0 logs the raw ratio; F2 adds the confidence that makes "≈1" a statistical claim."""
    vals = np.array([g["sigma"] for g in gens if g.get("sigma") is not None], dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"mean": None, "ci95": None, "n_gen": 0}
    rng = np.random.default_rng(_RNG_SEED)
    boot = rng.choice(vals, size=(BOOT_RESAMPLES, vals.size), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"mean": float(vals.mean()), "ci95": [float(lo), float(hi)], "n_gen": int(vals.size)}


# ---------------------------------------------------------------------------
# AC-F2.2 — avalanches + power-law alpha
# ---------------------------------------------------------------------------
def collect_avalanches(gens: list[dict[str, Any]]) -> list[float]:
    """Surprise-avalanche sizes (Option A). An avalanche is a maximal contiguous run of
    `active` generations; its size S is the integrated surprise-excess above the run's
    median-surprise baseline. Uses only F0's `active` + `surprise` fields."""
    surprises = np.array([g["surprise"] for g in gens], dtype=float)
    baseline = float(np.median(surprises)) if surprises.size else 0.0
    sizes: list[float] = []
    excess = 0.0
    in_av = False
    for g in gens:
        if g.get("active"):
            in_av = True
            excess += max(0.0, float(g["surprise"]) - baseline)
        elif in_av:
            if excess > 0.0:
                sizes.append(excess)
            excess = 0.0
            in_av = False
    if in_av and excess > 0.0:      # avalanche still open at the last generation
        sizes.append(excess)
    return sizes


def _plfit_alpha(tail: np.ndarray, xmin: float) -> float:
    """Continuous-power-law MLE exponent for a tail x>=xmin (Clauset eq. 3.1)."""
    n = tail.size
    s = float(np.sum(np.log(tail / xmin)))
    if s <= 0.0:
        return math.inf
    return 1.0 + n / s


def _ks_stat(tail: np.ndarray, xmin: float, alpha: float) -> float:
    """KS distance between the tail's empirical CDF and the fitted power-law CDF."""
    x = np.sort(tail)
    n = x.size
    model = 1.0 - (x / xmin) ** (-(alpha - 1.0))   # F(x)=1-(x/xmin)^-(alpha-1)
    emp_hi = np.arange(1, n + 1) / n
    emp_lo = np.arange(0, n) / n
    return float(max(np.max(np.abs(emp_hi - model)), np.max(np.abs(emp_lo - model))))


def _fit_xmin(sizes: np.ndarray) -> tuple[float, float, float, int]:
    """Clauset xmin selection: over candidate xmins pick the one minimising the KS
    distance of the MLE fit on its tail. Returns (alpha, xmin, ks, n_tail)."""
    candidates = np.unique(sizes)
    best = (math.inf, math.nan, math.inf, 0)    # (ks, alpha, xmin, n_tail) sort key = ks
    for xmin in candidates:
        tail = sizes[sizes >= xmin]
        if tail.size < MIN_TAIL:
            continue
        alpha = _plfit_alpha(tail, float(xmin))
        if not math.isfinite(alpha):
            continue
        ks = _ks_stat(tail, float(xmin), alpha)
        if ks < best[0]:
            best = (ks, alpha, float(xmin), int(tail.size))
    ks, alpha, xmin, n_tail = best
    return alpha, xmin, ks, n_tail


def _powerlaw_sample(rng: np.random.Generator, n: int, xmin: float, alpha: float) -> np.ndarray:
    """Draw n continuous power-law variates >= xmin (inverse-transform, Clauset eq. D.4)."""
    u = rng.random(n)
    return xmin * (1.0 - u) ** (-1.0 / (alpha - 1.0))


def fit_powerlaw(sizes_list: list[float]) -> dict[str, Any]:
    """MLE power-law exponent alpha with KS-minimised xmin and a semiparametric
    bootstrap goodness-of-fit p-value (Clauset-Shalizi-Newman). Target alpha ~ 1.5.
    Q4: below MIN_AVALANCHES the fit is still reported, with a `warning`, never nulled."""
    sizes = np.array([s for s in sizes_list if s > 0.0], dtype=float)
    n_av = int(sizes.size)
    out: dict[str, Any] = {"alpha": None, "xmin": None, "n_avalanches": n_av,
                           "ks_stat": None, "gof_pvalue": None, "warning": None}
    if n_av < MIN_TAIL or np.unique(sizes).size < 2:
        out["warning"] = f"too few avalanches to fit (n={n_av}); alpha not estimable"
        return out
    alpha, xmin, ks, n_tail = _fit_xmin(sizes)
    if not math.isfinite(alpha):
        out["warning"] = f"no valid xmin/tail (n={n_av}); alpha not estimable"
        return out
    out.update(alpha=float(alpha), xmin=float(xmin), ks_stat=float(ks), n_tail=n_tail)
    # semiparametric GOF: fraction of synthetic datasets with KS >= observed
    rng = np.random.default_rng(_RNG_SEED)
    below = sizes[sizes < xmin]
    p_tail = n_tail / n_av
    ge = 0
    reps = 0
    for _ in range(GOF_RESAMPLES):
        n_syn_tail = int(np.sum(rng.random(n_av) < p_tail))
        parts = [_powerlaw_sample(rng, n_syn_tail, xmin, alpha)]
        n_below = n_av - n_syn_tail
        if n_below > 0:
            parts.append(rng.choice(below, size=n_below, replace=True)
                         if below.size else _powerlaw_sample(rng, n_below, xmin, alpha))
        syn = np.concatenate(parts)
        s_alpha, s_xmin, s_ks, s_ntail = _fit_xmin(syn)
        if not math.isfinite(s_alpha):
            continue
        reps += 1
        if s_ks >= ks:
            ge += 1
    out["gof_pvalue"] = float(ge / reps) if reps else None
    if n_av < MIN_AVALANCHES:
        out["warning"] = (f"only {n_av} avalanches (< {MIN_AVALANCHES}); "
                          f"alpha={alpha:.2f} is low-confidence — do not over-claim the 1.5 fit")
    return out


# ---------------------------------------------------------------------------
# AC-F2.3 — entropy plateau vs collapse
# ---------------------------------------------------------------------------
def entropy_plateau(gens: list[dict[str, Any]]) -> dict[str, Any]:
    """Distinguish a lively entropy PLATEAU from an H->0 COLLAPSE (honesty gate 2:
    a run that "wins" by going silent FAILS criticality). plateau = late-window slope
    near zero AND late-window mean above the H_DEAD floor; collapsed = late mean at/under
    the floor. Reports both booleans so a silent run cannot masquerade as lively."""
    h = np.array([g["entropy"] for g in gens], dtype=float)
    if h.size == 0:
        return {"plateau": False, "plateau_mean": None, "slope_late": None, "collapsed": True}
    k = max(2, int(math.ceil(h.size * LATE_FRAC)))
    late = h[-k:]
    t = np.arange(late.size, dtype=float)
    slope = float(np.polyfit(t, late, 1)[0]) if late.size >= 2 else 0.0
    late_mean = float(late.mean())
    collapsed = late_mean <= H_DEAD
    plateau = (abs(slope) < SLOPE_EPS) and not collapsed
    return {"plateau": bool(plateau), "plateau_mean": late_mean,
            "slope_late": slope, "collapsed": bool(collapsed)}


# ---------------------------------------------------------------------------
# AC-F2.4 — order-parameter susceptibility peak
# ---------------------------------------------------------------------------
def susceptibility(gens: list[dict[str, Any]]) -> dict[str, Any]:
    """Susceptibility chi(g) = sliding-window variance of the order parameter (the
    surprise-activity indicator; Option A's stand-in for the invariant alive-fraction).
    At criticality fluctuations peak — the peak generation, coincident with sigma~1,
    corroborates the transition."""
    m = np.array([1.0 if g.get("active") else 0.0 for g in gens], dtype=float)
    if m.size == 0:
        return {"peak_gen": None, "peak_value": None, "series": []}
    w = min(SUSC_WINDOW, m.size)
    series: list[float] = []
    for i in range(m.size):
        lo = max(0, i - w + 1)
        series.append(float(np.var(m[lo:i + 1])))
    peak_idx = int(np.argmax(series))
    return {"peak_gen": int(gens[peak_idx]["gen"]), "peak_value": float(series[peak_idx]),
            "series": series}


# ---------------------------------------------------------------------------
# AC-F2.5 — post-poke relaxation time constant tau
# ---------------------------------------------------------------------------
def _exp_model(t: np.ndarray, baseline: float, amp: float, tau: float) -> np.ndarray:
    return baseline + amp * np.exp(-t / tau)


def _fit_exp_numpy(t: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """numpy fallback exp fit (log-linearised). Returns (baseline, amp, tau, r2)."""
    baseline = float(np.min(y)) - 1e-3
    z = y - baseline
    z = np.where(z > 0, z, 1e-9)
    slope, intercept = np.polyfit(t, np.log(z), 1)
    tau = -1.0 / slope if slope < 0 else math.inf
    amp = float(np.exp(intercept))
    pred = _exp_model(t, baseline, amp, tau)
    r2 = _r2(y, pred)
    return baseline, amp, float(tau), r2


def _r2(y: np.ndarray, pred: np.ndarray) -> float:
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def relaxation_tau(gens: list[dict[str, Any]], poke_gen: int | None,
                   observable: str = "surprise") -> dict[str, Any]:
    """Fit y(t) = baseline + A·exp(-t/tau) from poke_gen onward (AC-F2.5); report tau + R².
    Falls back to `entropy` if the surprise series is flat after the poke. Null when there
    is no poke or too few post-poke points to fit three parameters."""
    null = {"tau": None, "r2": None, "poke_gen": poke_gen, "observable": observable}
    if poke_gen is None:
        return {**null, "note": "no poke in this run"}
    post = [g for g in gens if g["gen"] >= poke_gen]
    if len(post) < 4:
        return {**null, "note": f"only {len(post)} post-poke generations (< 4)"}
    y = np.array([g[observable] for g in post], dtype=float)
    if float(np.var(y)) < FLAT_VAR and observable == "surprise":   # fall back to entropy
        observable = "entropy"
        y = np.array([g[observable] for g in post], dtype=float)
    t = np.arange(y.size, dtype=float)
    try:
        if _HAVE_SCIPY:
            p0 = (float(np.min(y)), float(y[0] - np.min(y)), 2.0)
            popt, _ = curve_fit(_exp_model, t, y, p0=p0, maxfev=10000,
                                bounds=([-np.inf, -np.inf, 1e-3], [np.inf, np.inf, np.inf]))
            baseline, amp, tau = (float(v) for v in popt)
            r2 = _r2(y, _exp_model(t, baseline, amp, tau))
        else:
            baseline, amp, tau, r2 = _fit_exp_numpy(t, y)
    except Exception as exc:  # noqa: BLE001 - report the failure, do not crash the suite
        return {**null, "observable": observable, "note": f"fit failed: {exc}"}
    if not math.isfinite(tau):
        return {**null, "observable": observable, "note": "no decay (tau non-finite)"}
    return {"tau": float(tau), "r2": float(r2), "poke_gen": int(poke_gen),
            "observable": observable}


# ---------------------------------------------------------------------------
# Assemble + write
# ---------------------------------------------------------------------------
def analyze(run: dict[str, Any]) -> dict[str, Any]:
    """Assemble the `criticality` block (plan §4) from the five estimators."""
    gens = run["generations"]
    poke_gen = run.get("meta", {}).get("poke_gen")
    if poke_gen is None:                       # fall back to a logged poke flag
        flagged = [g["gen"] for g in gens if g.get("poke")]
        poke_gen = flagged[0] if flagged else None
    return {
        "sigma": estimate_sigma(gens),
        "avalanche_alpha": fit_powerlaw(collect_avalanches(gens)),
        "entropy": entropy_plateau(gens),
        "susceptibility": susceptibility(gens),
        "relaxation_tau": relaxation_tau(gens, poke_gen),
    }


def write_criticality(run: dict[str, Any], block: dict[str, Any], source_path: str) -> str:
    """Add the `"criticality"` key to the source run-JSON in place (Q2). Re-running
    overwrites the prior block."""
    run["criticality"] = block
    with open(source_path, "w") as f:
        json.dump(run, f, indent=2, default=str)
    return source_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _summary_line(path: str, block: dict[str, Any]) -> str:
    sig = block["sigma"]["mean"]
    alpha = block["avalanche_alpha"]["alpha"]
    n_av = block["avalanche_alpha"]["n_avalanches"]
    plat = block["entropy"]["plateau"]
    tau = block["relaxation_tau"]["tau"]
    name = path.rsplit("/", 1)[-1]
    sig_s = "  -  " if sig is None else f"{sig:4.2f}"
    alpha_s = "  -  " if alpha is None else f"{alpha:4.2f}"
    tau_s = "  -  " if tau is None else f"{tau:4.2f}"
    return f"  {name}\n    sigma={sig_s}  alpha={alpha_s} (n={n_av})  plateau={plat}  tau={tau_s}"


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F2 — criticality metric suite")
    ap.add_argument("--runs", nargs="+", required=True,
                    help="F0 run-JSON paths (globs ok); the criticality block is added in place")
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=None,
                    help="override meta.poke_gen for the tau fit")
    ap.add_argument("--name", type=str, default=None, help="unused label (kept for symmetry)")
    args = ap.parse_args()

    runs = load_runs(args.runs)
    if not runs:
        print("[F2] no run-JSONs matched")
        raise SystemExit(1)
    print(f"=== CQL F2 criticality: {len(runs)} run(s) ===")
    for path, run in runs:
        if args.poke_gen is not None:
            run.setdefault("meta", {})["poke_gen"] = args.poke_gen
        block = analyze(run)
        write_criticality(run, block, path)
        print(_summary_line(path, block))
        warn = block["avalanche_alpha"].get("warning")
        if warn:
            print(f"    [warn] {warn}")


if __name__ == "__main__":
    main()
