# EPIC 5 — Setup & Implementation Status

This doc has two parts: **(1) how to start the whole stack locally** and **(2) what was
implemented for EPIC 5** (web app: explainer + dice, phone-first, no reload).

Feature plan: `qrng-eaas/claude/plans/feature-epic5-web-app.md` (Status: Complete).
Owning epic: `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 5.

---

## 1. How to start everything

Two processes: the FastAPI backend (`qrng-eaas/api`) and the Next.js frontend
(`qrng-eaas/web`). The backend needs a throwaway Postgres + Redis (Docker) and a seeded
entropy pool before it will serve real data.

### 1.1 Prerequisites

- Docker (for disposable Postgres + Redis containers)
- Python 3.11+ with a virtualenv, `pip install -r requirements.txt` (from `api/`)
- Node.js + npm (for `web/`)

### 1.2 Start the backend

From `qrng-eaas/api/`:

```bash
# 1. Bring up disposable Postgres + Redis containers (applies SQL migrations too)
./scripts/dev_db_up.sh
# prints env vars to export — or skip the copy/paste with:
eval "$(./scripts/dev_db_up.sh --print-env)"

# 2. Seed the entropy pool (any 0/1 bits file works for local dev — not measuring
#    quantumness, just exercising the pipeline)
python3 -c "
import random
random.seed(1)
open('/tmp/bits.txt','w').write(''.join(random.choice('01') for _ in range(700000)))
"
python scripts/ingest_bits.py /tmp/bits.txt seed

# 3. Start the API
source venv/bin/activate
uvicorn main:app --port 8000
```

Required env vars (if you didn't use `eval "$(...--print-env)"`):

```bash
export MASTER_KEY="00000000000000000000000000000000000000000000000000000000000000"
export DATABASE_URL="postgresql://postgres:pw@127.0.0.1:55432/qeaas"
export REDIS_URL="redis://127.0.0.1:56379"
export ADMIN_TOKEN="devtoken"
export WEB_ORIGIN="http://localhost:3000"
```

Confirm it's up:

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","quantum_entropy_level":"healthy","pool_bytes_remaining":...}
open http://127.0.0.1:8000/docs   # interactive Swagger UI
```

Tear down when done: `./scripts/dev_db_down.sh` (from `api/`).

### 1.3 Start the frontend

From `qrng-eaas/web/`:

```bash
npm install
npm run dev        # http://localhost:3000
```

`web/.env.local` already points the app at the local API:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

The API's CORS (`WEB_ORIGIN`) already allows `http://localhost:3000` by default, so no
extra config is needed.

Open **http://localhost:3000** for the explainer home page, **http://localhost:3000/dice**
for the dice player.

### 1.4 Useful checks

```bash
# Backend: roll dice, see the new byte-echo fields
curl -s -X POST http://127.0.0.1:8000/dice -H 'content-type: application/json' \
  -d '{"sides":20,"count":3}'
# { "sides":20, "count":3, "rolls":[...], "format":"base64",
#   "bytes_used":"<base64>", "bytes_count":N }

# Frontend build sanity (no dev server needed)
cd web && npx tsc --noEmit && npm run build
```

No automated tests exist in this project by design (see the plan's "No tests" note) —
verification is manual: run the app, hit `/docs`, `curl` the endpoints, and click through
the UI (desktop + ~380px mobile width in devtools responsive mode).

---

## 2. What was implemented (EPIC 5)

**Goal:** a page that explains the whole QRNG → DRBG → seeds/keys system, shows a live
`/health` badge, and lets you play dice with quantum-seeded numbers with no page reload —
phone-first.

### 2.1 Backend change (the only one — Q2)

`POST /dice` now echoes every DRBG byte it drew for the roll (accepted *and* rejected),
so the web dice player's "bytes behind this roll" toggle is literal, not simulated.

| File | Change |
|---|---|
| `api/qeaas/dice.py` | `roll(sides, count)` now returns `tuple[list[int], bytes]` — every drawn byte accumulates into a `bytearray`, returned alongside the rolls. |
| `api/qeaas/schemas.py` | `DiceResponse` gained `format: Literal["base64"]`, `bytes_used: str`, `bytes_count: int`. |
| `api/main.py` | `/dice` handler base64-encodes the drawn bytes into the response. |

Still DRBG output only — raw QRNG bits are never served (decision #2 unchanged).

### 2.2 Frontend (all new/replaced — was a stock `create-next-app` scaffold)

**Design system** — `web/app/globals.css`: Tailwind v4 `@theme` tokens (deep-navy /
neon-cyan palette, Orbitron font var), radial-gradient background, and `@utility
glow / pill / panel` so components inherit the look without any ported Django CSS.

**Layout** — `web/app/layout.tsx`: Orbitron via `next/font/google`, real
`metadata`/`viewport` exports, renders `<Header/>` … `{children}` … `<Footer/>`.

**API boundary** — `web/lib/api.ts`: `API_BASE` (reads `NEXT_PUBLIC_API_BASE`, falls back
to same-origin `/api` for prod), typed `Health`/`DiceRoll` interfaces, `ApiError`, and
native-`fetch` `getHealth()` / `rollDice(sides, count)` helpers. No `axios` used.

**Components** (`web/components/`):
- `Header.tsx` — sticky blurred header, logo + "Q-EaaS" wordmark, desktop nav (Home /
  How it works / API / Dice), `<HealthBadge/>`, hamburger + full-screen mobile overlay
  menu with scroll-lock.
- `Footer.tsx` — static neon-muted footer line.
- `HealthBadge.tsx` — polls `GET /health` every 20s + on mount + on tab refocus; green
  "healthy" / amber "degraded" / muted "unavailable" states.
- `DicePlayer.tsx` — preset chips (4/6/8/10/12/20/50/100) + custom sides (2–100) + count
  (1–6) + big Roll button; `preventDefault` + loading-guard on submit; framer-motion
  staggered result tiles; "show the quantum bytes behind this roll" toggle (reveals
  `bytes_used`/`bytes_count` already in the response — no extra request).

**Explainer sections** (`web/components/sections/`, all server components):
`WhatIsQrng.tsx`, `PipelineDiagram.tsx` (CSS/inline-SVG boxes+arrows, no external image),
`ApiUsage.tsx` (copy-able `curl` snippets for `/random`, `/dice`, keyed
`/v1/random/bytes`), `CryptoFraming.tsx` (the "entropy, not quantum-resistance" framing).

**Pages:**
- `web/app/page.tsx` — home/explainer: hero + CTA to `/dice`, then the four sections
  above under `#overview` / `#pipeline` / `#api` anchors.
- `web/app/dice/page.tsx` — dedicated, generously-laid-out dice route hosting
  `<DicePlayer/>` + a back link.

**Assets/env:** `web/public/logo.png` (copied from `claude/resources/img.png`),
`web/.env.local` (`NEXT_PUBLIC_API_BASE=http://localhost:8000`, dev-only).

**Docs:** `web/README.md` rewritten (setup, config, manual-verification checklist);
root `README.md`'s `/dice` curl example updated to show the new response fields.

### 2.3 Verification performed

- Backend: `curl` confirmed the new `/dice` response shape, byte-length/`bytes_count`
  match, `422` on bad input (`count:7`), `/openapi.json` schema updated.
- `npx tsc --noEmit` and `npm run build` — both clean.
- Browser pass (Playwright-driven): explainer renders all sections, health badge shows
  live "healthy" against the seeded backend, `/dice` roll produces animated tiles with
  **no URL change and a single POST `/dice` request** (no full-page navigation), bytes
  toggle reveals the payload with no extra request, 380px mobile viewport shows a
  single-column layout with a working hamburger overlay menu, no console errors.

### 2.4 Known caveat (not a defect in the shipped code)

During automated headless-browser testing, the home page occasionally showed a delayed
CSS paint on the very first cold load in Turbopack dev mode (a `.next` cache corruption
was also seen once, fixed by deleting `.next`). This traced to dev-server/HMR timing, not
to the app code — the compiled stylesheet was verified correct, and the production
`next build` output is clean. Do a quick eyeball check of `npm run dev` in a real browser
before demoing; prefer `npm run build && npm run start` for anything higher-stakes than
local iteration.

### 2.5 Explicitly out of scope (deferred to later epics, per the plan)

- Vercel `/api` prefix reconciliation → EPIC 6.
- "Verify a receipt" box → EPIC 9.
- Any old-site pages not in this brief (About, Generator, Coin, Charts, Login/etc.).
- Any backend change beyond the `/dice` byte-echo.

Full AC-by-AC coverage table with file:line evidence: see
`qrng-eaas/claude/plans/feature-epic5-web-app.md` §2 and §12.
