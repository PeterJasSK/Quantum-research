"""Anatomy masks for one LIDC host scan (plan AC-4, AC-5), cached per patient.

    python -m A_placement.src.segment --patient LIDC-IDRI-0001 [--force]

lungs  lungmask R231 (1 right, 2 left)          lobes  lungmask LTRCLobes fused with R231 (1..5)
vessels/airway  TotalSegmentator task lung_vessels: arteries ∪ veins / airway lumen ∪ wall    body  HU > -500, largest component, holes filled
Consensus LIDC nodules (dilated 2 voxels) are removed from `vessels`; the raw TotalSegmentator
vessel mask is kept as vessels_raw.nii.gz for the class reproduction. Cache key = host CT sha256
plus tool versions (meta.json); a matching cache is reused.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, binary_fill_holes, label

from shared import CONTRACT_VERSION, SHARED
from shared.seedhash import code_hash, sha256_file
from shared.volumes import read_volume, write_volume
from A_placement.src.lidc_io import A_DIR, CACHE, load_host, nodule_masks, series_for

MASKS = ("host_ct", "lungs", "lobes", "vessels", "airway", "body")
LABEL_TABLES = {"lungs": {"1": "right", "2": "left"},
                "lobes": {"1": "LUL", "2": "LLL", "3": "RUL", "4": "RML", "5": "RLL"}}
NODULE_VESSEL_DILATION = 2
# TotalSegmentator >= 2.x splits task lung_vessels into these classes
TS_VESSELS = ("lung_arteries", "lung_veins")
TS_AIRWAY = ("lung_airways", "lung_airways_wall")
TOOL = "A_placement.src.segment"


def tool_versions() -> dict:
    return {p: version(p) for p in ("lungmask", "TotalSegmentator", "torch", "pylidc", "SimpleITK")}


def a_code_hash() -> str:
    return code_hash([A_DIR, SHARED])


def write_json(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return path


def envelope(contract: str, run_id: str | None, chash: str, upstream: list | None = None) -> dict:
    return {
        "contract": contract,
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "A", "tool": TOOL if run_id is None else "A_placement.src.place",
                        "run_id": run_id, "code_hash": chash},
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": False,
        "upstream": upstream or [],
    }


def write_anatomy_json(d: Path, host_scan_id: str, meta: dict, run_id: str | None, chash: str) -> Path:
    f = d / "anatomy_masks.json"
    return write_json(f, {
        **envelope("anatomy_masks", run_id, chash),
        "host_scan_id": host_scan_id,
        "grid": {k: meta[k] for k in ("size_xyz", "spacing_mm_xyz", "origin_mm_lps")},
        "files": {k: {"path": f"{k}.nii.gz", "sha256": sha256_file(d / f"{k}.nii.gz")} for k in MASKS},
        "label_tables": LABEL_TABLES,
    })


def body_mask(ct: np.ndarray) -> np.ndarray:
    lab, n = label(ct > -500)
    if n == 0:
        return np.zeros(ct.shape, np.uint8)
    body = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return np.stack([binary_fill_holes(s) for s in body]).astype(np.uint8)


def lung_masks(host_path: Path) -> tuple[np.ndarray, np.ndarray]:
    import SimpleITK as sitk
    from lungmask import LMInferer

    img = sitk.ReadImage(str(host_path))
    lungs = LMInferer(modelname="R231").apply(img).astype(np.uint8)
    lobes = LMInferer(modelname="LTRCLobes", fillmodel="R231").apply(img).astype(np.uint8)
    return lungs, lobes


def vessel_airway(host_path: Path, out: Path) -> tuple[np.ndarray, np.ndarray]:
    from totalsegmentator.python_api import totalsegmentator

    if not all((out / f"{n}.nii.gz").exists() for n in (*TS_VESSELS, *TS_AIRWAY)):
        totalsegmentator(str(host_path), str(out), task="lung_vessels", device="cpu", quiet=True)

    def union(names):
        return np.any([read_volume(out / f"{n}.nii.gz")[0] > 0 for n in names], axis=0).astype(np.uint8)

    return union(TS_VESSELS), union(TS_AIRWAY)


def cached(d: Path) -> dict | None:
    m = d / "meta.json"
    if not m.exists():
        return None
    meta = json.loads(m.read_text())
    if meta.get("tool_versions") != tool_versions():
        return None
    if not all((d / f"{k}.nii.gz").exists() for k in (*MASKS, "vessels_raw", "nodules")):
        return None
    if sha256_file(d / "host_ct.nii.gz") != meta["host_ct_sha256"]:
        return None
    return meta


def segment(pid: str, force: bool = False) -> Path:
    """Return the cache dir holding contract-valid anatomy masks for `pid`."""
    d = CACHE / pid
    if not force and cached(d):
        return d
    d.mkdir(parents=True, exist_ok=True)
    series = series_for(pid)
    host = d / "host_ct.nii.gz"
    ct, meta = load_host(pid, series, host)
    sp, org = meta["spacing_mm_xyz"], meta["origin_mm_lps"]

    print(f"[{pid}] lungmask R231 + LTRCLobes")
    lungs, lobes = lung_masks(host)
    print(f"[{pid}] TotalSegmentator lung_vessels (CPU)")
    vessels_raw, airway = vessel_airway(host, d / "totalseg")

    nods = nodule_masks(series, meta)
    nod_label = np.zeros(ct.shape, np.uint8)
    for i, n in enumerate(nods, 1):
        nod_label[n["mask"]] = i
    keep_out = binary_dilation(nod_label > 0, iterations=NODULE_VESSEL_DILATION)
    vessels = (vessels_raw.astype(bool) & ~keep_out).astype(np.uint8)

    vols = {"lungs": lungs, "lobes": lobes, "vessels": vessels, "airway": airway, "body": body_mask(ct),
            "vessels_raw": vessels_raw, "nodules": nod_label}
    for k, v in vols.items():
        write_volume(d / f"{k}.nii.gz", v, sp, org)
    write_json(d / "nodules.json", [{k: v for k, v in n.items() if k != "mask"} | {"label": i}
                                    for i, n in enumerate(nods, 1)])
    write_anatomy_json(d, pid, meta, None, a_code_hash())
    write_json(d / "meta.json", {**meta, "patient_id": pid, "series_instance_uid": series,
                                 "host_ct_sha256": sha256_file(host), "tool_versions": tool_versions()})
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patient", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    print(segment(a.patient, a.force) / "anatomy_masks.json")


if __name__ == "__main__":
    main()
