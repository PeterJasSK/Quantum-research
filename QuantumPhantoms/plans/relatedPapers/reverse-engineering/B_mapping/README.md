# B — Mapping: rulebook + CT context → circuit

> Letter folder `B_mapping/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/B_mapping/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Turn a cited rulebook (published statistics only) plus A's context vector into a quantum circuit with no hand-written gates: a standalone Bayesian-network → circuit compiler (CPT → controlled rotations; one measurement = one joint sample). B-1: context selects the CPTs. B-2: site × phenotype drawn jointly in superposition (the novel contribution). B-5: QeMCMC tumor-in-anatomy energy sampler as a research arm. Quantum blur only together with its classical-blur baseline.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #1 | [Bayesian-network → circuit compiler (Low–Yoder–Chuang; Borujeni)](dossiers/01-bn-circuit-compiler.md) | ★★★ | quantum | adapted |
| #2 | [Quantum-enhanced MCMC (Layden; Ferguson–Wallden)](dossiers/02-quantum-enhanced-mcmc.md) | ★★ | quantum | adapted |
| #3 | [Quantum blur (Wootton)](dossiers/03-quantum-blur.md) | ★ | quantum | rejected |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `certificate` — stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) (or C's real `certificate.json`) · seed source for every B seed; `status: fail` → no draw · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `site_candidates` — stub: [`shared/stubs/site_candidates/sites.json`](../shared/stubs/site_candidates/sites.json) · schema: [`site_candidates.schema.json`](../shared/contracts/site_candidates.schema.json)
- `anatomy_masks` — stub: [`shared/stubs/anatomy_masks/anatomy_masks.json`](../shared/stubs/anatomy_masks/anatomy_masks.json) · schema: [`anatomy_masks.schema.json`](../shared/contracts/anatomy_masks.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `rulebook` — schema: [`rulebook.schema.json`](../shared/contracts/rulebook.schema.json) · stub example: [`shared/stubs/rulebook/rulebook.json`](../shared/stubs/rulebook/rulebook.json)
- `compiled_circuit` — schema: [`compiled_circuit.schema.json`](../shared/contracts/compiled_circuit.schema.json) · stub example: [`shared/stubs/compiled_circuit/compiled_circuit.json`](../shared/stubs/compiled_circuit/compiled_circuit.json)
- `quantum_job_record` — schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json) · stub example: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json)
- `tumor_draw` — schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json) · stub example: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to B_mapping/runs/ via shared.runrecord. -->
All commands run with cwd = `reverse-engineering/` (conda `base`). Every quantum number is labelled `simulated: ideal` or `simulated: Heron-class noise (FakeMarrakesh)`; `hardware: null`. Runs land in `B_mapping/runs/<timestamp>-<tag>/` (gitignored).

```text
python -m B_mapping.src.lidc_stats                              # data/lidc_counts.json (LIDC counts only)
python -m B_mapping.src.rulebook --write --joint --context free # data/rulebook_lung.json, class_prior.json
python -m B_mapping.src.compiler --check <rulebook.json>        # statevector vs exact joint, both control modes
python -m B_mapping.repro.borujeni --mode ideal|heron           # Borujeni 4-node repro (+ figure for heron)
python -m B_mapping.src.map --variant b1 --mode ideal|heron --site S001 [--sites F] [--certificate F] [--shots 4096]
python -m B_mapping.src.map --variant b2 --mode ideal|heron [--k-sites 8] [--multi-control mcry|ancilla]
python -m B_mapping.src.drift_report                            # B-1 x 3 classes + B-2, both modes, figure
python -m B_mapping.repro.layden                                # Layden gap scaling (ideal)
python -m B_mapping.src.qemcmc --tumor --mode ideal|heron [--patch 2,2,2|2,3,1]
python -m B_mapping.src.qemcmc_figure                           # figures/qemcmc_tumor_gap.png
python -m B_mapping.repro.wootton_blur                          # quantum blur vs Gaussian
```

Run a Python process alone or set `OMP_NUM_THREADS=1`: several concurrent BLAS-threaded jobs stalled the Layden run.

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
| # | Quantity | Paper | Ours | Agreement | Sim mode |
|---|---|---|---|---|---|
| #1 | Borujeni oil-stock RMSPE of marginals | 0.1 % (simulator) | 0.36 % (`mcry`), 0.18 % (`ancilla`); marginals within ±0.01 of Netica | match (≤ 0.5 %, ±0.01) | simulated: ideal |
| #1 | Borujeni RMSPE, transpiler level 0 → 3 | 4.9–36.3 % → 9.1–24 % (2020 hardware) | 1.70 → 0.82 % (`mcry`), 2.89 → 1.19 % (`ancilla`) | comparison only (2025 Heron model vs 2020 devices) | simulated: Heron-class noise (FakeMarrakesh) |
| #2 | Layden k_quantum / k_local / k_uniform | 0.264 / 0.94 / 0.948 | 0.250 / 1.017 / 0.939 | match (±0.08 / ±0.15) | simulated: ideal |
| #2 | Tumor patch gap δ quantum / local / uniform (8 spins) | — | 0.0180 / 0.0121 / 0.0084 | adaptation | simulated: ideal |
| #2 | Tumor patch gap δ quantum / local / uniform (6 spins) | — | 0.0392 / 0.0379 / 0.0469 | adaptation | simulated: ideal |
| #2 | Tumor patch gap, noisy proposal (6 spins), asymmetry 0.135 | — | 0.0536 | noise flattens Q; target distribution only approximately preserved | simulated: Heron-class noise (FakeMarrakesh) |
| #3 | Quantum blur vs best Gaussian (θ = 0.1π), correlation | qualitative figure | 2-D 0.967, 3-D 0.993 | equivalent to a Gaussian → rejected | simulated: ideal |

Drift of the pipeline draws (joint TVD to the exact rulebook; 4096 shots, B-2 Heron 256 shots; classical ancestral sampler at the same shot count in brackets):

| Case | simulated: ideal | simulated: Heron-class noise (FakeMarrakesh) | Heron invalid shots | depth / CZ |
|---|---|---|---|---|
| B-1 free | 0.018 (0.023) | 0.571 | 35 % | 5862 / 2033 |
| B-1 juxtavascular | 0.019 (0.028) | 0.596 | 35 % | 5862 / 2033 |
| B-1 juxtapleural | 0.018 (0.024) | 0.685 | 33 % | 5862 / 2033 |
| B-2 joint (3 stub sites) | 0.039 (0.042) | 0.737 (0.159) | 59 % | 31 965 / 11 516 |

Ideal circuits equal the classical sampler to shot noise; the Heron-class circuits are noise-dominated at this depth. Figure: [`figures/drift_b1_b2.png`](figures/drift_b1_b2.png). B-2 at K = 8 (synthetic 8-site file, 9 logical qubits + 7 ancillas) was run **simulated: ideal** only (depth 106 531, 38 123 CZ).

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
- **B-1: claim level L0** (provenance only: a certified sample of a classical distribution). The classical ancestral sampler draws the same distribution with lower error at the same shot count.
- **B-2: claim level L0.** The joint site × phenotype draw is a lookup table classically; no interference claim, no entanglement witness (`WitnessRecord` is D's).
- **QeMCMC: no claim level.** A correct sampler with quantum proposals; any speedup is ideal-simulation only (Layden k_quantum 0.250 vs k_local 1.017, simulated: ideal) and the noisy proposal is asymmetric (0.135).
- **Quantum blur: none.** Equivalent to a Gaussian where it blurs; rejected.
- Belief-propagation simulability number for the B circuits: **pending D #9** (gate counts are recorded in each run's `drift.json`).
- Context tilts and the placement prior are marked *(verify)* in the rulebook sources: the cited papers are not in `../papers/`.
- The stub `anatomy_masks` give an almost flat tumor energy landscape (h ≈ −0.1 everywhere); the QeMCMC adaptation needs A's real masks to say more.
- Real A output and the real C certificate are not wired in here (INT).


## Pipeline readiness

<!-- readiness: prototype -->

Ideal draws match the classical sampler (joint TVD 0.018–0.039), but under Heron-class noise the draw is
noise-dominated (TVD 0.571–0.737, 33–59 % invalid shots at depth 5 862–31 965). The chain asks for B-2 at K = 8 in
Heron mode, a setting that has only run ideal (depth 106 531, 38 123 CZ), so its cost and validity are unknown. The
honesty gate is still open: B's circuits have no BP simulability number, because D's BP adversary cannot read a B
circuit (probe `runs/20261029-185947-probe-gaps`: `bp --circuit` missing). All `map` flags the chain uses exist.

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| Heron noise dominates the draw | component | the sampled distribution is far from the rulebook; only an L0 provenance claim survives | drift table: TVD 0.571–0.737, invalid 33–59 % | fewer CZ (shallower encoding), K = 4, or draw ideal and keep Heron as a stress test |
| B-2 K = 8 Heron never run | data | runtime and invalid fraction at the chain's own setting are unknown | README: K = 8 ideal only | one standalone Heron run before the chain; record drift |
| No BP simulability number | gap | the classical-baseline + simulability gate is unmet for B | `drift.json` `bp_simulability: "pending D #9"`; probe `D.bp_b` | D `bp --circuit` (plan AC-9) |
| Class prior outside the commit | integration | `data/class_prior.json` is neither in the rulebook hash nor in the `.py` code hash, so it can change after the commit | probe `G.commit` | CCR-B1 (prior inside the rulebook) |
| Rulebook sources *(verify)* | assumption | tilts and prior are not traceable to a paper in `../papers/` | honesty notes above | add the papers, or label the values as assumptions |

**Used as-is in the chain?** Yes, all flags exist; in Heron mode its output is noise-dominated and B's job record is dropped by G (`fill --job`). Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[B01] Low–Yoder–Chuang:** write a Bayesian network (a chain of conditional probabilities) as a quantum
  circuit, so one measurement returns one joint sample, with a possible quadratic speedup for inference.
- **[B09] / [B10] Borujeni:** a practical recipe for such circuits, and its accuracy on IBM hardware.
- **[B11] Layden, [B12] Ferguson–Wallden:** quantum-enhanced Markov-chain Monte Carlo, with quantum proposals that
  can mix faster on rugged energy landscapes, extended to problems larger than the device.
- **[B04] / [B05] Wootton:** quantum procedural generation and "quantum blur" for images.

Why it matters: a **rulebook made only of published statistics**, compiled without hand-written gates, makes
every tumour property traceable to a citation.

### 2. Contribution

- A standalone BN → circuit compiler: Borujeni marginal RMSPE 0.36 % (`mcry`) / 0.18 % (`ancilla`) against
  the paper's 0.1 %, and marginals within ±0.01 of Netica. <span class="chip evidence">evidence-based</span>
- QeMCMC reproduced: k_quantum / k_local / k_uniform = 0.250 / 1.017 / 0.939 against 0.264 / 0.94 / 0.948
  (simulated: ideal). <span class="chip evidence">evidence-based</span>
- **B-2**, a joint site × phenotype draw: placement and tumour type drawn together in one quantum job. <span class="chip evidence">evidence-based</span>
- An honest drift table: ideal circuits equal the classical sampler (TVD 0.018–0.039); Heron-class noise does
  not (0.571–0.737). Quantum blur is rejected (correlation 0.967 / 0.993 with a Gaussian). <span class="chip evidence">evidence-based</span>

### 3. Role in cancer detection

**End goal:** cohorts whose tumour mix (type, size, margin, location) follows a **cited rulebook exactly**, with
every draw traceable. That turns detector testing into a controlled experiment: "how does sensitivity change
for 6 mm ground-glass nodules at the pleura?" <span class="chip extrapolation">extrapolation</span> The quantum circuit provides provenance (claim level L0). It does
not provide better tumours: the classical sampler draws the same distribution with lower error today. <span class="chip evidence">evidence-based</span>

### 4. Beyond lungs

- **Any disease with published statistics.** Liver, breast (procedural breast phantoms [H12]) and brain lesions can
  be rulebooks too: the compiler is organ-agnostic. <span class="chip extrapolation">extrapolation</span>
- **Comprehensive medicine.** BN nodes can encode comorbidities, risk factors or drug-response categories. A
  rulebook is then machine-readable clinical knowledge that a cohort generator samples from. <span class="chip extrapolation">extrapolation</span>
- **Treatment and drug response.** Conditional tables such as "response | phenotype, dose" would let virtual cohorts
  carry an outcome label. <span class="chip speculative">speculative</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> B is the twin's **prior-knowledge layer**. Path: (1) a tumour-phenotype rulebook (now) →
(2) a patient-level network (age, smoking, genetics → risk → phenotype) →
(3) conditioning on the patient's own measurements, so the twin samples only futures consistent with them →
(4) quantum sampling of very large joint distributions, which pays off only when the circuits are deep and
error-corrected [B01]. Step 4 is the only quantum-dependent step.

</div>

### 6. Predictions

**5 years**
*Assumptions:* Heron-class noisy devices; noise as in FakeMarrakesh; the classical ancestral sampler stays the baseline.
- At chain depth (5 862–31 965) Heron-class draws are noise-dominated (TVD 0.57–0.74, 33–59 % invalid shots). <span class="chip evidence">evidence-based</span>
- Useful near-term setups are small rulebooks, shallower compilations and K ≤ 4 sites, or an ideal draw stamped
  with a hardware certificate. <span class="chip extrapolation">extrapolation</span>
- B's BP simulability number (D #9) shows these circuits are classically easy at their width. <span class="chip extrapolation">extrapolation</span>

**10 years**
*Assumptions:* devices that run 10⁴–10⁵ two-qubit gates with error mitigation (utility-scale results exist
before fault tolerance [H11]).
- B-2 at K = 8–16 sites runs at chain depth with drift close to the classical sampler. <span class="chip extrapolation">extrapolation</span>
- QeMCMC proposals run on real-anatomy energy landscapes. Any speedup is unproven: today it exists in ideal
  simulation only. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**
*Assumptions:* fault-tolerant hardware with deep, error-corrected circuits.
- <span class="chip speculative">speculative</span> Amplitude-amplified inference over large networks [B01] could estimate rare-event probabilities (rare
  phenotype × location combinations) with quadratically fewer samples. This is a claim-level-L3 capability and the
  first point where B's quantum path could beat its classical baseline.

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Noise dominates the draw | technical | the drawn distribution drifts from the rulebook | shallow encodings; ideal draws + hardware certificate |
| Classical simulability | technical | if BP simulates the circuits, the quantum path adds provenance only | publish the BP number next to every quantum claim |
| Rulebook sources *(verify)* | data | priors without papers cannot be audited | add papers to `../papers/`; label assumptions |
| Prevalence ≠ realism | validation | drift is measured against the rulebook, not real-world prevalence | compare cohorts with LIDC statistics in H |
| Versioning of priors | regulatory | changed priors silently change cohorts | priors inside the committed rulebook (CCR-B1) |

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[B01], [B04], [B05], [B09], [B10], [B11], [B12] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
**CCR-B1: `rulebook`, class prior slot.**
- *Need:* the placement-class prior P(free, juxtavascular, juxtapleural) belongs to the rulebook (A emits equal counts per class).
- *Request:* an optional top-level `params` object (or `prior` field) in `rulebook`; nodes and top level are `additionalProperties: false` / `unevaluatedProperties: false` today.
- *Local workaround:* sidecar [`data/class_prior.json`](data/class_prior.json), read by `joint.py`.

**CCR-B2: `compiled_circuit`, logical-to-physical layout and ancillas.**
- *Need:* record the logical qubit order (clbit i = logical qubit i, node order, little-endian) and which physical qubits are ancillas.
- *Request:* an optional `extra` object on `compiled_circuit`.
- *Local workaround:* `qubit_map` holds the physical qubit whose measurement feeds each node's clbits (matches `$n` in the QASM); ancillas are an extra key `ancilla` (final layout); the logical order is documented here. No information is lost for decoding because decoding uses the compiler's own maps.

