"""D8 conserving-mixer library: fixed-composition (Kawasaki) sector, energies, proposals, Trotter, exact IAT.
All matrices live in the fixed-weight sector (n sites, k occupied; n=12,k=6 -> 924 states).
Occupation x_i in {0,1}; spin s_i = 2x_i - 1 (charge q_i = s_i for the Coulomb family).
"""
import itertools
import sys

import numpy as np
from scipy.linalg import eigh

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

# ------------------------------------------------------------------ sector


def sector(n, k):
    states = np.array([sum(1 << i for i in c) for c in itertools.combinations(range(n), k)], dtype=np.int64)
    index = {int(s): a for a, s in enumerate(states)}
    occ = ((states[:, None] >> np.arange(n)[None, :]) & 1).astype(float)  # (D, n)
    return states, index, occ


def swap_neighbours(states, index, i, j):
    """For edge (i,j): array nb[a] = index of state with x_i,x_j swapped, or -1 if x_i == x_j."""
    nb = -np.ones(len(states), dtype=np.int64)
    for a, s in enumerate(states):
        if ((s >> i) & 1) != ((s >> j) & 1):
            nb[a] = index[int(s ^ ((1 << i) | (1 << j)))]
    return nb


def hop_matrix(states, index, edges):
    """H_XY restricted to the sector: sum_e (X_iX_j + Y_iY_j)/2 = sum_e (s+_i s-_j + h.c.) -> 0/1 hopping."""
    D = len(states)
    H = np.zeros((D, D))
    nbs = []
    for (i, j) in edges:
        nb = swap_neighbours(states, index, i, j)
        a = np.where(nb >= 0)[0]
        H[a, nb[a]] += 1.0
        nbs.append(nb)
    return H, nbs


# ------------------------------------------------------------------ lattice 3 x 4 periodic (also 2 x 7 for n=14)


def torus(L1, L2):
    n = L1 * L2
    pos = np.array([(r, c) for r in range(L1) for c in range(L2)], float)
    def idx(r, c):
        return (r % L1) * L2 + (c % L2)
    nn, nnn = set(), set()
    for r in range(L1):
        for c in range(L2):
            a = idx(r, c)
            for dr, dc in ((1, 0), (0, 1)):
                b = idx(r + dr, c + dc)
                if a != b:
                    nn.add(tuple(sorted((a, b))))
            for dr, dc in ((1, 1), (1, -1)):
                b = idx(r + dr, c + dc)
                if a != b:
                    nnn.add(tuple(sorted((a, b))))
    nnn -= nn
    return n, pos, sorted(nn), sorted(nnn)


def min_image_dist(pos, L1, L2):
    d = pos[:, None, :] - pos[None, :, :]
    d[..., 0] -= L1 * np.round(d[..., 0] / L1)
    d[..., 1] -= L2 * np.round(d[..., 1] / L2)
    return np.sqrt((d ** 2).sum(-1))


def ring_edges(n):
    return [(i, (i + 1) % n) for i in range(n)]


def complete_edges(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def snake_ring(L1, L2):
    """Hamiltonian cycle on the torus grid that uses lattice NN bonds where possible (boustrophedon + wrap)."""
    order = []
    for r in range(L1):
        cols = range(L2) if r % 2 == 0 else range(L2 - 1, -1, -1)
        order += [r * L2 + c for c in cols]
    return [tuple(sorted((order[i], order[(i + 1) % len(order)]))) for i in range(len(order))]


# ------------------------------------------------------------------ energy families (spin form, s = 2x-1)


def pair_energy(occ, J):
    s = 2 * occ - 1
    return 0.5 * np.einsum("ai,ij,aj->a", s, J, s)


def fam_cuau(L1, L2, seed):
    """CuAu-like ordering CE: antiferro NN (J1>0 favours unlike NN) + ferro NNN (J2<0), 10% bond noise per instance.
    seed 0 = clean J1=1, J2=-0.5. Frustration from the odd periodic length L1=3 (checkerboard does not fit)."""
    n, pos, nn, nnn = torus(L1, L2)
    g = np.random.default_rng(1000 + seed)
    J1, J2 = 1.0, (-0.5 if seed == 0 else g.uniform(-0.7, -0.3))
    noise = 0.0 if seed == 0 else 0.1
    J = np.zeros((n, n))
    for (i, j) in nn:
        J[i, j] = J[j, i] = J1 * (1 + noise * g.standard_normal())
    for (i, j) in nnn:
        J[i, j] = J[j, i] = J2 * (1 + noise * g.standard_normal())
    return J, dict(J1=J1, J2=J2, noise=noise)


def fam_coulomb(L1, L2, seed, lam=2.0, jitter=0.15):
    """Screened Coulomb (Yukawa) between +-1 charges, minimum image on the L1xL2 torus, charge balanced (k = n/2).
    seed 0 = perfect lattice; others: random site displacements (std `jitter` lattice units) = disorder instances."""
    n, pos, _, _ = torus(L1, L2)
    g = np.random.default_rng(2000 + seed)
    p = pos + (0.0 if seed == 0 else jitter * g.standard_normal(pos.shape))
    r = min_image_dist(p, L1, L2)
    J = np.zeros((n, n))
    m = ~np.eye(n, dtype=bool)
    J[m] = np.exp(-r[m] / lam) / r[m]
    return J, dict(lam=lam, jitter=0.0 if seed == 0 else jitter)


def fam_sk(n, seed):
    """SK J_ij ~ N(0,1)/sqrt(n) at fixed magnetisation 0 (frustrated control), no field."""
    g = np.random.default_rng(3000 + seed)
    A = g.standard_normal((n, n)) / np.sqrt(n)
    J = np.triu(A, 1)
    return J + J.T, dict()


# ------------------------------------------------------------------ classical proposals (symmetric)


def swap_Q(nbs, D):
    """Pick one of the M edges uniformly; swap if unlike, else stay. Symmetric."""
    Q = np.zeros((D, D))
    M = len(nbs)
    for nb in nbs:
        a = np.where(nb >= 0)[0]
        Q[a, nb[a]] += 1.0 / M
        b = np.where(nb < 0)[0]
        Q[b, b] += 1.0 / M
    return Q


def uniform_Q(D):
    return np.full((D, D), 1.0 / D)


# ------------------------------------------------------------------ quantum proposals


def mixer_scale(Hm, n):
    """Normalise so the rms row norm of the mixer equals sqrt(n) as for P1's X mixer (degree n): scale = sqrt(n/mean_deg)."""
    deg = (Hm != 0).sum(1).mean()
    return float(np.sqrt(n / deg))


def quantum_Q(E, Hm, gammas, ts, alpha):
    D = len(E)
    Q = np.zeros((D, D))
    cache = {}
    for g, t in zip(gammas, ts):
        key = round(float(g), 12)
        if key not in cache:
            cache[key] = eigh(np.diag((1 - g) * alpha * E) + g * Hm)
        w, V = cache[key]
        U = (V * np.exp(-1j * w * t)) @ V.T
        Q += np.abs(U) ** 2
    return Q / len(gammas)


def decohered_Q(E, Hm, gammas, ts, alpha, dt=0.25):
    """Full Z-dephasing every dt (slice = exactly dt, k = round(t/dt) slices): T = |exp(-iH dt)|^2 is real symmetric,
    so T^k = W diag(l^k) W^T from one eigh per distinct gamma."""
    D = len(E)
    Q = np.zeros((D, D))
    cache = {}
    for g, t in zip(gammas, ts):
        key = round(float(g), 12)
        if key not in cache:
            w, V = eigh(np.diag((1 - g) * alpha * E) + g * Hm)
            Ud = (V * np.exp(-1j * w * dt)) @ V.T
            cache[key] = eigh(np.abs(Ud) ** 2)
        lt, Wt = cache[key]
        kk = max(1, int(round(t / dt)))
        Q += (Wt * lt ** kk) @ Wt.T
    return Q / len(gammas)


def draw(seed, m, grid=(0.25, 0.32, 0.39, 0.46, 0.53, 0.6)):
    g = np.random.default_rng(seed)
    return g.choice(grid, m), g.uniform(2.0, 20.0, m)


# ------------------------------------------------------------------ gaps, exact IAT


def mh(Q, E, beta):
    return qmc.mh_matrix(Q, E, beta)


def gap(Q, E, beta):
    return qmc.gap(Q, E, beta)


def exact_iat(Q, E, beta, fs):
    """Exact integrated autocorrelation times tau_f = sum_k (1+l_k)/(1-l_k) c_k^2 / sum c_k^2 (reversible P)."""
    P = qmc.mh_matrix(Q, E, beta)
    pi = qmc.boltzmann(E, beta)
    d = np.sqrt(pi)
    A = (d[:, None] * P) / d[None, :]
    A = 0.5 * (A + A.T)
    lam, W = eigh(A)
    out = []
    for f in fs:
        fc = f - (pi * f).sum()
        c = W.T @ (d * fc)
        keep = lam < 1 - 1e-10
        c2 = c[keep] ** 2
        out.append(float(((1 + lam[keep]) / (1 - lam[keep]) * c2).sum() / c2.sum()) if c2.sum() > 0 else np.nan)
    gap_ = 1 - np.sort(np.abs(lam))[::-1][1]
    return out, float(gap_)


def thermo_curve(E, Ts):
    out = []
    for T in Ts:
        p = qmc.boltzmann(E, 1.0 / T)
        m1 = (p * E).sum()
        out.append(((p * E * E).sum() - m1 * m1) / T ** 2)
    return np.array(out)


def find_Tc(E, n):
    """Specific-heat peak of the canonical ensemble (exact): coarse log grid then refine."""
    sd = np.std(E)
    Ts = np.geomspace(sd * 1e-3, sd * 10, 400)
    C = thermo_curve(E, Ts)
    i = int(np.argmax(C))
    Tf = np.geomspace(Ts[max(i - 2, 0)], Ts[min(i + 2, len(Ts) - 1)], 200)
    Cf = thermo_curve(E, Tf)
    j = int(np.argmax(Cf))
    return float(Tf[j]), float(Cf[j] / n)


# ------------------------------------------------------------------ Trotter in the sector


def edge_colouring(edges):
    cols = []
    for e in edges:
        for c in cols:
            if all(len(set(e) & set(f)) == 0 for f in c):
                c.append(e)
                break
        else:
            cols.append([e])
    return cols


def xy_gate(nb, theta, D):
    """exp(-i theta G_e), G_e^2 = P_e (unlike projector): 1 - P_e + cos(theta) P_e - i sin(theta) G_e."""
    U = np.eye(D, dtype=complex)
    a = np.where(nb >= 0)[0]
    U[a, a] = np.cos(theta)
    U[a, nb[a]] = -1j * np.sin(theta)
    return U


def layer_unitary(nbs_layer, theta, D):
    U = np.eye(D, dtype=complex)
    for nb in nbs_layer:
        U = xy_gate(nb, theta, D) @ U  # disjoint edges commute
    return U


def trotter_U(E, nbs_by_layer, gamma, t, r, alpha, scale, mode="palindromic", perm=None):
    """Second-order palindromic: D(dt/2) L1(dt/2)..L_{c-1}(dt/2) L_c(dt) L_{c-1}(dt/2)..L1(dt/2) D(dt/2).
    'ordered': first-order D(dt) L1(dt)...Lc(dt) per step (a typical transpiled, non-palindromic order).
    'scrambled': first-order with every individual edge gate in a fixed random order `perm` (transpiler-like)."""
    D = len(E)
    dt = t / r
    Dg = lambda th: np.diag(np.exp(-1j * th * (1 - gamma) * alpha * E))
    th = gamma * scale * dt
    if mode == "palindromic":
        Ls = [layer_unitary(L, th / 2, D) for L in nbs_by_layer[:-1]]
        Lc = layer_unitary(nbs_by_layer[-1], th, D)
        M = np.eye(D, dtype=complex)
        for L in Ls:
            M = L @ M
        M = Lc @ M
        for L in Ls[::-1]:
            M = L @ M
        step = Dg(dt / 2) @ M @ Dg(dt / 2)
    elif mode == "ordered":
        M = np.eye(D, dtype=complex)
        for L in nbs_by_layer:
            M = layer_unitary(L, th, D) @ M
        step = M @ Dg(dt)
    elif mode == "scrambled":
        flat = [nb for L in nbs_by_layer for nb in L]
        M = np.eye(D, dtype=complex)
        for p in perm:
            M = xy_gate(flat[p], th, D) @ M
        step = M @ Dg(dt)
    return np.linalg.matrix_power(step, r)
