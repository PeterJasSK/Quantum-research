# Feature Plan — M4 Web Demo: "Quantum Artificial Life" (living genealogy)

**Status:** Complete
**Study:** Month-4 full Alvarez-Rodriguez 2018 model at scale (`artificial-life/research/CONCLUSION_MONTH4.md`)
**Artifact:** `artificial-life/web/index.html` (new — a single self-contained page)
**Design source (visual sibling, NOT to copy):** `QuantumLife/web/index.html`
**Author:** Claude (Opus) · **Date:** 2026-08-25

> No GitHub issue — this study uses stage/phase IDs, not tickets (project convention; see
> `feature-S3-teleport.md` header). This plan is Month-4 **Phase 3** (RUNLOG_MONTH4 §"PHASE 3").
> No tests (project directive): production markup/JS + manual verification only.

---

## 1. Context & goal

Month 4 rebuilt the **whole** 2018 quantum-artificial-life model (self-replication, mutation, interaction,
death — all four Darwinian operators, verified operator-by-operator against the paper) and scaled it on a
real 156-qubit Heron-r2 (`ibm_kingston`). The honest headline is a single measured number: the
**genealogical entanglement depth W = 24 (48 qubits)** — the deepest genealogy whose entanglement witness
`⟨X^{⊗W}⟩` still beats its classical null, **~6× past the 2018 paper's ~4-qubit / 1-generation origin**,
on the one observable with no classical surrogate.

This demo is the **public face of that result.** It must:
1. Lead with the **6× headline** — "we recreated 2018 quantum artificial life on today's hardware and
   pushed it 6× deeper" — as the first thing a visitor sees.
2. Make the science **legible**: what the witness is, why it has no classical surrogate, and the measured
   witness-vs-width decay curve that lands at W=24.
3. Show, **intuitively**, what quantum artificial life *is* — a living population line that is born
   (self-replication), varies (mutation), interacts (phenotype exchange), and dies (aging to the dark
   state), with the genealogical entanglement thread visibly linking the line.
4. Stay **honest**: the ⟨σz⟩ population metrics are classical; the witness is the quantum claim; and
   teleport-routing was refuted (twice). State all three plainly — the honesty invariant is the study's
   spine, not a footnote.

**Visual relationship to `QuantumLife/web/index.html`:** same *family* (dark, glowing, immersive,
single-file, CDN-free, prose-below-a-canvas), **distinct execution.** QuantumLife grows one pixel-art
*tree/organism*; this demo animates a **horizontal population line of individuals cycling through the
Darwinian life-cycle**, with a **more scientific** framing (a real measured decay chart is a first-class
element, which QuantumLife has none of). Not a re-skin — a sibling with its own metaphor and its own
data-forward, chart-carrying layout.

### What exists (integration points)

- **Design source — `QuantumLife/web/index.html`** (surveyed): single self-contained HTML, ~93 KB. All CSS
  in one inline `<style>`, all JS in one inline `<script>`. **Zero external CDN** scripts/links (only an
  OG/canonical self-URL). No chart library — the visual is a `<canvas>`/WebGL generative organism. Data is
  **hardcoded as JS objects** inline (no `fetch`, no JSON file). Dark theme: near-black purple/green bg
  (`#0a0612`, `#05030a`), bio-quantum green + gold accents (`#6dffb0`, `#eafff2`, `#ffd66d`), system/mono
  font. This demo mirrors the *constraints* (single file, no CDN, inline data, dark organic theme) and
  diverges on *layout and metaphor*.
- **Measured data — `artificial-life/research_runs/qalife_m4*.json`** (surveyed). Uniform schema:
  `meta{ model, backend, steps, interaction, routing, death, mut_scale, alive_thresh, shots, repeats, k,
  widths[], sim, genealogical_entanglement_depth_W }` + `by_width{ "<W>": { witness_joint_mean,
  witness_joint_sigma, separable_mean, entanglement_signal, survives, alive_mean, deepest_mean } }`.
  Relevant files:
  - live hardware headline sweep: `qalife_m4p2_nn_unitary_ibm_kingston_20260825-090*.json` (W=3..32);
  - live population arm: `qalife_m4p3_pop_nn_damping_ibm_kingston_*.json`;
  - live teleport re-test: `qalife_m4p4_swap_longrange_unitary_ibm_kingston_*.json` (+`..._teleport_...`);
  - clean sim reference curve: `qalife_m4_nn_unitary_density_matrix_sim_sim.json` (smooth W=2..6 rungs).
- **Prose source of truth — `artificial-life/research/CONCLUSION_MONTH4.md`**: the two verbatim result
  tables (width sweep; teleport swap-vs-teleport), the operator table, and the final verdict. The demo's
  numbers and claims are transcribed from here — no new science, no re-derivation.
- **No `artificial-life/web/` directory yet** — this plan creates it. Sibling projects (`DNSPoisonRace`,
  `TargetedDosColisionsAndRNGAngle`, `qrng-eaas`) use Next.js builds; QuantumLife uses a single hand-written
  `index.html`. **This demo follows QuantumLife** (single file) — the user named it as the model.

---

## 2. Acceptance criteria

No GitHub issue; ACs are synthesized from the user's directive (2026-08-25) and the Month-4 result. Each
maps to a §8 manual check.

- **AC-1 (headline).** The **6× improvement** is the page headline — visible above the fold, first thing
  read: current-hardware recreation of the 2018 model pushed to **entanglement depth W=24 (48 qubits),
  ~6× the paper's ~4-qubit origin**. The two anchor numbers (W=24 / 48 qubits, and "6×") are present and
  correct per `CONCLUSION_MONTH4.md`.
- **AC-2 (scientific witness chart).** A **witness-vs-width decay chart** plots the measured
  `⟨X^{⊗W}⟩ ± 2σ` for the live hardware sweep (W = 3, 4, 6, 12, 24, 32) with the classical-null line at ~0
  and the `W=24` survival point marked. Values match the CONCLUSION table exactly (+0.879, +0.808, +0.612,
  +0.301, +0.038, +0.008). The chart makes clear W=24 is the last rung above the null and W=32 is buried.
- **AC-3 (intuitive Darwinian life).** An animated **24-step genealogy build** (Q1 = Concept B hero +
  Concept C backbone): the lineage assembles **exactly 24 individuals** (= headline depth W=24), one per
  step, cycling the four operators — **self-replication** (child inherits the parent genotype), **mutation**
  (a QRNG-driven angle nudge), **interaction** (phenotype exchange), **death/aging** (drift to the `|0⟩`
  dark state) — then **holds at 24, resets, and rebuilds** in a loop. The build is **cumulative** (once lit,
  a generation stays lit). **One individual per generation**, drawn as a node on a left→right lineage and
  **numbered 1 → 24** so the generational structure is explicit: the **founder** (gen 1) alone and coherent,
  replicating into gen 2, 3, … 24. The violet **inheritance thread linking parent→child dims each
  generation** — its brightness = the measured witness `witW(W)` (founder's bond strongest ≈1, **gen 24 a
  0.038 ember**), so each further generation visibly inherits a weaker entanglement share. Each individual is
  **alive (green, witness-bright)** or, where the measured alive-count marks it dead, a **red ✕ at the `|0⟩`
  dark state**; dead count = `N − alive` (W=24 → 23 green + 1 red). The **gen-24 node is the gold anchor**
  (hero run, Q2). A **live HUD shows multiple readouts** as it builds:
  **generation `N/24`**, witness at the current depth (measured vs interpolated), **alive-count**,
  **deepest-lineage**, and an **entanglement-vitality meter** (witness normalized, green→gold→red).
- **AC-4 (legible method).** Prose sections explain, in plain language: (a) what an "individual" is
  (2 qubits — genotype + phenotype); (b) the four operators, mapped to the exact gates
  (self-replication=CNOT, mutation=Ry(θ) from certified QRNG, death=amplitude damping to `|0⟩`,
  interaction=phenotype SWAP); (c) why the witness has **no classical surrogate** while the ⟨σz⟩
  alive-count does.
- **AC-5 (honesty).** The page states plainly, not hidden: (i) the population/alive-count metrics are
  **classical** (a death-matched surrogate reproduces them) — the quantum claim lives only in the witness;
  (ii) this is a **scale/faithfulness milestone, not a quantum-speed advantage**; (iii) a **prose-only**
  mention (Q3 — **NO data table, NO chart** for teleport) that teleport-routing was *tried and tied but
  failed here*, with a one-paragraph explanation of **why the same teleported gate won for QuantumLife but
  lost here** — the honest "bottleneck moved" contrast grounded in `QuantumLife/web/index.html` (SWAP depth
  ~31 decohered vs constant ~9-gate teleport there; 3 teleported CNOTs/bond + readout/mid-circuit-dominated
  Heron-r2 + a fragile many-body witness here). No teleport numbers plotted.
- **AC-6 (self-contained, no CDN).** Single file `artificial-life/web/index.html`, all CSS/JS inline,
  **no external CDN** scripts/links/fonts (matching QuantumLife's constraint), all measured numbers
  hardcoded inline as JS objects transcribed from the run JSONs. Opens correctly from `file://` and as a
  static host, no network needed. Dark theme, responsive down to a phone width.
- **AC-7 (provenance).** Every headline number is traceable: the page names the backend (`ibm_kingston`,
  156-qubit Heron-r2), shot count (8192), repeats (3), and cites the measured run so a reader knows these
  are real hardware measurements, not a simulation or a mock.

---

## 3. Scope

### In scope
- One new file `artificial-life/web/index.html` (single, self-contained, CDN-free).
- The **hero + 6× headline** (AC-1), the **witness-vs-W decay chart** (AC-2, hand-rolled inline SVG — no
  chart CDN), the **animated Darwinian population-line canvas** (AC-3), the **method/honesty prose**
  (AC-4/AC-5), and the **provenance strip** (AC-7).
- A small inline **JS data block** (`const DATA = {...}`) transcribing the real measured numbers from the
  run JSONs / CONCLUSION table: the hardware width sweep (**hero = W=24**, Q2), the faint sim reference
  curve, and the meta (backend, shots, repeats, alive/deepest at W=24). **No teleport numbers** (Q3).
- **Copy the most-important run JSON files into `artificial-life/web/data/`** (Q4) as committed provenance
  artifacts sitting beside the page — the hardware width-sweep runs + the sim reference run. The page does
  **not** `fetch` them (numbers are inlined); they ship alongside so every value is verifiable against a
  real file. Teleport run files are **not** copied (Q3 — not shown).
- Supporting assets in `artificial-life/web/`: `og.png` (social card) — `robots.txt`/`sitemap.xml` deferred
  (Q6); canonical/OG domain = **`life.peterjas.sk`**.

### Out of scope (deferred / not this plan)
- **The IEEE preprint / write-up** — RUNLOG_MONTH4 Phase 3's other half; separate artifact.
- **Live data loading / a backend.** No `fetch`, no API, no Next.js build. Numbers are inlined (Q4). If a
  later iteration wants live run-JSON loading, that is a follow-up, not this plan.
- **Re-running any hardware/sim.** The demo visualizes *already-measured* numbers; it launches no jobs and
  imports no Python. If a number is missing it is transcribed from `CONCLUSION_MONTH4.md`, not re-measured.
- **New science / re-derivation.** The witness definition, operators, and results are frozen in
  `stage4_qalife.py` + `CONCLUSION_MONTH4.md`; the demo only presents them.
- **A build toolchain, npm, framework, or bundler.** Single hand-written HTML by directive.
- **Interactive circuit builder / qubit-level simulator in-browser** — the population-line animation is
  an *illustrative* metaphor driven by the measured decay curve, not a live quantum simulator.

---

## 4. Data model — the inline `DATA` block

A single `const DATA = {…}` object near the top of the inline `<script>`, transcribed verbatim from the
run JSONs and `CONCLUSION_MONTH4.md`. Shape (mirrors the run-JSON field names so provenance is 1:1):

```js
const DATA = {
  meta: {
    backend: "ibm_kingston", qubits_total: 156, family: "Heron-r2",
    shots: 8192, repeats: 3, steps: 3, mut_scale: 0.08, k: 2,
    death: "unitary", interaction: "nn",
    entanglement_depth_W: 24, entanglement_depth_qubits: 48,
    paper_origin_W: 4, improvement_x: 6,          // ~6× (24/4)
    paper: "Alvarez-Rodriguez, Sanz, Lamata, Solano, Sci. Rep. 8:14793 (2018)",
  },
  // AC-2 headline chart — live hardware width sweep (values verbatim from CONCLUSION_MONTH4.md table)
  hardware_sweep: [
    { W: 3,  qubits: 6,  witness: 0.879, sigma: 0.027, twosigma: 0.054, alive: 2,  deepest: 1,  survives: true  },
    { W: 4,  qubits: 8,  witness: 0.808, sigma: 0.021, twosigma: 0.042, alive: 3,  deepest: 2,  survives: true  },
    { W: 6,  qubits: 12, witness: 0.612, sigma: 0.014, twosigma: 0.028, alive: 5,  deepest: 4,  survives: true  },
    { W: 12, qubits: 24, witness: 0.301, sigma: 0.017, twosigma: 0.034, alive: 11, deepest: 10, survives: true  },
    { W: 24, qubits: 48, witness: 0.038, sigma: 0.016, twosigma: 0.032, alive: 23, deepest: 22, survives: true  }, // marginal
    { W: 32, qubits: 64, witness: 0.008, sigma: 0.013, twosigma: 0.026, alive: 32, deepest: 31, survives: false }, // dead
  ],
  // context reference curve — clean noiseless sim (smooth rungs), plotted faint behind hardware
  sim_reference: [ /* from qalife_m4_nn_unitary_density_matrix_sim_sim.json: W 2..6, witness 0.974→0.930 */ ],
  // AC-3 colony driver — witness at EVERY integer depth W=1..24 for the 24-step build. The 5 measured
  // hardware widths (3,4,6,12,24) are exact; the rest are linearly interpolated between them (mark which
  // is which in the UI). Implementation computes these from `witW(W)` over the measured anchors rather than
  // hardcoding all 24, but the anchors + the measured/interp flag live in DATA:
  witness_anchors: [ [1,0.970],[2,0.930],[3,0.879],[4,0.808],[6,0.612],[12,0.301],[24,0.038],[32,0.008] ],
  measured_widths: [3,4,6,12,24,32],   // the rest of W=1..24 are interpolated, tagged "interp" in the HUD
  steps: 24,                            // exactly 24 individuals == headline depth W=24 (48 qubits)
  // AC-3 live HUD — the multiple "how alive is it" readouts, from the measured population arm (CONCLUSION):
  alive_anchors:   [ [3,2],[4,3],[6,5],[12,11],[24,23],[32,32] ],  // phenotypes still alive at each width
  deepest_anchors: [ [3,1],[4,2],[6,4],[12,10],[24,22],[32,31] ],  // deepest surviving lineage at each width
  // AC-4 method copy — mutation is a real operator (one Ry(θ) per generation, θ from the certified QRNG);
  // it is the physical reason the inheritance-thread witness decays with depth. Shown per node as the
  // genotype pip / small birth jitter (not a separate bond nick — that variant was rejected).
  mutation_note: "Each generation applies one Ry(θ) mutation (θ from the certified QRNG); accumulated " +
    "mutation is why the genealogical entanglement witness decays with depth.",
  // AC-5(iii) honesty — teleport is PROSE ONLY (no numbers plotted, Q3). Contrast copy grounded in the
  // QuantumLife/web/index.html source of truth (teleport WON there) vs this study (teleport lost).
  teleport_note: "The same teleported long-range gate that carried our earlier Quantum Tree study did not " +
    "help here — and the reason is instructive. In Quantum Tree, one long-range bond joined two genes ~12 " +
    "qubits apart; the SWAP ladder needed to route it was depth ~31 and simply ran past the chip's " +
    "coherence, washing the correlation out (even flipping its sign), so a constant ~9-gate teleported CNOT " +
    "won cleanly. Here the interaction is a full phenotype SWAP realised as three teleported CNOTs per bond, " +
    "each with its own reset corridor, mid-circuit measurements and feed-forward. On this newer Heron-r2 " +
    "chip readout and mid-circuit error now dominate two-qubit-gate error, so that teleport machinery costs " +
    "more coherence than the short SWAP ladder it replaces — and the many-body entanglement witness is far " +
    "more fragile than Quantum Tree's two-point correlation. Teleport tied, then lost. Same tool, opposite " +
    "verdict, because the bottleneck moved.",
  operators: [ /* {name, gate, meaning} × 6 rows from CONCLUSION §1 operator table for the method section */ ],
};
```

Rule: **no number in the markup or animation is invented** — each is either in `DATA` (traceable to a run
JSON / CONCLUSION table) or derived from `DATA` in code. The animation *reads* `hardware_sweep` to set the
entanglement-thread brightness per width, so the "life" visual is literally driven by the measured decay.

---

## 5. Design decisions (adopt; do not re-litigate at implementation)

- **DD-1 Single self-contained file, no CDN.** One `index.html`; all CSS in one `<style>`, all JS in one
  `<script>`; no external scripts, stylesheets, or web-fonts. Charts are hand-rolled inline SVG; the
  population line is a `<canvas>` 2D animation. (Mirrors QuantumLife's hard constraint — AC-6.)
- **DD-2 Distinct metaphor (Q1 RESOLVED → Concept B hero + Concept C backbone).** Central visual is a
  **24-generation lineage build** (Concept B): **one individual per generation**, numbered 1 → 24 on a
  left→right line — founder alone and coherent, replicating gen by gen to gen 24 (W=24). The **inheritance
  thread linking parent→child dims each generation** (witness ≈1 → 0.038 ember): the founder's bond is
  strongest, each further generation a weaker share. Alive green / dead red-✕ (`|0⟩` state), counts matching
  the data. Cumulative (generations persist), then holds at 24 and resets. A **live HUD** reads out multiple
  points (generation `N/24`, witness, alive-count, deepest lineage, vitality meter). Beneath/beside it, the
  **GHZ entanglement backbone** (Concept C): founder `|+⟩` braided across generations, fraying dark past
  W≈24. B = the *life*, C = the *thread that makes it quantum*. NOT QuantumLife's vertical growing tree.
  Prototype published (session artifact, "B-generational-line") is the build reference; step timing / hold
  length are tuning knobs.
- **DD-3 Data-forward / scientific.** Unlike QuantumLife (no charts), a **real measured decay chart** is a
  first-class, above-mid-page element. The science (witness, null, 2σ, W=24 survival) is shown, not just
  narrated (user directive: "more scientific focus").
- **DD-4 Hardcoded real numbers.** Data is inlined from the run JSONs (DD-1 forbids `fetch`); every value
  is transcribed, not mocked, and carries provenance (§4, AC-7).
- **DD-5 Honesty is on-page, first-class.** The classical-surrogate caveat, the "no speedup" statement, and
  the teleport refutation each get visible copy — not buried, not omitted (AC-5; the study's honesty
  invariant).
- **DD-6 Dark organic theme, own palette.** Same dark bio-quantum family as QuantumLife but the demo picks
  its own accent (proposed: witness-green `#6dffb0` for "alive/entangled", amber `#ffd66d` for headline,
  dim red/grey for "dead/classical") so it is visually distinct while cohesive.
- **DD-7 Responsive, accessible.** Fluid layout to phone width; chart and canvas scale; text has adequate
  contrast on the dark bg; the animation has a reduced-motion fallback (respect
  `prefers-reduced-motion` → freeze to a representative still frame).

---

## 6. File plan (concrete paths)

One new file + optional OG asset. No edits to any existing file.

### `artificial-life/web/index.html` (new)

Single document, sections in DOM order:

1. **`<head>`** — `<title>Quantum Artificial Life</title>`; full Open Graph set (type, url, site_name,
   title, description, image) mirroring QuantumLife's head; `<meta name="viewport">` for responsive;
   `prefers-color-scheme`/reduced-motion handled in CSS. Canonical/OG URL = **`https://life.peterjas.sk/`**
   (Q6). No external `<link>`/`<script>`.
2. **Inline `<style>`** — CSS variables for the DD-6 palette; dark bg; system/mono font stack (no web
   font); layout grid; the hero; the chart container; the canvas frame; prose typography; the provenance
   strip; media queries (phone) + `@media (prefers-reduced-motion: reduce)`.
3. **Hero (AC-1)** — `<h1>Quantum Artificial Life</h1>`, a one-line subtitle, and the **6× headline stat
   block**: big "W = 24 / 48 qubits" and "≈6× the 2018 origin", one sentence of context ("recreated the
   2018 model on a 156-qubit Heron-r2 and pushed its entanglement depth 6× deeper"). Immediately below:
   the live population-line canvas (§ item 4) so motion is above the fold.
4. **24-generation genealogy canvas — HERO (AC-3, Concept B, DD-2)** — `<canvas>` + inline 2D animation
   looping a **24-step cumulative build**, **one individual per generation** on a left→right lineage.
   Timing: `STEPS = 24`, `STEP_MS`/step, `HOLD_MS` at full, `FADE_MS` reset (`FILL = STEP_MS·24`,
   `LOOP = FILL+HOLD+FADE`; prototype ≈11 s — tunable). Nodes at `node(i)` on a **clean sinusoid**
   (`y = ymid + 0.34·H·sin(u·4π)`, u = i/23 — 2 clear periods across the 24 generations, one smooth wave, not
   a meander). Loop phase drives the fractional lit count `litF` (rising during fill, pinned
   at 24 during hold, global-alpha fade on reset); `N = floor(litF)`, `edge = litF−N` = the birthing leading
   individual (gold spark). **Cumulative** (an individual, once lit, persists until the whole-line reset —
   earlier generations never dim). **Generational read**: each node carries its **generation number** (1 →
   24; label every other one + gens 1–4 + 24 to avoid crowding), the **founder** labelled, the **gen-24 node
   gold-ringed + "W=24"**. The **inheritance thread** between consecutive nodes has width/brightness =
   `witW(i+1)` — **dimming each generation** (founder's bond ≈1 → **gen 24 a 0.038 ember**), so each further
   generation visibly inherits a weaker entanglement share. **Alive/dead per individual**: `aliveNow =
   min(N, round(interp(alive_anchors, N)))` are **alive (green, witness-bright)**, the trailing `N − aliveNow`
   (past the deepest surviving lineage) are **dead — red ✕ at the `|0⟩` dark state** (W=24 → 23 green +
   1 red). A **live HUD** reads out **multiple points**: **generation `N/24`**, `⟨X^{⊗W}⟩` at the current
   depth (tagged `measured`/`interp` via `DATA.measured_widths`), **alive-count** (`interp(alive_anchors,W)`),
   **deepest-lineage** (`interp(deepest_anchors,W)`), and an **entanglement-vitality bar** = `witW(W)/witW(1)`
   coloured green→gold→red. A loop bar tracks `litF/24`. Reduced-motion → a single frame at the full 24-line.
   **Matches the published prototype** (session artifact, "B-generational-line"); step timing / hold length
   are tuning knobs.
4a. **Causal-birth variant (Concept F — candidate hero, pending Q1 final pick)** — **identical to item 4**
   (same `node(i)` line, generation numbers, thread-dimming, alive/dead, HUD, 24→hold→reset) with the
   **self-replication causality** made explicit per birth: (1) a violet **`gene →` pip travels parent→child**
   over the first ~0.6 of the birth window (the CNOT genotype copy), (2) the child then blooms inheriting the
   gene and entangled, (3) **aging acts only after** — living cells **warm green→gold with age**
   (`age = (litF−i)/STEPS`), and the data-marked dead fall to the red `|0⟩` ✕. Message: gene copied forward
   **before** the body ages, so a death never breaks the line. On-canvas honesty rail (also in card copy):
   genotype copy onto a blank qubit (parent persists, no full clone), the split **entangles** parent+child
   (GHZ), and **depth ≠ population** (W=24 = 24 generations deep = 48 qubits). Prototype: session artifact
   "concept-F-causal-gene-split". **B chosen as hero (Q1); F retained only as an optional alternate**, not
   built by default.
4b. **GHZ backbone canvas — secondary (Concept C, DD-2)** — a **smooth** two-strand braided helix: the
   founder `|+⟩` spread across generations as one entangled strand. Strand + rung brightness (and a `fray`
   wobble past the midpoint) = `witU` (witness over W log-spaced 3..32), so the braid runs bright/tight early
   and **frays dark past W≈24** — the coherence wall made literal. ~20 rungs (generations). Same `LOOP`
   period as B so the two read as one system. Reduced-motion → still frame. **RESOLVED → smooth braid** (a
   24-discrete-segment variant was tried and rejected as worse; keep the smooth version). Prototype: session
   artifact "B-sine-C-smooth-braid".
5. **The measured result — witness decay chart (AC-2)** — a hand-rolled **inline SVG** line/point chart:
   x = width W (log-ish or categorical 3→32), y = witness `⟨X^{⊗W}⟩`; points with ±2σ error bars from
   `DATA.hardware_sweep`; a dashed **classical-null line at 0**; the faint `DATA.sim_reference` curve
   behind it for context; a marker/annotation at **W=24 "last rung above the null"** and W=32 "buried in
   noise". Caption states backend/shots/repeats (AC-7). Built with plain SVG elements generated in JS from
   `DATA` (no chart lib — DD-1).
6. **How it works — method (AC-4)** — `<h2>` prose: individual = 2 qubits (genotype g + phenotype p); the
   operator table (self-replication=CNOT, mutation=Ry(θ) from certified QRNG, death=amplitude damping to
   `|0⟩`, interaction=phenotype SWAP), rendered from `DATA.operators`; then the key idea — the population
   ⟨σz⟩ alive-count is **classical** (has an exact surrogate) while the joint X-parity **witness has no
   classical surrogate** (GHZ genealogy ⟨X^{⊗W}⟩=1 vs separable ∏⟨X⟩≈0). This is the "how it exists /
   how it lives the Darwinian way" explanation the user asked for.
7. **What we didn't get — honesty (AC-5)** — a visibly-styled honest panel: (i) classical population
   metrics; (ii) no quantum-speed advantage — a scale/faithfulness milestone; (iii) a **prose-only**
   paragraph (Q3 — **no table, no chart, no numbers**) noting teleport routing was tried, *tied but
   failed* here, and explaining **why it helped QuantumLife but not this study**. Source the "why" from
   `DATA.teleport_note` — grounded in the confirmed `QuantumLife/web/index.html` framing (there: one bond,
   SWAP depth ~31 ran past coherence, constant ~9-gate teleport won at ~10σ; here: interaction = 3
   teleported CNOTs/bond with reset corridors + mid-circuit + feed-forward, and on Heron-r2 readout/
   mid-circuit error now dominates 2q-gate error, so the teleport machinery costs more coherence than the
   short SWAP ladder, and the many-body witness is far more fragile than a two-point correlation).
8. **Provenance strip / footer (AC-7)** — backend `ibm_kingston` (156-qubit Heron-r2), 8192 shots ×3
   repeats, `nn`/unitary, `mut_scale 0.08`; a line crediting the 2018 paper; a pointer to the study
   (`artificial-life/research/CONCLUSION_MONTH4.md`) and that every number is a real measurement.

### `artificial-life/web/og.png` (optional, Q6)
Static social card. Default: generate/commit a simple dark card with the 6× headline; deferred if the
developer prefers to add it later. `robots.txt`/`sitemap.xml` deferred unless a domain is set (Q6).

No other files. No Python touched, no run JSON modified.

---

## 7. The one load-bearing detail — the animation is driven by the real curve

The demo's credibility rests on AC-3 + AC-2 being the **same number shown two ways**. The lineage canvas
(and the C backbone) must not animate an arbitrary "life"; the **inheritance-thread brightness at generation
W is a direct function of `witW(W)`** from `DATA.witness_anchors` (measured widths exact, others
interpolated). The lineage spans **gen 1..24**; the AC-2 chart carries the full sweep including W=32. So:
- founder → gen 6: thread thick/bright (witness 0.97→0.61) — inheritance visibly coherent;
- gen ~12: thread half-strength (0.30);
- gen ~24: thread a faint ember (0.038, marginal survival — the headline W): the **lineage is long but the
  entanglement is nearly gone**. Individuals may still be *drawn* alive by ⟨σz⟩ (classical life continues)
  while the thread that proves they are one quantum lineage has decayed — exactly the honest point
  (classical life continues; quantum coherence does not). The legend/annotation must connect "thread went
  faint by ~gen 24" to the chart's "last rung above the null at W=24"; both read from the same `DATA`.

Additionally, the build is **exactly 24 steps and deterministic**: `litF` is a pure function of loop time,
node positions from `node(i)` (index-derived, no per-frame randomness), and each thread segment's brightness
is `witW(i+1)` — so the fill is identical every cycle and the reset (fade → empty → rebuild from the
founder) is clean. The **HUD numbers must equal the data**: at gen 24 the witness reads **0.038** (measured),
alive ≈ **23**, deepest ≈ **22** — matching `CONCLUSION_MONTH4.md`. Reduced-motion still frame shows the
full 24-generation line with the same bright→ember thread so the message survives without animation.

---

## 8. Manual verification (no automated tests)

Open the file directly and in a static server; check against the ACs:

```bash
# open from file:// (AC-6: must work with no network)
xdg-open artificial-life/web/index.html
# and via a static server (closer to production)
python -m http.server -d artificial-life/web 8080   # then visit http://localhost:8080
```

- **§8-A — AC-1 headline.** Above the fold, first read: the 6× / W=24 / 48-qubit stat is present and the
  numbers match `CONCLUSION_MONTH4.md`. Resize to phone width — headline still legible.
- **§8-B — AC-2 chart.** The witness points are 0.879 / 0.808 / 0.612 / 0.301 / 0.038 / 0.008 at W =
  3/4/6/12/24/32 with 2σ bars 0.054/0.042/0.028/0.034/0.032/0.026; the null line sits at 0; W=24 is
  annotated as the last surviving rung, W=32 as dead. Cross-check each value against the CONCLUSION table.
- **§8-C — AC-3 24-generation build + multi-readout HUD.** Watch one full cycle: **one individual per
  generation, exactly 24 steps** (the `gen N/24` HUD must reach 24, no more/fewer; nodes carry generation
  numbers 1 → 24 and the founder is labelled). Confirm the **inheritance thread dims each generation**
  (founder bond thick → gen 24 a faint ember). Confirm **cumulative** (earlier generations don't dim).
  Confirm **alive/dead**: green + red-✕ sums to `N`, red count = `N − alive` (W=24 → 23 green + 1 red).
  Confirm the **HUD points match the data**: witness 0.97→**0.038** by gen 24 (measured/interp tag correct
  at 3/4/6/12/24), **alive ≈23/24**, **deepest ≈22**, vitality bar drains green→gold→red. At 24 it **holds
  then resets** and rebuilds from the founder (watch the loop bar). The gen-24 node is gold-ringed. The C
  backbone braid frays dark past W≈24.
- **§8-D — AC-4/AC-5 prose.** The four operators + exact gates are present; the "witness has no classical
  surrogate, alive-count does" explanation is present; the three honesty statements (classical metrics /
  no speedup / teleport tried-tied-failed as **prose only, no numbers/table** + the why-QuantumLife
  contrast) are visible without expanding anything. Confirm **no teleport figures** appear anywhere (Q3).
- **§8-E — AC-6 self-contained.** `grep -Ei 'src=|href=|@import|cdn|googleapis|unpkg|jsdelivr'
  artificial-life/web/index.html` returns only same-page anchors / the OG self-URL — **no external CDN
  script/style/font**. DevTools Network tab on load shows zero third-party requests. The page renders with
  the network disabled.
- **§8-F — AC-7 provenance.** Backend, shots, repeats, and "real hardware measurement" are stated;
  `ibm_kingston` / 156 / 8192 / 3 appear.
- **§8-G — reduced motion.** With `prefers-reduced-motion: reduce` (DevTools → Rendering → Emulate), the
  canvas freezes to a still frame that still shows the bright→dark entanglement gradient.
- **§8-H — responsive.** At 375 px width the chart, canvas, and prose reflow without horizontal scroll;
  at desktop the layout uses the space (no giant empty margins).

---

## 9. Out-of-context risks / notes

- **Distinct-not-clone is a judgement call.** DD-2/DD-3 make the metaphor (population line) and the
  data-forward chart the differentiators. If, on review, it still reads too much like QuantumLife's tree,
  the fix is layout/motion, not new data. Flag early if the silhouette feels derivative.
- **No CDN = hand-rolled chart.** The witness chart is inline SVG built in JS. It need not be a charting
  library's polish — it must be *correct* (right values, right error bars, null line, W=24 marker) and
  readable. Don't reach for Chart.js/d3 (breaks AC-6).
- **The animation must not overclaim.** It is an *illustration* of the operators driven by the measured
  witness — not a live in-browser quantum simulator. Copy near the canvas should say so, so no reader
  thinks the browser is simulating qubits.
- **Teleport contrast is now grounded in the source of truth (Q3/§7) — verified, keep it accurate.** The
  `QuantumLife/web/index.html` page **does** claim a teleport win: one long-range bond (~12-qubit gap),
  SWAP ladder depth ~31 decohered and even flipped the correlation sign, while a constant ~9-gate
  teleported CNOT gave a stable c(d)≈−0.065 at ~10σ (on `ibm_marrakesh`). So "teleport worked for
  QuantumLife" is TRUE and must be stated faithfully. The honest contrast for *this* study: teleport lost
  here because (a) the interaction is a full phenotype SWAP = **3 teleported CNOTs per bond** (not one), each
  with reset corridor + mid-circuit + feed-forward; (b) on the newer Heron-r2 **readout/mid-circuit error
  now dominates 2q-gate error**, inverting the depth tradeoff QuantumLife exploited; (c) the **many-body
  witness ⟨X^{⊗W}⟩ is far more fragile** than a two-point c(d). Do not overstate this study's teleport as
  "refuted physics" — it is "the bottleneck moved, so the same tool loses." `DATA.teleport_note` already
  encodes this; keep the copy within what the two sources support.
- **Number drift.** All values transcribed once into `DATA` from `CONCLUSION_MONTH4.md`. If the CONCLUSION
  table and a run JSON ever disagree, the CONCLUSION table wins (it is the reviewed source of truth); note
  any discrepancy rather than silently picking one.
- **Honesty panel is required, not optional (AC-5).** Omitting the teleport refutation or the "classical
  alive-count" caveat would misrepresent the study. It stays even though it is "negative" — that is the
  point of the study.
- **OG/canonical URL unknown (Q6).** QuantumLife deploys at `tree.peterjas.sk`. The demo's domain/subpath
  is a placeholder until the developer sets it; don't hardcode a wrong canonical.
- **`sim_reference` values.** §4 leaves the exact sim rung numbers to transcribe from
  `qalife_m4_nn_unitary_density_matrix_sim_sim.json` at implementation; the survey gives W 2..6, witness
  ~0.974→0.930. Read the file for the exact figures rather than approximating.

---

## 10. Ground rules honored

- Every AC (1–7) is synthesized from the user's directive + the Month-4 result and mapped to a §8 manual
  check.
- Every path in §6 is concrete; one new file (`artificial-life/web/index.html`) + one optional asset; no
  edits outside `artificial-life/web/`.
- Single self-contained, CDN-free file (DD-1, AC-6) — follows the named design source
  `QuantumLife/web/index.html`; distinct metaphor + data-forward layout (DD-2/DD-3).
- Honesty invariant on-page (DD-5, AC-5): classical alive-count, no speedup, teleport tried-tied-failed
  (prose only, no numbers — Q3).
- No tests, no test files (project directive). Verification is manual (§8).
- No new science; all numbers transcribed from `CONCLUSION_MONTH4.md` / run JSONs (DD-4).

---

## 11. Resolved decisions (developer, 2026-08-25)

- **Q1 — Central visualization: RESOLVED → Concept B (24-generation lineage build) HERO + Concept C (GHZ
  braid backbone) secondary.** B: **24 steps** to depth W=24, **one individual per generation** numbered
  1 → 24; the **inheritance thread dims each generation** (founder strongest → gen 24 ember); alive green /
  dead red-✕; cumulative, holds at 24, resets. **Multiple live readouts** (generation `N/24`, witness,
  alive-count, deepest, vitality). C: founder `|+⟩` braid fraying dark past W≈24. **Published prototype is
  the build reference** (session artifact, "B-sine-C-smooth-braid"). Not the QuantumLife tree (DD-2, §4 items
  4/4a/4b, §7). **Hero = B, RESOLVED 2026-08-25**; B's lineage rides a **clean sinusoid** (2 periods across
  24 gens). Concept **F** (§4a, causal gene-split) is **retained only as an optional alternate**, not the
  hero. Concept **C RESOLVED → the smooth braided helix** (fraying with the witness); a 24-discrete-segment
  variant was tried and rejected as worse (§4b). (Earlier "columns-of-relatives + mutation-nick" B variant
  also tried and rejected — keep the clean single-line read.)
- **Q2 — Hero run: RESOLVED → W=24.** The W=24 hardware result is THE headline/anchor (hero stat + the
  visually-anchored cell). Full hardware sweep still charted for the decay context; sim faint behind.
- **Q3 — Teleport: RESOLVED → do NOT show as data; prose contrast confirmed.** No teleport
  table/chart/numbers. **Prose-only** paragraph: teleport was tried, tied, then lost *here*, and — grounded
  in `QuantumLife/web/index.html` (the source of truth, which does claim a teleport win: SWAP depth ~31
  decohered vs constant ~9-gate teleport, c(d)≈−0.065 at ~10σ) — explains why the same tool wins there and
  loses here (bottleneck moved: 3 teleported CNOTs/bond + reset corridors, and on Heron-r2 readout/mid-
  circuit error now dominates 2q error; the many-body witness is more fragile than a 2-point c(d)). Copy in
  `DATA.teleport_note`.
- **Q4 — Data: RESOLVED → inline, no fetch; copy key run JSONs into `artificial-life/web/data/`.** Only the
  most-important runs (hardware width sweep + sim reference) copied beside the page as provenance; the page
  reads inline hardcoded `DATA`, never fetches. Teleport files not copied.
- **Q5 — Charts: RESOLVED → hand-rolled inline SVG.** No chart library, no CDN.
- **Q6 — Domain: RESOLVED → `life.peterjas.sk`.** Canonical/OG URL `https://life.peterjas.sk/`; committed
  `og.png`; `robots.txt`/`sitemap.xml` deferred.
- **Q7 — Title: RESOLVED → "Quantum Artificial Life"** (`<h1>` + `<title>`).

---

## 12. After approval

Open questions resolved (§11). Once the plan is approved, run
`/implement-feature artificial-life/plans/feature-M4-web-demo.md`.
Gate before "done": the file opens from `file://` with **zero** external requests (AC-6/§8-E), every
witness number matches `CONCLUSION_MONTH4.md` (AC-2/§8-B), the population-line animation's entanglement
thread is driven by the measured decay and its dim-out aligns with the chart's W=24 survival (§7), and the
honesty panel (classical metrics / no speedup / teleport refuted) is on-page (AC-5/§8-D).

---

## 13. Post-implementation (2026-08-25)

**Built:** one self-contained `artificial-life/web/index.html` (single inline `<style>` + single inline
`<script>`, no CDN). Sections in DOM order: hero + 6× headline, the living-genealogy hero canvas + HUD,
the entanglement-backbone braid canvas, the witness-decay SVG chart, the method/operator prose, the
honesty ledger, and the provenance strip.

**Developer directive honored (2026-08-25):** implemented the 24-generation lineage build (§4 item 4) as
the hero and the smooth GHZ braid (§4 item 4b) as the secondary — **referred to by descriptive names
on-page** ("living genealogy" / "the entanglement backbone"), no "Concept B/C" labels anywhere. The
causal-birth variant (§4a item 4a) was **not** built.

**AC coverage (file:line evidence, `artificial-life/web/index.html`):**
- **AC-1** headline W=24 / 48 / ≈6× — hero stat block `index.html:139-141`, context `:150`.
- **AC-2** witness-vs-W SVG chart with 2σ bars, null line, sim reference, W=24/W=32 markers — `drawChart()`
  `:407-470`; values in `DATA.hardware_sweep` `:302-309`.
- **AC-3** 24-gen cumulative build, one/gen, dimming inheritance thread = `witW`, alive-green / dead-red-✕,
  gold gen-24 anchor, multi-readout HUD (gen, witness+measured/interp tag, alive/deepest, vitality) —
  `lineage()` `:473-576`, HUD markup `:161-170`.
- **AC-4** individual=2 qubits, operator table (self-repl=CNOT, mutation=Ry(θ) QRNG, death=damping,
  interaction=SWAP), witness-has-no-classical-surrogate box — `DATA.operators` `:330-337`, `#opTable`
  render `:369-371`, key-idea `:196-206`.
- **AC-5** classical-metrics caveat + no-speedup + **prose-only** teleport (no numbers/table), why-it-won-
  for-QuantumLife contrast — honesty panel `:209-241`, `DATA.teleport_note` `:319-328`.
- **AC-6** single file, no CDN (only external ref is the canonical self-URL) — verified via grep §8-E;
  hi-dpi canvases + inline SVG, no chart lib.
- **AC-7** provenance chips (backend/qubits/shots/repeats/steps/mut_scale/err gates) + real-measurement
  copy — `#provChips` render `:377-382`, footer `:255-258`.

**Provenance artifacts copied (Q4):** `artificial-life/web/data/` now holds the three hardware width-sweep
runs (`qalife_m4p2_nn_unitary_ibm_kingston_*.json`), the population arm
(`qalife_m4p3_pop_nn_damping_ibm_kingston_*.json`), and the sim reference
(`qalife_m4_nn_unitary_density_matrix_sim_sim.json`). Teleport runs **not** copied (Q3).

**Verification:** inline JS `node --check` clean; headless-chrome render (`file://`) produced no runtime
JS errors and drew the hero, HUD, braid, and chart correctly. Witness values, 2σ bars, and provenance
match `CONCLUSION_MONTH4.md` exactly. Sim reference transcribed from the density-matrix-sim run
(W2..6 = 0.9736/0.9666/0.9592/0.9526/0.9300). Reduced-motion path freezes to a full-24 still frame.

**Follow-ups for the developer:**
- `og.png` (Q6) **not** generated — OG/canonical meta point at `https://life.peterjas.sk/og.png` but the
  image is deferred (no image tooling used; add a static dark card before deploy or the social preview 404s).
- `robots.txt` / `sitemap.xml` deferred (Q6), as planned.
- Live-browser eyeball of the full 24-step cycle recommended (headless virtual-clock only ticked the early
  frames; the build/hold/reset logic is deterministic and verified by code, but confirm timing feel).
