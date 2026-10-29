"""FakeMarrakesh heavy-hex geometry for D: coupling graph, a connected path (D-2), the 21-qubit two-hexagon
patch (D-3), its bipartition, planar layout and centre node. Deterministic: lowest node ids win."""
from __future__ import annotations

from functools import lru_cache

import networkx as nx
import numpy as np

from shared.simbackend import fake_backend


def coupling_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_edges_from(tuple(sorted(e)) for e in fake_backend().coupling_map.get_edges())
    return g


def path(n: int = 6) -> list[int]:
    """Lowest-id simple path of n physical qubits (degree ≤ 2 interior nodes preferred by DFS order)."""
    g = coupling_graph()

    def dfs(p):
        if len(p) == n:
            return p
        for v in sorted(g[p[-1]]):
            if v not in p:
                r = dfs(p + [v])
                if r:
                    return r
        return None

    for s in sorted(g):
        r = dfs([s])
        if r:
            return r
    raise RuntimeError("no path")


@lru_cache(maxsize=2)
def patch(kind: str = "full") -> dict:
    """kind='full': two adjacent 12-cycles of the heavy-hex lattice (union = 21 nodes), lowest ids first.
    kind='hexagon': the first of those two cells alone (12 nodes), used where the noisy 21-qubit run is infeasible."""
    if kind == "hexagon":
        full = patch("full")
        cell = sorted(full["cells"][0])
        h = full["graph"].subgraph(cell).copy()
        d = _describe(h, cell, cell)
        d["shared"] = []
        d["coords"] = {n: full["coords"][n] for n in cell}
        d["kind"] = "hexagon"
        return d
    g = coupling_graph()
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
    # centre = node with minimal eccentricity (ties: lowest id)
    ecc = nx.eccentricity(h)
    centre = min(h.nodes, key=lambda n: (ecc[n], n))
    return {"graph": h, "nodes": sorted(h.nodes), "A": A, "B": B, "centre": centre, "cells": [a, b],
            "shared": shared, "coords": layout(h, a, b)}


def layout(h: nx.Graph, a, b) -> dict[int, tuple[float, float]]:
    """Planar coords: place each 12-cycle as a regular dodecagon, second cell offset across the shared path."""
    pos: dict[int, tuple[float, float]] = {}
    sh = [n for n in a if n in b]

    def ring(cycle_nodes, centre_xy, start_nodes=None):
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
    # orient ring b so shared nodes coincide with those placed from ring a: assign by angle around c2
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
