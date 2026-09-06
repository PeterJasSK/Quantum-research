# The √2 Query-Advantage Ledger (schema v1)

Grover exponent (threshold): **0.5** — SURVIVES ⟺ best-known-classical exponent c > 0.5.

| id | name | space | verdict | c (best classical) | margin | mechanism | assumption |
|----|------|-------|---------|--------------------|--------|-----------|------------|
| `_3sat_reference` | 3-SAT (reference survivor) | 2^n | **SURVIVES** | 1.000 | +0.500 | — | SETH |
| `p1_betweenness` | Betweenness | n! | **COLLAPSES** | — | — | structural | none — a 2^n·poly subset DP over the placed set exists |
| `p2_numerical_matching` | Numerical Matching with Target Sums | n! | **COLLAPSES** | — | — | structural | none — best known is an O(2^n·n) bitmask assignment DP |
| `p3_quadratic_congruences` | Quadratic Congruences | 2^n | **COLLAPSES** | 0.075 | -0.425 | algebraic | none — sub-exponential (factor b + Tonelli–Shanks + CRT) |
| `p4_kernel_digraph` | Kernel of a Digraph | 2^n | **SURVIVES** | 0.531 | +0.031 | — | measured — branch-and-reduce exact exponent vs the √2 line |
| `p5_minla` | Minimum Linear Arrangement | n! | **COLLAPSES** | — | — | structural | none — best known is the O*(2^n) Bellman–Held–Karp DP |
