# P2 — Numerical Matching with Target Sums

## Formal definition
Given three multisets of positive integers `X = {x_1,…,x_n}`, `Y = {y_1,…,y_n}`,
and target sums `T = {T_1,…,T_n}`: does there exist a bijection (permutation)
`σ` of `{1,…,n}` such that `x_i + y_{σ(i)} = T_i` for every `i`?

- **Certificate:** a permutation σ → **assignment / ordering** search space, `|S| = n!`.
- **Feasibility optimum:** `cost(σ) = #{ i : x_i + y_{σ(i)} ≠ T_i }`, minimum `0`.
- Instances are generated with a **planted** σ* (`T_i := x_i + y_{σ*(i)}`), so a
  feasible matching always exists and brute force + the DP agree.

## Citation (AC-T1.8)
Numerical Matching with Target Sums is problem **[SP17]** in
M. R. Garey & D. S. Johnson, *Computers and Intractability: A Guide to the Theory
of NP-Completeness*, W. H. Freeman, 1979 — proved **strongly NP-complete**.

> **Citation caveat.** The epic draft attributed this to "Garey–Johnson, JACM 1978."
> No 1978 JACM primary was confirmed; the reliable primary is the 1979 book [SP17].
> Cited as the book here, honestly, per the epic's "verified citation before writeup".

## QUBO map
Assignment variables `z_{i,j} ∈ {0,1}` (`x_i` paired with `y_j`), variable index
`i·n + j`:
- Row one-hot `(Σ_j z_{i,j} − 1)²` and column one-hot `(Σ_i z_{i,j} − 1)²` enforce a
  permutation.
- Target penalty `Σ_i (Σ_j z_{i,j}(x_i + y_j) − T_i)²` — **the number-partitioning
  sum-to-target penalty form**, re-implemented self-contained (OQ-1; no import from
  `number-partitioning/`).

`n²` logical variables, degree 2, no ancillas. Used for the fault-tolerant resource
estimate and the deferred hardware appendix only — the headline is the query count.
