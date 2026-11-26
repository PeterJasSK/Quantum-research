"""D5 main sweep: exact spectral gaps of surrogate-driven quantum and classical proposals.
import sys; sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
Usage: python sweep.py --n 10 --inst 0 1 2 3 4 [--fams a b c] [--rhos ...] [--light]
Writes results/raw_n{n}_i{inst}.jsonl (one JSON record per (family, rho, regime))."""
import argparse
import json
import time
import numpy as np
import d5lib as L
import qmc

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, required=True)
ap.add_argument("--inst", type=int, nargs="+", required=True)
ap.add_argument("--fams", nargs="+", default=["a", "b", "c"])
ap.add_argument("--rhos", type=float, nargs="+", default=[0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9])
ap.add_argument("--rhos_c", type=float, nargs="+", default=[0.1, 0.2, 0.3, 0.5, 0.7])
ap.add_argument("--oracle_rhos", type=float, nargs="+", default=None, help="default: all")
ap.add_argument("--light", action="store_true", help="n=12 mode: no decohered control, nested K=1 only, no beta_loc")
ap.add_argument("--Kdecades", type=int, default=6)
args = ap.parse_args()

n = args.n
X = L.quad_design(n)
Ql = qmc.local_Q(n)
Qu = qmc.uniform_Q(n)
Qm = 0.5 * Ql + 0.5 * Qu
Ks = [10 ** k for k in range(args.Kdecades + 1)]
nested_Ks = [1] if args.light else [1, 10, 100]


def da_scan(Pinner, Et, Es, beta, lpt, Ks, pis):
    """gaps of DA with inner kernel Pinner^K for K in Ks (decades)."""
    res = {}
    cur = Pinner
    conv = False
    for K in Ks:
        if not conv:
            P = L.da_outer(cur, Et, Es, beta)
            g = L.gap_rev(P)
            mv, ca = L.move_stats(P, cur, lpt)
            if np.abs(cur - pis[None, :]).max() < 1e-13:
                conv = True
        res[K] = dict(gap=g, move=mv, acc=ca, converged=conv)
        if K != Ks[-1] and not conv:
            cur = L.matpow10(cur)
    return res


for inst in args.inst:
    t_inst = time.time()
    cache = {}
    gam, ts = L.qparams(7 + inst, 16)
    out = open(f"results/raw_n{n}_i{inst}.jsonl", "w")
    Qcache = {}
    for fam in args.fams:
        rhos = args.rhos_c if fam == "c" else args.rhos
        for rho in rhos:
            if fam == "b" and rho == 0.0:
                continue
            tc = time.time()
            built = L.make_family(fam, n, inst, rho, X, cache)
            if built is None:
                print("skip", fam, rho, "unreachable")
                continue
            Et, Es, info = built
            # quantum proposals
            key = "sk" if fam in ("a", "b") else f"c{rho}"
            if key not in Qcache:
                Qcache[key] = {"qs": L.quantum_Q_sym(Es, gam, ts)}
                if not args.light:
                    Qcache[key]["dec"] = L.decohered_Q_sym(Es, gam, ts)
            Qs = Qcache[key]["qs"]
            Qd = Qcache[key].get("dec")
            do_or = args.oracle_rhos is None or any(abs(rho - r) < 1e-9 for r in args.oracle_rhos)
            Qt = L.quantum_Q_sym(Et, gam, ts) if do_or else None
            bc, betas, grid, C = L.regime_betas(Et, n)
            beta_loc = None
            if not args.light:
                bl = np.logspace(-2, 0.7, 28)
                gl = np.array([L.gap_rev(L.mh_sym(Ql, Et, b)) for b in bl])
                below = np.where(gl < 0.1 * gl[0])[0]
                beta_loc = float(bl[below[0]]) if len(below) else None
            for reg, beta in betas.items():
                lpt = L.logpi(Et, beta)
                lps = L.logpi(Es, beta)
                pis = np.exp(lps)
                rec = dict(n=n, inst=inst, fam=fam, rho=rho, regime=reg, beta=beta, beta_c=bc, beta_loc=beta_loc,
                           **info, beta_sigma=beta * info["sigma_abs"], two_phi=float(L.two_phi(beta * info["sigma_abs"])))
                G = {}
                for name, Q in (("local", Ql), ("uniform", Qu), ("mix_lu", Qm), ("q_sur", Qs), ("q_true", Qt),
                                ("q_sur_decoh", Qd)):
                    if Q is None:
                        continue
                    P = L.mh_sym(Q, Et, beta)
                    mv, ca = L.move_stats(P, Q, lpt)
                    G[name] = dict(gap=L.gap_rev(P), move=mv, acc=ca)
                G["q_sur"]["acc_residual_only"] = L.residual_only_acceptance(Qs, Et, Es, beta, lpt)
                G["local"]["acc_residual_only"] = L.residual_only_acceptance(Ql, Et, Es, beta, lpt)
                # gap of the surrogate's own chains (how glassy is the surrogate?)
                G["sur_local_gap"] = L.gap_rev(L.mh_sym(Ql, Es, beta))
                G["sur_mix_gap"] = L.gap_rev(L.mh_sym(Qm, Es, beta))
                G["sur_qsur_gap"] = L.gap_rev(L.mh_sym(Qs, Es, beta))
                # classical delayed acceptance
                Kinf = L.independence_kernel(Es, beta)
                P = L.da_outer(Kinf, Et, Es, beta)
                mv, ca = L.move_stats(P, Kinf, lpt)
                G["DA_inf"] = dict(gap=L.gap_rev(P), move=mv, acc=ca,
                                   acc_incl_self=float(1 - (np.exp(lpt) * np.diag(P)).sum() + (np.exp(lpt) * pis).sum()),
                                   acc_residual_only=L.residual_only_acceptance(Kinf, Et, Es, beta, lpt))
                G["DA_local"] = da_scan(L.mh_sym(Ql, Es, beta), Et, Es, beta, lpt, Ks, pis)
                G["DA_mix"] = da_scan(L.mh_sym(Qm, Es, beta), Et, Es, beta, lpt, Ks, pis)
                G["nested_q"] = da_scan(L.mh_sym(Qs, Es, beta), Et, Es, beta, lpt, nested_Ks, pis)
                rec["G"] = G
                out.write(json.dumps(rec) + "\n")
                out.flush()
            print(f"n={n} inst={inst} fam={fam} rho={rho} rho_act={info['rho_actual']:.3f} bc={bc:.3f} "
                  f"t={time.time() - tc:.1f}s", flush=True)
    out.close()
    print(f"inst {inst} done in {time.time() - t_inst:.0f}s", flush=True)
