"""Exact spectral gap vs beta for every proposal, one instance of one family.
Usage: python run_family.py FAMILY INSTANCE      FAMILY in sk10, ea34, ea33, fe34, fe33
Writes results/fam_<FAMILY>_i<INSTANCE>.json
"""
import sys, json, time
import numpy as np
import d1lib as L
qmc = L.qmc

fam, inst = sys.argv[1], int(sys.argv[2])
T0 = time.time()
if fam == "sk10":
    n = 10; J, h = qmc.sk_instance(n, 1000 * n + inst); zero_field = False
elif fam in ("ea34", "ea33"):
    L1, L2 = (3, 4) if fam == "ea34" else (3, 3)
    n = L1 * L2; J, h = qmc.ea_instance(L1, L2, 500 + inst, dist="pm"); zero_field = True
elif fam in ("fe34", "fe33"):
    L1, L2 = (3, 4) if fam == "fe34" else (3, 3)
    n = L1 * L2; J, h = qmc.ferro_instance(L1, L2); zero_field = True
else:
    raise SystemExit("unknown family")
E = qmc.ising_energies(J, h)
dim = 2 ** n
bc, Cmax = L.beta_c_from_C(E, n)
ratios = L.RATIOS if n <= 10 else L.RATIOS[[0, 2, 4, 5, 6, 7, 8, 10, 12]]
betas = bc * ratios
res = dict(family=fam, instance=inst, n=n, beta_c=bc, Cmax=Cmax, ratios=ratios.tolist(), betas=betas.tolist(),
           gaps={}, timing={})
pis = [L.boltz(E, b) for b in betas]


def gaps_of(Q):
    return [L.gap_sym(L.mh_sym(Q, E, b), p) for b, p in zip(betas, pis)]


def put(name, Q):
    t = time.time()
    res["gaps"][name] = gaps_of(Q)
    res["timing"]["gap_" + name] = time.time() - t


# local-gap collapse beta (fine grid, n<=10 only)
if n <= 10:
    bf = bc * 10 ** np.linspace(-1.5, 1.5, 61)
    gl = qmc.local_gap_curve(E, n, bf)
    imax = int(np.argmax(gl))
    below = np.nonzero(gl[imax:] < 0.1 * gl[imax])[0]
    res["beta_local_max"] = float(bf[imax])
    res["beta_local_collapse"] = float(bf[imax + below[0]]) if len(below) else None

# ---------------- classical
Ql, Qu = qmc.local_Q(n), qmc.uniform_Q(n)
Qf = np.zeros((dim, dim)); Qf[np.arange(dim), np.arange(dim) ^ (dim - 1)] = 1.0
put("local", Ql); put("uniform", Qu)
mix = {f"mix_u{w}": [(1 - w, Ql), (w, Qu)] for w in ((0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9) if n <= 10 else (0.05, 0.2, 0.5))}
if zero_field:
    mix["mix_f0.1"] = [(0.9, Ql), (0.1, Qf)]
    mix["mix_u0.1_f0.1"] = [(0.8, Ql), (0.1, Qu), (0.1, Qf)]
    mix["mix_u0.5_f0.1"] = [(0.4, Ql), (0.5, Qu), (0.1, Qf)]
for k, parts in mix.items():
    put(k, sum(w * Q for w, Q in parts))
del Qf

# ---------------- cluster moves (lattices: exact)
if fam != "sk10":
    t = time.time()
    nv, ed = L.graph_from_J(J, h)
    X = L.ExactCluster(nv, ed)
    res["timing"]["cluster_build"] = time.time() - t
    sw, wo, asym = [], [], []
    for b, p in zip(betas, pis):
        assert np.abs(X.pi(b) - p).max() < 1e-10
        A = X.sw_sym(b)
        sw.append(L.gap_sym(A, p)); del A
        g, a = L.gap_P_reversible(X.wolff_P(b), p)
        wo.append(g); asym.append(a)
    res["gaps"]["SW"] = sw; res["gaps"]["Wolff"] = wo
    res["wolff_max_asym"] = float(max(asym))
    res["timing"]["cluster_total"] = time.time() - t
    del X

# ---------------- quantum: Layden (stratified), tuning grid, decohered, per gamma to save memory
t = time.time()
K = L.QKern(E)
lay = L.layden_draws(inst)
m_t = 3 if n <= 10 else 2
Qlay = np.zeros((dim, dim)); Qdec = np.zeros((dim, dim))
band = {j: np.zeros((dim, dim)) for j in range(len(L.TUNE_W))}
lay_g = sorted({g for g, _ in lay})
band_cnt = {j: 0 for j in range(len(L.TUNE_W))}
# n=12: reduced tuning grid (machine overloaded; 4 gammas x 3 windows x 2 t) -- see README
GL = L.TUNE_G if n <= 11 else [0.1, L.TUNE_G[2], L.TUNE_G[4], 0.7] + [x for x in L.TUNE_G[2:6] if x not in (L.TUNE_G[2], L.TUNE_G[4])]
for g in GL:
    WL = L.TUNE_W if (n <= 11 or g in (0.1, L.TUNE_G[2], L.TUNE_G[4], 0.7)) else []
    if n > 11: WL = WL[:3]
    for j, w in enumerate(WL):
        Qc = K.Qavg([(g, tt) for tt in L.tune_ts(w, m_t)])
        put(f"cell_g{g:.4f}_w{j}", Qc)
        if any(abs(g - x) < 1e-9 for x in lay_g):
            band[j] += Qc; band_cnt[j] += 1
        if n <= 10 and g in (0.1, L.TUNE_G[2], L.TUNE_G[4], 0.7):
            Qd = K.decohered([(g, tt) for tt in L.tune_ts(w, m_t)])
            res["gaps"][f"deccell_g{g:.4f}_w{j}"] = gaps_of(Qd)
        del Qc
    mine = [(gg, tt) for gg, tt in lay if abs(gg - g) < 1e-9]
    if mine:
        Qlay += K.Qavg(mine) * len(mine) / len(lay)
        Qdec += K.decohered(mine) * len(mine) / len(lay)
    K.cache.clear(); K.Tcache.clear()
res["timing"]["quantum_build_and_cells"] = time.time() - t
put("layden", Qlay)
put("decohered_layden", Qdec)
res["layden_asym"] = qmc.asymmetry(Qlay)
for j in band:
    if band_cnt[j]:
        put(f"band_layden_g_w{j}", band[j] / band_cnt[j])
del band, Qdec, K

# ---------------- coarse-grained (P2), state-independent uniform group choice -> symmetric
ks = {12: (3, 4, 6), 10: (3, 5), 9: (3,)}[n]
for k in ks:
    t = time.time()
    Qc = L.coarse_grained_Q(J, h, L.cyclic_groups(n, k), L.layden_draws(inst))
    res[f"cg{k}_asym"] = qmc.asymmetry(Qc)
    put(f"cg{k}", Qc)
    res["timing"][f"cg{k}_total"] = time.time() - t
    del Qc

res["timing"]["total"] = time.time() - T0
json.dump(res, open(f"results/fam_{fam}_i{inst}.json", "w"))
print(fam, inst, "beta_c=%.4f" % bc, "total %.0fs" % res["timing"]["total"])
