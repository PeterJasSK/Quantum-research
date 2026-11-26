"""Exp 4 (K14 negative control): binary MRF segmentation on a 3x4 open grid, exact gaps.

True label image: left/right split with a random vertical boundary column and a random flipped pixel;
observation o_i = s_i + N(0, sn^2); data term h_i = lam * o_i / sn^2 ... we use h_i = o_i / sn^2 * 0.5 (Gaussian
likelihood, means +-1, folded with a 1/2 so the data term is comparable to J). E(s) = -J sum_<ij> s_i s_j - h.s,
J = 1. Temperature: beta_peak from the exact specific heat per instance (the MEDIUM point), and beta in
{0.5, 1, 2} x beta_peak. Classical best = max(local, uniform, local+uniform, exact Swendsen-Wang with field,
SW+local). Quantum = QeMCMC on E (Layden params), decohered control.

Usage: python exp4_mrf.py --inst 10 --sn 1.0 --out ...
"""
import argparse
import json
import time
import numpy as np
import d6lib as d
import qmc

R, C = 3, 4
EDGES = [(r * C + c, r * C + c + 1) for r in range(R) for c in range(C - 1)] + \
        [(r * C + c, (r + 1) * C + c) for r in range(R - 1) for c in range(C)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", type=int, default=10)
    ap.add_argument("--sn", type=float, default=1.0)
    ap.add_argument("--J", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = R * C
    pairs = d.layden_draws(0)
    rows, t0 = [], time.time()
    for inst in range(a.inst):
        rng = np.random.default_rng([64, inst, int(a.sn * 100)])
        bcol = rng.integers(1, C)
        s0 = np.array([1 if (i % C) < bcol else -1 for i in range(n)])
        s0[rng.integers(n)] *= -1
        o = s0 + a.sn * rng.normal(size=n)
        h = 0.5 * o / a.sn ** 2
        Jv = np.full(len(EDGES), a.J)
        Jm = np.zeros((n, n))
        for (u, v) in EDGES:
            Jm[u, v] = Jm[v, u] = a.J
        E = qmc.ising_energies(Jm, h)
        bpk = d.beta_peak(E, n)
        kern = d.QKern(E)
        Qq, Qd = kern.Qavg(pairs), kern.decohered(pairs)
        QL, QU = d.local_Q(n), d.uniform_Q(n)
        for fac in (0.5, 1.0, 2.0):
            beta = fac * bpk
            ASW, asym, Esw = d.exact_sw_A(EDGES, Jv, h, beta)
            assert np.allclose(Esw - Esw.min(), E - E.min(), atol=1e-9)
            AL, AU = d.A_sym(QL, E, beta), d.A_sym(QU, E, beta)
            res = dict(inst=inst, beta=beta, beta_over_peak=fac, beta_peak=bpk, sw_asym=asym, sn=a.sn)
            for name, A in (("L", AL), ("U", AU), ("LU", 0.5 * (AL + AU)), ("SW", ASW), ("SWL", 0.5 * (ASW + AL)),
                            ("Q", d.A_sym(Qq, E, beta)), ("D", d.A_sym(Qd, E, beta))):
                res[f"g_{name}"], res[f"ga_{name}"] = d.gaps(A)
            best = max(res[f"g_{k}"] for k in ("L", "U", "LU", "SW", "SWL"))
            res.update(best_classical=best, S=res["g_Q"] / best, S_vs_SW=res["g_Q"] / res["g_SW"],
                       S_weak=res["g_Q"] / max(res["g_L"], res["g_U"], res["g_LU"]), S_dec=res["g_D"] / best)
            rows.append(res)
        print(f"inst={inst} t={time.time()-t0:.0f}s", flush=True)
    json.dump(rows, open(a.out, "w"))
    print("done", len(rows), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
