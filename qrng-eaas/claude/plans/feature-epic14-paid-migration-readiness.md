# Feature Plan — EPIC 14: Paid-migration readiness (escape the free tier cheaply)

**Status:** ❄️ **FROZEN / TBD** (developer, 2026-07-21) — do not implement. Kept as a parked
readiness plan; revisit only when free-tier limits actually bite. **Not required by EPIC 13.**
**Owning build plan:** `claude/QRNG_EaaS_BUILD_PLAN.md` (new epic; addresses the only
migration hint in the plan — constraints row 5: "Hosting starts on Vercel free tier … Revisit
if limits bite").
**Domains:** web `https://qeaas.eu`, API `https://api.qeaas.eu`.

> **No automated tests** (project directive). Production code + manual verification only.

---

## 1. Context & goal

**Goal:** when real users arrive and the free tiers (Vercel functions, Neon Postgres, Upstash
Redis) hit their limits, migrating to a **cheap paid** stack should be a **config + DNS
change**, not a rewrite. This epic makes the app portable and writes the runbook — but changes
**no runtime behaviour** and is **purely additive** on top of EPIC 13.

**Split guarantee (why this is a separate epic):** EPIC 13 ships and works entirely on the
current free tier. Everything here — a settings module, a Dockerfile, docs — can be added at
any later date without touching EPIC 13's discovery features. Implementation of EPIC 13 can
hard-stop before this epic with a complete, useful product.

### What already exists — the portability surface (`api/`)
- Env read **raw and scattered**: `qeaas/db.py:17` `os.environ["DATABASE_URL"]`,
  `qeaas/redis_client.py:17` `os.environ["REDIS_URL"]`, `qeaas/pool.py:26`
  `os.environ["MASTER_KEY"]`, `qeaas/auth.py:27` `os.environ["ADMIN_TOKEN"]`, `main.py:43`
  `WEB_ORIGIN`. EPIC 13 adds `PUBLIC_API_URL` / `PUBLIC_WEB_URL` (in `qeaas/urls.py`). **No
  central settings module** — that scatter is the main portability debt.
- DB access is **standard psycopg 3** with parameterised SQL (`qeaas/db.py`) — no Neon-only
  feature. Redis via `redis.Redis.from_url` (`qeaas/redis_client.py`) — standard `redis://`
  protocol, works with any Redis, not just Upstash.
- Served as a Vercel serverless ASGI function (`api/vercel.json` rewrites all to `main.py`,
  10s max duration). ASGI app object is `app` in `main.py` — trivially containerisable.
- `requirements.txt` is pure-Python wheels (`psycopg[binary]`, `redis`, `fastapi`, `uvicorn`,
  `kyber-py`, `pycryptodome`). No vendor SDKs → provider-agnostic already.

### What already exists — web (`web/`)
- Next.js 16 App Router on Vercel. Vercel's free web tier is generous; the **API function** is
  the likely bottleneck, not the web app. API base is referenced via `NEXT_PUBLIC_API_URL`
  (introduced in EPIC 13).

---

## 2. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-1 | New `api/qeaas/settings.py` is the single typed source for every env var (`DATABASE_URL`, `REDIS_URL`, `MASTER_KEY`, `ADMIN_TOKEN`, `WEB_ORIGIN`, `PUBLIC_API_URL`, `PUBLIC_WEB_URL`). All modules import from it; **no** direct `os.environ` reads remain in `qeaas/*` or `main.py`. Missing required vars fail fast with a clear message naming the var. |
| AC-2 | DB portability confirmed & documented: the app runs unchanged against any standard Postgres via `DATABASE_URL` (Neon → Supabase / Railway / Fly / Hetzner), with a `pg_dump`/`pg_restore` cutover runbook. No Neon-specific SQL is used. |
| AC-3 | Redis portability confirmed & documented: `redis_client.py` works against any `redis://` endpoint (Upstash → Railway / Fly / self-host), with a swap note. |
| AC-4 | `api/Dockerfile` (+ `.dockerignore`) builds an image that runs the FastAPI app via `uvicorn main:app` and behaves identically to the Vercel function. Buildable and runnable locally; **not** wired to any host in this epic. |
| AC-5 | Web is host-portable: deployable to Vercel **or** a Node/container host; API base always via `NEXT_PUBLIC_API_URL`. `web/.env.example` documents the vars. |
| AC-6 | `claude/MIGRATION.md` includes a **cost ladder**: cheap paid options for app host + managed Postgres + managed Redis, with rough limits and monthly price, and a recommended target. |
| AC-7 | `claude/MIGRATION.md` includes a **runbook**: provision target, set secrets, export/import data, deploy, DNS cutover for `api.qeaas.eu`, smoke checks, and rollback. |
| AC-8 | **Split invariant:** nothing in this epic is imported or required by EPIC 13 features; EPIC 13 endpoints behave identically before and after this epic. |

---

## 3. Scope

### In scope
- `qeaas/settings.py` and mechanical migration of all env reads to it.
- `api/Dockerfile` + `api/.dockerignore` (build artefact only; no host wiring).
- `web/.env.example` documenting `NEXT_PUBLIC_API_URL` (+ any web env).
- `claude/MIGRATION.md`: cost ladder + runbook.
- README pointer to `MIGRATION.md`.

### Out of scope (deferred / not now)
- **Actually cutting over** to a paid host — this epic is *readiness*, not execution. The
  cutover is run manually from `MIGRATION.md` when limits bite.
- Adding `pydantic-settings` or any new dependency (see Decision 1).
- Provider SDKs, ORMs, connection-pooler swaps beyond changing the URL.
- Autoscaling, multi-region, CI/CD pipeline changes.
- Any change to entropy/DRBG/KEM/receipt/discovery behaviour.

---

## 4. Key decisions

### Decision 1 — plain settings module, no new dependency
`settings.py` is a small module that reads `os.environ` once at import into a frozen
`dataclass` (or module constants), with `_require("VAR")` raising a clear error for missing
required vars and defaults for optional ones. **No `pydantic-settings`** — keeps
`requirements.txt` minimal and pure-wheel, matching the project directive.

### Decision 2 — portability by standards, not adapters
The app already speaks only standard Postgres (psycopg) and standard Redis (`redis://`). No
vendor abstraction layer is added — portability is achieved by *not* using vendor-specific
features and by centralising the connection strings. Migration = change env vars + move data.

### Decision 3 — containerise the API, keep web on Vercel (default)
Vercel's web tier is generous; the serverless **function** (cold starts, invocation limits,
10s cap) is the pinch point. The Dockerfile targets the API so it can move to a cheap
always-on host (Railway/Fly/Render) while the web stays on Vercel free. If web ever needs to
move, its Dockerfile is a follow-up, not this epic.

### Decision 4 — additive ordering preserves the split
Implement in order: (1) `settings.py` + mechanical read-swaps (behaviour-neutral refactor),
(2) Dockerfile, (3) docs. Each step is independently revertible and none touches EPIC 13
feature code paths beyond swapping how an env var is read.

---

## 5. File plan (concrete paths)

### Backend (`api/`)
- **NEW** `api/qeaas/settings.py` — `from __future__ import annotations`, strict hints;
  frozen dataclass `Settings` + a module-level `settings` instance; `_require()` helper.
- **EDIT** `api/qeaas/db.py` — `os.environ["DATABASE_URL"]` → `settings.database_url`.
- **EDIT** `api/qeaas/redis_client.py` — `REDIS_URL` → `settings.redis_url`.
- **EDIT** `api/qeaas/pool.py` — `MASTER_KEY` → `settings.master_key`.
- **EDIT** `api/qeaas/auth.py` — `ADMIN_TOKEN` → `settings.admin_token`.
- **EDIT** `api/qeaas/urls.py` — `PUBLIC_API_URL`/`PUBLIC_WEB_URL` → `settings` (fold in).
- **EDIT** `api/main.py` — `WEB_ORIGIN` → `settings.web_origins` (list).
- **NEW** `api/Dockerfile` — `python:3.12-slim`, `pip install -r requirements.txt`,
  `CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]`.
- **NEW** `api/.dockerignore` — `venv`, `__pycache__`, `.pytest_cache`, `.vercel`, `tests`.

### Web (`web/`)
- **NEW** `web/.env.example` — `NEXT_PUBLIC_API_URL=https://api.qeaas.eu` (+ any others).

### Docs
- **NEW** `qrng-eaas/claude/MIGRATION.md` — cost ladder + runbook (AC-6, AC-7).
- **EDIT** `qrng-eaas/README.md` — "Migrating off the free tier" pointer to `MIGRATION.md`.

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — running service
API + web up locally as in EPIC 13 Phase 0; `GET /health` green.

### Phase 1 — settings module (AC-1; Decisions 1, 4)
Write `settings.py`; swap every `os.environ[...]` in `qeaas/*` and `main.py` to `settings.*`.
Grep to prove no direct `os.environ` reads remain outside `settings.py`. Restart API; confirm
`/health`, an anonymous `/random`, and a keyed `/v1/random/bytes` all still work — behaviour
identical. Unset one required var → server startup / first request fails with the clear
message naming that var.

### Phase 2 — Dockerfile (AC-4; Decision 3)
Write `Dockerfile` + `.dockerignore`. `docker build -t qeaas-api api/` then
`docker run --env-file api/.env -p 8000:8000 qeaas-api`. Confirm `/health` and a keyed call
behave the same as the Vercel path. Note the image is not deployed anywhere yet.

### Phase 3 — web env (AC-5)
Add `web/.env.example`; confirm the web app reads `NEXT_PUBLIC_API_URL` for API links (from
EPIC 13) and builds with it set to `https://api.qeaas.eu`.

### Phase 4 — docs: cost ladder + runbook (AC-6, AC-7)
Write `MIGRATION.md`. Cost ladder table (app host / Postgres / Redis, limits, ~price,
recommended pick). Runbook steps: provision → secrets → `pg_dump` from Neon → `pg_restore` to
target → deploy container → point `api.qeaas.eu` DNS at the new host → smoke-check
(`/health`, keyed call, `/v1/verify`) → rollback = repoint DNS to Vercel.

### Phase 5 — README + "Done when"
Add the README pointer. **Done when:** the API runs identically from the Docker image with all
config supplied by env, no `os.environ` reads live outside `settings.py`, and `MIGRATION.md`
gives a followable cost ladder + cutover runbook — with EPIC 13's endpoints unchanged.

---

## 7. Design decisions carried from the epic / codebase (do not re-litigate)
- Pure-Python wheels only; **no new dependency** for settings (Decision 1).
- No raw SQL; parameterised psycopg stays.
- Strict type hints + `from __future__ import annotations` in new/edited modules.
- No business logic in `main.py` route bodies (this epic only changes how env is read there).
- Honest QRNG framing and the no-raw-bits invariant are untouched.

## 8. Troubleshooting
- **Import-time crash after settings swap** → a required var is unset in the current env; that
  is the intended fail-fast. Provide it or mark it optional in `settings.py`.
- **Docker run can't reach DB/Redis** → free-tier managed endpoints may need SSL / the pooled
  connection string; pass the exact URL Neon/Upstash give and keep `sslmode=require`.
- **CORS breaks after moving API host** → `WEB_ORIGIN` must still list `https://qeaas.eu`; the
  API host moving does not change the browser origin.
- **DNS cutover slow** → lower the `api.qeaas.eu` TTL before the switch; verify with `dig`.

## 9. Post-Implementation
- Keep the Docker image un-deployed until limits actually bite; this epic delivers readiness.
- When cutting over for real, follow `MIGRATION.md` and re-run the EPIC 13 discovery smoke
  checks against the new `api.qeaas.eu` host.

## 11. Open questions (proposed defaults — developer to confirm)
- **Q1 — Preferred paid target?** *Proposed:* **Railway** for lowest-friction (app + managed
  Postgres + Redis in one project, usage-based, cheap to start); Fly.io as the alternative if
  you want global/edge. Cost ladder will list both.
- **Q2 — Add `pydantic-settings`?** *Proposed:* no — plain module keeps deps minimal
  (Decision 1).
- **Q3 — Containerise web too?** *Proposed:* no — keep web on Vercel free; containerise only
  the API (Decision 3). Revisit if Vercel web limits bite.
- **Q4 — Execute the migration in this epic?** *Proposed:* no — readiness only; run the
  cutover from `MIGRATION.md` when limits are actually hit.
