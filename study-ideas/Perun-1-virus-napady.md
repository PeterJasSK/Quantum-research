# Quantum × Genomic Model Project Ideas — Bull/Bear Assessment

Context: exploring whether Perun's Qaptiva 808 quantum simulator could be hybridized
with a genomic foundation model (Evo-style) to test whether "quantum entropy"
improves model behavior. Below are three concrete testable ideas, each with an
honest bull case, bear case, most-likely outcome, and value assessment if the
result is null.

---

## Idea 1 — Quantum kernel classifier on Evo embeddings

**Setup:** Generate sequence embeddings with Evo on Perun's GPUs, compress them
to fit a small qubit budget, compute a quantum kernel on Qaptiva, feed into an
SVM. Compare against a classical RBF kernel on the same reduced embeddings.

**Bull case**
Quantum kernel methods are a legitimate, active QML research area. If the
kernel's mathematical structure happens to fit compressed genomic embeddings
better than an RBF kernel, you get a real accuracy/AUC delta — a clean,
publishable comparison.

**Bear case**
You're running this on a classical simulator (Qaptiva), so there is no
possible speed advantage even in principle — only "does this kernel shape fit
the data." Dequantization research shows classical methods (random Fourier
features) match quantum kernel performance in most practical regimes, and
near-term hybrid approaches rarely beat classical baselines. Compressing
Evo's rich embeddings down to ~15 dimensions to fit qubit limits will likely
destroy the signal that made Evo useful in the first place.

**Likely outcome**
Probably a wash or a loss vs. the classical kernel — the compression
bottleneck alone could sink it regardless of "quantum vs classical."

**Value if null**
Moderate. A clean negative result ("quantum kernel ≤ classical kernel once
you control for dimensionality reduction") is a useful, citable data point in
a field full of overclaiming. Not exciting, but honest and specific.

---

## Idea 2 — QRNG-seeded genetic search scored by Evo

**Setup:** Directed-evolution / genetic algorithm over sequence space, where
mutation and crossover randomness comes from true quantum randomness (QRNG)
instead of a classical PRNG, with Evo's zero-shot scoring as the fitness
function. Compare convergence speed and diversity, quantum-seeded vs.
classical-seeded.

**Bull case**
Directly builds on existing QRNG research — a genuinely novel combination
that doesn't appear to have been published. If quantum randomness meaningfully
improved exploration diversity or convergence speed, that would be a real,
unexpected result.

**Bear case**
GA performance is governed by selection pressure, mutation rate, and
landscape shape — not RNG source quality, once the RNG is decent. Evo's
zero-shot fitness scores also weren't designed to be a smooth iterative-search
landscape, so the pipeline itself may be shaky before RNG source even becomes
relevant.

**Likely outcome**
Very likely no measurable difference between quantum- and classical-seeded
runs — this mirrors decades of RNG-quality studies in Monte Carlo and
evolutionary computation, which consistently find no effect once the
classical RNG passes standard statistical tests.

**Value if null**
Low-to-moderate. This is the biggest engineering lift of the three (building
a working Evo-scored GA loop) for a result that's fairly predictable in
advance. The GA infrastructure itself might have reuse value beyond this
specific question, though.

---

## Idea 3 — Quantum-random sampling in Evo's generation step

**Setup:** Replace Evo's pseudorandom sampler (temperature/top-k sampling
over nucleotide logits) with true quantum-generated random bits at inference
time. Compare statistical properties of generated sequences (GC content,
motif frequency, entropy) across large batches.

**Bull case**
Cheapest to build of the three — swap the sampler, run large batches, compare
distributions. Simple, fast, testable in days rather than months.

**Bear case**
Randomness only picks among outputs the model already finds plausible — it
doesn't touch what the model "knows." Averaged over millions of tokens,
quality PRNGs and quantum RNGs are statistically indistinguishable, so any
detected "difference" is more likely to be noise or an artifact of
insufficient sample size than a real effect.

**Likely outcome**
No significant difference, with high confidence — this is the most
predictable null result of the three.

**Value if null**
Highest value-per-effort of the three, precisely because it's cheap. A
rigorous, pre-registered "we tested this obvious-seeming hypothesis and it's
false" result costs little and still adds a real data point to the
quantum-ML hype conversation. Best candidate if the goal is a real result on
Perun fast and cleanly, not a breakthrough.

---

## Overall takeaway

All three are more likely to yield null results than genuine improvements —
that's not a reason to skip them, but it means the framing of a Perun
proposal should be **"rigorously test whether X holds"** rather than **"build
a better virus model via quantum entropy."** The latter oversells; the former
is defensible science and still gets real hands-on time with the hybrid
HPC–quantum pipeline (Q-Pragma), which has standalone value even if every
result comes back null.