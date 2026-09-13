# Feature: Web index refactor — borderless CQL hero + one-page accordion-folded study

**Slug:** web-index-borderless-refactor
**Epic:** `plans/epic-qalife-darwinian-richness.md` — Phase 2 (P4 web strand; standalone web deliverable, not a code stage)
**Stage ID:** WEB (P4 web demo; no code-science AC)
**Target file:** `artificial-life/web/index.html` (single self-contained file — the only file edited)
**Author:** Claude (Opus)
**Date:** 2026-09-13
**Status:** Approved

> **No tests** (repo directive). Production HTML/CSS/JS + manual visual verification only.
> **No new physics / no new runs.** Presentation refactor of already-banked, already-measured results.
> Every number is copied verbatim from the three conclusion pages / the banked circuit dumps; none is recomputed.

---

## 1. Overview & intent

Rebuild `artificial-life/web/index.html` into **one self-contained page** that is a **spectacle on first
glance and a rigorous, truthful study on second glance**. Two design moves and one structural rule from the
developer:

1. **Hero: inline-canvas, borderless, slowed.** Port the wave-bars animation currently rendered in the
   `spectacle.html` **iframe** into an **inline `<canvas>`**, rendered the way
   `THESIS/CriticalQuantumLife/web/spectacle.html` does its `#life` canvas: full-bleed, edge-to-edge, filling
   the viewport as the background, with the chrome (eyebrow, live gates, heartbeat, readouts) **floating over
   it** as HUD overlays with **no surrounding frame**. Drop the iframe entirely. Keep the live values. Slow
   the animation ≈2×.

2. **Content: expand a lot, no clutter, QuantumLife-style.** Adopt the `QuantumLife/web/index.html` device —
   native `<details>` accordions for progressive disclosure. The default (mostly-collapsed) view reads as a
   clean spectacle; **every rigorous detail — full tables, circuits, honest-scope caveats, run logs — lives
   inside the expandable bars.**

3. **One page, no deep-dive links (Q7).** There are **no** links out to `pj0_/p2_/pj1_conclusion.html` or any
   other page. **All** their content is inlined here, folded into accordions. The **only** external link
   anywhere on the page is **`https://tree.peterjas.sk/`**. The three conclusion HTML files stay on disk but
   are no longer referenced.

**Three content blocks, in this order** (developer-specified — the *win* leads so the first thing read is why
it is interesting / what happened):

- **Block B — "The win" (P2 + PJ0).** First. The old design hit a wall; the new design moved it. Heavy text.
  One combined width table (unitary ceiling from P2 + width sweep from PJ0) with the new germ/soma design as
  the most visible line; the **four designs considered** (the four ASCII circuits from `pj0_conclusion.html`)
  and why germ/soma won; the **original P2 damping design shown in more detail** (the banked qiskit circuit
  dump); the 2×2 factorial "phenotype coupling is the kill switch" as a data-fill table; all P2 axes
  (unitary / damping-width / damping-depth) + confounds folded into accordions.
- **Block A — "What is happening" (PJ1).** Second. The arena: how the two bodies *collided* and *why they are
  organisms*, with the full 12-frame collision data + honest scope, folded.
- **Block C — "How this was built" (the beginning).** Last. Where the program came from (`tree.peterjas.sk`,
  102-qubit teleported genome) and the method it inherits (one certified witness, sim-first hardware-confirm,
  no speedup), with the reproduce recipe folded.

Static single file: inline CSS/JS, no build step, no external asset except the optional existing
`pj1_witness.png` and the `tree.peterjas.sk` hyperlink.

---

## 2. Acceptance criteria

Each manually verifiable in a browser.

- **AC-1 (hero = inline canvas, no iframe):** The wave-bars animation is rendered by an **inline `<canvas>`**
  in `index.html` (the `spectacle.html` iframe is removed). The renderer is the wave-bars renderer ported from
  `spectacle.html` (bars + glowing wave envelopes + interference flare + travelling A/B heads), driven by the
  same banked 12-frame PJ1 `DATA`.
- **AC-2 (borderless full-bleed, CQL treatment):** The canvas fills the stage edge-to-edge
  (`position:absolute;inset:0`, `100svh`, no border, no boxed card); eyebrow, gate readouts and heartbeat are
  **floating HUD overlays** (absolute, glass `backdrop-filter`, no outer frame), matching CQL's
  `.hud-tl` / `.hud-tr` / `.hud-bottom`; a `.veil` vignette + `.grain` sit over the canvas.
- **AC-3 (live values):** Top-right gate cards + bottom heartbeat + a frame/clock line show **live** values
  advancing with the animation — genealogy witness ⟨X⊗2W⟩, body overlap, frame counter, hardware line —
  interpolated from the same `DATA` frames.
- **AC-4 (slowed ≈2×):** The animation is ≈2× slower than the current builds — the ported wave-bars playback
  step (`spectacle.html`'s `pos += dt*0.006*SUB` → ≈`0.003`) and the heartbeat clock (`SEC_PER_FRAME` 1.6 →
  ≈2.9). Final by eye (§7 resolved: 2×).
- **AC-5 (block order):** Page order is Hero → **Block B (the win)** → Block A (PJ1) → Block C (how built).
- **AC-6 (Block B — combined table):** One combined width table shows **three designs on the same W axis** —
  P2 unitary ceiling, P2 faithful damping-death wall, PJ0 germ/soma sweep — with the **germ/soma column
  visually dominant** (the "most visible line"). Numbers verbatim (§5). Null-≈0 note present.
- **AC-7 (Block B — four designs, verbatim circuits):** The **four designs considered at W=4** are shown using
  the **four ASCII circuits from `pj0_conclusion.html`** (`.design .ckt` blocks 1–4, verbatim) with the
  winner marked and the per-axis rationale.
- **AC-8 (Block B — original design in detail):** The **original P2 damping design** (the version that was
  later improved) is shown in more detail via the banked qiskit circuit dump
  `research_runs/originalP2/3.1-draw-only_circuit_w2_s1.txt`, inlined verbatim in a `<pre>` (scrollable), with
  a caption identifying it as the amplitude-damping W=2 circuit that the final channel improved on.
- **AC-9 (Block B — kill switch):** The **2×2 factorial** ("the phenotype coupling is the kill switch") is a
  data-fill table, all four cells verbatim (§5).
- **AC-10 (Block B — full P2 rigor, folded):** The P2 unitary table, damping-width table, damping-depth table,
  and confound/decision-gate prose are all present, folded into accordions.
- **AC-11 (Block A — what is happening / PJ1):** A section explains in plain language **what is happening** —
  how the two bodies collided (walk from opposite ends of an 8-site track; measured occupancy overlap climbs
  0.00→0.72) and **why they are organisms** (each = a germ/soma individual: clean 12-qubit genealogy + moving
  body). The full 12-frame table + honest scope (witness insulated by design; body-body entanglement sim-only)
  are present, folded.
- **AC-12 (Block C — how built):** Origin + inherited method present; **`https://tree.peterjas.sk/`** linked;
  reproduce recipe folded.
- **AC-13 (spectacle-first / rigorous-second):** First-glance view is clean — hero + short block intros, only
  the first accordion (if any) open. Everything rigorous is reachable by expanding bars. All heavy content is
  behind native `<details>` (pure-CSS `+`/`–` marker via `::before` + `[open]`, no JS toggles).
- **AC-14 (no external pages):** No hyperlink to `pj0_/p2_/pj1_conclusion.html` or any page other than
  `tree.peterjas.sk`. All their load-bearing content is inlined.
- **AC-15 (self-contained & responsive):** Single static file, inline CSS/JS, no build step, no new external
  dependency. No horizontal page scroll on mobile; every table/`<pre>` wrapped in `overflow-x:auto`; hero HUD
  reflows (`@media(max-width:820px)`).
- **AC-16 (honesty invariant, CD-3/CD-4):** States the witness is the sole quantum claim, every diagonal
  metric has a classical surrogate, the null sits at ≈0, and the contribution is **scale · faithfulness ·
  certification — not a speedup**. Body-body entanglement labelled sim-only.

---

## 3. Out of scope

- Any new physics, operator, hardware run, or recomputation (data frozen).
- Editing the conclusion pages or `spectacle.html` (the renderer is **copied inline**, not imported; those
  files are left on disk untouched, just unreferenced).
- A sticky section-nav / TOC / scrollspy (§7 resolved: none).
- Light-theme support — dark-only, matching the family.
- Body-body entanglement measurement/claim (sim-only, stated as such).
- SEO/meta beyond the existing `<title>` + `<meta description>`.

---

## 4. Design language

**Keep the existing `index.html` `:root` palette** (already CQL-aligned: `--bg:#05070d`, `--witness:#37e6d4`,
`--A/--A2/--B/--B2` organism colours, `--good/--bad/--gold`, `--mono`, `--r:16px`, `--maxw:1180px`). Extend
only as needed for accordions / HUD.

**Hero — inline canvas, from `CriticalQuantumLife/web/spectacle.html` (§ the `#life` treatment):**
- `.stage{position:relative;height:100svh;min-height:640px;overflow:hidden}` with CQL's twin radial-gradient
  background.
- `<canvas id="life">` `position:absolute;inset:0;width:100%;height:100%;display:block` — the full-bleed layer
  (replaces the iframe). DPR-fit via CQL's `wrap()` helper (ResizeObserver + `devicePixelRatio`).
- `.veil` (radial vignette) + `.grain` overlays above the canvas, `pointer-events:none`.
- HUD overlays, `position:absolute;z-index:5`, **no frame**:
  - `.hud-tl` (top-left): eyebrow (pulsing dot) + `h1` + lede + `.clock` (frame counter + live tag).
  - `.hud-tr` (top-right): `.gate` glass cards (`background:var(--panel);backdrop-filter:blur(9px)`) —
    genealogy witness (certified/at-null state), body overlap, hardware line. Reuse current gate markup,
    restyle to CQL gate spec (`pass/weak/fail` colour states).
  - `.hud-bottom`: the `#heart` canvas (witness+overlap EKG, kept from current index) + caption/readout over a
    `linear-gradient(180deg,transparent,rgba(3,5,11,.72))` scrim.
  - `.cue` ("scroll ↓") bottom-center.
- `@media(max-width:820px)`: `.hud-tr` static/wrapping, `.hud-bottom` single-column, `.cue` hidden (CQL rules).

**Hero renderer (ported from `artificial-life/web/spectacle.html`):**
- Copy inline: the `DATA` object (12 real PJ1 frames), `frameAt` (frame interpolation), `smooth` (Catmull-Rom
  envelope), `stats`, `rr`, and `draw(fr)` (phosphor grid, additive bars per organism, glowing wave envelopes,
  interference flare where both bodies overlap, travelling A/B heads with droplines/labels).
- Adapt `draw()` from spectacle's fixed 920×340 canvas to the responsive DPR-fit `#life` canvas — it already
  uses `cv.width/cv.height` with relative `base=h*0.80`, `amp=h*0.62` (only `pad=50` is fixed; keep or scale).
- Drive it from a single slowed clock; feed the interpolated frame to `#life`, to `#heart` (EKG), and to the
  gate/clock readouts each rAF tick. Keep a reduced-motion static frame (paint mid-collision, no loop).
- Slow: playback step `dt*0.006*SUB` → ≈`0.003*SUB`; heartbeat `SEC_PER_FRAME` 1.6→≈2.9. Prefer a ping-pong
  clock (0↔11↔0) to avoid the hard reset jump spectacle's linear loop has.

**Content region — from `QuantumLife/web/index.html`:**
- Native `<details>` accordions as the disclosure device (pattern, adapt colours):
  ```html
  <details class="acc">
    <summary>Full frame-by-frame data (measured)</summary>
    <div class="acc-body"> …content… </div>
  </details>
  ```
  ```css
  .acc{border:1px solid var(--line2);border-radius:var(--r);
       background:linear-gradient(180deg,rgba(13,20,36,.5),rgba(8,12,22,.5));overflow:hidden;margin:14px 0}
  .acc>summary{list-style:none;cursor:pointer;user-select:none;display:flex;gap:11px;align-items:center;
       padding:15px 18px;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--witness)}
  .acc>summary::-webkit-details-marker{display:none}
  .acc>summary::before{content:"+";color:var(--gold);width:15px;text-align:center;flex:none}
  .acc[open]>summary::before{content:"\2013"}
  .acc-body{padding:6px 18px 18px}
  ```
- Keep the existing `section`/`.sec-eyebrow`/`h2`/`.big` rhythm for always-visible copy; move dense material
  into `.acc` bodies (AC-13).
- Tables: existing `.scroll{overflow-x:auto}` + `table` styling; reuse `tr.new{color:var(--good)}` /
  `tr.old{color:var(--bad)}` for the combined table's highlighted new line. ASCII circuits/dumps in
  `<pre>` inside an `overflow-x:auto` wrapper, monospace, small (`.ckt`-style).

---

## 5. Content spec (exact data — copy verbatim, do not recompute)

### Block B — "The win" · P2 + PJ0 (first block)

**Always-visible copy** (the story of the wall and the cut — heavy text):
- P2 drove the faithful 2018 death channel to its limit: with real amplitude-damping death in the loop, the
  genealogical witness collapsed at **W\* = 9 = 19 qubits**. Mechanical diagnosis — the death operator couples
  the mortal soma to the immortal germ line (`cx(g,p)`) then dissipates it, so body-death irreversibly
  decoheres the gene-witness. A **biology wall**, not a hardware one.
- PJ0 builds the **Weismann barrier**: germ line carries the GHZ witness and stays coherent; the soma is a
  separable diagonal trait dying in isolation (natural T1, no bath, no `cx(g,p)`). Severing that one coupling
  moved the certified ceiling to **W = 50 = 100 qubits (k=3σ)** — the run stopped only because the chip ran
  out of clean qubits (needs a 108-chain; longest clean is 107). **The machine ran out before the witness
  did** — the limiting resource flipped from entanglement to machine size.
- Honest: witness is **certified, not strong**, at the top (+0.058 at W=50, ~5σ over null, far below a fresh
  GHZ's ~0.9). Scale · faithfulness · certification — not a speedup. N=1 per width.
- The A/B one-liner: at W=4 the severed design reads **+0.899**; restoring the old `cx(g,p)` wound collapses
  it to **+0.120**. The coupling *is* the mechanism.

**Combined width table (AC-6)** — one W axis, three designs, germ/soma the visible line; blank where a design
was not measured; genealogy qubits = 2W (damping mode adds +1 shared bath ancilla physically). Verbatim from
P2 Table 1 (unitary), P2 Table 2 (damping), PJ0 Table 2 (germ/soma):

| W | qubits (2W) | Old · unitary ⟨X⊗W⟩ | Old · damping-death ⟨X⊗W⟩ | **New · germ/soma ⟨X⊗W⟩** |
|--:|--:|--:|--:|--:|
| 2 | 4 | +0.959 | +0.814 | — |
| 3 | 6 | +0.879 | — | — |
| 4 | 8 | +0.808 | — | — |
| 6 | 12 | +0.612 | +0.542 | **+0.870** |
| 8 | 16 | — | +0.468 | — |
| 9 | 18 | — | +0.171 (last alive) | — |
| 10 | 20 | — | +0.022 (dead) | — |
| 12 | 24 | +0.301 | −0.005 (dead) | **+0.756** |
| 16 | 32 | — | — | **+0.296** |
| 24 | 48 | +0.038 (k=2 only) | — | **+0.193** |
| 28 | 56 | — | — | **+0.355** |
| 32 | 64 | +0.008 (dead) | — | **+0.271** |
| 36 | 72 | — | — | **+0.220** |
| 40 | 80 | — | — | **+0.067** |
| 42 | 84 | — | — | **+0.068** |
| 46 | 92 | — | — | **+0.081** |
| 50 | 100 | — | — | **+0.058 (last certified, k=3σ)** |
| 54 | 108 | — | — | — abort · no clean 108-chain |

Highlight the New column (`--good` / heavier weight / `tr.new` treatment). Note under it: **separable null ≈ 0
everywhere** (P2 ≤ 3×10⁻⁷; PJ0 ≤ 10⁻¹³) — off the chart. Unitary axis exhausted at W\*=24 (geometric decay,
"bigger GHZ, same biology"); damping wall at W\*=9; germ/soma certified 5.5× further to W=50, stopped by qubit
count.

**Four designs considered (AC-7)** — verbatim ASCII circuits from `pj0_conclusion.html` (`.design .ckt`), each
with its heading, sub, verdict:

1 · **natural + separable — WINNER** · 2 qubits/individual · no bath · witness +0.899
```
g_k: ─[clone]─Ry(θ)──────────────●─H─M
p_k: ─Ry(aged)── idle ⇒ real T1 ────M
```
Germ and soma never share a gate. Soma idles and dies by real hardware T1. No `cx(g,p)`, no bath. Leanest.
▲ witness intact

2 · **local_damping + separable** · 3 qubits/individual · +bath · witness +0.768
```
g_k: ─[clone]─Ry(θ)────────────●─H─M
p_k: ─Ry(aged)─●──────X──────────M
              │cry    │cx
b_k: ─────────X───────●────────  (discarded)
```
Germ still safe (no `cx(g,p)`), but death is faked with ancilla + `cry`+`cx`: +1 qubit, 2 extra 2-qubit gates,
rigid tunable rate. ▲ alive, but heavier

3 · **natural + entangled** · 2 qubits/individual · witness +0.120
```
g_k: ─[clone]─Ry(θ)─●──────────H─M
                   │cx(g,p) ← P2 wound
p_k: ─Ry(aged)─────X─ idle⇒T1 ─H─M
```
The `cx(g,p)` couples the mortal soma to the immortal germ; soma decay back-acts and decoheres the
gene-witness. ▼ 0.90 → 0.12 collapse

4 · **local_damping + entangled — WORST** · 3 qubits/individual · witness +0.079
```
g_k: ─[clone]─Ry(θ)─●──────────H─M
                   │cx(g,p)
p_k: ─Ry(aged)─────X─●────X────H─M
                     │cry │cx
b_k: ────────────────X────●───
```
Both wounds at once — soma coupled to germ **and** dissipated through a bath — the P2 death channel doubled.
▼ floor

Then the "wins on every axis" table (verbatim, PJ0 Table 1b):

| axis | natural+sep ✓ | damp+sep | nat+ent | damp+ent |
|:--|--:|--:|--:|--:|
| witness ⟨X⊗4⟩ (live) | **+0.899** | +0.768 | +0.120 | +0.079 |
| qubits / individual | 2 | 3 | 2 | 3 |
| 2-qubit gates / individual | 1 | 3 | 2 | 4 |
| germ↔soma coupled? | no | no | yes | yes |
| bath qubit? | no | yes | no | yes |
| death = real T1 physics? | yes | no | yes | no |
| max width on 107-clean-chain | ~53 | ~35 | ~53 | ~35 |
| tunable/rigid death rate? | no (T1 drifts) | yes | no | yes |

Why (condensed, PJ0): fewer 2-qubit gates → less error → higher witness; no bath → 2 qubits/individual → *why
W=50 was reachable*; natural T1 death is the faithful model; damping kept only as a rigid-rate reference (sole
win: reproducibility).

**Original P2 damping design in detail (AC-8)** — the version that was improved. Inline verbatim in a
scrollable `<pre>` the banked dump `research_runs/originalP2/3.1-draw-only_circuit_w2_s1.txt` (the qiskit W=2,
steps=1 amplitude-damping circuit: two individuals `ind0/ind1`, `Ry(π/2)` founder, `Ry(0)` mutation, clone
`cx`, the bath ancilla `q_4` with `Ry(0.8763)` + `cx` + reset `|0>`, `interaction` swap barrier, then
`H`/`M` X-basis witness readout on 5 classical bits). Caption: *the original amplitude-damping channel (W=2,
γ per generation) — unstable at W=2 (runs −0.04…+0.35); the final rebuilt channel lifted W=2 to +0.814 and
pushed the width ceiling to W\*=9.* Fold in an accordion.

**2×2 factorial — the phenotype coupling is the kill switch (AC-9)** — data-fill table verbatim (PJ0 Table 1,
ibm_kingston, W=4, steps=4, shots 8192, σ≈0.011):

| soma death | phenotype | ⟨X⊗4⟩ | verdict |
|:--|:--|--:|:--|
| natural | separable | +0.899 | alive |
| local_damping | separable | +0.768 | alive |
| natural | entangled | +0.120 | collapsed |
| local_damping | entangled | +0.079 | collapsed |

Caption: the **phenotype axis decides everything** — separable keeps the witness alive (0.77–0.90); entangled
(restores the `cx(g,p)` wound) collapses it (0.08, 0.12). The P2 diagnosis, confirmed live.

**Accordions holding the rest of P2/PJ0 rigor (AC-10, all verbatim):**
- *P2 · unitary genealogy — witness vs width* (Table 1: W 2/3/4/6/12/24/32 → +0.959…+0.008; W\*=24=48q, k=2σ).
- *P2 · damping-death width sweep, final channel* (Table 2: W 2/6/8/9/10/12 → +0.814…−0.005; W\*=9=19q).
- *P2 · damping-death depth sweep* (Table 3: W4s4 +0.131, W5s4 +0.111, W5s5 +0.049, W6s5 +0.138, W6s6 +0.013;
  real death survives 5 generations, dies at the 6th).
- *P2 · confound & significance + decision gate* (fail-closed chain gate; null ≤3×10⁻⁷; sharp single-unit
  cliffs = death-channel entropy not drift; unitary/damping-width/damping-depth all exhausted → P3 gate opens).
- *PJ0 · width sweep detail* (Table 2 full, k=2/k=3 ticks; Figure-1 caption; last certified W=50).
- *PJ0 · the wall, verbatim* (W=54 runlog: 108 needed, dead qubits 112/113/120/121/146 dropped, longest clean
  chain 107 — gate holds, chip does not).
- *PJ0 · confound & honesty + decision gate* (null ≤10⁻¹³; certified-not-strong; N=1 per width; calibration/
  t1_band null; the machine ran out before the witness did; PJ1 tiles these organisms into the arena).

### Block A — "What is happening" · PJ1 (second block)

**Always-visible copy** (plain-language what-is-happening + why-organisms):
- The run: IBM `ibm_kingston` (156-qubit Heron r2), **42 qubits** = 2×(W12 germ + 8 body + 1 trait), 12
  measured frames, 8,192 shots/frame, QRNG-certified (fail-closed), chain-quality gate passed
  (`twoq_err_max 0.0073`, `readout_max 0.026`), selective DD on both germ lines, ~1 min QPU.
- Why organisms: each is a **germ/soma individual** — a clean 12-qubit quantum genealogy (germ line, carrying
  certified entanglement inheritance) plus a moving body (soma) on the track. Two of them.
- How they collided: bodies start at opposite ends of an 8-site track, walk toward each other; measured
  **occupancy overlap climbs monotonically 0.00 → 0.72** (Z-basis, off the chip) — a real collision, not an
  `if(contact)` branch; one physical coupling is always on and only acts where both bodies have amplitude.
- What held: joint witness ⟨X⊗2W⟩ (24 germ qubits) alive across all 12 frames, **+0.16…+0.50, mean +0.35**,
  far above the separable null (≈0; cross-lineage cut −0.003). Weismann barrier on a QPU: bodies collide,
  gene lines do not.

**Accordion "Frame-by-frame (measured, 8192 shots/frame)"** — 12 rows verbatim:

| frame | body A pos | body B pos | overlap | witness ⟨X⊗2W⟩ |
|--:|--:|--:|--:|--:|
| 0 | 0.1 | 7.0 | 0.004 | +0.169 |
| 1 | 1.5 | 7.8 | 0.120 | +0.427 |
| 2 | 2.9 | 7.1 | 0.200 | +0.253 |
| 3 | 3.3 | 6.9 | 0.258 | +0.293 |
| 4 | 5.1 | 6.7 | 0.262 | +0.503 |
| 5 | 4.2 | 6.6 | 0.233 | +0.462 |
| 6 | 4.5 | 5.8 | 0.236 | +0.163 |
| 7 | 5.7 | 6.5 | 0.317 | +0.311 |
| 8 | 5.9 | 5.9 | 0.362 | +0.402 |
| 9 | 6.3 | 8.1 | 0.575 | +0.480 |
| 10 | 6.9 | 6.5 | 0.480 | +0.212 |
| 11 | 8.1 | 8.9 | **0.721** | +0.500 |

**Accordion "Honest scope — what this does not claim":** (1) the witness does **not respond** to contact — by
construction `soma_soma` never touches a germ qubit, so the genealogy is insulated (that is the point);
frame-to-frame wiggle is transpilation/readout noise. (2) Body-body entanglement on contact is **sim-only**
(42-qubit register too large for a statevector); hardware proves the meeting + genealogy survival, not the
entangling.

Optional figure: `pj1_witness.png` (already in `web/`).

### Block C — "How this was built" · the beginning (third block)

**Always-visible copy:**
- Origin: the program began at **[tree.peterjas.sk](https://tree.peterjas.sk/)** — a genome of **102 qubits**
  on Heron r2 whose long-range genes are linked by **quantum teleportation**, not code; a correlation no
  classical surrogate can fake, proven at ~10σ past its baselines. It set the method every study here
  inherits.
- The method (inherited discipline): **one certified witness** (⟨X⊗W⟩, no classical surrogate, k=2σ headline /
  k=3σ reported; diagonal metrics carry no quantum claim); **sim-first, hardware-confirm** (certified QRNG
  fail-closed, chain-quality gate aborts if 2-qubit err > 0.05 or readout > 0.15, selective DD on the gene
  line only); **no speedup claimed** (scale · faithfulness · certification; negatives reported as readings).

**Accordion "Reproduce"** — the run recipe (trimmed `.steps` block): `--selftest`; the arena run; the render;
the prior P2/PJ0 runs. Commands only, no external page links.

### Footer

Measured-on line (ibm_kingston · 156-qubit Heron r2) + the PJ1/PJ0/P2 headline numbers + the single external
link **`tree.peterjas.sk`**.

---

## 6. File plan

- **`artificial-life/web/index.html`** — the entire refactor (only file edited). Strict single-file, inline
  CSS/JS.
  - `:root` — keep palette; add accordion/HUD tokens as needed.
  - Hero — replace the boxed `.stage`/`.instrument`(iframe)/`.readout` layout with CQL full-bleed
    `.stage`+`<canvas id="life">`+`.veil`+`.grain`+`.hud-tl`/`.hud-tr`/`.hud-bottom`/`.cue` (§4). Remove the
    iframe.
  - Hero JS — inline the wave-bars renderer ported from `spectacle.html` (`DATA`, `frameAt`, `smooth`,
    `stats`, `rr`, `draw`) adapted to a responsive DPR-fit `#life` canvas (CQL `wrap()`); keep the `#heart`
    EKG + gate/clock readouts; one slowed ping-pong clock feeding all three (AC-3/AC-4). Keep reduced-motion
    static frame.
  - Content — Block B → Block A → Block C (§5); add `.acc` accordion CSS + markup; build the combined width
    table (New column highlighted); inline the four ASCII circuits, the original-P2 circuit dump, the 2×2
    table, and all folded P2/PJ0 rigor; remove every `pj*_conclusion.html`/other-page link (AC-14); footer
    keeps only `tree.peterjas.sk`.
- **No other files edited.** `spectacle.html` and the three `*_conclusion.html` files stay on disk, untouched
  and unreferenced. The banked dump `research_runs/originalP2/3.1-draw-only_circuit_w2_s1.txt` is read once
  and its content pasted verbatim into the page (not linked).

---

## 7. Open questions

All prior questions resolved by the developer:
- Order → **win first** (Hero → B → A → C).
- Hero → **inline canvas**, CQL `#life` style (no iframe).
- Slow-down → **≈2×**, global.
- Combined table → **yes**, one 3-column table, new line highlighted.
- Circuits → **four ASCII circuits from `pj0_conclusion.html`** + **original P2 damping circuit** from
  `research_runs/originalP2/3.1-draw-only_circuit_w2_s1.txt` shown in detail.
- Section nav → **none**.
- Deep-dive links → **none except `tree.peterjas.sk`**; everything inlined in expandable bars.

Remaining minor decisions (proposals — implement unless told otherwise):
1. **Which accordion starts open.** Proposal: **all collapsed** on load for the cleanest spectacle-first view
   (AC-13), except optionally the Block A frame table. Confirm or pick.
2. **`pj1_witness.png` in the hero vs Block A.** Proposal: Block A figure only (hero is the live canvas).
3. **Ping-pong vs linear loop** for the hero clock. Proposal: ping-pong (0↔11) to avoid the reset jump.

---

## 8. Manual verification

- Open `artificial-life/web/index.html` (`file://` or static server).
- **Hero:** wave-bars render in an inline canvas (no iframe) filling the viewport edge-to-edge, no border/box;
  eyebrow/gates/heartbeat float over it (glass HUD); witness/overlap/frame readouts advance live and visibly
  **slower** than before; veil + grain present; `scroll ↓` cue shows. Resize <820px: HUD reflows, no
  horizontal scroll. Check console — no errors.
- **Order:** Block B (the win) is the first section after the hero, then Block A, then Block C.
- **Block B:** combined table shows all three designs on one W axis, germ/soma column dominant, last-certified
  **+0.058 @ W=50** and abort at W=54; the four ASCII circuits render verbatim with the winner marked; the
  original-P2 circuit dump appears verbatim in a scrollable `<pre>`; the 2×2 kill-switch table has all four
  cells; the P2 unitary/damping-width/damping-depth tables + confound/gate prose are reachable in accordions;
  null-≈0 note present.
- **Block A:** "what is happening" reads clearly (collision + why-organisms); 12-frame table opens with exact
  numbers ending at overlap **0.721**; honest-scope caveats present.
- **Block C:** origin + method present; `tree.peterjas.sk` link works; reproduce recipe folded.
- **Spectacle-first / rigorous-second:** default view is a clean spectacle; expanding the bars reveals all the
  rigor; markers toggle `+`/`–` with no JS.
- **No external pages:** search the file — the only off-page hyperlink is `tree.peterjas.sk`; no
  `*_conclusion.html` link remains.
- **Honesty:** "scale · faithfulness · certification — not a speedup", witness-is-only-claim, null ≈ 0,
  body-body entanglement sim-only all appear.
- **Reduced motion:** with `prefers-reduced-motion`, the hero paints a correct static mid-collision frame (no
  runaway loop).
