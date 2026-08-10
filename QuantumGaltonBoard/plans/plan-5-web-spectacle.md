# Plan P5 — The web spectacle

**Epic:** `plans/epic-quantum-galton-board.md` (Status: Draft — OQs resolved 2026-08-06)
**Plan ID:** P5 (`[MUST]`, depends on P1 `WALK_SPEC` + P4 `web/replay.json`; gates none)
**Slug:** web-spectacle
**Author:** Claude (Opus)
**Date:** 2026-08-10
**Status:** Complete (2026-08-10 — Tier A shipped on the on-disk `ideal` arm; parity gate green)

> **No automated tests (project directive, epic §3.6).** Verification is the offline
> JS↔Python **parity gate** (`code/parity_check.py`, node-driven, network-free / QPU-free),
> a manual browser walkthrough of the three visual components, and a JSON eyeball of the
> embedded replay. This plan lists no test files, no test suites, and no AC→test mapping.
> "How to verify" everywhere means the parity gate + manual browser inspection.

---

## 1. Context

P5 is the star of the epic (§3.4 LOCKED — the visualization is a first-class deliverable; the
depth slider dragging the ideal horns into the classical hump *is* the paper's headline figure
made live). It ships the self-contained browser spectacle and nothing else — no physics, no
metrics, no new data. Every contract it consumes is frozen and on disk:

- **P1** froze `WALK_SPEC` (`code/walk_spec.py:22`) and the one-hot decode rule
  `decode_counts(counts, steps)` (`code/walk_spec.py:39`) — the JS decoder is a hand-kept
  mirror of these (epic §4, §5 OQ-1). Endianness/index convention is fixed there: coin qubit =
  register index 0 (LSB, rightmost char), position qubits = indices `1..n+1`, bitstrings
  little-endian, `pos = 2*bin - n`.
- **P3** froze the metric functions the JS must reproduce under the parity gate
  (`code/metrics.py`): `variance` (`metrics.py:51`), `horn_contrast` (`metrics.py:117`),
  `entropy` (`metrics.py:150`), `tv_distance` (`metrics.py:94`), `hellinger` (`metrics.py:104`),
  `local_variance_exponent` (`metrics.py:163`), `crossover_depth` (`metrics.py:212`). Python is
  the source of truth (§3.6 LOCKED); the browser only *renders* these numbers.
- **P4** froze the replay contract `web/replay.json` (`code/replay_export.py:86`, shape in
  `code/SCHEMA.md`), the single file P5 embeds (OQ-6). Verified on disk 2026-08-10:
  top-level keys `walk_spec` / `encoding` / `arms` / `depths` / `binomial_reference` /
  `per_arm`; `arms = [ideal, noisy, hw]`; `depths = [2,4,…,18]`; `per_arm.ideal` **filled**
  (9 depths, each `{position_histogram, metrics:{variance,horn_contrast,entropy,a_local}}` plus
  a `knee`); `per_arm.noisy = null` and `per_arm.hw = null` (Phase-A state — the noisy sweep
  and the hw matrix have not been run yet, P4 §14 follow-ups). `binomial_reference[n]` carries
  the classical hump per depth.

**Structural twin:** `QuantumLife/web/quantum_tree.html` (344 lines, verified on disk). P5 clones
its delivery exactly (epic §9 P5 "Conventions"): a single self-contained file — inline `<style>`
(CSS custom properties, dark default via `prefers-color-scheme` + a `data-theme` override, lines
1–50), a `.stage` holding one `<canvas>` with HUD overlays, a `.controls` row (button + range +
file input), and one inline `<script>` (`"use strict"`) that decodes a spec **mirrored by hand
from the Python** (twin comment `"mirror of code/genome.py"`, line 78), builds the scene once,
and animates with `requestAnimationFrame` (`frame(now)`, line 164). No framework, no CDN, no
build tool at view time. The twin also ships a synthetic `demo()` (line 311) so the page is alive
before real data loads, and a `load run.json` file input (line 296) — P5 keeps both patterns
(an embedded default replay + a file-input override).

**Two-tier delivery (epic §7).** P5 splits exactly as the twin's viewer did:
- **Tier A (buildable now):** the ideal↔classical story — cascade animation, the classical vs
  quantum morph (binomial hump ↔ ideal twin horns), the depth slider over the `ideal` arm, and
  the interference glow. This runs entirely on the on-disk `per_arm.ideal` + `binomial_reference`
  and P1's `WALK_SPEC`.
- **Tier B (lights up when P4 fills the arms):** the **noise-melt** slider — dragging depth on
  the `noisy`/`hw` arm and watching the horns collapse toward the hump. This needs
  `per_arm.noisy` (P4 Phase-A noisy sweep, pending connectivity) and `per_arm.hw` (P4 Phase B,
  ≥ 2026-08-15). P5's code renders these arms generically today; they simply toggle from
  "awaiting data" to live when the null slots fill. **No P5 code change is needed when they
  arrive** — same contract, populated.

## 2. Acceptance criteria (from epic §9 P5 → source §THE VISUALIZATION, verbatim)

Copied verbatim from the epic brief; IDs preserved.

- **AC-5.1 — Cascade animation.** Balls/amplitude "waterfall" through the peg lattice, bins
  filling in real time; a toggle for classical vs quantum that morphs the bell curve into the
  twin horns.
  *Approach:* a triangular peg lattice drawn on the canvas; an amplitude "waterfall" descends
  row by row over `requestAnimationFrame` and accumulates into the bottom bins, whose heights
  ease toward the selected arm/depth `position_histogram` from the embedded replay. A
  `classical ⇄ quantum` toggle cross-fades the bin targets between `binomial_reference[n]` (the
  Gaussian pile) and the arm histogram (the twin horns), so the pile visibly morphs. Mirrors the
  twin's build-once-then-reveal-by-`rAF` pattern (`quantum_tree.html:164,209`).
- **AC-5.2 — Depth slider.** Drag `n` and see ideal horns melt toward the classical hump as
  noise wins — the paper's headline figure as a live control, replaying the P4 arms.
  *Approach:* a range input bound to `replay.depths`; changing it retargets the bins to that
  depth's histogram for the active arm and eases the pile between depths. On the `ideal` arm the
  horns stay horned at every depth (the honest ideal result — `knee_depth = null`, verified in
  replay); on `noisy`/`hw` the horns melt toward `binomial_reference` past the knee. A readout
  shows the depth's `metrics` (variance, horn_contrast, entropy, a_local) and the arm's
  `knee_depth` from the embedded replay — never recomputed for display unless a raw run.json is
  loaded (then the JS mirror computes them, §5).
- **AC-5.3 — Interference glow.** Color pegs by local phase so constructive/destructive
  interference is visible as it happens (the "why it's not Gaussian" panel).
  *Approach:* the measured replay carries **probabilities only**, not amplitude signs, so the
  glow is driven by a small **client-side analytic Hadamard-walk amplitude recurrence** (the
  known ideal DTQW amplitudes on the line) computed in JS purely for this panel: each peg is
  colored by the sign/magnitude of the local interference term (constructive = accent glow,
  destructive = dim), overlaid on the lattice. It is labeled **"ideal amplitude phase
  (illustrative)"** and is explicitly **not** a measured hardware quantity (OQ-5.3) — it explains
  *why* the ideal distribution is twin-horned, and it is **outside** the parity gate (§6), which
  covers only the distribution/metric rendering (§3.6 wording).
- **AC-5.4 — Self-contained + parity-gated.** Pure browser HTML/Canvas, self-contained (no
  build, no CDN, no framework), same delivery as `QuantumLife/web/`; the distribution/metric
  rendering is gated on JS↔Python parity (§3.6) against the P3 metrics.
  *Approach:* one file `web/quantum_galton.html` with the replay JSON embedded (OQ-6), viewable
  from `file://` by double-click. The shipping JS decoder + metric mirror sit between sentinel
  comments; `code/parity_check.py` extracts that exact block, runs it under `node` against every
  replay histogram (and synthetic decode inputs), and asserts equality to `walk_spec.decode_counts`
  / `metrics.py` within tolerance before the arm ships (§6).

### AC coverage — file:line evidence

| AC | Holds? | Covered by |
|----|--------|------------|
| AC-5.1 Cascade + classical⇄quantum morph | ✅ | `web/quantum_galton.html:326` (`frame` rAF), `:277` (`walkAmplitudes` waterfall reveal via `scanRow`), `:372` (bins ease toward target), `:385` (dashed `binomial_reference` hump), `:397` (quantum bars), `:317` (`targetHist` cross-fades binomial↔arm by `morph`); `morph` toggle handler `web/quantum_galton.html` `$("morph")`. Verified: `morph=1`→arm hist, `morph=0`→binomial (headless wiring check). |
| AC-5.2 Depth slider + arm toggle + readout | ✅ | `web/quantum_galton.html` `$("depth-slider")` handler retargets to `replay.depths[idx]`; `:453` `refreshArmButtons` (null arms disabled), `:455` `showAwait` Phase-B caption; `updateHud` prints embedded `metrics` + arm `knee`. Verified: depth 2→18 walks ideal horns, `knee_depth=null` on ideal, `noisy`/`hw` null-slot. |
| AC-5.3 Interference glow | ✅ | `web/quantum_galton.html:277` (`walkAmplitudes` analytic Hadamard recurrence), `:348`+glow loop (peg colored by `Re(c0·conj(c1))` sign, accent/accent2), label `:76` "ideal amplitude phase (illustrative) … not a measured hardware quantity". Excluded from the gate (`code/parity_check.py` scope note). |
| AC-5.4 Self-contained + parity-gated | ✅ | One file `web/quantum_galton.html`; replay embedded `:97` (`id="replay"`, `file://` no server); `code/build_web.py:37` splices it (codegen); `code/parity_check.py:45` extracts the sentinel block (`:110`/`:258`), `:128` decode parity, `:143` metric parity — **gate exits 0**, JS==Python ≤1e-9 on all 9 ideal depths. |

## 3. Out of scope (deferred, not omitted)

- Any metric definition, the knee rule, or the decode rule → **P3 / P1** (frozen). P5 *mirrors*
  them in JS and *proves the mirror* under the parity gate; it changes no Python.
- Generating, aggregating, or fitting data; rendering the static paper figures → **P4** (frozen).
  P5 consumes `web/replay.json` and renders it interactively; it runs no sweep and no matplotlib.
- The paper prose, `research/` docs, LaTeX thesis → **P6**.
- **Any live hardware or backend call from the browser** — the web app replays recorded P4 data
  only (epic §9 P5 "Out of scope"). No IBM account, no `fetch` to a QPU, no network at view time.
- A QRNG / QEaaS arm or provenance panel (epic §3.7).
- Running the `noisy` sweep or the `hw` matrix that fills `per_arm.noisy` / `per_arm.hw` →
  **P4** (Phase-A noisy pending connectivity, Phase B on the QC allocation). P5 renders those
  arms generically and is complete for the `ideal` arm now; the other arms light up on re-export
  with no P5 edit (§1 Tier B).

## 4. Decisions inherited from the epic (do not re-litigate)

- **§3.4 (LOCKED) — the viz is first-class.** P5 must be as polished as
  `QuantumLife/web/quantum_tree.html`: hand-rolled canvas + `requestAnimationFrame`, dark-friendly
  with a light override, self-contained, replaying recorded data. Not a stub.
- **§3.6 (LOCKED) — parity, not unit tests.** The browser's distribution/metric rendering is
  validated against `metrics.py` by the JS↔Python parity gate (§6). Python stays the source of
  truth; the JS mirror is kept in sync **by hand** and proven by the gate, never trusted blind.
- **OQ-1 (LOCKED) — one-hot line decode.** The JS decoder mirrors `walk_spec.decode_counts`
  exactly: coin qubit = index 0, position qubits `1..n+1`, little-endian bitstrings,
  `pos = 2*bin - n`. Frozen in `WALK_SPEC`, embedded verbatim in replay (`replay.walk_spec`), and
  hand-mirrored in the HTML (epic §5).
- **OQ-6 (LOCKED) — single self-contained HTML with embedded replay.** One file, replay JSON
  inlined; zero build step at view time. P5 owns the embed mechanism (§5, OQ-5.1).
- **§3.7 (LOCKED) — no QRNG arm / no provenance panel.** The independent variable is circuit
  depth; the arms are execution fidelity (ideal/noisy/hw). Do not import QRNG-client patterns.

## 5. The JS mirror + the embed (the frozen surface the gate checks)

The single HTML holds, in one inline `<script>`, three vendored-from-Python pieces plus the
embedded data. All three mirror pieces live between sentinel comments so the parity harness can
extract the *exact shipping code* (no drift, no second copy to keep in sync):

```
// ===GALTON-PARITY-BLOCK-START===
//   (JS decoder + JS metric mirror — the ONLY code the parity gate runs under node)
// ===GALTON-PARITY-BLOCK-END===
```

1. **`decodeCounts(counts, steps)`** — mirror of `walk_spec.decode_counts` (`walk_spec.py:39`).
   One-hot decode of a raw `{bitstring: count}` map to a normalised `{position: probability}`
   using `WALK_SPEC` (read from `replay.walk_spec`, not re-hardcoded): register index `1+j` for
   bin `j`, character `bits[-(idx+1)]` (little-endian), `pos = 2*bin - n`. Only exercised when a
   user loads a raw `run.json` via the file input; the embedded replay is already decoded.
2. **The metric mirror** — `variance(hist)`, `hornContrast(hist)`, `entropy(hist, base=2)`,
   `tvDistance(p,q)`, `hellinger(p,q)`, `localVarianceExponent(depths, variances, window=3)` and
   the `crossoverDepth` first-downcross rule — each a line-for-line port of the corresponding
   `metrics.py` function, including the parity/centre-band rule in `hornContrast`
   (`metrics.py:133`: `parity = firstKey % 2`; even → centre `{0}`, odd → centre mean of `±1`)
   and the sparse union-support rule in `tvDistance`/`hellinger`. These power the readout when a
   raw run.json is loaded and the on-hover distances (arm vs `binomial_reference`).
3. **`WALK_SPEC` / constants** — read from the embedded `replay.walk_spec`; no second literal.

**The embed (OQ-5.1).** The replay JSON is inlined as a `<script type="application/json"
id="replay">…</script>` block. `code/build_web.py` splices the current `web/replay.json` into
that block from a template, so a P4 re-export (noisy fill, or Phase-B hw) is followed by one
`python code/build_web.py` to refresh the single file — a codegen step, **not** a view-time
build (the shipped `.html` needs nothing). The twin's `load replay.json` file input is also kept
as a runtime override so an updated replay can be dropped in without re-splicing.

## 6. The JS↔Python parity gate — `code/parity_check.py` (§3.6, AC-5.4)

The honest realisation of "the browser matches the Python source of truth", with **no test
suite** and no browser automation. Node 24 is available on this machine (verified 2026-08-10),
so the gate runs the *actual shipping JS* server-side:

1. Read `web/quantum_galton.html`; extract the text between the two `GALTON-PARITY-BLOCK`
   sentinels (§5); write it to a temp `.mjs` with a thin `export` footer.
2. Read `web/replay.json`. For **every** filled arm and depth, take the decoded
   `position_histogram` and, under `node`, compute `variance` / `hornContrast` / `entropy` with
   the extracted JS; compute `tvDistance` / `hellinger` of the arm histogram vs
   `binomial_reference[n]`; and compute `localVarianceExponent` / `crossoverDepth` over the arm's
   depth series.
3. In-process, compute the same quantities with `metrics.py` on the same inputs.
4. Assert every JS value equals the Python value within `1e-9` (abs/rel); assert `decodeCounts`
   reproduces `walk_spec.decode_counts` on a handful of synthetic one-hot count maps (covering
   even/odd `n` and multi-bin superpositions). Print one `PASS` line per metric; **exit non-zero
   on the first mismatch** (mirrors `metrics_check.py` / `experiment_check.py`).

The gate is network-free and QPU-free and does not open a browser. Its scope is the
distribution/metric rendering only (§3.6); the AC-5.3 interference glow is analytic-illustrative
and deliberately excluded (OQ-5.3). If `node` is ever unavailable, the fallback is the printed
Python reference JSON + a manual browser-console comparison (OQ-5.2) — recommend node.

## 7. File Plan

All paths under `QuantumGaltonBoard/`. The HTML is authored in the twin's style (single file,
CSS custom properties, `"use strict"`, hand-rolled canvas + `requestAnimationFrame`, no
framework/CDN). The Python helpers use `from __future__ import annotations`, full type hints,
stdlib only (no new runtime deps; `node` is a dev/gate tool invoked via `subprocess`, not a
Python import). No business logic in the HTML beyond rendering; no metric or decode **definition**
is introduced in JS that is not a proven mirror of a frozen Python function (§6). No raw SQL
(n/a). No frozen artefact is edited.

| Path | New/Edit | Responsibility |
|------|----------|----------------|
| `web/quantum_galton.html` | **New** | The self-contained spectacle (AC-5.1–5.4). Inline `<style>` (dark default + `prefers-color-scheme` light + `data-theme` override, twin CSS-var palette); `.stage` canvas with HUD (arm, depth, knee, metrics readout); `.controls` (play/pause, **depth slider**, **arm toggle** ideal/noisy/hw with hw+noisy greyed while their replay slot is null, **classical⇄quantum morph** toggle, load-replay file input). One inline `<script>`: embedded `<script id="replay">` JSON; the sentinel-wrapped JS decoder + metric mirror (§5); the cascade/`rAF` animation and bin-easing; the analytic interference-glow recurrence (AC-5.3). |
| `code/build_web.py` | **New** | Zero-runtime splicer (OQ-5.1): read `web/replay.json` + the `web/quantum_galton.html` `id="replay"` block, write the embedded single-file HTML. Re-run after any P4 re-export (noisy fill / Phase-B hw). stdlib only; imports nothing physics-facing. |
| `code/parity_check.py` | **New** | The JS↔Python parity gate (§6, AC-5.4): extract the sentinel JS block from the HTML, run it under `node` against every replay histogram + synthetic decode inputs, assert equality to `metrics.py` / `walk_spec.decode_counts` within `1e-9`; one `PASS` line per metric, non-zero exit on mismatch. `subprocess` + `json` + `metrics`/`walk_spec`/`analytics`; no network, no QPU. |
| `code/SCHEMA.md` | **Edit** | Add a "P5 web parity" note: the `GALTON-PARITY-BLOCK` sentinel convention, the list of metrics the JS mirror must match, and the `build_web.py` embed step. **No `run.json` / `WALK_SPEC` / `summary.json` / `replay.json` key is added or changed** — replay is P4-frozen; P5 only documents how it is consumed. |

Nothing else is touched. `web/replay.json` is read, never rewritten (that is P4). The frozen
core (`walk_spec.py`, `walk.py`, `arms.py`, `pipeline.py`, `galton.py`, `metrics.py`,
`analytics.py`, and the P4 modules) is unchanged.

## 8. The three visual components (design, mirroring the source §THE VISUALIZATION)

- **Cascade (AC-5.1).** A triangular peg lattice of `n` rows for the current depth. An amplitude
  packet descends over `rAF`; on reaching the floor the bins ease (`current += (target-current)*k`)
  toward the active arm/depth histogram. The `classical⇄quantum` toggle cross-fades the *target*
  between `binomial_reference[n]` and the arm histogram — one visibly morphs into the other. Bin
  colors use the twin's accent gradient; the pile is drawn as vertical bars over the signed
  lattice `−n..+n` (step 2), decoded exactly as `WALK_SPEC` dictates.
- **Depth slider + arm toggle (AC-5.2).** The range spans `replay.depths`; each change retargets
  and eases the pile. The arm toggle switches which `per_arm` block feeds the targets; a null slot
  (Phase-A `noisy`/`hw`) renders greyed with an "awaiting hardware/noisy data — Phase B"
  caption (OQ-5.4) and disables that toggle until the slot fills. The HUD prints the depth's
  embedded `metrics` and the arm `knee_depth` (the "randomness-shape half-life"): on `ideal` it
  reads `null` (never collapses); on `noisy`/`hw` it marks the melt depth.
- **Interference glow (AC-5.3).** A JS analytic Hadamard-walk amplitude recurrence over the
  lattice colors each peg by its local constructive/destructive interference; a small side panel
  captions it "why it's not Gaussian" and "ideal amplitude phase (illustrative)". It is derived
  client-side from the ideal walk, not from replay probabilities, and is excluded from the parity
  gate (§6).

## 9. Manual verification (no automated tests)

1. **Parity gate (AC-5.4, the ship gate):** `python code/parity_check.py` exits 0 — every JS
   metric matches `metrics.py` within `1e-9` on all filled replay histograms, and `decodeCounts`
   matches `walk_spec.decode_counts` on the synthetic maps. Network-free, QPU-free, node-driven.
2. **Embed refresh (OQ-5.1):** `python code/build_web.py` splices the current `web/replay.json`
   into `web/quantum_galton.html`; diff shows only the `id="replay"` block changed.
3. **Open the file (AC-5.1/5.2/5.3):** double-click `web/quantum_galton.html` (from `file://`,
   no server). Confirm: the cascade fills and the `classical⇄quantum` toggle morphs the bell
   curve into the ideal twin horns; the depth slider walks `n = 2…18` on the `ideal` arm with the
   horns persisting (matching the on-disk `ideal` histograms and `knee_depth = null`); the metric
   readout equals the embedded `per_arm.ideal.by_depth[n].metrics`; the interference glow lights
   the lattice and is labeled illustrative; the `noisy`/`hw` toggles are greyed with the
   Phase-B caption (their replay slots are null today).
4. **Dark/light + self-contained:** toggle OS theme (and the `data-theme` control) — both render;
   the page loads with networking disabled (no CDN/framework/QPU calls).
5. **File-input override:** loading a raw `runs/*_run.json` via the input decodes through
   `decodeCounts` and shows a histogram consistent with the embedded arm — proving the JS
   decoder mirror on real measured counts.
6. **Tier-B dry run (when P4 fills an arm):** after P4 re-exports with `per_arm.noisy` (or
   Phase-B `hw`) populated, re-run `build_web.py` + `parity_check.py`; the greyed toggle lights
   and the noise-melt slider shows the horns collapsing toward the dashed hump past the knee —
   **with no P5 code change** (§1 Tier B).

## 10. Conventions & guardrails

- **Clone the twin's delivery**, don't invent a new stack: single self-contained HTML, inline
  CSS/JS, canvas + `requestAnimationFrame`, no framework, no CDN, no build tool at view time
  (epic §9 P5). Dark default + light override, matching `quantum_tree.html:1–50`.
- **Python is the source of truth (§3.6).** Every rendered variance/contrast/entropy/knee number
  either comes verbatim from the embedded replay (computed by `metrics.py` in P4) or, for a
  loaded raw run, from the JS mirror **that the parity gate has proven equal** to `metrics.py`.
  Never a third, unproven formula.
- **Keep the JS decoder in sync with `WALK_SPEC` by hand** (epic §5) — read the constants from
  `replay.walk_spec`, and let `parity_check.py` catch any drift before ship.
- **No live anything from the browser** (epic §9 P5 out-of-scope): no backend, no IBM account,
  no network at view time. The app replays recorded P4 data only.
- **Do not mutate frozen artefacts** — `web/replay.json` is read-only here (P4 owns it); the
  frozen core and the P4 modules are untouched. P5 adds `web/quantum_galton.html`,
  `code/build_web.py`, `code/parity_check.py`, and a `SCHEMA.md` note only.
- **The interference glow is illustrative, not measured** — label it, and keep it out of the
  parity gate so the page makes no false claim of hardware phase data (OQ-5.3).

## 11. Open questions — RESOLVED (2026-08-10, developer: "accept all defaults and approve")

All six accepted as proposed. Decisions bind the File Plan (§7) and the parity gate (§6) as
written; no further amendment needed before `/implement-feature`.

- **OQ-5.1 — Replay embed mechanism.** `[proposal]` Inline the replay JSON in a
  `<script type="application/json" id="replay">` block, refreshed by a `code/build_web.py`
  splicer after each P4 export (codegen, not a view-time build), plus the twin's file-input
  override for ad-hoc replays. Alternatives: runtime `fetch("./replay.json")` (breaks `file://`
  double-click, needs a server) or hand-paste (drift-prone). Recommend the splicer.
- **OQ-5.2 — Parity-gate runner.** `[proposal]` Run the extracted JS under **node 24** (present
  on this machine, verified) — the gate executes the exact shipping JS. Fallback if node is ever
  absent: print the Python reference JSON and compare manually in the browser console. Recommend
  node.
- **OQ-5.3 — Interference-glow data source.** `[proposal]` Compute it from a **client-side
  analytic Hadamard-walk amplitude recurrence**, label it "ideal amplitude phase (illustrative)",
  and **exclude it from the parity gate** (replay carries probabilities, not amplitude signs).
  Confirm this is acceptable framing (it explains *why* the ideal walk is twin-horned without
  claiming measured phase). Recommend yes.
- **OQ-5.4 — Null-arm rendering in Phase A.** `[proposal]` With `per_arm.noisy` / `per_arm.hw`
  null on disk today, render those arm toggles greyed/disabled with an "awaiting data — Phase B"
  caption; they light automatically when P4 fills the slots (no P5 edit). Confirm.
- **OQ-5.5 — Filename.** `[proposal]` `web/quantum_galton.html` (mirrors the twin's
  `web/quantum_tree.html`). Confirm.
- **OQ-5.6 — Tier-A ships before the noisy/hw arms exist.** `[proposal]` Build and verify P5 now
  against the on-disk `ideal` arm + `binomial_reference` (the full classical↔quantum morph,
  depth slider on ideal, and interference glow are complete today, epic §7 two-tier). The
  noise-melt slider is present but shows "awaiting data" until P4 fills `noisy`/`hw`. Confirm
  shipping Tier A now rather than blocking P5 on the P4 noisy/hw runs.

## 12. Dependencies & ordering

- **Depends on:** P1 (Complete — `WALK_SPEC` + `decode_counts`, the JS decoder mirror) and P4
  (Phase A Complete — `web/replay.json` with the `ideal` arm filled; the `noisy`/`hw` slots fill
  later with **no** P5 change). **Gates:** none (P5 is a leaf; P6 references its screenshots but
  does not import its code).
- **Runtime deps:** none added — pure browser HTML/Canvas at view time. **Dev/gate tool:** `node`
  (parity gate only, via `subprocess`; not a Python import, not shipped in the HTML).
- **Ordering within P5:** author `web/quantum_galton.html` (Tier A on the `ideal` arm) →
  `code/build_web.py` embed → `code/parity_check.py` gate green → manual browser walkthrough
  (§9). Tier B (`noisy`/`hw`) is a later `build_web.py` + `parity_check.py` re-run once P4
  populates those arms — no new P5 code.

## 13. Post-implementation notes

**Built (Tier A, 2026-08-10).** Three new files + one SCHEMA note, nothing frozen touched:
- `web/quantum_galton.html` — the self-contained spectacle (twin-styled, `"use strict"`,
  hand-rolled canvas + `requestAnimationFrame`, dark default + `prefers-color-scheme` light +
  `data-theme` toggle). Cascade waterfall, `classical ⇄ quantum` morph (dashed binomial hump ↔
  quantum bars), depth slider over `replay.depths`, ideal/noisy/hw arm toggle (noisy+hw greyed
  with a Phase-B caption while their replay slots are null), analytic interference glow
  (illustrative), and a file-input override that accepts **both** a `replay.json` (per_arm) and a
  raw `run.json` (counts→`decodeCounts` mirror). Replay embedded inline via `id="replay"`.
- `code/build_web.py` — the zero-runtime splicer (stdlib `json`+`re`); `web/replay.json` is
  read-only. Idempotent single-block replace, function-based sub (no regex backref expansion of
  the JSON payload).
- `code/parity_check.py` — the node-driven JS↔Python gate; extracts the sentinel block, runs it
  under `node` (v24.13 verified), asserts equality to `metrics.py` / `walk_spec.decode_counts`
  within `1e-9` over every filled arm/depth + synthetic decode maps. **Green:** all 8 PASS lines,
  exit 0.
- `code/SCHEMA.md` — added a "P5 web parity" section (sentinel convention, JS↔Python mirror table,
  embed step). No `run.json`/`WALK_SPEC`/`summary.json`/`replay.json` key added or changed.

**Parity note.** JS object key-iteration reorders non-negative integer-like keys ascending while
Python dict order is insertion; every metric mirror was written order-independent so this cannot
drift the result. The horn-contrast parity read uses `((k%2)+2)%2` to reproduce Python's
non-negative modulo (JS `%` keeps the sign). `localVarianceExponent` ports `numpy.polyfit(.,.,1)`
as a mean-centred OLS slope — matches to ≪1e-9.

**Verification (no automated tests, project directive).** Parity gate exits 0 (§9.1); `build_web.py`
diff confined to the `id="replay"` block (§9.2); the full inline script passes `node --check` and
boots + renders under a stubbed DOM without runtime error; a headless wiring check confirmed the
morph targets, depth retargeting, `ideal` knee=`null`, and the `noisy` null-slot (§9.3–9.5). These
node runs were throwaway diagnostics — **no test file was created or committed**. The `file://`
double-click browser walkthrough (§9.3 visual, dark/light §9.4) is the remaining manual step for
the developer to eyeball.

**Follow-ups (no P5 code change).** Tier B lights up automatically when P4 fills `per_arm.noisy`
(Phase-A noisy sweep, pending connectivity) / `per_arm.hw` (Phase B, ≥ 2026-08-15): re-run
`python code/build_web.py` then `python code/parity_check.py` — the greyed toggles go live and the
noise-melt slider shows the horns collapsing past the knee (§9.6).

---

*Plan drafted per epic §9 P5 and the P1/P3/P4 frozen contracts. No automated tests (project
directive, epic §3.6) — verification is the node-driven JS↔Python parity gate
(`parity_check.py`) + a manual browser walkthrough. Two-tier delivery (epic §7): Tier A (ideal↔
classical morph, depth slider, interference glow) ships now on the on-disk `ideal` replay; the
noise-melt slider lights when P4 fills `per_arm.noisy` / `per_arm.hw`, with no P5 code change.
Status stays Draft until the developer answers §11 and approves.*
