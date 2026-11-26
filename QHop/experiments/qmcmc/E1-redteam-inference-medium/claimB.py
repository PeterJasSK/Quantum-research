"""Claim B attack: EXACT Swendsen-Wang / Wolff (ghost spin for field, subset DP) on SK n=6..12 at MEDIUM beta,
vs Layden QeMCMC and a wider QeMCMC tuning grid (incl. alpha rescaling). Same instances as D1 (seed 1000n+i).
Usage: python claimB.py N NINST [tune]   -> results/claimB_n{N}.json"""
import sys, json, time
import numpy as np
import e1lib as e
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D1-temperature-map")
import d1lib as L  # noqa

qmc = e.qmc
n = int(sys.argv[1]); ninst = int(sys.argv[2]); tune = len(sys.argv) > 3 and sys.argv[3] == "tune"
KS = [5, 6, 7]  # beta/beta_c = 0.681, 1.0, 1.468 (D1 MEDIUM grid points)
WS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
TG = [0.2, 0.381, 0.556, 0.7]
out = []
t0 = time.time()
for inst in range(ninst):
    J, h = qmc.sk_instance(n, 1000 * n + inst); E = qmc.ising_energies(J, h)
    bc, _ = L.beta_c_from_C(E, n)
    nv, ed = L.graph_from_J(J, h, ghost=True)
    Ql, Qu = qmc.local_Q(n), qmc.uniform_Q(n)
    K = L.QKern(E); lay = L.layden_draws(inst); Qlay = K.Qavg(lay); Qdec = K.decohered(lay)
    cells = {}
    if tune:
        for am in (0.5, 1.0, 2.0):
            Ka = L.QKern(E, alpha=am * K.alpha)
            for g in TG:
                for w in L.TUNE_W:
                    cells[f"a{am}_g{g}_t{w[0]}-{w[1]}"] = Ka.Qavg([(g, t) for t in L.tune_ts(w, 3)])
            if am != 1.0:
                cells[f"a{am}_layden"] = Ka.Qavg(lay)
    tq = time.time() - t0
    full = 2 ** (n + 1) - 1
    X = np.arange(2 ** n)
    r = dict(n=n, inst=inst, beta_c=bc, ratios=[float(L.RATIOS[k]) for k in KS], rows=[])
    for k in KS:
        b = bc * L.RATIOS[k]
        pi = L.boltz(E, b)
        dct = {}
        def put(name, A):
            ga, gr = L.gap_sym(A, pi, both=True)
            dct[name] = (ga, gr)
        put("local", L.mh_sym(Ql, E, b)); put("uniform", L.mh_sym(Qu, E, b))
        mb = max(((w, L.gap_sym(L.mh_sym((1 - w) * Ql + w * Qu, E, b), pi, both=True)) for w in WS), key=lambda x: x[1][0])
        dct["mixbest"] = mb[1]
        put("layden", L.mh_sym(Qlay, E, b)); put("decohered", L.mh_sym(Qdec, E, b))
        if cells:
            best = max(((nm, L.gap_sym(L.mh_sym(Q, E, b), pi, both=True)) for nm, Q in cells.items()), key=lambda x: x[1][0])
            dct["tuned"] = best[1]; dct["tuned_cell"] = best[0]
        tc = time.time()
        Psw, Pw = e.cluster_kernels(nv, ed, b, X)
        for nm, P in (("SW", Psw), ("Wolff", Pw)):
            Pp = P[:, X] + P[:, X ^ full]
            rs = float(np.abs(Pp.sum(1) - 1).max())
            dq = np.sqrt(pi); A = (dq[:, None] * Pp) / dq[None, :]
            asym = float(np.abs(A - A.T).max())
            ga, gr = L.gap_sym(0.5 * (A + A.T), pi, both=True)
            dct[nm] = (ga, gr); dct[nm + "_rowsum_err"] = rs; dct[nm + "_asym"] = asym
        dct["t_cluster_s"] = time.time() - tc
        dct["beta"] = float(b); dct["ratio"] = float(L.RATIOS[k])
        r["rows"].append(dct)
    out.append(r)
    print(f"n={n} inst={inst} bc={bc:.3f} tq={tq:.0f}s t={time.time()-t0:.0f}s "
          + " ".join(f"r{x['ratio']:.2f}:lay/SW={x['layden'][0]/x['SW'][0]:.2f},lay/W={x['layden'][0]/x['Wolff'][0]:.2f},lay/mix={x['layden'][0]/x['mixbest'][0]:.2f},asym={x['SW_asym']:.1e}" for x in r["rows"]), flush=True)
    json.dump(out, open(f"results/claimB_n{n}.json", "w"))
print("done", time.time() - t0)
