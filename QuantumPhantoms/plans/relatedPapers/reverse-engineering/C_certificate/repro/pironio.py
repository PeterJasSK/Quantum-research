"""Reproduce Pironio et al. 2010 (C01): Î from Table 1, the 42 certified bits, the f(I) curve. Target #4.

    python -m C_certificate.repro.pironio

Paper: n = 3016 events, Î = 2.414 ± 0.058, uniform inputs (q = 1/4), confidence 1 − δ = 99%
⇒ "at least 42 new random bits" (C01 main text + App. A Eq. 12, H∞ ≥ n f(Î − ε)).
Paper uses the SDP curve f (Fig. 2 curve a); we use the analytic lower bound (curve b), so our
count is expected slightly below 42. Writes figures/hmin_vs_S.png with our latest simulated runs.
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from C_certificate.src.entropy import S_QUANTUM_MAX, f_hmin, f_no_signalling, pironio_bits, pironio_epsilon  # noqa: E402
from shared import RE_ROOT  # noqa: E402

LETTER = RE_ROOT / "C_certificate"
FIG = LETTER / "figures" / "hmin_vs_S.png"

# C01 Table 1: N(a, b; x, y) for (a,b) = 00, 01, 10, 11
TABLE1 = {"00": (293, 94, 70, 295), "01": (298, 70, 74, 309), "10": (283, 69, 64, 291), "11": (68, 340, 309, 89)}
PAPER = {"n": 3016, "I_hat": 2.414, "delta": 0.01, "q": 0.25, "bits": 42}


def table1_I() -> tuple[float, int]:
    I, n = 0.0, 0
    for xy, (n00, n01, n10, n11) in TABLE1.items():
        tot = n00 + n01 + n10 + n11
        n += tot
        corr = ((n00 + n11) - (n01 + n10)) / tot
        I += -corr if xy == "11" else corr
    return I, n


def latest_runs() -> dict:
    out = {}
    for mode in ("ideal", "heron"):
        dirs = sorted(glob.glob(str(LETTER / "runs" / f"*-chsh-{mode}")))
        if dirs:
            out[mode] = json.loads((Path(dirs[-1]) / "accounting.json").read_text()) | {"run_id": Path(dirs[-1]).name}
    return out


def main() -> None:
    I_tab, n_tab = table1_I()
    eps = pironio_epsilon(PAPER["n"], PAPER["delta"], PAPER["q"])
    ours = pironio_bits(PAPER["n"], PAPER["I_hat"], PAPER["delta"], PAPER["q"])
    dev = (ours - PAPER["bits"]) / PAPER["bits"]
    print(f"Table 1:  n = {n_tab} (paper {PAPER['n']}),  Î = {I_tab:.4f} (paper {PAPER['I_hat']})")
    print(f"Azuma–Hoeffding ε = (1/q + 2√2)·√(2 ln(1/δ)/n) = {eps:.4f}  ⇒  Î − ε = {PAPER['I_hat'] - eps:.4f}")
    print(f"certified min-entropy n·f(Î − ε): ours {ours:.1f} bits (analytic f) vs paper {PAPER['bits']} bits "
          f"(SDP f)  →  deviation {dev:+.1%}")
    print(f"asymptotic n·f(Î) (no finite-statistics penalty): {PAPER['n'] * f_hmin(PAPER['I_hat']):.0f} bits")

    runs = latest_runs()
    for mode, acc in runs.items():
        print(f"{acc['sim_label']}: Ŝ = {acc['S_hat']:.4f}, S_low = {acc['S_low']:.4f}, "
              f"h = {acc['h_min_per_round']:.4f}, certified = {acc['certified_bits']} bits ({acc['run_id']})")

    S = np.linspace(2.0, S_QUANTUM_MAX, 400)
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=130)
    ax.plot(S, [f_hmin(s) for s in S], color="#1f6feb", lw=2, label="f(S) analytic bound (Pironio Fig. 2 b)")
    ax.plot(S, [f_no_signalling(s) for s in S], color="#8b949e", lw=1, ls="--",
            label="no-signalling bound (Fig. 2 c)")
    ax.axvline(PAPER["I_hat"], color="#bf8700", lw=1, ls=":")
    ax.plot([PAPER["I_hat"] - eps], [f_hmin(PAPER["I_hat"] - eps)], "o", color="#bf8700",
            label=f"Pironio Î − ε = {PAPER['I_hat'] - eps:.3f} → {ours:.1f} bits (paper 42)")
    style = {"ideal": "#2da44e", "heron": "#cf222e"}
    for mode, acc in runs.items():
        ax.plot([acc["S_hat"]], [f_hmin(acc["S_hat"])], "s", mfc="none", color=style[mode])
        ax.plot([acc["S_low"]], [acc["h_min_per_round"]], "s", color=style[mode],
                label=f"{acc['sim_label']}: S_low = {acc['S_low']:.3f} (open: Ŝ)")
    ax.set_xlabel("CHSH value S")
    ax.set_ylabel("min-entropy per round (bits)")
    ax.set_title("H_min vs S: Pironio 2010 reproduced; our runs are simulated, not certified", fontsize=9)
    ax.set_xlim(2.0, 2.85)
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    FIG.parent.mkdir(exist_ok=True)
    fig.savefig(FIG)
    print(f"figure → {FIG.relative_to(RE_ROOT)}")
    assert math.isclose(f_hmin(2.0), 0.0) and math.isclose(f_hmin(S_QUANTUM_MAX), 1.0)


if __name__ == "__main__":
    main()
