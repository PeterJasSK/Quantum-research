"""Claim A attack: stronger classical baselines on the D6 planted dense BPSK/CDMA window (alpha=0.5), same instances.
Usage: python claimA.py --n 10 --inst 6 --snrs 3,6,10,14 --betas 0.5,1,2,4 --stbetas 1,2 --out results/claimA_n10.json
Exact symmetrised operators; gap = relaxation gap 1-lambda_2 (D6 primary convention)."""
import argparse, json, time, sys
import numpy as np
import e1lib as e
d = e.d
qmc = e.qmc
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D6-inference-nishimori")
from exp1_planted import instance  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=8)
ap.add_argument("--alpha", type=float, default=0.5)
ap.add_argument("--inst", type=int, default=10)
ap.add_argument("--inst0", type=int, default=0)
ap.add_argument("--snrs", default="3,6,10,14")
ap.add_argument("--betas", default="0.5,0.71,1,1.41,2,4")
ap.add_argument("--stbetas", default="0.5,0.71,1,1.41,2,4")
ap.add_argument("--iat", action="store_true", help="exact ST target IAT for best ladder (dense inverse)")
ap.add_argument("--lean", action="store_true", help="n=12: reduced kernel set")
ap.add_argument("--out", required=True)
a = ap.parse_args()
n = a.n
S = qmc.spins(n).astype(float)
betas = [float(x) for x in a.betas.split(",")]
stbetas = [float(x) for x in a.stbetas.split(",")]
QL, QU = d.local_Q(n), d.uniform_Q(n)
LADDERS = [(K, r) for K in (3, 4, 6, 8) for r in (0.3, 0.1, 0.03)]
rows = []
t0 = time.time()
for inst in range(a.inst0, a.inst0 + a.inst):
    A, x0, w = instance("dense", n, a.alpha, inst)
    x0_idx = int(sum(((1 - x0[i]) // 2) << i for i in range(n)))
    G = A.T @ A
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    pmasks = [(1 << i) | (1 << j) for i, j in pairs]
    pw = [abs(G[i, j]) for i, j in pairs]
    QPw = e.weighted_flip_Q(n, pmasks, pw)
    QH = {} if a.lean else {rho: e.hamming_Q(n, rho) for rho in (0.15, 0.3, 0.5)}
    for snr in [float(x) for x in a.snrs.split(",")]:
        sig = 10 ** (-snr / 20)
        y = A @ x0 + sig * w
        E = ((y[None, :] - S @ A.T) ** 2).sum(1) / (2 * sig ** 2)
        Jm = -(G - np.diag(np.diag(G))) / sig ** 2
        hv = A.T @ y / sig ** 2
        kern = d.QKern(E)
        prs = d.layden_draws(0)
        Qq = kern.Qavg(prs); Qd = kern.decohered(prs)
        dmap = e.descent_map(E, n)
        allmins = np.unique(dmap)
        rng = np.random.default_rng([11, n, inst, int(snr)])
        starts = rng.integers(0, 2 ** n, 2 * n)
        mins_real = np.unique(dmap[starts])
        hotgap = {}

        def best_cheap_gap(bh):
            k = round(bh, 10)
            if k not in hotgap:
                AL_, AU_ = d.A_sym(QL, E, bh), d.A_sym(QU, E, bh)
                hotgap[k] = max(e.relgap(AL_)[0], e.relgap(AU_)[0], e.relgap(0.5 * (AL_ + AU_))[0])
            return hotgap[k]

        for beta in betas:
            res = dict(n=n, alpha=a.alpha, inst=inst, snr_db=snr, beta=beta, n_minima=int(len(allmins)),
                       n_minima_found=int(len(mins_real)), map_is_planted=bool(np.argmin(E) == x0_idx))
            pi = np.exp(d.logpi(E, beta))
            q, Pd = e.overlap_dist(pi, n)
            res["Pq12"] = Pd.tolist()
            res["P_q12_lt_0.5"] = float(Pd[q < 0.5].sum())
            res["P_q12_eq_1"] = float(Pd[-1 if q[-1] == 1 else 0])
            mins, mass = e.basin_masses(E, pi, n)
            o = np.argsort(-mass)
            res["basin_mass_top"] = mass[o[:4]].tolist()
            res["n_basins_gt5pct"] = int((mass > 0.05).sum())
            if len(o) > 1:
                res["hamming_top2"] = int(bin(int(mins[o[0]]) ^ int(mins[o[1]])).count("1"))
            res["m_planted"] = float(pi @ (S @ S[x0_idx])) / n
            AL, AU = d.A_sym(QL, E, beta), d.A_sym(QU, E, beta)
            g = {}
            g["L"] = e.relgap(AL)[0]; g["U"] = e.relgap(AU)[0]; g["LU"] = e.relgap(0.5 * (AL + AU))[0]
            # (1) multi-temperature PT proxy, charged by the best cheap chain at the hot temperature
            best_pt = (-1, "")
            for fr in ((0.25,) if a.lean else (0.5, 0.25, 0.1)):
                bh = fr * beta
                kh = 1.0 / max(best_cheap_gap(bh), 1e-15)
                AH = e.A_indep(d.logpi(E, bh), E, beta)
                for ww in ((0.5,) if a.lean else (0.5, 0.2)):
                    gg = e.relgap((1 - ww) * AL + ww * AH)[0] / ((1 - ww) + ww * kh)
                    if gg > best_pt[0]:
                        best_pt = (gg, f"bh={fr}b,w={ww},kh={kh:.3g}")
            g["PTmulti"], res["PTmulti_name"] = best_pt
            # (4) pair / multi-flip moves
            APw = d.A_sym(QPw, E, beta)
            g["L+Pw"] = e.relgap(0.5 * (AL + APw))[0]
            if not a.lean:
                g["L+Pw+U"] = e.relgap((AL + APw + AU) / 3)[0]
            for rho, Qh in ({} if a.lean else QH).items():
                g[f"L+HM{rho}"] = e.relgap(0.5 * (AL + d.A_sym(Qh, E, beta)))[0]
            # mode-hopping independence proposal from greedy-descent minima (realisable: 2n random starts)
            def modeprop(minset, tag):
                C = S[minset]
                wts = np.exp(-beta * (E[minset] - E[minset].min()))
                bestm = (-1, "")
                for eps in ((0.15,) if a.lean else (0.05, 0.15)):
                    AH = e.A_indep(e.product_logq(C, eps, n, wts), E, beta)
                    for ww in ((0.9,) if a.lean else (0.5, 0.9)):
                        gg = e.relgap((1 - ww) * AL + ww * AH)[0]
                        if gg > bestm[0]:
                            bestm = (gg, f"eps={eps},w={ww}")
                g[tag], res[tag + "_name"] = bestm
            modeprop(mins_real, "MODE")
            # (3) mean-field / TAP-guided independence proposals (mixture over fixed points from 2n starts)
            bestmf = (-1, "")
            for tap in ((False,) if a.lean else (False, True)):
                M = e.tap_fixed_points(Jm, hv, beta, 2 * n, np.random.default_rng([12, n, inst, int(snr), tap]),
                                       tap=tap)
                if len(M) == 0:
                    continue
                for clip in ((0.2,) if a.lean else (0.05, 0.2)):
                    AH = e.A_indep(e.magnet_logq(M, n, clip), E, beta)
                    gg = e.relgap(0.5 * (AL + AH))[0]
                    if gg > bestmf[0]:
                        bestmf = (gg, f"tap={tap},clip={clip},nfp={len(M)}")
            g["MF"], res["MF_name"] = bestmf
            # (2) simulated tempering, exact weights, tuned ladder; charged gamma/K
            if any(abs(beta - b) < 1e-9 for b in stbetas):
                bst = (-1, None, -1)
                bst_un = -1
                for K, r in LADDERS:
                    lad = beta * r ** (np.arange(K) / (K - 1))
                    Ast, phi = e.st_operator(E, n, lad)
                    gs = e.relgap_sparse(Ast, phi)
                    bst_un = max(bst_un, gs)
                    if gs / K > bst[0]:
                        bst = (gs / K, (K, r), gs)
                g["ST"] = bst[0]; res["ST_ladder"] = bst[1]; res["ST_gap_uncharged_bestcharged"] = bst[2]
                res["ST_uncharged_max"] = bst_un
                if a.iat:
                    K, r = bst[1]
                    lad = beta * r ** (np.arange(K) / (K - 1))
                    Ast, phi = e.st_operator(E, n, lad)
                    res["ST_tau_target"] = e.st_target_iat(Ast, phi, K, 2 ** n, 0)
                    res["ST_tau_bound"] = K * e.tau_from_relgap(bst[2])
            # oracles (NOT in best): all minima, exact-marginal product
            modeprop(allmins, "MODEall")
            mag = pi @ S
            bo = -1
            for clip in (0.05, 0.2):
                bo = max(bo, e.relgap(0.5 * (AL + e.A_indep(e.magnet_logq(mag, n, clip), E, beta)))[0])
            g["EXMARG"] = bo
            # quantum
            AQ, AD = d.A_sym(Qq, E, beta), d.A_sym(Qd, E, beta)
            g["Q"] = e.relgap(AQ)[0]; g["D"] = e.relgap(AD)[0]
            realis = [k for k in g if k not in ("MODEall", "EXMARG", "Q", "D")]
            d6set = ["L", "U", "LU"]
            bname = max(realis, key=lambda k: g[k])
            res.update({f"g_{k}": v for k, v in g.items()})
            res["best_real"] = g[bname]; res["best_real_name"] = bname
            res["best_nomode"] = max(g[k] for k in realis if k != "MODE")
            res["S_new"] = g["Q"] / g[bname]
            res["S_nomode"] = g["Q"] / res["best_nomode"]
            res["S_C1"] = g["Q"] / max(g[k] for k in d6set)
            res["S_dec_new"] = g["D"] / g[bname]
            res["Q_over_D"] = g["Q"] / g["D"]
            rows.append(res)
        print(f"inst={inst} snr={snr} nmin={len(allmins)} found={len(mins_real)} t={time.time()-t0:.0f}s | " +
              " ".join(f"b{r['beta']}:S={r['S_new']:.2f}({r['best_real_name']}),Snm={r['S_nomode']:.2f},SC1={r['S_C1']:.2f}"
                       for r in rows[-len(betas):]), flush=True)
    json.dump(rows, open(a.out, "w"))
print("done", len(rows), f"{time.time()-t0:.0f}s")
