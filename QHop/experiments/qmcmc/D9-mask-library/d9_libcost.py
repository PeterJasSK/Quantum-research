"""Wall-clock cost to BUILD classical mask libraries of size L with the real procedures (not exact-law sampling),
SK n=12 and n=100 (to show scaling), plain numpy on this shared laptop (upper bound; C would be ~10-100x faster).
Run: python d9_libcost.py -> results/libcost.txt
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d9lib as D  # noqa: E402
from d9lib import qmc  # noqa: E402

here = os.path.dirname(os.path.abspath(__file__))
lines = []
for n in (12, 100):
    J, h = qmc.sk_instance(n, 1)
    for L in (1024, 8192):
        rng = np.random.default_rng(0)
        # (f) basin difference: 2L greedy steepest descents from random starts, batched
        t = time.time()
        S = rng.choice([-1, 1], size=(2 * L, n)).astype(float)
        for _ in range(10 * n):
            loc = S @ J + h  # local field; dE of flipping i = 2 s_i loc_i
            dE = 2 * S * loc
            i = dE.argmin(1)
            down = dE[np.arange(len(S)), i] < 0
            if not down.any():
                break
            S[np.nonzero(down)[0], i[down]] *= -1
        masks = (S[:L] != S[L:])
        tf = time.time() - t
        # (g) percolation clusters at beta=1 (law sampler = real procedure)
        t = time.time()
        if n <= 16:
            D.percolation_law(J, 1.0, n, L, 1)
        tg = time.time() - t if n <= 16 else np.nan
        # (e) DE masks need pairs from an equilibrated population: cost = PT/MCMC sweeps; estimate with
        # 2L samples x (10 sweeps decorrelation) x n proposals x 30 ns (A5 bench C cost); not run here.
        te = 2 * L * 10 * n * 30e-9
        lines.append(f"n={n} L={L}: basin-diff (f) {tf:.3f} s numpy | percolation (g) {tg:.3f} s numpy | "
                     f"DE (e) ~{te:.2e} s C-estimate (2L samples x 10 sweeps x n x 30 ns, assumes PT already mixes)")
        lines.append(f"   quantum library (b): L x 0.25-0.85 ms = {L*0.25e-3:.2f}-{L*0.85e-3:.2f} s QPU + job overhead ~2-3 s;"
                     f" price at $48-96/QPU-min: ${L*0.25e-3/60*48:.2f}-${L*0.85e-3/60*96:.2f}")
open(f"{here}/results/libcost.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
