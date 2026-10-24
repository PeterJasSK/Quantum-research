# Siemens Idea 1 — Quantum Monte-Carlo Dose: where does the *proven* quadratic speedup for radiotherapy dose estimation survive the noise floor, and where does it collapse?

**Tag: QUANTUM · siemens · effort: high**

## Pitch
Radiotherapy dose is computed by Monte-Carlo particle transport — the exact workload where quantum **amplitude estimation (QAE)** has a *proven* quadratic speedup over classical sampling (not hype, a theorem). This is the single most defensible claim in all of QC-healthcare, and it maps directly onto a real €3.6 bn Siemens product line (Varian Eclipse/Ethos dose engines). The one published "quantum-enhanced radiotherapy dose" result (*Scientific Reports* s41598-025-05673-y, Jun 2025) is **simulation-only** — projected 8–15× with no qubit counts and no hardware. That leaves the *honest* question unclaimed: on real noisy devices, at what problem size does the quadratic advantage get eaten by depth and the noise floor? We measure the crossover.
**Paper strength score: 70/100** — the speedup is real and the Siemens fit is perfect, but the honest hardware answer is very likely "advantage not reachable until fault-tolerance," so the study's value is the *quantified cliff*, not a win.

## How it becomes a study
**Research question:** For a toy dose integral solved by QAE, at what oracle/qubit budget does the theoretical quadratic query advantage over classical Monte-Carlo still hold once device noise and circuit depth are included?
**Hypothesis (falsifiable):** On Heron-r2-class hardware the QAE estimate hits a noise-floor variance plateau before reaching the problem size where its query count beats classical MC — i.e. the crossover is *beyond* NISQ and the advantage is fault-tolerant-only.
**Method:** Implement canonical QAE (Grover-operator iterations, no QPE / maximum-likelihood AE variant to cut depth) for a 1-D then 2-D toy dose/attenuation integral. Sweep estimation precision ε and count (a) ideal oracle queries vs classical MC samples for matched ε — the theorem check — and (b) achieved ε on statevector-with-noise and on real hardware vs circuit depth.
**Baseline:** Classical Monte-Carlo integration of the identical integrand; samples-to-ε is the honest control.
**Metrics:** oracle-query count to reach ε (quantum) vs sample count (classical) — the quadratic check; measured ε-vs-depth on noisy sim/HW; the problem size n* where measured quantum ε stops improving (the cliff); logical-vs-physical depth.
**Novel contribution:** The first *honest hardware-feasibility map* of QAE for radiotherapy dose — turning a sim-only projection into a measured crossover size, with the Siemens/Varian dose engine as the named application.

## Connection to what already exists
Reuses the repo's amplitude-/depth-cliff methodology (same shape as `qh-7-grover-advantage-cliff.md` "advantage cliff" and the QuantumGaltonBoard depth-collapse study), and the calibration→best_chain→transpile→Sampler workflow already built. QAE Grover operator ≈ the Grover machinery in `qh-7`. No new hardware dependency beyond existing IBM access.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** You own the single honest, theorem-backed QC-healthcare claim that a Siemens radiation-oncology audience instantly recognises; the cliff figure is clean and citable.
**Bear:** QAE on NISQ is notoriously depth-hungry; you may not get *any* regime where measured hardware beats classical, making the "study" entirely a negative-depth characterisation.
**Likely:** Theorem holds in ideal sim (clean quadratic), collapses on hardware well before advantage — a publishable "not yet, here's exactly how far off" result that is *exactly* Siemens' 10-year framing.
**Value if null:** A quantified n* and depth budget is the thing a funder needs to decide the scaling path — "advantage arrives at ~X logical qubits / error rate" is more useful to Siemens than a hand-wave that it will work.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Is QAE's proven quadratic dose-estimation speedup reachable on today's hardware, and if not, how far off? **Single defended claim:** the quantum/classical crossover size for toy dose QAE lies beyond NISQ reach — measured, not assumed. **Why 6–8 pp:** one algorithm, one integrand family, one crossover figure + one depth-cliff figure. **Target venue:** IEEE QCE (Quantum Week) short paper / workshop. **Compelling-study likelihood: 70/100.**
