"""Minimal second-order Trotter steps r so that the Trotter proposal stays within TVD 0.05 of the exact proposal.
Criterion: worst start state (max over rows) of TVD(Q_trot[s,:], Q_exact[s,:]), worst over gamma in {0.25,0.425,0.6}.
Also recorded: r for the row-averaged TVD criterion. Exact for all rows when dim <= 1024; sampled rows above (labelled).
Usage: python trotter_r.py [part]   (part in ising|potts|all)  -> results/trotter_r.jsonl
"""
import json
import sys
import time

import numpy as np

import d4lib as D

OUT = "results/trotter_r.jsonl"


def ising_jobs():
    J = []
    for n in range(4, 11):
        J += [("SK", n, s, lambda n=n, s=s: D.fam_sk(n, s)) for s in range(3)]
    for k in range(4, 11):
        J += [("CG", k, s, lambda k=k, s=s: D.fam_cg(k, s)) for s in range(3)]
    for n in range(6, 11):
        J += [("COUL", n, s, lambda n=n, s=s: D.fam_coulomb(n, s)) for s in range(3)]
    for L1, L2 in [(2, 2), (2, 3), (2, 4), (3, 3), (2, 5), (3, 4)]:
        J += [("EA", L1 * L2, s, lambda a=L1, b=L2, s=s: D.fam_ea(a, b, s)) for s in range(3)]
    for n in (6, 8, 10, 12):
        J += [("HH", n, s, lambda n=n, s=s: D.fam_hh(n, s)) for s in range(3)]
    return J


def run_ising(fh):
    for fam, n, seed, make in ising_jobs():
        J, h = make()
        N = 2 ** n
        rows = None if N <= 1024 else np.random.default_rng(n).choice(N, 128, replace=False)
        for g in D.GAMMAS:
            for t in D.TS:
                t0 = time.time()
                f = lambda rl: D.ising_rows(J, h, g, t, rl, rows)
                cache = {}
                rmx, _ = D.min_r(f, key=0, cache=cache)
                rmn, _ = D.min_r(f, key=1, cache=cache)
                rec = dict(family=fam, n=n, seed=seed, gamma=g, t=t, r_max=rmx, r_mean=rmn,
                           rows="all" if rows is None else len(rows), tvd_at_r=cache[rmx], secs=round(time.time() - t0, 2))
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
        print(fam, n, seed, flush=True)


def run_potts(fh):
    cases = [(2, 2, 3, (0, 1, 2), None), (2, 2, 4, (0, 1, 2), None), (2, 3, 3, (0, 1), None),
             (2, 3, 4, (0,), 64), (3, 3, 3, (0,), 16), (3, 3, 4, (0,), 4)]
    for L1, L2, q, seeds, nrow in cases:
        for seed in seeds:
            P = D.fam_potts(L1, L2, q, seed)
            N = q ** (L1 * L2)
            rows = np.arange(N) if nrow is None else np.random.default_rng(N).choice(N, nrow, replace=False)
            for g in D.GAMMAS:
                for t in D.TS:
                    t0 = time.time()
                    f = lambda rl: D.potts_rows(P, g, t, rl, rows)
                    cache = {}
                    rmx, _ = D.min_r(f, key=0, cache=cache)
                    rmn, _ = D.min_r(f, key=1, cache=cache)
                    rec = dict(family=f"POTTS{q}", n=L1 * L2 * q, sites=L1 * L2, grid=f"{L1}x{L2}", seed=seed, gamma=g, t=t,
                               r_max=rmx, r_mean=rmn, rows="all" if nrow is None else nrow, tvd_at_r=cache[rmx],
                               secs=round(time.time() - t0, 2))
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
            print("potts", L1, L2, q, seed, flush=True)


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    with open(OUT.replace(".jsonl", f"_{part}.jsonl"), "w") as fh:
        if part in ("ising", "all"):
            run_ising(fh)
        if part in ("potts", "all"):
            run_potts(fh)
