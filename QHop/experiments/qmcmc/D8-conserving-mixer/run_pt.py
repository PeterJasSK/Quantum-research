"""Parallel tempering with any-pair swaps (R=8 replicas, geometric T_target..5 Tc) vs single chains, simulated IATs.
Round = one any-pair-swap Metropolis proposal in every replica + one replica-exchange attempt on alternating pairs.
IAT of E, NN-SRO (unlike-bond fraction) and ground-state overlap |q| at the target replica, in rounds; per-proposal
cost-normalised IAT = rounds x R. Cross-check: simulated quantum chain (complete-graph XY, exact Q) and any-pair chain for
seed 0 vs the exact IATs from run_gaps.
Usage: OMP_NUM_THREADS=2 python run_pt.py <fam> [seeds=5] [rounds=200000] -> results/pt_<fam>.jsonl
"""
import json
import sys
import time

import numpy as np

import d8lib as L
import qmc

fam = sys.argv[1]
nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 5
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
n, k, L1, L2, R = 12, 6, 3, 4, 8
states, index, occ = L.sector(n, k)
D = len(states)
_, pos, nn, nnn = L.torus(L1, L2)
_, nb_all = L.hop_matrix(states, index, L.complete_edges(n))
NB = np.array(nb_all).T  # (D, 66), -1 where like pair
NBR = np.array([row[row >= 0] for row in NB])  # (D, 36) unlike-pair swaps
sro = np.mean([occ[:, i] != occ[:, j] for (i, j) in nn], axis=0)
s_occ = 2 * occ - 1


def pt(E, betas, rounds, seed):
    rng = np.random.default_rng(seed)
    a = rng.integers(D, size=R)
    rep = np.arange(R)
    trace = np.empty(rounds, np.int64)
    nacc_sw = np.zeros(R - 1)
    natt_sw = np.zeros(R - 1)
    B = 10000
    for b0 in range(0, rounds, B):
        J = rng.integers(NBR.shape[1], size=(B, R))
        U1 = rng.random((B, R))
        U2 = rng.random((B, R - 1))
        for s in range(min(B, rounds - b0)):
            prop = NBR[a, J[s]]
            dE = E[prop] - E[a]
            ok = (dE <= 0) | (U1[s] < np.exp(-betas * np.maximum(dE, 0)))
            a = np.where(ok, prop, a)
            par = (b0 + s) % 2
            for r in range(par, R - 1, 2):
                d = (betas[r] - betas[r + 1]) * (E[a[r]] - E[a[r + 1]])
                natt_sw[r] += 1
                if d >= 0 or U2[s, r] < np.exp(d):
                    a[r], a[r + 1] = a[r + 1], a[r]
                    nacc_sw[r] += 1
            trace[b0 + s] = a[0]
    return trace, nacc_sw / np.maximum(natt_sw, 1)


out = open(f"results/pt_{fam}.jsonl", "w")
for seed in range(nseeds):
    t0 = time.time()
    J, _ = {"cuau": lambda: L.fam_cuau(L1, L2, seed), "coulomb": lambda: L.fam_coulomb(L1, L2, seed),
            "sk": lambda: L.fam_sk(n, seed)}[fam]()
    E = L.pair_energy(occ, J)
    Tc, _ = L.find_Tc(E, n)
    q = np.abs(s_occ @ s_occ[int(np.argmin(E))]) / n
    for tr in (1.1, 0.5):
        Ts = np.geomspace(tr * Tc, 5 * Tc, R)
        betas = 1 / Ts
        tr_idx, swacc = pt(E, betas, ROUNDS, 100 + seed)
        burn = ROUNDS // 10
        x = tr_idx[burn:]
        rec = dict(fam=fam, seed=seed, Tc=Tc, T_over_Tc=tr, R=R, rounds=ROUNDS, swap_acc=swacc.round(3).tolist(),
                   pt_iat_rounds=dict(E=qmc.iat(E[x]), sro=qmc.iat(sro[x]), q=qmc.iat(q[x])))
        rec["pt_iat_per_proposal"] = {kk: v * R for kk, v in rec["pt_iat_rounds"].items()}
        if seed == 0:  # simulated single-chain cross-checks
            alpha = np.sqrt(n) / np.std(E)
            H, _ = L.hop_matrix(states, index, L.complete_edges(n))
            gam, ts = L.draw(seed, 24)
            Qq = L.quantum_Q(E, H * L.mixer_scale(H, n), gam, ts, alpha)
            Qa = L.swap_Q(nb_all, D)
            for name, Q in (("q_complete", Qq), ("anypair_swap", Qa)):
                y = qmc.run_chain(Q, E, betas[0], ROUNDS, 200 + seed)[burn:]
                rec[f"sim_{name}_iat"] = dict(E=qmc.iat(E[y]), sro=qmc.iat(sro[y]), q=qmc.iat(q[y]))
        out.write(json.dumps(rec) + "\n")
        out.flush()
    print(fam, seed, f"{time.time()-t0:.0f}s", flush=True)
out.close()
