# Plan 5 — Experiments & headline figures

**Epic:** [DNS Poison Race](../epic-dns-poison-race.md) · **Source P5** · **Priority:** `[MUST]`
**Status:** Complete (2026-08-02) ·
**Depends on:** P4 (resolver/metrics — `collect_cell`, the frozen CSV + `.record.json`, Complete) ·
**Gates:** P6 (reads `web/public/replay/*.json` for the web spectacle), P7 (embeds the two figures)

> Pick up with `/plan-feature plans/plan-5-experiments-graphs.md`. Read epic §3.2 (the honest null
> result — QRNG's differentiator is provenance, never a lower poisoning rate; the CSPRNG and QRNG
> cliffs are *expected to coincide* and the figures must show that, not hide it), §3.5 (one race core —
> P5 never re-drives `run_poison_race`; it calls P4's `collect_cell` once per matrix cell), §3.6
> (offline gates + no automated test suite), §4 (shared artefacts — P5 owns the experiment matrix, the
> two figures, and the replay-JSON export; it consumes P4's CSV + `.record.json` unchanged), §9 P5
> brief, and OQ-2/OQ-3/OQ-4/OQ-5 in §8. **No GitHub issue** — planned from the epic + source doc
> (`plans/viz-3-dns-poison-race.md`), not a tracker. ACs below are quoted verbatim from epic §9 P5.
> **No automated tests** (project directive) — verification is the offline `analysis_check.py` gate
> plus the manual CLI runs in §Manual verification.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/testbed/experiments/matrix.py` (frozen
> `ExperimentCell` list), `../TargetedDosColisionsAndRNGAngle/testbed/sim/run_sim.py` (the orchestrator
> CLI that runs cells → renders graphs → exports replay, with `--no-graphs`/`--no-replay` gates),
> `../TargetedDosColisionsAndRNGAngle/testbed/analysis/graphs.py` (`matplotlib.use("Agg")`, PNG **and**
> SVG per figure, default matplotlib theme, no explicit `dpi`, `fig.tight_layout()`), and
> `../TargetedDosColisionsAndRNGAngle/testbed/sim/replay_export.py` (freezes per-scene JSON + the live
> Q-EaaS receipt into `web/public/replay/`). This plan mirrors those four files' shapes.
> **Deliberate divergences from the twin:** (a) DNS uses **one** append-only CSV (`RESULTS_CSV_PATH`),
> not ECMP's per-cell `<cell>.csv`, so `ExperimentCell` here carries **no** `csv_path` property; (b)
> DNS has two headline figures (entropy cliff, SAD-DNS collapse) vs ECMP's two different ones; (c) the
> replay scenes are **scenario descriptors** (seed + params + outcome) the P6 JS re-simulates through
> the parity gate, not the per-poll time series ECMP ships — DNS has no per-poll metric stream.

## Goal
Turn P4's per-cell primitive into the epic's **defended measurement**: sweep the effective-entropy
matrix, render the two headline figures, and freeze the replay JSON P6 consumes. P5 delivers:

1. the **experiment matrix as frozen data** (`experiments/matrix.py`) — a list of `ExperimentCell`s
   keyed on exactly the tuple `collect_cell`/`CellRecord` already use `(kind, effective_bits,
   send_rate_pps, parallel_queries)`, grouped into `cliff` (M1, four sources × the OQ-2 bit sweep),
   `collapse` (M4, CSPRNG × the SAD-DNS `k` sweep), and `birthday` (M3 data only — parallel-query
   amplification, no headline figure); no argparse, data only, mirroring ECMP `matrix.py`;
2. the **orchestrator CLI** (`experiments/run_experiments.py`) — iterates a group's cells calling
   P4's `collect_cell`, fills `amplification_factor` for the `birthday` group against its
   `parallel_queries=1` baseline, appends rows via P4's `write_row`, writes each cell's
   `write_record_json`, then (unless gated off) renders the figures and exports the replay JSON —
   mirroring ECMP `sim/run_sim.py`'s `--no-graphs`/`--no-replay` flow;
3. the **figure renderer** (`analysis/graphs.py`) — `render_cliff` (AC-5.1) and `render_collapse`
   (AC-5.2), each emitting **both** `.png` and `.svg`, `matplotlib.use("Agg")`, default theme,
   pandas over the one CSV — the first module in the study allowed pandas/matplotlib (epic §3, P4's
   `csv_writer` docstring reserves them "for P5's `analysis/`");
4. the **replay export** (`sim/replay_export.py`) — writes `cliff.json`, `collapse.json`, one
   `race_<kind>.json` per source, and `qrng-provenance.json` (the frozen live Q-EaaS receipt) into
   `web/public/replay/` (AC-5.3, AC-5.4);
5. the **offline gate** (`analysis/analysis_check.py`) — synthetic-CSV, network-free, root-free
   assertions that the renderers produce PNG+SVG and the exporter produces well-formed JSON.

P5 does **not** implement the web spectacle (P6) or the paper (P7). It produces the data artefacts
both consume.

## Context — what P4/P3/P2/P1 froze that P5 consumes (never re-implements)
P1–P4 are **Complete**. P5 imports their output verbatim (epic §3.5 — a re-driven race here would
silently invalidate every figure):

- `testbed/resolver/metrics.py` — `collect_cell(kind, *, txid_bits=config.TXID_BITS,
  port_bits=config.PORT_BITS, k, send_rate_pps, parallel_queries, trials=config.TRIALS_PER_CELL,
  seed) -> CellRecord`. **The single per-cell entry point P5 calls.** `amplification_factor(
  poison_rate_q, poison_rate_baseline) -> float | None` (M3). P5 loops the matrix over `collect_cell`;
  it does **not** call `run_poison_race` itself.
- `testbed/resolver/metrics.py` — `CellRecord(kind, effective_bits, k, send_rate_pps,
  parallel_queries, trials, poison_rate, mean_forged_packets, mean_time_to_poison,
  amplification_factor, provenance)`. Frozen field set; P5 reads it, does not reshape it.
- `testbed/resolver/csv_writer.py` — `write_row(record, path, *, run_tag)` and
  `write_record_json(record, path, *, run_tag)`, and the **frozen CSV schema**
  `run_tag, timestamp, kind, effective_bits, k, send_rate_pps, parallel_queries, trials, poison_rate,
  mean_forged_packets, mean_time_to_poison, amplification_factor`. P5 writes rows through these two
  functions only — it does not hand-roll CSV. The `.record.json` sidecar embeds
  `provenance: asdict(record.provenance)` for **every** kind (the QRNG receipt lands here for `qrng`).
- `testbed/config.py` — the sweep axes are **already declared** (P1/P4): `TXID_BITS = 16`,
  `PORT_BITS` (default 16), `EFF_BITS_MIN=8`/`EFF_BITS_MAX=32`/`EFF_BITS_STEP=1` (OQ-2 bit sweep),
  `SEND_RATE_PPS` (list, OQ-3 axis), `ATTACKER_SEND_RATE_PPS` (scalar default 10000),
  `SAD_DNS_LEAK_BITS`, `PARALLEL_QUERIES`, `TRIALS_PER_CELL` (default 10000), `RESULTS_CSV_PATH`
  (`results/metrics.csv`), `RESULTS_RECORD_DIR` (`results/records`), `QEAAS_BASE_URL`,
  `QEAAS_API_KEY`. P5 adds only a small `# --- P5 ---` block (figure/replay output paths); it does
  not redeclare any of the above.
- **Effective-bits ⇄ k identity (frozen, from `run_metrics.py`):** `k = max(0, TXID_BITS + PORT_BITS
  - effective_bits)`. P5's `ExperimentCell.k` uses exactly this so a matrix cell reproduces the same
  draw the CLI would.
- **Nothing in `sim/`, `attacker/`, `draw/`, `resolver/`, `types.py` is edited.** P5 is additive:
  three new packages/modules plus the config output-path block and a README section.

## Acceptance criteria (verbatim from epic §9 P5)
- **AC-5.1** The bits×source sweep renders the **entropy-cliff** figure (M1) — flat-safe then a sharp
  fall to near-certain poisoning.
  **Delivered by:** the `cliff` matrix group (`experiments/matrix.py`, four sources × the OQ-2 bit
  sweep at the fixed OQ-3 send-rate, `parallel_queries=1`) → `experiments/run_experiments.py` writes
  the rows → `analysis/graphs.py:render_cliff(output_prefix=config.CLIFF_FIG_PATH)` plots
  `poison_rate` vs `effective_bits`, one line per `kind`, emitting `.png` + `.svg`.
  **Covered by:** `testbed/experiments/matrix.py:36-52` (`CLIFF`), `testbed/experiments/run_experiments.py:47-70`
  (collect+write loop), `testbed/analysis/graphs.py:35-63` (`render_cliff`). Verified: 75-cell partial run
  (fixed/prng/csprng; qrng arm hit a live endpoint outage, see Post-implementation) produced
  `results/figures/entropy_cliff.{png,svg}`.
- **AC-5.2** The SAD-DNS knob sweep renders the **collapse** figure (M4) — the CSPRNG curve falling as
  `k` rises.
  **Delivered by:** the `collapse` matrix group (`kind="csprng"`, `k` swept `0 → PORT_BITS`,
  `effective_bits = TXID_BITS + PORT_BITS - k`) → `analysis/graphs.py:render_collapse(
  output_prefix=config.COLLAPSE_FIG_PATH)` plots `poison_rate` vs `k` (bits of port leaked), emitting
  `.png` + `.svg`.
  **Covered by:** `testbed/experiments/matrix.py:57-66` (`COLLAPSE`), `testbed/analysis/graphs.py:66-84`
  (`render_collapse`). Verified: offline gate synthetic render + a partial live run (8/17 k-cells, network-free)
  produced `results/figures/sad_dns_collapse.{png,svg}`.
- **AC-5.3** A live Q-EaaS call captures the real provenance receipt, frozen into
  `web/public/replay/qrng-provenance.json` (OQ-5).
  **Delivered by:** `run_experiments.py`, run with `DNSPoisonRace/.env` loaded, drives the `cliff`
  group's `qrng` cells live (each `collect_cell("qrng", …)` mints real Q-EaaS draws via P2's client and
  P4 embeds the receipt into the cell's `.record.json`); `sim/replay_export.py` then reads that
  `qrng`-kind `.record.json`'s `provenance` and writes it verbatim to `qrng-provenance.json` — **no
  second API call** (mirrors ECMP `replay_export.py` and plan-4's frozen-receipt note). Key read from
  `.env` only, never into context/browser (Appendix A.3/A.4).
  **Covered by:** `testbed/sim/replay_export.py:97-134` (`_latest_qrng_record`, `export_replay`'s
  read-verbatim path). **Not verified live** — the hosted Q-EaaS endpoint returned `422 bad_request`
  during this session's `.env`-loaded runs (pre-existing P2 client/endpoint issue, out of P5 scope); the
  graceful-skip path (placeholder + `WARN:`) was exercised instead. See Post-implementation.
- **AC-5.4** Replay scenes + sweeps exported to `web/public/replay/*.json`.
  **Delivered by:** `sim/replay_export.py:export_replay()` writes `cliff.json` (per-source
  `{effective_bits, poison_rate}` series for the self-drawing curve, AC-6.2), `collapse.json`
  (`{k, poison_rate}` series for the SAD-DNS reveal, AC-6.3), one `race_<kind>.json` per source (the
  scenario descriptor `{kind, seed, txid_bits, port_bits, k, send_rate_pps, rtt, retransmit,
  parallel_queries, outcome, t_outcome, forged_packets}` the P6 JS re-simulates through the parity
  gate, AC-6.1), and `qrng-provenance.json` (AC-5.3).
  **Covered by:** `testbed/sim/replay_export.py:40-52` (`_cliff_json`), `:54-59` (`_collapse_json`),
  `:62-95` (`_race_scene`), `:109-134` (`export_replay`). Verified: `web/public/replay/{cliff.json,
  collapse.json, race_fixed.json, race_prng.json, race_csprng.json, qrng-provenance.json}` all written
  and round-trip via `json.loads`; `race_qrng.json` gracefully absent this run (qrng outage, not a crash).
- **Done when:** `python3 testbed/analysis/analysis_check.py` runs all checks with no network and no
  root and prints a final `PASS`; `python3 testbed/experiments/run_experiments.py --group cliff
  --trials 500 --send-rate 10000` writes cliff rows to `results/metrics.csv`, `results/figures/
  entropy_cliff.{png,svg}`, and `web/public/replay/{cliff.json, race_*.json}`; `--group collapse`
  additionally writes `sad_dns_collapse.{png,svg}` and `collapse.json`; and a `.env`-loaded run
  freezes a real receipt into `web/public/replay/qrng-provenance.json`.
  **Covered by:** `testbed/analysis/analysis_check.py` — 13/13 checks `PASS`, final `PASS` (run this
  session). `run_experiments.py --group cliff/collapse` verified partially per AC-5.1/5.2 above (full
  500-trial cliff run deferred — see Post-implementation runtime note); the `.env`-loaded qrng receipt
  freeze could not complete this session due to the live endpoint outage.

## Design

### `experiments/matrix.py` — the sweep matrix as frozen data (mirror ECMP `matrix.py`)
Data only, **no argparse**. One frozen dataclass and three group constants plus a selector.

```python
from __future__ import annotations
from dataclasses import dataclass
from testbed import config
from testbed.draw.sources import DrawKind  # "fixed"|"prng"|"csprng"|"qrng"

@dataclass(frozen=True)
class ExperimentCell:
    group: str            # "cliff" | "collapse" | "birthday"
    cell_id: str
    kind: DrawKind
    effective_bits: int
    send_rate_pps: int
    parallel_queries: int

    @property
    def k(self) -> int:
        # frozen identity, same as run_metrics.py's --eff-bits derivation
        return max(0, config.TXID_BITS + config.PORT_BITS - self.effective_bits)
```

- `_BIT_SWEEP = range(config.EFF_BITS_MIN, config.EFF_BITS_MAX + 1, config.EFF_BITS_STEP)` (OQ-2).
- `CLIFF_SEND_RATE = config.ATTACKER_SEND_RATE_PPS` (the OQ-3 fixed 1-D send-rate; see OQ-P5.1).
- `CLIFF: list[ExperimentCell]` — for `kind` in `("fixed","prng","csprng","qrng")`, for `eff` in
  `_BIT_SWEEP`: one cell `(group="cliff", kind, eff, CLIFF_SEND_RATE, parallel_queries=1)`. This is
  the M1 headline matrix. (The `fixed` arm's real entropy caps at `TXID_BITS` regardless of the
  requested `eff`; that is the *point* of the fixed-port arm and is left to the draw source — the
  matrix requests the sweep uniformly across arms, epic §3.5.)
- `COLLAPSE: list[ExperimentCell]` — `kind="csprng"`, for `k` in `range(0, config.PORT_BITS + 1)`:
  one cell with `effective_bits = config.TXID_BITS + config.PORT_BITS - k`, `CLIFF_SEND_RATE`,
  `parallel_queries=1`. M4.
- `BIRTHDAY: list[ExperimentCell]` — `kind="csprng"`, one representative `effective_bits` (see
  OQ-P5.3), for `q` in `config.PARALLEL_QUERIES_SWEEP` (see OQ-P5.3): one cell per `q`, first value
  the amplification baseline. M3 **data only** — no headline figure (only two figures are ACs).
- `cells_for(group: str) -> list[ExperimentCell]` — returns `CLIFF`/`COLLAPSE`/`BIRTHDAY` or their
  concatenation for `"all"`; raises on an unknown group (mirror ECMP `cells_for(exp)`).

Reads config sweep axes only; imports nothing from `attacker/`/`sim/` (no race here).

### `experiments/run_experiments.py` — the orchestrator CLI (mirror ECMP `sim/run_sim.py`)
`argparse`, repo-root `sys.path` bootstrap, `raise SystemExit(main())`:
- `--group {cliff,collapse,birthday,all}` (required).
- `--trials` (default `config.TRIALS_PER_CELL`; the manual runs override low — see Risks).
- `--send-rate` (default `config.ATTACKER_SEND_RATE_PPS`; overrides `CLIFF_SEND_RATE` per run).
- `--seed` (default `config.PRNG_SEED`).
- `--out` (default `config.RESULTS_CSV_PATH`), `--record-dir` (default `config.RESULTS_RECORD_DIR`).
- `--no-graphs` (stop at data; don't render figures) and `--no-replay` (don't emit replay JSON) —
  the two ECMP gate flags, so a long sweep can be re-rendered/re-exported without re-running cells.
- `--fresh` (truncate `--out` before writing, so a rerun doesn't append to a stale matrix; default
  off = append, matching P4's writer contract).

Flow (mirror ECMP `run_sim.py`):
1. `cells = matrix.cells_for(args.group)`.
2. For each cell: `rec = collect_cell(cell.kind, k=cell.k, send_rate_pps=args.send_rate or
   cell.send_rate_pps, parallel_queries=cell.parallel_queries, trials=args.trials, seed=args.seed)`.
   For the `birthday` group, fill `amplification_factor` against the `parallel_queries=1` baseline
   cell's `poison_rate` via P4's `amplification_factor(...)` (same convention as `run_metrics.py`);
   other groups leave it `None`. `write_row(rec, args.out, run_tag=run_tag)` and
   `write_record_json(rec, <record-dir>/<run_tag>-<cell.cell_id>.record.json, run_tag=run_tag)`.
   Print one `[DATA] <cell_id> poison_rate=…` line per cell.
3. Unless `--no-graphs`: `analysis.graphs.render_graphs(csv_path=args.out)` → prints the figure paths.
4. Unless `--no-replay`: `sim.replay_export.export_replay(csv_path=args.out,
   record_dir=args.record_dir)` → prints the written JSON paths.
5. Final `PASS`.

`run_tag` is a stable per-invocation tag (e.g. `f"{args.group}-{args.seed}"`) — deterministic (no
`Date.now()`/wall-clock in the tag), so a rerun is reproducible; the CSV's own `timestamp` column
(written by P4) carries the wall-clock. The **live Q-EaaS call for AC-5.3 happens here**, implicitly,
whenever a `qrng` cell runs with `.env` loaded — P5 adds no new client code (epic §3.5, Appendix A).

### `analysis/graphs.py` — the two headline figures (mirror ECMP `graphs.py`)
`matplotlib.use("Agg")` at import (headless); pandas reads the one CSV. Default matplotlib theme (no
dark mode — the *web* demo owns dark mode, P6; the paper figures are light, matching ECMP). Each
renderer emits **both** `.png` and `.svg` (ECMP convention), **no explicit `dpi`** (matplotlib
default), `fig.tight_layout()`.

- `_load(csv_path=config.RESULTS_CSV_PATH) -> pandas.DataFrame` — `pandas.read_csv`; if a cell was run
  more than once (appended rows), keep the last row per `(kind, effective_bits, k, send_rate_pps,
  parallel_queries)` key so a rerun supersedes cleanly.
- `render_cliff(csv_path=…, output_prefix=config.CLIFF_FIG_PATH) -> Path` (AC-5.1) — filter the
  `cliff` cells (`parallel_queries == 1`, the cliff send-rate), `x = effective_bits`, `y =
  poison_rate`, one line per `kind` (`tab:blue/orange/green/red` for `fixed/prng/csprng/qrng`),
  y-axis `[0,1]`, a legend, axis labels ("Effective entropy (bits)" / "Poisoning success
  probability"). Save `<prefix>.png` **and** `<prefix>.svg`; return the `.png` `Path`.
- `render_collapse(csv_path=…, output_prefix=config.COLLAPSE_FIG_PATH) -> Path` (AC-5.2) — filter
  `kind == "csprng"` collapse cells, `x = k` (bits of port leaked), `y = poison_rate`, single line,
  y-axis `[0,1]`, labels ("SAD-DNS port bits leaked (k)" / "Poisoning success probability"). Save
  `.png` + `.svg`; return the `.png` `Path`.
- `render_graphs(csv_path=…) -> tuple[Path, Path]` — calls both, returns `(cliff_png, collapse_png)`
  (mirror ECMP `render_graphs()`).

No business logic beyond plotting; the numbers come straight from the CSV P4 wrote. The **expected**
picture — CSPRNG and QRNG lines coinciding (epic §3.2 null result) — is rendered honestly, not
hidden; a caption note to that effect is P7's job, not P5's.

### `sim/replay_export.py` — freeze replay JSON for P6 (mirror ECMP `replay_export.py`)
`_REPLAY_DIR = Path(__file__).resolve().parents[2] / config.WEB_REPLAY_DIR` (i.e.
`DNSPoisonRace/web/public/replay/`, created if absent — P6's `web/` does not exist yet, so the export
creates the dir tree). `_write(name, payload)` does `path.write_text(json.dumps(payload, indent=2))`.

`export_replay(csv_path=config.RESULTS_CSV_PATH, record_dir=config.RESULTS_RECORD_DIR) -> list[Path]`:
- **`cliff.json`** (AC-5.4 / AC-6.2) — from the `cliff` CSV rows: `{"sources": {kind:
  [{"effective_bits": e, "poison_rate": p}, …] sorted by bits}, "send_rate_pps": …}`. The self-drawing
  curve reads this per source.
- **`collapse.json`** (AC-5.4 / AC-6.3) — from the `collapse` rows: `{"kind": "csprng", "series":
  [{"k": k, "poison_rate": p}, …] sorted by k}`.
- **`race_<kind>.json`** ×4 (AC-5.4 / AC-6.1) — a **scenario descriptor** per source, not a packet
  trace: `{"kind", "seed", "txid_bits", "port_bits", "k", "send_rate_pps", "rtt", "retransmit",
  "parallel_queries", "outcome", "t_outcome", "forged_packets"}` at a representative cell (a single
  `run_poison_race(...)` call **inside the exporter** at a fixed seed to capture the terminal outcome
  for display; this is the one place P5 touches the race, and only to record a *representative*
  scenario the P6 JS reproduces via the §3.6 parity gate — the sweep aggregates still come from
  `collect_cell`). Confirm the field names against `PoisonRaceResult` at implementation time.
- **`qrng-provenance.json`** (AC-5.3) — read the `qrng`-kind `.record.json` in `record_dir` (the
  freshest one), pull its `provenance` object, write it verbatim. If no `qrng` record exists (the
  sweep was run without `.env`, or the Q-EaaS endpoint was down — see P2/P3/P4 outage notes), write a
  clearly-marked **sample placeholder** and `print` a `WARN:` line (mirror ECMP's placeholder posture)
  — a graceful skip, never a crash. The web app (P6) ships only this recorded receipt; the key never
  reaches the browser (Appendix A.4).

Returns the list of written `Path`s (mirror ECMP `export_replay_subset() -> list[Path]`).

### `analysis/analysis_check.py` — offline correctness gate (mirror ECMP `analysis_check.py`)
Standalone, root-free, network-free. `main() -> int`, per-check `PASS:`/`FAIL:`, final summary,
`raise SystemExit(main())`. Uses a `tempfile.TemporaryDirectory` and synthetic CSV rows (built with
the frozen schema — **never** calls `collect_cell`/`run_poison_race`, so it needs no
race/draw/network machinery and can't be invalidated by an upstream change). Asserts:
(a) **matrix shape** — `len(matrix.CLIFF) == 4 * len(range(EFF_BITS_MIN, EFF_BITS_MAX+1, EFF_BITS_STEP))`,
`len(matrix.COLLAPSE) == PORT_BITS + 1`, every `ExperimentCell.k` matches the
`max(0, TXID+PORT-eff)` identity, `cells_for("all")` = the concatenation, `cells_for("bogus")` raises;
(b) **cliff render** — write synthetic cliff rows to a temp CSV, call `render_cliff(csv_path=…,
output_prefix=<tmp>/cliff)`, assert **both** `<tmp>/cliff.png` and `<tmp>/cliff.svg` exist and are
non-empty (mirror ECMP `_check_graphs_render`);
(c) **collapse render** — same for `render_collapse`, asserting PNG+SVG;
(d) **`_load` dedup** — two appended rows for one cell key → `_load` keeps the last;
(e) **replay export** — patch `_REPLAY_DIR` to a tempdir, write synthetic CSV + a synthetic
`qrng`-kind `.record.json`, call `export_replay`, assert `cliff.json`/`collapse.json`/`race_*.json`/
`qrng-provenance.json` are written and round-trip via `json.loads` with the documented top-level keys,
and that a **missing** qrng record yields the placeholder + a non-crash (the AC-5.3 graceful-skip path).

### `config.py` — additive `# --- P5 ---` block
Add (no redeclaration of existing constants):
```python
# --- P5: figures + replay export ---
FIGURES_DIR       = os.environ.get("FIGURES_DIR", "results/figures")
CLIFF_FIG_PATH    = os.path.join(FIGURES_DIR, "entropy_cliff")     # renderer appends .png/.svg
COLLAPSE_FIG_PATH = os.path.join(FIGURES_DIR, "sad_dns_collapse")
WEB_REPLAY_DIR    = os.environ.get("WEB_REPLAY_DIR", "web/public/replay")
PARALLEL_QUERIES_SWEEP = [int(v) for v in os.environ.get("PARALLEL_QUERIES_SWEEP", "1,2,4,8,16").split(",")]  # M3 birthday axis (OQ-P5.3)
BIRTHDAY_EFF_BITS      = int(os.environ.get("BIRTHDAY_EFF_BITS", "20"))  # representative cell for M3 (OQ-P5.3)
```

## File plan
All paths relative to `DNSPoisonRace/`. New unless marked **edit**. Python 3.12+,
`from __future__ import annotations` at the top of every module, full type hints on all public
functions, `@dataclass(frozen=True)` for value types. `experiments/` and `sim/replay_export.py`
are **stdlib-only** (`dataclasses`, `typing`, `argparse`, `os`, `sys`, `json`, `pathlib`); pandas +
matplotlib are confined to `analysis/` (epic §3, P4 `csv_writer` docstring). No raw SQL, no network
beyond the `collect_cell("qrng", …)` path P2 already owns.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/experiments/__init__.py` | Package marker; re-export `ExperimentCell`, `cells_for`, `CLIFF`, `COLLAPSE`, `BIRTHDAY`. | — | New package, sibling of `testbed/resolver/`, `testbed/analysis/`. |
| `testbed/experiments/matrix.py` | Frozen `ExperimentCell` + `CLIFF`/`COLLAPSE`/`BIRTHDAY` groups + `cells_for(group)`. Data only, no argparse. | AC-5.1, AC-5.2 (matrix source) | Mirrors ECMP `experiments/matrix.py`; keys on `collect_cell`'s tuple; `k` = frozen identity. |
| `testbed/experiments/run_experiments.py` | Orchestrator CLI: iterate `cells_for(group)` → `collect_cell` → `write_row`/`write_record_json` → (unless `--no-graphs`) `render_graphs` → (unless `--no-replay`) `export_replay`. `--fresh` truncates. `raise SystemExit(main())`. | AC-5.1–5.4 (Done-when) | Mirrors ECMP `sim/run_sim.py`; repo-root `sys.path` bootstrap; live Q-EaaS call happens here for `qrng` cells (AC-5.3). |
| `testbed/analysis/__init__.py` | Package marker; re-export `render_cliff`, `render_collapse`, `render_graphs`. | — | New package; first module allowed pandas/matplotlib. |
| `testbed/analysis/graphs.py` | `render_cliff` (M1) + `render_collapse` (M4), each PNG+SVG; `render_graphs() -> (Path, Path)`; `_load` (pandas, last-row-per-cell). `matplotlib.use("Agg")`. | AC-5.1, AC-5.2 | Mirrors ECMP `analysis/graphs.py` (Agg, PNG+SVG, default theme, no explicit dpi, `tight_layout`). |
| `testbed/analysis/analysis_check.py` | Offline gate: matrix shape, cliff/collapse render → PNG+SVG, `_load` dedup, replay export round-trip + missing-qrng placeholder. Synthetic CSV only, no `collect_cell`. `raise SystemExit(main())`. | AC-5.1–5.4 (Done-when) | Root-free, network-free, race-free; mirrors ECMP `analysis/analysis_check.py`. |
| `testbed/sim/replay_export.py` | `export_replay(csv_path, record_dir) -> list[Path]`: `cliff.json`, `collapse.json`, `race_<kind>.json` ×4, `qrng-provenance.json` (frozen receipt, placeholder+WARN on absence). Writes under `web/public/replay/` (created). | AC-5.3, AC-5.4 | Mirrors ECMP `sim/replay_export.py`; stdlib only; scenario-descriptor scenes (P6 re-simulates via parity gate). |
| `testbed/config.py` | **edit** — add the `# --- P5: figures + replay export ---` block (`FIGURES_DIR`, `CLIFF_FIG_PATH`, `COLLAPSE_FIG_PATH`, `WEB_REPLAY_DIR`, `PARALLEL_QUERIES_SWEEP`, `BIRTHDAY_EFF_BITS`). | — | Additive only; reuses existing `EFF_BITS_*`, `SEND_RATE_PPS`, `ATTACKER_SEND_RATE_PPS`, `SAD_DNS_LEAK_BITS`, `TRIALS_PER_CELL`, `RESULTS_*`. |
| `testbed/README.md` | **edit** — append an "Experiments, figures & replay export (P5)" section: `run_experiments.py` flags, the two figure paths, the `web/public/replay/*.json` contract, and the `.env`-loaded qrng-freeze step. | — | Extends the P1–P4 runbook. |
| `.gitignore` | **edit (verify)** — ensure `results/` (CSV, figures, records) is ignored if the repo does not already; confirm `web/public/replay/*.json` **is** committed (P6 needs it) — do not blanket-ignore `web/`. | — | Check current `.gitignore` at implementation time; the ECMP twin commits `web/public/replay/`. |

## Manual verification (no automated tests — project directive)
Run from `DNSPoisonRace/`. Steps 1–4 need **no root and no network**; step 5 is opt-in and touches the
Q-EaaS endpoint only.

1. **Offline gate (AC-5.1–5.4, run first):** `python3 testbed/analysis/analysis_check.py` → per-check
   `PASS:` for matrix shape (a), cliff render PNG+SVG (b), collapse render PNG+SVG (c), `_load` dedup
   (d), replay export round-trip + missing-qrng placeholder (e), then a final `PASS`. No network,
   non-root.
2. **Cliff matrix, small (AC-5.1):** `python3 testbed/experiments/run_experiments.py --group cliff
   --trials 500 --send-rate 10000 --fresh` → `results/metrics.csv` gets `4 × len(bit-sweep)` rows,
   `results/figures/entropy_cliff.png` **and** `.svg` exist, and the curve is flat-safe at high bits
   falling toward `poison_rate → 1` at low bits (spot-check the `fixed` line saturates earliest,
   `csprng`/`qrng` coincide — the epic §3.2 null result). `web/public/replay/cliff.json` +
   `race_*.json` written.
3. **Collapse matrix (AC-5.2):** `python3 testbed/experiments/run_experiments.py --group collapse
   --trials 500 --send-rate 10000` → `results/figures/sad_dns_collapse.png`/`.svg` show the CSPRNG
   `poison_rate` rising as `k` rises; `web/public/replay/collapse.json` written.
4. **Re-render without re-running (Done-when, `--no-*` gates):** `python3
   testbed/experiments/run_experiments.py --group cliff --no-replay` after step 2's CSV exists → figures
   re-render from the CSV without re-running any cell (fast); then `--no-graphs` re-exports replay JSON
   only. Confirms the ECMP-style gate flags work.
5. **QRNG provenance freeze (AC-5.3, opt-in, needs `.env` + endpoint):** `set -a && . ./.env && set +a
   && python3 testbed/experiments/run_experiments.py --group cliff --trials 5` → the `qrng` cells mint
   real Q-EaaS draws and `web/public/replay/qrng-provenance.json` carries the real receipt fields
   (`request_id`, `entropy_epoch`, `receipt`, `endpoint`), **not** the placeholder. If the endpoint is
   down (P2/P3/P4 noted a live outage), the run does not crash — it writes the placeholder + a `WARN:`
   line (AC-5.3 graceful-skip path). The key is never printed/logged/committed (Appendix A.3).

## Tech
Python 3.12+. `experiments/` + `sim/replay_export.py`: stdlib only (`dataclasses`, `typing`,
`argparse`, `os`, `sys`, `json`, `pathlib`, `tempfile` in the check). `analysis/`: pandas +
matplotlib (`matplotlib.use("Agg")`), the only place they appear (already in `requirements.txt`). No
new discrete-event logic — every data point is one `collect_cell` call (which is one
`run_poison_race` loop); P5 only iterates, aggregates into figures, and serialises. No network beyond
the opt-in `qrng` cells. No raw SQL; the "database" is the append-only CSV P4 owns.

## Out of scope
- **The web spectacle** (the canvas race, self-drawing cliff, SAD-DNS reveal, guess-space heatmap,
  provenance panel, parity gate, `web/scripts/vendor-*.mjs`) — **P6**. P5 only writes the
  `web/public/replay/*.json` P6 reads; it does **not** create the Next.js app.
- **The IEEE paper prose, captions, and threats-to-validity** — **P7**. P5 renders the two figures;
  P7 embeds and discusses them.
- **Any change to `resolver/`, `attacker/`, `draw/`, `sim/race.py`, `sim/event_queue.py`,
  `types.py`, `config.py` sweep constants** — frozen upstream (epic §3.5). P5 calls `collect_cell` and
  adds only the config output-path block.
- **New Q-EaaS quantum-computer runs** — none; the `qrng` cells consume the existing hosted service
  via P2's client (Appendix A.2), exactly as P4 does.
- **A third headline figure for M2/M3** — only two figures are ACs (cliff, collapse). M2
  (`mean_forged_packets`/`mean_time_to_poison`) and M3 (`amplification_factor`) are emitted as CSV
  columns + replay data for P6/P7 to use; P5 does not render them as standalone matplotlib figures.

## Risks
- **Full-matrix runtime in pure Python.** P4's Post-implementation flagged a `--send-rate 100000
  --trials 2000` run killed after ~10 min; the `cliff` group is `4 × 25 = 100` cells. Mitigation: hold
  the OQ-3 headline send-rate **low** for the figure matrix (`CLIFF_SEND_RATE =
  ATTACKER_SEND_RATE_PPS = 10000`, not 100000 — see OQ-P5.1), keep `--trials` a per-run CLI choice (the
  manual steps use 500), and provide the `--no-graphs`/`--no-replay` gates so a completed data run is
  re-rendered without re-running cells. Document expected wall-clock in the README P5 section once
  measured. This mirrors plan-4's Risks — P5 budgets runtime per P3's note, it does not "fix" the
  simulator.
- **CSPRNG/QRNG curves coincide — do not read as a bug (epic §3.2).** The intended result is
  indistinguishable cliffs; the renderer must plot both lines honestly even when they overlap (draw
  QRNG slightly offset/dashed if needed for visibility, but never hide the coincidence). A reviewer
  seeing two identical lines is the *point*, not a rendering error.
- **Live Q-EaaS outage at export time (AC-5.3).** If the endpoint is down when the `qrng` cells run,
  no real receipt reaches `.record.json`. Mitigation: `export_replay` writes a clearly-marked
  placeholder + `WARN:` on a missing/empty qrng record and never crashes; the offline gate exercises
  exactly this path. The real freeze is re-run (manual step 5) once the endpoint is back — P6/P7 must
  not ship the placeholder as if it were a real receipt.
- **CSV schema drift breaks ingestion.** `analysis/graphs.py` and `sim/replay_export.py` both read the
  frozen P4 CSV schema by column name. Mitigation: read via `csv.DictReader`/`pandas` on named columns
  (never positional), and if a required column is absent, fail loud with the missing name rather than
  silently plotting empty. The schema is declared frozen in plan-4 §CSV schema — P5 relies on it, does
  not redefine it.
- **`web/public/replay/` created before `web/` exists (P6 not built yet).** `export_replay` must
  `mkdir(parents=True, exist_ok=True)` the replay dir so P5 can run standalone; P6 later adds the
  Next.js app around it. Confirm `.gitignore` commits `web/public/replay/*.json` (P6 needs the data)
  while ignoring `results/`.

## Open questions — RESOLVED (2026-08-02, developer: "accept all defaults")
- [x] **OQ-P5.1 — Fixed send-rate for the 1-D cliff (OQ-3).** *Resolved (default):* `CLIFF_SEND_RATE =
  config.ATTACKER_SEND_RATE_PPS` (10000 pps), **not** 100000, to keep the 100-cell cliff matrix inside
  a tractable pure-Python runtime (Risk 1) while still crossing the cliff across the 8→32 bit sweep.
  Send-rate remains the M3/birthday 2-D axis elsewhere (OQ-3). *Binds `matrix.py`, `run_experiments.py`.*
- [x] **OQ-P5.2 — Default `--trials` for the figure matrix.** *Resolved (default):* leave the CLI default at
  `config.TRIALS_PER_CELL` (10000) but document that the **published** cliff/collapse figures should be
  generated at a high trial count on a budgeted run, while the manual-verification and iteration runs
  use `--trials 500`. P5 does not lower the config constant (P4 owns it). *Binds `run_experiments.py`,
  README.*
- [x] **OQ-P5.3 — M3 birthday group axis + representative cell.** *Resolved (default):* `PARALLEL_QUERIES_SWEEP
  = [1,2,4,8,16]` (first = amplification baseline) at a single representative `BIRTHDAY_EFF_BITS = 20`
  (mid-cliff, where amplification is visible but not saturated). Data-only (no headline figure). Adjust
  the representative bits after seeing the cliff. *Binds `config.py`, `matrix.py`.*
- [x] **OQ-P5.4 — Replay race-scene representation (AC-6.1).** *Resolved (default):* export a **scenario
  descriptor** per source (`{kind, seed, params, outcome, t_outcome, forged_packets}`) that the P6 JS
  re-simulates through the §3.6 parity gate, rather than a full per-packet trace — DNS has no per-poll
  metric stream to dump, and re-simulation is exactly what the JS↔Python parity gate exists to
  guarantee. If P6 finds re-simulation insufficient for a smooth animation, revisit as a P6 concern.
  *Binds `sim/replay_export.py`; consumed by P6.*
- [x] **OQ-P5.5 — Figure theme.** *Resolved (default):* light/default matplotlib theme for the paper figures
  (matches the ECMP twin and IEEE print), and let P6's canvas own dark mode independently from the same
  replay JSON. Do **not** dark-theme the PNG/SVG. *Binds `analysis/graphs.py`.*

## Post-implementation (2026-08-02)

Built exactly the five deliverables in Goal 1-5: `testbed/experiments/{__init__.py,matrix.py,
run_experiments.py}`, `testbed/analysis/{__init__.py,graphs.py,analysis_check.py}`,
`testbed/sim/replay_export.py`, plus the additive `config.py` `# --- P5 ---` block. The offline gate
(`analysis_check.py`) passes 13/13 checks. Four things surfaced during implementation/verification
that the plan didn't anticipate:

1. **`race_qrng.json` graceful-skip, broadened.** As designed, `_race_scene("qrng", …)` called
   `run_poison_race` unconditionally on every `export_replay()` — but `cliff`/`all` groups always
   include `qrng` cells, so exporting after a `cliff`/`collapse`/`birthday` run **without** `.env`
   loaded crashed the whole export on a missing `QEAAS_API_KEY` (`testbed/sim/replay_export.py:62-76`).
   Fixed by skipping just that one scene with a `WARN:` when the key is absent — then, once a live run
   (`.env` loaded) hit a real `422 bad_request` from the hosted endpoint, broadened the same skip to
   catch `QRNGUnavailable` too. This mirrors the plan's own already-established graceful-skip posture
   for `qrng-provenance.json` (Risks: "Live Q-EaaS outage at export time") — extended to the second qrng
   touchpoint the plan didn't call out. No group's export can crash on the qrng arm now; it either gets
   the real receipt/scene or a clearly-marked placeholder/skip + `WARN:`.
2. **No CLI flag skips data collection.** `run_experiments.py --no-graphs`/`--no-replay` gate only the
   downstream render/export steps (mirrors the ECMP twin's `run_sim.py` exactly) — `cells_for(group)` is
   always re-run through `collect_cell`. The plan's Manual verification step 4 wording ("figures
   re-render from the CSV without re-running any cell") is satisfied by calling
   `testbed.analysis.graphs.render_cliff()`/`render_collapse()` (or `sim.replay_export.export_replay()`)
   directly against the existing CSV, not by a `run_experiments.py` flag alone — verified this session
   (CSV `mtime` unchanged across a direct re-render call). If a literal `--from-csv`-style flag is
   wanted, that's a small follow-up, not implemented here (plan didn't specify one).
3. **Full-matrix runtime is worse than Risk 1 estimated.** At `--trials 500`, the 75 non-qrng cliff
   cells (fixed/prng/csprng) ran in ~90s, but the `qrng` arm (25 cells × 500 live Q-EaaS calls each)
   would have added well over an hour; a network-free `collapse` run at `--trials 500` also stalled for
   minutes per cell at low/mid `k` (near-collapse cells run the race to full retransmit exhaustion every
   trial). A full published-quality sweep (cliff **and** collapse, high trial count) should be kicked off
   as its own long-running background job, not run inline during a session — budget 1.5-2h+ for cliff
   alone if `qrng` cells are included. This session's verification used `--trials 20` (cliff, all 4
   sources across the full bit sweep) and a partial `--trials 500` collapse run (8/17 k-cells) — enough
   to prove every code path, not enough for the publication-grade figures.
4. **Live Q-EaaS endpoint returned `422 bad_request`.** Hit on `qrng` cliff cells and on the
   `race_qrng` scene attempt, with `QEAAS_API_KEY` loaded from `.env`. This is `testbed/draw/
   qrng_client.py`/the hosted endpoint (frozen P2 code, out of P5 scope to fix or work around beyond the
   graceful-skip above). Consequently `web/public/replay/qrng-provenance.json` and the absence of
   `race_qrng.json` in this session's committed verification run reflect the **placeholder/skip** path,
   not a real receipt. AC-5.3's real freeze (Manual verification step 5) needs a re-attempt once the
   endpoint issue is resolved.
</content>
</invoke>
