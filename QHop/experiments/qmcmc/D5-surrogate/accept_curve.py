"""D5 claim (ii): equilibrium acceptance vs beta*sigma against 2 Phi(-beta sigma / sqrt 2).
Run: python accept_curve.py --n 10 --inst 0 1 2 3 4   -> results/accept_curve_n{n}.csv"""
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
args = ap.parse_args()
n = args.n
X = L.quad_design(n)
Ql = qmc.local_Q(n)
betas = np.logspace(-2, 0.7, 25)
rows = []
for inst in args.inst:
    cache = {}
    gam, ts = L.qparams(7 + inst, 16)
    Qsk = None
    for fam in ("a", "b", "c"):
        for rho in (0.1, 0.3, 0.5, 0.7):
            built = L.make_family(fam, n, inst, rho, X, cache)
            if built is None:
                continue
            Et, Es, info = built
            if fam in ("a", "b"):
                if Qsk is None:
                    Qsk = L.quantum_Q_sym(Es, gam, ts)
                Qs = Qsk
            else:
                Qs = L.quantum_Q_sym(Es, gam, ts)
            for b in betas:
                lpt = L.logpi(Et, b)
                pit = np.exp(lpt)
                pis = np.exp(L.logpi(Es, b))
                Kinf = L.independence_kernel(Es, b)
                Pda = L.da_outer(Kinf, Et, Es, b)
                da_mv, da_acc = L.move_stats(Pda, Kinf, lpt)
                da_incl = float(1 - (pit * np.diag(Pda)).sum() + (pit * pis).sum())
                Pq = L.mh_sym(Qs, Et, b)
                q_mv, q_acc = L.move_stats(Pq, Qs, lpt)
                Pl = L.mh_sym(Ql, Et, b)
                l_mv, l_acc = L.move_stats(Pl, Ql, lpt)
                rows.append(dict(n=n, inst=inst, fam=fam, rho=rho, rho_actual=info["rho_actual"],
                                 sigma_abs=info["sigma_abs"], beta=b, beta_sigma=b * info["sigma_abs"],
                                 two_phi=float(L.two_phi(b * info["sigma_abs"])),
                                 DAinf_acc_incl_self=da_incl, DAinf_acc_cond=da_acc,
                                 qsur_acc=q_acc, qsur_acc_residual_only=L.residual_only_acceptance(Qs, Et, Es, b, lpt),
                                 local_acc=l_acc, local_acc_residual_only=L.residual_only_acceptance(Ql, Et, Es, b, lpt)))
            print(inst, fam, rho, flush=True)
with open(f"results/accept_curve_n{n}.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
