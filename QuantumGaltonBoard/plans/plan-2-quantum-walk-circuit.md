# Plan P2 — Quantum-walk circuit + three-arm runner

**Epic:** `plans/epic-quantum-galton-board.md` (Status: Draft — OQs resolved 2026-08-06)
**Plan ID:** P2 (`[MUST]`, depends on P1; gates P3, P4)
**Slug:** quantum-walk-circuit
**Author:** Claude (Opus)
**Date:** 2026-08-10
**Status:** Complete (2026-08-10) — implemented + manually verified; offline gate passes

> **No automated tests (project directive, epic §3.6).** Verification is offline
> correctness gates (`walk_check.py`), the root-free `--sim`/ideal path, and — for the
> live arms — a documented manual hardware run. This plan lists no test files, no test
> suites, and no AC→test mapping. "How to verify" everywhere means the offline gate + a
> manual arm run.

---

## 1. Context

P2 is the physics ticket. P1 froze the contracts (`WALK_SPEC`, `run.json`/`summary.json`
schema, the reuse-not-copy `pipeline_common`/`layout` wiring, the `"c"` register, the
root-free ideal smoke path). P2 replaces P1's **placeholder** 2-step reference circuit
(`code/galton.py:35` `build_reference_walk`) with the real discrete-time quantum walk and
adds the three execution arms.

P2 delivers two frozen interfaces (epic §4):

- `build_walk(steps, coin, encoding)` — one coin+shift DTQW builder under the OQ-1 one-hot
  line encoding, parameterised on step count. Consumed by P3 (metrics), P4 (sweep).
- `run_arm(kind, steps)` — one dispatch over `ideal | noisy | hw`; only the execution
  backend varies (epic §3.2). Each arm emits one frozen `run.json` via the existing
  `pipeline.write_run` (P1, `code/pipeline.py:83`). Consumed by P4 (sweep).

**Structural twin:** `QuantumLife/code/qtree.py`. Its hardware path is the exact precedent:
`run_hw` (`qtree.py:264-271`) transpiles with `generate_preset_pass_manager(optimization_level=3,
backend=backend, initial_layout=qubit_list)` then hands the ISA circuit to
`run_sampler`; `best_chain` is called on live calibration in `main()` (`qtree.py:317-320`);
the `--sim` arm skips `connect()` entirely (`qtree.py:315-316, 343-344`). P2 mirrors this
arm split, extended from two arms to three.

**Reuse target (verified on disk 2026-08-10):**
- `pipeline_common.run_sampler(backend, isa, shots, shots_per_job=SHOTS_PER_JOB) ->
  tuple[list[str], list[dict], float]` — chunked SamplerV2 loop; **does not transpile**
  (expects an already-ISA circuit); reads `res[0].data.c.get_bitstrings()` (creg must be
  `"c"`); returns `(per-shot bitstrings, jobs_meta, total_quantum_seconds)`
  (`old/code/pipeline_common.py:59-85`).
- `connect(name)` — live `QiskitRuntimeService`; explicit backend or least-busy Heron r2
  (`pipeline_common.py:29-35`). Re-exported through `code/pipeline.py:54`.
- `best_chain(backend, n)` — local (`code/layout.py:54`); returns `(qubit_list, stats)`,
  raises if no length-`n` SWAP-free chain (that ceiling sets `N`, OQ-2).

**Environment gaps this plan must close (from the P2 survey):**
- `qiskit-aer` is **not installed** and no `AerSimulator` / `NoiseModel` / `from_backend`
  code exists anywhere in the sibling studies. The `noisy` arm cannot exist until aer is
  installed — see AC-2.4 and OQ-2.1.
- `calibration_snapshot.py` does **not exist**; QuantumLife's `qtree.py:304-308` import of
  it always fails, so its `run.json` `calibration` is always `{"_error": …}`. P2 must
  build the `hw` calibration snapshot from data it can actually read
  (`best_chain` stats + `backend.target`), not from that missing module — see OQ-2.4.
- `run_sampler` returns **per-shot bitstrings** (a flat `list[str]`), not a counts dict,
  and qtree **reverses** each string (`qtree.py:270`, `s[::-1]`) for its own gene ordering.
  `walk_spec.decode_counts` (`code/walk_spec.py:39`) expects a **counts dict** in the
  little-endian convention it documents. P2 must aggregate the list into counts and get the
  endianness right or the whole hw histogram is scrambled — see OQ-2.2.

## 2. Acceptance criteria (from epic §9 P2 → source §Method)

Copied verbatim from the epic brief; IDs preserved.

**Coverage (verified 2026-08-10):**

| AC | Covered by | Verified |
|----|------------|----------|
| AC-2.1 | `code/arms.py:164` (build_walk once) + `code/arms.py:152` (dispatch) + `code/walk_check.py:97` (`check_dispatch`) | `walk_check.py` PASS AC-2.1 |
| AC-2.2 | `code/walk.py:build_walk` + `code/walk_check.py:107` (`check_physics` vs analytic recursion) | `walk_check.py` PASS AC-2.2, TV<1e-6 steps 2..8, twin horns |
| AC-2.3 | `code/arms.py:136` (live `best_chain`) + `code/arms.py:137-140` (transpile opt3 `initial_layout` → `run_sampler`) + `code/galton.py:33` (`_run_hw_matrix` loops `hw_depths×seeds`) | structural (hw run consumes QPU — manual) |
| AC-2.4 | `code/arms.py:120` (`AerSimulator.from_backend(connect(cfg.backend))`) | aer plumbing validated locally; live `from_backend` needs IBM account |
| AC-2.5 | `code/arms.py:61` (walk_spec+seed in meta) + `code/arms.py:145-148` (hw `qubit_list`/`chain_stats`/`calibration`) + `code/arms.py:107` (`sv.seed`) / `code/arms.py:122` (`seed_simulator`) | ideal run.json carries all REQUIRED_META_KEYS |

- **AC-2.1** One circuit builder drives all three arms; only the backend varies (epic §3.2).
  *Approach:* `run_arm(kind, steps)` calls `build_walk(steps, ...)` once and dispatches only
  on execution (Statevector / AerSimulator noise model / live `run_sampler`). No arm has
  bespoke circuit logic. Verified by `walk_check.py` asserting all three arms transpile/run
  the identical `build_walk` output.
- **AC-2.2** The `ideal` arm reproduces the analytic Hadamard-walk twin-horn distribution to
  tolerance (offline check, epic §3.6).
  *Approach:* `walk_check.py` computes the ideal position histogram two independent ways —
  (a) `build_walk` + `Statevector`, and (b) a direct numpy amplitude recursion of the
  Hadamard walk — and asserts total-variation distance `< TOL` (default `1e-6`) across
  `steps = 2..8`, and that the distribution is bimodal (twin horns: the two extreme-ish
  peaks exceed the central bin) for `steps >= 3`.
- **AC-2.3** The `hw` arm requests a SWAP-free low-error chain from `layout.best_chain` on
  **live** calibration before submitting, and runs at the OQ-3 depth subset with seeded
  repeats.
  *Approach:* `run_arm("hw", steps)` calls `connect()` then `best_chain(backend, n_qubits)`
  per invocation (never a hardcoded list), transpiles with `initial_layout=qubit_list`,
  submits via `run_sampler`. The driver loops the OQ-3 depths (`config.hw_depths`) × the
  seeded repeats (`config.seeds`), one `run.json` per `(depth, seed)`.
- **AC-2.4** The `noisy` arm builds its model from the same backend as `hw` so the two are
  comparable (OQ-5).
  *Approach:* `run_arm("noisy", steps)` builds `AerSimulator.from_backend(connect(cfg.backend))`
  (or a locally cached noise model from the same backend name) so the noise model and the
  `hw` arm share one Heron r2 target.
- **AC-2.5** Every run is reproducible from its `run.json` (spec + backend + calibration
  snapshot + seed).
  *Approach:* each arm writes the frozen meta (P1 `REQUIRED_META_KEYS`) with a real `seed`,
  `qubit_list` (hw), `chain_stats` (hw), and `calibration` (hw, per OQ-2.4). Ideal/noisy
  seed their simulators deterministically (Statevector `.seed()`, Aer `seed_simulator`).

## 3. Out of scope (deferred, not omitted)

- The four metrics + the ballistic→diffusive knee extractor → **P3**. P2 emits raw
  `position_histogram`s only; it computes **no** variance exponent, TV/Hellinger, horn
  contrast, or entropy beyond the minimal bimodality assertion inside `walk_check.py`
  (that assertion is a correctness gate, not a delivered metric).
- The depth×arm **sweep**, `summary.json` aggregation, figures, replay-JSON export → **P4**.
  P2 ships `run_arm` and a thin driver that can run one arm at one depth (and, for `hw`,
  loop the OQ-3 depths × seeds because AC-2.3 requires it); it does **not** aggregate a
  cross-arm sweep into `summary.json`.
- The analytic reference distributions as a **shared, importable module** → **P3** owns them
  (epic §4). P2's `walk_check.py` carries a *local, self-contained* Hadamard-walk recursion
  purely to satisfy AC-2.2 offline; P3 may later replace/absorb it.
- The web viewer + JS `WALK_SPEC` mirror + parity gate → **P5**.
- No QRNG / QEaaS arm or provenance receipt (epic §3.7).

## 4. Decisions inherited from the epic (do not re-litigate)

- **Encoding (OQ-1 LOCKED):** one-hot line. An `n`-step walk uses `n+1` position qubits +
  1 coin = `n+2` qubits. `build_walk` targets exactly this register; the coin qubit is index
  0, position bins 0..n are indices 1..n+1 (`walk_spec.py:11-14`, `SCHEMA.md`).
- **Three arms, one circuit (§3.2 LOCKED):** only the backend varies. `run_arm` dispatches
  on execution only.
- **Fixed Hadamard coin (OQ-4 LOCKED):** `build_walk`'s `coin` parameter accepts only
  `"hadamard"` in v1; any other value raises `NotImplementedError` (biased/DFT coins are P6
  future work). `WALK_SPEC.coin == "hadamard"`.
- **Reuse the pipeline, do not copy (§3.3 LOCKED):** import `run_sampler`/`connect` from
  `pipeline.py` (already wired, P1); never reimplement submission. Transpile in the caller
  (as `qtree.run_hw` does) because `run_sampler` does not.
- **Noisy from the same backend as hw (OQ-5 LOCKED):** `AerSimulator.from_backend` off the
  `config.backend` Heron r2.
- **hw depth subset + repeats (OQ-3 LOCKED):** a low anchor, 2–3 depths bracketing the
  predicted knee, one past it, ≥3 seeded repeats. Read from `config.hw_depths` /
  `config.seeds` (P1 defaults `[2,6,10,14]` / `[100,101,102]`, `config.py:28-29`); the
  concrete final subset is chosen in **P4** (OQ-3) — P2 only honours whatever the config
  carries.
- **`--sim`/ideal is root-free (§3.5/§3.6, OQ-1.3):** the ideal arm runs locally with no
  IBM account and no QPU cost.

## 5. The walk circuit — `build_walk` (the frozen builder)

`build_walk(steps: int, coin: str = "hadamard", encoding: str = "one_hot_line") ->
QuantumCircuit` builds an `n`-step discrete-time quantum walk in the one-hot line encoding,
returning a circuit on `n+2` qubits (`QuantumRegister(n+2, "q")`) with a `ClassicalRegister`
named `"c"` (via `pipeline.classical_register`, `code/pipeline.py:77`) and a final
`measure(qr, cr)`.

**Register:** coin = qubit 0; position bins 0..n = qubits 1..n+1 (one-hot: exactly one
position qubit carries the walker's excitation per basis component). This is the contract
`walk_spec.decode_counts` already decodes (`code/walk_spec.py:56-62`) and must not drift.

**Per-step structure (repeat `steps` times), one-hot line DTQW:**
1. **Coin:** `H` on the coin qubit (fixed Hadamard, OQ-4).
2. **Shift:** a coin-controlled one-hot *ladder shift* that moves the excitation one bin
   toward `+` when the coin is `|1>` and one bin toward `-` when the coin is `|0>`,
   implemented as a sequence of coin-controlled swaps between adjacent position qubits so
   the two directions' amplitudes **interfere** across steps (the twin-horn signature).
3. The walker is initialised localised at the centre bin before step 1 (`X` on the centre
   position qubit); the `n+1`-bin register holds exactly the `n+1` reachable end positions
   `-n..+n` (step 2), matching `bin_to_position` (`walk_spec.py:34`).

The implementer must produce a circuit whose **ideal** position histogram equals the
analytic Hadamard walk to `TOL` (AC-2.2). The exact swap-ladder wiring (bin ordering, edge
handling at the two ends of the one-hot register, and whether an ancilla-free ladder or a
controlled-increment/decrement is used) is an implementation detail **pinned by AC-2.2** —
if the shallowest correct construction cannot be expressed inside `n+1` one-hot bins without
losing amplitude at the boundaries, that is an encoding-adequacy finding (OQ-2.3) to raise
as an epic amendment, not to paper over. `build_walk` must not silently truncate probability.

**No coin re-use hazard:** the single coin qubit is re-Hadamard'd each step (standard DTQW);
it is measured into its `"c"` slot but ignored by `decode_counts` (coin qubit index 0,
`walk_spec.py:59` skips it). Confirm the coin measurement does not corrupt the one-hot
position decode.

## 6. The three-arm runner — `run_arm`

`run_arm(kind: str, steps: int, cfg: config.Config, seed: int) -> tuple[str, dict]` builds
`build_walk(steps)` once (AC-2.1) and dispatches on `kind`:

| kind | Backend | Execution | Cost | Writes |
|------|---------|-----------|------|--------|
| `ideal` | `qiskit.quantum_info.Statevector` (built-in, no aer) | exact statevector of `build_walk`, `.seed(seed)`, `sample_counts(shots)` | root-free, QPU-free | `run.json`, `backend="statevector"` |
| `noisy` | `AerSimulator.from_backend(connect(cfg.backend))` | run `build_walk` under the device noise model, `seed_simulator=seed` | local, no QPU | `run.json`, `backend=<heron r2 name>` |
| `hw` | live Heron r2 via `connect(cfg.backend)` | `best_chain` → transpile (`generate_preset_pass_manager`, opt 3, `initial_layout`) → `run_sampler` | **QPU** | `run.json`, `backend=<heron r2 name>` |

Shared, per arm:
- Aggregate raw measurement output into a `counts` dict, then `position_histogram =
  decode_counts(counts, steps)` (P1 source of truth). For `hw`, `run_sampler` returns a
  flat per-shot `list[str]`; aggregate with `collections.Counter` and feed to
  `decode_counts` **without** qtree's `s[::-1]` reversal (see OQ-2.2 — `decode_counts`
  already reads little-endian).
- Fill the frozen meta (`pipeline.REQUIRED_META_KEYS`, `code/pipeline.py:64`): `arm`,
  `backend`, `sim` (`True` only for `ideal`), `timestamp()`, `steps`, `n_position_qubits`
  (`steps+1`), `n_qubits` (`steps+2`), `coin`, `shots`, `seed`, `walk_spec` (embedded
  verbatim), `environment`, and — for `hw` — `qubit_list` (from `best_chain`), `chain_stats`
  (its stats dict), `calibration` (per OQ-2.4). For `ideal`/`noisy`, `qubit_list`,
  `chain_stats`, `calibration` stay `None`.
- Write via `pipeline.write_run(...)` (P1). `quantum_seconds` = 0.0 for `ideal`/`noisy`,
  the `run_sampler` total for `hw`; `jobs_meta` = `None` except `hw`.

**Driver / CLI (`galton.py`):** extend the existing argparse so `--arm {ideal,noisy,hw}`
and `--steps` drive `run_arm`. For `--arm hw` (AC-2.3) the driver loops `cfg.hw_depths ×
cfg.seeds`, submitting one run per `(depth, seed)` and re-picking `best_chain` on live
calibration each submission (§3.3). For `ideal`/`noisy` a single `(steps, seed)` run is the
default; a `--sweep` convenience flag may loop `2..N` but the full sweep matrix is **P4**.
The P1 guard that rejects non-ideal/non-sim arms (`code/galton.py:118-122`) is removed here.

## 7. File Plan

All paths under `QuantumGaltonBoard/`. `from __future__ import annotations`, full type
hints. Core stays stdlib + qiskit + qiskit-aer (aer new in P2, noisy arm only) — no
pandas/matplotlib (P4). No raw SQL (n/a). No business logic in the CLI beyond arg wiring.

| Path | New/Edit | Responsibility |
|------|----------|----------------|
| `code/walk.py` | **New** | `build_walk(steps, coin, encoding) -> QuantumCircuit` (§5) — the real one-hot coin+shift DTQW. Pure circuit construction; no execution, no IO. Imports `pipeline.classical_register` for the `"c"` register. Raises `NotImplementedError` for non-Hadamard coins / non-`one_hot_line` encodings (OQ-4/OQ-1). |
| `code/arms.py` | **New** | `run_arm(kind, steps, cfg, seed) -> (path, payload)` (§6) — the three-arm dispatch. Owns simulator/noise-model/hardware execution, counts aggregation, `decode_counts` call, meta assembly, `pipeline.write_run`. Imports `build_walk` (AC-2.1), `pipeline.{connect,run_sampler,timestamp,write_run,classical_register}`, `layout.best_chain`, and (noisy arm) `qiskit_aer.AerSimulator`. Owns `_calibration_snapshot(backend, chain, stats)` (OQ-2.4). |
| `code/galton.py` | **Edit** | Replace the placeholder `build_reference_walk`/`simulate_ideal`/`run_ideal` (`code/galton.py:35-102`) with calls into `walk.build_walk` + `arms.run_arm`. Keep the argparse; remove the P1 arm guard (`galton.py:118-122`); add the `--arm hw` OQ-3 depth×seed loop and the optional `--sweep`. CLI stays arg-wiring only. |
| `code/walk_check.py` | **New** | Offline correctness gate (no network, no QPU, no aer). AC-2.1: assert all three arms consume the identical `build_walk` output (dispatch-only difference; hw/noisy checked structurally, not executed). AC-2.2: `build_walk`+`Statevector` histogram vs a local numpy Hadamard-walk recursion, TV `< TOL` for `steps 2..8`, twin-horn bimodality for `steps >= 3`. Also asserts the hw-format endianness round-trips (OQ-2.2): a synthetic `get_bitstrings`-style string decodes to the expected bin. Exits non-zero on any breach. |
| `code/SCHEMA.md` | **Edit** | Add a short "P2 arms" note: `noisy`/`hw` `backend` is the Heron r2 name; `hw` fills `qubit_list`/`chain_stats`/`calibration`; document the `calibration` snapshot shape (OQ-2.4) and the no-reversal decode rule (OQ-2.2). No `run.json`/`WALK_SPEC` key changes (those are frozen). |
| `requirements` note | **Edit/New** | Record the new `qiskit-aer` dependency wherever the study records deps (a `code/requirements.txt` if one is added, else a note in `SCHEMA.md`/README). Do not vendor it. |

**No new frozen schema.** P2 fills P1's existing `run.json` keys with real values; it does
not add or rename keys (they are frozen, epic §3.6 / `SCHEMA.md`). The `calibration` snapshot
(OQ-2.4) populates the already-present `meta.calibration` slot.

## 8. Manual verification (no automated tests)

1. **Offline gate (AC-2.1/AC-2.2):** `python code/walk_check.py` exits 0 — ideal walk
   matches the analytic Hadamard recursion (TV `< 1e-6`) for `steps 2..8`, twin horns for
   `steps >= 3`, endianness round-trips.
2. **Ideal arm end-to-end (AC-2.1):** `python code/galton.py --sim --arm ideal --steps 6
   --shots 4096 --seed 100` writes `runs/ideal_statevector_steps6_seed100_*_run.json` whose
   `position_histogram` shows the twin-horn shape and sums to 1±1e-6.
3. **Noisy arm (AC-2.4)** *(needs `qiskit-aer` + a saved IBM account for
   `from_backend`)*: `python code/galton.py --arm noisy --steps 6 --backend <heron_r2>
   --seed 100` writes a `run.json` with `backend=<heron r2 name>`, `sim=false`, horns
   partially eroded vs the ideal arm at the same depth.
4. **hw arm (AC-2.3/AC-2.5)** *(consumes QPU — run deliberately)*: `python code/galton.py
   --arm hw --backend <heron_r2>` loops `config.hw_depths × config.seeds`, each run writing
   `qubit_list`, `chain_stats`, and a real `calibration` snapshot; `best_chain` is re-picked
   live per submission (confirm via distinct `qubit_list`s across calibration epochs).
5. **Reuse wiring unbroken (AC-2.3):** the hw path imports `run_sampler`/`connect` through
   `code/pipeline.py` (P1), transpiles in the caller, and never reimplements submission.
6. **No network on the ideal/offline paths:** steps 1–2 run with networking unavailable.

## 9. Conventions & guardrails

- `from __future__ import annotations`; full type hints; twin style (`QuantumLife/code/*`):
  snake_case, module docstrings mirroring `qtree.py`/`layout.py`.
- **Transpile in the caller.** `run_sampler` does not transpile; use
  `generate_preset_pass_manager(optimization_level=3, backend=backend,
  initial_layout=qubit_list)` then `pm.run(qc)` exactly as `qtree.run_hw`
  (`qtree.py:266-268`).
- **Re-pick the chain live** before every hw submission (`layout.best_chain`); never a
  hardcoded qubit list (`layout.py` docstring, epic §3.3 / Appendix A.3).
- **Do not mutate frozen artefacts.** `WALK_SPEC`, `decode_counts`, the `run.json` keys, and
  the `"c"` register are frozen at P1. If P2 needs `decode_counts` to handle a hw endianness
  detail, resolve it in `run_arm`'s aggregation (OQ-2.2), not by editing `walk_spec.py`.
- **`build_walk` must conserve probability** — no silent amplitude loss at the one-hot
  register boundaries (OQ-2.3); AC-2.2's TV gate catches this.
- One `run.json` per `(arm, depth, seed)` in `runs/` (P1 output discipline).

## 10. Dependencies & ordering

- **Depends on:** P1 (Complete). **Gates:** P3 (metrics consume `run_arm` histograms), P4
  (sweep drives `run_arm`).
- New runtime dependency: `qiskit-aer` (noisy arm only; ideal + `walk_check` stay aer-free
  so the offline gate runs in the minimal environment). See OQ-2.1.

## 11. Open questions — RESOLVED (2026-08-10, developer: "yes to all defaults")

All six accepted as proposed below.


- **OQ-2.1 — Install `qiskit-aer` for the noisy arm?** aer is absent and there is no
  existing noise-model code (survey §3). **[proposal]** Yes — add `qiskit-aer` as a P2
  dependency; the `noisy` arm uses `AerSimulator.from_backend`. Keep the `ideal` arm on the
  built-in `Statevector` (P1 choice) and keep `walk_check.py` aer-free so the offline gate
  and the root-free ideal arm still run in the minimal environment. Record the dep (§7).
- **OQ-2.2 — hw bitstring endianness: reverse or not?** `run_sampler` returns per-shot
  `get_bitstrings()` strings; qtree reverses them (`qtree.py:270`) for *its* gene ordering,
  but `decode_counts` already reads little-endian (`walk_spec.py:59`, `bits[-(i+1)]`).
  **[proposal]** Do **not** reverse — aggregate the raw `get_bitstrings()` list into counts
  and pass straight to `decode_counts`, since `measure(qr,cr)` maps qubit `i`→cbit `i` and
  `get_bitstrings` is MSB-first, making `bits[-(i+1)]` == qubit `i`. Pin it with the
  endianness round-trip assertion in `walk_check.py` (§7). If a live hw run shows a mirrored
  histogram, flip in `run_arm`'s aggregation only — never edit the frozen `walk_spec.py`.
- **OQ-2.3 — Is the one-hot `n+1`-bin register adequate for the full DTQW, or is a
  Galton-board peg construction needed?** A true line DTQW visits intermediate positions;
  the one-hot register holds only the `n+1` end bins. **[proposal]** Build `build_walk` as
  the incremental Galton-board coin+shift (one coin-controlled ladder-shift level per step)
  that yields the `n+1`-bin end distribution, and let AC-2.2's TV gate against the analytic
  Hadamard walk decide adequacy. If it cannot reproduce the twin horns without boundary
  amplitude loss, escalate as an epic amendment (encoding, OQ-1) rather than fudging the
  check tolerance.
- **OQ-2.4 — `hw` calibration snapshot source (the `calibration_snapshot` module is
  missing).** QuantumLife's snapshot import always fails (survey §4). **[proposal]** Build
  `meta.calibration` in `run_arm` from data we can actually read: the `best_chain` `stats`
  dict (`twoq_err_mean/max`, `readout_max`, `sx_max`, `dead_avoided`) plus `backend.name`
  and `timestamp()`. Store `chain_stats` = the raw `best_chain` stats and `calibration` =
  `{backend, timestamp, chain_twoq_err_mean, chain_twoq_err_max, readout_max, sx_max}`.
  Do not depend on the missing module; do not fabricate a fuller snapshot.
- **OQ-2.5 — Ideal simulator: `Statevector` or `AerSimulator`?** **[proposal]** Keep
  `Statevector` (P1 choice) — exact, root-free, aer-free — so the ideal arm and offline gate
  run without aer. Only the `noisy` arm pulls in aer (OQ-2.1). `meta.backend="statevector"`
  for ideal stays as P1 documented (`SCHEMA.md` note).
- **OQ-2.6 — Does P2 run the full ideal/noisy `2..N` sweep, or just single depths?**
  **[proposal]** P2 ships single-depth `run_arm` + the AC-2.3-required hw `hw_depths×seeds`
  loop; the ideal/noisy full `2..N` sweep matrix and its `summary.json` aggregation are
  **P4**. A `--sweep` convenience flag may loop depths for manual inspection but P2 does not
  aggregate or emit `summary.json`.

---

## 13. Post-implementation

**Built.** The real one-hot-line DTQW (`code/walk.py:build_walk`) replaces P1's
placeholder, plus the three-arm runner (`code/arms.py:run_arm`), the offline gate
(`code/walk_check.py`), the CLI rewire (`code/galton.py`), and the schema/dep docs.

**Physics.** `build_walk` uses the incremental Galton frame (OQ-2.3): coin `H` +
symmetric coin `(|0>+i|1>)/√2`, per step a top-down coin-controlled CSWAP ladder
(coin |1> → increment bin, coin |0> → stay). This is a shear of the textbook
Hadamard walk; the Statevector histogram equals an **independent** position-space
numpy recursion to **TV = 0** for steps 2..8 (well under the 1e-6 gate). No
boundary amplitude loss — at step k the walker never occupies a bin > k, so the
ladder never pushes off the top of the register. OQ-2.3 adequacy confirmed: the
`n+1`-bin one-hot register is sufficient; **no epic amendment needed**.

**Verified.** `python code/walk_check.py` → rc 0 (AC-2.1/2.2/OQ-2.2 all PASS).
`python code/galton.py --sim --arm ideal --steps 6 --shots 4096 --seed 100` writes
a twin-horn run.json (argmax pos ±4, centre 0.123 < peak, sums to 1.0) with every
`REQUIRED_META_KEYS` present. Noisy-arm plumbing (transpile → run → get_counts →
decode) validated with a local `AerSimulator`; `qiskit-aer 0.17.2` installed.

**Deferred / needs the developer.**
- **`noisy` + `hw` arms need a live IBM account.** `noisy` calls `connect()` for
  `AerSimulator.from_backend` (calibration only, no QPU); `hw` consumes QPU. Both
  are structurally verified but not executed here — run manually per §8 steps 3–4.
- **OQ-2.2 endianness** is pinned by a synthetic round-trip; a first live hw run
  should confirm the histogram is not mirrored (if it is, flip in
  `arms._run_hw` aggregation only — never edit `walk_spec.py`).
- **`qiskit-aer` newly installed** in the environment (recorded in
  `code/requirements.txt`); not vendored.

**Not done (correctly out of scope):** metrics/knee (P3), the sweep matrix +
`summary.json` (P4). `--sweep` is a manual convenience only.

---

*Plan implemented per epic §9 P2 and the P1 frozen contracts. No automated tests
(project directive) — verified via the offline gate + the root-free ideal arm.*
