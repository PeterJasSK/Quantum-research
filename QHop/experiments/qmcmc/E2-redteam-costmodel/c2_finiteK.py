"""E2 claim 2: re-score D5 with a REALISTIC classical surrogate sampler instead of exact pi_sur draws.
Competitor T-DA(K): inner kernel = K steps of Metropolis on E_sur at hotter beta' = f beta (inner proposal local, or
50/50 local+uniform), outer accept min(1, pi_t(s') pi'_sur(s) / (pi_t(s) pi'_sur(s'))) -> exact (Liu 2001 surrogate
transition, inner kernel reversible w.r.t. pi'_sur). Plus its 50/50 mixture with local Metropolis on E_true.
One true-energy call per outer step (K surrogate steps free), same accounting as D5 S_free / S_K1000.
q_sur gaps and same-beta DA gaps are READ from D5 raw jsonl (not recomputed). Exact matrices, ideal.
Usage: python c2_finiteK.py N INST... -> results/c2_finiteK_n{N}.jsonl"""
import json, os, sys, time
import numpy as np
D5 = "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D5-surrogate"
sys.path.insert(0, D5)
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import d5lib as L  # noqa
import qmc  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
n = int(sys.argv[1])
insts = [int(a) for a in sys.argv[2:]]
FS = [0.7, 0.5, 0.35, 0.25]
KS = [1, 10, 100, 1000]
CELLS = {("a", 0.1), ("a", 0.3), ("a", 0.5), ("b", 0.1), ("b", 0.3), ("b", 0.5), ("c", 0.3), ("a", 0.6)}
X = L.quad_design(n)
Ql = qmc.local_Q(n)
Qm = 0.5 * Ql + 0.5 * qmc.uniform_Q(n)


def tda(Kin, Et, Es, b, bp):
    lw = -b * Et + bp * Es
    M = lw[None, :] - lw[:, None]
    P = Kin * np.exp(np.minimum(0.0, M))
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return P


out = open(os.path.join(HERE, "results", f"c2_finiteK_n{n}.jsonl"), "a")
t0 = time.time()
for inst in insts:
    recs = [json.loads(l) for l in open(os.path.join(D5, "results", f"raw_n{n}_i{inst}.jsonl"))]
    cache = {}
    for r in recs:
        if r["regime"] not in ("MEDIUM", "LOW") or (r["fam"], r["rho"]) not in CELLS:
            continue
        built = L.make_family(r["fam"], n, inst, r["rho"], X, cache)
        Et, Es, _ = built
        b = r["beta"]
        Pl_true = L.mh_sym(Ql, Et, b)
        res = {}
        for iname, Qin in (("local", Ql), ("mix", Qm)):
            for f in FS:
                bp = f * b
                Pin = L.mh_sym(Qin, Es, bp)
                cur, Kc = Pin, 1
                for K in KS:
                    while Kc < K:
                        cur = L.matpow10(cur)
                        Kc *= 10
                    res[(iname, f, K)] = L.gap_rev(tda(cur, Et, Es, b, bp))
            for K in KS:
                fb = max(FS, key=lambda f: res[(iname, f, K)])
                Pin = L.mh_sym(Qin, Es, fb * b)
                cur = Pin
                for _ in range(int(np.log10(K))):
                    cur = L.matpow10(cur)
                res[(iname, "mixlocal", K)] = L.gap_rev(0.5 * tda(cur, Et, Es, b, fb * b) + 0.5 * Pl_true)
                res[(iname, "fbest", K)] = fb
        G = r["G"]
        rec = dict(n=n, inst=inst, fam=r["fam"], rho=r["rho"], regime=r["regime"], beta=b, beta_sigma=r["beta_sigma"],
                   gap_q_sur=G["q_sur"]["gap"], gap_local=G["local"]["gap"], gap_uniform=G["uniform"]["gap"],
                   gap_mix_lu=G["mix_lu"]["gap"], gap_DA_inf=G["DA_inf"]["gap"],
                   DA_same={f"{k}_{K}": v["gap"] for k in ("DA_local", "DA_mix") for K, v in G[k].items()},
                   TDA={f"{a}_{f}_{K}": v for (a, f, K), v in res.items()})
        out.write(json.dumps(rec) + "\n")
        out.flush()
    print(n, inst, f"{time.time()-t0:.0f}s", flush=True)
