"""One-off Fig. 3: M1 sim points vs. the analytic anchor (epic OQ-7.3).

Reads results/metrics.csv (P5's frozen 2026-08-03 full run) and overlays each
source's simulated poisoning rate against the closed-form anchor of
diag_cliff.anchor() -- the same formula thesis.tex Eq. 1 states. Standalone;
does not touch testbed/ or results/. Run from thesis/ via `make`, or directly:

  python3 figures/anchor_validation.py

Emits figures/anchor_validation.png (Fig. 3).
"""
from __future__ import annotations

import csv
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # DNSPoisonRace/thesis
_PROJECT = os.path.dirname(_ROOT)  # DNSPoisonRace/
sys.path.insert(0, _PROJECT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from testbed import config
from testbed.draw.source_model import attacker_search_bits

METRICS_CSV = os.path.join(_PROJECT, "results", "metrics.csv")
OUT_PNG = os.path.join(_HERE, "anchor_validation.png")

TXID, PORT = config.TXID_BITS, config.PORT_BITS
SEND = config.CLIFF_SEND_RATE_PPS
RTT = config.RTT_SECONDS
R_ROUNDS = config.MAX_RETRANSMITS + 1


def anchor(kind: str, eff: int, q: int = 1) -> float:
    k = max(0, TXID + PORT - eff)
    sbits = attacker_search_bits(
        kind, txid_bits=TXID, port_bits=PORT, k=k, prng_leak_bits=config.PRNG_LEAK_BITS
    )
    S = 1 << sbits
    g_live = min(int(SEND * RTT), S)
    if config.ATTACK_GUESS_BUDGET is not None:
        g_live = min(g_live, config.ATTACK_GUESS_BUDGET)
    windows = R_ROUNDS * q * config.ATTACK_ATTEMPTS
    return 1 - (1 - g_live / S) ** windows


def load_sim_points() -> dict[str, list[tuple[int, float]]]:
    points: dict[str, list[tuple[int, float]]] = {}
    with open(METRICS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if int(row["parallel_queries"]) != 1:
                continue  # M1 axis only, q=1 cells
            kind = row["kind"]
            eff = int(row["effective_bits"])
            rate = float(row["poison_rate"])
            points.setdefault(kind, []).append((eff, rate))
    for kind in points:
        points[kind] = sorted(set(points[kind]))
    return points


def main() -> int:
    sim = load_sim_points()
    kinds = ["fixed", "prng", "csprng", "qrng"]
    colors = {"fixed": "tab:red", "prng": "tab:orange", "csprng": "tab:blue", "qrng": "tab:green"}

    fig, ax = plt.subplots(figsize=(6, 4))
    worst = 0.0
    for kind in kinds:
        if kind not in sim:
            continue
        eff_vals = [e for e, _ in sim[kind]]
        sim_vals = [r for _, r in sim[kind]]
        anchor_vals = [anchor(kind, e) for e in eff_vals]
        worst = max(worst, max(abs(s - a) for s, a in zip(sim_vals, anchor_vals)))
        ax.plot(eff_vals, anchor_vals, "-", color=colors[kind], label=f"{kind} (anchor)", alpha=0.7)
        ax.scatter(eff_vals, sim_vals, color=colors[kind], marker="o", s=18, label=f"{kind} (sim)")

    ax.set_xlabel("effective entropy bits")
    ax.set_ylabel("poisoning probability")
    ax.set_title(f"Sim vs. analytic anchor (max |sim-anchor| = {worst:.3f})")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print(f"wrote {OUT_PNG}  max|sim-anchor|={worst:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
