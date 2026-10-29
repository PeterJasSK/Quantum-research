"""#14 Lesion-model fitting on LIDC: per-type shape, edge-profile and HU parameters — no voxels leave.

Per nodule (≥ 3 readers, 50 % consensus mask, Ø ≥ 6 mm):
  shape  r(θ, φ) = Σ_{l ≤ lmax} Σ_m a_lm Y_lm(θ, φ)        real spherical harmonics, least squares on the
         marching-cubes surface (Ambrosini [F01] eq. 1); power P_l = Σ_m a_lm² / a_00²; sphericity
         ψ = π^{1/3} (6V)^{2/3} / A; d_eq = (6V/π)^{1/3}
  edge   I(d) = bg + Δ · ½ erfc((d − d0) / (√2 σ_obs))    d = signed distance to the mask surface (mm),
         binned medians (Solomon–Samei-style erf edge). Intrinsic σ = √(σ_obs² − σ_psf²), σ_psf from the
         host scan's own fingerprint (#15), direction-averaged √((2σxy² + σz²)/3)
  HU     interior (d < −max(1 mm, 2σ_obs)) median; texture σ = √(σ_MAD² − σ_noise²), σ_noise from the σ map
  repro  [F01] §3: SH (lmax = 3) reconstruction → partial-volume voxelised, PSF-blurred simulated nodule
         → 3-D correlation coefficient with the real nodule (paper: 0.8897 ± 0.0609, 17 nodules 8–20 mm)

    python -m F_render.src.lesion_fit --lidc 20 [--out F_render/library/lesion_model_library.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import curve_fit
from scipy.special import erfc, sph_harm_y
from skimage import measure

from F_render.src import fingerprint as ffp
from F_render.src import host_masks as fhm
from F_render.src import io as fio
from F_render.src import lidc
from shared.runrecord import start_run

TYPES = ("solid", "part-solid", "ground-glass")


# ---------------------------------------------------------------- spherical harmonics
def real_sh(l: int, m: int, theta, phi):
    """Orthonormal real spherical harmonic; θ polar, φ azimuth."""
    if m == 0:
        return sph_harm_y(l, 0, theta, phi).real
    y = sph_harm_y(l, abs(m), theta, phi)
    return np.sqrt(2) * (-1) ** m * (y.real if m > 0 else y.imag)


def lm_list(lmax: int):
    return [(l, m) for l in range(lmax + 1) for m in range(-l, l + 1)]


def to_sph(p):
    r = np.linalg.norm(p, axis=1)
    theta = np.arccos(np.clip(p[:, 0] / np.maximum(r, 1e-12), -1, 1))   # polar about the z axis (index 0)
    phi = np.arctan2(p[:, 1], p[:, 2])
    return r, theta, phi


def fit_sh(points_mm_zyx, center_mm_zyx, lmax: int) -> np.ndarray:
    r, th, ph = to_sph(points_mm_zyx - center_mm_zyx)
    A = np.stack([real_sh(l, m, th, ph) for l, m in lm_list(lmax)], 1)
    coef, *_ = np.linalg.lstsq(A, r, rcond=None)
    return coef


def sh_radius(coef, theta, phi, lmax: int):
    return sum(c * real_sh(l, m, theta, phi) for c, (l, m) in zip(coef, lm_list(lmax)))


def sh_power(coef, lmax: int) -> list[float]:
    a00 = coef[0] ** 2
    return [float(sum(c ** 2 for c, (l, _) in zip(coef, lm_list(lmax)) if l == L) / a00) for L in range(1, lmax + 1)]


def sh_fraction(shape_zyx, sp_zyx, center_vox_zyx, coef, lmax: int, ss: int = 3) -> np.ndarray:
    """Partial-volume occupancy of the SH solid on a voxel grid (ss³ sub-samples per voxel)."""
    sp = np.asarray(sp_zyx, float)
    sub = (np.arange(ss) + 0.5) / ss - 0.5
    acc = np.zeros(shape_zyx, np.float32)
    base = np.indices(shape_zyx, dtype=np.float64).reshape(3, -1).T
    for dz in sub:
        for dy in sub:
            for dx in sub:
                p = (base + [dz, dy, dx] - center_vox_zyx) * sp
                r, th, ph = to_sph(p)
                acc += (r <= sh_radius(coef, th, ph, lmax)).reshape(shape_zyx)
    return acc / ss ** 3


# ---------------------------------------------------------------- edge
def erf_edge(d, bg, delta, d0, s):
    return bg + delta * 0.5 * erfc((d - d0) / (np.sqrt(2) * s))


def signed_distance(mask, sp):
    return ndi.distance_transform_edt(~mask, sampling=sp) - ndi.distance_transform_edt(mask, sampling=sp)


def fit_edge(roi_hu, d, bin_mm=0.25, span=(-4.0, 6.0)):
    edges = np.arange(span[0], span[1] + 1e-9, bin_mm)
    idx = np.digitize(d.ravel(), edges) - 1
    v = roi_hu.ravel().astype(float)
    xs, ys = [], []
    for i in range(len(edges) - 1):
        sel = idx == i
        if sel.sum() >= 3:
            xs.append(0.5 * (edges[i] + edges[i + 1]))
            ys.append(np.median(v[sel]))
    xs, ys = np.array(xs), np.array(ys)
    p0 = [ys[-3:].mean(), ys[:3].mean() - ys[-3:].mean(), 0.0, 1.0]
    (bg, delta, d0, s), _ = curve_fit(erf_edge, xs, ys, p0=p0, maxfev=20000)
    return {"bg": float(bg), "delta": float(delta), "d0": float(d0), "sigma_obs_mm": abs(float(s))}


# ---------------------------------------------------------------- per nodule
def fit_nodule(hu, mask, sp, sigma_psf_eff, sigma_noise, psf_zyx, lmax=4, repro_lmax=3) -> dict:
    sp = np.asarray(sp, float)
    m = mask.astype(bool)
    vol_mm3 = float(m.sum() * sp.prod())
    verts, faces, *_ = measure.marching_cubes(np.pad(m, 1).astype(np.float32), 0.5, spacing=tuple(sp))
    verts -= sp            # undo the 1-voxel pad
    area = float(measure.mesh_surface_area(verts, faces))
    c_vox = np.array(ndi.center_of_mass(m))
    c_mm = c_vox * sp
    coef = fit_sh(verts, c_mm, lmax)
    d = signed_distance(m, sp)
    edge = fit_edge(hu, d)
    inner = d < -max(1.0, 2 * edge["sigma_obs_mm"])      # clear of the partial-volume rim
    if inner.sum() < 10:
        inner = d < -1.0
    if inner.sum() < 10:
        inner = d < 0
    interior = hu[inner].astype(float)
    mad_std = 1.4826 * np.median(np.abs(interior - np.median(interior)))   # robust to calcification / bronchograms
    tex = float(np.sqrt(max(mad_std ** 2 - sigma_noise ** 2, 0.0)))
    rec = {
        "volume_mm3": vol_mm3,
        "d_eq_mm": float((6 * vol_mm3 / np.pi) ** (1 / 3)),
        "sphericity": float(np.pi ** (1 / 3) * (6 * vol_mm3) ** (2 / 3) / area),
        "sh_power": sh_power(coef, lmax),
        "hu_interior": float(np.median(interior)),
        "texture_std_hu": tex,
        "edge_sigma_obs_mm": edge["sigma_obs_mm"],
        "edge_sigma_mm": float(np.sqrt(max(edge["sigma_obs_mm"] ** 2 - sigma_psf_eff ** 2, 0.05 ** 2))),
        "edge_bg_hu": edge["bg"],
    }
    # [F01] reproduction: SH(lmax=3) simulated nodule vs the real one, 3-D correlation coefficient
    coef3 = fit_sh(verts, c_mm, repro_lmax)
    frac = sh_fraction(hu.shape, sp, c_vox, coef3, repro_lmax)
    sim = edge["bg"] + (rec["hu_interior"] - edge["bg"]) * frac
    sim = ndi.gaussian_filter(sim, np.asarray(psf_zyx) / sp)
    roi = ndi.binary_dilation(m, iterations=2)
    rec["f01_corr3d"] = float(np.corrcoef(sim[roi], hu[roi].astype(float))[0, 1])
    return rec


def fit_scan(rec_sel: dict) -> list[dict]:
    import pylidc as pl

    lidc.configure_pylidc()
    scan = pl.query(pl.Scan).filter(pl.Scan.series_instance_uid == rec_sel["series_uid"]).first()
    hu, sp_xyz, _ = lidc.load_scan(scan)
    sp = np.asarray(sp_xyz[::-1], float)
    masks = fhm.make_masks(hu, sp)
    rng = ffp.seeded_rng(ffp.FINGERPRINT_SEED, "F.fingerprint")
    psf = ffp.estimate_psf(hu, masks["body"], masks["lungs"], sp, rng, slice_thickness_mm=scan.slice_thickness)
    nps = ffp.estimate_nps(hu, masks["body"], sp)
    sig_map, _ = ffp.estimate_sigma_map(hu, masks["body"], sp, nps["freq"], nps["nps"])
    sxy, sz = psf["sigma_xy_mm"], psf["sigma_z_mm"]
    s_eff = float(np.sqrt((2 * sxy ** 2 + sz ** 2) / 3))
    out = []
    for nd, mask, bbox in lidc.nodule_masks(scan):
        roi = hu[bbox]
        c = np.round(ndi.center_of_mass(mask)).astype(int)
        sig_n = float(sig_map[bbox][tuple(c)]) or float(np.median(sig_map[sig_map > 0]))
        try:
            r = fit_nodule(roi, mask, sp, s_eff, sig_n, (sz, sxy, sxy))
        except (RuntimeError, ValueError) as e:     # curve_fit failure / degenerate mesh
            print(f"  skip {nd.patient_id} nodule {nd.index}: {e}")
            continue
        r.update({"patient_id": nd.patient_id, "nodule": nd.index, "type": nd.type, "texture_rating": nd.texture,
                  "n_readers": nd.n_readers, "psf_sigma_mm_zyx": [sz, sxy, sxy], "sigma_noise_hu": sig_n})
        out.append(r)
    return out


def aggregate(nodules: list[dict]) -> dict:
    types = {}
    for t in TYPES:
        rs = [r for r in nodules if r["type"] == t]
        if not rs:
            continue
        P = np.array([r["sh_power"] for r in rs])
        g = lambda k: np.array([r[k] for r in rs], float)   # noqa: E731
        shape = {"sphericity_mean": g("sphericity").mean(), "sphericity_std": g("sphericity").std(),
                 "d_eq_mm_min": g("d_eq_mm").min(), "d_eq_mm_max": g("d_eq_mm").max(),
                 "d_eq_mm_mean": g("d_eq_mm").mean(),
                 "texture_std_hu_mean": g("texture_std_hu").mean(), "texture_std_hu_std": g("texture_std_hu").std()}
        for L in range(P.shape[1]):
            shape[f"sh_l{L + 1}_power_mean"] = P[:, L].mean()
            shape[f"sh_l{L + 1}_power_std"] = P[:, L].std()
        types[t] = {
            "shape_params": {k: round(float(v), 6) for k, v in shape.items()},
            "edge_profile": {"model": "erf", "params": {
                "sigma_mm_mean": round(float(g("edge_sigma_mm").mean()), 4),
                "sigma_mm_std": round(float(g("edge_sigma_mm").std()), 4),
                "sigma_obs_mm_mean": round(float(g("edge_sigma_obs_mm").mean()), 4),
                "bg_hu_mean": round(float(g("edge_bg_hu").mean()), 2)}},
            "hu": {"mean": round(float(g("hu_interior").mean()), 2), "std": round(float(g("hu_interior").std()), 2)},
            "n_fitted": len(rs),
        }
    return types


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lidc", type=int, default=20, help="number of scans from the deterministic selection")
    ap.add_argument("--out", default=str(fio.FITTED_LIBRARY))
    a = ap.parse_args(argv)
    sel_file = lidc.LIDC_ROOT / "f_render_selection.json"
    sel = json.loads(sel_file.read_text())[: a.lidc] if sel_file.exists() else lidc.select_scans(a.lidc)
    run = start_run("F_render", "lesion-fit", tool="F_render.src.lesion_fit")
    nodules = []
    for i, rec in enumerate(sel, 1):
        rs = fit_scan(rec)
        print(f"[{i}/{len(sel)}] {rec['patient_id']}: {len(rs)} nodules "
              f"{sorted({r['type'] for r in rs})}", flush=True)
        nodules += rs
    # parameters only (scalars per nodule) — the privacy-safe audit table, kept in the gitignored run dir
    (run.path / "nodules.json").write_text(json.dumps(nodules, indent=1) + "\n")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fio.envelope("lesion_model_library", "F_render.src.lesion_fit", run.code_hash, run.path.name, [])
    doc.update({"source": "LIDC fitted parameters (no voxels)", "types": aggregate(nodules)})
    fio.write_manifest(out, doc)
    run.add_output(out, "lesion_model_library")
    run.finish(f"{len(nodules)} nodules from {len(sel)} LIDC scans; per-type n = "
               + ", ".join(f"{t}:{v['n_fitted']}" for t, v in doc["types"].items()))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
