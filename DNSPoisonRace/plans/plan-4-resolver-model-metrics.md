# Plan 4 — Resolver/victim model & instrumentation

**Epic:** [DNS Poison Race](../epic-dns-poison-race.md) · **Source P4** · **Priority:** `[MUST]`
**Status:** Approved (2026-07-30, all open questions resolved, developer: "accept all defaults") ·
**Depends on:** P3 (off-path attacker & poison race, Complete) ·
**Gates:** P5 (runs the sweeps, renders figures, exports replay JSON), P6 (reads the CSV / provenance
for the web spectacle)

> Pick up with `/plan-feature plans/plan-4-resolver-model-metrics.md`. Read epic §3.2 (the honest null
> result — QRNG differentiator is provenance, never a lower poisoning rate), §3.5 (one race core — this
> plan calls `run_poison_race` verbatim, never re-implements the draw/race), §3.6 (offline gates + no
> automated test suite), §4 (shared artefacts — the run-tagged CSV + `.record.json` this plan owns), §5
> (the resolver race state machine this plan gives a cache/TTL frame to), §9 P4 brief first.
> **No GitHub issue** — planned from the epic + source doc (`plans/viz-3-dns-poison-race.md`), not from
> a tracker. ACs below are quoted verbatim from epic §9 P4. **No automated tests** (project directive) —
> verification is the offline `metrics_check.py` gate + manual CLI runs, in §Manual verification.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/plans/plan-4-defences-instrumentation.md`
> (`testbed/metrics/` — `MetricsCollector`, `fairness.py`, `csv_writer.py`, `run_context.py`,
> `metrics_check.py`). This plan mirrors that package's shape: pure, OpenFlow/network-free metrics
> maths in stdlib-only modules, a run-tagged CSV + summary sidecar, and a standalone offline check
> script. **The deliberate divergence from the twin:** the twin's collector polls a live OpenFlow
> controller for port-stats deltas; this study has no live network at all (epic §3.4) — its per-cell
> "sample" is one `run_poison_race(...)` call repeated `TRIALS_PER_CELL` times on the virtual clock, and
> the "poll" is just the trial loop. There is no controller, no `iperf`, no OVS here.

## Goal
Give the epic's discrete-event race a **resolver-shaped frame** (a named cache/TTL wrapper around the
P3 outcome, epic §5) and the **five-metric collector** that turns many `PoisonRaceResult`s at one
`(source, effective-bits, send-rate, parallel-queries)` cell into the epic's headline numbers, written
to a **run-tagged CSV** plus a per-run `.record.json` carrying the cell's QRNG provenance receipt (M5).
P4 delivers:

1. the **resolver cache wrapper** (`resolver/cache.py`) — a thin, source-agnostic mapping from a
   `PoisonRaceResult.outcome` to a named cache state (`POISONED` / `RESOLVED_LEGIT` / `WINDOW_CLOSED`,
   epic §5) plus the TTL bookkeeping the diagram shows after `RESOLVED-LEGIT`. It gives P5/P6 a
   resolver-flavoured vocabulary to render and reason about — it does **not** decide any outcome; the
   race decision is P3's alone;
2. the **five-metric collector** (`resolver/metrics.py`) — `collect_cell(...)` runs `run_poison_race`
   `TRIALS_PER_CELL` times at one cell and aggregates M1 (poison probability), M2 (mean forged packets
   / mean time-to-poison among poisoned trials), M3 (amplification factor vs a `parallel_queries=1`
   baseline cell), M4 (the cell's `k` is carried through for P5's SAD-DNS sweep to plot against), and
   M5 (the first QRNG-arm draw's provenance, when `kind="qrng"`);
3. the **run-tagged CSV writer + `.record.json` writer** (`resolver/csv_writer.py`) — one CSV row per
   cell (frozen schema, §CSV schema below) and, for QRNG cells, a `.record.json` sidecar embedding the
   real Q-EaaS receipt;
4. the **CLI runner** (`resolver/run_metrics.py`) and the **offline gate** (`resolver/metrics_check.py`).

P4 does **not** run the epic's full bits×source×send-rate matrix or render the two headline figures —
that is P5, which calls `collect_cell` once per matrix cell and reads/concatenates this CSV.

## Context — what P1/P2/P3 froze that P4 consumes (never re-implements)
P1, P2, P3 are **Complete**. P4 aggregates their output and imports the rest verbatim (epic §3.5 — a
re-implemented race here would silently invalidate M1–M4):

- `testbed/attacker/attack.py` — `run_poison_race(kind, *, txid_bits, port_bits, k, send_rate_pps, rtt,
  retransmit, parallel_queries, seed) -> PoisonRaceResult`. **The single entry point P4 calls per
  trial.** `PoisonRaceResult` fields (frozen for P4, epic §9 P3): `kind, outcome, t_outcome,
  forged_packets, effective_bits, parallel_queries, send_rate_pps, k, poisoned_window, provenance`.
- `testbed/types.py` — `DrawProvenance(kind, detail)`. P4 reads `result.provenance` verbatim for M5; it
  does not reshape it.
- `testbed/draw/sources.py` — `DrawKind = "fixed"|"prng"|"csprng"|"qrng"`. P4's collector loops over
  these four kinds; it does not mint draws itself (that happens inside `run_poison_race`).
- `testbed/config.py` — `TXID_BITS`, `PORT_BITS`, `RTT_SECONDS`, `RETRANSMIT_SECONDS`,
  `PARALLEL_QUERIES`, `SEND_RATE_PPS` (the P4/P5 send-rate axis, already a comma-separated list),
  `SAD_DNS_LEAK_BITS`, `TRIALS_PER_CELL` (already declared, P1, for exactly this purpose), `PRNG_SEED`.
  P4 adds only a small `# --- P4 ---` block (below); it does not change existing constants.
- **Nothing else is touched.** `sim/race.py`, `sim/event_queue.py`, `draw/sad_dns.py`,
  `attacker/guessing.py`, `attacker/flood.py`, `attacker/portable_prng.py` stay exactly as P3 left them.

## The resolver frame (why a cache wrapper, given P3 already decided the outcome)
The epic §5 diagram names four states — `WINDOW OPEN`, `POISONED`, `RESOLVED-LEGIT`, `WINDOW CLOSED` —
and a TTL edge out of `RESOLVED-LEGIT`. P3's `PoisonRaceResult.outcome` already **is** the terminal
state (`"poisoned"|"resolved_legit"|"window_closed"`); P4 does not re-derive it. What P4 adds is the
**resolver-shaped vocabulary** downstream plans need:

- a `CacheEntry` recording what actually ends up cached — the attacker's forged answer data if
  `poisoned`, the real authoritative answer if `resolved_legit`, nothing if `window_closed` — plus a
  `ttl_expires_at` computed from `t_outcome + config.CACHE_TTL_SECONDS` for `resolved_legit`/`poisoned`
  entries (the diagram's `RESOLVED-LEGIT --cache TTL--> WINDOW CLOSED` edge, generalised to the
  poisoned case since a poisoned answer is cached too — that is the entire point of cache poisoning);
- `resolve_cache(result: PoisonRaceResult) -> CacheEntry` — a pure, one-line-per-branch mapping, no new
  decision logic, so P5/P6 can render "what's in the cache and until when" without re-deriving it from
  `outcome` + `t_outcome` themselves in three different places.

This is deliberately thin. The interesting state machine (window race, retransmit, acceptance) is P3's;
P4's cache wrapper exists so downstream plans have one canonical place that answers "what does the
victim's resolver actually believe now."

## Acceptance criteria (verbatim from epic §9 P4)
- **AC-4.1** M1 poisoning success probability per (source, effective-bits) cell.
  **Delivered by:** `resolver/metrics.py` `collect_cell(...)` — runs `run_poison_race` `trials` times,
  `poison_rate = poisoned_count / trials`. Verified offline: `metrics_check.py` feeds a synthetic
  all-poisoned and all-legit trial set and asserts `poison_rate == 1.0` / `0.0`; a mixed set asserts the
  exact fraction.
- **AC-4.2** M2 expected forgery packets and time-to-poison at fixed entropy.
  **Delivered by:** `collect_cell(...)` — `mean_forged_packets` over **all** trials (every trial spends
  packets whether or not it poisons) and `mean_time_to_poison` over **poisoned** trials only (undefined,
  written `None`/empty, when zero trials poisoned). Verified offline: `metrics_check.py` checks both
  means against hand-computed values and the empty-poisoned-set edge case.
- **AC-4.3** M3 birthday amplification factor vs parallel-query count.
  **Delivered by:** `resolver/metrics.py` `amplification_factor(poison_rate_q, poison_rate_baseline) ->
  float | None` (`poison_rate_q / poison_rate_baseline`, `None` when the baseline rate is `0.0` —
  division-by-zero guard, not a crash). `run_metrics.py --parallel 1,8` runs the `parallel_queries=1`
  cell first as the baseline, then each further value, and writes `amplification_factor` into that row.
  Verified offline: `metrics_check.py` checks the ratio on known rates and the `None` guard at a `0.0`
  baseline.
- **AC-4.4** M4 success vs bits-of-port-leaked (SAD-DNS sensitivity).
  **Delivered by:** every CSV row carries the cell's `k` (SAD-DNS leaked port bits) and `effective_bits`
  alongside `poison_rate` — P4 does not sweep `k` itself (that is P5's SAD-DNS collapse-figure matrix,
  epic §9 P5 AC-5.2), it guarantees the column exists and is correctly populated so P5's sweep is a
  concatenation of P4 cells, not a reshape. Verified offline: `metrics_check.py` asserts `k` and
  `effective_bits` pass through `collect_cell` unchanged into the returned `CellRecord`.
- **AC-4.5** M5 per-cell provenance record persisted to `.record.json`.
  **Delivered by:** `resolver/csv_writer.py` `write_record_json(cell_record, path)` — writes
  `{cell fields..., provenance: {kind, detail}}` verbatim from the **first** trial's
  `PoisonRaceResult.provenance` in the cell (documented: provenance is per-draw, not per-trial-aggregate;
  the first trial's receipt stands in for the cell for `kind="qrng"`, where every draw in a run shares
  one Q-EaaS response envelope's `entropy_epoch`/`request_id` shape). Verified offline:
  `metrics_check.py` asserts the written JSON's `provenance` matches the input `CellRecord.provenance`
  field-for-field.
- **Done when:** `python3 testbed/resolver/metrics_check.py` runs all checks with no network and no
  root and prints a final `PASS`; `python3 testbed/resolver/run_metrics.py --kind csprng --eff-bits 16
  --trials 2000` writes one CSV row plus (for `--kind qrng`) a `.record.json` with a real receipt; and
  `--parallel 1,8` at a fixed cell shows `amplification_factor > 1` in the `parallel_queries=8` row.

## Design

### `resolver/cache.py` — the cache wrapper (epic §5)
```python
@dataclass(frozen=True)
class CacheEntry:
    state: Literal["poisoned", "resolved_legit", "window_closed"]
    ttl_expires_at: float | None  # None for window_closed (nothing cached)

def resolve_cache(result: PoisonRaceResult, *, ttl_seconds: float = config.CACHE_TTL_SECONDS) -> CacheEntry:
    if result.outcome == "window_closed":
        return CacheEntry(state="window_closed", ttl_expires_at=None)
    return CacheEntry(state=result.outcome, ttl_expires_at=result.t_outcome + ttl_seconds)
```
Pure, three branches, no OpenFlow/network analogue here — stdlib only, no imports beyond `types`-level
dataclasses and `config`.

### `resolver/metrics.py` — the five-metric collector
- `@dataclass(frozen=True) CellRecord` — one row's worth of data:
  `kind, effective_bits, k, send_rate_pps, parallel_queries, trials, poison_rate,
  mean_forged_packets, mean_time_to_poison, amplification_factor, provenance`.
- `collect_cell(kind, *, txid_bits=config.TXID_BITS, port_bits=config.PORT_BITS, k, send_rate_pps, parallel_queries, trials=config.TRIALS_PER_CELL, seed) -> CellRecord`
  — loop `trials` times calling `run_poison_race(kind, txid_bits=..., port_bits=..., k=..., send_rate_pps=..., parallel_queries=..., seed=seed + trial_index)`
  (distinct seed per trial — reproducible as a whole cell, never repeating one race `trials` times);
  aggregate `poison_rate`, `mean_forged_packets`, `mean_time_to_poison` (over poisoned subset), keep the
  first trial's `provenance`. `amplification_factor` is left `None` here — filled in by the caller (CLI)
  once a baseline cell's `poison_rate` is known, via:
- `amplification_factor(poison_rate_q: float, poison_rate_baseline: float) -> float | None` — pure,
  `None` guard on a zero baseline (AC-4.3).

### `resolver/csv_writer.py`
- `write_row(record: CellRecord, path: str, *, run_tag: str) -> None` — appends one row (creates file +
  header on first write) to the frozen schema below via stdlib `csv`.
- `write_record_json(record: CellRecord, path: str) -> None` — one JSON object per cell:
  `{run_tag, kind, effective_bits, k, send_rate_pps, parallel_queries, trials, poison_rate,
  mean_forged_packets, mean_time_to_poison, amplification_factor, provenance: {kind, detail}}`.
  Written for every cell (not only `qrng`) so P5/P6 have one consistent per-cell artefact; for
  non-`qrng` kinds `provenance.detail` simply carries the PRNG seed+index / CSPRNG source note /
  fixed-port note P2 already puts there (epic §4 `DrawProvenance` row) — never empty.

### CSV schema (frozen — P5 and P6 read it)
One row per cell in `RESULTS_CSV_PATH`:
`run_tag, timestamp, kind, effective_bits, k, send_rate_pps, parallel_queries, trials, poison_rate,
mean_forged_packets, mean_time_to_poison, amplification_factor`.
(Provenance is **not** a CSV column — it lives in the per-cell `.record.json` sidecar, since
`DrawProvenance.detail` is a nested dict that does not flatten cleanly into one CSV cell; epic §4 lists
the CSV and the `.record.json` as separate artefacts for exactly this reason.)

### `resolver/run_metrics.py` — CLI
`argparse`: `--kind {fixed,prng,csprng,qrng}` (repeatable or comma-separated, for a quick multi-kind
run), `--eff-bits` (solves for `-k` at the current `--port-bits`, mirroring `run_attack.py`'s existing
flag), `--port-bits`, `--send-rate` (default `config.ATTACKER_SEND_RATE_PPS`), `--parallel` (comma-
separated list, e.g. `1,8` — first value is the amplification baseline), `--trials`, `--seed`,
`--out` (default `config.RESULTS_CSV_PATH`), `--record-dir` (default `config.RESULTS_RECORD_DIR`).
For each `(kind, parallel)` pair: `collect_cell(...)`, compute `amplification_factor` against the first
`--parallel` value's rate at the same `(kind, eff_bits, k, send_rate)`, `write_row`, `write_record_json`
under `--record-dir/<run_tag>.record.json`. Prints a one-line summary per cell + a final `PASS`.
Bootstraps repo root on `sys.path`; `raise SystemExit(main())`.

### `resolver/metrics_check.py` — offline correctness gate
Standalone, root-free, network-free (constructs synthetic `PoisonRaceResult` instances directly —
**never** calls `run_poison_race`, so it needs no attacker/draw/engine machinery and cannot be
invalidated by a change there). Asserts:
(a) `poison_rate` on all-poisoned / all-legit / mixed synthetic trial lists (AC-4.1);
(b) `mean_forged_packets` over all trials and `mean_time_to_poison` over the poisoned subset only,
including the zero-poisoned edge case (`None`, not a crash) (AC-4.2);
(c) `amplification_factor` on known rates and the zero-baseline guard (AC-4.3);
(d) `k`/`effective_bits` pass through `collect_cell`'s aggregation unchanged (patch `run_poison_race`
with a stub for this one check only, or assert on the `CellRecord` shape directly from synthetic input
— whichever keeps the module import-clean) (AC-4.4);
(e) `write_record_json` round-trips a `CellRecord`'s `provenance` field-for-field (AC-4.5);
(f) `resolve_cache` maps `poisoned`/`resolved_legit`/`window_closed` to the right state + TTL
presence/absence (epic §5).
Prints `PASS`/`FAIL` per check + a final summary; `raise SystemExit(main())`.

## Interfaces exposed to P5 / P6 (freeze — downstream reads, does not redefine)
- `resolver/metrics.py` `collect_cell(...) -> CellRecord` and `CellRecord`'s field set — **frozen for
  P5**, which calls this once per matrix cell instead of re-driving `run_poison_race` trial loops itself.
- The CSV schema above — P5 concatenates cells into the sweep matrix; P6 may read the summary CSV for
  static display data (the live replay comes from P5's replay-JSON export, not this CSV).
- `.record.json` per cell — the QRNG receipt's frozen home; P5's replay export (`qrng-provenance.json`,
  epic OQ-5) reads the `qrng`-kind cell's record rather than re-calling the Q-EaaS API a second time.
- `resolver/cache.py` `CacheEntry`/`resolve_cache` — the one place "what's cached and until when" is
  computed; P6's provenance/cache panel imports this rather than re-deriving TTL from `t_outcome`.
- P4 does **not** own the experiment matrix, the two headline figures, or the replay-JSON export — P5.
  It does not own the web spectacle — P6.

## File plan
All paths relative to `DNSPoisonRace/`. New unless marked **edit**. Python 3.12+,
`from __future__ import annotations` at the top of every module, full type hints on all public
functions, `@dataclass(frozen=True)` for value/result types, `Literal` for string enums. **Stdlib only**
(`dataclasses`, `typing`, `argparse`, `os`, `sys`, `csv`, `json`, `pathlib`, `statistics`) — no pandas/
matplotlib (confined to P5's `analysis/`), no network beyond what `run_poison_race("qrng", ...)` already
does when asked for.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/resolver/__init__.py` | Package marker; re-export `collect_cell`, `CellRecord`, `resolve_cache`, `CacheEntry`. | — | New package, sibling of `testbed/attacker/`, `testbed/draw/`, `testbed/sim/`. |
| `testbed/resolver/cache.py` | `CacheEntry(state, ttl_expires_at)`; `resolve_cache(result, *, ttl_seconds=config.CACHE_TTL_SECONDS) -> CacheEntry` (epic §5 vocabulary, no new decision logic). | — (epic §5, supports AC-4.5's framing) | Pure, 3-branch mapping over `PoisonRaceResult.outcome`. |
| `testbed/resolver/metrics.py` | `CellRecord` (frozen dataclass); `collect_cell(kind, *, txid_bits, port_bits, k, send_rate_pps, parallel_queries, trials, seed) -> CellRecord` (loops `run_poison_race`, aggregates M1/M2, carries `k`/`effective_bits`/first `provenance`); `amplification_factor(poison_rate_q, poison_rate_baseline) -> float \| None`. | AC-4.1–4.4 | The only module that calls `run_poison_race`; uses `statistics.fmean` over trial lists. |
| `testbed/resolver/csv_writer.py` | `write_row(record, path, *, run_tag)` (stdlib `csv`, frozen header, append + create-with-header-on-first-write); `write_record_json(record, path)` (one JSON object per cell, embeds `provenance`). | AC-4.5, Done-when | No pandas; hand-rolled `csv.DictWriter` only, matching the frozen schema. |
| `testbed/resolver/run_metrics.py` | CLI: `--kind` (repeatable/comma-separated), `--eff-bits`/`--port-bits`/`--send-rate`, `--parallel` (comma-separated, first = baseline), `--trials`, `--seed`, `--out`, `--record-dir`. Per cell: `collect_cell` -> compute `amplification_factor` against the baseline row -> `write_row` -> `write_record_json`. Prints per-cell summary + final `PASS`. | AC-4.1–4.5 (Done-when) | Mirrors `attacker/run_attack.py`'s CLI shape and repo-root `sys.path` bootstrap. |
| `testbed/resolver/metrics_check.py` | Offline correctness gate (project directive — no `pytest`). Synthetic `PoisonRaceResult`/`CellRecord` inputs only — no live `run_poison_race` calls. Checks (a)-(f) above. `raise SystemExit(main())`. | AC-4.1–4.5 (Done-when) | Root-free, network-free, engine-free — cannot be broken by a P1–P3 change, only by a P4 regression. |
| `testbed/config.py` | **edit** — add a `# --- P4: resolver cache + metrics ---` block: `CACHE_TTL_SECONDS = float(os.environ.get("CACHE_TTL_SECONDS", "300"))` (nominal DNS record TTL for the cache-wrapper edge, epic §5), `RESULTS_CSV_PATH = os.environ.get("RESULTS_CSV_PATH", "results/metrics.csv")`, `RESULTS_RECORD_DIR = os.environ.get("RESULTS_RECORD_DIR", "results/records")`. | — | Additive only; reuses existing `TRIALS_PER_CELL`, `SEND_RATE_PPS`, `SAD_DNS_LEAK_BITS`, `PARALLEL_QUERIES` — does not redeclare them. |
| `testbed/README.md` | **edit** — append a "Resolver cache + metrics collector" section: `metrics_check.py`, `run_metrics.py` flags, the CSV/`.record.json` schema, and the amplification-baseline convention (`--parallel`'s first value). | — | Extends the P1–P3 runbook. |

## Manual verification (no automated tests — project directive)
Run from `DNSPoisonRace/`. All steps need **no root and no network** (the last step is opt-in and
touches the QRNG endpoint only).

1. **Offline gate (AC-4.1–4.5, epic §5), run first:** `python3 testbed/resolver/metrics_check.py` →
   prints per-check `PASS` for poison-rate aggregation (a), M2 means + zero-poisoned edge case (b),
   amplification factor + zero-baseline guard (c), `k`/`effective_bits` passthrough (d), `.record.json`
   provenance round-trip (e), and cache-state mapping (f), then a final `PASS`. No network, non-root.
2. **Single cell (AC-4.1/4.2):** `python3 testbed/resolver/run_metrics.py --kind csprng --eff-bits 16
   --send-rate 100000 --trials 2000` → one CSV row with a plausible `poison_rate` (compare against
   plan-3's manually verified `eff_bits=16 -> poison_rate=0.0300` cell — same params should land in the
   same ballpark) and non-empty `mean_forged_packets`/`mean_time_to_poison`.
3. **Amplification factor (AC-4.3):** `python3 testbed/resolver/run_metrics.py --kind csprng --eff-bits
   16 --send-rate 100000 --trials 2000 --parallel 1,8` → the `parallel_queries=8` row's
   `amplification_factor` is `> 1` (compare against plan-3's manual M3 result, `q1=0.0333` vs
   `q8=0.2467`, factor ≈ 7.4 — this run's factor should be in a comparable range, not identical, since
   trial counts/seeds differ).
4. **CSV accumulates (Done-when):** run step 2 twice with different `--eff-bits` → `results/metrics.csv`
   has two rows, header written once, both rows well-formed (`csv.DictReader` round-trips cleanly).
5. **QRNG provenance in `.record.json` (AC-4.5, opt-in):** `set -a && . ./.env && set +a && python3
   testbed/resolver/run_metrics.py --kind qrng --eff-bits 16 --trials 5 --seed 1` → the written
   `results/records/<run_tag>.record.json` carries a `provenance.detail` with the real Q-EaaS receipt
   fields (subject to the live Q-EaaS outage noted in P2/P3's Post-implementation — a graceful skip, not
   a crash, if the endpoint is unreachable).

## Tech
Pure Python 3.12+, stdlib only (`dataclasses`, `typing`, `argparse`, `os`, `sys`, `csv`, `json`,
`pathlib`, `statistics`). No network beyond the opt-in `run_poison_race("qrng", ...)` path P3 already
owns. No pandas/matplotlib (P5's `analysis/` only). No new discrete-event logic — every trial is one
unmodified `run_poison_race` call; P4 only loops and aggregates.

## Out of scope
- **The experiment matrix (bits×send-rate×source), the two headline figures, and the replay-JSON
  export** — **P5**. P4 provides `collect_cell` as the per-cell primitive P5 sweeps over; it does not
  run the full matrix or render anything.
- **The web spectacle and its provenance panel rendering** — **P6**. P4 only guarantees the
  `.record.json` artefact P6 (via P5) can read.
- **The IEEE paper** — **P7**.
- **Any change to `sim/race.py`, `sim/event_queue.py`, `types.py`, `draw/sources.py`, `draw/sad_dns.py`,
  or `attacker/*`** — frozen upstream (epic §3.5); P4 only calls `run_poison_race`.
- **New Q-EaaS quantum-computer runs** — none; P4 consumes the existing client only when `--kind qrng`
  is asked for (Appendix A.2), exactly as P3 does.
- **A live resolver cache with real record data/DNSSEC/multi-record TTL semantics** — out of the study's
  scope (epic §3.4/§6); `CacheEntry` is a state+TTL label, not a real cache implementation.

## Risks
- **Provenance-per-cell is a simplification (AC-4.5).** A cell's `.record.json` carries only the
  **first** trial's provenance; for `qrng` cells every trial mints a fresh Q-EaaS draw with its own
  `request_id`, so the record is representative, not exhaustive. Mitigation: document this explicitly in
  the AC-4.5 note and in `run_metrics.py`'s docstring; P5/P7 must not claim the record.json enumerates
  every draw in the cell.
- **Amplification-factor baseline mismatch.** If a developer runs `--parallel 8` alone (no `1` in the
  list), there is no baseline to divide by. Mitigation: `run_metrics.py` requires the first `--parallel`
  value to be treated as baseline and computes `amplification_factor=None` (not a crash) for any cell
  run without a preceding baseline in the same invocation; document that `--parallel 1,8` (not `--parallel
  8` alone) is required to populate the column.
- **Runtime at high send-rate/high trial counts.** P3's Post-implementation performance note flags
  ~150k heap events per trial at `send_rate_pps=100000`/default retransmit settings — `TRIALS_PER_CELL`
  default `10000` at that send-rate is minutes-to-hours in pure Python. Mitigation: `run_metrics.py`'s
  `--trials` defaults are the CLI's own choice (not forced to `config.TRIALS_PER_CELL`), and the manual
  verification steps above use small trial counts (2000/5); P5's own sweep must budget runtime
  per P3's note, not P4's problem to solve here.
- **CSV/`.record.json` schema drift.** If a later plan renames a `CellRecord` field without updating both
  writers, P5's matrix ingestion silently breaks. Mitigation: `CellRecord` is the single source both
  writers read from — no duplicated field lists — and the schema is declared frozen in this plan (§CSV
  schema) for P5/P6 to rely on.

## Open questions — RESOLVED (2026-07-30, developer: "accept all defaults")
- [x] **OQ-P4.1 — Per-trial seed derivation. RESOLVED (default):** `seed=seed + trial_index` inside
  `collect_cell`'s loop (base seed + integer offset) — simplest reproducible scheme, mirrors P3's own
  `seed`-per-race convention. *Binds `resolver/metrics.py`.*
- [x] **OQ-P4.2 — `CACHE_TTL_SECONDS` default. RESOLVED (default):** `300` (common real-world DNS TTL;
  cosmetic — no downstream metric reads `ttl_expires_at` yet, it exists for P6's cache-panel rendering).
  *Binds `config.py`.*
- [x] **OQ-P4.3 — Multi-kind CSV convenience flag. RESOLVED (default):** `run_metrics.py --kind` accepts
  a comma-separated list (`--kind csprng,qrng`), looping cells across kinds in one invocation as operator
  convenience — P5 is not required to use this, it may call `collect_cell` directly per cell itself.
  *Binds `resolver/run_metrics.py`.*
