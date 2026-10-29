"""Kansal–Torquato 2000 [E02] cellular automaton, rebuilt from the paper (§3, Table 1, eqs. 3–6).

Four cell types: 0 healthy (inert, treated as empty), 1 proliferative, 2 non-proliferative (G0 / dormant),
3 necrotic (inert). One time step = one day. Per step:
    Rt  = mean radial position of the tumor edge cells            (eq. 3)
    dn  = a · Rt^(2/3)   dormant cells deeper than dn below the tumor edge turn necrotic   (eq. 4)
    pd  = p0 · (1 − r / Rmax)   probability that a proliferative cell attempts to divide   (eq. 5)
    dp  = b · Rt^(2/3)   a dividing cell searches for free space within dp, nearest first  (eq. 6)
    no free space found  →  the cell becomes non-proliferative.

The layer functions (`necrotic_thickness`, `prolif_thickness`, `division_probability`) are reused by the lung
engine (`engine.py`); `KTGraph` runs the original algorithm on an arbitrary neighbour graph (the paper's
Delaunay lattice, built in `repro/kt_lattice.py`).
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

HEALTHY, PROLIF, DORMANT, NECROTIC = 0, 1, 2, 3

# [E02] §4 "the following parameter set was used" (GBM test case)
P0 = 0.192          # base probability of division (per day)
A_MM13 = 0.42       # base necrotic thickness, mm^(1/3)
B_MM13 = 0.11       # base proliferative thickness, mm^(1/3)
RMAX_MM = 37.5      # maximum tumor extent, mm
R_INIT_MM = 0.1     # initial proliferative radius, mm ([E02] Table 2 footnote)

# [E02] Table 2: literature data and the paper's own simulation, at the four clinical stages
TABLE2 = {
    "stage": ["spheroid", "detectable lesion", "diagnosis", "death"],
    "radius_mm": [0.5, 5.0, 18.5, 25.0],
    "day": {"sim": [87, 198, 405, 492]},
    "cell_number": {"data": [1e6, 1e9, 5e10, 1e11], "sim": [7e5, 6e8, 4e10, 9e10]},
    "growth_fraction": {"data": [0.36, 0.30, 0.20, 0.09], "sim": [0.40, 0.30, 0.19, 0.13]},
    "necrotic_fraction": {"data": [0.46, 0.49, 0.55, 0.60], "sim": [0.38, 0.45, 0.57, 0.60]},
    "doubling_time_days": {"data": [6, 45, 70, 105], "sim": [5, 38, 72, 112]},
}


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


class KTGraph:
    """The [E02] algorithm on a point lattice with a CSR neighbour graph.

    points  (n, 3) mm, tumor grown from the origin;  weight (n,) cell-volume proxy used for the fractions.
    """

    def __init__(self, points: np.ndarray, indptr: np.ndarray, indices: np.ndarray, weight: np.ndarray,
                 rng: np.random.Generator, p0: float = P0, a: float = A_MM13, b: float = B_MM13,
                 rmax_mm: float = RMAX_MM, r_init_mm: float = R_INIT_MM):
        self.points, self.indptr, self.indices, self.weight = points, indptr, indices, weight
        self.r = np.linalg.norm(points, axis=1)
        self.rng = rng
        self.p0, self.a, self.b, self.rmax = p0, a, b, rmax_mm
        n = len(points)
        self.adj = sp.csr_matrix((np.ones(len(indices), np.float32), indices, indptr), shape=(n, n))
        self.state = np.zeros(n, np.int8)
        self.state[self.r <= r_init_mm] = PROLIF
        self.day = 0

    # ------------------------------------------------------------------ measurements
    def edge(self) -> np.ndarray:
        tumor = self.state > 0
        open_nbrs = self.adj @ (~tumor).astype(np.float32)
        return tumor & (open_nbrs > 0)

    def radius(self) -> float:
        e = self.edge()
        return float(self.r[e].mean()) if e.any() else 0.0

    def fractions(self) -> tuple[float, float]:
        w = self.weight
        tumor = w[self.state > 0].sum()
        return (float(w[self.state == PROLIF].sum() / tumor), float(w[self.state == NECROTIC].sum() / tumor))

    # ------------------------------------------------------------------ dynamics
    def _free_within(self, i: int, dp: float) -> int:
        """Nearest free (healthy) site reachable from i within distance dp; direct neighbours always searched."""
        p = self.points[i]
        nb = self.indices[self.indptr[i]:self.indptr[i + 1]]
        seen = {i}
        frontier = list(nb)
        first = True
        while frontier:
            fr = np.array(sorted(set(frontier) - seen), dtype=np.int64)
            if fr.size == 0:
                return -1
            seen.update(fr.tolist())
            d = np.linalg.norm(self.points[fr] - p, axis=1)
            ok = (self.state[fr] == HEALTHY) & (first | (d <= dp))
            if ok.any():
                return int(fr[ok][np.argmin(d[ok])])
            first = False
            inside = fr[d <= dp]
            frontier = [j for k in inside for j in self.indices[self.indptr[k]:self.indptr[k + 1]]]
        return -1

    def step(self) -> None:
        rt = self.radius()
        dn = necrotic_thickness(self.a, rt)
        dp = prolif_thickness(self.b, rt)
        dorm = self.state == DORMANT
        self.state[dorm & (rt - self.r > dn)] = NECROTIC
        prolif = np.flatnonzero(self.state == PROLIF)
        attempt = prolif[self.rng.random(prolif.size) < division_probability(self.p0, self.r[prolif], self.rmax)]
        for i in self.rng.permutation(attempt):
            j = self._free_within(int(i), dp)
            if j < 0:
                self.state[i] = DORMANT
            else:
                self.state[j] = PROLIF
        self.day += 1
