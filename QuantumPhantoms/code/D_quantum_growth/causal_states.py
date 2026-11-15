"""D-SCALE causal-state machinery (frozen copy of RE D `src/causal_states.py`).

Original docstring: Causal-state machinery for D-5 (target #6): renewal processes, C_mu / D_mu, quantum memory states,
C_q / D_q, Wu's 1-qubit PMD Kraus model [D16 SM S1], Gu's perturbed coin [D06], best 1-bit classical HMM.

Rebuilt from the papers (no code imported). Survival of a PMD renewal process (Wu Eq. 1):
    Phi(n) = Gamma^n (1 - V sin^2(n pi / N))
"""
# copied from plans/relatedPapers/reverse-engineering/D_quantum_growth/src/causal_states.py @ 2609cbe;
# changed: rng from common.runio, seed label D5-baseline -> DS-pmd-baseline.
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from common.runio import rng


# ------------------------------------------------------------------ renewal process -> causal states
def pmd_survival(n, Gamma: float, V: float, N: int):
    n = np.asarray(n, float)
    return Gamma ** n * (1 - V * np.sin(n * np.pi / N) ** 2)


def pmd_hazards(Gamma: float, V: float, N: int) -> np.ndarray:
    """P(tick | j zeros since last tick), j = 0..N-1 (periodic in j)."""
    j = np.arange(N)
    return 1 - pmd_survival(j + 1, Gamma, V, N) / pmd_survival(j, Gamma, V, N)


# ------------------------------------------------------------------ Wu 1-qubit model [D16 SM S1]
def wu_model(Gamma: float, V: float, N: int, m: int = 1) -> dict:
    """Solve (alpha, beta0, beta1, eta, phi) for the PMD process, build Kraus A0, A1 and memory states.
    eta^2 = 1/Gamma; eta^2 = 1 + g/2 + sqrt(g^2+4g)/2 with g = 4 alpha^2 sin^2(phi/2); V = 4 alpha b0 b1;
    (b0 + alpha b1)^2 + b1^2 = 1."""
    phi = 2 * m * np.pi / N
    eta2 = 1 / Gamma
    # invert eta^2 = 1 + g/2 + sqrt(g^2+4g)/2  ->  g = (eta^2-1)^2 / eta^2
    g = (eta2 - 1) ** 2 / eta2
    alpha = np.sqrt(g / (4 * np.sin(phi / 2) ** 2))
    # beta0 beta1 = V/(4 alpha); (b0 + alpha b1)^2 + b1^2 = 1 -> solve for b1 numerically
    k = V / (4 * alpha)

    def f(b1):
        b0 = k / b1
        return (b0 + alpha * b1) ** 2 + b1 ** 2 - 1

    grid = np.linspace(1e-3, 1.5, 20000)
    vals = np.array([f(b) for b in grid])
    roots = []
    for i in range(len(grid) - 1):
        if vals[i] * vals[i + 1] < 0:
            lo, hi = grid[i], grid[i + 1]
            for _ in range(80):
                mid = (lo + hi) / 2
                if f(lo) * f(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            roots.append((lo + hi) / 2)
    if not roots:
        raise ValueError(f"no real (beta0, beta1) for Gamma={Gamma}, V={V}, N={N}")
    b1 = roots[0]
    b0 = k / b1
    eta = np.sqrt(eta2)
    e = np.exp(1j * phi)
    A0 = np.array([[1, alpha * (e - 1)], [0, e]]) / eta
    Z0, Z1 = np.array([1, 0], complex), np.array([alpha, 1], complex)
    sigma0 = b0 * Z0 + b1 * Z1
    sigma0 = sigma0 / np.linalg.norm(sigma0)
    # A1 = zeta |sigma0><w| from completeness  A1^† A1 = 1 - A0^† A0  (rank 1)
    M = np.eye(2) - A0.conj().T @ A0
    M = (M + M.conj().T) / 2
    ev, evec = np.linalg.eigh(M)
    zeta2 = float(ev.max())
    w = evec[:, np.argmax(ev)]
    A1 = np.sqrt(zeta2) * np.outer(sigma0, w.conj())
    sig = [sigma0]
    for _ in range(N - 1):
        v = A0 @ sig[-1]
        sig.append(v / np.linalg.norm(v))
    return {"A0": A0, "A1": A1, "sigma": np.array(sig), "alpha": alpha, "beta": (b0, b1), "eta": eta,
            "phi": phi, "N": N}


# ------------------------------------------------------------------ circuit-ready unitary
def kraus_unitary(A0: np.ndarray, A1: np.ndarray) -> np.ndarray:
    """4x4 unitary U (qubit 0 = memory, qubit 1 = output; index = 2*o + m) with
    U |s>|0> = A0|s>|0> + A1|s>|1>; the |.>|1> columns completed by Gram-Schmidt (isometry completion)."""
    U = np.zeros((4, 4), complex)
    for s in range(2):
        e = np.zeros(2, complex); e[s] = 1
        col = np.concatenate([A0 @ e, A1 @ e])      # index = 2*o + m, o = output symbol
        U[:, s] = col
    basis = [U[:, 0], U[:, 1]]
    cand = [np.eye(4)[:, i].astype(complex) for i in range(4)]
    out = []
    for c in cand:
        v = c.copy()
        for b in basis + out:
            v = v - np.vdot(b, v) * b
        if np.linalg.norm(v) > 1e-8:
            out.append(v / np.linalg.norm(v))
        if len(out) == 2:
            break
    U[:, 2], U[:, 3] = out
    return U


# ------------------------------------------------------------------ word distributions
def exact_words(h: np.ndarray, L: int, start: int = 0) -> np.ndarray:
    """P(word of length L) from the cyclic machine, start state `start`; index = bits MSB-first (x_1 ... x_L)."""
    N = len(h)
    # probs[w, state]
    pr = np.zeros((1, N)); pr[0, start] = 1.0
    for _ in range(L):
        new = np.zeros((pr.shape[0] * 2, N))
        for s in range(N):
            new[0::2, (s + 1) % N] += pr[:, s] * (1 - h[s])
            new[1::2, 0] += pr[:, s] * h[s]
        pr = new
    return pr.sum(1)


def hmm_words(T: np.ndarray, L: int) -> np.ndarray:
    """Edge-emitting 2-state HMM, T[x, s, s'] summing to 1 over (x, s'); start state 0."""
    n = T.shape[1]
    pr = np.zeros((1, n)); pr[0, 0] = 1.0
    for _ in range(L):
        new = np.zeros((pr.shape[0] * 2, n))
        for x in range(2):
            new[x::2] = pr @ T[x]
        pr = new
    return pr.sum(1)


def kl_bits(p: np.ndarray, q: np.ndarray) -> float:
    """D(p || q) in bits; inf where q = 0 < p."""
    m = p > 0
    if np.any(q[m] <= 0):
        return float("inf")
    return float((p[m] * np.log2(p[m] / q[m])).sum())


def best_classical_fixed_memory(p_exact: np.ndarray, L: int, n_states: int, seed_hex: str,
                                n_starts: int = 24) -> dict:
    """Best n-state (log2 n bits) classical edge-emitting HMM minimising per-symbol KL(P_model || P_exact),
    the same direction as the quantum model's simulated-vs-exact figure. Multi-start L-BFGS-B on softmax params."""
    g = rng(seed_hex, "DS-pmd-baseline")
    npar = n_states * 2 * n_states

    def model(theta):
        z = theta.reshape(n_states, 2 * n_states)
        e = np.exp(z - z.max(1, keepdims=True))
        pr = e / e.sum(1, keepdims=True)                       # [s, (x, s')]
        return pr.reshape(n_states, 2, n_states).transpose(1, 0, 2)

    def obj(theta):
        q = hmm_words(model(theta), L)
        m = q > 1e-300
        with np.errstate(divide="ignore"):
            v = (q[m] * np.log2(q[m] / np.maximum(p_exact[m], 1e-300))).sum()
        return float(v) / L

    best = (np.inf, None)
    for _ in range(n_starts):
        res = minimize(obj, g.normal(0, 2, npar), method="L-BFGS-B", options={"maxiter": 400})
        if res.fun < best[0]:
            best = (res.fun, res.x)
    return {"d_kl_per_symbol": best[0], "T": model(best[1]), "n_states": n_states, "bits": float(np.log2(n_states))}
