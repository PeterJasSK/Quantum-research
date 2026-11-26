"""Aggregate D8 results -> results/gaps_all.csv, results/S_table.csv, results/pt_table.csv, plots/*.png, short stdout summary.
Usage: python analyze.py [n=12]
"""
import glob
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
CL = ["nn_kawasaki", "anypair_swap", "mix_nn_anypair", "uniform"]
QU = ["q_grid", "q_ring", "q_complete"]
DE = ["deco_grid", "deco_complete"]
ALL = CL + QU + DE
rows = []
for f in sorted(glob.glob(f"results/gaps_*_n{n}.jsonl")):
    rows += [json.loads(l) for l in open(f)]
fams = [f for f in ("cuau", "coulomb", "sk") if any(r["fam"] == f for r in rows)]

with open(f"results/gaps_all_n{n}.csv", "w") as fo:
    fo.write("fam,seed,Tc,T_over_Tc,proposal,gap,iat_E,iat_sro,iat_q\n")
    for r in rows:
        for p in ALL:
            d = r[p]
            fo.write(f"{r['fam']},{r['seed']},{r['Tc']:.6g},{r['T_over_Tc']},{p},{d['gap']:.6g},{d['iat_E']:.6g},"
                     f"{d['iat_sro']:.6g},{d['iat_q']:.6g}\n")


def q3(x):
    x = np.asarray(x)
    return np.median(x), np.percentile(x, 25), np.percentile(x, 75)


summary = []
SW = ["nn_kawasaki", "anypair_swap", "mix_nn_anypair"]
BASES = {"swap": SW, "all": CL}  # 'swap' = best swap mixture (kill-rule baseline); 'all' adds uniform over the 924 states
with open(f"results/S_table_n{n}.csv", "w") as fo:
    fo.write("fam,T_over_Tc,n_inst,baseline,best_classical_typical,gap_best_classical_med,ratio,median,q25,q75\n")
    for fam in fams:
        R = [r for r in rows if r["fam"] == fam]
        Tcs = sorted({r["seed"]: r["Tc"] for r in R}.items())
        summary.append(f"{fam}: Tc per seed " + ", ".join(f"{t:.3g}" for _, t in Tcs))
        for tr in sorted({r["T_over_Tc"] for r in R}):
            Rt = [r for r in R if r["T_over_Tc"] == tr]
            for bname, B in BASES.items():
                best = np.array([max(r[p]["gap"] for p in B) for r in Rt])
                arg = [max(B, key=lambda p: r[p]["gap"]) for r in Rt]
                typ = max(set(arg), key=arg.count)
                line = []
                for p in QU + DE + ["q_best"]:
                    g = np.array([max(r[q]["gap"] for q in QU) if p == "q_best" else r[p]["gap"] for r in Rt])
                    m, a, b = q3(g / best)
                    fo.write(f"{fam},{tr},{len(Rt)},{bname},{typ},{np.median(best):.4g},S_{p},{m:.3g},{a:.3g},{b:.3g}\n")
                    line.append(f"{p}={m:.2f}[{a:.2f},{b:.2f}]")
                if tr in (0.5, 1.1, 3.0):
                    summary.append(f"  T/Tc={tr} vs {bname}: best={typ} gap={np.median(best):.3g} | " + " ".join(line))

# PT
pt = []
for f in sorted(glob.glob("results/pt_*.jsonl")):
    pt += [json.loads(l) for l in open(f)]
if pt:
    with open("results/pt_table.csv", "w") as fo:
        fo.write("fam,seed,T_over_Tc,obs,pt_iat_rounds,pt_iat_per_proposal,anypair_exact_iat,qbest_exact_iat,"
                 "S_vs_PT_per_proposal,S_vs_PT_per_round\n")
        for fam in fams:
            for tr in (1.1, 0.5):
                SP, SR = [], []
                for p in [p for p in pt if p["fam"] == fam and p["T_over_Tc"] == tr]:
                    g = [r for r in rows if r["fam"] == fam and r["seed"] == p["seed"] and r["T_over_Tc"] == tr][0]
                    sp_o, sr_o = [], []
                    for o in ("E", "sro", "q"):
                        qi = min(g[q]["iat_" + o] for q in QU)
                        a = g["anypair_swap"]["iat_" + o]
                        sp, sr = p["pt_iat_per_proposal"][o] / qi, p["pt_iat_rounds"][o] / qi
                        fo.write(f"{fam},{p['seed']},{tr},{o},{p['pt_iat_rounds'][o]:.4g},{p['pt_iat_per_proposal'][o]:.4g},"
                                 f"{a:.4g},{qi:.4g},{sp:.3g},{sr:.3g}\n")
                        sp_o.append(sp)
                        sr_o.append(sr)
                    SP.append(min(sp_o))  # worst observable for the quantum chain
                    SR.append(min(sr_o))
                if SP:
                    m, a, b = q3(SP)
                    m2, a2, b2 = q3(SR)
                    summary.append(f"PT {fam} T/Tc={tr}: S_vs_PT per-proposal {m:.2f}[{a:.2f},{b:.2f}]  per-round "
                                   f"{m2:.2f}[{a2:.2f},{b2:.2f}] (min over E,SRO,q)")
        for p in pt:
            for kk in [k for k in p if k.startswith("sim_")]:
                g = [r for r in rows if r["fam"] == p["fam"] and r["seed"] == p["seed"] and r["T_over_Tc"] == p["T_over_Tc"]][0]
                nm = kk[4:-4]
                summary.append(f"  xcheck {p['fam']} T/Tc={p['T_over_Tc']} {nm}: sim IAT E {p[kk]['E']:.3g} vs exact "
                               f"{g[nm]['iat_E']:.3g}; q {p[kk]['q']:.3g} vs {g[nm]['iat_q']:.3g}")

# plots
sty = {"nn_kawasaki": ("C0", "-"), "anypair_swap": ("C1", "-"), "mix_nn_anypair": ("C2", "-"), "uniform": ("C7", "-"),
       "q_grid": ("C3", "--"), "q_ring": ("C4", "--"), "q_complete": ("C5", "--"), "deco_grid": ("C3", ":"),
       "deco_complete": ("C5", ":")}
fig, axs = plt.subplots(1, len(fams), figsize=(5 * len(fams), 4), squeeze=False)
for ax, fam in zip(axs[0], fams):
    R = [r for r in rows if r["fam"] == fam]
    trs = sorted({r["T_over_Tc"] for r in R})
    for p in ALL:
        med = [np.median([r[p]["gap"] for r in R if r["T_over_Tc"] == t]) for t in trs]
        ax.plot(trs, med, color=sty[p][0], ls=sty[p][1], marker="o", ms=3, label=p)
    ax.axvline(1.0, color="k", lw=0.5)
    ax.axvline(1.1, color="k", lw=0.5, ls="--")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("T / Tc (Cv peak)"); ax.set_ylabel("spectral gap (median over seeds)")
    ax.set_title(f"{fam}, n={n}, k={n//2}")
axs[0][0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"plots/gap_vs_T_n{n}.png", dpi=130)

fig, axs = plt.subplots(1, len(fams), figsize=(5 * len(fams), 4), squeeze=False)
for ax, fam in zip(axs[0], fams):
    R = [r for r in rows if r["fam"] == fam]
    trs = sorted({r["T_over_Tc"] for r in R})
    for p in QU + DE:
        S = [[r[p]["gap"] / max(r[c]["gap"] for c in SW) for r in R if r["T_over_Tc"] == t] for t in trs]
        ax.plot(trs, [np.median(s) for s in S], color=sty[p][0], ls=sty[p][1], marker="o", ms=3, label=p)
        ax.fill_between(trs, [np.percentile(s, 25) for s in S], [np.percentile(s, 75) for s in S], color=sty[p][0], alpha=0.1)
    ax.axhline(2, color="r", lw=0.7); ax.axhline(1, color="k", lw=0.5); ax.axvline(1.1, color="k", lw=0.5, ls="--")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("T / Tc"); ax.set_ylabel("S = gap(quantum) / gap(best swap mixture)")
    ax.set_title(f"{fam}, n={n} (median, IQR)")
axs[0][0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"plots/S_vs_T_n{n}.png", dpi=130)

open(f"results/summary_n{n}.txt", "w").write("\n".join(summary) + "\n")
print("\n".join(summary))
