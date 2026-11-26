"""Summaries for E1 red-team: results/summary.txt + results/claimA_cells.csv + results/claimB_rows.csv"""
import json, os, csv
import numpy as np

R = "results"
out = []
P = out.append


def mi(x):
    x = np.asarray([v for v in x if np.isfinite(v)])
    if len(x) == 0:
        return "n/a"
    return f"{np.median(x):.3g} [{np.percentile(x, 25):.3g},{np.percentile(x, 75):.3g}] N={len(x)}"


# ---------------- Claim A
P("CLAIM A (D6 overloaded CDMA window, alpha=0.5, dense) - relaxation-gap ratios, median [IQR] over instance x SNR cells")
cells_all = []
for n in (8, 10, 12):
    f = f"{R}/claimA_n{n}.json"
    if not os.path.exists(f):
        continue
    rows = json.load(open(f))
    cells_all += rows
    P(f"\n n={n}: {len(rows)} rows")
    for b in sorted(set(r["beta"] for r in rows)):
        rb = [r for r in rows if r["beta"] == b]
        P(f"  beta/bm={b}: S_D6(vs L,U,LU)={mi([r['S_C1'] for r in rb])} | S_vs_best_no_modehop={mi([r['S_nomode'] for r in rb])}"
          f" | S_vs_best_realisable={mi([r['S_new'] for r in rb])} | Q/D={mi([r['Q_over_D'] for r in rb])}")
    rb = [r for r in rows if r["beta"] == 1.0]
    P("  matched beta, by SNR:")
    for s in sorted(set(r["snr_db"] for r in rb)):
        rs = [r for r in rb if r["snr_db"] == s]
        names = {}
        for r in rs:
            names[r["best_real_name"]] = names.get(r["best_real_name"], 0) + 1
        P(f"   SNR {s:>4}: S_D6={np.median([r['S_C1'] for r in rs]):.2f} S_noMODE={np.median([r['S_nomode'] for r in rs]):.2f} "
          f"S_best={np.median([r['S_new'] for r in rs]):.2f} frac(S_best>1)={np.mean([r['S_new'] > 1 for r in rs]):.2f} "
          f"best={names} | Q/MODEall={np.median([r['g_Q'] / r['g_MODEall'] for r in rs]):.2f} "
          f"Q/EXMARG={np.median([r['g_Q'] / r['g_EXMARG'] for r in rs]):.2f} | "
          f"P(q12<.5)={np.median([r['P_q12_lt_0.5'] for r in rs]):.2f} basins>5%={np.median([r['n_basins_gt5pct'] for r in rs]):.1f} "
          f"dH(top2)={np.median([r.get('hamming_top2', 0) for r in rs]):.1f} minima={np.median([r['n_minima'] for r in rs]):.0f} "
          f"found={np.median([r['n_minima_found'] for r in rs]):.0f}")
    gk = [k for k in rb[0] if k.startswith("g_")]
    P("  matched beta: median gap Q / each classical kernel: " +
      " ".join(f"{k[2:]}={np.median([r['g_Q'] / max(r[k], 1e-300) for r in rb]):.3g}" for k in gk if k != "g_Q"))
    st = [r for r in rows if "ST_tau_target" in r]
    if st:
        P(f"  ST exact target IAT / charged bound K*tau(gap): {mi([r['ST_tau_target'] / r['ST_tau_bound'] for r in st])}")
        P(f"  ST charged gap / quantum gap: {mi([r['g_ST'] / r['g_Q'] for r in st])}; uncharged ST gap / Q: "
          f"{mi([r['ST_uncharged_max'] / r['g_Q'] for r in st])}")
# multimodality vs S across ALL D6 cells (alpha 0.5..2) at matched beta, n=8 and n=10
P("\n Multimodality vs S in D6's own data (matched beta; var_q12 = Var of two-replica overlap):")
for f in ("exp1_dense_n8.json", "exp1_dense_n10_a0.5.json", "exp1_dense_n10_a1.json", "exp1_dense_n10_a1.5.json",
          "exp1_dense_n10_a2.json"):
    D = [x for x in json.load(open(f"../D6-inference-nishimori/results/{f}")) if x["beta"] == 1.0]
    for al in sorted(set(x["alpha"] for x in D)):
        Da = [x for x in D if x["alpha"] == al]
        P(f"  {f[:-5]} alpha={al}: median var_q12={np.median([x['var_q12'] for x in Da]):.3f} median S={np.median([x['S'] for x in Da]):.2f}")
D = [x for x in json.load(open("../D6-inference-nishimori/results/exp1_dense_n8.json")) if x["beta"] == 1.0]
from scipy.stats import spearmanr
rho = spearmanr([x["var_q12"] for x in D], [x["S"] for x in D])
P(f"  Spearman(var_q12, S) over all n=8 matched cells: rho={rho.correlation:.2f} (p={rho.pvalue:.1e}, N={len(D)})")
if cells_all:
    keys = sorted({k for r in cells_all for k in r if k != "Pq12"})
    with open(f"{R}/claimA_cells.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in cells_all:
            w.writerow({k: r.get(k) for k in keys})

# ---------------- Claim B
P("\n\nCLAIM B (SK, J,h~N(0,1), D1 instances seed 1000n+i): EXACT SW/Wolff (ghost spin, subset DP) at MEDIUM beta/bc in {0.68,1,1.47}")
P(" ratio = absolute-gap ratio (D1 convention); per instance geometric mean over the 3 MEDIUM points, then median [IQR]")
brows = []
for n in (6, 8, 9, 10, 11, 12):
    f = f"{R}/claimB_n{n}.json"
    if not os.path.exists(f):
        continue
    B = json.load(open(f))
    def gm(r, num, den, j=0):
        v = [x[num][j] / max(max(x[d_][j] for d_ in den), 1e-300) for x in r["rows"]]
        return float(np.exp(np.mean(np.log(v))))
    lines = {}
    for tag, num, den in (("layden/mixbest", "layden", ["mixbest"]), ("layden/SW", "layden", ["SW"]),
                          ("layden/Wolff", "layden", ["Wolff"]),
                          ("layden/best(mix,SW,Wolff)", "layden", ["mixbest", "SW", "Wolff"]),
                          ("decohered/best", "decohered", ["mixbest", "SW", "Wolff"])):
        lines[tag] = mi([gm(r, num, den) for r in B])
    if "tuned" in B[0]["rows"][0]:
        lines["tuned/best(mix,SW,Wolff)"] = mi([gm(r, "tuned", ["mixbest", "SW", "Wolff"]) for r in B])
        lines["tuned/layden"] = mi([gm(r, "tuned", ["layden"]) for r in B])
    lines["layden/best relaxation-gap"] = mi([gm(r, "layden", ["mixbest", "SW", "Wolff"], 1) for r in B])
    P(f"\n n={n} ({len(B)} inst, beta_c median {np.median([r['beta_c'] for r in B]):.3f})")
    for k, v in lines.items():
        P(f"   {k:28s} {v}")
    for j, rt in enumerate(B[0]["ratios"]):
        P(f"   at beta/bc={rt:.2f}: layden/best={np.median([r['rows'][j]['layden'][0] / max(r['rows'][j]['mixbest'][0], r['rows'][j]['SW'][0], r['rows'][j]['Wolff'][0]) for r in B]):.3g}"
          f"  SW/mix={np.median([r['rows'][j]['SW'][0] / r['rows'][j]['mixbest'][0] for r in B]):.3g}"
          f"  Wolff/mix={np.median([r['rows'][j]['Wolff'][0] / r['rows'][j]['mixbest'][0] for r in B]):.3g}"
          f"  gaps(med) mix={np.median([r['rows'][j]['mixbest'][0] for r in B]):.3g} SW={np.median([r['rows'][j]['SW'][0] for r in B]):.3g}"
          f" Wolff={np.median([r['rows'][j]['Wolff'][0] for r in B]):.3g} layden={np.median([r['rows'][j]['layden'][0] for r in B]):.3g}")
    P(f"   max SW asym {max(x['SW_asym'] for r in B for x in r['rows']):.1e}, max rowsum err {max(x['SW_rowsum_err'] for r in B for x in r['rows']):.1e}")
    if "tuned_cell" in B[0]["rows"][0]:
        cnt = {}
        for r in B:
            for x in r["rows"]:
                k = x["tuned_cell"].split("_")[0]
                cnt[k] = cnt.get(k, 0) + 1
        P(f"   tuned cell alpha-multiplier counts: {cnt}")
    for r in B:
        for x in r["rows"]:
            brows.append(dict(n=n, inst=r["inst"], beta_c=r["beta_c"], ratio=x["ratio"], beta=x["beta"],
                              **{k: x[k][0] for k in ("local", "uniform", "mixbest", "layden", "decohered", "SW", "Wolff") },
                              tuned=x.get("tuned", [np.nan])[0]))
if brows:
    with open(f"{R}/claimB_rows.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(brows[0].keys()))
        w.writeheader(); w.writerows(brows)
open(f"{R}/summary.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
