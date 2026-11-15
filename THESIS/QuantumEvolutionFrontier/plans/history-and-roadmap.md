# From a quantum tree to quantum virtual tumours: full history, roadmap, and where it points

**Status:** exploration draft, 2026-11-08. **Author of the work:** Peter Jas. **Drafted with:** Claude (Opus 5.5).
**Companion:** `paper-concept.md` (first framing). This document supersedes its §8 with the paper framing in §7 below.

**Sources:**
- git history of the whole repo: 165 commits, 2026-07-08 → 2026-11-08;
- code in `QuantumLife/`, `artificial-life/`, `THESIS/CriticalQuantumLife/`, `THESIS/NPQuantumAdvantage/` and
  `QuantumPhantoms/` (MVP `code/` + RE pipeline);
- every conclusion and run log: QuantumLife conclusions, `RUNLOG_MONTH1–4`, `CONCLUSION_MONTH4`, `RUNLOG_PJ`,
  `MOTILE_CONCLUSION`, `how_is_this_study`, the QuantumPhantoms README, F6 plan and `currentRun`;
- hardware run files in `research_runs/`.

Numbers are quoted from those files. Where I re-read code and disagree with a doc, I say so.

---

## 0. The whole story in one paragraph

In four months Peter went from *"a tree grown by a quantum computer"* to a pipeline that puts certified quantum
draws into real Siemens-scanner CT. On the way he made, on real IBM hardware, almost every mistake the
quantum-biology field makes in print, and caught each one with a control experiment:

- **Diversity is blind to entanglement.** QuantumTree, July.
- **Diagonal readouts have exact classical surrogates.** Months 1–3: QDEP's C(g).
- **A correlation can be depth or crosstalk, not entanglement.** QuantumTree serial C(d).
- **Logical depth is not the figure of merit.** Teleport routing won once and was refuted three times.
- **Faithful biology destroys the signal.** Dissipative death: W* collapses from 24 to between 4 and 8.
- **Entangled is not the same as hard.** GHZ spine at belief-propagation bond dimension χ = 2; tree-shaped genealogies.
- **A one-basis test is not an entanglement certificate.** Found today in `qalife.py`; see §5.2.

Each correction moved the claim one rung up an honest ladder (L0 → L1 → L1′) and left a design rule. The rule that
matters most: the germ/soma split, which raises the signal from 0.12 to 0.90. The endpoint today: **every quantum
signal that survives on hardware is classically easy, and every circuit that might be hard does not survive.**
That gap, measured, is the real state of the field. It is also the paper.

---

## 1. Timeline map

```text
2026-07  ──┬── Phase 0  RANDOMNESS            Bell-pair QRNG on ibm_fez (07-07) → Q-EaaS service → calibration-guided QRNG
           │                                   hands on: certified entropy, signed receipts, calibration snapshot
2026-07  ──┼── Phase 1  QUANTUM TREE          108-q tree (07-15) → C(d) study z≈10 (07-17) → teleport bond wins at d=12 (08-17)
           │                                   hands on: layout.best_chain, "diversity is blind", B0 hardware-floor control
2026-08  ──┼── Phase 2  QDEP months 1–4       reproduce 2018 (fez) → g*=4 → Δg*=0 (cloner is a classical copier)
           │                                   → founder fix, LIFE g*=14 (diagonal) → teleport refuted → virus flip STOP
           │                                   → Month 4 rebuild: full 2018 model, off-diagonal witness, W=24 (48 q)
           │                                   hands on: "diagonal ⇒ classical surrogate", chain-quality gate
2026-09  ──┼── Phase 2b SIDE THESES           NP √2 advantage map (09-06: "advantage is the exception")
           │                                   Critical Quantum Life (closed vs yoked loop, canary, sandpile)
2026-09  ──┼── Phase 3  QALIFE EPIC (pivot)   P1 baseline → P2 ceilings (W*=24 unitary, damping W*∈[4,8))
           │                                   → PJ0 germ/soma W=50 (100 q) → PJ1 collision (42 q) → web spectacle
           │                                   → PJ2.2 lattice ("quantum walk in ALife clothing") → PJ2.3 deleted
           │                                   → PJ2.4 motile ghz2 1.96 (09-27) → PJ2.5 DD lever (10-19/24, HW pending)
           │                                   hands on: germ/soma rule, ghz2 two-basis certificate, "biology is the spec"
2026-10  ──┼── Phase 4  QUANTUM PHANTOMS      scaffold (10-26) → RE W + 8 letters in parallel (10-28/29)
           │                                   → first chain B→C→D→A→E→F→web (10-31) → D-SCALE live: CHSH 2.733,
           │                                     QCA L1 marginal, GHZ-28 fail, PMD lose (10-31) → exec page (11-03)
           │                                   → F6 plan: split jobs, distance-to-L2 per run (11-04) → current run (11-08)
2026-11  ──┴── NOW                            this document: the audit, the gap, the road
```

**Scale of the work:**
- **Code:** about 45,000 lines of Python:

  | Project | Lines |
  |---|---|
  | QuantumLife | 3.2 k |
  | artificial-life | 11.0 k |
  | Critical Quantum Life | 5.0 k |
  | QuantumPhantoms MVP | 10.7 k |
  | QuantumPhantoms RE pipeline | 15.6 k |

- **Hardware run files on disk:** about 145:
  - QuantumLife: 65 (36 `ibm_kingston`, 29 `ibm_marrakesh`);
  - artificial-life: 66 (50 kingston, 16 marrakesh);
  - Critical Quantum Life: 10 (kingston);
  - QuantumPhantoms: 4 live D-SCALE jobs.

  The Months 1–3 `ibm_fez` / `ibm_marrakesh` runs were removed from git in the 09-11 "big simplification".
- **Backends used:** `ibm_fez`, `ibm_marrakesh`, `ibm_kingston` (all Heron r2, 156 q).

---

## 2. Phase by phase

### Phase 0: randomness (2026-07-07 → 07-24)

| Project | What was built | What it handed on |
|---|---|---|
| `ErrorDetectionVSRawBits/` | Bell-pair QRNG vs Hadamard-noise QRNG on `ibm_fez` and `ibm_marrakesh` (07-07), NIST battery (`nist_pure.py`, `qrng_compare.py`) | The first hardware job. The idea that a Bell test, not "it came from a qubit", is what makes randomness quantum |
| `qrng-eaas/` (40 commits) | FastAPI + Next.js entropy-as-a-service. QRNG seeds an HMAC-DRBG (SP 800-90A); signed, offline-verifiable receipts; ML-KEM seeds; agent-first API, MCP registry | Provenance as a product. Later the mutation-angle source for QALife (fail-closed on hardware), then C and G in QuantumPhantoms |
| `CalibrationGuidedHighYieldQRNG/` | Does one calibration snapshot predict qubit quality and mid-circuit harvest depth? | Calibration-aware qubit selection, which became `layout.best_chain` and the fail-closed chain-quality gate behind every later run |

**Lesson:** randomness from a qubit is not evidence of anything quantum. Only a Bell-type test is (L0).

### Phase 1: QuantumLife, the quantum tree (07-15 → 08-18)

**07-15, art.** `qtree.py` + `genome.py`: a 108-qubit genome (18 slots × 6 bits), a CX + CRX(0.7) chain entangler,
environment rotations, and a feedback rule `θ ← θ + 0.18(2p−1)`. Every generation is one Heron job. Viewers:
`quantum_tree.html` and the pixel grove. The "honest version" chapter of the README already separated "2^108
amplitudes cannot be stored" from "the signature must be measured". The first claim is not a hardness argument; see
failure mode F7 in §5.

**07-17, research.** `research_qtree.py` added the connected correlation C(d), the normalised c(d) and ξ, plus three
arms: classical sim null, a `--layers 0` hardware floor (B0), and `--layers 2`.

| Arm | Result |
|---|---|
| Hardware, 2 layers | c(1) = −0.077 |
| Sim null | 0.000 |
| B0 floor | +0.015 |

That is z = −9.9 vs the sim null and −10.6 vs the floor. The dose response flips sign at L = 2 and is noisy at L = 4.
**Honest verdict, already written then:** "imprints a causal correlation signature, not yet entanglement". The
serial ladder is about 800 deep and confounded with crosstalk. The brick-wall redesign
(`research_qtree_brickwall.py`) was built as the decisive test. **I found no recorded result for it.**

**07-24.** LaTeX write-up started; CalibrationGuided restructured.

**08-17, teleport.** `research_qtree_teleport.py` vs `research_qtree_swaplr.py` on 102 qubits, `ibm_marrakesh`:
- **d = 12:** a heralded teleported CNOT gave a stable negative bond correlation, 11 of 11 generations negative,
  about −0.065 to −0.139.
- **d = 36:** noise.
- **SWAP ladder (depth 31):** at the floor and wrong-signed.
- **Exact sim (`sim_ideal_sign.py`):** the ideal sign is negative, so teleport was faithful and SWAP corrupted.

This was the **only "win" of the summer**. `thesis/teleport-routing-crossover-thesis-assessment.md` later
showed the proposed law is half right: it omits the O(d) Bell-pair distribution cost. It is also not new, since
dynamic-circuit vs SWAP is published.

**08-18.** `demo_qtree.py`, a small-scale model for the web.

**Lessons handed on:**
- diversity (mean entropy) is blind to entanglement, so correlations must be measured;
- every signal needs a hardware floor (B0), not just a sim null;
- teleport wins only when one long bond is depth-fragile and gate error ≫ readout error.

### Phase 2: QDEP, Months 1–4 (08-19 → 08-30)

The plan (`QDEP_Living_Genealogies.md`, epic qdep-1): reproduce Alvarez-Rodriguez et al. 2018, find the generation g*
where coherent inheritance beats a measure-and-resend surrogate, and show teleport beats SWAP.

| Month | Code | Hardware | Result | Verdict |
|---|---|---|---|---|
| 1 | `stage0_reproduce.py`, `stage1_temporal.py`, `stage2_scale.py`, `stage3_teleport.py` | `ibm_fez`, ~60 s | 2018 lifetime reproduced (η ≈ 0.9, fidelity ≥ 0.996 in sim); **g* = 4** at G = 8; teleport Δg* = 0 but a 1.7× bonded-pair edge | "Coherent ≈ ideal ≈ 0 in the discriminating basis: the Ry+CX clone copies a classical value" |
| 2 | `--readout midcircuit`, larger `--bond-dist` | `ibm_fez`, ~110 s, aborted 08-24 | Depth mechanism confirmed (SWAP 74, teleport flat at 39), but **C(g ≥ 1) ≈ 0 on every arm**: Δg* = 0 | "More routing is not the lever. The cloner is." |
| 3 | `--founder`, `--eta`, `--defer-readout`, `--quantum-only` | `ibm_marrakesh` | Founder fix gives a deep C(g): **LIFE g* = 14 at G = 14** (k = 3); full teleport ladder: **SWAP wins** in every configuration (readout_max 0.214, herald keeps 1.6 %) | Teleport dropped on Heron r2 |
| 3½ | `stage5_fliptest.py` (stone-wall virus, P0) | `ibm_kingston` 08-26 | Teleport must clear 2σ while SWAP is buried at far d | **Kill gate: STOP** (no flip) |
| 4 | `stage4_qalife.py` + `stage4_scale.py` (later `qalife.py`, `run_qalife.py`) | `ibm_marrakesh`, `ibm_fez`, `ibm_kingston` 08-24/25 | The full 2018 model (founder, replication, mutation, phenotype, damping or unitary death, SWAP interaction), verified operator by operator; the claim moved off the diagonal to ⟨X^⊗W⟩. **W = 24 (48 q)**, +0.038 vs 2σ = 0.032 (marginal), W = 32 dead | "An honest scale and faithfulness milestone, no quantum speed advantage" |

**The structural refutation (Month 4, proven in code).** Clone, damping and SWAP act only on the diagonal, so
`classical_surrogate_z` reproduces the phenotype ⟨σz⟩ exactly. All of Months 1–3 measured a classical quantity.
**This is the single most important negative in the whole body of work.** It is the same mistake as most
"quantum life" demos in print.

### Phase 2b: side theses (08-31 → 09-09)

- **NP Query-Advantage Map** (`THESIS/NPQuantumAdvantage/`, T1 on 09-06): five obscure NP problems placed on the "√2
  line". A Grover quadratic speedup survives only if the best classical exponent satisfies c > 0.5. Result:
  1 survivor, 1 borderline, the rest collapse. **This is where "advantage is the exception; measuring it is the
  result" was born.** It is also the template for an advantage *map* rather than an advantage *claim*.
- **Critical Quantum Life** (`THESIS/CriticalQuantumLife/`, 5 k lines):
  - closed-loop vs yoked-control Darwinian population, DishBrain / free-energy framing, sandpile criticality (σ ≈ 1,
    α ≈ 1.5) gated by a witness;
  - a zero-credit calibration poller ("canary") verified on `ibm_kingston`;
  - batch circuits submitted;
  - most verdict slots in the run logs are still empty.

  It handed on the **yoked control**, the cleanest way to prove that a feedback loop does something.

### Phase 3: the QALife Darwinian-richness epic (09-09 → 10-24)

**09-09, the "big pivot".** Stages 0–3 and 5 moved to `code/backlog/`; `stage4_*` renamed to `qalife.py` /
`run_qalife.py`. The QDEP epic archived as `OLD_`. New epic: `epic-qalife-darwinian-richness.md`, with stages R0
refactor, P1 baseline, P2 scale ceiling, P3 richness, P4 phase diagram. The scoring has two axes kept separate:
*biological richness added* vs *witness-survival cost*.

| Date | Stage | Hardware | Number | What it meant |
|---|---|---|---|---|
| 09-11 | P2 unitary | `ibm_kingston` | **W* = 24 (48 q)**, k = 2σ | Original design ceiling located |
| 09-11 | P2 damping | `ibm_kingston` | k = 3σ through W = 4, dead by W = 8; depth ceiling 5 generations | Faithful dissipative death is worse in every way |
| 09-12 | **PJ0 germ/soma** | `ibm_kingston` | 2×2 ablation: separable phenotype 0.77–0.90 vs entangled 0.08–0.12; `natural+separable` stays above the null at 3σ to **W = 50 (100 q)** (⟨X^⊗W⟩ = 0.058); stopped at W = 54 by the chip layout (needs 108 clean qubits, longest chain 107) | **The design rule:** isolate the mortal or measured subsystem from the coherent register. Fewer 2q gates, 2 qubits per individual instead of 3, one decoherence channel removed by construction |
| 09-13 | PJ1 collision | `ibm_kingston`, 42 q | Bodies meet (overlap 0 → 0.72) while each genealogy keeps its signal | Multi-organism tiling works |
| 09-13/15 | Web | — | `web/index.html`, `spectacle.html`, three conclusion pages | "First interactive QALife visualisation" (prior-art check done) |
| 09-23 | PJ2 / 2.1 | `ibm_kingston` | Solo vivarium, gradual biology | Vivarium primitives |
| 09-26 | PJ2.2 lattice | `ibm_kingston` (3×3) | Movement by excitation-conserving quantum walk | Self-verdict: **"a quantum walk in ALife clothing"**; the motion is classically reproducible |
| — | PJ2.3 | — | Labelled hardcore lattice | Deleted as a bad move (a recorded negative) |
| 09-27 | **PJ2.4 motile** | `ibm_marrakesh`, 16 q | Movement, metabolism (`ccx`), selection (`cry`), metabolism-gated birth, unitary aging death; **`--certify ghz2`: ⟨XX⟩+⟨ZZ⟩ ≈ 1.96 (separable bound 1)**, certified generations 3–5 | The first proper two-basis entanglement certificate on a living-organism circuit |
| 10-19/24 | PJ2.5 germ DD | sim | `--dd`, `--dd-ab`, `kept_fraction = 1`; sim delta 0 (correct) | First mitigation lever; **hardware A/B pending** |

**Framing doc (`plans/how_is_this_study.md`):**
- the study is informatics, not biology: the biology is the *specification*;
- the contribution is the circuit architecture and its measured consequence;
- it lists the five gaps between a master's thesis and a paper: GME certification, repeats, width-vs-depth
  confound, measuring the aging and DD features, positioning against GHZ-at-scale work.

### Phase 4: QuantumPhantoms (10-26 → now)

**Context.** Siemens wants a sellable healthcare quantum-computing concept, not security. The name went from QSC (retired 10-30)
to *Quantum Virtual Tumors* (pitch) and *Quantum Phantoms* (thesis).

**RE pipeline (10-28/29, parallel worktrees per letter):**
- W foundation: frozen contracts and stubs;
- A placement: #18 NOT matched at n = 9;
- B mapping: BN → circuit compiler, marginals within 0.01; QeMCMC;
- C certificate: Pironio entropy, 40.8 vs 42 bits; Toeplitz extractor; beacon chain;
- D quantum growth: dynamic lineage, PMD memory machine, Goldilocks QCA, BP adversary;
- E growth: Kansal–Torquato + Pixel2Cancer, 3 of 4 stages matched;
- F render: volume +0.25 %, NAEOTOM #17 not matched;
- G provenance: receipt, ledger, tamper test;
- H validation: CHO / MRMC, AI-Rad protocol;
- INT: chain runner, chain not closed.

**MVP:**
- F1 rulebook → 9-qubit circuit → certified draw;
- F2/F3 tiles and web;
- F4 Mode-A QALife arm;
- F5 Siemens LIDC-0481 host + E growth + F render;
- D-SCALE 40/100/120-q families with a survive-vs-simulable map.

**10-31, first live chain** (run `dscale_live_100_20261031-170957`, `ibm_marrakesh`, 60 qubits actually used):

| Experiment | Result |
|---|---|
| CHSH (12-tumour roll on the QPU) | **S = 2.733 (L0)** |
| ch-qca, 23 sites | Pair negativity passes on 1 of 4 edges, p_bonf 0.046 (**L1, marginal**) |
| ghz-spine, 28 q | GHZ fidelity **F = 0.055, fails** the GME bound 0.5 |
| pmd-bank | Memory gap −2.9 × floor: **the classical 2-bit model wins** |
| Survive-vs-simulable map (smoke) | **Goldilocks zone (alive ∧ BP-hard) empty** |

**11-04, F6 plan.** Split the three experiments into separate jobs; anatomy-driven placement; CT-conditioned QCA;
and **"distance to L2" per run, defined as t* − t_pass**:
- t* is the smallest depth at which BP needs χ > 16;
- t_pass is the deepest depth where the witness still passed.

This is the first operational L2 metric in the repo.

**11-08.** `currentRun` explains the live run in plain words: "the quantum part makes every case traceable and
replayable; it does not make the images more realistic".

---

## 3. How the threads connect (what each phase gave the next)

| Thread | Origin | Becomes | Ends up as |
|---|---|---|---|
| Certified randomness | Bell QRNG (07-07), Q-EaaS | QALife mutation angles from certified entropy | C certificate, CHSH S = 2.733, G lineage record; **claim L0** |
| Calibration awareness | CalibrationGuided QRNG | `layout.best_chain`, chain-quality gate | D-SCALE `allocate`, T1/T2 gate, Pauli-twirled noise model |
| "Measure correlations, not diversity" | QuantumTree C(d) | QDEP C(g), then "diagonal = classical", then off-diagonal witness | ghz2 two-basis certificate, then the claim ladder L1 |
| Routing | QuantumTree teleport win | QDEP: refuted ×2; virus flip STOP | D-2 dynamic lineage refuted on Heron r2; "error balance, not logical depth" |
| Faithful biology | 2018 reproduction | Damping collapse, then germ/soma | D design rule: coherent genotype register, phenotype expressed classically |
| Advantage maps | NP √2 map | "Advantage is the exception" | Survive-vs-simulable map, distance to L2 (F6) |
| Controls | B0 hardware floor | Matched separable null; yoked control | Every quantum number ships its classical baseline + BP number + label |

---

## 4. What exists today (state of the art inside this repo)

| Rung | Best hardware evidence | Where |
|---|---|---|
| **L0** provenance | CHSH S = 2.733, one job, 2 q | QuantumPhantoms D-SCALE 170957 |
| **L1** entangled generative state | ⟨XX⟩+⟨ZZ⟩ ≈ 1.96 on 2 germ qubits; QCA pair negativity (marginal) | PJ2.4 motile; D-SCALE ch-qca |
| L1 at scale (claimed) | ⟨X^⊗W⟩ − ∏⟨X_i⟩ to W = 50 | PJ0. **Not an entanglement certificate; see §5.2** |
| **L1′** memory advantage | none (gap below floor) | D-5 / pmd-bank |
| **L2** classical hardness | none; Goldilocks zone empty | D-SCALE maps (smoke, truncated) |
| **L3** useful advantage | none; fault-tolerant only | — |

---

## 5. The audit: why the standard quantum-biology hype fails, demonstrated on this repo's own hardware

Two different things travel under "quantum biology" and must be kept apart:

1. **Quantum effects in living matter.**
   - Real: radical-pair magnetoreception, enzyme tunnelling, excitation transfer in photosynthesis. All molecular
     and short-lived.
   - Over-sold: long-lived electronic coherence as the reason photosynthesis is efficient. Engel et al. 2007 started
     it; later analyses attribute the long-lived beats largely to vibrational / vibronic motion (Duan et al., PNAS
     2017, verify).
   - Not supported: quantum effects at the cell, tissue or brain level (Tegmark 2000 estimates decoherence in neural
     tissue at about 10⁻¹³–10⁻²⁰ s).

   **Tumours are not quantum.** This repo never claims they are.
2. **Quantum computing applied to biology.** This is what this work is about, and where the hype is loudest:
   "quantum computers will model evolution / cure cancer / design drugs".

### 5.1 Nine failure modes (each one made, caught and fixed in this repo)

| # | Failure mode | Typical hype sentence | Caught here | The test that catches it |
|---|---|---|---|---|
| F1 | **Diagonal readout**: counts, growth curves and lifetimes are Z-basis and have exact classical surrogates | "Quantum cells divide and die on a quantum computer" | QDEP Months 1–3 C(g); alive counts; F4 fate dial = biased coin (`analysis-stages-B-D-F.md` §0.1) | Build the classical surrogate fed the same probabilities; if it matches, there is no claim |
| F2 | **Diversity or entropy as evidence** | "Rich, unpredictable quantum behaviour" | QuantumTree art metric | 108 independent biased coins give the same diversity as an entangled register |
| F3 | **Weak or wrong null** | "Beats the classical model at 10σ" | QuantumTree sim null (smoothing surrogate); PJ0 null = Z measure-and-resend | The null must be the *set of all separable states*, not one convenient surrogate |
| F4 | **Confound with depth or crosstalk** | "Entanglement signature observed" | QuantumTree serial C(d), depth ~800 | Hardware floor (B0), dose response, brick-wall control at matched physics |
| F5 | **Single-basis witness** | "100-qubit entanglement" | PJ0 W = 50 (§5.2) | Two-setting GME witness (Tóth–Gühne 2005) or GHZ fidelity > ½ |
| F6 | **Entangled = hard** | "Impossible on a classical computer because it is entangled" | GHZ spine (stabilizer, BP χ = 2); genealogies are trees (treewidth ≈ 1) | Run the classical attack portfolio: stabilizer, treewidth contraction, MPS, BP, Pauli paths |
| F7 | **Hilbert-space size = hardness** | "2^108 amplitudes, more than atoms in …" | QuantumTree README "scale" sense | Hardness is the *cheapest* classical method, not the state-vector size; shallow 1-D circuits are MPS-cheap |
| F8 | **Logical depth or qubit count as figure of merit** | "Constant-depth teleportation beats SWAP"; "100 qubits" | Teleport: won once, then refuted ×3; 108/100-q headlines | Effective error budget on *this* calibration (readout ≫ 2q on Heron r2) |
| F9 | **Simulated certification** | "Certified quantum randomness" (from a simulator) | CLAUDE.md gate; MVP C before the live run | Only a hardware Bell test with S > 2 in the same job counts |

**For drug and medicine claims, add three that live outside the circuit:**
- **Loading and readout.** The input data must be loaded and the answer read out (Aaronson, "Read the fine print",
  Nat. Phys. 2015).
- **Quadratic speedups are eaten by error-correction overhead** for a long time (Babbush et al., PRX Quantum 2021).
- **Dequantization.** Many quantum machine-learning speedups have classical "dequantized" analogues (Tang 2019).
  Variational models hit barren plateaus (McClean et al. 2018).

The headline hardware "utility" experiment of 2023 (Kim et al., Nature 618, 500) was reproduced classically within
weeks with tensor networks and belief propagation (Tindall et al., PRX Quantum 2024; others, verify). That is
failure mode F6 at the top of the field.

**This table is the strongest asset of the paper.** It is not an outsider's critique. It is a self-audit with
hardware data, a fix for every failure mode, and dated commits.

### 5.2 The finding from re-reading the code (F5, applied to PJ0)

`artificial-life/code/qalife.py:212–241` treats joint = ⟨∏ x_i⟩ in the X basis as the witness and separable = ∏⟨x_i⟩
as the null.

- **What the test excludes:** the Z measure-and-resend surrogate.
- **What it does not exclude:** the separable state ½(|+…+⟩⟨+…+| + |−…−⟩⟨−…−|), which gives ⟨X^⊗n⟩ = 1 for even n
  with every ⟨X_i⟩ = 0.
- **What W = 24 and W = 50 therefore establish:** "connected n-point X-correlation beyond the measure-and-resend
  surrogate", not entanglement.
- **What does carry an entanglement claim:** the motile ghz2 (two bases, two qubits), the QCA negativity, and CHSH.
- **The only n-qubit GME test so far** (28-q spine) failed.

The germ/soma *ablation* still stands as a relative result. Same test, same chip: severing `cx(g,p)` raises the
signal from 0.12 to 0.90.

**The fix is cheap:** the Tóth–Gühne two-setting witness uses exactly the X^⊗n and Z^⊗n settings that `--certify
ghz2` already measures.

---

## 6. The road to quantum advantage in this field, right now

### 6.1 Why faithful evolution circuits are classically easy (the structural core)

Three reasons, each visible above:
1. **Biology gates are classical on the diagonal** (F1).
2. **Genealogies are trees.** Contraction cost is exponential only in treewidth (Markov & Shi 2008), so faithful
   phylogenies contract in polynomial time (F6).
3. **Mutation–selection equilibrium is the ground state of a sign-free (stoquastic) transverse-field Ising
   chain** (Baake, Baake & Wagner, PRL 78, 559, 1997). That is the regime where classical Monte Carlo usually
   works.

**So:** the more faithfully a circuit implements classical evolution, the more classically simulable it is.
Hardness has to come from somewhere else. Two candidates:
- interaction loops (competing lineages on 2D tissue lattices) combined with non-Clifford, non-stochastic coupling.
  The price is "quantum excess" that is not biology.
- asking the classical biology a question that is expensive classically, such as rare events or exact marginals over
  2^L genotypes. This is the algorithmic route.

### 6.2 The road, by time horizon

| Horizon | Hardware | What is honestly reachable | This repo's job |
|---|---|---|---|
| **Now (2026–28)** | Heron r2/r3, Nighthawk, 100–156 noisy qubits | L0 certified randomness / provenance; L1 witnesses at modest width (GME width to be measured, E1); L1′ memory advantage for small process models (Gu et al. 2012), not yet achieved here | Measure the frontier: S × H × Φ map, D_L2 per run, GME width, forecast ε* |
| **Early fault tolerance (≈ 2029–32, vendor roadmaps, verify)** | ~100–200 logical qubits | First chances for L2-type cells in bio-structured circuits on loop lattices; small chemistry beyond exact classical reach | The map becomes a benchmark: does the predicted Goldilocks cell open at the predicted error rate? |
| **Fault tolerance (2032+)** | 10³+ logical qubits | L3 where physics is native: **drug–target binding for resistance mutations** (quantum chemistry); quadratic Monte Carlo for rare-resistance probabilities; linear-ODE solvers on genotype space (case by case) | The two-scale response map: molecular layer (quantum) → fitness parameters → population layer (classical, later quantum-accelerated) |

### 6.3 Measuring how close we are (objective, falsifiable)

- **Three coordinates per run:**
  - S, alive: k-sigma of a *proper* witness;
  - H, hard: log₁₀ of the cheapest classical cost from a fixed attack portfolio;
  - Φ, faithful: 1 − TVD to the classical biology model at small n.
- **D_L2** = max H − budget over the alive and faithful cells. F6's operational version is t* − t_pass.
- **Forecast ε*:** the error per layered gate at which the first alive-and-hard cell appears. ε_now / ε* is how many
  hardware generations remain. It is checkable on every new chip.

**Today:** D_L2 < 0 everywhere measured.

---

## 7. What the projects point to, and the paper (v2)

### 7.1 Where it points

1. **An instrument, not an organism.** The lasting product is the measurement apparatus: witness rungs, matched and
   floor controls, the survive-vs-simulable map, D_L2 and ε*. It can be pointed at any quantum-biology claim and any
   new chip.
2. **Design rules that move the frontier:**
   - germ/soma isolation;
   - fewest 2q gates per individual;
   - unitary over dissipative death;
   - error-balance-aware routing;
   - DD on the coherent register only;
   - two-basis certificates.
3. **The honest job for quantum computing in medicine now:** provenance (L0) and correlated-lineage sampling (L1).
   Later, molecular chemistry feeding classical evolutionary models (L3). That is the "classical-strong engine with a
   measured quantum socket" already used for the Siemens pitch, now with a scientific argument behind it.
4. **The digital-twin long view.** Each stage is one twin layer. The quantum layer earns its place rung by rung, and
   the map says when.

### 7.2 Recommended paper

- **Tone:** the content can be blunt, but "nonsense" in the title will cost reviewers. Use "audit" or "field guide".
  The evidence does the work.
- **Working titles:**
  - *Entangled is not alive, alive is not hard: a hardware audit of quantum models of evolution, and the road to
    advantage*
  - *Quantum artificial life without the hype: nine tests, 100-qubit hardware data, and where advantage could
    actually come from*
- **One question:** what does it take for a quantum-computer model of a biological or evolutionary process to beat a
  classical computer, and how far is current hardware from that?

**Claims:**
1. **C1, audit:** quantum-biology computing claims fail one or more of nine tests (§5.1). Each is shown with a
   literature example and with this repo's own hardware run plus its fix.
2. **C2, structure:** faithfulness and hardness pull apart for three reasons: diagonal, tree, stoquastic.
3. **C3, measurement:** the S × H × Φ map and D_L2, with all hardware points placed. D_L2 < 0 today.
4. **C4, road:** the exits (loop lattices, algorithmic encodings, molecular layer), a forecast ε*, and a two-scale
   medication-response outlook labelled preliminary.
5. **C5, the job that exists now:** procedural content generation (trees, organisms, tumours, cohorts) needs no
   computational advantage. It needs unpredictability, replay, structure and a record, which L0 and L1 already give.
   This keeps the paper from being only negative: the hype fails, but here is what quantum computers can honestly
   generate today, and here is how to label it (§7.4).

**Positioning (quick search, 2026-11-08; a full literature search is still needed):**
- **"Quantum computing for biology is hyped" is already published.** Arcieri et al., *Front. HPC* 2026: a
  systematic review of 53 bioinformatics studies, almost all simulated or toy-scale, none showing advantage. Cordier
  et al., *J. R. Soc. Interface* 2022: a quantum-advantage framework for biology and medicine. Outeiral et al., *WIREs*
  2021. A 2026 *Quantum* history of advantage claims. Neither of the first two covers quantum artificial life,
  entanglement witnesses or procedural generation.
- **So the critique alone is not the novelty.** Lead with what is new:
  - QAL hardware data at 48–100 qubits (the 2018 origin used 5 qubits and already conceded that σz readouts are
    classical);
  - the germ/soma rule;
  - the measured GME width;
  - the faithfulness–hardness argument for evolution models;
  - the distance-to-L2 map;
  - the provenance ladder for procedural content.
- **Possible competitor to check:** a Zenodo record titled *Quantum Artificial Life Takes Its First Step on an IBM
  Quantum Computer* (zenodo.org/records/21469161). Its author and content are unread.
- **Quasispecies ↔ transverse-field Ising on hardware:** the quick search found no prior work. A proper search is
  needed before calling it new.

**Owned contributions:**
- the claim ladder L0–L3 plus witness rungs;
- the nine-test audit, backed by hardware;
- the germ/soma design rule (0.12 → 0.90);
- the measured GME width (E1);
- the empty Goldilocks zone;
- D_L2 / ε* as a benchmark.

**New experiments needed** (simulation first; hardware by Peter):
- **E1:** Tóth–Gühne GME sweep, W = 4…50, ≥ 3 repeats.
- **E2:** attack portfolio on every family.
- **Optional:**
  - E7, the classical-twin content test (§7.4; cheap, simulation and render only, uses existing H tools);
  - E3, faithfulness Φ;
  - E4, loop-lattice arena;
  - the brick-wall A/B that QuantumLife never closed;
  - the PJ2.5 DD A/B.

**Structure:**
1. Two meanings of quantum biology.
2. The ladder and witness rungs.
3. The nine-test audit.
4. Why faithful is easy.
5. The map, D_L2 and the hardware data.
6. Exits and road.
7. The medicine outlook.
8. Threats to validity.

**Minimum that publishes:** §§1–5 from existing data plus E1.

**Venues:** arXiv first (the timestamp). Then IEEE QCE 2027, ALIFE 2027, *Quantum Science and Technology* or *PRX
Life* (verify scope and deadlines).

**Relation to the existing plan** (`QuantumPhantoms/plans/publication-plan-3-papers.md`):
- P1 (the QALife arc) becomes the empirical companion.
- This paper is the position-plus-audit paper that frames P1 and P3.
- P1's headline must switch to the E1 GME width either way.

### 7.3 Ownership

- **The timestamp:** an arXiv preprint with Peter as first author, posted before the Siemens start date. The git
  history (dated commits since 2026-07-07) is supporting evidence.
- **Contract:** check the IP and background-IP clause of the Siemens or thesis agreement (verify).
- **Siemens-specific content** (CT pipeline, product names, cohorts) stays out of this paper.

### 7.4 Keeping the light on: quantum procedural content generation

**Procedural generation is the common thread of all three projects.**

| Project | Generated content |
|---|---|
| QuantumTree | Trees: `qtree.py`, the pixel grove, `demo_qtree.py` |
| QALife | Organisms: vivaria, `motile_life.html`, the spectacle page |
| Critical Quantum Life | A population you can poke: the ops console |
| QuantumPhantoms | Tumours and whole cohorts: F2 procedural renderer, F5 grown renderer, QCA seed shapes, growth player |

The audit does not remove this thread. It tells you how to state it so that it survives review.

**Why procedural generation is the right home now.** A content generator is judged on four things:
1. unpredictability (nobody chose the content);
2. replay (the same seed gives the same content);
3. controllable structure (correlated families, lineages, statistics that follow a rulebook);
4. a story the viewer can check.

None of the four needs L2. L0 and L1 cover them today. This is the one application in the repo where quantum has a
legitimate job **without** a computational-advantage claim.

**The honest ladder for quantum procedural generation:**

| Level | What the content can claim | Status here |
|---|---|---|
| **P-L0 certified seed** | Nobody chose it, not even the author. A Bell test in the same job (S > 2), the seed hash gives an exact replay, and a rejected draw is logged. Use: unbiased synthetic test cohorts (no cherry-picking for AI validation), fair game or art content, audit | **Done on hardware:** CHSH S = 2.733, 12 tumours rolled on `ibm_marrakesh` |
| **P-L1 content with a birth certificate** | The job that produced the content also passed an entanglement witness, so the generator was provably entangled when this content was made. The pixels themselves are classical | Motile ghz2 (1.96); QCA seed shapes per tumour (marginal). GME-wide lineages wait on E1 |
| **P-L1′ compressed generator** | A process generator (growth sequences, lineages) that needs less memory than any classical generator of the same process (Gu et al. 2012) | Not achieved (D-5 below the floor) |
| **P-L2 content no classical computer could have produced** *(speculative)* | Drawn from a distribution outside classical sampling reach, verified via the certificate and the attack portfolio. This is a claim about the *generator*, not the look: a single sample from a hard distribution looks like noise | Blocked until D_L2 > 0. Possibly the first *visible* artefact of L2 |
| **Never** | "More realistic, beautiful or organic because quantum" | Quantum Blur (Wootton), dissected in RE B #03: a classical Gaussian reproduces it at r ≈ 0.99; where it differs, it scrambles non-physically. **Rejected** |

**Rules for honest quantum procedural content** (the nine tests turned into a spec):
- Every generated item ships its claim level, its job ID, its witness value (or "none") and its seed hash.
- **Classical twin.** Every viewer offers the same content generated by a classical sampler fed the same
  probabilities, side by side. If the two look the same, that *is* the honest point: the quantum value is in the
  record, not in the pixels.
- Correlated families (sibling nodules, clone sub-regions, branch clusters) may be drawn from one entangled lineage
  state. The claim is P-L1 for the family, never "the shapes are quantum".

**One new experiment that makes this a result (E7, classical-twin test):**
- **Design:** render quantum-seeded and PRNG-seeded content from the same rulebook. QuantumPhantoms H already has
  radiomics, observer models and a Turing-test kit (`H_analysis/src/turing_kit.py`, `radiomics_cmp.py`). Test
  whether metrics or observers can tell them apart.
- **Expected:** no difference. That is a publishable null that confirms the value is provenance, not appearance.
- **If a difference appears:** it is a bug or a bias in the sampler. Either way it is reported.

**What this does for the paper and for Siemens:**
- **The paper:** keeps a constructive half. The hype fails on advantage; procedural generation with certified
  provenance is real now and moves up the ladder as hardware improves.
- **Benchmarking:** the same generator re-run on each new chip turns the S × H × Φ map into something people can see.
  The content is the outreach face of the measurement.
- **Siemens:** synthetic CT cohorts are procedural content with a lineage record. That is the bridge: same argument,
  medical content, without putting Siemens material into this paper.

---

## 8. Open items found while reading

| Item | Where | Why it matters for the paper |
|---|---|---|
| Brick-wall A/B never recorded | QuantumLife `research_qtree_brickwall.py` | Closes F4 with a clean example |
| PJ0 W sweep is N = 1; witness is single-basis | `artificial-life/research/pj0_germsoma/` | E1 + repeats; the headline changes |
| PJ2.5 DD hardware A/B pending | `RUNLOG_PJ.md` §5 | First measured mitigation lever (optional) |
| Critical Quantum Life verdicts empty | `THESIS/CriticalQuantumLife/plans/SANDPILE-runlog.md` | Could supply the yoked-control example (optional) |
| D-SCALE maps truncated (smoke) | `QuantumPhantoms/research_runs/_dscale/survival_*` | The full maps settle "Goldilocks empty" (runbook Part A) |
| D-5 gap below floor | `pmd_retune.json` | L1′ is the only provable NISQ advantage; needs re-tuning |

---

## 9. Numbers ledger and page budget (for a 6–8 page paper)

**Legend:**
- **HAVE** = a hardware or exact number already in the repo;
- **CHEAP** = a simulation or analysis on existing data, no QPU;
- **NEED-HW** = a new hardware run (Peter);
- **LIT** = a literature number (verify).

| Paper section | Hard numbers | Status |
|---|---|---|
| 1. Two meanings of quantum biology | Neural decoherence 10⁻¹³–10⁻²⁰ s (Tegmark 2000); photosynthesis reassessment (Duan 2017) | LIT |
| 2. Ladder + witness rungs | Bounds: CHSH 2; ⟨XX⟩+⟨ZZ⟩ 1; GHZ fidelity ½ (GME); separable max of ⟨X^⊗n⟩ = 1 | exact (theory) |
| 3. Audit, F1 diagonal | QDEP bd9: C(g ≥ 1) at the 10⁻³ level on every arm, Δg* = 0 (8 repeats); Month-4 `classical_surrogate_z` Δ ≈ 0; F4 dial P = sin²(φ/2) | HAVE |
| 3. Audit, F2 diversity | Diversity 0.86 (sim) vs 0.93–0.98 (hardware) while c(1) differs by ~10σ | HAVE (3 repeats, `ibm_kingston`) |
| 3. Audit, F3 weak null | QuantumTree z = −9.9 vs sim, −10.6 vs B0; PJ0 ⟨X^⊗50⟩ = 0.058 against a separable maximum of 1 | HAVE + exact |
| 3. Audit, F4 confound | Depth ~800; dose response L0/L1/L2/L4 = +0.019 / +0.015 / −0.030 / +0.043 (σ 0.042) | HAVE; **brick-wall A/B missing** (NEED-HW, small) |
| 3. Audit, F5 single basis | W = 24: +0.038 vs 2σ 0.032; GHZ-28: F = 0.055 ± 0.019 < 0.5 | HAVE; **GME width needs E1** (NEED-HW) |
| 3. Audit, F6 entangled ≠ hard | GHZ spine BP χ = 2, fidelity 1.0; treewidth of QALife circuits | χ HAVE; **treewidth CHEAP** (E2) |
| 3. Audit, F7 Hilbert size | 2^108 amplitudes vs the MPS χ actually needed for QuantumTree circuits | **CHEAP** (E2) |
| 3. Audit, F8 depth / qubits | QuantumTree teleport −0.065 vs SWAP +0.040 (p < 0.05, 4/4 seeds); QDEP teleport depth 7 vs SWAP 40, c(1..3) 0.48/0.22/0.11 vs 0.47/0.27/0.15; readout_max 0.214; herald 1.6 %; virus kill gate STOP | HAVE |
| 3. Audit, F9 simulated certificate | CHSH S = 2.733 on hardware vs a simulated S that certifies nothing | HAVE (1 job) |
| 4. Why faithful is easy | Three propositions (diagonal surrogate, treewidth, stoquastic quasispecies) with proofs or sketches; plus treewidth and χ per family | theory + **CHEAP** (E2) |
| Germ/soma result (used in 3/5) | 2×2: 0.77–0.90 vs 0.08–0.12; W = 50 at 3σ; W* damping ∈ [4, 8); unitary W* = 24 | HAVE; **N = 1** for the PJ0 sweep (repeats fold into E1) |
| 5. Map + D_L2 | QCA negativity 0.014 ± 0.006 (p_bonf 0.046); PMD gap −2.9 × floor; ghz2 1.96; smoke-map Goldilocks empty | HAVE (n = 1, smoke); **D_L2 per family CHEAP** (F6 S5 recipe, t* − t_pass); full maps CHEAP but hours |
| 6. Road + forecast ε* | Witness decay W = 3…32: 0.879 / 0.808 / 0.612 / 0.301 / 0.038 / 0.008 plus the recorded calibration (2q error ~0.002–0.007) gives a fitted decay per qubit and ε* | **CHEAP** (fit on existing data) |
| 6. Medicine outlook | Fault-tolerant chemistry cost (Reiher 2017); quadratic-speedup overhead (Babbush 2021) | LIT, one paragraph |
| 7. Procedural generation (C5) | 12 tumours rolled at S = 2.733, seed hashes, exact replay; classical-twin indistinguishability | HAVE; **E7 CHEAP** (render + H tools) |

**Bottom line:**
- About **70 % of the numbers exist**.
- **One must-have hardware gap:** E1, the GME width with repeats. Without it, §3 F5 and the germ/soma headline stay
  qualitative.
- **Everything else missing is simulation or analysis:** E2 (treewidth, χ, BP per family), D_L2 per family, the ε* fit,
  and E7.
- **Weak spot reviewers will hit:** N = 1 in several hardware rows. State it in Threats to validity; E1's repeats fix
  the most important one.

**Page budget** (2-column conference format, e.g. IEEE QCE; verify the page limit):

| Block | Pages | Content |
|---|---|---|
| Intro + two meanings | 0.75 | |
| Ladder + witness rungs | 0.75 | Table 1 |
| Audit | 1.5 | Table 2 with 9 compact rows; only F1, F5 and F6 worked in text |
| Why faithful is easy | 1.0 | Three propositions; proofs in the arXiv appendix |
| Map + hardware data | 1.5 | Fig. 1: the S × H map with every hardware point. Fig. 2: witness vs W with the GME bound (E1) |
| Road, ε*, procedural generation | 1.0 | Medicine is one paragraph; procedural generation is half a page |
| Threats + conclusion | 0.5 | |
| References | 0.75–1.0 | |
| **Total** | **≈ 7.5–8** | |

**It fits if:**
- full run tables, proofs and the history go to the arXiv appendix or supplement;
- the medicine outlook stays one paragraph;
- only three failure modes are worked in detail (the rest live in the table).

**It does not fit** if each of the nine failure modes gets its own figure.

---

## Key references (verify each before citing)

- Alvarez-Rodriguez, Sanz, Lamata, Solano, *Quantum artificial life in an IBM quantum computer*, Sci. Rep. 8, 14793
  (2018).
- Baake, Baake, Wagner, *Ising quantum chain is equivalent to a model of biological evolution*, PRL 78, 559 (1997).
- Gu, Wiesner, Rieper, Vedral, *Quantum mechanics can reduce the complexity of classical models*, Nat. Commun. 3, 762
  (2012).
- Tóth, Gühne, *Detecting genuine multipartite entanglement with two local measurements*, PRL 94, 060501 (2005).
- Gühne, Tóth, *Entanglement detection*, Phys. Rep. 474, 1 (2009).
- Jozsa, Linden, *On the role of entanglement in quantum-computational speed-up*, Proc. R. Soc. A 459, 2011 (2003).
- Markov, Shi, *Simulating quantum computation by contracting tensor networks*, SIAM J. Comput. 38, 963 (2008).
- Kim et al., *Evidence for the utility of quantum computing before fault tolerance*, Nature 618, 500 (2023).
- Tindall et al., *Efficient tensor network simulation of IBM's Eagle kicked Ising experiment*, PRX Quantum 5,
  010308 (2024).
- Aharonov et al., *A polynomial-time classical algorithm for noisy random circuit sampling*, STOC (2023).
- Montanaro, *Quantum speedup of Monte Carlo methods*, Proc. R. Soc. A 471 (2015).
- Babbush et al., *Focus beyond quadratic speedups for error-corrected quantum advantage*, PRX Quantum 2, 010103
  (2021).
- Aaronson, *Read the fine print*, Nat. Phys. 11, 291 (2015).
- Tang, *A quantum-inspired classical algorithm for recommendation systems*, STOC (2019).
- McClean et al., *Barren plateaus in quantum neural network training landscapes*, Nat. Commun. 9, 4812 (2018).
- Engel et al., Nature 446, 782 (2007); Duan et al., PNAS 114, 8493 (2017) (photosynthesis coherence and its
  reassessment).
- Tegmark, *Importance of quantum decoherence in brain processes*, PRE 61, 4194 (2000).
- Reiher et al., *Elucidating reaction mechanisms on quantum computers*, PNAS 114, 7555 (2017) (fault-tolerant
  chemistry cost).
