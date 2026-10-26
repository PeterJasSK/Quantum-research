"""F2 lesion geometry — TumorParams -> 3D HU blob (plan §4/§5, AC-1).

Pure numpy/scipy. `build_lesion` turns one decoded tumor into a small 3D HU volume +
support mask whose geometry is driven by the params:
  size_mm -> radius (via spacing),  type -> HU density profile (HU_BY_TYPE),
  margin  -> boundary deformation (smooth / lobulated / spiculated).
Shape detail is seeded from `shot_index` so each tile varies. No CT-physics — this is a
classical rendering of quantum-rolled parameters (honest label, epic §6).

The 3D blob exists so the design extends to F4; F2 inserts only its central axial slice
(Q3). `Lesion` holds numpy arrays and is a runtime object (not serialized) — kept here
rather than in datamodel.py so that module stays numpy-free and JSON-only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.datamodel import TumorParams

# Background lung parenchyma reference (HU) and per-type lesion HU (plan §4, Q7).
LUNG_BG_HU = -750.0
HU_BY_TYPE = {
    "solid": 30.0,
    "part-solid": 30.0,      # solid core; GGO halo applied separately
    "ground-glass": -650.0,
    "calcified": 300.0,
}
GGO_HALO_HU = -650.0


@dataclass
class Lesion:
    volume_hu: np.ndarray   # 3D HU delta over background (0 outside the blob)
    mask: np.ndarray        # 3D boolean support
    radius_vox: float
    hu_profile: str         # echo of the type-driven HU model used
    margin: str


def _deformed_threshold(theta, phi, margin, rng, radius):
    """Per-direction radius threshold implementing the three margin classes."""
    if margin == "smooth":
        return np.full_like(theta, radius)
    if margin == "lobulated":
        # a few low-frequency angular bulges
        bulge = (
            0.18 * np.cos(3 * theta + rng.uniform(0, 2 * np.pi)) * np.sin(2 * phi)
            + 0.10 * np.cos(2 * theta + rng.uniform(0, 2 * np.pi))
        )
        return radius * (1.0 + bulge)
    # spiculated: smooth core + thin radial spikes toward random directions
    n_spikes = rng.integers(6, 11)
    spike_field = np.zeros_like(theta)
    for _ in range(int(n_spikes)):
        t0 = rng.uniform(0, 2 * np.pi)
        p0 = rng.uniform(0.25 * np.pi, 0.75 * np.pi)
        ang = np.arccos(
            np.clip(
                np.sin(phi) * np.sin(p0) * np.cos(theta - t0)
                + np.cos(phi) * np.cos(p0),
                -1.0, 1.0,
            )
        )
        spike_field = np.maximum(spike_field, np.exp(-(ang ** 2) / (2 * 0.06)))
    return radius * (1.0 + 0.7 * spike_field)


def build_lesion(params: TumorParams, spacing_mm: float, seed: int) -> Lesion:
    """Build a 3D HU lesion blob for one tumor (AC-1)."""
    rng = np.random.default_rng(seed)
    radius = max(1.5, (params.size_mm / 2.0) / spacing_mm)  # voxels

    half = int(np.ceil(radius * 1.9)) + 2
    n = 2 * half + 1
    ax = np.arange(n) - half
    z, y, x = np.meshgrid(ax, ax, ax, indexing="ij")
    rr = np.sqrt(x * x + y * y + z * z)
    with np.errstate(invalid="ignore", divide="ignore"):
        theta = np.arctan2(y, x)
        phi = np.arccos(np.clip(np.where(rr > 0, z / rr, 0.0), -1.0, 1.0))

    thr = _deformed_threshold(theta, phi, params.margin, rng, radius)
    mask = rr <= thr

    volume = np.zeros((n, n, n), dtype=np.float32)
    core_hu = HU_BY_TYPE[params.type]

    if params.type == "ground-glass":
        # faint, soft-edged: fade from core to 40% at the boundary
        soft = np.clip(1.0 - (rr / np.maximum(thr, 1e-6)) * 0.6, 0.0, 1.0)
        volume[mask] = ((core_hu - LUNG_BG_HU) * soft)[mask]
        profile = "ggo-soft"
    elif params.type == "part-solid":
        # GGO halo everywhere in mask + a denser solid core inside inner radius
        volume[mask] = GGO_HALO_HU - LUNG_BG_HU
        core_mask = rr <= (0.55 * thr)
        volume[core_mask] = core_hu - LUNG_BG_HU
        profile = "part-solid-core"
    else:  # solid / calcified: fairly uniform fill
        volume[mask] = core_hu - LUNG_BG_HU
        profile = "solid-uniform"

    return Lesion(
        volume_hu=volume,
        mask=mask,
        radius_vox=float(radius),
        hu_profile=profile,
        margin=params.margin,
    )


def central_slice(lesion: Lesion) -> tuple[np.ndarray, np.ndarray]:
    """Central axial slice of the blob: (hu_delta_2d, mask_2d) for insertion (Q3)."""
    mid = lesion.volume_hu.shape[0] // 2
    return lesion.volume_hu[mid], lesion.mask[mid]
