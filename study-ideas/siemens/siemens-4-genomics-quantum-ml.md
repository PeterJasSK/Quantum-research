# Siemens Idea 4 — Genomics Quantum-ML, Honestly: does a quantum kernel classify disease-risk from genomic features better than a classical SVM, or does the data-loading wall erase any advantage?

**Tag: QUANTUM · siemens · effort: medium**

## Pitch
Jan named genome mapping + future-disease prediction, and there is a real on-hardware precedent to point at (Moderna + IBM ran mRNA-structure optimization on a 156-qubit Heron device, 2025). That makes genomic quantum-ML the most *sellable* candidate — and, honestly, the least likely to show advantage, because loading genomic features into a quantum feature map is exactly where the data-loading cost kills QML. The study's job is to make that honesty *measured*: build the quantum kernel, build the classical baseline, and show precisely where (and why) the advantage does or does not survive.
**Paper strength score: 60/100** — strong buzzword/sell value and a real hardware precedent, but quantum-kernel-vs-SVM with no advantage is the most saturated, least-honest corner of QML; the contribution is the *honest data-loading post-mortem*, not a win.

## How it becomes a study
**Research question:** On a small genomic disease-risk classification task, does a quantum kernel (quantum feature map) beat a classical kernel SVM, and how does any gap scale with the number of genomic features loaded?
**Hypothesis (falsifiable):** The quantum kernel matches but does not beat a classical RBF-SVM at low feature counts, and its advantage (if any) vanishes as feature count grows because encoding depth/cost grows faster than classical difficulty.
**Method:** Public genomic/clinical dataset reduced to a handful of features. Build a quantum-kernel classifier (statevector + small hardware) and a classical SVM. Sweep the number of encoded features; measure accuracy and encoding depth/cost.
**Baseline:** Classical kernel SVM (RBF / linear) on identical features and splits.
**Metrics:** classification accuracy / AUC quantum vs classical; encoding circuit depth vs feature count (the data-loading cost curve); the feature count at which quantum accuracy plateaus or encoding becomes infeasible.
**Novel contribution:** A clean, measured demonstration of *where the data-loading wall erases genomic quantum-ML advantage* — the honest counter-narrative to the genomics-QML hype, framed for Siemens' precision-medicine interest.

## Connection to what already exists
Methodologically a sibling of the repo's "advantage is the exception" thesis (`np-query-advantage-map`) — same spirit of mapping where a claimed quantum advantage survives vs collapses, applied to QML/genomics. No existing repo study touches genomics.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Lets you *honestly* address the genome ask Jan raised, with a real hardware precedent (Moderna-IBM) to anchor credibility.
**Bear:** The field is flooded with "quantum kernel ≈ classical SVM" papers; a pure null risks reading as derivative.
**Likely:** Quantum kernel ties classical at tiny feature counts, loses as features grow — the expected data-loading result.
**Value if null:** The data-loading cost curve is the honest artefact Siemens needs to *not* over-invest in genomic QML prematurely — a credibility-building "here's why this one waits" result.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Does genomic quantum-ML advantage survive the data-loading cost? **Single defended claim:** quantum-kernel accuracy ceases to track feature growth once encoding cost outpaces classical difficulty — measured crossover. **Why 6–8 pp:** one dataset, one accuracy + one encoding-cost figure. **Target venue:** IEEE QCE workshop / QML venue. **Compelling-study likelihood: 60/100.**
