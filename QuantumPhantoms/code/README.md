# Quantum Phantoms — code

The MVP pipeline (epic `plans/epic-quantum-phantoms-mvp.md`): roll certified-quantum tumor
parameters, render them into synthetic CT tiles, bake a self-contained web page.

```
F1  rulebook → circuit → certified params   (f1_quantum/)
F2  params → 3D lesion → CT tile            (f2_imaging/)
F3  tiles → self-contained web page         (f3_web/)
```

## Directory layout

```
code/
  common/            shared data model (JSON-only, no numpy/qiskit)
    datamodel.py       TumorParams, QuantumRun, CohortTile dataclasses
  f1_quantum/        F1 — the quantum roll
    rulebook.py        published nodule stats → Ry angle trees
    circuit.py         9-qubit property circuit + division + CHSH circuits
    lineage.py         one quantum division → sibling-pair decode
    decode.py          measured bits → TumorParams
    certify.py         CHSH S from counts
    backend.py         AerSimulator (dev) / ibm_heron (human-run) + runner
    sampler.py         Sampler seam: PRNGSampler + QRNGSampler
    run.py             F1 CLI entrypoint
  f2_imaging/        F2 — lesion → CT image
    lesion.py          TumorParams → 3D HU blob
    ctsource.py        real CT (SimpleITK/.npy/PNG) + synthetic dev fallback
    insert.py          HU-domain insertion + matched noise, windowing, crop
    build_tiles.py     F2 CLI entrypoint
  f3_web/            F3 — web demo (the MVP page)
    web_template.html  light Siemens-theme page shell (no logo)
    build_web.py       F3 CLI entrypoint (embeds PNGs + data → one HTML)
  README.md
```

Each entrypoint is a package module — **run from `code/` with `python -m`**. Outputs land in
`../research_runs/<run>/` (F1 + F2) and `../web/index.html` (F3).

```bash
pip install -r ../requirements.txt
cd QuantumPhantoms/code
```

## F1 — the quantum roll

Published Fleischner/LIDC nodule stats → `Ry` angles → shallow circuit (9 property qubits +
one quantum division + one CHSH pair) → decode → 12 `TumorParams` + a job-level CHSH value.
All behind the `Sampler` seam (`QRNGSampler` quantum / `PRNGSampler` classical baseline).

```bash
# development — the only path run during implementation/verification:
python -m f1_quantum.run --backend aer --tiles 12 --pairs 2
# classical baseline (same schema, no CHSH):
python -m f1_quantum.run --sampler prng --tiles 12 --pairs 2
```

Writes `../research_runs/<run>/cohort_params.json` (the `TumorParams` contract) +
`quantum_run.json` (provenance: backend, job id, CHSH value).

### Hardware (Peter only)

```bash
python -m f1_quantum.run --backend ibm_heron --tiles 12 --pairs 2   # or --backend auto
```

Submits one real job — **run by Peter, not by automated implementation** (plan HARD RULE).
Uses a pre-existing saved IBM account (`QiskitRuntimeService()`); **no token is ever read,
embedded, or committed** — the repo-root `credentialsApi.py` is never touched. Capture the
real `job_id` + CHSH value for the demo (Aer writes `job_id=""`).

## F2 — lesion → CT image

Builds a 3D lesion per tumor (size→radius, type→HU, margin→surface), inserts its central
slice into a lung-CT slice with matched noise, writes cropped PNG tiles + `tiles.json`.

```bash
# default — real bundled lung (CC BY-SA, see data/ct_slices/NOTICE.md):
python -m f2_imaging.build_tiles --run research_runs/<f1_run>
# real demo — dir of LUNA16 .mhd/.raw, .npy HU arrays, or grayscale PNG:
python -m f2_imaging.build_tiles --run research_runs/<f1_run> --ct-source /path/to/luna16
# synthetic dev fallback (cartoon, zero downloads):
python -m f2_imaging.build_tiles --run research_runs/<f1_run> --ct-source synthetic
```

Writes into the same run dir: one shared `tiles/full_slice.png` (the whole lung with every
nodule), per-tile `tiles/zoom_<shot>_<gen>.png`, and `tiles.json`
(`{honest_label, ct_attribution, quantum_run, tiles:[CohortTile]}`). **F3.1:** the default
background is a **real lung CT**; nodules are placed **inside the lung fields** (lung-field
mask + lobe bias) and each `CohortTile` carries `full_png_path` + a normalised `bbox` so F3
can mark the nodule. All cohort nodules share one reference lung (dev simplification; real
multi-patient via `--ct-source <luna16 dir>`). LIDC DICOM is not read directly — convert to
`.npy`/`.mhd` first. `--ct-source synthetic` is tagged `synthetic_dev`. Default spacing
0.7 mm/px (`.mhd` metadata wins). F2 copies `chsh_value`/`backend_name`/`job_id` from
`quantum_run.json` onto every tile — it never recomputes quantum anything.

## F3 — web demo (the MVP)

Bakes one F2 run into a **single self-contained HTML page** (PNGs + data embedded inline; no
backend, no external requests). Light theme in the Siemens color scheme, **no logo**.

```bash
python -m f3_web.build_web --run research_runs/<f2_run>
# -> ../web/index.html   (override with --out)
```

Header (cohort size · backend · job-level CHSH) → tile grid (image + params + CHSH stamp) →
click-to-open detail modal (full params + CHSH-vs-2.0 certificate) → sibling lineage badges →
cohort-vs-rulebook histogram → honest-label footer. Sampler-blind; never recomputes anything
quantum. Aer/PRNG runs are labeled "simulator"/"classical baseline"; the real-hardware CHSH
value is the one for the public demo.

## Honest claim (Tier 1 provenance)

Tumor **parameters** are sampled from certified-quantum measurement; the **image** is a
classical rendering. CHSH > 2 is evidence the roll was genuinely quantum. No claim that
quantum makes a better or non-classical tumor. The CHSH value is **job-level** (one Bell test
over many shots × 4 settings), carried onto every tile with that tile's shot index — never a
per-tile Bell value. Use the real-hardware S on the page; the Aer value (~2.83) is noiseless
and for development only.

See `../plans/runlog-mvp-run.txt` for the exact copy-paste commands for a live run and a PRNG
test run.
