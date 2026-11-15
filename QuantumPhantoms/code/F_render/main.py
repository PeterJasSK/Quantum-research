"""Section F: render. Every grown tumour is drawn into the host CT -> tiles.json + tiles/*.png.

Per tumour: site (section A) + growth frames (section E) -> lesion HU from the LIDC-fitted library (lesion_fitted)
-> 3-D insert into a region of interest with the host scan's own blur and noise (insert, fingerprint). The baseline
lesion goes into the shared hybrid volume (so the full slices show every nodule); each growth frame is rendered on a
copy of the same background with the same appearance seed, so only the lesion changes between frames. Calcified
tumours and failed growths use the procedural 3-D lesion (lesion.py), marked procedural-3d / procedural-fallback.
Growth and image are classical; the quantum values on a tile are copied from the roll, never recomputed.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace

import numpy as np
from PIL import Image

from common import HOST, runio
from common.datamodel import CohortTile
from common.runio import Ctx
from F_render.insert import crop, insert, window_to_uint8
from F_render.lesion_fitted import RenderParams, load_library, procedural_lesion_3d, render_lesion

CROP_PX = 128                 # zoom tile size
WL, WW = -600.0, 1500.0       # lung window
ROI_MARGIN_MM = 15.0
FRAME_SUPERSAMPLE = 2         # growth-player thumbnails; the inserted tile keeps RenderParams.supersample
LIDC_DOI = "https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX"
HONEST = ("Tumour parameters come from a quantum measurement (CHSH on the roll); growth (published models) and the "
          "image are classical. Host CT: one public LIDC-IDRI scan; all nodules are inserted into that one scan.")


@dataclass
class TumorRender:
    renderer: str
    center_zyx: tuple[int, int, int]        # host voxel of the exported slice / crop centre
    radius_mm: float
    frames: list[dict] = field(default_factory=list)   # {k, day, diameter_mm, role, u8}
    diag: dict = field(default_factory=dict)


def _roi(host, site_zyx, half_mm: float, min_half_xy_px: int = 0):
    sp = np.asarray(host.spacing_zyx, float)
    half = np.ceil(half_mm / sp).astype(int)
    half[1:] = np.maximum(half[1:], min_half_xy_px)       # frames are cropped from the ROI: no black border
    c = np.asarray(site_zyx, int)
    lo = np.clip(c - half, 0, host.hu.shape)
    hi = np.clip(c + half + 1, 0, host.hu.shape)
    R = tuple(slice(a, b) for a, b in zip(lo, hi))
    org = np.asarray(host.origin_lps, float) + lo[::-1] * sp[::-1]
    meta = {"size_xyz": [int(v) for v in (hi - lo)[::-1]], "spacing_mm_xyz": list(sp[::-1]),
            "origin_mm_lps": org.tolist()}
    return R, lo, meta


def _lps(meta: dict, zyx) -> list[float]:
    return (np.asarray(meta["origin_mm_lps"], float)
            + np.asarray(zyx, float)[::-1] * np.asarray(meta["spacing_mm_xyz"], float)).tolist()


def _export(vol_roi, cz: int, cyx) -> np.ndarray:
    u8 = window_to_uint8(vol_roi[cz].astype(np.float32), is_hu=True, wl=WL, ww=WW)
    return crop(u8, (int(cyx[1]), int(cyx[0])), CROP_PX)


def render_tumor(host, hybrid, fp: dict, params, site_zyx, seeds: tuple[str, str], library: dict, grown: dict | None,
                 proc_seed: int, rp: RenderParams = RenderParams()) -> TumorRender:
    """grown: section E's result for this tumour ({"growth": Growth | None, "error": str | None}), None if calcified."""
    geom_hex, app_hex = seeds
    sp = np.asarray(host.spacing_zyx, float)
    growth = grown["growth"] if grown else None
    reason = f"growth: {grown['error']}" if grown and grown.get("error") else None
    r_fu = (growth.frames[-1][2] / 2) if growth else params.size_mm / 2
    R, lo, meta = _roi(host, site_zyx, r_fu * 1.3 + rp.spicule_length_mm + ROI_MARGIN_MM, CROP_PX // 2 + 8)
    bg = hybrid[R].copy()
    lungs = host.lungs[R]
    site_roi = np.asarray(site_zyx) - lo

    def draw_and_insert(state, p=rp):
        lat_org = _lps(meta, growth.env.origin_zyx_vox - lo)
        les = render_lesion(state, lat_org, [growth.env.spacing_mm] * 3, meta, _lps(meta, site_roi),
                            {"type": params.type, "margin": params.margin, "shape_seed_hex": geom_hex},
                            library, p, app_hex)
        out, _, d = insert(bg, lungs, sp, les, params.type, fp, p, app_hex)
        return les, out, d

    if growth is not None:
        try:
            base_state = next(s for _, role, _, s in growth.frames if role == "baseline")
            les, base_out, ins = draw_and_insert(base_state)
            cz = int(round(les.center_vox_zyx[0]))
            cyx = np.rint(les.center_vox_zyx[1:]).astype(int)
            res = TumorRender("grown+fitted", tuple(int(v) for v in (cz + lo[0], cyx[0] + lo[1], cyx[1] + lo[2])),
                              les.radius_mm)
            rp_frames = replace(rp, supersample=FRAME_SUPERSAMPLE)
            for k, (day, role, diam, state) in enumerate(growth.frames):
                out = draw_and_insert(state, rp_frames)[1]
                res.frames.append({"k": k, "day": int(day), "diameter_mm": round(float(diam), 2), "role": role,
                                   "u8": _export(out, cz, cyx)})
            hybrid[R] = base_out
            res.diag = {**growth.summary, "hu_source": les.diag["hu_source"], "hu_core": round(les.hu_core, 1),
                        "sigma_edge_mm": round(les.diag["sigma_edge_mm"], 3), "filled_holes_vox": les.diag["filled_holes_vox"],
                        "volume_pd_pct": round(ins.get("volume_pd_pct", float("nan")), 2),
                        "sigma_ratio_in_out": round(ins["sigma_ratio_in_out"], 3),
                        "psf_sigma_mm_zyx": ins["psf_sigma_mm_zyx"]}
            return res
        except ValueError as e:
            reason = f"render: {e}"

    les = procedural_lesion_3d(params, meta, site_roi, proc_seed)
    out, _, ins = insert(bg, lungs, sp, les, params.type, fp, rp, app_hex)
    hybrid[R] = out
    cz, cy, cx = (int(v) for v in site_roi)
    res = TumorRender("procedural-3d" if reason is None else "procedural-fallback",
                      (cz + int(lo[0]), cy + int(lo[1]), cx + int(lo[2])), les.radius_mm)
    res.diag = {"hu_source": les.diag["hu_source"], "sigma_ratio_in_out": round(ins["sigma_ratio_in_out"], 3),
                "psf_sigma_mm_zyx": ins["psf_sigma_mm_zyx"]}
    if reason:
        res.diag["fallback_reason"] = reason
    return res


def _shape_seed(run, p) -> int:
    """Seed of the procedural lesion shape, from the tumour's own shot bits."""
    word = str(run.raw_bits[p.shot_index % len(run.raw_bits)])
    return (int(word, 2) ^ (p.shot_index * 2654435761) ^ (p.generation + 1)) & 0x7FFFFFFF


def _save(run_dir, rel: str, u8) -> str:
    Image.fromarray(u8, mode="L").save(os.path.join(run_dir, rel))
    return rel


def run(ctx: Ctx) -> None:
    from common.host import load_host
    from E_classical_growth import main as E
    from F_render import lesion_fitted
    from F_render.fingerprint import load_or_estimate

    run_dir = str(ctx.run_dir)
    params, qrun = runio.load_cohort(run_dir)
    host = load_host(HOST)
    fp = load_or_estimate(host, None)
    m = host.meta
    print(f"  host {HOST}: {m.get('manufacturer')} {m.get('model')}, kernel {m.get('kernel')}, shape {host.hu.shape}; "
          f"fingerprint PSF {fp['psf_sigma_mm_zyx']} mm, noise {fp['noise_sigma_hu']} HU")
    library = load_library()
    sites = runio.load_json(ctx.run_dir / "sites.json")["sites_zyx"]
    _, seed_tiles = runio.load_seed_shapes(run_dir)
    key = runio.run_key(run_dir)
    hybrid = host.hu.copy()
    renders = []
    for group in runio.group_by_lineage(params):
        for p in group:
            tid = runio.tile_id(p)
            geom, app, msource = runio.tile_seeds(key, p.shot_index, p.generation, qrun.raw_bits)
            t0 = time.time()
            r = render_tumor(host, hybrid, fp, p, tuple(sites[tid]), (geom, app), library,
                             runio.load_growth(run_dir, tid), _shape_seed(qrun, p))
            print(f"    {tid}: {p.type:12s} {p.margin:10s} {p.size_mm:5.1f} mm {p.lobe} -> {r.renderer:20s} "
                  f"z={r.center_zyx[0]:3d}  {time.time() - t0:5.1f} s"
                  + (f"  [{r.diag['fallback_reason']}]" if "fallback_reason" in r.diag else ""))
            renders.append((p, r, geom, app, msource))

    os.makedirs(os.path.join(run_dir, "tiles"), exist_ok=True)
    sp_xy = float(host.spacing_zyx[2])
    H, W = hybrid.shape[1:]
    full_by_z, cohort = {}, []
    for p, r, geom, app, msource in renders:
        z, y, x = r.center_zyx
        full_u8 = window_to_uint8(hybrid[z].astype(np.float32), is_hu=True, wl=WL, ww=WW)
        if z not in full_by_z:
            full_by_z[z] = _save(run_dir, os.path.join("tiles", f"full_{HOST}_{z}.png"), full_u8)
        tid = runio.tile_id(p)
        zoom = _save(run_dir, os.path.join("tiles", f"zoom_{p.shot_index}_{p.generation}.png"), crop(full_u8, (x, y), CROP_PX))
        growth = [{"k": f["k"], "day": f["day"], "diameter_mm": f["diameter_mm"], "role": f["role"],
                   "png_path": _save(run_dir, os.path.join("tiles", f"grow_{p.shot_index}_{p.generation}_{f['k']}.png"), f["u8"])}
                  for f in r.frames]
        rad = r.radius_mm / sp_xy + 4.0
        tile = CohortTile(
            tile_id=tid, png_path=zoom, size_mm=p.size_mm, type=p.type, margin=p.margin, lobe=p.lobe,
            lineage_id=p.lineage_id, generation=p.generation, shot_index=p.shot_index,
            insert_xy=[int(x), int(y)], spacing_mm=sp_xy, background_source="lidc_real",
            backend_name=qrun.backend_name, job_id=qrun.job_id, chsh_value=qrun.chsh_value, full_png_path=full_by_z[z],
            bbox=[round(float(v), 5) for v in ((x - rad) / W, (y - rad) / H, 2 * rad / W, 2 * rad / H)],
            morphology_source=msource, renderer=r.renderer, host_id=HOST, slice_z=int(z), growth=growth,
            seed_hex_geometry=geom, seed_hex_appearance=app,
            diag={k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.diag.items()})
        src = r.diag.get("seed_source", "")
        if src:
            tile.seed_source = src if src.startswith("dscale:") else "ball"
            info = seed_tiles.get(tid, {})
            tile.dscale = {"family": info.get("family", "-"), "claim_level": info.get("claim_level", "L0"),
                           "witness_passed": info.get("witness_passed")}
        cohort.append(tile)

    runio.save_json(ctx.path("tiles.json"), {
        "honest_label": HONEST,
        "ct_attribution": (f"Host CT: {HOST} (public LIDC-IDRI collection, TCIA, CC BY 3.0, {LIDC_DOI}), scanned on a "
                           f"{str(m.get('manufacturer', '')).title()} {m.get('model', '')} (kernel {m.get('kernel', '')}, "
                           f"{m.get('slice_thickness', '')} mm). Public case; no Siemens involvement."),
        "quantum_run": qrun.to_dict(),
        "tiles": [t.to_dict() for t in cohort],
        "provenance": {
            "library_sha256": runio.sha256_file(os.path.join(lesion_fitted.DATA, "lesion_model_library.json")),
            "params_lung_sha256": runio.sha256_file(E.PARAMS_FILE),
            "hosts": [{"host_id": HOST, **m, "fingerprint": {k: fp.get(k) for k in (
                "psf_sigma_mm_zyx", "noise_sigma_hu", "f50_cyc_per_mm", "plausibility", "source")}}]}})
    kinds = {k: sum(t.renderer == k for t in cohort) for k in sorted({t.renderer for t in cohort})}
    print(f"  rendered {len(cohort)} tiles ({kinds}), {sum(len(t.growth) for t in cohort)} growth frames")
