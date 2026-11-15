# Quantum Phantoms: instructions for Claude

Training-free synthetic lung CT for validating detection AI (Siemens Healthineers context). Virtual tumours are
placed by anatomy, grown by published models and rendered into real CT with the host scanner's blur and noise.
Quantum computing enters only where it has a measured job (certified seed, entangled lineage, process memory).
Long-term goal: each pipeline stage is one layer of a future patient digital twin.

## Names

- **Quantum Phantoms**: thesis / academic name (and this folder).
- **Quantum Virtual Tumors** (SK: *Kvantové virtuálne nádory*): pitch name for Siemens.
- **Quantum Synthetic Cultures (QSC)** is retired. It still appears in older plans; do not use it in new material.

## Code (minimal pipeline, 2026-11-11)

`code/` is the pipeline; entry doc `code/README.md` (**read first**). One directory per section, each with a
`main.py` exposing `run(ctx)`; `code/main.py` calls them in the order C B D A E F G H web. Sections exchange files
in `research_runs/<run>/` only.

```
cd code
python main.py                        # dry run on the local fake backend
python main.py --backend <name|auto>  # live (Peter only)
python main.py --shots N              # shots per circuit
python main.py --run <run dir>        # continue a stopped run
```

- **C runs first and is spent:** one Bell-map job gives the certificate, the bit pool (`certified_bits.bin`) and
  the pair map. B draws the tumours from the pool (`runio.draw_bits`), every `Q.rng` of a B or D circuit is seeded
  from it, and layouts rank by the pair map. No certificate, no bits, no tumours.
- **B, C and D have one switch each:** the `CIRCUIT` constant at the top of `B_mapping/main.py`,
  `C_certificate/main.py` (`BELL-MAP` default | `GRAPH-BELL`) and `D_quantum_growth/main.py` (the Q-HARD circuits
  of `plans/qhard-*.md` and the QCAND candidates `B-*` / `D-*` of `plans/feature-QCAND-*.md`; `ROLL` = cohort only).
  Every other section is one straight line, no variants. Keep it that way: a change lives in one place.
- QCAND candidates are additive and dry-run only so far; their bounds are [verify]. `B-KS` stays refused live
  until Peter sets `MID_CIRCUIT_LIVE` in `B_mapping/games.py`. C calls the public drand beacon once per run (one
  GET, skipped offline).
- Keep sections small: few files, no CLI flags beyond the four above, constants where they are used.
- Shared code is `code/common/` (`quantum.py` = the only way a circuit reaches a device; `runio.py` = files, seeds,
  claims).
- **The reverse-engineering (RE) work is an archive**, untouched, in `plans/relatedPapers/reverse-engineering/`
  (letters A–H, `shared/`, `INT_integration/`, dossiers, 21 targets). The pipeline does not import it. It still runs
  from its own folder (`python -m <L>_<name>.src.<module>`).
- Removed from `code/` (in git history): the procedural renderer, the QALife roll, the simulated D-SCALE orchestrator,
  survival map, BP copy, hardware packs, `run_budget_*.sh`.

Python: conda base `/home/peter/anaconda3/bin/python3` (3.13). Pinned deps in `requirements.txt`.

## Hard rules

- **Hardware jobs are run by Peter only.** Develop and verify on the dry run (`FakeMarrakesh`). Never submit an
  IBM job yourself, never read, print or commit a token, never touch the repo-root `credentialsApi.py`. Hardware
  uses a pre-saved `QiskitRuntimeService()` account.
- **No automated tests** (repo directive). Verification = manual runs + the paper reproduction in each `repro/`.
- **Q-HARD:** a configuration on the plans' "do not build" list stays refused; a bound marked [verify] or numerical
  never becomes a claim; L2 stays blocked until a certified hardware run exists.
- Paper PDFs (`plans/relatedPapers/papers/`) and run outputs stay local; they are gitignored.
- Never send email or contact anyone. Draft outreach for Peter to review and send.
- Commit only when Peter asks.

## Honesty gates (apply to code, plans, papers, slides)

- Every quantum number carries: claim level (**L0** provenance, **L1** entangled generative state, **L1′** memory
  advantage; L2/L3 are blocked, frontier map only), its classical baseline or surrogate, its BP simulability number
  (target #9), and a label: `simulated: ideal`, `simulated: Heron-class noise (FakeMarrakesh)` or `hardware: <backend>, job <id>`.
- Simulated CHSH certifies nothing: write "certification-ready, not certified (simulated)". Fewer than 8 certified
  pairs or pooled S − 3 sigma ≤ 2 or `p_value_local` ≥ 1e-6 = fail, no bits, no tumours, logged, no retry.
- The bit pool is "bits extracted from Bell-test outcomes on one chip; job-level; not device-independent". Never
  "certified random" without that scope. The cohort drawn from it is L0.
- **The 1.96 on `ibm_marrakesh` is the GHZ witness ⟨XX⟩+⟨ZZ⟩ (bound 1), not CHSH (bound 2).** Read as CHSH it is
  a failed Bell test. Never call it CHSH.
- A single-qubit dial read in Z is a classical biased coin. Interference claims need multi-qubit correlations in
  ≥ 2 bases. Diagonal observables (⟨σz⟩, cell counts, growth curves) have exact classical surrogates.
- D-5 (L1′): at Γ = 0.5, V = 0.4 the exact 1-bit classical d_KL (0.00136) is below the sampling floor (0.00184).
  Do not call it a headline until re-tuned.
- Record non-matches as results (e.g. A #18 placement NOT MATCHED at n = 9). "Advantage is the exception;
  measuring it is the result."
- Never claim "more realistic because quantum", "quantum biology", "classically impossible", or that quantum
  makes better images.
- Privacy comes from **parameter-only construction** (no patient voxels enter a generator), not from the quantum
  certificate. Keep the two arguments separate.
- Readiness is low: simulation only, the A→H chain is not closed, n = 1. Do not write "built" or "works end to end"
  until INT's done-criterion is met.

## Writing for Siemens

| Avoid | Say instead |
|---|---|
| signature, Ed25519, ledger | data lineage, replayable record, audit trail |
| tamper detection, CT-GAN attack | integrity check: any edit to a case is visible |
| security, attacker, threat | credibility, traceability, regulatory evidence |
| "quantum digital twin" | "quantum-ready digital twin" / "the quantum layer of a future patient twin" |
| "quantum" alone | "quantum computing" (Siemens uses "Quantum" for NAEOTOM detector marketing) |

- Sell a classical-strong virtual-cohort engine with a measured quantum socket, not a quantum product.
- Siemens data today: **none**. The 47 local LIDC hosts are GE/Toshiba; #16 runs on a synthetic XCIST phantom;
  #17 uses published NAEOTOM parameters; AI-Rad Companion (#21) has no access. Say "planned link", not "uses".
- Collaborations are not confirmed: write "plan to partner with", never "in collaboration with", until someone agrees.
- Keep `(verify)` markers on product names, deadlines and affiliations until checked.
- Peter often works in Slovak; reply in the language he writes. Pitch/outreach prose in full sentences.

## Key documents

- `README.md`: **live project progress** (per-letter RE vs MVP status, hardware, papers, changelog). Update its
  Progress tables + changelog whenever a stage changes state.
- `plans/siemens-fit-analysis-and-pitch.md`: fit verdict, weaknesses, twin ladder, Siemens assets per stage,
  people to contact, pre-pitch fix list (§5).
- `plans/publication-plan-3-papers.md`: P1 QALife on hardware (M1–M6), P2 pipeline building blocks (SPIE MI),
  P3 quantum ladder in tumour growth (IEEE QCE), thesis chapters, scope cuts.
- `plans/relatedPapers/reverse-engineering/pipeline-overview.md` and `future.md`: weakest links; 5/10/15-year forecast.
- `plans/siemens-8-certified-quantum-virtual-cohorts.md`: original concept (contains the CHSH 1.96 error in §3.7).

## Current priorities

1. Close the A→H chain: G `fill --job` → `action="append"`; D founder from B's draw; C beacon = first pulse after
   the commit, reject a reused pulse. Then one A→H run with a verifying record.
2. P1: PJ0 repeats + W sweep (W = 24–50) and the `analysis/plot_*` figures for the W24 → collapse → W50 arc
   (QALife work lives in `../artificial-life/`).
3. Re-tune D-5 so the L1′ gap clears the sampling floor.
4. T0 Siemens upgrade: reselect hosts to `Manufacturer = SIEMENS` LIDC scans, read CARE Dose4D from headers.
