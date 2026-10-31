"""F5 — cell lattice → lesion HU on the host grid with true partial volume, from the LIDC-fitted library.

1. the lattice (a growth snapshot, `state` uint8 z,y,x) is re-centred on the site and resampled onto a
   sub-grid of `supersample`³ points per host voxel; margin `lobulated` warps the sampling radially by a
   spherical-harmonic δ(θ, φ) drawn from the library power spectrum; a smooth random displacement deforms
   the outline ([H01]);
2. occupancy gets the library erf edge: f = ½ erfc((d + σ²/r) / √2σ); margin `spiculated` adds tapered
   radial spicules;
3. tissue classes: states 1/2 → the type's interior HU; 3 (necrotic) → mean − k·std; part-solid → solid
   core deeper than `part_solid_core_fraction` of max depth, ground-glass rim; plus the [H01] texture;
4. box integration: F = ⟨f⟩, LF = ⟨f·L⟩ over each host voxel's sub-samples.

Seeds: geometry draws (edge σ, lobulation, deformation, spicules) use the tile's geometry seed; appearance
draws (HU, texture) and the insert's noise use the appearance seed.

Library (data/lesion_model_library.json) = scalars fitted to 41 LIDC nodules (no patient voxels). F5 plan
Q4: the library's solid HU mean (−22 HU, a partial-volume bias of 2.5 mm slices) renders too dark, so
`load_library()` replaces the solid class HU with N(+30, 30) — this also sets part-solid's solid core.
Calcified has no library entry: `procedural_lesion_3d` wraps the procedural F2.1 `build_lesion` cube.
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/lesion_render.py @ 2609cbe (Lesion,
# _type_params, _block_mean, render_lesion verbatim apart from the draw keys), lesion_fit.py (real_sh,
# lm_list, to_sph), texture.py (texture_field, mass_effect) and params.py (RenderParams). Added:
# load_library (Q4 solid HU), procedural_lesion_3d (calcified / fallback).

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.special import erfc, sph_harm_y

from imaging.seedhash import rng

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SOLID_HU_Q4 = {"mean": 30.0, "std": 30.0}


# ---------------------------------------------------------------- params.py
@dataclass(frozen=True)
class RenderParams:
    method: str = "image-domain additive delta v1"
    supersample: int = 4                      # sub-voxels per host axis; box-integrated (partial volume)
    texture_eta_range: tuple[float, float] = (1.1, 1.5)
    texture_sigma_b_vox: float = 0.6
    deform_alpha_mm: float = 0.5
    deform_sigma_mm: float = 3.0
    lobulation_lmax: int = 4
    spicule_count: int = 10
    spicule_length_mm: float = 6.0
    spicule_width_mm: float = 0.6
    mass_effect: bool = True
    mass_effect_intensity: float = 30.0
    mass_effect_gamma_factor: float = 1.3
    ggo_alpha: float = 1.0
    part_solid_core_fraction: float = 0.5
    necrotic_offset_std: float = 1.0
    background_kernel_mm: float = 12.0
    anatomy_sigma_vox: float = 1.0
    residual_noise: bool = True
    psf_sigma_mm_zyx: tuple[float, float, float] | None = None   # None = from the scanner fingerprint
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}


# ---------------------------------------------------------------- lesion_fit.py (spherical harmonics)
def real_sh(l: int, m: int, theta, phi):
    """Orthonormal real spherical harmonic; θ polar, φ azimuth."""
    if m == 0:
        return sph_harm_y(l, 0, theta, phi).real
    y = sph_harm_y(l, abs(m), theta, phi)
    return np.sqrt(2) * (-1) ** m * (y.real if m > 0 else y.imag)


def lm_list(lmax: int):
    return [(l, m) for l in range(lmax + 1) for m in range(-l, l + 1)]


def to_sph(p):
    r = np.linalg.norm(p, axis=1)
    theta = np.arccos(np.clip(p[:, 0] / np.maximum(r, 1e-12), -1, 1))   # polar about the z axis (index 0)
    phi = np.arctan2(p[:, 1], p[:, 2])
    return r, theta, phi


# ---------------------------------------------------------------- texture.py
def texture_field(shape_zyx, hu_mean: float, hu_std: float, g: np.random.Generator,
                  eta: float, sigma_b_vox: float = 0.6) -> np.ndarray:
    """[H01] texture: N(0, 1) → cubic up-scaling by η → Gaussian blur σb → std reset to `hu_std`."""
    shape = np.asarray(shape_zyx)
    small = np.maximum(np.ceil(shape / eta).astype(int), 2)
    t = g.normal(0.0, 1.0, size=tuple(small))
    t = ndi.zoom(t, eta, order=3, grid_mode=True, mode="grid-mirror")
    t = t[tuple(slice(0, n) for n in shape)]
    if t.shape != tuple(shape):
        t = np.pad(t, [(0, n - m) for n, m in zip(shape, t.shape)], mode="reflect")
    t = ndi.gaussian_filter(t, sigma_b_vox)
    s = t.std()
    return (hu_mean + (t - t.mean()) * (hu_std / s if s > 0 else 0.0)).astype(np.float32)


def mass_effect(vol: np.ndarray, center_vox_zyx, radius_mm: float, spacing_mm_zyx,
                intensity: float = 30.0, gamma_factor: float = 1.3) -> np.ndarray:
    """[H01] eq. 5 local scaling warp: γ' = (1 − (1 − γ/γmax)² · I/100) · γ, γmax = 1.3 r."""
    sp = np.asarray(spacing_mm_zyx, float)
    gmax = gamma_factor * radius_mm
    c = np.asarray(center_vox_zyx, float)
    coords = np.indices(vol.shape, dtype=np.float64)
    off_mm = (coords - c[:, None, None, None]) * sp[:, None, None, None]
    g = np.sqrt((off_mm ** 2).sum(0))
    scale = np.where(g < gmax, 1.0 - (1.0 - g / gmax) ** 2 * intensity / 100.0, 1.0)
    src = c[:, None, None, None] + off_mm * scale / sp[:, None, None, None]
    return ndi.map_coordinates(vol.astype(np.float32), src, order=1, mode="nearest")


# ---------------------------------------------------------------- lesion_render.py
@dataclass
class Lesion:
    bbox: tuple[slice, slice, slice]      # host-grid region (z, y, x)
    F: np.ndarray                         # partial-volume lesion fraction, float32
    LF: np.ndarray                        # ⟨f · L⟩, float32 (HU · fraction)
    center_vox_zyx: np.ndarray            # lesion centre in host voxel coordinates (float)
    radius_mm: float                      # volume-equivalent radius
    hu_core: float                        # class HU used (solid core / single type)
    diag: dict


def load_library() -> dict:
    """Copied LIDC lesion library with the Q4 solid-HU replacement applied (and recorded)."""
    with open(os.path.join(DATA, "lesion_model_library.json")) as f:
        lib = json.load(f)
    lib = copy.deepcopy(lib)
    lib["types"]["solid"]["hu_library"] = lib["types"]["solid"]["hu"]
    lib["types"]["solid"]["hu"] = dict(SOLID_HU_Q4)
    return lib


def _type_params(library: dict, t: str) -> dict:
    if t not in library["types"]:
        raise ValueError(f"lesion library has no type {t!r} (has {sorted(library['types'])})")
    return library["types"][t]


def _block_mean(a: np.ndarray, k: int) -> np.ndarray:
    z, y, x = (n // k for n in a.shape)
    return a.reshape(z, k, y, k, x, k).mean(axis=(1, 3, 5))


def _volume_preserving_shift(d: np.ndarray, sigma_e: float, target_mm3: float, sub_vox_mm3: float,
                             start: float) -> float:
    """Edge offset δ so that Σ ½ erfc((d + δ)/√2σ) · v_sub equals the grown lattice volume (F5 addition).

    RE's fixed δ = σ²/r keeps the volume of a sphere only; the outline deformation and SH lobulation
    change it by several % (lobulated ≈ +16 %). Solving δ keeps the rendered lesion volume equal to the
    growth ground truth (plan AC-6). Bisection on a histogram of d, so it costs one pass over the grid.
    """
    lo_d, hi_d = float(d.min()), float(d.max())
    edges = np.linspace(lo_d, hi_d, 4097)
    cnt, _ = np.histogram(d, edges)
    mid = 0.5 * (edges[1:] + edges[:-1])

    def vol(s):
        return float((cnt * 0.5 * erfc((mid + s) / (np.sqrt(2) * sigma_e))).sum() * sub_vox_mm3)

    a, b = start - 5 * sigma_e - 3.0, start + 5 * sigma_e + 3.0   # vol is decreasing in δ
    if not (vol(a) >= target_mm3 >= vol(b)):
        return start
    for _ in range(50):
        m = 0.5 * (a + b)
        if vol(m) > target_mm3:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


def render_lesion(state: np.ndarray, lat_origin_lps, lat_spacing_xyz, host_meta: dict, site_center_lps,
                  draw: dict, library: dict, p: RenderParams, seed_hex: str) -> Lesion:
    """draw = {type, margin, shape_seed_hex}; seed_hex = appearance seed."""
    k = p.supersample
    h_org = np.asarray(host_meta["origin_mm_lps"], float)[::-1]          # z, y, x
    h_sp = np.asarray(host_meta["spacing_mm_xyz"], float)[::-1]
    h_size = np.asarray(host_meta["size_xyz"], int)[::-1]
    l_sp = np.asarray(lat_spacing_xyz, float)[::-1]
    l_org = np.asarray(lat_origin_lps, float)[::-1]

    # 1. re-centre the lattice's geometric centre on the site centre
    lat_center = l_org + (np.asarray(state.shape) - 1) / 2 * l_sp
    shift = np.asarray(site_center_lps, float)[::-1] - lat_center
    l_org = l_org + shift
    # E grown in real lung HU leaves 1.5–8 % isolated unfilled voxels inside the mass (parenchyma levels with
    # take-rates < 1); each one is "outside" for the distance transform and caps the interior depth at
    # ~5 mm, turning the core into a partial-volume haze. Enclosed holes become proliferating cells for the
    # geometry (F5 change; RE only ran on uniform stub phantoms, where this never shows).
    holes = ndi.binary_fill_holes(state > 0) & (state == 0)
    if holes.any():
        state = np.where(holes, np.uint8(1), state)
    occ_idx = np.argwhere(state > 0)
    if len(occ_idx) == 0:
        raise ValueError("lattice snapshot has no tumour cells")
    occ_mm = l_org + occ_idx * l_sp
    c_mm = occ_mm.mean(0)
    r_eq = float((3 * len(occ_idx) * l_sp.prod() / (4 * np.pi)) ** (1 / 3))

    t = draw["type"]
    tp = _type_params(library, t)
    shape_seed = draw["shape_seed_hex"]
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

    axes = [(h_org[a] + (lo[a] + (np.arange(nb[a] * k) + 0.5) / k - 0.5) * h_sp[a] - c_mm[a]).astype(np.float32)
            for a in range(3)]
    Q = np.stack(np.meshgrid(*axes, indexing="ij"), -1)                 # (Z, Y, X, 3), relative to c_mm
    sub_sp = h_sp / k
    if draw["margin"] == "lobulated":
        g = rng(shape_seed, "F.lobulation")
        sh = tp["shape_params"]
        coef = [1.0]
        for l, m in lm_list(p.lobulation_lmax)[1:]:
            pw = max(sh.get(f"sh_l{l}_power_mean", 0.0), 0.0)
            coef.append(g.normal(0.0, np.sqrt(pw / (2 * l + 1))))
        # δ(θ, φ) is a smooth function of direction (l ≤ 4): evaluated at the host-voxel centres and
        # linearly up-sampled to the sub-grid (F5 speed change; RE evaluates every sub-sample)
        hc = np.stack(np.meshgrid(*[a.reshape(-1, k).mean(1) for a in axes], indexing="ij"), -1)
        r, th, ph = to_sph(hc.reshape(-1, 3).astype(np.float64))
        y00 = real_sh(0, 0, 0.0, 0.0)
        delta = sum(c * real_sh(l, m, th, ph) for c, (l, m) in zip(coef[1:], lm_list(p.lobulation_lmax)[1:]))
        scale = (1.0 / (1.0 + delta / (coef[0] * y00))).reshape(hc.shape[:3]).astype(np.float32)
        scale = ndi.zoom(scale, k, order=1, grid_mode=True, mode="nearest")[: Q.shape[0], : Q.shape[1], : Q.shape[2]]
        Q *= scale[..., None]
    if p.deform_alpha_mm > 0:
        # smooth displacement (σ = deform_sigma_mm ≫ voxel) drawn + blurred on the host grid, then
        # linearly up-sampled to the sub-grid (F5 speed change; RE blurs on the sub-grid directly)
        g = rng(shape_seed, "F.deform")
        for a in range(3):
            d = ndi.gaussian_filter(g.uniform(-1, 1, tuple(nb)).astype(np.float32), p.deform_sigma_mm / h_sp)
            d = ndi.zoom(d, k, order=1, grid_mode=True, mode="nearest")[: Q.shape[0], : Q.shape[1], : Q.shape[2]]
            Q[..., a] += d * (p.deform_alpha_mm / (np.abs(d).max() + 1e-12))
    li = np.round((Q + (c_mm - l_org).astype(np.float32)) / l_sp.astype(np.float32)).astype(np.int32)
    inside = np.all((li >= 0) & (li < np.asarray(state.shape)), axis=-1)
    st = np.zeros(Q.shape[:3], np.uint8)
    st[inside] = state[li[inside][:, 0], li[inside][:, 1], li[inside][:, 2]]
    del Q, li

    # 2. edge profile on occupancy, spicules
    occ = st > 0
    d = ndi.distance_transform_edt(~occ, sampling=sub_sp) - ndi.distance_transform_edt(occ, sampling=sub_sp)
    edge_shift = _volume_preserving_shift(d, sigma_e, len(occ_idx) * l_sp.prod(), sub_sp.prod(),
                                     sigma_e ** 2 / max(r_eq, 1e-6))
    f = 0.5 * erfc((d + edge_shift) / (np.sqrt(2) * sigma_e))
    depth = np.maximum(-d, 0.0)
    del d
    if draw["margin"] == "spiculated":
        g = rng(shape_seed, "F.spiculation")
        v = g.normal(size=(p.spicule_count, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        cc = c_mm - (h_org + (lo - 0.5) * h_sp)
        for u in v:
            # evaluate each spicule only inside its own bounding box (F5 speed change; same geometry)
            ends = np.stack([cc + u * r_eq * 0.8, cc + u * (r_eq * 0.8 + p.spicule_length_mm)])
            b_lo = np.clip(np.floor((ends.min(0) - p.spicule_width_mm) / sub_sp).astype(int) - 1, 0, f.shape)
            b_hi = np.clip(np.ceil((ends.max(0) + p.spicule_width_mm) / sub_sp).astype(int) + 2, 0, f.shape)
            if np.any(b_hi <= b_lo):
                continue
            box = tuple(slice(a, b) for a, b in zip(b_lo, b_hi))
            Pc = np.stack(np.meshgrid(*[(np.arange(a, b) + 0.5) * s for a, b, s in zip(b_lo, b_hi, sub_sp)],
                                      indexing="ij"), -1)
            rel = Pc - cc
            tt = rel @ u - r_eq * 0.8
            perp = np.linalg.norm(rel - (rel @ u)[..., None] * u, axis=-1)
            w = 0.5 * p.spicule_width_mm * np.clip(1 - tt / p.spicule_length_mm, 0, 1)
            spic = (tt > 0) & (tt < p.spicule_length_mm) & (perp < np.maximum(w, 1e-6))
            f[box] = np.maximum(f[box], spic.astype(np.float32))

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
    tex = texture_field(tuple(nb), 0.0, tex_std, g_tex, eta, p.texture_sigma_b_vox)

    # 4. box integration onto the host grid. The texture lives at host-voxel scale, so it is added after
    # integration as tex·F (F5 speed change; RE cubic-zooms it onto the sub-grid first — equal up to the
    # sub-voxel variation of the zoomed texture)
    F = _block_mean(f.astype(np.float32), k)
    LF = _block_mean((f * L).astype(np.float32), k) + tex * F
    center_vox = (c_mm - h_org) / h_sp
    diag = {"sigma_edge_mm": sigma_e, "edge_shift_mm": round(float(edge_shift), 4), "filled_holes_vox": int(holes.sum()),
            "texture_eta": eta, "texture_std_hu": tex_std, "r_eq_mm": r_eq,
            "hu_core": hu_core, "hu_source": {"solid": "f2.1-constant", "part-solid": "f2.1-constant core + library rim"}.get(t, "library"),
            "lesion_volume_mm3_partial": float(F.sum() * h_sp.prod()),
            "lattice_volume_mm3": float(len(occ_idx) * l_sp.prod())}
    return Lesion(bbox, F, LF, center_vox, r_eq, hu_core, diag)


def procedural_lesion_3d(params, host_meta: dict, site_zyx, seed: int) -> Lesion:
    """F2.1 procedural cube (calcified / fallback) resampled onto the anisotropic host grid."""
    from imaging.lesion import LUNG_BG_HU, build_lesion

    h_sp = np.asarray(host_meta["spacing_mm_xyz"], float)[::-1]
    h_size = np.asarray(host_meta["size_xyz"], int)[::-1]
    les = build_lesion(params, float(h_sp[1]), seed=seed)              # isotropic at the in-plane spacing
    zf = h_sp[1] / h_sp[0]
    alpha = np.clip(ndi.zoom(les.alpha, (zf, 1, 1), order=1), 0, 1).astype(np.float32)
    hu = ndi.zoom(les.volume_hu, (zf, 1, 1), order=1).astype(np.float32) + LUNG_BG_HU
    c = np.asarray(site_zyx, int)
    half = np.asarray(alpha.shape) // 2
    lo = c - half
    hi = lo + np.asarray(alpha.shape)
    clo, chi = np.clip(lo, 0, h_size), np.clip(hi, 0, h_size)
    sl_src = tuple(slice(a - l, b - l) for a, b, l in zip(clo, chi, lo))
    F, L = alpha[sl_src], hu[sl_src]
    r_mm = float((3 * alpha.sum() * h_sp.prod() / (4 * np.pi)) ** (1 / 3))
    bbox = tuple(slice(a, b) for a, b in zip(clo, chi))
    diag = {"hu_core": float(np.median(L[F > 0.5])) if (F > 0.5).any() else float("nan"),
            "hu_source": "procedural-f2.1", "r_eq_mm": r_mm,
            "lesion_volume_mm3_partial": float(F.sum() * h_sp.prod())}
    return Lesion(bbox, F, (F * L).astype(np.float32), c.astype(float), r_mm, diag["hu_core"], diag)
