# Calibration-Guided High-Yield QRNG

## Research question

Does **one calibration read** predict both qubit quality *and* usable mid-circuit
measure-reset harvest depth — so an optimal high-yield QRNG config can be picked with
**zero trial-and-error** on free-tier hardware?

## Hypothesis

A single per-qubit calibration snapshot (`T1`, `T2`, `readout_error`, `sx` gate error,
reset error) is enough to (a) rank qubits by expected randomness quality, and (b) predict
how many mid-circuit measure-reset repetitions each qubit sustains before reset noise
dominates. If both hold, a calibration-optimal config is chosen up front — no scanning.

## Honest framing

> The novelty here is **not** a new randomness source. It is the claim that one
> calibration read predicts both qubit quality and usable harvest depth, so an optimal
> high-yield QRNG config is picked with zero trial-and-error on free-tier hardware. If the
> prediction fails — reset noise dominates, mid-circuit yield goes net-negative — that is
> still a publishable current-generation usability result. Say it that way in the write-up.

## The two stages

- **Stage A — calibration-aware selection (also the baseline).** Single-qubit Hadamard on
  every qubit in parallel, one batch = whole chip, 1 bit/qubit/shot. `--select all` (default)
  is the naive baseline with no selection; `--select good` / `--select list:q,q,...` are
  selectable variations for comparison (run by hand).
- **Stage B — mid-circuit measure-reset yield.** Loop circuit per qubit: prepare
  superposition → measure → reset → re-prepare → measure, repeated `k` times per qubit per
  shot, `k ∈ {1, 2, 4, 8}` by default (depth sweep). Runs on the top-ranked qubits from Stage
  A's evaluation (EPIC 1), passed in via `--qubits`.

## Baseline

Naive config: single-qubit Hadamard, 1 bit/qubit/shot, no qubit selection (Stage A with
`--select all`). Every gain is reported against this.

## Metrics (scored in EPIC 1, reusing `ErrorDetectionVSRawBits/qrng_compare.py`)

| Metric | PASS condition |
|--------|-----------------|
| Global bias | low `\|p1−0.5\|`; reported, not a hard gate |
| Min-entropy/bit | near 1.0 is ideal |
| Bias per 20 splits | low and flat, no drift |
| NIST SP 800-22 subset | overall pass rate ≥ 0.90 |
| Next-bit predictability | verdict PASS (AUC 95% CI includes 0.5) |
| Markov dependency | verdict PASS (no order beats baseline) |
| Serial correlation (Stage B only) | ≈ 0 |

Headline (EPIC 1): usable bits per free-tier minute, calibration-optimal config vs baseline.

## How to run each step

All commands run from `CalibrationGuidedHighYieldQRNG/`, using the shared pipeline in
`code/pipeline_common.py` (forked from `ErrorDetectionVSRawBits/qrng_bell_pairs.py`, D1 —
that file is never edited).

1. **Calibration snapshot + reset probe** (S0.3):
   ```
   python code/calibration_snapshot.py [backend]
   ```
   Writes `qrng_output/calib_<backend>_<ts>.json` and prints PASS/FAIL for the mid-circuit
   reset probe. **Do not run Stage B if this fails** — record it as the honest failure case.

2. **Stage A — whole-chip Hadamard** (S0.4):
   ```
   python code/stage_a_selection.py <shots> [backend] --select all
   ```
   Try `--select good` or `--select list:q1,q2,...` for comparison runs. Writes
   `qrng_output/stagea_<backend>_<ts>_raw.json` (with `qubits_used` order + embedded
   calibration snapshot) and `..._processed.txt` (`bits:...`).

3. **Stage B — mid-circuit depth sweep** (S0.5, after EPIC 1 picks the top-5 from Stage A):
   ```
   python code/stage_b_yield.py <shots> [backend] --qubits q1,q2,q3 --depths 1,2,4,8
   ```
   Defaults to the 3 lowest-readout-error non-faulty qubits from the live snapshot if
   `--qubits` is omitted. Writes `qrng_output/stageb_<backend>_<ts>_raw.json` (per-depth
   `(qubit, depth, creg-slot)` layout + calibration snapshot) and `..._processed.txt`.

Use tiny shot counts for verification runs — the whole study budget is the IBM Open plan's
free-tier ~10 min/month. Full runs are a manual hand-off after this epic (EPIC 0 only builds
runnable circuits; you submit and collect the jobs by hand).

## Folder layout

- `code/` — all Python for this study.
- `qrng_output/` — bit files (`_raw.json`, `_processed.txt`) and calibration snapshots.
- `results/` — EPIC 1 scores and the comparison PDF land here.
- `paper/` — the thesis / write-up.
