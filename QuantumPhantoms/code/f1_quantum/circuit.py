"""F1 circuits — the quantum roll (plan §4, AC-2).

Shallow, factorized encoding of the rulebook's Bayesian network onto a 9-qubit
property register, plus the division (sibling pair) and the CHSH certificate.

Property register layout (shared with decode.py), qubit index = MSB..LSB per field:
    size   q0 q1   |  type q2 q3   |  margin q4 q5   |  lobe q6 q7 q8

Conditioning (type|size, margin|type) is applied as nested controlled-`Ry` rotations
(`mcry`) keyed to the big-endian value of the parent register, matching the
breadth-first angle order from `rulebook.amp_tree_angles`. This stays far shallower
than a full 9-qubit arbitrary state preparation (epic §6: F1 is shallow by
construction).
"""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from f1_quantum.certify import CHSH_PAIRS, CHSH_SETTINGS

# Field slices within the 9-qubit property register (qubit indices; first = MSB).
SIZE_Q = (0, 1)
TYPE_Q = (2, 3)
MARGIN_Q = (4, 5)
LOBE_Q = (6, 7, 8)
N_PROP = 9


def _apply_tree(qc, qubits, tree, *, base, fixed_controls=(), fixed_value=0):
    """Apply a breadth-first `Ry` angle tree to a register, optionally conditioned.

    `qubits`/`fixed_controls` are integer offsets into the circuit's qubit list,
    added to `base`. `qubits[0]` is the MSB. When `fixed_controls` is non-empty,
    every rotation is additionally controlled on those parent qubits being in the
    big-endian state `fixed_value` (this is how type|size and margin|type condition).
    """
    tq = [base + q for q in qubits]
    fc = [base + q for q in fixed_controls]
    nfixed = len(fc)
    k = len(tq)
    pos = 0
    for level in range(k):
        target = tq[level]
        controls = fc + tq[:level]
        for c in range(1 << level):
            theta = tree[pos]
            pos += 1
            if not controls:
                qc.ry(theta, target)
                continue
            flips = []
            for m in range(nfixed):
                if not ((fixed_value >> (nfixed - 1 - m)) & 1):
                    flips.append(fc[m])
            for m in range(level):
                if not ((c >> (level - 1 - m)) & 1):
                    flips.append(tq[m])
            for q in flips:
                qc.x(q)
            qc.mcry(theta, controls, target)
            for q in flips:
                qc.x(q)


def _encode_properties(qc, angles, base=0):
    """Encode the rulebook Bayesian network onto the 9 property qubits at `base`."""
    _apply_tree(qc, SIZE_Q, angles["size"], base=base)
    for j in range(4):
        _apply_tree(qc, TYPE_Q, angles["type_given_size"][j],
                    base=base, fixed_controls=SIZE_Q, fixed_value=j)
    for j in range(4):
        _apply_tree(qc, MARGIN_Q, angles["margin_given_type"][j],
                    base=base, fixed_controls=TYPE_Q, fixed_value=j)
    _apply_tree(qc, LOBE_Q, angles["lobe"], base=base)


def build_tumor_circuit(angles: dict) -> QuantumCircuit:
    """Independent single-nodule circuit: one measured shot -> one tile (AC-2)."""
    prop = QuantumRegister(N_PROP, "prop")
    creg = ClassicalRegister(N_PROP, "c")
    qc = QuantumCircuit(prop, creg)
    _encode_properties(qc, angles, base=0)
    qc.measure(prop, creg)
    return qc


def build_sibling_pair_circuit(angles: dict, theta_mut: float) -> QuantumCircuit:
    """Division circuit: parent genotype -> controlled-copy + Ry(theta_mut) -> daughter.

    One measured shot -> one sibling pair (parent gen 0, daughter gen 1) correlated
    by shared ancestry (epic §5, AC-6). Full-genotype copy (Q2): every property qubit
    is copied, then mutated.
    """
    parent = QuantumRegister(N_PROP, "parent")
    daughter = QuantumRegister(N_PROP, "daughter")
    # One 18-bit register so both the Aer and SamplerV2 paths read via `.data.c`.
    # Low 9 bits (c0..c8) = parent word; high 9 bits (c9..c17) = daughter word.
    creg = ClassicalRegister(2 * N_PROP, "c")
    qc = QuantumCircuit(parent, daughter, creg)

    _encode_properties(qc, angles, base=0)  # parent occupies qubits 0..8
    for i in range(N_PROP):
        qc.cx(parent[i], daughter[i])        # controlled-copy (clone in Z basis)
        qc.ry(theta_mut, daughter[i])        # mutation

    qc.measure(parent, creg[:N_PROP])
    qc.measure(daughter, creg[N_PROP:])
    return qc


def build_chsh_circuits() -> dict[tuple[str, str], QuantumCircuit]:
    """The 4 CHSH setting circuits (AC-5). Bell pair h+cx, ry(-theta) per qubit, Z-measure."""
    out: dict[tuple[str, str], QuantumCircuit] = {}
    for a_key, b_key in CHSH_PAIRS:
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.ry(-CHSH_SETTINGS[a_key], 0)
        qc.ry(-CHSH_SETTINGS[b_key], 1)
        qc.measure([0, 1], [0, 1])
        out[(a_key, b_key)] = qc
    return out
