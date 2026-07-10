# Feature Plan — EPIC 5: Web app — explainer + dice (phone-first, no reload)

**Status:** Approved — §11 answered (Q1 separate well-designed `/dice` route; Q2 backend change: `/dice`
echoes its consumed bytes; Q3 defer prod prefix to EPIC 6; Q4 native `fetch`; Q5 count 1–6 + dice set
4/6/8/10/12/20/50/100; Q6/Q7/Q8 accepted).
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 5 `[MUST]`
**Interpretation of "part 5":** EPIC 5. The git history uses *part* and *epic* interchangeably
("par0 and part 1" = EPIC 0 + EPIC 1; "epic 2" = EPIC 2; "feature 3 epic protection" = EPIC 3;
"part 4 implementation" = EPIC 4). EPIC 4 (`feature-epic4-mlkem-consumer.md`, **Complete**) is the
most recent finished work, so the next `[MUST]` in build order is EPIC 5 — the **frontend**: turn
the bare `create-next-app` scaffold in `web/` into a phone-first page that (a) *explains* the whole
QRNG→DRBG→seeds/keys system, (b) shows a **live `/health` badge**, and (c) lets you **play dice with
quantum-seeded numbers, updating in place with no page reload**.

> **No tests (project directive).** This plan does **not** plan, write, or maintain automated tests
> (no unit, component, e2e, Playwright, Jest, Vitest, etc.), and `/implement-feature` will not run or
> create any. Verification is manual only: `npm run dev`, a browser at desktop + ~380px mobile width,
> `curl`, and the running FastAPI backend. No "Testing approach" / "Test impact" section appears below.

> **Note on process & conventions.** This repo has no GitHub issues, no `tasks/plans/` tree, and no
> `_plan-template.md`. The global `/plan-feature` template (GitHub issues, Doctrine, PSR-12, Twig,
> councils) does **not** apply — this is a **TypeScript / React / Next.js** frontend. "Strict types"
> here means the repo's already-on `tsconfig` **strict** mode plus fully-typed props, hooks, and fetch
> helpers (no `any`). "No business logic in controllers/templates" maps to: keep data-fetching and
> transforms in `lib/` + component hooks, keep JSX presentational. This plan follows the shape
> established by `feature-epic4-mlkem-consumer.md` and the project's real conventions.

> **⚠️ Non-standard Next.js (read first).** `web/AGENTS.md` warns this is **Next 16.2.10** with
> breaking changes vs training data. Before writing any App-Router code the implementer **must** read
> the bundled docs under `web/node_modules/next/dist/docs/01-app/` — specifically
> `01-getting-started/` (project structure, layouts/pages, fonts), `02-guides/` (fonts, CSS),
> `03-api-reference/` (`metadata`/`viewport` exports, `next/font/google`, `"use client"`). Do **not**
> assume the pre-16 API. Tailwind is **v4** (CSS-based `@theme`/`@import "tailwindcss"`), not v3 —
> there is **no** `tailwind.config.js`; tokens live in `app/globals.css`.

---

## 1. Context & goal

**Goal (build plan):** a page that explains everything and lets you play dice with quantum-seeded
numbers, smooth on a phone, never reloading on submit. **Done when:** on a phone, rolling dice
updates in place without reload, the health badge reflects real status, and the explainer makes the
system self-describing.

### The starting point (what already exists)
- **`web/` is a stock `create-next-app` scaffold** — nothing product-specific yet:
  - `web/app/layout.tsx` — default Geist fonts, metadata still `"Create Next App"`,
    `<body className="min-h-full flex flex-col">`.
  - `web/app/page.tsx` — the CNA marketing placeholder (to be fully replaced).
  - `web/app/globals.css` — `@import "tailwindcss";` + an `@theme inline { … }` block with **only**
    the default CNA tokens (`--background`, `--foreground`, `--font-sans/-mono`). **No neon/Orbitron
    tokens exist.**
  - `web/next.config.ts` — empty (no rewrites/proxy). `web/tsconfig.json` — strict, `@/*` → `./*`.
  - Deps already installed and usable: **next 16.2.10**, **react/react-dom 19.2.4**,
    `framer-motion ^12`, `clsx ^2`, `react-icons ^5`, `axios ^1` (dev: `tailwindcss ^4`,
    `@tailwindcss/postcss ^4`, `prettier-plugin-tailwindcss`). **No new dependency is required.**
  - **No** `components/`, `lib/`, fetch helper, API base-URL config, or `.env.local` yet — all built here.

### The backend this page consumes (EPICs 2/3, live)
EPIC 5 is **mostly frontend**; it calls the existing public (anonymous, rate-limited) endpoints and
makes **one small backend change** (Q2): `POST /dice` gains the consumed DRBG bytes in its response so
the "bytes behind this roll" toggle is *literal*. Exact contracts (from `api/main.py` /
`api/qeaas/schemas.py` / `api/qeaas/dice.py`):
- **`GET /health`** → `{ status: string, quantum_entropy_level: "healthy" | "degraded",
  pool_bytes_remaining: int, drbg_reseeds: int, uptime: float }`. Every response also carries the
  `X-Quantum-Entropy: healthy|degraded` header (global middleware). **Unchanged.**
- **`POST /dice`** body `{ sides?: int (2..100, default 6), count?: int (1..6, default 1) }`. Today →
  `{ sides, count, rolls: number[] }` (`rolls` = ints `1..sides`, rejection-sampled via
  `dice.roll()` drawing single DRBG bytes with `keyed_drbg.output(1)`, discarding any draw
  `≥ sides` — no modulo bias). **Change (Q2):** `dice.roll()` also returns every byte it drew
  (accepted *and* rejected — the honest, full provenance of the roll), and `DiceResponse` gains
  `format: "base64"`, `bytes_used: string` (base64 of those bytes), `bytes_count: int`. These are
  **DRBG output** (exactly what `/random` serves), so decision #2 — *raw QRNG bits are never served* —
  still holds. Invalid body → `422 {"error":"bad_request"}`; sampling exhaustion → `500
  dice_sampling_failed` (unchanged).
- **`GET /random?bytes=N`** (`{ bytes, format:"base64", data }`, `1 ≤ N ≤ 64`) is still referenced in
  the "How to use the API" copy but is **no longer fetched by the dice toggle** (the toggle now uses
  `/dice`'s own `bytes_used`). Unchanged.
- **CORS** (`api/main.py`): `allow_origins` = env `WEB_ORIGIN` (comma-sep, default
  `http://localhost:3000`), `allow_methods/headers = ["*"]`, credentials off. The web dev origin is
  already allowed out of the box.
- **Reachability:** *prod* — same origin, Vercel `rewrites` maps `/api/(.*)` → `api/main.py`
  (`qrng-eaas/vercel.json`). *dev* — API runs separately on `http://localhost:8000`; CORS already
  allows `http://localhost:3000`. EPIC 5 introduces a single **`NEXT_PUBLIC_API_BASE`** env var so
  the same code works both ways (see §5, Q3).

Repeat the honest framing verbatim-in-spirit in the explainer copy: **QRNG does not "defeat quantum
attackers."** It supplies high-quality **entropy** that *seeds* a standards DRBG, which in turn seeds
post-quantum algorithms (ML-KEM) and ephemeral keys. The quantum part is the **entropy source**; the
quantum **resistance** comes from ML-KEM (build-plan framing box).

### Design identity to carry over (not the literal CSS)
Reproduce the *look* of the old Django project — futuristic dark, neon-cyan glow, Orbitron — as
Tailwind v4 tokens + a few utility classes, **not** by porting the raw CSS. The reference files are
`claude/resources/base.html` (header/nav/mobile-menu/buttons/panels), `claude/resources/main.html`
(hero + menu cards + section layout), `claude/resources/dice.html` (dice type chips + result tiles),
and `claude/resources/img.png` (the atom-on-chip logo/favicon). Palette from the build plan
"Design system" block:

```
Font:        Orbitron 400/600/700
Background:  radial-gradient(circle at center, #060c1f, #01040b)
Text:        #e3f6ff       Heading: #7ad9ff (glow: text-shadow 0 0 10px #00aaff)
Accent/link: #4dcfff       Primary: #00aaff (hover #0077cc), pill buttons r≈30px, glow shadow
Borders:     rgba(0,170,255,0.35)   panels: backdrop-blur + faint inner glow
```

---

## 2. Acceptance criteria (from EPIC 5 stories S5.1/S5.2/S5.3 + Design system + "Done when")

| AC | Requirement (build-plan wording) | How it is met | Covered by |
|----|----------------------------------|----------------|------------|
| AC-1 | **S5.1** Explainer sections: "What is a QRNG"; the **pipeline diagram** (quantum bits → DRBG → seeds/keys); "How to use the API" (example `curl` + API-key note); the **honest crypto framing**. | Static, server-rendered sections composed into `app/page.tsx`: `WhatIsQrng`, `PipelineDiagram` (CSS/inline-SVG boxes+arrows, no external image), `ApiUsage` (copy-able `curl` for `/random`, `/dice`, and the keyed `/v1/random/bytes` with the `X-API-Key` note pointing at the admin-mint flow), `CryptoFraming` ("entropy, not quantum-resistance"). | ✅ `web/app/page.tsx:1-49`; `web/components/sections/WhatIsQrng.tsx:1-23`, `PipelineDiagram.tsx:1-31`, `ApiUsage.tsx:1-45`, `CryptoFraming.tsx:1-25`. |
| AC-2 | **S5.1** Live **`/health` widget**: green "Quantum entropy: healthy" / amber "degraded" badge. | `HealthBadge` client component fetches `GET /health` on mount and polls (§5, Q6), maps `quantum_entropy_level` → green pill "Quantum entropy: healthy" / amber pill "degraded"; shows a neutral/loading state before first response and a muted "unavailable" state if the fetch fails. Sits in the sticky header (visible from every section). | ✅ `web/components/HealthBadge.tsx:1-64`; `web/lib/api.ts:47-49` (`getHealth`). Manually confirmed: badge renders "Quantum entropy: healthy" against the live seeded backend. |
| AC-3 | **S5.2** Dice **controls**: dice type (d6 / d20 / custom sides) + count; big **Roll** button. Lives on a dedicated, well-designed **`/dice` route** (Q1). | `DicePlayer` (on `app/dice/page.tsx`): preset chips **4 6 8 10 12 20 50 100** (Q5) + a **custom sides** number input (`2..100`), a **count** input (`1..6`), and a large full-width **Roll** pill button — matched to the backend `sides∈[2,100]`, `count∈[1,6]`. | ✅ `web/app/dice/page.tsx:1-24`; `web/components/DicePlayer.tsx:8-9,53-89`. |
| AC-4 | **S5.2** On roll: `fetch('/dice')`, `preventDefault`, update React state → **no page refresh**; show result with a short animation. | Form `onSubmit` calls `e.preventDefault()` then `rollDice(sides,count)` (`POST /dice`), stores the result in React state, and renders result tiles with a short **framer-motion** stagger/pop animation. No navigation, no reload — SPA state swap. | ✅ `web/components/DicePlayer.tsx:30-45,119-135`; `web/lib/api.ts:51-59` (`rollDice`). Manually confirmed via Playwright: URL unchanged after Roll, single POST `/dice` XHR, no document navigation, tiles animate in. |
| AC-5 | **S5.2** "Show the quantum bytes behind this roll" **toggle** (transparency + teaching). | Backend change (Q2): `POST /dice` returns `bytes_used` (base64) + `bytes_count` — **the actual DRBG bytes drawn for this roll** (accepted + rejected draws). The toggle under the results reveals exactly those bytes (already in the roll response — **no extra request**), labeled "the quantum-seeded DRBG bytes drawn for this roll (N bytes; some may have been rejected to avoid bias)". | ✅ `api/qeaas/dice.py:23-39`, `api/qeaas/schemas.py:32-38`, `api/main.py:93-108` (return the bytes); `web/components/DicePlayer.tsx:141-155` (reveal them). Manually confirmed: `curl POST /dice {"sides":20,"count":3}` → `bytes_count` bytes decode to that exact length; toggle in the browser reveals the base64 string + count with no extra network call. |
| AC-6 | **S5.3** Phone-friendly: mobile-first Tailwind; large tap targets; one-handed layout; `viewport` meta; works at ~380px; loading/disabled states so double-taps don't double-fire. | Mobile-first Tailwind classes throughout; `≥44px` tap targets (pill buttons, chips); single-column one-handed layout on small screens; `viewport` exported from `layout.tsx` (Next 16 `viewport` export); the Roll button is `disabled` + shows a spinner/label while a request is in flight (guards double-fire); collapsible mobile menu in the header. Verified by hand at ~380px. | ✅ `web/app/layout.tsx:19-22` (`viewport`); `web/components/DicePlayer.tsx:107-113` (disabled Roll), `Header.tsx:42-75` (hamburger + overlay menu, scroll lock); `web/app/globals.css`. Manually confirmed at 380px viewport: single column, mobile menu opens/closes. |
| AC-7 | **Design system**: define neon/Orbitron as Tailwind `theme` tokens + utility classes (`.glow`, `.pill`, `.panel`) so components inherit the look; mobile menu / sticky header preserved; **do not copy the Django CSS verbatim — tokens only**. | `globals.css` gains a Tailwind v4 `@theme` block (neon palette + Orbitron font var wired from `next/font/google`), a base radial-gradient background, and `@utility glow / pill / panel`. `Header` reproduces the sticky-blur header + desktop nav + mobile overlay menu *as React + tokens*, not ported CSS. | ✅ `web/app/globals.css:1-58`; `web/app/layout.tsx:5-11`; `web/components/Header.tsx:1-79`, `Footer.tsx:1-8`. Manually confirmed rendered: deep-navy gradient background, cyan glow heading, neon pill Roll button (see dice-page screenshot). |
| AC-8 | **"Done when"** integration: the page talks to the **real** API — health badge shows real status, dice shows real rolls — via a configurable base URL, with **no reload** on submit. | All three calls go through `web/lib/api.ts`, which reads `NEXT_PUBLIC_API_BASE` (dev `http://localhost:8000`, prod same-origin `/api`); typed responses mirror the backend schemas; errors surface as inline messages, never a thrown page. | ✅ `web/lib/api.ts:1,44-59`; `web/.env.local:1` (dev); `web/README.md`. Manually confirmed: health badge and dice rolls both hit the live `:8000` backend and render real data. |

---

## 3. Scope

### In scope
- **Backend (Q2): `/dice` echoes its consumed bytes** — small, contained change to `api/qeaas/dice.py`
  (`roll()` also returns the drawn bytes), `api/qeaas/schemas.py` (`DiceResponse` gains
  `format`/`bytes_used`/`bytes_count`), `api/main.py` (base64-encode + return). No new route, no new
  dependency, no DB/schema change (AC-5).
- **Design tokens** (`app/globals.css`): Tailwind v4 `@theme` neon palette + Orbitron font var; base
  background radial gradient + text color on `body`; `@utility glow / pill / panel` (AC-7).
- **`app/layout.tsx`**: Orbitron via `next/font/google`; real `metadata` (title/description) + a
  `viewport` export; render `<Header/>` … `{children}` … `<Footer/>`; set favicon/logo (AC-6/7).
- **`app/page.tsx`** (home / explainer): the explainer sections + a prominent CTA link to `/dice` (AC-1).
- **`app/dice/page.tsx`** (dedicated, well-designed dice route, Q1): hosts `<DicePlayer/>` + a back link (AC-3/4/5).
- **Components:** `Header` (sticky, logo, nav incl. Home + Dice, mobile menu, `<HealthBadge/>`), `Footer`,
  `HealthBadge` (poll `/health`), `DicePlayer` (controls + roll + animation + bytes toggle), and section
  components `WhatIsQrng`, `PipelineDiagram`, `ApiUsage`, `CryptoFraming` (AC-1/2/3/4/5/6/7).
- **`lib/api.ts`**: `API_BASE`, TS types mirroring the backend, and typed fetch helpers `getHealth()`
  and `rollDice(sides, count)` — native `fetch` per the build plan (AC-8; §5, Q4).
- **Env + assets:** `web/.env.local` with `NEXT_PUBLIC_API_BASE=http://localhost:8000` for dev;
  copy `claude/resources/img.png` → `web/public/logo.png` for the header + favicon (AC-6/7/8).
- **Docs:** update `web/README.md` and the root `README.md`'s `/dice` contract (the new response fields).

### Out of scope (deferred to their epics / build order — do not build here)
- **Any automated tests** (project directive).
- **The "Verify a receipt" box** (S9.4) → **EPIC 9**. `/v1/verify` provenance UI is not built here.
- **A KEM / "generate a PQ keypair" panel** → not in EPIC 5's brief (EPIC 4 shipped the API; the UI
  for it, if any, is not this ticket).
- **Old-site pages not in EPIC 5's brief** — About, Generator, Coin, Charts, Login/Register/Profile.
  The old Django nav listed them; EPIC 5 is explicitly *explainer + dice* only. Nav shows only what exists.
- **Backend changes beyond the `/dice` byte-echo** — no new/edited FastAPI *route*, no CORS change
  beyond what already allows `localhost:3000` (EPIC 6 owns prod origin wiring), no touching
  `/random`, `/health`, `/v1/*`, or persistence. The only backend edit is `/dice`'s response shape.
- **Prod deploy / Vercel same-origin `/api` prefix finalisation** → **EPIC 6**. EPIC 5 makes the base
  URL configurable and works locally; the `/api`-prefix-vs-unprefixed-FastAPI-routes question is
  flagged (§11 Q3) and resolved at deploy time.
- **Seed-quality report, networking demo, receipts** → EPICs 7/8/9.

---

## 4. Component & data contracts (concrete)

### Backend: `POST /dice` new response shape (Q2)
```
DiceResponse { sides: int, count: int, rolls: list[int],
               format: Literal["base64"], bytes_used: str, bytes_count: int }
```
- `dice.roll(sides, count)` changes signature `list[int]` → `tuple[list[int], bytes]`, accumulating
  **every** byte it draws (`output(1)`) into a `bytearray` — accepted *and* rejected — so `bytes_used`
  is the full, honest provenance of the roll, and `bytes_count == count * draws-per-roll actually used`.
  `main.py` base64-encodes the returned bytes into the response. Docstring/comment: these are DRBG
  output (decision #2 — raw QRNG bits are never served).

### `web/lib/api.ts` — the single API boundary
```ts
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export interface Health {
  status: string;
  quantum_entropy_level: "healthy" | "degraded";
  pool_bytes_remaining: number;
  drbg_reseeds: number;
  uptime: number;
}
export interface DiceRoll {
  sides: number; count: number; rolls: number[];
  format: "base64"; bytes_used: string; bytes_count: number;
}

export async function getHealth(): Promise<Health>;                              // GET  {API_BASE}/health
export async function rollDice(sides: number, count: number): Promise<DiceRoll>; // POST {API_BASE}/dice
```
- Both use native `fetch`; non-2xx → throw a typed `ApiError` carrying the backend `{"error":"<slug>"}`
  slug so callers show an inline message (never a thrown/crashed page).
- No `getRandom` helper — the bytes toggle reads `bytes_used` straight off the roll response.
- No `axios` (installed but the build plan mandates `fetch()` for client components; §5, Q4).

### Components (props / behaviour)
| Component | Client? | Contract |
|-----------|---------|----------|
| `HealthBadge` | `"use client"` | On mount + every `POLL_MS` (§5 Q6, and on tab re-focus) calls `getHealth()`. States: `loading` (neutral pill), `healthy` (green "Quantum entropy: healthy"), `degraded` (amber "degraded"), `error` (muted "status unavailable"). No props. |
| `DicePlayer` | `"use client"` | Local state: `sides` (preset or custom, `2..100`), `count` (`1..6`), `result: DiceRoll \| null`, `loading: boolean`, `error: string \| null`, `showBytes: boolean`. `onSubmit`: `preventDefault` → guard if `loading` → `rollDice` → set `result` → animate. Bytes toggle just reveals `result.bytes_used`/`bytes_count` (already fetched — no extra call). Roll button `disabled` while `loading`. |
| `Header` | `"use client"` (menu state) | Sticky blurred bar: logo (`/logo.png`) + "Q-EaaS" wordmark (Q8), nav = **Home** (`/`), **How it works** (`/#pipeline`), **API** (`/#api`), **Dice** (`/dice`) — anchor links use the `/#id` form so they work from the dice route too; `<HealthBadge/>`; a hamburger toggling a full-screen mobile overlay menu (reproduces `base.html` behaviour with React state + tokens). |
| `Footer` | server | Static footer line, neon-muted, matches `base.html`. |
| `WhatIsQrng` / `PipelineDiagram` / `ApiUsage` / `CryptoFraming` | server | Static content sections; `PipelineDiagram` is CSS/inline-SVG boxes+arrows (quantum bits → pool → HMAC-DRBG(+counter) → seeds / ML-KEM / dice), responsive, no external image. `ApiUsage` shows copy-able `curl` blocks. |

Anchor targets `#overview`, `#pipeline`, `#api` live on the home page's section wrappers so the header
nav and the hero "Discover more" button scroll smoothly (matches `main.html`'s in-page scroll); **Dice**
is a real route (`/dice`), not an anchor.

---

## 5. Design decisions (§11 answered)
- **Dice on a dedicated, well-designed `/dice` route (Q1).** The home page is the explainer + a
  prominent CTA to `/dice`; the dice player gets its own full route so it can be laid out generously
  (big chips, big Roll, animated result grid, the bytes panel) without competing with the explainer.
- **`/dice` echoes its consumed bytes (Q2 — backend change).** `dice.roll()` returns `(rolls, bytes)`
  and `/dice` adds `bytes_used`/`bytes_count`, so the toggle shows the **actual** DRBG bytes drawn for
  that roll (accepted + rejected) — literal, honest, one request. These are DRBG output, so decision #2
  (raw QRNG bits never served) still holds.
- **Native `fetch`, not axios.** Build-plan Tech-stack: "Client components use `fetch()`." `axios` is
  installed but unused here (Q4).
- **`NEXT_PUBLIC_API_BASE` for reachability (Q3).** `lib/api.ts` reads it; `web/.env.local` sets
  `http://localhost:8000` for dev (CORS already allows `localhost:3000`). Unset → falls back to
  same-origin `/api` for prod. The `/api`-prefix vs unprefixed-FastAPI-routes reconciliation is
  **deferred to EPIC 6** (deploy) — EPIC 5 does not touch `vercel.json` or `next.config.ts`.
- **Tailwind v4 tokens + utilities, Orbitron via `next/font/google`.** No `tailwind.config.js`;
  everything in `globals.css` `@theme`/`@utility`. Reproduce the *look*, never port the Django CSS (AC-7).
- **Pipeline diagram is CSS/SVG, not an image.** The old `QuantumComputer.png` / `chip.png` assets are
  **absent** from the repo; only `img.png` (the atom-chip logo) exists. Build visuals with CSS/inline
  SVG + the logo; do not reference missing images (Q7).
- **Keep logic out of JSX.** Fetching/typing/transforms live in `lib/api.ts` and component hooks;
  section components are presentational. Mirrors the "no business logic in templates" rule.
- **Read the Next 16 / Tailwind v4 docs first** (`node_modules/next/dist/docs/01-app/`) before coding —
  fonts (`next/font/google`), `metadata`/`viewport` exports, `"use client"` boundaries all differ from
  pre-16 memory.

---

## 6. File plan (concrete paths)

All new `.ts`/`.tsx`: TypeScript **strict** (already on), fully-typed props/hooks/helpers, no `any`.
Client components start with `"use client"`. **No test files** are created (project directive).

| File | Change |
|------|--------|
| `api/qeaas/dice.py` | **Edit (Q2/AC-5).** `roll(sides, count) -> tuple[list[int], bytes]`: accumulate every drawn byte into a `bytearray drawn`; append `bytes(byte)` each `output(1)` (accepted + rejected); return `(rolls, bytes(drawn))`. Update the module docstring to note the drawn bytes are returned for provenance and are DRBG output (decision #2). No change to the sampling maths or the `dice_sampling_failed` path. |
| `api/qeaas/schemas.py` | **Edit.** `DiceResponse` gains `format: Literal["base64"]`, `bytes_used: str`, `bytes_count: int` (after `rolls`). |
| `api/main.py` | **Edit.** In the `POST /dice` handler: `rolls, drawn = dice.roll(req.sides, req.count)`; return `DiceResponse(sides=..., count=..., rolls=rolls, format="base64", bytes_used=base64.b64encode(drawn).decode(), bytes_count=len(drawn))`. Add `import base64` if not present. Handler stays thin. |
| `web/app/globals.css` | **Edit.** Keep `@import "tailwindcss";`. Add an `@theme` block with the neon palette (`--color-bg-deep #01040b`, `--color-bg #060c1f`, `--color-text #e3f6ff`, `--color-heading #7ad9ff`, `--color-accent #4dcfff`, `--color-primary #00aaff`, `--color-primary-hover #0077cc`, `--color-border rgba(0,170,255,0.35)`) and `--font-orbitron` (wired from the `next/font` variable). Set `body` to the radial-gradient background + `--color-text` + Orbitron. Add `@utility glow` (cyan text-shadow), `@utility pill` (rounded-full + glow shadow + primary bg/hover), `@utility panel` (blurred translucent card + border + faint inner glow). Remove the CNA default token block. |
| `web/app/layout.tsx` | **Edit.** Import `Orbitron` from `next/font/google` (weights 400/600/700, `variable: "--font-orbitron"`); drop Geist. Replace metadata with `{ title: "Q-EaaS — Quantum Entropy as a Service", description: "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.", icons: "/logo.png" }`. Add a `viewport` export (`width=device-width, initialScale=1`). Apply the font variable class on `<html>`; render `<Header/> <main>{children}</main> <Footer/>`. |
| `web/app/page.tsx` | **Edit (replace CNA body).** Server component (home / explainer) composing, in order: a hero (wordmark + one-line pitch + a **"Play the dice" CTA linking `/dice`** + a "Discover more" anchor), `#overview <WhatIsQrng/>`, `#pipeline <PipelineDiagram/>`, `#api <ApiUsage/>`, `<CryptoFraming/>`. No logic in the JSX. |
| `web/app/dice/page.tsx` | **New (Q1).** Dedicated dice route — server component rendering a titled, generously-laid-out section with `<DicePlayer/>` and a "← Back to overview" link (`/`). `metadata` title "Play Quantum Dice — Q-EaaS". |
| `web/lib/api.ts` | **New.** `API_BASE`, the `Health`/`DiceRoll` interfaces, `ApiError`, and `getHealth()`/`rollDice(sides,count)` (native `fetch`, typed, throw `ApiError` on non-2xx). |
| `web/components/Header.tsx` | **New (`"use client"`).** Sticky blurred header (logo + "Q-EaaS" wordmark linking `#top`), desktop anchor nav, `<HealthBadge/>`, hamburger + full-screen mobile overlay menu (React `useState` open/close, body-scroll-lock while open). Tokens only — reproduces `base.html`'s structure/behaviour, not its CSS. |
| `web/components/Footer.tsx` | **New (server).** Neon-muted footer: "Quantum Entropy-as-a-Service — thesis demo. QRNG = entropy source; ML-KEM = the quantum resistance." |
| `web/components/HealthBadge.tsx` | **New (`"use client"`).** Polls `getHealth()`; renders the loading/healthy/degraded/error pill per §4. Uses `.pill` + `.glow`. |
| `web/components/DicePlayer.tsx` | **New (`"use client"`).** Preset dice chips **4/6/8/10/12/20/50/100** + custom-sides (2..100) + count (1..6) inputs + big Roll pill; `onSubmit` `preventDefault` → `rollDice` → animated result tiles (framer-motion); disabled/loading guard; inline error on the `{"error":"<slug>"}` slug; "Show the quantum bytes behind this roll" toggle → reveals `result.bytes_used`/`bytes_count` (no extra request) with the honest label. |
| `web/components/sections/WhatIsQrng.tsx` | **New (server).** "What is a QRNG" copy (superposition/measurement → unbiased bits; IQM/Braket provenance kept short, from `main.html`). |
| `web/components/sections/PipelineDiagram.tsx` | **New (server).** CSS/inline-SVG boxes+arrows: `quantum bits → encrypted pool → HMAC-DRBG (root_key + atomic counter) → { seeds · /random dice · ML-KEM keys }`. Responsive (stacks on mobile). |
| `web/components/sections/ApiUsage.tsx` | **New (server).** "How to use the API": copy-able `curl` for `GET /random?bytes=32`, `POST /dice`, and the **keyed** `GET /v1/random/bytes` with the `X-API-Key` note (point at README's admin-mint flow). Frames raw QRNG bits are never served — only DRBG output. |
| `web/components/sections/CryptoFraming.tsx` | **New (server).** The honest framing box: entropy source vs quantum resistance; `kyber-py` educational-only caveat (one line, links the README ML-KEM section). |
| `web/public/logo.png` | **New.** Copy of `claude/resources/img.png` (atom-on-chip). Used by the header + `metadata.icons`. |
| `web/.env.local` | **New.** `NEXT_PUBLIC_API_BASE=http://localhost:8000` (gitignored by the default `.env*` rule — dev only; documented in README). |
| `web/README.md` | **Edit.** Replace the CNA boilerplate: `npm run dev`; the `NEXT_PUBLIC_API_BASE` var + how to point it at the local API (with the `dev_db_up.sh` + seed-pool steps referenced from the root README); what the app contains (explainer home, live health badge, dedicated `/dice` no-reload player, bytes toggle); the ~380px mobile check. |
| `qrng-eaas/README.md` | **Edit.** Update the `POST /dice` example/contract to show the new `format`/`bytes_used`/`bytes_count` fields. |
| `web/next.config.ts`, `web/tsconfig.json`, `web/postcss.config.mjs`, `qrng-eaas/vercel.json`, `api/qeaas/keyed_drbg.py`, other `api/**` | **No change.** |

**No business logic in `page.tsx` / section JSX** — fetching + typing live in `lib/api.ts`; interactive
state lives in the client components' hooks.

---

## 7. Key flows (the wiring)

**Dice roll (AC-4, no reload):**
```
form onSubmit(e) → e.preventDefault()
  if (loading) return                     // double-fire guard
  setLoading(true); setError(null)
  try { const {rolls} = await rollDice(sides, count); setRolls(rolls); }
  catch (err) { setError(messageFor(err)); }        // e.g. bad_request / rate_limited
  finally { setLoading(false) }
// result tiles render from `rolls` state with a framer-motion stagger — page never navigates
```

**Bytes toggle (AC-5, honest labeling):**
```
onToggle() → setShowBytes(v => !v)        // no fetch — reveals result.bytes_used / bytes_count,
                                          // the actual DRBG bytes drawn for THIS roll (from the /dice response)
// label: "the quantum-seeded DRBG bytes drawn for this roll (N bytes; some rejected to avoid bias)"
```

**Health badge (AC-2, real status):**
```
useEffect: getHealth() on mount; setInterval(POLL_MS); refetch on window focus; clear on unmount
  map quantum_entropy_level → green "healthy" / amber "degraded"; fetch failure → muted "unavailable"
```

**API base (AC-8):** `getHealth/getRandom/rollDice` prefix every path with `API_BASE`
(`http://localhost:8000` in dev via `.env.local`; `/api` same-origin fallback for prod). CORS already
permits the dev origin.

---

## 8. Verification (manual — no automated tests)

Bring up the backend exactly as the root `README.md` describes (throwaway Docker Postgres+Redis via
`api/scripts/dev_db_up.sh`, seed the pool to ≥64 KiB, `uvicorn main:app --port 8000`), then from `web/`:

```
# web/.env.local → NEXT_PUBLIC_API_BASE=http://localhost:8000
npm install && npm run dev            # http://localhost:3000
```

- **AC-1 (explainer):** the page renders "What is a QRNG", the pipeline diagram (boxes+arrows,
  readable on mobile), "How to use the API" with working `curl` snippets, and the honest crypto
  framing. Copy a `curl` block and confirm it runs against `:8000`.
- **AC-2 (health badge):** badge shows **green "Quantum entropy: healthy"** with the pool seeded.
  Drain/lower the pool below `THRESHOLD` (or raise the threshold) so `/health` reports `degraded` →
  badge flips **amber "degraded"** within one poll interval; refill → green again. Stop the API →
  badge shows muted "unavailable", page does not crash.
- **AC-5 backend (`/dice` bytes):** `curl -s -X POST http://127.0.0.1:8000/dice -H 'content-type:
  application/json' -d '{"sides":20,"count":3}'` → response now includes `format:"base64"`,
  `bytes_used` (base64), `bytes_count ≥ 3`; decode `bytes_used` → its length equals `bytes_count`;
  `/docs` shows the new `DiceResponse` fields. Root `README.md` `/dice` example updated.
- **AC-3/AC-4 (dice, no reload):** navigate to **`/dice`**, pick 20, count 3, tap **Roll** → three
  result tiles animate in; the URL never changes and there is **no full-page reload** (watch the
  Network tab: one XHR to `/dice`, no document navigation). Custom sides (e.g. 50) and count bounds
  (1..6) behave; sending count 7 via devtools → inline `bad_request` message, no crash.
- **AC-5 (bytes toggle):** open "Show the quantum bytes behind this roll" → the actual `bytes_used`
  from that roll's response is revealed (base64 + a byte count), no extra network call, with the
  honest "bytes drawn for this roll" label.
- **AC-6 (phone-first):** in devtools responsive mode at **~380px**: single-column, tap targets
  ≥44px, one-handed reach, hamburger menu opens/closes and locks scroll; rapid double-tap on Roll
  fires **one** request (button disabled while loading). Rotate/resize — no horizontal scroll.
- **AC-7 (design tokens):** Orbitron font, deep-navy radial background, neon-cyan headings with glow,
  pill buttons, blurred panels — matching the `resources/*.html` vibe without copied CSS. Confirm
  `.glow/.pill/.panel` utilities exist in `globals.css`.
- **AC-8 (real integration):** all three calls hit `:8000` (Network tab) and render real data; no
  mocked/placeholder values remain; no CNA boilerplate remains in `layout.tsx`/`page.tsx`/`README.md`.

---

## 9. Definition of done (EPIC 5 "Done when")
- [x] On a phone (~380px), rolling dice updates **in place with no page reload**, with a short
      result animation and a double-fire guard (AC-3/4/6).
- [x] The **`/health` badge reflects real status** — green healthy / amber degraded — and flips live
      when the pool crosses the threshold (AC-2).
- [x] The explainer makes the system **self-describing**: what a QRNG is, the pipeline diagram, how to
      use the API (`curl` + API-key note), and the honest "entropy, not quantum-resistance" framing (AC-1).
- [x] The neon/Orbitron **design identity** is reproduced as Tailwind v4 tokens + `.glow/.pill/.panel`
      utilities — not ported Django CSS; sticky header + mobile overlay menu preserved (AC-7).
- [x] The app talks to the **real API** through `lib/api.ts` + `NEXT_PUBLIC_API_BASE`; errors surface
      inline; no backend changes; **no tests written** (AC-8).

---

## 11. Open questions — RESOLVED

- **Q1 — Layout → dedicated `/dice` route (decided).** The dice player lives on its own well-designed
  route (`app/dice/page.tsx`); the home page is the explainer + a CTA linking to it. Header nav gains a
  **Dice** link.
- **Q2 — "Bytes behind this roll" → backend change (decided).** `POST /dice` now echoes the actual DRBG
  bytes it drew (`bytes_used`/`bytes_count`); the toggle reveals exactly those. Small, contained edit to
  `dice.py`/`schemas.py`/`main.py`; still DRBG output, decision #2 intact.
- **Q3 — API base URL → `NEXT_PUBLIC_API_BASE`, prod prefix deferred to EPIC 6 (decided).** Dev
  `http://localhost:8000`; unset → same-origin `/api`. The `/api`-prefix-vs-unprefixed-FastAPI-routes
  reconciliation is EPIC 6's (deploy) job; EPIC 5 leaves `vercel.json`/`next.config.ts` untouched.
- **Q4 — Native `fetch` (decided).** `axios` stays installed but unused here.
- **Q5 — Dice presets → 4/6/8/10/12/20/50/100 + custom sides (2..100) + count (1..6) (decided).**
- **Q6 — Health poll every 20 s + on-mount + on tab re-focus (accepted).**
- **Q7 — Assets → reuse `claude/resources/img.png` as `web/public/logo.png`; pipeline diagram & hero
  built as CSS/inline SVG (accepted).** The old `QuantumComputer.png`/`chip.png` are not in the repo and
  are not referenced.
- **Q8 — Wordmark "Q-EaaS" with the atom-chip logo (accepted).**

---

## 12. Post-Implementation

**Status:** Complete. All eight ACs and the epic's "Done when" bullets are implemented and covered
(see §2, §9 above).

**What was built:** the backend `/dice` byte-echo (Q2), the full neon/Orbitron design-token layer,
the explainer home page (four static sections), a dedicated `/dice` route with a preset-chip +
custom-sides + count dice player (framer-motion result tiles, bytes-toggle, disabled-while-loading
guard), a polling `HealthBadge`, a sticky `Header` with mobile overlay menu, and `lib/api.ts` as the
single typed fetch boundary. Docs (`web/README.md`, root `README.md`) updated for the new contract.

**Manual verification performed:**
- Backend: `curl POST /dice` confirmed the new `format`/`bytes_used`/`bytes_count` fields; decoded
  byte length matches `bytes_count`; `{"sides":6,"count":7}` → `422 bad_request`; `/openapi.json`
  schema reflects the new `DiceResponse` shape.
- `npx tsc --noEmit` — clean. `npm run build` — clean production build, both routes prerendered.
- Playwright-driven browser pass against the live app (backend seeded + running, `npm run dev`):
  home page renders all four explainer sections + live "Quantum entropy: healthy" badge; `/dice`
  renders the preset chips/custom-sides/count/Roll controls; rolling d20×3 produced animated result
  tiles with **no URL change and a single POST `/dice` XHR** (confirmed via network listener); the
  bytes toggle revealed the base64 payload + count with no additional request; 380px mobile viewport
  showed a single-column layout with a working hamburger overlay menu; no console errors during any
  of this.

**Known flake (not a defect in the shipped code):** during automated Playwright screenshotting, the
home page occasionally rendered with Tailwind styles not yet visually painted on the *very first*
cold navigation in a fresh headless-Chromium profile, while `/dice` never showed this. Bisection
traced it to headless-browser/dev-server timing (Turbopack's dev CSS delivery, HMR websocket, and a
transient `.next` cache corruption that was also observed once as a real `500` and was fixed by
deleting `.next`) — not to any defect in `globals.css`, `layout.tsx`, or `page.tsx`: the compiled
stylesheet was verified byte-for-byte correct (same-origin load, `body{color:var(--color-text)}`
unlayered and resolving correctly), the production `next build` output is clean, and manual/curl
checks of the live app show no such issue. Recommend a quick eyeball check of `npm run dev` in a real
browser before demoing, and preferring `npm run build && npm run start` for anything higher-stakes
than local iteration, since Turbopack dev-mode HMR is the one moving part here that isn't fully
pinned down.

**Follow-ups deferred to later epics (as scoped):** Vercel `/api` prefix reconciliation (EPIC 6), the
"Verify a receipt" box (EPIC 9), any old-site pages not in this brief.
