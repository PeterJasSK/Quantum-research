# Plan 6 — The web spectacle

**Epic:** `plans/epic-dns-poison-race.md` (Status: **Approved** 2026-07-30) · **Plan ID:** P6 · **Priority:** `[MUST]`
**Slug:** web-demo · **Author:** Claude (Opus) · **Date:** 2026-08-02 · **Status:** Draft (awaiting approval)

> Epic §3.3 locks this as a **first-class deliverable** — the spectacle carries the thesis. It must be
> as polished as the shipped twin `../TargetedDosColisionsAndRNGAngle/web/` (Next 16 static export,
> hand-rolled canvas + `requestAnimationFrame`, dark mode, JS↔Python parity gate). This plan clones
> that project's stack, layout, and discipline file-for-file; every convention here has a working
> precedent one directory over.

---

## Goal

Ship `DNSPoisonRace/web/` — a self-contained static-export Next.js interactive visualization that
renders the whole DNS-poison-race story client-side: the poison race (attacker forged-answer flood
vs authoritative reply), the self-drawing entropy cliff, the SAD-DNS reveal that collapses the safe
CSPRNG curve, a guess-space heatmap, and a QRNG provenance panel. The browser's race/hit logic is
**gated on JS↔Python parity** (epic §3.6, AC-6.6): `next build` refuses to run unless a vendored JS
mirror of the Python race engine reproduces `testbed/vectors/race_vectors.json` exactly.

## Context — what P1–P5 froze that P6 consumes (never re-implements)

P6 is the terminal consumer. It re-implements **nothing** of the Python model; it mirrors the race
engine in JS for the animation + parity gate, and reads P5's frozen replay JSON for the aggregate
curves.

- **Python race source-of-truth (P1/P3) — the JS mirror target.** The exact logic P6's JS must
  reproduce, all stdlib, all deterministic:
  - `testbed/sim/event_queue.py` — `heapq`-backed queue keyed `(time, seq)`; `seq` is a monotonic
    push counter so `payload` never participates in ordering (epic Risks: ordering must be
    reproducible in JS). **The tie-break rule is load-bearing for parity.**
  - `testbed/attacker/portable_prng.py` — `splitmix64(state) -> (value, next_state)` (64-bit,
    integer-only) and `bounded(state, n) -> (value % n, next_state)`. **Every** reproducible random
    choice (guess order, RTT jitter, parity targets) flows through this; never `random.Random`/
    `os.urandom`. This is the parity contract P6 vendors verbatim (its module docstring names P6).
  - `testbed/attacker/guessing.py` — `GuessStream` (seeded, distinct-guess rejection sampling with
    a seen-set + `reset_round()`), `effective_index(draw, port_bits, k)`, `guess_space_size(...)`.
  - `testbed/draw/sad_dns.py` — `sad_dns_leak(port_bits, k) = max(0, port_bits - k)` and
    `effective_bits(txid_bits, port_bits, k) = txid_bits + sad_dns_leak(...)`.
  - `testbed/sim/race.py` — `run_race(draw, forged_guess, rtt, send_schedule, seed) -> RaceResult`
    (literal `(txid, port)` match) and `run_attack_race(windows_spec, guess_stream, send_rate_pps,
    rtt, retransmit, parallel_queries, seed) -> AttackRaceResult` (effective-index match). The one
    canonical acceptance rule `_accepts(guess, target, t_event, t_auth) = guess == target and
    t_event < t_auth` (epic §5) is shared by both paths so they cannot drift.
  - `testbed/vectors/gen_race_vectors.py` — builds `race_vectors.json` from `SCENARIOS` (4 direct
    `run_race` rows) + `FLOOD_SCENARIOS` (3 `_flood_vector` rows: derives `windows_spec` targets +
    RTT jitter + `send_schedule` from `splitmix64`, then calls `run_attack_race`). **This is exactly
    what the parity gate must reproduce.**
- **`testbed/vectors/race_vectors.json` (P1, frozen).** The Python-generated golden vectors, the
  parity source of truth. Current row schema (per element): `{seed, txid, port, eff_bits, rtt,
  retransmit, send_schedule, parallel_queries, outcome, forged_packets, t_outcome}`. **See OQ-6.1 —
  these rows are not yet self-describing enough for a row-wise JS recompute; an additive enrichment
  is proposed.**
- **`Draw` / `DrawProvenance` canonical shape (P2, `testbed/types.py`).** Field order `(txid, port)`;
  `to_bytes()` = `struct.pack("!HH", txid, port)`; provenance excluded from the acceptance rule. P6's
  JS packing (if any) must match this big-endian order.
- **P5 replay JSON (already exported to `web/public/replay/`).** The aggregate curves + scenario
  descriptors + provenance receipt P6 renders. Frozen contract (see the dedicated section below):
  `cliff.json`, `collapse.json`, `race_fixed|prng|csprng|qrng.json`, `qrng-provenance.json`.
- **`testbed/config.py` knobs (P1).** `TXID_BITS=16`, `PORT_BITS` (default 16), `RTT_SECONDS=0.02`,
  `RETRANSMIT_SECONDS=0.5`, `RTT_JITTER_FRAC=0.1`, `ATTACKER_SEND_RATE_PPS=10000`. P6 mirrors the
  values it needs as UI defaults in `web/lib/constants.ts` — it does **not** read `config.py`.

## Acceptance criteria (verbatim from epic §9 P6, §THE VISUALIZATION)

- **AC-6.1 — The poison race.** A split timeline where the attacker's forged-answer stream sprays
  guesses at the resolver while the authoritative reply races back; a hit lights the cache red
  (poisoned) or green (legit wins first). Replayable per source.
- **AC-6.2 — Entropy cliff.** An animated curve drawing itself as the entropy slider drops:
  flat-safe, then a sudden fall to near-certain poisoning.
- **AC-6.3 — SAD-DNS reveal.** A toggle for the side-channel port leak that visibly collapses the
  safe CSPRNG curve (provenance/state beats raw source quality).
- **AC-6.4 — Guess-space heatmap.** A TXID×port grid with attacker coverage filling in over time vs
  the single correct cell.
- **AC-6.5 — Provenance panel.** Renders the QRNG Q-EaaS receipt (mirror ECMP `ProvenancePanel`).
- **AC-6.6 — Static + parity-gated.** Self-contained static HTML/Canvas, dark mode, `output:
  "export"`; the build is **gated on JS↔Python race-logic parity** (§3.6) — the browser must
  reproduce the Python race outcomes.

## Design

All web paths relative to `DNSPoisonRace/web/`. Stack pinned to the twin: **Next 16.2.10, React
19.2.4, next-themes ^0.4.6, clsx ^2.1.1, Tailwind v4** (`@tailwindcss/postcss`, no `tailwind.config`),
TypeScript ^5, `eslint-config-next 16.2.10`. TypeScript `strict`; `allowJs: true` (the vendored
`raceCore.js` is JS); `resolveJsonModule`; path alias `@/* -> ./*`. No animation library — canvas +
`requestAnimationFrame` only, exactly as `LiveFatTree.tsx`.

### Stack & static-export config

- **`next.config.ts`** — clone verbatim: `output: "export"`, `basePath`/`assetPrefix` both from
  `process.env.NEXT_PUBLIC_BASE_PATH ?? ""` (GitHub-Pages subpath, OQ-6 in epic), `images:
  {unoptimized: true}`, `turbopack: {root: __dirname}`. `next build` emits `web/out/` (no separate
  export step on Next 16).
- **`package.json`** — clone deps/devDeps above. Scripts: `dev: "next dev"`, `check:parity: "node
  scripts/check-parity.mjs"`, `vendor:p6: "node scripts/vendor-p6.mjs"`, `build: "npm run
  check:parity && next build"` (the parity gate, AC-6.6), `lint: "eslint"`. Package name
  `dns-poison-race-web-demo`.
- **`postcss.config.mjs`**, **`eslint.config.mjs`**, **`tsconfig.json`** — clone the twin's
  (single `@tailwindcss/postcss` plugin; flat eslint config ignoring `.next/**`, `out/**`,
  `next-env.d.ts`; `target ES2017`, `module esnext`, `moduleResolution bundler`, `noEmit`).

### App shell (`app/`)

- **`app/layout.tsx`** — `Inter` + `JetBrains_Mono` from `next/font/google` → `--font-inter`,
  `--font-jetbrains-mono` on `<html>` (`h-full antialiased`, `suppressHydrationWarning`). Wraps
  `<ThemeProvider><Nav/><main>{children}</main><Footer/></ThemeProvider>`. `metadata`:
  `metadataBase: new URL(WEB_URL)`, title `"DNS Poison Race · how many entropy bits stop a cache
  poisoner?"`, a description drawn from epic §1, `alternates.canonical: "/"`. Separate `viewport`
  export. **Analytics:** omit the Cloudflare `<Script>` for now (the twin hard-codes its own beacon
  token — shipping that token here would mis-attribute; see OQ-6.3).
- **`app/page.tsx`** — two lines: `export default function Home(){ return <PoisonRaceController/> }`.
  All page logic lives in the one client controller (mirror ECMP `page.tsx`).
- **`app/globals.css`** — `@import "tailwindcss";` then `@theme{}` defining `--font-*` and a
  `--color-*` token palette; dark mode via `[data-theme="dark"]{…}` overriding the same tokens
  (attribute-based, **not** Tailwind `dark:`). `@utility` classes: `panel`, `card-hover`, `chip`,
  `pill`, and the outcome lamps `lamp`/`lamp-green` (RESOLVED-LEGIT) / `lamp-red` (POISONED) — the
  §5 terminal-state colours the race animation lights up. Palette adapted from the twin
  (attacker-red / authoritative-green / safe-cyan).
- **`app/robots.ts`** — `dynamic = "force-static"`; allow `*` + explicit AI-crawler list; `sitemap:
  ${WEB_URL}/sitemap.xml`, `host: WEB_URL`.
- **`app/sitemap.ts`** — `force-static`; entry `/` (priority 1.0, `changeFrequency monthly`).
- **`app/manifest.ts`** — `force-static`; PWA manifest, `name: "DNS Poison Race — how many entropy
  bits stop a cache poisoner?"`, `short_name: "DNS Poison Race"`, `display: "standalone"`, theme/
  background colours from the palette.

### Components (`components/`)

All interactive components are `"use client"`. Presentational-only ones (`Nav`, `Footer`,
`QeaasCallout`, `StructuredData`) are server components.

- **`PoisonRaceController.tsx`** (client) — the whole page (ECMP `LoadBalanceController` analogue).
  Owns all state: `source: "fixed"|"prng"|"csprng"|"qrng"`, `effectiveBits` (slider, epic sweep
  8→32), `sadDnsLeakK` (SAD-DNS reveal toggle/slider), `parallelQueries` (birthday amplification),
  `running`, `speed`, plus the loaded replay payloads. On mount, loads `cliff.json`, `collapse.json`,
  and the four `race_<kind>.json` via `lib/replay.ts`. Derives a representative race scenario per
  `(source, effectiveBits, sadDnsLeakK, parallelQueries)` and feeds it to the canvas via
  `raceCore.traceFloodRace(...)`. Renders hero copy + source tablist + sliders +
  `<PoisonRaceCanvas/>` + `<EntropyCliff/>` + `<GuessSpaceHeatmap/>` + `<ProvenancePanel/>` +
  `<QeaasCallout/>`. **No business logic in JSX** — all derivation is in `lib/raceCore.js` and small
  `lib/` helpers; the component only wires state to props.
- **`PoisonRaceCanvas.tsx`** (client, AC-6.1) — the hand-rolled canvas + `requestAnimationFrame`
  loop (clone `LiveFatTree.tsx`'s structure: logical coordinate system, DPR-scaled `setTransform`,
  mutable `Packet[]`, refs mirroring `running`/`speed` so the loop reads live values without
  re-subscribing, theme colours parsed from CSS vars). Renders a split timeline: the resolver on one
  side, the authoritative server on the other; the attacker sprays forged-answer packets (many
  in-flight, dosing toward the resolver on the `send_schedule` times) while a single authoritative
  reply travels back over `rtt`. Props: `{ trace, running, speed, onOutcome }` where `trace` =
  `raceCore.traceFloodRace(...) → { events, sendSchedule, windows, result }`. On the winning event
  it lights the cache lamp `lamp-red` (POISONED) or `lamp-green` (RESOLVED-LEGIT) and calls
  `onOutcome(result)`. Replayable per source (re-key on `source`). The animation is a faithful
  render of the Python outcome — the terminal `result` must equal the `race_<kind>.json` descriptor
  for the matching cell (cross-checked by the parity gate, not by the browser at runtime).
- **`EntropyCliff.tsx`** (client, AC-6.2 + AC-6.3) — an SVG/canvas curve that draws itself
  (`requestAnimationFrame`-animated path) from `cliff.json` as the `effectiveBits` slider drops:
  flat-safe at high bits, a sharp fall to near-certain poisoning at low bits, one line per source.
  When the SAD-DNS toggle is on it overlays `collapse.json`'s CSPRNG series collapsing as `k` rises
  (the "safe curve falls" beat). Props: `{ cliff, collapse, effectiveBits, sadDnsK, sadDnsOn }`.
- **`SadDnsToggle.tsx`** (client, AC-6.3) — the labelled toggle + `k`-bit slider that drives
  `EntropyCliff`'s collapse overlay (kept a separate control so the reveal reads as a deliberate
  action). Props: `{ on, k, onToggle, onK }`.
- **`GuessSpaceHeatmap.tsx`** (client, AC-6.4) — a canvas TXID×port grid; attacker coverage fills in
  over time following the **real `GuessStream` order** from `raceCore` (seeded, distinct guesses),
  with the single correct cell highlighted. Props: `{ trace, running, speed }`. Cells shade as each
  guess is "sprayed"; the correct cell flips when the winning guess lands (or stays cold if the
  authoritative reply wins). Grid is downsampled for large spaces (e.g. bins for `eff_bits > 16`) —
  a display-only aggregation, never a change to the guess logic.
- **`ProvenancePanel.tsx`** (client, AC-6.5) — clone ECMP: `useEffect` → `loadRecordedProvenance()`,
  renders the receipt. **Shape matches P5's `qrng-provenance.json`** = `{kind: "qrng", detail:
  {request_id, entropy_epoch, timestamp, receipt, endpoint}}` (note this is nested under `detail`,
  unlike the twin's flat record — see the replay-contract section). Renders the `detail` fields in a
  `<dl>`; shows the sample-placeholder honestly if P5 has not yet frozen a real receipt.
- **`Nav.tsx`** — header + `<ThemeToggle/>`. **`Footer.tsx`** — static footer.
- **`ThemeProvider.tsx`** (client) — `next-themes` `ThemeProvider` with `attribute="data-theme"`,
  `themes=["light","dark"]`, `defaultTheme="system"`, `enableSystem`, `storageKey="dns-poison-theme"`.
- **`ThemeToggle.tsx`** (client) — light/dark segmented pill, `useTheme` + `useSyncExternalStore`
  mount guard, inline SVG icons (no icon dep). Clone the twin.
- **`QeaasCallout.tsx`** — static QEaaS marketing callout, adapted copy (provenance-not-magic, epic
  §3.2). **`StructuredData.tsx`** — JSON-LD `<script>` injector, prop `{data}`.

### lib/ — data loaders + vendored race core

- **`lib/urls.ts`** — `WEB_URL = process.env.NEXT_PUBLIC_WEB_URL ?? "https://dnsrace.peterjas.sk"`
  (OQ-6.2), `API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://api.qeaas.eu"`. Env-driven,
  never hard-coded elsewhere.
- **`lib/constants.ts`** — UI defaults mirroring `config.py` values used for display: `TXID_BITS
  = 16`, `PORT_BITS = 16`, `RTT_SECONDS = 0.02`, `RETRANSMIT_SECONDS = 0.5`, `RTT_JITTER_FRAC = 0.1`,
  `ATTACKER_SEND_RATE_PPS = 10000`, `EFF_BITS_MIN = 8`, `EFF_BITS_MAX = 32`. Comment: mirrors
  `testbed/config.py`; not read from Python.
- **`lib/qeaas.ts`** — `interface QrngProvenance { kind: string; detail: { request_id: string;
  entropy_epoch: string | number; timestamp: string; receipt: string; endpoint: string } }`;
  `SAMPLE_QRNG_PROVENANCE` placeholder (labelled NOT a real receipt); `loadRecordedProvenance()` =
  `fetch(${NEXT_PUBLIC_BASE_PATH ?? ""}/replay/qrng-provenance.json)`, falls back to the sample on
  non-ok/throw. **Key-out-of-browser posture (epic Appendix A.4):** the static bundle only ever
  reads this pre-recorded JSON; the `QEAAS_API_KEY` never reaches the browser.
- **`lib/replay.ts`** — typed loaders, each applying the basePath prefix inline (`assetPrefix` does
  not rewrite `fetch`): `loadCliff() → CliffData`, `loadCollapse() → CollapseData`,
  `loadRaceScenario(kind) → RaceScenario`. Types match the frozen replay contract below. Throw with
  a clear "P5 has not landed this recording" message on non-ok.
- **`lib/raceCore.js`** (vendored, `allowJs`) — **the JS mirror of the Python race**, copied verbatim
  from `testbed/vectors/race_core.js` by `vendor-p6.mjs`. Exports (matching the Python surface):
  `splitmix64(stateBigInt) → [value, next]`, `bounded(state, n) → [idx, next]`, `GuessStream`
  (distinct-guess rejection sampling), `effectiveBits(txid_bits, port_bits, k)`,
  `runRace(seed, [txid,port], forgedGuess, rtt, sendSchedule) → {outcome, forged_packets,
  t_outcome}`, `buildFloodVector(seed, txid, port, txid_bits, port_bits, k, rtt, retransmit,
  send_rate_pps, parallel_queries, retransmit_rounds, rtt_jitter_frac) → {send_schedule, outcome,
  forged_packets, t_outcome}`, and a display-only `traceFloodRace(...) → {events, sendSchedule,
  windows, result}` (same numbers as `buildFloodVector` plus the intermediate event list the canvas
  animates). **Implementation notes for parity (these are the drift risks):**
  - `splitmix64` uses `BigInt` with the exact constants `0x9E3779B97F4A7C15`,
    `0xBF58476D1CE4E5B9`, `0x94D049BB133111EB` and `& ((1n<<64n)-1n)` masking; final index via
    `Number(value % BigInt(n))` (safe, `n ≤ 2**32`).
  - The event queue is a min-heap (or sort) keyed **`(time, seq)`** with `seq` a monotonic push
    counter — identical push order to Python so equal-time ties resolve identically; `payload` never
    compared.
  - Float expressions must match Python **operator order byte-for-byte** (IEEE-754 doubles agree
    across Python/JS only if the op sequence is identical): jitter =
    `(jitter_unit/1_000_000 - 0.5) * 2 * rtt_jitter_frac * rtt`; `send_schedule[i] =
    max_t_authoritative / forged_count * (i + 0.5)`; `forged_count = Math.trunc(max_t_authoritative
    * send_rate_pps)` (Python `int()` truncates toward zero).
- **`lib/raceVectors.json`** (vendored) — copy of `testbed/vectors/race_vectors.json`, the parity
  golden set (staleness-guarded).

### Parity gate (`scripts/`) — the build-gating correctness contract (AC-6.6)

Two scripts, cloning the twin's `vendor-p2.mjs` / `check-parity.mjs` split.

- **`scripts/vendor-p6.mjs`** — copies the Python-adjacent source-of-truth artefacts into `web/lib/`,
  staleness-guarded exactly like `vendor-p2.mjs`. `PAIRS`:
  - `testbed/vectors/race_core.js` → `web/lib/raceCore.js`
  - `testbed/vectors/race_vectors.json` → `web/lib/raceVectors.json`
  For each pair: content-equal → "up to date"; with `--write` → overwrite; without `--write`, any
  difference sets `stale` and `process.exit(1)` (a forgotten re-vendor after the testbed changes
  fails loudly).
- **`scripts/check-parity.mjs`** — imports the vendored `raceCore.js`, iterates every row of the
  vendored `raceVectors.json`, recomputes the outcome from that row's inputs, and asserts equality
  with the stored outputs; any mismatch prints `vector[i] MISMATCH …` and `process.exit(1)`:
  - `mode === "run_race"` rows → `runRace(seed, [txid,port], forged_guess, rtt, send_schedule)`;
    assert `outcome`, `forged_packets` (integer `===`) and `t_outcome` (exact `===`, doubles are
    deterministic — see OQ-6.4 for the epsilon fallback).
  - `mode === "flood"` rows → `buildFloodVector(seed, txid, port, txid_bits, port_bits, k, rtt,
    retransmit, send_rate_pps, parallel_queries, retransmit_rounds, rtt_jitter_frac)`; assert
    `send_schedule` (element-wise exact), `outcome`, `forged_packets`, `t_outcome`.
  On success: `check-parity: N/N vectors match`. Wired into `build` (`check:parity && next build`)
  so **the static export cannot ship on drift.**

**New Python-adjacent files this plan adds (the only work outside `web/`):**
- `testbed/vectors/race_core.js` — the source-of-truth JS mirror (ECMP places its mirror at
  `testbed/vectors/ecmp_hash.js`; this is the direct analogue). Lives beside `gen_race_vectors.py`
  so Python + JS are reviewed together; vendored into `web/lib/` by `vendor-p6.mjs`.
- `testbed/vectors/gen_race_vectors.py` — **edit (additive, OQ-6.1)** to make each emitted row
  self-describing so `check-parity.mjs` can recompute it: append per-row a `mode` discriminator; for
  `run_race` rows append `forged_guess: [gtxid, gport]`; for flood rows append `txid_bits`,
  `port_bits`, `k`, `send_rate_pps`, `retransmit_rounds`, `rtt_jitter_frac`. Existing keys and their
  order are unchanged (P1's "schema stability" for the JS mirror is extended, not broken). Regenerate
  `race_vectors.json` by running the generator once (a manual-verification step).

### The replay JSON contract P6 consumes (frozen by P5, already present in `web/public/replay/`)

- **`cliff.json`** (AC-6.2) — `{ "sources": { "fixed"|"prng"|"csprng"|"qrng": [{ "effective_bits":
  int, "poison_rate": float }, … sorted by bits] }, "send_rate_pps": int }`.
- **`collapse.json`** (AC-6.3) — `{ "kind": "csprng", "series": [{ "k": int, "poison_rate": float },
  … sorted by k] }`.
- **`race_<kind>.json` ×4** (AC-6.1) — a scenario descriptor per source: `{ "kind", "seed",
  "txid_bits", "port_bits", "k", "send_rate_pps", "rtt", "retransmit", "parallel_queries",
  "outcome", "t_outcome", "forged_packets" }`. P6 renders the descriptor and re-derives the animated
  race from it via `raceCore.traceFloodRace(...)`.
- **`qrng-provenance.json`** (AC-6.5) — `{ "kind": "qrng", "detail": { "request_id", "entropy_epoch",
  "timestamp", "receipt", "endpoint" } }`. May currently hold the P5 sample-placeholder (`detail`
  values = `"sample-placeholder"`) until a `.env`-authenticated P5 export freezes a real receipt;
  P6 renders whatever is present, honestly (never presents the placeholder as an attestation).

## File plan

All paths under `DNSPoisonRace/`. New unless marked **edit**. `web/` is a fresh Next 16 app cloned
from `../TargetedDosColisionsAndRNGAngle/web/`; TypeScript `strict`, no `any` in authored code, no
business logic in JSX. `web/public/replay/*.json` already exist (P5) and are consumed, not authored.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `web/package.json` | Deps (Next 16.2.10, React 19.2.4, next-themes, clsx, Tailwind v4) + scripts incl. `build: "check:parity && next build"`, `vendor:p6`. | AC-6.6 | Clone twin; package name `dns-poison-race-web-demo`. |
| `web/next.config.ts` | `output: "export"`, `basePath`/`assetPrefix` = `NEXT_PUBLIC_BASE_PATH`, `images.unoptimized`, `turbopack.root`. | AC-6.6 | Verbatim clone (epic OQ-6). |
| `web/tsconfig.json` | `strict`, `allowJs`, `resolveJsonModule`, `@/*` alias, ES2017/esnext/bundler. | — | Clone; `allowJs` for vendored `raceCore.js`. |
| `web/postcss.config.mjs` | Single `@tailwindcss/postcss` plugin. | — | Clone. |
| `web/eslint.config.mjs` | Flat config, `eslint-config-next` core-web-vitals + typescript; ignores `out/**`. | — | Clone. |
| `web/app/layout.tsx` | Fonts, `ThemeProvider`, `Nav`/`main`/`Footer`, DNS metadata + `viewport`. | AC-6.5 | No analytics `<Script>` (OQ-6.3). |
| `web/app/page.tsx` | Renders `<PoisonRaceController/>`. | AC-6.1–6.5 | Two lines, mirror twin. |
| `web/app/globals.css` | `@import "tailwindcss"`, `@theme` tokens, `[data-theme="dark"]` overrides, `panel`/`card-hover`/`chip`/`pill`/`lamp-red`/`lamp-green` utilities. | AC-6.1 | Red=poisoned, green=legit (§5). |
| `web/app/robots.ts` | `force-static`; allow `*` + AI crawlers; sitemap/host from `WEB_URL`. | — | Clone. |
| `web/app/sitemap.ts` | `force-static`; `/` entry. | — | Clone. |
| `web/app/manifest.ts` | `force-static`; DNS-poison PWA manifest. | — | Clone. |
| `web/components/PoisonRaceController.tsx` | Page controller; owns source/bits/k/parallel/running/speed state; loads replay JSON; wires props. | AC-6.1–6.5 | `"use client"`; no logic in JSX. |
| `web/components/PoisonRaceCanvas.tsx` | Canvas + rAF poison-race animation; forged flood vs authoritative reply; red/green cache lamp. | AC-6.1 | Clone `LiveFatTree` structure; driven by `raceCore.traceFloodRace`. |
| `web/components/EntropyCliff.tsx` | Self-drawing cliff from `cliff.json`; SAD-DNS collapse overlay from `collapse.json`. | AC-6.2, AC-6.3 | rAF-animated path per source. |
| `web/components/SadDnsToggle.tsx` | SAD-DNS reveal toggle + `k` slider driving the collapse. | AC-6.3 | Separate control for the reveal beat. |
| `web/components/GuessSpaceHeatmap.tsx` | Canvas TXID×port grid; attacker coverage fills via real `GuessStream` order; correct cell highlighted. | AC-6.4 | Downsampled for `eff_bits>16` (display-only). |
| `web/components/ProvenancePanel.tsx` | Loads `qrng-provenance.json`; renders `detail` receipt fields. | AC-6.5 | Shape = `{kind, detail:{…}}`; honest placeholder. |
| `web/components/Nav.tsx` | Header + `ThemeToggle`. | — | Clone. |
| `web/components/Footer.tsx` | Static footer. | — | Clone. |
| `web/components/ThemeProvider.tsx` | `next-themes` provider, `data-theme`, `storageKey="dns-poison-theme"`. | — | Clone. |
| `web/components/ThemeToggle.tsx` | Light/dark pill, mount guard, inline SVG. | — | Clone. |
| `web/components/QeaasCallout.tsx` | Static QEaaS callout (provenance-not-magic). | AC-6.5 | Adapted copy. |
| `web/components/StructuredData.tsx` | JSON-LD injector. | — | Clone. |
| `web/lib/urls.ts` | `WEB_URL`/`API_URL` from env. | — | Defaults per OQ-6.2. |
| `web/lib/constants.ts` | UI defaults mirroring `config.py`. | AC-6.1 | Not read from Python. |
| `web/lib/qeaas.ts` | `QrngProvenance` iface (nested `detail`), sample, `loadRecordedProvenance`. | AC-6.5 | Key never in browser (Appendix A.4). |
| `web/lib/replay.ts` | `loadCliff`/`loadCollapse`/`loadRaceScenario`; basePath-prefixed `fetch`. | AC-6.1–6.3 | Typed to the frozen contract. |
| `web/lib/raceCore.js` | **Vendored** JS mirror of the Python race (splitmix64/GuessStream/runRace/buildFloodVector/traceFloodRace). | AC-6.6 | Copied by `vendor-p6.mjs`; do not hand-edit in `web/`. |
| `web/lib/raceVectors.json` | **Vendored** copy of `race_vectors.json` (parity golden set). | AC-6.6 | Copied by `vendor-p6.mjs`. |
| `web/scripts/vendor-p6.mjs` | Staleness-guarded vendor of `race_core.js` + `race_vectors.json`. | AC-6.6 | Clone `vendor-p2.mjs`. |
| `web/scripts/check-parity.mjs` | Recompute every vector row via `raceCore`; assert equality; `exit(1)` on drift. | AC-6.6 | Clone `check-parity.mjs`; wired into `build`. |
| `testbed/vectors/race_core.js` | Source-of-truth JS mirror beside the Python (analogue of `ecmp_hash.js`). | AC-6.6 | New; the only new file outside `web/`. |
| `testbed/vectors/gen_race_vectors.py` | **edit (additive)** — append `mode` + the recompute inputs to each row (OQ-6.1); regenerate `race_vectors.json`. | AC-6.6 | Additive only; existing keys/order unchanged. |
| `web/README.md` | Runbook: `dev`, `vendor:p6 --write`, `check:parity`, `build`, the `NEXT_PUBLIC_*` envs, the replay-JSON contract, how the parity gate works. | — | New; mirror twin `web/README.md`. |
| `web/.gitignore` | Ignore `node_modules/`, `.next/`, `out/`, `next-env.d.ts`, `*.tsbuildinfo`. **Commit `public/replay/*.json`** (P6 needs it). | — | Clone twin (does not ignore `public/`). |
| `.gitignore` | **edit (verify)** — confirm the repo root does not blanket-ignore `web/`; ensure `web/public/replay/*.json` stays committed. | — | Check at implementation time. |

## Manual verification (no automated tests — project directive)

Run from `DNSPoisonRace/`. No pytest; correctness = the parity gate + eyeballing the spectacle.

1. **Regenerate + vendor the parity artefacts.**
   - `python testbed/vectors/gen_race_vectors.py` → rewrites `race_vectors.json` with the additive
     fields; confirm it prints `wrote N vectors` and existing rows kept their original keys.
   - `cd web && node scripts/vendor-p6.mjs --write` → copies `race_core.js` + `race_vectors.json`
     into `web/lib/`; re-run without `--write` and confirm "up to date" (no staleness).
2. **Parity gate passes.** `cd web && npm run check:parity` prints `check-parity: N/N vectors
   match`. Deliberately perturb one constant in `web/lib/raceCore.js` (e.g. flip a splitmix64
   constant) and confirm it now reports `MISMATCH` and exits non-zero — proves the gate has teeth.
   Restore.
3. **Static export builds.** `cd web && npm install && npm run build` → parity runs first, then
   `next build` emits `web/out/` with no errors. Confirm `out/index.html` exists and
   `out/replay/*.json` are copied through.
4. **Spectacle, by hand** (`npm run dev`, open `localhost:3000`):
   - AC-6.1 — pick each source in turn; the forged-answer flood animates against the authoritative
     reply; `fixed`/`prng` at low bits light the cache **red** (poisoned), `csprng`/`qrng` at high
     bits light **green** (legit). Terminal outcome matches the `race_<kind>.json` descriptor.
   - AC-6.2 — drag the entropy slider down; the cliff curve draws itself flat-then-falls.
   - AC-6.3 — toggle SAD-DNS and raise `k`; the CSPRNG curve visibly collapses toward the fixed/prng
     line.
   - AC-6.4 — the TXID×port heatmap fills with attacker coverage over time; the single correct cell
     is distinct; it flips only when a forged guess wins.
   - AC-6.5 — the provenance panel renders the `qrng-provenance.json` receipt fields (or the labelled
     sample if P5 has not frozen a real receipt).
   - Toggle dark/light — palette flips via `data-theme`, no hydration flash.
5. **Subpath sanity.** `NEXT_PUBLIC_BASE_PATH=/dns-poison-race npm run build` then serve `web/out/`
   under that subpath; confirm `replay/*.json` fetches resolve (basePath applied inline in
   `qeaas.ts`/`replay.ts`).

## Tech

- Next 16.2.10 static export (`output: "export"`), React 19.2.4, Tailwind v4 (`@theme` +
  `[data-theme]`), `next-themes`, TypeScript strict. Hand-rolled canvas + `requestAnimationFrame`,
  **no animation library** (epic §3.3, clone `LiveFatTree`).
- Parity: `BigInt` splitmix64, min-heap `(time, seq)` event queue, IEEE-754-double-exact float order.
- Node scripts are ESM `.mjs` (`vendor-p6.mjs`, `check-parity.mjs`), run by `node`, no extra deps.

## Out of scope

- Any server-side key handling or live Q-EaaS call from the browser — the app renders only the
  **recorded** `qrng-provenance.json`; `QEAAS_API_KEY` never reaches the browser (epic §9 P6 OOS,
  Appendix A.4). The live receipt is captured by P5's export step, not here.
- Producing the replay JSON or the figures — that is P5 (already exported). P6 consumes them.
- New race logic, new sources, or the SAD-DNS math — all owned by P1/P2/P3; P6 only mirrors them in
  JS for the animation + gate.
- The IEEE paper prose (P7).
- Cloudflare/analytics wiring and a production domain purchase (OQ-6.2/6.3) — env-driven defaults
  ship; real values are a deploy-time concern.

## Risks

- **Float parity drift (highest).** Python and JS both use IEEE-754 doubles, so results agree **only
  if the operator order is identical**. Mitigation: `raceCore.js` mirrors each Python float
  expression token-for-token (documented inline); `check-parity.mjs` compares `t_outcome` and
  `send_schedule` with exact `===`. If a legitimate last-ULP difference appears, fall back to a tiny
  epsilon **and print a `WARN`** (never silently widen the tolerance) — see OQ-6.4.
- **Event-queue tie-break drift.** If the JS queue orders equal-`time` events differently from
  Python's `(time, seq)`, outcomes diverge. Mitigation: push in identical order, key strictly on
  `(time, seq)`, never compare payloads (mirror `event_queue.py`).
- **Stale vendored mirror.** If `race_core.js`/`race_vectors.json` change testbed-side but `web/lib/`
  is not re-vendored, the browser ships stale logic. Mitigation: `vendor-p6.mjs` staleness guard +
  the manual step 1; consider adding `vendor:p6` (check mode) ahead of `check:parity` in `build` if
  drift bites (kept out for now to match the twin, which vendors manually).
- **Placeholder provenance.** If P5 has not run a `.env`-authenticated export, `qrng-provenance.json`
  is the sample-placeholder; the panel must render it as clearly-not-real (epic §3.2). No crash, no
  false attestation.
- **Big guess space in the heatmap.** `eff_bits` up to 32 → 2³² cells cannot render 1:1. Mitigation:
  bin/downsample for display only; the underlying `GuessStream` order is unchanged.

## Open questions — RESOLVED (2026-08-02, developer: "accept all defaults; defer the name")

- [x] **OQ-6.1 — Enrich `race_vectors.json` rows so the JS parity gate can recompute them?**
  **Decision:** accept the recommended additive enrichment.
- [x] **OQ-6.2 — Production `WEB_URL` default?** **Decision:** deferred — the site name/domain is not
  chosen yet. Ship a neutral env-overridable default `http://localhost:3000` (valid for
  `new URL(...)`, signals "not chosen"); no SEO/domain investment now. Revisit before deploy.
- [x] **OQ-6.3 — Ship web analytics?** **Decision:** omit for now.
- [x] **OQ-6.4 — Exact vs epsilon float comparison?** **Decision:** exact `===`; epsilon+`WARN` only
  if a real last-ULP divergence surfaces. Exact `===` held for all 7 vectors — no epsilon needed.

## Post-implementation (2026-08-02)

Built and verified. `DNSPoisonRace/web/` is a Next 16.2.10 static export cloning the twin; the only
work outside `web/` was `testbed/vectors/race_core.js` (new JS mirror) + the additive enrichment of
`gen_race_vectors.py` (per OQ-6.1). Verified independently:

- **Parity gate passes 7/7** (`node scripts/check-parity.mjs`) — the vendored JS `race_core.js`
  reproduces every `race_vectors.json` row exactly (outcome, `forged_packets`, and float
  `send_schedule`/`t_outcome` via exact `===`). Teeth confirmed: perturbing a splitmix64 constant
  fails 3/7 and exits non-zero.
- **`npm run build` passes** — `check:parity` gates `next build`; `out/index.html` +
  `out/replay/*.json` emitted. `npm run lint` clean. Vendored `lib/raceCore.js`/`lib/raceVectors.json`
  are byte-identical to the testbed source (`vendor-p6.mjs` reports "up to date").

Notes / carried-forward gaps (P5 data, not P6 bugs):
- No `race_qrng.json` in `web/public/replay/` (only fixed/prng/csprng) — `loadRaceScenario("qrng")`
  falls back to the CSPRNG descriptor relabelled `qrng` (the honest null-result, epic §3.2). When P5
  re-exports with a `qrng` cell, the file appears and the fallback stops firing.
- `cliff.json`'s `qrng` series is empty and `collapse.json` is all-zeros in the current P5 export —
  `EntropyCliff` skips empty source lines and renders the flat overlay honestly. A fuller P5 sweep
  will populate them with no P6 change.
- The **canvas animations** drive a *display* trace (`buildFloodVector(..., trace)` plus a small
  documented source-entropy penalty + guess-space binning so fixed/prng visibly poison and large
  spaces downsample). This is presentation only — it never touches the parity path; race correctness
  is proven solely by the gate.
- `npm audit` reports 3 high-severity advisories in the transitive tree (identical to the twin's
  pinned versions); left as-is to honour the version pin.

### Original questions (for the record)

- **OQ-6.1 — Enrich `race_vectors.json` rows so the JS parity gate can recompute them?**
  The current P1 rows lack the flood inputs (`k`, `port_bits`, `send_rate_pps`, `retransmit_rounds`,
  `rtt_jitter_frac`) and the `run_race` `forged_guess`, so a row-wise JS recompute (the ECMP
  parity shape) is impossible without them. **Proposed (recommended):** additively append those
  fields plus a `mode` discriminator to `gen_race_vectors.py`'s output — existing keys and order
  unchanged, so P1's JS-mirror schema stability is *extended*, not broken — and regenerate. The only
  alternative (bake the `SCENARIOS`/`FLOOD_SCENARIOS` tables into `race_core.js`) duplicates the
  inputs in two languages and invites drift. Needs a nod because it edits a P1 file.
- [ ] **OQ-6.2 — Production `WEB_URL` default.** **Proposed:** `https://dnsrace.peterjas.sk` (mirrors
  the twin's `ecmp.peterjas.sk`), overridable via `NEXT_PUBLIC_WEB_URL`. Confirm the hostname or
  supply the intended one; it only affects `metadataBase`/robots/sitemap/manifest.
- [ ] **OQ-6.3 — Ship web analytics?** The twin hard-codes a Cloudflare beacon token. **Proposed:**
  omit analytics entirely for now (shipping the twin's token would mis-attribute); add a
  DNS-project token later if wanted.
- [ ] **OQ-6.4 — Exact vs epsilon float comparison in the gate.** **Proposed:** assert exact `===`
  on `t_outcome`/`send_schedule` (doubles are deterministic given identical op order); only if a
  real last-ULP divergence surfaces during implementation, switch that field to an epsilon compare
  **with a printed `WARN`**, never a silent tolerance.
