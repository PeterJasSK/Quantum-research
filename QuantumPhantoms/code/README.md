# Quantum Phantoms — code

One command, one line through the pipeline. Run from `code/` with `/home/peter/anaconda3/bin/python3`.

```bash
python main.py                          # dry run: small sizes on the local fake backend (FakeMarrakesh, not hardware)
python main.py --backend ibm_aachen     # live: real hardware ("auto" = least busy). Peter only.
python main.py --shots 2000             # shots per circuit (default 4000 live, 400 dry)
python main.py --run <run directory>    # continue a stopped run (finished sections skipped, submitted jobs fetched)
```

Every run lives in `../research_runs/run_<dry|live>_<timestamp>/`; the page is `../web/<run>.html`.

## Sections

`main.py` calls each section's `main.py` → `run(ctx)` in this order. Sections exchange files only.

| Section | Files | Does | Writes |
|---|---|---|---|
| `B_mapping` | `main.py`, `roll.py`, `rac.py`, `xeb.py` | rulebook → circuit → tumour parameters + CHSH pair, one job | `cohort_params.json`, `quantum_run.json`, `rulebook.json` |
| `C_certificate` | `main.py` | CHSH gate: S ≤ 2 rejects the draw and stops the run (no retry) | `certificate.json` |
| `D_quantum_growth` | `main.py`, `dscale.py` (+ `ghz_spine`, `ch_qca`, `pmd_bank`, `causal_states`, `seedlift`), `clock.py`, `pairs.py`, `ring_l2.py` | quantum growth: per-tumour seed shapes or a hypothesis circuit | `dscale/` |
| `A_placement` | `main.py` | a 3-D site per tumour in the host lung | `sites.json` |
| `E_classical_growth` | `main.py`, `params_lung.json` | Kansal–Torquato + Pixel2Cancer growth from the seed | `growth.json`, `_roi/` |
| `F_render` | `main.py`, `lesion_fitted.py`, `lesion.py`, `insert.py`, `noise.py`, `fingerprint.py` | render into the host CT with its own blur and noise | `tiles.json`, `tiles/*.png` |
| `G_provenance` | `main.py` | lineage record + hash-chained ledger | `lineage_record.json`, `ledger.jsonl` |
| `H_analysis` | `main.py` | what the run shows, with its limits | `analysis.json` |
| `webpage` | `main.py`, `template.html` | one self-contained HTML page | `../web/<run>.html` |
| `common` | `runio`, `quantum`, `targets`, `allocate`, `lint`, `pauli_noise`, `witness`, `qhard`, `game`, `host`, `lidc_fetch`, `datamodel` | shared code | — |

Constants live where they are used, one place each: `common/__init__.py` (`HOST`, `FAKE_BACKEND`,
`MAX_QPU_SECONDS`), `B_mapping/roll.py` (`TILES`, `PAIRS`), `D_quantum_growth/dscale.py` (`BUDGET`),
`E_classical_growth/main.py` (`FRAMES`), `A_placement/main.py` (`SEED`).

## Switching the circuit in B and D

One constant at the top of the section's `main.py`. The table of circuits (sizes, bound, pass rule, refusals) is
right below it.

```python
# B_mapping/main.py
CIRCUIT = "ROLL"      # ROLL | R2-Q2 | R2-Q3 | R2-D4 | R4-HEX | R5-H12 | R5-MAP8 | R5-D20 | R5-Y18

# D_quantum_growth/main.py
CIRCUIT = "DSCALE"    # DSCALE | GHZ-SPINE | CH-QCA | PMD-BANK | R1-STAR-001 | R1-TILE24 | R1-M2-00001 | R3-LADDER | R3-TEST | R3-CHIP64 | R3-INTRINSIC
                      # | R5-LADDER | R6a-S36 | R6a-S44 | R6b-LEAN64 | R6b-PUB64
```

- **B:** the roll always runs (it is the seed draw). Any other value adds that hypothesis circuit on the same
  backend; its claim is about the device, never the tumour.
- **D:** `DSCALE` is today's composite (GHZ spine + QCA + PMD); its QCA snapshots are the seed shapes. `GHZ-SPINE`,
  `CH-QCA`, `PMD-BANK` run one of its families alone (first pick of the qubits, nothing running next to it; the
  spine tree is then chosen by qubit quality, not depth). `CH-QCA` and the R6 rings also give seed shapes. With any other circuit the tumours grow from the 2 mm ball.
- `R3-TEST` is the hypothesis test of Seif et al. (2408.03376 Sec. III): name a hidden Pauli channel with a sister
  memory; without a quantum memory the success rate is at most 1/2 + 0.43 M 2^-n. One pool of 400 circuits serves
  every size (8 to 40 pairs) and every trial.
- Rings (R5, R6) are picked on the calibration-pruned chip; when pruning leaves no ring (one pruned qubit removes
  a hexagon) every ring is ranked by pruned qubits, then measured CZ + readout error, and the claim note says so.
- Claims go to `claims.json` and to the page. A dry-run pass is labelled "(dry run: not a claim)".
- A dry run tests the pipeline, not the science: 4 tumours of at most 7 mm (`DRY_*` in `B_mapping/roll.py`), 400
  shots, each circuit's `dry` sizes from its `CIRCUITS` row, no do-not-build refusals. About 2 to 3 minutes.
- Circuits on the plans' "do not build" list for a backend are refused (`refuse` in the table).
- Scores are raw counts: no readout mitigation in a hypothesis job.
- Sizes are first-run sizes; the plan's published size is in the comment next to it.

Plans: `../plans/qhard-D-L2-ring-configurations.md`, `../plans/qhard-R1-R5-configurations-and-BD-flagship.md`.

## Live runs

- Pre-saved `QiskitRuntimeService()` account, never a token. One backend per run (`backend.json`).
- Every job id is written to `jobs/<key>.json` before waiting. `--run <dir>` fetches it instead of resubmitting.
- Spend guard: the estimate over all jobs of a run stays under `MAX_QPU_SECONDS` (45); shots are cut to fit, below
  300 the job is refused.
- To redo a section, delete its output file and run `--run <dir>` again.

```bash
python -m common.lidc_fetch LIDC-IDRI-0481       # once: the public host CT (~136 MB)
python -m G_provenance.main <run directory>      # does every file still match the lineage record?
```

## Not run yet

Nothing here was executed after the refactor (repo directive). Syntax, import and undefined-name checks pass. First
places to look when a run fails:

| Where | Open point |
|---|---|
| `common/quantum.py` | New single path for every job (roll included). Dry run of wide Clifford jobs uses the Pauli-twirled model. |
| `D_quantum_growth/dscale.py` | Same logic as the old live job, re-plumbed. Default `BUDGET = 100` live; a dry run uses `DRY_BUDGET = 40`. |
| `common/game.py` | Win rule derived (all deterministic parities), not transcribed from 2110.04277. |
| `D_quantum_growth/ring_l2.py` | Own check construction; doping loss is a placeholder; doped circuits are sampled live only. |
| `B_mapping/xeb.py` | bits(ε) is a two-point line; inputs are pseudo-random, so it cannot pass as coded. |
| Pruned files | `ghz_spine`, `ch_qca`, `pmd_bank`, `causal_states`, `seedlift`, `allocate`, `lint` were cut to what the pipeline calls. |

## Honest claim

Tumour parameters are sampled from a quantum measurement; growth and image are classical. CHSH > 2 on hardware is
evidence the roll was quantum; a dry run certifies nothing. Every other quantum number carries its level, its
classical bound, the rigour of that bound and its label.
