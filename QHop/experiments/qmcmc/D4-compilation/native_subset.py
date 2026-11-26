"""Hardware-native coupling subset: U uses only the SK couplings that land on heavy-hex edges (all fields kept);
the Metropolis accept uses the EXACT full energy. U stays real symmetric -> proposal symmetric -> detailed balance exact
(same argument as P1). Exact ideal spectral gaps, SK n=8,10, 5 instances, m=16 (gamma,t) draws (qmc.draw_params(0,16)).
Embedding: best (max sum J_ij^2 kept) over all BFS-ball n-node heavy-hex subgraphs x local-search spin assignment.
-> results/native_subset.jsonl"""
import json
import time

import networkx as nx
import numpy as np

import d4lib as D
qmc = D.qmc

BETAS = (0.1, 0.3, 1.0)


def best_embedding(J, seed=0):
    G = D.heavy_hex_graph()
    n = len(J)
    shapes = {}
    for v in G.nodes:
        nodes = list(nx.bfs_tree(G, v))[:n]
        H = nx.convert_node_labels_to_integers(G.subgraph(nodes))
        key = nx.weisfeiler_lehman_graph_hash(H)
        shapes.setdefault(key, list(H.edges()))
    W = J ** 2
    rng = np.random.default_rng(seed)
    best = (-1, None)
    for E in shapes.values():
        for _ in range(20):
            p = rng.permutation(n)                      # p[node] = spin
            val = lambda p: sum(W[p[a], p[b]] for a, b in E)
            cur = val(p)
            improved = True
            while improved:
                improved = False
                for a in range(n):
                    for b in range(a + 1, n):
                        p[a], p[b] = p[b], p[a]
                        v = val(p)
                        if v > cur + 1e-12:
                            cur, improved = v, True
                        else:
                            p[a], p[b] = p[b], p[a]
            if cur > best[0]:
                best = (cur, [(int(p[a]), int(p[b])) for a, b in E])
    return best


if __name__ == "__main__":
    g, ts = qmc.draw_params(0, 16)
    with open("results/native_subset.jsonl", "w") as fh:
        for n in (8, 10):
            for seed in range(5):
                t0 = time.time()
                J, h = D.fam_sk(n, seed)
                w, kept = best_embedding(J)
                Js = np.zeros_like(J)
                for i, j in kept:
                    Js[i, j] = Js[j, i] = J[i, j]
                E = qmc.ising_energies(J, h)
                Es = qmc.ising_energies(Js, h)
                Q = {"full": qmc.quantum_Q(E, g, ts), "native": qmc.quantum_Q(Es, g, ts),
                     "native_decohered": qmc.decohered_Q(Es, g, ts), "local": qmc.local_Q(n), "uniform": qmc.uniform_Q(n)}
                rec = dict(n=n, seed=seed, kept_edges=len(kept), total_edges=n * (n - 1) // 2,
                           kept_J2_frac=float(w / (np.triu(J, 1) ** 2).sum()),
                           asym_native=qmc.asymmetry(Q["native"]))
                for b in BETAS:
                    for k, M in Q.items():
                        rec[f"gap_{k}_b{b}"] = qmc.gap(M, E, b)
                rec["secs"] = round(time.time() - t0, 1)
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                print(n, seed, {b: round(rec[f"gap_native_b{b}"] / rec[f"gap_full_b{b}"], 3) for b in BETAS}, flush=True)
