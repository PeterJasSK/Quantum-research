# Siemens Idea 6 — Sample the Physics, Not the Picture: can a training-free quantum circuit sample the *imaging forward-physics* (Compton scatter / photon transport), and is that distribution classically hard to sample?

**Tag: QUANTUM · siemens · effort: medium-high**

*(Single-idea spine. The 3-paper master's program built on this is `siemens-6-masters-trilogy.md`.)*

## NO quantum machine learning
Siemens explicitly does not want QML. This idea is **pure sampling**: a **physics-encoded quantum circuit with zero training** — a discrete-time quantum walk (DTQW) / transport-operator unitary whose dynamics *are* the scatter/transport physics, so measuring it samples the physics **by construction**. No learned generative model, no Born-machine training loop, no classifier, no feature map, no downstream ML. (Training-free precedent: DTQW for photon cross-sections, arXiv 2502.14374; MC particle transport via DTQW, arXiv 2410.19489.)

## Pitch
Every quantum medical-generative paper in the 2024–2026 literature mimics image *pixels* with a learned model — a crowded, QML-flavoured lane that loses to classical diffusion and is exactly what Siemens said they don't want. The non-obvious, non-ML move: don't learn the picture — **encode the physics into a quantum circuit and sample it**. A quantum walk whose unitary is the Compton/transport kernel produces samples of scatter angle, energy, and path-length directly from the physics. CERN openlab already sampled detector *scatter* on real IBM hardware (arXiv 2205.07674). No one has done it for medical imaging — open ground — and it maps onto Siemens' crown jewel: photon-counting CT (NAEOTOM) *is* photon-interaction physics. The honest value question is a **sampling-complexity** one, answered with the repo's classical-surrogate instrument re-cast as a cost probe: *is the distribution this circuit samples classically hard to sample, and where does that hardness switch on?* That is "the potential in image sampling," made measurable.
**Paper strength score: 74/100** — non-obvious, training-free (fits the no-QML constraint), hardware-precedented, Siemens-shaped, and honest-by-design because the classical-hardness verdict is the result; docked because mature classical MC engines (Geant4/GATE/MC-GPU/DeepDRR) win at low dimension, so the quantum contribution is fidelity + the hardness map, not a head-to-head beat.

## How it becomes a study
**Research question:** Can a training-free, physics-encoded quantum circuit sample a photon-interaction distribution (Compton scatter angle / free path-length, conditioned on photon energy by the physics) faithfully, and is that distribution classically hard to sample at reachable scale?
**Hypothesis (falsifiable):** A DTQW/transport circuit reproduces the Klein–Nishina / Geant4 reference to within sampling error, **and** a matched classical sampler reproduces the same output at comparable cost — i.e. at 1-D/2-D scale the physics is classically easy to sample and there is no sampling advantage yet, with the measured cost curve projecting where it would switch on.
**Method:** Encode the Klein–Nishina / transport kernel into a quantum-walk unitary (no fitting); sample by measurement. Reference = analytic Klein–Nishina + Geant4 histogram. Statevector → noisy sim → IBM Heron hardware. Instrument = a **classical-sampling-hardness probe** (can a matched classical sampler reproduce the output, at what cost, as dimension grows). Honest side-result: QAE of a derived scalar (mean scatter angle / scatter fraction) with its provable quadratic query count vs classical samples.
**Baseline:** Geant4/GATE Monte-Carlo for the physics reference; a matched classical sampler (inverse-CDF / KDE / MC) for the hardness control.
**Metrics:** KS / Wasserstein fidelity to the physics reference; qubit + depth budget; classical-sampling cost to match the output vs dimension (the hardness map); QAE query count vs classical sample count.
**Novel contribution:** First training-free quantum *sampler* of medical imaging forward-physics (scatter/transport), with an explicit measured map of where the sampled distribution is classically hard — reframing synthetic imaging-physics as a sampling-complexity question, not pixel-mimicry and not QML.

## THE VISUALIZATION
One screen, three panels sharing a photon-energy slider. Left: Geant4 scatter cloud (ground-truth physics). Middle: quantum-walk samples snapping onto the same Klein–Nishina arc as you drag energy — *conditioned physics sampled live, no training*. Right: a cost gauge — the classical-sampler cost to reproduce the quantum output, climbing as you add dimensions, with the verdict "classically easy here / projected hard at scale X." The thesis on one screen: *the quantum circuit samples the physics; the cost gauge tells you honestly whether that sampling is hard.*

## Connection to what already exists
DTQW sampling lineage = `QuantumGaltonBoard` (quantum walk → physical distribution). Classical-hardness probe = the classical-surrogate null-band method from `thesis-4-obscure-np-query-advantage` / `thesis-5-critical-quantum-life`, re-cast as a sampling-cost test. Hardware precedent = CERN openlab muon-scatter sampling (arXiv 2205.07674). Replaces the obvious, QML-flavoured pixel-GAN `siemens-2`.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** A genuinely new, non-ML framing (quantum *sampling* of imaging physics) with a real hardware precedent and a measurable hardness verdict — pointed straight at Siemens' photon-counting flagship, and exactly the "sampling potential" they asked about.
**Bear:** Classical MC physics engines are decades-mature; "faithful but classically easy to sample" could read as "why bother" unless the hardness-map + scaling projection is framed as the contribution.
**Likely:** The quantum walk reproduces 1-D/2-D scatter on hardware; the classical-sampling cost stays low at reachable scale — an honest "no sampling advantage yet, here's the projected crossover" result.
**Value if null:** The measured classical-sampling-cost curve *is* the deliverable — it tells Siemens where quantum image-physics sampling could pay off and the qubit/error budget to get there, feeding the "advantage is the exception" thesis and their 10-year roadmap.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Can a training-free quantum circuit sample medical imaging forward-physics, and is that distribution classically hard to sample? **Single defended claim:** a DTQW reproduces Compton scatter on hardware, but at reachable scale the distribution is classically easy to sample (matched classical sampler reproduces it) — faithful, bounded, and honestly mapped toward the projected crossover. **Why 6–8 pp:** one physics distribution, one fidelity figure + one classical-hardness-cost figure. **Target venue:** IEEE QCE short paper; medical-physics workshop cross-submit. **Compelling-study likelihood: 74/100.**
