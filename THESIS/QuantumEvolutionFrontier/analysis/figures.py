"""Fig. 1 (survival vs classical cost map) and Fig. 2 (CT classical-twin test), from the run JSONs only.

    /home/peter/anaconda3/bin/python3 THESIS/QuantumEvolutionFrontier/analysis/figures.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[3]
R = REPO / "THESIS/QuantumEvolutionFrontier/runs"
P = REPO / "THESIS/QuantumEvolutionFrontier/paper"
CORES = 8
# validated categorical palette (dataviz reference, light mode); identity also carried by marker shape + labels
C_TREE, C_QAL, C_CT, C_SIM = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2 = "#0b0b0b", "#52514e"
TIERS = [(3600.0, "core-hour"), (3.156e7, "core-year"), (3.156e13, r"$10^6$ core-years")]
MARK = {"W-a": "o", "W-b": "s", "W-c": "^", "W-d": "D"}

plt.rcParams.update({"font.size": 7, "font.family": "serif", "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6, "pdf.fonttype": 42})


def load(n):
    f = R / n
    return json.loads(f.read_text()) if f.exists() else None


def points() -> list[dict]:
    led, cc = load("ledger.json"), load("classical_cost.json")
    rep = load("teleport_replay.json")
    qt, ql, ds, ex = cc["qt"], cc["qalife"], cc["dscale"], cc.get("extra", {})
    arms = led["quantum_tree"]["arms"]
    t = lambda rows: float(np.mean([r["t_state_s"] + r["t_sample_s"] for r in rows]))
    pts = []
    a = arms["B_hw_ibm_kingston"]["c1"]
    pts.append(dict(lab="tree serial", q=108, rung="W-a", c=C_TREE, k=abs(led["quantum_tree"]["z_c1_B_vs_sim"]),
                    x=t(qt["serial_L2"]["rows"])))
    b = arms["bw_L2_ibm_kingston"]["c1"]
    pts.append(dict(lab="tree brick", q=108, rung="W-a", c=C_TREE, k=abs(b["mean"]) / b["se"], x=t(qt["brick_L2"]["rows"])))
    tel = led["teleport"].get("tel_herald_hw_ibm_marrakesh_d12")
    if tel and "teleport_herald_d12" in ex:
        pts.append(dict(lab="teleport bond", q=104, rung="W-a", c=C_TREE,
                        k=abs(tel["c_bond"]["mean"]) / tel["c_bond"]["se"], x=ex["teleport_herald_d12"]["t_sample_s"]))
    m4 = {r["W"]: r for r in led["qalife"]["month4_unitary"]}
    cm4 = {r["W"]: r for r in ql["month4_unitary"]}
    pts.append(dict(lab="QAL W=24", q=48, rung="W-a", c=C_QAL, k=m4[24]["k_sigma"],
                    x=cm4[24]["t_state_s"] + cm4[24]["t_sample_s"]))
    pj = {r["W"]: r for r in led["qalife"]["pj0"] if r["death"] == "natural" and r["phenotype"] == "separable"}
    cpj = {r["W"]: r for r in ql["pj0_natural_separable"]}
    pts.append(dict(lab="germ/soma W=50", q=100, rung="W-a", c=C_QAL, k=pj[50]["k_sigma"],
                    x=cpj[50]["t_state_s"] + cpj[50]["t_sample_s"]))
    mot = [fr for fr in led["motile"]["frames"] if fr["certified"]]
    sig = math.sqrt(2) * mot[0]["w_sigma"]
    pts.append(dict(lab="motile ghz2", q=16, rung="W-b", c=C_QAL, k=(min(fr["w_plus_zz"] for fr in mot) - 1) / sig,
                    x=ex["motile_org2_L4"]["t_sample_s"]))
    S = led["phantoms"]["chsh"]
    pts.append(dict(lab="CHSH roll", q=2, rung="W-d", c=C_CT, k=S["z_above_2"], x=ex["chsh_roll"]["t_sample_s"]))
    g = led["phantoms"]["ghz_spine"]
    pts.append(dict(lab="GHZ spine", q=28, rung="W-c", c=C_CT, k=(g["F_dfe"] - 0.5) / g["F_sigma"], x=ds["ghz_spine"]["t_s"]))
    neg = led["phantoms"]["claims"][1]
    pts.append(dict(lab="QCA t=2", q=23, rung="W-b", c=C_CT, k=neg["value"] / neg["sigma"],
                    x=max(r["t_state_s"] + r["t_sample_s"] for r in ds["ch_qca_tiles"])))
    for p in pts:
        p["xc"] = p["x"] * CORES
    return pts


def fig1() -> dict:
    pts = points()
    scan = load("qca_scan.json")
    fig = plt.figure(figsize=(3.5, 3.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[3.0, 1.15], hspace=0.1)
    ax, ax2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    xmin, xmax = 1e-1, 1e15
    for ax_ in (ax, ax2):
        ax_.set_xscale("log")
        ax_.set_xlim(xmin, xmax)
        for x, lab in TIERS:
            ax_.axvline(x, color=INK2, lw=0.5, ls=(0, (2, 2)), zorder=0)
        for s_ in ("top", "right"):
            ax_.spines[s_].set_visible(False)
    ax.set_yscale("symlog", linthresh=1, linscale=0.6)
    ax.set_ylim(-40, 120)
    ticks = [-30, -10, -3, 0, 3, 10, 30, 100]
    ax.set_yticks(ticks)
    ax.set_yticklabels([str(t) for t in ticks])
    ax.minorticks_off()
    ax.axhline(3, color=INK2, lw=0.6)
    ax.axhline(0, color=INK2, lw=0.3)
    ax.text(1e11, 3.3, r"alive: 3$\sigma$ above bound", ha="center", va="bottom", fontsize=5.5, color=INK2)
    ax.fill_between([TIERS[2][0], xmax], 3, 120, color="#e9e8e4", zorder=0, lw=0)
    ax.text(math.sqrt(TIERS[2][0] * xmax), 18, "L2 region:\nalive and\nout of\nclassical\nreach\n\nempty",
            ha="center", va="center", fontsize=5.3, color=INK2)
    for x, lab in TIERS:
        ax.text(x, 1.02, lab, transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=5.3, color=INK2)
    label_y = {"motile ghz2": 70, "CHSH roll": 34, "tree serial": 17, "teleport bond": 9.5, "germ/soma W=50": 5.6,
               "QAL W=24": 1.6, "QCA t=2": 0.75, "tree brick": -0.6, "GHZ spine": -23}
    for p_ in pts:
        ax.scatter(p_["xc"], p_["k"], marker=MARK[p_["rung"]], s=24, color=p_["c"], edgecolor="#fcfcfb", lw=0.9,
                   zorder=3)
        ax.annotate(f"{p_['lab']} ({p_['q']} q)", xy=(p_["xc"], p_["k"]), xytext=(2.5e4, label_y.get(p_["lab"], p_["k"])),
                    fontsize=5.3, color=INK, va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", color="#b5b4ae", lw=0.4, shrinkA=0, shrinkB=2))
    ax.set_ylabel(r"hardware margin above bound ($\sigma$)")
    ax.tick_params(labelbottom=False)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=MARK[r], ls="", color=INK2, markersize=3.5, label=r) for r in MARK] + \
        [Line2D([], [], marker="o", ls="", color=c, markersize=3.5, label=l)
         for c, l in ((C_TREE, "quantum tree"), (C_QAL, "artificial life"), (C_CT, "CT pipeline"))]
    ax.legend(handles=h, loc="lower right", bbox_to_anchor=(1.0, 0.0), fontsize=5.2, ncol=2, frameon=False,
              handletextpad=0.2, columnspacing=0.6, title="witness rung / project", title_fontsize=5.2)
    rowy = {23: 3, 40: 2, 60: 1, 100: 0}
    ax2.set_ylim(-0.6, 4.4)
    ax2.set_yticks(list(rowy.values()))
    alloc = {}
    if scan:
        for r in scan["rows"]:
            if "sites" in r:
                alloc[r["sites_requested"]] = r["sites"]
    ax2.set_yticklabels([f"{k} sites" if alloc.get(k, k) == k else f"{alloc[k]} sites ({k} req.)" for k in rowy],
                        fontsize=5.3)
    ax2.set_xlabel("exact classical cost on one machine (core-seconds, log scale)")
    ax2.text(xmin * 1.3, 4.35, "QCA family, simulation only (no hardware witness)", fontsize=5.3, color=INK2,
             ha="left", va="top")
    out = {"points": pts, "scan": []}
    if scan:
        for r in scan["rows"]:
            s_, tt = r["sites_requested"], r["t"]
            y = rowy.get(s_, 0)
            if "chi_max" in r:
                x = (r["t_state_s"] + r["t_sample_s"]) * CORES
                ax2.scatter(x, y, marker="o", s=10, facecolor="none", edgecolor=INK2, lw=0.7)
                ax2.annotate(f"t{tt}", (x, y), xytext=(0, -6.5), textcoords="offset points", fontsize=4.6,
                             color=INK2, ha="center")
                out["scan"].append({"sites": s_, "t": tt, "core_s": x, "chi": r["chi_max"]})
            elif "timeout_s" in r:
                x = r["timeout_s"] * CORES
                ax2.annotate("", xy=(x * 40, y), xytext=(x, y), arrowprops=dict(arrowstyle="->", color=INK2, lw=0.7))
                ax2.annotate(f"t{tt}: >{r['timeout_s']} s", (x * 45, y), xytext=(2, 0), textcoords="offset points",
                             fontsize=4.6, color=INK2, va="center")
                out["scan"].append({"sites": s_, "t": tt, "timeout_s": r["timeout_s"]})
    fig.savefig(P / "fig1_map.pdf", bbox_inches="tight")
    fig.savefig(R / "fig1_map.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def ecdf(ax, x, color, label, ls="-"):
    x = np.sort(np.asarray(x, float))
    ax.step(x, np.arange(1, len(x) + 1) / len(x), where="post", color=color, lw=1.2, ls=ls, label=label)


def fig2() -> dict:
    z = np.load(R / "ct_twin_seed_features.npz")
    feat = load("ct_twin_features.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 1.9), gridspec_kw={"wspace": 0.42, "width_ratios": [1, 1.25]})
    for ax_ in (a1, a2):
        for s in ("top", "right"):
            ax_.spines[s].set_visible(False)
    ecdf(a1, z["hardware_seed_vox"], C_CT, "hardware")
    ecdf(a1, z["ideal_seed_vox"], C_TREE, "ideal twin")
    ecdf(a1, z["noisy_seed_vox"], C_QAL, "noisy twin", ls=(0, (3, 1.5)))
    ecdf(a1, z["indep_seed_vox"], C_SIM, "independent", ls=(0, (1, 1.2)))
    a1.set_xlabel("seed size (voxels)")
    a1.set_ylabel("cumulative fraction")
    a1.set_title("(a) seed shapes, all tiles", fontsize=6.5, color=INK)
    a1.legend(fontsize=5, frameon=False, loc="lower right", handlelength=1.6)
    out = {}
    if feat:
        rows = feat["features"]["rows"]
        keys = [("seed_cells", "seed size"), ("vdt_d", "doubling time"), ("day_baseline", "days to baseline"),
                ("roi_mean", "ROI mean"), ("roi_sd", "ROI s.d."), ("glcm_contrast", "GLCM contrast")]
        u = feat["features"]["unpaired"]
        for i, (k, lab) in enumerate(keys):
            q = np.array([r[k] for r in rows if r["arm"] == "quantum" and r[k] is not None], float)
            t = np.array([r[k] for r in rows if r["arm"] == "twin" and r[k] is not None], float)
            mu, sd = np.concatenate([q, t]).mean(), np.concatenate([q, t]).std() or 1.0
            jit = np.linspace(-0.12, 0.12, max(len(q), 1))
            a2.scatter((q - mu) / sd, i + 0.15 + jit[: len(q)] * 0.5, s=5, color=C_CT, lw=0)
            a2.scatter((t - mu) / sd, i - 0.15 + jit[: len(t)] * 0.5, s=5, color=C_TREE, lw=0)
            a2.text(3.4, i, f"KS p={u[k]['ks_p']:.2f}", fontsize=5, va="center", color=INK2)
            out[k] = u[k]["ks_p"]
        a2.set_yticks(range(len(keys)))
        a2.set_yticklabels([l for _, l in keys], fontsize=5.5)
        a2.set_xlim(-3.2, 4.4)
        a2.set_xlabel("standardised value")
        a2.set_title("(b) rendered CT nodules", fontsize=6.5, color=INK)
        a2.scatter([], [], s=6, color=C_CT, label="quantum seeds")
        a2.scatter([], [], s=6, color=C_TREE, label="twin seeds")
        a2.legend(fontsize=5, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.28), ncol=2,
                  handletextpad=0.1)
    fig.savefig(P / "fig2_twin.pdf", bbox_inches="tight")
    fig.savefig(R / "fig2_twin.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["1", "2"]
    res = {}
    if "1" in which:
        res["fig1"] = fig1()
    if "2" in which:
        res["fig2"] = fig2()
    (R / "figures.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, default=float)[:1500])
