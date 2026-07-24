# Plan 6 — Web demonstration: three scenes (Next.js `/web` app, Tier A + Tier B)

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 5** · **Priority:** `[SHOULD]` (Tier B `[COULD]`)
**Status:** Draft · **Depends on:** P2 (shared vectors) · Tier B also P4 (CSV/counters), P5 (replay data)

> Pick up with `/plan-feature plans/plan-6-web-demo.md`. Read epic §3.3 (visualization is first-class) and
> §3.2 (QRNG provenance display) first. **This is the epic's primary visualization deliverable.**
> **No automated tests** (project directive). Parity-vs-drift is a **build-time assert** (§Parity), not a test suite.

## Goal
Make the five-experiment argument **visible to someone who has not read the paper**, in three scenes shown in
sequence. The demo is not supplementary material — it *is* the paper's argument made visual, and it doubles as a
reproducibility artefact (anyone verifies the mechanism in a browser without the Mininet stack).

## Deliverable — a Next.js app in `web/`
The demo is built as a **Next.js (App Router, TypeScript) application at `TargetedDosColisionsAndRNGAngle/web/`**,
integrating all upstream parts for a live demo:
- **P2** — the JS/TS mirror of `hash_core` + the shared test vectors (the demo's logic must equal the testbed's).
- **P4** — real OVS port-stat counters over WebSocket (Tier B live).
- **P5** — the recorded sweep subset for replay (Tier B replay) and the Q-EaaS provenance record.
- **Q-EaaS** — live `/v1/random/bytes` provenance for the QRNG panel (hosted `api.qeaas.eu`, epic §8 Q6).

## Decision D-web — Next.js + static export reconciles the "static HTML page" AC *(frozen here)*
The verbatim AC says "static HTML page." Next.js with `output: 'export'` produces a **fully static HTML/JS bundle**
with **no server runtime** — deployable to GitHub Pages and runnable offline, exactly satisfying the Tier A AC while
giving a real component framework for the three scenes and the Tier B live/replay modes. **Tier A = the static
export** (no Node server, no infra). **Tier B = the same static bundle** plus a client WebSocket/replay data source;
still no Next.js server — only a browser talking to the Ryu controller's thin WS layer. So "static HTML page" and
"Next.js app" are not in conflict: the export *is* the static page. This is recorded so no later reviewer reads the
Next.js choice as a violation of the AC.

## Two tiers
- **Tier A — browser-only `[SHOULD]`, ships first.** All salt/hash/bucket logic in TS, mirroring Python and sharing
  P2's test vectors. `next build && next export` → static bundle on GitHub Pages; usable as a conference QR code.
  Needs **only P2** (the vectors), no testbed infra.
- **Tier B — connected `[COULD]`, stretch.** Same front-end; link bars + victim numbers driven by **real OVS
  port-stat counters** over WebSocket from the Ryu controller. Sub-modes: **live** (WS to controller) + **replay**
  (recorded P5 sweep bundled as static JSON — no live infra needed for talks).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] **AC-1** Static HTML page, all salt/hash/bucket logic in JS (mirrors Python, shares EPIC 1 vectors). Topology view: attacker, switch, 4 links, victim.
- [ ] **AC-2** **Scene 1** naive flood → rate-limiter fires (red on attacker), links balanced, victim healthy.
- [ ] **AC-3** **Scene 2** precision mode → limiter/throttle stay green, one link climbs to red, victim collapses; predictable weak-PRNG salt shown on screen.
- [ ] **AC-4** **Scene 3** CSPRNG + rotation → links scatter, rotation event visibly disperses the crafted 5-tuples, victim stays healthy; **rotation-frequency slider** re-establishes/collapses saturation live (Experiment 5 interactive). QRNG selection shows entropy provenance without overstating.
- [ ] **AC-5** Same front-end; link bars + victim numbers driven by **real OVS port-stat counters** over WebSocket from the Ryu controller. Sub-modes: live + replay (recorded sweep, no live infra needed for talks).
- **Done when:** Tier A runs the three scenes offline on GitHub Pages; (stretch) Tier B shows real counters live or on replay.

> AC-1 realised via Next.js static export (D-web). "all salt/hash/bucket logic in JS" → `lib/hashCore.ts` +
> `lib/ecmp.ts` in TypeScript, mirroring Python and asserted against P2 vectors.

## The three scenes (what each makes visible)
- **Scene 1** (AC-2) = Experiment 1: standard defences stop a standard attacker. Rate-limiter goes red on the
  attacker; four link bars stay balanced; victim throughput bar healthy.
- **Scene 2** (AC-3) = Experiments 2–3: the gap. Rate-limiter and throttle indicators **stay green** (nothing looks
  wrong), yet one link bar climbs to red and the victim bar collapses. The predictable weak-PRNG salt is printed on
  screen so the viewer sees *why the attacker knew where to aim*.
- **Scene 3** (AC-4) = Experiments 4–5: rotation defeats it. Link bars scatter; a rotation event fires (salt visibly
  changes to a new opaque number) and the crafted 5-tuples disperse; victim stays healthy. A **rotation-frequency
  slider** lets the viewer slow rotation until saturation re-establishes, then speed it up until it collapses — the
  Exp 5 curve made interactive.

## QRNG provenance display (epic §3.2 — the user's "practical QRNG use")
When QRNG is selected, show the **real** Q-EaaS provenance from `/v1/random/bytes`: `entropy_epoch`, `timestamp`,
byte count, endpoint, and the Ed25519 `receipt`. Label honestly — **attestable entropy provenance**, not "stops the
attack better." In Tier A / replay, use the recorded provenance record (epic §4, from P5's QRNG run); in Tier B live
the panel may call hosted `api.qeaas.eu` directly. This is the visible payoff of the practical-QRNG angle without
overstating the null result.

## File plan
New Next.js app; nothing exists yet. TypeScript, App Router, function components. All paths relative to
`TargetedDosColisionsAndRNGAngle/`. No CSS framework mandated — plain CSS modules are fine; keep the bundle static.

| File | Purpose | Notes |
|------|---------|-------|
| `web/package.json` | Next + React deps, scripts: `dev`, `build`, `export`, `check:parity`. | Pin Next major. |
| `web/next.config.js` | `output: 'export'`; `basePath`/`assetPrefix` for GitHub Pages project path. | D-web — static export, no server. |
| `web/tsconfig.json` | Strict TS. | `strict: true`. |
| `web/app/layout.tsx` | Root layout, scene-agnostic chrome. | |
| `web/app/page.tsx` | Demo shell: scene stepper (1→2→3), data-source selector (sim/live/replay), salt-source selector. | Wires all components. |
| `web/components/TopologyView.tsx` | Attacker, switch, N=4 links, victim — the topology diagram. | AC-1. SVG. |
| `web/components/LinkBars.tsx` | N link-utilisation bars; red at saturation. | AC-2/3/4. Driven by data source. |
| `web/components/VictimThroughput.tsx` | Victim throughput bar (healthy/collapsed). | AC-2/3/4. |
| `web/components/DefenceIndicators.tsx` | Rate-limit + throttle status lamps (green/red). | AC-2 red, AC-3 stay-green. |
| `web/components/SaltPanel.tsx` | Shows active salt; weak-PRNG value visible in Scene 2; opaque rotating salt in Scene 3. | AC-3/4. |
| `web/components/RotationSlider.tsx` | Scene 3 rotation-frequency slider; drives re-establish/collapse of saturation. | AC-4 (Exp 5 interactive). |
| `web/components/ProvenancePanel.tsx` | QRNG `entropy_epoch`/`timestamp`/bytes/endpoint/`receipt`, honestly labelled. | §3.2. |
| `web/components/SceneController.tsx` | Advances scenes, applies each scene's salt-source + attack-mode preset. | |
| `web/lib/hashCore.ts` | **TS mirror of Python `hash_core`** — `ecmpLink(fiveTuple, salt, nLinks): number`. | AC-1. Must equal P2. |
| `web/lib/ecmp.ts` | Collision-set / bucket-spread demo logic (JS mirror of the sim). | AC-3/4. |
| `web/lib/vectors.ts` | P2's shared `(5tuple, salt) → link` test vectors. | Consumed by the parity check. |
| `web/lib/datasource.ts` | One interface, three impls: `sim` (Tier A, pure JS), `live` (WS), `replay` (JSON). | AC-5 — same front-end, swappable source. |
| `web/lib/ws.ts` | WebSocket client → Ryu controller port-stat stream (Tier B live). | AC-5. Server side = §Dependencies. |
| `web/lib/replay.ts` | Loads recorded sweep subset from `public/replay/`. | AC-5 replay. |
| `web/lib/qeaas.ts` | Fetch Q-EaaS `/v1/random/bytes` provenance (live) or read recorded record (replay). | §3.2, epic §8 Q6 hosted URL. |
| `web/public/replay/*.json` | Recorded P5 sweep **subset** (epic §8 Q4): 3-scene runs + QRNG provenance run + full rotation-interval sweep. Blind skipped. | From P5. |
| `web/scripts/check-parity.mjs` | Build-time assert: `hashCore.ts` output vs `vectors.ts` — **exits non-zero on drift**, wired into `build`. | Epic §3.3 "asserts fail on drift" — build tooling, not a test suite. |
| `web/README.md` | Run/build/export/deploy (GitHub Pages) + how to point Tier B at a live controller or replay. | |

## Parity — the hard constraint (epic §3.3)
The TS hash/salt/bucket functions **must be identical** to Python, guaranteed by P2's shared vectors. `hashCore.ts`
is checked against `vectors.ts` by `web/scripts/check-parity.mjs`, run as part of `npm run build` — **a drift fails
the build**. This is a build-time assertion, not an automated test (project directive), and it is what stops the demo
silently lying.

## Dependencies on other plans
- **P2 (hard):** `hashCore.ts`, `ecmp.ts`, and `vectors.ts` are P2's shared JS↔Python artefacts. Tier A cannot ship
  correct without them. Coordinate: P2 owns the vector format; P6 consumes it verbatim.
- **P4 + P5 (Tier B only):** live WS counters (P4) and the recorded replay subset + provenance record (P5). Tier A is
  independent of both and ships first.
- **Q-EaaS:** hosted `https://api.qeaas.eu` for the live provenance panel (epic §8 Q6, resolved).

## Manual verification (no automated tests)
1. **Parity (constraint):** `npm run check:parity` in `web/` → passes when TS matches P2 vectors; break a vector to
   confirm it fails (then restore). Also runs inside `npm run build`.
2. **Tier A offline (Done-when):** `npm run build && npm run export`, serve `web/out/` from a plain file server (or
   open the exported HTML), step Scene 1→2→3 with the network **disconnected** — all three scenes must run purely in
   the browser. Confirms AC-1/2/3/4 offline.
3. **Scene behaviours:** Scene 1 → rate-limiter red, links balanced, victim healthy (AC-2). Scene 2 → defence lamps
   green, one link red, victim collapsed, weak-PRNG salt on screen (AC-3). Scene 3 → salt rotates to opaque value,
   links scatter, victim healthy; drag the slider slow→fast and watch saturation re-establish then collapse (AC-4).
4. **QRNG provenance:** select QRNG → provenance panel shows `entropy_epoch`/`timestamp`/bytes/endpoint/`receipt`,
   labelled as provenance (§3.2).
5. **Tier B (stretch):** with the P4-instrumented controller running its WS layer, select `live` → link bars track
   real OVS port-stats; select `replay` → the recorded sweep drives the same bars with no live infra (AC-5).

## Out of scope
- Producing the underlying data (P5) and the paper (P7).
- The **WebSocket server** (thin port-stat push layer on the Ryu controller) — see Open Questions OQ-2; the browser
  WS *client* (`ws.ts`) is in scope, the controller-side server is not owned here by default.
- Tier B live infra generally — Tier A ships first and does not depend on it.

## Risks
- **TS/Python hash drift** → build-time parity assert against P2 vectors (above); build fails on drift.
- **GitHub Pages base path** breaks static asset/replay-JSON loading → set `basePath`/`assetPrefix` in
  `next.config.js` and verify the exported bundle loads from a subpath, not just `/`.
- **Q-EaaS reachability** for the live provenance panel → fall back to the recorded provenance record (replay);
  never block a scene on a network call. Handle `503 low_quantum_entropy`/`429` gracefully (epic §8 Q6).
- **Scope creep from Tier B** → Tier A `[SHOULD]` is the commitment; Tier B `[COULD]` is stretch. Ship A first.

## Open questions
- **OQ-1 — `/web` location confirm.** Placed at `TargetedDosColisionsAndRNGAngle/web/` (inside the epic project,
  beside `testbed/`), matching the repo's existing FastAPI+Next convention for Q-EaaS. *Proposed default: adopt.*
  Alternative: a repo-root `/web`. Confirm before scaffolding.
- **OQ-2 — Who owns the Tier B WebSocket *server* (Ryu port-stat push)?** The browser client is in P6; the
  controller-side WS layer touches P4's instrumentation. *Proposed default: build the thin WS push layer as part of
  P6 Tier B (it is demo infrastructure), reading P4's port-stat polling — not P4's job.* Confirm.
- **OQ-3 — Styling / charting library.** Slider + bars are simple; a chart lib is optional. *Proposed default: no
  chart framework — plain CSS + SVG, keep the static bundle small and dependency-light.* Confirm.
