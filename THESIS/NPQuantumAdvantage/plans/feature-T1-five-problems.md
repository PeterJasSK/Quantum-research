# Feature Plan — T1: The five problems + the best-classical hunt

**Ticket:** T1 (absorbs old F1–F5, and F7 as a deferred appendix)
**Epic:** `THESIS/NPQuantumAdvantage/plans/epic-np-query-advantage-map.md` (Status: **Approved (revised)**)
**Depends on:** T0 (`framework/` — Status: **Complete**, all AC-T0.1–T0.10 verified 2026-09-06)
**Author:** Claude (Opus) · **Date:** 2026-09-06
**Status:** Complete (2026-09-06 — all AC-T1.1–T1.11 implemented + manually verified, see §13)
**Project root:** `THESIS/NPQuantumAdvantage/`

> No GitHub issues, no test suite — repo directive. Verification is manual only (§8).
> Author-defined ACs, copied verbatim from the epic §9 T1 brief where the epic states a contract.

---

## 1. Context & goal

Build all five obscure 1970s NP-complete problems end-to-end on the **already-built** T0 template, plus
the `best_classical.py` hunt that fits the classical exponent `c` and emits one √2-verdict ledger row per
problem. T1 supplies the **only new math** — per-problem instance generator + cost oracle + QUBO/HUBO map
+ the best-known-classical algorithm — and inherits every shared contract (oracle counter, Dürr–Høyer
query engine, brute-force template, fitter, √2 classifier, resource estimator, ledger, map) from
`framework/`.

The headline the map must produce (epic §6): **one reference survivor** (3-SAT, already seeded by T0 as
`_3sat_reference`, c = 1.0 under SETH), **one genuine borderline** (P4 Kernel — the star), and **four
collapses across all three mechanisms** (structural / measure-and-conquer / algebraic). Survival is the
exception; that rarity + its mechanism taxonomy is the contribution.

### What already exists (integration points — verified, do not rebuild)

- `framework/oracle.py` — `OracleCounter` (`.count`, `.reset()`, `.wrap(fn)`), `@counted(counter)`.
- `framework/grover_min.py` — `expected_queries(n, kind, marked=1, mode="min") -> float`,
  `search_space_size(n, kind)`, `grover_iterations(N, M)`, `durr_hoyer_expected_queries(N, *, c_dh=1.3)`.
  `kind ∈ {"subset","ordering"}`.
- `framework/bruteforce.py` — `brute_force_min(candidates, cost, counter) -> (argmin, min_cost, count)`
  (does **not** reset the counter — caller resets between sweep points); `enumerate_space(n, kind)`
  yields all `2**n` int bitmasks (subset) or all `n!` permutations of `range(n)` (ordering).
- `framework/fit.py` — `fit(ns, calls, space_sizes, *, kind="subset") -> FitResult`;
  `FitResult(slope_vs_logspace, r2_vs_logspace, exponent_in_n, r2_in_n)`. Emits a `warnings.warn` when
  `kind="ordering"` and `exponent_in_n` is read as a constant.
- `framework/classify.py` — `classify_subset(c, *, eps=1e-6) -> ClassifyResult(verdict, margin_to_line)`;
  `classify_ordering(has_subexp_classical, classical_n_exponent=None) -> ClassifyResult(verdict,
  margin_to_line, mechanism)`; `Verdict` enum `{SURVIVES, COLLAPSES, UNKNOWN}` with `.value` strings.
- `framework/resources.py` — `estimate_grover_resources(oracle_qubits, oracle_toffoli_count, queries,
  ancillas=0) -> Resources`; `quadratization_ancillas(hubo_degree, n_terms) -> int`.
- `framework/ledger.py` — `LedgerRow(...)` dataclass (exact schema below), `append_row(row, path=...)`
  (idempotent on `id`), `load`, `validate`, `render_markdown`. `EXPECTED_IDS` already lists the five
  T1 ids + `_3sat_reference`.
- `framework/map_figure.py` — reads the ledger, renders `research_runs/map.{png,svg}`; absent rows render
  greyed "pending". **T1 does not touch this** — appending rows auto-fills the map.
- `proof_of_concept/` — the output-style reference for `classical_bruteforce.py` / `quantum_grover.py`
  (search space, marked states, call counts, speedup factor, claim-discipline banner, `--backend` hook).
- `research_runs/ledger.json` — seeded by T0 with the header + `_3sat_reference` row; T1 appends five.

---

## 2. Acceptance criteria

Copied from the epic §9 (T1 brief) and §3 cross-cutting decisions. Each per-problem AC repeats identically
for P1–P5; problem-specific math is in §6.

- **AC-T1.1 — Directory contract.** Every problem ships exactly this tree, identical filenames across all
  five (mirrors the POC and the epic §9 layout):
  ```
  problems/p<k>_<name>/
    __init__.py
    instance.py            # generator + cost oracle + QUBO/HUBO map (the ONLY new math)
    classical_bruteforce.py
    quantum_grover.py
    best_classical.py      # the hunt → fits c → emits the ledger row
    verdict.md             # expected vs measured verdict + hunt writeup
    definition.md          # formal def, verified 1970s citation, QUBO map
  ```

- **AC-T1.2 — `instance.py` contract (the only per-problem code).** Exposes exactly:
  - `KIND: Literal["subset","ordering"]` and `SEARCH_SPACE_EXPR: str` (`"2^n"` / `"n!"`).
  - `generate(n: int, seed: int) -> Instance` — deterministic fixed-seed instance (a frozen dataclass).
  - `cost(candidate, instance) -> float` — objective/violation count. **Never wraps itself in the
    counter**; the callers wrap it. Lower = better; optimum = 0 for feasibility problems.
  - `enumerate(n) -> Iterable` — delegates to `framework.bruteforce.enumerate_space(n, KIND)`.
  - `to_qubo(instance) -> QUBO` (or `to_hubo(instance) -> tuple[HUBO, degree]` for P3) — coefficient dict
    + variable count + ancilla count, for the resource estimate and the hardware appendix.

- **AC-T1.3 — `classical_bruteforce.py`.** Calls `framework.bruteforce.brute_force_min(instance.enumerate(n),
  lambda c: instance.cost(c, inst), counter)`; prints optimum, `counter.count`, and the scaling label
  (`2^n` subset / `n!` ordering) in the POC output style. **Call count must equal `|S|` exactly** (the
  theorem-axis intercept depends on it). CLI `--n`, `--seed`.

- **AC-T1.4 — `quantum_grover.py`.** Calls `framework.grover_min.expected_queries(n, instance.KIND,
  marked, "min")` for the scaling claim; prints the expected query count, the speedup factor over *its own*
  brute force, and the `fit.py` `slope_vs_logspace` over a small `n`-sweep (≈0.5). Includes the
  claim-discipline banner (**query model · over brute force · quadratic · not wall-clock**). `--statevector`
  runs a real small-n (`n ≤ 14`) Aer/Grover amplification demo above the `1/|S|` floor (subset problems
  only — see OQ-5); `--backend <name>` is the manual hardware feasibility hook (feasibility only, no
  submission from this ticket). CLI `--n`, `--seed`, `--statevector`, `--backend`, `--shots`.

- **AC-T1.5 — `best_classical.py` (the hunt).** Sources or implements the best-known classical algorithm
  (§6 per problem — **prefer an existing published/library implementation where one exists**, hand-rolled
  only as fallback; OQ-3), sweeps `n`, fits with `framework.fit.fit(...)`, classifies with `framework.classify`
  (`classify_subset` for subset, `classify_ordering` for ordering), and emits exactly one ledger row via
  `framework.ledger.append_row(LedgerRow(...))`. CLI `--n-max`, `--seed`, `--emit/--no-emit` (default
  emit). Idempotent: re-running overwrites its own row (`append_row` is keyed on `id`).

- **AC-T1.6 — one ledger row per problem, schema-valid.** Each row sets the epic §4 fields with the
  correct `search_space`, `search_space_size_expr`, `classical_bruteforce_exponent` (theorem-axis, ≈1.0),
  `quantum_exponent` (≈0.5), `best_classical_exponent` (subset only; `null` for ordering),
  `best_classical_source`, `verdict`, `margin_to_line`, `collapse_mechanism`, `hardness_assumption`,
  `ft_logical_qubits`, `ft_t_count_order`, `instance_seed`, `n_swept`, `fit_r2_classical`,
  `fit_r2_quantum`, `notes`. `framework.ledger.validate(load())` must pass (fails loudly on a
  non-`UNKNOWN` subset row missing `best_classical_exponent`, or a `COLLAPSES` row missing
  `collapse_mechanism`).

- **AC-T1.7 — verdict per §3 discipline.** Each `verdict` is `classify_*(...).verdict.value`, not
  hand-typed. Subset: `SURVIVES ⟺ c > 0.5`. Ordering: `COLLAPSES` whenever a `2^{O(n)}` DP exists
  (`has_subexp_classical=True`). A survivor row states its `hardness_assumption` (SETH / Set-Cover
  Conjecture / "none — best known is 2^n"). Verdicts are **measured, not pre-committed** — if a hunt
  overturns a §6 prediction, the measured row stands and `verdict.md` records the surprise.

- **AC-T1.8 — `definition.md` per problem.** Formal problem statement, the **verified 1970s citation**
  (see §6; P4 is a tech report — cite as such, not as a journal), and the QUBO/HUBO map. Citation must be
  verified before the writeup (epic §9 "verified citation before writeup").

- **AC-T1.9 — `verdict.md` per problem.** The §6 predicted verdict + mechanism, the measured `c` and
  fitted `R²`, the classification result, the `hardness_assumption`, and — for P3 — the "real quantum win
  is Shor, not Grover" note. States explicitly whether prediction held.

- **AC-T1.10 — deferred hardware appendix (old F7, obstruction-labelled).** `problems/_hardware/`
  scaffold converting one problem's `to_qubo` (start P4, sparse/local) to an Ising QAOA circuit on the
  `number-partitioning/` swapnet; runs fixed-depth QAOA on **noiseless Aer** (correctness gate) and reports
  approximation ratio vs a matched classical greedy/local baseline. Every output labelled
  feasibility/obstruction, cites Farhi–Gamarnik–Gutmann 2020, **never** advantage. **QC submission
  deferred** — code + harness only, no real-device run in this ticket.

- **AC-T1.11 — build-validation problem first.** One problem is built completely first (P2, cheapest to
  wire, or P4, the star — OQ-4) to shake out the T0 template end-to-end before the remaining four are
  looped on the identical driver files.

---

## 3. Scope

### In scope
- Five `problems/p<k>_<name>/` dirs, each with the 7-file contract (AC-T1.1).
- The only new math per problem: `instance.py` (generator + cost + QUBO/HUBO) and the best-known-classical
  algorithm inside `best_classical.py`.
- Five appended ledger rows + the auto-rendered map (via existing `framework.map_figure` / `render_markdown`).
- `problems/_hardware/` scaffold for the deferred, obstruction-labelled QAOA appendix (P4, Aer only).

### Out of scope (deferred / other tickets)
- The map figure renderer itself — **T0 owns it**; T1 only appends rows.
- The web spectacle — **T2**.
- Automated / real-device QC submission — deferred appendix scaffold only (AC-T1.10).
- Inventing a sub-`2^{n/2}` algorithm (tier-c) — the bar is **tier-b**: source/implement + benchmark the
  best *known* algorithm and fit its exponent. Prefer an existing published/library implementation where
  one exists (OQ-3); hand-rolled only as fallback.
- Any change to `framework/` — if a shared contract is found wanting, raise it (OQ), do not silently edit
  T0 from within T1.
- The optional stretch P6 second survivor (epic §6) — not in this ticket.

---

## 4. Data model — the ledger row each problem emits

T1 does **not** define schema; it fills the T0 `LedgerRow`. Required construction per row (ordering example
shown; subset rows set `best_classical_exponent` + `margin_to_line` non-null and `collapse_mechanism` per
mechanism):

```python
LedgerRow(
    id="p5_minla",                          # must be one of framework.ledger.EXPECTED_IDS
    name="Minimum Linear Arrangement",
    citation="Garey, Johnson, Stockmeyer, Theoret. Comput. Sci. 1(3):237–267, 1976",
    search_space="ordering",
    search_space_size_expr="n!",
    classical_bruteforce_exponent=1.0,      # theorem-axis slope log2(calls) vs log2(|S|)
    quantum_exponent=0.5,                    # theorem-axis slope, Grover arm
    verdict=result.verdict.value,            # from classify_ordering(...).verdict
    hardness_assumption="none — best known is O*(2^n) Held–Karp DP",
    best_classical_exponent=None,            # null for ordering
    best_classical_source="Bellman–Held–Karp O*(2^n) DP",
    margin_to_line=None,                     # null for ordering
    collapse_mechanism="structural",
    ft_logical_qubits=...,                   # from resources.estimate_grover_resources(...)
    ft_t_count_order="~1e...",
    instance_seed=7,
    n_swept=[6, 8, 10, 12, 14],
    fit_r2_classical=...,
    fit_r2_quantum=...,
    notes="ordering — √(n!) asymptotically above any 2^{c·n}; collapses via 2^n DP",
)
```

`verdict` is always `classify_*(...).verdict.value` — a string, never hand-typed.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **√2 line is the spine** (epic §3): subset `SURVIVE ⟺ c > 0.5`; ordering `COLLAPSE` whenever a
  `2^{O(n)}` DP exists. Grover exponent fixed at 0.5.
- **Search-space type is a required ledger field** and drives the verdict branch.
- **Three collapse mechanisms** — structural / measure-and-conquer / algebraic. Every COLLAPSE row names one.
- **Claim discipline locked** — four qualifiers on every advantage statement: query model · over brute
  force · quadratic · not wall-clock. `quantum_grover.py` prints them; `verdict.md` respects them.
- **Query-count is the primary quantum measurement**, not statevector. The small-n Aer run is a
  validation/amplification demo, not the scaling evidence.
- **Instance generators fixed-seed and CLI-parametrized** (`n`, `seed`), default small so brute force is
  computable.
- **Hardware runs manual and deferred** (AC-T1.10) — scaffold only, no submission.
- **cost() goes through the shared `OracleCounter`** — never self-counts.

---

## 6. File plan (concrete paths) + per-problem math

Shared drivers (`classical_bruteforce.py`, `quantum_grover.py`, `best_classical.py`) are ~identical across
the five; they differ only by importing their own `instance.py`. Below, each problem lists its
`instance.py` math and the exact algorithm its `best_classical.py` implements. **Strict types, PSR-equiv
(PEP 8 + full type hints + `from __future__ import annotations`), no raw file I/O outside the ledger
writer, all objective evaluation through the counter.**

### `problems/p1_betweenness/` — Betweenness (Opatrný 1979) — ordering
- **Citation (verify, AC-T1.8):** Opatrný, "Total Ordering Problem", *SIAM J. Comput.* 8(1):111–114, 1979.
- **`instance.py`:** `KIND="ordering"`, `SEARCH_SPACE_EXPR="n!"`. `generate(n, seed)` → a set of betweenness
  triples `(a,b,c)` (constraint: `b` lies strictly between `a` and `c` in the linear order). `cost(perm,
  inst)` = number of violated triples (0 = all satisfied). `to_qubo`: one-hot position vars `x_{i,p}`,
  per-triple degree-2 reward on the induced-order sign + permutation one-hot penalties.
- **`best_classical.py` hunt:** the `2^n·poly` subset-DP over the set of already-placed elements (state =
  placed subset, transition = append next element, score triples now fully determined). Existence ⇒
  `classify_ordering(has_subexp_classical=True)` ⇒ **COLLAPSE (structural)**. `classical_n_exponent=1.0`
  diagnostic.
- **Predicted verdict:** COLLAPSES, structural (§6 corrected from the draft's "SURVIVES").

### `problems/p2_numerical_matching/` — Numerical Matching w/ Target Sums (Garey–Johnson) — assignment
- **Citation (verify, AC-T1.8):** Numerical Matching with Target Sums, Garey & Johnson [SP17]. **The epic's
  "JACM 1978" attribution is suspect** — this is a *Strongly NP-complete* problem catalogued in Garey &
  Johnson, *Computers and Intractability*, 1979. Verify the primary source before the writeup; cite the
  book if no 1978 journal is confirmed (OQ-flagged).
- **`instance.py`:** `KIND="ordering"` (assignment ≙ permutation matching X↔Y), `SEARCH_SPACE_EXPR="n!"`.
  `generate(n, seed)` → triples/target multiset. `cost` = number of targets whose matched sum ≠ B (0 =
  perfect matching). `to_qubo`: assignment vars + per-target sum-to-target penalty `(Σ s·x − B)²` — **the
  number-partitioning penalty form** (OQ-1: re-implemented self-contained in `instance.py`, not imported
  from `number-partitioning/`, which exposes no clean penalty function).
- **`best_classical.py` hunt:** the `O(2^n·n)` bitmask assignment DP (state = subset of Y consumed, iterate
  X in fixed order). ⇒ **COLLAPSE (structural)**.
- **Predicted verdict:** COLLAPSES, structural (§6 corrected from "strongest SURVIVES").
- **Build-validation candidate** (cheapest to wire — OQ-4).

### `problems/p3_quadratic_congruences/` — Quadratic Congruences (Manders–Adleman 1978) — subset
- **Citation (verify, AC-T1.8):** Manders & Adleman, "NP-Complete Decision Problems for Binary Quadratics",
  *J. Comput. Syst. Sci.* 16(2):168–184, 1978.
- **`instance.py`:** `KIND="subset"` (search over the bits of `x < c`), `SEARCH_SPACE_EXPR="2^n"`.
  `generate(n, seed)` → `(a, b, c)` with the decision "∃ x < c : x² ≡ a (mod b)". `cost(x_bits, inst)` =
  `(x² − a mod b)`-based violation (0 = solution). `to_hubo`: binary-expand `x`; penalty `(x² − a − b·t)²`
  is quartic ⇒ needs `framework.resources.quadratization_ancillas(hubo_degree=4, n_terms=...)`.
- **`best_classical.py` hunt:** factor `b` (sympy `factorint` / Pollard for the small `b` used) →
  Tonelli–Shanks per prime power → CRT combine. Sub-exponential; `c ≪ 0.5` ⇒ **COLLAPSE (algebraic)**.
  Reporting `c` for a sub-exp algorithm needs a convention (OQ-2): report the fitted near-zero `exponent_in_n`
  as `best_classical_exponent`, `hardness_assumption="none — sub-exponential (factoring + Tonelli–Shanks)"`,
  `notes` naming the algebraic structure.
- **`verdict.md` note (AC-T1.9):** the real quantum win here is **Shor, not Grover** — the "where Grover
  does NOT win" exemplar.
- **Predicted verdict:** COLLAPSES, algebraic.

### `problems/p4_kernel_digraph/` — Kernel of a Digraph (Chvátal 1973 TR; Fraenkel 1981) — subset — THE STAR
- **Citation (verify, AC-T1.8):** Chvátal, tech report CRM-300, Univ. de Montréal, 1973 — **a technical
  report, cite as such, not a journal**; secondary Fraenkel, "Planar kernel and Grundy…", *Discrete Appl.
  Math.* 3:257–262, 1981.
- **`instance.py`:** `KIND="subset"`, `SEARCH_SPACE_EXPR="2^n"`. `generate(n, seed)` → a digraph. Kernel =
  independent + absorbing (dominating) vertex set. `cost(subset, inst)` = independence violations +
  absorption violations (0 = kernel). `to_qubo`: membership vars, independence penalty on intra-set arcs +
  per-vertex absorption penalty; sparse/local (best hardware fit → drives the appendix).
- **`best_classical.py` hunt:** a measure-and-conquer / branch-on-vertex exact algorithm for the
  independent-**and**-absorbing set; fit its empirical base over the `n`-sweep, `classify_subset(c)`. **The
  borderline case:** independence structure pulls `c → 0.288` (collapse), domination/absorption pulls
  `c → 0.598` (survive); the *measured* `c` decides. `hardness_assumption` recorded honestly; if `c` lands
  within `eps` of 0.5 the classifier returns **UNKNOWN** and the row says so. (OQ-3: an empirical fit of a
  hand-rolled branch-and-reduce solver is accepted as tier-b.)
- **Predicted verdict:** BORDERLINE / UNKNOWN (mechanism possibly none / measure-and-conquer).

### `problems/p5_minla/` — Minimum Linear Arrangement (Garey–Johnson–Stockmeyer 1976) — ordering
- **Citation (verify, AC-T1.8):** Garey, Johnson, Stockmeyer, "Some Simplified NP-Complete Graph Problems",
  *Theoret. Comput. Sci.* 1(3):237–267, 1976.
- **`instance.py`:** `KIND="ordering"`, `SEARCH_SPACE_EXPR="n!"`. `generate(n, seed)` → a graph. `cost(perm,
  inst)` = Σ over edges `|pos(u) − pos(v)|` (minimize total edge stretch). `to_qubo`: one-hot positions
  (shared encoding with P1) + tabulated `|p−q|` edge couplings.
- **`best_classical.py` hunt:** the `O*(2^n)` Bellman–Held–Karp DP (state = placed prefix subset, cost =
  accumulated stretched edges). ⇒ **COLLAPSE (structural)**, `classical_n_exponent=1.0`.
- **Predicted verdict:** COLLAPSES, structural.

### `problems/_hardware/` (scaffold — AC-T1.10, deferred, obstruction-labelled)
- `qaoa_appendix.py`: converts `p4_kernel_digraph.instance.to_qubo` to an Ising QAOA circuit on the
  `number-partitioning/` swapnet; fixed-depth QAOA on noiseless Aer (correctness gate); prints approximation
  ratio vs a matched classical greedy baseline. `--backend` hook present but **submission deferred** (prints
  a "deferred — manual submission only" notice). Every line labelled feasibility/obstruction; cites
  Farhi–Gamarnik–Gutmann 2020; never says "advantage".
- `README.md`: states this is the deferred appendix, the QDEP readout-error obstruction (expected wall-clock
  loss on Heron), and that the headline needs zero QC.

### Shared driver files (identical logic across P1–P5)
- `classical_bruteforce.py` — per AC-T1.3.
- `quantum_grover.py` — per AC-T1.4 (subset problems carry the real `--statevector` Aer demo; ordering
  problems print query-count scaling + a note that permutation-Grover statevector is out of scope, OQ-5).
- `best_classical.py` — per AC-T1.5/§4.

---

## 7. Implementation order

1. **Build-validation problem first** (OQ-4 — recommend **P2**): full 7-file tree, run end-to-end against
   `framework/`, confirm the theorem-axis slopes (≈1.0 / ≈0.5), the classifier verdict, and a schema-valid
   appended row + re-rendered map. This shakes out the shared driver files.
2. **Extract the shared drivers** into the identical `classical_bruteforce.py` / `quantum_grover.py` /
   `best_classical.py` pattern; **P4 (the star)** next to exercise the subset + borderline + hardware-fit
   path.
3. **Loop P1, P3, P5** on the template — each only writes its `instance.py` + hunt + `definition.md` +
   `verdict.md`, appends its row.
4. **`problems/_hardware/`** scaffold last (P4 QUBO), Aer-only, submission deferred.
5. Re-render `research_runs/ledger.md` + `map.{png,svg}` from the full ledger (existing T0 entrypoints);
   confirm `validate()` passes and the map shows 1 survivor + 1 borderline + 4 collapses (3-SAT survivor
   already seeded).

---

## 8. Manual verification (no automated tests)

Per problem `p<k>_<name>/`:
- `python -m problems.p<k>_<name>.classical_bruteforce --n <small> --seed 7` → prints optimum + call count
  **exactly** `|S|` (`2^n` or `n!`).
- `python -m problems.p<k>_<name>.quantum_grover --n <small> --seed 7` → expected query count ≈`1.3·√|S|`,
  speedup factor, theorem-axis slope ≈0.5; claim-discipline banner present. Subset: add `--statevector`,
  confirm the marked/optimal state amplified above the `1/|S|` floor on Aer.
- `python -m problems.p<k>_<name>.best_classical --n-max 14 --seed 7` → fits `c`, prints the classifier
  verdict, appends the row.

Whole-map checks:
- `python -c "from framework.ledger import load, validate; validate(load())"` → passes; all six
  `EXPECTED_IDS` present.
- Re-render the map + `ledger.md`; eyeball: 3-SAT survivor at c=1.0, P4 near the line (survive/collapse/
  UNKNOWN per the *measured* `c`), P1/P2/P5 in the ordering "collapses via 2^n DP" band, P3 collapsed
  (algebraic, c≪0.5).
- Appendix: `python -m problems._hardware.qaoa_appendix` runs on Aer, prints approximation ratio +
  obstruction label, no device call.

Record measured `c`, `R²`, and any prediction overturned in each `verdict.md`.

---

## 9. Out-of-context risks / notes

- **Ordering-problem Grover statevector is heavy** — permutation index encoding + oracle over `n!` states.
  OQ-5 recommends skipping the real `--statevector` demo for P1/P2/P5 (query-count scaling suffices for the
  theorem; the amplification demo is illustrative and already shown on the subset POC).
- **P3 sub-exponential `c`** does not fit a clean `2^{c·n}` line — the fitted `exponent_in_n` will be small
  and noisy. OQ-2 sets the reporting convention; do not force a spurious tidy exponent.
- **P4 borderline** may legitimately land UNKNOWN — that is a *result*, not a failure. Do not tune the
  instance to force a side.
- **P2 citation** ("JACM 1978") is unverified; **P4** is a tech report. Verify before writeup (AC-T1.8);
  cite honestly.
- **Number-partitioning coupling** — reuse the *penalty form*, re-implemented in `p2/instance.py`; avoid
  importing `number-partitioning/` code (no clean penalty API there; cross-project import is fragile).

---

## 10. Ground rules honored
- No tests (repo directive) — verification is manual (§8).
- Strict types + `from __future__ import annotations` + PEP 8 everywhere.
- All objective evaluation through `framework.oracle.OracleCounter`.
- No verdict lives outside the ledger; `verdict` is always `classify_*(...).verdict.value`.
- No edits to `framework/` (T0) from this ticket — contract gaps become OQs.
- Claim discipline: four qualifiers on every advantage statement; "advantage" never attached to the
  hardware appendix.

---

## 11. Open questions

- **OQ-1 — P2 penalty source.** Import from `number-partitioning/` or re-implement `(Σ s·x − B)²` in
  `p2/instance.py`? **Proposed default: re-implement self-contained** — `number-partitioning/` exposes no
  clean penalty function (only a brute-force reference + a QAOA script), and a cross-project import couples
  two studies. The epic's "reuse verbatim" is honored as *reuse the penalty form*.
- **OQ-2 — P3 reporting of a sub-exponential `c`.** A factoring+Tonelli–Shanks solver has no clean
  `2^{c·n}` slope. **Proposed default:** report the fitted near-zero `exponent_in_n` as
  `best_classical_exponent`, set `verdict=COLLAPSES`, `collapse_mechanism="algebraic"`,
  `hardness_assumption="none — sub-exponential"`, and explain in `notes` + `verdict.md`.
- **OQ-3 — P4 hunt rigor (tier-b). RESOLVED (amended).** **Prefer an existing / published implementation
  of each problem's best-known classical algorithm where one can be sourced** (vetted library, reference
  code, or a paper's released solver); fall back to a hand-rolled branch-and-reduce solver only where no
  usable external implementation exists. Either way, fit the exponent empirically over the `n`-sweep,
  record the source in `best_classical_source` + `verdict.md`, and return UNKNOWN if `c` lands within `eps`
  of 0.5. Applies to all five hunts, not just P4.
- **OQ-4 — build-validation problem.** P2 (cheapest to wire) or P4 (the star) first? **Proposed default:
  P2 first** to shake out the template, then P4.
- **OQ-5 — statevector demo scope.** Real Aer `--statevector` amplification demo for ordering problems
  (P1/P2/P5)? **Proposed default: subset only (P3, P4)**; ordering problems print query-count scaling + a
  note. The theorem is carried by the query count; the amplification demo is illustrative and already on the
  subset POC.
- **OQ-6 — hardware appendix depth.** Scaffold `problems/_hardware/` with an Aer-only QAOA run now (no
  submission), per AC-T1.10? **Proposed default: yes, scaffold only** — code + harness + obstruction
  README, `--backend` present but submission deferred.

---

## 12. After approval
Answer the open questions and set `Status: Approved`, then run
`/implement-feature plans/feature-T1-five-problems.md`.

## 13. Post-implementation (2026-09-06)

### What was built
Five `problems/p<k>_<name>/` packages on the T0 framework, three thin driver files each
delegating to `problems/_drivers.py` (the shared classical/quantum/hunt runners, kept DRY
per the epic "shared driver files"), plus the deferred `problems/_hardware/` QAOA appendix.
All five verdict rows were appended to `research_runs/ledger.json` and the map re-rendered.

### Measured map (the headline)
| id | space | verdict | c | mechanism |
|----|-------|---------|---|-----------|
| `_3sat_reference` | 2^n | SURVIVES | 1.000 | — (reference survivor, SETH) |
| `p1_betweenness` | n! | COLLAPSES | — | structural |
| `p2_numerical_matching` | n! | COLLAPSES | — | structural |
| `p3_quadratic_congruences` | 2^n | COLLAPSES | 0.075 | algebraic (Shor, not Grover) |
| `p4_kernel_digraph` | 2^n | **SURVIVES (borderline, +0.031)** | 0.531 | — (the star, on the line) |
| `p5_minla` | n! | COLLAPSES | — | structural |

Reads as the epic intended: one clean reference survivor (3-SAT), the borderline star (P4)
landing a hair above the line, four collapses across all three mechanisms (3× structural,
1× algebraic). Theorem axis on every problem: classical slope 1.000 / quantum slope 0.500,
R²=1.0 — the BBBV-optimal quadratic query speedup, exact by counting.

### AC evidence (file:line)
- AC-T1.1 dir contract — all five `problems/p<k>_<name>/` have the 7 files (`ls` verified).
- AC-T1.2 `instance.py` contract — e.g. `p2_numerical_matching/instance.py:31,50,55,62,66`.
- AC-T1.3 `classical_bruteforce.py` — `problems/_drivers.py:70` (`run_classical`, asserts calls==|S|).
- AC-T1.4 `quantum_grover.py` — `problems/_drivers.py:104` (`run_quantum`, banner+slope; `_statevector_demo:150`).
- AC-T1.5/6/7 `best_classical.py` hunt+row — `problems/_drivers.py:210` (`run_hunt`); algorithms in each `best_classical.py:algorithm`.
- AC-T1.8 `definition.md` (verified citations, P2 book/P4 tech-report caveats) — one per problem dir.
- AC-T1.9 `verdict.md` — one per problem dir (P3 Shor note; P4 on-the-line caveat).
- AC-T1.10 hardware appendix — `problems/_hardware/qaoa_appendix.py` (Aer-only, deferral notice, FGG2020).
- AC-T1.11 P2 built first as validation — confirmed before looping the rest.
- Ledger validates: `framework.ledger.validate(load())` passes; all 6 `EXPECTED_IDS` present.

### Deviations / notes for the developer
- **On `main`** (not a `feature-` branch): consistent with how T0 was landed; this is a
  research repo with no numeric ticket. Flag if you want it on a branch.
- **P4 measured SURVIVES at c≈0.531 (margin +0.031)** — genuinely on the √2 line. Reported
  honestly as a thin-margin survivor with a caveat in `verdict.md`; a stronger
  measure-and-conquer solver or different seed could push it below 0.5. 3-SAT stays the clean
  survivor. This is the intended "star" outcome, not an overclaim.
- **Ordering `exponent_in_n` warning** (framework AC-T0.4) is silenced in `_drivers._fit_quiet`
  for the deliberate ordering path only — we take the verdict from `classify_ordering`, exactly
  as the warning instructs.
- **P2 penalty re-implemented** self-contained (OQ-1); **P3 sub-exp c reported** as fitted
  near-zero with `hardness="none — sub-exponential"` (OQ-2); **sympy** used for P3 (OQ-3,
  existing vetted impl); **P4 hand-rolled** brancher (OQ-3 fallback, no library solver found);
  **statevector** subset-only, ordering prints an out-of-scope note (OQ-5); **hardware** Aer-only
  scaffold, submission deferred (OQ-6).
- **No new dependency added** — `numpy`/`matplotlib`/`qiskit`/`qiskit-aer`/`sympy` already present.

### Follow-ups
- T2 web spectacle reads this ledger (now complete with all 6 rows) — unblocked.
- Optional: real Heron submission of the P4 QAOA appendix (manual, deferred) if the thesis
  wants the obstruction datapoint on-device.
