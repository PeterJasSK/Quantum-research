# Epic: Stone-Wall Viral Genealogies — the teleport-flip on a multi-block quantum virus

**Slug:** stonewall-virus
**Phases (this epic):** Phase 0, Phase 1, Phase 2, Phase 3 (4 plans, this file)
**Source spec:** design discussion 2026-08-26 (this epic file is the spec of record)
**Successor to:** `artificial-life/code/stage4_qalife.py` + `stage4_scale.py` (QALife Month-4)
**Borrows from:** `artificial-life/code/stage3_teleport.py` (`_teleport_cx`, `_swap_cx`), `layout.py` (`best_chain`) — copied, not imported (CD-1)
**Author:** Claude (Opus)
**Date:** 2026-08-26
**Status:** Approved — **PIVOTED 2026-08-26 after P0 kill-gate (teleport headline refuted; now swap-routed).**

> **P0 RESULT (2026-08-26, `ibm_kingston` Heron-r2) — teleport-flip REFUTED, epic pivoted.** The P0 kill-gate ran
> the minimal 2-block flip test on hardware (3 runs, all agree). The teleport-routed infection bond **lost to
> swap-routing at every separation**, including the far `d=48` point predicted to be teleport's win:
>
> | d | swap signal | teleport signal | swap depth | tel depth |
> |---|---|---|---|---|
> | 2 (control) | **+0.215** ±0.019 clears | +0.058 ±0.012 clears | 28 | 29 |
> | 48 (far, predicted teleport-win) | **+0.060** ±0.015 clears | +0.029 ±0.017 **buried** | 111 | 29 |
> | 48 heralded teleport | — | **+0.000** ±0.011 dead | — | 29 |
>
> **Mechanism (decisive):** at `d=2` depths are near-equal (28 vs 29) yet teleport already craters (3.7× gap), so
> the loss is the **mid-circuit-measurement machinery itself**, not depth/distance. Live calib: `twoq_err_max`
> 0.003–0.007 vs `readout_max` 0.048 (readout ≫ 2q by 7–16×). Teleport is built on mid-circuit measurement = the
> expensive resource on Heron-r2; swap is cheap 2q gates. The constant-depth win (29 vs 111) is real but
> **irrelevant** — depth is not the cost that matters here. Heralding (drops feed-forward, keeps mid-measures)
> made it **worse** (0.029→0.000), proving feed-forward was helping and the mid-measures are the fundamental cost.
> Per-block headroom was healthy and even higher than assumed (A/B ≈ 0.44–0.56 vs 0.30), so the stone-wall
> **headroom hypothesis is refuted too**: headroom was never the bottleneck. This confirms the earlier M4/QDEP
> finding (advantage inverts on modern HW; `logical_depth` is not the routing figure of merit).
>
> **What survives:** the **connected-GHZ cross-block transmission witness works on metal, swap-routed** (signal
> 0.215 @ d=2, 0.060 @ d=48, real per-block headroom) — a genuine no-classical-surrogate quantum claim. The epic
> therefore **drops the teleport-flip (D) headline and pivots to swap-routed infection**, with the quantum headline
> now the **transmission-witness-vs-distance decay curve (B)**. Teleport is retained only as a documented negative
> baseline. Reproduce/verify P0:
> `python stage5_fliptest.py --verify research_runs/p0_hw_fliptest_ibm_kingston_20260826-134356.json` (→ CONSISTENT, STOP).

> One combined file: this epic plan (§1–§9) followed by the four full phase plans once each is specialised via `/plan-feature`.
> Phase 0–2 each ship a runnable Python file in `artificial-life/code/`; Phase 3 aggregates, writes up, and builds the web demo.

---

## 1. Why this epic exists

QALife Month-4 rebuilt the full 2018 Alvarez-Rodriguez model and delivered an honest scale result — genealogical
entanglement witness `⟨X^⊗W⟩` to **W=24 (48 qubits)** on `ibm_kingston`, the one observable with no classical
surrogate. But it had **no organism**: a bare Darwinian *structure* (one clone locus per individual, unconditional
replication, no real genome, no selection). And teleport-routing was **refuted twice** — on a single long line the
constant-depth teleport bond lost to a plain SWAP ladder because the many-body witness was already too fragile to
absorb teleport's mid-circuit-measurement error.

This epic builds something **lively** from that structure — a simplified quantum **virus** (explicitly NOT full
carbon life). The original thesis was a *teleport-flip* (constant-depth teleport bond beating a SWAP ladder across a
wide stone wall). **P0 refuted that on hardware** (see the boxed result above): on readout-dominated Heron-r2 the
teleport bond's mid-circuit measurements cost more than a swap ladder's cheap 2q gates, at every separation. The
epic pivots to what P0 *proved works on metal*:

> **PIVOTED THESIS (falsifiable):** a swap-routed quantum virus keeps a genuine, no-classical-surrogate
> **cross-block genealogical entanglement** as it infects A→B→C across wide stone walls. The quantum headline is the
> **connected-GHZ transmission witness `⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B` as a function of inter-block distance** (the
> decay curve): =1 for one genealogy connected across the wall, →0 for a measure-and-resend (classical) infector.
> P0 measured it alive at W12 across a 48-qubit wall (signal 0.060, clears 2σ). The genome staying coherent as the
> virus spreads is the vehicle; the distance-decay of that coherence is the result.

User-visible outcome: a measured **cross-block transmission-witness-vs-distance decay curve** (swap-routed; the
quantum claim, no classical surrogate) — plus a 2D environmental phase diagram (immune pressure × mutation stress)
of virus survival, and a web demo of the 3-block virus chain. The refuted teleport arm is retained as a documented
negative baseline. Population survival is narrative, not headline.

**Honesty invariant (carried from M4):** if a classical measure-and-resend surrogate can fake it, it is plumbing,
not quantum life. Population>0 / alive-count are diagonal ⟨σz⟩ = classical = story only. Only the off-diagonal
cross-block witness (B+D) is the claim.

---

## 2. Phases in this epic

Not GitHub tickets — the epic decomposes into 4 sequential phases, each a plan in this file. IDs (P0…P3) are
referenced throughout. Phase merges per user direction: original build steps (genome+selection, stone-wall layout,
chain infection) collapse into **P1**; original run steps (multi-generation, environment sweep) collapse into **P2**.

| ID | Phase | Python artifact | Depends on | One-line summary |
|----|-------|-----------------|------------|------------------|
| P0 | Flip-test (kill-gate) | `code/stage5_fliptest.py` | none | **DONE 2026-08-26.** Minimal 2-block × W12 × 1-generation infection, teleport vs swap. Teleport-flip **REFUTED** on HW (see boxed result); connected-GHZ transmission witness works **swap-routed**. Epic pivoted to swap. |
| P1 | Build the virus | `code/stage5_virus.py` | P0 | Merge of build steps: 3-locus genome `[q_witness, b1, b2]`, static 1-ancilla Darwinian selection, 3 disjoint W12 stone-wall blocks on 156q, **swap-routed** chain infection A→B→C (teleport kept as a documented negative baseline arm). `--selftest` verifies every operator. |
| P2 | Run + environment | `code/stage5_run.py` | P1 | Merge of run steps: ~9-generation multi-block run (population-survival track + cross-block **transmission-witness-vs-distance** track), then 2D environment sweep — damping γ (immune) × mutation angle (drug/stress) — to a survival/witness phase diagram. |
| P3 | Web demo + conclusion | `web/` + `research/CONCLUSION_MONTH5.md` | P0–P2 | Aggregate all runs, emit the **transmission-witness-vs-distance decay** headline figure + phase diagram + the P0 teleport-refutation negative result, write the conclusion, build the 3-block virus-chain web demo (twin of the M4 demo). |

---

## 3. Cross-cutting decisions

Decided once for the whole epic. Every phase plan below respects these.

- **CD-1 Copy, don't import.** Per standing repo rule, copy load-bearing modules into `code/` rather than importing
  across stages/projects. Copy `_teleport_cx`, `_swap_cx` from `stage3_teleport.py` and reuse `layout.best_chain`;
  reuse the operator library (`self_replication`, `mutation`, `phenotype`, aging, interaction) from
  `stage4_qalife.py`. Keep provenance comments (`# ported from stageN_*.py`).
- **CD-2 Genome architecture (decouples richness from fragility).** Individual = **G=3 genome + 1 phenotype = 4
  qubits**. Genome = `[q_witness, b1, b2]`:
  - `q_witness` — the **1 quantum locus**, carries the `|+>`-GHZ cross-block transmission witness (B). This is the
    only entangled locus; witness cost stays equal to the G=1 baseline.
  - `b1, b2` — **2 classical Z-basis loci**, carry the static fitness bits. Genome is "rich" for selection without
    eating the witness budget. Genome-internal entanglement (option E) is **OFF**.
- **CD-3 Selection = 1 fitness ancilla, static.** Compute `f(b1,b2)` into a single ancilla, measure that ancilla
  (mid-circuit) + feed-forward the replication decision. Do **not** measure all loci — first-order budget shows
  G=3 with 1-ancilla selection buys ~9 generations vs ~6 if all loci are measured. Fitness function is **static**
  (not coevolving) and fixed to **survive iff `b1=b2`** (2 of 4 genomes fit, 50% selection pressure) (Q2).
- **CD-4 One observable, one claim (pivoted).** The **connected-GHZ cross-block transmission witness**
  `⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B` (B), measured **vs inter-block distance** (the decay curve), is the **quantum
  headline** — no classical surrogate (a measure-and-resend infector drives it to 0). NB (P0 finding): the bonded
  two-point `⟨X_{A_tail} X_{B_head}⟩` is **identically zero** for a GHZ genealogy and must NOT be used; the
  per-block-product-nulled full parity is the only genuine low-... no, high-weight off-diagonal witness. The
  teleport-vs-swap crossover (D) is **retired as a headline** (refuted, P0) and kept only as a negative-result
  baseline. Population>0 / alive-count = **biology narrative only** (diagonal, classically simulable — never the
  headline).
- **CD-5 Infection topology = chain A→B→C, SWAP-ROUTED (pivoted).** Cross-block bond realised as a **SWAP ladder**
  (`_swap_cx`, O(distance), cheap 2q gates — the arm P0 proved carries the witness on Heron-r2). A teleport-routed
  arm (`_teleport_cx`) is retained **only as a documented negative baseline** for the conclusion, not the headline
  path. Reason: on readout-dominated modern HW the teleport bond's mid-circuit measurements cost more than the swap
  ladder's 2q gates (P0, 3 runs).
- **CD-6 Chain-quality gate per block.** Carry the M4 fail-closed gate (`twoq_err_max ≤ 0.05`, `readout_max ≤
  0.15`) applied to *each* block's contiguous chain independently, so witness decay is physical, not dead-edge
  artifact.

---

## 4. Shared data model — qubit budget & genome layout

| Quantity | Value | Note |
|----------|-------|------|
| Individual | 4 qubits | G=3 genome + 1 phenotype (CD-2) |
| Block | W12 = 48 qubits | 12 individuals per block |
| Blocks | 3 (A, B, C) | 144 qubits |
| Corridor / selection ancillas | shared, reused via `reset` | fits within 156q on `ibm_kingston` |
| Total | ≤156 qubits | Heron-r2, 156q |

Per-block layout is a physical qubit *line* (nearest-neighbour clone chain) picked by `layout.best_chain` from live
calibration; the three blocks occupy three disjoint contiguous chains ("stone walls" = the unused couplers between
them). Inter-block separation ~48 qubits ≫ the ~8-qubit teleport/swap crossover (D).

---

## 5. Observables & headline definitions

Replaces the generic "status workflow" section — the epic's spine is *what gets measured*.

- **B — cross-block transmission witness (THE HEADLINE, swap-routed).** The connected-GHZ witness
  `signal = ⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B` over the genealogy loci spanning two blocks after infection. `=1` for a
  genuinely entangled transmitted genealogy connected across the wall; `→0` for two separate blocks or any
  measure-and-resend classical infector. Measured **as a function of inter-block distance** = the transmission
  decay curve, the Month-5 quantum result. Read: `H` on genealogy loci then measure; phenotypes stay in Z for the
  alive-count context. (P0 finding: the bonded two-point `⟨X_{A_tail} X_{B_head}⟩` is identically 0 for a GHZ — do
  not use it; the per-block-product-nulled full 2W parity is the genuine witness.)
- **D — teleport-vs-swap crossover (RETIRED to negative baseline).** P0 refuted the teleport-flip on `ibm_kingston`
  (3 runs): teleport loses to swap at every separation because mid-circuit-measurement cost ≫ swap 2q cost on
  readout-dominated Heron-r2 (`readout_max` ≈ 7–16× `twoq_err_max`). Kept only as a documented negative result in
  P3; **not** a headline. The `logical_depth` split (teleport ~flat, swap ∝ distance) is real but not the figure of
  merit on this hardware.
- **Biology narrative (classical).** Population>0 and deepest-lineage per generation, per block — the "is the
  virus alive / how far did it spread" story. Never the quantum claim (CD-4).
- **Phase diagram (P2).** Survival + witness over the 2D grid of damping γ (immune pressure) × mutation angle
  (drug/stress).

---

## 6. Hardware considerations

- Target `ibm_kingston` (156q Heron-r2), same device as M4 so the budget calibration transfers.
- Per-block chain-quality gate (CD-6), fail-closed.
- Budget model is **first-order** (gate-count, calibrated to the 6 measured M4 points, death wall T_eff≈24). P0
  exists precisely to test the teleport-flip prediction on metal before committing to P1–P3.
- Certified QRNG mutation angles reused from the QALife pipeline (`qrng_client.py`).

---

## 7. Implementation order

Strictly sequential; P0 was a real kill-gate (it fired).

1. **P0 — flip-test. DONE 2026-08-26.** The kill-gate refuted the teleport-flip (D) on hardware but proved the
   swap-routed connected-GHZ transmission witness (B) is alive on metal. Per epic §7's own rule the D headline is
   dead and the epic is **re-scoped before P1**: pivot to swap-routed, headline = witness-vs-distance (this doc).
2. **P1 — build the virus (swap-routed).** Genome + selection + stone-wall layout + **swap-routed** chain infection,
   one runnable file, operator-by-operator `--selftest`. Teleport retained as an optional negative-baseline arm.
3. **P2 — run + environment.** Multi-generation run on the P1 build (transmission-witness-vs-distance track), then
   the 2D environment sweep.
4. **P3 — web demo + conclusion.** Aggregate, decay-curve figure, phase diagram, the P0 teleport-refutation
   negative result, write-up, demo.

---

## 8. Open questions (epic-wide) — RESOLVED 2026-08-26

- [x] Q1: **Flip metric threshold = STRICT.** P0 passes only if teleport clears the 2σ null *while* swap is buried
  in noise. Any weaker teleport>swap margin does not count as a flip. (Folded into AC-P0.3.)
- [x] Q2: **Static fitness `f(b1,b2)` = survive iff `b1=b2`** (2 of 4 genomes fit, 50% selection pressure).
  (Folded into CD-3 and AC-P1.2.)
- [x] Q3: **Generation count = fixed 9** for the P2 run; per-cell death-generation g\* is a P2 stretch, not required.
  (Folded into AC-P2.1.)
- [x] Q4: **P0 block separation = both (d-sweep).** Adjacent (small d, teleport predicted to lose = negative
  control) *and* far (large d, teleport predicted to win). The d-sweep is the flip proof. (Folded into AC-P0.3.)
  Implementation note: control moved `d=1`→`d=2` (teleport corridor needs a ≥2-wide wall); ran `--separations 2,48`.
- [x] Q5: **Environment grid = 3×3 on hardware, 5×5 in sim.** (Folded into AC-P2.3.)
- [x] **Q6 (P0 outcome, 2026-08-26): teleport-flip REFUTED → pivot to swap-routed.** P0's kill-gate fired STOP on
  the D headline (teleport loses to swap at every d; mid-measure cost ≫ 2q cost on readout-dominated Heron-r2). The
  connected-GHZ transmission witness (B) works swap-routed. Resolution: drop D as headline, pivot P1–P3 to
  swap-routed infection, new headline = transmission-witness-vs-distance decay (B). Teleport retained as a
  negative-baseline arm only. (Folded into CD-4, CD-5, §5, and the §9 P1–P3 briefs below.)

---

## 9. Per-phase briefs

### P0 — `code/stage5_fliptest.py` — Flip-test (kill-gate) — **DONE 2026-08-26**
- **What it delivered:** the minimal kill-gate. Two W12 blocks, one generation, one cross-block infection bond,
  measured connected-GHZ cross-block witness under swap-routing vs teleport-routing over a d-sweep (`2,48`).
- **Result:** teleport-flip **REFUTED** on `ibm_kingston` (3 runs, verdict STOP; see the boxed result at the top).
  Teleport loses to swap at every d; swap-routed connected-GHZ transmission witness is alive (0.215@d2, 0.060@d48).
- **Acceptance criteria (all met; witness redesigned mid-build — the planned bonded two-point is identically 0 for
  a GHZ, replaced by `⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B`):** AC-P0.1 disjoint gated blocks ✓; AC-P0.2 both arms ✓;
  AC-P0.3 d-sweep + strict-flip verdict ✓ (fired STOP); AC-P0.4 noiseless sim Δsignal=0, witness_ideal=1 ✓.
- **Verify the recorded result:** `python stage5_fliptest.py --verify research_runs/p0_hw_fliptest_ibm_kingston_20260826-134356.json`.
- **Full plan:** `feature-P0-fliptest.md` (Status: Complete).

### P1 — `code/stage5_virus.py` — Build the virus (SWAP-ROUTED; genome+selection, stone-wall layout, chain infection)
- **What it delivers:** the full virus model. 3-locus genome per CD-2, static 1-ancilla Darwinian selection per
  CD-3, three disjoint W12 stone-wall blocks per §4, **swap-routed** chain infection A→B→C per CD-5 (pivoted).
  Connected-GHZ cross-block transmission witness (the P0 form) is the quantum observable. Fully self-tested.
- **Acceptance criteria:**
  - AC-P1.1 Genome `[q_witness, b1, b2]` implemented; witness locus entangled, classical loci in Z (CD-2).
  - AC-P1.2 Static fitness `f(b1,b2)` (Q2) computed into 1 ancilla, measured, replication feed-forwarded (CD-3).
  - AC-P1.3 Three W12 blocks laid out on 144 qubits, per-block chain-quality gate (CD-6).
  - AC-P1.4 Chain infection A→B→C wired **swap-routed** (`_swap_cx`); a teleport arm retained as an optional,
    clearly-labelled negative baseline only (CD-5, pivoted — teleport is NOT the headline path).
  - AC-P1.5 Connected-GHZ cross-block transmission witness reused verbatim from P0 (`⟨X^⊗2W⟩ − per-block product`);
    the bonded two-point is not used (identically 0 for GHZ — P0 finding).
  - AC-P1.6 `--selftest` verifies every operator against closed-form values (mirror the M4 selftest discipline).
- **Depends on:** P0 (done; pivoted to swap-routed per P0's result).
- **Conventions:** extend the `stage4_qalife.py` operator library; copy P0's witness + `_swap_cx` (CD-1); keep
  `--selftest` parity with M4.
- **Out of scope:** the multi-generation run and environment sweep (P2); coevolving fitness (static only, CD-3); the
  teleport headline (refuted, P0).

### P2 — `code/stage5_run.py` — Run + environment (multi-generation + environment sweep)
- **What it delivers:** drives the P1 build for ~9 generations (Q3) tracking both the classical population-survival
  narrative and the quantum **cross-block transmission witness vs inter-block distance** (the decay curve, the
  headline), then sweeps the 2D environment grid (damping γ × mutation angle, Q5) to a survival/witness phase diagram.
- **Acceptance criteria:**
  - AC-P2.1 Fixed 9-generation run (Q3); per-generation population>0 and deepest-lineage recorded. Per-cell
    death-generation g\* is an optional stretch, not required.
  - AC-P2.2 Cross-block transmission witness recorded per generation and **per inter-block distance** (swap-routed;
    the decay curve tracked over depth and distance). Teleport baseline arm optional, off by default.
  - AC-P2.3 2D environment sweep (γ × mutation) executed — **3×3 on hardware, 5×5 in sim** (Q5); each cell
    reports survival + witness verdict.
  - AC-P2.4 JSON outputs to `research_runs/`, structured for the P3 figures/demo.
- **Depends on:** P1.
- **Conventions:** mirror `stage4_scale.py` sweep + JSON schema so P3 can consume it like the M4 demo data.
- **Out of scope:** write-up and demo (P3).

### P3 — `web/` + `research/CONCLUSION_MONTH5.md` — Web demo + conclusion
- **What it delivers:** the deliverable. Aggregates P0–P2 runs into the **transmission-witness-vs-distance decay**
  headline figure, the 2D phase diagram, and the **P0 teleport-refutation negative result**; writes
  `CONCLUSION_MONTH5.md` (honesty rails intact, CD-4); and builds a self-contained web demo of the 3-block virus
  chain (twin of the M4 `web/index.html`, values transcribed verbatim from the run JSON).
- **Acceptance criteria:**
  - AC-P3.1 `CONCLUSION_MONTH5.md` states the swap-routed transmission-witness-vs-distance result, the P0
    teleport-refutation (with mechanism: readout ≫ 2q on Heron-r2), the phase diagram, and the honesty split
    (witness = claim, population = narrative), with every table value traceable to a `research_runs/` JSON.
  - AC-P3.2 Web demo visualises the 3-block virus chain + transmission-decay headline + teleport-refutation
    baseline + phase diagram; self-contained, values transcribed from run JSON (M4 demo pattern).
  - AC-P3.3 Every quantitative claim in the conclusion is backed by a real run file (M4 validation discipline).
- **Depends on:** P0, P1, P2.
- **Conventions:** twin the M4 `web/index.html` structure and the M4 conclusion format.
- **Out of scope:** any new experiment — P3 only aggregates and presents.
