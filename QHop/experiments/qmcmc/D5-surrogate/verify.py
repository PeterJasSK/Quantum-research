"""D5 verification of claims (i) exactness, (ii) acceptance formula (analytic part), (iii) DA exactness.
import sys; sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
Run: OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 python verify.py
Writes results/verify.json and prints a summary."""
import json
import time
import numpy as np
from scipy import integrate
import d5lib as L
import qmc

t0 = time.time()
out = {"exactness": [], "analytic_2phi": [], "mc_chain": []}

# ---------------- (ii) analytic: Gaussian independent residuals -> D = beta (r' - r) ~ N(m, 2m), m = beta^2 sigma^2
for x in [0.25, 0.5, 1.0, 2.0, 3.0, 5.0]:
    m = x * x
    f = lambda d: min(1.0, np.exp(-d)) * np.exp(-(d - m) ** 2 / (4 * m)) / np.sqrt(4 * np.pi * m)
    val, _ = integrate.quad(f, m - 40 * np.sqrt(2 * m), m + 40 * np.sqrt(2 * m), points=[0.0], limit=400)
    out["analytic_2phi"].append(dict(beta_sigma=x, integral=val, two_phi=float(L.two_phi(x))))

# ---------------- (i),(iii) exact stationarity on full matrices, n = 8 and 10
for n in (8, 10):
    X = L.quad_design(n)
    gam, ts = L.qparams(7, 16)
    Ql = qmc.local_Q(n)
    for fam, rho in (("a", 0.3), ("b", 0.5), ("c", 0.3)):
        cache = {}
        Et, Es, info = L.make_family(fam, n, 0, rho, X, cache)
        bc, betas, *_ = L.regime_betas(Et, n)
        Qs = L.quantum_Q_sym(Es, gam, ts)
        Qraw = qmc.quantum_Q(Es, gam, ts)
        asym_raw = float(np.abs(Qraw - Qraw.T).max())
        # asymmetric control: T1-like decay 1->0 with prob p per bit after the measurement
        p = 0.02
        D1 = np.array([[1.0, 0.0], [p, 1 - p]])
        D = D1
        for _ in range(n - 1):
            D = np.kron(D1, D)  # bit ordering irrelevant: same factor per bit
        Qdec = Qs @ D
        for reg, beta in betas.items():
            lpt = L.logpi(Et, beta)
            pit = np.exp(lpt)
            Psur = L.mh_sym(Ql, Es, beta)
            K10 = L.matpow10(Psur)
            Pqs_inner = L.mh_sym(Qs, Es, beta)
            K10q = L.matpow10(Pqs_inner)
            cases = {
                "quantum_sur_in_U (1)": L.mh_sym(Qs, Et, beta),
                "DA_local_K1 (4)": L.da_outer(Psur, Et, Es, beta),
                "DA_local_K10 (4)": L.da_outer(K10, Et, Es, beta),
                "DA_exact_surrogate_draw_Kinf (4)": L.da_outer(L.independence_kernel(Es, beta), Et, Es, beta),
                "nested_quantum_inner_K10 (5)": L.da_outer(K10q, Et, Es, beta),
                "CONTROL_DA_K10_naive_ratio": L.da_naive(K10, Et, beta),
                "CONTROL_quantum_sur_T1_decay_p0.02": L.mh_sym(Qdec, Et, beta),
            }
            for name, P in cases.items():
                st, db = L.stationarity(P, lpt)
                pst = L.stationary_dist(P)
                tv = float(0.5 * np.abs(pst - pit).sum())
                out["exactness"].append(dict(n=n, fam=fam, rho=rho, regime=reg, beta=beta, case=name,
                                             stat_L1=st, detbal_L1=db, TV_stationary_vs_pi_true=tv,
                                             raw_Q_max_asym=asym_raw))

# ---------------- sampled chain check (n = 8, fam a rho 0.3, MEDIUM): DA K=10 inner local steps simulated explicitly
n = 8
X = L.quad_design(n)
Et, Es, info = L.make_family("a", n, 0, 0.3, X, {})
bc, betas, *_ = L.regime_betas(Et, n)
beta = betas["MEDIUM"]
pit = np.exp(L.logpi(Et, beta))
S = qmc.spins(n)
rng = np.random.default_rng(123)


def run_da(steps, K, correct=True):
    a = 0
    hist = np.zeros(2 ** n)
    for _ in range(steps):
        b = a
        for _k in range(K):  # inner Metropolis on the surrogate (local flips)
            c = b ^ (1 << rng.integers(n))
            d = Es[c] - Es[b]
            if d <= 0 or rng.random() < np.exp(-beta * d):
                b = c
        if correct:
            lr = -beta * ((Et[b] - Es[b]) - (Et[a] - Es[a]))
        else:
            lr = -beta * (Et[b] - Et[a])
        if lr >= 0 or rng.random() < np.exp(lr):
            a = b
        hist[a] += 1
    return hist / hist.sum()


for correct in (True, False):
    h = run_da(200000, 10, correct)
    out["mc_chain"].append(dict(n=n, fam="a", rho=0.3, beta=beta, K=10, corrected_ratio=correct, steps=200000,
                                TV_hist_vs_pi_true=float(0.5 * np.abs(h - pit).sum())))
# reference: TV of an exact i.i.d. sample of the same size (sampling noise floor)
ref = rng.multinomial(200000, pit) / 200000
out["mc_chain"].append(dict(note="iid sample of pi_true, same size (noise floor)", TV=float(0.5 * np.abs(ref - pit).sum())))

out["runtime_s"] = time.time() - t0
json.dump(out, open("results/verify.json", "w"), indent=1)
for r in out["analytic_2phi"]:
    print("2phi", r)
for r in out["exactness"]:
    print(f"n={r['n']} {r['fam']} {r['regime']:6s} {r['case']:38s} stat={r['stat_L1']:.1e} db={r['detbal_L1']:.1e} TV={r['TV_stationary_vs_pi_true']:.1e}")
for r in out["mc_chain"]:
    print(r)
print("runtime", out["runtime_s"])
