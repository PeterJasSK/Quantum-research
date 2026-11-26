"""Aggregate raw/*.json -> results/gaps.csv, kfits.csv, S_table.csv, summary.txt, plots/*.png.
Run: python d9_analyze.py
"""
import glob
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{here}/results", exist_ok=True)
os.makedirs(f"{here}/plots", exist_ok=True)
recs, meta = [], []
for f in sorted(glob.glob(f"{here}/raw/*.json")):
    r = json.load(open(f))
    meta.append(dict(family=r["family"], n=r["n"], seed=r["seed"], beta_c=r["beta_c"], n_minima=r["n_minima"],
                     t_total_s=r["t_total_s"], t_laws_s=r["t_laws_s"]))
    for x in r["rows"]:
        recs.append(dict(family=r["family"], n=r["n"], seed=r["seed"], **x))
df = pd.DataFrame(recs)
df["L"] = df["L"].astype(str)
df["gap"] = df["gap"].clip(lower=0)
meta = pd.DataFrame(meta)
df.to_csv(f"{here}/results/gaps.csv", index=False)
meta.to_csv(f"{here}/results/instances.csv", index=False)
REG = {"0.1": "HIGH", "0.3": "MEDIUM", "0.5": "MEDIUM", "bc": "MEDIUM", "1": "LOW", "3": "LOW"}
CLASS = ["cE_DEpi", "cF_basin", "cG_perc", "cH_wtmatch"]
out = []
P = lambda s: out.append(s)  # noqa: E731

P("D9 V24 mask-library summary (own simulation, ideal/noiseless, exact transition matrices).")
P("Instances: " + ", ".join(f"{fa} n={n}: {g.seed.nunique()}" for (fa, n), g in meta.groupby(["family", "n"])))
P("beta_c (specific-heat peak) median [min,max]: " + "; ".join(
    f"{fa} n={n}: {g.beta_c.median():.3f} [{g.beta_c.min():.3f},{g.beta_c.max():.3f}]"
    for (fa, n), g in meta.groupby(["family", "n"])))
P("local minima (greedy basins) median: " + "; ".join(
    f"{fa} n={n}: {g.n_minima.median():.0f}" for (fa, n), g in meta.groupby(["family", "n"])))

# ---------------- k fits (SK only, n = 6..12), bootstrap over instances
rng = np.random.default_rng(0)
krows = []
sk = df[df.family == "sk"]
for (law, L, mix, bl), g in sk.groupby(["law", "L", "mix", "blabel"]):
    ns = sorted(g.n.unique())
    if len(ns) < int(os.environ.get("D9_MIN_NS", 3)):
        continue
    per = {n: g[g.n == n].gap.values for n in ns}
    med = np.array([np.median(per[n]) for n in ns])
    if (med <= 1e-12).any():
        krows.append(dict(law=law, L=L, mix=mix, blabel=bl, regime=REG[bl], ns=f"{ns[0]}-{ns[-1]}", k=np.inf,
                          lo=np.inf, hi=np.inf, gap_maxn=med[-1]))
        continue
    k = -np.polyfit(ns, np.log2(med), 1)[0]
    bs = []
    for _ in range(200):
        m = [np.median(rng.choice(per[n], len(per[n]))) for n in ns]
        if min(m) > 1e-12:
            bs.append(-np.polyfit(ns, np.log2(m), 1)[0])
    lo, hi = np.percentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan)
    krows.append(dict(law=law, L=L, mix=mix, blabel=bl, regime=REG[bl], ns=f"{ns[0]}-{ns[-1]}", k=k, lo=lo, hi=hi,
                      gap_maxn=med[-1]))
kf = pd.DataFrame(krows)
kf.to_csv(f"{here}/results/kfits.csv", index=False)

P("\nFITTED k (gap ~ 2^-kn, SK, median over instances, 95% bootstrap CI), infinite libraries, pure mask moves:")
laws_show = ["qFull_P1", "qA_unifref", "qC_piref", "qD_decoh", "cE_DEpi", "cF_basin", "cG_perc", "cH_wtmatch", "uniform", "local"]
for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
    s = kf[(kf.L == "inf") & (kf.mix == 0) & (kf.blabel == bl)].set_index("law")
    P(f" beta={bl:>3} ({REG[bl]}): " + " | ".join(
        f"{l} {s.loc[l,'k']:.2f}[{s.loc[l,'lo']:.2f},{s.loc[l,'hi']:.2f}]" for l in laws_show if l in s.index))
P("Same, 50% local + 50% mask mixtures:")
for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
    s = kf[(kf.L == "inf") & (kf.mix == 1) & (kf.blabel == bl)].set_index("law")
    P(f" beta={bl:>3} ({REG[bl]}): " + " | ".join(
        f"{l} {s.loc[l,'k']:.2f}[{s.loc[l,'lo']:.2f},{s.loc[l,'hi']:.2f}]" for l in laws_show if l in s.index))
P("k of quantum library qA vs L (pure / mixed), per beta:")
for bl in ["0.1", "0.3", "bc", "1", "3"]:
    s = kf[(kf.law == "qA_unifref") & (kf.blabel == bl)]
    P(f" beta={bl:>3}: " + " | ".join(f"L={r.L} mix={r.mix} k={r.k:.2f} (n {r.ns})" for r in s.itertuples()))


# ---------------- step ratio S at equal L
def best_classical(g, L, mix, circular):
    c = g[(g.L == L) & (g.mix == mix) & g.law.isin(CLASS if circular else [x for x in CLASS if x != "cE_DEpi"])]
    base = g[(g.L == "inf") & g.law.isin(["uniform", "local"]) & ((g.mix == mix) | (g.law == "local"))]
    allc = pd.concat([c, base])
    if allc.empty:
        return np.nan, ""
    i = allc.gap.values.argmax()
    return allc.gap.values[i], allc.law.values[i]


srows = []
for (fa, n, seed, bl), g in df.groupby(["family", "n", "seed", "blabel"]):
    for L in sorted(g.L.unique(), key=lambda x: (x == "inf", int(x) if x != "inf" else 0)):
        for mix in (0, 1):
            q = g[(g.law == "qA_unifref") & (g.L == L) & (g.mix == mix)]
            if q.empty:
                continue
            for circ in (True, False):
                bc, who = best_classical(g, L, mix, circ)
                srows.append(dict(family=fa, n=n, seed=seed, blabel=bl, regime=REG[bl], L=L, mix=mix, circ=circ,
                                  gap_q=q.gap.values[0], gap_c=bc, best_c=who, S=q.gap.values[0] / bc))
        qd = g[(g.law == "qD_decoh") & (g.L == "inf") & (g.mix == 0)]
        qa = g[(g.law == "qA_unifref") & (g.L == "inf") & (g.mix == 0)]
        qc = g[(g.law == "qC_piref") & (g.L == "inf") & (g.mix == 0)]
        ce = g[(g.law == "cE_DEpi") & (g.L == "inf") & (g.mix == 0)]
    if not qd.empty:
        srows.append(dict(family=fa, n=n, seed=seed, blabel=bl, regime=REG[bl], L="inf", mix=0, circ="decoh",
                          gap_q=qa.gap.values[0], gap_c=qd.gap.values[0], best_c="qD_decoh",
                          S=qa.gap.values[0] / qd.gap.values[0]))
    srows.append(dict(family=fa, n=n, seed=seed, blabel=bl, regime=REG[bl], L="inf", mix=0, circ="piref_vs_DE",
                      gap_q=qc.gap.values[0], gap_c=ce.gap.values[0], best_c="cE_DEpi",
                      S=qc.gap.values[0] / max(ce.gap.values[0], 1e-300)))
St = pd.DataFrame(srows)
St.to_csv(f"{here}/results/S_per_instance.csv", index=False)


def summ(x):
    x = x.replace([np.inf], np.nan).dropna()
    return f"{np.median(x):.2f} [{np.percentile(x,25):.2f},{np.percentile(x,75):.2f}]" if len(x) else "na"


agg = St.groupby(["family", "n", "blabel", "L", "mix", "circ"]).agg(
    S_med=("S", "median"), S_q25=("S", lambda x: np.percentile(x, 25)), S_q75=("S", lambda x: np.percentile(x, 75)),
    best_c=("best_c", lambda x: x.value_counts().index[0])).reset_index()
agg.to_csv(f"{here}/results/S_table.csv", index=False)

P("\nS = gap(quantum library qA, uniform refs) / gap(best classical at equal L incl. uniform/local), median [IQR], most-frequent winner")
for fa in ["sk", "ea"]:
    for circ, lab in ((True, "classical set incl. DE-from-pi (circular)"), (False, "non-circular classical set (F,G,H,unif,local)")):
        P(f" {fa.upper()} vs {lab}:")
        for mix in (0, 1):
            for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
                for n in sorted(St.n.unique()):
                    s = St[(St.family == fa) & (St.n == n) & (St.blabel == bl) & (St.mix == mix) & (St.circ == circ)]
                    if s.empty:
                        continue
                    parts = []
                    for L, gL in s.groupby("L"):
                        parts.append((L, f"L={L}: {summ(gL.S)} {gL.best_c.value_counts().index[0]}"))
                    parts.sort(key=lambda p: (p[0] == "inf", int(p[0]) if p[0] != "inf" else 0))
                    P(f"  mix={mix} beta={bl:>3} n={n}: " + " | ".join(p[1] for p in parts))
P("\nDecohered control: gap(qA coherent)/gap(qD decohered), infinite library, pure masks, median [IQR]:")
for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
    P(f" beta={bl:>3}: " + " | ".join(f"n={n} {summ(g.S)}" for n, g in
                                    St[(St.circ == "decoh") & (St.blabel == bl)].groupby("n")))
P("Library keeps what fraction of full P1 QeMCMC gap: gap(qA)/gap(qFull), median [IQR]:")
for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
    parts = []
    for (fa, n), g in df[(df.blabel == bl) & (df.L == "inf") & (df.mix == 0)].groupby(["family", "n"]):
        a = g[g.law == "qA_unifref"].set_index("seed").gap
        f = g[g.law == "qFull_P1"].set_index("seed").gap
        r = (a / f).dropna()
        if len(r):
            parts.append(f"{fa} n={n} {summ(r)}")
    P(f" beta={bl:>3}: " + " | ".join(parts))
P("Circular pair: gap(qC, refs~pi)/gap(cE, DE r1 xor r2 ~ pi), infinite library, median [IQR]:")
for fa in ["sk", "ea"]:
    for bl in ["0.1", "0.3", "0.5", "bc", "1", "3"]:
        s = St[(St.circ == "piref_vs_DE") & (St.blabel == bl) & (St.family == fa)]
        if len(s):
            P(f" {fa} beta={bl:>3}: " + " | ".join(f"n={n} {summ(g.S)}" for n, g in s.groupby("n")))

# full-QeMCMC reference not recomputed here (see pilot / B7). Median raw gaps at max n for orientation:
P("\nMedian gaps, infinite libraries, pure masks (SK n=max, EA n=12):")
for fa in ["sk", "ea"]:
    sub = df[(df.family == fa) & (df.L == "inf") & (df.mix == 0)]
    if sub.empty:
        continue
    nm = sub.n.max()
    t = sub[sub.n == nm].groupby(["blabel", "law"]).gap.median().unstack()
    P(f" {fa} n={nm}:\n" + t.to_string(float_format=lambda v: f"{v:.2e}"))
open(f"{here}/results/summary.txt", "w").write("\n".join(out) + "\n")

# ---------------- plots
order = ["0.1", "0.3", "0.5", "1", "3"]
nm = df[df.family == "sk"].n.max()
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
for ax, mix in zip(axs, (0, 1)):
    for law in laws_show:
        s = df[(df.family == "sk") & (df.n == nm) & (df.L == "inf") & (df.mix == mix) & (df.law == law)]
        if s.empty:
            continue
        m = s.groupby("blabel").gap.median()
        xs = [float(b) for b in order if b in m.index]
        ax.plot(xs, [max(m[b], 1e-8) for b in order if b in m.index], "o-", label=law)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("beta"); ax.set_title(
        f"SK n={nm}, infinite mask libraries, {'50% local + 50% mask' if mix else 'pure mask moves'}")
axs[0].set_ylabel("spectral gap (median over instances)")
axs[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{here}/plots/gap_vs_beta_sk.png", dpi=120)

fig, ax = plt.subplots(figsize=(12, 4.5))
blist = ["0.1", "0.3", "bc", "1", "3"]
wd = 0.8 / len(blist)
for j, bl in enumerate(blist):
    s = kf[(kf.L == "inf") & (kf.mix == 0) & (kf.blabel == bl)].set_index("law")
    ks = [s.loc[l, "k"] if l in s.index and np.isfinite(s.loc[l, "k"]) else np.nan for l in laws_show]
    lo = [s.loc[l, "lo"] if l in s.index else np.nan for l in laws_show]
    hi = [s.loc[l, "hi"] if l in s.index else np.nan for l in laws_show]
    x = np.arange(len(laws_show)) + j * wd
    ax.bar(x, ks, wd, label=f"beta={bl}", yerr=[np.array(ks) - np.array(lo), np.array(hi) - np.array(ks)], capsize=2)
ax.set_xticks(np.arange(len(laws_show)) + 0.4); ax.set_xticklabels(laws_show, rotation=20, fontsize=8)
ax.set_ylabel("fitted k (gap ~ 2^-kn), SK n=6..12"); ax.legend(fontsize=8)
ax.set_title("k per mask law (infinite library, pure moves; reducible laws omitted)")
fig.tight_layout(); fig.savefig(f"{here}/plots/k_vs_law_sk.png", dpi=120)

fig, ax = plt.subplots(figsize=(7, 4.5))
for bl in ["0.3", "bc", "1", "3"]:
    s = St[(St.family == "sk") & (St.n == nm) & (St.blabel == bl) & (St.mix == 0) & (St.circ == False)]  # noqa: E712
    m = s.groupby("L").S.median()
    Lx = [L for L in ["32", "128", "1024", "8192"] if L in m.index]
    ax.plot([int(L) for L in Lx], [m[L] for L in Lx], "o-", label=f"beta={bl}")
ax.axhline(1, color="k", lw=0.8); ax.axhline(1.5, color="gray", ls=":"); ax.axhline(2, color="gray", ls="--")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("library size L"); ax.set_ylabel("S = gap(qA lib)/gap(best non-circular classical)")
ax.set_title(f"SK n={nm}: quantum vs classical library at equal L"); ax.legend()
fig.tight_layout(); fig.savefig(f"{here}/plots/S_vs_L_sk.png", dpi=120)
print("\n".join(out[:60]))
