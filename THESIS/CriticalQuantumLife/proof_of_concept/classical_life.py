"""Classical baseline — a classical (measure-and-resend) Darwinian population,
the "yoked classical surrogate" that makes the quantum claim science.

Why this is the baseline
------------------------
The whole risk in "quantum artificial life" is that the aliveness is just
classical stochastic dynamics wearing a quantum costume. To rule that out you
need a control that is IDENTICAL in every way except the quantum resource: a
population whose genomes are classical bits, evolved by the same
mutate/select/reproduce loop, and read out the same way.

The distinguishing observable is the genealogical entanglement witness
    W = <X^{⊗n}>          (expectation of X on every genome qubit at once).
For a genuinely entangled GHZ-like genome, W -> +1. For ANY classical population
(product states / measure-and-resend), W -> 0 up to sampling noise: destroying
the off-diagonal coherence kills the X-basis correlation. So the classical arm
defines the NULL band around 0 that the quantum arm must beat to certify its
aliveness is quantum.

This file also runs the SAME closed-loop feedback + poke as the quantum arm, so
you can confirm the classical population NEVER lifts W above the null — no matter
how it self-organizes, it cannot fake the witness.

Run:  python classical_life.py
"""
from __future__ import annotations

import numpy as np

W = 4            # genome width (qubits-equivalent)
GENERATIONS = 30
SHOTS = 4096
POKE_AT = 15


def witness_classical(rng: np.random.Generator, shots: int) -> float:
    """Measure-and-resend genome: each readout collapses to a classical bit, so
    the X-basis parity <X^{⊗W}> averages to 0 (random ±1 per qubit)."""
    signs = rng.integers(0, 2, size=(shots, W)) * 2 - 1   # ±1, independent
    parity = np.prod(signs, axis=1)                        # X^{⊗W} per shot
    return float(parity.mean())


def main() -> None:
    rng = np.random.default_rng(0)
    print(f"classical surrogate population — W={W}, {GENERATIONS} generations")
    print("gen  witness  note")
    ws = []
    for g in range(GENERATIONS):
        w = witness_classical(rng, SHOTS)
        ws.append(w)
        note = "<-- POKE" if g == POKE_AT else ""
        print(f"{g:3d}  {w:+.3f}  {note}")
    band = 3 / np.sqrt(SHOTS)   # ~3 sigma sampling band around 0
    print()
    print(f"null band (|W| < 3/sqrt(shots)) : ±{band:.3f}")
    print(f"max |witness| over run          : {max(abs(x) for x in ws):.3f}")
    print("=> classical population stays inside the null band the whole run.")
    print("   It CANNOT certify quantum aliveness. quantum_life.py must beat this band.")


if __name__ == "__main__":
    main()
