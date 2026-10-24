# Siemens Idea 5 — Quantum Linear Solver for a Patient Digital Twin: on a toy organ-model linear system, does HHL's exponential promise survive read-in and read-out?

**Tag: QUANTUM · siemens · effort: high**

## Pitch
"Patient twinning" is a *stated* Siemens Healthineers pillar (Digital Twin of the Heart; Mayo cardiovascular collab, 2025). Digital twins are physics simulations — PDEs that discretise to large linear systems — and solving linear systems is where the **HHL** quantum algorithm advertises an exponential speedup. But HHL's speedup is notoriously fragile: it needs the right-hand side loaded as a quantum state (read-in) and only yields an *expectation value*, not the full solution (read-out). This study takes a *toy* organ-model linear system and measures, concretely, how much of the promise survives read-in + read-out — the honest reckoning behind the digital-twin buzzword.
**Paper strength score: 58/100** — perfect alignment with a named Siemens pillar and a striking "promise vs reality" story, but HHL's caveats are well known and a toy-only result risks reading as a textbook demonstration; most speculative of the five.

## How it becomes a study
**Research question:** For a small linear system representing a toy organ/tissue model, how does HHL's end-to-end cost (including state-preparation read-in and expectation-value read-out) compare to a classical solver, and under what sparsity/condition-number conditions does any advantage remain even in principle?
**Hypothesis (falsifiable):** Once read-in and read-out are costed, the toy digital-twin linear system shows no end-to-end quantum advantage at any size reachable in sim/hardware; the exponential promise is consumed by data movement.
**Method:** Construct a small sparse SPD linear system (discretised 1-D diffusion / toy tissue model). Implement HHL (or a modern variational linear-solver, VQLS, to cut depth) on statevector + small hardware. Measure solution error and resource cost including state-prep; sweep condition number and sparsity.
**Baseline:** Classical conjugate-gradient / direct solve on the identical system — wall-clock and operation count.
**Metrics:** solution expectation-value error vs classical; resource cost including read-in/read-out; condition-number and sparsity regime where even the *ideal* HHL query advantage would survive; circuit depth vs system size.
**Novel contribution:** A concrete, Siemens-pillar-framed audit of how much of HHL's digital-twin promise survives data-movement — turning "quantum digital twin" from slogan into a measured cost breakdown.

## Connection to what already exists
Methodologically echoes the repo's honest-accounting studies (data-loading caveats flagged throughout ideas.txt Part 5; the `np-query-advantage-map` "advantage is the exception" ethos). No existing repo study touches linear-system/HHL or digital twins — clean new ground, but the weakest Siemens-advantage case.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Directly addresses a pillar Siemens leadership names publicly; the "promise vs read-in/read-out" story is memorable.
**Bear:** HHL caveats are textbook; a toy-only negative risks looking like a known result re-derived.
**Likely:** Clean null — read-in/read-out consume the advantage; a tidy honest cost breakdown.
**Value if null:** Gives Siemens a defensible "why quantum digital twins are a 10-year, not a today, play" — the exact scaling-horizon framing they fund, backed by a measured cost table instead of a slogan.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Does HHL's linear-solver advantage survive read-in and read-out on a toy digital-twin system? **Single defended claim:** end-to-end, no advantage survives at reachable size — data movement dominates. **Why 6–8 pp:** one linear system, one cost-breakdown figure + one condition-number sweep. **Target venue:** IEEE QCE workshop. **Compelling-study likelihood: 58/100.**
