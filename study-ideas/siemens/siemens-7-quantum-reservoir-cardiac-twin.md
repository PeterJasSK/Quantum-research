# Siemens Idea 7 — First Rigorous Quantum-Reservoir Baseline for Cardiac Signals: does a barren-plateau-free quantum reservoir match a fair classical reservoir on ECG, tied to the patient-twin pillar?

**Tag: QUANTUM · siemens · effort: medium**

## Pitch
Quantum reservoir computing (QRC) feeds a time-series into a *fixed* quantum system and trains **only a classical linear readout** — so it sidesteps the barren-plateau / vanishing-gradient wall that kills variational QML *by construction* (the quantum part is never optimized; training is one convex regression). That makes it one of the few genuinely NISQ-honest QML settings. And the niche is near-empty: cardiac/ECG QRC has essentially zero prior art, QRC-tied-to-digital-twins returned zero papers, and even EEG has exactly one 2026 hardware paper (arXiv 2608.00139 — ran on real hardware, but classical still won the hard signal). Siemens Healthineers markets "patient twinning" (Digital Twin of the Heart, Mayo cardiovascular collab) as a stated pillar — so cardiac-QRC-for-twins is white space that sits on their roadmap. The honest pitch is not a win: it is **the first rigorous, fairly-benchmarked QRC baseline for cardiac signals** — the paper the field is missing because published "quantum wins" keep pitting tuned quantum models against undertuned classical ones (critique: arXiv 2607.09905).
**Paper strength score: 70/100** — genuinely uncrowded, NISQ-feasible today, barren-plateau-free, strong Siemens-pillar fit, and honest-by-design; docked because no quantum advantage has been shown (parity-at-best) so the contribution is a rigorous baseline, not a beat.

## How it becomes a study
**Research question:** On a cardiac time-series task (arrhythmia classification / short-horizon forecasting from ECG windows), does a fixed quantum reservoir match a *size-and-tuning-matched* classical reservoir (echo-state network), and where does the data-loading / observable-estimation cost dominate?
**Hypothesis (falsifiable):** The quantum reservoir reaches parity with a matched classical echo-state network at small feature dimension, but a *fairly tuned* classical baseline erases any apparent quantum edge, and shot-based observable estimation is the binding cost — i.e. no advantage, honestly demonstrated.
**Method:** Public ECG dataset (e.g. an open arrhythmia set), windowed. Encode each window into a fixed ~4–8 qubit Ising/random reservoir (no circuit training), measure Pauli observables as features, train a classical ridge/logistic readout. Run statevector → noisy sim → IBM Heron hardware. Critically: benchmark against an echo-state network of *matched feature dimension and matched tuning effort* (the fairness the critique paper says the field skips).
**Baseline:** Classical echo-state network / reservoir of matched size + an LSTM reference, same windows, same splits, same tuning budget.
**Metrics:** classification accuracy / AUC quantum vs matched classical; feature-dimension and shot budget needed for parity; the observable-estimation (shots) cost curve; accuracy on real hardware vs noiseless sim.
**Novel contribution:** The first fair, hardware-run QRC baseline on cardiac signals — a rigorous parity map (and honest cost accounting) in a niche that is currently empty, framed to Siemens' patient-twin pillar.

## THE VISUALIZATION
A beating-ECG strip feeds a small glowing quantum reservoir; measured observables stream out as a feature bar that a classical readout turns into a live arrhythmia call. Beside it, the matched classical echo-state network runs the same strip. A fairness dial sweeps the classical tuning budget from "undertuned" (quantum looks ahead) to "matched" (the gap closes to parity) — the honest story in one interaction: *the quantum edge is only there until you tune the classical baseline fairly.*

## Connection to what already exists
New capability for the repo — no prior QRC work — but reuses the calibration→best_chain→transpile→Sampler workflow and the fair-classical-surrogate discipline that runs through `thesis-4` and the QDEP classical-surrogate studies. Sits beside `siemens-5` (patient digital twin) as a different, more NISQ-honest route into the same Siemens pillar.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** First-mover in an empty, on-roadmap niche with a method that genuinely dodges the QML killer; cheap to run, honest to report.
**Bear:** Parity-at-best means the headline is "no advantage"; the contribution rests entirely on rigor and first-ness, which a tough reviewer may undervalue.
**Likely:** Quantum reservoir reaches parity with a matched classical reservoir at small scale; the fair classical baseline closes the gap; shots dominate cost — a clean, honest baseline paper.
**Value if null:** A rigorous "no advantage, here is the matched comparison and the shot-cost wall" is precisely the fair baseline the QRC-biomedical literature lacks (the field is full of unfair wins) — citable, and a straight answer for Siemens on whether cardiac QRC is worth a 10-year bet.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Does a quantum reservoir match a *fairly-tuned* classical reservoir on cardiac signals, on real hardware? **Single defended claim:** quantum-reservoir ECG performance reaches parity but not advantage once the classical baseline is size- and tuning-matched, with shot-based observable estimation the binding cost. **Why 6–8 pp:** one dataset, one accuracy-vs-fairness figure + one shot-cost figure. **Target venue:** IEEE QCE short paper; a biomedical-signal / computing-in-cardiology workshop. **Compelling-study likelihood: 70/100.**
