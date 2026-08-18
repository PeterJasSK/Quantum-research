# QH Idea 11 — Entanglement Reach: a cheap per-device metric for how far a teleported bond stays alive on a chip

**Tag: QUANTUM · qh · effort: low-medium**

## Pitch
The QuantumTree teleport run found a **decoherence-vs-distance crossover**: a teleported
long-range bond was alive at 12-qubit separation (`c(d)≈-0.1`) and dead (pure noise) at 36.
That crossover is a *number* about the device, not the art. This idea turns it into a
standardized, cheap benchmark — **entanglement reach `R`**: the maximum on-chip separation
at which a teleported Bell/CNOT bond still yields a certified nonzero correlation (or
Bell-pair fidelity above threshold) on backend X at calibration Y. Report `R` per backend,
and track how it drifts across recalibration cycles.
**Paper strength score: 72/100** — a genuinely reusable device-characterization metric that
is cheap to produce and easy to compare across chips; docked because a single benchmark
number is thin for a full paper unless paired with the drift-tracking story.

## How it becomes a study
**Research question:** What is the entanglement reach `R` (max separation with a
certified-nonzero teleported bond) of Heron r2 backends, and how stable is `R` across
calibration windows?
**Hypothesis:** `R` is finite and backend/calibration-dependent; it correlates with live
two-qubit-error and readout-error along the routing path, and drifts measurably between
recalibrations.
**Method:** Prepare a teleported bond at separations `d = 6…48` qubits, read the connected
correlation at the exact bonded qubits (`bond_correlations`), and define `R` as the largest
`d` whose `|c(d)|` clears the `--sim` noise floor by ≥3σ. Repeat across ≥3 calibration days
and ≥2 backends. Regress `R` against the recorded `twoq_err_mean`, `readout_max`, and path
length. Simulation fixes the floor; the metric itself needs light QC.
**Baseline:** the classical `--sim` null (floor) and a same-distance SWAP bond (to show `R`
is a property of the link, contrasted against the depth-limited alternative).
**Metrics:** `R` per (backend, calibration); its variance across days; correlation of `R`
with live calibration numbers; QPU-seconds per `R` measurement (cheapness claim).
**Novel contribution:** a single, portable "how far can this chip entangle right now"
number, defined operationally and shown to track calibration — usable for device selection
and monitoring, not just this experiment.

## Connection to what already exists
Reuses `QuantumLife/code` bond machinery and the crossover already observed in
`research/conclusion_teleportation_longrange.md`. Borrows the *drift-tracking* design from
the README's `qh-2-temporal-drift-stability` stub (QRNG quality vs recalibration) but
measures entanglement reach, not RNG quality — a different observable and a different use.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Cheap, mostly-deterministic floor from simulation, a crisp scalar that is trivial
to compare across chips and days; naturally extends the existing crossover datapoint into a
repeatable metric.
**Bear:** `R` may be small and noisy on current hardware (already dead by `d=36`), so the
dynamic range is limited and day-to-day scatter could swamp the drift signal.
**Likely outcome:** `R` in the 12–24 qubit band on marrakesh, moving a few qubits between
calibrations and tracking `twoq_err_mean` — a modest but clean characterization figure.
**Value if null:** If `R` is unstable or uncorrelated with calibration, that is itself worth
reporting — it says teleported-bond survival on Heron is not predictable from the published
error rates, a caution for anyone planning long-range dynamic-circuit gates.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** How far, and how stably, can a Heron r2 chip sustain a teleported
long-range bond? **Single defended claim:** entanglement reach `R` is a finite,
calibration-dependent, cheaply measurable per-device metric. **Why it fits 6–8 pp:** one
metric, a distance sweep, a multi-day/multi-backend table, one `R`-vs-calibration figure.
**Target venue:** IEEE Quantum Week (QCE) device-characterization track / IEEE Access.
**Compelling-study likelihood: 72/100.**
