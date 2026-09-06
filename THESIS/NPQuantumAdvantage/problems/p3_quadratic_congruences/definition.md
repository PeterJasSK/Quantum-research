# P3 — Quadratic Congruences

## Formal definition
Given positive integers `a`, `b`, `c`: does there exist a non-negative integer
`x < c` with `x² ≡ a (mod b)`? Encoding `x` in `n` bits gives a feasible space of
`2^n`, so the certificate is a bit-string and this is a **subset-search** problem;
Grover costs `2^{n/2}`.

- **Certificate:** the `n`-bit integer `x` → subset search, `|S| = 2^n`.
- **Feasibility optimum:** `cost(x) = [x² ≢ a mod b] + [x ≥ c]`, minimum `0`.
- Instances plant `x* < c` and set `a = x*² mod b`, with `b = p·q` (two primes near
  `2^{n/2}`), so a solution always exists.

## Citation (AC-T1.8)
K. Manders & L. Adleman, "NP-Complete Decision Problems for Binary Quadratics",
*Journal of Computer and System Sciences* 16(2):168–184, 1978.

## HUBO map
Binary-expand `x = Σ_i 2^i x_i`; the natural penalty `(x² − a − b·t)²` is **quartic**,
so it needs quadratization ancillas to reach a QUBO
(`framework.resources.quadratization_ancillas(degree=4, …)`). Returned as a QUBO
dataclass with `degree = 4`; the ancilla overhead is the extra qubit cost the
algebraic-collapse case pays even in the fault-tolerant model.

## Why this is the "where Grover does NOT win" exemplar
The number-theoretic structure yields a sub-exponential classical algorithm (factor
`b`, take modular square roots, CRT combine), so the best-known classical exponent is
`c ≪ 0.5`. The genuine quantum win, if any, is **Shor's factoring — not Grover**.
