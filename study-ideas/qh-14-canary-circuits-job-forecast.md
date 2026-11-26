# QH Idea 14 — Canary Circuits: can 5 seconds of small certified circuits predict whether a big job will pass today?

**Tag: QUANTUM · qh · effort: medium · QC: yes (canaries cheap; big jobs already in RUNLOG)**

## Pitch
Every IBM user pays for jobs that fail because the calibration snapshot is stale: QuantumPhantoms found DSCALE "not
repeatable on a calibration snapshot more than a day old", while small circuits (0–32 CZ) passed every time. Turn
that asymmetry into a tool: run a few-second battery of tiny circuits with *known classical bounds* (CHSH, tick-clock,
random access code, Bell-pair learning) on the candidate qubits first, and forecast whether the expensive job will
pass. Prior art predicts success from calibration data (GNN "expected success probability", CNN on circuits) or
tracks drift with Bell tests; none uses bound-certified canaries as a go/no-go gate and prices the saved QPU time.

**Paper strength score: 64/100** — a real user (anyone paying per QPU-second) and data we already partly have;
docked because a month-long 2025 study found weak time-vs-fidelity correlation, so the forecast may be no better
than the backend's own error map.

## How it becomes a study
**Research question:** Do canary margins above classical bounds, measured minutes before a job, predict the job's
pass/fail better than the published calibration data alone?

**Hypothesis:** Canary margin on the job's own qubits predicts pass/fail with higher AUC than calibration-derived
expected fidelity, and gating on it saves ≥ 30 % of QPU time spent on failing jobs.

**Method:** For each big job (GHZ spine, ring, QCA from the QP ladder), first run the canary battery on the same
layout. Log canary margins, calibration-predicted fidelity, and job outcome. Fit a tiny logistic model; evaluate on
held-out days and on a second backend.

**Baseline:** calibration-only predictor (expected success probability from error map); "always submit".

**Metrics:** AUC; QPU-seconds saved per correctly skipped failing job; canary cost overhead; transfer across
backends.

**Novel contribution:** a cost-priced go/no-go gate built from circuits whose pass rule is a proven classical
bound, not a heuristic score.

## Connection to what already exists
- Canary circuits already built and passing: R1-STAR-001, R2-Q2/D4, R3-TEST, CHSH (QuantumPhantoms `code/`, RUNLOG).
- Calibration data handling: `CalibrationGuidedHighYieldQRNG/`, qh-11 entanglement-reach metric (sibling idea:
  that one characterises the device, this one forecasts a job).

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** canaries beat the error map clearly; a small open tool IBM users adopt; QCE software track.
**Bear:** canary health is local and short-range, big-job failure is global (crosstalk, readout of many qubits);
no predictive power beyond calibration.
**Likely:** modest AUC gain, strongest for readout-dominated failures.
**Value if null:** "calibration data already contains everything canaries tell you" is itself a useful, cheap
negative for users who over-probe.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** can bound-certified canaries forecast job success?
**Single defended claim:** canary gating saves X % of failing-job QPU time at Y % false-skip rate on two backends.
**Target venue:** IEEE QCE 2027 (Quantum system software).
**Compelling-study likelihood: 64/100.**

Citation check needed: arXiv 2203.13121 (cloud jobs, calibration cross-over), 2507.01195 (noise-adaptive
transpilation revisited), ESP-GNN device selection (TUM 2026).
