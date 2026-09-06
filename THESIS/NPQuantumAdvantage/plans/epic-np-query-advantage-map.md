# Epic: The Quantum Query-Advantage Map — five forgotten NP-complete problems, and the √2 line that decides whether Grover's provable speedup survives the best classical algorithm

**Slug:** np-query-advantage-map
**Tickets:** T0, T1, T2 (3) — merged from the original F0–F8 (9)
**Author:** Claude (Opus) · **Revised:** 2026-09-06 (√2 spine, corrected verdicts, 3-ticket merge)
**Date:** 2026-08-31
**Status:** Approved (revised)
**Project root:** `THESIS/NPQuantumAdvantage/` — plans in `plans/`, shared code in `framework/`,
per-problem code in `problems/p<k>_<name>/`, run/ledger artifacts in `research_runs/`, web
spectacle in `web/`. POC already lives in `proof_of_concept/` (the survives-mechanism, end to end).
**Source idea:** `plans/thesis-4-obscure-np-query-advantage.md`
**POC:** `proof_of_concept/` (3-SAT survives-case, hardware-run on `ibm_kingston`, 51.9% vs 6.2% floor).
The POC is also **the reference survivor** of the map: 3-SAT sits at classical exponent c = 1.0
(SETH), the cleanest point above the √2 line.
**Builds on:** `number-partitioning/` (QUBO/QAOA swapnet, `classical_reference.py`, `research_runs/`)
for the optional hardware appendix; honest successor to `qh-13` (drops its refuted teleport premise).

> No GitHub issues, no test suite — repo directive. "Tickets" T0–T2 are author-defined research
> deliverables. Acceptance criteria are author-defined. Each ticket is picked up with
> `/plan-feature plans/epic-np-query-advantage-map.md` naming the T-id.

---

## 1. Why this epic exists

There is exactly one honest way to say "quantum advantage on an NP-complete problem," and it is a
**theorem, not a benchmark**: Dürr–Høyer minimum-finding on Grover solves the optimization version
of *any* NP-complete problem in Θ(2^{n/2}) cost-oracle calls, and BBBV (1997) proves that quadratic
speedup is **optimal in the query model** — unconditional, independent of P vs NP. That part is
undeniable. Dürr–Høyer is also the *only* mainstream quantum-optimization method with a **provable**
query speedup (unlike QAOA / annealing, which have none). The catch that turns it into research: the
quadratic speedup only beats the *best known classical algorithm* when the best known classical
algorithm is **itself brute force**.

### The result, compressed to one inequality — the √2 line

Write every classical cost as `2^{c·n}` (c = the exponent per input bit). Grover / Dürr–Høyer over a
2^n subset-search space costs `2^{0.5·n}`, so its exponent is fixed at **c_Q = 0.5** (base
`2^{0.5} = √2 ≈ 1.414`). Therefore:

> **A problem SURVIVES ⟺ its best-known-classical exponent c > 0.5 (base > √2).
> It COLLAPSES ⟺ c ≤ 0.5 (a known classical algorithm already runs at or below `2^{n/2}`).**

That single line **is** the thesis, and it is the single figure: one axis (the classical exponent c),
one vertical threshold at 0.5, one dot per problem. Above the line the provable quantum query
advantage is real *over the best known method*; below it, it is erased. No table required to read the
result — the reader sees it in one glance.

### The novel, surprising headline: survival is the exception, not the rule

Naively one expects "some survive, some collapse." The corrected analysis (see §6) says something
sharper and more publishable: **for structured NP-complete problems, Grover advantage almost never
survives**, and it fails for three *distinct, classifiable* reasons. That rarity — and its mechanism
taxonomy — is the contribution. A uniform "all five show quantum advantage" would be a red flag and
an overclaim; the honest map (one reference survivor, one borderline case, and three mechanistically
different collapses) is the defensible, citable result.

### The search-space subtlety the first draft missed (now the spine of §6)

The √2 line above is stated for **subset-search** problems, whose certificate is a subset / bit-string
and whose feasible space is 2^n. Many classic problems are instead **ordering / assignment** problems,
whose certificate is a permutation and whose feasible space is `n!`. For those, Grover costs
`√(n!) = 2^{0.5·n·log₂n}`, which **exceeds 2^n for n > 4** — and every such problem admits a
Bellman–Held–Karp `2^n·poly` DP over subsets. So **ordering/assignment problems collapse structurally
and automatically**: a plain `2^n` classical DP already beats Grover-over-permutations. This single
distinction flips three of the original draft's predicted verdicts (see §6).

User-visible outcome: five problem folders, each with a `classical_bruteforce.py` and a
`quantum_grover.py` that print the oracle-call gap, plus a `best_classical.py` + `verdict.md`; a single
survive/collapse ledger + the √2 map figure; and a **TargetedDos-style web spectacle** that walks a
non-specialist through every problem, recomputes brute-force-vs-Grover call counts live in the browser,
and makes visible *why* quantum wins where it does — and honestly, where it does not.

## 2. Tickets in this epic (merged 9 → 3)

| ID | Title | State | One-line summary |
|----|-------|-------|------------------|
| T0 | Core framework, √2 classifier & the map machinery | open | Shared oracle-call counter, Dürr–Høyer query-count engine, brute-force template, exponent fitter (returns c in `2^{c·n}`), **√2 survive/collapse classifier**, fault-tolerant resource estimator, ledger schema + renderer, the single-axis **√2 map figure**, and the vendored JS mirror + parity assert. Absorbs old F0 + F6. Built once, reused by all five problems. |
| T1 | The five problems + the best-classical hunt | open | All five problems on the T0 template in one build: definition + citation + QUBO map, the two headline files, and `best_classical.py` + `verdict.md` per problem emitting a ledger row tagged with **search-space type** (subset/ordering) and **collapse mechanism**. Absorbs old F1–F5. The optional hardware/QAOA feasibility note (old F7) folds in here as an appendix, obstruction-labelled, deferred. |
| T2 | Web spectacle — the systemic visual | open | TargetedDos-style Next.js static-export app: scenes-in-sequence per problem, brute-force vs Grover call counts recomputed **live in-browser** from the vendored JS mirror, the √2 map scene rendered from the ledger, and the honest "where Grover does NOT win" scene (the three collapse mechanisms + the NISQ/wall-clock caveat). Absorbs old F8. |

> **Why the merge saves credits.** The original F1–F5 were the *identical* templated two-file+verdict
> contract; planning each with its own `/plan-feature` round paid five times for one design. T1 loops
> the five on the T0 template in a single build context. Old F6 ("render the map from the ledger") was
> a few-hundred-line renderer with no separate design — folded into T0. Old F7 (hardware QAOA) is a
> known-negative (QDEP already refuted the teleport-routing advantage; QAOA loses wall-clock on Heron)
> that claim discipline forbids presenting as advantage — demoted from a ticket to a deferred appendix
> inside T1. Net: 9 planning rounds → 3, one hardware submission cycle cut, no per-problem detail lost.

## 3. Cross-cutting decisions

Decisions made once for the whole epic. Every `/plan-feature` output must respect them.

- **THE √2 LINE IS THE SPINE.** Every verdict is `c > 0.5 → SURVIVES`, `c ≤ 0.5 → COLLAPSES`, where c
  is the best-known-classical exponent in `2^{c·n}` and Grover's exponent is the fixed threshold 0.5
  (base √2). The map figure is this axis. State the inequality up front in every writeup; do not bury
  it in a table.
- **SEARCH-SPACE TYPE IS RECORDED PER PROBLEM AND DRIVES THE VERDICT.** Every problem is tagged
  **subset-search** (certificate = subset/bit-string, feasible space ≈ 2^n, Grover = `2^{n/2}`) or
  **ordering/assignment** (certificate = permutation, feasible space = `n!`, Grover = `√(n!)`).
  Ordering/assignment problems collapse structurally whenever a `2^n·poly` Held–Karp/bitmask DP exists
  (essentially always). This tag is a required ledger field.
- **THREE COLLAPSE MECHANISMS — a taxonomy, not a binary.** Each COLLAPSE row must name its mechanism:
  (a) **structural** — a `2^n` Held–Karp/bitmask DP beats Grover-over-permutations (ordering/assignment
  problems); (b) **measure-and-conquer** — a subset problem with best-classical exponent c < 0.5 (e.g.
  independent-set-type at `2^{0.288n}`); (c) **algebraic** — number-theoretic structure gives a
  sub-`2^{n/2}` (often sub-exponential) classical algorithm, and the real quantum win, if any, is Shor,
  not Grover.
- **SURVIVORS ARE STATED CONDITIONAL ON A HARDNESS ASSUMPTION.** A survivor claim ("no classical
  algorithm with c ≤ 0.5 exists") is honest only under an assumption — SETH, the Set-Cover Conjecture,
  or an explicit "best known is `2^n`, none better published." Say which. The POC's 3-SAT is the
  reference survivor: c = 1.0 under SETH, already demonstrated on hardware.
- **CLAIM DISCIPLINE IS LOCKED.** Four qualifiers attach to every advantage statement, no exceptions:
  **query model · over brute force · quadratic · not wall-clock.**
  - CAN say: "BBBV-optimal quadratic quantum *query* speedup over brute force, shown by oracle-count
    on all five" (theorem, always true). "On the problems whose best-known-classical exponent c > 0.5,
    a provable advantage over the *best known* method" (true after the homework). "A √2 map of *where*
    the advantage survives vs collapses, and *why* it usually collapses."
  - CANNOT say: "I ran them on a quantum computer and beat classical" (false on NISQ). "I systematically
    verified quantum advantage" (unqualified → reads as beating best classical everywhere → false).
  - The word "undeniable" maps ONLY to the query-model theorem. The map is what is *novel*; the theorem
    is what is *undeniable*. Do not let T2 or any writeup blur these.
- **Two-file-per-problem contract (the user's core ask).** Every problem folder ships exactly two
  headline runnable files with the SAME names across all five (mirrors the POC):
  - `classical_bruteforce.py` — exhaustive solver/verifier, wraps the shared oracle counter, prints
    call count and its scaling (`2^n` for subset, `n!` for ordering).
  - `quantum_grover.py` — Dürr–Høyer/Grover-minimum, wraps the shared oracle counter, prints call
    count (`~1.3·2^{n/2}` subset, `~1.3·√(n!)` ordering), the speedup factor over *its own* brute
    force, and (Aer arm) amplifies the marked/optimal state above the floor. Runnable on Aer sim and,
    via `--backend`, on real IBM hardware (feasibility only).
  - `best_classical.py` (+ `verdict.md`) is the *hunt*: implements/benchmarks the best-known classical
    exponential algorithm, fits its exponent c, and emits the survive/collapse verdict row (with
    search-space type + mechanism). This is where "try to find a classical solution that beats the
    quantum" lives, per problem.
- **Query-count is the primary quantum measurement, NOT statevector.** `quantum_grover.py` demonstrates
  the theorem by *counting* Dürr–Høyer's expected oracle calls over an ideal Grover subroutine — no
  2^n-amplitude simulation needed for the scaling claim. A small-n (n ≤ ~14) real statevector/Aer
  Grover run is included as a *validation + amplification demo* (and the hardware hook), not the
  scaling evidence. (This is exactly the `MINIMAL.md` query-count pipeline — reuse it in T0.)
- **The ledger is the single source of truth.** One machine-readable file (`research_runs/ledger.json`
  + rendered `ledger.md`) with one row per problem: name, 1970s citation, search-space type, fitted
  classical exponent c, fitted quantum exponent (≈0.5), best-known-classical exponent + its source,
  verdict ∈ {SURVIVES, COLLAPSES, UNKNOWN}, collapse mechanism (if any), fault-tolerant qubit/T-count.
  T0 renders the map from this file; T2 reads it. No verdict lives anywhere else.
- **Systemic, not five one-offs.** All five share ONE framework (T0). Adding problem N+1 = write its
  instance generator + cost oracle + QUBO map + best-classical analysis, inherit everything else. The
  uniform theorem machinery isolates the only variable that matters: the classical exponent c.
- **Instance generators are fixed-seed and CLI-parametrized** (`n`, seed). Default small so the
  brute-force optimum is computable and the demo is cheap; exposed so sweeps scale without a rewrite.
- **Hardware runs are manual and deferred to an appendix** (same workflow as number-partitioning /
  QuantumLife): code emits circuits + harness, the user submits by hand, run JSONs land in
  `research_runs/`. Record live calibration (2q err, readout err) per run. No automated submission. The
  headline needs zero QC.
- **Web spectacle is first-class (T2), TargetedDos style.** Next.js App Router + TypeScript + Tailwind
  v4, `output: 'export'` → static `web/out/` (no server runtime, GitHub-Pages/offline runnable). The
  browser recomputes brute-force vs Grover call counts from a **vendored JS mirror of T0's counter**
  (build-time parity assert against the Python source of truth — the TargetedDos D-parity discipline),
  so the demo is a reproducibility artefact, not a hype page.

## 4. Shared data model / artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| `framework/oracle.py` — call-counting oracle wrapper (decorator + tally) | T0 | T1 (both files each) |
| `framework/grover_min.py` — ideal Dürr–Høyer query-count engine (`~1.3·2^{n/2}` / `~1.3·√(n!)`) | T0 | T1 `quantum_grover.py` |
| `framework/bruteforce.py` — generic exhaustive-search template | T0 | T1 `classical_bruteforce.py` |
| `framework/fit.py` — exponent fitter, returns c in `2^{c·n}` (subset) or slope on the right axis (ordering) + R² | T0 | T1, map |
| `framework/classify.py` — the √2 classifier: given c, return SURVIVES/COLLAPSES + margin to 0.5 | T0 | T1 verdicts, map |
| `framework/resources.py` — fault-tolerant qubit/T-count estimator | T0 | T1, map |
| `framework/ledger.py` — ledger schema (incl. search-space type + mechanism) + append/render | T0 | T1 (append), map + T2 (read) |
| `framework/map_figure.py` — renders the single-axis √2 map + exponent table from the ledger | T0 | thesis figure, T2 |
| Per-problem instance generator / cost oracle / QUBO map | T1 | that problem's files, hardware appendix |
| Per-problem `verdict.md` + ledger row | T1 | the map |
| `research_runs/ledger.json` (+ `ledger.md`) — the map's data | T0 schema, T1 rows | map figure, T2 scenes |
| Vendored `web/lib/grover_count.js` — JS mirror of T0's counter (parity-asserted) | T0 → T2 | T2 browser scenes |

## 5. Metrics / what "advantage" means

- **Fitted oracle-call exponent vs n** — for subset problems classical c ≈ 1.0, quantum c ≈ 0.5 on a
  log2 axis. This is the theorem, demonstrated identically for all five. (Primary, query-model,
  deterministic.)
- **Best-known-classical exponent c** — *the number the whole map turns on.* Survive if c > 0.5,
  collapse if c ≤ 0.5. For ordering problems, compare Grover's `√(n!)` against the `2^n` DP directly.
- **Survive/collapse verdict + mechanism per problem** — {SURVIVES, COLLAPSES, UNKNOWN} with the
  collapse mechanism (structural / measure-and-conquer / algebraic). The headline figure is the √2 line.
- **Fault-tolerant resource estimate** — logical qubits + T-count per problem (honest cost of the
  advantage; makes explicit it is not a NISQ wall-clock claim).
- **(Appendix, feasibility only)** QAOA approximation ratio vs a matched classical local baseline —
  reported as feasibility + locality obstruction, never as advantage.

## 6. The five problems — corrected verdicts

The reference survivor is the POC's **3-SAT** (subset-search, c = 1.0 under SETH — cleanest point above
the line, already on hardware). Against it, the five obscure 1970s problems map as follows. **Verdicts
are predictions to be confirmed by each `best_classical.py`, not pre-committed** — but the search-space
analysis makes the expected outcome clear, and it corrects three predictions from the first draft.

| # | Problem (1970s cite) | Search-space | Grover cost | Best-known classical | Expected verdict | Mechanism |
|---|----------------------|--------------|-------------|----------------------|------------------|-----------|
| P1 | Betweenness (Opatrný 1979) | ordering (`n!`) | `√(n!)` | `2^n` Held–Karp subset-DP | **COLLAPSES** (was "SURVIVES") | structural |
| P2 | Numerical Matching w/ Target Sums (Garey–Johnson, JACM 1978) | assignment (`n!`) | `√(n!)` | `2^n·n` bitmask assignment DP | **COLLAPSES** (was "strongest SURVIVES") | structural |
| P3 | Quadratic Congruences (Manders–Adleman 1978) | subset (`x<c`, 2^n) | `2^{n/2}` | factor b + Tonelli–Shanks + CRT → sub-exp (c ≪ 0.5) | **COLLAPSES** ✓ | algebraic (real quantum win = Shor, not Grover) |
| P4 | Kernel of a Digraph (Chvátal 1973 TR; Fraenkel 1981) | **subset (2^n)** | `2^{n/2}` | independent+absorbing: indep-set pulls c→0.288 (collapse), dominating pulls c→0.598 (survive) | **BORDERLINE / UNKNOWN — the star** | possibly none |
| P5 | MinLA (Garey–Johnson–Stockmeyer 1976) | ordering (`n!`) | `√(n!)` | `O*(2^n)` Bellman–Held–Karp DP | **COLLAPSES** ✓ | structural |

Cited classical exponents anchoring the analysis: independent set `2^{0.288n}` (Fomin–Grandoni–Kratsch),
dominating set `2^{0.598n}` (van Rooij–Bodlaender), MinLA `O*(2^n)` Held–Karp. Grover subset threshold
`2^{0.5n}`.

**Reading of the map (the honest headline):** one reference survivor (3-SAT, c=1.0), one genuine
borderline case worth real work (**P4 Kernel** — its verdict depends on whether the independence or the
domination constraint dominates the exponent, near the √2 line), and **four collapses across all three
mechanisms**. The map has teeth on both sides of the line, and its shape *is* the result: **Grover
advantage is rare among structured NP-complete problems, and here is exactly why, mechanism by
mechanism.** If a `best_classical.py` hunt overturns a predicted collapse (e.g. finds no `2^n` DP for a
constrained variant), that flips the row to SURVIVES — welcome, and recorded.

> **Optional survivor-side reinforcement (stretch, not required):** if the borderline P4 lands on the
> collapse side, the map still has 3-SAT as its survivor, but a second clean survivor strengthens it.
> Candidate obscure subset-search problems with a plausible c > 0.5 hardness anchor (Set-Cover
> Conjecture / SETH) may be added as a P6 — only with a verified 1970s citation. Do not swap out a
> locked, cited problem for an unverified one.

## 7. Implementation order

1. **T0 first** — nothing else can start without the shared harness (oracle counter, DH engine,
   brute-force template, fitter, √2 classifier, ledger schema, resource estimator, map renderer, JS
   mirror). It fixes the parity contract early and renders the map from a stubbed/partial ledger.
2. **T1 next** — build the framework-validation problem first (**P4 Kernel**, the subset-search star,
   or P2 as the cheapest to wire via the number-partitioning penalty), shake out T0 end to end, then
   loop the remaining four on the template. Each appends its verdict row. The hardware appendix is
   scaffolded but its QC submission is deferred.
3. **T2 after T0 (JS mirror + ledger schema) + at least one T1 verdict row** — the spectacle scaffold
   and one real scene can be built early; remaining scenes fill in as verdict rows land. Reads the
   ledger, so it auto-updates. The √2 map scene and the "where Grover does NOT win" honesty scene are
   first-class, not supplementary.

## 8. Open questions — RESOLVED

- [x] **Q1 — Project layout.** Root `THESIS/NPQuantumAdvantage/` with `framework/`,
  `problems/p<k>_<name>/`, `research_runs/`, `web/`; POC left in place. **Confirmed.**
- [x] **Q2 — The five problems.** Locked: P1 Betweenness · P2 Numerical Matching · P3 Quadratic
  Congruences · P4 Kernel of a Digraph · P5 MinLA. **Kept** (cited, approval-locked). Verdicts
  **corrected** per §6; predictions are not pre-committed — `best_classical.py` decides.
- [x] **Q3 — Best-classical hunt bar.** **Tier (b) for all five** — implement + benchmark the
  best-known classical exponential algorithm and fit its exponent c; classify against 0.5.
- [x] **Q4 — `quantum_grover.py` scope.** **Both** — query-count accounting for the scaling claim +
  a small-n statevector/Aer Grover amplification demo (and hardware hook), matching the POC.
- [x] **Q5 — Hardware arm.** **Demoted to a deferred appendix inside T1** (was standalone F7). Scaffold
  only; QC submission deferred until the map is done. Headline needs zero QC. QDEP already showed the
  advantage does not survive on Heron — it is the obstruction result, not a hole.
- [x] **Q6 — Deliverable.** **Both** — T2 web spectacle is the primary public artefact, IEEE 6–8pp
  short paper is the thesis document, and the √2 map is its single figure.
- [x] **Q7 — Web spectacle stack.** **Mirror TargetedDos exactly** — Next 16 + React 19 + Tailwind v4,
  static export, vendored parity JS.
- [x] **Q8 — Ticket count.** **Merged 9 → 3** (T0 Core, T1 Problems, T2 Web) to save planning rounds;
  old F6 folded into T0, old F7 folded into T1 as a deferred appendix. **Confirmed.**

## 9. Per-ticket briefs

### T0 — Core framework, √2 classifier & the map machinery (absorbs old F0 + F6)

- **What it delivers:** The shared, reused-by-all-five machinery + the map figure. This is what makes
  the study *systemic* rather than five disconnected scripts, and it renders the single thesis figure.
  T0 owns **all math and I/O contracts**; T1 problems only supply an instance generator + cost oracle +
  QUBO map and inherit everything below.

- **The two axes T0 must keep distinct (this is the crux — the vague draft conflated them):**
  1. **Theorem axis (universal, always demonstrated).** Plot `log2(oracle_calls)` against
     `log2(|S|)`, where `|S|` is the *feasible search-space size* (`2^n` for subset problems, `n!` for
     ordering/assignment problems). The slope is **1.0 for classical brute force, 0.5 for Grover /
     Dürr–Høyer — for every problem regardless of type.** This is the quadratic query speedup, proven
     by counting. `fit.py` returns this slope as the primary number.
  2. **Verdict axis (the √2 line, decides survive/collapse).** Compare the quantum cost against the
     *best-known-classical* cost, both as functions of the **input size n**. For **subset** problems
     both are `2^{c·n}`: quantum `c_Q = 0.5`, classical `c_cl`; **SURVIVE ⟺ c_cl > 0.5**. For
     **ordering** problems the quantum cost is `√(n!) = 2^{0.5·log2(n!)}` (its n-exponent
     `0.5·log2(n!)/n ≈ 0.5·log2 n` *grows*), while the best classical is typically a `2^n` Held–Karp DP
     (n-exponent 1.0, constant); the classical curve is asymptotically below the quantum one, so
     ordering problems **COLLAPSE whenever any `2^{O(n)}` classical algorithm exists** — they SURVIVE
     only if the best known classical is itself `Θ(n!)` (no sub-factorial algorithm), which for these
     problems is not the case. `classify.py` implements both branches.

- **Acceptance criteria (with the exact contract each file must expose):**

  - **AC-T0.1 `framework/oracle.py` — the single call counter.**
    - `class OracleCounter` with `.count: int`, `.reset() -> None`, and
      `.wrap(fn: Callable[..., T]) -> Callable[..., T]` that returns a wrapper incrementing `.count` on
      every call and forwarding args/result unchanged.
    - Also a `@counted(counter)` decorator form for module-level oracles.
    - Contract: exactly one increment per cost/verifier evaluation; both files of every problem share
      one `OracleCounter` instance per run; `.reset()` zeroes it between `n` points in a sweep.

  - **AC-T0.2 `framework/grover_min.py` — ideal query-count engine (no statevector).**
    - `search_space_size(n: int, kind: Literal["subset","ordering"]) -> int` → `2**n` or `factorial(n)`.
    - `grover_iterations(N: int, M: int) -> int` → the exact optimal Grover count
      `k = floor((pi/4) * sqrt(N / max(M, 1)))`, returned as `max(k, 1)` for `M ≥ 1`, `0` for `M == 0`.
      One iteration = one oracle call.
    - `durr_hoyer_expected_queries(N: int, *, c_dh: float = 1.3) -> float` → expected total oracle
      calls for quantum **minimum-finding** over `N` items, modelled as `c_dh * sqrt(N)`. **Document
      explicitly:** Dürr–Høyer (1996) prove an upper bound `≤ 22.5·√N`; the `1.3` default is the
      illustrative practical constant matching the POC. **Only the exponent (0.5) is the scientific
      claim; `c_dh` shifts the intercept, never the slope.** Expose `c_dh` so the intercept is not
      mistaken for a result.
    - `expected_queries(n, kind, marked=1, mode=Literal["search","min"]) -> float` → the single entry
      point every `quantum_grover.py` calls; dispatches to `grover_iterations` (search) or
      `durr_hoyer_expected_queries` (min) over `search_space_size(n, kind)`.

  - **AC-T0.3 `framework/bruteforce.py` — generic exhaustive template.**
    - `brute_force_min(candidates: Iterable[C], cost: Callable[[C], float], counter: OracleCounter)
      -> tuple[C, float, int]` → returns `(argmin, min_cost, counter.count)`, calling `cost` through
      the counter for every candidate.
    - `enumerate_space(n, kind)` helper → yields all `2^n` bitstrings (subset) or all `n!` permutations
      (ordering). Classical call count must equal `|S|` exactly (the `log2` intercept the theorem axis
      relies on).

  - **AC-T0.4 `framework/fit.py` — the exponent fitter (both axes).**
    - `fit(ns: list[int], calls: list[float], space_sizes: list[int]) -> FitResult`.
    - `FitResult` (dataclass) fields: `slope_vs_logspace: float` (least-squares slope of
      `log2(calls)` vs `log2(|S|)` — the **theorem-axis** number, expect ≈1.0 classical / ≈0.5
      quantum), `r2_vs_logspace: float`, `exponent_in_n: float` (slope of `log2(calls)` vs `n` — the
      **verdict-axis** `c` in `2^{c·n}`; a clean constant for subset problems, and for ordering
      problems a *diagnostic only*, since the true n-exponent grows), `r2_in_n: float`.
    - Must warn (not silently) when `kind == "ordering"` and `exponent_in_n` is read as a constant.

  - **AC-T0.5 `framework/classify.py` — the √2 classifier (two branches).**
    - `classify_subset(c_classical: float, *, eps: float = 1e-6) -> Verdict` → `SURVIVES` if
      `c_classical > 0.5 + eps`, `COLLAPSES` if `c_classical < 0.5 - eps`, else `UNKNOWN`.
    - `classify_ordering(has_subexp_classical: bool, classical_n_exponent: float | None) -> Verdict`
      → `COLLAPSES` if a `2^{O(n)}` classical algorithm exists (`has_subexp_classical` True — i.e. any
      Held–Karp/bitmask DP), else `UNKNOWN`/`SURVIVES` only if best known is `Θ(n!)`. Documents that
      `√(n!)` is asymptotically above `2^{c·n}` for any finite `c`.
    - `Verdict` = `Enum{SURVIVES, COLLAPSES, UNKNOWN}`. Both functions also return
      `margin_to_line: float` (`c_classical − 0.5` for subset; `None`/annotated for ordering) and a
      `mechanism: Literal["structural","measure-and-conquer","algebraic"] | None` slot the caller fills.

  - **AC-T0.6 `framework/resources.py` — fault-tolerant estimator (documented formula).**
    - `estimate_grover_resources(oracle_qubits: int, oracle_toffoli_count: int, queries: float,
      ancillas: int = 0) -> Resources`.
    - Formula (state it in the docstring): `logical_qubits = oracle_qubits + ancillas + 1` (phase
      workspace); `toffoli_total = queries * oracle_toffoli_count`; `t_count ≈ 7 * toffoli_total`
      (7 T-gates per Toffoli, standard). Report `t_count` as an order of magnitude (e.g. `"~1e6"`).
    - `quadratization_ancillas(hubo_degree: int, n_terms: int) -> int` helper for HUBO→QUBO overhead
      (P3), documented as the extra qubit cost the algebraic-collapse case pays even in the FT model.

  - **AC-T0.7 `framework/ledger.py` — the single source of truth (exact schema).**
    - `append_row(row: LedgerRow, path="research_runs/ledger.json") -> None` (idempotent on `id` —
      re-appending the same `id` overwrites, so re-runs don't duplicate), `load(path) -> Ledger`,
      `render_markdown(ledger) -> str` → `research_runs/ledger.md`.
    - **`ledger.json` schema (version 1) — every field required unless marked optional:**
      ```json
      {
        "schema_version": 1,
        "grover_exponent": 0.5,
        "threshold": 0.5,
        "rows": [{
          "id": "p4_kernel_digraph",
          "name": "Kernel of a Digraph",
          "citation": "Chvátal, CRM-300 tech report, Univ. Montréal, 1973",
          "search_space": "subset",                    // "subset" | "ordering"
          "search_space_size_expr": "2^n",             // human string: "2^n" | "n!"
          "classical_bruteforce_exponent": 1.0,        // theorem-axis slope, classical
          "quantum_exponent": 0.5,                     // theorem-axis slope, quantum
          "best_classical_exponent": 0.598,            // verdict-axis c (subset); null for ordering
          "best_classical_source": "van Rooij–Bodlaender 2011 (dominating set 2^{0.598n})",
          "verdict": "SURVIVES",                       // SURVIVES | COLLAPSES | UNKNOWN
          "margin_to_line": 0.098,                     // best_classical_exponent - 0.5 (subset); null ordering
          "collapse_mechanism": null,                  // null | structural | measure-and-conquer | algebraic
          "hardness_assumption": "measure-and-conquer upper bound",  // or "SETH" | "Set-Cover Conjecture" | "none"
          "ft_logical_qubits": 42,
          "ft_t_count_order": "~1e6",
          "instance_seed": 7,
          "n_swept": [6, 8, 10, 12, 14],
          "fit_r2_classical": 0.999,
          "fit_r2_quantum": 0.999,
          "notes": "borderline: independence constraint pulls c toward 0.288"   // optional
        }]
      }
      ```
    - A `validate(ledger)` that fails loudly if a row has `verdict != UNKNOWN` with a missing
      `best_classical_exponent` (subset) or missing `collapse_mechanism` on a `COLLAPSES` row.

  - **AC-T0.8 `framework/map_figure.py` — the single thesis figure (from the ledger only).**
    - `render(ledger_path, out="research_runs/map") -> None` → writes `map.png` **and** `map.svg`.
    - Layout: **subset problems** plotted on the primary horizontal axis = `best_classical_exponent`,
      with a bold vertical threshold at `0.5` (labelled "√2 line — Grover exponent"); one dot per
      problem, coloured by verdict (survive above/right, collapse below/left), the **3-SAT reference
      survivor** pinned at `c = 1.0`. **Ordering problems** shown in a separate labelled band
      ("ordering — collapses via 2^n Held–Karp DP") annotated with the `√(n!)` vs `2^n` crossover,
      since a fixed-`c` axis is not meaningful for them.
    - Must run against a **partial/stubbed ledger** (missing rows render as greyed "pending") so the
      figure exists from day one.

  - **AC-T0.9 `web/lib/grover_count.js` + parity harness — reproducibility contract.**
    - `grover_count.js` exports `searchSpaceSize(n, kind)`, `groverIterations(N, M)`, and
      `expectedQueries(n, kind, marked, mode)` — byte-for-byte the same integer/float logic as T0.2.
    - `tools/parity_check.py` dumps Python values for a fixed vector of
      `(n ∈ {4..14}) × (kind ∈ {subset, ordering}) × (marked ∈ {1, 2, 4})` to JSON; a Node runner
      computes the JS values; the harness asserts **identical integers** for iteration counts and
      floats within `1e-9` for expected-query counts. Runs at web build time (fails the build on
      mismatch — the TargetedDos D-parity discipline).

  - **AC-T0.10 A `framework/` smoke run** (`python -m framework.selftest`) that, on a trivial built-in
    subset oracle, sweeps `n ∈ {4..14}`, and asserts `fit().slope_vs_logspace ≈ 1.0` (classical) and
    `≈ 0.5` (quantum) with `R² > 0.99` — proving the theorem machinery before any real problem lands.
    (This is the `MINIMAL.md` pipeline, promoted into the framework as its self-test.)

- **Likely files / areas affected:** new `framework/` (`oracle.py`, `grover_min.py`, `bruteforce.py`,
  `fit.py`, `classify.py`, `resources.py`, `ledger.py`, `map_figure.py`, `selftest.py`);
  `research_runs/ledger.json` + `ledger.md` + `map.{png,svg}`; `web/lib/grover_count.js`;
  `tools/parity_check.py`.
- **Depends on:** none.
- **Conventions to follow:** mirror the POC's `classical_bruteforce.py` / `quantum_grover.py` output
  style (search space, marked states, call counts, speedup factor); ledger + parity discipline mirror
  TargetedDos P2's shared-vector parity. Deps: `numpy` for the fit, `matplotlib` for the figure, no
  Qiskit in T0 (query-count only).
- **Out of scope:** any specific problem's oracle or QUBO (those live in T1); full statevector Grover
  (problems opt into small-n statevector themselves).

### T1 — The five problems + the best-classical hunt (absorbs old F1–F5, and F7 as a deferred appendix)

- **What it delivers:** All five problems end to end on the T0 template — each a definition + verified
  citation + QUBO map, the two headline files, and the `best_classical.py` + `verdict.md` hunt that fits
  `c` and emits one ledger row. Build the framework-validation problem first (P4 Kernel — the clean
  subset shape — or P2 — cheapest to wire), then loop the rest.

- **Exact per-problem directory (identical across all five, `<k>`/`<name>` from §6):**
  ```
  problems/p<k>_<name>/
    __init__.py
    instance.py            # generator + cost oracle + QUBO/HUBO map (the ONLY new math)
    classical_bruteforce.py
    quantum_grover.py
    best_classical.py      # the hunt → fits c → emits the ledger row
    verdict.md             # expected vs measured verdict + the hunt writeup
    definition.md          # formal def, verified 1970s citation, QUBO map
  ```

- **Exact contract each `instance.py` must expose (the only per-problem code):**
  - `KIND: Literal["subset","ordering"]` and `SEARCH_SPACE_EXPR: str` (`"2^n"` / `"n!"`).
  - `generate(n: int, seed: int) -> Instance` — deterministic fixed-seed instance.
  - `cost(candidate, instance) -> float` — the objective/violation count; **wrapped in T0's
    `OracleCounter` by the callers, never counting itself**. Lower = better; optimum = 0 for feasibility
    problems.
  - `enumerate(n)` — yields the candidate space (delegates to `framework.bruteforce.enumerate_space`).
  - `to_qubo(instance) -> QUBO` (or `to_hubo` + degree for P3) — the Ising/QUBO map for the hardware
    appendix and `resources.py`; returns the coefficient dict + variable count + any ancilla count.

- **Exact behaviour of the three shared driver files (they are ~identical across problems; differ only
  by importing their `instance.py`):**
  - `classical_bruteforce.py` → calls `framework.bruteforce.brute_force_min(instance.enumerate(n),
    instance.cost, counter)`; prints optimum, `counter.count`, and the scaling label. Call count must
    equal `|S|` exactly.
  - `quantum_grover.py` → calls `framework.grover_min.expected_queries(n, instance.KIND, marked, "min")`
    for the scaling claim; prints the query count, the speedup factor over its own brute force, and the
    `fit.py` slope; `--statevector` runs a real small-n (n ≤ 14) Aer/Grover amplification demo above the
    `1/|S|` floor; `--backend <name>` is the manual hardware feasibility hook (feasibility only).
  - `best_classical.py` → implements the best-known classical algorithm (below), sweeps `n`, fits its
    exponent with `fit.py`, calls `classify.py`, and emits the row via
    `framework.ledger.append_row(LedgerRow(id=..., search_space=instance.KIND, best_classical_exponent=c,
    verdict=..., collapse_mechanism=..., hardness_assumption=..., ...))`.

- **Per-problem specifics — the map (§6) and the exact hunt each `best_classical.py` implements:**
  - **P1 Betweenness** (`p1_betweenness`, ordering) — QUBO: one-hot position vars `x_{i,p}`, per-triple
    degree-2 reward on the induced-order sign + permutation penalties. **Hunt:** the `2^n·poly` subset-DP
    over the set of already-placed elements (state = placed subset, transition = append next element,
    score satisfied triples). Existence of this DP ⇒ `classify_ordering(has_subexp_classical=True)` ⇒
    **COLLAPSE (structural).**
  - **P2 Numerical Matching** (`p2_numerical_matching`, assignment) — QUBO: assignment vars + per-target
    sum-to-target penalty `(Σ s·x − B)²`, **the number-partitioning penalty reused verbatim**. **Hunt:**
    the `O(2^n·n)` bitmask assignment DP (state = subset of Y used, iterate X in order). ⇒ **COLLAPSE
    (structural).** Cheapest to wire → good framework-validation candidate.
  - **P3 Quadratic Congruences** (`p3_quadratic_congruences`, subset over bits of x) — HUBO: binary-
    expand x; penalty `(x² − a − b·t)²`, quartic ⇒ needs quadratization ancillas (`resources.py`
    `quadratization_ancillas`). **Hunt:** factor `b` (Pollard/quadratic-sieve for the small `b` used) →
    Tonelli–Shanks per prime power → CRT combine; sub-exponential, `c ≪ 0.5` ⇒ **COLLAPSE (algebraic).**
    Note in `verdict.md`: the real quantum win here is **Shor**, not Grover — the "where Grover does not
    win" exemplar.
  - **P4 Kernel of a Digraph** (`p4_kernel_digraph`, **subset**) — QUBO: membership vars, independence
    penalty on intra-set arcs + per-vertex absorption penalty; sparse/local (best hardware fit). **Hunt:**
    a measure-and-conquer / branch-on-vertex exact algorithm for the independent-**and**-absorbing set;
    fit its base and test against √2. **The star / borderline case** — independence structure pulls the
    exponent toward `0.288` (collapse), the domination/absorption constraint toward `0.598` (survive);
    the measured `c` decides. Record `hardness_assumption` honestly.
  - **P5 MinLA** (`p5_minla`, ordering) — QUBO: one-hot positions (shared encoding with P1), tabulated
    `|p−q|` edge couplings. **Hunt:** the `O*(2^n)` Bellman–Held–Karp DP (state = placed prefix subset,
    cost = accumulated stretched edges). ⇒ **COLLAPSE (structural).**

- **Deferred hardware appendix (old F7, obstruction-labelled, NOT a headline):** `problems/_hardware/`
  converts one problem's `to_qubo` (start with P4, sparse/local) to an Ising QAOA circuit on the
  `number-partitioning/` swapnet; runs fixed-depth QAOA on **noiseless Aer** (sign/correctness gate) and
  reports approximation ratio vs a matched classical local/greedy baseline; optional manual Heron run
  with calibration (2q err, readout err) in the run JSON, **expected to lose wall-clock** (readout-error
  obstruction, per QDEP). Every output labelled feasibility/obstruction, cites Farhi–Gamarnik–Gutmann
  2020, **never** the advantage. QC submission deferred until the map (T0 figure) is done.

- **Likely files / areas affected:** the five `problems/p<k>_<name>/` dirs; `problems/_hardware/`;
  appends `research_runs/ledger.json`; imports the `number-partitioning/` penalty (P2) and swapnet
  (appendix).
- **Depends on:** T0 (every math/I/O contract).
- **Conventions to follow:** T0 framework for all shared files; POC output style; **verified citation
  before writeup** (P4's Chvátal 1973 is a tech report — cite carefully, not as a journal); reuse the
  number-partitioning sum-to-target penalty for P2; every `cost` goes through the shared `OracleCounter`.
- **Out of scope:** the map figure itself (T0 renders it); the web spectacle (T2); automated QC
  submission; inventing a sub-`2^{n/2}` algorithm (tier-c, opportunistic only — the bar is tier-b,
  implement/benchmark the best *known* algorithm).

### T2 — Web spectacle — the systemic visual (absorbs old F8, TargetedDos style)

- **What it delivers:** The primary public artefact: a Next.js static-export app that walks a
  non-specialist through *every* problem, recomputes brute-force vs Grover call counts **live in the
  browser** from the vendored JS mirror, renders the √2 map from the ledger, and makes the honest
  "where Grover does NOT win" case first-class.

- **Exact structure (mirror `TargetedDosColisionsAndRNGAngle/web/`):**
  ```
  web/
    app/page.tsx                 # scene sequencer (scroll/step through the manifest below)
    components/
      CallCountWidget.tsx        # the live 2^n/n! vs Grover widget
      Sqrt2Map.tsx               # the √2 map, rendered from the ledger
      Scene.tsx                  # shared scene shell
    lib/
      grover_count.js            # VENDORED from T0 (AC-T0.9), do not edit here
      ledger.ts                  # typed loader for the copied ledger.json
    public/ledger.json           # build-time copy of research_runs/ledger.json (single source)
    next.config.js               # output: 'export'
  ```

- **Exact scene manifest (AC-T2.2 — "scenes in sequence"):**
  1. **Intro / the theorem** — Grover + Dürr–Høyer quadratic query speedup, BBBV-optimal; the four
     claim-discipline qualifiers on screen (**query model · over brute force · quadratic · not
     wall-clock**); **the √2 line explained** (classical `2^{c·n}` vs Grover `2^{0.5n}`, survive ⟺
     c > 0.5).
  2–6. **One scene per problem P1–P5** — plain-language definition, the concrete instance, its
     **search-space type** (subset `2^n` / ordering `n!`), and a live `CallCountWidget`.
  7. **The √2 map scene** — `Sqrt2Map` (below).
  8. **Honesty scene — "where Grover does NOT win"** — the three collapse mechanisms
     (structural / measure-and-conquer / algebraic, with P3's Shor twist), the NISQ wall-clock caveat,
     the query-model-only scope; the headline **"advantage is the exception, not the rule."** No hype.

- **Acceptance criteria:**
  - AC-T2.1 Next.js App Router + TypeScript + Tailwind v4, `output: 'export'` → static `web/out/` (no
    server runtime; GitHub-Pages/offline runnable), mirroring the TargetedDos web stack.
  - AC-T2.2 The scene sequencer renders the 8-scene manifest above in order.
  - AC-T2.3 `CallCountWidget` — user picks `n` (slider 4–14) and search-space kind; it recomputes
    `searchSpaceSize(n, kind)` (`2^n`/`n!`) vs `expectedQueries(...)` (`~1.3·2^{n/2}` / `~1.3·√(n!)`)
    **in-browser** from `lib/grover_count.js`, showing both counts + the speedup factor. A **build-time
    parity assert** (T0's `tools/parity_check.py` vs the vendored JS) fails the build on mismatch — the
    widget is a reproducibility artefact, not a hype animation.
  - AC-T2.4 `Sqrt2Map` renders from `public/ledger.json`, auto-updating as verdicts land: the single
    horizontal axis (`best_classical_exponent`), the bold `0.5` threshold, one dot per subset problem
    coloured by verdict, the **3-SAT reference survivor** at `c = 1.0`, ordering problems in the separate
    "collapses via 2^n DP" band; each dot tagged SURVIVES/COLLAPSES/UNKNOWN with its `c`. Rows absent
    from the ledger render greyed "pending" (matches T0's `map_figure.py`).
  - AC-T2.5 The honesty scene is first-class (its own full scene, not a footnote), driven by each row's
    `collapse_mechanism` + `hardness_assumption` from the ledger.
  - AC-T2.6 `public/ledger.json` is a build-step copy of `research_runs/ledger.json` — web and paper
    read the **same** data; a build check asserts the copy matches the source hash.
- **Likely files / areas affected:** `web/` (Next app), `web/lib/grover_count.js` (vendored from T0),
  `web/public/ledger.json` (copied from `research_runs/`).
- **Depends on:** T0 (JS mirror + ledger schema + map layout to mirror) and ≥ one T1 verdict row;
  remaining scenes fill in as the rest land.
- **Conventions to follow:** mirror `TargetedDosColisionsAndRNGAngle/web/` exactly — Next static export,
  vendored parity artefact, scenes-in-sequence, first-class not supplementary. Never edit the vendored
  `grover_count.js` by hand — regenerate it from T0.
- **Out of scope:** any live QC call from the browser; presenting the hardware appendix as advantage.
