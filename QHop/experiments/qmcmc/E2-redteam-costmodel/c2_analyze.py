"""E2 claim 2 analysis: S_real(K) = gap(q_sur) / gap(best REALISTIC classical surrogate sampler with inner budget K).
Set A = local, uniform, local+uniform, same-beta DA (inner local/mix, K'<=K), tempered DA (beta'=f beta, inner local/mix,
K'<=K) and its 50/50 mix with local.  Set B = same without any uniform proposal (inner local only) - the large-n-honest set.
D5 reference: S_free (includes exact DA K=inf and K up to 1e6) and S_ext from D5 tempered csv (exact pi_sur(beta') draw).
Writes results/c2_S_table.csv and results/c2_summary.txt."""
import csv, glob, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D5R = "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D5-surrogate/results"
KS = [1, 10, 100, 1000]
ext = {}
for f in glob.glob(os.path.join(D5R, "tempered_n*.csv")):
    for r in csv.DictReader(open(f)):
        ext[(int(r["n"]), int(r["inst"]), r["fam"], round(float(r["rho"]), 3), r["regime"])] = max(
            float(r["gap_TDA_best"]), float(r["gap_mix_TDA_local"]))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "results", "c2_finiteK_n*.jsonl"))):
    for l in open(f):
        r = json.loads(l)
        q = r["gap_q_sur"]
        da, td = r["DA_same"], r["TDA"]
        free = max([r["gap_local"], r["gap_uniform"], r["gap_mix_lu"], r["gap_DA_inf"]] + list(da.values()))
        row = dict(n=r["n"], inst=r["inst"], fam=r["fam"], rho=r["rho"], regime=r["regime"], beta_sigma=r["beta_sigma"],
                   gap_q_sur=q, S_free_D5=q / free)
        key = (r["n"], r["inst"], r["fam"], round(r["rho"], 3), r["regime"])
        row["S_ext_D5"] = q / max(free, ext[key]) if key in ext else np.nan
        for K in KS:
            A = [r["gap_local"], r["gap_uniform"], r["gap_mix_lu"]]
            B = [r["gap_local"]]
            for k, v in da.items():
                nm, KK = k.rsplit("_", 1)
                if int(KK) <= K:
                    A.append(v)
                    if nm == "DA_local":
                        B.append(v)
            for k, v in td.items():
                inner, ff, KK = k.split("_")
                if ff == "fbest" or int(KK) > K:
                    continue
                A.append(v)
                if inner == "local":
                    B.append(v)
            row[f"S_A_K{K}"] = q / max(A)
            row[f"S_B_K{K}"] = q / max(B)
        rows.append(row)
with open(os.path.join(HERE, "results", "c2_S_table.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
cols = ["S_free_D5", "S_ext_D5"] + [f"S_A_K{K}" for K in KS] + [f"S_B_K{K}" for K in KS]
groups = {}
for r in rows:
    groups.setdefault((r["n"], r["fam"], r["rho"], r["regime"]), []).append(r)
lines = ["n fam rho regime N beta*sig | " + " ".join(f"{c:>9s}" for c in cols)]
for k in sorted(groups):
    g = groups[k]
    lines.append(f"{k[0]:2d} {k[1]} {k[2]:.1f} {k[3]:6s} {len(g)} {np.median([x['beta_sigma'] for x in g]):5.2f} | " +
                 " ".join(f"{np.nanmedian([x[c] for x in g]):9.3f}" for c in cols))
lines.append("")
for c in cols:
    v = np.array([r[c] for r in rows])
    low = np.array([r[c] for r in rows if r["regime"] == "LOW"])
    lines.append(f"{c:10s}: cells(instance-level) with S>1: all {np.sum(v > 1)}/{len(v)}, LOW {np.sum(low > 1)}/{len(low)};"
                 f" max {np.nanmax(v):.2f}")
open(os.path.join(HERE, "results", "c2_summary.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
# K* (set B, local-only inner chain): smallest K in KS with S_B <= 1, per n and regime
lines2 = ["", "K*_B = smallest inner local-Metropolis budget K (surrogate steps per true call) at which realistic classical"
          " matches q_sur (S_B<=1); counts per n/regime over instance-level cells:"]
for nn in sorted({r["n"] for r in rows}):
    for reg in ("MEDIUM", "LOW"):
        sub = [r for r in rows if r["n"] == nn and r["regime"] == reg]
        ks = []
        for r in sub:
            k = next((K for K in KS if r[f"S_B_K{K}"] <= 1.0), ">1000")
            ks.append(str(k))
        lines2.append(f"n={nn} {reg:6s} N={len(sub)}: " + ", ".join(f"K*={k}: {ks.count(k)}" for k in
                                                                      ["1", "10", "100", "1000", ">1000"]))
open(os.path.join(HERE, "results", "c2_summary.txt"), "a").write("\n".join(lines2) + "\n")
print("\n".join(lines2))
