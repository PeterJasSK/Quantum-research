"""Exact sector spectral gaps + exact IATs vs T/Tc for all proposals, one energy family per call.
Usage: OMP_NUM_THREADS=1 python run_gaps.py <cuau|coulomb|sk> [n=12] [seeds=5] [start_seed=0]  -> results/gaps_<fam>_n<n>.jsonl
"""
import json
import sys
import time

import numpy as np

import d8lib as L

fam = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
nseeds = int(sys.argv[3]) if len(sys.argv) > 3 else 5
seed0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0  # resume: append seeds seed0..nseeds-1
L1, L2 = (3, 4) if n == 12 else (2, 7)
k = n // 2
M_DRAWS = 24
IAT_T = (0.5, 1.1, 3.0)  # exact IATs (eigenvectors) only here; gap-only elsewhere
TR = [0.3, 0.5, 0.7, 0.9, 1.0, 1.1, 1.5, 2.0, 3.0, 5.0]

states, index, occ = L.sector(n, k)
D = len(states)
_, pos, nn, nnn = L.torus(L1, L2)
mixers = {"grid": nn, "ring": L.snake_ring(L1, L2), "complete": L.complete_edges(n)}
Hm, NB = {}, {}
for name, ed in mixers.items():
    H, nbs = L.hop_matrix(states, index, ed)
    Hm[name] = H * L.mixer_scale(H, n)
    NB[name] = nbs
Q_nn = L.swap_Q(NB["grid"], D)
Q_ap = L.swap_Q(NB["complete"], D)  # every one of the k(n-k) unlike pairs equally likely (complete graph edges)
classical = {"nn_kawasaki": Q_nn, "anypair_swap": Q_ap, "mix_nn_anypair": 0.5 * (Q_nn + Q_ap), "uniform": L.uniform_Q(D)}

s_occ = 2 * occ - 1
sro = np.mean([occ[:, i] != occ[:, j] for (i, j) in nn], axis=0)  # fraction of unlike NN bonds
alpha1 = 1.0 - 2.0 * sro  # Warren-Cowley NN SRO at c = 1/2

out = open(f"results/gaps_{fam}_n{n}.jsonl", "a" if seed0 > 0 else "w")
for seed in range(seed0, nseeds):
    t0 = time.time()
    if fam == "cuau":
        J, meta = L.fam_cuau(L1, L2, seed)
    elif fam == "coulomb":
        J, meta = L.fam_coulomb(L1, L2, seed)
    else:
        J, meta = L.fam_sk(n, seed)
    E = L.pair_energy(occ, J)
    Tc, cpk = L.find_Tc(E, n)
    gs = int(np.argmin(E))
    qov = np.abs(s_occ @ s_occ[gs]) / n
    alpha = np.sqrt(n) / np.std(E)
    gam, ts = L.draw(seed, M_DRAWS)
    props = dict(classical)
    for name in ("grid", "ring", "complete"):
        props["q_" + name] = L.quantum_Q(E, Hm[name], gam, ts, alpha)
    for name in ("grid", "complete"):
        props["deco_" + name] = L.decohered_Q(E, Hm[name], gam, ts, alpha)
    sym = {p: float(np.abs(Q - Q.T).max()) for p, Q in props.items()}
    rows = []
    for tr in TR:
        beta = 1.0 / (tr * Tc)
        rec = dict(fam=fam, n=n, seed=seed, Tc=Tc, Cpeak_per_site=cpk, T_over_Tc=tr, beta=beta, meta=meta)
        for p, Q in props.items():
            if tr in IAT_T:
                (tE, tS, tQ), g = L.exact_iat(Q, E, beta, [E, alpha1, qov])
            else:
                g, tE, tS, tQ = L.gap(Q, E, beta), np.nan, np.nan, np.nan
            rec[p] = dict(gap=g, iat_E=tE, iat_sro=tS, iat_q=tQ)
        rows.append(rec)
        out.write(json.dumps(rec) + "\n")
        out.flush()
    print(f"{fam} n={n} seed={seed} Tc={Tc:.4g} D={D} sym_maxdev={max(sym.values()):.1e} {time.time()-t0:.0f}s",
          flush=True)
out.close()
