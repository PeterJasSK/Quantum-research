"""D-3: Goldilocks QCA (target #7): Jones 1-D rule T6 (reproduction) and a heavy-hex-native rule (adaptation).

    python -m D_quantum_growth.src.qca --mode ideal|heron

T6 [D14 SM Eq. 3]:  U_i = |00><00| + |01> H <01| + |10> H <10| + |11><11| on the neighbours of i,
compiled as CH(a->i) CH(b->i) (H applied iff exactly one neighbour is |1>, since H H = 1), CH = RY(pi/4) CZ RY(-pi/4)
on the target. One cycle: the sublattice holding the central flip first, then the other (|0> padding at both ends).

Heavy-hex rule: "H on a site iff exactly one neighbour is active", one sublattice at a time (heavy-hex is bipartite).
Compiled as CH from every neighbour (= H^k, i.e. H iff k is odd) plus, on the degree-3 sites only, one C^3-H on the three
neighbours that cancels the k = 3 case, so the rule is exactly "k == 1". The C^3-H has mutually non-adjacent controls, so
on the full 21-qubit patch it needs routing SWAPs (the count is reported); the 12-qubit hexagon has no degree-3 site and
is SWAP-free. The odd-parity rule without the correction differs strongly (max population gap ~0.57), see qca_detail.json.
"""
from __future__ import annotations

import argparse
import itertools
from collections import Counter

import networkx as nx
import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import HGate

from D_quantum_growth.src import heavyhex, io_contracts as io, witness as W
from shared.seedhash import canonical_json, derive_seed, rng, sha256_bytes, sha256_file
from shared.simbackend import (REFERENCE_FAKE, calibration_snapshot, circuit_hash, fake_backend,
                               make_simulator, sim_label)

T_MAX = 10
SHOTS = 4000
TOOL = "D_quantum_growth.src.qca"
BASES = ("X", "Y", "Z")


# ---------------------------------------------------------------------------------------------- gates
def ch(qc: QuantumCircuit, c, t) -> None:
    """Controlled-Hadamard in the CZ basis: CH = RY(pi/4) CZ RY(-pi/4) on the target (D14 Eq. 4)."""
    qc.ry(-np.pi / 4, t)
    qc.cz(c, t)
    qc.ry(np.pi / 4, t)


def update_sites(qc, qubits, sites: list[int], nbrs: dict[int, list[int]], exact_one: bool = False) -> None:
    for i in sites:
        for a in nbrs[i]:
            ch(qc, qubits[a], qubits[i])
        if exact_one and len(nbrs[i]) == 3:                 # H^3 = H would fire at k = 3: cancel it
            qc.append(HGate().control(3), [qubits[a] for a in nbrs[i]] + [qubits[i]])


# ---------------------------------------------------------------------------------------------- 1-D T6
def t6_circuit(L: int, t: int, save: bool = False) -> QuantumCircuit:
    """Chain of L qubits (site i = qubit i-1). The |0> padding qubits of [D14] never change and a CH controlled by
    |0> is the identity, so they are omitted. Single flip at the centre. Even sites update first, then odd."""
    q = QuantumRegister(L, "q")
    qc = QuantumCircuit(q)
    qc.x(q[(L - 1) // 2])
    nbrs = {k: [m for m in (k - 1, k + 1) if 0 <= m < L] for k in range(L)}
    # first-updated sublattice = the one holding the central flip (reproduces D14 Fig. 3: for L = 17 the other order
    # gives C(t=2) = 0.115 instead of the printed ~0.09)
    c0 = (L - 1) // 2
    ev = [k for k in range(L) if k % 2 == c0 % 2]
    od = [k for k in range(L) if k % 2 != c0 % 2]
    if save:
        qc.save_statevector(label="t0")
    for c in range(t):
        update_sites(qc, q, ev, nbrs)
        update_sites(qc, q, od, nbrs)
        if save:
            qc.save_statevector(label=f"t{c + 1}")
    return qc


def marginals(sv: np.ndarray, n: int, keep: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """p1[i] = P(z_i = 1), p11[i, j] = P(z_i = z_j = 1) for the kept qubits (little-endian statevector)."""
    p = np.abs(sv) ** 2
    idx = np.arange(p.size, dtype=np.uint32)
    B = np.stack([((idx >> k) & 1) for k in keep], 1).astype(np.float64) if p.size <= 2 ** 20 else None
    if B is None:
        k = len(keep)
        p11 = np.zeros((k, k))
        p1 = np.zeros(k)
        for lo in range(0, p.size, 1 << 20):
            sl = slice(lo, lo + (1 << 20))
            Bc = np.stack([((idx[sl] >> kq) & 1) for kq in keep], 1).astype(np.float64)
            pw = p[sl]
            p1 += pw @ Bc
            p11 += (Bc * pw[:, None]).T @ Bc
        return p1, p11
    return p @ B, (B * p[:, None]).T @ B


def mi_matrix(p1: np.ndarray, p11: np.ndarray) -> np.ndarray:
    """Shannon mutual information (bits) of the z-basis 2-site marginals, D14 Eq. 22-23."""
    k = len(p1)
    I = np.zeros((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            joint = np.array([[1 - p1[i] - p1[j] + p11[i, j], p1[j] - p11[i, j]],
                              [p1[i] - p11[i, j], p11[i, j]]])
            joint = np.clip(joint, 0, None)
            joint /= joint.sum()
            a, b = joint.sum(1), joint.sum(0)
            m = joint > 1e-15
            I[i, j] = I[j, i] = float((joint[m] * np.log2(joint[m] / np.outer(a, b)[m])).sum())
    return I


def clustering(I: np.ndarray) -> float:
    """D14 Eq. 30: Tr[I^3] / sum_{i != j} [I^2]_ij."""
    I2 = I @ I
    den = I2.sum() - np.trace(I2)
    return float(np.trace(I @ I2) / den) if den > 1e-12 else 0.0


def path_length(I: np.ndarray) -> float:
    """D14 Eq. 31: mean over pairs of the shortest weighted path, edge weight 1 / I_kl."""
    k = len(I)
    g = nx.Graph()
    for i in range(k):
        for j in range(i + 1, k):
            if I[i, j] > 1e-9:
                g.add_edge(i, j, w=1.0 / I[i, j])
    tot, n = 0.0, 0
    d = dict(nx.all_pairs_dijkstra_path_length(g, weight="w"))
    for i in range(k):
        for j in range(k):
            if i != j and i in d and j in d[i]:
                tot += d[i][j]
                n += 1
    return float(tot / n) if n else float("nan")


def node_strength(I: np.ndarray) -> np.ndarray:
    return I.sum(1) / (len(I) - 1)


def t6_observables(sv: np.ndarray, L: int) -> dict:
    p1, p11 = marginals(sv, L, list(range(L)))
    I = mi_matrix(p1, p11)
    # O = sum_{i=0..L} Z_i Z_{i+1} with Z_0 = Z_{L+1} = +1 (|0> padding)
    zz = sum(1 - 2 * p1[i] - 2 * p1[i + 1] + 4 * p11[i, i + 1] for i in range(L - 1))
    O = zz + (1 - 2 * p1[0]) + (1 - 2 * p1[L - 1])
    return {"pop": p1, "I": I, "C": clustering(I), "ell": path_length(I), "strength": node_strength(I), "O": float(O)}


def t6_run(L: int, t_max: int, method: str = "statevector") -> dict:
    """Ideal T6 dynamics from the compiled circuit: populations <n_j(t)>, MI network measures, invariant O(t)."""
    qc = t6_circuit(L, t_max, save=True)
    sim = make_simulator("ideal")
    sim.set_options(method=method)
    res = sim.run(transpile(qc, sim), shots=1).result().data(0)
    out = {"t": [], "pop": [], "C": [], "ell": [], "strength": [], "O": []}
    for t in range(t_max + 1):
        o = t6_observables(np.asarray(res[f"t{t}"]), L)
        out["t"].append(t)
        for k in ("pop", "C", "ell", "strength", "O"):
            out[k].append(o[k])
    return out


# ---------------------------------------------------------------------------------------------- heavy hex
def patch_neighbours(patch: dict) -> dict[int, list[int]]:
    g = patch["graph"]
    return {n: sorted(g[n]) for n in g.nodes}


def goldilocks_circuit(patch: dict, t: int, basis=None) -> QuantumCircuit:
    """Bipartite Floquet update (A then B per cycle), t cycles from a single flip at the centre; optional
    final readout bases (bA, bB) applied to sublattice A / B. Qubit k of the circuit is nodes[k]."""
    nodes = patch["nodes"]
    pos = {n: k for k, n in enumerate(nodes)}
    q = QuantumRegister(len(nodes), "q")
    c = ClassicalRegister(len(nodes), "c")
    qc = QuantumCircuit(q, c, name=f"d3_t{t}" + (f"_{basis[0]}{basis[1]}" if basis else ""))
    nb = {pos[n]: [pos[m] for m in v] for n, v in patch_neighbours(patch).items()}
    qc.x(q[pos[patch["centre"]]])
    A = [pos[n] for n in patch["A"]]
    B = [pos[n] for n in patch["B"]]
    first, second = (A, B) if pos[patch["centre"]] in A else (B, A)
    for _ in range(t):
        update_sites(qc, q, first, nb, exact_one=True)
        update_sites(qc, q, second, nb, exact_one=True)
    if basis:
        for sub, b in ((A, basis[0]), (B, basis[1])):
            for k in sub:
                if b == "X":
                    qc.h(q[k])
                elif b == "Y":
                    qc.sdg(q[k]); qc.h(q[k])
    qc.measure(q, c)
    return qc


def exact_reference(patch: dict, t_max: int, rule: str) -> list[np.ndarray]:
    """Statevectors at t = 0..t_max with the rule applied directly: 'exact' = H iff exactly one neighbour
    active, 'parity' = H iff an odd number are active (what the circuit does)."""
    nodes = patch["nodes"]
    pos = {n: k for k, n in enumerate(nodes)}
    n = len(nodes)
    sv = np.zeros(2 ** n, complex)
    sv[1 << pos[patch["centre"]]] = 1.0
    idx = np.arange(2 ** n, dtype=np.uint32)
    nb = patch_neighbours(patch)
    bits = {k: ((idx >> k) & 1).astype(np.int8) for k in range(n)}
    out = [sv.copy()]
    centre_in_A = patch["centre"] in patch["A"]
    order = (patch["A"], patch["B"]) if centre_in_A else (patch["B"], patch["A"])
    for _ in range(t_max):
        for sub in order:
            for node in sub:
                i = pos[node]
                k = sum(bits[pos[m]] for m in nb[node])
                cond = (k == 1) if rule == "exact" else (k % 2 == 1)
                lo = idx[(bits[i] == 0) & cond]
                hi = lo | np.uint32(1 << i)
                a0, a1 = sv[lo].copy(), sv[hi].copy()
                sv[lo] = (a0 + a1) / np.sqrt(2)
                sv[hi] = (a0 - a1) / np.sqrt(2)
        out.append(sv.copy())
    return out


def swap_count(qc: QuantumCircuit, nodes: list[int], seed: int) -> int:
    """Routing SWAPs the transpiler needs on the FakeMarrakesh coupling map for this circuit (layout = patch nodes)."""
    r = transpile(qc, coupling_map=fake_backend().coupling_map, initial_layout=nodes, optimization_level=1,
                  seed_transpiler=seed, basis_gates=["swap", "cx", "cz", "rz", "sx", "x", "ry", "h", "sdg", "measure"])
    return sum(1 for i in r.data if i.operation.name == "swap")


def run(run_, seed_hex: str, mode: str, shots: int = SHOTS, t_max: int = T_MAX) -> dict:
    # Heron mode: Aer re-simulates every shot, so the noisy 21-qubit patch is infeasible (~37 s per ideal circuit);
    # heron runs one 12-qubit hexagon of the same patch (decision recorded in README / records).
    kind = "full" if mode == "ideal" else "hexagon"
    patch = heavyhex.patch(kind)
    nodes = patch["nodes"]
    n = len(nodes)
    seed = derive_seed(seed_hex, "D3-sim") % 2 ** 31
    pop_circs = [goldilocks_circuit(patch, t) for t in range(t_max + 1)]
    settings = list(itertools.product(BASES, BASES))
    set_circs = [goldilocks_circuit(patch, t_max, b) for b in settings]
    circs = pop_circs + set_circs
    # initial_layout = the patch's physical qubits, in node order; no routing needed
    tq = [transpile(c, backend=fake_backend(), initial_layout=nodes, optimization_level=1, seed_transpiler=seed)
          for c in circs]
    swaps = max(swap_count(c, nodes, seed) for c in circs)       # per circuit (they share the same cycles)
    sim = make_simulator(mode)
    res = sim.run(tq, shots=shots, seed_simulator=seed, memory=True).result()
    bits = [np.array([[int(ch_) for ch_ in s[::-1]] for s in res.get_memory(i)], np.uint8) for i in range(len(tq))]
    hashes = [circuit_hash(x) for x in tq]
    thash = sha256_bytes(canonical_json(hashes))
    pop = np.array([b.mean(0) for b in bits[: t_max + 1]])            # (t, node)

    # reference: exact / parity statevectors at each t (ideal), compared with the measured populations
    ref_exact = exact_reference(patch, t_max, "exact")
    ref_par = exact_reference(patch, t_max, "parity") if kind == "full" else ref_exact
    def pops(sv): return np.array([marginals(v, n, list(range(n)))[0] for v in sv])
    pe, pp = pops(ref_exact), pops(ref_par)
    rule_gap = float(np.abs(pe - pp).max())
    meas_vs_exact = float(np.abs(pop - pe).max())
    fid_gap = [float(abs(np.vdot(a, b)) ** 2) for a, b in zip(ref_exact, ref_par)]

    # job record
    merged = {}
    for i, b in enumerate(bits):
        for k, v in Counter("".join(map(str, r[::-1])) for r in b).items():
            merged[f"{i:05b} {k}"] = v
    job_id = io.job_id(seed_hex, "qca", mode, shots)
    cf = run_.add_job(job_id, thash, shots * len(tq), merged)
    jrec = io.envelope("quantum_job_record", run_, mode) | {
        "job_id": job_id, "sim_mode": mode, "fake_backend": REFERENCE_FAKE, "sim_seed": seed,
        "shots": shots * len(tq), "transpiled_hash": thash,
        "counts_file": {"path": cf.name, "sha256": sha256_file(cf)},
        "test_round_mask": None, "calibration_snapshot": calibration_snapshot()}
    jfile = run_.path / "quantum_job_record_qca.json"
    jref = io.write_contract(jfile, jrec)
    run_.add_output(jfile.name, "quantum_job_record")

    # witness: negativity + MI from the 9 bipartite settings
    pos = {nd: k for k, nd in enumerate(nodes)}
    set_bits = {s: bits[t_max + 1 + i] for i, s in enumerate(settings)}
    edges = sorted((min(a, b), max(a, b)) for a, b in patch["graph"].edges)
    Aset = set(patch["A"])
    obs, mi_edges, neg = {}, [], {}
    for (u, v) in edges:
        iA, jB = (u, v) if u in Aset else (v, u)
        rho_s = lambda sb: W.nearest_physical(W.tomo_pair(sb, pos[iA], pos[jB], True))
        rho = rho_s(set_bits)
        nv = W.negativity(rho)
        g = rng(seed_hex, f"D-bootstrap-qca-{u}-{v}")
        samples = []
        for _ in range(100):
            sb = {s: b[g.integers(0, len(b), len(b))] for s, b in set_bits.items()}
            samples.append(W.negativity(rho_s(sb)))
        se = float(np.std(samples, ddof=1))
        neg[(u, v)] = (nv, se)
        obs[f"N_{u}_{v}"] = {"value": nv, "stderr": se}
        mi_edges.append({"i": nodes.index(u), "j": nodes.index(v), "mi": max(W.mutual_information(rho), 0.0)})
    passed = any(v > 3 * s and v > 0 for v, s in neg.values())
    wrec = io.envelope("witness_record", run_, mode, [{"contract": "quantum_job_record", **jref}]) | {
        "claim_level": "L1", "job_record_ref": jref, "observables": obs,
        "witness_expression": "max over NN pairs of negativity N_ij > 0"
        + ("" if kind == "full" else " (12-qubit hexagon sub-patch)"), "threshold": 0.0, "passed": bool(passed),
        "bases": ["X", "Y", "Z"], "mi_network": {"nodes": [str(x) for x in nodes], "edges": mi_edges}}
    wfile = run_.path / "witness_record_qca.json"
    io.write_contract(wfile, wrec)
    run_.add_output(wfile.name, "witness_record")

    # snapshot shot at t_max for the seed shape
    shot = derive_seed(seed_hex, "D3-snapshot-shot") % shots
    snap = bits[t_max][shot]
    best_pair = max(neg, key=lambda e: neg[e][0] / max(neg[e][1], 1e-9))
    detail = {"sim_label": sim_label(mode), "patch_kind": kind, "patch_nodes": nodes, "A": patch["A"], "B": patch["B"],
              "centre": patch["centre"], "swaps_in_transpiled": swaps, "n_circuits": len(tq),
              "population": pop.tolist(), "rule_gap_max_pop": rule_gap, "rule_gap_fidelity_min": min(fid_gap),
              "measured_vs_exact_rule_max_pop_dev": meas_vs_exact, "t_max": t_max, "shots": shots,
              "negativity": {f"{u}_{v}": {"value": a, "stderr": b} for (u, v), (a, b) in neg.items()},
              "best_pair": list(best_pair), "witness_passed": bool(passed),
              "snapshot_shot": int(shot), "snapshot_bits": [int(x) for x in snap],
              "coords": {str(k): list(v) for k, v in patch["coords"].items()}}
    io.write_sidecar(run_.path / "qca_detail.json", detail)
    return {"detail": detail, "passed": bool(passed), "patch": patch, "snapshot": snap, "swaps": swaps,
            "neg": neg, "mi_edges": mi_edges, "pop": pop, "pop_exact": pe}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--shots", type=int, default=SHOTS)
    io.add_input_args(ap)
    a = ap.parse_args()
    run_, paths, docs, seed = io.begin(a.mode, f"qca-{a.mode}", TOOL, io.overrides_of(a))
    if seed is None:
        return 2
    r = run(run_, seed, a.mode, a.shots)
    d = r["detail"]
    best = max(r["neg"].values(), key=lambda v: v[0] / max(v[1], 1e-9))
    note = (f"{sim_label(a.mode)}; SWAPs: {r['swaps']}; witness passed={r['passed']} (best N={best[0]:.3f}+-{best[1]:.3f}); "
            f"exact-vs-parity rule max pop gap {d['rule_gap_max_pop']:.3g}")
    run_.finish(note)
    print(run_.path, "\n ", note, "\n  SWAPs:", r["swaps"], " physical qubits:", d["patch_nodes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
