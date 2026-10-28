# Feature F4 — QALife Mode-A living-process arm (optional)

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved)
**Feature ID:** F4
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Complete

> Stack locked: Python + Qiskit, `AerSimulator` default (dev), exactly one human-run
> `ibm_heron` job for the demo CHSH/witness. New `f4_qalife/` package plugs into the
> existing `Sampler` seam; F2/F3 are consumed **unchanged**. No signing, no ledger, no ML,
> no CT-physics. Mode B (coherent genealogy) is out of scope — physically blocked on Heron
> (memory `qdep-setup-bug-fix`). No automated tests — manual verification only.

---

## 1. Why (Step Goal)

**Before.** The MVP (F1→F3) rolls a *static* cohort: independent single nodules plus a few
sibling pairs from **one** quantum division (generation 0→1, no selection, no loop). The page
teases "generation 1 — full clonal evolution is the next step," but nothing actually evolves.

**After.** A real, if small, **evolutionary process runs on the quantum device**: founder
cells divide with mutation and commit a fate in superposition (P1 + P2), a **classical host**
scores fitness and kills losers, and survivors seed the next generation — 2–3 generations of
measure-and-restart (Mode A, constant depth, survives the coherence wall). Each generation
records a **within-generation entanglement witness** (the headline metric — ⟨σz⟩ is classical,
so we measure the off-diagonal ⟨XX⟩+⟨ZZ⟩ Bell witness on the division pair). The evolved
lineage is emitted as the **same `TumorParams` contract** F2/F3 already consume, so the cohort
grid renders an actual multi-generation genealogy (gen 0/1/2 sharing a `lineage_id`) with no
render changes. This is the first honest living-process deliverable and the bridge to the
parent plan's §5.2.5 arm.

**Honest label carried everywhere:** *quantum within a generation, classical genealogy*
(Mode A measures each generation, destroying cross-generation entanglement — parent plan §5.2.5,
Mode A). Still params-quantum / image-classical (epic §3).

---

## 2. Acceptance Criteria

- [x] **AC-1** (F4.1): A `QALifeSampler` implements the `Sampler` protocol and returns
  `list[TumorParams]` byte-identical in shape to `QRNGSampler`/`PRNGSampler`, so F2 cannot tell
  which sampler produced the cohort. **Evidence:** `f4_qalife/sampler.py:23` (class),
  `f4_qalife/sampler.py:52` (`draw` returns `list[TumorParams]`, sets `last_run`); verified —
  unmodified `f2_imaging.build_tiles` consumed the F4 dir and wrote 12 CohortTiles.
- [x] **AC-2** (F4.2): A Mode-A hybrid loop runs `--generations` generations over `--founders`
  lineages, each generation a **separate constant-depth quantum job**: prep → divide (P1) → fate
  (P2) → measure. **Evidence:** `f4_qalife/loop.py:105` (`run_mode_a`), per-gen job at
  `loop.py:137`/`:141` via `run_counts`; reuses `circuit._encode_properties` (`loop.py:67`) and
  controlled-copy + `Ry(θ_mut)` (`loop.py:76-78`). Ran 3 generations on Aer.
- [x] **AC-3** (F4.3): Classical **fitness → selection → seeding**: decode cells, score, keep top
  `--survivors`, seed g+1 from the survivor's measured genotype in the Z basis (X gates), then
  divide+mutate. **Evidence:** `f4_qalife/fitness.py:40` (`score`), `:66` (`select`);
  `loop.py:147` (select), `loop.py:157` (seed from best survivor bits), `loop.py:75` (X-gate Z-basis
  seed). Survivors visibly carried forward across generations.
- [x] **AC-4** (F4.4): P2 fate is genuinely quantum: a 2-qubit fate sub-register over
  {proliferative, quiescent, necrotic} (4th code remapped) with a **phase dial** `--phase` biasing
  interference before measurement. **Evidence:** `f4_qalife/loop.py:42` (`_fate_prep`, Ramsey
  `h`–`rz(phase)`–`h` at `loop.py:44-46`), `fitness.decode_fate` remap. Verified: phase 0 →
  proliferative/quiescent 50/50; π → proliferative/necrotic 50/50 (distribution shifts with phase).
- [x] **AC-5** (F4.5): Each generation records `W_g = ⟨XX⟩ + ⟨ZZ⟩` on a parent–daughter division
  pair from **dedicated XX/ZZ jobs** (separate from the generation job). **Evidence:**
  `f4_qalife/witness.py:28` (two single-basis circuits), `:44` (`witness_value`, reuses
  `certify.correlator`); `GenerationRecord` appended at `loop.py:160`. On Aer W_g ≈ 1.91 each
  generation (entangled).
- [x] **AC-6** (F4.6): Job-level **CHSH certificate** produced per run (reused from F1).
  **Evidence:** `f4_qalife/sampler.py:66-73` (`build_chsh_circuits` + `chsh_value` → `last_run`).
  Aer runs gave CHSH ≈ 2.80–2.87.
- [x] **AC-7** (F4.7): Evolved lineage threads genealogy: cells of one founder share a
  `lineage_id`; `generation` 0..G−1; `shot_index` unique. Rendered through **unmodified** F2→F3.
  **Evidence:** `loop.py:131`/`:118-156` (lineage_id `ql{f}`, generation `g`, unique `shot`);
  verified cohort = 12 tiles, lineages {ql0..ql3: 3 each}, gens {0,1,2}, unique shot_index;
  `f3_web.build_web` produced a 416 KB self-contained page with no edit to `f2_imaging/`/`f3_web/`.
- [x] **AC-8** (F4.8): Entrypoint writes `cohort_params.json`, `quantum_run.json`, `witness.json`
  under `research_runs/qalife_<backend>_<ts>/` and prints a per-generation summary + Mode-A label.
  **Evidence:** `f4_qalife/run_qalife.py:64` (`_write_artifacts`), `:92` (`_print_summary`), `:131`
  (hardware banner). Confirmed all three artifacts written; summary printed cells/survivors/W_g.

---

## 3. Out of Scope (Postponed)

- **Mode B (coherent genealogy) + the collapse curve** — deep, physically blocked on Heron
  (memory `qdep-setup-bug-fix`); it is the parent plan's separate §5.2.5 sub-study chapter, not
  this step.
- **Rendering the witness on the web page** (a per-generation witness strip/plot) — F4 reuses
  F3 **unchanged** (epic §7); witness ships as `witness.json` + console summary. A web witness
  panel is a later F3.x follow-up.
- **The interference-knob sub-study** (sweep `--phase`, show correlation shift at fixed
  marginals) — the `--phase` dial is wired and recorded, but the systematic sweep + analysis is
  deferred to the parent-plan living-process chapter (§5.2, §5.2.5 metrics).
- **Spatial genealogy in the image** (siblings-adjacent placement from the lineage tree, growth
  snapshots, longitudinal baseline/follow-up) — belongs to the parent plan's hybrid-assembly
  work; F4 reuses F2's existing per-tile placement.
- **Richer biology** (metastasis/motility, hypoxia field, apoptosis-as-channel) — later QALife
  arms (parent plan §5.2.5 clonal-evolution map).
- **Signing / ledger / audit / ML detector** — deferred across the whole epic (epic §3).

---

## 4. Technical Decisions

Adopts the epic's §3 cross-cutting decisions verbatim (Sampler seam; Aer dev / one Heron demo
job; self-contained static page; no signing/ledger/ML/CT-physics; research conventions — no
issues, no tests). F4-specific choices:

| Component | Choice / Implementation |
|---|---|
| Package | New `f4_qalife/` (`__init__.py`, `sampler.py`, `loop.py`, `fitness.py`, `witness.py`); sibling to `f1_quantum/`, imports from it. Does **not** touch `f2_imaging/`/`f3_web/`. |
| Sampler wiring | `QALifeSampler(Sampler)` — third implementation of the existing `f1_quantum.sampler.Sampler` protocol; `QALifeSampler` lives in `f4_qalife/` to keep F4 additive. |
| Genotype encoding | Reuse the 9-qubit property register + `circuit._encode_properties` and `decode.bits_to_params` unchanged (cohort stays rulebook-comparable; F3's cohort-vs-rulebook strip keeps working). |
| Division (P1) | Controlled-copy + `Ry(θ_mut)` per property qubit, same op as `build_sibling_pair_circuit` (`--theta-mut`, default 0.3). |
| Fate (P2) | One **2-qubit fate sub-register** per cell: `ry` to spread over 3 fates + `rz(--phase)` phase dial; Z-measured and decoded to {proliferative, quiescent, necrotic} (4th code → most common fate). |
| Mode | **Mode A only** — measure-and-restart; one constant-depth job per generation. Honest label "quantum within a generation, classical genealogy" on every artifact. |
| Selection | Classical, deterministic: `fitness.py` scores decoded cells (proliferative-fate bonus + mid-size preference), keeps top `--survivors` per lineage; ties broken by lowest `shot_index`. |
| Seeding gen g+1 | Prep survivor's **measured** genotype bits in Z basis via X gates (genuine measure-and-restart), then divide+mutate. No angle re-fit, no patient data (keeps it non-QML, epic §6). |
| Witness | `W_g = ⟨XX⟩+⟨ZZ⟩` on a parent–daughter pair from two dedicated single-basis jobs per generation; reuses `certify.correlator`. Separable bound 1; mirrors the surviving GHZ cert pattern (memory `qalife-pj24-motile-vivarium`). |
| CHSH | Reuse `build_chsh_circuits` + `chsh_value` once per run (provenance parity with F1). |
| Cohort size | `--founders × --generations × --survivors` cells = tiles; defaults 4 × 3 × 1 = 12 (epic default cohort = 12). |
| Hardware rule | Same as `run.py`: implementer runs Aer only; `--backend ibm`/`auto` is human-run with the banner; no token read/stored by this code. |

**Conventions & Notes:**
* F2/F3 stay sampler-blind — **no edits** to `f2_imaging/` or `f3_web/`. F4's output dir is a
  drop-in replacement for an F1 run dir (`cohort_params.json` + `quantum_run.json`).
* Every quantum label has a job (epic §3): P1 = division circuit, P2 = fate sub-register, witness
  = dedicated basis jobs, CHSH = certificate job. Fitness/selection/seeding are explicitly
  classical and documented as such.
* Death narrated as environment-driven selection, **not** engineered decoherence (parent plan
  §5.2.5 trap 1).
* Mode-A honest label is mandatory on `witness.json`, the console summary, and (via the honest
  label text) carried into the cohort — do not imply coherent genealogy.

---

## 5. Data Model (Additions/Modifications)

Reuses `TumorParams` and `QuantumRun` unchanged (shape parity is AC-1). `TumorParams.generation`
now ranges 0..G−1 instead of {0,1}; `lineage_id` now spans a whole founder genealogy. One new
entity (epic §4 `Generation`/`Lineage` row):

```text
[Reused unchanged]
TumorParams   (common/datamodel.py)  — generation now 0..G-1; one `fate` is carried in... (see note)
QuantumRun    (common/datamodel.py)  — job-level CHSH/backend/raw bits, as F1

[New Entity]  common/datamodel.py
GenerationRecord
  generation     int        # 0-based generation index
  n_cells        int        # cells prepared/measured this generation
  survivors      int        # kept by classical selection
  witness_value  float      # W_g = <XX> + <ZZ>  (entangled if > 1)
  xx             float      # <XX> correlator (dedicated job)
  zz             float      # <ZZ> correlator (dedicated job)
  phase          float      # P2 fate phase dial (radians) used this run
  to_dict / from_dict

[Note on fate]  TumorParams has no `fate` field today. Decision: keep the Sampler contract
byte-identical (AC-1) by NOT adding a field to TumorParams; the decoded fate influences
classical fitness/selection inside the loop but is not persisted per tile in the MVP. (Open
question Q4 proposes this; the alternative is a nullable `fate: str = ""` field.)
```

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `QuantumPhantoms/code/f4_qalife/__init__.py` | Package marker (mirror `f1_quantum/__init__.py`). |
| New | `QuantumPhantoms/code/f4_qalife/witness.py` | Build XX/ZZ witness circuits for a parent–daughter division pair; compute `W_g = ⟨XX⟩+⟨ZZ⟩` via `certify.correlator`. |
| New | `QuantumPhantoms/code/f4_qalife/fitness.py` | Pure classical `score(cell)` + `select(cells, k)`; proliferative-fate bonus + mid-size preference; deterministic tie-break. |
| New | `QuantumPhantoms/code/f4_qalife/loop.py` | Mode-A hybrid loop: per-gen prep (reuse `_encode_properties`) + division (P1) + fate (P2, `rz(phase)`) → measure → decode (`bits_to_params`) → fitness/select → seed survivors (Z-basis X-gate prep); returns `(cells, [GenerationRecord])`. |
| New | `QuantumPhantoms/code/f4_qalife/sampler.py` | `QALifeSampler(Sampler)`: wraps `loop`, runs one CHSH certificate, sets `last_run: QuantumRun`, exposes `generations: list[GenerationRecord]`. |
| New | `QuantumPhantoms/code/run_qalife.py` | Entrypoint; mirrors `run.py`. Flags: `--backend --founders --generations --survivors --theta-mut --phase --shots --chsh-shots --witness-shots`. Writes `cohort_params.json`, `quantum_run.json`, `witness.json`; prints per-gen summary + Mode-A label. |
| Modify | `QuantumPhantoms/code/common/datamodel.py` | Add `GenerationRecord` dataclass (+ `to_dict`/`from_dict`). Do **not** change `TumorParams`/`QuantumRun` (shape parity, AC-1). |
| Modify | `QuantumPhantoms/code/README.md` | Add an F4 section: what Mode A is, the run command, the honest "quantum within a generation, classical genealogy" label, and that F4 output drops into the existing F2→F3 commands unchanged. |

No changes under `f1_quantum/`, `f2_imaging/`, `f3_web/` (beyond importing F1 modules from F4).

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-2/AC-3/AC-8 (loop + artifacts):**
  `python QuantumPhantoms/code/run_qalife.py --backend aer --founders 4 --generations 3 --survivors 1`
  → console prints 3 generations (cells, survivors, `W_g`) and the Mode-A label; a new
  `research_runs/qalife_aer_<ts>/` contains `cohort_params.json`, `quantum_run.json`,
  `witness.json`.
- [ ] **Verify AC-7 (shape parity 12 tiles):** inspect `cohort_params.json` → 12 `TumorParams`;
  each founder's cells share one `lineage_id`; `generation` ∈ {0,1,2}; `shot_index` unique.
- [ ] **Verify AC-1 (sampler-blind) + AC-7 (render unchanged):**
  `python QuantumPhantoms/code/build_tiles.py --run research_runs/qalife_aer_<ts>` then
  `python QuantumPhantoms/code/build_web.py --run research_runs/qalife_aer_<ts>` complete with
  **no code change**; open `web/index.html` → cohort grid renders, lineages show `gen 0/1/2 of ∞`
  badges, CHSH stamp present.
- [ ] **Verify AC-5 (witness):** `witness.json` has one record per generation with
  `witness_value`, `xx`, `zz`; on noiseless Aer `W_g` ≈ > 1 for `theta_mut` away from 0/π
  (entangled). Console `W_g` matches the file.
- [ ] **Verify AC-4 (fate phase dial):** run twice, `--phase 0.0` vs `--phase 1.5708`; at fixed
  marginals the decoded fate mix / cross-fate pattern shifts (interference knob is live), recorded
  `phase` in `witness.json` matches the flag.
- [ ] **Verify AC-6 (CHSH):** `quantum_run.json` `chsh_value` ≈ 2.8 on noiseless Aer; console
  verdict line present (same format as F1).
- [ ] **Edge case (selection pressure):** `--survivors 1 --generations 3` → a single lineage
  narrows to one survivor line; `--founders 2 --generations 3 --survivors 2` → 12 tiles with
  branching genealogy; both render without error.
- [ ] **Hardware path (human-run, Peter only):** `python QuantumPhantoms/code/run_qalife.py
  --backend ibm_heron ...` prints the hardware banner; on Heron `W_g` is expected to degrade with
  generation and CHSH ≈ 1.9–2.6 (use the real values on any later page; Aer is noiseless and
  misleads — epic §6).

---

## 8. Open Questions

- [x] **Q1 (package layout):** New `f4_qalife/` package vs. adding `QALifeSampler` into the
  existing `f1_quantum/sampler.py`. **Resolved:** new `f4_qalife/` package (keeps F4 additive and
  clearly optional; imports F1).
- [x] **Q2 (cohort composition):** How founders/generations/survivors fill the 12-tile grid.
  **Resolved:** defaults `--founders 4 --generations 3 --survivors 1` = 12 cells (one cell per
  lineage per generation), every cell becomes a tile sharing its founder `lineage_id`.
- [x] **Q3 (witness on the page):** Render `W_g` on the web page now, or ship it as
  `witness.json` + console only. **Resolved:** console + `witness.json` only — reuse F3 unchanged
  (epic §7); a witness strip is a later F3.x.
- [x] **Q4 (persist fate on the tile):** Add a nullable `fate: str = ""` to `TumorParams`, or
  keep fate internal to the loop. **Resolved:** keep it internal (preserves byte-identical Sampler
  shape for AC-1); revisit if F2 later wants fate→texture.
- [x] **Q5 (witness pair choice):** Measure the witness on the **founder→first-daughter** pair
  each generation, vs. an aggregate over all division pairs. **Resolved:** founder→first-daughter
  of the first lineage per generation (one clean 2-qubit witness, cheapest, matches the GHZ-cert
  precedent); a representative pair, not a population average.
- [x] **Q6 (fitness definition):** Exact classical fitness. **Resolved:** `score = 1.0·[fate ==
  proliferative] + 0.5·[fate == quiescent] + size_band_preference(mid)`; deterministic,
  documented in `fitness.py`, explicitly non-learned.

---

## 9. Post-Implementation Notes

**Built.** New `f4_qalife/` package (`witness.py`, `fitness.py`, `loop.py`, `sampler.py`,
`run_qalife.py`) + `GenerationRecord` in `common/datamodel.py` + README F4 section. `f1_quantum/`,
`f2_imaging/`, `f3_web/` untouched (F4 only imports from F1). End-to-end verified on Aer: evolved
12-tile cohort → **unmodified** F2 → F3 → self-contained page.

**Deviations from the plan:**
1. **Entrypoint location.** Plan §6 placed the entrypoint at `code/run_qalife.py` (top level). The
   repo convention (runlog `python -m <pkg>.<module>` from `code/`, with F1/F2/F3 entrypoints
   inside their package dirs) and the `OUTPUT_BASE = _HERE/../../research_runs` formula both require
   it to live **inside** the package. Moved to `f4_qalife/run_qalife.py`, invoked
   `python -m f4_qalife.run_qalife`. This also fixes the output dir to `QuantumPhantoms/research_runs`
   (the top-level placement resolved one directory too high).
2. **`--offspring` flag added.** The plan's selection (keep top `--survivors`) needs more candidates
   than survivors to select among. Added `--offspring` (default 4) = candidates measured per lineage
   per generation (one circuit, `offspring` shots). Guarded `offspring >= survivors`. Cohort size =
   `founders × generations × survivors` (default 4×3×1 = 12) is unchanged.
3. **Fate interference construction.** `_fate_prep` uses a Ramsey interferometer on the fate MSB
   (`h`–`rz(phase)`–`h`) so the phase dial is observable in the Z measurement (a plain `rz` before a
   Z-basis measure is invisible). Phase sweeps the fate mix proliferative/quiescent → necrotic. This
   is a minimal interference primitive; the systematic fixed-marginal interference sweep stays
   deferred (§3).
4. **Witness pair is a fixed division-channel characterisation** (`h`–`cx`–`ry(θ_mut)`), not seeded
   from each generation's actual genotype — it measures P1's entangling capability per generation.
   On noiseless Aer W_g is ~flat (≈2·cos θ_mut ≈ 1.91); the per-generation index exists so a Heron
   run shows the real decay. Representative pair, not a population average (plan Q5).

**Follow-ups for the developer:**
- No demo run dir or web page was committed (verification artifacts were cleaned). Generate one with
  the README F4 commands when you want a shareable page.
- Hardware path (`--backend ibm_heron`) is wired and banner-gated but **not run** (Peter only).
  Expect W_g to decay across generations and CHSH ≈ 1.9–2.6 on Heron; use those real values on any
  public page (Aer is noiseless and misleads).
- A web witness strip (rendering `witness.json`'s W_g per generation) is the natural next F3.x
  (deferred here to keep F3 unchanged, §3).
