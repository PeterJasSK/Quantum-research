"""Quantum counterpart — Grover search for a satisfying assignment of the SAME
verifier as classical_bruteforce.py, run on REAL IBM quantum hardware.

Why it is better (the whole point)
----------------------------------
Classical unstructured search costs O(2^n) verifier calls and that is provably
optimal classically (adversary bound). Grover finds a marked assignment in
~(pi/4) * sqrt(2^n / M) oracle calls — a QUADRATIC speedup — and by BBBV
(Bennett-Bernstein-Brassard-Vazirani 1997) NO quantum algorithm can do better
than Omega(sqrt(2^n)) oracle calls. So the speedup is:
    - quadratic:  2^n         ->  2^(n/2)
    - provably optimal:       matching upper (Grover) and lower (BBBV) bounds
    - unconditional:          independent of P vs NP, holds in the query model

n=4, M=1 solution: classical = 16 calls, Grover = round((pi/4)*sqrt(16)) = 3
oracle calls. The gap widens as 2^n / 2^(n/2) for larger n.

HONESTY (the four qualifiers that keep this bulletproof)
-------------------------------------------------------
query model . over brute force . quadratic . NOT wall-clock.
On today's NISQ hardware Grover does NOT beat classical in wall-clock seconds:
noise degrades the amplitude amplification and the oracle depth is significant.
This script's hardware run is a FEASIBILITY demonstration — it shows the marked
state is amplified above the uniform 1/2^n floor on a real device. The *advantage*
claim lives in the oracle-call count, which is exact and device-independent.

Oracle note: in the query model the oracle is a black box; the theorem counts
CALLS, not gates. Here we realize the phase oracle by marking the (classically
known) satisfying states with a multi-controlled-Z. That is a legitimate Grover
oracle for a POC; a fault-tolerant version would synthesize V(x) as a reversible
circuit, which does not change the call count the advantage rides on.

Run (sim)      : python quantum_grover.py
Run (hardware) : python quantum_grover.py --backend ibm_fez
                 python quantum_grover.py --backend auto   # least-busy device
Deps: qiskit, qiskit-aer; hardware also needs qiskit-ibm-runtime + saved account.
"""
from __future__ import annotations

import argparse
from math import floor, pi, sqrt

from qiskit import QuantumCircuit

# Solve the SAME instance the classical baseline does.
from classical_bruteforce import N_VARS, verify


def solutions(n: int) -> list[int]:
    """The marked states. (Classical precompute only to BUILD the oracle; the
    query-count advantage is about oracle calls, not this construction.)"""
    return [x for x in range(1 << n) if verify(x)]


def _mark(qc: QuantumCircuit, state: int, n: int) -> None:
    """Flip the phase of one basis state |state> via an n-controlled Z."""
    zeros = [q for q in range(n) if not ((state >> q) & 1)]
    if zeros:
        qc.x(zeros)
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)   # CZ = H . MCX . H on the target
    qc.h(n - 1)
    if zeros:
        qc.x(zeros)


def oracle(n: int, marked: list[int]) -> QuantumCircuit:
    qc = QuantumCircuit(n, name="oracle")
    for s in marked:
        _mark(qc, s, n)
    return qc


def diffuser(n: int) -> QuantumCircuit:
    """Inversion about the mean: reflect around the uniform superposition."""
    qc = QuantumCircuit(n, name="diffuser")
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))
    return qc


def grover_circuit(n: int, marked: list[int]) -> tuple[QuantumCircuit, int]:
    """Full Grover circuit. Returns (circuit, oracle_calls)."""
    m = max(1, len(marked))
    iters = max(1, floor((pi / 4) * sqrt((1 << n) / m)))
    qc = QuantumCircuit(n, n)
    qc.h(range(n))                       # uniform superposition
    orc, dif = oracle(n, marked), diffuser(n)
    for _ in range(iters):
        qc.compose(orc, range(n), inplace=True)
        qc.compose(dif, range(n), inplace=True)
    qc.measure(range(n), range(n))
    return qc, iters


def _counts_sim(qc: QuantumCircuit, shots: int) -> dict[str, int]:
    from qiskit_aer import AerSimulator
    return AerSimulator().run(qc, shots=shots).result().get_counts()


def _counts_hw(qc: QuantumCircuit, shots: int, backend_name: str) -> dict[str, int]:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    if backend_name == "auto":
        backend = service.least_busy(operational=True, simulator=False,
                                     min_num_qubits=qc.num_qubits)
    else:
        backend = service.backend(backend_name)
    print(f"backend : {backend.name} ({backend.num_qubits} qubits)")
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa = pm.run(qc)
    result = SamplerV2(mode=backend).run([isa], shots=shots).result()
    return result[0].data.c.get_counts()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="", help="IBM backend, 'auto' for least-busy, empty=Aer sim")
    ap.add_argument("--shots", type=int, default=4096)
    args = ap.parse_args()

    n = N_VARS
    marked = solutions(n)
    qc, iters = grover_circuit(n, marked)
    N = 1 << n

    print(f"search space   : 2^{n} = {N}")
    print(f"marked states  : {[format(s, f'0{n}b') for s in marked]}  (M={len(marked)})")
    print(f"Grover oracle calls (quantum) : {iters}")
    print(f"classical calls (brute force) : {N}")
    print(f"speedup factor this instance  : {N / iters:.1f}x  (asymptotic: 2^(n/2))")
    print()

    counts = _counts_hw(qc, args.shots, args.backend) if args.backend else _counts_sim(qc, args.shots)
    total = sum(counts.values())
    marked_set = {format(s, f"0{n}b") for s in marked}
    hits = sum(v for k, v in counts.items() if k in marked_set)

    top = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
    print("top measured bitstrings:")
    for k, v in top:
        flag = "  <-- SOLUTION" if k in marked_set else ""
        print(f"  {k}  {v/total:6.1%}{flag}")
    print()
    print(f"success probability (measured a solution): {hits/total:.1%}")
    print(f"uniform-guess floor for comparison       : {len(marked)/N:.1%}")
    print("amplitude amplification worked if measured >> uniform floor.")


if __name__ == "__main__":
    main()
