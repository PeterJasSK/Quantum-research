"""#15 reproduction — scanner fingerprint.

(a) --selfcheck (plan AC-5): blur the noise-free stub phantom with a KNOWN 3-D Gaussian PSF, add NPS-shaped
    noise of KNOWN σ, and recover PSF σ (z, xy), σ and the NPS peak with F_render.src.fingerprint.
    PASS = σ within 10 %, NPS peak within one frequency bin (plan Q7).
(b) Peng et al. 2023 [F05] §2.2.1 / Fig. 2(i): patch-wise NPS noise synthesis (6.8 mm patches, 30 % overlap,
    trapezoid merge) estimated from 20 repeated acquisitions reproduces the real noise distribution's moments
    "within 2 %". Ours: a non-stationary ground-truth noise field (two regions with different NPS and σ) plays
    the repeated scans; we estimate the patch NPS from 20 realisations, synthesise, and compare moments
    (σ and kurtosis) region by region.

    python -m F_render.repro.r15_fingerprint [--selfcheck]
"""
from __future__ import annotations

import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.stats import kurtosis  # noqa: E402

from F_render.src import fingerprint as ffp  # noqa: E402
from F_render.src import io as fio  # noqa: E402
from F_render.src import noise as fn  # noqa: E402
from F_render.src.status import set_reproduced  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402

SEED = "15" * 32
TRUE_PSF = np.array([3.0, 1.6, 1.6])        # mm, z y x
TRUE_SIGMA = 15.0                           # HU


def _nps_curve(f, peak):
    return f * np.exp(-(f / peak) ** 2)


def selfcheck(run) -> dict:
    masks, mp = fio.load(fio.STUB["masks"], "anatomy_masks")
    v = fio.host_volumes(masks, mp)
    sp = np.array(v["meta"]["spacing_mm_xyz"][::-1])
    h = ndi.gaussian_filter(v["host_ct"].astype(np.float32), TRUE_PSF / sp)
    f = np.linspace(0, 0.25, 40)
    nps = _nps_curve(f, 0.12)
    h = h + fn.noise_slices(h.shape, sp[2], sp[1], f, nps, rng(SEED, "F.r15.noise"), sigma=TRUE_SIGMA)
    fp = ffp.estimate(h, v["body"], v["lungs"], sp, slice_thickness_mm=sp[0])
    p, n = fp["psf"], fp["nps"]
    sig_map = float(np.median(fp["sigma_map"][fp["sigma_map"] > 0]))
    est = {"sigma_z_mm": p["sigma_z_mm"], "sigma_xy_mm": p["sigma_xy_mm"], "sigma_map_hu": sig_map,
           "sigma_nps_hu": fn.sigma_of(n["freq"], n["nps"]),
           "nps_peak": float(n["freq"][np.argmax(n["nps"])]), "nps_bin": float(n["freq"][1] - n["freq"][0])}
    true_peak = float(f[np.argmax(nps)])
    checks = {
        "psf z": abs(est["sigma_z_mm"] / TRUE_PSF[0] - 1) <= 0.10,
        "psf xy": abs(est["sigma_xy_mm"] / TRUE_PSF[1] - 1) <= 0.10,
        "sigma (σ map)": abs(sig_map / TRUE_SIGMA - 1) <= 0.10,
        "NPS peak": abs(est["nps_peak"] - true_peak) <= est["nps_bin"],
    }
    print(f"true  PSF σ zyx = {TRUE_PSF.tolist()} mm, σ = {TRUE_SIGMA} HU, NPS peak = {true_peak:.3f} cyc/mm")
    print(f"est.  PSF σ z = {est['sigma_z_mm']:.3f} ({p['z_method']}), xy = {est['sigma_xy_mm']:.3f} mm; "
          f"σ map = {sig_map:.2f} HU, σ(NPS) = {est['sigma_nps_hu']:.2f} HU; NPS peak = {est['nps_peak']:.3f} "
          f"(bin {est['nps_bin']:.3f}); MTF f50 = {p['f50_cyc_per_mm']:.3f} cyc/mm")
    for k, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    print("PASS" if all(checks.values()) else "FAIL")

    fig, ax = plt.subplots(1, 3, figsize=(11, 3.2), dpi=110)
    ax[0].plot(p["esf_x"], p["esf"])
    ax[0].set_title("oversampled air–skin ESF", fontsize=9)
    ax[0].set_xlabel("mm along outward normal")
    ff = np.asarray(p["mtf_freq"])
    ax[1].plot(ff, p["mtf"], label="estimated")
    ax[1].plot(ff, np.exp(-2 * np.pi ** 2 * TRUE_PSF[1] ** 2 * ff ** 2), "--", label="true (Gaussian PSF)")
    ax[1].set_title("in-plane MTF", fontsize=9)
    ax[1].set_xlabel("cyc/mm")
    ax[1].legend(fontsize=7)
    scale = TRUE_SIGMA ** 2 / fn.sigma_of(f, nps) ** 2
    ax[2].plot(f, nps * scale, "--", label="true")
    ax[2].plot(n["freq"], n["nps"], label="estimated (detrended ROIs)")
    ax[2].set_title("NPS (HU² mm²)", fontsize=9)
    ax[2].set_xlabel("cyc/mm")
    ax[2].legend(fontsize=7)
    fig.suptitle("#15 self-check on the stub phantom (known PSF + noise) — " +
                 ("PASS" if all(checks.values()) else "FAIL"), fontsize=9)
    fig.tight_layout()
    fig.savefig(fio.F_DIR / "figures" / "r15-selfcheck.png")
    plt.close(fig)
    return {"est": est, "checks": {k: bool(v) for k, v in checks.items()}}


def peng(run) -> dict:
    g = rng(SEED, "F.r15.peng")
    ny = nx = 192
    dx = dy = 0.7
    f = np.linspace(0, 0.5 / dx, 60)
    nps_a, nps_b = _nps_curve(f, 0.15), _nps_curve(f, 0.30)
    sig_a, sig_b = 20.0, 35.0

    def truth(seed_label):
        gg = rng(SEED, seed_label)
        a = fn.noise_slices((1, ny, nx), dx, dy, f, nps_a, gg, sigma=sig_a)[0]
        b = fn.noise_slices((1, ny, nx), dx, dy, f, nps_b, gg, sigma=sig_b)[0]
        w = 1 / (1 + np.exp(-(np.arange(nx) - nx / 2) / 6.0))       # smooth left/right transition
        return a * np.sqrt(1 - w) + b * np.sqrt(w)

    reals = np.stack([truth(f"F.r15.real.{i}") for i in range(20)])      # 20 "repeated acquisitions"
    noise = reals - reals.mean(0)                                         # [F05]: subtract the average image
    noise *= np.sqrt(20 / 19)
    py = px = max(int(round(6.8 / dx)), 4)

    def nps_of_patch(cy, cx):
        patch = noise[:, cy:cy + py, cx:cx + px]
        if patch.shape[1:] != (py, px):
            pad = ((0, 0), (0, py - patch.shape[1]), (0, px - patch.shape[2]))
            patch = np.pad(patch, pad, mode="reflect")
        return np.fft.ifftshift(fn.nps2d(list(patch), dx, dy))

    sims = np.stack([fn.patch_noise_2d((ny, nx), dx, dy, nps_of_patch, g) for _ in range(20)])
    test = np.stack([truth(f"F.r15.test.{i}") for i in range(20)])     # independent "real" realisations
    out = {}
    for name, sl in (("left (σ 20, soft NPS)", slice(16, nx // 2 - 24)), ("right (σ 35, sharp NPS)",
                                                                           slice(nx // 2 + 24, nx - 16))):
        r, s = test[:, 16:-16, sl].ravel(), sims[:, 16:-16, sl].ravel()
        out[name] = {"std_real": float(r.std()), "std_sim": float(s.std()),
                     "std_diff_pct": float(100 * (s.std() / r.std() - 1)),
                     "kurt_real": float(kurtosis(r, fisher=False)), "kurt_sim": float(kurtosis(s, fisher=False)),
                     "kurt_diff_pct": float(100 * (kurtosis(s, fisher=False) / kurtosis(r, fisher=False) - 1))}
        print(f"{name:26s} σ real {r.std():6.2f} sim {s.std():6.2f} ({out[name]['std_diff_pct']:+.2f} %)  "
              f"kurtosis real {out[name]['kurt_real']:.3f} sim {out[name]['kurt_sim']:.3f} "
              f"({out[name]['kurt_diff_pct']:+.2f} %)")
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.4), dpi=110)
    ax[0].imshow(test[0], cmap="gray", vmin=-80, vmax=80)
    ax[0].set_title("ground-truth non-stationary noise", fontsize=9)
    ax[1].imshow(sims[0], cmap="gray", vmin=-80, vmax=80)
    ax[1].set_title("[F05] patch-NPS synthesis (6.8 mm, 30 %)", fontsize=9)
    ax[2].plot(test.std(axis=(0, 1)), label="real σ(x)")
    ax[2].plot(sims.std(axis=(0, 1)), label="simulated σ(x)")
    ax[2].set_title("column-wise σ (HU)", fontsize=9)
    ax[2].legend(fontsize=7)
    for a in ax[:2]:
        a.set_xticks([])
        a.set_yticks([])
    fig.tight_layout()
    fig.savefig(fio.F_DIR / "figures" / "r15-peng-patch-noise.png")
    plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selfcheck", action="store_true", help="only the AC-5 ground-truth recovery")
    a = ap.parse_args(argv)
    run = start_run("F_render", "repro-15", seed_hex=SEED, tool="F_render.repro.r15_fingerprint")
    sc = selfcheck(run)
    if a.selfcheck:
        run.finish("selfcheck " + ("PASS" if all(sc["checks"].values()) else "FAIL"))
        return 0 if all(sc["checks"].values()) else 1
    pg = peng(run)
    worst = max(max(abs(v["std_diff_pct"]), abs(v["kurt_diff_pct"])) for v in pg.values())
    agree = worst <= 2.0
    set_reproduced(15, "adapted" if agree and all(sc["checks"].values()) else "dissected", {
        "quantity": "moments (σ, kurtosis) of patch-NPS-synthesised vs real non-stationary noise ([F05] Fig. 2i)",
        "paper_value": "differences within 2 % (up to 4th moment)",
        "our_value": "; ".join(f"{k}: σ {v['std_diff_pct']:+.2f} %, kurtosis {v['kurt_diff_pct']:+.2f} %"
                               for k, v in pg.items()) + "; self-check PSF/σ within 10 %",
        "unit": "%", "agreement": ("agree" if agree else "disagree") + f" (worst {worst:.2f} %); synthetic "
                                  "ground-truth noise, not the orange-man phantom",
        "sim_mode": "n/a", "figure": "figures/r15-peng-patch-noise.png"},
        ["figures/r15-peng-patch-noise.png", "figures/r15-selfcheck.png"])
    run.finish(f"selfcheck {sc['checks']}; Peng moments worst {worst:.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
