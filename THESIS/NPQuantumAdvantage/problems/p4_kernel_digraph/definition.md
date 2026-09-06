# P4 — Kernel of a Digraph (the star)

## Formal definition
Given a directed graph `D = (V, A)`, a **kernel** is a set `S ⊆ V` that is both:
- **independent** — no arc between two vertices of `S`, and
- **absorbing / dominating** — every vertex `w ∉ S` has an arc `w → s` into some
  `s ∈ S`.

Decision: does `D` have a kernel? The certificate is a subset, so this is a
**subset-search** problem with feasible space `2^n`; Grover costs `2^{n/2}`.

- **Certificate:** a subset `S` → subset search, `|S| = 2^n`.
- **Feasibility optimum:** `cost(S) = (# intra-S arcs) + (# unabsorbed outside
  vertices)`, minimum `0` (a kernel). Instances are moderate-density random digraphs,
  which usually admit a kernel.

## Citation (AC-T1.8)
V. Chvátal, technical report **CRM-300**, Centre de Recherches Mathématiques, Univ.
de Montréal, **1973** — establishes the NP-completeness of kernel existence. **This is
a technical report, cited as such, not a journal.** Secondary: A. S. Fraenkel,
"Planar kernel and Grundy…", *Discrete Applied Mathematics* 3:257–262, 1981.

## QUBO map
Membership variables `x_v ∈ {0,1}` (index `v`): an independence penalty on each
intra-set arc (quadratic) + a per-vertex absorption bias (linear). Sparse and local —
the **best hardware fit**, which is why the deferred QAOA appendix targets P4.
`n` variables, degree 2, no ancillas.

## Why it is the borderline "star"
The two constraints pull the best-classical exponent in opposite directions:
independence pulls toward `2^{0.288n}` (Fomin–Grandoni–Kratsch independent set →
collapse), domination/absorption toward `2^{0.598n}` (van Rooij–Bodlaender dominating
set → survive). The **measured** exponent of the exact branch-and-reduce solver decides
which side of the √2 line P4 lands on — see `verdict.md`.
