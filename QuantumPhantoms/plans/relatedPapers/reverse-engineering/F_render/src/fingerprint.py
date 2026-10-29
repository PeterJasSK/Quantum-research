"""#15 Scanner fingerprint: the host scan's own resolution and noise, measured from the patient.

* MTF in-plane — Sanders/Hurwitz/Samei 2016 idea: the air–skin boundary is a natural edge. Pixels in a
  thin strip along each outward body normal are binned by their projected distance to the strip's own
  sub-pixel edge position (no interpolation blur) → oversampled ESF → LSF → |FFT| = MTF.
* PSF z — the same strip method across lung/soft-tissue boundaries whose normal is along z
  (diaphragm dome, apex); fallback slice_thickness / 2.355 when too few strips (recorded).
* NPS — detrended uniform soft-tissue ROIs (single realisation), radial average; per-ROI curves are
  the local NPS patches (CR-F1, written to local_nps.npz).
* σ map — high-pass residual variance by normalised convolution over flat voxels, divided by the
  fraction of noise power the high-pass keeps (computed from the measured NPS).

    python -m F_render.src.fingerprint --masks <anatomy_masks.json> --out <dir>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import curve_fit

from F_render.src import io as fio
from F_render.src import noise as fnoise
from shared.runrecord import start_run
from shared.seedhash import rng as seeded_rng
from shared.volumes import save_npz, write_volume

FINGERPRINT_SEED = "f0" * 32   # sampling of boundary points only; not part of any tumor's seed chain


def _gauss(x, a, mu, s):
    return a * np.exp(-0.5 * ((x - mu) / s) ** 2)


def _strip_esf(vol, pts, normals, offsets, sp, half_mm, halfwidth_mm, min_contrast):
    """Oversampled ESF samples (s − s0, f) from strips along `normals` at boundary points `pts`.

    f is the strip value normalised to inside = 1, outside = 0; s is mm along the outward normal.
    """
    shape = np.array(vol.shape)
    off_mm = offsets * sp
    s_all, f_all, n_ok = [], [], 0
    bins = np.arange(-half_mm, half_mm + 1e-9, 0.5 * sp.min())
    for p, n in zip(pts, normals):
        s = off_mm @ n
        perp = np.linalg.norm(off_mm - s[:, None] * n[None, :], axis=1)
        keep = (np.abs(s) <= half_mm) & (perp <= halfwidth_mm)
        q = p + offsets[keep]
        inb = np.all((q >= 0) & (q < shape), axis=1)
        q, s = q[inb], s[keep][inb]
        if len(s) < 8:
            continue
        v = vol[q[:, 0], q[:, 1], q[:, 2]].astype(float)
        vin, vout = v[s < -0.4 * half_mm], v[s > 0.4 * half_mm]
        if len(vin) < 4 or len(vout) < 4:
            continue
        lo, hi = np.median(vout), np.median(vin)
        c = abs(hi - lo)   # inside may be darker (lung) or brighter (body) than outside
        if c < min_contrast or vin.std() > 0.25 * c or vout.std() > 0.25 * c:
            continue
        f = (v - lo) / (hi - lo)
        idx = np.digitize(s, bins) - 1
        fb = np.array([f[idx == i].mean() if np.any(idx == i) else np.nan for i in range(len(bins) - 1)])
        fb = np.where(np.isnan(fb), np.interp(np.arange(len(fb)), np.flatnonzero(~np.isnan(fb)),
                                              fb[~np.isnan(fb)]), fb)
        s0 = float(np.clip(fb, 0, 1).sum() * (bins[1] - bins[0]) - half_mm)
        s_all.append(s - s0)
        f_all.append(f)
        n_ok += 1
    if not s_all:
        return np.array([]), np.array([]), 0
    return np.concatenate(s_all), np.concatenate(f_all), n_ok


def _lsf_mtf(s, f, bin_mm, half_mm):
    edges = np.arange(-half_mm, half_mm + 1e-9, bin_mm)
    idx = np.digitize(s, edges) - 1
    ok = (idx >= 0) & (idx < len(edges) - 1)
    cnt = np.bincount(idx[ok], minlength=len(edges) - 1)
    esf = np.bincount(idx[ok], f[ok], len(edges) - 1) / np.maximum(cnt, 1)
    good = cnt > 0
    x = 0.5 * (edges[1:] + edges[:-1])
    esf = np.interp(x, x[good], esf[good])
    esf = ndi.uniform_filter1d(esf, 3)
    lsf = -np.gradient(esf, bin_mm)
    npad = 4 * len(lsf)   # zero-pad: finer frequency sampling for f50 (resolution itself is set by half_mm)
    mtf = np.abs(np.fft.rfft(lsf * np.hanning(len(lsf)), npad))
    mtf /= mtf[0] if mtf[0] > 0 else 1.0
    freq = np.fft.rfftfreq(npad, bin_mm)
    try:
        (a, mu, sig), _ = curve_fit(_gauss, x, lsf, p0=[lsf.max(), 0.0, 1.0], maxfev=5000)
        sig = abs(float(sig))
    except RuntimeError:
        sig = float("nan")
    return x, esf, lsf, freq, mtf, sig


def _boundary_points(mask, rng, n, z_keep=None):
    bnd = mask & ~ndi.binary_erosion(mask)
    if z_keep is not None:
        bnd[~z_keep] = False
    pts = np.argwhere(bnd)
    if len(pts) > n:
        pts = pts[np.sort(rng.choice(len(pts), n, replace=False))]
    return pts


def estimate_psf(host, body, lungs, sp, rng, n_points=3000, half_mm=8.0, slice_thickness_mm=None):
    """In-plane MTF + σ (air–skin), z σ (lung/tissue with z-normal). Returns dict."""
    sp = np.asarray(sp, float)
    nz = host.shape[0]
    zk = np.zeros(nz, bool)
    zk[int(0.1 * nz):max(int(0.9 * nz), int(0.1 * nz) + 1)] = True
    zk3 = np.broadcast_to(zk[:, None, None], host.shape)

    # in-plane: 2-D normals from the smoothed body mask, strips at the same z
    bm = ndi.gaussian_filter(body.astype(np.float32), (0, 1.5, 1.5))
    gy, gx = np.gradient(bm, sp[1], sp[2], axis=(1, 2))
    pts = _boundary_points(body.astype(bool), rng, n_points, zk3)
    nrm = np.stack([np.zeros(len(pts)), -gy[tuple(pts.T)], -gx[tuple(pts.T)]], 1)
    nn = np.linalg.norm(nrm, axis=1)
    pts, nrm = pts[nn > 0], nrm[nn > 0] / nn[nn > 0, None]
    H = int(np.ceil(half_mm / sp[1:].min()))
    oy, ox = np.mgrid[-H:H + 1, -H:H + 1]
    off2 = np.stack([np.zeros(oy.size, int), oy.ravel(), ox.ravel()], 1)
    s, f, n_xy = _strip_esf(host, pts, nrm, off2, sp, half_mm, 0.75 * sp[1:].max(), 500.0)
    out = {"n_strips_xy": int(n_xy)}
    if n_xy < 20:
        raise RuntimeError(f"only {n_xy} usable air–skin strips; cannot estimate the in-plane MTF")
    x, esf, lsf, freq, mtf, sig_xy = _lsf_mtf(s, f, 0.1 * sp[2], half_mm)
    nyq = 0.5 / sp[1:].min()
    keep = freq <= nyq + 1e-9
    out.update({"mtf_freq": freq[keep], "mtf": mtf[keep], "sigma_xy_mm": sig_xy, "esf_x": x, "esf": esf,
                "lsf": lsf})
    if np.any(mtf < 0.5):
        i = int(np.argmax(mtf < 0.5))
        f50 = freq[i - 1] + (mtf[i - 1] - 0.5) / (mtf[i - 1] - mtf[i]) * (freq[i] - freq[i - 1])
    else:
        f50 = float("nan")
    out["f50_cyc_per_mm"] = float(f50)

    # z: lung boundary voxels whose 3-D normal is along z
    sigma_z, z_method = float("nan"), None
    if lungs is not None and lungs.any():
        lm = ndi.gaussian_filter((lungs > 0).astype(np.float32), 1.5)
        g = np.stack(np.gradient(lm, *sp), 0)
        pts = _boundary_points(lungs > 0, rng, 4 * n_points)
        nrm = -g[:, pts[:, 0], pts[:, 1], pts[:, 2]].T
        nn = np.linalg.norm(nrm, axis=1)
        sel = (nn > 0) & (np.abs(nrm[:, 0]) > 0.9 * np.maximum(nn, 1e-12))
        pts, nrm = pts[sel], nrm[sel] / nn[sel, None]
        Hz = int(np.ceil(half_mm / sp[0]))
        oz, oy, ox = np.mgrid[-Hz:Hz + 1, -1:2, -1:2]
        off3 = np.stack([oz.ravel(), oy.ravel(), ox.ravel()], 1)
        s, f, n_z = _strip_esf(host, pts, nrm, off3, sp, half_mm, 1.0 * sp[1:].max(), 400.0)
        out["n_strips_z"] = int(n_z)
        if n_z >= 20:
            *_, sigma_z = _lsf_mtf(s, f, 0.1 * sp[0], half_mm)
            z_method = "lung/soft-tissue z-edges"
    if not np.isfinite(sigma_z):
        st = slice_thickness_mm or sp[0]
        sigma_z, z_method = st / 2.355, f"fallback: slice thickness {st} mm / 2.355"
    out.update({"sigma_z_mm": float(sigma_z), "z_method": z_method})
    return out


def estimate_nps(host, body, sp, roi_mm=24.0, slice_step=4, max_rois=400):
    """Global + per-ROI radial NPS from detrended soft-tissue ROIs (single realisation)."""
    sp = np.asarray(sp, float)
    n = max(int(round(roi_mm / sp[2])), 8)
    sm = ndi.gaussian_filter(host.astype(np.float32), (0, 2, 2))
    soft = ndi.binary_erosion(body.astype(bool), iterations=max(int(10 / sp[2]), 1)) & (sm > -150) & (sm < 150)
    rois, centers = [], []
    for z in range(0, host.shape[0], slice_step):
        s2 = soft[z]
        if not s2.any():
            continue
        for y in range(0, host.shape[1] - n, n):
            for x in range(0, host.shape[2] - n, n):
                if s2[y:y + n, x:x + n].all():
                    rois.append(fnoise.detrend2(host[z, y:y + n, x:x + n].astype(float)))
                    centers.append((z, y + n // 2, x + n // 2))
    if len(rois) > max_rois:
        pick = np.linspace(0, len(rois) - 1, max_rois).astype(int)
        rois, centers = [rois[i] for i in pick], [centers[i] for i in pick]
    if not rois:
        f = np.linspace(0, 0.5 / sp[2], 8)
        return {"freq": f, "nps": np.zeros_like(f), "patches": np.zeros((0, 8), np.float32),
                "centers": np.zeros((0, 3), np.int32), "n_rois": 0, "roi_px": n}
    freq, glob = fnoise.radial(fnoise.nps2d(rois, sp[2], sp[1]), sp[2], sp[1])
    patches = np.stack([fnoise.radial(fnoise.nps2d([r], sp[2], sp[1]), sp[2], sp[1])[1] for r in rois])
    return {"freq": freq, "nps": glob, "patches": patches.astype(np.float32),
            "centers": np.array(centers, np.int32), "n_rois": len(rois), "roi_px": n}


def estimate_sigma_map(host, body, sp, nps_freq, nps_vals, hp_sigma_px=1.5, window_mm=10.0, flat_hu_per_mm=15.0):
    """Local noise σ (HU, float32) from the in-plane high-pass residual, corrected for the HP gain."""
    sp = np.asarray(sp, float)
    v = host.astype(np.float32)
    r = v - ndi.gaussian_filter(v, (0, hp_sigma_px, hp_sigma_px))
    sm = ndi.gaussian_filter(v, (0.5, 2, 2))
    g = np.sqrt(sum(d ** 2 for d in np.gradient(sm, *sp)))
    # structure (edges and their curved tails) leaks into the high-pass: keep only voxels ≥ 2 px from any edge
    flat = (body > 0) & ~ndi.binary_dilation(g >= flat_hu_per_mm, iterations=2)
    w = window_mm / sp
    num = ndi.gaussian_filter(np.where(flat, r * r, 0).astype(np.float32), w)
    den = ndi.gaussian_filter(flat.astype(np.float32), w)
    var = num / np.maximum(den, 1e-6)
    # fraction k² of noise power that survives (1 − G): from the measured NPS (white if NPS is empty)
    n = 64
    u = np.fft.fftfreq(n)
    U = np.hypot(*np.meshgrid(u, u, indexing="ij"))
    G = np.exp(-2 * np.pi ** 2 * hp_sigma_px ** 2 * U ** 2)
    nps2 = fnoise.nps_from_radial((n, n), sp[2], sp[1], nps_freq, nps_vals)
    k2 = float((nps2 * (1 - G) ** 2).sum() / nps2.sum()) if nps2.sum() > 0 else float(((1 - G) ** 2).mean())
    sigma = np.sqrt(np.maximum(var, 0) / k2)
    sigma[(body == 0) | (den < 1e-3)] = 0.0
    return sigma.astype(np.float32), k2


def estimate(host, body, lungs, sp, slice_thickness_mm=None, seed_hex=FINGERPRINT_SEED) -> dict:
    rng = seeded_rng(seed_hex, "F.fingerprint")
    psf = estimate_psf(host, body, lungs, sp, rng, slice_thickness_mm=slice_thickness_mm)
    nps = estimate_nps(host, body, sp)
    sigma, k2 = estimate_sigma_map(host, body, sp, nps["freq"], nps["nps"])
    return {"psf": psf, "nps": nps, "sigma_map": sigma, "hp_gain_k2": k2}


def write(fp: dict, host_scan_id: str, meta: dict, out_dir: Path, masks_path: Path, code_hash: str,
          run_id: str | None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    sig_p = write_volume(out_dir / "sigma_map.nii.gz", fp["sigma_map"], meta["spacing_mm_xyz"], meta["origin_mm_lps"])
    nps = fp["nps"]
    lnps_p = save_npz(out_dir / "local_nps.npz", nps_patches=nps["patches"], patch_centers_zyx=nps["centers"],
                      freq_cyc_per_mm=np.asarray(nps["freq"], np.float64),
                      spacing_mm_xyz=np.asarray(meta["spacing_mm_xyz"], np.float64))
    man = out_dir / "scanner_fingerprint.json"
    psf = fp["psf"]
    doc = fio.envelope("scanner_fingerprint", "F_render.src.fingerprint", code_hash, run_id,
                       [fio.up_ref("anatomy_masks", masks_path, man)])
    doc.update({
        "host_scan_id": host_scan_id,
        "mtf": {"freq_cyc_per_mm": [round(float(v), 5) for v in psf["mtf_freq"]],
                "values": [round(float(max(v, 0.0)), 5) for v in psf["mtf"]]},
        "psf_sigma_mm_zyx": [round(float(psf["sigma_z_mm"]), 4), round(float(psf["sigma_xy_mm"]), 4),
                             round(float(psf["sigma_xy_mm"]), 4)],
        "nps": {"freq_cyc_per_mm": [round(float(v), 5) for v in nps["freq"]],
                "values": [round(float(max(v, 0.0)), 5) for v in nps["nps"]]},
        "sigma_map": fio.file_ref(sig_p, man),
    })
    fio.write_manifest(man, doc)
    (out_dir / "local_nps.ref.json").write_text(
        __import__("json").dumps({"local_nps": fio.file_ref(lnps_p, man), "contract_change_request": "CR-F1"}) + "\n")
    return man


def summary(fp: dict) -> str:
    p, n = fp["psf"], fp["nps"]
    return (f"MTF f50={p['f50_cyc_per_mm']:.3f} cyc/mm  σxy={p['sigma_xy_mm']:.3f} mm  σz={p['sigma_z_mm']:.3f} mm "
            f"({p['z_method']})  strips xy={p['n_strips_xy']} z={p.get('n_strips_z', 0)}  "
            f"NPS rois={n['n_rois']} σ_NPS={fnoise.sigma_of(n['freq'], n['nps']):.1f} HU  "
            f"σ-map median(body)={float(np.median(fp['sigma_map'][fp['sigma_map'] > 0])) if (fp['sigma_map'] > 0).any() else 0:.1f} HU")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masks", default=str(fio.STUB["masks"]), help="anatomy_masks.json (host_ct, body, lungs)")
    ap.add_argument("--out", default=None, help="output dir (default: the run dir)")
    ap.add_argument("--slice-thickness", type=float, default=None)
    a = ap.parse_args(argv)
    masks, mp = fio.load(a.masks, "anatomy_masks")
    vols = fio.host_volumes(masks, mp)
    meta = vols["meta"]
    sp = meta["spacing_mm_xyz"][::-1]
    run = start_run("F_render", "fingerprint", tool="F_render.src.fingerprint")
    run.add_input(mp, "anatomy_masks")
    fp = estimate(vols["host_ct"], vols["body"], vols.get("lungs"), sp, a.slice_thickness)
    out = Path(a.out) if a.out else run.path
    man = write(fp, masks["host_scan_id"], meta, out, mp, run.code_hash, run.path.name)
    run.add_output(man, "scanner_fingerprint")
    run.finish(summary(fp))
    print(summary(fp))
    print(man)
    return 0


if __name__ == "__main__":
    sys.exit(main())
