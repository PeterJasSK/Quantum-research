# Flagship — Calibration-Guided High-Yield QRNG on Heron r2

## Pitch
On current IBM hardware, extract the maximum usable randomness by attacking two knobs at once:
pick the best qubits from the chip's own calibration report, and harvest many bits per qubit per
shot via mid-circuit measurement + reset. Core question: **does a qubit's calibration (T1, T2,
readout error, reset error) predict how far you can push the measure-reset loop before the extra
bits go correlated?** Output is a practical, turnkey rule — "given today's calibration, use these
qubits at this harvest depth" — a full QRNG config with zero trial-and-error, on free-tier hardware.

**Paper strength score: 81/100.** Higher than either half alone (mid-circuit yield 78, calibration
selection 74). One clean unifying hypothesis, a defining current-generation feature at its center
(mid-circuit reset), a strong reproducible deliverable, and it stays trivially inside the free budget.
Docked only for being characterization/engineering rather than new theory.

## Connection to what I already did
This is a direct extension of my bachelor thesis QRNG work:
- `ErrorDetectionVSRawBits/qrng_bell_pairs.py` — the Bell-pair QRNG on IBM Heron r2 (ibm_fez,
  ibm_marrakesh, ibm_kingston). This study reuses that hardware, account, and circuit-submission
  pipeline directly.
- `ErrorDetectionVSRawBits/qrng_compare.py` — the existing quality battery (bias in 20 splits, NIST
  SP800-22 subset, next-bit ML predictability à la Blum–Micali, Markov dependency, SHA-512 whitening).
  This becomes the ready-made measurement harness for both stages below — no new evaluation code needed.
- The thesis already established that Bell-pair output is statistically indistinguishable from ideal.
  This study moves the question from "is it random?" to "how do I get the MOST usable randomness per
  free-tier minute out of this exact hardware?" — the natural next step the thesis itself flagged as
  future work (advanced extractors, hardware-dependent quality).

## How it becomes a study

**Research question:** Can a single calibration read predict both (a) which qubits produce the best
random bits and (b) how deep a mid-circuit measure-reset loop each qubit sustains before bits become
correlated?

**Hypothesis:** Calibration properties (especially reset error, readout error, T1) correlate with
RNG quality AND with the maximum usable measure-reset depth, so one calibration snapshot yields a
complete optimal config.

**Baseline:** Naive single-qubit Hadamard, 1 bit per qubit per shot, no qubit selection.

**Metrics:**
- Per-qubit: bias, min-entropy, NIST subset pass/fail (Stage A)
- Correlation: each calibration property vs RNG quality, and vs max usable depth
- Per-depth: serial correlation between consecutive mid-circuit bits, min-entropy of harvested stream,
  reset-induced bias, next-bit predictability, Markov dependency
- Yield: usable bits/qubit/shot and total usable bits/shot at the predicted config
- Headline: usable bits per free-tier minute at the calibration-optimal config vs the naive baseline

**Free-tier fit:** Stage A = one all-qubit parallel job. Stage B = a handful of small depth-sweep
jobs on the ~5 top-ranked qubits. Comfortably under the ~10 min/month Open-plan budget.

**Target venues:** IEEE QCE (Quantum Week), Entropy, IEEE Access, ACM/IEEE quantum-engineering workshops.

## Detailed plan (defined steps for future planning)

### Phase 0 — Setup & reuse
1. Confirm IBM Open-plan access and pick the target Heron r2 device (record device name + calibration date — results are device-and-date specific).
2. Pull the reusable pieces: circuit-submission pipeline from `qrng_bell_pairs.py`, quality battery from `qrng_compare.py`.
3. Fetch the device's live calibration snapshot (per-qubit T1, T2, readout error, single-qubit gate error, reset error) via the backend properties API; save it timestamped alongside every run.

### Phase 1 — Stage A: calibration-aware qubit selection
4. Build a single-qubit Hadamard RNG circuit applied to every qubit of the chip in parallel (one batch = whole chip, cheap).
5. Run enough shots for a meaningful per-qubit bitstream; save raw output per qubit with the calibration snapshot.
6. Run the existing quality battery per qubit: bias, min-entropy, NIST subset, next-bit, Markov.
7. Correlate each calibration property against each quality metric; fit a simple predictor (e.g. ranked regression) that scores a qubit's expected RNG quality from calibration alone.
8. Rank all qubits; select the top ~5 for Stage B.

### Phase 2 — Stage B: mid-circuit measure-reset yield
9. Build a mid-circuit loop circuit: prepare superposition, measure, reset, re-prepare, measure — repeat k times per qubit per shot (k = 1, 2, 4, 8, ...).
10. Run the depth sweep on the top-ranked qubits; save the interleaved per-qubit, per-depth streams.
11. For each qubit and depth, measure: serial correlation between consecutive mid-circuit bits, min-entropy, reset-induced bias, next-bit predictability.
12. Find, per qubit, the maximum depth where bits stay independent and unbiased (the "usable depth").

### Phase 3 — The join (the novel contribution)
13. Test whether the Stage-A calibration predictor also predicts each qubit's Stage-B usable depth (correlation + a combined model).
14. If it does: publish the single-read recipe — calibration snapshot → chosen qubits × harvest depth → optimal config with no trial-and-error.
15. Compute the headline gain: usable bits/free-tier-minute at the calibration-optimal config vs the naive 1-bit-per-shot baseline.

### Phase 4 — Write-up
16. Report honestly, including the failure case (if reset noise dominates and mid-circuit yield is net-negative, that is still a publishable current-gen usability result).
17. Note device + calibration date prominently so the result is reproducible and its aging is transparent.
