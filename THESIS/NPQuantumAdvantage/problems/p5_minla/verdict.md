# P5 — verdict: COLLAPSES (structural)

| | |
|---|---|
| Search space | ordering, `n!` |
| Predicted (epic §6) | COLLAPSES, structural |
| **Measured** | **COLLAPSES, structural** — prediction held |
| Best-known classical | `O*(2^n)` Bellman–Held–Karp prefix-cut DP |
| Hardness assumption | none — a `2^{O(n)}` DP exists |

## The hunt (`best_classical.py`)
Using `total cost = Σ_{k=1}^{n−1} cut(P_k)`, the DP `dp[mask] = cut(mask) + min_{v∈mask}
dp[mask\{v}]` (cut counted for `|mask| = 1..n−1`) computes the exact minimum in
`O*(2^n)`. Cross-checked against brute force: identical optima at n = 5, 6, 7
(3, 8, 12). Existence of the DP ⇒ `classify_ordering(True)` ⇒ **COLLAPSES
(structural)**.

## Why the advantage collapses
Grover over `n!` costs `√(n!)` (per-bit exponent `≈ 0.5·log₂ n`, growing); the
`2^{O(n)}` DP is asymptotically below it. Structural collapse — same mechanism as P1.

## Measured (seed 7, n∈{5..8})
theorem axis classical slope `1.000` (R²=1.0), quantum slope `0.500` (R²=1.0). The
quadratic query speedup is real and undeniable; it does not survive the `2^n` DP.
