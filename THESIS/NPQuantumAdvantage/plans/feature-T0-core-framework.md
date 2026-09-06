# Feature Plan — T0: Core framework, √2 classifier & the map machinery

**Status:** Complete (2026-09-06 — all AC-T0.1–T0.10 manually verified, see §13)
**Epic:** `THESIS/NPQuantumAdvantage/plans/epic-np-query-advantage-map.md` (Status: **Approved (revised)**)
**Ticket ID:** T0 (first of 3; no dependency — gates T1 and T2)
**Absorbs:** old F0 (framework) + F6 (map renderer)
**Author:** Claude (Opus) · **Date:** 2026-09-06
**Mirrors output style of:** `proof_of_concept/classical_bruteforce.py`, `proof_of_concept/quantum_grover.py`
**Reuses pipeline of:** `plans/MINIMAL.md` (query-count POC → promoted to `framework.selftest`)

> No GitHub issue — this study uses author-defined T-ids, not tickets (repo directive).
> No tests (project directive): production code + manual verification only. The `framework.selftest`
> and `tools/parity_check.py` below are **framework self-checks / reproducibility artefacts**, not a test
> suite — they ship as runnable modules, not as `test_*.py` under a runner.

---

## 1. Context & goal

T0 is the shared spine of the whole epic. It builds the reused-by-all-five machinery so the study is
**systemic** (one framework, one theorem demonstrated identically) rather than five disconnected scripts,
and it renders the single thesis figure — the √2 map. T0 owns **all math and I/O contracts**; T1's five
problems supply only an instance generator + cost oracle + QUBO map and inherit everything here. T2's web
spectacle vendors T0's counter (JS mirror) and reads T0's ledger.

T0 fixes, once, the things T1/T2 must not re-decide:
1. The **oracle-call counter** contract (`framework/oracle.py`) — one increment per cost evaluation.
2. The **query-count engine** (`framework/grover_min.py`) — the ideal Dürr–Høyer/Grover call counts.
3. The **two-axis distinction** (§7): the *theorem axis* (slope 1.0 classical / 0.5 quantum, always true)
   vs the *verdict axis* (the √2 line: SURVIVE ⟺ best-classical exponent `c > 0.5`). Conflating these was
   the flaw the epic §6 spine corrects; `fit.py` + `classify.py` keep them distinct in code.
4. The **ledger schema** (`research_runs/ledger.json`, version 1) — the single source of truth every
   verdict lives in; T1 appends rows, the map + T2 read it.
5. The **JS mirror + parity contract** (`web/lib/grover_count.js` ↔ `tools/parity_check.py`) — the
   TargetedDos D-parity discipline, so the browser demo is a reproducibility artefact.

### What already exists (integration points)
- `proof_of_concept/classical_bruteforce.py` — the output style to mirror: prints problem, search space
  `2^n`, solutions/marked count `M`, verifier call count `== 2^n`, and the scaling label. `brute_force(n)`
  returns `(solutions, calls)` counting every `verify()` call — the query-model cost. T0 generalises this
  into `framework/bruteforce.py` (a `cost`-through-a-counter template).
- `proof_of_concept/quantum_grover.py` — the output style to mirror: prints search space, marked states,
  Grover oracle calls `iters = floor((pi/4)·sqrt(N/M))`, classical calls `N`, speedup factor, and (Aer arm)
  amplification above the uniform floor. T0's `grover_min.py` lifts the *counting* half (no statevector);
  the statevector/Aer amplification demo stays in T1's `quantum_grover.py`.
- `plans/MINIMAL.md` — the query-count pipeline (instance → counted cost → brute `2^n` → ideal
  Dürr–Høyer `~1.3·2^{n/2}` → fit exponent, expect classical ≈1.0 / quantum ≈0.5). T0 promotes this exact
  pipeline into `framework/selftest.py` (AC-T0.10).
- No `framework/` directory exists yet — T0 creates it. T0 has **no code dependency** on T1/T2.

---

## 2. Acceptance criteria

Verbatim from epic §9 (T0). IDs kept as the epic wrote them (`AC-T0.1`–`AC-T0.10`). Each maps to a manual
check in §8.

- **AC-T0.1 `framework/oracle.py` — the single call counter.**
  - `class OracleCounter` with `.count: int`, `.reset() -> None`, and
    `.wrap(fn: Callable[..., T]) -> Callable[..., T]` that returns a wrapper incrementing `.count` on every
    call and forwarding args/result unchanged.
  - Also a `@counted(counter)` decorator form for module-level oracles.
  - Contract: exactly one increment per cost/verifier evaluation; both files of every problem share one
    `OracleCounter` instance per run; `.reset()` zeroes it between `n` points in a sweep.

- **AC-T0.2 `framework/grover_min.py` — ideal query-count engine (no statevector).**
  - `search_space_size(n: int, kind: Literal["subset","ordering"]) -> int` → `2**n` or `factorial(n)`.
  - `grover_iterations(N: int, M: int) -> int` → the exact optimal Grover count
    `k = floor((pi/4) * sqrt(N / max(M, 1)))`, returned as `max(k, 1)` for `M ≥ 1`, `0` for `M == 0`.
    One iteration = one oracle call.
  - `durr_hoyer_expected_queries(N: int, *, c_dh: float = 1.3) -> float` → expected total oracle calls for
    quantum **minimum-finding** over `N` items, modelled as `c_dh * sqrt(N)`. **Document explicitly:**
    Dürr–Høyer (1996) prove an upper bound `≤ 22.5·√N`; the `1.3` default is the illustrative practical
    constant matching the POC. **Only the exponent (0.5) is the scientific claim; `c_dh` shifts the
    intercept, never the slope.** Expose `c_dh` so the intercept is not mistaken for a result.
  - `expected_queries(n, kind, marked=1, mode=Literal["search","min"]) -> float` → the single entry point
    every `quantum_grover.py` calls; dispatches to `grover_iterations` (search) or
    `durr_hoyer_expected_queries` (min) over `search_space_size(n, kind)`.

- **AC-T0.3 `framework/bruteforce.py` — generic exhaustive template.**
  - `brute_force_min(candidates: Iterable[C], cost: Callable[[C], float], counter: OracleCounter)
    -> tuple[C, float, int]` → returns `(argmin, min_cost, counter.count)`, calling `cost` through the
    counter for every candidate.
  - `enumerate_space(n, kind)` helper → yields all `2^n` bitstrings (subset) or all `n!` permutations
    (ordering). Classical call count must equal `|S|` exactly (the `log2` intercept the theorem axis relies on).

- **AC-T0.4 `framework/fit.py` — the exponent fitter (both axes).**
  - `fit(ns: list[int], calls: list[float], space_sizes: list[int]) -> FitResult`.
  - `FitResult` (dataclass) fields: `slope_vs_logspace: float` (least-squares slope of `log2(calls)` vs
    `log2(|S|)` — the **theorem-axis** number, expect ≈1.0 classical / ≈0.5 quantum), `r2_vs_logspace: float`,
    `exponent_in_n: float` (slope of `log2(calls)` vs `n` — the **verdict-axis** `c` in `2^{c·n}`; a clean
    constant for subset problems, and for ordering problems a *diagnostic only*, since the true n-exponent
    grows), `r2_in_n: float`.
  - Must warn (not silently) when `kind == "ordering"` and `exponent_in_n` is read as a constant.

- **AC-T0.5 `framework/classify.py` — the √2 classifier (two branches).**
  - `classify_subset(c_classical: float, *, eps: float = 1e-6) -> Verdict` → `SURVIVES` if
    `c_classical > 0.5 + eps`, `COLLAPSES` if `c_classical < 0.5 - eps`, else `UNKNOWN`.
  - `classify_ordering(has_subexp_classical: bool, classical_n_exponent: float | None) -> Verdict` →
    `COLLAPSES` if a `2^{O(n)}` classical algorithm exists (`has_subexp_classical` True — i.e. any
    Held–Karp/bitmask DP), else `UNKNOWN`/`SURVIVES` only if best known is `Θ(n!)`. Documents that `√(n!)`
    is asymptotically above `2^{c·n}` for any finite `c`.
  - `Verdict` = `Enum{SURVIVES, COLLAPSES, UNKNOWN}`. Both functions also return `margin_to_line: float`
    (`c_classical − 0.5` for subset; `None`/annotated for ordering) and a
    `mechanism: Literal["structural","measure-and-conquer","algebraic"] | None` slot the caller fills.

- **AC-T0.6 `framework/resources.py` — fault-tolerant estimator (documented formula).**
  - `estimate_grover_resources(oracle_qubits: int, oracle_toffoli_count: int, queries: float,
    ancillas: int = 0) -> Resources`.
  - Formula (state it in the docstring): `logical_qubits = oracle_qubits + ancillas + 1` (phase workspace);
    `toffoli_total = queries * oracle_toffoli_count`; `t_count ≈ 7 * toffoli_total` (7 T-gates per Toffoli,
    standard). Report `t_count` as an order of magnitude (e.g. `"~1e6"`).
  - `quadratization_ancillas(hubo_degree: int, n_terms: int) -> int` helper for HUBO→QUBO overhead (P3),
    documented as the extra qubit cost the algebraic-collapse case pays even in the FT model.

- **AC-T0.7 `framework/ledger.py` — the single source of truth (exact schema).**
  - `append_row(row: LedgerRow, path="research_runs/ledger.json") -> None` (idempotent on `id` —
    re-appending the same `id` overwrites, so re-runs don't duplicate), `load(path) -> Ledger`,
    `render_markdown(ledger) -> str` → `research_runs/ledger.md`.
  - **`ledger.json` schema (version 1)** — exactly the epic §9 AC-T0.7 block (reproduced in §4 below); every
    field required unless marked optional.
  - A `validate(ledger)` that fails loudly if a row has `verdict != UNKNOWN` with a missing
    `best_classical_exponent` (subset) or missing `collapse_mechanism` on a `COLLAPSES` row.

- **AC-T0.8 `framework/map_figure.py` — the single thesis figure (from the ledger only).**
  - `render(ledger_path, out="research_runs/map") -> None` → writes `map.png` **and** `map.svg`.
  - Layout: **subset problems** plotted on the primary horizontal axis = `best_classical_exponent`, with a
    bold vertical threshold at `0.5` (labelled "√2 line — Grover exponent"); one dot per problem, coloured by
    verdict (survive above/right, collapse below/left), the **3-SAT reference survivor** pinned at `c = 1.0`.
    **Ordering problems** shown in a separate labelled band ("ordering — collapses via 2^n Held–Karp DP")
    annotated with the `√(n!)` vs `2^n` crossover, since a fixed-`c` axis is not meaningful for them.
  - Must run against a **partial/stubbed ledger** (missing rows render as greyed "pending") so the figure
    exists from day one.

- **AC-T0.9 `web/lib/grover_count.js` + parity harness — reproducibility contract.**
  - `grover_count.js` exports `searchSpaceSize(n, kind)`, `groverIterations(N, M)`, and
    `expectedQueries(n, kind, marked, mode)` — byte-for-byte the same integer/float logic as T0.2.
  - `tools/parity_check.py` dumps Python values for a fixed vector of
    `(n ∈ {4..14}) × (kind ∈ {subset, ordering}) × (marked ∈ {1, 2, 4})` to JSON; a Node runner computes the
    JS values; the harness asserts **identical integers** for iteration counts and floats within `1e-9` for
    expected-query counts. Runs at web build time (fails the build on mismatch — the TargetedDos D-parity
    discipline).

- **AC-T0.10 A `framework/` smoke run** (`python -m framework.selftest`) that, on a trivial built-in subset
  oracle, sweeps `n ∈ {4..14}`, and asserts `fit().slope_vs_logspace ≈ 1.0` (classical) and `≈ 0.5`
  (quantum) with `R² > 0.99` — proving the theorem machinery before any real problem lands. (This is the
  `MINIMAL.md` pipeline, promoted into the framework as its self-test.)

---

## 3. Scope

### In scope
- New package `THESIS/NPQuantumAdvantage/framework/` with `__init__.py` and the nine modules:
  `oracle.py`, `grover_min.py`, `bruteforce.py`, `fit.py`, `classify.py`, `resources.py`, `ledger.py`,
  `map_figure.py`, `selftest.py`.
- New `research_runs/` outputs: `ledger.json` (seeded — see OQ-3), `ledger.md`, `map.png`, `map.svg`.
- New `web/lib/grover_count.js` (the vendored JS mirror) + `tools/parity_check.py` + a standalone Node
  runner `tools/parity_check.mjs` so the parity assert is runnable now (T2 wires it into the Next build).
- Query-count math only. Deps: `numpy` (fit), `matplotlib` (figure). **No Qiskit in T0** (epic §9
  "Conventions": query-count only; full statevector Grover is T1's per-problem opt-in).

### Out of scope (deferred to their tickets)
- Any specific problem's instance generator, cost oracle, or QUBO/HUBO map — **T1** (`problems/p<k>_*`).
- Full statevector / Aer Grover amplification demo — **T1** (`quantum_grover.py --statevector`).
- The `best_classical.py` hunts that fit each real `c` and append real ledger rows — **T1**.
- The Next.js web spectacle, its scenes, and wiring `parity_check` into the build — **T2**.
- Hardware / QAOA appendix — **T1** appendix (deferred), never T0.
- Inventing a sub-`2^{n/2}` classical algorithm — out of the whole epic (bar is tier-b, best *known*).

---

## 4. Data model — `research_runs/ledger.json` (the epic-wide schema; T0 defines it, version 1)

Written to `research_runs/` (i.e. `THESIS/NPQuantumAdvantage/research_runs/`). **This is the one file every
verdict lives in.** T0 owns the schema + writer + validator + renderer; T1 appends one row per problem; the
map figure and T2 read it. No verdict lives anywhere else (epic CD).

```jsonc
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

- `LedgerRow` is a dataclass with exactly these fields (optional fields default `None`). `Ledger` wraps
  `schema_version`, `grover_exponent`, `threshold`, and `rows: list[LedgerRow]`.
- `append_row` is **idempotent on `id`**: re-appending an existing `id` overwrites that row in place (re-runs
  don't duplicate); a new `id` appends. Rows keep insertion order for a stable figure/table.
- `validate(ledger)` raises loudly when `verdict != UNKNOWN` and (`search_space == "subset"` and
  `best_classical_exponent is None`) OR (`verdict == "COLLAPSES"` and `collapse_mechanism is None`).
- Field names are the epic §4/§9 contract — **do not rename**; T1 and T2 consume them.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **The √2 line is the spine.** `c > 0.5 → SURVIVES`, `c ≤ 0.5 → COLLAPSES`; Grover's exponent is the fixed
  threshold `0.5` (base √2). `classify.py` is this rule in code; the map figure is this axis.
- **Search-space type drives the verdict.** Every problem is `subset` (2^n, Grover `2^{n/2}`) or
  `ordering`/assignment (`n!`, Grover `√(n!)`). Ordering problems collapse structurally whenever a `2^{O(n)}`
  DP exists. This is a required ledger field and a `classify.py` branch.
- **Query-count is the primary quantum measurement, not statevector.** T0 counts Dürr–Høyer's expected
  oracle calls; no 2^n-amplitude simulation. (The small-n Aer amplification demo is T1's, not T0's.)
- **The ledger is the single source of truth** (§4). T0 renders the map from it; T1 appends; T2 reads.
- **Claim discipline is locked.** Four qualifiers on every advantage statement in docstrings/prints:
  **query model · over brute force · quadratic · not wall-clock.** "Undeniable" maps only to the query-model
  theorem; the map is what is *novel*. `c_dh`'s intercept is never presented as a result — only the exponent.
- **Parity discipline (TargetedDos).** The JS mirror is byte-for-byte the same logic as `grover_min.py`;
  `parity_check` asserts it. Never hand-edit the vendored JS to diverge from the Python source of truth.
- **Fixed-seed, CLI-parametrised, small defaults.** The selftest sweeps `n ∈ {4..14}` deterministically.

---

## 6. File plan (concrete paths)

All Python: `from __future__ import annotations`, full type hints (PEP 484), PSR-equivalent Python style
(PEP 8), no raw SQL (N/A — JSON ledger via `json`), no business logic in any I/O layer. New package under
`THESIS/NPQuantumAdvantage/`.

### `framework/__init__.py` (new)
Package marker + convenience re-exports (`OracleCounter`, `Verdict`, `LedgerRow`, `expected_queries`,
`fit`, `classify_subset`, `classify_ordering`). Docstring names the epic + the two-axis crux (§7).

### `framework/oracle.py` (new) — AC-T0.1
- `class OracleCounter`: `count: int = 0`; `reset() -> None`; `wrap(fn: Callable[..., T]) -> Callable[..., T]`
  returning a `functools.wraps`-preserving closure that does `self.count += 1; return fn(*a, **k)`.
- `def counted(counter: OracleCounter) -> Callable[[Callable[..., T]], Callable[..., T]]` decorator form.
- No I/O, no other deps.

### `framework/grover_min.py` (new) — AC-T0.2
- `from math import factorial, floor, pi, sqrt`; `KIND = Literal["subset","ordering"]`, `MODE = Literal["search","min"]`.
- `search_space_size(n, kind)`, `grover_iterations(N, M)`, `durr_hoyer_expected_queries(N, *, c_dh=1.3)`,
  `expected_queries(n, kind, marked=1, mode="min")` exactly per AC. Module docstring carries the
  Dürr–Høyer `≤ 22.5·√N` upper bound + the `c_dh`-is-intercept-not-result note + the four claim qualifiers.
- **This module is the Python source of truth the JS mirror parities against.** Keep the integer/float
  arithmetic simple and portable (no numpy) so JS reproduces it byte-for-byte.

### `framework/bruteforce.py` (new) — AC-T0.3
- `from itertools import permutations`; `brute_force_min(candidates, cost, counter)` calls
  `counter.wrap(cost)` (or increments inline) once per candidate, tracks argmin/min. Returns
  `(argmin, min_cost, counter.count)`.
- `enumerate_space(n, kind)`: subset → `range(1 << n)` (int bitmasks); ordering → `permutations(range(n))`.
  Yields exactly `|S|` candidates. Mirrors the POC's `brute_force` counting discipline.

### `framework/fit.py` (new) — AC-T0.4
- `numpy.polyfit` degree-1 for both slopes; `FitResult` dataclass (`slope_vs_logspace`, `r2_vs_logspace`,
  `exponent_in_n`, `r2_in_n`). `_r2(x, y, coeffs)` helper.
- `fit(ns, calls, space_sizes, *, kind="subset")` — **adds a `kind` keyword** (see OQ-1) so it can `warnings.warn`
  when `kind == "ordering"` and `exponent_in_n` is being read as a constant, per AC-T0.4's warn requirement.

### `framework/classify.py` (new) — AC-T0.5
- `class Verdict(Enum): SURVIVES; COLLAPSES; UNKNOWN`.
- `classify_subset(c_classical, *, eps=1e-6) -> ClassifyResult`, `classify_ordering(has_subexp_classical,
  classical_n_exponent) -> ClassifyResult`. `ClassifyResult` carries `verdict`, `margin_to_line`, and the
  caller-filled `mechanism` slot. Docstring states `√(n!) > 2^{c·n}` for any finite `c`.

### `framework/resources.py` (new) — AC-T0.6
- `@dataclass class Resources: logical_qubits: int; toffoli_total: float; t_count: str`.
- `estimate_grover_resources(...)` with the documented formula; `_order_of_magnitude(x) -> str` → `"~1e6"`.
- `quadratization_ancillas(hubo_degree, n_terms) -> int` (documented HUBO→QUBO overhead for P3).

### `framework/ledger.py` (new) — AC-T0.7
- `@dataclass class LedgerRow` (all §4 fields; optionals default `None`); `@dataclass class Ledger`
  (`schema_version=1`, `grover_exponent=0.5`, `threshold=0.5`, `rows: list[LedgerRow]`).
- `load(path)`, `append_row(row, path=...)` (idempotent on `id`, `os.makedirs` the dir),
  `save(ledger, path)`, `validate(ledger)` (loud `ValueError`), `render_markdown(ledger) -> str` +
  writes `research_runs/ledger.md`. All JSON via `json` (no raw SQL). `EXPECTED_IDS` constant lists the
  canonical row ids (`_3sat_reference`, `p1_betweenness`, …, `p5_minla`) so the map knows what is "pending".

### `framework/map_figure.py` (new) — AC-T0.8
- `matplotlib` (Agg backend, no display). `render(ledger_path, out="research_runs/map")` writes `map.png`
  + `map.svg`. Subset dots on the `best_classical_exponent` axis with the bold `0.5` threshold; ordering band
  separate; 3-SAT survivor pinned at `c = 1.0`; ledger `EXPECTED_IDS` absent from the loaded ledger drawn
  greyed "pending". Colour by verdict. No math here beyond reading the ledger — figure only.

### `framework/selftest.py` (new) — AC-T0.10
- `python -m framework.selftest`: a trivial built-in subset oracle (e.g. min of a random-but-seeded cost over
  `2^n` bitmasks), sweep `n ∈ {4..14}`; classical arm via `bruteforce.brute_force_min` (calls `== 2^n`),
  quantum arm via `grover_min.expected_queries(n,"subset","min")`; `fit(...)` both; assert
  `slope_vs_logspace ≈ 1.0` (classical) / `≈ 0.5` (quantum), `R² > 0.99`. Prints the POC-style table and a
  clear PASS/FAIL line. This is the `MINIMAL.md` pipeline promoted into the framework.

### `web/lib/grover_count.js` (new) — AC-T0.9 (vendored mirror)
- ES module exporting `searchSpaceSize(n, kind)`, `groverIterations(N, M)`,
  `expectedQueries(n, kind, marked, mode)` — the same arithmetic as `grover_min.py`. Header comment: "VENDORED
  from `framework/grover_min.py` — do not edit by hand; regenerate + re-run `tools/parity_check`."
  Uses BigInt for `factorial`/`2**n` where needed so large-n integers match Python exactly.

### `tools/parity_check.py` (new) — AC-T0.9 (Python side)
- Dumps the Python values for `(n ∈ 4..14) × (kind ∈ {subset,ordering}) × (marked ∈ {1,2,4})` to
  `tools/parity_vector.json`; then shells out to the Node runner and asserts integers identical / floats
  within `1e-9`; exits non-zero on mismatch (the build-fail hook T2 wires in).

### `tools/parity_check.mjs` (new) — AC-T0.9 (Node side)
- Imports `../web/lib/grover_count.js`, reads `parity_vector.json`, writes the JS-computed values to stdout
  as JSON for `parity_check.py` to compare. Standalone-runnable (`node tools/parity_check.mjs`).

### `research_runs/ledger.json` (new, seeded) + `ledger.md`, `map.png`, `map.svg`
- Seeded with the **3-SAT reference-survivor row** (OQ-3) so the map has its anchor survivor from day one;
  all five problem rows absent → render greyed "pending". `ledger.md` + `map.{png,svg}` generated by running
  `render_markdown` + `map_figure.render` once at the end of T0.

---

## 7. The two axes T0 must keep distinct (the crux)

This is the epic §9 T0 "two axes" contract, in code. `fit.py` and `classify.py` must never let a caller
conflate them.

1. **Theorem axis (universal, always demonstrated).** `log2(oracle_calls)` vs `log2(|S|)`, `|S|` = feasible
   space size (`2^n` subset, `n!` ordering). Slope is **1.0 classical / 0.5 quantum for every problem
   regardless of type** — the quadratic query speedup, proven by counting. `fit.FitResult.slope_vs_logspace`
   is this number; `selftest` asserts it.
2. **Verdict axis (the √2 line).** Quantum vs *best-known-classical* as functions of input size `n`. Subset:
   both `2^{c·n}`, quantum `c_Q = 0.5`; **SURVIVE ⟺ c_cl > 0.5** (`classify_subset`). Ordering: quantum
   `√(n!) = 2^{0.5·log2(n!)}` (n-exponent grows) vs a `2^n` Held–Karp DP (n-exponent 1.0, constant) → the
   classical curve is asymptotically below quantum, so ordering problems **COLLAPSE whenever any `2^{O(n)}`
   classical algorithm exists** (`classify_ordering`); they survive only if best known is `Θ(n!)`.

`fit.exponent_in_n` is the verdict-axis `c` — a clean constant for subset, a **diagnostic-only** growing
quantity for ordering (hence the `kind=="ordering"` warning in AC-T0.4).

---

## 8. Manual verification (no automated tests)

Run from `THESIS/NPQuantumAdvantage/`.

- **AC-T0.1** — `python -c "from framework.oracle import OracleCounter; c=OracleCounter(); f=c.wrap(lambda x:x*x);
  [f(i) for i in range(5)]; print(c.count)"` → prints `5`; `c.reset()` → `0`. Confirm one increment per call.
- **AC-T0.2** — `python -c "from framework.grover_min import *; print(search_space_size(4,'subset'),
  grover_iterations(16,1), round(durr_hoyer_expected_queries(16),3), round(expected_queries(4,'subset',1,'min'),3))"`
  → `16 3 5.2 5.2` (matches the POC: n=4,M=1 → 3 search iterations). `search_space_size(5,'ordering')` → `120`.
- **AC-T0.3** — `python -c "from framework.bruteforce import *; from framework.oracle import OracleCounter;
  c=OracleCounter(); a,v,n=brute_force_min(enumerate_space(4,'subset'), lambda x:(x-9)**2, c); print(a,v,n)"`
  → `9 0 16` (argmin=9, cost 0, exactly `2^4` calls).
- **AC-T0.4** — the selftest (AC-T0.10) prints both slopes; separately
  `python -W all -c "from framework.fit import fit; fit([4,5],[24,120],[24,120],kind='ordering')"` emits the
  ordering warning.
- **AC-T0.5** — `python -c "from framework.classify import *; print(classify_subset(0.598).verdict,
  classify_subset(0.288).verdict, classify_subset(0.5).verdict, classify_ordering(True,None).verdict)"`
  → `SURVIVES COLLAPSES UNKNOWN COLLAPSES`.
- **AC-T0.6** — `python -c "from framework.resources import *; r=estimate_grover_resources(20,50,1e6);
  print(r.logical_qubits, r.t_count)"` → `21 ~1e9` (order-of-magnitude string). `quadratization_ancillas(4,10)` returns an int.
- **AC-T0.7** — append two rows with the same `id`, `load`, confirm one row (idempotent); `validate` on a
  `COLLAPSES` row missing `collapse_mechanism` raises `ValueError`; `ledger.md` written.
- **AC-T0.8** — `python -c "from framework.map_figure import render; render('research_runs/ledger.json')"`
  writes `research_runs/map.png` + `map.svg`; open → the `0.5` threshold, the 3-SAT survivor at `c=1.0`, the
  five problem rows greyed "pending".
- **AC-T0.9** — `python tools/parity_check.py` → prints `PARITY OK` and exits 0; hand-edit one constant in
  `web/lib/grover_count.js`, re-run → non-zero exit + the mismatch line. Restore.
- **AC-T0.10** — `python -m framework.selftest` → POC-style table, `slope_vs_logspace` ≈1.0 classical / ≈0.5
  quantum, `R² > 0.99`, ends `SELFTEST PASS`.
- **Determinism** — the selftest and any seeded generator reproduce identical numbers across runs.

---

## 9. Out-of-context risks / notes

- **AC-T0.4 signature mismatch.** The epic writes `fit(ns, calls, space_sizes)` but also requires a warning
  keyed on `kind == "ordering"` — impossible without a `kind`. The plan adds a `kind="subset"` keyword
  (OQ-1). Flagged so the implementer doesn't "fix" it back and lose the warning.
- **JS/Python integer parity.** `2**n` and `factorial(n)` exceed JS `Number` safe-integer range past ~n=18;
  the sweep caps at n=14 so plain `Number` suffices, but `grover_count.js` uses `BigInt` for the size
  functions to stay exact if the vector is ever widened. `parity_check` compares as strings for integers.
- **`floor((pi/4)·sqrt(...))` rounding.** Both sides must use IEEE-754 double `Math.sqrt`/`math.sqrt` then
  floor — identical on both runtimes for the n≤14 vector. Verified by the parity assert, not assumed.
- **matplotlib backend.** `map_figure.py` must set `matplotlib.use("Agg")` before `pyplot` import (headless).
- **Node availability.** `parity_check.py` needs `node` on PATH. TargetedDos's web stack already requires it;
  if absent at T0 time the Python-side vector still dumps and the assert is deferred to the T2 build (OQ-2).
- **No Qiskit in T0** — if an implementer reaches for statevector Grover here, it belongs in T1. T0's quantum
  number is the *count*, full stop.

---

## 10. Ground rules honored

- Every AC (T0.1–T0.10) quoted verbatim from epic §9 and mapped to a §8 manual check.
- Every file path in §6 concrete; no placeholders. New package + `research_runs/` + `web/lib/` + `tools/`.
- Epic cross-cutting decisions adopted without re-arguing (√2 spine, search-space tag, query-count primary,
  ledger single-source, claim discipline, parity discipline).
- No tests, no test files, no test-impact section (project directive); the selftest/parity are runnable
  framework self-checks, not a suite.
- Strict typing + `from __future__ import annotations`; no raw SQL; no business logic in I/O layers.

---

## 11. Open questions — RESOLVED (developer accepted all defaults, 2026-09-06)

- [x] **OQ-1 — `fit()` signature.** **Resolved:** add a `kind: Literal["subset","ordering"] = "subset"`
  keyword to `fit()`; positional contract unchanged. Enables the AC-T0.4 ordering warning.
- [x] **OQ-2 — Parity assert at T0 or T2.** **Resolved:** T0 ships `grover_count.js` + `parity_check.py` +
  `parity_check.mjs`, manually verified once (§8 AC-T0.9); T2 wires the assert into the Next build.
- [x] **OQ-3 — Seed the 3-SAT reference row.** **Resolved:** T0 seeds `ledger.json` with one
  `_3sat_reference` row (`search_space="subset"`, `best_classical_exponent=1.0`, `verdict="SURVIVES"`,
  `hardness_assumption="SETH"`, POC citation) so figure + web read it uniformly.
- [x] **OQ-4 — `map.png` DPI / palette.** **Resolved:** 150 DPI PNG + SVG; colour-blind-safe verdict palette
  (SURVIVES green, COLLAPSES orange, UNKNOWN grey, pending light-grey).

---

## 12. After approval

Run `/implement-feature THESIS/NPQuantumAdvantage/plans/feature-T0-core-framework.md` to build T0. T1 and
T2 are blocked on this ticket (both consume T0's contracts).

---

## 13. Post-implementation

**Built (2026-09-06).** The whole T0 spine landed as `THESIS/NPQuantumAdvantage/framework/` (9 modules +
`__init__`), the vendored JS mirror + parity harness, and the seeded ledger + rendered map. Query-count math
only, no Qiskit. All AC manual checks (§8) pass.

### AC coverage (file:line evidence)

| AC | File:line | Verified |
|----|-----------|----------|
| T0.1 OracleCounter/counted | `framework/oracle.py:26,54` | `.count`→5, `.reset()`→0 |
| T0.2 grover_min engine | `framework/grover_min.py:31,44,64,76` | `16 3 5.2 5.2 120` |
| T0.3 brute_force_min/enumerate_space | `framework/bruteforce.py:26,52` | `9 0 16` (=2^4 calls) |
| T0.4 fit + ordering warn | `framework/fit.py:52,77` | slopes 1.0/0.5 R²=1.0; warning fires |
| T0.5 √2 classifier | `framework/classify.py:47,66` | `SURVIVES COLLAPSES UNKNOWN COLLAPSES` |
| T0.6 FT resources | `framework/resources.py:52,80` | `21 ~1e9`; `quadratization_ancillas(4,10)=20` |
| T0.7 ledger (idempotent+validate) | `framework/ledger.py:104,124,145` | double-append→1 row; validate raises |
| T0.8 map figure | `framework/map_figure.py:33` | `map.png`+`map.svg`, √2 line, 3-SAT@1.0, 5 pending |
| T0.9 JS mirror + parity | `web/lib/grover_count.js:17`, `tools/parity_check.py:63`, `tools/parity_check.mjs:16` | `PARITY OK — 66 vectors`; tamper→exit 1 |
| T0.10 selftest | `framework/selftest.py:45` | `SELFTEST PASS`, slopes 1.0/0.5, R²=1.0 |

### Notes / deviations
- **`_order_of_magnitude` uses `round(log10)` not `floor`** (§8 AC-T0.6 expects `~1e9` for 3.5e8 T-count;
  floor gives `~1e8`). Nearest-order-of-magnitude is the documented, honest reading. `resources.py:52`.
- **`fit()` gained `kind="subset"` keyword** (OQ-1, as planned) so the ordering diagnostic warning is possible.
- **Ledger seeded** with only the `_3sat_reference` row (OQ-3); the five problem rows are `EXPECTED_IDS` and
  render greyed "pending" until T1 appends them.
- **`node` present** (v24), so the parity assert runs live now (not deferred to T2).

### Follow-ups for the developer
- T1 supplies each problem's `instance.py` (KIND + cost + QUBO) and appends its real ledger row via
  `framework.ledger.append_row`; the map + `ledger.md` regenerate from it. Nothing in T0 needs re-touching.
- T2 vendors `web/lib/grover_count.js` verbatim and wires `tools/parity_check.py` into the Next build as a
  fail-on-mismatch step. **Never hand-edit the vendored JS** — regenerate from `grover_min.py`.
