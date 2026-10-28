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
| #1 | [Bayesian-network → circuit compiler (Low–Yoder–Chuang; Borujeni)](dossiers/01-bn-circuit-compiler.md) | ★★★ | quantum | listed |
| #2 | [Quantum-enhanced MCMC (Layden; Ferguson–Wallden)](dossiers/02-quantum-enhanced-mcmc.md) | ★★ | quantum | listed |
| #3 | [Quantum blur (Wootton)](dossiers/03-quantum-blur.md) | ★ | quantum | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
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
_Pending (feature B)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature B)._ Planned: Borujeni 4-node network on Aer (ideal, then Heron-class noise); drift (TVD) vs the network.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
B-1 is L0 (provenance only: a certified sample of a classical distribution). B-2 may claim L1 only with a multi-qubit witness read in ≥ 2 bases (a single-qubit dial in Z is a classical biased coin). QeMCMC speedups are ideal-simulation only; report mixing time vs classical Metropolis.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[B01], [B04], [B05], [B09], [B10], [B11], [B12] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
