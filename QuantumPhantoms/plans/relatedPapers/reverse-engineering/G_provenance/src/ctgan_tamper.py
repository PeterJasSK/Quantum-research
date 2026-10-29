"""CT-GAN-style 3-D injection / removal (target #19; Mirsky G01 §5 steps 2-12), GAN-free (AC-9).

Every non-learned step follows G01; step 7 (the cGAN in-painter) is replaced by a classical one:
removal = harmonic (Laplace) fill of the masked 16^3 from its boundary; injection = that fill plus a
Gaussian-edged solid nodule (10-16 mm, 0-60 HU). Touch-up and merge are eq. 1-2 with alpha = 500,
beta = 70. numpy / scipy only. Arrays are (z, y, x) HU; meta spacing is (x, y, z) mm.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import diags, identity, kron
from scipy.sparse.linalg import splu

CUBE_MM, MASK_MM = 32, 16
ALPHA, BETA = 500.0, 70.0
HU_LO, HU_HI = -1024, 3071
NODULE_MM, NODULE_HU = (10.0, 16.0), (0.0, 60.0)


def equalize(cube: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    """Histogram equalisation to [-1, 1] (steps 4-5). Returns (normalised, table) for `unequalize`."""
    vals = np.sort(cube.ravel())
    cdf = (np.arange(vals.size) + 0.5) / vals.size
    return 2.0 * np.interp(cube, vals, cdf) - 1.0, (vals, cdf)


def unequalize(norm: np.ndarray, table: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    vals, cdf = table
    return np.interp((np.clip(norm, -1, 1) + 1.0) / 2.0, cdf, vals)


@lru_cache(maxsize=8)
def _box_laplacian(shape: tuple[int, int, int]):
    """LU of the 7-point Dirichlet Laplacian on a box of `shape` unknowns."""
    ops = [diags([-1.0, -1.0], [-1, 1], shape=(k, k)) for k in shape]
    eye = [identity(k) for k in shape]
    a = 6.0 * identity(int(np.prod(shape))) + kron(kron(ops[0], eye[1]), eye[2]) \
        + kron(kron(eye[0], ops[1]), eye[2]) + kron(kron(eye[0], eye[1]), ops[2])
    return splu(a.tocsc())


def harmonic_fill(cube: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Solve Laplace(u) = 0 inside the box `mask` with the surrounding voxels as Dirichlet data (step 7)."""
    zz, yy, xx = (np.nonzero(mask.any(axis=ax))[0] for ax in ((1, 2), (0, 2), (0, 1)))
    box = tuple(slice(a[0], a[-1] + 1) for a in (zz, yy, xx))
    shape = tuple(s.stop - s.start for s in box)
    if int(mask.sum()) != int(np.prod(shape)):
        raise ValueError("harmonic_fill needs a box-shaped mask")
    pad = cube[tuple(slice(s.start - 1, s.stop + 1) for s in box)].astype(float)
    b = np.zeros(shape)
    for ax in range(3):
        for side in (0, -1):
            sl = [slice(1, -1)] * 3
            sl[ax] = side
            tgt = [slice(None)] * 3
            tgt[ax] = 0 if side == 0 else -1
            b[tuple(tgt)] += pad[tuple(sl)]
    out = cube.astype(float).copy()
    out[box] = _box_laplacian(shape).solve(b.ravel()).reshape(shape)
    return out


def merge_weights(x: np.ndarray, g: np.ndarray, alpha: float = ALPHA, beta: float = BETA) -> np.ndarray:
    """W_{alpha,beta}(x) = G(x) / (1 + exp(-(x + alpha) / beta))  (eq. 1)."""
    return g / (1.0 + np.exp(-(x + alpha) / beta))


def merge(w: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """merge(x, y) = W * x + (1 - W) * y  (eq. 2)."""
    return w * x + (1.0 - w) * y


def _cuboid_slices(center_zyx, meta, shape):
    """Per-axis (index array, in-range slice) of the cuboid whose rescale to 1 mm gives 32^3 (step 2)."""
    sp_zyx = meta["spacing_mm_xyz"][::-1]
    idxs, n = [], []
    for c, sp, dim in zip(center_zyx, sp_zyx, shape):
        k = max(int(round(CUBE_MM / sp)), 2)
        idxs.append(np.clip(np.arange(c - k // 2, c - k // 2 + k), 0, dim - 1))
        n.append(k)
    return idxs, n


def _tamper(vol: np.ndarray, meta: dict, center_zyx, rng: np.random.Generator | None, nodule: bool):
    idxs, n = _cuboid_slices(center_zyx, meta, vol.shape)
    sp_zyx = np.array(meta["spacing_mm_xyz"][::-1], float)
    x_r = vol[np.ix_(*idxs)].astype(float)                                    # step 2: cut
    cube = ndi.zoom(x_r, [CUBE_MM / k for k in n], order=3)                   # step 3: 1:1:1 mm
    norm, table = equalize(cube)                                              # steps 4-5
    lo, hi = (CUBE_MM - MASK_MM) // 2, (CUBE_MM + MASK_MM) // 2
    mask = np.zeros(cube.shape, bool)
    mask[lo:hi, lo:hi, lo:hi] = True                                          # step 6: zero the centre
    filled = harmonic_fill(np.where(mask, 0.0, norm), mask)                   # step 7: classical in-paint
    gen = unequalize(filled, table)                                           # step 8-9
    info = {"cuboid_voxels": n, "center_zyx": [int(c) for c in center_zyx]}
    if nodule:
        d, hu = rng.uniform(*NODULE_MM), rng.uniform(*NODULE_HU)
        grid = np.indices(cube.shape).astype(float) - (CUBE_MM - 1) / 2.0
        r = np.sqrt((grid ** 2).sum(0))
        s = 1.0 / (1.0 + np.exp((r - d / 2.0) / 0.8))                        # Gaussian-like soft edge
        gen = gen * (1 - s) + hu * s
        info |= {"diameter_mm": float(d), "hu": float(hu)}
    x_g = np.clip(ndi.zoom(gen, [k / CUBE_MM for k in n], order=3), HU_LO, HU_HI)  # step 10: spline back
    air = x_r[x_r < -600]
    sigma = float(air.std()) if air.size else 0.0                             # step 11: AWGN touch-up
    noise = rng.normal(0.0, sigma, x_g.shape) if (rng is not None and sigma) else 0.0
    x_g = x_g + noise
    region = np.zeros(x_r.shape)
    sl = tuple(slice(int(k * lo / CUBE_MM), int(round(k * hi / CUBE_MM))) for k in n)
    region[sl] = 1.0
    g = ndi.gaussian_filter(region, 1.5 / sp_zyx)
    g = g / g.max()
    w = merge_weights(np.maximum(x_g, x_r), g)                                # eq. 1 (tissue of either cuboid)
    merged = merge(w, x_g, x_r)                                               # eq. 2
    out = vol.copy()
    out[np.ix_(*idxs)] = np.clip(np.rint(merged), HU_LO, HU_HI).astype(vol.dtype)  # step 12: paste
    info["sigma_hu"] = sigma
    info["slices_z"] = sorted(set(int(i) for i in idxs[0]))
    return out, info


def inject(vol, meta, center_zyx, rng):
    """Add a solid nodule at `center_zyx` (voxel index)."""
    return _tamper(vol, meta, center_zyx, rng, True)


def remove(vol, meta, center_zyx, rng):
    """Erase the finding at `center_zyx` (harmonic fill + lung-noise touch-up)."""
    return _tamper(vol, meta, center_zyx, rng, False)


def pick_lung_site(lungs_zyx: np.ndarray, meta: dict, away_from_zyx, rng, min_mm: float = 15.0):
    """Random lung voxel >= min_mm from `away_from_zyx` and a full cuboid away from the volume border."""
    sp = np.array(meta["spacing_mm_xyz"][::-1], float)
    half = np.ceil(CUBE_MM / sp / 2).astype(int)
    ok = lungs_zyx > 0
    z, y, x = np.indices(lungs_zyx.shape)
    for ax, (arr, h) in enumerate(zip((z, y, x), half)):
        ok &= (arr >= h) & (arr < lungs_zyx.shape[ax] - h)
    d = np.sqrt((((np.stack([z, y, x]) - np.array(away_from_zyx).reshape(3, 1, 1, 1)) * sp.reshape(3, 1, 1, 1)) ** 2).sum(0))
    ok &= d >= min_mm
    cand = np.argwhere(ok)
    if not len(cand):
        raise ValueError("no lung voxel satisfies the distance / border constraints")
    return tuple(int(v) for v in cand[rng.integers(len(cand))])
