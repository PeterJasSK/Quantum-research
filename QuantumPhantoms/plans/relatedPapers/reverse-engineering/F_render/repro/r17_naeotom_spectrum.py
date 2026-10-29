"""#17 reproduction — NAEOTOM Alpha approximation from McCabe et al. 2025 [F04] published parameters only.

F04 Table 1 (ACR phantom, 120 kV, thresholds 20/65 keV, 0.4 mm): real-scanner MTF f50 = 0.39 mm⁻¹ (Br40),
0.77 (Br56), 1.08 (Br64); §3.1.1 / Fig. 3: noise follows dose over 1.5–12 mGy (19/38/72/152 mAs).
Ours (simulated, XCIST — not DukeSim, not the real scanner): `F_render/xcist/naeotom_alpha.cfg` scanning a
200 mm water cylinder at the four mAs levels; f50 from the air–water edge with the #15 estimator;
noise σ in a central ROI and its dose exponent (quantum-limited expectation −0.5).
XCIST's 'standard' FBP kernel stands in for Br40 + QIR-3 — only f50 order-of-magnitude agreement is expected.

    python -m F_render.repro.r17_naeotom_spectrum        (~15–25 min CPU: four XCIST photon-counting scans)
"""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from F_render.src import fingerprint as ffp  # noqa: E402
from F_render.src import io as fio  # noqa: E402
from F_render.src import projection_insert as pi  # noqa: E402
from F_render.src.status import set_reproduced  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402

SEED = "17" * 32
MAS = (19, 38, 72, 152)            # [F04 §2.9]
PAPER_F50_BR40 = 0.39              # mm⁻¹, real scanner [F04 Table 1]
VOX, N_XY, N_Z, R = 0.5, 440, 8, 100.0


def main() -> int:
    run = start_run("F_render", "repro-17", seed_hex=SEED, tool="F_render.repro.r17_naeotom_spectrum")
    wd = run.path / "xcist"
    yy, xx = np.meshgrid(*[(np.arange(N_XY) - N_XY / 2 + 0.5) * VOX] * 2, indexing="ij")
    ph = np.broadcast_to((np.hypot(yy, xx) < R).astype(np.float32), (N_Z, N_XY, N_XY))
    pj = pi.voxel_phantom(wd, "acr_like", ph, (VOX,) * 3)
    grid = pi.recon_grid(pi.NAEOTOM_CFG)
    px = grid["pixel_mm"]
    res = []
    imgs = {}
    for mas in MAS:
        name = f"naeotom_{mas}mAs"
        if not (wd / f"{name}.prep").exists():
            print(f"XCIST PCCT scan {mas} mAs", flush=True)
            pi.simulate(wd, name, pj, pi.NAEOTOM_CFG, noise=True, seed=mas, mA=mas / 0.5)
        img = pi.reconstruct(wd, name, pi.NAEOTOM_CFG)
        imgs[mas] = img
        c = img.shape[1] // 2
        w = int(20 / px)
        roi = img[0, c - w:c + w, c - w:c + w]
        res.append({"mAs": mas, "noise_hu": float(roi.std()), "water_hu": float(roi.mean())})
    hi = imgs[MAS[-1]]
    body = np.stack([ndi.binary_fill_holes(s) for s in ndi.gaussian_filter(hi, (0, 1, 1)) > -500]).astype(np.uint8)
    sp = np.array([grid["slice_mm"], px, px])
    if hi.shape[0] == 1:          # single slice: replicate so the 3-D estimator has a z extent (in-plane only)
        hi3, body3 = np.repeat(hi, 5, 0), np.repeat(body, 5, 0)
    else:
        hi3, body3 = hi, body
    psf = ffp.estimate_psf(hi3, body3, None, sp, rng(SEED, "F.fingerprint"), slice_thickness_mm=grid["slice_mm"])
    f50 = psf["f50_cyc_per_mm"]
    lm = np.log([r["mAs"] for r in res])
    ls = np.log([r["noise_hu"] for r in res])
    slope = float(np.polyfit(lm, ls, 1)[0])
    out = {"f50_mm-1": f50, "paper_f50_Br40": PAPER_F50_BR40, "noise_dose_exponent": slope, "levels": res}
    (run.path / "r17_results.json").write_text(json.dumps(out, indent=1) + "\n")

    fig, ax = plt.subplots(1, 3, figsize=(11, 3.3), dpi=110)
    c = hi.shape[1] // 2
    ax[0].imshow(hi[0], cmap="gray", vmin=-100, vmax=100)
    ax[0].set_title(f"XCIST NAEOTOM-approx., {MAS[-1]} mAs, W200/L0", fontsize=8)
    ax[0].set_xticks([])
    ax[0].set_yticks([])
    ax[1].plot(psf["mtf_freq"], psf["mtf"], label=f"ours f50 = {f50:.2f} mm⁻¹")
    ax[1].axvline(PAPER_F50_BR40, ls="--", c="k", label="F04 real f50 Br40 = 0.39")
    ax[1].axhline(0.5, c="0.7", lw=0.8)
    ax[1].set_xlabel("cyc/mm")
    ax[1].set_title("MTF (air–water edge, #15 estimator)", fontsize=8)
    ax[1].legend(fontsize=7)
    m = np.array([r["mAs"] for r in res])
    ax[2].loglog(m, [r["noise_hu"] for r in res], "o-", label=f"ours (exponent {slope:.2f})")
    ax[2].loglog(m, res[-1]["noise_hu"] * (m / m[-1]) ** -0.5, "--", label="∝ mAs^−0.5")
    ax[2].set_xlabel("mAs")
    ax[2].set_ylabel("σ (HU)")
    ax[2].set_title("noise vs dose (F04 levels 19–152 mAs)", fontsize=8)
    ax[2].legend(fontsize=7)
    fig.suptitle("#17 simulated: XCIST with NAEOTOM Alpha published parameters (approximation, not DukeSim)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(fio.F_DIR / "figures" / "r17-naeotom.png")
    plt.close(fig)
    rel = abs(f50 / PAPER_F50_BR40 - 1)
    agree = rel <= 0.25
    set_reproduced(17, "reproduced" if agree else "dissected", {
        "quantity": "MTF f50 of the 120 kV, 0.4 mm, 20/65 keV photon-counting configuration ([F04] Table 1, Br40)",
        "paper_value": "0.39 mm⁻¹ (real NAEOTOM Alpha, Br40, QIR-3); DukeSim 0.39",
        "our_value": f"{f50:.3f} mm⁻¹ (XCIST FBP 'standard'); noise ∝ mAs^{slope:.2f}",
        "unit": "mm⁻¹",
        "agreement": (f"{'within' if agree else 'outside'} 25 % ({100 * (f50 / PAPER_F50_BR40 - 1):+.0f} %); "
                      "approximation — XCIST kernel ≠ Br40, CZT response ≠ CdTe"),
        "sim_mode": "n/a", "figure": "figures/r17-naeotom.png"}, ["figures/r17-naeotom.png"])
    run.finish(f"f50 {f50:.3f} vs 0.39; noise exponent {slope:.2f}")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
