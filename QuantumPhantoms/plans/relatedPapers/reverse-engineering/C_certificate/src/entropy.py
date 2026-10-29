"""Bell-test entropy accounting (target #4; Pironio C01, spot-checking after Vazirani–Vidick C05).

CHSH value S → min-entropy per round f(S) → certified bits → extractable length. qiskit-free.

    f(S) = 1 − log₂(1 + √(2 − S²/4))        Pironio C01, Fig. 2 curve b (analytic lower bound)

Our pipeline certifies with f(S_low), where S_low is a Hoeffding lower confidence bound on S from
the hidden test rounds only. This is an i.i.d. finite-statistics treatment, not the entropy
accumulation theorem; see dossiers/04-bell-entropy-accounting.md.
"""
from __future__ import annotations

import math

import numpy as np

S_QUANTUM_MAX = 2.0 * math.sqrt(2.0)
SETTINGS = ((0, 0), (0, 1), (1, 0), (1, 1))


def f_hmin(S: float) -> float:
    """Pironio's analytic min-entropy bound per round on the pair (a, b) given (x, y)."""
    if S <= 2.0:
        return 0.0
    S = min(S, S_QUANTUM_MAX)
    return 1.0 - math.log2(1.0 + math.sqrt(max(0.0, 2.0 - S * S / 4.0)))


def f_no_signalling(S: float) -> float:
    """Pironio C01 Fig. 2 curve c: min-entropy implied by no-signalling alone."""
    return 0.0 if S <= 2.0 else -math.log2(1.5 - min(S, 4.0) / 4.0)


def chsh_estimate(x, y, a, b, test) -> dict:
    """Ŝ = E00 + E01 + E10 − E11 from test rounds only; E_xy = mean of (−1)^(a⊕b)."""
    x, y, a, b, test = (np.asarray(v, dtype=np.uint8) for v in (x, y, a, b, test))
    E, n = {}, {}
    for sx, sy in SETTINGS:
        sel = (test == 1) & (x == sx) & (y == sy)
        key = f"{sx}{sy}"
        n[key] = int(sel.sum())
        E[key] = float(np.mean(1.0 - 2.0 * (a[sel] ^ b[sel]))) if n[key] else 0.0
    S = E["00"] + E["01"] + E["10"] - E["11"]
    return {"S_hat": S, "E_xy": E, "n_xy": n}


def s_lower_bound(est: dict, eps_est: float) -> tuple[float, dict]:
    """S_low = Ŝ − Σ δ_xy, δ_xy = √(2 ln(8/ε)/n_xy): Hoeffding per correlator, union bound 4 × 2 sides."""
    delta = {k: (math.sqrt(2.0 * math.log(8.0 / eps_est) / n) if n else math.inf)
             for k, n in est["n_xy"].items()}
    return est["S_hat"] - sum(delta.values()), delta


def certified_bits(n_gen: int, h: float) -> int:
    return int(math.floor(n_gen * h))


def extractable_len(cert_bits: int, eps_ext: float) -> int:
    """Leftover hash lemma: L ≤ H_min − 2 log₂(1/ε_ext)."""
    return max(0, int(math.floor(cert_bits - 2.0 * math.log2(1.0 / eps_ext))))


def pironio_epsilon(n: int, delta: float, q: float = 0.25) -> float:
    """Pironio C01 App. A, Eq. (11) solved for ε: δ = exp(−n ε² / (2 (1/q + I_q)²))."""
    return (1.0 / q + S_QUANTUM_MAX) * math.sqrt(2.0 * math.log(1.0 / delta) / n)


def pironio_bits(n: int, I_hat: float, delta: float, q: float = 0.25) -> float:
    """Pironio C01 Eq. (12): H∞(R|S) ≥ n f(Î − ε) with probability ≥ 1 − δ (analytic f)."""
    return n * f_hmin(I_hat - pironio_epsilon(n, delta, q))
