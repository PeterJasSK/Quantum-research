"""B7 implementation-variant checks for the QeMCMC applied review.

Exact small-n checks (n<=10, mostly n<=8). For each variant: stationarity error
err = max_s |(pi P)(s) - pi(s)| and, for broken variants, TV distance between the chain's true
stationary distribution and Boltzmann pi.  Run:  python b7_checks.py [section ...]
Output is plain text; results captured in B7-checks/results.txt.
"""
import sys
import time
import itertools
import numpy as np
from scipy.linalg import eigh, expm

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402


# ------------------------------------------------------------------ helpers
def stat_err(P, pi):
    return float(np.max(np.abs(pi @ P - pi)))


def stationary(P):
    w, v = np.linalg.eig(P.T)
    k = int(np.argmin(np.abs(w - 1)))
    p = np.real(v[:, k])
    return p / p.sum()


def tv(p, q):
    return float(0.5 * np.abs(p - q).sum())


def fill_diag(P):
    np.fill_diagonal(P, 0.0)
    P[np.diag_indices_from(P)] = 1.0 - P.sum(1)
    return P


def mh_custom(Q, A):
    return fill_diag(Q * A)


def gap_any(P):
    lam = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    return float(1.0 - lam[1])


def report(name, P, pi, extra=""):
    e = stat_err(P, pi)
    t = tv(stationary(P), pi) if e > 1e-10 else 0.0
    print(f"  {name:58s} err={e:.2e}  TV(stat,pi)={t:.2e} {extra}")
    return e, t


def asym(Q):
    return float(np.abs(Q - Q.T).max())


def sk(n, seed):
    J, h = qmc.sk_instance(n, seed)
    return J, h, qmc.ising_energies(J, h)


GAM, TS = qmc.draw_params(5, 12)


def U_of(H, t):
    w, V = eigh(H)
    return (V * np.exp(-1j * w * t)) @ V.T


def U_general(H, t):
    return expm(-1j * H * t)


def Q_from_unitaries(Us):
    return sum(np.abs(U.T) ** 2 for U in Us) / len(Us)  # Q[a,b] = |<b|U|a>|^2 = |U[b,a]|^2


def xop(n, i):
    dim = 2 ** n
    a = np.arange(dim)
    M = np.zeros((dim, dim))
    M[a, a ^ (1 << i)] = 1.0
    return M


def yop(n, i):
    dim = 2 ** n
    a = np.arange(dim)
    M = np.zeros((dim, dim), complex)
    bit = (a >> i) & 1
    # Y|0>=i|1>, Y|1>=-i|0>  -> M[b,a]
    M[a ^ (1 << i), a] = np.where(bit == 0, 1j, -1j)
    return M


def zdiag(n, i):
    a = np.arange(2 ** n)
    return 1.0 - 2.0 * ((a >> i) & 1)


# ------------------------------------------------------------------ V01 CG group selection
def v01():
    print("V01 coarse-grained group selection (SK n=6, beta=1, groups = 6 cyclic triples)")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    groups = [[i, (i + 1) % n, (i + 2) % n] for i in range(n)]
    Qg = [qmc.coarse_grained_Q(J, h, [G], gammas=GAM, ts=TS) for G in groups]
    Qr = sum(Qg) / len(Qg)
    report("uniform random group (P2 style), plain Metropolis", qmc.mh_matrix(Qr, E, beta), pi)
    w = np.array([np.abs(J[np.ix_(G, G)]).sum() for G in groups])
    Qw = sum(wi * Q for wi, Q in zip(w / w.sum(), Qg))
    report("coupling-strength weighted (state-independent) group", qmc.mh_matrix(Qw, E, beta), pi)
    S = qmc.spins(n).astype(float)
    f = np.maximum(0.0, -S * (S @ J + h))  # unsatisfied local field per spin
    for lam in (1.0, 3.0):
        F = np.stack([f[:, G].sum(1) for G in groups], 1)
        p = np.exp(lam * F)
        p /= p.sum(1, keepdims=True)
        Qn = sum(p[:, [k]] * Qg[k] for k in range(len(groups)))
        report(f"frustration-selected lam={lam}, plain Metropolis (naive)", qmc.mh_matrix(Qn, E, beta), pi)
        P = np.zeros_like(Qn)
        for k in range(len(groups)):
            A = np.minimum(1.0, (pi[None, :] * p[:, k][None, :]) / (pi[:, None] * p[:, k][:, None]))
            P += p[:, [k]] * Qg[k] * A
        P = fill_diag(P)
        report(f"frustration-selected lam={lam}, Hastings p(g|s')/p(g|s)", P, pi,
               f"gap={qmc.spectral_gap(P, pi):.4f} vs uniform-group {qmc.gap(Qr, E, beta):.4f}")


# ------------------------------------------------------------------ V02 sweep order
def v02():
    print("V02 multi-group sweep (SK n=6, beta=1, groups {0,1,2},{3,4,5})")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    g1, g2 = [0, 1, 2], [3, 4, 5]
    Q1 = qmc.coarse_grained_Q(J, h, [g1], gammas=GAM, ts=TS)
    Q2 = qmc.coarse_grained_Q(J, h, [g2], gammas=GAM, ts=TS)
    Qf = Q1 @ Q2
    print(f"  asymmetry max|Q-Q^T|: fixed order {asym(Qf):.3e}, fwd/rev mixture {asym(0.5*(Q1@Q2+Q2@Q1)):.3e}")
    report("P2 fixed order g1->g2, one Metropolis at end", qmc.mh_matrix(Qf, E, beta), pi)
    Pfr = qmc.mh_matrix(0.5 * (Q1 @ Q2 + Q2 @ Q1), E, beta)
    report("random forward/reverse order, one Metropolis at end", Pfr, pi, f"gap={gap_any(Pfr):.4f}")
    P1, P2 = qmc.mh_matrix(Q1, E, beta), qmc.mh_matrix(Q2, E, beta)
    report("per-group Metropolis, systematic scan P1 P2", P1 @ P2, pi, f"gap(nonrev)={gap_any(P1@P2):.4f}")
    report("per-group Metropolis, random scan (P1+P2)/2", 0.5 * (P1 + P2), pi, f"gap={gap_any(0.5*(P1+P2)):.4f}")
    Q3 = qmc.coarse_grained_Q(J, h, [[2, 3, 4]], gammas=GAM, ts=TS)
    perms = list(itertools.permutations([Q1, Q2, Q3]))
    Qp = sum(a @ b @ c for a, b, c in perms) / len(perms)
    report("3 overlapping groups, uniformly random order (closed under reversal)", qmc.mh_matrix(Qp, E, beta), pi)


# ------------------------------------------------------------------ V03 parallel groups
def _par(Q1, Q2, g1, g2, n):
    dim = 2 ** n
    m1 = sum(1 << i for i in g1)
    m2 = sum(1 << i for i in g2)
    Q = np.zeros((dim, dim))
    for a in range(dim):
        for b in range(dim):
            if (a ^ b) & ~(m1 | m2):
                continue
            b1 = (a & ~m1) | (b & m1)
            b2 = (a & ~m2) | (b & m2)
            Q[a, b] = Q1[a, b1] * Q2[a, b2]
    return Q


def v03():
    print("V03 parallel QPUs on disjoint groups (SK n=6, beta=1, g1={0,1}, g2={3,4}, frozen {2,5})")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    g1, g2 = [0, 1], [3, 4]
    Q1 = qmc.coarse_grained_Q(J, h, [g1], gammas=GAM, ts=TS)
    Q2 = qmc.coarse_grained_Q(J, h, [g2], gammas=GAM, ts=TS)
    Ql = qmc.local_Q(n)  # 50/50 mixture with local moves so the chain is irreducible (frozen spins move)
    report("simultaneous (Jacobi) fields from old state, plain Metropolis", qmc.mh_matrix(0.5 * _par(Q1, Q2, g1, g2, n) + 0.5 * Ql, E, beta), pi)
    Jd = J.copy()
    Jd[np.ix_(g1, g2)] = 0
    Jd[np.ix_(g2, g1)] = 0
    Q1d = qmc.coarse_grained_Q(Jd, h, [g1], gammas=GAM, ts=TS)
    Q2d = qmc.coarse_grained_Q(Jd, h, [g2], gammas=GAM, ts=TS)
    Pd = qmc.mh_matrix(0.5 * _par(Q1d, Q2d, g1, g2, n) + 0.5 * Ql, E, beta)
    report("decoupled surrogate (inter-group J dropped in U), true-E accept", Pd, pi, f"gap={qmc.spectral_gap(Pd, pi):.4f}")


# ------------------------------------------------------------------ V04 mixture with local
def v04():
    print("V04 mixture w*Quantum + (1-w)*Local, cost-weighted (SK n=8)")
    n = 8
    J, h, E = sk(n, 21)
    g, t = qmc.draw_params(7, 20)
    Qq = qmc.quantum_Q(E, g, t)
    Ql = qmc.local_Q(n)
    ws = [0, 1e-4, 1e-3, 1e-2, 0.03, 0.1, 0.3, 1.0]
    for beta in (1.0, 0.3):
        pi = qmc.boltzmann(E, beta)
        gaps = [qmc.gap(qmc.mixture_Q([Qq, Ql], [w, 1 - w]), E, beta) for w in ws]
        gq, gl = gaps[-1], gaps[0]
        print(f"  beta={beta}: gap local={gl:.3e} quantum={gq:.3e}; err(mix w=0.1)="
              f"{stat_err(qmc.mh_matrix(qmc.mixture_Q([Qq, Ql],[0.1,0.9]), E, beta), pi):.1e}")
        print("   w      gap(w)     gap/(w gq+(1-w)gl)")
        for w, gw in zip(ws, gaps):
            lin = w * gq + (1 - w) * gl
            print(f"   {w:<6g} {gw:.3e}  {gw/lin:6.2f}")
        for R in (1e2, 1e4, 1e8):
            eff = [gw / (w * R + (1 - w)) for w, gw in zip(ws, gaps)]
            k = int(np.argmax(eff))
            print(f"   cost ratio t_Q/t_C={R:g}: best w={ws[k]:g}, gap-per-time gain over pure local={eff[k]/eff[0]:.3f}")


# ------------------------------------------------------------------ V05 surrogate
def v05():
    print("V05 surrogate H_prob inside U, true E in accept (SK n=8, beta=1)")
    n, beta = 8, 1.0
    J, h, E = sk(n, 21)
    pi = qmc.boltzmann(E, beta)
    g, t = qmc.draw_params(7, 20)
    rng = np.random.default_rng(3)
    sd = E.std()
    print(f"  baselines: gap local={qmc.gap(qmc.local_Q(n), E, beta):.3e} uniform={qmc.gap(qmc.uniform_Q(n), E, beta):.3e}")
    Jnn = np.zeros_like(J)
    for i in range(n - 1):
        Jnn[i, i + 1] = Jnn[i + 1, i] = J[i, i + 1]
    surr = [("exact E", E)]
    for s in (0.3, 1.0, 3.0):
        surr.append((f"E + {s} sd noise", E + s * sd * rng.normal(size=E.size)))
    surr.append(("line-only couplings (hardware-native subset)", qmc.ising_energies(Jnn, h)))
    surr.append(("fields only (J=0)", qmc.ising_energies(np.zeros_like(J), h)))
    surr.append(("independent random SK instance", sk(n, 999)[2]))
    for name, Hs in surr:
        Q = qmc.quantum_Q(Hs, g, t)
        P = qmc.mh_matrix(Q, E, beta)
        rho = np.corrcoef(Hs, E)[0, 1]
        e = stat_err(P, pi)
        print(f"  {name:46s} corr={rho:5.2f} asym={asym(Q):.1e} err={e:.1e} acc={qmc.acceptance(Q,E,beta):.3f} "
              f"gap={qmc.spectral_gap(P, pi):.3e}")


# ------------------------------------------------------------------ V06 temperature-aware tuning
def v06():
    print("V06 temperature-aware gamma/t/alpha (SK n=8, 2 instances); gap ratios vs P1 default")
    n = 8
    gl = [0.15, 0.3, 0.45, 0.6, 0.75]
    tw = [(0.5, 2.0), (2.0, 20.0), (20.0, 60.0)]
    betas = [0.1, 0.3, 1.0, 3.0]
    for seed in (21, 22):
        J, h, E = sk(n, seed)
        a0 = qmc.alpha_from_energy(E)
        Hm = qmc.mixer(n)
        rng = np.random.default_rng(seed)
        tdraw = {w: rng.uniform(*w, 15) for w in tw}
        for beta in betas:
            res = {}
            Qs = []
            for amode in ("norm", "beta"):
                a = a0 if amode == "norm" else a0 * beta
                for gm in gl:
                    for w in tw:
                        Q = qmc.quantum_Q(E, np.full(15, gm), tdraw[w], alpha=a, Hm=Hm)
                        Qs.append(Q)
                        res[(amode, gm, w)] = qmc.gap(Q, E, beta)
            g, t = qmc.draw_params(7, 20)
            gp1 = qmc.gap(qmc.quantum_Q(E, g, t, Hm=Hm), E, beta)
            best = max(res, key=res.get)
            gmix = qmc.gap(sum(Qs) / len(Qs), E, beta)
            gl_ = qmc.gap(qmc.local_Q(n), E, beta)
            gu = qmc.gap(qmc.uniform_Q(n), E, beta)
            print(f"  seed {seed} beta={beta}: P1 gap={gp1:.3e}; best {best} gap={res[best]:.3e} ({res[best]/gp1:.2f}x); "
                  f"fixed grid mixture {gmix/gp1:.2f}x; local {gl_:.2e} uniform {gu:.2e}")


# ------------------------------------------------------------------ V07 Rydberg
def rydberg_H(n, Om, De, V0, phi=0.0):
    dim = 2 ** n
    a = np.arange(dim)
    b = ((a[:, None] >> np.arange(n)) & 1).astype(float)
    d = -De * b.sum(1)
    for i in range(n):
        for j in range(i + 1, n):
            d += V0 / (j - i) ** 6 * b[:, i] * b[:, j]
    H = np.diag(d).astype(complex)
    for i in range(n):
        H += Om / 2 * (np.cos(phi) * xop(n, i) + np.sin(phi) * yop(n, i))
    return H


def v07():
    print("V07 Rydberg analog proposal used for an SK n=5 target (beta=1); Rydberg H acts as a surrogate")
    n, beta = 5, 1.0
    J, h, E = sk(n, 31)
    pi = qmc.boltzmann(E, beta)
    T, K = 6.0, 30
    dt = T / K
    tau = (np.arange(K) + 0.5) / K

    def evolve(Oms, Des, phi=0.0):
        U = np.eye(2 ** n, dtype=complex)
        for Om, De in zip(Oms, Des):
            U = U_general(rydberg_H(n, Om, De, 5.0, phi), dt) @ U
        return U

    cases = {
        "constant pulse (Om=1, De=0.5)": [evolve(np.ones(K), 0.5 * np.ones(K))],
        "constant pulse with laser phase 0.7": [evolve(np.ones(K), 0.5 * np.ones(K), 0.7)],
        "one-way detuning sweep -2 -> +2 (non-palindromic)": [evolve(np.sin(np.pi * tau), -2 + 4 * tau)],
        "palindromic sweep -2 -> +2 -> -2": [evolve(np.sin(np.pi * tau), -2 + 4 * (1 - np.abs(2 * tau - 1)))],
    }
    Uf = cases["one-way detuning sweep -2 -> +2 (non-palindromic)"][0]
    Ub = evolve(np.sin(np.pi * tau)[::-1], (-2 + 4 * tau)[::-1])
    cases["50/50 mixture of sweep and its time reverse"] = [Uf, Ub]
    for name, Us in cases.items():
        Q = Q_from_unitaries(Us)
        P = qmc.mh_matrix(Q, E, beta)
        report(name, P, pi, f"asym={asym(Q):.1e}")


# ------------------------------------------------------------------ V08 reverse annealing
def glauber(E, beta_p, n):
    dim = 2 ** n
    a = np.arange(dim)
    G = np.zeros((dim, dim))
    for i in range(n):
        b = a ^ (1 << i)
        p = 1.0 / (1.0 + np.exp(beta_p * (E[b] - E[a])))
        G[a, b] += p / n
    return fill_diag(G)


def v08():
    print("V08 D-Wave-style reverse anneal (SK n=5, target beta=1); closed part + thermal part")
    n, beta = 5, 1.0
    J, h, E = sk(n, 31)
    pi = qmc.boltzmann(E, beta)
    a = qmc.alpha_from_energy(E)
    Hm = qmc.mixer(n)
    K, T1, Tp, sp = 20, 5.0, 5.0, 0.45
    sched = list(1 - (1 - sp) * (np.arange(K) + 0.5) / K) + [sp] * K + list(sp + (1 - sp) * (np.arange(K) + 0.5) / K)
    dts = [T1 / K] * K + [Tp / K] * K + [T1 / K] * K
    U = np.eye(2 ** n, dtype=complex)
    for s, d in zip(sched, dts):
        U = U_of(-(1 - s) * Hm + s * a * np.diag(E), d) @ U
    Qc = Q_from_unitaries([U])
    report("closed-system palindromic reverse anneal, plain Metropolis", qmc.mh_matrix(Qc, E, beta), pi)
    rng = np.random.default_rng(1)
    E_ice = E + 0.03 * E.std() * rng.normal(size=E.size)  # programming (ICE) error on device
    for bp in (2.0,):
        Gk = np.linalg.matrix_power(glauber(E, bp, n), n)
        Gice = np.linalg.matrix_power(glauber(E_ice, bp, n), n)
        pip = qmc.boltzmann(E, bp)
        for lam in (0.1, 0.5, 1.0):
            Q = (1 - lam) * Qc + lam * Gk
            report(f"thermal frac {lam}, plain Metropolis", qmc.mh_matrix(Q, E, beta), pi)
            A = np.minimum(1.0, (pi[None, :] * pip[:, None]) / (pi[:, None] * pip[None, :]))
            report(f"thermal frac {lam}, Gibbs-corrected (known beta_phys, H)", mh_custom(Q, A), pi)
            report(f"thermal frac {lam}, exact Hastings (needs Q values)", qmc.mh_matrix(Q, E, beta, hastings=True), pi)
        Q = Gice
        A = np.minimum(1.0, (pi[None, :] * pip[:, None]) / (pi[:, None] * pip[None, :]))
        report("pure thermal on ICE-perturbed H (3% sd), Gibbs-corrected nominal", mh_custom(Q, A), pi)


# ------------------------------------------------------------------ V09 MTM and hub GMH
def v09():
    print("V09 shot batching: multiple-try Metropolis K=2 and Tjelmeland/Calderhead hub (SK n=4, beta=1)")
    n, beta = 4, 1.0
    J, h, E = sk(n, 41)
    pi = qmc.boltzmann(E, beta)
    Q = qmc.quantum_Q(E, GAM, TS)
    dim = 2 ** n
    Pm = np.zeros((dim, dim))
    Pn = np.zeros((dim, dim))
    Ph = np.zeros((dim, dim))
    for x in range(dim):
        for y1 in range(dim):
            for y2 in range(dim):
                pr = Q[x, y1] * Q[x, y2]
                sw = pi[y1] + pi[y2]
                for y in (y1, y2):
                    sel = pi[y] / sw
                    # MTM: reference x1* ~ Q(.|y), x2* = x
                    acc = np.minimum(1.0, sw / (pi + pi[x]))  # vector over x1*
                    Pm[x, y] += pr * sel * (Q[y] * acc).sum()
                    Pn[x, y] += pr * sel * min(1.0, pi[y] / pi[x])
        for z in range(dim):
            for y1 in range(dim):
                for y2 in range(dim):
                    pr = Q[x, z] * Q[z, y1] * Q[z, y2]
                    tot = pi[x] + pi[y1] + pi[y2]
                    Ph[x, y1] += pr * pi[y1] / tot
                    Ph[x, y2] += pr * pi[y2] / tot
                    Ph[x, x] += pr * pi[x] / tot
    Pm = fill_diag(Pm)
    Pn = fill_diag(Pn)
    np.fill_diagonal(Ph, 0)
    Ph = fill_diag(Ph)
    P1 = qmc.mh_matrix(Q, E, beta)
    report("plain QeMCMC (1 circuit, 1 shot)", P1, pi, f"gap={gap_any(P1):.4f}; two steps={gap_any(P1@P1):.4f}")
    report("MTM K=2 (2 circuits: K shots at x, K-1 at y)", Pm, pi, f"gap={gap_any(Pm):.4f}")
    report("naive best-of-2 + plain Metropolis (no reference set)", Pn, pi)
    report("hub GMH: z~Q(.|x), N=2 shots from z, pick prop. to pi", Ph, pi, f"gap={gap_any(Ph):.4f}")


# ------------------------------------------------------------------ V10 Trotter / QAOA
def v10():
    print("V10 shallow circuits: Trotter / QAOA-layer symmetry (SK n=6, beta=1)")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    a = qmc.alpha_from_energy(E)
    Hm = qmc.mixer(n)
    wB, VB = eigh(Hm)

    def eB(x):
        return (VB * np.exp(-1j * wB * x)) @ VB.T

    def eA(x):
        return np.diag(np.exp(-1j * x * a * E))

    for r in (1, 2, 4, 8, 32):
        Us = []
        for gm, t in zip(GAM, TS):
            dt = t / r
            step = eA((1 - gm) * dt) @ eB(gm * dt)
            Us.append(np.linalg.matrix_power(step, r))
        Q = Q_from_unitaries(Us)
        P = qmc.mh_matrix(Q, E, beta)
        print(f"  first-order Trotter r={r:2d}: asym={asym(Q):.1e} err={stat_err(P, pi):.1e} gap={qmc.spectral_gap(P, pi):.4f}")
    Qex = qmc.quantum_Q(E, GAM, TS)
    print(f"  exact exp(-iHt): gap={qmc.gap(Qex, E, beta):.4f}; local={qmc.gap(qmc.local_Q(n), E, beta):.4f}")
    rng = np.random.default_rng(5)
    Ur, Up = [], []
    for _ in range(12):
        g = rng.uniform(0, 2, 3)
        b = rng.uniform(0, 1.5, 3)
        Ur.append(eB(b[2]) @ eA(g[2]) @ eB(b[1]) @ eA(g[1]) @ eB(b[0]) @ eA(g[0]))
        Up.append(eB(b[0]) @ eA(g[0]) @ eB(b[1]) @ eA(g[0]) @ eB(b[0]))
    for name, Us in (("QAOA p=3 random (non-palindromic) angles", Ur), ("palindromic B A B' A B angles", Up)):
        Q = Q_from_unitaries(Us)
        report(name, qmc.mh_matrix(Q, E, beta), pi, f"asym={asym(Q):.1e}")


# ------------------------------------------------------------------ V11 Potts
def v11():
    print("V11 Potts q=3 on a triangle (27 feasible states), beta=1")
    rng = np.random.default_rng(8)
    ns, q = 3, 3
    Jp = rng.normal(size=(ns, ns))
    Jp = np.triu(Jp, 1)
    hp = rng.normal(size=(ns, q))
    beta = 1.0
    colors = list(itertools.product(range(q), repeat=ns))

    def Epotts(c):
        e = -sum(Jp[i, j] * (c[i] == c[j]) for i in range(ns) for j in range(i + 1, ns))
        return e - sum(hp[i, c[i]] for i in range(ns))

    Ef = np.array([Epotts(c) for c in colors])
    pi = qmc.boltzmann(Ef, beta)
    # one-hot: qubit 3i+c
    nq = ns * q
    dim = 2 ** nq
    bits = (np.arange(dim)[:, None] >> np.arange(nq)) & 1
    occ = bits.reshape(dim, ns, q)
    Eq = np.zeros(dim)
    for i in range(ns):
        for j in range(i + 1, ns):
            Eq -= Jp[i, j] * (occ[:, i, :] * occ[:, j, :]).sum(1)
        Eq -= (occ[:, i, :] * hp[i]).sum(1)
    Eq += 4.0 * ((occ.sum(2) - 1) ** 2).sum(1)
    feas_idx = np.array([sum(1 << (q * i + c[i]) for i in range(ns)) for c in colors])
    g, t = qmc.draw_params(7, 12)
    Qx = qmc.quantum_Q(Eq, g, t)
    Hxy = np.zeros((dim, dim))
    for a in range(dim):
        for i in range(ns):
            for c1 in range(q):
                for c2 in range(c1 + 1, q):
                    b1, b2 = q * i + c1, q * i + c2
                    if ((a >> b1) & 1) != ((a >> b2) & 1):
                        Hxy[a, a ^ (1 << b1) ^ (1 << b2)] += 1.0
    Qxy = qmc.quantum_Q(Eq, g, t, Hm=Hxy)
    for name, Q in (("one-hot + X mixer", Qx), ("one-hot + XY mixer per site", Qxy)):
        Qf = Q[np.ix_(feas_idx, feas_idx)]
        leak = 1 - (pi @ Qf.sum(1))
        Pr = qmc.mh_matrix(Qf.copy(), Ef, beta)  # leaked mass -> stay (reject)
        rep = f"leak(pi-avg)={leak:.3f} gap={qmc.spectral_gap(Pr, pi):.4f}"
        report(f"{name}: infeasible outcome = reject (stay)", Pr, pi, rep)
        if leak > 1e-9:
            Qr = Qf / Qf.sum(1, keepdims=True)
            report(f"{name}: resample until feasible (renormalise)", qmc.mh_matrix(Qr, Ef, beta), pi)
    # binary encoding: 2 qubits per site, code 3 invalid
    nb = 2 * ns
    dimb = 2 ** nb
    codes = (np.arange(dimb)[:, None] >> (2 * np.arange(ns))) & 3
    valid = (codes < 3).all(1)
    Eb = np.array([Epotts(tuple(c)) if v else 0.0 for c, v in zip(codes, valid)])
    Eb[~valid] = Eb[valid].max() + 4.0
    Qb = qmc.quantum_Q(Eb, g, t)
    vid = np.where(valid)[0]
    # map valid binary states to colours order used by pi
    Ef_b = Eb[vid]
    pib = qmc.boltzmann(Ef_b, beta)
    Qbf = Qb[np.ix_(vid, vid)]
    report("binary log2(q) encoding, invalid code = reject", qmc.mh_matrix(Qbf.copy(), Ef_b, beta), pib,
           f"leak={1-(pib@Qbf.sum(1)):.3f} gap={qmc.spectral_gap(qmc.mh_matrix(Qbf.copy(), Ef_b, beta), pib):.4f}")
    print(f"  local Potts move (recolour 1 site) gap={_potts_local_gap(Ef, colors, q, beta):.4f}")


def _potts_local_gap(Ef, colors, q, beta):
    idx = {c: k for k, c in enumerate(colors)}
    m = len(colors)
    Q = np.zeros((m, m))
    for c in colors:
        for i in range(len(c)):
            for col in range(q):
                if col != c[i]:
                    d = list(c)
                    d[i] = col
                    Q[idx[c], idx[tuple(d)]] += 1.0 / (len(c) * (q - 1))
    return qmc.gap(Q, Ef, beta)


# ------------------------------------------------------------------ V12 noise
def lindblad_super(H, Ls):
    d = H.shape[0]
    I = np.eye(d)
    L = -1j * (np.kron(I, H) - np.kron(H.T, I))
    for Lk in Ls:
        LdL = Lk.conj().T @ Lk
        L += np.kron(Lk.conj(), Lk) - 0.5 * np.kron(I, LdL) - 0.5 * np.kron(LdL.T, I)
    return L


def noisy_Q(Ediag, jumps, gammas, ts, n):
    d = 2 ** n
    a = qmc.alpha_from_energy(Ediag)
    Hm = qmc.mixer(n)
    Q = np.zeros((d, d))
    diag_idx = np.arange(d) * (d + 1)  # vec index of |b><b| (column stacking)
    for gm, t in zip(gammas, ts):
        H = (1 - gm) * a * np.diag(Ediag) + gm * Hm
        S = expm(lindblad_super(H.astype(complex), jumps) * t)
        # column for input |a><a| is diag_idx[a]; output diag entries rows diag_idx
        Q += np.real(S[np.ix_(diag_idx, diag_idx)]).T
    return Q / len(gammas)


def v12():
    print("V12 noise and symmetrisation (SK n=4, beta=1, Lindblad exact)")
    n, beta = 4, 1.0
    J, h, E = sk(n, 41)
    pi = qmc.boltzmann(E, beta)
    g, t = GAM[:6], TS[:6]
    sm = []
    for i in range(n):  # sigma^- : |1> -> |0>  (bit 1 -> bit 0)
        M = np.zeros((2 ** n, 2 ** n))
        a = np.arange(2 ** n)
        sel = ((a >> i) & 1) == 1
        M[a[sel] ^ (1 << i), a[sel]] = 1.0
        sm.append(M.astype(complex))
    r = 0.01
    pauli = [np.sqrt(r / 2) * xop(n, i).astype(complex) for i in range(n)] + \
            [np.sqrt(r / 2) * yop(n, i) for i in range(n)] + [np.sqrt(r) * np.diag(zdiag(n, i)).astype(complex) for i in range(n)]
    Qp = noisy_Q(E, pauli, g, t, n)
    report("unital Pauli Lindblad noise (X,Y,Z), constant rate", qmc.mh_matrix(Qp, E, beta), pi, f"asym={asym(Qp):.1e}")
    ad = [np.sqrt(r) * M for M in sm]
    Qa = noisy_Q(E, ad, g, t, n)
    report("amplitude damping T1 (rate 0.01/unit time)", qmc.mh_matrix(Qa, E, beta), pi, f"asym={asym(Qa):.1e}")
    d = 2 ** n
    idx = np.arange(d)
    Qg = np.zeros((d, d))
    for gg in range(d):
        Qphys = noisy_Q(E[idx ^ gg], ad, g, t, n)  # physical problem = gauge-transformed energies
        Qg += Qphys[np.ix_(idx ^ gg, idx ^ gg)]
    Qg /= d
    report("amplitude damping + full spin-reversal gauge average (16)", qmc.mh_matrix(Qg, E, beta), pi, f"asym={asym(Qg):.1e}")
    ad3 = [np.sqrt(0.05) * M for M in sm]
    Qa3 = noisy_Q(E, ad3, g, t, n)
    Qg3 = np.zeros((d, d))
    for gg in range(d):
        Qphys = noisy_Q(E[idx ^ gg], ad3, g, t, n)
        Qg3 += Qphys[np.ix_(idx ^ gg, idx ^ gg)]
    Qg3 /= d
    report("amplitude damping rate 0.05, no gauge", qmc.mh_matrix(Qa3, E, beta), pi)
    report("amplitude damping rate 0.05 + gauge average", qmc.mh_matrix(Qg3, E, beta), pi, f"asym={asym(Qg3):.1e}")
    Qid = qmc.quantum_Q(E, g, t)
    eps = 0.02
    B1 = np.array([[1 - eps, eps], [eps, 1 - eps]])
    B = B1
    for _ in range(n - 1):
        B = np.kron(B, B1)
    report("ideal U + symmetric readout flips eps=0.02 at end (Q B)", qmc.mh_matrix(Qid @ B, E, beta), pi)
    report("ideal U + readout flips + matched random input flips (B Q B)", qmc.mh_matrix(B @ Qid @ B, E, beta), pi)
    # fidelity threshold at n=8 under global depolarising
    print("  global-depolarising model Q_F = F Q + (1-F) uniform, SK n=8:")
    n8 = 8
    J8, h8, E8 = sk(n8, 21)
    g8, t8 = qmc.draw_params(7, 20)
    Q8 = qmc.quantum_Q(E8, g8, t8)
    U8 = qmc.uniform_Q(n8)
    for beta in (3.0, 1.0, 0.3):
        best = max(qmc.gap(qmc.local_Q(n8), E8, beta), qmc.gap(U8, E8, beta))
        Fs = np.linspace(0, 1, 101)
        gs = np.array([qmc.gap(F * Q8 + (1 - F) * U8, E8, beta) for F in Fs])
        above = Fs[gs > 2 * best]  # fidelity needed to keep a 2x step advantage over best of local/uniform
        Fstar = above.min() if above.size else np.nan
        ncz = np.log(Fstar) / np.log(1 - 2e-3) if Fstar and Fstar > 0 else np.inf
        print(f"   beta={beta}: gap(F=1)={gs[-1]:.3e} best classical(local/uniform)={best:.3e} gap(F=0.1)={gs[10]:.3e} "
              f"gap(F=0.5)={gs[50]:.3e}; F for 2x over best classical={Fstar:.2f} -> max CZ at eps2q=2e-3: {ncz:.0f}")


# ------------------------------------------------------------------ V13 classical emulation timing
def apply_rx_all(psi, k, theta):
    c, s = np.cos(theta), -1j * np.sin(theta)
    for j in range(k):
        psi = psi.reshape(-1, 2, 2 ** j)
        a0 = psi[:, 0, :].copy()
        psi[:, 0, :] = c * a0 + s * psi[:, 1, :]
        psi[:, 1, :] = s * a0 + c * psi[:, 1, :]
        psi = psi.reshape(-1)
    return psi


def v13():
    print("V13 quantum-inspired: classical statevector cost of ONE group proposal (Trotter r=40, t=10)")
    rng = np.random.default_rng(0)
    for k in (8, 12, 16, 20, 22):
        J, h = qmc.sk_instance(k, 1)
        # energies by bit tricks (k<=22 fine)
        idx = np.arange(2 ** k)
        s = 1 - 2 * ((idx[:, None] >> np.arange(k)) & 1).astype(np.int8)
        Ed = -0.5 * np.einsum("ai,ij,aj->a", s, J, s, optimize=True) - s @ h
        a = np.sqrt(k) / Ed.std()
        gm, t, r = 0.45, 10.0, 40
        dt = t / r
        ph = np.exp(-1j * (1 - gm) * a * Ed * dt)
        t0 = time.perf_counter()
        psi = np.zeros(2 ** k, complex)
        psi[rng.integers(2 ** k)] = 1.0
        for _ in range(r):
            psi = apply_rx_all(psi, k, gm * dt)
            psi *= ph
        p = np.abs(psi) ** 2
        rng.choice(2 ** k, p=p / p.sum())
        el = time.perf_counter() - t0
        print(f"  k={k:2d} qubits: {el*1e3:9.2f} ms per proposal (1 core, numpy, {r*k} RX + {r} diagonal layers)")
        del s


# ------------------------------------------------------------------ V14 lifted
def lifted_P(Q, E, beta, O):
    pi = qmc.boltzmann(E, beta)
    d = len(E)
    A = np.minimum(1.0, pi[None, :] / pi[:, None])
    up = (O[None, :] > O[:, None]).astype(float)
    dn = (O[None, :] < O[:, None]).astype(float)
    P = np.zeros((2 * d, 2 * d))
    for sgn, M in ((0, up), (1, dn)):
        T = Q * A * M
        np.fill_diagonal(T, 0)
        rest = 1 - T.sum(1)
        P[sgn * d:(sgn + 1) * d, sgn * d:(sgn + 1) * d] = T
        o = (1 - sgn) * d
        P[np.arange(sgn * d, (sgn + 1) * d), o + np.arange(d)] += rest  # flip direction on any non-move
    return P, np.concatenate([pi, pi]) / 2


def tmix(P, pi_full, d, eps=0.01, maxk=20000):
    """steps until max over starts of TV(marginal on s, pi) < eps (lifted chains: marginalise)."""
    D = len(pi_full)
    M = np.eye(D)
    marg = lambda X: X[:, :d] + X[:, d:] if D == 2 * d else X
    pis = pi_full[:d] * 2 if D == 2 * d else pi_full
    k = 1
    Pk = P.copy()
    while k < maxk:
        tvmax = 0.5 * np.abs(marg(Pk) - pis[None, :]).sum(1).max()
        if tvmax < eps:
            return k
        Pk = Pk @ P
        k += 1
    return np.inf


def v14():
    print("V14 lifted non-reversible QeMCMC (direction = sign of dE), SK n=6")
    n = 6
    J, h, E = sk(n, 11)
    Q = qmc.quantum_Q(E, GAM, TS)
    M = qmc.spins(n).sum(1).astype(float) + 1e-3 * np.arange(2 ** n)  # magnetisation, tie-broken
    for beta in (1.0, 0.3):
        pi = qmc.boltzmann(E, beta)
        P = qmc.mh_matrix(Q, E, beta)
        for name, O in (("energy", E), ("magnetisation", M)):
            PL, piL = lifted_P(Q, E, beta, O)
            e = stat_err(PL, piL)
            print(f"  beta={beta} lifted on {name:13s}: err={e:.1e}  t_mix(TV<.01)={tmix(PL, piL, 2**n)} "
                  f"vs reversible QeMCMC t_mix={tmix(P, pi, 2**n)}")
        Pl = qmc.mh_matrix(qmc.local_Q(n), E, beta)
        PLl, piLl = lifted_P(qmc.local_Q(n), E, beta, M)
        print(f"  beta={beta} classical: local t_mix={tmix(Pl, pi, 2**n)}, lifted-local(magnetisation) t_mix={tmix(PLl, piLl, 2**n)}")


# ------------------------------------------------------------------ V15 adiabatic dressing
def v15():
    print("V15 adiabatic-dressed (ramp) proposals, SK n=8 beta=1 and 3")
    n = 8
    J, h, E = sk(n, 21)
    a = qmc.alpha_from_energy(E)
    Hm = qmc.mixer(n)
    D = np.diag(a * E)
    rng = np.random.default_rng(2)
    gfs = rng.uniform(0.25, 0.6, 8)
    ths = rng.uniform(2, 20, 8)
    Tr, K = 10.0, 20
    cache = {}

    def Ug(gm, dt):
        key = (round(gm, 10), round(dt, 10))
        if key not in cache:
            cache[key] = U_of((1 - gm) * D + gm * Hm, dt)
        return cache[key]

    Uq, Up, U1 = [], [], []
    for gf, th in zip(gfs, ths):
        ramp = [gf * (k + 0.5) / K for k in range(K)]
        Uup = np.eye(2 ** n, dtype=complex)
        for gm in ramp:
            Uup = Ug(gm, Tr / K) @ Uup
        Udn = np.eye(2 ** n, dtype=complex)
        for gm in ramp[::-1]:
            Udn = Ug(gm, Tr / K) @ Udn
        Uh = U_of((1 - gf) * D + gf * Hm, th)
        Uq.append(Uh)
        Up.append(Udn @ Uh @ Uup)
        U1.append(Uh @ Uup)
    for beta in (1.0, 3.0):
        pi = qmc.boltzmann(E, beta)
        for name, Us in (("quench (P1)", Uq), ("palindromic ramp up-hold-down", Up), ("one-way ramp up-hold", U1)):
            Q = Q_from_unitaries(Us)
            P = qmc.mh_matrix(Q, E, beta)
            e = stat_err(P, pi)
            gtxt = f"gap={qmc.spectral_gap(P, pi):.3e}" if e < 1e-10 else f"TV={tv(stationary(P), pi):.2e}"
            print(f"  beta={beta} {name:32s} asym={asym(Q):.1e} err={e:.1e} {gtxt} acc={qmc.acceptance(Q,E,beta):.3f}")
        print(f"  beta={beta} local gap={qmc.gap(qmc.local_Q(n), E, beta):.3e}")


# ------------------------------------------------------------------ V16 delayed acceptance
def v16():
    print("V16 delayed acceptance (surrogate screen, then expensive E) with quantum proposal, SK n=8 beta=1")
    n, beta = 8, 1.0
    J, h, E = sk(n, 21)
    pi = qmc.boltzmann(E, beta)
    g, t = qmc.draw_params(7, 20)
    rng = np.random.default_rng(4)
    Q = qmc.quantum_Q(E, g, t)
    P0 = qmc.mh_matrix(Q, E, beta)
    for s in (0.1, 0.5, 1.0):
        Es = E + s * E.std() * rng.normal(size=E.size)
        ps = qmc.boltzmann(Es, beta)
        a1 = np.minimum(1, ps[None, :] / ps[:, None])
        a2 = np.minimum(1, (pi[None, :] * ps[:, None]) / (pi[:, None] * ps[None, :]))
        P = mh_custom(Q, a1 * a2)
        off = Q.copy()
        np.fill_diagonal(off, 0)
        frac = float((pi[:, None] * off * a1).sum() / (pi[:, None] * off).sum())
        print(f"  surrogate noise {s} sd: err={stat_err(P, pi):.1e} expensive evals per step={frac:.3f} "
              f"gap ratio DA/plain={qmc.spectral_gap(P, pi)/qmc.spectral_gap(P0, pi):.3f}")


# ------------------------------------------------------------------ V18 partial readout
def v18():
    print("V18 partial readout (measure qubits {0,1,2} only, keep rest = s), SK n=6 beta=1")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    Q = qmc.quantum_Q(E, GAM, TS)
    d = 2 ** n
    mS = 0b000111
    Qp = np.zeros((d, d))
    for a in range(d):
        for c in range(d):
            b = (a & ~mS) | (c & mS)
            Qp[a, b] += Q[a, c]
    Qp = 0.5 * Qp + 0.5 * qmc.local_Q(n)  # mixed with local moves so all spins can change (irreducible)
    report("partial readout (+50% local), plain Metropolis", qmc.mh_matrix(Qp, E, beta), pi, f"asym={asym(Qp):.1e}")
    report("partial readout (+50% local), exact Hastings (needs marginals)", qmc.mh_matrix(Qp, E, beta, hastings=True), pi)


# ------------------------------------------------------------------ V19 energy window
def v19():
    print("V19 energy-window filter on proposals, SK n=8 beta=1, window |dE|<=w")
    n, beta = 8, 1.0
    J, h, E = sk(n, 21)
    pi = qmc.boltzmann(E, beta)
    g, t = qmc.draw_params(7, 20)
    Q = qmc.quantum_Q(E, g, t)
    dE = np.abs(E[None, :] - E[:, None])
    g0 = qmc.gap(Q, E, beta)
    for w in (0.5, 1.0, 2.0):
        W = (dE <= w * E.std()).astype(float)
        Qa = Q * W
        Pa = qmc.mh_matrix(Qa.copy(), E, beta)
        report(f"w={w} sd: out-of-window -> reject (stay)", Pa, pi, f"gap/plain={qmc.spectral_gap(Pa, pi)/g0:.3f}")
        Qr = Qa / Qa.sum(1, keepdims=True)
        report(f"w={w} sd: resample until in window (post-select)", qmc.mh_matrix(Qr, E, beta), pi)


# ------------------------------------------------------------------ V21 block flips
def v21():
    print("V21 quantum proposal over fixed block (super-spin) flips, SK n=6 beta=1, blocks {01}{23}{45}")
    n, beta = 6, 1.0
    J, h, E = sk(n, 11)
    pi = qmc.boltzmann(E, beta)
    blocks = [0b000011, 0b001100, 0b110000]
    d = 2 ** n
    Q = np.zeros((d, d))
    for s in range(d):
        masks = [sum(blocks[i] for i in range(3) if (f >> i) & 1) for f in range(8)]
        Hf = np.array([E[s ^ m] for m in masks])
        Qf = qmc.quantum_Q(Hf, GAM, TS)
        for f in range(8):
            Q[s, s ^ masks[f]] += Qf[0, f]
    P = qmc.mh_matrix(Q, E, beta)
    report("block-flip quantum move (3 qubits for 6 spins)", P, pi, f"asym={asym(Q):.1e}")
    Pmix = qmc.mh_matrix(0.5 * Q + 0.5 * qmc.local_Q(n), E, beta)
    print(f"  gaps: block alone={gap_any(P):.4f} (not ergodic alone if 0), block+local 50/50={qmc.spectral_gap(Pmix, pi):.4f}, "
          f"full quantum={qmc.gap(qmc.quantum_Q(E, GAM, TS), E, beta):.4f}, local={qmc.gap(qmc.local_Q(n), E, beta):.4f}")


# ------------------------------------------------------------------ V22 XY mixer fixed magnetisation
def v22():
    print("V22 XY (Kawasaki-like) mixer, fixed weight 4 of n=8 (70 states), SK couplings, beta=1 and 3")
    n = 8
    J, h, E = sk(n, 21)
    d = 2 ** n
    w = np.array([bin(a).count("1") for a in range(d)])
    sec = np.where(w == 4)[0]
    Hring = np.zeros((d, d))
    Hall = np.zeros((d, d))
    for a in range(d):
        for i in range(n):
            for j in range(i + 1, n):
                if ((a >> i) & 1) != ((a >> j) & 1):
                    Hall[a, a ^ (1 << i) ^ (1 << j)] += 1.0
                    if j == i + 1 or (i == 0 and j == n - 1):
                        Hring[a, a ^ (1 << i) ^ (1 << j)] += 1.0
    g, t = qmc.draw_params(7, 12)
    Es = E[sec]
    a = np.sqrt(n) / Es.std()
    Kq = np.zeros((len(sec), len(sec)))
    for ii, ai in enumerate(sec):
        for jj, aj in enumerate(sec):
            if bin(ai ^ aj).count("1") == 2:
                Kq[ii, jj] = 1.0
    Kq /= Kq.sum(1, keepdims=True).max()
    Kq = fill_diag(Kq)
    for beta in (1.0, 3.0):
        pi = qmc.boltzmann(Es, beta)
        for name, Hm in (("XY ring", Hring), ("XY all-to-all", Hall)):
            Q = qmc.quantum_Q(E, g, t, alpha=a, Hm=Hm)
            Qs = Q[np.ix_(sec, sec)]
            leak = 1 - Qs.sum(1).min()
            P = qmc.mh_matrix(Qs.copy(), Es, beta)
            report(f"beta={beta} {name}", P, pi, f"leak={leak:.1e} gap={qmc.spectral_gap(P, pi):.3e}")
        print(f"   beta={beta} Kawasaki pair-exchange gap={qmc.gap(Kq, Es, beta):.3e}")


# ------------------------------------------------------------------ V24 mask donation
def v24():
    print("V24 latency-hiding mask donation: move s -> s XOR m, m from a quantum run on a reference r (SK n=8)")
    n = 8
    J, h, E = sk(n, 21)
    g, t = qmc.draw_params(7, 20)
    Q = qmc.quantum_Q(E, g, t)
    d = 2 ** n
    idx = np.arange(d)
    for beta in (1.0, 0.3):
        pi = qmc.boltzmann(E, beta)
        out = []
        for name, rho in (("reference r ~ pi (independent replica)", pi), ("reference r uniform", np.full(d, 1 / d))):
            M = np.zeros(d)
            for r in range(d):
                M += rho[r] * Q[r, r ^ idx]
            Qm = M[idx[:, None] ^ idx[None, :]]
            P = qmc.mh_matrix(Qm, E, beta)
            out.append(f"{name}: err={stat_err(P, pi):.1e} gap={qmc.spectral_gap(P, pi):.3e}")
        Mde = np.zeros(d)  # classical competitor: mask = XOR of two independent equilibrium samples
        for r in range(d):
            Mde += pi[r] * pi[r ^ idx]
        Pde = qmc.mh_matrix(Mde[idx[:, None] ^ idx[None, :]], E, beta)
        out.append(f"CLASSICAL differential-evolution mask r1 XOR r2 (r1,r2 ~ pi): err={stat_err(Pde, pi):.1e} "
                   f"gap={qmc.spectral_gap(Pde, pi):.3e}")
        print(f"  beta={beta}: quantum gap={qmc.gap(Q, E, beta):.3e} local={qmc.gap(qmc.local_Q(n), E, beta):.3e} "
              f"uniform={qmc.gap(qmc.uniform_Q(n), E, beta):.3e}")
        for o in out:
            print("   " + o)


# ------------------------------------------------------------------ V25 quantum Houdayer
def v25():
    print("V25 quantum Houdayer move on replica-difference clusters (ring n=5, replicas beta 1.0 and 0.5)")
    n = 5
    J, _ = qmc.ea_instance(1, n, 3)
    rng = np.random.default_rng(3)
    h = 0.3 * rng.normal(size=n)
    E = qmc.ising_energies(J, h)
    bA, bB = 1.0, 0.5
    d = 2 ** n
    piA, piB = qmc.boltzmann(E, bA), qmc.boltzmann(E, bB)
    pij = np.outer(piA, piB).reshape(-1)  # index A*d + B
    edges = [(i, (i + 1) % n) for i in range(n)]
    P = np.zeros((d * d, d * d))
    full = d - 1
    for A in range(d):
        for B in range(d):
            D = A ^ B
            sites = [i for i in range(n) if (D >> i) & 1]
            if not sites:
                continue
            comps, seen = [], set()
            for s0 in sites:
                if s0 in seen:
                    continue
                stack, comp = [s0], []
                seen.add(s0)
                while stack:
                    u = stack.pop()
                    comp.append(u)
                    for (x, y) in edges:
                        for v in ((y,) if x == u else (x,) if y == u else ()):
                            if v in sites and v not in seen:
                                seen.add(v)
                                stack.append(v)
                comps.append(sorted(comp))
            for C in comps:
                k = len(C)
                cm = sum(1 << i for i in C)
                xs = []
                for x in range(2 ** k):
                    xm = sum(((x >> j) & 1) << C[j] for j in range(k))
                    Ap = (A & ~cm) | xm
                    Bp = (B & ~cm) | (~xm & cm)
                    xs.append((Ap, Bp))
                Hx = np.array([E[Ap] + E[Bp] for Ap, Bp in xs])
                x0 = sum(((A >> C[j]) & 1) << j for j in range(k))
                Qc = qmc.quantum_Q(Hx, GAM[:6], TS[:6])
                src = A * d + B
                for x, (Ap, Bp) in enumerate(xs):
                    dst = Ap * d + Bp
                    if dst == src:
                        continue
                    acc = min(1.0, pij[dst] / pij[src])
                    P[src, dst] += Qc[x0, x] * acc / len(comps)
    P = fill_diag(P)
    report("quantum Houdayer (difference set invariant), joint target piA*piB", P, pij)


SECTIONS = dict(v01=v01, v02=v02, v03=v03, v04=v04, v05=v05, v06=v06, v07=v07, v08=v08, v09=v09, v10=v10,
                v11=v11, v12=v12, v13=v13, v14=v14, v15=v15, v16=v16, v18=v18, v19=v19, v21=v21, v22=v22,
                v24=v24, v25=v25)

if __name__ == "__main__":
    which = sys.argv[1:] or list(SECTIONS)
    for k in which:
        t0 = time.perf_counter()
        SECTIONS[k]()
        print(f"  [{k} done in {time.perf_counter()-t0:.1f} s]\n", flush=True)
