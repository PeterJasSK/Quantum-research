"""E1 red-team library: stronger classical baselines for D6 (planted CDMA) and exact SK cluster moves for D1.

All kernels are exact 2^n (or K*2^n) symmetrised operators; detailed balance holds by construction:
 - symmetric proposals + Metropolis (mask-XOR proposals with state-independent mask law are symmetric),
 - independence proposals + Hastings (A_hastings, exact q computable),
 - mixtures of reversible kernels with fixed weights are reversible,
 - simulated tempering with EXACT log Z weights is reversible w.r.t. pi(k,s) = pi_k(s)/K,
 - SW / Wolff: Edwards-Sokal / cluster-flip, reversible; checked numerically (asymmetry printed).
"""
import sys
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh, LinearOperator

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/D6-inference-nishimori")
import qmc  # noqa
import d6lib as d  # noqa


def relgap(A):
    lam = np.linalg.eigvalsh(A)
    i1 = np.argmin(np.abs(lam - 1.0))
    rest = np.delete(lam, i1)
    return float(1.0 - rest.max()), float(1.0 - np.abs(rest).max())


def relgap_sparse(A, phi):
    """1 - lambda_2 for symmetric sparse A with top eigvec phi (deflated Lanczos)."""
    dim = A.shape[0]
    op = LinearOperator((dim, dim), matvec=lambda x: A @ x - phi * (phi @ x), dtype=float)
    v0 = np.random.default_rng(0).normal(size=dim)
    w = eigsh(op, k=1, which="LA", v0=v0, tol=1e-12, ncv=40, maxiter=50000, return_eigenvectors=False)
    return float(1.0 - w.max())


def weighted_flip_Q(n, masks, weights):
    dim = 2 ** n
    Q = np.zeros((dim, dim))
    a = np.arange(dim)
    w = np.asarray(weights, float)
    w = w / w.sum()
    for m, x in zip(masks, w):
        Q[a, a ^ m] += x
    return Q


def hamming_Q(n, rho):
    """Q_ab = p(a^b), p(mask) ~ rho^|mask| for |mask|>=1 (state-independent -> symmetric)."""
    dim = 2 ** n
    hw = np.array([bin(x).count("1") for x in range(dim)])
    p = np.where(hw > 0, rho ** hw, 0.0)
    p /= p.sum()
    a = np.arange(dim)
    return p[a[:, None] ^ a[None, :]]


def descent_map(E, n):
    """Steepest single-flip descent: index of local minimum reached from each state."""
    dim = len(E)
    a = np.arange(dim)
    nb = a[:, None] ^ (1 << np.arange(n))[None, :]
    best = nb[a, np.argmin(E[nb], 1)]
    nxt = np.where(E[best] < E, best, a)
    for _ in range(4 * n):
        nxt2 = nxt[nxt]
        if np.array_equal(nxt2, nxt):
            break
        nxt = nxt2
    return nxt


def product_logq(centers, eps, n, weights=None):
    """log q(s) for a mixture of product distributions around spin vectors `centers` (K x n, +-1) with
    per-spin flip probability eps (independence proposal, exact)."""
    S = qmc.spins(n).astype(float)
    C = np.asarray(centers, float)
    dist = (n - S @ C.T) / 2.0  # Hamming distances, dim x K
    lq = dist * np.log(eps) + (n - dist) * np.log(1 - eps)
    w = np.ones(len(C)) / len(C) if weights is None else np.asarray(weights) / np.sum(weights)
    lq = lq + np.log(w)[None, :]
    mx = lq.max(1, keepdims=True)
    return (mx + np.log(np.exp(lq - mx).sum(1, keepdims=True)))[:, 0]


def magnet_logq(M, n, clip=0.05, weights=None):
    """log q(s) for a mixture of product measures with magnetisations rows of M (clipped to +-(1-clip))."""
    S = qmc.spins(n).astype(float)
    M = np.clip(np.atleast_2d(M), -1 + clip, 1 - clip)
    lq = np.log((1 + S[:, None, :] * M[None, :, :]) / 2).sum(2)
    w = np.ones(len(M)) / len(M) if weights is None else np.asarray(weights) / np.sum(weights)
    lq = lq + np.log(w)[None, :]
    mx = lq.max(1, keepdims=True)
    return (mx + np.log(np.exp(lq - mx).sum(1, keepdims=True)))[:, 0]


def A_indep(lq, E, beta):
    dim = len(E)
    return d.A_hastings(np.broadcast_to(lq[None, :], (dim, dim)), E, beta)


def tap_fixed_points(Jm, h, beta, starts, rng, iters=300, damp=0.5, tap=True):
    """Damped naive-MF / TAP iteration m_i = tanh(beta(h_i + sum_j J_ij m_j) - Onsager)."""
    n = len(h)
    out = []
    for _ in range(starts):
        m = rng.uniform(-1, 1, n)
        for _ in range(iters):
            fld = beta * (h + Jm @ m)
            if tap:
                fld = fld - beta ** 2 * ((Jm ** 2) @ (1 - m ** 2)) * m
            m = damp * m + (1 - damp) * np.tanh(fld)
        if np.all(np.isfinite(m)):
            out.append(m)
    # dedupe
    uniq = []
    for m in out:
        if not any(np.abs(m - u).max() < 1e-3 for u in uniq):
            uniq.append(m)
    return np.array(uniq)


# ------------------------------------------------------------------ simulated tempering (exact weights)

def st_operator(E, n, betas, top_uniform=True):
    """Simulated tempering on (k, s), K levels, exact log Z weights. Each step: prob 1/2 within-level MH
    (local single flip; at the hottest level 1/2 local + 1/2 uniform if top_uniform), prob 1/2 level move
    k -> k+-1 (each 1/2, rejected at the ends), accept min(1, pi_k'(s)/pi_k(s)). pi(k,s) = pi_k(s)/K.
    Returns sparse symmetrised operator and its top eigenvector phi."""
    K = len(betas)
    dim = len(E)
    QL = d.local_Q(n)
    QU = d.uniform_Q(n)
    lp = np.array([d.logpi(E, b) for b in betas])  # K x dim
    blocks = []
    rows, cols, vals = [], [], []
    diag_extra = np.zeros(K * dim)
    for k, b in enumerate(betas):
        Q = 0.5 * QL + 0.5 * QU if (top_uniform and k == int(np.argmin(betas))) else QL
        A = 0.5 * d.A_sym(Q, E, b)
        Ad = np.diag(A).copy()
        np.fill_diagonal(A, 0.0)
        As = sp.coo_matrix(A)
        rows.append(As.row + k * dim); cols.append(As.col + k * dim); vals.append(As.data)
        diag_extra[k * dim:(k + 1) * dim] += Ad  # = 0.5*(1 - out-rate)
        # level moves
        acc_out = np.zeros(dim)
        for kk in (k - 1, k + 1):
            if 0 <= kk < K:
                acc = np.exp(np.minimum(0.0, lp[kk] - lp[k]))
                acc_out += 0.25 * acc
                sym = 0.25 * np.exp(np.minimum(lp[kk], lp[k]) - 0.5 * (lp[kk] + lp[k]))
                rows.append(np.arange(dim) + k * dim); cols.append(np.arange(dim) + kk * dim); vals.append(sym)
        diag_extra[k * dim:(k + 1) * dim] += 0.5 - acc_out
    rows.append(np.arange(K * dim)); cols.append(np.arange(K * dim)); vals.append(diag_extra)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(K * dim,) * 2)
    phi = np.sqrt(np.exp(lp).ravel() / K)
    return A, phi


def st_target_iat(A, phi, K, dim, target_level):
    """Exact worst-case integrated autocorrelation time of target-level estimates (ratio estimator restricted
    to level `target_level`) for the ST chain: tau_max = K * lambda_max(P0 M00 P0), M = 2(I-A)^-1 - I on phi-perp."""
    Ad = A.toarray() if sp.issparse(A) else A
    N = Ad.shape[0]
    Z = np.linalg.inv(np.eye(N) - Ad + np.outer(phi, phi)) - np.outer(phi, phi)
    M = 2 * Z - (np.eye(N) - np.outer(phi, phi))
    sl = slice(target_level * dim, (target_level + 1) * dim)
    M00 = M[sl, sl]
    u = phi[sl] / np.linalg.norm(phi[sl])
    P0 = np.eye(dim) - np.outer(u, u)
    return float(K * np.linalg.eigvalsh(P0 @ M00 @ P0).max())


def tau_from_relgap(g):
    """Worst-case IAT (1+lambda2)/(1-lambda2) of a reversible chain with relaxation gap g."""
    return (2.0 - g) / g


# ------------------------------------------------------------------ overlap / modes

def overlap_dist(pi, n):
    """P(q12) for two independent replicas: q12 = 1 - 2 d_H/n. Via XOR autocorrelation (FWHT)."""
    dim = len(pi)
    a = np.arange(dim)
    # R(mask) = sum_s pi(s) pi(s^mask) via Walsh-Hadamard
    H = pi.copy()
    h = 1
    while h < dim:
        H = H.reshape(-1, 2, h)
        H = np.stack([H[:, 0] + H[:, 1], H[:, 0] - H[:, 1]], 1).reshape(-1)
        h *= 2
    R = H ** 2
    h = 1
    while h < dim:
        R = R.reshape(-1, 2, h)
        R = np.stack([R[:, 0] + R[:, 1], R[:, 0] - R[:, 1]], 1).reshape(-1)
        h *= 2
    R = R / dim
    hw = np.array([bin(x).count("1") for x in a])
    Pd = np.bincount(hw, weights=R, minlength=n + 1)
    q = 1 - 2 * np.arange(n + 1) / n
    return q, Pd


def basin_masses(E, pi, n):
    mp = descent_map(E, n)
    mins, inv = np.unique(mp, return_inverse=True)
    mass = np.bincount(inv, weights=pi)
    return mins, mass


# ------------------------------------------------------------------ exact SW / Wolff for dense graphs (subset DP)

def _submasks_with_low(S):
    """All T subset of S containing lowest set bit of S (including S)."""
    low = S & (-S)
    rest = S ^ low
    out = []
    t = rest
    while True:
        out.append(t | low)
        if t == 0:
            break
        t = (t - 1) & rest
    return np.array(out, dtype=np.int64)


def cluster_kernels(nv, ed, beta, reps):
    """Exact SW and Wolff transition rows from each state in `reps` (indices on 2^nv), general-sign couplings,
    bond p_e = 1 - exp(-2 beta |J_e|) on satisfied bonds. Subset DP over vertex sets:
      W_s(S)  = sum_{e inside S, e sat in s} log(1-p_e)
      Pc_s(S) = P(random open-bond subgraph on S is connected) = 1 - sum_{T∋low, T⊊S} Pc(T) exp(W(S)-W(T)-W(S\\T))
      Z_s(S)  = sum_{T∋low} (1/2) Pc(T) exp(W(S)-W(T)-W(S\\T)) Z(S\\T)     (random-cluster, q = 1/2)
    SW: P(s -> s^F) = exp(W(V) - W(F) - W(V\\F)) Z(F) Z(V\\F).
    Wolff: P(s -> s^F) = (|F|/nv) Pc(F) exp(W(V) - W(F) - W(V\\F))   (F = the seed's cluster; F nonempty).
    Returns (Psw, Pwolff) of shape (len(reps), 2^nv)."""
    S_ = qmc.spins(nv)
    reps = np.asarray(reps)
    R = len(reps)
    D = 2 ** nv
    W = np.zeros((D, R))
    msk = np.arange(D)
    for (u, v, Jv) in ed:
        p = 1.0 - np.exp(-2.0 * beta * abs(Jv))
        sat = (Jv * S_[reps, u] * S_[reps, v]) > 0  # R
        inside = ((msk >> u) & 1) & ((msk >> v) & 1)  # D
        W += np.outer(inside, sat * np.log(max(1 - p, 1e-300)))
    Pc = np.zeros((D, R))
    Z = np.zeros((D, R))
    Z[0] = 1.0
    for Sm in range(1, D):
        T = _submasks_with_low(Sm)
        Tp = T[:-1] if False else T  # includes S itself (last? order: rest..0) -> find S
        proper = T[T != Sm]
        if len(proper):
            cw = np.exp(W[Sm][None, :] - W[proper] - W[Sm ^ proper])
            Pc[Sm] = 1.0 - (Pc[proper] * cw).sum(0)
        else:
            Pc[Sm] = 1.0
        cwa = np.exp(W[Sm][None, :] - W[T] - W[Sm ^ T])
        Z[Sm] = (0.5 * Pc[T] * cwa * Z[Sm ^ T]).sum(0)
    full = D - 1
    F = np.arange(D)
    cut = np.exp(W[full][:, None] - W[F].T - W[full ^ F].T)  # R x D
    Psw = cut * Z[F].T * Z[full ^ F].T
    size = np.array([bin(x).count("1") for x in F])
    Pw = (size / nv)[None, :] * Pc[F].T * cut
    Pw[:, 0] = 0.0
    # map flip-set F to target state rep ^ F
    tgt = reps[:, None] ^ F[None, :]
    Psw_s = np.zeros((R, D)); Pw_s = np.zeros((R, D))
    np.put_along_axis(Psw_s, tgt, Psw, axis=1)
    np.put_along_axis(Pw_s, tgt, Pw, axis=1)
    return Psw_s, Pw_s
