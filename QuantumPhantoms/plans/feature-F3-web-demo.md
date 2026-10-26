# Feature F3 — Web demo: cohort grid web render (the MVP)

**Epic:** [`epic-quantum-phantoms-mvp.md`](./epic-quantum-phantoms-mvp.md) (Approved)
**Feature ID:** F3
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Complete

> **Technical constraints / core directive.** Output = **one self-contained static HTML page** (data + PNG tiles baked in; **no backend, no live QPU calls, no external CDN/JS**), built by a small **Python** script from one F2 run (epic §3). The page is **blind to the sampler** — it renders whatever `tiles.json` carries (epic §3 seam). **This is the shippable MVP.** Research-study conventions: **no GitHub issues, no automated test suite — manual verification only.** Honest claim ceiling unchanged: params quantum, **image classical**; provenance is about lesion/cohort *selection*, never the CT background (epic §6).

---

## 1. Why (Step Goal)

**Before.** F1 produced certified-quantum tumor parameters + a CHSH certificate; F2 rendered them into labeled synthetic CT tiles (`<run>/tiles/*.png` + `<run>/tiles.json`). But there is nothing to *show* — no page a person can open and see "a real synthetic-cohort dataset viewer whose data provably came from a quantum computer."

**After.** F3 is the MVP deliverable: a **single self-contained web page** that reads one F2 run and renders:
1. A **header** stating the cohort size, the backend, and the **job-level CHSH value** ("nobody chose this cohort — the distribution came from physics").
2. A **cohort grid** of the CT tiles — each cell shows the tile image, its decoded parameters (size / type / lobe), a **CHSH stamp**, and a **lineage badge** on sibling pairs.
3. A **single-tile detail view** (click a tile): the enlarged image, the full decoded parameters (size / type / margin / lobe), and a **quantum certificate** panel (CHSH bar vs the classical max 2.0, shot #, "✓ genuine quantum roll").
4. A **cohort-vs-rulebook strip**: a size-distribution histogram (cohort vs the published rulebook) and the type mix — the "matches ✓" credibility line.
5. The **honest label** (params quantum, image classical; synthetic-vs-real background status).

A Python builder (`build_web.py`) embeds the PNGs as base64 data URIs and the `tiles.json` data inline, so the result is **one `.html` file hostable anywhere / sendable as a link**. Shipping F3 completes the MVP (epic §7).

---

## 2. Acceptance Criteria

- [x] **AC-1** (F3.1) — `code/build_web.py:77` (`main`), `_png_data_uri:61`, `:108` (placeholder inject). Built `web/index.html` (198 KB); verified `grep -coE 'https?://'` = **0** external URLs, 0 leftover placeholders, 12 embedded `data:image/png` URIs, and the page renders fully from a `file://` load (playwright/chrome screenshot). One self-contained static HTML file, no backend, no external requests.
  → `build_web.py` reads `<run>/tiles.json` + `<run>/tiles/*.png`, base64-embeds every PNG as a `data:` URI, injects all data + the rulebook reference inline, and writes a single `index.html`. The file contains **no** `http(s)://` asset references, no CDN scripts, no backend calls — opening it offline renders fully.
- [x] **AC-2** (F3.2) — `code/web_template.html:131` (`renderMeta`). Screenshot shows "12 tumors · backend AerSimulator · CHSH 2.795 > 2.0 · simulator (noiseless)". Header shows cohort size, backend, and the job-level CHSH value.
  → header renders `N tumors · <backend_name> · CHSH <value>` from `tiles.json`'s `quantum_run`; when the value is NaN (PRNG baseline) or from a simulator it is labeled accordingly (AC-8).
- [x] **AC-3** (F3.3) — `code/web_template.html:194` (`renderGrid`; `auto-fill minmax` grid at CSS `:42`). Screenshot shows 12 cards, each with the CT image, `size mm` + type + lobe, and a green "CHSH 2.79 · shot #N" stamp (the job-level value + per-tile shot index, not a per-tile Bell value). A responsive grid shows every tile with image + decoded params + CHSH stamp.
  → one grid cell per `CohortTile`: the embedded PNG, `size_mm`/`type`/`lobe` labels, and a per-tile CHSH stamp (the **job-level** value + that tile's `shot_index` — never a fabricated per-tile Bell value).
- [x] **AC-4** (F3.4) — `code/web_template.html:220` (`openModal`; close on Esc/outside at `:258-260`). Modal screenshot shows the enlarged image, size/type/margin/lobe/shot, and a CHSH certificate bar filled to 2.795 with the classical-max 2.0 line on a 0–2.83 scale + verdict line. Clicking a tile opens a detail view with full params + a quantum certificate.
  → a modal/overlay shows the enlarged image, all four decoded params (size / type / margin / lobe), and a certificate panel: a CHSH bar against the classical-max 2.0 reference line, the tile's shot #, and "✓ genuine quantum roll" (mirrors the parent §2.5 single-tile mockup).
- [x] **AC-5** (F3.5) — `code/web_template.html:202` (`groups()` + "gen N of ∞" badge). Screenshot: pair8 and pair9 tiles carry "gen 0 of ∞" / "gen 1 of ∞" badges; the pair9 crops show the two adjacent related lesions. Sibling pairs carry a lineage badge and read as linked.
  → tiles sharing a `lineage_id` (generations 0 and 1) show a "gen 1 of ∞ — clonal evolution next" badge and are visually grouped/linked in the grid (epic §5, parent §2.5).
- [x] **AC-6** (F3.6) — `code/web_template.html:152` (`renderHist`, inline SVG) + `:171` (`renderTypeMix`); rulebook data from `code/build_web.py:67` (`_rulebook_block`). Screenshot shows cohort (filled petrol) vs rulebook (outline) bars across the 4 size bands with "matches ✓", plus the type-mix bars (solid 42% / GGO 42% / ps 8% / calc 8%). A cohort-vs-rulebook strip shows the size histogram and type mix.
  → an inline-SVG/vanilla-JS histogram compares the **cohort's** size-band distribution to the **rulebook's** published frequencies, plus the cohort type mix; drawn from embedded data only (no chart library). The rulebook reference comes from `rulebook.Rulebook` (epic §4).
- [x] **AC-7** (F3.7) — `code/build_web.py:77` reads `<run>/tiles.json` + PNGs only; no qiskit import, no CHSH recompute. Ran against the `qrng_aer` F2 run; identical `tiles.json` schema means a `prng` run renders the same (epic §3 seam). The builder consumes an F2 run and is sampler-blind.
  → `python build_web.py --run <dir>` reads `<run>/tiles.json` (+ PNGs) and renders identically whether F1 used `QRNGSampler` or `PRNGSampler`; the page never recomputes anything quantum (epic §3).
- [x] **AC-8** (F3.8) — `code/web_template.html:253` (`renderHonest` footer) + `:204`/`:58` (per-tile "synthetic bg" marker) + `chshLabel:121` (sim/classical labeling). Screenshot: footer shows the full honest label; every tile carries an amber "synthetic bg" marker; CHSH chip reads "simulator (noiseless)". The honest label and background status are shown on the page.
  → the page displays `tiles.json`'s `honest_label` (params quantum / image classical / provenance = selection, not background) and surfaces each tile's `background_source` (e.g. a "synthetic background — dev only" marker when `synthetic_dev`); nothing implies a quantum or non-classical image (epic §6, parent §5.4).

---

## 3. Out of Scope (Postponed)

- **The quantum roll, lesion rendering, CT insertion** → **F1 / F2** (done). F3 only reads their baked output.
- **Ed25519 signing, append-only ledger, formal cohort audit, "verify" button** → deferred to the full plan (parent §2.1). F3 shows a histogram "matches ✓", not an audit.
- **Live QPU calls / interactivity beyond the detail view / re-rolling from the browser** → not in the MVP (epic §3: static, baked artifact). Any live-data page is later work.
- **Multi-generation evolved lineages / the QALife loop arm** → **F4** (optional). F3 renders F1's single-division sibling pairs; if F4 later feeds a richer lineage into F2, F3 renders it unchanged (same `tiles.json` contract).
- **Deployment/hosting automation** → out of scope; the deliverable is the self-contained file the developer can host anywhere.

---

## 4. Technical Decisions

Adopts the epic's §3 cross-cutting decisions verbatim (self-contained static artifact, sampler-blind, honesty gates, no issues/tests). Feature-specific choices:

| Component | Choice / Implementation |
|---|---|
| Page stack | **Plain HTML + CSS + vanilla JS**, single file, no framework, **no external CDN** (self-contained requirement). **Light theme in the Siemens color scheme** (see below) — **no Siemens logo/wordmark**. |
| Color scheme | Light: white / light-gray background (`#ffffff` / `#f3f3f0`), **Siemens Petrol `#009999`** primary, **Deep Blue `#000028`** for primary text, **Bright Green `#00ffb9`** accent (CHSH/"genuine" highlights), muted grays for secondary text; an amber (`#ffb900`) only for the "simulator/synthetic — dev only" warnings. CT tile images render on a dark inset (medical-viewer feel) inside the otherwise light page. Colors only — **no logo, no wordmark, no trademarked assets**. |
| Builder | **Python** (`build_web.py`), mirroring F1/F2 flat-module style under `code/`. Reads `tiles.json`, base64-embeds PNGs, injects a JSON blob into a template, writes `index.html`. |
| Template | `code/web_template.html` — the static HTML/CSS/JS shell with a single `__COHORT_DATA__` placeholder the builder replaces with the embedded JSON. Keeps markup editable separate from Python. |
| Image embedding | each PNG → `data:image/png;base64,...` URI inline (true single-file artifact, AC-1). |
| Histogram | **inline SVG** drawn by vanilla JS from the embedded cohort + rulebook data — no chart library (keeps it self-contained). |
| Detail view | **click → modal overlay** (not hover), showing enlarged image + params + CHSH certificate bar (vs 2.0 line). |
| CHSH display | the **single job-level** value from `quantum_run`, shown in the header and stamped per tile with that tile's `shot_index`; the detail bar compares it to the classical bound 2.0. Never a per-tile Bell value (F1 §4 honesty note). |
| Rulebook reference | imported from `rulebook.Rulebook` at build time and embedded as JSON (size-band labels/probs, type mix) for the cohort-vs-rulebook strip. |
| Output | default `QuantumPhantoms/web/index.html` (sibling-study convention); `--out` overrides. Self-contained, so it can also be copied into `<run>/`. |

**Conventions & Notes:**
* Builder lives in `QuantumPhantoms/code/` (flat imports, run from inside `code/`), mirroring F1/F2.
* F3 **reads only** baked artifacts — it never imports qiskit, never recomputes CHSH, never calls a backend.
* The page must stay honest: CHSH is job-level; a simulator/PRNG value is labeled as such; the real-hardware value is the one for the public demo (epic §3).
* No horizontal page scroll; the grid is responsive and the detail modal fits small screens (self-contained, works opened as a local file).

---

## 5. Data Model (Additions/Modifications)

F3 **introduces no persisted entities** — it is the presentation layer. It **consumes**:
- `CohortTile[]` and the embedded `QuantumRun` from `<run>/tiles.json` (F2 output).
- `Rulebook` from `rulebook.Rulebook` (F1) for the cohort-vs-rulebook strip.

The only new on-disk artifact is the generated page:

```text
[Generated artifact — not a data entity]
QuantumPhantoms/web/index.html
  self-contained HTML; embeds:
    - COHORT_DATA.tiles[]        (from tiles.json, PNGs as data: URIs)
    - COHORT_DATA.quantum_run    (backend, job_id, chsh_value)
    - COHORT_DATA.rulebook       (size bands + probs, type mix)
    - COHORT_DATA.honest_label
```

---

## 6. File Plan (Concrete Changes)

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `QuantumPhantoms/code/build_web.py` | CLI: `--run <dir>` (F2 output), `--out` (default `../web/index.html`). Reads `tiles.json`, base64-embeds PNGs, builds `COHORT_DATA`, injects into the template, writes the page. Imports `rulebook.Rulebook` for the reference distribution. |
| New | `QuantumPhantoms/code/web_template.html` | Self-contained HTML/CSS/JS shell: header, responsive grid, click-to-open detail modal, cohort-vs-rulebook SVG strip, honest-label footer. Single `__COHORT_DATA__` placeholder; vanilla JS renders everything from it. **Light Siemens-color theme, no logo** (palette in §4). |
| New (generated) | `QuantumPhantoms/web/index.html` | The built MVP page (produced by `build_web.py`; the shippable artifact). |
| Modify | `QuantumPhantoms/code/README.md` | add an F3 section: how to build the page from a run, where it lands, the self-contained/no-backend note, the honest-label reminder. |

---

## 7. Manual Verification (No Tests)

- [ ] **Verify AC-1 / AC-7:** `python QuantumPhantoms/code/build_web.py --run research_runs/<f2_run>` → writes `web/index.html`; `grep -c 'http' web/index.html` shows no external asset URLs; open the file **offline** in a browser → it renders fully (images, grid, histogram).
- [ ] **Verify AC-2:** header shows the tile count, backend name, and CHSH value matching `tiles.json`'s `quantum_run`.
- [ ] **Verify AC-3:** the grid shows all N tiles, each with its image, size/type/lobe, and a CHSH stamp with the tile's shot #.
- [ ] **Verify AC-4:** clicking a tile opens the detail modal with size/type/margin/lobe and a CHSH bar past the 2.0 line + "genuine quantum roll"; closing returns to the grid.
- [ ] **Verify AC-5:** the two sibling-pair tiles (shared `lineage_id`) show the "gen 1 of ∞" badge and are visually grouped.
- [ ] **Verify AC-6:** the cohort-vs-rulebook strip shows a size histogram where the cohort bars track the rulebook bars, plus the type mix.
- [ ] **Verify AC-8:** the honest label is visible; a run built from a `synthetic_dev` background shows the "synthetic background — dev only" marker; a PRNG/sim run labels its CHSH accordingly.
- [ ] **Edge case:** `--run` pointing at a dir with no `tiles.json` → clear error telling the user to run F2 first; a run with 0 sibling pairs still renders (no badges, grid intact).

---

## 8. Open Questions

All resolved — defaults accepted by Peter (2026-10-26), with the theme set to **light / Siemens colors / no logo**. Locked decisions:

- [x] **Q1 (single-file embedding):** base64-embed every PNG + inline all data/JS/CSS → one truly self-contained `index.html` (epic §3).
- [x] **Q2 (histogram rendering):** inline SVG via vanilla JS from embedded data — no chart library.
- [x] **Q3 (detail view interaction):** click → modal overlay; Esc / click-outside closes.
- [x] **Q4 (output location):** default `QuantumPhantoms/web/index.html`, `--out` override, `--run` required.
- [x] **Q5 (non-hardware CHSH labeling):** show the value but label its source ("simulator (noiseless)" for Aer, "classical baseline — no CHSH" for PRNG); real-hardware value is the public one. Page does not block on source.
- [x] **Q6 (template vs inline HTML):** HTML/CSS/JS in `code/web_template.html` with a `__COHORT_DATA__` placeholder the builder fills.
- [x] **Q7 (aesthetic):** **Light theme in the Siemens color scheme — no Siemens logo/wordmark** (palette in §4: petrol `#009999`, deep blue `#000028`, bright green `#00ffb9`, white/light-gray bg, amber warnings). Colors only, no trademarked assets.

---

## 9. Post-Implementation Notes

**Built (2026-10-26).** 3 new files + 1 modified under `QuantumPhantoms/`, on `main`. **No new runtime dependency** (builder is stdlib + the existing `rulebook`/`datamodel`; the page is pure HTML/CSS/JS). This completes the MVP (epic §7: F1→F2→F3).

New: `code/build_web.py`, `code/web_template.html`, `web/index.html` (generated). Modified: `code/README.md` (+F3 section).

**Decisions within the plan:**
- Builder is stdlib-only (`base64`/`json`); imports `rulebook.Rulebook` + `datamodel.TYPES` for the reference strip. PNGs embed as `data:` URIs; `tiles.json` NaN (PRNG CHSH) is sanitized to `null` so the embedded blob is strict JSON the browser parses.
- Light **Siemens** palette, **no logo**: petrol `#009999`, deep blue `#000028`, bright green `#00ffb9`, white/`#f3f3f0` bg, amber warnings; CT tiles on a dark inset.
- Page writes to `QuantumPhantoms/web/index.html` (sibling-study convention); `--out` overrides.

**Verified (headless chrome via playwright, full-page + modal screenshots):** page renders fully offline from `file://`; header chips (12 tumors / backend / CHSH 2.795>2.0 / simulator label); cohort-vs-rulebook SVG histogram "matches ✓" + type mix; 12-tile grid with per-tile CHSH stamp + shot #; sibling badges "gen 0/1 of ∞" on both pairs (pair9 shows the two adjacent lesions); click → detail modal with full params + CHSH certificate bar vs the 2.0 line; honest-label footer + per-tile "synthetic bg" markers. `grep` confirmed 0 external URLs / 0 leftover placeholders.

**Follow-ups for the developer:**
- Rebuild the page from the real-hardware run once you run F1 `--backend ibm_heron` → F2 `--ct-source <luna16>` → `build_web.py --run <that run>`; the page will then show the real CHSH value (no "simulator" label) and real CT backgrounds (no "synthetic bg" marker).
- The page is self-contained — host `web/index.html` anywhere or send it as a file.
- Aesthetic uses Siemens colors only; confirm no trademarked assets are added before any external sharing.
