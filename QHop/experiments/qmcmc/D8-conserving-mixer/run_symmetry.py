"""Symmetry / exact-stationarity checks: exact U^T=U, Q symmetry, |pi P - pi|_inf; Trotter palindromic vs non-palindromic
(ordered layers, scrambled 'transpiled' gate order) and the forward/reverse random-order fix.
Usage: OMP_NUM_THREADS=1 python run_symmetry.py -> results/symmetry.json
"""
import json
import time

import numpy as np
from scipy.linalg import expm

import d8lib as L
import qmc

n, k, L1, L2 = 12, 6, 3, 4
states, index, occ = L.sector(n, k)
D = len(states)
_, pos, nn, nnn = L.torus(L1, L2)


def round_robin(n):
    """Proper (n-1)-edge-colouring of K_n (n even)."""
    cols = []
    others = list(range(1, n))
    for r in range(n - 1):
        rot = others[r:] + others[:r]
        lay = [(0, rot[0])] + [(rot[i], rot[-i]) for i in range(1, n // 2)]
        cols.append([tuple(sorted(e)) for e in lay])
    return cols


def gate_apply(M, nb, th):
    """Left-multiply M by exp(-i th G_e) via row operations."""
    a = np.where(nb >= 0)[0]
    Ma = M[a].copy()
    Mb = M[nb[a]]
    M[a] = np.cos(th) * Ma - 1j * np.sin(th) * Mb
    return M


def circuit_U(seq, E, gamma, alpha):
    """seq = list of ('D', dtheta) or ('G', nb, theta) in TIME order; returns U = G_m ... G_1."""
    M = np.eye(D, dtype=complex)
    for g in seq:
        if g[0] == "D":
            M *= np.exp(-1j * g[1] * (1 - gamma) * alpha * E)[:, None]
        else:
            M = gate_apply(M, g[1], g[2])
    return M


def make_seq(layers_nb, gamma, t, r, scale, mode, rng=None):
    dt = t / r
    th = gamma * scale * dt
    seq = []
    flat = [nb for Lr in layers_nb for nb in Lr]
    perm = rng.permutation(len(flat)) if rng is not None else None
    for _ in range(r):
        if mode == "palindromic":
            seq.append(("D", dt / 2))
            for Lr in layers_nb[:-1]:
                seq += [("G", nb, th / 2) for nb in Lr]
            seq += [("G", nb, th) for nb in layers_nb[-1]]
            for Lr in layers_nb[-2::-1]:
                seq += [("G", nb, th / 2) for nb in Lr]
            seq.append(("D", dt / 2))
        elif mode == "ordered":  # first order, fixed layer order (typical compiled order, not palindromic)
            seq.append(("D", dt))
            for Lr in layers_nb:
                seq += [("G", nb, th) for nb in Lr]
        elif mode == "scrambled":  # first order, one fixed random gate order (transpiler-like reordering)
            seq.append(("D", dt))
            seq += [("G", flat[p], th) for p in perm]
    return seq


def stat_metrics(Q, E, beta, tv=True):
    pi = qmc.boltzmann(E, beta)
    P = qmc.mh_matrix(Q, E, beta)
    viol = float(np.abs(pi @ P - pi).max())
    if not tv:
        return viol, None
    w, V = np.linalg.eig(P.T)
    v = np.real(V[:, np.argmin(np.abs(w - 1))])
    v = v / v.sum()
    tv = float(0.5 * np.abs(v - pi).sum())
    return viol, tv


res = {"note": "max|.| entries; asym_rel = mean|Q-Q^T|/mean Q (qmc.asymmetry); stationarity at T/Tc=1.1 and 0.5"}
rng = np.random.default_rng(7)
for fam in ("cuau", "sk"):
    J, _ = L.fam_cuau(L1, L2, 0) if fam == "cuau" else L.fam_sk(n, 0)
    E = L.pair_energy(occ, J)
    Tc, _ = L.find_Tc(E, n)
    alpha = np.sqrt(n) / np.std(E)
    for mname, edges, layers in (("ring", L.snake_ring(L1, L2), None), ("complete", L.complete_edges(n), round_robin(n))):
        t0 = time.time()
        H, nbs = L.hop_matrix(states, index, edges)
        sc = L.mixer_scale(H, n)
        ed_nb = dict(zip([tuple(sorted(e)) for e in edges], nbs))
        layers = layers or L.edge_colouring([tuple(sorted(e)) for e in edges])
        layers_nb = [[ed_nb[tuple(sorted(e))] for e in Lr] for Lr in layers]
        gamma, t = 0.425, 10.0
        Hfull = np.diag((1 - gamma) * alpha * E) + gamma * sc * H
        U = expm(-1j * t * Hfull)
        Qx = np.abs(U) ** 2
        rec = {"Tc": Tc, "n_layers": len(layers), "gamma": gamma, "t": t,
               "exact": {"max_U_minus_UT": float(np.abs(U - U.T).max()), "max_Q_minus_QT": float(np.abs(Qx - Qx.T).max()),
                         "unitarity_err": float(np.abs(Qx.sum(1) - 1).max())}}
        for tr in (1.1, 0.5):
            v, tv = stat_metrics(Qx, E, 1 / (tr * Tc))
            rec["exact"][f"pi_viol_T{tr}"] = v
            rec["exact"][f"TV_T{tr}"] = tv
        for mode in ("palindromic", "ordered", "scrambled"):
            for r in (10, 30):
                seq = make_seq(layers_nb, gamma, t, r, sc, mode, rng if mode == "scrambled" else None)
                Uf = circuit_U(seq, E, gamma, alpha)
                Ur = circuit_U(seq[::-1], E, gamma, alpha)
                Qf, Qr = np.abs(Uf) ** 2, np.abs(Ur) ** 2
                Qfix = 0.5 * (Qf + Qr)
                row = {"max_Q_minus_QT": float(np.abs(Qf - Qf.T).max()), "asym_rel": qmc.asymmetry(Qf),
                       "rev_equals_transpose": float(np.abs(Qr - Qf.T).max()),
                       "fix_max_Q_minus_QT": float(np.abs(Qfix - Qfix.T).max()),
                       "rowTV_vs_exact": float(0.5 * np.abs(Qf - Qx).sum(1).mean())}
                for tr in (1.1, 0.5):
                    v, tv = stat_metrics(Qf, E, 1 / (tr * Tc), tv=(tr == 1.1 or mode != "palindromic"))
                    vf, tvf = stat_metrics(Qfix, E, 1 / (tr * Tc), tv=False)
                    row.update({f"pi_viol_T{tr}": v, f"TV_T{tr}": tv, f"fix_pi_viol_T{tr}": vf})
                rec[f"{mode}_r{r}"] = row
        res[f"{fam}_{mname}"] = rec
        print(fam, mname, f"{time.time()-t0:.0f}s", flush=True)
json.dump(res, open("results/symmetry.json", "w"), indent=1)
