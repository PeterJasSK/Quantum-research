# Calibration-Guided High-Yield QRNG — Build Plan

**One-line goal:** from a single IBM Heron r2 calibration snapshot, produce a turnkey QRNG
config — *which qubits to use* and *how deep a mid-circuit measure-reset loop each sustains* —
and prove the extra bits stay random using the existing `ErrorDetectionVSRawBits` quality battery.

> **Framing (read once, repeat in the write-up):** the novelty is not a new randomness source.
> It is the claim that **one calibration read predicts both qubit quality and usable harvest
> depth**, so an optimal high-yield QRNG config is picked with *zero trial-and-error* on
> free-tier hardware. If the prediction fails (reset noise dominates, mid-circuit yield goes
> net-negative), that is still a publishable current-generation usability result. Say it that way.

**Source study:** `CalibrationGuidedHighYieldQRNG/1-calibration-guided-high-yield-qrng.md`
(paper strength 81/100). This plan operationalises it into **three parts**:

1. **EPIC 0 — Setup & measurement circuits.** Thesis scaffold + README, the reused pipeline, the
   calibration snapshot, and both measurement circuits (Stage A + Stage B) built and ready.
   *You then run them manually and collect the bit files.*
2. **EPIC 1 — Evaluation.** Score the Stage A and Stage B bits with the existing quality battery and
   emit the `qrng_compare.py` PDF report.
3. **Write-up (not an engineering epic).** Turn the numbers into the thesis / science paper.

---

## Locked decisions (from the source study)

| # | Decision |
|---|----------|
| 1 | Hardware is **IBM Heron r2** (ibm_fez / ibm_marrakesh / ibm_kingston), **Open plan / free tier**. Whole study stays under the ~10 min/month budget. |
| 2 | Reuse, do not rebuild: circuit-submission pipeline from `ErrorDetectionVSRawBits/qrng_bell_pairs.py`; quality battery from `ErrorDetectionVSRawBits/qrng_compare.py`. |
| 3 | **No new evaluation code.** The battery in `qrng_compare.py` (bias / NIST SP 800-22 / next-bit ML / Markov / min-entropy, plus SHA-512 whitening) is the measurement harness. It is *reused*, not reimplemented. |
| 4 | **Runs are manual.** EPIC 0 builds the circuits; the user submits jobs and collects the `bits:` files by hand. EPIC 1 starts from those files. |
| 5 | Every raw output file is saved **timestamped alongside its calibration snapshot** — results are device-and-date specific and must be reproducible as such. |
| 6 | **Baseline** = naive config: single-qubit Hadamard, 1 bit/qubit/shot, no qubit selection. Every gain is reported against this. **Headline** = usable bits per free-tier minute, optimal vs baseline. |

## Connection & reuse (what already exists)

- `qrng_bell_pairs.py` — live `QiskitRuntimeService` connection, `least_busy` Heron r2 pick,
  `backend.properties()` calibration reads (`t1`, `t2`, `readout_error`, `gate_error`,
  `faulty_qubits`), transpile + `SamplerV2` submission loop, `quantum_seconds` accounting, and
  the `bits:...\n` processed-file + `_raw.json` metadata output format. **Both measurement
  circuits fork this scaffold.**
- `qrng_compare.py` — `load_bits()`, `global_bias()`, `min_entropy_rate()`, `bias_splits()`,
  `strict_next_bit()` (bias-robust AUC), `markov_multi()`, `nist_battery()` (via `nist_pure.py`),
  `hash_extract()` (SHA-512, 75% kept), and the full PDF builder. **This is the evaluation harness.**
- Thesis result: Bell-pair output is statistically indistinguishable from ideal. This study moves
  the question from *"is it random?"* to *"how much usable randomness per free-tier minute?"*.

---

# EPICS

Each epic has a **Goal**, **Stories** (task checkboxes), and **Acceptance criteria (Done when…)**.
Priority: `[MUST]` core, `[SHOULD]` wanted, `[COULD]` stretch.

---

## EPIC 0 — Thesis setup & measurement circuits `[MUST]`

**Goal:** everything needed *before* running on hardware — the thesis scaffold and README, the
reused submission pipeline, one timestamped calibration snapshot, and **both measurement circuits
built and ready to submit**. Ends when the circuits are runnable; **you run them manually.**

- **S0.1 Thesis scaffold & README**
  - [ ] Create the study folder layout (code, `qrng_output/` for bit files, `results/` for scores
        and PDFs, `paper/` for the write-up).
  - [ ] Write `README.md` explaining the study: the research question (does one calibration read
        predict qubit quality *and* usable harvest depth?), the hypothesis, the two stages, the
        baseline, the metrics, and how to run each step. State the honest framing (decision box above).
- **S0.2 Device pick & pipeline reuse**
  - [ ] Fork `qrng_bell_pairs.py`'s scaffold (connect → transpile → `SamplerV2` loop →
        `quantum_seconds` accounting → `bits:` + `_raw.json` output). Do **not** rewrite it.
- **S0.3 Calibration snapshot**
  - [ ] Pull the live per-qubit snapshot: `T1`, `T2`, `readout_error`, `sx` gate error, and
        **reset error**. Save as `calib_<backend>_<ts>.json` — every later run anchors to this.
  - [ ] Tiny **measure-reset probe** job to confirm mid-circuit reset works on this device before
        committing the Stage B sweep.
- **S0.4 Stage A circuit — calibration-aware selection (also the baseline)**
  - [ ] Single-qubit Hadamard RNG applied to **every** qubit in parallel (one batch = whole chip).
        This is also the **naive baseline** (1 bit/qubit/shot, no selection).
  - [ ] Output writes **per-qubit** `bits:` streams + `_raw.json`, with the calibration snapshot
        attached. Print the shots needed for a meaningful per-qubit bitstream.
- **S0.5 Stage B circuit — mid-circuit measure-reset yield**
  - [ ] Loop circuit: prepare superposition → measure → reset → re-prepare → measure, repeated `k`
        times per qubit per shot, for `k = 1, 2, 4, 8, …` (depth sweep).
  - [ ] Parametrised to run on a chosen subset of qubits (the top-ranked qubits from Stage A, chosen
        after you evaluate Stage A). Output writes interleaved per-qubit, per-depth `bits:` streams.

**Done when:** README explains the study; the device is chosen and its calibration snapshot saved;
the measure-reset probe passes; and both circuits (Stage A whole-chip, Stage B depth sweep) run and
produce `bits:` + `_raw.json` files. **→ You now run the jobs and collect the bit files manually.**

---

## EPIC 1 — Evaluation of Stage A & Stage B `[MUST]`

**Goal:** take the manually collected bit files and turn them into the study's answer — per-qubit
and per-depth quality scores from the **existing** battery, the calibration→quality→usable-depth
analysis, and the publication **PDF** proving bit quality.

- **S1.1 Reuse the battery**
  - [ ] Import `analyze(arr)` from `qrng_compare.py` (returns bias, min-entropy, `bias_splits`,
        NIST, next-bit, Markov). Thin wrapper `evaluate_stream()` → flat verdicts using the existing
        `_stream_verdict()` rule (NIST ≥ 0.90 AND next-bit PASS AND Markov PASS).
  - [ ] Add the one metric the study needs that the battery lacks: **lag-1 serial correlation**
        between consecutive mid-circuit bits (for Stage B). Everything else reused as-is.
- **S1.2 Stage A evaluation → selection**
  - [ ] Score every per-qubit stream. Correlate each calibration property (`T1`, `T2`,
        `readout_error`, `sx` error, reset error) against each quality metric.
  - [ ] Fit a simple predictor (ranked regression) scoring expected quality from calibration alone;
        rank qubits; **select the top ~5** — these feed the Stage B run (back to S0.5, run manually).
- **S1.3 Stage B evaluation → usable depth**
  - [ ] For each qubit × depth: serial correlation, min-entropy, reset-induced bias, next-bit,
        Markov. Per qubit, find the **maximum depth where bits stay independent and unbiased** — the
        "usable depth".
- **S1.4 The join + headline**
  - [ ] Test whether the Stage-A calibration predictor **also** predicts each qubit's Stage-B usable
        depth (correlation + combined model). Report the answer either way.
  - [ ] Compute usable bits/qubit/shot and the **headline**: usable bits per free-tier minute at the
        calibration-optimal config vs the naive baseline.
- **S1.5 Quality PDF (reuse the report)**
  - [ ] Run `qrng_compare.py` on **baseline stream vs calibration-optimal harvested stream** to emit
        the native PDF (raw-vs-whitened, all-four-streams, bias / NIST / next-bit / Markov pages).
        This is the appendix figure set proving the bits are good.

**Done when:** every qubit and every qubit×depth has a battery score; the calibration predictor is
fit and its ability to predict usable depth is reported; the headline bits-per-free-tier-minute gain
vs baseline is computed; and the `qrng_compare.py` PDF is generated.

---

## Write-up — thesis / science paper (not an engineering epic)

**Goal:** turn EPIC 1's numbers into the thesis chapter / paper. No code.

- [ ] **The recipe (if it holds):** calibration snapshot → chosen qubits × harvest depth → optimal
      config, with zero trial-and-error. Present the correlation and combined model.
- [ ] **The headline:** usable bits per free-tier minute, optimal vs naive baseline, with the
      `qrng_compare.py` PDF as evidence the harvested bits pass the battery.
- [ ] **The honest failure case:** if reset noise dominates and mid-circuit yield is net-negative,
      state it — still a publishable current-gen usability result.
- [ ] **Reproducibility:** note **device + calibration date** prominently so the result and its
      aging are transparent. Target venues: IEEE QCE, Entropy, IEEE Access.

---

# Cross-cutting

## Evaluation criteria (reused verdict logic from `qrng_compare.py`)

| Metric | Source function | PASS condition |
|--------|-----------------|----------------|
| Global bias | `global_bias()` | low `|p1−0.5|`; reported, not a hard gate |
| Min-entropy/bit | `min_entropy_rate()` | near 1.0 is ideal |
| Bias per 20 splits | `bias_splits()` | low and flat, no drift |
| NIST SP 800-22 subset | `nist_battery()` | overall pass rate ≥ **0.90** |
| Next-bit predictability | `strict_next_bit()` | verdict **PASS** (AUC 95% CI includes 0.5) |
| Markov dependency | `markov_multi()` | verdict **PASS** (no order beats baseline) |
| Serial correlation (Stage B) | new lag-1 add-on | ≈ 0 |

A stream is **usable** when NIST ≥ 0.90 **AND** next-bit PASS **AND** Markov PASS (the existing
`_stream_verdict()` rule), plus serial-correlation ≈ 0 for mid-circuit harvested streams.

## Output artefacts (mirrors the existing `qrng_output/` convention)

| Artefact | From | Format |
|----------|------|--------|
| Calibration snapshot | EPIC 0 | `calib_<backend>_<ts>.json` (per-qubit T1/T2/readout/sx/reset) |
| Stage A per-qubit bits | manual run | `_raw.json` + `bits:...` processed, per qubit |
| Stage B depth-sweep bits | manual run | interleaved per-qubit, per-depth `bits:` streams + `_raw.json` |
| Per-stream scores | EPIC 1 | results table (CSV/JSON) keyed by qubit / qubit×depth |
| Comparison PDF | EPIC 1 | `qrng_compare.py` output (baseline vs optimal) |

## Flow (note the manual hand-off)

```
EPIC 0  build Stage A circuit ──► [you run it] ──► per-qubit bits
                                                        │
EPIC 1  evaluate Stage A ──► top-5 qubits ──► [you run Stage B on top-5] ──► depth bits
                                                        │
EPIC 1  evaluate Stage B ──► usable depth ──► join + headline ──► qrng_compare.py PDF
                                                        │
Write-up  thesis / paper
```

## Risks & mitigations

- **Mid-circuit reset unsupported / noisy** → S0.3 probe first; if net-negative, that becomes the
  honest failure result in the write-up.
- **Calibration drifts mid-study** → anchor every run to its own snapshot (decision #5); never mix
  streams across snapshots when fitting the predictor.
- **Free-tier budget** → Stage A is one whole-chip job; Stage B is a few small jobs on ~5 qubits.
  Track `quantum_seconds` (reused accounting) to stay under budget.
- **Predictor overfits ~5 qubits** → keep the model simple, report correlation strength honestly.

## Definition of Done (whole study)

- [ ] README explains the study; thesis folder scaffold in place.
- [ ] Device chosen; calibration snapshot (incl. reset error) saved; measure-reset probe passes.
- [ ] Both measurement circuits built and runnable (Stage A whole-chip, Stage B depth sweep).
- [ ] Stage A & Stage B bits collected (manual runs) and scored with the reused battery.
- [ ] Calibration→quality predictor fit; its ability to predict usable depth reported either way.
- [ ] Headline bits/free-tier-minute vs baseline computed; `qrng_compare.py` PDF generated.
- [ ] Thesis / paper written, stating device + calibration date and the failure case honestly.

## Stretch `[COULD]`

- [ ] Repeat on a second Heron r2 device to test cross-device generalisation of the predictor.
- [ ] Re-run Stage A on two calibration dates to show how fast the recipe ages (temporal drift).
