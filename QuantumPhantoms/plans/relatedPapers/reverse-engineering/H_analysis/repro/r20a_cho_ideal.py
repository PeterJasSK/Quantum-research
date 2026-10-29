"""R20a - CHO reaches the analytic ideal-observer AUC where it must (target #20, VICTRE H03).

Gaussian signal (sigma_s = 3 px) on white Gaussian noise, 64x64, SKE/BKE.
Ideal observer d' = ||s|| / sigma, AUC = Phi(d'/sqrt(2)). Channel width a is matched so
the signal lies in channel 0 (LG_0 is a Gaussian of sigma = a / sqrt(2*pi), so a = sigma_s*sqrt(2*pi)).

A CHO trained on 100 pairs pays a finite-training penalty (estimated template); the 1000-pair
arm isolates method correctness and is the agreement criterion, the 100-pair arm is printed as the
VICTRE-design penalty.

Usage (cwd = reverse-engineering/):  python -m H_analysis.repro.r20a_cho_ideal
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
from scipy.stats import norm

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from H_analysis.src import observer  # noqa: E402
from shared import seedhash  # noqa: E402

H = Path(__file__).resolve().parents[1]
SEED = seedhash.sha256_bytes(b"H.r20a")
N, SIGMA_S, NOISE = 64, 3.0, 1.0
N_READERS, N_TEST = 30, 20000  # plan says 2000; 2000 pairs leave +-0.013 test-set error at AUC 0.6
N_TRAIN_VICTRE, N_TRAIN_ASYMP = 100, 1000  # VICTRE design / near-asymptotic template (agreement criterion)
TARGET_AUC = [0.6, 0.75, 0.85, 0.93, 0.98]


def main() -> int:
    y, x = np.mgrid[:N, :N]
    c = (N - 1) / 2.0
    shape = np.exp(-((y - c) ** 2 + (x - c) ** 2) / (2 * SIGMA_S**2))
    shape_norm = np.linalg.norm(shape)
    chans = observer.lg_channels_2d(N, a=SIGMA_S * np.sqrt(2 * np.pi), n=5)
    test_rng = seedhash.rng(SEED, "H.r20a.test")
    rows = []
    for t in TARGET_AUC:
        dprime = np.sqrt(2) * norm.ppf(t)
        sig = shape * dprime * NOISE / shape_norm
        analytic = float(norm.cdf(dprime / np.sqrt(2)))
        ch2 = chans.reshape(5, -1)
        neg_t = np.concatenate([test_rng.normal(0, NOISE, (2000, N * N)) @ ch2.T for _ in range(N_TEST // 2000)])
        pos_t = np.concatenate([(test_rng.normal(0, NOISE, (2000, N * N)) + sig.ravel()) @ ch2.T
                                for _ in range(N_TEST // 2000)])
        res = []
        for n_train in (N_TRAIN_VICTRE, N_TRAIN_ASYMP):
            aucs = []
            for k in range(N_READERS):
                r = seedhash.rng(SEED, f"H.reader.{k}.{t}.{n_train}")
                neg = r.normal(0, NOISE, (n_train, N, N))
                pos = r.normal(0, NOISE, (n_train, N, N)) + sig
                w = observer.cho_train(pos, neg, chans)
                aucs.append(observer.auc(pos_t @ w, neg_t @ w))
            res.append((float(np.mean(aucs)), float(np.std(aucs))))
        rows.append((t, analytic, res[1][0], res[1][1], res[0][0]))
    worst = max(abs(r[2] - r[1]) for r in rows)
    for t, a, o, s, o100 in rows:
        print(f"  AUC target={t:.2f}  analytic={a:.4f}  CHO(1000 pairs)={o:.4f} (reader sd {s:.4f})  "
              f"|diff|={abs(o - a):.4f}   CHO(100 pairs, VICTRE design)={o100:.4f}")
    agree = "yes" if worst < 0.01 else "no"
    print(f"paper=analytic ours=max|dAUC|={worst:.4f} agreement={agree}")
    fig, ax = plt.subplots(figsize=(4.2, 4))
    ax.plot([0.5, 1], [0.5, 1], "k--", lw=0.8, label="ideal observer")
    ax.errorbar([r[1] for r in rows], [r[2] for r in rows], [r[3] for r in rows], fmt="o", label="CHO (30 readers, 1000 pairs)")
    ax.plot([r[1] for r in rows], [r[4] for r in rows], "s", mfc="none", label="CHO (100 pairs)")
    ax.set_xlabel("analytic AUC"); ax.set_ylabel("CHO AUC"); ax.legend(); fig.tight_layout()
    out = H / "figures" / "r20a_cho_vs_ideal.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"figure {out.relative_to(H.parent)}")
    return 0 if agree == "yes" else 1


if __name__ == "__main__":
    sys.exit(main())
