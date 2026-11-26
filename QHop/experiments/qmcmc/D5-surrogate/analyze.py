"""D5 analysis: S tables, regime table, plots. Run: python analyze.py  (reads results/raw_*.jsonl, accept_curve_*.csv)"""
import sys
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import glob
import json
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm

recs = [json.loads(l) for f in sorted(glob.glob("results/raw_n*_i*.jsonl")) for l in open(f)]
REG = ["HIGH", "MEDIUM", "LOW"]
COSTS = [1e-6, 1e-3]


def rate(g):
    return -np.log(1.0 - min(g, 1 - 1e-12))


rows = []
for r in recs:
    G = r["G"]
    gq = G["q_sur"]["gap"]
    noisur = {k: G[k]["gap"] for k in ("local", "uniform", "mix_lu")}
    da = {}
    for fam_k in ("DA_local", "DA_mix"):
        for K, v in G[fam_k].items():
            da[(fam_k, int(K))] = v["gap"]
    free_all = dict(noisur)
    free_all.update({f"{k[0]}_K{k[1]}": v for k, v in da.items()})
    free_all["DA_inf"] = G["DA_inf"]["gap"]
    best_free_name = max(free_all, key=free_all.get)
    best_free = free_all[best_free_name]
    fin = dict(noisur)
    fin.update({f"{k[0]}_K{k[1]}": v for k, v in da.items() if k[1] <= 1000})
    best_fin = max(fin.values())
    # K* = smallest inner K (local or mix inner) at which classical DA matches the quantum-surrogate gap
    Kstar = None
    for K in sorted({k[1] for k in da}):
        if max(da.get(("DA_local", K), 0), da.get(("DA_mix", K), 0)) >= gq:
            Kstar = K
            break
    if Kstar is None and G["DA_inf"]["gap"] >= gq:
        Kstar = "inf"
    row = dict(n=r["n"], inst=r["inst"], fam=r["fam"], rho=r["rho"], rho_actual=r["rho_actual"], regime=r["regime"],
               beta=r["beta"], beta_c=r["beta_c"], beta_loc=r["beta_loc"], beta_sigma=r["beta_sigma"],
               two_phi=r["two_phi"], gap_q_sur=gq,
               gap_q_true=G["q_true"]["gap"] if "q_true" in G else np.nan,
               gap_q_sur_decoh=G["q_sur_decoh"]["gap"] if "q_sur_decoh" in G else np.nan,
               gap_local=noisur["local"], gap_uniform=noisur["uniform"], gap_mix=noisur["mix_lu"],
               gap_DA_inf=G["DA_inf"]["gap"], gap_DA_best_finiteK1000=best_fin, gap_best_classical=best_free,
               best_classical=best_free_name,
               gap_nested_best=max(v["gap"] for v in G["nested_q"].values()),
               gap_sur_local=G["sur_local_gap"], gap_sur_mix=G["sur_mix_gap"], gap_sur_qsur=G["sur_qsur_gap"],
               acc_q_sur=G["q_sur"]["acc"], acc_q_sur_residual=G["q_sur"]["acc_residual_only"],
               acc_DA_inf=G["DA_inf"]["acc"], Kstar=Kstar)
    row["S_free"] = gq / best_free
    row["S_K1000"] = gq / best_fin
    row["S_vs_no_surrogate"] = gq / max(noisur.values())
    row["S_oracle"] = row["gap_q_true"] / best_free
    row["S_decoh"] = row["gap_q_sur_decoh"] / best_free
    row["S_nested"] = row["gap_nested_best"] / best_free
    for c in COSTS:
        cand = [rate(v) for v in noisur.values()] + [rate(v) / (1 + k[1] * c) for k, v in da.items()]
        row[f"S_cost{c:g}"] = rate(gq) / max(cand)
    rows.append(row)

TEMP = {}
for f in glob.glob("results/tempered_n*.csv"):
    for d in csv.DictReader(open(f)):
        TEMP[(int(d["n"]), int(d["inst"]), d["fam"], float(d["rho"]), d["regime"])] = \
            max(float(d["gap_TDA_best"]), float(d["gap_mix_TDA_local"]))
for row in rows:
    t = TEMP.get((row["n"], row["inst"], row["fam"], row["rho"], row["regime"]))
    row["gap_tempered_DA_best"] = t if t is not None else np.nan
    row["S_ext"] = row["gap_q_sur"] / max(row["gap_best_classical"], t) if t is not None else np.nan

keys = list(rows[0].keys())
with open("results/per_instance.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)


def q(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) == 0:
        return (np.nan, np.nan, np.nan, 0)
    return (np.median(x), np.percentile(x, 25), np.percentile(x, 75), len(x))


cols = ["S_free", "S_ext", "S_K1000", "S_cost0.001", "S_vs_no_surrogate", "S_oracle", "S_decoh", "S_nested"]
summ = []
lines = ["D5 S TABLE: median [IQR] over instances; S = gap(quantum, surrogate in U, true accept) / gap(best classical)",
         "S_free = vs best of {local, uniform, mix, DA local/mix inner K=1..1e6, DA K=inf exact surrogate draw}, surrogate steps free",
         "S_ext = S_free also vs tempered-surrogate independence DA (beta_sur = f beta) and its 50/50 mix with local (MEDIUM/LOW only)",
         "S_K1000 = same as S_free but classical inner K <= 1000; S_cost0.001 = relaxation-rate ratio with surrogate step = 1e-3 true call",
         "S_vs_no_surrogate = vs best of local/uniform/mix on E_true; S_oracle = quantum with E_true in U (not implementable for b,c)",
         "S_decoh = decohered control (E_sur in U); S_nested = best nested quantum-inner DA (K<=100 quantum calls per true call)",
         ""]
hdr = "n | fam | regime | rho | beta*sigma | 2Phi | " + " | ".join(cols) + " | Kstar(median) | n_inst"
lines.append(hdr)
for n in sorted({r["n"] for r in rows}):
    for fam in ("a", "b", "c"):
        for reg in REG:
            for rho in sorted({r["rho"] for r in rows if r["fam"] == fam and r["n"] == n}):
                sub = [r for r in rows if r["n"] == n and r["fam"] == fam and r["regime"] == reg and r["rho"] == rho]
                if not sub:
                    continue
                d = dict(n=n, fam=fam, regime=reg, rho=rho, beta_sigma=float(np.median([s["beta_sigma"] for s in sub])),
                         two_phi=float(np.median([s["two_phi"] for s in sub])), n_inst=len(sub))
                txt = []
                for c in cols:
                    m, lo, hi, k = q([s[c] for s in sub])
                    d[c] = m
                    d[c + "_q25"] = lo
                    d[c + "_q75"] = hi
                    txt.append("nan" if not np.isfinite(m) else f"{m:.2f} [{lo:.2f},{hi:.2f}]")
                ks = [s["Kstar"] for s in sub]
                kn = [np.inf if k in (None, "inf") else k for k in ks]
                kmed = np.median(kn)
                d["Kstar_median"] = "never" if all(k is None for k in ks) else (str(kmed) if np.isfinite(kmed) else "inf/never")
                d["Kstar_list"] = str(ks)
                summ.append(d)
                lines.append(f"{n} | {fam} | {reg} | {rho:.2f} | {d['beta_sigma']:.2f} | {d['two_phi']:.3f} | "
                             + " | ".join(txt) + f" | {d['Kstar_median']} | {len(sub)}")
open("results/S_table.txt", "w").write("\n".join(lines) + "\n")
with open("results/S_table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0].keys()))
    w.writeheader()
    w.writerows(summ)

# regime table
rl = ["REGIME TABLE: beta_c = specific-heat peak of E_true; beta_loc = beta where local gap < 0.1 x its beta->0 value;",
      "HIGH = beta_c/3, MEDIUM = beta_c, LOW = 3 beta_c. median [min,max] over instances",
      "n | fam | rho | beta_c | beta_loc"]
for n in sorted({r["n"] for r in rows}):
    for fam in ("a", "b", "c"):
        for rho in sorted({r["rho"] for r in rows if r["fam"] == fam and r["n"] == n}):
            sub = [r for r in rows if r["n"] == n and r["fam"] == fam and r["rho"] == rho and r["regime"] == "MEDIUM"]
            if not sub:
                continue
            bc = [s["beta_c"] for s in sub]
            bl = [s["beta_loc"] for s in sub if s["beta_loc"] is not None]
            bls = f"{np.median(bl):.3f} [{min(bl):.3f},{max(bl):.3f}]" if bl else "not computed"
            rl.append(f"{n} | {fam} | {rho:.2f} | {np.median(bc):.3f} [{min(bc):.3f},{max(bc):.3f}] | {bls}")
open("results/regime_table.txt", "w").write("\n".join(rl) + "\n")

# ---------------- plots: S vs rho per regime
fams = {"a": "SK + 3/4-body", "b": "SK + iid Gaussian residual", "c": "monotone f(E_SK) + small 3/4-body"}
ns = sorted({r["n"] for r in rows})
for metric, fname in (("S_free", "S_vs_sigma_free.png"), ("S_K1000", "S_vs_sigma_K1000.png"),
                      ("S_oracle", "S_vs_sigma_oracle.png")):
    fig, axs = plt.subplots(3, 3, figsize=(13, 10), sharey=True)
    for i, fam in enumerate("abc"):
        for j, reg in enumerate(REG):
            ax = axs[i, j]
            for n in ns:
                sub = [d for d in summ if d["n"] == n and d["fam"] == fam and d["regime"] == reg and np.isfinite(d[metric])]
                if not sub:
                    continue
                x = [d["rho"] for d in sub]
                ax.errorbar(x, [d[metric] for d in sub],
                            yerr=[[d[metric] - d[metric + "_q25"] for d in sub], [d[metric + "_q75"] - d[metric] for d in sub]],
                            marker="o", capsize=3, label=f"n={n}")
            ax.axhline(1, color="k", lw=0.8, ls="--")
            ax.set_yscale("log")
            ax.set_title(f"({fam}) {fams[fam]} - {reg}", fontsize=9)
            if i == 2:
                ax.set_xlabel("surrogate residual rho = sigma / std(E_true)")
            if j == 0:
                ax.set_ylabel(metric + " (gap ratio)")
            ax.legend(fontsize=7)
    fig.suptitle(f"{metric}: quantum proposal with surrogate in U vs best classical with same surrogate (median, IQR)")
    fig.tight_layout()
    fig.savefig("plots/" + fname, dpi=120)
    plt.close(fig)

# scatter S_free vs beta*sigma
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
mk = {"HIGH": "^", "MEDIUM": "s", "LOW": "o"}
colf = {"a": "C0", "b": "C1", "c": "C2"}
for r in rows:
    ax[0].scatter(r["beta_sigma"], r["S_free"], marker=mk[r["regime"]], color=colf[r["fam"]], s=12, alpha=0.6)
    ax[1].scatter(r["gap_sur_mix"], r["S_K1000"], marker=mk[r["regime"]], color=colf[r["fam"]], s=12, alpha=0.6)
for a in ax:
    a.set_yscale("log")
    a.axhline(1, color="k", ls="--", lw=0.8)
ax[0].set_xscale("symlog", linthresh=0.1)
ax[0].set_xlabel("beta * sigma (absolute residual std)")
ax[0].set_ylabel("S_free")
ax[1].set_xscale("log")
ax[1].set_xlabel("gap of best classical chain on the SURROGATE alone (mix local+uniform)")
ax[1].set_ylabel("S_K1000")
from matplotlib.lines import Line2D
h = [Line2D([], [], marker=mk[k], ls="", color="gray", label=k) for k in mk] + \
    [Line2D([], [], marker="o", ls="", color=colf[k], label="fam " + k) for k in colf]
ax[0].legend(handles=h, fontsize=7)
fig.suptitle("When does the surrogate-in-U quantum proposal win? (all n, instances, rho)")
fig.tight_layout()
fig.savefig("plots/S_condition_scatter.png", dpi=120)
plt.close(fig)

# acceptance plot
acc_files = sorted(glob.glob("results/accept_curve_n*.csv"))
if acc_files:
    A = [dict((k, (float(v) if k not in ("fam",) else v)) for k, v in row.items()) for f in acc_files for row in csv.DictReader(open(f))]
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    xs = np.logspace(-2, 1.2, 200)
    for i, fam in enumerate("abc"):
        ax = axs[i]
        sub = [a for a in A if a["fam"] == fam]
        x = np.array([a["beta_sigma"] for a in sub])
        ax.scatter(x, [a["DAinf_acc_incl_self"] for a in sub], s=6, label="classical DA, K=inf (exact surrogate draw)", color="C0")
        ax.scatter(x, [a["qsur_acc"] for a in sub], s=6, label="quantum, E_sur in U: total acceptance", color="C3")
        ax.scatter(x, [a["qsur_acc_residual_only"] for a in sub], s=6, label="quantum: residual-only factor", color="C1", marker="x")
        ax.scatter(x, [a["local_acc_residual_only"] for a in sub], s=6, label="local: residual-only factor", color="C2", marker="+")
        ax.plot(xs, 2 * norm.cdf(-xs / np.sqrt(2)), "k-", lw=2, label="2 Phi(-beta sigma / sqrt 2)")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(1e-4, 1.2)
        ax.set_xlabel("beta * sigma")
        ax.set_title(f"({fam}) {fams[fam]}, n={int(sub[0]['n'])}", fontsize=9)
        if i == 0:
            ax.set_ylabel("equilibrium acceptance")
            ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig("plots/acceptance_vs_beta_sigma.png", dpi=120)
    plt.close(fig)
print("\n".join(lines))
print("\n".join(rl))
