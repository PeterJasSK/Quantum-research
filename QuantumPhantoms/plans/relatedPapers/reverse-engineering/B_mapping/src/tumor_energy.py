"""Tumor-in-anatomy Ising energy on a 2x2x2 voxel patch: s_i = +1 tumor, -1 no tumor."""
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from shared import RE_ROOT
from shared.volumes import read_volume

# Every coefficient is a named parameter and is recorded in the run.
PARAMS = {
    "J_compact": 0.5,          # nearest-neighbour compactness (J > 0 favours aligned spins)
    "h_vessel": 1.0,           # vessel proximity attracts (h > 0)
    "h_pleura": 1.0,           # pleura proximity repels (h < 0)
    "length_mm": 5.0,          # decay length of both proximity terms
    "h_size": 0.5,             # size term: bigger drawn tumor -> bias toward tumor
    "size_ref_mm": 10.0,
    "patch": [2, 2, 2],
}


def build(sites_path: Path, site_id: str, size_mm: float, params: dict = PARAMS, patch=(2, 2, 2)):
    """Returns (J, h, info) for prod(patch) spins (z, y, x). Patch step (mm) = size_mm / 2."""
    sites_doc = json.loads(Path(sites_path).read_text())
    site = {s["site_id"]: s for s in sites_doc["sites"]}[site_id]
    am_path = (Path(sites_path).parent / sites_doc["anatomy_masks_ref"]["path"]).resolve()
    am = json.loads(am_path.read_text())
    vessels, meta = read_volume(am_path.parent / am["files"]["vessels"]["path"])
    lungs, _ = read_volume(am_path.parent / am["files"]["lungs"]["path"])
    sp_zyx = np.array(meta["spacing_mm_xyz"])[::-1]
    d_vessel = distance_transform_edt(vessels == 0, sampling=sp_zyx)
    d_pleura = distance_transform_edt(lungs > 0, sampling=sp_zyx)       # distance to lung boundary
    step = size_mm / 2
    centre = np.array(site["center_vox_zyx"], float)
    cells = list(itertools.product(*[range(k) for k in patch]))             # (z,y,x) offsets
    n = len(cells)
    h = np.zeros(n)
    for i, c in enumerate(cells):
        off_mm = (np.array(c) - (np.array(patch) - 1) / 2) * step
        v = np.clip(np.round(centre + off_mm / sp_zyx).astype(int), 0, np.array(d_vessel.shape) - 1)
        dv, dp = d_vessel[tuple(v)], d_pleura[tuple(v)]
        h[i] = (params["h_vessel"] * np.exp(-dv / params["length_mm"])
                - params["h_pleura"] * np.exp(-dp / params["length_mm"])
                + params["h_size"] * (size_mm - params["size_ref_mm"]) / params["size_ref_mm"])
    J = np.zeros((n, n))
    for i, a in enumerate(cells):
        for j, b in enumerate(cells):
            if sum(abs(x - y) for x, y in zip(a, b)) == 1:
                J[i, j] = params["J_compact"]
    info = {"patch": list(patch), "step_mm": step, "size_mm": size_mm, "h": h.round(4).tolist(), "centre_vox_zyx": centre.tolist(),
            "anatomy_masks": str(am_path.relative_to(RE_ROOT)) if RE_ROOT in am_path.parents else str(am_path)}
    return J, h, info
