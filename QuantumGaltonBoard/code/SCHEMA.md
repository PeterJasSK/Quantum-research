# Frozen schema — Quantum Galton Board (P1)

Frozen at P1 and consumed unchanged by P2 (`build_walk`), P3 (metrics), P4
(sweep/figures) and P5 (JS viewer). Any change is an **epic-level amendment**
(P5's JS `WALK_SPEC` mirror is kept in sync by hand), not a plan edit.

## `WALK_SPEC` — the decode contract

Module-level `dict` in `walk_spec.py`, the DTQW analogue of QuantumLife's
`genome.py:GENOME_SPEC`. Embedded **verbatim** into every `run.json` under
`meta.walk_spec` so the P5 JS decoder reproduces Python exactly.

| Key | Value | Meaning |
|-----|-------|---------|
| `encoding` | `"one_hot_line"` | one qubit per reachable bin (OQ-1) |
| `coin` | `"hadamard"` | fixed coin, v1 (OQ-4) |
| `coin_qubit` | `0` | coin qubit index; LSB / rightmost bitstring char |
| `position_qubits` | `"1..n+1"` | one-hot bins; qubit `j` set ⇒ amplitude at bin `j` |
| `bin_to_position` | `"pos = 2*bin - n"` | bins `0..n` ⇒ positions `-n..+n` (step 2) |
| `bitstring_order` | `"little"` | qubit `i` ⇒ character `bits[-(i+1)]` (matches `run_sampler`) |
| `version` | `1` | spec version |

An `n`-step walk uses `n+1` position qubits + 1 coin = **`n+2` qubits**. Decode
is `decode_counts(counts, steps, spec=WALK_SPEC) -> {position: probability}`;
Python is the source of truth, the JS viewer mirrors it (parity gate, epic §3.6).

## `run.json` — one per `(arm, steps)` run

Written by `pipeline.write_run`. Filename:
`<arm>_<backend>_steps<n>_seed<seed>_<ts>_run.json` in `runs/` (`ts` =
`pipeline_common.timestamp()`, `%Y%m%d-%H%M%S`).

Top-level keys (`pipeline.REQUIRED_RUN_KEYS`):

```jsonc
{
  "meta": { /* see below */ },
  "counts": { "0010": 2048, "1001": 2048 },   // raw measured bitstrings (little-endian)
  "position_histogram": { "-2": 0.5, "2": 0.5 }, // decoded, normalised; keys stringified ints
  "quantum_seconds": 0.0,       // 0 for sim; run_sampler total for hw
  "jobs_meta": null             // hw: run_sampler jobs_meta; else null
}
```

`meta` keys (`pipeline.REQUIRED_META_KEYS`):

```jsonc
{
  "project": "QuantumGaltonBoard",
  "arm": "ideal",              // ideal | noisy | hw
  "backend": "statevector",    // "statevector" for the P1 ideal arm; Heron r2 name for hw/noisy
  "sim": true,                 // args.sim
  "timestamp": "20260810-…",
  "steps": 2,                  // walk depth n
  "n_position_qubits": 3,      // n+1 under one-hot (OQ-1)
  "n_qubits": 4,               // n+2 (position + coin)
  "qubit_list": null,          // hw: best_chain result; sim: null
  "coin": "hadamard",          // OQ-4
  "shots": 4096,
  "seed": 100,
  "walk_spec": { /* WALK_SPEC embedded verbatim */ },
  "chain_stats": null,         // hw: best_chain stats; else null
  "calibration": null,         // hw: snapshot; else null (P2 fills for hw)
  "environment": { /* non-secret env hints from config.py */ }
}
```

> **Note (deviation from the plan's §7 example).** The P1 ideal arm records
> `backend: "statevector"` (built-in `qiskit.quantum_info.Statevector`), not
> `"aer_simulator"`. Both are local, exact, root-free ideal simulators; the
> switch keeps P1 dependency-light like the twin (see `galton.py` docstring and
> the epic OQ-1.3 rationale). P2's noisy arm introduces `qiskit-aer`.

## `summary.json` — one per sweep

Written by `pipeline.write_summary`. Filename:
`<arm>_<backend>_<ts>_summary.json` in `research_runs/` (same stem as the per-run
files minus the `seed<N>` segment). P1 defines the schema + writer; **P4**
populates `per_depth` across the sweep.

```jsonc
{
  "meta": { "project": "QuantumGaltonBoard", "arm": "…", "backend": "…",
            "depths": [2, 4, …], "shots": 4096, "seeds": [100,101,102],
            "walk_spec": { /* verbatim */ }, "timestamp": "…" },
  "per_depth": [ { "steps": 2, "run_files": ["…_run.json"],
                   "position_histogram": { }, "metrics": { } } ]  // metrics filled by P4
}
```

## P2 arms — how the frozen keys are filled (no new keys)

P2 fills P1's existing `run.json`/`meta` keys with real values across three arms
(`arms.run_arm`); it adds and renames nothing (the schema is frozen, epic §3.6).

| Arm | `meta.backend` | `sim` | `qubit_list` / `chain_stats` / `calibration` | `quantum_seconds` / `jobs_meta` |
|-----|----------------|-------|-----------------------------------------------|----------------------------------|
| `ideal` | `"statevector"` | `true` | `null` | `0.0` / `null` |
| `noisy` | Heron r2 name | `false` | `null` | `0.0` / `null` |
| `hw` | Heron r2 name | `false` | filled (see below) | `run_sampler` total / `run_sampler` jobs_meta |

- **`noisy`** builds its noise model from the *same* backend as `hw`
  (`AerSimulator.from_backend`, OQ-5), so `meta.backend` is the Heron r2 name,
  not `"aer_simulator"`. Deterministic via `seed_simulator=seed`.
- **`hw`** fills `qubit_list` (the live `layout.best_chain` chain), `chain_stats`
  (best_chain's raw stats dict), and `calibration` — the OQ-2.4 snapshot built
  from readable data (the `calibration_snapshot` module does not exist):

  ```jsonc
  "calibration": {
    "backend": "<heron r2 name>", "timestamp": "…",
    "chain_twoq_err_mean": 0.0, "chain_twoq_err_max": 0.0,
    "readout_max": 0.0, "sx_max": 0.0
  }
  ```

- **Decode / endianness (OQ-2.2).** `run_sampler` returns per-shot
  `get_bitstrings()` strings (MSB-first); `arms.run_arm` aggregates them with
  `collections.Counter` and feeds `decode_counts` **without** reversal — qubit
  `i` is `bits[-(i+1)]`, which `get_bitstrings`' MSB-first order already
  satisfies. Never reverse and never edit the frozen `walk_spec.py`; if a live hw
  histogram is ever mirrored, flip in `run_arm`'s aggregation only. Pinned by the
  round-trip assertion in `walk_check.py`.

## Dependencies

Core (`config.py`, `walk.py`, `walk_spec.py`, `pipeline.py`, `layout.py`,
`galton.py` ideal arm, `walk_check.py`): stdlib + `qiskit` + `numpy` only —
the offline gate and the root-free ideal arm run aer-free (OQ-2.5).
The **`noisy`** arm adds **`qiskit-aer`** (OQ-2.1), imported lazily inside
`arms._run_noisy` so its absence never blocks the ideal/offline paths. See
`code/requirements.txt`. Not vendored.
