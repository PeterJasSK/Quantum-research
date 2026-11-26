"""D9 mask-library helpers (V24). Copies/extends qmc functions; qmc itself is not edited.

A mask law M is a probability vector over the 2^n flip masks m (index = bit pattern). The chain move is
s -> s XOR m, m ~ M, then Metropolis accept min(1, pi(s')/pi(s)). Because M does not depend on s,
Q(s'|s) = M(s XOR s') = Q(s|s') -> symmetric -> exact Boltzmann stationarity (any M, incl. finite libraries).
The zero mask (no move) is dropped from every law and the law renormalised (same treatment for all laws).
"""
import sys
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import eigsh

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

GAMMA_GRID = np.array([0.25, 0.25 + 0.35 / 3, 0.25 + 0.70 / 3, 0.60])  # 4 distinct gammas -> 4 eigh per Q


def layden_params(seed, m=16):
    """P1 ad hoc params: gamma ~ U[.25,.6] snapped to a 4-point grid (eigh caching), t ~ U[2,20]."""
    g, t = qmc.draw_params(seed, m)
    g = GAMMA_GRID[np.abs(g[:, None] - GAMMA_GRID[None, :]).argmin(1)]
    return g, t


def _eig_cache(E, gammas):
    n = int(np.log2(len(E)))
    a = qmc.alpha_from_energy(E)
    Hm = qmc.mixer(n)
    return {float(g): eigh(np.diag((1 - g) * a * E) + g * Hm) for g in np.unique(gammas)}


def quantum_and_decohered_Q(E, gammas, ts, want_dec=True, dt=0.25):
    """Coherent P1 proposal matrix and the fully-dephased (every dt) classical control."""
    cache = _eig_cache(E, gammas)
    d = len(E)
    Q = np.zeros((d, d))
    Qd = np.zeros((d, d)) if want_dec else None
    for g, t in zip(gammas, ts):
        w, V = cache[float(g)]
        Q += np.abs((V * np.exp(-1j * w * t)) @ V.T) ** 2
        if want_dec:
            k = max(1, int(round(t / dt)))
            T = np.abs((V * np.exp(-1j * w * (t / k))) @ V.T) ** 2
            T = 0.5 * (T + T.T)
            lt, Vt = eigh(T)  # T symmetric -> T^k = V diag(l^k) V^T (cheaper than repeated squaring)
            Qd += np.clip((Vt * lt ** k) @ Vt.T, 0, None)
    Q /= len(gammas)
    if want_dec:
        Qd /= len(gammas)
        Qd /= Qd.sum(1, keepdims=True)
    return Q, Qd


def mask_law_from_Q(Q, rho):
    """M(m) = sum_r rho(r) Q(r, r XOR m)."""
    d = Q.shape[0]
    idx = np.arange(d)
    M = np.zeros(d)
    for r in np.nonzero(rho > 0)[0]:
        M += rho[r] * Q[r, r ^ idx]
    return M


def xor_autocorr(p, q=None):
    """M(m) = sum_r p(r) q(r XOR m)  (law of r1 XOR r2, r1~p, r2~q independent). Walsh-Hadamard O(d log d)."""
    q = p if q is None else q
    return np.clip(wht(wht(p) * wht(q)) / len(p), 0, None)


def wht(a):
    a = np.array(a, dtype=float)
    h = 1
    d = len(a)
    while h < d:
        a = a.reshape(-1, 2 * h)
        x, y = a[:, :h].copy(), a[:, h:].copy()
        a[:, :h], a[:, h:] = x + y, x - y
        a = a.reshape(d)
        h *= 2
    return a


def clean(M):
    M = np.array(M, dtype=float)
    M[0] = 0.0
    return M / M.sum()


def popcount(d):
    idx = np.arange(d)
    return np.array([bin(i).count("1") for i in idx])


def weight_matched(M, n):
    """(h) same Hamming-weight distribution as M, uniformly random positions."""
    from math import comb
    w = popcount(2 ** n)
    W = np.bincount(w, weights=M, minlength=n + 1)
    return np.array([W[k] / comb(n, k) for k in w])


def greedy_minima_law(E, n):
    """(f) basin weights: steepest single-spin descent from every state (exact over uniform starts).
    Returns prob vector over states = basin size / 2^n of each local minimum (0 elsewhere)."""
    d = len(E)
    idx = np.arange(d)
    nb = idx[:, None] ^ (1 << np.arange(n))[None, :]
    best = nb[idx, E[nb].argmin(1)]
    nxt = np.where(E[best] < E, best, idx)
    for _ in range(4 * n + 10):
        nn = nxt[nxt]
        if np.array_equal(nn, nxt):
            break
        nxt = nn
    return np.bincount(nxt, minlength=d) / d


def percolation_law(J, beta, n, samples, seed):
    """(g) state-independent bond-percolation clusters: bond ij open w.p. 1-exp(-2 beta |J_ij|), pick a uniform
    random site, flip its connected cluster. Law estimated from `samples` Monte Carlo draws (a large library)."""
    rng = np.random.default_rng(seed)
    P = 1 - np.exp(-2 * beta * np.abs(J))
    np.fill_diagonal(P, 0)
    counts = np.zeros(2 ** n)
    bits = 1 << np.arange(n)
    B = 4096
    for b0 in range(0, samples, B):
        nb = min(B, samples - b0)
        U = rng.random((nb, n, n))
        U = np.triu(U, 1)
        U = U + np.transpose(U, (0, 2, 1))
        adj = (U < P[None]) & (P[None] > 0)
        reach = np.zeros((nb, n), bool)
        reach[np.arange(nb), rng.integers(n, size=nb)] = True
        for _ in range(n):
            new = reach | np.einsum("bi,bij->bj", reach.astype(np.int32), adj.astype(np.int32)).astype(bool)
            if np.array_equal(new, reach):
                break
            reach = new
        counts += np.bincount(reach.astype(np.int64) @ bits, minlength=2 ** n)
    return counts / samples


def library(M, L, seed):
    """Finite fixed library: L masks drawn iid from law M (fixed seed); law = empirical frequencies."""
    rng = np.random.default_rng(seed)
    draws = rng.choice(len(M), size=L, p=M / M.sum())
    F = np.bincount(draws, minlength=len(M)).astype(float)
    if F[1:].sum() == 0:
        return None
    return clean(F)


def local_law(n):
    M = np.zeros(2 ** n)
    M[1 << np.arange(n)] = 1.0 / n
    return M


def uniform_law(n):
    return clean(np.ones(2 ** n))


def gap_mask(M, E, beta, lanczos_from=11):
    """Absolute spectral gap 1 - max_{k>=2}|lambda_k| of the Metropolis chain with mask law M."""
    d = len(E)
    idx = np.arange(d)
    Q = M[idx[:, None] ^ idx[None, :]]
    P = qmc.mh_matrix(Q, E, beta)
    pi = qmc.boltzmann(E, beta)
    s = np.sqrt(pi)
    A = (s[:, None] * P) / s[None, :]
    A = 0.5 * (A + A.T)
    n = int(np.log2(d))
    if n < lanczos_from:
        lam = np.sort(np.abs(np.linalg.eigvalsh(A)))[::-1]
        return float(1.0 - lam[1])
    A -= np.outer(s, s)  # deflate the stationary eigenvector (eigenvalue 1)
    v0 = np.random.default_rng(0).standard_normal(d)
    lam = eigsh(A, k=1, which="LM", tol=1e-9, v0=v0, return_eigenvectors=False, maxiter=20000)
    return float(1.0 - abs(lam[0]))


def mix(M1, M2, w=0.5):
    return w * M1 + (1 - w) * M2


def gap_Q(Q, E, beta):
    """Absolute gap for a general symmetric proposal matrix Q via deflated Lanczos (n >= 11)."""
    P = qmc.mh_matrix(Q, E, beta)
    pi = qmc.boltzmann(E, beta)
    s = np.sqrt(pi)
    A = (s[:, None] * P) / s[None, :]
    A = 0.5 * (A + A.T) - np.outer(s, s)
    lam = eigsh(A, k=1, which="LM", tol=1e-9, v0=np.random.default_rng(0).standard_normal(len(E)),
                return_eigenvectors=False, maxiter=20000)
    return float(1.0 - abs(lam[0]))
