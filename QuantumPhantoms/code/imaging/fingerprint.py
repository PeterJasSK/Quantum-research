"""F5 — scanner fingerprint of the host scan: its own resolution and noise, measured from the patient.

* MTF in-plane — Sanders/Hurwitz/Samei 2016 idea: the air–skin boundary is a natural edge. Pixels in a
  thin strip along each outward body normal are binned by their projected distance to the strip's own
  sub-pixel edge position → oversampled ESF → LSF → |FFT| = MTF; Gaussian LSF fit → in-plane PSF σ.
* PSF z — the same strip method across lung/soft-tissue boundaries whose normal is along z;
  fallback slice_thickness / 2.355 when too few strips (recorded).
* NPS — detrended uniform soft-tissue ROIs (single realisation), radial average.

Result (JSON, cached next to the host as fingerprint.json):
    {psf_sigma_mm_zyx, noise_sigma_hu, nps{freq_cyc_per_mm, values}, mtf{…}, f50_cyc_per_mm, method,
     plausibility{…}}
There is no RE reference for a Siemens host, so `plausibility` checks the numbers against broad CT ranges
(F5 plan AC-2) instead of a reproduced value.
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/fingerprint.py @ 2609cbe
# (_gauss, _strip_esf, _lsf_mtf, _boundary_points, estimate_psf, estimate_nps, the JSON mapping of write());
# dropped: estimate_sigma_map (only feeds the σ-map volume, unused by the insert), NIfTI/npz writing,
# contract envelope, run record. Added: plausibility check, JSON cache, --fingerprint override loader.

from __future__ import annotations

import json
import os

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import curve_fit

from imaging import noise as fnoise
from imaging.seedhash import rng as seeded_rng

FINGERPRINT_SEED = "f0" * 32   # sampling of boundary points only; not part of any tumor's seed chain


def _gauss(x, a, mu, s):
    return a * np.exp(-0.5 * ((x - mu) / s) ** 2)


def _strip_esf(vol, pts, normals, offsets, sp, half_mm, halfwidth_mm, min_contrast):
    """Oversampled ESF samples (s − s0, f) from strips along `normals` at boundary points `pts`."""
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
    npad = 4 * len(lsf)
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
    out.update({"mtf_freq": freq[keep], "mtf": mtf[keep], "sigma_xy_mm": sig_xy})
    if np.any(mtf < 0.5):
        i = int(np.argmax(mtf < 0.5))
        f50 = freq[i - 1] + (mtf[i - 1] - 0.5) / (mtf[i - 1] - mtf[i]) * (freq[i] - freq[i - 1])
    else:
        f50 = float("nan")
    out["f50_cyc_per_mm"] = float(f50)

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
    """Global radial NPS from detrended soft-tissue ROIs (single realisation)."""
    sp = np.asarray(sp, float)
    n = max(int(round(roi_mm / sp[2])), 8)
    sm = ndi.gaussian_filter(host.astype(np.float32), (0, 2, 2))
    soft = ndi.binary_erosion(body.astype(bool), iterations=max(int(10 / sp[2]), 1)) & (sm > -150) & (sm < 150)
    rois = []
    for z in range(0, host.shape[0], slice_step):
        s2 = soft[z]
        if not s2.any():
            continue
        for y in range(0, host.shape[1] - n, n):
            for x in range(0, host.shape[2] - n, n):
                if s2[y:y + n, x:x + n].all():
                    rois.append(fnoise.detrend2(host[z, y:y + n, x:x + n].astype(float)))
    if len(rois) > max_rois:
        pick = np.linspace(0, len(rois) - 1, max_rois).astype(int)
        rois = [rois[i] for i in pick]
    if not rois:
        f = np.linspace(0, 0.5 / sp[2], 8)
        return {"freq": f, "nps": np.zeros_like(f), "n_rois": 0, "roi_px": n}
    freq, glob = fnoise.radial(fnoise.nps2d(rois, sp[2], sp[1]), sp[2], sp[1])
    return {"freq": freq, "nps": glob, "n_rois": len(rois), "roi_px": n}


def plausibility(fp: dict, slice_thickness_mm: float) -> dict:
    """Broad CT ranges (F5 plan AC-2): in-plane σ 0.4–1.5 mm, z σ 0.3–1.0 × thickness, noise σ 5–60 HU."""
    sz, sy, _ = fp["psf_sigma_mm_zyx"]
    t = slice_thickness_mm
    checks = {"sigma_xy_mm_in_0.4_1.5": bool(0.4 <= sy <= 1.5),
              "sigma_z_mm_in_0.3t_1.0t": bool(0.3 * t <= sz <= 1.0 * t),
              "noise_sigma_hu_in_5_60": bool(5.0 <= fp["noise_sigma_hu"] <= 60.0)}
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "FAIL"}


def estimate(host, body, lungs, sp, slice_thickness_mm=None, seed_hex=FINGERPRINT_SEED) -> dict:
    """Fingerprint dict in the JSON form the insert consumes (RE `write()` mapping)."""
    rng = seeded_rng(seed_hex, "F.fingerprint")
    psf = estimate_psf(host, body, lungs, sp, rng, slice_thickness_mm=slice_thickness_mm)
    nps = estimate_nps(host, body, sp)
    fp = {
        "psf_sigma_mm_zyx": [round(float(psf["sigma_z_mm"]), 4), round(float(psf["sigma_xy_mm"]), 4),
                             round(float(psf["sigma_xy_mm"]), 4)],
        "noise_sigma_hu": round(fnoise.sigma_of(nps["freq"], nps["nps"]), 2),
        "nps": {"freq_cyc_per_mm": [round(float(v), 5) for v in nps["freq"]],
                "values": [round(float(max(v, 0.0)), 5) for v in nps["nps"]]},
        "mtf": {"freq_cyc_per_mm": [round(float(v), 5) for v in psf["mtf_freq"]],
                "values": [round(float(max(v, 0.0)), 5) for v in psf["mtf"]]},
        "f50_cyc_per_mm": round(psf["f50_cyc_per_mm"], 4),
        "method": {"xy": f"air–skin edge, {psf['n_strips_xy']} strips", "z": psf["z_method"],
                   "nps": f"{nps['n_rois']} soft-tissue ROIs of {nps['roi_px']} px"},
    }
    fp["plausibility"] = plausibility(fp, slice_thickness_mm or float(sp[0]))
    return fp


def load_or_estimate(host, override: str | None = None, log=print) -> dict:
    """--fingerprint JSON (RE scanner_fingerprint.json or ours) > cached > freshly estimated."""
    if override:
        with open(override) as f:
            fp = json.load(f)
        if "noise_sigma_hu" not in fp:
            fp["noise_sigma_hu"] = round(fnoise.sigma_of(fp["nps"]["freq_cyc_per_mm"], fp["nps"]["values"]), 2)
        fp["source"] = f"override: {override}"
        log(f"  fingerprint: override ({override})")
        return fp
    from imaging.host import HOSTS_DIR

    path = os.path.join(HOSTS_DIR, host.host_id, "fingerprint.json")
    if os.path.isfile(path):
        with open(path) as f:
            fp = json.load(f)
        fp["source"] = "cached"
        return fp
    thick = float(host.meta.get("slice_thickness") or host.spacing_zyx[0])
    fp = estimate(host.hu, host.body, host.lungs, host.spacing_zyx, thick)
    with open(path, "w") as f:
        json.dump(fp, f, indent=2)
    fp["source"] = "estimated"
    log(f"  fingerprint {host.host_id}: PSF σ zyx {fp['psf_sigma_mm_zyx']} mm, noise σ {fp['noise_sigma_hu']} HU, "
        f"f50 {fp['f50_cyc_per_mm']} cyc/mm, plausibility {fp['plausibility']['verdict']}")
    return fp
