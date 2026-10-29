"""3-D ROI crop + 1 mm isotropic resampling, shell masks, radial edge profiles.

Shared by real (LIDC) and synthetic (hybrid) lesions so both go through identical geometry.
Arrays are (z, y, x); spacing/centres in the same order. Resampling is linear for CT, nearest for masks.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import curve_fit
from scipy.special import erf

ROI_MM = 48
EDGE_FACTOR = 2.563  # 10-90 % width of an erf edge = 2.563 sigma


def crop_iso(vol_zyx: np.ndarray, spacing_zyx, centre_vox_zyx, size_mm: int = ROI_MM,
             order: int = 1, cval: float = -1024.0) -> np.ndarray:
    """(size_mm,)*3 ROI at 1 mm isotropic centred on centre_vox (float voxel coords)."""
    ax = np.arange(size_mm) - (size_mm - 1) / 2.0
    zz, yy, xx = np.meshgrid(ax, ax, ax, indexing="ij")
    coords = np.stack([centre_vox_zyx[i] + g / spacing_zyx[i] for i, g in enumerate((zz, yy, xx))])
    return ndi.map_coordinates(vol_zyx.astype(np.float32), coords, order=order, mode="constant", cval=cval)


def crop_mask(mask_zyx: np.ndarray, spacing_zyx, centre_vox_zyx, size_mm: int = ROI_MM) -> np.ndarray:
    return crop_iso(mask_zyx.astype(np.uint8), spacing_zyx, centre_vox_zyx, size_mm, order=0, cval=0).astype(np.uint8)


def equivalent_diameter_mm(mask_1mm: np.ndarray) -> float:
    return float((6.0 * mask_1mm.sum() / np.pi) ** (1 / 3))


def eroded_interior(mask_1mm: np.ndarray, mm: int = 1) -> np.ndarray:
    return ndi.binary_erosion(mask_1mm.astype(bool), iterations=mm)


def shell(mask_1mm: np.ndarray, r_in: float = 10.0, r_out: float = 20.0) -> np.ndarray:
    d = ndi.distance_transform_edt(~mask_1mm.astype(bool))
    return (d >= r_in) & (d <= r_out)


def signed_distance(mask_1mm: np.ndarray) -> np.ndarray:
    m = mask_1mm.astype(bool)
    return ndi.distance_transform_edt(~m) - ndi.distance_transform_edt(m)


def _edge_model(x, lo, hi, x0, sig):
    return lo + (hi - lo) * 0.5 * (1.0 - erf((x - x0) / (np.sqrt(2) * sig)))


def edge_width(roi_1mm: np.ndarray, mask_1mm: np.ndarray) -> dict:
    """erf fit of the HU profile vs signed distance to the mask boundary -> sigma_mm and 10-90 % width."""
    sd = signed_distance(mask_1mm)
    sel = np.abs(sd) <= 8
    x = sd[sel]
    y = roi_1mm[sel]
    bins = np.arange(-8, 8.5, 1.0)
    idx = np.digitize(x, bins)
    xs = np.array([x[idx == k].mean() for k in range(1, len(bins)) if (idx == k).any()])
    ys = np.array([y[idx == k].mean() for k in range(1, len(bins)) if (idx == k).any()])
    if len(xs) < 6:
        return {"sigma_mm": float("nan"), "width_10_90_mm": float("nan")}
    try:
        p, _ = curve_fit(_edge_model, xs, ys, p0=[ys[-1], ys[0], 0.0, 1.0],
                         bounds=([-1100, -1100, -4, 0.2], [400, 400, 4, 6]))
        sig = float(p[3])
    except (RuntimeError, ValueError):
        return {"sigma_mm": float("nan"), "width_10_90_mm": float("nan")}
    return {"sigma_mm": sig, "width_10_90_mm": EDGE_FACTOR * sig}


def local_noise(roi_1mm: np.ndarray, region: np.ndarray) -> float:
    """Std of HU in region after removing a 3-D linear trend (low-frequency anatomy)."""
    if region.sum() < 50:
        return float("nan")
    z, y, x = np.nonzero(region)
    a = np.stack([np.ones_like(z), z, y, x], 1).astype(float)
    v = roi_1mm[region].astype(float)
    c, *_ = np.linalg.lstsq(a, v, rcond=None)
    return float(np.std(v - a @ c))


def nps_radial(roi_1mm: np.ndarray, region: np.ndarray, nbins: int = 8) -> np.ndarray:
    """Radially averaged 3-D NPS of detrended HU inside region (zeros outside, windowed); same estimator for all arms."""
    if region.sum() < 50:
        return np.full(nbins, np.nan)
    z, y, x = np.nonzero(region)
    a = np.stack([np.ones_like(z), z, y, x], 1).astype(float)
    v = np.zeros(roi_1mm.shape, float)
    vv = roi_1mm[region].astype(float)
    c, *_ = np.linalg.lstsq(a, vv, rcond=None)
    v[region] = vv - a @ c
    f = np.abs(np.fft.fftshift(np.fft.fftn(v))) ** 2 / max(region.sum(), 1)
    n = roi_1mm.shape[0]
    fz, fy, fx = np.meshgrid(*[np.fft.fftshift(np.fft.fftfreq(n))] * 3, indexing="ij")
    r = np.sqrt(fz**2 + fy**2 + fx**2)
    edges = np.linspace(0, 0.5, nbins + 1)
    idx = np.digitize(r.ravel(), edges) - 1
    out = np.full(nbins, np.nan)
    for k in range(nbins):
        sel = idx == k
        if sel.any():
            out[k] = f.ravel()[sel].mean()
    return out
