"""Validation of d1lib against qmc and against Monte-Carlo (run: python validate.py)."""
import time, json, numpy as np
import d1lib as L
qmc = L.qmc
out = {}
# 1. mh_sym gap == qmc.gap
J, h = qmc.sk_instance(8, 8); E = qmc.ising_energies(J, h)
g, t = qmc.draw_params(0, 16); Qq = qmc.quantum_Q(E, g, t); Ql = qmc.local_Q(8)
for b in (0.3, 1.0, 3.0):
    a1 = qmc.gap(Qq, E, b); a2 = L.gap_Q(Qq, E, b); b1 = qmc.gap(Ql, E, b); b2 = L.gap_Q(Ql, E, b)
    print("gap check", b, a1, a2, b1, b2)
out["harness_ratio_q_local_beta1_n8"] = L.gap_Q(Qq, E, 1.0) / L.gap_Q(Ql, E, 1.0)
print("q/local n8 beta1 (harness says 29.25):", out["harness_ratio_q_local_beta1_n8"])
# 2. Layden stratified vs iid draws (pilot instance n=10 seed 100)
J, h = qmc.sk_instance(10, 100); E = qmc.ising_energies(J, h)
g, t = qmc.draw_params(0, 16); Qiid = qmc.quantum_Q(E, g, t)
K = L.QKern(E); Qst = K.Qavg(L.layden_draws(0))
for b in (0.1, 0.3, 1.0, 3.0):
    print("layden iid vs stratified", b, L.gap_Q(Qiid, E, b), L.gap_Q(Qst, E, b))
# 3. decohered vs qmc.decohered_Q (n=8)
J, h = qmc.sk_instance(8, 8); E = qmc.ising_energies(J, h); K = L.QKern(E)
pairs = L.layden_draws(1)
Qd1 = qmc.decohered_Q(E, [p[0] for p in pairs], [p[1] for p in pairs]); Qd2 = K.decohered(pairs)
print("decohered diff", np.abs(Qd1 - Qd2).max(), L.gap_Q(Qd1, E, 1.0), L.gap_Q(Qd2, E, 1.0))
# 4. coarse-grained vs qmc
J, h = qmc.sk_instance(7, 3); E = qmc.ising_energies(J, h); grp = L.cyclic_groups(7, 3)
pairs = L.layden_draws(2)
t0 = time.time(); Qc1 = qmc.coarse_grained_Q(J, h, grp, gammas=[p[0] for p in pairs], ts=[p[1] for p in pairs]); t1 = time.time()
Qc2 = L.coarse_grained_Q(J, h, grp, pairs); t2 = time.time()
print("CG diff", np.abs(Qc1 - Qc2).max(), "asym", qmc.asymmetry(Qc2), "times", t1 - t0, t2 - t1)
# 5. exact SW/Wolff vs sampled, 3x3 ferro and 3x3 EA +-J, and SK n=5 ghost
for name, (J, h, ghost) in {"fe33": (*qmc.ferro_instance(3, 3), False),
                            "ea33": (*qmc.ea_instance(3, 3, 1, dist="pm"), False),
                            "sk5g": (*qmc.sk_instance(5, 5), True)}.items():
    nv, ed = L.graph_from_J(J, h, ghost)
    t0 = time.time(); X = L.ExactCluster(nv, ed); tb = time.time() - t0
    n = J.shape[0]
    E = qmc.ising_energies(J, h)
    for beta in (0.2, 0.5, 1.0):
        Asw = X.sw_sym(beta); Pw = X.wolff_P(beta); pie = X.pi(beta)
        # stationarity / reversibility checks on extended chain
        d = np.sqrt(pie); Psw = Asw * d[None, :] / d[:, None]
        rs = np.abs(Psw.sum(1) - 1).max(); rw = np.abs(Pw.sum(1) - 1).max()
        st = np.abs(pie @ Pw - pie).max()
        Aw = (d[:, None] * Pw) / d[None, :]; asw = np.abs(Aw - Aw.T).max(); assw = np.abs(Asw - Asw.T).max()
        if ghost:
            Psw_p = L.lump_ghost(Psw, n); Pw_p = L.lump_ghost(Pw, n)
        else:
            Psw_p, Pw_p = Psw, Pw
        pi = L.boltz(E, beta)
        gsw, a1 = L.gap_P_reversible(Psw_p, pi); gw, a2 = L.gap_P_reversible(Pw_p, pi)
        # check pi of ext matches Boltzmann
        pich = np.abs((L.lump_ghost(pie[None, :], n)[0] if ghost else pie) - pi).max() if not ghost else \
            np.abs(pie[:2 ** n] + pie[(np.arange(2 ** n)) ^ (2 ** (n + 1) - 1)] - pi).max()
        Csw, Cw, lcf = L.sampled_cluster_P(nv, ed, beta, 20000, 7)
        if ghost:
            Csw = L.lump_ghost(Csw.astype(float), n); Cw = L.lump_ghost(Cw.astype(float), n)
        gsw_s, bs = L.gap_from_counts(Csw, pi, nboot=10); gw_s, bw = L.gap_from_counts(Cw, pi, nboot=10)
        print(f"{name} beta={beta}: rows {rs:.1e} {rw:.1e} stat {st:.1e} asym {assw:.1e} {asw:.1e} pi-chk {pich:.1e} | "
              f"SW exact {gsw:.4f} sampled {gsw_s:.4f}+-{np.std(bs):.4f} | Wolff exact {gw:.4f} sampled {gw_s:.4f}+-{np.std(bw):.4f}  build {tb:.1f}s")
        out[f"{name}_b{beta}"] = dict(sw_exact=gsw, sw_sampled=gsw_s, sw_boot_sd=float(np.std(bs)), wolff_exact=gw,
                                      wolff_sampled=gw_s, wolff_boot_sd=float(np.std(bw)), rowsum_err=max(rs, rw),
                                      stationarity_err=st, sym_err=max(asw, assw), pi_err=pich)
json.dump(out, open("results/validate.json", "w"), indent=1)
