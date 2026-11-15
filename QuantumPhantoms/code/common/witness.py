"""Witnesses and their statistics, one implementation for every circuit family.

  dfe_ghz          direct fidelity estimation over random GHZ stabilizers; GME iff F - 0.5 > 2 sigma
  ghz2             <X^N> + mean adjacent <Z Z> > 1 (the 1.96 on ibm_marrakesh is this witness, bound 1, not CHSH)
  trex_lite        divide a parity by prod(1 - p01 - p10) over its qubits, propagate sigma
  echo_fidelity    return probability to the initial bitstring after U^t U^-t
  pair_negativity  2-qubit tomography on pre-registered edges, Bonferroni-corrected
  alive            sigma = sqrt(repeat spread^2 + 1/shots); k = 2 headline, k = 3 reported
All bootstrap errors resample shots with rng(seed, "DS-bootstrap").
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from common.runio import rng

BOOT = 1000
I2 = np.eye(2, dtype=complex)
PAULI = {"I": I2, "X": np.array([[0, 1], [1, 0]], dtype=complex),
         "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1.0, -1.0]).astype(complex)}


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """<sigma sigma> from 0/1 outcomes: mean of (-1)^(a xor b)."""
    a, b = a.astype(np.int64), b.astype(np.int64)
    return float(np.mean(1 - 2 * ((a ^ b) & 1))) if a.size else float("nan")


def boot_se(vals: np.ndarray, stat, seed_hex: str, label: str = "DS-bootstrap", n: int = BOOT) -> float:
    if vals.shape[0] < 2:
        return float("nan")
    g = rng(seed_hex, label)
    idx = g.integers(0, vals.shape[0], size=(n, vals.shape[0]))
    return float(np.std([stat(vals[i]) for i in idx], ddof=1))


def chsh_S(x, y, a, b) -> tuple[float, float, int]:
    """S = E00 + E01 + E10 - E11 and its standard error (binomial per setting pair)."""
    s, var = 0.0, 0.0
    for xi, yi in itertools.product((0, 1), (0, 1)):
        m = (x == xi) & (y == yi)
        n = int(m.sum())
        if n == 0:
            return float("nan"), float("nan"), 0
        e = corr(a[m], b[m])
        s += (-1 if (xi, yi) == (1, 1) else 1) * e
        var += (1 - e * e) / n
    return float(s), float(np.sqrt(var)), int(len(x))


# ---------------------------------------------------------------- 2-qubit linear-inversion tomography
def _pauli2(p: str, q: str) -> np.ndarray:
    return np.kron(PAULI[p], PAULI[q])




def tomo_pair(shots: dict[tuple[str, str], np.ndarray], i_idx: int, j_idx: int, i_in_A: bool) -> np.ndarray:
    """rho_ij from the 9 bipartite settings. shots[(bA, bB)] has columns = qubit index; site i is in the
    sublattice whose basis is bA if i_in_A else bB (and j in the other)."""
    exp = {}
    for (bA, bB), bits in shots.items():
        bi, bj = (bA, bB) if i_in_A else (bB, bA)
        zi = 1 - 2 * bits[:, i_idx].astype(float)
        zj = 1 - 2 * bits[:, j_idx].astype(float)
        exp[(bi, bj)] = float(np.mean(zi * zj))
        exp.setdefault((bi, "I"), float(np.mean(zi)))
        exp.setdefault(("I", bj), float(np.mean(zj)))
    rho = np.eye(4, dtype=complex) / 4
    for (p, q), v in exp.items():
        rho += v * _pauli2(p, q) / 4
    return rho


def nearest_physical(rho: np.ndarray) -> np.ndarray:
    """Smolin-Gambetta-Smith fast maximum-likelihood projection of a Hermitian trace-1 matrix to a state."""
    rho = (rho + rho.conj().T) / 2
    w, v = np.linalg.eigh(rho)
    order = np.argsort(w)[::-1]
    w, v = w[order], v[:, order]
    lam, acc, d = w.copy(), 0.0, len(w)
    i = d
    while i > 0 and lam[i - 1] + acc / i < 0:
        acc += lam[i - 1]
        lam[i - 1] = 0
        i -= 1
    lam[:i] += acc / i
    return (v * lam) @ v.conj().T


def negativity(rho: np.ndarray) -> float:
    r = rho.reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)  # partial transpose on qubit 2
    ev = np.linalg.eigvalsh((r + r.conj().T) / 2)
    return float(-ev[ev < 0].sum())


def vn_entropy(rho: np.ndarray) -> float:
    ev = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    ev = ev[ev > 1e-12]
    return float(-(ev * np.log2(ev)).sum())


def mutual_information(rho: np.ndarray) -> float:
    r = rho.reshape(2, 2, 2, 2)
    ra, rb = np.trace(r, axis1=1, axis2=3), np.trace(r, axis1=0, axis2=2)
    return float(vn_entropy(ra) + vn_entropy(rb) - vn_entropy(rho))


M_DFE = 40
K_HEADLINE, K_REPORTED = 2, 3


# ---------------------------------------------------------------------------------------------- bits
def bits_of(result, i: int) -> np.ndarray:
    """(shots, n_clbits) uint8 array; column k = classical bit k."""
    mem = result.get_memory(i)
    return np.array([[int(ch) for ch in s.replace(" ", "")[::-1]] for s in mem], dtype=np.uint8)


def parity_expect(bits: np.ndarray, cols: list[int]) -> tuple[float, float]:
    """<prod (-1)^b> over the given columns, with its shot standard error."""
    if not cols:
        return 1.0, 0.0
    v = 1 - 2 * (bits[:, cols].sum(1) & 1).astype(float)
    return float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else float("nan")


# ---------------------------------------------------------------------------------------------- GHZ
def ghz_stabilizers(n: int, m: int, g: np.random.Generator) -> list[dict]:
    """m elements drawn uniformly from the n-qubit GHZ stabilizer group.
    Z-type: Z_S with |S| even. X-type: X^n Z_S = (-1)^{|S|/2} Y_S X_rest with |S| even."""
    out = []
    for _ in range(m):
        s = g.integers(0, 2, n)
        s[-1] = s[:-1].sum() & 1                                  # |S| even
        if g.integers(0, 2) == 0:
            lab = ["Z" if b else "I" for b in s]
            sign = 1
        else:
            lab = ["Y" if b else "X" for b in s]
            sign = -1 if (int(s.sum()) // 2) % 2 else 1
        out.append({"paulis": "".join(lab), "sign": sign})
    return out


def stabilizer_value(bits: np.ndarray, st: dict, cols: list[int]) -> tuple[float, float]:
    """Expectation of a stabilizer measured with per-qubit basis = its Pauli (I columns skipped)."""
    use = [c for c, p in zip(cols, st["paulis"]) if p != "I"]
    v, se = parity_expect(bits, use)
    return st["sign"] * v, se


def dfe_ghz(values: list[float]) -> dict:
    """F = mean <S_k>; sigma from the spread of the m sampled stabilizers (includes the shot noise)."""
    v = np.asarray(values, float)
    m = len(v)
    F = float(v.mean())
    sig = float(v.std(ddof=1) / math.sqrt(m)) if m > 1 else float("nan")
    return {"F": F, "sigma": sig, "m": m, "gme": bool(F - 0.5 > K_HEADLINE * sig),
            "gme_k3": bool(F - 0.5 > K_REPORTED * sig)}


def ghz2(xbits: np.ndarray, zbits: np.ndarray, cols: list[int], edges: list[tuple[int, int]]) -> dict:
    """<X^N> + mean adjacent <Z_i Z_j> (edges in column indices). Bound 1 (separable)."""
    xx, sx = parity_expect(xbits, cols)
    zz = [parity_expect(zbits, [a, b]) for a, b in edges]
    zm = float(np.mean([z for z, _ in zz])) if zz else 1.0
    zs = float(math.sqrt(sum(s * s for _, s in zz)) / len(zz)) if zz else 0.0
    return {"X": xx, "ZZ": zm, "value": xx + zm, "sigma": math.sqrt(sx * sx + zs * zs)}


# ---------------------------------------------------------------------------------------------- mitigation
def trex_lite(value: float, sigma: float, qubits: list[int], p01: dict, p10: dict) -> tuple[float, float]:
    """Readout-twirled parity correction: <P>_corrected = <P>_raw / prod_q (1 - p01_q - p10_q)."""
    f = float(np.prod([1 - p01[q] - p10[q] for q in qubits])) if qubits else 1.0
    f = max(f, 1e-6)
    return value / f, sigma / f


# ---------------------------------------------------------------------------------------------- QCA
def echo_fidelity(bits: np.ndarray, init: np.ndarray) -> tuple[float, float]:
    """Fraction of shots returning to the initial bitstring (U^t U^-t), with its binomial standard error."""
    hit = (bits == init[None, :]).all(1).astype(float)
    p = float(hit.mean())
    return p, float(math.sqrt(max(p * (1 - p), 1.0 / len(hit)) / len(hit)))


def random_band(n_sites: int, shots: int) -> float:
    """Echo fidelity of a fully scrambled register: 2^-n (+ the shot floor 1/shots)."""
    return 2.0 ** (-n_sites)


def pair_negativity(shots9: dict[tuple[str, str], np.ndarray], edges: list[tuple[int, int]], A: set[int],
                    col: dict[int, int], seed_hex: str, alpha: float = 0.05, boot: int = 200) -> list[dict]:
    """Negativity on pre-registered edges from the 9 bipartite settings (sublattice A measured in bA, B in bB).
    One-sided normal p-value N / sigma, Bonferroni over the registered edges."""
    out = []
    n_e = max(len(edges), 1)
    keys = sorted(shots9)
    for i, j in edges:
        ii, jj = col[i], col[j]

        def neg_of(sub: dict) -> float:
            rho = nearest_physical(tomo_pair(sub, ii, jj, i in A))
            return negativity(rho)

        N = neg_of(shots9)
        n = min(len(shots9[k]) for k in keys)
        stacked = np.stack([shots9[k][:n] for k in keys], 1)            # (shots, 9, ncols)

        def stat(sample):
            return neg_of({k: sample[:, t] for t, k in enumerate(keys)})

        sig = boot_se(stacked, stat, seed_hex, "DS-bootstrap-negativity", boot)
        z = N / sig if sig and sig > 0 else (float("inf") if N > 0 else 0.0)
        p = 0.5 * math.erfc(z / math.sqrt(2))
        out.append({"i": int(i), "j": int(j), "N": float(N), "sigma": float(sig), "p": float(p),
                    "p_bonf": float(min(1.0, p * n_e)), "passed": bool(p * n_e < alpha)})
    return out


# ---------------------------------------------------------------------------------------------- significance
def alive(values: list[float] | float, shots: int, k: float = K_HEADLINE, threshold: float = 0.0,
          sigma_extra: float = 0.0) -> dict:
    """value = mean over repeats; sigma = sqrt(repeat spread^2 + 1/shots + sigma_extra^2); alive iff
    value - threshold > k sigma. Reports the k = 3 verdict too."""
    v = np.atleast_1d(np.asarray(values, float))
    spread = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    sig = math.sqrt(spread ** 2 + 1.0 / shots + sigma_extra ** 2)
    val = float(v.mean())
    return {"value": val, "sigma": sig, "k": k, "threshold": threshold, "repeats": int(len(v)),
            "alive": bool(val - threshold > k * sig), "alive_k3": bool(val - threshold > K_REPORTED * sig)}
