"""Python driver for the D7 C kernels (libcgmc.so). Instances come from the shared harness qmc.py."""
import ctypes as C
import os
import sys

import numpy as np

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = C.CDLL(os.path.join(HERE, "libcgmc.so"))
dp = np.ctypeslib.ndpointer(np.float64, flags="C_CONTIGUOUS")
ip = np.ctypeslib.ndpointer(np.int32, flags="C_CONTIGUOUS")
LIB.chain_run.restype = C.c_int
LIB.chain_run.argtypes = [C.c_int, C.c_int, C.c_int, C.c_int, ip, ip, dp, dp, dp, C.c_double, ip, ip,
                          ip, ip, C.c_int, C.c_int, C.c_int, C.c_double, C.c_uint64, dp, ip, dp, dp]
LIB.pt_run.restype = C.c_int
LIB.pt_run.argtypes = [C.c_int, ip, ip, dp, dp, C.c_int, dp, ip, C.c_int, C.c_int, C.c_int, ip, C.c_int,
                       C.c_double, C.c_uint64, dp, ip, dp, dp, dp]
LIB.test_evolve.argtypes = [C.c_int, dp, C.c_double, C.c_double, C.c_int, dp]
LIB.test_bessel.argtypes = [C.c_double, C.c_int, dp]

METHODS = {"metro": 0, "hb": 1, "q": 2, "dec": 3}
GMODES = {"block": 0, "subset": 1, "cluster": 2}


class Inst:
    def __init__(self, family, size, seed):
        self.family, self.size, self.seed = family, size, seed
        if family == "sk":
            J, h = qmc.sk_instance(size, seed)
        else:
            J, h = qmc.ea_instance(size, size, seed)
        self.J = np.ascontiguousarray(J, float)
        self.h = np.ascontiguousarray(h, float)
        self.n = len(h)
        rp, ci, cv = [0], [], []
        for i in range(self.n):
            nz = np.nonzero(self.J[i])[0]
            ci += nz.tolist(); cv += self.J[i, nz].tolist(); rp.append(len(ci))
        self.rp = np.array(rp, np.int32); self.ci = np.array(ci, np.int32); self.cv = np.array(cv, float)
        self.name = f"{family}{size}_s{seed}"

    def energy(self, s):
        s = s.astype(float)
        return float(-0.5 * s @ self.J @ s - self.h @ s)


def cluster_partition(J, k):
    """Fixed partition into groups of size k (last may be smaller) by greedy strongest-|J| growth.
    Computed once from |J| only -> state independent."""
    n = len(J)
    A = np.abs(J)
    left = set(range(n))
    parts = []
    while left:
        L = np.array(sorted(left))
        sub = A[np.ix_(L, L)]
        seed = int(L[np.argmax(sub.sum(1))])
        grp = [seed]; left.remove(seed)
        while len(grp) < k and left:
            L = np.array(sorted(left))
            score = A[np.ix_(L, grp)].sum(1)
            j = int(L[np.argmax(score)])
            grp.append(j); left.remove(j)
        parts.append(grp)
    return parts


def chain(inst, method, beta, tlimit, seed, k=0, gmode="block", moves_per_rec=None, max_rec=2_000_000,
          s0=None, sref=None, parts=None):
    n = inst.n
    rng = np.random.default_rng(seed)
    s = (rng.choice([-1, 1], n) if s0 is None else s0).astype(np.int32).copy()
    sref = np.ones(n, np.int32) if sref is None else sref.astype(np.int32)
    if moves_per_rec is None:
        moves_per_rec = 1 if method == "metro" else max(1, int(round(n / k)))
    if gmode == "cluster":
        parts = parts if parts is not None else cluster_partition(inst.J, k)
        flat = np.array([i for p in parts for i in p], np.int32)
        poff = np.array(np.cumsum([0] + [len(p) for p in parts]), np.int32)
        npart = len(parts)
    else:
        flat = np.zeros(1, np.int32); poff = np.zeros(2, np.int32); npart = 0
    recE = np.zeros(max_rec); recH = np.zeros(max_rec, np.int32); recT = np.zeros(max_rec); st = np.zeros(8)
    nr = LIB.chain_run(METHODS[method], GMODES[gmode], int(k), n, inst.rp, inst.ci, inst.cv, inst.J, inst.h,
                       float(beta), s, sref, flat, poff, npart, int(moves_per_rec), int(max_rec), float(tlimit),
                       int(seed), recE, recH, recT, st)
    return dict(E=recE[:nr].copy(), H=recH[:nr].copy(), T=recT[:nr].copy(), acc=st[0], moves=st[1], cpu=st[2],
                cheb=st[3], s=s, moves_per_rec=moves_per_rec)


def pt(inst, betas, tgt, tlimit, seed, houdayer=False, houd_from=None, max_rec=2_000_000, sref=None):
    n = inst.n
    R = len(betas)
    nsets = 2 if houdayer else 1
    rng = np.random.default_rng(seed)
    S = rng.choice([-1, 1], (nsets * R, n)).astype(np.int32)
    sref = np.ones(n, np.int32) if sref is None else sref.astype(np.int32)
    hf = R if not houdayer else (0 if houd_from is None else houd_from)
    recE = np.zeros(max_rec); recH = np.zeros(max_rec, np.int32); recT = np.zeros(max_rec)
    sw = np.zeros(max(R - 1, 1)); st = np.zeros(8)
    b = np.ascontiguousarray(betas, float)
    nr = LIB.pt_run(n, inst.rp, inst.ci, inst.cv, inst.h, R, b, S, nsets, int(hf), int(tgt), sref, int(max_rec),
                    float(tlimit), int(seed), recE, recH, recT, sw, st)
    return dict(E=recE[:nr].copy(), H=recH[:nr].copy(), T=recT[:nr].copy(), swap=sw[:R - 1].copy(),
                sweeps=st[1], cpu=st[2], houd_size=st[3], S=S)


def test_evolve(d, gam, t, x0):
    k = int(np.log2(len(d)))
    out = np.zeros(len(d))
    LIB.test_evolve(k, np.ascontiguousarray(d, float), gam, t, x0, out)
    return out


def test_bessel(x, M):
    out = np.zeros(M + 1)
    LIB.test_bessel(x, M, out)
    return out
