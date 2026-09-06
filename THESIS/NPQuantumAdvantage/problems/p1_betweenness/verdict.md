# P1 — verdict: COLLAPSES (structural)

| | |
|---|---|
| Search space | ordering, `n!` |
| Predicted (epic §6) | COLLAPSES, structural (**corrected** from the draft's "SURVIVES") |
| **Measured** | **COLLAPSES, structural** — prediction held |
| Best-known classical | `2^n·poly` placed-prefix DP |
| Hardness assumption | none — a `2^{O(n)}` DP exists |

## The hunt (`best_classical.py`)
Insert elements left to right; the state is the set already placed. A constraint
`(a, b, c)` is decided the moment its **middle** `b` is inserted: satisfied iff exactly
one of `{a, c}` is already placed (so `b` lands strictly between them in insertion
order). This contribution depends only on `(mask, b)`, so

    dp[mask ∪ {e}] = min over e of dp[mask] + viol(mask, e)

is an exact minimum-violation DP in `O(2^n·(n+m))`. Existence ⇒
`classify_ordering(True)` ⇒ **COLLAPSES (structural)**. Cross-checked: the DP optimum
equals the brute-force optimum (0) on the planted instances.

## Why the advantage collapses
Grover over `n!` costs `√(n!)`, whose per-bit exponent `≈ 0.5·log₂ n` **grows**; the
`2^{O(n)}` DP is asymptotically below it for all `n > 4`. Structural collapse.

## Measured (seed 7, n∈{5..8})
theorem axis classical slope `1.000` (R²=1.0), quantum slope `0.500` (R²=1.0) — the
quadratic **query** speedup, exact by counting; verdict axis: ordering, DP exists ⇒
collapse. The undeniable part (query-model theorem) holds; the advantage over the
*best known* classical method does not.
