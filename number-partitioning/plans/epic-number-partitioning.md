# Epic: Teleport-routed Number Partitioning (SK) QAOA on heavy-hex

**Slug:** number-partitioning
**Tickets:** F1, F2 (2)
**Author:** Claude (Opus)
**Date:** 2026-08-26
**Status:** Approved
**Project root:** `number-partitioning/` (repo root); plans in `number-partitioning/plans/`,
new code in `number-partitioning/array/`, run JSONs in `number-partitioning/research_runs/`.
**Source idea:** `study-ideas/qh-13-np-problems-teleport-routing.md`
**Builds on:** `QuantumLife/research/conclusion_teleportation_longrange.md` (reuses
`QuantumLife/code` primitives — does not copy them)

## 1. Why this epic exists

The QuantumLife teleport study established a **constant-depth long-range CNOT** on real
IBM heavy-hex silicon (`ibm_marrakesh`, Heron r2): a teleported CX (Bell pair + 2
mid-circuit measures + feed-forward) delivers a correct-signed, crosstalk-immune
correlation at depth 9, where the logically-equivalent SWAP ladder costs depth 31 and
grows O(distance). That primitive is reusable, but so far it only drove an evolving-genome
tree — not a recognized optimization problem.

Idea qh-13 maps every named NP-hard problem by interaction-graph density × heavy-hex
hardware status and finds one clean, unclaimed, maximal-payoff target: **fully-connected
Number Partitioning / Sherrington–Kirkpatrick QAOA**. Objective `H = A(Σᵢ nᵢ sᵢ)²`
expands to a coupling `2A·nᵢnⱼ` for *every* pair — a complete graph Kₙ where **every** QAOA
cost-layer edge is long-range. That makes teleport-vs-SWAP contrast maximal, and because
every bitstring is a valid partition (no one-hot, no penalty ancillas, no infeasible
states), routing is the *only* variable between arms. It is the purest teleport-vs-SWAP
stress test that exists, and no heavy-hex hardware result exists for it (only a
market-split cousin).

User-visible outcome: a proof-of-concept that builds the SK QAOA cost layer two ways
(teleport-routed vs SWAP-routed) and shows the depth advantage, plus a web demo that makes
the routing contrast and the honest noise verdict legible to a non-specialist.

## 2. Tickets in this epic

| ID | Title | State | One-line summary |
|----|-------|-------|------------------|
| F1 | SK QAOA proof of concept — teleport vs SWAP cost layer | open | Build a small-n SK number-partitioning QAOA, route the ZZ cost layer via `_teleport_cx` and `_swap_cx`, compare depth + approximation ratio on noiseless sim (then optionally one HW run). |
| F2 | Evaluate results + build web demo | open | Aggregate F1 runs into the honest verdict (depth win, does approx-ratio survive MCM noise?), build a web demo visualizing complete-graph routing and the teleport-vs-SWAP contrast. |

## 3. Cross-cutting decisions

Decisions made once for the whole epic; each `/plan-feature` must respect them.

- **Reuse, do not reinvent the primitive.** Route the QAOA cost layer with the *existing*
  `_teleport_cx` (`QuantumLife/code/research_qtree_teleport.py`) and `_swap_cx`
  (`QuantumLife/code/research_qtree_swaplr.py`). Only the QAOA cost/mixer layer over an SK
  QUBO is new — do not rewrite the teleport/SWAP machinery.
- **Problem = pure SK number partitioning.** `sᵢ ∈ {±1}`, objective `A(Σ nᵢ sᵢ)²`, cost
  coupling `2A·nᵢnⱼ` on complete graph Kₙ. No slack bits, no one-hot, no penalty ancillas.
  Keep this the clean case — deliberately NOT knapsack/TSP (those are later, out of scope).
- **Scale is parametrized.** `n` (spins) and QAOA depth `p` are CLI/function parameters, not
  hardcoded — default small (n≈8–12, p=1) so the first demo/run is cheap and the exact
  optimum is classically computable, but exposed so the study scales up later without a
  rewrite. Push the demo first, then scale.
- **Two arms, one difference.** Both arms apply the *same logical* ZZ cost layer on the same
  input; the only difference is how the long-range ZZ is routed. Mirror the teleport study's
  discipline: any sign/magnitude difference between arms is a routing/noise effect, not a
  logic difference — verify on noiseless sim first (Aer supports dynamic circuits).
- **Verdict is either-way.** Per idea §4, teleport may LOSE to SWAP on fidelity even while
  winning on depth (many teleported gates → many noisy MCMs on a complete graph). Report the
  honest outcome; the either-way result IS the contribution. Do not pre-commit to "teleport
  wins."
- **Run artifacts** follow the repo convention: JSON run files under
  `number-partitioning/research_runs/`, named by arm/backend/timestamp.
- **QAOA depth `p`** defaults to 1 for the proof of concept (single cost + mixer layer) but
  is a parameter (see scale note above); keep the routing contrast, not QAOA tuning, as the
  headline.
- **Hardware runs are manual.** F1 code emits the circuits + run harness; the **user submits
  to QC by hand and drops run JSONs into `research_runs/`**, exactly as in the QuantumLife
  teleport study. No automated backend submission in this epic.

## 4. Shared data model / artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| SK instance generator (fixed seed, n numbers) | F1 | F2 |
| `number-partitioning/array/qaoa_sk.py` cost-layer builder (teleport + SWAP arms) | F1 | F2 |
| Per-arm run JSON (depth, approx ratio, energy hist) in `number-partitioning/research_runs/` | F1 | F2 |
| Depth-vs-n table (`qc.depth()`, deterministic, zero QC) | F1 | F2 web demo |

## 5. Metrics / what "advantage" means

- **Depth** — `qc.depth()` of the compiled cost layer, teleport (constant) vs SWAP
  (O(distance)). Deterministic, no QC needed. This is the defensible win (mirrors §6c of the
  teleport conclusion).
- **Approximation ratio** — ⟨best sampled partition energy⟩ / exact optimum, on noiseless
  sim first, then optionally one HW run on a current Heron backend.
- **Noise survival (the open question)** — does teleport's approx ratio beat SWAP's *net of*
  mid-circuit-measurement noise on a dense (complete-graph) problem? Either answer is
  publishable.

## 6. Hardware / backend considerations

- Noiseless Aer simulation is the gate for correctness and the sign check BEFORE any QC time
  (dynamic circuits supported in Aer).
- HW runs are **in scope and manual** — user submits circuits to QC and returns run JSONs.
  Note live calibration (2q err, readout err, dead qubits) in each run JSON as the teleport
  study did. Prior QDEP finding: on modern Heron, readout error can dominate 2q error —
  teleport's MCM-heavy routing may be penalized. Flag, don't hide.
- Noiseless sim is the correctness/sign gate that runs BEFORE the manual HW submission.

## 7. Implementation order

1. **F1 first** — it produces every artifact F2 consumes. Within F1: (a) SK instance +
   classical optimum, (b) QAOA cost/mixer layer, (c) wire teleport arm, (d) wire SWAP arm,
   (e) noiseless sim compare depth + approx ratio, (f) optional single HW run.
2. **F2 second** — depends entirely on F1's run JSONs and depth table. Cannot start the
   evaluation writeup until F1 has runs, but the web-demo scaffold can be stubbed in parallel.

## 8. Open questions (epic-wide) — RESOLVED

- [x] Q1: Project root = `number-partitioning/` at repo root, with `plans/`, `code/`,
  `research_runs/` under it. Reuses `QuantumLife/code` primitives by import, not copy.
- [x] Q2: Real-hardware runs **in scope** for F1, performed **manually by the user** (same
  workflow as the QuantumLife teleport study — code emits the circuits/run harness, user
  submits to QC and drops the run JSONs into `research_runs/`). Noiseless sim still runs first
  as the correctness/sign gate.
- [x] Q3: Web demo (F2) = **DNSPoisonRace "web spectacle" style** (first-class interactive
  demo, not a static report). Mirror the DNSPoisonRace/ web treatment.
- [x] Q4: `n` (spins) and QAOA depth `p` are **parameters**, not fixed constants — default
  small for the first demo, but exposed so the study can scale up later. Push the demo, then
  scale.

## 9. Per-feature briefs

### F1 — SK QAOA proof of concept — teleport vs SWAP cost layer
- **What it delivers:** A runnable script that builds a small SK number-partitioning QAOA
  (n=8–12), constructs the ZZ cost layer over the complete graph Kₙ, routes it two ways
  (teleport vs SWAP), and compares depth and approximation ratio on a noiseless simulator.
  Establishes the depth win and the first honest approx-ratio read.
- **Acceptance criteria:**
  - AC-F1.1 Generate a fixed-seed SK instance of `n` numbers (`n` a parameter) and compute
    its exact equal-sum-partition optimum classically (for the approximation ratio).
  - AC-F1.2 Build the QAOA cost layer `H = A(Σ nᵢ sᵢ)²` → `2A·nᵢnⱼ` ZZ couplings on the
    complete graph Kₙ, plus a standard transverse-field mixer, at parametrized depth `p`
    (default 1). Both `n` and `p` are exposed parameters.
  - AC-F1.3 Route the cost layer's long-range ZZ terms via the existing `_teleport_cx`
    (teleport arm) and via `_swap_cx` (SWAP arm) — same logical layer, routing is the only
    difference.
  - AC-F1.4 Report `qc.depth()` for both arms across n (or across bond distance) — show
    teleport constant vs SWAP O(distance). Deterministic, no QC.
  - AC-F1.5 Run both arms on a noiseless Aer simulator (dynamic circuits) and report the
    approximation ratio; confirm both arms are same-sign / logically equivalent ideally
    (the sign-check discipline from the teleport study §4b).
  - AC-F1.6 Real-hardware run(s) on a current Heron backend, **submitted manually by the
    user** (code emits circuits + run harness; user runs on QC), calibration recorded in the
    run JSON.
  - AC-F1.7 Persist run outputs as JSON under `number-partitioning/research_runs/`.
- **Likely files / areas affected:** new `number-partitioning/array/qaoa_sk.py`; imports
  `QuantumLife/code/research_qtree_teleport.py::_teleport_cx` and
  `research_qtree_swaplr.py::_swap_cx`; writes `number-partitioning/research_runs/`.
- **Depends on:** none.
- **Conventions to follow:** mirror the arm/control structure and run-JSON schema of
  `research_qtree_teleport.py` / `research_qtree_swaplr.py`; keep the teleport study's
  noiseless-sim-first, sign-check-before-claims discipline.
- **Out of scope:** knapsack / TSP / any other problem in the qh-13 map; penalty ancillas;
  QAOA hyperparameter tuning beyond what's needed to show the routing contrast; multi-p
  optimization.

### F2 — Evaluate results + build web demo
- **What it delivers:** An evaluation of F1's runs into the honest verdict (depth advantage;
  does the approximation ratio survive MCM noise on a complete graph?), and a web demo that
  visualizes the complete-graph routing problem and the teleport-vs-SWAP contrast for a
  general audience.
- **Acceptance criteria:**
  - AC-F2.1 Aggregate F1 run JSONs into a short results writeup: depth table, approx-ratio
    comparison, and the either-way noise verdict (teleport depth win vs SWAP fidelity).
  - AC-F2.2 State the defensible claim precisely (constant-depth long-range routing on a
    guaranteed-dense problem) and the honest limitation (net-of-noise outcome), mirroring the
    teleport conclusion's claim/anti-claim discipline.
  - AC-F2.3 Build a **DNSPoisonRace-style web spectacle** under `number-partitioning/web/`
    (first-class interactive demo, not a static report) visualizing: the complete graph Kₙ,
    why every edge is long-range on heavy-hex, and the depth curve (teleport flat vs SWAP
    rising). `n`/`p` adjustable so the demo scales when the study does.
  - AC-F2.4 The demo surfaces the headline numbers from F1 (depth win, approx ratios) and
    the honest verdict — spectacle presentation, honest content, not a hype page.
- **Likely files / areas affected:** `number-partitioning/plans/` (results writeup),
  `number-partitioning/web/` (demo), reads `number-partitioning/research_runs/`.
- **Depends on:** F1 (needs its run JSONs and depth table).
- **Conventions to follow:** web demo mirrors the **DNSPoisonRace/ web spectacle** treatment;
  keep the writeup in the same honest, claim/anti-claim voice as
  `research/conclusion_teleportation_longrange.md`.
- **Out of scope:** any new hardware runs (uses F1's); other NP problems; a general QAOA
  playground.
