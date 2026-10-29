"""Context vector fields from the anatomy masks (plan AC-6).

All distances are Euclidean in mm (`distance_transform_edt` with the voxel spacing). Fields are
computed on a crop around the lungs (LUNG_MARGIN_MM), which holds every candidate site; `Fields`
keeps the crop offset so sites are reported on the full host grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from shared.volumes import read_volume
from A_placement.src.bifurcation import bifurcations

LUNG_MARGIN_MM = 20.0
VESSEL_DENSITY_RADIUS_MM = 10.0
LOBE_NAMES = {1: "LUL", 2: "LLL", 3: "RUL", 4: "RML", 5: "RLL"}
LUNG_NAMES = {1: "right", 2: "left"}


@dataclass
class Fields:
    offset: np.ndarray        # crop origin in full-grid voxels (z, y, x)
    spacing_zyx: tuple
    ct: np.ndarray
    lungs: np.ndarray
    lobes: np.ndarray
    vessels: np.ndarray
    airway: np.ndarray
    nodules: np.ndarray
    d_pleura: np.ndarray
    d_vessel: np.ndarray
    d_airway: np.ndarray
    d_bif: np.ndarray
    d_nodule: np.ndarray


def _edt_to(mask: np.ndarray, spacing) -> np.ndarray:
    if not mask.any():
        return np.full(mask.shape, np.inf, np.float32)
    return distance_transform_edt(~mask, sampling=spacing).astype(np.float32)


def load_fields(cache_dir: Path) -> Fields:
    vols = {k: read_volume(cache_dir / f"{k}.nii.gz")[0]
            for k in ("host_ct", "lungs", "lobes", "vessels", "airway", "nodules")}
    _, meta = read_volume(cache_dir / "lungs.nii.gz")
    spacing = tuple(meta["spacing_mm_xyz"][::-1])
    idx = np.argwhere(vols["lungs"] > 0)
    pad = np.ceil(LUNG_MARGIN_MM / np.asarray(spacing)).astype(int)
    lo = np.maximum(idx.min(0) - pad, 0)
    hi = np.minimum(idx.max(0) + pad + 1, vols["lungs"].shape)
    crop = tuple(slice(a, b) for a, b in zip(lo, hi))
    v = {k: a[crop] for k, a in vols.items()}
    lungs = v["lungs"] > 0
    return Fields(
        offset=lo, spacing_zyx=spacing, ct=v["host_ct"], lungs=v["lungs"], lobes=v["lobes"],
        vessels=v["vessels"], airway=v["airway"], nodules=v["nodules"],
        d_pleura=distance_transform_edt(lungs, sampling=spacing).astype(np.float32),
        d_vessel=_edt_to(v["vessels"] > 0, spacing),
        d_airway=_edt_to(v["airway"] > 0, spacing),
        d_bif=_edt_to(bifurcations(v["vessels"], spacing), spacing),
        d_nodule=_edt_to(v["nodules"] > 0, spacing),
    )


def sphere_offsets(radius_mm: float, spacing_zyx) -> np.ndarray:
    """Integer (dz, dy, dx) offsets of voxels within radius_mm of the centre voxel."""
    n = np.ceil(radius_mm / np.asarray(spacing_zyx)).astype(int)
    g = np.stack(np.meshgrid(*[np.arange(-k, k + 1) for k in n], indexing="ij"), -1).reshape(-1, 3)
    return g[((g * spacing_zyx) ** 2).sum(1) <= radius_mm ** 2]


def _sphere_values(arr: np.ndarray, v, offsets: np.ndarray) -> np.ndarray:
    p = offsets + np.asarray(v)
    ok = np.all((p >= 0) & (p < arr.shape), axis=1)
    return arr[tuple(p[ok].T)]


def site_context(f: Fields, v, placement_class: str, radius_mm: float) -> dict:
    """Contract context vector for crop voxel v (z, y, x)."""
    v = tuple(int(i) for i in v)
    hu = _sphere_values(f.ct, v, sphere_offsets(radius_mm, f.spacing_zyx)).astype(float)
    hu_tissue = hu[_sphere_values(f.vessels, v, sphere_offsets(radius_mm, f.spacing_zyx)) == 0]
    hu = hu_tissue if hu_tissue.size else hu
    dens = _sphere_values(f.vessels, v, sphere_offsets(VESSEL_DENSITY_RADIUS_MM, f.spacing_zyx))
    return {
        "placement_class": placement_class,
        "lung": LUNG_NAMES[int(f.lungs[v])],
        "lobe": LOBE_NAMES[int(f.lobes[v])],
        "dist_pleura_mm": round(float(f.d_pleura[v]), 2),
        "dist_vessel_mm": round(float(f.d_vessel[v]), 2),
        "dist_airway_mm": round(float(min(f.d_airway[v], 1e6)), 2),
        "local_hu_mean": round(float(hu.mean()), 2),
        "local_hu_std": round(float(hu.std()), 2),
        "extra": {
            "nominal_radius_mm": round(float(radius_mm), 2),
            "vessel_density": round(float((dens > 0).mean()), 4),
            "dist_bifurcation_mm": round(float(min(f.d_bif[v], 1e6)), 2),
        },
    }
