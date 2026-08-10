#!/usr/bin/env python3
"""
sweep.py — Quantum Galton Board: the depth×arm experiment driver (P4, plan §5).

The single owner of "load ``runs/``, aggregate ``summary.json``, feed the P3
functions across the depth×arm matrix" (P3 §3 defers this here). Pure
orchestration + numpy; imports ``arms``/``config``/``pipeline``/``metrics``/
``analytics`` and never a plotting or web module (matplotlib is confined to
figures.py, epic §9 P1).

Two responsibilities, kept separate so Phase B reuses both:

  run_sim_sweep(arm, depths, seeds, cfg)  — drive the ideal/noisy sim sweep by
      looping the frozen ``arms.run_arm`` (Phase A). ``ideal`` is deterministic ->
      one seed; ``noisy`` uses ``cfg.seeds`` so the sim collapse curve carries a
      spread (OQ-4.6). NEVER drives ``hw`` (Phase B uses galton.py --arm hw).
  aggregate(arm, run_paths_or_dir, ...)   — group any set of run.json by depth,
      compute per-depth mean±std of the P3 metrics + the mean position histogram,
      feed the P3 knee extractor, and write ONE summary.json via the frozen
      ``pipeline.write_summary`` (both phases). Data for AC-4.1/4.2/4.4.

No metric or knee definition lives here — every number comes from metrics.py /
analytics.py (plan §11). No frozen key is added: aggregate populates the P1
``per_depth[].metrics`` and ``per_depth[].position_histogram`` slots
(SCHEMA.md:87); their *contents* are P4's to define.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

import analytics
import config
import metrics
import pipeline
from arms import run_arm
from walk_spec import WALK_SPEC

# the per-depth metric field names populated in summary.json per_depth[].metrics
METRIC_FIELDS = [
    "variance_mean", "variance_std",
    "horn_contrast_mean", "horn_contrast_std",
    "entropy_mean", "entropy_std",
    "a_local",
    "tv_to_ideal", "hellinger_to_ideal",
    "tv_to_binomial", "hellinger_to_binomial",
]


# --- driving the sim sweep (Phase A; AC-4.1/4.2/4.4 data) -------------------

def run_sim_sweep(arm: str, depths: list[int], seeds: list[int],
                  cfg: config.Config) -> list[str]:
    """Loop ``arms.run_arm`` over depths × seeds; return the run.json paths.

    ``ideal`` is deterministic given the Statevector seed -> a single seed
    (``cfg.seed``); ``noisy`` sweeps every seed in ``seeds`` so the sim collapse
    curve carries a ± std band (OQ-4.6). ``hw`` is rejected: the hw matrix is
    driven by the frozen ``galton.py --arm hw`` in Phase B (plan §5), never here.
    """
    if arm == "hw":
        raise ValueError(
            "run_sim_sweep drives sim arms only; the hw matrix is Phase B via "
            "galton.py --arm hw (plan §0/§5)")
    if arm not in ("ideal", "noisy"):
        raise ValueError(f"unknown sim arm {arm!r}; expected 'ideal' or 'noisy'")
    use_seeds = [cfg.seed] if arm == "ideal" else list(seeds)
    paths: list[str] = []
    for n in depths:
        for s in use_seeds:
            path, _ = run_arm(arm, n, cfg, s)
            paths.append(path)
    return paths


# --- loading + grouping run.json (both phases) ------------------------------

def load_run(path: str) -> tuple[int, int, str, dict[int, float]]:
    """One run.json -> (steps, seed, backend, int-keyed position histogram).

    Re-``int()``s the string-keyed histogram via ``metrics.to_int_hist``
    (pipeline.py:101) so the P3 metrics consume the loaded run directly. Sparse:
    the histogram is not densified (plan §11).
    """
    with open(path) as f:
        payload = json.load(f)
    meta = payload["meta"]
    hist = metrics.to_int_hist(payload["position_histogram"])
    return int(meta["steps"]), int(meta["seed"]), str(meta["backend"]), hist


def _resolve_run_paths(arm: str, run_paths_or_dir) -> list[str]:
    """Accept a run.json path list, a single path, or a directory to glob."""
    if isinstance(run_paths_or_dir, (list, tuple)):
        return list(run_paths_or_dir)
    if os.path.isdir(run_paths_or_dir):
        return sorted(glob.glob(
            os.path.join(run_paths_or_dir, f"{arm}_*_run.json")))
    return [run_paths_or_dir]


def _load_reference(reference_summary) -> dict[int, dict[int, float]]:
    """A reference arm's summary (path or dict) -> {steps: int-keyed mean hist}."""
    if reference_summary is None:
        return {}
    if isinstance(reference_summary, str):
        with open(reference_summary) as f:
            reference_summary = json.load(f)
    out: dict[int, dict[int, float]] = {}
    for entry in reference_summary.get("per_depth", []):
        out[int(entry["steps"])] = metrics.to_int_hist(
            entry["position_histogram"])
    return out


def _mean_hist(hists: list[dict[int, float]]) -> dict[int, float]:
    """Average probability per position over seeds (union support, sparse-safe)."""
    if not hists:
        return {}
    positions: set[int] = set()
    for h in hists:
        positions |= set(h)
    k = len(hists)
    return {pos: sum(h.get(pos, 0.0) for h in hists) / k
            for pos in sorted(positions)}


# --- aggregation -> summary.json (both phases; AC-4.1/4.2/4.4 data) ---------

def aggregate(arm: str, run_paths_or_dir, *,
              backend: str | None = None,
              reference_summary=None,
              cfg: config.Config | None = None,
              out_dir: str = pipeline.RESEARCH_RUNS_DIR) -> str:
    """Group runs by depth, feed the P3 metrics + knee, write one summary.json.

    Per depth, across its seeds: per-seed ``variance``/``horn_contrast``/
    ``entropy`` (metrics.py) then their **mean ± std** (``std`` ddof=0,
    QuantumLife style, research_qtree.py:410) plus the **mean position
    histogram**. The per-depth ``variance_mean``/``horn_contrast_mean`` series
    feed ``metrics.local_variance_exponent`` (a_local) and
    ``metrics.crossover_depth`` (the sweep-level knee, in ``meta``).

    M2 pairings (OQ-4.7): each arm-vs-binomial distance is always computed
    (closed-form reference, every phase); the arm-vs-ideal distance is filled
    only when a ``reference_summary`` (the ideal sweep) is supplied and this arm
    is not ``ideal`` — else ``None`` (nulls where a pairing is unavailable this
    phase). Written via the frozen ``pipeline.write_summary``; no frozen key is
    added (plan §5).
    """
    run_paths = _resolve_run_paths(arm, run_paths_or_dir)
    if not run_paths:
        raise ValueError(f"aggregate: no run.json found for arm {arm!r}")

    # dedup by (steps, seed): the latest file wins (filenames sort by timestamp),
    # so an arm re-run over the same seed does not double-count.
    by_seed: dict[tuple[int, int], dict[int, float]] = {}
    files_by_depth: dict[int, list[str]] = defaultdict(list)
    backends: set[str] = set()
    for p in sorted(run_paths):
        steps, seed, bk, hist = load_run(p)
        by_seed[(steps, seed)] = hist
        files_by_depth[steps].append(os.path.basename(p))
        backends.add(bk)

    hists_by_depth: dict[int, list[dict[int, float]]] = defaultdict(list)
    for (steps, _seed), hist in by_seed.items():
        hists_by_depth[steps].append(hist)

    depths = sorted(hists_by_depth)
    reference = _load_reference(reference_summary)

    per_depth: list[dict] = []
    variance_mean_series: list[float] = []
    contrast_mean_series: list[float] = []
    mean_hist_by_depth: dict[int, dict[int, float]] = {}

    for n in depths:
        seed_hists = hists_by_depth[n]
        variances = np.array([metrics.variance(h) for h in seed_hists], float)
        contrasts = np.array([metrics.horn_contrast(h) for h in seed_hists], float)
        entropies = np.array([metrics.entropy(h) for h in seed_hists], float)
        mhist = _mean_hist(seed_hists)
        mean_hist_by_depth[n] = mhist
        variance_mean_series.append(float(variances.mean()))
        contrast_mean_series.append(float(contrasts.mean()))

        binom = analytics.binomial_reference(n)
        tv_bin = metrics.tv_distance(mhist, binom)
        hell_bin = metrics.hellinger(mhist, binom)
        if arm != "ideal" and n in reference:
            tv_ideal = metrics.tv_distance(mhist, reference[n])
            hell_ideal = metrics.hellinger(mhist, reference[n])
        else:
            tv_ideal = hell_ideal = None

        per_depth.append({
            "steps": n,
            "run_files": files_by_depth[n],
            "position_histogram": {str(pos): p for pos, p in mhist.items()},
            "metrics": {
                "variance_mean": float(variances.mean()),
                "variance_std": float(variances.std(ddof=0)),
                "horn_contrast_mean": float(contrasts.mean()),
                "horn_contrast_std": float(contrasts.std(ddof=0)),
                "entropy_mean": float(entropies.mean()),
                "entropy_std": float(entropies.std(ddof=0)),
                "a_local": None,               # filled below once the series exists
                "tv_to_ideal": tv_ideal,
                "hellinger_to_ideal": hell_ideal,
                "tv_to_binomial": tv_bin,
                "hellinger_to_binomial": hell_bin,
            },
        })

    # a_local(t) and the sweep knee need >= 2 depths (metrics.py raises otherwise);
    # a single-depth aggregate leaves a_local/knee None (an honest degenerate case).
    knee: dict = {"knee_depth": None, "exponent_knee": None,
                  "contrast_knee": None, "rule": None}
    variance_exponent: dict | None = None
    if len(depths) >= 2:
        a_local = dict(metrics.local_variance_exponent(
            depths, variance_mean_series))
        for entry in per_depth:
            entry["metrics"]["a_local"] = a_local.get(entry["steps"])
        knee = metrics.crossover_depth(
            depths, variance_mean_series, contrast_mean_series)
        variance_exponent = metrics.variance_exponent(
            depths, variance_mean_series)

    resolved_backend = backend or (sorted(backends)[0] if backends else "sim")
    all_files = sorted(f for fs in files_by_depth.values() for f in fs)
    all_seeds = sorted({seed for (_steps, seed) in by_seed})

    meta = {
        "project": "QuantumGaltonBoard",
        "arm": arm,
        "backend": resolved_backend,
        "phase": "A",
        "hw_error_bars": False,               # Phase A: sim knee, no hw error bars
        "depths": depths,
        "shots": cfg.shots if cfg is not None else None,
        "seeds": all_seeds,
        "walk_spec": dict(WALK_SPEC),          # embedded verbatim (P5 decoder parity)
        "timestamp": pipeline.timestamp(),
        "run_files": all_files,
        "knee_depth": knee["knee_depth"],
        "exponent_knee": knee["exponent_knee"],
        "contrast_knee": knee["contrast_knee"],
        "rule": knee["rule"],
        "variance_exponent": variance_exponent,
        "environment": cfg.environment if cfg is not None else {},
    }
    return pipeline.write_summary(meta, per_depth, out_dir=out_dir)


# --- script entry (own argparse; does not touch the frozen galton.py) -------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="P4 depth×arm sim sweep + aggregation (plan §5).")
    p.add_argument("--arm", choices=["ideal", "noisy"], required=True,
                   help="sim arm to drive/aggregate (hw is Phase B via galton.py)")
    p.add_argument("--run", action="store_true",
                   help="drive the sim sweep first (writes runs/*_run.json)")
    p.add_argument("--aggregate", action="store_true",
                   help="aggregate the arm's runs into research_runs/*_summary.json")
    p.add_argument("--depths", type=str, default=None,
                   help="comma/space depth list; default 2..n_max step 2")
    p.add_argument("--reference-summary", type=str, default=None,
                   help="ideal summary.json for the noisy-vs-ideal M2 pairings")
    p.add_argument("--backend", type=str, default=None)
    p.add_argument("--shots", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--n-max", dest="n_max", type=int, default=None)
    return p


def _parse_depths(raw: str | None, cfg: config.Config) -> list[int]:
    if raw:
        return [int(x) for x in raw.replace(",", " ").split()]
    return list(range(2, cfg.n_max + 1, 2))


def main() -> int:
    args = _build_parser().parse_args()
    cfg = config.load(args)
    depths = _parse_depths(args.depths, cfg)

    if args.run:
        paths = run_sim_sweep(args.arm, depths, cfg.seeds, cfg)
        print(f"ran {len(paths)} {args.arm} run(s) over depths {depths}")

    if args.aggregate:
        out = aggregate(args.arm, pipeline.RUNS_DIR,
                        reference_summary=args.reference_summary, cfg=cfg)
        with open(out) as f:
            summary = json.load(f)
        m = summary["meta"]
        print(f"wrote {out}")
        print(f"  arm={m['arm']} backend={m['backend']} depths={m['depths']}")
        print(f"  knee_depth={m['knee_depth']} contrast_knee={m['contrast_knee']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
