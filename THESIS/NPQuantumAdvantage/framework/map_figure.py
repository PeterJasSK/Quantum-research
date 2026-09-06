"""AC-T0.8 — the single thesis figure, rendered from the ledger ONLY.

One axis, one threshold, one dot per problem: the √2 map. Subset problems sit on
the ``best_classical_exponent`` axis with a bold vertical line at 0.5 ("√2 line");
ordering problems live in a separate band ("collapses via 2^n Held–Karp DP") since
a fixed-``c`` axis is not meaningful for them. The 3-SAT reference survivor is
pinned at c = 1.0. Rows in ``EXPECTED_IDS`` absent from the ledger render greyed
"pending", so the figure exists from day one.

No math here beyond reading the ledger — figure only.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless; must precede pyplot import

import matplotlib.pyplot as plt  # noqa: E402

from .ledger import EXPECTED_IDS, load  # noqa: E402

# Colour-blind-safe verdict palette (OQ-4).
_COLOURS = {
    "SURVIVES": "#1b9e77",   # green
    "COLLAPSES": "#d95f02",  # orange
    "UNKNOWN": "#7570b3",    # purple-grey
    "pending": "#bdbdbd",    # light grey
}


def render(ledger_path: str = "research_runs/ledger.json", out: str = "research_runs/map") -> None:
    """Render ``map.png`` (150 DPI) and ``map.svg`` from the ledger at ``ledger_path``."""
    ledger = load(ledger_path)
    by_id = {r.id: r for r in ledger.rows}

    fig, (ax, band) = plt.subplots(
        2, 1, figsize=(9, 6), height_ratios=[3, 1], constrained_layout=True
    )

    # --- Subset panel: the √2 line -------------------------------------------
    ax.axvline(0.5, color="black", lw=2.5, zorder=1)
    ax.text(0.5, 0.5, " √2 line — Grover exponent 0.5", ha="left", va="center",
            rotation=90, transform=ax.get_xaxis_transform(), fontsize=9,
            fontweight="bold", color="black")

    subset_ids = [i for i in EXPECTED_IDS if by_id.get(i, None) is None
                  or by_id[i].search_space == "subset"]
    y = 0
    yticks: list[int] = []
    ylabels: list[str] = []
    for rid in subset_ids:
        row = by_id.get(rid)
        if row is None:
            ax.scatter(0.5, y, s=140, color=_COLOURS["pending"], edgecolor="black",
                       zorder=3, marker="o")
            ax.annotate("pending", (0.5, y), textcoords="offset points",
                        xytext=(8, 0), va="center", fontsize=8, color="grey")
            ylabels.append(rid)
        else:
            c = row.best_classical_exponent
            if c is None:
                continue  # a subset row must carry c; skip defensively
            ax.scatter(c, y, s=160, color=_COLOURS.get(row.verdict, _COLOURS["UNKNOWN"]),
                       edgecolor="black", zorder=3, marker="o")
            ax.annotate(f"{row.verdict}  c={c:.3f}", (c, y), textcoords="offset points",
                        xytext=(8, 0), va="center", fontsize=8)
            ylabels.append(row.name)
        yticks.append(y)
        y += 1

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_xlim(0.0, 1.15)
    ax.set_ylim(-0.6, max(y - 0.4, 0.6))
    ax.set_xlabel("best-known-classical exponent  c  in  2^{c·n}   "
                  "(SURVIVES → right of line, COLLAPSES → left)")
    ax.set_title("The Quantum Query-Advantage Map — survive/collapse across the √2 line",
                 fontsize=11)
    ax.grid(axis="x", ls=":", alpha=0.4)

    # --- Ordering band: fixed-c axis not meaningful --------------------------
    band.set_title("ordering / assignment problems — collapse via 2^n Held–Karp DP "
                   "(√(n!) exceeds 2^n for n>4)", fontsize=9)
    ordering_ids = [i for i in EXPECTED_IDS
                    if by_id.get(i) is not None and by_id[i].search_space == "ordering"]
    if ordering_ids:
        x = 0
        labels = []
        for rid in ordering_ids:
            row = by_id[rid]
            band.scatter(x, 0, s=160, color=_COLOURS.get(row.verdict, _COLOURS["UNKNOWN"]),
                         edgecolor="black", zorder=3)
            labels.append(f"{row.name}\n{row.verdict}")
            x += 1
        band.set_xticks(range(len(labels)))
        band.set_xticklabels(labels, fontsize=7)
        band.set_xlim(-0.6, max(x - 0.4, 0.6))
    else:
        band.text(0.5, 0.5, "no ordering rows yet (pending)", ha="center", va="center",
                  transform=band.transAxes, color="grey", fontsize=9)
        band.set_xticks([])
    band.set_yticks([])

    fig.savefig(f"{out}.png", dpi=150)
    fig.savefig(f"{out}.svg")
    plt.close(fig)
