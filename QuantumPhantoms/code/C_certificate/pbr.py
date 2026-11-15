"""C-PBR: a finite-statistics verdict that does not assume independent rounds (plans/feature-QCAND-*.md).

Test factor. A round wins the CHSH game when the outcomes agree (settings a0b0, a0b1, a1b0) or differ (a1b1). With
uniform settings a local model wins a round with probability <= 3/4 whatever happened before, so
    R = 1 + lam (win),  1 - 3 lam (loss),  0 <= lam < 1/3
has expectation <= 1 under every local model, and the product T of R over the test rounds obeys P(T >= t) <= 1/t
(Markov on a supermartingale): p-value = min(1, 1 / T). lam is fixed on a training set (the first third of each
circuit's rounds: lam = (4 p_win - 3) / 3, the maximiser of the expected log R) and applied to the rest.

This is the prediction-based ratio restricted to the CHSH win function (2503.18949 uses the full optimisation
[verify]). Its proof needs the setting of each round to be random; here settings are fixed per circuit with equal
rounds per setting, so the p-value carries the certificate's scope (job-level, not device-independent).

no_signalling: per pair, the marginal of one qubit must not depend on the other qubit's setting. A small p-value
flags cross-talk or drift between the four setting circuits.
"""
from __future__ import annotations

import math

import numpy as np

LAM_MAX = 1 / 3 - 1e-6
P_STOP = 1e-6                 # section C's stop rule: p_value_local below this (and S_low > 2)
P_CROSS_TALK = 0.01


def wins(bits: np.ndarray) -> np.ndarray:
    """bits: (4 settings, rounds, 2) in the order of bell_map.CHSH_PAIRS -> (4, rounds) win flags."""
    same = bits[:, :, 0] == bits[:, :, 1]
    same[3] = ~same[3]
    return same


def p_value(bits: np.ndarray, shots: int) -> dict:
    """bits: (4, rounds, 2), pooled pair after pair with `shots` rounds each per setting. Training = the first third
    of every pair's rounds."""
    w = wins(bits)
    train = (np.arange(w.shape[1]) % shots) < shots // 3
    p_train = float(w[:, train].mean())
    lam = float(min(max((4 * p_train - 3) / 3, 0.0), LAM_MAX))
    test = w[:, ~train]
    n_win, n_loss = int(test.sum()), int(test.size - test.sum())
    log_t = n_win * math.log1p(lam) + n_loss * math.log1p(-3 * lam)
    log10_p = min(0.0, -log_t / math.log(10))
    return {"p_value_local": float(10.0 ** max(log10_p, -300.0)), "log10_p_value_local": log10_p, "lam": lam,
            "win_rate_training": p_train, "win_rate_test": float(test.mean()), "rounds_training": int(w[:, train].size),
            "rounds_test": int(test.size),
            "rigour": "CHSH-game test factor, p <= 1 / T, valid for dependent rounds under uniform random settings; "
                      "settings here are fixed per circuit [verify]"}


def no_signalling(bits: np.ndarray) -> float:
    """bits: (4, shots, 2) of one pair -> Bonferroni p-value of the four marginal comparisons (two-proportion z)."""
    from scipy.stats import norm

    ps = []
    for side, pairs in ((0, ((0, 1), (2, 3))), (1, ((0, 2), (1, 3)))):       # first qubit: b0 against b1; second: a0 against a1
        for i, j in pairs:
            x, y = bits[i, :, side], bits[j, :, side]
            p = (x.sum() + y.sum()) / (len(x) + len(y))
            se = math.sqrt(max(p * (1 - p), 1e-12) * (1 / len(x) + 1 / len(y)))
            ps.append(2 * float(norm.sf(abs(float(x.mean()) - float(y.mean())) / se)))
    return float(min(1.0, 4 * min(ps)))
