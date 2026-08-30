"""QAOA circuit for SK number partitioning, with three interchangeable routers.

One LOGICAL cost layer (the same list of ZZ terms) is consumed by three routers:
  * logical  -- bare qc.cx (no routing; the ideal reference for the sign check)
  * teleport -- each long-range CX via _teleport_cx (constant depth, dynamic circuit)
  * swap     -- each long-range CX via _swap_cx (SWAP ladder, O(distance) depth)

Routing is the ONLY difference between arms (epic cross-cutting decision).

Each ZZ term uses the identity
    exp(-i theta Z_i Z_j) = CX(i,j) . RZ(2 theta, j) . CX(i,j)
so every cost edge costs TWO long-range CNOTs -- on K_n that is n(n-1) per layer.

Spins sit on a linear qubit line: spin i -> physical qubit i (layout = identity).
The teleport arm adds 2 ancilla qubits, reused across edges via mid-circuit reset.
"""
from __future__ import annotations

import os
import sys
from math import pi

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

# Reuse the verified long-range CNOT primitives by import (never copy).
_QLIFE_CODE = os.path.join(
    os.path.dirname(__file__), "..", "..", "QuantumLife", "code"
)
if _QLIFE_CODE not in sys.path:
    sys.path.insert(0, _QLIFE_CODE)
from research_qtree_teleport import _teleport_cx  # noqa: E402
from research_qtree_swaplr import _swap_cx  # noqa: E402


def cost_terms(
    couplings: dict[tuple[int, int], float], gamma: float
) -> list[tuple[int, int, float]]:
    """One layer's ZZ terms as (lo, hi, theta), theta = gamma * J_ij.

    lo < hi always, so both arms drive control=lo, target=hi identically.
    """
    terms: list[tuple[int, int, float]] = []
    for (i, j), jij in couplings.items():
        lo, hi = (i, j) if i < j else (j, i)
        terms.append((lo, hi, gamma * jij))
    return terms


def _apply_zz_logical(qc: QuantumCircuit, qr, lo: int, hi: int, theta: float) -> None:
    qc.cx(qr[lo], qr[hi])
    qc.rz(2.0 * theta, qr[hi])
    qc.cx(qr[lo], qr[hi])


def _apply_zz_swap(qc: QuantumCircuit, qr, lo: int, hi: int, theta: float) -> None:
    # _swap_cx indexes the register arithmetically -> pass integer positions.
    # Layout is identity (spin i -> qubit i), so lo/hi are the physical indices.
    _swap_cx(qc, lo, hi)
    qc.rz(2.0 * theta, qr[hi])
    _swap_cx(qc, lo, hi)


def _apply_zz_teleport(
    qc: QuantumCircuit, qr, anc, tel, k_ref: list[int],
    lo: int, hi: int, theta: float, herald: bool,
) -> None:
    """Two teleported CX around a local RZ. Ancillas reset between calls."""
    for a in (anc[0], anc[1]):
        qc.reset(a)
    _teleport_cx(qc, qr[lo], qr[hi], anc[0], anc[1], tel, k_ref[0],
                 feedforward=not herald)
    k_ref[0] += 1
    qc.rz(2.0 * theta, qr[hi])
    for a in (anc[0], anc[1]):
        qc.reset(a)
    _teleport_cx(qc, qr[lo], qr[hi], anc[0], anc[1], tel, k_ref[0],
                 feedforward=not herald)
    k_ref[0] += 1


def teleport_calls_per_run(n_edges: int, p: int) -> int:
    """Total _teleport_cx invocations -> sizes the tel classical register."""
    return 2 * n_edges * p


def build_circuit(
    arm: str,
    couplings: dict[tuple[int, int], float],
    n: int,
    p: int,
    gammas: list[float],
    betas: list[float],
    herald: bool = False,
) -> QuantumCircuit:
    """Build the p-layer QAOA circuit for the given routing arm.

    arm in {"logical", "teleport", "swap"}. Initial state H|0>^n, then p rounds
    of (cost layer, RX mixer), then measure the spin register into `c`.
    """
    if arm not in ("logical", "teleport", "swap"):
        raise ValueError(f"unknown arm: {arm}")
    n_edges = len(couplings)

    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    regs: list = [qr]
    anc = tel = None
    if arm == "teleport":
        anc = QuantumRegister(2, "a")
        tel = ClassicalRegister(2 * teleport_calls_per_run(n_edges, p), "tel")
        regs.append(anc)
    regs.append(cr)
    if tel is not None:
        regs.append(tel)
    qc = QuantumCircuit(*regs)

    qc.h(qr)

    k_ref = [0]
    for layer in range(p):
        for lo, hi, theta in cost_terms(couplings, gammas[layer]):
            if arm == "logical":
                _apply_zz_logical(qc, qr, lo, hi, theta)
            elif arm == "swap":
                _apply_zz_swap(qc, qr, lo, hi, theta)
            else:
                _apply_zz_teleport(qc, qr, anc, tel, k_ref, lo, hi, theta, herald)
        for i in range(n):
            qc.rx(2.0 * betas[layer], qr[i])

    qc.measure(qr, cr)
    return qc


def single_edge_circuit(arm: str, distance: int) -> QuantumCircuit:
    """One ZZ term across a line of `distance`+1 qubits -- for the depth report.

    Isolates the routing cost of a single long-range coupling at a given
    distance (teleport constant, swap O(distance)).
    """
    n = distance + 1
    couplings = {(0, distance): 1.0}
    return build_circuit(arm, couplings, n, 1, [pi / 4], [pi / 8])
