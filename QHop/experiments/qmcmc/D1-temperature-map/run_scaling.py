"""SK gap scaling with n at fixed beta/beta_c in {0.5, 1, 3}.
Usage: python run_scaling.py N INSTANCE   -> results/scal_n<N>_i<INSTANCE>.json"""
import sys, json, time, math
import numpy as np
import d1lib as L
qmc = L.qmc
n, inst = int(sys.argv[1]), int(sys.argv[2])
T0 = time.time()
J, h = qmc.sk_instance(n, 1000 * n + inst)
E = qmc.ising_energies(J, h); dim = 2 ** n
bc, _ = L.beta_c_from_C(E, n)
ratios = np.array([0.5, 1.0, 3.0]); betas = bc * ratios
pis = [L.boltz(E, b) for b in betas]
gaps_of = lambda Q: [L.gap_sym(L.mh_sym(Q, E, b), p) for b, p in zip(betas, pis)]
res = dict(n=n, instance=inst, beta_c=bc, ratios=ratios.tolist(), betas=betas.tolist(), gaps={})
Ql, Qu = qmc.local_Q(n), qmc.uniform_Q(n)
res["gaps"]["local"] = gaps_of(Ql); res["gaps"]["uniform"] = gaps_of(Qu)
for w in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
    res["gaps"][f"mix_u{w}"] = gaps_of((1 - w) * Ql + w * Qu)
del Ql, Qu
K = L.QKern(E); lay = L.layden_draws(inst); m_t = 3 if n <= 10 else 2
Qlay = np.zeros((dim, dim))
# n=12: reduced tuning grid (machine overloaded; 4 gammas x 3 windows x 2 t) -- see README
GL = L.TUNE_G if n <= 11 else [0.1, L.TUNE_G[2], L.TUNE_G[4], 0.7] + [x for x in L.TUNE_G[2:6] if x not in (L.TUNE_G[2], L.TUNE_G[4])]
for g in GL:
    WL = L.TUNE_W if (n <= 11 or g in (0.1, L.TUNE_G[2], L.TUNE_G[4], 0.7)) else []
    if n > 11: WL = WL[:3]
    for j, w in enumerate(WL):
        res["gaps"][f"cell_g{g:.4f}_w{j}"] = gaps_of(K.Qavg([(g, tt) for tt in L.tune_ts(w, m_t)]))
    mine = [(gg, tt) for gg, tt in lay if abs(gg - g) < 1e-9]
    if mine:
        Qlay += K.Qavg(mine) * len(mine) / len(lay)
    K.cache.clear()
res["gaps"]["layden"] = gaps_of(Qlay); del Qlay, K
k = math.ceil(math.sqrt(n)); res["cg_k"] = k
res["gaps"][f"cg"] = gaps_of(L.coarse_grained_Q(J, h, L.cyclic_groups(n, k), lay))
res["time"] = time.time() - T0
json.dump(res, open(f"results/scal_n{n}_i{inst}.json", "w"))
print(n, inst, "%.0fs" % res["time"])
