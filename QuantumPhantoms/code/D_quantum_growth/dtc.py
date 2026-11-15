"""D-DTC: time-crystal dynamics as growth frames (plans/feature-QCAND-*.md).

Floquet cycle on a heavy-hex patch, after the 2-D time crystal of 2501.18036 [verify: the couplings and the
imperfection here are this module's choice, not transcribed]:
    three two-qubit layers (one colour class of couplers each) of the anisotropic coupling
        exp(-i (jx X X + jy Y Y + jz Z Z))                      (up to 3 CZ per coupler, so 9 CZ layers per cycle)
    then the imperfect pi pulse  RX(pi (1 - eps))  on every qubit
from a product state in Z (a random bit string from the pool-seeded generator). One circuit per cycle count.

    Delta(t)              mean over qubits of (input sign) x <Z> after t cycles: flips sign every cycle
    subharmonic contrast  mean over the circuits of (-1)^t Delta(t)
    growth frames         frame k = the Z snapshots of circuit k: per tumour one shot on its patch, lifted to a seed
                          shape; frame 0 is the seed, all frames are stored as "<tile id>/f<k>" for section E

Quantum-sourced dynamics, diagonal observable, no separation: Delta(t) and the snapshots have classical surrogates.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit

from common import qhard as QH, quantum as Q
from common.runio import Ctx
from D_quantum_growth import graph_state as GS


def dtc_circuit(nodes: list[int], layers: list, s: np.ndarray, cycles: int, cfg: dict, name: str) -> QuantumCircuit:
    pos = {q: k for k, q in enumerate(nodes)}
    n = len(nodes)
    qc = QuantumCircuit(n, n, name=name)
    for q in np.flatnonzero(s):
        qc.x(int(q))
    for _ in range(cycles):
        for layer in layers:
            for a, b in layer:
                qc.rxx(2 * cfg["jx"], pos[a], pos[b])
                qc.ryy(2 * cfg["jy"], pos[a], pos[b])
                qc.rzz(2 * cfg["jz"], pos[a], pos[b])
        qc.rx(math.pi * (1 - cfg["eps"]), range(n))
    qc.measure(range(n), range(n))
    qc.metadata = {"layout": [int(q) for q in nodes]}
    return qc


def run(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    tg = Q.session(ctx).target
    reg = QH.region(tg, cfg["n"])
    nodes, edges = reg["nodes"], reg["edges"]
    layers = QH.edge_layers(edges)
    s = Q.rng(ctx, name, "input").integers(0, 2, len(nodes)).astype(np.uint8)
    circuits = [dtc_circuit(nodes, layers, s, t, cfg, f"dtc_t{t:02d}") for t in cfg["cycles"]]
    bits, info = Q.execute(ctx, name, circuits, ctx.shots, opt=3)
    sign = 1.0 - 2.0 * s
    rows = []
    for t, bt in zip(cfg["cycles"], bits):
        v = ((1.0 - 2.0 * bt) * sign).mean(1)
        rows.append({"cycle": t, "delta": float(v.mean()), "sigma": float(max(v.std() / math.sqrt(len(v)), 1e-9))})
    contrast = float(np.mean([(-1) ** r["cycle"] * r["delta"] for r in rows]))
    sigma = float(math.sqrt(sum(r["sigma"] ** 2 for r in rows)) / len(rows))
    seed_note = GS.seed_shapes(ctx, name, nx.Graph(edges), nodes, bits, "dtc")
    Q.save(ctx, name, {"n": len(nodes), "qubits": nodes, "couplers": len(edges), "layers_per_cycle": len(layers),
                       "couplings": {k: cfg[k] for k in ("jx", "jy", "jz", "eps")}, "input": s, "info": info, "rows": rows,
                       "subharmonic_contrast": contrast, "sigma": sigma, "frames": len(rows), "seed_shapes": seed_note})
    return [Q.claim(ctx, name, cfg, contrast, sigma, True, info["label"],
                    "Delta(t): " + ", ".join(f"t = {r['cycle']}: {r['delta']:+.3f}" for r in rows)
                    + f"; {len(nodes)} qubits, {len(edges)} couplers, {len(layers)} coupling layers per cycle, up to "
                      f"{info['two_qubit_gates_max']} two-qubit gates; quantum-sourced dynamics, diagonal observable, no "
                      f"separation; couplings not transcribed from 2501.18036; {seed_note}")]
