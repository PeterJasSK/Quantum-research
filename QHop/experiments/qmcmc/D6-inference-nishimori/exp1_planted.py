"""Exp 1 (B4-04): planted BPSK posteriors y = A x0 + sigma w, exact gaps at matched and colder beta.

E(s) = |y - A s|^2 / (2 sigma^2): matched (Nishimori) posterior at beta = 1.
A: dense Gaussian N(0, 1/m) (unit column norm on average; CDMA/MIMO-like) or sparse (3 nonzeros per row,
N(0, 1/3) entries). alpha = m/n (measurement rate; CDMA load = 1/alpha, so alpha = 0.5 is 2x overloaded).
SNR_dB = 10 log10(1/sigma^2) per user. Same A, x0, w per instance across the SNR sweep.

Usage: python exp1_planted.py --family dense --n 10 --alphas 0.5,1,1.5,2 --snrs -3,0,3,6,10,14 --inst 10
"""
import argparse
import json
import time
import numpy as np
import d6lib as d
import qmc


def instance(family, n, alpha, inst):
    m = max(1, int(round(alpha * n)))
    rng = np.random.default_rng([6, {"dense": 0, "sparse": 1}[family], n, int(alpha * 10), inst])
    if family == "dense":
        A = rng.normal(0, 1 / np.sqrt(m), (m, n))
    else:
        A = np.zeros((m, n))
        for r in range(m):
            A[r, rng.choice(n, 3, replace=False)] = rng.normal(0, 1 / np.sqrt(3), 3)
        # rescale so columns have unit norm on average (same SNR meaning as dense)
        A *= np.sqrt(n / (A ** 2).sum())
    x0 = 1 - 2 * rng.integers(0, 2, n)
    w = rng.normal(size=m)
    return A, x0, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="dense")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--alphas", default="0.5,1,1.5,2")
    ap.add_argument("--snrs", default="-3,0,3,6,10,14")
    ap.add_argument("--inst", type=int, default=10)
    ap.add_argument("--inst0", type=int, default=0)
    ap.add_argument("--betas", default="1,2,4,8")
    ap.add_argument("--lean", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S = qmc.spins(a.n).astype(float)
    betas = [float(b) for b in a.betas.split(",")]
    rows = []
    t0 = time.time()
    for alpha in [float(x) for x in a.alphas.split(",")]:
        for inst in range(a.inst0, a.inst0 + a.inst):
            A, x0, w = instance(a.family, a.n, alpha, inst)
            x0_idx = int(sum(((1 - x0[i]) // 2) << i for i in range(a.n)))
            for snr in [float(x) for x in a.snrs.split(",")]:
                sig = 10 ** (-snr / 20)
                y = A @ x0 + sig * w
                R = y[None, :] - S @ A.T
                E = (R ** 2).sum(1) / (2 * sig ** 2)
                rows += d.evaluate(E, a.n, betas, x0_index=x0_idx, lean=a.lean,
                                   extra=dict(family=a.family, n=a.n, alpha=alpha, inst=inst, snr_db=snr,
                                              map_is_planted=bool(np.argmin(E) == x0_idx)))
            print(f"alpha={alpha} inst={inst} t={time.time()-t0:.0f}s", flush=True)
    json.dump(rows, open(a.out, "w"))
    print("done", len(rows), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
