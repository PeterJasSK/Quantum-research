"""D-GRAPH: the graph state of the chip region, entanglement checked coupler by coupler (plans/feature-QCAND-*.md).

    state      H on every qubit of the region, CZ on every coupler (3 layers on heavy-hex)
    batches    sets of couplers no two of which touch or are joined by a coupler, so each pair of a batch can be read
               in its own Pauli basis while every neighbour is read in Z
    tomography per pair: the 9 two-qubit Pauli bases; a neighbour that reads 1 leaves a Z on the pair's qubit, undone
               in the counts (the X / Y outcome of that qubit is flipped); linear inversion; negativity from the
               partial transpose (0.5 for the ideal pair, 0 for a separable one)
    seeds      one more circuit reads every qubit in X; its snapshots give the per-tumour seed shapes

The claim is bipartite entanglement on each measured coupler, given its neighbours' outcomes: NOT genuine
multipartite entanglement. Linear inversion is not constrained to physical states, so the negativity of a separable
pair reads slightly above 0 (sampling noise); the 3-sigma rule with Bonferroni over the couplers carries that.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from common import qhard as QH, quantum as Q, runio
from common.runio import Ctx

PAULIS = "XYZ"
BOOTSTRAP = 40                # resamples for the sigma of one coupler's negativity
SEED_NODES = 21               # qubits of one tumour's seed patch (the size of the two-hexagon patch)
_P = {"X": np.array([[0, 1], [1, 0]], complex), "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1.0 + 0j, -1.0])}


def batches(edges: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Couplers coloured so that two of one colour neither share a qubit nor are joined by a coupler; largest first."""
    adj: dict[int, set[int]] = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    c = nx.Graph()
    c.add_nodes_from(edges)
    for e in edges:
        near = set(e) | adj[e[0]] | adj[e[1]]
        c.add_edges_from((e, f) for f in edges if f > e and set(f) & near)
    col = nx.greedy_color(c, strategy="saturation_largest_first")
    out = [[e for e in edges if col[e] == k] for k in range(max(col.values()) + 1)]
    return sorted(out, key=lambda b: (-len(b), b))


def negativity(sa: np.ndarray, sb: np.ndarray) -> float:
    """sa, sb: (9, shots) outcomes +-1 of the two qubits, basis k = 3 i + j (first qubit PAULIS[i], second PAULIS[j])."""
    e2 = (sa * sb).mean(1).reshape(3, 3)
    ea, eb = sa.mean(1).reshape(3, 3).mean(1), sb.mean(1).reshape(3, 3).mean(0)
    rho = np.eye(4, dtype=complex)
    for i, p in enumerate(PAULIS):
        rho += ea[i] * np.kron(_P[p], np.eye(2)) + eb[i] * np.kron(np.eye(2), _P[p])
        for j, q in enumerate(PAULIS):
            rho += e2[i, j] * np.kron(_P[p], _P[q])
    pt = (rho / 4).reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)
    ev = np.linalg.eigvalsh(pt)
    return float(-ev[ev < 0].sum())


def pair_negativity(nine: np.ndarray, g: np.random.Generator) -> tuple[float, float]:
    """nine: (9, shots, 2) corrected bits of one pair -> (negativity, bootstrap sigma)."""
    s = 1.0 - 2.0 * nine
    val = negativity(s[:, :, 0], s[:, :, 1])
    sh = s.shape[1]
    boot = []
    for _ in range(BOOTSTRAP):
        idx = g.integers(0, sh, (9, sh))
        r = np.take_along_axis(s, idx[:, :, None], axis=1)
        boot.append(negativity(r[:, :, 0], r[:, :, 1]))
    return val, float(max(np.std(boot, ddof=1), 1e-9))


def seed_shapes(ctx: Ctx, name: str, g: nx.Graph, order: list[int], frames: list[np.ndarray], kind: str) -> str:
    """Seed shapes for section E from snapshots of a region: per tumour a patch of up to SEED_NODES qubits around a
    qubit picked by rng(tile geometry seed), one shot picked the same way, the qubits that read 1 lifted to 3-D like
    D-SCALE's snapshots. frames[k]: (shots, len(order)) bits; frame 0 is the seed (key = tile id); with more frames
    every frame k is also stored under "<tile id>/f<k>". Claim level per tile is L0."""
    from D_quantum_growth import seedlift as SL

    comp = sorted(max(nx.connected_components(g), key=len))
    col = {q: k for k, q in enumerate(order)}
    masks, tiles, patches = {}, {}, {}
    for d in runio.draws(ctx.run_dir):
        r = runio.rng(d["seed_hex"], f"{name}-snapshot")
        centre = comp[int(r.integers(len(comp)))]
        if centre not in patches:
            ball = list(nx.bfs_tree(g.subgraph(comp), centre).nodes)[:SEED_NODES]
            patches[centre] = SL.patch_dict(g.subgraph(ball).copy(), None, kind=kind)
        patch = patches[centre]
        shot = int(r.integers(min(len(f) for f in frames)))
        per = [[int(q) for q in patch["nodes"] if f[shot, col[q]]] for f in frames]
        tid = d["tile_id"]
        masks[tid] = SL.lift(patch, per[0])
        if len(frames) > 1:
            masks |= {f"{tid}/f{k}": SL.lift(patch, act) for k, act in enumerate(per)}
        tiles[tid] = {"region": kind, "sites": len(patch["nodes"]), "active": per[0], "shot": shot, "claim_level": "L0",
                      "seed_cells": int(masks[tid].sum()), "witness_passed": None, "frames": len(frames)}
    runio.save_seed_shapes(ctx, masks, tiles, name)
    return f"seed shapes for {len(tiles)} tumours from {kind} snapshots" + (f", {len(frames)} frames each" if len(frames) > 1 else "")


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    from scipy.stats import norm

    tg = Q.session(ctx).target
    reg = QH.region(tg, cfg["n"])
    nodes, edges = reg["nodes"], reg["edges"]
    col = {q: k for k, q in enumerate(nodes)}
    nb: dict[int, set[int]] = {q: set() for q in nodes}
    for a, b in edges:
        nb[a].add(b)
        nb[b].add(a)
    all_b = batches(edges)
    bs = all_b[:cfg.get("batches") or len(all_b)]
    circuits = [QH.graph_circuit(nodes, edges, {q: p for a, b in batch for q, p in ((a, pa), (b, pb))}, f"graph_b{k}_{pa}{pb}")
                for k, batch in enumerate(bs) for pa in PAULIS for pb in PAULIS]
    circuits.append(QH.graph_circuit(nodes, edges, {q: "X" for q in nodes}, "graph_snapshot_x"))
    bits, info = Q.execute(ctx, name, circuits, max(100, ctx.shots // 2))
    g = np.random.default_rng(0)                                # bootstrap of the analysis, not an input of the circuit
    rows = []
    for k, batch in enumerate(bs):
        nine = bits[9 * k:9 * k + 9]
        for a, b in batch:
            pair = np.zeros((9, len(nine[0]), 2), dtype=np.uint8)
            for j, bt in enumerate(nine):
                for side, (q, other) in enumerate(((a, b), (b, a))):
                    out = bt[:, col[q]].copy()
                    if PAULIS[(j // 3, j % 3)[side]] != "Z":            # a Z left by the neighbours flips X and Y
                        out ^= bt[:, [col[x] for x in nb[q] - {other}]].sum(1).astype(np.uint8) & 1
                    pair[j, :, side] = out
            val, sig = pair_negativity(pair, g)
            rows.append({"a": int(a), "b": int(b), "batch": k, "negativity": val, "sigma": sig})
    z_need = float(norm.isf(norm.sf(3.0) / max(len(rows), 1)))          # Bonferroni over the measured couplers
    good = nx.Graph()
    good.add_nodes_from(nodes)
    for r in rows:
        r["entangled"] = bool(r["negativity"] / r["sigma"] > z_need)
        if r["entangled"]:
            good.add_edge(r["a"], r["b"])
    largest = max(len(c) for c in nx.connected_components(good))
    frac = largest / len(nodes)
    h = nx.Graph(edges)
    seed_note = seed_shapes(ctx, name, h, nodes, [bits[-1]], "graph")
    n_ok = sum(r["entangled"] for r in rows)
    Q.save(ctx, name, {"n": len(nodes), "qubits": nodes, "couplers": len(edges), "couplers_measured": len(rows),
                       "batches": len(bs), "batches_needed": len(all_b), "whole_chip": reg["whole_chip"], "info": info,
                       "z_needed": z_need, "edges": rows, "couplers_entangled": n_ok, "connected_fraction": frac,
                       "largest_component": largest, "seed_shapes": seed_note})
    neg = [r["negativity"] for r in rows]
    return [Q.claim(ctx, name, cfg, frac, None, frac >= cfg["bound"], info["label"],
                    f"{n_ok} of {len(rows)} measured couplers entangled (negativity > 0 at z > {z_need:.2f}); "
                    f"{len(rows)} of {len(edges)} couplers of the {len(nodes)}-qubit region measured in {len(bs)} of "
                    f"{len(all_b)} batches; median negativity {np.median(neg):.3f} (ideal 0.5); largest connected set "
                    f"{largest} qubits; bipartite entanglement on every such coupler given its neighbours' outcomes, "
                    f"not genuine multipartite; linear inversion, raw counts; {seed_note}")]
