"""D3 sweep: exact noisy proposal matrices Q (density matrix, all inputs) for one instance.

python sweep.py --family sk --n 6 --seed 100 --noises dep,deph,ad,adgp,adtw --eps 1e-4,3e-4,1e-3,2e-3,5e-3,1e-2
Saves cache/<family>n<n>_s<seed>.npz with Q_ideal (Trotter grid), Q_<noise>_<eps>, gate counts.
eps = average 2q gate infidelity. dep: 2q depolarizing lambda2 = 4/3 eps, 1q lambda1 = 2*(eps/10).
deph: Z-dephasing p = eps per qubit per 2q gate, eps/10 per 1q gate.  ad: amplitude damping gamma = eps per
qubit per 2q gate, eps/10 per 1q gate.  adgp: ad averaged over gauge pair {0, all-ones} (literal gauge
transform of the problem + relabel).  adtw: ad replaced by its exact Pauli twirl.  adsplit: ad, split placement.
Grid: gamma in --gammas x t in --ts, each grid point used with equal probability (Q = grid average).
"""
import argparse
import json
import os
import time
import numpy as np
import dmsim as D
import qmc

ap = argparse.ArgumentParser()
ap.add_argument("--family", default="sk")
ap.add_argument("--n", type=int, default=6)
ap.add_argument("--seed", type=int, default=100)
ap.add_argument("--noises", default="dep,deph,ad,adgp,adtw")
ap.add_argument("--eps", default="1e-4,3e-4,1e-3,2e-3,5e-3,1e-2")
ap.add_argument("--gammas", default="0.3,0.5")
ap.add_argument("--ts", default="2,6")
ap.add_argument("--c64", action="store_true")
ap.add_argument("--chunk", type=int, default=0)
ap.add_argument("--tag", default="")
a = ap.parse_args()

if a.family == "sk":
    J, h = qmc.sk_instance(a.n, a.seed)
else:                                   # 2D EA 3x3 periodic gauss, no field
    L = int(round(np.sqrt(a.n)))
    J, h = qmc.ea_instance(L, L, a.seed)
n = len(h)
gammas = [float(x) for x in a.gammas.split(",")]
ts = [float(x) for x in a.ts.split(",")]
grid = [(g, t) for g in gammas for t in ts]
dtype = np.complex64 if a.c64 else np.complex128
chunk = a.chunk or None
os.makedirs("cache", exist_ok=True)
out = f"cache/{a.family}n{n}_s{a.seed}{a.tag}.npz"
store = dict(np.load(out)) if os.path.exists(out) else {}


def units_for(Jx, hx, g, t):
    u, info = D.trotter_units(Jx, hx, g, t)
    assert D.is_palindrome(u)
    return u


def noise_dict(kind, e):
    if kind == "dep":
        return dict(dep2=4 / 3 * e, dep1=2 * e / 10)
    if kind == "deph":
        return dict(deph2=e, deph1=e / 10)
    if kind in ("ad", "adgp", "adsplit"):
        return dict(ad2=e, ad1=e / 10)
    if kind == "adtw":
        return dict(ad2=e, ad1=e / 10, twirl_ad=True)
    raise ValueError(kind)


def Q_grid(kind, e):
    Qs = []
    for g, t in grid:
        if kind == "adgp":
            acc = 0
            for m in (0, 2 ** n - 1):
                Jm, hm = D.gauge(J, h, m)
                acc = acc + D.relabel(D.noisy_Q(units_for(Jm, hm, g, t), n, noise_dict(kind, e),
                                                "after", dtype, chunk), m)
            Qs.append(acc / 2)
        else:
            pl = "split" if kind == "adsplit" else "after"
            Qs.append(D.noisy_Q(units_for(J, h, g, t), n, noise_dict(kind, e), pl, dtype, chunk))
    return np.mean(Qs, 0)


if "Q_ideal" not in store:
    Qs, n2, n1, ut = [], [], [], []
    for g, t in grid:
        u = units_for(J, h, g, t)
        U = D.ideal_unitary(u, n)
        ut.append(float(np.abs(U - U.T).max()))
        Qs.append(np.abs(U) ** 2)
        c2, c1 = D.gate_counts(u)
        n2.append(c2)
        n1.append(c1)
    store["Q_ideal"] = np.mean(Qs, 0)
    store["n2q"] = np.array(n2)
    store["n1q"] = np.array(n1)
    store["UT_err"] = np.array(ut)
    store["grid"] = np.array(grid)
    np.savez_compressed(out, **store)

log = []
for kind in a.noises.split(","):
    for e in [float(x) for x in a.eps.split(",")]:
        key = f"Q_{kind}_{e:g}"
        if key in store:
            continue
        t0 = time.time()
        store[key] = Q_grid(kind, e)
        dt = time.time() - t0
        np.savez_compressed(out, **store)
        log.append(dict(key=key, sec=round(dt, 1), asym=qmc.asymmetry(store[key])))
        print(json.dumps(log[-1]), flush=True)
