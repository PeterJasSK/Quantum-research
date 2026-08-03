"""The two headline figures (epic §9 P5, AC-5.1/AC-5.2): entropy-cliff (M1) and SAD-DNS
collapse (M4). `matplotlib.use("Agg")` (headless), pandas over P4's one CSV. Default
matplotlib theme (OQ-P5.5) -- the *web* demo (P6) owns dark mode, not these paper figures.
Mirrors the ECMP twin's `analysis/graphs.py` (Agg, PNG+SVG, no explicit dpi, tight_layout).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from testbed import config  # noqa: E402

_KIND_COLORS = {
    "fixed": "tab:blue",
    "prng": "tab:orange",
    "csprng": "tab:green",
    "qrng": "tab:red",
}


def _load(csv_path: str = config.RESULTS_CSV_PATH) -> pd.DataFrame:
    """Read the frozen P4 CSV; if a cell was run more than once (appended rows), keep the
    last row per `(kind, effective_bits, k, send_rate_pps, parallel_queries)` key so a
    rerun supersedes cleanly."""
    df = pd.read_csv(csv_path)
    key = ["kind", "effective_bits", "k", "send_rate_pps", "parallel_queries"]
    return df.drop_duplicates(subset=key, keep="last")


def render_cliff(
    csv_path: str = config.RESULTS_CSV_PATH, output_prefix: str = config.CLIFF_FIG_PATH
) -> Path:
    """AC-5.1: poison_rate vs effective_bits, one line per source. The CSPRNG/QRNG lines
    are *expected* to coincide (epic §3.2 null result) -- plotted honestly, dashed for
    qrng only for visibility, never hidden."""
    df = _load(csv_path)
    cliff = df[df["parallel_queries"] == 1]

    fig, ax = plt.subplots()
    for kind, color in _KIND_COLORS.items():
        rows = cliff[cliff["kind"] == kind].sort_values("effective_bits")
        if rows.empty:
            continue
        style = "--" if kind == "qrng" else "-"
        ax.plot(rows["effective_bits"], rows["poison_rate"], style, color=color, label=kind)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Effective entropy (bits)")
    ax.set_ylabel("Poisoning success probability")
    ax.set_title("Entropy cliff")
    ax.legend()
    fig.tight_layout()

    out = Path(output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".svg"))
    plt.close(fig)
    return out.with_suffix(".png")


def render_collapse(
    csv_path: str = config.RESULTS_CSV_PATH, output_prefix: str = config.COLLAPSE_FIG_PATH
) -> Path:
    """AC-5.2: poison_rate vs k (SAD-DNS port bits leaked), CSPRNG only, bounded to the
    legal leak range `[0, PORT_BITS]`."""
    df = _load(csv_path)
    collapse = df[(df["kind"] == "csprng") & (df["k"] <= config.PORT_BITS)].sort_values("k")

    fig, ax = plt.subplots()
    ax.plot(collapse["k"], collapse["poison_rate"], "-", color="tab:green")
    ax.set_ylim(0, 1)
    ax.set_xlabel("SAD-DNS port bits leaked (k)")
    ax.set_ylabel("Poisoning success probability")
    ax.set_title("SAD-DNS collapse")
    fig.tight_layout()

    out = Path(output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".svg"))
    plt.close(fig)
    return out.with_suffix(".png")


def render_graphs(csv_path: str = config.RESULTS_CSV_PATH) -> tuple[Path, Path]:
    return render_cliff(csv_path=csv_path), render_collapse(csv_path=csv_path)
