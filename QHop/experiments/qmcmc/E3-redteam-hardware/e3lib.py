"""E3 red-team helpers: stronger classical kernels, global-depolarizing noisy proposals, T1 tilt bias.
All kernels here are reversible w.r.t. Boltzmann pi (block heat-bath: exact conditional; MH: symmetric Q or Hastings)."""
import itertools
import sys

import numpy as np

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

MIX_W = np.linspace(0, 1, 11)          # weight on local in local+uniform mixture (tuned)


def block_hb_P(E, beta, blocks):
    """Random-block heat-bath kernel (uniform over blocks), exact conditional with the FULL energy.
    Reversible w.r.t. pi (each block kernel is the pi-conditional projection). Classical cost 2^|B| per step."""
    dim = len(E)
    n = int(np.log2(dim))
    pi = qmc.boltzmann(E, beta)
    s = np.arange(dim)
    P = np.zeros((dim, dim))
    for B in blocks:
        mask = sum(1 << i for i in B)
        base = s & ~mask
        assigns = [sum(((a >> j) & 1) << B[j] for j in range(len(B))) for a in range(2 ** len(B))]
        idx = base[:, None] | np.array(assigns)[None, :]          # dim x 2^k
        w = pi[idx]
        w /= w.sum(1, keepdims=True)
        np.add.at(P, (np.repeat(s, idx.shape[1]), idx.ravel()), w.ravel())
    return P / len(blocks)


def gap_P(P, E, beta):
    return qmc.spectral_gap(P, qmc.boltzmann(E, beta))


def best_mix(E, beta, n):
    QL, QU = qmc.local_Q(n), qmc.uniform_Q(n)
    gs = [qmc.gap(qmc.mixture_Q([QL, QU], [w, 1 - w]) if 0 < w < 1 else (QL if w == 1 else QU), E, beta)
          for w in MIX_W]
    k = int(np.argmax(gs))
    return gs[k], float(MIX_W[k]), gs


def hb_mixed_with_uniform(PB, E, beta, n, ws=(1.0, 0.75, 0.5, 0.25)):
    """Mixture kernel w*HB + (1-w)*MH(uniform): still reversible. Returns best gap and weight."""
    PU = qmc.mh_matrix(qmc.uniform_Q(n), E, beta)
    best = (-1, None)
    for w in ws:
        g = gap_P(w * PB + (1 - w) * PU, E, beta)
        if g > best[0]:
            best = (g, w)
    return best


def tree_indep_gap(E, Enat, beta, bq):
    """Independence sampler: propose s' ~ exp(-bq*E_native) (exactly sampleable on a tree, O(n)), Hastings accept with
    FULL energy -> exact detailed balance. Gap via the reversible symmetric form."""
    q = np.exp(-bq * (Enat - Enat.min()))
    q /= q.sum()
    pi = qmc.boltzmann(E, beta)
    Q = np.tile(q, (len(E), 1))
    ratio = (pi[None, :] * q[:, None]) / (pi[:, None] * q[None, :])
    P = Q * np.minimum(1.0, ratio)
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return qmc.spectral_gap(P, pi), P


def tilt_bias(E, beta, n, z):
    """Deep-circuit limit: proposal ~ row-independent product q(s) with per-qubit P(|0>) = (1+z)/2 (T1 + readout pull
    to |0> = spin +1). Plain Metropolis with an independent q has stationary pi' ~ pi*q (exact; derived). TVD(pi, pi')."""
    s = qmc.spins(n).sum(1)
    mu = np.arctanh(z)
    pi = qmc.boltzmann(E, beta)
    p2 = pi * np.exp(mu * s)
    p2 /= p2.sum()
    return 0.5 * np.abs(pi - p2).sum()


def connected_subtrees(edges, n, k):
    """All connected vertex subsets of size k of the graph given by edges."""
    adj = {i: set() for i in range(n)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    out = set()
    for comb in itertools.combinations(range(n), k):
        S = set(comb)
        seen, stack = {comb[0]}, [comb[0]]
        while stack:
            v = stack.pop()
            for u in adj[v] & S:
                if u not in seen:
                    seen.add(u)
                    stack.append(u)
        if seen == S:
            out.add(comb)
    return sorted(out)


def r_of_t(t):
    """D4 Trotter steps for SK n=10 (worst-case criterion row-TVD<=0.05): 5/17/43/86 at t=2/6/12/20; log-log interp."""
    T = np.log([2, 6, 12, 20]); R = np.log([5, 17, 43, 86])
    return float(np.exp(np.interp(np.log(t), T, R)))
