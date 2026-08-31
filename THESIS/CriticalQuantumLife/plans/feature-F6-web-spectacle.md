# Feature Plan — F6: Web spectacle — "Life You Can Poke" (`life_you_can_poke.html`)

**Status:** Draft
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F6 (depends on F0 + F4; readouts firm up as F2/F3 land)
**Artifact:** `THESIS/CriticalQuantumLife/web/life_you_can_poke.html` (new, single self-contained file)
**Mirrors:** `QuantumLife/web/quantum_tree.html` (single-file canvas aesthetic, theme system)
**Reads:** `research_runs/*.json` (F0 runs + F2 `criticality` + F3 `panel`) as the hardware overlay
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.
> **The primary public artefact / headline figure of the whole program** (epic §1, Q6).

---

## 1. Context & goal

F6 is the **primary public artefact**: a single self-contained HTML canvas dashboard, in the
`QuantumLife/web/quantum_tree.html` style, that makes the whole claim visible and interactive. A swarm of glowing
genome-individuals with a generation counter; a **criticality dial** hovering at σ=1 between a frozen-blue dead
zone and a boiling-red chaos zone; an **avalanche histogram** snapping onto the −3/2 power-law line; a **falling
surprise meter**. An interactive **POKE button** (calling F4's poke semantics in an in-browser toy loop) spikes the
surprise, lurches the needle, scrambles the swarm — then you watch it crawl back to the edge of chaos over the next
generations. Beside it, a ghosted **yoked-control panel** pokes identically and never recovers — the adaptation
honesty gate made visual. Real `research_runs/` hardware traces overlay as the "this actually happened on IBM"
layer (epic Q5), so the demo is honest, not just a pretty toy.

F6 has **two data sources** (epic Q5): a **live in-browser toy closed-loop** (JS, no QC — instant POKE
interactivity) and **real hardware traces** loaded from F0/F3 run-JSON overlaid on the same axes.

### What already exists (integration points)
- `QuantumLife/web/quantum_tree.html` — the single-file template: `:root` CSS vars, `@media (prefers-color-scheme)`
  + `:root[data-theme="dark"|"light"]` overrides, `<canvas id="c">` full-bleed, inline `<style>`/`<script>`.
- F4 `session.py` `POKE_KINDS = ("flip_expected", "alter_selection", "inject_stimulus")` + poke semantics — the
  JS toy loop mirrors these (same vocabulary so the button maps 1:1 to the Python reference).
- F2 `criticality` block (σ, α, entropy plateau, τ) + F3 `panel` (quantum vs surrogate witness per gen) — the
  hardware-overlay data the dials read.
- Epic §9 F6 ACs + Q5 (both live + real) + the honesty-gate-is-law rule (the yoked ghost panel is mandatory).

---

## 2. Acceptance criteria

Verbatim from epic §9 (F6). IDs added.

- **AC-F6.1** (verbatim): "Single self-contained HTML file (inline CSS/JS, canvas-driven), theme-aware
  (dark/light via `prefers-color-scheme` + `data-theme`), hosted-ready — mirroring `QuantumLife/web/quantum_tree.html`."
- **AC-F6.2** (verbatim): "Live glowing genome swarm + generation counter."
- **AC-F6.3** (verbatim): "Three dominant readouts: criticality dial (needle at σ=1, dead↔chaos gradient),
  avalanche histogram converging to the −3/2 line, surprise meter falling over generations."
- **AC-F6.4** (verbatim): "An interactive **POKE** button calling the F4 poke semantics (in-browser toy loop):
  surprise spikes, needle lurches, swarm scrambles, then relaxes back to criticality over following generations."
- **AC-F6.5** (verbatim): "A ghosted yoked-control panel that pokes identically and does NOT recover — the honesty
  gate made visual; mandatory, not optional."
- **AC-F6.6** (verbatim): "Real `research_runs/` hardware traces overlaid/loadable as the 'this actually happened
  on IBM' layer (per Q5), keeping the demo honest, not just a pretty toy."

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New single file `web/life_you_can_poke.html`: inline CSS/JS, canvas swarm + three readouts + POKE button + yoked
  ghost panel + hardware-trace overlay. Theme-aware, hosted-ready, no build step, no external requests.
- A JS **toy closed-loop** mirroring F4's poke semantics (flip-expected / alter-selection / inject-stimulus) for
  instant in-browser interactivity — a faithful cartoon of the Python loop, NOT a physics engine.
- A loader for real `research_runs/` JSON (F0 `generations[]` + F3 `panel` + F2 `criticality`) as the honest
  hardware overlay (fetch a bundled/pasted JSON — no live QC).

### Out of scope (deferred / forbidden)
- Any live QC call from the browser (epic §9 F6 out-of-scope) — the swarm is a JS toy; reality comes from the
  loaded run-JSON. A Next.js app or any framework/build step — single-file static HTML only. New metrics — the JS
  reproduces F2/F3 definitions; it does not invent them.

---

## 4. Data model — what the page reads

Two inputs, both already produced upstream (F6 defines no new schema):

- **Live toy loop (JS, in-memory):** a `population[]` of genome sprites, a `runningDist{}`, per-tick
  `{gen, surprise, sigma, entropy, witnessSignal, avalanches[]}` — the JS analogue of F0's `generations[]` row,
  computed client-side each animation tick. Mirrors F0 field names.
- **Hardware overlay (loaded JSON):** F0 run-JSON `generations[]` (`surprise`, `sigma`, `witness_signal`, `poke`),
  F3 sidecar `panel[]` (`quantum_signal`, `surrogate_signal`, `null_band`), F2 `criticality` (`sigma.mean`,
  `avalanche_alpha.alpha`, `relaxation_tau.tau`). The page ships one embedded default trace (the POC / an F5 run)
  and accepts a pasted/loaded JSON to swap it.

To stay self-contained (CSP: no external fetch when hosted as an artifact), the default hardware trace is **embedded
inline** as a `const HW_TRACE = {...}` at build time; a "load run" control accepts a pasted JSON for other runs (Q3).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Single-file static HTML canvas, `QuantumLife/web/` aesthetic** (epic §3/§9) — inline CSS/JS, theme-aware,
  hosted-ready, self-contained. NOT Next.js, no build.
- **The yoked ghost panel is MANDATORY** (epic §3/§9 F6, honesty gate 1 made visual) — the page must show the
  yoked control poking identically and never recovering, beside the closed-loop arm. Not optional, not hidden.
- **Honest hardware overlay** (epic Q5, honesty rule) — real IBM traces overlaid so the spectacle is anchored to
  data, not just a toy. The "this happened on IBM" layer is required.
- **Two data sources** (epic Q5) — live toy loop for instant POKE + real run-JSON overlay. No live QC in-browser.
- **One poke vocabulary** (epic §3) — the JS POKE calls the same `POKE_KINDS` F4 defines, so the demo and the
  Python/hardware results are the same interaction.

---

## 6. File plan (concrete paths)

One new self-contained file. No build, no deps, no external requests.

### `THESIS/CriticalQuantumLife/web/life_you_can_poke.html` (new)

Structure (mirror `quantum_tree.html` top-to-bottom):

1. **`<head>`** — `<title>Life You Can Poke</title>`; `<meta name="viewport">`; inline `<style>`:
   - `:root{ --bg --bg2 --fg --dim --accent --dead(blue) --chaos(red) --crit(green) ... }`
   - `@media (prefers-color-scheme: light){ :root{...} }` + `:root[data-theme="dark"]{...}` +
     `:root[data-theme="light"]{...}` — the QuantumLife theme system, both directions win.
   - Layout: full-bleed `<canvas id="c">` for the swarm; an overlay grid (CSS grid/flex) for the three readouts +
     the POKE button + the yoked ghost panel; `overflow-x` guarded (no horizontal body scroll).
2. **`<body>`** — `<canvas id="c">`; an HUD: generation counter, criticality dial `<canvas>`, avalanche histogram
   `<canvas>`, surprise meter `<canvas>`, the **POKE** `<button>` (+ a kind selector for the three `POKE_KINDS`),
   a theme toggle, a "load hardware run" control, and the **ghosted yoked panel** (a dimmed mirror of the swarm +
   its own surprise meter).
3. **`<script>` (inline, no modules):**
   - **Theme** — `data-theme` toggle stamping `:root`, mirroring `quantum_tree.html`.
   - **Toy population** — `Genome` sprites (position, glow ∝ fitness, color ∝ σ-zone); `stepGeneration()` runs the
     cartoon closed loop: measure a toy outcome → update `runningDist` → `surprise = -log P` → contingent feedback
     (predictable vs high-entropy) → select/reproduce/mutate → recompute σ, entropy, avalanches, witnessSignal.
   - **Yoked twin** — a second population fed the SAME poke sequence but non-contingent feedback; never recovers.
   - **`poke(kind)`** (AC-F6.4) — `flip_expected` / `alter_selection` / `inject_stimulus` (the F4 vocabulary):
     spike surprise, lurch the dial, scramble the swarm; the closed arm relaxes over the next gens, the yoked twin
     does not (AC-F6.5).
   - **Readouts (AC-F6.3):** `drawDial(sigma)` (needle at σ=1, dead-blue↔chaos-red gradient, crit-green at 1);
     `drawAvalanche(hist)` (log-log bars snapping onto the −3/2 reference line); `drawSurprise(series)` (falling meter).
   - **Hardware overlay (AC-F6.6):** `loadHardware(json)` parses an F0 run + F3 panel; overlays the real
     `witness_signal` / `surprise` as a distinct "IBM" trace on the meters and a witness-vs-surrogate strip from the
     F3 `panel`; `const HW_TRACE = {...}` embedded default (the POC or an F5 run).
   - **`requestAnimationFrame` loop** — advance the toy loop at a watchable rate, redraw swarm + readouts + ghost.
4. No external assets — any icon/gradient is canvas-drawn or a data-URI; fonts are system stack.

No other files. Hosted-ready: opening the file (or publishing as an artifact) needs no server, no network.

---

## 7. The spectacle contract (what F6 must get right)

- **Honest, not just pretty** — every visual maps to a gate: the dial = criticality gate (σ≈1, not 0/∞), the
  avalanche −3/2 line = the α criticality signature (F2), the surprise meter = the adaptation gate, the ghost
  panel = the yoked control, the IBM overlay = the quantum gate (witness above surrogate). A visual with no
  gate behind it is a bug (epic honesty rule).
- **The ghost panel is the best figure in the program** (epic §1) — closed arm recovers after the poke, yoked twin
  pokes identically and stays scrambled. Make the contrast unmissable.
- **The POKE is the F4 interaction** — same three kinds, same "change contingency → surprise spikes → reorganize"
  story, so a viewer clicking POKE sees the exact interaction F5 runs between hardware batches.
- **Toy ≠ physics** — the in-browser loop is a faithful cartoon (fast, illustrative); the "this really happened"
  claim rides entirely on the loaded hardware trace. Label the toy as a toy; label the overlay as real IBM data.

---

## 8. Manual verification (no automated tests)

Open `THESIS/CriticalQuantumLife/web/life_you_can_poke.html` in a browser (and/or publish as an artifact):

- **AC-F6.1** — single file, no network requests (check devtools Network tab is empty); toggling OS theme and the
  in-page theme button both restyle correctly (dark ↔ light), mirroring `quantum_tree.html`.
- **AC-F6.2** — a glowing genome swarm animates; a generation counter increments.
- **AC-F6.3** — the criticality dial needle sits near σ=1 between blue/red zones; the avalanche histogram tracks the
  −3/2 line; the surprise meter falls as generations advance.
- **AC-F6.4** — clicking POKE (each of the three kinds) spikes the surprise, lurches the needle, scrambles the
  swarm; over the next generations the closed arm relaxes back toward σ=1.
- **AC-F6.5** — the ghosted yoked panel pokes at the same moment and does NOT recover; the contrast is visible
  side-by-side. Removing it should be impossible without breaking the page (it's mandatory, not a toggle).
- **AC-F6.6** — the embedded IBM trace overlays as a distinct layer; loading/pasting an F5 run-JSON swaps it; the
  witness-vs-surrogate strip (F3 `panel`) shows the quantum trace above the surrogate null band.
- **Responsive** — no horizontal body scroll at narrow widths; readouts reflow.

---

## 9. Out-of-context risks / notes

- **CSP self-containment.** If published as a claude.ai artifact, a strict CSP blocks all external hosts — so
  inline every asset, embed the default HW trace, and never `fetch()` a remote URL. A local `research_runs/` file
  load must be via a file-input/paste, not a network fetch, to survive hosting.
- **Toy-vs-real honesty.** The single biggest failure mode is the demo reading as "quantum life running live in
  your browser." It must be labelled: the swarm is a cartoon; the IBM overlay is the real data. Keep that label
  prominent (epic honesty rule).
- **Readouts must match F2/F3 definitions.** The JS α reference line is −3/2 (F2), the dial target is σ=1 (F2), the
  null band is F3's — reproduce the definitions, don't drift. When F2/F3 land, reconcile the JS constants to them.
- **Data-shape coupling.** The overlay loader reads F0 `generations[]` + F3 `panel` field names — if those change,
  the loader breaks. They are the epic §4 contract (frozen by F0/F3), so this is low-risk, but note it.

---

## 10. Ground rules honored

- Every AC (F6.1–F6.6) verbatim from epic §9, mapped to a §8 manual check.
- One concrete file path; single-file static HTML, `QuantumLife/web/` aesthetic, theme-aware, self-contained.
- The yoked ghost panel + the honest IBM overlay are required, not optional (epic honesty rule).
- No tests / no test sections. No framework, no build, no external requests.

---

## 11. Open questions (defaults proposed)

- **Q1 — Toy-loop fidelity.** *Proposed default:* a faithful cartoon of F0's loop (same field names, same poke
  vocabulary) tuned for watchability, explicitly labelled a toy. Accept, or drive the toy loop from a small
  pre-computed sim trace embedded inline (more faithful, less interactive)?
- **Q2 — Default embedded hardware trace.** *Proposed default:* embed the POC `ibm_kingston` witness trace as the
  shipped "this happened on IBM" overlay until an F5 run exists, then swap in the F5 W=8 run. Accept?
- **Q3 — Loading other runs.** *Proposed default:* a paste-JSON / file-input control (no network) so the page stays
  CSP-safe when hosted. Accept, or also support a same-origin `fetch('../research_runs/..')` for local use?
- **Q4 — Palette.** *Proposed default:* the `quantum_tree.html` green-forest theme vars, extended with a
  blue(dead)↔green(critical)↔red(chaos) dial gradient. Accept, or a distinct CQL palette?
