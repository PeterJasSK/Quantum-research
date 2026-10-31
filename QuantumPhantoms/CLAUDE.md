# Quantum Phantoms: instructions for Claude

Training-free synthetic lung CT for validating detection AI (Siemens Healthineers context). Virtual tumours are
placed by anatomy, grown by published models and rendered into real CT with the host scanner's blur and noise.
Quantum computing enters only where it has a measured job (certified seed, entangled lineage, process memory).
Long-term goal: each pipeline stage is one layer of a future patient digital twin.

## Names

- **Quantum Phantoms**: thesis / academic name (and this folder).
- **Quantum Virtual Tumors** (SK: *Kvantové virtuálne nádory*): pitch name for Siemens.
- **Quantum Synthetic Cultures (QSC)** is retired. It still appears in older plans; do not use it in new material.

## Two codebases (do not mix)

| | MVP | Reverse-engineering (RE) pipeline |
|---|---|---|
| Where | `code/` (F1 quantum roll, F2 imaging, F3 web, F4 QALife arm) | `plans/relatedPapers/reverse-engineering/` (letters A–H + W + INT) |
| Entry doc | `code/README.md` | `plans/relatedPapers/reverse-engineering/README.md` (**read first** before RE work) |
| Run from | `code/`, `python -m f1_quantum.run …` | the RE folder, `python -m <L>_<name>.src.<module>` |
| Outputs | `research_runs/<run>/`, `web/index.html` | `<L>/runs/` (gitignored), via `shared.runrecord.start_run` |

The RE pipeline never imports `code/`. RE letters import only `shared/`, never each other, and exchange **files
only** through the frozen contracts in `shared/contracts/` (check outputs with `python -m shared.validate <file>`).

Pipeline: **A** placement → **B** rulebook + CT context → circuit → **C** certificate → **D** quantum growth →
**E** classical growth → **F** render into CT → **G** lineage record → **H** validation. Chain runner:
`python -m INT_integration.src.chain --probe` (see `INT_integration/README.md` for the known gaps).

Python: conda base `/home/peter/anaconda3/bin/python3` (3.13). Pinned deps in `requirements.txt`.

## Hard rules

- **Hardware jobs are run by Peter only.** Develop and verify on AerSimulator / `FakeMarrakesh`. Never submit an
  IBM job yourself, never read, print or commit a token, never touch the repo-root `credentialsApi.py`. Hardware
  uses a pre-saved `QiskitRuntimeService()` account.
- **No automated tests** (repo directive). Verification = manual runs + the paper reproduction in each `repro/`.
- **RE parallel work:** one git worktree + branch per letter; a session writes only inside its own letter folder
  and `feature-<L>-*.md`. Never edit `shared/`, the epic, `index.html` or `site/` from a letter session. Contract
  changes go under "Contract change requests" in the letter README; INT applies them.
- Paper PDFs (`plans/relatedPapers/papers/`) and run outputs stay local; they are gitignored.
- Never send email or contact anyone. Draft outreach for Peter to review and send.
- Commit only when Peter asks.

## Honesty gates (apply to code, plans, papers, slides)

- Every quantum number carries: claim level (**L0** provenance, **L1** entangled generative state, **L1′** memory
  advantage; L2/L3 are blocked, frontier map only), its classical baseline or surrogate, its BP simulability number
  (target #9), and a label: `simulated: ideal`, `simulated: Heron-class noise (FakeMarrakesh)` or `hardware: <backend>, job <id>`.
- Simulated CHSH certifies nothing: write "certification-ready, not certified (simulated)". S ≤ 2 = fail, no seed,
  draw rejected and logged, no retry.
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
