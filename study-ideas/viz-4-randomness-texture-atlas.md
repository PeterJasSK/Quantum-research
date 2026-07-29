# Viz Idea 4 — Randomness Texture Atlas: Does Bad Randomness Have a Look?

**Tag: NON-QUANTUM · viz · effort: medium**

## Pitch
Randomness is invisible in a bitstream but *visible* the moment you feed it to an emergent system.
Drive four classic pattern-forming processes — percolation clusters, diffusion-limited aggregation
(DLA), Turing reaction-diffusion, and Ising domains — from PRNG, CSPRNG, and QRNG, and render the
resulting textures side by side. Then ask the sharp question: are the differences *only* aesthetic,
or do measurable pattern statistics (cluster-size law, fractal dimension) actually shift when the
source is weak? A gallery you can look at, backed by numbers you can test.

**Paper strength score: 73/100.** Strong hook, real measurables, and a built-in honesty check: a
truly good CSPRNG should be statistically indistinguishable from QRNG here, so any visible or metric
difference flags a *defective* generator. That reframes the piece as a **visual randomness-quality
diagnostic** — "if you can see the seams, your RNG is broken" — which is genuinely useful and novel
as a presentation. Docked because the honest result for good sources is "no difference," so the
payload is the diagnostic framing + the low-quality-source failure cases.

## How it becomes a study
**Research question:** Do emergent spatial statistics of pattern-forming systems detect randomness
defects that pass or nearly pass standard bit-level batteries?

**Hypothesis:** Structured/low-quality sources (LCG, truncated PRNG, biased QRNG pre-whitening)
leave measurable fingerprints in cluster and fractal statistics; CSPRNG and whitened QRNG do not.

**Method:** Fix each generative process; swap only the entropy source. Include deliberately weak
sources (bad LCG, low-period, biased raw device bits) as positive controls. Many seeds per cell.

**Metrics:**
- Percolation: cluster-size distribution exponent, spanning-cluster threshold p_c
- DLA: fractal (box-counting) dimension
- Turing: dominant wavelength + orientation-order spectrum
- Ising: domain-size distribution, correlation length
- Cross-source distances (energy distance) per metric — the hypothesis test

## THE VISUALIZATION (the star)
- **The Atlas**: a grid — rows = processes, columns = sources — of high-res generated textures. One
  screen, the whole thesis.
- **Reveal mode**: overlay the metric heatmap on each texture (fractal dimension map, cluster
  coloring) to show where a defect hides.
- **Live grow**: animate DLA/percolation nucleating from the same seed under different sources.
- **"Spot the fake"** interaction: shuffle tiles, let the viewer guess which came from the broken
  generator — the diagnostic pitch, made playable.
- Canvas/WebGL, self-contained HTML.

## Connection to what I already did
- Direct visual companion to the QRNG quality battery (`qrng_compare.py`) and the extraction-budget
  study (`qh-3-minimum-extraction-budget`): those measure bits; this shows what the bits *become*.
- The raw-vs-whitened device bits from `ErrorDetectionVSRawBits` are ready-made positive controls.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** *Do emergent spatial statistics of pattern-forming systems detect randomness
defects that pass, or nearly pass, standard bit-level (NIST) batteries?*

**Single defended claim:** Percolation/DLA/Ising order statistics form a cheap visual-plus-metric
diagnostic that flags structured or biased generators — "if you can see the seams, the RNG is broken"
— and confirm indistinguishability for CSPRNG/whitened-QRNG.

**Why it fits 6–8 pp:** four fixed processes, source swap only, deliberately-weak positive controls,
one atlas figure + one metric-distance table. Clear pass/fail deliverable; no hardware or calendar
dependency.

**Target venue:** IEEE Access, or IEEE Transactions on Information Forensics & Security (diagnostic
angle) as a short contribution.

**Compelling-study likelihood: 70/100** — great hook, honest built-in check, real measurables, and
the broken-generator cases give a genuine positive result. Docked because good sources yield "no
difference," so the diagnostic + failure-case framing carries the paper.
