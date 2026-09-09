# Feature Plan — F8: The Quantum Sandpile — self-organized absorbing-state criticality on a QPU

**Status:** Complete (build) · **Sim verdict: KILL — do not run QC** (see §14; honest-negative, closed arm subcritical, worsens with width)
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F8 (post-LEAP deliverable; see `plans/LEAP-candidates-ranked.md` §10 + §11.8)
**Author:** Claude (Opus) · **Date:** 2026-09-06
**Depends on:** F0 (engine idioms), F2 (avalanche/σ analysis), F3 (null band), F5 (chain picker + batch harness). All landed.

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.
> **The decisive ~2-hour science swing** — the self-tuned counterpart to the *hand-tuned* absorbing-state
> transition of arXiv:2512.07966 / IBM 2509.18259. **This is the study that fixes the failed criticality
> gate (Run-1 σ=0.44):** SOC reaches criticality *by design* (slow-drive + fast-dissipation, Dickman et
> al. 1998) instead of by luck.

---

## 1. Context & goal

Recent hardware experiments observe measurement-induced absorbing-state / directed-percolation (DP)
criticality by **hand-tuning the measurement rate p** (p = 0.10 → 0.35 → 0.45 in 2512.07966, 30
qubits; IBM 2509.18259 at 100 qubits). Nobody has added the **drive-when-quiet feedback loop** that
makes the processor **self-organize** to that critical point with no fine-tuning. That self-tuning is
the entire identity of CriticalQuantumLife.

The Sandpile turns a monitored circuit into a sandpile — grains = quanta of activity, toppling =
measurement-induced relaxation — that self-parks at the critical slope. Per time-step on a W≈20–30
chain:
1. **Spread** — one brick-wall layer of 2-qubit entangling gates (activity spreads to neighbors).
2. **Dissipate** — mid-circuit measure each site + feed-forward **conditional reset toward `|0⟩`**
   (the absorbing/"dead" state). The fast relaxation.
3. **Drive-when-quiet (the SOC trick)** — read global activity `A` (non-`|0⟩` sites) from the
   mid-circuit record; **if `A = 0`, inject exactly one grain** (feed-forward `X`/`Ry` on one site);
   **else nothing.** No measurement rate is set by hand.
4. Repeat for T steps; log the activity time-series.

**Headline if it works:** *first self-organized (self-tuned) absorbing-state critical point on a
quantum processor, certified quantum.*

### What already exists (integration points — verified in code)
- `code/criticality.py` — `estimate_sigma`, `collect_avalanches`, `_fit_xmin` (α power-law MLE + KS
  goodness-of-fit), Beggs–Plenz / BTW metric definitions. **Currently fits σ/α on the
  surprise-activity process from `research_runs/*.json`** — must be adapted to the per-site
  occupation/activity time-series.
- `code/certify.py` — null band `k/√shots`, witness-vs-surrogate margin.
- `code/hardware_batches.py` — `layout.best_chain` picker, live calibration recording, manual IBM
  submission pipeline.
- `code/closed_loop.py` — genome/witness idioms + `run_counts` (Aer path).
- **Does NOT exist (the real build):** any dynamic-circuit machinery. `build_generation`
  (`closed_loop.py:205`) emits one static circuit with terminal `measure_all()` and a
  `--death=unitary` σ_y stand-in. There are **zero** `if_test` / `c_if` / mid-circuit `measure` /
  `reset` primitives anywhere in `code/`. So the Sandpile is **not** "the existing engine with a
  different rule" (as LEAP §10.6/§11.8 loosely imply) — it is a genuinely new dynamic-circuit builder.

### Honest scoping note (load-bearing)
The mechanism *requires* real dynamic circuits: per-step mid-circuit measurement, real-time
feed-forward conditional reset, and a conditional grain-injection gated on live activity. Qiskit
supports this (`if_test` / dynamic circuits) and Heron runs it, but per-shot cost is higher (each
step carries a mid-circuit measure + feed-forward, ~hundreds of ns–µs latency each). The build is the
cost, not the physics.

---

## 2. Acceptance criteria

Author-defined (LEAP §10.2–§10.4 / §11.8). IDs added; each maps to a manual check in §8.

- **[x] AC-F8.1** A **per-step dynamic-circuit builder** on a W-site chain: (a) one brick-wall 2q
  entangling layer (spread); (b) mid-circuit measure every site + feed-forward conditional reset
  toward `|0⟩` (dissipate); (c) **drive-when-quiet** — if global activity `A = 0`, feed-forward one
  grain (`X`/`Ry`) on one site, else nothing. Built with Qiskit dynamic-circuit primitives
  (`if_test`), runnable on Aer's dynamic simulator.
  **Covered by:** `code/sandpile.py:105` `build_step` (brick-wall `rxx`/`ryy`, per-site
  `qc.measure`, `with qc.if_test((creg[i],1)): qc.reset(...)`, drive `with qc.if_test((creg,0))`);
  `code/sandpile.py:141` `build_trajectory` (one ClassicalRegister per step). Verified on Aer
  (W=8 smoke run: all four primitives execute).
- **[x] AC-F8.2** A **trajectory runner** executes T steps, records the per-step, per-site activity
  time-series (from the mid-circuit records) and the injected-grain events, to
  `research_runs/sandpile_*.json`.
  **Covered by:** `code/sandpile.py:191` `run_trajectory` + `:209` `assemble_run` (`steps[]` with
  `activity_sites`/`A`/`density`/`grain_injected`/`grain_site` + per-shot `trajectories`) + `:305`
  `write_run`.
- **[x] AC-F8.3** A **yoked-drive control**: inject grains at the *same average rate* but at *random
  times regardless of quiescence*. Prediction (the whole claim): drive-when-quiet self-tunes to
  criticality; yoked random drive does not.
  **Covered by:** `code/sandpile.py:94` `yoked_schedule` (matched-rate random times) +
  `:105` `build_step` `mode="yoked"` (unconditional fire, no `if_test`) + `:250`
  `measured_drive_rate` (matches energy); contrast in `code/sandpile_analysis.py:186`
  `compare_closed_vs_yoked` (`self_organized`).
- **[x] AC-F8.4** **DP analysis** over the activity series: activity density self-parks at a nonzero
  steady value; avalanche size-distribution `P(S) ∝ S^{−α}` with α ≈ 1.5; branching σ → 1. Reuses/
  adapts `criticality.py` (`_fit_xmin`, `estimate_sigma`, `collect_avalanches`) to the site-activity
  substrate.
  **Covered by:** `code/sandpile_analysis.py:89` `activity_density`, `:112` `branching_sigma`
  (wraps `crit.estimate_sigma`), `:134` `avalanches` + `:156` `fit_alpha` (wraps
  `crit.fit_powerlaw`/`_fit_xmin`), `:216` `finite_size_scaling`.
- **[x] AC-F8.5** **Quantum certification** at the self-organized steady state: the genealogical witness
  `⟨X^⊗W⟩` (or a cluster witness) over the active cluster sits above the classical measure-and-resend
  null (reuse F3 null band).
  **Covered by:** `code/sandpile.py:263` `build_cluster_witness` (central sub-block, Q2) + `:282`
  `witness_trajectory` (X-basis parity) + `code/sandpile_analysis.py:165` `certify_steady_state`
  (reuses `certify.null_band`); wired into `code/sandpile_batches.py:166` `signcheck` for witness
  tiers.
- **[x] AC-F8.6** **Tiered budget configs** (LEAP §10.7): a 10-min go/no-go (1 width, closed vs 2–3 yoked
  points, existence + contrast), a 30-min single-size decisive config (avalanche + σ + witness), and a
  180-min full config (3 widths for finite-size scaling, error mitigation, ≥5 seeds). Each is a named
  preset in the batch harness.
  **Covered by:** `code/sandpile_batches.py` `TIERS` (`verify`/`10min`/`30min`/`180min`) +
  `circuit_specs` + `budget_estimate` (**shot-count arithmetic**, no time/rate model). Budgets in
  `plans/SANDPILE-runlog.md`.
- **[x] AC-F8.7** A **hardware batch harness** reusing `hardware_batches.py` (chain picker, calibration
  recording, manual submission) that emits the per-step dynamic circuits for a chosen tier; Aer
  dynamic-sim go/no-go is mandatory before any hardware submission (epic §3, sim-first).
  **Covered by:** `code/sandpile_batches.py:207` `emit` (reuses `hb.gated_chain_with_stats` +
  `hb.connect`, transpiles to QPY, writes submit bundle, STOPS) + `:166` `signcheck` (mandatory
  Aer go/no-go) + `:313` `ingest`. Run recipe: `plans/SANDPILE-runlog.md`.

---

## 3. Scope

### In scope
- New `code/sandpile.py` (dynamic-circuit builder + trajectory runner + yoked-drive control).
- New `code/sandpile_analysis.py` (DP order-parameter analysis over the activity series; adapts
  `criticality.py`).
- New `code/sandpile_batches.py` (tiered presets + hardware harness reusing `hardware_batches.py`).
- New `research_runs/sandpile_*.json` artifacts.
- Aer dynamic-simulator validation of the full mechanism before hardware.

### Out of scope
- The web spectacle (F6/F7 surface); a Sandpile view is a later add-on.
- The thesis writeup (F9 per §10 Q1) — this ticket produces runs + figures data, not prose.
- Automated QC submission (manual per epic §3).
- Full finite-size-scaling universality claim without the 180-min tier actually being run — the code
  supports it; the *claim* waits on the run.

---

## 4. Data model / artifacts

`research_runs/sandpile_<session>.json`:
```
{ backend, W, T, arm: "closed"|"yoked", tier, seed, chain, calibration:{twoq_err,readout_err},
  steps: [ { t, activity_sites:[0/1 per site], A, grain_injected:bool, grain_site }... ],
  witness: { joint, separable, signal, null_band, margin },   # at steady state
  analysis: { density, sigma, alpha, alpha_ks, n_avalanches } }
```
Same field vocabulary as F0/F2 run-JSON where possible so `criticality.py` tooling reads it. All
`strict_types`-clean, full type hints.

---

## 5. File plan

**`code/sandpile.py`** (new — the real build)
- `def build_step(width, chain, mode) -> QuantumCircuit` — one time-step as a dynamic circuit:
  brick-wall 2q layer → per-site mid-circuit `measure` into a classical register → `if_test`
  feed-forward conditional `reset`/X toward `|0⟩` → drive-when-quiet: `if_test` on the OR of the
  activity register (`A==0`) applying one grain. `mode="closed"` gates the grain on quiescence;
  `mode="yoked"` injects on a precomputed random schedule at matched rate.
- `def run_trajectory(width, T, mode, backend, seed) -> dict` — assemble T steps (or re-submit
  step-by-step for hardware feed-forward), run on Aer dynamic sim or a hardware sampler, extract the
  per-step activity series + grain events, return the run dict.
- `def yoked_schedule(T, rate, seed) -> list[int]` — matched-rate random injection times.
- Reuses `layout.best_chain`, `closed_loop.run_counts` (Aer), F3 witness/null.

**`code/sandpile_analysis.py`** (new)
- `def activity_density(steps) -> float`, `def branching_sigma(steps) -> dict` (adapt
  `criticality.estimate_sigma` to site-activity), `def avalanches(steps) -> list[float]` +
  `def fit_alpha(sizes) -> dict` (reuse `criticality._fit_xmin`).
- `def certify_steady_state(run) -> dict` — witness margin above F3 null over the active cluster.
- `def compare_closed_vs_yoked(closed, yoked) -> dict` — the decisive contrast (AC-F8.3).
- `def finite_size_scaling(runs_by_width) -> dict` — DP exponents (z≈1.58, β) across widths (180-min
  tier).

**`code/sandpile_batches.py`** (new)
- `TIERS = {"10min": ..., "30min": ..., "180min": ...}` — width(s), T, shots, seeds, error-mitigation
  flags per LEAP §10.7 table.
- `def emit_batch(tier) -> None` — build the dynamic circuits for the tier, run the Aer go/no-go, and
  emit hardware-submission artifacts via `hardware_batches.py` (chain picker + calibration recording).
  Manual submission thereafter.

**`research_runs/`** — `sandpile_*.json` (data only).

---

## 6. Implementation steps (order)

1. `sandpile.py::build_step` — the dynamic-circuit step; verify on Aer dynamic sim that mid-circuit
   measure + feed-forward reset + drive-when-quiet all execute.
2. `sandpile.py::run_trajectory` + `yoked_schedule` — full T-step trajectory, both arms, on Aer.
3. `sandpile_analysis.py` — density, σ, avalanche α, witness certification, closed-vs-yoked contrast.
4. `sandpile_batches.py` — the three tiered presets; wire the Aer go/no-go + `hardware_batches.py`
   emission.
5. Run the **10-min-tier Aer go/no-go**: does closed self-park at nonzero density while yoked does
   not? This is the internal gate before any Heron time (epic §3, sim-first; mirrors the F1 kill-gate
   discipline).

---

## 7. Conventions
- `strict_types`-clean Python, full type hints; reuse the F0/F2 run-JSON vocabulary so
  `criticality.py` reads Sandpile output.
- Reuse, don't reimplement: chain picker (`layout`), calibration recording + submission
  (`hardware_batches.py`), null band (`certify.py`), α/σ fits (`criticality.py`).
- Cite Dickman–Muñoz–Vespignani–Zapperi 1998 (cond-mat/9712115), Front. Phys. 8:333 (2020), and the
  tuned-transition baselines (2512.07966, 2509.18259) up front — position explicitly as the
  *self-organized counterpart*.
- Honesty-gates-are-law: the criticality claim traces to σ→1 + α≈1.5 + the yoked-drive contrast;
  the quantum claim to the witness above the F3 null. A single subcritical run does not establish SOC.

---

## 8. Manual verification
- **AC-F8.1/2:** run one trajectory on Aer dynamic sim; confirm the per-step activity series records
  mid-circuit measures, feed-forward resets, and quiescence-triggered grain injections.
- **AC-F8.3:** run closed vs yoked at one width; confirm closed self-parks at nonzero density and
  yoked does not (the decisive contrast).
- **AC-F8.4:** run the analysis; confirm activity density is nonzero-steady, avalanche α ≈ 1.5 (with
  KS goodness-of-fit), σ → 1.
- **AC-F8.5:** confirm the steady-state witness margin sits above the F3 null band.
- **AC-F8.6/7:** confirm each tier preset emits the right circuit count/width/T and that the 10-min
  Aer go/no-go runs end-to-end before any hardware artifact is emitted.

---

## 9. Risks
- **NISQ noise adds uncontrolled dissipation** → pile pushed subcritical (the Run-1 failure mode).
  Mitigation: small W to keep depth low; the SOC loop self-corrects (dies → reseeds; saturates →
  dissipation wins); light sweep of grain size / relaxation strength if density sits off-critical.
- **Dynamic-circuit per-shot cost + queue time** → budgets are counted in **shots**, not wall-clock;
  the shot total is exact, but the QPU-seconds those shots take (per-step feed-forward latency) and
  device queue are not modelled. Mitigation: Run log 1's verify pass (24,000 shots) runs the real
  circuits on Heron cheaply first — it exposes any per-shot-cost surprise before the full-shot spend.
- **Witness weak at critical density** → lead the physics claim with the DP avalanche/σ result; report
  the witness as margin-above-null (certification layer), not the headline.
- **Feed-forward support / transpilation** on the target Heron backend may constrain the step
  structure. Mitigation: validate the dynamic-circuit build on Aer dynamic sim + a 1-step hardware
  smoke job first.

---

## 10. Open questions — RESOLVED
- [x] **Q1 — Ticket numbering.** F7 = Canary, F8 = Sandpile. Thesis synthesis is stripped of its
  number and shelved (numberless, assembled only after everything is built + validated). Epic §2
  updated.
- [x] **Q2 — Witness form at W≈20–30.** Certify a **cluster/sub-block witness** over the active
  cluster, not the full-chain product (the full `⟨X^⊗W⟩` died at W=32 in artificial-life).
- [x] **Q3 — Feed-forward vs re-submission.** In-circuit dynamic feed-forward for spread/dissipate/
  drive within a step; if the backend limits step depth, batch a few steps per submission with
  persisted classical state between jobs (reuse F4 `session.py`).
- [x] **Q4 — First run tier.** Build + validate all three tiers on Aer, then run the **10-min
  go/no-go on hardware first**; spend the 180-min allocation only if the cheap tier says yes.

---

## 13. Post-implementation

**Built (2026-09-08).** Three new files, all `strict_types`-clean (`from __future__ import
annotations`, full type hints), matching the F0/F2/F5 module shape and run-JSON idioms:

- `code/sandpile.py` — the genuinely new dynamic-circuit builder (`build_step`: brick-wall XX+YY
  hopping → per-site mid-circuit `measure` → feed-forward conditional `reset` on a fixed relaxation
  mask → drive-when-quiet `if_test((creg,0))`). `build_trajectory` assembles T steps (one
  ClassicalRegister per step). `run_trajectory`/`assemble_run` extract the per-shot A(t) trajectories
  (Aer `memory=True`) + the per-step ensemble series. `yoked_schedule` + `measured_drive_rate` give
  the matched-rate control. `build_cluster_witness`/`witness_trajectory` are the AC-F8.5 cluster
  witness.
- `code/sandpile_analysis.py` — DP order parameter over the activity series: `activity_density`,
  `branching_sigma` (wraps `criticality.estimate_sigma`), `avalanches`+`fit_alpha` (wraps
  `criticality.fit_powerlaw`/`_fit_xmin`), `certify_steady_state` (wraps `certify.null_band`),
  `compare_closed_vs_yoked` (the decisive `self_organized` verdict), `finite_size_scaling`.
- `code/sandpile_batches.py` — the three LEAP tiers as `TIERS` presets, `budget_estimate` (the
  execution-time arithmetic the run log quotes), `signcheck` (mandatory Aer go/no-go, incl. the
  witness cert on witness tiers), `emit` (reuses `hardware_batches.gated_chain_with_stats` + `connect`,
  QPY + submit bundle, STOPS), `ingest` (per-shot memory → run-JSON), `analyze` (DP report + FSS).
- `plans/SANDPILE-runlog.md` — the three **connected** run logs, budgeted in **shots** (no
  time/rate arithmetic): Run log 1 (`--tier verify`, 6 circuits × 4000 = 24,000 shots, does-it-work
  eyeball), Run log 2 (`--tier 10min`, same 6 circuits × 8192 = 49,152 shots, go/no-go), Run log 3
  (`--tier 180min`, 170 circuits × 8192 × 3 ZNE = 4,177,920 shots). The logs chain: the `verify`
  tier's six circuits are the `10min` tier's, re-emitted at full shots once the eyeball passes.

**Verified (Aer, manual, no automated tests).** The dynamic circuit executes end-to-end on Aer's
dynamic simulator (W=8 smoke: `if_test` + mid-circuit `measure` + `reset` + drive-when-quiet all
run). Closed self-parks at a stable **nonzero** density; the matched yoked arm parks at a different
density — the decisive contrast (AC-F8.3) is present and in the predicted direction. Default
`SPREAD_THETA=1.20`, `RELAX_P=0.35` chosen so closed parks nonzero without over-driving.

**Both-basins convergence (added post-review — the load-bearing self-organization test).** A
self-organized critical point must be an ATTRACTOR reached from either side (Dickman et al.), so a
`hot` (saturated/chaotic) start was added alongside the `cold` (empty) start: `sandpile.py:141`
`build_trajectory(..., init)` (X on every qubit for `hot`), `sandpile_analysis.py` `convergence`
(cold-rises + hot-falls to the same density/σ ⇒ `converged`). `signcheck` now runs the hot basin and
gates GO on `self_organized AND converged`; the 30-/180-min tiers emit both `closed-cold` and
`closed-hot` (`both_sides`), and `analyze` reports per-config `convergence`. This closes the
"only the frozen side" gap: the yoked contrast proves the drive *contingency* matters; the
cold/hot convergence proves the critical point is a genuine attractor, not an initial-condition
artefact. (Cost: 180-min tier grows 125 → 170 circuits, ≈102 → ≈139 min, still inside 180.)

**Follow-ups for the developer.**
1. **Live runs deferred by directive** — no QC and no further sim runs were executed after the
   builder smoke test (developer said "no live runs, only write run log"). Before hardware, run
   `python sandpile_batches.py signcheck --tier 10min` and confirm GO (now = self-organized **and**
   both-basins converged; epic §3, AC-F8.7). It is wired and ready; it was not executed here.
2. **Per-shot memory is required** on submission — A(t) is reconstructed from per-shot per-step
   registers. `ingest --memory` expects one JSON of shot bitstrings per trajectory circuit. The
   generic `submit_batch.py` returns aggregated counts; a memory-returning submit is the one piece of
   hardware plumbing to confirm before Run log 2.
3. **Density is on the low side** (~0.06 at the toy W=8) — the fixed relaxation is strongly
   dissipative. The tiers include the grain-size × relaxation-strength robustness sweep (180-min) to
   find a healthier self-organized density if it sits off-critical (plan §9 mitigation).
4. **Witness hardware ingest is thin** — `certify_steady_state` runs on Aer inside `signcheck`; the
   full hardware witness path (memory → parity for the emitted witness QPY) mirrors the trajectory
   ingest but is not separately wired into `analyze` yet.

---

## 14. Sim verdict — KILL (this mechanism does not self-organize; do NOT run QC)

**Status of this try: DEAD on noiseless simulation. No hardware run is warranted.** The Aer
`signcheck` kill-gate (AC-F8.7, epic §3 sim-first) returned **NO-GO**, and a full root-cause
investigation on the dynamic simulator shows the failure is in the **mechanism**, not in the
hyperparameters or the shot budget. Because Aer is noiseless, this is the most favourable possible
test — real Heron adds *uncontrolled dissipation* that can only push the pile **further** subcritical
(plan §9, §1). A mechanism that will not self-organize on a perfect simulator cannot be rescued by
running it on hardware. The 24,000-shot verify pass (Run log 1) is therefore **cancelled**; spending
it would only re-confirm subcriticality at cost.

This section records exactly what was measured and why it kills the try, so the negative is fully
documented from simulation alone and no QPU time is needed to reach it.

### 14.1 The gate result that triggered the investigation

Default build (`SPREAD_THETA=1.20`, `RELAX_P=0.35`, `GRAIN_SIZE=1`), smoke config W=8, T=40,
2048 shots, seed 100:

| arm | density ρ | branching σ |
|---|---|---|
| closed (drive-when-quiet) | 0.097 | **0.721** |
| yoked (matched-rate random) | 0.247 | 1.114 |

`converged = True` (both basins meet), but `self_organized = NO`. The gate's `self_organized`
predicate is `closed parks nonzero AND |σ_closed − 1| ≤ |σ_yoked − 1|`. Here the closed arm parks
**subcritical** (σ=0.72, well below the critical σ=1), and the yoked control sits *closer* to 1
(distance 0.114 vs 0.279). The decisive AC-F8.3 contrast fails in the σ channel — the same failure
mode as Run-1 (σ=0.44), the very thing this study was designed to fix "by design."

### 14.2 Root cause — the closed arm is structurally subcritical

Four sweeps on the dynamic simulator (seed 100, W=8 unless noted) isolate the cause. Raw tables in
§14.5.

1. **`RELAX_P` (dissipation) is not a lever.** Across the band relax_p ∈ [0.15, 0.40] at θ=1.35, the
   closed branching ratio moved only 0.72 → 0.83 — never near 1. Density stayed pinned ≈ 0.10.

2. **`SPREAD_THETA` (branching) is not a lever either.** Pushing the hopping angle all the way to
   π/2 (maximal XX+YY spread) at relax_p=0.20 left closed σ at **0.78** — flat. The entangling
   strength does not lift the closed arm toward criticality.

3. **A real bug was found and fixed in grain injection.** `build_step` applied `GRAIN_SIZE` X gates
   to the **same** qubit (`for _ in range(GRAIN_SIZE): qc.x(qr[drive_site])`). Since X·X = I, every
   *even* `GRAIN_SIZE` injected **nothing**, and odd values injected exactly one grain — so the
   plan's grain-size robustness axis (§9, {1,2}) was inert. Fixed at `sandpile.py:128-139` to spread
   grains over `GRAIN_SIZE` **distinct** sites (contiguous block from `drive_site`, wrapping). After
   the fix, injected mass is real: steady density now responds to grain size (0.10 → 0.18 → 0.29 as
   grain 1 → 3 → 5). **But closed σ still did not rise** — it stayed in the band 0.62–0.79 across
   every (grain, relax_p) combination tested. The lever moves *density*, not the *branching ratio*.

4. **The only GO observed is a criterion artifact, not self-organization.** One config
   (grain=5, relax_p=0.25) flipped `self_organized = True` — but not because the closed arm reached
   criticality. Closed σ there was **0.777 (still subcritical)**; the predicate passed only because
   the **yoked** control over-drove to σ=1.55, making closed "nearer 1" than an exploded control.
   That is the gate passing for the wrong reason, and it is non-robust: 1 of 6 neighbouring configs.
   Shipping it would be exactly the fine-tuned-knife-edge result the §7 honesty gate forbids.

### 14.3 The decisive test — width trend refutes the finite-size rescue

The last hypothesis that could have saved the try: the W=8 smoke is simply too small, and the closed
arm reaches σ→1 at the hardware width (W≈14). This was tested directly at one fixed config
(grain=3, relax_p=0.30, θ=1.35):

| W | closed σ | closed density |
|---|---|---|
| 8 | 0.837 | 0.163 |
| 10 | 0.719 | 0.147 |
| 12 | **0.621** | 0.113 |

**Closed σ decreases monotonically with width** — it moves *away* from criticality, not toward it,
and extrapolates to ≈0.55 at the hardware width W=14. The finite-size rescue is **refuted**: larger
systems are *more* subcritical, so hardware width would make the result worse, not better.

### 14.4 Why it fails — the drive does not scale with system size

The physics is now unambiguous and explains every number above. The 1998 Dickman–Muñoz–Vespignani–
Zapperi result (cond-mat/9712115) that this study invoked guarantees self-organization to the
absorbing-state critical point **only in the slow-drive / fast-dissipation limit** — it requires a
genuine *separation of timescales*, drive rate → 0 relative to relaxation. This circuit does not sit
in that limit:

- **Dissipation scales with the system:** every site is measured and conditionally reset **every
  step**, so total dissipation is O(W) per step and grows with width.
- **Drive does not scale:** a fixed handful of grains (1, later up to 5) is injected **only on full
  quiescence** (A==0). As W grows, the same weak drive is spread over a larger volume that dissipates
  faster, so the *relative* drive weakens — hence σ falling with W.

The drive-when-quiet loop, as built with a fixed-size grain and an all-sites-every-step relaxation,
**underdrives at scale**. It never establishes the timescale separation the Dickman theorem needs, so
the theorem's guarantee never applies. The LEAP §10 framing ("repairs Run-1 by design… expected
behavior") over-trusted the theorem to transfer to this discrete construction; it does not. The
critical-point attractor exists (both-basins `converged=True` throughout — the pile does relax to a
*single* self-consistent set-point from either side), but that set-point is **subcritical** (σ≈0.6–0.8),
not the critical σ=1. It is a genuine self-organized *absorbing-phase* fixed point, just on the wrong
side of the transition.

### 14.5 The measured data (simulation, self-contained — no QC needed)

All runs: Aer dynamic simulator, seed 100, drive-when-quiet closed arm vs matched-rate yoked, plus a
hot-start basin for convergence. `margin = |σ_yoked−1| − |σ_closed−1|` (positive ⇒ closed nearer 1).

**Sweep A — `RELAX_P` band (θ=1.35, grain=1[pre-fix], W=8, T=30, 512 shots):**
```
relax |   σ_c    σ_y  |  ρ_c    ρ_y  | margin | conv | self-org
0.15  |  0.833  1.078 | 0.108  0.318 | -0.089 | True | NO
0.20  |  0.817  1.082 | 0.107  0.258 | -0.101 | True | NO
0.25  |  0.806  1.072 | 0.106  0.303 | -0.123 | True | NO
0.30  |  0.725  1.094 | 0.098  0.286 | -0.181 | True | NO
0.35  |  0.720  1.093 | 0.099  0.251 | -0.186 | True | NO
```

**Sweep B — `SPREAD_THETA` lever (relax_p=0.20, grain=1[pre-fix], W=8, T=25, 256 shots):**
```
theta |   σ_c    σ_y  |  ρ_c    ρ_y  | margin | conv | self-org
1.45  |  0.781  1.037 | 0.104  0.300 | -0.183 | True | NO
1.55  |  0.779  0.855 | 0.104  0.269 | -0.076 | True | NO
π/2   |  0.778  0.844 | 0.104  0.260 | -0.066 | True | NO
```

**Sweep C — grain size × relax, AFTER the distinct-site fix (θ=1.35, W=8, T=25, 256 shots):**
```
grain relax |   σ_c    σ_y  |  ρ_c    ρ_y  | margin | conv | self-org
  1   0.25  |  0.788  1.103 | 0.102  0.268 | -0.109 | True | NO
  1   0.40  |  0.694  1.163 | 0.092  0.167 | -0.143 | True | NO
  3   0.25  |  0.759  1.178 | 0.179  0.403 | -0.063 | True | NO
  3   0.40  |  0.722  1.238 | 0.202  0.372 | -0.040 | True | NO
  5   0.25  |  0.777  1.552 | 0.254  0.446 | +0.329 | True | YES*  (*artifact: yoked overdrove; σ_c still 0.78)
  5   0.40  |  0.666  1.154 | 0.292  0.465 | -0.179 | True | NO
```

**Sweep D — width trend (grain=3, relax_p=0.30, θ=1.35, T=20, 128 shots):**
```
 W  |   σ_c    σ_y  |  ρ_c    ρ_y  | margin | conv | self-org
 8  |  0.837  1.229 | 0.163  0.347 | +0.066 | True | YES*  (*artifact, as above)
10  |  0.719  1.274 | 0.147  0.320 | -0.007 | True | NO
12  |  0.621  1.028 | 0.113  0.359 | -0.351 | True | NO
```

**Robustness caveat (honest).** Sweeps C/D are lean smoke (128–256 shots, T=20–25), so the absolute
σ values carry noise. The *conclusion* does not rest on any single number: closed σ never approached
1 in **any** of the ~20 configs across four independent sweeps (observed band 0.62–0.84), and the
width trend is monotone and large (0.84 → 0.62). The direction is robust; only the second decimal is
noisy. The single `self_organized=YES` cell in each of C and D is the same artifact — yoked
over-driving past σ=1 — not the closed arm reaching criticality.

### 14.6 Reproduce (all on the free Aer simulator — no hardware)

```bash
cd THESIS/CriticalQuantumLife/code
python sandpile_batches.py signcheck --tier verify          # the NO-GO gate (§14.1)
# root-cause sweeps are in scratchpad (sweep.py / sweep2.py / sweep4.py / sweep5.py);
# each monkeypatches sandpile.SPREAD_THETA / RELAX_P / GRAIN_SIZE and reruns closed+yoked+hot.
```

### 14.7 What would be required to revive it (a NEW study, not this ticket)

The absorbing-state / DP analysis suite, the yoked control, the both-basins convergence test, the
cluster witness, and the whole dynamic-circuit harness are **correct and reusable** — the negative is
about the *drive rule*, nothing else. To reach σ=1 the drive must be made to hold the Dickman
timescale separation as W grows, e.g.:

- **Scale the drive with the system** — inject grains ∝ W (or ∝ dissipated mass) when quiet, so the
  drive keeps pace with O(W) dissipation instead of falling behind it; or
- **Drive-when-low, not only drive-when-empty** — fire on A ≤ θ_low·W (a size-scaled quiescence
  threshold) rather than strictly A==0, restoring a nonzero steady drive at scale; or
- **Weaken dissipation to a sub-extensive schedule** — relax a *fixed number* of sites per step
  rather than a fixed *fraction*, so dissipation stops scaling with W.

Each of these **changes the mechanism** and therefore the SOC claim, so it must be re-gated from
scratch (new `signcheck` GO on sim) — it is a fresh study, not a parameter change to F8. Per the §7
honesty gate, none of it may be back-fitted to the current run to manufacture a positive.

### 14.8 Decision

**This F8 try is closed as a documented honest-negative.** The deliverable is the negative itself:
*a drive-when-quiet absorbing-state loop with fixed-grain drive and extensive (all-sites-every-step)
dissipation self-organizes to a single set-point from both basins, but that set-point is subcritical
(σ≈0.6–0.8) and grows more subcritical with width, because the drive does not scale with the system
and so never enters the slow-drive limit the Dickman self-organization theorem requires.* This is a
sharper, mechanism-level result than Run-1's bare σ=0.44, and it is established entirely from
noiseless simulation. **No QC run is required or justified.**
