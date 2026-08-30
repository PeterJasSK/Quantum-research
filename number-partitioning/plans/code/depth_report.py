"""Depth report: teleport (constant) vs SWAP (O(distance)) routing.

Deterministic, no QC. Depth is read from the CONSTRUCTED circuit (the routing is
explicit in construction -- teleported measurements vs SWAP ladders), matching how
the QuantumLife teleport study reads qc.depth() per generation.

Two views:
  * single-edge depth vs bond distance d   -> isolates one long-range coupling
  * full cost-layer depth vs n             -> the K_n cost layer (p=1, no mixer)
"""
from __future__ import annotations

import argparse
import json
import os

from qaoa_sk import single_edge_circuit, build_circuit
from sk_instance import make_instance, ising_couplings

RUNS_DIR = os.path.join(os.path.dirname(__file__), "research_runs")


def single_edge_depths(distances: list[int]) -> list[dict]:
    rows = []
    for d in distances:
        row = {"distance": d}
        for arm in ("teleport", "swap"):
            row[arm] = single_edge_circuit(arm, d).depth()
        rows.append(row)
    return rows


def cost_layer_depths(ns: list[int], seed: int, A: float) -> list[dict]:
    rows = []
    for n in ns:
        a = make_instance(n, seed)
        couplings = ising_couplings(a, A)
        row = {"n": n, "edges": len(couplings)}
        for arm in ("teleport", "swap"):
            # cost layer only: p=1, gamma arbitrary, no mixer needed for depth.
            qc = build_circuit(arm, couplings, n, 1, [0.5], [0.0])
            row[arm] = qc.depth()
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Teleport vs SWAP depth report")
    ap.add_argument("--distances", type=str, default="2,4,6,8,12,16,24,36")
    ap.add_argument("--ns", type=str, default="4,6,8,10,12")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--A", type=float, default=1.0)
    args = ap.parse_args()

    distances = [int(x) for x in args.distances.split(",") if x]
    ns = [int(x) for x in args.ns.split(",") if x]

    edge = single_edge_depths(distances)
    layer = cost_layer_depths(ns, args.seed, args.A)

    print("== single-edge depth (one ZZ term) vs distance ==")
    print(f"{'d':>4} {'teleport':>10} {'swap':>8}")
    for r in edge:
        print(f"{r['distance']:>4} {r['teleport']:>10} {r['swap']:>8}")

    print("\n== full K_n cost-layer depth vs n ==")
    print(f"{'n':>4} {'edges':>6} {'teleport':>10} {'swap':>8}")
    for r in layer:
        print(f"{r['n']:>4} {r['edges']:>6} {r['teleport']:>10} {r['swap']:>8}")

    os.makedirs(RUNS_DIR, exist_ok=True)
    out = os.path.join(RUNS_DIR, "depth_report.json")
    with open(out, "w") as fh:
        json.dump(
            {"single_edge": edge, "cost_layer": layer,
             "meta": {"study": "sk-qaoa-teleport-routing", "seed": args.seed,
                      "A": args.A}},
            fh, indent=2,
        )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
