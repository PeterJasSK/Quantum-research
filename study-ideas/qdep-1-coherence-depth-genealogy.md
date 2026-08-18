# QDEP Idea 1 — Coherence Depth of an Inherited-Entanglement Genealogy: how many generations of quantum inheritance can Heron r2 carry before a classical measure-and-resend surrogate fakes it perfectly?

**Tag: QUANTUM · qdep · effort: medium-high**

## Pitch
Carve the one falsifiable spine out of the QDEP *Living Genealogies* spec and drop the rest.
Build a **single line of descent**: each generation approximately-clones the parent genotype
qubit into a fresh ancilla, then Q-EaaS entropy mutates it. Track the cross-generational
correlation of the trait observable down the lineage. Run two matched arms — a coherent
quantum arm (real cloning, entanglement inherited) and a classical **measure-and-resend**
surrogate (measure parent trait, ship classical bits, re-prepare separable child) on the
*same* Q-EaaS mutation stream and schedule. The single number: **g\*** = the generation at
which the quantum-vs-classical correlation gap closes to within error. Nobody has cleanly
measured how deep a quantum genealogy stays quantum on today's hardware.

**Paper strength score: 75/100** — novel axis (temporal inheritance, not spatial), null
result is a real coherence-budget number, reuses proven engine; docked for shared method
DNA with QuantumLife, an approximate-cloning confound, and IBM-account access risk.

## Build-on / grounding links
- **Ground truth (reproduce this):** Alvarez-Rodriguez, Sanz, Lamata & Solano,
  *Quantum Artificial Life in an IBM Quantum Computer*, Sci. Rep. 8:14793 (2018) —
  DOI 10.1038/s41598-018-33125-3 · arXiv:1711.09442. Gives the exact operators.
- **Plain-language map:** https://en.wikipedia.org/wiki/Quantum_artificial_life — the
  page lays out the same protocol in words: mutation `M(θ) = [[cosθ, sinθ],[sinθ, −cosθ]]`,
  imperfect-clone `U_M(θ)` (no-cloning → variation), phenotype `⟨σ_z⟩_p` exponential decay
  as the "lifetime" observable, genotype passed to the next generation. **Caveat:** the
  article carries a Wikipedia "multiple issues / fringe" banner — use it as the readable
  map, cite the peer-reviewed paper for every claim.
- **What we already learned (port this):** `QuantumLife/` growth engine + `--sim` classical
  surrogate + `pipeline_common`/`layout.best_chain`, and `QuantumLife/research/` teleport
  bond (Stage-3 reach extender).

## How it becomes a study
**Research question:** How many generations of coherent inheritance can current Heron r2
hardware sustain before a matched classical measure-and-resend surrogate reproduces the
lineage's cross-generational trait correlation within statistical error?

**Hypothesis:** For small g the quantum arm shows a cross-generational correlation the
matched separable surrogate provably cannot reach; the gap decays with g and closes at a
finite, measurable **g\*** > 1. (Falsified if g\* = 1, i.e. no advantage survives past a
single inheritance step.)

**Method:** Strip QDEP to inheritance only — **no death, no interaction, no teleport in the
minimal build** (those are follow-ons). Linear lineage of depth G. Per generation:
(1) approximate quantum clone of parent genotype → child ancilla via a fixed entangling
unitary (the 2018 route); (2) Q-EaaS-seeded single-qubit rotation (mutation), receipt
logged. Hold fixed across arms: population=1 line, G, mutation angle schedule, the *same*
Q-EaaS bitstream, measurement settings. Swap only the inheritance channel: coherent clone
(quantum) vs measure-and-resend (classical surrogate, fully simulable). Sim-first to fix
the pipeline, then hardware confirm. Reuses QuantumLife's growth engine + `--sim` surrogate
harness + `pipeline_common`/`layout.best_chain`.

**Baseline:** the measure-and-resend surrogate — identical evolutionary schedule, separable
by construction, classically computable. Same seeds, same angles, same shot budget.

**Metrics:**
- Cross-generational connected correlation `C(g)` of the trait observable between generation
  0 and generation g, quantum arm vs surrogate.
- **g\*** = max g where `|C_q(g) − C_cl(g)|` exceeds k·σ (the headline number).
- Per-generation fidelity vs the ideal noiseless model (reproduce 2018-level agreement at
  g=1 as the toolchain check).
- Cloning-fidelity confound control: report the ideal-clone `C(g)` from a noiseless sim so
  approximate-cloning decay is separated from hardware decoherence.
- Entropy provenance: every mutation traceable to a signed Q-EaaS receipt.

**Novel contribution:** the first cleanly-measured *coherence depth* of an inherited-
entanglement genealogy — one integer g\* that says how far quantum lineage beats a matched
classical surrogate on real hardware.

## THE VISUALIZATION
Two correlation-decay curves, `C(g)` vs generation number: quantum arm (solid) riding above
the classical measure-and-resend surrogate (dashed), error bands shaded. The curves converge
and the shading overlaps at **g\*** — a single vertical marker where "still quantum" becomes
"classically fakeable." One frame carries the whole thesis: the width of the gap *is* the
result, and where it pinches shut *is* the number.

## Staged ambition — reproduce first, then port, then scale (big, not noise)
Ambitious end state, earned in steps. Each stage is a checkpoint that must pass before the
next, so scale-up rests on a verified spine, never on hope.

- **Stage 0 — Reproduce.** Rebuild the 2018 single-lineage result with the *exact* operators
  from the paper/wiki: `M(θ)` mutation, `U_M(θ)` imperfect clone, `⟨σ_z⟩_p` lifetime. Success
  = the noiseless-sim agreement the 2018 work reported. This proves the toolchain and gives a
  fixed reference the hardware run is judged against.
- **Stage 1 — Port QuantumLife's lessons.** Reuse the growth engine, the `--sim` classical
  surrogate harness, and the Heron-r2 layout pipeline — but *re-aim* the correlation tooling
  from QuantumLife's **spatial** `c(d)` (across qubits, one generation) to this study's
  **temporal** `C(g)` (across generations, one lineage). Same trusted machinery, orthogonal
  axis. Add the measure-and-resend surrogate arm and run the g\* comparison at small scale.
- **Stage 2 — Scale big, not noise.** Grow G (generations) and lineage width toward the QDEP
  ceiling **only as coherence allows**, tracking where the quantum-vs-classical gap dies. The
  governing rule (QDEP §1): *noise is not a fitness function.* Every scale-up keeps selection
  an explicit **measured** operation and every mutation tied to a signed Q-EaaS receipt — so
  "bigger" means more coherent generations under control, never more entropy dressed up as
  biology.
- **Stage 3 — Break the SWAP ceiling.** This is where we scale bigger than the current
  heavy-hex connectivity + SWAP routing allows. Interacting distant individuals via a SWAP
  ladder costs depth that *grows with chain distance* — and that depth eats exactly the
  coherence budget g\* depends on, so on this hardware SWAP-routed genealogies hit a wall.
  Swap in the teleported long-range bond (`QuantumLife/research/`, viz-9 result: a faithful
  long-range CNOT at **constant depth 9**, crosstalk-immune): distance no longer taxes depth,
  so lineages can go deeper / wider than SWAP permits *on the same chip*. Attempted only
  after g\* is banked at small scale — Stage 3's claim is measured as **Δg\*** = extra
  coherent generations bought by teleport routing over the matched SWAP-routed lineage.

**The honesty invariant across all stages:** if a result can be reproduced by the matched
separable surrogate, it is noise/plumbing, not inherited quantum life — report it as such.

## Connection to what already exists
Sits directly next to **QuantumLife/** — reuses its L-system growth engine, the classical
no-entanglement `--sim` surrogate arm, and the Heron-r2 `pipeline_common` /
`layout.best_chain` machinery. But QuantumLife measures **spatial** `c(d)` *along the qubit
chain within one generation*; this measures **temporal** `C(g)` *across generations down a
lineage* — orthogonal axis, same trusted tooling. The teleport machinery from
`QuantumLife/research/` (viz-9 → qh-10/11/12) is the Stage-3 follow-on that would extend
g\* by keeping distant lineage bonds coherent. Source spec:
`study-ideas/QDEP_Living_Genealogies.md` §8.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** g\* comes out ≥ 3 with a clean gap that survives noise. That's a crisp, quotable
claim — "quantum inheritance stays classically-inimitable for N generations on Heron r2" —
and it opens the whole QDEP program (add death, interaction, teleport) with a proven spine.

**Bear:** approximate-cloning fidelity is low enough that even the ideal-sim `C(g)` decays
fast, so the hardware gap is small and g\* pins at 1–2. The cloning confound muddies the
story, and reviewers read it as "QuantumLife, but along time."

**Likely outcome:** g\* = 2–3. A real, modest advantage that decays visibly — enough for a
defensible short paper if the cloning-confound control (ideal-sim curve) is done honestly.

**Value if null (g\* = 1):** still publishable and useful. It puts a hard number on the
coherent-generation budget of current dynamic-circuit hardware — the exact quantity QDEP
§10 says nobody has cleanly measured — and tells the whole quantum-artificial-life program
that the interesting regime lives at far fewer generations than the 102-qubit dream assumed.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** How deep can a quantum genealogy stay quantum on real hardware?
**Single defended claim:** On Heron r2, coherent inheritance beats a matched classical
measure-and-resend surrogate up to a measurable generation g\*, and we report that integer
with error bars and a cloning-confound control.
**Why it fits 6–8 pp:** one linear lineage, one observable, two arms, one figure, one number
— no interaction/death/teleport in the minimal build.
**Target venue:** IEEE QCE (Quantum Week) short paper / device-characterization track.
**Compelling-study likelihood: 75/100.**
