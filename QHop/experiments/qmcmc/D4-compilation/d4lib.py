"""D4 shared library: problem families, exact vs Trotter proposal (numpy), Qiskit circuit builder.

Conventions (same as common/qmc.py): bit i of a basis index = qubit i (Qiskit little-endian), spin s_i = 1 - 2 bit_i = Z_i,
E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i.  H = (1-g) alpha E + g sum_i X_i, alpha = sqrt(n)/std_uniform(E)
(= Layden sqrt(n)/sqrt(sum_{i<j}J^2 + sum h^2) for Ising).
Second-order (Strang) Trotter, r steps: U_r = D/2 [X D]^(r-1) X D/2 with D = exp(-i dt (1-g) alpha E), X = prod_i Rx(2 g dt).
On a basis input and Z readout the first and last D/2 are pure phases, so they are dropped (exact for the proposal
matrix): the circuit has r X-layers and r-1 full diagonal (ZZ) layers.
Potts (one-hot, q colours per site): mixer = g sum_sites sum_{ring pairs (a,b)} (X_a X_b + Y_a Y_b)/2, split into
edge-colour classes C_1..C_c, palindromic within a step: M_1/2 ... M_{c-1}/2 M_c M_{c-1}/2 ... M_1/2.
"""
import itertools
import sys
import warnings

import networkx as nx
import numpy as np
from scipy.linalg import eigh, expm

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

GAMMAS = (0.25, 0.425, 0.6)
TS = (2.0, 6.0, 12.0, 20.0)


# ------------------------------------------------------------------ problem families (J symmetric, zero diag)

def sym(n, pairs, vals):
    J = np.zeros((n, n))
    for (i, j), v in zip(pairs, vals):
        J[i, j] += v
        J[j, i] += v
    return J


def fam_sk(n, seed):
    return qmc.sk_instance(n, 1000 + seed)


def fam_cg(k, seed):
    """Coarse-grained group of k spins cut from a parent SK of n_tot = k^2 spins (P2: k ~ sqrt(n)); rest frozen at
    random s, effective field h~_j = h_j + sum_{i not in g} J_ji s_i."""
    ntot = k * k
    J, h = qmc.sk_instance(ntot, 2000 + seed)
    s = np.random.default_rng(3000 + seed).choice([-1.0, 1.0], ntot)
    g = np.arange(k)
    rest = np.arange(k, ntot)
    heff = h[g] + J[np.ix_(g, rest)] @ s[rest]
    return J[np.ix_(g, g)].copy(), heff


def fam_coulomb(n, seed):
    """Dense long-range 'Coulomb gas' Ising: random points in the unit square, E = sum_{i<j} s_i s_j / r_ij
    (J_ij = -1/r_ij, r clipped at 0.05), no field. Ewald-like dense, frustrated."""
    p = np.random.default_rng(4000 + seed).uniform(size=(n, 2))
    r = np.maximum(np.linalg.norm(p[:, None] - p[None], axis=-1), 0.05)
    J = -1.0 / r
    np.fill_diagonal(J, 0.0)
    return J, np.zeros(n)


def grid_edges(L1, L2):
    return qmc.lattice_edges(L1, L2, periodic=False)


def fam_ea(L1, L2, seed):
    """2D EA, open boundaries (native to a square-lattice chip), J ~ N(0,1), no field."""
    return qmc.ea_instance(L1, L2, 5000 + seed, periodic=False)


_HH = None


def heavy_hex_graph():
    global _HH
    if _HH is None:
        from qiskit_ibm_runtime import fake_provider as fp
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            b = fp.FakeMarrakesh()
        G = nx.Graph()
        G.add_edges_from(tuple(e) for e in b.coupling_map.get_edges())
        _HH = G
    return _HH


def hh_subgraph(n):
    """Connected n-node subgraph of the Heron 156q heavy-hex map. n=12: one hexagon cell (12-cycle).
    Otherwise BFS ball grown from the node nearest the graph centre (deterministic)."""
    G = heavy_hex_graph()
    if n == 12:
        cyc = sorted((c for c in nx.minimum_cycle_basis(G) if len(c) == 12), key=lambda c: sorted(c))
        centre = nx.center(G)[0]
        d = nx.single_source_shortest_path_length(G, centre)
        c = min(cyc, key=lambda c: (sum(d[v] for v in c), sorted(c)))
        nodes = sorted(c)
    else:
        centre = nx.center(G)[0]
        order = list(nx.bfs_tree(G, centre))
        nodes = sorted(order[:n])
    H = G.subgraph(nodes)
    idx = {v: i for i, v in enumerate(nodes)}
    return nodes, sorted(tuple(sorted((idx[a], idx[b]))) for a, b in H.edges())


def fam_hh(n, seed):
    nodes, E = hh_subgraph(n)
    g = np.random.default_rng(6000 + seed)
    return sym(n, E, g.normal(size=len(E))), g.normal(size=n)


def edges_of(J):
    n = len(J)
    return [(i, j) for i in range(n) for j in range(i + 1, n) if J[i, j] != 0]


def alpha_ising(J, h):
    s2 = sum(J[i, j] ** 2 for i, j in edges_of(J)) + float(np.sum(h ** 2))
    return np.sqrt(len(h)) / np.sqrt(s2)


# ------------------------------------------------------------------ Potts (one-hot)

def ring_classes(q):
    """Edge-colour classes of the q-ring (q>=3)."""
    edges = [(a, (a + 1) % q) for a in range(q)]
    if q % 2 == 0:
        return [edges[0::2], edges[1::2]]
    return [edges[:-1][0::2], edges[:-1][1::2], [edges[-1]]]


def fam_potts(L1, L2, q, seed):
    g = np.random.default_rng(7000 + 10 * q + seed)
    E = grid_edges(L1, L2)
    return {"L1": L1, "L2": L2, "q": q, "edges": E, "J": g.normal(size=len(E)), "h": g.normal(size=(L1 * L2, q))}


def potts_energies(P):
    L, q = P["L1"] * P["L2"], P["q"]
    c = np.array(list(itertools.product(range(q), repeat=L)))      # row-major: site 0 = most significant axis
    E = np.zeros(len(c))
    for (i, j), Jv in zip(P["edges"], P["J"]):
        E -= Jv * (c[:, i] == c[:, j])
    E -= P["h"][np.arange(L)[None, :], c].sum(1)
    return E


# ------------------------------------------------------------------ exact vs Trotter proposal rows

def _rx_all(Psi, n, th):
    c, s = np.cos(th / 2), -1j * np.sin(th / 2)
    T = Psi.reshape((2,) * n + (-1,))
    for ax in range(n):
        T = c * T + s * np.flip(T, axis=ax)
    return T.reshape(Psi.shape)


_EIG = {}


def ising_rows(J, h, gamma, t, r_list, rows=None):
    """Return {r: max-row TVD, mean-row TVD} of Trotter vs exact proposal rows for the given start states."""
    n = len(h)
    E = qmc.ising_energies(J, h)
    a = alpha_ising(J, h)
    Ea = (1 - gamma) * a * E
    N = 2 ** n
    rows = np.arange(N) if rows is None else np.asarray(rows)
    key = (hash(Ea.tobytes()), gamma)
    if _EIG.get("key") != key:
        _EIG.clear()
        _EIG["key"], _EIG["wV"] = key, eigh(np.diag(Ea) + gamma * qmc.mixer(n))
    w, V = _EIG["wV"]
    Ue = V @ (np.exp(-1j * w * t)[:, None] * V[rows, :].T)
    Qe = np.abs(Ue) ** 2
    out = {}
    for r in r_list:
        dt = t / r
        Psi = np.zeros((N, len(rows)), complex)
        Psi[rows, np.arange(len(rows))] = 1.0
        ph = np.exp(-1j * dt * Ea)[:, None]
        Psi = _rx_all(Psi, n, 2 * gamma * dt)
        for _ in range(r - 1):
            Psi = _rx_all(ph * Psi, n, 2 * gamma * dt)
        tv = 0.5 * np.abs(np.abs(Psi) ** 2 - Qe).sum(0)
        out[r] = (float(tv.max()), float(tv.mean()))
    return out


def potts_rows(P, gamma, t, r_list, rows):
    from scipy.sparse import identity, kron, csr_matrix, diags
    from scipy.sparse.linalg import expm_multiply
    L, q = P["L1"] * P["L2"], P["q"]
    E = potts_energies(P)
    a = np.sqrt(L) / np.std(E)
    Ea = (1 - gamma) * a * E
    N = q ** L
    cls = ring_classes(q)
    A = np.zeros((q, q))
    for C in cls:
        for x, y in C:
            A[x, y] = A[y, x] = 1.0
    Hm = csr_matrix((N, N))
    for i in range(L):
        Hm = Hm + kron(kron(identity(q ** i), csr_matrix(A)), identity(q ** (L - 1 - i)), format="csr")
    H = diags(Ea) + gamma * Hm
    B = np.zeros((N, len(rows)), complex)
    B[rows, np.arange(len(rows))] = 1.0
    if N <= 4096:
        Ue = expm(-1j * t * H.toarray()) @ B
    else:
        Ue = expm_multiply(-1j * t * H, B)
    Qe = np.abs(Ue) ** 2
    Acls = []
    for C in cls:
        M = np.zeros((q, q))
        for x, y in C:
            M[x, y] = M[y, x] = 1.0
        Acls.append(M)
    out = {}
    for r in r_list:
        dt = t / r
        seq = [(k, 0.5) for k in range(len(cls) - 1)] + [(len(cls) - 1, 1.0)] + [(k, 0.5) for k in reversed(range(len(cls) - 1))]
        Us = {(k, f): expm(-1j * gamma * dt * f * Acls[k]) for k, f in seq}
        ph = np.exp(-1j * dt * Ea)[:, None]

        def mix(Psi):
            T = Psi.reshape((q,) * L + (-1,))
            for k, f in seq:
                U = Us[(k, f)]
                for ax in range(L):
                    T = np.moveaxis(np.tensordot(U, T, axes=([1], [ax])), 0, ax)
            return T.reshape(Psi.shape)
        Psi = mix(B.copy())
        for _ in range(r - 1):
            Psi = mix(ph * Psi)
        tv = 0.5 * np.abs(np.abs(Psi) ** 2 - Qe).sum(0)
        out[r] = (float(tv.max()), float(tv.mean()))
    return out


def min_r(fun, tol=0.05, rmax=400, key=0, cache=None):
    """Smallest r with fun([r])[r][key] <= tol (geometric scan then integer bisection; assumes monotone)."""
    cache = {} if cache is None else cache

    def f(r):
        if r not in cache:
            cache[r] = fun([r])[r]
        return cache[r][key]
    prev, r = 1, 2
    while r <= rmax and f(r) > tol:
        prev, r = r, int(np.ceil(r * 1.5))
    if r > rmax:
        return None, cache
    lo, hi = prev, r
    while hi - lo > 1:
        m = (lo + hi) // 2
        if f(m) <= tol:
            hi = m
        else:
            lo = m
    return hi, cache


# ------------------------------------------------------------------ circuits

def ising_circuit(J, h, gamma, t, r, state=0, measure=True):
    from qiskit import QuantumCircuit
    n = len(h)
    a = alpha_ising(J, h)
    dt = t / r
    qc = QuantumCircuit(n, n if measure else 0)
    for i in range(n):
        if (state >> i) & 1:
            qc.x(i)
    E = edges_of(J)

    def xl():
        for i in range(n):
            qc.rx(2 * gamma * dt, i)
    xl()
    for _ in range(r - 1):
        for i in range(n):
            if h[i]:
                qc.rz(2 * (1 - gamma) * a * (-h[i]) * dt, i)
        for i, j in E:
            qc.rzz(2 * (1 - gamma) * a * (-J[i, j]) * dt, i, j)
        xl()
    if measure:
        qc.measure(range(n), range(n))
    return qc


def ising_swapnet_circuit(J, h, gamma, t, r, measure=True):
    """Dense Ising via odd-even transposition swap network on a LINE of n qubits: each D-layer = n rounds of
    (RZZ + SWAP) on alternating neighbour pairs; every pair meets once; order reverses each D-layer.
    X-layers are permutation-invariant (same angle on every qubit) and fields are applied by tracked position."""
    from qiskit import QuantumCircuit
    n = len(h)
    a = alpha_ising(J, h)
    dt = t / r
    qc = QuantumCircuit(n, n if measure else 0)
    pos = list(range(n))           # pos[p] = logical spin at line position p

    def xl():
        for p in range(n):
            qc.rx(2 * gamma * dt, p)
    xl()
    for _ in range(r - 1):
        for p in range(n):
            if h[pos[p]]:
                qc.rz(2 * (1 - gamma) * a * (-h[pos[p]]) * dt, p)
        for rnd in range(n):
            for p in range(rnd % 2, n - 1, 2):
                i, j = pos[p], pos[p + 1]
                if J[i, j]:
                    qc.rzz(2 * (1 - gamma) * a * (-J[i, j]) * dt, p, p + 1)
                qc.cx(p, p + 1)            # SWAP as 3 CX (qc.swap would be deleted by level-3 ElidePermutations)
                qc.cx(p + 1, p)
                qc.cx(p, p + 1)
                pos[p], pos[p + 1] = pos[p + 1], pos[p]
        xl()
    if measure:
        for p in range(n):
            qc.measure(p, pos[p])
    return qc


def potts_circuit(P, gamma, t, r, measure=True):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import XXPlusYYGate
    L, q = P["L1"] * P["L2"], P["q"]
    E = potts_energies(P)
    a = np.sqrt(L) / np.std(E)
    dt = t / r
    nq = L * q
    Q = lambda i, c: i * q + c
    qc = QuantumCircuit(nq, nq if measure else 0)
    for i in range(L):
        qc.x(Q(i, 0))
    cls = ring_classes(q)
    seq = [(k, 0.5) for k in range(len(cls) - 1)] + [(len(cls) - 1, 1.0)] + [(k, 0.5) for k in reversed(range(len(cls) - 1))]

    def mix():
        for k, f in seq:
            for i in range(L):
                for x, y in cls[k]:
                    qc.append(XXPlusYYGate(2 * gamma * dt * f), [Q(i, x), Q(i, y)])
    # n_{i,c} = (1 - Z)/2 : -J n n = -J/4 (1 - Z_a - Z_b + Z_a Z_b);  -h n = -h/2 (1 - Z)
    zz = {}
    z = np.zeros(nq)
    for (i, j), Jv in zip(P["edges"], P["J"]):
        for c in range(q):
            zz[(Q(i, c), Q(j, c))] = zz.get((Q(i, c), Q(j, c)), 0.0) - Jv / 4
            z[Q(i, c)] += Jv / 4
            z[Q(j, c)] += Jv / 4
    for i in range(L):
        for c in range(q):
            z[Q(i, c)] += P["h"][i, c] / 2
    mix()
    for _ in range(r - 1):
        for k in range(nq):
            if z[k]:
                qc.rz(2 * (1 - gamma) * a * z[k] * dt, k)
        for (u, v), c in zz.items():
            qc.rzz(2 * (1 - gamma) * a * c * dt, u, v)
        mix()
    if measure:
        qc.measure(range(nq), range(nq))
    return qc
