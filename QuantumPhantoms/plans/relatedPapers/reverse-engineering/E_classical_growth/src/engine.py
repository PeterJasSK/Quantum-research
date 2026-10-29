"""Lung growth engine: Kansal–Torquato layers + Pixel2Cancer anatomy barriers on a cubic lattice (AC-10, AC-12).

Per day:
  1. Rt = mean distance of the tumor's edge voxels from the seed centroid; dn = a·Rt^(2/3), dp = b·Rt^(2/3)
     (dp floored at the 26-neighbour distance, so the first shell is always searched, as on the KT lattice).
  2. dormant voxels deeper than dn below the tumor surface (Euclidean distance transform) → necrotic.
  3. Pixel2Cancer pressure: every dormant (crowded) cell pushes one random 26-neighbour; a soft barrier
     (vessel / airway) whose pressure reaches vessel_threshold is entered (becomes level-1 parenchyma).
  4. proliferative voxels attempt to divide with pd = p0·(1 − r/Rmax), in a seeded random order
     (Poleszczuk–Enderling active-cell list on a flattened, padded lattice). Candidates within dp, nearest
     first on a jittered lattice (isotropic, like KT's Voronoi lattice):
       tumor, hard or soft barrier → skip;  parenchyma of level L → taken with probability rates[L]
       (Pixel2Cancer tissue levels). No target → the cell becomes dormant.
States: 0 host, 1 proliferating, 2 dormant, 3 necrotic (shared/contracts/VOLUMES.md).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure

from E_classical_growth.src import kt
from E_classical_growth.src.lattice import Environment

HOST, PROLIF, DORMANT, NECROTIC = 0, 1, 2, 3
_S26 = generate_binary_structure(3, 3)
JITTER = 0.8      # sub-voxel site jitter, fraction of the lattice spacing


@dataclass
class LungParams:
    p0: float
    a_mm13: float
    b_mm13: float
    Rmax_mm: float
    vessel_threshold: int
    parenchyma_rates: list[float]       # levels 1–4

    @classmethod
    def from_json(cls, d: dict) -> "LungParams":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


class LungEngine:
    def __init__(self, env: Environment, seed: np.ndarray, params: LungParams, g: np.random.Generator):
        self.env, self.p, self.g = env, params, g
        self.sp = env.spacing_mm
        # padding (hard barrier) must cover the widest division search, dp(Rmax)
        self.pad = pad = max(3, int(np.ceil(kt.prolif_thickness(params.b_mm13, params.Rmax_mm) / self.sp)) + 1)
        self.shape = tuple(s + 2 * pad for s in env.shape)
        self.inner = np.pad(np.ones(env.shape, bool), pad)
        self.state = np.pad(seed.astype(np.uint8) * PROLIF, pad).ravel()
        self.hard = np.pad(env.hard, pad, constant_values=True).ravel()
        self.soft = np.pad(env.soft, pad).ravel()
        self.level = np.pad(env.level, pad).ravel()
        self.rates = np.concatenate([[0.0], np.asarray(params.parenchyma_rates, float)])
        self.pressure = np.zeros(self.state.size, np.int32)
        self.entered = np.zeros(self.state.size, bool)
        self.centroid = np.argwhere(seed).mean(axis=0) + pad     # padded zyx
        self.day = 0
        self.vessel_entered_day: int | None = None
        # jittered cubic lattice: every voxel's site sits at a fixed random sub-voxel position (±JITTER/2), so
        # "nearest free site" is isotropic like KT's Voronoi lattice instead of favouring face neighbours
        self.jitter = (g.random((self.state.size, 3)) - 0.5) * JITTER
        self._offsets: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    # ------------------------------------------------------------------ geometry helpers
    def grid(self) -> np.ndarray:
        return self.state.reshape(self.shape)

    def unpadded(self) -> np.ndarray:
        p = self.pad
        return self.grid()[p:-p, p:-p, p:-p].copy()

    def _shell(self, rad_vox: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(flat offsets, offset vectors zyx, nominal distance) of all voxels within max(rad_vox, √3)."""
        if rad_vox not in self._offsets:
            r = np.arange(-rad_vox, rad_vox + 1)
            dz, dy, dx = np.meshgrid(r, r, r, indexing="ij")
            vec = np.column_stack([dz.ravel(), dy.ravel(), dx.ravel()]).astype(float)
            d = np.linalg.norm(vec, axis=1)
            keep = (d > 0) & (d <= max(rad_vox, np.sqrt(3)) + 1e-9)
            flat = (vec[:, 0] * self.shape[1] + vec[:, 1]) * self.shape[2] + vec[:, 2]
            self._offsets[rad_vox] = (flat[keep].astype(np.int64), vec[keep], d[keep])
        return self._offsets[rad_vox]

    def _bbox(self, mask: np.ndarray, margin: int) -> tuple[slice, ...]:
        idx = np.argwhere(mask)
        lo = np.maximum(idx.min(axis=0) - margin, 0)
        hi = np.minimum(idx.max(axis=0) + margin + 1, self.shape)
        return tuple(slice(a, b) for a, b in zip(lo, hi))

    # ------------------------------------------------------------------ measurements
    def measure(self) -> dict:
        g = self.grid()
        tum = g > 0
        bb = self._bbox(tum, 2)
        t = tum[bb]
        edge = t & ~binary_erosion(t)
        off = np.array([s.start for s in bb])
        e = (np.argwhere(edge) + off - self.centroid) * self.sp
        rt = float(np.linalg.norm(e, axis=1).mean()) if len(e) else 0.0
        n = int(t.sum())
        vol = n * self.sp ** 3
        soft = self.soft.reshape(self.shape)[bb]
        contacts = int((binary_dilation(t, _S26) & soft).sum())
        return {"day": self.day, "Rt_mm": round(rt, 4), "volume_mm3": round(vol, 4),
                "eq_diameter_mm": round((6 * vol / np.pi) ** (1 / 3), 4),
                "f_prolif": round(int((g[bb] == PROLIF).sum()) / n, 4),
                "f_dormant": round(int((g[bb] == DORMANT).sum()) / n, 4),
                "f_necrotic": round(int((g[bb] == NECROTIC).sum()) / n, 4),
                "barrier_contacts": contacts, "barrier_entries": int(self.entered.sum()),
                "touches_box_edge": bool((binary_dilation(t, _S26) & ~self.inner[bb]).any())}

    # ------------------------------------------------------------------ dynamics
    def step(self, rt_mm: float) -> None:
        p, sp = self.p, self.sp
        g = self.grid()
        tum = g > 0
        bb = self._bbox(tum, 2)
        dn = kt.necrotic_thickness(p.a_mm13, rt_mm)
        dp = max(kt.prolif_thickness(p.b_mm13, rt_mm), sp * np.sqrt(3))
        depth = distance_transform_edt(tum[bb], sampling=sp)
        sub = g[bb]
        sub[(sub == DORMANT) & (depth > dn)] = NECROTIC
        g[bb] = sub
        st, hard, soft, lev, jit = self.state, self.hard, self.soft, self.level, self.jitter
        # Pixel2Cancer R2 pressure: every crowded (dormant) cell pushes one random kernel neighbour per day;
        # a soft barrier (vessel / airway) gives way once its pressure reaches vessel_threshold
        off26 = self._shell(1)[0]
        crowd = np.flatnonzero(st == DORMANT)
        t = crowd + off26[self.g.integers(0, off26.size, crowd.size)]
        t = t[soft[t]]
        if t.size:
            np.add.at(self.pressure, t, 1)
            t = np.unique(t)
            give = t[self.pressure[t] >= p.vessel_threshold]
            if give.size:
                soft[give] = False
                lev[give] = 1
                self.entered[give] = True
                if self.vessel_entered_day is None:
                    self.vessel_entered_day = self.day + 1
        prolif = np.flatnonzero(st == PROLIF)
        zyx = np.column_stack(np.unravel_index(prolif, self.shape))
        r = np.linalg.norm((zyx - self.centroid) * sp, axis=1)
        attempt = prolif[self.g.random(prolif.size) < kt.division_probability(p.p0, r, p.Rmax_mm)]
        offs, vec, dist = self._shell(int(np.ceil(dp / sp)))
        keep = (dist <= np.sqrt(3) + 1e-9) | (dist * sp <= dp + 1e-9)   # 26-neighbours always searched
        offs, vec = offs[keep], vec[keep]
        for i in self.g.permutation(attempt):
            placed = False
            cand = i + offs
            for t in cand[np.argsort(np.linalg.norm(vec + jit[cand] - jit[i], axis=1), kind="stable")]:
                if st[t] or hard[t] or soft[t]:
                    continue
                if self.g.random() < self.rates[lev[t]]:
                    st[t] = PROLIF
                    placed = True
                    break
            if not placed:
                st[i] = DORMANT
        self.day += 1

    def run(self, size_mm: float, follow_up_days: int, every: int, max_days: int) -> tuple[list, list, str | None]:
        """Grow until the follow-up snapshot. Returns (snapshots [(day, role, state)], per_day, failure|None)."""
        snaps, per_day = [], []
        baseline_day = None
        m = self.measure()
        per_day.append(m)
        while True:
            if baseline_day is None and m["eq_diameter_mm"] >= size_mm:
                baseline_day = self.day
                snaps.append((self.day, "baseline", self.unpadded()))
            elif baseline_day is not None and self.day == baseline_day + follow_up_days:
                snaps.append((self.day, "follow-up", self.unpadded()))
                break
            elif every and self.day % every == 0 and self.day > 0:
                snaps.append((self.day, "other", self.unpadded()))
            if self.day >= max_days:
                why = "baseline size not reached" if baseline_day is None else "follow-up day not reached"
                return snaps, per_day, f"{why} within --max-days {max_days} (eq. diameter {m['eq_diameter_mm']} mm)"
            self.step(m["Rt_mm"])
            m = self.measure()
            per_day.append(m)
        vdt = kt.doubling_time(np.array([x["day"] for x in per_day]), np.array([x["volume_mm3"] for x in per_day]))
        for x, v in zip(per_day, vdt):
            x["vdt_days"] = None if np.isnan(v) else round(float(v), 2)
        return snaps, per_day, None
