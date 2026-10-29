"""Candidate tumor sites per placement class for one host scan (plan AC-10, AC-11).

    python -m A_placement.src.place --patient LIDC-IDRI-0001 [--per-class 10] [--seed-hex HEX]
                                    [--radius-mm R]

Eligible voxels: inside lungs with a lobe label, outside airway and vessels, farther than 2r from
any LIDC consensus nodule. Each is classed with classify_site for a sphere of nominal radius r
(default: median LIDC consensus radius from the latest class_proportions run). K sites per class
are drawn with shared.seedhash.rng(seed_hex, "A.place.<class>"), keeping >= 2r between sites.
Output in A_placement/runs/<run_id>/: masks + anatomy_masks.json + sites.json + run.json.
A emits candidates only; B draws the site (B-2) and owns the class prior.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from shared.runrecord import start_run
from shared.seedhash import rng, sha256_file
from A_placement.src.classes import CLASS_CODE, CLASSES, THRESHOLDS, classify_site_arrays
from A_placement.src.context import load_fields, site_context
from A_placement.src.lidc_io import A_DIR
from A_placement.src.segment import MASKS, envelope, segment, write_anatomy_json, write_json

DEFAULT_SEED_HEX = "00" * 32


def latest_radius() -> float:
    runs = sorted((A_DIR / "runs").glob("*-repro-proportions/proportions.json"))
    if not runs:
        raise SystemExit("no class_proportions run found: pass --radius-mm or run the reproduction first")
    return float(json.loads(runs[-1].read_text())["median_radius_mm"])


def draw(cands: np.ndarray, k: int, gen: np.random.Generator, taken: list, min_dist_mm: float,
         spacing) -> list:
    out = []
    sp = np.asarray(spacing)
    for i in gen.permutation(len(cands)):
        p = cands[i]
        if all(np.sqrt((((p - q) * sp) ** 2).sum()) >= min_dist_mm for q in taken + out):
            out.append(p)
            if len(out) == k:
                break
    return out


def place(pid: str, per_class: int, seed_hex: str, radius_mm: float) -> Path:
    cache = segment(pid)
    meta = json.loads((cache / "meta.json").read_text())
    f = load_fields(cache)
    eligible = ((f.lungs > 0) & (f.lobes > 0) & (f.airway == 0) & (f.vessels == 0)
                & (f.d_nodule > 2 * radius_mm))
    codes = classify_site_arrays(f.d_pleura, f.d_vessel, f.d_bif, radius_mm)
    codes[~eligible] = 0

    run = start_run("A_placement", "place", seed_hex=seed_hex, tool="A_placement.src.place")
    taken, shortfall, picked = [], {}, []
    for cls in CLASSES:
        cands = np.argwhere(codes == CLASS_CODE[cls])
        got = draw(cands, per_class, rng(seed_hex, f"A.place.{cls}"), taken, 2 * radius_mm, f.spacing_zyx)
        if len(got) < per_class:
            shortfall[cls] = {"requested": per_class, "emitted": len(got), "eligible_voxels": int(len(cands))}
        taken += got
        picked += [(cls, v) for v in got]

    for k in MASKS:
        shutil.copyfile(cache / f"{k}.nii.gz", run.path / f"{k}.nii.gz")
    anatomy = write_anatomy_json(run.path, pid, meta, run.path.name, run.code_hash)

    sp_xyz, org = np.asarray(meta["spacing_mm_xyz"]), np.asarray(meta["origin_mm_lps"])
    sites = []
    for i, (cls, v) in enumerate(picked, 1):
        full = (np.asarray(v) + f.offset).astype(int)
        sites.append({"site_id": f"S{i:03d}", "center_vox_zyx": full.tolist(),
                      "center_mm_lps": [round(float(x), 3) for x in org + full[::-1] * sp_xyz],
                      "context": site_context(f, v, cls, radius_mm)})
    ref = {"path": anatomy.name, "sha256": sha256_file(anatomy)}
    sites_f = write_json(run.path / "sites.json", {
        **envelope("site_candidates", run.path.name, run.code_hash, [{"contract": "anatomy_masks", **ref}]),
        "host_scan_id": pid, "anatomy_masks_ref": ref, "sites": sites})

    run.add_output(anatomy, "anatomy_masks")
    run.add_output(sites_f, "site_candidates")
    notes = {"patient_id": pid, "series_instance_uid": meta["series_instance_uid"], "per_class": per_class,
             "nominal_radius_mm": radius_mm, "thresholds": THRESHOLDS, "shortfall": shortfall,
             "tool_versions": meta["tool_versions"]}
    run.finish(json.dumps(notes, sort_keys=True))
    return run.path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patient", required=True)
    ap.add_argument("--per-class", type=int, default=10)
    ap.add_argument("--seed-hex", default=DEFAULT_SEED_HEX)
    ap.add_argument("--radius-mm", type=float)
    a = ap.parse_args()
    out = place(a.patient, a.per_class, a.seed_hex, a.radius_mm or latest_radius())
    print(out / "sites.json")


if __name__ == "__main__":
    main()
