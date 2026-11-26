"""Aggregate D6 results -> results/*.csv summary tables + plots. Usage: python analyze.py"""
import glob
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES, PLOT = os.path.join(HERE, "results"), os.path.join(HERE, "plots")


def load(pat):
    rows = []
    for f in sorted(glob.glob(os.path.join(RES, pat))):
        rows += json.load(open(f))
    return rows


def to_csv(rows, path):
    keys = sorted({k for r in rows for k in r})
    with open(path, "w") as fh:
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r.get(k, "")) for k in keys) + "\n")


def med_iqr(x):
    x = np.asarray(x, float)
    return np.median(x), np.percentile(x, 25), np.percentile(x, 75)


def table(rows, keys, val="S", out=None, extra=("S_C1", "S_weak", "S_dec", "Q_over_D")):
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)
    lines = []
    hdr = " | ".join(keys) + f" | N | {val} med [IQR] | " + " | ".join(f"{e} med" for e in extra) + " | frac S>2 | best classical (mode)"
    lines.append(hdr)
    for k in sorted(groups):
        g = groups[k]
        m, lo, hi = med_iqr([r[val] for r in g])
        ex = " | ".join(f"{np.median([r[e] for r in g]):.2f}" for e in extra if e in g[0])
        names = [r.get("best_name", "") for r in g]
        mode = max(set(names), key=names.count)
        lines.append(" | ".join(str(x) for x in k) + f" | {len(g)} | {m:.2f} [{lo:.2f},{hi:.2f}] | {ex} | "
                     f"{np.mean([r[val] > 2 for r in g]):.2f} | {mode}")
    txt = "\n".join(lines)
    if out:
        open(out, "w").write(txt + "\n")
    return txt


def main():
    out = []
    # ---------------- exp1
    r1 = load("exp1_*.json")
    if r1:
        to_csv(r1, os.path.join(RES, "exp1_all.csv"))
        out.append("EXP1 planted BPSK, S by family,n,beta (pooled over alpha, SNR)")
        out.append(table(r1, ["family", "n", "beta"]))
        out.append("\nEXP1 at matched beta=1 by family,n,alpha")
        out.append(table([r for r in r1 if r["beta"] == 1], ["family", "n", "alpha"]))
        out.append("\nEXP1 at matched beta=1 by family,n,alpha,snr")
        out.append(table([r for r in r1 if r["beta"] == 1], ["family", "n", "alpha", "snr_db"]))
        out.append("\nEXP1 colder beta=8 by family,n,alpha")
        out.append(table([r for r in r1 if r["beta"] == 8], ["family", "n", "alpha"]))
        out.append("\nEXP1 Nishimori check (median over instances): m_planted, q_replica, var_q12 by beta, family, n")
        g = {}
        for r in r1:
            g.setdefault((r["family"], r["n"], r["beta"]), []).append(r)
        for k in sorted(g):
            out.append(f"{k} m={np.mean([r['m_planted'] for r in g[k]]):.3f} q={np.mean([r['q_replica'] for r in g[k]]):.3f}"
                       f" var_q12={np.median([r['var_q12'] for r in g[k]]):.3f}"
                       f" beta_peak med={np.median([r['beta_peak'] for r in g[k]]):.2f}")
        # plot: S vs SNR per alpha at beta 1 and 8, dense, largest n
        for fam in sorted({r["family"] for r in r1}):
            ns = sorted({r["n"] for r in r1 if r["family"] == fam})
            fig, axs = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
            for ax, b in zip(axs, (1, 2, 4, 8)):
                for n in ns:
                    for al in sorted({r["alpha"] for r in r1}):
                        sel = [r for r in r1 if r["family"] == fam and r["n"] == n and r["alpha"] == al and r["beta"] == b]
                        if not sel:
                            continue
                        snrs = sorted({r["snr_db"] for r in sel})
                        med = [np.median([r["S"] for r in sel if r["snr_db"] == s]) for s in snrs]
                        ax.plot(snrs, med, "o-" if n == ns[-1] else "x--", label=f"n={n} a={al}", alpha=0.8)
                ax.axhline(1, color="k", lw=0.6)
                ax.axhline(2, color="r", lw=0.6, ls=":")
                ax.set_yscale("log")
                ax.set_xlabel("SNR (dB)")
                ax.set_title(f"{fam}, beta/beta_match={b}")
            axs[0].set_ylabel("S = gap_Q / gap_best_classical")
            axs[-1].legend(fontsize=6, ncol=2)
            fig.tight_layout()
            fig.savefig(os.path.join(PLOT, f"exp1_S_vs_snr_{fam}.png"), dpi=120)
            plt.close(fig)
    # ---------------- exp2
    r2 = load("exp2_*.json")
    if r2:
        to_csv(r2, os.path.join(RES, "exp2_all.csv"))
        out.append("\nEXP2 tomography, S by n,views,beta")
        out.append(table(r2, ["n", "views", "beta"]))
        out.append("\nEXP2 at matched beta=1 by n,views,sigma")
        out.append(table([r for r in r2 if r["beta"] == 1], ["n", "views", "sigma"]))
        fig, axs = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
        for ax, V in zip(axs, (2, 3, 4)):
            for n in sorted({r["n"] for r in r2}):
                for b in (1, 2, 4, 8):
                    sel = [r for r in r2 if r["views"] == V and r["beta"] == b and r["n"] == n]
                    if not sel:
                        continue
                    sg = sorted({r["sigma"] for r in sel})
                    ax.plot(sg, [np.median([r["S"] for r in sel if r["sigma"] == s]) for s in sg], "o-",
                            label=f"n={n} b={b}")
            ax.axhline(1, color="k", lw=0.6)
            ax.axhline(2, color="r", lw=0.6, ls=":")
            ax.set_yscale("log")
            ax.set_xscale("log")
            ax.set_xlabel("noise sigma")
            ax.set_title(f"tomography, {V} views")
        axs[0].set_ylabel("S vs best classical (incl. ghost swaps)")
        axs[-1].legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(os.path.join(PLOT, "exp2_S_vs_sigma.png"), dpi=120)
        plt.close(fig)
    # ---------------- exp3
    r3 = load("exp3_*.json")
    if r3:
        to_csv(r3, os.path.join(RES, "exp3_all.csv"))
        out.append("\nEXP3 genomics, S by beta")
        out.append(table(r3, ["beta"]))
        out.append("\nEXP3 by r_target,g at beta=1")
        out.append(table([r for r in r3 if r["beta"] == 1], ["r_target", "g"]))
        out.append("\nEXP3 by r_target at beta=8")
        out.append(table([r for r in r3 if r["beta"] == 8], ["r_target"]))
        out.append("\nEXP3 gap ratio Q / swap baselines (LS = local+uniform swap, LW = local+LD-weighted swap), median by beta:")
        for b in sorted({r["beta"] for r in r3}):
            sel = [r for r in r3 if r["beta"] == b]
            out.append(f"beta={b} Q/LS={np.median([r['g_Q']/r['g_LS'] for r in sel]):.2f} "
                       f"Q/LW={np.median([r['g_Q']/r['g_LW'] for r in sel]):.2f} "
                       f"r_emp={np.mean([r['r_emp'] for r in sel]):.3f} post_true={np.median([r['post_true'] for r in sel]):.2f}")
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        for b in (1, 2, 4, 8):
            rs = sorted({r["r_target"] for r in r3})
            ax.plot(rs, [np.median([r["S"] for r in r3 if r["beta"] == b and r["r_target"] == x]) for x in rs], "o-",
                    label=f"beta={b}")
        ax.axhline(1, color="k", lw=0.6)
        ax.axhline(2, color="r", lw=0.6, ls=":")
        ax.set_yscale("log")
        ax.set_xlabel("within-block LD r (target)")
        ax.set_ylabel("S vs best classical (incl. swap)")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(PLOT, "exp3_S_vs_ld.png"), dpi=120)
        plt.close(fig)
    # ---------------- exp4
    r4 = load("exp4_*.json")
    if r4:
        to_csv(r4, os.path.join(RES, "exp4_all.csv"))
        out.append("\nEXP4 MRF negative control, by beta/beta_peak")
        out.append(table(r4, ["beta_over_peak"], extra=("S_vs_SW", "S_weak", "S_dec", "Q_over_D")))
        out.append(f"max SW asymmetry {max(r['sw_asym'] for r in r4):.2e}")
    txt = "\n".join(out)
    open(os.path.join(RES, "summary_tables.txt"), "w").write(txt + "\n")
    print(txt[:200])


if __name__ == "__main__":
    main()
