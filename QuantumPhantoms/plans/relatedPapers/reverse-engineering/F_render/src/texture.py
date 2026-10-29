"""#13 SyntheticTumors [H01] generation steps, rebuilt in 3-D (Hu et al. CVPR 2023, §3.1, Table 1).

All functions are pure; every random draw comes from an `rng` built by `shared.seedhash.rng`
with its own label (F.texture, F.deform, …), so each step is replayable on its own.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def texture_field(shape_zyx, hu_mean: float, hu_std: float, rng: np.random.Generator,
                  eta: float, sigma_b_vox: float = 0.6, renormalise: bool = True) -> np.ndarray:
    """[H01] texture: T ~ N(µt, σp) → cubic up-scaling by η (coarser grain) → Gaussian blur σb.

    The up-scaled field is cropped back to `shape_zyx`. With `renormalise` (lung render) its std is reset
    to `hu_std` after blurring, so the library's intrinsic texture σ is what ends up in the lesion;
    without it (the [H01] reproduction) the blur reduces σp exactly as in the paper.
    """
    shape = np.asarray(shape_zyx)
    small = np.maximum(np.ceil(shape / eta).astype(int), 2)
    t = rng.normal(0.0, 1.0, size=tuple(small))
    t = ndi.zoom(t, eta, order=3, grid_mode=True, mode="grid-mirror")
    t = t[tuple(slice(0, n) for n in shape)]
    if t.shape != tuple(shape):
        t = np.pad(t, [(0, n - m) for n, m in zip(shape, t.shape)], mode="reflect")
    t = ndi.gaussian_filter(t, sigma_b_vox)
    if not renormalise:
        return (hu_mean + hu_std * t).astype(np.float32)
    s = t.std()
    return (hu_mean + (t - t.mean()) * (hu_std / s if s > 0 else 0.0)).astype(np.float32)


def deform_shape(occ: np.ndarray, spacing_mm_zyx, alpha_mm: float, sigma_mm: float,
                 rng: np.random.Generator) -> np.ndarray:
    """[H01] elastic deformation of the outline: smooth random displacement field, amplitude α (mm)."""
    if alpha_mm <= 0:
        return occ
    sp = np.asarray(spacing_mm_zyx, float)
    coords = np.indices(occ.shape, dtype=np.float32)
    for ax in range(3):
        d = ndi.gaussian_filter(rng.uniform(-1, 1, occ.shape), sigma_mm / sp)
        d *= alpha_mm / (np.abs(d).max() + 1e-12) / sp[ax]
        coords[ax] += d
    return ndi.map_coordinates(occ.astype(np.float32), coords, order=1, mode="nearest")


def mass_effect(vol: np.ndarray, center_vox_zyx, radius_mm: float, spacing_mm_zyx,
                intensity: float = 30.0, gamma_factor: float = 1.3) -> np.ndarray:
    """[H01] eq. 5 local scaling warp: γ' = (1 − (1 − γ/γmax)² · I/100) · γ, γmax = 1.3 r.

    A voxel at distance γ < γmax from the centre takes its value from γ' ≤ γ, which pushes the
    surrounding tissue outward. Identity beyond γmax and for I = 0.
    """
    sp = np.asarray(spacing_mm_zyx, float)
    gmax = gamma_factor * radius_mm
    c = np.asarray(center_vox_zyx, float)
    coords = np.indices(vol.shape, dtype=np.float64)
    off_mm = (coords - c[:, None, None, None]) * sp[:, None, None, None]
    g = np.sqrt((off_mm ** 2).sum(0))
    scale = np.where(g < gmax, 1.0 - (1.0 - g / gmax) ** 2 * intensity / 100.0, 1.0)
    src = c[:, None, None, None] + off_mm * scale / sp[:, None, None, None]
    return ndi.map_coordinates(vol.astype(np.float32), src, order=1, mode="nearest")


def capsule(t_soft: np.ndarray, bounds=(0.4, 0.7), sigma_d_vox: float = 0.8, d_hu: float = 120.0) -> np.ndarray:
    """[H01] eq. 6–8: edge band e = [lb ≤ t'' ≤ ub], blurred by σd, scaled by d → HU to add."""
    e = ((t_soft >= bounds[0]) & (t_soft <= bounds[1])).astype(np.float32)
    return d_hu * ndi.gaussian_filter(e, sigma_d_vox)


def ellipsoid_mask(shape_zyx, center_zyx, half_axes_vox_zyx) -> np.ndarray:
    """[H01] base shape: an axis-aligned ellipsoid (used by the liver reproduction, r13)."""
    idx = np.indices(shape_zyx, dtype=np.float32)
    q = sum(((idx[a] - center_zyx[a]) / half_axes_vox_zyx[a]) ** 2 for a in range(3))
    return (q <= 1.0).astype(np.float32)
