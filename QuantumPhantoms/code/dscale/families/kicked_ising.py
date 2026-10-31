"""D-SCALE family `kicked-ising` (AC-12): the Kim / Tindall anchor that calibrates the predictor and BP.

    python -m dscale.families.kicked_ising --theta 0 pi/2 --steps 5 --target marrakesh nighthawk --smoke

Kim et al. (Nature 2023) Floquet step on any target graph, starting all-up |0...0>:
    U(theta_h) = prod_edges RZZ(-pi/2) . prod_q RX(theta_h)
in edge-colour layers on native couplers (0 routing SWAPs). Observable: mean magnetisation <Z>.
  * Clifford points theta_h in {0, pi/2}: stabilizer-exact (ideal) vs the Pauli-twirled target model at full width.
  * Sweep at 5 / 20 steps: the BP chi-gap |O(chi) - O(2 chi)| on heavy-hex (`marrakesh`) vs square (`nighthawk`), at
    non-Clifford theta_h in [pi/8, 3pi/8]. Tests "4-cycles hurt BP more" (RE paper HW04: BP error ~exp(-c l), smallest
    loop l = 12 on heavy-hex, 4 on the square lattice, inferred); it stays inferred until measured.
Calibration only: no claim level of its own (known BP territory).
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np
from qiskit import QuantumCircuit

from dscale import allocate as A, bp as BPm, budget as B, families as F, lint as L, targets as T

NAME = "kicked-ising"
CLAIM = "cal"
WITNESS = "magnetisation at the Clifford points (calibration of the Pauli predictor and BP)"
HARDNESS = "known BP territory (Tindall); heavy-hex vs square chi-gap"
PRESETS = {40: {"n": 40}, 100: {"n": 100}, 120: {"n": 120}}
PARAM_GRID = {"theta_h": [0.0, math.pi / 8, math.pi / 4, 3 * math.pi / 8, math.pi / 2], "steps": [5, 20],
              "chi": [2, 4, 8]}
CLIFFORD_THETAS = (0.0, math.pi / 2)


def preset_text(budget: int) -> str:
    return f"{PRESETS[budget]['n']}-qubit patch" + (" (full Nighthawk)" if budget == 120 else "")


def default_draw() -> dict:
    return F.default_draw()


def region_request(budget: int, tg: T.Target, params: dict | None = None) -> list[dict]:
    p = PRESETS[budget] | (params or {})
    return [{"name": "ising", "family": NAME, "kind": "patch", "n": p["n"], "role": "active", "min_n": 6, "lattice": "grid"}]


def _layers(edges: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    import networkx as nx
    from dscale.families.ch_qca import colour_layers

    h = nx.Graph()
    h.add_edges_from(edges)
    return colour_layers(h)


def circuit(nodes: list[int], edges: list[tuple[int, int]], theta: float, steps: int, measure: bool = True) -> QuantumCircuit:
    col = {q: k for k, q in enumerate(nodes)}
    qc = QuantumCircuit(len(nodes), len(nodes) if measure else 0, name=f"kim_t{steps}_th{theta:.3f}")
    layers = _layers([tuple(e) for e in edges])
    for _ in range(steps):
        for k in range(len(nodes)):
            qc.rx(theta, k)
        for layer in layers:
            for a, b in layer:
                qc.rzz(-math.pi / 2, col[a], col[b])
    if measure:
        for k in range(len(nodes)):
            qc.measure(k, k)
    qc.metadata = {"layout": list(nodes), "basis": "Z", "family": NAME, "root": None, "theta_h": theta,
                   "steps": steps}
    return qc


def _region(alloc: dict) -> tuple[list[int], list[tuple[int, int]]]:
    r = alloc["regions"]["ising"]
    return r["qubits"], [tuple(e) for e in r["edges"]]


def build(alloc: dict, params: dict, draw: dict) -> list[QuantumCircuit]:
    nodes, edges = _region(alloc)
    return [circuit(nodes, edges, float(params.get("theta_h", 0.0)), int(params.get("steps", 5)))]


def clifford_twin(circuits: list[QuantumCircuit]) -> list[QuantumCircuit]:
    """Snap theta_h to the nearest Clifford point (same RZZ skeleton)."""
    out = []
    for c in circuits:
        th = min(CLIFFORD_THETAS, key=lambda x: abs(x - c.metadata["theta_h"]))
        lay = c.metadata["layout"]
        out.append(circuit(lay, _edges_of(c), th, c.metadata["steps"]))
    return out


def _edges_of(qc: QuantumCircuit) -> list[tuple[int, int]]:
    lay = qc.metadata["layout"]
    seen = []
    for ins in qc.data:
        if ins.operation.name == "rzz":
            e = tuple(sorted(lay[qc.qubits.index(q)] for q in ins.qubits))
            if e not in seen:
                seen.append(e)
    return seen


def bp_circuits(alloc: dict, params: dict) -> list[dict]:
    nodes, edges = _region(alloc)
    col = {q: k for k, q in enumerate(nodes)}
    th, st = float(params.get("theta_h", math.pi / 4)), int(params.get("steps", 5))
    return [{"name": f"kicked-ising:{len(nodes)}:t{st}:th{th:.3f}", "qc": circuit(nodes, edges, th, st, measure=False),
             "clifford": any(math.isclose(th, c) for c in CLIFFORD_THETAS),
             "edges": [(col[a], col[b]) for a, b in edges]}]


def magnetisation(bits: np.ndarray) -> float:
    return float((1 - 2 * bits.astype(float)).mean())


def bp_magnetisation(qc: QuantumCircuit, edges_idx, chi: int) -> tuple[float, float]:
    import networkx as nx

    g = nx.Graph()
    g.add_nodes_from(range(qc.num_qubits))
    g.add_edges_from(edges_idx)
    t0 = time.time()
    tn = BPm.simulate(qc, chi, graph=g)
    m = float(np.mean([tn.expect_1(n, BPm.Zm) for n in g.nodes]))
    return m, time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--theta", nargs="*", default=["0", "pi/2"], help="Clifford points to check (0, pi/2)")
    ap.add_argument("--steps", type=int, nargs="*", default=[5])
    ap.add_argument("--target", nargs="*", default=["marrakesh", "nighthawk"], choices=T.NAMES)
    ap.add_argument("--budget", type=int, default=40, choices=F.BUDGETS)
    ap.add_argument("--bp-theta", type=float, nargs="*", default=[math.pi / 4])
    ap.add_argument("--chi", type=int, nargs="*", default=[2, 4, 8])
    B.add_args(ap)
    a = ap.parse_args()
    dl = B.check(a, default_repeats=1)
    thetas = [float(eval(t, {"pi": math.pi})) for t in a.theta]                 # "0", "pi/2"
    draw = default_draw()
    for tname in a.target:
        tg = T.get(tname)
        alloc = A.allocate(region_request(a.budget, tg), tg)
        nodes, edges = _region(alloc)
        print(f"kicked-ising on {tg.label}: {len(nodes)} qubits, {len(edges)} couplers")
        for st in a.steps:
            for th in thetas:
                if dl.expired():
                    dl.skip(f"{tname} Clifford theta={th:.3f} steps={st}")
                    continue
                job = build(alloc, {"theta_h": th, "steps": st}, draw)
                L.enforce(job, alloc["regions"], NAME, tg.graph, claim=False)
                exact = F.execute(job, "ideal", tname, a.shots, 1)
                noisy = F.execute(job, f"pauli:{tname}", tname, a.shots, 2)
                me, mn = magnetisation(exact["bits"][0]), magnetisation(noisy["bits"][0])
                print(f"  steps={st:2d} theta_h={th:.3f}: <Z> stabilizer-exact {me:+.4f}  |  Pauli-twirled "
                      f"{tname} {mn:+.4f}  ({noisy['sim_label']})", flush=True)
            for th in a.bp_theta:
                prev = None
                for chi in a.chi:
                    if dl.expired():
                        dl.skip(f"{tname} BP chi={chi} theta={th:.3f} steps={st}")
                        continue
                    ent = bp_circuits(alloc, {"theta_h": th, "steps": st})[0]
                    m, sec = bp_magnetisation(ent["qc"], ent["edges"], chi)
                    gap = abs(m - prev) if prev is not None else None
                    print(f"  BP steps={st:2d} theta_h={th:.3f} chi={chi:2d}: <Z>={m:+.5f}"
                          + (f"  chi-gap vs chi/2 = {gap:.2e}" if gap is not None else "") + f"  ({sec:.1f} s)",
                          flush=True)
                    prev = m
    print(dl.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
