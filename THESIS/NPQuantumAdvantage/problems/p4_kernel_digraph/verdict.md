# P4 — verdict: SURVIVES (borderline) — the star

| | |
|---|---|
| Search space | subset, `2^n` |
| Predicted (epic §6) | **BORDERLINE / UNKNOWN — the star** |
| **Measured** | **SURVIVES by a hair** — best-classical `c ≈ 0.531`, margin `+0.031` above the √2 line |
| Best-known classical | branch-on-vertex exact independent-and-absorbing-set solver (measured base) |
| Hardness assumption | measured — the branch-and-reduce exponent vs the line |

## The hunt (`best_classical.py`)
An exact branch-and-bound over include/exclude, with inclusion allowed only when it
keeps `S` independent (hard constraint) and the objective the number of unabsorbed
outside vertices. Fitting the recursion-node count against `n` (seed 7, n∈{6..14})
gives a base with exponent **c ≈ 0.531**, i.e. `2^{0.531·n}` — just **above** the
Grover exponent `0.5`. `classify_subset(0.531)` returns **SURVIVES**, margin `+0.031`.

OQ-3: a hand-rolled branch-and-reduce is used because no drop-in library exact solver
for the kernel (independent-and-absorbing) set was available; the base is measured
empirically and reported honestly.

## Read this honestly
This is the **borderline star**, and it lands **essentially on the √2 line** (margin
`+0.031`). The result "SURVIVES" is real for this solver at this seed, but the margin
is within the modelling noise of a hand-rolled brancher — the honest headline is
"**Kernel sits on the line**: the independence structure (→0.288) and the domination
structure (→0.598) very nearly cancel." A stronger measure-and-conquer solver, or a
different density/seed, could push it below `0.5`. The map records the measured
SURVIVES with its thin margin and this caveat, rather than overclaiming a clean
survivor — 3-SAT (c = 1.0) remains the clean reference survivor.

## Measured (seed 7, n∈{6..14})
theorem axis classical slope `1.000` (R²=1.0), quantum slope `0.500` (R²=1.0); verdict
axis best-classical `c ≈ 0.531` (margin `+0.031`). A real kernel exists (optimum 0),
and `--statevector` amplifies it to prob ≈ 1.0 vs the `1/2^n` floor.
