"""D9 V24 mask-library experiment, one instance per call. Exact transition matrices, ideal (noiseless) proposals.
Usage: python d9_run.py FAMILY N SEED [--lite]     FAMILY in {sk, ea}; ea uses a 3x4 periodic lattice (N must be 12).
Writes raw/{family}_n{N}_s{SEED}.json. --lite (used at n=12): no decohered law, libraries L in {128,1024,8192}
(plus 32 for the quantum law), SK betas without 0.5, local-mixtures for infinite laws and L=1024 only.
"""
import json
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d9lib as D  # noqa: E402
from d9lib import qmc  # noqa: E402

fam, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
lite = "--lite" in sys.argv
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", f"{fam}_n{n}_s{seed}.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
t0 = time.time()
if fam == "sk":
    J, h = qmc.sk_instance(n, seed)
else:
    J, h = qmc.ea_instance(3, 4, seed)
    assert n == 12
E = qmc.ising_energies(J, h)
d = 2 ** n

# regime markers
bgrid = np.round(np.geomspace(0.05, 5, 41), 4)
C = qmc.thermo(E, n, bgrid)
beta_c = float(bgrid[C.argmax()])
lgrid = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]
if not lite:
    lg = [D.gap_mask(D.local_law(n), E, b) for b in lgrid]
else:
    lg = None
betas = [0.1, 0.3, 0.5, beta_c, 1.0, 3.0] if fam == "sk" else [beta_c, 1.0, 3.0]
blabel = ["0.1", "0.3", "0.5", "bc", "1", "3"] if fam == "sk" else ["bc", "1", "3"]
if lite and fam == "sk":  # n=12: drop beta=0.5 (beta_c ~0.3 covers MEDIUM) to save time on the shared machine
    betas, blabel = [b for b, l in zip(betas, blabel) if l != "0.5"], [l for l in blabel if l != "0.5"]

# beta-independent laws
ga, ts = D.layden_params(seed, 16)
Q, Qd = D.quantum_and_decohered_Q(E, ga, ts, want_dec=not lite)
unif_r = np.full(d, 1.0 / d)
laws0 = {"qA_unifref": D.clean(D.mask_law_from_Q(Q, unif_r))}
if Qd is not None:
    laws0["qD_decoh"] = D.clean(D.mask_law_from_Q(Qd, unif_r))
laws0["cH_wtmatch"] = D.clean(D.weight_matched(laws0["qA_unifref"], n))
basin = D.greedy_minima_law(E, n)
laws0["cF_basin"] = D.clean(D.xor_autocorr(basin))
laws0["uniform"] = D.uniform_law(n)
laws0["local"] = D.local_law(n)
n_minima = int((basin > 0).sum())
t_laws = time.time() - t0

Ls = [128, 1024, 8192] if lite else [32, 128, 1024, 8192]
Lmix = [1024] if lite else Ls
w = D.popcount(d)
rows, meta_w = [], {}
for b, bl in zip(betas, blabel):
    pi = qmc.boltzmann(E, b)
    laws = dict(laws0)
    laws["qC_piref"] = D.clean(D.mask_law_from_Q(Q, pi))
    laws["cE_DEpi"] = D.clean(D.xor_autocorr(pi))
    laws["cG_perc"] = D.clean(D.percolation_law(J, b, n, 1 << 16, 7000 + seed))
    # reference: full state-dependent P1 QeMCMC (latency mode), pure and 50% local mixture
    rows.append(dict(beta=b, blabel=bl, law="qFull_P1", L="inf", mix=0, gap=qmc.gap(Q, E, b) if n < 11 else
                     D.gap_Q(Q, E, b)))
    for name, M in laws.items():
        g = D.gap_mask(M, E, b)
        rows.append(dict(beta=b, blabel=bl, law=name, L="inf", mix=0, gap=g))
        meta_w[f"{name}@{bl}"] = float((M * w).sum())
        if name != "local":
            gm = D.gap_mask(D.mix(D.local_law(n), M), E, b)
            rows.append(dict(beta=b, blabel=bl, law=name, L="inf", mix=1, gap=gm))
    for name in ("qA_unifref", "cE_DEpi", "cF_basin", "cG_perc", "cH_wtmatch"):
        for L in ([32] + Ls if (lite and name == "qA_unifref") else Ls):
            Ml = D.library(laws[name], L, 100000 * seed + 10 * L + 1)
            if Ml is None:
                continue
            g = D.gap_mask(Ml, E, b)
            rows.append(dict(beta=b, blabel=bl, law=name, L=L, mix=0, gap=g, distinct=int((Ml > 0).sum())))
            if L in Lmix:
                gm = D.gap_mask(D.mix(D.local_law(n), Ml), E, b)
                rows.append(dict(beta=b, blabel=bl, law=name, L=L, mix=1, gap=gm))
    print(f"{fam} n={n} s={seed} beta={bl} done {time.time() - t0:.0f}s", flush=True)

json.dump(dict(family=fam, n=n, seed=seed, beta_c=beta_c, C_grid=bgrid.tolist(), C=C.tolist(),
               local_gap_grid=lgrid, local_gap=lg, n_minima=n_minima, mean_weight=meta_w,
               params=dict(gammas=ga.tolist(), ts=ts.tolist()), t_laws_s=t_laws, t_total_s=time.time() - t0,
               rows=rows), open(out, "w"))
print(f"wrote {out} in {time.time() - t0:.0f}s", flush=True)
