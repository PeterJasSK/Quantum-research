# D — Quantum growth: certified quantum generations + honest simulability

> Letter folder `D_quantum_growth/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/D_quantum_growth/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
The non-classical part of growth. D-2: one-job dynamic-circuit lineage (mid-circuit measure, feed-forward, reset, hidden CHSH rounds). D-5: quantum causal-state model of a division-timing/fate process with measured memory advantage C_q < C_μ (the headline). D-3: heavy-hex Goldilocks QCA tissue patch whose snapshot becomes E's initial shape. A belief-propagation adversary runs on every circuit. D-4 (#10) is out of scope.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #6 | [Quantum causal-state (memory-efficient) process models (Gu; Elliott; Wu; Palsson; Ghafari)](dossiers/06-quantum-causal-states.md) | ★★★ | quantum | listed |
| #7 | [Goldilocks quantum cellular automata (Hillberry; Jones; Farrelly)](dossiers/07-goldilocks-qca.md) | ★★★ | quantum | listed |
| #8 | [Dynamic-circuit feed-forward (Bäumer; Córcoles)](dossiers/08-dynamic-circuit-feedforward.md) | ★★★ | quantum | listed |
| #9 | [Belief-propagation simulator of heavy-hex circuits (Tindall)](dossiers/09-bp-heavy-hex-adversary.md) | ★★ | classical | listed |
| #10 | [Measurement-induced entanglement transition (Koh)](dossiers/10-measurement-induced-transition.md) | ★ | quantum | rejected (out of scope) |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `tumor_draw` — stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `compiled_circuit` — stub: [`shared/stubs/compiled_circuit/compiled_circuit.json`](../shared/stubs/compiled_circuit/compiled_circuit.json) · schema: [`compiled_circuit.schema.json`](../shared/contracts/compiled_circuit.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `witness_record` — schema: [`witness_record.schema.json`](../shared/contracts/witness_record.schema.json) · stub example: [`shared/stubs/witness_record/witness_record.json`](../shared/stubs/witness_record/witness_record.json)
- `memory_advantage_record` — schema: [`memory_advantage_record.schema.json`](../shared/contracts/memory_advantage_record.schema.json) · stub example: [`shared/stubs/memory_advantage_record/memory_advantage_record.json`](../shared/stubs/memory_advantage_record/memory_advantage_record.json)
- `simulability_report` — schema: [`simulability_report.schema.json`](../shared/contracts/simulability_report.schema.json) · stub example: [`shared/stubs/simulability_report/simulability_report.json`](../shared/stubs/simulability_report/simulability_report.json)
- `quantum_lineage` — schema: [`quantum_lineage.schema.json`](../shared/contracts/quantum_lineage.schema.json) · stub example: [`shared/stubs/quantum_lineage/quantum_lineage.json`](../shared/stubs/quantum_lineage/quantum_lineage.json)
- `seed_shape` — schema: [`seed_shape.schema.json`](../shared/contracts/seed_shape.schema.json) · stub example: [`shared/stubs/seed_shape/seed_shape.json`](../shared/stubs/seed_shape/seed_shape.json)
- `quantum_job_record` — schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json) · stub example: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to D_quantum_growth/runs/ via shared.runrecord. -->
_Pending (feature D)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature D)._ Planned: Jones 1-D QCA metrics and a Wu-style C_q vs C_μ, both ideal + Heron-class noise.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
L1 (witness, ⟨XX⟩+⟨ZZ⟩ style, ≥ 2 bases) and L1′ (memory advantage). No L2: shallow heavy-hex circuits are belief-propagation-simulable — #9 makes that a measured number. Check Aer support for noisy dynamic-circuit feed-forward before relying on it.

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[D03], [D06], [D07], [D08], [D13], [D14], [D15], [D16], [D17], [HW04], [HW05], [HW06] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
