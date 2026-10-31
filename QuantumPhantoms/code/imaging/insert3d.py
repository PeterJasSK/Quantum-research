"""F5 — additive-delta insertion into a 3-D host region of interest (ROI), with the host's own blur + noise.

Within the ROI the host is split into anatomy A = G_σ(host) and noise N = host − A.
  1. mass effect ([H01] eq. 5) warps A only (inside the lungs) — the host's noise N is never resampled;
  2. background B = normalised-convolution mean of A over lung parenchyma (no lesion);
  3. δ = ⟨f·L⟩ − ⟨f⟩·B on the host grid, clipped to the lung mask (juxtapleural), blurred by the 3-D PSF
     from the scanner fingerprint — only the delta is blurred, the host keeps its own resolution and noise;
  4. composition, then N added back:
       solid / part-solid / calcified   hybrid = A' + N + max(A', B + δ) − max(A', B)
       ground-glass                     hybrid = A' + N + α δ        (additive α-blend: parenchyma shows)
  5. residual noise: if the lesion-interior σ is below the surrounding lung's, top it up with NPS-shaped
     noise inside the lesion (appearance seed, label F.noise) — the same seed every frame, so a growth
     sequence never flickers;
  6. round + clip to int16 [−1024, 3071]. Outside the touched region the ROI is unchanged.
No vessel mask (F5 plan Q8): the max-rule above uses A' itself, so bright host structure still wins; the
σ reference shell of step 5 keeps aerated voxels only (A < −500 HU) in place of RE's `~vessels`.
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/insert.py @ 2609cbe (_grow, _local_sigma,
# insert); changed: no vessel argument (Q8), operates on a ROI copy (never the full volume), adds the
# volume check volume_pd_pct (rendered partial volume vs lattice volume, AC-6).

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from imaging import noise as fnoise
from imaging.lesion_fitted import Lesion, RenderParams, mass_effect
from imaging.seedhash import rng

HU_MIN, HU_MAX = -1024, 3071


def _grow(bbox, pad, shape):
    return tuple(slice(max(s.start - p, 0), min(s.stop + p, n)) for s, p, n in zip(bbox, pad, shape))


def _local_sigma(x, mask, hp_px=1.5):
    r = x - ndi.gaussian_filter(x, (0, hp_px, hp_px))
    return float(r[mask].std()) if mask.sum() > 20 else float("nan")


def insert(host: np.ndarray, lungs: np.ndarray, sp_zyx, les: Lesion, lesion_type: str,
           fingerprint: dict, p: RenderParams, seed_hex: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """host/lungs = ROI arrays (z, y, x); les rendered on the same ROI grid. Returns (hybrid, mask, diag)."""
    sp = np.asarray(sp_zyx, float)
    psf = np.asarray(p.psf_sigma_mm_zyx or fingerprint["psf_sigma_mm_zyx"], float)
    psf_vox = psf / sp
    me_mm = (p.mass_effect_gamma_factor - 1) * les.radius_mm if p.mass_effect else 0.0
    pad = np.ceil((4 * psf + me_mm + p.background_kernel_mm) / sp).astype(int) + 2
    R = _grow(les.bbox, pad, host.shape)
    off = np.array([les.bbox[a].start - R[a].start for a in range(3)])
    h = host[R].astype(np.float32)
    lung = lungs[R] > 0

    A = ndi.gaussian_filter(h, p.anatomy_sigma_vox)
    N = h - A
    c = les.center_vox_zyx - np.array([s.start for s in R])
    if p.mass_effect and p.mass_effect_intensity > 0:
        Aw = mass_effect(A, c, les.radius_mm, sp, p.mass_effect_intensity, p.mass_effect_gamma_factor)
        A2 = np.where(lung, Aw, A)
    else:
        A2 = A

    F = np.zeros_like(h)
    LF = np.zeros_like(h)
    inner = tuple(slice(o, o + n) for o, n in zip(off, les.F.shape))
    F[inner], LF[inner] = les.F, les.LF
    w = (lung & (F < 0.01)).astype(np.float32)
    sb = p.background_kernel_mm / 2 / sp
    B = ndi.gaussian_filter(A2 * w, sb) / np.maximum(ndi.gaussian_filter(w, sb), 1e-6)

    delta = (LF - F * B) * lung
    db = ndi.gaussian_filter(delta, psf_vox)

    if lesion_type == "ground-glass":
        hyb = A2 + N + p.ggo_alpha * db
    else:
        hyb = A2 + N + np.maximum(A2, B + db) - np.maximum(A2, B)

    mask = (F >= 0.5).astype(np.uint8)
    diag = {"psf_sigma_mm_zyx": psf.tolist()}
    m = mask.astype(bool)
    # σ reference shell: aerated parenchyma only (smoothed anatomy < −500 HU). RE uses `lung & ~vessels`;
    # with no vessel mask (Q8) vessel edges would inflate the shell σ ~2× and over-noise the lesion.
    shell = lung & (A < -500) & ~ndi.binary_dilation(m, iterations=3) & ndi.binary_dilation(m, iterations=8)
    m_in = ndi.binary_erosion(m) if ndi.binary_erosion(m).sum() > 20 else m
    s_in, s_out = _local_sigma(hyb, m_in), _local_sigma(hyb, shell)
    diag.update({"sigma_in_hu": s_in, "sigma_out_hu": s_out, "sigma_added_hu": 0.0})
    if p.residual_noise and np.isfinite(s_in) and np.isfinite(s_out) and s_in < s_out:
        add = float(np.sqrt(s_out ** 2 - s_in ** 2))
        n = fnoise.noise_slices(h.shape, sp[2], sp[1], fingerprint["nps"]["freq_cyc_per_mm"],
                                fingerprint["nps"]["values"], rng(seed_hex, "F.noise"), sigma=1.0)
        if not np.any(fingerprint["nps"]["values"]):
            n = rng(seed_hex, "F.noise").normal(0, 1, h.shape).astype(np.float32)
        hp_gain = _local_sigma(n, np.ones_like(m)) or 1.0
        hyb = hyb + n * (add / hp_gain) * np.clip(F, 0, 1)
        diag["sigma_added_hu"] = add
        diag["sigma_in_after_hu"] = _local_sigma(hyb, m_in)
    diag["sigma_ratio_in_out"] = (diag.get("sigma_in_after_hu", s_in) / s_out) if s_out else float("nan")

    out = host.copy()
    out[R] = np.clip(np.rint(hyb), HU_MIN, HU_MAX).astype(np.int16)
    full_mask = np.zeros(host.shape, np.uint8)
    full_mask[R] = mask
    lat_v = les.diag.get("lattice_volume_mm3")
    if lat_v:
        diag["volume_pd_pct"] = 100.0 * (float(les.F.sum() * sp.prod()) - lat_v) / lat_v
    return out, full_mask, diag
