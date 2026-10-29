"""Pixel2Cancer [E01] cellular automaton, rebuilt on the CPU from the paper (§2) and the open reference code
(MrGiovanni/Pixel2Cancer, Apache-2.0, read only: Tumor_Synthesis/utils.py, cellular/csrc/cellular.cu).

Tumor population map `pop` (int16): 0 no tumor, 1…10 population, −1 dead. Per growth step, 3×3×3 kernel:
    R1 growth    1 ≤ s < threshold      → s + 1
    R2 invasion  s ≥ threshold/2        → up to `max_try` random kernel targets, one success:
                 barrier target (level 0: vessel / outside organ) — only a crowded cell (s ≥ threshold) acts:
                     pressure ≥ pressure_threshold → barrier invaded (becomes level-1 tissue), else pressure + 1;
                 tissue target of level L accepted with probability RATES[L]; target s < threshold → target + 1.
    R3 death     after the growth loop, if steps > tumor-size steps and a fair coin: start points (+ random
                 points of full population around them) → −1, then −1 spreads into full-population (10)
                 neighbours for int(steps/7 + 1) iterations.

Differences from the reference code (documented in dossiers/11-pixel2cancer.md):
  * curand seeded with clock64() → numpy Generator from shared.seedhash.rng (deterministic, replayable);
  * the CUDA grid-stride race is replaced by a synchronous vectorized step: all tries of one round are drawn
    at once against the current map and increments are applied with np.add.at (the kernel's atomicAdd);
    population is clipped to `threshold` at the end of a step;
  * check_tissue() receives its uniform draw as `int`, so in the reference every tissue level is accepted;
    we apply the documented rates (1, 0.3, 0.1). `faithful_int_cast=True` reproduces the reference behaviour.
"""
from __future__ import annotations

import numpy as np

# reference hyper-parameters (Tumor_Synthesis/tumor_synthesis.py, utils.py)
ORGAN_HU = {"liver": (100, 160), "pancreas": (100, 160), "kidney": (140, 200)}
MAX_STEPS = {"liver": 150, "pancreas": 80, "kidney": 80}
TUMOR_SIZE_STEPS = {"liver": 50, "pancreas": 30, "kidney": 30}   # "when tumor larger than 2 cm" proxy
THRESHOLD = 10
PRESSURE_THRESHOLD = 3     # barrier value outrange … outrange+2 is pushed; > outrange+2 is invaded
MAX_TRY = 3                # grow_per_cell = 1, max_try = 3 · grow_per_cell
RATES = (0.0, 1.0, 0.3, 0.1)   # index = tissue level; level 0 = barrier


def quantify(hu: np.ndarray, organ: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """[E01] §2.2 quantified organ: 0 barrier (outside organ or HU ≥ hi, e.g. vessels), 1–3 tissue levels."""
    interval = (hi - lo) / 3.0
    lev = np.ones(hu.shape, np.int8)
    lev[hu >= lo + interval] = 2
    lev[hu >= lo + 2 * interval] = 3
    lev[(hu >= hi) | ~organ.astype(bool)] = 0
    return lev


def _offsets(shape: tuple[int, int, int]) -> np.ndarray:
    _, ny, nx = shape
    return np.array([dz * ny * nx + dy * nx + dx for dz in (-1, 0, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])


class P2C:
    """Pixel2Cancer automaton on a quantified organ `levels` (z, y, x); 1-voxel padding handles the volume edge."""

    def __init__(self, levels: np.ndarray, rng: np.random.Generator, threshold: int = THRESHOLD,
                 pressure_threshold: int = PRESSURE_THRESHOLD, max_try: int = MAX_TRY, rates=RATES,
                 faithful_int_cast: bool = False):
        self.shape = tuple(s + 2 for s in levels.shape)
        self.levels = np.pad(levels.astype(np.int8), 1).ravel()
        self.oob = np.pad(np.zeros(levels.shape, bool), 1, constant_values=True).ravel()
        self.pop = np.zeros(self.levels.size, np.int16)
        self.pressure = np.zeros(self.levels.size, np.int16)
        self.pushes_at_invasion: list[int] = []
        self.invaded = np.zeros(self.levels.size, bool)
        self.off = _offsets(self.shape)
        self.rng = rng
        self.threshold, self.pth, self.max_try = threshold, pressure_threshold, max_try
        self.rates = np.ones(4) if faithful_int_cast else np.asarray(rates, float)
        self.rates[0] = 0.0
        self.starts: list[int] = []

    # ------------------------------------------------------------------ index helpers
    def flat(self, zyx) -> int:
        z, y, x = (int(v) + 1 for v in zyx)
        return (z * self.shape[1] + y) * self.shape[2] + x

    def volume(self, a: np.ndarray) -> np.ndarray:
        return a.reshape(self.shape)[1:-1, 1:-1, 1:-1]

    def seed(self, zyx) -> None:
        i = self.flat(zyx)
        if self.levels[i] == 0:
            raise ValueError(f"start point {tuple(zyx)} lies in a barrier")
        self.pop[i] = self.threshold // 2
        self.starts.append(i)

    # ------------------------------------------------------------------ rules
    def grow_step(self) -> None:
        prev = self.pop.copy()
        thr = self.threshold
        live = (prev >= 1) & (prev < thr)
        self.pop[live] += 1                                            # R1
        todo = np.flatnonzero(prev >= thr // 2)                       # R2 spreaders
        crowded_all = prev >= thr
        for _ in range(self.max_try):
            if todo.size == 0:
                break
            t = todo + self.off[self.rng.integers(0, 27, todo.size)]
            ok = ~self.oob[t]
            barrier = ok & (self.levels[t] == 0)
            crowded = crowded_all[todo]
            # crowded cell against a barrier: invade if the pressure is high enough, else push
            inv = barrier & crowded & (self.pressure[t] >= self.pth)
            if inv.any():
                ti = np.unique(t[inv])
                new = ti[self.levels[ti] == 0]
                self.pushes_at_invasion.extend(self.pressure[new].tolist())
                self.levels[new] = 1
                self.invaded[new] = True
            push = barrier & crowded & ~inv
            np.add.at(self.pressure, t[push], 1)
            cand = ok & ~push & (self.levels[t] > 0)
            u = self.rng.random(todo.size)
            cand &= u < self.rates[self.levels[t]]
            cand &= self.pop[t] < thr
            np.add.at(self.pop, t[cand], 1)
            todo = todo[~cand]
        np.minimum(self.pop, thr, out=self.pop)

    def death(self, steps: int) -> int:
        """R3 after the growth loop. Returns the number of dead cells."""
        thr = self.threshold
        cores = np.array(self.starts, dtype=np.int64)
        self.pop[cores[self.pop[cores] == thr]] = -1
        bias = max(int(steps / 10 - 2), 1)
        for i in cores:
            n = int(self.rng.integers(5, 20))
            d = self.rng.integers(-bias, bias, size=(n, 3))
            z, y, x = np.unravel_index(i, self.shape)
            zz, yy, xx = z + d[:, 0], y + d[:, 1], x + d[:, 2]
            inside = ((zz >= 0) & (zz < self.shape[0]) & (yy >= 0) & (yy < self.shape[1])
                      & (xx >= 0) & (xx < self.shape[2]))
            t = np.ravel_multi_index((zz[inside], yy[inside], xx[inside]), self.shape)
            self.pop[t[self.pop[t] == thr]] = -1
        for _ in range(int(steps / 7 + 1)):
            todo = np.flatnonzero(self.pop == -1)
            for _ in range(self.max_try):
                if todo.size == 0:
                    break
                t = todo + self.off[self.rng.integers(0, 27, todo.size)]
                hit = ~self.oob[t] & (self.pop[t] == thr)
                self.pop[t[hit]] = -1
                todo = todo[~hit]
        return int((self.pop == -1).sum())

    def run(self, steps: int, tumor_size_steps: int) -> dict:
        contact_step = None
        for s in range(steps + 1):
            self.grow_step()
            if contact_step is None and self.touching_barrier():
                contact_step = s
        dead = 0
        died = steps > tumor_size_steps and int(self.rng.integers(0, 2)) == 0
        if died:
            dead = self.death(steps)
        return {"steps": steps, "death_rule": bool(died), "dead": dead, "contact_step": contact_step}

    def touching_barrier(self) -> bool:
        tum = np.flatnonzero(self.pop != 0)
        nb = (tum[:, None] + self.off[None, :]).ravel()
        return bool(((self.levels[nb] == 0) & ~self.oob[nb]).any())
