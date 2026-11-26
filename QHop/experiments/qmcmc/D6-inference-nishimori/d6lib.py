"""D6 Nishimori transfer test: shared library (exact, ideal).

Builds on common/qmc.py (not edited). QKern / layden_draws are copied (with small changes) from
D1-temperature-map/d1lib.py. All chains are exact 2^n matrices.

Kernels are handled as SYMMETRISED operators A = D^1/2 P D^-1/2 (D = diag pi). A mixture of MH kernels
(choose a move type with fixed probability, then its own MH accept) is reversible and its symmetrised
operator is the same mixture of the A's, so every mixture costs one eigvalsh.

Gaps: we report both the relaxation gap 1 - lambda_2 (primary: equals 2x the absolute gap of the lazy
chain, so it is not distorted by near-periodic local flips at high T) and the absolute gap
1 - max_{k>=2}|lambda_k| (P1 convention).
"""
import sys
import numpy as np
from scipy.linalg import eigh

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

LAYDEN_G = (0.25, 0.6)
LAYDEN_T = (2.0, 20.0)


def bits(n):
    """x[a, i] = bit i of a (0/1)."""
    a = np.arange(2 ** n)
    return ((a[:, None] >> np.arange(n)) & 1)


def logpi(E, beta):
    l = -beta * (E - E.min())
    return l - np.log(np.exp(l).sum())


def layden_draws(seed, m_g=4, m_t=4):
    rng = np.random.default_rng(seed)
    gs = LAYDEN_G[0] + (np.arange(m_g) + 0.5) * (LAYDEN_G[1] - LAYDEN_G[0]) / m_g
    out = []
    for g in gs:
        tt = LAYDEN_T[0] + (np.arange(m_t) + rng.random(m_t)) * (LAYDEN_T[1] - LAYDEN_T[0]) / m_t
        out += [(float(g), float(t)) for t in tt]
    return out


class QKern:
    """|<b|exp(-i H(g) t)|a>|^2, H(g) = (1-g) alpha diag(Hprob) + g sum X; alpha = sqrt(n)/std(Hprob)."""

    def __init__(self, Hprob):
        self.E = np.asarray(Hprob, float)
        self.n = int(round(np.log2(len(self.E))))
        self.alpha = qmc.alpha_from_energy(self.E)
        self.Hm = qmc.mixer(self.n)
        self.cache, self.Tcache = {}, {}

    def eig(self, g):
        k = round(float(g), 12)
        if k not in self.cache:
            self.cache[k] = eigh(np.diag((1 - g) * self.alpha * self.E) + g * self.Hm)
        return self.cache[k]

    def Qt(self, g, t):
        w, V = self.eig(g)
        Ur = (V * np.cos(w * t)) @ V.T
        Ui = (V * np.sin(w * t)) @ V.T
        return Ur * Ur + Ui * Ui

    def Qavg(self, pairs):
        Q = sum(self.Qt(g, t) for g, t in pairs) / len(pairs)
        return 0.5 * (Q + Q.T)

    def decohered(self, pairs, dt=0.25):
        Q = np.zeros((2 ** self.n,) * 2)
        for g, t in pairs:
            k = round(float(g), 12)
            if k not in self.Tcache:
                self.Tcache[k] = eigh(self.Qt(g, dt))
            lam, VT = self.Tcache[k]
            Q += (VT * lam ** max(1, int(round(t / dt)))) @ VT.T
        Q = np.clip(Q / len(pairs), 0.0, None)
        Q = 0.5 * (Q + Q.T)
        return Q / Q.sum(1, keepdims=True)


# ------------------------------------------------------------------ symmetrised MH operators

def A_sym(Q, E, beta):
    """Symmetric proposal Q: A_ab = Q_ab exp(-beta|dE|/2); diagonal = rejection mass."""
    dE = E[None, :] - E[:, None]
    A = Q * np.exp(-0.5 * beta * np.abs(dE))
    out = Q * np.exp(-beta * np.maximum(dE, 0.0))
    np.fill_diagonal(out, 0.0)
    np.fill_diagonal(A, 1.0 - out.sum(1))
    return A


def A_hastings(logQ, E, beta):
    """General proposal given as log Q (-inf for zero). pi_a P_ab = min(pi_a Q_ab, pi_b Q_ba)."""
    lp = logpi(E, beta)
    with np.errstate(invalid="ignore"):
        fwd = lp[:, None] + logQ
        bwd = lp[None, :] + logQ.T
        m = np.minimum(fwd, bwd)
        A = np.exp(m - 0.5 * (lp[:, None] + lp[None, :]))
        P = np.exp(m - lp[:, None])
    A = np.nan_to_num(A)
    P = np.nan_to_num(P)
    np.fill_diagonal(P, 0.0)
    np.fill_diagonal(A, 1.0 - P.sum(1))
    return A


def A_hot_indep(E, beta, beta_hot):
    """Independence proposal from the hotter posterior pi_{beta_hot} (idealised 2-replica PT proxy)."""
    lh = logpi(E, beta_hot)
    logQ = np.broadcast_to(lh[None, :], (len(E), len(E)))
    return A_hastings(logQ, E, beta)


def gaps(A):
    """(relaxation gap 1-lambda_2, absolute gap) of symmetric A with top eigenvalue 1."""
    lam = np.linalg.eigvalsh(A)
    i1 = np.argmin(np.abs(lam - 1.0))
    rest = np.delete(lam, i1)
    return float(1.0 - rest.max()), float(1.0 - np.abs(rest).max())


def flip_Q(n, masks):
    """Symmetric proposal: XOR with a mask drawn uniformly from `masks` (each mask an involution)."""
    dim = 2 ** n
    Q = np.zeros((dim, dim))
    a = np.arange(dim)
    for m in masks:
        Q[a, a ^ m] += 1.0 / len(masks)
    return Q


def local_Q(n):
    return flip_Q(n, [1 << i for i in range(n)])


def uniform_Q(n):
    return np.full((2 ** n, 2 ** n), 1.0 / 2 ** n)


def nishimori_stats(E, beta, x0_index, n):
    """Planted overlap m = <s.s0>/n, replica overlap q = sum_i <s_i>^2/n, and P(q) spread:
    Var of the two-replica overlap q12 under pi x pi, and P(|q12| < 0.5)."""
    pi = np.exp(logpi(E, beta))
    S = qmc.spins(n).astype(float)
    s0 = S[x0_index]
    m = float(pi @ (S @ s0)) / n
    mag = pi @ S
    q = float(mag @ mag) / n
    # distribution of q12 = s.s'/n: compute via overlap-with-s xor s'; use distribution of S
    # q12 = sum_i s_i s'_i / n; E[q12^2] = sum_ij C_ij^2 / n^2 with C_ij = <s_i s_j>
    C = (S * pi[:, None]).T @ S
    q2 = float((C ** 2).sum()) / n ** 2
    return m, q, q2 - q ** 2


def beta_peak(E, n, lo=0.01, hi=100.0, num=400):
    b = np.exp(np.linspace(np.log(lo), np.log(hi), num))
    C = qmc.thermo(E, n, b)
    return float(b[np.argmax(C)])


# ------------------------------------------------------------------ exact Swendsen-Wang with field

def exact_sw_A(edges, Jvals, h, beta):
    """Exact SW kernel for a FERROMAGNETIC graph (J_e > 0) with external field h, field handled by
    heat-bath choice of each cluster's new sign (P(sigma) ~ exp(beta sigma h_C)). Returns symmetrised
    operator on 2^n states.  P(s,s') = exp(beta h.s') prod_{e in sat(s)} (1-p_e) G[sat(s)&sat(s')],
    G(X) = sum_{w subset X} prod_{e in w} p_e/(1-p_e) / prod_C 2cosh(beta h_C(w)).
    pi(s)P(s,s') is symmetric -> reversible (checked numerically in callers)."""
    n = len(h)
    m = len(edges)
    S = qmc.spins(n)
    Jvals = np.asarray(Jvals, float)
    assert np.all(Jvals > 0)
    p = 1.0 - np.exp(-2.0 * beta * Jvals)
    # component labels for all 2^m bond subsets (vectorised union by relabel)
    lab = np.arange(n, dtype=np.int16)[None, :].copy()
    for k, (u, v) in enumerate(edges):
        L = lab.copy()
        lu, lv = L[:, u].copy(), L[:, v].copy()
        L = np.where(L == lv[:, None], lu[:, None], L).astype(np.int16)
        lab = np.concatenate([lab, L], axis=0)
    # lab row index = subset mask (bit k = edge k), by construction of concatenation order
    hC = np.zeros((2 ** m, n))
    for i in range(n):
        np.add.at(hC, (np.arange(2 ** m), lab[:, i]), h[i])
    logZ = np.log(2.0 * np.cosh(beta * hC)).sum(1)  # empty labels contribute log 2 each -> constant
    lw = np.zeros(2 ** m)
    msk = np.arange(2 ** m)
    for k in range(m):
        lw += ((msk >> k) & 1) * np.log(p[k] / (1 - p[k]))
    sat = np.zeros(2 ** n, dtype=np.int64)
    l1m = np.zeros(2 ** n)
    for k, (u, v) in enumerate(edges):
        s_ = (S[:, u] == S[:, v])
        sat |= s_.astype(np.int64) << k
        l1m += s_ * np.log(1 - p[k])
    hs = S @ h
    # empty-label correction: labels with no vertex have hC=0 -> 2cosh(0)=2 factor each, n - #clusters
    # of them; compensate: the true Z_w = prod over actual clusters only.
    ncl = (lab == np.arange(n, dtype=np.int16)[None, :]).sum(1)
    f = np.exp(lw - (logZ - (n - ncl) * np.log(2.0)))
    G = f.copy()
    for k in range(m):
        Gv = G.reshape(-1, 2, 2 ** k)
        Gv[:, 1, :] += Gv[:, 0, :]
    P = np.exp(beta * hs[None, :] + l1m[:, None]) * G[sat[:, None] & sat[None, :]]
    rs = P.sum(1)
    assert np.allclose(rs, 1.0, atol=1e-8), (rs.min(), rs.max())
    E = -np.array([sum(Jvals[k] * S[a, u] * S[a, v] for k, (u, v) in enumerate(edges)) for a in range(2 ** n)]) - hs
    lp = logpi(E, beta)
    d = np.exp(0.5 * lp)
    A = (d[:, None] * P) / d[None, :]
    asym = float(np.abs(A - A.T).max())
    return 0.5 * (A + A.T), asym, E


# ------------------------------------------------------------------ generic evaluation of one posterior

def evaluate(E, n, betas, structured=None, x0_index=None, draw_seed=0, lean=False, extra=None):
    """Exact gaps of classical and quantum kernels on pi ~ exp(-beta E) for beta in betas.
    structured: dict name -> ('sym', Q) or ('log', logQ) classical move kernels (ghost / swap moves).
    Classical families (all one proposal per step unless charged):
      C1 (cheap moves): L, U, LU and, per structured move k: k, Lk, LUk (lean: Lk, LUk).
      PT proxy (charged): mixture (1-w) M + w H(beta_h), M = L (and Lk), H = independence proposal from
        pi_{beta_h} with beta_h in {0.5, 0.25} x beta_peak (HIGH regime, capped at beta/2); each H proposal is
        charged k_h = 1/gap_L(beta_h) proposals (cost of one fresh hot sample by local Metropolis):
        effective gap = gap / ((1-w) + w k_h), w in {0.5, 0.2, 0.05}. Idealised 2-replica PT with a perfectly
        decorrelated hot replica refreshed by local moves.
      ORACLE (reported, NOT in best): L + independence from pi_{beta/2}, uncharged (assumes free exact samples).
    best_classical = max(C1, PT proxy). Quantum: Q (pure QeMCMC, Layden), D (decohered), QL (Q/L 50:50)."""
    structured = structured or {}
    pairs = layden_draws(draw_seed)
    kern = QKern(E)
    Qq = kern.Qavg(pairs)
    Qd = kern.decohered(pairs)
    QL, QU = local_Q(n), uniform_Q(n)
    bpk = beta_peak(E, n)
    bh_list = [0.5 * bpk] if lean else [0.5 * bpk, 0.25 * bpk]
    ws = (0.5, 0.1) if lean else (0.5, 0.2, 0.05)
    kh = {}
    rows = []
    for beta in betas:
        AL, AU = A_sym(QL, E, beta), A_sym(QU, E, beta)
        Ak = {k: (A_sym(M, E, beta) if kind == "sym" else A_hastings(M, E, beta))
              for k, (kind, M) in structured.items()}
        res = {"beta": beta, "beta_peak": bpk}
        if x0_index is not None:
            m, q, vq = nishimori_stats(E, beta, x0_index, n)
            res.update(m_planted=m, q_replica=q, var_q12=vq)
        c1 = {"L": AL, "U": AU, "LU": 0.5 * (AL + AU)}
        for k, A in Ak.items():
            if not lean:
                c1[k] = A
            c1[f"L{k}"] = 0.5 * (AL + A)
            c1[f"LU{k}"] = (AL + AU + A) / 3
        best, best_name, weak = -1.0, None, -1.0
        for name, A in c1.items():
            gr, ga = gaps(A)
            res[f"g_{name}"], res[f"ga_{name}"] = gr, ga
            if gr > best:
                best, best_name = gr, name
            if name in ("L", "U", "LU"):
                weak = max(weak, gr)
        res["best_C1"], res["best_C1_name"] = best, best_name
        ptb = -1.0
        for j, bh0 in enumerate(bh_list):
            bh = min(bh0, beta / 2)
            kb = round(bh, 10)
            if kb not in kh:
                kh[kb] = 1.0 / max(gaps(A_sym(QL, E, bh))[0], 1e-15)
            AH = A_hot_indep(E, beta, bh)
            bases = {"L": AL}
            for k in Ak:
                bases[f"L{k}"] = c1[f"L{k}"]
            for bn, M in bases.items():
                for w in ws:
                    g = gaps((1 - w) * M + w * AH)[0] / ((1 - w) + w * kh[kb])
                    if g > ptb:
                        ptb = g
                        res.update(PT_name=f"{bn}+H(bh={bh:.3g},w={w})", PT_kh=kh[kb])
        res["g_PT"] = ptb
        if ptb > best:
            best, best_name = ptb, "PTproxy"
        if not lean:
            res["g_ORACLE"] = gaps(0.5 * (AL + A_hot_indep(E, beta, beta / 2)))[0]
        AQ, AD = A_sym(Qq, E, beta), A_sym(Qd, E, beta)
        for name, A in (("Q", AQ), ("D", AD), ("QL", 0.5 * (AQ + AL))):
            res[f"g_{name}"], res[f"ga_{name}"] = gaps(A)
        res.update(best_classical=best, best_name=best_name, weak_classical=weak,
                   S=res["g_Q"] / best, S_C1=res["g_Q"] / res["best_C1"], S_weak=res["g_Q"] / weak,
                   S_dec=res["g_D"] / best, S_QL=res["g_QL"] / best, Q_over_D=res["g_Q"] / res["g_D"],
                   S_abs_weak=res["ga_Q"] / max(res["ga_L"], res["ga_U"], res["ga_LU"]),
                   alpha_layden=kern.alpha, below_precision=bool(best < 1e-12))
        if not lean:
            res["S_oracle"] = res["g_Q"] / res["g_ORACLE"]
        if extra:
            res.update(extra)
        rows.append(res)
    return rows
