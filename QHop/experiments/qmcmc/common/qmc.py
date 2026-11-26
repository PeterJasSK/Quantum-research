"""Shared exact harness for the QeMCMC applied review (QHop/experiments/qmcmc).

Everything here is exact linear algebra on the full 2^n state space (n <= ~13 dense).
Conventions: state index a, bit i of a = spin i (bit 0 -> s_i = +1, bit 1 -> s_i = -1).
Energy E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i.  Target pi(s) ~ exp(-beta E(s)).

Proposals return a row-stochastic matrix Q[a, b] = Q(b | a). Metropolis acceptance
min(1, pi_b/pi_a) is exact iff Q is symmetric; mh_matrix(..., hastings=True) uses the
full Hastings ratio for asymmetric Q.

Usage (from any folder):
    import sys; sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
    import qmc
"""
import numpy as np
from scipy.linalg import eigh

# ---------------------------------------------------------------- states, energies, instances

def spins(n):
    idx = np.arange(2 ** n)
    return 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)


def ising_energies(J, h):
    s = spins(len(h)).astype(float)
    return -0.5 * np.einsum("ai,ij,aj->a", s, J, s) - s @ h


def sk_instance(n, seed, field=True):
    """Layden-style SK: J_ij, h_i ~ N(0,1)."""
    g = np.random.default_rng(seed)
    J = np.triu(g.normal(size=(n, n)), 1)
    J = J + J.T
    h = g.normal(size=n) if field else np.zeros(n)
    return J, h


def lattice_edges(L1, L2, periodic=True):
    E = []
    idx = lambda x, y: x * L2 + y
    for x in range(L1):
        for y in range(L2):
            if periodic or x + 1 < L1:
                E.append((idx(x, y), idx((x + 1) % L1, y)))
            if periodic or y + 1 < L2:
                E.append((idx(x, y), idx(x, (y + 1) % L2)))
    return sorted({tuple(sorted(e)) for e in E if e[0] != e[1]})


def ea_instance(L1, L2, seed, periodic=True, dist="gauss", field=0.0):
    """2D Edwards-Anderson glass on an L1 x L2 grid (gauss or +-1 bonds)."""
    g = np.random.default_rng(seed)
    n = L1 * L2
    J = np.zeros((n, n))
    for i, j in lattice_edges(L1, L2, periodic):
        v = g.normal() if dist == "gauss" else g.choice([-1.0, 1.0])
        J[i, j] += v
        J[j, i] += v
    h = field * g.normal(size=n) if field else np.zeros(n)
    return J, h


def ferro_instance(L1, L2, periodic=True, Jval=1.0):
    n = L1 * L2
    J = np.zeros((n, n))
    for i, j in lattice_edges(L1, L2, periodic):
        J[i, j] += Jval
        J[j, i] += Jval
    return J, np.zeros(n)


# ---------------------------------------------------------------- proposals

def mixer_diag_flip(n):
    """Return (rows, cols) for the sparse sum_i X_i pattern (used to build dense mixer)."""
    dim = 2 ** n
    a = np.arange(dim)
    return np.concatenate([a] * n), np.concatenate([a ^ (1 << i) for i in range(n)])


def mixer(n):
    dim = 2 ** n
    H = np.zeros((dim, dim))
    r, c = mixer_diag_flip(n)
    np.add.at(H, (r, c), 1.0)
    return H


def alpha_from_energy(Ediag):
    """Scale so the problem term and the mixer have comparable norms: alpha = sqrt(n)/std(E).
    For pure Ising with N(0,1) couplings this matches Layden's sqrt(n)/||J,h||_F up to O(1)."""
    n = int(np.log2(len(Ediag)))
    sd = np.std(Ediag)
    return np.sqrt(n) / sd if sd > 0 else 1.0


def draw_params(seed, m, gamma=(0.25, 0.6), t=(2.0, 20.0)):
    g = np.random.default_rng(seed)
    return g.uniform(*gamma, m), g.uniform(*t, m)


def quantum_Q(Hprob, gammas, ts, alpha=None, Hm=None):
    """Q[a,b] = mean_k |<b| exp(-i H_k t_k) |a>|^2, H_k = (1-g_k) alpha diag(Hprob) + g_k sum X.
    Hprob may be any real energy vector (true energy or a surrogate). Symmetric for any real
    diagonal Hprob because H_k is real symmetric -> U = U^T."""
    n = int(np.log2(len(Hprob)))
    a = alpha_from_energy(Hprob) if alpha is None else alpha
    Hm = mixer(n) if Hm is None else Hm
    Q = np.zeros((2 ** n, 2 ** n))
    cache = {}
    for g, t in zip(gammas, ts):
        key = round(float(g), 12)
        if key not in cache:
            cache[key] = eigh(np.diag((1 - g) * a * Hprob) + g * Hm)
        w, V = cache[key]
        U = (V * np.exp(-1j * w * t)) @ V.T
        Q += np.abs(U) ** 2
    Q /= len(gammas)
    return Q


def decohered_Q(Hprob, gammas, ts, dt=0.25, alpha=None, Hm=None):
    """Same generator with full Z-dephasing every dt: classical Markov kernel |e^{-iH dt}|^2
    composed t/dt times (interference removed between slices)."""
    n = int(np.log2(len(Hprob)))
    a = alpha_from_energy(Hprob) if alpha is None else alpha
    Hm = mixer(n) if Hm is None else Hm
    Q = np.zeros((2 ** n, 2 ** n))
    for g, t in zip(gammas, ts):
        w, V = eigh(np.diag((1 - g) * a * Hprob) + g * Hm)
        k = max(1, int(round(t / dt)))
        Ud = (V * np.exp(-1j * w * (t / k))) @ V.T
        T = np.abs(Ud) ** 2
        Q += np.linalg.matrix_power(T, k)
    return Q / len(gammas)


def local_Q(n):
    dim = 2 ** n
    Q = np.zeros((dim, dim))
    a = np.arange(dim)
    for i in range(n):
        Q[a, a ^ (1 << i)] += 1.0 / n
    return Q


def uniform_Q(n):
    return np.full((2 ** n, 2 ** n), 1.0 / 2 ** n)


def mixture_Q(Qs, weights):
    w = np.asarray(weights, float) / np.sum(weights)
    return sum(wi * Qi for wi, Qi in zip(w, Qs))


def coarse_grained_Q(J, h, groups, beta_unused=None, gammas=None, ts=None, group_probs=None,
                     alpha_mode="group"):
    """Coarse-grained QeMCMC proposal (Ferguson-Wallden style) as an exact full matrix.
    Pick group G with state-independent prob p_G; the spins outside G are frozen and enter as
    an effective field h_eff_i = h_i + sum_{j not in G} J_ij s_j; a quantum proposal on G only.
    Symmetric because the frozen part is identical in s and s' and the group Hamiltonian
    depends on the frozen part only."""
    n = len(h)
    dim = 2 ** n
    S = spins(n).astype(float)
    groups = [np.asarray(g) for g in groups]
    p = np.full(len(groups), 1.0 / len(groups)) if group_probs is None else np.asarray(group_probs)
    Q = np.zeros((dim, dim))
    for G, pG in zip(groups, p):
        k = len(G)
        rest = np.setdiff1d(np.arange(n), G)
        JG = J[np.ix_(G, G)]
        sub_s = spins(k).astype(float)
        Hm = mixer(k)
        # enumerate frozen configurations of the rest
        rest_bits = (np.arange(dim)[:, None] >> rest) & 1
        rest_key = (rest_bits * (1 << np.arange(len(rest)))).sum(1) if len(rest) else np.zeros(dim, int)
        G_bits = (np.arange(dim)[:, None] >> G) & 1
        G_key = (G_bits * (1 << np.arange(k))).sum(1)
        cache = {}
        for a in range(dim):
            rk = rest_key[a]
            if rk not in cache:
                s_rest = S[a, rest]
                heff = h[G] + J[np.ix_(G, rest)] @ s_rest
                Eg = -0.5 * np.einsum("ai,ij,aj->a", sub_s, JG, sub_s) - sub_s @ heff
                cache[rk] = quantum_Q(Eg, gammas, ts, Hm=Hm)
            Qg = cache[rk]
            # target states: same rest bits, any group bits
            base = a & ~np.bitwise_or.reduce(1 << G)
            for gb in range(2 ** k):
                b = base
                for idx_bit, site in enumerate(G):
                    if (gb >> idx_bit) & 1:
                        b |= (1 << site)
                Q[a, b] += pG * Qg[G_key[a], gb]
    return Q


# ---------------------------------------------------------------- Metropolis matrix and gap

def boltzmann(E, beta):
    w = np.exp(-beta * (E - E.min()))
    return w / w.sum()


def mh_matrix(Q, E, beta, hastings=False):
    pi = boltzmann(E, beta)
    with np.errstate(divide="ignore", invalid="ignore"):
        if hastings:
            ratio = (pi[None, :] * Q.T) / (pi[:, None] * Q)
            ratio = np.where(Q > 0, ratio, 0.0)
        else:
            ratio = pi[None, :] / pi[:, None]
    P = Q * np.minimum(1.0, ratio)
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return P


def spectral_gap(P, pi=None):
    """1 - max |lambda| over the non-unit spectrum. If pi given and P reversible w.r.t. pi,
    uses the symmetric form D^1/2 P D^-1/2 (fast, stable)."""
    if pi is not None:
        d = np.sqrt(pi)
        A = (d[:, None] * P) / d[None, :]
        A = 0.5 * (A + A.T)
        lam = np.linalg.eigvalsh(A)
        lam = np.sort(np.abs(lam))[::-1]
        return float(1.0 - lam[1])
    lam = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    return float(1.0 - lam[1])


def gap(Q, E, beta, hastings=False):
    P = mh_matrix(Q, E, beta, hastings)
    pi = None if hastings else boltzmann(E, beta)
    return spectral_gap(P, pi)


def acceptance(Q, E, beta):
    pi = boltzmann(E, beta)
    acc = np.minimum(1.0, pi[None, :] / pi[:, None])
    off = Q.copy()
    np.fill_diagonal(off, 0.0)
    return float((pi[:, None] * off * acc).sum())


def mean_hamming(Q, E, beta):
    n = int(np.log2(len(E)))
    pi = boltzmann(E, beta)
    a = np.arange(2 ** n)
    ham = np.array([[bin(x ^ y).count("1") for y in a] for x in a]) if n <= 10 else None
    if ham is None:
        x = a[:, None] ^ a[None, :]
        ham = np.zeros_like(x)
        for i in range(n):
            ham += (x >> i) & 1
    return float((pi[:, None] * Q * ham).sum())


def asymmetry(Q):
    return float(np.abs(Q - Q.T).mean() / Q.mean())


# ---------------------------------------------------------------- regime markers (exact)

def thermo(E, n, betas):
    """Exact specific heat per spin C(beta) = beta^2 Var(E)/n."""
    out = []
    for b in betas:
        p = boltzmann(E, b)
        m1 = (p * E).sum()
        out.append(b * b * ((p * E * E).sum() - m1 * m1) / n)
    return np.array(out)


def local_gap_curve(E, n, betas):
    Ql = local_Q(n)
    return np.array([gap(Ql, E, b) for b in betas])


# ---------------------------------------------------------------- chains, PT, IAT

def iat(x, c=5.0):
    """Integrated autocorrelation time, Sokal automatic window (tau = 1 + 2 sum rho)."""
    x = np.asarray(x, float) - np.mean(x)
    N = len(x)
    if N < 10 or np.var(x) == 0:
        return np.nan
    f = np.fft.rfft(x, n=2 * N)
    acf = np.fft.irfft(f * np.conj(f))[:N] / (N - np.arange(N))
    acf /= acf[0]
    tau = 1.0
    for M in range(1, N):
        tau = 1.0 + 2.0 * acf[1:M + 1].sum()
        if M >= c * tau:
            break
    return float(tau)


def sample_row(Q, a, rng):
    return rng.choice(Q.shape[1], p=Q[a])


def run_chain(Q, E, beta, steps, seed, start=None):
    """Exact-matrix chain (any proposal matrix). Returns visited state indices."""
    rng = np.random.default_rng(seed)
    dim = len(E)
    a = rng.integers(dim) if start is None else start
    out = np.empty(steps, int)
    cdf = np.cumsum(Q, 1)
    for k in range(steps):
        b = int(np.searchsorted(cdf[a], rng.random() * cdf[a, -1]))
        dE = E[b] - E[a]
        if dE <= 0 or rng.random() < np.exp(-beta * dE):
            a = b
        out[k] = a
    return out


def parallel_tempering(E_fn_flip, n, betas, sweeps, seed, s0=None, record=None):
    """Generic single-spin-flip PT on +-1 spins with replica swaps after each sweep.
    E_fn_flip(s, i) -> energy change of flipping spin i; E_total(s) via record func if needed.
    Returns dict with swap rates and recorded observable per sweep for each beta."""
    rng = np.random.default_rng(seed)
    R = len(betas)
    S = rng.choice([-1, 1], size=(R, n)) if s0 is None else s0.copy()
    swaps = np.zeros(R - 1)
    tries = np.zeros(R - 1)
    rec = [[] for _ in range(R)]
    for sw in range(sweeps):
        for r in range(R):
            for i in rng.integers(0, n, n):
                d = E_fn_flip(S[r], i)
                if d <= 0 or rng.random() < np.exp(-betas[r] * d):
                    S[r, i] *= -1
        Etot = np.array([record["E"](S[r]) for r in range(R)])
        for r in range(sw % 2, R - 1, 2):
            tries[r] += 1
            x = (betas[r + 1] - betas[r]) * (Etot[r + 1] - Etot[r])
            if x >= 0 or rng.random() < np.exp(x):
                S[[r, r + 1]] = S[[r + 1, r]]
                Etot[[r, r + 1]] = Etot[[r + 1, r]]
                swaps[r] += 1
        if record is not None:
            for r in range(R):
                rec[r].append(record["obs"](S[r]))
    return {"swap_rate": (swaps / np.maximum(tries, 1)).tolist(), "obs": [np.array(o) for o in rec]}


def ising_flip_fn(J, h):
    def dE(s, i):
        return 2.0 * s[i] * (J[i] @ s + h[i])
    return dE


def ising_E_fn(J, h):
    def E(s):
        return -0.5 * s @ J @ s - h @ s
    return E
