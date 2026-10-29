"""General Bayesian-network -> circuit compiler (Low-Yoder-Chuang [B01], Borujeni [B09, B10])."""
import argparse
import itertools
import json
import math
from dataclasses import dataclass, field

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import Statevector

from B_mapping.src.rulebook import contexts, joint_table, node_table, order
from shared import RE_ROOT


def n_qubits(n_states: int) -> int:
    return max(1, math.ceil(math.log2(n_states)))


@dataclass
class Compiled:
    """Logical circuit plus the maps needed to decode shots."""
    circuit: QuantumCircuit            # measured; clbit i measures logical qubit i
    nodes: list                        # node names in order
    states: list                       # states per node
    node_qubits: dict                  # node name -> logical qubit list (little-endian)
    n_logical: int
    n_ancilla: int
    multi_control: str
    extra: dict = field(default_factory=dict)  # e.g. B-2 site register info
    ops: list = field(default_factory=list)


# ---- op recording ---------------------------------------------------------------------------------

def load_dist(ops: list, qubits: list, p, controls: list):
    """Record Ry-tree ops that load categorical p on `qubits` (little-endian) conditional on `controls`
    = [(qubit, bit), ...]. Unused codes get probability 0."""
    k = len(qubits)
    full = np.zeros(2 ** k)
    full[: len(p)] = p
    for j in range(k - 1, -1, -1):
        for prefix in range(2 ** (k - 1 - j)):
            m = [0.0, 0.0]
            for code in range(2 ** k):
                if code >> (j + 1) == prefix:
                    m[(code >> j) & 1] += full[code]
            if m[0] + m[1] <= 0:
                continue
            theta = 2 * math.atan2(math.sqrt(m[1]), math.sqrt(m[0]))  # 2*atan(sqrt(P1/P0)) [B01, B09]
            if abs(theta) < 1e-15:
                continue
            own = [(qubits[j + 1 + i], (prefix >> i) & 1) for i in range(k - 1 - j)]
            ops.append((theta, list(controls) + own, qubits[j]))


def max_controls(ops: list) -> int:
    return max((len(c) for _, c, _ in ops), default=0)


def emit(qc: QuantumCircuit, ops: list, mode: str, anc: list):
    for theta, controls, target in ops:
        m = len(controls)
        if m == 0:
            qc.ry(theta, target)
            continue
        qs = [q for q, _ in controls]
        if mode == "mcry" or m == 1:
            cs = sum(b << i for i, (_, b) in enumerate(controls))
            qc.append(RYGate(theta).control(m, ctrl_state=cs), qs + [target])
            continue
        zeros = [q for q, b in controls if b == 0]
        for q in zeros:
            qc.x(q)
        chain = [(qs[0], qs[1], anc[0])] + [(qs[i], anc[i - 2], anc[i - 1]) for i in range(2, m)]
        for a, b, t in chain:
            qc.ccx(a, b, t)
        qc.cry(theta, anc[m - 2], target)
        for a, b, t in reversed(chain):
            qc.ccx(a, b, t)
        for q in zeros:
            qc.x(q)


def _bits(state: int, width: int) -> list:
    return [(state >> i) & 1 for i in range(width)]


def node_ops(node: dict, table: np.ndarray, qubits: dict, extra_controls: list = ()) -> list:
    """Ops for one node: one Ry tree per parent-state combination (controlled on parent qubits)."""
    ops = []
    pnames = node["parents"]
    pstates = [table.shape[i] for i in range(len(pnames))]
    for combo in itertools.product(*[range(s) for s in pstates]):
        row = table[combo] if pnames else table
        controls = list(extra_controls)
        for name, s in zip(pnames, combo):
            controls += [(q, b) for q, b in zip(qubits[name], _bits(s, len(qubits[name])))]
        load_dist(ops, qubits[node["name"]], row, controls)
    return ops


def finish(ops, node_qubits, nodes, states, n_logical, multi_control, extra=None) -> Compiled:
    n_anc = max(0, max_controls(ops) - 1) if multi_control == "ancilla" else 0
    qr = QuantumRegister(n_logical + n_anc, "q")
    cr = ClassicalRegister(n_logical, "c")
    qc = QuantumCircuit(qr, cr)
    emit(qc, ops, multi_control, list(range(n_logical, n_logical + n_anc)))
    qc.measure(range(n_logical), range(n_logical))
    return Compiled(qc, nodes, states, node_qubits, n_logical, n_anc, multi_control, extra or {}, ops)


def compile_rulebook(rulebook: dict, context: dict, *, multi_control: str = "mcry") -> Compiled:
    if multi_control not in ("mcry", "ancilla"):
        raise ValueError("multi_control must be mcry or ancilla")
    nodes = order(rulebook)
    qubits, nxt = {}, 0
    for n in nodes:
        k = n_qubits(len(n["states"]))
        qubits[n["name"]] = list(range(nxt, nxt + k))
        nxt += k
    ops = []
    for n in nodes:
        ops += node_ops(n, node_table(n, context), qubits)
    return finish(ops, qubits, [n["name"] for n in nodes], [n["states"] for n in nodes], nxt, multi_control)


# ---- exact statevector and decoding ----------------------------------------------------------------

def unmeasured(c: Compiled) -> QuantumCircuit:
    return c.circuit.remove_final_measurements(inplace=False)


def decode_bits(c: Compiled, bits: list):
    """bits[i] = value of logical qubit i. Returns tuple of state indices, or None if an unused code."""
    combo = []
    for name, st in zip(c.nodes, c.states):
        code = sum(bits[q] << i for i, q in enumerate(c.node_qubits[name]))
        if code >= len(st):
            return None
        combo.append(code)
    return tuple(combo)


def statevector_joint(c: Compiled) -> dict:
    """Exact output distribution over node-state combos. Checks ancillas return to |0>."""
    probs = np.abs(Statevector(unmeasured(c)).data) ** 2
    out, leak = {}, 0.0
    for idx, p in enumerate(probs):
        if p < 1e-15:
            continue
        if idx >> c.n_logical:
            leak += p
            continue
        combo = decode_bits(c, [(idx >> i) & 1 for i in range(c.n_logical)])
        if combo is None:
            leak += p
            continue
        out[combo] = out.get(combo, 0.0) + p
    if leak > 1e-9:
        raise AssertionError(f"probability {leak:.3e} on invalid codes / dirty ancillas")
    return out


def max_dp(a: dict, b: dict) -> float:
    return max((abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)), default=0.0)


def check(rulebook: dict, modes=("mcry", "ancilla")) -> list:
    rows = []
    for ctx in contexts(rulebook):
        exact = joint_table(rulebook, ctx)
        for mode in modes:
            c = compile_rulebook(rulebook, ctx, multi_control=mode)
            rows.append((ctx, mode, c.n_logical, c.n_ancilla, max_dp(statevector_joint(c), exact)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", required=True, metavar="RULEBOOK", help="statevector vs joint_table")
    ap.add_argument("--multi-control", choices=("mcry", "ancilla"), help="default: both")
    args = ap.parse_args()
    p = RE_ROOT / args.check if not args.check.startswith("/") else args.check
    rb = json.loads(open(p).read())
    rows = check(rb, (args.multi_control,) if args.multi_control else ("mcry", "ancilla"))
    worst = 0.0
    for ctx, mode, nq, na, d in rows:
        print(f"{rb['rulebook_id']:<22} {str(ctx):<34} {mode:<8} qubits={nq}+{na}anc  max|dp|={d:.2e}")
        worst = max(worst, d)
    print("OK" if worst <= 1e-9 else "FAIL", f"(worst {worst:.2e})")
    raise SystemExit(0 if worst <= 1e-9 else 1)


if __name__ == "__main__":
    main()
