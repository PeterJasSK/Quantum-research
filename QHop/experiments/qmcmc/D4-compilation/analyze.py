"""Combine Trotter-r, per-layer compile costs, device error/timing models -> results/costs.csv, results/fits.csv,
results/thresholds.csv, results/native_subset_summary.txt, plots/*.png.  Pure post-processing (no transpiles)."""
import collections
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import d4lib as D

TS = (2.0, 6.0, 12.0, 20.0)

# ---- device models (label: source) ------------------------------------------------------------------------------
DEV = {
    "HeronR2": dict(topo="heavyhex", e2=2.0e-3, e1=2.3e-4, ro=1.67e-2, mem=0.0, src="A4: 2q 2.03e-3 dashboard reprint, ro 1.666e-2; 1q = FakeMarrakesh sx median"),
    "HeronR3": dict(topo="heavyhex", e2=2.15e-3, e1=1.4e-4, ro=1.67e-2, mem=0.0, src="A4: EPLG(100q) ibm_boston 2.15e-3 used as per-gate error (pessimistic); ro not found -> r2 value; 1q FakeBoston"),
    "HeronR3_fakecal": dict(topo="heavyhex", e2=1.27e-3, e1=1.4e-4, ro=5.13e-3, mem=0.0, src="FakeBoston calibration medians (optimistic alt)"),
    "Nighthawk": dict(topo="square", e2=2.0e-3, e1=1.5e-4, ro=1.67e-2, mem=0.0, src="A4: 'Heron-class' 2q -> 2e-3; ro not found -> Heron r2 value; 1q FakeNighthawk"),
    "Helios": dict(topo="alltoall_native", e2=8.0e-4, e1=3.0e-5, ro=5.0e-4, mem=6.0e-4, src="A4 datasheet: 2q 8e-4, 1q 3e-5, SPAM 5e-4, memory 6e-4 per qubit per depth-1 layer"),
}
HELIOS_LAYER_S = 0.055          # A4: 55 ms per depth-1 layer (measured at ~98 q; assumed for all n)
IBM_REP = 250e-6                # A4: rep_delay 250 us, ~4,000 circuits/s
NH_FLOOR = 1e-5                 # A4: Nighthawk r2 >100,000 circuits/s
LAT = {"opt": 2.0, "real": 3.0}  # A4/BRIEF: IBM ~2 s per sub-job best, ~3 s per step realistic (Marshall 2026 derived)
BATCH = {"HeronR2": 1e4, "HeronR3": 1e4, "HeronR3_fakecal": 1e4, "Nighthawk": 1e5}

FAM_SIZES = {"SK": [6, 8, 10, 12, 16, 20, 27], "EA": [9, 16, 25, 36], "HH": [12, 27, 60, 100],
             "CG": list(range(4, 13)), "COUL": [8, 10, 12, 14, 16], "POTTS3": [27], "POTTS4": [36]}
STRUCT = {"SK": "DENSE", "CG": "DENSE", "COUL": "DENSE", "EA": "EA", "HH": "HH", "POTTS3": "POTTS3", "POTTS4": "POTTS4"}


def load_r():
    R = collections.defaultdict(list)
    for f in ("results/trotter_r_ising.jsonl", "results/trotter_r_potts.jsonl"):
        for l in open(f):
            d = json.loads(l)
            R[(d["family"], d["n"], d["t"])].append(d["r_max"])
    Rm = {k: max(v) for k, v in R.items()}
    # POTTS4 3x3 run was killed (machine overload) before gamma=0.6 at t=12,20: take max with the full 2x3 q=4 result
    for t in (12.0, 20.0):
        Rm[("POTTS4", 36, t)] = max(Rm[("POTTS4", 36, t)], Rm[("POTTS4", 24, t)])
    fits = {}
    for fam in {k[0] for k in Rm}:
        ks = [k for k in Rm if k[0] == fam]
        X = np.array([[1, np.log(k[2]), np.log(k[1])] for k in ks])
        y = np.log([Rm[k] for k in ks])
        c, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ c
        fits[fam] = (c, float(res.max()))
    return Rm, fits


def r_for(Rm, fits, fam, n, t):
    if (fam, n, t) in Rm:
        return Rm[(fam, n, t)], "measured"
    c, rmax = fits[fam]
    return int(np.ceil(np.exp(c[0] + c[1] * np.log(t) + c[2] * np.log(n) + rmax))), "extrapolated(fit+max residual)"


def load_layers():
    L = {}
    for l in open("results/compile_layers.jsonl"):
        d = json.loads(l)
        L[(d["struct"], d["n"], d["topo"], d["variant"], d["r"])] = d
    return L


def lin(L, key, r, field):
    a3, a5 = L[key + (3,)], L[key + (5,)]
    if a3.get(field) is None:
        return None
    return a3[field] + (r - 3) * (a5[field] - a3[field]) / 2


def cost(L, struct, n, topo, r):
    """Best variant cost at r Trotter steps on a topology."""
    if topo == "alltoall_native":
        a3, a5 = L[(struct, n, topo, "analytic", 3)], L[(struct, n, topo, "analytic", 5)]
        return dict(variant="analytic", n2q=a3["n2q"] + (r - 3) * (a5["n2q"] - a3["n2q"]) / 2,
                    depth2q=a3["depth2q"] + (r - 3) * (a5["depth2q"] - a3["depth2q"]) / 2, n1q=None, duration_s=None,
                    qubits_used=n)
    out = []
    for v in ("sabre", "swapnet", "nomap"):
        k = (struct, n, topo, v)
        if k + (3,) in L:
            out.append(dict(variant=v, **{f: lin(L, k, r, f) for f in ("n2q", "depth2q", "n1q", "duration_s")},
                            qubits_used=L[k + (5,)]["qubits_used"]))
    return min(out, key=lambda x: x["n2q"])


def fidelity(dev, c, nmeas):
    m = DEV[dev]
    n1 = c["n1q"] if c["n1q"] is not None else 2 * nmeas * c["depth2q"] / max(1, nmeas - 1)
    lf = c["n2q"] * np.log1p(-m["e2"]) + n1 * np.log1p(-m["e1"]) + nmeas * np.log1p(-m["ro"])
    if m["mem"]:
        lf += nmeas * c["depth2q"] * np.log1p(-m["mem"])
    return float(np.exp(lf))


def timing(dev, c, nmeas):
    if dev == "Helios":
        ts = c["depth2q"] * HELIOS_LAYER_S
        pack = max(1, 98 // nmeas)
        return dict(t_shot=ts, tQ_opt=ts, tQ_real=ts, tQ_batch=ts / pack, batch_note=f"{pack} chains packed per circuit")
    ts = c["duration_s"] + (IBM_REP if dev != "Nighthawk" else 1e-6)
    ts_eff = max(ts, NH_FLOOR) if dev == "Nighthawk" else max(ts, 3.5e-4)
    B = BATCH[dev]
    return dict(t_shot=ts, tQ_opt=LAT["opt"] + ts, tQ_real=LAT["real"] + ts, tQ_batch=ts_eff + LAT["opt"] / B,
                batch_note=f"B={int(B)} executions per job")


def main():
    Rm, rfits = load_r()
    L = load_layers()
    rows = []
    for fam, sizes in FAM_SIZES.items():
        for n in sizes:
            nmeas = n
            for t in TS:
                r, rsrc = r_for(Rm, rfits, fam, n if not fam.startswith("POTTS") else n, t)
                ref = cost(L, STRUCT[fam], n, "alltoall_cz", r)
                for dev in DEV:
                    c = cost(L, STRUCT[fam], n, DEV[dev]["topo"], r)
                    tm = timing(dev, c, nmeas)
                    rows.append(dict(family=fam, n=n, t=t, r=r, r_source=rsrc, device=dev, topo=DEV[dev]["topo"],
                                     variant=c["variant"], N2q=round(c["n2q"]), depth2q=round(c["depth2q"]),
                                     qubits_used=c["qubits_used"], N2q_alltoall_cz=round(ref["n2q"]),
                                     swap_overhead=round(c["n2q"] / ref["n2q"], 3) if DEV[dev]["topo"] != "alltoall_native" else None,
                                     F=fidelity(dev, c, nmeas), **tm))
    keys = list(rows[0].keys())
    with open("results/costs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, keys)
        w.writeheader()
        w.writerows(rows)

    # ---- power-law fits N2q = A n^b per family x device x t; thresholds
    fits, thr = [], []
    for fam in FAM_SIZES:
        for dev in DEV:
            for t in TS:
                sub = [x for x in rows if x["family"] == fam and x["device"] == dev and x["t"] == t]
                ns = np.array([x["n"] for x in sub], float)
                if len(ns) >= 2:
                    b, lA = np.polyfit(np.log(ns), np.log([x["N2q"] for x in sub]), 1)
                    fits.append(dict(family=fam, device=dev, t=t, A=float(np.exp(lA)), b=float(b), sizes=len(ns)))
                    lF = np.polyfit(ns, np.log([x["F"] for x in sub]), 2 if len(ns) >= 3 else 1)
                else:
                    lF = None
                for th in (0.5, 0.1):
                    ok = [x["n"] for x in sub if x["F"] >= th]
                    meas = max(ok) if ok else None
                    ext = None
                    if lF is not None:
                        grid = np.arange(2, 400)
                        okg = grid[np.polyval(lF, grid) >= np.log(th)]
                        okg = okg[okg <= (156 if DEV[dev]["topo"] == "heavyhex" else 120 if DEV[dev]["topo"] == "square" else 98)]
                        ext = int(okg.max()) if len(okg) else None
                    thr.append(dict(family=fam, device=dev, t=t, F_thr=th, largest_n_measured=meas,
                                    smallest_measured=int(min(ns)), largest_n_fit=ext))
    for name, data in (("fits", fits), ("thresholds", thr)):
        with open(f"results/{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
    with open("results/trotter_r_fit.json", "w") as fh:
        json.dump({k: dict(logc=v[0][0], t_exp=v[0][1], n_exp=v[0][2], max_resid=v[1]) for k, v in rfits.items()}, fh, indent=1)

    # ---- plots
    for qty, fn, ylab in (("N2q", "plots/N2q_vs_n.png", "two-qubit gates N_2q (one proposal)"),
                          ("F", "plots/F_vs_n.png", "pessimistic circuit fidelity F")):
        fig, axs = plt.subplots(2, 3, figsize=(15, 9))
        for ax, fam in zip(axs.flat, ["SK", "CG", "COUL", "EA", "HH", "POTTS3"]):
            for dev, mk in (("HeronR2", "o-"), ("HeronR3", "s--"), ("Nighthawk", "^-"), ("Helios", "d-")):
                for t, col in ((6.0, "C0"), (20.0, "C3")):
                    sub = [x for x in rows if x["family"] == fam and x["device"] == dev and x["t"] == t]
                    if fam == "POTTS3":
                        sub += [x for x in rows if x["family"] == "POTTS4" and x["device"] == dev and x["t"] == t]
                    if qty == "N2q" and dev == "HeronR3":
                        continue
                    ax.plot([x["n"] for x in sub], [x[qty] for x in sub], mk, color=col, label=f"{dev} t={t:g}", ms=4)
            if qty == "F":
                for th in (0.5, 0.1):
                    ax.axhline(th, color="gray", lw=0.6)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(fam if fam != "POTTS3" else "POTTS q=3 (27q), q=4 (36q)")
            ax.set_xlabel("logical spins / qubits n")
            ax.set_ylabel(ylab)
            if qty == "F":
                ax.set_ylim(1e-12, 1.2)
        axs.flat[0].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(fn, dpi=110)
        plt.close(fig)

    # ---- r vs t plot
    fig, ax = plt.subplots(figsize=(7, 5))
    for i, fam in enumerate(sorted({k[0] for k in Rm})):
        ns = sorted({k[1] for k in Rm if k[0] == fam})
        nb = ns[-1]
        ax.plot(TS, [Rm[(fam, nb, t)] for t in TS], "o-", color=f"C{i}", label=f"{fam} n={nb}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("evolution time t")
    ax.set_ylabel("min Trotter steps r (max-row TVD <= 0.05, worst gamma, worst seed)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("plots/r_vs_t.png", dpi=110)

    # ---- native subset
    try:
        recs = [json.loads(l) for l in open("results/native_subset.jsonl")]
    except FileNotFoundError:
        recs = []
    lines = []
    for n in sorted({r["n"] for r in recs}):
        S = [r for r in recs if r["n"] == n]
        lines.append(f"SK n={n}: {len(S)} instances, kept edges {S[0]['kept_edges']}/{S[0]['total_edges']}, "
                     f"kept J^2 fraction median {np.median([r['kept_J2_frac'] for r in S]):.2f}, max asymmetry native Q {max(r['asym_native'] for r in S):.1e}")
        for b in (0.1, 0.3, 1.0):
            def med(k):
                v = [r[f"gap_{k}_b{b}"] for r in S]
                return np.median(v), np.percentile(v, 25), np.percentile(v, 75)
            rat = [r[f"gap_native_b{b}"] / r[f"gap_full_b{b}"] for r in S]
            best_c = [max(r[f"gap_local_b{b}"], r[f"gap_uniform_b{b}"]) for r in S]
            rn = [r[f"gap_native_b{b}"] / c for r, c in zip(S, best_c)]
            rf = [r[f"gap_full_b{b}"] / c for r, c in zip(S, best_c)]
            rd = [r[f"gap_native_decohered_b{b}"] / c for r, c in zip(S, best_c)]
            lines.append(f"  beta={b}: gap native/full median {np.median(rat):.2f} IQR [{np.percentile(rat,25):.2f},{np.percentile(rat,75):.2f}] | "
                         f"full/best(local,uniform) {np.median(rf):.2f} | native/best {np.median(rn):.2f} IQR [{np.percentile(rn,25):.2f},{np.percentile(rn,75):.2f}] | "
                         f"native-decohered/best {np.median(rd):.2f}")
    # gate counts per D-layer, heavy-hex
    for n in (8, 10, 12, 16, 20, 27):
        c3 = cost(L, "DENSE", n, "heavyhex", 3)["n2q"] - cost(L, "DENSE", n, "heavyhex", 2)["n2q"]
        dense_layer = (cost(L, "DENSE", n, "heavyhex", 5)["n2q"] - cost(L, "DENSE", n, "heavyhex", 3)["n2q"]) / 2
        _, E = D.hh_subgraph(n)
        lines.append(f"heavy-hex per diagonal layer n={n}: dense best {dense_layer:.0f} CZ vs native subset {len(E)} edges -> ~{2*len(E)} CZ "
                     f"(x{dense_layer/(2*len(E)):.1f} fewer; native subset has {len(E)}/{n*(n-1)//2} couplings)")
    open("results/native_subset_summary.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
