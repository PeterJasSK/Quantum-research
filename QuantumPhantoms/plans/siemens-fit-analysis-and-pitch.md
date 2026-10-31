# Quantum Phantoms / QSC: Siemens fit analysis, funding case and elevator pitch

**Date:** 2026-10-30 · **Inputs:** `siemens-8-certified-quantum-virtual-cohorts.md`, `epic-quantum-phantoms-mvp.md`,
`relatedPapers/reverse-engineering/{epic-reverse-engineering.md, pipeline-overview.md, README.md, future.md}`,
`INT_integration/README.md`, letter readiness markers.

---

## 0. Verdict in five lines

1. **Domain fit: very strong.** It is exactly what Siemens asked for: procedurally generated synthetic CT for
   training and testing detection AI, with no QML, small now and with a credible 10-year path.
2. **Quantum essentiality: weak today, and honestly so.** About 90 % of what Siemens would use (anatomy, growth,
   scanner-matched rendering, traceability, validation) is classical. Today's quantum contribution is L0 provenance
   plus small simulated L1/L1′ results.
3. **Credibility: much stronger than the MVP.** 21 published methods have been dissected, 13 adapted, and each one
   has a reproduced number, a classical baseline, a claim label and a belief-propagation (BP) simulability check.
   The rigour is the asset.
4. **Readiness: low.** Everything runs in simulation only, the A→H chain stops at G, n = 1, and the pilot cohort
   has not been run. There is a known hole in the provenance chain, which is the thing being sold.
5. **How to sell it:** a fundable *research programme*. Do not sell it as a quantum product. Sell a classical-strong
   **certified virtual-cohort engine** whose layers are the layers of a patient digital twin, with a **quantum
   socket** that is measured as hardware matures. Estimated funding odds: about 50 % with this framing, about 20 %
   if it is pitched as "quantum proves nobody chose" or with security language.

---

## 1. What was weak in the original system (siemens-8 + MVP), and what the reverse-engineering (RE) work fixed

| # | MVP-era weakness | What the RE epic changed | Residual |
|---|---|---|---|
| 1 | **Quantum = dice.** The CHSH pair sits *beside* the tumour qubits. Commit-then-reveal plus a public beacon replaces it classically (siemens-8 §7.1). | C now does the full accounting: Pironio H_min, hidden test rounds, Toeplitz extraction (40.8 vs 42 bits reproduced). D adds non-dice jobs: D-5 causal-state memory advantage (L1′), D-2 one-job dynamic-circuit lineage, D-3 heavy-hex QCA seed shape. | Every quantum number is simulated. The certificate is "certification-ready, not certified". The core "why quantum" objection is narrowed, not removed. |
| 2 | **Toy tumours.** About 10 parameters, a blob in a 2-D slice, cruder than X-Lesions (§7.4). | A: anatomy-informed placement. E: Pixel2Cancer + Kansal–Torquato growth ported to lung (3 of 4 stages match). F: lesion library fitted to LIDC (shape-fit agreement 0.87 vs paper 0.89), scanner fingerprint matched within 2 %, projection-domain insertion on XCIST within 3 %. All of it in 3-D. | No powered realism number yet: no train-synthetic/test-real result, no visual Turing test, n = 1. |
| 3 | **Unvalidated.** No study design beyond a histogram strip. | H: study architecture modelled on VICTRE, own MRMC statistics, CHO model observer, and a black-box protocol for AI-Rad Companion. | The pilot cohort (20 hosts × 3 placement classes) has never been run. |
| 4 | **"Quantum" overclaim risk** (P2 phase dial "no classical sampler"). | Claim ladder L0/L1/L1′ (L2/L3 blocked). Single-qubit dial = classical biased coin. BP adversary (#9) on every circuit. Labels enforced by schema. | None. This is now a strength. |
| 5 | **Security vocabulary** (Ed25519, ledger, tamper). Jan rejected this. | G is still built around signatures and a CT-GAN tamper test. | **Reframe still needed** (§5). |
| 6 | **Hand-wavy 10-year story.** | future.md has a 5/10/15-year forecast with an evidence/extrapolation/speculative label on every claim, plus a 7-step digital-twin ladder. | Good material, but too long for management. It needs the one-slide version (§4). |
| 7 | **Ad-hoc architecture** (one `Sampler` seam). | 21 frozen file contracts with stubs. Every stage runs alone, and the INT runner plus probe chain them. | The chain is not closed yet (§2). |

**Net:** the RE work turned a demo with a thin quantum story into a credible research pipeline with an honest
quantum story. It did **not** yet produce what management judges: one end-to-end case, one hardware number and one
utility number.

---

## 2. Remaining weaknesses that a Siemens reviewer will find

Ranked by how much damage each would do in the room.

1. **Factual error in siemens-8 §3.7: "CHSH certification (measured ~1.96 on `ibm_marrakesh`)".** The 1.96 is the
   GHZ witness ⟨XX⟩+⟨ZZ⟩ (entanglement bound 1), not CHSH (classical bound 2). Read as CHSH, 1.96 is a **failed**
   Bell test. Fix it before any Siemens deck. State it as "entanglement witness 1.96 vs bound 1.0 on Heron".
2. **Provenance hole in the product being sold** (pipeline-overview #3). No chain got a beacon pulse later than its
   commit, and two chains with different commits produced the **identical** seed `7dfb4d50…`. Anyone who checks
   "nobody chose" would find this first. The fix is small: take the first pulse after the commit, and refuse a pulse
   that was already used.
3. **The chain does not run end to end.** G `fill --job` keeps only the last job, so only D's job gets signed. D
   ignores B's draw and grows every tumour from one fixed founder. The epic's done-criterion is not met.
4. **The L1′ headline is not resolved yet.** For D-5, the exact 1-bit classical d_KL (0.00136) is *below* the
   sampling floor (0.00184) at the chosen parameters (Γ = 0.5, V = 0.4). The simulated advantage is therefore not
   distinguishable from sampling noise. Pick a strongly modulated process where C_q ≪ C_μ is resolvable before
   calling this "the headline".
5. **Zero hardware results** in the RE epic. "Quantum" with no QPU number reads as theory.
6. **No utility number.** Management will ask: "Does training or testing on this improve or expose our detector?"
   There is no answer yet.
7. **The buyer's pain is unproven.** No seed-shopping case in virtual trials has ever been reported (siemens-8
   §7.3). Selection bias is a risk the FDA names (Badano 2023), not a complaint from a customer.
8. **Too many directions at once.** 8 letters, 21 targets and a 108-qubit L2 plan look like research sprawl. Siemens
   funds one spine.
9. **Classical competition is strong.** NVIDIA MAISI, DiffTumor, Duke CVIT/X-Lesions. Do not compete on realism or
   volume. You lose there and do not need to win there.
10. **Privacy claim discipline.** Privacy comes from **parameter-only construction**, not from the quantum
    certificate. A witness does not certify non-memorization. Keep the two arguments separate in every sentence.

---

## 3. Fit scorecard (judgement, 1–10)

| Criterion | Score | Why |
|---|---|---|
| Matches Siemens' stated wish (synthetic CT for AI, healthcare, no QML) | **9** | Hits the named direction. Training-free by construction. |
| Siemens product hooks | **6 now / 8 potential** | These are **planned links, not Siemens data in use.** The 47 local LIDC hosts are all GE (46) or Toshiba (1); there are 0 Siemens scans. Mayo LDCT Siemens raw data was **not** used (it needs a TCIA agreement), so #16 ran on a synthetic XCIST phantom with a Siemens-Definition-like config. #17 takes the NAEOTOM Alpha parameters from the published DukeSim paper only; DukeSim itself is closed. AI-Rad Companion is a documented-interface black box (#21 dissected; the H protocol exists, no access). Cheap upgrade: pick Siemens-made LIDC hosts and apply for Mayo access. |
| Regulatory tailwind | **7** | FDA VICTRE, AAPM TG387, FDA cohort-bias concern. EU AI Act data governance for high-risk medical AI (Art. 10, *verify obligations and dates before citing*): synthetic training/test data with a replayable lineage is directly on-theme. |
| "Small now, scalable over 10 years" | **8** | Claim ladder L0 → L1/L1′ → L2 → L3 tracks IBM's hardware roadmap. Every rung is a measurable number, null results included. |
| Quantum essentiality today | **3–4** | L0 can be replaced by beacon + commit-reveal. L1/L1′ are small-block and simulated. Honest, but modest. |
| Technical credibility / rigour | **8** | Reproductions, baselines, BP adversary, labels, recorded non-matches. Rare in quantum-for-health pitches. |
| Readiness | **3** | Simulation only, chain broken at G, n = 1, no pilot. |
| Strategic position (white space) | **8** | Healthineers has no public quantum programme (our scrape, 2026-10-24), while the parent Siemens AG does industrial quantum. First-mover ground at low cost. |
| **Overall as a fundable research programme** | **≈7** | Strong fit *as a programme with a measured quantum frontier*. A weak fit if sold as a quantum product. |

---

## 4. How to sell it: a stepping stone to a quantum-ready digital twin

### 4.1 The core reframe

Do **not** sell "quantum makes tumours". Sell three things in this order:

1. **A virtual-cohort engine that is useful now.** Realistic, scanner-matched lung tumours in real CT, with exact
   masks, controlled difficulty, longitudinal pairs and no patient voxels. Every case can be replayed from its record.
   This is mostly classical and it is the value Siemens gets regardless of quantum.
2. **Every engine stage is a layer of a patient digital twin.** Siemens Healthineers already uses the digital-twin
   vision in its research messaging (*verify the current wording*). This engine is the population-level version
   of those layers, built with frozen interfaces so each layer can be upgraded from "generic" to "this patient".
3. **A quantum socket at the layer where quantum has a real job.** That layer is the stochastic dynamics: how a
   tumour grows and chooses cell fates. Quantum models of stochastic processes are the one proven place where
   quantum *simplifies* such a process (memory advantage, L1′). Today the socket is filled with small simulated
   blocks. With each hardware generation we **measure** how far it reaches. That measured curve is the investment
   signal.

### 4.2 The twin ladder (one slide)

| Stage | Twin type | What the engine does | Quantum role | When |
|---|---|---|---|---|
| **1. Population twin** | Virtual cohort: synthetic patients, nobody in particular | A–H pipeline: placement, growth, scanner render, lineage record, VICTRE-style validation | L0: certified randomness for the cohort draw. L1′: quantum growth-process model in small blocks (simulation, then a first hardware run) | **Now – 3 yr** |
| **2. Calibrated twin** | Growth model fitted to one patient's serial scans | E's growth parameters fitted to baseline/follow-up. Forecast of the next scan, checked against AI-Rad Companion's prior comparison | L1/L1′ on hardware: entangled lineage, compressed process memory for patient-level models | **3–7 yr** (mitigated Heron-class, 10⁴–10⁵ gates) |
| **3. Predictive twin** | "What if we treat it this way?" | Therapy-response rules (Varian link), multi-organ anatomy (TotalSegmentator), other modalities | L2/L3: sampling large patient Bayesian networks, rare-event amplitude estimation, stochastic tissue simulation beyond classical tensor methods. **Speculative, needs fault tolerance** | **10–15 yr** |

**Wording rule:** say "quantum-ready digital twin" or "the quantum layer of a future digital twin". Never say "we
are building a quantum digital twin". The first is accurate, the second is hype that a Siemens technical reviewer
will reject.

### 4.3 Why Siemens should fund it (the investment logic)

- **Cheap option on a strategic technology.** Thesis-scale cost: open data (LIDC, Mayo), simulation, a handful of
  QPU jobs, conference travel. If quantum matures, Healthineers holds the reproduced building blocks, the
  benchmarks and the people. If it does not, Siemens still keeps the classical engine and the papers.
- **Pays off even if the quantum part does not.** The classical virtual-cohort engine (longitudinal nodule pairs
  with exact ground truth) is directly useful for testing AI-Rad Companion's detection and growth assessment.
- **A measured frontier, not a promise.** Each paper reports a number that is publishable whether it is positive
  or null: the hardware certificate, the witness survival, the L1′ gap, and the BP-simulability boundary. Siemens
  is visibly "in the quantum race" (about 3 conference talks) without betting on an outcome.
- **Regulatory direction.** Synthetic evidence is being accepted case by case (VICTRE, TG387), and data governance
  for medical AI is tightening. A cohort engine with a replayable lineage and privacy by construction fits where
  regulation is heading.
- **White space.** Healthineers has no public quantum programme yet. First credible results define the narrative.

### 4.4 Vocabulary swap (Jan's rule: data credibility, not security)

| Avoid | Say instead |
|---|---|
| signature, Ed25519, ledger | data lineage, replayable record, audit trail |
| tamper detection, CT-GAN attack | integrity check: any edit to a case is visible |
| certified randomness against seed shopping | unbiased cohort draw: the case mix comes from a physics-checked source, fixed before the run |
| security, attacker, threat | credibility, traceability, regulatory evidence |
| "only quantum can prove nobody chose" | "the cohort is fixed by the rulebook before the run and drawn from a physics-checked source; every case can be replayed" |

---

## 5. What to fix before the pitch (ordered by return on effort)

1. **Correct the "CHSH 1.96" line** in siemens-8 §3.7 (≈ 5 minutes; it prevents losing credibility in the room).
2. **Close the chain** with the three known fixes: `fill --job` append, founder from the draw, beacon freshness plus
   no reuse of a pulse. Then run one tumour A→H with a verifying record. This is the "it works" moment.
3. **One real Heron job** for C (CHSH certificate with H_min) and the D-2 witness. This turns
   "certification-ready" into a real number and earns the word "quantum" in the room.
4. **Pilot cohort plus one utility number** (H): train-synthetic/test-real AUC and a small visual Turing test.
   This is the number management remembers.
5. **AI-Rad Companion growth-error demo** (H #21 protocol on E's longitudinal pairs): "your product's
   volume-doubling-time error on cases where we know the true answer". This is the most Siemens-native result
   available.
6. **Re-tune D-5** so the L1′ gap is clearly above the sampling floor before calling it a headline.
7. **Name the spine.** For Siemens: *certified longitudinal virtual cohorts for validating nodule AI*. For the
   quantum thesis: *D, the growth-process layer on the claim ladder*. Everything else is supporting work.

---

## 6. Elevator pitches

### 6.1 Management, 30 seconds (Quantum Synthetic Cultures)

> Siemens' lung-cancer AI needs test cases that are realistic, have perfect ground truth, contain no real patient,
> and can be traced by a regulator. **Quantum Synthetic Cultures** grows virtual tumours inside real chest CT: placed
> by anatomy, grown by validated tumour models, rendered with the scanner's own noise, with baseline and follow-up
> scans. Every case can be replayed from its record. It is useful today as a virtual-cohort engine for testing
> products like AI-Rad Companion. It is built so its growth layer runs on quantum hardware as that hardware matures,
> which makes it the first step toward the quantum layer of a patient digital twin. It is small and cheap now, and
> publishable either way. We measure the quantum path; we don't promise it.

### 6.2 Technical / science room, 30 seconds (Quantum Phantoms)

> Quantum Phantoms is a training-free pipeline for synthetic lung-nodule CT, built from 21 reverse-engineered
> published methods. Each one is reproduced against its paper and paired with a classical baseline. Quantum enters
> only where it has a job. A Bell test turns hardware randomness into an accounted, certified seed (L0). An entangled
> lineage and a quantum causal-state model of tumour growth need less memory than any classical model of the same
> process (L1/L1′). Every quantum circuit is also checked against a belief-propagation simulator, so "not classically
> hard" is a measured number, not a disclaimer. The deliverable is a working cohort engine plus a hardware-tracked map
> of where quantum stops being simulable.

### 6.3 One-liners

- **Management:** *Realistic virtual tumours with perfect ground truth and no patient inside, with a growth layer
  built to move onto quantum hardware as it matures.*
- **Twin framing:** *Today a virtual cohort, tomorrow a calibrated patient twin, with a quantum layer that grows
  with each hardware generation.*
- **Honesty line (keep it ready for the sceptic):** *We don't claim quantum makes better images. We claim a measured,
  labelled frontier: where quantum earns a job, and when.*

### 6.4 The ask (shape, not figures)

A 12-month, thesis-scale programme:
1. a closed A→H chain;
2. a pilot cohort of 20 hosts × 3 placement classes with a utility number;
3. one hardware certificate run and one witness run on IBM Heron;
4. the AI-Rad Companion growth-error protocol on synthetic longitudinal pairs;
5. two papers: SPIE Medical Imaging for the virtual-trial angle, IEEE QCE for the quantum frontier map.

Year 2 and later: patient-calibrated growth (twin stage 2) and the D scaling study.

---

## 7. Probability estimates (judgement, updating siemens-8 §9)

| Outcome | siemens-8 (MVP era) | Now (after RE, if §5 fixes 1–4 are done) |
|---|---|---|
| Siemens funds it | 35–45 % | **~50 %** with the twin + data-credibility framing; **~20 %** with security or "quantum proves" framing |
| Reviewers accept quantum as essential | 20–30 % (base) | **~30–40 %** as "essential"; **~70 %** as "honestly scoped and well measured", which is the bar Jan actually set |
| Programme delivers publishable results | ~70 % | **~80 %** (the building blocks already exist; null results publish) |
| L2 (classical hardness) at 108 q within the programme | n/a | **< 10 %**. Present it only as the frontier map, never as a promise. |

---

## 8. Using Siemens parts across the whole pipeline

**Today no stage uses Siemens data or software** (§3: all 47 local hosts are GE or Toshiba, #16 runs on a synthetic
phantom, #17 uses parameters from a paper, #21 has no access). This section maps, letter by letter, which Siemens
asset could fill each stage.

There are three tiers:

- **T0, public now:** no agreement needed. Can start immediately.
- **T1, research agreement:** a TCIA data-use agreement, or a Siemens / Duke research collaboration. Weeks to months.
- **T2, product integration:** Siemens provides tools, data or a product interface. This needs funding or a
  partnership, so it is part of the ask.

Product names and capabilities below come from public Siemens Healthineers material. Items marked *(verify)* must be
confirmed with Siemens before they go on a slide.

### 8.1 Per stage

| Stage | Siemens part | Tier | What it changes |
|---|---|---|---|
| **A** placement | **Siemens-made LIDC-IDRI host scans**: filter the TCIA series by DICOM `Manufacturer = SIEMENS` (the full collection is multi-vendor; count not checked yet) | T0 | Tumours sit in Siemens-scanner anatomy. Swapping the 20 hosts costs about a day of download and segmentation. |
| | **AI-Rad Companion Chest CT** lung and lobe segmentation *(verify output access)* as a second segmenter next to lungmask/TotalSegmentator | T2 | Siemens' own anatomy feeds the context vector; the agreement between the two segmenters is a free quality check. |
| **B** rulebook → circuit | **AI-Rad Companion / syngo.CT Lung CAD findings statistics**: aggregate nodule size/type/location frequencies on Siemens installs *(verify availability)* | T2 | Rulebook CPTs come from Siemens-population statistics instead of literature only. These must be aggregates, never patient records, to stay non-QML and privacy-by-construction. |
| **C** certificate | none: Siemens does not build QPUs. IBM Heron stays the hardware; the beacon stays NIST/CURBy | — | Keep it vendor-neutral. The parent Siemens AG's quantum activity (QUTAC) is a door-opener for hardware access, not a component. |
| **D** quantum growth | none directly. Siemens AG industrial quantum teams could co-review the quantum circuits | T2 | Credibility and hardware time, not data. |
| **E** classical growth | **Longitudinal Siemens CT pairs** from partner sites (baseline + follow-up, true growth from serial scans) | T1/T2 | Calibrates the growth rates on real Siemens-scanner doubling times. This is the bridge to the calibrated twin (§4.2, stage 2). |
| **F** render | **Mayo LDCT-and-Projection-data, Siemens SOMATOM cases** (TCIA, DICOM-CT-PD format) for #16 | T1 | Real projection-domain insertion on Siemens raw data instead of the synthetic XCIST phantom. Only Siemens cases may be used for Siemens work (epic §6). |
| | **Siemens reconstruction kernels and iterative reconstruction** (Br/Qr kernels, ADMIRE/SAFIRE, QIR on NAEOTOM) as published parameters or via a research reconstruction tool such as ReconCT *(verify name and licence)* | T1/T2 | The rendered tumour gets the same sharpness and noise texture a Siemens reader sees. This fixes #17's f50 mismatch (0.57 vs 0.39 mm⁻¹). |
| | **NAEOTOM Alpha detector response** (QE, crosstalk, noise covariance) provided by Siemens or Duke for the XCIST model (#17) | T2 | Turns the "Siemens-flavoured approximation" into a photon-counting model Siemens can sign off on. |
| | **CARE Dose4D tube-current modulation** profiles from the host DICOM | T0 | Noise varies along the scan as on a real Siemens exam. The data is already in the DICOM headers of Siemens hosts. |
| **G** lineage / provenance | **DICOM private tags plus Siemens' QMS** (ISO 13485 / IEC 62304 traceability practice), with optional storage of the record on **teamplay** *(verify)* | T2 | The replayable record lives in Siemens' own data platform and quality system, framed as data lineage for regulatory files, not security. |
| **H** validation | **AI-Rad Companion Chest CT** run on the synthetic longitudinal pairs: detection rate, volume error, doubling-time error vs known truth (#21 protocol) | T2 | The single most Siemens-native result: "your product's growth-assessment error on cases where we know the answer". |
| | **syngo.via Frontier** research platform *(verify)* to deploy the generator as a research prototype next to Siemens readers | T2 | Visual Turing tests and reader studies on Siemens workstations. |
| | **Siemens regulatory affairs** using the cohort as supporting evidence in a VICTRE-style submission | T2 | The end customer of the "credibility" argument. |
| **Twin stages 2–3** | **Varian Eclipse / Ethos** (treatment planning, adaptive radiotherapy) for therapy-response rules; Siemens AG's industrial digital-twin experience (Simcenter) for twin architecture *(verify fit)* | T2 | The predictive twin connects to a Siemens Healthineers business line (Varian ≈ 16 % of revenue). |

### 8.2 What this does to the pitch

With T0 and T1 done (Siemens LIDC hosts, CARE Dose4D noise, Mayo Siemens raw data), the honest sentence becomes:

> Synthetic tumours inserted into **Siemens-scanner CT**, matched to that scanner's noise and dose modulation, plus
> projection-domain insertion on **Siemens raw data**, all from public data.

With T2 the sentence becomes:

> Tested on **AI-Rad Companion**, rendered with **Siemens reconstruction**, and recorded in **Siemens' quality
> system**.

The product-hook score from §3 moves from 6 to about 9.

### 8.3 Order to do it in

1. **T0, now:** reselect the 20 hosts to Siemens-made LIDC scans and read the CARE Dose4D profiles from their headers.
   Re-run F #15 so the fingerprint measures a Siemens scanner.
2. **T1, start the paperwork now:** apply for the Mayo LDCT TCIA agreement, then re-run #16 on Siemens projections.
3. **T2, in the ask (§6.4):**
   - access to AI-Rad Companion for the #21 protocol;
   - the NAEOTOM detector response and reconstruction parameters;
   - aggregate nodule statistics;
   - a partner site with longitudinal Siemens CT.

### 8.4 Caveats

- **Keep a vendor-neutral path.** The "independent benchmark" argument (siemens-8 §8) needs cohorts no single vendor
  tuned. Ship Siemens-native as the main configuration and keep the GE/Toshiba LIDC path as the neutral baseline.
  Showing that a tumour renders correctly on both is itself a result.
- **Licences.** Never decompile AI-Rad Companion, DukeSim or Siemens reconstruction. Use documented interfaces and
  tools that Siemens provides under agreement only (epic §3).
- **Privacy rule unchanged.** Siemens data enters only as host backgrounds, fitted parameters or aggregate statistics.
  No patient voxels enter a generator.
- **Naming clash.** Siemens already uses "Quantum" in NAEOTOM marketing (photon counting, e.g. QuantumPeak, QIR).
  Say "quantum computing" explicitly so nobody hears "quantum" as detector physics.

---

## 9. People to reach out to (to make the project stronger)

**How to read the odds.** These are judgement calls, not measurements. Two numbers per person:

- **Cold:** an email from you alone, today.
- **Warm:** an introduction through Siemens/Jan, or an email with a working artifact attached (the closed A→H chain,
  the hardware certificate, a rendered cohort).

Every warm number assumes §5 fixes 1–3 are done. Researchers answer concrete offers ("here is your method rebuilt
for lungs, one number reproduced, can we compare?") far more often than open requests ("would you collaborate?").
Every person below has a dossier in this repo built on their work, and that dossier is your opener.

Affiliations were checked on 2026-10-30 (sources at the end of this section). Entries marked *(verify)* were not
confirmed in that check.

### 9.0 Where each name comes from

**Most names are authors of the papers that the pipeline reverse-engineers.** Authorship was checked against the
first page of the local PDFs in `relatedPapers/papers/`. A few names come from elsewhere, and they are flagged in the
table.

| Person | Basis | Paper code → RE target |
|---|---|---|
| Thomas J. Elliott | pipeline paper | D17 Elliott 2018 → #6 (D-5) |
| Mile Gu | pipeline paper | D06 Gu 2012 (also co-author of D17) → #6 |
| Zongwei Zhou, Alan Yuille | pipeline paper | E01 Lai et al., Pixel2Cancer 2024 → #11 (also the SyntheticTumors line, #13) |
| Ehsan Abadi, Ehsan Samei | pipeline paper | F04 McCabe 2025, DukeSim NAEOTOM → #17 |
| Fakrul Islam Tushar, W. Paul Segars | pipeline paper | A01 SYN-LUNGS 2025 → #18 |
| Heiko Enderling | pipeline paper | E03 Poleszczuk–Enderling 2014 → #12. The digital-twin angle comes from his lab page (web), not from the paper. |
| Joseph Tindall | pipeline paper | HW04 Tindall 2024 → #9 |
| Lifeng Yu, Shuai Leng, Cynthia McCollough | pipeline paper | F03 Mayo 2017 → #16 |
| Petros Wallden, Stuart Ferguson | pipeline paper | B12 Ferguson–Wallden 2025 → #2 |
| Krister Shalm, Emanuel Knill | pipeline paper | C04 Kavuri et al., CURBy 2025 → #5 |
| Elisa Bäumer | pipeline paper | HW05 Bäumer 2024 → #8 |
| Lincoln Carr, Logan Hillberry, Eric B. Jones | pipeline paper | D13 Hillberry 2021 + D14 Jones 2022 → #7 |
| Aldo Badano | pipeline paper + siemens-8 | VICTRE H03 → #20 (PDF missing locally; read via Europe PMC). Also siemens-8 refs 3–4 and §12. |
| Predrag Bakic | supporting reference, not an RE target | H12 Pokrajac–Maidment–Bakic 2012 (cited in future.md §4); siemens-8 §12 |
| Sofia Vallecorsa (CERN QTI) | **not from the pipeline** | siemens-8 §12 ("CERN openlab") plus web; no paper in `papers/` |
| Siemens AG QUTAC, Siemens Healthineers CT R&D / DT&I | **not from the pipeline** | Siemens context (memory, §8), only via Jan |

Every location, current role and the "why now" hooks (Elliott's open PhD post, Enderling's twin lab, CURBy's
public-use messaging) come from the 2026-10-30 web check, not from the papers. The likelihood numbers are judgement
calls.

### 9.1 Tier 1: highest value × reachable (contact first)

| Person | Where | Why them (repo link) | Concrete offer / ask | Cold | Warm |
|---|---|---|---|---|---|
| **Thomas J. Elliott** | University of Manchester, UK | Quantum memory advantage for stochastic modelling, the theory behind D-5 (L1′). His team ran a 1-qubit-memory experiment (Nat. Commun. 2023). He has an open PhD on quantum memory advantage starting Oct 2026, so he is actively growing this line. | "First biomedical process (tumour division timing and fate) modelled with a quantum causal-state machine: can you check our C_q vs C_μ, and help pick parameters where the gap is resolvable?" Co-authorship on the D-5 paper. | 35 % | 60 % |
| **Zongwei Zhou** (+ Qixin Hu, Alan Yuille) | Johns Hopkins, Computer Science, Baltimore, USA | Pixel2Cancer and SyntheticTumors are your E (#11) and F (#13). They covered liver, pancreas and kidney, **never lung**. Open-source and very active. | "We ported Pixel2Cancer to lung with Kansal–Torquato layers, and 3 of 4 growth stages match. Want to compare against your pipeline, or co-author the lung extension?" | 30 % | 50 % |
| **Ehsan Abadi** (+ Fakrul Islam Tushar, W. Paul Segars) | Duke CVIT, Durham NC, USA | Co-author of F04 (McCabe, DukeSim NAEOTOM Alpha, F #17); lung virtual imaging trials. Tushar and Segars are authors of A01 SYN-LUNGS (A #18). Already works with Siemens. Associate professor, more reachable than the centre director. | "Certified, replayable lung cohorts as an input to your virtual trials." Ask for the NAEOTOM detector response or XCAT lung phantoms. Through Siemens this becomes a three-way link. | 15 % | 45 % |
| **Heiko Enderling** | MD Anderson, Radiation Oncology, Houston, USA | Mathematical oncology; his lab explicitly builds **digital twins for oncology** and patient-specific treatment-response models. Co-author of Poleszczuk–Enderling (E #12). Radiation oncology connects to Varian. | Twin stages 2–3 (§4.2): "Calibrated growth from serial CT, with a quantum slot for the growth process. Can your response models be the therapy layer?" | 15 % | 35 % |
| **Joseph Tindall** | Flatiron Institute (CCQ), New York, USA | Belief-propagation simulation of IBM heavy-hex circuits, the method behind your BP adversary (#9). Known for debunking quantum-advantage claims. | "Try to break our D circuits." This is the strongest possible honesty credential: if Tindall cannot simulate D at scale, that is the L2 evidence; if he can, that is your measured frontier. | 30 % | 45 % |

### 9.2 Tier 2: strong value, harder to reach or a narrower role

| Person | Where | Why them | Offer / ask | Cold | Warm |
|---|---|---|---|---|---|
| **Lifeng Yu** (+ Cynthia McCollough, Shuai Leng) | Mayo Clinic CT Clinical Innovation Center, Rochester MN, USA | Projection-domain lesion insertion (F #16, rebuilt on XCIST); the Mayo LDCT Siemens raw data; deep Siemens CT partnership. | Advice on raw-data insertion; faster access to Siemens projection cases; validate our XCIST rebuild against theirs. | 10 % | 35 % |
| **Mile Gu** | NTU + Centre for Quantum Technologies, Singapore | Founder of the quantum causal-state line (D-5 source, Gu 2012). Group studies quantum vs complexity science. | Same offer as Elliott; approach both together (they co-author often). | 20 % | 40 % |
| **Petros Wallden** (+ Stuart Ferguson) | University of Edinburgh, Quantum Software Lab, UK | Coarse-grained QeMCMC (B #2): needs fewer qubits and was already applied to a new domain (causal sets). | "QeMCMC for tumour placement in anatomy (vessels attract, pleura repels): a new application domain with A's masks as the energy." | 30 % | 45 % |
| **Krister Shalm** (+ Emanuel Knill) | NIST / CU Boulder, USA | CURBy beacon (C #5). Their public messaging asks for audit and selection applications. **Note:** your C run found CURBy stale since 2025-08-22, so ask about its status. | "Medical virtual-cohort selection as a CURBy audit use case." Ask about the stale-pulse issue and the Twine format. | 20 % | 35 % |
| **Aldo Badano** (+ Miguel Lago, Andreu Badal) | FDA CDRH OSEL, DIDSR, Silver Spring MD, USA | VICTRE (H #20); raised cohort-selection bias in in-silico trials. The regulator view is the end customer of the credibility argument. | Feedback on whether replayable, unbiased cohort draws matter for submissions. FDA staff rarely co-develop with a single company; aim for a talk or comment, not a partnership. | 5 % | 20 % |
| **Predrag Bakic** | Lund University (Translational Medicine, SUS Malmö), Sweden; adjunct UPenn | OpenVCT, algorithmic (training-free) breast phantoms, the same philosophy as your rulebook. **Europe-based.** | Methods exchange on procedural phantoms; possible EU co-applicant for a grant. | 25 % | 40 % |

### 9.3 Tier 3: quantum-hardware and ecosystem contacts

| Person / group | Where | Role | Cold | Warm |
|---|---|---|---|---|
| **Elisa Bäumer** / IBM Quantum dynamic-circuit team | IBM Research Zurich, Switzerland *(verify affiliation)* | D-2 one-job lineage (#8, Bäumer). Hardware time and dynamic-circuit advice. IBM likes healthcare showcases. | 15 % | 40 % |
| **Lincoln Carr** (+ Logan Hillberry, Eric B. Jones) | Colorado School of Mines, USA *(verify affiliation)* | Goldilocks QCA (D #7). Advice on why the 12-qubit witness fails under noise. | 20 % | 35 % |
| **Sofia Vallecorsa**, CERN QTI | CERN, Geneva, Switzerland | Quantum-algorithm industry co-development. No medical project found; precedent for quantum detector-physics sampling. | 10 % | 25 % |
| **Siemens AG / QUTAC quantum team** | Munich, Germany | Internal hardware access and credibility. **Only via Jan.** | — | 50 % |
| **Siemens Healthineers CT R&D** (Forchheim) and **DT&I** (Princeton / Erlangen) *(verify names)* | Germany / USA | The internal customer: AI-Rad Companion access, NAEOTOM parameters, reconstruction. This is where §8's T2 items come from. **Only via Jan.** | — | 40 % |

### 9.4 Order of approach

1. **Now, while fixing the chain:** Elliott, then Tindall, then Zhou. Each is a peer-level technical offer with a
   number attached, and none needs Siemens. One yes in quantum and one yes in imaging is enough to say "in
   collaboration with Manchester / JHU" in the pitch.
2. **With Jan, at the pitch:** Abadi at Duke and the internal Siemens CT and QUTAC contacts. Duke and Siemens
   already work together, so the introduction makes this a natural three-way link.
3. **After the first hardware number:** Mayo (Yu), Shalm, Wallden, Gu.
4. **After the pilot cohort:** Enderling (twin stage 2) and Badano/FDA (regulatory view).

### 9.5 Email template (adapt per person)

> Subject: [their method] rebuilt for lung CT, a number reproduced; quick comparison?
>
> Dear Dr X, I'm building Quantum Phantoms, a training-free pipeline for synthetic lung-nodule CT (research context:
> Siemens). I rebuilt your [method] from [paper] and reproduced [number] (ours vs yours: …). I adapted it to
> [lung / certified seed / heavy-hex], and the one-page dossier is attached. Two questions: [specific question 1],
> [specific question 2]. If useful, I'd be glad to share the code and co-author the lung/quantum extension.

Keep it to 6 lines, attach the dossier, and ask exactly one thing they can answer in 10 minutes.

### 9.6 Sources for the affiliations

- Elliott: [Manchester news](https://www.manchester.ac.uk/discover/news/scientists-propose-revolution-in-complex-systems-modelling-with-quantum-technologies/), [PhD listing](https://www.jobs.ac.uk/job/DPO597)
- Zhou: [Pixel2Cancer (JHU)](https://www.cs.jhu.edu/~alanlab/Pubs24/lai2024pixel.pdf), [CV](https://cs.jhu.edu/~zongwei/profile/CV_Zhou.pdf)
- Abadi: [Duke Scholars](https://scholars.duke.edu/person/ehsan.abadi), [PCCT virtual framework (PMC9125732)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9125732)
- Enderling: [MD Anderson profile](https://faculty.mdanderson.org/profiles/heiko_enderling.html), [Enderling Lab](https://www.mdanderson.org/research/departments-labs-institutes/labs/enderling-laboratory.html)
- Tindall: [Simons Foundation](https://simonsfoundation.org/people/joseph-tindall)
- Yu / Mayo: [projection-domain insertion (PMC4654739)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4654739), [lung nodule insertion](https://mayoclinic.elsevierpure.com/en/publications/evaluation-of-a-projection-domain-lung-nodule-insertion-technique)
- Gu: [CQT group page](https://links.quantumlah.org/research/group.php?id=51)
- Wallden: [QeMCMC arXiv:2405.04247](https://arxiv.org/abs/2405.04247v1), [Edinburgh portal](https://www.research.ed.ac.uk/en/publications/quantum-enhanced-markov-chain-monte-carlo-for-systems-larger-than/)
- Shalm: [Help Net Security on CURBy](https://www.helpnetsecurity.com/2025/06/17/curby-nist-quantum-random-number-generator/), [JILA](https://jila.colorado.edu/node/6769)
- Badano: [DPA PV26 speaker page](https://digitalpathologyassociation.org/speakers/show/id/260/agenda/6)
- Vallecorsa: [CERN QTI](https://home.cern/leaders-quantum-technology-connect-cern/)

### 9.7 Contact addresses (published only; checked 2026-10-30)

Only addresses printed in a paper or on an official page are listed. None of the addresses are guessed. Paper
addresses can be stale when someone has moved, so where possible confirm against the current institutional page
before sending.

| Person | Address | Source | Status |
|---|---|---|---|
| Thomas J. Elliott | thomas.elliott@manchester.ac.uk | Manchester PhD listing ([jobs.ac.uk DPO597](https://www.jobs.ac.uk/job/DPO597)); 2018 paper D17 also gives physics@tjelliott.net | current (2026 listing) |
| Mile Gu | mgu@quantumcomplexity.org | paper D17 (2018) | possibly stale; confirm on the NTU / Nanyang Quantum Hub directory |
| Zongwei Zhou | zzhou82@jh.edu | papers E01 (2024) and H01 (2023) | likely current |
| Ehsan Abadi | ehsan.abadi@duke.edu | paper H04 (2020) | likely current (still at Duke) |
| Cindy McCabe (DukeSim NAEOTOM lead author, Abadi's group) | cindy.mccabe@duke.edu | paper F04 (2025) | current. A good junior entry point into Duke CVIT. |
| Lifeng Yu | Lifeng@mayo.edu | paper F03 (2017) | likely current |
| Heiko Enderling | heiko.enderling@moffitt.org | paper E03 (2014) | **stale**: he moved to MD Anderson in 2023. Use the contact on his [MD Anderson profile](https://faculty.mdanderson.org/profiles/heiko_enderling.html). |
| Jan Poleszczuk (E03 co-author) | j.poleszczuk@mimuw.edu.pl | paper E03 (2014) | possibly stale |
| Stuart Ferguson (B12 lead author, Wallden's student) | S.A.ferguson-3@ed.ac.uk | paper B12 (2025) | current. A route to Wallden. |
| Krister Shalm | lynden.shalm@nist.gov | NIST staff directory + [CU Boulder CUbit page](https://www.colorado.edu/initiative/cubit/krister-shalm-0) | current |
| Elisa Bäumer | eba@zurich.ibm.com | paper HW05 (2024) | likely current. This also confirms IBM Zurich. |
| Lincoln Carr | lcarr@mines.edu | Mines research profile / [CURIE contact](https://curie.mines.edu/contact/) | likely current |
| Predrag Bakic | predrag.bakic@med.lu.se | [Lund University staff listing](https://www.lunduniversity.lu.se/lucat/group/v1001347) | current |
| Joseph Tindall | not found | — | use the [Simons Foundation directory](https://simonsfoundation.org/people/joseph-tindall) or the first page of his newest arXiv paper |
| Petros Wallden | not found | — | Edinburgh Informatics directory (people.inf.ed.ac.uk), or go via Ferguson |
| Aldo Badano | not found | — | FDA DIDSR page, or the corresponding-author line of a recent VICTRE paper |
| Fakrul Islam Tushar | not found | — | A01 SYN-LUNGS has no email on page 1; check its arXiv page or go via Abadi/McCabe |
| Sofia Vallecorsa | not searched | — | CERN QTI contact page |
| Siemens internal | — | — | only via Jan |
