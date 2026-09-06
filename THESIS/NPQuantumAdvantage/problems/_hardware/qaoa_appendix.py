"""Deferred hardware appendix — QAOA feasibility on P4's kernel QUBO (AC-T1.10).

OBSTRUCTION-LABELLED. This is NOT part of the headline map and makes NO advantage
claim. It converts P4's sparse/local QUBO to an Ising cost Hamiltonian, runs a
fixed-depth (p=1) QAOA on NOISELESS Aer as a sign/correctness gate, and reports the
best-sampled cost against a matched classical greedy baseline and the exact optimum.

Claim discipline: QAOA has NO provable query speedup (unlike Dürr–Høyer). Farhi,
Gamarnik & Gutmann (2020, arXiv:2004.09002) show low-depth QAOA is obstructed by
locality on such problems. The real-device (Heron) run is DEFERRED — QDEP already
found the routing advantage does not survive readout error there. `--backend` only
prints a deferral notice.

Run: python -m problems._hardware.qaoa_appendix --n 8 --seed 7
"""
from __future__ import annotations

import argparse
import itertools
from math import pi
from typing import Dict, List, Tuple

from framework.bruteforce import brute_force_min
from framework.oracle import OracleCounter
from problems.p4_kernel_digraph import instance as p4


def _ising_from_qubo(qubo, n: int) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float], float]:
    """x_i∈{0,1} → z_i∈{±1} via x_i=(1−z_i)/2. Return (h, J, offset) for the Ising
    cost Σ h_i z_i + Σ J_ij z_i z_j + offset (offset dropped from optimisation)."""
    h: Dict[int, float] = {i: 0.0 for i in range(n)}
    J: Dict[Tuple[int, int], float] = {}
    offset = 0.0
    for i, w in qubo.linear.items():
        h[i] -= w / 2.0
        offset += w / 2.0
    for (i, j), w in qubo.quadratic.items():
        J[(i, j)] = J.get((i, j), 0.0) + w / 4.0
        h[i] -= w / 4.0
        h[j] -= w / 4.0
        offset += w / 4.0
    return h, J, offset


def _qaoa_circuit(n: int, h, J, gamma: float, beta: float):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    # cost layer (linear SWAP-network-free direct couplers; swapnet routing deferred)
    for i, hi in h.items():
        if hi != 0.0:
            qc.rz(2 * gamma * hi, i)
    for (i, j), Jij in J.items():
        if Jij != 0.0:
            qc.cx(i, j)
            qc.rz(2 * gamma * Jij, j)
            qc.cx(i, j)
    # mixer layer
    qc.rx(2 * beta, range(n))
    qc.measure(range(n), range(n))
    return qc


def _greedy_baseline(inst) -> float:
    """Matched classical local baseline: greedily add the vertex that most reduces
    total violation, stop when no single move helps."""
    n = inst.n
    s = 0
    cur = p4.cost(s, inst)
    improved = True
    while improved:
        improved = False
        for v in range(n):
            cand = s ^ (1 << v)
            val = p4.cost(cand, inst)
            if val < cur:
                s, cur, improved = cand, val, True
    return cur


def main() -> None:
    ap = argparse.ArgumentParser(description="Deferred QAOA feasibility appendix (P4, obstruction-labelled)")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--backend", default="", help="real IBM device — DEFERRED (prints a notice, does not submit)")
    args = ap.parse_args()

    if args.backend:
        print(f"--backend {args.backend!r}: real-device submission is DEFERRED in this ticket.")
        print("QDEP already showed the routing advantage does not survive readout error on Heron.")
        print("Submit manually per the number-partitioning / QuantumLife workflow; run JSONs land in research_runs/.")
        return

    from qiskit_aer import AerSimulator

    inst = p4.generate(args.n, args.seed)
    qubo = p4.to_qubo(inst)
    n = args.n
    h, J, _offset = _ising_from_qubo(qubo, n)

    # exact optimum (small n) + greedy baseline
    counter = OracleCounter()
    _, opt, _ = brute_force_min(p4.enumerate(n), lambda c: p4.cost(c, inst), counter)
    greedy = _greedy_baseline(inst)

    # p=1 QAOA, coarse angle grid (feasibility only)
    sim = AerSimulator()
    grid = [pi * k / 6 for k in range(1, 6)]
    best_cost = float("inf")
    for gamma in grid:
        for beta in grid:
            qc = _qaoa_circuit(n, h, J, gamma, beta)
            counts = sim.run(qc, shots=args.shots).result().get_counts()
            for bitstr in counts:
                s = int(bitstr[::-1], 2)  # qiskit little-endian
                c = p4.cost(s, inst)
                if c < best_cost:
                    best_cost = c

    print("=== DEFERRED HARDWARE APPENDIX — FEASIBILITY / OBSTRUCTION, NOT AN ADVANTAGE CLAIM ===")
    print(f"problem            : P4 Kernel of a Digraph, n={n}, seed={args.seed}")
    print(f"exact optimum      : {opt}   (0 == a kernel exists)")
    print(f"classical greedy   : {greedy}   (matched local baseline)")
    print(f"QAOA p=1 best (Aer): {best_cost}   (noiseless sign/correctness gate)")
    print("note: QAOA has NO provable query speedup; low-depth QAOA is locality-obstructed")
    print("      (Farhi–Gamarnik–Gutmann 2020, arXiv:2004.09002). Heron run DEFERRED (QDEP obstruction).")


if __name__ == "__main__":
    main()
