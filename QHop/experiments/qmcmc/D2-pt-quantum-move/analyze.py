"""Aggregate results/*.json -> summary CSVs, tables (summary.txt) and plots. Run: python analyze.py"""
import glob
import json
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json")))]
REGS = ["LOW", "MED", "HIGH"]
RS = [1e3, 1e6, 1e8]
lines = []


def P(*a):
    lines.append(" ".join(str(x) for x in a))


def tmax(d, flips=True):
    if flips:
        return max(d["tauE_flips"], d["tauQ_flips"])
    return np.nanmax([d["tauE"], d["tauQ"]])


def valid(x, key):
    """chain equilibrated: run-mean energy within 1% of the exact Boltzmann mean (trapped chains give fake small tau)."""
    return abs(x[key]["E_mean"] - x["E_exact"]) <= 0.01 * abs(x["E_exact"])


def best_classical(x):
    ks = [k for k in ("metro", "pt", "pt_houdayer") if k in x and valid(x, k)]
    return min(tmax(x[k]) for k in ks) if ks else tmax(x["pt"])


def mi(x):
    x = np.array([v for v in x if np.isfinite(v)])
    if len(x) == 0:
        return "nan"
    q1, m, q3 = np.percentile(x, [25, 50, 75])
    return f"{m:.3g} [{q1:.3g},{q3:.3g}]"


rows = []
groups = {}
for r in RES:
    groups.setdefault((r["family"], r["n"]), []).append(r)

P("D2 summary (own simulation, ideal/noiseless proposal). Medians over instances [IQR]. tau = integrated autocorrelation time")
P("(Sokal window, qmc.iat). Classical tau in single-spin-flip proposals (PT: tau_sweeps x n x R x copies [+ n R Houdayer]);")
P("quantum tau in quantum proposal steps. tau_max = max(tau_E, tau_q), q = overlap with ground state (|q| for EA).")
P("")
for (fam, n), rr in sorted(groups.items()):
    P(f"==== {fam.upper()} n={n}: {len(rr)} instances, seeds {[r['seed'] for r in rr]}")
    P("  beta_c (C peak): " + ", ".join(f"{r['beta_c']:.3f}" for r in rr))
    for reg in REGS:
        R = [r["regimes"].get(reg) for r in rr if reg in r["regimes"]]
        if not R:
            continue
        P(f"  -- {reg} (beta = {mi([x['beta'] for x in R])})")
        lad = R[0]["pt"]
        P(f"     PT ladder (seed {rr[0]['seed']}): betas {np.round(lad['betas'], 3).tolist()} swap {np.round(lad['swap'], 2).tolist()}")
        P(f"     PT replicas R: {mi([len(x['pt']['betas']) for x in R])}; all swap rates: min {min([min(x['pt']['swap'] or [np.nan]) for x in R]):.2f} max {max([max(x['pt']['swap'] or [np.nan]) for x in R]):.2f}")
        for key, lab in [("metro", "Metropolis"), ("pt", "PT"), ("pt_houdayer", "PT+Houdayer")]:
            if key in R[0]:
                P(f"     {lab:12s} tauE_flips {mi([x[key]['tauE_flips'] for x in R])}  tauQ_flips {mi([x[key]['tauQ_flips'] for x in R])}"
                  f"  equilibrated {sum(valid(x, key) for x in R)}/{len(R)}  t_eq_flips {mi([x[key]['t_eq_flips'] for x in R])}  N/tau_min {mi([x[key]['N'] / max(x[key]['tauE'], x[key]['tauQ']) for x in R])}")
        for key, lab in [("qemcmc", "QeMCMC"), ("decohered", "Decohered")]:
            if key in R[0]:
                extra = f"  t_eq_steps {mi([x[key]['t_eq_steps'] for x in R])}" if key == "qemcmc" else ""
                P(f"     {lab:12s} tauE_steps {mi([x[key]['tauE'] for x in R])}  tauQ_steps {mi([x[key]['tauQ'] for x in R])}"
                  f"  equilibrated {sum(valid(x, key) for x in R)}/{len(R)}  acc {mi([x[key]['acc'] for x in R])}  N {mi([x[key]['N'] for x in R])}{extra}")
        # step advantages
        if "qemcmc" in R[0]:
            best = [best_classical(x) for x in R]
            S_pt = [tmax(x["pt"]) / tmax(x["qemcmc"], False) for x in R]
            S_best = [b / tmax(x["qemcmc"], False) for b, x in zip(best, R)]
            S_loc = [tmax(x["metro"]) / tmax(x["qemcmc"], False) for x in R]
            S_dec = [tmax(x["pt"]) / tmax(x["decohered"], False) for x in R if "decohered" in x]
            P(f"     S vs PT (tau_PT flips / tau_Q steps) {mi(S_pt)} | vs best classical {mi(S_best)} | vs Metropolis {mi(S_loc)}"
              f" | decohered vs PT {mi(S_dec)}")
            for x, s1, s2, s3 in zip(R, S_pt, S_best, S_loc):
                rows.append(dict(family=fam, n=n, regime=reg, beta=x["beta"], S_vs_PT=s1, S_vs_best=s2, S_vs_metro=s3,
                                 S_dec_vs_PT=tmax(x["pt"]) / tmax(x["decohered"], False) if "decohered" in x else np.nan))
        # hybrids
        if R[0].get("hybrid"):
            keys = list(R[0]["hybrid"].keys())
            for kk in keys:
                rel = [tmax(x["hybrid"][kk], False) / tmax(x["pt"], False) for x in R if kk in x["hybrid"]]
                Ns = [x["hybrid"][kk]["N"] for x in R if kk in x["hybrid"]]
                P(f"     PT+{kk:5s} tau_sweeps/tau_PT {mi(rel)}  qacc {mi([x['hybrid'][kk]['q_acc'] for x in R if kk in x['hybrid']])}"
                  f"  N_sweeps {mi(Ns)}")
            for kind in ["Q", "D"]:
                for Rc in RS:
                    bestpq, ratio = [], []
                    for x in R:
                        c0 = tmax(x["pt"], False) * x["pt"]["cost_per_sweep"]
                        cands = {0.0: c0}
                        for kk, h in x["hybrid"].items():
                            if kk.startswith(kind):
                                cands[h["p_q"]] = tmax(h, False) * (h["cost_classical_per_sweep"] + h["qmoves_per_sweep"] * Rc)
                        pq = min(cands, key=cands.get)
                        bestpq.append(pq)
                        ratio.append(cands[pq] / c0)
                    vals, cnt = np.unique(bestpq, return_counts=True)
                    P(f"     best p_q ({kind}) at R={Rc:.0e}: " + ", ".join(f"{v:g}x{c}" for v, c in zip(vals, cnt))
                      + f"  cost(best)/cost(PT) {mi(ratio)}")
            # break-even R* for each hybrid (max R at which it beats plain PT)
            for kk in keys:
                rs = []
                for x in R:
                    h = x["hybrid"].get(kk)
                    if h is None:
                        continue
                    t0, t1 = tmax(x["pt"], False), tmax(h, False)
                    cps = x["pt"]["cost_per_sweep"]
                    rs.append((t0 - t1) * cps / (t1 * h["qmoves_per_sweep"]) if t1 < t0 and h["qmoves_per_sweep"] > 0 else 0.0)
                P(f"     break-even R* PT+{kk}: {mi(rs)} flips")
    P("")

# wall-clock check: any quantum sampler cheaper than best classical at R >= 1e6 ?
P("==== Wall-clock check (cost in single-flip equivalents, quantum move = R flips)")
for Rc in RS:
    wins = []
    for r in RES:
        for reg, x in r["regimes"].items():
            if "qemcmc" not in x:
                continue
            best = best_classical(x)
            cq = tmax(x["qemcmc"], False) * Rc
            if cq < best:
                wins.append((r["family"], r["n"], r["seed"], reg, "pure"))
            for kk, h in x.get("hybrid", {}).items():
                if kk.startswith("Q") and tmax(h, False) * (h["cost_classical_per_sweep"] + h["qmoves_per_sweep"] * Rc) < best:
                    wins.append((r["family"], r["n"], r["seed"], reg, kk))
    P(f"  R={Rc:.0e}: {len(wins)} (instance,regime,sampler) wins over best classical: {wins[:10]}")
open(os.path.join(HERE, "summary.txt"), "w").write("\n".join(lines) + "\n")

import csv

if rows:
    with open(os.path.join(HERE, "step_advantage.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
# flat per-run CSV
flat = []
for r in RES:
    for reg, x in r["regimes"].items():
        for key in ("metro", "pt", "pt_houdayer", "qemcmc", "decohered"):
            if key in x:
                d = x[key]
                flat.append([r["family"], r["n"], r["seed"], reg, x["beta"], key, d["tauE"], d["tauQ"], d.get("tauE_flips", ""),
                             d.get("tauQ_flips", ""), d["N"], d.get("t_eq_flips", d.get("t_eq_steps", "")),
                             len(d.get("betas", [])) or "", ";".join(f"{v:.3f}" for v in d.get("swap", []))])
        for kk, h in x.get("hybrid", {}).items():
            flat.append([r["family"], r["n"], r["seed"], reg, x["beta"], "PT+" + kk, h["tauE"], h["tauQ"], "", "", h["N"], "",
                         len(x["pt"]["betas"]), f"qps={h['qmoves_per_sweep']:.4f};qacc={h['q_acc']:.3f};cps={h['cost_classical_per_sweep']}"])
with open(os.path.join(HERE, "all_runs.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["family", "n", "seed", "regime", "beta", "sampler", "tauE_native", "tauQ_native", "tauE_flips", "tauQ_flips",
                "N_native", "t_eq", "R_replicas", "swap_or_hybrid_info"])
    w.writerows(flat)

# plots
if rows:
    fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, reg in zip(axs, REGS):
        for fam, mk in [("sk", "o"), ("ea", "s")]:
            for key, col, lab in [("S_vs_PT", "C0", "QeMCMC vs PT"), ("S_dec_vs_PT", "C3", "decohered vs PT"),
                                  ("S_vs_metro", "C2", "QeMCMC vs Metropolis")]:
                ns = sorted({x["n"] for x in rows if x["family"] == fam and x["regime"] == reg})
                med, lo, hi = [], [], []
                for nn in ns:
                    v = [x[key] for x in rows if x["family"] == fam and x["regime"] == reg and x["n"] == nn and np.isfinite(x[key])]
                    q1, m, q3 = np.percentile(v, [25, 50, 75])
                    med.append(m), lo.append(m - q1), hi.append(q3 - m)
                if ns:
                    ax.errorbar(np.array(ns) + (0.15 if fam == "ea" else 0), med, yerr=[lo, hi], marker=mk, color=col,
                                ls="-" if fam == "sk" else "none", label=f"{fam.upper()} {lab}", capsize=3)
        for Rc in RS:
            ax.axhline(Rc, color="k", ls=":", lw=0.8)
            ax.text(12, Rc * 1.3, f"R={Rc:.0e}", fontsize=7)
        ax.set_yscale("log")
        ax.set_title(f"{reg}")
        ax.set_xlabel("n spins")
    axs[0].set_ylabel("S = tau_classical [flips] / tau_quantum [steps]\n(= break-even cost R of one quantum step)")
    axs[0].legend(fontsize=6)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "fig_step_advantage_vs_PT.png"), dpi=140)

    # hybrid tau ratio vs p_q
    fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, reg in zip(axs, REGS):
        for (fam, n), rr in sorted(groups.items()):
            R = [r["regimes"][reg] for r in rr if reg in r["regimes"] and r["regimes"][reg].get("hybrid")]
            if not R:
                continue
            for kind, ls in [("Q", "-"), ("D", "--")]:
                pqs = sorted({h["p_q"] for x in R for kk, h in x["hybrid"].items() if kk.startswith(kind)})
                med = [np.median([tmax(x["hybrid"][f"{kind}{p}"], False) / tmax(x["pt"], False) for x in R
                                  if f"{kind}{p}" in x["hybrid"]]) for p in pqs]
                ax.plot(pqs, med, ls, marker="o", label=f"{fam.upper()}{n} {kind}")
        ax.set_xscale("log")
        ax.axhline(1, color="k", lw=0.8)
        ax.set_title(reg)
        ax.set_xlabel("p_q (quantum/decohered moves per cold replica per sweep)")
    axs[0].set_ylabel("tau_sweeps(PT + move) / tau_sweeps(PT)")
    axs[0].legend(fontsize=6, ncol=2)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "fig_hybrid_tau_vs_pq.png"), dpi=140)

    # tau per sampler vs n, native units
    fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, reg in zip(axs, REGS):
        for key, col, lab in [("metro", "C2", "Metropolis [flips]"), ("pt", "C0", "PT [flips]"),
                              ("pt_houdayer", "C4", "PT+Houdayer [flips]"), ("qemcmc", "C1", "QeMCMC [steps]"),
                              ("decohered", "C3", "decohered [steps]")]:
            for fam, mk in [("sk", "o"), ("ea", "s")]:
                pts = [(n, np.median([tmax(r["regimes"][reg][key], key not in ("qemcmc", "decohered")) for r in rr]))
                       for (f, n), rr in sorted(groups.items()) if f == fam and reg in rr[0]["regimes"]
                       and key in rr[0]["regimes"][reg]]
                if pts:
                    ax.plot(*zip(*pts), marker=mk, color=col, ls="-" if fam == "sk" else "none", label=f"{fam.upper()} {lab}")
        ax.set_yscale("log")
        ax.set_title(reg)
        ax.set_xlabel("n spins")
    axs[0].set_ylabel("median tau_max")
    axs[0].legend(fontsize=6)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "fig_tau_vs_n.png"), dpi=140)
print("\n".join(lines))
