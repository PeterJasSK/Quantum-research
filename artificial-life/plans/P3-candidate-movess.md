# P3 — Candidate moves (the "potential moves" menu)

**Owning epic:** `plans/epic-qalife-darwinian-richness.md` (§9 P3) · **Stage:** P3 (late-stage, exploratory)
**Status:** **Candidate menu — nothing here is locked.** Ideas to be *evaluated*, not a build spec.
**Opened:** 2026-09-09 · **Expanded:** 2026-09-11 (post-P2, paper-grounded moves + error-mitigation work-package added) · **Author:** Claude (Opus), from developer brainstorming + the 2018 paper's own future-work text.

> **Where P2 left it (2026-09-11, `research/P2_CONCLUSION.html`).** The scale axes are worked. The
> **unitary** genealogy is exhausted — geometric, structureless decay, W\*=24=48 qubits (k=2σ), dead
> at W=32: "more width = bigger GHZ, same biology." The **amplitude-damping death channel** — the
> first genuine biological operator — is the *live* frontier: certified k=3σ through **W=4**
> (+0.55 / +0.78 / +0.65), collapsed to +0.001 by **W=8**, so the death-channel ceiling is bracketed
> **W\* ∈ [4, 8)** but not located. Live calib on the W=3/W=4 runs (2q err ≈ 0.002, readout ≤ 0.012)
> proves the decay is the death channel, not a bad chain. **The P2 gate opens through the death
> channel, not around it.** Two things happen before any broad biology, in this order (CD-11, epic §7):
> **(1) pin the collapse edge** (W=5, W=6, damping) and **(2) spend error mitigation on it** to push
> W\* outward. That makes **Work-package EM the literal next move** — see §0 and the EM section.

> **What this file is.** P3 is deliberately exploratory (epic §9: "this is what we explore, not a
> rigid spec"). This is the running list of *potential* richness investigations — each written up
> enough to judge, honestly costed against the quantum signature, and marked **not started**. When
> the P2 decision gate (AC-P2.4) opens, we pick from here on P2 evidence; entries can be dropped,
> merged, or reshaped. Add freely; commit to nothing until the gate.

> **The rule every entry is judged by (CD-3/CD-4).** The witness `⟨X^⊗W⟩` is the *only* quantum
> claim. Any biology that a classical agent-sim reproduces (competition counts, who-survives,
> population size) is **plumbing dressed as life** — it can enrich the demo but adds no quantum
> content, and usually *costs* witness. So each move is scored on two axes, kept separate:
> **(1) biological richness** added, and **(2) witness survival** — the W/G at which the certified
> signature crosses into classical (measured against `research/baseline_P1/`). The result of P3 is
> that trade-off curve, not "the most alive-looking demo." A move that kills the witness is not a
> failure — *where* and *why* it dies is the datapoint (AC-P3.2).

## 0 · Sequencing & the single best next move (post-P2, developer-directed)

The developer directive is explicit: **after damping (done), the paper's own scalability ideas are
tried first, and error mitigation is the focus of this investigation.** That fixes an order the rest
of this file is organized around — three tiers, worked top-down, nothing below a tier starts until the
tier above is judged spent:

1. **Tier EM — error mitigation (do this now).** CD-11 makes mitigation the *first* lever at any
   ceiling, and P2 left a concrete, bounded job: locate the damping W\* (run W=5, W=6) and push it
   outward with mitigation. This is the highest-value, lowest-risk next move — it costs no new physics,
   reuses the exact damping circuit, and every technique has a published GHZ/witness precedent (below).
   **This is the single best next candidate.** Full spec: **Work-package EM**.
2. **Tier PM — paper-grounded richness (the paper's own routes).** The 2018 paper names the exact ways
   it expected the model to grow (verbatim text preserved at the bottom of this file — *source of
   thought, do not edit*). Those are written up as the **PM-series** and are tried **before** the
   developer-brainstorm M-series, per the directive. Best paper-grounded entry points: **PM1** (more
   degrees of freedom per unit — the paper's literal first sentence) and **PM6** (branching genealogy /
   tree substrate — the one PM move that adds *new* off-diagonal quantum content, not diagonal plumbing).
3. **Tier M — developer-brainstorm menu (later).** M1–M6 (selection, competition, multiple lineages,
   teleport-routed fights, QRNG stochasticity, quantum environment) stay as written but are **downstream
   of Tier PM** — richer, more speculative, and mostly diagonal until coupled. Unchanged below.

**Developer decision (2026-09-11): the first new biology to build is PJ0 — the germ/soma split (Idea A).**
It fixes the exact self-inflicted wound P2 exposed (mortal phenotype entangled to the immortal genotype,
then discarded → witness collapse), is single-lineage and sim-first (cheapest experiment in the program),
and is the substrate every later PJ stage stands on. See **PJ0** and the **gradual ladder** (rung 1 = the
first deliverable). Selective DD (from Work-package EM) is pulled *into* PJ0 as the physical germ/soma
barrier — so EM and PJ0 align rather than compete.

**Two things run in parallel, both cheap:** (a) **PJ0 germ/soma** — the first new biology (sim Test 1
first); (b) **Work-package EM on W=5, W=6** — the small remaining P2 loose end (locate the damping W\*),
still worth closing and shares the DD/readout tooling PJ0 needs. Rationale and costing: EM section, PJ
section; ordering in §Recommendation.

## How to read each entry

- **Idea** — the biological process, in plain terms.
- **Encoding** — how it maps to gates/qubits (grounded in `code/qalife.py` where primitives exist).
- **Quantum vs classical (honesty)** — what part carries a real witness claim vs what's diagonal plumbing.
- **Expected witness cost** — best honest guess at how hard it bites the signature on Heron-r2, and why.
- **Measured against** — the baseline/observable it's scored on.
- **Prereqs / status** — what must land first; always starts **NOT STARTED — candidate**.

---

## M1 — Adaptive measured selection (`death_mode='selection'`)

*The epic's best-specified entry point (QDEP §6.5) — listed here for completeness; already named in epic §9.*

- **Idea.** Replace scripted aging (`age = steps − k`) with **earned** survival: mid-circuit measure
  the phenotype ("lifetime" observable); individuals below threshold are reset/removed via conditional
  feed-forward. Death becomes a fitness verdict, not a birth-order script.
- **Encoding.** New `death_mode='selection'` plug-in operator on the model file (CD-1): `qc.measure`
  the phenotype qubit mid-circuit, `with qc.if_test(...)` → `reset`/`X` the individual. Reuses the
  dynamic-circuit / feed-forward pattern already in the file (`_teleport_cx`, :121).
- **Quantum vs classical.** The selection *decision* is classical (a threshold on a measured value).
  The quantum claim stays the genotype-line witness. Selection's interest is that it perturbs the
  GHZ via measurement back-action.
- **Expected witness cost.** **Heavy.** Mid-circuit measurement is the dominant error channel on this
  chip (it is why teleport-routing lost twice). The witness is expected to bite hard — *that bite is
  the measurement, not a bug* (epic §6). Report against `kept_fraction`.
- **Measured against.** `baseline_P1` ideal + hardware witness vs W/G, k=2/k=3 gate.
- **Prereqs / status.** P2 gate open. **NOT STARTED — candidate (highest-specified).**

## M2 — Energy-transfer competition ("the strong eat the weak")

- **Idea.** Two lineages that meet **fight over a shared resource**: the weaker (more aged, closer to
  the `|0⟩` dark state = less excitation) loses; the stronger absorbs its "energy" to keep replicating.
  Carrying-capacity dynamics — winner monopolizes or the two coexist below a resource ceiling.
- **Encoding.** "Energy" = qubit excitation (amplitude). Aging already leaks excitation to a bath
  (`apply_aging_damping`, :86). Model the fight as a **controlled amplitude transfer** between the two
  competitors' phenotype (or a resource-ancilla) qubits — a partial-SWAP / beam-splitter gate
  `√SWAP`-like coupling that moves amplitude from the low-excitation (weak) qubit into the high one.
  Optionally gate it on a measured fitness readout (→ merges with M1).
- **Quantum vs classical.** ⚠ **This is where the honesty knife falls.** Resource competition,
  who-wins, population bookkeeping = **pure classical Darwinism** (a laptop Lotka-Volterra sim does it
  trivially). It makes the life far more *complete* but adds **zero** quantum content on its own. The
  only way it earns a quantum claim is if the *coherent* amplitude exchange keeps the competitors
  entangled — i.e. the fight leaves an off-diagonal signature the witness can see. Whether it does is
  the open question; default expectation is it mostly shows up diagonally (classical).
- **Expected witness cost.** Medium-heavy if the transfer is coherent (extra 2q coupling + possible
  feed-forward); severe if it needs mid-circuit measurement to decide the winner.
- **Measured against.** Witness vs separable null at matched W/G, plus a classical-surrogate check
  (CD-4): if a matched classical energy-competition sim reproduces the population outcome within kσ,
  the population dynamics are declared plumbing and only any residual witness carries the claim.
- **Prereqs / status.** Needs M3 (multiple lineages) to have opponents. **NOT STARTED — candidate.**

## M3 — Multiple competing lineages (break the single line)

- **Idea.** Today the population is **one** line (`k` = child of `k−1`) → one GHZ. Real selection needs
  **several** lineages that coexist and compete: multiple founders, each seeding its own genealogy;
  only one survives, or several coexist, by Darwinian rules.
- **Encoding.** Multiple founder `Ry(π/2)` seeds → several independent CNOT-clone trees (several GHZs)
  laid on disjoint qubit blocks. Spatial/2D topology from the epic menu (§9). Each tree measured with
  its own per-lineage witness; competition operators (M2/M4) couple them.
- **Quantum vs classical.** Per-lineage witness = genuine quantum claim per tree. *Which* lineage wins
  = classical. Interesting quantum question: does inter-lineage coupling create entanglement *between*
  trees (a joint witness across lineages), or just classical correlation?
- **Expected witness cost.** Neutral for isolated trees (just more qubits — scale is cheap, epic §6);
  the cost comes from whatever coupling M2/M4 adds.
- **Measured against.** Per-lineage witness vs baseline; optional cross-lineage joint witness.
- **Prereqs / status.** Enables M2 and M4. **NOT STARTED — candidate (structural prereq).**

## M4 — Teleport-routed inter-lineage fight (SWAP-vs-teleport, under the witness)

- **Idea.** Lineages that "meet" needn't be physical neighbours on the chip — realize the competition
  interaction between **distant** trees via a **teleported gate** so they fight at constant circuit
  depth instead of a long SWAP ladder. Optionally let **QRNG choose the fight-partners** (certified
  stochastic mating/competition, CD-6).
- **Encoding.** Primitives already in the model (CD-10): `_teleport_cx` (:121), `apply_interaction_
  teleport` (:142) — a SWAP as 3 teleported CNOTs over a shared corridor (`+2 ancillas/bond`, a `tel`
  feed-forward register). A/B it against the plain SWAP ladder `_swap_cx` (:111). QRNG picks the bond
  graph — **fixed per circuit**, not per shot (else the witness average is ill-defined).
- **Quantum vs classical.** The routing choice is a hardware-efficiency question, not a new biology.
  The claim is still the witness; this move asks *which routing preserves it better at scale*.
- **Expected witness cost.** **Probably a loss on 2026 hardware — honestly.** Teleport trades
  SWAP-depth for **mid-circuit measurement + feed-forward**, the worst channel on Heron-r2; teleport-
  routing is **already refuted twice** on this chip (readout err ≫ 2q err → the advantage inverts). BUT
  both refutations were on the *old diagonal C(g) metric*; **under the witness it is untested** — and
  the epic P3 menu lists exactly this ("teleport-vs-SWAP re-examined under the witness observable",
  §9). Prediction: teleport loses; *where and by how much* is the datapoint; flips to a win only if a
  future chip gets cheap mid-circuit measurement. Not "not physically connected" — still needs a
  pre-shared Bell pair (physically distributed) + classical wires; it saves *data-qubit routing*, and
  costs *more* qubits, not fewer.
- **Measured against.** Witness vs W at matched biology, SWAP arm vs teleport arm, reported with
  `kept_fraction` and depth.
- **Prereqs / status.** Needs M3 (distant lineages to route between). **NOT STARTED — candidate.**

## M5 — QRNG-driven stochastic biology (cheap add-on)

- **Idea.** Use the certified QRNG stream (already the mutation source, CD-6) to also drive *which*
  individuals interact, mutate hardest, or are selected — genuine environmental stochasticity with a
  certified-entropy receipt, not a PRNG stand-in.
- **Encoding.** Draw control-flow choices (partner graph, mutation targets) from `qrng_client.py` at
  circuit-build time. Record provenance per run (the deferred `meta.entropy_provenance` field, epic §4).
- **Quantum vs classical.** The randomness *source* is certified-quantum (a provenance claim, not a
  computational-advantage claim). Does **not** by itself touch the witness — it's a control choice.
- **Expected witness cost.** ~None directly; cost lives in whatever operator it gates (M1/M2/M4).
- **Measured against.** N/A for the witness; scored on provenance completeness (CD-6) + entropy receipt.
- **Prereqs / status.** Trivial to bolt onto any move; **NOT STARTED — candidate (enabler).**

## M6 — Quantum-random environment (external conditions that affect survival)

- **Idea.** Selection isn't only internal (age, fights) — the **world** presses on the population. Add
  an **environment**: fluctuating conditions (resource abundance, hazard/harshness, "temperature")
  drawn from the certified QRNG stream that modulate who survives. A harsh draw culls the weak harder;
  a rich draw lets more coexist. Carrying capacity becomes environment-dependent, not fixed. Ties the
  whole thing to a changing world instead of a static script.
- **Encoding.** Two flavours, keep them distinct:
  - **(a) Environment as a classical control field** — QRNG draws a per-generation (or per-region)
    parameter that sets the aging rate `gamma`/`delta`, the `ALIVE_THRESH`, or a resource-bath fill
    level; those feed the existing death operators (`apply_aging_damping`, :86). Cheap, no extra
    coherent qubits. Environment **fixed per circuit** (drawn once, held across the 8192 shots) — a
    per-shot-random world makes the witness average ill-defined (same caveat as M4).
  - **(b) Environment as a quantum bath register** — a shared environment ancilla block the population
    couples to (beyond the single damping bath), carrying its own state. System–environment coupling.
- **Quantum vs classical (honesty).** ⚠ **Flavour (a) is pure classical selection pressure** — a laptop
  applies a fluctuating death rate trivially; the QRNG only buys a *provenance* claim on the world's
  randomness (like M5), **not** quantum content. Flavour (b) is the only quantum-interesting version,
  and it cuts the wrong way: **coupling the population to an environment is literally the decoherence
  channel.** Environment = the thing that measures/damps the system = the witness's executioner. The
  one subtle upside: if system+environment stay jointly coherent, an *extended* witness across
  system+bath could survive where the reduced-system witness dies — worth a look, low odds on this chip.
- **Expected witness cost.** **(a):** none directly (it's diagonal); cost lives in the death operator it
  tunes. **(b):** **severe and monotone** — more environment coupling → more damping → faster witness
  death. Honest prior: environment is a signature-killer; the value is charting *how fast* different
  environmental regimes extinguish it.
- **Measured against.** Witness vs separable null across QRNG-drawn environmental regimes (e.g. sweep
  harshness), each vs `baseline_P1`; plus a classical-surrogate check — if a matched classical
  fluctuating-death sim reproduces the survival statistics within kσ, the environment is declared
  plumbing (CD-4) and only any residual/extended witness carries the claim. Record the QRNG receipt
  per regime (CD-6, the deferred `meta.entropy_provenance`).
- **Prereqs / status.** Pairs with M2 (resource competition) and M3 (multiple lineages under one
  shared world); M5 supplies the certified entropy. **NOT STARTED — candidate.**

---

## Evaluation checklist (apply to any move before it graduates from candidate → P3 plan)

1. **Two-axis score stated?** biological richness added AND witness-survival cost, kept separate.
2. **Classical surrogate identified?** what a laptop reproduces (the plumbing) vs the residual witness claim (CD-4).
3. **Measured against `baseline_P1`?** ideal + hardware witness vs separable null at matched W/G, k=2/k=3.
4. **Plug-in, not a fork?** implemented on the model file as an operator/topology (CD-1); `--selftest` coverage where a closed form exists.
5. **Honest expected outcome recorded** *before* running — including "expected to kill the witness, and that's the datapoint."
6. **Fits the P4 phase diagram?** yields a richness-vs-survival point (AC-P4.1) and, if it earns a headline, an honest scale/certification framing (AC-P4.3) — never a speedup claim.

## Combination sketch (the developer's full vision, for reference — NOT committed)

M3 (multiple lineages) + M2 (energy-transfer competition) + M4 (teleport-routed, QRNG-chosen fights)
+ M1 (measured selection) + M6 (quantum-random environment pressing on all of them) → *"multiple
quantum organisms competing over energy under a fluctuating world, weaker consumed by stronger,
ending in coexistence or a monopoly, shown in a web demo (P4, AC-P4.3)."* Honest headline if
built: **"the most complete Darwinian quantum life that still carries a certified witness on 2026
hardware — and the exact boundary where each added process (competition, selection, long-range fight)
extinguishes the signature."** The demo shows the **frontier**, not a miracle. Expect the witness to be
low or dead once all four stack — that collapse *is* the finding.

---

# PJ · Multi-organism coherent competition — survival of the fittest, death emergent (the flagship richness target)

**Status: NOT STARTED — flagship candidate (developer-authored). Sharpens and supersedes M2 + M3;
absorbs M4 as an optional routing arm.** This is the honest end-game of the whole richness program:
several quantum organisms living side by side, competing over energy, the fittest genome earning the
most generations, the losers dying — and the whole thing looking *alive*.

## PJ · design principle (settled, not an open question)

**Death is emergent from losing, never injected as dissipation.** A death operator that only decoheres
the system — damps a qubit to `|0⟩` and traces out a bath — is dumb design: it throws entanglement away
irreversibly and calls the throwing-away "biology." We stop doing that. In PJ there is **no damping
channel, no bath, no trace-out**. An organism dies because a rival takes its energy — a *relative*
outcome between living things, not an absolute leak to the environment. Every operation is **coherent
and unitary**; nothing is discarded; the only witness loss is real hardware noise — which, unlike
modeled damping-death, **error mitigation (Work-package EM) is allowed to fight.** That single property —
all witness loss is EM-fightable — is the structural reason PJ can be witness-positive where damping
death was witness-negative.

**Second principle — germ line outlives soma (Weismann barrier).** The genotype is the *immortal germ
line* (heritable, carries the witness, kept coherent); the phenotype is the *mortal soma* (expresses the
trait, reproduces, then dies). Death happens to the **body, after the gene is passed** — never to the
gene-line while it is still propagating. That is what makes death honest *and* cheap: the soma can die
for real without dragging the witness into the grave with it. **PJ0 (Idea A) below is the first build of
this principle, and the first new biology to implement in the artificial life.**

**Division of labour (settled 2026-09-11).** **PJ0 is the science — the certified quantum life; we let it
live.** A single germ/soma organism, capped at **W12** (12 individuals = 24 qubits, safely inside the
proven-alive unitary regime W≤24 from P2), engineered so its witness survives as long as possible. This
carries the honest quantum claim. **PJ1 is the flagship engineering show-off — the spectacle.** Many W12
organisms tiled along the longest chip chain, competing under QRNG-driven erratic encounters, rendered as
a living, moving world (P4 demo). PJ1's joint cross-lineage witness is **upside, not obligation** — if it
survives, bonus; the flagship's job is the spectacle + the PJ0 witness running underneath. This split is
what de-risks the hard witness questions (I1): the claim lives in PJ0, the wow lives in PJ1.

## PJ0 · Germ/soma split (Weismann barrier) — THE FIRST THING TO BUILD

**This is the first implementation step of the artificial-life program going forward — the substrate
every later PJ stage (competition, multiple lineages, spatial motion) is built on.** Single-lineage,
cheap, sim-first, and it fixes the exact self-inflicted wound P2 exposed.

- **The wound it fixes.** The faithful damping model entangles the mortal phenotype to the immortal
  genotype (`cx(g,p)` in the damping arm), then dissipates the phenotype and discards its bath — so
  **body-death irreversibly decoheres the gene-witness.** That is why the damping ceiling collapsed to
  W\*∈[4,8): the soma drags the germ line into the grave. Dumb design (settled, §principle).
- **The fix (Idea A), three moves:**
  1. **Pass the gene first.** Build the germ-line GHZ chain to completion — all `cx(g_k,g_{k+1})` +
     mutations `ry(θ_k)` — *before any death*. The gene is inherited before the body can die.
  2. **Express the trait diagonally.** Set the phenotype's ⟨σz⟩ from the genotype value (the paper's
     classical trait) as a **separable** state — no `cx(g,p)` back-action. This is what the *unitary*
     arm already does (`_z_geno_chain:87` → `ry(aged)` phenotype); reuse it.
  3. **Kill the body in isolation.** Let the phenotype decay on its own qubit, reaching *nothing* on the
     genotype line → real, irreversible soma death at ~zero witness cost.
- **Two ways the soma dies (pick per run, both isolated from the germ line):**
  - **(i) Local damping** — a bath *dedicated to the phenotype qubit only*, never coupled to a genotype
    (a phenotype-scoped copy of the damping arm, `:144–147`, with the `cx(g,p)` removed). Explicit,
    controlled, reproducible. The safe first version.
  - **(ii) Natural decoherence** — no operator at all; the phenotype qubit's own T1 decay toward `|0⟩`
    *is* the death. Free, maximally honest, but device-dependent (see ladder rung 2). The elegant version.
- **Selective DD = the barrier, physically realized (ties PJ0 to Work-package EM).** Apply dynamical
  decoupling **only to the genotype qubits** (protect the immortal germ line / the witness) and **none to
  the phenotype qubits** (let the mortal soma decohere). Selective DD is Weismann's barrier built with the
  EM toolkit — genes get the anti-aging drug, bodies do not. Note the tension it resolves: you cannot both
  *use noise as death* and *mitigate noise* globally; selective DD is the only honest way to do both at
  once.
- **Honesty.** The trait (alive/dead, predator/prey) is classical by the paper's own admission — so a
  *separable* phenotype is a faithful expression of a classical trait, not a cheat. The germ line keeps
  the sole quantum claim (the witness); the soma is honestly diagonal. Cleaner than damping (which
  *manufactures* witness loss) and than unitary (whose death is a reversible *fake*): PJ0 is **real death,
  honestly isolated.**

## PJ0 · main issues & unknowns (the real remaining work — all must clear before PJ1)

These are the concrete engineering questions for the single germ/soma organism. They are the *reason* PJ0
is a stage and not a one-liner; each has a fail-fast test on the ladder (rungs 0–2).

**I4 — Isolated-soma leakage (the PJ0 core pass/fail).** *Rung 1.*
- *What it is.* Germ/soma requires soma death to reach **nothing** on the genotype. Any residual path — a
  stray gate, transpiler re-entangling during routing, chip **crosstalk** between neighbouring
  phenotype/genotype qubits — and body-death bleeds back onto the witness.
- *How to fight.* (a) **Sim Test 1** is exactly this gate (witness soma-on ≈ soma-off). (b) **Layout
  constraint:** place phenotype qubits physically apart from genotype qubits in `layout.best_chain` to
  minimize crosstalk. (c) **Schedule guard:** no genotype gate during the soma decay/idle window;
  barriers to stop the transpiler recoupling. (d) If leakage persists, prefer explicit local-damping soma
  (controlled) over natural decay.

**I5 — Aging order after transpile (natural-decay clock).** *Rung 2.*
- *What it is.* Natural-decoherence death assumes the founder-soma (built first) idles longest → dies
  first → correct aging order. But post-transpile idle time is set by the **scheduler's** gate placement,
  not build order — it may equalize or scramble idle times → wrong aging.
- *How to fight.* (a) **Inspect the scheduled circuit** (Qiskit scheduling analysis) — verify idle time
  is monotone in birth order. (b) If not, **enforce it** with scheduling barriers/`delay` so older
  individuals genuinely idle longer, or **fall back to explicit local-damping soma** where age is a
  controlled parameter, not a hardware accident. (c) Report realized lifespan as per-qubit `T1 × idle`.

**I6 — Selective-DD support.** *Rung 2.*
- *What it is.* The germ/soma barrier needs DD on genotype qubits **only**, none on phenotype. Stock
  `PadDynamicalDecoupling` may pad *all* idle qubits globally.
- *How to fight.* (a) Target the pass at the **genotype physical qubits** (its `qubits`/constraint arg).
  (b) If not granular enough, a **custom pass** inserting DD sequences on the genotype register alone.
  (c) Verify in the scheduled circuit that phenotype qubits are DD-free.

**I7 — Separable-phenotype faithfulness.** *Document, not a blocker.*
- *What it is.* Expressing the trait as a separable diagonal state (not entangled to genotype) — is that
  still a legitimate "phenotype"? A purist points at the paper's quantum partial-cloning phenotype.
- *How to fight.* (a) **The honest argument:** the trait (alive/dead, predator/prey) is *classical* by
  the paper's own text → a diagonal expression is faithful to what the trait *is*. (b) **Make it an
  experiment:** offer an optional entangled-phenotype mode (the current damping arm) → show it gives the
  *same* diagonal ⟨σz⟩ but costs the witness → proves the entanglement was gratuitous.

**I8 — Natural-death reproducibility.** *Reporting discipline.*
- *What it is.* Natural-decoherence death is device/calibration-specific and drifts run-to-run → "lifespan"
  isn't a stable biological constant.
- *How to fight.* (a) **Report a band** (min–max over calibration snapshots), not a point. (b) For
  reproducible science use explicit local-damping soma (controlled rate); reserve natural-decay for the
  "look how honest/free it is" demo variant. (c) Record `meta.calibration` per run (already in schema) so
  lifespan is traceable to T1.

## PJ0 · build plan, deliverables & acceptance (the first build)

- **Goal.** One W12 germ/soma organism whose **genotype witness survives its soma death** — real,
  irreversible death at ~zero witness cost. This carries the certified quantum-life claim ("let it live").
- **Where the code goes (CD-1 plug-in, not a fork).** A new death mode on `qalife.py` —
  `death_mode='germsoma'` (or a `soma_isolated=True` flag on `build_population:107`): keep the germ-line
  CNOT chain + mutations exactly as today; express the phenotype separably from `_z_geno_chain:87`
  (drop the damping arm's `cx(g,p)`); attach a **phenotype-only** soma-death (local bath copy of `:144–147`
  without the genotype coupling, or none + natural decay). `--selftest` covers it vs the separable closed
  form.
- **Steps = ladder rungs 0–2.**
  - **Rung 0** — reorder the current damping model so all genotype cloning finishes before any phenotype
    couple/decay. Sim: witness(reordered) vs witness(current damping). *(warm-up, may already help.)*
  - **Rung 1 (core deliverable)** — the germ/soma operator above + isolated local soma damping. **Sim
    Test 1: witness(soma-death on) ≈ witness(soma-death off).** THE gate on the whole premise (I4).
  - **Rung 2** — swap local damping for natural decoherence + **selective DD on genotype only**; verify
    aging order (I5) and selective-DD targeting (I6).
- **Deliverables.** (1) germ/soma operator + `--selftest`; (2) sim Test 1 result; (3) small hardware
  confirm at **W12** on the longest chain; (4) banked germ/soma witness-vs-soma-death dataset vs
  `baseline_P1`; (5) the selective-DD schedule; (6) the entangled-phenotype A/B (I7).
- **Acceptance.** (a) sim Test 1 passes — soma death leaves the witness intact within noise (I4);
  (b) aging order monotone or enforced (I5); (c) DD verified on genotype only, phenotype DD-free (I6);
  (d) faithfulness documented + A/B shows entangled-phenotype gives same ⟨σz⟩ but costs witness (I7);
  (e) soma-death reported as controlled rate or T1 band (I8); (f) **hardware: W12 germ/soma witness ≥ the
  damping-model witness at matched W**, ideally approaching the unitary ceiling — proof the wound is
  healed.
- **Then.** L (arena size) is read off the qubits one PJ0 organism needs; the PJ1 arena (rungs 3–6) opens.

## PJ · gradual implementation ladder (current model → full arena; one change per rung, each measured)

Each rung is a single testable change, sim-first then a small hardware confirm, and can fail-fast without
wasting the rungs below. Rungs 0–2 are single-lineage germ/soma (**PJ0**, the first build); rungs 3–6
open the arena (**PJ1**).

| Rung | Change vs previous rung | Unknown it tests | Fail-fast question |
|---|---|---|---|
| **0** | Reorder current damping model so **all** genotype cloning finishes before any phenotype couple/decay | does ordering *alone* recover witness? | witness(reordered) > witness(current damping)? |
| **1** | **Germ/soma:** separable diagonal phenotype + isolated **local** soma damping (drop `cx(g,p)`) | does isolated soma death leave the germ-line witness intact? | witness(soma-death on) ≈ witness(soma-death off)? |
| **2** | Swap local damping for **natural decoherence** + **selective DD** on genotype only | is natural decay the right aging clock, and does selective DD protect the germ line? | founder-soma dies first? germ-line witness lifted by DD? |
| **3** | **Two lineages** (L=2), independent, **no competition** | baseline joint witness (should be ≈ product / near-zero) | both per-lineage witnesses survive? joint ≈ product null? |
| **4** | Add coherent **energy transfer** (partial-SWAP on reserves); reproduction not yet gated | does competition raise the joint witness above the product null? | joint witness − separable joint null > kσ? |
| **5** | Add **differential reproduction** (controlled-clone gated on reserve) | superposition of winners — meaningfully weighted or smeared? | joint witness survives full competition? |
| **6** | Scale **L** (→4, balanced arena) | how many lineages survive | joint-witness depth vs L |

**Rung 1 is the core germ/soma result and the first concrete deliverable.** Rung 0 is a warm-up that may
already help. Everything from rung 3 is the PJ1 arena, gated on rungs 0–2 landing.

## PJ1 · the core arena (coherent competition, superposition of winners)

**Goal.** On top of the PJ0 germ/soma substrate, add *selection* — several germ/soma organisms competing
for energy, the fittest reproducing most — and measure whether a **joint cross-lineage witness** survives.
Reached via ladder rungs 3–6; do not start before PJ0 (rungs 0–2) lands.

- **Idea.** Lay several genealogies side by side (the "stone-wall" of blocks). Give each an energy
  reserve. Let neighbours fight coherently for that energy; the richer lineage keeps cloning (extends its
  chain, deepens its entanglement), the drained one freezes (implicit death). Because the fight is
  coherent and unmeasured, **who wins stays in superposition** — the state becomes a superposition of
  different evolutionary histories, entangled across lineages.
- **Encoding (grounded in `qalife.py`).**
  - **Blocks / stone-wall:** generalize `geno_q`/`pheno_q` (`:60/:64`) from a single stride-2 line to
    `L` disjoint blocks, each an independent founder + CNOT-clone chain (`build_population:107`, looped
    per block). Each block = one GHZ lineage.
  - **Energy reserve:** one resource qubit per lineage (or a shared resource register); excitation
    amplitude = fitness / "life blood".
  - **Competition = coherent energy transfer:** a partial-SWAP / beam-splitter (`√iSWAP`-like, or a
    parameterized 2-qubit rotation) between adjacent lineages' resource qubits — amplitude flows
    weak→strong. Unitary. No measurement, no bath.
  - **Survival of the fittest = differential reproduction:** the next clone gate in a lineage is
    **controlled on that lineage's resource qubit** (a Toffoli-/controlled-CX clone). Full reserve →
    the clone fires → deeper chain → deeper witness. Drained reserve → clone doesn't fire → the lineage
    stops = death by starvation. Coherent, so "did it reproduce?" is itself in superposition.
  - **QRNG-chosen encounters (certified-quantum stochasticity, M5 applied):** draw *which* lineages meet
    and *where* on the chain from the certified QRNG stream (`qrng_client.py`, already the mutation source,
    CD-6) — encounters are erratic, quantum-sourced, and the meeting points differ run to run (the erratic,
    alive-looking dynamics). **Fixed per circuit, not per shot** — the QRNG draws the arena topology once
    and holds it across all shots, varying only across runs (a per-shot-random topology makes the witness
    average ill-defined; same caveat as M4/M6). Honesty: a *provenance* claim on the randomness, **not** a
    computational-advantage claim — the quantum content stays the witness (M5).
  - **Layout — adjacent only (teleport is DEAD, developer-decided 2026-09-11):** tile the lineages as
    adjacent W12 segments along the longest low-error chain (`layout.best_chain`) so encounters use direct
    / short-SWAP gates. No teleport routing — see I9.
- **The two witnesses (this is the measurement).**
  - **Per-lineage witness** — ⟨X^⊗D⟩ within each block (`xbasis_witness_from_counts:217`), as today.
  - **Joint cross-lineage witness** — the new quantum content: ⟨X^⊗(all genotypes)⟩ over *all* blocks +
    resource qubits. Do competing organisms become entangled *with each other*? A partial-SWAP between
    reserves entangles them, so in principle yes — this is the observable with no classical analogue.
- **The quantum prize (why this beats a laptop).** A classical genetic algorithm picks *one* winner. The
  coherent arena holds **all winners at once** — "lineage A won ⊗ A's deep chain" + "lineage B won ⊗ B's
  deep chain", entangled. The joint witness certifies that superposition of evolutionary outcomes. This
  is literally the paper's "evolutionary plot … may not be predicted classically" and its "extra free
  parameters in superposition and entanglement describe the collective dynamics of individuals." **No
  classical surrogate exists for the joint witness** — that is the entire quantum claim of PJ.
### PJ1 · main issues & unknowns (ranked by risk; each with what it is + how to fight)

**I1 — Joint witness may smear or stay tiny (biggest risk).** *Test at rung 4.*
- *What it is.* The joint cross-lineage witness ⟨X^⊗(all genotypes)⟩ is PJ1's only quantum claim. A
  partial-SWAP between reserves makes *some* A–B entanglement, but it may be a tiny perturbation on two
  nearly-independent GHZ chains → the joint witness sits just above the product null. Worse, the full
  X-string over L blocks × depth D is a very long Pauli product → it decays geometrically with total
  width, so even genuine entanglement reads as a small number.
- *How to fight.* (a) **Sim-scan the coupling strength** — find the regime where cross-block entanglement
  is macroscopic, not perturbative (strong/resonant transfer), before committing to hardware. (b) **Use a
  smarter witness than the global GHZ string:** a *graph/tree-state stabilizer* witness matched to the
  actual entangled structure (fewer terms, higher value), or a **bipartite cut witness** across the A|B
  boundary that certifies A–B entanglement directly instead of a global parity. (c) Start L=2, shallow D
  — prove nonzero first. (d) Ride the EM stack (DD + readout) to lift it above the gate.

**I2 — Coherent competition is self-limiting (depth vs coherence).** *Rungs 5–6.*
- *What it is.* The controlled-clone (Toffoli-class ≈ 6 CX decomposed) plus the partial-SWAP coupling add
  circuit depth every competition event. Depth → decoherence → shorter effective life. Each unit of "more
  competition" buys a unit of "less coherence" — the witness can fall *despite* the design being coherent.
- *How to fight.* (a) **Cheapest primitive that still competes:** a single parameterized 2-qubit rotation
  (`Rxx`/`Rzz`/`√iSWAP`-class, 1–2 CX) for energy transfer instead of a full SWAP; a single
  controlled-rotation instead of a full Toffoli clone-gate. (b) **Compete sparsely** — one competition
  event per few generations, not every step. (c) Pulse-efficient / native-gate decompositions on Heron.
  (d) DD in the idle windows the competition opens.

**I3 — Superposition-of-winners dilution.** *Rung 5.*
- *What it is.* If the arena explores many possible winners, amplitude splits across many branches → each
  evolutionary history carries tiny weight → the witness (dominated by the largest branch, often the
  boring no-clear-winner one) is small. The "all winners at once" state is beautiful but statistically
  thin.
- *How to fight.* (a) **Concentrate amplitude:** bias initial reserves so a *few* strong contenders
  dominate, not a flat superposition over all. (b) **Decisive transfer** so branches coherently collapse
  toward a couple of dominant winners. (c) **Conditional witness:** post-select on "a winner emerged"
  and report the conditional value + `kept_fraction` (separates the interesting branches from the null
  branch — labelled conditional, CD-4). (d) Keep L small so dilution is bounded.

> **I4–I8 are PJ0 issues** (single-organism germ/soma, not the arena) — written under the PJ0 section
> above (**PJ0 · main issues & unknowns**). All five must clear before the PJ1 arena opens.

**I9 — Routing between lineages (teleport is DEAD — decided 2026-09-11).** *Resolved.*
- *What it is.* Competition needs a 2-qubit coupling between lineages; distant blocks would force a deep
  SWAP ladder. PJ's stone-wall layout resembles the tree/teleport-routing studies, so teleport looks
  tempting — but it pays **mid-circuit measurement + feed-forward** (Heron's dominant error channel,
  refuted twice), which **collapses PJ's superposition-of-winners** and whose loss is **not DD-fightable**.
  Teleport therefore *violates PJ's coherent principle.*
- *Resolution (settled).* **No teleport.** Tile lineages as **adjacent W12 segments** along the longest
  low-error chain (`layout.best_chain`) so every encounter is neighbour-to-neighbour, using direct /
  short-SWAP gates. The routing problem disappears by construction. The entanglement-swap "predation"
  variant (which *is* teleportation) is likewise **parked** — measurement-heavy, revisit only if a future
  chip gets cheap mid-circuit measurement.
- **What PJ1 improves over the current model.** Real *irreversible* death with **no** witness wound
  (germ/soma, PJ0); death that is *emergent and selective* (competition) not injected; all remaining
  witness loss is hardware noise = EM-fightable; and a *new* observable (joint cross-lineage witness) no
  classical GA can produce. It converts death from a witness-**cost** into a witness-**neutral** soma +
  witness-**source** competition.

### PJ1 · build plan, deliverables & acceptance (the flagship arena — QRNG-driven)

- **Goal.** Tile L germ/soma organisms (each PJ0, W12) as adjacent segments on the longest chain; let them
  compete for energy under **QRNG-driven erratic encounters**; render the living, moving world (P4). The
  spectacle + engineering show-off; the joint witness is upside, not obligation.
- **Prereq.** PJ0 accepted (its five issues cleared). L read off PJ0's per-organism qubit need.
- **Steps = ladder rungs 3–6.**
  - **Rung 3** — L=2 germ/soma organisms, independent, no competition. Baseline: both per-lineage
    witnesses survive; joint ≈ product null.
  - **Rung 4** — add coherent energy transfer (cheap 1–2 CX primitive, I2), QRNG-chosen encounter points
    (fixed per circuit, M5). **Sim Test 2: joint witness − product null > kσ** while the drained lineage
    goes diagonally dead. The quantum-content gate (I1, I3).
  - **Rung 5** — add differential reproduction (controlled-clone gated on reserve); check the
    superposition-of-winners is meaningfully weighted (I3).
  - **Rung 6** — scale L→~4 to fill the longest chain; report joint-witness depth vs L.
- **QRNG role (decided).** Certified stream picks *which* neighbours meet and *when*, fixed per circuit,
  varied per run → erratic, alive-looking dynamics with an entropy receipt (`meta.entropy_provenance`).
  Provenance claim only — quantum content stays the witness.
- **Deliverables.** (1) multi-block arena builder on `qalife.py`; (2) coherent competition + gated-clone
  operators + `--selftest` (2-block closed form); (3) joint-witness helper (generalize
  `xbasis_witness_from_counts:217`); (4) sim Test 2 result; (5) L=2 then L=4 hardware runs vs
  `baseline_P1`; (6) the P4 web-demo feed (positions, encounters, births/deaths, witness overlay).
- **Acceptance.** (a) per-lineage witnesses survive at L=2 (rung 3); (b) sim Test 2 passes — joint witness
  conserved while loser dies diagonally (else PJ1 is honestly the classical spectacle + PJ0 witness only);
  (c) diagonal population dynamics confirmed classically-reproducible (CD-4); (d) any post-selected /
  conditional joint witness labelled with `kept_fraction`; (e) honest framing throughout — spectacle +
  provenance, never speedup.

## PJ2 · multi-run "ages" (classical-stitched lineages — honest compromise, more lively)

- **Idea.** A second, cheaper way to grow richness: run one organism, let its entanglement progress,
  **save the lineage result, then start a new run that treats the saved state as the organism's next
  age** — chaining runs as successive generations, the way the tree study did. Repeat to build a long
  life-history from many short coherent runs.
- **Quantum vs classical (honesty ⚠).** Stitching runs together is **classical concatenation** — the
  quantum coherence does **not** carry across the save/reload boundary (measurement collapses it). So the
  cross-run genealogy is a *classical* record of quantum snapshots; the quantum claim survives **only
  within** each single run, never across the seam. This **compromises the quantum claim** and must be
  labelled as such (CD-4): PJ2 buys *apparent* liveliness and long histories, not deeper certified
  entanglement. Worth building for the demo and for exploring long-horizon dynamics cheaply; never
  headlined as a quantum result.
- **Use it for:** the P4 web demo's long evolutionary narrative, parameter exploration, and as the
  classical scaffold PJ1's genuinely-coherent short runs plug into.

## PJ · how many genealogical lineages are possible

**Settled 2026-09-11: cap depth at W12/lineage, fill the longest chain, let L fall out of PJ0.**

- **Depth per lineage = W12 (max).** 12 individuals = 24 qubits — deliberately half the proven-alive
  unitary ceiling (P2: W\*=24), so each organism sits *comfortably* inside the coherent regime rather than
  at its edge. W12 is the anchor depth (matches the stone-wall virus study); do not exceed it.
- **Fill the longest chain.** Tile adjacent W12 lineages along the longest low-error SWAP-free chain
  (`layout.best_chain`) — the honest "use the whole chip" engineering show-off (PJ1). Each lineage =
  2·12 + 1 resource = **25 qubits**; a ~100-qubit chain holds **≈ 4 lineages**.
- **L is determined by PJ0, not chosen up front.** How many W12 organisms fit = (usable chain length) ÷
  (qubits one PJ0 organism needs to live well). If PJ0 shows an organism needs its full 25 qubits + DD
  headroom to keep its witness, L≈4; if PJ0 lives leaner, L rises. **So finish PJ0 first, then L is read
  off, not guessed.**

| lineages L | depth per lineage | qubits (25/lineage) | note |
|---|---|---|---|
| 2 | W12 | 50 | first arena — easiest coupling, sim + first hardware |
| 3 | W12 | 75 | mid arena |
| 4 | W12 | 100 | **flagship target — fills the longest chain** |

- **Witness-survivable (the real limit, sim-gated).** Qubits are not the wall — the joint witness is.
  Coherent competition + W12 depth *should* survive deeper than damping (W=8) since all loss is
  EM-fightable, but the joint witness over L blocks is fragile (I1). **Survivable L is an empirical P3
  result.** Start L=2 (sim Test 2), scale to L=4 only once the joint witness clears the gate.

## PJ · how they compete (three primitives, pick per experiment)

1. **Energy transfer** — partial-SWAP on reserves; weak lineage bleeds excitation to strong. Gentlest,
   most clearly coherent. Start here.
2. **Differential reproduction** — controlled-clone gated on reserve; fit lineages get more generations.
   This is the actual "survival of the fittest → most generations" mechanism.
3. **Predation (aggressive) — PARKED.** Winner grafts the loser's qubits onto its own chain via
   entanglement swapping = teleportation = mid-circuit measurement. Killed for now with teleport (I9);
   revisit only on a chip with cheap measurement.

**Encounter scheduling for all primitives:** *which* neighbours meet and *when* is drawn from the
certified QRNG (fixed per circuit, varied per run) — erratic, quantum-sourced dynamics (M5). Provenance
claim, not advantage; quantum content stays the witness.

## PJ · honest two-axis score

- **Biological richness:** very high — multiple organisms, real competition, differential reproduction,
  emergent death, survival of the fittest. The most alive-looking life in the whole menu.
- **Witness survival:** the open bet. Per-lineage witness may drop as entanglement spreads; the **joint**
  witness is the claim, and PJ's design keeps all loss EM-fightable — so it is the **first richness move
  with a credible path to being witness-positive** rather than a pure cost. Not guaranteed. Sim decides.
- **Classical surrogate:** population dynamics / who-wins = classical plumbing (declare it so, CD-4).
  Only the joint cross-lineage witness carries the quantum claim.

## PJ · the honest end-game

Organisms with a **position in space** (PM3), **moving**, **competing** for energy, the fittest genome
persisting across the most generations, losers dying by starvation — rendered as a P4 web demo that
**looks like living organisms in a world**, with the certified joint witness reported honestly alongside
(never as speedup). PJ1 supplies the genuine quantum core (short coherent arenas); PJ2 supplies the long
classical narrative; PM3 supplies the spatial embodiment. That composite — coherent where it can be,
classically-stitched where it must be, always labelled — is the honest "most lively quantum life on 2026
hardware."

## PJ · the sim tests that prove-or-kill it (do before any hardware)

Two gates, cheap and decisive, run in ladder order:

- **Test 1 — germ/soma isolation (rung 1, the FIRST test, single lineage).** Ideal statevector. Compare
  the germ-line witness with soma-death **on** vs **off**. **Pass ⇔** the two are equal within noise —
  isolated soma death costs the witness ~zero (Idea A works). **Fail ⇔** soma death still drops the
  witness → the decoupling leaks; fix before anything else. This is the gate on the whole germ/soma
  premise and the cheapest experiment in the program.
- **Test 2 — coherent competition conserves the joint witness (rung 4, two blocks).** L=2, small depth,
  coherent energy-transfer + controlled-clone, **no damping**. **Pass ⇔** the joint cross-lineage witness
  stays certified (> kσ over its separable joint null) while the losing lineage goes **diagonally** dead
  (phenotype ⟨σz⟩ → `|0⟩`) — death with entanglement *conserved, not discarded*. **Fail ⇔** the joint
  witness collapses with the loser → PJ reduces to M2's pessimistic case. No chip time either.

## PJ · prereqs / status

- **Prereqs (PJ0, the first build):** separable diagonal phenotype (reuse the unitary arm's
  `_z_geno_chain:87` → `ry(aged)`); a phenotype-only soma-death (local-damping copy of `:144–147` with
  `cx(g,p)` removed, or none + natural decay); selective DD targeting genotype qubits (EM1). All
  single-lineage — no new multi-block code yet.
- **Prereqs (PJ1 arena, later):** M3-style multi-block encoding; a coherent competition gate (new,
  `--selftest` vs a closed-form 2-block case); the joint-witness helper (generalize
  `xbasis_witness_from_counts:217` / `entanglement_depth:239`).
- **Status:** **PJ0 = NOT STARTED — the first new biology to implement (developer-directed).** Gated only
  behind sim Test 1. PJ1 arena is the richness *destination*, gated behind sim Test 2 + PJ0 landing. The
  EM stack (esp. selective DD) is pulled in *by* PJ0, not a separate prerequisite.

---

# Work-package EM · Error mitigation — the first lever (CD-11) and the focus of P3-entry

**Status: NOT STARTED — this is the recommended next move (§0).** This is not one candidate move; it is
a bounded work-package whose job is fixed by P2: **finish the damping W\* measurement (run W=5, W=6)
and push the ceiling outward.** Every diagonal metric here is already exact-classical (CD-3); the *only*
thing mitigation buys is a taller, farther-reaching **witness** ⟨X^⊗W⟩ — so mitigation is not cosmetic,
it is the instrument that moves the frontier. The published precedent is exact: genuine multipartite
entanglement in GHZ states — the same object as our genotype-line witness — has been certified on
IBM superconducting hardware out to tens (Mooney 2021, 27 qubits) and hundreds (2023, up to 414 qubits)
of qubits **specifically by stacking readout mitigation, dynamical decoupling, and parity/stabilizer
post-selection**. Our witness is that literature's central observable; those are our levers.

**Pipeline reality (governs order).** The witness is computed from **Sampler counts** by
`xbasis_witness_from_counts` (`qalife.py:217`) — H on the genotype qubits, joint X-parity of the
bitstrings. This splits the levers cleanly:

- **Counts-native (cheap, no pipeline rewrite):** DD (a transpile-time scheduling pass), readout
  mitigation (post-processing the counts), and stabilizer/parity **post-selection** (filtering the
  bitstrings we already have). These bolt onto `build_measured`/`run_counts` (`run_qalife.py:100`,
  and the sampler dispatch) with almost no structural change — **do these first.**
- **Estimator-native (heavier lift, real shot cost):** ZNE, Pauli-twirled TREX, and PEC are natural to
  Qiskit Runtime's V2 **Estimator** `resilience` options, not the Sampler-counts path. Adopting them
  means either moving the witness onto an Estimator (compute ⟨X^⊗W⟩ as a Pauli expectation directly) or
  hand-rolling folding/twirling around the sampler. **Do these only after the cheap levers are spent.**

**Reporting rule for every EM sub-move (extends the CD-11 kept-fraction rule).** Each lever is scored as
**ΔW\*** (how far it moves the certified damping ceiling) against its **cost**: shot-overhead multiplier
and — for post-selection — `kept_fraction` (epic §4 field). A witness that only clears the gate *after*
post-selection is a **weaker, conditional** claim than a raw one (you conditioned on GHZ-looking shots);
report raw and post-selected witnesses **side by side**, never post-selected alone. This is the honesty
knife applied to mitigation itself.

## EM1 — Dynamical decoupling (do first: free, counts-native)

- **Idea.** The genealogy is built individual-by-individual; early founders' genotype qubits sit
  **idle** (accumulating dephasing) while the later CNOT-clones and the per-generation damping arms are
  laid down. Idle time grows ~O(W). DD fills that idle time with pulse trains (X–I–X–I / XY4) that
  average slow dephasing to identity — the exact technique shown to prolong 7-qubit GHZ coherence on
  IBM `mumbai`.
- **Encoding.** A transpiler scheduling pass (`PadDynamicalDecoupling`, XY4 or `XX`) inserted after the
  layout/routing done in `run_qalife.py`; no change to `qalife.py`, no change to the witness math. Draw
  under `--dump-circuit` to confirm pulses land on idle windows.
- **Cost.** ~zero. No extra shots, `kept_fraction = 1`. Pure suppression, not post-selection → the
  witness stays an *unconditional* claim.
- **Expected ΔW\*.** Positive on both axes; largest on the damping axis where idle windows are longest.
  Best value-per-effort lever in the whole package. **Try first.**

## EM2 — Readout / measurement-error mitigation (do second: counts-native)

- **Idea.** ⟨X^⊗W⟩ is a joint Pauli expectation read off bitstrings; assignment error on any single
  qubit corrupts the joint parity. QREM shifts stabilizer expectations back toward their ideal ±1 and
  is reported to lift the median genuine-witness value.
- **Encoding.** **TREX** (twirled readout extinction — the textbook fit for a Pauli-observable
  expectation, twirls before measurement so readout error becomes a uniform shift) or **M3/mthree**
  (matrix-free, ideal for the sparse GHZ-like X-basis outcome distribution). M3 runs as post-processing
  on the returned counts; TREX needs pre-measurement twirl circuits.
- **Cost.** M3: light (calibration shots + cheap linear solve), `kept_fraction = 1`. TREX: modest shot
  overhead for the twirl set. Both are mitigation, not post-selection → witness stays unconditional.
- **Expected ΔW\*.** Solid, compounding with EM1. On this chip readout ≤ 0.012 on good chains, so the
  gain is bounded — but at large W the joint parity is where single-qubit readout error accumulates, so
  it matters more as W grows.

## EM3 — Pauli twirling / randomized compiling on the CNOT-clone chain (do third)

- **Idea.** The self-replication ladder is a chain of CX gates (`qalife.py` self-rep, one CX per birth);
  their **coherent** error is what a witness is most sensitive to. Twirling each CX (random Paulis
  before/after, compiled away in the ideal) converts coherent error into stochastic/depolarizing error —
  which both raises the raw witness slightly and is the **precondition** for well-behaved ZNE (EM4).
- **Encoding.** Randomized-compiling wrapper generating N twirled variants of the circuit; split the
  shot budget across them and average. Sits between `build_measured` and submission.
- **Cost.** No net shot increase (shots split across variants); some classical build overhead.
  `kept_fraction = 1`.
- **Expected ΔW\*.** Small on its own; its real role is to **de-bias EM4**. Do it as the bridge to ZNE.

## EM4 — Zero-noise extrapolation (do fourth: estimator-native, real shot cost)

- **Idea.** Amplify noise (fold the CX clone ladder: G → G G† G at factors 1, 3, 5), measure the witness
  at each factor, extrapolate to zero noise.
- **Encoding.** Two routes: (a) move the witness onto a V2 **Estimator** with `resilience_level`/ZNE
  options and observable X^⊗W; or (b) manual local folding of the CX ladder in `qalife.py` + polynomial
  extrapolation of the counts-witness. Requires EM3 (twirling) first, or the extrapolation is biased by
  coherent error.
- **Cost.** ~3–5× shots (one witness estimate per noise factor). `kept_fraction = 1` but a genuine
  budget hit — report ΔW\* per shot-multiplier.
- **Expected ΔW\*.** Potentially the largest single push, but the most expensive and the biggest code
  change. Gate it behind the cheap levers.

## EM5 — Stabilizer / parity post-selection (the counts-native standout — do alongside EM1/EM2)

- **Idea.** *We already measure every genotype in the X basis.* The ideal genotype line is a GHZ-like
  state whose X-basis outcomes obey the stabilizer group (neighbour parities X_iX_{i+1} = +1, fixed
  global parity). Decohered shots violate that structure. So we can **discard the violating bitstrings
  and recompute the witness on the survivors** — pure post-processing on data we already have, *no extra
  circuit, no extra qubit*. This is the epic's "parity herald," and it is exactly the parity-verification
  error-detection Mooney 2021 used to certify the 27-qubit GHZ.
- **Encoding.** A filter inside `xbasis_witness_from_counts` (or a wrapper): keep shots consistent with
  the GHZ stabilizers, track surviving fraction as `kept_fraction`. Optional stronger form: add an
  ancilla parity check + mid-circuit measure — but that reintroduces the dominant Heron error channel
  (why teleport-routing lost), so the **pure post-processing form is strongly preferred**.
- **Cost.** `kept_fraction < 1` (drops with W — the honest price). **Post-selection biases the witness
  upward** → report raw vs post-selected side by side (CD-4); the post-selected number is a *conditional*
  certification, a weaker claim than EM1/EM2's unconditional one.
- **Expected ΔW\*.** Large — post-selection is how GHZ experiments reach their deepest certified widths —
  but it must be labelled as conditional. This is the single most *powerful* counts-native lever and the
  one most in need of an honesty caveat.

## EM6 — Probabilistic error cancellation (the ceiling — probably too costly, list for completeness)

- **Idea.** Learn the per-layer noise (Heron exposes layer-fidelity / sparse Pauli-Lindblad models) and
  sample its inverse to produce an **unbiased** zero-noise witness estimate.
- **Cost.** Sampling overhead grows exponentially in circuit error → feasible only for the *shallow* end
  of the clone chain (small W), which is exactly where the witness already survives. `kept_fraction = 1`
  but the shot cost is the wall.
- **Expected ΔW\*.** In principle the strongest and only *unbiased* heavy lever; in practice a research
  aside — quote it as the theoretical ceiling, not a planned run, unless a small-W unbiased cross-check
  of EM4/EM5 is wanted.

### EM — recommended stack, immediate deliverable, honesty ledger

- **Stack, cheap→costly (report ΔW\* and cost at each step):** EM1 (DD) → EM2 (readout, M3) → EM5
  (parity post-selection, raw+conditional) → EM3 (twirl) → EM4 (ZNE) → [EM6 ceiling].
- **Immediate deliverable (finishes P2 §6):** rerun the damping circuit at **W=5 and W=6** with the
  EM1+EM2+EM5 stack; report (a) the raw damping W\*, (b) the mitigation-pushed W\*, (c) the
  post-selected conditional W\* with its `kept_fraction`, and (d) re-render Fig. 1's damping series.
  Then the P2→P3 gate is genuinely closed and Tier PM opens.
- **Honesty ledger (per run):** raw vs post-selected witness side by side; `kept_fraction`; shot
  multiplier; the separable null (must stay ≤ 2×10⁻⁶ as in P2); live 2q/readout calib. Mitigation must
  never be allowed to manufacture a witness the separable null doesn't confirm is off-diagonal.

**Internet grounding (searched 2026-09-11):** GHZ = our witness object; the mitigation recipe is
borrowed, not invented. Mooney et al. 2021 (QREM + parity verification, 27-qubit GHZ GME, fidelity
0.546±0.017, 98.6% confidence) `https://inspirehep.net/files/a6f163ddf8e35baa771a97047ce128af`;
characterization of entanglement up to 414 qubits `https://arxiv.org/pdf/2312.15170`; multiple-quantum-
coherence GHZ verification `https://arxiv.org/pdf/1905.05720`; IBM error-mitigation & suppression
(DD, ZNE, TREX, PEC, resilience levels) `https://quantum.cloud.ibm.com/docs/en/guides/error-mitigation-and-suppression-techniques`;
M3 sparse readout mitigation `https://arxiv.org/html/2201.11046`.

---

# Paper-grounded richness moves (PM-series) — the 2018 paper's own scalability routes

**Tried before the developer-brainstorm M-series (developer directive, §0).** Every move here maps to a
specific sentence of the paper's future-work text preserved verbatim at the bottom of this file (*source
of thought — do not edit*); the mapping is quoted per entry so the provenance is auditable. Same two-axis
honesty rule as every other move: **biological richness added** vs **witness survival**, kept separate,
scored against `research/baseline_P1/`. Crucially, the paper *itself* concedes (bottom text) that
lifetime and predator–prey character are **classical** (encoded in ⟨σ_z⟩) — so several of its own routes
are diagonal plumbing, and the honest quantum question for each is whether it changes the *entanglement
structure* the witness sees, not whether it makes the life look more alive.

## PM1 — More degrees of freedom per living unit (the paper's literal first route)

- **Paper.** *"increasing the number of qubits, and making them part of the updated genotype and
  phenotype … repeating the partial cloning processes and extending the dissipation to the new
  phenotype qubits."*
- **Idea.** Grow each individual from 2 qubits (1 genotype + 1 phenotype) to **g genotype + p phenotype**
  qubits. Self-replication becomes a multi-qubit partial clone; dissipation extends to every new
  phenotype qubit; the extra genotype observables carry new traits (→ PM2).
- **Encoding.** Generalize `geno_q`/`pheno_q`/`bath_q` (`qalife.py:60/64/68`) from stride-2 to
  stride-(g+p); the self-rep CX becomes a CX *fan* (one per genotype qubit); the damping arm
  (`qalife.py:144–147`, CRY→bath→CX) repeats per phenotype qubit. The witness generalizes to a joint
  X-parity over the **enlarged** genotype register — still a single Pauli string, still counts-native.
- **Quantum vs classical.** This is the paper's stated **route to genuine new quantum content**: more
  entangled genotype qubits = a larger, richer multi-qubit entangled state = a *deeper* witness with no
  classical surrogate. The diagonal phenotype metrics stay exact-classical (CD-3). This is the rare move
  that adds richness **on the quantum axis**, not just the plumbing axis.
- **Expected witness cost.** Mixed: more genotype qubits per unit deepen the witness (good) but multiply
  gate count and idle time per generation (decoherence, bad). Net effect is an **empirical** question —
  exactly the kind P3 exists to measure. Pairs naturally with Work-package EM.
- **Measured against.** Enlarged-register witness vs separable null vs ideal, at matched *total* qubit
  budget, so "richer unit at fixed width" is separated from "more width."
- **Prereqs / status.** EM stack landed (so the deeper witness has a fighting chance). **NOT STARTED —
  candidate (best paper-grounded entry point).**

## PM2 — Genotype-encoded trait observables (differentiated individuals)

- **Paper.** *"additional observables in the genotype would enable … different self-replication rates,
  independent lifetime and interaction role, or capacity to displace along the associated Hilbert
  space."*
- **Idea.** Use PM1's extra genotype qubits to encode **per-individual traits**: a self-replication-rate
  observable (how strongly it clones), a lifetime observable **decoupled** from the interaction-role
  observable (today one ⟨σ_z⟩ conflates them). Individuals become heterogeneous — real variation for
  selection to act on.
- **Encoding.** Extra genotype qubit(s) whose ⟨σ_z⟩ set, per individual, the clone strength (partial-CX
  angle), the damping `g_eff` (`qalife.py:141`), and the interaction partner/strength
  (`interaction_partner`, `:74`) — read at circuit-build time from the genotype prep.
- **Quantum vs classical.** ⚠ **The paper concedes this is diagonal:** trait values live in ⟨σ_z⟩ and a
  classical analogue reproduces them exactly (bottom text). Richness: high (heterogeneous population).
  Quantum content: **near-zero by itself** — the honest question is whether trait-driven *differential
  entangling* (unequal clone strengths) leaves a distinguishable off-diagonal fingerprint the witness
  sees. Default prior: mostly classical.
- **Expected witness cost.** Low-to-moderate direct cost; value is biological completeness, not witness.
- **Measured against.** Witness at matched W plus a **classical-surrogate check** — if a laptop
  heterogeneous-trait sim reproduces the population within kσ, traits are declared plumbing (CD-4).
- **Prereqs / status.** Needs PM1. **NOT STARTED — candidate (richness-heavy, quantum-light).**

## PM3 — Mobility / spatial variables ("displace along the Hilbert space")

- **Paper.** *"capacity to displace along the associated Hilbert space"* and *"even considering spatial
  variables for the individuals."*
- **Idea.** Give individuals a **position** and let them move, so who-meets-whom is emergent geometry,
  not the fixed `k−1` neighbour rule. The epic menu's "spatial / 2D population" is this.
- **Encoding.** A position register per individual (or a 2D lattice embedding of the genotype qubits);
  `interaction_partner` (`:74`) generalizes from `k−1` to a distance rule on positions; movement =
  updating the position register between generations.
- **Quantum vs classical.** Position bookkeeping and who-meets-whom = **classical** (a laptop
  cellular-automaton does it). Quantum-interesting *only* if position is held in **superposition**
  (an individual entangled across locations) so the interaction graph itself is a quantum variable —
  otherwise diagonal.
- **Expected witness cost.** Diagonal version: cost lives in whatever interaction it enables. Coherent-
  position version: heavy (more entangled DOF to protect) but the only version with a witness claim.
- **Measured against.** Witness vs baseline at matched W; classical spatial-sim surrogate check.
- **Prereqs / status.** Pairs with PM1 (DOF for the position register) and M3 (multiple lineages to move
  among). **NOT STARTED — candidate.**

## PM4 — Qudit / high-dimensional partial cloning

- **Paper.** *"encode the information in quantum states of higher dimensions. The general result of
  partial quantum cloning to qudits of any dimension makes this family of hypothetical models feasible,
  conditional to the availability of high dimensional entangling operations."*
- **Idea.** Represent genotype/phenotype as **qudits** (d>2) — more information per living unit at fixed
  particle count.
- **Encoding.** No native qudits on Heron transmons → **emulate** a d-level unit with ⌈log₂ d⌉ qubits
  and synthesize the partial-clone + damping as multi-qubit unitaries. In practice this collapses toward
  PM1 (more qubits per unit) unless a genuinely qudit-native platform is used.
- **Quantum vs classical.** Genuinely quantum (higher-dimensional entanglement) **but** the paper's own
  caveat — "conditional to high dimensional entangling operations" — is the blocker: emulated qudits pay
  full multi-qubit-gate decoherence for the encoding overhead. Likely a **witness loser** on 2026
  transmon hardware.
- **Expected witness cost.** Heavy (encoding overhead) with weak upside on this platform. Honest verdict:
  **deferred / low priority** here; flagged as the move that wants a different platform (trapped-ion /
  photonic qudits).
- **Measured against.** N/A near-term — documented as a platform-gated future route.
- **Prereqs / status.** Platform-gated. **NOT STARTED — candidate (parked, honestly).**

## PM5 — Trace-out mechanism for dead units (the paper's "removal" primitive)

- **Paper.** *"a mechanism for tracing out death living units"* → *"the evolution will be an intrinsic
  property of the system."*
- **Idea.** Today dead individuals linger in the register (damping just drives them toward |0⟩). Add an
  explicit **trace-out**: reclaim a dead unit's qubits (reset) so the register is a living population, not
  a full history — the enabler for open-ended, autonomous runs (PM7) and for fitting more *live*
  individuals in a fixed width.
- **Encoding.** Mid-circuit measure of the phenotype "lifetime" observable + conditional `reset` of a
  below-threshold individual's qubits — the same feed-forward primitive as M1 (`death_mode='selection'`),
  which is why PM5 and M1 are close cousins.
- **Quantum vs classical.** The trace-out *decision* is classical; its cost is quantum. ⚠ **Mid-circuit
  measurement is the dominant Heron error channel** (why teleport-routing lost) — the reset injects the
  worst noise on the chip. As with M1, the witness bite *is* the measurement.
- **Expected witness cost.** Heavy (mid-circuit measure + feed-forward). But it is the structural
  prerequisite for genuine autonomy (PM7).
- **Measured against.** Witness vs baseline with/without trace-out at matched live-population size;
  `kept_fraction`. Overlaps M1 — run them as one experiment.
- **Prereqs / status.** Dynamic-circuit capability (present, per `_teleport_cx`). **NOT STARTED —
  candidate (merge with M1).**

## PM6 — Branching genealogy / tree substrate (the one PM move that adds *new* quantum content)

- **Paper.** *"the extra free parameters available in the superposition and entanglement of quantum
  states are used for describing … the collective dynamics of individuals … the new source of complex
  behavior."* Also the epic menu's "Quantum-Tree genealogy substrate (§2B)."
- **Idea.** Today the genealogy is a **line** (each individual clones the previous one → a GHZ chain).
  Let a parent spawn **multiple offspring** → a **branching tree**. The entangled state is no longer a
  GHZ chain but a **graph/tree state** with richer multipartite structure — genuinely new *collective*
  quantum content, not diagonal plumbing.
- **Encoding.** Self-replication CX fans from one parent genotype to several children
  (`build_population` loop generalized from `k−1` predecessor to a branching parent map); the witness
  generalizes from a single X-parity string to the **tree-state stabilizers** (per-branch X-parities and
  their products). Still Clifford entangling, still counts-native — **no mid-circuit measurement**, so it
  does *not* pay the Heron measurement tax.
- **Quantum vs classical.** ⭐ **This is the strongest paper-grounded quantum-content move.** A tree state
  has entanglement structure a GHZ chain does not; the joint/graph witness has no classical surrogate;
  and unlike PM2/PM3 it needs no diagonal-only bookkeeping. It directly instantiates the paper's
  "collective dynamics via superposition and entanglement."
- **Expected witness cost.** Comparable to the unitary GHZ chain per qubit (only CX + H), so it inherits
  the *good* axis (W\*=24-class survival), while delivering richer structure. Best richness-per-witness-
  cost of the PM-series.
- **Measured against.** Tree/graph witness vs its separable null vs ideal, at matched qubit count against
  the linear-genealogy baseline — the headline comparison "does branching structure survive as far as
  the line?"
- **Prereqs / status.** Reuses existing Clifford machinery; benefits from EM. **NOT STARTED — candidate
  (best paper-grounded richness move; co-lead with PM1).**

## PM7 — Autonomous / intrinsic evolution (the paper's far horizon)

- **Paper.** *"the evolution will be an intrinsic property of the system, and the desired behavior will
  emerge without following the instructions of a previously designed quantum algorithm … an intelligent
  source of quantum complexity."*
- **Idea.** Replace the scripted per-generation program with a **closed feedback loop**: measured
  fitness drives births/deaths/mutations at runtime (dynamic circuits + classical controller), so
  evolution is emergent, not choreographed.
- **Encoding.** M1 (measured selection) + PM5 (trace-out) + M5/M6 (QRNG environment) fused under a
  runtime controller in `run_qalife.py`; heavy use of mid-circuit measure + feed-forward.
- **Quantum vs classical.** The autonomy is a control-architecture property; the quantum claim is still
  the witness. ⚠ Maximally measurement-heavy → **expected to crush the witness on 2026 hardware.** Value
  is the demonstration of autonomy + charting how fast feedback extinguishes the signature.
- **Expected witness cost.** Severe. Frontier/aspirational.
- **Measured against.** Witness under closed-loop vs scripted, at matched biology; `kept_fraction`.
- **Prereqs / status.** Needs M1 + PM5 + a controller. **NOT STARTED — candidate (far horizon).**

## PM8 — Optimization-encoding & replicating QML agents (the application horizon)

- **Paper.** *"channeling this complexity to encode optimization problems by tuning the self-replication,
  mutation and dissipation rates … recent advances in quantum machine learning … intelligent and
  replicating quantum agents."*
- **Idea.** Treat the model as a substrate: tune (self-rep, mutation, dissipation) rates so the
  population's evolution **solves** an optimization problem (genetic-algorithm framing), or couple it to
  a QML agent.
- **Encoding.** Parameterize the existing rate constants (`DAMP_GAMMA:53`, mutation scale, clone angle)
  as optimizable variables; define a cost from a measured observable; outer classical optimizer.
- **Quantum vs classical.** An *applications* direction, not a richness-vs-witness measurement — the
  witness is not the figure of merit here, solution quality is. Kept in scope only as the eventual "so
  what" (ties to P4 framing / the thesis narrative), explicitly **out of the P3 witness study**.
- **Expected witness cost.** N/A (different figure of merit).
- **Measured against.** Optimization performance vs a classical GA baseline — a separate study.
- **Prereqs / status.** Post-P3. **NOT STARTED — candidate (application horizon, parked).**

---

# Updated evaluation — the mitigation-budget axis (extends the checklist above)

Every move now carries a **third** honesty column beyond richness and witness-survival: its **mitigation
budget** — shot multiplier + `kept_fraction` + whether its witness claim is *unconditional* (suppression:
DD, readout, twirl, ZNE, PEC) or *conditional* (post-selection: EM5, and any stabilizer herald). A move
that only survives under post-selection is reported as a conditional datapoint, never conflated with an
unconditional one. This column is what makes the P4 phase diagram honest: some frontier points will be
"alive only with mitigation X at kept-fraction Y," and that label is part of the result.

# Recommendation — the best next candidate, and the run order behind it

0. **NOW (the first build) — PJ0 germ/soma split, ladder rung 1.** Separable diagonal phenotype + isolated
   soma death + selective DD on the genotype. Sim Test 1 first (witness with soma-death on ≈ off). Fixes
   the P2 witness wound, single-lineage, cheapest experiment in the program, and the substrate all later
   PJ stages need. *Developer-directed first new biology.*
1. **IN PARALLEL — Work-package EM (EM1+EM2+EM5) on the damping circuit at W=5, W=6.** Closes the open P2
   loose end (locate the damping W\*), cheap and counts-native, shares the DD/readout tooling PJ0 pulls in.
   Deliver raw + mitigation-pushed + conditional (post-selected) W\*.
2. **THEN — PM1 (more DOF per unit) and PM6 (branching tree), co-led.** The two paper-grounded moves that
   add richness on the **quantum** axis rather than diagonal plumbing; both reuse existing Clifford +
   damping machinery and ride the EM stack. PM6 is the safer bet (Clifford-only, no measurement tax);
   PM1 is the paper's literal first sentence.
3. **FLAGSHIP — PJ (multi-organism coherent competition).** The richness *destination*: several organisms
   competing over energy, fittest earning the most generations, **death emergent from losing (no
   dissipation)** so all witness loss is EM-fightable. Gated behind its own cheap **sim test** (2 blocks,
   joint witness conserved while loser goes diagonally dead). If sim passes, PJ jumps ahead of the
   diagonal-heavy PM/M moves — it is the only richness candidate with a credible path to being
   witness-*positive*. Supersedes M2 + M3.
4. **LATER — PM2/PM3/PM5 (diagonal-heavy richness), then the residual M-series (M1 selection, M4 routing,
   M5/M6 stochastic environment).** Rich, mostly-diagonal, measurement-heavy; each a phase-diagram
   datapoint once the quantum-axis moves are charted. (M2/M3 now live inside PJ.)
5. **PARKED — PM4 (qudits, wrong platform), PM7 (autonomy, measurement-crushed), PM8 (optimization/QML,
   different figure of merit).** Documented as future/off-platform routes, not near-term runs.

Honest expected shape of the P3 result: **EM widens the certified frontier a bounded amount; PM1/PM6
push richness up the quantum axis at real but survivable witness cost; everything measurement-heavy
(M1, PM5, PM7) collapses the witness — and where each collapses is the datapoint.** No speedup is
claimed anywhere (CD-4).


## Ideas that are in the original rersearch paper to improve the QC artificial life  DO NOT CHANGE THIS IS SOURCE OF THROUGHT
## link to the paper  https://pmc.ncbi.nlm.nih.gov/articles/PMC6172259/#Abs1
## link to wiki https://en.wikipedia.org/wiki/Quantum_artificial_life

Regarding the emergence of complexity, the route towards the scalability of our quantum algorithm is intrinsically
related to the inclusion of more degrees of freedom in the description of quantum living units. 
These may be introduced by simply increasing the number of qubits, and making them part of the updated genotype and phenotype.
A part of the dynamics would be adapted by repeating the partial cloning processes and extending the dissipation to the new phenotype qubits. 
Another part of the dynamics would deal with the properties introduced by the new degrees of freedom. 
In the same way as the genotype in the current model rules the individual-environment and inter-individual interactions, 
additional observables in the genotype would enable the exploration of more characteristics: different self-replication rates, 
independent lifetime and interaction role, or capacity to displace along the associated Hilbert space, all of them encoded in the genotype. 
An alternative is to encode the information in quantum states of higher dimensions. 
The general result of partial quantum cloning to qudits of any dimension makes this family of hypothetical models feasible, 
conditional to the availability of high dimensional entangling operations.

A different question is the scalability of the current model without including any modification. 
Notice that, in our protocol, the information about the lifetime and the predator-prey character 
is classical and encoded in the mean value 〈σz〉 of the phenotype and the genotype of the individual, respectively. 
Therefore, this partial dynamics can be predicted with a simpler classical analogue. However, 
the full quantum description of our protocol allows one to retrieve the connections between the quantum living units, 
linked through entanglement, which is a useful complement that is absent in the classical analogue. 
In other words, the extra free parameters available in the superposition and entanglement of quantum states are used for describing questions regarding the collective dynamics of individuals, and this is precisely the new source of complex behavior our algorithm is able to create. In this sense, the complexity of our quantum algorithm may only be reached by a larger quantum computer, currently being built in academic institutions and companies. This might yield unexpectedly interesting outcomes but, at the same time, will increase the sensitivity to decoherence during the self-replication process.

This experimental realization of the proposed quantum algorithm represents the consolidation of the theoretical 
framework of quantum artificial life. The improvement in scalable quantum computers will soon allow us for more accurate 
quantum emulations with growing complexity towards quantum supremacy, even considering spatial variables for the individuals 
and a mechanism for tracing out death living units. These future developments should lead towards an autonomous character of the set of individuals, 
i.e., the evolution will be an intrinsic property of the system, and the desired behavior will emerge without following the instructions 
of a previously designed quantum algorithm. In this context, the system would be transformed into an intelligent source of quantum complexity 
whose evolutionary plot for a large number of individuals may not be predicted classically and, consequently, 
has the capacity to produce unexpected results when scaled up. An interesting question to address is to establish the relation existing 
between the parameters defining the fundamental processes of the model, and the emergent multiqubit quantum state. Along these lines, 
and following the frame of artificial life oriented genetic algorithms37, we speculate about the idea of channeling this complexity 
to encode optimization problems by tuning the self-replication, mutation and dissipation rates that define the evolution. Furthermore, 
recent advances in quantum machine learning constitute a promising material to work with in the study of algorithms combining the properties of both fields,
pursuing the design of intelligent and replicating quantum agents. Therefore, the creation of these quantum living units and their possible 
applications are expected to have deep implications in the community of quantum simulation and quantum computing in a variety of quantum platforms.

All in all, the experiments presented here entail the validation of quantum artificial life in the lab and, in particular,
in cloud quantum computers as that of IBM. Still another interesting step would be the development of autonomous quantum devices following the 
theoretical and experimental results in quantum cellular automata38–42. Our quantum individuals are driven by an adaptation effort along the 
lines of a quantum Darwinian evolution, which effectively transfer the quantum information through generations of larger multiqubit entangled states. 
We believe that the presented results and vision, both in theory and experiments, should hoist this innovative research line as one of the leading 
banners in the future of quantum technologies.