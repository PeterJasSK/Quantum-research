# Epic: Quantum Galton Board — The Depth at Which Noise Erases the Quantum Walk

**Slug:** quantum-galton-board
**Plans:** Plan 1–Plan 6 (6 plans)
**Author:** Claude (Opus)
**Date:** 2026-08-06
**Status:** Draft

> **Source material:** `plans/viz-2-quantum-galton-board.md` (the study idea: pitch,
> research question, hypothesis, method, metrics, visualization spec, and IEEE short-paper
> thesis). This epic operationalises that pitch into pickup-ready plans; it does not
> override it. Where the source and this epic disagree, the source wins and the conflict is
> raised in §8.
>
> **Structural twin:** `../QuantumLife/` (the shipped Quantum Tree entanglement-correlation
> study). This epic deliberately mirrors that project's layout (`code/ research/ web/ runs/
> research_runs/`), its **reuse-not-copy** Heron r2 pipeline wiring (`pipeline_common` +
> `layout.best_chain` imported from `../CalibrationGuidedHighYieldQRNG/code/`), its
> `run.json` + `summary.json` output discipline, its `--sim` classical surrogate arm, and
> its self-contained browser `web/` viewer. Read `../QuantumLife/README.md` and
> `../QuantumLife/research/STUDY_ENTANGLEMENT_CORRELATION.md` alongside this document —
> every convention here has a working precedent one directory over.
>
> **Authoring convention:** planned with `/plan-epic`, specialised per unit of work with
> `/plan-feature` (the same epic→plan workflow used across this repo). Per project directive
> there are **no automated test suites** and **no GitHub issues** — verification is offline
> correctness gates, a `--sim` root-free simulator, and a JS↔Python parity check on the
> web arm (see §3.6 and each plan's "Verification" note). ACs are derived from the source
> doc's numbered sections, not from a tracker.

---

## 1. Why this epic exists

A classical Galton board drops balls through a lattice of pegs and builds a binomial →
Gaussian pile: variance grows diffusively, σ ∝ √t. The quantum version replaces each peg
with a coin+shift unitary — a discrete-time quantum walk (DTQW) on a line — where amplitudes
interfere instead of branching randomly. The emergent distribution is **not** Gaussian: it
develops the twin-horn ballistic profile of a quantum walk, spreading σ ∝ t (variance ∝ t²).
That ballistic-vs-diffusive contrast is a known, clean, hardware-friendly benchmark with a
striking, unambiguous signature.

Pure physics novelty is modest, so this epic frames the walk as a **device-fidelity
storyteller**. On a real Heron r2 chip, every extra walk step is more two-qubit gates and
more decoherence. At some depth the horns collapse back toward the classical hump — the
ballistic signature dies and σ ∝ t reverts to σ ∝ √t. That knee is a fresh, measurable,
chip-specific result: a **"randomness-shape half-life"** of the device set by its two-qubit
error rate. The single defended claim is that this ballistic-to-diffusive crossover depth is
a reproducible, hardware-specific fidelity metric — and the headline figure is the ideal
horns melting into the classical curve under a depth slider you can drag live.

The user-visible outcome is a self-contained interactive web demo (the spectacle — a
cascade animation of the pile forming, a depth slider, an interference glow), a set of
`research_runs/` with real Heron r2 data across three arms, and a 6–8 page IEEE short paper.
This is the dynamic-systems sibling of the `qh-2-temporal-drift-stability` and
`qh-3-minimum-extraction-budget` reliability studies and reuses the exact same hardware
access and noise-model tooling as the QRNG thesis and Quantum Tree.

## 2. Plans in this epic

| ID | Plan file | Title | Delivers | Priority |
|----|-----------|-------|----------|----------|
| P1 | `plans/plan-1-scaffolding-pipeline.md` | Scaffolding & Heron r2 pipeline wiring | `code/` skeleton, `config.py` env single-source, DTQW register/position contract, `run.json`/`summary.json` schema, `pipeline_common`+`layout` reuse, `--sim` path, seed determinism | `[MUST]` |
| P2 | `plans/plan-2-quantum-walk-circuit.md` | Quantum-walk circuit + three-arm runner | Coin+shift DTQW builder, depth sweep n=2…N, three arms (ideal sim / device-noise-model sim / real hardware), SWAP-free chain layout | `[MUST]` |
| P3 | `plans/plan-3-metrics-analysis.md` | Metrics & collapse-knee analysis | The four metrics (variance exponent, TV/Hellinger, horn contrast, entropy) + the ballistic→diffusive crossover-depth extractor | `[MUST]` |
| P4 | `plans/plan-4-experiments-figures.md` | Experiments, sweeps & headline figures | Depth×arm sweep matrix, the horns-melting figure + the collapse-curve figure, replay-JSON export for the web arm | `[MUST]` |
| P5 | `plans/plan-5-web-spectacle.md` | The web spectacle | Self-contained HTML/Canvas: cascade waterfall, depth slider, classical↔quantum morph, interference glow, ideal/noisy/hardware toggle | `[MUST]` |
| P6 | `plans/plan-6-research-writeup.md` | Research docs + IEEE short paper | `research/` STUDY+RUNBOOK+CONCLUSION, `thesis/` LaTeX 6–8 pp, both figures wired in, positioning | `[SHOULD]` |

The `ID` column (P1…P6) is referenced from the rest of this document and from each
`/plan-feature` output. IDs match the sibling studies' `P#` / `AC-#` / `OQ-#` scheme.

## 3. Cross-cutting decisions

Decisions made once for the whole epic. Every `/plan-feature` invocation must respect these
and must not re-litigate them.

- **§3.1 — Device-fidelity storyteller, not new physics (LOCKED).** The defended claim is
  that the ballistic→diffusive crossover *depth* is a chip-specific, reproducible fidelity
  metric. The quantum walk itself is a known benchmark; novelty is the device-specific
  collapse curve and it must be framed as the contribution (source §Pitch, §Thesis). Do not
  claim a new quantum-walk result.

- **§3.2 — Three arms, one circuit (LOCKED).** There is a single DTQW circuit builder (P2).
  The only thing that varies across arms is the execution backend: `ideal` (noiseless
  statevector/`AerSimulator`), `noisy` (`AerSimulator.from_backend` device noise model), and
  `hw` (real Heron r2 via `pipeline_common.run_sampler`). No arm gets bespoke circuit logic.
  This mirrors QuantumLife's art-vs-`--sim` split, extended to three arms.

- **§3.3 — Reuse the Heron r2 pipeline, do not copy (LOCKED).** Hardware access, submission,
  and the SWAP-free low-error chain selection are imported from
  `../CalibrationGuidedHighYieldQRNG/code/` exactly as QuantumLife does:
  `sys.path.insert(0, _CALIB_CODE)` then `from pipeline_common import connect, run_sampler,
  timestamp` and `from layout import best_chain`. The classical register must be named `"c"`
  (required by `pipeline_common.run_sampler`, see `QuantumLife/code/qtree.py:151`).
  Re-pick the chain from **live** calibration before every hardware run — never hardcode a
  stale qubit list (`layout.py` docstring).

- **§3.4 — The visualization is a first-class deliverable (LOCKED).** P5 is not a
  nice-to-have. The spectacle carries the thesis: the depth slider dragging the ideal horns
  into the classical hump *is* the paper's headline figure made live (source §THE
  VISUALIZATION). It must be as polished as `../QuantumLife/web/` — pure browser HTML/Canvas,
  self-contained (no build step, no CDN, no framework), dark-friendly, replaying recorded
  `run.json`/replay data. Faithfulness to the Python source of truth is enforced by the
  parity gate (§3.6).

- **§3.5 — Simulated arms are sufficient for most of the sweep; hardware anchors the knee
  (LOCKED, with caveat).** The full depth sweep runs on `ideal` and `noisy` arms cheaply; the
  `hw` arm runs at a **subset** of depths (chosen in P4, OQ-3) to anchor and validate the
  collapse curve without burning excessive QPU time. The caveat — real-device drift means the
  knee is a distribution over calibration epochs, not a single number — is stated as a
  threat-to-validity in P6, not engineered away.

- **§3.6 — Testing = offline gates + `--sim` + JS↔Python parity, no unit-test suite
  (LOCKED).** Per project directive (same as QuantumLife, ECMP, DNSPoisonRace, `qrng-eaas`),
  there is no `pytest` suite. Correctness is established by: (a) standalone offline
  `*_check.py` scripts that assert circuit/metric invariants with no network and no QPU
  (e.g. ideal-arm DTQW reproduces the known analytic Hadamard-walk twin-horn distribution to
  tolerance); (b) the `--sim` classical surrogate that runs the whole pipeline root-free and
  QPU-free; (c) a JS↔Python parity gate proving the browser's distribution/metric rendering
  matches the Python source of truth before the web arm ships. "How it will be tested"
  everywhere in this epic means these three mechanisms, not automated tests.

- **§3.7 — No QRNG / QEaaS arm (LOCKED).** Unlike the ECMP and DNS attack-papers, this study
  has **no** randomness-source variable and **no** Q-EaaS provenance receipt. The randomness
  here is the quantum measurement itself; the independent variable is *circuit depth*, and
  the arms are *execution fidelity* (ideal/noisy/hardware). Do not import QRNG-client
  patterns or add a provenance panel — that would be scope creep from the wrong sibling.

## 4. Shared artefacts & data model

Artefacts more than one plan touches. Introduced once, consumed unchanged downstream (frozen
interfaces, QuantumLife `genome.py` style).

| Artefact | Introduced by | Consumed by | Notes |
|----------|---------------|-------------|-------|
| `code/config.py` (env single-source) | P1 | all | backend name, `IBM` account env, depth range `N`, shots, seeds, hw-depth subset — mirrors QuantumLife's env/arg handling |
| `WALK_SPEC` position/coin contract (register → position-space histogram) | P1 | P2, P3, P5 | the DTQW analogue of `genome.py:GENOME_SPEC`; embedded verbatim into `run.json` so the JS viewer decodes identically; keep the JS mirror in sync by hand |
| `build_walk(steps, coin, encoding)` circuit builder | P2 | P3, P4 | one builder; coin+shift unitary; parameterised step count |
| `run_arm(kind, steps)` dispatch `ideal\|noisy\|hw` | P2 | P4 | one factory, three arms (§3.2); `hw` calls `pipeline_common.run_sampler` |
| `run.json` schema (spec + counts + backend + calibration snapshot + seed) | P1 | P3, P4, P5 | mirror `QuantumLife/runs/*_run.json`; one file per (arm, depth) run |
| `summary.json` (per-sweep aggregate) | P1/P4 | P4, P5, P6 | mirror `QuantumLife/research_runs/*_summary.json` |
| Metric functions (`variance_exponent`, `tv_distance`, `hellinger`, `horn_contrast`, `entropy`) | P3 | P4, P5, parity gate | Python is source of truth; JS is a vendored mirror for the web arm |
| Analytic reference distributions (ideal Hadamard walk + binomial) | P3 | P3 check, P4, P5 | closed-form baselines the arms are compared against |
| Replay export JSON (`web/replay/*.json` or embedded) | P4 | P5 | per-depth position histograms for the three arms + fitted metrics |

**The four metrics** (from source §Metrics — the measurables this epic must produce):

| ID | Metric | Definition | Owner |
|----|--------|------------|-------|
| M1 | Variance growth exponent `a` | fit σ² ∝ tᵃ over the depth sweep; a→2 ballistic, a→1 diffusive | P3/P4 (defines the knee) |
| M2 | Distribution distance to references | total-variation and Hellinger distance: hardware vs ideal, and hardware vs classical binomial, per depth | P3/P4 |
| M3 | Peak-splitting visibility (horn contrast) | contrast between the twin-horn peaks and the central valley, vs depth — the collapse curve | P3/P4 (headline) |
| M4 | Output-distribution entropy | Shannon entropy of the position distribution vs depth | P3/P4 |

The **crossover / knee depth** (the single defended metric, §3.1) is derived from M1+M3:
the depth at which `a` falls through the ballistic/diffusive midpoint and the horn contrast
collapses. Its extractor is owned by P3 and reported by P4/P6.

## 5. The mechanism under study — the discrete-time quantum walk

The domain's substitute for a status workflow (DNS epic §5 style). One walk of `n` steps:

```
   |position = 0>  ⊗  |coin>                         (localised start)
        │
        ▼
   ┌─────────────── repeat n times (n = board rows = walk steps) ───────────────┐
   │  COIN:  apply coin unitary (Hadamard) to the coin qubit                     │
   │  SHIFT: conditional shift — coin |0> moves position left, |1> moves right   │
   │         (amplitudes for the two directions INTERFERE across steps)          │
   └─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
   MEASURE position register  ──▶  histogram over positions
        │
        ├── ideal arm  ─▶ twin horns, σ ∝ t   (ballistic, variance ∝ t²)
        ├── noisy arm  ─▶ horns erode as n grows (device noise model)
        └── hw arm     ─▶ horns collapse toward the classical hump past the knee
```

- **Classical reference:** each peg is an independent fair coin → binomial → Gaussian pile,
  σ ∝ √t (diffusive). This is the baseline the hardware reverts to under noise.
- **Quantum walk:** coin+shift with a fixed coin (Hadamard) makes the two shift amplitudes
  interfere step-to-step, producing the ballistic twin-horn profile — the signature that
  distinguishes it from the classical board.
- **The collapse:** two-qubit gate error accumulates with depth; past the knee the
  interference washes out and the measured distribution returns to the diffusive hump. The
  knee depth is the defended fidelity metric (§3.1, M1+M3).
- **Encoding decision (OQ-1):** position register encoding (one-hot line vs binary
  counter vs `n+1`-qubit chain) is chosen once in P1 and frozen into `WALK_SPEC`; it fixes
  qubit count, the SWAP-free chain length P2 requests from `layout.best_chain`, and the JS
  decoder in P5.

## 6. Scope & experimental design

- **In scope:** a discrete-time quantum walk on a line, `n` rows = `n` steps, swept
  `n = 2…N`; three arms (ideal sim, device-noise-model sim, real Heron r2); the four metrics;
  the crossover-depth extraction; the interactive web spectacle; a 6–8 pp IEEE short paper.
- **Out of scope (stated, not engineered away — becomes threats-to-validity in P6):**
  continuous-time quantum walks; 2-D walks; error mitigation / dynamical decoupling (a
  no-mitigation baseline is the honest first result — mitigation is future work); walks with
  a non-Hadamard or time-dependent coin (fixed Hadamard for v1); more than one physical chip
  (one Heron r2 backend for v1, `config.py` swappable).
- **Arms and depths:** `ideal` and `noisy` run the full `n = 2…N` sweep (cheap); `hw` runs a
  chosen subset of depths (OQ-3) with repeats and seeds so hardware points carry mean ± std,
  exactly as QuantumLife's `--repeats` gives its C(d)/ξ numbers a spread (§3.5).
- **Determinism:** every arm is seed-tagged and reproducible (`--sim`/ideal from a seed;
  `noisy` from a seeded noise model; `hw` tagged by calibration snapshot + timestamp), so
  `run.json` fully reconstructs a run — mirror `QuantumLife/code/research_qtree.py` repeats.

## 7. Implementation order

1. **P1** (scaffolding) — gates everything; freezes `config.py`, `WALK_SPEC`, the
   `run.json`/`summary.json` schema, and the `pipeline_common`/`layout` wiring.
2. **P2** (circuit + arms) — depends on P1's contract; freezes `build_walk` and the
   three-arm dispatch. The ideal arm becomes runnable and checkable against the analytic walk.
3. **P3** (metrics) — depends on P2 outputs; freezes the four metric functions and the knee
   extractor, checked against analytic references.
4. **P4** (experiments/figures) — depends on P3; runs the depth×arm sweep, extracts the knee,
   renders the two figures, exports replay JSON.
5. **P5** (web) — depends on P1 `WALK_SPEC` (decoder parity) and P4 replay JSON; the
   spectacle. Its Tier-A pure-JS ideal-walk shell can start as soon as P1's spec exists,
   before P4 data is final (same two-tier pattern as QuantumLife's viewer).
6. **P6** (writeup) — depends on P4 figures + the knee; `research/` docs can be drafted early
   (STUDY is a design doc), CONCLUSION and thesis land once P4 data is in.

P5 can begin its Tier-A (pure-JS ideal walk) shell as soon as P1's `WALK_SPEC` exists, before
P4 replay data is final.

## 8. Open questions (epic-wide) — RESOLVED (2026-08-06, developer: "yes to all defaults")

- [x] **OQ-1 — Position-register encoding.** **Decision:** one-hot line for v1 (`n+1`
  position qubits, simple shift, shallow per-step depth so more steps survive before the knee,
  direct histogram decode, matches the "pile of bins" visual). Fixes qubit count, the
  SWAP-free chain length requested from `layout.best_chain`, and the JS decoder. Binds P1
  (`WALK_SPEC`), P2 (`build_walk`), P5 (decoder).
- [x] **OQ-2 — Max depth `N` and the qubit budget.** **Decision:** set `N` from the live
  `best_chain` length under the OQ-1 one-hot encoding (QuantumLife tops out at a 108-qubit
  chain; a full 120-qubit simple path does not exist on the heavy-hex); sweep `n = 2…N` for
  the sim arms. Binds P1 (`config.py`), P2 (layout request), P4 (sweep range).
- [x] **OQ-3 — Hardware-arm depth subset & repeats.** **Decision:** a low anchor depth, 2–3
  depths bracketing the predicted knee, and one past it; ≥3 seeded repeats per hw point so
  hardware carries mean ± std. Binds P4 (matrix), P6 (error bars).
- [x] **OQ-4 — Coin operator for v1.** **Decision:** fixed Hadamard coin only (canonical
  twin-horn walk); biased/DFT coins noted as future work in P6 (§6). Binds P2.
- [x] **OQ-5 — Backend & noise-model source.** **Decision:** the `noisy` arm builds its model
  from the same Heron r2 backend as the `hw` arm via `AerSimulator.from_backend` on live
  calibration, so noisy and hw are apples-to-apples. Backend name read from `config.py`. Binds
  P1 (`config.py`), P2 (noisy arm).
- [x] **OQ-6 — Web delivery target.** **Decision:** single self-contained HTML file with
  embedded replay JSON (QuantumLife `quantum_tree.html` style) — zero build, matches source's
  "self-contained". Binds P4 (export shape), P5.

All resolved; decisions folded into the relevant plan briefs above and into §3/§5 where they
lock cross-cutting behaviour.

## 9. Per-plan briefs

Acceptance criteria below are **derived from `plans/viz-2-quantum-galton-board.md`** (§How it
becomes a study, §Metrics, §THE VISUALIZATION, §Thesis) — there is no upstream issue tracker
to quote verbatim (this project uses source docs, not GitHub issues). Each AC cites the
source section it comes from so it stays traceable, not invented.

### P1 — Scaffolding & Heron r2 pipeline wiring
- **Delivers:** the `code/` package skeleton, `config.py` as the single env source-of-truth,
  the `WALK_SPEC` position/coin contract (the DTQW analogue of `genome.py:GENOME_SPEC`), the
  `run.json`/`summary.json` schema, the `pipeline_common`+`layout` import wiring, and the
  `--sim`/ideal root-free path.
- **Acceptance criteria (derived from source §Method, §Connection):**
  - AC-1.1 A root-free, QPU-free ideal/`--sim` run produces one `run.json` for a trivial
    2-step walk end to end.
  - AC-1.2 `config.py` reads the backend name, IBM account env, depth range `N`, shots, seeds,
    and the hw-depth subset from the environment/args only.
  - AC-1.3 `WALK_SPEC` and the `run.json` schema are frozen and documented for P2/P3/P5, and
    `WALK_SPEC` is embedded verbatim into every `run.json` (mirror `genome.py`).
  - AC-1.4 Hardware wiring imports `pipeline_common.{connect,run_sampler,timestamp}` and
    `layout.best_chain` from `../CalibrationGuidedHighYieldQRNG/code/` (reuse, not copy);
    the classical register is named `"c"` (§3.3).
- **Depends on:** none. **Gates:** P2, P3, P4, P5.
- **Conventions to follow:** mirror `../QuantumLife/code/{qtree.py,genome.py,layout.py}` and
  the `runs/`+`research_runs/` `run.json`/`summary.json` split; stdlib + qiskit only for the
  core (pandas/matplotlib confined to the analysis/figure code in P4).
- **Out of scope:** the walk circuit (P2), metrics (P3).

### P2 — Quantum-walk circuit + three-arm runner
- **Delivers:** `build_walk(steps, coin, encoding)` (coin+shift DTQW under the OQ-1 encoding)
  and `run_arm(kind, steps)` with three arms — `ideal` (noiseless statevector/`AerSimulator`),
  `noisy` (`AerSimulator.from_backend` device noise model, OQ-5), `hw` (real Heron r2 via
  `pipeline_common.run_sampler`) — each emitting a `run.json`.
- **Acceptance criteria (derived from source §Method):**
  - AC-2.1 One circuit builder drives all three arms; only the backend varies (§3.2).
  - AC-2.2 The `ideal` arm reproduces the analytic Hadamard-walk twin-horn distribution to
    tolerance (offline check, §3.6).
  - AC-2.3 The `hw` arm requests a SWAP-free low-error chain from `layout.best_chain` on
    **live** calibration before submitting, and runs at the OQ-3 depth subset with seeded
    repeats.
  - AC-2.4 The `noisy` arm builds its model from the same backend as `hw` so the two are
    comparable (OQ-5).
  - AC-2.5 Every run is reproducible from its `run.json` (spec + backend + calibration
    snapshot + seed).
- **Depends on:** P1. **Gates:** P3, P4.
- **Conventions to follow:** the arm split mirrors QuantumLife's hardware-vs-`--sim` runner
  (`qtree.py`/`research_qtree.py`); reuse the Heron r2 submission path, do not reimplement it.
- **Out of scope:** metric computation (P3), figures (P4).

### P3 — Metrics & collapse-knee analysis
- **Delivers:** the four metric functions and the ballistic→diffusive crossover-depth
  extractor, over the depth sweep, with analytic references.
- **Acceptance criteria (derived from source §Metrics):**
  - AC-3.1 M1 variance growth exponent: fit σ² ∝ tᵃ across depths; report `a` per arm (a→2
    ballistic, a→1 diffusive).
  - AC-3.2 M2 total-variation and Hellinger distance: hardware vs ideal, and hardware vs
    classical binomial, per depth.
  - AC-3.3 M3 peak-splitting visibility (horn contrast) vs depth — the collapse curve.
  - AC-3.4 M4 Shannon entropy of the output distribution vs depth.
  - AC-3.5 The crossover/knee depth is extracted from M1+M3 and is reproducible from the
    sweep data (the single defended metric, §3.1).
- **Depends on:** P2. **Gates:** P4, P5 (metric parity mirror).
- **Conventions to follow:** Python is the source of truth for every metric; the JS mirror in
  P5 must reproduce these values (parity gate, §3.6). Analytic references (ideal Hadamard
  walk, binomial) are closed-form baselines.
- **Out of scope:** rendering figures (P4), the web viz (P5).

### P4 — Experiments, sweeps & headline figures
- **Delivers:** the depth×arm experiment matrix (as data), the two headline figures, the
  extracted knee, and the replay-JSON export for P5.
- **Acceptance criteria (derived from source §Metrics, §THE VISUALIZATION "depth slider"):**
  - AC-4.1 The depth sweep across the three arms renders the **horns-melting** figure — ideal
    twin horns morphing toward the classical hump as depth/noise grows (the paper's headline).
  - AC-4.2 The M1+M3 sweep renders the **collapse-curve** figure — horn contrast and variance
    exponent falling with depth, marking the crossover knee.
  - AC-4.3 The extracted knee depth is reported with hardware error bars from the OQ-3 repeats.
  - AC-4.4 Per-depth, per-arm position histograms + fitted metrics are exported as replay JSON
    for the web arm (shape per OQ-6).
- **Depends on:** P3. **Gates:** P5, P6.
- **Conventions to follow:** mirror QuantumLife's `research_runs/*_summary.json` aggregation
  and any figure-rendering script; matplotlib confined here.
- **Out of scope:** the paper prose (P6), the interactive viz (P5).

### P5 — The web spectacle
- **Delivers:** the self-contained browser HTML/Canvas visualization — the star of the epic.
- **Acceptance criteria (derived verbatim from source §THE VISUALIZATION):**
  - AC-5.1 **Cascade animation** — balls/amplitude "waterfall" through the peg lattice, bins
    filling in real time; a toggle for classical vs quantum that morphs the bell curve into
    the twin horns.
  - AC-5.2 **Depth slider** — drag `n` and watch the ideal horns melt toward the classical
    hump as noise wins (the headline figure as a live control), replaying the P4 arms.
  - AC-5.3 **Interference glow** — color pegs by local phase so constructive/destructive
    interference is visible as it happens (the "why it's not Gaussian" panel).
  - AC-5.4 Pure browser HTML/Canvas, self-contained (no build, no CDN, no framework), same
    delivery as `../QuantumLife/web/`; the distribution/metric rendering is **gated on
    JS↔Python parity** (§3.6) against the P3 metrics.
- **Depends on:** P1 (`WALK_SPEC` decoder), P4 (replay JSON). **Gates:** none.
- **Conventions to follow:** clone the delivery of `../QuantumLife/web/quantum_tree.html` —
  hand-rolled canvas + `requestAnimationFrame`, no animation library, recorded data replayed
  in-browser, dark-friendly. Keep the JS `WALK_SPEC` decoder in sync with P1 by hand.
- **Out of scope:** any live hardware call from the browser — the web app replays recorded P4
  data only.

### P6 — Research docs + IEEE short paper
- **Delivers:** the `research/` design docs (STUDY + RUNBOOK + CONCLUSION, mirroring
  QuantumLife) and `thesis/` LaTeX (6–8 pp, double-column) with both figures wired in and the
  positioning against prior work.
- **Acceptance criteria (derived from source §Thesis):**
  - AC-6.1 States the single defended claim: the ballistic→diffusive crossover depth is a
    chip-specific, reproducible fidelity metric set by two-qubit error rate — a
    "randomness-shape half-life" of the device.
  - AC-6.2 Includes the horns-melting figure (headline) and the collapse-curve figure.
  - AC-6.3 Frames the quantum walk as a known benchmark and the device-specific collapse curve
    as the contribution (§3.1); does not claim new quantum-walk physics.
  - AC-6.4 States the §6 out-of-scope items (no mitigation, single chip, Hadamard-only,
    device drift) as threats to validity; targets IEEE TQE (short) or IEEE QCE.
- **Depends on:** P4. **Out of scope:** new experiments (all data comes from P4).

## 10. Related work & positioning (novelty scan — 2026-08-06)

**Must cite and distinguish:**
- **Discrete-time quantum walk / quantum Galton board literature** (Aharonov et al.;
  Kempe survey; hardware DTQW demonstrations) — the ballistic-vs-diffusive spreading and
  twin-horn signature are established. This epic *does not* claim them as new; it measures the
  device-specific depth at which they die.
- **NISQ benchmarking via structured circuits** (volumetric benchmarks, mirror circuits) —
  position the collapse-knee as a physically-interpretable, single-number fidelity storyteller
  complementary to those, tied to a visible distribution shape.

**Builds on / internal prior work:**
- `../QuantumLife/` (Quantum Tree entanglement-correlation study) — reuses the exact Heron r2
  pipeline wiring (`pipeline_common` + `layout.best_chain`), the `run.json`/`summary.json`
  discipline, the `--sim` surrogate arm, the seeded-repeats spread, and the self-contained
  browser viewer. No overlap in the measured question (spatial correlation vs depth-collapse).
- `../CalibrationGuidedHighYieldQRNG/` — the source of the reused pipeline and calibration
  tooling; this study is a consumer, not a fork.
- `study-ideas/qh-2-temporal-drift-stability` and `qh-3-minimum-extraction-budget` — sibling
  reliability studies; the collapse-knee is their dynamic-systems sibling (source §Connection).

**Framing adjustment:** avoid any "quantum walk beats classical" novelty claim — the honest
and more defensible contribution is the chip-specific collapse curve (§3.1), which must
survive into P6.

## Appendix A — Heron r2 pipeline reuse runbook

Mirror of `../QuantumLife/README.md` "The pipeline for talking to IBM hardware is reused, not
copied". This study consumes the **live hardware pipeline**; it does not reimplement
submission.

- **A.1 — Import path.** `sys.path.insert(0, _CALIB_CODE)` where `_CALIB_CODE` points at
  `../CalibrationGuidedHighYieldQRNG/code/`, then
  `from pipeline_common import connect, run_sampler, timestamp` and
  `from layout import best_chain` (verbatim pattern from `QuantumLife/code/qtree.py:85-86`).
- **A.2 — Register naming.** The `ClassicalRegister` must be named `"c"` — required by
  `pipeline_common.run_sampler` (`QuantumLife/code/qtree.py:151`).
- **A.3 — Chain selection.** Re-pick the SWAP-free low-error chain from **live** calibration
  before every hardware run via `layout.best_chain`; never hardcode a stale qubit list
  (`layout.py` docstring). Chain length under the OQ-1 encoding sets the max walk depth `N`.
- **A.4 — Backend & account.** Backend name and IBM account env come from `config.py` (P1);
  the same saved IBM account QuantumLife/CalibrationGuidedHighYieldQRNG use works unchanged.
- **A.5 — Noisy arm comparability.** The `noisy` arm builds its device noise model from the
  same backend as the `hw` arm (`AerSimulator.from_backend`, OQ-5) so the two arms are
  apples-to-apples across the sweep.
