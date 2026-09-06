# P3 — verdict: COLLAPSES (algebraic)

| | |
|---|---|
| Search space | subset, `2^n` |
| Predicted (epic §6) | COLLAPSES, algebraic |
| **Measured** | **COLLAPSES, algebraic** (best-classical `c ≈ 0.075`) — prediction held |
| Best-known classical | factor `b` → Tonelli–Shanks → CRT (sub-exponential) |
| Hardness assumption | none — sub-exponential |

## The hunt (`best_classical.py`)
Instead of scanning `2^n` values of `x`, factor `b` (`sympy.factorint`), take modular
square roots of `a` modulo each prime power (`sympy` Tonelli–Shanks), CRT-combine, and
check whether any root is `< c`. The runtime is governed by **factoring `b`**
(sub-exponential in the bit-length of `b`), **not** by `2^n`. Fitting the operation
count against `n` gives a classical exponent `c ≈ 0.075` — far below the `0.5` √2 line
⇒ `classify_subset` ⇒ **COLLAPSES (algebraic)**. (OQ-3: `sympy`'s vetted number-theory
routines are used rather than a hand-rolled solver.)

## Reporting a sub-exponential exponent (OQ-2)
A factoring+Tonelli–Shanks solver has no clean `2^{c·n}` law; the fitted near-zero
`exponent_in_n` is reported as `best_classical_exponent`, with
`hardness_assumption = "none — sub-exponential"` and the algebraic structure named in
`notes`.

## The honest twist
Grover's `2^{n/2}` is beaten by classical number theory here. The real quantum win is
**Shor**, not Grover — this is the map's "where Grover does NOT win" exemplar, and the
`--statevector` amplification demo (marked-state prob ≈ 1.0 vs the `1/2^n` floor) shows
Grover *works*, it just is not the best available algorithm.

## Measured (seed 7, n∈{6..14})
theorem axis classical slope `1.000` (R²=1.0), quantum slope `0.500` (R²=1.0);
verdict axis best-classical `c ≈ 0.075` (margin `−0.425` below the line).
