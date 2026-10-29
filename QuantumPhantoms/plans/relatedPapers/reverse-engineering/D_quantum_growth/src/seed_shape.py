"""D-3 -> E hand-off: one QCA Z-snapshot becomes a 3-D `seed_shape` (occupancy uint8 3-D, 0.5 mm voxels).

Lift (plan Q2): solid of revolution of the active node set about the patch's principal axis through the centre node.
Each active node at (axial z, radial |r|) in patch units becomes a torus tube of radius `TUBE` patch steps; one patch
step = one voxel (Q4). Then binary closing by one voxel and the connected component containing the centre."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from D_quantum_growth.src import heavyhex, io_contracts as io
from shared.volumes import save_npz

PITCH_MM = 0.5
TUBE = 1.2          # tube radius around each active node, in patch steps (voxels)


def to_voxel_units(coords: dict[int, tuple[float, float]], nodes: list[int]) -> dict[int, np.ndarray]:
    """Layout coordinates rescaled so that the median nearest-neighbour distance is one voxel."""
    pts = np.array([coords[n] for n in nodes])
    d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    nn = np.median(d.min(1))
    return {n: np.array(coords[n]) / nn for n in nodes}


def lift(patch: dict, active: list[int]) -> np.ndarray:
    nodes = patch["nodes"]
    centre = patch["centre"]
    active = sorted(set(active) | {centre})                 # force the centre node active
    xy = to_voxel_units(patch["coords"], nodes)
    c0 = xy[centre]
    rel = {n: xy[n] - c0 for n in active}
    if len(active) > 1:
        axis = heavyhex.principal_axis({n: tuple(rel[n]) for n in active} | {centre: (0.0, 0.0)}, centre, active)
    else:
        axis = np.array([1.0, 0.0])
    perp = np.array([-axis[1], axis[0]])
    zr = np.array([[rel[n] @ axis, abs(rel[n] @ perp)] for n in active])        # (axial, radial)
    R = int(np.ceil(np.abs(zr).max() + TUBE)) + 2
    g = np.arange(-R, R + 1)
    Z, Y, X = np.meshgrid(g, g, g, indexing="ij")                                # axis along x
    rho = np.sqrt(Y ** 2 + Z ** 2)
    occ = np.zeros(X.shape, bool)
    for (z, r) in zr:
        occ |= (X - z) ** 2 + (rho - r) ** 2 <= TUBE ** 2
    occ = ndi.binary_closing(occ, structure=ndi.generate_binary_structure(3, 1), iterations=1, border_value=0)
    lab, _ = ndi.label(occ)
    centre_vox = tuple([R, R, R])
    if lab[centre_vox] == 0:
        occ[centre_vox] = True
        lab, _ = ndi.label(occ)
    return (lab == lab[centre_vox]).astype(np.uint8)


def write(run_, out_dir, patch: dict, snapshot_bits: np.ndarray, lineage_file, witness_passed: bool, mode: str,
          upstream_refs: list[dict]) -> dict:
    nodes = patch["nodes"]
    active = [n for n, b in zip(nodes, snapshot_bits) if b]
    occ = lift(patch, active)
    npz = out_dir / "seed_shape.npz"
    save_npz(npz, occupancy=occ, spacing_mm_xyz=np.full(3, PITCH_MM, dtype=np.float64))
    man = out_dir / "seed_shape.json"
    lref = io.ref(lineage_file, man)
    rec = io.envelope("seed_shape", run_, mode, upstream_refs) | {
        "lineage_ref": lref, "claim_level": "L1" if witness_passed else "L0",
        "npz": io.ref(npz, man), "n_cells": int(occ.sum())}
    io.write_contract(man, rec)
    run_.add_output(man.name, "seed_shape")
    return {"occupancy": occ, "active": active, "manifest": man}
