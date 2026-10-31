# Quantum Phantoms — code

The MVP pipeline (epic `plans/epic-quantum-phantoms-mvp.md`): roll certified-quantum tumor
parameters, render them into synthetic CT tiles, bake a self-contained web page.

```
F1  rulebook → circuit → certified params   (f1_quantum/)
F2  params → 3D lesion → CT tile            (imaging/, renderer "procedural")
F5  params → grown lesion → Siemens LIDC CT (imaging/, renderer "grown", default)
F3  tiles → self-contained web page         (f3_web/)
D-SCALE  40/100/120-q circuit families + seed shapes for F5 (dscale/, optional)
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
  imaging/           F2 + F5 — lesion → CT image (both renderers; was f2_imaging/)
    build_tiles.py     CLI entrypoint (--renderer grown|procedural)
    lesion.py          procedural: TumorParams → 3D HU blob (F2.1)
    ctsource.py        procedural: real CT (SimpleITK/.npy/PNG) + synthetic dev fallback
    insert.py          procedural: 2-D insertion + matched noise; windowing, crop (shared)
    lidc_fetch.py      grown: fetch a public LIDC-IDRI series from TCIA
    host.py            grown: 3-D HU host + threshold lung/body masks (cached, gitignored)
    fingerprint.py     grown: host scanner PSF + NPS (air–skin edge MTF, soft-tissue NPS)
    place.py           grown: lobe → 3-D site in the lung mask
    growth.py          grown: Kansal–Torquato + Pixel2Cancer growth engine (RE E copy)
    lesion_fitted.py   grown: lattice → lesion HU from the LIDC-fitted library (RE F copy)
    insert3d.py        grown: 3-D additive-delta insert with host blur + noise (RE F copy)
    frames.py          grown: per-tumour grow → render → insert + growth frames
    seedhash.py        grown: per-tile seeds from the quantum shot bits
    data/              copied RE parameter files (params_lung.json, lesion_model_library.json)
    PORTED.md          what was copied from the RE pipeline @ 2609cbe and what changed
  f3_web/            F3 — web demo (the MVP page)
    web_template.html  light Siemens-theme page shell (no logo)
    build_web.py       F3 CLI entrypoint (embeds PNGs + data → one HTML)
  f4_qalife/         F4 — Mode-A living-process arm (optional)
    witness.py         within-generation entanglement witness W = ⟨XX⟩+⟨ZZ⟩
    fitness.py         classical (non-learned) fitness + selection
    loop.py            Mode-A hybrid loop: divide (P1) + fate (P2) + measure-restart
    sampler.py         QALifeSampler — third Sampler impl (evolved cohort)
    run_qalife.py      F4 CLI entrypoint
  dscale/            D-SCALE — quantum growth at 40 / 100 / 120 q (simulation only; optional)
    budget.py          20-min deadline + 4000-shot / 15-repeat caps (--full lifts them)
    targets.py         marrakesh / kingston / boston / nighthawk / helios-class calibration records
    allocate.py        calibration pruning, path / BFS tree / patch, buffered composite
    lint.py            seven survival lints (exit 5 on a violation)
    pauli_noise.py     Pauli-twirled target noise for stabilizer simulation up to 156 q
    witness_scale.py   DFE GHZ fidelity, ghz2, TREX-lite, echo, Bonferroni negativity, k·σ
    families/          ghz_spine, ch_qca, pmd_bank, kicked_ising (+ the composite recipe)
    survival.py        survive-vs-simulable map + Goldilocks zone
    validate_noise.py  Pauli model vs full fake-backend noise; hardware back-test
    run.py             orchestrator over an F1/F4 run → <run>/dscale/
    hw_pack.py         hardware packs (files only, never submits)
    bp.py, tomography.py, causal_states.py, seedlift.py   frozen RE D copies (PORTED.md)
    RUNBOOK_DSCALE.md  full sweeps + hardware steps (Peter only)
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

## Imaging — params → CT tiles (F2 procedural, F5 grown)

One package, two renderers, one output contract (`tiles.json` + `CohortTile`). Re-rendering a run
**overwrites** `tiles/zoom_*.png` + `tiles.json`; files only the other renderer makes are left and logged
as `stale:` (delete them by hand if you want).

### F5 `grown` (default) — Siemens LIDC host + classical growth + fitted render

```bash
python -m imaging.lidc_fetch LIDC-IDRI-0481            # once: ~136 MB public CT -> ~/data/LIDC-IDRI
python -m imaging.build_tiles --run research_runs/<run> [--host LIDC-IDRI-0481] [--frames 8] [--compare]
```

- **Host:** `LIDC-IDRI-0481`, a public LIDC-IDRI case scanned on a SIEMENS SOMATOM Definition (kernel
  B45f, 1 mm; CC BY 3.0). None of the older local LIDC scans is Siemens. Fallback Definition cases:
  `LIDC-IDRI-0507`, `-0736`. First use builds `research_runs/_hosts/<id>/` (HU volume, threshold masks,
  fingerprint; ~1 min; gitignored — patient voxels).
- **Per tumour:** site in the lung (lobe → side + z band) → growth from a Ø 2 mm seed to the rolled size
  (Kansal–Torquato layers + Pixel2Cancer pleura wall, p0 calibrated to published VDTs *(verify)*), then
  +90 d follow-up → render with the LIDC-fitted lesion library (solid core HU N(+30, 30), plan Q4) →
  3-D insert with the scan's own PSF + NPS noise. Calcified: procedural lesion in 3-D, no growth.
- **Outputs:** `tiles/zoom_<shot>_<gen>.png`, `tiles/full_<host>_<z>.png`, 8 pixel-growth frames
  `tiles/grow_<shot>_<gen>_<k>.png` (seed → baseline → follow-up), `tiles.json` with `renderer`, `diag`
  (VDT, volume check, σ ratio), seeds and provenance; `--compare` adds `compare_procedural_vs_grown.png`.
- **Exit codes:** 0 ok, 1 bad input, 2 host missing (prints the fetch command), 3 a tile fell back to
  the procedural lesion (`renderer: procedural-fallback`, reason in `diag`).
- **Runtime (CPU, one cached host):** ≈ 11 min for 12 tiles × 8 frames when the roll draws three 26 mm
  tumours (each ~2–3 min); ≈ 4 min for a typical small-nodule cohort. Same inputs → byte-identical PNGs.
- **Seeds:** per tile from the job id / run name + the tile's quantum shot bits. Each shot carries only
  ~9 quantum bits, so the seed is a **replay key and provenance, not strong randomness**.
- Code copied (frozen) from the RE pipeline — see `imaging/PORTED.md`.

### F2 `procedural` — the original look

```bash
# default — real bundled lung (CC BY-SA, see data/ct_slices/NOTICE.md):
python -m imaging.build_tiles --run research_runs/<f1_run> --renderer procedural
# real demo — dir of LUNA16 .mhd/.raw, .npy HU arrays, or grayscale PNG:
python -m imaging.build_tiles --run research_runs/<f1_run> --renderer procedural --ct-source /path/to/luna16
# synthetic dev fallback (cartoon, zero downloads):
python -m imaging.build_tiles --run research_runs/<f1_run> --renderer procedural --ct-source synthetic
```

Builds a **realistic procedural** lesion per tumor (F2.1): irregular lobulated/spiculated shape,
heterogeneous textured interior, soft partial-volume edge; inserts its central slice into one shared
lung slice with a point-spread blur (`--psf`, default 0.7 px) + correlated matched noise. Writes
`tiles/full_slice.png`, per-tile `tiles/zoom_<shot>_<gen>.png` and `tiles.json`. `--ct-source
synthetic` is tagged `synthetic_dev`. Default spacing 0.7 mm/px (`.mhd` metadata wins). Both renderers
copy `chsh_value`/`backend_name`/`job_id` from `quantum_run.json` onto every tile — never recompute
quantum anything.

## F3 — web demo (the MVP)

Bakes one F2 run into a **single self-contained HTML page** (PNGs + data embedded inline; no
backend, no external requests). Light theme in the Siemens color scheme, **no logo**.

```bash
python -m f3_web.build_web --run research_runs/<f2_run>
# -> ../web/index.html   (override with --out)
```

Header (cohort size · backend · job-level CHSH) → tile grid (image + params + CHSH stamp, renderer
chip for F5 runs) → click-to-open detail modal (full params + CHSH-vs-2.0 certificate; F5 runs add the
pixel-growth player: play/pause/scrub, day · Ø · role) → sibling lineage badges →
cohort-vs-rulebook histogram → honest-label footer. Sampler-blind; never recomputes anything
quantum. Aer/PRNG runs are labeled "simulator"/"classical baseline"; the real-hardware CHSH
value is the one for the public demo.

## F4 — Mode-A living-process arm (optional)

Turns F1's one-division hint into a real **evolutionary loop**: founder cells divide with
mutation (P1) and commit a fate in superposition under a phase dial (P2); a **classical host**
scores fitness, kills losers, and seeds the next generation from the survivor's measured bits
(measure-and-restart = **Mode A**, constant depth, survives the coherence wall). Each
generation records a **within-generation entanglement witness** `W = ⟨XX⟩+⟨ZZ⟩` (`W > 1` ⇒
entangled; ⟨σz⟩ alone is classical — we measure the off-diagonal).

`QALifeSampler` is a third `Sampler` implementation, so the evolved lineage comes out as the
same `TumorParams` contract — **feed the F4 run dir straight into the unmodified F2 → F3
commands**; the page renders the multi-generation genealogy via the existing `gen N of ∞`
lineage badges.

```bash
# evolve a cohort (default 4 founders × 3 generations × 1 survivor = 12 tiles):
python -m f4_qalife.run_qalife --backend aer --founders 4 --generations 3 --survivors 1
# the interference knob — phase sweeps the fate mix (proliferative/quiescent → necrotic):
python -m f4_qalife.run_qalife --backend aer --phase 1.5708
# then render with the SAME F2/F3 entrypoints (no code change):
python -m imaging.build_tiles --run research_runs/qalife_aer_<ts>
python -m f3_web.build_web       --run research_runs/qalife_aer_<ts>
```

Writes `cohort_params.json` + `quantum_run.json` (as F1) plus `witness.json` (per-generation
`W`). Honest label, carried on every artifact: **quantum *within* a generation, classical
genealogy** — the measure-and-restart seed between generations is classical. Mode B (coherent
genealogy) and the collapse-curve sub-study are out of scope (physically blocked on Heron).

## D-SCALE — quantum growth at 40 / 100 / 120 qubits (optional)

Plan: `../plans/feature-D-SCALE-decoherence-surviving-circuits.md`. Four plug-and-play circuit families with a
40, 100 and 120-qubit preset each, built on the survival laws measured in `artificial-life/` (unitary, terminal
readout, equator founder, separable soma, native couplers only):

| Family | What | Claim | Hardness |
|---|---|---|---|
| `ghz-spine` | certified clonal genealogy: Big-Cats GHZ tree + parity checks + separable draw-driven soma | L1 (GME, DFE F > 0.5 by 2σ) | none (stabilizer, BP χ = 2) |
| `ch-qca` | single-control Goldilocks QCA (exact T6 on degree-2 sites, parity-Goldilocks on degree 3/4), 0 routing SWAPs | L1 (Bonferroni negativity) | the frontier family |
| `pmd-bank` | deferred-measurement causal-state machines (Wu PMD process, re-tuned) | L1′ (gap > 3× sampling floor) | none (2-q blocks) |
| `kicked-ising` | Kim / Tindall anchor: calibrates the Pauli predictor and BP | calibration | known BP territory |

The **quantum layer now shapes the tumour**: per tile, a QCA Z-snapshot driven by the tile's draw (21-site patch in
ideal mode, 12-site hexagon in heron mode) is lifted to a 3-D seed, and F5's grower starts from it instead of the
2 mm ball. Without `<run>/dscale/` every output is byte-identical to F5.

```bash
python -m dscale.targets --show                                       # the 5 simulation targets
python -m dscale.families --list                                      # families, claims, 40/100/120 presets
python -m dscale.allocate --target nighthawk --budget 120 --recipe composite
python -m dscale.lint --selftest                                      # exit 5 = the 2 injected violations
python -m dscale.validate_noise --pauli --smoke                       # AC-4 Pauli vs full noise
python -m dscale.validate_noise --backtest --smoke                    # AC-5 QALife / PJ0 / Big Cats back-test
python -m dscale.bp --equivalence                                     # QR BP copy == RE BP, and faster
python -m dscale.survival --budget 120 --target nighthawk --smoke     # survive-vs-simulable map
python -m dscale.run --run ../research_runs/<run> --budget 40 --mode ideal --smoke
python -m imaging.build_tiles --run ../research_runs/<run>            # grows from the quantum seeds
python -m f3_web.build_web --run ../research_runs/<run>               # adds the "Quantum growth (D-SCALE)" panel
python -m dscale.hw_pack --budget 40 --backend ibm_boston --from-map <survival_map.json>
```

Outputs: `<run>/dscale/` (`dscale_run.json`, `allocation.json`, `scale_detail.json`, `seed_shapes.npz`,
`circuits/*.qasm`, `figures/`); standalone maps, validation, the PMD re-tune and hardware packs go to
`../research_runs/_dscale/`. `dscale.run` refuses (exit 6) a run dir with git-tracked files.

**Caps.** Every CLI stops at `--max-minutes 20` by default, writes what it has with `truncated: true` and prints
what it skipped; `--shots` is capped at 4000 and `--repeats` at 15. `--full` (with `--max-minutes 0`) lifts them
and is meant only for the runbook. Full sweeps and all hardware steps are in `dscale/RUNBOOK_DSCALE.md`; nothing
in `dscale/` submits a job.

**Honest label.** Simulated; the seed shape is a quantum snapshot; growth and image are classical; no
classical-hardness claim. Survives (L1 / L1′) and BP-hard (frontier) are separate columns: GHZ and PMD never count
as frontier. The Goldilocks zone (alive and BP-hard) is the only honest meaning of "closer to quantum advantage"
here, and an empty zone is a reported result.

## Honest claim (Tier 1 provenance)

Tumor **parameters** are sampled from certified-quantum measurement; the **growth** (F5) and the
**image** are classical. CHSH > 2 is evidence the roll was genuinely quantum. No claim that
quantum makes a better or non-classical tumor. The CHSH value is **job-level** (one Bell test
over many shots × 4 settings), carried onto every tile with that tile's shot index — never a
per-tile Bell value. Use the real-hardware S on the page; the Aer value (~2.83) is noiseless
and for development only.

See `../plans/runlog-mvp-run.txt` for the exact copy-paste commands for a live run and a PRNG
test run.
