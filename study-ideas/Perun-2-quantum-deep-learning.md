# Field 3: Quantum-Enhanced Generative / Deep Learning
### Detailed project definitions — Perun (Qaptiva + H200 GPU fleet)

Goal for all three: demonstrate a genuine hybrid advantage where the GPU fleet
and the quantum simulator are each doing something the other structurally
cannot — not just "quantum method, but bigger."

---

## 7. Quantum Circuit Born Machine (QCBM) + GPU-trained adversarial loss

### Defined setup
- **Generator:** a Quantum Circuit Born Machine on Qaptiva — a parameterized
  circuit of N qubits (start at N=12–20, well inside exact-simulation range)
  whose measurement outcomes form the generated sample distribution.
- **Discriminator:** a classical deep network trained on the H200 GPUs, large
  batch size, real dataset scale (not toy — e.g. tabular fraud/credit data,
  or a structured molecular/binary dataset, not MNIST-scale).
- **Training loop:** standard GAN alternation — generator (Qaptiva) proposes
  a batch, discriminator (GPU) scores it, gradients update both. This loop
  runs thousands of times per epoch, so the quantum-simulator call latency
  and GPU throughput both matter simultaneously.
- **Baseline for comparison:** the same discriminator architecture trained
  against a classical generator (standard GAN) and against a classical prior
  (e.g. normalizing flow) of matched parameter count.
- **Metric:** distributional fidelity (MMD / KL divergence to real data),
  mode coverage (does it avoid mode collapse), and downstream utility
  (train-on-synthetic, test-on-real accuracy).

### How this is studied today
QCBMs as GAN priors are an active, real research line — e.g. QCA-MolGAN uses
a QCBM as a learnable latent-space prior for a molecular GAN, and earlier work
demonstrated adversarial training of a Born machine on superconducting
hardware with high fidelity to a target distribution on small proof-of-concept
tasks. Most published results are on tabular/synthetic benchmarks (Iris,
Telco churn) or small pattern datasets (bars-and-stripes), not large-scale
data.

### Bull case
This is the most defensible "hybrid loop is the point" idea of the three —
the GPU discriminator genuinely needs scale to be a meaningful adversary, and
the quantum sampler is called at high frequency, so the tight low-latency
loop (not just "quantum, then classical, done") is structurally necessary.
QCBMs also have a real theoretical argument for expressivity advantages on
certain distributions (harder for classical samplers to represent
efficiently).

### Bear case
Every published QCBM-GAN success is on small-scale, structured, or synthetic
data — nobody has shown this scales to real "large dataset" generative
quality competitive with a modern classical GAN or diffusion model. The
quantum sampler's expressivity advantage is theoretical and dataset-specific;
for most real-world data, a classical latent noise source (even plain
Gaussian) works fine, so the QCBM may add complexity without adding quality.
There's also a serious scaling ceiling: Qaptiva's exact simulation cost still
grows exponentially with qubit count, so "N large enough to matter" and
"N small enough to simulate" may not overlap for a genuinely large dataset.

### Likely outcome
Most probable result: comparable but not better distributional fidelity vs.
a matched-size classical GAN, with the QCBM version being slower per epoch
due to simulator overhead. A more optimistic plausible outcome: better mode
coverage / less mode collapse on a specific structured dataset, which would
still be a real, useful, narrow result.

### Value if null
Moderate-to-good. Even a "no quality advantage, but here's the actual
wall-clock/scaling cost" result is useful — it's a real hybrid-architecture
engineering exercise (which has standalone value for demonstrating Perun's
Q-Pragma-style integration) and a legitimate benchmarking contribution to a
field where clean quantum-vs-classical GAN comparisons at scale are rare.

---

## 8. Hybrid quantum-classical neural network with quantum layers at scale

### Defined setup
- **Classical backbone:** a real-sized deep network (e.g. ResNet-scale CNN
  or a transformer of meaningful depth), trained on the GPU fleet on a
  full-size dataset (not MNIST/Iris-scale — pick something like CIFAR-100,
  a materials/molecular property dataset, or a time-series forecasting
  dataset with real complexity).
- **Quantum layer(s):** 1–2 parameterized quantum circuits (angle embedding +
  entangling layers, 4–10 qubits) inserted at a bottleneck or early
  feature-extraction point, evaluated on Qaptiva during both forward and
  backward passes.
- **Matched-capacity baseline:** a fully classical network with the quantum
  layer replaced by a classical layer of equivalent parameter count — this
  is the comparison that actually isolates "does the quantum layer help,"
  rather than "does having more layers help."
- **Metrics:** test accuracy/loss at matched parameter count, training FLOPs,
  convergence speed (epochs to target accuracy), and — importantly — wall
  clock time including simulator overhead.

### How this is studied today
This is a genuinely active area with mixed, contested results. Some studies
report hybrid models beating classical ones on image classification and
time-series tasks at matched or smaller size; other systematic reviews find
advantages mostly on small-scale or narrowly-scoped comparisons, and a
widely-cited benchmarking paper ("Better than classical? The subtle art of
benchmarking quantum machine learning models," Bowles et al., 2024) argues
many claimed QML advantages don't hold up once baselines are tuned fairly.
A separate 2024/2025 analysis specifically asked whether hybrid quantum
neural network advantages are "myth or reality" and found the picture is
scaling-dependent rather than a clean win.

### Bull case
If a real effect exists, this setup gives you the fairest possible test of
it: full-scale classical backbone (needs the GPU fleet to be meaningful),
matched-parameter classical baseline (removes the "more layers = better"
confound), and a genuine dedicated quantum simulator rather than a toy
approximation. This is exactly the kind of test that's rare in the
literature because most groups don't have both a serious GPU cluster and a
dedicated quantum simulator on the same low-latency fabric.

### Bear case
The literature is genuinely split, and the split correlates suspiciously
well with how carefully the classical baseline was tuned — the field's own
benchmarking critics argue that many "hybrid wins" disappear under fair
comparison. There's also a structural risk: quantum layers are typically
small (4–10 qubits) relative to a "real-sized" classical backbone, so their
practical contribution to a large model's capacity may be marginal regardless
of any per-layer expressivity advantage — like adding one exotic layer to an
otherwise enormous network and hoping it moves the needle.

### Likely outcome
No statistically significant difference at matched parameter count is the
single most common finding in fair QML benchmarking studies once the
classical baseline is properly tuned. A modest, task-specific edge on one
dataset but not others is the next most likely outcome.

### Value if null
Good. This is precisely the kind of fair, matched-baseline test the field
is short on — publishing "we ran the careful comparison and found no
advantage at scale X" using genuinely large-scale infrastructure is a real
contribution to resolving the myth-vs-reality debate, not just another small
anecdotal case study.

---

## 9. Quantum kernel at scale with GPU-accelerated kernel machinery

### Defined setup
- **Dataset:** a large classical dataset (tens of thousands to millions of
  rows) where the outer kernel-machine computation is genuinely expensive —
  e.g. large-scale fraud detection, a big materials/chemistry property
  dataset, or a large tabular benchmark.
- **Quantum kernel entries:** computed on Qaptiva for each pairwise sample
  (or a Nyström-approximated subset to control cost).
- **Kernel matrix operations:** the O(n²)-or-worse matrix construction,
  eigendecomposition, and SVM solve run GPU-accelerated (cuML/cuQuantum-style
  libraries) on the H200 fleet — this is the genuinely HPC-scale part.
- **Baseline:** classical RBF/polynomial kernel SVM using the same
  GPU-accelerated solver, same dataset, same train/test split.
- **Metrics:** classification accuracy/AUC, and — separately — wall-clock
  and memory scaling as dataset size grows, since that's the part where
  "large data + quantum kernel" is either genuinely enabled by Perun or just
  padding.

### How this is studied today
Quantum kernel methods are a real, established QML sub-field going back to
Havlicek et al.'s original quantum kernel estimation proposal, but a growing
body of "dequantization" work shows classical methods (random Fourier
features, tensor-network surrogates) can match quantum kernel performance in
most practical regimes — and a 2024 benchmarking study titled "Quantum
kernel methods under scrutiny" specifically stress-tests these claims and
finds the advantages are narrower than often presented. Nearly all published
quantum kernel experiments use small datasets (hundreds to low thousands of
rows); genuinely large-scale quantum kernel classification is rare
specifically because kernel matrix cost and quantum circuit evaluation cost
both scale badly with dataset size.

### Bull case
This is the one idea of the three where "big data" is not artificial padding
— kernel matrix construction and solving at real scale is a legitimate
GPU-HPC workload regardless of where the kernel values come from, so the
infrastructure story is honest. If the quantum kernel's inductive bias
happens to suit the dataset, you get a real accuracy delta at a scale nobody
else has tested.

### Bear case
Since Qaptiva is a classical simulator, there is no possible computational
speed advantage from "quantumness" itself — only a possible difference in
which functions the kernel can represent well. Dequantization research
argues that in most practical regimes classical surrogates match quantum
kernel behavior. Cost also scales badly two ways at once: kernel matrix
construction is O(n²) and each entry requires a quantum circuit evaluation,
so "large dataset" and "quantum kernel" pull against each other computationally
— you may be forced back toward the Nyström/subsampling approximations that
undercut the "true large-scale" framing.

### Likely outcome
Most likely: performance roughly matches the classical kernel baseline, with
the quantum kernel being substantially more expensive to compute — a result
consistent with the dequantization literature. A genuine accuracy edge on a
specific dataset is possible but would need to be checked carefully against
kernel scrutiny methodology to rule out confounds (calibration, kernel
normalization, unfair baseline tuning).

### Value if null
Good, if framed honestly. "We ran the largest-scale quantum kernel
classification study to date, using real HPC infrastructure to make it
possible, and found the classical baseline matches it at a fraction of the
cost" is a legitimate, citable scaling result — genuinely useful to the field
even though it's a negative headline finding.

---

## Summary comparison

| Idea | Infra story honesty | Existing precedent | Most likely result | Null-result value |
|---|---|---|---|---|
| 7. QCBM + GPU discriminator | Strong — tight, high-frequency loop | Small-scale precedent (QCA-MolGAN, superconducting demos) | Comparable fidelity, slower per epoch | Moderate–good |
| 8. Quantum layers at scale | Strong — matched-baseline test rarely done at this scale | Mixed/contested literature | No significant difference at matched params | Good |
| 9. Quantum kernel at scale | Strong — kernel matrix cost is genuine HPC workload | Established sub-field, but almost all small-scale | Comparable accuracy, worse cost | Good |

**Overall recommendation:** all three are legitimate, well-grounded projects
with real scientific value even in the (statistically most likely) case of a
null result — because in each case the null result is itself informative and
comes from infrastructure nobody else has used to test it this way. Idea 8
has the strongest existing debate to contribute to; idea 7 has the most
interesting best-case upside; idea 9 has the cleanest "why Perun" story.