# Feature Plan — EPIC 13: Agent-first API integration & indexing maps

**Status:** Complete
**Owning build plan:** `claude/QRNG_EaaS_BUILD_PLAN.md` (new epic; not in the original 0–10 list — plan files already run to epic12).
**Domains (new):** canonical web `https://qeaas.eu`, API `https://api.qeaas.eu`. Old base `https://qrng.peterjas.sk` becomes a legacy alias (see Open Q1).

> **No automated tests** (project directive). Production code + manual verification only.

---

## 1. Context & goal

**Goal:** make Q-EaaS *agent-first discoverable*. An AI agent that lands on `api.qeaas.eu`
(or `qeaas.eu`) can, in effectively one request, find machine-readable instructions
tailored to it, self-integrate, and receive **everything necessary** to call the service:
auth flow, the endpoint catalog, request/response schemas, quotas, the error envelope, and
the provenance model. In parallel, the site must be **correctly indexable** — by classic
crawlers and by LLM crawlers — via up-to-date maps (`sitemap`, `robots`, `llms.txt`) and
discovery documents.

This epic is **Part 1 of 2**. Part 2 (EPIC 14 — paid-migration readiness) is deliberately
split out so that this epic ships and works end-to-end on the current free tier with **no
hard dependency** on Part 2. Nothing here requires the migration work; implementation can
stop cleanly after this plan.

### What already exists — backend integration points (`api/`)
- `api/main.py` — `app = FastAPI(title="Quantum Entropy-as-a-Service")` (main.py:39), **no**
  `description`/`version`/`servers`/`openapi_tags`, no custom OpenAPI. `CORSMiddleware`
  already wired (main.py:45) with origins from `WEB_ORIGIN` env (default
  `http://localhost:3000`), `allow_headers=["*"]`. An entropy header middleware adds
  `X-Quantum-Entropy` (main.py:58).
- Public routes (no key): `GET /health`, `GET /random`, `POST /dice`, `POST /v1/verify`,
  `GET /v1/pubkey`. Premium (key + entropy gate): `GET /v1/random/bytes`, `GET /v1/seed`
  (`include_in_schema=False`), `POST /v1/kem/keypair`, `POST /v1/kem/encapsulate`. Admin
  (`X-Admin-Token`): `/admin/*`.
- `qeaas/auth.py` — `require_api_key(x_api_key: str | None = Header(...))` reads header
  **`X-API-Key`**; `require_admin` reads **`X-Admin-Token`**. Both use raw `Header`, so the
  security scheme is currently **absent from OpenAPI**.
- `qeaas/schemas.py` — Pydantic request/response models for the EPIC 2 endpoints (source of
  truth for JSON Schema).
- `qeaas/ratelimit.py` — per-IP + per-key fixed-window + daily-quota values (source of truth
  for quota numbers we advertise).
- `qeaas/receipts.py` + `GET /v1/pubkey` + `POST /v1/verify` — provenance model to describe.
- Env read raw & scattered: `DATABASE_URL`, `REDIS_URL`, `MASTER_KEY`, `ADMIN_TOKEN`,
  `WEB_ORIGIN`. **No settings module** (centralising is EPIC 14, not here).
- `api/vercel.json` rewrites all traffic to `main.py`, 10s max duration.

### What already exists — web integration points (Next 16.2.10 App Router, React 19, Tailwind v4)
- `web/app/` pages: `page.tsx` (home/explainer), `demo/page.tsx`, `dice/page.tsx`.
- `web/app/robots.ts` — allow `/`, disallow `/api/`, host `https://qrng.peterjas.sk`.
- `web/app/sitemap.ts` — `/`, `/demo`, `/dice`, host `https://qrng.peterjas.sk`.
- **No** `llms.txt`, **no** `.well-known/`. `public/` holds only `logo.png`.
- Design tokens (Orbitron, deep-navy / neon-cyan, `.glow`/`.pill`/`.panel`) established in
  earlier epics — new page reuses them, no new CSS system.

---

## 2. Acceptance criteria

| ID | Criterion | Covered by |
|----|-----------|-----------|
| AC-1 | `GET /.well-known/agent.json` (api.qeaas.eu, no auth, cacheable) returns a JSON manifest: service name/description, honest QRNG framing line, `web_url` + `api_url`, auth model (header `X-API-Key`, how to obtain a key), a capability list, and absolute links to `/openapi.json`, `/v1/agent/tools`, `/v1/agent/manifest`, `/v1/pubkey`, and the web `/llms.txt`. | ✅ `api/main.py:365` route → `api/qeaas/agent.py:337` `well_known_agent()` (links map `agent.py:294`) |
| AC-2 | `GET /.well-known/ai-plugin.json` returns a minimal ChatGPT-plugin-style manifest pointing at the enriched `/openapi.json`. `GET /.well-known/mcp.json` advertises the MCP endpoint (URL, transport, protocol version). | ✅ `api/main.py:371,377` → `api/qeaas/agent.py:361` `ai_plugin()`, `agent.py:381` `well_known_mcp()` |
| AC-3 | `GET /v1/agent/tools` returns machine-readable **tool descriptors** — one entry per callable endpoint with `name`, `description`, `method`, `path`, `auth`, `quota_cost` (where applicable), `input_schema`, `output_schema` (JSON Schema derived from `qeaas/schemas.py`). Ready to register directly in a function-calling / MCP runtime. | ✅ `api/main.py:383` → `api/qeaas/agent.py:414` `tool_descriptors()`; schemas via `model_json_schema()` `agent.py:257` |
| AC-4 | `/openapi.json` is enriched: `description`, `version`, `servers: [https://api.qeaas.eu]`, `openapi_tags` (public / developer / kem / verify / admin), per-route `summary`+`description`, and an `ApiKeyAuth` security scheme (header `X-API-Key`) attached to the premium routes. `/docs` (Swagger) renders it. `/v1/seed` stays hidden. | ✅ `api/main.py:49` `FastAPI(...)` + `OPENAPI_TAGS main.py:41`; per-route tags/summaries; `api/qeaas/auth.py:24` `ApiKeyAuth` `APIKeyHeader`; `/v1/seed include_in_schema=False main.py:144` |
| AC-5 | `GET /v1/agent/manifest` returns one onboarding document with **everything an agent needs**: numbered auth steps, endpoint catalog with copy-paste `curl` examples, quota/rate-limit numbers (read from `ratelimit.py`), the flat error-envelope shape (`{"error":"<slug>"}`), and the provenance/verify summary. `?profile=<http|openai-tools|anthropic-tools|mcp>` returns the quickstart tailored to that agent framework; unknown/absent profile returns the full document. | ✅ `api/main.py:393` → `api/qeaas/agent.py:550` `agent_manifest()`; profile builders `agent.py:487`; quotas from `ratelimit` `agent.py:279` |
| AC-6 | Web serves `GET /llms.txt` (App Router route, `text/plain`): honest one-paragraph framing, what the service does, and links to the API discovery docs + endpoints. `GET /llms-full.txt` returns an expanded variant (full endpoint list + quickstart). | ✅ `web/app/llms.txt/route.ts`, `web/app/llms-full.txt/route.ts` |
| AC-7 | Web page `/agents` (human- and crawler-readable, existing design tokens) presents the same onboarding info: discovery links, how to get a key, tool-spec download link, and one worked example. Linked from the site header/footer. | ✅ `web/app/agents/page.tsx`; header link `web/components/Header.tsx:22`; footer link `web/components/Footer.tsx:6` |
| AC-8 | **Indexing maps — full coverage.** `sitemap.ts` lists every public page (`/`, `/demo`, `/dice`, `/agents`) with `lastModified`/`changeFrequency`/`priority`. `robots.ts` sets `host` + `sitemap` to `https://qeaas.eu`, allows the `/.well-known/` path, and explicitly allows the major AI crawlers: **GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, anthropic-ai, Claude-Web, PerplexityBot, Google-Extended, CCBot, Bytespider, Amazonbot, Applebot-Extended**. | ✅ `web/app/sitemap.ts` (4 pages); `web/app/robots.ts:5` `AI_CRAWLERS` + `/.well-known/` allow + host |
| AC-9 | **Structured data & metadata for indexing.** `metadataBase = https://qeaas.eu`; every page exports Next `metadata` with title/description, canonical URL, and Open Graph + Twitter card. JSON-LD `<script type="application/ld+json">` injected: `WebSite` + `Organization` site-wide, and `SoftwareApplication`/`APIReference` (with `SoftwareApplication.offers` free tier) on `/agents`. A `manifest.webmanifest` (name, icons from `logo.png`, theme colour) is served and linked. | ✅ `web/app/layout.tsx:26` `metadataBase` + `SITE_JSON_LD:10`; `web/components/StructuredData.tsx`; `web/app/agents/page.tsx:27` page JSON-LD; `web/app/manifest.ts` |
| AC-10 | **Full MCP server.** `POST /mcp` (Streamable-HTTP transport, JSON-RPC 2.0) implements the MCP handshake (`initialize` → capabilities, `notifications/initialized`, `ping`), `tools/list` + `tools/call` for every callable endpoint (random/bytes, dice, kem keypair/encapsulate, verify — sourced from the same catalog), `resources/list` + `resources/read` (receipt public key, `llms.txt`, provenance doc), and `prompts/list` + `prompts/get` (at least one "integrate Q-EaaS" prompt). Premium tools require `X-API-Key`; errors use JSON-RPC error objects. Advertised via `/.well-known/mcp.json` (AC-2) and in `agent.json`. | ✅ `api/qeaas/mcp.py:390` `handle()` (initialize/ping/tools/resources/prompts); `api/main.py:403` `POST /mcp`; premium key+quota via `_require_premium mcp.py:96` |
| AC-11 | Base URLs come from env: `PUBLIC_API_URL` (default `http://localhost:8000`) and `PUBLIC_WEB_URL` (default `http://localhost:3000`) on the API; `NEXT_PUBLIC_API_URL` on the web. Every emitted absolute link uses these — no hard-coded `qrng.peterjas.sk`. `WEB_ORIGIN`/CORS includes `https://qeaas.eu`. | ✅ `api/qeaas/urls.py`; `web/lib/urls.ts`; CORS default `api/main.py:57`; no `qrng.peterjas.sk` remains (grep clean) |
| AC-12 | Cross-domain works: `agent.json` / `manifest` fetched from `api.qeaas.eu` return correct absolute cross-links to `qeaas.eu`, and a browser on `qeaas.eu` can fetch the discovery endpoints + `POST /mcp` (CORS passes). | ✅ links built from `urls.web_url()`/`api_url()` `agent.py:294`; CORS `allow_origins` includes qeaas.eu `main.py:57`; `allow_headers=["*"]` passes `X-API-Key` |

---

## 3. Scope

### In scope
- New backend module `qeaas/agent.py`: the single endpoint **catalog** plus payload builders
  for agent.json, ai-plugin.json, tool descriptors, and the onboarding manifest.
- New backend URL helper (`qeaas/urls.py`, minimal) reading `PUBLIC_API_URL` / `PUBLIC_WEB_URL`.
- New discovery routes in `main.py` (thin bodies delegating to `qeaas.agent`).
- OpenAPI enrichment + documented `X-API-Key` security scheme.
- **Full MCP server** (`qeaas/mcp.py` + `POST /mcp`, Streamable-HTTP JSON-RPC 2.0): tools,
  resources, prompts, handshake — plus `/.well-known/mcp.json` discovery.
- Web `/llms.txt`, `/llms-full.txt`, `/agents` page; `sitemap.ts` + `robots.ts` updates.
- **Full indexing surface:** per-page Next `metadata` (canonical, OG, Twitter),
  JSON-LD structured data (`WebSite`/`Organization`/`SoftwareApplication`),
  `manifest.webmanifest`, `metadataBase`.
- Domain/base-URL config (new env vars) and CORS origin update for `qeaas.eu`.
- README "Agent-first integration" section.

### Out of scope (deferred)
- **Central settings module, Dockerfile, provider migration, cost ladder** — all EPIC 14
  (currently **frozen / TBD** — do not start).
- Any change to entropy/DRBG/KEM/receipt *behaviour*. Discovery is read-only description of
  what already exists.
- Auth model changes beyond documenting the existing `X-API-Key` scheme in OpenAPI.
- Automated per-agent auth (OAuth, dynamic key issuance for agents) — keys stay admin-minted.

---

## 4. Key decisions

### Decision 1 — one catalog, many renderings (no drift)
A single Python data structure in `qeaas/agent.py` (list of endpoint descriptors: name,
method, path, auth, tags, quota cost, request/response model class, summary) is the source of
truth. agent.json, `/v1/agent/tools`, `/v1/agent/manifest`, and the web `/llms-full.txt`
content all **derive** from it. No hand-maintained duplicate endpoint lists.

### Decision 2 — schemas come from Pydantic, not by hand
Tool `input_schema`/`output_schema` are produced with `Model.model_json_schema()` on the
existing `qeaas/schemas.py` models, so tool specs can never drift from the real request/
response contract. Endpoints without a body model advertise their query params explicitly in
the catalog entry.

### Decision 3 — discovery lives on the API, thin route bodies
All discovery routes are added to `main.py` but contain no logic: each calls a builder in
`qeaas.agent`. Well-known routes use `include_in_schema=False` (keep OpenAPI clean);
`/v1/agent/*` stay in-schema so agents discover them via OpenAPI too.

### Decision 4 — minimal URL config now, full settings later
`qeaas/urls.py` reads only `PUBLIC_API_URL` / `PUBLIC_WEB_URL` with localhost defaults. This
is intentionally *not* the centralised settings module — that generalisation is EPIC 14. Keep
Part 1 small and additive so the split holds.

### Decision 5 — `?profile=` is the "instructions specific to them" mechanism
The profile parameter selects a rendering of the catalog for a named agent framework:
`http` (raw curl/fetch), `openai-tools` (OpenAI function-calling tool array), `anthropic-tools`
(Anthropic `tools` array), `mcp` (MCP tool-descriptor array). Unknown/absent → full document
with a `note` listing valid profiles. One catalog, four projections.

### Decision 6 — document the API-key scheme via `APIKeyHeader`
Switch `require_api_key` / `require_admin` in `qeaas/auth.py` to
`fastapi.security.APIKeyHeader(name="X-API-Key", auto_error=False)` /
`APIKeyHeader(name="X-Admin-Token", auto_error=False)`. Behaviour is unchanged (still raise
the same `ApiError` slugs), but the scheme now appears in OpenAPI so `/docs` shows the auth
box and agents read the security requirement. Keep the manual `if not key` checks for the
existing error envelope.

### Decision 7 — llms.txt / robots / sitemap follow existing App Router patterns
`/llms.txt` and `/llms-full.txt` are App Router route handlers (`route.ts`, `text/plain`),
mirroring the existing `robots.ts` / `sitemap.ts` metadata routes — not static files. Content
is a static template string (no live cross-fetch) for reliability on the edge.

### Decision 8 — MCP over stateless Streamable HTTP, hand-rolled JSON-RPC (no SSE session store)
The MCP server is implemented in `qeaas/mcp.py` as a **stateless Streamable-HTTP** endpoint
(`POST /mcp`) speaking MCP's JSON-RPC 2.0 directly. Rationale: the API runs as a Vercel
serverless function (stateless, 10s cap) — long-lived SSE sessions and server-side session
stores fight that model. A stateless request/response MCP endpoint (each call carries its own
context; `X-API-Key` passed through per call) is spec-compatible and serverless-safe. **No new
dependency**: JSON-RPC is a thin dict layer over the existing catalog; we do *not* pull the
`mcp` SDK (it assumes a long-running host). `tools/call` dispatches into the same
`qeaas.generation` / `qeaas.dice` / `qeaas.kem` / `qeaas.receipts` functions the REST routes
use — one implementation, two surfaces (REST + MCP). Tool input schemas reuse Decision 2's
`model_json_schema()`. A best-effort `GET /mcp` may return `405`/an SSE hint; the supported
transport is POST. Advertise protocol version and endpoint in `/.well-known/mcp.json`.

### Decision 9 — indexing is first-class, not an afterthought
Search + LLM discoverability is an explicit deliverable (AC-8, AC-9). Set `metadataBase` once
in `web/app/layout.tsx`; every page exports `metadata` (title, description, canonical
`alternates.canonical`, OpenGraph, Twitter). JSON-LD is injected via a small
`components/StructuredData.tsx` server component (raw `<script type="application/ld+json">`),
not a runtime dep. `manifest.webmanifest` via App Router `app/manifest.ts`. All hosts come
from `NEXT_PUBLIC_*` / `metadataBase` — never hard-coded.

---

## 5. File plan (concrete paths)

### Backend (`api/`)
- **NEW** `api/qeaas/agent.py` — `from __future__ import annotations`, strict hints. Defines
  `ENDPOINTS` catalog + builders: `well_known_agent() -> dict`, `ai_plugin() -> dict`,
  `tool_descriptors() -> list[dict]`, `agent_manifest(profile: str | None) -> dict`. Reads
  quota/rate values from `qeaas.ratelimit`, schemas from `qeaas.schemas`, URLs from
  `qeaas.urls`.
- **NEW** `api/qeaas/urls.py` — `api_url()`, `web_url()` reading `PUBLIC_API_URL` /
  `PUBLIC_WEB_URL` (localhost defaults).
- **NEW** `api/qeaas/mcp.py` — `from __future__ import annotations`, strict hints. Stateless
  MCP JSON-RPC handler: `handle(request_body: dict, api_key: str | None) -> dict`. Implements
  `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`,
  `resources/list`, `resources/read`, `prompts/list`, `prompts/get`. Dispatches tool calls to
  existing `qeaas.generation`/`dice`/`kem`/`receipts`; reuses the `ENDPOINTS` catalog +
  `schemas.py`. JSON-RPC error objects for bad method / missing key / bad params.
- **EDIT** `api/main.py` —
  - enrich `FastAPI(...)`: `description`, `version`, `openapi_tags`, `servers`.
  - add routes (thin): `GET /.well-known/agent.json`, `GET /.well-known/ai-plugin.json`,
    `GET /.well-known/mcp.json` (all `include_in_schema=False`), `GET /v1/agent/tools`,
    `GET /v1/agent/manifest`, and `POST /mcp` (+ `GET /mcp` returning `405`/SSE hint).
    `POST /mcp` body delegates to `qeaas.mcp.handle`, reading the optional `X-API-Key` header.
  - extend CORS default origins / `WEB_ORIGIN` handling to include `https://qeaas.eu`.
- **EDIT** `api/qeaas/auth.py` — `APIKeyHeader` scheme for `X-API-Key` / `X-Admin-Token`
  (Decision 6); logic and error slugs unchanged.

### Web (`web/`)
- **NEW** `web/app/llms.txt/route.ts` — `text/plain` short index.
- **NEW** `web/app/llms-full.txt/route.ts` — `text/plain` expanded index.
- **NEW** `web/app/agents/page.tsx` — onboarding page (design tokens; link in header/footer;
  exports `metadata`; renders `StructuredData` with `SoftwareApplication`/`APIReference`).
- **NEW** `web/app/manifest.ts` — `manifest.webmanifest` (name, icons from `logo.png`, theme).
- **NEW** `web/components/StructuredData.tsx` — server component emitting JSON-LD `<script>`.
- **EDIT** `web/app/layout.tsx` — set `metadataBase = https://qeaas.eu`, default OG/Twitter,
  site-wide `WebSite` + `Organization` JSON-LD; ensure `/agents` linked in header/footer.
- **EDIT** `web/app/sitemap.ts` — list `/`, `/demo`, `/dice`, `/agents` with lastmod/priority; host `https://qeaas.eu`.
- **EDIT** `web/app/robots.ts` — host/sitemap `https://qeaas.eu`; allow the full AI-crawler set (AC-8) + `/.well-known/`.
- **EDIT** `web/lib/` API-base config (or `.env`) to use `NEXT_PUBLIC_API_URL` for links shown
  on `/agents` (no hard-coded host).

### Docs
- **EDIT** `qrng-eaas/README.md` — "Agent-first integration" section: discovery URLs, the
  `?profile=` options, how an agent gets a key, one worked `curl`.

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — running service
Bring up API (`uvicorn main:app --port 8000` from `api/`, with `.env` loaded) and web
(`npm run dev` in `web/`). Confirm `GET /health` and the home page render.

### Phase 1 — catalog + URL helper (Decisions 1, 2, 4)
Write `qeaas/urls.py` and `qeaas/agent.py` with the `ENDPOINTS` catalog and the four builders.
Verify in a Python REPL that `tool_descriptors()` emits valid JSON and that schemas come from
`schemas.py` (`model_json_schema()`), quota numbers from `ratelimit.py`.

### Phase 2 — discovery routes + OpenAPI enrichment (AC-1, AC-2, AC-4; Decisions 3, 6)
Add the routes and enrich `FastAPI(...)`; switch auth to `APIKeyHeader`. Verify:
- `curl -s localhost:8000/.well-known/agent.json | jq` — has web/api URLs, capability list,
  cross-links (incl. `mcp` endpoint).
- `curl -s localhost:8000/.well-known/ai-plugin.json | jq` and `/.well-known/mcp.json | jq`.
- `curl -s localhost:8000/openapi.json | jq '.servers, .components.securitySchemes, .tags'`
  — servers, `ApiKeyAuth`, tags present; `/v1/seed` absent from `paths`.
- Open `/docs` — auth box present; premium routes show the lock.

### Phase 3 — tool descriptors + manifest profiles (AC-3, AC-5; Decision 5)
- `curl -s localhost:8000/v1/agent/tools | jq` — one entry per callable endpoint, each with
  input/output JSON Schema.
- `curl -s "localhost:8000/v1/agent/manifest" | jq` — auth steps, catalog, quotas, error
  shape, provenance summary.
- `curl -s "localhost:8000/v1/agent/manifest?profile=openai-tools" | jq` and `?profile=mcp`,
  `?profile=anthropic-tools`, `?profile=http` — each returns the framework-shaped quickstart;
  bogus profile returns full + `note`.

### Phase 4 — full MCP server (AC-10; Decision 8)
Write `qeaas/mcp.py` + `POST /mcp`. Verify with raw JSON-RPC:
- `initialize` → returns `protocolVersion`, `serverInfo`, `capabilities` (tools/resources/prompts).
- `tools/list` → every callable endpoint with `inputSchema`; `tools/call` `dice` (anon) returns
  a roll; `tools/call` `random_bytes` without `X-API-Key` → JSON-RPC error; with a valid key →
  bytes. `resources/list` + `resources/read` return pubkey/llms/provenance. `prompts/list` +
  `prompts/get` return the integrate prompt. Then connect a real MCP client (e.g. Claude
  Desktop / `mcp` inspector) at `POST https://api.qeaas.eu/mcp` and confirm tools appear and
  call through.

### Phase 5 — web maps, agents page, structured data (AC-6, AC-7, AC-8, AC-9)
- `curl -s localhost:3000/llms.txt` and `/llms-full.txt` — `text/plain`, correct links.
- Load `/agents` on mobile viewport — tokens applied, links resolve, header/footer link works.
- `curl -s localhost:3000/robots.txt` — full AI-crawler allowlist, `/.well-known/` allowed,
  host `qeaas.eu`; `curl -s localhost:3000/sitemap.xml` — all four pages listed.
- View page source of `/` and `/agents` — canonical, OG/Twitter tags, and JSON-LD
  (`WebSite`/`Organization`, `SoftwareApplication`) present; validate JSON-LD parses.
- `curl -s localhost:3000/manifest.webmanifest | jq` — name/icons/theme present.

### Phase 6 — cross-domain / base-URL swap (AC-11, AC-12)
Set `PUBLIC_API_URL=https://api.qeaas.eu`, `PUBLIC_WEB_URL=https://qeaas.eu`,
`NEXT_PUBLIC_API_URL=https://api.qeaas.eu`, `WEB_ORIGIN=https://qeaas.eu,...`. Re-fetch
`agent.json` / `manifest` — absolute links now use the real domains. From a browser tab on
the deployed `qeaas.eu`, `fetch('https://api.qeaas.eu/.well-known/agent.json')` succeeds
(CORS passes). Grep the repo for `qrng.peterjas.sk` — no stray hard-codes remain in emitted
output.

### Phase 7 — README + "Done when"
Add the README section. **Done when:** an agent can either (a) fetch `agent.json` → follow to
`/v1/agent/manifest?profile=<its framework>` → obtain a key → call a premium REST endpoint, or
(b) connect an MCP client to `POST /mcp`, list tools, and call one — successfully; and
`llms.txt` + `robots.txt` + `sitemap.xml` + JSON-LD all point at `qeaas.eu` with the full AI-
crawler set allowed.

---

## 7. Design decisions carried from the epic / codebase (do not re-litigate)
- Raw QRNG bits are **never** served or described as servable — discovery docs advertise only
  DRBG-derived bytes/seeds and the KEM demo (Locked decision 2 / framing).
- Flat error envelope `{"error":"<slug>"}` (`qeaas/errors.py`) — manifest documents exactly this.
- No raw SQL; discovery is read-only and touches no DB anyway.
- No business logic in `main.py` route bodies — builders live in `qeaas/agent.py`.
- Strict type hints + `from __future__ import annotations`; pure-Python wheels only — **no new
  deps**: `APIKeyHeader` ships with FastAPI/Starlette, and the MCP server is hand-rolled
  JSON-RPC over the existing catalog (no `mcp` SDK).
- Reuse existing design tokens for `/agents`; do not port old CSS verbatim.

## 8. Troubleshooting
- **Security scheme not showing in `/docs`** → ensure the `APIKeyHeader` instance is used as a
  dependency, not just instantiated; FastAPI only documents schemes reached via `Depends`.
- **CORS failure from qeaas.eu** → `WEB_ORIGIN` must list the exact scheme+host
  (`https://qeaas.eu`), no trailing slash; check `allow_origins` after split.
- **`/llms.txt` returns HTML/404** → App Router route must be `app/llms.txt/route.ts` exporting
  `GET` with `Content-Type: text/plain`; a folder literally named `llms.txt` is correct.
- **Absolute links still show old host** → a value was hard-coded instead of read from
  `qeaas/urls.py` / `NEXT_PUBLIC_API_URL`.
- **`model_json_schema()` errors** → model has an unsupported default; give the field an
  explicit `json_schema_extra` example.
- **MCP client won't connect / no tools** → client must POST JSON-RPC to `/mcp` with
  `Accept: application/json`; confirm `initialize` returns a `protocolVersion` the client
  supports and `capabilities.tools` is present. Premium `tools/call` needs `X-API-Key` in the
  request headers (map it in the client's server config).
- **MCP call times out on Vercel** → keep each `tools/call` within the 10s function cap; the
  transport is stateless request/response, so do not hold SSE streams open.

## 9. Post-Implementation

### What was built
- **Backend:** `qeaas/urls.py` (env base URLs), `qeaas/agent.py` (single `ENDPOINTS`
  catalog + `well_known_agent`/`ai_plugin`/`well_known_mcp`/`tool_descriptors`/
  `agent_manifest` builders; four `?profile=` projections), `qeaas/mcp.py` (stateless
  JSON-RPC 2.0 MCP handler: initialize/ping/tools/resources/prompts). `main.py` enriched
  (`description`/`version`/`servers`/`openapi_tags`, per-route tags+summaries) and 6
  discovery routes + `POST/GET /mcp` added; CORS default now includes `https://qeaas.eu`.
  `auth.py` switched to `APIKeyHeader` (`ApiKeyAuth`/`AdminTokenAuth`), behaviour + slugs
  unchanged.
- **Web:** `llms.txt` + `llms-full.txt` route handlers, `/agents` page, `manifest.ts`,
  `components/StructuredData.tsx`, `lib/urls.ts`; `layout.tsx` (metadataBase + site-wide
  JSON-LD), `sitemap.ts`, `robots.ts` (AI-crawler allowlist), Header/Footer links.
- **Docs:** README §12 "Agent-first integration".

### Verification done
- Catalog builders + MCP handler exercised offline with the project venv: 6 tool
  descriptors emit valid JSON with Pydantic-derived schemas; all four profiles project;
  MCP `initialize`/`ping`/`tools/list`/`resources/{list,read}`/`prompts/{list,get}`
  return correct shapes; error codes verified (`-32601` unknown method, `-32602`
  unknown tool/bad params/bad uri, `-32700` parse); notifications return `None`.
  `grep` confirms no `qrng.peterjas.sk` remains in emitted output.

### Follow-ups / notes for the developer
- **Live end-to-end (`tools/call`, premium REST, `/docs`, `/openapi.json`) not run here** —
  those need a running stack (Neon + Upstash). Verify per §6 Phases 2–4 against the deployed
  API before relying on it.
- **Refinement vs plan:** MCP premium tools validate `X-API-Key` **and** enforce the per-key
  quota + write usage/issue logs (mirroring REST) so MCP cannot bypass anti-abuse — the plan
  left this under-specified. MCP anon tools (random/dice/verify) are **not** IP-rate-limited
  (no client IP in a stateless JSON-RPC call); the pool is still protected by the reseed floor.
- **Web env var:** existing `NEXT_PUBLIC_API_BASE` (runtime fetch base) left untouched; new
  `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WEB_URL` (`lib/urls.ts`) added for absolute display
  links. Set both in Vercel web project env.
- Set API env in prod: `PUBLIC_API_URL=https://api.qeaas.eu`, `PUBLIC_WEB_URL=https://qeaas.eu`,
  `WEB_ORIGIN=https://qeaas.eu` (+ any others).
- No new dependencies added (MCP is hand-rolled; `APIKeyHeader` ships with FastAPI).

- Verify the deployed `https://api.qeaas.eu/.well-known/agent.json` and
  `https://qeaas.eu/llms.txt` resolve over TLS with correct cross-links.
- Confirm Vercel serves the new web routes and the API function still fits the 10s limit
  (discovery is static-ish, trivially fast).
- Leave EPIC 14 (paid-migration readiness) unstarted — this epic must be complete and useful
  on the free tier by itself.

## 11. Open questions — RESOLVED (developer: "all defaults; full MCP server", 2026-07-21)
- **Q1 — Legacy domain.** ✅ Keep `qrng.peterjas.sk` as a **301 alias** to `qeaas.eu`;
  canonical everywhere = `qeaas.eu`.
- **Q2 — `?profile=` values.** ✅ Ship all four: `http`, `openai-tools`, `anthropic-tools`,
  `mcp`.
- **Q3 — `ai-plugin.json`.** ✅ Ship the minimal manifest.
- **Q4 — MCP.** ✅ **CHANGED:** implement a **full MCP server** (`POST /mcp`, Streamable-HTTP
  JSON-RPC: tools + resources + prompts + handshake), not just descriptor JSON — see AC-10 &
  Decision 8.
- **Q5 — Route name.** ✅ `/agents`.

*(EPIC 14 — paid-migration readiness — is **frozen / TBD** per developer; do not start it.)*
