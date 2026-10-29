"""Cell lattice → lesion HU on the host grid with true partial volume (plan AC-7).

1. the lattice (E's snapshot, `state` uint8 z,y,x) is re-centred on the site and resampled onto a
   sub-grid of `supersample`³ points per host voxel (nearest; never point-sampled onto the host);
   margin `lobulated` warps the sampling radially by a spherical-harmonic δ(θ, φ) drawn from the library
   power spectrum; an [H01]-style smooth random displacement deforms the outline;
2. occupancy gets the library erf edge (intrinsic σ, PSF already removed in #14): f = ½ erfc((d + σ²/r) / √2σ);
   margin `spiculated` adds tapered radial spicules;
3. tissue classes: states 1/2 → the type's interior HU; 3 (necrotic) → mean − k·std (plan Q9);
   part-solid → solid core deeper than `part_solid_core_fraction` of max depth, ground-glass rim;
   plus the [H01] texture (generated at host-voxel scale, cubic-zoomed to the sub-grid);
4. box integration: F = ⟨f⟩, LF = ⟨f·L⟩ over each host voxel's sub-samples.

Seeds: geometry draws (edge σ, lobulation, deformation, spicules) use the TumorDraw's `shape_seed_hex`;
appearance draws (HU, texture) and the insert's noise use the certificate's extracted seed. A new
certificate therefore re-textures the same lesion; the mask only changes with the draw.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from scipy.special import erfc

from F_render.src import texture as ftex
from F_render.src.lesion_fit import lm_list, real_sh, to_sph
from F_render.src.params import RenderParams
from shared.seedhash import rng


@dataclass
class Lesion:
    bbox: tuple[slice, slice, slice]      # host-grid region (z, y, x)
    F: np.ndarray                         # partial-volume lesion fraction, float32
    LF: np.ndarray                        # ⟨f · L⟩, float32 (HU · fraction)
    center_vox_zyx: np.ndarray            # lesion centre in host voxel coordinates (float)
    radius_mm: float                      # volume-equivalent radius
    hu_core: float                        # class HU used (solid core / single type)
    diag: dict


def _type_params(library: dict, t: str) -> dict:
    if t not in library["types"]:
        raise ValueError(f"lesion library has no type {t!r} (has {sorted(library['types'])})")
    return library["types"][t]


def _block_mean(a: np.ndarray, k: int) -> np.ndarray:
    z, y, x = (n // k for n in a.shape)
    return a.reshape(z, k, y, k, x, k).mean(axis=(1, 3, 5))


def render_lesion(state: np.ndarray, lat_origin_lps, lat_spacing_xyz, host_meta: dict, site_center_lps,
                  draw: dict, library: dict, p: RenderParams, seed_hex: str) -> Lesion:
    k = p.supersample
    h_org = np.asarray(host_meta["origin_mm_lps"], float)[::-1]          # z, y, x
    h_sp = np.asarray(host_meta["spacing_mm_xyz"], float)[::-1]
    h_size = np.asarray(host_meta["size_xyz"], int)[::-1]
    l_sp = np.asarray(lat_spacing_xyz, float)[::-1]
    l_org = np.asarray(lat_origin_lps, float)[::-1]

    # 1. re-centre the lattice's geometric centre on the site centre (E may have grown it elsewhere)
    lat_center = l_org + (np.asarray(state.shape) - 1) / 2 * l_sp
    shift = np.asarray(site_center_lps, float)[::-1] - lat_center
    l_org = l_org + shift
    occ_idx = np.argwhere(state > 0)
    if len(occ_idx) == 0:
        raise ValueError("lattice snapshot has no tumour cells")
    occ_mm = l_org + occ_idx * l_sp
    c_mm = occ_mm.mean(0)
    r_eq = float((3 * len(occ_idx) * l_sp.prod() / (4 * np.pi)) ** (1 / 3))

    t = draw["type"]
    tp = _type_params(library, t)
    shape_seed = draw["shape_seed_hex"]     # geometry: B's per-draw shape seed; appearance: certificate seed
    edge_sd = tp["edge_profile"]["params"]
    g_edge = rng(shape_seed, "F.edge")
    sigma_e = float(np.clip(g_edge.normal(edge_sd.get("sigma_mm_mean", 0.8), edge_sd.get("sigma_mm_std", 0.0)),
                            0.05, None))
    reach = r_eq + 3 * sigma_e + (p.spicule_length_mm if draw["margin"] == "spiculated" else 0) \
        + 2 * p.deform_alpha_mm + 2.0
    lo = np.floor((occ_mm.min(0) - reach - h_org) / h_sp).astype(int)
    hi = np.ceil((occ_mm.max(0) + reach - h_org) / h_sp).astype(int) + 1
    lo, hi = np.clip(lo, 0, h_size), np.clip(hi, 0, h_size)
    bbox = tuple(slice(a, b) for a, b in zip(lo, hi))
    nb = hi - lo
    if np.any(nb <= 0):
        raise ValueError("lesion falls outside the host volume")

    # sub-grid sample positions (mm, z y x)
    axes = [h_org[a] + (lo[a] + (np.arange(nb[a] * k) + 0.5) / k - 0.5) * h_sp[a] for a in range(3)]
    P = np.stack(np.meshgrid(*axes, indexing="ij"), -1)                 # (Z, Y, X, 3)
    sub_sp = h_sp / k
    Q = P - c_mm
    if draw["margin"] == "lobulated":
        g = rng(shape_seed, "F.lobulation")
        sh = tp["shape_params"]
        coef = [1.0]
        for l, m in lm_list(p.lobulation_lmax)[1:]:
            pw = max(sh.get(f"sh_l{l}_power_mean", 0.0), 0.0)
            coef.append(g.normal(0.0, np.sqrt(pw / (2 * l + 1))))
        r, th, ph = to_sph(Q.reshape(-1, 3))
        y00 = real_sh(0, 0, 0.0, 0.0)
        delta = sum(c * real_sh(l, m, th, ph) for c, (l, m) in zip(coef[1:], lm_list(p.lobulation_lmax)[1:]))
        Q = Q / (1.0 + delta / (coef[0] * y00)).reshape(Q.shape[:3] + (1,))
    if p.deform_alpha_mm > 0:
        g = rng(shape_seed, "F.deform")
        for a in range(3):
            d = ndi.gaussian_filter(g.uniform(-1, 1, Q.shape[:3]).astype(np.float32), p.deform_sigma_mm / sub_sp)
            Q[..., a] += d * (p.deform_alpha_mm / (np.abs(d).max() + 1e-12))
    li = np.round((Q + c_mm - l_org) / l_sp).astype(int)
    inside = np.all((li >= 0) & (li < np.asarray(state.shape)), axis=-1)
    st = np.zeros(Q.shape[:3], np.uint8)
    st[inside] = state[li[inside][:, 0], li[inside][:, 1], li[inside][:, 2]]
    del P, Q, li

    # 2. edge profile on occupancy, spicules
    occ = st > 0
    d = ndi.distance_transform_edt(~occ, sampling=sub_sp) - ndi.distance_transform_edt(occ, sampling=sub_sp)
    # erf edge on the signed distance; shifted inward by σ²/r so a convex lesion keeps its lattice volume
    # (for a sphere, V(erf edge at R − δ) ≈ 4π/3 [(R − δ)³ + 3(R − δ)σ²] = 4π/3 R³ at δ ≈ σ²/R)
    f = 0.5 * erfc((d + sigma_e ** 2 / max(r_eq, 1e-6)) / (np.sqrt(2) * sigma_e))
    depth = np.maximum(-d, 0.0)
    del d
    if draw["margin"] == "spiculated":
        g = rng(shape_seed, "F.spiculation")
        v = g.normal(size=(p.spicule_count, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        Pc = np.stack(np.meshgrid(*[(np.arange(n) + 0.5) * s for n, s in zip(f.shape, sub_sp)], indexing="ij"), -1)
        cc = c_mm - (h_org + (lo - 0.5) * h_sp)
        for u in v:
            rel = Pc - cc
            tt = rel @ u - r_eq * 0.8
            perp = np.linalg.norm(rel - (rel @ u)[..., None] * u, axis=-1)
            w = 0.5 * p.spicule_width_mm * np.clip(1 - tt / p.spicule_length_mm, 0, 1)
            spic = (tt > 0) & (tt < p.spicule_length_mm) & (perp < np.maximum(w, 1e-6))
            f = np.maximum(f, spic.astype(np.float32))
        del Pc

    # 3. tissue classes + texture
    g_hu = rng(seed_hex, "F.hu")

    def class_hu(tt):
        q = _type_params(library, tt)["hu"]
        return float(np.clip(g_hu.normal(q["mean"], q["std"]), q["mean"] - 2 * q["std"], q["mean"] + 2 * q["std"]))

    def nec_hu(tt, base):
        return base - p.necrotic_offset_std * _type_params(library, tt)["hu"]["std"]

    L = np.zeros(f.shape, np.float32)
    if t == "part-solid":
        hu_s, hu_g = class_hu("solid"), class_hu("ground-glass")
        core = depth > p.part_solid_core_fraction * depth.max()
        L[:] = hu_g
        L[core] = hu_s
        L[(st == 3) & core] = nec_hu("solid", hu_s)
        hu_core = hu_s
        tex_std = _type_params(library, "part-solid")["shape_params"].get("texture_std_hu_mean", 0.0)
    else:
        hu_core = class_hu(t)
        L[:] = hu_core
        L[st == 3] = nec_hu(t, hu_core)
        tex_std = tp["shape_params"].get("texture_std_hu_mean", 0.0)
    g_tex = rng(seed_hex, "F.texture")
    eta = float(g_tex.uniform(*p.texture_eta_range))
    tex = ftex.texture_field(tuple(nb), 0.0, tex_std, g_tex, eta, p.texture_sigma_b_vox)
    L += ndi.zoom(tex, k, order=3, grid_mode=True, mode="grid-mirror")[: L.shape[0], : L.shape[1], : L.shape[2]]
    if p.capsule:
        L += ftex.capsule(f, p.capsule_bounds, p.capsule_sigma_d_vox * k, p.capsule_d_hu)

    # 4. box integration onto the host grid
    F = _block_mean(f.astype(np.float32), k)
    LF = _block_mean((f * L).astype(np.float32), k)
    center_vox = (c_mm - h_org) / h_sp
    diag = {"sigma_edge_mm": sigma_e, "texture_eta": eta, "texture_std_hu": tex_std, "r_eq_mm": r_eq,
            "lattice_shift_mm_zyx": [round(float(v), 3) for v in shift], "hu_core": hu_core,
            "sub_grid": list(f.shape), "lesion_volume_mm3_partial": float(F.sum() * h_sp.prod()),
            "lattice_volume_mm3": float(len(occ_idx) * l_sp.prod())}
    return Lesion(bbox, F, LF, center_vox, r_eq, hu_core, diag)
