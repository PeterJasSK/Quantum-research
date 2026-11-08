# Feature F6 — Next cycle: prune, three separate quantum jobs, anatomy-driven placement (two arms), CT-conditioned quantum early growth with measured progression, distance-to-L2 per run

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved). **The epic has no F6 row (and no D-SCALE row) yet**; the developer adds them (Q1). F6 builds on F5 ([feature-F5-re-realism.md](feature-F5-re-realism.md), Complete) and D-SCALE ([feature-D-SCALE-decoherence-surviving-circuits.md](feature-D-SCALE-decoherence-surviving-circuits.md), Approved). Reference run: `research_runs/dscale_live_100_20261031-170957` (live executive demo).
**Feature ID:** F6
**Author:** Claude (Opus)
**Date:** 2026-11-04
**Status:** Draft

> **Stack locked.** Python 3.13 (conda base `/home/peter/anaconda3/bin/python3`), the pinned `requirements.txt` (qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy, scikit-image, SimpleITK, networkx, matplotlib). pylidc and its local annotation DB are already installed. **No new dependency** unless Q4 says otherwise.
>
> **Core directive.**
> - **Less code, not more.** The cycle opens with a pruning stage (P0). Every new module must replace or absorb something. The target is a smaller live tree at the end of F6 than at the start, excluding ported frozen copies.
> - **Run from `code/`**, `python -m <pkg>.<module>`. The MVP never imports the RE tree. Needed RE pieces (A `classes.py`, B `qemcmc.py` + `tumor_energy.py`) are copied frozen and listed in `code/dscale/PORTED.md` / `code/imaging/PORTED.md`.
> - **Hardware is Peter's.** Everything is developed and verified on AerSimulator / `FakeMarrakesh` (`FAKE=FakeMarrakesh`). Nothing in F6 submits to a QPU when run by Claude. The live scripts keep the existing pre-saved `QiskitRuntimeService()` path for Peter.
> - **No automated tests** (repo directive). Verification = the manual runs in §7, each smoke ≤ 20 min.
> - **Honesty gates (CLAUDE.md) apply to every number:**
>   - Claim level L0 / L1 / L1′, its classical baseline, its BP simulability number and its `simulated: …` / `hardware: <backend>, job <id>` label.
>   - **L2 is blocked today.** F6 *measures the distance to L2*; it never claims L2.

---

## 1. Why (Step Goal)

**Before (run 170957).**
- **One mixed job.** The D-SCALE job multiplexes three unrelated experiments into the same 26 circuits:
  - ghz-spine: L0. No parity checks were placed. It probably idled while the QCA ran.
  - ch-qca: L1, marginal (p_bonf 0.046 on 1 of 4 edges).
  - pmd-bank: L0. The 2-bit classical model beat the quantum machine.
  - Their failures cannot be separated, and the GHZ tree likely lost coherence waiting for the QCA.
- **Placement ignores anatomy.** The lobe is a statistical draw, but the site inside the lobe is a classical `default_rng(--seed)` pick (`imaging/place.py:58`) with no pleura or vessel awareness. Daughters anchor on the founder site even when their lobe differs (tile 9_1 RUL at the RLL founder's z = 123).
- **The quantum seed shape is a single snapshot.** It is one Z shot at t = 2 from a QCA that knows nothing about the CT. Classical growth after it is driven only by type-level published rates plus PRNG noise.
- **No BP simulability number.** None is computed for the live circuits, so "how far from L2" is unknown.

**After F6.**
1. **Pruned tree.** Dead scripts and modules are removed per the approved list (P0). `research_runs/` stops growing in git.
2. **Three separate jobs.** A (GHZ tree), B (CT-conditioned QCA) and C (memory machine) are each built, linted, submitted, analysed and recorded on their own, with their own validation gate. C refuses to go to hardware until its simulated gap clears 3 × floor.
3. **Anatomy-driven placement.**
   - A placement class (free / juxta-vascular / juxta-pleural) is drawn from an LIDC-measured prior (pylidc, `d_pleura ≤ r` rule, which fixes the #18 mismatch cause) and conditioned on what this host's lobe offers.
   - Two arms are evaluated side by side against the same target:
     - **Arm D (CT-conditioned dice):** the class is a node in the F1 Bayesian-network circuit, with angles from prior × host availability.
     - **Arm Q (quantum-enhanced MCMC):** the site is sampled from an anatomy energy with a quantum proposal and classical accept (Layden). It is compared with classical local and uniform Metropolis.
4. **Quantum early growth.**
   - The QCA patch is laid onto the CT around the placed site. Cells outside the lung are switched off and the initial set is biased by local anatomy.
   - It runs **T generations** (t = 1..T), each with a Z snapshot per tile and an entanglement witness per generation.
5. **Measured progression.** The classical grower continues from the last quantum generation. Its rate and anisotropy are **estimated from the measured quantum generation history** (occupancy trend, principal axis), clipped to published biology, instead of type-level constants plus noise.
6. **Distance to L2 per run.** Every submitted circuit family gets a BP simulability profile (chi sweep, fidelity, easy/hard) and a survive-vs-simulable cell. This shows where L2 would begin if hardware improves.

**Claim this cycle can earn.**
- **L1 per generation** (QCA negativity, Bonferroni, per t), for early growth on hardware.
- **L0 provenance** for the parameters and the placement.
- Arm Q is reported as a measured mixing comparison with **no advantage claim** unless one is measured.

---

## 2. Acceptance Criteria

**P0: pruning (first, before any new code)**

- [ ] **AC-1** (F6.1): an inventory of unused code exists and the approved items are removed.
  → `code/PRUNE.md` lists every module or script that is not on the live path (`run_budget_100.sh → dscale.live → imaging.build_tiles → f3_web.build_web`) and not on the D-SCALE sweep path, each with line count, importers and verdict (survey 2026-11-04). The items Peter ticks in Q2 are deleted. `code/README.md` and `code/dscale/RUNBOOK_DSCALE.md` drop the references to them.
- [ ] **AC-2** (F6.2): `research_runs/` stops growing in git.
  → Repo-root `.gitignore` ignores `QuantumPhantoms/research_runs/*` except an explicit whitelist (Q2; default: the demo run `dscale_live_100_20261031-170957/` and `_dscale/pmd_retune.json`). Untracking already-committed runs (`git rm --cached`) is listed as a command for Peter. Claude does not run it.

**S1: three separate jobs**

- [ ] **AC-3** (F6.3): `dscale.live` runs one family per invocation.
  → `--family ghz-spine|ch-qca|pmd-bank` builds, lints (`dscale.lint.enforce`), transpiles, applies the spend guard, submits (or fakes) and analyses **only** that family's circuits on its own region. Each family writes `<run>/dscale/<family>/` (`plan.json`, `bits.npz`, `circuits/`, `detail.json`). The run-level `dscale/dscale_run.json` aggregates the claims of the families that ran. `merge()` (`live.py:129`) is removed.
- [ ] **AC-4** (F6.4): job A validates the tree on its own.
  → `ghz-spine` runs a width ladder `--ladder 6,12,20,28` (one circuit set per N, same job).
  - Placing ≥ 1 parity check is required; if the allocator cannot place one, the record says `unchecked` explicitly instead of `kept 1.00`.
  - ghz2 is reported both raw and TREX-lite corrected.
  - The output is the crossover N where ghz2 drops below 1 (the collapse curve).
- [ ] **AC-5** (F6.5): job C has a simulation gate.
  → `--family pmd-bank` on real hardware refuses to submit (exit 8) unless `_dscale/pmd_retune.json` shows a simulated gap/floor > 3 for the chosen process. `--fake` runs are always allowed.
- [ ] **AC-6** (F6.6): the shell runner reflects the split.
  → `code/dscale/run_budget_100.sh` becomes the cycle runner with these steps:
  1. roll
  2. place
  3. job B
  4. job A, if `JOBS` contains `A`
  5. job C, if `JOBS` contains `C`
  6. tiles
  7. web

  Each step has its own log and a resume variable (`ROLLJOB=`, `JOB_B=`, `JOB_A=`, `JOB_C=`). Default `JOBS=B`. Backend auto-pick is unchanged (Out of Scope, Peter's refactor).

**S2: anatomy-driven placement, two arms**

- [ ] **AC-7** (F6.7): anatomy fields exist on the host.
  → `code/imaging/anatomy.py`:
  - `d_pleura` = EDT of `host.lungs` in mm.
  - `vessel_proxy` = in-lung voxels with smoothed HU > −500, minus airway; labelled **"HU proxy, not a segmentation"**.
  - `d_vessel` = EDT of `vessel_proxy`.
  - `classify(site, r)`, ported frozen from RE A `classes.py` (`classify_site_arrays`): juxtapleural if `d_pleura ≤ r`; juxtavascular if `d_vessel ≤ r` and pleura clear by 3 mm; free if both are clear; otherwise ambiguous.
  - The fields are cached in `research_runs/_hosts/<id>/anatomy.npz`.
- [ ] **AC-8** (F6.8): the placement prior is measured from LIDC, not assumed.
  → `python -m imaging.placement_prior` reads pylidc consensus nodules (≥ 3 readers, ≥ 3 mm) on the scan list in Q5 and classifies each with the `d_pleura ≤ r` rule (the fix proposed in RE A dossier #18). It writes `code/imaging/data/placement_prior.json` with class rates, n, a 95 % CI and the Kostis/Ambrosini [F01] reference 0.33 / 0.45 / 0.22. It prints MATCHED / NOT MATCHED (reference inside the CI). A non-match is recorded as a result, not hidden.
- [ ] **AC-9** (F6.9): Arm D, the CT-conditioned dice.
  → The F1 rulebook gains a `placement_class` node (2 qubits, 3 classes + 1 spare remapped) **conditioned on lobe**.
  - P(class | lobe) = prior × availability(class, lobe on this host), renormalised.
  - Availability is the fraction of the lobe's candidate voxels in each class, computed from `anatomy.py`.
  - `type | class` and `margin | class` tilts follow RE B `rulebook.py` `cpt_by_context` (values marked "(verify)").
  - The property register grows from 9 to 11 qubits (pairs: 22). `decode.py` returns the class. The site is then picked among that class's candidates by `rng(seed_hex_geometry, "F6-site")`, **not** `--seed`.
  - Honest label on the page: "conditioning (CT features pick the angles), not quantum anatomy".
- [ ] **AC-10** (F6.10): Arm Q, the quantum-enhanced MCMC placement.
  → `code/dscale/qmcmc.py` is a frozen copy of RE B `qemcmc.py` (`quantum_Q`, `local_Q`, `uniform_Q`, `mh_matrix`, `spectral_gap`, `trotter_circuit`, `noisy_Q`).
  - **Energy.** E(site) is defined on the n = 8-qubit coarse site index of the drawn lobe (256 candidate sites, Q6): an attraction term `−w_v·exp(−d_vessel/λ)`, a pleura term `w_p·exp(−d_pleura/λ)` and a class-prior term `−log P(class)`, fitted to a quadratic Ising form (h, J). The fit residual is recorded.
  - **Sampling.** Quantum proposal (Trotter circuit, simulated: ideal and `FakeMarrakesh`) plus classical Metropolis accept. Baselines: local and uniform proposals.
  - **Report.** Exact spectral gap δ for each of the 3 arms, and the total-variation distance of the sampled sites to the Boltzmann target at equal steps.
  - **Claim:** none above L0 unless δ_q > max(δ_local, δ_uniform) beyond the noise-flattening check (asymmetry), as in the RE B dossier. A hardware pack for Peter is written; nothing is submitted.
- [ ] **AC-11** (F6.11): both arms are evaluated against the same target.
  → `python -m imaging.place_cohort --run <run> --arm dice|qmcmc|both` writes `<run>/placement.json`. Per tile it holds `{arm, class, site_zyx, d_pleura_mm, d_vessel_mm, lobe, lobe_source: "z-band proxy"}`; per arm it holds class proportions vs `placement_prior.json` (χ² p-value) and the median `d_pleura` / `d_vessel` vs LIDC. Daughters inherit the parent's lobe and class and sit ≤ 3·r from the parent **within that lobe** (fixes the 9_0 / 9_1 mismatch). `build_tiles` reads `placement.json` and no longer constructs `Placer` with `--seed`.

**S3: CT-conditioned QCA, quantum early growth**

- [ ] **AC-12** (F6.12): the QCA patch is conditioned on the CT at the placed site.
  → `ch_qca.spec()` accepts `site_ctx`:
  - The patch layout is mapped to voxels around `site_zyx` (one patch step = `PITCH_MM` 0.5 mm, scaled by `size_mm`).
  - Cells whose voxel is outside the lung are **disabled**: no gates touch them and they read 0.
  - The k extra initial cells are drawn with weights ∝ `exp(−d_vessel/λ)` (growth toward vessels), from `rng(seed_hex, "DS-qca-init")`.
  - α stays global π/2, so CH = 1 CZ (Q7).
- [ ] **AC-13** (F6.13): generations with a witness each.
  → Job B builds per tile one Z snapshot at each t = 1..T (T = 3 default, Q8), plus run-level tomography (9 settings) and an echo **at each t** on tile 0's conditioned patch.
  - Analysis gives, per generation, the Bonferroni negativity on the 4 pre-registered edges, the echo vs the random band, and the claim (L1 if negativity passes at that t, else L0).
  - The echo is reported but is not part of the pass rule (stated in `WITNESS`, fixing the docstring/code mismatch at `ch_qca.py:39` vs `:269`).
  - Witness circuits get `SHOTS_WITNESS` (default 20 000, inside the cap); snapshots get `SHOTS`.
- [ ] **AC-14** (F6.14): the seed is the last quantum generation, and all generations are kept.
  → `seedlift.lift` runs on each t's chosen shot (`rng(geom, f"DS-qca-snapshot-t{t}")`). `dscale/<ch-qca>/seed_shapes.npz` holds one mask per tile per t. `CohortTile.quantum_growth` lists `{t, active, seed_cells, witness_passed, claim_level}`.

**S4: progression estimated from the quantum history**

- [ ] **AC-15** (F6.15): classical growth continues the measured trend.
  → `code/dscale/progression.py` `estimate(masks_by_t, size_mm, type)` returns three things:
  - **Rate:** a growth exponent from log(occupied voxels) vs t (least squares, with σ), mapped to `p0` and clipped to the published VDT range for the type (`params_lung.json`, Hasegawa (verify)).
  - **Anisotropy:** the principal axis of the t = T mask and an eccentricity weight w ≤ 0.3 (Q9).
  - **Fallback:** `"constant"` when the fit is undetermined (σ > estimate or < 3 generations).

  `imaging/growth.py` takes `cfg["types"][type]["p0"]` from the estimate and a new optional `anisotropy=(axis, w)` that scales the distance in `division_probability` along the axis. The first T growth frames are the lifted quantum generations (role `quantum-gen`); later frames are classical (role `classical`).
  - Honest label: "progression parameters estimated from T measured quantum generations; extrapolation is classical; the Z snapshots have an exact classical surrogate".

**S5: distance to L2**

- [ ] **AC-16** (F6.16): every run measures how far it is from L2.
  → For each family job that ran, `dscale/l2_distance.py` calls `survival.bp_profile` on that job's actual circuits (per generation for ch-qca) and writes `dscale/<family>/bp.json`: `chi_max`, `fidelity_vs_ref`, `easy` / `hard`, runtime per chi.
  - It also writes one survive-vs-simulable line: witness passed (y/n) × BP hard (y/n).
  - It reports the **smallest depth t\* at which BP needs chi > 16** (simulation ladder t = 1..6 on the same patch, ≤ 20 min), next to the deepest t where the witness still passed on this run. "Distance to L2" = t\* − t_pass.
  - `bp.smallest_chi` is fixed to accept `bp_profile` rows (`chi` / `fidelity`).

**S6: records, page, docs**

- [ ] **AC-17** (F6.17): the page shows the split and the generations.
  → `f3_web/build_web.py` + `web_template.html` show:
  - one result card per job (A / B / C) with label, claim, witness and BP line;
  - a per-tile placement badge (arm, class, distances);
  - a per-generation witness strip (t = 1..T, L1 / L0);
  - quantum-gen frames tinted in the growth player.

  The honest label states: L1 per generation at most; placement = conditioning (Arm D) or measured mixing (Arm Q); image classical; L2 not claimed, distance shown.
- [ ] **AC-18** (F6.18): reproducibility.
  → The same inputs reproduce `placement.json`, the circuits (QPY/QASM hashes) and `seed_shapes.npz` byte-identically. Only `created_utc` differs.
- [ ] **AC-19** (F6.19): docs are updated.
  → `QuantumPhantoms/README.md` Progress table + changelog; `code/README.md`; `code/dscale/RUNBOOK_DSCALE.md` (new cycle runner, per-job resume, the C gate, Peter-only hardware steps); both `PORTED.md` files list the new frozen copies.

---

## 3. Out of Scope (Postponed)

- **Backend chosen by name, fit check, kill if it does not fit** → planned refactor, **Peter does it himself**. F6 keeps `pick_backend` unchanged and keeps every new entry point callable with a backend object so his `--backend <name>` drops in.
- **Real segmentation** (lungmask lobes, TotalSegmentator vessels) → postponed unless Q4 says install. F6 uses the pleura EDT and the HU vessel proxy, both labelled.
- **Dynamic-circuit lineage (RE D-2: divide / rest / necrotic with feed-forward)** → a later cycle (F7 candidate), if CT-conditioned QCA generations survive.
- **Per-site α (2 CZ per CV)** → simulation-only flag, not on the live path (Q7).
- **Any L2 / advantage claim** → blocked by CLAUDE.md. F6 only measures the distance.
- **Hardware submission by Claude** → never. Peter runs the hardware steps from the runbook.
- **Siemens host reselection (T0), G lineage record, H validation, INT chain** → their own plans.
- **Certified bit count (C01 min-entropy, hidden rounds)** → stays the RE C / INT priority, not F6.
- **Calcified tiles:** no quantum growth (Q11). They keep `procedural-3d` and are labelled "no growth (calcified)".

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Job split | One family per `dscale.live` call (`--family`), one region per job, same allocator (`allocate.composite` restricted to the family's requests) |
| Anatomy | `scipy.ndimage.distance_transform_edt` on `host.lungs` and the HU vessel proxy; frozen RE A class rule |
| Placement prior | pylidc consensus (≥ 3 readers, ≥ 3 mm), `d_pleura ≤ r` rule, binomial 95 % CI; reference Kostis/Ambrosini [F01] |
| Arm D | F1 BN + `placement_class \| lobe` node, prior × host availability; site pick `rng(seed_hex_geometry, "F6-site")` |
| Arm Q | Frozen RE B `qemcmc.py`; 8-qubit coarse site index; quadratic Ising fit of the anatomy energy; exact δ for 3 arms (256 states) |
| QCA conditioning | Disabled out-of-lung cells; vessel-weighted initial set; α = π/2 global |
| Generations | T = 3; snapshot per tile per t; witness per t on tile 0; `SHOTS_WITNESS` 20 000 |
| Progression | Log-occupancy slope → p0 (clipped to published VDT), principal-axis anisotropy w ≤ 0.3, constant fallback |
| L2 distance | `survival.bp_profile` on live circuits; depth ladder t = 1..6 to find t\* (chi > 16) |
| Seeds | All new hidden choices use `rng(seed_hex, "F6-*")` or `"DS-*"` labels (imaging.seedhash) |

**Conventions & Notes:**
* Follow the D-SCALE conventions: lint before transpile, job id written before waiting, `--fake` path identical except the sampler, hardware label `hardware: <backend>, job <id>`.
* Frozen copies, never imports, from the RE tree. Each copy gets a `PORTED.md` row (source commit, kept, changed).
* Every new CLI respects the 20-minute smoke cap (D-SCALE AC-7) and prints its honest label.
* Net code size: P0 deletions are counted in `code/PRUNE.md` against F6 additions (frozen copies listed separately).

---

## 5. Data Model (Additions/Modifications)

```text
[Existing Entity - Modifying] TumorParams            (common/datamodel.py)
  ...(existing fields)...
  placement_class   str | None   free | juxtavascular | juxtapleural (Arm D roll); None for old runs

[Existing Entity - Modifying] CohortTile             (added to _F5_OPTIONAL, omitted when unset)
  placement         dict | None  {arm, class, site_zyx, d_pleura_mm, d_vessel_mm, lobe, lobe_source}
  quantum_growth    list | None  [{t, active, seed_cells, witness_passed, claim_level}]
  progression       dict | None  {p0, p0_source: "fit"|"constant", rate, rate_sigma, axis, w}

[Existing Entity - Modifying] DScaleRun
  jobs              dict         {family: {job_id, backend, label, claim, detail_ref, bp_ref}}
  generations       list | None  ch-qca per-t witness rows
  l2_distance       dict | None  {t_star, t_pass, distance}

[New File] <run>/placement.json
  tiles: {tile_id: {arm, class, site_zyx, d_pleura_mm, d_vessel_mm, lobe, lobe_source}}
  arms:  {dice|qmcmc: {class_props, chi2_p, median_d_pleura, median_d_vessel, delta (qmcmc), tv (qmcmc)}}

[New File] code/imaging/data/placement_prior.json
  {rates, n, ci95, reference, matched, scans, rule: "d_pleura <= r"}

[New File] research_runs/_hosts/<id>/anatomy.npz   (gitignored cache)
  d_pleura, d_vessel, vessel_proxy
```

Old runs load unchanged: every new field is optional.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `code/PRUNE.md` | Inventory (path, lines, importers, verdict) + approved deletions + net-size ledger |
| Delete | items ticked in Q2 (default: `code/dscale/run_budget_40.sh`, `code/dscale/run_budget_120.sh`, `code/dscale/families/__main__.py`, `code/f4_qalife/` if no page uses it, the 2-D procedural path `code/imaging/insert.py`, `code/imaging/lesion.py`, `code/imaging/ctsource.py` + `--renderer procedural`) | P0 |
| Modify | `/home/peter/PycharmProjects/Quantum-research/.gitignore` | Ignore `QuantumPhantoms/research_runs/*` except the whitelist |
| Modify | `code/dscale/live.py` | `--family`; remove `merge`; per-family build / analyse / record; ladder for A; C gate; ch-qca generations + `site_ctx`; reads `placement.json` |
| Modify | `code/dscale/run_budget_100.sh` | Cycle runner: roll → place → B → (A) → (C) → tiles → web; per-step resume vars; `JOBS` |
| Modify | `code/dscale/families/ch_qca.py` | `spec(site_ctx)`, disabled cells, vessel-weighted init, per-t snapshot/tomo/echo builders, `WITNESS` text fixed |
| Modify | `code/dscale/families/ghz_spine.py` | Ladder build; explicit `unchecked` when 0 checks; raw + TREX ghz2 |
| Modify | `code/dscale/families/pmd_bank.py` | `sim_gate()` reading `pmd_retune.json` |
| Modify | `code/dscale/allocate.py` | `composite(..., families=[...])` restricts requests to one family |
| New | `code/dscale/qmcmc.py` | Frozen copy of RE B `qemcmc.py` + energy fit for site placement |
| New | `code/dscale/progression.py` | `estimate()` from per-t masks → p0, anisotropy, fallback |
| New | `code/dscale/l2_distance.py` | `bp_profile` on live circuits, t\* ladder, survive-vs-simulable line |
| Modify | `code/dscale/bp.py` | `smallest_chi` accepts `bp_profile` rows |
| Modify | `code/dscale/PORTED.md` | Rows for `qmcmc.py` |
| New | `code/imaging/anatomy.py` | EDT fields, vessel proxy, frozen class rule, cache |
| New | `code/imaging/placement_prior.py` | pylidc → `data/placement_prior.json` + MATCHED verdict |
| New | `code/imaging/data/placement_prior.json` | Generated output (committed, small) |
| New | `code/imaging/place_cohort.py` | CLI `--arm dice|qmcmc|both` → `placement.json` + arm evaluation |
| Modify | `code/imaging/place.py` | Class-aware candidates; seed from `seed_hex`; daughter within parent lobe. Absorbs the Arm-D site pick (no new module) |
| Modify | `code/imaging/growth.py` | `anisotropy` in `division_probability`; quantum-gen frames first |
| Modify | `code/imaging/frames.py` | Pass progression + per-t masks |
| Modify | `code/imaging/build_tiles.py` | Read `placement.json`; drop `Placer(--seed)`; fill `placement`, `quantum_growth`, `progression` |
| Modify | `code/imaging/PORTED.md` | Row for the A class rule |
| Modify | `code/f1_quantum/rulebook.py` | `placement_class \| lobe` node + type/margin tilts, context from host availability |
| Modify | `code/f1_quantum/circuit.py` | 11-qubit register (22 for pairs) |
| Modify | `code/f1_quantum/decode.py` | Decode class (spare code remapped) |
| Modify | `code/common/datamodel.py` | Fields from §5 |
| Modify | `code/f3_web/build_web.py`, `code/f3_web/web_template.html` | Job cards, placement badge, generation strip, quantum-gen frame tint, label |
| Modify | `code/dscale/RUNBOOK_DSCALE.md`, `code/README.md`, `QuantumPhantoms/README.md` | Docs, progress, changelog |

---

## 7. Manual Verification (No Tests)

All runs from `code/`, `FAKE=FakeMarrakesh` or Aer. Nothing touches a QPU.

- [ ] **Verify AC-1:**
  - `cat PRUNE.md` lists each candidate with importers.
  - `grep -rn "<deleted module>" .` returns nothing for each deleted item.
  - `FAKE=FakeMarrakesh bash dscale/run_budget_100.sh` still runs end to end.
- [ ] **Verify AC-2:** `git status --short ../research_runs | head` shows new run directories as ignored (absent). The whitelisted run still shows as tracked.
- [ ] **Verify AC-3:** `python -m dscale.live --run <r> --budget 100 --family ch-qca --fake FakeMarrakesh` writes only `dscale/ch-qca/`, and its circuits touch only the qca region (lint log). Repeat for `ghz-spine` and `pmd-bank`.
- [ ] **Verify AC-4:** the ghz-spine fake run prints one ghz2 (raw, TREX) per N in the ladder and a crossover N. With 0 placeable checks, `detail.json` says `"checks": "unchecked"`.
- [ ] **Verify AC-5:** with `pmd_retune.json` gap/floor ≤ 3, the hardware path (`--dry-run` without `--fake`) exits 8 with the gate message. `--fake` runs.
- [ ] **Verify AC-6:** `FAKE=FakeMarrakesh JOBS=ABC bash dscale/run_budget_100.sh` shows 7 steps, one log each. Killing it after step 3 and rerunning with `RUN=… JOB_B=<fake id>` resumes.
- [ ] **Verify AC-7:** `python -m imaging.anatomy --host LIDC-IDRI-0481` prints the class fractions per lobe and writes `anatomy.npz`. A spot-check slice PNG shows `d_pleura` and the vessel proxy overlay.
- [ ] **Verify AC-8:** `python -m imaging.placement_prior` prints rates ± CI vs 0.33 / 0.45 / 0.22 and MATCHED / NOT MATCHED. The JSON holds n and the scan list.
- [ ] **Verify AC-9:** an Aer roll decodes 11-bit words to `placement_class`. The cohort's class proportions over 4,000 shots match the conditioned CPT within sampling error (printed).
- [ ] **Verify AC-10:** `python -m imaging.place_cohort --run <r> --arm qmcmc` prints δ_q / δ_local / δ_uniform, the asymmetry, the TV distance at equal steps, the Ising-fit residual and the claim (L0 unless the gap check passes).
- [ ] **Verify AC-11:** `--arm both` writes `placement.json` with both arms' evaluation. Every daughter's lobe equals its parent's (printed check). `build_tiles` log shows sites from `placement.json`.
- [ ] **Verify AC-12:** for a juxta-pleural tile, the printed patch map shows disabled cells on the outside-lung side, and the QASM has no gate on them.
- [ ] **Verify AC-13:** the ch-qca fake run prints per-t rows `t=1..3: negativity (p_bonf), echo F vs band, claim`. `WITNESS` text equals the pass rule.
- [ ] **Verify AC-14:** `seed_shapes.npz` keys are `tile_<s>_<g>_t<t>`. The montage figure shows T masks per tile.
- [ ] **Verify AC-15:** the build_tiles log prints per tile `p0 fit/constant, rate ± σ, axis, w`. Growth frames 0..T−1 carry role `quantum-gen`. With `--no-dscale` the old constant path is unchanged.
- [ ] **Verify AC-16:** `dscale/ch-qca/bp.json` exists with `chi_max`, `easy/hard` per t, and `t_star`, `t_pass`, `distance`. Runtime ≤ 20 min.
- [ ] **Verify AC-17:** open `../web/dscale_live_100.html`: three job cards (or one with `JOBS=B`), placement badges, the generation strip, tinted quantum frames, and the label text as in AC-17.
- [ ] **Verify AC-18:** rerun the same fake run into a copy; `sha256sum` of `placement.json`, `seed_shapes.npz` and the QASM files match.
- [ ] **Verify AC-19:** README Progress row for F6 and a changelog line exist. The runbook lists the per-job hardware commands as Peter-only.

---

## 8. Open Questions

- [ ] **Q1:** Add F6 (and the missing D-SCALE row) to the epic §2 table and §7 graph? *Proposed:* yes, the developer adds both; F6 depends on F5 + D-SCALE.
- [ ] **Q2:** Which pruning items to delete, and which runs to keep tracked?
  *Proposed:*
  - **Delete:** `run_budget_40.sh`, `run_budget_120.sh`, `families/__main__.py`; `f4_qalife/` only if no page under `QuantumPhantoms/web/` uses it (checked in P0); the 2-D procedural renderer (`imaging/insert.py`, `lesion.py`, `ctsource.py`, `--renderer procedural`).
  - **Keep:** `survival.py`, `bp.py`, `kicked_ising.py`, `pauli_noise.py` (needed for the L2 distance and noise checks); `hw_pack.py`, `validate_noise.py` (runbook tools; delete if you no longer use them); `f1_quantum/run.py` + `sampler.py` (ROLL=0 source cohort).
  - **Keep tracked:** only `dscale_live_100_20261031-170957/` and `_dscale/pmd_retune.json`.
- [ ] **Q3:** Pruning inside F6 or as a separate feature? *Proposed:* inside F6 as stage P0, done and verified before any S1 code.
- [ ] **Q4:** Install real segmentation (lungmask, TotalSegmentator) for true lobes and vessels? *Proposed:* no in F6 (no new dependency). Use the pleura EDT + HU vessel proxy, both labelled; lobes stay the z-band proxy. Revisit if the AC-8 verdict depends on vessel accuracy.
- [ ] **Q5:** Which LIDC scans for the placement prior? *Proposed:* the 20 scans in RE A `repro/lidc_subset.txt` (the #18 rerun list), extended to all local `~/data/LIDC-IDRI` cases if n < 30 nodules.
- [ ] **Q6:** Arm Q encoding? *Proposed:* 8-qubit coarse site index per lobe (256 sites on a grid over the lobe's candidate mask), anatomy energy fitted to quadratic Ising (h, J), residual reported. Alternative: occupancy Ising on a 2×2×2 patch as in RE B, which models shape, not site, so it is not proposed.
- [ ] **Q7:** Per-site α (anatomy sets the QCA angle) or masking + init bias only? *Proposed:* masking + vessel-weighted init on the live path (α = π/2, 1 CZ per CH). Per-site α is a simulation-only flag because it doubles the CZ count.
- [ ] **Q8:** How many generations, and is the witness per tile or run-level? *Proposed:* T = 3; witness per generation run-level on tile 0's conditioned patch (9 settings + echo per t = 30 circuits) at 20 000 shots. Per-tile witnesses would be 12 × 30 circuits, too expensive.
- [ ] **Q9:** Bounds on the measured progression? *Proposed:* p0 clipped to the published VDT range per type; anisotropy weight w ≤ 0.3; constant fallback when σ > estimate.
- [ ] **Q10:** Default hardware plan per job? *Proposed:*
  - B: always (≈ 2–3 QPU-min at the proposed shots).
  - A: once, as the ladder (≈ 1 QPU-min).
  - C: only after the sim gate passes.
- [ ] **Q11:** Quantum growth for calcified nodules? *Proposed:* no (calcified nodules are stable); keep `procedural-3d`, labelled.
- [ ] **Q12:** Daughter placement rule? *Proposed:* the daughter inherits the parent's lobe and class and sits ≤ 3·r from the parent inside the lobe; if no candidate exists, the nearest same-lobe candidate, logged.

---

## 9. Post-Implementation Notes

[Filled after implementation.]
