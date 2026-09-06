# P1 — Betweenness

## Formal definition
Given a finite set and a collection of ordered triples `(a, b, c)`, each read as the
constraint "**b lies strictly between a and c**": is there a total order (linear
arrangement) of the elements satisfying every triple? `b` is between `a` and `c` iff
`pos(a) < pos(b) < pos(c)` or `pos(c) < pos(b) < pos(a)`.

- **Certificate:** a total order → **ordering** search space, `|S| = n!`.
- **Feasibility optimum:** `cost(order) = #{ violated triples }`, minimum `0`.
- Instances are generated from a **planted order π\*** (only π\*-satisfied triples are
  kept), so a satisfying order always exists.

## Citation (AC-T1.8)
J. Opatrný, "Total Ordering Problem", *SIAM Journal on Computing* 8(1):111–114, 1979
— proves the betweenness/total-ordering problem NP-complete.

## QUBO map
One-hot position variables `x_{e,p} ∈ {0,1}` (element `e` at position `p`), index
`e·n + p`: row/column one-hot penalties enforce a permutation, plus a per-triple
degree-2 coupling on the middle element vs its endpoints. `n²` variables, degree 2,
no ancillas. Resource estimate / hardware appendix only.
