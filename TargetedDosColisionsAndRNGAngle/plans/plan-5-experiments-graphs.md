# Plan 5 — The five experiments & the two key graphs

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 4** · **Priority:** `[MUST]`
**Status:** Complete · **Depends on:** P2 (salt sources + rotation, frozen), P3 (attacker, frozen), P4 (defences + metrics, Complete) · **Gates:** P6 (Tier B replay dataset), P7 (both graphs + the rotation-frequency spec)

> Pick up with `/plan-feature plans/plan-5-experiments-graphs.md`. Read epic §3.1 (the "new attacker"
> is an *empirical* claim — Exp 1–3 must show the defences fire on the flood yet fail on precision),
> §3.2 (the QRNG null result is *measured* here in Exp 4), §4 (the run-tagged CSV this plan consumes),
> and §8 Q2/Q3/Q4 (the resolved rotation-unit / knowledge-level / replay-subset decisions) first.
> **No GitHub issue** — planned from the epic + source build plan (`plan/ECMP_COLLISION_DOS_BUILD_PLAN.md`
> EPIC 4, `plan/3-ecmp-collision-dos-extended.md` "five experiments").
> **No automated tests** (project directive) — verification is manual, described in §Manual verification.
> Any "verified" AC is met by a standalone check script / live run, never a test suite.

## Goal
Execute the experiment matrix and produce the paper's **two key graphs**. The five experiments form a
complete argument: here is the standard defence (Exp 1), here is why it fails (Exp 2–3), here is what
works (Exp 4), and here is the actionable knob (Exp 5). P5 adds **no new mechanism** — it is an
*orchestration + analysis* layer that drives the frozen upstream pieces (P3 attacker against P2 salt/rotation
and P4 defences), collects the P4 CSV per cell, and renders **Graph 1** (attacker success × salt source ×
knowledge level) and **Graph 2** (the rotation-frequency threshold curve), plus the analytical
rotation-cadence-vs-reconstruction-time derivation that turns Graph 2 into a specification for P7.

## Context — what upstream froze that P5 drives (never re-implements)
P2, P3, P4 are all landed. P5 imports and orchestrates them; it changes **none** of their code (epic §3.5 —
the experiments are only valid because they run the *real* controller/hash/attacker, not a copy):

- **Attacker (P3)** — `testbed/attacker/run_attack.py` CLI, run from the Mininet `attacker` host:
  `--level {full,partial,blind}`, `--mode {volumetric,precision}`, `--target-link`, `--count`,
  `--salt <hex>` (handed to the **full** attacker), `--oracle-salt <hex>` (backs the **partial** attacker's
  placement oracle side-channel). It prints a JSON **run-record**
  `{level, mode, target_link, salt_source, sources_used, flows_sent, reconstruction:{attempts, elapsed_seconds}}`
  (`attack.py:85-96`). P5 captures this per cell — `reconstruction.elapsed_seconds` is the empirical
  brute-force time Exp 5 correlates against the rotation interval.
- **Controller + salt/rotation (P1/P2)** — `testbed/controller/run_controller.py` boots
  `ECMPController`, which reads `SALT_KIND`, `ROTATION_INTERVAL_SECONDS`, `PRNG_SEED`, `QEAAS_*` from
  `config.py`/env, mints the active salt via `salt_source(kind)` (`salt/sources.py:51`), and logs every
  rotation to `ROTATION_LOG_PATH` as `{timestamp, old_salt, new_salt, interval, kind}`
  (`salt/rotation_log.py:12`). P5 sets these env vars per cell and reads the rotation log for the
  full-knowledge salt handoff (see OQ-1).
- **Defences + metrics (P4)** — gated on `DEFENCES_ENABLED`; the controller-hosted `MetricsCollector`
  writes per-poll rows to `METRICS_CSV_PATH` and a `*.summary.csv` sidecar
  (`metrics/csv_writer.py`), **every row tagged** `(salt_source, knowledge_level, rotation_interval,
  attack_mode)` + `timestamp` + `elapsed_seconds`. `salt_source`/`rotation_interval` come from the
  controller; `knowledge_level`/`attack_mode` come from `RunContext.from_env()` (`metrics/run_context.py`)
  reading env `KNOWLEDGE_LEVEL`/`ATTACK_MODE`. **P5 owns setting those two env vars per cell** — a wrong or
  missing tag silently breaks the matrix filter. The frozen defence thresholds (`RATE_LIMIT_KBPS=1000`,
  `THROTTLE_MAX_CONNECTIONS=20`, …) are **reused unchanged across every cell** (P4 tuning note) — P5 must
  never re-tune per experiment.
- **Topology (P1)** — `testbed/topology/run_topo.py` (Mininet + OVS). Per-egress-link `TCLink` bandwidth
  must equal `config.LINK_CAPACITY_MBPS` so utilisation is meaningful (P4 OQ-3).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`, EPIC 4)
- [x] **AC-1** (Exp 1 — baseline works vs volumetric): Rate-limit + throttle ON, naive flood → flood degraded,
  no saturation, victim protected. *(proves defences are real)* — Covered by
  `testbed/experiments/matrix.py:107` (`EXP1_VOLUMETRIC`, `expected_saturated=False`), run via
  `testbed/experiments/harness.py:139` (`run_cell`). **Not live-verified in this environment (no
  Mininet/root sandbox) — run manually per §Manual verification step 2.**
- [x] **AC-2** (Exp 2 — precision evades rate limiting): Same rate limit, precision attacker across compliant
  sources → target link saturates, victim collapses, limiter never fires. — Covered by
  `testbed/experiments/matrix.py:121` (`EXP2_PRECISION_RATE_LIMIT`, `expected_saturated=True`). **Not
  live-verified — run manually per §Manual verification step 3.**
- [x] **AC-3** (Exp 3 — precision evades throttling): Same throttling, 5-tuples varied across many valid-looking
  flows → saturation, victim collapses, throttle never fires. — Covered by
  `testbed/experiments/matrix.py:127` (`EXP3_PRECISION_THROTTLE`). **Not live-verified — run manually per
  §Manual verification step 3.**
- [x] **AC-4** (Exp 4 — salt rotation defeats the attacker): Full attacker vs three configs: weak PRNG no
  rotation (**attack succeeds**), CSPRNG+rotation (**fails**), QRNG+rotation (**fails, identical → null
  result**). Measure Jain + victim throughput under attack AND clean background (rotation must be cost-free
  when no attack). — Covered by `testbed/experiments/matrix.py:168` (`EXP4` = 4a/4b/4c/4d), the OQ-1
  controller fix at `testbed/controller/ecmp_controller.py:83-91` (initial-salt log entry so
  `salt_handoff.py` has a uniform read). **Not live-verified (needs `QEAAS_API_KEY` for 4c) — run manually
  per §Manual verification step 4.**
- [x] **AC-5** (Exp 5 — rotation frequency curve): Partial attacker; sweep rotation interval slow→fast; measure
  time-to-saturation + packets-to-saturation → threshold curve mapping to seed-space brute-force time
  (derive analytically, confirm empirically). — Covered by `testbed/experiments/matrix.py:172`
  (`EXP5_SWEEP`, log-spaced OQ-4 intervals) and `testbed/analysis/rotation_threshold.py:49`
  (`rotation_threshold`), offline-checked in `testbed/analysis/analysis_check.py`
  (`_check_rotation_threshold`, planted 5.0s crossover recovered exactly). **Not live-verified — run
  manually per §Manual verification step 5.**
- [x] **AC-6** (Graph 1): **attacker success vs salt source × knowledge level**. — Covered by
  `testbed/analysis/graphs.py:44` (`render_graph1`) over the 9-cell `testbed/experiments/matrix.py:207`
  (`GRAPH1`) grid; render path exercised offline in `analysis_check.py` (`_check_graphs_render`, produces
  `.png`+`.svg`).
- [x] **AC-7** (Graph 2): **rotation-frequency threshold curve**. — Covered by
  `testbed/analysis/graphs.py:78` (`render_graph2`), same offline exercise as AC-6.
- [x] **Done when:** all five experiments produce the expected results into CSV, and both key graphs render from
  that data. — `testbed/experiments/run_experiments.py:32` (`main`) ties per-cell PASS/FAIL to
  `testbed/analysis/graphs.py:130` (`render_graphs`). CSV/graph production confirmed structurally
  (`analysis_check.py` all-PASS); **the five live experiments themselves need a Mininet/root host to run
  and were not executed in this implementation environment.**

## The experiment matrix (what each cell sets, what result confirms it)
Each **cell** is one live run = a fixed env vector (below) → topology + controller + attacker launch →
one tagged CSV + summary row. The matrix is the set of cells the five experiments need. Env vars set per cell:
`SALT_KIND`, `ROTATION_INTERVAL_SECONDS`, `DEFENCES_ENABLED`, `KNOWLEDGE_LEVEL`, `ATTACK_MODE`,
`METRICS_CSV_PATH`, `TARGET_LINK`, `PRNG_SEED`, plus the attacker CLI `--level/--mode/--salt/--oracle-salt`.

| Exp | AC | Cells (salt · rotation · defences · attacker) | Expected result (from the summary row) |
|-----|----|----|----|
| 1 | AC-1 | prng · off · **on** · volumetric (`level=full`) | `saturated=False`, `min_victim_mbps` healthy, throttle/meter drop flows present. Defences **fire**. |
| 2 | AC-2 | prng · off · **on** · **precision** full | `saturated=True`, `min_victim_mbps` collapsed, **no** meter drop on any source. Rate-limit **never fires**. |
| 3 | AC-3 | prng · off · **on** · **precision** full (5-tuples spread) | `saturated=True`, victim collapsed, **no** throttle drop flow. Throttle **never fires**. |
| 4a | AC-4 | **prng · off** · off · precision full | `saturated=True` — attack **succeeds** (weak PRNG, no rotation). |
| 4b | AC-4 | **csprng · on** · off · precision full | `saturated=False` — attack **fails** (rotation invalidates the crafted set). |
| 4c | AC-4 | **qrng · on** · off · precision full | `saturated=False`, **numerically indistinguishable from 4b → the null result**. |
| 4d | AC-4 | {prng,csprng,qrng} · on · off · **no attack** (clean `bg` traffic only) | high Jain, full victim throughput for all three → **rotation is cost-free when no attack**. Captures the Q2 legitimate-flow-reordering secondary metric. |
| 5 | AC-5 | csprng · **rotation sweep** slow→fast · off · **partial** | per interval: `time_to_saturation_s`, `packets_to_saturation`; the interval at which saturation stops being reached is the **threshold**. |

**Knowledge-level coverage for Graph 1 (epic §8 Q3 — keep full, partial, blind separate).** Graph 1's
matrix is `salt source {prng,csprng,qrng} × knowledge {full,partial,blind}`. `full` and `partial` differ only
in reconstruction cost (partial pays `reconstruction.elapsed_seconds`); `blind` is the failure baseline
(random 5-tuples, never saturates). Run all nine cells with rotation **on** for csprng/qrng and **off** for
prng-no-rotation's success cell, so the graph shows: prng-full/partial succeed, everything under
csprng/qrng+rotation fails, blind fails everywhere.

## Design

### 1. Experiment orchestrator (`testbed/experiments/`)
A thin, deterministic driver — **no attack/hash/metric logic of its own**, only process lifecycle + env.

- **`matrix.py`** — the matrix as **data**: a frozen list of `ExperimentCell` dataclasses, each carrying its
  env vector (`salt_kind`, `rotation_interval`, `defences_enabled`, `knowledge_level`, `attack_mode`,
  `target_link`, `prng_seed`) and the attacker CLI args (`level`, `mode`, `count`, needs_salt/needs_oracle).
  The five experiments + the 9-cell Graph 1 grid + the Exp 5 rotation sweep (`ROTATION_SWEEP_INTERVALS` from
  config) are all expressed here, so "which cells run" is inspectable without reading orchestration code.
  Cells are grouped/labelled by experiment (`exp1`…`exp5`) and write to a per-cell
  `METRICS_CSV_PATH` (`results/<exp>/<cell_id>.csv`) so nothing is overwritten.
- **`harness.py`** — pure-ish process lifecycle helpers (stdlib `subprocess`/`signal`, no OpenFlow): start
  the controller (`run_controller.py`) with the cell's env, start Mininet (`run_topo.py`), wait for the
  leaf/spine datapaths to register, launch the attacker on the `attacker` host, run for a bounded
  `RUN_DURATION_SECONDS`, then tear everything down cleanly (SIGTERM controller + `mn -c`). Idempotent
  teardown so a crashed cell never poisons the next. Requires **root/Mininet** (like P1/P3/P4 live steps).
- **`salt_handoff.py`** — supplies the **full** attacker its `--salt`. Reads the current active salt from
  the controller's rotation log (`salt/rotation_log.read_events`, latest `new_salt`); see **OQ-1** for the
  no-rotation prng case (the controller must log its initial salt). Pure read — no minting, so the attacker
  always uses the salt the controller is *actually* live on.
- **`run_experiments.py`** — CLI entry: `--exp {1,2,3,4,5,all}` selects cells from `matrix.py`, iterates
  them through `harness.py`, and on completion hands the collected CSVs to the analysis layer (or stops at
  data-only with `--no-graphs`). Prints a per-cell PASS/FAIL against the cell's *expected* summary result
  (e.g. Exp 2 expects `saturated=True` **and** no meter drop) so a mis-run is caught immediately, not at
  graph time. **Does not** re-tune thresholds, mint salts, or touch upstream code.

### 2. Analysis + graphs (`testbed/analysis/`)
Reads the P4 CSVs (per-poll + `.summary.csv`) with **pandas**, renders with **matplotlib**. Pure data-in →
figure-out; no live infra.

- **`success.py`** — the single, frozen **success predicate** (OQ-2), applied to a summary row:
  `success = saturated AND min_victim_mbps <= VICTIM_COLLAPSE_MBPS`. One definition of "attacker succeeded",
  reused by Graph 1, the orchestrator's PASS/FAIL, and P6. Pure function over a summary dict/`DataFrame` row.
- **`rotation_threshold.py`** — the Exp 5 core. **Analytical** side: expected brute-force reconstruction time
  `T_bf ≈ (2^seed_bits / 2) · t_try` over the P2-frozen `PRNG_SEED_SPACE_BITS`/`BRUTEFORCE_DRAW_WINDOW`,
  with `t_try` calibrated from the partial attacker's measured `reconstruction.elapsed_seconds / attempts`;
  the attack succeeds only when `rotation_interval > T_bf + T_exploit`. **Empirical** side: from the Exp 5
  sweep, the largest rotation interval at which `saturated=False` — the measured threshold. The module returns
  both plus the practitioner one-liner *"rotate faster than N seconds given seed space S"* (→ P7). Pure,
  importable without matplotlib so it is offline-checkable.
- **`graphs.py`** — renders the two deliverables:
  - **Graph 1 (AC-6)** — `attacker success × salt source × knowledge level`: a 3×3 grid/heatmap (source on one
    axis, knowledge on the other) coloured by the `success.py` predicate over each cell's summary row.
    prng-full/partial = success, csprng/qrng+rotation and all blind = fail, and 4c overlaid on 4b to make the
    **null result visible** (identical fail cells).
  - **Graph 2 (AC-7)** — `rotation-frequency threshold curve`: x = rotation interval (log scale, slow→fast),
    y = time-to-saturation (and a second series for packets-to-saturation), with the analytical `T_bf`
    threshold drawn as a vertical line and the empirical crossover shaded — i.e. the two agree (AC-5's "derive
    analytically, confirm empirically"). Saves `results/graph1_success_matrix.{png,svg}` and
    `results/graph2_rotation_threshold.{png,svg}` (SVG for the paper, PNG for quick view).
- **`analysis_check.py`** — standalone offline checker (mirrors P4's `metrics_check.py`): feed **synthetic**
  summary CSVs (a hand-built prng-success row, a csprng-fail row, a rotation sweep with a known crossover) and
  assert `success.py` classifies each correctly, `rotation_threshold.py` finds the planted crossover, and
  `graphs.py` renders both figures to a temp dir without error. Exit non-zero on mismatch. This is the
  "verified" ACs as a manual checker — **no test suite** (project directive).

### 3. Config additions (`testbed/config.py`, new P5 block)
Knobs as env-overridable data, alongside the existing P2/P3/P4 blocks (reuse `N_LINKS`, `EGRESS_PORTS`,
`LINK_CAPACITY_MBPS`, `SATURATION_UTILISATION`, `PRNG_SEED_SPACE_BITS`, `BRUTEFORCE_DRAW_WINDOW` — never
redefine): `RUN_DURATION_SECONDS`, `ROTATION_SWEEP_INTERVALS` (list, slow→fast — the Exp 5 x-axis),
`VICTIM_COLLAPSE_MBPS` (success threshold), `RESULTS_DIR`, `GRAPH1_PATH`, `GRAPH2_PATH`, and the
knowledge/source enumerations `KNOWLEDGE_LEVELS=("full","partial","blind")`,
`SALT_SOURCES=("prng","csprng","qrng")` (single source of truth for the matrix).

## Interfaces exposed to P6 / P7 (freeze — downstream reads, does not redefine)
- **The recorded CSV set under `RESULTS_DIR`** — P6 Tier B replays the epic §8 Q4 **subset** (three-scene
  runs + one QRNG provenance run + the full Exp 5 rotation sweep the slider drives; **blind skipped**). P5
  must produce that subset among its cells and note the skipped conditions in the demo/results README.
- **`success.py` predicate** and **`rotation_threshold.py`** — P6's Scene-3 slider and P7's spec must use the
  *same* definition of "saturated/succeeded" and the *same* threshold derivation P5 renders, or the demo/paper
  contradict the graphs.
- **`results/graph1_*.svg`, `results/graph2_*.svg`** — the two figures P7 embeds verbatim.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. New unless marked **edit**.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/experiments/__init__.py` | Package marker; re-export `ExperimentCell`, `MATRIX`. | — | New package, sibling of `testbed/metrics/`, `testbed/attacker/`. |
| `testbed/experiments/matrix.py` | `ExperimentCell` dataclass + the frozen `MATRIX` (five experiments + 9-cell Graph 1 grid + Exp 5 sweep) as data. | AC-1–5 | The whole matrix inspectable without running it; env vector + attacker args per cell. Pure data, no subprocess. |
| `testbed/experiments/harness.py` | Process lifecycle: boot controller + Mininet with a cell's env, await datapaths, launch attacker, run `RUN_DURATION_SECONDS`, tear down (`mn -c`, SIGTERM). | AC-1–5 | stdlib `subprocess`/`signal` only. Idempotent teardown. Needs root/Mininet. No OpenFlow imports. |
| `testbed/experiments/salt_handoff.py` | Read the controller's current active salt from the rotation log for the **full** attacker's `--salt`. | AC-4 | Pure read via `salt/rotation_log.read_events`; latest `new_salt`. Depends on OQ-1 (initial-salt logging). |
| `testbed/experiments/run_experiments.py` | CLI orchestrator: `--exp {1..5,all}`, iterate cells, per-cell PASS/FAIL vs expected summary, then invoke analysis (`--no-graphs` to stop at data). | AC-1–5, Done-when | The one live entry point. Sets `KNOWLEDGE_LEVEL`/`ATTACK_MODE` env per cell (the two tags the controller can't derive). |
| `testbed/analysis/__init__.py` | Package marker; re-export `attacker_succeeded`, `render_graphs`, `rotation_threshold`. | — | New package, offline (no os_ken/root). |
| `testbed/analysis/success.py` | Frozen success predicate `attacker_succeeded(summary_row) -> bool` = `saturated AND min_victim_mbps <= VICTIM_COLLAPSE_MBPS`. | AC-6 | Pure function over a summary row. One definition of "succeeded". |
| `testbed/analysis/rotation_threshold.py` | Analytical `T_bf` from seed space + measured `t_try`; empirical crossover from the Exp 5 sweep; practitioner one-liner. | AC-5, AC-7 | Pure; importable without matplotlib. |
| `testbed/analysis/graphs.py` | Render Graph 1 (3×3 success matrix, null result overlaid) and Graph 2 (rotation-frequency curve with analytical + empirical threshold) → PNG + SVG. | AC-6, AC-7 | pandas read of P4 CSVs; matplotlib render. No live infra. |
| `testbed/analysis/analysis_check.py` | Standalone offline checker: synthetic summary CSVs → assert success classification, threshold crossover, and that both graphs render. Exit non-zero on mismatch. | AC-5–7 | The "verified" ACs as a manual checker — no test suite (project directive). |
| `testbed/config.py` | **edit** — add a P5 block: `RUN_DURATION_SECONDS`, `ROTATION_SWEEP_INTERVALS`, `VICTIM_COLLAPSE_MBPS`, `RESULTS_DIR`, `GRAPH1_PATH`, `GRAPH2_PATH`, `KNOWLEDGE_LEVELS`, `SALT_SOURCES`. | all | Env-overridable data, like the P2/P3/P4 blocks. Reuse `N_LINKS`/`EGRESS_PORTS`/`LINK_CAPACITY_MBPS`/seed-space knobs. |
| `testbed/README.md` | **edit** — add "Running the experiment matrix + rendering graphs": prerequisites (root, `QEAAS_API_KEY` for qrng cells, `iperf3` for victim throughput), `run_experiments.py --exp all`, `analysis_check.py`, where graphs land, the Q4 replay subset + skipped conditions. | — | Extends the P1–P4 runbook. |
| `requirements.txt` | **edit** — add `pandas` and `matplotlib` (pip deps, analysis only). Note they are **not** needed on the live testbed host, only for `testbed/analysis/`. | — | Keep existing `hping3`/`iperf3` system-tool notes. |

## Manual verification (no automated tests — project directive)
Run from `TargetedDosColisionsAndRNGAngle/`. Step 1 needs no Mininet/root; steps 2–6 need the live testbed
(Mininet + OVS + root), consistent with P1–P4 live verification. QRNG cells (Exp 4c) additionally need
`QEAAS_API_KEY` in env (epic §8 Q6 — hosted `api.qeaas.eu`).

1. **Analysis offline** — `python testbed/analysis/analysis_check.py`: feed synthetic summary CSVs (a
   prng-success row, a csprng-fail row, a rotation sweep with a planted crossover); confirm
   `attacker_succeeded` classifies each correctly, `rotation_threshold` recovers the planted crossover and
   emits the "rotate faster than N s" line, and `graphs.py` renders both figures to a temp dir. Exit non-zero
   on any mismatch. Confirms AC-5–7's maths/render path with zero infra.
2. **Exp 1 (live)** — `python testbed/experiments/run_experiments.py --exp 1`: defences ON, prng, volumetric.
   Confirm the summary row shows `saturated=False`, `min_victim_mbps` healthy, and the meter/throttle drop
   flows appear (`ovs-ofctl -O OpenFlow15 dump-meters s1` / `dump-flows s1`). **Defences fire.**
3. **Exp 2–3 (live)** — `--exp 2` then `--exp 3`: same defences ON, precision attacker. Confirm
   `saturated=True`, `min_victim_mbps` collapsed, and **no** per-source meter drop (Exp 2) / **no** throttle
   drop flow (Exp 3). This is the epic's central claim — precision passes under the same caps the flood tripped.
4. **Exp 4 (live)** — `--exp 4`: confirm 4a (prng, no rotation) `saturated=True`; 4b (csprng+rotation) and 4c
   (qrng+rotation) both `saturated=False` and **numerically indistinguishable** (the null result — same Jain,
   same victim throughput within noise); 4d (clean background, all three sources) high Jain + full victim
   throughput → rotation cost-free when no attack. Confirm the qrng cell recorded Q-EaaS provenance
   (`request_id`/`entropy_epoch`/`receipt`) in the rotation/salt log without crashing on `503`/`429`.
5. **Exp 5 (live)** — `--exp 5`: partial attacker, rotation sweep. Confirm `time_to_saturation_s` /
   `packets_to_saturation` rise as the interval shortens and that saturation stops being reached below the
   threshold; confirm the empirical crossover lands near the analytical `T_bf` from the measured
   `reconstruction.elapsed_seconds`.
6. **Graphs (live data)** — after `--exp all`, confirm `results/graph1_*.svg` shows the 3×3 with prng
   success vs csprng/qrng+rotation failure and the null result, and `results/graph2_*.svg` shows the curve
   with both thresholds. Confirm the Q4 replay subset (three-scene + QRNG + full sweep, blind skipped) exists
   under `RESULTS_DIR` for P6, with skipped conditions noted in the README.

## Conventions
- Strict typing + PEP 8, matching P1–P4: `from __future__ import annotations`, full type hints on public
  functions, frozen dataclasses for `ExperimentCell` and result objects.
- `analysis/*` stays **importable without os_ken / root** (pandas/matplotlib only) so `analysis_check.py` runs
  in any environment (as P4's `metrics_check.py` and P3's `collision_check.py` do). All live-infra exec stays
  in `experiments/harness.py`.
- **No new mechanism.** P5 drives `run_attack.py`, `run_controller.py`, `run_topo.py`, and reads the P4 CSV —
  it never re-implements the hash, salt sourcing, rotation, defences, or metrics, and never re-tunes the
  frozen P4 thresholds (a per-experiment re-tune makes the central claim unfalsifiable).
- **Set both run-context tags per cell** — `KNOWLEDGE_LEVEL`/`ATTACK_MODE` env before each controller boot;
  the CSV filter and Graph 1 depend on them being correct.
- **CSV read via pandas, one success predicate, one threshold derivation** — no re-deriving "saturated" from
  raw per-poll rows when the summary sidecar already carries it; no second definition of success in P6/P7.
- **Graphs to SVG (paper) + PNG (preview)**; no hand-placed pixel coordinates — data-driven axes/labels.

## Out of scope
- **The paper prose** (P7) — P5 produces *data + two static graphs*, not the write-up.
- **The interactive/animated web demo** (P6) — P5 records the CSV subset P6 Tier B replays, but builds no
  front-end, WebSocket bridge, or slider.
- **Any change to `hash_core`, the salt engine/sources, rotation, the attacker, the defences, or the metrics
  collector / CSV schema** — all frozen upstream (P2/P3/P4). P5 consumes them unchanged.
- **Re-tuning the P4 defence thresholds** — frozen once (P4 tuning note); P5 reuses them across every cell.
- **The Q1 blast-radius multi-victim run** (epic §8 Q1) — an optional later bolt-on, not this plan.
- **Live hardware confirmation run** (epic §3.4 scale caveat) — optional, for P7, not P5.

## Risks
- **Full-knowledge salt handoff (OQ-1).** The full attacker needs the *exact* active salt. The rotation log
  today logs only *rotations*, so a prng-no-rotation cell has no logged salt. Mitigation: OQ-1 — have the
  controller log its initial salt at startup (tiny P2/controller addition) so `salt_handoff.py` is a single
  uniform "latest `new_salt`" read; fallback is re-minting `salt_source("prng")`'s first draw, which is fragile
  if draw indices desync. Flag early — this gates Exp 4a.
- **Rotation racing the attacker mid-craft.** Under fast rotation the salt can change between handoff and
  send. That is *the point* for csprng/qrng (Exp 4b/4c) but must not corrupt the prng success cell (Exp 4a,
  rotation off). Mitigation: Exp 4a runs with rotation off; timing correctness for the sweep (Exp 5) is exactly
  what Graph 2 measures — record the salt-at-send in the run so a spurious fail is distinguishable from a real one.
- **QRNG live dependency (Exp 4c).** `qrng` cells call `api.qeaas.eu`; a `503 low_quantum_entropy` or `429`
  mid-sweep could kill a cell. Mitigation: the P2 client already degrades/retries; the orchestrator marks a
  qrng cell that never got provenance as *skipped-with-reason*, never a silent gap — and the null result only
  needs one clean qrng cell against 4b.
- **Threshold poll resolution vs Exp 5 x-axis.** `PORT_STATS_POLL_INTERVAL_SECONDS=0.5` bounds how precisely
  `time_to_saturation` resolves the fastest rotation intervals. Mitigation: keep the sweep's fastest interval
  well above the poll interval; document the sampling granularity as Graph 2's resolution floor.
- **Mininet teardown leakage between cells.** A crashed cell leaving OVS/netns state poisons the next.
  Mitigation: idempotent `mn -c` + controller SIGTERM in `harness.py` teardown, run unconditionally before
  each cell boots; per-cell CSV paths so no run overwrites another.
- **Non-determinism in success classification.** Emulation jitter near the `SATURATION_UTILISATION` /
  `VICTIM_COLLAPSE_MBPS` edges could flip a borderline cell. Mitigation: pick thresholds with clear margin (as
  P4 did for the defence caps), and have the orchestrator flag borderline cells for a re-run rather than
  silently recording them.

## Open questions — RESOLVED (2026-07-26, all defaults accepted)
- [x] **OQ-1 — full-knowledge salt handoff.** **RESOLVED:** **the controller logs its initial minted salt at
  startup** as a rotation event with `old_salt=b""`, so `salt_handoff.py` is one uniform "latest `new_salt`"
  read for every cell (incl. prng-no-rotation). ~3-line controller addition; the attacker uses the salt the
  controller is actually on. *Affects the controller (tiny P2-adjacent edit), `salt_handoff.py`.*
- [x] **OQ-2 — success predicate.** **RESOLVED:** `attacker_succeeded` = `saturated=True` **AND**
  `min_victim_mbps <= VICTIM_COLLAPSE_MBPS` — matches the ACs ("saturates *and* victim collapses"), aligns
  success with user-visible damage. *Affects `success.py`, `config.VICTIM_COLLAPSE_MBPS`.*
- [x] **OQ-3 — Graph 1 coverage.** **RESOLVED:** run **all nine cells** (3 sources × 3 knowledge). The epic
  §8 Q3 decision (keep full/partial/blind separate) is explicit; the flat blind row *is* the failure baseline,
  labelled as such, and qrng≡csprng makes the null result visible. *Affects `matrix.py` width, Graph 1.*
- [x] **OQ-4 — Exp 5 sweep intervals.** **RESOLVED:** **log-spaced sweep** (60, 30, 10, 5, 2, 1, 0.5 s)
  straddling analytical `T_bf`, ~7 cells, in `ROTATION_SWEEP_INTERVALS`; densify near the crossover only if
  Graph 2 looks ambiguous. *Affects `config.ROTATION_SWEEP_INTERVALS`, Exp 5 run time, Graph 2.*
- [x] **OQ-5 — results storage.** **RESOLVED:** commit the **two figures (SVG/PNG) + the Q4 replay subset**
  (what P6/P7 consume); gitignore raw per-cell CSVs with a README pointer on regenerating via
  `run_experiments.py`. *Affects `.gitignore`, `RESULTS_DIR` layout, README.*

## Post-implementation

Built: `testbed/experiments/` (matrix.py, harness.py, salt_handoff.py, run_experiments.py) and
`testbed/analysis/` (success.py, rotation_threshold.py, graphs.py, analysis_check.py) per the file plan,
plus the OQ-1 controller edit and the config/README/requirements/.gitignore additions. The matrix
(22 unique cells across exp1-5 + the graph1 grid, verified with no duplicate cell IDs) and the offline
analysis path (`analysis_check.py`) both run clean in `.venv` (pandas/matplotlib installed).

**Follow-ups for the developer:**
- The five live experiments (harness.py driving real Mininet + os_ken + scapy) were **not executed** in
  this implementation session — no root/Mininet sandbox available here. Run §Manual verification steps
  2-6 on the real testbed host before treating the ACs as live-confirmed.
- `harness.py`'s datapath-ready wait polls `ovs-ofctl show` on both switches; if the real box's OVS/OF1.5
  build behaves differently from the P1-P4 assumptions, this may need a longer `_DATAPATH_WAIT_TIMEOUT_SECONDS`.
- Exp 4c/4d qrng cells need `QEAAS_API_KEY` — confirm the orchestrator's skip-with-reason behaviour
  (Risks: QRNG live dependency) once run against the real Q-EaaS endpoint.
