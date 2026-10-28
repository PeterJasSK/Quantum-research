# Epic: Quantum Phantoms reverse engineering: 21 published methods rebuilt standalone, one feature per pipeline letter, built in parallel (10 steps)

**Slug:** quantum-phantoms-reverse-engineering
**Features:** W + A–H + INT (10 total: W = foundation (contracts, stubs, site skeleton); A–H = one feature per pipeline letter, built in parallel sessions; INT = integration pass)
**Author:** Claude (Opus)
**Date:** 2026-10-28
**Status:** Approved (by developer, 2026-10-28)

*This epic is **independent of the MVP**. Nothing here imports, extends or fixes MVP code (`QuantumPhantoms/code/`). All work (plans, dossiers, code, runs) lives in `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`, next to the papers it reverse-engineers (`../papers/`).*
*It is **simulation only**: no real IBM jobs. Quantum parts run on `AerSimulator`, both ideal and with the `FakeMarrakesh` Heron r2 noise model.*
*It is **fully 3-D**: 2-D slices exist only as a final export.*
*Every technique gets a human page (HTML) and an equivalent README (Markdown) for future AI agents.*
*It is **built in parallel**: after W, letters A–H are implemented by separate Claude sessions in separate git worktrees, then joined in one INT pass (§3 "Parallel execution", §7).*

---

## 1. Why this epic exists (Vision & Context)

**Context / Assignment.**
- The full Quantum Phantoms pipeline has 8 stages (`../README.md` §0):
  **A** placement → **B** biology + CT context mapped into the circuit → **C** certificate → **D** quantum (non-classical) growth → **E** classical growth (PRNG seeded from certified bits) → **F** render into CT → **G** sign / provenance → **H** analysis. The web viewer is decoration.
- For every stage a published method already solves part of the problem. This epic **reverse-engineers those methods from scratch, standalone**:
  1. dissect the paper;
  2. reproduce one published number;
  3. rebuild the concept in our own clean implementation, adapted to lungs, certification and signing.
- No proprietary code is copied, and nothing is inherited from the MVP. The result is a library of reproduced, understood building blocks, one folder per letter, that later becomes the real pipeline.
- Sources:
  - Target list: `reverse-engineering-targets.md` (21 targets).
  - Claim analysis and Heron r2 budget: `../analysis-stages-B-D-F.md`.
  - Papers: `../papers/`. Codes in brackets such as [B01] refer to files there.

**User outcome.**
- *Peter (builder / thesis):* every stage rests on a reproduced, cited method instead of an ad-hoc guess. Each quantum stage states its claim level: L0 provenance, L1 entangled generative state, L1′ memory advantage, L2 hardness (not reachable on this hardware), L3 fault-tolerant.
- *Jan / Siemens:* a credible route to realistic lung tumors in real CT, with Siemens-native upgrade paths (Mayo Siemens raw data, the NAEOTOM Alpha model) and a provable "nobody chose these" receipt.
- *Reviewer / examiner:* each quantum building block ships with its classical baseline and a measured simulability number. Each method carries a documented reproduction of the original paper.

**Delivery strategy.**
- One feature per pipeline letter (A–H). Each bundles that stage's targets and ends with:
  - a reproduction of each target's published result;
  - a standalone, runnable module in `reverse-engineering/<letter>_<name>/`;
  - a dossier per target.
- Every target follows the same lifecycle (§5): **dissect → reproduce → adapt → integrate**, or **reject with a reason**.
- Letters exchange data only through file contracts (§4). Each letter therefore runs on its own, with stub inputs until its upstream letter exists.
- **W comes first and is small.** It sets up:
  - `about.html`, an explainer of what the project does;
  - `index.html`, a browser over all letters and techniques;
  - the README templates.

  Every later letter must add its README, its dossiers and its pages, so the site grows with the work.
- **Simulation only.** All quantum targets are built and checked on `AerSimulator`, both ideal and with a Heron-class noise model on the heavy-hex coupling map. A hardware run is out of scope and labelled as future work everywhere.

### Full target list and why each matters

The `#` numbers match `reverse-engineering-targets.md`. ★★★ = do now · ★★ = analyse deeper, rebuild parts · ★ = read only.

| # | Feature | Target (source) | Priority | Why it is important |
|---|---|---|---|---|
| 18 | A | SYN-LUNGS anatomy-informed placement [A01], with lungmask [A03] and TotalSegmentator [A04] on LIDC [A02] | ★★ | Real nodules sit in lung tissue in three placement classes (free, juxtavascular, juxtapleural). Placement produces the **context vector** that B conditions on. Without A there is no "CT context" to map into the circuit. |
| 1 | B | Bayesian-network → circuit compiler (Low–Yoder–Chuang [B01]; Borujeni [B09, B10]; pyAgrum reference) | ★★★ | Formal basis of "rulebook → circuit": CPT → controlled rotations, one measurement = one joint sample. It underlies B-1 (context selects CPTs) and B-2 (site × phenotype drawn jointly in superposition, the novel contribution). Borujeni's IBM study is the precedent for measuring rulebook drift on hardware. |
| 2 | B | Quantum-enhanced MCMC (Layden [B11]; Ferguson–Wallden [B12]) | ★★ | A sampler that stays **provably correct under hardware noise** (quantum proposals, classical accept/reject). A tumor-in-anatomy energy (vessels attract, pleura repels) unifies placement and growth. The speedup is shown only in ideal simulation, so we must measure mixing time against classical Metropolis. |
| 3 | B | Quantum blur (Wootton [B04, B05]) | ★ | The only quantum procedural-generation precedent on IBM. Useful for shape-seed variation, and only together with its own classical-blur baseline, which shows when quantum adds nothing. |
| 4 | C | Entropy accounting from Bell tests (Pironio [C01]; Liu 2025 [C02]; Vazirani–Vidick [C05]) | ★★★ | "CHSH > 2" on its own is a label. The min-entropy bound H_min ≥ 1 − log₂(1 + √(2 − S²/4)), hidden test rounds and a Toeplitz extractor turn it into **a number of certified bits and an extracted seed**. Every later seed depends on this. |
| 5 | C | CURBy / NIST beacon chain (Kavuri [C04]) | ★★ | A loophole-free public source for the test-round choice, which narrows the "single chip is not loophole-free" gap. Its hash-chained, signed-pulse format is the template for the G ledger. |
| 6 | D | Quantum causal-state (memory-efficient) process models (Gu [D06]; Elliott [D17]; Wu [D16]; Palsson [D07]; Ghafari [D08]) | ★★★ | **The only proven sense in which quantum simplifies a biological-style stochastic process** (memory, claim level L1′). Building the quantum model of a division-timing/fate process on 2–4 qubits and showing C_q < C_μ (simulated, with Heron-class noise) would be the headline result. Nobody has done it for tumor growth. |
| 7 | D | Goldilocks quantum cellular automata (Hillberry [D13]; Jones [D14]; Farrelly [D03]) | ★★★ | QCA already ran on 23 superconducting qubits with about 1,056 two-qubit gates and measurable network complexity. A heavy-hex-native "tissue patch" needs no SWAPs, and its measured snapshot becomes the **initial shape for E's cellular automaton**. This is the bridge from quantum growth to the image. |
| 8 | D | Dynamic-circuit feed-forward (Bäumer [HW05]; Córcoles [HW06]) | ★★★ | All generations of a quantum lineage run in **one job** (mid-circuit measure, conditional seed, reset) with hidden CHSH rounds interleaved. Lineage plus certificate sit under one job ID and one calibration, which is the strongest provenance. |
| 9 | D | Belief-propagation simulator of heavy-hex circuits (Tindall [HW04]) | ★★ | The competitor becomes our adversary. Running every D circuit through it turns "we don't claim classical hardness" from a disclaimer into a **measured number**. |
| 10 | D | Measurement-induced entanglement transition (Koh [D15]) | ★ (out of scope) | **Decided out of scope** (D-4 not built). Kept as a dossier with only the note on avoiding post-selection, for future reference. |
| 11 | E | Pixel2Cancer [E01] + Kansal–Torquato layers [E02] | ★★★ | The validated CA for tumors in real CT (growth/invasion/death, organ-mask constraint, radiologist-rated realistic). It is untouched for lungs, so a lung port with proliferating/dormant/necrotic layers is both the E engine and a novelty. |
| 12 | E | High-performance CA (Poleszczuk–Enderling [E03]) | ★ | Data structures for millions of cells; needed only when cohorts get large. |
| 13 | F | SyntheticTumors / Label-free pipeline [H01] | ★★★ | Texture synthesis, shape deformation and mass-effect/capsule steps are the **fastest realism win**. Its rule-based tumors trained an AI as well as real ones did. |
| 14 | F | Lesion-model fitting (Ambrosini [F01]; Solomon–Samei PMB 2014) | ★★★ | Fitting a parametric shape + edge-profile model to LIDC nodules gives a per-type parameter library. **Only parameters leave patient data**, which keeps privacy-by-construction while making HU and edges type-correct. |
| 15 | F | Scanner fingerprint estimator (Sanders MTF 2016; Divel–Pelc 2019; Peng [F05]) | ★★★ | The biggest image-quality lever. It measures the host scan's own sharpness (MTF from the air–skin edge) and its local NPS and σ, which drive PSF blur and noise matching for additive-delta insertion. |
| 16 | F | Projection-domain insertion rebuilt on XCIST (Mayo [F03]; Mayo LDCT raw data [A06]) | ★★ | Mayo's code is not public. Rebuilding it gives reconstruction-consistent lesions in **Siemens raw data** without Duke access, which is the Siemens-native upgrade. |
| 17 | F | DukeSim NAEOTOM Alpha parameters (McCabe [F04]) | ★★ | The published spectra, thresholds and noise correlation of Siemens' photon-counting CT, written as an XCIST configuration. A Siemens hook without the closed simulator. |
| 19 | G | CT-GAN as a tamper test [G01] | ★★ | Indistinguishable fakes are why signed provenance matters. Re-implementing injection and removal only as a test shows that the G receipt and signature catch both edits. Pitch it as traceability, not security. |
| 20 | H | FDA VICTRE pipeline [H03] | ★★ | A regulator-accepted end-to-end in-silico trial. It is the template for the study architecture and the model-observer analysis. |
| 21 | H | Siemens AI-Rad Companion Chest CT | ★ | The product that longitudinal tumor pairs would test. Treat it as a **black box through its documented interface only**; no decompiling (licence). |

**Explicitly not reverse-engineered** (reasons in `reverse-engineering-targets.md`):
- FRQI/NEQR amplitude-encoded CT (data loading [B13]).
- Carleman PDE / QAE [D21] (fault-tolerant only).
- Quantum-walk invasion [D19, D20] (unrealistic spread).
- MAISI [F11] / DiffTumor [F07] (trained on patients; ablation only).
- QALife 2018 [D01] (already reproduced elsewhere in this repo).

---

## 2. Steps in this Epic (Milestones)

| ID | Step / Feature | Title | Status | Summary |
|----|----------------|-------|--------|---------|
| W | Foundation | Contracts + stubs + site skeleton | open | **Must finish before any parallel work.** (1) **Freeze the file contracts** for every §4 hand-off entity in `shared/contracts/` (JSON Schema + volume conventions: NIfTI, spacing, orientation, HU). (2) **A stub fixture per contract** in `shared/stubs/` (stub sites, rulebook, certificate, draw, seed shape, cell lattice, hybrid volume, receipt), so every letter runs before its upstream exists. (3) Shared helpers only: seed/hash utilities, run-record writer, `FakeMarrakesh` sim-backend factory. (4) Skeleton folders `A_…`–`H_…`, each with a README template, dossier template and its **own `status.json`** (targets pre-filled as `listed`). (5) `about.html` (internal explainer), root `README.md` (AI entry point), and the site build script that aggregates the per-letter status files and Markdown into `index.html` + `site/`. Done when every letter folder exists, every stub validates against its contract, and the site renders all 21 targets as `listed`. |
| A | Placement | Anatomy-informed site + context vector | open | Target #18. Lung/lobe/vessel/airway masks (lungmask, TotalSegmentator) on LIDC; SYN-LUNGS-style placement rules; three placement classes. Output: `sites.json` (candidate sites + context vectors) + masks. Reproduce: placement-class proportions against LIDC annotations. |
| B | Mapping | Rulebook + CT context → circuit | open | Targets #1–#3. Standalone Bayesian-network → circuit compiler with context conditioning (B-1), then the joint site × phenotype superposition (B-2). QeMCMC energy sampler as a research arm (B-5). Quantum blur only with its baseline. Reproduce: a Borujeni 4-node network on Aer (ideal, then Heron-class noise); measure drift (TVD) vs the network. |
| C | Certificate | CHSH → certified bits → seed | open | Targets #4, #5. Min-entropy accounting, hidden test rounds, Toeplitz extraction, CURBy-seeded test-round choice, ledger format modelled on the beacon chain. Reproduce: the Pironio H_min-vs-S curve, then apply it to our measured S. |
| D | Quantum growth | Certified quantum generations + honest simulability | open | Targets #6–#10. One-job dynamic-circuit lineage (D-2); quantum causal-state model of a growth process with measured memory advantage (D-5); heavy-hex Goldilocks QCA tissue patch whose snapshot seeds E (D-3); belief-propagation adversary on every circuit. D-4 is out of scope. Reproduce: Jones 1-D QCA metrics and a Wu-style C_q vs C_μ, both in simulation (ideal + Heron-class noise). |
| E | Classical growth | Lung Pixel2Cancer engine | open | Targets #11, #12. Rebuild Pixel2Cancer's rules standalone, port them to lungs with Kansal–Torquato layers, constrain with A's masks, seed the PRNG from C's extracted seed, start from D's snapshot (stub shape until D exists). Snapshots give baseline/follow-up pairs. Reproduce: Pixel2Cancer growth behaviour on one of their organs. |
| F | Render into CT | Realistic, scanner-matched insertion | open | Targets #13–#17. Cell states → HU from the LIDC-fitted lesion library; supersampled partial volume; additive-delta insertion (vessel max-rule, ground-glass α-blend); 3-D PSF + noise from the scanner fingerprint, inserted into the full 3-D host volume; 2-D slices exported only at the end. Upgrade: projection-domain on Mayo Siemens raw data via XCIST, then NAEOTOM Alpha approximation. Reproduce: Robins/Duke volume agreement (< 3 %) on one case. |
| G | Sign / provenance | Commit-before-draw receipt + tamper test | open | Target #19 (consumes C's ledger format). Commit rulebook + code hash before the job; receipt (job ID, counts, S/H_min, witnesses, params, seed, code hash) → Ed25519 → hash-chained ledger + DICOM tag. A CT-GAN-style injection/removal must fail verification. |
| H | Analysis / use | VICTRE-shaped validation + black-box target | open | Targets #20, #21. VICTRE-modelled study architecture: physics realism (HU, edge, NPS vs LIDC), PyRadiomics distributions, in-context visual Turing test, train-synthetic/test-real detection, cohort drift vs rulebook, certificate and witness statistics, classical baseline. AI-Rad Companion as a documented-interface black box only. |
| INT | Integration | Stubs → real chain, site rebuild | open | One session after the letters have merged. Replace the stubs with real upstream files in order A → B → C/D → E → F → G. Run one end-to-end simulated tumor (3-D) and fix contract mismatches by **amending the contract in one place, then the producer and consumer**. Rebuild the site, then run H's full validation on the integrated output. Done when one tumor travels A→H from real files with a verifying receipt. |

---

## 3. Cross-Cutting Decisions (Global Architecture)

**Tech stack.**
- Python 3 + Qiskit + `qiskit-aer`. **Simulation only, no real QPU jobs in this epic.**
- Two simulation modes for every quantum target:
  1. ideal;
  2. **Heron-class noise**: the noise model and heavy-hex coupling map of **`FakeMarrakesh`** (pinned reference for every letter), transpiled with CZ basis and dynamic-circuit support where Aer allows. The installed versions (qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0) provide `FakeFez`, `FakeMarrakesh`, `FakeKingston` and `FakeAachen` (Heron r2) and `FakeTorino` (Heron r1).

  Results stay hardware-realistic without spending jobs.
- Imaging: NumPy/SciPy, SimpleITK/pydicom, `pylidc`, `lungmask` / TotalSegmentator, PyRadiomics, XCIST (`gecatsim`).
- No database, no backend, no web layer in this epic.

**Dimensionality: 3-D only.** Every imaging artifact is a 3-D volume:
- masks;
- context features;
- cell lattices;
- lesion models;
- PSF and NPS;
- hybrid CT.

Voxel spacing comes from the host scan's DICOM. 2-D slices are a final export step only (figures, site, slice-based reader tests) and never an intermediate representation.

**Isolation from the MVP.** Nothing is imported from `QuantumPhantoms/code/`, and MVP data classes are not reused. Every letter defines its own contract (§4). Ideas that the MVP also had (rulebook, CHSH pair, QALife loop) are re-derived here from the papers.

**Folder layout (one root, one subfolder per letter).**
```text
QuantumPhantoms/plans/relatedPapers/
├── papers/                      # PDFs (sources, read-only)
├── README.md, analysis-stages-B-D-F.md
└── reverse-engineering/
    ├── README.md                # AI entry point: purpose, folder map, conventions, status table (W)
    ├── about.html               # human explainer: what this project does (W)
    ├── index.html               # human browser over letters → techniques (W, generated)
    ├── (no root status file)    # status lives per letter: <L>_<name>/status.json, aggregated by the site build
    ├── site/                    # generated per-letter / per-target HTML pages + figures (W)
    ├── epic-reverse-engineering.md, reverse-engineering-targets.md
    ├── feature-<L>-<name>.md    # from /plan-feature, one per letter
    ├── shared/                  # FROZEN after W: contracts/ (JSON Schema), stubs/, seed+hash+run-record helpers,
    │                            #   sim-backend factory (FakeMarrakesh), site build script. Changed only in INT.
    ├── A_placement/  B_mapping/  C_certificate/  D_quantum_growth/
    ├── E_classical_growth/  F_render/  G_provenance/  H_analysis/
    │     each: README.md, status.json, dossiers/<#>-<target>.md, src/, repro/ (paper reproduction), figures/, runs/
    └── runs/                    # cross-letter end-to-end runs
```

**Reverse-engineering rule (every target).**
1. **Dissect:** a dossier with method, equations, parameters and claimed results.
2. **Reproduce** one published number or figure in `repro/` before adapting.
3. **Adapt** to lungs, certification and our contracts.
4. **Integrate**, or reject with a written reason.

Re-implement from papers. Open code may be read and used only within its licence (check the Pixel2Cancer / SyntheticTumors / VICTRE / QuantumBlur licences first). Never decompile proprietary software (AI-Rad Companion, DukeSim, Mayo tools).

**Documentation and visual output (every feature, set up by W).**

*Markdown is the source of truth; HTML is generated from it.*

- **Per letter:** `<L>_<name>/README.md`, written for a future AI agent, with fixed sections:
  - Purpose;
  - Targets and their status;
  - Inputs (contract files);
  - Outputs (contract files);
  - How to run (sim commands);
  - Reproduced result vs. paper;
  - Claim level and honesty notes;
  - References (paper codes).
- **Per target:** `dossiers/<#>-<target>.md` with fixed sections:
  - Concept;
  - Equations;
  - Parameters;
  - Paper's claimed result;
  - Our reproduction (number + figure);
  - Adaptation;
  - Verdict;
  - What to reuse next.
- **Generated HTML:** `shared/` holds one build script that renders the READMEs, dossiers and the per-letter `status.json` files into `index.html` and `site/`. It is static, self-contained and offline: no server, no CDN dependencies. The rendered pages carry the same content as the Markdown, so a human and an AI read the same thing.
- **Explainer:** `about.html` is hand-written and **internal** (Peter + future AI agents), so it can be technical. It explains what the project does. It covers the A–H pipeline diagram, why reverse-engineer, the claim ladder L0–L3, "simulation only", privacy-by-construction, and links into `index.html`.
- **Definition of done (every letter):** its README, its dossiers and its figures exist, and its own `status.json` is updated. The letter may run the site build locally to preview, but must not commit `index.html` / `site/`; only INT commits the rebuilt site.

**Contracts between letters are files only:** JSON for metadata, NIfTI/NPZ for volumes and masks (§4), frozen in `shared/contracts/` by W. Every letter runs standalone against `shared/stubs/` and swaps in real upstream files in INT.

**Parallel execution (multiple Claude sessions at once).**
- **Isolation:** one git worktree + branch per letter, e.g. `git worktree add ../qp-re-<L> -b re-<L>`, or a worktree-isolated Claude session. Never run two sessions in the same checkout.
- **Ownership:** a session writes only inside its own `<L>_<name>/` folder and its own `feature-<L>-<name>.md`. It **never** edits `shared/`, the epic, the targets list, `about.html`, `index.html`, `site/`, `.gitignore`, or another letter's folder.
- **Contract change needed?** Do not edit `shared/`. Record it in the letter's README under "Contract change requests" and keep working on the frozen contract (adapt locally). INT applies all requests in one place.
- **Workflow per session:** `/plan-feature <L>` → review → `/implement-feature` → merge the branch to `main` (folders are disjoint, so merges should not conflict).
- **Resources:** Aer noise simulation, TotalSegmentator and 3-D volumes are CPU/RAM-heavy. Run about 4 sessions at a time (waves in §7), not all 8.

**Honesty gates.**
- Every quantum deliverable states its claim level (L0 / L1 / L1′) and ships with its classical baseline and its belief-propagation simulability number (#9).
- Never claim "more realistic because quantum", "quantum biology", or "classically impossible" (`../analysis-stages-B-D-F.md` §0, §3.1).
- **Every quantum number is simulated** and must be labelled "simulated: ideal" or "simulated: Heron-class noise" in its README, dossier and page. Nothing may be presented as a hardware result.
- **Simulated CHSH certifies nothing.** C's deliverable is the *accounting pipeline validated on simulated data* ("certification-ready, not certified"). Real certification needs a hardware run, which is future work.
- Lesson from the analysis: a **single-qubit** phase dial measured in Z is a classical biased coin. Any "interference" claim in B or D must sit in multi-qubit correlations read in ≥ 2 bases.

**Seed and provenance chain.** Certified raw counts → C extractor → seed hash → every PRNG in E and F. Everything after the quantum job is deterministic and replayable from the G receipt.

**Logging.** Every run directory records backend, job IDs, calibration snapshot, transpiled-circuit hash, counts, code hash and seed. This is the raw material for G.

**Conventions.** Repo study workflow: **no GitHub issues, no automated test suite**; verification is manual plus the reproduction step. Git: `../papers/` and every `runs/` folder are gitignored. READMEs, dossiers, code, figures and the generated site are committed.

---

## 4. Shared Data Model Evolution

| Entity | Introduced In | Consumed By | Notes (Purpose) |
|--------|---------------|-------------|-----------------|
| `TargetStatus` (`<L>_<name>/status.json`, one file per letter) | W | own letter only; site build aggregates | One record per target: letter, #, name, lifecycle state, reproduced number, claim level, sim mode, links (dossier, paper codes, figures). |
| `TargetDossier` | W (template), every letter | H, site build | One per target: summary, reproduced number, adaptation notes, verdict (integrated/rejected). Markdown source for its HTML page. |
| `LetterReadme` | W (template), every letter | site build, future AI agents | Per-letter README with the fixed sections in §3. |
| `AnatomyMasks` | A | E, F | Lung, lobe, vessel and airway masks per host scan (NIfTI). |
| `SiteCandidate` / `ContextVector` | A | B, E, F | Location + placement class + anatomical features (`sites.json`). |
| `Rulebook` | B | B, H | Published statistics only, cited, with context-conditioned CPTs. Hashed for commit-before-draw (G). |
| `CompiledCircuit` | B | C, D, G | Compiler output: circuit, qubit map, gate counts, rulebook hash. |
| `QuantumJobRecord` | B (first quantum use) | C, D, G | Simulator mode (ideal / Heron-class noise + fake-backend name), seed, transpiled hash, raw counts, test-round mask. Hardware fields reserved for future work. |
| `TumorDraw` | B | D, E, H | Decoded joint sample: site ID, size, type, margin, shape seed. |
| `Certificate` | C | D, E, F, G, H | CHSH S, H_min bound, certified-bit count, extracted seed, CURBy pulse ID. |
| `WitnessRecord` / `MemoryAdvantageRecord` | D | G, H | L1 / L1′ evidence: ⟨XX⟩+⟨ZZ⟩, mutual-information network, C_q vs C_μ. |
| `SimulabilityReport` | D | H | Belief-propagation adversary fidelity per circuit. |
| `QuantumLineage` / `SeedShape` | D | E | Measured generations and QCA snapshot, the E initial state. |
| `CellLattice` / `GrowthTrajectory` | E | F, H | 3-D cell states over time. Snapshots give baseline/follow-up pairs. |
| `LesionModelLibrary` | F | F, H | Parameters fitted from LIDC per nodule type. No voxels. |
| `ScannerFingerprint` | F | F, H | MTF/PSF, local NPS and σ map per host scan. |
| `HybridVolume` | F | G, H | 3-D host CT + inserted lesion (+ 3-D ground-truth mask). 2-D slices are derived from it only at export. |
| `Receipt` / `LedgerEntry` | G | H | Commit → fill → sign → chain. Holds every hash and seed above. |
| `ValidationReport` | H | — | Realism, utility, drift, certificate and baseline results. |

---

## 5. State Changes / Workflows

* **Reverse-engineering target (all 21):** `listed → dissected → reproduced (published number matched) → adapted → integrated | rejected (reason recorded)`. Each transition updates the letter's own `status.json` and the target's dossier in the same change. The site badge follows at the next INT rebuild.
* **Tumor, end-to-end:** `site chosen (A) → context-conditioned certified draw (B + C) → quantum generations with witness (D) → hand-off (SeedShape + extracted seed) → classical growth snapshots (E) → rendered + inserted (F) → signed (G) → validated (H)`
* **Certificate:** `test-round choice seeded (CURBy) → job run → raw counts → CHSH S → H_min bound → { pass → extracted seed | fail (S ≤ 2) → draw rejected + logged (no retry, no fallback) }`
* **Receipt:** `committed (rulebook + code hash, BEFORE job) → job run → filled → signed (Ed25519) → ledgered → { verified | tamper detected }`
* **Quantum lineage (D-2, one job):** `prep founder → divide/fate → { hidden CHSH round | genotype round } → mid-circuit measure → feed-forward seed → reset → next generation … → final readout`

---

## 6. Environment Specifics & Constraints

**Simulation only, but Heron-realistic** (`../analysis-stages-B-D-F.md` §1). There are no real IBM jobs. Every circuit is still designed as if it had to run on Heron r2:
- transpile to the heavy-hex coupling map and CZ basis;
- keep all-to-all registers ≤ 15–20 q;
- assume readout error ≫ 2q error (use the noise model; minimise mid-circuit readouts);
- coherent multi-generation genealogy stays out of scope;
- shallow heavy-hex circuits are belief-propagation-simulable, so there is no L2 claim.

Simulator limits matter too:
- statevector width;
- whether Aer supports dynamic-circuit feed-forward with noise. Check this in D before relying on it.

**Data and licensing:**
- LIDC-IDRI: host scans, rulebook source, realism reference.
- Mayo LDCT raw data (TCIA, CC BY): **Siemens cases only for Siemens work** (manufacturer restriction). Confirm in the Siemens contract.
- Open repositories are used only under their licences.

**Privacy-by-construction:** no patient voxels enter any generator. Only fitted parameters and published statistics. Learned refiners (DiffTumor, MAISI) are excluded from the main path.

**Framing:** for Siemens, lead with data credibility and traceability, not security vocabulary.

**Resolved decisions (developer, 2026-10-28):**
1. **Slug:** `quantum-phantoms-reverse-engineering`.
2. **Location:** plans, dossiers, code, figures, site and runs all live in `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`, in one subfolder per letter (layout in §3).
3. **Fully 3-D.** Placement, growth, lesion models, insertion and validation all work on 3-D volumes. 2-D slices are produced **only at the end**, as an export from the 3-D result (figures, site, any slice-based reader test).
4. **Hardware:** zero real IBM jobs. Simulation only (ideal + Heron-class noise).
5. **D-4 (measurement-induced transition) is out of scope.** Target #10 is recorded as `rejected (out of scope)` in `D_quantum_growth/status.json`; its dossier keeps only the post-selection note.
6. **CHSH ≤ 2 in simulation:** the draw is **rejected and logged**. No retry loop and no CURBy fallback.
7. **Git:** PDFs (`papers/`) and every `runs/` folder are gitignored. READMEs, dossiers, code, figures and the generated site are committed (`.gitignore` updated).
8. **W is its own small first feature.**
9. **Explainer audience is internal** (Peter + future AI agents). `about.html` may be technical; no Siemens/non-specialist version is needed.
10. **Reference noise model:** `FakeMarrakesh` (Heron r2) for every letter.

---

## 7. Implementation Order (Dependency Graph)

```text
Wave 0  (1 session, sequential)   W ── freezes shared/contracts + shared/stubs + site skeleton
                                  │
            ┌─────────────┬───────┴─────┬─────────────┐
Wave 1  (4 parallel)      A             C             E             F        (worktrees re-A, re-C, re-E, re-F)
            │             │             │             │
            ▼             ▼             ▼             ▼          merge each branch to main when done
            ┌─────────────┬─────────────┬─────────────┐
Wave 2  (4 parallel)      B             D             G             H        (worktrees re-B, re-D, re-G, re-H)
            │             │             │             │          run on stubs or merged wave-1 outputs
            └─────────────┴──────┬──────┴─────────────┘
INT     (1 session, sequential)  real chain A → B → C/D → E → F → G, contract fixes, site rebuild, H full validation
```

- **W is strictly first.** Nothing parallel starts until the contracts and stubs are frozen and every stub validates.
- **Wave 1 = A, C, E, F.** These are the highest-priority targets (#18, #4, #11, #13–#15) and need no real upstream. E and F give the fastest visible 3-D result; C unblocks every seed.
- **Wave 2 = B, D, G, H.** Each can start on stubs. B and D benefit from merged A/C, and G from merged C. H builds its validation harness on stub hybrid volumes. Wave 2 may overlap wave 1 if resources allow, since the stubs make every letter independent.
- **The data dependency still exists** (A → B → D → E → F → G → H). It is satisfied only in **INT**: parallel sessions give working, reproduced parts; INT gives the working pipeline.
- **Priority within the epic:** #11 + #13 → #15 → #4 → #1 → #6 → #7 checked by #9.

---

*Inputs:* `reverse-engineering-targets.md`, `../analysis-stages-B-D-F.md`, `../README.md`.
*Next:* `/plan-feature W` in this session, then open 4 worktree sessions for wave 1 (A, C, E, F), each running `/plan-feature <L>` → `/implement-feature`.