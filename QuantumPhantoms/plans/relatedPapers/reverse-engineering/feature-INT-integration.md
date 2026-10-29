# Feature INT — Integration: stubs → real A→H chain, contract v1.1.0, site rebuild, pipeline-readiness + Future sections

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). INT is the last step (epic §7). It runs after every letter has merged to `main`: W (`a2ff3dc`), C (`249a4fe`), F, E, G (`6079294`), H (`b081a4e`), A (`169bc33`), D (`43267b8`), B (`d426cab`). No worktrees remain, and no parallel session runs during INT.
**Feature ID:** INT
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Partially implemented (2026-10-29). Developer cut the scope to *runner + weakness finding*: AC-4 and AC-16–AC-19 are done. The Future sections were added in a second pass on the same day. AC-20 is done except the commit. Everything else is deferred (§9). Approved by developer 2026-10-29 (Q1–Q14 defaults accepted).

> **Technical constraints / core directive.**
> - **Stack.** As in the epic: Python 3 + Qiskit 2.3.1 + qiskit-aer 0.17.2, NumPy/SciPy, SimpleITK, pydicom, cryptography, markdown-it-py + Jinja2 (site build). Two interpreters, both already on the machine:
>   - conda **base** (`/home/peter/anaconda3/bin/python3`, 3.13.5) for B–H, `shared/` and the site build;
>   - conda env **`qp-re-a`** (`/home/peter/anaconda3/envs/qp-re-a/bin/python`, 3.12.16) for A only (torch, TotalSegmentator, lungmask).
>
>   **No new installs.** H runs its "radiomics-lite" engine; `qp-re-h` is not created (Q8).
> - **Simulation only.** Every quantum stage runs on `AerSimulator`, either ideal or with `FakeMarrakesh` Heron-class noise. No real IBM job is submitted. The end-to-end tumour is labelled "simulated: Heron-class noise" everywhere.
> - **INT is the only feature allowed to edit** `shared/`, `about.html`, `index.html`, `site/`, the root `README.md` and every letter folder. Contract changes follow the `shared/README.md:5` order: **amend the contract once, then the producer, then the consumer.**
> - **No cross-letter imports.** The chain runner calls every letter through its existing CLI, as a subprocess. It passes contract file paths and never imports another letter's code.
> - **Commands** run with `RE/` as the working directory, where `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.
> - **Honesty gates (epic §3) also apply to the new Readiness and Future prose.** Specifically:
>   - Every claim is labelled evidence-based / extrapolation / speculative.
>   - No "quantum biology", no "more realistic because quantum", and no "classically impossible" claim outside the 15-year fault-tolerant horizon. Even there it is labelled speculative and tied to claim levels L2/L3.
> - **No automated tests.** Verification is manual, plus the end-to-end run itself, which is the integration check.

---

## 1. Why (Step Goal)

**Before.**
- Eight letters exist, each reproduced or dissected and runnable **standalone**. Every letter's real runs consume `shared/stubs/` (`stub: true`). Real files never travel from one letter to the next.
  - E: 27 runs on disk, all on stubs. F: 21 runs. A, B, C, D, G and H have no runs left on disk, because their worktrees were removed and `runs/` is gitignored.
- **33 contract change requests sit unapplied** in letter READMEs against the frozen contract v1.0.0: CCR-A1, B1–B2, C1–C3, D1–D7, E 1–4, CR-F1/F2, G1–G4, H1–H3.
- Several INT hand-offs are written down but not done:
  - D still uses a fixed founder instead of B's draw.
  - F uses its own threshold masks (all lobes = 0) instead of A's masks.
  - E's `vessel_threshold` and `lung_hu_bounds` are unchecked on real LIDC.
  - B's circuits have no belief-propagation (BP) simulability number; D #9 never ran over them.
  - C's beacon cache dates from 2026-10-28, which is earlier than any INT commit.
- **The site is stale.**
  - `index.html` says "20 listed, 1 rejected". The real state is 13 adapted, 5 dissected, 3 rejected.
  - The root README `STATUS` block still shows every target as listed.
  - `index.html` renders no Markdown. It has cards plus one table and nothing more.
- Nothing tells a reader how far each letter is from **pipeline use**, where the chain is weakest, or where the work leads: cancer detection, other organs, digital twin.

**After.**
1. **Contract v1.1.0.** Every accepted CCR is applied once in `shared/contracts/`, as an additive change except where Q2 says otherwise. Producers and consumers are updated. Stubs are regenerated, and every stub and every new run validates.
2. **One tumour travels A→H from real files with a verifying receipt.** This is the epic §2 done-criterion. A new runner, `INT_integration/src/chain.py`, executes:
   `G commit → C certify (fresh beacon pulse) → A place (LIDC-IDRI-0004) → B-2 draw → D grow (founder from B) → E grow → F render (A masks) → G fill + DICOM + verify → H report`
   - Each stage reads the previous stage's real contract files.
   - All PRNG seeds descend from C's extracted seed.
   - A stage failure, for example CHSH S ≤ 2, stops the chain and is logged. There is no retry (epic §6 decision 6).
3. **Honesty-gate debt is paid.**
   - BP simulability numbers exist for B's compiled circuits.
   - E's lung HU/vessel thresholds are checked on LIDC.
   - The chain's ValidationReport (H) is produced on the integrated output.
4. **Target states advance.** Every `adapted` target whose output the verified chain consumed moves to `integrated`. Nothing skips a state.
5. **Pipeline-readiness evaluation.**
   - Each letter README gets a `## Pipeline readiness` section. It contains a rating (Not ready / Prototype / Usable with caveats / Production-ready), a justification, the weak links, and how to strengthen each one.
   - `index.html` gets an overall view: a pipeline diagram coloured by rating, the contract edges between letters, and the weakest points of the whole chain.
6. **Future sections.**
   - Each letter README gets a `## Future` section covering: aim of the paper(s), contribution, role in cancer detection, beyond lungs, digital-twin vision, and 5/10/15-year predictions with assumptions, evidence labels and risks.
   - `index.html` gets a whole-pipeline Future section.
7. **Site rebuilt and committed** (INT is the only step that commits `index.html` / `site/`), with the root README `STATUS` block updated.

---

## 2. Acceptance Criteria

### Contracts (v1.1.0)

- [ ] **AC-1** (INT.1): *Contract v1.1.0 applies every accepted CCR in one place.*
  - `shared/__init__.py` `CONTRACT_VERSION = "1.1.0"`.
  - The `_envelope.schema.json` version const becomes `enum ["1.0.0","1.1.0"]`, so the E/F runs already on disk still validate. New writes are `1.1.0`. The same applies to the own consts in `target_status` and `ledger_entry`.
  - Each accepted CCR is applied as listed in §5. All changes are additive or optional, except the D4 and D5 enum relaxations and the C2 `chsh_S` maximum.
  - `shared/contracts/README.md` gets a "v1.1.0 changelog" table: CCR id → schema → change → producer → consumer.
  - → `shared/contracts/*.schema.json`, `shared/contracts/README.md`, `shared/__init__.py`.
- [ ] **AC-2** (INT.2): *Producers and consumers follow the amended contract.*
  - Each producer listed in §6 writes the new fields:
    - C writes `beacon_pulse_id`, `chsh_S_lower`, `eps` and `transpiled_hashes[]`.
    - D writes `transpiled_hashes[]`, `d_kl_bits_per_symbol`, the witness `chsh` block, and `claim_level: "L0"` when its witness fails.
    - G writes ledger `kind: "commit"`, `commit.code_hashes{}` and `fill.voxel_sha256`.
    - F writes `local_nps`, `ssp`, `tumor_type` and `size_mm`.
    - B writes `params.prior`, `extra` and `state_encoding`.
    - A writes `nominal_radius_mm`.
    - E writes `snapshots[].summary` and `draw_id`.
  - Each consumer reads the new field, with a fallback to the v1.0.0 field:
    - G and H read `beacon_pulse_id`, falling back to `curby_pulse_id`.
    - H reads `tumor_type`/`size_mm`, falling back to `tumor_draw`.
    - G's verifier passes its trusted keys into `shared.validate` (G4).
  - Each letter README's "Contract change requests" section marks every request as `applied in v1.1.0 (INT)` or `declined: <reason>`.
- [ ] **AC-3** (INT.3): *Shared helpers are INT-aware, and stubs are regenerated.*
  - `shared/runrecord.py` `_letter_of` maps a folder named `INT_integration` to letter `"INT"`. The contracts already allow `produced_by.letter = "INT"`.
  - `shared/validate.py` gains `--trusted <trusted_keys.json>` (G4): with it, a receipt's key must appear in the list.
  - `python -m shared.stubs.make_stubs` is rerun. Stubs embed `code_hash(shared/)`.
  - `python -m shared.validate --stubs` and `python -m shared.validate --status` both pass.

### End-to-end chain

- [x] **AC-4** (INT.4): *The chain runner exists and is resumable.* → `INT_integration/src/chain.py:280` (CLI), `:259` (run), `:80` (reuse check), `:72` (code freeze); stages `INT_integration/src/stages.py:460`. Deviations: `chain.json` only (no `run.json` via `start_run`, because that needs the `shared/runrecord._letter_of` change); added `--resume`, `--stop-after`, `--probe`, `--dry-run`, `--allow-gaps`.
  - Command: `python -m INT_integration.src.chain --host LIDC-IDRI-0004 [--mode heron|ideal] [--site-class auto|free|juxtavascular|juxtapleural] [--from <stage>] [--reuse <stage>=<run_dir> …] [--tag <tag>]`.
  - It creates `runs/<YYYYmmdd-HHMMSS>-e2e-<tag>/` (the epic's cross-letter `RE/runs/`) through `shared.runrecord.start_run`, with letter `INT`.
  - It runs the 9 stages in order:
    1. `commit`
    2. `certify`
    3. `place`
    4. `draw`
    5. `grow_q`
    6. `grow_c`
    7. `render`
    8. `sign`
    9. `validate`
  - Each stage is a subprocess call to the letter's existing CLI:
    - A runs with the `qp-re-a` interpreter.
    - All other letters run with `sys.executable`.
    - Each call passes `--tag int-<chain_id>`, or for CLIs without `--tag` (Q11), the run is found as the single new `runs/*` directory created after the stage started.
  - After each stage:
    - it records `{stage, argv, interpreter, run_dir, outputs{contract: path}, exit_code, started_utc, finished_utc}` in `runs/<…>/chain.json`;
    - it validates every output with `shared.validate`.
  - `--from` and `--reuse` let a stage reuse an earlier run directory; the main case is A's TotalSegmentator cache, about 25–75 min. Reuse is allowed only if that run was **produced after this chain's commit and by the committed code**, which is G's own ordering rule. Otherwise the runner refuses and says why.
- [ ] **AC-5** (INT.5): *Commit comes first, with a fresh beacon pulse.*
  - Stage `commit` runs `G_provenance.src.keys init` if no key exists, then `G_provenance.src.receipt commit --rulebook B_mapping/data/rulebook_lung.json`. This creates a ledger entry with `kind: "commit"`.
  - Stage `certify` first runs `C_certificate.repro.fetch_pulses --n 12`, so the test-round choice uses a NIST Beacon pulse **later than** the commit. It then runs `C_certificate.src.certify --mode heron --pulse-index <latest>`.
  - If the network is unavailable, the runner falls back to the cached pulse (Q4) and records `beacon_fresh: false` with an honesty note in `chain.json` and the INT README.
  - If the certificate fails (S ≤ 2), the chain stops at `certify` with exit 2. The rejection is logged in `C_certificate/runs/rejections.jsonl` and `chain.json`, with no retry.
- [ ] **AC-6** (INT.6): *Real placement, seeded from the certificate.*
  - Stage `place` runs `A_placement.src.segment --patient LIDC-IDRI-0004` (cached when present), then `A_placement.src.place --patient LIDC-IDRI-0004 --per-class 10 --seed-hex <derive(cert.extracted_seed_hex,"A.place")>` (Q3).
  - Its `sites.json` and `anatomy_masks.json` are the only placement inputs used downstream.
  - With `--site-class auto`, the site is the first site of the class drawn by B-2 (stage `draw`). Otherwise it is the first site of the requested class.
- [ ] **AC-7** (INT.7): *Real context-conditioned certified draw.*
  - Stage `draw` runs `B_mapping.src.map --variant b2 --mode heron --sites <A sites.json> --certificate <C certificate.json> --k-sites 8` (Q5).
  - It writes `compiled_circuit`, `quantum_job_record`, `tumor_draw` and `drift.json`.
  - The decoded draw's `site_id` must exist in A's `sites.json`. If it does not, the runner stops: this is a contract mismatch to fix (§3 rule), not to skip.
  - A drawn size that violates its placement class, for example a juxtapleural draw too large for its site, is re-checked as B deferred. The runner logs it as a weak-link finding.
- [ ] **AC-8** (INT.8): *Quantum growth starts from B's founder.*
  - D's founder is derived from B's `tumor_draw` instead of D's fixed founder (feature-D Q1). The mapping is deterministic and documented in D's README:
    - draw `type` / `margin` → founder fate-angle preset;
    - `shape_seed_hex` → D's lineage seed label.
  - Stage `grow_q` runs `D_quantum_growth.src.grow --mode heron --tumor-draw <B> --certificate <C> --compiled-circuit <B>`.
  - It writes `quantum_lineage`, `witness_record_{lineage,qca}`, `memory_advantage_record`, `simulability_report` and `seed_shape`.
  - Its claim levels are stated as measured. If the QCA witness fails under Heron noise, the seed shape is recorded as L0 (CCR-D4).
  - Coupling the lineage outcome into the QCA initial condition is out of scope (§3).
- [ ] **AC-9** (INT.9): *BP simulability exists for B's circuits.*
  - `D_quantum_growth.src.bp --run --circuit <B compiled_circuit>` (a new `--circuit` input, so D's BP adversary also serves B's circuits) writes one `simulability_report` per B circuit used in the chain, linked from B's README.
  - B's README replaces "BP number pending D #9" with the measured `fidelity_vs_sim` and χ, labelled "simulated: Heron-class noise".
- [ ] **AC-10** (INT.10): *Real classical growth.*
  - Before the run, E's `params_lung.json` `vessel_threshold` and `lung_hu_bounds` are checked against A's LIDC-IDRI-0004 masks and HU histogram. The result goes into a "Checked on LIDC (INT)" note in E's README, and the values are changed only if they fall outside the measured range.
  - Stage `grow_c` runs `E_classical_growth.src.grow --masks <A anatomy_masks.json> --sites <A sites.json> --site-id <chosen> --draw <B tumor_draw> --certificate <C> --seed-shape <D seed_shape.json> --follow-up-days 90`.
  - It exits 0. Its output `growth_trajectory` has `stub: false` and carries baseline + follow-up snapshots.
- [ ] **AC-11** (INT.11): *Real render with A's masks.*
  - Stage `render` runs `F_render.src.fingerprint` on LIDC-IDRI-0004 (CR-F1/F2 fields), then `F_render.src.render --trajectory <E> --step <follow-up> --masks <A anatomy_masks.json> --sites <A> --draw <B> --certificate <C> --library F_render/library/lesion_model_library.json --fingerprint <F fp> --export`.
  - The 3-D `hybrid_volume` (host CT + inserted lesion + 3-D ground-truth mask) lies on A's host geometry: same spacing, origin and LPS direction. The runner asserts this.
  - 2-D slices are exported only at the end.
  - The F-local threshold-mask path stays available but is not used by the chain.
- [ ] **AC-12** (INT.12): *The receipt verifies, and tampering is caught.*
  - Stage `sign` runs `G_provenance.src.receipt fill --commit <commit receipt> --job <C qjr> --job <B qjr> --job <D qjr…> --certificate <C> --witness <D lineage> --witness <D qca> --draw <B> --hybrid <F> --ledger <G ledger>`, then `G_provenance.src.dicom_export <receipt>`, then `G_provenance.src.verify <series> --trusted G_provenance/runs/keys/trusted_keys.json`.
  - The result is `verified`: every upstream was produced after the commit and by the committed code hashes, `voxel_sha256` matches, and the ledger chain holds.
  - One extra check: the runner copies the series, flips one voxel in one slice and reruns `verify`. Expected: `tamper detected` at that slice index. This is a manual-evidence line in `chain.json`. It does not rerun the 20-case R19 repro.
- [ ] **AC-13** (INT.13): *H validates the integrated output.*
  - The runner writes `runs/<…>/cohort.json` in H's manifest format (`H_analysis/src/manifest.py`), listing every real contract file of the chain.
  - Stage `validate` runs `H_analysis.src.lidc_ref --scans all` (cached when present), then `H_analysis.src.report --cohort runs/<…>/cohort.json --lidc-ref <ref run> --tag int`.
  - The result is a `validation_report.json` with all 6 sections filled. Sections whose statistics need n > 1 (MRMC, train-synthetic/test-real) say `n=1 — not powered` instead of a number (Q7).
  - It passes `shared.validate`.
- [ ] **AC-14** (INT.14): *Done-criterion evidence.*
  - `INT_integration/README.md` records the chain run directory, every stage's run directory and its contract outputs, the verify result, the H report path, and every contract mismatch found and how it was fixed (contract → producer → consumer).
  - The epic done-criterion line, "one tumour travels A→H from real files with a verifying receipt", is ticked with these links.

### Status, docs and site

- [ ] **AC-15** (INT.15): *Target states advance by rule.*
  - Each target in state `adapted` whose output the verified chain consumed moves to `integrated` in its letter's `status.json`, and its dossier's Verdict says so: expected #18, #1, #4, #5, #6, #7, #11, #13, #14, #15, #19.
  - Targets that are `dissected` (#8, #9, #12, #17, #20, #21) stay where they are, even when they were exercised. Targets not on the chain path (#2 QeMCMC, #16 projection domain) stay `adapted`.
  - `python -m shared.validate --status` passes.
- [x] **AC-16** (INT.16): *Per-letter Pipeline readiness section.* → `A_placement/README.md:83`, `B_mapping/README.md:96`, `C_certificate/README.md:96`, `D_quantum_growth/README.md:121`, `E_classical_growth/README.md:111`, `F_render/README.md:122`, `G_provenance/README.md:83`, `H_analysis/README.md:94`. The ratings come from the probe and the commit→certify prefix; E, F and H keep their drafts (the chain has not reached them).
  - Each `<L>_<name>/README.md` (A–H) gets `## Pipeline readiness`, placed after "Claim level and honesty notes". It contains:
    - a machine-readable marker on its own line, `<!-- readiness: not-ready|prototype|caveats|production -->`, rendered by the build as a rating badge (AC-19);
    - a 2–4 sentence justification citing chain evidence (run dir, number);
    - a **Weak links** table with columns `Weak link | Kind (component / assumption / data / integration) | Why it limits reliability | Evidence | To strengthen`;
    - a one-line "Used as-is in the chain?" verdict.
  - The ratings are set **after** the chain run, from what it showed. The starting drafts are in §4.
- [x] **AC-17** (INT.17): *Per-letter Future section.* → `## Future` with the 7 subsections, the labelled 5/10/15-year predictions with **Assumptions**, and speculative callouts, in `A_placement/README.md:104`, `B_mapping/README.md:119`, `C_certificate/README.md:121`, `D_quantum_growth/README.md:145`, `E_classical_growth/README.md:135`, `F_render/README.md:146`, `G_provenance/README.md:106`, `H_analysis/README.md:117`. Each one links to the overview for shared material.
  - Each letter README gets `## Future`, after Pipeline readiness, with these fixed subsections:
    1. Aim of the paper(s), one line per target paper code.
    2. Contribution: methods, results, tools and capabilities this letter adds.
    3. Role in cancer detection, with the concrete end goal.
    4. Beyond lungs: other organs, and diagnosis / monitoring / treatment planning / drug response.
    5. Long-term vision: digital twin, labelled speculative, written as a logical chain of steps from the current result.
    6. Predictions: 5 / 10 / 15 years, each with **Assumptions** and an evidence label per claim (`evidence-based` / `extrapolation` / `speculative`). The 15-year horizon assumes fault-tolerant hardware and says what that unlocks (L2/L3).
    7. Risks and obstacles: technical, regulatory, data and validation.
  - Shared, pipeline-wide material lives once in the overview (AC-18). Letter sections link to it rather than repeating it.
- [x] **AC-18** (INT.18): *Overview source for index.html.* → `pipeline-overview.md` (readiness table, edges, weakest 3, `weak-edges` marker; `## Future (whole pipeline)` with the 7 subsections and the `#future` anchor).
  - A new Markdown source `RE/pipeline-overview.md` (Q9) holds `## Pipeline readiness (whole chain)` and `## Future (whole pipeline)`.
  - The readiness part has:
    - a table of all 8 letters (rating badge, one-line why, worst weak link);
    - the edges between letters with the contract file each carries and a per-edge risk;
    - a "**Where the chain is weakest**" ranked list (top 3, each with evidence and a fix);
    - marker `<!-- weak-edges: A>B, B>D, … -->`, which the build uses to highlight edges in the diagram (AC-19).
  - The Future part follows the same 7 subsections as AC-17, written for the whole pipeline.
- [x] **AC-19** (INT.19): *Site build renders readiness and Future natively.* → `shared/site/build.py:63` (marker parse), `:107` (unrated warning), `:73` (heading anchors), `:207` (overview + weak-edges), `:95` (INT page); `shared/site/templates/index.html.j2:17,22,37`; `base.html.j2:17`; `style.css:63`. Future rendering is generic Markdown; there is no Future content yet.
  - `shared/site/build.py`:
    1. parses each letter README's readiness marker into `cards[].readiness` (a missing marker is a build **warning**, shown as "unrated", not an abort);
    2. replaces the marker in the rendered letter page with `<span class="badge ready-<r>">…</span>`;
    3. renders `pipeline-overview.md` into `index.html.j2` below the cards;
    4. passes the `weak-edges` list to the template;
    5. renders `INT_integration/README.md` as `site/INT_integration/index.html`, and nav gains an "INT" entry.
  - `index.html.j2` gets:
    - a readiness chip on each card;
    - an inline SVG pipeline diagram, adapted from `about.html` lines 70–112, with nodes classed `ready-<r>` and weak edges classed `edge-weak`;
    - the rendered overview.
  - `style.css` gets `--ready-not|prototype|caveats|production` colours (light and dark), `.badge.ready-*`, `.chip.evidence|extrapolation|speculative`, `.callout` and `.callout.speculative`, the diagram classes moved from `about.html`, and `details`/`summary` styling.
  - The build stays offline: no CDN, `_EXTERNAL_ASSET` still passes.
- [ ] **AC-20** (INT.20): *Site rebuilt and README status current.* → Done:
  - the build and `--update-readme` both run;
  - the totals come from `status.json`;
  - readiness and Future render on all 8 letter pages and on the index;
  - `about.html` "Where next" links to `index.html#future`;
  - H's duplicate References heading is merged (its CCR text moved into "Contract change requests").

  **Open:** the commit by INT.
  - `python -m shared.site.build --update-readme` succeeds.
  - `index.html` totals match `status.json`. The root README `STATUS` block matches too.
  - Readiness and Future render on all 8 letter pages and on the index.
  - `about.html` "Where next" gets one link to the overview's Future section.
  - H README's duplicate `## References` heading (lines 93 and 98) is merged.
  - `index.html` and `site/` are committed by INT.

---

## 3. Out of Scope (Postponed)

- **Real IBM hardware runs and real certification.** Every number stays simulated. "Certification-ready, not certified" remains the C wording. → Post-epic hardware feature.
- **Coupling D's lineage outcome into the QCA initial condition** (D Q2). The founder is wired (AC-8); the lineage→QCA coupling is not. → Post-INT D follow-up.
- **Projection-domain insertion (#16) and NAEOTOM Alpha (#17) on the chain path.** The chain uses F's image-domain additive-delta path. Running Mayo Siemens raw data through XCIST end-to-end stays future work: #16 has run on a synthetic phantom only, and #17 is not matched.
- **Cohort-scale validation.** The chain produces one tumour. H's 20 hosts × 3 pilot, MRMC power, and a visual Turing test with real readers are deferred. → Post-INT H cohort feature.
- **A's 20-scan reproduction rerun with a juxtapleural contact fix.** This is A's own reproduction debt. INT records it as a weak link only.
- **Statistical upgrades in C:** entropy accumulation (EAT) instead of i.i.d. Hoeffding, and a loophole-free CURBy quantum pulse (CURBy is `isQuantum: False` since 2025-08-22).
- **G production trust:** PKI or HSM keys, and anchoring the ledger head in a public beacon. The stolen-key ledger re-forge stays a documented limit.
- **AI-Rad Companion actual run (#21).** It stays dissected, protocol only.
- **Learned refiners (DiffTumor, MAISI)** stay excluded (privacy-by-construction).
- **Any MVP (`QuantumPhantoms/code/`) change or import.**
- **A non-specialist or Siemens edition of the site.** The audience stays internal (epic §6 decision 9). The Future prose is written for a technically literate non-specialist, as requested, but the site is not split by audience.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Chain runner | New folder `RE/INT_integration/` (README + `src/`). A subprocess orchestrator that calls each letter's CLI and never imports letter code. The run directory lives in the epic's cross-letter `RE/runs/`. |
| Interpreters | A → `/home/peter/anaconda3/envs/qp-re-a/bin/python`. B–H, shared and site build → `sys.executable` (base 3.13). The paths can be overridden with `--python-a` / `--python`. |
| Stage order | commit → certify → place → draw → grow_q → grow_c → render → sign → validate. C runs before A so A's PRNG descends from the certified seed (Q3). The data order A→B→D→E→F→G of epic §7 is unchanged. |
| Simulation mode | `--mode heron` (FakeMarrakesh) for C, B and D in the reference chain. `--mode ideal` is supported for a comparison run. |
| B variant | B-2 joint site × phenotype (the quantum contribution) at K = 8 sites (Q5). |
| Host scan | LIDC-IDRI-0004, A's reference host (r = 4.72 mm run). |
| Seeds | All derived with `shared.seedhash.derive_seed(cert.extracted_seed_hex, "<L>.<purpose>")`. F's existing split is kept and documented: appearance ← certificate, geometry ← `tumor_draw.shape_seed_hex`. Both descend from the certified job. |
| Beacon | Fresh NIST Beacon 2.0 pulse fetched after the commit. Cached fallback is labelled `beacon_fresh: false` (Q4). |
| Contract versioning | One bump to **v1.1.0**. The envelope accepts `1.0.0` and `1.1.0`. CCRs are additive or optional. The C3 rename is done as add `beacon_pulse_id` + deprecate `curby_pulse_id`, read with fallback (Q2). |
| Readiness scale | `not-ready` (Not ready) · `prototype` (Prototype) · `caveats` (Usable with caveats) · `production` (Production-ready). Rule: **no letter is `production`** while the chain is simulation-only and clinically unvalidated. The scale keeps the level so the gap is visible. |
| Readiness source of truth | The letter README marker `<!-- readiness: … -->`. The build aggregates it into index cards and the diagram, so the rating is not duplicated by hand. |
| Index Markdown | New `RE/pipeline-overview.md`, rendered into `index.html.j2`. The root README stays unrendered and links to it (Q9). |
| Evidence labels | Inline chips `<span class="chip evidence">evidence-based</span>`, `…extrapolation…`, `…speculative…`. The 15-year and digital-twin blocks sit in `<div class="callout speculative">`. |
| Diagram | Inline SVG in `index.html.j2`, adapted from `about.html` (same layout: A–D top row, E–H bottom row, contract labels on edges). Node fill comes from the readiness class; `edge-weak` gets a dashed red stroke plus a label. The `about.html` diagram CSS moves into `style.css`, and `about.html` keeps its own copy (hand-written file, Q10). |

**Draft readiness ratings.** These are a starting point only. AC-16 sets the final values from the chain run.

| Letter | Draft | Main reasons (from the letter READMEs) |
|---|---|---|
| A | Prototype | Class proportions not matched (0.56/0.44/0.00 vs 0.33/0.45/0.22, n = 9). The one-voxel contact rule undercounts juxtapleural nodules, so B's class prior is biased. Segmentation takes 25–75 min/scan on CPU. |
| B | Prototype | Heron drift TVD 0.57–0.74, with 33–59 % invalid shots (depth 5 862 / 31 965). The quantum draw is noise-dominated. Rulebook sources are marked *(verify)*. |
| C | Usable with caveats | Accounting validated end to end (Heron 14 726 certified bits). But simulated CHSH certifies nothing, the statistics are i.i.d. rather than EAT, and the beacon was stale or not quantum. |
| D | Prototype | The QCA witness is 3.04σ ideal and fails under Heron noise, so the seed shape is L0. #8 crossover not matched. Memory advantage is small. BP is χ ≤ 8 only. |
| E | Usable with caveats | KT Table 2 matches 3 of 4 stages, only at the paper's site count. Every run so far is on stubs. VDT targets are *(verify)*. |
| F | Usable with caveats | The image-domain path works. #16 is synthetic only, #17 f50 is +47 % off, and the solid-nodule HU is −22 (partial volume). |
| G | Usable with caveats | The verifier catches every edit. But it uses a demo key with no PKI, the ledger has no external anchor, and ordering resolution is 1 s. |
| H | Prototype | R20b not matched (SE 0.0033–0.0051 vs 0.0073). Pilot never run. pyradiomics absent (lite engine). n = 1 in INT. |

**Conventions & notes.**
- **Contract change discipline.** Every mismatch found during the chain is fixed in this order: schema in `shared/contracts/`, then producer, then consumer. It is logged in the `INT_integration/README.md` "Contract fixes" table. Never adapt a consumer silently.
- **Code freeze inside a chain.** G checks that each upstream run was produced by the committed code hashes. Any code edit after `commit` therefore invalidates the chain, and it reruns from `commit`. Contract and producer fixes happen *between* chain attempts, never inside one.
- **No retries on certificate failure** (epic decision 6). The runner stops, and a new chain gets a new commit.
- **Future prose rules.**
  - Every evidence-based sentence cites a repo number (run dir, `status.json` value) or a paper code from `../papers/`.
  - No external statistics without a paper code.
  - Never write "quantum biology", "more realistic because quantum", or "classically impossible" except in the 15-year FT block, and there tied to L2/L3 and labelled speculative.
  - Siemens framing: data credibility and traceability, not security (epic §6).
- **Readiness must be honest about the simulation.** "Usable with caveats" means usable inside this simulated research pipeline, not clinically.
- Match the existing site: same template inheritance (`base.html.j2`), same badge and chip idiom, offline and self-contained, dark-mode variables for every new colour.
- `make_stubs` is rerun after any `shared/*.py` change, because stubs embed `code_hash(shared/)`.
- **Epic notes** (things the epic never decided, decided here):
  - (a) `runrecord` letter parsing for INT;
  - (b) readiness scale and marker;
  - (c) `pipeline-overview.md` as the index source;
  - (d) C before A in the run order.

---

## 5. Data Model (Additions/Modifications)

```text
[Envelope — Modifying]  shared/contracts/_envelope.schema.json
  contract_version   const "1.0.0" → enum ["1.0.0","1.1.0"]   (new writes 1.1.0)

[site_candidates — Modifying]  (CCR-A1)
  sites[].context.nominal_radius_mm   number, optional   (promoted from context.extra)

[rulebook — Modifying]  (CCR-B1)
  params             object, optional   { prior: {free, juxtavascular, juxtapleural}, … }

[compiled_circuit — Modifying]  (CCR-B2, CCR-H2)
  extra              object, optional   (logical order, ancillas)
  state_encoding     string, optional   e.g. "b2-site-x-phenotype"

[quantum_job_record — Modifying]  (CCR-C1 = CCR-D1)
  transpiled_hashes  array<string sha256>, optional   (multi-circuit jobs)
  fake_backend       const "FakeMarrakesh" → enum [FakeMarrakesh, FakeFez, FakeKingston,
                     FakeAachen, FakeTorino]   (CCR-D5; FakeMarrakesh stays the pinned reference)

[certificate — Modifying]  (CCR-C2, CCR-C3)
  chsh_S             max 2.8285 → max 4   (statistical Ŝ can exceed Tsirelson)
  chsh_S_lower       number, optional
  eps                object, optional   { est: number, ext: number }
  beacon_pulse_id    string, optional   (new name)
  curby_pulse_id     string, optional, DEPRECATED (read fallback only)

[witness_record — Modifying]  (CCR-D3, CCR-D4, CCR-D7 docs)
  chsh               object, optional   { S, n_rounds, settings }
  claim_level        const "L1" → enum ["L0","L1"]   (L0 when witness fails)
  mi_network         description clarified: index = logical qubit order

[memory_advantage_record — Modifying]  (CCR-D2)
  d_kl_bits_per_symbol  number, optional

[quantum_lineage — Modifying]  (CCR-D6 docs)
  fate               description clarified: one entry per (generation, cell)

[growth_trajectory — Modifying]  (E CCR 1–4)
  snapshots[].summary   object, optional   (volume_mm3, n_cells per layer)
  draw_id               string, optional
  population NPZ key and origin_mm_lps = voxel (0,0,0) centre — documented in VOLUMES.md

[scanner_fingerprint — Modifying]  (CR-F1, CR-F2)
  local_nps          object, optional   { ref: npz path, roi_mm, n_rois }
  ssp                object, optional   { fwhm_mm, ref }

[hybrid_volume — Modifying]  (CCR-H3)
  tumor_type         string, optional
  size_mm            number, optional

[receipt — Modifying]  (CCR-G2, CCR-G3)
  commit.code_hashes  object<letter, sha256>, optional
  fill.voxel_sha256   string sha256, optional

[ledger_entry — Modifying]  (CCR-G1)
  kind               enum + "commit"

[validation_report — Modifying]  (CCR-H1)
  $defs for the 6 sections (realism, radiomics, turing, utility, drift, certificate+baseline);
  additionalProperties stays true (loose sub-schemas)

[New, INT-local file — not a contract]  runs/<ts>-e2e-<tag>/chain.json
  chain_id, host, mode, beacon_fresh, commit_receipt,
  stages[]: { stage, argv, interpreter, run_dir, outputs{contract: path},
              exit_code, started_utc, finished_utc },
  verify_result, tamper_check{slice, detected}, validation_report, mismatches[]

[New, doc-level marker — not a contract]
  <!-- readiness: not-ready|prototype|caveats|production -->   in each <L>/README.md
  <!-- weak-edges: X>Y, … -->                                   in pipeline-overview.md
```

Migration: there is no database. Stubs are regenerated (`make_stubs`). Old v1.0.0 E/F runs still validate through the envelope enum. Letter runs are regenerated by the chain.

---

## 6. File Plan (Concrete Changes)

All paths are relative to `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| **Contracts / shared** | | |
| Modify | `shared/__init__.py` | `CONTRACT_VERSION = "1.1.0"` |
| Modify | `shared/contracts/_envelope.schema.json` | Version const → enum `["1.0.0","1.1.0"]` |
| Modify | `shared/contracts/site_candidates.schema.json` | CCR-A1 `nominal_radius_mm` |
| Modify | `shared/contracts/rulebook.schema.json` | CCR-B1 `params` |
| Modify | `shared/contracts/compiled_circuit.schema.json` | CCR-B2 `extra`, CCR-H2 `state_encoding` |
| Modify | `shared/contracts/quantum_job_record.schema.json` | CCR-C1/D1 `transpiled_hashes`, CCR-D5 `fake_backend` enum |
| Modify | `shared/contracts/certificate.schema.json` | CCR-C2 `chsh_S` max 4, `chsh_S_lower`, `eps`; CCR-C3 `beacon_pulse_id` + deprecate `curby_pulse_id` |
| Modify | `shared/contracts/witness_record.schema.json` | CCR-D3 `chsh`, CCR-D4 `claim_level` enum, CCR-D7 description |
| Modify | `shared/contracts/memory_advantage_record.schema.json` | CCR-D2 `d_kl_bits_per_symbol` |
| Modify | `shared/contracts/quantum_lineage.schema.json` | CCR-D6 `fate` description |
| Modify | `shared/contracts/growth_trajectory.schema.json` | E CCR 1, 3 (`snapshots[].summary`, `draw_id`) |
| Modify | `shared/contracts/scanner_fingerprint.schema.json` | CR-F1 `local_nps`, CR-F2 `ssp` |
| Modify | `shared/contracts/hybrid_volume.schema.json` | CCR-H3 `tumor_type`, `size_mm` |
| Modify | `shared/contracts/receipt.schema.json` | CCR-G2 `commit.code_hashes`, CCR-G3 `fill.voxel_sha256` |
| Modify | `shared/contracts/ledger_entry.schema.json` | CCR-G1 `kind` + `"commit"`; version const → enum |
| Modify | `shared/contracts/target_status.schema.json` | Version const → enum |
| Modify | `shared/contracts/validation_report.schema.json` | CCR-H1 `$defs` per section (loose) |
| Modify | `shared/contracts/VOLUMES.md` | E CCR 2 (`population` NPZ key), E CCR 4 (`origin_mm_lps` = voxel (0,0,0) centre) |
| Modify | `shared/contracts/README.md` | v1.1.0 changelog table (CCR → schema → producer → consumer) |
| Modify | `shared/runrecord.py` | `_letter_of`: `INT_integration` → `"INT"` |
| Modify | `shared/validate.py` | CCR-G4 `--trusted <file>` for receipts |
| Modify | `shared/stubs/make_stubs.py` | Write v1.1.0 fields: `beacon_pulse_id`, ledger `kind: "commit"` entry, `voxel_sha256` |
| Regenerate | `shared/stubs/**` | `python -m shared.stubs.make_stubs` |
| Modify | `shared/README.md` | Note v1.1.0 and that INT applied every CCR |
| Modify | `shared/templates/LETTER_README.template.md` | Add `## Pipeline readiness` (marker + weak-links table) and `## Future` (7 subsections) skeletons |
| **Producers / consumers** | | |
| Modify | `A_placement/src/place.py` | Write `context.nominal_radius_mm` (CCR-A1) |
| Modify | `B_mapping/src/rulebook.py` | Write `params.prior` from `class_prior.json` (CCR-B1) |
| Modify | `B_mapping/src/map.py` | Write `compiled_circuit.extra` + `state_encoding` (B2, H2); `transpiled_hashes` |
| Modify | `C_certificate/src/certify.py` | Write `beacon_pulse_id`, `chsh_S_lower`, `eps`, `transpiled_hashes` (C1–C3) |
| Modify | `C_certificate/src/beacon.py` | Pulse selection "latest after a given UTC time" (used by the chain after commit) |
| Modify | `D_quantum_growth/src/io_contracts.py` | Founder derived from `tumor_draw` (AC-8); read `beacon_pulse_id` with fallback |
| Modify | `D_quantum_growth/src/grow.py` | Pass the derived founder into the lineage stage |
| Modify | `D_quantum_growth/src/lineage.py` | Accept a founder preset; write `transpiled_hashes`, witness `chsh` block (D1, D3) |
| Modify | `D_quantum_growth/src/qca.py` | `claim_level: "L0"` on witness fail (D4); `transpiled_hashes` |
| Modify | `D_quantum_growth/src/memory_advantage.py` | Write `d_kl_bits_per_symbol` (D2) |
| Modify | `D_quantum_growth/src/bp.py` | `--circuit <compiled_circuit.json>` input so BP runs on B's circuits (AC-9) |
| Modify | `E_classical_growth/src/io_contracts.py` | Write `snapshots[].summary`, `draw_id` (E CCR 1, 3) |
| Modify | `E_classical_growth/src/params_lung.json` | Only if the LIDC check (AC-10) puts `vessel_threshold` / `lung_hu_bounds` outside the measured range |
| Modify | `F_render/src/fingerprint.py` | Write `local_nps`, `ssp` (CR-F1/F2) |
| Modify | `F_render/src/render.py` | Write `tumor_type`, `size_mm` (H3); assert A-mask geometry equals host geometry |
| Modify | `F_render/src/io.py` | Read A's `anatomy_masks` lobes/vessels in place of the F-local masks when `--masks` is given; read `beacon_pulse_id` with fallback |
| Modify | `G_provenance/src/ledger.py` | Write `kind: "commit"` for commits (G1) |
| Modify | `G_provenance/src/receipt.py` | Write `commit.code_hashes`, `fill.voxel_sha256` (G2, G3); accept repeated `--job` |
| Modify | `G_provenance/src/verify.py` | Pass the trusted list into `shared.validate` (G4); read `beacon_pulse_id` with fallback |
| Modify | `H_analysis/src/manifest.py` | Read `hybrid_volume.tumor_type` / `size_mm` (H3) |
| Modify | `H_analysis/src/certstats.py` | Read `beacon_pulse_id`, `chsh_S_lower` (C2, C3) |
| Modify | `H_analysis/src/report.py` | Emit `n=1 — not powered` for sections needing n > 1 (Q7) |
| **Chain runner (new)** | | |
| New | `INT_integration/__init__.py` | Package marker |
| New | `INT_integration/src/__init__.py` | Package marker |
| New | `INT_integration/src/chain.py` | 9-stage subprocess orchestrator, `chain.json`, `--from` / `--reuse`, validation after each stage, stop-on-fail |
| New | `INT_integration/src/stages.py` | One function per stage that builds its argv from upstream outputs; the run-dir discovery rule |
| New | `INT_integration/src/cohort.py` | Writes H's cohort manifest from `chain.json` |
| New | `INT_integration/src/tamper_check.py` | Copy the series, flip one voxel, run `G verify`, record the slice index |
| New | `INT_integration/README.md` | Purpose, how to run, chain run record, "Contract fixes" table, done-criterion evidence |
| **Letter docs** (each gets `## Pipeline readiness` + `## Future`, CCR section marked applied/declined, statuses) | | |
| Modify | `A_placement/README.md`, `A_placement/status.json`, `A_placement/dossiers/18-*.md` | Readiness, Future, CCR-A1 applied; #18 → integrated |
| Modify | `B_mapping/README.md`, `B_mapping/status.json`, `B_mapping/dossiers/01-*.md` | Readiness, Future, BP number (AC-9), B1/B2 applied; #1 → integrated |
| Modify | `C_certificate/README.md`, `C_certificate/status.json`, `C_certificate/dossiers/04-*.md`, `C_certificate/dossiers/05-*.md` | Readiness, Future, C1–C3 applied; #4, #5 → integrated |
| Modify | `D_quantum_growth/README.md`, `D_quantum_growth/status.json`, `D_quantum_growth/dossiers/06-*.md`, `D_quantum_growth/dossiers/07-*.md` | Readiness, Future, founder mapping, D1–D7 applied; #6, #7 → integrated |
| Modify | `E_classical_growth/README.md`, `E_classical_growth/status.json`, `E_classical_growth/dossiers/11-*.md` | Readiness, Future, "Checked on LIDC (INT)" note, CCR 1–4 applied; #11 → integrated |
| Modify | `F_render/README.md`, `F_render/status.json`, `F_render/dossiers/13-*.md`, `F_render/dossiers/14-*.md`, `F_render/dossiers/15-*.md` | Readiness, Future, CR-F1/F2 applied, seed split documented; #13–#15 → integrated |
| Modify | `G_provenance/README.md`, `G_provenance/status.json`, `G_provenance/dossiers/19-*.md` | Readiness, Future, G1–G4 applied; #19 → integrated |
| Modify | `H_analysis/README.md` | Readiness, Future, H1–H3 applied, duplicate References heading merged, link to the INT report |
| **Site** | | |
| New | `pipeline-overview.md` | Whole-chain readiness (table, edges, weakest-3, `weak-edges` marker) + whole-pipeline Future |
| Modify | `shared/site/build.py` | Readiness marker parse + badge replace, overview render, `weak-edges`, INT page + nav, warn on unrated |
| Modify | `shared/site/templates/index.html.j2` | Readiness chip per card, SVG diagram, rendered overview block |
| Modify | `shared/site/templates/base.html.j2` | Nav entry "INT" |
| Modify | `shared/site/style.css` | `--ready-*` colours (light/dark), `.badge.ready-*`, `.chip.evidence/extrapolation/speculative`, `.callout`, diagram classes, `details`/`summary` |
| Modify | `about.html` | "Where next": link to `index.html#future` (an anchor id set in the template) |
| Modify | `README.md` | Link to `pipeline-overview.md` and `INT_integration/README.md`; `STATUS` block refreshed by `--update-readme` |
| Regenerate | `index.html`, `site/**` | `python -m shared.site.build --update-readme` (committed by INT) |
| Modify | `epic-reverse-engineering.md` | §2 INT row Status → done, with links to the chain run; §4 note `RunRecord` / ledger rows (W deferral) |

Dossier filenames use the existing `<NN>-<slug>.md` pattern in each `dossiers/` folder. The implementer opens the exact file there (the slugs come from `status.json` `dossier`).

---

## 7. Manual Verification (No Tests)

Run everything from `RE/` with base Python unless stated.

- [ ] **Verify AC-1 / AC-3:** `python -m shared.stubs.make_stubs && python -m shared.validate --stubs && python -m shared.validate --status`. Expect all to pass. `grep -c '"1.1.0"' shared/stubs/*/*.json` > 0. One old E run, `python -m shared.validate E_classical_growth/runs/<old>/growth_trajectory/growth_trajectory.json`, still passes (v1.0.0 accepted).
- [ ] **Verify AC-2:** after the chain run, `jq 'has("beacon_pulse_id"), has("chsh_S_lower")' <C certificate.json>` → `true true`. `jq '.kind' <G ledger first line>` → `"commit"`. Every letter README's CCR section shows `applied in v1.1.0 (INT)` or `declined: …`.
- [ ] **Verify AC-4 / AC-14:** `python -m INT_integration.src.chain --host LIDC-IDRI-0004 --mode heron --tag ref`. The chain exits 0, and `runs/<ts>-e2e-ref/chain.json` lists 9 stages, each with `exit_code: 0`. Then `python -m INT_integration.src.chain --from render --reuse place=<A run> … --tag resume` reuses the earlier stages without recomputation. A reuse of a pre-commit run is refused with a message.
- [ ] **Verify AC-5:** `chain.json` → `beacon_fresh: true`, and the pulse time stamp is later than the commit `committed_utc`. Offline check: disconnect the network, run `--from certify`, and expect `beacon_fresh: false` plus the honesty note.
- [ ] **Verify AC-5 (fail path):** `python -m INT_integration.src.chain … --certify-args "--settings classical"` gives S ≤ 2, so the runner stops at `certify` with exit 2, writes a new line in `C_certificate/runs/rejections.jsonl`, and runs no later stage.
- [ ] **Verify AC-6 / AC-7:** the B `tumor_draw.site_id` appears in A's `sites.json`. A's `run.json` `seed_hex` = `derive(cert seed, "A.place")` (recompute in a Python one-liner with `shared.seedhash`).
- [ ] **Verify AC-8:** D's `quantum_lineage.json` records `founder_from: <B tumor_draw path>` and the preset name. A rerun with an ideal-mode B draw of a different type produces a different preset.
- [ ] **Verify AC-9:** B's README shows a BP `fidelity_vs_sim` number with "simulated: Heron-class noise", linked to a `simulability_report.json` that passes `shared.validate`.
- [ ] **Verify AC-10:** E's README has the "Checked on LIDC (INT)" note with the measured values. E's `growth_trajectory.json` → `"stub": false`, with ≥ 2 snapshots (baseline, +90 d).
- [ ] **Verify AC-11:** open `F_render/runs/<chain render>/hybrid_ct.nii.gz` in a viewer (or `SimpleITK` one-liner). Spacing, origin and direction equal A's `host_ct`. The lesion sits at the drawn site. The exported 2-D slices exist only under the export folder.
- [ ] **Verify AC-12:** `python -m G_provenance.src.verify <series> --trusted G_provenance/runs/keys/trusted_keys.json` → `verified`. `chain.json.tamper_check.detected` is `true`, with the flipped slice index reported.
- [ ] **Verify AC-13:** `python -m shared.validate <H validation_report.json>` passes. Open `report_detail.json`: 6 sections present, and the n-dependent ones say `n=1 — not powered`.
- [ ] **Verify AC-15:** `python -m shared.validate --status` passes. `jq '[.targets[] | select(.state=="integrated") | .number]' */status.json` lists exactly the AC-15 set.
- [ ] **Verify AC-16 / AC-17:** `grep -c '^## Pipeline readiness\|^## Future' */README.md` → 2 per letter (A–H). Each readiness section has a marker line and a weak-links table. Each Future section has the 7 subsections, 3 horizons each carry **Assumptions**, and every prediction line carries an evidence chip. `grep -n 'quantum biology\|classically impossible\|more realistic because quantum'` across the READMEs + `pipeline-overview.md` returns only negated or FT-labelled uses.
- [ ] **Verify AC-18 / AC-19 / AC-20:** `python -m shared.site.build --update-readme` finishes without errors and without an "unrated" warning. Open `index.html` in a browser (file://, offline):
  - the totals match `status.json`;
  - each card shows a readiness chip;
  - the SVG diagram colours nodes by rating and dashes the `weak-edges` edges;
  - the overview renders below the cards with a working `#future` anchor.
  
  Open each `site/<L>/index.html`: a rating badge replaces the marker, and the Future section's speculative callouts are styled. Toggle the OS dark mode: every new colour stays readable. `about.html` "Where next" links to the index Future.
- [ ] **Edge case:** delete one README marker temporarily and run the build. It finishes with a warning, and that card shows "unrated". Restore the marker.
- [ ] **Edge case:** edit any `B_mapping/src/*.py` after `commit` and run `--from draw`. G `fill` (or the runner's reuse check) must report a code-hash mismatch. Revert the edit.

---

## 8. Open Questions

- [x] **Q1: Which CCRs to accept?** *Proposed:* accept all 33 as listed in §5. All are additive or relax a constraint. H1 is done as loose `$defs` (`additionalProperties: true`) so H's current output stays valid. None are declined.
- [x] **Q2: C3 rename (`curby_pulse_id` → `beacon_pulse_id`): hard rename or add + deprecate?** *Proposed:* add + deprecate. New writes use `beacon_pulse_id`; consumers read it with a fallback; old runs stay valid. Remove the old field in a later contract version.
- [x] **Q3: Run C before A, so A's placement PRNG also descends from the certified seed?** *Proposed:* yes. The order becomes commit → C → A → B → D → E → F → G → H. The epic's data order is unchanged, because A has no upstream.
- [x] **Q4: Fresh beacon pulse after the commit (network needed), or the cached pulse?** *Proposed:* fetch fresh. If offline, fall back to the cache with `beacon_fresh: false` and an honesty note. Do not block the chain.
- [x] **Q5: Which B variant and mode draws the chain tumour?** *Proposed:* B-2 at K = 8 with Heron-class noise, the quantum contribution, accepting its high drift as a recorded weak link. A comparison chain with `--mode ideal` is optional, not required.
- [x] **Q6: D founder mapping from the draw.** *Proposed:* draw `type` × `margin` → one of D's existing fate-angle presets (table in D's README), with the lineage seed from `shape_seed_hex`. Lineage → QCA coupling stays out of scope.
- [x] **Q7: H on n = 1. Is the single chain tumour enough for "H full validation"?** *Proposed:* yes for INT. All 6 sections are produced, and n-dependent statistics are marked `n=1 — not powered`. A multi-tumour cohort (e.g., 3 tumours, one per placement class) is a post-INT feature.
- [x] **Q8: Create `qp-re-h` for real pyradiomics?** *Proposed:* no. INT uses radiomics-lite (no new installs), which is noted as an H weak link.
- [x] **Q9: Where does the index Markdown live?** *Proposed:* new `RE/pipeline-overview.md`, rendered into `index.html` and linked from the root README. The root README stays the AI entry point and stays unrendered.
- [x] **Q10: Does `about.html` reuse the shared diagram CSS?** *Proposed:* no. `about.html` stays hand-written with its own inline style; INT adds only one "Where next" link. The diagram CSS is copied into `style.css` for the index.
- [x] **Q11: Do any letter CLIs lack `--tag`, making run-dir discovery ambiguous?** *Proposed:* the runner first passes `--tag` where the CLI supports it. Otherwise it takes the single new `runs/*` directory created after the stage started, and fails loudly if there are 0 or more than 1. No sessions run in parallel during INT, so this is safe.
- [x] **Q12: Future scope on index vs letters.** *Proposed:* the index gets the full whole-pipeline Future (cancer detection, beyond lungs, digital twin, 5/10/15 years). Each letter gets a focused Future on its own paper(s), and links to the index for shared parts instead of repeating them.
- [x] **Q13: Branch / commit strategy.** *Proposed:* work on branch `re-INT` in the main checkout (no other session runs), with commits per block:
  1. contracts + stubs;
  2. producer/consumer;
  3. runner + chain evidence;
  4. statuses + docs;
  5. site.

  Then merge to `main`. The pre-existing unrelated change to `../README.md` stays unstaged.
- [x] **Q14: Rating wording.** *Proposed:* the user's four levels exactly (Not ready / Prototype / Usable with caveats / Production-ready). Explicit rule: nothing is Production-ready while the chain is simulation-only, so the top level is shown as the target, not used.

---

## 9. Post-Implementation Notes

**Scope.** The developer asked for the full-pipeline command with its steps, without running the whole pipeline,
and with the focus on finding weak links. Built: the runner `python -m INT_integration.src.chain` (9 stages,
`--dry-run`, `--probe` gap finder, `--stop-after`, `--from`/`--resume`/`--reuse`, `--allow-gaps`), the Pipeline
readiness sections A–H, `pipeline-overview.md` (whole-chain readiness, edges, weakest 3, `weak-edges`), the site build
support for both, `INT_integration/README.md`, and the root README links.

**Ran.** Probe `runs/20261029-185947-probe-gaps` (exit 4, blocked at G.fill), and 4 real `commit → certify`
prefixes in Heron mode. All passed: Ŝ 2.722–2.762, 15 668–17 869 bits. The reuse refusal (exit 3) and the
missing-upstream stop (exit 1) were exercised. `shared.site.build --update-readme` rebuilt the site with no unrated
warning. No automated tests.

**Findings that change the plan.**
- G `fill --job` is single-value, so the chain cannot pass `sign` as planned (AC-12).
- D's founder ignores the draw, and `bp --circuit` is missing (AC-8, AC-9).
- AC-5's "fresh pulse after commit" fails in practice: `/pulse/last` lags 2–3 min, and repeated fetches time out. The runner now re-fetches up to 10× and falls back. A reused pulse gives an identical seed.
- AC-10's `vessel_threshold` is a push count, not HU.
- The commit freezes A–F `.py` only.
- `fetch_pulses` and `render --export` write into git-tracked folders.

Full list: `INT_integration/README.md`.

**Deferred.**
- AC-1–3: contract v1.1.0, CCRs, stubs.
- AC-2: producer/consumer edits.
- AC-5–15: full chain run, BP for B, LIDC check result, H report, statuses → integrated.
- AC-20: the commit itself.

**Future sections (second pass, 2026-10-29).**
- Written from the letter results and the paper codes in `../papers/`. No external statistic is used without a paper code.
- Every claim carries an evidence-based / extrapolation / speculative chip.
- The 15-year blocks and the digital-twin blocks sit in `callout speculative`.
- The forbidden phrases are absent.
- G's 15-year block notes that fault-tolerant hardware *breaks* Ed25519 (post-quantum migration).

The tracked beacon cache was restored after the prefix runs.

**Site restructure (developer request, 2026-10-29).**
- **About merged into the index.** `about.html` (hand-written, W) is merged into the generated index: the intro, the A–H contract-flow diagram and the explainer sections. The sections live in `shared/site/templates/explainer.html.j2`; their styles moved to `style.css`. `about.html` is deleted. This reverses Q10 and the AC-20 "about link".
- **Future is its own page.** The whole-pipeline Future moved from `pipeline-overview.md` into its own source, `future.md`, rendered as `site/future.html`, and the nav links to it as "Future". The letter READMEs link to `../future.md`.
- **Navigation is now Index · Future · INT.** The "About" and "Contracts" links and the A–H letter links are removed. Contracts are still reachable from the index ("The pipeline, A to H" and "Where to go next"); letters are reachable from the cards and the diagrams.
- **Older plans left unchanged.** Plans written before INT (W, A–H, epic) still mention `about.html` as their own record.
- **Index simplified.**
  - Cards and diagram nodes show plain step labels (`STEP` in `shared/site/build.py`), not the technical letter titles.
  - The "The pipeline, A to H" contract-flow diagram is removed. The Pipeline readiness diagram now takes its place, followed by the contracts / seed-chain paragraph.
- **Claim ladder moved.** The L0–L3 table and the "never claim" callout were removed from the index explainer and appended to `future.md` as a closing "Disclaimer" section.
- **Overview trimmed.** `pipeline-overview.md` now holds only "Where the chain is weakest" and the `weak-edges` marker. The scale note, how the ratings were set, the per-letter rating table and the edge-risk table were removed from the index; per-letter ratings stay in each letter README.
- **Index intro rewritten.**
  - Sections: "What we aim to achieve", "Why it matters", "How", and an open "Why quantum?" box.
  - The "brings detection forward by a few years" claim is labelled extrapolation and conditional on clinical validation.
  - The "Why quantum?" box separates the classical parts (A, E–H, and B today), the parts that are quantum now (C via the CHSH bound, D memory advantage; simulated) and the quantum-ready parts (speculative).
  - Heading anchors now unescape HTML entities.
- **"Why it matters" and "Why quantum" reworked.**
  - "Why it matters" is cut to 4 sentences.
  - "Why quantum" is now a plain paragraph in body font: D is the quantum-only goal (108-qubit plan, claim level L2, speculative); C and B are described as the other quantum modules.
  - A Disclaimer follows: classical simulation on laptops and supercomputers (tensor networks / BP, [HW04]), so the work is about building a quantum-ready pipeline. It links to the Future page and the claim ladder.
- **Cards merged into the readiness diagram.**
  - The A–H cards and the total state badges are removed from the index.
  - Each diagram node shows letter, stage, plain description and rating, and a hover title with folder + target count.
  - "How" is removed; "Why quantum" and "Disclaimer" are shortened. Card CSS is removed.
- **Index sections removed.**
  - Removed: "Where the chain is weakest", "Simulation only" and "How the work is organised".
  - `pipeline-overview.md` is no longer rendered; its `weak-edges` marker still colours the diagram.
  - Links that used to point at it now go to the INT gap list or to the index diagram.
- **D-108 L2 plan made visible.**
  - The index "Why quantum" now opens as the plan: one large circuit that maps how a tumour starts growing.
  - `future.md` adds "Planned: L2 in D at 108 qubits": the 4 conditions and the fallback result (a measured simulability boundary).
  - The L2 row of the claim ladder now says "planned: D at 108 qubits".
  - Title is "Quantum Phantoms (live document)" with a progress-tracking note.
