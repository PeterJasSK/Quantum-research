# Q-EaaS web app

Next.js (App Router) + TypeScript + Tailwind v4 frontend for Quantum
Entropy-as-a-Service: an explainer of the QRNG → DRBG → seeds/keys pipeline,
a live `/health` badge, and a dedicated `/dice` route that rolls
quantum-seeded dice with no page reload.

> **Non-standard Next.js.** This uses Next 16.2.10 and Tailwind v4 — see
> `AGENTS.md` and the bundled docs under `node_modules/next/dist/docs/01-app/`
> before assuming pre-16 App Router conventions.

## Local dev

The app talks to the FastAPI backend in `../api`. Bring that up first — see
the root `README.md`'s "Running the API locally against a real (throwaway)
backend" section (`api/scripts/dev_db_up.sh`, seed the pool, `uvicorn
main:app --port 8000`).

Then, from `web/`:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Configuration

`NEXT_PUBLIC_API_BASE` (see `.env.local`) points the app at the API:

- **Dev:** `http://localhost:8000` — the API's CORS already allows
  `http://localhost:3000` by default (`WEB_ORIGIN`).
- **Prod:** left unset, it falls back to the same-origin `/api` prefix. The
  Vercel `rewrites`/routing needed to make that prefix work is EPIC 6's job —
  not touched here.

## What's in the app

- **Home (`/`)** — the explainer: what a QRNG is, the pipeline diagram
  (quantum bits → DRBG → seeds/keys), how to use the API (`curl` examples +
  API-key note), and the honest "entropy, not quantum-resistance" framing.
  A live health badge sits in the sticky header on every page.
- **`/dice`** — a dedicated, generously-laid-out dice player: preset chips
  (4/6/8/10/12/20/50/100) + custom sides (2–100) + count (1–6), a big Roll
  button, animated result tiles, and a "show the quantum bytes behind this
  roll" toggle that reveals the actual DRBG bytes drawn for that roll (no
  extra request — it's already in the `/dice` response).
- All fetches go through `lib/api.ts` (native `fetch`, typed, no `axios`).

## Manual verification (no automated tests)

This project does not use automated tests. Check by hand:

- Desktop and ~380px mobile width (devtools responsive mode): single-column,
  ≥44px tap targets, hamburger menu opens/closes and locks scroll, no
  horizontal scroll.
- Roll dice on `/dice`: result tiles animate in, the URL never changes, and
  the Network tab shows one XHR to `/dice` and no document navigation.
  Rapid double-tap on Roll fires exactly one request.
- The health badge shows green "healthy" with the pool seeded, flips to amber
  "degraded" when the pool drops below the threshold, and shows a muted
  "unavailable" state if the API is stopped.
