"""Renders the two paper deliverables (AC-6, AC-7, plan-5 Design "2.
Analysis + graphs"): Graph 1 (attacker success x salt source x knowledge
level) and Graph 2 (the rotation-frequency threshold curve). Pandas read of
the P4 CSVs, matplotlib render -- no live infra.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from testbed.analysis.rotation_threshold import rotation_threshold, t_try_from_reconstruction  # noqa: E402
from testbed.analysis.success import attacker_succeeded  # noqa: E402
from testbed.config import GRAPH1_PATH, GRAPH2_PATH, KNOWLEDGE_LEVELS, PRNG_SEED_SPACE_BITS, SALT_SOURCES  # noqa: E402
from testbed.experiments.matrix import GRAPH1, EXP5_SWEEP, ExperimentCell  # noqa: E402


def _summary_path(cell: ExperimentCell) -> Path:
    return Path(cell.csv_path).with_suffix(".summary.csv")


def _read_summary_row(cell: ExperimentCell) -> dict | None:
    path = _summary_path(cell)
    if not path.exists():
        return None
    with path.open() as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def _read_record(cell: ExperimentCell) -> dict | None:
    path = Path(cell.csv_path).with_suffix(".record.json")
    if not path.exists():
        return None
    return json.loads(path.read_text())


def render_graph1(output_prefix: str = GRAPH1_PATH) -> Path:
    """3x3 grid: salt source x knowledge level, coloured by `success.py`'s
    predicate over each cell's summary row. csprng/qrng+rotation cells that
    both fail make the null result visible (identical fail colouring)."""
    grid = pd.DataFrame(index=list(KNOWLEDGE_LEVELS), columns=list(SALT_SOURCES), dtype=float)
    for cell in GRAPH1:
        row = _read_summary_row(cell)
        success = attacker_succeeded(row) if row is not None else None
        grid.loc[cell.knowledge_level, cell.salt_kind] = float("nan") if success is None else float(success)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(grid.values.astype(float), cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(SALT_SOURCES)))
    ax.set_xticklabels(SALT_SOURCES)
    ax.set_yticks(range(len(KNOWLEDGE_LEVELS)))
    ax.set_yticklabels(KNOWLEDGE_LEVELS)
    ax.set_xlabel("salt source")
    ax.set_ylabel("knowledge level")
    ax.set_title("Graph 1 -- attacker success x salt source x knowledge level")
    for i, level in enumerate(KNOWLEDGE_LEVELS):
        for j, source in enumerate(SALT_SOURCES):
            value = grid.iloc[i, j]
            label = "no data" if pd.isna(value) else ("success" if value else "fail")
            ax.text(j, i, label, ha="center", va="center", fontsize=9)
    fig.tight_layout()

    out = Path(output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".svg"))
    plt.close(fig)
    return out


def render_graph2(output_prefix: str = GRAPH2_PATH) -> Path:
    """Rotation-frequency threshold curve: x = rotation interval (log
    scale), y = time-to-saturation + packets-to-saturation, with the
    analytical T_bf drawn as a vertical line against the empirical crossover."""
    records = [(cell, _read_summary_row(cell)) for cell in EXP5_SWEEP]
    rows = [(cell.rotation_interval, row) for cell, row in records if row is not None]
    rows.sort(key=lambda pair: pair[0])

    fig, ax1 = plt.subplots(figsize=(7, 5))
    intervals = [interval for interval, _ in rows]
    time_to_sat = [float(row["time_to_saturation_s"]) if row["time_to_saturation_s"] else None for _, row in rows]
    packets_to_sat = [
        int(row["packets_to_saturation"]) if row["packets_to_saturation"] else None for _, row in rows
    ]

    ax1.plot(intervals, time_to_sat, "o-", color="tab:blue", label="time to saturation (s)")
    ax1.set_xscale("log")
    ax1.set_xlabel("rotation interval (s, log scale, slow -> fast)")
    ax1.set_ylabel("time to saturation (s)", color="tab:blue")

    ax2 = ax1.twinx()
    ax2.plot(intervals, packets_to_sat, "s--", color="tab:orange", label="packets to saturation")
    ax2.set_ylabel("packets to saturation", color="tab:orange")

    threshold = None
    first_record = next((_read_record(cell) for cell in EXP5_SWEEP if _read_record(cell) is not None), None)
    if first_record is not None:
        reconstruction = first_record["reconstruction"]
        t_try = t_try_from_reconstruction(reconstruction["elapsed_seconds"], reconstruction["attempts"])
        threshold = rotation_threshold(
            [row for _, row in rows], seed_space_bits=PRNG_SEED_SPACE_BITS, t_try=t_try
        )
        ax1.axvline(threshold.analytical_t_bf_seconds, color="tab:red", linestyle=":", label="analytical T_bf")
        if threshold.empirical_threshold_seconds is not None:
            ax1.axvspan(0, threshold.empirical_threshold_seconds, color="tab:green", alpha=0.1)

    ax1.set_title("Graph 2 -- rotation-frequency threshold curve")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    fig.tight_layout()

    out = Path(output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".svg"))
    plt.close(fig)
    if threshold is not None:
        print(threshold.recommendation)
    return out


def render_graphs() -> tuple[Path, Path]:
    return render_graph1(), render_graph2()
