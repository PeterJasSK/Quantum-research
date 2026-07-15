# Feature Plan — EPIC 2: Band-stratified evaluation (best / next / worst)

**Status:** Complete
**Owning epic:** `CalibrationGuidedHighYieldQRNG/Plans/CALIBRATION_QRNG_BUILD_PLAN.md` → EPIC 2 `[MUST]`
**Source study:** `CalibrationGuidedHighYieldQRNG/Plans/1-calibration-guided-high-yield-qrng.md`
**Slug:** `band-stratified-evaluation`

> No automated tests (project directive). Production code + manual verification only.
> **No new hardware runs.** The three bands are already on disk (best/next/worst Stage B runs).
> EPIC 2 is pure offline re-analysis of existing bit files. Nothing here submits a job.

---

## §1 Context — and why the question is now different

### What actually happened on the metal
EPIC 1 assumed one Stage B run: score Stage A → pick the **top-5** qubits → harvest mid-circuit on
those five → test the predictor on those five. A last-minute call at run time changed that: Stage B
was submitted on **three bands of five qubits each**, spanning the full calibration ranking —

| Band | Stage-A predictor rank | Qubits (as run) | Canonical `_raw.json` |
|------|------------------------|-----------------|-----------------------|
| **best** | 1–5 | `98,10,14,75,154` | `stageb_ibm_marrakesh_20260714-214816_raw.json` (20000 shots/depth) |
| **next** | 6–10 | `0,86,132,42,54` | `stageb_ibm_marrakesh_20260714-215558_raw.json` |
| **worst** | 152–156 (absolute bottom-5) | `39,91,113,119,82` | `stageb_ibm_marrakesh_20260714-215818_raw.json` |

All three swept depths `1,2,4,8`. A fourth file, `…-214301_raw.json`, is a **10-shot probe of the
best band — discard it** (superseded by the 20000-shot `…-214816`).

### How three bands reframe the research question
This is not a cosmetic "more data" change. The top-5-only design in EPIC 1 could **not actually test
the study's central claim**, and the three-band design repairs that:

1. **Range restriction killed the EPIC 1 join.** Selecting the top-5 on calibration and then
   correlating calibration-predicted quality against usable depth *within those five* conditions on
   the winners: their predicted qualities are nearly identical, x-variance ≈ 0, and
   `join_and_headline.predictor_test` returns `rho=0` by construction (it even guards `n<3` and
   zero-std). You cannot learn "does calibration predict yield" from the winners alone — that is a
   classic range-restriction null.
2. **Confirmation → falsification.** Harvesting only where you predicted success can confirm but
   never refute. The **worst-5 band is the control**: if the worst qubits yield as much usable depth
   as the best, the calibration→depth claim is *refuted*, and now you can see it. The honest-failure
   branch finally has teeth.
3. **Point estimate → gradient (dose–response).** With 15 qubits spanning the ranked spectrum, the
   sharp question becomes: **does empirical usable depth increase monotonically best → next →
   worst?** That is an ordered-groups trend test plus a full-range Spearman — a far stronger result
   than a single point, and it is only computable now.
4. **The headline gains its true form.** EPIC 1's headline was *optimal vs naive baseline* (Stage A
   `--select all`), which conflates two effects: harvesting depth exists at all, and calibration
   selection is worth anything. Three bands separate them. The new headline is **best-band vs
   worst-band usable-bits/free-tier-minute** — the value of *choosing well by calibration*, isolated
   from the value of harvesting at all. Baseline→any-band = "harvest exists"; best↔worst spread =
   "calibration selection has value."

**One-line reframe:** the study moves from *"we harvested extra bits on qubits calibration liked"*
(confirmatory, underpowered, no control) to *"a single calibration read orders empirical harvest
yield across the quality spectrum"* (falsifiable, controlled, gradient) — same hardware already
spent, dramatically stronger inference.

### A data-quality fact this epic must handle
The predictor and band ranking that were **live at run time** were fit on the **100-shot** Stage A
probe (`…-210551`, R²=0.051 ≈ noise), not the **65000-shot** Stage A run (`…-210803`). The band
membership is therefore frozen as-run from a weak ranking. EPIC 2 does **not** re-assign bands (the
hardware is spent) but **does** re-fit the Stage-A quality/predictor on the 65000-shot run so that
`predicted_quality` in the join is meaningful. The near-zero R² is itself a finding and is exactly
*why* the three-band gradient is the only route to a defensible signal (or an honest null).

### Reuse base (decisions #2/#3, do not rebuild)
- Battery `ErrorDetectionVSRawBits/qrng_compare.py` — unchanged, imported via `eval_common`.
- EPIC 1 code is reused, not rewritten: `eval_common.evaluate_stream / reconstruct_stage_b /
  load_run / calibration_of / write_json / write_csv / stem_of`; `evaluate_stage_b.score_depths /
  usable_depths / is_usable`; `evaluate_stage_a.score_qubits / calibration_matrix / fit_predictor`;
  `join_and_headline.headline`; `emit_quality_pdf` for the PDF.

---

## §2 Acceptance criteria

**S2.1 — Band registry & provenance**
- **AC-1** ✅ `code/band_registry.py` — `BAND_FILES` maps best/next/worst to the canonical
  `_raw.json` (band_registry.py:19-24), `DISCARDED_PROBE` names the `…-214301` probe as excluded
  (band_registry.py:26), `verify_against_ranking()` checks each band's `qubit_list` against the
  100-shot run-time predictor slice and raises `ValueError` on mismatch (band_registry.py:59-77).
  Ran clean: `best [98,10,14,75,154]`, `next [0,86,132,42,54]`, `worst [39,91,113,119,82]`,
  "Ranking guard passed."

**S2.2 — Proper Stage-A quality for the join**
- **AC-2** ✅ `code/evaluate_bands.py:refit_stage_a_predictor()` (evaluate_bands.py:23-33) re-runs
  `evaluate_stage_a`'s `score_qubits/calibration_matrix/correlate/fit_predictor` on
  `stagea_ibm_marrakesh_20260714-210803_raw.json` (65000-shot). Recorded R² = **0.4842** (vs
  0.051 on the 100-shot run the bands were frozen from) — printed and written to
  `results/bands_ibm_marrakesh_bands_stagea_predictor_65000shot.json`. Band membership untouched
  (loaded verbatim from the registry).

**S2.3 — Band-aware Stage B evaluation**
- **AC-3** ✅ `code/evaluate_bands.py:score_band()` (evaluate_bands.py:57-83) reuses
  `evaluate_stage_b.score_depths/usable_depths` per band, one row per qubit (15 total) with
  `band`, `predicted_quality`, `rank`, `usable_depth`, `flagged`, and per-depth
  `min_entropy_per_bit_d{1,2,4,8}` / `serial_correlation_d{…}` / `global_bias_d{…}` /
  `verdict_d{…}` columns. Output: `results/bands_ibm_marrakesh_bands_combined.csv` (15 rows,
  verified by the script's own row-count assertion).

**S2.4 — Gradient / trend test (the reframed core)**
- **AC-4** ✅ `code/band_trend.py:gradient_tests()` (band_trend.py:52-69) — Spearman
  `predicted_quality` vs `usable_depth`: **rho=0.646, p=0.009** over the 15 qubits; each raw
  calibration feature (`t1,t2,readout_error,sx_error,reset_error`) vs `usable_depth` also computed
  and written to `results/bands_ibm_marrakesh_bands_trend.json`.
- **AC-5** ✅ `code/band_trend.py:ordered_band_trend()` (band_trend.py:87-104) — Kruskal-Wallis +
  monotone best≥next≥worst check on `usable_depth` (H=7.113, p=0.029, monotone=True, means
  best=2.6/next=1.0/worst=0.2), min-entropy at depth-1 and depth-8, and |serial-correlation| at
  depth-1 and depth-8 — all reported in `trend.json` regardless of significance (D-E2.4: no
  Jonckheere-Terpstra, scipy `kruskal` + ordinal Spearman only).

**S2.5 — Reframed headline**
- **AC-6** ✅ `code/band_headline.py` — per-band usable-bits/qubit/shot and usable-bits/free-tier
  minute (band_headline.py:31-48); best-vs-worst ratio **13.000**, best-vs-next ratio **2.600**
  (band_headline.py:93-95); reused baseline-vs-best ratio **0.018** (band_headline.py:55-72, 105) —
  low because the naive 156-qubit baseline out-throughputs a 5-qubit harvest on raw bit count, per
  the epic's decision that baseline-vs-band tests "harvest exists" while best-vs-worst tests
  "calibration selection has value"; `monotone_across_bands` = **True** (band_headline.py:106);
  verdict wording branches GAIN vs honest-failure (band_headline.py:108-116). Output:
  `results/bands_ibm_marrakesh_bands_headline.json`.

**S2.6 — Band-stratified quality PDF**
- **AC-7** ✅ Ran the unmodified `code/emit_quality_pdf.py` twice against
  `qrng_output/stagea_ibm_marrakesh_20260714-210803_processed.txt` (the Stage-A `--select all`
  baseline) — once vs `stageb_…-214816_raw.json` (best band, 260,000 harvested bits) →
  `results/qrng_compare_ibm_marrakesh_20260714-214816.pdf`; once vs `stageb_…-215818_raw.json`
  (worst band, 20,000 harvested bits — matches the expected mostly-zero worst-band shape, D-E2.5)
  → `results/qrng_compare_ibm_marrakesh_20260714-215818.pdf`. Both PDFs generated successfully.

**Done when:** the registry resolves all three bands (probe discarded); Stage-A quality is re-fit on
the 65000-shot run; the 15-qubit combined table exists; the Spearman + calibration-vs-yield
correlations and the ordered-band trend test are computed and reported either way; the per-band
headline with best-vs-worst ratio and monotone flag is written; and both band PDFs are generated.

---

## §3 Scope

**In:** offline re-analysis of existing bit files; new band-registry + trend/gradient analysis;
extended headline; two PDF emissions; re-run of Stage-A eval on the 65000-shot file.

**Out:** any hardware submission; new metrics beyond what the battery + lag-1 serial correlation
already provide; editing anything under `ErrorDetectionVSRawBits/`; re-assigning band membership;
re-running Stage B.

---

## §4 Decisions (this epic)

| # | Decision |
|---|----------|
| D-E2.1 | Band → file mapping is an **explicit registry**, not a glob. Canonical: best `…-214816`, next `…-215558`, worst `…-215818`. Discard the 10-shot best probe `…-214301`. |
| D-E2.2 | `predicted_quality`/`rank` come from re-fitting Stage-A eval on the **65000-shot** run (`…-210803`). Band membership stays **as-run** (frozen from the 100-shot run-time ranking). Both are recorded; the divergence, if any, is reported, not hidden. |
| D-E2.3 | The join test is **continuous** — Spearman on `predicted_quality` across all 15 qubits — so it does not depend on band bins. Bands are used for the grouped omnibus (Kruskal–Wallis) and the headline presentation. |
| D-E2.4 | **No new heavy deps.** Ordered-trend = `scipy.stats.kruskal` (omnibus) + Spearman on band ordinal as the monotone-trend proxy (Jonckheere–Terpstra is not in scipy; do not add it). |
| D-E2.5 | Worst-band failures (`usable_depth=0`, flagged) are **data, not errors** — kept in every table and test. Many zeros in the worst band is the expected, publishable shape. |
| D-E2.6 | EPIC 1 scripts are extended by **new sibling scripts**, not edited in place, so the original single-band path still runs. |

---

## §5 File plan

New (all in `code/`, all reuse EPIC 1 imports):

- **`band_registry.py`** — the explicit band→file map (D-E2.1), a `load_bands()` that returns
  `{band: raw_dict}` with the probe excluded, and a `verify_against_ranking(predictor)` guard
  (AC-1).
- **`evaluate_bands.py`** — imports `score_depths`/`usable_depths` from `evaluate_stage_b` and the
  registry; scores all three bands; merges into the combined 15-qubit table tagged with `band`,
  `predicted_quality`, `rank` (AC-3). Output:
  `results/bands_<backend>_<ts>_combined.csv` + `…_usable_depth.json`.
- **`band_trend.py`** — Spearman(predicted_quality, usable_depth) and each calibration feature vs
  usable_depth (AC-4); Kruskal–Wallis + monotone check across bands on usable_depth / min-entropy /
  |serial-corr| (AC-5). Output: `results/bands_<backend>_<ts>_trend.json`.
- **`band_headline.py`** — per-band usable-bits/minute, best-vs-worst / best-vs-next ratios, the
  reused baseline-vs-best ratio, `monotone_across_bands` (AC-6). Output:
  `results/bands_<backend>_<ts>_headline.json`.

Reused / re-run, not edited:
- `evaluate_stage_a.py` re-run on `…-210803_raw.json` (AC-2).
- `emit_quality_pdf.py` invoked twice for the band PDFs (AC-7).
- `evaluate_stage_b.py`, `eval_common.py`, `join_and_headline.headline` imported as-is.

---

## §6 Manual verification

Run order (all offline):

```
# AC-2 — proper Stage-A quality on the 65000-shot run
python code/evaluate_stage_a.py qrng_output/stagea_ibm_marrakesh_20260714-210803_raw.json --top 5

# AC-1/AC-3 — score all three bands, merge the 15-qubit table
python code/evaluate_bands.py

# AC-4/AC-5 — gradient + ordered-band trend
python code/band_trend.py

# AC-6 — reframed headline
python code/band_headline.py

# AC-7 — band-stratified PDFs (baseline = Stage A --select all aggregate)
python code/emit_quality_pdf.py --baseline <stageA_all> --harvested <best-band aggregate>  -o results/pdf_best.pdf
python code/emit_quality_pdf.py --baseline <stageA_all> --harvested <worst-band aggregate> -o results/pdf_worst.pdf
```

Checks:
- Registry resolves exactly three bands; the `…-214301` probe is absent; the ranking guard passes.
- Combined table has 15 rows, `band ∈ {best,next,worst}`, no NaN in `predicted_quality`.
- `trend.json` reports a Spearman rho + p and a Kruskal p for each outcome, and a
  `monotone_across_bands` bool — present whether the trend is significant or null.
- Headline reports best-vs-worst ratio and the honest-failure verdict wording when worst ≈ best.
- Both PDFs render (worst-band page visibly worse if the gradient holds).

---

## §7 Carried decisions (from EPIC 0 / EPIC 1 / build plan)

- Reuse, do not rebuild; battery is the only measurement harness (#2/#3).
- Never edit `ErrorDetectionVSRawBits/`.
- Every result anchored to its calibration snapshot + device + date (#5); do not mix snapshots.
- Free-tier budget already spent — EPIC 2 adds **zero** `quantum_seconds`.
- `_stream_verdict` rule unchanged: NIST ≥ 0.90 AND next-bit PASS AND Markov PASS, plus
  serial-correlation gate for mid-circuit streams.

---

## §8 Troubleshooting

- **Ranking guard fails** (band qubits ≠ ranked slice): expected if you compare against the
  65000-shot ranking — the bands were frozen from the 100-shot ranking. Verify against
  `…-210551_predictor.json` (the run-time ranking), and record the divergence per D-E2.2.
- **Kruskal warns on ties/zeros**: worst-band zeros are intended (D-E2.5); ties are handled by the
  test — do not drop them.
- **Spearman rho=0 / p=1**: check `predicted_quality` actually has range now (it must, across 15
  qubits); if flat, you are still reading the 100-shot predictor — switch to the 65000-shot re-fit.
- **PDF next-bit "single class" warnings**: known short-stream noise, already suppressed in
  `eval_common` — not an error.

---

## §11 Open questions

- **Q1** Should the monotone/omnibus trend use as-run bands or bins re-derived from the 65000-shot
  ranking? Plan uses **as-run bands** for grouping and continuous `predicted_quality` for the
  Spearman (D-E2.3); revisit only if the two rankings diverge enough to change the story.
- **Q2** For the band PDFs, aggregate each band across all four depths, or PDF the depth-1 stream
  only? Depth-1 is the cleanest apples-to-apples vs the depth-less baseline; all-depths shows the
  harvest. Default: all-depths aggregate, note depth-1 as an appendix option.
- **Q3** Report best-vs-worst as a ratio of usable-bits/minute, or as Δ usable-depth? Ratio is the
  headline; keep Δ usable-depth in the table.

---

## Post-implementation (2026-07-15)

Built exactly per §5: `code/band_registry.py`, `code/evaluate_bands.py`, `code/band_trend.py`,
`code/band_headline.py` — all new, all reusing EPIC 1 imports (`eval_common`,
`evaluate_stage_a.{score_qubits,calibration_matrix,correlate,fit_predictor}`,
`evaluate_stage_b.{score_depths,usable_depths}`), no edits to EPIC 1 files or
`ErrorDetectionVSRawBits/`. `evaluate_stage_a.py` and `emit_quality_pdf.py` re-run unmodified per
§5 (not new files).

Headline finding: the 65000-shot Stage-A predictor (R²=0.4842, vs 0.051 on the 100-shot run the
bands were frozen from) predicts Stage-B usable depth at rho=0.646 (p=0.009); usable depth is
monotone best(2.6) ≥ next(1.0) ≥ worst(0.2) across the ordered bands (Kruskal p=0.029). This is a
**GAIN** result, not the honest-failure branch — the calibration read carries real signal despite
being fit on a noisy 100-shot ranking at run time.

One naming deviation from §6's illustrative command: `emit_quality_pdf.py` has no `-o` flag (its
own fixed `results/qrng_compare_<stem>.pdf` naming, unchanged per D-E2.6) — ran it with its actual
CLI signature (`baseline_processed.txt stageb_raw.json usable_depth.json`) instead of `--baseline/
--harvested/-o`. No code was changed to work around this; the plan's verification snippet was
illustrative shorthand, not the real CLI.

Follow-up for the write-up: the baseline-vs-best ratio (0.018) reads as a loss because it compares
156-qubit raw throughput against a 5-qubit depth harvest — flag this in the thesis text per the
epic's own framing (baseline→band tests "harvest exists", best-vs-worst tests "selection has
value") so it isn't misread as a negative result.
