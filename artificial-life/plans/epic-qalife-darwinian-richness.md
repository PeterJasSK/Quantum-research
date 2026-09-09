# Epic: QAL Phase 2 — Darwinian Richness vs the Quantum Signature (+ enabling refactor)

**Slug:** qalife-darwinian-richness
**Stages (this epic):** R0 refactor, P1 reconstruction-baseline, P2 scale-ceiling, P3 richness-investigations (exploratory), P4 frontier-synthesis (5 stages, this file)
**Supersedes:** the coherence-depth C(g) program (`epic-qdep-coherence-depth-genealogy.md`) — refuted, archived to backlog
**Source specs:** `artificial-life/plans/QDEP_Living_Genealogies.md` (§5, §6, §7 biology), `artificial-life/research/CONCLUSION_MONTH4.md` (the honest verdict this epic builds on)
**Canonical code:** model = `code/stage4_qalife.py`, driver = `code/stage4_scale.py`, infra = `code/layout.py` + `code/qrng_client.py`
**Author:** Claude (Opus)
**Date:** 2026-09-09
**Status:** Approved (2026-09-09; Q1–Q6 resolved §8)

> **Near-term focus (developer-directed):** R0 refactor → P1 reconstruction → **P2 scale, with error mitigation as the first lever**. Biology (P3 richness investigations) is **late-stage** — deferred; the P2→biology gate is evaluated **gradually**, not on a hard trigger. Get the faithful model scaling cleanly first.

> Not GitHub tickets — this research repo decomposes an epic into sequential **stages**, each a brief in §9 and (later) a full plan via `/plan-feature`. IDs R0/P1…P4 are referenced throughout.

---

## 1. Why this epic exists

Four months of work (Months 1–4) settled the honest state of quantum artificial life on this hardware. The original coherence-depth framing — `g*`, the generation where coherent inheritance beats a measure-and-resend surrogate — **collapsed structurally**: the metric `C(g)` is a diagonal `⟨σ_z⟩` quantity with an *exact* classical surrogate, and on modern Heron-r2 the supposed advantage physically inverts (readout error now dominates two-qubit error). Teleport-routing was refuted twice. Month 4 threw out the stand-in and rebuilt the **whole** Alvarez-Rodriguez 2018 model — all four Darwinian operators, verified operator-by-operator — and moved the quantum claim **off-diagonal** to the one observable with no classical surrogate: the genealogical entanglement witness `⟨X^⊗W⟩`. That reached a real, measured number: entanglement depth **W = 24 = 48 qubits**, ~6× the paper's ~4-qubit origin.

This epic is **Phase 2**. It asks one question, and only this question:

> **How much Darwinian richness can you pile on before the genuine quantum signature collapses to classical?**

The tension that makes this a real study, not a scaling stunt: the witness `⟨X^⊗W⟩` is the *only* quantum content — every diagonal metric (alive-count, lifetime, lineage depth) is classically reproducible by construction — **and every biological operator you add tends to destroy that witness** (mutation rotates the GHZ off-parity, death damps it toward `|0⟩`, interaction scrambles it, mid-circuit selection injects the worst noise on this chip). So "the most impressive life we can build today" is not "the biggest population." It is *the maximal biological complexity that still carries a certified non-classical signature on real hardware* — a constrained frontier, and where each added process extinguishes the quantum signature is the boundary of current quantum computation for this field.

**Sequencing (user-directed).** Do **reconstruction + scale first** (P1, P2): re-anchor the exact model on clean refactored code and find the coherence ceiling of the *faithful* model by scale alone. Then a **decision gate**: if further growth is just "bigger GHZ, same biology" — adding qubits for the sake of scale — pivot into biology (P3+) and start measuring richness-vs-collapse. Biology is entered *through* the gate, not before it. First, though, the code must be reorganized so Phase-2 experiments plug in cleanly (R0).

User-visible outcome: a refactored repo whose main folder holds only the exact reproduction + infra; a re-anchored scale ceiling for the faithful model; and — if the gate opens — a **richness-vs-survival phase diagram**: for each Darwinian process added, the population/generation depth at which the certified quantum signature dies. Honest framing throughout: this is scale / faithfulness / certification, **not** a quantum speedup.

---

## 2. Stages in this epic

| ID | Stage | Artifact(s) | Depends on | One-line summary |
|----|-------|-------------|------------|------------------|
| R0 | Refactor & backlog | `code/` reorg + `code/backlog/README.md` | none | Main folder = infra + the exact reproduction only; archive everything else (refuted lines, other epics) to `backlog/`, referenceable, index it, verify reproduction still runs. |
| P1 | Reconstruction baseline | reproduction module + baseline dataset/figure | R0 | Re-anchor the exact 2018 four-operator model on the clean code; bank the canonical clean-witness reference `⟨X^⊗W⟩` vs W/G with the classical-surrogate null overlaid at ≈0. |
| P2 | Scale ceiling (the "how big" axis) | driver sweep + ceiling figure | P1 | Push W and G on live Heron-r2; report entanglement depth W\* (kσ gate); ideal-vs-hardware confound curve; **decision gate**: is scale exhausted → open biology? |
| P3 | Richness investigations **(late-stage, exploratory)** | one+ biology extensions + richness datapoints | P2 gate | Exploratory, not a fixed build. Spend the qubit headroom Heron-r2 gives on **more complete / more complex** quantum life: adaptive measured selection (QDEP §6.5), interaction dynamics, spatial/2D population, long-range bonds, environment/carrying-capacity. Each added process measured as witness collapse per added complexity. Direction chosen from P2 evidence — "this is what we explore," not a locked spec. |
| P4 | Frontier synthesis & write-up | phase diagram + web demo + preprint skeleton | P1–P3 | Assemble the richness-vs-survival phase diagram; headline the most complex certifiable quantum life + the boundary; honest scale/certification framing. |

R0 is the only stage with no dependency. P1→P2 are linear and are the **near-term** work. P3 (biology) is **late-stage** and **exploratory**, entered only after the P2 scale axis is worked and judged exhausted (Q4/Q5) — a menu to explore, not a fixed build. P4 aggregates.

---

## 3. Cross-cutting decisions

Decided once; every stage below respects these.

- **CD-1 Main folder minimalism (Q1 resolved: two files).** After R0, `code/` contains exactly: `layout.py`, `qrng_client.py`, and the **reproduction module — kept as two files**: model `qalife.py` (+ `--selftest`, the honesty anchor, must stand alone) and hardware driver `run_qalife.py`. Everything else lives in `code/backlog/`. New Phase-2 richness operators are added to the model file as plug-in operators, not new top-level forks.
- **CD-2 Drop the misleading `stage4_` prefix (Q2 resolved: yes).** `stage4_qalife.py` and `stage4_scale.py` were named as "stage 4" of the now-refuted staged C(g) line; they are actually the canonical model + driver. Rename to `qalife.py` (model) and `run_qalife.py` (driver), updating the single real cross-file import (`stage4_scale.py:44 import stage4_qalife as q4` → `import qalife as q4`).
- **CD-3 The witness is the only quantum claim.** `⟨X^⊗W⟩` (`xbasis_witness_from_counts`, `stage4_qalife.py:385`) is the sole non-classical observable. Every diagonal metric (alive-count, deepest-lineage, phenotype `⟨σ_z⟩`) has an exact classical surrogate (`classical_surrogate_z`, `:419`) and carries **no** quantum claim. Every stage reports the separable null alongside the witness — the null must sit at ≈0 or the experiment is invalid.
- **CD-4 Honesty invariant.** If the matched separable / measure-and-resend surrogate reproduces a result within kσ, it is plumbing, not quantum life — report it as such. This is the whole-project discipline and the reason Phase 1's headline was retired.
- **CD-5 Significance + chain-quality gates.** Certified "ALIVE" ⇔ `witness[g] − sep[g] > k·σ` (`entanglement_depth`, `:407`), default **k = 2** (report **k = 3** too), σ from `--repeats` + shot-noise floor in quadrature. Hardware runs enforce the fail-closed chain-quality gate (abort if `twoq_err_max > 0.05` or `readout_max > 0.15`, `stage4_scale.py:147`) so witness decay is physical, not a dead-edge artifact.
- **CD-6 QRNG certified, fail-closed.** Mutation angles come from the Q-EaaS certified stream via `qrng_client.py`; on `QRNGUnavailable` the run aborts — never a silent PRNG fallback (provenance would become a lie).
- **CD-7 Sim-first, hardware-confirm, every stage.** Fix each pipeline in `--sim` (and `--selftest` for operators), then confirm live. `--selftest` verifying operators vs paper closed-forms is the verification mechanism — no separate test framework is added (repo convention: no tests).
- **CD-8 Reconstruction+scale before biology; biology is late-stage (Q4/Q5 resolved).** P1/P2 land first and are the near-term focus. The scale axis is worked and judged **gradually** — no hard plateau trigger; biology (P3 richness investigations) is deferred to a late stage and entered only once scale-for-scale's-sake is judged exhausted (§7). "Noise is not a fitness function" (QDEP §1): every added operator is an explicit, measured, entropy-traced biological process — never noise dressed as selection.
- **CD-11 Error mitigation is the first scale lever (Q6 resolved).** When P2 hits the faithful ceiling, error detection / mitigation (parity herald, readout mitigation, ZNE, DD) is the **first** thing tried to push W\* out — before any biology and before declaring the ceiling. Reported against kept-fraction cost.
- **CD-9 Backlog is reference-only.** Archived files under `code/backlog/` are for reference and provenance, **not** guaranteed runnable in place — their `sys.path`/sibling-copy assumptions may break after the move. The `backlog/README.md` index records what each was, its verdict, and what supersedes it. To resurrect one, reference it and fix paths deliberately.
- **CD-10 The routing primitives stay copied, not shared.** `_swap_cx`/`_teleport_cx` are text-copied into the model (CD-1 verbatim-copy rule); they remain in the reproduction module for the (gated, backlog) long-range interaction richness, even though standalone teleport-routing is refuted.

---

## 4. Shared data model (run/summary JSON schema)

All stages persist runs in the existing `stage4_scale.py` schema so P4 can aggregate uniformly. Output dir `research_runs/`, naming `<TAG>_<interaction>_<death>_<backend|sim>_<ts>.json`.

| Field | Level | Change vs current | Introduced by | Consumed by |
|-------|-------|-------------------|---------------|-------------|
| `witness_by_width[W]` = `⟨X^⊗W⟩` | run/summary | reused (`xbasis_witness_from_counts`) | P1 | P2,P3,P4 |
| `separable_null[W]` = `∏_i⟨X⟩_i` | run/summary | reused — the classical null (must ≈0) | P1 | all |
| `witness_ideal[W]` | run | reused — noiseless confound reference | P2 | P4 |
| `entanglement_depth` (k=2, k=3) | summary | reused — the headline W\* | P2 | P4 |
| `death_mode ∈ {damping, unitary, selection}` | run | **new** — `selection` = adaptive measured culling (P3) | P3 | P4 |
| `selection_events[]` | run | **new** — mid-circuit measure + feed-forward cull records (gen, individual, outcome) | P3 | P4 |
| `kept_fraction` | run | **new** — post-selection / herald survival fraction (mitigation lever) | P2 | P4 |
| `interaction ∈ {none, nn, longrange, spatial2d, …}` | run | extended — richness topology (P3) | P3 | P4 |
| `richness_score` | summary | **new** — count of active biological operators + topology complexity (P4 axis) | P4 | P4 |
| `meta.entropy_provenance` | run | reused — QRNG receipt per mutation (CD-6) | P1 | P4 |
| `meta.calibration` | run | reused — `read_snapshot(backend)` | P1 | P4 |

---

## 5. Repo layout — before / after (the refactor "workflow" change)

**Before** (`code/`, 5004 LOC across 9 files, tangled by verbatim-copy):
```
stage0_reproduce.py  stage1_temporal.py  stage2_scale.py  stage3_teleport.py
stage4_qalife.py     stage4_scale.py     stage5_fliptest.py
layout.py            qrng_client.py
```

**After** (main folder = infra + reproduction only):
```
code/
  layout.py                 # infra (unchanged)
  qrng_client.py            # infra (unchanged)
  qalife.py                 # was stage4_qalife.py — exact 2018 4-operator model + --selftest + witness
  run_qalife.py             # was stage4_scale.py — Heron-r2 driver (import fixed)
  backlog/
    README.md               # index: original name → role → verdict → superseded-by
    stage0_reproduce.py     # (b) simplified C(g) precursor — refuted line
    stage1_temporal.py      # (b) temporal C(g) + surrogate — refuted line
    stage2_scale.py         # (b) C(g) scale — refuted line
    stage3_teleport.py      # (d) teleport-routing — refuted twice; source of _swap_cx/_teleport_cx
    stage5_fliptest.py      # (e) stone-wall-virus epic Phase-0 — different study (see plans/virus/)
```

Rename per CD-2 (Q2). Only real code edit beyond `git mv`: fix `run_qalife.py`'s `import stage4_qalife as q4` → `import qalife as q4`. `qalife.py` is otherwise self-contained (imports only qiskit + stdlib; the two routing primitives are already text-copies, not imports). The five archived files are reference-only (CD-9).

---

## 6. Hardware / platform considerations

- Target: least-busy IBM **Heron r2** (156-qubit, e.g. `ibm_marrakesh`, `ibm_kingston`) via `pipeline_common.connect`; `layout.best_chain` picks the SWAP-free low-error chain; chain-quality gate fail-closed (CD-5).
- Qubit budget: each individual = 2 qubits (genotype + phenotype); `damping` death adds **one shared** bath ancilla (reused via `reset`). `nq = 2·W + (1 if death=='damping' else 0)` → W=77 fills a 156-q chip. Scale is qubit-cheap; the wall is decoherence, not width.
- P3 adaptive selection needs **dynamic circuits** (mid-circuit measure + classical feed-forward). On this chip, mid-circuit measurement / readout is the **dominant** error channel (it is exactly why teleport-routing lost). So P3 is expected to bite the witness hard — that bite *is* the measurement, not a bug.
- The witness `⟨X^⊗W⟩` decays roughly geometrically with W; the ceiling is a **hardware** number sim cannot find — hardware confirm is mandatory at P2/P3. Fake-noise backends are too benign (Month-3 finding).
- Error detection / mitigation (parity herald, readout mitigation, ZNE, DD) is the one honest lever to push W\* out (P2.3) — measured against kept-fraction cost.

---

## 7. Implementation order & the P2→P3 decision gate

Strict sequence: **R0 → P1 → P2 → [gate] → P3 → P4.**

1. **R0** — reorganize; reproduction must still `--selftest` green and reproduce the Month-4 baseline in sim before any Phase-2 science.
2. **P1** — re-anchor the exact model; bank the clean-witness baseline (the reference every richness run is judged against).
3. **P2** — scale W/G to the coherence ceiling of the *faithful* model; report W\* with confounds.
   - At the ceiling, **error mitigation is the first lever** (CD-11) — push W\* out before declaring the ceiling or touching biology.
4. **DECISION GATE (AC-P2.4) — evaluated gradually.** Judge scale's marginal value as the sweep proceeds; there is no hard plateau trigger. Open the **late-stage** biology block (P3+) only once further growth adds no new scientific content — "more qubits, same biology" (bigger GHZ), after mitigation is spent. While scale still surfaces understanding (non-geometric decay, structure in where the witness dies), stay on the scale axis. Record the decision + rationale in the P2 runlog. The developer's branch: *don't add biology until scale-for-scale's-sake is proven exhausted.*
5. **P3 (late-stage, exploratory)** — richness investigations: spend the qubit headroom on more complete / more complex quantum life. Exploratory, not a rigid spec — direction set by P2 evidence. Adaptive measured selection (QDEP §6.5) is the best-specified entry point; interaction / spatial / long-range / environment are the menu to explore from there. Deferred (Q5) until the scale axis is exhausted.
6. **P4** — aggregate into the phase diagram + demo + preprint. Can scaffold early; needs P1–P3 data.

No stage except R0 is independently pickup-able.

---

## 8. Open questions (epic-wide) — all resolved 2026-09-09

**Resolved:** Q1 two files · Q2 rename yes · Q3 same backlog (no `virus/` sub-area) · Q4 gradual gate, biology late-stage · Q5 adaptive selection deferred · Q6 error mitigation is the first P2 lever. Folded into CD-1/CD-2/CD-8/CD-11, §5, §7, §9 below.

- [x] **Q1 (CD-1, "the reproduction file"):** the reproduction is currently two files — model (`qalife.py`) + driver (`run_qalife.py`). Keep them as **two** (recommended: the 598-line model with `--selftest` must stand alone as the honesty anchor; the driver is the hardware layer) or merge into a single file as the user's phrasing ("the reproduction file", singular) literally reads?
- [x] **Q2 (CD-2):** rename to `qalife.py`/`run_qalife.py` — **yes.**
- [x] **Q3 (§5):** `stage5_fliptest.py` → **same `code/backlog/`** as the rest (no separate `virus/` area); index note points to its home epic.
- [x] **Q4 (P2 gate, AC-P2.4):** **gradual** — work the scale axis and judge marginal value as it goes; **biology is a late-stage part**, no hard plateau trigger.
- [x] **Q5 (P3):** adaptive selection **deferred** — late-stage, not the immediate post-P2 step.
- [x] **Q6 (P2.3):** error mitigation is **in scope and first** — the first lever tried at the P2 ceiling, before biology.

---

## 9. Per-stage briefs

### R0 — Refactor & backlog
- **Delivers:** main `code/` = `layout.py` + `qrng_client.py` + reproduction module only; all else archived to `code/backlog/` with an index; reproduction verified still-working post-move.
- **Acceptance criteria:**
  - AC-R0.1: main `code/` contains exactly the two infra files and the reproduction module(s); every other `.py` is moved (not copied) to `code/backlog/`.
  - AC-R0.2: `code/backlog/README.md` indexes each archived file — original name, role tag (refuted-C(g) / refuted-teleport / other-epic), verdict, and what supersedes it (pointing at the reproduction module or the relevant conclusion/runlog).
  - AC-R0.3: reproduction still runs — `--selftest` passes (all four operators verified vs the paper's closed-form values) and a small `--sim` run reproduces the Month-4 baseline witness within noise.
  - AC-R0.4: pure move + import-fixup — no change to model/driver logic; the single real cross-file import is updated if renamed (CD-2).
- **Depends on:** none. **Out of scope:** any new physics, any new operator, any hardware run.
- **Conventions:** `git mv` to preserve history; keep provenance comments in archived files intact.

### P1 — Reconstruction baseline
- **Delivers:** the exact 2018 four-operator model re-anchored on the clean code; the canonical clean-witness reference dataset + figure.
- **Acceptance criteria:**
  - AC-P1.1: full model (self-replication `CX`, mutation `Ry(θ)` from QRNG, death amplitude-damping via bath ancilla, interaction `SWAP`) runs with `--selftest` green.
  - AC-P1.2: bank `⟨X^⊗W⟩` vs W (and vs generations) from ideal sim + a small hardware confirm, with `separable_null` overlaid and verified ≈0 (CD-3).
  - AC-P1.3: archive the baseline dataset + figure as the fixed reference every richness experiment (P3+) is judged against.
- **Depends on:** R0. **Borrows:** the Month-4 driver run recipe (`RUNBOOK_QDEP_LIVE.md`). **Out of scope:** scaling to the ceiling (P2), any new biology.

### P2 — Scale ceiling
- **Delivers:** the genealogical entanglement depth W\* of the *faithful* model on live hardware, with confounds; the decision gate.
- **Acceptance criteria:**
  - AC-P2.1: sweep W (and G) on Heron-r2; report W\* = largest W with `witness − sep > k·σ` (k=2 headline, k=3 reported), chain-quality gate enforced (CD-5).
  - AC-P2.2: report the ideal noiseless `witness_ideal` curve alongside hardware so decoherence is separated from model-intrinsic (mutation/clone) decay.
  - AC-P2.3 (**first lever**, CD-11): at the ceiling, quantify how far error detection / mitigation (parity herald, readout mitigation, ZNE, DD) pushes W\* out, reporting kept-fraction cost — done before declaring the ceiling and before any biology.
  - AC-P2.4 (**decision gate, gradual**): record whether scale's marginal value is exhausted (§7) after mitigation, and therefore whether the late-stage biology block (P3+) opens.
- **Depends on:** P1. **Out of scope:** any Darwinian richness beyond the faithful four operators (that is P3+).

### P3 — Richness investigations (spend more qubits on more complete / more complex life) — **late-stage, exploratory**
- **Delivers:** one or more biological extensions that use the qubit headroom Heron-r2 gives (§6: W=77 fills a 156-q chip) to make the life *more complete and more complex*, each measured identically — witness collapse per added complexity. **Exploratory:** direction chosen from P2 evidence, not locked up front. "This is what we explore," not a rigid build. Not started until the P2 scale axis (incl. mitigation) is judged exhausted.
- **Framing:** P2 shows scale is qubit-cheap — the wall is decoherence, not width (§6). P3 asks the positive question the faithful four operators leave open: **given spare qubits, what richer biology can we add that still carries a certified witness?** Every candidate is an explicit, entropy-traced biological process — never noise dressed as selection (CD-8).
- **Where to look (menu — QDEP §6/§7 Part C; explore, don't exhaust):**
  - **adaptive measured selection (best-specified entry point, QDEP §6.5, verbatim):** *"Selection is explicit and measured: a mid-circuit measurement of the phenotype (the 'lifetime' observable) determines survival; individuals below threshold are reset/removed via conditional feed-forward."* Implement as `death_mode='selection'`, swapping passive amplitude-damping for measured fitness culling. Mid-circuit measure is the dominant noise channel on this chip — the witness cost *is* the finding.
  - **interaction dynamics (§6.3):** competition/cooperation two-qubit gates between individuals.
  - **spatial / 2D population:** neighbors on a grid vs the 1-D line.
  - **long-range bonds (§6.4):** the backlog teleport-vs-SWAP routing re-examined under the witness observable.
  - **environment / carrying-capacity (§6.5, §8):** threshold culling against a resource bath.
  - **Quantum-Tree genealogy substrate (§2B):** as the population topology.
- **Acceptance criteria (per explored extension):**
  - AC-P3.1: implement as a plug-in operator/topology on the model file (CD-1), not a new top-level fork; add `--selftest` coverage where a closed form exists.
  - AC-P3.2: report witness vs separable-null vs ideal at matched W/G; record the W/G at which the signature crosses into classical — the richness-vs-signature datapoint.
  - AC-P3.3: confirm the diagonal metrics (alive-count, deepest-lineage) still have an exact classical surrogate under the extension; only the witness carries the quantum claim (CD-3/CD-4).
- **Depends on:** P2 gate open. **Borrows:** dynamic-circuit / feed-forward pattern from archived `stage3_teleport.py` (`_teleport_cx`); routing primitives `_swap_cx`/`_teleport_cx` already in the model (CD-10); witness helpers from the reproduction module. **Out of scope:** ~102-qubit maximal scale-out (a later program); locking to a single fixed extension up front (this stage is exploratory).

### P4 — Frontier synthesis & write-up
- **Delivers:** the richness-vs-survival phase diagram; the headline config + number; web demo + preprint skeleton.
- **Acceptance criteria:**
  - AC-P4.1: assemble the phase diagram — for each operator/complexity added (P1 baseline → P2 scale → P3 investigations), the W/G at which the witness crosses into classical.
  - AC-P4.2: headline = *"the most complex quantum artificial life certifiable on 2026 hardware"* — the config and the certified entanglement depth — plus the boundary where each added Darwinian process extinguishes the signature.
  - AC-P4.3: honest framing (scale / faithfulness / certification, **not** speedup, CD-4); data-forward web demo (extend `feature-M4-web-demo.md`) + IEEE-style short-paper skeleton.
- **Depends on:** P1–P3 runs. **Out of scope:** new physics — aggregation and write-up only.

---

## 10. Ground rules honored
- Every stage (R0, P1–P4) appears in §2 and has a brief in §9.
- ACs quote source material where verbatim quotes exist (QDEP §6.5 in P3); others are grounded in the Month-4 conclusion and the user's Phase-2 framing, not invented.
- No implementation "how" beyond file/function targets — left to `/plan-feature` per stage.
- Honesty invariant (CD-3/CD-4) and the no-speedup framing (CD-4, AC-P4.3) are stated, not papered over.
- The refactor is move-only (CD-9); backlog is reference, not deletion — nothing refuted is destroyed.
- `Status: Draft` — the developer flips to Approved.
