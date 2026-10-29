"""F-LOCAL host masks + one free site for LIDC hosts (plan Q8). Replaced by A's masks in INT.

Threshold + connected components only (no lungmask / TotalSegmentator: torch is not installed):
body = largest component of smoothed HU > −500, holes filled per slice; lungs = HU < −400 inside the
filled body, split left/right at the body's x centre (LPS: patient right = low x); vessels = HU > −400
inside the hole-filled lungs; airway = HU < −950 near the midline. Lobes are NOT derivable → all 0.
The single site is the right-lung voxel farthest from both pleura and vessels (deterministic argmax).

    python -m F_render.src.host_masks --lidc LIDC-IDRI-0001 [--out DIR]

Output (default: a run dir under F_render/runs/, gitignored — it holds patient voxels):
anatomy_masks.json + host_ct/body/lungs/lobes/vessels/airway .nii.gz, sites.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from F_render.src import io as fio
from shared.runrecord import start_run
from shared.volumes import write_volume

NOTE = "F-local threshold masks (plan Q8); lobes unavailable (all 0); replaced by A in INT"


def _largest(mask, k=1):
    lab, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, bool), []
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:k] + 1
    return np.isin(lab, order), [lab == i for i in order]


def _fill_slices(mask):
    return np.stack([ndi.binary_fill_holes(s) for s in mask])


def make_masks(host: np.ndarray, sp_zyx) -> dict:
    sp = np.asarray(sp_zyx, float)
    sm = ndi.gaussian_filter(host.astype(np.float32), (0, 1, 1))
    body, _ = _largest(sm > -500)
    body = _fill_slices(body)
    cand = (sm < -400) & body
    cand = ndi.binary_opening(cand, iterations=1)
    big, comps = _largest(cand, 3)
    vox_ml = sp.prod() / 1000.0
    comps = [c for c in comps if c.sum() * vox_ml > 100]
    xs = np.flatnonzero(body.any((0, 1)))
    cx = 0.5 * (xs.min() + xs.max())
    lung_any = np.zeros_like(body)
    for c in comps:
        lung_any |= c
    xg = np.arange(host.shape[2])[None, None, :]
    airway = lung_any & (sm < -950) & (np.abs(xg - cx) * sp[2] < 25)
    airway, _ = _largest(airway)
    lung_any &= ~ndi.binary_dilation(airway, iterations=2)
    filled = _fill_slices(ndi.binary_closing(lung_any, iterations=2))
    lungs = np.zeros(host.shape, np.uint8)
    lungs[filled & (xg < cx)] = 1      # patient right
    lungs[filled & (xg >= cx)] = 2     # patient left
    vessels = filled & (ndi.gaussian_filter(host.astype(np.float32), 0.7) > -400)
    return {"body": body.astype(np.uint8), "lungs": lungs, "lobes": np.zeros(host.shape, np.uint8),
            "vessels": vessels.astype(np.uint8), "airway": airway.astype(np.uint8)}


def free_site(host, masks, sp_zyx, meta) -> dict:
    sp = np.asarray(sp_zyx, float)
    right = masks["lungs"] == 1
    d_pl = ndi.distance_transform_edt(right, sampling=sp)
    d_ve = ndi.distance_transform_edt(~masks["vessels"].astype(bool), sampling=sp)
    d_aw = ndi.distance_transform_edt(~masks["airway"].astype(bool), sampling=sp) if masks["airway"].any() \
        else np.full(host.shape, 999.0)
    score = np.where(right, np.minimum(d_pl, d_ve), -1)
    zs = np.flatnonzero(right.any((1, 2)))
    if len(zs):   # keep away from the dome/apex: middle 60 % of the right lung's z extent
        lo, hi = zs.min() + int(0.2 * len(zs)), zs.max() - int(0.2 * len(zs))
        score[:lo] = -1
        score[hi + 1:] = -1
    z, y, x = np.unravel_index(int(np.argmax(score)), score.shape)
    org = np.asarray(meta["origin_mm_lps"], float)
    sx = np.asarray(meta["spacing_mm_xyz"], float)
    loc = host[max(z - 2, 0):z + 3, max(y - 3, 0):y + 4, max(x - 3, 0):x + 4].astype(float)
    mid = 0.5 * (zs.min() + zs.max()) if len(zs) else z
    return {"site_id": "S001", "center_vox_zyx": [int(z), int(y), int(x)],
            "center_mm_lps": [round(float(v), 3) for v in org + np.array([x, y, z]) * sx],
            "context": {"placement_class": "free", "lung": "right", "lobe": "RLL" if z < mid else "RUL",
                        "dist_pleura_mm": round(float(d_pl[z, y, x]), 2),
                        "dist_vessel_mm": round(float(d_ve[z, y, x]), 2),
                        "dist_airway_mm": round(float(d_aw[z, y, x]), 2),
                        "local_hu_mean": round(float(loc.mean()), 2), "local_hu_std": round(float(loc.std()), 2)}}


def write_host(host, meta, host_scan_id: str, out: Path, code_hash: str, run_id: str | None) -> tuple[Path, Path]:
    sp = meta["spacing_mm_xyz"][::-1]
    masks = make_masks(host, sp)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"host_ct": write_volume(out / "host_ct.nii.gz", host, meta["spacing_mm_xyz"], meta["origin_mm_lps"])}
    for k, v in masks.items():
        paths[k] = write_volume(out / f"{k}.nii.gz", v, meta["spacing_mm_xyz"], meta["origin_mm_lps"])
    man = out / "anatomy_masks.json"
    doc = fio.envelope("anatomy_masks", "F_render.src.host_masks (F-local, plan Q8)", code_hash, run_id, [])
    doc.update({"host_scan_id": host_scan_id,
                "grid": {"size_xyz": list(meta["size_xyz"]), "spacing_mm_xyz": meta["spacing_mm_xyz"],
                         "origin_mm_lps": meta["origin_mm_lps"]},
                "files": {k: fio.file_ref(paths[k], man) for k in
                          ("host_ct", "lungs", "lobes", "vessels", "airway", "body")},
                "label_tables": {"lungs": {"1": "right", "2": "left"},
                                 "lobes": {"1": "LUL", "2": "LLL", "3": "RUL", "4": "RML", "5": "RLL"}}})
    fio.write_manifest(man, doc)
    sites = out / "sites.json"
    sdoc = fio.envelope("site_candidates", "F_render.src.host_masks (F-local, plan Q8)", code_hash, run_id,
                        [fio.up_ref("anatomy_masks", man, sites)])
    sdoc.update({"host_scan_id": host_scan_id, "anatomy_masks_ref": fio.file_ref(man, sites),
                 "sites": [free_site(host, masks, sp, meta)]})
    fio.write_manifest(sites, sdoc)
    return man, sites


def load_lidc_host(patient_id: str):
    from F_render.src import lidc
    import pylidc as pl

    lidc.configure_pylidc()
    scan = pl.query(pl.Scan).filter(pl.Scan.patient_id == patient_id).first()
    if scan is None:
        raise ValueError(f"{patient_id} not in the pylidc database")
    arr, spacing_xyz, origin = lidc.load_scan(scan)
    meta = {"size_xyz": [arr.shape[2], arr.shape[1], arr.shape[0]], "spacing_mm_xyz": spacing_xyz,
            "origin_mm_lps": origin}
    return arr, meta, scan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lidc", required=True, help="LIDC patient id, e.g. LIDC-IDRI-0001")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    host, meta, _ = load_lidc_host(a.lidc)
    run = start_run("F_render", f"host-{a.lidc}", tool="F_render.src.host_masks")
    out = Path(a.out) if a.out else run.path
    man, sites = write_host(host, meta, a.lidc, out, run.code_hash, run.path.name)
    run.add_output(man, "anatomy_masks")
    run.add_output(sites, "site_candidates")
    run.finish(NOTE)
    print(man)
    print(sites)
    return 0


if __name__ == "__main__":
    sys.exit(main())
