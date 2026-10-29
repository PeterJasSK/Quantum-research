"""Reproduce Layden et al. [B11]: spectral-gap scaling of quantum-enhanced MCMC on SK instances (ideal)."""
import argparse
import json

import numpy as np

from B_mapping.src.qemcmc import (draw_params, energies, local_Q, mh_matrix, quantum_Q, spectral_gap, uniform_Q)
from shared import RE_ROOT

LETTER_DIR = RE_ROOT / "B_mapping"
PAPER = {"quantum": 0.264, "local": 0.94, "uniform": 0.948}
TOL = {"quantum": 0.08, "local": 0.15, "uniform": 0.15}


def sk(n, g):
    J = np.triu(g.normal(size=(n, n)), 1)
    return J + J.T, g.normal(size=n)


def fit_k(ns, gaps):
    """<delta> ~ 2^(-k n): slope of log2 <delta> vs n."""
    return float(-np.polyfit(ns, np.log2(gaps), 1)[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--instances", type=int, default=100)
    ap.add_argument("--m", type=int, default=64)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    g = np.random.default_rng(a.seed)
    ns = list(range(3, 9))
    gaps = {k: [] for k in PAPER}
    for n in ns:
        acc = {k: [] for k in PAPER}
        for _ in range(a.instances):
            J, h = sk(n, g)
            E = energies(J, h)
            gam, ts = draw_params(g, a.m)
            acc["quantum"].append(spectral_gap(mh_matrix(quantum_Q(J, h, gam, ts), E)))
            acc["local"].append(spectral_gap(mh_matrix(local_Q(n), E)))
            acc["uniform"].append(spectral_gap(mh_matrix(uniform_Q(n), E)))
        for k in PAPER:
            gaps[k].append(float(np.mean(acc[k])))
        print(f"n={n}: <delta> " + "  ".join(f"{k}={gaps[k][-1]:.4f}" for k in PAPER), flush=True)
    ks = {k: fit_k(ns, gaps[k]) for k in PAPER}
    ok = {k: abs(ks[k] - PAPER[k]) <= TOL[k] for k in PAPER}
    for k in PAPER:
        print(f"[simulated: ideal] k_{k} = {ks[k]:.3f}  (paper {PAPER[k]}, tol {TOL[k]})  {'MATCH' if ok[k] else 'NO MATCH'}")
    out = {"sim_label": "simulated: ideal", "hardware": None, "ns": ns, "gaps": gaps, "k": ks, "paper": PAPER,
           "match": ok, "instances": a.instances, "M": a.m}
    (LETTER_DIR / "data" / "layden_result.json").write_text(json.dumps(out, indent=2) + "\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for k, mk in zip(PAPER, "osd"):
        ax.semilogy(ns, gaps[k], mk + "-", label=f"{k}: k={ks[k]:.2f} (paper {PAPER[k]})")
    ax.set_xlabel("n spins"); ax.set_ylabel("mean spectral gap")
    ax.set_title("Layden QeMCMC gap scaling, simulated: ideal", fontsize=9)
    ax.legend(fontsize=7); fig.tight_layout()
    fig.savefig(LETTER_DIR / "figures" / "layden_gap_scaling.png", dpi=150)


if __name__ == "__main__":
    main()
