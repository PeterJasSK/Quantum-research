#!/usr/bin/env python3
"""
demo_qtree.py -- the SMALLEST faithful Quantum Tree teleport demo.

Two "genomes", 3 qubits each, wired the SAME two ways the full study wires its
102-qubit tree (research_qtree_teleport.py), just shrunk so every mechanism fits
one screen:

    genome A : qubits A0 A1 A2      3-bit branch decision
    genome B : qubits B0 B1 B2      3-bit branch decision

    1. LOCAL bond   -- a neighbour CX chain INSIDE each genome, so every gene is
                       linked to the whole genome (mirrors `_entangle`).
    2. LONG-RANGE   -- a TELEPORTED CNOT between the two genomes' lead genes
       teleported CX   (A0 control -> B0 target). NOT moving a state: it applies
                       CX(A0,B0) across the gap via a Bell pair + two mid-circuit
                       measurements + classical feed-forward (mirrors
                       `_teleport_cx`). BOTH A0 and B0 survive and come out
                       CORRELATED -- the long-range bond crosstalk cannot fake.

On a real chip A0 and B0 need never be physical neighbours, yet the teleported
CNOT still entangles them. That correlation, visible between the two genomes in
the output, is the whole point made small enough to eyeball.

TELEPORTED CNOT, step by step (the block in build_circuit):
    Bell pair          H(a); CX(a, b)          two couriers a, b entangled
    inject control     CX(A0, a); measure a    fold A0's parity into courier a
    feed-forward X     if a == 1:  X(b)
    apply to target    CX(b, B0)               courier b acts as control on B0
    disentangle        H(b); measure b
    feed-forward Z     if b == 1:  Z(A0)
    net effect = CX(A0, B0); A0 and B0 both still live, now correlated.

RUN
    # local simulator (default) -- instant, no account needed
    python demo_qtree.py

    # real IBM quantum computer (needs qiskit-ibm-runtime + saved account)
    python demo_qtree.py --real
    python demo_qtree.py --real --backend ibm_marrakesh --shots 2048

READ THE OUTPUT
    Each row is two 3-bit strings: genome A (A0 A1 A2) and genome B (B0 B1 B2).
    Because a teleported CNOT bonds A0<->B0, the two genomes are correlated --
    that shared structure is the long-range bond, small enough to see by eye.
"""

from __future__ import annotations

import argparse
from collections import Counter

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


# "character" angles so the genomes aren't trivial -- the belief encode (RY)
# of the big study, one lean per gene.
THETA_A = [1.9, 0.7, 2.4]   # genome A qubits A0,A1,A2
THETA_B = [0.6, 2.1, 1.2]   # genome B qubits B0,B1,B2


def build_circuit() -> QuantumCircuit:
    """Two 3-qubit genomes, each a local CX chain, bonded by a teleported CNOT."""
    A = QuantumRegister(3, "A")      # genome A
    B = QuantumRegister(3, "B")      # genome B
    a = QuantumRegister(1, "a")      # teleport courier near A0 (Bell-pair half)
    b = QuantumRegister(1, "b")      # teleport courier near B0 (Bell-pair half)
    cA = ClassicalRegister(3, "cA")  # genome A readout
    cB = ClassicalRegister(3, "cB")  # genome B readout
    bell = ClassicalRegister(2, "bell")  # the two teleport-measurement outcomes
    qc = QuantumCircuit(A, B, a, b, cA, cB, bell)

    # 1. belief encode -- each gene's inborn lean (RY)
    for i in range(3):
        qc.ry(THETA_A[i], A[i])
        qc.ry(THETA_B[i], B[i])

    # 2. LOCAL bond -- neighbour CX chain inside each genome, so every gene is
    #    linked to the whole genome (mirrors the full study's `_entangle`).
    qc.cx(A[0], A[1]); qc.cx(A[1], A[2])
    qc.cx(B[0], B[1]); qc.cx(B[1], B[2])
    qc.barrier()

    # 3. LONG-RANGE bond -- teleported CNOT(A0 -> B0). Applies CX across the gap
    #    via one Bell pair + two mid-circuit measures + feed-forward. A0 and B0
    #    are NEVER physical neighbours, yet end correlated (mirrors `_teleport_cx`).
    qc.h(a)
    qc.cx(a, b)                       # Bell pair spans the gap
    qc.cx(A[0], a)                    # inject A0's parity into courier a
    qc.measure(a, bell[0])
    with qc.if_test((bell[0], 1)):    # feed-forward X
        qc.x(b)
    qc.cx(b, B[0])                    # courier b acts as control on B0
    qc.h(b)
    qc.measure(b, bell[1])
    with qc.if_test((bell[1], 1)):    # feed-forward Z
        qc.z(A[0])
    # net effect: CX(A0, B0). Both genes still live, now bonded across the gap.
    qc.barrier()

    # 4. read out both genomes
    for i in range(3):
        qc.measure(A[i], cA[i])
        qc.measure(B[i], cB[i])
    return qc


def show(counts: dict, shots: int) -> None:
    """counts keys look like 'bell cB cA' (Qiskit prints cregs reversed)."""
    print(f"\ngenome A (A0A1A2) | genome B (B0B1B2) | count   ({shots} shots)")
    print("-" * 52)
    tally = Counter()
    for key, n in counts.items():
        parts = key.split()          # [bell, cB, cA]  (register order reversed)
        cA = parts[-1][::-1]         # un-reverse bit order -> A0 A1 A2
        cB = parts[-2][::-1]         # -> B0 B1 B2
        tally[(cA, cB)] += n
    for (gA, gB), n in tally.most_common(12):
        bar = "#" * max(1, round(30 * n / shots))
        print(f"   {gA}         |    {gB}         | {n:6d} {bar}")


def main() -> None:
    ap = argparse.ArgumentParser(description="tiny 2-genome teleported-CNOT demo")
    ap.add_argument("--real", action="store_true",
                    help="run on a real IBM quantum computer (default: local sim)")
    ap.add_argument("--backend", default=None,
                    help="IBM backend name; default = least busy")
    ap.add_argument("--shots", type=int, default=1024)
    args = ap.parse_args()

    qc = build_circuit()
    print("Circuit (6 genome qubits + 2 teleport couriers):")
    print(qc.draw(output="text"))

    if not args.real:
        # local dynamic-circuit simulator -- instant, no IBM account needed
        from qiskit_aer import AerSimulator
        backend = AerSimulator()
        counts = backend.run(qc, shots=args.shots).result().get_counts()
        print(f"\nBackend: AerSimulator (local)")
    else:
        # real hardware via Qiskit Runtime SamplerV2
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        service = QiskitRuntimeService()
        backend = (service.backend(args.backend) if args.backend
                   else service.least_busy(operational=True, simulator=False))
        print(f"\nBackend: {backend.name} ({backend.num_qubits} qubits)")
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
        isa = pm.run(qc)
        sampler = Sampler(mode=backend)
        job = sampler.run([isa], shots=args.shots)
        print(f"job {job.job_id()} submitted ... waiting")
        res = job.result()[0]
        # merge the three classical registers back into one 'bell cB cA' key
        d = res.data
        cnt = Counter()
        for aa, bb, bl in zip(d.cA.get_bitstrings(),
                              d.cB.get_bitstrings(),
                              d.bell.get_bitstrings()):
            cnt[f"{bl} {bb} {aa}"] += 1
        counts = dict(cnt)

    show(counts, args.shots)


if __name__ == "__main__":
    main()
