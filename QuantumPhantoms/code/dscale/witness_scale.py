"""D-SCALE witnesses and significance (AC-6): one implementation for every family.

  dfe_ghz        direct fidelity estimation, F = (1/m) sum_k <S_k> over m = 40 stabilizers drawn uniformly from the
                 GHZ stabilizer group; GME iff F - 0.5 > 2 sigma (Q8; GHZ fidelity > 1/2 witnesses genuine
                 multipartite entanglement)
  ghz2           <X^N> + mean adjacent <Z Z> > 1 (the 1.96 on ibm_marrakesh is this witness, bound 1, not CHSH)
  trex_lite      divide a parity by prod(1 - p01 - p10) over its qubits, propagate sigma (no M3: not installed)
  echo_fidelity  return probability to the initial bitstring after U^t U^-t
  pair_negativity  2-qubit tomography on pre-registered edges (dscale.tomography), Bonferroni-corrected
  alive          sigma = sqrt(repeat spread^2 + 1/shots); k = 2 headline, k = 3 reported
"""
from __future__ import annotations

import math

import numpy as np

from dscale import tomography as W

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
            rho = W.nearest_physical(W.tomo_pair(sub, ii, jj, i in A))
            return W.negativity(rho)

        N = neg_of(shots9)
        n = min(len(shots9[k]) for k in keys)
        stacked = np.stack([shots9[k][:n] for k in keys], 1)            # (shots, 9, ncols)

        def stat(sample):
            return neg_of({k: sample[:, t] for t, k in enumerate(keys)})

        sig = W.boot_se(stacked, stat, seed_hex, "DS-bootstrap-negativity", boot)
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
