# Idea — Minimum Entropy Extraction Needed for NISQ QRNG to Pass NIST

## Pitch
Real device output is biased and correlated — you must "whiten" it, but whitening throws bits away.
What is the *minimum* extraction you can get away with? Find the cheapest extractor that makes real
Heron r2 output pass the NIST battery, and measure exactly how many bits it costs. Turn ad-hoc
whitening into a principled extraction budget for current hardware.

**Paper strength score: 72/100.** A direct, rigorous extension of work I have already done,
reproducible, with a clear deliverable (a trade-off curve). Docked because extractor theory itself is
well-trodden; the novelty is the device-specific measurement, not the method.

## Connection to what I already did
- My existing `qrng_compare.py` already applies **SHA-512 whitening at a fixed 75% keep ratio** and
  runs the full NIST + next-bit + Markov battery. This study generalizes that single fixed point into
  a full curve: sweep the keep ratio and the extractor family, and find the knee.
- Reuses the thesis hardware output (Bell-pair and Hadamard streams from Heron r2) as the raw input.
- Answers the exact "more sophisticated entropy extractors" future-work item the thesis named.

## How it becomes a study

**Research question:** What is the minimum entropy extraction (which extractor, at what keep ratio)
required to make real Heron r2 QRNG output pass the full NIST battery, and what is the bit-yield cost?

**Hypothesis:** There is a measurable knee — below some extraction strength the output fails NIST;
above it, passing is achieved but extra extraction only wastes bits. The knee's location is set by
the device's raw min-entropy.

**Baseline:** Raw device output (no extraction) and the current fixed SHA-512-at-75% point.

**Method:** Measure raw min-entropy of the device output, then apply a ladder of extractors at varying
strengths and test each against the full battery.
- Extractor ladder: von Neumann debiasing; SHA-256 / SHA-512 hashing at varying keep ratios; Toeplitz-hash
  with output length tuned to the measured min-entropy.

**Metrics:**
- Raw min-entropy estimate of the device stream
- Extractor yield (%) per method and per keep ratio (bits out / bits in)
- Full NIST battery pass/fail at each extraction strength
- Next-bit predictability and Markov dependency post-extraction
- Bit-efficiency: usable output bits per raw device bit at the minimum passing config

**Free-tier fit:** No new hardware runs strictly needed — reuse existing captured streams. Optional
small fresh runs to confirm on current calibration. Effectively free.

**Target venues:** Entropy, IEEE Access, IEEE QCE, cryptographic-engineering workshops.

## High-level 5 steps to the goal
1. Gather raw device streams (reuse existing thesis captures; optionally add a fresh Heron r2 run).
2. Estimate the raw min-entropy of each stream (the theoretical extraction ceiling).
3. Apply the extractor ladder at a sweep of keep ratios / output lengths; save each extracted stream.
4. Run the full NIST + next-bit + Markov battery on every extracted stream; record pass/fail and yield.
5. Plot the extraction-strength vs pass/yield curve, locate the knee, and report the minimum passing config + its bit cost.
