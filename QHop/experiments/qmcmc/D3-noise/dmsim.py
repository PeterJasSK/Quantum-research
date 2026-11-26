"""D3 exact density-matrix simulator for noisy QeMCMC proposal circuits (logical level, all-to-all).

Q_noisy[a, b] = <b| E(|a><a|) |b> is computed EXACTLY for every basis input a at once: the batch of
density matrices rho_a (shape B x d x d) is propagated gate by gate with the noise channels applied
as exact linear maps (no shots, no trajectories).

Conventions as qmc.py: bit i of the index = spin i, bit 0 -> s=+1 (Z=+1).
E(s) = -sum_{i<j} J_ij s_i s_j - sum_i h_i s_i;  H = (1-g) alpha E + g sum_i X_i, alpha = qmc.alpha_from_energy.

Circuit = second-order (Strang) Trotter, r steps (r odd), built as an explicit list of gate units that is a
literal palindrome (checked by is_palindrome).  Gate units: ('zz', i, j, theta) = exp(-i theta/2 Z_i Z_j),
('z', i, phi) = exp(-i phi/2 Z_i) (virtual, noiseless), ('x', i, theta) = exp(-i theta/2 X_i).

Noise model (dict), attached to gate units:
  dep2  : 2q depolarizing parameter lambda on the pair after each zz      rho -> (1-l) rho + l I/4 (x) Tr_ij rho
  dep1  : 1q depolarizing lambda after each x gate
  deph2 / deph1 : Z-dephasing probability p on each qubit of a zz / x gate  rho -> (1-p) rho + p Z rho Z
  ad2 / ad1     : amplitude damping gamma on each qubit of a zz / x gate (T1-like, |1> -> |0>)
  pump_mask     : int bitmask, qubits on which amplitude damping is replaced by its X-conjugate (|0> -> |1>)
  twirl_ad      : True -> replace each AD channel by its exact Pauli twirl (Pauli channel px=py=g/4)
placement: 'after' (channel after its gate, the Aer/Qiskit convention) or 'split' (half-strength channel
before and after the gate: discrete model of noise acting continuously during the gate).
"""
import sys
import numpy as np

sys.path.insert(0, "/home/peter/PycharmProjects/Quantum-research/QHop/experiments/qmcmc/common")
import qmc  # noqa: E402


# ----------------------------------------------------------------------------------------- circuit

def round_robin(n):
    """Edge rounds (perfect matchings) of K_n, circle method; each round = disjoint pairs."""
    m = n if n % 2 == 0 else n + 1
    players = list(range(m))
    rounds = []
    for _ in range(m - 1):
        rd = []
        for k in range(m // 2):
            a, b = players[k], players[m - 1 - k]
            if a < n and b < n:
                rd.append((min(a, b), max(a, b)))
        rounds.append(rd)
        players = [players[0]] + [players[-1]] + players[1:-1]
    return rounds


def edge_order(J):
    """Interaction edges ordered by matching rounds (dense: round robin; sparse: greedy colouring)."""
    n = len(J)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if J[i, j] != 0]
    if len(edges) == n * (n - 1) // 2:
        return [e for rd in round_robin(n) for e in rd]
    rounds = []
    for e in edges:
        for rd in rounds:
            if all(e[0] not in f and e[1] not in f for f in rd):
                rd.append(e)
                break
        else:
            rounds.append([e])
    return [e for rd in rounds for e in rd]


def trotter_units(J, h, gamma, t, r=None, order="second", alpha=None):
    """Gate-unit list of the Trotterised exp(-iHt). order='second' -> palindromic Strang splitting,
    adjacent half layers merged; layer orders alternate so the list is a literal palindrome (r odd).
    order='first' -> D X D X ... (not palindromic), the control that breaks U^T=U."""
    n = len(h)
    E = qmc.ising_energies(J, h)
    a = qmc.alpha_from_energy(E) if alpha is None else alpha
    if r is None:
        r = 2 * int(round(t)) + 1
    if order == "second" and r % 2 == 0:
        r += 1
    dt = t / r
    edges = edge_order(J)
    fields = [i for i in range(n) if h[i] != 0]

    def diag(w, rev):
        u = [("zz", i, j, 2 * w * dt * (1 - gamma) * a * (-J[i, j])) for (i, j) in edges]
        u += [("z", i, 2 * w * dt * (1 - gamma) * a * (-h[i])) for i in fields]
        return u[::-1] if rev else u

    def xl(rev):
        u = [("x", i, 2 * gamma * dt) for i in range(n)]
        return u[::-1] if rev else u

    units = []
    if order == "first":
        for _ in range(r):
            units += diag(1.0, False) + xl(False)
        return units, dict(r=r, dt=dt, alpha=a)
    # second order: D(1/2) X D(1) X ... X D(1/2); layer k (k=0..r) diag, order f if k even else rev
    for k in range(r + 1):
        w = 0.5 if k in (0, r) else 1.0
        units += diag(w, rev=(k % 2 == 1))
        if k < r:
            units += xl(rev=(k % 2 == 1))
    return units, dict(r=r, dt=dt, alpha=a)


def is_palindrome(units):
    """Literal palindrome check, modulo reordering inside runs of 'x' units (disjoint qubits, they
    commute exactly even with their 1q noise attached)."""
    key, run = [], []
    for u in units:
        k = (u[0],) + tuple(int(q) for q in u[1:-1]) + (round(float(u[-1]), 12),)
        if u[0] == "x":
            run.append(k)
            continue
        if run:
            key.append(tuple(sorted(run)))
            run = []
        key.append(k)
    if run:
        key.append(tuple(sorted(run)))
    return key == key[::-1]


def gate_counts(units):
    n2 = sum(1 for u in units if u[0] == "zz")
    n1 = sum(1 for u in units if u[0] == "x")
    return n2, n1


# ----------------------------------------------------------------------------------------- ideal unitary

def ideal_unitary(units, n):
    d = 2 ** n
    idx = np.arange(d)
    z = 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)
    U = np.eye(d, dtype=complex)
    for u in units:
        if u[0] == "zz":
            _, i, j, th = u
            U = (np.exp(-0.5j * th * z[:, i] * z[:, j]))[:, None] * U
        elif u[0] == "z":
            _, i, ph = u
            U = (np.exp(-0.5j * ph * z[:, i]))[:, None] * U
        else:
            _, i, th = u
            c, s = np.cos(th / 2), -1j * np.sin(th / 2)
            U = c * U + s * U[idx ^ (1 << i)]
    return U


# ----------------------------------------------------------------------------------------- DM batch

class DMBatch:
    def __init__(self, n, inputs, dtype=np.complex128):
        self.n = n
        d = 2 ** n
        B = len(inputs)
        R = np.zeros((B, d, d), dtype)
        R[np.arange(B), inputs, inputs] = 1.0
        self.R = R.reshape((B,) + (2,) * (2 * n))
        self.c = 1.0                                   # global scale (depolarizing bookkeeping)
        self.nd = 2 * n + 1

    def ax(self, q, col=False):
        return 1 + (self.n if col else 0) + (self.n - 1 - q)

    def S(self, spec):
        idx = [slice(None)] * self.nd
        for a_, v in spec.items():
            idx[a_] = v
        return tuple(idx)

    # unitaries ------------------------------------------------------------------------------
    def u1(self, q, u):
        R = self.R
        for col in (False, True):
            a_ = self.ax(q, col)
            m = np.conj(u) if col else u
            A = R[self.S({a_: 0})]
            Bv = R[self.S({a_: 1})]
            t0 = m[0, 0] * A + m[0, 1] * Bv
            Bv *= m[1, 1]
            Bv += m[1, 0] * A
            A[...] = t0

    def rx(self, q, th):
        c, s = np.cos(th / 2), -1j * np.sin(th / 2)
        self.u1(q, np.array([[c, s], [s, c]]))

    def rz(self, q, ph):
        ar, ac = self.ax(q), self.ax(q, True)
        self.R[self.S({ar: 0, ac: 1})] *= np.exp(-1j * ph)
        self.R[self.S({ar: 1, ac: 0})] *= np.exp(1j * ph)

    def rzz(self, i, j, th):
        ri, rj, ci, cj = self.ax(i), self.ax(j), self.ax(i, True), self.ax(j, True)
        for xi in (0, 1):
            for xj in (0, 1):
                for yi in (0, 1):
                    for yj in (0, 1):
                        zr = 1 if xi == xj else -1
                        zc = 1 if yi == yj else -1
                        if zr != zc:
                            self.R[self.S({ri: xi, rj: xj, ci: yi, cj: yj})] *= np.exp(-0.5j * th * (zr - zc))

    # channels -------------------------------------------------------------------------------
    def dep2(self, i, j, lam):
        if lam <= 0:
            return
        ri, rj, ci, cj = self.ax(i), self.ax(j), self.ax(i, True), self.ax(j, True)
        sl = [self.S({ri: x, rj: y, ci: x, cj: y}) for x in (0, 1) for y in (0, 1)]
        T = sum(self.R[s] for s in sl)
        k = lam / (4.0 * (1.0 - lam))
        for s in sl:
            self.R[s] += k * T
        self.c *= (1.0 - lam)

    def pauli1(self, q, px, py, pz):
        pI = 1.0 - px - py - pz
        ar, ac = self.ax(q), self.ax(q, True)
        R = self.R
        d0, d1 = R[self.S({ar: 0, ac: 0})], R[self.S({ar: 1, ac: 1})]
        o01, o10 = R[self.S({ar: 0, ac: 1})], R[self.S({ar: 1, ac: 0})]
        a, b = pI + pz, px + py
        t0 = a * d0 + b * d1
        d1 *= a
        d1 += b * d0
        d0[...] = t0
        a, b = pI - pz, px - py
        t0 = a * o01 + b * o10
        o10 *= a
        o10 += b * o01
        o01[...] = t0

    def dep1(self, q, lam):
        if lam > 0:
            self.pauli1(q, lam / 4, lam / 4, lam / 4)

    def deph(self, q, p):
        if p <= 0:
            return
        ar, ac = self.ax(q), self.ax(q, True)
        self.R[self.S({ar: 0, ac: 1})] *= (1 - 2 * p)
        self.R[self.S({ar: 1, ac: 0})] *= (1 - 2 * p)

    def ad(self, q, g, pump=False):
        if g <= 0:
            return
        ar, ac = self.ax(q), self.ax(q, True)
        lo, hi = (1, 0) if pump else (0, 1)           # population flows hi -> lo
        R = self.R
        Rl, Rh = R[self.S({ar: lo, ac: lo})], R[self.S({ar: hi, ac: hi})]
        Rl += g * Rh
        Rh *= (1 - g)
        sq = np.sqrt(1 - g)
        R[self.S({ar: 0, ac: 1})] *= sq
        R[self.S({ar: 1, ac: 0})] *= sq

    def probs(self):
        B = self.R.shape[0]
        d = 2 ** self.n
        R = self.R.reshape(B, d, d)
        return self.c * np.real(np.einsum("bii->bi", R))


def ad_twirl(g):
    s = np.sqrt(1 - g)
    return g / 4, g / 4, ((1 - s) / 2) ** 2


def _half(kind, v):
    if kind in ("dep", "ad"):
        return 1 - np.sqrt(1 - v)
    if kind == "deph":
        return 0.5 * (1 - np.sqrt(1 - 2 * v))
    raise ValueError(kind)


def apply_noise(sim, qubits, noise, two, frac):
    """frac = 1 (after) or 'half' (split)."""
    hf = frac == "half"
    g = (lambda kind, v: _half(kind, v) if hf else v)
    pm = noise.get("pump_mask", 0)
    if two:
        lam = noise.get("dep2", 0.0)
        if lam > 0:
            sim.dep2(qubits[0], qubits[1], g("dep", lam))
        p, gam = noise.get("deph2", 0.0), noise.get("ad2", 0.0)
    else:
        lam = noise.get("dep1", 0.0)
        if lam > 0:
            sim.dep1(qubits[0], g("dep", lam))
        p, gam = noise.get("deph1", 0.0), noise.get("ad1", 0.0)
    for q in qubits:
        if p > 0:
            sim.deph(q, g("deph", p))
        if gam > 0:
            gg = g("ad", gam)
            if noise.get("twirl_ad", False):
                sim.pauli1(q, *ad_twirl(gg))
            else:
                sim.ad(q, gg, pump=bool((pm >> q) & 1))


def run_units(sim, units, noise, placement="after"):
    frac = "half" if placement == "split" else 1
    noisy = any(v for k, v in noise.items() if k not in ("pump_mask", "twirl_ad"))
    for u in units:
        if u[0] == "z":
            sim.rz(u[1], u[2])
            continue
        two = u[0] == "zz"
        qs = (u[1], u[2]) if two else (u[1],)
        if noisy and placement == "split":
            apply_noise(sim, qs, noise, two, frac)
        if two:
            sim.rzz(u[1], u[2], u[3])
        else:
            sim.rx(u[1], u[2])
        if noisy:
            apply_noise(sim, qs, noise, two, frac)


def noisy_Q(units, n, noise, placement="after", dtype=np.complex128, chunk=None):
    d = 2 ** n
    chunk = d if chunk is None else chunk
    Q = np.zeros((d, d))
    for s0 in range(0, d, chunk):
        inp = np.arange(s0, min(d, s0 + chunk))
        sim = DMBatch(n, inp, dtype)
        run_units(sim, units, noise, placement)
        Q[inp] = sim.probs()
    return Q


def gauge(J, h, m):
    """Ising gauge transform by bitmask m: s_i -> -s_i on masked spins."""
    n = len(h)
    sg = 1 - 2 * ((m >> np.arange(n)) & 1)
    return J * np.outer(sg, sg), h * sg


def relabel(Qm, m):
    p = np.arange(len(Qm)) ^ m
    return Qm[np.ix_(p, p)]


# ----------------------------------------------------------------------------------------- classical maps

def readout_apply(Q, n, p01, p10):
    """Q -> Q M, M = kron of per-qubit [[1-p01, p01], [p10, 1-p10]] (row = true bit, col = reported)."""
    d = 2 ** n
    T = Q.reshape((d,) + (2,) * n)
    M = np.array([[1 - p01, p01], [p10, 1 - p10]])
    for q in range(n):
        a_ = 1 + (n - 1 - q)
        T = np.moveaxis(np.tensordot(T, M, axes=([a_], [0])), -1, a_)
    return T.reshape(d, d)


def prep_apply(Q, n, p01, p10):
    """Q -> M^T Q: classical random flip of the INPUT bits before preparation. Stochastic (a valid
    pre-flip) only for symmetric flips p01 == p10, the case used for the mirrored-readout fix."""
    return readout_apply(Q.T, n, p01, p10).T
