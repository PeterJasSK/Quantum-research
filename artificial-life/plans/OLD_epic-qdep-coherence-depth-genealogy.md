# Epic: QDEP — Coherence Depth of an Inherited-Entanglement Genealogy

**Slug:** qdep-coherence-depth-genealogy
**Stages (this epic):** Stage 0, Stage 1, Stage 2, Stage 3, Stage 4 (5 plans, this file)
**Source specs:** `artificial-life/plans/qdep-1-coherence-depth-genealogy.md`, `artificial-life/plans/QDEP_Living_Genealogies.md`
**Borrows from:** `QuantumLife/code/` (infrastructure copied, not imported)
**Author:** Claude (Opus)
**Date:** 2026-08-19
**Status:** Approved

> One combined file: this epic plan (§1–§9) followed by **five full stage plans** (§10 Stage 0 → §14 Stage 4).
> Stages 0–3 each ship a **separate runnable Python file** in `artificial-life/code/`; Stage 4 aggregates and writes up.

---

## 1. Why this epic exists

The QDEP *Living Genealogies* spec (`QDEP_Living_Genealogies.md`) is a broad program — self-replication,
mutation, interaction, death, teleported non-local gates, scale to ~102 qubits. `qdep-1` carves the one
falsifiable spine out of it: **how many generations of coherent quantum inheritance can Heron r2 sustain
before a matched classical measure-and-resend surrogate reproduces the lineage's cross-generational trait
correlation within statistical error?** The headline is a single integer **g\*** with error bars.

This is deliberately the *temporal twin* of the completed QuantumLife study, which measured **spatial**
connected correlation `c(d)` across qubits within one generation. Here we re-aim the exact same trusted
machinery at **temporal** `C(g)` across generations down one lineage — orthogonal axis, same tooling.
Every claim is a measured number matched against a matched separable surrogate, so the honesty invariant
holds throughout: *if the separable surrogate can fake it, it is plumbing, not inherited quantum life.*

User-visible outcome: an IEEE QCE short-paper-grade result — one figure (two `C(g)` decay curves, quantum
solid above classical dashed, error bands, a vertical `g*` marker) and one defended claim, plus a Stage-3
extension number **Δg\*** = extra coherent generations bought by teleport-routing over SWAP-routing on the
same chip. Every stage is a checkpoint that must pass before the next; scale-up rests on a verified spine.

---

## 2. Stages in this epic

Not GitHub tickets — the epic decomposes into 5 sequential stages, each a plan in this file with its own
runnable artifact. IDs (S0…S4) are referenced throughout.

| ID | Stage | Python artifact | Depends on | One-line summary |
|----|-------|-----------------|------------|------------------|
| S0 | Reproduce | `artificial-life/code/stage0_reproduce.py` | none | Rebuild the 2018 single-lineage result with exact operators `M(θ)`, `U_M(θ)`, `⟨σ_z⟩_p`; noiseless-sim agreement proves the toolchain. |
| S1 | Port + temporal C(g) + surrogate | `artificial-life/code/stage1_temporal.py` | S0 | Re-aim `two_point_correlation` from spatial `c(d)` to temporal `C(g)`; add measure-and-resend surrogate arm; report small-scale g\*. |
| S2 | Scale big, not noise | `artificial-life/code/stage2_scale.py` | S1 | Grow generations G (and lineage width) tracking where the quantum-vs-classical gap dies; ideal-clone confound curve; g\* with error bars. |
| S3 | Break the SWAP ceiling | `artificial-life/code/stage3_teleport.py` | S2 | Swap `_swap_cx` (O(distance) depth) for `_teleport_cx` (constant depth); measure Δg\* = extra coherent generations from teleport routing. |
| S4 | Write-up & evaluate | `artificial-life/code/stage4_evaluate.py` | S0–S3 | Aggregate all stage runs, emit THE figure + fidelity table + honesty-invariant check, draft the IEEE short paper. |

---

## 3. Cross-cutting decisions

Decided once for the whole epic. Every stage plan below respects these.

- **CD-1 Copy, don't import.** Per user direction, copy the load-bearing QuantumLife modules into
  `artificial-life/code/` rather than importing across projects. Copy: `layout.py` (`best_chain`, `_pull`),
  the `two_point_correlation` / `bond_correlations` / `field_stats` / `next_belief` helpers, the
  `run_sim` surrogate producer, `_teleport_cx` + `_swap_cx` + `_entangle` + `resolve_bonds`, and the
  `sim_ideal_sign.py` noiseless-reference pattern. Keep provenance comments (`# ported from QuantumLife/code/<file>`).
- **CD-2 `pipeline_common` stays an external dependency.** `pipeline_common` is **not** in QuantumLife —
  it lives in the sibling `CalibrationGuidedHighYieldQRNG/code` and supplies `connect`, `run_sampler`,
  `qpu_seconds`, `timestamp`, `Sampler`, `SHOTS_PER_JOB`. Stage files add it to `sys.path` the same way
  QuantumLife does. Do **not** copy it (it is the submission/backend layer, shared and maintained upstream).
- **CD-3 Temporal axis is the whole novelty.** Reuse the connected-correlation math verbatim but index by
  **generation g**, not qubit distance d. `C(g) = ⟨T₀ T_g⟩ − ⟨T₀⟩⟨T_g⟩`, normalized `C(g)/C(0)`, where
  `T` is the **phenotype** trait observable `⟨σ_z⟩_p` (Q3 resolved: phenotype via the genotype→phenotype
  ancilla map of QDEP §5, not the raw genotype). `T₀` and `T_g` are read **per shot via mid-circuit
  measurement** down a single lineage (Q2 resolved: mid-circuit + feed-forward dynamic circuit, one lineage
  per shot — truest to the lineage, accepts feed-forward latency). This is the one place the ported math
  changes meaning.
- **CD-4 Two matched arms, one schedule.** Quantum (coherent approximate clone) vs classical
  (measure-and-resend, separable, `run_sim`-style). Hold fixed across arms: population = 1 line, G,
  mutation-angle schedule, the **same** entropy stream/seed, measurement settings, shot budget. Swap only
  the inheritance channel. Seeds shared: repeat `r` uses `seed = base_seed + r` in *both* arms (QuantumLife
  convention) so the environment is identical.
- **CD-5 g\* definition (headline).** `g* = max g such that |C_q(g) − C_cl(g)| > k·σ`, default `k = 2`
  (report `k=3` too). `σ` from `--repeats` independent seeded runs (QuantumLife error-bar convention).
  `Δg* = g*(teleport) − g*(swap)` at matched settings (S3 only).
- **CD-6 Cloning-confound control is mandatory.** Every hardware `C_q(g)` is reported alongside the
  **ideal noiseless-sim** `C(g)` (statevector, exact approximate-clone, no decoherence) so approximate-cloning
  decay is separated from hardware decoherence. This is the `sim_ideal_sign.py` pattern re-aimed to C(g).
- **CD-7 Q-EaaS provenance: certified from S1 (resolved, was Q1).** QuantumLife does **not** consume QRNG —
  its seeding is plain `random.seed(args.seed)`; only "provenance" is `meta.calibration = read_snapshot(backend)`.
  So the signed-receipt mutation stream is genuine new work, not a borrow. **Decision:** `QEAAS_API_KEY` is
  available in env, so the certified Q-EaaS entropy stream is wired **from S1 onward**. **Copy** the existing
  `QRNGClient` (`DNSPoisonRace/testbed/draw/qrng_client.py`, structural twin in
  `TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py`) into `artificial-life/code/qrng_client.py`:
  `GET /v1/random/bytes?size=&format=`, header `X-API-Key`, returns `QRNGResponse{request_id, data,
  entropy_epoch, timestamp, receipt}`. Each mutation angle is derived from fetched bytes and its `receipt` +
  `request_id` logged (§4 `meta.entropy_provenance`). S0 stays sim-only on `random.seed` (no mutation-provenance
  claim); S1–S4 use the certified stream. Fail-closed policy: if `QRNGUnavailable` is raised, the run aborts
  rather than silently falling back to PRNG (else M7 provenance is a lie).
- **CD-8 No death, no interaction, no teleport in the minimal build.** Per `qdep-1` §Method: the minimal
  spine (S0–S2) is inheritance only — single linear lineage, one observable, two arms. Teleport enters only
  at S3; population/death/interaction are explicitly out of scope for this epic (they are the follow-on QDEP
  program). Keep the code paths absent, not stubbed, in S0–S2. (Q4 resolved: minimal build is **population = 1,
  one big single lineage**; S2 grows G to find the SWAP-routed coherence limit empirically before deciding
  whether parallel lineages are worth adding for tighter statistics.)
- **CD-9 Sim-first, hardware-confirm, every stage.** Fix the pipeline in `--sim`, then confirm on Heron r2.
  Same `--sim` branch structure as QuantumLife's `run_once`.

---

## 4. Shared data model (run/summary JSON schema)

All stages persist runs mimicking QuantumLife's schema so Stage 4 can aggregate uniformly. Output dir
constant `OUTPUT_DIR = ../research_runs` (relative to `artificial-life/code/`), naming
`<TAG>_<backend|sim>_seed<K>_<ts>_run.json` and `<TAG>_<backend|sim>_<ts>_summary.json` (`ts = timestamp()`).

| Field | Level | Change vs QuantumLife | Introduced by | Consumed by |
|-------|-------|-----------------------|---------------|-------------|
| `meta.study = "coherence-depth-genealogy"` | run+summary | new study tag | S0 | S4 |
| `meta.arm ∈ {"quantum","classical","ideal"}` | run | new — names the inheritance channel | S1 | S2,S3,S4 |
| `generations[].gen` | run | reused as-is | S0 | all |
| `generations[].trait_sigmaz` | run | new — `⟨σ_z⟩_p` per generation (the 2018 lifetime observable) | S0 | S1,S4 |
| `generations[].fidelity_vs_ideal` | run | new — per-gen fidelity to noiseless model | S0 | S4 |
| `correlation_temporal.C` / `.c` / `.C0` | run | `two_point_correlation` re-indexed by g (CD-3) | S1 | S2,S3,S4 |
| `logical_depth` | run | reused — carries the constant-vs-O(distance) claim | S3 | S4 |
| `per_generation[].C_g_mean/std` | summary | temporal `C(g)` mean±σ over repeats | S1 | S4 |
| `gstar` (k=2, k=3) | summary | headline integer + which k | S1 | S4 |
| `delta_gstar` | summary | S3-only: teleport − swap | S3 | S4 |
| `meta.entropy_provenance` | run | new (CD-7): certified Q-EaaS from S1 — `{source:"qeaas", request_id, receipt, entropy_epoch, timestamp}` per mutation | S1 | S4 |
| `meta.calibration = read_snapshot(backend)` | run | reused verbatim | S0 | S4 |

---

## 5. Metrics / success criteria (the measurable spine)

Every stage lands a number, mimicking the QuantumLife `c(d)` study's rigor.

- **M1 Per-generation fidelity vs ideal noiseless model** — S0 gate: reproduce 2018-level agreement at g=1.
- **M2 Temporal connected correlation `C(g)`** — quantum arm vs surrogate, normalized `C(g)/C(0)`, with
  error bands from `--repeats`.
- **M3 g\*** = max g where `|C_q(g) − C_cl(g)| > k·σ` (k=2 headline, k=3 reported). The single number.
- **M4 Ideal-clone `C(g)` confound curve** (CD-6) — separates approximate-cloning decay from decoherence.
- **M5 Δg\*** (S3) — extra coherent generations from teleport routing over matched SWAP routing.
- **M6 `logical_depth` per generation** (S3) — evidences constant-depth teleport vs O(distance) SWAP.
- **M7 Entropy provenance** — every mutation traceable to a signed Q-EaaS receipt via the certified stream, from S1 (CD-7).

**Falsification:** if at every accessible G the surrogate reproduces `C(g)` within k·σ, `g* = 1` and the
"inherited entanglement is classically-inimitable on Heron r2" claim is falsified for current devices —
reported as a hard coherent-generation-budget number (still publishable, per `qdep-1` Value-if-null).

---

## 6. Hardware / platform considerations

- Target backend: least-busy IBM **Heron r2** (auto-select via `pipeline_common.connect`, matching
  QuantumLife `--backend` default None). `best_chain` picks the SWAP-free low-error qubit chain.
- Dynamic circuits (mid-circuit measure + classical feed-forward) are required for temporal `T₀,T_g`
  readout (CD-3) and for teleport (S3). QuantumLife's `run_hw` already handles the dynamic-circuit path
  and reads both `c` and `tel` registers — copy that.
- IBM-account access risk is a named epic risk (`qdep-1` score note). Sim-first (CD-9) de-risks: S0–S2 are
  fully defensible from `--sim` + ideal statevector even before hardware time lands.
- Qubit/depth budget grows fast; **noise is not a fitness function** (QDEP §1). S2 scale-up keeps selection
  an explicit measured op and every mutation entropy-traced — "bigger" = more coherent generations under
  control, never more entropy dressed as biology.

---

## 7. Implementation order

Strict sequence — each stage is a checkpoint gating the next (`qdep-1` Staged ambition):

1. **S0** — must hit M1 (2018 agreement in noiseless sim) before anything else. Fixes operators + toolchain.
2. **S1** — re-aim correlation to C(g), add surrogate, bank a small-scale g\* in sim then hardware.
3. **S2** — scale G with the ideal-clone confound control; g\* with error bars is the paper's core result.
4. **S3** — only after g\* is banked: teleport vs SWAP, measure Δg\*.
5. **S4** — aggregate all of S0–S3, produce the figure + paper. Can start scaffolding early but needs S0–S3 runs.

S0 is the only stage with no dependency; everything else is linear. No stage is independently pickup-able
except S0.

---

## 8. Open questions (epic-wide)

- [x] Q1 (CD-7): **RESOLVED** — `QEAAS_API_KEY` is in env; wire the certified Q-EaaS signed-receipt mutation
  stream **from S1** (S0 stays sim-only on `random.seed`). Copy the existing `QRNGClient`. Fail-closed on
  `QRNGUnavailable`. Folded into CD-7 and M7.
- [x] Q2 (CD-3): **RESOLVED** — mid-circuit measurement of `T_g` per generation (dynamic circuit + feed-forward,
  one lineage per shot). Accepts feed-forward latency for lineage fidelity. Folded into CD-3.
- [x] Q3 (CD-3): **RESOLVED** — trait = **phenotype** `⟨σ_z⟩_p` via the genotype→phenotype ancilla map (QDEP §5).
  S0 must fix that ancilla map. Folded into CD-3.
- [x] Q4 (S2): **RESOLVED** — start with population = 1, one big single lineage; grow G to **find the SWAP
  limit empirically** (how deep before the gap dies), then decide whether parallel lineages are needed for
  tighter σ. Test-first, decide-after. Folded into CD-8 note and S2.
- [ ] Q5 (S3): **DEFERRED to `/plan-feature stage3`** — `--bond-dist` / `--anchors` mapping from spatial chain
  geometry onto the temporal generational chain.
- [ ] Q6: **DEFERRED to `/plan-feature`** — shot budget per generation for stable g\* statistics (QDEP §11).

---

## 9. Per-stage briefs

Short orientation per stage. Full plans follow in §10–§14.

### S0 — Reproduce — `stage0_reproduce.py`
- **Delivers:** the 2018 single-lineage operators rebuilt exactly; noiseless-sim agreement (M1) as the fixed reference the hardware run is judged against.
- **Depends on:** none. **Borrows:** `sim_ideal_sign.py` statevector pattern, genome decode helpers.
- **Out of scope:** correlation metric, surrogate, hardware run (that's S1+).

### S1 — Port + temporal C(g) + surrogate — `stage1_temporal.py`
- **Delivers:** temporal `C(g)` (M2), measure-and-resend surrogate arm, small-scale g\* (M3) in sim then hardware.
- **Depends on:** S0. **Borrows:** `two_point_correlation` (re-indexed), `run_sim`, `run_once`/`--sim` branch, `layout.best_chain`, `run_hw`, argparse conventions.
- **Out of scope:** scaling G, teleport, ideal-confound-vs-hardware sweep.

### S2 — Scale big, not noise — `stage2_scale.py`
- **Delivers:** g\* with error bars across growing G (M3), ideal-clone confound curve (M4), entropy provenance (M7).
- **Depends on:** S1. **Borrows:** repeats/aggregation loop, summary.json writer, ideal statevector reference.
- **Out of scope:** teleport routing (S3), population/death/interaction (whole-epic scope, CD-8).

### S3 — Break the SWAP ceiling — `stage3_teleport.py`
- **Delivers:** Δg\* (M5) and `logical_depth` evidence (M6) — teleport constant-depth bond vs SWAP-ladder O(distance).
- **Depends on:** S2 (g\* banked). **Borrows:** `_teleport_cx`, `_swap_cx`, `_entangle`, `resolve_bonds`, `bond_correlations`, teleport `run_hw` (`tel` register).
- **Out of scope:** anything beyond the matched teleport-vs-swap comparison; ~102-qubit scale-out.

### S4 — Write-up & evaluate — `stage4_evaluate.py`
- **Delivers:** THE figure (two `C(g)` decay curves + g\* marker), fidelity table (M1), honesty-invariant check, IEEE short-paper draft.
- **Depends on:** S0–S3 runs. **Borrows:** QuantumLife summary/figure conventions.
- **Out of scope:** new physics; it only aggregates and writes up.

---
---

# STAGE PLANS (5)

Each Stage 0–3 plan targets one runnable Python file that reads `--sim`/hardware and writes
`research_runs/*.json`. Stage 4 reads those and writes figures + paper. All respect §3 cross-cutting decisions.

---

## 10. Stage 0 — Reproduce (`stage0_reproduce.py`)

**Goal:** rebuild the Alvarez-Rodriguez et al. (2018) single-lineage result with the *exact* operators, and
hit noiseless-sim agreement (M1). This proves the toolchain and fixes the reference the hardware run is judged
against. No correlation metric, no surrogate, no hardware yet.

**Operators (verbatim from spec §6 / wiki map):**
- Mutation `M(θ) = [[cosθ, sinθ], [sinθ, −cosθ]]` — single-qubit rotation on offspring genotype.
- Approximate clone `U_M(θ)` — fixed entangling unitary, parent genotype → fresh ancilla (no-cloning ⇒ variation).
- Phenotype `⟨σ_z⟩_p` — the "lifetime" observable; expected exponential decay across generations.

**Acceptance criteria (from `qdep-1` Stage 0 + QDEP §9/§10):**
- AC-S0.1 (verbatim, `qdep-1`): "Rebuild the 2018 single-lineage result with the *exact* operators from the paper/wiki: `M(θ)` mutation, `U_M(θ)` imperfect clone, `⟨σ_z⟩_p` lifetime. Success = the noiseless-sim agreement the 2018 work reported."
- AC-S0.2 (verbatim, QDEP §9): "Fidelity vs. ideal model per generation (the 2018 work reported close agreement at small scale — reproduce that first)."
- AC-S0.3: the `⟨σ_z⟩_p` phenotype shows the expected exponential "lifetime" decay across generations in noiseless sim.

**Build notes:**
- **Copy** the `sim_ideal_sign.py` statevector pattern (`AerSimulator(method="statevector")`, `unit_test()`
  logical-equivalence style) into `stage0_reproduce.py`; add a `unit_test()` that verifies `U_M`/`M(θ)`
  against the paper's matrices, and an `ideal_lifetime(gens)` that reports `⟨σ_z⟩_p` per generation.
- Copy genome decode helpers from `genome.py` only if the genotype encoding is reused; the 2018 protocol is
  a single genotype qubit + ancilla, so a minimal register is fine (CD-8).
- Persist a run.json with `meta.study`, `meta.arm="ideal"`, `generations[].trait_sigmaz`,
  `generations[].fidelity_vs_ideal` (§4).
- CLI (borrow conventions, CD-2): `--generations --shots --seed --name` (+ `--sim` default true here since
  Stage 0 is sim-only). Add `sys.path` hook for `pipeline_common` even if unused, for parity.

**Deliverable:** `artificial-life/code/stage0_reproduce.py` runnable as `python stage0_reproduce.py
--generations 6` → prints per-gen `⟨σ_z⟩_p` and fidelity, writes run.json. **Gate:** M1 met before S1.

---

## 11. Stage 1 — Port + temporal C(g) + surrogate (`stage1_temporal.py`)

**Goal:** re-aim the trusted QuantumLife correlation machinery from spatial `c(d)` to temporal `C(g)` (CD-3),
add the matched measure-and-resend classical surrogate arm (CD-4), and bank a small-scale g\* (M3) — sim first,
then a hardware confirm.

**Acceptance criteria (from `qdep-1` Stage 1 + §8/§9):**
- AC-S1.1 (verbatim, `qdep-1`): "Reuse the growth engine, the `--sim` classical surrogate harness, and the Heron-r2 layout pipeline — but *re-aim* the correlation tooling from QuantumLife's **spatial** `c(d)` (across qubits, one generation) to this study's **temporal** `C(g)` (across generations, one lineage). Same trusted machinery, orthogonal axis. Add the measure-and-resend surrogate arm and run the g\* comparison at small scale."
- AC-S1.2 (verbatim, QDEP §8 surrogate): "Same population size, same generation count, same mutation rate/schedule, same selection thresholds, same random seeds from the *same* Q-EaaS stream. Replace every coherent inheritance/interaction with a **measure-and-resend** step: measure the parent's trait, send classical bits, re-prepare a separable state from those bits."
- AC-S1.3: `C(g)` computed for both arms with error bands from `--repeats`; g\* (M3, k=2 and k=3) reported.

**Build notes:**
- **Copy** `two_point_correlation` and rename/re-index to `temporal_correlation(traits_by_gen, G)` computing
  connected `C(g) = ⟨T₀T_g⟩ − ⟨T₀⟩⟨T_g⟩`, `c(g)=C(g)/C(0)`, returning `{"C","c","C0","gstar_input"}` (§4).
  Keep the connected-correlation math identical; only the index changes from qubit-distance d to generation g.
- **Copy** the `run_sim` independent-qubit producer as the surrogate base, then adapt to measure-and-resend:
  per generation measure parent trait → classical bit → re-prepare separable child (this yields `C(g>0)≈0` by
  construction, exactly like QuantumLife's `run_sim` yields `c(d>0)≈0`). Quantum arm = coherent `U_M` clone from S0.
- **Copy** `run_once` `--sim`/`run_hw` branch structure and `layout.best_chain`; copy `run_hw` (dynamic-circuit
  aware, reads `c` register). Readout is mid-circuit `T_g` per generation with feed-forward (Q2 resolved) —
  trait = phenotype `⟨σ_z⟩_p` via the S0 ancilla map (Q3 resolved).
- **Wire certified Q-EaaS from here (CD-7, Q1).** Copy `qrng_client.py` into `artificial-life/code/`; construct
  `QRNGClient(base_url, api_key=os.environ["QEAAS_API_KEY"])`. Draw each mutation angle from fetched bytes
  (`fetch(size=…, fmt="hex")` → map bytes to the rotation angle), and log `request_id`+`receipt`+`entropy_epoch`
  into `meta.entropy_provenance` (§4). Fail-closed: abort on `QRNGUnavailable`, never silently PRNG-fallback.
  Both arms consume the **same** Q-EaaS byte stream at matched positions so the schedule is identical (CD-4).
- CLI: `--generations --shots --seed --repeats --backend --name --sim --arm {quantum,classical,both}`.

**Deliverable:** `artificial-life/code/stage1_temporal.py`; `--sim` run produces both arms' `C(g)` and a g\*;
hardware confirm reproduces at small G. **Gate:** clean small-scale g\* in sim before S2.

---

## 12. Stage 2 — Scale big, not noise (`stage2_scale.py`)

**Goal:** grow generations G (and optionally lineage width, Q4) toward the coherence ceiling, tracking where
the quantum-vs-classical gap dies — with the ideal-clone confound control (M4) mandatory. This produces the
paper's core number: g\* with honest error bars, decoherence separated from approximate-cloning decay.

**Acceptance criteria (from `qdep-1` Stage 2 + §Metrics):**
- AC-S2.1 (verbatim, `qdep-1`): "Grow G (generations) and lineage width toward the QDEP ceiling **only as coherence allows**, tracking where the quantum-vs-classical gap dies. The governing rule (QDEP §1): *noise is not a fitness function.* Every scale-up keeps selection an explicit **measured** operation and every mutation tied to a signed Q-EaaS receipt."
- AC-S2.2 (verbatim, `qdep-1` Metrics): "Cloning-fidelity confound control: report the ideal-clone `C(g)` from a noiseless sim so approximate-cloning decay is separated from hardware decoherence."
- AC-S2.3 (verbatim, `qdep-1` Metrics): "Entropy provenance: every mutation traceable to a signed Q-EaaS receipt."
- AC-S2.4: g\* (M3) reported with mean±σ over `--repeats`, at each G, quantum vs surrogate vs ideal.

**Build notes:**
- **Copy** the repeats/aggregation loop + summary.json writer pattern from QuantumLife `main()` (per-generation
  `mean/std` over seeded repeats; `run_files` list). Emit `per_generation[].C_g_mean/std` and top-level
  `gstar` (k=2,k=3) (§4).
- **Copy** the `sim_ideal_sign.py` statevector reference re-aimed to C(g): a `ideal_temporal_correlation(G)`
  giving the noiseless exact-clone `C(g)` curve (M4). This runs as `meta.arm="ideal"` alongside the two hardware arms.
- CD-7 already satisfied from S1 (certified Q-EaaS via `QRNGClient`); S2 just carries it forward at scale —
  record each generation's mutation angle + `request_id`/`receipt` in run.json, fail-closed on `QRNGUnavailable`.
  At large G watch Q-EaaS request volume/quota (429 `Retry-After` handling is in the copied client).
- Keep selection an explicit measured op; **no** noise-as-fitness. No teleport, no cross-lineage interaction (CD-8).
- **Q4 resolved:** run population = 1, one big single lineage; sweep G with `--gmax` to find the SWAP-routed
  coherence limit empirically (the G at which the quantum-vs-surrogate gap dies). Keep `--width` (parallel
  independent lineages, default 1) available but **off by default** — only turn it on if σ is too loose to
  resolve g\* after the single-lineage sweep. Decide from the data, not up front.
- CLI adds: `--gmax` (sweep G up to), `--width` (parallel lineages, default 1, off unless σ demands it), `--k` (σ multiplier for g\*).

**Deliverable:** `artificial-life/code/stage2_scale.py`; produces g\* vs G with error bands and the ideal
confound curve. **Gate:** g\* banked (the headline) before attempting S3.

---

## 13. Stage 3 — Break the SWAP ceiling (`stage3_teleport.py`)

**Goal:** show that teleport-routed lineage bonds (constant depth) buy coherent generations that SWAP-routed
bonds (depth O(chain distance)) cannot, on the same chip. Headline: Δg\* (M5), evidenced by `logical_depth` (M6).

**Acceptance criteria (from `qdep-1` Stage 3 + QDEP §6.4):**
- AC-S3.1 (verbatim, `qdep-1`): "Interacting distant individuals via a SWAP ladder costs depth that *grows with chain distance* — and that depth eats exactly the coherence budget g\* depends on... Swap in the teleported long-range bond... a faithful long-range CNOT at **constant depth 9**, crosstalk-immune: distance no longer taxes depth, so lineages can go deeper / wider than SWAP permits *on the same chip*."
- AC-S3.2 (verbatim, `qdep-1`): "Attempted only after g\* is banked at small scale — Stage 3's claim is measured as **Δg\*** = extra coherent generations bought by teleport routing over the matched SWAP-routed lineage."
- AC-S3.3 (verbatim, QDEP §6.4 honesty): "the correct claim is *'constant-depth long-range interaction at the cost of ancillas and classical latency,'* **not** 'instant, free bypass of the bottleneck.'"

**Build notes:**
- **Copy** `_teleport_cx` (1 Bell pair + 2 mid-circuit measures + feed-forward `if_test`, `feedforward`/
  `herald` modes), `_swap_cx` (SWAP-ladder O(distance) baseline), `_entangle`, `resolve_bonds`,
  `bond_correlations`, and the teleport `run_hw` that reads both `c` and `tel` registers.
- Two matched runs at each G: `arm="quantum"` with `_swap_cx` routing vs with `_teleport_cx` routing, identical
  seeds/schedule/shots. Compute g\* for each, then `delta_gstar = gstar_teleport − gstar_swap` (§4, M5).
- Record `logical_depth = qc.depth()` per generation for both routings (M6): teleport ≈ constant, swap grows
  with distance. Report as evidence, and state the ancilla/latency cost honestly (AC-S3.3) — do **not** claim a free bypass.
- Resolve Q5: map the QuantumLife spatial bond geometry (`--anchors`, `--bond-dist` in slot units) onto the
  temporal lineage — i.e. which generation-to-generation bond is routed long-range.
- CLI adds (borrow teleport fork): `--bond-dist --anchors --herald --routing {swap,teleport,both}`.

**Deliverable:** `artificial-life/code/stage3_teleport.py`; produces Δg\* and per-gen `logical_depth` for both
routings. **Gate:** Δg\* measured and honesty caveat recorded before write-up.

---

## 14. Stage 4 — Write-up & evaluate (`stage4_evaluate.py`)

**Goal:** aggregate every S0–S3 run into the defended result and draft the IEEE QCE short paper. This stage
adds no physics — it reads `research_runs/*.json` and emits figures, tables, and prose.

**Acceptance criteria (from `qdep-1` THE VISUALIZATION / Thesis + QDEP §8/§9):**
- AC-S4.1 (verbatim, `qdep-1` THE VISUALIZATION): "Two correlation-decay curves, `C(g)` vs generation number: quantum arm (solid) riding above the classical measure-and-resend surrogate (dashed), error bands shaded. The curves converge and the shading overlaps at **g\*** — a single vertical marker where 'still quantum' becomes 'classically fakeable.'"
- AC-S4.2 (verbatim, `qdep-1` Metrics): "Per-generation fidelity vs the ideal noiseless model (reproduce 2018-level agreement at g=1 as the toolchain check)."
- AC-S4.3 (verbatim, `qdep-1` honesty invariant): "if a result can be reproduced by the matched separable surrogate, it is noise/plumbing, not inherited quantum life — report it as such."
- AC-S4.4 (verbatim, `qdep-1` Thesis single claim): "On Heron r2, coherent inheritance beats a matched classical measure-and-resend surrogate up to a measurable generation g\*, and we report that integer with error bars and a cloning-confound control."

**Build notes:**
- Read all `research_runs/*_summary.json` and per-arm run.json; produce THE figure: `C_q(g)` solid, `C_cl(g)`
  dashed, ideal-clone `C(g)` (M4) as a third reference curve, shaded ±σ bands, vertical marker at g\* (M3).
  Export PNG+SVG to `artificial-life/figures/` (mirror QuantumLife figure conventions).
- Emit a fidelity table (M1/AC-S4.2), a g\* summary (k=2,k=3), and the Δg\* / `logical_depth` panel from S3 (M5/M6).
- Run the honesty-invariant check (AC-S4.3): for each g, flag whether the quantum arm is within k·σ of the
  surrogate; everything at/below g\* boundary that the surrogate matches is labeled "plumbing, not quantum life."
- Draft `artificial-life/research/CONCLUSION_QDEP_COHERENCE_DEPTH.md` + a 6–8pp IEEE short-paper skeleton
  (central question, single defended claim AC-S4.4, method, figure, g\*/Δg\* with error bars, value-if-null).

**Deliverable:** `artificial-life/code/stage4_evaluate.py` + figures + conclusion write-up. **Gate:** epic complete.

---

## 15. Ground rules honored

- Every stage (S0–S4) appears in §2 and has a brief in §9 and a full plan in §10–§14.
- Every AC is quoted **verbatim** from `qdep-1-coherence-depth-genealogy.md` / `QDEP_Living_Genealogies.md`.
- No implementation detail beyond file/function targets — the "how" is left to `/plan-feature` per stage.
- Honesty invariant (CD-8, AC-S4.3) and the Q-EaaS provenance-is-new caveat (CD-7) are stated, not papered over.
- `Status: Draft` — the developer flips to Approved.
