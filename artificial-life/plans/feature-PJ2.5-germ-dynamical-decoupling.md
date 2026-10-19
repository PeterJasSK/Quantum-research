# Feature PJ2.5 — Germ-selective dynamical decoupling as a measured witness lever (EM1 on the motile organism)

**Epic:** [epic-qalife-darwinian-richness.md](epic-qalife-darwinian-richness.md) (Approved) — Work-package **EM1** (`P3-candidate-movess.md:664`), under cross-cutting decision **CD-11** (error mitigation is the first scale lever). Successor to **PJ2.4** (honest motile vivarium); directly closes its named follow-up *"germ selective-DD in the motile path."*
**Feature ID:** PJ2.5
**Author:** Claude (Opus)
**Date:** 2026-10-19
**Status:** Approved (2026-10-19, defaults accepted)

> **Technical constraints / core directive:** Python + Qiskit on IBM Heron-r2 (`ibm_marrakesh` / `ibm_kingston`) via the existing `pj_run_qalife` infra. No automated tests — verification is `--dump-circuit` structural inspection + a banked sim/hardware A/B. The change is **additive**: `build_motile_vivarium`, `build_line_vivarium`, `2D_alive`, and the witness math stay byte-stable. DD touches **germ (witness) physical qubits only** — body/vitality/energy stay DD-free (Weismann barrier). DD is pure pulse suppression, **not** post-selection → the witness stays an *unconditional* claim (`kept_fraction = 1`).

---

## 1. Why (Step Goal)

**Before.** The PJ2.4 flagship (`1D_alive.py --model motile`) runs its hardware circuits through `_run_counts_simple` (`code/1D_alive.py:242`), which transpiles at `optimization_level=3` and submits — **with no dynamical decoupling**. The germ (genotype) qubits of the founder sit idle through the body walk, metabolism, aging, and reproduction gates, accumulating dephasing that rots the one quantum claim, the genealogy witness `⟨X^⊗W⟩` (and its `ghz2` Z-sector `⟨ZZ⟩`). The banked M5 result (`research_runs/pj2_motile/pj2_line_org2L4_ibm_marrakesh_20260927-180920.json`: `⟨X^W⟩≈0.98`, `⟨ZZ⟩≈0.98`, certified gens 3–5) was therefore obtained with the first, free mitigation lever **switched off**. Meanwhile the sibling line path already has germ-selective DD wired (`schedule_line_selective_dd`, `:124`; gated by the module-global `SELECTIVE_DD=True`, `:63`) — so the technique exists in the file but never reaches the motile organism, and is a hardcoded always-on global with no measured evidence it helps.

**After.** Germ-selective DD is applied to the motile path too, and DD becomes an explicit, switchable, **measured** lever rather than a silent global:

- `--dd {off,x2,xy4}` selects no DD, the current CPMG `[X,X]` sequence, or an `XY4` sequence; it replaces the `SELECTIVE_DD` global across **both** motile and line paths (default preserves today's line behaviour).
- DD pulses land **only** on the germ physical qubits (the witness set), confirmed by `--dump-circuit`.
- A single driver invocation can bank an **A/B** comparison (DD-off vs DD-on) at one config, writing both witnesses side by side plus the delta, so EM1's reporting rule is honoured: `ΔW*` is measured against its cost, and the raw (DD-off) and mitigated (DD-on) witnesses are reported together, never the mitigated one alone.
- A hardware A/B at the exact M5 config quantifies how much the free lever buys on the real organism — the first EM datapoint for P4.

This is EM1 as the epic specifies it: no biology added, no witness math changed; the lever is the *instrument* that moves the certified frontier, and here it is applied to the live flagship and proven (or honestly not) rather than assumed.

---

## 2. Acceptance Criteria

- [ ] **AC-1** (PJ2.5.1): The motile hardware path applies germ-selective DD when `--dd` is not `off`.
  → A new `schedule_motile_selective_dd(qc, backend, organisms, length, gens, rep_gen, *, dd)` (mirroring `schedule_line_selective_dd`) pads DD on the physical qubits mapped from `pj.motile_witness_qubits(organisms, length, gens, rep_gen)` only; `_run_counts_simple` routes through it (both the `basis="x"` and `basis="z"` circuits) instead of the bare `generate_preset_pass_manager(...).run(qc)` at `code/1D_alive.py:245`.
- [ ] **AC-2** (PJ2.5.2): DD is a CLI switch, not a global. `--dd {off,x2,xy4}` (default `x2`) drives both motile and line scheduling; the `SELECTIVE_DD` module global is removed and every reader uses the resolved mode.
  → `off` ⇒ no `PadDynamicalDecoupling` pass (plain `opt-level 3`); `x2` ⇒ `dd_sequence=[XGate(),XGate()]` (today's behaviour); `xy4` ⇒ `dd_sequence=[XGate(),YGate(),XGate(),YGate()]`.
- [ ] **AC-3** (PJ2.5.3): DD lands on the germ only (Weismann barrier preserved). With `--dump-circuit`, the scheduled motile circuit shows DD pulse trains inserted on idle windows of the germ physical qubits and **none** on body / vitality / energy qubits.
  → `qubits=` argument to `PadDynamicalDecoupling` is exactly the mapped germ physical set; a printed `dd_physical_qubits` list in the report confirms the mapping.
- [ ] **AC-4** (PJ2.5.4): The run banks an A/B witness comparison when `--dd-ab` is passed. The run JSON carries, per arm/gen, `witness_dd_off` and `witness_dd_on` (and `zz_dd_off`/`zz_dd_on` under `ghz2`) plus a summary `delta_witness` / `delta_certified_gens`.
  → With `--dd-ab`, `depth_scan_motile` runs each measured circuit twice (DD-off then the chosen DD-on mode) and records both; without it, a single pass at the resolved `--dd` mode (current cost).
- [ ] **AC-5** (PJ2.5.5): The witness stays an unconditional claim. `kept_fraction = 1.0` is written to the run meta for every DD mode (DD is suppression, not post-selection); no bitstrings are discarded.
  → New `meta.kept_fraction` field (epic §4) set to `1.0`; `meta.dd` records the mode; `meta.selective_dd` is dropped/aliased.
- [ ] **AC-6** (PJ2.5.6): Sim A/B is noiseless-neutral. On the statevector backend, DD-off and DD-on give identical witnesses (DD is identity in the absence of noise) — a correctness check that the DD pass did not perturb the logical circuit.
  → `--dd-ab` on `statevector_sim` prints `delta_witness ≈ 0` across all gens.
- [ ] **AC-7** (PJ2.5.7): Hardware A/B banked at the M5 config. One `ibm_marrakesh` run at `--model motile --organisms 2 --length 4 --gens 6 --food 1,3 --certify ghz2 --shots 8192 --dd-ab --dd x2` writes a run JSON under `research_runs/pj2_motile/`; the writeup records `⟨X^W⟩`, `⟨ZZ⟩`, and certified-gen count for DD-off vs DD-on side by side against the banked M5 (no-DD) numbers, honestly whatever the sign of the delta.

---

## 3. Out of Scope (Postponed)

- **Readout / measurement-error mitigation (EM2)** and **Pauli twirling (EM3)** — later EM sub-moves (`P3-candidate-movess.md`), their own features.
- **Estimator-native levers (ZNE / TREX / PEC)** — require moving the witness off the Sampler-counts path; explicitly "after the cheap levers are spent" (epic §6). Not here.
- **DD on the 2D lattice motile path** — `2D_alive.py` already has its own DD block; re-tuning it belongs to the 2D-motile port (the PJ2.4 "later port" follow-up), not PJ2.5.
- **Founder feeding robustness** (energy≈0.4 half-starve) — a separate PJ2.4 follow-up; PJ2.5 changes only the mitigation, not the food/hop.
- **Any new biology** (M1 selection, M2 competition, M3 lineages) — gated to later P3 features.
- **Changing the witness definition or the separable bound** — `xbasis_witness_from_counts` and the `⟨XX⟩+⟨ZZ⟩≤1` certificate stay byte-stable.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| DD insertion point | Transpile-time scheduling pass after layout/routing — `ALAPScheduleAnalysis` + `PadDynamicalDecoupling`, mirroring `schedule_line_selective_dd` (`code/1D_alive.py:124`). No change to `pj_qalife` builders or witness math. |
| DD target qubits | Germ physical qubits only, mapped from `pj.motile_witness_qubits(...)` via `routed.layout.final_index_layout()` — identical mapping idiom to the line pass. Body/vitality/energy left idle-but-bare (Weismann barrier, CD). |
| DD sequences | `x2` = `[X,X]` (today's CPMG, default, back-compat); `xy4` = `[X,Y,X,Y]` (EM1's suggested, more robust to pulse miscalibration). Selected by `--dd`. |
| Switch surface | `--dd {off,x2,xy4}` (default `x2`) replaces the `SELECTIVE_DD` global for **both** motile and line paths; `--dd-ab` toggles the two-pass A/B banking. |
| Cost accounting | `kept_fraction = 1.0` always (DD is unconditional suppression). A/B doubles shots **only** when `--dd-ab` is set; the normal single-mode run keeps today's shot cost. |
| Reporting rule | Raw (DD-off) and mitigated (DD-on) witnesses banked and reported side by side; `delta_witness` is descriptive, never a substitute for the raw number (EM1 honesty rule). |
| Verification | `--dump-circuit` for the pulse-placement check (AC-3); `statevector_sim --dd-ab` for the noiseless-neutral check (AC-6); one Heron A/B for the headline datapoint (AC-7). No automated tests. |

**Conventions & Notes:**
* Additive only — `build_motile_vivarium`, `build_line_vivarium`, `2D_alive.py`, `pj_qalife.py`, and `qalife.py` stay byte-stable. All changes live in `code/1D_alive.py` (+ the renderer/writeup).
* DD on germ physical qubits only; the barrier is a hard invariant, asserted by the printed `dd_physical_qubits` excluding every body/vitality/energy physical index.
* Chain-quality gate (`gated_chain`, CD-5) and QRNG environment (`qrng_environment`, CD-6) are unchanged and still fail-closed on hardware.
* Reuse the existing `pj_run_qalife` imports (`connect`, `run_sampler`, `gated_chain`, `OUTPUT_DIR`, `timestamp`); no new infra.

---

## 5. Data Model (Additions/Modifications)

```text
[Existing run JSON — modifying meta] (code/1D_alive.py run_motile, ~:400, :560)
run.meta
  ...(existing)...
  dd               str    one of {off, x2, xy4}        [replaces selective_dd:bool]
  dd_ab            bool   whether an A/B pass was banked
  dd_physical_qubits  list[int]   germ physical qubits DD was padded on (barrier evidence)
  kept_fraction    float  always 1.0 (DD is unconditional; CD-11 schema, epic §4)

[Existing per-frame dict — adding A/B fields] (depth_scan_motile frame)
frame
  ...(existing: gen, fields, w, w_sigma, sep, alive, energy, born, zz, certified, survives)...
  witness_dd_off   float  joint <X^W> with DD off     [only when dd_ab]
  witness_dd_on    float  joint <X^W> with DD on      [only when dd_ab]
  zz_dd_off        float|null  Z-sector, DD off        [ghz2 + dd_ab]
  zz_dd_on         float|null  Z-sector, DD on         [ghz2 + dd_ab]

[New summary block] (run_motile endpoint)
run.summary.dd_ab
  delta_witness          float   mean(witness_dd_on - witness_dd_off) over gens
  delta_certified_gens   int     certified-gen count (DD on) - (DD off)
```

No schema-breaking changes: readers of the old `selective_dd` boolean are updated to `meta.dd != "off"`; all other fields are additive and absent unless `--dd-ab`.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| Modify | `code/1D_alive.py` | Remove `SELECTIVE_DD` global (`:63`); add `--dd {off,x2,xy4}` + `--dd-ab` args; resolve a `dd_sequence` helper (`x2`/`xy4` → gate list). |
| New (in `1D_alive.py`) | `code/1D_alive.py` | `schedule_motile_selective_dd(qc, backend, organisms, length, gens, rep_gen, *, dd)` — germ-only DD for the motile circuits, mirroring `schedule_line_selective_dd`; returns submit-ready circuit + the germ physical set. |
| Modify | `code/1D_alive.py` | `_run_counts_simple` (`:242`): accept the motile DD context + `dd` mode and route through `schedule_motile_selective_dd` when `dd != off` (currently bare `opt-level 3`, `:245`). |
| Modify | `code/1D_alive.py` | Generalise `schedule_line_selective_dd` (`:124`) to take the resolved `dd` mode (keep `x2` default so the line path is behaviour-identical). |
| Modify | `code/1D_alive.py` | `depth_scan_motile` (`:310`): when `--dd-ab`, run each measured circuit twice (off, then chosen on-mode); record `witness_dd_off/on`, `zz_dd_off/on` per frame. |
| Modify | `code/1D_alive.py` | `run_motile` (`:352`) + meta writer (`:400`, `:560`): write `meta.dd`, `meta.dd_ab`, `meta.dd_physical_qubits`, `meta.kept_fraction=1.0`; add `summary.dd_ab` delta block; drop/alias `selective_dd`. |
| Modify | `analysis/line_render.py` | Motile render: show the DD mode in the HUD and, when present, a small DD-off vs DD-on witness delta badge on the certified frames (honest side-by-side). |
| Modify | `research/pj2_vivarium/MOTILE_CONCLUSION.md` | Add an "EM1 — dynamical decoupling (PJ2.5)" section recording the hardware A/B vs the no-DD M5 baseline, honestly. |
| New | `research_runs/pj2_motile/` | Banked A/B run JSON(s) from AC-6 (sim) and AC-7 (hardware) — produced by running, not hand-authored. |

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-3 (barrier + placement):** `python code/1D_alive.py --model motile --organisms 2 --length 4 --gens 6 --food 1,3 --certify ghz2 --dd x2 --dump-circuit` → printed schedule shows `[X,X]` trains on the listed `dd_physical_qubits`; cross-check that set contains no body/vitality/energy physical index.
- [ ] **Verify AC-6 (noiseless-neutral):** `python code/1D_alive.py --model motile --organisms 2 --length 4 --gens 6 --food 1,3 --certify ghz2 --dd-ab --dd x2` (sim) → `summary.dd_ab.delta_witness ≈ 0` and per-gen `witness_dd_on ≈ witness_dd_off` (DD is identity without noise).
- [ ] **Verify AC-1 / AC-2 (switch drives the path):** run once with `--dd off` and once with `--dd xy4` on sim; confirm the `off` run takes the bare transpile branch (no DD in `--dump-circuit`) and `xy4` inserts `[X,Y,X,Y]` on the germ.
- [ ] **Verify AC-5 (unconditional claim):** inspect any run JSON → `meta.kept_fraction == 1.0`, `meta.dd` set, no shots discarded (counts total == shots).
- [ ] **Verify AC-4 / AC-7 (hardware datapoint):** `python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 --gens 6 --food 1,3 --certify ghz2 --shots 8192 --dd-ab --dd x2` → run JSON under `research_runs/pj2_motile/` carries `witness_dd_off/on` + `zz_dd_off/on` per gen; record the side-by-side table (DD-off vs DD-on vs banked M5 no-DD) in `MOTILE_CONCLUSION.md`.
- [ ] **Edge case:** `--dd-ab` with `--certify xonly` → only `witness_dd_off/on` banked (no `zz_*`), run completes without error.
- [ ] **Regression:** a plain `--model line` run with default `--dd x2` reproduces the pre-PJ2.5 line behaviour (witness within shot noise of a pre-change run) — confirms the global→flag swap is behaviour-neutral for the line path.

---

## 8. Open Questions

- [ ] **Q1 — Default DD mode.** Keep `x2` (today's line behaviour) as the default so nothing silently changes, and treat `xy4` as an opt-in to A/B? *Proposed:* **yes** — default `--dd x2`; run `xy4` once on hardware in the A/B, adopt it as default only if it measurably beats `x2`.
- [ ] **Q2 — A/B shot cost.** `--dd-ab` doubles submitted circuits (off + on). Acceptable at the minimal M5 config (org2/L4/gens6/ghz2 = 2 settings × 6 gens × 2 DD = 24 circuits)? *Proposed:* **yes** — it is a one-off headline datapoint; normal runs stay single-mode.
- [ ] **Q3 — Line path parity.** Should the line path also gain `--dd-ab` banking, or is A/B motile-only for PJ2.5? *Proposed:* **motile-only** — the line path keeps its single-mode DD; PJ2.5's measured-lever claim is scoped to the flagship organism, line gets only the global→flag swap.
- [ ] **Q4 — `xy4` needs YGate.** Confirm `from qiskit.circuit.library import YGate` is acceptable alongside the existing `XGate` import. *Proposed:* **yes** — trivial import, same module.
- [ ] **Q5 — Baseline for the delta.** Compare DD-on against a *fresh* same-session DD-off pass (apples-to-apples, same calibration) rather than the 2026-09-27 banked M5? *Proposed:* **both** — the in-run `--dd-ab` off pass is the rigorous delta; the banked M5 is cited as the historical no-DD reference.

---

## 9. Post-Implementation Notes

[Filled after implementation.]
