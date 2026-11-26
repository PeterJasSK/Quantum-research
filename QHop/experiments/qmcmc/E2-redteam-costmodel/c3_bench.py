"""E2 claim 3(a): basin-difference mask library (+50% local) vs Metropolis and tuned PT per CPU second.
SK n=32,64 (qmc.sk_instance, J,h~N(0,1), beta_c:=1/sqrt(n)); 2D EA Gaussian periodic L=8,12 (qmc.ea_instance, h=0).
Regimes (as D7): SK MEDIUM beta=1/sqrt(n), LOW 3/sqrt(n); EA MEDIUM T=0.8, LOW T=0.4. PT ladders = D7 tuned sizes.
Library: 256 steepest-descent minima from uniform random starts, 1024 random pairs -> XOR masks (zero masks dropped);
build CPU time recorded. Methods: metro, pt, mask (50% mask / 50% single flip), ptmask (PT whose replicas use mask-mix).
Observables per sweep: E and |q| = |overlap with reference state| (reference = lowest E from a 3 s PT run + library).
Usage: python c3_bench.py FAMILY SIZE [budget_s] -> results/c3_bench.jsonl (appends)"""
import ctypes as C, json, os, sys, time
import numpy as np
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
lib = C.CDLL(os.path.join(HERE, "libe2mc.so"))
P = np.ctypeslib.ndpointer
i32, f64, i8 = (P(dtype=np.int32, flags="C"), P(dtype=np.float64, flags="C"), P(dtype=np.int8, flags="C"))
lib.seed_rng.argtypes = [C.c_uint64]
lib.greedy_min.argtypes = [C.c_int, i32, i32, f64, f64, i8]
lib.random_state.argtypes = [C.c_int, i8]
lib.run_single.argtypes = [C.c_int, i32, i32, f64, f64, C.c_double, i8, i32, i32, C.c_int, C.c_double, C.c_double, i8,
                           f64, f64, C.c_int, C.POINTER(C.c_double), C.POINTER(C.c_double)]
lib.run_single.restype = C.c_int
lib.run_pt.argtypes = [C.c_int, i32, i32, f64, f64, C.c_int, f64, i8, i32, i32, C.c_int, C.c_double, C.c_double, i8,
                       f64, f64, C.c_int, C.POINTER(C.c_double), C.POINTER(C.c_double)]
lib.run_pt.restype = C.c_int
MAXREC = 3_000_000


def iat(x, c=5.0):
    x = np.asarray(x, float) - np.mean(x)
    N = len(x)
    if N < 10 or np.var(x) == 0:
        return np.nan
    f = np.fft.rfft(x, n=2 * N)
    acf = np.fft.irfft(f * np.conj(f))[:N] / (N - np.arange(N))
    acf /= acf[0]
    tau = 1 + 2 * np.cumsum(acf[1:])
    M = np.arange(1, N)
    ok = np.nonzero(M >= c * tau)[0]
    return float(tau[ok[0]]) if len(ok) else float(tau[-1])


def csr(J):
    n = len(J)
    off, nb, w = [0], [], []
    for i in range(n):
        js = np.nonzero(J[i])[0]
        nb += js.tolist()
        w += J[i, js].tolist()
        off.append(len(nb))
    return np.array(off, np.int32), np.array(nb, np.int32), np.array(w, float)


def build_library(n, off, nb, w, h, nstart=256, L=1024, seed=0):
    lib.seed_rng(seed)
    t0 = time.thread_time()
    mins = np.zeros((nstart, n), np.int8)
    for a in range(nstart):
        s = np.zeros(n, np.int8)
        lib.random_state(n, s)
        lib.greedy_min(n, off, nb, w, h, s)
        mins[a] = s
    rng = np.random.default_rng(seed)
    masks = []
    while len(masks) < L:
        a, b = rng.integers(nstart, size=2)
        m = np.nonzero(mins[a] != mins[b])[0]
        if len(m):
            masks.append(m)
    moff = np.cumsum([0] + [len(m) for m in masks]).astype(np.int32)
    midx = np.concatenate(masks).astype(np.int32)
    t = time.thread_time() - t0
    nuniq = len({tuple(x) for x in mins.tolist()})
    return moff, midx, t, mins, nuniq, float(np.mean([len(m) for m in masks]))


def summarize(rE, rq, cpu_used, nrec, Eref_mean):
    Es, qs = rE[:nrec], rq[:nrec]
    b = nrec // 4
    tE, tq = iat(Es[b:]), iat(qs[b:])
    spr = cpu_used / nrec
    hit = np.nonzero(Es <= Eref_mean)[0]
    N = nrec - b
    return dict(nrec=nrec, sec_per_rec=spr, tauE=tE, tauq=tq, tauE_sec=tE * spr, tauq_sec=tq * spr,
                resE=bool(N / tE >= 50 and N >= 1000) if np.isfinite(tE) else False,
                resq=bool(N / tq >= 50 and N >= 1000) if np.isfinite(tq) else False,
                t_eq=float(hit[0] * spr) if len(hit) else None, meanE=float(Es[b:].mean()), meanq=float(qs[b:].mean()))


def main():
    fam, size = sys.argv[1], int(sys.argv[2])
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    out = open(os.path.join(HERE, "results", "c3_bench.jsonl"), "a")
    rE, rq = np.zeros(MAXREC), np.zeros(MAXREC)
    for seed in range(1, 6):
        if fam == "sk":
            J, h = qmc.sk_instance(size, seed)
            n = size
            bc = 1 / np.sqrt(n)
            regs = {"MEDIUM": (bc, 4), "LOW": (3 * bc, {32: 6, 64: 8}[n])}
            bmin = 0.3 * bc
        else:
            J, h = qmc.ea_instance(size, size, seed)
            n = size * size
            regs = {"MEDIUM": (1 / 0.8, {8: 6, 12: 8}[size]), "LOW": (1 / 0.4, {8: 6, 12: 10}[size])}
            bmin = 0.5
        off, nb, w = csr(J)
        h = np.ascontiguousarray(h, float)
        moff, midx, tlib, mins, nuniq, mlen = build_library(n, off, nb, w, h, seed=1000 + seed)
        # reference: 3 s PT at LOW (+ library minima)
        bL, RL = regs["LOW"]
        betasL = np.geomspace(bmin, bL, RL)
        S = np.zeros(RL * n, np.int8)
        lib.seed_rng(999 + seed)
        for k in range(RL):
            lib.random_state(n, S[k * n:(k + 1) * n])
        cu, sw = C.c_double(), C.c_double()
        dummy = np.ones(n, np.int8)
        nr = lib.run_pt(n, off, nb, w, h, RL, betasL, S, moff, midx, len(moff) - 1, 0.0, 3.0, dummy, rE, rq, MAXREC,
                        C.byref(cu), C.byref(sw))
        cands = [S[(RL - 1) * n:].copy()] + list(mins)
        Es_c = [(-0.5 * c.astype(float) @ J @ c.astype(float) - h @ c) for c in cands]
        ref = np.ascontiguousarray(cands[int(np.argmin(Es_c))], np.int8)
        for reg, (beta, R) in regs.items():
            betas = np.geomspace(bmin, beta, R)
            res = {}
            # reference mean energy from a PT run (second half) at this beta, 3 s
            lib.seed_rng(5000 + seed)
            S = np.zeros(R * n, np.int8)
            for k in range(R):
                lib.random_state(n, S[k * n:(k + 1) * n])
            nr = lib.run_pt(n, off, nb, w, h, R, betas, S, moff, midx, len(moff) - 1, 0.0, 3.0, ref, rE, rq, MAXREC,
                            C.byref(cu), C.byref(sw))
            Eref = float(rE[nr // 2:nr].mean())
            for mi, meth in enumerate(("metro", "mask", "pt", "ptmask")):
                lib.seed_rng(10 * seed + mi + 1)
                pm = 0.5 if "mask" in meth else 0.0
                if meth in ("metro", "mask"):
                    s = np.zeros(n, np.int8)
                    lib.random_state(n, s)
                    am = C.c_double()
                    nr = lib.run_single(n, off, nb, w, h, beta, s, moff, midx, len(moff) - 1, pm, budget, ref, rE, rq,
                                        MAXREC, C.byref(cu), C.byref(am))
                    extra = dict(acc_mask=am.value)
                else:
                    S = np.zeros(R * n, np.int8)
                    for k in range(R):
                        lib.random_state(n, S[k * n:(k + 1) * n])
                    nr = lib.run_pt(n, off, nb, w, h, R, betas, S, moff, midx, len(moff) - 1, pm, budget, ref, rE, rq,
                                    MAXREC, C.byref(cu), C.byref(sw))
                    extra = dict(swap=sw.value, R=R)
                row = dict(fam=fam, size=size, n=n, seed=seed, regime=reg, beta=beta, method=meth, budget=budget,
                           t_lib=tlib if "mask" in meth else 0.0, n_unique_minima=nuniq, mean_mask_len=mlen,
                           Eref=Eref, **extra, **summarize(rE, rq, cu.value, nr, Eref))
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(fam, size, seed, reg, meth, f"tauE_s={row['tauE_sec']:.2e} tauq_s={row['tauq_sec']:.2e}",
                      row["resE"], row["resq"], flush=True)


if __name__ == "__main__":
    main()
