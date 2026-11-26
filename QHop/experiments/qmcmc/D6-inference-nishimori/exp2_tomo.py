"""Exp 2 (B6-01): few-view binary tomography posterior, exact gaps.

Image x in {0,1}^N on an R x C grid (pixel i = r*C + c = spin/bit i; bit 1 = pixel on), x0 ~ iid Bernoulli(1/2)
(the prior; uniform prior => matched posterior has no prior term). Rays: rows, cols, diagonals (r-c const),
anti-diagonals (r+c const); V = 2, 3, 4 directions in that order. b = A x0 + sigma w.
E(x) = |A x - b|^2 / (2 sigma^2), matched beta = 1. Ghost-swap move: pick one of all axis-aligned rectangles
(r1<r2, c1<c2) uniformly and flip its 4 corner pixels (involution, uniform choice -> symmetric proposal; on a
checkerboard corner pattern it leaves all row and column sums invariant).

Usage: python exp2_tomo.py --R 3 --C 3 --views 2,3,4 --sigmas 0.2,0.35,0.5,0.75,1.0 --inst 10 --out ...
"""
import argparse
import json
import time
import itertools
import numpy as np
import d6lib as d


def ray_matrix(R, C, V):
    rays = []
    dirs = [lambda r, c: ("r", r), lambda r, c: ("c", c), lambda r, c: ("d", r - c), lambda r, c: ("a", r + c)]
    for k in range(V):
        keys = {}
        for r in range(R):
            for c in range(C):
                keys.setdefault(dirs[k](r, c), []).append(r * C + c)
        rays += list(keys.values())
    A = np.zeros((len(rays), R * C))
    for j, pix in enumerate(rays):
        A[j, pix] = 1.0
    return A


def ghost_masks(R, C):
    ms = []
    for r1, r2 in itertools.combinations(range(R), 2):
        for c1, c2 in itertools.combinations(range(C), 2):
            ms.append((1 << (r1 * C + c1)) | (1 << (r1 * C + c2)) | (1 << (r2 * C + c1)) | (1 << (r2 * C + c2)))
    return ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--R", type=int, default=3)
    ap.add_argument("--C", type=int, default=3)
    ap.add_argument("--views", default="2,3,4")
    ap.add_argument("--sigmas", default="0.2,0.35,0.5,0.75,1.0")
    ap.add_argument("--inst", type=int, default=10)
    ap.add_argument("--betas", default="1,2,4,8")
    ap.add_argument("--lean", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = a.R * a.C
    X = d.bits(n).astype(float)
    G = d.flip_Q(n, ghost_masks(a.R, a.C))
    betas = [float(b) for b in a.betas.split(",")]
    rows, t0 = [], time.time()
    for V in [int(v) for v in a.views.split(",")]:
        A = ray_matrix(a.R, a.C, V)
        for inst in range(a.inst):
            rng = np.random.default_rng([62, a.R, a.C, V, inst])
            x0 = rng.integers(0, 2, n)
            x0_idx = int(sum(int(x0[i]) << i for i in range(n)))
            w = rng.normal(size=A.shape[0])
            for sig in [float(s) for s in a.sigmas.split(",")]:
                b = A @ x0 + sig * w
                E = ((X @ A.T - b[None, :]) ** 2).sum(1) / (2 * sig ** 2)
                # count exact ghosts: states with identical noiseless projections to x0
                nghost = int((np.abs(X @ A.T - (A @ x0)[None, :]).sum(1) < 1e-9).sum())
                rows += d.evaluate(E, n, betas, structured={"G": ("sym", G)}, x0_index=x0_idx, lean=a.lean,
                                   extra=dict(R=a.R, C=a.C, views=V, inst=inst, sigma=sig, n=n,
                                              n_proj_equiv=nghost))
            print(f"V={V} inst={inst} t={time.time()-t0:.0f}s", flush=True)
    json.dump(rows, open(a.out, "w"))
    print("done", len(rows), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
