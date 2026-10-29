# INT — Integration: the A→H chain runner and its weak links

Plan: [`feature-INT-integration.md`](../feature-INT-integration.md) · Epic: [`epic-reverse-engineering.md`](../epic-reverse-engineering.md) · Whole chain: [index](../index.html#pipeline)

## Purpose

One command runs the whole pipeline, one tumour from real contract files, letter by letter, through each letter's
existing CLI (no cross-letter imports). Its main use in this pass is **finding weaknesses**:

- `--probe` asks every letter's argparse whether the flags the chain passes exist, and checks preconditions, without running anything;
- a real run validates every output against `shared/contracts/` and adds runtime findings (stale beacon pulse, duplicate seed, founder ignored, geometry mismatch …).

**Scope of this pass (developer decision, 2026-10-29).** Built: the runner, the probe, readiness sections and the
overview. Run for real: only the cheap prefix `commit → certify`. **Not done:** contract v1.1.0 and the
producer/consumer CCR edits, the full A→H run, the target-state advance to `integrated`, and the Future sections.
The epic done-criterion ("one tumour travels A→H from real files with a verifying receipt") is therefore
**not met yet**. The probe shows the chain would stop at `sign` (G `fill --job`).

## How to run

From `RE/` with base Python (`/home/peter/anaconda3/bin/python3`). A runs with `qp-re-a` automatically.

```bash
python -m INT_integration.src.chain --probe --tag gaps                 # gap report, nothing runs (exit 4 = blocked)
python -m INT_integration.src.chain --dry-run                          # every step's command, in order
python -m INT_integration.src.chain --host LIDC-IDRI-0004 --mode heron --tag ref            # the full chain
python -m INT_integration.src.chain --stop-after certify --tag prefix   # only a prefix (what ran here)
python -m INT_integration.src.chain --from draw --resume runs/<chain> --reuse place=A_placement/runs/<run> --tag resume
python -m INT_integration.src.chain ... --allow-gaps                    # run past a gap (still recorded) to see what breaks next
python -m INT_integration.src.chain ... --certify-args "--settings classical"   # fail path: S ≤ 2 → exit 2
```

Exit codes: `0` ok · `1` stage failure · `2` certificate fail (S ≤ 2, no retry) · `3` code changed after the commit,
or `--reuse` refused · `4` blocked by an integration gap.

| Stage | Steps (letter CLI) | Inputs from | Main outputs |
|---|---|---|---|
| `commit` | `G keys init` (once), `G receipt commit --rulebook B_mapping/data/rulebook_lung.json` | — | commit `receipt`, ledger entry |
| `certify` | `C fetch_pulses` (re-fetched until a pulse postdates the commit, ≤ 10 tries), `C certify --mode … --pulse-index -1` | commit time | `certificate`, `quantum_job_record` |
| `place` | `A segment` (cached), `A place --seed-hex derive(cert seed, "A.place") --radius-mm 4.72` | C | `site_candidates`, `anatomy_masks` |
| `draw` | `B map --variant b2 --k-sites 8` | A, C | `compiled_circuit`, `quantum_job_record`, `tumor_draw` |
| `grow_q` | `D grow --tumor-draw --certificate --compiled-circuit`, `D bp --circuit` (optional) | B, C | witnesses, `memory_advantage_record`, `simulability_report`, `seed_shape` |
| `grow_c` | LIDC HU check (runner), `E grow --follow-up-days 90` | A, B, C, D | `growth_trajectory` |
| `render` | `F fingerprint --masks`, `F render … --export` + geometry assert (runner) | A, B, C, E | `scanner_fingerprint`, `hybrid_volume` |
| `sign` | `G receipt fill`, `G dicom_export`, `G verify --trusted`, tamper check (runner) | all | `receipt`, signed series, verify report |
| `validate` | cohort manifest (runner), `H lidc_ref` (cached), `H report` | all | `validation_report` |

Each run writes `runs/<ts>-e2e-<tag>/chain.json` (stage records, `ctx`, findings, `beacon_fetch`, `mismatches`)
and `logs/<step>.log`, after every step. Files: [`src/chain.py`](src/chain.py) (CLI, run/probe/dry-run),
[`src/stages.py`](src/stages.py) (stages as data + checks), [`src/cohort.py`](src/cohort.py),
[`src/tamper_check.py`](src/tamper_check.py).

## What ran (evidence)

All simulated (`FakeMarrakesh` Heron-class noise). `runs/` is gitignored; the IDs are the record.

| Run | What | Result |
|---|---|---|
| `runs/20261029-185947-probe-gaps` | probe, all 9 stages | **1 blocking gap** (G.fill), 5 warn; exit 4 |
| `runs/20261029-184821-e2e-probe-prefix` | commit → certify, no wait | pass; pulse 18:47:00 < commit 18:48:22 → `beacon_fresh: false` |
| `runs/20261029-184911-e2e-probe-prefix2` | + fixed 57 s wait | pass; NIST `/pulse/last` still returned 18:48:00 at 18:50:21 (lag ≈ 2 min) |
| `runs/20261029-185117-e2e-probe-prefix3` | + re-fetch loop | 3 fetches lagged, 4th `ReadTimeout` → cache fallback; Ŝ 2.762, S_low 2.442, 17 869 bits |
| `runs/20261029-185431-e2e-probe-prefix4` | same | 1st fetch `ReadTimeout` → fallback; certificate **byte-identical** to prefix3 (seed `7dfb4d50…`) |
| `runs/20261029-185537-e2e-reuse-test` | `--reuse` of a pre-commit C run | refused, exit 3 (G ordering rule) |
| `runs/20261029-185538-e2e-resume-test` | `--from draw` without A | stops: upstream `A.sites` missing, exit 1 |

C certificates from the 4 prefix chains: Ŝ 2.722–2.762, S_low 2.403–2.442, 15 668–17 869 certified bits, all pass
(`C_certificate/runs/20261029-18*-chsh-heron`). The git-tracked beacon cache was restored by hand afterwards
(`git checkout`), because `fetch_pulses` overwrites it (gap 9).

## Integration gaps and weak links found

Ranked by how hard they stop the chain. The top 3 are the dashed red edges in the [index diagram](../index.html#pipeline) (`weak-edges` in `pipeline-overview.md`).

| # | Where | Kind | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| 1 | G `receipt fill` | gap · **block** | `--job` is a single value: the chain passes 5 job records (C, B, 3× D), argparse keeps the last, so only one quantum job is bound in `fill.job_ids` | probe `G.fill` | `action="append"`; bind every job id + counts hash |
| 2 | B → D | gap | D ignores B's draw: `--tumor-draw` is only an upstream ref; lineage uses fixed `PHI0, DPHI` and parent `|1>` (`lineage.py:26, 135`), so every tumour gets the same founder | agent read + runner check `_post_grow_q` | AC-8 founder preset from draw `type × margin`, seed label from `shape_seed_hex` |
| 3 | D `bp` | gap | no `--circuit`; requires `--run <D run>` → B's circuits have no BP simulability number (honesty gate) | probe `D.bp_b` | add `--circuit <compiled_circuit.json>` (AC-9) |
| 4 | C beacon | weak-link | no chain got a pulse later than its commit: `/pulse/last` lags ≈ 2–3 min, and each fetch makes 13+ HTTPS calls that time out (`ReadTimeout`, 30 s) | prefix runs 1–4, `chain.json.beacon_fetch` | fetch only the newest pulse; poll with backoff; select "first pulse after `committed_utc`" in `beacon.py` |
| 5 | C seed | weak-link | the simulated job is seeded from the public pulse: reusing a pulse reproduces the same "certified" seed in two different chains → the same tumour | prefix3 vs prefix4 certificates identical | refuse a pulse already used by an earlier certificate (runner now warns) |
| 6 | G commit | weak-link | `code_hash` covers `*.py` of A–F only: G and H code, and the parameter JSONs (`class_prior.json`, `params_lung.json`, lesion library) can change after the commit unnoticed | `commit_manifest.json` keys `ABCDEF`; probe `G.commit` | hash parameter files into the commit (`commit.code_hashes` + params) |
| 7 | A `segment` | precondition | no segmentation cache for LIDC-IDRI-0004: first `place` costs ~25–75 min CPU | probe `A.segment` | pre-segment the reference host once |
| 8 | A `place` | gap (worked around) | plan argv has no `--radius-mm`; fallback `latest_radius()` needs an A repro run (none on disk → `SystemExit`) | probe `A.place` | runner passes `--radius-mm 4.72`; make the radius explicit in the contract (CCR-A1) |
| 9 | C `fetch_pulses` | weak-link | overwrites the git-tracked `repro/data/beacon_pulses.json`; no run dir | probe `C.fetch`, `git status` after prefix runs | write chain pulses into the run dir |
| 10 | F `render --export` | weak-link | PNGs go into git-tracked `F_render/figures/`: each chain run adds host-derived images to the repo | probe `F.render` | export into the run dir |
| 11 | C `certify` | weak-link | exits 0 on S ≤ 2 (B, D, E exit 2) | `certify.py` main; runner gates on `status` | exit 2 on fail |
| 12 | E params | assumption | `vessel_threshold` (30) is a Pixel2Cancer push count, not HU: the plan's "check against the HU histogram" does not apply | `params_lung.json` | check `lung_hu_bounds` only (runner does, before E) |
| 13 | G ledger | contract | the commit's ledger entry has `kind: "receipt"` | prefix runs, `G_provenance/runs/ledger.jsonl` | CCR-G1 |
| 14 | C certificate | contract | no `beacon_pulse_id`, `chsh_S_lower`, `eps` | runner check `_post_certify` | CCR-C2, CCR-C3 |

Runtime checks that exist but did not run yet (the chain did not reach them): draw `site_id` ∈ A's sites; drawn size
vs placement radius; witness `claim_level` vs `passed` (CCR-D4); trajectory `stub: false` + ≥ 2 snapshots; LIDC
lung-HU check; hybrid geometry = A's host geometry; receipt binds every job; `VERIFIED`; one-voxel tamper detected;
H sections without a number at n = 1.

## Contract fixes

None applied in this pass. The 33 CCRs stay open in the letter READMEs; v1.1.0 is the next INT step (plan AC-1–AC-3).

## Done-criterion

- [ ] One tumour travels A→H from real files with a verifying receipt. **Not met**: blocked at `sign` (gap 1), and the
  A→F stages have not run (A segmentation not cached).
