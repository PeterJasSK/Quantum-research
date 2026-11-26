"""Aggregate D1 results -> CSV tables, summary text, plots.  Usage: python analyze.py"""
import glob, json, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import d1lib as L

R = "results/"
out = open(R + "summary.txt", "w")
def P(*a):
    print(*a); print(*a, file=out)

fams = ["sk10", "ea34", "ea33", "fe34", "fe33"]
famname = {"sk10": "SK n=10 (with field)", "ea34": "2D EA +-J 3x4 periodic (n=12)", "ea33": "2D EA +-J 3x3 periodic (n=9)",
           "fe34": "2D ferromagnet 3x4 periodic (n=12)", "fe33": "2D ferromagnet 3x3 periodic (n=9)"}

# SK sampled clusters (n=10, instances 0..4)
sk_s = {}
for f in glob.glob(R + "sk_clusters_sampled_n10_i*.json"):
    r = json.load(open(f)); sk_s[r["instance"]] = r


def derived(r):
    g = {k: np.array(v) for k, v in r["gaps"].items()}
    d = {}
    d["local"], d["uniform"] = g["local"], g["uniform"]
    d["bestmix"] = np.max([v for k, v in g.items() if k.startswith("mix") or k in ("local", "uniform")], 0)
    d["layden"] = g["layden"]
    tk = [k for k in g if k.startswith("cell") or k.startswith("band")]
    T = np.array([g[k] for k in tk])
    d["tuned"] = T.max(0)
    d["tuned_choice"] = [tk[i] for i in T.argmax(0)]
    d["decohered"] = g["decohered_layden"]
    dk = [k for k in g if k.startswith("deccell")]
    if dk:
        d["decohered_tuned"] = np.max([g[k] for k in dk], 0)
    for k in g:
        if k.startswith("cg"):
            d[k] = g[k]
    if "SW" in g:
        d["SW"], d["Wolff"] = g["SW"], g["Wolff"]
    elif r["family"] == "sk10" and r["instance"] in sk_s:
        s = sk_s[r["instance"]]
        idx = [int(np.argmin(np.abs(np.array(r["ratios"]) - x))) for x in s["ratios"]]
        for key in ("SW", "Wolff"):
            a = np.full(len(r["ratios"]), np.nan); a[idx] = s[key]; d[key] = a
    d["bestclassical"] = np.nanmax([d[k] for k in ("bestmix", "SW", "Wolff") if k in d], 0)
    return d


rows = []          # long csv
data = collections.defaultdict(list)
for fam in fams:
    for f in sorted(glob.glob(R + f"fam_{fam}_i*.json")):
        r = json.load(open(f)); d = derived(r)
        data[fam].append((r, d))
        for k, v in d.items():
            if k in ("tuned_choice", "SW_sd"):
                continue
            for ratio, b, x in zip(r["ratios"], r["betas"], v):
                rows.append((fam, r["instance"], r["n"], r["beta_c"], ratio, b, L.regime_of(ratio), k, x))
with open(R + "gaps_long.csv", "w") as fh:
    fh.write("family,instance,n,beta_c,beta_over_beta_c,beta,regime,proposal,gap\n")
    for row in rows:
        fh.write(",".join(str(x) for x in row) + "\n")

# ---------------- regime boundaries
P("D1 TEMPERATURE MAP - summary (own simulation, ideal, exact unless marked sampled)")
P("Regimes per instance: HIGH beta/beta_c <= 0.5, MEDIUM 0.5 < beta/beta_c <= 2, LOW > 2; beta_c = specific-heat peak.")
for fam in fams:
    if not data[fam]:
        continue
    bcs = [r["beta_c"] for r, _ in data[fam]]
    bl = [r.get("beta_local_collapse") for r, _ in data[fam] if r.get("beta_local_collapse")]
    P(f"{famname[fam]}: instances {len(bcs)}, beta_c median {np.median(bcs):.3f} [range {min(bcs):.3f}-{max(bcs):.3f}]"
      + (f", local-gap collapse (gap<10% of its max) beta median {np.median(bl):.3f}" if bl else ""))

# ---------------- S tables
def regime_stat(fam, num, den):
    res = {}
    for reg in ("HIGH", "MEDIUM", "LOW"):
        vals = []
        for r, d in data[fam]:
            if num not in d or den not in d:
                continue
            m = np.array([L.regime_of(x) == reg for x in r["ratios"]])
            ratio = d[num][m] / np.maximum(d[den][m], 1e-300)
            if np.all(np.isnan(ratio)):
                continue
            vals.append(np.exp(np.nanmean(np.log(np.maximum(ratio, 1e-300)))))
        if vals:
            res[reg] = (np.median(vals), np.percentile(vals, 25), np.percentile(vals, 75), len(vals))
    return res

pairs = [("layden", "local"), ("layden", "uniform"), ("layden", "bestmix"), ("layden", "bestclassical"),
         ("tuned", "bestmix"), ("tuned", "bestclassical"), ("decohered", "bestclassical"),
         ("decohered_tuned", "bestclassical"), ("layden", "decohered"), ("tuned", "decohered_tuned"),
         ("SW", "bestmix"), ("Wolff", "bestmix"), ("cg3", "bestclassical"), ("cg4", "bestclassical"),
         ("cg5", "bestclassical"), ("cg6", "bestclassical"), ("cg3", "layden"), ("cg6", "layden")]
st_rows = []
P("\nS = gap ratio, per instance geometric mean over the regime's beta points, then median [IQR] over instances")
for fam in fams:
    if not data[fam]:
        continue
    P(f"\n{famname[fam]}")
    for num, den in pairs:
        s = regime_stat(fam, num, den)
        if not s:
            continue
        line = f"  {num:>15s}/{den:<14s}" + "".join(
            f" {reg}: {v[0]:9.3g} [{v[1]:.3g},{v[2]:.3g}] N={v[3]}" for reg, v in s.items())
        P(line)
        for reg, v in s.items():
            st_rows.append((fam, num, den, reg, *v))
with open(R + "S_table.csv", "w") as fh:
    fh.write("family,numerator,denominator,regime,median,q25,q75,n_instances\n")
    for row in st_rows:
        fh.write(",".join(str(x) for x in row) + "\n")

# winner of best classical and tuned choice per regime
P("\nWhich classical method is best (count of instance-beta points) and tuned-cell choice")
for fam in fams:
    for reg in ("HIGH", "MEDIUM", "LOW"):
        win = collections.Counter(); tc = collections.Counter()
        for r, d in data[fam]:
            ks = [k for k in ("bestmix", "SW", "Wolff") if k in d]
            for i, x in enumerate(r["ratios"]):
                if L.regime_of(x) != reg:
                    continue
                win[ks[int(np.nanargmax([d[k][i] for k in ks]))]] += 1
                c = d["tuned_choice"][i]
                tc[c.split("_w")[-1] if c.startswith("cell") else "band"] += 1
        if win:
            P(f"  {fam} {reg}: best classical {dict(win)}; tuned t-window index (0:[.3,1.5] 1:[1.5,6] 2:[6,24] 3:[24,96]) {dict(tc)}")

# ---------------- plots gap vs beta/beta_c
show = [("uniform", "C0", "-"), ("local", "C1", "-"), ("bestmix", "C2", "--"), ("SW", "C3", "-"), ("Wolff", "C4", "-"),
        ("layden", "k", "-"), ("tuned", "k", "--"), ("decohered", "0.5", ":"), ("cg3", "C5", "-."), ("cg4", "C6", "-."),
        ("cg5", "C6", "-."), ("cg6", "C7", "-.")]
fig, axs = plt.subplots(2, 3, figsize=(16, 9))
for ax, fam in zip(axs.flat, fams):
    if not data[fam]:
        continue
    x = np.array(data[fam][0][0]["ratios"])
    for k, c, ls in show:
        ys = [d[k] for r, d in data[fam] if k in d]
        if not ys:
            continue
        y = np.nanmedian(np.maximum(ys, 1e-16), 0); ok = ~np.isnan(y)
        ax.plot(x[ok], y[ok], color=c, ls=ls, marker="o", ms=3, label=f"{k} (N={len(ys)})")
    ax.axvspan(0.5, 2.0, color="y", alpha=0.15)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(1e-8, 1.2)
    ax.set_xlabel("beta / beta_c (beta_c = specific-heat peak)"); ax.set_ylabel("spectral gap (median over instances)")
    ax.set_title(famname[fam], fontsize=10); ax.grid(alpha=0.3)
    ax.legend(fontsize=6.5, loc="lower left")
axs.flat[-1].axis("off")
axs.flat[-1].text(0.05, 0.5, "Shaded = MEDIUM (0.5..2 beta_c)\nleft = HIGH, right = LOW\nexact ideal gaps; SK SW/Wolff sampled (2e4/state)\n"
                  "tuned = best of 32 (gamma,t-window) cells + 4 bands per beta", fontsize=10)
plt.tight_layout(); plt.savefig("plots/gap_vs_beta_all_families.png", dpi=130); plt.close()

fig, axs = plt.subplots(2, 3, figsize=(16, 9))
for ax, fam in zip(axs.flat, fams):
    if not data[fam]:
        continue
    x = np.array(data[fam][0][0]["ratios"])
    for (num, den, c, ls) in [("layden", "bestclassical", "k", "-"), ("tuned", "bestclassical", "k", "--"),
                              ("layden", "bestmix", "C2", "-"), ("tuned", "bestmix", "C2", "--"),
                              ("decohered", "bestclassical", "0.5", ":")]:
        ys = np.array([d[num] / d[den] for r, d in data[fam]])
        med = np.nanmedian(ys, 0); q1, q3 = np.nanpercentile(ys, [25, 75], 0)
        ax.plot(x, med, color=c, ls=ls, marker="o", ms=3, label=f"{num}/{den}")
        ax.fill_between(x, q1, q3, color=c, alpha=0.1)
    ax.axhline(1, color="r", lw=0.8); ax.axvspan(0.5, 2.0, color="y", alpha=0.15)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("beta / beta_c"); ax.set_ylabel("S = gap ratio (median, IQR)")
    ax.set_title(famname[fam], fontsize=10); ax.grid(alpha=0.3); ax.legend(fontsize=7)
axs.flat[-1].axis("off")
plt.tight_layout(); plt.savefig("plots/S_vs_beta_all_families.png", dpi=130); plt.close()

# ---------------- scaling
sc = collections.defaultdict(list)
for f in glob.glob(R + "scal_n*_i*.json"):
    r = json.load(open(f)); g = {k: np.array(v) for k, v in r["gaps"].items()}
    d = {"local": g["local"], "uniform": g["uniform"], "layden": g["layden"], "cg_sqrt_n": g["cg"],
         "bestmix": np.max([v for k, v in g.items() if k.startswith("mix") or k in ("local", "uniform")], 0),
         "tuned": np.max([v for k, v in g.items() if k.startswith("cell")], 0)}
    sc[r["n"]].append(d)
props = ["local", "uniform", "bestmix", "layden", "tuned", "cg_sqrt_n"]
regs = ["HIGH (0.5 beta_c)", "MEDIUM (1 beta_c)", "LOW (3 beta_c)"]
fit = {}
rng = np.random.default_rng(0)
ns = sorted(sc)


def fitk(nlist, ylist):
    A = np.vstack([nlist, np.ones(len(nlist))]).T
    c, *_ = np.linalg.lstsq(A, ylist, rcond=None)
    pred = A @ c; ss = ((ylist - pred) ** 2).sum(); st = ((ylist - ylist.mean()) ** 2).sum()
    return -c[0], 1 - ss / st if st > 0 else np.nan


if ns:
    P(f"\nSK GAP SCALING gap ~ 2^(-k n), n = {ns}, instances per n = {[len(sc[n]) for n in ns]}; fit on all instance points, "
      "95% CI from 2000 bootstrap resamples of instances within each n; also split fits n<=9 and n>=9")
    with open(R + "scaling_fits.csv", "w") as fh:
        fh.write("regime,proposal,k,ci_lo,ci_hi,R2,k_n6to9,k_n9to12\n")
        for ri, reg in enumerate(regs):
            for p in props:
                nn = np.concatenate([[n] * len(sc[n]) for n in ns])
                yy = np.concatenate([[np.log2(max(d[p][ri], 1e-300)) for d in sc[n]] for n in ns])
                k, r2 = fitk(nn, yy)
                bs = []
                for b in range(2000):
                    nb, yb = [], []
                    for n in ns:
                        idx = rng.integers(0, len(sc[n]), len(sc[n]))
                        nb += [n] * len(idx); yb += [np.log2(max(sc[n][i][p][ri], 1e-300)) for i in idx]
                    bs.append(fitk(np.array(nb), np.array(yb))[0])
                lo, hi = np.percentile(bs, [2.5, 97.5])
                m1 = nn <= 9; m2 = nn >= 9
                k1 = fitk(nn[m1], yy[m1])[0]; k2 = fitk(nn[m2], yy[m2])[0]
                fit[(reg, p)] = (k, lo, hi, r2, k1, k2)
                fh.write(f"{reg},{p},{k:.4f},{lo:.4f},{hi:.4f},{r2:.3f},{k1:.4f},{k2:.4f}\n")
                P(f"  {reg:18s} {p:10s} k = {k:6.3f} [{lo:6.3f},{hi:6.3f}]  R2 {r2:.2f}  k(n6-9) {k1:6.3f}  k(n9-12) {k2:6.3f}")
    fig, axs = plt.subplots(1, 4, figsize=(19, 4.6))
    for ri, reg in enumerate(regs):
        ax = axs[ri]
        for p, c in zip(props, ["C1", "C0", "C2", "k", "0.4", "C5"]):
            med = [np.median([np.log2(max(d[p][ri], 1e-300)) for d in sc[n]]) for n in ns]
            ax.plot(ns, med, "o-", color=c, label=f"{p} k={fit[(reg, p)][0]:.2f}")
        ax.set_xlabel("n (SK spins)"); ax.set_ylabel("log2 spectral gap (median)"); ax.set_title("SK " + reg); ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    ax = axs[3]
    for j, (p, c) in enumerate(zip(props, ["C1", "C0", "C2", "k", "0.4", "C5"])):
        ks = [fit[(reg, p)] for reg in regs]
        xx = np.arange(3) + (j - 2.5) * 0.12
        ax.errorbar(xx, [v[0] for v in ks], yerr=[[v[0] - v[1] for v in ks], [v[2] - v[0] for v in ks]], fmt="o", color=c,
                    capsize=3, label=p)
    ax.set_xticks(range(3)); ax.set_xticklabels(["HIGH\n0.5 bc", "MEDIUM\n1 bc", "LOW\n3 bc"])
    ax.set_ylabel("fitted k (gap ~ 2^-kn), 95% bootstrap CI"); ax.axhline(0, color="k", lw=0.5); ax.legend(fontsize=7)
    ax.grid(alpha=0.3); ax.set_title("k vs regime (SK, n=6..12)")
    plt.tight_layout(); plt.savefig("plots/sk_scaling_k_vs_regime.png", dpi=130); plt.close()

# ---------------- SK clusters
try:
    ex = json.load(open(R + "sk_clusters_exact_n6.json"))
    x = np.array(ex[0]["ratios"])
    P("\nSK n=6 with field, EXACT SW/Wolff (ghost spin), median over 10 instances, per beta/beta_c:")
    P("  ratio   " + " ".join(f"{v:7.2f}" for v in x))
    for k in ("SW", "Wolff", "local", "uniform", "mixbest", "layden", "tunedbest"):
        P(f"  {k:8s}" + " ".join(f"{v:7.4f}" for v in np.median([e["gaps"][k] for e in ex], 0)))
    P("  SW/mixbest per regime: " + ", ".join(
        f"{reg} {np.median([np.exp(np.mean(np.log(np.array(e['gaps']['SW'])[m] / np.array(e['gaps']['mixbest'])[m]))) for e in ex]):.3g}"
        for reg, m in [(rg, np.array([L.regime_of(v) == rg for v in x])) for rg in ("HIGH", "MEDIUM", "LOW")]))
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    for k, c in zip(("SW", "Wolff", "local", "uniform", "mixbest", "layden", "tunedbest"), ["C3", "C4", "C1", "C0", "C2", "k", "0.4"]):
        axs[0].plot(x, np.median([e["gaps"][k] for e in ex], 0), "o-", color=c, ms=3, label=k)
    axs[0].set_xscale("log"); axs[0].set_yscale("log"); axs[0].set_title("SK n=6 exact (ghost-spin SW/Wolff), median 10 inst.")
    axs[0].set_xlabel("beta/beta_c"); axs[0].set_ylabel("spectral gap"); axs[0].legend(fontsize=7); axs[0].grid(alpha=0.3)
    if sk_s:
        for i, s in sorted(sk_s.items()):
            axs[1].plot(s["ratios"], s["largest_cluster_frac_pi"], "o-", ms=3, label=f"inst {i}")
        axs[1].set_xscale("log"); axs[1].set_xlabel("beta/beta_c"); axs[1].set_ylabel("<largest SW cluster>/(n+1) under pi")
        axs[1].set_title("SK n=10: SW clusters percolate (sampled)"); axs[1].legend(fontsize=7); axs[1].grid(alpha=0.3)
        P("\nSK n=10 sampled clusters: median largest-cluster fraction per ratio: " + " ".join(
            f"{v:.2f}" for v in np.median([s["largest_cluster_frac_pi"] for s in sk_s.values()], 0)))
        P("  median SW bootstrap sd per ratio: " + " ".join(f"{v:.1e}" for v in np.median([[np.std(b) for b in s["SW_boot"]] for s in sk_s.values()], 0)))
    plt.tight_layout(); plt.savefig("plots/sk_cluster_moves.png", dpi=130); plt.close()
except FileNotFoundError:
    pass
out.close()
