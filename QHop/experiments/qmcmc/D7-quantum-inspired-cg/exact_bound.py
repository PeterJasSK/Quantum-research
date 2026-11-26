"""Exact-matrix check (SK n=10) of the own-calculation bound: for the SAME state-independent group choice,
any group proposal + MH (quantum, decohered, ...) has  gap <= 2 * gap(block heat-bath)  and
tau_f >= (tau_f(HB) - 1)/2 for every observable f. Ideal (noiseless) exact linear algebra."""
import json
import numpy as np
import cg  # noqa: F401  (puts harness on path)
import qmc

n = 10
gam, ts = qmc.draw_params(0, 16)
_qQ = qmc.quantum_Q


def hb_matrix(J, h, groups, beta):
    dim = 2 ** n
    E = qmc.ising_energies(J, h)
    P = np.zeros((dim, dim))
    for G in groups:
        mask = int(np.bitwise_or.reduce(1 << np.asarray(G)))
        sub = np.array([sum(((gb >> i) & 1) << G[i] for i in range(len(G))) for gb in range(2 ** len(G))])
        for a in range(dim):
            tgt = (a & ~mask) | sub
            w = np.exp(-beta * (E[tgt] - E[tgt].min()))
            P[a, tgt] += w / w.sum() / len(groups)
    return P


def tau_exact(P, pi, f):
    f = f - pi @ f
    A = np.eye(len(pi)) - P + np.outer(np.ones(len(pi)), pi)
    g = np.linalg.solve(A, f)  # (I-P)^-1 f on mean-zero
    var = pi @ (f * f)
    return float((2 * pi @ (f * g) - var) / var)


rows = []
for seed in range(1, 6):
    J, h = qmc.sk_instance(n, seed)
    E = qmc.ising_energies(J, h)
    S = qmc.spins(n)
    for k in [4, 6]:
        groups = [[(r + a) % n for a in range(k)] for r in range(n)]
        qmc.quantum_Q = _qQ
        Qq = qmc.coarse_grained_Q(J, h, groups, gammas=gam, ts=ts)
        qmc.quantum_Q = lambda Hp, g, t, Hm=None: qmc.decohered_Q(Hp, g, t, Hm=Hm)
        Qd = qmc.coarse_grained_Q(J, h, groups, gammas=gam, ts=ts)
        qmc.quantum_Q = _qQ
        for bb in [0.5, 1.0, 3.0]:
            beta = bb / np.sqrt(n)
            pi = qmc.boltzmann(E, beta)
            gs = np.argmin(E)
            ham = (S != S[gs]).sum(1).astype(float)
            out = dict(seed=seed, k=k, beta_over_betac=bb)
            Phb = hb_matrix(J, h, groups, beta)
            for name, P in [("hb", Phb), ("q", qmc.mh_matrix(Qq, E, beta)), ("dec", qmc.mh_matrix(Qd, E, beta))]:
                out[f"gap_{name}"] = float(qmc.spectral_gap(P, pi))
                out[f"tauE_{name}"] = tau_exact(P, pi, E.astype(float))
                out[f"tauH_{name}"] = tau_exact(P, pi, ham)
            out["gap_ratio_q_hb"] = out["gap_q"] / out["gap_hb"]
            out["tauE_ratio_hb_q"] = out["tauE_hb"] / out["tauE_q"]
            out["tauH_ratio_hb_q"] = out["tauH_hb"] / out["tauH_q"]
            out["gap_ratio_dec_hb"] = out["gap_dec"] / out["gap_hb"]
            rows.append(out)
            print(seed, k, bb, "gap q/hb %.3f dec/hb %.3f  tauE hb/q %.3f tauH hb/q %.3f" % (
                out["gap_ratio_q_hb"], out["gap_ratio_dec_hb"], out["tauE_ratio_hb_q"], out["tauH_ratio_hb_q"]),
                flush=True)
json.dump(rows, open(cg.HERE + "/results/exact_bound_n10.json", "w"), indent=1)
import csv
with open(cg.HERE + "/results/exact_bound_n10.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
print("max gap ratio q/hb", max(r["gap_ratio_q_hb"] for r in rows), "max tau ratio hb/q",
      max(max(r["tauE_ratio_hb_q"], r["tauH_ratio_hb_q"]) for r in rows))
