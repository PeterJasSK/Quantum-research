"""LIDC-IDRI host CT and consensus-nodule I/O on the contract grid (plan AC-3).

Host CT: DICOM series -> SimpleITK -> LPS identity, int16 HU in [-1024, 3071], native spacing,
no resampling (contracts/VOLUMES.md). Nodules: pylidc consensus masks placed on that exact grid
by physical position (pylidc indexes volumes as (row, col, slice) = (y, x, k)).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from shared.volumes import HU_MAX, HU_MIN, IDENTITY, write_volume

A_DIR = Path(__file__).resolve().parents[1]
LIDC_ROOT = Path(os.environ.get("LIDC_ROOT", Path.home() / "data" / "LIDC-IDRI"))
SUBSET = A_DIR / "repro" / "lidc_subset.txt"
CACHE = A_DIR / "runs" / "cache"
MAX_Z_JITTER_MM = 0.01


def read_subset(path: Path = SUBSET) -> list[tuple[str, str]]:
    rows = [ln.split() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    return [(r[0], r[1]) for r in rows]


def series_for(pid: str) -> str:
    for p, s in read_subset():
        if p == pid:
            return s
    raise KeyError(f"{pid} is not in {SUBSET}")


def pylidc():
    """Import pylidc 0.2.3, which still uses numpy aliases removed in numpy 1.24."""
    for alias, typ in (("int", int), ("float", float), ("bool", bool)):
        if alias not in np.__dict__:
            setattr(np, alias, typ)
    import pylidc as pl

    return pl


def scan_for(series_uid: str):
    pl = pylidc()

    return pl.query(pl.Scan).filter(pl.Scan.series_instance_uid == series_uid).first()


def series_files(pid: str, series_uid: str) -> list[str]:
    base = LIDC_ROOT / pid
    for d in [base / series_uid, *sorted(p for p in base.rglob("*") if p.is_dir())]:
        files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(d), series_uid)
        if files:
            return list(files)
    raise FileNotFoundError(f"series {series_uid} not found under {base} (run lidc_fetch --fetch)")


def load_host(pid: str, series_uid: str, out_path: Path) -> tuple[np.ndarray, dict]:
    """Write host_ct.nii.gz; return (ct_zyx int16, meta). Raises on uneven slices or oblique scans."""
    files = series_files(pid, series_uid)
    zs = []
    for f in files:
        r = sitk.ImageFileReader()
        r.SetFileName(f)
        r.ReadImageInformation()
        zs.append(float(r.GetMetaData("0020|0032").split("\\")[2]))
    dz = np.diff(np.sort(zs))
    if dz.size and (dz.max() - dz.min()) > MAX_Z_JITTER_MM:
        raise ValueError(f"{pid}: uneven slice spacing {dz.min():.3f}-{dz.max():.3f} mm (contract forbids resampling)")
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(files)
    img = sitk.DICOMOrient(reader.Execute(), "LPS")
    if not np.allclose(img.GetDirection(), IDENTITY, atol=1e-4):
        raise ValueError(f"{pid}: oblique acquisition, direction {img.GetDirection()}")
    ct = np.clip(sitk.GetArrayFromImage(img), HU_MIN, HU_MAX).astype(np.int16)
    spacing, origin = list(img.GetSpacing()), list(img.GetOrigin())
    write_volume(out_path, ct, spacing, origin)
    return ct, {"size_xyz": list(img.GetSize()), "spacing_mm_xyz": spacing, "origin_mm_lps": origin}


def nodule_masks(series_uid: str, meta: dict) -> list[dict]:
    """Consensus nodules (>= MIN_READERS readers, mean diameter >= MIN_DIAMETER_MM) on the host grid.

    Each item: mask (bool zyx, full grid), n_readers, diameter_mm, volume_mm3, radius_mm, centroid_vox_zyx.
    """
    pylidc()
    from pylidc.utils import consensus

    from A_placement.src.classes import CONSENSUS_LEVEL, MIN_DIAMETER_MM, MIN_READERS

    scan = scan_for(series_uid)
    nx, ny, nz = meta["size_xyz"]
    sx, sy, sz = meta["spacing_mm_xyz"]
    oz = meta["origin_mm_lps"][2]
    if abs(scan.pixel_spacing - sx) > 1e-3 or abs(scan.pixel_spacing - sy) > 1e-3:
        raise ValueError(f"{scan.patient_id}: pylidc pixel spacing {scan.pixel_spacing} != grid {sx, sy}")
    zvals = np.asarray(scan.slice_zvals, float)
    out = []
    for cluster in scan.cluster_annotations(verbose=False):
        diam = float(np.mean([a.diameter for a in cluster]))
        if len(cluster) < MIN_READERS or diam < MIN_DIAMETER_MM:
            continue
        cmask, cbbox, _ = consensus(cluster, clevel=CONSENSUS_LEVEL)
        full = np.zeros((nz, ny, nx), bool)
        rows, cols, ks = cbbox
        for kk, k in enumerate(range(ks.start, ks.stop)):
            zf = (zvals[k] - oz) / sz
            zi = int(round(zf))
            if abs(zf - zi) > 0.25 or not 0 <= zi < nz:
                raise ValueError(f"{scan.patient_id}: slice z={zvals[k]} does not land on the grid")
            full[zi, rows, cols] |= cmask[:, :, kk]
        vol = float(full.sum() * sx * sy * sz)
        out.append({"mask": full, "n_readers": len(cluster), "diameter_mm": round(diam, 2),
                    "volume_mm3": round(vol, 1), "radius_mm": round((3 * vol / (4 * np.pi)) ** (1 / 3), 2),
                    "centroid_vox_zyx": [int(round(c)) for c in np.argwhere(full).mean(0)]})
    return out
