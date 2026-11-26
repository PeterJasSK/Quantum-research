"""D3 analysis: regimes, gaps, bias, eps*, fit of a.  python analyze.py  -> results/*.csv, results/summary.json, plots/*.png"""
import glob
import json
import os
import re
import numpy as np
import dmsim as D
import qmc

os.makedirs("results", exist_ok=True)
os.makedirs("plots", exist_ok=True)
EPS = [1e-4, 3e-4, 1e-3, 2e-3, 5e-3, 1e-2]
RO_P = [1e-3, 3e-3, 1e-2, 2e-2, 5e-2]
BG = np.logspace(-2, 1, 61)


def stationary(P):
    w, V = np.linalg.eig(P.T)
    k = np.argmin(np.abs(w - 1))
    p = np.real(V[:, k])
    return p / p.sum()


def chain_metrics(Q, E, beta, symmetric):
    pi = qmc.boltzmann(E, beta)
    P = qmc.mh_matrix(Q, E, beta)
    if symmetric:
        g_plain = qmc.spectral_gap(P, pi)
        tvd = kl = 0.0
    else:
        lam = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
        g_plain = float(1 - lam[1])
        ps = np.clip(stationary(P), 1e-300, None)
        tvd = float(0.5 * np.abs(ps - pi).sum())
        kl = float(np.sum(pi * np.log(pi / ps)))
    Ph = qmc.mh_matrix(Q, E, beta, hastings=True)
    g_h = g_plain if symmetric else qmc.spectral_gap(Ph, pi)   # Hastings chain is reversible w.r.t. pi
    return g_plain, g_h, tvd, kl


def regimes(E, n):
    C = qmc.thermo(E, n, BG)
    bc = float(BG[np.argmax(C)])
    gl = qmc.local_gap_curve(E, n, BG)
    k0 = int(np.argmax(gl))
    below = np.where(gl[k0:] < 0.5 * gl[k0])[0]
    bloc = float(BG[k0 + below[0]]) if len(below) else float("nan")
    return bc, bloc, {"HIGH": bc / 3, "MEDIUM": bc, "LOW": 3 * bc}


def classical_best(n, E, beta):
    L, U = qmc.local_Q(n), qmc.uniform_Q(n)
    cands = {"local": L, "uniform": U}
    for w in (0.25, 0.5, 0.75):
        cands[f"mix{w}"] = w * L + (1 - w) * U
    gs = {k: qmc.gap(v, E, beta) for k, v in cands.items()}
    k = max(gs, key=gs.get)
    return gs[k], k


def row_tvd(A, B):
    return float(0.5 * np.abs(A - B).sum(1).mean())


def feff(Q, Qi):
    d = len(Q)
    U = np.full_like(Q, 1 / d)
    A, Bm = (Qi - U).ravel(), (Q - U).ravel()
    f = float(A @ Bm / (A @ A))
    res = np.linalg.norm(Bm - f * A) / np.linalg.norm(Bm)
    return f, float(res)


def Fproxy(e, n2, n1):
    return float(np.mean((1 - e) ** n2 * (1 - e / 10) ** n1))


rows = []
inst_info = []


def add_rows(meta, Qd, Qi, E, n, regs, best):
    for name, (Q, extra) in Qd.items():
        asym = qmc.asymmetry(Q)
        sym = asym < 1e-9
        fe, res = feff(Q, Qi)
        for rg, b in regs.items():
            gp, gh, tvd, kl = chain_metrics(Q, E, b, sym)
            gb, kb = best[rg]
            rows.append(dict(meta, variant=name, **extra, regime=rg, beta=b, asym=asym,
                             tvd_ideal=row_tvd(Q, Qi), tvd_unif=row_tvd(Q, np.full_like(Q, 1 / len(Q))),
                             F_eff=fe, gdep_resid=res, gap_plain=gp, gap_hast=gh, gap_best_classical=gb,
                             best_classical=kb, S_plain=gp / gb, S_hast=gh / gb, bias_tvd=tvd, bias_kl=kl))


# ------------------------------------------------------------------ exact DM caches (sk n6, n8, ea)
for f in sorted(glob.glob("cache/*n*_s*.npz")):
    if os.path.basename(f).startswith("fake_"):
        continue
    fam, n, seed = re.match(r"cache/(\w+?)n(\d+)_s(\d+)\.npz", f).groups()
    n, seed = int(n), int(seed)
    z = dict(np.load(f))
    J, h = qmc.sk_instance(n, seed) if fam == "sk" else qmc.ea_instance(3, 3, seed)
    E = qmc.ising_energies(J, h)
    bc, bloc, regs = regimes(E, n)
    best = {rg: classical_best(n, E, b) for rg, b in regs.items()}
    grid = z["grid"]
    gam, ts = sorted(set(grid[:, 0])), sorted(set(grid[:, 1]))
    n2, n1 = z["n2q"], z["n1q"]
    inst_info.append(dict(family=fam, n=n, seed=seed, source="exactDM", beta_c_Cpeak=bc, beta_loc_half=bloc, **{f"beta_{k}": v for k, v in regs.items()},
                          grid=grid.tolist(), n2q=n2.tolist(), n1q=n1.tolist(), UT_err=float(z["UT_err"].max()),
                          best_classical={k: v[1] for k, v in best.items()}))
    Qi = z["Q_ideal"]
    Qd = {"ideal": (Qi, dict(noise="none", eps=0.0, F=1.0))}
    gg, tt = qmc.draw_params(0, 16)
    Qd["P1_exact_m16"] = (qmc.quantum_Q(E, gg, tt), dict(noise="none", eps=0.0, F=1.0))
    Qd["decohered_grid"] = (qmc.decohered_Q(E, grid[:, 0], grid[:, 1]), dict(noise="decohered", eps=np.inf, F=0.0))
    for k, Q in z.items():
        m = re.match(r"Q_(\w+?)_([\d.e-]+)$", k)
        if m:
            e = float(m.group(2))
            Qd[k[2:]] = (Q, dict(noise=m.group(1), eps=e, F=Fproxy(e, n2, n1)))
    for p in RO_P:                                # readout, analytic on the ideal Trotter Q
        Qs = D.readout_apply(Qi, n, p, p)
        Qd[f"rosym_{p:g}"] = (Qs, dict(noise="rosym", eps=p, F=np.nan))
        Qd[f"roasym_{p:g}"] = (D.readout_apply(Qi, n, 0.5 * p, 1.5 * p), dict(noise="roasym", eps=p, F=np.nan))
        # fix: readout twirl (-> symmetric flip pbar=p) + mirrored classical input pre-flip with the same flip
        Qd[f"rofix_{p:g}"] = (D.prep_apply(D.readout_apply(Qi, n, p, p), n, p, p), dict(noise="rofix", eps=p, F=np.nan))
    add_rows(dict(family=fam, n=n, seed=seed, source="exactDM"), Qd, Qi, E, n, regs, best)
    print(f, "done", flush=True)

# ------------------------------------------------------------------ fake backends (Aer DM, n=6, grid t=2)
for f in sorted(glob.glob("cache/fake_*.npz")):
    bk, n, seed = re.match(r"cache/fake_(\w+)_n(\d+)_s(\d+)\.npz", f).groups()
    n, seed = int(n), int(seed)
    z = dict(np.load(f))
    J, h = qmc.sk_instance(n, seed)
    E = qmc.ising_energies(J, h)
    bc, bloc, regs = regimes(E, n)
    best = {rg: classical_best(n, E, b) for rg, b in regs.items()}
    Qs = []
    for g, t in z["grid"]:
        u, _ = D.trotter_units(J, h, g, t)
        Qs.append(np.abs(D.ideal_unitary(u, n)) ** 2)
    Qi = np.mean(Qs, 0)
    Qd = {"ideal_t2": (Qi, dict(noise="none", eps=0.0, F=1.0))}
    for k in ("Q_noRO", "Q_RO", "Q_gp_noRO", "Q_gp_RO"):
        if k in z:
            Qd[f"{bk}_{k[2:]}"] = (z[k], dict(noise=f"fake_{bk}", eps=np.nan, F=np.nan, cz=float(np.mean(z["cz"]))))
    if "Q_RO" in z:   # Hastings-free fix attempt: gauge pair + mirrored symmetric pre-flip of mean readout
        pbar = float(np.mean(z["ro"]))
        if "Q_gp_RO" in z:
            Qd[f"{bk}_gp_RO_mirror"] = (D.prep_apply(z["Q_gp_RO"], n, pbar, pbar),
                                        dict(noise=f"fake_{bk}", eps=np.nan, F=np.nan, cz=float(np.mean(z["cz"]))))
    add_rows(dict(family="sk", n=n, seed=seed, source=f"aer_{bk}"), Qd, Qi, E, n, regs, best)
    print(f, "done", flush=True)

# ------------------------------------------------------------------ global-depolarizing model, n = 6, 8, 10 (t grid 2,6)
for fam, n, seeds in [("sk", 6, range(100, 105)), ("sk", 8, range(100, 105)), ("sk", 10, range(100, 105)),
                      ("ea", 9, range(200, 205))]:
    for seed in seeds:
        J, h = qmc.sk_instance(n, seed) if fam == "sk" else qmc.ea_instance(3, 3, seed)
        E = qmc.ising_energies(J, h)
        bc, bloc, regs = regimes(E, n)
        best = {rg: classical_best(n, E, b) for rg, b in regs.items()}
        Qs, n2, n1 = [], [], []
        for g in (0.3, 0.5):
            for t in (2.0, 6.0):
                u, _ = D.trotter_units(J, h, g, t)
                Qs.append(np.abs(D.ideal_unitary(u, n)) ** 2)
                c2, c1 = D.gate_counts(u)
                n2.append(c2)
                n1.append(c1)
        Qi = np.mean(Qs, 0)
        n2, n1 = np.array(n2), np.array(n1)
        U = np.full_like(Qi, 1 / len(Qi))
        Qd = {"ideal": (Qi, dict(noise="none", eps=0.0, F=1.0))}
        for e in EPS:
            # per grid point F_k, Q = mean_k [F_k Q_k + (1-F_k) U]  (symmetric -> plain chain unbiased)
            Fk = (1 - e) ** n2 * (1 - e / 10) ** n1
            Qm = np.mean([F * Qk + (1 - F) * U for F, Qk in zip(Fk, Qs)], 0)
            Qd[f"gdep_{e:g}"] = (Qm, dict(noise="gdepmodel", eps=e, F=float(Fk.mean())))
        add_rows(dict(family=fam, n=n, seed=seed, source="model_global_dep"), Qd, Qi, E, n, regs, best)
        inst_info.append(dict(family=fam, n=n, seed=seed, source="model", beta_c_Cpeak=bc, beta_loc_half=bloc,
                              **{f"beta_{k}": v for k, v in regs.items()}, n2q=n2.tolist(), n1q=n1.tolist(),
                              best_classical={k: v[1] for k, v in best.items()}))
        print("model", fam, n, seed, flush=True)

import csv  # noqa: E402
keys = sorted({k for r in rows for k in r})
with open("results/all_rows.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
json.dump(inst_info, open("results/instances.json", "w"), indent=1)
print("rows", len(rows))
