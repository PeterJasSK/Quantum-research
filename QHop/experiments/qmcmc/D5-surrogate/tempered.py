"""D5 extra classical competitors using the SAME surrogate (stress test of the cells where quantum wins):
  T-DA: independence proposal from pi_sur at a hotter beta' = f*beta (f in 0..1; exact draw), accept with
        min(1, pi_t(s') pi_sur,beta'(s) / (pi_t(s) pi_sur,beta'(s'))) -> exact (Hastings independence sampler).
  MIXK: 50/50 mixture of the T-DA kernel (best f) and local Metropolis on E_true (mixture of pi-reversible kernels
        is pi-reversible) - one true-energy call per step either way.
Run: python tempered.py --n 10 --inst 0 1 2 3 4  -> results/tempered_n{n}.csv"""
import sys
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import argparse
import csv
import numpy as np
import d5lib as L
import qmc

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--inst", type=int, nargs="+", default=[0, 1, 2, 3, 4])
ap.add_argument("--fams", nargs="+", default=["a", "b", "c"])
ap.add_argument("--rhos", type=float, nargs="+", default=[0.1, 0.2, 0.3, 0.5, 0.7])
args = ap.parse_args()
n = args.n
X = L.quad_design(n)
Ql = qmc.local_Q(n)
Qu = qmc.uniform_Q(n)
FS = [1.0, 0.7, 0.5, 0.35, 0.25, 0.15, 0.08, 0.0]
rows = []
for inst in args.inst:
    cache = {}
    for fam in args.fams:
        for rho in args.rhos:
            built = L.make_family(fam, n, inst, rho, X, cache)
            if built is None:
                continue
            Et, Es, info = built
            bc, betas, *_ = L.regime_betas(Et, n)
            for reg in ("MEDIUM", "LOW"):
                b = betas[reg]
                Pl = L.mh_sym(Ql, Et, b)
                gaps = {}
                for f in FS:
                    bp = f * b
                    Kin = L.independence_kernel(Es, bp)
                    # Hastings independence sampler: accept min(1, w(s')/w(s)), w = pi_t / pi_sur,beta'
                    lw = -b * Et + bp * Es
                    M = lw[None, :] - lw[:, None]
                    P = Kin * np.exp(np.minimum(0.0, M))
                    np.fill_diagonal(P, 0.0)
                    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
                    gaps[f] = (L.gap_rev(P), P)
                fbest = max(gaps, key=lambda k: gaps[k][0])
                gmix = L.gap_rev(0.5 * gaps[fbest][1] + 0.5 * Pl)
                rows.append(dict(n=n, inst=inst, fam=fam, rho=rho, regime=reg, beta=b,
                                 **{f"gap_TDA_f{f:g}": gaps[f][0] for f in FS},
                                 f_best=fbest, gap_TDA_best=gaps[fbest][0], gap_mix_TDA_local=gmix))
            print(inst, fam, rho, flush=True)
with open(f"results/tempered_n{n}.csv" if n < 12 else f"results/tempered_n{n}_i{args.inst[0]}.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
