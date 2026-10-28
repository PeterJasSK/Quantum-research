# Quantum Phantoms — reading list for the full pipeline

Sources merged here: `references` (chat research notes) and
`../Certified Quantum Tumor Generation Full Pipeline and Literature.pdf` (61 refs).
Duplicates were removed, and every arXiv ID was checked against the arXiv API on 2026-10-28.
PDFs are in `papers/`. The filename prefix gives the pipeline stage and the rank within that stage.

This list covers the **full** pipeline. The MVP (F1–F4: one quantum roll, image-domain draw,
web grid) uses only a thin slice of it.

---

## 0. Target pipeline (diagnosis)

The PDF frames quantum as a **seed only**: a Bayesian-network draw plus CHSH, followed by classical growth.
The pipeline you described goes further in two places, and the reading list is ordered to match it.

```
 real CT ──► [A] WHERE: anatomy + placement prior ──► context vector per site
                                                         │
 rulebook (published stats) ─────────────────────────────┤
                                                         ▼
            [B] MAP: biology + CT context ──► quantum circuit (BN + growth primitives)
                                                         │      ┌─ [C] CHSH/KCBS certificate,
                                                         ▼      │     same hardware job
            [D] QUANTUM GROWTH: first generations non-classical ┘   (QALife Mode A: divide,
                fate-in-superposition, entanglement witness per generation)
                                                         │  hand-off: lineage cells + certified bits
                                                         ▼  = CA initial state + RNG seed
            [E] CLASSICAL GROWTH: cellular automaton, PRNG seeded from certified bits,
                constrained by CT anatomy (lung mask, vessels, pleura); snapshots = follow-ups
                                                         │
                                                         ▼
            [F] RENDER INTO CT: cell states ──► HU map ──► partial volume ──► PSF blur
                ──► matched noise ──► image-domain insert (later: projection-domain / DukeSim)
                                                         │
                                                         ▼
            [G] SIGN: commit rulebook + code hash BEFORE job; receipt (job id, counts, CHSH,
                witness, params, seed, code hash) ──► Ed25519 ──► append-only ledger + DICOM tag
                                                         │
                                                         ▼
            [H] ANALYSE: realism (radiomics vs LIDC, reader test) · utility (train-synthetic /
                test-real detector) · cohort fidelity vs rulebook vs HW noise · certificate +
                witness stats · classical baseline (PRNG + commit-reveal) · privacy
                                                         │
                                                         ▼
                                              web viewer (decoration only)
```

### Where your version differs from the PDF, and what that means

| Stage | PDF plan | Your full pipeline | Consequence |
|---|---|---|---|
| A — where | 3-qubit "lobe" register only | Real anatomy decides the site: lung mask, distance to pleura and vessels, lobe prior | New stage. Needs segmentation (A03/A04) and a placement prior (A01/A02). Ambrosini (F01) supplies the three placement classes: free, juxta-vascular, juxta-pleural. |
| B — map | Bayesian network over size → type → margin → location | The same network, **conditioned on CT context**: site features become rotation angles or control bits | Nothing in the literature does CT-conditioned circuits. Here the novelty is real. Cheapest honest form: context is a classical input that picks the conditional probability table / angles (B01). Neighbour constraints can be encoded WFC-style (B02). |
| D — quantum growth | Absent (the quantum part stops at the seed) | First generations grow **non-classically** | This is the F4/QALife arm. Honest label: *quantum within a generation, classical genealogy* (Mode A). Coherent multi-generation growth (Mode B) is physically blocked on Heron (QDEP results). The only proven "quantum simplifies a process" result is memory (D06–D08), and classical tensor networks compete when correlations are low (D09–D12). |
| E — classical growth | Torquato-style CA, PRNG seeded from certified bits | Same, plus anatomical constraints from A | Pixel2Cancer (E01) already does mask-constrained CA in CT. Lung CA growth is still open ground. |
| F — render | Image-domain recipe | Same, with HU mapping per cell state (solid / necrotic / ground-glass) | Validated: image-domain is within 3% of projection-domain (F02). |
| G — sign | Receipt + Ed25519 + ledger | Same, and the receipt also carries the quantum-growth witness values | The receipt must let anyone replay A → H deterministically from the stored counts and seed. |
| H — analyse | Listed as results | First-class stage | The classical baseline is mandatory (H06). |

**Main risks, ranked:** (1) Stage D: "quantum growth" has to stay a *measured* claim (witness per generation, drift vs. hardware) 
and never become "quantum makes the tumor more realistic" (E05 and the GATE paper show RNG quality does not change simulation outcomes).
(2) Stage B: if the CT context enters only as a classical lookup, call it conditioning, not "quantum maps the anatomy".
(3) Stage F realism matters more for Siemens than any quantum claim, so budget the most effort there.

Relevance marks: ★★★ = core, you build directly from it. ★★ = supports or justifies a design choice. ★ = background or the honesty argument.

---

## A. Where to place the tumor: anatomy + placement prior

**A01 ★★★ SYN-LUNGS** (Tushar et al., arXiv:2502.21187, 2025; v4 retitled "Virtual Patients, Real Gains: Simulated CT from Digital Twins for Multi-Task Lung Nodule Analysis") — `A01_SYN-LUNGS_anatomy-informed-nodules_2025.pdf`
Duke places 512 procedurally generated lung nodules into 174 XCAT digital twins using anatomy-informed placement, then simulates 1,044 CT scans and trains detection, segmentation and malignancy models on them. This is the closest published version of stages A + F for lungs. Read it for the placement rules and the train-synthetic/test-real protocol.

**A02 ★★★ LIDC-IDRI database** (Armato et al., Med. Phys. 38(2), 2011) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC3041807/
About 1,000 chest CTs with radiologist-annotated nodules. Serves three roles: host scans for insertion, the empirical distribution of nodule location, size and type for the rulebook, and the real-nodule reference for realism checks in H. Use `pylidc` for the annotations.

**A03 ★★★ lungmask** (Hofmanninger et al., Eur. Radiol. Exp. 4, 50, 2020; arXiv:2001.11767) — `A03_…pdf` *(added: fills the stage-A gap)*
Robust lung and lobe segmentation on routine CT (pip package `lungmask`). Gives the lung mask and the five-lobe labels that the "location" register and the CA boundary need.

**A04 ★★ TotalSegmentator** (Wasserthal et al., Radiol. AI 2023; arXiv:2208.05868) — `A04_…pdf` *(added)*
Segments 104 structures in CT, including lung lobes, airways, vessels and ribs. Use it to compute the context vector per candidate site (distance to pleura, nearest vessel, airway) and the obstacles for CA growth.

**A05 ★★ XCAT-3.0** (Dahal et al., arXiv:2405.11133, 2024) — `A05_…pdf`
More than 2,500 CT-derived digital twins with full organ segmentations. The phantom side of the "full virtual patient" upgrade path, and the substrate SYN-LUNGS uses.

**A06 ★★ Mayo Low-Dose CT image + projection dataset** (Moen et al., Med. Phys. 48(2), 2021) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC7985836/ · data: TCIA https://wiki.cancerimagingarchive.net/x/fwAWB
Raw projection data plus images, including Siemens chest scans under CC BY. These are the host scans for the projection-domain upgrade in F. (The PDF's ref 44 cites a "Chen et al. 2015" technical note; this dataset paper is the citable one.)

## B. Mapping biology + CT context into the circuit

**B01 ★★★ Quantum inference on Bayesian networks** (Low, Yoder, Chuang, PRA 89, 062315, 2014; arXiv:1402.7359) — `B01_…pdf`
Shows how a Bayesian network becomes controlled rotations, so one measurement gives one joint sample. This is the formal basis of the rulebook circuit. CT context enters as evidence or conditioning on parent nodes. Software: pyAgrum's quantum BN sampling module.

**B02 ★★ Quantum Wave Function Collapse** (Heese, IEEE CG&A; arXiv:2312.13853, 2023) — `B02_…pdf`
A constraint-based tile generator on qubits. It is the template for encoding **local neighbour rules** ("no spiculated cell next to calcified", "no growth across the pleura"), which is how CT context can enter the circuit as constraints instead of a lookup.

**B03 ★★ A quantum procedure for map generation** (Wootton, IBM, arXiv:2005.10327, 2020) — `B03_…pdf`
Quantum hardware makes the seed structure, and classical code completes the map. The same split as B → E. The closest structural precedent.

**B04 ★★ Procedural generation using quantum computation** (Wootton, arXiv:2007.11510, 2020) — `B04_…pdf`
"Quantum blur": encode an image or height map in amplitudes, rotate, measure. A candidate way to give the seed shape natural variation (shape-seed register).

**B05 ★★ Investigating the usefulness of Quantum Blur** (Wootton & Pfaffhauser, arXiv:2112.01646, 2021) — `B05_…pdf`
An honest check of when the quantum version beats a classical blur. The model for your own classical-baseline section.

**B06 ★ Resource-efficient quantum algorithm for protein folding** (Robert et al., npj QI 7, 38, 2021; arXiv:1908.02163) — `B06_…pdf`
A full template for biology → qubit encoding → resource count → hardware run. Use it to structure the "resource estimate" chapter.

**B07 ★ Prospects of QC in computational molecular biology** (Outeiral et al., WIREs CMS 2021; arXiv:2005.12792) — `B07_…pdf`
A sober review of where quantum helps biology and where it is hype (data loading, noise).

**B08 ★ Quantum computing at the frontiers of biological sciences** (Emani et al., Nat. Methods 18, 2021; arXiv:1911.07127) — `B08_…pdf`
A broader review. Cite it for context, not for method.

## C. Certification (runs in the same job as B/D)

**C01 ★★★ Random numbers certified by Bell's theorem** (Pironio et al., Nature 464, 2010; arXiv:0911.3427) — `C01_…pdf`
The founding result: CHSH > 2 certifies randomness. The physics behind the certificate.

**C02 ★★★ Certified randomness using a trapped-ion quantum processor** (Liu et al., Nature 640, 2025; arXiv:2503.20498) — `C02_…pdf`
Certified randomness from a commercial cloud QPU, verified on a supercomputer by cross-entropy benchmarking. The template for the PERUN verification layer.

**C03 ★★ Loophole-free Bell violation with superconducting circuits** (Storz et al., Nature 617, 2023) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC10172133/
Superconducting qubits (IBM's technology class) pass a loophole-free Bell test. The answer to the objection that "a single chip is not loophole-free".

**C04 ★★ CURBy: traceable random numbers from a nonlocal quantum advantage** (Kavuri et al., Nature 2025; arXiv:2411.05247) — `C04_…pdf`
NIST/CU public Bell-test beacon. The external certified seed for hidden test-round choice (certificate layer 2).

**C05 ★★ Certifiable quantum dice** (Vazirani & Vidick, STOC 2012; arXiv:1111.6054) — `C05_…pdf`
Randomness expansion from a small seed. Theory behind "CURBy seeds, IBM expands".

**C06 ★ DI randomness expansion with entangled photons** (Shalm et al., Nat. Phys. 17, 2021; arXiv:1912.11158) — `C06_…pdf`
**C07 ★ DI randomness expansion against quantum side information** (Liu W.-Z. et al., Nat. Phys. 2021; arXiv:1912.11159) — `C07_…pdf`
The two experimental demonstrations of expansion (NIST, USTC). Note: the PDF's link for ref 33 points to 1912.11159 (USTC), while Shalm is 1912.11158.

**C08 ★ KCBS: simple test for hidden variables in spin-1** (Klyachko et al., PRL 101, 2008; arXiv:0706.0126) — `C08_…pdf`
The contextuality inequality for the second, single-system certificate (layer 3).

**C09 ★ Self-testing of quantum systems: a review** (Šupić & Bowles, Quantum 4, 2020; arXiv:1904.10042) — `C09_…pdf`
What near-maximal CHSH values prove about state and measurements (layer 4).

## D. Quantum (non-classical) growth phase

**D01 ★★★ Quantum artificial life in an IBM quantum computer** (Alvarez-Rodriguez, Sanz, Lamata, Solano, Sci. Rep. 8, 14793, 2018; arXiv:1711.09442) — `D01_…pdf`
Self-replication, mutation, interaction and death as gates, run on IBM hardware. The direct ancestor of the QALife / F4 Mode A growth phase (the 2018 model this repo has already reproduced).

**D02 ★★ Artificial life in quantum technologies** (Alvarez-Rodriguez et al., Sci. Rep. 6, 20956, 2016; arXiv:1505.03775) — `D02_…pdf`
The theory paper behind D01: the gate-level definitions of each living primitive.

**D03 ★★ A review of quantum cellular automata** (Farrelly, Quantum 4, 368, 2020; arXiv:1904.13318) — `D03_…pdf` *(added: fills the "quantum growth on a grid" gap)*
The formal toolbox for local, unitary, grid-based quantum dynamics. Read it before calling any grid growth rule "quantum".

**D04 ★★ Quantum Game of Life** (Bleh, Calarco, Montangero, EPL 97, 2012; arXiv:1010.4666) — `D04_…pdf`
Cellular birth and death rules mapped to quantum dynamics. The closest precedent for a "quantum CA tumor".

**D05 ★ QGoL: Quantum Game of Life** (Quantum Inf. Process., 2025) — *manual download, may be paywalled* https://link.springer.com/article/10.1007/s11128-025-05022-y
A recent circuit-level version of quantum Life.

**D06 ★★ Occam's quantum razor** (Gu, Wiesner, Rieper, Vedral, Nat. Commun. 3, 762, 2012; arXiv:1102.1994) — `D06_…pdf`
The one **proven** sense in which quantum simplifies a stochastic process: less memory than any classical model. The legitimate theoretical hook for "growth as a quantum process" (future work, not a claim).

**D07 ★ Experimentally modeling stochastic processes with less memory** (Palsson et al., Sci. Adv. 3, 2017; arXiv:1602.05683, preprint title "Experimental quantum processing enhancement…") — `D07_…pdf`
**D08 ★ Single-shot quantum memory advantage** (Ghafari et al., PRX 9, 2019; arXiv:1812.04251) — `D08_…pdf`
Experimental confirmations of D06.

**D09 ★ Direct solution of the CME using quantized tensor trains** (Kazeev, Khammash, Nip, Schwab, PLoS Comp. Biol. 10, 2014) — `D09_…pdf`
**D10 ★ Simultaneous state-time approximation of the CME using tensor formats** (Dolgov & Khoromskij, 2015; arXiv:1311.3143) — `D10_…pdf`
**D11 ★ Analysis of tensor methods for stochastic models of gene regulatory networks** (Liao et al., arXiv:1910.02520) — `D11_…pdf`
**D12 ★ CME parameter exploration using DMRG** (Zima et al., arXiv:2501.09692) — `D12_…pdf`
The classical competition: tensor networks already compress biological stochastic models when correlations (entanglement) are low, so a quantum-growth claim needs high correlations. **Citation fix:** both `references` and the PDF (ref 27) attach Kazeev's title to arXiv:1311.3143, but that ID is the Dolgov–Khoromskij paper. Both papers are included here. `references` calls D11 "Ion et al."; the arXiv first author is Liao.

## E. Classical growth (PRNG seeded from certified bits)

**E01 ★★★ From Pixel to Cancer: Cellular Automata in CT (Pixel2Cancer)** (Lai, Chen, Wang, Yuille, Zhou, MICCAI 2024; arXiv:2403.06459) — `E01_…pdf`
Tumors grow pixel by pixel in real CT with growth, invasion and death rules, constrained to organ masks, then blend into the scan. Radiologists judged them realistic. This is stages E + F already validated (liver, pancreas, kidney). Lung is still open. The single most important implementation reference.

**E02 ★★★ Cellular automaton of idealized brain tumor growth dynamics** (Kansal, Torquato et al., BioSystems 55, 2000) — `E02_…pdf`
The classic CA: proliferating, dormant and necrotic layers emerge from a few cells. Gives the cell-state model (which F maps to HU: solid rim, necrotic core).

**E03 ★★ High-performance CA model of tumor growth with dynamically growing domains** (Poleszczuk & Enderling, Appl. Math. 2014; arXiv:1309.6015) — `E03_…pdf`
How to make the CA fast for millions of cells and many cohort members.

**E04 ★ Self-reproduction and evolution in CA: 25 years after Evoloops** (Sayama et al., arXiv:2402.03961, 2024) — `E04_…pdf`
Background on rule-based self-reproduction and mutation, useful when designing clonal-evolution rules in the CA.

**E05 ★★ Impact of PRNGs on dosimetric parameters in GATE/GEANT4 linac simulation** (Quantum Beam Sci. 9(2), 16, 2025) — `E05_…pdf`
Evidence that the choice of RNG does not change simulation outcomes. It justifies a plain PRNG for growth and blocks the "quantum = better images" claim. (The companion paper, "Selection of random number generators in GATE", NIM-A 2020, https://www.sciencedirect.com/science/article/abs/pii/S0168900220305684, is paywalled and listed only.)

## F. Rendering and inserting into CT

**F01 ★★★ Realistic simulated lung nodule dataset for testing CAD** (Ambrosini & O'Dell, SPIE Med. Imaging 2010) — `F01_…pdf`
The image-domain recipe: sub-voxel placement, blood-matched density with partial-volume edges, max-rule over vessels, Gaussian PSF, matched noise. Also covers the three placement classes. Version 1 of stage F.

**F02 ★★★ Techniques for virtual lung nodule insertion: projection- vs image-based** (Robins et al., Duke, Phys. Med. Biol. 62(18), 2017) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC5693368/
Image-domain insertion matches projection-domain within 3% in volume. The justification for starting image-domain.

**F03 ★★ Evaluation of a projection-domain lung nodule insertion technique in thoracic CT** (Mayo Clinic CT group, J. Med. Imaging 4(1), 013510, 2017) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC5374359/
The upgrade path: forward-project the lesion into raw data and reconstruct. Readers could barely tell inserted nodules from real ones (AUC 0.57–0.69).

**F04 ★★ In silico modeling of a clinical photon-counting CT system (DukeSim on NAEOTOM Alpha)** (McCabe, Harrawood, Samei, Abadi, Med. Phys. 52(6), 2025) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC12285274/
A simulator of Siemens' own photon-counting scanner. The highest-fidelity version of F, and a direct Siemens hook.

Listed only (paywalled or no open copy found): Mayo, "Insertion of hepatic lesions into clinical photon-counting-detector CT projection data" (2025), https://mayoclinic.elsevierpure.com/en/publications/insertion-of-hepatic-lesions-into-clinical-photon-counting-detect/ · Abadi et al., "A framework for realistic virtual clinical trials in photon counting CT", Proc. SPIE 10948 (2019).

## G. Signing and provenance

**G01 ★★★ CT-GAN: malicious tampering of 3D medical imagery** (Mirsky et al., USENIX Security 2019; arXiv:1901.03597) — `G01_…pdf`
A GAN injects and removes lung cancer convincingly enough to fool radiologists. The argument for why every synthetic image needs a verifiable origin. Pitch it as traceability, not security.

**G02 ★★★ AAPM TG387: toward widespread use of virtual trials** (Med. Phys. 51(12), 2024) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC11659034/
The field's reproducibility and credibility requirements. The signed, replayable receipt is your answer to them.

**G03 ★★ The stochastic digital human is now enrolling** (Badano et al., arXiv:2301.08719, 2023) — `G03_…pdf`
FDA review of how digital cohorts are sampled, which names cohort-selection bias as a risk. This is the problem that "commit before you draw" + certified randomness solves.

## H. Analysis, validation and use

**H01 ★★★ Label-free liver tumor segmentation** (Hu et al., CVPR 2023; arXiv:2303.14869) — `H01_…pdf`
An AI trained only on rule-based synthetic tumors segments real tumors about as well as one trained on real data, and doctors confused synthetic with real. The protocol for your utility test. (Its precursor, arXiv:2210.14845, is a duplicate and was skipped.)

**H02 ★★★ Analyzing tumors by synthesis** (Chen et al., arXiv:2409.06035, 2024) — `H02_…pdf`
A review of rule-based and learned tumor synthesis, with case studies where synthetic training matches or beats real-data training. The map for positioning against the field.

**H03 ★★ VICTRE in-silico imaging trial** (Badano et al., JAMA Netw. Open 1(7), 2018) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC6324392/
2,986 virtual patients reproduced a real trial's result. Regulators accept simulated evidence.

**H04 ★★ Virtual clinical trials in medical imaging: a review** (Abadi et al., J. Med. Imaging 7(4), 2020) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC7148435/
Phantom + scanner simulator + model observer: the vocabulary of the field.

**H05 ★★ PyRadiomics** (van Griethuysen et al., Cancer Res. 77(21), 2017) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC5672828/ *(added: realism metric)*
Standard radiomic features (shape, texture, intensity). Use them to compare inserted vs. real LIDC nodules of the same size quantitatively.

**H06 ★★ Better than classical? Benchmarking QML models** (Bowles, Ahmed, Schuld, arXiv:2403.07059, 2024) — `H06_…pdf`
Classical baselines often win, and removing entanglement often changes nothing. The reason the classical baseline (PRNG + commit-reveal, classical growth) is mandatory.

**H07 ★★ Unconditional latent diffusion models memorize patient imaging data** (Dar et al., Nat. Biomed. Eng. 2025; arXiv:2402.01054) — `H07_…pdf`
**H08 ★ Beware of diffusion models for synthesizing medical images** (Akbar et al., arXiv:2305.07644) — `H08_…pdf`
Learned generators leak patients. A rule-based generator that sees no scan cannot. This is the privacy-by-construction argument.

**H09 ★ Do quantum circuit Born machines generalize?** (Gili et al., QST 8, 2023; arXiv:2207.13645) — `H09_…pdf`
**H10 ★ "Train classical, deploy quantum" requires rethinking generalization** (Raj et al., arXiv:2608.31117, 2026) — `H10_…pdf`
Why the pipeline deliberately uses no trained (QML) generator.

**H11 ★ Evidence for the utility of quantum computing before fault tolerance** (Kim et al., IBM, Nature 618, 2023) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC10266970/
127-qubit IBM results with error mitigation. Hardware-feasibility support for the ~100-qubit virtual patient.

**H12 ★ Optimized generation of high-resolution breast anthropomorphic software phantoms** (Pokrajac, Maidment, Bakic, Med. Phys. 2012) — *manual download* https://pmc.ncbi.nlm.nih.gov/articles/PMC3337667/
Rule-based procedural phantoms: precedent that "phantoms from rules" is established practice.

---

## Not downloaded: peripheral or not a paper

Peripheral to this pipeline (quantum Monte Carlo / amplitude estimation, relevant only if the cohort audit uses QAE):
Montanaro, "Quantum speedup of Monte Carlo methods" (arXiv:1504.06987) · Herbert, "The problem with Grover–Rudolph state preparation for quantum Monte Carlo" (arXiv:2101.02240) · Lal et al., MLAE on trapped ions (arXiv:2609.25992) · Chakrabarti et al., "A threshold for quantum advantage in derivative pricing" (Quantum 5, 463) · Noto, logical qubits for radiation transport (arXiv:2203.03165).

Other items:
- Arute et al., "Quantum supremacy" (Nature 574, 2019): the arXiv ID 1910.11333 is the **supplementary information** only, and the cross-entropy verification idea is covered by C02.
- Siemens AI-Rad Companion Chest CT whitepaper (product doc): https://academy.siemens-healthineers.com/_/en-us/whitepaper-features-data-and-algorithms-ai-rad-companion-chest-ct
- PERUN wiki: https://wiki.perun.tuke.sk/
- PennyLane blog "Benchmarking is an art": the same content as H06.
- Quantum Country (web course) and the books *Q is for Quantum* and *Complexity: A Guided Tour*: not papers.

## Manual-download checklist (13): publisher or PMC bot-walls

PMC, Nature and Springer return HTML challenge pages to scripts. Open each link in a browser and save with this name in `papers/`:

| Save as | Link |
|---|---|
| `A02_Armato_LIDC-IDRI_database_2011.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3041807/ |
| `A06_Moen_Mayo_LDCT-image-and-projection-dataset_2021.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC7985836/ |
| `C03_Storz_Loophole-free-Bell-superconducting_2023.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC10172133/ |
| `D05_QGoL_Quantum-Game-of-Life_QIP_2025.pdf` | https://link.springer.com/article/10.1007/s11128-025-05022-y |
| `F02_Robins_Virtual-lung-nodule-insertion-projection-vs-image_2017.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC5693368/ |
| `F03_Mayo_Projection-domain-lung-nodule-insertion_2017.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC5374359/ |
| `F04_McCabe_DukeSim-NAEOTOM-Alpha-PCCT-in-silico_2025.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC12285274/ |
| `G02_AAPM-TG387_Virtual-trials-regulatory-science_2024.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC11659034/ |
| `H03_Badano_VICTRE-in-silico-imaging-trial_2018.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC6324392/ |
| `H04_Abadi_Virtual-clinical-trials-review_2020.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC7148435/ |
| `H05_vanGriethuysen_PyRadiomics_2017.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC5672828/ |
| `H11_Kim_IBM-utility-before-fault-tolerance_2023.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC10266970/ |
| `H12_Pokrajac_Procedural-breast-phantoms_2012.pdf` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3337667/ |

## Read-first shortlist for the full build

1. E01 Pixel2Cancer: growth + CT blending, the backbone of E/F
2. F01 Ambrosini: lung insertion recipe
3. A01 SYN-LUNGS: lung placement + train-synthetic protocol
4. B01 Low–Yoder–Chuang: rulebook-to-circuit
5. D01 Quantum artificial life on IBM: quantum growth phase
6. C01 Pironio + C02 Liu 2025: certificate
7. H01 Label-free: utility test
8. G01 CT-GAN + G03 Badano: why sign and commit-before-draw
9. H06 Bowles: classical-baseline discipline
10. D06 Gu + D09 Kazeev: the honest ceiling for "quantum simplifies growth"
---

## Addendum 2026-10-28: B/D/F deep-dive (+32 papers)

Full analysis, with implementation options, Heron r2 budget and claim levels L0–L3, is in
[`analysis-stages-B-D-F.md`](analysis-stages-B-D-F.md). The reverse-engineering epic and target list are in
[`reverse-engineering/`](reverse-engineering/). New files, each with a one-line description in §5 of the analysis doc:

- **B (mapping):** B09 Borujeni QBN circuits · B10 Borujeni QBN on IBM HW · B11 Layden quantum-enhanced MCMC · B12 Ferguson–Wallden coarse-grained QeMCMC · B13 Aaronson "Read the fine print" · B14 Flöther QC in health/medicine
- **D (quantum growth):** D13 Hillberry Goldilocks QCA · D14 Jones QCA on 23-qubit HW · D15 Koh measurement-induced transition (IBM, mid-circuit) · D16 Wu quantum dimensionality reduction · D17 Elliott–Garner–Gu memory-efficient tracking · D18 García-Pérez open systems on IBM · D19 Carney–Varcoe Galton board · D20 Qiang quantum-walk review · D21 Liu Carleman nonlinear ODEs
- **Q (quantum biology limits):** Q01 Lambert · Q02 Cao "revisited" · Q04 Tegmark decoherence · Q05 Marletto constructor theory of life
- **HW (Heron r2 / heavy-hex):** HW01 Chamberland heavy-hex · HW02 McKay layer fidelity/EPLG · HW03 Montañez-Barrera width×depth (Heron) · HW04 Tindall BP simulation of heavy-hex · HW05 Bäumer dynamic circuits · HW06 Córcoles dynamic circuits
- **F (image):** F05 Peng patch-NPS noise · F06 Lee GGO HU thresholds · F07 DiffTumor · F08 Kannan LDM nodules (reader test) · F09 Han 3D-MCGAN · F10 Chuquicusma visual Turing test · F11 MAISI

Manual downloads (bot-walled or paywalled): Q03 Marais "Future of quantum biology" (https://pmc.ncbi.nlm.nih.gov/articles/PMC6283985/) · XCIST (https://pmc.ncbi.nlm.nih.gov/articles/PMC10151073/) · Solomon & Samei PMB 2014 · Sanders/Hurwitz/Samei Med. Phys. 2016 · Divel & Pelc SPIE 2019 · Gong (Mayo) SPIE 2021. DOIs are in the analysis doc.
