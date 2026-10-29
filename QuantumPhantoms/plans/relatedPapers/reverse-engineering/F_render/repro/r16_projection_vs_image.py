"""#16 reproduction — Robins et al. PMB 2017 [F02] Table 4: projection-domain (Technique A) and image-domain
(Technique B) virtual nodules vs nodules physically present in the scan, volume percent difference.

Paper (SOMATOM Definition Flash, KYOTO KAGAKU phantom, 24 nodules): Technique B average PD −0.28 … +0.57 %
(FBP/IR 1.4–22 mGy, one IR protocol −2.28 %), Technique A −2.24 … −1.01 %; all |PD| < 3 %.

Ours (simulated: XCIST, not a physical phantom): a water cylinder with a lung-density (0.2 water) core,
6 nodules (5 / 8 / 10 mm × sphere / lobulated SH) scanned three times with the Definition-like config:
  real    — nodules in the phantom                         (the CT-derived reference)
  host    — no nodules                                      → Technique B: image-domain insert (#14 SH voxeliser,
                                                              partial volume, PSF from #15 on the host recon)
  lesion  — nodule excess attenuation alone, noise off      → Technique A: prep_host + prep_lesion, FBP
Volumes: threshold at the lung/nodule HU midpoint, connected component at the nodule centre.

    python -m F_render.repro.r16_projection_vs_image          (~45 min CPU: three XCIST scans)
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
from F_render.src.lesion_fit import lm_list, sh_fraction  # noqa: E402
from F_render.src.status import set_reproduced  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import rng  # noqa: E402

VOX = 0.4                         # phantom voxel (mm)
N_XY, N_Z = 500, 36               # 200 mm FOV, 14.4 mm in z
R_BODY, R_LUNG = 90.0, 75.0
LUNG_FRAC = 0.2
SEED_HEX = "16" * 32              # reproduction seed (not a tumour seed chain)
NODULES = [(d, s) for d in (5.0, 8.0, 10.0) for s in ("sphere", "lobulated")]


def sh_coef(shape: str, d_mm: float, lib: dict, g) -> np.ndarray:
    lmax = 3
    a00 = (d_mm / 2) / 0.28209479177387814           # r = a00·Y00 with Y00 = 1/(2√π)
    coef = np.zeros(len(lm_list(lmax)))
    coef[0] = a00
    if shape == "lobulated":
        sp = lib["types"].get("solid", {}).get("shape_params", {})
        for i, (l, m) in enumerate(lm_list(lmax)):
            if l >= 2:
                pw = max(sp.get(f"sh_l{l}_power_mean", 0.01), 0.01)
                coef[i] = a00 * g.normal(0, np.sqrt(pw / (2 * l + 1)))
    return coef


def nodule_positions():
    ang = np.deg2rad(np.arange(len(NODULES)) * 360 / len(NODULES))
    return [np.array([0.0, 40 * np.sin(a), 40 * np.cos(a)]) for a in ang]       # mm, z y x from iso


def phantoms(lib):
    g = rng(SEED_HEX, "F.r16.shape")
    zz, yy, xx = np.meshgrid(*[(np.arange(n) - n / 2 + 0.5) * VOX for n in (N_Z, N_XY, N_XY)], indexing="ij")
    rr = np.hypot(yy, xx)
    host = np.where(rr < R_BODY, 1.0, 0.0).astype(np.float32)
    host[rr < R_LUNG] = LUNG_FRAC
    les = np.zeros_like(host)
    coefs = []
    for (d, shape), c in zip(NODULES, nodule_positions()):
        coef = sh_coef(shape, d, lib, g)
        coefs.append(coef)
        h = int(np.ceil((d / 2 * 1.6 + 1) / VOX))
        cv = c / VOX + np.array([N_Z, N_XY, N_XY]) / 2 - 0.5
        lo = np.floor(cv).astype(int) - h
        box = tuple(slice(max(a, 0), min(a + 2 * h + 1, n)) for a, n in zip(lo, (N_Z, N_XY, N_XY)))
        f = sh_fraction(tuple(b.stop - b.start for b in box), (VOX,) * 3, cv - [b.start for b in box], coef, 3, ss=2)
        les[box] = np.maximum(les[box], (1 - LUNG_FRAC) * f)
    return host, les, coefs


def segment_volume(img, center_vox, thr, vox_mm3, half_vox):
    lo = np.maximum(np.round(center_vox).astype(int) - half_vox, 0)
    box = tuple(slice(a, a + 2 * h + 1) for a, h in zip(lo, half_vox))
    roi = img[box] > thr
    lab, _ = ndi.label(roi)
    c = tuple(np.clip(np.round(center_vox).astype(int) - lo, 0, np.array(roi.shape) - 1))
    if lab[c] == 0:
        return 0.0
    return float((lab == lab[c]).sum() * vox_mm3)


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xcist-dir", default=None, help="reuse the XCIST scans of an earlier repro-16 run dir")
    a = ap.parse_args(argv)
    lib_path = fio.FITTED_LIBRARY if fio.FITTED_LIBRARY.exists() else fio.STUB["library"]
    lib, _ = fio.load(lib_path, "lesion_model_library")
    run = start_run("F_render", "repro-16", seed_hex=SEED_HEX, tool="F_render.repro.r16_projection_vs_image")
    wd = run.path / "xcist"
    if a.xcist_dir:
        import shutil

        shutil.copytree(a.xcist_dir, wd, dirs_exist_ok=True)
    host_f, les_f, coefs = phantoms(lib)
    pj = {"host": pi.voxel_phantom(wd, "host", host_f, (VOX,) * 3),
          "real": pi.voxel_phantom(wd, "real", host_f + les_f, (VOX,) * 3),
          "lesion": pi.voxel_phantom(wd, "lesion", les_f, (VOX,) * 3)}
    true_vol = []
    for (d, _), c, coef in zip(NODULES, nodule_positions(), coefs):
        cv = c / VOX + np.array([N_Z, N_XY, N_XY]) / 2 - 0.5
        h = int(np.ceil((d / 2 * 1.6 + 1) / VOX))
        box = tuple(slice(max(int(np.floor(a)) - h, 0), min(int(np.floor(a)) + h + 1, n))
                    for a, n in zip(cv, (N_Z, N_XY, N_XY)))
        true_vol.append(float(les_f[box].sum() / (1 - LUNG_FRAC) * VOX ** 3))
    del host_f
    for name, noise in (("host", True), ("real", True), ("lesion", False)):
        if not (wd / f"{name}.prep").exists():
            print(f"XCIST scan: {name}", flush=True)
            pi.simulate(wd, name, pj[name], noise=noise, seed=1)
    pi.add_prep(wd / "host.prep", wd / "lesion.prep", wd / "techA.prep")
    img = {k: pi.reconstruct(wd, k) for k in ("host", "real", "techA")}
    grid = pi.recon_grid()
    px, sz = grid["pixel_mm"], grid["slice_mm"]
    sp = np.array([sz, px, px])

    # #15 on the host recon: the cylinder's air–water edge gives the in-plane PSF; no z edges → slice fallback
    h = img["host"]
    body = (ndi.gaussian_filter(h, 1) > -500)
    body = np.stack([ndi.binary_fill_holes(s) for s in body]).astype(np.uint8)
    lungs = ((h < -500) & (body > 0)).astype(np.uint8)
    psf = ffp.estimate_psf(h, body, lungs, sp, rng(SEED_HEX, "F.fingerprint"), slice_thickness_mm=sz)
    psf_zyx = np.array([psf["sigma_z_mm"], psf["sigma_xy_mm"], psf["sigma_xy_mm"]])

    hu_lung = float(np.median(h[lungs > 0]))
    vox_mm3 = float(sp.prod())
    rows, imgB = [], h.copy()
    # co-register (F02 §2.4): blobs of real − host vs the designed positions under the 8 in-plane
    # flips/transposes (XCIST image orientation vs phantom axes); keep the best-fitting one
    diff = ndi.gaussian_filter(img["real"] - h, 1) > 200
    lab, n = ndi.label(diff)
    sizes = ndi.sum(diff, lab, range(1, n + 1))
    cents = [np.array(c) for c in ndi.center_of_mass(diff, lab, [int(i) + 1 for i in np.argsort(sizes)[::-1][:len(NODULES)]])]
    mid = (np.array(h.shape) - 1) / 2
    # the 6 nodules sit on a symmetric ring, so several flips fit the positions equally well but permute the
    # nodules; among position-equivalent transforms keep the one whose blob volumes match the designed ones
    thr0 = hu_lung + 400
    blob_vol = [segment_volume(img["real"], m, thr0, vox_mm3, np.ceil(8 / sp).astype(int)) for m in cents]
    cands = []
    for sy in (1, -1):
        for sx in (1, -1):
            for tr in (False, True):
                exp = []
                for c in nodule_positions():
                    y, x = (c[2], c[1]) if tr else (c[1], c[2])
                    exp.append(np.array([mid[0], mid[1] + sy * y / px, mid[2] + sx * x / px]))
                m = {i: int(np.argmin([np.linalg.norm(e[1:] - c[1:]) for c in cents])) for i, e in enumerate(exp)}
                pos = sum(np.linalg.norm(e[1:] - cents[m[i]][1:]) for i, e in enumerate(exp)) / len(exp)
                vol = sum(abs(np.log(max(blob_vol[m[i]], 1e-6) / true_vol[i])) for i in m) / len(m)
                cands.append((pos, vol, m))
    pos_best = min(c[0] for c in cands)
    best = min((c for c in cands if c[0] <= pos_best + 1.0), key=lambda c: c[1])
    match = best[2]
    big = cents[match[int(np.argmax(true_vol))]]
    zz, yy, xx = np.indices(h.shape)
    core = ((zz - big[0]) * sp[0]) ** 2 + ((yy - big[1]) * sp[1]) ** 2 + ((xx - big[2]) * sp[2]) ** 2 < 2.0 ** 2
    hu_nod = float(np.median(img["real"][core]))
    thr = 0.5 * (hu_lung + hu_nod)
    for i in range(len(NODULES)):
        d, shape = NODULES[i]
        cv = cents[match[i]]
        # Technique B: voxelise the same SH model on the recon grid with partial volume, PSF-blur, add
        hb = np.ceil((d / 2 * 1.6 + 4 * psf_zyx.max() + 1) / sp).astype(int)
        lo = np.floor(cv).astype(int) - hb
        box = tuple(slice(max(a, 0), min(a + 2 * b + 1, n)) for a, b, n in zip(lo, hb, h.shape))
        shp = tuple(b.stop - b.start for b in box)
        f = sh_fraction(shp, sp, cv - [b.start for b in box], coefs[i], 3, ss=4)
        delta = ndi.gaussian_filter(f * (hu_nod - hu_lung), psf_zyx / sp)
        imgB[box] += delta
        half = np.ceil(8 / sp).astype(int)
        v = {k: segment_volume(im, cv, thr, vox_mm3, half) for k, im in
             (("real", img["real"]), ("A", img["techA"]), ("B", imgB))}
        rows.append({"d_mm": d, "shape": shape, "true_mm3": true_vol[i], "real_mm3": v["real"],
                     "A_mm3": v["A"], "B_mm3": v["B"],
                     "PD_A_pct": 100 * (v["A"] - v["real"]) / v["real"],
                     "PD_B_pct": 100 * (v["B"] - v["real"]) / v["real"], "center_vox": [float(x) for x in cv]})
    pdA = np.array([r["PD_A_pct"] for r in rows])
    pdB = np.array([r["PD_B_pct"] for r in rows])
    summary = {"coregistration_px": float(best[0]), "volume_log_mismatch": float(best[1]), "hu_lung": hu_lung, "hu_nodule": hu_nod, "threshold": thr, "psf_sigma_mm_zyx": psf_zyx.tolist(),
               "mtf_f50": psf["f50_cyc_per_mm"], "PD_A_mean": float(pdA.mean()), "PD_A_sd": float(pdA.std(ddof=1)),
               "PD_B_mean": float(pdB.mean()), "PD_B_sd": float(pdB.std(ddof=1)), "nodules": rows}
    (run.path / "r16_results.json").write_text(json.dumps(summary, indent=1) + "\n")

    fig, axs = plt.subplots(3, len(NODULES) + 1, figsize=(2.1 * (len(NODULES) + 1), 6.6), dpi=110,
                            gridspec_kw={"width_ratios": [1] * len(NODULES) + [1.6]})
    for j, r in enumerate(rows):
        c = np.round(r["center_vox"]).astype(int)
        w = int(9 / px)
        for i, (nm, im) in enumerate((("real", img["real"]), ("A (proj.)", img["techA"]), ("B (image)", imgB))):
            axs[i, j].imshow(im[c[0], c[1] - w:c[1] + w, c[2] - w:c[2] + w], cmap="gray", vmin=-1100, vmax=200)
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            if j == 0:
                axs[i, j].set_ylabel(nm, fontsize=8)
        axs[0, j].set_title(f"{r['d_mm']:.0f} mm {r['shape']}", fontsize=7)
    for i in range(3):
        axs[i, -1].axis("off")
    ax = fig.add_subplot(1, len(NODULES) + 1, len(NODULES) + 1)
    x = np.arange(len(rows))
    ax.bar(x - 0.2, pdA, 0.4, label="A projection")
    ax.bar(x + 0.2, pdB, 0.4, label="B image")
    ax.axhspan(-3, 3, color="0.9", zorder=0, label="±3 % (F02)")
    ax.set_xticks(x, [f"{r['d_mm']:.0f}{r['shape'][0]}" for r in rows], fontsize=7)
    ax.set_ylabel("volume PD vs real (%)", fontsize=8)
    ax.legend(fontsize=7)
    fig.suptitle(f"#16 simulated (XCIST, Definition-like): PD_A = {pdA.mean():+.2f} ± {pdA.std(ddof=1):.2f} %, "
                 f"PD_B = {pdB.mean():+.2f} ± {pdB.std(ddof=1):.2f} %  · paper [F02] B −0.28 … +0.57 %, A −2.24 … −1.01 %",
                 fontsize=8)
    fig.tight_layout()
    fig_path = fio.F_DIR / "figures" / "r16-projection-vs-image.png"
    fig.savefig(fig_path)
    agree = "agree (|PD| < 3 %)" if abs(pdA.mean()) < 3 and abs(pdB.mean()) < 3 else "disagree (|PD| ≥ 3 %)"
    set_reproduced(16, "adapted" if agree.startswith("agree") else "dissected", {
        "quantity": "volume percent difference of inserted vs physically present nodules (F02 Table 4)",
        "paper_value": "Technique B −0.28 … +0.57 % (one protocol −2.28 %); Technique A −2.24 … −1.01 %",
        "our_value": f"B {pdB.mean():+.2f} ± {pdB.std(ddof=1):.2f} %; A {pdA.mean():+.2f} ± {pdA.std(ddof=1):.2f} % "
                     f"(6 nodules, XCIST synthetic phantom)",
        "unit": "%", "agreement": agree + "; simulated XCIST phantom, not the physical KYOTO phantom",
        "sim_mode": "n/a", "figure": "figures/r16-projection-vs-image.png"}, ["figures/r16-projection-vs-image.png"])
    run.finish(f"PD_A {pdA.mean():+.2f}±{pdA.std(ddof=1):.2f} %, PD_B {pdB.mean():+.2f}±{pdB.std(ddof=1):.2f} %")
    print(json.dumps({k: v for k, v in summary.items() if k != "nodules"}, indent=1))
    for r in rows:
        print(f"{r['d_mm']:4.0f} {r['shape']:9s} true {r['true_mm3']:7.1f} real {r['real_mm3']:7.1f} "
              f"A {r['A_mm3']:7.1f} ({r['PD_A_pct']:+.2f} %)  B {r['B_mm3']:7.1f} ({r['PD_B_pct']:+.2f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
