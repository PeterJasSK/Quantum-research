# Plan P3 — Metrics & collapse-knee analysis

**Epic:** `plans/epic-quantum-galton-board.md` (Status: Draft — OQs resolved 2026-08-06)
**Plan ID:** P3 (`[MUST]`, depends on P2; gates P4, P5)
**Slug:** metrics-analysis
**Author:** Claude (Opus)
**Date:** 2026-08-10
**Status:** Complete (2026-08-10) — offline gate green, sim-sweep verified

> **No automated tests (project directive, epic §3.6).** Verification is the offline
> correctness gate (`metrics_check.py`), which runs the metric functions against the
> closed-form analytic references (ideal Hadamard walk = ballistic, binomial = diffusive)
> with no network and no QPU, plus a manual run of the metric series over a real `--sim`
> ideal sweep. This plan lists no test files, no test suites, and no AC→test mapping.
> "How to verify" everywhere means the offline gate + the manual sim-sweep inspection.

---

## 1. Context

P3 is the analysis ticket. P1 froze the contracts (`WALK_SPEC`, the
`run.json`/`summary.json` schema, the reuse wiring). P2 froze the physics: `build_walk`
(the one-hot-line Hadamard DTQW) and `run_arm` (three arms), each emitting a `run.json`
whose `position_histogram` is a normalised `{position: probability}` over the signed
lattice positions `-n..+n` step 2 (`code/arms.py:89`, decoded via
`walk_spec.decode_counts`, `code/walk_spec.py:39`). P3 turns those histograms into the
four metrics and the single defended fidelity number — the ballistic→diffusive crossover
depth (epic §3.1, §4 "The four metrics").

P3 delivers the frozen analysis interfaces the rest of the epic consumes (epic §4):

- **Metric functions** — `variance_exponent` (M1), `tv_distance` + `hellinger` (M2),
  `horn_contrast` (M3), `entropy` (M4). Pure functions over `{position: probability}`
  histograms and per-depth series. Python is the source of truth; P5 vendors a JS mirror
  and the parity gate (§3.6) proves the browser reproduces these exact values.
- **Analytic reference distributions** — the ideal Hadamard walk (ballistic baseline) and
  the classical binomial (diffusive baseline), as a *shared, importable* module. Epic §4
  names P3 the owner. P2's `walk_check.py` carries a local copy of the walk recursion
  purely for its own gate; P3 introduces the shared owner and cross-checks the two agree.
- **The crossover / knee extractor** — derives the ballistic→diffusive crossover depth
  from M1 (local variance exponent crossing the ballistic/diffusive midpoint) corroborated
  by M3 (horn-contrast collapse). This is the single defended metric (epic §3.1); P4
  reports it with hardware error bars, P6 defends it.

**Structural twin:** QuantumLife's analysis split — pure metric functions consumed by a
sweep/summary driver, with an offline `*_check.py` gate asserting the metrics against
closed-form baselines. P3 mirrors that: `metrics.py` (pure) + `analytics.py` (baselines) +
`metrics_check.py` (gate). No pandas/matplotlib here — those stay confined to P4's figure
code (epic §9 P1 conventions).

**Inputs P3 consumes (verified on disk 2026-08-10):**
- `position_histogram` per run — `{position: probability}`, int lattice positions, sums to
  1 (`code/arms.py:89`, `code/pipeline.py:101` stringifies the keys on write, so a loader
  must re-`int()` them). P3 metric functions take **int-keyed** histograms; a small
  `to_int_hist` normaliser bridges the string-keyed `run.json` form.
- Histograms are **sparse** — only occupied positions appear (the one-hot decode omits
  zero-probability bins, `walk_spec.py:56`). Every metric must treat a missing position as
  probability 0 (union-of-support for pairwise distances).
- `steps` (walk depth `n`) is available in `meta.steps`; positions for an `n`-step walk are
  `-n..+n` step 2 (`walk_spec.bin_to_position`).

**Scope boundary with P4 (verified against epic §9):** P3 owns the metric *functions* and
the knee *extractor* as pure, importable code plus their offline gate. P4 owns loading the
`run.json` sweep, aggregating `summary.json`, feeding these functions across the depth×arm
matrix, rendering figures, and exporting replay JSON. P3 does **not** read `runs/`, does
**not** write `summary.json`, and does **not** render figures. The offline gate builds its
own histograms from `analytics.py` (no I/O), so P3 is fully verifiable before any sweep
exists.

## 2. Acceptance criteria (from epic §9 P3 → source §Metrics)

Copied verbatim from the epic brief; IDs preserved. Each AC's planned owner:

| AC | Covered by (file:line) |
|----|------------------------|
| AC-3.1 | ✅ `code/metrics.py:51` `variance`, `code/metrics.py:62` `variance_exponent` + gate `code/metrics_check.py:65` `check_exponent` (real sim sweep n≥8: a=1.976, r²=1.0) |
| AC-3.2 | ✅ `code/metrics.py:94` `tv_distance`, `code/metrics.py:104` `hellinger` + gate `code/metrics_check.py:77` `check_distances` |
| AC-3.3 | ✅ `code/metrics.py:117` `horn_contrast` + gate `code/metrics_check.py:90` `check_contrast` |
| AC-3.4 | ✅ `code/metrics.py:150` `entropy` + gate `code/metrics_check.py:102` `check_entropy` (see §13 note: entropy ordering corrected vs plan heuristic) |
| AC-3.5 | ✅ `code/metrics.py:163` `local_variance_exponent`, `code/metrics.py:212` `crossover_depth` + gate `code/metrics_check.py:123` `check_knee` |

- **AC-3.1** M1 variance growth exponent: fit σ² ∝ tᵃ across depths; report `a` per arm
  (a→2 ballistic, a→1 diffusive).
  *Approach:* `variance(hist)` returns σ² = Σ p(x)·x² − (Σ p(x)·x)² for one histogram.
  `variance_exponent(depths, variances)` does a degree-1 least-squares fit of
  `log σ² = a·log t + b` (numpy `polyfit` on the log-log points) and returns
  `{"a": …, "b": …, "r2": …}`. The gate asserts `a ≈ 2` (±tol) for the analytic ideal
  walk over `steps 2..N_check` and `a ≈ 1` (±tol) for the binomial reference.
- **AC-3.2** M2 total-variation and Hellinger distance: hardware vs ideal, and hardware vs
  classical binomial, per depth.
  *Approach:* `tv_distance(p, q) = 0.5·Σ|p−q|` and `hellinger(p, q) =
  (1/√2)·√(Σ(√p−√q)²)` over the union of the two histograms' supports (missing = 0). Both
  are arm-agnostic pairwise functions; the *specific pairings* (hw vs ideal, hw vs
  binomial, and — for the full sim sweep — noisy vs ideal) are selected in **P4**
  (OQ-3.5). The gate asserts `d(p,p)=0`, symmetry, and range `[0,1]`.
- **AC-3.3** M3 peak-splitting visibility (horn contrast) vs depth — the collapse curve.
  *Approach:* `horn_contrast(hist)` = `(P_horn − P_centre)/(P_horn + P_centre)` where
  `P_centre` is the probability at the most-central position(s) (position 0 for even `n`;
  the mean of ±1 for odd `n`, OQ-3.3) and `P_horn` is the max probability over the
  remaining off-centre positions. Twin horns → positive and high; a diffusive central hump
  → the centre dominates → contrast →0/negative. The per-depth series is the collapse
  curve. The gate asserts `horn_contrast(ideal) > 0` (high) and `horn_contrast(binomial)`
  is markedly lower.
- **AC-3.4** M4 Shannon entropy of the output distribution vs depth.
  *Approach:* `entropy(hist, base=2.0)` = −Σ p·log₂ p over occupied positions
  (0·log0 ≡ 0), in bits (OQ-3.4). The per-depth series is entropy vs depth. The gate
  asserts entropy is `≥0`, `0` for a delta histogram, and larger for the diffusive hump
  than for the twin-horn walk at matched depth (heuristic sanity, not a hard physics law).
- **AC-3.5** The crossover/knee depth is extracted from M1+M3 and is reproducible from the
  sweep data (the single defended metric, §3.1).
  *Approach:* `local_variance_exponent(depths, variances, window=3)` returns `a(t)` per
  depth from a sliding log-log fit (OQ-3.2). `crossover_depth(depths, variances, contrasts)`
  returns `{"knee_depth", "exponent_knee", "contrast_knee", "rule"}`: the primary
  `knee_depth` is the (linearly interpolated) depth where `a(t)` first falls through the
  ballistic/diffusive midpoint `1.5`; `contrast_knee` is the depth where `horn_contrast`
  first drops below half its sweep maximum (the "randomness-shape half-life" framing,
  source §Thesis), reported as corroboration (OQ-3.1). Deterministic and reproducible from
  the `(depths, variances, contrasts)` series alone. The gate asserts: a pure-ideal
  (ballistic) sweep yields **no** knee (`a(t)` stays ≈2), and a synthetic ideal→binomial
  morph sweep yields a knee inside the swept range.

## 3. Out of scope (deferred, not omitted)

- Loading `run.json` from `runs/`, aggregating the depth×arm matrix, and writing
  `summary.json` → **P4**. P3 metric functions operate on in-memory histograms/series; the
  offline gate synthesises its own from `analytics.py`.
- Rendering the horns-melting figure and the collapse-curve figure → **P4** (matplotlib
  confined there).
- The replay-JSON export for the web arm → **P4**.
- The JS metric mirror and the JS↔Python parity gate → **P5** (P3 only guarantees Python is
  the source of truth and documents each metric precisely enough to mirror by hand).
- Editing the P2-frozen `walk_check.py` to absorb its local walk recursion. P2 plan §3
  says P3 "may later replace/absorb it"; P3 chooses **not** to edit the frozen gate (avoid
  churn on a passing gate) — instead it introduces the shared owner in `analytics.py` and
  cross-checks agreement in `metrics_check.py` (OQ-3.6).
- Any new `run.json`/`WALK_SPEC`/`summary.json` schema keys — all frozen (epic §3.6).
- No QRNG / QEaaS arm or provenance metric (epic §3.7).

## 4. Decisions inherited from the epic (do not re-litigate)

- **The four metrics are M1–M4 exactly as epic §4 defines them** — variance exponent,
  TV/Hellinger, horn contrast, entropy. The defended metric is the M1+M3 crossover depth
  (epic §3.1). P3 adds no fifth metric.
- **Python is the source of truth (§3.6 LOCKED):** every metric is computed in Python;
  P5's JS is a vendored mirror validated by the parity gate. P3 must keep each definition
  simple and fully specified so the hand-mirror is unambiguous.
- **Analytic references are closed-form baselines (§4 LOCKED):** the ideal Hadamard walk
  and the binomial. No fitted/empirical baselines.
- **One-hot line encoding, signed positions `−n..+n` step 2 (OQ-1 LOCKED):** metrics read
  the `position_histogram` in this frame; do not re-derive bins.
- **Fixed Hadamard coin (OQ-4 LOCKED):** the ideal analytic reference uses the symmetric
  coin `(|0>+i|1>)/√2` (matching `walk.build_walk`, `code/walk.py:82`); no other coin in v1.
- **No new runtime dependency:** `numpy` is already used by the core (`walk_check.py:27`,
  `SCHEMA.md` "Dependencies"); P3 uses stdlib + `numpy` only. No pandas/matplotlib (P4).

## 5. The metric functions — `metrics.py` (the frozen analysis interface)

All functions are pure (no I/O, no globals) and take **int-keyed** histograms
`dict[int, float]` normalised to sum 1. A `to_int_hist(hist: dict) -> dict[int, float]`
helper converts the string-keyed `run.json` `position_histogram` form (`pipeline.py:101`)
so P4 can feed loaded runs directly; the gate feeds `analytics.py` output (already int-keyed).

**M1 — variance growth exponent (AC-3.1).**
- `mean(hist) -> float` = Σ p(x)·x.
- `variance(hist) -> float` = Σ p(x)·x² − mean². (Symmetric ideal walks have mean ≈ 0; the
  subtraction keeps it honest for the noisy/hw arms whose mean may drift.)
- `variance_exponent(depths: list[int], variances: list[float]) -> dict[str, float]`:
  degree-1 `numpy.polyfit(log(depths), log(variances), 1)` → `{"a", "b", "r2"}` where `a`
  is the slope (exponent), `b` the intercept, `r2` the coefficient of determination of the
  log-log fit. Requires `len(depths) >= 2`; raises `ValueError` otherwise. Guards against
  non-positive variance (a delta/zero-variance depth is dropped with a documented rule, not
  fed to `log`).

**M2 — distribution distance (AC-3.2).**
- `tv_distance(p: dict[int,float], q: dict[int,float]) -> float` = `0.5·Σ_{x∈supp(p)∪supp(q)} |p(x)−q(x)|`.
- `hellinger(p, q) -> float` = `(1/√2)·√(Σ_{x} (√p(x) − √q(x))²)`.
- Both range `[0,1]`, are symmetric, and are 0 iff `p==q`. Support is the union; a position
  absent from one dict contributes with value 0.

**M3 — horn contrast / peak-splitting visibility (AC-3.3).**
- `horn_contrast(hist) -> float` = `(P_horn − P_centre)/(P_horn + P_centre)` with:
  - `P_centre` = `hist.get(0, 0.0)` when `steps` is even (position 0 exists), else the mean
    of `hist.get(-1,0)` and `hist.get(1,0)` when odd (OQ-3.3).
  - `P_horn` = max probability over positions with `|pos|` greater than the central band
    used above (i.e. exclude the position(s) that defined `P_centre`).
  - Returns `0.0` when both are 0 (empty/degenerate). Ballistic twin horns → strongly
    positive; a central hump → `P_centre` dominates → negative/→0. This monotone sign flip
    is what makes the per-depth series a clean collapse curve.
- `steps` is inferred from the histogram support (`max(|pos|)`), so `horn_contrast` needs
  only the histogram; parity of `steps` = parity of that support.

**M4 — output entropy (AC-3.4).**
- `entropy(hist, base: float = 2.0) -> float` = `−Σ_{x: p>0} p·log_base(p)`, in bits by
  default (OQ-3.4). `0·log0 ≡ 0`. Raw (un-normalised) Shannon entropy is primary; P4/P6 may
  additionally divide by `log_base(n+1)` for a normalised view, but P3 returns raw bits.

## 6. The crossover / knee extractor (AC-3.5) — the single defended metric

The knee is a **depth**, so the global M1 fit (`variance_exponent`) is insufficient — P3
adds a *local* exponent and combines it with the horn-contrast collapse.

- `local_variance_exponent(depths, variances, window: int = 3) -> list[tuple[int, float]]`:
  for each depth `t`, fit `log σ² = a·log t + b` over the `window` depths centred on `t`
  (forward/backward 2-point at the ends), returning `[(t, a_local(t)), …]` (OQ-3.2).
- `crossover_depth(depths, variances, contrasts, *, midpoint: float = 1.5) ->
  dict[str, float | None]`:
  1. Compute `a_local(t)`. The **primary knee** = the linearly-interpolated depth at which
     `a_local(t)` first crosses down through `midpoint` (1.5 = midway between ballistic 2
     and diffusive 1). If `a_local(t)` never falls to `midpoint` across the sweep → `None`
     (no collapse observed in range — an honest result, not an error).
  2. The **contrast knee** = the depth at which `contrasts` first drops below
     `0.5·max(contrasts)` (half of the peak horn contrast — the "randomness-shape
     half-life", source §Thesis), interpolated between bracketing depths; `None` if it
     never does.
  3. Return `{"knee_depth": <primary>, "exponent_knee": <primary>, "contrast_knee":
     <secondary>, "rule": "a_local crosses 1.5; contrast half-max corroborates"}`.
- **Combination rule (OQ-3.1):** the reported `knee_depth` is the M1 exponent crossing;
  `contrast_knee` corroborates. Rationale: epic §3.1 names the ballistic→diffusive exponent
  crossover the defended metric; horn contrast is the headline *visual* but is noisier near
  collapse, so it corroborates rather than defines. Both are returned so P4/P6 can report
  the pair and their agreement.
- **Reproducibility:** the extractor is a pure function of the `(depths, variances,
  contrasts)` series — no randomness, no I/O — so re-running on the same `summary.json`
  series yields an identical knee (AC-3.5). P4 supplies the series from real sweep data;
  the gate supplies synthetic series.

## 7. The analytic references — `analytics.py` (shared baselines, epic §4)

Closed-form `{position: probability}` distributions the arms are compared against. P3 owns
the shared, importable versions (epic §4); P2's `walk_check.py` keeps its own local copy
untouched (OQ-3.6).

- `analytic_hadamard_walk(steps: int) -> dict[int, float]` — the ideal ballistic reference:
  the position-space Hadamard DTQW with the symmetric coin `(|0>+i|1>)/√2`, over positions
  `−n..+n` step 2. Same construction as `walk_check.analytic_hadamard_walk`
  (`code/walk_check.py:37`); P3 is now the canonical owner. `metrics_check.py` asserts this
  equals `build_walk` + `Statevector` (aer-free) to `TOL`, so the shared reference is pinned
  to the P2 physics.
- `binomial_reference(steps: int) -> dict[int, float]` — the classical diffusive baseline:
  `p(bin j) = C(n, j) / 2ⁿ` at position `2j − n` for `j = 0..n` (a fair-coin Galton board →
  binomial B(n, ½) mapped into the same signed-position frame). σ² = n → variance exponent
  `a = 1` (diffusive). Computed with `math.comb` (exact) then normalised.

Both return sparse int-keyed histograms in the same frame the arms produce, so every metric
consumes references and measured runs identically.

## 8. File Plan

All paths under `QuantumGaltonBoard/`. `from __future__ import annotations`, full type
hints, PSR-equivalent Python style (snake_case, module docstrings mirroring `walk.py` /
`walk_check.py`). Core stays stdlib + `qiskit` + `numpy` (no new dependency; no
pandas/matplotlib — P4). No raw SQL (n/a). No business logic outside the pure functions.

| Path | New/Edit | Responsibility |
|------|----------|----------------|
| `code/analytics.py` | **New** | The shared closed-form baselines (§7): `analytic_hadamard_walk(steps)` (ideal ballistic) and `binomial_reference(steps)` (classical diffusive). Pure, stdlib + numpy. Imported by `metrics_check.py` and (later) P4. Owns no metric logic. |
| `code/metrics.py` | **New** | The frozen metric functions (§5) + the knee extractor (§6): `to_int_hist`, `mean`, `variance`, `variance_exponent` (M1), `tv_distance`, `hellinger` (M2), `horn_contrast` (M3), `entropy` (M4), `local_variance_exponent`, `crossover_depth` (M1+M3 knee). Pure functions over histograms/series; no I/O, no globals, no run.json loading (P4). stdlib + numpy. |
| `code/metrics_check.py` | **New** | The P3 offline correctness gate (epic §3.6). No network, no QPU, aer-free. Builds histograms from `analytics.py` and asserts: M1 exponent ≈2 (ideal) / ≈1 (binomial); M2 distances are 0 on identical, symmetric, in `[0,1]`; M3 contrast high for horns / low for the hump; M4 entropy ≥0, larger for the hump; the knee extractor finds no knee on a ballistic sweep and a knee on a synthetic ideal→binomial morph; and `analytics.analytic_hadamard_walk` equals `build_walk`+`Statevector` to `TOL` (pins the shared reference to P2). Prints one PASS line per check; exits non-zero on any breach (mirrors `walk_check.py`). |
| `code/SCHEMA.md` | **Edit** | Add a "P3 metrics" section documenting each metric's exact definition (the formulas in §5/§6), the knee combination rule (OQ-3.1), the odd-`n` horn-centre rule (OQ-3.3), the entropy base (OQ-3.4), and that Python is the source of truth with P5 obliged to mirror these values under the parity gate. No `run.json`/`WALK_SPEC`/`summary.json` key changes (frozen). |

**No new frozen schema and no edits to frozen code.** P3 adds analysis modules only;
`walk_spec.py`, `pipeline.py`, `walk.py`, `arms.py`, and `walk_check.py` are untouched. The
`summary.json` `per_depth[].metrics` slot (already present, `SCHEMA.md:87`) is *populated by
P4* using these functions — P3 defines the functions, not the aggregation.

## 9. Manual verification (no automated tests)

1. **Offline gate (all ACs):** `python code/metrics_check.py` exits 0 — every M1–M4 and
   knee assertion (§8) passes, and the shared analytic walk matches `build_walk`+
   `Statevector` to `TOL`. This is the primary gate and runs in the minimal aer-free
   environment with networking unavailable.
2. **M1 on a real ideal sweep (AC-3.1):** run the P2 ideal arm across depths, e.g.
   `for n in 2 4 6 8 10; do python code/galton.py --sim --arm ideal --steps $n --seed 100;
   done`, then in a REPL feed the resulting `position_histogram`s (via `metrics.to_int_hist`)
   through `metrics.variance` + `metrics.variance_exponent` and confirm `a ≈ 2` (ballistic).
   *(Loading the run.json files is a manual REPL step here; the automated loader is P4.)*
3. **M3 collapse-curve shape (AC-3.3):** confirm `horn_contrast` is strongly positive for
   the ideal twin-horn histograms and drops toward/below 0 for `analytics.binomial_reference`
   at matched depth — the sign flip the collapse curve rides on.
4. **Knee reproducibility (AC-3.5):** call `metrics.crossover_depth` twice on the same
   synthetic ideal→binomial series and confirm an identical `knee_depth`; confirm a
   pure-ideal series returns `knee_depth is None`.
5. **No frozen artefact changed:** `git diff` touches only `code/analytics.py`,
   `code/metrics.py`, `code/metrics_check.py`, `code/SCHEMA.md` — `walk_spec.py`,
   `pipeline.py`, `walk.py`, `arms.py`, `walk_check.py` are unmodified.

## 10. Conventions & guardrails

- `from __future__ import annotations`; full type hints; twin style (`code/walk.py`,
  `code/walk_check.py`): snake_case, module docstrings stating the AC each block satisfies.
- **Pure functions only.** No metric reads a file or the network. All I/O (run.json load,
  summary.json write, figures) is P4. This keeps the parity gate (P5) trivial to mirror.
- **Sparse-safe.** Every metric treats an absent position as probability 0 and uses the
  union of supports for pairwise distances — never assume a dense contiguous array.
- **Do not mutate frozen artefacts.** `WALK_SPEC`, `decode_counts`, `pipeline.py`,
  `walk.py`, `arms.py`, and the passing `walk_check.py` are frozen. P3 adds new modules; if
  the shared analytic reference must diverge from `walk_check.py`'s local copy, that is an
  epic amendment, not a silent edit (OQ-3.6).
- **Guard the log-log fit.** `variance_exponent` / `local_variance_exponent` must reject
  non-positive variances and `< 2` points with a clear `ValueError`, never emit a `nan`
  slope silently.
- **Determinism.** No randomness anywhere in P3; the knee is a pure function of the series.

## 11. Dependencies & ordering

- **Depends on:** P1 (Complete), P2 (Complete — supplies `position_histogram` shape and the
  `build_walk`+`Statevector` reference the gate pins against). **Gates:** P4 (feeds these
  functions across the sweep, writes `summary.json`, renders figures) and P5 (vendors the JS
  metric mirror; parity gate compares against these Python values).
- **No new runtime dependency:** stdlib + `numpy` (already present) + `qiskit`
  (`Statevector`, for the gate's cross-check only). No pandas/matplotlib (P4). Record
  nothing new in `code/requirements.txt`.

## 12. Open questions — RESOLVED (2026-08-10, developer: "accept all defaults and approve")

All six accepted as proposed below.


- **OQ-3.1 — Knee combination rule (M1 vs M3).** **[proposal]** Primary `knee_depth` = the
  depth where the *local* variance exponent `a(t)` crosses down through the
  ballistic/diffusive midpoint `1.5`; the horn-contrast half-max depth is reported as a
  corroborating `contrast_knee`, not as the defended number. Rationale: epic §3.1 names the
  exponent crossover the defended metric; contrast is the headline *visual* but noisier near
  collapse. Both are returned so P4/P6 can show their agreement.
- **OQ-3.2 — Local-exponent window size.** **[proposal]** A sliding **3-point** log-log fit
  (`t−1, t, t+1`), with forward/backward 2-point fits at the sweep ends. Small window =
  responsive knee; its sensitivity to window size is flagged as a P6 threat-to-validity, not
  engineered away.
- **OQ-3.3 — Horn-contrast centre for odd `n` (no position-0 bin).** **[proposal]**
  `P_centre` = position 0 for even `n`; the mean of positions ±1 for odd `n`. `P_horn` = max
  over the remaining off-centre positions. Documented in `SCHEMA.md`.
- **OQ-3.4 — Entropy base and normalisation.** **[proposal]** Shannon entropy in **bits**
  (`log₂`) over occupied positions, `0·log0 ≡ 0`, returned **raw** (un-normalised). A
  `log₂(n+1)`-normalised view is a P4/P6 presentation choice, not a P3 return value.
- **OQ-3.5 — Which arm pairings for TV/Hellinger.** **[proposal]** P3 ships arm-agnostic
  pairwise `tv_distance`/`hellinger`; the specific pairings required by AC-3.2 (hw vs ideal,
  hw vs binomial) plus noisy vs ideal for the sim sweep are *selected in P4*. The P3 gate
  validates the functions on ideal-vs-ideal (=0), ideal-vs-binomial, and range/symmetry.
- **OQ-3.6 — Shared analytic walk vs P2's local copy.** **[proposal]** Introduce the
  canonical `analytic_hadamard_walk` in `code/analytics.py` and **leave `walk_check.py`
  untouched** (avoid churn on a passing frozen gate); `metrics_check.py` asserts the shared
  reference equals `build_walk`+`Statevector` to `TOL`, so both copies stay pinned to the
  same physics. Absorbing `walk_check.py`'s copy is deferred as optional cleanup, not part
  of P3.

## 13. Post-Implementation (2026-08-10)

**Built.** Three new analysis modules + a SCHEMA.md section, no frozen artefact
touched:
- `code/analytics.py` — shared closed-form baselines `analytic_hadamard_walk`,
  `binomial_reference` (canonical owner, OQ-3.6).
- `code/metrics.py` — the four metrics (M1–M4) + the knee extractor, pure over
  int-keyed histograms; `to_int_hist` bridges the string-keyed `run.json` form.
- `code/metrics_check.py` — offline gate, exits 0 (aer-free, no network/QPU).
- `code/SCHEMA.md` — "P3 metrics" section documenting each definition + OQ rules as
  the P5 mirror contract.

**Verification.** `python code/metrics_check.py` → all 6 checks PASS, exit 0. Manual
sim-sweep (`--arm ideal`, seed 100): real `run.json` histograms fed through
`to_int_hist` + `variance_exponent` over n=8..18 give **a=1.976, r²=1.0** (ballistic),
`horn_contrast` positive across the sweep. `git diff` touches only the four listed
files.

**Deviation the developer must know (AC-3.4 entropy ordering).** Plan §2 AC-3.4's
heuristic said entropy is "larger for the diffusive hump than for the twin-horn
walk". That is **backwards** — the ballistic Hadamard walk spreads over
~[−n/√2, +n/√2] with a broad plateau, so its Shannon entropy is *higher* than the
binomial at every matched depth (e.g. n=16: 3.414 vs 3.047 bits). The gate asserts
the physically-correct ordering (`entropy(ideal) > entropy(binomial)`), which the
plan itself flagged as "heuristic sanity, not a hard physics law". No metric formula
changed — only the direction of the gate's sanity assertion.

**Follow-ups (not P3).** P4 loads the sweep, feeds these functions across the
depth×arm matrix, writes `summary.json` `per_depth[].metrics`, renders figures, and
applies the arm pairings for M2 (OQ-3.5). P5 vendors the JS mirror + parity gate
against these Python values. `crossover_depth`'s return annotation is `dict[str,
float | None]` per plan §6, but the `"rule"` value is a `str` — harmless (hints
unenforced), left verbatim to the plan contract; P4/P5 can widen if it matters.

---

*Plan drafted per epic §9 P3 and the P1/P2 frozen contracts. No automated tests (project
directive, epic §3.6) — verification is the offline gate (`metrics_check.py`) + a manual
sim-sweep inspection. Status stays Draft until the developer answers §12 and approves.*
