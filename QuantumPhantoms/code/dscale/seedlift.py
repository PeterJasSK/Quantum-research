"""D-SCALE seed lift: one QCA Z-snapshot -> a 3-D seed shape (uint8 occupancy, 0.5 mm voxels) for F5's grower.

Frozen copy of RE D `src/seed_shape.py` (`to_voxel_units`, `lift`) and `src/heavyhex.py` (`patch`, `_describe`,
`layout`, `principal_axis`) @ 2609cbe, generalised to any planar coupling graph (see dscale/PORTED.md):
  * the heavy-hex two-cell / hexagon patch takes the coupling graph as an argument (RE: FakeMarrakesh only);
  * `square_patch` + `square_coords` give the same patch dict on Nighthawk's 12 x 10 grid (q = 10 r + c);
  * `patch_dict` wraps any allocated region with a layout (square grid, heavy-hex cells, or Kamada-Kawai).

Original lift (RE plan Q2): solid of revolution of the active node set about the patch's principal axis through the
centre node. Each active node at (axial z, radial |r|) in patch units becomes a torus tube of radius `TUBE` patch
steps; one patch step = one voxel (0.5 mm = params_lung.json lattice_mm). Then binary closing by one voxel and the
connected component containing the centre.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
from scipy import ndimage as ndi

PITCH_MM = 0.5
TUBE = 1.2          # tube radius around each active node, in patch steps (voxels)


# ---------------------------------------------------------------------------------------------- heavyhex.py
def patch(g: nx.Graph, kind: str = "full") -> dict:
    """kind='full': two adjacent 12-cycles of the heavy-hex lattice (union = 21 nodes), lowest ids first.
    kind='hexagon': the first of those two cells alone (12 nodes)."""
    if kind == "hexagon":
        full = patch(g, "full")
        cell = sorted(full["cells"][0])
        h = full["graph"].subgraph(cell).copy()
        d = _describe(h, cell, cell)
        d["shared"] = []
        d["coords"] = {n: full["coords"][n] for n in cell}
        d["kind"] = "hexagon"
        return d
    cycles = sorted((sorted(c) for c in nx.minimum_cycle_basis(g)))
    for i, a in enumerate(cycles):
        for b in cycles[i + 1:]:
            if len(set(a) & set(b)) >= 2:
                nodes = sorted(set(a) | set(b))
                h = g.subgraph(nodes).copy()
                if len(nodes) == 21:
                    d = _describe(h, a, b)
                    d["kind"] = "full"
                    return d
    raise RuntimeError("no two-cell patch")


def _describe(h: nx.Graph, a, b) -> dict:
    colour = nx.bipartite.color(h)
    A = sorted(n for n, c in colour.items() if c == 0)
    B = sorted(n for n, c in colour.items() if c == 1)
    shared = sorted(set(a) & set(b))
    ecc = nx.eccentricity(h)
    centre = min(h.nodes, key=lambda n: (ecc[n], n))
    return {"graph": h, "nodes": sorted(h.nodes), "A": A, "B": B, "centre": centre, "cells": [a, b],
            "shared": shared, "coords": layout(h, a, b)}


def layout(h: nx.Graph, a, b) -> dict[int, tuple[float, float]]:
    """Planar coords: place each 12-cycle as a regular dodecagon, second cell offset across the shared path."""
    pos: dict[int, tuple[float, float]] = {}
    sh = [n for n in a if n in b]

    def ring(cycle_nodes, centre_xy):
        order = nx.cycle_basis(h.subgraph(cycle_nodes))[0]
        k = len(order)
        for i, n in enumerate(order):
            ang = 2 * np.pi * i / k
            pos.setdefault(n, (centre_xy[0] + np.cos(ang), centre_xy[1] + np.sin(ang)))
        return order

    ring(a, (0.0, 0.0))
    if len(sh) >= 2:
        sx = np.mean([pos[n][0] for n in sh]); sy = np.mean([pos[n][1] for n in sh])
        c2 = (2 * sx, 2 * sy)
    else:
        c2 = (2.0, 0.0)
    order_b = nx.cycle_basis(h.subgraph(b))[0]
    rest = [n for n in order_b if n not in pos]
    k = len(order_b)
    for n in rest:
        i = order_b.index(n)
        ang = 2 * np.pi * i / k
        pos[n] = (c2[0] + np.cos(ang), c2[1] + np.sin(ang))
    return pos


def principal_axis(coords: dict[int, tuple[float, float]], centre: int, nodes) -> np.ndarray:
    p = np.array([coords[n] for n in nodes]) - np.array(coords[centre])
    w, v = np.linalg.eigh(p.T @ p)
    ax = v[:, np.argmax(w)]
    return ax / np.linalg.norm(ax)


# ---------------------------------------------------------------------------------------------- generalisation
def square_coords(nodes, ncol: int = 10) -> dict[int, tuple[float, float]]:
    return {n: (float(n % ncol), float(-(n // ncol))) for n in nodes}


def square_patch(g: nx.Graph, rows: int, cols: int, ncol: int = 10, nrow: int = 12) -> dict:
    """rows x cols rectangle at the grid centre (falls back to the next shift if a qubit is missing)."""
    r0, c0 = (nrow - rows) // 2, (ncol - cols) // 2
    for dr in range(0, nrow - rows + 1):
        for dc in range(0, ncol - cols + 1):
            rr, cc = (r0 + dr) % (nrow - rows + 1), (c0 + dc) % (ncol - cols + 1)
            nodes = [ncol * (rr + i) + (cc + j) for i in range(rows) for j in range(cols)]
            if all(n in g for n in nodes):
                h = g.subgraph(nodes).copy()
                if nx.is_connected(h):
                    return patch_dict(h, square_coords(nodes, ncol), kind=f"square{rows}x{cols}")
    raise RuntimeError("no square patch")


def patch_dict(h: nx.Graph, coords: dict | None = None, kind: str = "region") -> dict:
    """Patch dict (graph, nodes, A, B, centre, coords, kind) for any connected bipartite region."""
    if coords is None:
        coords = {n: tuple(map(float, xy)) for n, xy in nx.kamada_kawai_layout(h).items()}
    colour = nx.bipartite.color(h)
    ecc = nx.eccentricity(h)
    centre = min(h.nodes, key=lambda n: (ecc[n], n))
    return {"graph": h, "nodes": sorted(h.nodes), "A": sorted(n for n, c in colour.items() if c == 0),
            "B": sorted(n for n, c in colour.items() if c == 1), "centre": centre, "coords": coords, "kind": kind,
            "cells": [], "shared": []}


def seed_patch(target_name: str, g: nx.Graph, mode: str) -> dict:
    """AC-10 seed regions: 21-site two-hexagon patch (ideal) / 12-site hexagon (noisy) on heavy-hex; the same sizes
    on the square lattice as 3 x 7 / 3 x 4 rectangles."""
    noisy = mode != "ideal"
    if target_name == "nighthawk":
        return square_patch(g, 3, 4 if noisy else 7)
    return patch(g, "hexagon" if noisy else "full")


# ---------------------------------------------------------------------------------------------- seed_shape.py
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
        axis = principal_axis({n: tuple(rel[n]) for n in active} | {centre: (0.0, 0.0)}, centre, active)
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
