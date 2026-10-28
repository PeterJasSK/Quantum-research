"""F2 entrypoint — render F1's certified params into labeled synthetic CT tiles.

Usage:
    python QuantumPhantoms/code/build_tiles.py --run research_runs/<f1_run>
    python QuantumPhantoms/code/build_tiles.py --run research_runs/<f1_run> --ct-source /path/to/luna16

Reads F1's cohort_params.json + quantum_run.json (sampler-blind, epic §3), builds a 3D
lesion per tumor, inserts its central slice into a real/synthetic lung-CT slice with matched
noise, and writes:
    <run>/tiles/tile_<shot>_<gen>.png     one windowed crop per tile
    <run>/tiles.json                      {honest_label, quantum_run, tiles:[CohortTile]}
These are F3's inputs. F2 never recomputes quantum anything — it copies the provenance.
"""

from __future__ import annotations

import argparse
import functools
import json
import os

import numpy as np
from PIL import Image

from f2_imaging.ctsource import BUNDLED_ATTRIBUTION, load_background
from common.datamodel import CohortTile, QuantumRun, TumorParams
from f2_imaging.insert import (
    crop,
    insert_lesion,
    lung_field_mask,
    place_for_lobe,
    window_to_uint8,
)
from f2_imaging.lesion import build_lesion, central_slice

print = functools.partial(print, flush=True)

HONEST_LABEL = (
    "Size, type, margin, lobe and the lesion's shape/texture are seeded from the same "
    "certified-quantum measurement (F1's CHSH > 2); the image is a classical procedural "
    "rendering (no training). Provenance is about lesion/cohort selection, not the CT "
    "background. All nodules are shown in one shared reference lung (a dev simplification, "
    "not 12 distinct patients). Synthetic backgrounds (background_source=synthetic_dev) are "
    "development only."
)


def _parse_args():
    ap = argparse.ArgumentParser(description="F2 — render certified params into CT tiles.")
    ap.add_argument("--run", required=True,
                    help="F1 run dir containing cohort_params.json + quantum_run.json "
                         "(absolute, or relative to QuantumPhantoms/).")
    ap.add_argument("--ct-source", default="bundled",
                    help="'bundled' (default, real CC BY-SA lung), 'synthetic' (dev), or a "
                         "dir of LUNA16 .mhd / .npy / .png.")
    ap.add_argument("--spacing", type=float, default=0.7, help="mm/px for npy/png/synthetic.")
    ap.add_argument("--crop", type=int, default=128, help="tile crop size (px).")
    ap.add_argument("--wl", type=float, default=-600.0, help="lung window level (HU).")
    ap.add_argument("--ww", type=float, default=1500.0, help="lung window width (HU).")
    ap.add_argument("--psf", type=float, default=0.7, help="scanner point-spread blur sigma (px).")
    ap.add_argument("--seed", type=int, default=0, help="placement RNG + morphology fallback seed.")
    return ap.parse_args()


def _quantum_seed(run, p, fallback: int):
    """Per-tile morphology seed from the tile's certified-quantum bitstring (F2.1 AC-6).

    Falls back to the classical `--seed` when the run carries no raw bits (PRNG).
    Returns (seed, morphology_source).
    """
    rb = getattr(run, "raw_bits", None)
    if rb:
        word = str(rb[p.shot_index % len(rb)])
        try:
            base = int(word, 2)
        except ValueError:
            base = abs(hash(word))
        seed = (base ^ (p.shot_index * 2654435761) ^ (p.generation + 1)) & 0x7FFFFFFF
        return seed, "quantum"
    return (fallback + p.shot_index * 7 + p.generation) & 0x7FFFFFFF, "classical"


def _resolve_run(run_arg: str) -> str:
    if os.path.isabs(run_arg) and os.path.isdir(run_arg):
        return run_arg
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.normpath(os.path.join(here, "..", "..", run_arg))
    if os.path.isdir(cand):
        return cand
    if os.path.isdir(run_arg):
        return os.path.abspath(run_arg)
    raise FileNotFoundError(f"--run dir not found: {run_arg}")


def _load_f1(run_dir: str):
    cp = os.path.join(run_dir, "cohort_params.json")
    qr = os.path.join(run_dir, "quantum_run.json")
    if not (os.path.isfile(cp) and os.path.isfile(qr)):
        raise FileNotFoundError(
            f"{run_dir} is missing cohort_params.json / quantum_run.json (not an F1 run?)."
        )
    with open(cp) as f:
        tiles = [TumorParams.from_dict(d) for d in json.load(f)]
    with open(qr) as f:
        run = QuantumRun.from_dict(json.load(f))
    return tiles, run


def _group_by_lineage(params):
    groups: dict[str, list] = {}
    for p in params:
        groups.setdefault(p.lineage_id, []).append(p)
    return list(groups.values())


def main():
    args = _parse_args()
    run_dir = _resolve_run(args.run)
    params, run = _load_f1(run_dir)

    groups = _group_by_lineage(params)

    # ONE shared reference lung for the whole cohort (F3.1, Q2).
    bg = load_background(args.ct_source, args.spacing, seed=args.seed)
    shared = bg.array.astype(np.float32).copy()
    mask = lung_field_mask(shared, bg.is_hu)
    rng = np.random.default_rng(args.seed)

    tiles_dir = os.path.join(run_dir, "tiles")
    os.makedirs(tiles_dir, exist_ok=True)

    # 1) place every nodule into the single shared slice; record each centre + radius.
    placements = []  # (params, (x, y), radius_vox, morphology_source)
    for group in groups:
        base_xy = None
        for p in group:
            mseed, msource = _quantum_seed(run, p, args.seed)
            lesion = build_lesion(p, bg.spacing_mm, seed=mseed)
            delta2d, alpha2d = central_slice(lesion)
            if base_xy is None:
                xy = place_for_lobe(p.lobe, shared.shape, rng, mask=mask)
                base_xy = xy
            else:
                off = int(max(6, lesion.radius_vox * 3))  # sibling daughter: nearby (AC-5)
                xy = (int(np.clip(base_xy[0] + off, 0, shared.shape[1] - 1)),
                      int(np.clip(base_xy[1] + off, 0, shared.shape[0] - 1)))
            shared = insert_lesion(shared, delta2d, alpha2d, xy,
                                   is_hu=bg.is_hu, rng=rng, psf_sigma=args.psf)
            placements.append((p, xy, lesion.radius_vox, msource))

    # 2) window the finished shared slice once -> the full-lung view every tile references.
    full_u8 = window_to_uint8(shared, is_hu=bg.is_hu, wl=args.wl, ww=args.ww)
    full_rel = os.path.join("tiles", "full_slice.png")
    Image.fromarray(full_u8, mode="L").save(os.path.join(run_dir, full_rel))
    H, W = full_u8.shape

    # 3) per tile: a zoom crop + a normalised bbox for the F3 marker overlay.
    cohort: list[CohortTile] = []
    for p, xy, rad, msource in placements:
        patch = crop(full_u8, xy, args.crop)
        tile_id = f"tile_{p.shot_index}_{p.generation}"
        zoom_rel = os.path.join("tiles", f"zoom_{p.shot_index}_{p.generation}.png")
        Image.fromarray(patch, mode="L").save(os.path.join(run_dir, zoom_rel))
        r = rad + 4.0
        bbox = [
            (xy[0] - r) / W, (xy[1] - r) / H, (2 * r) / W, (2 * r) / H,
        ]
        cohort.append(CohortTile(
            tile_id=tile_id, png_path=zoom_rel,
            size_mm=p.size_mm, type=p.type, margin=p.margin, lobe=p.lobe,
            lineage_id=p.lineage_id, generation=p.generation, shot_index=p.shot_index,
            insert_xy=[int(xy[0]), int(xy[1])], spacing_mm=float(bg.spacing_mm),
            background_source=bg.source,
            backend_name=run.backend_name, job_id=run.job_id, chsh_value=run.chsh_value,
            full_png_path=full_rel, bbox=[round(float(v), 5) for v in bbox],
            morphology_source=msource,
        ))

    out = {
        "honest_label": HONEST_LABEL,
        "ct_attribution": BUNDLED_ATTRIBUTION if bg.source == "bundled_real" else "",
        "quantum_run": run.to_dict(),
        "tiles": [t.to_dict() for t in cohort],
    }
    tiles_json = os.path.join(run_dir, "tiles.json")
    with open(tiles_json, "w") as f:
        json.dump(out, f, indent=2, default=str)

    print(f"  rendered {len(cohort)} tiles ({len(groups)} lineages) "
          f"from {os.path.basename(run_dir)}")
    msrcs = sorted({t.morphology_source for t in cohort})
    print(f"  background: {bg.source}   full slice: {W}x{H}   lung mask: "
          f"{'yes' if mask is not None else 'no (region fallback)'}")
    print(f"  morphology: {', '.join(msrcs)}   PSF sigma: {args.psf}px")
    print(f"  CHSH stamp carried: {run.chsh_value}  backend: {run.backend_name}")
    print(f"  wrote full-slice + {len(cohort)} zoom PNGs -> {tiles_dir}")
    print(f"  wrote      -> {tiles_json}")


if __name__ == "__main__":
    main()
