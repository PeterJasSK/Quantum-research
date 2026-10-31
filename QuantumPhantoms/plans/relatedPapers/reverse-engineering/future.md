# Future: where Quantum Phantoms leads

Whole-pipeline outlook, written in INT (2026-10-29): cancer detection, other organs and body systems, the path toward a
digital twin, predictions at 5 / 10 / 15 years, and the risks. Today's state is on the [index](index.html)
and in the [INT gap list](INT_integration/README.md).

How to read this page: every claim carries a label. <span class="chip evidence">evidence-based</span> means a number in this repo or a cited paper code
(PDFs in `../papers/`). <span class="chip extrapolation">extrapolation</span> means a reasoned step beyond that evidence. <span class="chip speculative">speculative</span> means possible but not supported yet.
Each letter's README has its own Future section for its paper(s); this page covers the pipeline as a whole.

## 1. Aim of the work

Quantum Phantoms generates **synthetic lung tumours inside real 3-D chest CT**, with every step reproducible and
signed. The 21 reverse-engineering targets each rebuild one published method for one stage:

1. **Where a tumour sits** inside the lung anatomy (A).
2. **What kind of tumour it is**, drawn from cited statistics (B).
3. **How its randomness is certified** by a Bell test (C).
4. **How it grows quantum-mechanically** at the cell-fate level (D).
5. **How it grows as tissue** between baseline and follow-up (E).
6. **How it looks on a scanner** with that scanner's noise and blur (F).
7. **How it is traced** back to its signed inputs (G).
8. **How it is validated** against real patient scans (H).

Why it matters: AI that finds lung cancer on CT is trained and tested on scarce, unevenly labelled patient data.
Synthetic tumours with **exact ground truth**, **controlled difficulty** and **no patient voxels** can fill the
gaps, but only if they are realistic, traceable and validated. This project is about that credibility, not about
security and not about quantum speed-ups.

## 2. Contribution

- **Reproduced methods.** 13 targets are adapted and 6 dissected, and every one carries a published number checked
  against ours ([index](index.html) target table). Several honest non-matches are recorded: A #18, D #8, F #17, H R20b. <span class="chip evidence">evidence-based</span>
- **One contract layer.** 21 frozen contracts with stubs let every stage be built and tested alone, and the INT
  runner chains them through their own CLIs. <span class="chip evidence">evidence-based</span>
- **A claim ladder for "quantum".** L0 provenance, L1 entangled generative state, L1′ memory advantage; L2/L3 are
  out of reach today. Every quantum number ships its classical baseline and simulation label. <span class="chip evidence">evidence-based</span>
- **Privacy by construction.** Tumours are drawn from fitted parameters (about 4 KB of scalars from LIDC), never
  from patient voxels. This avoids the memorization risk of learned generators [H07, H08]. <span class="chip evidence">evidence-based</span>
- **A weak-link map** of the integrated chain ([INT gap list](INT_integration/README.md)): the three weakest edges are known and each has a fix. <span class="chip evidence">evidence-based</span>

## 3. Role in cancer detection

**Concrete end goal:** a generator of **certified, traceable synthetic lung-nodule CT cohorts**, with baseline
and follow-up, used to:

1. **Train** detection and segmentation models on cases that real data under-represents: juxtapleural, tiny or
   ground-glass nodules (A, B, E, F). <span class="chip extrapolation">extrapolation</span>
2. **Stress-test** them per location, size, type, scanner and dose with exact masks, finding blind spots before
   patients do. <span class="chip extrapolation">extrapolation</span>
3. **Measure growth assessment**: reported vs true volume and doubling time on a commercial assistant, using
   H's #21 protocol with E's baseline/follow-up pairs. <span class="chip extrapolation">extrapolation</span>
4. **Document** every case so a regulator or clinical partner can replay how the test set was made (C, G). <span class="chip extrapolation">extrapolation</span>

Today the pipeline is a simulated research chain: no part of it is clinically validated, and the chain stops at G
(INT findings). <span class="chip evidence">evidence-based</span>

## 4. Beyond lungs: toward comprehensive medicine

| Direction | What carries over | What must be new | Label |
|---|---|---|---|
| Liver, kidney, pancreas lesions | A's segment-then-sample, E's automaton (Pixel2Cancer already covers these organs [E01]), F's insertion, G, H | organ rulebooks, organ HU libraries | <span class="chip extrapolation">extrapolation</span> |
| Breast, brain | B's compiler, G, H (VICTRE is a breast trial [H03]) | organ anatomy and imaging physics (procedural breast phantoms [H12]) | <span class="chip extrapolation">extrapolation</span> |
| MR and other modalities | A, B, C, E, G, H unchanged | F's physics model (signal, coil noise) | <span class="chip speculative">speculative</span> |
| Monitoring | E's baseline/follow-up pairs; H's growth-error protocol | longitudinal validation data | <span class="chip extrapolation">extrapolation</span> |
| Treatment planning | A's distances to airways/vessels; F's exact masks for contour QA | dose and margin models | <span class="chip extrapolation">extrapolation</span> |
| Drug and therapy response | E's proliferation and death rules; B's conditional tables | response parameters fitted to trial data | <span class="chip speculative">speculative</span> |
| Diagnosis beyond cancer | site sampling in vessel/parenchyma masks (emboli, emphysema) | lesion models for each finding | <span class="chip speculative">speculative</span> |

The architecture is not cancer-specific: anatomy → knowledge → certified randomness → dynamics → imaging →
provenance → validation is a generic recipe for **synthetic, auditable medical evidence**.

## 5. Long-term vision: a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> A **digital twin** here means a computational copy of one patient that is updated from their own scans and
can be run forward to answer "what will this look like next time?" and "what if we treat it this way?". The
current pipeline is an early, generic version of several of its layers. The logical path, each step building on
the one before:

| Step | Twin layer | Today | What has to happen | Label |
|---|---|---|---|---|
| 1 | Anatomy (A) | generic LIDC host + sampled site | the patient's own segmentation; all organs [A04, A05] | <span class="chip extrapolation">extrapolation</span> |
| 2 | Knowledge (B) | cited tumour rulebook | patient-level network: risk factors → phenotype | <span class="chip extrapolation">extrapolation</span> |
| 3 | Dynamics (D, E) | population-calibrated growth | parameters fitted to the patient's serial scans; therapy rules | <span class="chip speculative">speculative</span> |
| 4 | Imaging (F) | image-domain insertion with a host fingerprint | full scanner simulation [F04]; any scanner, any dose | <span class="chip extrapolation">extrapolation</span> |
| 5 | Trust (C, G) | simulated certificate; signed receipts | hardware certificates; PKI; post-quantum signatures | <span class="chip extrapolation">extrapolation</span> |
| 6 | Validation (H) | n = 1 report | each forecast checked against the patient's next real scan | <span class="chip speculative">speculative</span> |
| 7 | Twin | — | steps 1–6 coupled and updated continuously, accepted as decision support | <span class="chip speculative">speculative</span> |

Virtual clinical trials on stochastic digital human cohorts [H04, G03, G02] are the realistic intermediate goal:
a population of synthetic patients, not yet one specific person. That is where steps 1–6 pay off first.

</div>

## 6. Predictions

The predictions follow a twin ladder with three rungs. Each rung reuses the A–H pipeline and changes what the
pipeline is fitted to:

1. **Population twin:** synthetic patients, nobody in particular.
2. **Calibrated twin:** one real patient's serial scans.
3. **Predictive twin:** "what if we treat it this way?".

The quantum role grows one claim level per rung, and only when the hardware earns it. The steps refer to the
twin table in §5.

### Population twin: now to 3 years

**What it is:** synthetic cohorts. Generic patients built from public data, used to train and stress-test detection
AI. **Quantum role:** L0 provenance and small L1′ blocks.

*Assumptions:* Heron-class noisy quantum hardware (error mitigation, no error correction); public LIDC and Mayo
data; classical compute as today; no clinical partner data.

- **INT.** The chain runs end to end in simulation after the three known fixes: `fill --job` binds every job,
  D grows from B's draw instead of a fixed founder, and C takes the first beacon pulse after the commit and never
  reuses one. One tumour travels A→H with a verifying receipt. <span class="chip extrapolation">extrapolation</span>
- **A, E, F (classical core).** These carry the value at this rung:
  - A: anatomy-informed placement in three classes. Its juxtapleural rule still needs fixing; it undercounts at n = 9.
  - E: lung Pixel2Cancer growth, with baseline and follow-up +90 days.
  - F: scanner-matched 3-D insertion (fingerprint within 2 %, XCIST projection insertion within 3 %).

  <span class="chip evidence">evidence-based</span>
- **H.** A pilot cohort (20 hosts × 3 placement classes) gives the first powered numbers: realism (HU, edge, NPS
  vs LIDC), train-synthetic/test-real and a small visual Turing test. <span class="chip extrapolation">extrapolation</span>
- **B, C (L0).** B's context-conditioned draw (B-1) is fixed before the run. One hardware CHSH run turns C's
  "certification-ready" into a real, accounted certificate (H_min → certified bits → seed), though not a
  loophole-free one. <span class="chip extrapolation">extrapolation</span>
- **D (small L1′ blocks).** Quantum stays small:
  - the D-5 causal-state growth model on 1–4 qubits, re-tuned so the C_q < C_μ gap sits clearly above the sampling
    floor (today it does not);
  - the D-2 lineage witness on a short dynamic circuit.

  Large circuits are noise-dominated (B: TVD 0.57–0.74) or BP-simulable (D: lineage χ = 2).
  <span class="chip evidence">evidence-based</span>
- **G.** Every case can be replayed from its signed record. The cohort is a documented, auditable test set.
  <span class="chip evidence">evidence-based</span>

### Calibrated twin: 3 to 7 years

**What it is:** growth fitted to one patient's serial scans. The model forecasts the next scan and is checked against
it. **Quantum role:** L1/L1′ on hardware.

*Assumptions:* devices running 10⁴–10⁵ two-qubit gates with mitigation [H11]; access to multi-centre and
longitudinal CT under agreement; accepted methods for virtual imaging trials [G02].

- **A.** The generic LIDC host is replaced by the patient's own segmentation: lungs first, then all organs with
  TotalSegmentator [A04, A05]. <span class="chip extrapolation">extrapolation</span>
- **B.** The tumour rulebook becomes a patient-level network: risk factors and prior findings select the
  conditional tables. <span class="chip extrapolation">extrapolation</span>
- **E.** Growth parameters are fitted to the patient's baseline and follow-up instead of population VDTs. Forecasts
  of the next scan are evaluated retrospectively. <span class="chip extrapolation">extrapolation</span>
- **F.** Insertion moves to projection domain on Siemens raw data (Mayo-style, XCIST) and to a closer NAEOTOM Alpha
  model. Today's f50 mismatch (0.57 vs 0.39 mm⁻¹) is closed with vendor parameters. <span class="chip extrapolation">extrapolation</span>
- **H.** The AI-Rad Companion protocol (#21) measures reported vs true volume and doubling time on known-truth
  longitudinal pairs. Certified cohorts serve as **supporting evidence** for validating a nodule-detection product,
  in the style of VICTRE [H03]. <span class="chip extrapolation">extrapolation</span>
- **D (L1/L1′ on hardware).** The entangled lineage (D-2) and the quantum growth-process model (D-5) run on real
  hardware with a witness that survives noise. The quantum model compresses the memory of patient-level growth
  processes. Every circuit keeps its BP simulability number. The D-3 QCA patch must first pass its witness above
  12 qubits, which it fails today under Heron-class noise. <span class="chip extrapolation">extrapolation</span>
- **C, G.** Certified randomness from device-independent sources becomes a routine provenance stamp [C06, C07].
  The receipt binds every hardware job. <span class="chip extrapolation">extrapolation</span>
- **Beyond lungs.** The same pipeline produces liver and kidney cohorts (E's automaton already covers these organs
  [E01]). <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

### Predictive twin: 10 to 15 years

**What it is:** "what if we treat it this way?". The calibrated twin is run forward under candidate therapies.
**Quantum role:** L2/L3; this needs fault-tolerant hardware.

*Assumptions:* **fault-tolerant quantum hardware** is available (deep, error-corrected circuits); twin-style
patient models are in research use and accepted as decision support.

- <span class="chip speculative">speculative</span> **E, B.** Therapy-response rules are added to the growth engine.
  These are proliferation and death rates under treatment, fitted to trial data, and connect to radiation-therapy
  planning. B's network carries treatment as a variable.
- <span class="chip speculative">speculative</span> **A, F.** Whole-body anatomy and other modalities (MR) use the
  same A–H recipe. Only F's physics model changes.
- <span class="chip speculative">speculative</span> **D, B (what fault tolerance would unlock, L2/L3):**
  - Amplitude-amplified sampling of very large patient-level networks [B01], for rare-event probabilities.
  - Quantum solvers for nonlinear growth equations [D21].
  - Simulation of large stochastic tissue models beyond classical tensor methods (D; the 108-qubit L2 plan below
    is the first measured step toward this).
  - Certified randomness whose guarantee rests on classical hardness [C02].

  None of this is shown today, and the end-to-end gain (including readout) is unproven.
- <span class="chip speculative">speculative</span> **G (what fault tolerance would break):** today's Ed25519
  receipts. Provenance must move to post-quantum signatures first.
- <span class="chip speculative">speculative</span> **H.** Each forecast is checked against the patient's next real
  scan. Twin cohorts become a standard arm of regulatory evidence, with every simulated patient traceable to
  certified inputs.

</div>

## 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Hardware noise | technical | deep quantum circuits are noise-dominated today (B, D) | shallow circuits; claim ladder; ideal draw + certificate |
| Classical simulability | technical | BP or tensor methods may match the quantum parts | publish the BP number next to every quantum claim |
| Integration gaps | technical | the chain stops at G; D ignores B's draw (INT) | fix list in [INT](INT_integration/README.md) |
| Domain gap | validation | synthetic lesions may be detectable as synthetic | visual Turing tests [F10]; train-synthetic/test-real |
| Small n | validation | n = 1 in INT; pilot never run | pilot and multi-centre cohorts |
| Data access | data | longitudinal and raw-projection data need agreements | public sets first (LIDC [A02], Mayo [A06]) |
| Privacy | regulatory | learned generators can memorize patients [H07, H08] | parameter-only rendering (kept) |
| Acceptance of synthetic evidence | regulatory | regulators accept in-silico evidence case by case [G02] | follow virtual-trial guidance; full provenance |
| Overclaiming "quantum" | regulatory | invites distrust from clinicians and reviewers | labels on every number; no claims above the evidence |
| Post-quantum transition | technical | fault-tolerant hardware breaks today's signatures | plan the migration of G's receipts |

## Disclaimer: what "quantum" is allowed to mean here

Every quantum statement on this page, and in the letters' Future sections, is bounded by this claim ladder. Claims
at L2 or L3 appear only in the 15-year blocks, labelled speculative, under the assumption of fault-tolerant hardware. All quantum numbers in this repo are simulated (AerSimulator ideal or
FakeMarrakesh Heron-class noise); no hardware result exists yet, and nothing here is clinically validated.

<div class="table-wrap">
<table>
  <thead><tr><th>Level</th><th>Claim</th><th>Where</th><th>Status</th></tr></thead>
  <tbody>
    <tr><td class="lvl">L0</td><td>Provenance: the randomness came from a CHSH-checked quantum source and is accounted for (certified bits → extracted seed).</td><td>C, B-1</td><td>Reachable</td></tr>
    <tr><td class="lvl">L1</td><td>Entangled generative state, shown by a multi-qubit witness (e.g. ⟨XX⟩+⟨ZZ⟩) read in ≥ 2 bases.</td><td>B-2, D-2, D-3</td><td>Reachable</td></tr>
    <tr><td class="lvl">L1′</td><td>Quantum memory advantage: the causal-state model of a growth process needs less memory than any classical one (C_q &lt; C_μ). <strong>Headline result.</strong></td><td>D-5</td><td>Reachable</td></tr>
    <tr><td class="lvl no">L2</td><td>Classical hardness.</td><td>none today; <strong>planned: D at 108 qubits</strong></td><td class="no">Blocked today: shallow heavy-hex circuits are belief-propagation-simulable (Tindall). Target #9 turns this into a measured number. Planned target of the 108-qubit D (see below).</td></tr>
    <tr><td class="lvl no">L3</td><td>Fault-tolerant algorithms (Carleman PDE, amplitude estimation).</td><td>none</td><td class="no">Needs fault-tolerant hardware; out of scope.</td></tr>
  </tbody>
</table>
</div>

<p class="callout">Never claim "more realistic because quantum", "quantum biology", or "classically impossible". A
<strong>single-qubit</strong> phase dial measured in Z is a classical biased coin, so any interference claim must sit in
multi-qubit correlations read in at least two bases. Every quantum deliverable also ships its classical baseline and
its belief-propagation simulability number.</p>

### Planned: L2 in D at 108 qubits

<span class="chip speculative">speculative</span> D is the one stage planned to reach L2. Its 108-qubit version maps
how a tumour starts growing (cell lineage and the first tissue patch) onto one large entangled circuit on IBM's
heavy-hex chip. The modular contracts let D scale without changing any other letter. Today D runs at up to 21 qubits
in simulation, and nothing here claims L2 yet. The claim is earned only if all four hold:

1. **Entanglement across the whole patch**, not 54 separate 2-qubit blocks.
2. **Beyond the best classical simulators**: D's belief-propagation adversary, tensor networks and newer methods all
   fail to reproduce it. A 127-qubit IBM experiment was reproduced classically within weeks [HW04].
3. **Verified on hardware** by a witness that survives noise. The exact simulation used today is impossible above
   about 50 qubits, and the QCA witness already fails at 12 qubits under Heron-class noise.
4. **It shapes the tumour**: the seed shape and cell fates come from the hard part, and it gives something a
   classical growth model of the same size cannot.

If L2 does not hold, the fallback result is still valuable: a measured map of where D stops being classically
simulable (qubits, depth, noise).

