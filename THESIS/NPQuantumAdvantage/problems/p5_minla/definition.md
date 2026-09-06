# P5 — Minimum Linear Arrangement (MinLA)

## Formal definition
Given a graph `G = (V, E)` with `|V| = n`, find a bijection (linear arrangement)
`φ: V → {0,…,n−1}` minimising the total edge stretch
`Σ_{(u,v)∈E} |φ(u) − φ(v)|`. (Decision version: is the minimum ≤ K?)

- **Certificate:** a vertex ordering → **ordering** search space, `|S| = n!`.
- **Objective:** `cost(order) = Σ_{(u,v)∈E} |pos(u) − pos(v)|` (minimise).

## Citation (AC-T1.8)
M. R. Garey, D. S. Johnson & L. Stockmeyer, "Some Simplified NP-Complete Graph
Problems", *Theoretical Computer Science* 1(3):237–267, 1976 — establishes MinLA
(optimal linear arrangement) NP-complete.

## QUBO map
One-hot position variables `x_{v,p} ∈ {0,1}` (vertex `v` at position `p`), index
`v·n + p`: permutation one-hot penalties + tabulated `|p−q|` couplings on the edge
endpoints. `n²` variables, degree 2, no ancillas. Resource estimate / hardware
appendix only.

## Key identity used by the hunt
Total cost `= Σ_{k=1}^{n−1} cut(P_k)`, where `P_k` is the first `k` placed vertices and
`cut(S)` counts edges with exactly one endpoint in `S`. This turns the objective into
a subset-cut sum, which the `O*(2^n)` Bellman–Held–Karp DP minimises exactly.
