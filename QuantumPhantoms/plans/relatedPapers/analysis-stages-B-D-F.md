# Stages B, D (the quantum claim) and F (the image): deep-dive analysis

**Date:** 2026-10-28 · **Scope:** full pipeline, not the MVP · **Target hardware:** IBM Heron r2 (heavy-hex, 156 q)
**Reading list:** `README.md` (this folder). The codes in brackets (B09, D15, HW04 …) are files in `papers/`. Reverse-engineering work: `reverse-engineering/`.

---

## 0. The test every quantum stage must pass

A stage's output is the set of Z-basis bits that feed the image. **Any Z-basis distribution over a few
qubits can be reproduced by a classical sampler that is given the same probabilities.** So the image can
never carry "quantumness" by itself. Non-classicality lives only in statistics measured in
several bases (Bell/CHSH, entanglement witnesses) or in resource costs (memory, sampling hardness).
Every claim must therefore name its level:

| Level | Claim | Evidence needed | Status on Heron r2 |
|---|---|---|---|
| **L0 provenance** | Nobody chose the draw | CHSH > 2 in the same job [C01, C02] | Achievable now. Done in the MVP. |
| **L1 non-classical generative state** | The growth state was entangled while the tumor was being generated | Witness per generation, e.g. ⟨XX⟩+⟨ZZ⟩ > 1, or mutual-information networks [D14] | Achievable at small width. The `ghz2` certificate survived on `ibm_marrakesh` (≈1.96). |
| **L1′ resource advantage** | The quantum model of the growth *process* needs less memory than any classical one | Measured C_q < C_μ [D06, D16, D17] | Achievable (1–3 memory qubits). **Not done for any biology process yet.** |
| **L2 classical hardness** | The output distribution cannot be sampled efficiently classically | Cross-entropy benchmarking vs. supercomputer [C02] | **Not reachable with meaningful biology.** Shallow heavy-hex circuits are belief-propagation-simulable [HW04]. |
| **L3 computational advantage** | Quantum computes biology faster or better | Asymptotic proof plus hardware | Fault-tolerant only [D21, B11, B13]. |

**Thesis position:** deliver L0 + L1 + L1′, and **measure the gap to L2** (cohort drift and witness collapse vs. width and depth).
This is what "small-now, scalable-10yr" means in concrete terms.

### 0.1 A finding in the current code (fix before any claim)

`code/f4_qalife/loop.py:42` `_fate_prep` implements the "fate interference phase dial" as a
**single-qubit** Ramsey sequence `h – rz(φ) – h`. Measured in Z, this gives P(f0=1) = sin²(φ/2), which is
exactly a classical biased coin. Pillar 6 in `future.txt` ("at fixed property frequencies, a phase dial
shifts how traits correlate — no classical sampler reproduces that") is **not true as implemented**.
To make it true, the phase has to act on a **correlation between ≥ 2 qubits** (e.g. sister-cell fates) and be
read out in **≥ 2 bases**: the Z marginals stay fixed while ⟨XX⟩ moves with φ. Even then, the claim is L1
(a witness), not L2.

### 0.2 Quantum biology: what can and cannot be claimed

- Real biological quantum effects exist only at the molecular scale and are short-lived: radical-pair
  magnetoreception, tunnelling in enzymes, and excitation transfer in photosynthesis [Q01, Q03 (manual)].
  Even the photosynthesis coherence story was walked back: inter-exciton coherences are too short-lived
  to matter functionally [Q02].
- Decoherence in warm, wet tissue takes 10⁻¹³–10⁻²⁰ s [Q04]. **Tumor growth is a classical
  stochastic process.**
- So **never** argue "quantum because cancer is quantum". The legitimate framing is *representational*:
  the quantum computer is a generative substrate whose primitives (replicate, mutate, interact, die)
  mirror clonal biology [D01, D02], and quantum mechanics permits self-reproduction without design
  [Q05]. The defensible "quantum simplifies biology" result is the memory advantage for simulating
  stochastic processes [D06–D08, D16, D17], and tumor growth is such a process.
- Reviews of health and medicine QC put the whole field at the proof-of-concept stage [B14, B07, B08].
  Data loading is the generic killer for "put the patient into the qubits" [B13].

---

## 1. What Heron r2 (heavy-hex) can carry

**Hardware facts:**
- 156 fixed-frequency transmons on a heavy-hex lattice (qubit degree 2–3) [HW01], with tunable couplers and CZ native.
- Fractional gates RZZ(θ)/RX(θ) are available on Heron [HW03].
- Dynamic circuits are supported: mid-circuit measurement, reset and feed-forward [HW05, HW06].
- Layer fidelity / EPLG is the right scale metric [HW02]. Published EPLG snapshots: about 0.4–0.8 % (`ibm_fez` 0.8 %, `ibm_marrakesh` ≈ 0.4 %). These change with every calibration, so check live properties.

**Own measurements** (from this repo's QDEP and PJ2.4 runs):
- Readout error ≫ 2q error on Heron r2.
- Teleport-routing does not beat SWAP routing on Heron r2.
- Coherent multi-generation genealogy (Mode B) collapses, so it is blocked.
- Constant-depth, measure-and-restart Mode A survives.

**What the literature says about limits:**
- A fully connected problem passes the depth benchmark only up to about **20 qubits** on the best Heron (`ibm_fez`). Native-layout and 1-D chain problems scale to 100+ qubits [HW03]. → Keep all-to-all registers ≤ 15–20 q, and lay everything larger along heavy-hex paths.
- A 1-D Goldilocks QCA ran on chains of up to **23 qubits** with about **1,056 two-qubit gates** and still showed complex-network structure [D14].
- A measurement-induced entanglement transition ran on **14 IBM qubits** with repeated mid-circuit readout [D15].
- A 4-node quantum Bayesian network on older IBM devices showed clear transpiler- and device-dependent distortion [B10]. → Expect rulebook drift. Measure it (TVD vs. rulebook) as a result, not a failure.
- Belief-propagation tensor networks simulate 127-qubit heavy-hex kicked-Ising dynamics better than the device [HW04]. → **Everything native and shallow on heavy-hex is classically simulable.** This rules out an L2 claim and is fine for L0/L1.

### 1.1 Budget table (per draw/job)

| Construct | Qubits | 2q depth (after routing) | Heron verdict |
|---|---|---|---|
| Rulebook QBN (size 2, type 2, margin 2, lobe 3, shape 3–5) [B01, B09] | 9–14 | ~20–60 CZ (multi-controlled Ry) | ✅ Expect measurable drift |
| + CT context as **classical angle selection** | +0 | +0 | ✅ trivial |
| + CT context as **quantum root nodes** (candidate sites in superposition) | +3–5 | +10–30 | ✅ |
| + CT context as **evidence** via amplitude amplification [B01] | +ancillas | × O(1/√P(e)) Grover rounds | ❌ only 0–1 rounds; theory only |
| Amplitude-encoded CT patch (FRQI/NEQR, quantum blur) [B04, B13] | 6–12 | Exponential in the address qubits for general data | ❌ demo only, claim nothing |
| QALife division + fate (Mode A, per generation) [D01, F4] | 4–11 per cell | ~3–15 | ✅ done (Aer), GHZ certificate on HW |
| Mode A **in one job** via dynamic circuits [HW05, HW06] | 10–30 | per-generation constant + mid-circuit readout | ✅ / ⚠️ readout error and latency, use DD (PJ2.5) |
| Coherent multi-generation genealogy (Mode B) | — | grows with generations | ❌ blocked (QDEP) |
| Heavy-hex QCA "tissue patch" (Goldilocks rule) [D13, D14] | 20–40 | 10–30 Floquet layers | ✅ with mitigation; classically simulable |
| Monitored growth with mid-circuit "commitment" [D15] | 10–20 | ≥ 10 rounds | ✅ / ⚠️ needs many shots; post-selection issue |
| Quantum memory-efficient stochastic model of division timing [D16, D17] | 2–4 | small, repeated | ✅ small, the cleanest L1′ |
| Quantum-enhanced MCMC proposals on a tumor/anatomy Ising/Potts energy [B11, B12] | 10–27 | moderate (Trotter steps) | ⚠️ runs; advantage only in ideal simulation |
| Discrete-time quantum walk "invasion" on an anatomy graph [D19, D20] | 8–20 | grows with steps | ⚠️ depth-collapse (see the Galton-board epic) |
| Reaction–diffusion PDE (Carleman/QLSA) [D21], QAE cohort audit | 100s logical | — | ❌ fault-tolerant only (10-yr spine) |

---

## 2. Stage B: mapping biology + CT context into the circuit

Input from stage A: candidate sites, each with a context vector (lobe, distance to pleura, vessel density,
airway proximity, local HU), plus the published rulebook (conditional probabilities).
Output: one certified joint draw of (site, size, type, margin, shape seed) per tumor.

### B-1 Classically conditioned QBN (the production default)
The context selects which conditional probability table the circuit uses. In practice it is a classical lookup:
`angles = f(rulebook, context)`, then the existing F1 circuit. This is the Low–Yoder–Chuang / Borujeni
construction [B01, B09], with roots as Ry and children as controlled Ry.
- **Claim:** L0. **Cost:** none beyond F1. **Risk:** none.
- **Honest wording:** "context-conditioned certified draw", not "quantum reads the anatomy".

### B-2 Joint site × phenotype draw with constraint rules (the recommended quantum-native contribution)
Put the K candidate sites into superposition (⌈log₂K⌉ qubits) as root nodes. Make the phenotype nodes
controlled on the site register, and encode anatomy-compatibility rules (no ground-glass at the pleura,
juxtavascular → lobulated more likely, and so on) as controlled rotations or as WFC-style local constraints [B02].
One measurement gives a jointly consistent (site, phenotype). The CHSH pair is in the same job.
- **Claim:** L0, plus "the anatomy-phenotype joint distribution was drawn in one certified quantum
  measurement". Note that the classical equivalent is a joint lookup table, so stay at L0.
- **Cost:** +3–5 q, keeping the all-to-all part ≤ 15–20 q (HW03 limit).
- **Thesis value:** this is the novel piece. No CT-conditioned quantum generators exist in the literature.

### B-3 QBN inference with CT evidence via amplitude amplification [B01]
Treat the context as *evidence* and amplify the matching samples. This gives a quadratic speedup over classical rejection
sampling. It is not NISQ-feasible beyond one Grover round. Cite it as the fault-tolerant upgrade path and
show 0–1 rounds on hardware as a demonstration.

### B-4 Amplitude-encode the CT patch (FRQI/NEQR/quantum blur) [B04, B05, B13]
The circuit literally "sees" an 8×8 or 16×16 patch. Preparing a general state costs depth exponential in the
address qubits, and reading the output back needs many shots. Aaronson's data-loading caveat applies in
full [B13]. Use it at most as a visual demo with a classical-blur baseline [B05]. **Do not build on it.**

### B-5 Energy-based placement and growth (QeMCMC) [B11, B12]
Write tumor-in-anatomy compatibility as an Ising/Potts energy. CT fields enter as local biases: vessels
attract (angiogenesis), pleura and bone repel, and same-phenotype neighbours couple. Sample it with
quantum-proposal MCMC, where the classical accept/reject step keeps the chain **provably correct** even under
hardware noise [B11]. The same Hamiltonian can then be used for growth in D, which unifies B and D.
Layden's group ran this on 27 IBM qubits, and the coarse-grained variant [B12] reaches lattices larger than the device.
- **Claim:** "correct sampler with quantum proposals". The convergence speedup is shown only in ideal
  simulation, so report the measured mixing time vs. a classical baseline (Metropolis), whichever way it goes.
- **Thesis value:** strong research chapter. Its coupling graph can match heavy-hex natively.

### B-6 Hardware-native "tissue graph"
Map the voxel/cell neighbourhood around the chosen site onto a heavy-hex sub-patch, so that qubit = cell and the
coupler weight comes from CT density. This is the substrate shared with D-3 and B-5.

**Recommendation for B:** ship **B-1** now (an extension of F1). Build **B-2** as the quantum contribution.
Run **B-5** as a research arm if time allows. Cite B-3 and B-4 as limits.

---

## 3. Stage D: quantum (non-classical) growth

Input: the founder state from B. Output: a measured lineage (cells with genotype and fate, optionally positions), certified
bits, and witness values. The hand-off to E is: measured cells become the cellular automaton's initial lattice, and
SHA-256 of the certified raw counts becomes the PRNG seed (e.g. NumPy `Philox`). The receipt binds both.

### D-1 QALife Mode A (existing F4) [D01, D02]
Each generation is a separate constant-depth job (divide P1, fate P2, measure), with classical fitness and selection.
**Fix §0.1 first.** Use the division-pair witness ⟨XX⟩+⟨ZZ⟩ per generation as the headline.
- **Claim:** L1 within a generation, with classical genealogy. **Status:** built (Aer); the certificate already survived on hardware.

### D-2 Mode A in a single job with dynamic circuits [HW05, HW06] (recommended upgrade)
Run all generations inside **one** job:
1. Mid-circuit measure the daughter genotype.
2. Feed forward a conditional X to seed the next parent.
3. Reset the ancillas and repeat.
4. Interleave CHSH test rounds at random positions (hidden test rounds, certificate layer 1).

This puts the whole lineage and its certificate under one job ID and one calibration snapshot.
- **Costs:** Heron readout error (QDEP) and feed-forward latency idle the other qubits. Use DD (PJ2.5 lever) and keep the register small.
- **Selection:** fitness selection is classical, but a *threshold* rule (keep the daughter if fate ≠ necrotic) can run as feed-forward on-chip.
- **Claim:** L0 (strongest provenance) + L1.

### D-3 Heavy-hex QCA "tissue patch" (Goldilocks rules) [D13, D14, D03, D04]
Each qubit is a tissue site on a heavy-hex patch around the lesion. A Goldilocks rule (activate if exactly one
neighbour is active) behaves like a growth front. Run 5–20 Floquet steps and measure snapshots in the Z basis
(cells, to the CA) and in the X/Z bases (mutual-information network, entanglement). The heavy-hex degree-3 neighbourhood is the native
"tissue" geometry, so there are no SWAPs.
- **Claim:** L1, measured entangled growth-front structure. **Must state:** classically simulable by
  belief propagation at this depth [HW04].
- **Value:** the most visual link between quantum and image. The QCA snapshot *is* the cellular automaton's initial shape.

### D-4 Monitored growth: measurement as cell commitment [D15]
Entangling layers act as "proliferation/interaction", and mid-circuit measurement with probability p acts as "commitment"
(differentiation or necrosis). The measurement-induced entanglement transition at p_c gives a tunable
order parameter for "how quantum the growth stayed".
- **Claim:** L1 plus a measured phase-transition curve. This is publishable physics, but the biological meaning is thin.
- **Risk:** these transitions need post-selection or decoding tricks. Make it optional.

### D-5 Quantum causal-state model of the growth process (the honest "quantum simplifies biology") [D06, D16, D17]
Take the classical growth model from E (e.g. a renewal process for division timing, or a fate Markov chain) and build its
minimal classical model (statistical complexity C_μ) and its quantum model (C_q). Run the quantum model
on 2–4 Heron qubits and measure that it reproduces the process statistics with less memory or higher precision at fixed
memory, as in the photonic experiments [D07, D08, D16].
- **Claim:** L1′. It is **the only proven type of quantum advantage that applies to a biological growth process**, and
  nobody has done it for a tumor-growth model. The cost is small and it is publishable on its own.
- **Caution:** the advantage needs high correlations. Low-correlation models are compressed classically by tensor networks [D09–D12].

### D-6 Quantum-walk invasion [D19, D20, D18]
A DTQW on an anatomy graph (vessel or airway tree as edges) gives ballistic σ ∝ t vs. diffusive √t. Tune decoherence
(open-system channels [D18]) to move between the two. The depth-collapse behaviour is the same as in the Galton-board epic.
Realism is weak, since tumors do not spread ballistically. Use it only as an "invasion mode" knob.
**Avoid** modelling death as amplitude damping (a known bad design in this repo).

### D-7 Fault-tolerant spine (not to build)
Reaction–diffusion tumor PDEs via Carleman + QLSA [D21] (efficient only for R < 1 dissipative systems),
amplitude estimation for cohort audit, and QBN evidence inference at scale [B01]. These are the 10-year milestones.

**Recommendation for D:**
- **Core:** D-1 (fix the fate dial), then **D-2** (one-job certified lineage).
- **Headline research result:** **D-5**.
- **Bridge to image:** **D-3** (QCA snapshot as the CA seed shape).
- **Optional:** D-4.
- **Cite only:** D-6, D-7.

### 3.1 What the B+D combination can honestly be called
> "A certified quantum generative process: the tumor's founding anatomy-phenotype draw and its first
> generations are produced by entangled quantum dynamics on IBM Heron, with a measured witness per
> generation and a measured quantum memory advantage for the growth process. All later growth is
> classical, deterministic and replayable from the signed receipt."

Never call it: "more realistic because quantum", "quantum biology", or "classically impossible".

---

## 4. Stage F: making the image as good as possible

The order matters. Each step names its source.

1. **High-resolution lesion model.** Render the CA cell grid (≈ 0.1–0.2 mm) into tissue classes: proliferating
   solid rim, necrotic/low-attenuation core, ground-glass component, calcification. Set the HU per class **from
   LIDC measurements per type** (A02), not from guesses. The ground-glass vs. solid boundary is threshold-dependent in the
   literature (−400 vs. −160 HU) [F06]. Add the margin from a parametric morphology with a fitted edge profile
   (Solomon–Samei framework, manual) and spiculation as thin radial structures. Ambrosini's spherical-harmonic shapes are the baseline [F01].
2. **Partial volume.** Supersample (≥ 4× per axis) and integrate into the host voxel grid with a box/aperture
   filter. Never point-sample.
3. **Compose correctly.**
   - Insert an **additive delta**: (lesion − local background) after blurring. This preserves the host's real noise texture.
   - Where the lesion overlaps vessels, use the max-rule [F01].
   - Ground-glass must let vessels show through (α-blend toward the target HU, not replacement).
   - Clip juxtapleural lesions with the lung mask and merge them with the pleura.
4. **Match resolution.** Estimate the host scan's MTF from the patient image itself (air–skin edge method; Sanders,
   Hurwitz & Samei, Med. Phys. 2016, manual). Build a 3-D PSF from the in-plane kernel MTF plus the z slice-sensitivity profile, and
   convolve only the delta, so the host is not blurred twice.
5. **Match noise.**
   - With additive insertion the host noise remains, but CT noise is signal- and position-dependent, so add the
     residual noise inside dense lesions from a **local NPS + local σ map** (patch-wise NPS-filtered white noise blended
     with windows [F05]; Divel & Pelc, SPIE 2019, manual).
   - Check that the NPS inside the lesion matches the NPS outside.
   - The Mayo CNN approach reached SSIM 0.94 and ≈ 5 % noise error vs. projection-domain [Gong 2021, manual].
6. **Reconstruction-consistent upgrade.**
   - Projection-domain insertion into Mayo Siemens raw data [F03, A06] is the reference method.
   - A full open simulator is **XCIST** (GE's CatSim in Python, `pip install gecatsim`; Wu et al., PMB 2022, manual).
   - **DukeSim on NAEOTOM Alpha** [F04] is the best-fidelity, Siemens-native path.
   - Image-domain insertion is within 3 % of projection-domain in volume [F02], so start in the image domain.
7. **Learned refinement: ablation arm only.** DiffTumor [F07], histogram-regularized LDM nodules [F08]
   and MAISI [F11] can harmonize texture. All are **trained on patient data**, which breaks privacy-by-construction
   [H07, H08] and deterministic replay. If you use one, make it a separate, labelled arm with a fixed seed and a memorization check.
8. **Validate realism.**
   - (a) Physics: HU profile, edge 10–90 % width, and NPS vs. real LIDC nodules of the same size and type.
   - (b) PyRadiomics feature distributions [H05].
   - (c) A visual Turing test **in full anatomical context**. Isolated nodules fool readers, while in-context boundary
     shading gives fakes away [F09]. Current benchmarks are reader accuracy ≈ 64–66 % for state-of-the-art diffusion nodules [F08]; ≈ 50 % is the
     goal. Use the protocol from [F10].
   - (d) Train-synthetic / test-real detection [H01, A01].

**Biggest image-quality wins, ranked:** additive-delta insertion with patient-measured MTF (steps 3–4) >
type-correct HU from LIDC (step 1) > local-NPS noise (step 5) > supersampled partial volume (step 2) >
projection-domain (step 6).

---

## 5. New references (downloaded to `relatedPapers/papers/`)

**B: mapping**
- B09 Borujeni et al., *Quantum circuit representation of Bayesian networks*, ESWA 2021, arXiv:2004.14803. Explicit compact QBN circuits (Ry roots, controlled-Ry children, multi-state nodes). The template for the rulebook circuit.
- B10 Borujeni et al., *Experimental evaluation of QBN on IBM QX hardware*, arXiv:2005.12474. A 4-node QBN on nine IBM devices, showing hardware and transpiler distortion. The precedent for the drift measurement.
- B11 Layden et al., *Quantum-enhanced MCMC*, Nature 619 (2023), arXiv:2203.12497. Quantum proposals with classical accept/reject, provably correct under noise, run on IBM. Basis for B-5.
- B12 Ferguson & Wallden, *QeMCMC for systems larger than your quantum computer*, PRR 2025, arXiv:2405.04247. A coarse-grained variant that fits lattices larger than the device.
- B13 Aaronson, *Read the fine print*, Nat. Phys. 11 (2015). The data-loading and readout caveats that kill amplitude-encoded CT.
- B14 Flöther, *The state of quantum computing applications in health and medicine*, RDQT 2023, arXiv:2301.09106. A survey of 40+ medical QC proofs of concept; places the thesis in the field.

**D: quantum growth**
- D13 Hillberry et al., *Entangled QCA, physical complexity, and Goldilocks rules*, QST 6 (2021), arXiv:2005.01763. Rules that balance activity and stasis produce complex entangled structure. Basis for D-3.
- D14 Jones et al., *Small-world complex network generation on a digital quantum processor*, Nat. Commun. 2022, arXiv:2111.00167. The first QCA on hardware: 23 superconducting qubits, about 1,056 2q gates, measured network complexity.
- D15 Koh et al., *Measurement-induced entanglement phase transition … with mid-circuit readout*, Nat. Phys. 2023, arXiv:2203.04338. 14 IBM qubits, repeated mid-circuit measurement. Basis for D-4.
- D16 Wu et al., *Implementing quantum dimensionality reduction for non-Markovian stochastic simulation*, Nat. Commun. 2023, arXiv:2208.12744. Single-qubit-memory quantum models beat classical models at equal memory. Template for D-5.
- D17 Elliott, Garner & Gu, *Memory-efficient tracking of complex temporal and symbolic dynamics with quantum simulators*, arXiv:1803.05426. Theory for D-5.
- D18 García-Pérez, Rossi & Maniscalco, *IBM Q as a testbed for simulating open quantum systems*, npj QI 2020, arXiv:1906.07099. Channels and decoherence as tunable knobs on IBM.
- D19 Carney & Varcoe, *Universal statistical simulator*, arXiv:2202.01735. A quantum Galton board on IBM. Basis for D-6 and linked to the Galton-board epic.
- D20 Qiang et al., *Review on quantum walk computing*, arXiv:2404.04178. Hardware status of quantum walks.
- D21 Liu et al., *Efficient quantum algorithm for dissipative nonlinear differential equations*, PNAS 118 (2021), arXiv:2011.03185. Carleman + QLSA for reaction–diffusion-type models. Fault-tolerant spine.

**Q: quantum biology limits**
- Q01 Lambert et al., *Quantum biology*, Nat. Phys. 9 (2013), arXiv:1205.0883. Evidence for and against functional quantum effects.
- Q02 Cao et al., *Quantum biology revisited*, Sci. Adv. 6 (2020). The photosynthesis coherence claim walked back.
- Q03 Marais et al., *The future of quantum biology*, J. R. Soc. Interface 15 (2018). **Manual download:** https://pmc.ncbi.nlm.nih.gov/articles/PMC6283985/
- Q04 Tegmark, *The importance of quantum decoherence in brain processes*, PRE 61 (2000), arXiv:quant-ph/9907009. Decoherence times in warm, wet tissue.
- Q05 Marletto, *Constructor theory of life*, J. R. Soc. Interface 2015, arXiv:1407.0681. Self-reproduction is compatible with quantum physics without design. Philosophical background for QALife.

**HW: Heron r2 / heavy-hex**
- HW01 Chamberland et al., *Topological and subsystem codes on low-degree graphs with flag qubits*, PRX 10 (2020), arXiv:1907.09528. Why IBM chose heavy-hex (degree ≤ 3).
- HW02 McKay et al., *Benchmarking quantum processor performance at scale*, arXiv:2311.05933. Layer fidelity and EPLG definitions.
- HW03 Montañez-Barrera et al., *Evaluating the performance of QPUs at large width and depth*, arXiv:2502.06471. 24 QPUs including Heron r1/r2. Fully connected problems fail beyond about 20 q; native layouts scale.
- HW04 Tindall et al., *Efficient tensor network simulation of IBM's Eagle kicked Ising experiment*, PRX Quantum 5 (2024), arXiv:2306.14887. Heavy-hex shallow dynamics are belief-propagation-simulable, which blocks L2.
- HW05 Bäumer et al., *Efficient long-range entanglement using dynamic circuits*, PRX Quantum 5 (2024), arXiv:2308.13065. Feed-forward at 100+ qubit scale. Basis for D-2.
- HW06 Córcoles et al., *Exploiting dynamic quantum circuits in a quantum algorithm with superconducting qubits*, PRL 127 (2021), arXiv:2102.01682. Mid-circuit measurement and feed-forward on IBM.

**F: image**
- F05 Peng et al., arXiv:2303.02466. Whole-image CT noise synthesis from patch-wise NPS with windowed blending.
- F06 Lee et al., *High vs. low attenuation thresholds to determine the solid component of GGO nodules*, PLOS ONE 2018. HU thresholds (−400 vs. −160).
- F07 Chen et al., *Towards generalizable tumor synthesis (DiffTumor)*, CVPR 2024, arXiv:2402.19470. Diffusion refinement; ablation arm only.
- F08 Kannan et al., *Controllable lung nodule synthesis via histogram-regularized LDM*, arXiv:2605.30631. Reader accuracy 66 % on 50 real / 50 synthetic nodules. The current realism benchmark.
- F09 Han et al., *3D multi-conditional GAN lung nodules*, arXiv:1906.04962. Readers fooled without context but not with it; boundary shading matters.
- F10 Chuquicusma et al., *How to fool radiologists with GANs? A visual Turing test for lung cancer*, ISBI 2018, arXiv:1710.09762. The reader-study protocol.
- F11 Guo et al., *MAISI: Medical AI for synthetic imaging*, arXiv:2409.11169. NVIDIA CT foundation generator; context for learned alternatives.

**Manual / paywalled (F):**
- Solomon & Samei, *A generic framework to simulate realistic lung, liver and renal pathologies in CT imaging*, PMB 59(21):6637 (2014), doi:10.1088/0031-9155/59/21/6637.
- Sanders, Hurwitz & Samei, *Patient-specific quantification of image quality: automated measurement of spatial resolution in clinical CT*, Med. Phys. 43(10):5330 (2016), doi:10.1118/1.4961984.
- Wu et al., *XCIST — an open access x-ray/CT simulation toolkit*, PMB 67(19) (2022): https://pmc.ncbi.nlm.nih.gov/articles/PMC10151073/
- Divel & Pelc, *Image-domain insertion of spatially correlated, locally varying noise in CT*, Proc. SPIE 10948 (2019), doi:10.1117/12.2512453.
- Gong et al. (Mayo), *Deep-learning lesion and noise insertion for virtual clinical trial in chest CT*, Proc. SPIE 11595 (2021), doi:10.1117/12.2582106.