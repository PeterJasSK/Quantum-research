# QH Idea 17 — Quantum-Proposed Tumour: can one quantum-enhanced MCMC engine generate every random layer of a synthetic tumour, correct by construction, and where does the quantum proposal actually speed it up?

**Tag: QUANTUM · qh · effort: high · QC: yes (sim-first, then Heron r2 / r3) · master's thesis spine**

## Pitch
QuantumPhantoms used the measured circuit *as* the sample, so noise corrupted the tumour and a classical coin could
fake the quantum part (F4 fate-dial flaw). Layden et al. (Nature 2023) show the honest pattern: the quantum circuit
only *proposes* the next state of a Markov chain, a classical Metropolis step accepts or rejects it with the exact
energy, so the output distribution is correct no matter how noisy the hardware is — quantum only changes how fast the
chain mixes. We rebuild the tumour generator around that one principle: every random layer (genotype, phenotype,
clone map) is a Boltzmann distribution with a classical energy, sampled by one engine with pluggable proposals
(local, uniform, tensor-network, quantum-sim, quantum-hardware). The headline result is a per-layer measured mixing
speedup and its error threshold ε\* — which layers quantum helps, and which it does not.

**Paper strength score: 72/100** — Nature-line method applied to a data-fitted, frustrated, clinically meaningful
energy (not an invented one), correctness guaranteed classically, and a null on some layers is expected and
reportable; docked because the speedup at n ≤ 40 may be small or absent, all-to-all couplings cost many CZ on
heavy-hex, and the sequential chain is QPU-latency heavy.

## The principle
"Fully quantum tumour" means precisely: **every stochastic layer draws its proposals from a quantum circuit; every
layer's distribution is defined and checked classically.** Growth dynamics and rendering stay deterministic. No layer
may claim quantum benefit without its measured mixing comparison against the classical proposals.

## Layers (each = energy model E(x | upstream) + the shared engine)
| Layer | State x | Energy from | Size (qubits) | Expected quantum value |
|---|---|---|---|---|
| **G Genotype (tumour start)** | driver-mutation on/off per gene | pairwise Ising / max-ent fit on TCGA LUAD mutations (cBioPortal); co-occurrence = ferro, mutual exclusivity (e.g. KRAS vs EGFR) = antiferro → frustrated | 12–40 | **main claim** — spin-glass-like, Layden regime |
| **B Phenotype** | size / type / margin / location | stage B Bayesian network as E = −log P, conditioned on genotype; rare-case evidence clamped | 5–10 | likely none (small, exact inference wins) — reported honestly |
| **C Clone map (heterogeneity)** | clone label per tumour patch | Potts over patches; couplings from genotype (subclones with exclusive drivers compete = antiferro) | patches × log2(clones), e.g. 16 × 2 = 32 | medium — only if competition makes it frustrated; pure ferro Potts is easy for Swendsen–Wang |
| A Placement | voxel region in LIDC lung | anatomy prior | — | classical (low-dimensional), same engine API for uniformity |
| E Growth → F Render | grown volume in CT | deterministic grower driven by clone map | — | none; consumes samples |
| G Provenance → H Analysis | — | logs every proposal (backend, circuit hash, acceptance rate, chain diagnostics) | — | provenance of *how* each tumour was sampled |

## How it becomes a study
**Research question:** For the genotype and clone-map energies of a synthetic lung tumour, does a quantum-proposal
Metropolis chain on Heron mix faster than local, uniform and tensor-network proposals as n grows, and below which
two-qubit error ε\* does that advantage survive?

**Hypothesis:** On the TCGA-fitted genotype Ising, the quantum proposal shows a smaller gap-scaling exponent than
local and uniform proposals in simulation and at n ≤ 12 on hardware; the clone map shows an advantage only in the
competing-clone regime; phenotype shows none.

**Method:**
- Fit genotype Ising by pseudo-likelihood on TCGA LUAD; prune small couplings to cut CZ count; check frustration.
- Proposal circuit: Layden quench H = (1−γ)H_prob + γH_mix, Trotterized; parameters per Orfi–Sels regime.
- n ≤ 12: estimate full proposal matrix on hardware, exact spectral gap. n = 16–40: long chains in a Qiskit Runtime
  session, integrated autocorrelation time.
- Noise sweep (calibration tiers + gate folding) → α(ε) → ε\* per layer, r2 vs r3.
- Pipeline: genotype → phenotype → clone map → placement → growth → render on LIDC host, end to end.

**Baselines:** local single-flip Metropolis; uniform proposal; Swendsen–Wang (clone map); tensor-network proposal
χ ≤ 8 (Christmann et al., verify); exact enumeration where n ≤ 20 for ground-truth distribution checks.

**Metrics:** gap exponent α per layer and proposal; τ_int(n); ε\*; total-variation distance of samples to the exact
distribution (must be ≈ 0 for every proposal — the correctness guarantee); QPU seconds per effective sample.

**Novel contribution:** the first generative pipeline where quantum hardware is in the loop without being able to
corrupt the output, with a per-layer measured answer to "does quantum help here?".

## Connection to what already exists
- qh-15 (ε\* threshold) = the measurement core of this idea; qh-16 = phenotype-layer alternative (rare evidence).
- QuantumPhantoms pipeline A–H and RE letter B (B-5 QeMCMC reproduction: none at 6 spins, 1.5× at 8):
  `QuantumPhantoms/plans/relatedPapers/reverse-engineering/B_mapping/`, LS1 in `feature-QLONG-*.md`.
- Imaging grower / LIDC renderer from MVP F5.

## Prior work check (from qh-15 plus)
Layden 2023 (Nature, 2203.12497); Ferguson–Wallden 2025 (2405.04247); Orfi–Sels 2024 (2408.07881); Marshall 2026
(2602.06171, QeMCMC optimisation 117 vars); Christmann 2024 (2411.17821, verify). Needs a citation check: published
Ising / max-ent fits of cancer driver-mutation co-occurrence; mutual-exclusivity tools (MEMo, DISCOVER).

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** the genotype layer shows a clear exponent gap in sim and a measured ε\* just above r3 error; full
pipeline renders cohorts in CT; QCE27 paper plus thesis.
**Bear:** fitted genotype Ising is weakly frustrated, local Metropolis mixes fine at n ≤ 40, no quantum gain on any
layer.
**Likely:** modest gain on genotype in sim, marginal on hardware at small n, none on phenotype, conditional on
clone map.
**Value if null:** a working generator correct by construction, plus "real tumour-genotype landscapes are (not)
hard enough for QeMCMC, and here is the error rate needed" — a clean per-layer answer instead of a decorative claim.

## Thesis — master's thesis + IEEE short paper (6–8 pp)
**Central question:** where in a synthetic-tumour generator does a quantum proposal speed up sampling?
**Single defended claim (paper):** on the TCGA-fitted genotype energy, the quantum proposal mixes with exponent α_q
< α_classical for ε < ε\* = X, measured on Heron.
**Thesis chapters:** 1 engine + pipeline (engineering) · 2 genotype layer + ε\* (core) · 3 clone-map layer ·
4 per-layer verdict.
**Target venue:** IEEE QCE 2027 (Applications / Algorithms).
**Compelling-study likelihood: 72/100.**

Open risks for planning: CZ cost of all-to-all genotype couplings on heavy-hex (pruning, qubit ordering); sequential
chain latency (sessions, batched parallel chains); IP — rebuild pipeline pieces from public RE material if the
QuantumPhantoms code is Siemens-owned.
