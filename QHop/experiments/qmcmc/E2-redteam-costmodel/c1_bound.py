"""E2 claim 1: numerical attack on the D7 theorem gap(any reversible group kernel mixture) <= 2 gap(block heat-bath mixture).
Exact matrices, SK n=6..8. Random-scan (state-independent p_g, uniform or Dirichlet), and fixed-order systematic scan (NOT
covered by the theorem). Kernels per group fiber: HB (heat-bath), MGS (Metropolized Gibbs, Liu 1996), MH with random symmetric
proposal, MH with random involution (perfect-matching) proposal, coarse-grained quantum (qmc.coarse_grained_Q).
Usage: python c1_bound.py -> results/c1_bound.csv, results/c1_summary.txt"""
import csv, itertools, os, sys, time
import numpy as np
sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(2024)


def fibers(n, G):
    dim = 2 ** n
    gm = 0
    for s in G:
        gm |= 1 << s
    idx = np.arange(dim)
    base = idx & ~gm
    # order inside each fiber by group-bit pattern
    k = len(G)
    gb = np.zeros(dim, int)
    for b, s in enumerate(G):
        gb |= ((idx >> s) & 1) << b
    fib = {}
    for a in idx:
        fib.setdefault(base[a], np.zeros(2 ** k, int))[gb[a]] = a
    return list(fib.values())


def fiber_kernel(kind, p, R=None):
    """pi_cond-reversible kernel on one fiber with conditional probs p."""
    m = len(p)
    if kind == "HB":
        return np.tile(p, (m, 1))
    if kind == "MGS":  # Metropolized Gibbs: propose y != x from p/(1-p_x), accept min(1,(1-p_x)/(1-p_y))
        P = np.zeros((m, m))
        for x in range(m):
            for y in range(m):
                if y != x:
                    P[x, y] = p[y] / max(1 - p[x], 1 - p[y], 1e-300)
            P[x, x] = max(0.0, 1 - P[x].sum())
        return P
    # symmetric proposal R, Metropolis accept
    with np.errstate(divide="ignore", invalid="ignore"):
        A = np.minimum(1.0, p[None, :] / p[:, None])
    P = R * A
    np.fill_diagonal(P, 0)
    P[np.diag_indices(m)] = 1 - P.sum(1)
    return P


def rand_sym(m):
    X = rng.random((m, m)) ** 3
    X = X + X.T
    for _ in range(200):  # Sinkhorn on symmetric -> symmetric doubly stochastic
        d = X.sum(1)
        X = X / np.sqrt(d[:, None] * d[None, :])
    return 0.5 * (X + X.T)


def rand_invol(m):
    perm = rng.permutation(m)
    R = np.zeros((m, m))
    for a, b in zip(perm[0::2], perm[1::2]):
        R[a, b] = R[b, a] = 1
    return R


def group_kernel(kind, n, G, pi):
    dim = len(pi)
    P = np.zeros((dim, dim))
    for f in fibers(n, G):
        p = pi[f] / pi[f].sum()
        m = len(f)
        R = rand_sym(m) if kind == "SYM" else (rand_invol(m) if kind == "INV" else None)
        P[np.ix_(f, f)] = fiber_kernel(kind if kind in ("HB", "MGS") else "R", p, R)
    return P


def gaps(P, pi):
    if not np.all(np.isfinite(P)):
        raise RuntimeError("nonfinite P")
    A = np.sqrt(np.maximum(P, 0) * np.maximum(P.T, 0))  # = D^1/2 P D^-1/2 for reversible P (no underflow)
    lam = np.sort(np.linalg.eigvalsh(A))
    right = 1 - lam[-2]
    absg = 1 - max(abs(lam[0]), abs(lam[-2]))
    return right, absg


def slem(P):
    lam = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    return lam[1]


def main():
    rows = []
    t0 = time.time()
    ga, ts = qmc.draw_params(5, 8)
    ga = np.round(ga * 4) / 4  # small gamma grid for eigh caching
    for n in (6, 8):
        for seed in range(1, 6 if n == 6 else 4):
            J, h = qmc.sk_instance(n, seed)
            E = qmc.ising_energies(J, h)
            for beta in (0.1, 0.3, 1.0, 3.0):
                pi = np.maximum(qmc.boltzmann(E, beta), 1e-250)
                pi /= pi.sum()
                for k in (1, 2, 3):
                    blocks = [list(range(i, i + k)) for i in range(0, n, k) if i + k <= n]
                    rnd = [sorted(rng.choice(n, k, replace=False).tolist()) for _ in range(n)]
                    for gname, groups in (("blocks", blocks), ("random", rnd)):
                        for pname in ("uniform", "dirichlet"):
                            pg = np.full(len(groups), 1 / len(groups)) if pname == "uniform" else rng.dirichlet(
                                np.full(len(groups), 0.5))
                            Ks = {}
                            for kind in ("HB", "MGS", "SYM", "INV"):
                                Ks[kind] = [group_kernel(kind, n, G, pi) for G in groups]
                            if k >= 2 and n <= 6:
                                Qq = qmc.coarse_grained_Q(J, h, groups, gammas=ga, ts=ts, group_probs=pg)
                                Qq = 0.5 * (Qq + Qq.T)
                                Pq = qmc.mh_matrix(Qq, E, beta)
                            else:
                                Pq = None
                            mixes = {kind: sum(w * K for w, K in zip(pg, Ks[kind])) for kind in Ks}
                            if Pq is not None:
                                mixes["QCG"] = Pq
                            gHB = gaps(mixes["HB"], pi)
                            for kind, P in mixes.items():
                                if kind == "HB":
                                    continue
                                try:
                                    g = gaps(P, pi)
                                except Exception as e:
                                    print("FAIL", kind, n, seed, beta, k, gname, pname, e, flush=True); continue
                                rows.append(dict(scan="random", n=n, seed=seed, beta=beta, k=k, groups=gname, pg=pname,
                                                 kernel=kind, right_ratio=g[0] / gHB[0], abs_ratio=g[1] / gHB[1],
                                                 gap_HB=gHB[0]))
                            # systematic scan (fixed order, blocks only, one sweep = product over groups)
                            if gname == "blocks" and pname == "uniform":
                                def sweep(Ps):
                                    M = np.eye(len(pi))
                                    for P in Ps:
                                        M = M @ P
                                    return M
                                lHB = slem(sweep(Ks["HB"]))
                                for kind in ("MGS", "SYM", "INV"):
                                    l = slem(sweep(Ks[kind]))
                                    rows.append(dict(scan="systematic", n=n, seed=seed, beta=beta, k=k, groups=gname,
                                                     pg=pname, kernel=kind, right_ratio=(1 - l) / max(1 - lHB, 1e-300),
                                                     abs_ratio=np.log(max(l, 1e-300)) / np.log(max(lHB, 1e-300)),
                                                     gap_HB=1 - lHB))
            print(n, seed, f"{time.time()-t0:.0f}s", flush=True)
    with open(os.path.join(HERE, "results", "c1_bound.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    out = []
    for scan in ("random", "systematic"):
        for kind in ("MGS", "SYM", "INV", "QCG"):
            r = [x for x in rows if x["scan"] == scan and x["kernel"] == kind]
            if not r:
                continue
            rr = np.array([x["right_ratio"] for x in r])
            ar = np.array([x["abs_ratio"] for x in r])
            i = int(rr.argmax())
            out.append(f"{scan:10s} {kind:4s} N={len(r):4d} right/1-slem ratio max={rr.max():.4f} median={np.median(rr):.3f}"
                       f" | abs (or log-rate) ratio max={ar.max():.4f} | argmax n={r[i]['n']} beta={r[i]['beta']} k={r[i]['k']}"
                       f" {r[i]['groups']} {r[i]['pg']}")
    open(os.path.join(HERE, "results", "c1_summary.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
