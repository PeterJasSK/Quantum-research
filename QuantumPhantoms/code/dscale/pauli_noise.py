"""D-SCALE Pauli-twirled noise model (AC-4): noisy stabilizer simulation of Clifford circuits up to 156 q.

`noise_model(target)`:
  * per-edge 2q depolarizing (the target's CZ error) and per-qubit 1q depolarizing (sx / x error);
  * asymmetric readout p01 = p(1|0), p10 = p(0|1);
  * idle Pauli twirl from T1/T2, p_x = p_y = (1 - e^{-t/T1}) / 4, p_z = (1 - e^{-t/T2}) / 2 - p_x, applied by
    `delays_to_pauli`, which turns every scheduled `delay` of the ALAP-scheduled ISA circuit into an appended
    `pauli_error` (helios-class has no schedule: its datasheet memory error 1e-3 per layer is applied to every idle
    active qubit of every DAG layer, as a depolarizing Pauli mix).
DD pulses are inert here: an X-X pair is the identity on the stabilizer and the twirled idle error is unchanged.

`run(circuits, target, shots, seed)` runs on `AerSimulator(method="stabilizer")` (Clifford only; non-Clifford
circuits use method="automatic" and are limited to what Aer can hold).
`clifford_twin(circuit, stand_ins)` swaps each named non-Clifford gate for the family's declared Clifford stand-in
with the same CZ skeleton (ch-qca: CH -> CY).
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, pauli_error

from dscale import targets as T

ONEQ = ("sx", "x")
CLIFFORD_NAMES = {"h", "s", "sdg", "x", "y", "z", "sx", "sxdg", "cx", "cy", "cz", "swap", "id", "measure", "barrier",
                  "delay", "pauli", "ecr"}


def idle_probs(t: float, t1: float, t2: float) -> tuple[float, float, float]:
    px = (1 - np.exp(-t / t1)) / 4 if np.isfinite(t1) else 0.0
    pz = (1 - np.exp(-t / t2)) / 2 - px if np.isfinite(t2) else 0.0
    return float(px), float(px), float(max(pz, 0.0))


@lru_cache(maxsize=8)
def noise_model(name: str) -> NoiseModel:
    tg = T.get(name)
    nm = NoiseModel(basis_gates=["cz", "sx", "x", "rz", "id"])
    if tg.meta.get("all_to_all"):                       # uniform datasheet values: all-qubit errors (same model)
        nm.add_all_qubit_quantum_error(depolarizing_error(min(tg.e1q[0] * 3 / 2, 0.75), 1), ONEQ)
        nm.add_all_qubit_quantum_error(depolarizing_error(min(tg.e2q[(0, 1)] * 5 / 4, 15 / 16), 2), "cz")
        nm.add_all_qubit_readout_error(ReadoutError([[1 - tg.p01[0], tg.p01[0]], [tg.p10[0], 1 - tg.p10[0]]]))
        return nm
    for q in range(tg.n_qubits):
        e = min(max(tg.e1q[q], 0.0), 0.75)
        if e > 0:
            nm.add_quantum_error(depolarizing_error(e * 3 / 2, 1), ONEQ, [q])       # avg infidelity -> param
        nm.add_readout_error(ReadoutError([[1 - tg.p01[q], tg.p01[q]], [tg.p10[q], 1 - tg.p10[q]]]), [q])
    for (i, j), e in tg.e2q.items():
        lam = min(e * 5 / 4, 15 / 16)                                               # avg infidelity -> param
        if lam > 0:
            err = depolarizing_error(lam, 2)
            nm.add_quantum_error(err, "cz", [i, j])
            nm.add_quantum_error(err, "cz", [j, i])
    return nm


def isa(qc: QuantumCircuit, name: str, seed: int, layout: list[int] | None = None,
        dd_qubits: list[int] | None = None) -> QuantumCircuit:
    """Transpile to the target's ISA on the given physical layout (ALAP scheduled where durations exist).
    dd_qubits: physical qubits that get an X-X dynamical-decoupling pair in each idle window (heron mode only)."""
    tg = T.get(name)
    lay = layout if layout is not None else (qc.metadata or {}).get("layout")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if tg.backend is None:                                                      # helios-class: all-to-all
            out = transpile(qc, basis_gates=["cz", "sx", "x", "rz"], optimization_level=1, seed_transpiler=seed)
        elif dd_qubits:
            from qiskit.circuit.library import XGate
            from qiskit.transpiler import PassManager
            from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDelay, PadDynamicalDecoupling

            out = transpile(qc, backend=tg.backend, initial_layout=lay, optimization_level=1, seed_transpiler=seed)
            tgt = tg.backend.target
            out = PassManager([ALAPScheduleAnalysis(target=tgt),
                               PadDynamicalDecoupling(target=tgt, dd_sequence=[XGate(), XGate()],
                                                      qubits=list(dd_qubits)),
                               PadDelay(target=tgt)]).run(out)
        else:
            out = transpile(qc, backend=tg.backend, initial_layout=lay, optimization_level=1,
                            seed_transpiler=seed, scheduling_method="alap")
    out.metadata = dict(qc.metadata or {}) | {"isa_target": name}
    return out


def _snap(ins):
    """rz angles within 1e-6 of a multiple of pi/2 are set to it exactly (Aer's stabilizer check is strict)."""
    op = ins.operation
    if op.name == "rz":
        th = float(op.params[0])
        k = round(th / (np.pi / 2))
        if abs(th - k * np.pi / 2) < 1e-6 and th != k * np.pi / 2:
            from qiskit.circuit.library import RZGate
            return ins.replace(operation=RZGate(k * np.pi / 2))
    return ins


def delays_to_pauli(tqc: QuantumCircuit, name: str) -> QuantumCircuit:
    tg = T.get(name)
    out = tqc.copy_empty_like()
    idx = {q: k for k, q in enumerate(tqc.qubits)}
    if tg.backend is not None:
        dt = tg.backend.dt
        for ins in tqc.data:
            op = ins.operation
            if op.name == "delay":
                q = idx[ins.qubits[0]]
                t = float(op.duration) * (dt if op.unit == "dt" else {"s": 1, "ms": 1e-3, "us": 1e-6,
                                                                     "ns": 1e-9}[op.unit])
                px, py, pz = idle_probs(t, tg.t1[q], tg.t2[q])
                if px + py + pz > 0:
                    out.append(pauli_error([("X", px), ("Y", py), ("Z", pz), ("I", 1 - px - py - pz)]), [ins.qubits[0]])
                continue
            out.append(_snap(ins))
        return out
    # helios-class: memory error per layer on idle active qubits
    p = tg.memory_per_layer
    err = pauli_error([("X", p / 3), ("Y", p / 3), ("Z", p / 3), ("I", 1 - p)])
    dag = circuit_to_dag(tqc)
    active = {q for ins in tqc.data for q in ins.qubits if ins.operation.name not in ("barrier",)}
    started: set = set()
    for layer in dag.layers():
        busy = set()
        for node in layer["graph"].op_nodes():
            op = node.op
            if op.name == "rz":
                th = float(op.params[0])
                k = round(th / (np.pi / 2))
                if abs(th - k * np.pi / 2) < 1e-6:
                    from qiskit.circuit.library import RZGate
                    op = RZGate(k * np.pi / 2)
            out.append(op, node.qargs, node.cargs)
            busy |= set(node.qargs)
            if node.op.name != "measure":
                started |= set(node.qargs)
        for q in active - busy:
            if q in started:
                out.append(err, [q])
    return out


def is_clifford(qc: QuantumCircuit) -> bool:
    for ins in qc.data:
        op = ins.operation
        if op.name in CLIFFORD_NAMES:
            continue
        if op.name in ("rz", "rx", "ry", "rzz", "rxx", "ryy", "p", "u1"):
            ms = [float(t) % (np.pi / 2) for t in op.params]
            if all(np.isclose(m, 0) or np.isclose(m, np.pi / 2) for m in ms):
                continue
        if op.name in ("quantum_channel", "kraus") or op.name.startswith("pauli") or op.name == "qerror_loc":
            continue
        if getattr(op, "_quantum_error", None) is not None:
            continue
        return False
    return True


def prepare(circuits: list[QuantumCircuit], name: str, seed: int) -> list[QuantumCircuit]:
    return [delays_to_pauli(isa(qc, name, seed), name) for qc in circuits]


def run(circuits: list[QuantumCircuit], name: str, shots: int, seed: int, prepared: bool = False,
        method: str | None = None):
    """Simulate under the Pauli-twirled target model. Returns the Aer Result (memory on)."""
    pcs = circuits if prepared else prepare(circuits, name, seed)
    meth = method or ("stabilizer" if all(is_clifford(_strip_errors(c)) for c in pcs) else "automatic")
    sim = AerSimulator(method=meth, noise_model=noise_model(name))
    return sim.run(pcs, shots=shots, seed_simulator=seed, memory=True).result(), pcs


def _strip_errors(qc: QuantumCircuit) -> QuantumCircuit:
    out = qc.copy_empty_like()
    for ins in qc.data:
        if ins.operation.name in ("quantum_channel", "kraus", "qerror_loc") or \
                type(ins.operation).__name__ in ("QuantumError", "PauliError"):
            continue
        out.append(ins)
    return out


def clifford_twin(qc: QuantumCircuit, stand_ins: dict) -> QuantumCircuit:
    """Copy of qc with each instruction named in `stand_ins` replaced by stand_ins[name](op) (same qubits)."""
    out = qc.copy_empty_like()
    for ins in qc.data:
        f = stand_ins.get(ins.operation.name)
        out.append(f(ins.operation) if f else ins.operation, ins.qubits, ins.clbits)
    out.metadata = dict(qc.metadata or {}) | {"twin": True}
    out.name = qc.name + "_twin"
    return out
