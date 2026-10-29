"""Figures for D from grow runs.

    python -m D_quantum_growth.src.figures --ideal <run> --heron <run> [--heron-dd <run>]

Writes lineage_witness.png, cellcycle_memory_advantage.png, qca_snapshot_2d.png, qca_mi_network.png and
simulability.png into D_quantum_growth/figures/. Every title carries the sim label."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from shared import RE_ROOT
from shared.simbackend import sim_label

FIG = RE_ROOT / "D_quantum_growth" / "figures"
RUNS = RE_ROOT / "D_quantum_growth" / "runs"


def _j(run: Path, name: str):
    return json.loads((run / name).read_text())


def lineage_witness(runs: dict[str, Path]) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4))
    cols = {"ideal": "C0", "heron": "C3", "heron+DD": "C2"}
    for k, (name, run) in enumerate(runs.items()):
        d = _j(run, "lineage_detail.json")["per_generation"]
        g = sorted(int(x.split("_g")[1]) for x in d)
        ax.errorbar(np.array(g) + 0.12 * (k - 1), [d[f"XX+ZZ_g{x}"]["value"] for x in g],
                    [d[f"XX+ZZ_g{x}"]["stderr"] for x in g], fmt="o-", color=cols[name],
                    label=f"{name}: {sim_label('ideal' if name == 'ideal' else 'heron')}")
    ax.axhline(1, color="k", ls="--", lw=0.8, label="witness threshold 1")
    ax.set_xlabel("generation g (non-test)"); ax.set_ylabel("<XX>_g + <ZZ>_g")
    ax.set_title("Lineage division-pair witness", fontsize=9); ax.legend(fontsize=6)
    fig.tight_layout(); fig.savefig(FIG / "lineage_witness.png", dpi=130)


def memory(runs: dict[str, Path]) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
    for k, (mode, run) in enumerate(runs.items()):
        d = _j(run, "memory_advantage_detail.json")
        ax[0].bar([3 * k, 3 * k + 1, 3 * k + 2],
                  [d["d_kl_quantum_bits_per_symbol"], d["d_kl_classical_1bit_sampled"],
                   d["d_kl_classical_1bit_bits_per_symbol"]],
                  color=["C0", "C1", "C7"], label=None)
        ax[0].text(3 * k + 1, ax[0].get_ylim()[1] * 0.02, mode, ha="center", fontsize=7)
        ax[1].errorbar([k], [d["C_q_measured"]], [d["C_q_measured_stderr"]], fmt="o", color="C0")
        ax[1].plot([k], [d["C_q_theory"]], "k_", ms=14)
    ax[0].set_xticks([]); ax[0].set_ylabel("d_KL (bits/symbol)")
    ax[0].set_title("blue: quantum (sampled)  orange: best 1-bit classical (same sample count)\n"
                    "grey: classical exact; sampling floor ~0.0018", fontsize=6)
    ax[1].axhline(_j(next(iter(runs.values())), "memory_advantage_detail.json")["C_mu"], color="r", ls="--",
                  label="C_mu (classical)")
    ax[1].set_xticks(range(len(runs))); ax[1].set_xticklabels([sim_label(m) for m in runs], fontsize=5)
    ax[1].set_ylabel("memory entropy (bits)"); ax[1].set_title("C_q measured (dot) vs theory (bar)", fontsize=8)
    ax[1].legend(fontsize=6)
    fig.suptitle("Cell-cycle division timer, 1-qubit quantum model (L=10)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "cellcycle_memory_advantage.png", dpi=130)


def qca_figs(run: Path, mode: str) -> None:
    d = _j(run, "qca_detail.json")
    nodes = d["patch_nodes"]
    pos = {n: d["coords"][str(n)] for n in nodes}
    w = _j(run, "witness_record_qca.json")
    snap = dict(zip(nodes, d["snapshot_bits"]))
    edges = [(nodes[e["i"]], nodes[e["j"]], e["mi"]) for e in w["mi_network"]["edges"]]
    occ = np.load(run / "seed_shape.npz")["occupancy"]
    fig = plt.figure(figsize=(10, 3.8))
    a0 = fig.add_subplot(1, 2, 1)
    for u, v, _ in edges:
        a0.plot(*zip(pos[u], pos[v]), color="0.7", lw=1, zorder=1)
    a0.scatter([pos[n][0] for n in nodes], [pos[n][1] for n in nodes], c=[snap[n] for n in nodes], cmap="coolwarm",
               s=90, edgecolor="k", zorder=2)
    c = d["centre"]
    a0.scatter([pos[c][0]], [pos[c][1]], marker="*", s=240, facecolor="none", edgecolor="g", zorder=3)
    a0.set_aspect("equal"); a0.axis("off")
    a0.set_title(f"QCA Z snapshot at t={d['t_max']} ({d['patch_kind']} patch), {sim_label(mode)}", fontsize=7)
    mid = [occ.shape[0] // 2, occ.shape[1] // 2, occ.shape[2] // 2]
    for k, (sl, nm) in enumerate(((occ[mid[0]], "z-slice"), (occ[:, mid[1]], "y-slice"), (occ[:, :, mid[2]], "x-slice"))):
        ax = fig.add_axes([0.52 + 0.16 * k, 0.15, 0.14, 0.6])
        ax.imshow(sl, cmap="gray_r", origin="lower"); ax.axis("off"); ax.set_title(nm, fontsize=7)
    fig.text(0.52, 0.85, f"3-D seed shape (0.5 mm voxels), n_cells={int(occ.sum())}", fontsize=7)
    fig.savefig(FIG / "qca_snapshot_2d.png", dpi=130)

    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    neg = d["negativity"]
    mx = max(max(e[2] for e in edges), 1e-9)
    for u, v, mi in edges:
        n = neg.get(f"{min(u, v)}_{max(u, v)}", neg.get(f"{max(u, v)}_{min(u, v)}"))
        ax.plot(*zip(pos[u], pos[v]), color=plt.cm.viridis(mi / mx), lw=1 + 5 * mi / mx, zorder=1)
        mid_ = np.mean([pos[u], pos[v]], 0)
        ax.text(mid_[0], mid_[1], f"{n['value']:.2f}" if n else "", fontsize=5, ha="center", color="r")
    ax.scatter([pos[n][0] for n in nodes], [pos[n][1] for n in nodes], s=40, c="w", edgecolor="k", zorder=2)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"QCA MI network (colour/width = MI), red = negativity N_ij\n{sim_label(mode)}, witness passed={d['witness_passed']}",
                 fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "qca_mi_network.png", dpi=130)


def simulability(runs: dict[str, Path]) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4))
    rows = _j(next(iter(runs.values())), "simulability_detail.json")["rows"]
    for name in dict.fromkeys(r["name"] for r in rows):
        rr = [r for r in rows if r["name"] == name]
        ax.plot([r["bond_dim"] for r in rr], [r["fidelity_vs_sim"] for r in rr], "o-", label=name)
    ax.axhline(0.99, color="k", ls="--", lw=0.8)
    ax.set_xscale("log", base=2); ax.set_xlabel("bond dimension chi"); ax.set_ylabel("fidelity_vs_sim (Q6)")
    ax.set_title("Belief-propagation adversary vs ideal simulation (classical; circuits as in the ideal run)", fontsize=7)
    ax.legend(fontsize=6)
    fig.tight_layout(); fig.savefig(FIG / "simulability.png", dpi=130)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ideal", required=True)
    ap.add_argument("--heron", required=True)
    ap.add_argument("--heron-dd")
    ap.add_argument("--lineage-heron", help="standalone 20000-shot lineage heron run matching --heron-dd")
    a = ap.parse_args()
    r = lambda p: RUNS / p if not Path(p).is_absolute() else Path(p)
    lw = {"ideal": r(a.ideal), "heron": r(a.lineage_heron or a.heron)}
    if a.heron_dd:
        lw["heron+DD"] = r(a.heron_dd)
    lineage_witness(lw)
    memory({"ideal": r(a.ideal), "heron": r(a.heron)})
    qca_figs(r(a.ideal), "ideal")
    simulability({"ideal": r(a.ideal)})


if __name__ == "__main__":
    main()
