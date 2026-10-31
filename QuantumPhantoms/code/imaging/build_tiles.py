"""Imaging entrypoint (F2 + F5) — render a run's certified params into labeled synthetic CT tiles.

Usage (run from code/):
    python -m imaging.build_tiles --run research_runs/<run>                         # grown (F5 default)
    python -m imaging.build_tiles --run research_runs/<run> --host LIDC-IDRI-0481 --frames 8 --compare
    python -m imaging.build_tiles --run research_runs/<run> --renderer procedural   # F2/F2.1 look
    python -m imaging.build_tiles --run research_runs/<run> --renderer procedural --ct-source /path/to/luna16

Reads cohort_params.json + quantum_run.json (sampler-blind, epic §3) and writes into the run dir:
    tiles/zoom_<shot>_<gen>.png           one windowed crop per tile (overwritten on re-render)
    tiles.json                            {honest_label, ct_attribution, quantum_run, tiles:[CohortTile], …}
  procedural: tiles/full_slice.png (all nodules in one 2-D slice)
  grown:      tiles/full_<host>_<z>.png (one per distinct z), tiles/grow_<shot>_<gen>_<k>.png (growth frames)
Files from the other renderer that this one does not produce are left in place and logged as `stale:`.
Never recomputes quantum anything — it copies the provenance.

Exit codes: 0 ok, 1 bad input, 2 host data missing, 3 at least one tile fell back to procedural.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

from imaging.ctsource import BUNDLED_ATTRIBUTION, load_background
from common.datamodel import CohortTile, QuantumRun, TumorParams
from imaging.insert import (
    crop,
    insert_lesion,
    lung_field_mask,
    place_for_lobe,
    window_to_uint8,
)
from imaging.lesion import build_lesion, central_slice

print = functools.partial(print, flush=True)

GROWN_HONEST_LABEL = (
    "Tumour parameters (size, type, margin, lobe) come from a certified-quantum roll (job-level "
    "CHSH; simulator runs are labelled as such). Growth is a classical cellular automaton "
    "(Kansal–Torquato layers + Pixel2Cancer pleura wall, calibrated to published volume-doubling "
    "times (verify)). The image is a classical 3-D insertion into a public LIDC-IDRI CT scanned on a "
    "Siemens scanner, with that scan's own measured blur and noise; lesion shape and HU come from a "
    "parameter-only library fitted to LIDC nodules (no patient voxels in the generator). The quantum "
    "bits seed growth and appearance: replayable provenance, not realism. All nodules sit in one "
    "host scan (one patient background)."
)
LIDC_DOI = "https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX"

HONEST_LABEL = (
    "Size, type, margin, lobe and the lesion's shape/texture are seeded from the same "
    "certified-quantum measurement (F1's CHSH > 2); the image is a classical procedural "
    "rendering (no training). Provenance is about lesion/cohort selection, not the CT "
    "background. All nodules are shown in one shared reference lung (a dev simplification, "
    "not 12 distinct patients). Synthetic backgrounds (background_source=synthetic_dev) are "
    "development only."
)


def _parse_args():
    ap = argparse.ArgumentParser(description="Imaging — render certified params into CT tiles.")
    ap.add_argument("--run", required=True,
                    help="F1/F4 run dir containing cohort_params.json + quantum_run.json "
                         "(absolute, or relative to QuantumPhantoms/).")
    ap.add_argument("--renderer", choices=("grown", "procedural"), default="grown",
                    help="'grown' (F5: Siemens LIDC host + E growth + F render) or 'procedural' (F2.1).")
    ap.add_argument("--host", default="LIDC-IDRI-0481",
                    help="grown: LIDC host id (fetch with `python -m imaging.lidc_fetch <id>`).")
    ap.add_argument("--frames", type=int, default=8, help="grown: growth frames per tile.")
    ap.add_argument("--fingerprint", default=None, help="grown: scanner_fingerprint JSON override.")
    ap.add_argument("--max-days", type=int, default=15000, help="grown: growth day limit (debug).")
    ap.add_argument("--compare", action="store_true",
                    help="grown: also write compare_procedural_vs_grown.png (procedural rendered in memory).")
    ap.add_argument("--ct-source", default="bundled",
                    help="procedural: 'bundled' (default, real CC BY-SA lung), 'synthetic' (dev), or a "
                         "dir of LUNA16 .mhd / .npy / .png.")
    ap.add_argument("--spacing", type=float, default=0.7, help="mm/px for npy/png/synthetic.")
    ap.add_argument("--crop", type=int, default=128, help="tile crop size (px).")
    ap.add_argument("--wl", type=float, default=-600.0, help="lung window level (HU).")
    ap.add_argument("--ww", type=float, default=1500.0, help="lung window width (HU).")
    ap.add_argument("--psf", type=float, default=0.7, help="scanner point-spread blur sigma (px).")
    ap.add_argument("--seed", type=int, default=0, help="placement RNG + morphology fallback seed.")
    ap.add_argument("--no-dscale", action="store_true",
                    help="grown: ignore <run>/dscale/seed_shapes.npz (grow every nodule from the 2 mm ball).")
    return ap.parse_args()


def _load_dscale(run_dir: str) -> dict | None:
    """D-SCALE (optional): per-tile quantum seed shapes + the run record for the F3 panel."""
    d = os.path.join(run_dir, "dscale")
    npz, rec = os.path.join(d, "seed_shapes.npz"), os.path.join(d, "dscale_run.json")
    if not (os.path.isfile(npz) and os.path.isfile(rec)):
        return None
    with np.load(npz) as z:
        masks = {k: z[k] for k in z.files}
    with open(rec) as f:
        run_rec = json.load(f)
    tiles = {}
    detail = os.path.join(d, "scale_detail.json")
    if os.path.isfile(detail):
        with open(detail) as f:
            tiles = json.load(f).get("seed_tiles", {})
    return {"masks": masks, "run": run_rec, "tiles": tiles}


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


def _procedural_render(args, params, run):
    """F2.1 path in memory: (bg, full_u8, mask, [(params, xy, radius_vox, morphology_source)], n_groups)."""
    groups = _group_by_lineage(params)

    # ONE shared reference lung for the whole cohort (F3.1, Q2).
    bg = load_background(args.ct_source, args.spacing, seed=args.seed)
    shared = bg.array.astype(np.float32).copy()
    mask = lung_field_mask(shared, bg.is_hu)
    rng = np.random.default_rng(args.seed)

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
    return bg, full_u8, mask, placements, len(groups)


def _write_procedural(args, run_dir, params, run):
    bg, full_u8, mask, placements, n_groups = _procedural_render(args, params, run)
    tiles_dir = os.path.join(run_dir, "tiles")
    os.makedirs(tiles_dir, exist_ok=True)
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

    print(f"  rendered {len(cohort)} tiles ({n_groups} lineages) "
          f"from {os.path.basename(run_dir)}")
    msrcs = sorted({t.morphology_source for t in cohort})
    print(f"  background: {bg.source}   full slice: {W}x{H}   lung mask: "
          f"{'yes' if mask is not None else 'no (region fallback)'}")
    print(f"  morphology: {', '.join(msrcs)}   PSF sigma: {args.psf}px")
    print(f"  CHSH stamp carried: {run.chsh_value}  backend: {run.backend_name}")
    print(f"  wrote full-slice + {len(cohort)} zoom PNGs -> {tiles_dir}")
    print(f"  wrote      -> {tiles_json}")
    return {os.path.join(run_dir, t.png_path) for t in cohort} | {os.path.join(run_dir, full_rel)}, 0


def _save(run_dir, rel, u8) -> str:
    Image.fromarray(u8, mode="L").save(os.path.join(run_dir, rel))
    return rel


def _compare_figure(path, proc_zooms, grown_zooms, labels):
    """12 rows: procedural zoom | grown zoom, with a short label."""
    s, gap, top = proc_zooms[0].shape[0], 6, 18
    W, H = 2 * s + 3 * gap, top + len(labels) * (s + gap) + gap
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    d.text((gap, 3), "procedural (F2.1)", fill=0)
    d.text((2 * gap + s, 3), "grown + fitted (F5)", fill=0)
    for i, (a, b, lab) in enumerate(zip(proc_zooms, grown_zooms, labels)):
        y = top + i * (s + gap)
        img.paste(Image.fromarray(a), (gap, y))
        img.paste(Image.fromarray(b), (2 * gap + s, y))
        d.text((gap + 2, y + 2), lab, fill=255)
    img.save(path)


def _write_grown(args, run_dir, params, run):
    from imaging.fingerprint import load_or_estimate
    from imaging.frames import render_tumor
    from imaging.growth import load_params
    from imaging.host import load_host
    from imaging.lesion_fitted import load_library
    from imaging.place import Placer
    from imaging.seedhash import tile_seeds

    t0 = time.time()
    host = load_host(args.host)
    fp = load_or_estimate(host, args.fingerprint)
    t_host = time.time() - t0
    m = host.meta
    print(f"  host {args.host}: {m.get('manufacturer')} {m.get('model')}, kernel {m.get('kernel')}, "
          f"thickness {m.get('slice_thickness')} mm, shape {host.hu.shape}, spacing {host.spacing_zyx}, "
          f"lungs {int(host.lungs.sum())} vox")
    if "SIEMENS" not in str(m.get("manufacturer", "")).upper():
        print(f"  WARNING: {args.host} is not a Siemens-scanner case.")
    print(f"  fingerprint ({fp.get('source')}): PSF σ zyx {fp['psf_sigma_mm_zyx']} mm, "
          f"noise σ {fp['noise_sigma_hu']} HU, plausibility {fp.get('plausibility', {}).get('verdict', 'n/a')}")

    library, cfg = load_library(), load_params()
    hybrid = host.hu.copy()
    placer = Placer(host, np.random.default_rng(args.seed))
    run_key = run.job_id or os.path.basename(run_dir)
    ds = None if args.no_dscale else _load_dscale(run_dir)
    if ds:
        print(f"  D-SCALE seed shapes: {len(ds['masks'])} tiles from {os.path.join(run_dir, 'dscale')} "
              f"({ds['run'].get('sim_label')})")
    renders = []                       # (params, TumorRender, seeds, morphology_source)
    t1 = time.time()
    for group in _group_by_lineage(params):
        parent = None
        for p in group:
            geom, app, msource = tile_seeds(run_key, p.shot_index, p.generation, run.raw_bits)
            site = placer.place(p.lobe, p.size_mm / 2, parent)
            parent = parent or site
            mseed, _ = _quantum_seed(run, p, args.seed)
            ts = time.time()
            tid = f"tile_{p.shot_index}_{p.generation}"
            mask = ds["masks"].get(tid) if ds else None
            label = f"dscale:ch-qca:{ds['tiles'].get(tid, {}).get('region', 'seed')}" if mask is not None else "dscale"
            r = render_tumor(host, hybrid, fp, p, site, (geom, app), library, cfg, n_frames=args.frames,
                             max_days=args.max_days, crop_px=args.crop, wl=args.wl, ww=args.ww, proc_seed=mseed,
                             seed_mask=mask, seed_label=label)
            print(f"    tile {p.shot_index}_{p.generation}: {p.type:12s} {p.margin:10s} {p.size_mm:5.1f} mm "
                  f"{p.lobe} -> {r.renderer:20s} z={r.center_zyx[0]:3d}  {time.time() - ts:5.1f} s"
                  + (f"  [{r.diag['fallback_reason']}]" if "fallback_reason" in r.diag else ""))
            renders.append((p, r, (geom, app), msource))
    t_tiles = time.time() - t1

    tiles_dir = os.path.join(run_dir, "tiles")
    os.makedirs(tiles_dir, exist_ok=True)
    written, full_rel_by_z = set(), {}
    sp_xy = float(host.spacing_zyx[2])
    for _, r, _, _ in renders:
        z = r.center_zyx[0]
        if z not in full_rel_by_z:
            u8 = window_to_uint8(hybrid[z].astype(np.float32), is_hu=True, wl=args.wl, ww=args.ww)
            full_rel_by_z[z] = _save(run_dir, os.path.join("tiles", f"full_{args.host}_{z}.png"), u8)
            written.add(os.path.join(run_dir, full_rel_by_z[z]))
    H, W = hybrid.shape[1:]
    cohort, grown_zooms, fallbacks = [], [], 0
    for p, r, (geom, app), msource in renders:
        z, y, x = r.center_zyx
        full_u8 = window_to_uint8(hybrid[z].astype(np.float32), is_hu=True, wl=args.wl, ww=args.ww)
        patch = crop(full_u8, (x, y), args.crop)
        grown_zooms.append(patch)
        zoom_rel = _save(run_dir, os.path.join("tiles", f"zoom_{p.shot_index}_{p.generation}.png"), patch)
        written.add(os.path.join(run_dir, zoom_rel))
        growth = []
        for f in r.frames:
            rel = _save(run_dir, os.path.join("tiles", f"grow_{p.shot_index}_{p.generation}_{f['k']}.png"), f["u8"])
            written.add(os.path.join(run_dir, rel))
            growth.append({"k": f["k"], "day": f["day"], "diameter_mm": f["diameter_mm"], "role": f["role"],
                           "png_path": rel})
        rad = r.radius_mm / sp_xy + 4.0
        fallbacks += r.renderer == "procedural-fallback"
        cohort.append(CohortTile(
            tile_id=f"tile_{p.shot_index}_{p.generation}", png_path=zoom_rel,
            size_mm=p.size_mm, type=p.type, margin=p.margin, lobe=p.lobe,
            lineage_id=p.lineage_id, generation=p.generation, shot_index=p.shot_index,
            insert_xy=[int(x), int(y)], spacing_mm=sp_xy, background_source="lidc_real",
            backend_name=run.backend_name, job_id=run.job_id, chsh_value=run.chsh_value,
            full_png_path=full_rel_by_z[z],
            bbox=[round(float(v), 5) for v in ((x - rad) / W, (y - rad) / H, 2 * rad / W, 2 * rad / H)],
            morphology_source=msource, renderer=r.renderer, host_id=args.host, slice_z=int(z),
            growth=growth, seed_hex_geometry=geom, seed_hex_appearance=app,
            diag={k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.diag.items()},
        ))
        tid = cohort[-1].tile_id
        if ds and tid in ds["masks"] and "seed_source" in r.diag:          # grown from a D-SCALE seed (or fallback)
            src = r.diag["seed_source"]
            cohort[-1].seed_source = src if src.startswith("dscale:") else "ball"
            info = ds["tiles"].get(tid, {})
            cohort[-1].dscale = {"family": "ch-qca", "claim_level": info.get("claim_level", "L0"),
                                 "witness_passed": info.get("witness_passed")}

    def _sha(name):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    attribution = (f"Host CT: {args.host} (public LIDC-IDRI collection, TCIA, CC BY 3.0, {LIDC_DOI}), "
                   f"scanned on a {m.get('manufacturer', '').title()} {m.get('model', '')} "
                   f"(kernel {m.get('kernel', '')}, {m.get('slice_thickness', '')} mm). Public case; "
                   f"no Siemens involvement.")
    out = {
        "honest_label": GROWN_HONEST_LABEL,
        "ct_attribution": attribution,
        "quantum_run": run.to_dict(),
        "tiles": [t.to_dict() for t in cohort],
        "renderer_version": "imaging-grown@RE-2609cbe",
        "provenance": {
            "library_sha256": _sha("lesion_model_library.json"), "params_lung_sha256": _sha("params_lung.json"),
            "ported_from": "QuantumPhantoms/plans/relatedPapers/reverse-engineering @ 2609cbe (E, F)",
            "hosts": [{"host_id": args.host, **m,
                       "fingerprint": {k: fp.get(k) for k in ("psf_sigma_mm_zyx", "noise_sigma_hu",
                                                              "f50_cyc_per_mm", "plausibility", "source")}}],
        },
    }
    if ds:
        out["dscale"] = ds["run"]
    tiles_json = os.path.join(run_dir, "tiles.json")
    with open(tiles_json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    written.add(tiles_json)

    if args.compare:
        _, full_u8, _, placements, _ = _procedural_render(args, params, run)
        order = {(p.shot_index, p.generation): xy for p, xy, _, _ in placements}
        proc = [crop(full_u8, order[(p.shot_index, p.generation)], args.crop) for p, _, _, _ in renders]
        labels = [f"{p.shot_index}_{p.generation} {p.type} {p.size_mm:g}mm" for p, _, _, _ in renders]
        cmp_path = os.path.join(run_dir, "compare_procedural_vs_grown.png")
        _compare_figure(cmp_path, proc, grown_zooms, labels)
        written.add(cmp_path)
        print(f"  compare  -> {cmp_path}")

    n_frames = sum(len(t.growth) for t in cohort)
    kinds = {k: sum(t.renderer == k for t in cohort) for k in sorted({t.renderer for t in cohort})}
    print(f"  rendered {len(cohort)} tiles ({kinds}), {n_frames} growth frames, "
          f"{len(full_rel_by_z)} full slices")
    print(f"  time: host+fingerprint {t_host:.1f} s, tiles {t_tiles:.1f} s")
    print(f"  CHSH stamp carried: {run.chsh_value}  backend: {run.backend_name}")
    print(f"  wrote      -> {tiles_json}")
    return written, fallbacks


def _log_stale(run_dir, written):
    tiles_dir = os.path.join(run_dir, "tiles")
    stale = sorted(os.path.join("tiles", f) for f in os.listdir(tiles_dir)
                   if os.path.join(tiles_dir, f) not in written)
    for s in stale:
        print(f"  stale: {s}")


def main() -> int:
    args = _parse_args()
    try:
        run_dir = _resolve_run(args.run)
        params, run = _load_f1(run_dir)
    except (FileNotFoundError, TypeError, ValueError) as e:
        print(f"  bad input: {e}", file=sys.stderr)
        return 1
    if args.renderer == "procedural":
        written, fallbacks = _write_procedural(args, run_dir, params, run)
    else:
        from imaging.host import HostMissing

        try:
            written, fallbacks = _write_grown(args, run_dir, params, run)
        except HostMissing as e:
            print(f"  host data missing: {e}", file=sys.stderr)
            return 2
    _log_stale(run_dir, written)
    if fallbacks:
        print(f"  {fallbacks} tile(s) fell back to the procedural lesion (see diag.fallback_reason)")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
