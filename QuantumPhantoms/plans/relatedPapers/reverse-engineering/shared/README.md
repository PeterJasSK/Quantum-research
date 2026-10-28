# shared/: FROZEN foundation (contract version 1.0.0, frozen 2026-10-28)

> **FROZEN.** Letter sessions (A–H) **never edit anything in `shared/`**. If a contract or helper must change,
> write it under "Contract change requests" in your letter's README, adapt locally, and keep working.
> INT applies all requests in one place: amend the contract, then the producer, then the consumer.

Everything runs with `reverse-engineering/` as the working directory: `python -m shared.<module>`.
Python 3.13 (conda base); dependencies in [`requirements.txt`](requirements.txt) are already installed.
Letters import only `shared`, never another letter, and nothing from the MVP (`QuantumPhantoms/code/`).

| Path | What it is |
|---|---|
| [`contracts/`](contracts/README.md) | JSON Schemas for every hand-off file + [`VOLUMES.md`](contracts/VOLUMES.md) |
| [`stubs/`](stubs/README.md) | one valid example per contract: a synthetic tumor story, inputs until the upstream letter exists |
| `seedhash.py` | hashing, canonical JSON, code/git hash, seed derivation |
| `volumes.py` | NIfTI (SimpleITK, LPS) and deterministic NPZ I/O |
| `simbackend.py` | AerSimulator ideal / FakeMarrakesh noise factory (the only module importing qiskit) |
| `runrecord.py` | run directory + `run.json` writer (epic §3 Logging) |
| `validate.py` | contract validator CLI |
| `site/` | static site build (`build.py`, jinja2 templates, `style.css`) |
| `templates/` | `LETTER_README.template.md`, `DOSSIER.template.md` |

## `seedhash` (no qiskit)

- `sha256_bytes(data)`, `sha256_file(path)`: hex digests.
- `canonical_json(obj) -> bytes`: sorted keys, `(",", ":")` separators, UTF-8. Everything hashed or signed uses it.
- `hash_json(obj, exclude=())`: sha256 of `canonical_json` without the excluded top-level keys.
- `code_hash(paths)`: tree hash of `.py` files (paths relative to `reverse-engineering/`, so identical in every worktree).
- `git_state()`: `{commit, dirty}` with `dirty` scoped to `reverse-engineering/`, or `None`.
- `derive_seed(seed_hex, label) -> int`: uint64 = first 8 bytes of `sha256(seed || label)`.
- `rng(seed_hex, label) -> numpy.random.Generator` (PCG64): **the** way to seed every PRNG in E/F from
  C's `extracted_seed_hex`. Use a distinct label per consumer, e.g. `rng(seed, "E.growth")`, `rng(seed, "F.noise")`.

## `volumes`

- `read_volume(path) -> (array_zyx, meta)`: reorients to LPS identity; `meta` has `size_xyz`, `spacing_mm_xyz`,
  `origin_mm_lps`, `direction`.
- `write_volume(path, array_zyx, spacing_mm_xyz, origin_mm_lps)`: `.nii.gz`, LPS identity direction.
- `read_header(path)`, `same_grid(a, b)`, `check_same_grid(paths) -> [errors]`.
- `save_npz(path, **arrays)` (byte-identical output), `load_npz(path, required={key: (dtype, ndim)})`.

## `simbackend`

- `REFERENCE_FAKE = "FakeMarrakesh"`; `fake_backend()` (cached).
- `transpile_heron(circ, *, seed, optimization_level=1)`: always to the FakeMarrakesh target (heavy-hex, CZ).
- `make_simulator("ideal" | "heron", *, seed)`: noiseless `AerSimulator()` / `AerSimulator.from_backend(FakeMarrakesh())`.
- `run_counts(circ, mode, shots, seed, job_id=None) -> (counts, transpiled_hash, job_id)`: both modes run the
  same transpiled circuit, so only the noise differs.
- `sim_label(mode)`: the exact contract strings `simulated: ideal` / `simulated: Heron-class noise (FakeMarrakesh)`.
- `calibration_snapshot()`: `{fake_backend, qiskit_ibm_runtime_version, props_sha256, last_update_date}`.
- `circuit_hash(circ)`: sha256 of `qiskit.qasm3.dumps(circ)`.
- Not checked here: Aer support for **noisy dynamic-circuit feed-forward**. D must verify it before relying on it.

## `runrecord`

```python
from shared.runrecord import start_run
from shared.simbackend import run_counts

run = start_run("C_certificate", "chsh-heron", seed_hex=None, sim_mode="heron")  # C_certificate/runs/<ts>-chsh-heron/
counts, thash, job_id = run_counts(circ, "heron", 4000, seed=7)
run.add_job(job_id, thash, 4000, counts)                   # writes counts_<job_id>.json
run.add_input("shared/stubs/tumor_draw/tumor_draw.json", "tumor_draw")
run.add_output(run.path / "certificate.json", "certificate")
run.finish("notes")                                        # validates, then writes run.json
```

`run.json` records backend, sim label, calibration snapshot, job IDs, transpiled hashes, counts files,
code hash, git state and seed. `runs/` folders are gitignored.

## `validate`

```text
python -m shared.validate --stubs              # all stubs
python -m shared.validate --status             # all letter status.json + the 21-target set
python -m shared.validate path/to/output.json  # any contract file (or ledger .jsonl)
```

## `site.build`

```text
python -m shared.site.build                    # renders index.html + site/ (letters: preview only, never commit)
python -m shared.site.build --update-readme    # also refreshes the STATUS table in README.md (W / INT only)
```

Regenerate the stubs (`python -m shared.stubs.make_stubs`) after any change to `shared/*.py`, because the
stubs embed `code_hash(shared/)`. That happens only in W and INT.
