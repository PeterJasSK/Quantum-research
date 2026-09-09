# Feature Plan — F9: The Unified Quantum-Tree Canary — one decomposable health index, validated to track QPU health objectively over time and across fault scenarios

**Status:** Draft
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F9 (post-LEAP deliverable, sibling of F7 Canary / F8 Sandpile; author-defined, no GitHub issue)
**Author:** Claude (Opus) · **Date:** 2026-09-08
**Depends on:** F0 (engine: surprise/σ/witness machinery), F3 (null band), F7 (probe/exporter shell,
`fault_injection.py`, `calibration_poller.py`). All landed. Reuses the **QuantumTree** schematic
(`QuantumLife/code/qtree.py`, `genome.py`, `research_qtree_teleport.py`).

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.
> **Feasibility is validated first (§1.5) as an explicit gate, then the feature is built** — per the
> user directive "first validate this is feasible and then plan the feature."

---

## 1. Context & goal

F7 (the Quantum Canary) proved a **single entanglement-witness margin** can be an always-on QPU health
signal — but on a **static GHZ** circuit, and it *loses* to RB on 2q/readout faults (its own honest
coverage map: 3 wins / 2 loses). F8 (Sandpile) added dynamic-circuit criticality as separate physics.

F9 asks a different, sharper question, in the user's words: **build the ONE best canary — the single
best representation of overall QPU health — on the quantum-tree schematic (minimal qtree), measure
everything, and prove objectively that this one index tracks the real health of the device over time
and across scenarios.**

The move that makes this more than "F7 again":
- **Substrate = the quantum-tree schematic, minimal.** Reuse `qtree.py`'s `build_circuit` shape (RY
  belief-encode per bit → brick-wall CX/CRX neighbour chain → terminal genome measure) at a *minimal*
  slot count, **plus one heralded long-range teleport bond** (`research_qtree_teleport._teleport_cx`,
  herald mode). This one small circuit exercises encode + local entangle + long-range teleport +
  mid-circuit measure — the whole schematic in miniature.
- **Measure it all → one decomposable index.** From the single measured genome we read a *vector* of
  subsystem-sensitive observables (local correlation, long-range correlation, dynamic-circuit herald
  hit-rate, diversity, witness-vs-null margin, surprise/σ) and fold them into **one health index
  H ∈ [0,1]** that falls when *any* subsystem degrades — while every component stays in the record so
  the drop is always traceable to a subsystem.
- **Prove it tracks health objectively.** Two ground truths already exist: in **sim**, injected fault
  *magnitude* (`fault_injection.py`); on **hardware**, live calibration read at **zero credits**
  (`calibration_poller.py`). The headline result is a **rank correlation** between H and each ground
  truth across a fault menu and over a scripted time trajectory, shown to track **more fault types**
  than either the single F7 witness margin or an RB/coherence baseline.

### The one honest catch (load-bearing, designed around not hidden)
A single scalar can mask *which* subsystem failed. Therefore H is **never opaque**:
1. H is a **weighted geometric mean of normalized sub-signals** — geometric (not arithmetic) so a
   single component collapsing to ~0 drags H down (an "overall health" index must not let a healthy
   readout hide a dead entangler).
2. Every normalized component is emitted alongside H in the same record; any H drop decomposes to the
   responsible subsystem.
3. A **coverage map** reports where H tracks, ties, and is **blind** (a fault H misses) as prominently
   as wins. No speed/classical-hardness claim (mirrors AC-F7.7).

### What already exists (integration points — verified in code)
- `QuantumLife/code/qtree.py` — `build_circuit(theta, kick, env, layers, spec)` (`:146`): the tree
  schematic (RY encode `:156`, brick-wall `_entangle` CX+CRX `:166–172`, env/mutation bias, measure
  `:192`). Imports only `genome` + qiskit → **import-safe** (no submission pipeline).
- `QuantumLife/code/genome.py` — `GENOME_SPEC`, `decode_field`; a `spec` is a plain dict, so a
  **minimal spec** (fewer slots, angle-only) is constructed locally without editing genome.py.
- `QuantumLife/code/research_qtree_teleport.py` — `_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k,
  feedforward)` (`:201`) and `bond_correlations` (`:327`). **NOTE:** this module imports the heavy
  `pipeline_common`; F9 **copies** the ~15-line `_teleport_cx` herald helper with attribution instead
  of importing the module.
- `code/closed_loop.py` — `witness_gen` (`:131`), `outcome_key`/`surprise_nll`/`running_sigma`,
  `run_counts`, `DECAY`/`MUT_FLOOR`. Reused for the surprise/σ and null-band components.
- `code/fault_injection.py` — `Fault`, `noise_model` (`:54`), `FAULTS` (`:94`), `chain_quality`. The
  sim ground-truth generator; F9 adds two fault kinds (long-range/routing, dynamic-circuit/measure).
- `code/calibration_poller.py` — zero-credit live-calibration reader (2q err, readout, T1/T2, queue);
  the **hardware** ground-truth reference for the deferred hardware-tracking confirmation.
- `code/canary_exporter.py` — stdlib OpenMetrics endpoint + run-JSON writer; extended with the H gauge.
- **Does NOT exist:** any qtree-substrate probe, any composite health index, any objective-tracking
  (rank-correlation) study, any two new fault kinds. (grep-confirmed.)

### Honest scoping note
- **In scope:** the minimal-qtree canary circuit, the full observable vector, the one decomposable
  index H, the sim objective-tracking study (H vs witness vs RB baseline across a fault menu +
  magnitude sweep), a scripted time-trajectory trace, the coverage/blind-spot map, and the exporter +
  run-JSON wiring.
- **Deferred:** the **hardware** objective-tracking confirmation (correlate an H heartbeat against
  `calibration_poller` drift over repeated polls) — the harness is built and the free calibration side
  runs at zero credits, but the cost-side H heartbeat waits on a QC allocation window (mirrors F7's
  free/cost split).
- **Not claimed:** any quantum-advantage / classical-hardness / speed claim. H is a monitoring
  statistic, not a computational result.

---

## 1.5. Feasibility validation (the gate, done first)

Per the user directive, feasibility is settled before the build. Verdict: **FEASIBLE**, on four legs.

1. **An objective ground truth exists — twice.** Sim: `fault_injection.Fault` carries a magnitude, so
   a magnitude sweep gives a monotone severity axis to correlate against. Hardware: `calibration_poller`
   reads live 2q/readout/T1/T2 at **zero credits**, giving a real device-health axis over time without
   spending budget. "Objective tracking" is therefore a measurable Spearman ρ, not a subjective claim.
2. **The minimal-qtree substrate emits a genuinely multi-subsystem observable vector.** Local C0/xi
   (2q/entangler health), long-range heralded c(d) (deep-entanglement + routing, crosstalk-immune),
   herald hit-rate (mid-circuit-measure / feed-forward health), diversity (readout/decoherence
   balance), witness-vs-null margin (overall entanglement). One circuit, ≥4 distinct subsystems — the
   precondition for one index to represent *overall* health rather than one axis.
3. **A decomposable single index is definable and defensible.** Weighted geometric mean of
   healthy-normalized components ∈ [0,1]; drops on any subsystem collapse; every component retained.
4. **Cost is small and the honest risk is mitigated.** Sim stays cheap by using **per-shot
   Monte-Carlo noise (statevector), not `density_matrix`**, at ≤~16 qubits (minimal qtree = angle-only
   slots ≈6–7 + 1 teleport bond + 2 ancilla). The single-scalar-hides-subsystem risk is mitigated by
   decomposition + the blind-spot coverage map.

**Feasibility deliverable (AC-F9.0):** a one-shot sim sanity run — sweep a single fault's magnitude,
show H falls monotonically while the responsible component drops and the others hold — written to
`research_runs/qtree_canary_feasibility.json`. If H does **not** move monotonically with a clear
single-fault sweep, that is a documented no-go and the index design is revisited before AC-F9.4.

**Residual risks accepted (see §9):** Aer noise is a proxy for real hardware; a composite index is a
modelling choice, not a ground truth — both stated openly, both bounded by reporting the decomposition
and the blind spots.

---

## 2. Acceptance criteria

Author-defined (no GitHub issue). Each maps to a manual check in §8.

- [ ] **AC-F9.0 (feasibility gate).** A sim sanity run sweeps one fault's magnitude and demonstrates H
  falls monotonically while the responsible normalized component drops and unrelated components hold;
  written to `research_runs/qtree_canary_feasibility.json` with a printed verdict. A non-monotone
  result is a documented no-go that blocks AC-F9.4 until the index is fixed.
- [ ] **AC-F9.1 (minimal-qtree canary circuit).** A parametrized minimal quantum-tree generation
  circuit reusing the `qtree.py` schematic (RY belief-encode → brick-wall CX/CRX neighbour chain → env/
  mutation bias → terminal genome measure) at a small slot count (default: angle-only slots, ~6–7
  slots), **plus one heralded long-range teleport bond** (copied `_teleport_cx`, herald/post-select
  mode). One short circuit per cycle. Aer (per-shot noise) by default; a hardware backend streams
  counts. — `qtree_canary.py`.
- [ ] **AC-F9.2 (measure it all — one observable vector).** Per cycle, from the measured genome:
  local `C0`, correlation length `xi`, per-bond long-range `c_at_d`, `diversity` (Shannon), heralded
  `herald_frac`; plus `surprise` and `sigma` (reuse F0); plus reported/live `twoq_err`, `readout_err`,
  and (hardware) `T1`/`T2` via `calibration_poller`. All in one record written to the shared run-JSON
  schema. — `qtree_canary.py`.
- [ ] **AC-F9.3 (one decomposable health index H).** A documented health index `H ∈ [0,1]` = weighted
  geometric mean of healthy-normalized sub-signals, falling when any subsystem degrades; the record
  carries `H`, every normalized component, and the component weights, so any H drop is traceable to a
  subsystem. Default weights equal; a documented (optional) weight-fit maximizes tracking ρ on a
  training fault subset and is validated on held-out faults (overfit guard). — `qtree_canary.py`.
- [ ] **AC-F9.4 (objective tracking — sim, the headline).** Across the fault menu (existing 5 + a new
  long-range/routing fault + a new dynamic-circuit/measure fault) swept over magnitude, compute the
  Spearman rank correlation between H and fault severity, and the same for the single F7 witness margin
  and an RB/coherence baseline. H must track (|ρ| above a stated threshold, correct sign) across
  **more fault types** than either comparator. Written to `research_runs/qtree_canary_tracking.json`
  plus a printed summary table (fault × [H ρ, witness ρ, baseline ρ, verdict]). — `qtree_canary_tracking.py`.
- [ ] **AC-F9.5 (time / scenario trajectory).** A scripted multi-onset health timeline (healthy →
  fault onset → worsen → clear) run through the canary; H is shown to track the timeline, and the trace
  is written to `research_runs/qtree_canary_trajectory.json` with a printed per-cycle H + component
  breakdown. — `qtree_canary_tracking.py`.
- [ ] **AC-F9.6 (honesty / blind-spot coverage map).** The tracking summary reports where H tracks,
  ties, and is **blind** (≥1 fault H misses) as prominently as wins; contains no speed/classical-
  hardness claim; states H's blind spots explicitly. — `qtree_canary_tracking.py` (`_print_table`).
- [ ] **AC-F9.7 (exporter + record wiring).** The F7 OpenMetrics exporter is extended with a
  `qcanary_health` gauge for H plus one `qcanary_h_<component>` gauge per component; the per-cycle
  record appends to `research_runs/qtree_canary_<session>.json`. Scrape-verified via `urllib`. —
  `canary_exporter.py` (extended).

---

## 3. Scope

### In scope
- New `code/qtree_canary.py` (minimal-qtree circuit + observable vector + composite H).
- New `code/qtree_canary_tracking.py` (feasibility sanity run + objective-tracking study + trajectory +
  coverage map + artifacts).
- Two new fault kinds added to `code/fault_injection.py` (long-range/routing degrade; dynamic-circuit/
  mid-measure degrade) with magnitude, reusing the existing `Fault`/`noise_model` machinery.
- Extend `code/canary_exporter.py` with the `qcanary_health` + component gauges.
- New `research_runs/qtree_canary_*.json` artifacts (feasibility, tracking, trajectory, session).

### Out of scope
- **Hardware** objective-tracking confirmation (H heartbeat vs `calibration_poller` drift over time) —
  harness reuses `hardware_batches.py`/`canary_validate.py`; actual QC submission deferred to an
  allocation window. The zero-credit calibration side may still be polled now.
- Any new physics, new witness, or new entangling primitive beyond the existing qtree schematic +
  copied herald teleport.
- Rewiring `web/ops_console.html` for an H panel — optional stretch, not required by any AC.
- Any quantum-advantage / classical-hardness / speed claim.
- Editing `qtree.py`, `genome.py`, `research_qtree_teleport.py`, or the QuantumTree `runs/`/viewer
  (F9 imports/copies; it does not modify the source study).

---

## 4. Data model / artifacts

Per-cycle record (one entry in `research_runs/qtree_canary_<session>.json` `cycles[]`, field names
mirroring the F0/F7 run-JSON so F2/F3 tooling reads it unchanged):

| Field | Source |
|---|---|
| `cycle` | probe counter |
| `C0`, `xi` | qtree `two_point_correlation` on the measured genome |
| `bonds` (`[{i,j,d_qubits,c_at_d}]`) | copied `bond_correlations` at the teleport bond |
| `herald_frac` | heralded post-selection kept-fraction (dynamic-circuit health) |
| `diversity` | qtree `field_stats` Shannon diversity |
| `witness_signal`, `null_band`, `witness_margin` | `closed_loop.witness_gen` + F3 band |
| `surprise`, `sigma` | F0 surprise/branching machinery |
| `twoq_err`, `readout_err`, `T1`, `T2` | `fault_injection.chain_quality` (sim) / `calibration_poller` (hw) |
| `H`, `components` (`{name: normalized∈[0,1]}`), `weights` | composite index (AC-F9.3) |
| `fault` | injected fault label + magnitude + onset (null when none) |

Tracking artifact `research_runs/qtree_canary_tracking.json`:
`{ faults: [{id, magnitude_sweep, H_rho, witness_rho, baseline_rho, verdict: track|tie|blind}], summary }`.

Trajectory artifact `research_runs/qtree_canary_trajectory.json`: `{ cycles: [{cycle, H, components,
fault}], onsets: [...] }`.

OpenMetrics names: `qcanary_health` (H), `qcanary_h_<component>` per component, alongside the existing
`qcanary_*` gauges (`strict`-clean, full type hints).

---

## 5. File plan

**`code/qtree_canary.py`** (new)
- Build a **minimal `spec`** dict locally (small `n_slots`, angle-only `slot_bits`) — does not edit
  `genome.py`.
- `build_min_qtree(spec, thetas, bond, herald=True) -> QuantumCircuit` — reuse the `qtree.py`
  schematic (import `qtree` — it is import-safe): RY encode + brick-wall `_entangle` neighbour chain +
  env/mutation bias + terminal measure, then insert **one** heralded long-range bond via a **copied**
  `_teleport_cx` helper (attributed to `research_qtree_teleport.py:201`; herald = no feed-forward,
  post-select `tel==00`).
- `observe(counts, spec, bond, geno, shots) -> dict` — compute `C0`/`xi` (qtree
  `two_point_correlation`), `bond` `c_at_d` (copied `bond_correlations`), `diversity`
  (`field_stats`), `herald_frac`, `witness_margin` (`closed_loop.witness_gen` + F3 band), `surprise`/
  `sigma` (F0 rolling). Uses only the ancilla `tel` register for the herald post-select — never the
  genome bits.
- `health_index(components, weights) -> tuple[float, dict]` — normalize each component to a
  healthy-referenced [0,1], return `H` = weighted **geometric mean** + the normalized component dict.
  Baselines from a clean (`fault=None`) reference run; weights default equal.
- `class QtreeCanary` — holds spec/bond/shots/backend/rolling state + `fault` hook; `cycle() -> dict`
  builds one circuit, runs (per-shot noisy Aer default, or backend counts), returns the full record;
  `run(cycles, on_record)` = the always-on driver (mirrors `CanaryProbe`).
- `strict`-clean, full type hints; per-shot noise (`AerSimulator()` default method + noise_model), NOT
  `density_matrix`, to keep ≤~16 qubits cheap.

**`code/fault_injection.py`** (extend, do not rewrite)
- Add two `Fault` entries + `noise_model` branches: `longrange_routing` (extra 2q depolarizing /
  crosstalk on the teleport bond path) and `dyncircuit_measure` (mid-circuit measurement / reset error
  bump — the herald-hit-rate stressor). Both carry magnitude + onset; reuse the existing builder.

**`code/qtree_canary_tracking.py`** (new)
- `feasibility_run(fault_id) -> None` — AC-F9.0 single-fault magnitude sweep → monotonicity verdict →
  `research_runs/qtree_canary_feasibility.json`.
- `baseline_detector(records) -> ...` — the RB/coherence proxy (thresholds on `twoq_err`/`readout_err`
  only), reused from the F7 coverage idea = the incumbent comparator.
- `spearman(xs, ys) -> float` — rank correlation (numpy; small, self-contained).
- `run_tracking() -> None` — AC-F9.4: for each fault × magnitude, run the canary, collect H / witness /
  baseline, compute ρ each, classify `track|tie|blind`, write `qtree_canary_tracking.json` + print the
  table (H must track more fault types than either comparator; blind spots printed as loudly as wins).
- `run_trajectory() -> None` — AC-F9.5: scripted multi-onset timeline → `qtree_canary_trajectory.json`
  + per-cycle H/component print.
- CLI: `python qtree_canary_tracking.py [--feasibility|--tracking|--trajectory]`.

**`code/canary_exporter.py`** (extend)
- Add `qcanary_health` + `qcanary_h_<component>` gauges to the registry mapping and the render/
  `record_to_registry` paths; no new dependency.

**`research_runs/`** — new `qtree_canary_feasibility.json`, `qtree_canary_tracking.json`,
`qtree_canary_trajectory.json`, `qtree_canary_<session>.json` (data only).

---

## 6. Implementation steps (order)

1. `qtree_canary.py` — minimal spec + `build_min_qtree` (schematic + copied herald bond); verify one
   circuit builds and runs on Aer (per-shot noise), prints qubit count ≤~16.
2. `observe` + `health_index` — one cycle emits the full record with H and its decomposition.
3. Extend `fault_injection.py` — the two new fault kinds (`longrange_routing`, `dyncircuit_measure`).
4. `qtree_canary_tracking.py` `feasibility_run` — **AC-F9.0 gate**: single-fault sweep, monotonicity
   verdict, feasibility JSON. Do not proceed past here if non-monotone.
5. `run_tracking` — the objective-tracking study (H vs witness vs baseline, ρ per fault, coverage map).
6. `run_trajectory` — the scripted time trajectory trace.
7. Extend `canary_exporter.py` — H + component gauges; `urllib` scrape check.

Sim-first throughout (epic §3). Hardware confirmation deferred (reuses `calibration_poller` free side +
`canary_validate.py` cost pattern).

---

## 7. Conventions
- `strict`-clean Python, full type hints; mirror F0/F7 run-JSON field names so F2/F3 tooling reads the
  Canary output unchanged.
- Reuse, don't reimplement: qtree schematic via import (`qtree.py` is import-safe); F0 witness/surprise/
  σ; F3 null band; F7 `fault_injection`/`calibration_poller`/exporter. The **only** copy-with-attribution
  is the ~15-line herald `_teleport_cx` (to avoid `research_qtree_teleport`'s heavy `pipeline_common`
  import) — cite `research_qtree_teleport.py:201`.
- No `density_matrix` at this qubit count — per-shot Monte-Carlo noise only.
- Honesty-gates-are-law (epic §3): every "healthy/degrading" statement traces to H **and its
  decomposition**; the coverage map states H's blind spots as loudly as its wins (AC-F9.6); no
  speed/classical-hardness claim.
- Do not edit the QuantumTree source study (`qtree.py`/`genome.py`/`research_qtree_teleport.py`) or its
  `runs/`/viewer.

---

## 8. Manual verification
- **AC-F9.0:** `python qtree_canary_tracking.py --feasibility`; inspect
  `research_runs/qtree_canary_feasibility.json` — H monotone-decreasing over the swept fault, the
  responsible component dropping, others flat; printed verdict = feasible.
- **AC-F9.1/2/3:** `python qtree_canary.py` (one/few cycles); confirm the printed record has C0, xi,
  bond c_at_d, herald_frac, diversity, witness_margin, surprise, sigma, and H + components + weights;
  confirm the built circuit is ≤~16 qubits and uses per-shot noise.
- **AC-F9.4/6:** `python qtree_canary_tracking.py --tracking`; inspect `qtree_canary_tracking.json` +
  the printed table — each fault has H/witness/baseline ρ and a track/tie/blind verdict; H tracks more
  fault types than either comparator; at least one blind-spot row is printed; no speed claim present.
- **AC-F9.5:** `python qtree_canary_tracking.py --trajectory`; inspect `qtree_canary_trajectory.json`
  and the printed per-cycle H — H tracks the scripted onset/worsen/clear timeline.
- **AC-F9.7:** run the extended exporter; `curl -s localhost:<port>/metrics` shows `qcanary_health` +
  `qcanary_h_<component>` gauges updating each cycle.

---

## 9. Risks
- **Single scalar hides which subsystem failed.** Mitigation (load-bearing): geometric-mean H +
  full component decomposition in every record + blind-spot coverage map. H is never reported without
  its decomposition.
- **Aer noise is a proxy, not the device** → sim tracking ρ is indicative, not absolute. Mitigation:
  state it; the deferred hardware confirmation correlates H against zero-credit live calibration.
- **Composite index is a modelling choice, not ground truth.** Mitigation: default equal weights;
  any weight-fit is trained on a fault subset and validated on held-out faults; report both.
- **Minimal-qtree statistics weak at small W / few shots** → noisy C0/xi/c_at_d. Mitigation: rolling
  window; report `null_band`; raise shots for the tracking study; keep the herald to a single bond so
  post-selection keeps enough shots.
- **Herald post-selection thins shots** (~4^−nbonds). Mitigation: exactly one bond in the minimal
  circuit; warn when kept shots < floor (reuse the teleport module's warning pattern).
- **Scope creep** into the hardware tracking confirmation → keep it deferred; only the free calibration
  side may run now.

---

## 10. Epic touch-point
The epic §2 ticket table lists F0–F8; F9 is a new post-LEAP sibling of F7/F8. Adding an F9 row to
`epic-critical-quantum-life.md` §2 (and a one-line brief in §9) is a small follow-up — proposed in §11
Q4 rather than done here, to keep this plan self-contained until approved.

---

## 11. Open questions (proposed answers marked)

- **Q1 — Minimal-qtree dimensions.** *Proposal:* angle-only slots (`slot_bits = 2`), `n_slots = 7` →
  14 genome qubits + 1 teleport bond (2 ancilla) = 16 qubits; one bond at slot-distance 5 (qubit
  distance 10). Small enough for per-shot noisy Aer, long enough for a real long-range c(d). Final dims
  pinned empirically by the AC-F9.0 feasibility run. **Accept this default?**
- **Q2 — H aggregation + weights.** *Proposal:* weighted **geometric mean** of healthy-normalized
  components, **equal weights** by default; an optional weight-fit (maximize tracking ρ on a training
  fault subset, validate on held-out faults) reported as a secondary analysis, never as the headline.
  **Accept geometric-mean + equal-weight default?**
- **Q3 — Which subsystems compose H (v1).** *Proposal:* five components — local correlation (C0/xi),
  long-range c_at_d, herald hit-rate, diversity, witness-vs-null margin. Surprise/σ are *recorded* but
  **not** folded into H v1 (they are dynamics signals, not device-health signals). **Agree to keep
  surprise/σ out of H v1?**
- **Q4 — Epic table.** *Proposal:* after approval, add an F9 row to epic §2 + a one-line §9 brief (no
  other epic edits). **OK to update the epic on approval?**
- **Q5 — Hardware tracking confirmation.** *Proposal:* build the harness, run **only** the zero-credit
  `calibration_poller` side now; defer the cost-side H heartbeat vs calibration-drift correlation to a
  QC allocation window (mirrors F7's free/cost split). **Accept deferral?**
