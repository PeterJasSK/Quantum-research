"""LIDC-IDRI access for F: host scans (#15) and nodules to fit (#14).

Scans live OUTSIDE the repo (plan Q1): $LIDC_ROOT, default ~/data/LIDC-IDRI, in the pylidc
layout <root>/<patient_id>/<study_uid>/<series_uid>/*.dcm. Pixel data are only ever held in
memory; nothing voxel-wise derived from a patient is written into the repo (privacy-by-construction).

    python -m F_render.src.lidc select --n 20            # print the chosen scans (deterministic)
    python -m F_render.src.lidc download --n 20          # fetch them from TCIA (public collection)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LIDC_ROOT = Path(os.environ.get("LIDC_ROOT", "~/data/LIDC-IDRI")).expanduser()
NBIA = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
TYPES = ("solid", "part-solid", "ground-glass")


def _numpy2_compat() -> None:
    """pylidc 0.2.3 still uses np.int / np.float / np.bool (removed in numpy 2) and
    configparser.SafeConfigParser (removed in Python 3.12); alias them."""
    import configparser

    for name, typ in (("int", int), ("float", float), ("bool", bool)):
        if name not in np.__dict__:
            setattr(np, name, typ)
    if not hasattr(configparser, "SafeConfigParser"):
        configparser.SafeConfigParser = configparser.ConfigParser


def configure_pylidc() -> None:
    """Point pylidc at LIDC_ROOT (writes ~/.pylidcrc once; never overwrites an existing one)."""
    _numpy2_compat()
    rc = Path("~/.pylidcrc").expanduser()
    if not rc.exists():
        rc.write_text(f"[dicom]\npath = {LIDC_ROOT}\nwarn = True\n")
    LIDC_ROOT.mkdir(parents=True, exist_ok=True)


def texture_to_type(texture: float) -> str:
    """LIDC radiologist texture rating (1 non-solid/GGO … 5 solid) → contract tumor_type.

    Median rating ≤ 2 → ground-glass, < 5 → part-solid, 5 → solid (plan AC-3).
    """
    if texture <= 2:
        return "ground-glass"
    return "part-solid" if texture < 5 else "solid"


@dataclass
class Nodule:
    scan_id: int
    patient_id: str
    series_uid: str
    index: int
    n_readers: int
    texture: float
    type: str
    diameter_mm: float


def scan_nodules(scan, min_readers: int = 3, min_diam: float = 6.0) -> list[Nodule]:
    out = []
    for i, cluster in enumerate(scan.cluster_annotations(verbose=False)):
        if not min_readers <= len(cluster) <= 4:  # >4 = pylidc failed to separate adjacent nodules
            continue
        tex = float(np.median([a.texture for a in cluster]))
        diam = float(np.mean([a.diameter for a in cluster]))
        if diam < min_diam:
            continue
        out.append(Nodule(scan.id, scan.patient_id, scan.series_instance_uid, i, len(cluster), tex,
                          texture_to_type(tex), diam))
    return out


def select_scans(n: int = 20, max_thickness: float = 2.5) -> list[dict]:
    """Deterministic pick of n scans that together cover all three nodule types.

    One pass over scans sorted by patient_id (one series per patient); each scan is assigned to the
    rarest still-open type it contains (ground-glass, part-solid, then solid), roughly n/3 scans each.
    """
    import pylidc as pl

    configure_pylidc()
    scans = (pl.query(pl.Scan).filter(pl.Scan.slice_thickness <= max_thickness)
             .order_by(pl.Scan.patient_id).all())
    quota = {t: n // 3 + (1 if i < n % 3 else 0) for i, t in enumerate(("ground-glass", "part-solid", "solid"))}
    seen_patients, picked = set(), []
    for s in scans:
        if not any(quota.values()):
            break
        if s.patient_id in seen_patients:
            continue
        seen_patients.add(s.patient_id)
        types = {nd.type for nd in scan_nodules(s)}
        t = next((t for t in ("ground-glass", "part-solid", "solid") if quota[t] and t in types), None)
        if t:
            picked.append({"patient_id": s.patient_id, "study_uid": s.study_instance_uid,
                           "series_uid": s.series_instance_uid, "slice_thickness": s.slice_thickness,
                           "for_type": t, "types": sorted(types)})
            quota[t] -= 1
    return picked


def series_dir(rec: dict) -> Path:
    return LIDC_ROOT / rec["patient_id"] / rec["study_uid"] / rec["series_uid"]


def download_series(rec: dict) -> Path:
    """Fetch one series zip from the TCIA NBIA API and unpack it in the pylidc layout."""
    dest = series_dir(rec)
    if dest.is_dir() and any(dest.glob("*.dcm")):
        return dest
    url = f"{NBIA}/getImage?SeriesInstanceUID={rec['series_uid']}"
    with urllib.request.urlopen(url, timeout=600) as r:
        data = r.read()
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.endswith(".dcm"):
                (dest / Path(name).name).write_bytes(zf.read(name))
    return dest


def load_scan(scan) -> tuple[np.ndarray, list[float], list[float]]:
    """In-memory HU volume (z, y, x) int16 in LPS identity + spacing_mm_xyz + origin_mm_lps.

    pylidc's volume is (row=y, col=x, slice=z) with slices sorted by ascending patient z,
    which for axial LIDC series is already the LPS identity frame.
    """
    images = scan.load_all_dicom_images(verbose=False)
    vol = scan.to_volume(verbose=False)
    arr = np.clip(np.transpose(vol, (2, 0, 1)), -1024, 3071).astype(np.int16)
    zs = [float(im.ImagePositionPatient[2]) for im in images]
    dz = float(np.median(np.diff(zs)))
    ps = [float(v) for v in images[0].PixelSpacing]
    origin = [float(v) for v in images[0].ImagePositionPatient]
    return arr, [ps[1], ps[0], dz], origin


def nodule_masks(scan, min_readers: int = 3, min_diam: float = 6.0):
    """Yield (Nodule, consensus_mask_zyx bool, bbox slices zyx) at 50 % reader agreement."""
    from pylidc.utils import consensus

    clusters = scan.cluster_annotations(verbose=False)
    for nd in scan_nodules(scan, min_readers, min_diam):
        mask, bbox, _ = consensus(clusters[nd.index], clevel=0.5, pad=[(8, 8), (8, 8), (4, 4)])
        yield nd, np.transpose(mask, (2, 0, 1)), (bbox[2], bbox[0], bbox[1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["select", "download"])
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args(argv)
    picked = select_scans(a.n)
    if a.action == "select":
        print(json.dumps(picked, indent=1))
        return 0
    for i, rec in enumerate(picked, 1):
        d = download_series(rec)
        print(f"[{i}/{len(picked)}] {rec['patient_id']} {rec['for_type']:12s} {len(list(d.glob('*.dcm')))} files")
    (LIDC_ROOT / "f_render_selection.json").write_text(json.dumps(picked, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
