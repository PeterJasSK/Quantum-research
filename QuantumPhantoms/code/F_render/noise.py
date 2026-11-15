"""F5 — NPS estimation and NPS-shaped noise synthesis (Peng [F05] §2.2.1 after Divel–Pelc 2019).

CT noise is treated as in-plane correlated and independent between slices (axial NPS only).

    NPS(fx, fy) = Δx Δy / (Nx Ny) · ⟨|F(n)|²⟩                               ([F05] eq. 3)
    noise       = F⁻¹( √(NPS / ΔxΔy) · F(w) ),  w white N(0, 1)             (filtered white noise)
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/noise.py @ 2609cbe
# (detrend2, nps2d, radial, nps_from_radial, sigma_of, noise_slices); dropped: patch_noise_2d (local NPS, CR-F1).

from __future__ import annotations

import numpy as np


def detrend2(roi: np.ndarray) -> np.ndarray:
    """Subtract a 2nd-order polynomial surface (removes anatomy/cupping from single-scan ROIs)."""
    ny, nx = roi.shape
    y, x = np.mgrid[0:ny, 0:nx].astype(float)
    A = np.stack([np.ones_like(x), x, y, x * x, y * y, x * y], -1).reshape(-1, 6)
    coef, *_ = np.linalg.lstsq(A, roi.reshape(-1).astype(float), rcond=None)
    return roi - (A @ coef).reshape(ny, nx)


def nps2d(rois: list[np.ndarray], dx: float, dy: float) -> np.ndarray:
    """Ensemble-averaged 2-D NPS (HU² mm²) of already zero-mean noise ROIs, fftshifted."""
    ny, nx = rois[0].shape
    acc = np.zeros((ny, nx))
    for r in rois:
        acc += np.abs(np.fft.fft2(r)) ** 2
    return np.fft.fftshift(acc / len(rois) * dx * dy / (nx * ny))


def radial(nps: np.ndarray, dx: float, dy: float, n_bins: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Radial average of a fftshifted 2-D NPS → (freq_cyc_per_mm, values)."""
    ny, nx = nps.shape
    fy = np.fft.fftshift(np.fft.fftfreq(ny, dy))
    fx = np.fft.fftshift(np.fft.fftfreq(nx, dx))
    fr = np.hypot(*np.meshgrid(fy, fx, indexing="ij"))
    fmax = min(abs(fx).max(), abs(fy).max())
    n_bins = n_bins or nx // 2
    edges = np.linspace(0, fmax, n_bins + 1)
    idx = np.digitize(fr.ravel(), edges) - 1
    ok = (idx >= 0) & (idx < n_bins)
    s = np.bincount(idx[ok], nps.ravel()[ok], n_bins)
    c = np.bincount(idx[ok], minlength=n_bins)
    centers = 0.5 * (edges[1:] + edges[:-1])
    return centers, s / np.maximum(c, 1)


def nps_from_radial(shape_yx, dx: float, dy: float, freq, values) -> np.ndarray:
    """Rebuild an isotropic 2-D NPS (unshifted FFT layout) from a radial curve."""
    ny, nx = shape_yx
    fr = np.hypot(*np.meshgrid(np.fft.fftfreq(ny, dy), np.fft.fftfreq(nx, dx), indexing="ij"))
    return np.interp(fr, np.asarray(freq, float), np.asarray(values, float), right=0.0)


def sigma_of(freq, values) -> float:
    """σ (HU) implied by an isotropic radial NPS: σ² = ∫∫ NPS df = ∫ 2π f NPS(f) df."""
    f, v = np.asarray(freq, float), np.asarray(values, float)
    return float(np.sqrt(max(np.trapezoid(2 * np.pi * f * v, f), 0.0)))


def noise_slices(shape_zyx, dx: float, dy: float, freq, values, rng: np.random.Generator,
                 sigma: float | None = None) -> np.ndarray:
    """3-D noise, each axial slice filtered by the same isotropic NPS; optionally rescaled to σ."""
    nz, ny, nx = shape_zyx
    filt = np.sqrt(nps_from_radial((ny, nx), dx, dy, freq, values) / (dx * dy))
    w = rng.normal(0.0, 1.0, size=(nz, ny, nx))
    n = np.real(np.fft.ifft2(np.fft.fft2(w, axes=(1, 2)) * filt, axes=(1, 2)))
    if sigma is not None:
        s = n.std()
        n *= sigma / s if s > 0 else 0.0
    return n.astype(np.float32)
