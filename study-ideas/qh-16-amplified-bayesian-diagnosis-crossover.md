# QH Idea 16 — Amplified Bayesian Diagnosis: below what evidence probability does quantum rejection sampling beat classical on real hardware?

**Tag: QUANTUM · qh · effort: medium-high · QC: yes (sim-first, small networks on Heron)**

## Pitch
Diagnosis with a Bayesian network means conditioning on evidence ("patient has dyspnoea, X-ray abnormal"). When the
evidence is rare (probability P), classical rejection sampling wastes ~1/P samples per useful one; Low, Yoder &
Chuang (2014) proved quantum rejection sampling with amplitude amplification needs ~1/√P. Borujeni et al. ran plain
quantum Bayesian networks on IBM QX in 2020 and left "fault-tolerant circuits to manage the noise" as future work;
no amplification survived the hardware then. On Heron, ~280 two-qubit gates fit before fidelity halves, enough for
1–3 Grover iterations on small clinical networks. We measure the crossover P\* where the amplified sampler delivers
more correct accepted samples per unit cost than classical rejection, with and without error detection and with
fixed-point amplification (Yoder–Low–Chuang), and track how P\* would move with r3.

**Paper strength score: 70/100** — continues a named future-work line with a provable (query) advantage and a
clinical-shaped task; prior hardware evidence is a single course project and one 2026 preprint to check; docked
because the advantage is per query not wall-clock, small networks are classically trivial, and deep Grover circuits
may not survive at all.

## How it becomes a study
**Research question:** For a small clinical Bayesian network on Heron, below what evidence probability P\* does
amplified quantum rejection sampling yield more correct accepted samples per circuit cost than classical rejection
sampling?

**Hypothesis:** With 1–2 Grover iterations and post-selection on an error-detecting check, a P\* exists on Heron r2
in the range 1/16–1/64 for networks of 4–6 binary nodes; without detection no P\* exists.

**Method:**
- Networks: the classic Asia (lung cancer / tuberculosis) network cut to 4–6 nodes, plus synthetic networks with
  tunable P(e) from 1/4 to 1/256. CPTs encoded by Borujeni's circuit construction (multi-controlled RY).
- Samplers: (a) plain q-sample + measure + reject; (b) k-iteration amplitude amplification, k chosen for P(e);
  (c) fixed-point amplification (robust to unknown P); (d) (b)/(c) inside an error-detecting code with post-selection.
- Cost unit: two-qubit-gate-weighted shots (and raw shots); correctness: total-variation distance of the accepted
  posterior to the exact posterior (numpy enumeration, already built in RE letter B).

**Baseline:** classical rejection sampling (exact 1/P cost); classical likelihood weighting; exact inference (to
state plainly that small networks are classically trivial — the claim is about the sampling scaling).

**Metrics:** accepted-correct samples per cost unit vs P; crossover P\*; posterior TVD; post-selection kept
fraction; P\* forecast at r3 error.

**Novel contribution:** the first hardware measurement of the evidence-probability crossover for amplified Bayesian
inference, and whether error detection is what makes it exist.

## Connection to what already exists
- RE letter B (Borujeni reproduction, numpy reference inference, B-1/B-2 circuits):
  `QuantumPhantoms/plans/relatedPapers/reverse-engineering/B_mapping/`.
- Error detection on hardware: `ErrorDetectionVSRawBits/` (check which code it implements before reuse).
- Grover-depth machinery and query-advantage honesty rules: `THESIS/NPQuantumAdvantage/` (thesis-4) and idea
  `qh-7-grover-advantage-cliff.md` — sibling: qh-7 asks where unstructured search dies; this asks where *conditioned
  inference* wins. Must not duplicate qh-7's search-size sweep.

## Phantoms integration (master's thesis spine)
QuantumPhantoms stage B already IS a Bayesian network (size → type → margin → location, conditioned on CT context).
Evidence = the rare case a clinician wants ("juxtapleural, spiculated, part-solid, ≥ 8 mm"). The amplified sampler
becomes stage B's rare-case engine: sampled phenotypes flow into A placement → E growth → F render → G provenance →
H analysis, giving a rare-condition synthetic cohort. Thesis = engineering pipeline + measured P\* for the quantum
stage. Honesty: for small networks exact classical inference samples the posterior with no rejection at all, so the
quantum claim is the scaling frontier (high-treewidth networks), the pipeline is the demonstrator. IP check: confirm
the QuantumPhantoms code is not Siemens-owned before reusing it in the thesis.

## Prior work check (2026-11-18)
| Work | What it did | Gap left for us |
|---|---|---|
| Low, Yoder & Chuang 2014 (1402.7359) | quantum rejection sampling, O(P^-1/2) | theory only |
| Borujeni et al. 2021 (2004.14803) | circuit construction for QBNs | no amplification |
| Borujeni et al. 2020 (2005.12474) | QBNs on 9 IBM QX devices, noise effect | future work = noise management; no amplification |
| pyAgrum qBNSampling | simulator implementation incl. Asia network | simulator only |
| Temple course project 2025 (IBM Torino) | 24 Grover iterations, ~27 % success vs 99 % sim | course report, no crossover, no detection |
| QANTIS 2026 (2603.00785, 2607.06760; checked 2026-11-19) | Neura Parse Ltd preprints, no journal ref. Tiny Tiger POMDP belief updates on Heron: no-amp vs Grover vs FPAA, BIQAE; "operating envelope, not advantage claim" | **overlaps the FPAA/rare-evidence arm.** Publishes no classical-baseline comparison (repo withholds data and benchmarks), so the P\* crossover vs classical rejection is still open. Peter's verdict: quantum for its own sake, no point |
| Quantum BNs for POMDP RL (2507.18606) | quantum BN speed-up in RL | theory/sim |

Verdict: viable but QANTIS must be read before committing; if it already reports a hardware crossover, pivot to the
error-detection / fixed-point arm only.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** a clean P\* with detection on r2, none without; the r3 forecast doubles the usable range. A crisp QCE27
figure: two curves crossing.
**Bear:** CPT encoding of even 5 nodes costs too many CZ, one Grover iteration already destroys the posterior, no
P\* anywhere.
**Likely:** P\* exists only for the smallest networks with detection and k = 1.
**Value if null:** "amplified inference has no crossover on 2026 hardware; it needs error below X" is a clean, cited
negative and a concrete hardware target.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** does amplified Bayesian inference beat classical rejection anywhere on today's hardware?
**Single defended claim:** below P\* = X, with error detection, Heron delivers more correct accepted samples per cost
than classical rejection sampling.
**Why it fits 6–8 pp:** one network family, four samplers, one crossover figure.
**Target venue:** IEEE QCE 2027 (Applications / Algorithms).
**Compelling-study likelihood: 70/100.**
