# Epic: Life You Can Poke — a certified-quantum Darwinian population that self-organizes to the edge of chaos, recovers when you prod it, and stands one class above the 2018 model it grew from

**Slug:** critical-quantum-life
**Tickets:** F0, F1, F2, F3, F4, F5, F6, F7 (8)
**Author:** Claude (Opus)
**Date:** 2026-08-31
**Status:** Approved
**Project root:** `THESIS/CriticalQuantumLife/` — plans in `plans/`, code in `code/`, run
artifacts in `research_runs/`, web spectacle in `web/`. POC already lives in `proof_of_concept/`
(witness `+0.87` vs classical null `±0.047`, poke-and-recover, hardware run on `ibm_kingston`).
**Source idea:** `study-ideas/thesis-5-critical-quantum-life.md`
**Builds on:** `artificial-life/` — `code/stage4_qalife.py` + `code/stage4_scale.py` (the recreated
2018 model + `⟨X^⊗W⟩` witness at W=24), `stage0_reproduce.py`→`stage5_fliptest.py` (kill-gate
discipline), `qrng_client.py` (QRNG entropy → now doubles as the "surprising feedback" source),
`layout.py`. Web aesthetic mirrors `QuantumLife/web/` (single-file static HTML canvas dashboard).

> No GitHub issues, no test suite — repo directive. "Tickets" F0–F7 are author-defined research
> deliverables; acceptance criteria are author-defined. Pick up with
> `/plan-feature plans/epic-critical-quantum-life.md` naming the F-id.

---

## 1. Why this epic exists

In 2018 Alvarez-Rodriguez et al. built the first quantum-artificial-life model — genomes that
copy, mutate, and are selected, on a quantum processor. It was ahead of its time: the hardware was
too shallow, the population too small, and nobody could yet *interact* with it. This repo already
recreated that model and pushed it to a W=24 / 48-qubit entanglement genealogy (~6× the origin
paper) with a working `⟨X^⊗W⟩` entanglement witness. That is the foundation. **This epic stands one
class above it** — not by making it bigger, but by making it *alive in a way the 2018 model could
not be*: closed-loop, self-organizing, interactive, and certified quantum. We build on people who
were ahead of their time; the hardware and the ideas have finally caught up, and the moment is now.

The one-class-up is a *kind* of result, not a scale of it. The 2018 model was open-loop — it evolved,
but it did not sense and respond. Here the population runs under **closed-loop DishBrain-style
feedback** (Kagan et al. 2022): outcomes it "predicts" get predictable feedback, surprising outcomes
get high-entropy (QRNG-seeded) feedback, and per Friston's Free Energy Principle it reorganizes
across generations to **minimize its own surprise**. The honest target is not "least chaotic" but
**criticality** — the edge of chaos (branching σ≈1, avalanche exponent α≈1.5; Beggs & Plenz 2003):
maximal order is dead, maximal chaos is seizure, "lively" means poised at the critical point. And
you can **poke it** — change the contingency mid-session — and watch a surprise spike relax back to
the edge over the next generations.

"Alive" survives only if three honesty gates pass, and they are foregrounded relentlessly so the
claim never degrades to metaphor: (1) a **yoked open-loop control fails to adapt** (same pokes,
feedback scrambled), (2) the population **settles at criticality, not silence** (entropy plateau,
not H→0), and (3) the **entanglement witness certifies the aliveness is quantum**, above a matched
classical measure-and-resend surrogate. User-visible outcome: a striking, honest, interactive
"life you can poke" — a swarm of glowing quantum genomes with a criticality dial, an avalanche
histogram snapping to the −3/2 law, and a surprise meter; you hit **POKE**, watch it scramble and
crawl back to the edge of chaos, with a ghosted yoked control beside it that pokes identically and
never recovers — the best figure in the whole program.

## 2. Tickets in this epic

| ID | Title | State | One-line summary |
|----|-------|-------|------------------|
| F0 | Closed-loop engine + core observable suite | open | Fork `stage4_qalife.py` into a closed-loop engine: contingent feedback, yoked control, and the observable logger (surprise proxy, σ, entropy, witness) → run JSON. Default **~15 generations**, parametrized. The shared core every other ticket uses. |
| F1 | DRAFT kill-gate (sim, toy scale) | open | The three-gate go/no-go on Aer at toy scale (W=4): surprise drops under closed loop but NOT yoked; σ trends to 1; a poke spikes-then-relaxes. GO/no-go before any hardware spend. |
| F2 | Criticality metric suite | open | Harden the "is it really critical" rigor: σ→1, avalanche size-distribution α≈1.5 power-law fit, entropy plateau, susceptibility peak, and post-poke relaxation time constant τ. |
| F3 | Quantum certification vs classical surrogate | open | `⟨X^⊗W⟩` genealogical witness held above the matched classical measure-and-resend surrogate null throughout — the gate that keeps "quantum-alive" from being classical dynamics in disguise. |
| F4 | Interactive poke + inter-batch state persistence | open | The "life you can poke" spine: a `poke()` API (user-triggered, not scripted) that changes contingency/selection mid-session, plus persistence of inherited quantum+classical state between runs so a session continues across batches. |
| F5 | Hardware batch runs (scaled, manual) | open | Scale genome width, run generations in hardware batches on a current Heron backend (manual user submission), persist state between jobs, poke between batches; produce the thesis figures + witness-vs-surrogate panel. |
| F6 | Web spectacle — "Life You Can Poke" | open | Single-file static HTML canvas dashboard in `QuantumLife/web/` style: glowing genome swarm, criticality dial, avalanche histogram, falling surprise meter, **interactive POKE button**, ghosted yoked-control panel. The primary public artefact. |
| F7 | Thesis synthesis / IEEE short paper | open | The 6–8pp writeup: one criticality figure, one poke-and-recover trace, one witness-vs-surrogate panel, the yoked control as the spine, honesty gates foregrounded, the "standing on 2018's shoulders" framing. |

## 3. Cross-cutting decisions

Decisions made once for the whole epic. Every `/plan-feature` output must respect them.

- **THE THREE HONESTY GATES ARE LAW (the spine of the epic).** "Alive" is a claim only if all three
  pass, and they are foregrounded in every artefact (code output, web, paper), never buried:
  1. **Adaptation gate** — the closed-loop arm's surprise proxy falls where a **yoked control** (same
     stimulation, feedback scrambled / non-contingent) does not. No gap → not learning, not alive.
  2. **Criticality gate** — the population settles at the **edge of chaos** (σ≈1, α≈1.5, entropy
     *plateau*), NOT at silence (H→0 = dead) or chaos (seizure). "Least chaotic" is the wrong target.
  3. **Quantum gate** — the `⟨X^⊗W⟩` witness stays above the matched classical measure-and-resend
     surrogate null. Below it → classical dynamics in a quantum costume, not quantum life.
  Any "alive"/"lively"/"learning" statement anywhere must be traceable to a passed gate. A metaphor
  that isn't gate-backed is a bug.
- **Default ~15 generations (user directive), parametrized.** Generation count defaults to ≈15 (a CLI/
  function parameter, not hardcoded) — enough to show surprise-drop + criticality trend + poke-relax
  cheaply. (Supersedes the POC/MINIMAL's 30.) Exposed so thesis runs sweep longer.
- **The poke is INTERACTIVE (user directive), not scripted.** The engine exposes a `poke()` API
  (change which outcomes count as "expected", alter selection pressure, or inject a stimulus) callable
  mid-session by a human — via the web POKE button (F6) live, and between hardware batches (F4/F5). A
  scripted default-gen poke remains available only for the non-interactive DRAFT sim gate (F1).
- **One class above 2018, by kind not scale.** The origin Alvarez-Rodriguez 2018 model was open-loop
  evolution. The class-up here is **closed-loop active inference + criticality target + interactive
  perturbation + quantum certification** — a qualitatively new capability, reusing the same engine and
  witness. Do NOT frame the contribution as "bigger W than 2018"; frame it as "the first *interactive,
  self-organizing, certified-quantum* one." Width is a means, not the headline.
- **Reuse the artificial-life engine; do not rewrite it.** Fork/import `stage4_qalife.py` /
  `stage4_scale.py` (encode/reproduce/mutate + `⟨X^⊗W⟩` witness), `qrng_client.py` (QRNG feed → the
  "surprising feedback" entropy source), `layout.py`. Copy the `stage0→stage5` kill-gate discipline
  for the DRAFT gate. New code = the closed loop, the yoked control, the observables, the interactivity.
- **Sim-first, always.** Every claim clears Aer at toy scale before any QC time. The DRAFT gate (F1)
  is the go/no-go before hardware budget, mirroring the virus P0 fliptest discipline.
- **Hardware runs are manual** (same workflow as QuantumLife / number-partitioning): code emits
  circuits + a batch harness; the **user submits to QC by hand** and drops run JSONs into
  `research_runs/`, with live calibration (2q err, readout err) recorded. No automated submission.
- **Inter-batch state persistence is real state, not a redraw.** A session's inherited quantum+classical
  population state persists between jobs (F4) so a poke between batches continues the *same* population
  — the interactivity is a true session, not independent runs stitched together.
- **The ledger of observables is one run-JSON schema.** Every run (closed-loop, yoked, surrogate,
  hardware) writes the same schema to `research_runs/`: per-generation surprise, σ, α-fit, entropy,
  witness, poke events. F6 web and F7 paper both read it — one source of truth, they agree by construction.
- **Web spectacle = single-file static HTML canvas, `QuantumLife/web/` aesthetic (F6).** Self-contained,
  theme-aware (dark/light, `prefers-color-scheme` + `data-theme`), canvas-driven, hosted-ready — NOT a
  Next.js app. Interactive, first-class, honest (the yoked ghost panel is mandatory, not optional).

## 4. Shared data model / artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| `code/closed_loop.py` — closed-loop engine (fork of `stage4_qalife.py`) | F0 | F1–F5 |
| Contingent-feedback + yoked-control runners | F0 | F1 (gate), F5 (hardware) |
| Observable logger (surprise, σ, entropy, witness) → run JSON | F0 | F1–F7 |
| `poke()` API (interactive, mid-session) | F4 | F5 (between batches), F6 (POKE button) |
| Inter-batch state persistence (inherited quantum+classical state) | F4 | F5 |
| Criticality metric suite (σ, α power-law fit, entropy plateau, susceptibility, τ) | F2 | F5, F6, F7 |
| Classical measure-and-resend surrogate + null band | F3 | F5, F6, F7 |
| `research_runs/*.json` — one observable schema per run | F0–F5 | F6 web, F7 paper |
| `web/` single-file canvas dashboard (reads run JSON / embedded data) | F6 | public |

## 5. Metrics / what the gates measure

- **Free-energy / surprise proxy vs generation** — negative log-likelihood of observed outcome under
  the population's running distribution; expected to *fall* under closed loop, *not* under yoked.
- **Branching parameter σ** — descendants per active individual; target → 1 (criticality).
- **Avalanche size-distribution exponent α** — power-law fit P(S) ∝ S^{−α}; target ≈ 1.5.
- **Shannon entropy of the population distribution** — target a *plateau* (lively), NOT H→0 (dead).
- **Order-parameter susceptibility peak** — the criticality signature at the transition.
- **Post-poke relaxation time constant τ** — how fast surprise/entropy returns to the critical set-point.
- **Entanglement-witness σ-margin** — `⟨X^⊗W⟩` distance above the classical-surrogate null.
- **Closed-loop-minus-yoked adaptation gap** — the DishBrain control gap; the number that makes it science.

## 6. Hardware / backend considerations

- **Sim-first (Aer) is the gate for everything.** The DRAFT (F1) and the criticality/certification
  rigor (F2/F3) all clear simulation before QC. The POC already showed the hardware *feasibility* side
  (witness `+0.87`, poke-recover on `ibm_kingston`).
- **F5 hardware is manual and batched** — user submits circuits per batch on a current Heron backend,
  persists inherited state between jobs (F4), pokes between batches, records calibration in each run
  JSON. Keep W modest enough that the GHZ genome survives NISQ readout+2q error (the witness must stay
  above the surrogate null); width is a parameter, defaulted small, scaled deliberately.
- **QRNG feedback source** = `artificial-life/qrng_client.py` for the "surprising" high-entropy feedback
  (PRNG acceptable for the DRAFT gate; QRNG for the thesis runs).

## 7. Implementation order

1. **F0 first** — the closed-loop engine + observable logger + yoked runner; nothing else runs without it.
2. **F1 second** — the DRAFT kill-gate on Aer at W=4. **GO/no-go: do not proceed to F5 hardware unless
   all three gates show a signal at toy scale.** (The POC already shows the witness + poke-recover; F1
   completes the surprise-vs-yoked and σ→1 gates the POC didn't cover.)
3. **F2 + F3 in parallel after F1** — criticality rigor and quantum certification both extend F0's
   observables; independent of each other. Both must land before hardware figures mean anything.
4. **F4 after F0** — interactive poke + state persistence; can develop alongside F2/F3 (needs the engine,
   not the metrics). Gates F5's between-batch interactivity.
5. **F5 after F1 (gate passed) + F2 + F3 + F4** — hardware batches need the gates green, the metrics, the
   surrogate, and the persistence/poke machinery. Manual, last of the science tickets.
6. **F6 after F0 + F4** — the web spectacle needs the engine and the poke API; scaffold early against sim
   run JSON, wire the ghost yoked panel and criticality/avalanche/surprise readouts as F2/F3 land.
7. **F7 last** — synthesis; reads the populated `research_runs/` ledger. Draftable in parallel once F5
   has runs.

## 8. Open questions (epic-wide) — RESOLVED

- [x] **Q1 — Project layout.** Root `THESIS/CriticalQuantumLife/` with `code/`, `research_runs/`,
  `web/`; POC left in place. **Confirmed.**
- [x] **Q2 — Scripted-poke position for the DRAFT sim gate.** **Gen 8**, mid-run, so spike + relaxation
  both fit inside the ~15-gen default. (The interactive poke — web + between-batches — is unaffected.)
- [x] **Q3 — Thesis-stage genome width W.** **W=8 default for hardware, parametrized.** The class-up is
  closed-loop, not width — keep W modest so the `⟨X^⊗W⟩` witness clears the surrogate null on NISQ.
- [x] **Q4 — Hardware scope.** **DRAFT-first-defer.** Land the F1 gate + F2/F3/F4 on sim; scaffold F5's
  batch harness but defer actual QC submission until all three gates are green.
- [x] **Q5 — Web data source.** **Both** — a live in-browser toy closed-loop for instant POKE
  interactivity (no QC in browser), with real `research_runs/` JSON overlaid as the "this happened on IBM"
  hardware trace.
- [x] **Q6 — Deliverable.** **Both** — web spectacle is the primary public artefact / headline figure,
  IEEE 6–8pp short paper is the thesis document.

## 9. Per-feature briefs

### F0 — Closed-loop engine + core observable suite
- **What it delivers:** A closed-loop quantum-artificial-life engine forked from
  `artificial-life/stage4_qalife.py`: contingent feedback (predictable on "expected" outcomes,
  high-entropy on "surprising" ones), a yoked-control runner, and an observable logger writing the
  shared run-JSON schema. Default ~15 generations, parametrized. Everything downstream uses this.
- **Acceptance criteria:**
  - AC-F0.1 Fork the encode/reproduce/mutate population from `stage4_qalife.py` (import, do not rewrite
    the genome primitives or the `⟨X^⊗W⟩` witness).
  - AC-F0.2 Closed loop per generation: measure outcome → predictable (deterministic) feedback on
    "expected" outcomes, high-entropy (QRNG via `qrng_client.py`, PRNG fallback) feedback on surprising
    ones → select → reproduce → mutate.
  - AC-F0.3 Surprise proxy = negative log-likelihood of the observed outcome under the population's
    running outcome distribution; logged per generation.
  - AC-F0.4 Yoked-control runner: identical stimulation sequence, feedback scrambled / non-contingent;
    runnable alongside the closed loop from the same instance.
  - AC-F0.5 Observable logger writes the shared `research_runs/*.json` schema (per-generation surprise,
    σ, entropy, witness, poke events, arm=closed|yoked|surrogate, backend, seed).
  - AC-F0.6 Generation count and genome width W are CLI/function parameters; generations default to ≈15.
- **Likely files / areas affected:** new `code/closed_loop.py`; imports `artificial-life/code/stage4_qalife.py`,
  `qrng_client.py`, `layout.py`; writes `research_runs/`.
- **Depends on:** none.
- **Conventions to follow:** mirror the `stage4_*` run-JSON style and the `stage0→stage5` kill-gate
  discipline; QRNG feed via existing `qrng_client.py`.
- **Out of scope:** criticality α-fit + τ (F2); surrogate certification (F3); interactivity/persistence
  (F4); hardware (F5); web (F6).

### F1 — DRAFT kill-gate (sim, toy scale)
- **What it delivers:** The go/no-go before hardware spend: on Aer at W=4, demonstrate all three gate
  *signals* exist at toy scale — surprise drops under closed loop but not yoked, σ trends toward 1, and a
  poke spikes-then-relaxes. Same discipline as the virus P0 fliptest.
- **Acceptance criteria:**
  - AC-F1.1 Run closed-loop and yoked arms (F0) at W=4, ~15 generations, on Aer; show the surprise proxy
    falls under closed loop but NOT under yoked (the adaptation gate signal).
  - AC-F1.2 Log branching σ per generation and show a trend toward 1 (criticality signal), not toward 0.
  - AC-F1.3 A single scripted poke (default gen per Q2) produces a surprise spike followed by relaxation
    over the following generations.
  - AC-F1.4 Emit an explicit GO/no-go verdict: all three signals present → GO to hardware thesis; any
    absent → documented no-go with the toy-scale evidence.
- **Likely files / areas affected:** `code/` (a `draft_gate.py` driver over F0); `research_runs/`.
- **Depends on:** F0.
- **Conventions to follow:** kill-gate discipline (`stage5_fliptest.py`); sim-first; honest no-go allowed.
- **Out of scope:** α power-law fit, τ, surrogate null, scaled width, hardware — all deferred.

### F2 — Criticality metric suite
- **What it delivers:** The rigor that turns "σ trends to 1" into a defensible criticality claim: the
  branching parameter, the avalanche size-distribution exponent α≈1.5 power-law fit, the entropy plateau
  test, the susceptibility peak, and the post-poke relaxation time constant τ.
- **Acceptance criteria:**
  - AC-F2.1 Branching parameter σ estimator with target →1 and its confidence.
  - AC-F2.2 Avalanche size-distribution: collect avalanches, fit P(S) ∝ S^{−α}, report α with goodness of
    fit; target α ≈ 1.5.
  - AC-F2.3 Shannon-entropy trajectory with a plateau test (distinguish lively plateau from H→0 collapse).
  - AC-F2.4 Order-parameter susceptibility peak locating the critical point.
  - AC-F2.5 Post-poke relaxation time constant τ fit from the surprise/entropy return-to-set-point.
- **Likely files / areas affected:** `code/criticality.py` over F0's logs; consumed by F5/F6/F7.
- **Depends on:** F0 (needs runs); best validated after F1 shows a signal.
- **Conventions to follow:** cite Beggs & Plenz 2003 (α≈1.5, σ≈1) and Bak-Tang-Wiesenfeld 1987 for the
  metric definitions.
- **Out of scope:** the quantum-certification surrogate (F3); hardware runs (F5).

### F3 — Quantum certification vs classical surrogate
- **What it delivers:** The quantum honesty gate: the `⟨X^⊗W⟩` genealogical witness held above a matched
  classical measure-and-resend surrogate's null band throughout the run — the certificate that the
  aliveness is quantum, not classical dynamics in disguise.
- **Acceptance criteria:**
  - AC-F3.1 Compute `⟨X^⊗W⟩` per generation for the quantum population (reuse the `stage4` witness).
  - AC-F3.2 Implement the matched classical measure-and-resend surrogate running the identical
    closed loop, and compute its null band (`|W| < k/√shots`).
  - AC-F3.3 Report the witness σ-margin above the surrogate null across the run; the gate passes iff the
    witness stays above the band (allowing for NISQ degradation — pass = "above null", not "= 1").
  - AC-F3.4 Produce the witness-vs-surrogate panel data for F6/F7.
- **Likely files / areas affected:** `code/certify.py`; imports the `stage4` witness; `research_runs/`.
- **Depends on:** F0.
- **Conventions to follow:** mirror the POC's null-band discipline (`±0.047`, witness above band); keep W
  small enough that the GHZ survives.
- **Out of scope:** criticality metrics (F2); hardware submission (F5).

### F4 — Interactive poke + inter-batch state persistence
- **What it delivers:** The "life you can poke" spine: a human-triggered `poke()` API that changes
  contingency/selection pressure or injects a stimulus mid-session, and persistence of the inherited
  quantum+classical population state between runs so a session continues across batches as the *same*
  population.
- **Acceptance criteria:**
  - AC-F4.1 `poke()` API: change which outcomes count as "expected", alter selection pressure, or inject a
    stimulus — callable mid-session, not scripted; records a poke event in the run JSON.
  - AC-F4.2 Persist inherited state (population genomes, running distribution, generation counter, RNG
    state) to disk between runs; a new run resumes the *same* population from it.
  - AC-F4.3 A session driver: run a batch → allow a poke → run the next batch continuing from persisted
    state, demonstrating a spike-then-relax across the batch boundary.
  - AC-F4.4 The API is the one both F5 (between hardware batches) and F6 (web POKE button) call.
- **Likely files / areas affected:** `code/session.py`, a state-persistence format under `research_runs/`.
- **Depends on:** F0. (Develops alongside F2/F3.)
- **Conventions to follow:** state format reuses the run-JSON schema fields; keep the poke semantics
  identical across web / hardware so results are comparable.
- **Out of scope:** the hardware submission itself (F5); the web UI (F6).

### F5 — Hardware batch runs (scaled, manual)
- **What it delivers:** The thesis-scale hardware result: scaled genome width, generations run in hardware
  batches on a current Heron backend (manual submission), inherited state persisted between jobs, pokes
  between batches — producing the criticality figure, the poke-and-recover trace, and the
  witness-vs-surrogate panel.
- **Acceptance criteria:**
  - AC-F5.1 Emit per-batch circuits + a batch harness; user submits to QC by hand and drops run JSONs into
    `research_runs/` with live calibration (2q err, readout err) recorded.
  - AC-F5.2 Persist inherited quantum+classical state between batches (F4); poke between batches.
  - AC-F5.3 Report the closed-loop-minus-yoked adaptation gap, the criticality metrics (F2), the post-poke
    τ, and the witness σ-margin (F3) at the scaled width.
  - AC-F5.4 W kept modest enough that the witness clears the surrogate null on real hardware; width a
    parameter (default per Q3).
- **Likely files / areas affected:** `code/hardware_batches.py`; `research_runs/`; manual QC workflow.
- **Depends on:** F1 (gate green), F2, F3, F4.
- **Conventions to follow:** manual-submission workflow (QuantumLife / number-partitioning); record
  calibration; sim-first sign check before each hardware batch.
- **Out of scope:** automated backend submission; the web (F6); the paper (F7).

### F6 — Web spectacle — "Life You Can Poke"
- **What it delivers:** The primary public artefact: a single-file static HTML canvas dashboard in
  `QuantumLife/web/` style — a swarm of glowing genome-individuals with a generation counter, a
  criticality dial hovering at σ=1 between a frozen-blue dead zone and a boiling-red chaos zone, an
  avalanche histogram snapping onto the −3/2 power-law line, and a falling surprise meter. An
  **interactive POKE button** spikes the surprise, lurches the needle, scrambles the swarm; over the next
  generations you watch it crawl back to the edge of chaos. A ghosted **yoked-control panel** beside it
  pokes identically and never recovers.
- **Acceptance criteria:**
  - AC-F6.1 Single self-contained HTML file (inline CSS/JS, canvas-driven), theme-aware (dark/light via
    `prefers-color-scheme` + `data-theme`), hosted-ready — mirroring `QuantumLife/web/quantum_tree.html`.
  - AC-F6.2 Live glowing genome swarm + generation counter.
  - AC-F6.3 Three dominant readouts: criticality dial (needle at σ=1, dead↔chaos gradient), avalanche
    histogram converging to the −3/2 line, surprise meter falling over generations.
  - AC-F6.4 An interactive **POKE** button calling the F4 poke semantics (in-browser toy loop): surprise
    spikes, needle lurches, swarm scrambles, then relaxes back to criticality over following generations.
  - AC-F6.5 A ghosted yoked-control panel that pokes identically and does NOT recover — the honesty gate
    made visual; mandatory, not optional.
  - AC-F6.6 Real `research_runs/` hardware traces overlaid/loadable as the "this actually happened on IBM"
    layer (per Q5), keeping the demo honest, not just a pretty toy.
- **Likely files / areas affected:** `web/` (single HTML file + assets), reads `research_runs/`.
- **Depends on:** F0 + F4 (poke semantics); criticality/certification readouts firm up as F2/F3 land.
- **Conventions to follow:** mirror `QuantumLife/web/` aesthetic and single-file discipline; the yoked
  ghost panel and the honest hardware-trace overlay are required.
- **Out of scope:** any live QC call from the browser; a Next.js app (single-file static HTML only).

### F7 — Thesis synthesis / IEEE short paper
- **What it delivers:** The 6–8pp double-column writeup: central question, single defended claim, one
  criticality figure, one poke-and-recover trace, one witness-vs-surrogate panel, the yoked control as the
  spine, the three honesty gates foregrounded, and the "standing on the shoulders of the 2018 model —
  one class above it" framing.
- **Acceptance criteria:**
  - AC-F7.1 State the single defended claim with all three gates explicit (adaptation vs yoked; criticality
    not silence; witness above surrogate null).
  - AC-F7.2 Assemble the four figures from the `research_runs/` ledger (criticality, poke-recover,
    witness-vs-surrogate, closed-vs-yoked gap).
  - AC-F7.3 Frame the contribution as one *class* above the 2018 model (interactive, self-organizing,
    certified quantum), not merely larger W; verify the Alvarez-Rodriguez 2018 citation (venue/year).
  - AC-F7.4 If any gate fails, write the honest negative (the width/noise budget at which it dies) — still
    a first, per the idea's "value if null".
- **Likely files / areas affected:** `plans/` or `results/` writeup; reads `research_runs/`.
- **Depends on:** F5 (needs runs); F2/F3 (metrics); F6 (figure).
- **Conventions to follow:** claim/anti-claim honesty voice; cite Kagan 2022, Friston 2010, Beggs & Plenz
  2003, Bak-Tang-Wiesenfeld 1987; verify the NEEDS-CITATION-CHECK anchors before submission.
- **Out of scope:** new experiments (uses F5's runs).
```
