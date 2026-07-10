# Feature Plan — EPIC 6: Persistence & deployment

**Status:** Approved — file-level prep complete; live deployment steps still pending (developer-owned, see §10)
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 6 `[MUST]`
**Interpretation of "step 6":** EPIC 6. EPICS 1–5 are complete (entropy core, public API,
anti-abuse, ML-KEM, web app) and verified locally via Docker Postgres/Redis. Nothing has been
deployed anywhere yet — no Vercel project, no Neon project, no Upstash database exist. This
plan is written as a **full beginner walkthrough**: every step names the exact screen, button,
or command, because the developer has said they don't know much about deployment yet.

---

## 1. Context & goal

Wire the app to real, persistent, external state (Neon Postgres, Upstash Redis) and put both
the web app and the API on a public URL, so the "Done when" of EPIC 6 is met:

> the public URL serves the web app and all endpoints, with state surviving across serverless
> invocations.

Everything built so far only exists on the developer's laptop, talking to disposable Docker
containers that vanish on `scripts/dev_db_down.sh`. This plan replaces those with permanent
free-tier services and gets a real URL you can open on your phone.

### What already exists (integration points)
- `api/main.py` — full FastAPI app, all EPIC 1–4 routes (`/health`, `/random`, `/dice`,
  `/v1/random/bytes`, `/v1/seed`, `/v1/kem/*`, `/v1/verify`, `/admin/*`). Reads
  `DATABASE_URL`, `REDIS_URL`, `MASTER_KEY`, `ADMIN_TOKEN`, `WEB_ORIGIN` from the environment
  (`api/.env.example` documents each).
- `api/sql/001_entropy_core.sql`, `002_api_keys.sql`, `003_usage_log.sql` — the full schema,
  never yet applied to a real Postgres (only to throwaway Docker containers).
- `api/scripts/ingest_bits.py`, `mint_key.py`, `revoke_key.py` — CLI tools that connect via
  `DATABASE_URL`/`REDIS_URL` env vars; they work against **any** reachable Postgres/Redis,
  including a real Neon/Upstash instance, not just the local Docker containers.
- `web/` — Next.js app, reads the API's base URL from `NEXT_PUBLIC_API_BASE`
  (`web/.env.local` currently points it at `http://localhost:8000`).
- `vercel.json` (repo root) — **already present but broken for this app's route shape** (see
  §5 Decision 1). It was written speculatively in EPIC 0 and never exercised against a real
  deploy.
- No Vercel, Neon, or Upstash account/project exists yet for this app (checked: no `.vercel/`
  directory, no Vercel CLI installed locally, `git remote -v` shows only the GitHub repo).

---

## 2. Acceptance criteria (from EPIC 6 "Done when" + story checkboxes, verbatim intent)

| AC | Source |
|----|--------|
| AC-1 | S6.1: Neon (pooled URL) provisioned; schema tables created. |
| AC-2 | S6.1: Upstash Redis provisioned. |
| AC-3 | S6.1: credentials stored as Vercel env vars (never committed to git). |
| AC-4 | S6.2: Next.js + FastAPI both reachable from one public deployment. |
| AC-5 | S6.2: cold-start latency confirmed acceptable; ML-KEM-768 keygen (~tens of ms) stays well inside the 10s serverless timeout. |
| AC-6 | S6.2: every endpoint smoke-tested on the deployed URL, including from a phone. |
| AC-7 | Done when: state (entropy pool, DRBG root key/counter, API keys, usage log) survives across separate serverless invocations — i.e. two requests minutes apart see continuity, not a reset. |

---

## 3. Scope

### In scope
- Creating and configuring the Neon Postgres project, Upstash Redis database, and Vercel
  project(s) — via their web dashboards, with exact click-paths spelled out.
- Applying the existing SQL migrations to the real Neon database.
- Generating **real** production secrets (`MASTER_KEY`, `ADMIN_TOKEN`) — never reusing the
  local dev placeholder values.
- Fixing the routing mismatch in `vercel.json` (§5 Decision 1) so the API is actually reachable
  in production — this is a **required correctness fix**, not a stretch goal, because the
  current file cannot serve any of the app's real routes.
- Seeding a production entropy pool and minting a first production API key.
- A full manual smoke-test pass against the live URL (the literal S6.2 instruction).
- A short "Deployment" section added to `qrng-eaas/README.md` so this isn't a one-time
  tribal-knowledge exercise.

### Out of scope (deferred to their epics)
- Seed-quality report against the deployed API (EPIC 7).
- Networking handshake demo script (EPIC 8).
- Receipts/`/v1/verify` real signing (EPIC 9 — the route already exists as a stub from EPIC 2/4
  and is deployed as-is, unchanged).
- Full EPIC 10 lifecycle beyond what EPIC 1 already pulled forward (pool encryption). No new
  crypto work here.
- Moving off Vercel/Neon/Upstash free tiers (only relevant if a limit is actually hit — noted
  as a risk, not planned for).
- CI/CD pipeline (GitHub Actions, preview-deploy-on-PR). This plan is a **manual, one-time**
  production deploy; Vercel's default "deploy on push to `main`" behavior (enabled automatically
  once the project is linked to the GitHub repo) is all that's set up.

---

## 4. Accounts you will need (create these first, all free)

| Service | URL | What it's for |
|---|---|---|
| GitHub | already have it | Vercel deploys straight from your existing repo. |
| Vercel | vercel.com — "Sign Up", choose "Continue with GitHub" | Hosting for both the web app and the API. |
| Neon | neon.tech — "Sign Up", choose "Continue with GitHub" | Free Postgres database. |
| Upstash | upstash.com — "Sign Up", choose "Continue with GitHub" | Free Redis database. |

Signing up with "Continue with GitHub" on all three avoids creating separate passwords and
makes it obvious which account is "yours" later.

---

## 5. Key decisions (read before doing anything)

### Decision 1 — the existing `vercel.json` cannot work as written; fix it, don't work around it

`api/main.py` defines routes at the **root** of the API (`/health`, `/random`, `/dice`,
`/v1/random/bytes`, …) — there is no `/api` prefix anywhere in the Python code, matching how
they're already exercised locally (`http://127.0.0.1:8000/health`, not `/api/health`).

The repo-root `vercel.json` currently says:
```json
"rewrites": [ { "source": "/api/(.*)", "destination": "/api/main.py" } ]
```
This only forwards requests whose **public** path starts with `/api/...` to the Python
function — and the function then receives that same `/api/...` path, which matches **none**
of `main.py`'s routes (they're registered as `/health`, not `/api/health`). So as written,
literally every API request in production would 404, both `/health` directly (never reaches
the function — Vercel would try to serve it as a static file / Next.js page and 404) and
`/api/health` (reaches the function, but FastAPI has no route for that path).

There's also a genuine **path collision**: the web app has a page at `/dice`
(`web/app/dice/...`) and the API has a route `POST /dice`. A single Vercel project serving
both from the same domain cannot route `GET /dice` (→ the Next.js page) and `POST /dice`
(→ the FastAPI function) differently using plain path-based rewrites — Vercel rewrites match
on path, not HTTP method.

**Resolution — deploy two separate Vercel projects, one domain each:**
- `qeaas-web` — the Next.js app, its own `*.vercel.app` domain.
- `qeaas-api` — the FastAPI app (unmodified route paths), its own `*.vercel.app` domain.

They talk to each other over the network exactly like local dev already does (web →
`NEXT_PUBLIC_API_BASE` → API), just with real URLs instead of `localhost`. This requires
**zero changes to `api/main.py`, `api/qeaas/*`, or any web `fetch()` call** — only
`web/.env.local`'s equivalent (`NEXT_PUBLIC_API_BASE`, set as a Vercel env var instead) and the
API's `WEB_ORIGIN` CORS setting change. It also sidesteps the `/dice` collision entirely, since
each app owns its whole domain.

This is a deliberate, explicit deviation from the build plan's "Next.js + FastAPI in one Vercel
project (Services)" phrasing (Locked decision #1 / S6.2). Vercel's multi-service-per-project
"Services" feature *could* achieve one domain, but it adds a second layer of Vercel-specific
configuration to learn on top of everything else — not a good trade for a first deployment.
Flagged as **Open Question 1** (§11) for explicit sign-off; recommendation is two projects.

The repo-root `vercel.json` becomes redundant if we do this — `web/` and `api/` become their
own Vercel projects with **root directory** set per-project (§7 File Plan covers the exact
file changes).

### Decision 2 — production secrets are generated fresh, never copied from `.env.example`/local dev

The local dev `MASTER_KEY` used in most walkthroughs is a placeholder string of zeros — fine
for throwaway Docker containers, catastrophic if it ends up protecting a real, persistent
entropy pool. §6 Phase 3 generates real random values.

### Decision 3 — where the "256 bits of quantum entropy" for the production pool comes from

The build plan's real intent is to ingest actual IBM QRNG output (the `*_processed.txt` files
already in the repo under `ErrorDetectionVSRawBits/`, once converted to the plain `0`/`1`
contract `parse_bits_file` expects — **not** the legacy `bits:`-prefixed format). This plan
seeds the production pool with an initial batch of that real data (§6 Phase 6) rather than the
`random.seed(1)` placeholder used in local dev. Converting one processed file to the plain
contract is a two-line script, included in §6 Phase 6.

---

## 6. Step-by-step deployment guide

Work through these phases in order. Each command is meant to be copy-pasted as-is.

### Phase 0 — install the Vercel CLI (optional but recommended)

The dashboard alone is enough, but the CLI makes env vars and redeploys much less clicky.

```bash
npm install -g vercel
vercel --version   # confirms it installed
vercel login       # opens a browser, log in with the same GitHub account
```

If you'd rather stay in the browser the whole time, skip this — every step below has a
dashboard equivalent, called out explicitly.

### Phase 1 — provision Neon Postgres

1. Go to https://console.neon.tech → **New Project**.
2. Name it `qeaas` (or anything), pick any nearby region, Postgres version default (16+) is
   fine. Click **Create Project**.
3. On the project's **Dashboard** tab, find the **Connection string** box. There's a toggle
   for **Pooled connection** — turn it **on** (the build plan requires the pooled string
   because serverless functions open a fresh connection per invocation; the pooled endpoint
   uses PgBouncer under the hood so this doesn't exhaust Postgres's connection limit).
4. Copy the full string. It looks like:
   ```
   postgresql://<user>:<password>@<host>-pooler.<region>.aws.neon.tech/qeaas?sslmode=require
   ```
   Save it somewhere temporary (a scratch note) — this is your production `DATABASE_URL`.
5. Apply the schema using Neon's dashboard **SQL Editor** tab (no `psql` needed — confirmed
   you don't have it installed, so this is the path to use, not a fallback):
   - Open `qrng-eaas/api/sql/001_entropy_core.sql` locally, copy its full contents, paste into
     the SQL Editor, click **Run**.
   - Repeat for `002_api_keys.sql`, then `003_usage_log.sql` — **in that numeric order** (002/003
     don't strictly depend on 001's data, but keep the order to match the migration history).
   - Each run should show a success result (`CREATE TABLE` and no red error banner).
6. Sanity check, still in the SQL Editor:
   ```sql
   select table_name from information_schema.tables where table_schema = 'public';
   ```
   You should see `entropy_pool`, `drbg_root`, `api_keys`, `usage_log`.

### Phase 2 — provision Upstash Redis

1. Go to https://console.upstash.com → **Create Database**.
2. Name it `qeaas`, type **Regional** (not Global — you don't need multi-region for this),
   pick a region close to where you'll set Vercel's functions (doesn't have to be exact).
   Free tier ("Pay as you go" with the free monthly quota) is enough.
3. On the database's page, find **REST API** vs **Redis** connection details — you want the
   **Redis** (TCP) connection string, not the REST URL. It's labeled something like
   `UPSTASH_REDIS_URL` or just shown as a `rediss://...` string under "Connect" → look for the
   `redis-cli` / `ioredis` / generic Redis client tab. It looks like:
   ```
   rediss://default:<password>@<host>.upstash.io:<port>
   ```
   (`rediss://` — with two `s` — means TLS; the app's `redis_client.py` should be given exactly
   this, unmodified.) Save it as your production `REDIS_URL`.
4. No schema step for Redis — the app creates keys (`drbg:counter`, `rl:ip:*`, `quota:key:*`)
   on first use.

### Phase 3 — generate real production secrets

Run these locally — do **not** reuse the local-dev values from `api/.env.example`.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"   # -> MASTER_KEY (64 hex chars = 256 bits)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # -> ADMIN_TOKEN
```

Save both somewhere safe (a password manager, not a file you'll commit). You'll paste them
into Vercel's env var UI in Phase 4 and never need them in plaintext again after that, except
once in Phase 6 to call the admin endpoints.

### Phase 4 — create the two Vercel projects

**4a. API project (`qeaas-api`)**

Dashboard path: https://vercel.com/new → pick your GitHub account → find and **Import** the
`Quantum-research` repo.

- **Root Directory**: click **Edit** next to it, choose `qrng-eaas/api`.
- **Framework Preset**: Vercel should offer "Other" — that's correct, this isn't a JS
  framework. If it insists on a framework, pick "Other"/"No Framework".
- Vercel auto-detects `requirements.txt` in that root and builds it as a Python serverless
  function using the runtime declared for `api/main.py` — but since we're setting **Root
  Directory** to `qrng-eaas/api`, the function file is now just `main.py` relative to that
  root. You need a `vercel.json` **inside `qrng-eaas/api/`** (new file, not the repo-root one)
  telling Vercel that `main.py` is the entrypoint for every path — see §7 File Plan for its
  exact contents. Add that file (§7) **before** clicking Deploy, or the first deploy will fail
  to find the function.
- **Environment Variables** — add these four (paste the real values from Phases 1–3):
  | Key | Value |
  |---|---|
  | `DATABASE_URL` | the Neon pooled connection string |
  | `REDIS_URL` | the Upstash `rediss://` string |
  | `MASTER_KEY` | the hex string from Phase 3 |
  | `ADMIN_TOKEN` | the token from Phase 3 |
  | `WEB_ORIGIN` | leave as `http://localhost:3000` for now — you'll update it in 4b once the web project's real URL exists |
- Click **Deploy**. Watch the build log. Expected outcome: a green checkmark and a URL like
  `https://qeaas-api-<random>.vercel.app`. Copy that URL — this is your production API base.

**If the build fails**, the most likely cause is a native-wheel problem with `pycryptodome`
(flagged as an open risk back in the EPIC 1 plan — this was never actually verified on
Vercel's runtime). Read the build log for a line mentioning `pycryptodome` or a compilation
error. If that's it, see §9 Troubleshooting.

**4b. Web project (`qeaas-web`)**

Same **Import** flow, same GitHub repo, second time:

- **Root Directory**: `qrng-eaas/web`.
- **Framework Preset**: Vercel should auto-detect **Next.js** here — leave it.
- **Environment Variables**:
  | Key | Value |
  |---|---|
  | `NEXT_PUBLIC_API_BASE` | the API URL you copied in 4a, e.g. `https://qeaas-api-<random>.vercel.app` |
- Click **Deploy**. Expected outcome: a URL like `https://qeaas-web-<random>.vercel.app`.

**4c. Close the loop — CORS**

Go back to the **`qeaas-api`** project → **Settings** → **Environment Variables** → edit
`WEB_ORIGIN` → set it to the exact web URL from 4b (e.g.
`https://qeaas-web-<random>.vercel.app`, no trailing slash). Saving an env var change doesn't
auto-redeploy — go to the **Deployments** tab and **Redeploy** the latest deployment (checkbox
"Use existing Build Cache" is fine) so the new `WEB_ORIGIN` takes effect.

### Phase 5 — confirm the API is actually reachable

```bash
curl -s https://qeaas-api-<random>.vercel.app/health
```
Expect `{"status":"ok","quantum_entropy_level":"degraded", ...}` — `degraded` is correct and
expected right now, because the production pool is still empty (Phase 6 fixes that). If this
404s or times out, stop and work through §9 before continuing — nothing past this point will
work until `/health` responds.

### Phase 6 — seed the production entropy pool

Two real IBM QRNG batches were chosen for this (Q2, resolved):
- `ErrorDetectionVSRawBits/qrng_output/FEZ/noise_ibm_fez_20260707-135456_processed.txt` (~10.5 MB of `0`/`1` text ≈ 1.3M bits ≈ 164 KB)
- `ErrorDetectionVSRawBits/qrng_output/MARRAKESH/noise_ibm_marrakesh_20260707-173420_processed.txt` (~9.0 MB of `0`/`1` text ≈ 1.1M bits ≈ 141 KB)

Both use the legacy `bits:`-prefixed format (confirmed by inspection — each file starts with
literal `bits:` followed by `0`/`1` characters), so both need the same conversion
`parse_bits_file` expects: strip the `bits:` prefix and drop any non-`0`/`1` characters.
Ingest them as **two separate admin calls** (not concatenated) — each keeps its own
`source_label` and `uploaded_at` row in `entropy_pool`, which is more honest provenance than
merging two IBM device runs into one anonymous blob, and gives ~300 KB of real pool headroom
either way (comfortably above the 64 KiB `degraded` threshold on its own from either file).

Convert both to the plain contract:

```bash
cd /home/peter/PycharmProjects/Quantum-research
python3 -c "
import re
files = {
    'fez': 'ErrorDetectionVSRawBits/qrng_output/FEZ/noise_ibm_fez_20260707-135456_processed.txt',
    'marrakesh': 'ErrorDetectionVSRawBits/qrng_output/MARRAKESH/noise_ibm_marrakesh_20260707-173420_processed.txt',
}
for label, src in files.items():
    raw = open(src).read()
    bits = re.sub(r'[^01]', '', raw.split('bits:', 1)[-1] if 'bits:' in raw else raw)
    out = f'/tmp/prod_bits_{label}.txt'
    open(out, 'w').write(bits)
    print(label, len(bits), 'bits ->', len(bits)//8, 'bytes ->', out)
"
```

Ingest both against the **production** Neon/Redis via the deployed admin endpoint (simpler
than running `ingest_bits.py` locally, since that would need production `DATABASE_URL`/
`MASTER_KEY` on your laptop — the HTTP route needs only the `ADMIN_TOKEN`):

```bash
curl -s -X POST https://qeaas-api-<random>.vercel.app/admin/ingest \
  -H "X-Admin-Token: <the ADMIN_TOKEN from Phase 3>" \
  -F "file=@/tmp/prod_bits_fez.txt"

curl -s -X POST https://qeaas-api-<random>.vercel.app/admin/ingest \
  -H "X-Admin-Token: <the ADMIN_TOKEN from Phase 3>" \
  -F "file=@/tmp/prod_bits_marrakesh.txt"
```

Then re-check health:
```bash
curl -s https://qeaas-api-<random>.vercel.app/health
# quantum_entropy_level should now read "healthy"; pool_bytes_remaining should be roughly
# the sum of both converted byte counts printed above
```

### Phase 7 — mint a production API key and exercise the keyed routes

```bash
curl -s -X POST https://qeaas-api-<random>.vercel.app/admin/keys \
  -H "X-Admin-Token: <ADMIN_TOKEN>" \
  -H 'content-type: application/json' \
  -d '{"owner":"prod-smoke-test","tier":"default"}'
# copy the plaintext key from the response — shown once, never again
```

### Phase 8 — full smoke test (AC-6 — do this from your phone too, not just curl)

Open `https://qeaas-web-<random>.vercel.app` on your phone's browser first — confirm the
explainer page loads, the health badge shows green/"healthy", and `/dice` rolls without a page
reload. Then run the same endpoint sweep from the local README's "Confirm it's actually
working" section against the **production** URL instead of `127.0.0.1:8000`:

```bash
API=https://qeaas-api-<random>.vercel.app
KEY=<key from Phase 7>

curl -s "$API/health"
curl -s "$API/random?bytes=32"
curl -s -X POST "$API/dice" -H 'content-type: application/json' -d '{"sides":6,"count":2}'
curl -s -H "X-API-Key: $KEY" "$API/v1/random/bytes?size=64&format=hex"
curl -s -H "X-API-Key: $KEY" "$API/v1/seed?bytes=64"
curl -s -X POST "$API/v1/kem/keypair" -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{}'
curl -s -X POST "$API/v1/verify" -H 'content-type: application/json' -d '{"request_id":"abc"}'
```

Every call should return the same shapes documented in `qrng-eaas/README.md`'s local smoke
test — no `500`s. A `503 {"error":"low_quantum_entropy"}` on the keyed routes means Phase 6
didn't actually raise the pool above threshold; recheck `/health`.

### Phase 9 — confirm state survives across invocations (AC-7)

Serverless functions are torn down between requests — this is the one thing local dev (a
single long-running `uvicorn` process) can't prove by itself. Confirm continuity on the real
deployment:

```bash
curl -s "$API/health" | python3 -c "import json,sys; print(json.load(sys.stdin)['pool_bytes_remaining'])"
# wait a minute, hit /v1/random/bytes a few times to force output, then:
curl -s "$API/health" | python3 -c "import json,sys; print(json.load(sys.stdin)['pool_bytes_remaining'])"
```
The second number should be less than or equal to the first (it only drops on a reseed, not on
every request — see the EPIC 1 plan's drain-budget table — so don't expect it to move on every
single call, just confirm it never resets upward, which would mean state isn't persisting).
Also confirm `drbg_reseeds` in the `/health` body is a small positive integer, not `0` forever
and not reset to `0` between two calls minutes apart.

---

## 7. File plan (concrete paths)

| File | Change |
|------|--------|
| `qrng-eaas/api/vercel.json` | **New.** Per-project config for the `qeaas-api` Vercel project (root directory `qrng-eaas/api`). Rewrites every path to `main.py` so the deployed FastAPI app sees the exact same route paths it already defines (`/health`, `/dice`, `/v1/*`, `/admin/*`) — no code changes to `main.py` needed. Contents: `{"rewrites": [{"source": "/(.*)", "destination": "/main.py"}]}` plus the `functions` block pinning the Python runtime (copy the `"runtime": "python3.13"` block from the current repo-root `vercel.json`, path updated to `main.py`). |
| `qrng-eaas/web/vercel.json` | **New, optional.** Only needed if Next.js defaults need overriding; likely unnecessary since Framework Preset auto-detection handles a standard `next build`. Add only if Phase 4b's deploy needs it (leave out unless the build fails without it). |
| `vercel.json` (repo root) | **Delete.** Superseded by the two per-project files above (Decision 1) — it targets a monorepo-in-one-project layout this plan explicitly moves away from, and leaving it in place is misleading for the next person reading the repo. |
| `qrng-eaas/README.md` | **Edit.** Add a "## Deployment (EPIC 6)" section: the two Vercel project URLs (once known), the env var table per project, and a condensed version of §6 Phases 5–9 (the parts worth keeping as a runbook — provisioning steps are one-time and don't need to live in the README). |
| `qrng-eaas/api/.env.example` | **Edit.** Add a comment above `MASTER_KEY`/`ADMIN_TOKEN` noting production values are generated fresh (Decision 2) and must never match this file's placeholders. |
| `qrng-eaas/web/.env.local` | **Unchanged.** Stays pointed at `http://localhost:8000` for local dev; production `NEXT_PUBLIC_API_BASE` lives only in Vercel's env var UI (per-environment, never committed). |

No changes to `api/main.py`, `api/qeaas/*`, `api/sql/*`, or any `web/app/**` component —
this epic is infrastructure wiring, not application code.

---

## 8. Design decisions carried from the epic (do not re-litigate)
- Free tier first (Vercel + Neon + Upstash); revisit only if a real limit is hit (build plan
  risk list already calls this out — Render/Fly as the fallback, not planned here).
- Neon **pooled** connection string, one connection opened and closed per invocation — no
  connection-pool object held across invocations (already how `api/qeaas/db.py` is written).
- `MASTER_KEY` lives only in Vercel's env var store, never in Neon next to the ciphertext it
  protects (EPIC 10 invariant, unchanged by this plan).

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| API build fails mentioning `pycryptodome` or a compiler error | Native wheel isn't available for Vercel's Python 3.13 runtime (flagged as an open risk since EPIC 1) | Try pinning to the latest `pycryptodome` release compatible with 3.13; if it still fails, swap to the `cryptography` package for AES-256-GCM in `api/qeaas/pool.py` (small, contained change — re-plan as its own ticket if it comes to this, don't improvise it mid-deploy) |
| `curl .../health` after Phase 4a returns Vercel's default 404 page | The per-project `qrng-eaas/api/vercel.json` (§7) is missing or wasn't committed before the first deploy | Add the file, commit, push — Vercel auto-redeploys on push to `main` |
| Web app loads but every `fetch()` call fails with a CORS error in the browser console | `WEB_ORIGIN` on the API project doesn't exactly match the web project's URL (scheme, no trailing slash) | Fix the env var, redeploy the API project (Phase 4c) |
| `/admin/ingest` or `/admin/keys` return `401` | Wrong or missing `X-Admin-Token` header, or the value doesn't match what's set in Vercel | Recheck the exact value saved in Phase 3 / Vercel's env var UI (values are write-only after saving — regenerate and re-save if unsure, then redeploy) |
| Nothing pasted into the SQL Editor happens / red error banner | Usually a partial paste (missed the trailing `;`) or running 002/003 before 001 exists | Re-copy the full file contents, confirm 001 ran and created tables (§6 Phase 1 step 6) before running 002/003 |
| Redeploying doesn't seem to pick up a changed env var | Vercel only applies env var changes to **new** deployments | Trigger a redeploy from the **Deployments** tab (or push any commit) after every env var change |

---

## 10. Post-Implementation

**What an agent could and couldn't do:** all the account/dashboard steps in §6 (Vercel CLI
login, Neon project + SQL Editor, Upstash project, Vercel project imports, live `curl` against
a deployed URL) require a human browser session and account credentials that an automation
agent does not have. Those steps (Phases 0–5, 7–9) are **not done** — they're still yours to
run by hand, following §6 (or the condensed runbook now in `qrng-eaas/README.md` §Deployment).

**What was actually implemented (file-level prep, §7):**
- `qrng-eaas/api/vercel.json` — **created**. Pins `main.py` to the Python 3.13 runtime and
  rewrites every path to it, so the deployed function sees the same bare route paths
  (`/health`, `/dice`, `/v1/*`, `/admin/*`) `main.py` already defines locally — zero code
  changes needed.
- **Path correction vs. the plan:** §7's file-plan table named a nonexistent repo-root
  `vercel.json` for deletion. The file that actually existed and matched Decision 1's
  description was `qrng-eaas/vercel.json` (the qrng-eaas subproject root, one level below the
  git repo root) — its `buildCommand`/`rewrites` matched the plan's description exactly, just
  at the wrong documented path. That file was deleted instead; substance of Decision 1 is
  unaffected, only the path in §7 was wrong.
- `qrng-eaas/web/vercel.json` — **not created**, per the plan's own "leave out unless the build
  fails without it" guidance (Framework Preset auto-detection should handle a standard
  `next build`; nobody has actually run this deploy yet to confirm).
- `qrng-eaas/api/.env.example` — **edited**. Added production-secret-generation notes above
  `MASTER_KEY` and `ADMIN_TOKEN` (Decision 2).
- `qrng-eaas/README.md` — **edited**. Added a "## Deployment (EPIC 6)" section: per-project
  root directories, env var tables, one-time provisioning steps, a condensed verify/seed
  runbook, and the troubleshooting table from §9.
- Phase 6 bit conversion — **run locally**. Converted both `bits:`-prefixed processed files to
  the plain `0`/`1` contract: `/tmp/prod_bits_fez.txt` (10,540,000 bits → 1,317,500 bytes) and
  `/tmp/prod_bits_marrakesh.txt` (9,040,000 bits → 1,130,000 bytes). **Note:** §6 Phase 6's
  size estimate ("~1.3M bits ≈ 164 KB" per file) undercounted by ~8x — the real per-file bit
  counts match the files' full character length (~10.5M / ~9.0M bits, i.e. ~1.3 MB / ~1.1 MB
  once packed to bytes), not 1.3M bits. Harmless (more pool headroom than planned, well above
  the 64 KiB `degraded` threshold either way), but the plan's arithmetic there was wrong.
- These `/tmp/prod_bits_*.txt` files are ephemeral scratch output, not committed — they'll need
  regenerating (same script, §6 Phase 6 or the README runbook) once you're ready to actually
  ingest them against a live `qeaas-api` deployment.

**Everything else in §6 (Phases 0–5, 7–9) and all 7 ACs in §2 remain open** — none of them can
be verified true until the real Neon/Upstash/Vercel resources exist and are deployed. Follow
`qrng-eaas/README.md`'s new "Deployment (EPIC 6)" section, or §6 of this plan directly, to
finish the rollout, then come back and tick §2's AC table with real evidence (e.g. the actual
`curl` output, the actual Vercel project URLs).

---

## 11. Open questions — RESOLVED

**Q1 — Two Vercel projects vs. one project using Vercel "Services"? → RESOLVED: two projects.**
`qeaas-api` and `qeaas-web`, each its own domain, per §5 Decision 1 / §6 Phase 4.

**Q2 — Which real QRNG file(s) to seed the production pool with? → RESOLVED: both.**
`ErrorDetectionVSRawBits/qrng_output/FEZ/noise_ibm_fez_20260707-135456_processed.txt` and
`ErrorDetectionVSRawBits/qrng_output/MARRAKESH/noise_ibm_marrakesh_20260707-173420_processed.txt`,
ingested as two separate `/admin/ingest` calls (§6 Phase 6) so each keeps its own provenance
row rather than being merged into one blob.

**Q3 — Keep the repo-root `vercel.json` around or delete it? → RESOLVED: delete.**
Per §7 File Plan — superseded by the two per-project `vercel.json` files.

**Q4 — Is `psql` available, or lean on Neon's web SQL Editor? → RESOLVED: no `psql`, use the
SQL Editor.** §6 Phase 1 step 5 now names the SQL Editor as the only path, not a fallback.
