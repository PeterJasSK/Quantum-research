"""Reproduction #6 (AC-8): Gu's perturbed coin [D06] and Wu's PMD processes [D16], analytic.

    python -m D_quantum_growth.repro.causal_states_repro

Gu: C_q(p) = H2((1 + 2 sqrt(p(1-p)))/2) < C_mu = 1 for 0 < p < 1, p != 1/2; D06 prints "p > 0.2: C_q < 0.5" and
"p > 0.4: C_q < 0.1". Wu: PMD survival Phi(n) = Gamma^n (1 - V sin^2(n pi / N)): D_mu = log2 N grows, the 1-qubit Kraus
model of D16 SM S1 is statistically exact (survival error ~1e-16) with D_q = 1 for every N; parameters of D16 Fig. 5
(Gamma = 0.5, V = 0.4, N = 3..8).
"""
from __future__ import annotations

import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from D_quantum_growth.src import causal_states as C
from shared import RE_ROOT

FIGDIR = RE_ROOT / "D_quantum_growth" / "figures"
LABEL = "analytic (no simulation): exact theory"


def main() -> None:
    p = np.linspace(0.001, 0.999, 400)
    cq = np.array([C.gu_perturbed_coin(x)["C_q"] for x in p])
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    ax.plot(p, np.ones_like(p), "k--", label="C_mu = 1 bit (classical)")
    ax.plot(p, cq, label="C_q(p) (quantum)")
    ax.axvline(0.2, color="gray", lw=0.6, ls=":"); ax.axvline(0.4, color="gray", lw=0.6, ls=":")
    ax.set_xlabel("perturbation p"); ax.set_ylabel("memory (bits)")
    ax.set_title(f"Gu perturbed coin ({LABEL})", fontsize=8); ax.legend()
    fig.tight_layout(); fig.savefig(FIGDIR / "gu_perturbed_coin.png", dpi=130)

    gu = {x: C.gu_perturbed_coin(x)["C_q"] for x in (0.1, 0.2, 0.3, 0.4, 0.5)}
    print("Gu perturbed coin (C_mu = 1):")
    for x, v in gu.items():
        print(f"  p={x:.1f}  C_q={v:.4f}")
    ok_gu = gu[0.2] < 0.5 and gu[0.4] < 0.1
    print(f"  D06 printed: C_q < 0.5 for p > 0.2, C_q < 0.1 for p > 0.4  ->  {'MATCH' if ok_gu else 'MISMATCH'}"
          f" (C_q(0.2)={gu[0.2]:.4f}, C_q(0.4)={gu[0.4]:.4f})")

    rows = []
    print("\nWu PMD family (Gamma = 0.5, V = 0.4):")
    print("   N  n_causal  D_mu   D_q   C_mu    C_q     max|Phi_model - Phi|")
    for N in range(2, 17):
        cc = C.classical_complexity(0.5, 0.4, N)
        m = C.wu_model(0.5, 0.4, N)
        cq_, dq = C.wu_cq(m, cc["pi"])
        err = C.wu_check(m, 0.5, 0.4, N)["max_survival_err"]
        rows.append({"N": N, "n_causal": cc["n_causal"], "D_mu": cc["D_mu"], "D_q": dq, "C_mu": cc["C_mu"],
                     "C_q": cq_, "survival_err": err})
        print(f"  {N:2d}  {cc['n_causal']:3d}      {cc['D_mu']:.2f}  {dq:.0f}   {cc['C_mu']:.3f}  {cq_:.4f}   {err:.1e}")
    ok_wu = all(r["D_q"] <= 1 and abs(r["D_mu"] - np.log2(r["N"])) < 1e-9 and r["survival_err"] < 1e-9 for r in rows)
    print(f"  D16: D_mu = log2 N grows, D_q <= 1 qubit for every N, statistically exact  ->  {'MATCH' if ok_wu else 'MISMATCH'}")

    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    Ns = [r["N"] for r in rows]
    ax.plot(Ns, [r["D_mu"] for r in rows], "o-", label="D_mu = log2 N (classical bits)")
    ax.plot(Ns, [r["D_q"] for r in rows], "s-", label="D_q (qubits)")
    ax.plot(Ns, [r["C_mu"] for r in rows], "^--", label="C_mu"); ax.plot(Ns, [r["C_q"] for r in rows], "v--", label="C_q")
    ax.set_xlabel("period N"); ax.set_ylabel("memory (bits / qubits)")
    ax.set_title(f"Wu PMD processes, Gamma=0.5, V=0.4 ({LABEL})", fontsize=8); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIGDIR / "wu_pmd_memory.png", dpi=130)
    (FIGDIR / "causal_states_summary.json").write_text(json.dumps(
        {"label": LABEL, "gu": {str(k): v for k, v in gu.items()}, "gu_match": bool(ok_gu), "wu": rows,
         "wu_match": bool(ok_wu)}, indent=1))


if __name__ == "__main__":
    main()
