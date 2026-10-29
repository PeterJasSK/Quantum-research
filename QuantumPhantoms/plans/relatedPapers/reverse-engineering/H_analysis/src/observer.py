"""Linear model observer: Laguerre-Gauss channelized Hotelling observer (CHO), as in VICTRE (Badano 2018, H03).

Signal-known-exactly / background-known-statistically detection. 2-D channels for the
reproductions, radially symmetric 3-D generalisation for lung ROIs (plan Q5).
"""
from __future__ import annotations

import numpy as np
from scipy.special import eval_laguerre
from scipy.stats import rankdata


def _radial_lg(r2: np.ndarray, a: float, n: int) -> np.ndarray:
    """Stack of n radial LG functions; r2 = squared radius in the same unit as a^2."""
    g = np.sqrt(2.0) / a * np.exp(-np.pi * r2 / a**2)
    out = np.stack([g * eval_laguerre(j, 2.0 * np.pi * r2 / a**2) for j in range(n)], axis=0)
    flat = out.reshape(n, -1)
    flat /= np.linalg.norm(flat, axis=1, keepdims=True)  # unit-norm channels on the sampled grid
    return out


def lg_channels_2d(size: int | tuple[int, int], a: float, n: int = 5) -> np.ndarray:
    """(n, ny, nx) channels centred on the grid; a in pixels."""
    ny, nx = (size, size) if isinstance(size, int) else size
    y, x = np.mgrid[:ny, :nx]
    r2 = (y - (ny - 1) / 2.0) ** 2 + (x - (nx - 1) / 2.0) ** 2
    return _radial_lg(r2, a, n)


def lg_channels_3d(shape_zyx: tuple[int, int, int], a_mm: float,
                   spacing_mm: tuple[float, float, float] = (1.0, 1.0, 1.0), n: int = 5) -> np.ndarray:
    """(n, nz, ny, nx) radially symmetric 3-D channels; spacing_mm in (z, y, x) order."""
    nz, ny, nx = shape_zyx
    z, y, x = np.mgrid[:nz, :ny, :nx].astype(float)
    r2 = (((z - (nz - 1) / 2.0) * spacing_mm[0]) ** 2
          + ((y - (ny - 1) / 2.0) * spacing_mm[1]) ** 2
          + ((x - (nx - 1) / 2.0) * spacing_mm[2]) ** 2)
    return _radial_lg(r2, a_mm, n)


def channel_outputs(rois: np.ndarray, channels: np.ndarray) -> np.ndarray:
    """rois (N, *shape) -> (N, n_channels)."""
    n = channels.shape[0]
    return rois.reshape(len(rois), -1) @ channels.reshape(n, -1).T


def cho_train_v(vp: np.ndarray, vn: np.ndarray, reg: float = 1e-6) -> np.ndarray:
    """Hotelling template from channel outputs (N, n_ch): w = K^-1 (mean_pos - mean_neg).

    K is the average of the class covariances, regularised K + reg*tr(K)/n*I.
    """
    k = 0.5 * (np.cov(vp, rowvar=False) + np.cov(vn, rowvar=False))
    k = np.atleast_2d(k)
    n = k.shape[0]
    k = k + reg * np.trace(k) / n * np.eye(n)
    return np.linalg.solve(k, vp.mean(0) - vn.mean(0))


def cho_train(pos: np.ndarray, neg: np.ndarray, channels: np.ndarray, reg: float = 1e-6) -> np.ndarray:
    return cho_train_v(channel_outputs(pos, channels), channel_outputs(neg, channels), reg)


def cho_score(template: np.ndarray, rois: np.ndarray, channels: np.ndarray) -> np.ndarray:
    return channel_outputs(rois, channels) @ template


def auc(scores_pos: np.ndarray, scores_neg: np.ndarray) -> float:
    """Mann-Whitney AUC (ties count 1/2)."""
    sp, sn = np.asarray(scores_pos, float).ravel(), np.asarray(scores_neg, float).ravel()
    ranks = rankdata(np.concatenate([sp, sn]))
    return float((ranks[: len(sp)].sum() - len(sp) * (len(sp) + 1) / 2.0) / (len(sp) * len(sn)))
