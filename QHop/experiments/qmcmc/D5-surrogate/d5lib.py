"""D5 surrogate-driven QeMCMC vs classical delayed acceptance (exact linear algebra).

Conventions follow common/qmc.py (state index a, bit i -> spin i).
Families of true energies (all normalised so std(E_true) = std(E_SK)):
  a: E_true = sqrt(1-rho^2) E_SK + rho sd u34    (u34 = random dense 3-body + 4-body, unit std, Walsh-orthogonal to
     the quadratic space)  -> LS quadratic fit on all states = sqrt(1-rho^2) E_SK exactly, residual ratio = rho exactly.
  b: E_true = sqrt(1-rho^2) E_SK + rho sd xi       (xi = iid N(0,1) per state, projected orthogonal to the quadratic
     space, unit std)  -> same surrogate, residual unstructured.
  c: E_true = norm[ g_a(z) + eps sd(g) u34 ], z = standardised E_SK, g_a(z) = (1 - exp(-a z))/a  (monotone, -> z at a=0),
     eps = 0.1; surrogate = LS quadratic fit of E_true on all states; a tuned to hit the target residual ratio rho.
"""
import sys
import itertools
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm as _norm

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

GAMMA_GRID = np.array([0.275, 0.375, 0.475, 0.575])  # bin midpoints of U[0.25,0.6] (eigh caching)


# ------------------------------------------------------------------ energies

def quad_design(n):
    s = qmc.spins(n).astype(float)
    cols = [np.ones(len(s))] + [s[:, i] for i in range(n)]
    cols += [s[:, i] * s[:, j] for i, j in itertools.combinations(range(n), 2)]
    return np.stack(cols, 1)


def fit_quadratic(E, X):
    coef, *_ = np.linalg.lstsq(X, E, rcond=None)
    return X @ coef


def higher_order(n, seed):
    """Dense random 3-body + 4-body energy, unit std, zero mean (pure Walsh degree 3 and 4)."""
    g = np.random.default_rng(seed)
    s = qmc.spins(n).astype(float)
    E3 = np.zeros(2 ** n)
    for c in itertools.combinations(range(n), 3):
        E3 += g.normal() * s[:, c[0]] * s[:, c[1]] * s[:, c[2]]
    E4 = np.zeros(2 ** n)
    for c in itertools.combinations(range(n), 4):
        E4 += g.normal() * s[:, c[0]] * s[:, c[1]] * s[:, c[2]] * s[:, c[3]]
    u = E3 / E3.std() + E4 / E4.std()
    return (u - u.mean()) / u.std()


def iid_noise_perp(n, seed, X):
    g = np.random.default_rng(seed)
    xi = g.normal(size=2 ** n)
    xi = xi - fit_quadratic(xi, X)
    return xi / xi.std()


def make_family(fam, n, inst, rho, X, cache):
    """Return E_true, E_sur, info dict. cache holds per-instance base energies."""
    if "Esk" not in cache:
        J, h = qmc.sk_instance(n, seed=1000 * n + inst)
        Esk = qmc.ising_energies(J, h)
        cache["Esk"] = Esk - Esk.mean()
        cache["u34"] = higher_order(n, seed=1000 * n + inst + 500)
        cache["xi"] = iid_noise_perp(n, 1000 * n + inst + 700, X)
    Esk, u34, xi = cache["Esk"], cache["u34"], cache["xi"]
    sd = Esk.std()
    if fam in ("a", "b"):
        res = u34 if fam == "a" else xi
        Et = np.sqrt(1 - rho ** 2) * Esk + rho * sd * res
        Es = np.sqrt(1 - rho ** 2) * Esk
        par = None
    elif fam == "c":
        z = Esk / sd
        eps = 0.1

        def build(a):
            gz = z if a < 1e-9 else (1 - np.exp(-a * z)) / a
            Et = gz + eps * gz.std() * u34
            Et = (Et - Et.mean()) / Et.std() * sd
            Es = fit_quadratic(Et, X)
            return Et, Es

        def r_of(a):
            Et, Es = build(a)
            return (Et - Es).std() / Et.std()

        r0 = r_of(0.0)
        if rho <= r0 + 1e-9:
            par = 0.0
        else:
            hi = 8.0
            if r_of(hi) < rho:
                return None
            par = brentq(lambda a: r_of(a) - rho, 0.0, hi, xtol=1e-6)
        Et, Es = build(par)
    else:
        raise ValueError(fam)
    info = dict(rho_actual=float((Et - Es).std() / Et.std()), sigma_abs=float((Et - Es).std()),
                sd_true=float(Et.std()), param=par)
    return Et, Es, info


# ------------------------------------------------------------------ proposals and kernels

def qparams(seed, m=16):
    g = np.random.default_rng(seed)
    return GAMMA_GRID[g.integers(0, len(GAMMA_GRID), m)], g.uniform(2.0, 20.0, m)


def quantum_Q_sym(E, gam, ts):
    Q = qmc.quantum_Q(E, gam, ts)
    return 0.5 * (Q + Q.T)  # exactly symmetric in exact arithmetic; remove roundoff asymmetry


def decohered_Q_sym(E, gam, ts):
    Q = qmc.decohered_Q(E, gam, ts)
    return 0.5 * (Q + Q.T)


def logpi(E, beta):
    lw = -beta * (E - E.min())
    return lw - np.logaddexp.reduce(lw)


def mh_sym(Q, E, beta):
    """Metropolis with a symmetric proposal Q on energy E."""
    M = -beta * (E[None, :] - E[:, None])
    P = Q * np.exp(np.minimum(0.0, M))
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return P


def da_outer(Kmat, Et, Es, beta):
    """Delayed acceptance / surrogate transition: proposal kernel Kmat reversible w.r.t. pi_sur(beta);
    accept min(1, pi_t(s') pi_s(s) / (pi_t(s) pi_s(s')))."""
    lw = -beta * (Et - Es)
    M = lw[None, :] - lw[:, None]
    P = Kmat * np.exp(np.minimum(0.0, M))
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return P


def da_naive(Kmat, Et, beta):
    """WRONG control: asymmetric kernel Kmat with plain Metropolis ratio pi_t(s')/pi_t(s) (no Hastings correction)."""
    return mh_sym(Kmat, Et, beta)


def independence_kernel(Es, beta):
    p = np.exp(logpi(Es, beta))
    return np.tile(p, (len(p), 1))


def gap_rev(P):
    """Spectral gap 1 - max|lambda_2| of a pi-reversible P via A = sqrt(P o P^T) (= D^1/2 P D^-1/2)."""
    A = np.sqrt(np.maximum(P, 0.0) * np.maximum(P.T, 0.0))
    lam = np.linalg.eigvalsh(A)
    lam = np.sort(np.abs(lam))[::-1]
    return float(max(1.0 - lam[1], 0.0))


def move_stats(P, Kprop, lp):
    """move rate = P(state changes) at equilibrium; cond acceptance = move rate / P(proposal != current)."""
    pi = np.exp(lp)
    mv = float(1.0 - (pi * np.diag(P)).sum())
    prop_off = float(1.0 - (pi * np.diag(Kprop)).sum())
    return mv, (mv / prop_off if prop_off > 0 else np.nan)


def stationarity(P, lp):
    pi = np.exp(lp)
    st = float(np.abs(pi @ P - pi).sum())
    F = pi[:, None] * P
    db = float(np.abs(F - F.T).sum())
    return st, db


def stationary_dist(P):
    w, V = np.linalg.eig(P.T)
    k = np.argmin(np.abs(w - 1))
    v = np.real(V[:, k])
    return v / v.sum()


def residual_only_acceptance(Kprop, Et, Es, beta, lp_true):
    """E_{s~pi_t, s'~K(s,.)}[ min(1, exp(-beta (r(s') - r(s)))) ], excluding s'=s (what 2 Phi predicts)."""
    pi = np.exp(lp_true)
    r = Et - Es
    M = -beta * (r[None, :] - r[:, None])
    A = np.exp(np.minimum(0.0, M))
    W = pi[:, None] * Kprop
    np.fill_diagonal(W, 0.0)
    return float((W * A).sum() / W.sum())


def two_phi(x):
    return 2.0 * _norm.cdf(-np.asarray(x) / np.sqrt(2.0))


def matpow10(P):
    p2 = P @ P
    p4 = p2 @ p2
    p8 = p4 @ p4
    return p8 @ p2


def regime_betas(Et, n, grid=None):
    grid = np.logspace(-2.5, 1.0, 141) if grid is None else grid
    C = qmc.thermo(Et, n, grid)
    bc = float(grid[np.argmax(C)])
    return bc, dict(HIGH=bc / 3.0, MEDIUM=bc, LOW=3.0 * bc), grid, C
