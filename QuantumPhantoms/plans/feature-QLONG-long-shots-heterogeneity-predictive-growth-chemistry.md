# Feature Q-LONG — Exploration: a staged road to the three long shots (heterogeneity sampling B-5, predictive growth D-5, quantum chemistry into E), validated on paper against Heron r3 and later hardware

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved). **The epic has no Q-LONG row**; the developer adds it (Q1). Q-LONG is the sibling of [feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md](feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md) (Draft): Q-HARD asked "what hardness can Heron r2 earn today", Q-LONG asks "what has to be true, and in what order, for each long shot to be reached".
**Feature ID:** Q-LONG (proposed, Q1)
**Author:** Claude (Fable 5.2)
**Date:** 2026-11-10
**Status:** Draft

> **Stack locked.** Python 3.13 (conda base `/home/peter/anaconda3/bin/python3`), pinned `requirements.txt` (qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy, networkx). Long shot 3 cannot be done without a chemistry stack: `pyscf`, `ffsim`, `qiskit-addon-sqd` are **not installed** (checked 2026-11-10) and are requested in Q4.
>
> **Core directive.**
> - **This is an exploration and validation plan.** Part I (§1, §4) is the finished desk study: for each long shot the obstacles with numbers, a ladder of routes ordered by hardware horizon, the papers behind each rung, a pass rule and a probability. Part II (§2, §6, §7) is the simulation-only follow-up that turns the first rungs into go / no-go numbers.
> - **Hardware assumption (given by Peter):** Heron r3 or better will be reachable. The plan therefore sizes every rung for four horizons (§4.2): H1 Heron r2/r3 and Nighthawk, H2 early fault tolerance (Kookaburra, Starling), H3 full fault tolerance (Blue Jay class). Nothing in this plan was run on a QPU or a circuit simulator. The only computations done while drafting were classical arithmetic on the `FakeMarrakesh` coupling map (§4.2).
> - **No automated tests.** Manual verification only (§7). Smoke runs ≤ 20 minutes (D-SCALE rule).
> - **Honesty gates (CLAUDE.md) apply.** Every probability is a subjective estimate with its basis. No long shot is claimed to work. Hardware jobs are Peter's, from a pack.

---

## 1. Why (Step Goal)

**The three long shots (translated from Peter's Slovak brief).**

1. **Heterogeneity sampling (layer B, branch B-5).** A tumour is not a homogeneous ball. It is a mixture of clones (genetically distinct cell groups) that are distributed differently in space and have different properties (growth rate, density, resistance). The three are linked: where a clone sits influences its phenotype. The object is a correlated field clones × space × phenotype. Classically it is sampled by MCMC, a random walk over configurations; under strong correlations the walk gets stuck in one tumour type and rare types are missing. Quantum-enhanced MCMC (Layden 2023) proposes jumps through a quantum circuit and mixes faster: more diverse tumours for the same time and money. Status: shown on small models. The thesis goal is to show the mechanism; practical gain comes at scale (2 to 5 years).
2. **Predictive growth (layer D, branch D-5).** From the tumour's history, predict how it will grow next: speed up, slow down, a new clone? Growth is a stochastic process. The module keeps what matters from the past in memory and generates probable future growth steps. In a digital twin this is the core: "what will this patient's tumour look like in 3 months?" Gu 2012 proved that a quantum model of a stochastic process needs less memory than any classical model for the same predictive accuracy, so a small model can hold a longer, more complex history. Status: proven in theory, shown in small experiments; on Heron noise killed it (L0). Practical value is modest; it is strong as a scientific result.
3. **Quantum chemistry (entry into layer E).** Compute the behaviour of the specific molecules that drive tumour biology: (a) hypoxia: the Fe(II) enzymes a cell uses to sense lack of oxygen; a hypoxic tumour responds worse to radiation (Varian); (b) drug metabolism: cytochrome P450, which decides how much drug reaches the tumour; (c) MR contrast: Gd / Mn contrast agents and how strongly they brighten a tumour on MR (Siemens MR).

**Before.**
- **B-5** exists only as an RE reproduction on a 2×2×2 voxel patch with one binary spin per voxel (`B_mapping/src/qemcmc.py`, `tumor_energy.py`): Layden's exponents reproduced (k_quantum 0.250 against 0.264), tumour-patch gap 0.0180 / 0.0121 / 0.0084 (quantum / local / uniform) at 8 spins, **no advantage at 6 spins**, and a noisy proposal with asymmetry 0.135 (`simulated: Heron-class noise (FakeMarrakesh)`). There are no clones and no phenotype in the model, and no comparison with a strong classical sampler.
- **D-5** is L0 on hardware (`pmd-bank` lost to a 2-bit classical model, gap / floor −2.88). The simulated gap is 10⁻³ in d_KL at a sampling floor of the same size. Q-HARD R1 (tick-clock) repairs the *certificate*; nothing yet repairs the *predictive model*.
- **Chemistry** does not exist in the project: no code, no dossier, no target molecule model, no dependency. Layer E takes its hypoxia and drug parameters from published constants.
- None of the three has a written route from "today" to "goal" with the conditions that hardware must meet.

**After this plan (Part I, done here).**
1. A **horizon table** (§4.2) that translates "Heron r3 or better" into budgets each long shot can spend.
2. For each long shot a **ladder of rungs** (§4.3 to §4.5): what is shown at each rung, on which hardware, against which classical adversary, with which papers, and with what probability.
3. Three **findings that reorder the work**:
   - **LS1.** The adversary of quantum-enhanced MCMC is no longer Metropolis; it is the *quantum-inspired* proposal (a classical tensor-network simulation of the same circuit). On heavy-hex (treewidth ≤ 4, Q-HARD §4.2) every proposal circuit shallower than the Q-HARD threshold is cheaply simulable, so **a real advantage in LS1 needs the same ≈ 2,000 to 2,900 CZ at ≤ 0.26 % loss that L2 needs**. Below that, the honest claim is "correct sampler, measured mixing, mechanism shown", which is exactly the thesis goal.
   - **LS2.** The failure on Heron was a failure of the *scoring statistic*, not of the memory advantage. The road is: a growth process whose classical memory *diverges* with time resolution (age-dependent division timing), scored by "smallest classical memory that matches the quantum model", then a model *learned from growth data* rather than written by hand.
   - **LS3.** The three chemistry targets are not equal. Cytochrome P450 has the best-documented quantum case, the hypoxia sensor (Fe(II)/O₂ binding) is the best open target, and **Gd / Mn contrast is the weakest quantum case** (half-filled shells, weak correlation, relaxivity set mostly by classical dynamics). The plan demotes it to a resource estimate (Q8).

**After the follow-up (Part II, to be approved).** A simulation-only package `code/qlong/` that produces, for the first rungs of each ladder, the predicted margin under Heron-class noise and under r3-scaled noise, a go / no-go, and hardware packs for the rungs that pass. Nothing is submitted.

---

## 2. Acceptance Criteria

Part II only. Part I is this document.

- [ ] **AC-1** (Q-LONG.1): the horizon table is reproducible.
  → `python -m qlong.horizon` writes `research_runs/_qlong/horizon.json`: per hardware tier (r2, r3, Nighthawk, early-FT, FT) the assumed qubits, two-qubit and readout error with a `source` field (`fake snapshot` | `published` | `roadmap`), and the derived budgets of §4.2 (RZZ per Trotter step on the native graph, proposal fidelity per depth, memory survival per sequence length, readout survival per width). For r2 it reproduces 176 couplers and 0.31 / 0.055 fidelity at 2 / 5 Trotter steps.
- [ ] **AC-2** (Q-LONG.2): the heterogeneity energy model exists with clones and phenotype.
  → `python -m qlong.hetero.energy --sites 6 --clones 4` builds a Potts-type energy on a heavy-hex-native patch: per site 2 clone bits + 1 phenotype bit; terms: same-clone neighbour coupling, clone-dependent phenotype bias, position-dependent bias (rim / core distance, vessel distance), and an optional fixed clone-fraction constraint. It writes the coefficient table and, for ≤ 20 qubits, the exact Boltzmann distribution with the list of "rare types" (modes below a stated mass). Every coefficient is a named parameter (mirrors `B_mapping/src/tumor_energy.py`).
- [ ] **AC-3** (Q-LONG.3): exact mixing comparison against the right adversaries.
  → `python -m qlong.hetero.gap --qubits 6,9,12 --T 0.5,1,2` computes the exact spectral gap of the Metropolis–Hastings chain for five proposals: quantum (Layden quench), local flip, uniform, clone-swap (Kawasaki, fraction-preserving), and **quantum-inspired** (the same quench simulated with truncated bond dimension χ = 2, 4, 8). It writes `gap.json` with fitted exponents and the label `simulated: ideal`. The output states whether the quantum proposal beats the quantum-inspired one at each χ.
- [ ] **AC-4** (Q-LONG.4): the chain is run with a noisy proposal and its correctness is checked.
  → `python -m qlong.hetero.chain --qubits 12 --noise heron|r3 --steps 4000` samples chains with the proposal drawn from `AerSimulator` under noise, reports proposal asymmetry, total-variation distance of the chain's empirical distribution to the exact Boltzmann distribution, integrated autocorrelation time of the rare-type indicator, and "rare types found per 1,000 steps" for quantum, local and clone-swap proposals. A chain whose TVD exceeds the shot-noise bound by 3σ is reported as `not exact under noise`.
- [ ] **AC-5** (Q-LONG.5): the coarse-grained route to tumour-sized lattices is sized.
  → `python -m qlong.hetero.coarse --sites 48 --block 4` runs the coarse-grained scheme (blocks of ≤ 12 qubits, the rest frozen) with an ideal block proposal against parallel tempering on the same energy, at equal numbers of energy evaluations. It reports autocorrelation per step and the break-even proposal rate (proposals per second) the QPU would need.
- [ ] **AC-6** (Q-LONG.6): a growth process with a large, provable memory gap is defined.
  → `python -m qlong.predict.process --family division-timer --resolution 2,4,8,16,32` builds the age-dependent division renewal process from E's doubling-time parameters at increasing time resolution, and writes C_μ, C_q, the classical state count, and the quantum memory dimension per resolution (reuses `dscale/causal_states.py`). Pass shape: C_μ grows with resolution while the quantum dimension stays ≤ 2 (one qubit) or ≤ 4 (two qubits).
- [ ] **AC-7** (Q-LONG.7): the score is "classical memory needed to match", not d_KL at equal memory.
  → `python -m qlong.predict.match --resolution 8 --L 8` computes, for the one-qubit and two-qubit quantum models, the smallest classical state count d\* whose best model (global optimisation, ≥ 24 restarts, `rigour: numerical`) reaches the quantum model's word distribution within the sampling floor at 20,000 shots. Output: d\*, the gap in probability of the most discriminating word, and that gap divided by the floor. A rung is usable only if the ratio is ≥ 10.
- [ ] **AC-8** (Q-LONG.8): a predictive model is learned from growth data, both ways.
  → `python -m qlong.predict.learn --source e-engine --train 2000 --test 500` takes binarised growth-event sequences exported from E's engine (grow / rest per interval; a new-clone event as a third symbol in a second run), fits (a) a classical d-state hidden Markov model and (b) a quantum model of equal memory dimension (Kraus parametrisation, NumPy/SciPy), and reports held-out log-loss for d = 2, 3, 4 with bootstrap error. Label: `simulated: ideal`. The file records whether (b) < (a) by 3σ; either outcome is a result.
- [ ] **AC-9** (Q-LONG.9): the predictive machine is simulated on hardware-shaped circuits.
  → `python -m qlong.predict.machine --L 10,30 --noise heron|r3` builds the deferred-measurement machine (memory qubit(s) + L output qubits on a path, no mid-circuit operation; mirrors `dscale/families/pmd_bank.machine_circuit`) for the AC-7 process and reports the discriminating-word probability ± σ against the d\*−1 classical bound. A `--dynamic` flag builds the measure-and-reset variant and is marked `horizon ≥ r3; not for r2` in the output.
- [ ] **AC-10** (Q-LONG.10): the three chemistry targets exist as active-space ladders with classical references.
  → `python -m qlong.chem.models --target phd2|p450|mn-agent` (PySCF) builds a cluster model from a geometry file in `code/qlong/chem/geometries/`, runs ROHF, selects a ladder of active spaces (smallest: the metal 3d shell; then + ligand donor orbitals; then + O₂ π\* for `phd2`), and writes per rung: (electrons, orbitals), qubits (2 × orbitals), CASCI energies of the lowest spin states, the spin gap, and an FCIDUMP file. Rungs above 16 orbitals record `classical reference: not computed here`.
- [ ] **AC-11** (Q-LONG.11): sample-based diagonalisation is simulated on the smallest rungs.
  → `python -m qlong.chem.sqd --target phd2 --rung 0,1 --noise ideal|heron` prepares LUCJ circuits (`ffsim`), samples them, runs configuration recovery and subspace diagonalisation (`qiskit-addon-sqd`), and reports the energy error against CASCI in kcal/mol, the spin-gap error, CZ count after heavy-hex layout, and subspace dimension. Label per CLAUDE.md. Pass shape: ≤ 1 kcal/mol on rung 0 with noise.
- [ ] **AC-12** (Q-LONG.12): the fault-tolerant cost is tabulated, not guessed.
  → `python -m qlong.chem.resources` writes `resources.json`: per target and rung the published logical-qubit / Toffoli / runtime figures transcribed from the cited papers (`rigour: published`, with paper and table), and, where no paper exists (PHD2, Gd, Mn), a scaling estimate from orbital count marked `rigour: rough, own`. It prints the hardware tier at which each rung first fits (§4.2).
- [ ] **AC-13** (Q-LONG.13): the chemistry is linked to layer E by a sensitivity number.
  → `python -m qlong.chem.link` reads `plans/relatedPapers/reverse-engineering/E_classical_growth/src/params_lung.json` (read-only) and writes, per target, the chain "energy error → rate factor at 310 K → E parameter → change in E's output (hypoxic / dormant shell thickness, kill fraction)". It states the energy accuracy each target needs before a quantum result could change E's output by more than its existing parameter uncertainty.
- [ ] **AC-14** (Q-LONG.14): one scorecard and packs, nothing submitted.
  → `python -m qlong.scorecard` merges all outputs into `research_runs/_qlong/scorecard.json` and `scorecard.md`: per rung the long shot, horizon, classical adversary, simulated margin, prior (§4.3 to §4.5), posterior (Q-HARD rule), verdict. `python -m qlong.pack --rung <id> --target <backend>` writes ISA circuits (QPY), shot plan, QPU-time estimate and analysis command for rungs with verdict `go`. The package contains no `QiskitRuntimeService` call. `code/qlong/RUNBOOK_QLONG.md` lists the Peter-only steps.
- [ ] **AC-15** (Q-LONG.15): docs.
  → `QuantumPhantoms/README.md` Progress row + changelog line; `code/README.md` section for `qlong`; a dossier stub for the chemistry targets in `code/qlong/chem/README.md` with the sources of every geometry.

---

## 3. Out of Scope (Postponed)

- **Any hardware submission** → Peter, from the packs. Never by Claude.
- **Rungs at horizon H2 and H3** (early and full fault tolerance) → documented with thresholds in §4, not simulated. Their only Part II artefact is the resource table (AC-12).
- **Wiring any long shot into the A→H chain** (B's rulebook draw replaced by an MCMC draw, D-5 driving E, chemistry parameters written into `params_lung.json`) → a later RE feature per letter, after the scorecard. Q-LONG reads E's parameters and never writes them.
- **Tick-clock, hand-off, sister-memory certificates** → Q-HARD (R1 to R3). Q-LONG LS2 uses the Q-HARD tick-clock result as its first rung and does not rebuild it.
- **Real patient data.** Growth sequences come from E's engine. Public longitudinal volumes (NLST nodule series) are a *planned link* (Q6), not used here.
- **Protein-scale QM/MM and molecular dynamics** → cluster models only. Embedding (DMET, LASSCF) is a documented rung, not built.
- **Relativistic 4f chemistry for Gd(III)** → resource estimate only (Q8).
- **Backend selection by name** → Peter's own refactor; `qlong.pack` takes `--target`.
- **A claim that any of this makes better images or more realistic tumours.** LS1 certifies a sampler, LS2 a process representation, LS3 a molecular parameter. None certifies the tumour.

---

## 4. Technical Decisions

### 4.1 What "achieved" means for a long shot

Each long shot has four rungs. The thesis owns rungs 1 and 2; rungs 3 and 4 are the road.

| Rung | Meaning | Evidence required | Ladder level |
|---|---|---|---|
| M (mechanism) | The quantum method does the stated job on a tumour-shaped model in ideal simulation | Exact or converged numbers against a named classical baseline | `simulated: ideal`, no level claim |
| H (hardware) | The same on a QPU, with correctness checked | Margin ≥ 3σ against the baseline, job id | L0 or L1′ sub-label, or "reproduces reference" |
| A (advantage) | It beats the **best known** classical method on a stated resource (steps, memory, accuracy) | The adversary of §4.3 to §4.5 fails at stated cost | L1′ (unconditional) or L2 (conjectured) |
| P (practical) | It changes an output of the pipeline that matters | Sensitivity analysis shows the pipeline output moves | none; engineering claim |

### 4.2 Hardware horizons and the budgets they give (computed 2026-11-10; r2 from the `FakeMarrakesh` snapshot, not a live calibration)

| Tier | Device | Qubits / graph | 2-qubit error / readout error | Source and status |
|---|---|---|---|---|
| H1a | Heron r2 (`ibm_marrakesh`) | 156, heavy-hex, 176 couplers | 3.3 × 10⁻³ / 9.5 × 10⁻³ | fake snapshot |
| H1b | Heron r3 (`ibm_boston`, `ibm_pittsburgh`) | 156, heavy-hex | ≈ 1.2 × 10⁻³ / 5.1 × 10⁻³ median; one report 2.15 × 10⁻³ across 100 qubits | published benchmarks (verify on live calibration) |
| H1c | Nighthawk | 120, square lattice, 218 couplers | not found; 5,000 gates now, 15,000 planned for 2028 | IBM announcements (verify) |
| H2 | Kookaburra, then Starling | logical module (2026 roadmap; no delivery announced as of October 2026); Starling 2029, ≈ 200 logical qubits, ≈ 10⁸ gates | logical | roadmap (verify) |
| H3 | Blue Jay class | ≈ 2,000 logical qubits, ≈ 10⁹ gates, 2033 | logical | roadmap (verify) |

Derived budgets:

| Quantity | r2 | r3 | at 5 × 10⁻⁴ | Used by |
|---|---|---|---|---|
| One Trotter step of a native-graph Ising / Potts energy on the full chip | 176 RZZ in 3 layers (bipartite, maximum degree 3) | same | same | LS1 |
| Fidelity of a full-chip proposal at 2 / 5 / 10 Trotter steps | 0.31 / 0.055 / 0.003 | 0.66 / 0.35 / 0.12 | 0.84 / 0.64 / 0.42 | LS1 |
| Readout survival at 30 / 60 / 100 qubits | 0.75 / 0.56 / 0.39 | 0.86 / 0.74 / 0.60 | – | LS1, LS3 |
| Memory survival after L = 10 / 30 / 100 / 300 steps at 3 CZ per step | 0.91 / 0.74 / 0.37 / 0.05 | 0.97 / 0.90 / 0.70 / 0.34 | 0.99 / 0.96 / 0.86 / 0.64 | LS2 |
| Break-even size against local Metropolis if the classical chain is 10³ / 10⁶ / 10⁹ times faster per step (Layden exponents 0.264 against 0.94) | n ≈ 15 / 30 / 44 spins | same | same | LS1 |
| Rate factor at 310 K per 0.3 / 1 / 3 kcal/mol energy error | 1.6 / 5.1 / 130 | – | – | LS3 |

Reading: (a) r3 turns a 5-step full-chip proposal from noise (0.055) into signal (0.35); (b) r3 keeps a one-qubit memory coherent for about 30 growth steps, 5 × 10⁻⁴ for about 100; (c) LS1's break-even against *local* Metropolis is only 30 to 44 spins, which is why the real question is the stronger classical adversaries; (d) LS3 needs ≤ 1 kcal/mol or its output is a factor 5 off in rate.

### 4.3 Long shot 1: heterogeneity sampling (B-5)

**Obstacles, in order of severity.**
1. **Dequantisation.** Christmann et al. show that an *unconverged* tensor-network simulation of Layden's proposal keeps the scaling advantage over classical samplers. The accept / reject step forgives an inaccurate proposal, so the classical simulation does not have to be good. On heavy-hex the Q-HARD budget says exact contraction costs 2^(4c) for c uses of each cut coupler: a 5-step proposal is 2²⁰.
2. **No generic speedup.** Orfi and Sels bound the gap for any unital proposal and find the speedup only for fine-tuned quenches into a non-ergodic regime. A tumour energy is structured (ferromagnetic clone domains, fields), not a spin glass; the Layden exponents need not transfer. Own evidence: no advantage at 6 spins, 1.5× at 8.
3. **Noise breaks exactness, not only speed.** The measured proposal asymmetry of 0.135 means detailed balance holds only approximately.
4. **Wall clock.** A QPU proposal costs milliseconds; a classical flip costs nanoseconds.
5. **The model.** Clones need a Potts variable (≥ 2 bits per site) plus phenotype; no published quantum-proposal study of a Potts model was found.

**Ladder.**

| # | Rung | What is shown | Hardware | Adversary | Sources | P |
|---|---|---|---|---|---|---|
| A1 | M: Potts clone × phenotype patch, exact gaps | Quantum proposal has a larger gap than local, uniform and clone-swap at ≥ 12 qubits; rare types found sooner | none | Metropolis variants | Layden 2203.12497; own RE result | **0.75** |
| A2 | M: against the quantum-inspired proposal | At which bond dimension χ the classical imitation matches the quantum gap | none | Tensor-network proposal | Christmann 2411.17821; Orfi–Sels 2403.03087, 2408.07881 | 0.9 that it is measured; **0.2** that quantum wins at χ ≤ 8 |
| A3 | H: correct sampler on hardware | Chain on 12 to 36 qubits converges to the exact / reference distribution; autocorrelation per step ≤ local Metropolis | r3 (r2 as stress test) | Local and clone-swap Metropolis | Layden (hardware at n ≤ 10, verify); Kawamata–Fujii 2611.05883 (Heron r2) | **0.55** on r3, 0.3 on r2 |
| A4 | H: exactness restored by a neural surrogate | A network trained on QPU samples gives a proposal with known probability, so Metropolis–Hastings is exact under any noise; fixed clone fractions (from bulk sequencing) as a Hamming-weight constraint | r2 / r3 | Kawasaki dynamics | Nakano 2305.08789, 2506.01335; Kawamata–Fujii 2611.05883 (N = 1,064; 5.2× and 12.3× faster autocorrelation decay per step than global / local Kawasaki) | **0.45** |
| A5 | H: tumour-sized lattice by coarse graining | 10² to 10³ sites sampled with ≤ 12-qubit blocks | r3 | Parallel tempering | Ferguson–Wallden 2405.04247 (36 spins with 6 simulated qubits) | 0.35 |
| A6 | A: proposal that classical simulation cannot imitate | Per-step advantage over the χ-limited imitation, at the Q-HARD threshold (≈ 2,000 to 2,900 CZ, ≤ 0.26 % loss) or on a square lattice | r3 at best hexagons, Nighthawk, later | Tensor networks, belief propagation | Q-HARD §4.2; quantum-annealing variant 2502.08060 | **0.10** by 2029 |
| A7 | A / P: fault-tolerant sampler | Quadratic speedup in the gap by a quantum walk on the chain, or a quantum Gibbs sampler | H2 to H3 | All classical chains | Szegedy 2004; Lemieux et al. 2020; Chen–Kastoryano–Gilyén 2023 (IDs not verified) | 0.15 by 2033 |

**Validation notes.**
- A1 is the thesis goal ("show the mechanism"). It already half-exists; what it lacks is clones, phenotype and the fraction-preserving baseline. The 6-spin null stays in the table.
- A2 decides what the thesis may say. If χ = 4 matches the quantum gap, the sentence is "the quantum circuit is a design tool for a classical sampler", which is still a result and is what Christmann et al. propose.
- A4 is the most promising hardware rung and it appeared this week (4 November 2026). Its constraint is biology-shaped: bulk sequencing fixes clone fractions, the unknown is the spatial arrangement. Before adoption, read the full paper: which energy, which baseline tuning, and whether the surrogate, not the QPU, carries the gain.
- A6 is where LS1 meets Q-HARD: a sampler advantage is an L2 claim about the proposal circuit. Same threshold, same probability class.
- Wall clock (obstacle 4) is reported at every rung as "break-even proposal rate", never hidden.

### 4.4 Long shot 2: predictive growth (D-5)

**Obstacles.**
1. **The statistic.** d_KL at equal memory rewards approximate classical models; the gap sat at the sampling floor. (Banchi et al. study exactly this accuracy-against-memory regime.)
2. **The process.** A weakly modulated division timer is nearly memoryless; the advantage needs strong, long-range temporal correlation.
3. **Hand-written model.** The quantum model was constructed from a known process. A predictor must be learned from sequences.
4. **Length.** Prediction "3 months ahead" is many steps; r2 holds a memory qubit for about 10.
5. **Value.** Memory is cheap classically. The advantage is in model dimension, not in time. "Quantum-inspired memory-enhanced stochastic algorithms" (1906.00263) shows some quantum protocols of this family can be imitated classically; every claim names the classical model class it excludes.

**Ladder.**

| # | Rung | What is shown | Hardware | Adversary | Sources | P |
|---|---|---|---|---|---|---|
| B1 | H: one qubit beats one bit on a growth-timing pattern | Tick-clock, p(001) > 8/27 | r2 | Any 2-state classical machine | Q-HARD R1 | 0.85 (Q-HARD) |
| B2 | M: a growth process with diverging classical memory | Age-dependent division timing at finer time resolution: C_μ grows, quantum memory stays one or two qubits | none | Exact classical minimal model | Gu 1102.1994; Elliott–Gu 1704.04231; Elliott et al. 1909.02817; Elliott 2105.06831 | **0.8** |
| B3 | M: score by "classical memory needed to match" | d\* ≥ 3 for a one-qubit model with a discriminating-word gap ≥ 10× floor | none | Best d-state hidden Markov model (numerical) | Banchi 2312.13473; Yang et al. 2404.10338 | **0.6** |
| B4 | M: model learned from growth sequences | A quantum model of dimension d has lower held-out log-loss than the best classical d-state model on E-generated sequences | none | Classical hidden Markov models of equal dimension | Yang et al. 2105.14434; Ho et al. 1911.02767; Sundar–Elliott 2601.16126 (compression of any ergodic HMM) | **0.4** |
| B5 | H: multi-step machine on hardware | B3's word gap survives at L = 10 to 30 | r3 | d\*−1 state machines | Wu 2208.12744 (photonic template); Ghafari 1905.06953 | **0.5** on r3, 0.15 on r2 |
| B6 | H: two-qubit memory, long sequences, measure-and-reset | L = 100 to 300 with a recycled output qubit | ≤ 5 × 10⁻⁴ error or logical qubits | 4-state machines | Binder et al. 1709.02375; Yang et al. 1803.08220; Elliott–Gu 2402.04708 | 0.25 by 2029 |
| B7 | A / P: forecasting with a time advantage | A superposition of futures (q-sample) plus amplitude estimation gives a quadratic saving in estimating "P(volume > threshold at 3 months)" | H2 to H3 | Classical Monte Carlo over trajectories | Blank et al. 2021 (ID not verified); Yang et al. 2404.10338; Korzekwa–Lostaglio 2005.02403 | 0.10 by 2033 |

**Validation notes.**
- B2 is biology-native: a cell's division hazard depends on its age, and a classical predictor must store the age at the chosen time resolution. Finer resolution means more states; the quantum model stores overlapping states. This is the process family the 2017 to 2021 theory papers analyse, so the C_μ / C_q values can be checked against published curves before any run.
- B3 changes the question from "how much better at equal memory" (gap 10⁻³) to "how much classical memory to tie" (an integer). The classical optimum is numerical, so it is marked `rigour: numerical` and supports a go, not a claim, until a bound is found. The 2025 preprint on identifiability and minimality bounds of quantum models (2509.03004) is the place to look for a proven bound.
- B4 is the first step that deserves the word "predictive". A null result (classical model of equal dimension ties) is likely for weakly correlated E output and is recorded as such; it would mean E's growth engine is too Markovian to need a quantum memory.
- B6 needs mid-circuit measurement and reset. Own evidence says these lose on r2; the rung is gated on r3 results, not planned for r2.
- B7 is the only rung with practical forecasting value and the only one that needs fault tolerance. It is the sentence for the 10-year slide, not for the thesis.

### 4.5 Long shot 3: quantum chemistry into layer E

**How each molecule enters E, and what accuracy it needs.**

| Target | Molecular quantity | E parameter it informs | Quantum case | Published quantum cost |
|---|---|---|---|---|
| Hypoxia sensor (HIF prolyl hydroxylase PHD2, Fe(II) + 2-oxoglutarate + O₂) | O₂ binding and activation energetics across spin states (S = 1, 2, 3 surfaces) | Oxygen level at which cells switch to the hypoxic programme → dormant / necrotic shell thickness, radiosensitivity | **Good, open.** Spin-state crossing at a non-heme iron site; classical studies use DFT and QM/MM (Domene et al. 2020; Wick et al. 2012; SyrB2 analogue, Rugg–Senn 2017). No multireference benchmark and no quantum resource estimate were found | none found (gap) |
| Drug metabolism (cytochrome P450, Compound I) | Spin gaps and barrier of the oxidising intermediate | Clearance → drug concentration at the tumour → kill term | **Best documented.** | Goings et al. 2202.01244: largest model ≈ 4.9 million physical qubits and 135 hours with two Toffoli factories (surface code, 0.1 % error); 500 thousand qubits and 25 hours at 0.001 %. Caesura et al. 2501.06165: ≥ 233× shorter runtime on an active-volume architecture. Kanasugi et al. 2603.22778: P450 active-site models in an early-fault-tolerant estimate |
| MR contrast (Gd(III), Mn(II) complexes) | Zero-field splitting, hyperfine coupling → electron-spin relaxation → relaxivity r₁ | Signal of an enhancing tumour in a future MR renderer (F, not E) | **Weak.** Half-filled shells (4f⁷, 3d⁵), weakly correlated ground state; CASSCF / NEVPT2 already treats 23 Mn(II) complexes (Dalton Trans. 2025); relaxivity also depends on classical water exchange and tumbling. Gd needs relativistic treatment | none found |

**Ladder.**

| # | Rung | What is shown | Hardware | Adversary | Sources | P |
|---|---|---|---|---|---|---|
| C1 | M: three active-space ladders with classical references | Cluster models, spin gaps, qubit counts per rung | none | – | Goings 2202.01244 (hierarchy from 5 singly occupied orbitals upward) | **0.85** (needs Q4, Q5) |
| C2 | M: sample-based diagonalisation in simulation | ≤ 1 kcal/mol against CASCI on rungs of 8 to 16 orbitals | none | CASCI | Robledo-Moreno et al. 2405.05068; Yu et al. 2501.09702; McFarthing et al. 2602.01165 (half the qubits) | **0.7** |
| C3 | H: the same on hardware | Fe(II) site, 16 to 40 qubits, spin gap within 1 to 3 kcal/mol of the reference | r3 | CASCI / DMRG (the reference wins; claim is "reproduces") | 2405.05068 ([2Fe–2S], [4Fe–4S], up to 77 qubits, verify); Shirakawa et al. 2511.00224; Liepuoniute et al. 2411.04827 (open shell); QC Ware–IonQ P450nor on 8 qubits (press, 2026) | **0.35** |
| C4 | H: embedding to the protein environment | Fragment solver inside LASSCF or DMET with the enzyme pocket | r3 + classical cluster | Classical fragment solvers | Wang et al. 2512.14936; Evenseth et al. 2604.10487; Li et al. 2401.03759 | 0.2 by 2029 |
| C5 | A: early fault tolerance | Phase estimation on a 25 to 100 logical-qubit active space where DMRG does not converge | Starling class | DMRG, coupled cluster | Kanasugi et al. 2603.22778; perspective 2506.19337 | 0.2 by 2031 |
| C6 | A / P: chemically decisive P450 or PHD2 number | Barrier or spin gap to 1 kcal/mol on a ≥ 50-orbital model, changing an E parameter | Blue Jay class | All classical methods | Goings 2202.01244; Caesura 2501.06165; Lee et al. 2011.03494; symmetry-compressed double factorization 2403.03502 | 0.2 by 2035 |
| C7 | Gd / Mn contrast | Resource estimate; Mn(II) (5e, 5o) toy on 10 qubits | none / r3 | CASSCF / NEVPT2 (already adequate) | Dalton Trans. 2025 (d5dt01381j) | 0.05 that quantum computing adds value before 2035 |

**Validation notes.**
- **No hardware rung of LS3 is an advantage claim.** Sample-based diagonalisation is a classical diagonalisation in a subspace the QPU proposes; the 2026 review (Bonilla Vargas, 2608.05314) maps its classical-simulability frontier, and DMRG remains the benchmark for iron–sulfur clusters. The honest sentence for C3 is "the quantum processor reproduces the classical reference for a tumour-relevant iron site at n qubits".
- **The thesis-sized novelty is PHD2.** P450 has been costed by Google and by PsiQuantum; the hypoxia sensor has not. A cluster model, a classical multireference ladder and a first resource estimate (C1 + AC-12) would be new, with no hardware at all. The search was limited, so "none found" must be re-checked before it is written as "first".
- **Accuracy is the gate.** 1 kcal/mol is a factor 5 in rate at body temperature; 3 kcal/mol is a factor 130. Active-space energies without dynamic correlation miss by more than that, so C3 results cannot be fed into E. AC-13 exists to say this with a number.
- **Geometry provenance.** Every cluster model needs a citable structure (PDB entry or a paper's supplementary coordinates). Q5.
- **Fe(II) high-spin circuits** need open-shell LUCJ; the methylene study is the published template. Rung 0 (five 3d orbitals, 10 qubits) is a wiring check, not chemistry.

### 4.6 Combined view

| Long shot | Thesis rung (M) | Hardware rung on r3 (H) | Advantage (A) | Practical (P) | Binding constraint |
|---|---|---|---|---|---|
| LS1 heterogeneity | 0.75 | 0.55 | 0.10 by 2029 | 0.10 by 2031 | Classical imitation of the proposal; needs L2-grade circuits |
| LS2 predictive growth | 0.6 to 0.8 | 0.5 (0.85 for the Q-HARD certificate on r2) | 0.25 by 2029 (unconditional, memory) | 0.05 by 2036 | Memory is cheap classically; value needs B7 |
| LS3 chemistry | 0.85 | 0.35 | 0.2 by 2031 | 0.2 by 2035 | Fault tolerance at 10⁸ to 10⁹ gates; accuracy 1 kcal/mol |

All three thesis rungs together (treated as independent): ≈ 0.4 to 0.5. At least one hardware rung on r3: ≈ 0.85. All three advantage rungs by 2031: < 0.01. The long shots are sequential in hardware: LS2 first (works at 10 to 100 gates), LS1 second (10³ gates), LS3 last (10⁸ gates).

### 4.7 Stack choices for Part II

| Component | Choice / Implementation |
|---|---|
| Package | New `code/qlong/` with sub-packages `hetero`, `predict`, `chem`; simulation-only; never imported by the live path |
| Reuse (LS1) | Port `spins`, `energies`, `quantum_Q`, `local_Q`, `uniform_Q`, `mh_matrix`, `spectral_gap`, `asymmetry`, `trotter_circuit` from `plans/relatedPapers/reverse-engineering/B_mapping/src/qemcmc.py` (copy, recorded in `code/qlong/PORTED.md`, as `code/dscale/PORTED.md` does; the RE tree is not imported) |
| Reuse (LS2) | `code/dscale/causal_states.py` (`renewal_machine`, `classical_complexity`, `wu_model`, `kraus_unitary`, `exact_words`, `best_classical_fixed_memory`), `code/dscale/families/pmd_bank.py` (`machine_circuit`) |
| Noise | `heron` = `AerSimulator.from_backend(FakeMarrakesh)`; `r3` = the same model with two-qubit and readout errors scaled to the H1b row (labelled `simulated: Heron-class noise (FakeMarrakesh), errors scaled to r3`, never "r3 simulated") |
| Quantum-inspired proposal (AC-3) | Own truncated matrix-product-state evolution in NumPy for ≤ 14 qubits (no `quimb`) |
| Classical baselines | Local flip, uniform, clone-swap (Kawasaki), parallel tempering (LS1); Baum–Welch plus global restarts (LS2); CASCI via PySCF (LS3) |
| Chemistry | `pyscf` (integrals, ROHF, CASCI), `ffsim` (LUCJ), `qiskit-addon-sqd` (recovery, diagonalisation) (Q4) |
| Statistics | k = 3σ for go / no-go; first-run caps 4,000 shots, ≤ 15 repeats; LS2 additionally gap ≥ 10× sampling floor |

**Conventions & Notes:**
* Every output carries the long shot, rung id, horizon, classical adversary, `rigour: proven | numerical | published | rough`, and the CLAUDE.md label.
* A rung is `go` only against its *strongest listed* adversary. LS1 rungs report the quantum-inspired comparison even when it loses.
* Null results are rows, not omissions (6-spin QeMCMC, `pmd-bank`, any tie in AC-8).
* `Deadline` from `code/dscale/budget.py` caps every CLI at 20 minutes; larger ladders go into the runbook.
* No mid-circuit measurement, reset or feed-forward in any r2 circuit (D-SCALE lint rule 1). The `--dynamic` variant of AC-9 is built but never packed for r2.
* Siemens wording: "quantum computing", "quantum-ready"; LS3 says "planned link to Varian / Siemens MR use cases", never "used by".

---

## 5. Data Model (Additions/Modifications)

```text
[New File] research_runs/_qlong/horizon.json
  tiers: [{id, device, qubits, graph, e2q, e_readout, source, status}]
  budgets: {rzz_per_step, proposal_fidelity[tier][steps], readout_survival[tier][n],
            memory_survival[tier][L], breakeven_spins[rate_ratio], rate_factor[kcal]}

[New File] research_runs/_qlong/hetero_energy_<sites>x<clones>.json
  sites, clones, qubits, params {J_clone, h_pheno[clone], h_rim, h_vessel, fraction_constraint}
  graph (edges), boltzmann (<= 20 qubits), rare_types: [{bitstring, mass}]

[New File] research_runs/_qlong/hetero_gap.json
  rows: [{qubits, T, proposal ("quantum"|"local"|"uniform"|"clone-swap"|"qi-chi<k>"), gap}]
  fits: [{proposal, exponent, stderr}], quantum_beats_qi: {chi: bool}, label

[New File] research_runs/_qlong/hetero_chain_<n>_<noise>.json
  proposal, steps, asymmetry, tvd_to_exact, tvd_floor, exact_under_noise (bool)
  tau_int, rare_found_per_1000, label

[New File] research_runs/_qlong/hetero_coarse.json
  sites, block, tau_int {cg, parallel_tempering}, breakeven_proposals_per_second

[New File] research_runs/_qlong/predict_process.json
  family, rows: [{resolution, n_causal_states, C_mu, C_q, quantum_dim}]

[New File] research_runs/_qlong/predict_match.json
  resolution, L, quantum_dim, d_star, word, gap, floor, gap_over_floor, rigour

[New File] research_runs/_qlong/predict_learn.json
  source, symbols, train, test, rows: [{d, logloss_classical, logloss_quantum, diff, sigma}]

[New File] research_runs/_qlong/predict_machine_<L>_<noise>.json
  circuit {qubits, cz, depth_2q, dynamic}, p_word, sigma, classical_bound, margin_sigma, verdict, label

[New File] research_runs/_qlong/chem_<target>.json
  target, geometry_source, basis, rungs: [{id, electrons, orbitals, qubits,
    casci {S: energy}, spin_gap_kcal, fcidump, classical_reference}]

[New File] research_runs/_qlong/chem_sqd_<target>_<rung>_<noise>.json
  energy_error_kcal, spin_gap_error_kcal, cz, subspace_dim, shots, label, verdict

[New File] research_runs/_qlong/resources.json
  rows: [{target, rung, logical_qubits, toffoli, runtime_h, physical_qubits, rigour, paper, table, first_tier}]

[New File] research_runs/_qlong/chem_link.json
  rows: [{target, e_parameter, kcal_error, rate_factor, e_output, delta, needed_accuracy_kcal}]

[New File] research_runs/_qlong/scorecard.json  (+ scorecard.md)
  rungs: [{id, long_shot, rung_type ("M"|"H"|"A"|"P"), horizon, adversary, prior, posterior, verdict, ref}]

[New Dir]  research_runs/_qlong/pack_<rung>/            (only for verdict == "go")
  circuits.qpy, plan.json {target, layout, shots, est_qpu_seconds}, ANALYSE.md
```

No existing entity changes. `research_runs/_qlong/` follows the `_dscale/` and `_qhard/` convention. No RE contract is touched.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `code/qlong/__init__.py` | Package marker, rung registry (id, long shot, rung type, horizon, prior from §4.3 to §4.5) |
| New | `code/qlong/horizon.py` | AC-1: tier table, derived budgets from `FakeMarrakesh` coupling map |
| New | `code/qlong/noise.py` | `heron` and `r3`-scaled noise models; label strings |
| New | `code/qlong/PORTED.md` | What was copied from `B_mapping/src/qemcmc.py` and why |
| New | `code/qlong/hetero/__init__.py` | Sub-package marker |
| New | `code/qlong/hetero/energy.py` | AC-2: Potts clone × phenotype × position energy on a heavy-hex patch; mirrors `B_mapping/src/tumor_energy.py` (named parameters) |
| New | `code/qlong/hetero/proposals.py` | Ported quantum / local / uniform proposals + clone-swap + truncated-MPS quantum-inspired proposal |
| New | `code/qlong/hetero/gap.py` | AC-3: exact gaps, exponent fits |
| New | `code/qlong/hetero/chain.py` | AC-4: sampled chains with noisy proposals, asymmetry, TVD, autocorrelation, rare-type recall |
| New | `code/qlong/hetero/coarse.py` | AC-5: coarse-grained blocks against parallel tempering |
| New | `code/qlong/predict/__init__.py` | Sub-package marker |
| New | `code/qlong/predict/process.py` | AC-6: division-timer family per resolution; calls `dscale.causal_states` |
| New | `code/qlong/predict/match.py` | AC-7: d\* search, discriminating word, gap over floor |
| New | `code/qlong/predict/learn.py` | AC-8: classical HMM and quantum Kraus model fits, held-out log-loss |
| New | `code/qlong/predict/export_e.py` | Reads a `growth_trajectory` file produced by E and binarises it into event sequences (file exchange only; no import of the RE tree) |
| New | `code/qlong/predict/machine.py` | AC-9: deferred machine and `--dynamic` variant; mirrors `code/dscale/families/pmd_bank.py` |
| New | `code/qlong/chem/__init__.py` | Sub-package marker |
| New | `code/qlong/chem/models.py` | AC-10: cluster model → ROHF → active-space ladder → CASCI, FCIDUMP |
| New | `code/qlong/chem/geometries/phd2.xyz`, `p450_cpd1.xyz`, `mn_agent.xyz` | Cluster coordinates with source in the header comment (Q5) |
| New | `code/qlong/chem/sqd.py` | AC-11: LUCJ sampling, recovery, subspace diagonalisation |
| New | `code/qlong/chem/resources.py` | AC-12: transcribed published costs + rough own scaling, first fitting tier |
| New | `code/qlong/chem/link.py` | AC-13: energy error → rate → E parameter sensitivity (reads `params_lung.json`) |
| New | `code/qlong/chem/README.md` | Chemistry dossier: targets, geometry provenance, what is and is not claimed |
| New | `code/qlong/scorecard.py` | AC-14: merge, posterior rule (Q-HARD §4.5), `scorecard.md` |
| New | `code/qlong/pack.py` | AC-14: ISA circuits + shot plan; mirrors `code/dscale/hw_pack.py`; no runtime service |
| New | `code/qlong/RUNBOOK_QLONG.md` | Peter-only hardware steps; ladders beyond the smoke cap |
| Modify | `QuantumPhantoms/requirements.txt` | Add pinned `pyscf`, `ffsim`, `qiskit-addon-sqd` (only after Q4) |
| Modify | `code/README.md` | Section for `qlong` |
| Modify | `QuantumPhantoms/README.md` | Progress row + changelog |
| Modify (developer) | `plans/epic-quantum-phantoms-mvp.md` | Row from §9 |

---

## 7. Manual Verification (No Tests)

All from `code/`, simulators only.

- [ ] **Verify AC-1:** `python -m qlong.horizon` prints 176 couplers, proposal fidelity 0.31 / 0.055 (r2) and 0.66 / 0.35 (r3) at 2 / 5 steps, break-even 29.5 spins at rate ratio 10⁶.
- [ ] **Verify AC-2:** `python -m qlong.hetero.energy --sites 4 --clones 4` prints 12 qubits, a coefficient table, and a Boltzmann distribution summing to 1 with at least one listed rare type; with `--fix-fractions` only fraction-preserving states carry mass.
- [ ] **Verify AC-3:** `python -m qlong.hetero.gap --qubits 6,9` reproduces the ordering of the RE table at the binary limit (`--clones 2`, no phenotype: quantum ≈ local at 6) and prints the χ at which the quantum-inspired gap reaches 90 % of the quantum gap.
- [ ] **Verify AC-4:** `python -m qlong.hetero.chain --qubits 12 --noise ideal` gives TVD inside the floor for all proposals; `--noise heron` prints an asymmetry > 0 and the `exact_under_noise` verdict.
- [ ] **Verify AC-5:** `python -m qlong.hetero.coarse --sites 24 --block 4` prints two autocorrelation times and a break-even proposal rate in proposals per second.
- [ ] **Verify AC-6:** `python -m qlong.predict.process --family division-timer --resolution 2,4,8` prints a rising state count and C_μ and a quantum dimension that does not rise; `--family perturbed-coin` reproduces C_q = 0.4690 at p = 0.2 (the RE analytic check).
- [ ] **Verify AC-7:** `python -m qlong.predict.match --resolution 8 --L 8` prints d\*, the word, the gap and the ratio to the floor; rerunning with another seed changes the classical optimum by less than the floor (otherwise the restart count is too low and is raised).
- [ ] **Verify AC-8:** `python -m qlong.predict.learn --source synthetic-coin` (a process with known quantum advantage) shows quantum log-loss below classical at d = 2; `--source e-engine` prints the table whichever way it goes.
- [ ] **Verify AC-9:** `python -m qlong.predict.machine --L 10 --noise ideal` matches the AC-7 word probability; `--noise heron` and `--noise r3` print margins; the printed circuit has no mid-circuit operation unless `--dynamic`.
- [ ] **Verify AC-10:** `python -m qlong.chem.models --target phd2` prints a ladder whose rung 0 is (6e, 5o) or the documented equivalent for high-spin Fe(II), 10 qubits, with a quintet ground state; the geometry source is printed.
- [ ] **Verify AC-11:** `python -m qlong.chem.sqd --target phd2 --rung 0 --noise ideal` returns an energy error < 0.1 kcal/mol; `--noise heron` prints the error and CZ count.
- [ ] **Verify AC-12:** `resources.json` contains the Goings and Caesura rows with paper and table fields filled, and PHD2 / Gd / Mn rows marked `rough, own`.
- [ ] **Verify AC-13:** `python -m qlong.chem.link` prints 5.1 as the rate factor for 1 kcal/mol and a needed-accuracy value per target; `git status` shows `params_lung.json` unchanged.
- [ ] **Verify AC-14:** `scorecard.md` lists every rung of §4.3 to §4.5 with prior, posterior and verdict; `grep -rn "QiskitRuntimeService" code/qlong` returns nothing.
- [ ] **Verify AC-15:** README rows exist; every command finishes inside 20 minutes.

---

## 8. Open Questions

- [ ] **Q1:** Feature ID and epic row. *Proposed:* `Q-LONG`; the developer adds the row (§9).
- [ ] **Q2:** One plan or three? *Proposed:* one desk study (this file), but Part II may be implemented in three passes in the order LS2 → LS1 → LS3 (cheapest hardware first; LS3 blocked on Q4 and Q5).
- [ ] **Q3:** Which hardware may the plan assume for packs? *Proposed:* simulate r2 and r3-scaled noise; write packs for whichever backend Peter names. If only r2 is accessible, rungs A3 and B5 are packed for r2 as stress tests with their lower probabilities stated.
- [ ] **Q4:** New dependencies `pyscf`, `ffsim`, `qiskit-addon-sqd` (LS3 only). *Proposed:* yes, pinned, installed by Peter; without them LS3 shrinks to AC-12 and AC-13 (tables only).
- [ ] **Q5:** Source of the three cluster geometries. *Proposed:* P450 Compound I from the Goings et al. supplementary coordinates; PHD2 from a published crystal structure of the Fe(II)·2OG·substrate complex, cut to the first coordination shell (2 His, 1 Asp, 2-oxoglutarate, O₂) and capped; Mn agent from the 2025 Dalton Transactions set. Peter confirms the entries; nothing is downloaded by Claude without that.
- [ ] **Q6:** Growth data for B4. *Proposed:* E-engine sequences now; NLST longitudinal nodule volumes as a "planned link" in the runbook, used only if Peter obtains access.
- [ ] **Q7:** How many clones and which phenotype? *Proposed:* 4 clones (2 bits) and one binary phenotype (fast / slow growth) per site, so 3 qubits per site and 12 sites on 36 qubits.
- [ ] **Q8:** Demote Gd / Mn contrast to a resource estimate plus a 10-qubit Mn(II) toy? *Proposed:* yes. It is the weakest quantum case and belongs to the MR renderer (F), not E. It stays in the pitch as "planned link to MR", with the honest sentence that classical chemistry is adequate there today.
- [ ] **Q9:** Is "classical memory needed to match" (B3) an acceptable L1′ score next to Q-HARD's sub-labels? *Proposed:* yes, as L1′-S with the adversary written out, and only `numerical` until a proven bound is found.
- [ ] **Q10:** Should LS1 adopt the neural-surrogate route (A4) as its hardware rung instead of the bare Layden chain (A3)? *Proposed:* simulate both in Part II is too much; do A3 in Part II and read 2611.05883 in full first, then decide A4 as a follow-up feature.
- [ ] **Q11:** Is PHD2 confirmed as the hypoxia target? Other Fe(II) oxygen sensors exist (FIH). *Proposed:* PHD2 only.
- [ ] **Q12:** May the thesis text say "first quantum resource estimate for the HIF hydroxylase"? *Proposed:* not until a dedicated literature check; this plan's search was a handful of queries.

---

## 9. Post-Implementation Notes

**Edits for the developer (not made by this plan):**
- Epic §2 row: `| Q-LONG | Road to the three long shots | Horizon table, three rung ladders (LS1 heterogeneity sampling, LS2 predictive growth, LS3 chemistry into E), simulation scorecard, hardware packs | open | Exploration. Sim only. Thesis owns the mechanism rungs; advantage rungs are gated on L2-grade circuits (LS1), ≤ 5 × 10⁻⁴ error (LS2) and fault tolerance (LS3). Plan: feature-QLONG-long-shots-heterogeneity-predictive-growth-chemistry.md. |`
- `plans/relatedPapers/analysis-stages-B-D-F.md` B-5: add the quantum-inspired adversary (Christmann et al.) and the Orfi–Sels bound to the claim line.
- CLAUDE.md honesty gates: consider one line, "A quantum-proposal sampler is compared with its tensor-network imitation, not only with Metropolis."

**Sources checked while drafting (2026-11-10).**
- Title and authors confirmed through the arXiv API or the arXiv abstract page: 2011.03494, 1602.05683, 2604.10487, 2405.05068, 2608.05314, 2401.03759, 1803.05426, 1905.06953, 2202.01244, 2501.06165, 2005.02403, 2411.04827, 2602.01165, 2511.00224, 2501.09702, 2611.05883, 2603.22778, 2506.19337, 2601.16126, 2411.17821, 2512.14936, 2404.10338.
- Seen with matching title in search results only (the arXiv API rate-limited the batch): 2203.12497, 2405.04247, 2403.03087, 2408.07881, 2305.08789, 2506.01335, 2502.08060, 1909.02817, 2105.06831, 2312.13473, 2105.06448, 1704.04231, 1906.00263, 2402.04708, 2509.03004, 1911.02767, 2403.03502, 2105.14434.
- **Not verified:** 1102.1994 (Gu 2012), 1709.02375 (Binder), 1803.08220 (Yang, matrix product states), 2208.12744 (taken from the local analysis document); Szegedy 2004, Lemieux 2020, Chen–Kastoryano–Gilyén 2023, Blank 2021 (no IDs checked); Layden's hardware size; qubit counts and active spaces of 2405.05068; Starling and Blue Jay figures; Nighthawk error rates; Kookaburra status after October 2026; the QC Ware–IonQ result (press release only); the P450 logical-qubit count (one secondary source gives ≈ 4,900 logical qubits, the paper text read here gives 4.9 million *physical* qubits; transcribe from the paper's table in AC-12).
- Full texts were not read except parts of 2202.01244. Every number quoted from an abstract or a search summary is to be re-read in the paper before it enters the thesis.

[Implementation notes filled after implementation.]
