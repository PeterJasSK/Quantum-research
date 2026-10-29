"""Sub-voxel growth lattice around one site (feature plan AC-8, AC-9).

An isotropic, LPS-aligned cubic grid centred on the site's `center_mm_lps`. Host masks are resampled onto it
nearest-neighbour, host HU linearly (SimpleITK), and turned into the growth environment:
    hard barrier   outside the site's lung, or another lobe (fissure)        — never entered
    soft barrier   vessel or airway inside the site's lobe                   — Pixel2Cancer pressure barrier
    levels 1–4     parenchyma quantified from host HU between `hu_bounds`   — levels 1–3 split [lo, hi]
                   in three, HU > hi (dense, not vessel/airway) is level 4
Host HU is only read to describe the environment (privacy-by-construction): no voxel becomes tumor appearance.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import zoom

from shared.volumes import IDENTITY

LOBE_CODE = {"LUL": 1, "LLL": 2, "RUL": 3, "RML": 4, "RLL": 5}
LUNG_CODE = {"right": 1, "left": 2}


@dataclass
class Environment:
    spacing_mm: float
    origin_mm_lps: list[float]          # LPS of lattice index (0, 0, 0), (x, y, z)
    center_zyx: tuple[int, int, int]
    hard: np.ndarray                    # bool (z, y, x)
    soft: np.ndarray                    # bool
    level: np.ndarray                   # int8, 1–4 on parenchyma, 0 on barriers
    outside_lung: np.ndarray            # bool, for the juxtapleural check
    notes: list[str] = field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.hard.shape

    def barrier_code(self) -> np.ndarray:
        """uint8 0 free, 1 hard, 2 soft — for figures."""
        return (self.hard * 1 + (self.soft & ~self.hard) * 2).astype(np.uint8)


def _image(array_zyx: np.ndarray, meta: dict) -> sitk.Image:
    img = sitk.GetImageFromArray(np.ascontiguousarray(array_zyx))
    img.SetSpacing(meta["spacing_mm_xyz"])
    img.SetOrigin(meta["origin_mm_lps"])
    img.SetDirection(IDENTITY)
    return img


def _resample(array_zyx, meta, n: int, origin, sp: float, linear: bool, default: float) -> np.ndarray:
    out = sitk.Resample(_image(array_zyx, meta), [n, n, n], sitk.Transform(),
                        sitk.sitkLinear if linear else sitk.sitkNearestNeighbor,
                        list(origin), [sp] * 3, IDENTITY, default,
                        sitk.sitkFloat32 if linear else sitk.sitkUInt8)
    return sitk.GetArrayFromImage(out)


def build(volumes: dict, meta: dict, site: dict, half_width_mm: float, spacing_mm: float,
          hu_bounds: tuple[float, float]) -> Environment:
    """volumes: host-grid arrays {host_ct, lungs, lobes, vessels, airway} sharing `meta` (one grid)."""
    n = 2 * int(np.ceil(half_width_mm / spacing_mm)) + 1
    c = np.asarray(site["center_mm_lps"], float)
    origin = (c - (n - 1) / 2 * spacing_mm).tolist()
    rs = {k: _resample(volumes[k], meta, n, origin, spacing_mm, False, 0) for k in ("lungs", "lobes", "vessels", "airway")}
    hu = _resample(volumes["host_ct"], meta, n, origin, spacing_mm, True, -1000.0)
    ctx = site["context"]
    lung = rs["lungs"] == LUNG_CODE[ctx["lung"]]
    hard = ~lung | (rs["lobes"] != LOBE_CODE[ctx["lobe"]])
    soft = ((rs["vessels"] > 0) | (rs["airway"] > 0)) & ~hard
    lo, hi = hu_bounds
    step = (hi - lo) / 3.0
    level = np.ones(hard.shape, np.int8)
    level[hu >= lo + step] = 2
    level[hu >= lo + 2 * step] = 3
    level[hu > hi] = 4
    level[hard | soft] = 0
    env = Environment(spacing_mm, origin, ((n - 1) // 2,) * 3, hard, soft, level, rs["lungs"] == 0)
    used = sorted(set(np.unique(level[level > 0]).tolist()))
    env.notes.append(f"lattice {n}³ at {spacing_mm} mm, origin_mm_lps {[round(v, 3) for v in origin]}")
    env.notes.append(f"hard barrier {int(hard.sum())} vox, soft barrier {int(soft.sum())} vox, "
                     f"parenchyma levels used {used}")
    if len(used) == 1:
        env.notes.append(f"uniform HU → 1 parenchyma level (level {used[0]})")
    return env


def place_seed(env: Environment, occupancy: np.ndarray, seed_spacing_mm: float) -> np.ndarray:
    """Seed-shape occupancy (z, y, x) resampled onto the lattice, centred at the site, clipped to free voxels."""
    occ = occupancy.astype(bool)
    if abs(seed_spacing_mm - env.spacing_mm) > 1e-9:
        occ = zoom(occ.astype(np.uint8), seed_spacing_mm / env.spacing_mm, order=0).astype(bool)
    pts = np.argwhere(occ)
    shift = np.asarray(env.center_zyx) - np.round(pts.mean(axis=0)).astype(int)
    pts = pts + shift
    inside = np.all((pts >= 0) & (pts < np.asarray(env.shape)), axis=1)
    pts = pts[inside]
    seed = np.zeros(env.shape, bool)
    seed[tuple(pts.T)] = True
    seed &= ~env.hard & ~env.soft
    if not seed.any():
        raise ValueError("seed shape lands entirely in a barrier at this site")
    return seed
