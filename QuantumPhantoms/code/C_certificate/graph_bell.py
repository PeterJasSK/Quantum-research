"""GRAPH-BELL: one Bell inequality over the graph state of the chip region (plans/feature-QCAND-*.md).

After Baccari et al. (scalable Bell inequalities for graph states) and its test on IBM devices (2101.10307). The
form below is an own derivation with several special qubits, NOT a transcription of 2101.10307 Eq. 3 [verify].

Graph state on a bipartite region (sublattices P and Q). G_i = X_i prod_{j in N(i)} Z_j are its stabilizers.
Special qubits S: all in P, pairwise more than 2 couplers apart. A special qubit v is never read in X or Z but in
A0 = (X + Z) / sqrt 2 and A1 = (X - Z) / sqrt 2. With d_v = |N(v)|:

    I =  sum_{v in S} [ d_v <(A0 + A1)_v prod_{N(v)} Z>  +  sum_{u in N(v)} <(A0 - A1)_v X_u prod_{N(u) \\ v} Z> ]
       + sum_{every other qubit i} <G_i>

    local models   I <= sum_v 2 d_v + (n - |S| - sum_v d_v)        (d_v CHSH expressions per special qubit, each <= 2;
                                                                     every other term <= 1)
    graph state    I  = sum_v 2 sqrt 2 d_v + (n - |S| - sum_v d_v)

4 circuits: (P in X, Q in Z) and (Q in X, P in Z), each with the special qubits in A0 and in A1. The qubits sit on
one chip and the settings are fixed per circuit: a violation is job-level, locality assumed (same chip).
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

from common import qhard as QH, quantum as Q
from common.runio import Ctx

ANGLES = (math.pi / 4, 3 * math.pi / 4)        # A0, A1: the readout axis at this angle from Z in the X-Z plane


def plan(nodes: list[int], edges: list[tuple[int, int]]) -> dict:
    """Sublattices, special qubits and the terms: [{layer 0 | 1 (the sublattice read in X), sites, coeff (A0, A1)}]."""
    g = nx.Graph(edges)
    g.add_nodes_from(nodes)
    if not nx.is_bipartite(g):
        raise QH.NoLayout("the region is not bipartite: no two-layer readout of its stabilizers")
    side = nx.bipartite.color(g)
    best = None
    for p in (0, 1):
        special: list[int] = []
        for v in sorted((q for q in nodes if side[q] == p), key=lambda q: (-g.degree(q), q)):
            near = nx.single_source_shortest_path_length(g, v, cutoff=2)
            if g.degree(v) and not any(s in near for s in special):
                special.append(v)
        gain = sum(g.degree(v) for v in special)
        if best is None or gain > best[0]:
            best = (gain, p, special)
    gain, p, special = best
    owner = {u: v for v in special for u in g[v]}
    terms = []
    for i in nodes:
        sites = [i] + sorted(g[i])
        if i in special:
            terms.append({"layer": side[i], "sites": sites, "coeff": (float(g.degree(i)),) * 2})
        elif i in owner:
            terms.append({"layer": side[i], "sites": sites, "coeff": (1.0, -1.0)})
        else:
            terms.append({"layer": side[i], "sites": sites, "coeff": (0.5, 0.5)})
    rest = len(nodes) - len(special) - gain
    return {"side": side, "special": special, "terms": terms, "classical_bound": 2.0 * gain + rest,
            "quantum_bound": 2.0 * math.sqrt(2.0) * gain + rest}


def circuits(nodes: list[int], edges: list[tuple[int, int]], pl: dict, entangle: bool = True) -> list:
    """Circuit 2 * layer + setting. entangle = False: the product state |+>^n (manual verification)."""
    out = []
    for layer in (0, 1):
        for k, angle in enumerate(ANGLES):
            basis = {q: "X" for q in nodes if pl["side"][q] == layer} | {v: angle for v in pl["special"]}
            out.append(QH.graph_circuit(nodes, edges if entangle else [], basis, f"graph_bell_{'PQ'[layer]}{k}"))
    return out


def value(bits: list[np.ndarray], nodes: list[int], pl: dict) -> tuple[float, float]:
    """bits: the 4 circuits' outcomes -> (I, sigma). Terms of one circuit share its shots: the variance is taken on
    the per-shot sum."""
    col = {q: k for k, q in enumerate(nodes)}
    total, var = 0.0, 0.0
    for layer in (0, 1):
        for k in (0, 1):
            bt = bits[2 * layer + k]
            v = np.zeros(len(bt))
            for t in pl["terms"]:
                if t["layer"] == layer:
                    v += t["coeff"][k] * (1.0 - 2.0 * (bt[:, [col[q] for q in t["sites"]]].sum(1) & 1))
            total += float(v.mean())
            var += float(v.var() / len(v))
    return total, math.sqrt(max(var, 1e-18))


def build(ctx: Ctx, cfg: dict) -> dict:
    reg = QH.region(Q.session(ctx).target, cfg["n"])
    reg["plan"] = plan(reg["nodes"], reg["edges"])
    reg["circuits"] = circuits(reg["nodes"], reg["edges"], reg["plan"])
    return reg


def measure(ctx: Ctx, built: dict, shots: int) -> dict:
    """The GRAPH-BELL job -> the certificate's graph_bell entry."""
    pl = built["plan"]
    bits, info = Q.execute(ctx, "graph_bell", built["circuits"], shots)
    val, sigma = value(bits, built["nodes"], pl)
    return {"value": val, "classical_bound": pl["classical_bound"], "quantum_bound": pl["quantum_bound"], "sigma": sigma,
            "passed": bool(val - 3.0 * sigma > pl["classical_bound"]), "n": len(built["nodes"]), "qubits": built["nodes"],
            "special": pl["special"], "circuits": len(built["circuits"]), "job_id": info["job_id"], "label": info["label"],
            "rigour": "sum of CHSH-type bounds, own derivation after Baccari et al.; not transcribed from 2101.10307 "
                      "Eq. 3 [verify]; locality assumed (same chip)"}
