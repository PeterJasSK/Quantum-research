"""D1 temperature map: shared library (exact, ideal).

Builds on common/qmc.py (not edited). Adds:
  - numerically robust symmetric Metropolis operator and spectral gap (dense or Lanczos),
  - EXACT Swendsen-Wang and Wolff transition matrices for small graphs with general-sign couplings
    (bond activation p_e = 1 - exp(-2 beta |J_e|) on satisfied bonds), via an Edwards-Sokal
    factorisation over all bond subsets (2^m, m = #edges <= 24),
  - ghost-spin embedding for fields (SK with h): Z2-lumped projection, exact,
  - sampled SW/Wolff transition-matrix estimate (for SK n=10, 55 bonds) with bootstrap,
  - quantum proposal kernels with eigendecomposition cache (Layden stratified draws, tuning grid),
  - decohered control with cached eigendecompositions, vectorised coarse-grained (P2) proposal.

State convention as qmc: bit i of index a = spin i (bit 0 -> +1, bit 1 -> -1).
"""
import sys
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import eigsh, LinearOperator

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

# ----------------------------------------------------------------------------- gap

def boltz(E, beta):
    return qmc.boltzmann(E, beta)


def mh_sym(Q, E, beta):
    """Symmetrised Metropolis operator A = D^1/2 P D^-1/2 for a SYMMETRIC proposal Q.
    Off-diagonal A_ab = Q_ab exp(-beta |E_b - E_a| / 2) (exactly symmetric), diagonal = P_aa."""
    dE = E[None, :] - E[:, None]
    A = Q * np.exp(-0.5 * beta * np.abs(dE))
    acc_out = (Q * np.exp(-beta * np.maximum(dE, 0.0)))
    np.fill_diagonal(acc_out, 0.0)
    np.fill_diagonal(A, 1.0 - acc_out.sum(1))
    return A


def gap_sym(A, pi, both=False):
    """Absolute spectral gap 1 - max_{k>=2} |lambda_k| of symmetric A whose top eigvec is sqrt(pi).
    dim <= 2048: full eigvalsh; else Lanczos on the deflated operator. If both: also 1 - lambda_2."""
    u = np.sqrt(pi)
    dim = len(pi)
    if dim <= 2048 or both:
        lam = np.linalg.eigvalsh(A)
        lam = np.sort(lam)
        # drop the eigenvalue closest to 1 (stationary)
        i1 = np.argmin(np.abs(lam - 1.0))
        rest = np.delete(lam, i1)
        g_abs = 1.0 - np.max(np.abs(rest))
        if both:
            return float(g_abs), float(1.0 - rest.max())
        return float(g_abs)
    op = LinearOperator((dim, dim), matvec=lambda x: A @ x - u * (u @ x), dtype=float)
    v0 = np.random.default_rng(0).normal(size=dim)
    w = eigsh(op, k=1, which="LM", v0=v0, tol=0, ncv=40, maxiter=20000, return_eigenvectors=False)
    return float(1.0 - np.max(np.abs(w)))


def gap_Q(Q, E, beta):
    return gap_sym(mh_sym(Q, E, beta), boltz(E, beta))


def gap_P_reversible(P, pi):
    """Gap of a reversible (not necessarily symmetric-proposal) chain P, symmetrised with pi."""
    d = np.sqrt(pi)
    A = (d[:, None] * P) / d[None, :]
    asym = float(np.abs(A - A.T).max())
    A = 0.5 * (A + A.T)
    return gap_sym(A, pi), asym


# ----------------------------------------------------------------------------- regimes

def beta_c_from_C(E, n, lo=0.005, hi=20.0, num=600):
    b = np.exp(np.linspace(np.log(lo), np.log(hi), num))
    C = qmc.thermo(E, n, b)
    return float(b[np.argmax(C)]), float(C.max())


RATIOS = 10 ** np.linspace(-1, 1, 13)  # beta / beta_c, 0.1 .. 10


def regime_of(r):
    return "HIGH" if r <= 0.5 + 1e-9 else ("MEDIUM" if r <= 2.0 + 1e-9 else "LOW")


# ----------------------------------------------------------------------------- graphs

def graph_from_J(J, h=None, ghost=False, tol=1e-14):
    """Edges (u,v,Jval) of the coupling graph. If ghost, add vertex n with bonds h_i."""
    n = J.shape[0]
    ed = [(i, j, J[i, j]) for i in range(n) for j in range(i + 1, n) if abs(J[i, j]) > tol]
    nv = n
    if ghost:
        ed += [(i, n, h[i]) for i in range(n) if abs(h[i]) > tol]
        nv = n + 1
    return nv, ed


def sat_masks(nv, ed):
    """Bitmask over edges of satisfied bonds (J_e s_u s_v > 0), for each of 2^nv states; and W_sat."""
    S = qmc.spins(nv)
    m = len(ed)
    mask = np.zeros(2 ** nv, dtype=np.int64)
    absJ = np.array([abs(e[2]) for e in ed])
    W = np.zeros(2 ** nv)
    for k, (u, v, Jv) in enumerate(ed):
        sat = (Jv * S[:, u] * S[:, v]) > 0
        mask |= sat.astype(np.int64) << k
        W += sat * absJ[k]
    return mask, absJ, W


def component_counts(nv, ed):
    """c[omega] = number of connected components (all nv vertices) of the edge subset omega."""
    m = len(ed)
    lab = np.arange(nv, dtype=np.uint8)[None, :].copy()
    for k, (u, v, _) in enumerate(ed):
        L = lab.copy()
        lu = L[:, u].copy()
        lv = L[:, v].copy()
        mrg = L == lv[:, None]
        L = np.where(mrg, lu[:, None], L).astype(np.uint8)
        lab = np.concatenate([lab, L], axis=0)
    c = (lab == np.arange(nv, dtype=np.uint8)[None, :]).sum(1).astype(np.uint8)
    del lab
    return c


def prob_zeta(f, p):
    """G(X) = sum_{w subset X} prod_{e in w} p_e prod_{e in X\\w} (1-p_e) f(w) over all edge subsets."""
    G = f.astype(float).copy()
    m = len(p)
    for e in range(m):
        Gv = G.reshape(-1, 2, 2 ** e)
        Gv[:, 1, :] = p[e] * Gv[:, 1, :] + (1.0 - p[e]) * Gv[:, 0, :]
    return G


def mask_weight(m, absJ):
    W = np.zeros(2 ** m)
    for e in range(m):
        Wv = W.reshape(-1, 2, 2 ** e)
        Wv[:, 1, :] += absJ[e]
    return W


class ExactCluster:
    """Exact SW and Wolff kernels for a graph with nv vertices and m <= ~24 edges."""

    def __init__(self, nv, ed):
        self.nv, self.ed = nv, ed
        self.m = len(ed)
        self.c = component_counts(nv, ed)
        self.satmask, self.absJ, self.Wsat = sat_masks(nv, ed)
        self.Wmask = mask_weight(self.m, self.absJ)
        self.f_sw = 2.0 ** (-self.c.astype(float))
        # Wolff subsets: connected vertex subsets D
        adj = [[] for _ in range(nv)]
        for k, (u, v, _) in enumerate(ed):
            adj[u].append(v)
            adj[v].append(u)
        self.Ds = []
        for D in range(1, 2 ** nv):
            verts = [i for i in range(nv) if (D >> i) & 1]
            # connectivity of D in graph
            seen = {verts[0]}
            st = [verts[0]]
            while st:
                x = st.pop()
                for y in adj[x]:
                    if (D >> y) & 1 and y not in seen:
                        seen.add(y)
                        st.append(y)
            if len(seen) != len(verts):
                continue
            inner = [k for k, (u, v, _) in enumerate(ed) if (D >> u) & 1 and (D >> v) & 1]
            bnd = [k for k, (u, v, _) in enumerate(ed) if ((D >> u) & 1) != ((D >> v) & 1)]
            # global masks of all subsets of inner edges
            kk = len(inner)
            loc = np.arange(2 ** kk, dtype=np.int64)
            gm = np.zeros(2 ** kk, dtype=np.int64)
            for j, e in enumerate(inner):
                gm |= ((loc >> j) & 1) << e
            conn = (self.c[gm] == (nv - len(verts) + 1)).astype(float)
            # local index of each state's satisfied inner edges
            sl = np.zeros(2 ** nv, dtype=np.int64)
            for j, e in enumerate(inner):
                sl |= ((self.satmask >> e) & 1) << j
            bw = np.zeros(2 ** nv)
            for e in bnd:
                bw += ((self.satmask >> e) & 1) * self.absJ[e]
            self.Ds.append((D, len(verts), np.array(inner, int), conn, sl, bw))

    def pi(self, beta):
        w = 2.0 * beta * (self.Wsat - self.Wsat.max())
        p = np.exp(w)
        return p / p.sum()

    def p_bond(self, beta):
        return 1.0 - np.exp(-2.0 * beta * self.absJ)

    def sw_sym(self, beta):
        """Symmetrised SW operator on 2^nv states (exact)."""
        G = prob_zeta(self.f_sw, self.p_bond(beta))
        X = self.satmask[:, None] & self.satmask[None, :]
        A = G[X] * np.exp(-beta * (self.Wsat[:, None] + self.Wsat[None, :] - 2.0 * self.Wmask[X]))
        return A

    def wolff_P(self, beta):
        """Wolff transition matrix P[s, s xor D] (exact)."""
        dim = 2 ** self.nv
        P = np.zeros((dim, dim))
        p = self.p_bond(beta)
        a = np.arange(dim)
        for (D, size, inner, conn, sl, bw) in self.Ds:
            ct = prob_zeta(conn, p[inner]) if len(inner) else conn
            prob = (size / self.nv) * ct[sl] * np.exp(-2.0 * beta * bw)
            P[a, a ^ D] += prob
        return P


def lump_ghost(Pext, n):
    """Lump a Z2-symmetric chain on n+1 spins (ghost = bit n) to physical spins s_i*s_0."""
    dim = 2 ** n
    full = 2 ** (n + 1) - 1
    X = np.arange(dim)  # representatives with ghost bit 0 (s0=+1)
    return Pext[np.ix_(X, X)] + Pext[np.ix_(X, X ^ full)]


def lump_ghost_sym(Aext, n):
    """Same for a symmetrised operator: since pi_ext(x)=pi_ext(Gx), lumping commutes with symmetrisation
    up to the factor: A_phys = (A[x,y] + A[x,Gy]) ; stationary sqrt(pi_phys) = sqrt(2) sqrt(pi_ext[x])."""
    return lump_ghost(Aext, n)


# ----------------------------------------------------------------------------- sampled clusters

def sampled_cluster_P(nv, ed, beta, nsamp, seed, chunk=32, rows=None):
    """Monte-Carlo estimate of SW and Wolff transition counts on 2^nv states (nsamp moves per state).
    Returns (counts_sw, counts_wolff, mean largest cluster fraction per state)."""
    rng = np.random.default_rng(seed)
    dim = 2 ** nv
    satmask, absJ, _ = sat_masks(nv, ed)
    p = 1.0 - np.exp(-2.0 * beta * absJ)
    Csw = np.zeros((dim, dim), dtype=np.int32)
    Cw = np.zeros((dim, dim), dtype=np.int32)
    lcf = np.zeros(dim)
    pw = (1 << np.arange(nv)).astype(np.int64)
    rows = np.arange(dim) if rows is None else np.asarray(rows)
    for a0 in range(0, len(rows), chunk):
        st = rows[a0:a0 + chunk]
        B = len(st)
        L = np.broadcast_to(np.arange(nv, dtype=np.int16), (B, nsamp, nv)).copy()
        for k, (u, v, _) in enumerate(ed):
            sat = ((satmask[st] >> k) & 1).astype(bool)
            op = (rng.random((B, nsamp)) < p[k]) & sat[:, None]
            lu = L[:, :, u]
            lv = L[:, :, v]
            mrg = (L == lv[:, :, None]) & op[:, :, None]
            L = np.where(mrg, lu[:, :, None], L)
        # SW: random sign per label (labels are vertex ids)
        flipbit = rng.random((B, nsamp, nv)) < 0.5  # flip decision indexed by label id
        fl = np.take_along_axis(flipbit, L.astype(np.int64), axis=2)
        Dsw = (fl * pw).sum(2)
        # Wolff: seed uniform vertex, flip its cluster
        seedv = rng.integers(0, nv, (B, nsamp))
        sl = np.take_along_axis(L, seedv[:, :, None].astype(np.int64), axis=2)
        Dw = ((L == sl) * pw).sum(2)
        # largest cluster fraction
        cnt = np.zeros((B, nsamp, nv), dtype=np.int16)
        for i in range(nv):
            cnt += (L == i)
        lcf[st] = cnt.max(2).mean(1) / nv
        for bi, a in enumerate(st):
            np.add.at(Csw[a], a ^ Dsw[bi], 1)
            np.add.at(Cw[a], a ^ Dw[bi], 1)
    return Csw, Cw, lcf


def gap_from_counts(C, pi, nboot=0, seed=0):
    P = C / C.sum(1, keepdims=True)
    g, asym = gap_P_reversible(P, pi)
    boots = []
    if nboot:
        rng = np.random.default_rng(seed)
        N = int(C.sum(1)[0])
        for b in range(nboot):
            Cb = np.array([rng.multinomial(N, P[i]) for i in range(len(P))])
            boots.append(gap_P_reversible(Cb / N, pi)[0])
    return g, boots


# ----------------------------------------------------------------------------- quantum kernels

LAYDEN_G = (0.25, 0.6)
LAYDEN_T = (2.0, 20.0)


def layden_draws(seed, m_g=4, m_t=4):
    """Stratified draws from Layden's gamma~U[.25,.6], t~U[2,20]: m_g gamma strata midpoints, m_t jittered
    t strata per gamma (m_g*m_t draws). Same expectation as i.i.d. draws, lower variance, few eigh."""
    rng = np.random.default_rng(seed)
    g_lo, g_hi = LAYDEN_G
    t_lo, t_hi = LAYDEN_T
    gs = g_lo + (np.arange(m_g) + 0.5) * (g_hi - g_lo) / m_g
    out = []
    for g in gs:
        tt = t_lo + (np.arange(m_t) + rng.random(m_t)) * (t_hi - t_lo) / m_t
        out += [(float(g), float(t)) for t in tt]
    return out


TUNE_G = [0.1, 0.2] + [0.25 + (k + 0.5) * 0.35 / 4 for k in range(4)] + [0.7, 0.85]
TUNE_W = [(0.3, 1.5), (1.5, 6.0), (6.0, 24.0), (24.0, 96.0)]


def tune_ts(w, m):
    lo, hi = w
    return list(np.exp(np.log(lo) + (np.arange(m) + 0.5) * (np.log(hi) - np.log(lo)) / m))


class QKern:
    """|<b|exp(-i H(g) t)|a>|^2 with H(g) = (1-g) alpha diag(Hprob) + g sum X, eigh cached per gamma."""

    def __init__(self, Hprob, alpha=None):
        self.E = np.asarray(Hprob, float)
        self.n = int(np.log2(len(self.E)))
        self.alpha = qmc.alpha_from_energy(self.E) if alpha is None else alpha
        self.Hm = qmc.mixer(self.n)
        self.cache = {}
        self.Tcache = {}

    def eig(self, g):
        key = round(float(g), 12)
        if key not in self.cache:
            self.cache[key] = eigh(np.diag((1 - g) * self.alpha * self.E) + g * self.Hm)
        return self.cache[key]

    def Qt(self, g, t):
        w, V = self.eig(g)
        Ur = (V * np.cos(w * t)) @ V.T
        Ui = (V * np.sin(w * t)) @ V.T
        return Ur * Ur + Ui * Ui

    def Qavg(self, pairs):
        Q = np.zeros((2 ** self.n, 2 ** self.n))
        for g, t in pairs:
            Q += self.Qt(g, t)
        return Q / len(pairs)

    def decohered(self, pairs, dt=0.25):
        """As qmc.decohered_Q: kernel T_g = |exp(-i H dt_k)|^2 composed k = round(t/dt) times, dt_k = t/k.
        Uses dt_k = dt exactly (k = round(t/dt)) so T_g is cached per gamma; the total time differs
        from t by < dt/2 (immaterial for a fully dephased control)."""
        Q = np.zeros((2 ** self.n, 2 ** self.n))
        for g, t in pairs:
            key = round(float(g), 12)
            if key not in self.Tcache:
                T = self.Qt(g, dt)
                lam, VT = eigh(T)
                self.Tcache[key] = (lam, VT)
            lam, VT = self.Tcache[key]
            k = max(1, int(round(t / dt)))
            Q += (VT * lam ** k) @ VT.T
        Q /= len(pairs)
        Q = np.clip(Q, 0.0, None)
        Q = 0.5 * (Q + Q.T)
        return Q / Q.sum(1, keepdims=True)


# ----------------------------------------------------------------------------- coarse-grained (P2)

def cyclic_groups(n, k):
    return [np.array([(s + j) % n for j in range(k)]) for s in range(n)]


def coarse_grained_Q(J, h, groups, pairs):
    """Vectorised equivalent of qmc.coarse_grained_Q (state-independent uniform group choice).
    Group Hamiltonian: frozen spins outside G enter as h_eff; alpha from std of group energies."""
    n = len(h)
    dim = 2 ** n
    a = np.arange(dim)
    S = qmc.spins(n).astype(float)
    Q = np.zeros((dim, dim))
    pG = 1.0 / len(groups)
    for G in groups:
        k = len(G)
        rest = np.setdiff1d(np.arange(n), G)
        Gmask = int(np.bitwise_or.reduce(1 << G))
        sub = qmc.spins(k).astype(float)
        Hm = qmc.mixer(k)
        rest_key = np.zeros(dim, dtype=np.int64)
        for j, site in enumerate(rest):
            rest_key |= ((a >> site) & 1) << j
        g_key = np.zeros(dim, dtype=np.int64)
        for j, site in enumerate(G):
            g_key |= ((a >> site) & 1) << j
        # target table
        gb = np.arange(2 ** k)
        spread = np.zeros(2 ** k, dtype=np.int64)
        for j, site in enumerate(G):
            spread |= ((gb >> j) & 1) << site
        btab = (a & ~Gmask)[:, None] | spread[None, :]
        JG = J[np.ix_(G, G)]
        Qg_all = {}
        for rk in np.unique(rest_key):
            a0 = int(np.nonzero(rest_key == rk)[0][0])
            heff = h[G] + J[np.ix_(G, rest)] @ S[a0, rest]
            Eg = -0.5 * np.einsum("ai,ij,aj->a", sub, JG, sub) - sub @ heff
            kern = QKern(Eg)
            kern.Hm = Hm
            Qg_all[rk] = kern.Qavg(pairs)
        Qstack = np.stack([Qg_all[rk] for rk in range(2 ** len(rest))])
        Q[a[:, None], btab] += pG * Qstack[rest_key, g_key, :]
    return Q
