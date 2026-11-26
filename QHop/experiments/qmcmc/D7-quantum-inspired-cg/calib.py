"""Regime calibration: single-spin Metropolis specific heat C(beta) and energy IAT on a beta grid.
SK: beta/beta_c grid with beta_c = 1/sqrt(n) (to verify). EA 2D Gaussian: T grid, MEDIUM = T where IAT_E ~ 100 sweeps.
usage: python calib.py sk|ea"""
import json, sys
import numpy as np
import cg, qmc

fam = sys.argv[1]
rows = []
if fam == "sk":
    sizes, grid = [32, 64, 128], [0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0]
else:
    sizes, grid = [8, 12, 16], [3.0, 2.0, 1.5, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3]
for size in sizes:
    for seed in [1, 2, 3]:
        inst = cg.Inst(fam, size, seed)
        n = inst.n
        for g in grid:
            beta = g / np.sqrt(n) if fam == "sk" else 1.0 / g
            r = cg.chain(inst, "metro", beta, 2.0, 100 + seed, moves_per_rec=1)
            E = r["E"][len(r["E"]) // 3:]
            tau = qmc.iat(E)
            rows.append(dict(inst=inst.name, n=n, x=g, beta=beta, C=float(beta ** 2 * E.var() / n),
                             Emean_per_spin=float(E.mean() / n), tauE_sweeps=tau, nsweeps=len(r["E"])))
            print(inst.name, g, "C=%.3f tau=%.1f N=%d" % (rows[-1]["C"], tau, len(r["E"])), flush=True)
json.dump(rows, open(f"results/calib_{fam}.json", "w"), indent=1)
