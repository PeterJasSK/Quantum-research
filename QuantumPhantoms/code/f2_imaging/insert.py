"""F2 insertion — place a lesion into a CT slice with matched noise (plan §4, AC-2/AC-4).

Pure numpy. `insert_lesion` adds the lesion's central-slice HU delta at a point and adds
Gaussian noise whose sigma matches the local background grain, so the lesion does not read
as pasted (parent §10 Path A). `place_for_lobe` maps the decoded lobe to an approximate
slice region (no lung segmentation in the MVP). Windowing + cropping produce the uint8 tile.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

# Approximate slice-region centres per lobe, as (col_frac, row_frac).
# Radiological convention: patient-right lung appears on the LEFT of the image.
_LOBE_REGION = {
    "RUL": (0.32, 0.32),
    "RML": (0.32, 0.50),
    "RLL": (0.32, 0.70),
    "LUL": (0.68, 0.32),
    "LLL": (0.68, 0.70),
}


def lung_field_mask(arr, is_hu: bool):
    """Boolean mask of the lung fields: dark parenchyma INSIDE the body (F3.1, AC-2).

    Threshold dark pixels, label connected components, drop any component touching the
    image border (that is outside-body air) and any tiny speck (airways/noise); what
    remains is the lungs. Returns None if nothing plausible is found (caller falls back
    to the region heuristic).
    """
    from scipy import ndimage

    dark = (arr < -400.0) if is_hu else (arr < 70.0)
    labels, n = ndimage.label(dark)
    if n == 0:
        return None
    h, w = arr.shape
    border_ids = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
    keep = np.zeros_like(dark, dtype=bool)
    min_area = 0.002 * h * w
    for i in range(1, n + 1):
        if i in border_ids:
            continue
        comp = labels == i
        if comp.sum() < min_area:
            continue
        keep |= comp
    return keep if keep.any() else None


def place_for_lobe(lobe: str, shape, rng, mask=None) -> tuple[int, int]:
    """(x, y) insertion centre for the lobe (AC-2/AC-4).

    With a lung-field `mask`, sample a mask pixel near the lobe's target region (guarantees
    the nodule lands inside a lung). Without a mask, fall back to the region heuristic.
    """
    h, w = shape
    cf, rf = _LOBE_REGION.get(lobe, (0.5, 0.5))
    if mask is not None:
        ys, xs = np.where(mask)
        if len(xs):
            tx, ty = cf * w, rf * h
            d = (xs - tx) ** 2 + (ys - ty) ** 2
            k = max(1, len(d) // 5)          # the 20% of lung nearest the lobe region
            idx = np.argsort(d)[:k]
            j = int(rng.integers(0, len(idx)))
            return int(xs[idx[j]]), int(ys[idx[j]])
    cf += rng.uniform(-0.06, 0.06)
    rf += rng.uniform(-0.06, 0.06)
    x = int(np.clip(cf, 0.08, 0.92) * w)
    y = int(np.clip(rf, 0.08, 0.92) * h)
    return x, y


def _match_noise(ct_slice, x, y, half, rng):
    """Local background sigma from a patch around (x, y), robust to the edge."""
    h, w = ct_slice.shape
    y0, y1 = max(0, y - half), min(h, y + half)
    x0, x1 = max(0, x - half), min(w, x + half)
    patch = ct_slice[y0:y1, x0:x1]
    if patch.size < 16:
        return 0.0
    return float(np.std(patch))


def insert_lesion(ct_slice, hu_delta_2d, alpha_2d, xy, *, is_hu: bool, rng,
                  psf_sigma: float = 0.7) -> np.ndarray:
    """Insert the lesion at xy: soft-alpha composite + scanner PSF blur + matched noise.

    `alpha_2d` is the lesion's partial-volume coverage [0,1] (F2.1 AC-3). The composite is
    convolved with a Gaussian point-spread (reconstruction-kernel blur, AC-4) so the edge
    blends, then correlated noise matched to the local background is added (AC-5). HU delta
    is scaled to the 0..255 window for intensity (PNG/bundled) backgrounds.
    """
    out = ct_slice.astype(np.float32).copy()
    h, w = out.shape
    lh, lw = hu_delta_2d.shape
    x, y = xy

    ty0, tx0 = y - lh // 2, x - lw // 2
    sy0, sy1 = max(0, ty0), min(h, ty0 + lh)
    sx0, sx1 = max(0, tx0), min(w, tx0 + lw)
    ly0, ly1 = sy0 - ty0, sy0 - ty0 + (sy1 - sy0)
    lx0, lx1 = sx0 - tx0, sx0 - tx0 + (sx1 - sx0)
    if sy1 <= sy0 or sx1 <= sx0:
        return out

    delta = hu_delta_2d[ly0:ly1, lx0:lx1].astype(np.float32)
    alpha = alpha_2d[ly0:ly1, lx0:lx1].astype(np.float32)
    if not is_hu:
        delta = delta / (1500.0 / 255.0)  # HU -> lung-window intensity units

    region = out[sy0:sy1, sx0:sx1].astype(np.float32)
    composite = region + delta * alpha            # soft partial-volume blend (AC-3)

    if psf_sigma > 0:
        composite = gaussian_filter(composite, psf_sigma)   # scanner PSF (AC-4)

    sigma = _match_noise(out, x, y, max(lh, lw), rng)
    if sigma > 0:
        noise = gaussian_filter(rng.normal(0.0, 1.0, composite.shape).astype(np.float32), 0.6)
        noise = noise * (sigma * 0.7) / (noise.std() + 1e-6)   # correlated, matched (AC-5)
        composite = composite + noise * (alpha > 0.02)

    out[sy0:sy1, sx0:sx1] = composite
    return out


def window_to_uint8(arr, *, is_hu: bool, wl: float = -600.0, ww: float = 1500.0):
    """Lung-window an HU array to uint8; pass intensity arrays through with a clip."""
    if is_hu:
        lo, hi = wl - ww / 2.0, wl + ww / 2.0
        scaled = (arr - lo) / (hi - lo)
    else:
        scaled = arr / 255.0
    return (np.clip(scaled, 0.0, 1.0) * 255.0).astype(np.uint8)


def crop(arr, xy, size: int):
    """size x size crop centered on xy, zero-padded at the edges."""
    h, w = arr.shape
    x, y = xy
    half = size // 2
    out = np.zeros((size, size), dtype=arr.dtype)
    sy0, sy1 = max(0, y - half), min(h, y - half + size)
    sx0, sx1 = max(0, x - half), min(w, x - half + size)
    dy0 = sy0 - (y - half)
    dx0 = sx0 - (x - half)
    out[dy0:dy0 + (sy1 - sy0), dx0:dx0 + (sx1 - sx0)] = arr[sy0:sy1, sx0:sx1]
    return out
