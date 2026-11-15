# Own paper, concept draft: how far are quantum models of evolution from beating a classical computer?

**Status:** exploration draft, 2026-11-08. The focus is open to change. **The paper framing in §8 is superseded by
`history-and-roadmap.md` §7 (v2: the hype audit and the road to advantage).** §§3–6 here still hold.
**Author of the work:** Peter Jas. **Drafted with:** Claude (Opus 5.5).
**Sources read:** `QuantumLife/` (README, research conclusions, thesis assessment), `artificial-life/` (study framing,
Month-4 conclusion, PJ0/PJ2 conclusions, PJ runlog, epic, P3 move menu, `code/qalife.py` witness code),
`QuantumPhantoms/` (README, CLAUDE.md, claim ladder in `analysis-stages-B-D-F.md`, `future.md`, publication plan,
D-SCALE runbook and the live run `research_runs/dscale_live_100_20261031-170957`).

Purpose: one paper that is clearly Peter's own (ideas, method, hardware data), written **before** the Siemens work
starts, so that the framework is timestamped under his name. Siemens material (CT, cohorts, pitch) stays out of it,
or appears only as one outlook paragraph.

---

## 1. The three projects, one paragraph each

The order is QuantumLife (summer 2026), then artificial-life (Aug to Oct 2026), then QuantumPhantoms (Oct 2026 to
now). Each project inherited the honest negatives of the one before it.

### 1.1 QuantumLife ("Quantum Tree")

A 108-qubit "genome" (18 slots × 6 bits) is run on IBM Heron r2 once per generation, and its measured bits decide
how a tree branches; a feedback rule (belief reinforced toward the measured frequencies) turns repeated sampling
into inherited, directed growth. The research fork asked whether the entangling chain leaves a spatial correlation
C(d) that a classical no-entanglement surrogate cannot reproduce. The answer was yes at z ≈ 10 against both the
surrogate and a no-entangler hardware control, with a causal dose response (the sign flips at 2 layers). The
caveat is that ~800 logical depth confounds it with crosstalk. A teleported long-range bond then gave a stable,
correctly signed correlation at distance 12 on `ibm_marrakesh`, where the SWAP ladder washed out; a later Heron-r2
re-test refuted teleport routing.

**Deliverables:**
- `code/qtree.py`, `genome.py`, `layout.py` (the SWAP-free low-error chain picker, reused in every later project);
- `research_qtree*.py` (C(d)/ξ metric; serial, brick-wall, teleport and SWAP arms; `sim_ideal_sign.py`);
- the web viewers (line art, pixel grove);
- `research/CONCLUSION_ENTANGLEMENT_CORRELATION.md`, `conclusion_teleportation_longrange.md`, and the
  teleport-crossover thesis assessment.

The brick-wall A/B that would separate entanglement from depth is coded, but I found no conclusion that records
its result.

### 1.2 artificial-life (QALife)

This project is a faithful, operator-by-operator rebuild of Alvarez-Rodriguez et al. 2018 (*Quantum artificial life
in an IBM quantum computer*): replication, mutation, death and interaction. The quantum claim moved off the diagonal
once Months 1–3 showed that the clone correlation C(g) has an exact classical surrogate. The project then scaled the
genealogy to W = 24 (48 qubits) on `ibm_kingston` and located the collapse that faithful dissipative death causes
(W* = 9, 5 generations). It traced that collapse to one gate, the soma-to-germ `cx(g,p)`, and fixed it with a germ/soma
split (the Weismann barrier) that keeps the signal above its null at 3σ through W = 50 (100 qubits). There, the chip
layout stopped the run, not decoherence. Later builds added a two-organism collision (42 q) and a motile organism
with metabolism, selection, reproduction and unitary death. On `ibm_marrakesh` its two-basis certificate gave
⟨XX⟩+⟨ZZ⟩ ≈ 1.96 (bound 1).

**Deliverables:**
- `code/qalife.py` (frozen 2018 reproduction), `pj_qalife.py` + `pj_run_qalife.py` (germ/soma, arena), and
  `1D_alive.py` / `2D_alive.py` (vivaria);
- `analysis/` renderers and the web pages (`index`, `spectacle`, three conclusion pages);
- the 2×2 ablation;
- `plans/how_is_this_study.md` (the informatics-thesis framing), the Darwinian-richness epic, and the P3 move
  menu (competition, error mitigation).

### 1.3 QuantumPhantoms

This is a training-free synthetic lung-CT pipeline. Tumours are placed by anatomy (A), drawn from published
statistics through a circuit (B), certified by a Bell test (C), given a quantum growth layer (D), grown classically
(E), rendered into real CT with the host scanner's blur and noise (F), recorded (G) and validated (H). It has two
codebases: a reverse-engineering pipeline that rebuilds 21 published methods behind frozen file contracts, with
honest non-matches recorded, and an MVP that runs quantum roll → Siemens-scanner LIDC host → grown, rendered tiles
→ web page. D-SCALE adds 40/100/120-qubit circuit families and a "survive vs simulable" map. The first live
hardware run gave CHSH S = 2.733 (L0), a marginal QCA pair-negativity witness (L1, Bonferroni p ≈ 0.046), a failed
28-qubit GHZ fidelity test (F = 0.055, needs > 0.5) and no L1′ memory gap. The Goldilocks zone (alive **and**
belief-propagation-hard) is empty in every map computed so far; those maps are smoke runs and truncated.

**Deliverables:**
- RE letters A–H + INT (contracts, dossiers, reproduction numbers, chain probe);
- MVP `code/` (F1 roll, `imaging/`, F3 web, F4 QALife arm, F5 realism, `dscale/`);
- the claim ladder L0/L1/L1′/L2/L3 and the honesty gates;
- the 3-paper publication plan, Siemens fit analysis and 5/10/15-year forecast.

The A→H chain is not closed; n = 1 host.

---

## 2. What the body of work delivers (evaluation)

**Real, ownable assets:**

1. **A claim ladder for "quantum" in biology-shaped models** (L0 provenance, L1 entangled generative state, L1′
   memory advantage, L2 classical hardness, L3 computational advantage), with the rule that every number carries
   its level, classical baseline, simulability number and sim/hardware label. I have not seen this discipline
   written down for quantum artificial life or quantum tumour models. It is Peter's.
2. **A hardware design rule with a causal ablation:** isolate the mortal or measured subsystem from the coherent
   register. The germ/soma 2×2 gives 0.90 vs 0.12 (separable vs entangled phenotype). This holds as a *relative*
   result whatever the witness class (see §3.3).
3. **A record of honest negatives that generalise:**
   - diagonal observables of these circuits have exact classical surrogates;
   - coherent depth advantage inverts on Heron r2 (readout ≫ 2q error);
   - teleport routing was refuted twice;
   - D-5 memory gap below the sampling floor;
   - the Goldilocks zone empty in every map so far (smoke runs, truncated).
4. **Infrastructure:** calibration-aware chain layout, a survive-vs-simulable mapper with belief propagation (BP)
   attached, and a Pauli-twirled noise model.

**Gaps:**

- Nothing is above L1 anywhere.
- Nearly everything is N = 1 per configuration.
- The one point near L2 (QCA, non-Clifford) is a marginal pair witness with no biological meaning.
- **One finding changes the paper's L1 claim; see §3.3.**

**Verdict on "is there a point":** yes, but not the point the projects started from.
- **Not the point:** a "quantum organism" that simulates tumour evolution better than a classical computer. There
  are structural reasons why faithful evolution circuits tend to be classically easy (§4).
- **The point:**
  - a measured, reproducible frontier map of where biology-shaped quantum states survive and where they become
    hard, plus the design rules that move that frontier;
  - an explicit argument for where a real advantage for medication prediction can and cannot come from (§6).

That combination is publishable, it is new as a framework, and nobody else has the hardware record behind it.

---

## 3. The witness: what it is and why everything hangs on it

### 3.1 Definition

An **entanglement witness** is an observable 𝒲 whose expectation value is bounded for every separable (classically
correlated) state, for example Tr(𝒲ρ) ≥ 0 for all separable ρ. A measured violation proves entanglement without full
tomography. A Bell inequality (CHSH, bound 2) is the device-independent version: it assumes nothing about the
device.

### 3.2 Why it is the gate

1. **It is the only part of these experiments a classical sampler cannot fake.** Any Z-basis distribution can be
   reproduced by a classical sampler fed the same probabilities, and every *biological* readout (cell counts,
   lineage sizes, survival curves, tumour size) is Z-basis. Without a passed witness, "quantum" in the paper is a
   random-number source.
2. **Entanglement is necessary for hardness.** Pure-state quantum circuits with bounded multipartite entanglement
   are efficiently simulable (Jozsa & Linden 2003), and low-entanglement states are cheap as matrix product states.
   No witness means no L2, for certain.
3. **Entanglement is not sufficient.** GHZ states are maximally entangled and still stabilizer states, so they are
   classically trivial (Gottesman–Knill; D-SCALE's ghz-spine has BP χ = 2). A passed witness is the entry ticket,
   not the claim. Hardness needs a second axis (§5).

### 3.3 The finding: the W = 24 / W = 50 headline is not yet an entanglement certificate

`artificial-life/code/qalife.py:212–241` compares joint = ⟨∏ xᵢ⟩ (X basis) against separable = ∏⟨xᵢ⟩ and calls the
difference the entanglement signal.

- **What this excludes:** the specific measure-and-resend surrogate (a classical Z-copy gives ⟨X^⊗n⟩ ≈ 0).
- **What it does not exclude:** the separable mixture ½(|+…+⟩⟨+…+| + |−…−⟩⟨−…−|), which gives ⟨X^⊗n⟩ = 1 for even
  n while every ⟨Xᵢ⟩ = 0. A classically correlated state saturates the test.
- **The established result:** "connected n-point X-correlation beyond the measure-and-resend surrogate", not
  "entanglement to 100 qubits". `how_is_this_study.md` §7.1 already suspected this; this note makes it concrete.

**The fix is cheap and uses the same two measurement settings as `--certify ghz2`.** The Tóth–Gühne
two-setting GHZ witness (PRL 94, 060501, 2005) needs only the X^⊗n basis and the Z^⊗n basis. It certifies
**genuine multipartite entanglement (GME)** of the whole germ register.

The ladder of witnesses the paper should use, weakest to strongest:

| Rung | Test | Excludes | Where the projects stand |
|---|---|---|---|
| W-a | Connected correlation vs a chosen surrogate (C(d), ⟨X^⊗n⟩ − ∏⟨Xᵢ⟩) | that surrogate only | QuantumTree z ≈ 10; QALife W = 24, W = 50 |
| W-b | Pairwise witness (⟨XX⟩+⟨ZZ⟩ ≤ 1, pair negativity) | separable pairs | motile ghz2 1.96 (2 q); QCA negativity, 23 sites, marginal |
| W-c | n-qubit GME (Tóth–Gühne, GHZ fidelity F > ½), entanglement depth k from fidelity bounds | all biseparable states | **one test, failed:** 28-q ghz-spine F = 0.055 |
| W-d | Bell / CHSH (S > 2) | any local hidden variable model | S = 2.733 on `ibm_marrakesh` (2 q, one job) |

**Prediction to test first (experiment E1):** the GME width of the germ/soma register is far below 50,
plausibly 10–30. The 28-q spine failed, and published IBM GHZ work needed dedicated layouts and error detection to
pass at 100+ qubits (verify the current record). That number, honestly measured, is the real L1 width of quantum
artificial life on Heron. It is a stronger paper result than an unqualified 100.

---

## 4. The faithfulness–hardness tension (the paper's central idea)

The three projects keep hitting the same wall from different sides. Stated as one claim:

> **The more faithfully a circuit implements classical evolutionary biology, the more classically simulable it
> becomes.**

There are three structural reasons, each visible in the existing work:

1. **Biology gates act classically on the diagonal.** Clone (CNOT), metabolism (Toffoli), phenotype copy, SWAP
   interaction and amplitude-damping death all map basis states to basis states, or act as stochastic maps on them.
   So every biological readout has an exact classical surrogate. This was proven in code in Month 4
   (`classical_surrogate_z`).
2. **Genealogies are trees.** A clone cascade has an interaction graph of treewidth ≈ 1, and tensor-network
   contraction cost is exponential only in treewidth (Markov & Shi 2008). So a faithful phylogeny, even with
   non-Clifford mutation angles, contracts exactly in polynomial time. W = 50 is large but classically easy.
3. **Mutation–selection equilibrium is a stoquastic ground state.** The quasispecies (Eigen / Crow–Kimura)
   equilibrium on sequence space is the ground state of an Ising quantum chain in a transverse field: mutation is
   the transverse field and fitness is the Ising energy (Baake, Baake & Wagner, PRL 78, 559, 1997). That
   Hamiltonian is stoquastic (sign-free), which is the regime where classical quantum Monte Carlo usually works.

**Where the exits are, each a falsifiable hypothesis:**

- **Interaction loops.** Competition between lineages and spatial tissue (2D lattices, PJ1 arena, ch-qca on a
  square lattice) raise treewidth toward √n. Hardness can only appear here.
- **Non-Clifford, non-stochastic coupling.** Hardness needs magic (stabilizer Rényi entropy > 0) *and*
  interference that does not reduce to a stochastic map. The price: the interference is no longer classical
  biology. It is "quantum excess" layered on the biology.
- **Algorithmic encoding instead of a quantum organism.** Keep the biology classical and use the quantum computer
  to *compute a property of it*: rare-event probabilities, marginals over 2^L genotypes, mixing. Here the hardness
  sits in the question asked, not in a quantum imitation of life (§6).

This tension is the honest answer to "how do we get to a more complex simulation than any classical computer". You
get there by asking the classical biology a question that is expensive classically, not by making the organism more
quantum. Hardness bought with quantum excess is a hardware benchmark, not a better biological model.

---

## 5. Measuring objectively how close we are to L2

Every circuit family at width n and depth d gets three coordinates, from the same run where possible.

| Axis | Symbol | Definition | Pass mark |
|---|---|---|---|
| **Alive** (survival) | S | k-sigma margin of a *proper* witness (rung W-b or higher, §3.3), raw, `kept_fraction` stated | S ≥ 3 |
| **Hard** (classical cost) | H | log₁₀ of the cheapest cost, in core-seconds, for a fixed attack portfolio to reproduce the measured witness and target observables to the hardware's own accuracy | above a stated budget tier: laptop < cluster < supercomputer |
| **Faithful** (biology) | Φ | 1 − TVD between the circuit's biological readouts and the target classical model (branching process, Wright–Fisher, quasispecies), checked at small n where the reference is exact | Φ ≥ 0.9 (to be set) |

**Attack portfolio for H** (fixed and published, like the community quantum-advantage tracker; verify its current
form):
- exact stabilizer simulation and treewidth contraction;
- MPS/TEBD with the minimal bond dimension χ* that matches the hardware error;
- belief-propagation tensor networks (Tindall et al., PRX Quantum 2024, the paper that undid the 127-q "utility"
  experiment);
- Pauli-path propagation (verify reference);
- for noisy deep circuits, the polynomial noisy-sampling algorithms (verify reference).

**Diagnostics logged next to H:** treewidth of the circuit graph, stabilizer Rényi entropy M₂ (Leone, Oliviero &
Hamma, PRL 2022), half-cut entanglement entropy (small-n sim, extrapolated).

**Distance to L2.** For the alive and faithful points (S ≥ 3, Φ ≥ Φ_min):

  D_L2 = max(H) − H_budget   (orders of magnitude; negative means a classical computer wins)

**Forecast metric.** Fit the survival model S(n, d) ≈ f(e^(−ε·N₂q)) per family. That gives the error per layered gate
ε* at which an alive-and-hard cell first appears. The ratio ε_now / ε* is an objective "how many hardware
generations to an L2 candidate". It can be checked against the vendors' published error roadmaps. It is
falsifiable: when a better chip arrives, the cell either opens at the predicted ε or it does not.

**Where the existing data sits today** (my reading; the numbers are from the repo):

| Point | n | S (rung) | H | Φ | Level today |
|---|---|---|---|---|---|
| QuantumTree C(d), serial, 2 layers | 108 | z ≈ 10 (W-a only; depth-confounded) | likely low: deep noisy circuits drift to easy | no target model (art) | below L1 |
| Teleport bond, d = 12 | 102 | 2-point correlation, sign matches ideal (W-a) | — | — | below L1 |
| QALife W = 24 / W = 50 germ/soma | 48 / 100 | 3σ (W-a) | tree, treewidth ≈ 1: easy | high (2018 operators, selftest) | L1 *candidate*, pending E1 |
| Motile vivarium, ghz2 | 16 | 1.96 vs 1 (W-b, pairs) | trivial at 16 q | high | L1 (small) |
| D-SCALE CHSH roll | 2 | S = 2.733 (W-d) | n/a | n/a | L0 |
| D-SCALE ch-qca | 23 sites | negativity, k = 2, marginal (W-b) | non-Clifford; BP column not yet run at full grid | none (generic rule) | L1 marginal |
| D-SCALE ghz-spine | 28 | F = 0.055 (W-c, **fail**) | χ = 2: easy | n/a | L0 |
| D-SCALE pmd-bank (L1′) | 2-q blocks | gap −2.9 × floor | never L2 | process model | not L1′ |

**Summary in one line: every alive point is classically easy, every point that might be hard is dead or meaningless,
and D_L2 is negative everywhere measured.** That is the starting coordinate, and it is a legitimate result.

---

## 6. The medication prediction and response map: where quantum can and cannot help

**What the map is.** For a tumour described by its clonal composition (genotypes, sizes, spatial layout) and a
therapy (drug, dose, schedule), predict the response: shrinkage, time to resistance, probability that a resistant
clone exists or emerges. Classical models already do this:
- branching processes and Luria–Delbrück estimates of pre-existing resistance;
- evolutionary game theory and adaptive therapy (Gatenby; the prostate adaptive-therapy trial, verify citation);
- agent-based tissue simulators (PhysiCell-class).

**What is expensive classically:** not sampling one trajectory, which is cheap. The expensive parts are:
- rare events (a resistant clone at 10⁻⁹ frequency);
- exact marginals over 2^L genotypes with epistasis;
- fitting parameters to sparse patient data;
- the molecular question of how a mutation changes drug binding.

Ranked by credibility:

| Route | What quantum computes | Advantage type | Claim level, horizon | Comment |
|---|---|---|---|---|
| Molecular layer | Binding energy of drug vs mutant target (e.g., resistance mutations) | Potentially large; the native quantum problem | L3, fault-tolerant, 10–15 years | Strongest route. Feeds *fitness parameters* to the evolution layer. It is quantum chemistry, not evolution. |
| Rare-resistance estimation | Amplitude estimation over a classical stochastic model (Montanaro 2015) | Quadratic | L3, fault-tolerant | Quadratic gains are eaten by error-correction overhead for a long time (Babbush et al., PRX Quantum 2021, verify) |
| Genotype-space dynamics | Linear ODE / imaginary-time solvers on the 2^L master equation (LCHS-type, verify) | Possibly large for few observables | L3, fault-tolerant | Stoquasticity (§4.3) may let classical Monte Carlo keep up; needs a case-by-case check |
| Compressed process models | Quantum causal states with less memory than any classical model (Gu et al. 2012) | Provable memory advantage | L1′, NISQ now | The D-5 route. Real, but memory is not prediction quality |
| "Quantum organism" sampling | A QALife-type circuit whose output is a cohort | none for the biology | L1 at best | Useful as the hardware benchmark of §5 and as provenance (L0); not a better predictor |

**Honest picture for the paper's outlook:** a two-scale, quantum-ready response map.
- **Molecular layer:** quantum chemistry → fitness and drug-sensitivity parameters.
- **Population layer:** classical evolutionary simulation, later quantum-accelerated for rare events.
- **Validation spine:** the §5 witness and hardness ledger.

This puts the quantum computer where physics says it is strong and says plainly where it is not. It is also the
version that survives a hostile reviewer.

---

## 7. The path to L2 and beyond: experiments in order

Develop in simulation (Aer, `FakeMarrakesh`); hardware runs are Peter's.

| # | Experiment | Question | Acceptance | Cost |
|---|---|---|---|---|
| **E1** | Tóth–Gühne GME witness on the germ register, W = 4…50, ≥ 3 repeats per W across calibration cycles | What is the *real* L1 width? | Table: certified GME width and entanglement depth k vs W, with bound and citation | small: same two settings as ghz2 |
| **E2** | Attack portfolio on every family (QALife tree, arena, motile, ch-qca, kicked Ising) | Where is H on the map? | H, χ*, treewidth, M₂ per (n, d); code public | simulation only |
| **E3** | Faithfulness: circuit readouts vs classical branching / Wright–Fisher model at n ≤ 20 | Is Φ high, and how large is the quantum excess? | Φ per family; the excess quantified as the off-diagonal weight that the biology does not determine | simulation only |
| **E4** | Interacting lineages on loop lattices (PJ1 arena on 2D; ch-qca on a square lattice) | Does treewidth growth raise H before S dies? | S and H on the same (n, d) grid; the Goldilocks cell found or shown empty | simulation, then hardware |
| **E5** | Quasispecies ↔ transverse-field Ising: prepare the equilibrium for a small epistatic landscape (VQE or adiabatic), compare with the exact quasispecies | Can evolution's equilibrium be read off a quantum ground state, and is it hard? | Φ vs exact; a QMC baseline time; stoquastic ⇒ expected easy, recorded as such | simulation, then small hardware run |
| **E6** | Forecast: fit S(n, d; ε) and compute ε* for the first alive-and-hard cell | How many hardware generations to an L2 candidate? | ε_now / ε* per family, re-tested on the next backend (Heron r3, Nighthawk) | simulation plus existing calibration data |

E1 and E2 alone are enough for the paper. E3–E6 make it strong. E5 is the novel theory hook that connects evolution
to quantum Hamiltonians. As far as I know, it has not been tried on hardware for tumour-like landscapes (verify with a
literature search before claiming that).

---

## 8. Recommended paper

**Recommendation:** a framework-plus-measurement paper, separate from Siemens, posted to arXiv first for the
timestamp. It is distinct from the planned P1 (QALife arc) but feeds it: E1 goes into P1 too, because P1's current
headline rests on the W-a test.

**Working titles:**
- *Alive, Hard, Faithful: a witness-based map of how far quantum models of evolution are from classical reach*
- *Where can quantum simulations of evolution beat a classical computer? A three-axis measurement framework with
  100-qubit hardware data*

**One question:** can a circuit that faithfully implements evolutionary biology be both entangled on hardware and
hard to simulate classically, and how far are we from that point?

**Headline (expected, still publishable if it changes):**
- Today no biology-faithful circuit is both alive and hard: D_L2 < 0 everywhere. The reason is structural (§4).
- The only exits are interaction loops with non-Clifford coupling, or algorithmic encodings.
- The measured GME width is X qubits (E1), and the forecast puts the first candidate cell at ε* = Y.

**Structure (about 8–10 pages):**
1. Introduction: the "quantum life / quantum tumour" claims in the literature and why they need a ladder.
2. The claim ladder L0–L3 and the witness rungs W-a…W-d.
3. The faithfulness–hardness tension: three propositions (diagonal surrogate, tree contraction, stoquastic
   equilibrium), with short proofs or sketches.
4. The three-axis metric (S, H, Φ), the attack portfolio, D_L2 and the forecast ε*.
5. Hardware data: QuantumTree C(d), the QALife arc (W24 → collapse → germ/soma W50, with the corrected E1
   witness), motile ghz2, the D-SCALE live run; all placed on the map, recorded negatives included.
6. Exits: interaction lattices (E4), the quasispecies ground state (E5).
7. Outlook: the two-scale medication response map (§6), labelled preliminary.

**Owned novelty:**
- the ladder plus the three-axis map as a method;
- the tension stated and evidenced;
- the germ/soma design rule;
- the corrected GME width of quantum artificial life on Heron;
- the empty Goldilocks zone as a result.

**Prior art to cite and position against:**
- Alvarez-Rodriguez et al. 2018 (origin);
- Baake, Baake & Wagner 1997 (evolution ↔ quantum chain);
- Gu et al. 2012 (memory advantage);
- Jozsa & Linden 2003; Markov & Shi 2008; Gottesman–Knill (simulability);
- Tóth & Gühne 2005 and Gühne & Tóth 2009 (witnesses);
- Kim et al. 2023 and Tindall et al. 2024 (utility vs BP);
- Mooney et al. 2021 and later IBM GHZ records (scale is not the novelty);
- Montanaro 2015 and Babbush et al. 2021 (Monte Carlo speedup and its limits).

**Venues:** arXiv first, then IEEE QCE 2027, *Quantum Science and Technology*, or *PRX Life* (verify scope and
deadlines).

**Minimum that still publishes:** sections 2–4 plus the existing hardware data plus E1. That is one hardware session of
moderate size plus simulation.

**Risks:**
- A reviewer calls the tension "obvious". Mitigation: the propositions are precise and the hardware data is real.
- E1 shows a small GME width. That is fine: it is the honest number, and it is new.
- Scope creep into the medical layer. Keep §6 as outlook only.

---

## 9. Ownership: practical steps

- **arXiv preprint** with Peter as first author is the timestamp that counts. The git history in this repo (dated
  commits since summer 2026) is supporting evidence.
- **Check before starting at Siemens:** the employment, thesis or internship agreement's IP clause, and whether
  pre-existing work needs to be listed as background IP. Posting the preprint before the start date is the cleanest
  route (verify with the contract and the supervisor).
- **Keep Siemens-specific content out of this paper** (CT pipeline, cohorts, product names), so there is no overlap
  question later. The medical outlook stays generic.

---

## 10. Open questions for Peter

1. **Scope:** the framework paper (recommended), or fold everything into P1 and skip a separate paper?
2. **E1 timing:** can a GME sweep (W = 4…50, 3 repeats) fit the next QPU budget? It is the decisive experiment.
3. **E5 (quasispecies ↔ Ising):** keep it in this paper as the theory hook, or save it for P3 / the thesis?
4. **Authorship:** supervisor as co-author or acknowledgement? This affects how "own" the timestamp reads.
