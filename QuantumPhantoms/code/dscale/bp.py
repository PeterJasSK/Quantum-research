"""D-SCALE belief-propagation tensor-network simulator (AC-13), frozen copy of RE D `src/bp.py` @ 2609cbe.

Original docstring: Belief-propagation-gauged tensor-network simulator of heavy-hex circuits (target #9), pure NumPy.
Rebuilt from Tindall et al., "Efficient tensor network simulation of IBM's Eagle kicked Ising experiment" [HW04] and
Tindall & Fishman, "Gauging tensor networks with belief propagation":
  * one tensor per qubit, one virtual leg per coupling-graph edge, one bond-weight vector (Vidal lambda) per edge;
  * a 2-qubit gate is applied by simple update (environment = bond weights on the other legs), SVD-truncated to chi;
  * the gauge is kept by BP: messages m_{i->j} are iterated to a fixed point on the loopy graph, each edge is moved
    into the canonical (symmetric) gauge from its two messages, and expectation values use the BP environments.
It ignores measure / reset / delay / feed-forward and simulates the coherent gates of the circuit it is given.

Changed in the copy (see dscale/PORTED.md): `apply_2q` QR-reduces each site tensor before the SVD, so the SVD is
(2 r_i) x (2 r_j) with r <= 2 chi instead of (2 chi^{d-1}) x (2 chi^{d-1}); the same truncated state results. The
run-dir adversary (`adversary_circuits`, `reference_observables`, `run_adversary`, `write_report`, `main`) is dropped:
D-SCALE builds its own circuits and references (dscale.survival).
"""
from __future__ import annotations


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
        ra, rb = Ai2.shape[2], Aj2.shape[2]
        # D-SCALE: QR-reduce the "rest" legs, A[p, x, rest] = sum_r Q[rest, r] R[p, x, r]
        Qi, Ri = np.linalg.qr(Ai2.transpose(2, 0, 1).reshape(ra, -1))
        Qj, Rj = np.linalg.qr(Aj2.transpose(2, 0, 1).reshape(rb, -1))
        Ri3 = Ri.reshape(-1, 2, Ai2.shape[1]).transpose(1, 2, 0)          # (p, x, r_i)
        Rj3 = Rj.reshape(-1, 2, Aj2.shape[1]).transpose(1, 2, 0)
        theta = np.einsum("pxa,x,qxb->paqb", Ri3, lam, Rj3)              # (p_i, r_i, p_j, r_j)
        U4 = U.reshape(2, 2, 2, 2)
        theta = np.einsum("pqrs,rasb->paqb", U4, theta)
        si, sj = theta.shape[1], theta.shape[3]
        M = theta.reshape(2 * si, 2 * sj)
        u, s, vh = np.linalg.svd(M, full_matrices=False)
        keep = min(self.chi, int((s > 1e-12 * s[0]).sum()))
        self.trunc_err += float((s[keep:] ** 2).sum() / (s ** 2).sum())
        u, s, vh = u[:, :keep], s[:keep], vh[:keep]
        s = s / np.linalg.norm(s)
        u = np.einsum("pak,ba->pbk", u.reshape(2, si, keep), Qi)          # back to (p, rest_i, keep)
        vh = np.einsum("kqa,ba->kqb", vh.reshape(keep, 2, sj), Qj)
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


def smallest_chi(rows: list[dict], thr: float = 0.99) -> dict[str, int | None]:
    out = {}
    for name in dict.fromkeys(r["name"] for r in rows):
        ok = [r["bond_dim"] for r in rows if r["name"] == name and r["fidelity_vs_sim"] >= thr]
        out[name] = min(ok) if ok else None
    return out


# ---------------------------------------------------------------------------------------------- D-SCALE: AC-13 check
RE_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2] / "plans" / "relatedPapers" / "reverse-engineering"
_RE_SNIPPET = r'''
import json, sys, time, warnings
warnings.simplefilter("ignore")
from qiskit import qpy, transpile
from D_quantum_growth.src import bp, heavyhex, qca
from shared.simbackend import fake_backend
out = sys.argv[1]; t = int(sys.argv[2]); chis = [int(x) for x in sys.argv[3].split(",")]
patch = heavyhex.patch("hexagon"); nodes = patch["nodes"]
qc = qca.goldilocks_circuit(patch, t); qc.remove_final_measurements(inplace=True)
tq = transpile(qc, backend=fake_backend(), initial_layout=nodes, optimization_level=1, seed_transpiler=1)
g = bp.interaction_graph(tq, extra_nodes=nodes)
g = g.subgraph(set(nodes) | {n for n in g.nodes if g.degree(n) > 0}).copy()
edges = [tuple(sorted(e)) for e in patch["graph"].edges]
rows = {}
for chi in chis:
    t0 = time.time(); tn = bp.simulate(tq, chi, graph=g, regauge=True)
    rows[chi] = {"obs": bp.observables(tn, nodes, edges), "runtime_s": time.time() - t0}
with open(out + "/circuit.qpy", "wb") as f:
    qpy.dump(tq, f)
json.dump({"nodes": nodes, "edges": edges, "rows": rows}, open(out + "/re_bp.json", "w"))
'''


def equivalence(t: int = 4, chis=(2, 4, 8)) -> dict:
    """AC-13: the 12-q hexagon QCA (t steps) through the RE bp (subprocess from the RE folder, read-only) and through
    this QR-reduced copy, on the identical transpiled circuit. Returns max |delta| per chi and the runtimes."""
    import json
    import subprocess
    import sys
    import tempfile
    import time
    from pathlib import Path

    from qiskit import qpy

    with tempfile.TemporaryDirectory(prefix="dscale_bp_eq_") as d:
        subprocess.run([sys.executable, "-c", _RE_SNIPPET, d, str(t), ",".join(map(str, chis))], cwd=RE_ROOT,
                       check=True)
        re_out = json.loads((Path(d) / "re_bp.json").read_text())
        with open(Path(d) / "circuit.qpy", "rb") as f:
            tq = qpy.load(f)[0]
    nodes, edges = re_out["nodes"], [tuple(e) for e in re_out["edges"]]
    g = interaction_graph(tq, extra_nodes=nodes)
    g = g.subgraph(set(nodes) | {n for n in g.nodes if g.degree(n) > 0}).copy()
    res = {}
    for chi in chis:
        t0 = time.time()
        tn = simulate(tq, chi, graph=g, regauge=True)
        o = observables(tn, nodes, edges)
        dt = time.time() - t0
        ref = re_out["rows"][str(chi)]
        res[chi] = {"max_abs_delta": max(abs(o[k] - ref["obs"][k]) for k in ref["obs"]), "runtime_mvp_s": dt,
                    "runtime_re_s": ref["runtime_s"], "n_observables": len(o)}
    return res


_RE_SPEED = r'''
import json, sys, time
from qiskit import qpy
import networkx as nx
from D_quantum_growth.src import bp
d = sys.argv[1]; chi = int(sys.argv[2])
qc = qpy.load(open(d + "/sq.qpy", "rb"))[0]; meta = json.load(open(d + "/sq.json"))
g = nx.Graph(); g.add_nodes_from(range(qc.num_qubits)); g.add_edges_from(tuple(e) for e in meta["edges"])
t0 = time.time(); tn = bp.simulate(qc, chi, graph=g)
json.dump({"obs": bp.observables(tn), "runtime_s": time.time() - t0}, open(d + "/sq_re.json", "w"))
'''


def speed(chi: int = 8, steps: int = 4, side: int = 4) -> dict:
    """Degree-4 case: kicked Ising (theta_h = pi/4) on a side x side square patch of Nighthawk, RE bp vs this copy."""
    import json
    import math
    import subprocess
    import sys
    import tempfile
    import time
    from pathlib import Path

    import networkx as nx
    from qiskit import qpy

    from dscale.families import kicked_ising as K

    nodes = [10 * r + c for r in range(side) for c in range(side)]
    edges = [(a, b) for a in nodes for b in nodes if a < b and (b - a == 1 and a // 10 == b // 10 or b - a == 10)]
    col = {q: k for k, q in enumerate(nodes)}
    qc = K.circuit(nodes, edges, math.pi / 4, steps, measure=False)
    eidx = [(col[a], col[b]) for a, b in edges]
    with tempfile.TemporaryDirectory(prefix="dscale_bp_speed_") as d:
        with open(Path(d) / "sq.qpy", "wb") as f:
            qpy.dump(qc, f)
        (Path(d) / "sq.json").write_text(json.dumps({"edges": eidx}))
        subprocess.run([sys.executable, "-c", _RE_SPEED, d, str(chi)], cwd=RE_ROOT, check=True)
        re_out = json.loads((Path(d) / "sq_re.json").read_text())
    g = nx.Graph()
    g.add_nodes_from(range(qc.num_qubits))
    g.add_edges_from(eidx)
    t0 = time.time()
    o = observables(simulate(qc, chi, graph=g))
    dt = time.time() - t0
    return {"case": f"kicked Ising {side}x{side} square, {steps} steps, chi={chi}",
            "max_abs_delta": max(abs(o[k] - re_out["obs"][k]) for k in o), "runtime_mvp_s": dt,
            "runtime_re_s": re_out["runtime_s"]}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="D-SCALE BP copy: AC-13 equivalence check against the RE bp")
    ap.add_argument("--equivalence", action="store_true")
    ap.add_argument("--t", type=int, default=4)
    ap.add_argument("--chi", type=int, nargs="*", default=[2, 4, 8])
    a = ap.parse_args()
    if not a.equivalence:
        ap.print_help()
        return 0
    res = equivalence(a.t, tuple(a.chi))
    ok = True
    for chi, r in res.items():
        same = r["max_abs_delta"] <= 1e-10
        ok &= same
        print(f"  chi={chi:2d}: max |MVP - RE| = {r['max_abs_delta']:.2e} over {r['n_observables']} observables "
              f"({'identical to 1e-10' if same else 'DIFFERENT'});  MVP {r['runtime_mvp_s']:.3f} s vs "
              f"RE {r['runtime_re_s']:.3f} s")
    sp = speed()
    print(f"  speed ({sp['case']}): MVP {sp['runtime_mvp_s']:.2f} s vs RE {sp['runtime_re_s']:.2f} s "
          f"(x{sp['runtime_re_s'] / max(sp['runtime_mvp_s'], 1e-9):.1f}); max |delta| = {sp['max_abs_delta']:.1e}")
    print("equivalence:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
