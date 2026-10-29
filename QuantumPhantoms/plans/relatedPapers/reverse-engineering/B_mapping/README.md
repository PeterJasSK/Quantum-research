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

