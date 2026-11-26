"""SK cluster moves (ghost spin for the field). Exact SW/Wolff at n=6 (7 vertices, 21 bonds) for 10 instances;
sampled (2e4 moves/state, 10 bootstrap) at n=10 (11 vertices, 55 bonds) for instance INSTANCE on the
same beta grid as run_family sk10.  Usage: python run_sk_clusters.py exact6 | python run_sk_clusters.py s10 INSTANCE"""
import sys, json, time
import numpy as np
import d1lib as L
qmc = L.qmc
mode = sys.argv[1]
if mode == "exact6":
    n = 6; out = []
    for inst in range(10):
        J, h = qmc.sk_instance(n, 1000 * n + inst); E = qmc.ising_energies(J, h)
        bc, _ = L.beta_c_from_C(E, n); betas = bc * L.RATIOS
        nv, ed = L.graph_from_J(J, h, ghost=True); X = L.ExactCluster(nv, ed)
        r = dict(instance=inst, beta_c=bc, ratios=L.RATIOS.tolist(), gaps={k: [] for k in
                 ("SW", "Wolff", "local", "uniform", "mixbest", "layden", "tunedbest")})
        Ql, Qu = qmc.local_Q(n), qmc.uniform_Q(n)
        K = L.QKern(E); Qlay = K.Qavg(L.layden_draws(inst))
        cells = [K.Qavg([(g, t) for t in L.tune_ts(w, 3)]) for g in L.TUNE_G for w in L.TUNE_W]
        for b in betas:
            pi = L.boltz(E, b); d = np.sqrt(X.pi(b))
            Psw = X.sw_sym(b) * d[None, :] / d[:, None]
            r["gaps"]["SW"].append(L.gap_P_reversible(L.lump_ghost(Psw, n), pi)[0])
            r["gaps"]["Wolff"].append(L.gap_P_reversible(L.lump_ghost(X.wolff_P(b), n), pi)[0])
            r["gaps"]["local"].append(L.gap_Q(Ql, E, b)); r["gaps"]["uniform"].append(L.gap_Q(Qu, E, b))
            r["gaps"]["mixbest"].append(max(L.gap_Q((1 - w) * Ql + w * Qu, E, b) for w in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)))
            r["gaps"]["layden"].append(L.gap_Q(Qlay, E, b))
            r["gaps"]["tunedbest"].append(max(L.gap_Q(Q, E, b) for Q in cells))
        out.append(r); print("exact6", inst, flush=True)
    json.dump(out, open("results/sk_clusters_exact_n6.json", "w"))
else:
    inst = int(sys.argv[2]); n = 10
    J, h = qmc.sk_instance(n, 1000 * n + inst); E = qmc.ising_energies(J, h)
    bc, _ = L.beta_c_from_C(E, n); betas = bc * L.RATIOS
    nv, ed = L.graph_from_J(J, h, ghost=True)
    r = dict(instance=inst, beta_c=bc, ratios=L.RATIOS.tolist(), nsamp=20000, SW=[], SW_boot=[], Wolff=[],
             Wolff_boot=[], largest_cluster_frac_pi=[])
    KS = [2, 4, 6, 8, 10]  # ratios 0.215, 0.464, 1.0, 2.15, 4.64 (CPU budget)
    r["ratios"] = [float(L.RATIOS[k]) for k in KS]
    for k in KS:
        b = betas[k]
        t = time.time()
        # only ghost-bit-0 rows are needed for the Z2-lumped physical chain
        Csw, Cw, lcf = L.sampled_cluster_P(nv, ed, b, 20000, 1000 + 17 * inst + k, chunk=16, rows=np.arange(2 ** n))
        pi = L.boltz(E, b)
        Csw = L.lump_ghost(Csw.astype(float), n); Cw = L.lump_ghost(Cw.astype(float), n)
        g, bs = L.gap_from_counts(Csw, pi, nboot=10, seed=k); r["SW"].append(g); r["SW_boot"].append(bs)
        g, bw = L.gap_from_counts(Cw, pi, nboot=10, seed=k); r["Wolff"].append(g); r["Wolff_boot"].append(bw)
        # pi-weighted largest cluster fraction (ext states with ghost bit 0 represent physical states)
        r["largest_cluster_frac_pi"].append(float((pi * lcf[:2 ** n]).sum()))
        print("s10", inst, k, "%.0fs" % (time.time() - t), flush=True)
    json.dump(r, open(f"results/sk_clusters_sampled_n10_i{inst}.json", "w"))
