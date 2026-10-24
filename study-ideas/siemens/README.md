# Siemens Healthineers — healthcare quantum study ideas

Candidate studies for the Siemens thesis (pivot from security → sellable **healthcare** QC, small-now / scalable-10yr). Contact: Jan Majoros (Head of Offensive Security, Siemens) — but the ask is Siemens **Healthineers / healthcare**, not security.

Full scraped company deep-dive + ranking lives in repo-root `ideas.txt` **Part 6**.

## Two hard constraints (confirmed by the user — they override everything below)
1. **NO QML.** Siemens does not want quantum machine learning — no classifiers, kernels, feature-maps, learned generative models, or downstream ML. They want **image/physics SAMPLING and the potential in that field.** The main-thesis sampler is therefore **training-free** (a physics-encoded quantum walk whose dynamics *are* the scatter/transport physics).
2. **Deliverable = a 3-paper continuous research PROGRAM** toward the master's. Siemens pays conference travel to present ~3× during research; **null results are fine** — a visible cadence keeps Siemens "in the quantum race." Every paper's headline is a measurable number (fidelity / classical-sampling cost / breakdown size) that publishes null-or-positive.

## ⭐ Main thesis — quantum *sampling* of imaging forward-physics (the chosen line)
- `siemens-6-quantum-imaging-physics-sampler.md` — **spine.** Sample the imaging *forward-physics* (Compton scatter / photon transport) with a **training-free physics-encoded quantum walk** instead of mimicking pixels; a classical-sampling-hardness probe maps where the distribution is classically hard to sample. CERN hardware precedent (muon scatter, arXiv 2205.07674); Siemens photon-counting-CT fit; medical = open ground. **74/100 · want-to-do 4/5 · effort medium-high · QC yes (sim+hw)**
- `siemens-6-masters-trilogy.md` — **THE PROGRAM** (read this one). siemens-6 carved into 3 continuous, no-QML conference papers:
  - **P1** sample 1-D photon physics + classical-hardness probe (sim, de-risked, **first conference**, mo 0–5)
  - **P2** hardware fidelity on IBM Heron + 2-D joint scatter, where classical cost bites (visible race signal, mo 5–11)
  - **P3** structured 2-D scatter field + the classical-hardness *potential map* + scaling path (capstone, mo 11–18)
  - One shared physics-encoded sampler reused 3×; **program likelihood 76/100**.

## Non-obvious runner-up (different flavour)
- `siemens-7-quantum-reservoir-cardiac-twin.md` — first rigorous, fairly-benchmarked quantum-reservoir baseline for cardiac/ECG; barren-plateau-free; Siemens' patient-twinning pillar. Near-empty niche, honest "parity-not-advantage." **70/100 · want-to-do 4/5 · effort medium · QC yes (NISQ-small)** *(note: reservoir computing sits near the QML line — keep only as fallback given constraint #1.)*

## Original ranked menu (siemens-1..5 — the reactive map, obvious lane)
Ranked by Siemens-fit × honesty × feasibility. `siemens-2` is the crowded pixel-GAN / QML-flavoured lane — superseded by `siemens-6` as the non-obvious, no-QML replacement.
- `siemens-1-quantum-monte-carlo-dose.md` — honest hardware-feasibility map of QAE for radiotherapy dose (proven quadratic speedup; where the noise floor eats it). Varian fit, honesty anchor. Could be reframed as **uncertainty-quantification** (calibrated dose error bars, not speedup). **70/100 · 3/5 · high · QC sim-first**
- `siemens-2-quantum-generative-synthetic-imaging.md` — certifiably-quantum, non-memorising synthetic CT/MR distribution (certificate + privacy differentiator). **Obvious/sellable but QML-flavoured — superseded by siemens-6.** **73/100 · 4/5 · medium · QC yes**
- `siemens-3-treatment-plan-optimization.md` — QAOA on the radiotherapy beam-selection QUBO; crossover vs classical planner. Varian fit, NISQ-closer. **66/100 · 3/5 · medium · QC sim-first + small hw**
- `siemens-4-genomics-quantum-ml.md` — honest data-loading post-mortem: where quantum-kernel genomic disease-risk advantage collapses vs classical SVM (QML — against constraint #1; kept for completeness). **60/100 · 2/5 · medium · QC yes**
- `siemens-5-patient-digital-twin.md` — HHL/VQLS on a toy organ linear system; how much of the digital-twin promise survives read-in/read-out. Stated-pillar fit, most speculative. **58/100 · 2/5 · high · QC sim-first**

## Not drafted (reasons obvious — from the `ideas.txt` Part 6 map)
- Molecular-imaging / VQE chemistry — cleanest theory, worst Siemens fit (not pharma).
- Image reconstruction / HHL — data-loading wall, speculative.
- Quantum sensing (OPM-MEG / NV / SQUID) — hardware, not a QC algorithm; not the user's domain.
- Medical-data PQC / QRNG — Jan rejected the security angle.

## Next step
Graduate **trilogy P1** to a real build via `/plan-epic` (cheap, near-guaranteed, first-conference de-risk gate). Ideation stops here; planning is `/plan-epic`'s job.
