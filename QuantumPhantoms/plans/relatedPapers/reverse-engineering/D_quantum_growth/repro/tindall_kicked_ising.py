"""Reproduction #9 (AC-17): belief-propagation simulation of the 127-qubit Eagle kicked Ising circuit [HW04].

    python -m D_quantum_growth.repro.tindall_kicked_ising [--steps 5] [--chi 2 4 8] [--theta-points 5]   (proof-of-concept sweep)

Circuit (HW04 Eq. 1 / Kim et al.): per Trotter step Rx(theta_h) on every qubit, then exp(i pi/4 Z Z) = RZZ(-pi/2) on
every coupling edge; Eagle coupling map (geometry only) from FakeSherbrooke. Checks:
  (a) BP vs exact light-cone statevector for every site whose depth-`steps` light cone fits in <= 22 qubits, at
      theta_h in {pi/4, 1.0}, per chi;
  (b) the statement HW04 prints for short depth: "for n < 6 our method gives perfect agreement with the exact
      simulation" (p. 2): max |BP - exact| at the largest chi must be < 1e-3;
  (c) the <Z_62> theta_h sweep for each chi (figure; no exact value exists at this light-cone size here).
"""
from __future__ import annotations

import argparse
import json
import time

import matplotlib
import networkx as nx
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from D_quantum_growth.src import bp
from shared import RE_ROOT

FIG = RE_ROOT / "D_quantum_growth" / "figures" / "tindall_magnetisation.png"
LABEL = "classical simulation (belief propagation, NumPy); no quantum hardware or noise model involved"


def eagle() -> nx.Graph:
    g = nx.Graph()
    g.add_edges_from(tuple(sorted(e)) for e in FakeSherbrooke().coupling_map.get_edges())
    return g


def kicked_ising(g: nx.Graph, theta_h: float, steps: int, nodes=None) -> QuantumCircuit:
    nodes = sorted(g.nodes) if nodes is None else sorted(nodes)
    idx = {n: k for k, n in enumerate(nodes)}
    qc = QuantumCircuit(len(nodes))
    sub = g.subgraph(nodes)
    for _ in range(steps):
        for n in nodes:
            qc.rx(theta_h, idx[n])
        for a, b in sorted(sub.edges):
            qc.rzz(-np.pi / 2, idx[a], idx[b])
    return qc


def bp_zs(g: nx.Graph, theta_h: float, steps: int, chi: int, sites: list[int]) -> tuple[dict, float]:
    qc = kicked_ising(g, theta_h, steps)
    t0 = time.time()
    tn = bp.simulate(qc, chi, graph=g, regauge=False)
    return {s: tn.expect_1(s, bp.Zm) for s in sites}, time.time() - t0


def exact_lightcone(g: nx.Graph, theta_h: float, steps: int, site: int) -> float:
    ball = nx.single_source_shortest_path_length(g, site, cutoff=steps)
    nodes = sorted(ball)
    qc = kicked_ising(g, theta_h, steps, nodes)
    sub = nx.relabel_nodes(g.subgraph(nodes), {n: k for k, n in enumerate(nodes)})
    return bp.exact_observables(qc, sub)[f"Z{nodes.index(site)}"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--chi", type=int, nargs="*", default=[2, 4, 8])
    ap.add_argument("--theta-points", type=int, default=5)
    ap.add_argument("--max-lightcone", type=int, default=20)
    a = ap.parse_args()
    g = eagle()
    print(f"Eagle coupling map: {g.number_of_nodes()} qubits, {g.number_of_edges()} edges ({LABEL})")
    sites = []
    for s in sorted(g.nodes):
        if len(nx.single_source_shortest_path_length(g, s, cutoff=a.steps)) <= a.max_lightcone:
            sites.append(s)
    sites = sites[:3]
    print("sites with light cone <=", a.max_lightcone, "at depth", a.steps, ":", sites)

    table = {}
    for th in (np.pi / 4, 1.0):
        ex = {s: exact_lightcone(g, th, a.steps, s) for s in sites}
        for chi in a.chi:
            vals, dt = bp_zs(g, th, a.steps, chi, sites)
            err = max(abs(vals[s] - ex[s]) for s in sites)
            table[(round(th, 4), chi)] = {"max_err": err, "runtime_s": round(dt, 1)}
            print(f"  theta_h={th:.4f} chi={chi:2d}  max|BP - exact light-cone| over {len(sites)} sites = {err:.2e}  ({dt:.0f}s)")
    err16 = max(v["max_err"] for (th, c), v in table.items() if c == max(a.chi))
    verdict = "MATCH" if err16 < 1e-3 else "MISMATCH"
    print(f"HW04 p.2 'for n < 6 perfect agreement with exact': max err at chi={max(a.chi)} = {err16:.2e} -> {verdict}")

    ths = np.linspace(0.0, np.pi / 2, a.theta_points)
    sweep = {chi: [] for chi in a.chi}
    for chi in a.chi:
        for th in ths:
            v, _ = bp_zs(g, float(th), a.steps, chi, [62])
            sweep[chi].append(v[62])
        print(f"  <Z62>(theta_h) chi={chi}:", " ".join(f"{x:+.3f}" for x in sweep[chi]))
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    for chi in a.chi:
        ax.plot(ths, sweep[chi], "o-", ms=3, label=f"chi={chi}")
    ax.set_xlabel("theta_h"); ax.set_ylabel("<Z_62> after %d steps" % a.steps)
    ax.set_title("127-qubit Eagle kicked Ising, BP-gauged TN\n" + LABEL, fontsize=7); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG, dpi=130)
    (RE_ROOT / "D_quantum_growth" / "figures" / "tindall_summary.json").write_text(json.dumps({
        "label": LABEL, "steps": a.steps, "sites": sites,
        "table": {f"{k[0]}|{k[1]}": v for k, v in table.items()}, "max_err_largest_chi": err16, "verdict": verdict,
        "sweep": {str(c): v for c, v in sweep.items()}, "theta": ths.tolist()}, indent=1))


if __name__ == "__main__":
    main()
