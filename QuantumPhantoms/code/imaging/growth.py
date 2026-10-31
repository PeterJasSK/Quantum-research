"""F5 — classical tumour growth: Kansal–Torquato layers + Pixel2Cancer lung wall on a 0.5 mm lattice.

    g = grow(host, site_zyx, tumor_type, size_mm, seed_hex)

A cubic lattice centred on the site; the host lung mask is resampled onto it (nearest) and the host HU
(linear) sets the Pixel2Cancer parenchyma levels. Outside-lung = hard wall (pleura). No soft barriers:
no vessel mask (F5 plan Q8), airways out of scope. Growth starts from a Ø 2 mm ball, runs until the
equivalent diameter reaches the rolled `size_mm` (baseline), then +90 d (follow-up). Snapshots are taken
at log-spaced diameters on the way, for the pixel-growth frames. Per-type parameters (p0 calibrated to
published volume-doubling times, marked (verify)) are copied verbatim from RE E's params_lung.json.

Engine (per day; KT [E02] + P2C [E01], RE E plan AC-10/12):
  1. Rt = mean distance of the tumour's edge voxels from the seed centroid; dn = a·Rt^(2/3), dp = b·Rt^(2/3)
  2. dormant voxels deeper than dn → necrotic
  3. Pixel2Cancer pressure on soft barriers (none here; kept for fidelity with RE E)
  4. proliferative voxels divide with pd = p0·(1 − r/Rmax) into the nearest free voxel within dp (jittered
     lattice); no space → dormant
States: 0 host, 1 proliferating, 2 dormant, 3 necrotic. Identical inputs give byte-identical states.
Host HU only describes the environment; no host voxel becomes tumour appearance.
"""
# copied from plans/relatedPapers/reverse-engineering/E_classical_growth/src/engine.py @ 2609cbe (LungParams,
# LungEngine verbatim), kt.py (necrotic_thickness, prolif_thickness, division_probability, doubling_time) and
# lattice.py (Environment, levels rule of build()). Changed: lattice built with scipy map_coordinates
# instead of SimpleITK; hard = outside the lung mask only (no lobes/fissures), soft = none; run() replaced
# by grow() with log-spaced diameter snapshots.

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import (binary_dilation, binary_erosion, distance_transform_edt, generate_binary_structure,
                           map_coordinates)

from imaging.seedhash import rng

HOST, PROLIF, DORMANT, NECROTIC = 0, 1, 2, 3
_S26 = generate_binary_structure(3, 3)
JITTER = 0.8      # sub-voxel site jitter, fraction of the lattice spacing
SEED_DIAMETER_MM = 2.0
SEED_MAX_FRAC = 0.5          # D-SCALE: a quantum seed may be at most half the rolled diameter (scaled down if larger)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ---------------------------------------------------------------- kt.py
def necrotic_thickness(a: float, rt_mm: float) -> float:
    return a * max(rt_mm, 0.0) ** (2.0 / 3.0)


def prolif_thickness(b: float, rt_mm: float) -> float:
    return b * max(rt_mm, 0.0) ** (2.0 / 3.0)


def division_probability(p0: float, r_mm: np.ndarray, rmax_mm: float) -> np.ndarray:
    return np.clip(p0 * (1.0 - np.asarray(r_mm) / rmax_mm), 0.0, 1.0)


def doubling_time(days: np.ndarray, volume: np.ndarray, window: int = 10) -> np.ndarray:
    """Volumetric doubling time ln2·Δt / ln(V(t+Δ/2)/V(t−Δ/2)) on a centred window (NaN at the ends)."""
    v = np.asarray(volume, float)
    out = np.full(v.shape, np.nan)
    h = window // 2
    for i in range(h, len(v) - h):
        lo, hi = v[i - h], v[i + h]
        if lo > 0 and hi > lo:
            out[i] = np.log(2.0) * (days[i + h] - days[i - h]) / np.log(hi / lo)
    return out


# ---------------------------------------------------------------- lattice.py
@dataclass
class Environment:
    spacing_mm: float
    origin_zyx_vox: np.ndarray          # host voxel coordinate (z, y, x) of lattice index (0, 0, 0)
    center_zyx: tuple[int, int, int]
    hard: np.ndarray                    # bool (z, y, x)
    soft: np.ndarray                    # bool
    level: np.ndarray                   # int8, 1–4 on parenchyma, 0 on barriers
    notes: list[str] = field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.hard.shape


def build_environment(host, site_zyx, half_width_mm: float, spacing_mm: float, hu_bounds) -> Environment:
    n = 2 * int(np.ceil(half_width_mm / spacing_mm)) + 1
    sp_host = np.asarray(host.spacing_zyx, float)
    step = spacing_mm / sp_host                                  # host voxels per lattice step, per axis
    origin = np.asarray(site_zyx, float) - (n - 1) / 2 * step
    idx = np.indices((n, n, n), dtype=np.float32).reshape(3, -1)
    coords = origin[:, None] + idx * step[:, None]
    lung = map_coordinates(host.lungs, coords, order=0, mode="constant", cval=0).reshape(n, n, n) > 0
    hu = map_coordinates(host.hu.astype(np.float32), coords, order=1, mode="constant",
                         cval=-1000.0).reshape(n, n, n)
    hard = ~lung
    soft = np.zeros_like(hard)
    lo, hi = hu_bounds
    st = (hi - lo) / 3.0
    level = np.ones(hard.shape, np.int8)
    level[hu >= lo + st] = 2
    level[hu >= lo + 2 * st] = 3
    level[hu > hi] = 4
    level[hard] = 0
    env = Environment(spacing_mm, origin, ((n - 1) // 2,) * 3, hard, soft, level)
    env.notes.append(f"lattice {n}³ at {spacing_mm} mm; hard (outside lung) {int(hard.sum())} vox; "
                     f"levels used {sorted(set(np.unique(level[level > 0]).tolist()))}")
    return env


def seed_ball(env: Environment, diameter_mm: float = SEED_DIAMETER_MM) -> np.ndarray:
    r = diameter_mm / 2 / env.spacing_mm
    c = np.asarray(env.center_zyx)
    d = np.sqrt(((np.indices(env.shape) - c[:, None, None, None]) ** 2).sum(0))
    seed = (d <= r) & ~env.hard & ~env.soft
    if not seed.any():
        raise ValueError("seed lands entirely outside the lung at this site")
    return seed


def seed_from_mask(env: Environment, mask: np.ndarray) -> np.ndarray:
    """D-SCALE hook: centre a quantum seed shape (uint8 occupancy at the lattice pitch, centre voxel = shape // 2) on
    the environment centre, crop it to the lattice and keep only lung voxels. May return an all-False mask."""
    m = np.asarray(mask, bool)
    seed = np.zeros(env.shape, bool)
    c = np.asarray(env.center_zyx)
    mc = np.asarray(m.shape) // 2
    lo = c - mc
    src = tuple(slice(max(0, -lo[a]), min(m.shape[a], env.shape[a] - lo[a])) for a in range(3))
    dst = tuple(slice(max(0, lo[a]), max(0, lo[a]) + (src[a].stop - src[a].start)) for a in range(3))
    seed[dst] = m[src]
    return seed & ~env.hard & ~env.soft


def fit_seed(mask: np.ndarray, size_mm: float, spacing_mm: float) -> tuple[np.ndarray, float]:
    """D-SCALE: shrink a quantum seed whose equivalent diameter exceeds SEED_MAX_FRAC x the rolled size, keeping its
    shape (linear zoom about the centre, threshold 0.5, centre component). The zoom factor is bisected so the result
    lands just under the cap (thin lifted tubes erode faster than a plain 1/d scale). Returns (mask, scale)."""
    from scipy.ndimage import label, zoom

    m = np.asarray(mask, bool)
    eqd = lambda x: (6 * x.sum() * spacing_mm ** 3 / np.pi) ** (1 / 3)
    dmax = SEED_MAX_FRAC * size_mm
    if m.sum() == 0 or eqd(m) <= dmax:
        return m, 1.0

    def shrink(f: float) -> np.ndarray:
        z = zoom(m.astype(np.float32), f, order=1) >= 0.5
        if not z.any():
            return z
        lab, _ = label(z)
        c = tuple(np.asarray(z.shape) // 2)
        keep = lab[c] if lab[c] else np.bincount(lab.ravel())[1:].argmax() + 1
        return lab == keep

    lo, hi, best = 0.0, 1.0, None
    for _ in range(14):
        f = (lo + hi) / 2
        z = shrink(f)
        if z.any() and eqd(z) <= dmax:
            lo, best = f, (z, f)
        else:
            hi = f
    if best is None:                                     # cap below one voxel: a single centre voxel
        z = np.zeros((1, 1, 1), bool)
        z[0, 0, 0] = True
        return z, 0.0
    return best[0], float(best[1])


# ---------------------------------------------------------------- engine.py
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
        self.pad = pad = max(3, int(np.ceil(prolif_thickness(params.b_mm13, params.Rmax_mm) / self.sp)) + 1)
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
        self.jitter = (g.random((self.state.size, 3)) - 0.5) * JITTER
        self._offsets: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    def grid(self) -> np.ndarray:
        return self.state.reshape(self.shape)

    def unpadded(self) -> np.ndarray:
        p = self.pad
        return self.grid()[p:-p, p:-p, p:-p].copy()

    def _shell(self, rad_vox: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        hard = self.hard.reshape(self.shape)[bb]
        return {"day": self.day, "Rt_mm": round(rt, 4), "volume_mm3": round(vol, 4),
                "eq_diameter_mm": round((6 * vol / np.pi) ** (1 / 3), 4),
                "f_prolif": round(int((g[bb] == PROLIF).sum()) / n, 4),
                "f_dormant": round(int((g[bb] == DORMANT).sum()) / n, 4),
                "f_necrotic": round(int((g[bb] == NECROTIC).sum()) / n, 4),
                "wall_contacts": int((binary_dilation(t, _S26) & hard & self.inner[bb]).sum()),
                "touches_box_edge": bool((binary_dilation(t, _S26) & ~self.inner[bb]).any())}

    def step(self, rt_mm: float) -> None:
        p, sp = self.p, self.sp
        g = self.grid()
        tum = g > 0
        bb = self._bbox(tum, 2)
        dn = necrotic_thickness(p.a_mm13, rt_mm)
        dp = max(prolif_thickness(p.b_mm13, rt_mm), sp * np.sqrt(3))
        depth = distance_transform_edt(tum[bb], sampling=sp)
        sub = g[bb]
        sub[(sub == DORMANT) & (depth > dn)] = NECROTIC
        g[bb] = sub
        st, hard, soft, lev, jit = self.state, self.hard, self.soft, self.level, self.jitter
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
        attempt = prolif[self.g.random(prolif.size) < division_probability(p.p0, r, p.Rmax_mm)]
        offs, vec, dist = self._shell(int(np.ceil(dp / sp)))
        keep = (dist <= np.sqrt(3) + 1e-9) | (dist * sp <= dp + 1e-9)
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


# ---------------------------------------------------------------- F5 driver
@dataclass
class Growth:
    env: Environment
    frames: list[tuple[int, str, float, np.ndarray]]   # (day, role, eq_diameter_mm, state) — growth…, baseline, follow-up
    summary: dict


class GrowthFailed(RuntimeError):
    pass


def load_params() -> dict:
    with open(os.path.join(DATA, "params_lung.json")) as f:
        return json.load(f)


def grow(host, site_zyx, tumor_type: str, size_mm: float, seed_hex: str, *, n_frames: int = 8,
         follow_up_days: int = 90, max_days: int = 15000, cfg: dict | None = None,
         seed_mask: np.ndarray | None = None, seed_label: str = "dscale") -> Growth:
    """seed_mask (D-SCALE): a quantum seed shape used instead of the 2 mm ball when given; it falls back to the ball
    (and says so in the summary) if it lies entirely outside the lung at this site. Without it the path is F5's."""
    cfg = cfg or load_params()
    tp = cfg["types"][tumor_type]
    params = LungParams.from_json(tp)
    sp = float(cfg["lattice_mm"])
    fu_diam = size_mm * 2 ** (follow_up_days / (3 * tp["vdt_target_days"]))
    env = build_environment(host, site_zyx, 1.3 * fu_diam / 2 + 5.0, sp, tuple(cfg["lung_hu_bounds"]))
    seed_info = None
    if seed_mask is None:
        seed = seed_ball(env)
    else:
        fitted, scale = fit_seed(seed_mask, size_mm, sp)
        seed = seed_from_mask(env, fitted)
        if seed.any():
            seed_info = {"seed_source": seed_label, "seed_cells": int(seed.sum())}
            if scale < 1:
                seed_info["seed_scaled"] = round(scale, 3)   # quantum seed shrunk to <= half the rolled size
        else:
            print(f"  [growth] D-SCALE seed mask lies outside the lung at {tuple(site_zyx)}: falling back to the ball")
            seed = seed_ball(env)
            seed_info = {"seed_source": "ball (dscale seed outside the lung)", "seed_cells": int(seed.sum())}
    eng = LungEngine(env, seed, params, rng(seed_hex, f"E/engine/{tumor_type}"))

    n_growth = max(n_frames - 2, 1)
    d0 = max(SEED_DIAMETER_MM, 1e-3)
    if seed_info is not None and seed_info["seed_source"] == seed_label:
        d0 = max(eng.measure()["eq_diameter_mm"], 1e-3)          # equivalent diameter of the quantum seed
    targets = [d0 * (size_mm / d0) ** (k / n_growth) for k in range(n_growth)] if size_mm > d0 else [d0]
    frames, per_day = [], []
    m = eng.measure()
    per_day.append(m)
    ti, baseline_day = 0, None
    while True:
        while baseline_day is None and ti < len(targets) and m["eq_diameter_mm"] >= targets[ti]:
            frames.append((eng.day, "growth", m["eq_diameter_mm"], eng.unpadded()))
            ti += 1
        if baseline_day is None and m["eq_diameter_mm"] >= size_mm:
            baseline_day = eng.day
            frames.append((eng.day, "baseline", m["eq_diameter_mm"], eng.unpadded()))
        if baseline_day is not None and eng.day == baseline_day + follow_up_days:
            frames.append((eng.day, "follow-up", m["eq_diameter_mm"], eng.unpadded()))
            break
        if eng.day >= max_days:
            why = "baseline size not reached" if baseline_day is None else "follow-up day not reached"
            raise GrowthFailed(f"{why} within max_days {max_days} (eq. diameter {m['eq_diameter_mm']} mm)")
        eng.step(m["Rt_mm"])
        m = eng.measure()
        per_day.append(m)
    vdt = doubling_time(np.array([x["day"] for x in per_day]), np.array([x["volume_mm3"] for x in per_day]))
    i_b = baseline_day
    vdt_b = next((float(v) for v in vdt[i_b::-1] if np.isfinite(v)), float("nan"))
    base, fu = per_day[i_b], per_day[-1]
    summary = {"day_baseline": baseline_day, "follow_up_days": follow_up_days,
               "diameter_baseline_mm": base["eq_diameter_mm"], "diameter_follow_up_mm": fu["eq_diameter_mm"],
               "vdt_d": round(vdt_b, 1) if np.isfinite(vdt_b) else None,
               "f_necrotic_baseline": base["f_necrotic"], "wall_contacts_baseline": base["wall_contacts"],
               "touches_box_edge": fu["touches_box_edge"], "lattice": env.notes[0],
               "seed_diameter_mm": SEED_DIAMETER_MM, "params_type": tumor_type}
    if seed_info is not None:
        summary |= seed_info | {"seed_diameter_mm": round(d0, 3)}
    return Growth(env, frames, summary)
