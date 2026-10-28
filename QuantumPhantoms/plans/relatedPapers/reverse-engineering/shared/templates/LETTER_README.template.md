# {{LETTER}} — {{TITLE}}

> Letter folder `{{FOLDER}}/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/{{FOLDER}}/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
{{PURPOSE}}

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
{{TARGETS}}

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
{{INPUTS}}

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
{{OUTPUTS}}

## How to run (sim commands)

<!-- Exact commands, cwd = reverse-engineering/. Label every quantum number "simulated: ideal" or
     "simulated: Heron-class noise (FakeMarrakesh)". Runs go to {{FOLDER}}/runs/ via shared.runrecord. -->
{{HOW_TO_RUN}}

## Reproduced result vs. paper

<!-- Per target: the published number/figure, our number/figure, agreement, sim mode. -->
{{REPRODUCED}}

## Claim level and honesty notes

<!-- L0 provenance / L1 entangled generative state / L1′ memory advantage; never L2/L3.
     Classical baseline + belief-propagation simulability number for every quantum deliverable. -->
{{CLAIM}}

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
{{REFERENCES}}

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
_None yet._
