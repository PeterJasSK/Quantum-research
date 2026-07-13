# Quantum Entropy-as-a-Service (Q-EaaS)

Monorepo: `/web` (Next.js App Router + Tailwind), `/api` (FastAPI), `/shared` (docs, diagrams, spikes).
See `claude/QRNG_EaaS_BUILD_PLAN.md` for the full epic plan.

## Local dev

**API** (from `api/`):

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000 --env-file .env
```

That starts the app, but every route touches Postgres (`DATABASE_URL`) and most touch Redis
(`REDIS_URL`) — without real values in `.env` every request 500s. See the next section for a
throwaway local backend.

**Web** (from `web/`):

```
npm install
npm run dev
```

## Running the API locally against a real (throwaway) backend

The app needs a real Postgres (root key + entropy pool + API keys) and Redis (DRBG output
counter). If you don't have Neon/Upstash dev credentials, spin up disposable containers with
Docker — this is exactly how EPIC 2 was verified.

### 1. Start Postgres + Redis (one command)

From `api/`:

```bash
./scripts/dev_db_up.sh
```

This starts two disposable containers (`qeaas-pg`, `qeaas-redis`, both `--rm` so they vanish
on stop), waits for Postgres to actually be ready, and applies all SQL migrations. It prints
the env vars to export.

To skip the copy/paste, export them straight into your shell instead:

```bash
eval "$(./scripts/dev_db_up.sh --print-env)"
```

Running it again while the containers are still up will refuse (it tells you to run
`dev_db_down.sh` first) rather than silently reusing/duplicating them.

### 2. Configure the environment

If you used `eval "$(...--print-env)"` above, skip this — it's already exported. Otherwise
copy the block the plain `dev_db_up.sh` run printed, or put it in `api/.env` and pass
`--env-file .env` to uvicorn.

### 3. Seed the entropy pool

The DRBG root key bootstraps itself from the pool on first use, and `/health` reports
`quantum_entropy_level: "degraded"` below 64 KiB of pool bytes (gated routes 503 until then).
Feed it a `0`/`1` bits file:

```bash
python3 -c "
import random
random.seed(1)
open('/tmp/bits.txt','w').write(''.join(random.choice('01') for _ in range(700000)))
"
python scripts/ingest_bits.py /tmp/bits.txt seed
```

(Real deployments ingest actual QRNG output; for local testing any `0/1` text works — it's
only exercising the pipeline, not measuring quantumness.)

### 4. Mint a dev API key

`/v1/random/bytes` and `/v1/seed` require `X-API-Key`. Mint one with the CLI, which prints
the plaintext key once:

```bash
python -m scripts.mint_key --owner devtest --tier default
# api key for 'devtest' (tier=default): <plaintext key>  <-- copy this
```

Or via the HTTP admin route (`X-Admin-Token` from step 2, `devtoken` for the throwaway
backend):

```bash
curl -s -X POST http://127.0.0.1:8000/admin/keys -H "X-Admin-Token: devtoken" \
  -H 'content-type: application/json' -d '{"owner":"devtest","tier":"default"}'
```

### 5. Start the app

```bash
uvicorn main:app --port 8000
```

### 6. Confirm it's actually working

```bash
curl -s http://127.0.0.1:8000/health          # {"status":"ok","quantum_entropy_level":"healthy",...}
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/openapi.json   # 200
open http://127.0.0.1:8000/docs               # interactive Swagger UI, every route typed
```

Then exercise the actual routes (replace `<key>` with the value from step 4):

```bash
# public, ungated
curl -s "http://127.0.0.1:8000/random?bytes=32"
curl -s -X POST http://127.0.0.1:8000/dice -H 'content-type: application/json' \
  -d '{"sides":6,"count":2}'
# { "sides":6, "count":2, "rolls":[3,6], "format":"base64",
#   "bytes_used":"<base64>", "bytes_count":2 }
# bytes_used/bytes_count (EPIC 5 Q2) are every DRBG byte drawn for the roll,
# accepted and rejected -- the honest provenance behind the toggle in /dice on
# the web app. Still DRBG output, never raw QRNG bits (decision #2).

# key-gated (canonical dev endpoint + alias)
curl -s -H "X-API-Key: <key>" "http://127.0.0.1:8000/v1/random/bytes?size=64&format=hex"
curl -s -H "X-API-Key: <key>" "http://127.0.0.1:8000/v1/seed?bytes=64"

# provenance: verify a signed receipt (paste one from a /v1/random/bytes response above)
curl -s -X POST http://127.0.0.1:8000/v1/verify -H 'content-type: application/json' \
  -d '{"receipt":"<receipt from a keyed issue response>"}'
curl -s http://127.0.0.1:8000/v1/pubkey

# admin-only pool refill
echo -n "01010101" > /tmp/small.txt
curl -s -X POST http://127.0.0.1:8000/admin/ingest -H "X-Admin-Token: devtoken" \
  -F "file=@/tmp/small.txt"
```

Edge cases worth checking (each should return the flat `{"error": "<slug>"}` body):

| Request | Expected |
|---|---|
| `/random?bytes=65` | `422` |
| `/dice {"sides":6,"count":7}` | `422` |
| `/v1/random/bytes` with no `X-API-Key` | `401 missing_api_key` |
| `/v1/random/bytes` with a revoked key | `401 invalid_api_key` |
| `/admin/ingest` with wrong `X-Admin-Token` | `401` |
| `/admin/ingest` with a file > 10 MB | `413` |
| pool below 64 KiB (skip step 3, or don't seed enough) | `/v1/random/bytes`, `/v1/seed` → `503` |
| `/random` hammered past 60 req/min from one IP | `429 rate_limited` |
| `/v1/random/bytes` past a key's daily quota | `429 quota_exceeded` |
| `/admin/keys/revoke` with an unknown `key_hash` | `404 not_found` |

Every `429` carries a `Retry-After` header (seconds).

To revoke the test key and confirm the `401`:

```bash
python -m scripts.revoke_key --owner devtest
# or: curl -s -X POST http://127.0.0.1:8000/admin/keys/revoke -H "X-Admin-Token: devtoken" \
#       -H 'content-type: application/json' -d '{"key_hash":"<hash>"}'
```

### 7. Tear down

```bash
pkill -f "uvicorn main:app"
./scripts/dev_db_down.sh
```

## Anti-abuse & bit-drain (EPIC 3)

"No one can raid my bits": every byte served by this API is **DRBG-derived**
(`qeaas.keyed_drbg.output()`), never a raw QRNG bit. That single fact decouples request
volume from pool consumption — the three defences below just bound *served output volume*
and abuse visibility; the pool itself is protected separately by a reseed-frequency floor.

1. **Public throttling (S3.1).** Anonymous `/random` and `/dice` are limited per IP to
   **60 req/min** (`rl:ip:{ip}:{minute}`, atomic `INCR` + `EXPIRE 60`), and `/random` output
   is additionally capped by a **global 5 MB/day** ceiling (`anon:daily:{day}`, atomic
   `INCRBY` + `EXPIRE`). Over either → `429` with a `Retry-After` header.
2. **Keyed throttling (S3.2).** `/v1/random/bytes` and `/v1/seed` enforce a per-key rate
   limit and a per-key daily byte quota (`rl:key:{hash}:{minute}`, `quota:key:{hash}:{day}`),
   both tier-driven:

   | Tier | Daily quota | Rate limit |
   |------|-------------|------------|
   | `default` | 256 KB/day | 120 req/min |
   | `iot` | 10 MB/day | 600 req/min |
   | `trusted` | 500 MB/day | 1,200 req/min |

   A key's explicit `daily_quota_bytes` (set at mint time) overrides the tier default;
   `NULL` falls back to it. Over rate → `429 rate_limited`; over quota → `429 quota_exceeded`
   (a rejected request's bytes are refunded via `DECRBY`, so it never burns quota it didn't
   use).
3. **Bit-drain protection (S3.3 — the actual worry).** `qeaas.keyed_drbg.maybe_reseed()`
   rotates `root_key` from the pool on whichever comes first: a fixed 15-minute interval, or
   an output-count limit — but the output-count branch is now additionally floored by
   `RESEED_MIN_INTERVAL_SECONDS` (5 minutes), so no amount of request volume can rotate the
   key (and pull pool bytes) faster than wall-clock time allows. Pool drain is a function of
   *time*, never of *traffic*. `usage_log` records every keyed issue (`principal`, `endpoint`,
   `nbytes`) for abuse spotting, and revocation (`POST /admin/keys/revoke` or
   `scripts/revoke_key.py`) is instant — `require_api_key` reads the row fresh from Neon on
   every request, no caching.

All counters are atomic Redis ops only (`INCR`/`INCRBY`/`EXPIRE`/`DECRBY`) — no
read-modify-write, serverless-safe. On a Redis outage, throttling **fails open** (logs a
warning, allows the request); the reseed floor still guarantees the pool can't be drained.

## ML-KEM consumer (EPIC 4)

The **crypto payload**: `/v1/kem/*` turns QRNG entropy into working post-quantum key material.
Repeat the honest framing here too — QRNG does not "defeat quantum attackers." It supplies
entropy that seeds a standards DRBG (`qeaas.generation.random_bytes`, the same choke point
`/v1/random/bytes` uses — raw QRNG bits are never served, decision #2), which in turn seeds
**ML-KEM-768** (FIPS 203). The quantum part is the *entropy source*; the quantum *resistance*
comes from ML-KEM.

**`kyber-py` is educational and not constant-time** — correct for a thesis demo, not
production. A production deployment would swap to `liboqs` on a persistent host (a
non-serverless target, since `liboqs` needs a native build step).

Both routes are gated (`503 low_quantum_entropy` while degraded), API-keyed (`401` for a
missing/bad/revoked key), and throttled exactly like `/v1/random/bytes` (per-key rate limit +
daily quota, `429 rate_limited` / `429 quota_exceeded`); every issue is recorded in
`usage_log`.

**`POST /v1/kem/keypair`** — QRNG-seeded ML-KEM-768 keygen. `public_key` (`ek`, base64) is
always returned; `secret_key` (`dk`) is returned only in the demo flow (`include_secret_key`),
with a loud "demo only" note — real keygen happens client-side in production, and the secret
key never leaves the holder.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/kem/keypair -H "X-API-Key: <key>" \
  -H 'content-type: application/json' -d '{}'
curl -s -X POST http://127.0.0.1:8000/v1/kem/keypair -H "X-API-Key: <key>" \
  -H 'content-type: application/json' -d '{"include_secret_key":true}'
```

**`POST /v1/kem/encapsulate`** — encapsulate against a supplied `public_key`. `ciphertext` is
always returned; `shared_secret` and an illustrative HKDF-derived `demo_key` are returned only
with `include_shared_secret` (the encapsulator legitimately knows the shared secret, but the
default response stays a pure `{ciphertext}`). There is **no** server-side decapsulate route —
decapsulation happens client-side, on the holder of `dk`.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/kem/encapsulate -H "X-API-Key: <key>" \
  -H 'content-type: application/json' \
  -d '{"public_key":"<ek from the keypair call>","include_shared_secret":true}'
```

A malformed or wrong-length `public_key` → `422 bad_request`.

**Round-trip proof (AC-6):** `keygen -> encaps -> decaps` recovers the same shared secret,
verified end-to-end against the running API (no server-side decaps oracle involved):

```bash
API_KEY=<key> api/venv/bin/python api/scripts/kem_roundtrip.py
# OK: QRNG-seeded ML-KEM-768 keypair round-trips (ss=32B)
```

## Deployment (EPIC 6)

Production is **two separate Vercel projects**, not one monorepo project — a deliberate
deviation from the build plan's "Next.js + FastAPI in one Vercel project (Services)" phrasing
(see `claude/plans/feature-epic6-deployment.md` §5 Decision 1). The old repo-level
`qrng-eaas/vercel.json` rewrote `/api/(.*)` → `/api/main.py`, but `main.py`'s routes are bare
(`/health`, `/dice`, …, no `/api` prefix) and `GET /dice` (web page) vs `POST /dice` (API route)
collide on one domain — path-based rewrites can't route by HTTP method. Two projects, two
domains, sidesteps both problems with zero code changes.

| Project | Root directory | Domain (fill in once deployed) |
|---|---|---|
| `qeaas-api` | `qrng-eaas/api` | `https://quantum-research-api.vercel.app` |
| `qeaas-web` | `qrng-eaas/web` | `https://eaas-two.vercel.app` |

### Env vars per project

**`qeaas-api`:**

| Key | Value |
|---|---|
| `DATABASE_URL` | Neon **pooled** connection string |
| `REDIS_URL` | Upstash `rediss://` (TLS) connection string |
| `MASTER_KEY` | fresh `secrets.token_hex(32)` — never the `.env.example` placeholder |
| `ADMIN_TOKEN` | fresh `secrets.token_urlsafe(32)` — never the `.env.example` placeholder |
| `WEB_ORIGIN` | the `qeaas-web` domain above, no trailing slash |

**`qeaas-web`:**

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE` | the `qeaas-api` domain above |

Env var changes only apply to new deployments — redeploy from the **Deployments** tab after
editing one.

### One-time provisioning

1. Neon: new project → **Connection string** with **Pooled connection** toggled on → run
   `api/sql/001_entropy_core.sql`, `002_api_keys.sql`, `003_usage_log.sql`, `004_provenance.sql`
   in that order via the dashboard SQL Editor.
2. Upstash: new **Regional** Redis database → copy the `rediss://` (TCP) connection string,
   not the REST URL.
3. Import the repo into Vercel twice (once per project above), setting **Root Directory** per
   project. `qrng-eaas/api/vercel.json` pins the Python 3.13 runtime and rewrites every path to
   `main.py`; it must exist and be committed before the first `qeaas-api` deploy.

### Runbook: verify + seed a fresh deploy

```bash
API=https://quantum-research-api.vercel.app
WEB=https://eaas-two.vercel.app

# 1. confirm the function is reachable at all
curl -s "$API/health"   # quantum_entropy_level: "degraded" is expected pre-seed

# 2. seed the production entropy pool from real QRNG output (convert the `bits:`-prefixed
#    processed files to the plain 0/1 contract first — see feature-epic6-deployment.md §6
#    Phase 6 for the exact conversion script), then ingest each as its own admin call:
curl -s -X POST "$API/admin/ingest" -H "X-Admin-Token: <ADMIN_TOKEN>" -F "file=@/tmp/prod_bits_fez.txt"
curl -s -X POST "$API/admin/ingest" -H "X-Admin-Token: <ADMIN_TOKEN>" -F "file=@/tmp/prod_bits_marrakesh.txt"
curl -s "$API/health"   # should now read "healthy"

# 3. mint a production API key (shown once)
curl -s -X POST "$API/admin/keys" -H "X-Admin-Token: <ADMIN_TOKEN>" \
  -H 'content-type: application/json' -d '{"owner":"prod-smoke-test","tier":"default"}'

# 4. full endpoint sweep against production (same shapes as the local smoke test above)
KEY=<key from step 3>
curl -s "$API/random?bytes=32"
curl -s -X POST "$API/dice" -H 'content-type: application/json' -d '{"sides":6,"count":2}'
curl -s -H "X-API-Key: $KEY" "$API/v1/random/bytes?size=64&format=hex"
curl -s -H "X-API-Key: $KEY" "$API/v1/seed?bytes=64"
curl -s -X POST "$API/v1/kem/keypair" -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{}'
curl -s "$API/v1/pubkey"
curl -s -X POST "$API/v1/verify" -H 'content-type: application/json' -d '{"request_id":"abc"}'

# 5. confirm state survives across separate serverless invocations (not just within one
#    process, the way local uvicorn trivially does) — pool_bytes_remaining should never
#    reset upward between two calls minutes apart, and drbg_reseeds should be a small
#    positive integer, not stuck at 0
curl -s "$API/health" | python3 -c "import json,sys; print(json.load(sys.stdin)['pool_bytes_remaining'])"
# wait a minute, hit a few keyed routes, then re-run the line above
```

Open `$WEB` on your phone too — confirm the explainer loads, the health badge is green, and
`/dice` rolls without a page reload.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| API build fails mentioning `pycryptodome` or a compiler error | native wheel unavailable for Vercel's Python 3.13 runtime | pin the latest compatible `pycryptodome`; if it still fails, this needs its own ticket (swap to `cryptography`), not a mid-deploy improvisation |
| `curl .../health` 404s | `qrng-eaas/api/vercel.json` missing or not committed before the first deploy | add it, commit, push |
| Every `fetch()` fails with CORS in the browser console | `WEB_ORIGIN` doesn't exactly match the web project's URL | fix the env var, redeploy `qeaas-api` |
| `/admin/*` returns `401` | wrong/missing `X-Admin-Token`, or it doesn't match Vercel's stored value | re-check Phase 3's saved value; regenerate + re-save + redeploy if unsure |
| env var change doesn't seem to take effect | Vercel only applies env var changes to new deployments | trigger a redeploy from the **Deployments** tab |

## Seed-quality report (EPIC 7)

Produces the statistical evidence (bias, NIST SP 800-22, next-bit ML predictability, Markov
dependency) that the deployed service's `/v1/seed` output is indistinguishable from the OS
CSPRNG, for the thesis appendix. Read-only against the live deployment; scripts and sample data
live under `qrng-eaas/claude/validation/`.

```bash
cd qrng-eaas/claude/validation

# 0. local tooling for the report only — separate from api/venv
python3 -m venv .report-venv
source .report-venv/bin/activate
pip install -r requirements-report.txt

# 1. mint a dedicated, higher-quota (iot tier, 10 MiB/day) API key for the pull —
#    don't reuse the smoke-test key. Use the ADMIN_TOKEN already hardcoded in
#    ../prod_seed/mint_prod_key.sh. The plaintext key is in the response's `api_key` field.
curl -s -X POST https://quantum-research-api.vercel.app/admin/keys \
  -H "X-Admin-Token: <token from ../prod_seed/mint_prod_key.sh>" \
  -H 'content-type: application/json' \
  -d '{"owner":"seed-quality-report","tier":"iot"}'

# 2. pull ~1.5 MB from the deployed service, and an equal-size os.urandom baseline
mkdir -p samples
python3 pull_seed_sample.py \
  --api-base https://quantum-research-api.vercel.app \
  --api-key <key from step 1> \
  --total-bytes 1572864 \
  --out samples/service_sample.txt
python3 pull_urandom_sample.py --total-bytes 1572864 --out samples/urandom_sample.txt

# 3. run the existing, unmodified qrng_compare.py battery against both samples
python3 ../../../ErrorDetectionVSRawBits/qrng_compare.py \
  samples/service_sample.txt samples/urandom_sample.txt \
  -o seed_quality_report.pdf
```

The sample files under `samples/` are regenerable scratch data (gitignored). The generated
`seed_quality_report.pdf` is the committed, point-in-time deliverable referenced from the thesis
appendix — it is not auto-regenerated on every re-run; a fresher report is a deliberate manual
re-run and a new commit.

## Networking demonstration (EPIC 8)

Where the QRNG→ML-KEM entropy chain plugs into networking: a two-role Server/Client
handshake (QRNG-seeded ML-KEM-768 keygen + encaps → shared secret → HKDF → AES-GCM
message exchange), runnable as a CLI script or interactively in the web app, plus an
honest mapping to five real networking use cases. Full write-up:
`shared/docs/networking-demo.md`.

**CLI (rigorous, reproducible — independently verifies both parties agree on the shared
secret):**

```bash
cd qrng-eaas/api
API_KEY=<key> python -m scripts.kem_handshake --base-url http://localhost:8000
# or: --base-url https://quantum-research-api.vercel.app
```

**Web demo** — `/demo` on the web app (`https://eaas-two.vercel.app/demo` in prod, or
`http://localhost:3000/demo` locally): the same handshake, visualized live with no page
reload, plus the five networking use-case mappings.

**Provisioning `KEM_DEMO_API_KEY`** — the web demo's server-side proxy
(`web/app/api/kem/*/route.ts`) needs a dedicated `iot`-tier API key so the browser
never sees a key directly:

```bash
curl -s -X POST <base>/admin/keys -H "X-Admin-Token: <ADMIN_TOKEN>" \
  -H 'content-type: application/json' -d '{"owner":"networking-demo","tier":"iot"}'
```

Set the plaintext `api_key` from the response as `KEM_DEMO_API_KEY`, and `API_ORIGIN`
to the FastAPI base URL, in `web/.env.local` (local dev) and in the Vercel project env
for `qeaas-web` (prod) — both are server-only, never `NEXT_PUBLIC_*`.

## Provenance & verification (EPIC 9)

Verify **provenance, not the secret**: every keyed/KEM issue (`/v1/random/bytes`, `/v1/seed`,
`/v1/kem/keypair`, `/v1/kem/encapsulate`) ships a signed `receipt` alongside its data, but the
output bytes themselves are never persisted anywhere.

- **Signing key.** An Ed25519 key derived via `pool.derive_subkey("receipt-signing-key")` --
  the third named sub-key off `MASTER_KEY`, alongside `pool-encryption-key`/`api-key-pepper`. No
  new env var. The public key is published at `GET /v1/pubkey` for external, offline
  verification (`{algorithm:"Ed25519", format:"base64", public_key}`).
- **Receipts.** `qeaas/receipts.py` signs `(request_id, size, entropy_epoch, timestamp)` into a
  compact `qeaas1.<payload>.<signature>` token (`receipt` field on every issue response).
  `issue_log` (metadata only -- `request_id, principal, endpoint, size, epoch_id, ts`, **no
  output bytes column**) is written alongside `usage_log` for every issue.
- **`POST /v1/verify {request_id?, receipt?}`.** With a `receipt`, the signature is
  cryptographically verified and the response resolves `entropy_epoch` plus the pool's
  `qrng_source_labels` -- a real QRNG batch. With only a `request_id`, it's a plain `issue_log`
  lookup (the response says so honestly). A tampered/forged receipt fails: `verified:false`,
  `provenance:null`. Anonymous, but per-IP rate-limited like `/random`/`/dice`.
- **Web "Verify a receipt" box.** A section on the explainer home page: paste a receipt or a
  bare `request_id`, get back the resolved provenance, no page reload.
- **Not an oracle.** `/v1/verify` never accepts or compares an output value -- it only proves a
  receipt's metadata is authentic, which is exactly what lets the service guarantee it never
  stored the bytes it issued.

## Spikes

- `shared/spikes/mlkem_seed_spike.py` — proves DRBG bytes deterministically drive ML-KEM-768 keygen
  and that encaps/decaps round-trips (S0.2). Run with `api/venv/bin/python shared/spikes/mlkem_seed_spike.py`.
