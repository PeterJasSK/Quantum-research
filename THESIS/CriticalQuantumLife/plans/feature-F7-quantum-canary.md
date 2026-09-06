# Feature Plan — F7: The Quantum Canary — entanglement-native, always-on QPU health monitor

**Status:** Complete
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F7 (post-LEAP deliverable; see `plans/LEAP-candidates-ranked.md` §9 + §11.7)
**Author:** Claude (Opus) · **Date:** 2026-09-06
**Depends on:** F0 (engine), F2 (criticality metrics), F3 (certify / null band), F5 (hardware chain picker). All landed.

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.
> **The shippable product face of the program** — runs on the quantum gate that already PASSED
> (F3: 15/16 above null, margin +0.338) and treats σ=0.44 homeostasis as a feature, not a failure.
> Needs **no unmet gate**.

---

## 1. Context & goal

The Canary is an **entanglement-native, always-on QPU health-and-anomaly monitor**, delivered as a
lightweight process that runs the existing F0 closed-loop engine at small W on a spare qubit chain,
one short circuit per cycle, and exports its homeostatic signals as Prometheus/OpenMetrics text that
drops into the QRMI → Prometheus → Grafana stack quantum-cloud operators already run.

The health signal *is* the organism's homeostasis:
- **`witness_margin`** (`⟨X^⊗W⟩` above the classical null) = the device can still create + inherit
  genuine entanglement. Sagging = entanglement quality degrading — a signal no gate-fidelity
  dashboard reports.
- **`surprise` spike / failure to re-cohere after a poke** = anomaly / drift / tamper. The
  active-inference loop is already an anomaly detector.
- **`sigma`** = homeostatic set-point to watch for departures (σ≈0.44 is a *steady* baseline — good
  for a monitor).
- **Yoked baseline** = separates "the world changed" from "the monitor drifted."

The study that makes it a thesis-grade result (not just a feature): **build the monitor, then prove
it catches faults that standard tools (randomized benchmarking, coherence-time tracking) miss** —
delivered as an honest **coverage map** (where it wins, ties, and loses; detection latency vs
incumbents).

### What already exists (integration points — verified in code)
- `code/closed_loop.py` — F0 engine. `witness_gen(counts, geno, shots)` (`:131`) computes joint +
  separable + shot-floor σ; `surrogate_readout` (`:141`) is the classical measure-and-resend null;
  `run_closed_loop` / `run_yoked` (`:274` / `:369`); `outcome_key` / `surprise` machinery;
  `build_generation` (`:205`) builds one GHZ-genealogy circuit with **terminal `measure_all()`**.
- `code/criticality.py` — `estimate_sigma`, `collect_avalanches`, `_fit_xmin` (α), over
  `research_runs/*.json`.
- `code/certify.py` — null band `k/√shots`, witness-vs-surrogate margin logic.
- `code/hardware_batches.py` (777 lines) — live chain-quality numbers (`twoq_err`, `readout_err`),
  `layout.best_chain` low-error qubit-path picker, IBM submission pipeline.
- `code/session.py` — `poke()` API (`flip_expected`, `inject_stimulus`, `alter_selection`) + state
  persistence.
- `web/spectacle.html` — single-file canvas dashboard (the product surface to rewire).
- **Does NOT exist:** any Prometheus/OpenMetrics/HTTP exporter, any fault-injection harness, any
  coverage study (grep confirmed zero `prometheus|http|flask|exporter` in `code/`).

### Honest scoping note (load-bearing)
The LEAP doc sells the Canary as also monitoring **dynamic-circuit health** (mid-circuit
measurement, feed-forward, reset/reuse). The current F0 engine does **none** of those — it emits one
static circuit per generation with terminal `measure_all()` and a `--death=unitary` σ_y stand-in;
there are zero `if_test`/`c_if`/`reset` dynamic primitives anywhere in `code/`. Therefore:
- **In scope for F7:** the entanglement-witness heartbeat monitor + surprise/anomaly detection +
  coverage study over faults the *witness* is sensitive to (entanglement collapse, 2q-gate
  degradation, readout error, calibration drift). This is fully buildable now.
- **Deferred to F8 (Sandpile):** the dynamic-circuit-coverage differentiator (mid-circuit-measure /
  feed-forward / reset faults) — it needs the same feed-forward machinery F8 builds. F7 exposes the
  hooks so that coverage can be added once F8 lands, but does not claim it.

---

## 2. Acceptance criteria

Author-defined (LEAP §9.3 / §11.7). IDs added; each maps to a manual check in §8.

- [x] **AC-F7.1** A **probe loop** wraps the F0 engine at small W (default 6, parametrized 4–8), one
  short circuit per cycle, emitting a per-cycle metrics record: `witness_margin`, `surprise`, `sigma`,
  `adaptation_gap`, `avalanche_rate`, plus `twoq_err` / `readout_err`. Runs in Aer (default) or against
  a hardware backend job stream. — `canary_probe.py:101` (`CanaryProbe.cycle`).
- [x] **AC-F7.2** A **Prometheus/OpenMetrics exporter** serves those metrics as OpenMetrics text over
  a local HTTP endpoint (Python stdlib `http.server`, no new dependency), with `# TYPE`/`# HELP` lines
  and a stable `qcanary_` prefix. — `canary_exporter.py:61` (`render`), `:107` (`serve`), verified via
  `urllib` scrape of `/metrics`.
- [x] **AC-F7.3** A **fault-injection harness** applies labelled faults to the Aer run (entanglement
  collapse, dephasing drift, 2q degrade, readout error, stale calibration), each with id/magnitude/
  onset. — `fault_injection.py:54` (`noise_model`), `FAULTS` `:94`.
- [x] **AC-F7.4** A **coverage study** runs the probe across the fault menu, computes per-fault
  detection latency + specificity for the Canary vs an RB/coherence-proxy baseline, and writes
  `research_runs/canary_coverage.json` + a summary table. — `canary_coverage.py:49` (`run_fault`).
  Validated: 3 wins / 2 honest loses, specificity 1.00.
- [x] **AC-F7.5** An **alert rule** fires when `witness_margin` sits below the null band for N cycles,
  or `surprise` exceeds the yoked baseline by k·σ; the alert is recorded in the metrics stream
  (`qcanary_alert`) and logged. — `canary_probe.py:152` (`_check_alerts`), gauge `canary_exporter.py:59`.
- [x] **AC-F7.6** A **new** single-file ops console `web/ops_console.html` (spectacle.html untouched):
  inject-drift control, heartbeat trace, yoked ghost baseline, anomaly timeline, real-run overlay
  loader. Theme-aware, no external requests. — `web/ops_console.html` (whole file).
- [x] **AC-F7.7** Honesty: no speed/classical-hardness claim; the coverage map reports Canary **loses**
  (readout/2q faults RB catches faster) as prominently as wins. — `canary_coverage.py:115`
  (`_print_table` win/lose legend), `fault_injection.py:104` RB-territory faults.

---

## 3. Scope

### In scope
- New `code/canary_probe.py`, `code/canary_exporter.py`, `code/fault_injection.py`,
  `code/canary_coverage.py`.
- New `web/ops_console.html` (spectacle.html left untouched as template).
- New `research_runs/canary_*.json` + `canary_coverage.json` artifacts.
- Aer-based coverage study; a small hardware confirmation deferred until QC budget allows (harness
  reuses `hardware_batches.py`, no new submission code).

### Out of scope
- Dynamic-circuit fault coverage (mid-circuit-measure / feed-forward / reset) — needs F8's machinery.
- Any new physics or new witness; the probe reuses F0/F3 as-is.
- A packaged Grafana dashboard JSON (optional stretch; the OpenMetrics endpoint is the contract).
- Live automated QC submission (manual workflow per epic §3).

---

## 4. Data model / artifacts

Per-cycle metrics record (one JSON line appended to `research_runs/canary_<session>.json`
`cycles[]`, mirroring the F0 run-JSON field names so F2/F3 tooling reads it unchanged):

| Field | Source |
|---|---|
| `cycle` | probe counter |
| `witness_joint`, `witness_separable`, `witness_signal` | `closed_loop.witness_gen` |
| `witness_margin`, `null_band` | `certify` null-band logic |
| `surprise`, `sigma` | F0 surprise/branching machinery |
| `adaptation_gap` | closed-minus-yoked surprise drop (rolling) |
| `avalanche_rate` | `criticality.collect_avalanches` on the rolling window |
| `twoq_err`, `readout_err`, `chain` | `hardware_batches.py` chain-quality |
| `fault` | injected fault label + magnitude + onset (null when none) |
| `alert` | fired rule id + reason (null when none) |

Coverage-map artifact `research_runs/canary_coverage.json`: `{ faults: [{id, magnitude, onset,
canary_latency, canary_specificity, baseline_latency, verdict: win|tie|lose}], summary }`.

OpenMetrics names: `qcanary_witness_margin`, `qcanary_surprise`, `qcanary_sigma`,
`qcanary_adaptation_gap`, `qcanary_avalanche_rate`, `qcanary_twoq_err`, `qcanary_readout_err`,
`qcanary_alert` (all `strict_types`-clean Python; full type hints).

---

## 5. File plan

**`code/canary_probe.py`** (new)
- `class CanaryProbe` — holds W, chain, backend, rolling windows (witness, surprise), yoked baseline.
- `def cycle(self) -> dict` — build one F0 generation circuit (reuse `build_generation`), run
  (`run_counts` for Aer or a hardware counts stream), call `witness_gen` + `certify` null band,
  update surprise/σ, compute `adaptation_gap` + `avalanche_rate`, attach chain-quality, return the
  metrics record.
- `def run(self, cycles: int | None, on_record: Callable[[dict], None]) -> None` — loop; `None` =
  run until stopped (the always-on mode); calls `on_record` (the exporter/logger sink).
- Reuses, does not duplicate: `closed_loop.witness_gen`, `run_counts`, `certify` band,
  `criticality.collect_avalanches`, `hardware_batches` chain-quality, `layout.best_chain`.

**`code/canary_exporter.py`** (new)
- `class MetricsRegistry` — latest value per `qcanary_*` metric, thread-safe.
- `def serve(registry, port) -> None` — stdlib `http.server` `/metrics` endpoint emitting OpenMetrics
  text (`# HELP` / `# TYPE gauge` / value). No third-party dependency.
- `def record_to_registry(record: dict, registry) -> None` — map a probe record onto gauges.
- CLI: `python -m canary_exporter --w 6 --port 9797 [--backend ...]` wires `CanaryProbe.run` →
  `record_to_registry` → HTTP.

**`code/fault_injection.py`** (new)
- `def noise_model(fault: Fault | None) -> NoiseModel` — build an Aer `NoiseModel`: baseline from a
  calibration snapshot, then apply the fault (extra dephasing/detune on a qubit, readout-error bump,
  2q-depolarizing bump, or frozen/stale layout). `strict_types`, full hints.
- `FAULTS: list[Fault]` — the labelled menu (id, target, magnitude, onset cycle).
- Injected via the Aer path only; hardware fault injection (real detune) is a manual note, not code.

**`code/canary_coverage.py`** (new)
- `def baseline_detector(records) -> ...` — a simple RB/coherence-proxy alarm (thresholds on
  `twoq_err`/`readout_err` only) = the incumbent the Canary is compared against.
- `def run_coverage() -> None` — for each fault: run the probe with `noise_model(fault)`, run the
  baseline over the same records, compute latency/specificity, classify win/tie/lose, write
  `research_runs/canary_coverage.json` + print the summary table.

**`web/ops_console.html`** (new — `spectacle.html` is the template, left untouched)
- Poke control labelled "Inject drift" (drives the fault menu); heartbeat trace = `witness_margin`;
  ghost panel = yoked baseline; drift/anomaly timeline reading `research_runs/canary_*.json`.
  Single-file, inline CSS/JS, `prefers-color-scheme` + `data-theme`, no external requests (mirror F6
  discipline). Start from a copy of `spectacle.html`, then relabel/rewire.

**`research_runs/`** — new `canary_<session>.json`, `canary_coverage.json` (data only).

---

## 6. Implementation steps (order)

1. `canary_probe.py` — the probe cycle over the existing engine (Aer first). Verify one cycle emits a
   full metrics record.
2. `canary_exporter.py` — OpenMetrics endpoint; scrape it with `curl localhost:9797/metrics`.
3. `fault_injection.py` — the Aer noise menu.
4. `canary_coverage.py` — the study + coverage-map artifact + summary table.
5. `alert` rule wired into the probe record + exporter gauge (AC-F7.5).
6. Rewire `web/spectacle.html` into the ops console (AC-F7.6).

Sim-first throughout (epic §3). Hardware confirmation deferred (reuses `hardware_batches.py`).

---

## 7. Conventions
- `strict_types`-clean Python, full type hints; mirror `stage4_*` / F0 run-JSON field names so F2/F3
  tooling reads Canary output unchanged.
- No new third-party dependency for the exporter (stdlib `http.server` + OpenMetrics text).
- Reuse, don't reimplement, the witness / null band / chain-quality (import from F0/F3/F5).
- Honesty-gates-are-law (epic §3): every "healthy/degrading" label traces to `witness_margin` vs the
  null band; the coverage map states losses as loudly as wins (AC-F7.7).

---

## 8. Manual verification
- **AC-F7.1/2:** run `python -m canary_exporter --w 6 --port 9797`; `curl -s localhost:9797/metrics`
  shows all `qcanary_*` gauges updating each cycle.
- **AC-F7.3/4:** run `python canary_coverage.py`; inspect `research_runs/canary_coverage.json` + the
  printed table — each fault has canary vs baseline latency and a win/tie/lose verdict.
- **AC-F7.5:** inject an entanglement-collapse fault; confirm `qcanary_alert` fires and is logged
  within N cycles.
- **AC-F7.6:** open the ops console in a browser (dark + light); confirm heartbeat trace, drift
  injection, yoked ghost baseline, and the anomaly timeline render with no external requests.
- **AC-F7.7:** confirm the coverage summary lists at least one tie/lose row (e.g. single-qubit T1)
  and contains no speed/classical-hardness claim.

---

## 9. Risks
- **Witness statistics weak at small W / few shots** → alert flapping. Mitigation: rolling window +
  N-consecutive-cycle rule; report `null_band` alongside margin.
- **Aer noise model is a proxy, not the device** → coverage latencies are indicative, not absolute.
  Mitigation: state this explicitly; a small hardware confirmation later.
- **Scope creep into dynamic-circuit coverage** → keep that deferred to F8 (see §1 honest scoping).

---

## 10. Open questions — RESOLVED
- [x] **Q1 — Ticket numbering.** F7 = Canary, F8 = Sandpile. Thesis synthesis is **stripped of its
  number and shelved** — it becomes a numberless deliverable to assemble only once everything is
  built and validated. Epic §2 table updated accordingly.
- [x] **Q2 — Exporter transport.** Default: stdlib `http.server` OpenMetrics endpoint (zero new deps).
- [x] **Q3 — Ops console file.** Leave `web/spectacle.html` as the template; create a **new**
  `web/ops_console.html`.
- [x] **Q4 — Baseline detector fidelity.** The RB/coherence "incumbent" stays a documented threshold
  proxy for the coverage study; a real RB head-to-head is future hardware work.

---

## 11. Post-implementation notes

**Built (Aer-only, no QC touched — `backend=None` throughout, PRNG entropy):**
- `code/fault_injection.py` — labelled fault menu + Aer `NoiseModel` builder + reported chain-quality.
- `code/canary_probe.py` — `CanaryProbe`: closed cycle + yoked-shadow cycle, witness margin, surprise,
  σ, adaptation gap, avalanche rate, two alert rules. Reuses F0 (`closed_loop`), F3 null band,
  `criticality.collect_avalanches`.
- `code/canary_exporter.py` — stdlib `http.server` OpenMetrics endpoint (`qcanary_*` gauges) +
  per-cycle `research_runs/canary_<session>.json` writer.
- `code/canary_coverage.py` — fault-injection coverage study → `research_runs/canary_coverage.json`.
- `web/ops_console.html` — new single-file, theme-aware ops console (spectacle.html untouched).
- `code/calibration_poller.py` — **zero-credit** calibration poller: reads a real backend's
  published `target/properties/status` (2q err, readout, T1/T2, queue) — no job, no shots. Writes
  `research_runs/canary_calibration_<backend>.json`. Verified live against `ibm_kingston` (credits=0).
- `web/ops_console.html` free/cost split: a "free calibration layer (zero credits)" panel loads the
  poller series; the witness heartbeat panel is labelled "cost layer · runs on allocation".
- `plans/RUNLOG-real-QC.md` — how to run real QC later (free poller now; cost heartbeat on allocation
  when the free tier resets), incl. the one deferred plumbing change to wire `CanaryProbe._run` to
  `hardware_batches` submission.

**Validation (Aer):** coverage at W=6, 3072 shots, 18 cycles →
`{win: 3, lose: 2}`, specificity 1.00. Wins = entanglement_collapse, dephasing_drift,
stale_calibration (incumbent's 2q/readout numbers miss them). Loses = twoq_degrade, readout_error
(RB catches at onset — honest, that is RB's territory). OpenMetrics endpoint scrape-verified via
`urllib`; exporter writes the run JSON.

**Deferred / follow-ups:**
- Dynamic-circuit fault coverage (mid-circuit-measure / feed-forward / reset) waits on F8's machinery
  — the probe exposes the `fault` hook but does not yet exercise dynamic-circuit primitives.
- Hardware confirmation of the coverage map (real detune / stale-cal) is manual, deferred to a QC
  window; `CanaryProbe(backend=...)` streams counts from a hardware sampler when one is supplied.
- Optional: a packaged Grafana dashboard JSON (the OpenMetrics endpoint is the contract; not built).
- `hardware_batches.gated_chain_with_stats` is the real-calibration source to wire in place of the
  fault-menu `chain_quality` numbers when running against a backend.
