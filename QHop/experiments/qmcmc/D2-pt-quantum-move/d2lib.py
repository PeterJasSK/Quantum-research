"""D2 library: QeMCMC vs tuned parallel tempering; QeMCMC / decohered move inside PT.

Exactness notes (how detailed balance is known to hold):
 * Quantum proposal Q_m(s'|s) = (1/16) sum_k |<s'|exp(-i H_k t_k)|s>|^2 over a FIXED pool of 16 (gamma,t) pairs
   (4 gammas x 4 times, drawn once with seed 0, same convention as qmc.quantum_Q with m=16). Each H_k is real symmetric,
   so U_k = U_k^T and Q_m is symmetric -> Metropolis min(1, pi'/pi) is exact. Rows are computed by Chebyshev
   propagation of the statevector (no full matrix), verified against qmc.quantum_Q (test_d2.py). Samples are drawn
   either from a single (gamma,t) evolution (one outcome) or from a cached exact row (reservoir of iid draws, refilled
   by fresh draws) -- both are iid draws from the same Q_m(.|s), so the chain is unchanged in law.
 * Decohered control: same generator, full Z-dephasing every dt = t/round(t/0.25) (qmc.decohered_Q convention);
   kernel T = |exp(-iH dt)|^2 is symmetric, T^k symmetric -> Metropolis exact. Each dt-substep is computed on the
   Hamming ball of radius 3 around the current state (truncation leak reported, ~1e-7 per substep).
 * PT: Metropolis sweeps at fixed beta + standard replica-exchange; Houdayer move is rejection-free and preserves the
   product measure of two replicas at equal beta (Houdayer 2001). Quantum/decohered moves inside PT are Metropolis
   moves at the replica's own beta with a symmetric proposal -> each move leaves the joint product measure invariant.
"""
import ctypes
import os
import sys
import time

import numpy as np
from scipy.special import jv

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_lib = ctypes.CDLL(os.path.join(HERE, "libckern.so"))
P = np.ctypeslib.ndpointer
D = P(dtype=np.float64, flags="C_CONTIGUOUS")
I8 = P(dtype=np.int8, flags="C_CONTIGUOUS")
U64 = P(dtype=np.uint64, flags="C_CONTIGUOUS")
I64 = P(dtype=np.int64, flags="C_CONTIGUOUS")
I32 = P(dtype=np.int32, flags="C_CONTIGUOUS")
ci, cl, cd = ctypes.c_int, ctypes.c_long, ctypes.c_double
_lib.metro_run.restype = cl
_lib.metro_run.argtypes = [ci, D, cd, cl, ci, I8, D, D, D, I8, U64, D, D]
_lib.pt_run.restype = None
_lib.pt_run.argtypes = [ci, ci, ci, D, D, D, I8, D, D, D, I8, cl, U64, I64, D, D, ci, ctypes.c_void_p,
                        ctypes.c_void_p, ci, I32, I32, ci, D]
_lib.recompute_row.restype = None
_lib.recompute_row.argtypes = [ci, D, D, I8, D, D, D, I8]
_lib.cheb_evolve.restype = None
_lib.cheb_evolve.argtypes = [ci, D, cd, cl, ci, ci, D, D, D]
_lib.dec_walk.restype = cl
_lib.dec_walk.argtypes = [ci, I64, I32, I32, D, cl, cd, cd, cd, cd, ci, D, ci, U64, D, D]


def rng_state(seed):
    g = np.random.default_rng(seed)
    return g.integers(1, 2 ** 63, size=4, dtype=np.uint64)


# ---------------------------------------------------------------- instances


class Instance:
    def __init__(self, family, n, seed):
        self.family, self.n, self.seed = family, n, seed
        if family == "sk":
            J, h = qmc.sk_instance(n, seed)
        elif family == "ea":
            L1, L2 = {12: (3, 4), 16: (4, 4)}[n]
            J, h = qmc.ea_instance(L1, L2, seed, periodic=True, dist="gauss")
        else:
            raise ValueError(family)
        self.J = np.ascontiguousarray(J, float)
        self.h = np.ascontiguousarray(h, float)
        self.E = qmc.ising_energies(J, h)
        self.igs = int(np.argmin(self.E))
        self.Egs = float(self.E[self.igs])
        self.sgs = np.ascontiguousarray(qmc.spins(n)[self.igs].astype(np.int8)) if n <= 18 else None
        self.absq = family == "ea"  # h = 0 -> Z2 symmetric: use |q|
        self.alpha = qmc.alpha_from_energy(self.E)
        # neighbour lists (for Houdayer)
        nz = np.abs(self.J) > 0
        self.maxdeg = max(1, int(nz.sum(1).max()))
        self.nbr = np.zeros(n * self.maxdeg, np.int32)
        self.deg = np.zeros(n, np.int32)
        for i in range(n):
            js = np.nonzero(nz[i])[0]
            self.deg[i] = len(js)
            self.nbr[i * self.maxdeg:i * self.maxdeg + len(js)] = js
        self.pow2 = (1 << np.arange(n)).astype(np.int64)

    def idx(self, s):
        return int(((s < 0).astype(np.int64) * self.pow2).sum())

    def spins_of(self, a):
        return np.ascontiguousarray((1 - 2 * ((a >> np.arange(self.n)) & 1)).astype(np.int8))

    def exact(self, beta):
        p = qmc.boltzmann(self.E, beta)
        e = float(p @ self.E)
        return e, float(beta * beta * (p @ self.E ** 2 - e * e) / self.n)

    def exact_q(self, beta):
        p = qmc.boltzmann(self.E, beta)
        s = qmc.spins(self.n) @ self.sgs.astype(float) / self.n
        if self.absq:
            s = np.abs(s)
        return float(p @ s)

    def beta_c(self):
        b = np.exp(np.linspace(np.log(0.01), np.log(3.0), 400))
        C = qmc.thermo(self.E, self.n, b)
        k = int(np.argmax(C))
        bf = np.linspace(b[max(k - 3, 0)], b[min(k + 3, len(b) - 1)], 200)
        Cf = qmc.thermo(self.E, self.n, bf)
        return float(bf[np.argmax(Cf)]), float(Cf.max())


# ---------------------------------------------------------------- quantum proposal (Chebyshev statevector)


def pool(seed=0):
    g = np.random.default_rng(seed)
    gammas = g.uniform(0.25, 0.6, 4)
    ts = np.sort(g.uniform(2.0, 20.0, (4, 4)), axis=1)
    return gammas, ts


def cheb_coefs(w, ts, tol=1e-15):
    x = w * np.max(ts)
    K = int(x + 12 * x ** (1 / 3) + 40)
    k = np.arange(K)
    sign = np.where(k % 2 == 0, (-1.0) ** (k // 2), (-1.0) ** ((k + 1) // 2))
    C = np.array([jv(k, w * t) * np.where(k == 0, 1.0, 2.0) * sign for t in ts])
    big = np.nonzero(np.abs(C).max(0) > tol)[0]
    K = int(big.max()) + 2
    return np.ascontiguousarray(C[:, :K]), K


class QSampler:
    """Exact sampler of the symmetric pooled QeMCMC proposal Q_m(.|s) via Chebyshev statevector propagation."""

    def __init__(self, inst, gammas=None, ts=None, row_after=4, reservoir=2048, seed=12345):
        self.inst, self.n = inst, inst.n
        self.dim = 1 << inst.n
        if gammas is None:
            gammas, ts = pool(0)
        self.gammas, self.ts = gammas, ts
        E, a, n = inst.E, inst.alpha, inst.n
        self.par = []
        for g, tg in zip(gammas, ts):
            lo = (1 - g) * a * E.min() - g * n
            hi = (1 - g) * a * E.max() + g * n
            c, w = 0.5 * (lo + hi), 0.5 * (hi - lo)
            dtil = np.ascontiguousarray(((1 - g) * a * E - c) / w)
            C, K = cheb_coefs(w, tg)
            singles = [cheb_coefs(w, [t]) for t in tg]
            self.par.append(dict(g=g, w=w, dtil=dtil, gw=g / w, C=C, K=K, singles=singles))
        self.work = np.zeros(3 * self.dim + 2 * 4 * self.dim)
        self.out = np.zeros(4 * self.dim)
        self.row_after, self.reservoir = row_after, reservoir
        self.count, self.res, self.ptr = {}, {}, {}
        self.rng = np.random.default_rng(seed)
        self.n_row = self.n_single = 0
        self.t_row = self.t_single = 0.0

    def row(self, s):
        t0 = time.time()
        acc = np.zeros(self.dim)
        for p in self.par:
            _lib.cheb_evolve(self.n, p["dtil"], p["gw"], s, p["K"], 4, p["C"], self.out, self.work)
            acc += self.out.reshape(4, self.dim).sum(0)
        self.n_row += 1
        self.t_row += time.time() - t0
        return acc / 16.0

    def single(self, s):
        t0 = time.time()
        p = self.par[self.rng.integers(4)]
        C, K = p["singles"][self.rng.integers(4)]
        wk = self.work[:3 * self.dim + 2 * self.dim]
        _lib.cheb_evolve(self.n, p["dtil"], p["gw"], s, K, 1, C, self.out, wk)
        pr = self.out[:self.dim]
        cdf = np.cumsum(pr)
        b = int(np.searchsorted(cdf, self.rng.random() * cdf[-1]))
        self.n_single += 1
        self.t_single += time.time() - t0
        return min(b, self.dim - 1)

    def propose(self, s):
        r = self.res.get(s)
        if r is not None:
            k = self.ptr[s]
            if k < len(r):
                self.ptr[s] = k + 1
                return int(r[k])
        c = self.count.get(s, 0) + 1
        self.count[s] = c
        if c >= self.row_after:
            pr = self.row(s)
            cdf = np.cumsum(pr)
            draws = np.searchsorted(cdf, self.rng.random(self.reservoir) * cdf[-1])
            self.res[s] = np.minimum(draws, self.dim - 1).astype(np.int64)
            self.ptr[s] = 1
            return int(self.res[s][0])
        return self.single(s)

    def stats(self):
        return dict(n_row=self.n_row, n_single=self.n_single, t_row=self.t_row, t_single=self.t_single,
                    cached_states=len(self.res))


class DSampler:
    """Decohered control: dephase every dt (= t/round(t/0.25)), substeps on the radius-3 Hamming ball."""

    def __init__(self, inst, gammas=None, ts=None, dt=0.25, rad=3, seed=777):
        self.inst, n = inst, inst.n
        if gammas is None:
            gammas, ts = pool(0)
        masks = [0]
        from itertools import combinations
        for r in range(1, rad + 1):
            for c in combinations(range(n), r):
                masks.append(sum(1 << i for i in c))
        self.masks = np.array(masks, np.int64)
        pos = {m: k for k, m in enumerate(masks)}
        aptr, aidx = [0], []
        for m in masks:
            for i in range(n):
                j = pos.get(m ^ (1 << i))
                if j is not None:
                    aidx.append(j)
            aptr.append(len(aidx))
        self.aptr, self.aidx = np.array(aptr, np.int32), np.array(aidx, np.int32)
        self.nb = len(masks)
        E, a = inst.E, inst.alpha
        self.items = []
        for g, tg in zip(gammas, ts):
            lo = (1 - g) * a * E.min() - g * n
            hi = (1 - g) * a * E.max() + g * n
            c, w = 0.5 * (lo + hi), 0.5 * (hi - lo)
            for t in tg:
                k = max(1, int(round(t / dt)))
                C, K = cheb_coefs(w, [t / k])
                self.items.append(dict(scale=(1 - g) * a, c=c, winv=1.0 / w, gw=g / w, C=np.ascontiguousarray(C[0]),
                                       K=K, k=k))
        self.work = np.zeros(6 * self.nb)
        self.leak = np.zeros(1)
        self.rs = rng_state(seed)
        self.rng = np.random.default_rng(seed)
        self.nsub = 0
        self.t = 0.0

    def propose(self, s):
        t0 = time.time()
        it = self.items[self.rng.integers(len(self.items))]
        b = _lib.dec_walk(self.nb, self.masks, self.aptr, self.aidx, self.inst.E, s, it["scale"], it["c"], it["winv"],
                          it["gw"], it["K"], it["C"], it["k"], self.rs, self.work, self.leak)
        self.nsub += it["k"]
        self.t += time.time() - t0
        return int(b)

    def stats(self):
        return dict(substeps=self.nsub, mean_leak_per_substep=float(self.leak[0] / max(self.nsub, 1)), t=self.t)


# ---------------------------------------------------------------- chains


def metro(inst, beta, nflips, rec_every, seed, a0=None):
    rs = rng_state(seed)
    n = inst.n
    a0 = np.random.default_rng(seed).integers(1 << n) if a0 is None else a0
    s = inst.spins_of(int(a0))
    F, E, q = np.zeros(n), np.zeros(1), np.zeros(1)
    _lib.recompute_row(n, inst.J, inst.h, s, F, E, q, inst.sgs)
    nrec = nflips // rec_every
    oE, oQ = np.zeros(nrec), np.zeros(nrec)
    _lib.metro_run(n, inst.J, beta, nflips, rec_every, s, F, E, q, inst.sgs, rs, oE, oQ)
    return oE, (np.abs(oQ) if inst.absq else oQ)


class PT:
    def __init__(self, inst, betas, seed, ncopy=1, houdayer=False, target=None):
        self.inst, self.n = inst, inst.n
        self.betas = np.ascontiguousarray(betas, float)
        self.R, self.ncopy, self.hou = len(betas), ncopy, int(houdayer)
        g = np.random.default_rng(seed)
        self.rs = rng_state(seed + 1)
        self.S = np.ascontiguousarray(g.choice([-1, 1], size=(ncopy * self.R, self.n)).astype(np.int8))
        self.F = np.zeros((ncopy * self.R, self.n))
        self.Ec = np.zeros(ncopy * self.R)
        self.Qc = np.zeros(ncopy * self.R)
        for c in range(ncopy * self.R):
            self.fix(c)
        self.parity = np.zeros(1, np.int64)
        self.acc = np.zeros(max(self.R - 1, 1))
        self.tries = np.zeros(max(self.R - 1, 1))
        self.hstat = np.zeros(2)
        self.target = self.R - 1 if target is None else target  # coldest (betas ascending)

    def fix(self, c):
        Fr, e, q = np.zeros(self.n), np.zeros(1), np.zeros(1)
        s = np.ascontiguousarray(self.S[c])
        _lib.recompute_row(self.n, self.inst.J, self.inst.h, s, Fr, e, q, self.inst.sgs)
        self.F[c], self.Ec[c], self.Qc[c] = Fr, e[0], q[0]

    def run(self, nsweeps, record=True):
        oE = np.zeros(nsweeps) if record else None
        oQ = np.zeros(nsweeps) if record else None
        Fv = self.F.reshape(-1)
        Sv = self.S.reshape(-1)
        _lib.pt_run(self.n, self.R, self.ncopy, self.inst.J, self.inst.h, self.betas, Sv, Fv, self.Ec, self.Qc,
                    self.inst.sgs, nsweeps, self.rs, self.parity, self.acc, self.tries, self.target,
                    None if oE is None else oE.ctypes.data, None if oQ is None else oQ.ctypes.data,
                    self.hou, self.inst.nbr, self.inst.deg, self.inst.maxdeg, self.hstat)
        if record and self.inst.absq:
            oQ = np.abs(oQ)
        return oE, oQ

    def swap_rates(self):
        return (self.acc / np.maximum(self.tries, 1)).tolist()

    def reset_stats(self):
        self.acc[:] = 0
        self.tries[:] = 0

    def cost_per_sweep(self):
        c = self.n * self.R * self.ncopy
        if self.hou:
            c += self.n * self.R  # Houdayer cluster move ~ O(n) per temperature
        return c

    def qmove(self, slot, sampler, rng):
        """one Metropolis move with an external symmetric proposal on config at temperature slot (copy 0)."""
        a = self.inst.idx(self.S[slot])
        b = sampler.propose(a)
        if b == a:
            return 0
        dE = self.inst.E[b] - self.inst.E[a]
        if dE <= 0 or rng.random() < np.exp(-self.betas[slot] * dE):
            self.S[slot] = self.inst.spins_of(b)
            self.fix(slot)
            return 1
        return 0


def tune_ladder(inst, bmin, bmax, seed, target=(0.20, 0.30), iters=8, sweeps=4000, ncopy=1, houdayer=False):
    """Geometric start, then iterative re-spacing (equal -log acceptance per gap) and rung-count adjustment
    until every adjacent swap rate lies in [0.2, 0.3] (or iterations exhausted)."""
    if bmax / bmin < 1.0001:
        return np.array([bmax]), [], []
    R = 4
    betas = np.geomspace(bmin, bmax, R)
    hist = []
    for it in range(iters):
        pt = PT(inst, betas, seed + it, ncopy, houdayer)
        pt.run(sweeps // 4, record=False)
        pt.reset_stats()
        pt.run(sweeps, record=False)
        a = np.array(pt.swap_rates())
        hist.append(dict(betas=betas.tolist(), swap=a.tolist()))
        if a.min() >= target[0] and a.max() <= target[1] + 0.05:
            return betas, a.tolist(), hist
        d = -np.log(np.clip(a, 0.02, 0.999))
        cum = np.concatenate([[0], np.cumsum(d)])
        tot = cum[-1]
        goal = -np.log(np.mean(target))
        Rn = max(2, int(np.ceil(tot / goal)) + 1)
        u = np.linspace(0, tot, Rn)
        lb = np.log(betas)
        betas = np.exp(np.interp(u, cum, lb))
        betas[0], betas[-1] = bmin, bmax
    pt = PT(inst, betas, seed + 99, ncopy, houdayer)
    pt.run(sweeps // 4, record=False)
    pt.reset_stats()
    pt.run(sweeps, record=False)
    hist.append(dict(betas=betas.tolist(), swap=pt.swap_rates()))
    return betas, pt.swap_rates(), hist


def qchain(inst, sampler, beta, steps, seed, a0=None):
    rng = np.random.default_rng(seed)
    a = int(rng.integers(1 << inst.n)) if a0 is None else a0
    E = inst.E
    oE, oA = np.zeros(steps), np.zeros(steps, np.int64)
    nacc = 0
    for k in range(steps):
        b = sampler.propose(a)
        dE = E[b] - E[a]
        if b != a and (dE <= 0 or rng.random() < np.exp(-beta * dE)):
            a = b
            nacc += 1
        oE[k] = E[a]
        oA[k] = a
    return oE, inst_q(inst, oA), nacc / steps


def inst_q(inst, states):
    s = 1 - 2 * ((states[:, None] >> np.arange(inst.n)) & 1)
    q = s @ inst.sgs.astype(float) / inst.n
    return np.abs(q) if inst.absq else q


def iat2(E, q):
    return qmc.iat(E), qmc.iat(q)


def t_equil(Emat, Eex, tol_rel=0.01):
    """Emat: (M chains, T) energy traces from random starts. Ensemble mean over chains, averaged over dyadic windows
    [2^j, 2^(j+1)); t_eq = start of the first window after which every window mean is within tol of E_exact.
    Returns (t_eq in recorded units, or nan if never)."""
    T = Emat.shape[1]
    m = Emat.mean(0)
    tol = tol_rel * abs(Eex)
    starts = [0] + [2 ** j for j in range(int(np.log2(T)) + 1) if 2 ** j < T]
    ok = []
    for j, s0 in enumerate(starts):
        s1 = starts[j + 1] if j + 1 < len(starts) else T
        if s1 <= s0:
            s1 = s0 + 1
        ok.append(abs(m[s0:s1].mean() - Eex) < tol)
    ok = np.array(ok)
    for j in range(len(ok)):
        if ok[j:].all():
            return float(max(starts[j], 1))
    return float("nan")
