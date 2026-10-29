"""#14 reproduction — Ambrosini et al. SPIE 2010 [F01] §3: spherical-harmonic (lmax = 3) reconstructions of real
nodules, voxelised with partial volume and PSF blur, correlate with the real nodule at 0.8897 ± 0.0609
(3-D correlation coefficient, 17 lung metastases 8–20 mm).

Ours: the same measurement per LIDC nodule (consensus ≥ 3 readers, 8 ≤ d_eq ≤ 20 mm), computed inside
F_render.src.lesion_fit (field `f01_corr3d`; PSF = the host scan's own fingerprint, #15). This script reads
the latest lesion-fit run's parameter table (scalars only), summarises it and plots the library.

    python -m F_render.src.lesion_fit --lidc 20     # first (writes the library + nodules.json)
    python -m F_render.repro.r14_lesion_fit
"""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from F_render.src import io as fio  # noqa: E402
from F_render.src.status import set_reproduced  # noqa: E402
from shared.runrecord import start_run  # noqa: E402

PAPER = (0.8897, 0.0609, 17)
TYPES = ("solid", "part-solid", "ground-glass")


def main() -> int:
    fits = sorted((fio.F_DIR / "runs").glob("*-lesion-fit/nodules.json"))
    if not fits:
        print("no lesion-fit run found: run `python -m F_render.src.lesion_fit --lidc 20` first", file=sys.stderr)
        return 1
    nod = json.loads(fits[-1].read_text())
    run = start_run("F_render", "repro-14", tool="F_render.repro.r14_lesion_fit")
    run.add_input(fio.FITTED_LIBRARY, "lesion_model_library")
    # F01's 17 nodules are lung METASTASES (solid): like-for-like = solid LIDC nodules 8–20 mm.
    # All types are reported too — ground-glass texture is not captured by a uniform-HU SH model.
    sel = [r for r in nod if 8.0 <= r["d_eq_mm"] <= 20.0 and r["type"] == "solid"]
    c = np.array([r["f01_corr3d"] for r in sel])
    allc = np.array([r["f01_corr3d"] for r in nod if 8.0 <= r["d_eq_mm"] <= 20.0])
    z = (c.mean() - PAPER[0]) / np.hypot(c.std(ddof=1) / np.sqrt(len(c)), PAPER[1] / np.sqrt(PAPER[2]))
    print(f"F01 3-D correlation, solid 8–20 mm: ours {c.mean():.4f} ± {c.std(ddof=1):.4f} (n = {len(c)}) "
          f"vs paper {PAPER[0]} ± {PAPER[1]} (n = {PAPER[2]}); z = {z:+.2f}; "
          f"all types 8–20 mm {allc.mean():.4f} ± {allc.std(ddof=1):.4f} (n = {len(allc)})")
    for t in TYPES:
        rs = [r for r in nod if r["type"] == t]
        if rs:
            print(f"  {t:12s} n={len(rs):3d}  HU {np.mean([r['hu_interior'] for r in rs]):7.1f}  "
                  f"edge σ {np.mean([r['edge_sigma_mm'] for r in rs]):.2f} mm  "
                  f"ψ {np.mean([r['sphericity'] for r in rs]):.2f}  corr {np.mean([r['f01_corr3d'] for r in rs]):.3f}")

    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4), dpi=110)
    ax[0].hist(allc, bins=12, color="0.6", alpha=0.6, label=f"all types 8–20 mm (n={len(allc)})")
    ax[0].hist(c, bins=12, color="C0", alpha=0.8, label=f"solid 8–20 mm (n={len(c)})")
    ax[0].axvline(c.mean(), color="C0")
    ax[0].axvspan(PAPER[0] - PAPER[1], PAPER[0] + PAPER[1], color="0.85", label="F01 mean ± sd")
    ax[0].axvline(PAPER[0], color="k", ls="--")
    ax[0].set_xlabel("3-D correlation, SH(l≤3) simulated vs real")
    ax[0].legend(fontsize=7)
    for i, t in enumerate(TYPES):
        rs = [r for r in nod if r["type"] == t]
        ax[1].scatter([r["d_eq_mm"] for r in rs], [r["hu_interior"] for r in rs], s=12, label=f"{t} ({len(rs)})")
    ax[1].axhline(-400, c="0.6", lw=0.8, ls=":")
    ax[1].axhline(-160, c="0.6", lw=0.8, ls=":")
    ax[1].set_xlabel("d_eq (mm)")
    ax[1].set_ylabel("interior HU")
    ax[1].set_title("HU by type (dotted: F06 −400 / −160)", fontsize=8)
    ax[1].legend(fontsize=7)
    for i, t in enumerate(TYPES):
        rs = [r for r in nod if r["type"] == t]
        if rs:
            P = np.array([r["sh_power"] for r in rs])
            ax[2].errorbar(np.arange(1, P.shape[1] + 1) + 0.08 * i, P.mean(0), P.std(0), marker="o", capsize=2,
                           label=t)
    ax[2].set_yscale("log")
    ax[2].set_xlabel("SH degree l")
    ax[2].set_ylabel("P_l = Σ a_lm² / a_00²")
    ax[2].legend(fontsize=7)
    fig.suptitle("#14 lesion-model library from LIDC (parameters only) and the [F01] SH-reconstruction check",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(fio.F_DIR / "figures" / "r14-lesion-library.png")
    plt.close(fig)
    agree = abs(z) < 2 or abs(c.mean() - PAPER[0]) <= PAPER[1]
    set_reproduced(14, "adapted", {
        "quantity": "3-D correlation of SH(l≤3) simulated vs real solid nodules, 8–20 mm ([F01] §3, Table 1)",
        "paper_value": f"{PAPER[0]} ± {PAPER[1]} (n = {PAPER[2]} metastases)",
        "our_value": f"{c.mean():.4f} ± {c.std(ddof=1):.4f} (n = {len(c)} solid LIDC nodules); "
                     f"all types {allc.mean():.4f} ± {allc.std(ddof=1):.4f} (n = {len(allc)})",
        "unit": "", "agreement": ("agree" if agree else "disagree") + f" (difference {c.mean() - PAPER[0]:+.4f}, "
                                 f"within one paper sd: {abs(c.mean() - PAPER[0]) <= PAPER[1]})",
        "sim_mode": "n/a", "figure": "figures/r14-lesion-library.png"}, ["figures/r14-lesion-library.png"])
    run.finish(f"corr {c.mean():.4f}±{c.std(ddof=1):.4f} n={len(c)} vs {PAPER[0]}±{PAPER[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
