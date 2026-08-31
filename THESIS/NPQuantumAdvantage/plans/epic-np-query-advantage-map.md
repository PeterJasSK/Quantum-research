# Epic: The Quantum Query-Advantage Map — five forgotten NP-complete problems, brute force vs Grover, and the classical hunt that decides each verdict

**Slug:** np-query-advantage-map
**Tickets:** F0, F1, F2, F3, F4, F5, F6, F7, F8 (9)
**Author:** Claude (Opus)
**Date:** 2026-08-31
**Status:** Approved
**Project root:** `THESIS/NPQuantumAdvantage/` — plans in `plans/`, shared code in `framework/`,
per-problem code in `problems/p<k>_<name>/`, run/ledger artifacts in `research_runs/`, web
spectacle in `web/`. POC already lives in `proof_of_concept/` (the survives-mechanism, end to end).
**Source idea:** `study-ideas/thesis-4-obscure-np-query-advantage.md`
**POC:** `proof_of_concept/` (3-SAT survives-case, hardware-run on `ibm_kingston`, 51.9% vs 6.2% floor)
**Builds on:** `number-partitioning/` (QUBO/QAOA swapnet, `classical_reference.py`, `research_runs/`)
for the hardware arm; honest successor to `study-ideas/qh-13` (drops its refuted teleport premise).

> No GitHub issues, no test suite — repo directive. "Tickets" F0–F8 are author-defined research
> deliverables. Acceptance criteria are author-defined (not verbatim-from-issue). Each ticket is
> picked up with `/plan-feature plans/epic-np-query-advantage-map.md` naming the F-id.

---

## 1. Why this epic exists

There is exactly one honest way to say "quantum advantage on an NP-complete problem," and it is a
**theorem, not a benchmark**: Dürr–Høyer minimum-finding on Grover solves the optimization version
of *any* NP-complete problem in Θ(2^{n/2}) cost-oracle calls, and BBBV (1997) proves that quadratic
speedup is **optimal in the query model** — unconditional, independent of P vs NP. That part is
undeniable. The catch that turns it into research: the quadratic speedup only beats the *best known
classical algorithm* when the best known classical algorithm is **itself brute force**. For famous
problems it isn't (number partitioning: classical meet-in-the-middle already runs Õ(2^{n/2}) → the
advantage is *erased*). So the question nobody has answered systematically is: **for which problems
does the provable quadratic query advantage survive the best classical algorithm, and for which does
it collapse to brute-force-only?**

This epic is that map. We take **five 1970s NP-complete problems with essentially zero quantum
literature**, and for each we build two files — a **brute-force classical solver** and an
**optimized quantum solver** (Grover / Dürr–Høyer) — count oracle calls to demonstrate the theorem,
then do the real work: **actively hunt for a classical algorithm that beats the quantum one.** If we
find one, that problem *collapses*. If nobody has one and we can argue none is known, it *survives*.
The mixed answer — some survive, some collapse — **is** the result. This is exactly the shape the
user asked for: old, forgotten hard problems, re-examined with a revolutionary tool (Grover's
provably-optimal query speedup), and an honest, systematic ledger of where that tool genuinely wins.

The framing that keeps it "undeniable" while staying novel: the **undeniable** part is the
query-model theorem (we prove it up front by counting, for all five). The **novel** part is the
survive/collapse map — the per-problem best-known-classical homework nobody did. A uniform
"all five show quantum advantage" would be a red flag and an overclaim; the map with teeth (real
survivors *and* real collapses) is the defensible, citable contribution.

User-visible outcome: five problem folders, each with a `classical_bruteforce.py` and a
`quantum_grover.py` that print the oracle-call gap; a single survive/collapse ledger + exponent
table; and a **TargetedDos-style web spectacle** that walks a non-specialist through every problem,
shows the brute-force vs Grover call counts recomputed live in the browser, and makes visible *why*
quantum is better where it is — and honestly, where it isn't.

## 2. Tickets in this epic

| ID | Title | State | One-line summary |
|----|-------|-------|------------------|
| F0 | Systemic framework & claim-discipline harness | open | Shared oracle-call counter, Dürr–Høyer/Grover query-count engine, brute-force template, exponent fitter, fault-tolerant resource estimator, and the machine-readable survive/collapse ledger schema every problem appends to. Built once, reused by all five. |
| F1 | P1 — Betweenness (Total Ordering) | open | Definition + citation + QUBO map; `classical_bruteforce.py` + `quantum_grover.py`; best-known-classical hunt → survive/collapse verdict. Ordering-encoding problem; likely SURVIVES. |
| F2 | P2 — Numerical Matching with Target Sums | open | Same two-file contract; reuses the number-partitioning sum-to-target penalty verbatim (POC-proven). Strongly NP-complete; strongest "buildable + likely SURVIVES." |
| F3 | P3 — Quadratic Congruences | open | Same contract; HUBO/quartic map needs quadratization ancillas. Highest **collapse** risk (number theory has clever algorithms) — kept expressly as an honest collapse case. |
| F4 | P4 — Kernel of a Digraph | open | Same contract; sparse/local QUBO, best hardware fit; cleanest obscurity (zero prior quantum work). Feasibility problem recast as constraint-violation minimization. |
| F5 | P5 — Minimum Linear Arrangement (MinLA) | open | Same contract; one-hot position encoding (shares with P1). Likely **COLLAPSES** (known 2^n·poly Held–Karp DP) — the clean collapse contrast that proves the map has teeth. |
| F6 | Survive/collapse map + best-classical synthesis | open | Cross-problem: pin each best-known-classical exponent, classify SURVIVES/COLLAPSES, produce the map figure + exponent table (the thesis's single figure). Consumes every problem's verdict row. |
| F7 | Hardware feasibility arm (optional, obstruction-labeled) | open | Per-problem QUBO/Ising → fixed-depth QAOA on the number-partitioning swapnet; approximation ratio vs matched classical local baseline. Presented as feasibility + Farhi–Gamarnik–Gutmann locality obstruction — **never** as the advantage. Manual QC submission. |
| F8 | Web spectacle — the systemic visual | open | TargetedDos-style Next.js static-export app: scenes-in-sequence walking every problem, brute-force vs Grover call counts recomputed **live in-browser** from a vendored JS mirror of F0's counter, the survive/collapse map, and the honest "where quantum does NOT win" scene. |

## 3. Cross-cutting decisions

Decisions made once for the whole epic. Every `/plan-feature` output must respect them.

- **CLAIM DISCIPLINE IS LOCKED (the spine of the whole epic).** Four qualifiers attach to every
  advantage statement, no exceptions: **query model · over brute force · quadratic · not wall-clock.**
  - CAN say: "BBBV-optimal quadratic quantum *query* speedup over brute force, shown by oracle-count
    on all five" (theorem, always true). "On the *k of 5* whose best-known-classical is exhaustive,
    a provable advantage over the *best known* method" (true after the homework). "A map of *where*
    the advantage survives vs collapses."
  - CANNOT say: "I ran them on a quantum computer and beat classical" (false on NISQ; the QAOA arm
    likely *loses*). "I systematically verified quantum advantage" (unqualified → reads as beating
    best classical everywhere → false). A hardware run presented as the advantage proof.
  - The user's word "undeniable" maps ONLY to the query-model theorem. The map is what is *novel*;
    the theorem is what is *undeniable*. Do not let the web spectacle (F8) or any writeup blur these.
- **Two-file-per-problem contract (the user's core ask).** Every problem folder ships exactly two
  headline runnable files with the SAME names across all five (mirrors the POC):
  - `classical_bruteforce.py` — exhaustive solver/verifier, wraps the shared oracle counter, prints
    call count = 2^n and the O(2^n) scaling.
  - `quantum_grover.py` — Dürr–Høyer/Grover-minimum, wraps the shared oracle counter, prints call
    count ≈ 1.3·2^{n/2}, the speedup factor, and (Aer arm) amplifies the marked/optimal state above
    the 1/2^n floor. Runnable on Aer sim and, via `--backend`, on real IBM hardware (feasibility).
  - A third file `best_classical.py` (+ `verdict.md`) is the *hunt*: implements/benchmarks the
    best-known classical exponential algorithm and emits the survive/collapse verdict row. This is
    where "we try to find a classical solution that beats the quantum" lives, per problem.
- **Query-count is the primary quantum measurement, NOT statevector.** The theorem lives in the
  query model. `quantum_grover.py` demonstrates it by *counting* Dürr–Høyer's expected oracle calls
  over an ideal Grover subroutine (the `~1.3·2^{n/2}` accounting) — no 2^n-amplitude simulation
  needed for the scaling claim. A small-n (n ≤ ~14) real statevector/Aer Grover run is included as a
  *validation + amplification demo* (and the hardware feasibility hook), not as the scaling evidence.
- **Systemic, not five one-offs.** All five problems share ONE framework (F0): one oracle-counter,
  one Dürr–Høyer engine, one brute-force template, one exponent fitter, one resource estimator, one
  ledger. Adding problem N+1 = write its instance generator + cost oracle + QUBO map + best-classical
  analysis, and inherit everything else. The systemic uniformity is itself part of the contribution
  (identical theorem machinery across all five isolates the *only* variable that matters: the
  classical baseline).
- **The ledger is the single source of truth.** One machine-readable file
  (`research_runs/ledger.json` + rendered `ledger.md`) with one row per problem: name, 1970s
  citation, fitted classical exponent, fitted quantum exponent, best-known-classical exponent + its
  source, verdict ∈ {SURVIVES, COLLAPSES, UNKNOWN}, fault-tolerant qubit/T-count. F6 renders the map
  from this file; F8 reads it. No verdict lives anywhere else.
- **Reuse the number-partitioning codebase for the hardware arm; do not reinvent QUBO/QAOA.** F7
  imports the swapnet + `classical_reference.py` from `number-partitioning/`. P2 reuses its
  sum-to-target penalty almost verbatim.
- **Instance generators are fixed-seed and CLI-parametrized** (`n`, seed). Default small so the
  brute-force optimum is computable and the demo is cheap; exposed so sweeps scale without a rewrite.
- **Hardware runs are manual** (same workflow as number-partitioning / QuantumLife): code emits
  circuits + harness, the **user submits to QC by hand** and drops run JSONs into `research_runs/`.
  Record live calibration (2q err, readout err) in each run JSON. No automated backend submission.
- **Web spectacle is first-class (F8), TargetedDos style.** Next.js App Router + TypeScript + Tailwind
  v4, `output: 'export'` → static `web/out/` (no server runtime, GitHub-Pages/offline runnable).
  The browser recomputes the brute-force vs Grover call counts from a **vendored JS mirror of F0's
  counter** (build-time parity assert against the Python source of truth — the TargetedDos D-parity
  discipline), so the demo is a reproducibility artefact, not a hype page.

## 4. Shared data model / artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| `framework/oracle.py` — call-counting oracle wrapper (decorator + tally) | F0 | F1–F5 (both files each) |
| `framework/grover_min.py` — ideal Dürr–Høyer query-count engine (`~1.3·2^{n/2}` accounting) | F0 | F1–F5 `quantum_grover.py` |
| `framework/bruteforce.py` — generic exhaustive-search template | F0 | F1–F5 `classical_bruteforce.py` |
| `framework/fit.py` — log2-axis exponent fitter (slope ≈1.0 classical, ≈0.5 quantum) | F0 | F1–F5, F6 |
| `framework/resources.py` — fault-tolerant qubit/T-count estimator | F0 | F1–F5, F6 |
| `framework/ledger.py` — survive/collapse ledger schema + append/render | F0 | F1–F5 (append), F6+F8 (read) |
| Per-problem instance generator (fixed seed) | F1–F5 | that problem's files, F7 |
| Per-problem cost oracle | F1–F5 | that problem's two files, F7 QUBO |
| Per-problem QUBO/Ising map | F1–F5 | F7 hardware arm |
| Per-problem `verdict.md` + ledger row | F1–F5 | F6 |
| `research_runs/ledger.json` (+ `ledger.md`) — the map's data | F1–F6 | F6 figure, F8 scenes |
| Vendored `web/lib/grover_count.js` — JS mirror of F0's counter (parity-asserted) | F0 → F8 | F8 browser scenes |

## 5. Metrics / what "advantage" means

- **Fitted oracle-call exponent vs n** — classical slope ≈1.0, quantum ≈0.5 on a log2 axis. This is
  the theorem, demonstrated identically for all five. (Primary, query-model, deterministic.)
- **Per-problem best-known-classical exponent** — *the number the whole map turns on.* Survive if
  best-known-classical ≈ 2^n (quantum beats best classical); collapse if a known algorithm ≤ 2^{n/2}.
- **Survive/collapse verdict per problem** — {SURVIVES, COLLAPSES, UNKNOWN}. The headline figure.
- **Fault-tolerant resource estimate** — logical qubits + T-count per problem (honest cost of the
  advantage; makes explicit it is not a NISQ wall-clock claim).
- **(F7, feasibility only)** QAOA approximation ratio vs matched classical local baseline — reported
  as feasibility + locality obstruction, never as advantage.

## 6. Hardware / backend considerations

- **Sim-first.** The entire advantage claim (F0–F6) is query-count + resource estimate in simulation.
  No QC needed for the headline. The POC already showed the hardware *feasibility* side (Grover
  amplification above floor on `ibm_kingston`).
- **F7 hardware arm is optional and manual** — QUBO → fixed-depth QAOA on a current Heron backend,
  user-submitted. Prior QDEP finding: on modern Heron readout error can dominate 2q error, so QAOA
  likely *loses* wall-clock — flag it, it is the obstruction result, not a hole.
- **The optional statevector Grover runs (small n)** validate the query-count accounting and double
  as the amplification demo; they are not the scaling evidence.

## 7. Implementation order

1. **F0 first** — nothing else can start without the shared harness (oracle counter, DH engine,
   brute-force template, fitter, ledger schema, resource estimator). It also emits the JS mirror F8
   vendors, so F0 fixes the parity contract early.
2. **F2 second** (P2 Numerical Matching) — reuses the number-partitioning sum-to-target penalty and
   is the POC-proven survives-shape; it is the cheapest first problem and validates F0 end to end.
3. **F1, F3, F4, F5 in any order / parallel** — each is independent once F0 + F2 have shaken out the
   framework. Suggested pairing per the idea: **P1+P5 together** (shared one-hot ordering encoding),
   **P3 alone** (HUBO/quadratization build risk), **P4 alone** (sparse/local, easiest hardware).
4. **F6 after all five verdict rows exist** — it only synthesizes; cannot render the map until the
   ledger is populated. (Its figure scaffold can be stubbed against a partial ledger in parallel.)
5. **F7 optional, after any single problem's QUBO map lands** — independent of the map; can run
   alongside F6. Deliberately last in priority (feasibility, not the thesis).
6. **F8 after F0 (for the JS mirror) + at least F2's verdict** — the spectacle scaffold and one
   real scene can be built early; remaining scenes fill in as F1/F3/F4/F5 land. Reads the ledger, so
   it auto-updates as verdicts arrive.

## 8. Open questions (epic-wide) — RESOLVED

- [x] **Q1 — Project layout.** Root `THESIS/NPQuantumAdvantage/` with `framework/`,
  `problems/p<k>_<name>/`, `research_runs/`, `web/`; POC left in place. **Confirmed.**
- [x] **Q2 — The five problems.** Locked: P1 Betweenness · P2 Numerical Matching · P3 Quadratic
  Congruences · P4 Kernel of a Digraph · P5 MinLA. **No 3-Partition warm-up** — the five obscure
  problems only.
- [x] **Q3 — Best-classical hunt bar.** **Tier (b) for all five** — implement + benchmark the
  best-known classical exponential algorithm head to head for every problem (not just literature-cite).
  Tier (c) (attempt to invent a sub-2^{n/2} algorithm) is opportunistic, not required — if a survivor
  invites it, take it, but the epic's bar is (b) across the board.
- [x] **Q4 — `quantum_grover.py` scope.** **Both** — query-count accounting for the scaling claim +
  a small-n statevector/Aer Grover amplification demo (and hardware hook), matching the POC.
- [x] **Q5 — F7 hardware arm.** **Scaffold F7 now, defer actual QC submission** until the map (F6)
  is done. Headline needs zero QC.
- [x] **Q6 — Deliverable.** **Both** — F8 web spectacle is the primary public artefact, IEEE 6–8pp
  short paper is the thesis document.
- [x] **Q7 — Web spectacle stack.** **Mirror TargetedDos exactly** — Next 16 + React 19 + Tailwind v4,
  static export, vendored parity JS.

## 9. Per-feature briefs

### F0 — Systemic framework & claim-discipline harness
- **What it delivers:** The shared, reused-by-all-five machinery: a call-counting oracle wrapper, an
  ideal Dürr–Høyer/Grover-minimum query-count engine, a generic brute-force template, a log2-axis
  exponent fitter, a fault-tolerant resource estimator, and the survive/collapse ledger schema. Plus
  the JS mirror of the counter that F8 vendors, with a build-time parity assert. This is what makes
  the study *systemic* rather than five disconnected scripts.
- **Acceptance criteria:**
  - AC-F0.1 `framework/oracle.py` — an oracle wrapper (decorator or class) that tallies every call
    to a cost/verifier function; resettable per run; the single counter both files of every problem use.
  - AC-F0.2 `framework/grover_min.py` — Dürr–Høyer control loop over an *ideal* Grover subroutine
    that returns the expected oracle-call count `~1.3·2^{n/2}` for M marked items (query-model
    accounting; no statevector). Exposes a function usable by every `quantum_grover.py`.
  - AC-F0.3 `framework/bruteforce.py` — generic exhaustive-search template that enumerates the 2^n
    space through the F0.1 counter and returns the optimum + call count = 2^n.
  - AC-F0.4 `framework/fit.py` — fit oracle-calls-vs-n on a log2 axis; return the slope (expect ≈1.0
    classical, ≈0.5 quantum) and R².
  - AC-F0.5 `framework/resources.py` — a documented fault-tolerant estimator: given oracle qubit
    width + gate depth, report logical qubits and T-count order for the Grover arm.
  - AC-F0.6 `framework/ledger.py` — schema + append/read/render for `research_runs/ledger.json`
    (fields per §3 ledger) and a Markdown renderer `ledger.md`.
  - AC-F0.7 `web/lib/grover_count.js` — a JS mirror of the F0.1/F0.2 counting logic, plus a
    parity check (Python vs JS produce identical call counts on shared vectors) runnable at build time.
- **Likely files / areas affected:** new `framework/`; `research_runs/ledger.json`;
  `web/lib/grover_count.js`.
- **Depends on:** none.
- **Conventions to follow:** mirror the POC's `classical_bruteforce.py` / `quantum_grover.py` output
  style (search space, marked states, call counts, speedup factor); the ledger + parity discipline
  mirror TargetedDos P2's shared-vector parity.
- **Out of scope:** any specific problem's oracle or QUBO (those live in F1–F5); full statevector
  Grover (problems opt into small-n statevector themselves).

### F1 — P1 Betweenness (Total Ordering)
- **What it delivers:** The Betweenness problem end to end: definition + citation + QUBO map, the two
  headline files, and the best-classical hunt → verdict.
- **Definition:** Given triples (a,b,c) over a set, find a total order placing b between a and c for
  as many triples as possible. *Opatrný, SIAM J. Comput. 8(1):111–114, 1979 (G&J [MS1]).*
- **QUBO map:** one-hot position vars x_{i,p}; per-triple degree-2 reward on the induced-order sign +
  permutation penalties; medium density. (Shares the one-hot ordering encoding with P5 — build together.)
- **Expected verdict:** likely **SURVIVES** — check for a sub-2^n ordering DP; APX-hard, frustrated
  random-triple hard regime. Best all-round shape.
- **Acceptance criteria:**
  - AC-F1.1 Fixed-seed instance generator (triples over n elements, `n` + seed CLI params).
  - AC-F1.2 Cost oracle = number of satisfied betweenness triples for a given ordering, wrapped in F0's counter.
  - AC-F1.3 `problems/p1_betweenness/classical_bruteforce.py` — exhaustive over orderings via F0's
    template; prints optimum + call count and O(2^n)/O(n!) scaling.
  - AC-F1.4 `problems/p1_betweenness/quantum_grover.py` — Dürr–Høyer query-count via F0's engine;
    prints `~1.3·2^{n/2}` call count, speedup factor, fitted exponent; optional small-n statevector
    Grover amplifying the best ordering above the uniform floor; `--backend` hardware feasibility hook.
  - AC-F1.5 `problems/p1_betweenness/best_classical.py` + `verdict.md` — implement/benchmark the
    best-known classical exponential algorithm; emit the survive/collapse verdict row to the ledger.
  - AC-F1.6 `problems/p1_betweenness/definition.md` — formal definition, 1970s citation (verified),
    QUBO map, expected vs measured verdict.
- **Likely files / areas affected:** `problems/p1_betweenness/`; appends `research_runs/ledger.json`.
- **Depends on:** F0. (Pairs with F5 on the shared ordering encoding.)
- **Conventions to follow:** F0 framework for both files; POC output style; verified citation before writeup.
- **Out of scope:** hardware QAOA (F7); the cross-problem map (F6).

### F2 — P2 Numerical Matching with Target Sums
- **What it delivers:** Same two-file + verdict contract, maximizing reuse of the number-partitioning
  penalty (POC-proven survives-shape). The recommended first problem after F0.
- **Definition:** Given X, Y, and targets, pair one X- and one Y-element per target so each pair hits
  its target sum. *Garey & Johnson, J. ACM 25(3):499–508, 1978 (G&J [SP17]; cite the JACM paper).*
- **QUBO map:** assignment vars + per-target sum-to-target penalty (Σ s·x − B)² — **the partition
  penalty per target, verbatim reuse**; block-structured medium density.
- **Expected verdict:** **strongly** NP-complete (no pseudo-poly, hard at small integers →
  hardware-friendly couplings); strongest "buildable + likely SURVIVES." Check for a meet-in-the-middle
  across the matching (the classical move that would collapse it).
- **Acceptance criteria:**
  - AC-F2.1 Fixed-seed instance generator (X/Y/targets, `n` + seed CLI params).
  - AC-F2.2 Cost oracle = Σ_targets (achieved_sum − target)² through F0's counter (reuses partition penalty).
  - AC-F2.3 `problems/p2_numerical_matching/classical_bruteforce.py` — exhaustive via F0's template.
  - AC-F2.4 `problems/p2_numerical_matching/quantum_grover.py` — Dürr–Høyer query-count + optional
    small-n statevector + `--backend` hook, per the F0 contract.
  - AC-F2.5 `best_classical.py` + `verdict.md` — best-known-classical hunt (meet-in-the-middle check)
    → ledger row.
  - AC-F2.6 `definition.md` — definition, verified JACM citation, QUBO map, verdict.
- **Likely files / areas affected:** `problems/p2_numerical_matching/`; ledger; imports the
  number-partitioning penalty.
- **Depends on:** F0. (Validates the framework end to end — do first among F1–F5.)
- **Conventions to follow:** reuse `number-partitioning/` sum-to-target penalty; POC style.
- **Out of scope:** F7 hardware; F6 map.

### F3 — P3 Quadratic Congruences
- **What it delivers:** Same contract, kept expressly as the **honest collapse** case.
- **Definition:** Does there exist integer x, 0<x<c, with x² ≡ a (mod b)? *Manders & Adleman,
  J. Comput. Syst. Sci. 16(2):168–184, 1978 (G&J [AN1]).*
- **QUBO map:** binary-expand x; penalty (x² − a − b·t)² — **quartic/HUBO, needs quadratization
  ancillas** (build risk); dense among the ~log c bits, large coefficients.
- **Expected verdict:** **highest collapse risk** — number theory is full of clever algorithms, so
  the best-classical check most likely demotes it to brute-force-only. High novelty; the deliberate
  collapse demonstration.
- **Acceptance criteria:**
  - AC-F3.1 Fixed-seed instance generator (a, b, c, `n`=bit-width + seed).
  - AC-F3.2 Cost oracle = |x² − a mod b| (or squared residual) through F0's counter.
  - AC-F3.3 `classical_bruteforce.py` — exhaustive over x via F0's template.
  - AC-F3.4 `quantum_grover.py` — Dürr–Høyer query-count + optional small-n statevector; document the
    HUBO→QUBO quadratization ancilla cost in the resource estimate.
  - AC-F3.5 `best_classical.py` + `verdict.md` — survey the number-theoretic classical algorithms
    (the likely collapse driver) → ledger row, explicitly framed as an honest collapse.
  - AC-F3.6 `definition.md` — definition, verified citation, HUBO map + quadratization note, verdict.
- **Likely files / areas affected:** `problems/p3_quadratic_congruences/`; ledger.
- **Depends on:** F0.
- **Conventions to follow:** F0 framework; be explicit about the quadratization ancilla overhead in
  `resources.py`.
- **Out of scope:** F7 hardware; F6 map.

### F4 — P4 Kernel of a Digraph
- **What it delivers:** Same contract; cleanest obscurity + best hardware fit.
- **Definition:** Find an independent, absorbing vertex set (kernel) of a digraph. *Chvátal, CRM-300
  tech report, Univ. Montréal, 1973 — cite carefully as a tech report; strengthened by Fraenkel,
  Discrete Appl. Math. 3(4):257–262, 1981 (planar, in/out-degree ≤ 2).*
- **QUBO map:** membership vars; independence penalty on intra-set arcs; per-vertex absorption
  penalty; **sparse/local → best hardware fit.** Feasibility problem recast as constraint-violation
  minimization.
- **Expected verdict:** cleanest obscurity (zero prior quantum work); check best-known-classical for
  kernel existence.
- **Acceptance criteria:**
  - AC-F4.1 Fixed-seed digraph generator (`n` vertices + edge density + seed).
  - AC-F4.2 Cost oracle = total constraint violations (independence + absorption) through F0's counter.
  - AC-F4.3 `classical_bruteforce.py` — exhaustive over vertex subsets via F0's template.
  - AC-F4.4 `quantum_grover.py` — Dürr–Høyer query-count + optional small-n statevector + `--backend`
    hook (best hardware fit — flag it for F7).
  - AC-F4.5 `best_classical.py` + `verdict.md` → ledger row.
  - AC-F4.6 `definition.md` — definition, careful tech-report citation, QUBO map, verdict.
- **Likely files / areas affected:** `problems/p4_kernel_digraph/`; ledger; flagged as F7's best target.
- **Depends on:** F0.
- **Conventions to follow:** F0 framework; careful citation (tech report, not journal).
- **Out of scope:** F7 hardware run itself; F6 map.

### F5 — P5 Minimum Linear Arrangement (MinLA)
- **What it delivers:** Same contract; the clean **collapse contrast** that proves the map has teeth.
- **Definition:** Place graph vertices on a line minimizing Σ_{(i,j)∈E} |pos(i) − pos(j)|.
  *Garey, Johnson & Stockmeyer, Theor. Comput. Sci. 1(3):237–267, 1976.*
- **QUBO map:** one-hot positions (shared with P1); tabulated |p−q| edge couplings; graph-structured
  medium density. (Build P1+P5 together on the shared ordering encoding.)
- **Expected verdict:** likely **COLLAPSES** — a known 2^n·poly Held–Karp-style DP means the honest
  verdict is probably advantage-over-brute-force-only. The deliberate collapse contrast.
- **Acceptance criteria:**
  - AC-F5.1 Fixed-seed graph generator (`n` vertices + density + seed).
  - AC-F5.2 Cost oracle = Σ_edges |pos(i)−pos(j)| for an arrangement, through F0's counter.
  - AC-F5.3 `classical_bruteforce.py` — exhaustive over arrangements via F0's template.
  - AC-F5.4 `quantum_grover.py` — Dürr–Høyer query-count + optional small-n statevector.
  - AC-F5.5 `best_classical.py` + `verdict.md` — implement/cite the Held–Karp-style 2^n·poly DP (the
    collapse driver) → ledger row.
  - AC-F5.6 `definition.md` — definition, verified citation, QUBO map, verdict.
- **Likely files / areas affected:** `problems/p5_minla/`; ledger; shares ordering encoding with P1.
- **Depends on:** F0. (Pairs with F1.)
- **Conventions to follow:** F0 framework; share the one-hot ordering encoding with P1.
- **Out of scope:** F7 hardware; F6 map.

### F6 — Survive/collapse map + best-classical synthesis
- **What it delivers:** The thesis's single figure. Cross-problem synthesis: pin each best-known-
  classical exponent, classify every problem SURVIVES/COLLAPSES/UNKNOWN, and render the map +
  exponent table from the ledger. This is where the five per-problem verdicts become *the result*.
- **Acceptance criteria:**
  - AC-F6.1 Read `research_runs/ledger.json`; validate every problem has classical exponent, quantum
    exponent, best-known-classical exponent + source, and a verdict.
  - AC-F6.2 Render the **survive/collapse map** figure (the headline) + the exponent table.
  - AC-F6.3 Write the synthesis note: which survive, which collapse, why, and the honest caveat that a
    thin/ambiguous classical literature yields UNKNOWN, not a forced verdict.
  - AC-F6.4 Sanity gate: assert the map has *both* survivors and collapses, or explicitly justify a
    uniform result (a uniform "all survive" is a red flag per the idea).
- **Likely files / areas affected:** `plans/` or `results/` synthesis note; the map figure; reads ledger.
- **Depends on:** F1–F5 (all verdict rows). Scaffold can stub against a partial ledger.
- **Conventions to follow:** the ledger is the only source of verdicts; claim discipline in the writeup.
- **Out of scope:** generating verdicts (that is each problem's job); hardware.

### F7 — Hardware feasibility arm (optional, obstruction-labeled)
- **What it delivers:** The honestly-labeled feasibility chapter: per-problem QUBO/Ising → fixed-depth
  QAOA on the number-partitioning swapnet, approximation ratio vs a matched classical local baseline.
  Presented as feasibility + the Farhi–Gamarnik–Gutmann locality obstruction — **never** as advantage.
- **Acceptance criteria:**
  - AC-F7.1 Convert one problem's QUBO (start with P4, the sparse/local best-fit) to an Ising QAOA
    circuit on the `number-partitioning/` swapnet.
  - AC-F7.2 Run fixed-depth QAOA on noiseless Aer (correctness/sign gate) and report approximation
    ratio vs a matched classical local/greedy baseline.
  - AC-F7.3 Optional manual hardware run on a current Heron backend (user-submitted), calibration
    recorded in the run JSON; expect QAOA to *lose* wall-clock (readout-error obstruction) — report it.
  - AC-F7.4 Label every output feasibility/obstruction, cite Farhi–Gamarnik–Gutmann 2020; never as
    the advantage.
- **Likely files / areas affected:** imports `number-partitioning/` swapnet + `classical_reference.py`;
  writes `research_runs/`.
- **Depends on:** F0 + at least one problem's QUBO map (F4 preferred). Independent of F6.
- **Conventions to follow:** number-partitioning run-JSON schema + manual-submission workflow;
  noiseless-sim-first, sign-check-before-claims.
- **Out of scope:** any claim that a hardware run demonstrates the advantage; automated QC submission.

### F8 — Web spectacle — the systemic visual (TargetedDos style)
- **What it delivers:** The primary public artefact: a Next.js static-export app that walks a
  non-specialist through *every* NP problem, shows brute-force vs Grover call counts recomputed **live
  in the browser** from the vendored JS mirror of F0's counter, renders the survive/collapse map from
  the ledger, and includes an honest "where quantum does NOT win" scene. Makes visible *how each
  problem works* and *why quantum is better where it is* — and honest where it isn't.
- **Acceptance criteria:**
  - AC-F8.1 Next.js App Router + TypeScript + Tailwind v4, `output: 'export'` → static `web/out/`
    (no server runtime; GitHub-Pages/offline runnable), mirroring the TargetedDos web stack.
  - AC-F8.2 **Scenes in sequence** — an intro (the theorem: quadratic query speedup, BBBV-optimal,
    with the four claim-discipline qualifiers on screen), then one scene per problem (P1–P5): plain-
    language definition, the instance, and a live brute-force-vs-Grover call-count widget.
  - AC-F8.3 The call-count widget recomputes 2^n vs ~1.3·2^{n/2} **in-browser** from
    `web/lib/grover_count.js` (F0's vendored mirror), with a build-time parity assert vs the Python
    counter (TargetedDos D-parity discipline) — the demo is a reproducibility artefact.
  - AC-F8.4 A **survive/collapse map scene** rendered from `research_runs/ledger.json`, auto-updating
    as verdicts land; each problem tagged SURVIVES/COLLAPSES/UNKNOWN with its exponents.
  - AC-F8.5 An explicit **honesty scene**: "where quantum does NOT win" — the collapses, the NISQ
    wall-clock caveat, the query-model-only scope. No hype; the honesty is the point.
  - AC-F8.6 Reads the same ledger F6 renders — one source of truth, web and paper agree by construction.
- **Likely files / areas affected:** `web/` (Next app), `web/lib/grover_count.js` (from F0), reads
  `research_runs/ledger.json`.
- **Depends on:** F0 (JS mirror + ledger schema) and ≥ F2 (one real verdict); remaining scenes fill
  in as F1/F3/F4/F5 land.
- **Conventions to follow:** mirror `TargetedDosColisionsAndRNGAngle/web/` exactly — Next static
  export, vendored parity artefact, scenes-in-sequence, first-class not supplementary.
- **Out of scope:** any live QC call from the browser; presenting the hardware arm as advantage.
```
