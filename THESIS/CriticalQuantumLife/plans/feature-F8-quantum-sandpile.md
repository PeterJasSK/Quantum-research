# Feature Plan — F8: The Quantum Sandpile — self-organized absorbing-state criticality on a QPU

**Status:** Draft
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

- **AC-F8.1** A **per-step dynamic-circuit builder** on a W-site chain: (a) one brick-wall 2q
  entangling layer (spread); (b) mid-circuit measure every site + feed-forward conditional reset
  toward `|0⟩` (dissipate); (c) **drive-when-quiet** — if global activity `A = 0`, feed-forward one
  grain (`X`/`Ry`) on one site, else nothing. Built with Qiskit dynamic-circuit primitives
  (`if_test`), runnable on Aer's dynamic simulator.
- **AC-F8.2** A **trajectory runner** executes T steps, records the per-step, per-site activity
  time-series (from the mid-circuit records) and the injected-grain events, to
  `research_runs/sandpile_*.json`.
- **AC-F8.3** A **yoked-drive control**: inject grains at the *same average rate* but at *random
  times regardless of quiescence*. Prediction (the whole claim): drive-when-quiet self-tunes to
  criticality; yoked random drive does not.
- **AC-F8.4** **DP analysis** over the activity series: activity density self-parks at a nonzero
  steady value; avalanche size-distribution `P(S) ∝ S^{−α}` with α ≈ 1.5; branching σ → 1. Reuses/
  adapts `criticality.py` (`_fit_xmin`, `estimate_sigma`, `collect_avalanches`) to the site-activity
  substrate.
- **AC-F8.5** **Quantum certification** at the self-organized steady state: the genealogical witness
  `⟨X^⊗W⟩` (or a cluster witness) over the active cluster sits above the classical measure-and-resend
  null (reuse F3 null band).
- **AC-F8.6** **Tiered budget configs** (LEAP §10.7): a 10-min go/no-go (1 width, closed vs 2–3 yoked
  points, existence + contrast), a 30-min single-size decisive config (avalanche + σ + witness), and a
  180-min full config (3 widths for finite-size scaling, error mitigation, ≥5 seeds). Each is a named
  preset in the batch harness.
- **AC-F8.7** A **hardware batch harness** reusing `hardware_batches.py` (chain picker, calibration
  recording, manual submission) that emits the per-step dynamic circuits for a chosen tier; Aer
  dynamic-sim go/no-go is mandatory before any hardware submission (epic §3, sim-first).

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
- **Dynamic-circuit per-shot cost + queue time** → tiers are QPU-execution estimates, not wall-clock.
  Mitigation: calibrate against one small timed dynamic-circuit job before committing an allocation.
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
