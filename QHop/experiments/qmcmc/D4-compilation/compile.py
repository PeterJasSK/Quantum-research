"""Transpile one QeMCMC proposal circuit per (structure, size, topology) at r = 2, 3, 5 Trotter steps (1, 2, 4 diagonal
layers; end half-layers dropped, exact for Z readout) with qiskit optimization_level=3, several seeds, best kept by N_2q.
Cost at any r is then the linear model N(r) = N(3) + (r-3) * (N(5)-N(3))/2  (validated against full-r transpiles in
validate.py).  Topologies: heavy-hex 156q (FakeMarrakesh map == FakeFez == FakeKingston == FakeBoston map, checked),
square 120q (FakeNighthawk), all-to-all CZ reference (no coupling map, same basis), all-to-all native RZZ (Helios-like,
counted analytically: one native 2q gate per RZZ, two per XX+YY).
Variants for dense structures: 'sabre' (default router) and 'swapnet' (odd-even transposition network on a line path,
fixed initial layout).
Usage: python compile.py  -> results/compile_layers.jsonl
"""
import json
import sys
import time
import warnings

import networkx as nx
import numpy as np
from qiskit import transpile
from qiskit_ibm_runtime import fake_provider as fp

import d4lib as D

warnings.simplefilter("ignore")
OUT = "results/compile_layers.jsonl"
RS = (2, 3, 5)
GAM, DT = 0.425, 0.5


def backends():
    return {"heavyhex": fp.FakeMarrakesh(), "square": fp.FakeNighthawk()}


def line_path(G, n, seed=0):
    """A simple path of n nodes (DFS with backtracking from low-degree start nodes)."""
    sys.setrecursionlimit(10000)
    for start in sorted(G.nodes, key=lambda v: (G.degree(v), v)):
        path, seen = [start], {start}

        def dfs():
            if len(path) == n:
                return True
            for w in sorted(G.neighbors(path[-1]), key=lambda w: G.degree(w)):
                if w not in seen:
                    path.append(w)
                    seen.add(w)
                    if dfs():
                        return True
                    path.pop()
                    seen.discard(w)
            return False
        if dfs():
            return path
    return None


def stats(tq, target):
    ops = tq.count_ops()
    n2 = sum(v for k, v in ops.items() if k in ("cz", "ecr", "cx", "swap", "rzz"))
    n1 = sum(v for k, v in ops.items() if k in ("sx", "x"))
    d2 = tq.depth(lambda x: x.operation.num_qubits == 2)
    act = {tq.find_bit(q).index for inst in tq.data for q in inst.qubits if inst.operation.name not in ("barrier",)}
    dur = tq.estimate_duration(target, unit="s") if target is not None else None
    return dict(n2q=int(n2), n1q=int(n1), depth2q=int(d2), depth=int(tq.depth()), qubits_used=len(act), duration_s=dur)


def best_of(qc, backend, seeds, layout=None):
    recs = []
    for s in seeds:
        t0 = time.time()
        if backend is None:
            tq = transpile(qc, basis_gates=["cz", "rz", "sx", "x"], optimization_level=3, seed_transpiler=s)
        else:
            tq = transpile(qc, backend, optimization_level=3, seed_transpiler=s, initial_layout=layout)
        st = stats(tq, None if backend is None else backend.target)
        st["seed"], st["secs"] = s, round(time.time() - t0, 2)
        recs.append(st)
    b = min(recs, key=lambda x: (x["n2q"], x["depth2q"]))
    return b, recs


def structures():
    S = []
    for n in (4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 27):
        S.append(("DENSE", n, lambda r, n=n: D.ising_circuit(*D.fam_sk(n, 0), GAM, DT * r, r), D.fam_sk(n, 0)))
    for L in (3, 4, 5, 6):
        S.append(("EA", L * L, lambda r, L=L: D.ising_circuit(*D.fam_ea(L, L, 0), GAM, DT * r, r), D.fam_ea(L, L, 0)))
    for n in (12, 27, 60, 100):
        S.append(("HH", n, lambda r, n=n: D.ising_circuit(*D.fam_hh(n, 0), GAM, DT * r, r), D.fam_hh(n, 0)))
    for q in (3, 4):
        P = D.fam_potts(3, 3, q, 0)
        S.append((f"POTTS{q}", 9 * q, lambda r, P=P: D.potts_circuit(P, GAM, DT * r, r), P))
    return S


def native_counts(name, inst, r):
    """All-to-all native-RZZ (Helios-like) count and 2q depth (greedy edge colouring; K_n uses n-1 / n)."""
    if name.startswith("POTTS"):
        P = inst
        q, L = P["q"], 9
        nzz = len(P["edges"]) * q
        cls = D.ring_classes(q)
        xy_per_step = L * (2 * sum(len(c) for c in cls[:-1]) + len(cls[-1]))
        n2 = (r - 1) * nzz + r * 2 * xy_per_step
        G = nx.Graph()
        for (i, j) in P["edges"]:
            for c in range(q):
                G.add_edge(i * q + c, j * q + c)
        lg = nx.line_graph(G)
        dz = 1 + max(nx.greedy_color(lg, strategy="largest_first").values()) if len(lg) else 0
        dxy = 2 * (2 * (len(cls) - 1) + 1)          # each XX+YY = 2 native ZZ-type gates; sub-layers are site-parallel
        return dict(n2q=int(n2), depth2q=int((r - 1) * dz + r * dxy))
    J, h = inst
    E = D.edges_of(J)
    n = len(h)
    G = nx.Graph(E)
    if len(E) == n * (n - 1) // 2:
        dz = n - 1 if n % 2 == 0 else n
    else:
        lg = nx.line_graph(G)
        dz = 1 + max(nx.greedy_color(lg, strategy="largest_first").values())
    return dict(n2q=int((r - 1) * len(E)), depth2q=int((r - 1) * dz))


def main(only=None):
    B = backends()
    with open(OUT if only is None else OUT.replace(".jsonl", f"_{only}.jsonl"), "w") as fh:
        for name, n, make, inst in structures():
            if only and name != only:
                continue
            seeds = range(4) if n <= 16 else range(3)
            for r in RS:
                qc = make(r)
                rec = dict(struct=name, n=n, r=r, layers=r - 1)
                fh.write(json.dumps(dict(rec, topo="alltoall_native", variant="analytic", **native_counts(name, inst, r))) + "\n")
                b, _ = best_of(qc, None, range(1))
                fh.write(json.dumps(dict(rec, topo="alltoall_cz", variant="nomap", **b)) + "\n")
                for topo, be in B.items():
                    b, recs = best_of(qc, be, seeds)
                    fh.write(json.dumps(dict(rec, topo=topo, variant="sabre", **b,
                                             seed_n2q=[x["n2q"] for x in recs])) + "\n")
                    if name == "DENSE":
                        G = nx.Graph([tuple(e) for e in be.coupling_map.get_edges()])
                        path = line_path(G, n)
                        J, h = inst
                        qs = D.ising_swapnet_circuit(J, h, GAM, DT * r, r)
                        b2, _ = best_of(qs, be, range(2), layout=path)
                        fh.write(json.dumps(dict(rec, topo=topo, variant="swapnet", **b2)) + "\n")
                fh.flush()
                print(name, n, r, flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
