"""Quantum-enhanced MCMC (Layden et al. [B11]): quantum proposals inside Metropolis-Hastings."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from shared import RE_ROOT, STUBS
from shared.seedhash import derive_seed, rng
from shared.simbackend import calibration_snapshot, make_simulator, sim_label, transpile_heron

LETTER_DIR = RE_ROOT / "B_mapping"


# ---- Ising model ----------------------------------------------------------------------------------

def spins(n: int) -> np.ndarray:
    """(2^n, n) array of +-1; bit i of the state index = spin i (0 -> +1)."""
    idx = np.arange(2 ** n)
    return 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)


def energies(J: np.ndarray, h: np.ndarray) -> np.ndarray:
    """E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i (J symmetric, zero diagonal)."""
    s = spins(len(h))
    return -0.5 * np.einsum("ai,ij,aj->a", s, J, s) - s @ h


def alpha(J, h) -> float:
    return np.sqrt(len(h)) / np.sqrt(np.sum(np.triu(J, 1) ** 2) + np.sum(h ** 2))


def mixer(n: int) -> np.ndarray:
    """H_mix = sum_i X_i as a dense matrix."""
    dim = 2 ** n
    H = np.zeros((dim, dim))
    for i in range(n):
        H[np.arange(dim), np.arange(dim) ^ (1 << i)] += 1
    return H


# ---- proposals ------------------------------------------------------------------------------------

def quantum_Q(J, h, gammas, ts) -> np.ndarray:
    """Q[s, s'] = mean over (gamma, t) of |<s'|exp(-iHt)|s>|^2, H = (1-g) alpha H_prob + g H_mix."""
    n = len(h)
    E, a, Hm = energies(J, h), alpha(J, h), mixer(n)
    Q = np.zeros((2 ** n, 2 ** n))
    for g, t in zip(gammas, ts):
        w, V = np.linalg.eigh(np.diag((1 - g) * a * E) + g * Hm)
        U = (V * np.exp(-1j * w * t)) @ V.T
        Q += np.abs(U) ** 2
    return Q / len(gammas)


def local_Q(n: int) -> np.ndarray:
    dim = 2 ** n
    Q = np.zeros((dim, dim))
    for i in range(n):
        Q[np.arange(dim), np.arange(dim) ^ (1 << i)] += 1 / n
    return Q


def uniform_Q(n: int) -> np.ndarray:
    return np.full((2 ** n, 2 ** n), 1 / 2 ** n)


def mh_matrix(Q: np.ndarray, E: np.ndarray, T: float = 1.0) -> np.ndarray:
    """P(s->s') = Q(s'|s) min(1, pi(s')/pi(s)); rest stays put. Correct for symmetric Q."""
    pi = np.exp(-(E - E.min()) / T)
    acc = np.minimum(1.0, pi[None, :] / pi[:, None])
    P = Q * acc
    np.fill_diagonal(P, 0.0)
    P[np.arange(len(P)), np.arange(len(P))] = 1 - P.sum(1)
    return P


def spectral_gap(P: np.ndarray) -> float:
    lam = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    return float(1 - lam[1])


def asymmetry(Q: np.ndarray) -> float:
    """Mean |Q - Q^T| per entry relative to mean Q (0 = exactly symmetric proposal)."""
    return float(np.abs(Q - Q.T).mean() / Q.mean())


def draw_params(g, m: int):
    return g.uniform(0.25, 0.6, m), g.uniform(2, 20, m)


# ---- Trotter circuit (Heron arm) -------------------------------------------------------------------

GRID = [(0.3, 2.0), (0.3, 6.0), (0.5, 2.0), (0.5, 6.0)]


def trotter_circuit(J, h, gamma, t, state: int, steps_per_t: float = 2.0):
    """Second-order Trotter of exp(-iHt); input = basis state `state`; measured in Z."""
    from qiskit import QuantumCircuit
    n = len(h)
    a = alpha(J, h)
    r = max(2, int(round(t * steps_per_t)))
    dt = t / r
    qc = QuantumCircuit(n, n)
    for i in range(n):
        if (state >> i) & 1:
            qc.x(i)

    def diag(frac):
        for i in range(n):
            if h[i]:
                qc.rz(2 * (1 - gamma) * a * (-h[i]) * dt * frac, i)   # exp(-i dt frac (1-g) a (-h_i Z_i))
        for i in range(n):
            for j in range(i + 1, n):
                if J[i, j]:
                    qc.rzz(2 * (1 - gamma) * a * (-J[i, j]) * dt * frac, i, j)

    for _ in range(r):
        diag(0.5)
        for i in range(n):
            qc.rx(2 * gamma * dt, i)
        diag(0.5)
    qc.measure(range(n), range(n))
    return qc


def noisy_Q(J, h, mode, seed, shots=1024, grid=GRID):
    """Q estimated from circuits: every basis input x grid point, run on the simulator."""
    n = len(h)
    dim = 2 ** n
    circs = [trotter_circuit(J, h, g, t, s) for (g, t) in grid for s in range(dim)]
    tq = [transpile_heron(c, seed=seed, optimization_level=1) for c in circs]
    sim = make_simulator(mode, seed=seed)
    sim.set_options(max_parallel_experiments=0)
    res = sim.run(tq, shots=shots).result()
    Q = np.zeros((dim, dim))
    for k in range(len(circs)):
        s = k % dim
        for bits, c in res.get_counts(k).items():
            Q[s, int(bits.replace(" ", ""), 2)] += c / shots
    depth = int(np.mean([c.depth() for c in tq]))
    cz = float(np.mean([c.count_ops().get("cz", 0) for c in tq]))
    return Q / len(grid), {"mean_depth": depth, "mean_cz": cz, "circuits": len(circs)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tumor", action="store_true", required=True, help="tumor-in-anatomy energy (AC-11)")
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--site", default="S001")
    ap.add_argument("--sites", default=str(STUBS / "site_candidates" / "sites.json"))
    ap.add_argument("--certificate", default=str(STUBS / "certificate" / "certificate.json"))
    ap.add_argument("--size-mm", type=float, default=8.0)
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--patch", default="2,2,2", help="voxel patch z,y,x (fallback 2,3,1 = 6 spins)")
    ap.add_argument("--m", type=int, default=64, help="(gamma, t) draws for the ideal arm")
    a = ap.parse_args()
    from B_mapping.src.tumor_energy import PARAMS, build
    from shared.runrecord import start_run
    cert = json.loads(Path(a.certificate).read_text())
    if cert["status"] != "pass":
        print("certificate failed: no run", file=sys.stderr)
        raise SystemExit(2)
    seed = cert["extracted_seed_hex"]
    J, h, info = build(Path(a.sites), a.site, a.size_mm, patch=tuple(int(x) for x in a.patch.split(",")))
    n = len(h)
    E = energies(J, h)
    run = start_run(LETTER_DIR, f"qemcmc-{a.mode}", sim_mode=a.mode, tool="B_mapping.src.qemcmc")
    g = rng(seed, "B.qemcmc")
    gam, ts = draw_params(g, a.m)
    out = {"sim_label": sim_label(a.mode), "hardware": None, "n_spins": n, "site": a.site, "params": PARAMS,
           "patch": info, "claim": "correct sampler with quantum proposals; any speedup is ideal-simulation only"}
    Qid = quantum_Q(J, h, gam, ts)
    out["ideal_random_draws"] = {"gap_quantum": spectral_gap(mh_matrix(Qid, E)),
                                 "gap_local": spectral_gap(mh_matrix(local_Q(n), E)),
                                 "gap_uniform": spectral_gap(mh_matrix(uniform_Q(n), E)), "M": a.m}
    Qgrid = quantum_Q(J, h, [x[0] for x in GRID], [x[1] for x in GRID])
    out["ideal_grid"] = {"gap_quantum": spectral_gap(mh_matrix(Qgrid, E))}
    if a.mode == "heron":
        Qn, ci = noisy_Q(J, h, "heron", derive_seed(seed, "B.qemcmc") % 2 ** 31, a.shots)
        out["heron"] = {"gap_quantum": spectral_gap(mh_matrix(Qn, E)), "asymmetry_Q": asymmetry(Qn),
                        "row_sum_err": float(np.abs(Qn.sum(1) - 1).max()), "tvd_Q_vs_ideal_grid":
                        float(0.5 * np.abs(Qn - Qgrid).sum(1).mean()), **ci, "grid": GRID,
                        "calibration": calibration_snapshot()}
    (run.path / "qemcmc_result.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    run.finish(f"qemcmc tumor {a.mode}: " + json.dumps({k: v for k, v in out.items() if k.startswith(("ideal", "heron"))},
                                                      default=lambda o: None)[:800])
    print(run.path.relative_to(RE_ROOT))
    print(f"[{sim_label(a.mode)}] n={n} spins, site {a.site}")
    for k in ("ideal_random_draws", "ideal_grid", "heron"):
        if k in out:
            print(k, {x: (round(v, 5) if isinstance(v, float) else v) for x, v in out[k].items() if x != "calibration" and x != "grid"})


if __name__ == "__main__":
    main()
