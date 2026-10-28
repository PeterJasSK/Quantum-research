# C — Certificate: CHSH → certified bits → seed

> Letter folder `C_certificate/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/C_certificate/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
Make "certified" a number: CHSH value → min-entropy bound H_min ≥ 1 − log₂(1 + √(2 − S²/4)) → certified-bit count → Toeplitz-extracted seed, with hidden test rounds whose choice is seeded from CURBy, and a ledger format modelled on the beacon chain. The extracted seed seeds every PRNG downstream (shared.seedhash.rng).

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #4 | [Entropy accounting from Bell tests (Pironio; Liu 2025; Vazirani–Vidick)](dossiers/04-bell-entropy-accounting.md) | ★★★ | quantum | listed |
| #5 | [CURBy / NIST beacon chain (Kavuri)](dossiers/05-curby-beacon-chain.md) | ★★ | classical | listed |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `quantum_job_record` — own CHSH runs; stub: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json) · schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `certificate` — schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json) · stub example: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json)
- `quantum_job_record` — schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json) · stub example: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json)

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to C_certificate/runs/ via shared.runrecord. -->
_Pending (feature C)._

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
_Pending (feature C)._ Planned: Pironio H_min-vs-S curve, then applied to our measured S.

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
L0 only. **Simulated CHSH certifies nothing**: the deliverable is the accounting pipeline validated on simulated data — every certificate says "certification-ready, not certified (simulated)". S ≤ 2 ⇒ status fail, no seed, draw rejected and logged (no retry, no fallback).

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[C01], [C02], [C04], [C05] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
