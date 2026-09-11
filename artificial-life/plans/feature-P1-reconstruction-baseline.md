# Feature Plan — P1: Reconstruction baseline

**Ticket:** P1 (stage, not a GitHub issue — this research repo decomposes epics into sequential stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09)
**Slug:** reconstruction-baseline
**Author:** Claude (Opus)
**Date:** 2026-09-09
**Status:** Complete (2026-09-09; OQ-1/OQ-2/OQ-3 → all proposed defaults accepted; "NO QC RUN" — hardware reused, not re-run)

> **No tests (repo convention, CD-7).** Verification is `--selftest` (operators vs paper
> closed-forms) + manual sim/figure inspection. No test framework, no test files.

---

## 1. Summary

P1 **re-anchors** the exact Alvarez-Rodriguez 2018 four-operator model on the R0-clean
two-file reproduction (`code/qalife.py` + `code/run_qalife.py`) and **banks the canonical
clean-witness reference** — the fixed baseline every P3 richness run is judged against.

Two things ship:

1. **The re-anchor** — confirm `python qalife.py --selftest` is green on the renamed model
   (all four operators verified vs the paper closed-forms), i.e. the honesty anchor still
   holds after R0. No model logic changes.
2. **The banked baseline** — a consolidated dataset + figure of the genealogical entanglement
   witness `⟨X^⊗W⟩` **vs width W** and **vs generation depth**, overlaying (a) the exact
   noiseless *ideal* curve, (b) the *hardware* confirm from the Month-4 live runs, and (c) the
   *separable null* `∏_i⟨X_i⟩`, verified ≈0 (CD-3). Archived to a stable location as the
   reference P3+ compares against.

The only new code is a **single standalone analysis/plotting script** — the project has **no
plotting infrastructure at all** (grep for `matplotlib`/`savefig` across `code/` + `research/`
returns nothing; the RUNBOOK's intended `stage4_evaluate.py` was never built). The script
imports the model as a library and reads existing driver JSON; it does **not** touch `code/`
(CD-1 keeps the main folder at exactly four files).

P1 deliberately does **not** scale to the coherence ceiling or run fresh live sweeps — that
is P2. P1's hardware content is a *confirm* using data already banked in `research_runs/`.

---

## 2. Acceptance criteria (verbatim from epic §9)

- [x] **AC-P1.1:** full model (self-replication `CX`, mutation `Ry(θ)` from QRNG, death
  amplitude-damping via bath ancilla, interaction `SWAP`) runs with `--selftest` green.
  **Covered by:** `python code/qalife.py --selftest` → all 7 checks `OK` + `SELFTEST PASS`,
  exit 0 (verified 2026-09-09). No code change. No code change —
  R0 already verified this; P1 re-confirms it as the baseline's honesty anchor. The four
  operators are `apply_self_replication` (`qalife.py:69`), `apply_mutation` (`:76`),
  `apply_aging_damping` (`:86`), `apply_interaction` (`:100`); QRNG mutation is exercised on
  the hardware confirm (sim/selftest use the PRNG stand-in `_sim_thetas`, `:522`).
- [x] **AC-P1.2:** bank `⟨X^⊗W⟩` vs W (and vs generations) from ideal sim + a small hardware
  confirm, with `separable_null` overlaid and verified ≈0 (CD-3).
  **Covered by:** `analysis/plot_baseline.py:36` (`ideal_witness_and_sep`, exact statevector
  joint + product null), `:76` (`load_hardware`, banked kingston runs), `:198` (CD-3 gate)
  emit `research/baseline_P1/baseline_P1.json` — ideal 0.879–0.993, hardware W=12 +0.301 /
  W=24 +0.038, `separable_null_max=1.86e-06 < 0.05`. The analysis script (§6.1) + figures (§6.2) with
  three series on the vs-W axis — `ideal` (exact statevector via `witness_ideal_by_gen`,
  `qalife.py:368`), `hardware` (from the banked Month-4 `ibm_kingston` unitary-death runs),
  and `separable_null` (exact product null + the driver's `separable_mean`), plus a
  vs-generation exact-ideal depth curve. The script asserts `separable_null` ≈0 (CD-3 gate,
  §8).
- [x] **AC-P1.3:** archive the baseline dataset + figure as the fixed reference every richness
  experiment (P3+) is judged against.
  **Covered by:** `research/baseline_P1/` holds `baseline_P1.json`,
  `baseline_P1_witness_vs_W.png`, `baseline_P1_witness_vs_gen.png`, `README.md` (verified
  present 2026-09-09). `research/baseline_P1/` holds `baseline_P1.json`, the two PNGs, and a
  `README.md` recording the numbers, the source run filenames, and the one-command regen
  recipe (§6.3). This directory is the immutable P1 reference.

**Conventions (epic §3):** witness is the sole quantum claim (CD-3); separable null must sit at
≈0 or the experiment is invalid (CD-3); sim-first then hardware-confirm (CD-7); honesty
invariant (CD-4).

**Out of scope (epic §9):** scaling to the ceiling (P2); any new biology/operator (P3).

---

## 3. Out of scope

- **Scaling W/G to the coherence ceiling and fresh live sweeps — that is P2** (AC-P2.1). P1's
  hardware is a *confirm* of the faithful model using data already in `research_runs/`, not a
  new scaling campaign. Default is **reuse** the banked Month-4 runs (see §11 OQ-1).
- **Wiring an ideal-witness column into the driver's `by_width` run schema** (`witness_ideal[W]`).
  Epic §4 assigns `witness_ideal` to **P2** (AC-P2.2, the live noiseless-confound overlay). P1
  computes the ideal **offline** in the analysis script (imports `qalife.witness_ideal_by_gen`),
  changing **no** code in `code/`. See §11 OQ-2.
- **Any new Darwinian operator, topology, or death mode** (P3). P1 is the faithful four
  operators only.
- **Error mitigation / ZNE / DD / heralding** (P2.3, CD-11).
- **Editing model/driver logic.** The model runs as-is; only a new sibling analysis script is
  added.
- **The web demo.** Extending `web/` is P4 (AC-P4.3); P1 emits static PNG + JSON only.

---

## 4. Cross-cutting decisions applied (from epic §3)

| ID | Applied here |
|----|--------------|
| CD-1 | No new file in `code/` — it stays at the four files. The analysis script lives in a new sibling `analysis/` dir and imports the model as a library. |
| CD-3 | The witness `⟨X^⊗W⟩` is the only banked quantum claim; every figure/series overlays the separable null, and the script fails closed if `separable_null` is not ≈0. |
| CD-4 | Honesty framing in the baseline `README.md`: sim saturates (~0.95) because it is noiseless; the *hardware* number is the real ceiling; diagonal metrics (alive/deepest) carry no quantum claim. |
| CD-5 | Report the k=2 headline and k=3 too; the survival test is `witness − sep > k·σ` (`entanglement_depth`, `qalife.py:407`; the driver already computes `survives` per width). |
| CD-6 | QRNG mutation is a hardware concern; P1 records the entropy provenance of whatever hardware source run it consumes (see §5 gap note + §9 R3). |
| CD-7 | Sim-first (exact ideal + selftest) then hardware-confirm; `--selftest` is the verification mechanism, no test framework added. |

---

## 5. Verified codebase facts (grounding the plan)

Confirmed by inspection on 2026-09-09 (current filenames post-R0):

- **Model writes only phenotype JSON, not the witness.** `qalife.py --sim` (main, `:532`;
  write at `:590–594`) persists `{meta, arms}` with `pheno_z, classical_z, alive_population,
  deepest_lineage` — **no witness**. The witness-from-counts helper
  `xbasis_witness_from_counts` (`:385`) returns `(joint, sep)` where `sep` **is** the
  separable null (computed `:401–404`).
- **The exact ideal witness already exists but is unused outside selftest.**
  `witness_ideal_by_gen(width, steps, thetas, interaction, death=...)` (`:368`) returns the
  noiseless `⟨X^⊗(g+1)⟩` per generation depth — Statevector for `unitary` death, DensityMatrix
  for `damping`. It is called **only** in `selftest` (`:498`). This is the natural building
  block for P1's ideal reference.
- **The driver measures the witness from counts into `by_width`.** `run_qalife.py` writes
  `{meta, by_width}`; each `by_width[str(W)]` = `witness_joint_mean, witness_joint_sigma,
  separable_mean, entanglement_signal, survives, alive_mean, deepest_mean`. σ handling:
  `ws = sqrt(std(reps)² + 1/shots)` (shot-noise floor in quadrature), `survives = signal >
  k·ws`. `meta` = `stage, model, backend, steps, interaction, routing, death, mut_scale,
  delta, gamma, alive_thresh, shots, repeats, k, widths, sim, genealogical_entanglement_depth_W`.
- **Density-matrix sim walls out early.** The driver sim path is `AerSimulator(method=
  "density_matrix")`; a DM of `n` qubits is `2^{2n}` — `nq = 2W` (unitary), so W≈7 (14q, 2^28)
  is the practical wall. The **exact statevector** path in `witness_ideal_by_gen` (unitary arm)
  is `2^{2W}` amplitudes and reaches ≈W=13 (26q, 2^26 ≈ 0.5 GB). **⇒ P1's ideal curve comes
  from the exact statevector helper, not the driver `--sim`.**
- **Month-4 hardware baseline (the confirm source).** `research/CONCLUSION_MONTH4.md` L142–159,
  backend `ibm_kingston` (Heron-r2), unitary death, `nn`, `mut_scale 0.08`, steps 3, k=2:
  W=12 → witness **+0.301 ± 0.017** (2σ=0.034, ALIVE); W=24 → **+0.038 ± 0.016** (2σ=0.032,
  ALIVE marginal); W=32 → buried in noise (dead). Headline: **entanglement depth W=24=48
  qubits, ~6× the paper's ~4-qubit origin.** Separable null ≈0. Banked as
  `research_runs/qalife_m4p2_*_ibm_kingston_*.json` (`by_width` schema).
- **Sim baseline (RUNLOG_MONTH4 Phase 1):** noiseless witness ≈ **0.93–0.97 at every width**,
  separable null **0.000** — sim saturates; the ceiling is a hardware number.
- **Model imports are library-safe.** `qalife.py` imports only stdlib + numpy + qiskit; it has
  a guarded `if __name__ == "__main__"` and no import-time side effects, so `import qalife`
  from a sibling dir (with `code/` on `sys.path`) is clean.
- **Schema gap — `meta.entropy_provenance` is not yet persisted.** Epic §4 lists it, but the
  driver `meta` (above) does not include it. P1 records the QRNG provenance *by source-run
  filename*; wiring the field into the driver is deferred (see §9 R3).

---

## 6. File plan

No changes under `code/` (CD-1). One new sibling code dir + one new artifact dir.

### 6.1 New — `artificial-life/analysis/plot_baseline.py` (the only new code)

Standalone, strict-typed (`from __future__ import annotations`, full type hints), PEP-8. No
business logic in any importable helper; a guarded `main()` under `if __name__ == "__main__"`.

Responsibilities:
1. **Path shim** — prepend `../code` to `sys.path` so `import qalife as q4` resolves without
   touching `code/`.
2. **Ideal (exact) curve** — for each W in the sim range (`SIM_WIDTHS`, default `2..12`),
   build reproducible mutation angles via `q4._sim_thetas(W, seed=100, mut_scale=0.08)` (same
   PRNG stand-in the selftest/sim use, so the ideal matches the modeled biology, not a
   zero-mutation clean GHZ), then:
   - `ideal[W] = q4.witness_ideal_by_gen(W, steps=3, thetas, "nn", death="unitary")[-1]`
     (final-depth exact witness).
   - `ideal_separable[W]` = exact product null `∏_i ⟨X_i⟩` from the statevector (compute via
     `qiskit.quantum_info.Statevector` single-qubit X expectation over the genotype-line
     qubits; expected ≈0 for the clean line). A small local helper mirroring the qubit
     selection `xbasis_witness_from_counts` uses (`qalife.py:385`).
3. **vs-generation curve** — at a fixed representative width `W_GEN` (default = max feasible
   sim width, 12): `witness_ideal_by_gen(W_GEN, steps=3, thetas, "nn", "unitary")` → the full
   per-generation array (shows the exact witness is depth-flat=1 for a clean GHZ and how
   mutation pulls it down per generation).
4. **Hardware series** — glob `research_runs/qalife_*_nn_unitary_ibm_kingston_*.json`, load the
   `by_width` dicts, and collect `(W, witness_joint_mean, witness_joint_sigma, separable_mean,
   survives)` for the unitary-death `ibm_kingston` runs (the Month-4 confirm). Record the
   source filenames for provenance.
5. **Emit** `research/baseline_P1/baseline_P1.json` (schema §6.4) and the two PNGs (§6.2).
6. **CD-3 gate** — assert `max(separable_null across ideal + hardware) < SEP_TOL` (default
   0.05); if not, print `[FAIL] separable null not ≈0` and exit non-zero (the baseline is
   invalid, CD-3).

CLI flags (all optional, sane defaults so a bare `python analysis/plot_baseline.py` reproduces
the banked baseline): `--sim-widths` (CSV, def `2,3,4,5,6,8,10,12`), `--w-gen` (def 12),
`--steps` (def 3), `--mut-scale` (def 0.08), `--seed` (def 100), `--k` (def 2.0),
`--hw-glob` (def the `ibm_kingston` unitary glob), `--sep-tol` (def 0.05), `--out-dir`
(def `../research/baseline_P1`).

### 6.2 New figures — under `research/baseline_P1/`

- `baseline_P1_witness_vs_W.png` — x=W; series: `ideal` (line, saturating ≈0.95), `hardware`
  (markers with ±k·σ error bars, decaying 0.30→0.038), `separable_null` (near-zero band).
  Annotate W\*=24 marginal-ALIVE and the k=2 / k=3 thresholds. Log-friendly y if needed.
- `baseline_P1_witness_vs_gen.png` — x=generation depth at `W_GEN`; the exact ideal witness
  per generation (=1 clean GHZ, mutation-decayed).

Matplotlib `Agg` backend (no display), `savefig(dpi=150)`.

### 6.3 New — `research/baseline_P1/README.md`

Records: what this baseline is (the P1 fixed reference, CD-3/CD-4 framing); the headline
numbers (sim ≈0.93–0.97 saturating; hardware W=12 +0.301, W=24 +0.038 marginal, W=32 dead);
the **source run filenames** consumed (hardware provenance, CD-6); the exact regen command
(`python analysis/plot_baseline.py`); and the honesty note (sim saturates because noiseless;
the ceiling is the hardware number; diagonal metrics carry no quantum claim).

### 6.4 `baseline_P1.json` schema (the banked reference)

```json
{
  "meta": {
    "stage": "P1", "model": "AlvarezRodriguez2018_full",
    "interaction": "nn", "death": "unitary",
    "steps": 3, "mut_scale": 0.08, "seed": 100, "k": 2.0,
    "ideal_method": "statevector_exact (qalife.witness_ideal_by_gen)",
    "sim_widths": [2,3,4,5,6,8,10,12],
    "hw_source_runs": ["qalife_m4p2_nn_unitary_ibm_kingston_20260825-090905.json", "..."],
    "hw_backend": "ibm_kingston"
  },
  "witness_vs_W": {
    "W":               [2,3,4,5,6,8,10,12],
    "ideal":           [/* exact final-depth witness */],
    "ideal_separable": [/* exact product null, ~0 */],
    "hardware": {
      "W":         [12,24],
      "witness":   [0.301,0.038],
      "sigma":     [0.017,0.016],
      "separable": [/* ~0 */],
      "survives_k2": [true,true],
      "survives_k3": [/* recomputed at k=3 */]
    }
  },
  "witness_vs_gen": {"W_fixed": 12, "gen": [0,1,2,3], "ideal": [/* per-gen exact */]},
  "separable_null_max": 0.0
}
```

### 6.5 Resulting layout

```
artificial-life/
  code/                       # UNCHANGED (four files, CD-1)
  analysis/
    plot_baseline.py          # NEW — imports qalife, reads research_runs/, emits baseline
  research/
    baseline_P1/              # NEW — the fixed P1 reference (AC-P1.3)
      baseline_P1.json
      baseline_P1_witness_vs_W.png
      baseline_P1_witness_vs_gen.png
      README.md
```

---

## 7. Implementation steps

1. **Re-anchor (AC-P1.1).** From `code/`: `python qalife.py --selftest` → capture `SELFTEST
   PASS` + exit 0. If red, stop — the baseline is invalid before it starts.
2. **Confirm the hardware source (OQ-1 default = reuse).** Identify the banked Month-4
   `ibm_kingston` unitary-death `by_width` runs in `research_runs/` (W=12, W=24). Record their
   filenames. *(If the developer chooses OQ-1 "fresh confirm", run the small live sweep in §7a
   first and glob that instead.)*
3. **Write `analysis/plot_baseline.py`** (§6.1) — path shim, exact-ideal curve + separable,
   vs-gen curve, hardware loader, JSON + figure emit, CD-3 separable gate.
4. **Generate the baseline:** `python analysis/plot_baseline.py` → writes
   `research/baseline_P1/{baseline_P1.json, *_vs_W.png, *_vs_gen.png}`. Verify the CD-3 gate
   passed (exit 0).
5. **Write `research/baseline_P1/README.md`** (§6.3) with the numbers + source-run provenance +
   regen command.
6. **Eyeball the figures** (§8): ideal saturates ≈0.95; hardware decays through the k=2 line
   near W=24; separable band sits on ≈0.

**§7a — optional fresh live confirm (only if OQ-1 → fresh):**
`python run_qalife.py --no-sim --backend ibm_kingston --widths 4,8,12 --steps 3
--interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_p1_hw`
(the Month-4 recipe, current filenames; chain-quality gate + QRNG fail-closed apply, CD-5/CD-6).

---

## 8. Manual verification (no tests — CD-7)

Run from `artificial-life/`:

- **AC-P1.1 — selftest green:** `python code/qalife.py --selftest` → exit 0; all four operators
  (`self-replication CNOT eta=1`, `interaction SWAP`, `aging unitary→dark`, `aging damping→dark`)
  and the witness checks (`GHZ ⟨X^n⟩=1`, `separable joint==product`) print `OK`.
- **AC-P1.2 — baseline banked + separable ≈0:** `python analysis/plot_baseline.py` exits 0
  (CD-3 gate passed); `baseline_P1.json` exists; `jq '.separable_null_max' baseline_P1.json`
  < 0.05; `witness_vs_W.ideal` values ≈0.9–0.97; `witness_vs_W.hardware.witness` = `[0.301,
  0.038]` (matching CONCLUSION_MONTH4). Open `baseline_P1_witness_vs_W.png` — three series
  present, separable band on ≈0, hardware error bars visible.
- **AC-P1.2 — vs-generation curve:** `witness_vs_gen.ideal[0]` ≈ modeled clean value, monotone
  behaviour consistent with mutation depth; `baseline_P1_witness_vs_gen.png` renders.
- **AC-P1.3 — reference archived:** `ls research/baseline_P1/` → `baseline_P1.json`,
  `baseline_P1_witness_vs_W.png`, `baseline_P1_witness_vs_gen.png`, `README.md`; the README
  names the hardware source runs and the regen command.
- **CD-1 preserved:** `ls code/*.py` still exactly `layout.py qrng_client.py qalife.py
  run_qalife.py` — no new file leaked into `code/`.

If the CD-3 separable gate fails (separable null not ≈0), the banked baseline is invalid — stop
and diagnose the qubit-selection / null computation, do not archive.

---

## 9. Risks

- **R1 — statevector memory wall.** Exact ideal is `2^{2W}` amplitudes; W>13 (≈26q) risks OOM.
  Mitigated: `SIM_WIDTHS` caps at 12; the ideal curve is meant to show *saturation*, not reach
  the hardware ceiling (that gap is the whole point). If a machine can't hold W=12, drop to 10.
- **R2 — hardware source mismatch.** The banked Month-4 runs must be `nn` + `unitary` +
  `ibm_kingston` to be the faithful-model confirm (the damping arm reads ≈0 by construction;
  longrange/teleport runs are a different topology). Mitigated: the glob pins
  `nn_unitary_ibm_kingston`; the loader records exactly which files it used.
- **R3 — entropy provenance not in schema.** The driver `meta` lacks `entropy_provenance`
  (epic §4 field not yet implemented). P1 records QRNG provenance *by source-run filename* only;
  wiring the field into the driver is deferred to P2 (where fresh live runs are produced). Noted
  in the baseline README, not blocking.
- **R4 — ideal-vs-modeled-biology ambiguity.** Using `_sim_thetas(mut_scale=0.08)` makes the
  ideal reflect the *modeled* mutation (≈0.95), not a mutation-free clean GHZ (=1.0). This is
  deliberate (the honest baseline the richness runs share); the README states it so P3 uses the
  same thetas convention.
- **R5 — no plotting deps installed.** matplotlib may be absent in the env. Mitigated: import
  guard with a clear message; JSON still writes even if the figure step is skipped (figures are
  regenerable from the banked JSON). See §11 OQ-3.

---

## 10. What P2 picks up next

P1 hands P2 the fixed clean-witness reference (`research/baseline_P1/`) and a proven library
call (`witness_ideal_by_gen`) for the noiseless overlay. P2 then scales W/G to the coherence
ceiling on **live** hardware, wires `witness_ideal` into the driver's `by_width` run schema as
the AC-P2.2 confound overlay, applies error mitigation as the first lever (CD-11), and runs the
AC-P2.4 decision gate. P1 deliberately does **not** scale or run fresh sweeps.

---

## 11. Open questions

**Resolution (2026-09-09): all three resolved to their proposed defaults.** OQ-1 → reuse banked
Month-4 `ibm_kingston` runs (no fresh live sweep in P1). OQ-2 → compute the ideal offline in
`analysis/plot_baseline.py`, leave `witness_ideal` driver wiring to P2. OQ-3 → new `analysis/`
dir for the tool + `research/baseline_P1/` for artifacts.

**OQ-1 (hardware confirm source) — proposed default: REUSE.** AC-P1.2 wants "a small hardware
confirm." Options: **(a, recommended)** reuse the banked Month-4 `ibm_kingston` unitary runs
(W=12, W=24) already in `research_runs/` — P1's job is to *bank the reference*, not to burn
queue/QRNG on a fresh scaling run (that is P2); the Month-4 points already confirm the faithful
model on hardware. **(b)** run one fresh small live sweep (§7a, W=4,8,12) to re-anchor with a
fresh receipt. Proposal: **(a) reuse**; the fresh live campaign belongs to P2.

**OQ-2 (where the ideal witness is computed) — proposed default: OFFLINE in the analysis
script.** Compute the exact ideal via `import qalife` in `analysis/plot_baseline.py` (no `code/`
change, CD-1 clean) vs adding a `witness_ideal[W]` column to the driver now. Epic §4 tags
`witness_ideal` as **P2**. Proposal: **offline in P1**, leave the driver wiring to P2 — keeps
P1 non-invasive and avoids pre-empting AC-P2.2.

**OQ-3 (analysis location) — proposed default: new `analysis/` dir + `research/baseline_P1/`
artifacts.** CD-1 forbids a 5th file in `code/`, so the plotting script needs a home. Proposal:
`artificial-life/analysis/plot_baseline.py` for the tool, `artificial-life/research/baseline_P1/`
for the banked dataset+figures (sits beside the existing runlogs). Alternative: a single
`artificial-life/baseline/` dir holding both. Proposal: **separate `analysis/` + `research/
baseline_P1/`**.

---

## 12. Ground rules honored

- Every AC (P1.1–P1.3) is copied verbatim from epic §9 and mapped to a file-plan item + a
  manual-verification step.
- Concrete paths + real line numbers/field names throughout; no placeholders.
- No tests planned (CD-7); verification is `--selftest` + figure/JSON inspection.
- `code/` untouched (CD-1); the witness is the only banked quantum claim and the separable null
  is gated ≈0 (CD-3); honest sim-saturates / hardware-is-the-ceiling framing (CD-4).
- Scale, fresh live sweeps, new biology, and mitigation are explicitly deferred to P2/P3
  (epic §9 out-of-scope respected).
- No raw SQL / no business logic in the wrong layer is N/A (no DB, no web) — the one new script
  keeps importable helpers pure with a guarded `main()`.
```

---

## 13. Post-implementation notes (2026-09-09)

**Built:** one new script `analysis/plot_baseline.py` (imports `qalife` via a `../code` path
shim, CD-1 clean) + the banked reference `research/baseline_P1/` (`baseline_P1.json`, two PNGs,
`README.md`). `code/` untouched — still exactly `layout.py qrng_client.py qalife.py
run_qalife.py`. `--selftest` green (7/7 OK). CD-3 gate passed (`separable_null_max=1.86e-06`).

**Banked numbers:** ideal (exact statevector, mut_scale=0.08) saturates **0.879 (W=12) → 0.993
(W=2)** — never decays (noiseless, CD-4). Hardware (`ibm_kingston`, reused Month-4): W=12 **+0.301
±0.017**, W=24 **+0.038 ±0.016** (marginal-ALIVE k=2, dies k=3), W=32 dead. Entanglement depth
**W=24 = 48 qubits**. Matches CONCLUSION_MONTH4 exactly.

**Deviations from plan (minor, non-blocking):**
- **`_sim_thetas` defaults** — plan §6.1 assumed `_sim_thetas(W, seed=100, mut_scale=0.08)` as
  the signature; real signature is `_sim_thetas(width, seed, mut_scale=1.0)` (`seed` required,
  `mut_scale` default 1.0). The script passes all three **explicitly**, so the plan's call site
  is valid — only the assumed defaults differed. No code change needed.
- **Ideal magnitude** — plan/§8 said ideal ≈0.93–0.97; exact statevector gives **0.879–0.993**
  (W=12 is 0.879, just under 0.9). The 0.93–0.97 in the plan came from the DM-driver sim; the
  exact-statevector number is the honest one and is what is banked. Still saturates high (CD-4
  intact).
- **Hardware widths** — banked all six kingston widths found (3,4,6,12,24,32), not just the
  {12,24} headline in the schema example — richer figure, same headline. `survives_k3`
  recomputed (`witness − sep > 3σ`): true through W=12, false at W=24 (marginal), consistent
  with the k=2 headline.
- **`witness_vs_gen.gen` axis** — plan schema example showed `[0,1,2,3]`; the true output of
  `witness_ideal_by_gen(W_GEN=12)` is a **12-element** per-depth array (g=0..11, line grown to
  width g+1 — the function's native axis), banked as such. The `[0,1,2,3]` example was
  illustrative; the vs-gen curve is the dense width-depth progression, noted in the README.

**Follow-ups for P2:** wire `witness_ideal` into the driver `by_width` schema (AC-P2.2) and
persist `meta.entropy_provenance` (epic §4, deferred here — provenance banked by source-run
filename only, R3). This baseline is the fixed reference P2/P3 compare against.
