# Plan P4 — Experiments, sweeps & headline figures

**Epic:** `plans/epic-quantum-galton-board.md` (Status: Draft — OQs resolved 2026-08-06)
**Plan ID:** P4 (`[MUST]`, depends on P3; gates P5, P6)
**Slug:** experiments-figures
**Author:** Claude (Opus)
**Date:** 2026-08-10
**Status:** Phase A Complete (2026-08-10) — Phase B awaits the Heron r2 allocation (≥ 2026-08-15). All §12 OQs accepted as proposed.

> **No automated tests (project directive, epic §3.6).** Verification is the offline
> correctness gate (`experiment_check.py`, ideal-only / aer-free / network-free), a manual
> inspection of the rendered figures, and a JSON-schema eyeball of the exported
> `summary.json` / `web/replay.json`. This plan lists no test files, no test suites, and no
> AC→test mapping. "How to verify" everywhere means the offline gate + manual inspection.

---

## 0. Two-phase split (the whole point of this plan)

**No live QC is available until 2026-08-15 (5 days out).** P4 is therefore cut into two
phases that are each independently implementable. `/implement-feature` runs **Phase A now**;
**Phase B** is picked up the day the Heron r2 allocation lands.

| Phase | When | Arms | Produces | Unblocks |
|-------|------|------|----------|----------|
| **A — sim experiments** | **now** | `ideal` (offline) + `noisy` (`from_backend` noise model; network, **zero QPU**) | full depth sweep as data, both figures rendered from sim, `summary.json` per sim arm, the knee from the noisy sim sweep, and `web/replay.json` with the `ideal`+`noisy` arms (the `hw` arm present but `null`) | **P5 can be built and demoed on simulated data today** |
| **B — hardware anchor** | **on QC (≥ 2026-08-15)** | `hw` (live Heron r2) | the OQ-3 hw depth subset with ≥3 seeded repeats, the knee with **hardware error bars**, the hw-vs-ideal / hw-vs-binomial distances, both figures **re-rendered with the hw overlay**, and `web/replay.json` updated with the populated `hw` arm | P5 gets its `hw` toggle lit; P6 gets the defended number with error bars |

The code written in Phase A is **arm-generic**: the sweep driver, the figure renderer, and
the replay exporter all already accept an `hw` arm. Phase B is therefore mostly *running the
hw matrix and re-invoking the same drivers*, plus two small, clearly-scoped edits
(error-bar overlay in `figures.py`, hw pairings in the exporter). No Phase-A module is
thrown away or rewritten in Phase B.

**Why the `noisy` arm is allowed in Phase A.** `arms._run_noisy`
(`code/arms.py:114`) builds its model with `AerSimulator.from_backend(connect(cfg.backend))`
— it reads the Heron r2 *calibration/noise model over the network* and then simulates
**locally**. It submits **no circuit to hardware** and consumes **no QPU allocation**. This
is exactly OQ-5's design (epic §3.5, §3.2) and is *not* "live QC". The user's "do not run
live QC" constraint binds the `hw` arm only. See OQ-4.1 if a fully-offline Phase A is
required instead.

---

## 1. Context

P4 is the experiments-and-figures ticket. The contracts it consumes are all frozen and on
disk:

- **P1** froze `WALK_SPEC`, the `run.json`/`summary.json` schema and their writers
  (`code/pipeline.py:83` `write_run`, `code/pipeline.py:110` `write_summary`), and the reuse
  wiring.
- **P2** froze the physics and the three-arm runner: `arms.run_arm(kind, steps, cfg, seed)`
  (`code/arms.py:155`) builds `walk.build_walk` once and dispatches on `ideal|noisy|hw`, each
  emitting one `run.json` whose `position_histogram` is a normalised, **string-keyed**
  `{position: probability}` over signed lattice positions `−n..+n` step 2.
- **P3** froze the analysis: the pure metric functions and the knee extractor in
  `code/metrics.py` (`to_int_hist`, `mean`, `variance`, `variance_exponent`, `tv_distance`,
  `hellinger`, `horn_contrast`, `entropy`, `local_variance_exponent`, `crossover_depth`) and
  the closed-form baselines in `code/analytics.py` (`analytic_hadamard_walk`,
  `binomial_reference`).

P4 is the *first* consumer that reads `runs/`, aggregates `research_runs/*_summary.json`,
feeds the P3 functions across the whole **depth × arm** matrix, renders the two headline
figures, and exports the replay JSON P5 embeds (epic §9 P4; P3 §3 explicitly defers all of
this to P4). P4 is where `pandas`/`matplotlib` first appear in this project (epic §9 P1
conventions confine them here); the core stays stdlib + qiskit + numpy.

**Scope boundary with P3 (verified against P3 §3, epic §9):** P4 does **not** add or change
any metric definition or the knee rule — it *calls* P3's frozen functions. P4 does **not**
add or rename any `run.json` / `WALK_SPEC` / `summary.json` **key** (frozen, epic §3.6); it
*populates* the already-present `summary.json` `per_depth[].metrics` slot
(`code/SCHEMA.md:87`). The `web/replay.json` file is a **new P4 artefact** (its shape is
frozen here for P5, OQ-6) — not a change to a frozen schema.

**Structural twin:** QuantumLife's `research_qtree.py` (`QuantumLife/code/research_qtree.py:396`)
— load per-seed `run.json`, aggregate `mean`/`std` per swept variable into a `summary.json`
with a `per_<variable>` list, round floats, print a one-line headline. P4 mirrors that
aggregation for the `per_depth` axis. (Note: QuantumLife renders its figures in the browser
and has **no** matplotlib; P4 renders static figures in Python because the epic P4 brief and
the IEEE paper (P6) require them — this is per the epic, not a deviation.)

**Inputs P4 consumes (verified on disk 2026-08-10):**
- `runs/*_run.json` — the per-`(arm, steps, seed)` files. `position_histogram` keys are
  **strings** (`code/pipeline.py:101`); the loader re-`int()`s them via `metrics.to_int_hist`
  before calling any metric. `meta.steps`, `meta.arm`, `meta.seed`, `meta.backend` locate
  each run in the matrix.
- Histograms are **sparse** (only occupied positions), and every P3 metric already treats a
  missing position as probability 0 — the loader must not densify.
- Existing on-disk data: only `ideal` runs (`runs/ideal_statevector_steps{2..18}_*`); **no**
  `noisy` and **no** `hw` runs exist yet. Phase A generates the `noisy` sweep; Phase B the
  `hw` matrix.

## 2. Acceptance criteria (from epic §9 P4 → source §Metrics, §THE VISUALIZATION)

Copied verbatim from the epic brief; IDs preserved. The **Phase** column says which phase
delivers each AC; ACs that begin in Phase A and are *enriched* in Phase B are marked `A→B`.

| AC | Phase | Covered by (file:line) |
|----|-------|------------------------|
| AC-4.1 | A→B | ✅ Phase A: `code/figures.py:69` `fig_horns_melting` — ideal grid + dashed `binomial_reference`, rendered `figures/horns_melting.{png,svg}`. Data: `code/sweep.py:136` `aggregate` mean histograms. hw row = Phase B. |
| AC-4.2 | A→B | ✅ Phase A: `code/figures.py:123` `fig_collapse_curve` — `horn_contrast_mean` (±std) + `a_local` twin-axis, knee marks; rendered `figures/collapse_curve.{png,svg}`. hw points/error bars = Phase B. |
| AC-4.3 | **B** | Deferred to Phase B (not claimed in Phase A). `code/sweep.py:136` `aggregate` already emits per-depth `variance_std`/`horn_contrast_std`; the `knee_depth_lo`/`_hi` band + `figures.py` error bars land with the hw runs. |
| AC-4.4 | A→B | ✅ Phase A: `code/replay_export.py:86` `export_replay` — `web/replay.json` with `walk_spec` verbatim, `arms:[ideal,noisy,hw]`, `per_arm.ideal` filled, `per_arm.hw:null`. `hw` populated in Phase B. |

- **AC-4.1** The depth sweep across the three arms renders the **horns-melting** figure —
  ideal twin horns morphing toward the classical hump as depth/noise grows (the paper's
  headline).
  *Approach (Phase A):* a small-multiples grid of `position_histogram` bar plots across a
  chosen set of depths, one row per available arm (`ideal`, `noisy`), with the closed-form
  `analytics.binomial_reference(n)` drawn as the dashed "classical hump" reference on each.
  Reading left→right (shallow→deep) and top→bottom (ideal→noisy) shows the ideal twin horns
  eroding toward the hump. *Phase B* adds an `hw` row (mean histogram over the OQ-3 repeats)
  at the hw depth subset.
- **AC-4.2** The M1+M3 sweep renders the **collapse-curve** figure — horn contrast and
  variance exponent falling with depth, marking the crossover knee.
  *Approach (Phase A):* a twin-axis line plot vs depth — `metrics.horn_contrast` (M3) on one
  axis, `metrics.local_variance_exponent` `a(t)` (M1) on the other, with a horizontal marker
  at the ballistic/diffusive midpoint `1.5` and a vertical marker at
  `metrics.crossover_depth(...)["knee_depth"]` (drawn per arm). *Phase B* overplots the hw
  points with vertical error bars from the seed spread and the hw knee.
- **AC-4.3** The extracted knee depth is reported with hardware error bars from the OQ-3
  repeats.
  *Approach (Phase B only):* `sweep.py` aggregates the ≥3 seeded hw repeats per depth into
  per-depth `variance`/`horn_contrast` **mean ± std**; the knee is extracted on the mean
  series and its uncertainty reported from the spread (a simple resample/bracket band, §6).
  In Phase A this AC is *not claimed* — the sim knee is reported without hardware error bars
  and the figure/summary label it "sim (no hw error bars — Phase B)".
- **AC-4.4** Per-depth, per-arm position histograms + fitted metrics are exported as replay
  JSON for the web arm (shape per OQ-6).
  *Approach (Phase A):* `replay_export.py` writes `web/replay.json` (OQ-6 = a single file
  P5 embeds into its self-contained HTML) carrying, per depth and per arm, the
  `position_histogram` (int-keyed→string on write, mirroring `run.json`) plus the fitted
  per-depth metrics (`variance`, `horn_contrast`, `entropy`, `a_local`), the classical
  `binomial_reference`, and the extracted knee. Phase A fills `ideal` and `noisy`; `hw` is an
  empty/`null` arm slot. *Phase B* populates the `hw` arm (mean histograms + error bars).

## 3. Out of scope (deferred, not omitted)

- Any metric definition, the knee combination rule, or a new metric → **P3** (frozen). P4
  only *calls* `metrics.py` / `analytics.py`.
- The interactive browser spectacle — cascade animation, depth slider, interference glow, the
  JS metric mirror and the JS↔Python parity gate → **P5**. P4 emits the *data* P5 replays and
  the *static* figures the paper uses; it renders no interactive HTML and writes no JS.
- The paper prose, `research/` docs, and the LaTeX thesis → **P6** (consumes P4's figures +
  knee).
- Any change to `walk_spec.py`, `walk.py`, `arms.py`, `pipeline.py`, `galton.py`, `metrics.py`,
  `analytics.py`, `walk_check.py`, `metrics_check.py` — all **frozen** (epic §3.6). P4 adds
  new modules only and *populates* the already-present `summary.json` `metrics` slot.
- A QRNG / QEaaS arm or provenance panel (epic §3.7).
- **The `hw` arm run itself, hw error bars, and any live-QC submission → Phase B**, not now
  (§0). Phase A must not call `run_arm("hw", …)`.

## 4. Decisions inherited from the epic (do not re-litigate)

- **Three arms, one circuit (§3.2 LOCKED).** P4 varies only the execution backend by calling
  the frozen `arms.run_arm`. It adds no bespoke circuit logic and no fourth arm (so **no**
  synthetic/parametric noise arm — the collapse-on-sim story rides on the `noisy`
  `from_backend` arm, OQ-5).
- **Sim arms sweep cheaply; hardware anchors a subset (§3.5 LOCKED).** `ideal`+`noisy` run the
  full `n = 2…N` sweep; `hw` runs the OQ-3 subset (a low anchor, 2–3 depths bracketing the
  predicted knee, one past it) with ≥3 seeded repeats. This is exactly the Phase-A/Phase-B
  cut of §0.
- **One-hot line encoding, signed positions `−n..+n` step 2 (OQ-1 LOCKED).** P4 reads
  `position_histogram` in this frame; it never re-derives bins.
- **`summary.json` shape is P1-frozen (epic §3.6).** P4 *populates* `per_depth` and its
  `metrics` slot; it adds no top-level key. Aggregation mirrors QuantumLife's mean/std style.
- **OQ-6 web delivery = single self-contained HTML with embedded replay.** P4 emits one
  `web/replay.json`; P5 inlines it. P4 does not build the HTML.
- **Python is the source of truth (§3.6 LOCKED).** The metrics in `summary.json` /
  `replay.json` are computed by `metrics.py`; P5's JS mirror is validated against these under
  the parity gate (P5, not P4).

## 5. The experiment driver — `sweep.py` (the depth × arm matrix, as data)

The single owner of "load `runs/`, aggregate `summary.json`, feed the P3 functions across the
matrix" (P3 §3 defers this here). Pure orchestration + numpy; it imports `arms`, `config`,
`pipeline`, `metrics`, `analytics`, never a plotting or web module.

**Two responsibilities, kept separate so Phase B reuses both:**

1. **Drive a sim sweep (Phase A).** `run_sim_sweep(arm, depths, seeds, cfg) -> list[str]`:
   loop `arms.run_arm(arm, n, cfg, seed)` over `depths × seeds`, returning the emitted
   `run.json` paths. `ideal` is deterministic → **one** seed; `noisy` uses `cfg.seeds`
   (≥3) so the sim collapse curve carries a spread (OQ-4.6). Phase B does **not** call this
   for `hw` — the `hw` matrix is driven by the frozen `galton.py --arm hw` (`galton.py:33`
   `_run_hw_matrix`), which already loops `hw_depths × seeds` and re-picks `best_chain` live.
2. **Aggregate any set of `run.json` into one `summary.json` (both phases).**
   `aggregate(arm, run_paths_or_dir) -> str`:
   - `load_run(path) -> (steps, seed, int_hist)` — `json.load`, then
     `metrics.to_int_hist(payload["position_histogram"])` (re-`int()`s the string keys,
     `metrics.py`), reading `meta.steps` / `meta.seed`.
   - Group the runs by `steps`. For each depth, across its seeds, compute per-seed
     `metrics.variance`, `metrics.horn_contrast`, `metrics.entropy`, then the **mean ± std**
     of each (QuantumLife style, `research_qtree.py:410`; `std(ddof=0)`), and the
     **mean position histogram** (average probability per position over seeds; used for the
     figure and replay). A single-seed arm (`ideal`) has `std = 0`.
   - Build the per-depth series `depths`, `variance_mean[]`, `contrast_mean[]` and hand them
     to `metrics.local_variance_exponent` and `metrics.crossover_depth(depths,
     variance_mean, contrast_mean)` to get `a_local(t)` and the `knee_depth` /
     `contrast_knee`.
   - Also compute, per depth, the M2 pairings **available in this phase** (OQ-4.7): Phase A
     → `tv_distance`/`hellinger` of `noisy` vs `ideal` and `noisy` vs
     `analytics.binomial_reference(n)`; Phase B → `hw` vs `ideal` and `hw` vs binomial
     (AC-3.2's named pairings). Pairings need the *other* arm's mean histogram, so
     `aggregate` accepts an optional `reference_arm_summary` for cross-arm distances, or is
     called after both sim summaries exist (§5 note).
   - Write via the **frozen** `pipeline.write_summary(meta, per_depth)`
     (`code/pipeline.py:110`) into `research_runs/`. `meta` carries `project`, `arm`,
     `backend`, `depths`, `shots`, `seeds`, `walk_spec` (verbatim), `timestamp`, `run_files`;
     each `per_depth[i]` carries `steps`, `run_files`, `position_histogram` (the mean, string
     keyed), and `metrics` = `{variance_mean, variance_std, horn_contrast_mean,
     horn_contrast_std, entropy_mean, entropy_std, a_local, tv_to_ideal, hellinger_to_ideal,
     tv_to_binomial, hellinger_to_binomial}` (nulls where a pairing is not available this
     phase). The sweep-level knee (`knee_depth`, `contrast_knee`, `rule`) goes in `meta`.
   - **No frozen key is added** — `per_depth[].metrics` and `per_depth[].position_histogram`
     are the P1 slots (`SCHEMA.md:87`); their *contents* are P4's to define.

`sweep.py` is runnable as a script (`python code/sweep.py --arm noisy --aggregate` etc.) via
its own small argparse that builds `config.load(args)`; it does not modify the frozen
`galton.py`.

## 6. The knee with hardware error bars (AC-4.3, Phase B) — how the uncertainty is formed

`metrics.crossover_depth` is a pure function of the `(depths, variances, contrasts)` series
(P3 §6) — deterministic, no error bars of its own. Phase B forms the hw knee uncertainty
**outside** the frozen function, in `sweep.py`:

- Each hw depth has ≥3 seeded repeats → per-depth `variance` samples and `horn_contrast`
  samples. The **reported knee** is `crossover_depth` on the per-depth **means**.
- The **error band** is a small nonparametric bracket: recompute `crossover_depth` on the
  `mean ± std` variance series (and, separately, on each single-seed series) and report the
  spread of resulting `knee_depth` values as `knee_depth_lo`/`knee_depth_hi` in the hw
  `summary.json` `meta`. This is an honest band from the seed spread, not a fabricated CI
  (matches the epic §3.5 caveat that the knee is a distribution, not a point). No random
  resampling (determinism, epic §6) — the band is the min/max over the ±std and per-seed
  series.
- `figures.py` draws the hw knee as a point with this band; P6 quotes it as "knee ≈ k
  (±band) at two-qubit error ≈ …" using the `meta.calibration.chain_twoq_err_mean` recorded
  by the hw arm (`arms.py:147`).

## 7. The figures — `figures.py` (matplotlib, confined here)

Renders from a `summary.json` (or two, for cross-arm overlays). Uses the non-interactive
`Agg` backend (`matplotlib.use("Agg")`) so it runs headless in the offline gate. Writes both
PNG (paper raster) and SVG (paper vector) into a new `figures/` directory. No business logic:
it reads already-aggregated series and draws.

- `fig_horns_melting(summaries, depths_to_show, out_stem) -> list[str]` (AC-4.1) — a
  small-multiples grid: columns = `depths_to_show` (a shallow→deep subset, e.g. `[2, 6, 10,
  14, 18]`), rows = arms present (`ideal`, `noisy`, and `hw` in Phase B). Each cell bar-plots
  that arm's mean `position_histogram` and overlays `analytics.binomial_reference(n)` as a
  dashed line — the "classical hump" the horns melt toward. Title states the arm/backend and
  that hw is absent in Phase A.
- `fig_collapse_curve(summary, out_stem) -> list[str]` (AC-4.2) — twin-axis vs depth:
  `horn_contrast_mean` (± std band) on the left axis, `a_local` on the right axis, a dashed
  horizontal at `1.5` (ballistic/diffusive midpoint) and a dashed horizontal at contrast
  half-max, and a vertical line at `meta.knee_depth` (and `contrast_knee`). Phase B overlays
  the `hw` points with vertical error bars and the hw knee band (§6).
- **Phase B edit surface:** both functions already loop over "arms present" and "points with
  optional error bars", so Phase B is: pass the hw `summary.json` in and enable the error-bar
  path — a small addition, not a rewrite.

Figure filenames: `figures/horns_melting.{png,svg}`, `figures/collapse_curve.{png,svg}`.

## 8. The replay export — `replay_export.py` (the P5 contract, OQ-6)

Writes one `web/replay.json` that P5 embeds verbatim into its single self-contained HTML
(OQ-6). This is the **frozen interface to P5** (the JS decoder + JS metric mirror read it),
so its shape is documented in `SCHEMA.md` (§9) and must not drift without a P5-visible
amendment.

`export_replay(summaries, knee, out_path="web/replay.json") -> str` writes:

```jsonc
{
  "walk_spec": { /* WALK_SPEC verbatim — P5 JS decoder parity, epic §4 */ },
  "encoding": "one_hot_line",
  "arms": ["ideal", "noisy", "hw"],       // hw present but its data null in Phase A
  "depths": [2, 4, 6, …],
  "binomial_reference": { "2": {"-2":0.25,…}, … },   // classical hump per depth (analytics)
  "per_arm": {
    "ideal": { "backend": "statevector",
      "by_depth": { "2": { "position_histogram": {"-2":0.5,"2":0.5},
                           "metrics": {"variance":…, "horn_contrast":…,
                                       "entropy":…, "a_local":…} }, … },
      "knee": { "knee_depth": null_or_number, "contrast_knee": …, "rule": "…" } },
    "noisy": { /* same shape; knee usually non-null — the collapse */ },
    "hw":    null                          // Phase A; Phase B fills same shape + error bars
  }
}
```

- Histogram keys are stringified ints (mirrors `run.json`, `pipeline.py:101`) so the JS
  decode is identical.
- `walk_spec` is embedded verbatim from `walk_spec.WALK_SPEC` (single source of truth; P5's
  hand-kept JS mirror is checked against it under the parity gate).
- Phase B rewrites the same file with `per_arm.hw` populated (`by_depth` mean histograms +
  `metrics` with `_mean`/`_std`, and a `knee` with `knee_depth_lo`/`_hi`). P5 needs no
  structural change — the `hw` toggle simply stops seeing `null`.

## 9. File Plan

All paths under `QuantumGaltonBoard/`. `from __future__ import annotations`, full type hints,
twin style (module docstrings stating the AC each block satisfies, snake_case), mirroring
`walk.py` / `metrics.py`. Core stays stdlib + qiskit + numpy; **P4 is where matplotlib
enters** (epic §9 P1 — confined here). No raw SQL (n/a). No business logic in the figure or
export modules (they read aggregated series and draw/serialise).

| Path | New/Edit | Phase | Responsibility |
|------|----------|-------|----------------|
| `code/sweep.py` | **New** | A (hw aggregation reused in B) | The depth×arm experiment driver (§5): `run_sim_sweep` (drive ideal/noisy), `load_run`, `aggregate` (per-depth mean±std, feed P3 metrics + knee, write `summary.json` via frozen `pipeline.write_summary`). Own argparse; imports `arms/config/pipeline/metrics/analytics`. numpy only (no matplotlib). |
| `code/figures.py` | **New** | A (hw overlay added in B) | The two headline figures (§7): `fig_horns_melting` (AC-4.1), `fig_collapse_curve` (AC-4.2). `matplotlib.use("Agg")`. Reads `summary.json`, writes `figures/*.{png,svg}`. No metric logic — calls into `metrics`/`analytics` only for the binomial reference and `a_local` recompute. |
| `code/replay_export.py` | **New** | A (hw filled in B) | The P5 replay contract (§8, OQ-6): `export_replay` → `web/replay.json` with `walk_spec` verbatim, per-arm per-depth histograms + metrics + knee, `hw` null in Phase A. numpy + json only. |
| `code/experiment_check.py` | **New** | A | Offline gate (epic §3.6), **ideal-only, aer-free, network-free**: drive a tiny ideal sweep (`n = 2,4,6`, one seed), aggregate to a `summary.json` in a temp dir, assert it carries every `per_depth[].metrics` field and a well-formed (possibly `None`) knee; render both figures to a temp dir with the `Agg` backend and assert the files exist and are non-empty; export a replay JSON and assert it validates against the §8 shape (arms list, `walk_spec` present, string-keyed histograms sum≈1). Prints one PASS line per check; exits non-zero on any breach (mirrors `metrics_check.py`). |
| `code/SCHEMA.md` | **Edit** | A | Add a "P4 experiments" section: the populated `summary.json` `per_depth[].metrics` field list + the sweep-level `meta.knee_depth`/`contrast_knee`(+ Phase-B `knee_depth_lo`/`_hi`); the **`web/replay.json` schema** (§8) as the frozen P5 contract; the `figures/` filenames. **No `run.json`/`WALK_SPEC`/`summary.json` key additions** — only documents how P4 fills existing slots + the new replay artefact. |
| `code/requirements.txt` | **Edit** | A | Add `matplotlib` under a "P4 figures only" note (imported only by `figures.py`; absent it, the sim sweep + aggregation + replay still run). Already-satisfied on this machine (mpl 3.10). |

**Phase B adds no new file.** It re-runs `galton.py --arm hw` (frozen) to produce the hw
matrix, then re-invokes `sweep.aggregate` / `figures.*` / `replay_export.export_replay` with
the hw runs included, plus the two small in-file edits already scoped in §6/§7/§8
(error-bar overlay, hw pairings, hw replay slot). Those edits land in `sweep.py`,
`figures.py`, `replay_export.py` — the files P4 itself created, not any frozen artefact.

## 10. Manual verification (no automated tests)

**Phase A (now):**
1. **Offline gate (all Phase-A ACs, no network/QPU/aer):** `python code/experiment_check.py`
   exits 0 — tiny ideal sweep aggregates, both figures render to temp, replay JSON validates.
2. **Ideal sweep already on disk:** the `runs/ideal_statevector_steps{2..18}_*` files exist;
   `python code/sweep.py --arm ideal --aggregate` writes one `research_runs/ideal_*_summary.json`
   with `a_local ≈ 2` across depths and `knee_depth = None` (ballistic never collapses — the
   honest ideal result, matching P3 §2 AC-3.5).
3. **Noisy sweep (network, zero QPU):** with `BACKEND=<heron r2 name>` set and the saved IBM
   account present, `python code/sweep.py --arm noisy --run --aggregate` drives
   `run_arm("noisy", …)` over `n = 2…N × seeds`, then aggregates. Confirm the noisy
   `horn_contrast_mean` **falls with depth** and, if the knee lies in range, `knee_depth`
   is a finite depth (the collapse). If no knee appears in `n ≤ N`, that is reported as
   `None` honestly (see OQ-4.2 — the sim sweep may be extended cheaply to surface it).
4. **Figures (AC-4.1/4.2):** `python code/figures.py` renders `figures/horns_melting.*`
   (ideal horns vs noisy erosion vs dashed binomial) and `figures/collapse_curve.*` (contrast
   + `a_local` vs depth, knee marked). Eyeball: ideal row stays horned; noisy row melts toward
   the dashed hump as depth grows.
5. **Replay (AC-4.4):** `python code/replay_export.py` writes `web/replay.json`; confirm
   `arms` lists all three, `per_arm.hw` is `null`, `walk_spec` matches `walk_spec.WALK_SPEC`,
   and every histogram's probabilities sum to ≈1. **This file is what unblocks P5 today.**
6. **No frozen artefact changed:** `git diff` touches only `code/sweep.py`,
   `code/figures.py`, `code/replay_export.py`, `code/experiment_check.py`, `code/SCHEMA.md`,
   `code/requirements.txt`, plus new `research_runs/*`, `figures/*`, `web/replay.json`.

**Phase B (on QC, ≥ 2026-08-15):**
7. **hw matrix:** `python code/galton.py --arm hw` (frozen driver) with `BACKEND` set runs
   the OQ-3 `hw_depths × seeds` on live Heron r2, re-picking `best_chain` per submission;
   confirm one `run.json` per `(depth, seed)` with `meta.qubit_list`/`meta.calibration` filled.
8. **hw knee with error bars (AC-4.3):** `python code/sweep.py --arm hw --aggregate` produces
   the hw `summary.json` with per-depth `mean ± std` and `meta.knee_depth`(+`_lo`/`_hi`).
9. **Figures + replay re-rendered with hw:** re-run `figures.py` / `replay_export.py` with the
   hw summary included; confirm the hw row/points appear with error bars and `per_arm.hw` is
   populated. P5's hw toggle now shows data.

## 11. Conventions & guardrails

- `from __future__ import annotations`; full type hints; twin style (`walk.py`, `metrics.py`):
  snake_case, module docstrings naming the AC each block satisfies.
- **Call P3, never re-implement it.** Every variance/contrast/entropy/knee number comes from
  `metrics.py`; every baseline from `analytics.py`. P4 owns *orchestration + rendering*, not
  physics or statistics definitions.
- **Do not mutate frozen artefacts.** `walk_spec.py`, `walk.py`, `arms.py`, `pipeline.py`,
  `galton.py`, `metrics.py`, `analytics.py`, `walk_check.py`, `metrics_check.py` are frozen
  (epic §3.6). Write `summary.json` only through `pipeline.write_summary`; add no schema key.
- **Phase A never touches the `hw` arm.** No `run_arm("hw", …)`, no live submission before the
  QC allocation. The offline gate is network-free and aer-free (ideal only).
- **`noisy` = network, zero QPU.** The only network the `noisy` arm uses is
  `from_backend`'s calibration read; it submits no hardware job (OQ-4.1). If the machine is
  offline, Phase A still delivers the ideal sweep + figures + replay (noisy arm fills when
  connectivity returns) — P5 can start on the ideal+binomial data.
- **Determinism.** Aggregation and the knee band use fixed `mean ± std`/per-seed brackets — no
  random resampling (epic §6). `ideal` is single-seed deterministic; `noisy` seeds come from
  `config.seeds`.
- **Matplotlib is Phase-A-and-later only, `Agg` backend, confined to `figures.py`.** No other
  module imports it; the sweep/aggregate/replay path never needs a display.
- **Sparse-safe.** Never densify a histogram; feed sparse int-keyed dicts straight to the P3
  functions.

## 12. Open questions — RESOLVED (2026-08-10, developer: "yes to all defaults and approve")

All seven accepted as proposed. OQ-4.1 = **noisy arm on** (network noise-model read, zero
QPU) — Phase A shows the real noise-collapse on sim.

- **OQ-4.1 — Is the `noisy` arm's `from_backend` network read allowed during the
  pre-allocation window?** **[proposal] Yes.** It reads the Heron r2 noise model over the
  network and simulates locally; it submits **no** hardware job and consumes **no** QPU
  allocation, so it is not "live QC". This is what makes the Phase-A horns-melting story real
  on sim. *If you want Phase A to be **100% offline** instead:* Phase A ships **ideal-only**
  (twin horns vs dashed binomial hump, no noise-collapse), the noisy sweep moves to "as soon
  as connectivity is available (still pre-QPU)", and P5 today shows the ideal↔classical morph
  without the noise-melt slider until then. Recommend the default (noisy on).
- **OQ-4.2 — Sim sweep depth range.** **[proposal]** Sweep `ideal`+`noisy` over
  `n = 2…N_MAX` (`config.DEFAULT_N_MAX = 20`, 22 qubits — fine for statevector and noisy Aer
  sampling). Because sim is cheap and the collapse may sit beyond the hw subset, allow the sim
  sweep to run **higher than the hw depths** if no noisy knee appears in `n ≤ 20` (bump
  `N_MAX` via env). The hw subset stays the OQ-3 bracket. Confirm 20 as the default sim
  ceiling.
- **OQ-4.3 — One plan file with two phases, or two plan files?** **[proposal] One file, two
  phases** (this document). It keeps the epic's single P4 row intact, lets `/implement-feature`
  run Phase A now against one contract, and lets Phase B be picked up later against the same
  file. The alternative (`plan-4a` / `plan-4b`) duplicates the shared context. Recommend one
  file.
- **OQ-4.4 — Figure format + location.** **[proposal]** PNG **and** SVG into a new
  `QuantumGaltonBoard/figures/` dir (`horns_melting.*`, `collapse_curve.*`); P6's thesis wires
  in the SVG. Confirm the dir name/format.
- **OQ-4.5 — `web/replay.json` as the P5 hand-off.** **[proposal]** One `web/replay.json`
  (§8 shape), embedded verbatim by P5's single self-contained HTML (OQ-6). Its schema is
  frozen in `SCHEMA.md` as the P5 contract. Confirm the filename/shape.
- **OQ-4.6 — Seeds/repeats for the sim arms.** **[proposal]** `ideal` = **1** seed
  (deterministic given the Statevector seed); `noisy` = `config.seeds` (**3**) so the sim
  collapse curve carries a `± std` band like the hw arm will. Confirm.
- **OQ-4.7 — M2 arm pairings per phase (P3 deferred this here, OQ-3.5).** **[proposal]**
  Phase A computes `tv`/`hellinger` for **noisy vs ideal** and **noisy vs binomial**; Phase B
  adds **hw vs ideal** and **hw vs binomial** (the AC-3.2 named pairings). Confirm.

## 13. Dependencies & ordering

- **Depends on:** P1 (Complete), P2 (Complete — `run_arm`, `run.json`), P3 (Complete — the
  metric functions + knee + baselines). **Gates:** P5 (consumes `web/replay.json` + the
  `WALK_SPEC` decoder; the parity gate compares JS against P4's Python-computed metrics) and
  P6 (consumes both figures + the knee-with-error-bars).
- **Runtime dependency added:** `matplotlib` (Phase A, `figures.py` only; already present,
  mpl 3.10). `qiskit-aer` (already present, 0.17.2) is used by the frozen `noisy` arm, not by
  new P4 code. numpy (present) does the aggregation. No pandas (not needed; numpy suffices).
- **Ordering within P4:** Phase A → (P5 starts on sim data + P6 drafts) → Phase B on QC
  (2026-08-15) → re-render figures/replay with hw → P6 finalises the defended number.

## 14. Post-Implementation (Phase A, 2026-08-10)

**Built.** Four new modules under `code/`, no frozen artefact touched:
- `sweep.py` — `run_sim_sweep` (drive ideal/noisy), `load_run`, `aggregate`
  (per-depth mean±std of `variance`/`horn_contrast`/`entropy` + mean histogram,
  a_local, `crossover_depth` knee, M2 pairings; writes via frozen
  `pipeline.write_summary`). Own argparse.
- `figures.py` — `fig_horns_melting` (AC-4.1), `fig_collapse_curve` (AC-4.2),
  `matplotlib.use("Agg")`, PNG+SVG into `figures/`.
- `replay_export.py` — `export_replay` → `web/replay.json` (§8 shape, `hw:null`).
- `experiment_check.py` — the offline gate (ideal-only, aer-free, network-free).

Doc edits: `code/SCHEMA.md` (+ "P4 experiments" section — the populated
`per_depth[].metrics`, the `web/replay.json` contract, the `figures/` names) and
`code/requirements.txt` (+ `matplotlib`, figures-only note).

**Verified (manual, no automated tests).**
- `python code/experiment_check.py` → exits 0, all three offline checks PASS.
- `python code/sweep.py --arm ideal --aggregate` → `research_runs/ideal_statevector_*_summary.json`,
  depths 2..18, `a_local`→~2 asymptotically (1.31 at n=2 rising to 1.999 at n=18 —
  small-n transient before the horns separate, the same regime `metrics_check.py`
  restricts to 8..20), `knee_depth=None` (ballistic never collapses — the honest
  ideal result, AC-3.5).
- `python code/figures.py` → `figures/horns_melting.{png,svg}` + `collapse_curve.{png,svg}`;
  eyeballed: ideal twin horns pull away from the dashed binomial hump as depth grows.
- `python code/replay_export.py` → `web/replay.json`; `arms=[ideal,noisy,hw]`,
  `per_arm.hw=null`, `walk_spec` matches `WALK_SPEC`, every histogram sums to ~1.
  **This file unblocks P5 today.**

**Follow-ups / notes for the developer.**
- **Noisy sweep not yet run** (needs a live `BACKEND` + saved IBM account for the
  `from_backend` calibration read, zero QPU). Run
  `python code/sweep.py --arm noisy --run --aggregate` when connectivity is up, then
  re-run `figures.py` / `replay_export.py` — both already accept the noisy summary
  and fill `per_arm.noisy`. Until then P5 has the ideal↔binomial data only.
- **Phase B (hw)** is unchanged from §0/§6/§7/§8: run `galton.py --arm hw`, then
  `sweep.aggregate("hw", …)` + the two small in-file edits (knee lo/hi band, hw row
  + error bars in `figures.py`, hw slot in `replay_export.py`).
- **Stray `code/runs/` directory.** A duplicate set of `ideal_*_run.json` exists
  under `code/runs/` (from earlier runs launched with a different cwd);
  `pipeline.RUNS_DIR` is `QuantumGaltonBoard/runs/` and all P4 code reads there.
  `code/runs/` is orphaned and can be deleted — not touched by this plan.
- The offline gate writes its tiny `n=2,4,6` ideal runs into `runs/` (adds the
  previously-absent `n=4`); they are valid deterministic ideal runs.

---

*Plan drafted per epic §9 P4 and the P1/P2/P3 frozen contracts. No automated tests (project
directive, epic §3.6) — verification is the offline gate (`experiment_check.py`) + manual
figure/JSON inspection. Two-phase split (§0): Phase A runs now on sim to unblock P5 today;
Phase B runs on the Heron r2 allocation from 2026-08-15. Status stays Draft until the
developer answers §12 and approves.*
