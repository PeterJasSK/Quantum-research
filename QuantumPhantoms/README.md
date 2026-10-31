# Quantum Phantoms

> **Live document.** This README tracks overall progress. Update the "Progress" tables and the changelog
> whenever a stage changes state. Last updated: **2026-10-31**.

Training-free synthetic lung CT for validating detection AI. Virtual tumours are **placed** by anatomy, **grown**
by published models and **rendered** into real CT with the host scanner's own blur and noise. Quantum computing
enters only where it has a measured job: a certified random seed, an entangled lineage, a process-memory
advantage. Long-term goal: each pipeline stage becomes one layer of a future patient digital twin.

- **Quantum Phantoms**: thesis / academic name (this folder).
- **Quantum Virtual Tumors** (SK *Kvantové virtuálne nádory*): pitch name for Siemens.
- *Quantum Synthetic Cultures (QSC)* is retired; it still appears in older plans.

Honest one-liner: *tumour parameters can come from certified-quantum measurement; growth and image are
classical.* No claim that quantum makes better or more realistic tumours.

---

## The pipeline (letters A–H)

```text
A placement → B rulebook + CT context → circuit → C certificate → D quantum growth
            → E classical growth → F render into CT → G lineage record → H validation
```

| Letter | Stage | Job | Quantum? |
|---|---|---|---|
| **A** | Placement | Lung/lobe/vessel masks; choose a plausible site | classical |
| **B** | Mapping | Published nodule statistics (+ CT context) → circuit angles → tumour draw | quantum sampling |
| **C** | Certificate | Bell (CHSH) test → certified min-entropy → extracted seed | quantum (L0) |
| **D** | Quantum growth | Entangled lineage / quantum process memory / quantum seed shape | quantum (L1, L1′) |
| **E** | Classical growth | Cellular-automaton growth inside the lung (Kansal–Torquato + Pixel2Cancer) | classical |
| **F** | Render | Lesion HU + partial volume, inserted into real CT with the scanner fingerprint | classical |
| **G** | Provenance | Replayable record: what was drawn, by which job, with which code | classical |
| **H** | Validation | Does a detector or reader treat synthetic like real? | classical |

**Claim ladder:**

| Level | Meaning |
|---|---|
| L0 | provenance (certified seed) |
| L1 | entangled generative state (witness) |
| L1′ | quantum memory advantage of the growth process |
| L2 / L3 | classical hardness / fault-tolerant; **blocked**, kept only as a frontier map |

---

## Two codebases (do not mix)

| | MVP prototype | Reverse-engineering (RE) pipeline |
|---|---|---|
| Purpose | One working demo end to end: quantum roll → realistic CT tiles → web page | Rebuild 21 published methods one letter at a time, each with a reproduced paper number |
| Where | [`code/`](code/README.md) | [`plans/relatedPapers/reverse-engineering/`](plans/relatedPapers/reverse-engineering/README.md) |
| Plans | [`plans/epic-quantum-phantoms-mvp.md`](plans/epic-quantum-phantoms-mvp.md), `plans/feature-F*.md` | `epic-reverse-engineering.md`, `feature-<L>-*.md` (in the RE folder) |
| Quantum | Aer simulator; hardware path wired, run by Peter only | Simulation only (Aer ideal + `FakeMarrakesh` noise) |
| Imports | MVP **copies** frozen RE code (`code/imaging/PORTED.md`), never imports it | RE never imports `code/` |

---

## Progress

Status words used below:
- `none`: not started
- `stand-in`: simplified placeholder, not the RE method
- `partial`: part of the RE method
- `built (sim)`: implemented and verified in simulation / software
- `hardware`: verified on real quantum hardware

### Per letter

| Letter | RE pipeline (readiness) | MVP prototype | MVP gap vs RE | Claim today |
|---|---|---|---|---|
| **A** placement | prototype. Lungmask + TotalSegmentator masks; #18 placement mix *not matched* at n = 9 (adapted) | **stand-in.** Threshold lung/body masks; lobe = side + z band; aerated-lung site (`code/imaging/place.py`, `host.py`) | no real lobes or fissures, no vessel or airway masks, no placement-class mix | n/a |
| **B** mapping | prototype. BN → circuit compiler (#1, marginals within 0.01), QeMCMC (#2); B-2 joint site × phenotype | **partial (B-1-like).** Fleischner/LIDC rulebook → Ry angles → 9-qubit circuit + one division (`code/f1_quantum/`) | no CT-context conditioning, no B-2 | L0 path only |
| **C** certificate | caveats. Pironio entropy (40.8 vs 42 bits), NIST beacon chain verified | **partial.** Job-level CHSH value; per-tile seeds = hash of shot bits (`f1_quantum/certify.py`, `imaging/seedhash.py`) | no min-entropy bound, no extractor, no beacon, **no S ≤ 2 reject gate, job ID not recorded** | simulated: certification-ready, not certified |
| **D** quantum growth | prototype. D-5 memory (#6, L1′ gap below sampling floor), D-3 Goldilocks QCA (#7, L1 ideal only), D-2 dynamic lineage | **built (sim), D-SCALE.** F4 Mode-A loop (optional) + `code/dscale/`: 40/100/120-q families (ghz-spine, ch-qca, pmd-bank, kicked-ising), survive-vs-simulable map; **a QCA snapshot per tile is now the seed F5 grows from** | no D-2 dynamic lineage (refuted on Heron r2); L1′ gap still below 3× floor at first-run caps; maps are smoke-truncated (full sweeps in the runbook) | sim only: spine L1 (GME), QCA seed L1 per tile; L2 none |
| **E** classical growth | caveats. KT Table 2 matched 3 of 4 stages; P2C behaviours B1–B4 pass; lung VDT calibrated | **built (sim), adapted copy.** 0.5 mm lattice, pleura wall, Ø 2 mm seed → rolled size → +90 d (`code/imaging/growth.py`) | no fissure walls, no vessel/airway barriers (F5 decision Q8) | n/a (classical) |
| **F** render | caveats. Volume +0.25 ± 1.02 %, SH shape 0.87, noise within 2 %; NAEOTOM #17 not matched | **built (sim), adapted copy.** LIDC-fitted library, partial volume, 3-D additive insert, host PSF + NPS, Siemens host LIDC-IDRI-0481 (`code/imaging/`) | no local NPS, no projection-domain insert (#16), no NAEOTOM look (#17) | n/a (classical) |
| **G** provenance | prototype. Signed receipt + ledger + voxel binding + 1-voxel tamper test | **none.** Only provenance fields in `tiles.json` (seeds, file hashes, host series UID) | no record, no signing, no ledger | — |
| **H** validation | prototype. CHO-LG vs ideal, MRMC variance band, radiomics, AI-Rad protocol (dissected) | **none.** Only per-tile checks (volume, σ, VDT) and a procedural-vs-grown comparison image | no observer model, no reader study, no real-vs-synthetic test | — |
| **INT** chain | A→H runner + gap probe; **chain not closed** (G `fill --job` keeps only one job) | MVP chain: B → C → (D) → A → E → F → web, single host | — | — |

Nothing is production-ready. Everything is simulation or software-only, with n = 1 host scan.

### MVP features

| Feature | What | Status |
|---|---|---|
| F1 | Quantum roll: rulebook → circuit → certified parameters, `Sampler` seam (QRNG / PRNG) | built (sim); hardware path wired, **not yet run** |
| F2 / F2.1 | Procedural lesion → CT tile (now `imaging --renderer procedural`) | built |
| F3 / F3.1 | Self-contained web page: grid, CHSH stamp, lineage badges, rulebook strip | built |
| F4 | Mode-A QALife arm: divide + fate + per-generation witness | built (sim), optional |
| F5 | RE realism: Siemens LIDC host + E growth + F render + pixel-growth player | **built (sim), 2026-10-31** |
| D-SCALE | Quantum growth at 40 / 100 / 120 q: plug-and-play decoherence-surviving families, survive-vs-simulable map, quantum seed shapes for the F5 grower, F3 panel, hardware runbook (`code/dscale/`) | **built (sim), 2026-10-31**; smoke runs only (≤ 20 min); hardware: runbook only |
| PRES | Presentation | plan only |

### Quantum hardware

| Item | Status |
|---|---|
| MVP F1 run on IBM hardware | **not yet run.** Known issues before the first run: `--backend ibm_heron` is not a device name (use `ibm_marrakesh` / `ibm_fez` / `ibm_kingston` / `auto`); ~6 jobs instead of 1; job ID not recorded; no S ≤ 2 reject |
| QALife (sibling project `../artificial-life/`) | GHZ witness ⟨XX⟩+⟨ZZ⟩ ≈ 1.96 on `ibm_marrakesh` (bound 1). **This is not CHSH**; read as CHSH it would be a failed Bell test |
| RE letters | simulation only by design |
| D-SCALE live (Peter, 2026-10-31) | **ran on hardware.** `code/dscale/run_budget_<B>.sh` (auto backend, ≤ 1 QPU-min). 40 q: ibm_kingston `dbj0ddd6p51s73cjqak0`; 100 q: ibm_marrakesh `dbj0i556p51s73cjqmgg`; 100 q with the cohort rolled on the QPU: ibm_marrakesh `dbj15npffo6c73b8mls0` (roll + CHSH **S = 2.733**) + `dbj16056p51s73cjs7q0` (32 QPU-s). QCA witness L1 in all three (marginal), GHZ spine L0, PMD L0; hardware size mix not matched to the rulebook. Ranking below |

#### D-SCALE hardware ranking (web survey 2026-10-31; "(unverified)" = secondary sources only)

| Budget | Sim proxy | 1st choice (real) | Alternatives | Why |
|---|---|---|---|---|
| 40 | `boston`, `nighthawk` 5×8 | Heron r3: ibm_boston, or ibm_aachen (EU; Heron r3 since 2026-03) (unverified) | Quantinuum Helios 98 q (institutional access only); IQM Emerald 54 q (EU, Braket); Nighthawk r2 ibm_phoenix | GHZ scale proven on Heron; slack for pruning |
| 100 | `boston`, `kingston` | Heron r3 (boston / pittsburgh / aachen) | Nighthawk r1/r2; Helios (≤ 98 q) | Big Cats: 100-q GHZ F = 0.55–0.70 on Heron |
| 120 | `nighthawk` (square), `marrakesh` (spine) | Nighthawk r2 ibm_phoenix for `ch-qca`; Heron r3 for `ghz-spine` | Nighthawk r1 ibm_berlin (EU, Premium/Flex early access) | only the square lattice gives 4-loops natively |
| — | not recommended | Google Willow (no access), IonQ Tempo (no public 100-q cloud), Rigetti Cepheus 108 q (2q 99.1 %), neutral atoms | | |

Student access: IBM Open Plan 10 min/month (kingston open since 2026-05, unverified); IBM Quantum Credits via the
supervisor; EuroHPC Quantum Access Pilot (≤ 54 q, cut-offs 1 Nov / 1 Dec 2026, via the supervisor) (verify).

### Publications (plan: [`plans/publication-plan-3-papers.md`](plans/publication-plan-3-papers.md))

| Paper | Content | Target | Status |
|---|---|---|---|
| P1 | QALife on hardware: W24 → collapse → germ/soma W50 | QCE / ALIFE 2027 | in progress (in `../artificial-life/`) |
| P2 | Reproduced pipeline blocks (B#1, E#11, F#14–16, G#19) as one replayable tumour | SPIE MI 2028 | blocks reproduced; assembly pending |
| P3 | Quantum ladder in tumour growth (L0 HW CHSH, L1 D-2, L1′ D-5, BP frontier) | 2028 | research |

---

## Run it

**MVP** (from `code/`; details in [`code/README.md`](code/README.md)):

```bash
python -m f1_quantum.run --backend aer --tiles 12 --pairs 2          # quantum roll (simulator)
python -m imaging.lidc_fetch LIDC-IDRI-0481                         # once: public Siemens-scanner CT (~136 MB)
python -m imaging.build_tiles --run ../research_runs/<run> --compare  # grow + render (~4–11 min CPU)
python -m f3_web.build_web --run ../research_runs/<run>             # -> ../web/index.html
```

**RE pipeline**: from `plans/relatedPapers/reverse-engineering/`, `python -m <L>_<name>.src.<module>`. Chain probe:
`python -m INT_integration.src.chain --probe`.

Hardware jobs are run by Peter only, from a pre-saved `QiskitRuntimeService()` account. No tokens in code.

---

## Honesty gates (short version; full list in [`CLAUDE.md`](CLAUDE.md))

- Every quantum number carries a claim level, a classical baseline, a BP simulability number and a label
  (`simulated: ideal`, `simulated: Heron-class noise (FakeMarrakesh)`, `hardware: <backend>, job <id>`).
- Simulated CHSH certifies nothing. S ≤ 2 means fail: no seed, the draw rejected and logged.
- Diagonal observables (⟨σz⟩, cell counts, growth curves) have exact classical surrogates.
- Privacy comes from parameter-only construction (no patient voxels in a generator), not from the quantum
  certificate.
- Record non-matches as results. "Advantage is the exception; measuring it is the result."

---

## Next up

1. **C (MVP):** record job IDs, add the S ≤ 2 reject gate, batch F1 into one job, fix the backend name in the docs.
   Then the first F1 hardware run.
2. **G-lite (MVP):** a record per run (hash of `tiles.json` + job IDs + code commit).
3. **INT (RE):** close the A→H chain (G `fill --job` append, D founder from B's draw, first beacon pulse after the commit).
4. **Feed back to RE E/F** the three real-host findings from F5: enclosed holes, volume-preserving edge, vessel-free σ shell.
5. **A (MVP):** real lobes (TotalSegmentator) to replace the z-band proxy; more Siemens hosts (`-0507`, `-0736`).
6. Re-tune D-5 so the L1′ gap clears the sampling floor.

---

## Key documents

- [`CLAUDE.md`](CLAUDE.md): working rules, honesty gates, Siemens wording.
- [`plans/siemens-fit-analysis-and-pitch.md`](plans/siemens-fit-analysis-and-pitch.md): fit verdict, weaknesses, twin ladder, people.
- [`plans/publication-plan-3-papers.md`](plans/publication-plan-3-papers.md): papers P1–P3 and thesis chapters.
- [`plans/relatedPapers/reverse-engineering/pipeline-overview.md`](plans/relatedPapers/reverse-engineering/pipeline-overview.md) and `future.md`: weakest links; 5/10/15-year forecast.
- [`plans/siemens-8-certified-quantum-virtual-cohorts.md`](plans/siemens-8-certified-quantum-virtual-cohorts.md): original concept (§3.7 CHSH 1.96 error).

---

## Changelog

| Date | Change |
|---|---|
| 2026-10-31 | **D-SCALE built (sim) and first live hardware runs:** `code/dscale/` (4 families × 40/100/120 q, survival map, Pauli-twirled 156-q model, BP copy 104× faster); quantum seed shapes now drive F5's grower. Live on ibm_kingston / ibm_marrakesh: first hardware CHSH S = 2.733 with the cohort rolled on the QPU, QCA witness L1 (marginal), GHZ spine L0. Found: dead qubit inside a GHZ tree (T1/T2 gate added), seeds larger than the tumour (capped at ½ Ø), hardware roll size mix not matched. RE pages updated. |
| 2026-10-31 | **F5 done (sim):** `f2_imaging` → `imaging`; grown renderer (RE E + F copy) in Siemens LIDC-IDRI-0481; pixel-growth player. Found three RE issues visible only on a real host (enclosed growth holes, render volume drift, vessel-inflated σ shell). README created. |
| 2026-10-29 | RE letters A–H merged; INT pass 1 (runner, probe, readiness, Future). |
| 2026-10-28 | RE epic approved; W foundation built. |
| 2026-10-26 | MVP epic approved; F1–F4 built on the simulator. |
