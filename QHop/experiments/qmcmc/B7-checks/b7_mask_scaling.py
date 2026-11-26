"""Preliminary n-scaling of V24 (mask donation) vs P1 QeMCMC, local, uniform. SK, beta=1, exact gaps.
Fits gap ~ 2^(-k n) by least squares on log2(median gap) over n. Run: python b7_mask_scaling.py
"""
import sys
import numpy as np
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

beta = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
ns = [4, 5, 6, 7, 8, 9, 10]
seeds = [101, 102, 103, 104, 105]
rows = {k: [] for k in ("quantum", "mask_pi", "mask_unif", "local", "uniform")}
for n in ns:
    g = {k: [] for k in rows}
    d = 2 ** n
    idx = np.arange(d)
    for sd in seeds:
        J, h = qmc.sk_instance(n, sd)
        E = qmc.ising_energies(J, h)
        pi = qmc.boltzmann(E, beta)
        ga, ts = qmc.draw_params(sd, 20)
        Q = qmc.quantum_Q(E, ga, ts)
        g["quantum"].append(qmc.gap(Q, E, beta))
        for name, rho in (("mask_pi", pi), ("mask_unif", np.full(d, 1.0 / d))):
            M = np.zeros(d)
            for r in range(d):
                M += rho[r] * Q[r, r ^ idx]
            g[name].append(qmc.gap(M[idx[:, None] ^ idx[None, :]], E, beta))
        g["local"].append(qmc.gap(qmc.local_Q(n), E, beta))
        g["uniform"].append(qmc.gap(qmc.uniform_Q(n), E, beta))
    for k in rows:
        rows[k].append(np.median(g[k]))
    print(f"n={n:2d} " + " ".join(f"{k}={rows[k][-1]:.3e}" for k in rows), flush=True)
print(f"beta={beta}: fitted k in gap ~ 2^(-k n), median over {len(seeds)} SK instances, n={ns[0]}..{ns[-1]}")
for k, v in rows.items():
    slope = np.polyfit(ns, np.log2(v), 1)[0]
    print(f"  {k:10s} k={-slope:.3f}")
