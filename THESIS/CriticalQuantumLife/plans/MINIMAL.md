# MINIMAL — Critical Quantum Life

Absolute minimal proof of concept. Simulator only (Aer), toy scale, no hardware. This is the DRAFT go/no-go kill-gate.

## Claim to demonstrate
Under contingent closed-loop feedback, a toy Darwinian quantum population shows (a) surprise drops vs a yoked control, (b) a criticality trend, (c) a poke produces spike-then-relax — at toy scale, cheap.

## Scale
Genome width `W = 4`, population `~8`, `~30` generations. Runs on Aer in seconds.

## Minimal pipeline (single file `poc.py`, ~150 lines — fork `../artificial-life/stage4_qalife.py`)
1. **Population** — `W`-qubit genome individuals; reuse existing encode/reproduce/mutate.
2. **Closed loop** — each generation: measure outcome → if "expected" apply predictable (deterministic) feedback, if "surprising" apply high-entropy (QRNG or PRNG-seeded) feedback → select → reproduce → mutate.
3. **Surprise proxy** — negative log-likelihood of observed outcome under the population's running outcome distribution; log per generation.
4. **Criticality fingerprint** — branching parameter `σ` (descendants per active individual); log, watch for trend toward 1.
5. **Yoked control** — identical stimulation sequence, feedback scrambled (non-contingent). Run in parallel.
6. **One scripted poke** — at generation 15 flip which outcomes count as "expected"; watch surprise spike then relax.

## Pass condition (all three = GO to hardware thesis)
- Surprise proxy falls under closed loop but NOT under yoked control.
- `σ` trends toward 1 (not toward 0 = dead).
- Poke at gen 15 → surprise spike → relaxation over following gens.

## Explicitly out of scope for POC
Hardware batches, inter-run state persistence, entanglement witness certification, avalanche exponent α fit, scaled width, live dashboard. All deferred to Stage THESIS.

## Deps
`qiskit`, `qiskit-aer`. QRNG feedback source optional — PRNG fine for DRAFT.
