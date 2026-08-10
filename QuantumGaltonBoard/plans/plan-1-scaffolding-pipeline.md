# Plan P1 — Scaffolding & Heron r2 pipeline wiring

**Epic:** `plans/epic-quantum-galton-board.md` (Status: Draft — OQs resolved 2026-08-06)
**Plan ID:** P1 (`[MUST]`, gates P2/P3/P4/P5)
**Slug:** scaffolding-pipeline
**Author:** Claude (Opus)
**Date:** 2026-08-06
**Status:** Complete (2026-08-10)

> **No automated tests (project directive, epic §3.6).** Verification is offline
> correctness gates + the root-free `--sim`/ideal path only. This plan lists no test
> files, no test suites, and no AC→test mapping. "How to verify" everywhere means the
> offline `scaffold_check.py` gate and a manual root-free run.

---

## 1. Context

P1 is the foundation ticket of the Quantum Galton Board epic. It ships nothing physics-
facing; it freezes the contracts every later plan builds on:

- the `code/` package skeleton and output-dir discipline (`runs/`, `research_runs/`),
- `config.py` as the single environment/arg source of truth,
- `WALK_SPEC` — the position/coin decode contract (the DTQW analogue of QuantumLife's
  `genome.py:GENOME_SPEC`, `QuantumLife/code/genome.py:33`), embedded verbatim into every
  `run.json` so the P5 JS viewer decodes identically,
- the frozen `run.json` / `summary.json` schema,
- the reuse-not-copy wiring to the calibration study's `pipeline_common` submission path,
- a minimal root-free `--sim`/ideal path that proves the plumbing end to end.

**Structural twin:** `QuantumLife/code/{qtree.py,genome.py,layout.py}` and its
`runs/`+`research_runs/` split. Every convention below has a working precedent there.
This plan mirrors those files' structure; it does not copy the tree-specific logic.

**Reuse target (verified on disk 2026-08-06):**
- `pipeline_common.py` (the reused IBM submission path) lives at
  `CalibrationGuidedHighYieldQRNG/old/code/pipeline_common.py`. Signatures (verbatim):
  - `connect(name: str | None) -> Any` — live `QiskitRuntimeService`; explicit backend or
    least-busy Heron r2 (`pipeline_common.py:29`).
  - `run_sampler(backend, isa, shots, shots_per_job=SHOTS_PER_JOB) -> tuple[list[str],
    list[dict], float]` — chunked SamplerV2 loop; **reads `res[0].data.c.get_bitstrings()`**,
    i.e. the `ClassicalRegister` MUST be named `"c"` (`pipeline_common.py:59,73`).
  - `timestamp() -> str` — `"%Y%m%d-%H%M%S"` (`pipeline_common.py:55`).
- `best_chain(backend, n, time_budget=40.0) -> tuple[list[int], dict]` is a **QuantumLife-
  local module** (`QuantumLife/code/layout.py:52`), **not** part of the calibration study.
  It raises if no length-`n` SWAP-free chain exists — that ceiling sets the max walk depth
  `N` (OQ-2). See OQ-1.2 below: the epic §3.3/Appendix A.1 mis-state its origin.

## 2. Acceptance criteria (from epic §9 P1 → source §Method, §Connection)

Copied from the epic brief; IDs preserved.

- [x] **AC-1.1** A root-free, QPU-free ideal/`--sim` run produces one `run.json` for a trivial
  2-step walk, end to end (build → simulate → decode → write).
  *Covered by* `code/galton.py:71` (`run_ideal`: build `code/galton.py:35` → simulate
  `code/galton.py:61` → decode `code/walk_spec.py:39` → write `code/pipeline.py:83`); verified
  §8.1 — `runs/ideal_statevector_steps2_seed100_*_run.json` written.
- [x] **AC-1.2** `config.py` reads the backend name, IBM account env, depth range `N`, shots,
  seeds, and the hw-depth subset from environment/args only — no hardcoded values in the
  business logic.
  *Covered by* `code/config.py:63` (`load`, arg>env>default) + `code/config.py:73-79`; verified
  §8.3 — `SHOTS=1024` lands in `meta.shots`, `BACKEND` in `meta.environment`.
- [x] **AC-1.3** `WALK_SPEC` and the `run.json` schema are frozen and documented for P2/P3/P5,
  and `WALK_SPEC` is embedded verbatim into every `run.json` (mirror `genome.py`).
  *Covered by* `code/walk_spec.py:22` (`WALK_SPEC`), `code/SCHEMA.md`, embedded verbatim at
  `code/galton.py:88`; verified §8.2 — gate asserts `meta.walk_spec == WALK_SPEC`.
- [x] **AC-1.4** Hardware wiring imports `pipeline_common.{connect,run_sampler,timestamp}` from
  the calibration study (reuse, not copy) and provides `best_chain`; the `ClassicalRegister`
  is named `"c"` (epic §3.3).
  *Covered by* `code/pipeline.py:54` (import), `code/pipeline.py:77-80` (`classical_register`
  → `"c"`), `code/layout.py:54` (`best_chain`); verified §8.4 — three symbols resolve,
  `_CALIB_CODE` = `.../old/code` (OQ-1.1 fallback).

## 3. Out of scope (deferred, not omitted)

- The general parameterised walk builder `build_walk(steps, coin, encoding)` → **P2**. P1
  ships only a minimal 2-step one-hot reference circuit sufficient to exercise the pipeline
  (AC-1.1). P2 replaces it with the real builder.
- The three-arm dispatch `run_arm(ideal|noisy|hw)` and any real hardware / noisy-model
  submission → **P2**. P1 wires the *imports* and writers; it does not call `connect` /
  `run_sampler` against a live backend.
- The four metrics and the knee extractor → **P3**.
- Sweeps, figures, replay-JSON export → **P4**. P1 defines the `summary.json` schema but
  does not aggregate a sweep.
- The web viewer and its JS `WALK_SPEC` mirror → **P5** (P1 only freezes the spec it mirrors).
- No QRNG / QEaaS arm or provenance receipt (epic §3.7).

## 4. Decisions inherited from the epic (do not re-litigate)

- **Encoding (OQ-1 LOCKED):** one-hot line. An `n`-step walk uses `n+1` position qubits
  (one qubit per reachable bin) + 1 coin qubit = `n+2` qubits total; direct histogram decode.
- **Three arms, one circuit (§3.2):** only the backend varies. P1 provides the plumbing; P2
  the builder.
- **Reuse the pipeline, do not copy (§3.3):** import `pipeline_common`; never reimplement
  submission. (Origin path corrected in OQ-1.2.)
- **`--sim`/ideal is root-free (§3.5, §3.6):** the ideal arm runs on `AerSimulator`
  (statevector) with no IBM account and no QPU cost. P1's smoke path is this arm.
- **Fixed Hadamard coin (OQ-4):** the only coin in v1. `WALK_SPEC.coin = "hadamard"`.

## 5. The `WALK_SPEC` contract (the frozen interface)

`WALK_SPEC` is a module-level `dict` in `code/walk_spec.py`, mirroring the shape and role of
`genome.py:GENOME_SPEC` (`QuantumLife/code/genome.py:33`): a static decode contract embedded
verbatim into `run.json` and hand-mirrored in the P5 JS decoder. Unlike `GENOME_SPEC` (fixed
108-qubit register), the walk register size grows with depth, so `WALK_SPEC` encodes the
decode **rule**, and each `run.json` records the concrete `steps` / `n_position_qubits`.

```python
WALK_SPEC: dict = {
    "encoding": "one_hot_line",   # OQ-1
    "coin": "hadamard",           # OQ-4
    "coin_qubit": 0,              # coin qubit index in the register (MSB/LSB rule stated)
    "position_qubits": "1..n+1", # one-hot bins; qubit j set == amplitude at bin j
    # bin index -> signed lattice position for an n-step walk
    "bin_to_position": "pos = 2*bin - n",   # bins 0..n  ->  positions -n..+n (step 2)
    "bitstring_order": "little",  # how run_sampler bitstrings map to qubit indices
    "version": 1,
}
```

`code/walk_spec.py` also owns the single decode function, the Python source of truth the JS
viewer must reproduce (parity gate, epic §3.6):

```python
def decode_counts(counts: dict[str, int], steps: int,
                  spec: dict = WALK_SPEC) -> dict[int, float]:
    """Raw measured bitstring counts -> normalised {position: probability}."""
```

The exact one-hot bit→bin map and the coin/position qubit ordering are frozen here in P1
and cited by P2 (`build_walk`), P3 (metrics consume the histogram), and P5 (JS decoder).

## 6. File Plan

All paths under `QuantumGaltonBoard/`. Strict `from __future__ import annotations`, full type
hints, stdlib + qiskit + qiskit-aer only in the core (no pandas/matplotlib in P1 — those are
confined to P4). No raw SQL anywhere (not applicable; no DB). No business logic in the CLI
entry beyond arg wiring.

| Path | New/Edit | Responsibility |
|------|----------|----------------|
| `code/config.py` | New | Single source of truth. Reads from `os.environ` + `argparse` only: `BACKEND` (name or `None`→least-busy Heron r2), IBM account env (reused saved account — no secrets stored), `N_MAX` (depth range), `SHOTS`, `SEEDS` (list), `HW_DEPTHS` (subset), `SHOTS_PER_JOB`. Mirrors `qtree.py:276-290` arg/env handling. Exposes a typed `Config` dataclass + `load(args)`. (AC-1.2) |
| `code/walk_spec.py` | New | `WALK_SPEC` dict (§5) + `decode_counts(...)`. Analogue of `genome.py`. Python source of truth for the decode contract. (AC-1.3) |
| `code/layout.py` | New | Local copy of `best_chain` adapted from `QuantumLife/code/layout.py` (see OQ-1.2 for why it is copied, not imported). Signature and live-calibration warning preserved verbatim; docstring points the length-`n` ceiling at OQ-2's `N`. |
| `code/pipeline.py` | New | Reuse wiring + IO. Does `sys.path.insert(0, _CALIB_CODE)` then `from pipeline_common import connect, run_sampler, timestamp` (mirror `qtree.py:81-86`); `_CALIB_CODE` resolved per OQ-1.1. Re-exports those three symbols. Owns the frozen `run.json`/`summary.json` writers (`write_run`, `write_summary`) and the schema constants (§7). Builds the `ClassicalRegister(n, "c")` per §3.3. (AC-1.4) |
| `code/galton.py` | New | CLI entry (arg wiring only). Builds a **minimal 2-step one-hot reference walk** (placeholder — P2 owns the general `build_walk`), runs it on `AerSimulator` statevector under `--sim`/ideal, decodes via `walk_spec.decode_counts`, writes one `run.json` via `pipeline.write_run`. Argparse mirrors `qtree.py`: `--steps` (default 2), `--shots`, `--backend`, `--sim`, `--seed`, `--arm`. (AC-1.1) |
| `code/scaffold_check.py` | New | Offline correctness gate (no network, no QPU). Runs the `--sim` 2-step path in-process and asserts: `run.json` exists with every required key (§7); `walk_spec` embedded verbatim equals `WALK_SPEC`; `position_histogram` sums to 1±1e-6; register named `"c"`; `qubit_list` present. Exits non-zero on any breach. This is the AC-1.1 + AC-1.3 verification mechanism. |
| `code/SCHEMA.md` | New | Documents the frozen `run.json` / `summary.json` schema and `WALK_SPEC` for P2/P3/P5 (satisfies AC-1.3 "documented"). |
| `runs/` | New (runtime) | Per-`(arm, depth)` `run.json` output dir. Mirrors `QuantumLife/runs/`. Created via `os.makedirs(..., exist_ok=True)`. |
| `research_runs/` | New (runtime) | Per-sweep `summary.json` output dir. Mirrors `QuantumLife/research_runs/`. |

## 7. Frozen schema (mirrors `QuantumLife` `meta`+array shape)

**`run.json`** — one per `(arm, steps)` run. Mirrors `qtree.py:373-392` (`meta` block) and the
`QuantumLife/runs/*_run.json` layout. Frozen keys:

```jsonc
{
  "meta": {
    "project": "QuantumGaltonBoard",
    "arm": "ideal",              // ideal | noisy | hw
    "backend": "aer_simulator",  // or Heron r2 name for hw/noisy
    "sim": true,                 // args.sim
    "timestamp": "20260806-…",   // pipeline_common.timestamp()
    "steps": 2,                  // walk depth n
    "n_position_qubits": 3,      // n+1 under one-hot (OQ-1)
    "n_qubits": 4,               // n+2 (position + coin)
    "qubit_list": null,          // hw: best_chain result; sim: null
    "coin": "hadamard",          // OQ-4
    "shots": 4096,
    "seed": 100,
    "walk_spec": { /* WALK_SPEC embedded verbatim */ },
    "chain_stats": null,         // hw: best_chain stats; else null
    "calibration": null          // hw: snapshot; else null (P2 fills for hw)
  },
  "counts": { "0100": 2048, "0001": 2048 },      // raw measured bitstrings
  "position_histogram": { "-2": 0.5, "0": 0.0, "2": 0.5 },  // decoded, normalised
  "quantum_seconds": 0.0,        // 0 for sim; run_sampler total for hw
  "jobs_meta": null              // hw: run_sampler jobs_meta; else null
}
```

**`summary.json`** — one per sweep. Mirrors `QuantumLife/research_runs/*_summary.json`
(`{meta, per_generation}` → here `{meta, per_depth}`). P1 defines the schema + `write_summary`;
P4 populates it across the sweep.

```jsonc
{
  "meta": { "project": "QuantumGaltonBoard", "arm": "…", "backend": "…",
            "depths": [2, 4, …], "shots": 4096, "seeds": [100,101,102],
            "walk_spec": { /* verbatim */ }, "timestamp": "…" },
  "per_depth": [ { "steps": 2, "run_files": ["…_run.json"],
                   "position_histogram": { }, "metrics": { } } ]  // metrics filled by P4
}
```

## 8. Manual verification (no automated tests)

1. Root-free smoke (AC-1.1): `python code/galton.py --sim --steps 2 --shots 4096 --seed 100`
   → prints the output path; `runs/…_run.json` exists with the §7 keys.
2. Offline gate (AC-1.1/AC-1.3): `python code/scaffold_check.py` exits 0; asserts embedded
   `walk_spec == WALK_SPEC`, histogram normalised, register `"c"`, required keys present.
3. Env single-source (AC-1.2): run with `SHOTS=1024 BACKEND=ibm_… python code/galton.py --sim
   --steps 2` and confirm the values land in `run.json.meta` — nothing hardcoded overrides them.
4. Reuse wiring (AC-1.4): `python -c "import sys; sys.path.insert(0,'code'); import pipeline;
   print(pipeline.connect, pipeline.run_sampler, pipeline.timestamp)"` resolves the three
   symbols from `pipeline_common` (import succeeds → path in OQ-1.1 is correct). No live
   connection is made.
5. No network on the `--sim` path: steps 1–3 run with networking unavailable.

## 9. Conventions & guardrails

- `from __future__ import annotations`; full type hints; PSR-12 has no Python analogue — follow
  the twin's style (`QuantumLife/code/*`): stdlib + qiskit(+aer) only in core, snake_case,
  module docstrings mirroring `genome.py`/`layout.py`.
- Re-pick the chain from **live** calibration before every hardware run (P2 concern; `layout.py`
  docstring preserved). Never hardcode a stale qubit list.
- `WALK_SPEC` is frozen at P1. Any later change is an epic-level amendment, not a plan edit,
  because P5's JS mirror is kept in sync by hand.
- Output discipline: one `run.json` per `(arm, depth)` in `runs/`; one `summary.json` per sweep
  in `research_runs/` — exactly the `QuantumLife` split.

## 10. Dependencies & ordering

- **Depends on:** none (foundation). **Gates:** P2, P3, P4, P5.
- P5's Tier-A pure-JS ideal shell can start once `WALK_SPEC` (this plan) is frozen, before P4
  data exists (epic §7).

## 11. Open questions — RESOLVED (2026-08-06, developer: "accept all defaults and approve")

All resolved by accepting the proposed default. Two arise from disk facts that contradict the
epic's Appendix A; the epic (§3.3, Appendix A.1) still needs the same correction — noted for a
follow-up epic amendment, not blocking P1 (P1 owns its own import path via OQ-1.1).

- **OQ-1.1 — Calibration code import path (epic §3.3 / Appendix A.1 is stale).** The epic says
  import from `../CalibrationGuidedHighYieldQRNG/code/`, and QuantumLife resolves
  `_CALIB_CODE = ../../CalibrationGuidedHighYieldQRNG/code` (`qtree.py:82-84`). **That directory
  does not exist on disk today** — the calibration study was reorganised into `new/` (empty) and
  `old/`, and `pipeline_common.py` now lives at `CalibrationGuidedHighYieldQRNG/old/code/`.
  **[proposal]** Set `_CALIB_CODE` to `../../CalibrationGuidedHighYieldQRNG/old/code`, resolved
  with a fallback that tries `.../code` then `.../old/code` and raises a clear error naming both
  if neither has `pipeline_common.py`. Also flag to the epic author that Appendix A.1 and §3.3
  need updating (and that QuantumLife's own import is currently broken against this layout).
- **OQ-1.2 — `layout.best_chain` origin (epic §3.3 / Appendix A is wrong).** The epic states
  `from layout import best_chain` is imported "from `../CalibrationGuidedHighYieldQRNG/code/`".
  On disk, `layout.py` is **QuantumLife-local** (`QuantumLife/code/layout.py`); there is no
  `layout.py` anywhere under `CalibrationGuidedHighYieldQRNG/`. **[proposal]** Ship a local
  `QuantumGaltonBoard/code/layout.py` copied/adapted from QuantumLife (reuse-not-copy applies to
  the *submission pipeline* `pipeline_common`; `layout` is small per-study tooling each sibling
  owns). Note the correction to the epic.
- **OQ-1.3 — Does `--sim` mean the ideal AerSimulator arm, or a separate non-circuit classical
  surrogate?** In QuantumLife `--sim` is a classical surrogate with no circuit; epic §3.6 reuses
  that phrasing, but for the Galton board the ideal arm is already a real circuit on
  `AerSimulator` (root-free, QPU-free). **[proposal]** `--sim` == the ideal `AerSimulator`
  (statevector) arm; there is no separate classical surrogate arm. The classical **binomial**
  is an analytic *reference* (owned by P3), not an execution arm. This satisfies AC-1.1's
  "root-free ideal/`--sim` run" with one code path.
- **OQ-1.4 — Offline default for `N_MAX` when no live backend (OQ-2 derives `N` from live
  `best_chain`).** P1's root-free path cannot query a backend. **[proposal]** `config.N_MAX`
  carries a static default (e.g. `20`), overridable by env/arg; the `hw`/`noisy` arms in P2
  override it from the live `best_chain` length. P1 only needs it to size the smoke run.
- **OQ-1.5 — Coin/position qubit ordering & bitstring endianness in `WALK_SPEC`.** The exact
  MSB/LSB convention and coin-qubit index must be fixed now because P5's JS mirror depends on it.
  **[proposal]** coin qubit = index 0, position qubits = indices `1..n+1`, `bitstring_order =
  "little"` matching `run_sampler`'s `get_bitstrings()`; frozen in `walk_spec.py` and `SCHEMA.md`.

---

## 13. Post-implementation (2026-08-10)

**Built.** The full `code/` scaffold: `walk_spec.py` (frozen `WALK_SPEC` + `decode_counts`),
`config.py` (env/arg single-source `Config`+`load`), `layout.py` (`best_chain` adapted verbatim
from the twin), `pipeline.py` (reuse wiring + `run.json`/`summary.json` writers + `"c"` register
helper + schema constants), `galton.py` (CLI + minimal 2-step one-hot reference walk on
`Statevector`), `scaffold_check.py` (offline gate), `SCHEMA.md` (frozen-schema doc). All four ACs
verified against the running code; the §8 manual checks (smoke, gate exit 0, env single-source,
reuse-wiring resolution) all pass. `runs/` and `research_runs/` are created at runtime.

**Deviations / follow-ups for the developer:**

- **`Statevector`, not `AerSimulator`, for the P1 ideal arm.** `qiskit-aer` was not installed;
  rather than add it, the ideal arm uses the built-in `qiskit.quantum_info.Statevector` (exact,
  local, root-free — same result for the tiny reference circuit). `meta.backend` records
  `"statevector"` (plan §7's example said `"aer_simulator"`). Both are local ideal simulators;
  this keeps P1 dependency-light like QuantumLife (which carries no aer). **P2's noisy arm will
  need `qiskit-aer`** (`AerSimulator.from_backend`) — install it then. Rationale matches epic
  OQ-1.3. Noted in `SCHEMA.md` and `galton.py`.
- **OQ-1.1 confirmed on disk.** QuantumLife's own `qtree.py` resolves the now-missing
  `.../CalibrationGuidedHighYieldQRNG/code`; `pipeline.py` here uses the two-candidate fallback
  and resolved `.../old/code`. The epic §3.3 / Appendix A.1 still need the same correction
  (epic-level amendment, not a plan edit) — flagged as agreed in OQ-1.1.
- **`layout._pull` copied verbatim** from `QuantumLife/code/layout.py` (uses
  `target.operation_names`, `error`-or-`0.0` fallbacks). `best_chain` is unexercised in P1 (hw is
  P2); its live-calibration path is validated only when P2 runs against a backend.
- **Branch:** work done on `main` (this study has no ticket/branch convention — the Galton epic
  was committed straight to `main`; the `feature-<N>` convention is from the Symfony
  `/implement-feature` template, not this Python study).

---

*Plan complete. Implemented and manually verified per §8; no automated tests (project directive).*
