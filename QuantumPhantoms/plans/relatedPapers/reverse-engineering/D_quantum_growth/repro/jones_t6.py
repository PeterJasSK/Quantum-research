"""Reproduction #7 (AC-12): Jones et al. 1-D Goldilocks rule T6 on a chain [D14].

    python -m D_quantum_growth.repro.jones_t6 [--tmax 15] [--heron-shots 2000] [--no-heron]

Rule T6 (D14 SM Eq. 3): H on site i iff exactly one neighbour is |1>, single central flip, |0> padding, sublattice of the centre
flip first, then the other, per cycle, compiled to CH = RY(pi/4) CZ RY(-pi/4). Ideal: L in {11, 15, 17, 23} by Aer statevector
(plan said matrix_product_state for 23; its 16-snapshot save_statevector was far slower than the 2^23 statevector). Heron-class noise: L = 11 only (the noisy 17-qubit run is not feasible: Aer
re-simulates every shot). Measures: population <n_j(t)>, MI network (Shannon, z basis) clustering coefficient C(t),
weighted path length, node strength, and the domain-wall invariant O(t) = sum Z_i Z_{i+1} (conserved by T6, D14 SM).
Paper values: D14 prints the emulated clustering of Fig. 3 only graphically (L = 15, 17, 19); the figure readings below
are +-0.03 (pixel reading), so agreement is checked at that tolerance, not at the +-0.02 the plan hoped for.
"""
from __future__ import annotations

import argparse
import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import transpile

from D_quantum_growth.src import heavyhex, qca
from shared import RE_ROOT
from shared.simbackend import fake_backend, make_simulator, sim_label

FIGDIR = RE_ROOT / "D_quantum_growth" / "figures"
# D14 Fig. 3, L = 17, blue "emulated" curve, read off the printed figure (pixel reading, +-0.03)
FIG3_L17 = {2: 0.09, 4: 0.19, 6: 0.26, 8: 0.30, 10: 0.31}


def heron_L(L: int, t_max: int, shots: int, seed: int = 11) -> dict:
    out = {"t": [], "pop": [], "C": [], "ell": [], "O": []}
    path = heavyhex.path(L)
    for t in range(t_max + 1):
        qc = qca.t6_circuit(L, t)
        qc.measure_all()
        tq = transpile(qc, backend=fake_backend(), initial_layout=path, optimization_level=1, seed_transpiler=seed)
        mem = make_simulator("heron").run(tq, shots=shots, seed_simulator=seed, memory=True).result().get_memory(0)
        bits = np.array([[int(c) for c in s[::-1]] for s in mem], float)[:, :L]
        p1 = bits.mean(0)
        p11 = (bits.T @ bits) / len(bits)
        I = qca.mi_matrix(p1, p11)
        out["t"].append(t); out["pop"].append(p1); out["C"].append(qca.clustering(I)); out["ell"].append(qca.path_length(I))
        zz = sum(np.mean((1 - 2 * bits[:, i]) * (1 - 2 * bits[:, i + 1])) for i in range(L - 1))
        out["O"].append(float(zz + np.mean(1 - 2 * bits[:, 0]) + np.mean(1 - 2 * bits[:, L - 1])))
        print(f"  heron L={L} t={t:2d} C={out['C'][-1]:.3f} O={out['O'][-1]:.2f}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tmax", type=int, default=15)
    ap.add_argument("--heron-shots", type=int, default=2000)
    ap.add_argument("--no-heron", action="store_true")
    a = ap.parse_args()
    ideal = {}
    for L in (11, 15, 17, 23):
        r = qca.t6_run(L, a.tmax, method="statevector")
        ideal[L] = r
        O = np.array(r["O"])
        print(f"ideal L={L}: O(t) conserved: max|O(t)-O(0)| = {np.abs(O - O[0]).max():.2e}; "
              f"C(t) = " + " ".join(f"{c:.3f}" for c in r["C"]), flush=True)
    heron = None if a.no_heron else heron_L(11, a.tmax, a.heron_shots)

    print("\nD14 Fig. 3 (L=17, emulated clustering, figure reading +-0.03):")
    cmp_rows = []
    for t, v in FIG3_L17.items():
        ours = ideal[17]["C"][t]
        cmp_rows.append({"t": t, "paper_figure": v, "ours_ideal": ours, "diff": ours - v})
        print(f"  t={t:2d}  paper~{v:.2f}  ours={ours:.3f}  diff={ours - v:+.3f}")
    ok = all(abs(r["diff"]) <= 0.03 for r in cmp_rows)
    print("agreement within figure-reading tolerance (0.03):", "YES" if ok else "NO")

    fig, ax = plt.subplots(1, 3, figsize=(12.5, 3.6))
    for ax_, L in zip(ax, (11, 17, 23)):
        pop = np.array(ideal[L]["pop"])
        im = ax_.imshow(pop.T, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=1)
        ax_.set_title(f"T6, L={L}: <n_j(t)>  (simulated: ideal)", fontsize=8)
        ax_.set_xlabel("QCA cycle t"); ax_.set_ylabel("site j")
        fig.colorbar(im, ax=ax_)
    fig.tight_layout(); fig.savefig(FIGDIR / "jones_t6_population.png", dpi=130)

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for L in (11, 15, 17, 23):
        ax[0].plot(ideal[L]["t"], ideal[L]["C"], label=f"L={L} ideal")
    if heron:
        ax[0].plot(heron["t"], heron["C"], "k--", label="L=11 Heron-class noise")
    ax[0].plot(list(FIG3_L17), list(FIG3_L17.values()), "rs", ms=4, label="D14 Fig.3 L=17 (read)")
    ax[0].set_xlabel("QCA cycle t"); ax[0].set_ylabel("clustering coefficient C")
    ax[0].set_title("MI-network clustering; ideal = " + sim_label("ideal"), fontsize=7); ax[0].legend(fontsize=6)
    for L in (11, 15, 17, 23):
        ax[1].plot(ideal[L]["t"], ideal[L]["ell"], label=f"L={L} ideal")
    if heron:
        ax[1].plot(heron["t"], heron["ell"], "k--", label="L=11 Heron-class noise")
    ax[1].set_xlabel("QCA cycle t"); ax[1].set_ylabel("weighted path length"); ax[1].legend(fontsize=6)
    ax[1].set_title("Heron curve = " + sim_label("heron"), fontsize=7)
    fig.tight_layout(); fig.savefig(FIGDIR / "jones_t6_network.png", dpi=130)
    (FIGDIR / "jones_t6_summary.json").write_text(json.dumps({
        "fig3_L17_comparison": cmp_rows, "within_0.03": bool(ok),
        "O_conserved_max_dev": {str(L): float(np.abs(np.array(ideal[L]["O"]) - ideal[L]["O"][0]).max()) for L in ideal},
        "C": {str(L): ideal[L]["C"] for L in ideal}, "heron_L11_C": heron["C"] if heron else None}, indent=1))


if __name__ == "__main__":
    main()
