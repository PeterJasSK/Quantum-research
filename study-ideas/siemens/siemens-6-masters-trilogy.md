# Siemens Idea 6 — Master's Trilogy: quantum *sampling* of medical imaging forward-physics (NOT QML), three continuous conference-publishable deliverables

**Tag: QUANTUM · siemens · effort: medium-high · spans the whole master's**

Companion to `siemens-6-quantum-imaging-physics-sampler.md`. This file is the **3-paper program** that carries one research line across the master's and produces a presentable, measurable deliverable three times, even when results are null.

## Hard constraint from Siemens: NO quantum machine learning
They explicitly do **not** want QML (no classifiers, no quantum kernels, no feature maps, no downstream ML detector). They want **image/physics sampling and the potential in that field**. So this program is built on *sampling*, not learning:
- The sampler is a **physics-encoded quantum circuit with zero training** — a discrete-time quantum walk (DTQW) / transport-operator circuit whose unitary dynamics *are* the scatter/transport physics, so measuring it samples the physics **by construction**. (Precedent, no learning: DTQW for photon cross-sections, arXiv 2502.14374; MC particle transport via DTQW, arXiv 2410.19489.)
- There is **no learned generative model, no Born-machine training loop, no ML pipeline anywhere**. If a parametric sampler is ever used it is fixed by the physics, not fitted to data.
- The value question is a **sampling-complexity** question, not an accuracy-vs-classifier question: *is the distribution this quantum circuit samples classically hard to sample, and where does that hardness switch on?* That is "the potential in the field," made measurable.

## The one trick that guarantees 3 publications under uncertainty
Make the publishable unit a **measured answer to "is this imaging-physics distribution classically hard to sample, and how faithfully can a quantum circuit sample it?"** — never "did I beat a classifier." The headline of every paper is a **number** (fidelity, classical-sampling cost, breakdown size) that publishes regardless of sign. Repo ethos: `thesis-4`, "advantage is the exception" — a null is a result.

## Why this keeps Siemens "in the quantum race" even on nulls
1. **Visible cadence** — three conference talks on quantum *sampling* for medical imaging-physics; competitors (GE, Philips) have nothing public here.
2. **An honest classical-hardness map de-risks the bet** — "quantum image-sampling pays off starting at ~X dimensionality / ~Y qubits" is exactly the 10-year-horizon artifact they fund; a null with a measured cost-crossover curve is an asset.
3. **Owning the sampling-fidelity + hardness instrument** — being the group that can state, for any imaging-physics distribution, whether quantum sampling is faithful and whether it's classically hard = a defensible position regardless of whether advantage has arrived.

## Continuity (why it's one research line)
P1 builds the **physics-encoded sampler + the classical-hardness probe**. P2 reuses both on real hardware and adds a dimension. P3 reuses both on a structured 2-D imaging field and charts the potential map. One codebase, one instrument, escalating scope: **1-D primitive → hardware 2-D → image-level field + potential map.**

---

## PAPER 1 — "Sampling the physics." A physics-encoded quantum sampler for photon interactions (simulation-first)
**Question:** Can a training-free, physics-encoded quantum circuit (DTQW / transport-operator) sample the 1-D photon-interaction distribution (Compton scatter angle, or free path-length) faithfully, and is that distribution classically hard to sample at this scale?
**Build:** encode the Klein–Nishina / transport kernel directly into a quantum-walk unitary (no fitting); measure the walker to draw samples. Reference = analytic Klein–Nishina + a Geant4 1-D histogram. Statevector → noisy sim → small hardware confirm. Instrument = a **classical-sampling-hardness probe**: can a matched classical sampler reproduce the output distribution, and at what cost. Optional honest side-result: quantum amplitude estimation of a derived scalar (mean scatter angle / scatter fraction) with its **provable quadratic** query count vs classical sample count.
**Measurables (presentable numbers):** KS / Wasserstein fidelity to the physics reference; qubit + circuit-depth budget; classical-sampling cost to match the output (the hardness verdict); QAE query count vs classical samples for the derived scalar.
**Null value:** "1-D photon physics is classically easy to sample — no sampling advantage at this scale; here is the fidelity baseline and the quadratic-estimation check." Clean, honest, publishable.
**Venue:** IEEE QCE (Quantum Week) short paper / a quantum-simulation workshop. **Hardware risk: LOW** — the de-risk gate for the whole program.
**Timing:** months ~0–5 (first conference).

## PAPER 2 — "On the metal, up a dimension." Hardware fidelity and where the classical cost starts to bite
**Question:** How far does the physics sampler's fidelity survive on real IBM Heron hardware, and as the distribution goes from 1-D to 2-D (joint scatter angle × scattered energy, parameterised by photon energy and absorber material — all set by physics, not learned), does classical sampling cost start to grow?
**Build:** run the P1 sampler on Heron-156q with dynamical decoupling / error mitigation (CERN-style sampling-on-hardware precedent: muon-detector scatter QCBM, arXiv 2205.07674); extend the quantum walk to the 2-D joint distribution; sweep circuit depth.
**Measurables:** hardware fidelity-vs-depth curve; breakdown size n* (depth/qubits where fidelity crosses a usefulness threshold); classical-sampling cost vs dimension (does 2-D correlation start to cost?); mitigation ROI (DD/ZNE gain).
**Null value:** "hardware isn't there yet — measured gap + scaling slope"; and "2-D is still classically cheap, here's the cost curve." Both are the 10-year-horizon artifact.
**Venue:** IEEE QCE full/short; cross-submit a medical-physics venue (AAPM / MICCAI workshop). **Hardware risk: MEDIUM** (needs IBM QPU time — concrete Siemens-funded spend).
**Siemens-race value:** the visible real-hardware result on a Siemens-relevant imaging-physics task.
**Timing:** months ~5–11.

## PAPER 3 — "The image-level field and the potential map." Sampling a structured 2-D scatter field + where quantum sampling could matter
**Question:** Can the quantum sampler produce a *structured 2-D imaging-physics field* (a scatter map / small sinogram patch across a detector array — the image-sampling object proper), and over dimensionality + correlation structure, where does classical sampling cost grow fast (quantum headroom) vs stay cheap?
**Build:** scale the sampler to a small 2-D detector-array scatter field; reference = a Geant4 scatter field. Chart the **classical-sampling-cost-vs-structure** map: sweep field size / correlation length and measure how fast a matched classical sampler's cost grows; extrapolate the crossover regime and the qubit/error budget to reach it.
**Measurables:** 2-D field fidelity to Geant4; classical-sampling-cost-vs-dimension/correlation curve (the headroom map); extrapolated crossover regime + the qubit/error-rate budget to get there (the explicit scaling path); fidelity retained on hardware.
**Null value:** "at reachable scales the imaging-physics field is classically easy to sample; the measured cost curve projects the crossover at ~X — the 10-year target." Thesis-grade regardless.
**Venue:** IEEE QCE full; MICCAI / medical-physics workshop. **Hardware risk: MEDIUM** (sampler runs in sim for the large maps; hardware for the fidelity anchor).
**Siemens-race value:** an honest map of where quantum image-physics sampling has potential + the scaling path = the fundable story and thesis capstone.
**Timing:** months ~11–18.

---

## Sequencing, dependencies, hedge
- **Build order = paper order**; each artifact feeds the next. P1 is the de-risk gate — ship before committing QPU budget.
- **Shared asset:** one physics-encoded sampler + one classical-hardness probe, reused three times. ~60% of P2/P3 code is P1's.
- **Physics-target fallback:** if Compton scatter is too hard to encode, swap the physical channel (photon attenuation / free-path distribution, PET annihilation-angle) — instrument and program survive, because the contribution is *sample-the-physics + probe-its-classical-hardness*, not the specific channel.
- **Claim discipline:** never claim to beat Geant4/GATE at low dimension (classical MC wins there). Defended claims = sampling fidelity on hardware, the measured classical-hardness map, and the projected crossover — the *potential*, honestly bounded.

## Measurables cheat-sheet (every one presentable, publishes null-or-positive)
P1: fidelity-to-physics · qubit/depth budget · classical-sampling-cost-to-match · QAE query count vs classical samples.
P2: hardware fidelity-vs-depth · breakdown size n* · classical-cost-vs-dimension · mitigation ROI.
P3: 2-D field fidelity · classical-cost-vs-structure curve · extrapolated crossover regime · qubit/error budget to reach it.

## Connection to what already exists
Sampler lineage = the DTQW machinery in `QuantumGaltonBoard` (quantum walk → physical distribution) and `QuantumTree` (quantum sampling + certification), re-pointed at imaging physics. Classical-hardness probe = the classical-surrogate null-band method from `thesis-4-obscure-np-query-advantage` / `thesis-5-critical-quantum-life`, re-cast as a *sampling-cost* test. Hardware precedent = CERN openlab muon-scatter sampling (arXiv 2205.07674). Replaces the obvious pixel-GAN `siemens-2` and strips its QML framing.

## Thesis framing
Three papers = three chapters under one claim: *a training-free quantum circuit can sample medical imaging forward-physics distributions; its fidelity and the classical hardness of those distributions are measurable and bounded on today's hardware; and the honest map of where quantum sampling of imaging physics gains headroom is the deliverable Siemens needs for its 10-year quantum roadmap.* No QML, pure sampling. **Program likelihood: 76/100** — three independent null-tolerant shots, de-risked front-loaded, one shared asset.
