# Plan 6 — Web demonstration: three scenes (Next.js `/web` app, Tier A + Tier B)

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 5** · **Priority:** `[SHOULD]` (Tier B `[COULD]`)
**Status:** Complete (Tier A) — Tier B scaffolded, not wired (2026-07-26) · **Depends on:** P2 (shared vectors, landed) · Tier B also P4 (CSV/counters), P5 (replay data)

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
- **P2 (landed, commit `6adb4d2`)** — the demo **vendors P2's already-shipped JS parity artefacts verbatim**
  (see D-parity): `testbed/vectors/ecmp_hash.js` (the `ecmpLink` mirror of Python `ecmp_link`) and
  `testbed/vectors/hash_vectors.json` (28 shared vectors). The demo's hash logic *is* P2's, not a re-mirror.
- **P4 (in progress, untracked)** — real OVS port-stat counters over WebSocket (Tier B live). No WS layer exists
  in the testbed today; metrics are file-based CSV/JSONL (see §Dependencies).
- **P5 (Draft)** — the recorded sweep subset for replay (Tier B replay) and the Q-EaaS provenance record.
- **Q-EaaS** — recorded `/v1/random/bytes` provenance for the QRNG panel; **no live browser call carrying the API
  key** (see D-qrng-key). Hosted base URL `https://api.qeaas.eu` (epic §8 Q6).

**Stack — mirror the repo's existing Next convention (`qrng-eaas/web/`):** Next **16.2.10**, React **19.2.x**,
TypeScript `^5` (`strict`, `moduleResolution: "bundler"`, path alias `@/* → ./*`), Tailwind CSS **v4**
(`@tailwindcss/postcss`), ESLint 9 + `eslint-config-next`. Non-standard Next 16 + Tailwind v4 — consult the bundled
docs under `node_modules/next/dist/docs/01-app/` rather than pre-16 App-Router assumptions (the sibling app's
`CLAUDE.md`/`AGENTS.md` carry the same warning).

## Decision D-web — Next.js static export reconciles the "static HTML page" AC *(frozen here)*
The verbatim AC says "static HTML page." Next.js with `output: 'export'` in `next.config.ts` produces a **fully
static HTML/JS bundle** with **no server runtime** — deployable to GitHub Pages and runnable offline, exactly
satisfying the Tier A AC while giving a real component framework for the three scenes and the Tier B live/replay
modes. **Tier A = the static export** (no Node server, no infra). **Tier B = the same static bundle** plus a client
WebSocket/replay data source; still no Next.js server — only a browser talking to the Ryu controller's thin WS layer.
So "static HTML page" and "Next.js app" are not in conflict: the export *is* the static page. Recorded so no later
reviewer reads the Next.js choice as a violation of the AC.

> **Next 16 export mechanics (corrected):** there is **no `next export` command** — it was removed after Next 13.
> Setting `output: 'export'` in `next.config.ts` makes plain `next build` emit the static bundle to `web/out/`.
> So the build script is `next build` alone; **do not** add an `export` script or run `next export` (both fail on
> Next 16). Verified against the `qrng-eaas/web` Next 16.2.10 install.

## Decision D-parity — vendor P2's `ecmp_hash.js` verbatim, do NOT re-mirror in TS *(frozen here)*
P2 already shipped a browser-ready JS mirror of the Python hash: `testbed/vectors/ecmp_hash.js`. It uses
`crypto.subtle.digest("SHA-256", …)` + `BigInt` (works in-browser and in Node), exposes
`ecmpLink(fiveTuple, saltHex, nLinks)` and `fiveTupleToBytes(fiveTuple)`, and is already the artefact P2's own
parity checker (`testbed/vectors/check_parity.py`) asserts against the Python source of truth. Re-writing it as a
fresh `hashCore.ts` would create a **second** implementation that can silently drift from Python — the exact failure
epic §3.3 forbids. So the demo **vendors the file unchanged** (copied into `web/lib/`, or the whole `vectors/` dir
symlinked/copied at build time) and adds only a thin `ecmpHash.d.ts` type declaration. Two consequences the
implementer must respect:
- `ecmpLink` is **async** (returns `Promise<number>`) — every call site awaits it.
- It takes the salt as a **hex string** (`saltHex`), not `bytes` — the SaltPanel/sim must carry salts as hex
  (matching P2's `salt_hex` vector field and the Q-EaaS `data` hex payload).

## Two tiers
- **Tier A — browser-only `[SHOULD]`, ships first.** All salt/hash/bucket logic in JS/TS, using P2's **vendored**
  `ecmp_hash.js` + `hash_vectors.json` (D-parity). `next build` (with `output: 'export'`) → static bundle in
  `web/out/` on GitHub Pages; usable as a conference QR code. Needs **only P2** (already landed), no testbed infra.
- **Tier B — connected `[COULD]`, stretch.** Same front-end; link bars + victim numbers driven by **real OVS
  port-stat counters** over WebSocket from the Ryu controller. Sub-modes: **live** (WS to controller) + **replay**
  (recorded P5 sweep bundled as static JSON — no live infra needed for talks).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [x] **AC-1** Static HTML page, all salt/hash/bucket logic in JS (mirrors Python, shares EPIC 1 vectors). Topology view: attacker, switch, 4 links, victim. — `web/next.config.ts` (`output: 'export'`), `web/lib/ecmpHash.js` (vendored), `web/scripts/check-parity.mjs` (28/28 pass), `web/components/TopologyView.tsx`.
- [x] **AC-2** **Scene 1** naive flood → rate-limiter fires (red on attacker), links balanced, victim healthy. — `web/components/SceneController.tsx:52-59` (rate-limited flood, `rateLimiterActive: true`), `web/components/DefenceIndicators.tsx`.
- [x] **AC-3** **Scene 2** precision mode → limiter/throttle stay green, one link climbs to red, victim collapses; predictable weak-PRNG salt shown on screen. — `web/components/SceneController.tsx:61-70` (`weakPrngSaltHex`, `findColliding5Tuple` targeting link 0, defences `false/false`), `web/components/SaltPanel.tsx`.
- [x] **AC-4** **Scene 3** CSPRNG + rotation → links scatter, rotation event visibly disperses the crafted 5-tuples, victim stays healthy; **rotation-frequency slider** re-establishes/collapses saturation live (Experiment 5 interactive). QRNG selection shows entropy provenance without overstating. — `web/components/SceneController.tsx:72-96` (rotation timer + lock-on model), `web/components/RotationSlider.tsx`, `web/components/ProvenancePanel.tsx`, `web/lib/qeaas.ts`.
- [~] **AC-5** Same front-end; link bars + victim numbers driven by **real OVS port-stat counters** over WebSocket from the Ryu controller. Sub-modes: live + replay (recorded sweep, no live infra needed for talks). — **scaffolded, not wired**: `web/lib/datasource.ts` (interface + `sim` impl), `web/lib/ws.ts`, `web/lib/replay.ts` are typed stubs; controller-side WS server (OQ-2) and P5's recorded sweep don't exist yet, so `live`/`replay` throw a clear "not wired" error if selected. Out of scope per plan (Tier B `[COULD]`, stretch).
- **Done when:** Tier A runs the three scenes offline on GitHub Pages ✅ (verified: `npm run build` succeeds, `grep -r X-API-Key web/out/` empty, dev server starts clean); (stretch) Tier B shows real counters live or on replay — not done, deferred to P4/P5 landing.

> AC-1 realised via Next.js static export (D-web). "all salt/hash/bucket logic in JS" → **vendored**
> `lib/ecmpHash.js` (P2's `ecmp_hash.js`, D-parity) + a thin `lib/ecmp.ts` for collision-set/bucket-spread demo
> logic, asserted against P2's `hash_vectors.json` at build time.

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
When QRNG is selected, show the **real** Q-EaaS provenance from `/v1/random/bytes`. The concrete fields (verbatim
from P2's `QRNGResponse` / `SaltProvenance`): `request_id`, `entropy_epoch` (DRBG reseed counter), `timestamp` (UTC),
byte count (`size` = 32), endpoint (`{QEAAS_BASE_URL}/v1/random/bytes`), and the Ed25519 `receipt`
(`qeaas1.<payload>.<sig>`). Label honestly — **attestable entropy provenance**, not "stops the attack better."

Source of the record (see D-qrng-key): Tier A and replay read the **recorded** provenance record (epic §4, from
P5's QRNG run) bundled as static JSON — a static browser bundle must never embed the Q-EaaS API key. This is the
visible payoff of the practical-QRNG angle without overstating the null result.

## Decision D-qrng-key — never ship the Q-EaaS API key in the static bundle *(frozen here)*
The keyed endpoint `GET /v1/random/bytes` requires header `X-API-Key`, and provenance (`receipt`, `entropy_epoch`)
only comes from the keyed endpoint — the anonymous `GET /random?bytes=` returns no provenance. A Tier A static
bundle on GitHub Pages has no server to hold a secret, so a "live" browser fetch would have to embed the key in
client JS — a credential leak. Therefore:
- **Tier A / replay (the shipping commitment):** provenance comes from the **recorded** P5 QRNG record (static
  JSON). No network, no key.
- **Tier B live (stretch):** if a genuinely live receipt is wanted on stage, the browser calls the **Ryu
  controller's WS/proxy** (which already holds `QEAAS_API_KEY` server-side via P2's config), never `api.qeaas.eu`
  directly with an embedded key.
This keeps the provenance story honest and the secret server-side. Handle `503 low_quantum_entropy`/`429`
gracefully (epic §8 Q6) — fall back to the recorded record, never block a scene.

## File plan
New Next.js app; nothing exists under `TargetedDosColisionsAndRNGAngle/web/` yet. TypeScript (`strict`), App Router,
function components; Tailwind v4 for styling (mirrors `qrng-eaas/web`). All paths relative to
`TargetedDosColisionsAndRNGAngle/`. Keep the bundle static (D-web).

| File | Purpose | Notes |
|------|---------|-------|
| `web/package.json` | Next 16.2.10 + React 19 + Tailwind v4 deps, scripts: `dev`, `build` (runs parity first), `check:parity`, `lint`. **No `export` script** (D-web). | Mirror `qrng-eaas/web`. |
| `web/next.config.ts` | `output: 'export'`; `basePath`/`assetPrefix` for GitHub Pages project path; `images.unoptimized: true`. | D-web — static export, no server. |
| `web/postcss.config.mjs` | **Copied verbatim** from `qrng-eaas/web` (`@tailwindcss/postcss`). | OQ-3 — identical styling. |
| `web/tsconfig.json` | Strict TS, `moduleResolution: "bundler"`, `@/* → ./*`. | Copy `qrng-eaas/web`. |
| `web/lib/theme.ts` | **Copied verbatim** from `qrng-eaas/web/lib/theme.ts` + `next-themes` provider wiring. | OQ-3. |
| `web/app/layout.tsx` | Root layout; same `next/font` families + `next-themes` provider as `qrng-eaas/web`; scene-agnostic chrome. | OQ-3. |
| `web/app/globals.css` | **Copied verbatim** from `qrng-eaas/web/app/globals.css` — same Tailwind v4 entry, design tokens, palette, dark-mode. | OQ-3 — sites visually identical. |
| `web/app/page.tsx` | Demo shell: scene stepper (1→2→3), data-source selector (sim/live/replay), salt-source selector. | Wires all components. |
| `web/components/TopologyView.tsx` | Attacker, switch, N=4 links, victim — the topology diagram. | AC-1. SVG. |
| `web/components/LinkBars.tsx` | N=4 link-utilisation bars; red at saturation (≥ `SATURATION_UTILISATION` 0.9). | AC-2/3/4. Driven by data source. |
| `web/components/VictimThroughput.tsx` | Victim throughput bar (healthy/collapsed at `VICTIM_COLLAPSE_MBPS` 1.0). | AC-2/3/4. |
| `web/components/DefenceIndicators.tsx` | Rate-limit + throttle status lamps (green/red). | AC-2 red, AC-3 stay-green. |
| `web/components/SaltPanel.tsx` | Shows active salt (hex); weak-PRNG value visible in Scene 2; opaque rotating salt in Scene 3. | AC-3/4. Salt carried as hex (D-parity). |
| `web/components/RotationSlider.tsx` | Scene 3 rotation-frequency slider; drives re-establish/collapse of saturation. | AC-4 (Exp 5 interactive). |
| `web/components/ProvenancePanel.tsx` | QRNG `request_id`/`entropy_epoch`/`timestamp`/bytes/endpoint/`receipt`, honestly labelled. | §3.2, D-qrng-key. |
| `web/components/SceneController.tsx` | Advances scenes, applies each scene's salt-source + attack-mode preset. | |
| `web/lib/ecmpHash.js` | **Vendored verbatim** from `testbed/vectors/ecmp_hash.js` (D-parity) — `ecmpLink(fiveTuple, saltHex, nLinks)` **async**, `fiveTupleToBytes`. Do not edit. | AC-1. *Is* P2, not a re-mirror. |
| `web/lib/ecmpHash.d.ts` | Thin TS declarations for the vendored JS (`FiveTuple`, `ecmpLink → Promise<number>`). | Types only. |
| `web/lib/ecmp.ts` | Collision-set / bucket-spread demo logic (awaits `ecmpLink`). | AC-3/4. |
| `web/lib/vectors.json` | **Vendored verbatim** from `testbed/vectors/hash_vectors.json` (28 vectors; fields `five_tuple`,`salt_hex`,`n_links`,`link`). | Consumed by the parity check. |
| `web/lib/datasource.ts` | One interface, three impls: `sim` (Tier A, pure JS), `live` (WS), `replay` (JSON). | AC-5 — same front-end, swappable source. |
| `web/lib/ws.ts` | WebSocket client → Ryu controller port-stat stream (Tier B live). | AC-5. Server side = §Dependencies / OQ-2. |
| `web/lib/replay.ts` | Loads recorded sweep subset from `public/replay/`. | AC-5 replay. |
| `web/lib/qeaas.ts` | Read recorded Q-EaaS provenance record (Tier A/replay); optional Tier B proxy call. | §3.2, D-qrng-key — no embedded key. |
| `web/public/replay/*.json` | Recorded P5 sweep **subset** (epic §8 Q4): 3-scene runs + QRNG provenance run + full rotation-interval sweep. Blind skipped. | From P5. |
| `web/scripts/check-parity.mjs` | Build-time assert: runs vendored `ecmpHash.js` `ecmpLink` over every `vectors.json` row, compares to `link` — **exits non-zero on drift**, wired into `build`. | Epic §3.3 "asserts fail on drift" — build tooling, not a test suite. |
| `web/scripts/vendor-p2.mjs` | Copies `testbed/vectors/ecmp_hash.js` + `hash_vectors.json` into `web/lib/`; fails if source changed but copy stale. | Keeps the vendored copies honest to P2. |
| `web/README.md` | Run/build/deploy (GitHub Pages) + how to point Tier B at a live controller or replay + how to re-vendor P2. | |

## Parity — the hard constraint (epic §3.3)
The demo's hash logic **must be identical** to Python. Two layers guarantee it:
1. **Vendoring, not re-mirroring (D-parity):** `web/lib/ecmpHash.js` is P2's `testbed/vectors/ecmp_hash.js` copied
   byte-for-byte; `web/lib/vectors.json` is P2's `hash_vectors.json` copied byte-for-byte. There is no hand-written
   second implementation to drift. `web/scripts/vendor-p2.mjs` re-copies and fails the build if the `web/` copy is
   stale versus the testbed source.
2. **Build-time assert:** `web/scripts/check-parity.mjs` runs the vendored `ecmpLink` over every `vectors.json` row
   and compares to the expected `link`; **any mismatch exits non-zero** and fails `npm run build`. Mirrors P2's own
   `testbed/vectors/check_parity.py` (which asserts the same JS against the Python source of truth), so the chain is
   Python ⇄ vectors ⇄ vendored JS ⇄ demo.

This is a build-time assertion, not an automated test (project directive), and it is what stops the demo silently
lying. Note `ecmpLink` is async — the parity script must `await` each call.

## Dependencies on other plans
- **P2 (hard, LANDED commit `6adb4d2`):** the vendored `testbed/vectors/ecmp_hash.js` and
  `testbed/vectors/hash_vectors.json` are P2's shared JS↔Python artefacts — **they exist now**, so Tier A is
  unblocked. P2 owns the vector format; P6 consumes it verbatim (D-parity). Salts are hex strings (`salt_hex`).
- **P4 (Tier B only, IN PROGRESS/untracked):** live counters come from the controller's in-process port-stat poll
  loop (`_port_stats_poll_loop` in `testbed/controller/ecmp_controller.py`) and the CSV schema in
  `testbed/metrics/csv_writer.py` (columns `link{i}_util`, `max_link_util`, `jains_index`, `victim_mbps`, …). **There
  is no WebSocket layer in the testbed today** — all output is file-based (CSV + JSONL). Tier B must add the thin WS
  push (OQ-2). The demo's `LinkBars`/`VictimThroughput` map onto these columns.
- **P5 (Tier B replay, Draft):** the recorded replay subset (`public/replay/*.json`) + the Q-EaaS provenance record.
  Tier A does not need P5 — `sim` datasource generates the scene numbers in-browser.
- **Q-EaaS:** hosted `https://api.qeaas.eu` (epic §8 Q6, resolved). Per D-qrng-key the static bundle uses the
  **recorded** provenance record, not a live keyed browser call.

## Manual verification (no automated tests)
1. **Parity (constraint):** `npm run check:parity` in `web/` → passes when TS matches P2 vectors; break a vector to
   confirm it fails (then restore). Also runs inside `npm run build`.
2. **Tier A offline (Done-when):** `npm run build` (with `output: 'export'` this emits `web/out/`; **there is no
   `next export` step** — D-web), serve `web/out/` from a plain file server (or open the exported HTML), step
   Scene 1→2→3 with the network **disconnected** — all three scenes must run purely in the browser. Confirms
   AC-1/2/3/4 offline.
3. **Scene behaviours:** Scene 1 → rate-limiter red, links balanced, victim healthy (AC-2). Scene 2 → defence lamps
   green, one link red, victim collapsed, weak-PRNG salt on screen (AC-3). Scene 3 → salt rotates to opaque value,
   links scatter, victim healthy; drag the slider slow→fast and watch saturation re-establish then collapse (AC-4).
4. **QRNG provenance:** select QRNG → provenance panel shows `request_id`/`entropy_epoch`/`timestamp`/bytes/
   endpoint/`receipt` from the recorded record, labelled as provenance (§3.2); confirm no API key appears anywhere
   in the shipped `web/out/` bundle (D-qrng-key) — `grep -r X-API-Key web/out/` returns nothing.
5. **Tier B (stretch):** with the P4-instrumented controller running its WS layer, select `live` → link bars track
   real OVS port-stats; select `replay` → the recorded sweep drives the same bars with no live infra (AC-5).

## Out of scope
- Producing the underlying data (P5) and the paper (P7).
- The **WebSocket server** (thin port-stat push layer on the Ryu controller) — see Open Questions OQ-2; the browser
  WS *client* (`ws.ts`) is in scope, the controller-side server is not owned here by default.
- Tier B live infra generally — Tier A ships first and does not depend on it.

## Risks
- **JS/Python hash drift** → eliminated by vendoring (D-parity) + the build-time parity assert against P2's
  `hash_vectors.json`; build fails on drift, and `vendor-p2.mjs` fails if the copy is stale versus the testbed source.
- **Next 16 export gotcha** → `next export` no longer exists; rely on `output: 'export'` + `next build` (D-web). A
  stray `next export` in scripts/README would fail CI.
- **GitHub Pages base path** breaks static asset/replay-JSON loading → set `basePath`/`assetPrefix` in
  `next.config.ts`, `images.unoptimized: true`, and verify the exported bundle loads from a subpath, not just `/`.
- **Q-EaaS key leak** → static bundle uses the **recorded** provenance record only; no `X-API-Key` in client JS
  (D-qrng-key). Live receipts (Tier B) go through the controller proxy that holds the key server-side.
- **Async hash ergonomics** → `ecmpLink` returns a Promise; forgetting to `await` yields `[object Promise] % N`
  bugs. Call sites and the parity script must await.
- **Scope creep from Tier B** → Tier A `[SHOULD]` is the commitment; Tier B `[COULD]` is stretch. Ship A first.

## Open questions — RESOLVED (2026-07-26, all defaults accepted)
- **OQ-1 — `/web` location. [RESOLVED: adopt.]** App lives at `TargetedDosColisionsAndRNGAngle/web/`, beside
  `testbed/`, matching the `qrng-eaas/api` + `qrng-eaas/web` convention. Greenfield (no existing `web/`).
- **OQ-2 — Tier B WebSocket *server* ownership. [RESOLVED: P6 owns it.]** No WS layer exists in the testbed; metrics
  are file-based CSV/JSONL. P6 Tier B builds the thin WS push layer (demo infrastructure) reading P4's
  `_port_stats_poll_loop` — not P4's job. Browser client `ws.ts` + controller-side push both live in P6 Tier B.
- **OQ-3 — Styling. [RESOLVED: reuse `qrng-eaas/web` styling *exactly*.]** Not just "Tailwind v4" — the demo copies
  the sibling app's styling foundation verbatim so the two sites are visually identical: the same
  `app/globals.css` (Tailwind v4 `@import "tailwindcss";` + the same CSS custom-property design tokens / colour
  palette / dark-mode setup), the same `postcss.config.mjs`, the same font wiring in `layout.tsx`
  (`next/font` families as `qrng-eaas/web`), the same `lib/theme.ts` + `next-themes` provider, and the same base
  component styling idioms (spacing, radius, card/lamp/bar classes). Charts: still no chart framework — plain SVG
  bars styled with the shared tokens. **Action for the implementer:** copy `qrng-eaas/web`'s `app/globals.css`,
  `postcss.config.mjs`, `lib/theme.ts`, font setup, and `next-themes` wiring into `web/` as the styling baseline,
  then build the scene components on top of those tokens. Add these to the File Plan when scaffolding.
- **OQ-4 — Vendor vs re-mirror the hash. [RESOLVED: vendor (D-parity).]** Vendor P2's `ecmp_hash.js`; no second
  implementation. Parity still asserts against `hash_vectors.json`.
- **OQ-5 — Live QRNG receipt. [RESOLVED: recorded record for Tier A/replay; live only via controller proxy.]** The
  static bundle holds no API key (D-qrng-key). A recorded-but-real Ed25519-signed receipt is an acceptable
  attestation for the conference demo; live receipts require the Tier B controller proxy.

## Post-implementation (2026-07-26)

Built Tier A in full at `TargetedDosColisionsAndRNGAngle/web/`: Next.js 16.2.10 + React 19.2.4 static-export app,
Tailwind v4 styling copied from `qrng-eaas/web` (light/dark only — dropped the sibling app's unrelated "quantum"
Easter-egg theme, not part of this plan), vendored `ecmpHash.js`/`vectors.json` from P2 with a build-time parity
assert (28/28 vectors pass) and a `vendor-p2.mjs` staleness check. All three scenes are driven by the real vendored
`ecmpLink` (not fabricated numbers): Scene 1 buckets a rate-limited flood across links, Scene 2 uses a weak-PRNG
salt + `findColliding5Tuple` to target link 0, Scene 3 runs a rotation timer with a time-since-rotation "lock-on"
model so the rotation-frequency slider visibly re-establishes/collapses saturation.

**Deviations from the file plan:**
- `web/lib/ws.ts`, `web/lib/replay.ts`, `web/lib/datasource.ts`'s `live`/`replay` impls, and
  `web/public/replay/*.json` (sweep data) are typed **scaffolding, not wired** — P4's controller has no WS server
  yet (OQ-2, owned by this plan's Tier B) and P5 (Draft) hasn't landed a recorded sweep. Selecting them throws a
  clear "not wired yet" error rather than faking data. This matches the plan's own "Out of scope" section (Tier B
  live infra is stretch); flagging it explicitly since the File Plan table lists these files without marking them
  stretch-only.
- `web/public/replay/qrng-provenance.json` is a **structurally-accurate sample**, clearly labelled as a placeholder
  in-file and in the README — not a real Q-EaaS receipt, since P5 hasn't produced one yet. Swap it for P5's actual
  recorded run before using the demo publicly; the `ProvenancePanel`/`qeaas.ts` code path is otherwise final.
- No Header/Footer/StructuredData/next-themes "quantum" theme — plan explicitly called `app/layout.tsx`
  "scene-agnostic chrome," so kept it to font + theme-provider wiring only.

**Verification performed (manual, no automated tests per project directive):**
- `npm run check:parity` → 28/28 vectors match.
- `npm run build` → clean TypeScript compile + static export to `web/out/`, no errors/warnings.
- `grep -r X-API-Key web/out/` → empty (D-qrng-key holds).
- `npm run dev` → starts clean, no runtime errors in server log.
- **Not performed:** interactive browser click-through of the three scenes / rotation slider — no headless-browser
  tool was available in this session. The build, type-check, and parity assert all pass, and the scene logic was
  traced by hand against `SceneController.tsx`, but visual/interactive confirmation in an actual browser is still
  outstanding and should be done before treating this as demo-ready for a conference.

**Follow-ups for the developer:**
- Manually open `web/out/index.html` (or `npm run dev`) in a browser and click through Scene 1→2→3 plus the
  rotation slider to confirm the visual behaviour matches the AC descriptions.
- When P4 lands a WS server and P5 lands recorded sweep data, wire `createLiveDataSource`/`createReplayDataSource`
  in `web/lib/datasource.ts` to the real `ws.ts`/`replay.ts` clients (currently stubs).
- Replace `web/public/replay/qrng-provenance.json` with P5's real recorded provenance record before any public demo.
