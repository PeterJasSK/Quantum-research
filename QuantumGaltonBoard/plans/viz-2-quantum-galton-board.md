# Viz Idea 2 — Quantum Galton Board: Watch a Distribution Build Itself

**Tag: QUANTUM · viz · effort: low-medium**

## Pitch
A classical Galton board (bean machine) drops balls through a lattice of pegs and builds a binomial
→ Gaussian pile. The quantum version replaces each peg with a coin+shift unitary: amplitudes
interfere, and the emergent distribution is **not** Gaussian — it develops the twin-horn ballistic
profile of a quantum walk. Build it as a shallow circuit on real Heron r2 hardware, run it at growing
depth, and animate the pile forming layer by layer: classical bell curve vs quantum horns, ideal vs
noisy-device.

**Paper strength score: 71/100.** The quantum Galton board / quantum walk is a known, clean,
hardware-friendly benchmark with a striking signature (ballistic vs diffusive spreading, variance ∝
t² vs t). Novelty is modest as pure physics, so frame it as a **device-fidelity storyteller**: how
many rows before real-hardware noise collapses the horns back toward the classical curve? That knee
is a fresh, measurable, chip-specific result and ties straight to the calibration/drift work.

## How it becomes a study
**Research question:** At what circuit depth does NISQ noise erase the ballistic quantum-walk
signature and return the output distribution to the classical diffusive one?

**Hypothesis:** Quantum spreading (σ ∝ t) survives only to a depth set by two-qubit gate error;
beyond it, decoherence restores the classical σ ∝ √t.

**Method:** Discrete-time quantum walk on a line, n rows = n steps. Run ideal simulator, noisy
simulator (device noise model), and real hardware at n = 2…N. Compare bin distributions.

**Metrics:**
- Variance growth exponent (fit σ² ∝ tᵃ; a→2 ballistic, a→1 diffusive)
- Total-variation / Hellinger distance: hardware vs ideal, hardware vs classical
- Peak-splitting visibility (horn contrast) vs depth — the collapse curve
- Entropy of the output distribution vs depth

## THE VISUALIZATION (the star)
- **Cascade animation**: balls/amplitude "waterfall" through the peg lattice, bins filling in real
  time; toggle classical vs quantum and watch bell curve morph into twin horns.
- **Depth slider**: drag n and see ideal horns melt toward the classical hump as noise wins — the
  paper's headline figure as a live control.
- **Interference glow**: color pegs by local phase so constructive/destructive interference is
  visible as it happens (the "why it's not Gaussian" panel).
- Pure browser HTML/Canvas, self-contained — same delivery as QuantumLife `web/`.

## Connection to what I already did
- Runs on the same Heron r2 access + noise-model tooling as the QRNG thesis.
- The "noise collapses the signature at depth X" knee is the dynamic-systems sibling of the
  `qh-2-temporal-drift-stability` and `qh-3-minimum-extraction-budget` reliability studies.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** *At what circuit depth does NISQ gate noise erase the ballistic
quantum-walk signature and return a Heron r2 Galton board to the classical diffusive distribution?*

**Single defended claim:** The ballistic-to-diffusive crossover depth is a chip-specific,
reproducible fidelity metric set by two-qubit error rate — a "randomness-shape half-life" of the
device.

**Why it fits 6–8 pp:** shallow circuit, one sweep over depth, three arms (ideal / noise-model /
hardware), one headline figure (horns melting under the depth slider), variance-exponent + TV-distance
metrics. Self-contained, hardware-backed, no calendar dependency.

**Target venue:** IEEE Transactions on Quantum Engineering (short) or IEEE QCE conference paper.

**Compelling-study likelihood: 75/100** — hardware-backed, unambiguous measurable knee, and a
striking figure. Docked because the quantum walk is a known benchmark; novelty is the device-specific
collapse curve, which must be framed as the contribution.
