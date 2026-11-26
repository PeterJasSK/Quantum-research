"""Claim 2 (D4 native-subset U) attack. Same instances/embedding/draws as D4 native_subset.py (fam_sk seeds 0-4, n=8,10,
qmc.draw_params(0,16)). Adds: (a) stronger classical incl. tuned local+uniform mixture, exact block heat-bath (full-E
conditional) on all pairs / native edges / native connected subtrees of size 3,4, and a tree independence sampler that
uses the same native couplings (exact O(n) sampling on a tree, Hastings accept with full E); (b) per-draw global
depolarizing F_k = (1-2e-3)^N2q_k with N2q_k = 2*edges*r(t_k) (r from D4 SK n=10 Trotter table), optional readout factor;
(c) short-t variant t~U[2,6]. -> results/claim2.jsonl, results/claim2_Q_n8.npz"""
import itertools
import json
import sys
import time

import numpy as np

import e3lib as L
qmc = L.qmc
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D4-compilation")
import d4lib as D  # noqa: E402
from native_subset import best_embedding  # noqa: E402

E2Q, RO = 2e-3, 1.67e-2
BETAS = (0.3, 1.0)
g16, t16 = qmc.draw_params(0, 16)
tshort = np.random.default_rng(1).uniform(2, 6, 16)
saveQ = {}
fh = open("results/claim2.jsonl", "w")
for n in (8, 10):
    U = qmc.uniform_Q(n)
    for seed in range(5):
        t0 = time.time()
        J, h = D.fam_sk(n, seed)
        w, kept = best_embedding(J)
        Js = np.zeros_like(J)
        for i, j in kept:
            Js[i, j] = Js[j, i] = J[i, j]
        E, Enat = qmc.ising_energies(J, h), qmc.ising_energies(Js, h)
        rec = dict(n=n, seed=seed, edges=len(kept))
        Qs = {}
        for tag, ts in (("long", t16), ("short", tshort)):
            Qk = [qmc.quantum_Q(Enat, [g], [t]) for g, t in zip(g16, ts)]
            N2q = np.array([2 * len(kept) * L.r_of_t(t) for t in ts])
            F = (1 - E2Q) ** N2q
            Fro = F * (1 - RO) ** n
            rec[f"N2q_mean_{tag}"] = float(N2q.mean()); rec[f"F_mean_{tag}"] = float(F.mean())
            Qs[f"ideal_{tag}"] = np.mean(Qk, 0)
            Qs[f"noisy_{tag}"] = np.mean([f * q + (1 - f) * U for f, q in zip(F, Qk)], 0)
            Qs[f"noisyro_{tag}"] = np.mean([f * q + (1 - f) * U for f, q in zip(Fro, Qk)], 0)
        Qs["decoh_long"] = qmc.decohered_Q(Enat, g16, t16)
        pairs = list(itertools.combinations(range(n), 2))
        sub3 = L.connected_subtrees(kept, n, 3)
        sub4 = L.connected_subtrees(kept, n, 4)
        rec["n_sub3"], rec["n_sub4"] = len(sub3), len(sub4)
        for b in BETAS:
            cl = {}
            cl["mix"], rec[f"mixw_b{b}"], _ = L.best_mix(E, b, n)
            cl["pairHB"], _ = L.hb_mixed_with_uniform(L.block_hb_P(E, b, pairs), E, b, n)
            cl["natpairHB"], _ = L.hb_mixed_with_uniform(L.block_hb_P(E, b, [tuple(e) for e in kept]), E, b, n)
            cl["natsub3HB"], _ = L.hb_mixed_with_uniform(L.block_hb_P(E, b, sub3), E, b, n)
            cl["natsub4HB"], _ = L.hb_mixed_with_uniform(L.block_hb_P(E, b, sub4), E, b, n)
            PL = qmc.mh_matrix(qmc.local_Q(n), E, b)
            gi = []
            for f in (0.5, 1.0):
                g_, P_ = L.tree_indep_gap(E, Enat, b, f * b)
                gi += [g_, L.gap_P(0.5 * P_ + 0.5 * PL, E, b)]
            cl["treeIndep"] = max(gi)
            for k, v in cl.items():
                rec[f"gap_{k}_b{b}"] = v
            best_old = max(cl["mix"], qmc.gap(qmc.local_Q(n), E, b), qmc.gap(U, E, b))
            best = max(cl.values())
            rec[f"best_kind_b{b}"] = max(cl, key=cl.get)
            for k, Q in Qs.items():
                gq = qmc.gap(Q, E, b)
                rec[f"S_{k}_vs_mix_b{b}"] = gq / cl["mix"]
                rec[f"S_{k}_vs_best_b{b}"] = gq / best
        if n == 8:
            saveQ[f"s{seed}_noisy_long"] = Qs["noisy_long"]; saveQ[f"s{seed}_ideal_long"] = Qs["ideal_long"]
            saveQ[f"s{seed}_noisy_short"] = Qs["noisy_short"]
        rec["secs"] = round(time.time() - t0, 1)
        fh.write(json.dumps(rec) + "\n"); fh.flush()
        print(n, seed, rec["secs"], {k: round(v, 3) for k, v in rec.items() if k.startswith("S_") and "b1.0" in k},
              rec["best_kind_b1.0"], flush=True)
np.savez_compressed("results/claim2_Q_n8.npz", **saveQ)
