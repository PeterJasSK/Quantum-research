"""Exp 3 (B6-18): Bayesian variable selection (fine-mapping) over 12 SNPs in 3 LD blocks of 4, exact.

Genotypes: two haplotypes per individual, each haplotype allele = 1[z > 0], z ~ N(0, Sigma), Sigma block
equicorrelated with latent rho chosen so the allele correlation (2/pi) arcsin(rho) = r_target (MAF 0.5);
genotype = sum of the two haplotypes, columns centred and standardised. N = 1000 individuals.
Causal set gamma0 ~ iid Bernoulli(pi=1/8) conditioned on 1 <= k0 <= 3; effects b ~ N(0, g (X^T X)^-1) on
gamma0 (g-prior draw, sigma = 1), y = X b + N(0,1), centred.
Posterior over all 4096 inclusion vectors: Zellner g-prior marginal likelihood (Liang et al. 2008, JASA 103:410,
intercept integrated out) p(y|gamma) ~ (1+g)^((N-1-k)/2) (1 + g (1 - R^2_gamma))^(-(N-1)/2), prior pi^k (1-pi)^(p-k).
E(gamma) = -log posterior; matched beta = 1 (model and hyper-parameters are the data-generating ones, up to the
k0 >= 1 conditioning).
Moves: L = add/delete one SNP (single flip); S = uniform swap (one included <-> one excluded, symmetric since
k(p-k) is conserved); W = LD-weighted swap (j chosen ~ r_ij^2, Hastings correction).

Usage: python exp3_genomics.py --rs 0.8,0.9,0.95,0.98 --gs 10,30,100 --inst 10 --out ...
"""
import argparse
import json
import time
import numpy as np
import d6lib as d

NIND, PI = 1000, 1.0 / 8
P = 12


def make_instance(r_target, g, inst):
    rng = np.random.default_rng([63, P, int(r_target * 1000), int(g), inst])
    rho = np.sin(np.pi * r_target / 2)
    blk = np.arange(P) // 4
    Sig = np.where(blk[:, None] == blk[None, :], rho, 0.0) + np.eye(P) * (1 - rho)
    Lc = np.linalg.cholesky(Sig)
    hap = lambda: (rng.normal(size=(NIND, P)) @ Lc.T > 0).astype(float)
    X = hap() + hap()
    X = (X - X.mean(0)) / X.std(0)
    while True:
        gam0 = rng.random(P) < PI
        if 1 <= gam0.sum() <= 3:
            break
    idx = np.nonzero(gam0)[0]
    XtX = X[:, idx].T @ X[:, idx]
    b = rng.multivariate_normal(np.zeros(len(idx)), g * np.linalg.inv(XtX))
    y = X[:, idx] @ b + rng.normal(size=NIND)
    y -= y.mean()
    return X, y, gam0


def log_post(X, y, g):
    Bt = d.bits(P)
    yy = y @ y
    Xy = X.T @ y
    XtX = X.T @ X
    lp = np.zeros(2 ** P)
    for a in range(2 ** P):
        idx = np.nonzero(Bt[a])[0]
        k = len(idx)
        R2 = 0.0 if k == 0 else float(Xy[idx] @ np.linalg.solve(XtX[np.ix_(idx, idx)], Xy[idx])) / yy
        lp[a] = (0.5 * (NIND - 1 - k) * np.log1p(g) - 0.5 * (NIND - 1) * np.log1p(g * (1 - R2))
                 + k * np.log(PI) + (P - k) * np.log(1 - PI))
    return lp


def swap_kernels(Rld):
    dim = 2 ** P
    Bt = d.bits(P)
    Qs = np.zeros((dim, dim))
    logW = np.full((dim, dim), -np.inf)
    w2 = Rld ** 2
    for a in range(dim):
        inn = np.nonzero(Bt[a])[0]
        out = np.nonzero(1 - Bt[a])[0]
        k = len(inn)
        if k == 0 or k == P:
            Qs[a, a] = 1.0
            logW[a, a] = 0.0
            continue
        for i in inn:
            ww = w2[i, out] / w2[i, out].sum()
            for j, pj in zip(out, ww):
                b = a ^ (1 << i) ^ (1 << int(j))
                Qs[a, b] += 1.0 / (k * (P - k))
                logW[a, b] = np.logaddexp(logW[a, b], np.log(pj / k))
    return Qs, logW


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rs", default="0.8,0.9,0.95,0.98")
    ap.add_argument("--gs", default="10,30,100")
    ap.add_argument("--inst", type=int, default=10)
    ap.add_argument("--betas", default="1,2,4,8")
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    global P
    P = a.P
    betas = [float(b) for b in a.betas.split(",")]
    rows, t0 = [], time.time()
    for r in [float(x) for x in a.rs.split(",")]:
        for g in [float(x) for x in a.gs.split(",")]:
            for inst in range(a.inst):
                X, y, gam0 = make_instance(r, g, inst)
                Rld = np.corrcoef(X.T)
                np.fill_diagonal(Rld, 0.0)
                emp_r = float(np.mean([abs(Rld[i, j]) for i in range(P) for j in range(P)
                                       if i != j and i // 4 == j // 4]))
                assert X.shape[1] == P
                E = -log_post(X, y, g)
                Qs, logW = swap_kernels(Rld)
                x0 = int(sum(int(gam0[i]) << i for i in range(P)))
                rows += d.evaluate(E, P, betas, structured={"S": ("sym", Qs), "W": ("log", logW)},
                                   lean=True, extra=dict(P=P, r_target=r, r_emp=emp_r, g=g, inst=inst,
                                                         k0=int(gam0.sum()), map_is_true=bool(np.argmin(E) == x0),
                                                         post_true=float(np.exp(d.logpi(E, 1.0))[x0])))
                print(f"r={r} g={g} inst={inst} t={time.time()-t0:.0f}s", flush=True)
                json.dump(rows, open(a.out, "w"))
    print("done", len(rows), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
