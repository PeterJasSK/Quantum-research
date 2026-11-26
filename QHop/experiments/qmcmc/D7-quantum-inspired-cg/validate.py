"""Correctness checks for the C kernels: Bessel, statevector evolution vs scipy expm, energy bookkeeping,
exact Boltzmann stationarity (TV distance) of every move type on small instances."""
import json
import os
import numpy as np
from scipy.special import jv
from scipy.linalg import expm
import cg
import qmc

out = {}
# 1 Bessel
err = 0
for x in [0.3, 2.5, 17.0, 120.0, 380.0]:
    M = int(x + 6 * x ** (1 / 3) + 25)
    b = cg.test_bessel(x, M)
    err = max(err, np.max(np.abs(b - jv(np.arange(M + 1), x))))
out["bessel_max_abs_err"] = float(err)

# 2 evolution vs expm
rng = np.random.default_rng(0)
errs = []
for k in [3, 5, 8]:
    D = 2 ** k
    Hm = qmc.mixer(k)
    for trial in range(3):
        d = rng.normal(size=D) * np.sqrt(k)
        gam, t, x0 = rng.uniform(0.25, 0.6), rng.uniform(2, 20), int(rng.integers(D))
        p = cg.test_evolve(d, gam, t, x0)
        U = expm(-1j * t * (np.diag(d) + gam * Hm))
        errs.append(np.max(np.abs(p - np.abs(U[:, x0]) ** 2)))
        p2 = cg.test_evolve(d, gam, 0.25, x0)
        U2 = expm(-1j * 0.25 * (np.diag(d) + gam * Hm))
        errs.append(np.max(np.abs(p2 - np.abs(U2[:, x0]) ** 2)))
out["evolve_max_abs_err_prob"] = float(max(errs))

# 3 stationarity: SK n=8 at beta = 1/sqrt(8)*2 ; EA 3x3 for PT/Houdayer
def tv_from_states(inst, beta, states):
    n = inst.n
    S = qmc.spins(n)
    E = qmc.ising_energies(inst.J, inst.h)
    pi = np.exp(-beta * (E - E.min())); pi /= pi.sum()
    idx = ((states < 0).astype(int) * (1 << np.arange(n))).sum(1)
    emp = np.bincount(idx, minlength=2 ** n) / len(idx)
    return 0.5 * np.abs(emp - pi).sum()

res = {}
inst = cg.Inst("sk", 8, 11)
beta = 2.0 / np.sqrt(8)
# use energy distribution: compare <E> and P(E-level) via full-state hist requires states; we instead
# collect the state through repeated short runs: chain_run records only E,H -> compare energy histogram
E_all = qmc.ising_energies(inst.J, inst.h)
pi = np.exp(-beta * (E_all - E_all.min())); pi /= pi.sum()
Emean_exact = float(pi @ E_all)
levels = np.round(E_all, 8)
def tv_energy(rec):
    u, inv = np.unique(levels, return_inverse=True)
    p_exact = np.bincount(inv, weights=pi)
    r = np.round(rec, 6)
    # map each recorded energy to nearest level
    j = np.searchsorted(u, r)
    j = np.clip(j, 0, len(u) - 1)
    jm = np.clip(j - 1, 0, len(u) - 1)
    pick = np.where(np.abs(u[jm] - r) < np.abs(u[j] - r), jm, j)
    p_emp = np.bincount(pick, minlength=len(u)) / len(pick)
    return 0.5 * np.abs(p_emp - p_exact).sum()

for method, k, gm in [("metro", 0, "block"), ("hb", 3, "block"), ("hb", 4, "subset"), ("hb", 3, "cluster"),
                      ("q", 3, "block"), ("q", 4, "subset"), ("q", 4, "cluster"), ("dec", 3, "block")]:
    r = cg.chain(inst, method, beta, tlimit=6.0 if method in ("q", "dec") else 3.0, seed=5, k=k, gmode=gm,
                 moves_per_rec=1)
    # bookkeeping check
    e_end = inst.energy(r["s"])
    res[f"{method}_k{k}_{gm}"] = dict(nrec=len(r["E"]), Emean=float(r["E"][1000:].mean()),
                                      Eexact=Emean_exact, tv_energy=float(tv_energy(r["E"][1000:])),
                                      bookkeeping_err=abs(e_end - r["E"][-1]))
# reference: TV of an iid sample of the same size from exact pi (noise floor)
g = np.random.default_rng(1)
for N in [20000, 200000]:
    smp = g.choice(len(E_all), N, p=pi)
    res[f"iid_noise_floor_N{N}"] = float(tv_energy(E_all[smp]))

# PT / Houdayer on EA 3x3 at several temps
ea = cg.Inst("ea", 3, 3)
Eea = qmc.ising_energies(ea.J, ea.h)
betas = np.geomspace(0.5, 3.0, 5)
for hd in [False, True]:
    r = cg.pt(ea, betas, 4, tlimit=3.0, seed=7, houdayer=hd)
    p = np.exp(-3.0 * (Eea - Eea.min())); p /= p.sum()
    res[f"pt_houd{hd}"] = dict(nrec=len(r["E"]), Emean=float(r["E"][1000:].mean()), Eexact=float(p @ Eea),
                               swap=r["swap"].tolist(), houd_size=r["houd_size"])
out["stationarity"] = res
json.dump(out, open(os.path.join(cg.HERE, "results", "validate.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
