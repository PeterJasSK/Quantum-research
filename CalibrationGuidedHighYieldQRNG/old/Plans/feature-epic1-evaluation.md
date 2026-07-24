# Feature Plan — EPIC 1: Evaluation of Stage A & Stage B

**Status:** Approved (awaiting approval)
**Owning epic:** `CalibrationGuidedHighYieldQRNG/Plans/CALIBRATION_QRNG_BUILD_PLAN.md` → EPIC 1 `[MUST]`
**Source study:** `CalibrationGuidedHighYieldQRNG/Plans/1-calibration-guided-high-yield-qrng.md`
**Slug:** `evaluation`

> No automated tests (project directive). Production code + manual verification only.
> No quantum-hardware runs in this epic (developer directive): EPIC 1 is pure offline analysis of
> the bit files EPIC 0's manual runs produced. Nothing here submits a job.

---

## §1 Context

EPIC 0 built and ran (manually) the two measurement circuits and produced timestamped bit files
under `qrng_output/`. EPIC 1 takes those files and turns them into the study's answer:

1. **Reuse the battery** (`ErrorDetectionVSRawBits/qrng_compare.py`) to score every reconstructed
   stream, plus one new metric the battery lacks (lag-1 serial correlation).
2. **Stage A → selection:** score every per-qubit stream, correlate each calibration property
   against each quality metric, fit a simple predictor from calibration alone, rank qubits, select
   the top ~5. That list is fed back to EPIC 0's `stage_b_yield.py --qubits …` (manual run).
3. **Stage B → usable depth:** score every qubit×depth stream, find each qubit's maximum usable
   measure-reset depth.
4. **The join + headline:** test whether the Stage-A calibration predictor also predicts each
   qubit's Stage-B usable depth; compute the headline — usable bits per free-tier minute at the
   calibration-optimal config vs the naive baseline.
5. **Quality PDF:** run the existing `qrng_compare.py` on baseline-vs-optimal to emit its native PDF.

**Reuse base (decisions #2/#3, do not rebuild):**

- `ErrorDetectionVSRawBits/qrng_compare.py` — the battery. Key surface EPIC 1 imports:
  `load_bits(path, max_bits=0) -> np.int8[]` (strips a leading `bits:` prefix), `analyze(arr) -> dict`
  (`{n_bits, global_bias, min_entropy_per_bit, bias_splits, nist, next_bit, markov}`),
  `_stream_verdict(r) -> (verdict, nist_ok, nb_ok, mk_ok)` (PASS iff
  `nist.overall_pass_rate >= 0.90` **AND** `next_bit.verdict=="PASS"` **AND** `markov.verdict=="PASS"`),
  `hash_extract(arr, ratio=0.75)`, and the `main()` CLI (`file1 file2 -o out.pdf -n bits`) that
  builds the matplotlib PDF. `nist_battery` lives in `nist_pure.py` (same directory).
- EPIC 0 output schemas (both keyed off `run["strategy"]`):
  - **Stage A** `_raw.json`: `{run, calibration, jobs, raw_measurements}`. `run.qubits_used` is the
    ordered physical-qubit list; `raw_measurements` is one **unreversed** creg string per shot.
  - **Stage B** `_raw.json`: `{run, calibration, depths:[…]}`. Each `depths[j]` = `{depth,
    creg_size, qubit_list, slot_layout, n_qubits, shots, total_bits, quantum_seconds, jobs,
    raw_measurements}` with rep-major slots (`slot = rep*n_qubits + qubit_index`).
  - **Calibration** is embedded in each `_raw.json` under `calibration` as the flat per-qubit dict
    keyed `"0","1",…` with `{t1, t2, readout_error, sx_error, reset_error}` (T1/T2 in seconds,
    `reset_error` may be `null`). The standalone `calib_*.json` wraps the same dict under `"qubits"`.

This is a Python/Qiskit research study, not the Symfony/GitHub-issue workflow the `/plan-feature`
template assumes and not the FastAPI+Next QRNG-EaaS project. There is no GitHub issue: the "ticket"
is EPIC 1, and the ACs below are lifted verbatim from the epic's stories (S1.1–S1.5) and its
Done-when clause. There is no `_plan-template.md`; this plan mirrors the EPIC 0 feature-plan layout.

---

## §2 Acceptance criteria (verbatim from EPIC 1)

Copied from the epic's stories S1.1–S1.5 and Done-when. Each gets an ID.

**S1.1 — Reuse the battery**
- **AC-1** Import `analyze(arr)` from `qrng_compare.py` (returns bias, min-entropy, `bias_splits`,
  NIST, next-bit, Markov). Thin wrapper `evaluate_stream()` → flat verdicts using the existing
  `_stream_verdict()` rule (NIST ≥ 0.90 AND next-bit PASS AND Markov PASS).
- **AC-2** Add the one metric the study needs that the battery lacks: **lag-1 serial correlation**
  between consecutive mid-circuit bits (for Stage B). Everything else reused as-is.

**S1.2 — Stage A evaluation → selection**
- **AC-3** Score every per-qubit stream. Correlate each calibration property (`T1`, `T2`,
  `readout_error`, `sx` error, reset error) against each quality metric.
- **AC-4** Fit a simple predictor (ranked regression) scoring expected quality from calibration
  alone; rank qubits; **select the top ~5** — these feed the Stage B run (back to S0.5, run
  manually).

**S1.3 — Stage B evaluation → usable depth**
- **AC-5** For each qubit × depth: serial correlation, min-entropy, reset-induced bias, next-bit,
  Markov. Per qubit, find the **maximum depth where bits stay independent and unbiased** — the
  "usable depth".

**S1.4 — The join + headline**
- **AC-6** Test whether the Stage-A calibration predictor **also** predicts each qubit's Stage-B
  usable depth (correlation + combined model). Report the answer either way.
- **AC-7** Compute usable bits/qubit/shot and the **headline**: usable bits per free-tier minute at
  the calibration-optimal config vs the naive baseline.

**S1.5 — Quality PDF (reuse the report)**
- **AC-8** Run `qrng_compare.py` on **baseline stream vs calibration-optimal harvested stream** to
  emit the native PDF (raw-vs-whitened, all-four-streams, bias / NIST / next-bit / Markov pages).
  This is the appendix figure set proving the bits are good.

**Done when (AC-9):** every qubit and every qubit×depth has a battery score; the calibration
predictor is fit and its ability to predict usable depth is reported; the headline
bits-per-free-tier-minute gain vs baseline is computed; and the `qrng_compare.py` PDF is generated.

---

## §3 Scope

### In scope
- A shared EPIC 1 helper module: battery import shim, `evaluate_stream()`, lag-1 serial
  correlation, stream reconstruction (Stage A per-qubit, Stage B per-qubit-per-depth), and
  results IO to `results/`.
- Stage A evaluation script: per-qubit scoring, calibration↔quality correlations, predictor fit,
  ranking, top-N selection.
- Stage B evaluation script: per-qubit-per-depth scoring, usable-depth determination.
- Join + headline script: predictor→usable-depth test, bits/qubit/shot and bits/free-tier-minute
  headline vs baseline.
- Quality-PDF emitter: build the calibration-optimal harvested `_processed.txt`, then invoke the
  existing `qrng_compare.py` CLI to produce the PDF.

### Out of scope (deferred to EPIC 0 manual runs / write-up)
- Running any quantum job (Stage A/B submission is EPIC 0, manual — decision #4; also the developer
  directive: no hardware runs here).
- Editing anything under `ErrorDetectionVSRawBits/` (decision #2). The battery is imported, never
  modified.
- The thesis/paper prose — write-up phase.
- Cross-device / temporal-drift repeats — Stretch `[COULD]`.
- Re-deriving or reimplementing any battery metric other than serial correlation (AC-2).

---

## §4 Decisions (this ticket)

Adopted from the epic without restating rationale (reuse not rebuild; battery verdict rule; naive
baseline = Stage A `--select all`; anchor every result to its source run's snapshot/timestamp; keep
the predictor simple). New decisions this ticket needs:

- **E1 — Import the battery via `sys.path`, never by editing or copying it.** `eval_common.py`
  computes the repo root from `__file__` (three `dirname`s up from `code/eval_common.py`) and
  inserts `<repo_root>/ErrorDetectionVSRawBits` onto `sys.path`, then
  `from qrng_compare import analyze, _stream_verdict, load_bits, hash_extract`. `nist_pure` resolves
  from the same directory (qrng_compare imports it relatively). No file under
  `ErrorDetectionVSRawBits/` is touched. The PDF (AC-8) reuses `qrng_compare.py`'s own `main()` via
  `subprocess`, not a reimplementation.
- **E2 — Reconstruction branches on `run["strategy"]`.**
  - Stage A per-qubit: for `raw_measurements` shot string `s`, reverse it (`s[::-1]`); string index
    `i` ↔ physical qubit `run["qubits_used"][i]`. Qubit `q`'s stream = `"".join(s[::-1][i] …)` over
    all shots in list order, where `i = qubits_used.index(q)`.
  - Stage B per-qubit-per-depth: for a `depths[j]` entry, reverse each shot string `r = s[::-1]`
    (length `n*depth`); qubit `qubit_list[i]` at rep `rep` is `r[rep*n + i]` (rep-major). A qubit's
    depth-`k` stream = those bits across all shots and reps, in (shot, rep) order — so consecutive
    entries are the temporally consecutive mid-circuit bits the serial-correlation metric needs.
- **E3 — Lag-1 serial correlation (AC-2) lives in `eval_common.py`.** `serial_correlation(arr) ->
  float` = Pearson `r` between `arr[:-1]` and `arr[1:]` (0.0 for a constant stream). PASS gate:
  `|r| * sqrt(N-1) < 1.96` (two-sided α=0.05 large-sample test) — i.e. `r` not significantly
  non-zero (§11 Q1). Reported for every stream; only *gating* for Stage B usable-depth.
- **E4 — Usable depth (AC-5) = the largest depth `k` in the sweep such that every depth `≤ k` for
  that qubit is "usable".** A depth-`k` stream is usable when `_stream_verdict` is PASS **and** the
  serial-correlation gate passes **and** `|global_bias|` is below the same magnitude the depth-1
  stream shows for that qubit (reset-induced bias did not grow materially — §11 Q2/Q6). Contiguous
  (not just "any passing k") so the reported depth is a sustainable harvest depth, not a lucky
  outlier. If depth 1 itself fails, usable depth = 0 and that qubit is flagged.
- **E5 — Predictor (AC-4) is a simple, fully-reported linear model.** Features = the five
  calibration properties per qubit (`t1, t2, readout_error, sx_error, reset_error`),
  standardized; qubits whose `reset_error` is `null` get it mean-imputed and flagged. Target =
  per-qubit `min_entropy_per_bit` from `analyze()` (continuous, always available regardless of NIST
  eligibility — §11 Q3). Model = `sklearn.linear_model.Ridge` (already a battery dependency);
  additionally report per-feature Spearman correlation (`scipy.stats.spearmanr`) of each raw
  property vs each quality metric (AC-3). Rank qubits by predicted quality; select the top `N`
  (default 5, `--top`).
- **E6 — Per-qubit NIST ineligibility counts as FAIL.** Per-qubit Stage A streams are short
  (≈ shots bits/qubit; even a 1 M-bit whole-chip run gives only ~shots per qubit), so many NIST
  tests are ineligible. `evaluate_stream()` records NIST exactly as the battery returns it
  (`tests_run` may be 0). When `tests_run == 0` the NIST leg is **FAIL** — `overall_pass_rate` is
  0.0, so `_stream_verdict` returns FAIL unchanged (no fallback). The row carries an `nist_na=True`
  flag so the write-up can distinguish "failed NIST" from "too few bits to run NIST", but the stream
  verdict is FAIL either way (§11 Q5). The predictor target (E5) uses min-entropy, which is still
  computed regardless — so an `nist_na` qubit still gets a quality score and a rank.
- **E7 — Results are written to `results/`, keyed and anchored to the source run.** Each evaluation
  writes both a machine-readable JSON and a flat CSV, named from the source `_raw.json` stem (e.g.
  `results/stagea_<backend>_<ts>_scores.csv`). No timestamp of its own — results inherit the run's
  timestamp so they stay device-and-date anchored (decision #5). JSON via `json.dump`; CSV via the
  stdlib `csv` module. No database, no raw SQL.
- **E8 — Headline (AC-7) uses measured QPU seconds from the run metadata.** For each config compute
  usable-bits-per-shot and usable-bits-per-quantum-second (`total_bits`/`quantum_seconds` scaled by
  the usable fraction), then ×60 for per-free-tier-minute. Baseline config = Stage A `--select all`
  (usable bits/shot = count of qubits whose stream passes). Optimal config = top-`N` qubits, each at
  its usable depth (usable bits/shot = Σ usable_depth). Report the ratio; if optimal ≤ baseline,
  state it plainly as the honest failure case (epic framing).
- **E9 — Strict, fully-typed Python** with `from __future__ import annotations`, PEP 8, type hints
  on every function signature; matches the EPIC 0 / battery idioms (numpy, sklearn, scipy,
  matplotlib already present). Each script has a `main()` + argparse and a module docstring.

---

## §5 File plan

All paths under `CalibrationGuidedHighYieldQRNG/`. New files unless noted. No edits anywhere under
`ErrorDetectionVSRawBits/`.

| Path | Change | Purpose |
|------|--------|---------|
| `code/eval_common.py` | new | AC-1, AC-2, E1–E3, E6, E7. Battery import shim (`sys.path` → `ErrorDetectionVSRawBits`); `evaluate_stream(bits: str) -> dict` (calls `analyze`, applies `_stream_verdict` with the E6 NIST-N/A fallback, appends `serial_correlation`); `serial_correlation(arr) -> float` + `serial_corr_ok(r, n) -> bool` (E3); `load_run(path) -> dict`; `reconstruct_stage_a(raw) -> dict[int, str]`; `reconstruct_stage_b(raw) -> dict[tuple[int, int], str]` (keyed `(qubit, depth)`); `calibration_of(raw) -> dict[int, dict]`; `write_json(path, obj)` / `write_csv(path, rows, fieldnames)`; `RESULTS_DIR = "results"`. |
| `code/evaluate_stage_a.py` | new | AC-3, AC-4, E4-adjacent, E5, E7. `main()` loads a `stagea_*_raw.json`, reconstructs per-qubit streams, scores each via `evaluate_stream`, computes per-feature↔per-metric Spearman correlations, fits the Ridge predictor (E5), ranks qubits, selects top-`N` (`--top`, default 5). Writes `results/stagea_<backend>_<ts>_scores.{json,csv}`, `results/stagea_<backend>_<ts>_correlations.json`, `results/stagea_<backend>_<ts>_predictor.json`. Prints the ready-to-paste `--qubits q1,q2,…` line for the manual Stage B run. |
| `code/evaluate_stage_b.py` | new | AC-5, E2–E4, E7. `main()` loads a `stageb_*_raw.json`, reconstructs per-qubit-per-depth streams, scores each (serial correlation, min-entropy, reset-induced bias, next-bit, Markov via `evaluate_stream`), applies the E4 usable-depth rule per qubit. Writes `results/stageb_<backend>_<ts>_scores.{json,csv}` (one row per qubit×depth) and `results/stageb_<backend>_<ts>_usable_depth.json` (one usable depth per qubit + the flag). |
| `code/join_and_headline.py` | new | AC-6, AC-7, E8. `main()` loads a Stage A predictor JSON + a Stage B usable-depth JSON (paths via argv), tests whether predicted quality (and each raw calibration property) predicts usable depth — Spearman + a combined Ridge model — and computes the headline (E8): usable bits/qubit/shot, usable bits/free-tier-minute for baseline vs optimal, and the ratio. Writes `results/headline_<backend>_<ts>.json` and prints the summary (including the honest-failure verdict when optimal ≤ baseline). |
| `code/emit_quality_pdf.py` | new | AC-8, E1. `main()` takes the baseline `_processed.txt` (Stage A `--select all`) and a Stage B `_raw.json` + usable-depth JSON; reconstructs the calibration-optimal harvested stream (top-`N` qubits each truncated to its usable depth) and writes `results/optimal_harvested_<backend>_<ts>_processed.txt` (`bits:…`); then invokes the existing battery via `subprocess.run([sys.executable, "<repo>/ErrorDetectionVSRawBits/qrng_compare.py", baseline_txt, optimal_txt, "-o", "results/qrng_compare_<backend>_<ts>.pdf"])`. The PDF itself is 100% the reused report — this script only assembles its two input files and shells out. |

### Key implementation notes
- **AC-1 fidelity:** `evaluate_stream` calls `analyze(arr)` and `_stream_verdict(r)` exactly as the
  battery defines them — no reimplementation of bias / NIST / next-bit / Markov. The only additions
  are the appended serial-correlation and the `nist_na` flag (E6); neither changes the verdict rule
  (NIST-ineligible already yields `overall_pass_rate == 0.0` → FAIL).
- **AC-2 / E3:** `serial_correlation` operates on the int8 array `analyze` already uses; guard the
  zero-variance case (constant stream → return 0.0). The gate is the only new PASS condition and it
  applies to Stage B streams (mid-circuit), per the epic's metrics table.
- **E2 reversal is the single source of truth.** Both reconstructors use the same `s[::-1]`
  convention EPIC 0's `process()` uses, so per-qubit reconstruction and the aggregate
  `_processed.txt` agree bit-for-bit. Spot-check one qubit's reconstructed bias against
  `run["bias"]` sanity in manual verification.
- **E5 predictor stays small:** five features, one Ridge fit, coefficients + R² reported in
  `predictor.json`. With only ~5 selected qubits downstream the epic warns against overfitting —
  the model is fit on **all** Stage A qubits (whole chip), not just the top 5, and its honest
  correlation strength is reported (epic Risks).
- **No hardware, no network:** every script reads existing files under `qrng_output/` and writes
  under `results/`. None import `pipeline_common.connect` or any Qiskit runtime path.
- **No raw SQL / no DB** — pure numpy/sklearn/scipy + JSON/CSV files, matplotlib PDF via the reused
  battery.

---

## §6 Manual verification

No automated tests; no hardware runs. Verify by hand against the EPIC 0 sample files already in
`qrng_output/` (and against full manual runs once collected):

1. **Battery import (AC-1):** `python -c "import sys; sys.path.insert(0,'code'); import eval_common"`
   from `CalibrationGuidedHighYieldQRNG/` succeeds — confirms the `sys.path` shim reaches
   `qrng_compare` + `nist_pure` without editing them.
2. **Stage A eval (AC-3/4):** `python code/evaluate_stage_a.py qrng_output/stagea_ibm_marrakesh_20260714-210551_raw.json --top 5`.
   Confirm `results/stagea_*_scores.{json,csv}` (one row per qubit, verdict + metrics + `nist_na`
   flag where applicable), `results/stagea_*_correlations.json` (each property × each metric
   Spearman), `results/stagea_*_predictor.json` (coefficients + R²), and a printed
   `--qubits q1,q2,…` line. Sanity: a reconstructed qubit's bias is finite and the aggregate matches
   `run["bias"]` order of magnitude.
   *(Note: the 100-shot sample gives ~100 bits/qubit — NIST will be N/A and next-bit/Markov
   marginal; this exercises the code path. Trustworthy numbers need the ~1 M-bit manual run.)*
3. **Stage B eval (AC-5):** once a `stageb_*_raw.json` exists (manual run), run
   `python code/evaluate_stage_b.py qrng_output/stageb_<backend>_<ts>_raw.json`. Confirm
   `results/stageb_*_scores.csv` has one row per qubit×depth with serial-correlation, min-entropy,
   reset-induced bias, next-bit and Markov verdicts, and `results/stageb_*_usable_depth.json` gives
   each qubit a usable depth (0 if depth-1 fails).
4. **Join + headline (AC-6/7):** `python code/join_and_headline.py results/stagea_*_predictor.json results/stageb_*_usable_depth.json`.
   Confirm `results/headline_*.json` with the predictor→usable-depth Spearman + combined-model
   result and the baseline-vs-optimal bits/free-tier-minute ratio; confirm the printed summary
   states the honest-failure verdict when optimal ≤ baseline.
5. **Quality PDF (AC-8):** `python code/emit_quality_pdf.py <baseline_processed.txt> <stageb_raw.json> results/stageb_*_usable_depth.json`.
   Confirm `results/optimal_harvested_*_processed.txt` (`bits:…`) is written and
   `results/qrng_compare_*.pdf` is produced by the reused battery (7 pages: summary / bias / global
   bias / NIST / next-bit / Markov / conclusions, four streams).
6. **Done-when (AC-9):** every qubit and qubit×depth has a scored row; predictor fit and its
   usable-depth prediction reported; headline computed; PDF generated — all artefacts present under
   `results/`.

---

## §7 Carried decisions (from the epic)

- Reuse, do not rebuild the battery (decisions #2, #3): `qrng_compare.py` / `nist_pure.py` imported,
  never edited.
- Verdict rule = the existing `_stream_verdict()` (NIST ≥ 0.90 AND next-bit PASS AND Markov PASS),
  plus serial-correlation ≈ 0 for Stage B (cross-cutting evaluation-criteria table).
- Baseline = naive single-qubit Hadamard, 1 bit/qubit/shot, no selection = Stage A `--select all`
  (decision #6); every gain reported against it.
- Headline = usable bits per free-tier minute, calibration-optimal vs baseline (decision #6).
- Every result anchored to its source run's device + calibration snapshot + timestamp (decision #5);
  never mix streams across snapshots when fitting the predictor.
- Runs are manual (decision #4): EPIC 1 consumes files; the Stage B run that follows Stage A
  selection is a manual hand-off with the printed `--qubits` list.

---

## §8 Troubleshooting

- **`qrng_compare` import fails:** confirm the `sys.path` shim points at `<repo>/ErrorDetectionVSRawBits`
  (three `dirname`s up from `code/eval_common.py`); confirm numpy/sklearn/scipy/matplotlib are
  installed (same env EPIC 0 used).
- **NIST reports `tests_run == 0`:** expected for short per-qubit streams — the stream verdict is
  FAIL and the row is flagged `nist_na=True` (E6) so the write-up can distinguish "failed" from "too
  few bits". The qubit still gets a min-entropy quality score and a rank. Real confidence needs the
  ~1 M-bit manual runs.
- **Per-qubit index misalignment:** re-check the `s[::-1]` reversal and that `qubits_used`/`qubit_list`
  order matches `initial_layout`; spot-check one qubit's reconstructed bias.
- **Stage B `raw_measurements` length ≠ `n*depth`:** the run is malformed for that depth — skip the
  depth and flag it; do not silently pad.
- **`reset_error` is `null` for every qubit (device exposes none):** E5 mean-imputes and flags it;
  the predictor is then effectively four-feature — report that honestly.
- **Predictor R² is low / near zero:** that is a valid result (calibration does not predict quality
  on this device/date) — report it, do not tune until it looks good (epic Risks: overfit ~5 qubits).
- **Optimal ≤ baseline in the headline:** the honest failure case — mid-circuit yield went
  net-negative; state it as a publishable current-gen usability result (epic framing).

---

## §11 Open questions — RESOLVED

All resolved by developer 2026-07-14; answers folded into §4/§5.

- **Q1 — Serial-correlation PASS threshold.** ✅ Statistical: PASS iff `|r| * sqrt(N-1) < 1.96`
  (two-sided α=0.05) (E3).
- **Q2 — Usable-depth rule.** ✅ Contiguous — largest `k` such that *all* depths `≤ k` pass (E4).
- **Q3 — Predictor quality target.** ✅ Regress on per-qubit `min_entropy_per_bit` (E5).
- **Q4 — Selection count `N`.** ✅ Default 5, overridable with `--top` (E5).
- **Q5 — NIST-ineligible verdict.** ✅ `tests_run == 0` → NIST leg FAIL → stream verdict FAIL. Row
  still flagged `nist_na=True` and still gets a min-entropy quality score/rank (E6). No fallback.
- **Q6 — "Reset-induced bias" definition (Stage B).** ✅ Per qubit, growth of `|global_bias|` at
  depth `k` relative to that qubit's depth-1 bias; the usable gate requires it not exceed the
  depth-1 magnitude materially (E4).

---

**Plan ready for review.** Do not run implementation from this command; after approval run
`/implement-feature CalibrationGuidedHighYieldQRNG/Plans/feature-epic1-evaluation.md`.
