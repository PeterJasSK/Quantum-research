"""LIDC real-nodule reference set for validation (privacy: voxels stay in gitignored runs/, never feed a generator).

    python -m H_analysis.src.lidc_ref --scans <N | all | PID,PID,...> [--out DIR]

Nodules >= 3 mm annotated by >= 2 readers, 50 % consensus mask, type from median texture rating
(<= 2 ground-glass, < 5 part-solid, 5 solid). Hosts = the F render selection (synthetic insertion hosts);
the remaining patients contribute real nodules; the two sets are patient-disjoint (plan Q6).
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from H_analysis.src import roi
from shared import runrecord, seedhash

LIDC_ROOT = Path(os.environ.get("LIDC_ROOT", "~/data/LIDC-IDRI")).expanduser()
H = Path(__file__).resolve().parents[1]
MIN_DIAM_MM, MIN_READERS = 3.0, 2


def pylidc_shim():
    """pylidc 0.2.3 uses np.int/np.float/np.bool and configparser.SafeConfigParser (gone in numpy 2 / Python 3.12)."""
    for name, typ in (("int", int), ("float", float), ("bool", bool)):
        if name not in np.__dict__:
            setattr(np, name, typ)
    if not hasattr(configparser, "SafeConfigParser"):
        configparser.SafeConfigParser = configparser.ConfigParser
    import pylidc  # noqa: F401
    return sys.modules["pylidc"]


def texture_to_type(tex: float) -> str:
    return "ground-glass" if tex <= 2 else ("part-solid" if tex < 5 else "solid")


def host_patients() -> set[str]:
    sel = LIDC_ROOT / "f_render_selection.json"
    return {d["patient_id"] for d in json.loads(sel.read_text())} if sel.exists() else set()


def lung_mask(vol_zyx: np.ndarray, spacing_zyx) -> np.ndarray:
    """H-local lung mask on a 2x2x1-downsampled volume (-400 HU, two largest non-border air components, hole fill), full-res."""
    step = (1, 2, 2)
    small = vol_zyx[:: step[0], :: step[1], :: step[2]] < -400
    lab, n = ndi.label(small)
    border = set(np.unique(np.concatenate([lab[:, 0].ravel(), lab[:, -1].ravel(), lab[:, :, 0].ravel(),
                                           lab[:, :, -1].ravel()])))
    sizes = ndi.sum(small, lab, range(1, n + 1))
    keep = [i + 1 for i in np.argsort(sizes)[::-1] if (i + 1) not in border][:2]
    m = np.isin(lab, keep)
    m = ndi.binary_fill_holes(m)
    return np.kron(m, np.ones(step, bool))[: vol_zyx.shape[0], : vol_zyx.shape[1], : vol_zyx.shape[2]]


def process_scan(scan, rng, n_neg: int = 3):
    vol_yxz = scan.to_volume(verbose=False)
    vol = np.transpose(vol_yxz, (2, 0, 1)).astype(np.float32)  # z, y, x
    sp = (float(scan.slice_thickness), float(scan.pixel_spacing), float(scan.pixel_spacing))
    nodules, annotated = [], np.zeros(vol.shape, bool)
    clusters = scan.cluster_annotations(verbose=False)
    for k, cl in enumerate(clusters):
        if len(cl) < MIN_READERS:
            continue
        from pylidc.utils import consensus
        cmask, cbbox, _ = consensus(cl, clevel=0.5, pad=None)
        cm = np.transpose(cmask, (2, 0, 1))
        sl = (cbbox[2], cbbox[0], cbbox[1])
        full = np.zeros(vol.shape, np.uint8)
        full[sl] = cm
        annotated |= ndi.binary_dilation(full.astype(bool), iterations=3)
        if full.sum() == 0:
            continue
        z, y, x = (np.argwhere(full).mean(0))
        mask_roi = roi.crop_mask(full, sp, (z, y, x))
        d_eq = roi.equivalent_diameter_mm(mask_roi)
        if d_eq < MIN_DIAM_MM:
            continue
        tex = float(np.median([a.texture for a in cl]))
        nodules.append({"cluster": k, "type": texture_to_type(tex), "texture": tex, "n_readers": len(cl),
                        "d_eq_mm": d_eq, "centroid_zyx_vox": [float(z), float(y), float(x)],
                        "roi": roi.crop_iso(vol, sp, (z, y, x)), "mask": mask_roi})
    lm = lung_mask(vol, sp)
    margin = np.array([int(np.ceil(roi.ROI_MM / 2 / s)) for s in sp])
    ok = lm.copy()
    for ax, m in enumerate(margin):
        idx = [slice(None)] * 3
        idx[ax] = slice(0, m)
        ok[tuple(idx)] = False
        idx[ax] = slice(vol.shape[ax] - m, None)
        ok[tuple(idx)] = False
    dist_ann = ndi.distance_transform_edt(~annotated, sampling=sp) if annotated.any() else None
    if dist_ann is not None:
        ok &= dist_ann >= 15
    # eroded lung so ROI centre is deep in parenchyma
    pts = np.argwhere(ok[::4, ::4, ::4]) * 4
    negs = []
    if len(pts):
        for i in rng.choice(len(pts), min(n_neg, len(pts)), replace=False):
            c = pts[i]
            negs.append({"centre_zyx_vox": [float(v) for v in c], "roi": roi.crop_iso(vol, sp, c)})
    return nodules, negs


def build(scans: list, out: Path, seed_hex: str) -> dict:
    pl = pylidc_shim()
    hosts = host_patients()
    meta, arrays = [], {}
    for scan in scans:
        rng = seedhash.rng(seed_hex, f"H.lidc_ref.{scan.patient_id}")
        nods, negs = process_scan(scan, rng)
        role = "host" if scan.patient_id in hosts else "real"
        for j, n in enumerate(nods):
            key = f"{scan.patient_id}_n{j}"
            arrays[key + "_roi"] = n.pop("roi")
            arrays[key + "_mask"] = n.pop("mask")
            meta.append({"kind": "nodule", "key": key, "patient_id": scan.patient_id, "role": role, **n})
        for j, n in enumerate(negs):
            key = f"{scan.patient_id}_neg{j}"
            arrays[key + "_roi"] = n.pop("roi")
            meta.append({"kind": "negative", "key": key, "patient_id": scan.patient_id, "role": role, **n})
        print(f"  {scan.patient_id} ({role}): {len(nods)} nodules, {len(negs)} negatives", flush=True)
    real_pat = sorted({m["patient_id"] for m in meta if m["role"] == "real"})
    host_pat = sorted({m["patient_id"] for m in meta if m["role"] == "host"})
    assert not set(real_pat) & set(host_pat)
    counts = {t: sum(1 for m in meta if m["kind"] == "nodule" and m["role"] == "real" and m["type"] == t)
              for t in ("solid", "part-solid", "ground-glass")}
    ref = {"roi_mm": roi.ROI_MM, "seed_hex": seed_hex, "real_patients": real_pat, "host_patients": host_pat,
           "real_nodule_counts_by_type": counts, "items": meta}
    (out / "lidc_ref.json").write_text(json.dumps(ref, indent=1))
    np.savez_compressed(out / "rois.npz", **arrays)
    return ref


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scans", default="all", help="N | all | comma-separated patient ids")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    pl = pylidc_shim()
    allscans = sorted((s for s in pl.query(pl.Scan).all() if (LIDC_ROOT / s.patient_id).is_dir()),
                      key=lambda s: s.patient_id)
    if a.scans == "all":
        scans = allscans
    elif a.scans.isdigit():
        scans = allscans[: int(a.scans)]
    else:
        want = set(a.scans.split(","))
        scans = [s for s in allscans if s.patient_id in want]
    seed_hex = seedhash.sha256_bytes(("H.lidc_ref:" + ",".join(s.patient_id for s in scans)).encode())
    run = runrecord.start_run("H_analysis", "lidc-ref", seed_hex=seed_hex, tool="H_analysis.src.lidc_ref")
    out = Path(a.out) if a.out else run.path
    out.mkdir(parents=True, exist_ok=True)
    ref = build(scans, out, seed_hex)
    run.finish(notes="LIDC real-nodule reference set (validation only)")
    print(f"real patients {len(ref['real_patients'])}, host patients {len(ref['host_patients'])}, disjoint: True")
    print("real nodules by type:", ref["real_nodule_counts_by_type"])
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
