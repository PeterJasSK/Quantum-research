# Feature Plan — PJ1: Two germ/soma organisms colliding in one environment (the arena)

**Ticket:** PJ1 (stage, not a GitHub issue — this research repo decomposes epics into stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09), stage **P3** (richness investigations)
**Candidate source:** `artificial-life/plans/P3-candidate-movess.md` §"PJ · gradual implementation ladder" rungs **3–4**, §"PJ1 · the core arena", §"PJ1 · main issues & unknowns" (I1–I3, I9)
**Pre-plan visual study:** `artificial-life/pj1Concepts/` (4 prototypes + generators; picked visual = `4_wave-bars_PICKED.html`)
**Slug:** two-organism-collision
**Substrate:** `code/pj_qalife.py` + `code/pj_run_qalife.py` (PJ0 pair; organism-offset layout + `#PJ1` boundary-coupling hook already present)
**Author:** Claude (Opus)
**Date:** 2026-09-13
**Status:** Complete

> **No tests (repo convention, CD-7).** Verification is `--selftest` (static circuit-structure checks) +
> `--dump-circuit` printing + `--sim` runs + a written correctness/conclusion evaluation. No test framework,
> no test files.
>
> **This ticket RUNS (developer-directed lock).** Unlike PJ0 (build + static eval only), PJ1's locked run
> target is **build + sim + live Heron-r2 run in-ticket** — it banks real witness numbers and the rendered
> web demo. Sim-first, hardware-confirm (CD-7).

---

## 1. Summary

PJ1 opens the **arena**: two germ/soma organisms living in one environment, their bodies moving toward each
other, meeting, and interacting **coherently** — then measured to see whether a **joint cross-lineage
entanglement witness** survives the collision. It is built directly on the PJ0 substrate (which proved a
single germ/soma organism keeps its certified witness to W=50 = 100 qubits by severing soma from germ). PJ1
is ladder **rungs 3–4** (P3-candidate §ladder): rung 3 = two independent lineages (joint witness ≈ product
null); rung 4 = add coherent **energy transfer** (the collision) and ask whether it lifts the joint witness
above the product null. Reproduction (rung 5) and L>2 (rung 6) are **out of scope** (§3).

Each organism = a **germ line** (the W-individual GHZ genealogy carrying the witness `⟨X^⊗W⟩`, kept
coherent — unchanged from PJ0) + a **soma body** (a small position register = a quantum walker on a shared
track, the thing that moves and collides). The two bodies start apart, walk toward each other, and where
they overlap a coherent **XX+YY exchange** coupling acts — transferring excitation and **entangling the two
bodies**. The coupling is a Hamiltonian term that is *always present at the shared sites and only acts when
both bodies have amplitude there* — interaction **emerges from co-location, never `if(contact)`** (the whole
"as if alive" point, confirmed in the visual study: entropy stays 0 until the bodies meet).

**Three arms** (the science), each a build/sim/run:
1. **`pass_through`** (control) — coupling off; the bodies glide through each other; joint witness ≈ product
   null; contact entanglement ≈ 0. Proves any reaction below is *caused* by the coupling.
2. **`soma_soma`** (the result) — XX+YY exchange between the two **body** registers only; germ lines never
   touched → **joint witness survives** the collision (rung-4 question: does it sit above the product null?
   I1). Contact-entanglement rises on overlap.
3. **`germ_routed`** (A/B) — the same collision coupling routed through a **germ** qubit → **joint witness
   collapses**. The PJ0 kill-switch, now cross-organism: proves the Weismann barrier is the mechanism.

**Headline output (locked):** the **live collision spectacle** — the wave-bars visualization
(`pj1Concepts/4_wave-bars_PICKED.html`) rendered from the **banked run data**: two organisms' body-occupancy
per time-step (measured Z-basis), the joint genealogy witness (measured X-basis), and the contact meter,
scrubbable through real measured generations — plus the 3-arm witness contrast as the science figure.

**Certified quantum claim (CD-3):** the **joint genotype-only** witness `⟨X^⊗2W⟩` over both germ lines
(and, per I1, a **bipartite A|B cut** witness as a second, tighter certificate). The body occupancy and the
per-body ⟨σz⟩ trait are honestly **diagonal/classical plumbing** (they have an exact classical surrogate)
— only the germ witness carries the quantum claim.

**Locks (visual study 2026-09-13 + OQ answers 2026-09-13):** visual = wave-bars; soma encoding = **unary
one-hot track, `track=6` sites/organism** + 1 trait qubit (Q1/OQ-1 — XX+YY is site-local, unary is what the
picked visual uses); interaction gate = XX+YY exchange; headline = live spectacle + the certificate that best
proves non-classicality (Q6: **A|B bipartite-cut witness** headline, no classical surrogate); run target =
build + sim + **live** (developer runs the hardware, Q2). Live anchor = **W12 / track=6**, kept to **few
frames + few steps to save QC time** (Q3). Arena **driver in a new file** so PJ0 stays byte-stable and easily
recreatable (Q5).

---

## 2. Acceptance criteria

Grounded in `P3-candidate-movess.md` ladder rungs 3–4, §"PJ1 · the core arena" (encoding + the two
witnesses), and §"PJ1 · main issues" I1–I3/I9. IDs added. All hardware ACs enforce the fail-closed
chain-quality gate (CD-5) and certified QRNG (CD-6).

- [x] **AC-PJ1.1 (rung 3, arena substrate):** an **arena builder** in `code/pj_qalife.py` places **two**
  germ/soma organisms as adjacent segments (reusing the organism-offset layout), each germ line the clean
  W-individual GHZ chain (unchanged PJ0 genealogy), each with a **soma body register** on a shared track.
  `--selftest` green on the new static arena checks (§6.1). Static Test 1 still holds **per organism**
  (no gate couples a body/germ pair within an organism) in the `soma_soma`/`pass_through` arms.
  ✔ Covered by `code/pj_qalife.py:566` (`build_arena`, adjacent tiling `arena_base`:502), `:654`
  (`arena_coupling_report` per-organism Static Test 1), `:781` (`run_arena_selftest`) — five checks green at
  W∈{2,4,12} (`research/pj1_arena/circuits/_arena_selftest.txt`).
- [x] **AC-PJ1.2 (rung 3 baseline, the product null):** with the coupling **off** (`pass_through`), the
  **joint** witness `⟨X^⊗2W⟩` ≈ the **separable joint null** `∏_i⟨X⟩_i` (both per-lineage witnesses
  survive independently; the joint carries no cross-lineage entanglement). Reported from sim and a small HW
  confirm; separable null pinned ≈0 (CD-3).
  ✔ Covered by `code/pj1_run_arena.py:107` (`reduce_frame`: joint/sep/per-lineage). Sim: `none` arm
  joint=+1.00, sep_null≈0, cut_AB≈0 (`research_runs/pj1/pj1_arena_statevector_sim_sim.json`,
  `research/pj1_arena/CONCLUSION.html`). HW confirm = developer (AC-PJ1.10).
- [x] **AC-PJ1.3 (rung 4, THE result — I1, Q6):** with the XX+YY **exchange** coupling **on** (`soma_soma`),
  measure whether the collision lifts cross-lineage entanglement above the product null. **Headline
  certificate = the bipartite A|B cut witness** (certifies A–B entanglement directly, no classical surrogate —
  the "can't be replicated" proof, Q6); the global joint string `⟨X^⊗2W⟩` reported alongside. Gate:
  `witness − separable_joint_null > k·σ` (k=2 headline, k=3 reported). Report the **coupling-strength sim-scan**
  locating the macroscopic (non-perturbative) regime **before** hardware (I1a). Honest framing: if the witness
  stays at/near the null, that is a reported result (flagship witness is *upside, not obligation* —
  P3-candidate §"Division of labour"); the per-lineage witnesses + the spectacle stand.
  ✔ Covered by `code/pj1_run_arena.py:107` (`witness_cut_AB` = joint − w_A·w_B) + `:258` (`scan_coupling`,
  I1a). **Honest result:** A|B germ cut stays at 0 across the encounter and across φ∈[0,π] (soma_soma couples
  bodies only) → the collision does NOT lift cross-lineage *germ* entanglement (I1 predicted). Body
  entanglement (contact S) peaks ~2.3 bits at φ≈π/4. Reported, not a failure — `research/pj1_arena/CONCLUSION.html`.
- [x] **AC-PJ1.4 (the collision is emergent, not coded):** the interaction is a coherent operator applied
  at the shared track sites with **no classical branch** on contact. Static check: the built circuit contains
  the coupling gates unconditionally (no `c_if`/measurement-conditioned gate on the body path); and the
  `pass_through` arm — identical except the coupling is absent — produces **contact-entanglement ≈ 0** while
  `soma_soma` produces contact-entanglement > 0 **only during overlap** (sim, statevector). This pair is the
  "emergent, not `if(contact)`" evidence.
  ✔ Covered by `code/pj_qalife.py:539` (`_collision_layer`, unconditional gates), `:654`
  (`arena_coupling_report` `has_classical_branch`=False), selftest check (iv). Sim: `none` contact-entropy =
  0.0 at every frame; `soma_soma` 0.0→~1.59 bits on overlap (`contact_entropy_sim`, `pj1_run_arena.py:147`).
- [x] **AC-PJ1.5 (A/B kill-switch — the barrier mechanism):** the `germ_routed` arm re-routes the same
  collision coupling through a **germ** qubit; static check shows it violates per-organism Static Test 1
  (a body–germ or germ–germ coupling gate is present), and the measured **joint witness collapses** relative
  to `soma_soma` at matched settings. Proves cross-organism that coupling the body to the gene line is what
  kills the joint genealogy (the PJ0 diagnosis extended, I7-analogue).
  ✔ Covered by `code/pj_qalife.py:539` (`_collision_layer` `germ_routed`: body↔`germ_q(1,0)`), selftest
  check (i) (`germ_routed_disjoint=False`). Sim: joint witness collapses +1.00 → −0.39 vs `soma_soma`
  (`research/pj1_arena/circuits/arena_W4_track5_frame3_germ_routed.txt`, `CONCLUSION.html`).
- [x] **AC-PJ1.6 (movement banked as frames — the spectacle data):** the driver banks, per **time-step
  frame** and per arm, the **body occupancy** of each organism (P(site)=Z-basis on the body register), the
  **joint witness** + **separable joint null** + **per-lineage witnesses** (X-basis on the germ lines,
  co-measured in one circuit), and the sim-only **contact entanglement** (statevector S(ρ_bodyA); labelled
  sim-only, no cheap HW estimator — OQ-4). Occupancy + witness are **measured on hardware** at the chosen
  frames.
  ✔ Covered by `code/pj1_run_arena.py:223` (`run_arm` frame sweep) + `:83` (`build_measured_arena`: H germ
  only, bodies in Z, one circuit) + `:107` (`reduce_frame`) + `:147` (`contact_entropy_sim`). Schema
  `arms[arm]=[{t,occ,witness_joint,separable_joint_null,witness_per_lineage,witness_cut_AB,entanglement_signal,contact_entropy_sim}]`
  banked to `research_runs/pj1/`.
- [x] **AC-PJ1.7 (the locked visualization):** `analysis/pj1_render.py` reads a banked PJ1 run JSON and
  emits a **self-contained** wave-bars web demo (port of `pj1Concepts/4_wave-bars_PICKED.html`) with the
  **real** measured frames injected: two organisms' bodies as position bars + ψ-envelope + travelling A/B
  heads, additive-overlap flare, the live genealogy witness meter (green survives / red collapses) and the
  contact meter, arm toggle, smooth interpolation, plain-language caption. CSP-safe (all inline, no external
  fetch), theme-aware note, `research/pj1_arena/index.html`.
  ✔ Covered by `analysis/pj1_render.py:76` (`render_html`, swaps the `const DATA=` literal) + `:46`
  (`build_data`, maps frames→`{a,b,s,ov,w}`). Output `research/pj1_arena/index.html` (23 KB, 0 external
  refs, DATA L=5/24 frames/3 arms) + `:101` `pj1_witness_3arm.png`.
- [x] **AC-PJ1.8 (selective DD on both germ lines — Weismann barrier, HW):** `schedule_with_selective_dd`
  extended so DD lands on the **genotype physical qubits of both organisms** only; body qubits DD-free.
  Verified by inspecting the scheduled circuit (static). Reuses the PJ0 pass, generalized to
  `arena_witness_qubits`.
  ✔ Covered by `code/pj1_run_arena.py:172` (`schedule_arena_selective_dd`, DD on
  `arena_witness_qubits` = both germ lines). **DEVIATION:** re-implemented in the new driver (not by
  extending PJ0's pass) — PJ0's `schedule_with_selective_dd` derives its target internally from
  `pj.witness_qubits(width, has_bath)` (PJ0 layout, one organism) and cannot target both arena germ lines
  under the arena layout without editing `pj_run_qalife.py` (forbidden, Q5). Pass otherwise identical.
- [x] **AC-PJ1.9 (honest diagonal plumbing, CD-3/CD-4):** the body occupancy and the per-body ⟨σz⟩ trait
  are shown to have an **exact classical surrogate** (they are diagonal), so only the germ witness carries
  the quantum claim; the separable joint null is reported alongside every witness and must sit ≈0.
  ✔ Covered by `code/pj1_run_arena.py:107` (`reduce_frame` reports `separable_joint_null` alongside every
  witness; occupancy = Z-basis marginals = diagonal). Framing in `research/pj1_arena/CONCLUSION.html` foot +
  `CORRECTNESS.md`. Sim: sep_null≈0 in every arm.
- [ ] **AC-PJ1.10 (live run banked, CD-6/CD-7):** a live Heron-r2 run at the chosen W (W12/organism default,
  OQ-3) for the three arms, QRNG-certified fail-closed, chain-quality gate enforced; banked to
  `research_runs/pj1/` in the extended schema; PJ0 runs remain reproducible (`organisms=1` path byte-stable).
  ◑ **Code complete; live run pending developer (Q2/OQ-2 — "the developer executes the hardware runs").**
  HW path `code/pj1_run_arena.py:223` (`run_arm`, `sim=False` branch: `schedule_arena_selective_dd` +
  `gated_chain` fail-closed + QRNG `coll_site`) + `main()` QRNG fail-closed gate; banks to
  `research_runs/pj1/`. Sim banked; byte-stability confirmed (`git diff` empty on `qalife.py`,
  `run_qalife.py`, `pj_run_qalife.py`; PJ0 `--selftest` green). Run:
  `python code/pj1_run_arena.py --backend <heron> --width 12 --track 6 --frames 6 --shots 8192`.

---

## 3. Out of scope

- **Ladder rung 5 — differential reproduction** (controlled-clone gated on a reserve / "survival of the
  fittest" superposition-of-winners). Not built. The body-trait qubit is left as the reproduction hook
  (§6) but no gated clone is added.
- **Ladder rung 6 — scaling L>2** (3–4 lineages, balanced arena). PJ1 is **L=2 only**. The arena builder is
  written to admit L>2 (organism loop) but only two are built/run.
- **Energy-reserve register as a separate resource qubit** (P3-candidate §encoding). PJ1 folds "reserve /
  life-blood" into the **body register itself** (excitation on the body = presence/energy); a dedicated
  resource qubit is a rung-5 concern.
- **Teleport / long-range routing (I9 — DEAD).** Lineages are **adjacent** on `layout.best_chain`;
  encounters use direct/short coupling only. Not touched.
- **Mid-circuit measurement / feed-forward selection** (the P3 adaptive-selection move). PJ1 is fully
  unitary until the terminal readout (I9 rationale: mid-circuit measure collapses the superposition and is
  not DD-fightable).
- **Any change to the faithful `qalife.py` / `run_qalife.py`** (byte-stable, Q1). PJ1 extends the `pj_*`
  pair only.
- 
- **PJ0 behavior change.** `build_germsoma` and the `organisms=1` run path stay byte-stable; PJ1 is added as
  new functions + an arena mode, not by editing PJ0's build.

---

## 4. Cross-cutting decisions applied (epic §3 + PJ0 §4)

- **CD-1 (main-folder minimalism) — PJ pair, in place.** PJ1 **extends** `code/pj_qalife.py` +
  `code/pj_run_qalife.py` (the substrate PJ0 built explicitly to be extended: the organism-offset layout and
  the `#PJ1` marker at `pj_qalife.py:160` are already there). **No new top-level fork** and **no edit to the
  faithful reproduction.** `pj_qalife.py` keeps importing `qalife as q4` read-only. Analysis/rendering goes
  in `analysis/` (mirroring `analysis/plot_baseline.py`).
- **CD-3 (witness is the only quantum claim).** PJ1's sole quantum observables are the **joint genotype-only**
  `⟨X^⊗2W⟩` and the **A|B bipartite** witness. Body occupancy and body ⟨σz⟩ are declared classical; the
  separable joint null is reported alongside and must sit ≈0.
- **CD-4 (honesty invariant).** The collision's *diagonal* effects (who is where, occupancy) have an exact
  classical surrogate → reported as plumbing. Only cross-lineage entanglement (the joint witness above the
  null) is the quantum content. If a matched classical sim reproduces the population/occupancy outcome, it is
  named as such. The flagship's job is the spectacle + the PJ0 witness underneath; the joint witness is
  **upside, not obligation** (P3-candidate §"Division of labour").
- **CD-5 (significance + chain-quality gates).** `entanglement_depth` (k=2 headline, k=3 reported); σ from
  `--repeats` + shot-noise in quadrature; fail-closed chain-quality gate (`gated_chain`,
  `pj_run_qalife.py:243`).
- **CD-6 (QRNG certified, fail-closed).** Mutation angles **and** the QRNG-chosen **encounter parameters**
  (collision site / phase — a *provenance* claim, not a computational one, M5) come from `qrng_client.py`;
  fail-closed on hardware (`pj_run_qalife.py:297–314`). Fixed per circuit, not per shot (P3-candidate
  §encounters). PJ1 keeps `MUT_SCALE=0` faithful by default (clean GHZ), so the collision effect is isolated.
- **CD-7 (sim-first, hardware-confirm; verification without a test framework).** Fix in `--sim` + `--selftest`
  first, then confirm live. Static circuit-structure checks + printed circuits + written conclusion; no test
  framework.
- **CD-8/CD-11 (biology is measured, not noise; EM is a lever).** The collision is an explicit, coherent,
  entropy-traced operator — never noise dressed as interaction. All witness loss is real hardware noise
  (no bath, no trace-out — P3-candidate §"design principle"), so selective DD (AC-PJ1.8) is allowed to fight
  it.

---

## 5. Verified codebase facts (grounding the plan)

From the substrate survey (2026-09-13), current line numbers:

- **Layout is organism-offset index functions** (`pj_qalife.py:77–99`): `segment_len(width, has_bath)`
  (`2W + W·has_bath`), `organism_base(o, width, has_bath) = o·segment_len`, `geno_q(o,k,…)=base+k`,
  `pheno_q(o,k,…)=base+W+k`, `soma_bath_q(o,k,…)=base+2W+k`. The `#PJ1: … boundary coherent-coupling
  (partial-SWAP)` marker is at **`pj_qalife.py:160`**.
- **`build_germsoma`** (`pj_qalife.py:114`) already loops `for o in range(organisms)` (the PJ1 hook, `:136`);
  `organisms=1` for PJ0. Gates used are `qc.ry/cx/cry/barrier` only — **no `rxx`/`ryy`/`swap`/`cz` exist yet**
  (they will be added for the XX+YY coupling).
- **Witness helpers:** `witness_qubits(width, organisms=1, has_bath=False)` (`pj_qalife.py:208`) already
  returns **all germ qubits across organisms** → `witness_qubits(W, 2)` **is** the joint-witness qubit set.
  `soma_qubits` (`:214`), `to_witness_basis(qc, width, *, phenotype, soma_death, organisms=1)` (`:190`,
  H on germ qubits only), `germsoma_coupling_report` (`:245`, keys incl. `disjoint`, `gene_first`),
  `aging_order_deviation` (`:287`).
- **Witness math (`qalife.py`, read-only):** `xbasis_witness_from_counts(counts, qubits) -> (joint, sep)`
  (`:217`) over an arbitrary qubit list; `entanglement_depth(witness_by_gen, sep_by_gen, sigma, k=2.0)`
  (`:239`); `classical_surrogate_z(width, steps, thetas, interaction, death, …)` (`:251`);
  `_z_geno_chain(width, thetas, founder_equator)` (`:87`). Constants `AGING_DELTA=π/8`, `DAMP_GAMMA=0.18`,
  `ALIVE_THRESH=0.80`.
- **Driver (`pj_run_qalife.py`):** globals `INTERACTION="none"` (`:58`), `REPEATS=1`, `K=2.0`,
  `MUT_SCALE=0.0`, `SOMA_DEATH="natural"`, `PHENOTYPE="separable"`, `SELECTIVE_DD=True`, `AGING_ORDER_TOL=2`,
  gate thresholds `MAX_TWOQ_ERR=0.05`/`MAX_READOUT_ERR=0.15` (`:80–82`). `build_measured_germsoma`
  (`:122`, H germ only + `ClassicalRegister` + measure). `qrng_thetas(client, width, mut_scale, repeat)`
  (`:104`, fail-closed). `schedule_with_selective_dd(qc, backend, width, *, soma_death)` (`:163`) — opt-3
  preset PM, reads `routed.layout.final_index_layout()`, DD (`[XGate,XGate]`) on `germ_physical =
  witness_qubits(width, has_bath)` **only**. `gated_chain(backend, nq)` (`:243`) → `best_chain` + gate.
  **Sim vs HW = `args.backend is None`** (`:292`); `--dump-circuit`/`--draw-only`; output to
  `../research_runs`, naming `f"{name}_{SOMA_DEATH}_{PHENOTYPE}_{backend}_{tag}.json"` (`:419`); banked PJ
  runs live in `research_runs/pj/`. The run JSON is an **inline dict in `main()`** (`:337–346, 399–412`) with
  `meta.*` (stage="PJ0", model, backend, steps, soma_death, phenotype, selective_dd, aging_order_tol,
  interaction, mut_scale, k, delta, gamma, alive_thresh, shots, repeats, widths, sim, calibration, t1_band,
  genealogical_entanglement_depth_W) and `by_width[str(W)] = {witness_joint_mean, witness_joint_sigma,
  separable_mean, entanglement_signal, survives, alive_mean, deepest_mean}`. **No `_run_schema`,
  `schedule_report`, or `--run` symbols exist** — the schema/decision live inline.
- **Layout:** `best_chain(backend, n, time_budget=40.0) -> (chain, stats)` (`layout.py:54`); raises on no
  clean n-chain (PJ0 hit that wall at W54 = 108 qubits vs 107 available).
- **QRNG:** `QRNGClient.fetch(size, fmt)` (`qrng_client.py:84`), `health()` (`:59`), both raise
  `QRNGUnavailable`; byte→angle done in `qrng_thetas`.
- **Plot infra:** `analysis/plot_baseline.py` — `matplotlib.use("Agg")`, degrades if matplotlib absent,
  `fig.savefig(dpi=150)`, writes PNG + JSON to `--out-dir`. The PJ1 renderer mirrors this (own file, no
  edit).

---

## 6. File plan

One file **extended** in place (`pj_qalife.py`, the shared model) + **two new files** (`pj1_run_arena.py`
arena driver, `analysis/pj1_render.py`) + one new research dir. All new code: strict-typed, PEP-8,
`from __future__ import annotations`, mirroring `pj_qalife.py` style. `qalife.py`, `run_qalife.py`, **and
`pj_run_qalife.py` are not edited** (Q5 — PJ0 driver byte-stable/recreatable); `build_germsoma` and the
`organisms=1` paths stay byte-stable.

### 6.1 Extend — `code/pj_qalife.py` (arena model + arena `--selftest`)

Add PJ1 alongside PJ0 (no edit to `build_germsoma`). New code, all reusing `geno_q`/`witness_qubits` for the
germ blocks:

- **Arena body layout (new, unary track — Q1/OQ-1, `track=6`):** an organism's **body** is a `track`-site
  **unary** register (one excitation = the body's location) + `traits` qubits. New index helpers:
  - `arena_segment_len(width, track, traits) -> int` = `width` (germ) `+ track + traits` (body).
  - `arena_base(o, width, track, traits) -> int`.
  - `germ_q(o, k, width, track, traits) -> int` — germ block, contiguous (nearest-neighbor clone).
  - `body_q(o, j, width, track, traits) -> int` — body site `j` (unary position).
  - `trait_q(o, t, width, track, traits) -> int` — reproduction/energy hook (rung-5, built only as an
    idle qubit here).
  - Two organisms tile as **adjacent** segments (I9): `o=0` then `o=1`. A `# PJ1-rung5: gated clone on
    trait_q here` marker left, built as nothing.
- **`build_arena(width, steps, thetas, *, organisms=2, track=6, traits=1, interaction='soma_soma',
  frame=None, founder_equator=True, delta=AGING_DELTA, coupling=DEFAULT_COUPLING, coll_site=None,
  annotate=False) -> QuantumCircuit`** — phased build:
  1. **Germ lines first** (rung 0 discipline): per organism, founder `ry(π/2)` + nearest-neighbor
     `cx` clone chain + `ry(thetas[k])` mutation on the contiguous germ block. Barrier `"germline"`.
  2. **Bodies:** initialize each organism's walker localized at opposite ends of the shared track
     (`x` on `body_q(0,0)` and `body_q(1,track-1)`).
  3. **Time evolution to `frame`** (the animation clock): repeat `frame` times a **`walk_layer`** =
     nearest-neighbor **`rxx(θ)+ryy(θ)`** hopping on each body register (excitation-conserving quantum
     walk), followed by a **`collision_layer`**:
     - `interaction='soma_soma'` — `rxx(φ)+ryy(φ)` **exchange between the two bodies at aligned sites**
       (`body_q(0,j)`↔`body_q(1,j)`), optionally only at `coll_site` (QRNG-chosen, CD-6). Body↔body only;
       **no germ qubit** in any operand.
     - `interaction='germ_routed'` — the A/B: the exchange couples a body qubit to **`germ_q(1,0)`**
       (restores the wound cross-organism). Deliberately violates per-organism Static Test 1.
     - `interaction='none'` — walk only, no collision layer (control / product null).
     Barrier `"frame{frame}"`.
  4. No death channel, no bath (P3-candidate §principle: all loss is real noise, EM-fightable).
- **`walk_layer` / `collision_layer`** as private helpers taking the built `qc` (so `--dump-circuit` shows
  them). `θ`, `φ` from `coupling` (fixed defaults; the driver sim-scans `φ` per I1a).
- **Static analysis / observables (build-time, no execution):**
  - `arena_witness_qubits(width, organisms=2, track, traits) -> list[int]` → all germ qubits (joint set);
    reuse the sense of `witness_qubits`.
  - `bipartite_cut_qubits(width, organisms, …) -> tuple[list[int], list[int]]` → (A germ, B germ) for the
    A|B cut witness (I1b).
  - `body_site_qubits(o, width, track, traits) -> list[int]` → the Z-basis occupancy readout set.
  - `arena_coupling_report(qc, width, organisms, track, traits) -> dict` — walks `qc.data`; returns, **per
    organism**, whether any gate couples that organism's body to any germ qubit (per-organism Static Test 1),
    whether any collision gate touches a germ qubit (the germ_routed flag), the presence of any
    measurement-conditioned gate on the body path (must be **False** → AC-PJ1.4 "no `if(contact)`"), and
    gate counts.
- **Extend `--selftest`** with arena checks at representative `(W, track)` (e.g. W2/track5, W4/track5,
  W12/track7): (i) per-organism Static Test 1 holds for `soma_soma`/`none`, **fails** for `germ_routed`;
  (ii) germ-first ordering; (iii) witness readout isolation (H on germ only, bodies in Z); (iv) **no
  classical branch** on the body path (no `c_if`/conditioned gate — AC-PJ1.4); (v) `pass_through` build ==
  `soma_soma` build **minus** the collision layer (structural diff). Print per-check `OK` + `SELFTEST PASS`.
- **Extend `main()`** with arena flags: `--arena` (switch to arena build), `--organisms` (default 2),
  `--track` (default 6), `--traits` (default 1), `--interaction` (choices `none|soma_soma|germ_routed`),
  `--frame` (which time-step to draw). Default (no `--arena`) = the existing PJ0 static CLI, unchanged.

### 6.2 New — `code/pj1_run_arena.py` (the arena driver — build + sim + live)

Per Q5, the arena run logic goes in a **new driver file** (not by extending `pj_run_qalife.py`) so the PJ0
driver stays **byte-stable and easily recreatable**. `pj1_run_arena.py` imports `pj_qalife as pj`,
`qalife as q4`, and **reuses PJ0's infra by import** — `from pj_run_qalife import gated_chain, qrng_thetas,
schedule_with_selective_dd, OUTPUT_DIR, SIM` and the `pipeline_common`/`qrng_client` plumbing PJ0 already
wires (no copy, no edit to `pj_run_qalife.py`). `schedule_with_selective_dd` is called with
`arena_witness_qubits` (both germ lines) — it already takes the germ-qubit set as its DD target, so it
generalizes without editing PJ0.

- **Globals:** `ORGANISMS=2`, `TRACK=6`, `TRAITS=1`, `FRAMES_SIM` (e.g. 36, smooth demo), `FRAMES_HW` (few —
  e.g. 6–8, concentrated on the collision, Q2/Q3 to save QC time), `STEPS_HW` (few — Q3), `COUPLING` (θ,φ),
  `ARMS=("none","soma_soma","germ_routed")`. Reuse PJ0 chain-quality thresholds + `SELECTIVE_DD`.
- **`build_measured_arena(width, steps, thetas, *, interaction, frame, organisms=ORGANISMS, track=TRACK,
  traits=TRAITS) -> QuantumCircuit`** — call `pj.build_arena(...)`, then `pj.to_witness_basis`-analogue:
  **H on germ qubits only** (X-basis witness), **bodies left in Z** (occupancy); add `ClassicalRegister`;
  measure all. One circuit yields **both** the witness (germ, X) and occupancy (body, Z).
- **Measurement reductions from counts:** `joint_witness` + `separable_joint_null` via
  `q4.xbasis_witness_from_counts(counts, pj.arena_witness_qubits(...))`; the **A|B cut** witness via the two
  halves (I1b); **per-lineage** witness per germ block; **occupancy** per organism = P(site=1) marginals of
  the body qubits from the same counts.
- **Sim-only contact meter:** a statevector pass (`Statevector` on the unmeasured `build_arena`) computing
  `S(ρ_bodyA)` per frame — the entanglement "contact" reading (OQ-4, labelled sim-only; no cheap HW
  estimator).
- **Coupling-strength sim-scan (I1a):** a `--scan-coupling` mode sweeping `φ` in `--sim`, reporting joint
  witness vs φ, to locate the macroscopic-entanglement regime before HW; the chosen φ is banked in `meta`.
- **Frame sweep + arm sweep:** for each arm and each frame, build → (sim: `SIM.run`; HW: selective-DD
  schedule via the imported `schedule_with_selective_dd` called with `arena_witness_qubits` for **both** germ
  lines, then `run_sampler`). Reuse imported `gated_chain` (fail-closed) and QRNG (`qrng_thetas` + QRNG-chosen
  `coll_site`). HW sweep uses `FRAMES_HW`/`STEPS_HW` (few — Q3, save QC time); sim uses `FRAMES_SIM`.
- **Extend the run schema (inline dict):** `meta.stage="PJ1"`, `meta.model="germsoma_arena"`, add
  `meta.organisms/track/traits/coupling/coll_site/frames/arms`; add a per-arm **`frames[]`** array, each
  `{t, occ:[[…A…],[…B…]], witness_joint, separable_joint_null, witness_cut_AB, witness_per_lineage:[…],
  entanglement_signal, contact_entropy_sim}` — **exactly the shape the wave-bars renderer consumes**
  (AC-PJ1.7). Keep `by_width` for the depth summary. Bank to `research_runs/pj1/`.
- **CLI (own `main()`):** `--backend` (None=sim), `--width` (default 12), `--track` (default 6), `--traits`
  (default 1), `--interaction` (default: run all three arms), `--frames`, `--steps`, `--shots`,
  `--scan-coupling`, `--dump-circuit`/`--draw-only`, `--name` (default `pj1_arena`). No `--arena` flag needed
  — this file **is** the arena driver.

### 6.3 New — `analysis/pj1_render.py` (the locked wave-bars web demo, from banked data)

Mirror `analysis/plot_baseline.py` structure (path shim, `main() -> int`, degrade-gracefully). Reads a
banked `research_runs/pj1/*.json`, extracts the per-arm `frames[]`, and writes a **self-contained**
`research/pj1_arena/index.html` by injecting the real frames into a port of
`pj1Concepts/4_wave-bars_PICKED.html` (the picked renderer). Requirements: CSP-safe (all CSS/JS inline, no
external fetch/CDN), body never scrolls sideways, works from `file://`. Also emit a static 3-arm witness PNG
(matplotlib Agg, `savefig` — the science figure) `research/pj1_arena/pj1_witness_3arm.png`. CLI:
`--run-glob`, `--out-dir` (default `research/pj1_arena`).

### 6.4 New — `research/pj1_arena/` (the banked result + demo + conclusion)

- `index.html` — the rendered wave-bars demo (real data).
- `pj1_witness_3arm.png` — the 3-arm witness figure.
- `circuits/*.txt` — printed arena circuits (`--dump-circuit`) per arm at representative `(W, track, frame)`.
- `CORRECTNESS.md` — static-correctness argument (per-organism Static Test 1, no-`if(contact)` proof,
  germ_routed A/B contrast, selective-DD on both germ lines) with `--selftest` output.
- `CONCLUSION.html` — the results writeup (mirrors `PJ0_CONCLUSION.html`): the three arms, the joint-witness
  vs product-null result (I1), the A/B collapse, honest framing (scale·faithfulness·certification, not a
  speedup; joint witness upside-not-obligation).

### 6.5 Resulting layout (after PJ1)

```
code/
  layout.py  qrng_client.py            # infra (unchanged)
  qalife.py  run_qalife.py             # faithful reproduction (UNCHANGED)
  pj_qalife.py                         # EXTENDED — + build_arena, arena layout/analysis, arena --selftest
  pj_run_qalife.py                     # UNCHANGED — PJ0 driver (byte-stable, Q5)
  pj1_run_arena.py                     # NEW — arena driver: build_measured_arena, arm/frame sweep, PJ1 schema
analysis/
  plot_baseline.py                     # (unchanged)
  pj1_render.py                        # NEW — banked data -> wave-bars web demo + 3-arm PNG
research/
  pj0_germsoma/ ...                    # PJ0 (unchanged)
  pj1_arena/                           # NEW — index.html, pj1_witness_3arm.png, circuits/, CORRECTNESS.md, CONCLUSION.html
research_runs/
  pj/ ...                              # PJ0 runs (unchanged)
  pj1/                                 # NEW — PJ1 arena run JSON
```

---

## 7. Implementation steps

1. **Arena layout + `build_arena` (rung 3 core)** — new index helpers, two germ lines + two body registers
   on a shared track, walk + collision layers, three `interaction` modes. `pj_qalife.py`; `build_germsoma`
   untouched.
2. **Arena static analyzers** — `arena_witness_qubits`, `bipartite_cut_qubits`, `body_site_qubits`,
   `arena_coupling_report` (per-organism Static Test 1 + no-`if(contact)` check).
3. **Extend `--selftest`** — the five arena checks (§6.1) at W{2,4,12}. Iterate to `SELFTEST PASS`.
4. **Arena `main()` static CLI** — `--arena --dump-circuit` prints the circuit + correctness report per arm.
5. **New `code/pj1_run_arena.py`: `build_measured_arena` + count reductions** — H germ only + bodies in Z;
   joint/cut/per-lineage witness, separable null, occupancy from one circuit. Imports PJ0 infra
   (`gated_chain`, `qrng_thetas`, `schedule_with_selective_dd`) — no edit to `pj_run_qalife.py` (Q5).
6. **Sim path + coupling sim-scan (I1a)** — `--sim` frame×arm sweep; `--scan-coupling` locates the φ regime;
   sim-only contact entropy overlay.
7. **HW path** — imported `schedule_with_selective_dd` called with both germ lines (AC-PJ1.8); `gated_chain` +
   QRNG (angles + coll_site) fail-closed; `FRAMES_HW`/`STEPS_HW` few (Q3); schema to `research_runs/pj1/`.
8. **`analysis/pj1_render.py`** — port the picked wave-bars HTML, inject banked frames → self-contained
   `research/pj1_arena/index.html`; 3-arm witness PNG.
9. **Live W12 run + bank** (OQ-3) — three arms on least-busy Heron-r2; render the demo from the live data;
   write `CORRECTNESS.md` + `CONCLUSION.html`.

---

## 8. Manual verification (no tests; static + sim + one live run — CD-7)

- `python code/pj_qalife.py --arena --selftest` → five arena checks `OK` at W{2,4,12}, `SELFTEST PASS`,
  exit 0. Also `python code/pj_qalife.py --selftest` (PJ0) still passes (byte-stable).
- `python code/pj_qalife.py --arena --width 12 --track 6 --interaction soma_soma --frame 4 --dump-circuit`
  → per-organism qubit-disjoint (body↔germ) = **yes**, no measurement-conditioned gate on the body path,
  joint-witness set = both germ lines, XX+YY collision gates present at shared sites.
- `... --interaction germ_routed --dump-circuit` → per-organism Static Test 1 = **no** (a germ-coupling gate
  present) — the A/B contrast.
- `python code/pj1_run_arena.py --width 4 --track 5 --frames 24` (no `--backend` = sim) → banks the three
  arms; `pass_through` joint witness ≈ separable null, contact entropy ≈ 0; `soma_soma` contact entropy rises
  on overlap, joint witness ≥ null (report sign/size); `germ_routed` joint witness collapses vs `soma_soma`.
- `python code/pj1_run_arena.py --scan-coupling --width 4 --track 5` → joint witness vs φ; confirm a
  macroscopic (non-perturbative) regime exists (I1a) before HW.
- `python analysis/pj1_render.py --run-glob 'research_runs/pj1/*sim*.json'` → opens
  `research/pj1_arena/index.html`; arms toggle, bodies approach/meet/part smoothly, meters update; 3-arm PNG
  written.
- Inspect the **scheduled** HW circuit → selective DD on **both** germ lines only, bodies DD-free (AC-PJ1.8).
- Live (developer, Q2): `python code/pj1_run_arena.py --backend <heron> --width 12 --track 6 --frames 6
  --steps <few> --shots 8192` (QRNG env set) → three arms banked to `research_runs/pj1/`; render from live
  data.
- Confirm `qalife.py`, `run_qalife.py`, `pj_run_qalife.py` unchanged (`git diff` empty); PJ0 sim reproduces.

---

## 9. Risks

- **I1 — joint witness tiny/smeared (biggest).** A long `⟨X^⊗2W⟩` string decays geometrically; a weak
  coupling only perturbs two near-independent GHZ chains → joint sits just above the null. Mitigations
  (baked into ACs): sim-scan φ for the macroscopic regime (AC-PJ1.3/step 6); report the **A|B bipartite cut**
  witness as the tighter certificate (I1b); start small W to prove nonzero; ride selective DD. **Honest
  fallback:** joint-witness-at-null is a reported result — the spectacle + per-lineage witnesses + the PJ0
  witness underneath still stand (division of labour: claim in PJ0, wow in PJ1).
- **I2 — depth vs coherence.** Each frame adds walk+collision depth; `frames×(walk+collision)` erodes the
  witness. Mitigations: cheapest primitive (single `rxx+ryy`, ~1–2 CX — I2a); few HW frames (`FRAMES_HW`
  sparse, OQ-2); DD in idle windows; pick the frame(s) near peak overlap for the HW witness measurement.
- **Qubit budget.** 2×(W12 germ + track6 body + 1 trait) = 2×19 = **38 qubits** — fits the 107-clean-chain
  comfortably (PJ0 reached 100). Larger track or L>2 approaches the wall; `gated_chain` fail-closes.
- **Encoding (resolved OQ-1) — unary.** XX+YY hopping/exchange is site-local → **unary** track (what the
  picked visual uses); binary would need adder-based walks + a non-site-local collision (deeper → worse for
  the witness, I2) and would not match the renderer. Built unary; binary is the leaner fallback only if the
  track must grow past ~10 sites.
- **Occupancy + witness co-measurement.** Bodies measured in Z, germ in X, same circuit — valid (disjoint
  qubits, independent bases). Verified by `--dump-circuit`.
- **Contact meter is sim-only.** Entanglement entropy needs tomography on HW → banked from statevector sim,
  labelled sim-only (OQ-4). The HW-measured contact evidence is instead the joint-witness lift + occupancy
  overlap.
- **QRNG fail-closed / PJ0 regressions.** Reuse the PJ0 fail-closed gating; keep `organisms=1` byte-stable;
  `--selftest` (PJ0) must stay green.

---

## 10. What PJ2 / later rungs pick up

Rung 5 (differential reproduction: controlled-clone gated on `trait_q`) and rung 6 (scale L→4) extend the
arena builder's organism loop + the `# PJ1-rung5` marker without a rewrite. The energy-reserve resource
qubit and QRNG-chosen multi-pair encounters generalize the two-body collision. The joint-witness result
(I1) from this ticket sets whether the arena's quantum claim is pursued (chase the A|B cut) or the spectacle
carries it (division of labour).

---

## 11. Open questions — ALL RESOLVED (developer, 2026-09-13)

- **OQ-1 (soma encoding) — RESOLVED: unary one-hot, `track=6`.** XX+YY is site-local → unary (what the
  picked visual uses). Build a **unary track of 6 sites/organism** (6 body qubits), one excitation = the
  body; `traits=1` (diagonal alive/energy + rung-5 hook). Binary stays the documented leaner-alternative only
  if the track must grow. Budget at W12×2: `2×(12+6+1)=38` qubits — fits the clean chain.
- **OQ-2 (hardware frame count) — RESOLVED: sim full, HW sparse; developer runs HW.** Full-resolution frames
  in sim (`FRAMES_SIM≈36`, smooth demo); a **few measured frames** on HW (`FRAMES_HW≈6–8`), concentrated on
  the collision; the demo interpolates. The **developer executes the hardware runs**.
- **OQ-3 (live W) — RESOLVED: W12 / track=6, few steps.** Proof-of-concept at the real anchor **W12,
  track=6**, but with **few life-cycle steps + few frames** so the two organisms interact in the fewest ops
  that show contact — **saves QC time** (`STEPS_HW` small). W6×2 remains available as an even-cheaper first
  sign-check if wanted.
- **OQ-4 (contact meter on HW) — RESOLVED: sim-only, labelled.** Entanglement entropy banked from
  statevector sim as the demo overlay; HW-measured contact evidence = joint-witness lift + occupancy overlap.
- **OQ-5 (extend vs fork) — RESOLVED: extend model, new driver file.** `build_arena` etc. **extend
  `pj_qalife.py`** (shared model). The arena **run logic goes in a NEW `code/pj1_run_arena.py`** (imports PJ0
  infra by name, no edit) so `pj_run_qalife.py` / PJ0 stay byte-stable and **easily recreatable**.
- **OQ-6 (primary certificate) — RESOLVED: headline whatever best proves non-classicality.** Spectacle-first;
  headline the **A|B bipartite-cut witness** (directly certifies A–B entanglement, **no classical
  surrogate** = the "can't be replicated" claim), with the global `⟨X^⊗2W⟩` + the separable-null contrast
  reported alongside in the demo.

---

## 12. Ground rules honored

- Every AC traces to `P3-candidate-movess.md` (ladder rungs 3–4, §PJ1 core arena, I1–I3/I9); none invented.
- Concrete file paths + line-grounded source references throughout (§5, §6).
- Epic cross-cutting decisions applied (§4); the CD-1 in-place extension is stated.
- Rung 5 (reproduction), rung 6 (L>2), teleport (I9), mid-circuit selection kept out of scope (§3); the
  builder is structured to admit them without a rewrite.
- Strict types + PEP-8 for all new code; no raw SQL / templates (N/A).
- No tests (CD-7): verification is static `--selftest` + `--dump-circuit` + `--sim` + one live run + written
  conclusion.
- `qalife.py` / `run_qalife.py` byte-stable; PJ0 `build_germsoma` + `organisms=1` byte-stable.
- The locked visual (`pj1Concepts/4_wave-bars_PICKED.html`) is the demo contract (AC-PJ1.7).
- `Status: Draft` — the developer flips to Approved.

---

## 13. Post-implementation (2026-09-13)

**Built.** The arena model (`code/pj_qalife.py`, +~290 lines alongside PJ0, `build_germsoma`/`organisms=1`
untouched): `build_arena` (two germ/soma organisms on a shared unary track, three interaction arms), the
walk/collision layers, the arena static analyzers (`arena_witness_qubits`, `bipartite_cut_qubits`,
`body_site_qubits`, `arena_coupling_report`), five arena `--selftest` checks, and an `--arena` CLI. The new
arena driver `code/pj1_run_arena.py` (build + sim + HW path, `reduce_frame`, `contact_entropy_sim`,
coupling sim-scan, `schedule_arena_selective_dd`, PJ1 run schema → `research_runs/pj1/`). The renderer
`analysis/pj1_render.py` (banked JSON → self-contained wave-bars `index.html` + 3-arm witness PNG). Banked
artifacts in `research/pj1_arena/` (index.html, PNG, circuits/, CORRECTNESS.md, CONCLUSION.html).

**Result (sim, W4/track5).** `none`: joint witness +1.00, contact 0 at every frame. `soma_soma`: joint
+1.00 (germ survives the collision), contact-entropy 0→~1.59 bits **only on overlap** (the emergent-contact
proof); but the **A|B germ cut witness stays at 0** across the encounter and across φ∈[0,π] — the collision
entangles the *bodies*, not the *germ lines* (I1's predicted honest outcome; flagship witness was upside,
not obligation). `germ_routed`: joint witness **collapses** +1.00 → −0.39 — the Weismann kill-switch, now
cross-organism.

**Deviations from the plan (both forced, documented).**
1. **Selective DD re-implemented in the new driver** (`schedule_arena_selective_dd`) rather than
   "generalizing PJ0's `schedule_with_selective_dd`" as §6.2 assumed. That function derives its DD target
   internally from `pj.witness_qubits(width, has_bath)` (PJ0 layout, one organism) and takes no qubit-set
   argument — it cannot address the arena's two germ lines under the different arena layout without editing
   `pj_run_qalife.py`, which Q5 forbids. The new pass is byte-identical except it targets
   `arena_witness_qubits` (both germ lines). This is the only way to satisfy AC-PJ1.8 **and** Q5.
2. **Sim uses a statevector Aer backend, not PJ0's density-matrix `SIM`.** The arena is fully unitary (no
   bath, no damping — CD-8), so statevector is exact and does not double the qubit budget; density_matrix
   would halve the reachable sim W for no benefit. Contact entropy + sim counts are capped at 26 qubits
   (`_SV_MAX_QUBITS`); larger W is HW-only, as intended.

**Follow-ups for the developer.**
- **Live W12/track6 Heron-r2 run (AC-PJ1.10)** is yours (Q2/OQ-2): `python code/pj1_run_arena.py --backend
  <heron> --width 12 --track 6 --frames 6 --shots 8192` (QRNG env set). Then re-render from the live JSON:
  `python analysis/pj1_render.py --run-glob 'research_runs/pj1/*<heron>*.json'`.
- Pre-existing (not touched by PJ1): `analysis/plot_baseline.py` references `q4._x_string_op` and
  `q4.witness_ideal_by_gen`, neither of which exists in the current `qalife.py` — that plot script would
  error if run. Out of scope here; flagged only.
