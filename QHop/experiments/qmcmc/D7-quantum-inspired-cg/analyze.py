"""Aggregate results/runs/*.json -> results/summary_runs.csv, results/table_medians.csv, results/verdict.csv, plots."""
import csv, glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
runs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(HERE, "results", "runs", "*.json")))]


def cfg(r):
    return f"{r['method']}" + (f"_k{r['k']}_{r['group']}" if r["method"] in ("hb", "q", "dec") else "")


# reference mean energy per (inst,target): best available classical run (pth > pt > metro)
eref = {}
for pref in ["metro", "pt", "pth"]:
    for r in runs:
        if r["method"] == pref and (r["target"] != "HIGH" or pref == "metro"):
            eref[(r["inst"], r["target"])] = r["Emean2"]

rows = []
for r in runs:
    N = r["nrec"]; b = N // 4
    lbE = (N - b) / 50.0
    tE = r["tauE_rec"] if r["tauE_rec"] == r["tauE_rec"] else lbE
    tH = r["tauH_rec"] if r["tauH_rec"] == r["tauH_rec"] else lbE
    tE_eff = tE
    tH_eff = tH
    tr = r["trace"]; Er = eref.get((r["inst"], r["target"]))
    teq = np.nan
    if Er is not None:
        hit = np.nonzero(np.array(tr["E"]) <= Er)[0]
        if len(hit):
            teq = tr["T"][hit[0]]
    spins_per_rec = {"metro": r["n"], "pt": r["n"] * r.get("R", 1), "pth": 2 * r["n"] * r.get("R", 1)}.get(
        r["method"], r["moves_per_rec"] * r["k"])
    rows.append(dict(inst=r["inst"], family=r["family"], size=r["size"], n=r["n"], seed=r["seed"], target=r["target"],
                     beta=r["beta"], config=cfg(r), method=r["method"], k=r["k"], group=r["group"],
                     us_per_move=r["us_per_move"], acc=r.get("acc", np.nan), R=r.get("R", 1),
                     minswap=min(r["swap"]) if r.get("swap") else np.nan,
                     tauE_moves=tE_eff * r["moves_per_rec"], tauH_moves=tH_eff * r["moves_per_rec"],
                     tauE_spinupd_per_n=tE_eff * spins_per_rec / r["n"],
                     tauE_sec=tE_eff * r["sec_per_rec"], tauH_sec=tH_eff * r["sec_per_rec"],
                     resE=int(r["resolvedE"] and N - b >= 1000), resH=int(r["resolvedH"] and N - b >= 1000), teq_sec=teq, cpu=r["cpu"], nrec=N))
keys = list(rows[0].keys())
with open(os.path.join(HERE, "results", "summary_runs.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow(x) for x in rows]


def med_iqr(v):
    v = np.asarray([x for x in v if x == x], float)
    if not len(v):
        return np.nan, np.nan, np.nan
    return np.median(v), np.percentile(v, 25), np.percentile(v, 75)


groups = {}
for x in rows:
    groups.setdefault((x["family"], x["size"], x["target"], x["config"]), []).append(x)
tab = []
for (fam, size, tgt, c), xs in sorted(groups.items()):
    d = dict(family=fam, size=size, target=tgt, config=c, nseeds=len(xs))
    for kk in ["us_per_move", "tauE_moves", "tauE_spinupd_per_n", "tauE_sec", "tauH_moves", "tauH_sec", "teq_sec"]:
        m, lo, hi = med_iqr([x[kk] for x in xs]); d[kk] = m; d[kk + "_q25"] = lo; d[kk + "_q75"] = hi
    d["fracResE"] = np.mean([x["resE"] for x in xs]); d["fracResH"] = np.mean([x["resH"] for x in xs])
    d["fracEq"] = np.mean([x["teq_sec"] == x["teq_sec"] for x in xs])
    tab.append(d)
with open(os.path.join(HERE, "results", "table_medians.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(tab[0].keys())); w.writeheader(); [w.writerow(x) for x in tab]

# verdict per instance/target: best q config vs (a) hb same k/group (per move and per sec) (b) best of metro/pt/pth
ver = []
byit = {}
for x in rows:
    byit.setdefault((x["inst"], x["target"]), []).append(x)
for (inst, tgt), xs in sorted(byit.items()):
    cl = [x for x in xs if x["method"] in ("metro", "pt", "pth")]
    hb = {(x["k"], x["group"]): x for x in xs if x["method"] == "hb"}
    best_cl = {o: min(cl, key=lambda x: x[f"tau{o}_sec"]) for o in "EH"}
    best_hb = {o: min(hb.values(), key=lambda x: x[f"tau{o}_sec"]) for o in "EH"}
    for x in xs:
        if x["method"] not in ("q", "dec"):
            continue
        h = hb[(x["k"], x["group"])]
        d = dict(inst=inst, family=x["family"], size=x["size"], target=tgt, config=x["config"])
        for o in "EH":
            d[f"{o}_perstep_hb_over_q"] = h[f"tau{o}_moves"] / x[f"tau{o}_moves"]
            d[f"{o}_persec_hb_over_q"] = h[f"tau{o}_sec"] / x[f"tau{o}_sec"]
            d[f"{o}_persec_bestclassical_over_q"] = best_cl[o][f"tau{o}_sec"] / x[f"tau{o}_sec"]
            d[f"{o}_bestclassical"] = best_cl[o]["config"]
            d[f"{o}_persec_besthb_over_q"] = best_hb[o][f"tau{o}_sec"] / x[f"tau{o}_sec"]
            d[f"{o}_q_resolved"] = x[f"res{o}"]
        ver.append(d)
with open(os.path.join(HERE, "results", "verdict.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ver[0].keys())); w.writeheader(); [w.writerow(x) for x in ver]

# compact verdict medians
vg = {}
for d in ver:
    vg.setdefault((d["family"], d["size"], d["target"], d["config"]), []).append(d)
lines = ["family size target config | perstep hb/q (E,H) | persec hb/q (E,H) | persec bestclassical/q (E,H) | q resolved E"]
for key, ds in sorted(vg.items()):
    f = lambda kk: np.median([d[kk] for d in ds])
    lines.append("%s %d %s %s | %.3g %.3g | %.3g %.3g | %.3g %.3g | %.1f" % (
        *key, f("E_perstep_hb_over_q"), f("H_perstep_hb_over_q"), f("E_persec_hb_over_q"), f("H_persec_hb_over_q"),
        f("E_persec_bestclassical_over_q"), f("H_persec_bestclassical_over_q"), np.mean([d["E_q_resolved"] for d in ds])))
open(os.path.join(HERE, "results", "verdict_medians.txt"), "w").write("\n".join(lines) + "\n")
mx = {o: max(max(d[f"{o}_persec_hb_over_q"], d[f"{o}_persec_bestclassical_over_q"]) for d in ver if d["config"].startswith("q")) for o in "EH"}
mxs = {o: max(d[f"{o}_perstep_hb_over_q"] for d in ver if d["config"].startswith("q")) for o in "EH"}
print("max over all instances of (classical tau_sec / q tau_sec):", mx, " max per-step hb/q:", mxs)

# ---------------- plots
os.makedirs(os.path.join(HERE, "plots"), exist_ok=True)
tim = json.load(open(os.path.join(HERE, "results", "timing.json")))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for i, fam in enumerate(["sk", "ea"]):
    for m, mk in [("hb", "o-"), ("q", "s-"), ("dec", "^-")]:
        for inst in sorted({r["inst"] for r in tim["rows"] if r["inst"].startswith(fam)}):
            xs = [r for r in tim["rows"] if r["inst"] == inst and r["move"] == m]
            ax[i].plot([r["k"] for r in xs], [r["us_per_move"] for r in xs], mk, label=f"{m} {inst.split('_')[0]}")
    for r in tim["rows"]:
        if r["inst"].startswith(fam) and r["move"] == "metro_sweep":
            ax[i].axhline(r["us_per_move"], ls=":", c="gray")
    ax[i].set_yscale("log"); ax[i].set_xlabel("group size k"); ax[i].set_ylabel("CPU us per move")
    ax[i].set_title(f"{fam.upper()}: CPU time per move (dotted = 1 Metropolis sweep)"); ax[i].legend(fontsize=6, ncol=2)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "plots", "cpu_per_move.png"), dpi=130); plt.close()

for o in "EH":
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    for i, fam in enumerate(["sk", "ea"]):
        for j, tgt in enumerate(["HIGH", "MEDIUM", "LOW"]):
            a = axs[i, j]
            T = [t for t in tab if t["family"] == fam and t["target"] == tgt]
            cfgs = sorted({t["config"] for t in T}, key=lambda c: (c.split("_")[0], c))
            sizes = sorted({t["size"] for t in T})
            for si, s in enumerate(sizes):
                vals = [next((t[f"tau{o}_sec"] for t in T if t["size"] == s and t["config"] == c), np.nan) for c in cfgs]
                a.plot(range(len(cfgs)), vals, "o", label=f"size {s}", alpha=0.8)
            a.set_xticks(range(len(cfgs))); a.set_xticklabels(cfgs, rotation=90, fontsize=6)
            a.set_yscale("log"); a.set_ylabel(f"IAT({o}) in CPU seconds (median)")
            a.set_title(f"{fam.upper()} {tgt}"); a.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "plots", f"iat{o}_per_cpu_second.png"), dpi=120); plt.close()

eb = json.load(open(os.path.join(HERE, "results", "exact_bound_n10.json")))
fig, ax = plt.subplots(figsize=(6, 4))
for k, mk in [(4, "o"), (6, "s")]:
    xs = [e for e in eb if e["k"] == k]
    ax.plot([e["beta_over_betac"] for e in xs], [e["gap_ratio_q_hb"] for e in xs], mk, label=f"quantum/HB k={k}")
    ax.plot([e["beta_over_betac"] for e in xs], [e["gap_ratio_dec_hb"] for e in xs], mk, mfc="none",
            label=f"decohered/HB k={k}")
ax.axhline(2, c="r", ls="--", label="proved upper bound 2"); ax.axhline(1, c="gray", ls=":")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("beta / beta_c"); ax.set_ylabel("spectral gap ratio vs block heat-bath")
ax.set_title("SK n=10 exact, same groups (random consecutive block)"); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "plots", "exact_gap_ratio_vs_hb.png"), dpi=130); plt.close()
print("wrote tables and plots")
