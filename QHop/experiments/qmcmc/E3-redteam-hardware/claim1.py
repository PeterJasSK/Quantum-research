"""Claim 1 (D3) attack. Uses D3 cached exact Q matrices (D3-noise/cache) and D3 instance/regime definitions.
(a) eps_half predicted from circuit fidelity alone; (b) S vs stronger classical (tuned mixture, block heat-bath);
(c) deep-circuit T1/readout tilt bias. -> results/claim1.json, stdout log."""
import itertools
import json

import numpy as np
from scipy.optimize import brentq

import e3lib as L
qmc = L.qmc
D3 = "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D3-noise/"
inst = json.load(open(D3 + "results/instances.json"))
out = {"a_eps_half": [], "b_rows": [], "c_tilt": []}

# (a) eps_half from F alone: S-1 halves when F(eps)^a = 1/2, F = grid mean (1-eps)^N2q (1-eps/10)^N1q
for n, n2q, n1q, rep in ((6, [90, 210], [30, 78], 2.6e-3), (8, [168], [40], 2.3e-3)):
    F = lambda e: np.mean([(1 - e) ** a * (1 - e / 10) ** b for a, b in zip(n2q, n1q)])
    for a in (0.99, 1.35):
        e = brentq(lambda x: F(x) ** a - 0.5, 1e-6, 0.5)
        out["a_eps_half"].append(dict(n=n, a=a, eps_half_from_F=e, D3_reported_LOW=rep, ln2_over_meanN2q=np.log(2) / np.mean(n2q)))
        print(f"(a) n={n} a={a}: eps_half(F only)={e:.2e}  D3 LOW={rep:.1e}  ln2/<N2q>={np.log(2)/np.mean(n2q):.2e}", flush=True)

for rec in inst:
    if rec["family"] != "sk" or rec["n"] not in (6, 8) or rec["source"] != "exactDM":
        continue
    n, seed = rec["n"], rec["seed"]
    J, h = qmc.sk_instance(n, seed)
    E = qmc.ising_energies(J, h)
    C = np.load(D3 + f"cache/skn{n}_s{seed}.npz")
    Qi = C["Q_ideal"]
    pairs = list(itertools.combinations(range(n), 2))
    triples = list(itertools.combinations(range(n), 3))
    try:
        M = np.load(D3 + f"cache/fake_marrakesh_n{n}_s{seed}.npz")["Q_RO"]
    except FileNotFoundError:
        M = None
    for reg in ("LOW", "MEDIUM", "HIGH"):
        b = rec[f"beta_{reg}"]
        gmix, wmix, _ = L.best_mix(E, b, n)
        g2, w2 = L.hb_mixed_with_uniform(L.block_hb_P(E, b, pairs), E, b, n)
        g3, w3 = L.hb_mixed_with_uniform(L.block_hb_P(E, b, triples), E, b, n)
        gq = qmc.gap(Qi, E, b)
        gU = qmc.gap(qmc.uniform_Q(n), E, b)
        best = max(gmix, g2, g3)
        row = dict(n=n, seed=seed, regime=reg, beta=b, S_vs_mix=gq / gmix, best_mix_w_local=wmix,
                   S_vs_pairHB=gq / g2, S_vs_tripleHB=gq / g3, S_vs_best=gq / best,
                   rU=gU / best, best_kind=["mix", "pairHB", "tripleHB"][int(np.argmax([gmix, g2, g3]))])
        for eps in ("0.002", "0.005", "0.01"):
            k = f"Q_dep_{eps}"
            if k in C:
                row[f"S_dep{eps}_vs_best"] = qmc.gap(C[k], E, b) / best
        if M is not None:
            row["S_marrakesh_vs_mix"] = qmc.gap(M, E, b) / gmix
            row["S_marrakesh_vs_best"] = qmc.gap(M, E, b) / best
        out["b_rows"].append(row)
        print("(b)", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        for z in (0.02, 0.05, 0.1, 0.2):
            out["c_tilt"].append(dict(n=n, seed=seed, regime=reg, z=z, tvd=L.tilt_bias(E, b, n, z)))


def med(rows, key, **f):
    v = [r[key] for r in rows if all(r.get(a) == c for a, c in f.items()) and key in r]
    return (float(np.median(v)), float(np.percentile(v, 25)), float(np.percentile(v, 75)), len(v)) if v else None


summ = {}
for n in (6, 8):
    for reg in ("LOW", "MEDIUM", "HIGH"):
        for key in ("S_vs_mix", "S_vs_pairHB", "S_vs_tripleHB", "S_vs_best", "rU", "S_dep0.002_vs_best",
                    "S_dep0.005_vs_best", "S_dep0.01_vs_best", "S_marrakesh_vs_mix", "S_marrakesh_vs_best"):
            m = med(out["b_rows"], key, n=n, regime=reg)
            if m:
                summ[f"n{n}_{reg}_{key}"] = m
        for z in (0.02, 0.05, 0.1, 0.2):
            summ[f"n{n}_{reg}_tilt_z{z}"] = med(out["c_tilt"], "tvd", n=n, regime=reg, z=z)
out["summary"] = summ
for k, v in summ.items():
    print("SUM", k, "median %.3g IQR [%.3g, %.3g] N=%d" % v)
json.dump(out, open("results/claim1.json", "w"), indent=1)
