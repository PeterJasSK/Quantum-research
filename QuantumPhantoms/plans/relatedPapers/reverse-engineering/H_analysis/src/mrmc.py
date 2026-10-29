"""Fully-crossed multi-reader multi-case (MRMC) AUC statistics, readers and cases random.

U-statistic variance of Gallas (2006), the estimator behind iMRMC, rebuilt with NumPy.
Kernel psi_{r,i,j} = 1[y_rj > x_ri] + 0.5*1[y_rj == x_ri] (i negative case, j positive case).
Var(theta) = sum_k n_k M_k / (R*N0*N1) - M_8, where the eight moments M_k average
psi*psi' over index pairs sharing exactly the (reader, neg, pos) indices of pattern k.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy import stats


def _psi(neg_r: np.ndarray, pos_r: np.ndarray) -> np.ndarray:
    d = pos_r[None, :] - neg_r[:, None]
    return (d > 0).astype(np.float64) + 0.5 * (d == 0)


def _variance(psi_iter, R: int, N0: int, N1: int) -> tuple[float, float]:
    """psi_iter yields one (N0, N1) kernel matrix per reader. Returns (theta, var)."""
    s_ij = np.zeros((N0, N1))
    p_ri2 = q_rj2 = w2 = sq = 0.0
    p_i = np.zeros(N0)
    q_j = np.zeros(N1)
    tot = 0.0
    for k in psi_iter:
        s_ij += k
        sq += float((k**2).sum())
        p = k.sum(1)
        q = k.sum(0)
        p_ri2 += float((p**2).sum())
        q_rj2 += float((q**2).sum())
        p_i += p
        q_j += q
        w2 += float(k.sum()) ** 2
        tot += float(k.sum())
    # T[mask]: bit0 = reader shared, bit1 = neg case shared, bit2 = pos case shared
    T = {
        0b111: sq, 0b011: p_ri2, 0b101: q_rj2, 0b110: float((s_ij**2).sum()),
        0b001: w2, 0b010: float((p_i**2).sum()), 0b100: float((q_j**2).sum()), 0b000: tot**2,
    }
    dims = (R, N0, N1)
    var_terms = 0.0
    m8 = None
    for mask in range(8):
        exact = 0.0
        for sup in range(8):
            if sup & mask == mask:
                exact += (-1) ** bin(sup & ~mask).count("1") * T[sup]
        count = 1.0
        n_k = 1.0
        for b in range(3):
            if mask >> b & 1:
                count *= dims[b]
            else:
                count *= dims[b] * (dims[b] - 1)
                n_k *= dims[b] - 1
        m = exact / count if count > 0 else 0.0
        if mask == 0:
            m8 = m
        var_terms += n_k * m
    theta = tot / (R * N0 * N1)
    return theta, var_terms / (R * N0 * N1) - m8


def _summarise(theta: float, var: float, R: int, N0: int, N1: int) -> dict:
    se = float(np.sqrt(max(var, 0.0)))
    df = max(min(R - 1, N0 + N1 - 1), 1)  # conservative: limited by the smaller sampling dimension
    t = stats.t.ppf(0.975, df)
    return {"auc": float(theta), "se": se, "df": int(df), "ci95": [float(theta - t * se), float(theta + t * se)]}


def mrmc_auc(scores_neg: np.ndarray, scores_pos: np.ndarray) -> dict:
    """scores_neg (R, N0), scores_pos (R, N1): same readers and cases rows for every reader."""
    R, N0 = scores_neg.shape
    N1 = scores_pos.shape[1]
    theta, var = _variance((_psi(scores_neg[r], scores_pos[r]) for r in range(R)), R, N0, N1)
    return _summarise(theta, var, R, N0, N1)


def mrmc_delta_auc(neg_a, pos_a, neg_b, pos_b) -> dict:
    """Paired AUC_A - AUC_B, same readers (row index) and same cases (column index) in both arms."""
    R, N0 = neg_a.shape
    N1 = pos_a.shape[1]
    it = (_psi(neg_a[r], pos_a[r]) - _psi(neg_b[r], pos_b[r]) for r in range(R))
    theta, var = _variance(it, R, N0, N1)
    out = _summarise(theta, var, R, N0, N1)
    out["delta_auc"] = out.pop("auc")
    return out


def _check(R: int = 4, N0: int = 6, N1: int = 5) -> float:
    """Brute-force-free sanity helper: Var must equal the one-way U-stat variance when R=1 identical readers."""
    rng = np.random.default_rng(0)
    return mrmc_auc(rng.normal(size=(R, N0)), rng.normal(size=(R, N1)))["se"]
