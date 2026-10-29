"""Variable-density point lattice of [E02] §2 + its Delaunay neighbour graph.

Mean site spacing grows with radius as z(r) = k · r^(2/3) / 6 mm (eq. 2; k = 1 is the literal law), so the
target number density is ρ(r) = 1 / z(r)^3 and dN/dr = 4π r² ρ(r) = 864π / k³ per mm: candidate radii are
therefore uniform in [0, R]. Sites are placed by random sequential addition (RSA): a candidate is kept only if
no kept site lies closer than 0.9·z(r). Candidates are processed in radial shells (inner first, random order
inside a shell), so each shell only has to be checked against the kept sites of the shells just below it.

`spacing_scale` k exists because the literal law gives ~9·10^4 sites out to 50 mm while [E02] reports
1.5·10^6 sites; k ≈ 0.4 reproduces the reported site count. Both are run and reported by kt_table2.

Neighbours = Delaunay edges (scipy / Qhull), returned as CSR (indptr, indices). Cached by parameters.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import Delaunay, cKDTree

from shared.volumes import load_npz, save_npz

CACHE = Path(__file__).resolve().parent.parent / "runs" / "_cache"
R_FLOOR_MM = 0.01   # z(0) = 0: floor the radius used in the spacing law
EXCLUSION = 0.9


def spacing_mm(r_mm: np.ndarray, k: float = 1.0) -> np.ndarray:
    return k * np.maximum(r_mm, R_FLOOR_MM) ** (2.0 / 3.0) / 6.0


def _rsa(radius_mm: float, k: float, rng: np.random.Generator, oversample: float, batch: int) -> np.ndarray:
    n_cand = int(oversample * 864 * np.pi * radius_mm / k ** 3)
    r = np.sort(radius_mm * rng.random(n_cand))
    kept: list[np.ndarray] = []
    kept_r: list[np.ndarray] = []
    for s in range(0, n_cand, batch):
        rb = rng.permutation(r[s:s + batch])
        v = rng.normal(size=(rb.size, 3))
        c = v / np.linalg.norm(v, axis=1, keepdims=True) * rb[:, None]
        ex = EXCLUSION * spacing_mm(rb, k)
        ok = np.ones(rb.size, bool)
        # against kept sites of the shells below (any site closer than ex.max() has r ≥ rb.min() − ex.max())
        lo = rb.min() - ex.max()
        near = [p[pr >= lo] for p, pr in zip(kept[-50:], kept_r[-50:])]
        near = np.vstack(near) if near else np.zeros((0, 3))
        if len(near):
            d, _ = cKDTree(near).query(c, k=1)
            ok &= d >= ex
        # within the shell: of each conflicting pair the later candidate is dropped
        pairs = cKDTree(c).query_pairs(float(ex.max()), output_type="ndarray")
        if len(pairs):
            d = np.linalg.norm(c[pairs[:, 0]] - c[pairs[:, 1]], axis=1)
            bad = pairs[d < np.maximum(ex[pairs[:, 0]], ex[pairs[:, 1]])]
            ok[bad.max(axis=1)] = False
        kept.append(c[ok])
        kept_r.append(rb[ok])
    return np.vstack(kept)


def build(radius_mm: float = 50.0, spacing_scale: float = 1.0, seed: int = 0, oversample: float = 6.0,
          batch: int = 50000) -> dict:
    """Return {points, indptr, indices, weight}; cached under E_classical_growth/runs/_cache/."""
    key = hashlib.sha256(json.dumps([radius_mm, spacing_scale, seed, oversample, batch, EXCLUSION,
                                     R_FLOOR_MM]).encode()).hexdigest()[:16]
    f = CACHE / f"kt_lattice_{key}.npz"
    if f.exists():
        return load_npz(f)
    rng = np.random.Generator(np.random.PCG64(seed))
    pts = _rsa(radius_mm, spacing_scale, rng, oversample, batch)
    indptr, indices = Delaunay(pts).vertex_neighbor_vertices
    r = np.linalg.norm(pts, axis=1)
    out = {"points": pts, "indptr": indptr.astype(np.int64), "indices": indices.astype(np.int64),
           "weight": spacing_mm(r, spacing_scale) ** 3}
    save_npz(f, **out)
    return out
