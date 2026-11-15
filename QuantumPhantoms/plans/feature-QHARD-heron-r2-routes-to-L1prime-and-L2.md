# Feature Q-HARD — Exploration: every route by which Heron r2 could earn L1′ or L2 in stage B (seeding) or stage D (start of growth), validated on paper, with a probability per route

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved). **The epic has no Q-HARD row** (it also has none for D-SCALE or F6); the developer adds it (Q1). Q-HARD sits next to [feature-D-SCALE-decoherence-surviving-circuits.md](feature-D-SCALE-decoherence-surviving-circuits.md) (Approved) and [feature-F6-split-jobs-placement-quantum-growth.md](feature-F6-split-jobs-placement-quantum-growth.md) (Draft) and feeds both.
**Feature ID:** Q-HARD (proposed, Q1)
**Author:** Claude (SONET)
**Date:** 2026-11-10
**Status:** Draft

> **Stack locked.** Python 3.13 (conda base `/home/peter/anaconda3/bin/python3`), pinned `requirements.txt` (qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy, networkx). No new dependency (Q6).
>
> **Core directive.**
> - **This is an exploration and validation plan.** Part I (§1, §4) is the finished desk study: the candidate routes, the papers behind them, the arithmetic against Heron r2, and a probability for each. Part II (§2, §6, §7) is the simulation-only follow-up that would turn the top routes into go / no-go numbers.
> - **No quantum computer is used.** Nothing in this plan was run on a QPU or on a circuit simulator. The only computations done while drafting were classical: graph cuts of the Heron r2 coupling map and a NumPy optimisation of sequence probabilities (§4.2, §4.4). The follow-up runs on AerSimulator / `FakeMarrakesh` only; hardware stays Peter's, from a pack.
> - **No automated tests.** Manual verification only (§7). Smoke runs ≤ 20 minutes (D-SCALE rule).
> - **Honesty gates (CLAUDE.md) apply.** Every probability below is a subjective estimate, stated with its basis. No route is claimed to work. "L2 is blocked" stays true for Heron r2 after this study; what changes is that the blockade now has numbers.

---

## 1. Why (Step Goal)

**Before.**
- The claim ladder stops at L1 on hardware. Best run (`research_runs/dscale_live_100_20261031-170957`, `hardware: ibm_marrakesh, job dbj16056p51s73cjs7q0`): CHSH 2.733 (L0), QCA negativity on 1 of 4 edges with p_bonf 0.046 (L1, marginal), GHZ spine F_dfe 0.055 (L0), and the only L1′ attempt, `pmd-bank`, lost to a 2-bit classical model (gap / floor −2.88, L0).
- The L1′ design has a structural weakness. It scores a d_KL difference of about 10⁻³ against a sampling floor of the same size (simulated gap / floor 2.75, below the 3× rule in `_dscale/pmd_retune.json`).
- L2 is marked "blocked: shallow heavy-hex is BP-simulable" with no number for *how* blocked, and F6 plans to measure "distance to L2" with belief propagation only.
- Stage B has no claim above L0 in any design. The reverse-engineered B circuits are noise-dominated on Heron-class noise (2,033 to 38,123 CZ, TVD 0.57 to 0.74).

**After this plan (Part I, done here).**
1. A **hardness budget for Heron r2** from its own coupling graph and calibration snapshot (§4.2). It replaces "blocked" with a threshold: about 2,000 to 2,900 CZ at roughly 10× lower effective error than r2 delivers.
2. A **catalogue of 17 routes** to L1′ or L2 for B and D, each with its source papers, its circuit cost on heavy-hex, the classical adversary it defeats, the arithmetic against r2, and a probability (§4.3).
3. A **finding that reorders the work**: conjecture-based hardness (L2) is out of reach on r2 (best route ≈ 3 %), but **unconditional resource separations are within reach**, and they are the hardness r2 can earn. Three kinds: memory (a qubit against a bit), communication (n qubits against proven classical bits) and sample complexity (learning with a quantum memory against without).
4. A **replacement for the failed L1′ experiment**: the tick-sequence test. It uses the same circuit shape as `pmd-bank`, but its gap is 0.14 in probability (≈ 14σ at 4,000 shots) where the PMD gap was ≈ 10⁻³ in d_KL (§4.4).

**After the follow-up (Part II, to be approved).** A simulation-only package `code/qhard/` that gives, for the six shortlisted routes, the predicted hardware margin under `FakeMarrakesh` noise, a go / no-go, and hardware packs for the routes that pass. Nothing is submitted.

---

## 2. Acceptance Criteria

Part II only. Part I is this document.

- [ ] **AC-1** (Q-HARD.1): the hardness budget is reproducible for every target.
  → `python -m qhard.budget --target marrakesh|kingston|boston|nighthawk` reads the fake backend's coupling map and calibration and writes `research_runs/_qhard/budget_<target>.json`: qubits, couplers, minimum row cut, balanced bisection, treewidth upper bound, median CZ / readout error, and the derived table (CZ count needed for exact-contraction cost 2⁴⁰ / 2⁵⁰ / 2⁶⁰, raw fidelity at that count). For `marrakesh` it reproduces §4.2 (cut 4, treewidth ≤ 4, 21 hexagons).
- [ ] **AC-2** (Q-HARD.2): tick-sequence bounds are computed and stored with their status.
  → `python -m qhard.seqbound --memory 1 --lengths 3,4,5,6` writes `seqbound.json`: per sequence the classical d-state maximum, the qubit maximum, the optimal instrument (2-qubit unitary), and a `rigour` field. `rigour` is `"proven"` only where the value equals a published bound (one-tick, L = d + 1: ((L−1)/L)^L, Vieira–Ku–Budroni Table 1); everything else is `"numerical"`. For `001` it reproduces 8/27 against 7/16.
- [ ] **AC-3** (Q-HARD.3): the tick-clock machine is simulated under Heron-class noise.
  → `python -m qhard.tick_clock --seq 001 --noise heron --shots 4000 --repeats 15` builds the deferred-measurement machine (1 memory qubit + L output qubits on a path, one 2-qubit unitary per step, all measured at the end, no mid-circuit operation) and reports p(seq) ± σ, the classical bound, the margin in σ, and the verdict. Label: `simulated: Heron-class noise (FakeMarrakesh)`. The same command accepts `--memory 2` (4-state classical bound) and reports it separately.
- [ ] **AC-4** (Q-HARD.4): the one-qubit hand-off test (random access code) is simulated.
  → `python -m qhard.qrac --n 2|3 --noise heron` reports the average success probability against the classical one-bit bound (0.75) for the 2→1 and 3→1 codes.
- [ ] **AC-5** (Q-HARD.5): learning the growth channel with a sister memory is simulated on a width ladder.
  → `python -m qhard.memlearn --pairs 4,8,16,32 --noise pauli:marrakesh` prepares n Bell pairs (founder, sister) on a heavy-hex path, applies a programmed Pauli "mutation" channel to the founder half, Bell-measures, and estimates the hidden Pauli eigenvalue. It reports samples-to-decide with the memory against the best memoryless strategy coded as a baseline, and the fitted per-qubit overhead with its error, to be compared with the proven memoryless lower bound of 2 per qubit (Seif et al.). Stabilizer simulation, so 64 qubits fit.
- [ ] **AC-6** (Q-HARD.6): the information-supremacy route gets a feasibility number, not a run.
  → `python -m qhard.dxhog --n 8,10 --layers 10..60` trains the brickwork ring ansatz to Haar-random targets (NumPy/SciPy, statevector algebra, no circuit simulator needed), and combines ansatz fidelity, the `FakeMarrakesh` gate and readout errors and Bob's Clifford cost into a predicted XEB ε per depth. It converts ε to the classical-bit lower bound with the explicit constants transcribed from the Kretschmer et al. Supplement (Theorem 3 and Lemma 9), and prints the verdict "bits > n: yes / no" for n = 8, 10 and an extrapolation to n = 12 (one hexagon). n = 12 training goes into the runbook, not the smoke run.
- [ ] **AC-7** (Q-HARD.7): the hexagon nonlocal game is simulated.
  → `python -m qhard.ring_game --noise heron` prepares the 12-qubit cyclic cluster state on one hexagon, plays the game of Daniel et al., and reports the win probability against the classical bound transcribed from that paper.
- [ ] **AC-8** (Q-HARD.8): doped-Clifford sampling is sized for r2 and for r3.
  → `python -m qhard.dcs --n 12,20,30,40 --noise pauli:marrakesh|pauli:boston` builds the 1-D Clifford brickwork with single-qubit ancilla checks (caterpillar layout), simulates the Clifford skeleton with Pauli noise, and reports the post-selection rate and stabilizer-state fidelity per n. It fits the per-CZ loss and extrapolates to the published size (70 data qubits, 2,869 CZ), printing the predicted acceptance next to the published 5.9 × 10⁻⁴ for `ibm_boston`. A statevector cross-check with T gates runs at n ≤ 16.
- [ ] **AC-9** (Q-HARD.9): the L2-distance metric gets the right adversary.
  → `qhard.budget` exposes `exact_cost(circuit, layout)` = log₂ of the exact-contraction cost from the cut structure (4 couplers per row cut, operator-Schmidt rank 2 per CZ). `scorecard` reports it next to the BP number for the `ch-qca` and `kicked-ising` circuits at t = 1..6. The plan text for F6 AC-16 is amended by the developer to "t\* = smallest depth where **both** BP needs χ > 16 **and** exact cost > 2⁴⁵" (§9).
- [ ] **AC-10** (Q-HARD.10): one scorecard, with updated probabilities.
  → `python -m qhard.scorecard` merges all outputs into `research_runs/_qhard/scorecard.json` and `scorecard.md`: per route the claim sub-level, classical bound and its rigour, simulated margin, prior probability (§4.3), posterior after simulation, and go / no-go. A route is `go` only if its simulated margin is ≥ 3σ at ≤ 20,000 shots.
- [ ] **AC-11** (Q-HARD.11): hardware packs for the routes that pass, nothing submitted.
  → `python -m qhard.pack --route <id> --target marrakesh` writes ISA circuits (QPY), the shot plan, a QPU-time estimate and the analysis command into `research_runs/_qhard/pack_<route>/`. The package contains no `QiskitRuntimeService` call. `code/qhard/RUNBOOK_QHARD.md` lists the Peter-only steps.
- [ ] **AC-12** (Q-HARD.12): docs.
  → `QuantumPhantoms/README.md` Progress row + changelog line; `code/README.md` section for `qhard`; the route labels of Q2, once approved, are written into the runbook.

---

## 3. Out of Scope (Postponed)

- **Any hardware submission** → Peter, from the packs, after the scorecard. Never by Claude.
- **Promoting a winning route into the live pipeline** (`dscale.live`, the page, the tile badges) → F6 or its successor. Q-HARD only says which route deserves it. The natural hand-over is tick-clock replacing `pmd-bank` as F6's job C (Q7).
- **Routes rated ≤ 5 %** (peaked circuits, mitigated Floquet / Loschmidt observables, random-circuit XEB, deep QCA, certified randomness from sampling) → documented in §4.3, not simulated.
- **Heron r3 and Nighthawk hardware work.** Every published heavy-hex advantage result of 2026 ran on r3, and the random-circuit result ran on Nighthawk r2. Q-HARD simulates r3 as a comparison column only (Q3).
- **Backend selection by name** → Peter's own refactor. `qhard.pack` takes a `--target` name and stays compatible with it.
- **Changing CLAUDE.md's ladder text** → the developer, after Q2.
- **A biology argument for any of this.** Tumour growth is classical. Every route certifies a property of the generating device or process representation, never of the tumour.

---

## 4. Technical Decisions

### 4.1 What "L1′" and "L2" must mean for this study

A Z-basis draw has an exact classical surrogate (analysis doc §0). So in both stages the claim lives in a **certificate that shares the job and the qubits' neighbourhood with the draw**, exactly as the CHSH pair does today. Stage B = the device prepares; stage D = the device evolves and is read. The proposed sub-labels (Q2):

| Label | Meaning | Classical adversary defeated | Conjecture needed |
|---|---|---|---|
| L1′-T | Temporal memory: a k-qubit memory emits a sequence more often than any 2^k-state classical machine can | Any classical finite-state machine of the same memory size | None (dimension assumption on the memory) |
| L1′-C | Communication memory: an n-qubit hand-off solves a task that needs provably more than n classical bits | Any classical one-way protocol | None |
| L1′-L | Learning memory: a quantum sister memory learns the process with fewer samples than any memoryless strategy | Any strategy without quantum memory | None |
| L1′-S | Simulation memory (the existing D-5): C_q < C_μ, scored by distortion at equal memory | Classical models of equal memory | None |
| L1.5 | Locality: correlations no bounded-depth, bounded-fan-in classical circuit (no "local growth rule") can produce | Local hidden-variable models, NC⁰ circuits | None |
| L2 | Sampling or estimation beyond the best known classical algorithms | Tensor networks, BP, Pauli propagation, stabilizer-rank methods | Yes (and history of being overturned) |

### 4.2 Hardness budget of Heron r2 (computed 2026-11-10 from the `FakeMarrakesh` snapshot; not a live calibration)

| Quantity | Value | Consequence |
|---|---|---|
| Qubits / couplers / hexagons | 156 / 176 / 21 | |
| Coupler cut between any two adjacent rows | **4** | Balanced bisection of the whole chip = 4 couplers (Kernighan–Lin, 20 seeds) |
| Treewidth of the coupling graph (min-fill upper bound) | **≤ 4** | The chip is quasi-one-dimensional for a classical simulator |
| Median CZ error / readout error | 3.3 × 10⁻³ / 9.5 × 10⁻³ | 0.99¹⁵⁶ ≈ 0.21 readout survival on the full chip |
| Median T1 / T2 | 197 µs / 118 µs | |

Derived:
- A CZ has operator-Schmidt rank 2. After each cut coupler has been used c times, the bond across a row cut is at most 2^(4c). Exact contraction therefore costs about 2^(4c): **c = 3 (the depth where our QCA witness is still alive) is 2¹², a laptop second.** BP is not needed to simulate today's live circuits; exact contraction does it.
- Pushing the exact cost to 2⁴⁸ or more needs c ≥ 12 on every cut, about **2,100 CZ on the full chip**. Raw fidelity at the median error: e^(−0.0033 × 2112) ≈ 10⁻³, before readout.
- IBM's own route confirms the number from the other side. Martiel et al. (arXiv 2607.25941) used a **1-D chain** of 70 data qubits at depth 70 plus 27 ancillas: **2,869 CZ**, bond dimension 2³⁰ for the Clifford skeleton, post-selection rate 5.9 × 10⁻⁴, on `ibm_boston` (**Heron r3**). That acceptance implies an effective loss of 0.26 % per CZ. If r2 loses 2 to 2.5 times more per CZ (assumption from the median errors; verify on live calibration), the same circuit is accepted at 10⁻⁷ to 10⁻⁸: the published 2 × 10⁷ shots would return about one sample.
- **Threshold statement.** L2 on heavy-hex needs roughly 2,000 to 2,900 CZ at ≤ 0.26 % effective loss per CZ with error detection or mitigation on top. Heron r2 is a factor 2 to 2.5 short in error rate, which is a factor 10³ to 10⁵ in accepted shots.
- The 2026 advantage candidates confirm the pattern: doped-Clifford sampling (r3, 97 q), Floquet magnet on a heavy-hex ladder (r3, 51 to 74 q, arXiv 2607.24937), operator Loschmidt echo (Heron, 56 q, arXiv 2607.25998), peaked circuits (`ibm_boston`, 4,000 to 5,000 CZ, later matched classically in seconds to an hour), random-circuit sampling (Nighthawk r2 square lattice, 61 q, 918 CZ, arXiv 2609.28657). **None ran on Heron r2.**

### 4.3 Route catalogue

P = subjective probability that the stated pass rule is met on Heron r2 in one prepared campaign by Peter (≈ 10 QPU-minutes), assuming the simulation step passed first. Costs are for heavy-hex after layout.

**Shortlist (simulated in Part II)**

| # | Route | Stage | Level | Circuit on r2 | Pass rule | Sources | P (r2) |
|---|---|---|---|---|---|---|---|
| R1 | **Tick-clock**: a one-qubit division-timing machine emits the pattern "rest, rest, divide" more often than any one-bit machine can | D | L1′-T | 4 q path, ≤ 9 CZ, deferred measurement | p(001) > 8/27 = 0.296 by 3σ; ideal 7/16 = 0.4375 | Budroni et al. 1902.06517; Vieira–Budroni 2104.02467; Vieira–Ku–Budroni 2402.16789 | **0.85** |
| R2 | **One-qubit hand-off** (random access code): the founder passes two traits through one qubit; the daughter reads either one | B→D | L1′-C (smallest) | 1 q, 0 CZ | Average success > 0.75; ideal 0.854 | Ambainis et al. 1999 (verify); dimension-witness experiment 1111.1208 | **0.95** |
| R3 | **Sister-memory learning**: Bell pair (founder, sister); the growth step acts on the founder as a Pauli "mutation" channel; a Bell measurement learns it | D | L1′-L | 2n q on a path, n CZ + n CZ, n = 8 to 32 | Fitted per-qubit sample overhead < 2 (the proven memoryless lower bound) by 3σ | Seif et al. 2408.03376 (IBM hardware, 64 q, overhead 1.33 ± 0.05); Huang et al. 2112.00778 | **0.50** |
| R4 | **Information supremacy on one hexagon**: B prepares a 12-qubit state from a classical description, D measures it in a random Clifford basis | B→D | L1′-C | 12-q ring = one hexagon; 180 to 360 RZZ + ≈ 100 CZ; 10,000 single-shot circuits | XEB ε such that the proven classical bound exceeds 12 bits (ε ≳ 0.16 by extrapolation from the paper's two points) | Kretschmer et al. 2509.07255 (H1-1: ε = 0.427, ≥ 62 bits) | **0.12** |
| R5 | **Hexagon nonlocal game**: cyclic cluster state on one hexagon wins a game no local classical strategy wins | D (also B) | L1.5 | 12 q, 12 CZ, depth 2 | Win probability above the classical bound by 3σ | Daniel et al. 2110.04277; Bravyi–Gosset–König 1704.00690; Watts–Parham 2301.00995 | **0.55** |
| R6a | **Doped-Clifford lineage, sub-threshold**: genealogy = Clifford skeleton, mutations = T gates, ancilla checks give a fidelity lower bound | D (samples can seed B) | "L2 protocol, not L2" | 30 to 46 data q on a chain + ancillas, 500 to 1,250 CZ | Certified fidelity lower bound > 0 at 95 % on a T-doped state, cross-checked by exact simulation | Martiel et al. 2607.25941 | **0.40** |
| R6b | The same at hardness size | D | **L2** | ≥ 60 data q, ≥ 2,400 CZ | Certified bound > 0 where no classical method reproduces it | same | **0.03** |

**Second tier (documented, simulated only if Peter asks, Q4)**

| # | Route | Stage | Level | Why second tier | Sources | P (r2) |
|---|---|---|---|---|---|---|
| R7 | Tick-clock with a 2-qubit memory against 4-state machines | D | L1′-T | Gap ≈ 12 % of the bound at 50 to 100 CZ; margin ≈ noise | 2402.16789 Table 1 | 0.30 |
| R8 | Memory cost of contextuality: sequential Peres–Mermin measurements on 2 qubits need more than 2 classical bits | D | L1′-T | Published bounds are for perfect correlations; a noise-robust inequality must be found first | Kleinmann et al. 1007.3650; Fagundes–Kleinmann 1611.07515 | 0.35 |
| R9 | PMD re-tune plus error mitigation (the existing D-5) | D | L1′-S | Gap stays near the floor; mitigation adds variance | Wu 2208.12744; Ho–Takagi–Gu 2105.06448; Banchi 2312.13473 | 0.15 |
| R10 | Extreme-compression process (classical memory diverges, one qubit suffices) | D | L1′-S | Same scoring weakness as R9: small approximate classical models are good in d_KL | Elliott et al. 1909.02817 | 0.15 |
| R11 | Contextual generative draw: the rulebook network read in random bases needs a larger classical network | B | L1 + expressivity statement | Violation is likely (P ≈ 0.7) but the claim is close to an entanglement witness | Gao et al. 2101.08354; Anschuetz et al. 2209.14353 | 0.70 for the violation |

**Rejected for r2 (documented only)**

| # | Route | Level | Reason | Sources | P (r2) |
|---|---|---|---|---|---|
| R12 | Peaked-circuit seed (the peak is the committed seed) | L2, verifiable | 4,000 to 5,000 CZ on r3; classical methods then solved the instances in seconds to an hour | Aaronson–Zhang 2404.14493; Gharibyan et al. 2510.25838; tracker | 0.02 |
| R13 | Mitigated Floquet magnet or operator Loschmidt echo (our QCA echo is the same kind of observable) | L2, estimation | r3 results at 51 to 74 q; mitigation overhead grows as the square or cube at r2 error | 2607.24937; 2607.25998 | 0.04 |
| R14 | Random-circuit sampling with XEB on heavy-hex | L2 | Treewidth 4; hardness needs ≥ 2,100 CZ; sample-only verification is under attack | 2609.28657 (Nighthawk); Oh 2607.04054; Aharonov et al. 2211.03999 | < 0.01 |
| R15 | Deeper `ch-qca` until BP fails | L2 | Witness dies at t ≈ 2 to 3 while exact cost is 2¹²; BP-hard is not classically hard | Tindall 2306.14887; Park et al. 2504.07344 | 0.01 |
| R16 | Certified randomness from sampling for the seed | L2 | Needs R14 first | Liu et al. 2503.20498 (C02) | < 0.01 |
| R17 | Constant-depth cluster-state (measurement-based) sampling on the whole chip | L2 | Exact contraction is trivial at treewidth 4; noisy constant-depth sampling has polynomial classical algorithms | Napp et al. 2001.00021; Rajakumar et al. 2403.14607; Schuster et al. 2407.12768 | < 0.01 |

**Combined (rough, routes treated as independent):** at least one L1′-class success on r2 ≈ 0.95 (R1 and R2 carry it); at least one success beyond single-qubit memory (R3, R4, R5 or R6a) ≈ 0.85; any L2 on r2 ≈ 0.05.

### 4.4 Validation notes per shortlisted route

- **R1 tick-clock.**
  - Classical bound 8/27 for `001` with a 2-state machine is published and exact (one-tick, L = 3, d = 2). Vieira–Ku–Budroni report no violation at d = 2 **for entanglement-breaking instruments**; the machine here keeps the memory qubit coherent between steps, which is the point.
  - Own classical numerics (NumPy/SciPy, 12 restarts, one Kraus operator per outcome, 2026-11-10): qubit optimum 0.4375 for `001`; ratio 1.48. Longer sequences give larger ratios (`001001`: 0.191 against 0.088, ratio 2.2) but those classical values are **numerical, not proven**.
  - Noise arithmetic: 9 CZ and 4 readouts keep ≈ 93 % of the signal, so p ≈ 0.41, a margin of ≈ 0.11 over the bound, ≈ 14σ at 4,000 shots.
  - Honest limits: (a) the claim is "one qubit beats one bit"; a 3-state classical machine emits `001` with certainty. (b) It rests on the memory being one qubit; output qubits are written once and never read back. (c) Before any claim, the 0.4375 optimum is checked against Vieira–Budroni's table and the instrument is re-derived, not taken from the optimiser.
  - Why it fixes the PMD failure: same deferred machine (`pmd_bank.machine_circuit`: memory + L outputs on a path, ≤ 3 CZ per step), different statistic. A probability gap of 0.14 replaces a d_KL gap of 10⁻³.
- **R2 hand-off.** Textbook numbers; readout error 1 % moves 0.854 to ≈ 0.846. It is a dimension witness under the assumption that one two-level system is sent. Its role is the first rung of the L1′-C ladder that R4 completes.
- **R3 sister-memory learning.** The proven separation is exponential for an ideal memory; with a noisy memory Seif et al. prove and measure a per-qubit overhead below the memoryless bound of 2 on IBM hardware. The Bell pair is the project's existing division primitive (⟨XX⟩+⟨ZZ⟩ witness), so the route reuses a circuit already shown to survive on `ibm_marrakesh`. Risk: a programmed single-qubit Pauli channel is a synthetic process; a referee may ask for an intrinsic one (the gate layer's own noise, as in the paper). Layout risk is low for single-qubit channels (pairs sit on neighbouring qubits of a path).
- **R4 information supremacy.**
  - The paper's ring brickwork with periodic boundary is native to one heavy-hex hexagon (12-cycle), and Heron has fractional RZZ.
  - Crude forecast: ε(d) ≈ (1 − 1.25 p)^(6d + 100) × F_ansatz(d) × 0.886, with F_ansatz calibrated to the paper's point (86 layers ↔ ≈ 0.71). At p = 0.33 % (median) ε ≈ 0.10: fail. At p = 0.2 %: ε ≈ 0.165: on the threshold. At p = 0.15 % (best hexagon): ε ≈ 0.21, ≈ 25 bits against 12 qubits: pass.
  - So the route lives or dies on the best hexagon's calibration, and on the exact constants in the bound (AC-6 transcribes them).
  - Extra cost: 10,000 distinct circuits at one shot each, each with fresh true random inputs; classical pre-training of 10,000 ansatz circuits. Bob's product-Clifford variant costs no 2-qubit gates but its bound is ε²(3/2)ⁿ, useless at n = 12.
  - On Heron r3 (p ≈ 0.1 %) the same arithmetic gives ε ≈ 0.3: P ≈ 0.5.
- **R5 hexagon game.** State fidelity ≈ 0.96 from 12 CZ, readout survival 0.886; the product ≈ 0.85 sits between the two classical bounds that such games have (3/4 and 7/8), so the verdict depends on which game the paper's bound belongs to (AC-7 transcribes it). Readout-error mitigation is not allowed in a game score.
- **R6 doped-Clifford lineage.** The acceptance rate is the same with and without T gates (reported in the paper), so a stabilizer simulation of the skeleton predicts it. At an assumed 0.5 to 0.65 % loss per CZ, an acceptance of 10⁻³ allows ≈ 1,100 to 1,400 CZ, i.e. 43 to 48 data qubits at depth = width. That size is classically simulable (split the chain: 2²³ paths of 2²³ amplitudes), which is why R6a is "the L2 protocol verified below the hardness threshold" and makes the cross-check possible. It gives the project a measured distance to L2 in IBM's own units.

### 4.5 Stack choices for Part II

| Component | Choice / Implementation |
|---|---|
| Package | New `code/qhard/`, simulation-only, never imported by the live path (Q5) |
| Noise | `heron` = `AerSimulator.from_backend(FakeMarrakesh)` for ≤ 16 q; `pauli:<target>` = existing `dscale/pauli_noise.py` model for stabilizer runs |
| Deferred machine | Reuse `dscale/families/pmd_bank.machine_circuit` shape (memory + outputs on a path); the unitary comes from `seqbound.json` |
| Graph numbers | `networkx` (`treewidth_min_fill_in`, `kernighan_lin_bisection`) on `target.build_coupling_map()` |
| Ansatz training (R4) | NumPy statevector algebra + `scipy.optimize` (L-BFGS, analytic gradients); no circuit simulator |
| Statistics | k = 3σ for go / no-go; first-run caps 4,000 shots, ≤ 15 repeats (D-SCALE Q9); R3 fit by weighted least squares |
| Randomness (R4) | True random inputs per trial from an F1 CHSH-certified roll (Q8) |

**Conventions & Notes:**
* Every output carries claim sub-level (§4.1), the classical bound with `rigour: proven | numerical`, and the label `simulated: ideal` or `simulated: Heron-class noise (FakeMarrakesh)`.
* A bound marked `numerical` can support a go for more simulation, never a claim.
* `Deadline` from `dscale/budget.py` caps every CLI at 20 minutes.
* No mid-circuit measurement, reset or feed-forward in any route (D-SCALE lint rule 1; own evidence that they lose on r2).
* Probabilities in the scorecard are updated by a stated rule: posterior = prior × 1.3 (cap 0.97) if the simulated margin is ≥ 5σ, prior if 3σ to 5σ, prior × 0.3 if below 3σ.

---

## 5. Data Model (Additions/Modifications)

```text
[New File] research_runs/_qhard/budget_<target>.json
  target, n_qubits, n_couplers, n_hexagons, row_cut, bisection_cut, treewidth_ub
  median_cz_error, median_readout_error, median_t1_us, median_t2_us, source ("fake snapshot")
  table: [{exact_cost_log2, cut_uses, cz_full_chip, raw_fidelity}]

[New File] research_runs/_qhard/seqbound.json
  memory_qubits, rows: [{seq, classical_max, quantum_max, ratio, rigour, unitary (4x4 re/im)}]

[New File] research_runs/_qhard/<route>.json            (one per shortlisted route R1..R6)
  route, stage ("B"|"D"|"B->D"), level ("L1'-T"|"L1'-C"|"L1'-L"|"L1.5"|"L2-protocol")
  label, noise, shots, repeats
  statistic, value, sigma, classical_bound, bound_rigour, margin_sigma
  circuit: {qubits, cz, depth_2q, dynamic: false}
  verdict ("go"|"no-go"), notes

[New File] research_runs/_qhard/scorecard.json  (+ scorecard.md)
  routes: [{id, name, stage, level, prior, posterior, verdict, ref: "<route>.json"}]
  combined: {any_l1prime, beyond_single_qubit, any_l2}

[New Dir]  research_runs/_qhard/pack_<route>/           (only for verdict == "go")
  circuits.qpy, plan.json {target, layout, shots, est_qpu_seconds}, ANALYSE.md
```

No existing entity changes. `research_runs/_qhard/` follows the `_dscale/` convention.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `code/qhard/__init__.py` | Package marker, route registry (id, stage, level, prior from §4.3) |
| New | `code/qhard/budget.py` | AC-1, AC-9: coupling-graph cuts, treewidth bound, CZ-budget table, `exact_cost()` |
| New | `code/qhard/seqbound.py` | AC-2: classical d-state and qubit optima per sequence, `rigour` field, optimal unitary |
| New | `code/qhard/tick_clock.py` | AC-3: deferred machine from `seqbound.json`; mirrors `code/dscale/families/pmd_bank.py` (`machine_circuit`, `run_cell`) |
| New | `code/qhard/qrac.py` | AC-4: 2→1 and 3→1 codes on one qubit |
| New | `code/qhard/memlearn.py` | AC-5: Bell-pair ladder, Pauli channel, memoryless baseline, overhead fit; noise from `code/dscale/pauli_noise.py` |
| New | `code/qhard/dxhog.py` | AC-6: ring-ansatz training, ε forecast, bit bound with transcribed constants |
| New | `code/qhard/ring_game.py` | AC-7: hexagon cyclic cluster game |
| New | `code/qhard/dcs.py` | AC-8: chain Clifford brickwork + ancilla checks, acceptance and fidelity ladder, r2 / r3 extrapolation |
| New | `code/qhard/scorecard.py` | AC-10: merge, posterior rule, `scorecard.md` |
| New | `code/qhard/pack.py` | AC-11: ISA circuits + shot plan; mirrors `code/dscale/hw_pack.py`; no runtime service |
| New | `code/qhard/RUNBOOK_QHARD.md` | Peter-only hardware steps; n = 12 training for R4; full ladders beyond the smoke cap |
| Modify | `code/README.md` | Section for `qhard` (commands, outputs, labels) |
| Modify | `QuantumPhantoms/README.md` | Progress row + changelog |
| Modify (developer) | `plans/epic-quantum-phantoms-mvp.md` | Row from §9 |
| Modify (developer) | `plans/feature-F6-split-jobs-placement-quantum-growth.md` | AC-16 wording and job C note from §9 |

---

## 7. Manual Verification (No Tests)

All from `code/`, simulators only.

- [ ] **Verify AC-1:** `python -m qhard.budget --target marrakesh` prints row cut 4, bisection 4, treewidth ≤ 4, 21 hexagons, and a table whose 2⁴⁸ row needs ≈ 2,100 CZ. `--target nighthawk` prints a larger cut.
- [ ] **Verify AC-2:** `python -m qhard.seqbound --memory 1 --lengths 3` prints `001: classical 0.2963 (proven), qubit 0.4375 (numerical)`.
- [ ] **Verify AC-3:** `python -m qhard.tick_clock --seq 001 --noise ideal` gives p ≈ 0.4375; `--noise heron` gives p between 0.38 and 0.43 with a positive margin in σ; the printed circuit has no mid-circuit operation and ≤ 9 CZ after transpile.
- [ ] **Verify AC-4:** `python -m qhard.qrac --n 2 --noise heron` prints a success probability between 0.83 and 0.86 against 0.75.
- [ ] **Verify AC-5:** `python -m qhard.memlearn --pairs 4,8 --noise ideal` shows the memory arm deciding in a number of samples that does not grow with n while the memoryless baseline grows; with `--noise pauli:marrakesh` it prints an overhead with an error bar and the comparison with 2.
- [ ] **Verify AC-6:** `python -m qhard.dxhog --n 8 --layers 10,20,30` prints ansatz fidelity rising with depth, the predicted ε per depth and the bits bound; the paper's own point (n = 12, ε = 0.427 → 78 bits; 0.362 → 62 bits) is reproduced by the bound function as a self-check.
- [ ] **Verify AC-7:** `python -m qhard.ring_game --noise ideal` wins with probability 1 (or the paper's ideal value); `--noise heron` prints the value and the bound.
- [ ] **Verify AC-8:** `python -m qhard.dcs --n 12 --noise ideal` accepts every shot with fidelity 1; with Pauli noise the acceptance falls with n and the extrapolated r3 value lands within a factor 3 of 5.9 × 10⁻⁴ (if not, the noise model is recorded as unvalidated, as `validate_noise` does).
- [ ] **Verify AC-9:** the scorecard shows, for `ch-qca` at t = 2, an exact cost near 2⁸ to 2¹² next to the BP row.
- [ ] **Verify AC-10:** `scorecard.md` lists six routes with prior, posterior and verdict; changing one route file's margin below 3σ flips its verdict on rerun.
- [ ] **Verify AC-11:** `grep -rn "QiskitRuntimeService" code/qhard` returns nothing; a pack directory holds `circuits.qpy`, `plan.json`, `ANALYSE.md`.
- [ ] **Verify AC-12:** README rows exist; every command finishes inside 20 minutes.

---

## 8. Open Questions

- [ ] **Q1:** Feature ID and epic row. *Proposed:* `Q-HARD`; the developer adds the row (§9).
- [ ] **Q2:** Does the ladder accept the sub-labels of §4.1 (L1′-T, L1′-C, L1′-L next to the existing L1′-S, and L1.5 for locality)? *Proposed:* yes, always written with the sub-label and its adversary, never as bare "L1′". This is the decision the whole plan hangs on: under a strict reading (L1′ = C_q < C_μ only), only R9 and R10 qualify and the best probability is 0.15.
- [ ] **Q3:** Is Heron r3 allowed as a second column? *Proposed:* simulate r2 and r3; packs for r2 only. Reason: R4 moves from 0.12 to ≈ 0.5 and R6b from 0.03 to maybe 0.2 on r3, which Peter should see before spending r2 time.
- [ ] **Q4:** Shortlist and order. *Proposed:* R1, R2, R3 first (cheap, high probability), then R6, R4, R5. Second-tier routes R7 to R11 only on request.
- [ ] **Q5:** Where does the code live? *Proposed:* `code/qhard/`. It conflicts with F6's "less code" directive, so it stays off the live path and is deleted or absorbed when a route is promoted. Alternative: `code/dscale/explore/`.
- [ ] **Q6:** New dependency? *Proposed:* none. (`stim` would make AC-8 faster; Aer's stabilizer method is enough for the ladder.)
- [ ] **Q7:** Should tick-clock replace `pmd-bank` as F6's job C? *Proposed:* yes if AC-3 passes at ≥ 5σ; `pmd-bank` stays in the tree as the L1′-S record of a negative result.
- [ ] **Q8:** Source of true randomness for R4's 10,000 trials. *Proposed:* bits from an F1 CHSH roll on hardware, stored before the circuits are built; a PRNG is not acceptable for the theorem.
- [ ] **Q9:** Is R2 worth a hardware slot at all? It will pass, and a referee will call it a textbook exercise. *Proposed:* run it only as the first rung of a ladder R2 → R4 in the same job family.
- [ ] **Q10:** Stage B. No route puts hardness into the rulebook draw itself. *Proposed:* accept that B's claim lives in a certificate register next to the draw (R2, R4, and R6's samples as seed bits), as CHSH does today, and say so on the page.
- [ ] **Q11:** Posterior rule in §4.5 (×1.3 / ×1 / ×0.3). *Proposed:* keep it simple and stated; Peter may prefer his own.

---

## 9. Post-Implementation Notes

**Edits for the developer (not made by this plan):**
- Epic §2 row: `| Q-HARD | Routes to L1′ / L2 on Heron r2 | Hardness budget, 17-route catalogue, simulation scorecard, hardware packs | open | Exploration. Sim only. Shortlist: tick-clock (L1′-T), one-qubit hand-off and hexagon information supremacy (L1′-C), sister-memory learning (L1′-L), hexagon game (L1.5), doped-Clifford lineage (L2 protocol below threshold). Plan: feature-QHARD-heron-r2-routes-to-L1prime-and-L2.md. |`
- F6 AC-16: "t\* = smallest depth where BP needs χ > 16 **and** the exact-contraction cost from the row cuts exceeds 2⁴⁵". F6 §1: add that exact contraction, not BP, is the adversary at t ≤ 3.
- F6 AC-5 (job C gate): accept either the PMD gate or the tick-clock margin, pending Q7.

**Sources checked while drafting (arXiv IDs verified against arxiv.org on 2026-11-10):** 2509.07255, 2607.25941, 2607.24937, 2607.25998, 2607.04054, 2609.28657, 2510.25838, 2404.14493, 2506.20658, 2603.09901, 2408.03376, 2112.00778, 2402.16789, 2104.02467, 1902.06517, 2601.14191, 1007.3650, 1611.07515, 2208.12744, 1909.02817, 2105.06448, 2312.13473, 2101.08354, 2209.14353, 1704.00690, 1904.01502, 2301.00995, 2110.04277, 2306.14887, 2504.07344, 2407.12768, 2211.03999, 2403.14607, 2001.00021, 2305.04954, 2510.09520, 1111.1208. Not verified: Ambainis et al. 1999; the exact game and bound in 2110.04277; the explicit constants of the 2509.07255 bound; live Heron r2 calibration.

[Implementation notes filled after implementation.]
