"""Belief-propagation-gauged tensor-network simulator of heavy-hex circuits (target #9), pure NumPy.

Rebuilt from Tindall et al., "Efficient tensor network simulation of IBM's Eagle kicked Ising experiment" [HW04] and
Tindall & Fishman, "Gauging tensor networks with belief propagation":
  * one tensor per qubit, one virtual leg per coupling-graph edge, one bond-weight vector (Vidal lambda) per edge;
  * a 2-qubit gate is applied by simple update (environment = bond weights on the other legs), SVD-truncated to chi;
  * the gauge is kept by BP: messages m_{i->j} are iterated to a fixed point on the loopy graph, each edge is moved
    into the canonical (symmetric) gauge from its two messages, and expectation values use the BP environments.
It ignores measure / reset / delay / feed-forward and simulates the coherent gates of the circuit it is given.

    python -m D_quantum_growth.src.bp --run <run_dir>     # writes simulability_report.json for a D run
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

X = np.array([[0, 1], [1, 0]], complex)
Zm = np.diag([1.0, -1.0]).astype(complex)
SKIP = {"measure", "reset", "delay", "barrier", "if_else", "switch_case", "for_loop", "save_statevector", "id"}


class BPTN:
    def __init__(self, graph: nx.Graph, chi: int):
        self.g = graph
        self.chi = chi
        self.nb = {n: sorted(graph[n]) for n in graph.nodes}
        self.T = {n: np.zeros((2,) + (1,) * len(self.nb[n]), complex) for n in graph.nodes}
        for n in graph.nodes:
            self.T[n].reshape(-1)[0] = 1.0
        self.lam = {self._e(i, j): np.ones(1) for i, j in graph.edges}
        self.msg: dict[tuple[int, int], np.ndarray] = {}
        self.trunc_err = 0.0

    @staticmethod
    def _e(i, j):
        return (i, j) if i < j else (j, i)

    # ------------------------------------------------------------ gates
    def apply_1q(self, n: int, U: np.ndarray) -> None:
        self.T[n] = np.tensordot(U, self.T[n], axes=([1], [0]))

    def apply_2q(self, i: int, j: int, U: np.ndarray) -> None:
        """U[(p_i p_j), (p_i' p_j')] as a 4x4 matrix."""
        if j not in self.nb[i]:
            raise ValueError(f"gate on ({i},{j}) is not a coupling-graph edge")
        Ti, Tj = self.T[i], self.T[j]
        ki, kj = self.nb[i].index(j), self.nb[j].index(i)
        # weight the other legs by their bond weights (simple-update environment)
        Ai = self._weighted(i, Ti, skip=j)
        Aj = self._weighted(j, Tj, skip=i)
        Ai = np.moveaxis(Ai, 1 + ki, 1)                      # (p, x, others...)
        Aj = np.moveaxis(Aj, 1 + kj, 1)
        lam = self.lam[self._e(i, j)]
        di = Ai.shape[2:]
        dj = Aj.shape[2:]
        Ai2 = Ai.reshape(2, Ai.shape[1], -1)
        Aj2 = Aj.reshape(2, Aj.shape[1], -1)
        theta = np.einsum("pxa,x,qxb->paqb", Ai2, lam, Aj2)              # (p_i, rest_i, p_j, rest_j)
        U4 = U.reshape(2, 2, 2, 2)
        theta = np.einsum("pqrs,rasb->paqb", U4, theta)
        ra, rb = theta.shape[1], theta.shape[3]
        M = theta.reshape(2 * ra, 2 * rb)
        u, s, vh = np.linalg.svd(M, full_matrices=False)
        keep = min(self.chi, int((s > 1e-12 * s[0]).sum()))
        self.trunc_err += float((s[keep:] ** 2).sum() / (s ** 2).sum())
        u, s, vh = u[:, :keep], s[:keep], vh[:keep]
        s = s / np.linalg.norm(s)
        u = u.reshape(2, ra, keep)
        vh = vh.reshape(keep, 2, rb)
        Ai_new = u.reshape((2,) + di + (keep,))                           # (p, others_i..., x)
        Ai_new = np.moveaxis(Ai_new, -1, 1)                                # (p, x, others...)
        Aj_new = vh.transpose(1, 2, 0).reshape((2,) + dj + (keep,))
        Aj_new = np.moveaxis(Aj_new, -1, 1)
        # remove the environment weights again (Gamma form)
        Ai_new = self._unweight(i, Ai_new, skip=j, bond_axis=1)
        Aj_new = self._unweight(j, Aj_new, skip=i, bond_axis=1)
        # restore the leg order
        self.T[i] = np.moveaxis(Ai_new, 1, 1 + ki)
        self.T[j] = np.moveaxis(Aj_new, 1, 1 + kj)
        self.lam[self._e(i, j)] = s
        self.msg.clear()

    def _legs_others(self, n, skip):
        return [k for k in self.nb[n] if k != skip]

    def _weighted(self, n, T, skip):
        out = T
        for ax, k in enumerate(self.nb[n]):
            if k == skip:
                continue
            w = self.lam[self._e(n, k)]
            sh = [1] * out.ndim
            sh[1 + ax] = len(w)
            out = out * w.reshape(sh)
        return out

    def _unweight(self, n, A, skip, bond_axis):
        """A has axes (p, bond(skip), others in nb order without skip). Divide the others by their weights."""
        others = self._legs_others(n, skip)
        for pos, k in enumerate(others):
            w = self.lam[self._e(n, k)]
            sh = [1] * A.ndim
            sh[2 + pos] = len(w)
            A = A / np.where(np.abs(w) < 1e-12, 1.0, w).reshape(sh)
        return A

    # ------------------------------------------------------------ BP
    def _absorbed(self, n):
        """Tensor with sqrt(lambda) absorbed on every leg."""
        out = self.T[n]
        for ax, k in enumerate(self.nb[n]):
            w = np.sqrt(self.lam[self._e(n, k)])
            sh = [1] * out.ndim
            sh[1 + ax] = len(w)
            out = out * w.reshape(sh)
        return out

    def _double(self, n, T, keep: list[int]):
        """Contract T_n with conj(T_n) and incoming messages on every leg not in `keep`.
        Returns axes (p, keep_ket..., p', keep_bra...)."""
        legs = self.nb[n]
        nl = len(legs)
        # indices: p=0, ket legs 1..nl, p'=nl+1, bra legs nl+2..2nl+1
        ket = [0] + [1 + a for a in range(nl)]
        bra = [nl + 1] + [nl + 2 + a for a in range(nl)]
        ops, subs = [T, T.conj()], [ket, bra]
        for a, k in enumerate(legs):
            if k in keep:
                continue
            ops.append(self.msg[(k, n)])
            subs.append([1 + a, nl + 2 + a])
        out = [0] + [1 + a for a, k in enumerate(legs) if k in keep] + [nl + 1] + \
              [nl + 2 + a for a, k in enumerate(legs) if k in keep]
        return np.einsum(*[x for pair in zip(ops, subs) for x in pair], out, optimize=True)

    def bp(self, iters: int = 60, tol: float = 1e-10) -> int:
        T = {n: self._absorbed(n) for n in self.g.nodes}
        if not self.msg:
            for i, j in self.g.edges:
                for a, b in ((i, j), (j, i)):
                    d = T[a].shape[1 + self.nb[a].index(b)]
                    self.msg[(a, b)] = np.eye(d, dtype=complex) / d
        for it in range(iters):
            delta = 0.0
            for (a, b) in list(self.msg):
                R = self._double(a, T[a], keep=[b])
                m = np.einsum("pxpy->xy", R)
                m = (m + m.conj().T) / 2
                m = m / np.trace(m).real
                delta = max(delta, float(np.abs(m - self.msg[(a, b)]).max()))
                self.msg[(a, b)] = m
            if delta < tol:
                return it + 1
        return iters

    def gauge(self) -> None:
        """BP gauge fixing: from the converged messages of each edge, m_{i->j} = Pi Pi^dag, m_{j->i} = Pj Pj^dag,
        the core Pi^T Pj = U L W^dag gives the canonical bond (weights L) and the leg transforms
        X_i = pinv(Pi^T) U, X_j = (W^dag pinv(Pj))^T that put every edge in symmetric (Vidal) gauge."""
        if not self.msg:
            self.bp()
        Tt = {n: self._absorbed(n) for n in self.g.nodes}
        X, newlam = {}, {}
        for i, j in self.g.edges:
            def factor(m):
                w, v = np.linalg.eigh(m)
                keep = w > 1e-12 * max(w.max(), 1e-300)
                return v[:, keep] * np.sqrt(w[keep])
            Pi, Pj = factor(self.msg[(i, j)]), factor(self.msg[(j, i)])
            A, B = Pi.T, Pj
            U, L, Wh = np.linalg.svd(A @ B, full_matrices=False)
            k = max(1, int((L > 1e-12 * L[0]).sum()))
            k = min(k, self.chi)
            U, L, Wh = U[:, :k], L[:k], Wh[:k]
            X[(i, j)] = np.linalg.pinv(A) @ U
            X[(j, i)] = (Wh @ np.linalg.pinv(B)).T
            newlam[self._e(i, j)] = L / np.linalg.norm(L)
        for n in self.g.nodes:
            T = Tt[n]
            for ax, k in enumerate(self.nb[n]):
                T = np.moveaxis(np.tensordot(T, X[(n, k)], axes=([1 + ax], [0])), -1, 1 + ax)
            self.T[n] = T
        self.lam = newlam
        self.msg.clear()

    def expect_1(self, n: int, O: np.ndarray) -> float:
        if not self.msg:
            self.bp()
        T = self._absorbed(n)
        R = self._double(n, T, keep=[])
        return float((np.trace(R @ O.T) / np.trace(R)).real)

    def expect_2(self, i: int, j: int, Oi: np.ndarray, Oj: np.ndarray) -> float:
        if not self.msg:
            self.bp()
        Ti, Tj = self._absorbed(i), self._absorbed(j)
        Ei = self._double(i, Ti, keep=[j])           # (p, x, p', x')
        Ej = self._double(j, Tj, keep=[i])
        rho = np.einsum("pxrw,qxsw->pqrs", Ei, Ej)
        rho = rho.reshape(4, 4)
        O = np.kron(Oi, Oj)
        return float((np.trace(rho @ O.T) / np.trace(rho)).real)


# ---------------------------------------------------------------------------------------------- circuits
def gates_of(qc: QuantumCircuit):
    """Yield (qubit indices, matrix) for the coherent gates of the circuit (control flow etc. skipped)."""
    idx = {q: k for k, q in enumerate(qc.qubits)}
    for ins in qc.data:
        op = ins.operation
        if op.name in SKIP or op.name.startswith("save"):
            continue
        qs = [idx[q] for q in ins.qubits]
        U = Operator(op).data
        if len(qs) == 1:
            yield qs, U
        elif len(qs) == 2:
            # qiskit little-endian: index = q1*2 + q0; convert to (q0, q1) ordering
            yield qs, U.reshape(2, 2, 2, 2).transpose(1, 0, 3, 2).reshape(4, 4)
        else:
            raise ValueError(f"unsupported {len(qs)}-qubit gate {op.name}")


def interaction_graph(qc: QuantumCircuit, extra_nodes=None) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(range(qc.num_qubits) if extra_nodes is None else extra_nodes)
    for qs, _ in gates_of(qc):
        if len(qs) == 2:
            g.add_edge(*qs)
    return g


def simulate(qc: QuantumCircuit, chi: int, graph: nx.Graph | None = None, regauge: bool = False) -> BPTN:
    g = graph if graph is not None else interaction_graph(qc)
    tn = BPTN(g, chi)
    for qs, U in gates_of(qc):
        if len(qs) == 1:
            tn.apply_1q(qs[0], U)
        else:
            tn.apply_2q(qs[0], qs[1], U)
    tn.bp()
    if regauge:
        tn.gauge()
        tn.bp()
    return tn


def observables(tn: BPTN, nodes=None, edges=None) -> dict[str, float]:
    """Reported observables (Q6): every <Z_i>, every nearest-neighbour <Z_i Z_j>, <X_i X_j> (keys use sorted ids)."""
    out = {}
    for n in (tn.g.nodes if nodes is None else nodes):
        out[f"Z{n}"] = tn.expect_1(n, Zm)
    for i, j in (tn.g.edges if edges is None else edges):
        a, b = sorted((i, j))
        out[f"Z{a}Z{b}"] = tn.expect_2(a, b, Zm, Zm)
        out[f"X{a}X{b}"] = tn.expect_2(a, b, X, X)
    return out


def exact_observables(qc: QuantumCircuit, graph: nx.Graph) -> dict[str, float]:
    """Exact reference by statevector of the coherent gates only (<= ~22 qubits)."""
    from qiskit.quantum_info import Pauli, Statevector

    coh = QuantumCircuit(qc.num_qubits)
    idx = {q: k for k, q in enumerate(qc.qubits)}
    for ins in qc.data:
        if ins.operation.name in SKIP or ins.operation.name.startswith("save"):
            continue
        coh.append(ins.operation, [idx[q] for q in ins.qubits])
    sv = Statevector(coh)
    n = qc.num_qubits

    def ev(lbl: dict[int, str]) -> float:
        s = ["I"] * n
        for k, p in lbl.items():
            s[n - 1 - k] = p
        return float(sv.expectation_value(Pauli("".join(s))).real)

    out = {}
    for k in graph.nodes:
        out[f"Z{k}"] = ev({k: "Z"})
    for i, j in graph.edges:
        a, b = sorted((i, j))
        out[f"Z{a}Z{b}"] = ev({a: "Z", b: "Z"})
        out[f"X{a}X{b}"] = ev({a: "X", b: "X"})
    return out


def fidelity_vs_sim(bp_obs: dict, ref: dict) -> float:
    """Q6: 1 - 1/2 * mean |BP - ideal| over every reported observable, clipped to [0, 1]."""
    d = np.mean([abs(bp_obs[k] - ref[k]) for k in ref])
    return float(np.clip(1 - 0.5 * d, 0.0, 1.0))


# ---------------------------------------------------------------------------------------------- run-dir adversary
CHIS = (2, 4, 8, 16)


def _sv_observables(sv: np.ndarray, n: int, graph: nx.Graph) -> dict[str, float]:
    """<Z_i>, <Z_i Z_j>, <X_i X_j> from a little-endian statevector (qubit k = bit k)."""
    p = np.abs(sv) ** 2
    idx = np.arange(sv.size, dtype=np.int64)
    out = {}
    bit = lambda k: ((idx >> k) & 1)
    for k in graph.nodes:
        out[f"Z{k}"] = float(p @ (1 - 2 * bit(k)))
    for i, j in graph.edges:
        a, b = sorted((i, j))
        out[f"Z{a}Z{b}"] = float(p @ ((1 - 2 * bit(a)) * (1 - 2 * bit(b))))
        out[f"X{a}X{b}"] = float((sv.conj() * sv[idx ^ ((1 << a) | (1 << b))]).sum().real)
    return out


def adversary_circuits(run_dir: Path) -> list[dict]:
    """Coherent circuits of a D run: lineage generation blocks, q-machine step, QCA t_max block (the transpiled
    physical circuit on FakeMarrakesh, so every gate is a coupling-graph edge; the C^3-H correction of the full
    patch is thereby decomposed into 1- and 2-qubit gates). Each entry: name, circuit, nodes/edges to report."""
    from qiskit import transpile

    from D_quantum_growth.src import heavyhex, lineage, memory_advantage as MA, qca
    from D_quantum_growth.src import causal_states as C
    from shared.simbackend import fake_backend

    out = [{"name": f"lineage:{k}", "qc": lineage.coherent_block(k)} for k in ("divide_Z", "divide_X", "chsh")]
    p = C.CELLCYCLE
    model = C.wu_model(p["Gamma"], p["V"], p["N"])
    out.append({"name": "qmachine:step", "qc": MA.build(model, "Z", steps=1)})
    detail = json.loads((run_dir / "qca_detail.json").read_text())
    patch = heavyhex.patch(detail["patch_kind"])
    nodes = patch["nodes"]
    qc = qca.goldilocks_circuit(patch, detail["t_max"])
    qc.remove_final_measurements(inplace=True)
    tq = transpile(qc, backend=fake_backend(), initial_layout=nodes, optimization_level=1, seed_transpiler=1)
    out.append({"name": f"qca:{detail['patch_kind']}:t{detail['t_max']}", "qc": tq, "nodes": nodes,
                "edges": [tuple(sorted(e)) for e in patch["graph"].edges], "kind": detail["patch_kind"],
                "t": detail["t_max"]})
    return out


def reference_observables(entry: dict, graph: nx.Graph) -> dict[str, float]:
    if "kind" in entry:
        from D_quantum_growth.src import heavyhex, qca
        patch = heavyhex.patch(entry["kind"])
        nodes = patch["nodes"]
        sv = qca.exact_reference(patch, entry["t"], "exact")[-1]
        idx_graph = nx.relabel_nodes(patch["graph"], {n: k for k, n in enumerate(nodes)})
        o = _sv_observables(sv, len(nodes), idx_graph)
        out = {}
        for key, v in o.items():
            if "X" in key:
                a, b = key[1:].split("X")
                out[f"X{nodes[int(a)]}X{nodes[int(b)]}" if nodes[int(a)] < nodes[int(b)] else f"X{nodes[int(b)]}X{nodes[int(a)]}"] = v
            elif key.count("Z") == 2:
                a, b = key[1:].split("Z")
                x, y = sorted((nodes[int(a)], nodes[int(b)]))
                out[f"Z{x}Z{y}"] = v
            else:
                out[f"Z{nodes[int(key[1:])]}"] = v
        return out
    return exact_observables(entry["qc"], graph)


def run_adversary(run_dir: Path, chis=CHIS, regauge: bool = True) -> dict:
    from shared.simbackend import circuit_hash

    rows = []
    for entry in adversary_circuits(run_dir):
        name, qc = entry["name"], entry["qc"]
        g = interaction_graph(qc, extra_nodes=entry.get("nodes"))
        if "nodes" in entry:                                   # drop untouched physical qubits except the patch
            keep = set(entry["nodes"]) | {n for n in g.nodes if g.degree(n) > 0}
            g = g.subgraph(keep).copy()
        ref = reference_observables(entry, g)
        for chi in chis:
            t0 = time.time()
            tn = simulate(qc, chi, graph=g, regauge=regauge)
            o = observables(tn, entry.get("nodes"), entry.get("edges"))
            rows.append({"name": name, "circuit_hash": circuit_hash(qc), "method": "belief-propagation",
                         "bond_dim": int(chi), "fidelity_vs_sim": fidelity_vs_sim(o, ref),
                         "runtime_s": round(time.time() - t0, 3), "trunc_err": tn.trunc_err})
            print(f"  {name:28s} chi={chi:2d}  fidelity_vs_sim={rows[-1]['fidelity_vs_sim']:.5f}  {rows[-1]['runtime_s']}s",
                  flush=True)
    return {"rows": rows}


def write_report(run_, rows: list[dict], mode: str) -> Path:
    from D_quantum_growth.src import io_contracts as io

    circuits = [{k: r[k] for k in ("circuit_hash", "method", "bond_dim", "fidelity_vs_sim", "runtime_s")} for r in rows]
    rec = io.envelope("simulability_report", run_, mode) | {"circuits": circuits}
    f = run_.path / "simulability_report.json"
    io.write_contract(f, rec)
    run_.add_output(f.name, "simulability_report")
    io.write_sidecar(run_.path / "simulability_detail.json", {"rows": rows, "sim_label": __import__("shared.simbackend", fromlist=["x"]).sim_label(mode)})
    return f


def smallest_chi(rows: list[dict], thr: float = 0.99) -> dict[str, int | None]:
    out = {}
    for name in dict.fromkeys(r["name"] for r in rows):
        ok = [r["bond_dim"] for r in rows if r["name"] == name and r["fidelity_vs_sim"] >= thr]
        out[name] = min(ok) if ok else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True, help="a D run directory (needs qca_detail.json)")
    ap.add_argument("--chi", type=int, nargs="*", default=list(CHIS))
    a = ap.parse_args()
    run_dir = Path(a.run).resolve()
    rec = json.loads((run_dir / "run.json").read_text())
    mode = rec["sim"]["mode"]
    # reopen the run: append the report to the existing run record
    from D_quantum_growth.src import io_contracts as io
    from shared.runrecord import start_run

    res = run_adversary(run_dir, tuple(a.chi))
    run_ = start_run(io.LETTER_DIR, f"bp-{mode}", sim_mode=mode, tool="D_quantum_growth.src.bp",
                     seed_hex=rec.get("seed_hex"))
    write_report(run_, res["rows"], mode)
    sc = smallest_chi(res["rows"])
    run_.finish("belief-propagation adversary on run " + run_dir.name + "; smallest chi with fidelity>=0.99: " + json.dumps(sc))
    print(run_.path, sc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
