# Feature Plan — PJ2: An enriched proto-viral organism living in a quantum habitat (the solo vivarium, one run)

**Ticket:** PJ2 (stage, not a GitHub issue — this research repo decomposes epics into stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09), stage **P3** (richness investigations, late-stage/exploratory)
**Candidate source:** `artificial-life/plans/P3-candidate-movess.md` — PJ ladder **rung 5** (differential reproduction / "survival of the fittest"), **M5** (QRNG-driven stochastic biology), **M6** (quantum-random environment), **PM1** (more degrees of freedom per unit), **PM3** (mobility/spatial); picks up the rung-5 hook PJ1 left explicitly out of scope.
**Inspiration (developer-directed):** the 2018 paper's own end — Alvarez-Rodriguez, Sanz, Lamata, Solano, *Quantum Artificial Life in an IBM Quantum Computer*, Sci. Rep. 8:14793 (2018), **Discussion §"Scope of Quantum Artificial Life"** (roadmap quotes in §1).
**Substrate:** `code/pj_qalife.py` (germ/soma model — PJ0 `build_germsoma` + PJ1 `build_arena`, both byte-stable) + a **new** driver `code/pj_vivarium.py`.
**Slug:** solo-vivarium
**Author:** Claude (Opus)
**Date:** 2026-09-23
**Status:** Complete (2026-09-23; OQ-1…OQ-7 resolved §11; see §13)

> **No tests (repo convention, CD-7).** Verification is `--selftest` (static circuit-structure checks) +
> `--dump-circuit` printing + `--sim` runs + a written correctness/conclusion evaluation. No test framework,
> no test files.
>
> **This ticket RUNS (build + sim + live-ready).** Like PJ1: build the model, verify statically, run in `--sim`,
> and land a **live Heron-r2** circuit. The developer executes the hardware run (per the established
> division of labour). Sim-first, hardware-confirm (CD-7).
>
> **One quantum run, not frames (the defining lock, developer-directed).** Unlike PJ1 (which banked a
> **movie** = one measured circuit *per time-step frame*, many jobs), PJ2 bakes the whole life cycle —
> genealogy + the body's walk through its habitat + consumption + selection — into **one circuit** measured
> **once** at a terminal time `T`. Time is **circuit depth**, not job count. The animation is reconstructed
> from a **statevector-sim snapshot at each internal barrier of the identical circuit** (labelled sim-only,
> exactly the existing `pj1_spectacle.py` "simulation artifact" pattern); the **certified numbers are the
> single measured endpoint** (`⟨X^⊗W⟩` alive, final occupancy, alive-count, selected survivors, food consumed).

---

## 1. Summary

PJ2 puts **meat on the bone of a single organism** and drops it into **a space to live in** — a bounded
quantum **habitat (vivarium)** seeded with resources — with **heredity, viral traits, and survival-of-the-fittest
baked in**, all contained in **one quantum run** (no frame-sweep). It is the single-organism (L=1) counterpart
of PJ1's two-organism arena, and it activates the **rung-5 differential-reproduction hook** PJ1 left as an idle
qubit (`trait_q`, PJ1 §3 out-of-scope).

The design is taken straight from the **end of the 2018 paper** (Discussion §"Scope of Quantum Artificial
Life"), which lays out exactly this next step, verbatim:

- *"the inclusion of **more degrees of freedom** in the description of quantum living units… by simply
  increasing the number of qubits, and making them part of the updated genotype and phenotype"* → the
  enriched, more-defined organism (§Architecture).
- *"additional observables in the genotype would enable the exploration of more characteristics: **different
  self-replication rates, independent lifetime and interaction role, or capacity to displace along the
  associated Hilbert space, all of them encoded in the genotype**"* → the **structured genome trait bits**
  (replication-rate / lifetime / role) and **genotype-encoded motility** (the hop that moves the body).
- *"even considering **spatial variables for the individuals** and a **mechanism for tracing out death living
  units**"* → the **habitat track** + **trace-out death** (dead soma idled, read as a marginal, never coupled
  back to the germ line).
- *"exploit the **natural decoherence** present in quantum platforms and use error correction protocols **only
  in the genotype qubits**… this phenotype-genotype asymmetry… is the key element"* → **already built** as
  PJ0's Weismann barrier + selective DD on the germ line only (reused unchanged).
- *"channeling this complexity to encode optimization problems by **tuning the self-replication, mutation**"* →
  **survival of the fittest**: a **static fitness ancilla** (no mid-circuit measurement) gates who persists /
  replicates based on what the body ate.

**The organism (enriched, "viral-simple") — one thing, not two.** The genome has two co-inherited parts:
the **witness loci** `witness_q` (the W-generation GHZ genealogy carrying `⟨X^⊗W⟩` — the quantum, certified
heredity, unchanged from PJ0) and a **small register of classical genes** `gene_q` (diagonal trait bits
`t_repl`, `t_life`, `t_role`/motility — the paper's extra genotype observables, displayed as the organism's
*properties*). The **soma body** is a walker in the habitat — and it is **expressed from the genome**: the
classical genes drive the body's behavior (motility gene → hop rate, etc.). Simplest real organism = a **virus**:
a minimal genome, a body that **infects/consumes** its environment, replicates when fed, is traced out when
starved — no full metabolism, no bath dissipation.

**The Weismann barrier here is ASYMMETRIC, not total disconnection (faithfulness point).** A real germ/soma
split is *directional*: **germ→soma expression flows** (the genome builds and runs the body — the paper:
*"the phenotype is determined by the genetic information"*), but **soma→germ back-action is forbidden** (the
body's fate never rewrites the genes). PJ2 implements exactly this:
- **Expression (germ→soma) is present and required** — the body is built from the **classical genes** via
  **diagonal (Z-basis) controls**. This is faithful, not a cheat: the paper's own model says the gene→body
  information (lifetime, predator-prey role) **is classical**, encoded in ⟨σz⟩ — so classical/diagonal
  expression is the correct level. The organism is genuinely *of* its genome.
- **Back-action (soma→germ) is forbidden** — no coherent gate lets the walking / starving / dying body write
  decoherence into the **witness loci**. That, and only that, is what keeps the `⟨X^⊗W⟩` heredity clean.
The quantum content was never in the within-individual gene→body link (classical in the paper too); it lives in
the **cross-generation genealogical entanglement**. Total germ⊥soma disjointness (the naive reading of PJ0's
"Static Test 1") would make the body a *separate thing*; PJ2's barrier is the asymmetric, faithful one.

**The habitat (the space to live in).** A `track`-site **unary** lattice (the environment) seeded with a few
**resource/food** excitations. The body **walks** (excitation-conserving `rxx+ryy` quantum walk, hop rate set
by a genotype motility bit) and, **on co-location with a food site**, **consumes** it — a coherent exchange
that empties the host site and raises the body's **energy** register. Consumption is **emergent from
co-location** (the coupling is always present at shared sites, only acts where the body has amplitude —
**never `if(contact)`**), exactly PJ1's "as-if-alive" principle.

**Emergence principle (the "alive, not on rails" discipline — developer-directed).** The organism's *behavior*
is **not scripted**; only **local physical laws** are. The whole life cycle is a **Trotterized evolution under
one fixed local "vivarium Hamiltonian"** `H_viv = H_forage + H_eat + H_starve + H_bud`, applied `steps` times
from the seeded habitat. Nothing tells the body where to go, what to eat, whether to survive, or whether to
reproduce — those all **emerge** from evolving `H_viv`. There is **no `if`/measurement branch on the body path**
(verified statically, AC-PJ2.4), exactly the standard PJ1 already met (contact entropy rose only on overlap,
never coded). The certified germ genealogy rides *above* this dynamics, kept clean by the Weismann barrier.
Honest ceiling: on a fixed one-circuit unitary the *laws* are always coded — "emergent" means behavior arises
from the dynamics, never from a scripted move or a classical branch; open-ended novelty / true autonomy (the
paper's far goal: *"evolution will be an intrinsic property… behavior will emerge without following the
instructions of a previously designed algorithm"*) is **not** claimed here.

**Survival of the fittest — emergent from physics, not an imposed threshold (one circuit, no mid-circuit
measure).** Selection is **not** a bolted-on fitness function. It emerges from three fixed laws in `H_viv`,
all diagonal / phenotype-side so the Weismann barrier holds and the witness survives:
- **Forage (state-dependent motility, `H_forage`):** the body's **energy** qubit *controls the hop angle* — an
  un-fed body hops (searches), a fed body rests. Foraging emerges from one coupling, not a route script.
- **Eat (`H_eat`):** the co-location exchange (emergent, above) empties food into the energy register.
- **Starvation death (`H_starve`):** an un-energized soma **relaxes toward `|0⟩`** under the aging/idle law
  (the paper's *"exploit natural decoherence… trace out dead living units"*) — a body dies because it failed to
  eat, not because a comparator culled it.
- **Budding (`H_bud`):** a fed body's **own energy excitation powers** a soma-replication into a neighbor site —
  reproduction is a *physical consequence of having eaten*, gated by the body's energy (phenotype), never by an
  imposed rule.
So who forages well eats, eaters persist and bud, starvers fade — **survival of the fittest as an emergent
property**. The old static `energy ≥ θ_fit` comparator is **not** the default; it is relegated to an optional
`--hard-select` arm for contrast (and remains the witness-safe, mid-circuit-measure-free fallback). The
`--gate-repl` variant (germ clone powered by the body's energy, coupling germ↔soma) stays the **measured
richness datapoint**: how much genuine physical selection costs the witness (R1, CD-4).

**Three arms (the science A/B):**
1. **`barren`** (control) — habitat seeded with **no food** (consumption coupling absent). The body walks,
   nothing to eat, selection is neutral → baseline witness, baseline alive-count. Proves any effect below is
   *caused* by the resources.
2. **`vivarium`** (the result) — habitat seeded with food; the organism evolves under the fixed `H_viv`:
   it **forages** (energy-gated hopping), **eats** on co-location, **starves** toward `|0⟩` if it doesn't, and
   **buds** when fed. Survival of the fittest is an **emergent** outcome of these laws + the seeded habitat, not
   a scripted cull. The certified germ witness must survive the added life-cycle depth (measure how much it
   costs); the diagonal story (where it went, who ate, who starved, who budded, food remaining) is honest
   plumbing.
3. **`germ_coupled`** (A/B kill-switch) — the same consumption/selection coupling **routed through a germ
   qubit** (breaks the Weismann barrier). The witness **collapses**. Proves the barrier is the mechanism,
   cross-checking PJ0/PJ1 in the single-organism vivarium.

**Certified quantum claim (CD-3):** the genealogical witness `⟨X^⊗W⟩` over the germ line vs the separable null
`∏⟨X⟩_i ≈ 0`. **Everything else is diagonal, classical narrative** with an exact measure-and-resend surrogate:
body occupancy (Z), energy/fitness, alive-count, food remaining, trait bits. Only the germ witness carries the
quantum claim — no speedup, ever (CD-4).

**Headline output (locked):** the **solo-vivarium spectacle** — a single-organism wave-bars view (extending
`pj1Concepts/4_wave-bars_PICKED.html`): one body walking a habitat with food sites, an **energy/fitness meter**
filling as it eats, an **alive/selected** indicator, the genome **trait chips**, food sites winking out on
consumption, and the **genealogy witness meter** (green survives / red collapse) — **reconstructed from the
statevector snapshots of the one measured circuit**, with the terminal certified numbers overlaid; plus the
3-arm witness contrast as the science figure.

---

## 2. Acceptance criteria

Grounded in `P3-candidate-movess.md` (rung 5 differential reproduction, M5 QRNG biology, M6 quantum-random
environment, PM1/PM3), the 2018 Discussion roadmap (§1 quotes), and the PJ0/PJ1 substrate. IDs added. All
hardware ACs enforce the fail-closed chain-quality gate (CD-5) and certified QRNG (CD-6). No tests (CD-7).

- [x] **AC-PJ2.1 (enriched-organism substrate — "meat on the bone", PM1):** a **vivarium builder**
  `build_vivarium(...)` in `code/pj_qalife.py` places **one** organism whose **genome has two co-inherited
  parts** — the **witness loci** `witness_q` (the clean W-individual GHZ germ line, reusing PJ0
  `geno_q`/`witness_qubits`, byte-stable) and a **classical-gene register** `gene_q` (diagonal trait bits
  `t_repl`, `t_life`, `t_role`, copied down the lineage) — plus a **soma body** (unary walker on a `track`-site
  habitat) + an **energy** register (+ one **fitness ancilla** only under `--hard-select`). `--selftest` green
  on the new static vivarium checks (§6.1). `build_germsoma` / `build_arena` untouched.
- [x] **AC-PJ2.1b (germ→soma expression is PRESENT — the organism is one thing):** the body is **expressed
  from the classical genes** — at least the motility gene `t_role` drives the body's hop (a diagonal control),
  and `t_repl`/`t_life` are displayed heredity. Static check (positive): `vivarium_coupling_report` reports
  `expression=True` (≥1 gate reads a `gene_q` qubit to set a soma/body qubit). A build with **no** gene→soma
  link is a failure — that would be two disjoint things, not an organism. This is the germ→soma direction of the
  asymmetric Weismann barrier.
- [x] **AC-PJ2.2 (the habitat / spatial variable — M6/PM3, paper "spatial variables"):** the builder seeds a
  parameterizable set of **food** excitations on the habitat lattice (`--food` sites, QRNG-chosen positions,
  CD-6 provenance) and initializes the body localized at a start site. In the `barren` arm the habitat carries
  **no food**; in `vivarium`/`germ_coupled` it carries the seeded food. Reported: initial food layout in
  `meta`.
- [x] **AC-PJ2.3 (one circuit, no frames — the defining lock):** the **entire** life cycle (germ genealogy →
  body walk over `steps` hops → consumption → static-ancilla selection) is built into **one** circuit to a
  terminal time `T` and **measured once**. The driver performs **no per-frame job sweep**. The trajectory for
  the demo is a **statevector snapshot at each internal `barrier`** of the *same* circuit (sim-only, labelled).
  Verified by `--dump-circuit` (single measured circuit) + the driver banking exactly one HW measurement per
  arm/repeat.
- [x] **AC-PJ2.4 (viral consumption is emergent, not coded — PJ1 principle):** the body **consumes** a food
  site by a coherent operator applied at the shared habitat sites with **no classical branch** on contact
  (no `c_if`/measurement-conditioned gate on the body/food path). Static check: consumption gates are present
  **unconditionally**; and the `barren` arm — identical minus the food + consumption layer — yields **energy ≈ 0
  / no consumption** while `vivarium` yields energy > 0 **only where the body meets food** (sim, statevector).
  This pair is the "emergent, not `if(ate)`" evidence.
- [x] **AC-PJ2.5 (survival of the fittest — EMERGENT from fixed laws, not an imposed threshold; rung 5, no
  mid-circuit measure):** selection is produced by the fixed `H_viv` laws, **not** a bolted-on comparator.
  Build **`H_starve`** (an un-energized soma relaxes toward `|0⟩` under the aging/idle law — a `cry`/`rx`
  toward the dark state controlled by *absence* of energy) and **`H_bud`** (a fed body's own energy excitation
  drives a soma-replication into a neighbor site — a controlled operation whose **control is the body's energy
  qubit**, phenotype-side). Both act on **soma/energy qubits only — never a witness locus** (the soma→germ
  back-action ban; gene→soma expression is separately allowed, AC-PJ2.1b). No mid-circuit measurement, no
  feed-forward, no `if`. Result: eaters persist + bud, starvers fade — survival of the fittest **emerges**. The
  static `energy ≥ θ_fit` comparator is **not** default; it is an optional `--hard-select` arm (witness-safe
  contrast). Reported: alive-count / population / survivors (all diagonal, classically surrogate-able, CD-4).
  - **`--gate-repl` (opt-in, the measured richness datapoint):** route budding through the **witness-locus
    clone** (witness↔energy coupling) so real physical selection touches the genealogy — deliberately breaking
    the soma→germ ban; report the **witness cost** vs the default soma-only budding (R1, AC-PJ2.7).
- [x] **AC-PJ2.6 (genotype-encoded + state-dependent motility — paper "capacity to displace", PM1):** the hop
  angle is set by **two** emergent inputs, not a script: (a) the genotype **motility** trait `t_role` (the
  genome *means something for behavior*, inherited down the germ line), and (b) the body's **energy** qubit
  (state-dependent foraging — hungry hops, fed rests, `H_forage`). Both are diagonal controls on the walk
  angle. `t_repl`/`t_life` are carried down the germ line (diagonal heredity) and **displayed as organism
  properties**. Static check: the trait/energy controls are diagonal-only and never enter the X-basis witness
  set; the walk law is applied unconditionally (no `if` on position).
- [x] **AC-PJ2.7 (certified witness survives the added biology — THE quantum result, CD-3/CD-5):** with the
  full life cycle in one circuit (`vivarium`), report `⟨X^⊗W⟩` vs the **separable null** (pinned ≈0) from sim
  and a small HW confirm; gate `witness − sep > k·σ` (k=2 headline, k=3 reported). Report the **W (and food/
  step budget) at which the signature crosses into classical** — the **richness-vs-collapse datapoint** this
  ticket contributes to the P4 phase diagram (AC-P3.2). Honest framing: if the added depth kills the witness at
  small W, that boundary **is** the result.
- [x] **AC-PJ2.8 (A/B kill-switch — the barrier mechanism):** the `germ_coupled` arm re-routes the
  consumption/selection coupling through a **witness locus** (a coherent soma→witness back-action — the exact
  ban broken on purpose); static check shows `back_action=True`, and the measured witness **collapses** relative
  to `vivarium` at matched settings. Confirms the *asymmetric* Weismann barrier (expression yes, back-action no)
  is what protects the genealogy under the richer biology (PJ0/PJ1 cross-check).
- [x] **AC-PJ2.9 (honest diagonal plumbing, CD-3/CD-4):** body occupancy, energy, fitness, alive-count, food
  remaining, and the trait bits are shown to be **diagonal** (exact classical surrogate); only the germ witness
  is the quantum claim; the separable null is reported alongside the witness and must sit ≈0. The vivarium
  banks the diagonal story as narrative, not as a quantum claim.
- [x] **AC-PJ2.10 (selective DD on the germ line — Weismann barrier, HW):** the HW path schedules selective DD
  (`[X,X]`) on the **germ-line physical qubits only** (reusing PJ0's pass sense), body/habitat/energy DD-free.
  Verified by inspecting the scheduled circuit (static).
- [x] **AC-PJ2.11 (the locked spectacle — one-run reconstruction):** `analysis/pj_vivarium_render.py` reads a
  banked PJ2 run JSON and emits a **self-contained** single-organism vivarium web demo (extension of
  `pj1Concepts/4_wave-bars_PICKED.html`): body position bars + ψ-envelope + habitat food sites (winking out on
  consumption) + **energy/fitness meter** + **alive/selected** indicator + genome **trait chips** + the live
  **genealogy witness meter** (green/red) + arm toggle + plain-language caption. The animation frames come from
  the **sim statevector snapshots**; the **terminal certified numbers** (measured) are overlaid as the "final
  state." CSP-safe (all inline, no external fetch), no sideways body scroll, works from `file://`;
  `research/pj2_vivarium/index.html`.
- [x] **AC-PJ2.12 (live run banked, CD-6/CD-7):** a live Heron-r2 run at the chosen W (W12/track6 default) for
  the three arms, QRNG-certified fail-closed (angles + food positions + hop schedule), chain-quality gate
  enforced; **one measured circuit per arm/repeat** (no frame sweep); banked to `research_runs/pj2/`. PJ0/PJ1
  paths remain byte-stable (`build_germsoma`/`build_arena` unedited; `pj_run_qalife.py`/`pj1_run_arena.py`
  unedited). *Code complete; the developer executes the hardware run* (established division of labour).

---

## 3. Out of scope

- **More than one organism (L>1) / colliding lineages.** PJ2 is **single-organism** (that is the whole point:
  "meat on one bone"). Multi-organism competition is PJ1 (already built) / later rungs.
- **Amplitude-damping / bath death channel.** Death here is **trace-out of a starved/aged soma** (paper's
  "mechanism for tracing out death living units") — an idled qubit read as a marginal — **no bath, no
  dissipation** (P3-candidate §PJ principle: all witness loss is real, EM-fightable). The `local_damping`
  option is not used.
- **Mid-circuit measurement / feed-forward selection.** Selection is **static** (a diagonal fitness ancilla).
  Adaptive measured culling (`death_mode='selection'`, epic §9 P3) is a *separate* future move and is
  deliberately avoided (it collapses the superposition and is the dominant Heron error, I9 rationale).
- **A per-frame HW movie.** Explicitly rejected by the developer lock — **one run, not frames** (AC-PJ2.3).
  The movie is sim-reconstructed.
- **Teleport / long-range routing (I9 — DEAD).** The body walks a contiguous habitat on
  `layout.best_chain`; consumption is short/co-located only.
- **Qudit / higher-dimensional genome** (paper's alternative "encode in higher dimensions") — parked, wrong
  platform (P3-candidate PM4).
- **Any change to `qalife.py` / `run_qalife.py`** (faithful reproduction, byte-stable) and to PJ0/PJ1 builds
  (`build_germsoma`, `build_arena`, `pj_run_qalife.py`, `pj1_run_arena.py`). PJ2 adds new functions + a new
  driver only.

---

## 4. Cross-cutting decisions applied (epic §3 + PJ0/PJ1 §4)

- **CD-1 (main-folder minimalism) — PJ pair, in place.** PJ2 **extends** `code/pj_qalife.py` (the shared model,
  the substrate PJ0/PJ1 already extend) with `build_vivarium` + vivarium analyzers + `--selftest` checks, and
  adds a **new driver** `code/pj_vivarium.py`. **No edit** to the faithful reproduction or to PJ0/PJ1 builds.
  `pj_qalife.py` keeps importing `qalife as q4` read-only. Analysis/render goes in `analysis/`.
- **CD-3 (witness is the only quantum claim).** PJ2's sole quantum observable is `⟨X^⊗W⟩` over the germ line.
  Occupancy, energy, fitness, alive-count, food, traits are declared classical; the separable null is reported
  alongside and must sit ≈0.
- **CD-4 (honesty invariant).** The viral biology (consumption, fitness, selection, motility, aging/trace-out
  death) is **diagonal** → exact classical surrogate → reported as plumbing/narrative. Only the germ witness
  surviving the added life-cycle depth is quantum content. The richness datapoint = the W/food/step budget where
  the witness dies (CD-8 "noise is not a fitness function"): every added process is explicit and entropy-honest,
  never noise dressed as biology.
- **CD-5 (significance + chain-quality gates).** `entanglement_depth` (k=2 headline, k=3 reported); σ from
  `--repeats` + shot-noise in quadrature; fail-closed chain-quality gate (reuse `gated_chain`).
- **CD-6 (QRNG certified, fail-closed).** Mutation angles **and** the environment's stochastic parameters —
  **food positions** and the **hop schedule** (M5/M6: a *provenance* claim, fixed per circuit, not per shot) —
  come from `qrng_client.py`; fail-closed on hardware. `MUT_SCALE=0` faithful default (clean GHZ) so the
  vivarium's effect on the witness is isolated.
- **CD-7 (sim-first, hardware-confirm; verification without a test framework).** `--sim` + `--selftest` +
  `--dump-circuit` + written conclusion; then the live confirm. No test framework.
- **CD-8/CD-11 (biology is measured, not noise; EM is a lever).** Consumption/selection are explicit coherent/
  diagonal operators, never a bath. All witness loss is real hardware noise, so selective DD (AC-PJ2.10) is
  allowed to fight it. The witness-vs-richness boundary is the measured deliverable.

---

## 5. Verified codebase facts (grounding the plan)

From the substrate surveys (PJ0/PJ1, current tree):

- **Germ/soma model `code/pj_qalife.py`:** `build_germsoma` (`:114`, PJ0, loops `for o in range(organisms)`);
  `build_arena` (`:566`, PJ1, adjacent tiling `arena_base` `:502`, `_walk_layer` `:527` = NN `rxx+ryy`,
  `_collision_layer` `:539` with arms `none|soma_soma|germ_routed`). **PJ2 reuses `_walk_layer` for the body's
  habitat walk.** Layout index helpers (organism-offset) `:77–99`; witness helpers
  `witness_qubits(width, organisms=1, has_bath=False)` (`:208`, returns germ qubits),
  `to_witness_basis(qc, width, *, phenotype, soma_death, organisms=1)` (`:190`, H on germ only),
  `germsoma_coupling_report` (`:245`, `disjoint`/`gene_first`), `arena_coupling_report` (`:654`,
  per-organism Static Test 1 + `has_classical_branch`), `run_arena_selftest` (`:781`). Gates in use:
  `ry/cx/cry/rxx/ryy/x/barrier` — **`ccx`/`mcx` for the static fitness comparator will be added.**
- **Witness math `qalife.py` (read-only):** `xbasis_witness_from_counts(counts, qubits) -> (joint, sep)`
  (`:217`) over an arbitrary qubit list; `entanglement_depth(...)` (`:239`); `classical_surrogate_z(...)`
  (`:251`); `phenotype_z_from_counts` (`:181`). Constants `AGING_DELTA=π/8`, `ALIVE_THRESH=0.80`.
- **PJ0 driver `pj_run_qalife.py`:** `build_measured_germsoma` (`:122`, H germ only + measure),
  `qrng_thetas(client, width, mut_scale, repeat)` (`:104`, fail-closed),
  `schedule_with_selective_dd(qc, backend, width, *, soma_death)` (`:163`, opt-3 preset PM +
  DD on `germ_physical = witness_qubits(width, has_bath)` only), `gated_chain(backend, nq)` (`:243`),
  globals `INTERACTION/REPEATS/K/MUT_SCALE/SOMA_DEATH/PHENOTYPE/SELECTIVE_DD` + thresholds
  `MAX_TWOQ_ERR=0.05`/`MAX_READOUT_ERR=0.15`. **Sim vs HW = `args.backend is None`.** Output → `research_runs/`.
- **PJ1 driver `pj1_run_arena.py` (the closest template):** `build_measured_arena` (`:83`, H germ only + bodies
  in Z, one circuit), `reduce_frame` (`:107`, joint/sep/per-lineage witness + `witness_cut_AB` + occupancy),
  `contact_entropy_sim` (`:147`, statevector S(ρ)), `scan_coupling` (`:258`),
  `schedule_arena_selective_dd` (`:172`, DD on both germ lines), imports PJ0 infra by name
  (`from pj_run_qalife import gated_chain, qrng_thetas, ...`), statevector Aer sim (`_SV_MAX_QUBITS=26`),
  inline run-schema dict in `main()`, banks to `research_runs/pj1/`. **PJ2's driver mirrors this file.**
- **Renderer template:** `analysis/pj1_render.py` (`:46` `build_data` maps frames→`{a,b,s,ov,w}`, `:76`
  `render_html` swaps the `const DATA=` literal in a port of `pj1Concepts/4_wave-bars_PICKED.html`, `:101`
  witness PNG). `analysis/plot_baseline.py` = the degrade-gracefully matplotlib-Agg pattern. **PJ2's renderer
  mirrors `pj1_render.py`.**
- **Layout / QRNG:** `best_chain(backend, n, time_budget=40.0)` (`layout.py:54`, raises on no clean n-chain);
  `QRNGClient.fetch/health` (`qrng_client.py:84/59`, raise `QRNGUnavailable`).
- **Spectacle precedent for "sim movie, one real endpoint":** `pj1_spectacle.py` already reconstructs a
  smooth multi-frame animation from a **cheap classical/statevector sim** and labels the extra frames a
  "simulation artifact" — PJ2 reuses this pattern deliberately (one measured circuit, sim-reconstructed movie).

---

## 6. File plan

One file **extended** in place (`pj_qalife.py`, the shared model) + **two new files** (`pj_vivarium.py`
driver, `analysis/pj_vivarium_render.py`) + one new research dir + one new run dir. All new code: strict-typed,
PEP-8, `from __future__ import annotations`, mirroring `pj_qalife.py`/`pj1_run_arena.py` style. `qalife.py`,
`run_qalife.py`, `pj_run_qalife.py`, `pj1_run_arena.py` are **not edited**; `build_germsoma`/`build_arena`
byte-stable.

### 6.1 Extend — `code/pj_qalife.py` (vivarium model + vivarium `--selftest`)

Add PJ2 alongside PJ0/PJ1. New code reuses `geno_q`/`witness_qubits` for the germ block and `_walk_layer` for
the habitat walk.

- **Vivarium layout (new, single organism, unary habitat):** index helpers, contiguous SWAP-free order:
  - `viv_segment_len(width, track, energy, traits, *, hard_select=False) -> int` = `width` (germ) `+ track`
    (body) `+ track` (food lattice) `+ energy` `+ traits` `+ (1 if hard_select else 0)` (fitness ancilla only
    under `--hard-select`). Default at W12/track6 = 30.
  - `viv_witness_q(k, ...)` (the witness loci = germ line, alias of the PJ0 `geno_q` sense),
    `viv_body_q(j, ...)` (unary body site `j`), `viv_energy_q(e, ...)` (unary energy accumulator),
    `viv_gene_q(t, ...)` (`t ∈ {repl, life, role}` — the **classical-gene** register read to express the body),
    `viv_fit_q(...)` (the static fitness ancilla, only under `--hard-select`). Food occupies a **track-length
    lattice** `viv_food_q(j, ...)` (unary, seeded sites `|1⟩`) — OQ-2 (unary default).
- **`build_vivarium(width, steps, thetas, *, track=6, food=(2,4), energy=3, traits=3,
  interaction='vivarium', hop=DEFAULT_HOP, consume=DEFAULT_CONSUME, theta_fit=1, founder_equator=True,
  select=True, annotate=False) -> QuantumCircuit`** — phased build, **all in one circuit**:
  1. **Germ line first** (rung-0 discipline): founder `ry(π/2)` + NN `cx` clone chain + `ry(thetas[k])`
     mutation on the contiguous germ block. Barrier `"germline"`. (Heredity + witness — unchanged from PJ0.)
  2. **Genome + expression (germ→soma, AC-PJ2.1b):** set the diagonal classical genes `t_repl/t_life/t_role`
     on `viv_gene_q` (from `thetas`/QRNG or fixed) and copy them by CX so they are inherited alongside the
     witness loci. Then **express the body from the genes**: a diagonal `viv_gene_q(role)`-controlled setup of
     the body's motility (and any other gene→body links) — the germ→soma direction. Controls are gene qubits
     (Z-basis), targets are soma qubits; **no witness locus is a target/control here**, so the witness stays
     clean. Barrier `"genome"`.
  3. **Habitat seed:** `x` the body at its start site; `x` the QRNG-chosen **food** sites (`barren` arm seeds
     **no** food). Barrier `"habitat"`.
  4. **Life cycle = Trotterized `H_viv` (the one-circuit trajectory, emergent behavior):** repeat `steps`
     times, each iteration a **`barrier`** (the sim snapshot point, AC-PJ2.3). Each iteration applies the fixed
     local laws — nothing is scripted per-site:
     - **`H_forage` (walk):** `_walk_layer` NN `rxx(hop)+ryy(hop)` on the body register, `hop` set by **`t_role`
       (genotype motility)** AND **controlled by the energy qubit** (hungry hops, fed rests, AC-PJ2.6) —
       diagonal controls on the angle. Applied unconditionally (no `if` on position).
     - **`H_eat` (consume):** where a body site aligns with a food site, a coherent `rxx(consume)+ryy(consume)`
       exchange empties the food site into the **energy** register (unary increment) — **body/food/energy only,
       no germ qubit** (`vivarium`); for `germ_coupled` it routes through `viv_germ_q(0)` (the A/B wound).
       `barren`: no food seeded → the same law is present but never fires (emergence, not a code branch).
     - **`H_starve` (death):** an energy-*absent*-controlled `cry`/`rx` relaxing the soma toward `|0⟩` (natural
       decoherence / trace-out of the un-fed — paper's mechanism). Phenotype-side only.
     - **`H_bud` (reproduction):** an energy-*present*-controlled soma-replication into a neighbor body site
       (a fed body's excitation powers budding). Control = the body's energy qubit (phenotype); **no germ
       qubit** by default. `--gate-repl` instead controls the **germ clone** (the measured-cost variant).
  5. **No imposed selection step by default.** Survival of the fittest is already produced by
     `H_forage`+`H_eat`+`H_starve`+`H_bud` above (AC-PJ2.5). `--hard-select` optionally appends a **static**
     `energy ≥ θ_fit` comparator (CX/MCX + `viv_fit_q`, diagonal, no measurement) as a contrast arm.
     Barrier `"select"` only when `--hard-select`.
  6. No bath, no damping. Death is emergent (`H_starve` relaxation) + trace-out of the idle soma at readout.
- **Static analyzers (build-time, no execution):**
  - `viv_witness_qubits(width, ...) -> list[int]` → germ qubits (the witness set; reuse `witness_qubits`).
  - `viv_body_site_qubits(...)`, `viv_energy_qubits(...)`, `viv_food_qubits(...)`, `viv_trait_qubits(...)` →
    the Z-basis diagonal readout sets.
  - `vivarium_coupling_report(qc, width, track, food, energy, traits) -> dict` — walks `qc.data`; encodes the
    **asymmetric** Weismann barrier and returns:
    - `expression` (**True** required — ≥1 gate reads a `gene_q` classical-gene qubit to set a soma/body qubit;
      the germ→soma direction, AC-PJ2.1b — a build without it is two disjoint things, a failure),
    - `back_action` (**False** required in `vivarium`/`barren`; **True** in `germ_coupled` — any coherent gate
      coupling a **witness locus** to a soma/food/energy qubit; the forbidden soma→germ direction, AC-PJ2.8),
    - `witness_isolated` (the witness loci appear only in founder/clone/mutation/gene-copy gates + the terminal
      H+measure — never paired with a soma/energy/food qubit),
    - `gene_first` (germ gates precede the life cycle),
    - `selection_diagonal` (the emergent selection laws + any `--hard-select` comparator touch only Z-basis
      soma/energy qubits + the ancilla, never a witness locus),
    - `has_classical_branch` (must be **False** — no `c_if`/measurement-conditioned gate, AC-PJ2.4),
    - gate counts.
- **Extend `--selftest`** with vivarium checks at representative `(W, track)` (e.g. W2/track5, W4/track6,
  W12/track6): (i) **asymmetric barrier** — `expression=True` AND `back_action=False` for `barren`/`vivarium`,
  and `back_action=True` for `germ_coupled` (the A/B); (ii) `witness_isolated=True` (witness loci never paired
  with a soma qubit) in `barren`/`vivarium`; (iii) germ-first ordering; (iv) witness readout isolation (H on
  witness loci only; body/energy/food/genes in Z); (v) **no classical branch** on the body/selection path
  (AC-PJ2.4); (vi) selection laws are **diagonal** and touch no witness locus (AC-PJ2.5); (vii) `barren` build
  == `vivarium` build **minus** the food seed + `H_eat` layer (structural diff). Print per-check `OK` +
  `SELFTEST PASS`.
- **Extend `main()`** with vivarium flags: `--vivarium` (switch to vivarium build), `--track`, `--food`,
  `--energy`, `--traits`, `--interaction {barren|vivarium|germ_coupled}`, `--hard-select` (append the optional
  static comparator arm), `--gate-repl` (route budding through the germ clone — the measured-cost variant).
  Default (no `--vivarium`/`--arena`) = the existing PJ0 static CLI, unchanged.

### 6.2 New — `code/pj_vivarium.py` (the vivarium driver — build + sim + one live run)

Mirror `pj1_run_arena.py`. Imports `pj_qalife as pj`, `qalife as q4`, and **reuses PJ0/PJ1 infra by import**
(`from pj_run_qalife import gated_chain, qrng_thetas, OUTPUT_DIR`; selective-DD reused/adapted for the germ set),
**no edit** to `pj_run_qalife.py`/`pj1_run_arena.py`.

- **Globals:** `TRACK=6`, `FOOD=(2,4)`, `ENERGY=3`, `TRAITS=3`, `STEPS_HW` (few — one run, save QC), `HOP`,
  `CONSUME`, `THETA_FIT=1`, `ARMS=("barren","vivarium","germ_coupled")`, reuse chain thresholds + `SELECTIVE_DD`.
- **`build_measured_vivarium(width, steps, thetas, *, interaction, ...) -> QuantumCircuit`** — call
  `pj.build_vivarium(...)`, then **H on germ qubits only** (X witness), **body/energy/food/traits/fitness left
  in Z** (diagonal readout); add `ClassicalRegister`; measure all → **one circuit** yields witness (germ) +
  the whole diagonal story (occupancy, energy, alive/fit, food-remaining).
- **Count reductions:** `witness_joint` + `separable_null` via
  `q4.xbasis_witness_from_counts(counts, pj.viv_witness_qubits(...))`; occupancy = P(body site) marginals;
  energy/fitness/alive = marginals of the diagonal registers; food-remaining = marginals of the food register.
- **One-run + sim-snapshot movie (AC-PJ2.3):** HW = **one measured circuit per arm/repeat** (no frame sweep).
  Sim = a `Statevector` evolved through the identical circuit, snapshotting at each internal `barrier` to build
  the animation frames + the sim-only energy/witness trajectory (capped at `_SV_MAX_QUBITS`, reuse PJ1's cap).
- **QRNG (CD-6):** `qrng_thetas` for mutation angles + a QRNG draw for **food positions** and the **per-step hop
  schedule** (fixed per circuit); fail-closed on HW.
- **Selective DD (AC-PJ2.10):** schedule `[X,X]` on the germ physical qubits only (reuse PJ0's pass sense; if
  the internal target-derivation can't address the vivarium layout, re-implement a `schedule_vivarium_selective_dd`
  targeting `viv_witness_qubits` — the same forced deviation PJ1 documented, not an edit to PJ0).
- **Run schema (inline dict, mirror PJ1):** `meta.stage="PJ2"`, `meta.model="germsoma_vivarium"`, +
  `meta.track/food/energy/traits/hop/consume/theta_fit/steps/arms/select`; per-arm banked block
  `{witness_joint_mean, witness_joint_sigma, separable_mean, entanglement_signal, survives, occupancy,
  energy, alive_selected, food_remaining, sim_frames:[{t, body, food, energy, fit, witness_sim}]}` — the
  `sim_frames` array is **exactly what the renderer consumes**. Bank to `research_runs/pj2/`.
- **CLI (own `main()`):** `--backend` (None=sim), `--width` (default 12), `--track` (default 6), `--food`,
  `--energy`, `--traits`, `--interaction` (default: run all three arms), `--steps`, `--shots`, `--hard-select`
  (optional static-comparator contrast arm), `--gate-repl` (germ-coupled budding, measured-cost variant),
  `--dump-circuit`/`--draw-only`, `--name` (default `pj2_vivarium`). No `--vivarium` flag needed — this file
  **is** the vivarium driver.

### 6.3 New — `analysis/pj_vivarium_render.py` (the locked solo-vivarium spectacle)

Mirror `analysis/pj1_render.py` (path shim, `main() -> int`, degrade-gracefully). Reads a banked
`research_runs/pj2/*.json`, extracts each arm's `sim_frames` (the movie) + the terminal measured numbers, and
writes a **self-contained** `research/pj2_vivarium/index.html` — a port of
`pj1Concepts/4_wave-bars_PICKED.html` reduced to **one organism** and augmented with: **food sites** on the
habitat (winking out on consumption), an **energy/fitness bar**, an **alive/selected** indicator, the genome
**trait chips**, the **genealogy witness meter** (green survives / red collapse), and an arm toggle. The demo's
frames are the **sim snapshots**; the **terminal certified numbers** are overlaid as the measured "final state."
CSP-safe (all inline, no external fetch/CDN), body never scrolls sideways, works from `file://`. Also emit a
static 3-arm witness PNG (matplotlib Agg) `research/pj2_vivarium/pj2_witness_3arm.png`. CLI: `--run-glob`,
`--out-dir` (default `research/pj2_vivarium`).

### 6.4 New — `research/pj2_vivarium/` (banked result + demo + conclusion)

- `index.html` — the rendered solo-vivarium spectacle (sim frames + measured endpoint).
- `pj2_witness_3arm.png` — the 3-arm witness figure.
- `circuits/*.txt` — printed vivarium circuits (`--dump-circuit`) per arm at representative `(W, track, food)`.
- `CORRECTNESS.md` — static-correctness argument (Static Test 1, no-`if(ate)` proof, diagonal-selection proof,
  germ_coupled A/B contrast, selective-DD on the germ line) with `--selftest` output.
- `CONCLUSION.html` — results writeup (mirrors `PJ0_CONCLUSION.html`/`pj1_arena/CONCLUSION.html`): the three
  arms, witness-vs-null under the added biology (the richness datapoint), the A/B collapse, the diagonal life
  story, honest framing (scale·faithfulness·certification, not a speedup).

### 6.5 Resulting layout (after PJ2)

```
code/
  layout.py  qrng_client.py            # infra (unchanged)
  qalife.py  run_qalife.py             # faithful reproduction (UNCHANGED)
  pj_qalife.py                         # EXTENDED — + build_vivarium, vivarium layout/analysis, --selftest
  pj_run_qalife.py                     # UNCHANGED — PJ0 driver
  pj1_run_arena.py                     # UNCHANGED — PJ1 arena driver
  pj_vivarium.py                       # NEW — vivarium driver: build_measured_vivarium, one-run + sim movie, PJ2 schema
analysis/
  plot_baseline.py  pj1_render.py      # (unchanged)
  pj_vivarium_render.py                # NEW — banked data -> solo-vivarium spectacle + 3-arm PNG
research/
  pj0_germsoma/ ... pj1_arena/ ...     # (unchanged)
  pj2_vivarium/                        # NEW — index.html, pj2_witness_3arm.png, circuits/, CORRECTNESS.md, CONCLUSION.html
research_runs/
  pj/ ... pj1/ ...                     # (unchanged)
  pj2/                                 # NEW — PJ2 vivarium run JSON
```

---

## 7. Implementation steps

1. **Vivarium layout + `build_vivarium` (rungs 0+5 core, one circuit)** — new index helpers; germ line +
   genome trait bits + unary habitat/body + energy register + fitness ancilla; germ-first, then the
   walk/consume life cycle with a `barrier` per step, then static selection; three `interaction` arms.
   `pj_qalife.py`; `build_germsoma`/`build_arena` untouched. Reuse `_walk_layer`.
2. **Vivarium static analyzers** — `viv_witness_qubits`, the diagonal readout-set helpers,
   `vivarium_coupling_report` (Static Test 1 + diagonal-selection + no-`if(ate)` check).
3. **Extend `--selftest`** — the six vivarium checks (§6.1) at W{2,4,12}. Iterate to `SELFTEST PASS`.
4. **Vivarium `main()` static CLI** — `--vivarium --dump-circuit` prints the one circuit + report per arm.
5. **New `code/pj_vivarium.py`: `build_measured_vivarium` + count reductions** — H germ only + diagonal
   registers in Z; witness/null + occupancy/energy/fit/food from one circuit. Imports PJ0/PJ1 infra by name.
6. **Sim path + one-run snapshot movie** — `--sim` builds one circuit, `Statevector` snapshots at each barrier
   → `sim_frames`; sim-only energy/witness trajectory; verify `barren` energy≈0, `vivarium` energy>0 on
   contact, `germ_coupled` witness collapses.
7. **HW path (one run, no frames)** — selective DD on the germ line (AC-PJ2.10); `gated_chain` + QRNG (angles +
   food + hop schedule) fail-closed; **one measured circuit per arm/repeat**; schema to `research_runs/pj2/`.
8. **`analysis/pj_vivarium_render.py`** — port the picked wave-bars HTML to one organism + food/energy/fitness/
   trait/witness widgets; inject sim frames + measured endpoint → self-contained `research/pj2_vivarium/index.html`;
   3-arm witness PNG.
9. **Live W12/track6 run + bank** — three arms on least-busy Heron-r2 (developer); render the demo from the
   live JSON; write `CORRECTNESS.md` + `CONCLUSION.html`.

---

## 8. Manual verification (no tests; static + sim + one live run — CD-7)

- `python code/pj_qalife.py --vivarium --selftest` → six vivarium checks `OK` at W{2,4,12}, `SELFTEST PASS`,
  exit 0. Also `python code/pj_qalife.py --selftest` (PJ0) and `--arena --selftest` (PJ1) still pass
  (byte-stable).
- `python code/pj_qalife.py --vivarium --width 12 --track 6 --interaction vivarium --dump-circuit`
  → **one** measured-free build; `expression=True` (a gene→body gate is present — the organism is one thing),
  `back_action=False` + `witness_isolated=True` (no soma→witness coupling); no measurement-conditioned gate on
  the body/selection path; witness set = the witness loci; selection laws diagonal + witness-clear; walk+consume
  gates present.
- `... --interaction germ_coupled --dump-circuit` → `back_action=True` (a soma→witness coupling present) — the
  A/B contrast that collapses the witness.
- `python code/pj_vivarium.py --width 4 --track 5 --steps <few>` (no `--backend` = sim) → banks the three arms
  in **one circuit each**; `barren` energy ≈ 0 and witness ≈ baseline; `vivarium` energy rises where body meets
  food, population/survivors reflect emergent selection, witness reported vs null; `germ_coupled` witness
  collapses vs `vivarium`. Confirm exactly **one measured circuit per arm** (no frame sweep).
- **Emergence check (behavior from the seed, not the code):** `barren` and `vivarium` run the **identical
  circuit law** (`H_viv`) differing **only** in the seeded food — confirm (from the sim `sim_frames`) that
  foraging concentrates, eating, starvation, and budding appear **only** in `vivarium` (where food was seeded)
  and are **absent** in `barren`, with no code-path/`if` difference between them (`--dump-circuit` structural
  diff = food seed + the fired `H_eat` term only). This is the "alive, not on rails" evidence, mirroring PJ1's
  emergent-contact proof.
- `python analysis/pj_vivarium_render.py --run-glob 'research_runs/pj2/*sim*.json'` → opens
  `research/pj2_vivarium/index.html`; the organism walks its habitat, eats food (sites wink out), the
  energy/fitness bar fills, alive/selected + trait chips update, the witness meter stays green (`vivarium`) /
  goes red (`germ_coupled`); arms toggle; 3-arm PNG written.
- Inspect the **scheduled** HW circuit → selective DD on the **germ line only**, body/habitat/energy DD-free
  (AC-PJ2.10).
- Live (developer): `python code/pj_vivarium.py --backend <heron> --width 12 --track 6 --steps <few>
  --shots 8192` (QRNG env set) → three arms, **one measured circuit each**, banked to `research_runs/pj2/`;
  render from live data.
- Confirm `qalife.py`, `run_qalife.py`, `pj_run_qalife.py`, `pj1_run_arena.py` unchanged (`git diff` empty);
  PJ0/PJ1 `--selftest` green.

---

## 9. Risks

- **R1 — energy-powered budding can bite the witness (biggest, and the point).** `H_bud`/`H_forage`/`H_starve`
  are **phenotype-side** by default (control = the body's energy qubit; germ line untouched → Weismann holds,
  witness clean). The risk lives only in the opt-in `--gate-repl` variant, where budding drives the **germ
  clone** — coupling the germ to the mortal, decohering body (the PJ0 wound). Mitigation: `--gate-repl` is
  off by default and exists precisely to **measure** that cost against the phenotype-only baseline; if it kills
  the witness at small W, that boundary **is** the P3 richness result (CD-4, AC-PJ2.7). Note the emergent laws
  act on **diagonal/energy** qubits, so even the default budding injects no coherence into the germ line.
- **R2 — depth vs coherence (one circuit, no frames).** Baking the whole life cycle into one circuit stacks
  germ + `steps`×(walk+consume) + selection depth → the witness erodes with `steps`/`track`/`food`. Mitigation:
  cheapest primitives (single `rxx+ryy` per hop, unary consume), **few steps** on HW (one run, save QC), DD on
  the germ line, measure at the terminal time only. The one-run choice is *cheaper* than PJ1's frame sweep
  (1 job/arm vs many), which is the upside of "no frames."
- **R3 — qubit budget.** Formula `nq = W + traits + 2·track + energy` (`= W + 2·track + 6` at traits=3,
  energy=3, food-lattice=track). At the W12/track6 anchor: germ 12 + traits 3 + body 6 + food-lattice 6 (2
  seeded) + energy 3 = **30 qubits** (default emergent, **no** fitness ancilla); `--hard-select` adds the one
  comparator ancilla → 31. W6 cheap variant = 24; W24 = 42. Fits the ~107-clean-chain comfortably (PJ0 reached
  100, PJ1 used 38). Leaner food (2 qubits, seeded sites only, not a full lattice) → 26 at W12. Larger
  habitat/energy approaches the wall; `gated_chain` fail-closes.
- **R4 — "one run" loses intermediate measured data.** By construction only the endpoint is measured; the
  trajectory is sim-only (labelled). Mitigation: this is the developer's explicit lock (AC-PJ2.3); the sim
  movie + measured endpoint is the deliverable, matching the existing `pj1_spectacle.py` "simulation artifact"
  precedent. If intermediate *measured* checkpoints are later wanted, that is a small number of extra terminal
  circuits at different `T` (a follow-up, not this ticket).
- **R5 — encoding (unary vs binary).** `rxx+ryy` hopping + co-located consume are **site-local** → **unary**
  habitat/energy (matches the renderer, keeps gates shallow). Binary would need adder-based walks/consume
  (deeper → worse witness) and would not match the picked visual. Built unary; binary is the leaner fallback
  only if the habitat must grow past ~10 sites (OQ-2).
- **R6 — QRNG fail-closed / PJ0-PJ1 regressions.** Reuse the fail-closed gating; keep `build_germsoma`/
  `build_arena` and both existing drivers byte-stable; PJ0/PJ1 `--selftest` must stay green.
- **R7 — faithfulness of the barrier (developer question, 2026-09-23).** Total germ⊥soma disjointness would
  make the body a *separate object*, not an expression of the genome — unfaithful. PJ2 fixes this to the
  **asymmetric** Weismann barrier: germ→soma **expression is present** (`expression=True`, the classical genes
  drive the body — faithful to the paper's "phenotype determined by genetic information", and legitimately
  classical since the paper's gene→body info is ⟨σz⟩-encoded), while soma→germ **back-action is banned**
  (`back_action=False`, `witness_isolated=True`, the mortal body cannot decohere the witness loci). The quantum
  claim rests on the cross-generation genealogical entanglement, never the within-individual gene→body link.
  `--gate-repl` intentionally breaks the ban to *measure* the cost (AC-PJ2.7). This is the one design choice the
  developer explicitly probed; the asymmetric barrier is the answer.

---

## 10. What later rungs pick up

- **PJ1 cross-over:** a vivarium with **two** organisms sharing one habitat + resources (competition for food)
  fuses PJ2's environment with PJ1's arena — the L=2 resource-competition arena. PJ2's food/energy/fitness
  machinery drops straight into `build_arena`'s organism loop.
- **Adaptive measured selection (epic §9 P3):** swap PJ2's *static* fitness ancilla for mid-circuit measured
  culling to quantify the (expected large) witness cost of real feed-forward selection on this chip — the
  separate, deliberately-deferred move.
- **Stone-wall virus epic:** PJ2's structured viral genome + consumption is the single-block precursor of the
  cross-block infection witness (`plans/virus/`); the two studies inform each other but stay separate (epic Q3).

---

## 11. Open questions — ALL RESOLVED (developer, 2026-09-23)

- **OQ-1 (ticket ID / naming) — RESOLVED: `PJ2` = the "solo vivarium".** Retire the old candidate-menu
  "PJ2 = multi-run ages" (an unbuilt classical-stitch compromise, never headlined as quantum); this
  single-circuit certified move takes the PJ2 slot. Record the supersession in `P3-candidate-movess.md`. The
  ticket's public name is **"solo vivarium."**
- **OQ-2 (habitat/energy encoding) — RESOLVED: unary, `track=6`, `energy=3`; food = a track-length lattice
  (6 q) with `2` sites seeded `|1⟩`.** Default organism = **30 qubits** at W12 (no fitness ancilla in emergent
  mode; `--hard-select` = 31). Leaner food (2 qubits, seeded sites only) = 26 q, kept as fallback. Binary
  encoding stays the documented leaner alternative only if the habitat must grow past ~10 sites.
- **OQ-3 (selection) — RESOLVED + STRENGTHENED (developer, 2026-09-23): selection is EMERGENT, not an imposed
  threshold.** Default = survival emerges from the fixed `H_viv` laws (forage/eat/starve/bud), phenotype-side,
  witness-safe (AC-PJ2.5). The static `energy ≥ θ_fit` comparator is demoted to an optional `--hard-select`
  contrast arm. `--gate-repl` opt-in couples budding to the germ clone as the measured richness datapoint
  (witness cost of real physical selection, R1/AC-PJ2.7).
- **OQ-4 (live anchor + who runs HW) — RESOLVED: W12 / track6 / few steps; the developer runs the hardware**
  (as with PJ1). W6 kept as an even-cheaper first sign-check.
- **OQ-5 (one run vs a few terminal circuits) — RESOLVED: strictly one measured circuit per arm/repeat; the
  movie is sim-reconstructed.** Measured intermediate checkpoints, if ever wanted, are a follow-up (extra
  terminal circuits at different `T`), not this ticket.
- **OQ-6 (visualization) — RESOLVED: extend the wave-bars picked visual to a single-organism vivarium** (body +
  food sites + energy/fitness bar + alive/selected + trait chips + witness meter), reusing the locked look.
- **OQ-7 (genome trait semantics) — RESOLVED: `t_role`=motility (active — sets the hop rate, the paper's
  "capacity to displace"), `t_repl`=replication-rate flag & `t_life`=lifetime flag = displayed-only heredity
  now, activated in a later rung.** Only `t_role` acts (on the hop) for AC-PJ2.6.

---

## 12. Ground rules honored

- Every AC traces to `P3-candidate-movess.md` (rung 5, M5, M6, PM1, PM3), the 2018 Discussion roadmap (§1
  quotes), and the PJ0/PJ1 substrate; none invented.
- Concrete file paths + line-grounded source references throughout (§5, §6).
- Epic cross-cutting decisions applied (§4); CD-1 in-place model extension + new driver stated.
- L>1, bath death, mid-circuit selection, per-frame HW movie, teleport kept out of scope (§3); the builder is
  structured to admit them without a rewrite (§10).
- Strict types + PEP-8 for all new code; no raw SQL / templates (N/A).
- No tests (CD-7): verification is static `--selftest` + `--dump-circuit` + `--sim` + one live run + written
  conclusion.
- `qalife.py`/`run_qalife.py` byte-stable; PJ0 `build_germsoma` + PJ1 `build_arena` + both existing drivers
  byte-stable.
- The locked visual is extended to a single-organism vivarium spectacle (AC-PJ2.11).
- `Status: Complete` (see §13).

---

## 13. Post-implementation (2026-09-23)

**Built.** The vivarium model (`code/pj_qalife.py`, +~370 lines alongside PJ0/PJ1;
`build_germsoma`/`build_arena` and all four other files byte-stable): `build_vivarium`
(`code/pj_qalife.py:920`) — one enriched proto-viral organism (witness germ line + classical genes +
unary body + food lattice + energy + death bath), the fixed local `H_viv` life cycle (forage / eat /
bud / age-via-bath + revive-the-fed), the layout/analyzer helpers, `viv_to_witness_basis`
(`:1024`), `vivarium_coupling_report` (`:1058`, the asymmetric-barrier static check), seven vivarium
`--selftest` checks (`run_vivarium_selftest`, `:1193`), and a `--vivarium` CLI. New driver
`code/pj_vivarium.py` (`build_measured_vivarium:75`, `sim_snapshots:119` — Aer statevector movie,
`schedule_vivarium_selective_dd:162`, `run_arm:200` — ONE measured circuit per arm, PJ2 schema →
`research_runs/pj2/`). New renderer `analysis/pj_vivarium_render.py` (`build_data:41`,
`render_html:242` self-contained spectacle, `render_witness_png:254`). Banked artifacts in
`research/pj2_vivarium/` (index.html, pj2_witness_3arm.png, circuits/, CORRECTNESS.md, CONCLUSION.html).

**Result (statevector sim, W=3, track=5, 5 steps; one measured circuit per arm).**

| arm | witness ⟨X^⊗3⟩ | population (alive) | food left | verdict |
|-----|----------------|--------------------|-----------|---------|
| `barren`       | +1.000 | 0.41 | 0.00 | witness survives; body starves |
| `vivarium`     | +1.000 | 0.87 | 1.64 | witness survives; **fed body thrives** (~2× barren) |
| `germ_coupled` | +0.006 | 1.23 | 1.63 | **witness collapses** (barrier broken) |

Survival of the fittest is visible and emergent (fed population ≈ 2× starved); the germ witness stays
certified through the whole enriched life cycle and collapses only in the deliberately mis-wired arm.

**AC coverage (file:line).**
- AC-PJ2.1/1b — `code/pj_qalife.py:920` (`build_vivarium`), `:1058` (`expression` check); selftest (i).
- AC-PJ2.2 — habitat/food seed in `build_vivarium` (`:1000` genome+habitat phase); `meta.food_sites` in the run JSON.
- AC-PJ2.3 — `code/pj_vivarium.py:200` (`run_arm`, one measured circuit) + `:119` (`sim_snapshots` movie); `meta.one_run_no_frames=True`.
- AC-PJ2.4 — `vivarium_coupling_report` `has_classical_branch=False` (`code/pj_qalife.py:1058`); selftest (v); barren/vivarium emergence diff, selftest (vii).
- AC-PJ2.5 — `H_bud` + age-via-bath + revive-the-fed in `build_vivarium` (`:1005`); `--hard-select` / `--gate-repl` opt-ins; selftest (vi).
- AC-PJ2.6 — motility gene scales the hop + energy-controlled hop in `build_vivarium` (`:990`); expression `cx(gene_role→body)`.
- AC-PJ2.7 — `code/pj_vivarium.py:96` (`reduce_counts` witness vs null), endpoint witness/signal/survives; sim result above (richness datapoint = the arm contrast).
- AC-PJ2.8 — `germ_coupled` back-action in `build_vivarium` (`:1013`); `vivarium_coupling_report` `back_action=True`; sim collapse +0.006.
- AC-PJ2.9 — diagonal readouts in `reduce_counts` (`code/pj_vivarium.py:96`); separable null reported ≈0; CONCLUSION honesty note.
- AC-PJ2.10 — `schedule_vivarium_selective_dd` (`code/pj_vivarium.py:162`, DD on `viv_witness_qubits` only).
- AC-PJ2.11 — `analysis/pj_vivarium_render.py:242` (`render_html`) → `research/pj2_vivarium/index.html` (14.5 KB, 0 external refs, canvas + 3 arms + food/energy/witness widgets + endpoint overlay).
- AC-PJ2.12 — HW path in `run_arm` (`sim=False` branch: selective DD + `gated_chain` + QRNG fail-closed) + `main()`; **code complete, live W12 run pending developer** (OQ-4).

**Deviations from the plan (documented).**
1. **Death needs an explicit bath, not pure "natural T1".** §3 preferred natural trace-out with "no bath",
   but a noiseless statevector shows NO T1 decay — the first `rx`-toward-|0⟩ attempt actually *injected*
   population (barren organisms grew). Replaced with a per-body-site amplitude-damping **bath** (the paper's
   dissipation / PJ0's `local_damping` channel, soma-side, witness-safe) + revive-the-fed, so survival is
   visible in sim and EM-fightable on HW. Qubit count rose accordingly.
2. **Qubit budget: 30 → depends on encoding.** With food a full-track lattice + a per-site death bath,
   `nq = W + traits + 3·track + n_food`. W12/track6 = **35** (+1 `--hard-select`), not 30. Still well under
   the ~107 clean chain. The compact-food fallback (OQ-2) recovers ~30 if wanted.
3. **Sim is small (W3/track5 = 23 q).** Repeated full statevectors are heavy; the demo/banked sim is W3, and
   `sim_snapshots` uses Aer `save_statevector` (C++) rather than `quantum_info.Statevector.from_instruction`
   (Python) for speed. W12 is HW-only, exactly as PJ1 (sim small, HW big).

**Follow-ups for the developer.**
- **Live W12/track6 Heron-r2 run (AC-PJ2.12)** is yours (OQ-4): `python code/pj_vivarium.py --backend
  <heron> --width 12 --track 6 --steps 4 --shots 8192` (QRNG env set). Then re-render:
  `python analysis/pj_vivarium_render.py --run-glob 'research_runs/pj2/*<heron>*.json'`.
- `--gate-repl` and `--hard-select` variants are wired but unrun — they are the measured-cost / contrast
  datapoints when you want them.
- Note the pre-existing `analysis/plot_baseline.py` issue (flagged in the PJ1 plan) is unrelated and untouched.
```

