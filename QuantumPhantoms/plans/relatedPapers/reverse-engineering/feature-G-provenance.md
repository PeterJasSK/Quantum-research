# Feature G — Sign / provenance: commit-before-draw receipt, Ed25519, hash-chained ledger, DICOM tag + CT-GAN tamper test (target #19)

**Epic:** [`epic-reverse-engineering.md`](./epic-reverse-engineering.md) (Approved, 2026-10-28). G is a wave-2 letter (epic §7), built in its own worktree `re-G`. It depends on W (committed). It benefits from merged C (`249a4fe`, ledger template in dossier #5) and merged F (`16c195d`, real `hybrid_volume`), but runs on `shared/stubs/` by default.
**Feature ID:** G
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Complete (approved 2026-10-29, implemented 2026-10-29)

> **Technical constraints / core directive.**
> - **Stack.** Python 3.13 (conda base) with libraries already installed: cryptography 44 (Ed25519), pydicom 3.0.2, SimpleITK 2.5.6, numpy 2.4, scipy 1.15, scikit-image 0.25, matplotlib 3.10, jsonschema 4.23. **No new installs.** No torch / TensorFlow / GPU on this machine, so **no GAN is trained or run** (Q2).
> - **Classical only.** G runs no quantum job and makes no quantum claim (claim level `n/a`). It hashes, signs and verifies what other letters produced.
> - **Scope of writes.** The session writes only inside `RE/G_provenance/` and this plan, where `RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. `shared/` is frozen and is imported, never edited. Nothing is imported from `QuantumPhantoms/code/` (the MVP) or from any other letter: upstream letters are consumed **only through their contract files** (stubs by default, real paths via CLI flags).
> - **Commands** run with `RE/` as the working directory.
> - **Framing.** Traceability / data credibility, not security vocabulary (epic §6). The tamper test is a *traceability validation*.
> - **No automated tests.** Verification is manual, plus the reproduction step.

---

## 1. Why (Step Goal)

**Before.**
- `G_provenance/` is a W skeleton: a pre-filled README, `status.json` with #19 at `listed`, and an empty dossier.
- `shared/stubs/receipt/receipt.json` and `shared/stubs/ledger_entry/ledger.jsonl` exist, but they are made in one shot by `make_stubs` with a hard-coded key (`sha256(b"qp-re-stub-key")`). Nothing commits **before** a job, nothing checks time order, nothing binds the actual CT voxels, and no DICOM file exists anywhere in `RE/` (no `pydicom` use).
- `shared.validate` already checks a receipt's Ed25519 signature against the key **inside the receipt** and a ledger file's internal chain. It cannot tell an attacker's re-signed receipt from ours, and it never looks at an image.
- C's dossier #5 left a "Ledger template for G" mapping table and three rules: commit is a separate earlier entry; verify recomputes, never trusts a stored hash; verify reports which check failed at which index.

**After.** G is a standalone provenance tool with four stages and a verifier, matching the epic §5 receipt state machine
`committed (BEFORE job) → job run → filled → signed (Ed25519) → ledgered → { verified | tamper detected }`:
1. **Commit** (before any job): hash the rulebook and the producing code, sign `{commit, fill: null}`, append it to the ledger. The ledger index and time stamp prove the commitment came first.
2. **Fill + sign + ledger** (after the job and render): bind job IDs, counts, S / H_min, witness refs, parameters, seed and the hybrid volume, including a **canonical voxel hash** of the 3-D hybrid CT; check that every upstream was produced after the commit and by the committed code; sign; append.
3. **DICOM export with provenance tags**: write the 3-D hybrid volume as a CT DICOM series (final export, epic "3-D only" rule) whose private tags carry the signed receipt, the bound parameters and the ledger entry.
4. **Verify**: from a DICOM series (or the NIfTI + JSON), recompute everything against a **pinned trusted key** and the ledger, and report each failing check with its location (slice index, ledger index).
5. **Target #19, CT-GAN as a tamper test (Mirsky G01)**: dissect the paper; re-implement its 3-D injection/removal pipeline (cube cut, 1:1:1 mm rescale, histogram equalisation, 16³ centre mask, in-paint, inverse steps, AWGN touch-up from voxels < −600 HU, sigmoid-Gaussian merge eq. 1–2 with α = 500, β = 70, paste) with a **classical in-painter in place of the GAN**; tamper signed series and show that verification flags 100 % of injections and removals and localises the tampered slices, with 0 false positives on untampered round-trips. This reproduces the paper's §7.2 countermeasure claim ("the best way to detect this attack is to have the scanner sign each scan with a digital signature"); the human-reader numbers (99 % / 94 % misdiagnosis) are reported, not reproduced (Q3).
6. **Docs and status**: README, dossier #19, figures and `status.json` updated.

INT can then put a real receipt at the end of the A→G chain, and H gets `Receipt` / `LedgerEntry` instances and a tamper-detection result to report.

---

## 2. Acceptance Criteria

- [x] **AC-1** (G.1) — *Canonical hashes.*
  - `voxel_sha256(array_zyx, meta)` = sha256 of `canonical_json({shape, spacing_mm_xyz, origin_mm_lps, dtype:"int16"})` ‖ the array as little-endian int16 (z, y, x), after `shared.volumes.read_volume` (LPS). Identical for the NIfTI and for the DICOM series written from it.
  - `slice_sha256s(array_zyx)` = one sha256 per axial slice (z order), used for tamper localisation.
  - `producer_code_hashes(letters)` = `{letter: shared.seedhash.code_hash([<letter dir>, shared])}` for every producing letter folder that exists (same formula as `shared.runrecord`, so it equals each producer's `produced_by.code_hash`); `commit.code_hash` = `hash_json(producer_code_hashes)` (CCR-G2).
  → `G_provenance/src/hashing.py`; qiskit-free, uses `shared.seedhash` / `shared.volumes` only.
  - **Evidence:** `G_provenance/src/hashing.py:32,37,46,56`
- [x] **AC-2** (G.2) — *Signing key and trust.*
  - `python -m G_provenance.src.keys init` generates a random Ed25519 key once into `G_provenance/runs/keys/signing_key.pem` (PKCS8, unencrypted, gitignored via `runs/`) and writes `G_provenance/runs/keys/trusted_keys.json` = `[{key_id, public_key_b64, created_utc, note:"demo key, not a PKI"}]`. It refuses to overwrite an existing key.
  - `key_id` = first 16 hex of sha256(raw public key).
  - `load_signer()`, `trusted_public_keys()`; verification accepts a signature only if `public_key_b64` is in the trusted list (Q4).
  → `G_provenance/src/keys.py`.
  - **Evidence:** `G_provenance/src/keys.py:40,56,63`
- [x] **AC-3** (G.3) — *Commit before the job.*
  - `python -m G_provenance.src.receipt commit --rulebook <rulebook.json>` (default: the stub) writes a run dir `G_provenance/runs/<ts>-commit/` via `shared.runrecord.start_run`, with `receipt.json` in state `committed`: `commit = {rulebook_hash, code_hash, committed_utc}`, `fill: null`, and `signature` over `canonical_json({commit, fill: null})` (the schema's `signed_over` string holds for `fill = null`).
  - `rulebook_hash` is the rulebook's own `rulebook_hash` field, re-verified with `hash_json(doc minus rulebook_hash/created_utc/produced_by)` before use (same rule as `shared.validate`).
  - `commit_manifest.json` (letter-local) lists the per-letter code hashes behind `code_hash`.
  - The committed receipt is appended to the ledger as a `kind: "receipt"` entry (CCR-G1 asks for `kind: "commit"`), and the run prints `committed: ledger index i`.
  - Output passes `python -m shared.validate <receipt.json>`.
  → `G_provenance/src/receipt.py` + `src/ledger.py`.
  - **Evidence:** `G_provenance/src/receipt.py:81 (commit), src/ledger.py:46`
- [x] **AC-4** (G.4) — *Fill + order + code checks.*
  - `python -m G_provenance.src.receipt fill --commit <committed receipt.json> --job <quantum_job_record.json> --certificate <certificate.json> --witness <witness_record.json>... --draw <tumor_draw.json> --hybrid <hybrid_volume.json>` (all default to the stubs).
  - Every input passes `shared.validate` first; a failing input aborts with its errors.
  - `fill` fields: `job_ids` (job record), `counts_sha256` = `hash_json(counts)`, `chsh_S` / `h_min_per_round` (certificate), `witness_refs` (file_refs), `seed_hex` = certificate `extracted_seed_hex`, `hybrid_volume_sha256` = sha256 of `hybrid_volume.json`, `params_sha256` = sha256 of `canonical_json(bound_params)` (AC-5).
  - **Order check:** every non-stub input's `created_utc` ≥ `commit.committed_utc`; the committed receipt's ledger index < the new entry's index.
  - **Code check:** every non-stub input's `produced_by.code_hash` ∈ the committed per-letter hashes.
  - **Rulebook check:** the draw / compiled circuit's rulebook hash (where the contract carries one) equals `commit.rulebook_hash`.
  - A stub input (`stub: true`) is exempt from the order and code checks; the exemption is written to `fill_report.json` as `"order not provable (stub input)"` (Q5).
  - Certificate `status: "fail"` → no receipt is filled; the run logs `"certificate failed, nothing to sign"` and exits 0 (consistent with epic decision 6).
  - Any failed check → no signature, `fill_report.json` lists the failures, exit code 1.
  - **Evidence:** `G_provenance/src/receipt.py:145 (order / code / rulebook / stub exemption / failed certificate)`
- [x] **AC-5** (G.5) — *Bound parameters.* `bound_params.json` (letter-local, its sha256 = `fill.params_sha256`) = `{tumor_draw_sha256, certificate_sha256, job_record_sha256, hybrid: {voxel_sha256, slice_sha256s[], grid}, lesion_mask_voxel_sha256, host_voxel_sha256, insertion}`. This is how the receipt binds the actual voxels until CCR-G3 adds a dedicated field.
  - **Evidence:** `G_provenance/src/receipt.py:127`
- [x] **AC-6** (G.6) — *Sign + ledger.*
  - After a clean fill, the receipt is signed (`state: "signed"`), the ledger entry is appended (`receipt_sha256` = sha256 of the final `receipt.json` file), and the receipt is re-written with `state: "ledgered"`.
  - Because `receipt_sha256` must cover the final file, the order is: write receipt with `state: "ledgered"` and signature → hash file → append entry. (The signature covers only `{commit, fill}`, so `state` may change without re-signing.)
  - `upstream[]` holds `upstream_ref`s to every consumed input plus the committed receipt.
  - `ledger.py`: `append(entry_body)` computes `entry_hash` = sha256(canonical_json(entry − entry_hash)), `prev_hash` = previous `entry_hash`, genesis `prev_hash` = 64 × "0". The ledger lives at `G_provenance/runs/ledger.jsonl` (persistent across runs, gitignored); a genesis entry is written on first use.
  - `python -m shared.validate G_provenance/runs/ledger.jsonl` and `<receipt.json>` both print OK.
  → `G_provenance/src/ledger.py`, `src/receipt.py`.
  - **Evidence:** `G_provenance/src/receipt.py:58,208-215, src/ledger.py:46`
- [x] **AC-7** (G.7) — *DICOM export with provenance tags.*
  - `python -m G_provenance.src.dicom_export <ledgered receipt.json> [--out DIR]` reads `hybrid_ct.nii.gz` via the receipt's `hybrid_volume.json`, and writes one CT Image Storage file per axial slice (pydicom 3, explicit VR little endian, int16 `PixelData`, `RescaleSlope` 1 / `RescaleIntercept` 0, `ImagePositionPatient` / `ImageOrientationPatient` / `PixelSpacing` / `SliceThickness` from the LPS grid).
  - Synthetic markers: `ImageType` `DERIVED\SECONDARY\SYNTHETIC`, `PatientName` `SYNTHETIC^QP-RE`, `PatientID` = `draw_id`, new UIDs derived deterministically from the receipt hash (`pydicom.uid.generate_uid(entropy_srcs=[...])`), no host-scan patient attributes copied.
  - Private block, group `0x0011`, creator `QP-RE G PROVENANCE`: `receipt_json` (canonical, UT), `bound_params_json` (UT), `ledger_index` (UL), `ledger_entry_hash` (LO), `slice_index` (UL), `slice_sha256` (LO).
  - Default `--out` = `G_provenance/runs/<ts>-dicom/series/` (gitignored, can contain LIDC voxels when F used an LIDC host).
  → `G_provenance/src/dicom_export.py`.
  - **Evidence:** `G_provenance/src/dicom_export.py:46,107`
- [x] **AC-8** (G.8) — *Verifier.*
  - `python -m G_provenance.src.verify <series dir | receipt.json> [--ledger G_provenance/runs/ledger.jsonl]` runs and prints each check as `OK` / `FAIL <where>`:
    1. `signature` — Ed25519 over `canonical_json({commit, fill})` with the receipt's key;
    2. `trusted_key` — key in `trusted_keys.json`;
    3. `params` — sha256(bound_params) = `fill.params_sha256`;
    4. `voxels` — recomputed `voxel_sha256` from the pixels = bound value; on mismatch, `slices` lists every z whose recomputed slice hash differs;
    5. `geometry` — grid from the DICOM / NIfTI = bound grid;
    6. `ledger_chain` — `shared.validate.ledger_errors` is empty;
    7. `ledger_entry` — the entry at `ledger_index` has `receipt_sha256` = sha256 of the canonical receipt and `entry_hash` = the tag value;
    8. `commit_first` — the receipt's committed entry exists at a smaller ledger index with the same `commit`.
  - Verdict line `VERIFIED` or `TAMPER DETECTED: <checks>`; exit 0 / 2. A JSON report goes to `G_provenance/runs/<ts>-verify/verify_report.json`.
  - For a series, the receipt is read from the tags and re-serialised canonically; the per-file `receipt_json` must be identical on all slices (else `FAIL receipt_consistency`).
  → `G_provenance/src/verify.py`.
  - **Evidence:** `G_provenance/src/verify.py:53 (8 checks + receipt_consistency), main at :140`
- [x] **AC-9** (G.9) — *CT-GAN-style tamper module (GAN-free).*
  - `G_provenance/src/ctgan_tamper.py` implements G01 §5 steps on a 3-D array: (2) cut a cuboid around the target sized so that (3) rescaling to 1:1:1 mm gives 32³; (4–5) histogram equalisation + normalisation to [−1, 1]; (6) zero the central 16³; (7) **in-paint classically** (Q2): *removal* = harmonic (Laplace) fill of the masked region from its boundary, plus lung-parenchyma noise; *injection* = in-paint the removal fill, then add a Gaussian-edged solid nodule (diameter drawn in [10, 16] mm, HU ≈ 0–60, like G01's ≥ 10 mm trial nodules); (8–10) un-normalise, un-equalise, spline-rescale (`scipy.ndimage.zoom`, order 3) to the original spacing; (11) touch-up: AWGN with σ = std of the original cuboid's voxels < −600 HU, then merge with W_{α,β}(x) = G(x) / (1 + e^{−(x+α)/β}), α = 500, β = 70, merge = W·x_g + (1 − W)·x_r (eq. 1–2); (12) paste.
  - `inject(vol, meta, center_zyx, rng)` and `remove(vol, meta, center_zyx, rng)`; removal targets the lesion centre from F's `lesion_mask`; injection targets a lung voxel ≥ 15 mm from the lesion, from `anatomy_masks` (stub `lung` mask).
  - Every random choice comes from `shared.seedhash.rng(<receipt seed>, "G.tamper.<k>")`.
  - **Evidence:** `G_provenance/src/ctgan_tamper.py:87,125,130`
- [x] **AC-10** (G.10) — *Reproduction #19.*
  - `python -m G_provenance.repro.r19_ctgan_tamper [--n 20]` builds one signed, ledgered, DICOM-exported hybrid (stubs by default, or `--receipt` for a real one), then for k = 1..n makes one injection and one removal copy of the series (pixel tamper written back into the DICOM files, tags untouched — the G01 attacker model), plus 4 non-pixel attacks: (a) edit `fill.seed_hex` in the tag; (b) (a) + re-sign with a fresh attacker key; (c) (b) + rewrite the ledger file consistently with the forged receipt; (d) delete the commit entry from the ledger and re-chain.
  - Controls: the untampered series and a re-save after changing an unbound tag (`InstitutionName`) must both verify.
  - Prints a table: attack → detected (y/n), failing checks, localised slices vs ground-truth tampered slices (Jaccard). Expected: 2n/2n pixel tampers detected with slice Jaccard 1.0; (a) by `signature`; (b) by `trusted_key`; (c) by `trusted_key` (and, honestly, **only** by it: a full re-forge with a stolen key + rewritten ledger is undetectable without an external anchor — documented as the limit, future fix = anchor the ledger head in a public beacon pulse, C dossier #5 last row); (d) by `commit_first` / `ledger_chain`; controls 0 false positives.
  - Stealth numbers (for the dossier, not gates): mean / max |ΔHU| inside and outside the tampered cuboid, and confirmation that the plain DICOM header of a tampered file is unchanged.
  - Writes `G_provenance/figures/r19-ctgan-tamper.png` (exported axial slices: original / injected / removed / |Δ| map, plus the verifier's per-slice FAIL strip) and `r19-detection-table.png`, and updates `status.json` #19 `reproduced{}`.
  - **Evidence:** `G_provenance/repro/r19_ctgan_tamper.py:89; figures/r19-*.png`
- [x] **AC-11** (G.11) — *Dossier #19.* `dossiers/19-ct-gan-tamper-test.md` fills all 8 fixed sections: G01 attack model (PACS data-in-motion / at-rest), the 13-step pipeline, eq. 1–2 with α / β, training-set facts (32³ samples, 16³ mask, pix2pix-style 3-D cGAN), published results (99 % injected → malign, 94 % removed → healthy, 60 % / 87 % after being told, 100 % fooled screening AI, page refs), §7.2 countermeasures (scanner signature, DICOM Digital Signatures, watermarking); our classical-in-painter substitution and why (no GAN, privacy, licence check per Q2); verdict; what to reuse (H's tamper statistic, INT's real chain, DICOM Digital Signatures Sequence as the standard-conformant upgrade).
  - **Evidence:** `G_provenance/dossiers/19-ct-gan-tamper-test.md`
- [x] **AC-12** (G.12) — *README + status.*
  - `G_provenance/README.md`: "How to run" (key init → commit → [run C / E / F] → fill → export → verify → repro), "Reproduced result vs. paper", "Claim level and honesty notes" (n/a; traceability, not security; demo key; limit of AC-10c; simulated upstream numbers keep their sim labels inside the receipt), "Contract change requests" CCR-G1..G4 (§5).
  - `status.json` #19 → `adapted` with `reproduced{quantity, paper_value, our_value, agreement, sim_mode: "n/a", figure}`, `claim_level: null`, `figures[]`, `updated`.
  - `python -m shared.validate --status` passes. `python -m shared.site.build` previews locally; the site is **not** committed.
  - **Evidence:** `G_provenance/README.md, G_provenance/status.json`

---

## 3. Out of Scope (Postponed)

- **Real upstream chain** (B rulebook, D witness / lineage, real A→F files in one run): **INT**. G runs on stubs, with an optional real C certificate + F hybrid to exercise the order check (§7).
- **Ledger anchoring in a public beacon / CURBy / Twine chain** (closes the AC-10c gap): future work after INT; noted in the dossier.
- **Standard DICOM Digital Signatures Sequence (FFFA,FFFA) / MAC parameters, PKI, key rotation, HSM**: future; G uses a private tag block and a pinned demo key (Q6).
- **Training or running the CT-GAN GAN** (pix2pix 3-D cGAN, LUNA16 training): not built (no torch / GPU; privacy). Classical in-painter only.
- **Radiologist / AI-detector reader studies** (G01's 99 % / 94 % / 100 %): **H** owns reader-style validation (in-context visual Turing test); G only reports the published values.
- **Cohort-level receipt / tamper statistics**: **H**.
- **Watermarking**: not built; dossier note only.
- **Any change to `shared/`** (CCR-G1..G4): **INT**. Committing `index.html` / `site/`: **INT**.

---

## 4. Technical Decisions

Epic §3 and the frozen W decisions are adopted as-is: file-only contracts, ownership rules, no MVP imports, honesty gates, seed chain, logging, 3-D only (2-D only at export), no tests.

| Component | Choice / Implementation |
|---|---|
| Signature | Ed25519 via `cryptography` (`Ed25519PrivateKey`), over `canonical_json({commit, fill})` exactly as the frozen schema + `shared.validate._verify_signature` define it |
| Key | random per-machine demo key in `G_provenance/runs/keys/` (gitignored), pinned in `trusted_keys.json`; never the stub key |
| Ledger | append-only `G_provenance/runs/ledger.jsonl`, frozen `ledger_entry` contract, chain checked with `shared.validate.ledger_errors` |
| Commit-before-draw | committed receipt signed with `fill: null` and ledgered as its own entry before the job; order proved by ledger index + `created_utc` |
| Code hash | `hash_json({letter: code_hash([letter, shared])})` over producing letters (matches each producer's `produced_by.code_hash`) |
| Voxel binding | canonical int16 LPS voxel hash + per-slice hashes in `bound_params.json`, bound via `params_sha256` |
| DICOM | pydicom 3, CT Image Storage, one file per axial slice, private group 0x0011 creator `QP-RE G PROVENANCE` |
| Tamper pipeline | G01 §5 pre/post-processing verbatim (32³ @ 1 mm, 16³ mask, equalise, spline order 3, AWGN σ(< −600 HU), α = 500, β = 70), classical in-paint (harmonic fill via `scipy.sparse.linalg.spsolve` on the 16³ mask, or `skimage.restoration.inpaint_biharmonic` per slice as fallback) |
| Randomness | `shared.seedhash.rng(seed_hex, "G.<purpose>")` only |
| Run records | `shared.runrecord.start_run("G_provenance", <tag>)` for commit / fill / dicom / verify / repro |
| Figures | matplotlib → PNG in `G_provenance/figures/` (committed) |

**Conventions & Notes:**
- Module split: `hashing`, `keys`, `ledger`, `receipt`, `verify` are image-library-free except `hashing` (SimpleITK via `shared.volumes`); `dicom_export` and `verify` are the only `pydicom` users; `ctgan_tamper` is numpy/scipy only.
- Verification never trusts a stored hash: every hash is recomputed from bytes / pixels (C dossier #5 rule 2) and every failure names its check and location (rule 3).
- Pattern-only analogues (read, never import): `C_certificate/src/beacon.py` `verify_chain` (per-index failure reporting); `shared/stubs/make_stubs.py:402-430` (receipt + ledger construction). The MVP is off-limits.
- **Scale.** Stub hybrid ~ small phantom; LIDC hybrid ≈ 512² × ~130–300 slices int16 ≈ 70–150 MB → n = 20 injections + 20 removals = 40 series copies; repro writes copies to a temp dir under `runs/` one at a time and deletes each after verifying, so disk stays ≈ 2 series.
- **Note for the epic (§4/§5):** the frozen contracts lack a `commit` ledger kind, a per-letter code-hash map and a voxel-hash field; G works around all three locally (CCR-G1..G3). The epic's "+ DICOM tag" is decided here as a private tag block (Q6).

---

## 5. Data Model (Additions/Modifications)

No contract is added or changed (`shared/` is frozen). G produces instances of `receipt` and `ledger_entry`, plus letter-local files.

```text
[Existing contract — produced by G]  receipt.json   (receipt.schema.json v1.0.0)
  committed run:  state "committed", fill null, signature over canonical_json({commit, fill: null})
  final run:      state "ledgered", fill{...}, signature over canonical_json({commit, fill})
  commit.code_hash        = hash_json(commit_manifest.code_hashes)            (CCR-G2)
  fill.counts_sha256      = hash_json(job_record.counts)
  fill.params_sha256      = sha256(canonical_json(bound_params))              (CCR-G3)
  fill.hybrid_volume_sha256 = sha256_file(hybrid_volume.json)
  upstream[]              = job record, certificate, witness(es), tumor_draw, hybrid_volume, committed receipt

[Existing contract — produced by G]  G_provenance/runs/ledger.jsonl   (ledger_entry v1.0.0)
  index 0 genesis; commit entries and final entries both kind "receipt"     (CCR-G1)

[Letter-local, run dirs only (gitignored)]
  commit_manifest.json   {rulebook_path, rulebook_hash, code_hashes{letter: hex64}, ledger_index}
  bound_params.json      {tumor_draw_sha256, certificate_sha256, job_record_sha256,
                          hybrid{voxel_sha256, slice_sha256s[], grid{shape, spacing_mm_xyz, origin_mm_lps}},
                          lesion_mask_voxel_sha256, host_voxel_sha256, insertion{}}
  fill_report.json       {checks[{name, ok, detail}], stub_exemptions[]}
  series/*.dcm           CT slices + private block (0011,xx) "QP-RE G PROVENANCE"
  verify_report.json     {target, checks[{name, ok, where}], verdict}
  keys/signing_key.pem, keys/trusted_keys.json
  r19 table              G_provenance/runs/<ts>-r19/detection.json
```

**Contract change requests** (recorded in the README; INT decides):
- **CCR-G1:** `ledger_entry.kind` gains `"commit"` so the commit-before-draw entry is typed. *Workaround:* `kind "receipt"`, distinguished by the receipt's `state: "committed"`.
- **CCR-G2:** `receipt.commit` gains `code_hashes{letter: hex64}`. *Workaround:* `commit_manifest.json` + `code_hash` = hash of that map.
- **CCR-G3:** `receipt.fill` gains `voxel_sha256` (+ optional `slice_sha256s`) for the hybrid CT. *Workaround:* bound via `params_sha256` → `bound_params.json`.
- **CCR-G4:** `shared.validate` receipt check gains an optional trusted-key list (today it trusts the key embedded in the receipt). *Workaround:* `G_provenance.src.verify` pins keys.

---

## 6. File Plan (Concrete Changes)

`RE/` = `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. Everything is inside `RE/G_provenance/` except this plan.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `RE/G_provenance/src/hashing.py` | `voxel_sha256`, `slice_sha256s`, `grid_of`, `producer_code_hashes`, `commit_code_hash` (AC-1) |
| New | `RE/G_provenance/src/keys.py` | CLI `init`; `load_signer`, `trusted_public_keys`, `key_id` (AC-2) |
| New | `RE/G_provenance/src/ledger.py` | `ensure_genesis`, `append`, `read`, `find_receipt`, `verify_chain` (wraps `shared.validate.ledger_errors`) (AC-6) |
| New | `RE/G_provenance/src/receipt.py` | CLI `commit` / `fill`; input validation, order / code / rulebook checks, `bound_params`, sign, ledger, run record (AC-3..AC-6) |
| New | `RE/G_provenance/src/dicom_export.py` | NIfTI → CT DICOM series with private provenance block; `read_series(dir)` → (array, meta, tags) for the verifier (AC-7) |
| New | `RE/G_provenance/src/verify.py` | CLI verifier, 8 checks, slice localisation, report (AC-8) |
| New | `RE/G_provenance/src/ctgan_tamper.py` | G01 pipeline with classical in-painter: `inject`, `remove`, `merge_weights`, `equalize` / `unequalize` (AC-9) |
| New | `RE/G_provenance/repro/r19_ctgan_tamper.py` | end-to-end demo + 2n pixel tampers + 4 forgery attacks + 2 controls, table, figures, `status.json` update (AC-10) |
| New | `RE/G_provenance/figures/r19-ctgan-tamper.png` | generated, committed |
| New | `RE/G_provenance/figures/r19-detection-table.png` | generated, committed |
| Modify | `RE/G_provenance/dossiers/19-ct-gan-tamper-test.md` | fill all 8 sections (AC-11) |
| Modify | `RE/G_provenance/README.md` | How to run, reproduced result, honesty, CCR-G1..G4 (AC-12) |
| Modify | `RE/G_provenance/status.json` | #19 → `adapted`, `reproduced{}`, figures (AC-12) |
| Modify | `RE/feature-G-provenance.md` | §9 Post-Implementation Notes only |

**Untouched:** `shared/`, the other letters, the epic, the targets list, `about.html`, `index.html`, `site/`, `.gitignore`, the MVP.

---

## 7. Manual Verification (No Tests)

All commands run from `RE/` (inside the `re-G` worktree) with conda-base `python`.

- [x] **Verify AC-2:** `python -m G_provenance.src.keys init` → key + `trusted_keys.json` under `G_provenance/runs/keys/`; a second `init` refuses. `git status --short G_provenance` shows no key file.
- [x] **Verify AC-3:** `python -m G_provenance.src.receipt commit` → prints `committed: ledger index 1` on a fresh ledger (0 = genesis); `python -m shared.validate <run>/receipt.json` OK; `state` = `committed`, `fill` = null.
- [x] **Verify AC-4 (real order):** after the commit, run `python -m C_certificate.src.certify --mode ideal` (C is on `main`), then `python -m G_provenance.src.receipt fill --commit <commit receipt> --certificate C_certificate/runs/<ts>-chsh-ideal/certificate.json --job C_certificate/runs/<ts>-chsh-ideal/quantum_job_record.json` (other inputs stubs) → passes; `fill_report.json` lists stub exemptions only for stub inputs. Then use a C certificate produced **before** a fresh commit → `FAIL order`, exit 1, no signature.
- [x] **Verify AC-4 (code check):** commit, then edit a comment in any `C_certificate/src/*.py`, re-run C, fill → `FAIL code_hash (C)`. Revert the edit.
- [x] **Verify AC-4 (fail certificate):** fill with `C_certificate` output from `--settings classical` → "certificate failed, nothing to sign", exit 0, no ledger append.
- [x] **Verify AC-5 / AC-6:** after a clean fill, `python -m shared.validate <receipt.json>` and `python -m shared.validate G_provenance/runs/ledger.jsonl` print OK; `sha256sum bound_params` matches `fill.params_sha256` (via `python -c` with `canonical_json`); last ledger line's `receipt_sha256` = `sha256sum receipt.json`.
- [x] **Verify AC-7:** `python -m G_provenance.src.dicom_export <receipt>` → N slice files; `python -c "import pydicom; d=pydicom.dcmread('<first>.dcm'); print(d.ImageType, d.PatientName, d[0x0011,0x0010].value)"` → `DERIVED\SECONDARY\SYNTHETIC`, `SYNTHETIC^QP-RE`, `QP-RE G PROVENANCE`. Load the series in SimpleITK and compare to the NIfTI: identical array and grid.
- [x] **Verify AC-8:** `python -m G_provenance.src.verify <series>` → 8 × OK, `VERIFIED`, exit 0. Same on the `receipt.json` path.
- [x] **Verify AC-9 / AC-10:** `python -m G_provenance.repro.r19_ctgan_tamper --n 20` → table with 40/40 pixel tampers detected, slice Jaccard 1.0, attacks (a)–(d) detected by the expected checks, both controls `VERIFIED`; open `figures/r19-ctgan-tamper.png`: injected nodule and removed lesion are visible on the exported slices and the |Δ| map is confined to the cuboid.
- [x] **Verify AC-11 / AC-12:** dossier has all 8 sections filled; `python -m shared.validate --status` → 8 × OK; `python -m shared.site.build` and open `index.html`: #19 shows `adapted`; then `git checkout -- index.html site/` (nothing from the site committed).
- [x] **Edge case — isolation:** `grep -rnE "QuantumPhantoms/code|from (A|B|C|D|E|F|H)_" G_provenance/` prints nothing; `git diff --stat main -- shared/` empty.
- [x] **Edge case — framing:** `grep -niE "attack(er)?s? (on|against) (hospital|patient)|security product" G_provenance/README.md` empty; README speaks of traceability; the AC-10c limit is stated.
- [x] **Edge case — privacy:** when the hybrid comes from an LIDC host, the DICOM series exists only under `G_provenance/runs/` (`git check-ignore` confirms).

---

## 8. Open Questions

- [x] **Q1: How does the receipt bind the actual CT voxels?** The frozen `fill.hybrid_volume_sha256` hashes only `hybrid_volume.json`, which points at a gzip NIfTI whose bytes cannot be recomputed from DICOM pixels. *Resolved (accepted default):* canonical int16 voxel hash + per-slice hashes in `bound_params.json`, bound through `params_sha256` (AC-5), plus CCR-G3 for a dedicated field.
- [x] **Q2: GAN or no GAN for the CT-GAN tamper?** No torch / TF / GPU, privacy rule (GAN trained on patient scans), and the CT-GAN repo licence is unchecked. *Resolved (accepted default):* re-implement every non-learned step of G01 verbatim and replace step 7 by a classical in-painter (harmonic fill; injection adds a parametric nodule). The tamper test needs realistic *pixel edits under the G01 attacker model*, not GAN realism; the signature check is independent of how the pixels were changed. The implementer checks `github.com/ymirsky/CT-GAN`'s licence and records it in the dossier, but uses no code or weights from it.
- [x] **Q3: What counts as the "published number" for #19?** G01's numbers are reader-study results (99 % / 94 %, 60 % / 87 %, 100 % AI) that need radiologists and the trained GAN. *Resolved (accepted default):* reproduce G01's §7.2 claim quantitatively (detection rate of injection / removal by signed provenance, expected 100 %, with slice localisation and 0 false positives) and the step-11 parameters (α = 500, β = 70, σ from < −600 HU); report the reader numbers as "not reproduced — H's reader test territory". State → `adapted`.
- [x] **Q4: Key management.** *Resolved (accepted default):* one random demo Ed25519 key per machine in `G_provenance/runs/keys/` (gitignored), trust by pinned public-key list; the stub key `sha256(b"qp-re-stub-key")` is never trusted. If a key committed in the repo is preferred (so INT on another machine verifies the same receipts), commit only `trusted_keys.json` outside `runs/` — say so.
- [x] **Q5: Commit-before-draw with stub inputs.** Stub files carry `created_utc` 2026-10-28T00:00Z, before any commit. *Resolved (accepted default):* stub inputs are exempt from the order / code checks, recorded as `"order not provable (stub input)"`; the order check is demonstrated for real with a C run done after the commit (§7, AC-4).
- [x] **Q6: Which "DICOM tag"?** *Resolved (accepted default):* private block group 0x0011, creator `QP-RE G PROVENANCE`, full canonical receipt + bound params + ledger entry hash + per-slice hash in every slice file. The standard DICOM Digital Signatures Sequence (PS3.15 / PS3.3 C.12.1) is named in the dossier as the conformant upgrade, not built.
- [x] **Q7: Which code does `commit.code_hash` cover?** *Resolved (accepted default):* every producing letter folder that exists at commit time among A–F (+ `shared/`), one `code_hash([letter, shared])` each, combined by `hash_json`; G's own code is recorded in the run record, not in the commit.
- [x] **Q8: Default real host?** *Resolved (accepted default):* stubs by default (fast, no patient data); `--hybrid F_render/runs/<ts>-lidc0001/hybrid_volume.json` optional for one LIDC-host demonstration figure, kept in `runs/`, with only the exported figure (synthetic insert region, no full patient slice beyond the cuboid crop) committed. Say if any LIDC-derived figure must stay out of git.
- [x] **Q9: Where does this plan live?** *Resolved (accepted default):* `RE/feature-G-provenance.md` (epic §3 layout and the W / A / C / E / F precedent), not `tasks/plans/`. Commit it on `main`, then `git worktree add ../qp-re-G -b re-G` before `/implement-feature`.

---

## 9. Post-Implementation Notes

Built in worktree `re-G`; all code in `RE/G_provenance/`, nothing in `shared/` or other letters touched.

- **Result (stub phantom, n = 20):** 20/20 injections and 20/20 removals flagged by `voxels` with exact slice Jaccard 1.00; forgeries (a) `signature`, (b) `trusted_key`, (c) `trusted_key` only (the documented limit), (d) `commit_first`; both controls verify. Order and code checks verified by hand with real C runs (pass after commit; `FAIL order` for a C run made before a fresh commit; `FAIL code_hash` after a one-comment edit to `C_certificate/src/chsh.py`, reverted; a `fail` certificate signs nothing, exit 0, ledger unchanged).
- **Deviations / additions (all local):**
  - `bound_params.json` also carries `commit_receipt{ledger_index, sha256, receipt}` so the verifier can run `commit_first` from the DICOM tags alone (AC-5 listed the other keys).
  - Receipt files are written as canonical JSON (compact, no newline) so `sha256sum receipt.json` equals the ledger's `receipt_sha256` and tag re-serialisation is stable.
  - Fill's code check compares per letter (`produced_by.letter`), a subset of "∈ the committed hashes"; a letter folder absent at commit time cannot produce accepted inputs.
  - Verifier adds a 9th check `receipt_consistency` (series only). Attacks (a) and (b) also trip `ledger_entry` (receipt no longer matches the ledger); (d) also trips `ledger_entry`.
  - CT-GAN merge weight W is evaluated on the voxel-wise maximum of generated and original cuboid (paper text does not say which cuboid); noted in the dossier. First `remove` / `inject` call spends ~4 s on a cached sparse LU.
  - Injection site is the lung voxel pick; the stub noise-free phantom gives σ(< −600 HU) = 0, so the AWGN step is a no-op there (it works on real hosts).
  - The first r19 run per receipt writes a new commit + fill (and ledger entries) into the persistent `runs/ledger.jsonl`.
- **CT-GAN repo licence:** MIT (checked with `gh api`, 2026-10-29); no code or weights used.
- **Follow-ups for INT:** decide CCR-G1..G4; anchor the ledger head in a public beacon pulse; DICOM Digital Signatures Sequence instead of the private block; run once on a real LIDC hybrid from F (`--hybrid`, `--receipt`) — not done here (Q8 default: stubs).
- No automated tests written or run; flake8 clean (max line 130).
