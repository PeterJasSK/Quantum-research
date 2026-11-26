"""Run every D2 sampler on one instance. Usage: python run_instance.py FAMILY N SEED [--noq]
Writes results/<family>_n<N>_s<SEED>.json. Quantum parts are wall-time capped (caps below, scaled with n);
the number of steps actually run is stored with every IAT so reliability (N/tau) can be checked."""
import json
import os
import sys
import time

import numpy as np

import d2lib as L
import qmc

fam, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
noq = "--noq" in sys.argv
os.makedirs(os.path.join(L.HERE, "results"), exist_ok=True)
outp = os.path.join(L.HERE, "results", f"{fam}_n{n}_s{seed}.json")
T0 = time.time()
CAP = {12: 45, 14: 75}.get(n, 75)  # seconds per quantum-chain run (pure chain gets 2x)
PQS = {"Q": [0.01, 0.1, 0.5, 1.0], "D": [0.1, 1.0]}  # decohered: reduced set (machine overload)

inst = L.Instance(fam, n, seed)
bc, Cmax = inst.beta_c()
regs = {"LOW": 3 * bc, "MED": bc, "HIGH": 0.3 * bc}
res = dict(family=fam, n=n, seed=seed, beta_c=bc, Cmax=Cmax, Egs=inst.Egs, alpha=inst.alpha, regimes={})


def iats(E, q):
    return dict(tauE=qmc.iat(E), tauQ=qmc.iat(q), N=len(E))


def log(*a):
    print(f"[{fam}{n}s{seed} {time.time() - T0:7.0f}s]", *a, flush=True)


# local-gap collapse marker: Metropolis tau_E (flips) on a beta grid (cheap, C)
grid = bc * np.array([0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
res["metro_tau_grid"] = []
for b in grid:
    E, q = L.metro(inst, b, 4_000_000, n, seed + 7)
    res["metro_tau_grid"].append([float(b), qmc.iat(E[len(E) // 10:]) * n])

qs = None if noq else L.QSampler(inst, seed=seed + 11)
ds = None if noq else L.DSampler(inst, seed=seed + 13)

for reg, beta in regs.items():
    Eex, Cex = inst.exact(beta)
    r = dict(beta=beta, E_exact=Eex, C_exact=Cex, q_exact=inst.exact_q(beta))
    # (1) single-spin Metropolis
    if reg == "HIGH":
        E, q = L.metro(inst, beta, 2_000_000, 1, seed + 21)
        d = iats(E[1000:], q[1000:])
        d["unit"] = "flip"
        d["tauE_flips"], d["tauQ_flips"] = d["tauE"], d["tauQ"]
    else:
        E, q = L.metro(inst, beta, 40_000_000 * n // 16, n, seed + 21)
        d = iats(E[len(E) // 10:], q[len(E) // 10:])
        d["unit"] = "sweep"
        d["tauE_flips"], d["tauQ_flips"] = d["tauE"] * n, d["tauQ"] * n
    d["N_flips"] = len(E) * (1 if reg == "HIGH" else n)
    Em = np.array([L.metro(inst, beta, 4096 * n, n, seed + 1000 + c)[0] for c in range(32)])
    d["t_eq_flips"] = L.t_equil(Em, Eex) * n
    d["E_mean"] = float(E[len(E) // 10:].mean())
    r["metro"] = d
    log(reg, "metro", round(d["tauE_flips"], 1), round(d["tauQ_flips"], 1))
    # (2) tuned PT (HIGH: a ladder is not needed -> PT == Metropolis, R=1)
    if reg == "HIGH":
        betas, sw, hist = np.array([beta]), [], []
    else:
        betas, sw, hist = L.tune_ladder(inst, 0.3 * bc, beta, seed + 31)
    pt = L.PT(inst, betas, seed + 41)
    pt.run(5000, record=False)
    pt.reset_stats()
    NS = 200_000 if n <= 16 else 100_000
    E, q = pt.run(NS)
    d = iats(E, q)
    cps = pt.cost_per_sweep()
    d.update(betas=betas.tolist(), swap=pt.swap_rates(), tune_hist=hist, cost_per_sweep=cps,
             tauE_flips=d["tauE"] * cps, tauQ_flips=d["tauQ"] * cps, E_mean=float(E.mean()))
    Em = []
    for c in range(32):
        p2 = L.PT(inst, betas, seed + 2000 + c)
        Em.append(p2.run(2048)[0])
    d["t_eq_flips"] = L.t_equil(np.array(Em), Eex) * cps
    r["pt"] = d
    log(reg, "PT R", len(betas), "swap", np.round(pt.swap_rates(), 2), "tau(flips)", round(d["tauE_flips"]),
        round(d["tauQ_flips"]))
    # (3) PT + Houdayer (2 copies) for 2D EA
    if fam == "ea":
        ph = L.PT(inst, betas, seed + 51, ncopy=2, houdayer=True)
        ph.run(5000, record=False)
        ph.reset_stats()
        E, q = ph.run(NS)
        d = iats(E, q)
        cps = ph.cost_per_sweep()
        d.update(cost_per_sweep=cps, tauE_flips=d["tauE"] * cps, tauQ_flips=d["tauQ"] * cps,
                 mean_cluster=float(ph.hstat[1] / max(ph.hstat[0], 1)), swap=ph.swap_rates(), E_mean=float(E.mean()))
        Em = []
        for c in range(32):
            p2 = L.PT(inst, betas, seed + 3000 + c, ncopy=2, houdayer=True)
            Em.append(p2.run(2048)[0])
        d["t_eq_flips"] = L.t_equil(np.array(Em), Eex) * cps
        r["pt_houdayer"] = d
        log(reg, "PT+H tau(flips)", round(d["tauE_flips"]), round(d["tauQ_flips"]))
    if noq:
        res["regimes"][reg] = r
        continue
    # (4) pure QeMCMC chain (time-capped)
    rng = np.random.default_rng(seed + 61)
    a = int(rng.integers(1 << n))
    Es, As, nacc, t1 = [], [], 0, time.time()
    while len(Es) < 20000 and time.time() - t1 < 2 * CAP:
        for _ in range(100):
            b = qs.propose(a)
            dE = inst.E[b] - inst.E[a]
            if b != a and (dE <= 0 or rng.random() < np.exp(-beta * dE)):
                a, nacc = b, nacc + 1
            Es.append(inst.E[a])
            As.append(a)
    Es, As = np.array(Es), np.array(As)
    burn = min(200, len(Es) // 10)
    d = iats(Es[burn:], L.inst_q(inst, As[burn:]))
    d.update(acc=nacc / len(Es), wall=time.time() - t1, E_mean=float(Es[burn:].mean()))
    # QeMCMC equilibration: M chains in lockstep from random starts (capped)
    M, Tq = (16, 256) if n <= 14 else (8, 128)
    st = [int(x) for x in np.random.default_rng(seed + 71).integers(1 << n, size=M)]
    tr, t1, rr = [], time.time(), np.random.default_rng(seed + 72)
    while len(tr) < Tq and time.time() - t1 < CAP:
        for c in range(M):
            b = qs.propose(st[c])
            dE = inst.E[b] - inst.E[st[c]]
            if dE <= 0 or rr.random() < np.exp(-beta * dE):
                st[c] = b
        tr.append([inst.E[x] for x in st])
    tr = np.array(tr).T
    d["t_eq_steps"] = L.t_equil(tr, Eex)
    d["t_eq_T"] = tr.shape[1]
    r["qemcmc"] = d
    log(reg, "QeMCMC tau", round(d["tauE"], 1), round(d["tauQ"], 1), "N", d["N"], "acc", round(d["acc"], 3),
        "teq", d["t_eq_steps"], qs.stats())
    # (4b) pure decohered-control chain (same generator, dephased every dt), time-capped
    rng = np.random.default_rng(seed + 63)
    a = int(rng.integers(1 << n))
    Es, As, nacc, t1 = [], [], 0, time.time()
    while len(Es) < 20000 and time.time() - t1 < CAP:
        for _ in range(100):
            b = ds.propose(a)
            dE = inst.E[b] - inst.E[a]
            if b != a and (dE <= 0 or rng.random() < np.exp(-beta * dE)):
                a, nacc = b, nacc + 1
            Es.append(inst.E[a])
            As.append(a)
    Es, As = np.array(Es), np.array(As)
    burn = min(200, len(Es) // 10)
    d = iats(Es[burn:], L.inst_q(inst, As[burn:]))
    d.update(acc=nacc / len(Es), wall=time.time() - t1, E_mean=float(Es[burn:].mean()))
    r["decohered"] = d
    log(reg, "decohered tau", round(d["tauE"], 1), round(d["tauQ"], 1), "N", d["N"], "acc", round(d["acc"], 3))
    # (5)/(6) PT with quantum / decohered move on the coldest k replicas with prob p_q per sweep
    k = min(2, len(betas))
    slots = list(range(len(betas) - k, len(betas)))
    hyb = {}
    cap_h = CAP if reg != "HIGH" else CAP / 2
    if reg == "HIGH" and n > 12:
        r["hybrid"] = {}
        res["regimes"][reg] = r
        continue
    for kind, smp in [("Q", qs), ("D", ds)]:
        for pq in PQS[kind]:
            ph = L.PT(inst, betas, seed + 81)
            ph.run(2000, record=False)
            ph.reset_stats()
            rq = np.random.default_rng(seed + 91)
            NSH = 50000
            ev = rq.random((NSH, k)) < pq
            evs = np.nonzero(ev.any(1))[0]
            Es, Qq, nq, nqa, t1, done = np.zeros(NSH), np.zeros(NSH), 0, 0, time.time(), 0
            for e in list(evs) + [NSH - 1]:
                if e < done:
                    continue
                e1, q1 = ph.run(e + 1 - done)
                Es[done:e + 1], Qq[done:e + 1] = e1, q1
                done = e + 1
                for j, sl in enumerate(slots):
                    if ev[e, j]:
                        nq += 1
                        nqa += ph.qmove(sl, smp, rq)
                if time.time() - t1 > cap_h:
                    break
            d = iats(Es[:done], Qq[:done])
            d.update(p_q=pq, k=k, n_qmoves=nq, q_acc=nqa / max(nq, 1), cost_classical_per_sweep=ph.cost_per_sweep(),
                     qmoves_per_sweep=nq / done, wall=time.time() - t1, swap=ph.swap_rates(),
                     E_mean=float(Es[:done].mean()))
            hyb[f"{kind}{pq}"] = d
            log(reg, f"PT+{kind} pq={pq} tau", round(d["tauE"], 2), round(d["tauQ"], 2), "N", done, "qacc",
                round(d["q_acc"], 3))
    r["hybrid"] = hyb
    r["qs_stats"], r["ds_stats"] = qs.stats(), ds.stats()
    res["regimes"][reg] = r
    json.dump(res, open(outp, "w"), indent=1, default=float)

res["wall_s"] = time.time() - T0
json.dump(res, open(outp, "w"), indent=1, default=float)
log("done")
