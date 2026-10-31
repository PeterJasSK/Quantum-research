"""F2.1 lesion geometry — realistic procedural nodule (plan §4/§5).

Pure numpy/scipy, no ML. Reverse-engineers the classical phantom-synthesis pipeline so the
nodule reads like a real CT lesion instead of a sharp uniform disc:
  * irregular shape  — sphere radius displaced by low-frequency lobulation + roughness +
                       (for spiculated) sparse radial spikes, keyed to `margin`.
  * heterogeneous interior — a correlated texture field around the type's mean HU (not a
                       constant), per type (solid / GGO / part-solid / calcified).
  * partial-volume edge — a continuous `alpha` coverage [0,1] feathered over ~1-2 voxels
                       (not a binary mask); insert.py composites with it and applies the
                       scanner point-spread blur.

`seed` is derived by build_tiles from the tile's CERTIFIED-QUANTUM bits (QuantumRun.raw_bits),
so the exact shape + texture inherit the same provenance as size/type — still a classical
rendering, no training (honest label, epic §6). The 3D blob stays for F4; F2 inserts the
central slice (Q2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter

from common.datamodel import TumorParams

LUNG_BG_HU = -750.0
HU_BY_TYPE = {
    "solid": 30.0,
    "part-solid": 30.0,      # solid core; GGO halo applied separately
    "ground-glass": -650.0,
    "calcified": 300.0,
}
GGO_HALO_HU = -650.0

# margin -> (lobulation amplitude, number of spiculation spikes)
_MARGIN_SHAPE = {
    "smooth": (0.05, 0),
    "lobulated": (0.16, 0),
    "spiculated": (0.09, 8),
}


@dataclass
class Lesion:
    volume_hu: np.ndarray   # 3D HU delta over background (textured)
    alpha: np.ndarray       # 3D partial-volume coverage in [0, 1] (soft edge)
    radius_vox: float
    hu_profile: str
    margin: str


def _deformed_radius(theta, phi, margin, rng, radius):
    """Irregular surface radius r(theta, phi): lobulation + roughness (+ spikes)."""
    amp, n_spikes = _MARGIN_SHAPE.get(margin, (0.08, 0))
    # low-frequency lobulation as a sum of a few pseudo-harmonic terms
    bulge = np.zeros_like(theta)
    for k in (2, 3, 4, 5):
        ak = amp * rng.uniform(0.5, 1.0) / (k - 1)
        bulge = bulge + ak * np.cos(k * theta + rng.uniform(0, 2 * np.pi)) \
            * (0.6 + 0.4 * np.sin((k - 1) * phi + rng.uniform(0, 2 * np.pi)))
    r = radius * (1.0 + bulge)
    # spiculation: thin radial spikes toward random directions
    for _ in range(int(n_spikes)):
        t0 = rng.uniform(0, 2 * np.pi)
        p0 = rng.uniform(0.3 * np.pi, 0.7 * np.pi)
        ang = np.arccos(np.clip(
            np.sin(phi) * np.sin(p0) * np.cos(theta - t0) + np.cos(phi) * np.cos(p0),
            -1.0, 1.0,
        ))
        r = r + radius * 0.55 * np.exp(-(ang ** 2) / (2 * 0.02))
    return r


def build_lesion(params: TumorParams, spacing_mm: float, seed: int) -> Lesion:
    """Realistic 3D HU lesion blob + soft alpha for one tumor (AC-1/2/3)."""
    rng = np.random.default_rng(seed)
    radius = max(1.5, (params.size_mm / 2.0) / spacing_mm)

    half = int(np.ceil(radius * 2.4)) + 3
    n = 2 * half + 1
    ax = np.arange(n) - half
    z, y, x = np.meshgrid(ax, ax, ax, indexing="ij")
    rr = np.sqrt(x * x + y * y + z * z)
    with np.errstate(invalid="ignore", divide="ignore"):
        theta = np.arctan2(y, x)
        phi = np.arccos(np.clip(np.where(rr > 0, z / rr, 0.0), -1.0, 1.0))

    thr = _deformed_radius(theta, phi, params.margin, rng, radius)
    # partial-volume soft coverage: feather ~1.5 vox across the deformed contour
    alpha = np.clip((thr - rr) / 1.5 + 0.5, 0.0, 1.0).astype(np.float32)

    # heterogeneous interior texture (correlated field around the type mean)
    sigma_tex = max(1.0, radius * 0.28)
    tex = gaussian_filter(rng.normal(0.0, 1.0, (n, n, n)).astype(np.float32), sigma_tex)
    tex = tex / (tex.std() + 1e-6)

    core_hu = HU_BY_TYPE[params.type]
    contrast = core_hu - LUNG_BG_HU
    base = np.full((n, n, n), float(contrast), dtype=np.float32)

    if params.type == "ground-glass":
        radial = np.clip(1.0 - (rr / np.maximum(thr, 1e-6)) * 0.5, 0.0, 1.0)
        base = (contrast * 0.8) * radial.astype(np.float32)
        alpha = alpha * 0.85            # translucent: background shows through
        profile = "ggo-textured"
    elif params.type == "part-solid":
        base = np.full((n, n, n), float(GGO_HALO_HU - LUNG_BG_HU), dtype=np.float32)
        core = rr <= (0.5 * thr)
        base[core] = contrast
        profile = "part-solid-textured"
    elif params.type == "calcified":
        speckle = (rng.random((n, n, n)) > 0.985).astype(np.float32)
        base = base + speckle * (abs(contrast) * 0.8)
        profile = "calcified-speckled"
    else:
        profile = "solid-textured"

    tex_amp = 0.30 * abs(contrast)
    volume = (base + tex * tex_amp).astype(np.float32)

    return Lesion(
        volume_hu=volume,
        alpha=alpha,
        radius_vox=float(radius),
        hu_profile=profile,
        margin=params.margin,
    )


def central_slice(lesion: Lesion) -> tuple[np.ndarray, np.ndarray]:
    """Central axial slice: (hu_delta_2d, alpha_2d) for insertion (Q2)."""
    mid = lesion.volume_hu.shape[0] // 2
    return lesion.volume_hu[mid], lesion.alpha[mid]
