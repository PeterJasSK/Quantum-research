# Idea — Temporal Drift: Does QRNG Quality Survive Recalibration Cycles?

## Pitch
Quantum chips are recalibrated daily and drift between calibrations. Run the same tiny QRNG circuit
repeatedly over days and weeks and ask: is the randomness *stable*, or does quality swing with the
calibration cycle? Can you trust a fixed QRNG config over time, or must you re-tune constantly? This
is the reliability question nobody covers — and it matters directly to anyone running QRNG as a service.

**Paper strength score: 69/100.** Cheap per run, a real and under-covered reliability question, and
it connects to my Q-EaaS service. Docked because it needs calendar time (weeks of scheduled runs)
and the drift may turn out boringly small.

## Connection to what I already did
- Reuses the thesis hardware pipeline (`qrng_bell_pairs.py`) and quality battery (`qrng_compare.py`) —
  same device, same tests, just repeated on a schedule.
- Directly relevant to the **Q-EaaS API** I built: that service treats QRNG as a dependable entropy
  feed. This study tests the unspoken assumption behind it — that quality is stable enough to trust
  a fixed config over time. A drift finding feeds straight back into how the service should reseed
  and monitor its source.

## How it becomes a study

**Research question:** How stable is the statistical quality of a fixed QRNG circuit on a real
Heron r2 device across time and across recalibration events?

**Hypothesis:** RNG quality varies measurably between calibrations; quality dips correlate with
recalibration timing and with drift in per-qubit calibration properties.

**Baseline:** The first run's quality as the reference; also a classical CSPRNG stream run through
the same battery as a stability floor.

**Metrics:**
- Bias drift over time
- Day-to-day variance of min-entropy
- NIST subset pass-rate stability
- Correlation of quality drops with recalibration timestamps
- Correlation of quality with drift in the qubit's calibration properties (T1, T2, readout error)
- Worst-case vs mean quality over the whole window

**Free-tier fit:** A small fixed job (few qubits, modest shots) on a schedule. Each run is tiny; the
cost is calendar time, not quota.

**Target venues:** Entropy, IEEE Access, IEEE QCE, quantum-reliability workshops.

## High-level 5 steps to the goal
1. Fix one small QRNG circuit and one target device; freeze the config so nothing but time varies.
2. Schedule repeated runs over several weeks; each run, save output + the live calibration snapshot + timestamp.
3. Run the quality battery on every run's output; record all metrics per run.
4. Align the quality time-series against recalibration events and against calibration-property drift.
5. Report stability (or instability), quantify worst-case quality, and translate into a reseed/monitoring recommendation for Q-EaaS.
