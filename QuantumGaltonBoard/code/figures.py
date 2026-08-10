#!/usr/bin/env python3
"""
figures.py — Quantum Galton Board: the two headline figures (P4, plan §7).

Renders from an aggregated summary.json (or two, for cross-arm overlays); no
business logic — it reads already-aggregated per-depth series and draws. The
non-interactive ``Agg`` backend is forced so the module runs headless in the
offline gate (plan §7). matplotlib is confined to THIS module (epic §9 P1); the
sweep/aggregate/replay path never imports it.

  fig_horns_melting(summaries, depths_to_show, out_stem)  (AC-4.1) — a
      small-multiples grid: columns = a shallow->deep depth subset, rows = arms
      present (ideal, noisy; hw added in Phase B). Each cell bar-plots that arm's
      mean position_histogram and overlays ``analytics.binomial_reference(n)`` as
      the dashed "classical hump". Reading left->right and top->bottom shows the
      ideal twin horns eroding toward the hump.
  fig_collapse_curve(summary, out_stem)  (AC-4.2) — twin-axis vs depth:
      ``horn_contrast_mean`` (± std band) left, ``a_local`` right, a dashed line
      at the ballistic/diffusive midpoint 1.5 and at contrast half-max, and a
      vertical marker at ``meta.knee_depth`` / ``meta.contrast_knee``.

Both functions already loop over "arms present" / "points with optional error
bars", so Phase B is a small addition (hw row + hw error bars), not a rewrite.
Each writes PNG (paper raster) + SVG (paper vector); returns the written paths.
"""

from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")                       # headless; must precede pyplot import
import matplotlib.pyplot as plt              # noqa: E402

import analytics                             # noqa: E402
import metrics                               # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.normpath(os.path.join(_HERE, "..", "figures"))
RESEARCH_RUNS_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))


def _load(summary) -> dict:
    """A summary.json path or already-loaded dict -> dict."""
    if isinstance(summary, str):
        with open(summary) as f:
            return json.load(f)
    return summary


def _save(fig, out_stem: str) -> list[str]:
    """Write ``<out_stem>.png`` and ``<out_stem>.svg``; return both paths."""
    os.makedirs(os.path.dirname(os.path.abspath(out_stem)), exist_ok=True)
    paths = []
    for ext in ("png", "svg"):
        path = f"{out_stem}.{ext}"
        fig.savefig(path, bbox_inches="tight", dpi=150)
        paths.append(path)
    plt.close(fig)
    return paths


def _depth_index(summary: dict) -> dict[int, dict]:
    """{steps: per_depth entry} for O(1) lookup by depth."""
    return {int(e["steps"]): e for e in summary["per_depth"]}


def fig_horns_melting(summaries, depths_to_show: list[int],
                      out_stem: str) -> list[str]:
    """AC-4.1: small-multiples grid of mean histograms + dashed binomial hump.

    ``summaries`` is one-or-more summary.json (paths or dicts), one row per arm.
    ``depths_to_show`` selects the columns (shallow->deep). Cells whose depth is
    absent from an arm's sweep are left blank. Positions are the signed lattice
    (-n..+n step 2); the dashed line is the classical ``binomial_reference(n)``.
    """
    if not isinstance(summaries, (list, tuple)):
        summaries = [summaries]
    loaded = [_load(s) for s in summaries]
    indices = [_depth_index(s) for s in loaded]

    n_rows = len(loaded)
    n_cols = len(depths_to_show)
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(2.6 * n_cols, 2.4 * n_rows),
        squeeze=False, sharex="col")

    for r, (summary, index) in enumerate(zip(loaded, indices)):
        arm = summary["meta"]["arm"]
        backend = summary["meta"]["backend"]
        for c, n in enumerate(depths_to_show):
            ax = axes[r][c]
            entry = index.get(int(n))
            if entry is not None:
                hist = metrics.to_int_hist(entry["position_histogram"])
                positions = sorted(hist)
                ax.bar(positions, [hist[p] for p in positions],
                       width=1.4, color="#3b7dd8", alpha=0.85,
                       label=arm)
                binom = analytics.binomial_reference(int(n))
                bpos = sorted(binom)
                ax.plot(bpos, [binom[p] for p in bpos], "--",
                        color="#d1495b", linewidth=1.3, label="binomial")
            else:
                ax.text(0.5, 0.5, "—", ha="center", va="center",
                        transform=ax.transAxes, color="#999")
            if r == 0:
                ax.set_title(f"n = {n}", fontsize=10)
            if c == 0:
                ax.set_ylabel(f"{arm}\n({backend})", fontsize=9)
            ax.tick_params(labelsize=7)

    axes[0][-1].legend(fontsize=7, loc="upper right")
    fig.suptitle(
        "Horns melting: ideal twin horns eroding toward the classical hump "
        "(dashed) with depth/noise\n(hw row added in Phase B)",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return _save(fig, out_stem)


def fig_collapse_curve(summary, out_stem: str) -> list[str]:
    """AC-4.2: twin-axis collapse curve — horn contrast (±std) + a_local vs depth.

    Left axis: ``horn_contrast_mean`` with a ± std band. Right axis: the local
    variance exponent ``a_local``. Dashed horizontals at the ballistic/diffusive
    midpoint 1.5 and at contrast half-max; dashed verticals at ``meta.knee_depth``
    (defended) and ``meta.contrast_knee`` (corroborating). Phase B overlays the hw
    points with vertical error bars and the hw knee band (plan §6).
    """
    summary = _load(summary)
    meta = summary["meta"]
    entries = sorted(summary["per_depth"], key=lambda e: int(e["steps"]))
    depths = [int(e["steps"]) for e in entries]
    contrast = [e["metrics"]["horn_contrast_mean"] for e in entries]
    contrast_std = [e["metrics"].get("horn_contrast_std", 0.0) or 0.0
                    for e in entries]
    a_local = [e["metrics"].get("a_local") for e in entries]

    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.set_xlabel("walk depth n (steps)")
    ax1.set_ylabel("horn contrast M3", color="#d1495b")
    ax1.plot(depths, contrast, "-o", color="#d1495b", label="horn contrast")
    lo = [c - s for c, s in zip(contrast, contrast_std)]
    hi = [c + s for c, s in zip(contrast, contrast_std)]
    ax1.fill_between(depths, lo, hi, color="#d1495b", alpha=0.18)
    ax1.tick_params(axis="y", labelcolor="#d1495b")
    if any(c is not None for c in contrast):
        half = 0.5 * max(contrast)
        ax1.axhline(half, ls="--", color="#d1495b", alpha=0.5,
                    label="contrast half-max")

    ax2 = ax1.twinx()
    ax2.set_ylabel("local variance exponent a(t) M1", color="#3b7dd8")
    a_depths = [d for d, a in zip(depths, a_local) if a is not None]
    a_values = [a for a in a_local if a is not None]
    ax2.plot(a_depths, a_values, "-s", color="#3b7dd8", label="a_local")
    ax2.axhline(1.5, ls="--", color="#3b7dd8", alpha=0.6,
                label="ballistic/diffusive midpoint 1.5")
    ax2.tick_params(axis="y", labelcolor="#3b7dd8")

    knee = meta.get("knee_depth")
    if knee is not None:
        ax1.axvline(knee, ls="--", color="black", alpha=0.7,
                    label=f"knee ≈ {knee:.2f}")
    contrast_knee = meta.get("contrast_knee")
    if contrast_knee is not None:
        ax1.axvline(contrast_knee, ls=":", color="grey", alpha=0.7,
                    label=f"contrast knee ≈ {contrast_knee:.2f}")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="best")
    knee_label = "sim (no hw error bars — Phase B)"
    fig.suptitle(
        f"Collapse curve — {meta['arm']} ({meta['backend']}), {knee_label}",
        fontsize=11)
    fig.tight_layout()
    return _save(fig, out_stem)


# --- script entry: render both figures from the latest research_runs summaries

def _latest_summary(arm: str, out_dir: str = RESEARCH_RUNS_DIR) -> str | None:
    import glob
    matches = sorted(glob.glob(os.path.join(out_dir, f"{arm}_*_summary.json")))
    return matches[-1] if matches else None


def main() -> int:
    summaries = []
    for arm in ("ideal", "noisy"):
        path = _latest_summary(arm)
        if path is not None:
            summaries.append(path)
    if not summaries:
        print("no research_runs/*_summary.json found; run sweep.py --aggregate first")
        return 1

    loaded = [_load(s) for s in summaries]
    all_depths = sorted({int(e["steps"]) for s in loaded for e in s["per_depth"]})
    # a shallow->deep column subset (<= 5 columns) spanning the sweep
    if len(all_depths) > 5:
        idx = [round(i * (len(all_depths) - 1) / 4) for i in range(5)]
        depths_to_show = sorted({all_depths[i] for i in idx})
    else:
        depths_to_show = all_depths

    horns = fig_horns_melting(
        summaries, depths_to_show, os.path.join(FIGURES_DIR, "horns_melting"))
    print("wrote", *horns, sep="\n  ")
    # collapse curve prefers the noisy sweep (the one that collapses)
    collapse_summary = summaries[-1]
    collapse = fig_collapse_curve(
        collapse_summary, os.path.join(FIGURES_DIR, "collapse_curve"))
    print("wrote", *collapse, sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
