# Quantum Phantoms: publication plan

**Rev. 3, 2026-11-11.** Paper 1 is unchanged. Papers 2 and 3 now follow the minimal pipeline in `code/` and the
Q-HARD plans. The reverse-engineering work is an archive and is no longer a paper of its own (parked, §5).

**Rules for every paper**
- One question, one measurable headline, and a null result must still be publishable.
- Every quantum number carries its claim level (in standard terms), its classical bound, and a dry-run / hardware label.
- Venue deadlines are the usual yearly cycle. *Verify each when the call opens.*

| | Paper 1 | Paper 2 | Paper 3 |
|---|---|---|---|
| Topic | Quantum artificial life on hardware | The quantum-seeded tumour pipeline | Ladder of quantum resource separations |
| Question | How much biology can a certified quantum genealogy carry? | Can a quantum layer live inside a real imaging workflow? | Which quantum resources survive on one chip, and where do they stop? |
| Data | Banked; needs repeats | Mostly exists; needs repeats | All new |
| Submit | M4–M6 | M3–M5 | M10–M12 |
| Risk | Lowest | Low | Medium to high |

M1 = Nov 2026.

---

## 1. Paper 1 (M1–M6): certified quantum artificial life

**Working title:** *How much biology can quantum artificial life carry? Certified genealogies on 100-qubit hardware,
and what they imply for quantum models of tumour evolution.*

**Banked results (hardware)**

| Result | Hardware | Number | Source (`artificial-life/`) |
|---|---|---|---|
| Full 2018 model, scaled | ibm_kingston | genealogy entanglement depth W = 24 (48 qubits) | `research/CONCLUSION_MONTH4.md` |
| Faithful dissipative death | ibm_kingston | witness collapses at W* ∈ [4, 8) | `research/P2_CONCLUSION.html` |
| Germ/soma split | ibm_kingston | witness certified at 3σ through **W = 50 (100 qubits)**; stopped by chip layout | `research/pj0_germsoma/PJ0_CONCLUSION.html` |

**Story:** the faithful model scales to W = 24 → realistic death collapses it at W 4–8 → splitting germ from soma
holds it to W = 50. Problem, failure, fix.

**Negatives that go in the paper**
- Diagonal observables (⟨σz⟩, alive counts) have exact classical surrogates.
- Coherent multi-generation correlation is blocked on Heron r2.
- Teleport routing was refuted twice.

**Gallery (art, not claims):** two organisms colliding (42 qubits), the motile vivarium on ibm_marrakesh (GHZ witness
⟨XX⟩+⟨ZZ⟩ ≈ 1.96, bound 1; not CHSH), the interactive web view.

**Medical reading (labelled preliminary)**
1. Population statistics gain nothing from quantum: they are diagonal and classically reproducible. *Evidence-based.*
2. Lineage is the quantum content: the natural quantum job is sampling correlated clonal families. *Extrapolation.*
3. Keep the genotype coherent and express the phenotype separably. *Evidence-based design rule.*

**Remaining work**

| Month | Work |
|---|---|
| M1 | Repeats of the germ/soma run (N = 1 today) and the W sweep around 24–50 |
| M1–M2 | One results table and figures for the arc (plot scripts do not exist yet) |
| M2–M4 | Write: medical reading, gallery, prior art (2018 origin; Qonway is a different lineage) |
| M4–M6 | Submit + arXiv |

**Venues:** IEEE QCE 2027 or ALIFE 2027; journal: *Artificial Life*, *Scientific Reports*, *Quantum Science and Technology*.

**Wording limits:** no "quantum biology"; the witness certifies lineage entanglement, not usefulness.

**Minimum that still publishes:** the arc as banked.

---

## 2. Paper 2 (M1–M5): the quantum-seeded tumour pipeline

**Working title:** *A quantum-seeded virtual tumour pipeline: what one Heron processor certifies today.*

**Type:** system and first-results paper.

**Content**
- The pipeline end to end (`code/`): roll → CHSH gate → quantum seed shape → placement → growth → render into real
  CT → lineage record.
- The claim taxonomy, defined once and mapped to standard names (randomness, entanglement witness, memory /
  communication advantage, shallow-circuit advantage, sampling advantage).
- First hardware results: CHSH 2.73 on the roll (ibm_marrakesh), QCA witness marginal, GHZ spine failed, PMD lost to
  the classical model.
- Design rules learned from failures: terminal readout only, calibration pruning, spend guard.
- **Prior work:** Paper 1's artificial-life experiments, as the origin of the growth circuits and the survival rules.

**Remaining work**

| Month | Work |
|---|---|
| M1 | Make the refactored pipeline run, dry and live (nothing has run since the refactor) |
| M1–M2 | 3–5 repeats of the `ROLL` + `DSCALE` run; one classical-baseline cohort |
| M2–M4 | Write |
| M3–M5 | Submit + arXiv |

**Venues:** IEEE QCE 2027, or arXiv + *Quantum Science and Technology*. Optional short SPIE Medical Imaging version
of the classical engine afterwards.

**Wording limits:** quantum does not make the images better; a certificate is about the device, not the tumour;
Siemens data is not used (public LIDC host).

**Minimum that still publishes:** provenance certified on hardware, entangled-seed claims marginal or failed, with
repeats and the reasons.

---

## 3. Paper 3 (M5–M12): a measured ladder of quantum resource separations

**Working title:** *A measured ladder of quantum resource separations on a 156-qubit processor, and where it stops.*

**Type:** physics and benchmarking paper. Opens the four-year memory-advantage project.

**Content** (circuits: `CIRCUIT` in `code/B_mapping/main.py` and `code/D_quantum_growth/main.py`)

| Rung | Circuit | Standard name | Classical bound |
|---|---|---|---|
| Memory | `R1-STAR-001`, `R1-TILE24` | quantum memory advantage (dimension assumed) | 8/27, proven |
| Communication | `R2-Q2`, `R2-D4` | random access code (dimension assumed) | 0.75 / 0.625 |
| Learning | `R3-LADDER`, `R3-CHIP64` | learning advantage with quantum memory | overhead 2 per qubit |
| Locality | `R5-H12`, `R5-MAP8` | advantage over shallow classical circuits | 0.80 |
| Sampling | `L2-BAND` or `R6b-PUB64` | sampling advantage (attempt) | cost ledger ≥ 2⁷³ |

- Per-tile maps on one chip, with repeats; every non-pass reported.
- The classical-cost ledger: why lean rings are simulable, how many CZ a hard circuit needs, patch versus ring.
- At least two backends (marrakesh plus kingston, aachen or boston).

**Remaining work**

| Month | Work |
|---|---|
| M5–M6 | Transcribe the unverified bounds from the source papers (game rule, learning bound, XEB constants) |
| M6–M8 | Validate the circuits in dry runs; first hardware campaign on marrakesh |
| M8–M10 | Second backend; one sampling attempt on the best backend available |
| M10–M12 | Write; submit + arXiv |

**Venues:** *PRX Quantum* or *Quantum* if the maps are clean and the sampling attempt gives a number; IEEE QCE 2028
otherwise.

**Minimum that still publishes:** the memory and communication rungs on hardware with repeats, plus the ledger and
the failures above them.

---

## 4. Thesis

**Question:** which parts of a tumour's life story can today's quantum hardware carry with certified non-classical
content, and how does that fit a training-free pipeline for replayable synthetic lung CT?

| Chapter | Content |
|---|---|
| 1 | Introduction and contributions |
| 2 | Background: virtual imaging trials, growth models, quantum artificial life, the claim taxonomy |
| 3 | Paper 1 |
| 4 | Paper 2 |
| 5 | Paper 3 |
| 6 | Method appendix: the 21 reverse-engineered methods (archive in `plans/relatedPapers/reverse-engineering/`) |
| 7 | Synthesis: process × claim × classical bound × hardware result; outlook to the memory-advantage project |

---

## 5. Parked

- **Reproducibility paper** on the 21 reverse-engineered methods (SPIE MI / MELBA). All material exists in the
  archive; write it only if a paper is needed with no new hardware.
- Sampling advantage as a headline claim. It stays an attempt inside Paper 3.
- Other organs, MR, therapy response.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Pipeline does not run after the refactor | First task of M1; Paper 1 does not depend on it |
| Single-job results | Repeats are budgeted before writing in every paper |
| Hardware minutes or no better backend | Each paper has a minimum that runs on marrakesh |
| Unverified bounds in Paper 3 | Transcribed before any hardware campaign |
| Overlap between papers | P1 = artificial life; P2 = the pipeline and its first results; P3 = the resource ladder. P2 cites P1, P3 cites P2 |
| Rejection | arXiv at each submission; journal backups listed per paper |

## 7. Milestones Siemens sees

| When | Deliverable |
|---|---|
| M1 | Pipeline runs end to end; repeats of the artificial-life headline |
| **M3–M5** | **Paper 2 submitted + arXiv** |
| **M4–M6** | **Paper 1 submitted + arXiv** |
| M8 | First per-tile hardware maps |
| **M10–M12** | **Paper 3 submitted + arXiv** |
| M12+ | Thesis; start of the four-year project |
