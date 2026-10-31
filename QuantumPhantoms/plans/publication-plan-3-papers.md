# Quantum Phantoms: three papers in 18 months, one master's thesis

**Date:** 2026-10-30 (rev. 2: P1 = quantum artificial life, P2 = pipeline building blocks, P3 = quantum job in tumour
growth) · **Window:** Nov 2026 – Apr 2028 (M1–M18)

**Basis:**
- `artificial-life/` (QALife hardware results);
- the reverse-engineering pipeline (`relatedPapers/reverse-engineering/`, A–H + INT);
- `siemens-fit-analysis-and-pitch.md`;
- `future.md`.

**Rule for every paper:** one clear question, one measurable headline, and a null result must still be publishable.
Every quantum number carries its claim level, its classical baseline (or surrogate) and a sim/hardware label. Venue
dates below are the usual yearly cycle. *Verify each deadline when the call opens.*

---

## 1. The arc

```text
            M1 ─────────── M6 ─────────── M12 ─────────── M18
Paper 1     [ QALife on hardware + medical reading ]──► submit ~M5–M6
            "What survives when quantum life gets biology, and what does that tell tumour models?"

Paper 2                   [ pipeline building blocks, assembled ]──► submit ~M10–M12
                          "Can small reproduced methods make a replayable, scanner-matched tumour?"

Paper 3                                  [ quantum ladder inside tumour growth ]──► submit ~M18
                                         "Where does quantum earn a job in tumour growth?"

Thesis      P1 + P2 + P3 + method chapter + Siemens/integration + synthesis + twin outlook ─► M18–M20
```

How the papers connect:
- **P1 gives the design rules.** Lineage is the only quantum content, and the germ/soma split protects it (W = 50, 100 qubits); later runs are shown as art.
- **P2 gives the medical substrate:** placement, growth, render and replay.
- **P3 puts the rules from P1 into the substrate from P2** and measures where quantum earns a job.

The order is easy to defend:
1. A hardware-backed quantum result first.
2. Then the medical imaging engine.
3. Then the two joined.

---

## 2. Paper 1 (M1–M6): certified quantum artificial life, with a first reading for tumour models

**Working title:** *How much biology can quantum artificial life carry? Certified genealogies on 100-qubit hardware,
and what they imply for quantum models of tumour evolution.*

### 2.1 What is already done (hardware, banked)

| Result | Hardware | Number | Source |
|---|---|---|---|
| Full 2018 model (replication, mutation, death, interaction), scaled | ibm_kingston | genealogy entanglement depth **W = 24 (48 qubits)**, ~6× the 2018 origin | `research/CONCLUSION_MONTH4.md` |
| Faithful dissipative death | ibm_kingston | witness collapses: W* ∈ [4, 8) | `research/P2_CONCLUSION.html` |
| Germ/soma split (Weismann barrier) | ibm_kingston | witness certified at k = 3σ through **W = 50 (100 qubits)**. It was stopped by chip layout, not by decoherence. **← the paper's endpoint and headline** | `research/pj0_germsoma/PJ0_CONCLUSION.html` |

**Story line (stop here):**
1. Faithful model, which scales to W = 24.
2. Add realistic death, and it collapses at W 4–8.
3. Split germ from soma, and it holds to W = 50 / 100 qubits.

Problem, failure, fix: one clean scientific arc.

**Recorded negatives:**
- Diagonal observables (⟨σz⟩, alive counts) have exact classical surrogates.
- Coherent multi-generation C(g) is blocked on Heron-r2.
- Teleport routing was refuted twice.

All of these go into the paper.

**Shown as art, not as claims:** the later runs are real hardware runs, but they extend the biology beyond what this
paper argues. They go in a short closing "gallery" section (or supplementary material plus a link to the web page),
with one sentence of honest scope each and no headline numbers in the abstract.

| Piece | Hardware | What it shows | Source |
|---|---|---|---|
| Two organisms collide | ibm_kingston, 42 q | bodies meet (overlap 0 → 0.72) while each genealogy stays certified | `research/pj1_arena/` (wave-bars view) |
| Motile vivarium | ibm_marrakesh | a moving organism with reproduction, selection, metabolism and death acting; GHZ certificate ≈ 1.96 | `research/pj2_vivarium/` |
| Interactive web viz | — | the first interactive QALife visualisation (prior-art check done) | `web/index.html` |

These pieces are the bridge to future work (multi-clone competition, invasion) and the Siemens demo material. They
are not evidence the paper rests on.

### 2.2 The medical reading (the new part, labelled preliminary)

QALife operators map onto tumour processes (siemens-8 §5.2.5):

| QALife | Tumour |
|---|---|
| replication | proliferation |
| mutation | mutation |
| death | apoptosis |
| selection / energy | clonal selection under limited resources |
| motility | invasion |
| germ/soma | heritable genotype vs expressed phenotype |

The hardware results then become four **testable statements** for tumour models:

1. **Population statistics gain nothing from quantum.** Cell counts, growth curves and occupancy are diagonal
   observables, and a classical surrogate reproduces them exactly. A quantum tumour model must not be sold on these.
   <span>evidence-based</span>
2. **Lineage is the quantum content.** The only certified non-classical signal is genealogical entanglement, and it
   survives at scale (48–100 qubits). Clonal phylogeny is central to tumour heterogeneity. So the natural quantum job
   in tumour modelling is sampling **correlated clonal families**, for example sibling nodules or clonal sub-regions,
   not counting cells. <span>extrapolation</span>
3. **The architecture rule: keep the genotype coherent and express the phenotype separably.** Dissipative death on an
   entangled phenotype destroys the witness; the germ/soma split protects it, from W 4–8 to W 50. This is the design
   rule for D in the pipeline: a quantum genotype register, with fate, density and texture expressed
   classically. <span>evidence-based design rule</span>
*(Multi-clone competition, from the PJ1 collision, is deliberately left to the gallery and the outlook, not stated as
a finding.)*

### 2.3 Bridge figure (optional, art)

Decode a PJ0 germ-line lineage into a clone tree. Write it as the pipeline's `QuantumLineage` / `SeedShape` contract
and run E → F, giving one CT figure with clonal sub-regions grown from a real quantum genealogy. It belongs in the
gallery, labelled *"illustration of the coupling, not validation"*. It costs a small adapter (a few days). Skip it if
time is short; P3 does the real coupling.

### 2.4 Remaining work (now smaller: the headline is already banked)

| Month | Work |
|---|---|
| M1 | **Make the headline robust:** PJ0 repeats (N = 1 today), the T1 band, and the W sweep with repeats around W = 24–50. This is the one thing a reviewer will ask for. |
| M1–M2 | One unified results table plus figures for the arc: Month-4 W24 → damping collapse → PJ0 W50 (no plotting infrastructure exists yet, so write `analysis/plot_*`). Optional: fill the damping W = 5/6 slots to locate the collapse edge. |
| M2–M3 | Write the medical-reading section and the short gallery (PJ1, motile vivarium, web). |
| M3–M4 | Write the rest; the prior-art section uses the existing check (2018 origin; Qonway is a different lineage). |
| M4–M6 | **Submit + arXiv.** This could go earlier than M6, because the paper no longer waits on new biology. |

PJ2.5 (DD A/B on the motile path) is no longer needed for P1. Run it only if you want a better gallery number.

### 2.5 Venues and fallback

- **Venues:** IEEE QCE 2027 (deadline ~April 2027) or ALIFE 2027 (ISAL; deadline usually spring). Journal
  extension: *Artificial Life* (MIT Press), *Scientific Reports* (the 2018 origin's venue), or *Quantum Science and
  Technology*.
- **Honesty rules (from the QALife work):** no "quantum biology" (tumours are not quantum); the "alive" wording must
  be backed by a gate; the witness certifies lineage entanglement, not usefulness. The medical section is labelled
  preliminary.
- **Minimum that still publishes:** the arc W24 → collapse → W50 as banked. The repeats strengthen it; the gallery
  and the bridge figure are decoration. **This is the lowest-risk paper of the three.**

---

## 3. Paper 2 (M6–M12): small reproduced building blocks, assembled into one tumour

**Working title:** *From published statistics to a scanner-matched, replayable lung nodule: six reproduced methods
assembled into one training-free pipeline.*

**Idea:** each block is a small result that is interesting on its own, with a published number matched (or
honestly missed). Assembled through the frozen contracts, they produce one tumour in real 3-D CT that can be
replayed byte for byte. The paper is the blocks plus the assembly.

| Block | Letter / # | Individually interesting because | Number (sim) |
|---|---|---|---|
| Clinical rulebook → circuit compiler | B #1 | a CPT-to-circuit compiler on a medical network; drift ideal vs Heron-class noise | marginals 0.36 % RMSPE (ideal); Heron-class TVD 0.57–0.74 at depth |
| Lung growth automaton | E #11 | Pixel2Cancer was never ported to lung; the port adds Kansal–Torquato layers and pressure barriers | 3 of 4 growth stages within tolerance |
| Lesion-model library from LIDC | F #14 | parameters only leave patient data (privacy by construction) | 0.870 vs paper 0.890 |
| Scanner fingerprint from the host scan | F #15 | MTF and NPS measured from the scan itself, which drives insertion | σ and kurtosis within 2 % |
| Projection-domain insertion on XCIST | F #16 | open rebuild of a non-public Mayo method | within 3 % |
| Replay and integrity check | G #19 | any edit to a case is visible (CT-GAN injection/removal as the test) | 40/40 detected, 0 false positives |
| *(optional)* Anatomy placement | A #18 | three placement classes on real lungs | **not matched** at n = 9 (report as a negative, or fix the contact rule first) |

**Headline of the assembly:** one tumour A→H from real files, with a verifying record. Add the pilot cohort
(20 hosts × 3 placement classes) for first realism numbers (HU, edge and NPS vs LIDC), plus a small reader test if
time allows.

**Siemens angle:** hosts reselected to Siemens-made LIDC scans, with the CARE Dose4D noise profile (analysis §8, T0).
Mayo Siemens raw data for #16 if the TCIA agreement arrives.

**Work, in order:**

| Month | Work |
|---|---|
| M6 | The three INT fixes (`fill --job`, founder from the draw, beacon freshness) and one full A→H run. |
| M7 | Siemens host reselection; re-run the A segmentation and F #15. Decide on A: fix the contact rule or report it as a negative. |
| M8–M9 | Pilot cohort; realism metrics. Contact Zhou (lung port) and Abadi/McCabe (Duke). |
| M9–M10 | **Submit the SPIE abstract** (usually early/mid August). |
| M11–M12 | Full paper plus journal version. |

**Venues:**
- **Primary:** SPIE Medical Imaging 2028 (abstract ~Aug 2027, manuscript ~Jan 2028, talk Feb 2028). Peer review is
  on the abstract, so acceptance is predictable. Siemens CT physicists attend.
- **Alternatives:** MICCAI 2027 SASHIMI workshop (simulation and synthesis; deadline ~June/July), ISBI 2028 (deadline
  ~Oct 2027), or *Medical Physics* / *J. Medical Imaging*.

**Alternative framing, if the assembly is late:** a **reproducibility paper**. "We rebuilt 21 published methods for
synthetic tumour CT from the papers alone; 13 adapted, 6 dissected, these numbers match, these do not, and why."
Everything already exists in the dossiers. Venues: MELBA, or a MICCAI/MIDL reproducibility-style track.

**Minimum that still publishes:** the blocks with their reproductions and a partial chain. The reproducibility
framing is the safety net.

---

## 4. Paper 3 (M12–M18): where does quantum earn a job in tumour growth?

**Working title:** *Where quantum earns a job in tumour growth: certified seeds, entangled lineages, compressed
process memory, and a measured classical-simulability frontier on IBM Heron.*

**Builds on P1:** P1's rules (lineage = quantum content; germ/soma split; dynamical decoupling as the free lever;
no teleport; diagonal statistics stay classical) are applied inside P2's pipeline.

**Climbs the whole claim ladder in one paper:**

| Rung | Pipeline part | Question | Measured |
|---|---|---|---|
| **L0** | C #4/#5 + B | Can the cohort draw come from a certified quantum source? | **first hardware CHSH certificate** → H_min → certified bits → seed |
| **L1** | D-2 #8 (one-job dynamic-circuit lineage, germ/soma from P1) | Do clonal families stay entangled across generations? | witness vs generation on Heron; where it dies |
| **L1′** | D-5 #6 (quantum causal-state growth model) | Does quantum need less memory for a growth process? | C_q vs C_μ and d_KL vs the best equal-memory classical model, on hardware. Re-tune first: the gap is below the sampling floor today (0.00136 vs 0.00184). |
| **L2 frontier** | #9 BP adversary + D-3 QCA | Where does D stop being classically simulable? | BP/tensor-network fidelity vs qubits × depth × noise (the honest form of the 108-qubit plan) |
| **Coupling** | D → E → F | Does the quantum stage shape the tumour? | the seed shape and clonal fates from hardware, rendered into CT (P1's bridge, now on the real pipeline) |

**Work, in order:**

| Month | Work |
|---|---|
| M12 | Hardware CHSH certificate run (C plus a B-1 draw in one job). |
| M13 | D-5 re-tune; contact Elliott/Gu. |
| M14 | D-2 lineage with the germ/soma split and DD (port the PJ0/PJ2.5 levers). D-3 12-qubit witness: fix it or record the negative. |
| M15 | Hardware jobs: D-5 q-machine and the D-2 lineage. BP adversary on every D circuit; contact Tindall ("try to break it"). |
| M16 | Frontier sweep (Aer up to its limit, BP beyond). |
| M17 | Write. |
| M18 | **Submit + arXiv.** |

**Venues:**
- **Primary:** IEEE QCE 2028 (deadline ~Apr 2028).
- **Journal:** *Quantum Science and Technology*, *npj Quantum Information*, *Physical Review Applied*. A journal is
  realistic with Elliott/Gu or Tindall as co-authors.

**Minimum that still publishes:** a measured null frontier. "The certificate holds; the lineage witness dies at
generation g; BP reproduces D below n qubits; the memory advantage does or does not survive noise." This is the
repo's ethos: advantage is the exception, and measuring it is the result.

---

## 5. The master's thesis

**Research question:** *Which parts of a tumour's life story can today's quantum hardware carry with certified
non-classical content, and how can that be built into a training-free pipeline that produces realistic, replayable
synthetic lung CT?*

| Chapter | Content | Source |
|---|---|---|
| 1. Introduction | Siemens' problem (AI needs labelled, traceable, privacy-safe data); contributions | analysis §0, §4 |
| 2. Background | Virtual imaging trials; tumour evolution and growth models; quantum artificial life (2018 origin); certified randomness; quantum stochastic models; the claim ladder | papers/, future.md |
| 3. Paper 1 | Certified quantum artificial life plus its medical reading | P1 |
| 4. **Method: reverse engineering** *(added)* | 21 methods: dissect → reproduce → adapt → integrate/reject; contracts; honesty gates; the full reproduction table | RE epic, dossiers |
| 5. Paper 2 | Building blocks assembled into one tumour | P2 |
| 6. Paper 3 | Quantum ladder in tumour growth | P3 |
| 7. **Integration and Siemens** *(added)* | Full A→H run; Siemens hosts and raw data; NAEOTOM approximation; AI-Rad protocol; T0/T1/T2 | INT, analysis §8 |
| 8. **Synthesis: where quantum earns a job** *(added)* | One table across P1–P3: process × claim level × classical surrogate/baseline × BP number × hardware result | P1–P3 |
| 9. **Outlook: the twin ladder** *(added)* | Population → calibrated → predictive twin, with the 5/10/15-year predictions and their evidence labels | future.md §5–§7 |
| Appendices | Condensed dossiers, contracts, run records | RE letters, artificial-life/research |

---

## 6. Scope control

| Kept | Cut or parked |
|---|---|
| QALife Month-4, P2, PJ0 in P1 (claims); PJ1 + PJ2.4 + web as the gallery (art) | PJ2.5 (optional, only to improve a gallery number); Critical Quantum Life (thesis-5): separate project, not merged; 2D_alive lattice: appendix at most |
| B #1, E #11, F #14–#16, G #19 (+A #18) in P2 | B-5 QeMCMC, #12 HPC automaton, #17 beyond published parameters, H's full VICTRE MRMC |
| C, D-2, D-5, D-3, #9 in P3 | 108-qubit L2 *as a claim* (map only); #3, #10 (rejected) |
| Lung, CT | Other organs, MR, therapy response: outlook chapter only |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| P1 medical section reads as hand-waving | four statements, each labelled; one bridge figure; no claims about patients |
| Hardware minutes | P1 needs ~1 small batch (PJ0 repeats + W sweep); P3 needs ~3. The IBM Open plan plus Siemens/IBM contacts cover this. Every paper has a minimum that needs no new hardware. |
| Pipeline chain still broken at M6 | P2's reproducibility framing needs no chain |
| QCE or SPIE reject | journal backups; arXiv at each submission secures priority; count "submitted + arXiv" as the milestone |
| Overlap between P1 and P3 | P1 = artificial life on its own terms plus medical hypotheses; P3 = those hypotheses tested inside the tumour pipeline, with a new hardware certificate, a new lineage and a new memory model |
| P3 still in review at the thesis deadline | normal; the thesis cites the arXiv version |

---

## 8. Milestones that Jan / Siemens see

| When | Deliverable |
|---|---|
| M1 | PJ0 repeats and the W sweep; unified figures for the W24 → collapse → W50 arc |
| M3 | Gallery: the collision and the motile vivarium as visuals (optional bridge figure) |
| **M5–M6** | **Paper 1 submitted + arXiv** |
| M6 | One tumour A→H with a verifying record |
| M8 | Pilot cohort on Siemens-scanner hosts |
| **M10–M12** | **Paper 2 (SPIE abstract, then full paper / journal)** |
| M12 | First hardware CHSH certificate in the pipeline |
| M15 | Quantum lineage and memory model on hardware |
| **M18** | **Paper 3 submitted + arXiv; thesis draft** |
| M19–M20 | Thesis submission and defence |
