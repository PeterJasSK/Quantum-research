# QH Idea 15 — QeMCMC Noise Threshold: at what two-qubit error does the quantum-enhanced MCMC speedup die on real hardware?

**Tag: QUANTUM · qh · effort: high · QC: yes (sim-first, then Heron r2 + r3 comparison)**

## Pitch
Quantum-enhanced Markov chain Monte Carlo (Layden et al., Nature 2023) uses a quantum circuit as the *proposal*
step of an otherwise classical Metropolis chain, so hardware noise only slows mixing and never biases the samples.
Ferguson & Wallden (2025) state the open question plainly: *"concrete analysis for the level and types of noise
under which we maintain the quantum scaling advantage is an important open question."* Hardware improved about
15× in two-qubit error since Layden ran on Falcon-era IBM; nobody has measured the speedup *exponent* against error
rate on real devices. We measure the spectral-gap / mixing-time scaling on Heron r2 and r3 as n grows, sweep the
effective error, and report the threshold ε\* below which the polynomial speedup survives — a dated forecast of when
the method becomes useful.

**Paper strength score: 74/100** — continues a named open question in a Nature-level line, MCMC has real users,
and the result is a number (ε\*) that moves with hardware; docked because Orfi & Sels show the advantage needs
fine-tuned quenches, quantum-inspired tensor-network proposals may tie, and the chain loop is QPU-latency heavy.

## How it becomes a study
**Research question:** On real Heron processors, does the QeMCMC spectral-gap scaling exponent stay above the best
classical proposal as n grows, and at which effective two-qubit error ε\* does the advantage vanish?

**Hypothesis:** At r2 error (~0.25 %) the exponent advantage survives to n ≈ 12–20 for SK instances and closes
beyond; at r3 (~0.15 %) the crossover moves to larger n; ε\* lies between 0.1 % and 0.5 %.

**Method:**
- *Small n (8–12):* estimate the full proposal matrix Q(s′|s) on hardware (as Layden did) and compute the exact
  gap δ of the resulting Metropolis chain. Fit δ ∝ 2^(−αn) for quantum vs classical proposals.
- *Larger n (16–40):* the matrix is out of reach, so run long chains and measure integrated autocorrelation time of
  energy / magnetisation; compare with classical chains on the same instances.
- *Noise sweep:* same circuits on calibration-sorted qubit tiers (best / median / worst) and with unitary gate
  folding to raise effective error → curve α(ε) → ε\* where α_quantum = α_classical.
- Sim-first: ideal + FakeFez/FakeMarrakesh noise to set n range and quench parameters (Orfi–Sels intermediate
  regime) before any QPU minute.

**Baseline:** local single-spin Metropolis; uniform proposal; classical clone/cluster moves where applicable;
quantum-inspired tensor-network proposal at bond dimension χ ≤ 8 (Christmann et al. 2024) — the adversary that
decides the claim.

**Metrics:** gap exponent α (quantum vs each classical baseline, with CI); autocorrelation time τ(n); ε\*; QPU
seconds per effective independent sample.

**Novel contribution:** the first measured noise threshold ε\* for the QeMCMC scaling advantage on real hardware,
with an r2 → r3 comparison that turns "when hardware improves" into a number.

## Connection to what already exists
- QuantumPhantoms RE letter B, target B-5 (QeMCMC reproduction: no advantage at 6 spins, 1.5× at 8):
  `QuantumPhantoms/plans/relatedPapers/reverse-engineering/B_mapping/`.
- Ladder rungs A1–A3 and obstacles in `QuantumPhantoms/plans/feature-QLONG-long-shots-heterogeneity-predictive-growth-chemistry.md` §4.3.
- Calibration-tier selection: `CalibrationGuidedHighYieldQRNG/`; calibration pruning in QP `code/`.
- Sibling, not overlap: `qh-13` / number-partitioning QAOA (optimisation, not sampling).

## Phantoms integration (optional second thesis chapter)
QeMCMC fits QuantumPhantoms long shot LS1 "heterogeneity sampling" (B-5): a Potts / Ising energy over tumour patches
(clone domains × phenotype) sampled by the quantum-proposal chain gives the intra-tumour heterogeneity map that E
grows and F renders as texture. Weaker fit than qh-16: the energy model is invented, not a clinical rulebook. Use
the pipeline as demonstrator; the claim is ε\* on SK-type instances. Same IP check as qh-16.

## Prior work check (2026-11-18)
| Work | What it did | Gap left for us |
|---|---|---|
| Layden et al. 2023 (2203.12497) | QeMCMC, hardware at small n on IBM, gap from estimated Q | no noise-vs-exponent curve; old hardware |
| Ferguson & Wallden 2025 (2405.04247) | coarse-grained QeMCMC with √n qubits | names noise threshold as open question |
| Orfi & Sels 2024 (2408.07881) | gap bounded by IPR; advantage needs fine-tuned quench | tells us *which* quench to use; no hardware |
| Marshall et al. 2026 (2602.06171) | QeMCMC for MIS optimisation, 117 decision variables on IBM | optimisation + iterations-to-optimum, not sampling gap vs noise |
| Claudon et al. 2026 (2603.08395) | quantum-walk MCMC with amplitude estimation on Quantinuum | different algorithm |
| Adiabatic dressing (2603.28076), irreversible QeMCMC (2606.23350) | theory variants with larger gaps | candidate proposals to test; no hardware threshold |
| Christmann et al. 2024 (2411.17821, verify) | quantum-inspired classical proposals | the adversary we must include |

Verdict: viable. The specific measured quantity (α vs ε, ε\*) appears not to be published; Marshall 2026 is the
closest and must be cited and distinguished.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** clear exponent advantage at small n on r3, measured ε\* sitting just above r3 error — "useful on the next
generation" with evidence. Strong QCE27 paper, possibly PRX Quantum.
**Bear:** the advantage at n ≤ 12 is too small to fit exponents, the tensor-network adversary ties, and the chain
loop eats QPU budget.
**Likely:** a modest exponent gap in sim, a measured ε\* between r2 and r3, adversary ties at the smallest sizes.
**Value if null:** "on 2026 hardware the QeMCMC advantage is below threshold, and here is the error rate needed" is
exactly the number Ferguson–Wallden ask for.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** what error rate does the QeMCMC speedup need?
**Single defended claim:** the gap-scaling advantage survives for ε < ε\* = X, measured on Heron r2 and r3.
**Why it fits 6–8 pp:** one algorithm, one instance family (SK), one sweep, one α(ε) figure.
**Target venue:** IEEE QCE 2027 (Algorithms / Benchmarks); extended version PRX Quantum or Quantum.
**Compelling-study likelihood: 74/100.**

Open risks to settle in planning: QPU latency of a sequential chain (batch many independent chains per job;
parameterise the current state as input bits); which quench parameters (Orfi–Sels regime); access to an r3 device.
