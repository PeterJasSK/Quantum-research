"""Section A: placement. One 3-D site per tumour inside the host's lung, respecting its lobe -> sites.json.

Threshold masks give no lobes, so the lobe is a proxy:
    side   = left / right lung component (RUL, RML, RLL -> patient right; LUL, LLL -> patient left)
    height = z band of that lung's extent (upper lobes top half, lower lobes bottom half, RML the middle third)
Candidates are aerated parenchyma (smoothed HU in [-950, -700], so a seed never starts inside a vessel), at least
1.5 mm inside the lung. Every site prefers >= 2 r separation from every placed site. A sibling daughter stays in
its own rolled lobe and takes the clear candidate nearest to a point 1.5 (r_parent + r) from its parent (so in
another lobe it is that lobe's nearest clear site). Placement is classical and seeded (SEED).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from common import HOST, runio
from common.runio import Ctx

SEED = 0                      # placement RNG seed

_SIDE = {"RUL": 1, "RML": 1, "RLL": 1, "LUL": 2, "LLL": 2}
_BAND = {"RUL": (0.5, 1.0), "LUL": (0.5, 1.0), "RLL": (0.0, 0.5), "LLL": (0.0, 0.5), "RML": (1 / 3, 2 / 3)}


class Placer:
    def __init__(self, host, rng: np.random.Generator):
        self.host, self.rng = host, rng
        sp = np.asarray(host.spacing_zyx, float)
        self.sp = sp
        inside = ndi.distance_transform_edt(host.lungs > 0, sampling=sp) >= 1.5
        sm = ndi.gaussian_filter(host.hu.astype(np.float32), (0.5, 1, 1))
        self.cand = inside & (sm >= -950) & (sm <= -700)
        self.placed: list[tuple[np.ndarray, float]] = []   # (zyx, radius_mm)
        self._by_lobe: dict[str, np.ndarray] = {}

    def _lobe_points(self, lobe: str) -> np.ndarray:
        if lobe not in self._by_lobe:
            side = self.host.left_right == _SIDE[lobe]
            zs = np.flatnonzero(side.any((1, 2)))
            lo, hi = _BAND[lobe]
            z0 = zs.min() + int(lo * (zs.max() - zs.min()))
            z1 = zs.min() + int(hi * (zs.max() - zs.min()))
            m = self.cand & side
            m[:z0] = False
            m[z1 + 1:] = False
            # keep clear of the volume's top/bottom slices (the growth ROI needs room)
            m[:8] = False
            m[-8:] = False
            self._by_lobe[lobe] = np.argwhere(m)
        pts = self._by_lobe[lobe]
        if len(pts) == 0:
            raise ValueError(f"no aerated lung candidates for lobe {lobe}")
        return pts

    def _clear(self, pts: np.ndarray, radius_mm: float) -> np.ndarray:
        ok = np.ones(len(pts), bool)
        for c, r in self.placed:
            ok &= np.linalg.norm((pts - c) * self.sp, axis=1) >= 2 * max(r, radius_mm)
        return ok

    def place(self, lobe: str, radius_mm: float, parent=None) -> tuple[int, int, int]:
        """parent = (zyx, radius_mm) of the sibling's parent, or None."""
        pts = self._lobe_points(lobe)
        ok = self._clear(pts, radius_mm)
        pool = pts[ok] if ok.any() else pts
        if parent is not None:                             # the clear site of its own lobe nearest to the parent
            p_zyx, p_r = parent
            ang = self.rng.uniform(0, 2 * np.pi)
            target = np.asarray(p_zyx, float) + np.array([0.0, np.sin(ang), np.cos(ang)]) \
                * (1.5 * (p_r + radius_mm)) / self.sp
            site = pool[int(np.argmin(np.linalg.norm((pool - target) * self.sp, axis=1)))]
        else:
            site = pool[int(self.rng.integers(len(pool)))]
        self.placed.append((site, radius_mm))
        return tuple(int(v) for v in site)


def run(ctx: Ctx) -> None:
    from common.host import load_host

    params, _ = runio.load_cohort(ctx.run_dir)
    placer = Placer(load_host(HOST), np.random.default_rng(SEED))
    sites = {}
    for group in runio.group_by_lineage(params):
        parent = None
        for p in group:
            site = placer.place(p.lobe, p.size_mm / 2, parent)
            parent = parent or (site, p.size_mm / 2)
            sites[runio.tile_id(p)] = [int(v) for v in site]
            print(f"  {runio.tile_id(p):10s} {p.lobe}  r {p.size_mm / 2:4.1f} mm -> zyx {site}")
    runio.save_json(ctx.path("sites.json"), {"host": HOST, "placement_seed": SEED, "sites_zyx": sites})
