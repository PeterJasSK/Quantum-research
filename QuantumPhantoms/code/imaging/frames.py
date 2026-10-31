"""F5 — one tumour through the grown renderer: grow → render → insert, plus the pixel-growth frames.

    res = render_tumor(host, hybrid, fp, params, site_zyx, seeds, library, cfg, ...)

Works on a region of interest (ROI) around the site (≈ follow-up radius + spicules + 15 mm), never on the
full volume. The baseline lesion is inserted into `hybrid` (the shared hybrid volume, so later tiles and
the per-z full slices show every nodule); each growth frame is rendered + inserted on a copy of the same
ROI background with the same appearance seed, so only the lesion changes from frame to frame (no noise
flicker). Frames are thumbnails and render at supersample 2 (all 8 alike, incl. baseline); the inserted
tile keeps supersample 4. Every frame and the tile use one fixed axial slice (through the baseline centroid) and one fixed
crop centre. Calcified tumours (no library, no growth) and failed growths use the procedural F2.1 lesion in
3-D (`procedural-3d` / `procedural-fallback`).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from imaging.growth import GrowthFailed, grow
from imaging.insert import crop, window_to_uint8
from imaging.insert3d import insert
from imaging.lesion_fitted import RenderParams, procedural_lesion_3d, render_lesion

ROI_MARGIN_MM = 15.0
FRAME_SUPERSAMPLE = 2   # growth-player thumbnails; the inserted tile keeps RenderParams.supersample (4)


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


def _export(vol_roi, cz: int, cyx, crop_px: int, wl: float, ww: float) -> np.ndarray:
    u8 = window_to_uint8(vol_roi[cz].astype(np.float32), is_hu=True, wl=wl, ww=ww)
    return crop(u8, (int(cyx[1]), int(cyx[0])), crop_px)


def render_tumor(host, hybrid, fp: dict, params, site_zyx, seeds: tuple[str, str], library: dict, cfg: dict,
                 *, n_frames: int = 8, max_days: int = 15000, crop_px: int = 128, wl: float = -600.0,
                 ww: float = 1500.0, proc_seed: int = 0, rp: RenderParams = RenderParams(),
                 seed_mask: np.ndarray | None = None, seed_label: str = "dscale") -> TumorRender:
    geom_hex, app_hex = seeds
    sp = np.asarray(host.spacing_zyx, float)
    reason = None
    growth = None
    if params.type != "calcified":
        try:
            growth = grow(host, site_zyx, params.type, params.size_mm, geom_hex, n_frames=n_frames,
                          max_days=max_days, cfg=cfg, seed_mask=seed_mask, seed_label=seed_label)
        except (GrowthFailed, ValueError) as e:
            reason = f"growth: {e}"

    r_fu = (growth.frames[-1][2] / 2) if growth else params.size_mm / 2
    R, lo, meta = _roi(host, site_zyx, r_fu * 1.3 + rp.spicule_length_mm + ROI_MARGIN_MM, crop_px // 2 + 8)
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
                                   "u8": _export(out, cz, cyx, crop_px, wl, ww)})
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
