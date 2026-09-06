# P2 — verdict: COLLAPSES (structural)

| | |
|---|---|
| Search space | ordering / assignment, `n!` |
| Predicted (epic §6) | COLLAPSES, structural (corrected from the draft's "strongest SURVIVES") |
| **Measured** | **COLLAPSES, structural** — prediction held |
| Best-known classical | `O(2^n·n)` bitmask assignment DP |
| Hardness assumption | none — a `2^{O(n)}` DP exists |

## The hunt (`best_classical.py`)
The bitmask assignment DP assigns `x_0,…,x_{n-1}` in order; the state is the subset
of `Y`-indices already consumed, and `reachable[mask]` holds iff some feasible
partial assignment uses exactly those `Y`-indices for the first `popcount(mask)`
`x`'s. Feasibility ⇔ the full mask is reachable. This is a `2^{O(n)}` classical
algorithm, so `classify_ordering(has_subexp_classical=True)` returns **COLLAPSES
(structural)**.

## Why the √2 line erases the advantage here
Grover over the `n!` assignment space costs `√(n!) = 2^{0.5·log₂(n!)}`, whose
per-input-bit exponent `0.5·log₂(n!)/n ≈ 0.5·log₂ n` **grows** with `n`. The
classical DP is `2^{O(n)}` (exponent constant ≈ 1.0). For all `n > 4` the DP is
asymptotically below `√(n!)`: a plain subset DP already beats Grover-over-permutations.
This is the **structural** collapse mechanism — it applies to every
ordering/assignment problem admitting a Held–Karp/bitmask DP (here, always).

## Measured (seed 7, n∈{5,6,7,8})
- theorem axis: classical slope `1.000` (R²=1.0), quantum slope `0.500` (R²=1.0) —
  the BBBV-optimal quadratic **query** speedup, demonstrated by counting.
- verdict axis: ordering — no fixed `2^{c·n}` law; the DP's existence decides.
- **Advantage claim discipline:** the quadratic query speedup over brute force is real
  and undeniable (theorem); it does **not** survive against the best *known* classical
  method — that is the point of the map.
