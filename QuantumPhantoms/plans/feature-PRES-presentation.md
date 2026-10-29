# Feature PRES — Quantum Phantoms presentation: one tumour, step by step, in real CT (Reveal.js)

**Epic:** none. This is a standalone feature with no owning epic, at the developer's request. It **consumes** the outputs of
the reverse-engineering epic ([`relatedPapers/reverse-engineering/epic-reverse-engineering.md`](relatedPapers/reverse-engineering/epic-reverse-engineering.md),
Approved) and of INT ([`feature-INT-integration.md`](relatedPapers/reverse-engineering/feature-INT-integration.md)), and changes neither.
**Feature ID:** PRES
**Author:** Claude (Opus)
**Date:** 2026-10-29
**Status:** Approved (by developer, 2026-10-29; Q1–Q8 defaults accepted)

> **Technical constraints / core directive.**
> - **Stack.**
>   - Python 3 (conda base: numpy, SimpleITK, matplotlib, PIL, imageio, pydicom, jinja2; all already installed).
>   - **Reveal.js 5.1.0** vendored once into the repo, so the deck runs offline. This is the only new dependency (Q1).
>   - A run uses the existing letter CLIs only.
> - **Read-only on the RE epic.** PRES never edits `relatedPapers/reverse-engineering/**`, and never imports letter
>   code or `QuantumPhantoms/code/` (the MVP). It runs the INT chain and letter CLIs as subprocesses, then reads their
>   contract files.
> - **Simulation only, classical mode allowed.** Every quantum number on a slide carries its sim label. Claim
>   ladder rules apply: no "more realistic because quantum", no "quantum biology", no "classically impossible".
> - **Offline and self-contained.** The deck opens from `file://` with no network. A single-file "compiled" HTML is
>   also produced.
> - **No automated tests.** Verification is manual: open the deck and check each slide and image.

---

## 1. Why (Step Goal)

**Before.**
- The pipeline A→H exists and is documented on the site, but nobody can *see* it work on one patient.
- Only three committed figures show real CT:
  - `A_placement/figures/18-host-sites.png` (LIDC-IDRI-0004);
  - `F_render/figures/render-lidc0001-{lung,mediastinal}.png` (LIDC-IDRI-0001).
- Everything else is plots, synthetic phantoms or stub masks. E's lung figures, for example, show masks on a stub phantom
  without CT pixels.
- No slide deck exists.

**After.**
- A **Reveal.js deck** in `QuantumPhantoms/presentation/` tells the story of **one tumour on one real LIDC host**,
  step by step:
  - the empty lung;
  - anatomy and candidate sites (A);
  - the drawn tumour (B);
  - the certified seed (C);
  - the quantum seed shape (D);
  - growth from baseline to follow-up (E), shown **as it appears in CT** over several time points;
  - the scanner-matched render (F);
  - the signed DICOM and the tamper check (G);
  - the validation numbers (H).
- Every slide uses the **same axial slice and crop**, so the viewer watches the lung change.
- A **hero image** (1920×1080) looks like a real CT scan: the final hybrid slice, large, with a strip of eight step
  thumbnails (A→H) along the bottom.
- `python -m presentation.build` regenerates all of it from one recorded story run. `--single-file` compiles a
  self-contained HTML deck to send around.

---

## 2. Acceptance Criteria

### Story run (the data behind the slides)

- [ ] **AC-1** (PRES.1): *One recorded story run produces every step's real contract files on one host.*
  - Command: `python -m presentation.story_run --host LIDC-IDRI-0004 [--mode ideal] [--chain-dir <existing chain run>]`.
  - It runs the INT chain as a subprocess from the RE folder:
    `python -m INT_integration.src.chain --host LIDC-IDRI-0004 --mode ideal --allow-gaps --stop-after sign --tag story`
    (Q7: H's `validate` stage is not part of the story run).
  - It then runs F `render --step <k>` once per extra growth time point (Q4: 6 time points) on the chain's E trajectory,
    so growth can be shown in CT.
  - It writes `presentation/story/story.json` (§5) with the chain run dir, every needed contract path, the extra hybrid
    volumes, and the chosen slice and crop.
  - `--chain-dir` reuses an existing chain run without recomputing (A's segmentation costs ~25–75 min once).
  - If a chain stage fails, the story run stops and names the stage. It never fakes a step. The gap is listed
    on the INT page.

### Frames (the images)

- [ ] **AC-2** (PRES.2): *One frame per step, on the same slice and crop, in CT look.*
  - `presentation/build/frames.py` reads `story.json` and writes PNGs into `presentation/assets/frames/`.
  - Shared geometry: the axial slice through the final lesion centre, a crop of ±60 mm (Q5), lung window
    W1500/L−600 (as `F_render/src/export_slices.py:24`), 1600 px wide.

  | Frame file | Step | Content |
  |---|---|---|
  | `00-host.png` | — | raw host CT slice |
  | `A-anatomy.png` | A | lungs/lobes/vessels/airway contours + candidate sites by placement class + chosen site |
  | `B-draw.png` | B | the chosen site with a ring of the drawn diameter + a label card (type, size, margin) |
  | `C-seed.png` | C | host slice unchanged + certificate stamp (Ŝ, S_low, certified bits, pulse id, sim label) |
  | `D-seed-shape.png` | D | D's 3-D seed shape (`seed_shape.npz`) at the site, as a coloured overlay on CT |
  | `E-growth-<k>.png` (k = 1…6) | E | tumour states (proliferating / dormant / necrotic) as overlays at each time point |
  | `F-ct-<k>.png` (k = 1…6) | F | the **hybrid CT** at each time point: no overlay, pure CT look |
  | `F-mediastinal.png` | F | final hybrid in mediastinal window W400/L40 |
  | `F-diff.png` | F | hybrid − host difference map |
  | `G-tamper.png` | G | one exported DICOM slice, plus the flipped-voxel tamper copy with G's verdict per slice |
  | `H-validation.png` | H | H's report figures if the validate stage ran, else H's committed R20a/R20b figures, labelled |

- [ ] **AC-3** (PRES.3): *Growth is shown as it happens.*
  - `presentation/build/frames.py` also writes two animations:
    - `assets/anim/growth-ct.webp`: the F CT frames, baseline → follow-up;
    - `assets/anim/growth-states.webp`: the E state overlays.
  - Both are written with imageio at ~2 fps, looping.
  - The deck shows each one with a still-frame fallback.

- [ ] **AC-4** (PRES.4): *The hero image looks like a real CT scan and shows all steps.*
  - `presentation/build/hero.py` writes `presentation/assets/hero.png` (1920×1080):
    - the final hybrid axial slice, full field of view, on a black background;
    - a thin unobtrusive marker at the lesion (no labels on the image itself);
    - a bottom strip of eight 1:1 thumbnails `00-host → A → B → C → D → E(final) → F → G`, each captioned with its
      plain step label from the index (*Where a tumour sits*, *What kind of tumour*, …).
  - A small corner caption reads *"LIDC-IDRI-0004 (CC BY 3.0) · synthetic nodule · simulated"*.

### Deck

- [ ] **AC-5** (PRES.5): *The Reveal.js deck tells the story in order.*
  - `presentation/build/deck.py` renders `presentation/templates/deck.html.j2` (Jinja2) into
    `presentation/index.html`, which loads the vendored Reveal.js from `presentation/vendor/reveal.js/`.
  - Slides, in order:
    1. **Title:** hero image.
    2. **Aim and why it matters:** the text from the index intro.
    3. **The pipeline:** the readiness diagram, the same SVG as the index (plain step labels).
    4. **The host:** `00-host`.
    5. **One slide per step A→H.** Each has the frame, one-line "what happened", one key number from the run, and a
       quantum/classical badge. A slide may use Reveal fragments to step from the previous frame to the next.
    6. **Growth in CT:** the `growth-ct` animation, then baseline vs follow-up side by side.
    7. **Final render:** lung and mediastinal windows plus the diff.
    8. **Provenance:** the tamper slide.
    9. **Validation:** what H measured, and that n = 1 here (`ValidationPlan.md` as the next step).
    10. **Why quantum:** D at 108 qubits as the plan, plus the disclaimer.
    11. **Future:** horizons in one slide, linking to the Future page.
    12. **Credits and disclaimers:**
        - LIDC-IDRI CC BY 3.0 attribution;
        - paper codes used;
        - "simulation only";
        - the claim ladder in one line.
  - Every number on a slide is read from `story.json` or the run's contract files. **No hand-typed numbers.**

- [ ] **AC-6** (PRES.6): *It looks native and good.*
  - `presentation/theme/qp.css` is a Reveal theme built from the RE site tokens (`shared/site/style.css`).
  - It uses the dark palette: `--bg #15171a`, `--ink #e7e5e0`, `--accent #8ab4e0`, `--quantum #b29df5`, and the readiness
    colours. This keeps CT readable.
  - It uses the system font stack (no web fonts), 16:9 at 1920×1080, and CT images on pure black.
  - Code and step badges reuse the site's chip and badge idiom.

- [ ] **AC-7** (PRES.7): *It compiles to one file and runs offline.*
  - `python -m presentation.build --single-file` writes `presentation/dist/quantum-phantoms.html`, with Reveal JS/CSS,
    the theme and every image inlined (base64). The approach mirrors `QuantumPhantoms/web/index.html`.
  - No `http(s)://` asset references remain; the build checks this like the site's `_EXTERNAL_ASSET` rule.
  - The size is reported.
  - `python -m presentation.build` (no flag) writes the multi-file `presentation/index.html` + `assets/`.

- [ ] **AC-8** (PRES.8): *Honest labels everywhere.*
  - Every quantum number carries `simulated: ideal` / `simulated: Heron-class noise`.
  - The INT gaps that the story run hit are shown on the provenance slide as known gaps, not hidden. The `--job`
    binding in particular is shown with `--allow-gaps`.
  - The build checks that the forbidden phrases appear nowhere in the rendered deck.

---

## 3. Out of Scope (Postponed)

- **Fixing RE pipeline gaps or flaws** (G `fill --job`, D founder, solid HU −22, GGO texture, juxtapleural rule).
  They belong to INT / the letters. PRES shows them honestly as they are.
- **A multi-tumour cohort or realism statistics.** These go to `ValidationPlan.md` (a later VAL feature).
- **Real IBM hardware runs.** The deck uses simulation only.
- **Speaker video, voice-over and a PDF export pipeline.** Reveal's own `?print-pdf` works manually and is not
  automated.
- **Embedding the deck in the RE site navigation.** That would change `relatedPapers/reverse-engineering/` and is a
  follow-up for INT.
- **Any use of the MVP render** (`QuantumPhantoms/code/f2_imaging`, the Wikimedia thorax). This is a separate lineage.

---

## 4. Technical Decisions

| Component | Choice / Implementation |
|---|---|
| Slides | **Reveal.js 5.1.0**, vendored from the npm tarball (`npm pack reveal.js@5.1.0`, MIT) into `presentation/vendor/reveal.js/` (`dist/` + `LICENSE`). One-time network fetch; offline afterwards (Q1). |
| Host | **LIDC-IDRI-0004**, the INT chain's reference host. A's committed figure already shows good sites on it (Q2). |
| Story data | The **INT chain** (`INT_integration.src.chain`) as a subprocess with `--mode ideal --allow-gaps`, so the story is one real chain run. Extra growth time points come from F `render --step` (Q3). |
| Growth in CT | F `render --step k` for 6 evenly spaced trajectory steps, so each frame is a real hybrid CT, not a drawn overlay. |
| Image I/O | SimpleITK for `.nii.gz`, pydicom for G's series, numpy, matplotlib for overlays (contours, rings), PIL for compositing, imageio for animated WebP. |
| Geometry | All frames share one axial slice index and crop, derived once from the final `lesion_mask` centre of mass and stored in `story.json`. Windowing follows `F_render/src/export_slices.py` (lung W1500/L−600, mediastinal W400/L40). |
| Templates | Jinja2 (`templates/deck.html.j2`), as in the RE site build. |
| Single file | Inline Reveal CSS/JS + theme; images become base64 `data:` URIs (the `QuantumPhantoms/web/index.html` approach). |
| Theme | Reveal custom theme `theme/qp.css` with dark RE tokens; system fonts only. |

**Conventions & Notes:**
- **Read-only consumer.** Contract files are read by path from `story.json`. Nothing under `relatedPapers/reverse-engineering/`
  is written, except the run dirs the CLIs themselves create (gitignored).
- **Numbers from data.** `deck.py` passes a `facts` dict built from contract files (`certificate.json`, `tumor_draw.json`,
  `witness_record_*.json`, `growth_trajectory.json`, `hybrid_volume.json`, `verify_report.json`, `validation_report.json`).
  Templates never contain literal results.
- **Privacy and licence.** Frames are display exports of a public CC BY 3.0 scan (the same policy as F's committed
  `render-lidc0001-*.png`). Volumes stay in gitignored `runs/`. Only PNG/WebP display exports enter
  `presentation/assets/`.
- **Layering.**
  - `story_run.py`: subprocess orchestration only.
  - `build/frames.py` and `build/hero.py`: image logic only.
  - `build/deck.py`: assembly only.
  - `build/__main__.py`: CLI.
- Plain step labels and readiness ratings come from the RE site: the `STEP` dict in `shared/site/build.py` and the
  letter README readiness markers. They are read as text, not imported, to stay read-only (`build/facts.py`).

---

## 5. Data Model (Additions/Modifications)

```text
[New, PRES-local file]  presentation/story/story.json
  host                 str            "LIDC-IDRI-0004"
  mode                 str            "ideal" | "heron"
  chain_dir            str            RE-relative path of the INT chain run used
  created_utc          str
  contracts            object         { key: RE-relative path }  (keys as in chain.json ctx: A.masks, A.sites,
                                      B.draw, C.certificate, D.seed_shape, D.witness_lineage, E.trajectory,
                                      F.hybrid, G.receipt, G.series, G.verify, H.report?, …)
  growth_steps         array<{ step:int, day:float, hybrid:str }>   one F render per time point (6)
  geometry             { slice_index:int, centre_vox_zyx:[int,int,int], crop_mm:float,
                         window_lung:[1500,-600], window_mediastinal:[400,40] }
  gaps                 array<{ stage:str, msg:str }>   copied from chain.json findings (severity != info)

[New, PRES-local file]  presentation/assets/frames.json
  frames               array<{ id:str, step:str, file:str, caption:str, sim_label:str|null }>
```

There is no database and no contract change. `story.json` is presentation data, not an RE contract.

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `QuantumPhantoms/presentation/__init__.py` | package marker |
| New | `QuantumPhantoms/presentation/README.md` | what the deck is, how to rebuild it, licence/attribution, honesty rules |
| New | `QuantumPhantoms/presentation/story_run.py` | runs the INT chain + extra F `render --step` runs as subprocesses (cwd = RE folder); writes `story/story.json` |
| New | `QuantumPhantoms/presentation/build/__init__.py` | package marker |
| New | `QuantumPhantoms/presentation/build/__main__.py` | `python -m presentation.build [--single-file] [--story story/story.json]`: frames → hero → deck |
| New | `QuantumPhantoms/presentation/build/geometry.py` | slice and crop from `lesion_mask`; windowing; CT-to-RGB helpers |
| New | `QuantumPhantoms/presentation/build/frames.py` | the per-step PNGs of AC-2 and the two animations of AC-3; writes `assets/frames.json` |
| New | `QuantumPhantoms/presentation/build/hero.py` | the AC-4 hero composite |
| New | `QuantumPhantoms/presentation/build/facts.py` | reads numbers from contract files, plain step labels and readiness markers (text only) |
| New | `QuantumPhantoms/presentation/build/deck.py` | renders the Jinja2 template; single-file inlining; offline and forbidden-phrase checks |
| New | `QuantumPhantoms/presentation/templates/deck.html.j2` | Reveal slide markup (AC-5) |
| New | `QuantumPhantoms/presentation/theme/qp.css` | dark Reveal theme from RE tokens (AC-6) |
| New | `QuantumPhantoms/presentation/vendor/reveal.js/` | Reveal.js 5.1.0 `dist/` + `LICENSE` (vendored) |
| Generated | `QuantumPhantoms/presentation/assets/frames/*.png`, `assets/anim/*.webp`, `assets/hero.png`, `assets/frames.json` | build output (committed, Q6) |
| Generated | `QuantumPhantoms/presentation/index.html`, `QuantumPhantoms/presentation/dist/quantum-phantoms.html` | deck output (committed, Q6) |
| Generated | `QuantumPhantoms/presentation/story/story.json` | story record (committed; contains paths and numbers only) |

Analogues to mirror:
- the INT runner (`relatedPapers/reverse-engineering/INT_integration/src/chain.py`) for subprocess style;
- `F_render/src/export_slices.py` for windowing and cropping;
- `shared/site/build.py` for Jinja2 and the offline asset check;
- `QuantumPhantoms/web/index.html` for single-file base64 inlining.

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-1:**
  - From `QuantumPhantoms/`, run `python -m presentation.story_run --host LIDC-IDRI-0004 --mode ideal`.
  - Expect the INT chain to run (A's segmentation once, ~25–75 min) and 6 extra F renders.
  - `presentation/story/story.json` must list every contract key in §5, with existing paths.
  - Re-run with `--chain-dir <that run>`: it finishes in minutes without re-segmenting.
- [ ] **Verify AC-2:**
  - Open `presentation/assets/frames/`. Every file in the AC-2 table exists.
  - All CT frames show the same slice and crop.
  - The lesion appears first in `D-seed-shape` (as an overlay) and grows across `F-ct-1…6` in pure CT look.
- [ ] **Verify AC-3:** open `assets/anim/growth-ct.webp` in a browser. It loops baseline → follow-up at ~2 fps.
- [ ] **Verify AC-4:**
  - Open `assets/hero.png`. At 1920×1080 the main panel reads as a real CT slice, and the bottom strip shows 8 captioned
    steps.
  - The attribution caption is present.
- [ ] **Verify AC-5:**
  - Open `presentation/index.html` via `file://` with the network off.
  - Arrow through all slides in the AC-5 order. Each step slide shows its frame, one line, one key number and a badge.
  - Spot-check three numbers against `story.json` and the contract files.
- [ ] **Verify AC-6:**
  - The deck uses the dark palette and system fonts.
  - CT images sit on black.
  - Badges and chips look like the site's.
- [ ] **Verify AC-7:**
  - `python -m presentation.build --single-file` writes `dist/quantum-phantoms.html` and prints its size.
  - Open it from a different folder, offline: all slides and images render.
  - `grep -c 'https\?://' dist/quantum-phantoms.html` finds no asset URLs. Only text links such as the attribution URL are allowed.
- [ ] **Verify AC-8:**
  - Every quantum number on screen has a sim label.
  - The provenance slide lists the INT gaps hit.
  - The build reports "forbidden phrases: none".
- [ ] **Edge case:** delete `story/story.json` and run `python -m presentation.build`. It stops with "run presentation.story_run first", not a traceback.
- [ ] **Edge case:** if the chain stops before `render`, the story run exits non-zero and names the stage. No deck is
  built from partial data.

---

## 8. Open Questions

- [x] **Q1: Vendor Reveal.js (new dependency, one network download)?** *Proposed:* yes. Use Reveal.js 5.1.0 via
  `npm pack`, `dist/` + `LICENSE` only, committed under `presentation/vendor/`. The alternative is a hand-written slide
  engine, which is more work and not what was asked.
- [x] **Q2: Which host?** *Proposed:* LIDC-IDRI-0004, the INT reference host. A's committed site figure already looks
  good on it. LIDC-IDRI-0001 has F renders on disk but no A segmentation either, so both cost one A run.
- [x] **Q3: Run the story through the INT chain (one real chain run), or call the letter CLIs one by one?** *Proposed:*
  INT chain with `--mode ideal --allow-gaps`. It is the honest "one tumour through the pipeline", and gaps get recorded.
  If B-2 at K = 8 is too slow in ideal mode, fall back to per-letter CLIs with B-1, noted on the slide.
- [x] **Q4: How many growth time points for the CT animation?** *Proposed:* 6, evenly spaced from the first snapshot to
  +90 days. That means 6 F renders of seconds to minutes each.
- [x] **Q5: Crop size for the step frames?** *Proposed:* ±60 mm around the lesion for steps, and the full field of view
  for the hero and the host slide.
- [x] **Q6: Commit the generated deck and images?** *Proposed:* yes: `index.html`, `dist/quantum-phantoms.html`,
  `assets/**` and `story/story.json`. These are display exports of a public CC BY 3.0 scan, like F's committed figures.
  Volumes stay in gitignored `runs/`. Report the total size; if it is above ~30 MB, commit only `dist/` + `hero.png`.
- [x] **Q7: Run H's `validate` stage (full `lidc_ref` over all LIDC scans) for the story?** *Proposed:* no. Use
  `--stop-after sign`, and let the validation slide show H's committed figures labelled "method check, not this
  tumour" plus the n = 1 note. Validation proper belongs to `ValidationPlan.md`.
- [x] **Q8: Where should the deck be linked from?** *Proposed:* `QuantumPhantoms/presentation/README.md` only for now.
  A link from the RE index is an INT follow-up (out of scope).

---

## 9. Post-Implementation Notes

[Filled after implementation.]
