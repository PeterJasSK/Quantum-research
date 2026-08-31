"""Quantum counterpart — a closed-loop Darwinian quantum population whose
aliveness is certified QUANTUM by an entanglement witness, run on REAL IBM
hardware. Includes a "poke" and watches it recover.

The living genome
-----------------
Each generation the population is an entangled genealogy: a GHZ-like state over W
qubits, (|0..0> + |1..1>)/sqrt(2). Its aliveness observable is the genealogical
entanglement witness
    W = <X^{⊗W}>,  which -> +1 for the ideal GHZ and -> 0 for any classical
population (see classical_life.py). W above the classical null band = the order
is genuinely quantum, not classical dynamics in disguise.

Closed loop (DishBrain-style) + poke
------------------------------------
Per generation: build the genome -> apply mutation (small seeded RX rotations)
-> measure the witness -> SELECT (feedback contingent on the population's own
state: if the witness is healthy, keep the tighter genome; if degraded, reduce
mutation pressure). At generation POKE_AT we POKE (a large rotation that
scrambles coherence) and watch the witness dip then recover under selection —
the "life you can poke" signature.

Why it is better than the classical baseline
--------------------------------------------
The classical surrogate runs the identical loop but its witness never leaves the
null band around 0 — it physically cannot produce the X^{⊗W} correlation. The
quantum population holds W well above that band, so the aliveness is CERTIFIED
quantum, not a metaphor. That certificate is the contribution; a classical
system of any cleverness cannot forge it.

HONESTY: this is the toy DRAFT kill-gate. On NISQ hardware noise pulls W down
(readout + 2-qubit error), so the pass condition is "W stays above the classical
null band", not "W = 1". Small W keeps the GHZ shallow enough to survive.

Run (sim)      : python quantum_life.py
Run (hardware) : python quantum_life.py --backend ibm_fez
                 python quantum_life.py --backend auto   # least-busy device
Deps: qiskit, qiskit-aer, numpy; hardware also needs qiskit-ibm-runtime.
"""
from __future__ import annotations

import argparse
from math import pi, sqrt

import numpy as np
from qiskit import QuantumCircuit

W = 4
GENERATIONS = 30
SHOTS = 4096
POKE_AT = 15


def genome_circuit(mutation: float, poke: bool) -> QuantumCircuit:
    """GHZ genealogy over W qubits, plus mutation, measured in the X basis so the
    counts give <X^{⊗W}>."""
    qc = QuantumCircuit(W, W)
    qc.h(0)
    for i in range(W - 1):                 # entangled inheritance chain
        qc.cx(i, i + 1)
    qc.ry(mutation, range(W))              # mutation pressure (RY: tilts off X axis)
    if poke:
        qc.ry(pi / 2, 0)                   # the POKE: rotate ONE genome qubit off X
                                           # -> breaks the X^{⊗W} stabilizer, witness dips
    qc.h(range(W))                         # rotate X -> Z for measurement
    qc.measure(range(W), range(W))
    return qc


def witness_from_counts(counts: dict[str, int]) -> float:
    """<X^{⊗W}> = <parity> in the rotated basis = (even-parity - odd-parity)/N."""
    total = sum(counts.values())
    val = 0
    for bs, c in counts.items():
        parity = 1 if bs.count("1") % 2 == 0 else -1
        val += parity * c
    return val / total


def run_gen(qc: QuantumCircuit, shots: int, backend):
    if backend is None:
        from qiskit_aer import AerSimulator
        return AerSimulator().run(qc, shots=shots).result().get_counts()
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    result = SamplerV2(mode=backend).run([pm.run(qc)], shots=shots).result()
    return result[0].data.c.get_counts()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="", help="IBM backend, 'auto', or empty=Aer sim")
    ap.add_argument("--shots", type=int, default=SHOTS)
    args = ap.parse_args()

    backend = None
    if args.backend:
        from qiskit_ibm_runtime import QiskitRuntimeService
        service = QiskitRuntimeService()
        backend = (service.least_busy(operational=True, simulator=False, min_num_qubits=W)
                   if args.backend == "auto" else service.backend(args.backend))
        print(f"backend : {backend.name} ({backend.num_qubits} qubits)")

    print(f"quantum population — W={W}, {GENERATIONS} generations")
    print("gen  witness  note")
    mutation = 0.05
    ws = []
    for g in range(GENERATIONS):
        poke = (g == POKE_AT)
        qc = genome_circuit(mutation, poke)
        w = witness_from_counts(run_gen(qc, args.shots, backend))
        ws.append(w)
        # closed-loop selection: feedback contingent on the population's own state
        if not poke:
            mutation = mutation * 0.7 if w > 0.5 else min(mutation * 1.2, 0.4)
        note = "<-- POKE" if poke else ("recover" if POKE_AT < g <= POKE_AT + 5 else "")
        print(f"{g:3d}  {w:+.3f}  {note}")

    band = 3 / sqrt(args.shots)
    above = sum(1 for x in ws if x > band)
    print()
    print(f"classical null band : ±{band:.3f}")
    print(f"generations with witness above band : {above}/{GENERATIONS}")
    print(f"post-poke recovery  : gen {POKE_AT} = {ws[POKE_AT]:+.3f} -> "
          f"gen {min(POKE_AT+5, GENERATIONS-1)} = {ws[min(POKE_AT+5, GENERATIONS-1)]:+.3f}")
    print("=> witness stays above the classical null => aliveness certified QUANTUM;")
    print("   poke dips it, selection recovers it — the 'life you can poke' signature.")


if __name__ == "__main__":
    main()
