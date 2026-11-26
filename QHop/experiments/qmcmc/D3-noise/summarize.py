"""D3 summary tables + plots from results/all_rows.csv.  python summarize.py"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

d = pd.read_csv("results/all_rows.csv")
REG = ["LOW", "MEDIUM", "HIGH"]
out = {}


def q(x):
    return f"{np.median(x):.3g} [{np.percentile(x, 25):.3g},{np.percentile(x, 75):.3g}]"


def cross(eps, y, level):
    """first eps where y crosses below level (log-linear interpolation); None if never; 0 if already below."""
    eps, y = np.asarray(eps, float), np.asarray(y, float)
    if y[0] <= level:
        return 0.0
    for k in range(1, len(y)):
        if y[k] <= level:
            l0, l1 = np.log(eps[k - 1]), np.log(eps[k])
            f = (y[k - 1] - level) / (y[k - 1] - y[k])
            return float(np.exp(l0 + f * (l1 - l0)))
    return None


lines = []
P = lambda s="": lines.append(s)  # noqa: E731

# ---------------- regimes
inst = json.load(open("results/instances.json"))
P("REGIMES per instance (beta_c = specific-heat peak; beta_loc = local gap fell to half its max; LOW=3bc MEDIUM=bc HIGH=bc/3)")
for r in inst:
    P(f"  {r['source']} {r['family']} n={r['n']} seed={r['seed']}: beta_c={r['beta_c_Cpeak']:.3f} beta_loc={r['beta_loc_half']:.3f} "
      f"best classical {r['best_classical']}  N2q per grid point {r['n2q']}  max|U-U^T|={r.get('UT_err', float('nan')):.1e}")

# ---------------- ideal S
P("\nIDEAL step advantage S = gap_q / gap_best_classical, median [IQR] over seeds")
for (src, fam, n), g in d[d.variant.isin(["ideal", "ideal_t2", "P1_exact_m16", "decohered_grid"])].groupby(["source", "family", "n"]):
    for v, gv in g.groupby("variant"):
        P(f"  {src} {fam} n={n} {v}: " + "  ".join(f"{rg} {q(gv[gv.regime == rg].S_plain)}" for rg in REG))

# ---------------- eps* tables
P("\nTHRESHOLDS (median over seeds of S_plain(eps)); eps*=S drops to 1; epsU=row-TVD(Q,uniform)<0.1")
P("  eps = avg 2q gate infidelity (dep), per-gate dephasing prob (deph), per-gate damping gamma (ad*), readout flip prob (ro*)")
thr = []
for (src, n, noise), g in d[d.noise.isin(["dep", "deph", "ad", "adgp", "adtw", "adsplit", "gdepmodel", "rosym", "roasym", "rofix"])].groupby(
        ["source", "n", "noise"]):
    for rg in REG:
        gr = g[g.regime == rg]
        med = gr.groupby("eps")[["S_plain", "S_hast", "tvd_unif", "bias_tvd", "asym", "F"]].median().sort_index()
        ideal = d[(d.source == src) & (d.n == n) & (d.variant == "ideal") & (d.regime == rg)].S_plain.median()
        e = list(med.index)
        es = cross([0] + e if False else e, med.S_plain.values, 1.0)
        eu = cross(e, med.tvd_unif.values, 0.1)
        thr.append(dict(source=src, n=n, noise=noise, regime=rg, S_ideal=ideal, eps_star=es, eps_U=eu,
                        S_by_eps={f"{k:g}": round(v, 3) for k, v in med.S_plain.items()},
                        Shast_by_eps={f"{k:g}": round(v, 3) for k, v in med.S_hast.items()},
                        bias_tvd_by_eps={f"{k:g}": float(f"{v:.3g}") for k, v in med.bias_tvd.items()},
                        asym_by_eps={f"{k:g}": float(f"{v:.3g}") for k, v in med.asym.items()}))
        tag = "never<=1 in range" if es is None else ("S<=1 already ideal" if es == 0 else f"{es:.2g}")
        P(f"  {src:16s} n={n:2d} {noise:9s} {rg:6s} S_ideal={ideal:6.2f} eps*={tag:18s} epsU={eu if eu is None else f'{eu:.2g}'}  "
          + " ".join(f"{k:g}:{v:.2f}" for k, v in med.S_plain.items()))
json.dump(thr, open("results/thresholds.json", "w"), indent=1, default=float)

# ---------------- bias
P("\nBIAS of plain Metropolis (exact stationary distribution vs Boltzmann), median over seeds; Hastings chain bias = 0 by construction")
for (src, n, noise), g in d[d.noise.isin(["ad", "adgp", "adtw", "adsplit", "rosym", "roasym", "rofix", "dep", "deph"])].groupby(["source", "n", "noise"]):
    for rg in REG:
        gr = g[g.regime == rg].groupby("eps")[["asym", "bias_tvd", "bias_kl"]].median()
        P(f"  {src} n={n} {noise:7s} {rg:6s} " + " ".join(f"{k:g}: asym {r.asym:.2g} TVD {r.bias_tvd:.2g} KL {r.bias_kl:.2g} |" for k, r in gr.iterrows()))

# ---------------- fake backends
P("\nDEVICE-CALIBRATED (Aer density matrix, exact probabilities, n=6, grid gamma{0.3,0.5} x t=2), median [IQR] over seeds")
fk = d[d.source.str.startswith("aer_")]
for (src, v), g in fk.groupby(["source", "variant"]):
    s = f"  {src} {v}: asym {q(g.asym)} TVD_ideal {q(g.tvd_ideal)} TVD_unif {q(g.tvd_unif)} F_eff {q(g.F_eff)}"
    if "cz" in g:
        s += f" CZ/circuit {g.cz.median():.0f}"
    P(s)
    for rg in REG:
        gr = g[g.regime == rg]
        P(f"      {rg:6s} S_plain {q(gr.S_plain)} S_hast {q(gr.S_hast)} bias TVD {q(gr.bias_tvd)} KL {q(gr.bias_kl)}")

# ---------------- fit a
P("\nFIT S_eff = 1 + (S_ideal-1) F^a  (least squares in log, points with 0.02<F<0.98 and S>1)")
fits = {}
for src, noise in [("exactDM", "dep"), ("model_global_dep", "gdepmodel")]:
    for rg in REG:
        g = d[(d.source == src) & (d.noise == noise) & (d.regime == rg)]
        xs, ys, xe, ye = [], [], [], []
        for (n, seed), gg in g.groupby(["n", "seed"]):
            Si = d[(d.source == src) & (d.n == n) & (d.seed == seed) & (d.variant == "ideal") & (d.regime == rg)].S_plain.iloc[0]
            if Si <= 1.05:
                continue
            y = (gg.S_plain.values - 1) / (Si - 1)
            for F, Fe, yy in zip(gg.F.values, gg.F_eff.values, y):
                if 0.02 < F < 0.98 and yy > 0:
                    xs.append(np.log(F)); ys.append(np.log(yy)); xe.append(np.log(max(Fe, 1e-6))); ye.append(np.log(yy))
        if len(xs) >= 3:
            xs, ys, xe = map(np.array, (xs, ys, xe))
            a = float(xs @ ys / (xs @ xs))
            ae = float(xe @ ys / (xe @ xe))
            fits[f"{src}_{rg}"] = dict(a_Fproxy=a, a_Feff=ae, npts=len(xs))
            P(f"  {src} {noise} {rg}: a (F proxy (1-eps)^N2q (1-eps/10)^N1q) = {a:.2f}; a (F_eff fitted from Q) = {ae:.2f}; points {len(xs)}")
        else:
            P(f"  {src} {noise} {rg}: too few points (S_ideal<=1.05 or F out of range)")
json.dump(fits, open("results/fit_a.json", "w"), indent=1)

open("results/summary.txt", "w").write("\n".join(lines) + "\n")

# ---------------- plots
cols = {"dep": "C0", "deph": "C1", "ad": "C3", "adgp": "C4", "adtw": "C2", "gdepmodel": "C7", "roasym": "C5", "rosym": "C8"}
fig, axs = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
for ax, rg in zip(axs, REG):
    for (src, n, noise), g in d[(d.regime == rg) & d.noise.isin(list(cols))].groupby(["source", "n", "noise"]):
        if noise.startswith("ro"):
            continue
        med = g.groupby("eps").S_plain.median()
        ls = {6: "-", 8: "--", 10: ":", 9: "-."}.get(n, "-")
        ax.plot(med.index, med.values, ls, marker="o", ms=3, color=cols[noise], label=f"{noise} n={n} {src.split('_')[0]}")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(f"{rg} (beta = {dict(LOW='3', MEDIUM='1', HIGH='1/3')[rg]} x beta_c)")
    ax.set_xlabel("eps (2q error / per-gate damping or dephasing)")
axs[0].set_ylabel("S = gap_noisy(plain Metropolis) / gap_best_classical  (median of 5 SK seeds)")
axs[2].legend(fontsize=6)
fig.tight_layout(); fig.savefig("plots/S_vs_eps.png", dpi=130)

fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
for noise in ["ad", "adgp", "adtw", "roasym", "rosym", "rofix"]:
    for n in (6, 8):
        g = d[(d.source == "exactDM") & (d.n == n) & (d.noise == noise) & (d.regime == "LOW")]
        if len(g) == 0:
            continue
        med = g.groupby("eps")[["bias_tvd", "S_plain", "S_hast"]].median()
        ls = "-" if n == 6 else "--"
        axs[0].plot(med.index, np.maximum(med.bias_tvd, 1e-12), ls, marker="o", ms=3, label=f"{noise} n={n} plain MH")
        axs[1].plot(med.index, med.S_plain / med.S_hast, ls, marker="o", ms=3, label=f"{noise} n={n}")
axs[0].axhline(1e-12, color="gray", lw=0.6)
axs[0].set_xscale("log"); axs[0].set_yscale("log"); axs[0].set_xlabel("eps (per-gate gamma; readout flip prob for ro*)")
axs[0].set_ylabel("TVD(stationary of plain Metropolis, Boltzmann)  LOW regime\n(Hastings with exact Q_noisy: 0; floor 1e-12 = exact)")
axs[0].legend(fontsize=7)
axs[1].set_xscale("log"); axs[1].set_xlabel("eps"); axs[1].set_ylabel("gap plain / gap Hastings (LOW)"); axs[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig("plots/bias_vs_eps.png", dpi=130)

fig, ax = plt.subplots(figsize=(6, 4.5))
for src, noise, mk in [("exactDM", "dep", "o"), ("model_global_dep", "gdepmodel", "x")]:
    for rg, c in zip(REG, ["C0", "C1", "C3"]):
        g = d[(d.source == src) & (d.noise == noise) & (d.regime == rg)]
        for (n, seed), gg in g.groupby(["n", "seed"]):
            Si = d[(d.source == src) & (d.n == n) & (d.seed == seed) & (d.variant == "ideal") & (d.regime == rg)].S_plain.iloc[0]
            if Si > 1.05:
                ax.plot(gg.F, (gg.S_plain - 1) / (Si - 1), mk, color=c, ms=4, alpha=0.6,
                        label=f"{src.split('_')[0]} {rg}" if (n, seed) == (6, 100) else None)
Fg = np.logspace(-2, 0, 50)
ax.plot(Fg, Fg, "k--", lw=0.8, label="a=1")
ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=1e-2); ax.set_xlabel("F = (1-eps)^N2q (1-eps/10)^N1q (grid mean)")
ax.set_ylabel("(S_noisy - 1) / (S_ideal - 1)"); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig("plots/afit.png", dpi=130)
print("\n".join(lines[-12:]))
