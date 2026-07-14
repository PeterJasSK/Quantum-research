# Quantum Entropy-as-a-Service (Q-EaaS) — API Reference

FastAPI service that turns preloaded **QRNG (quantum random number generator)** bits into
served randomness, dice rolls, cryptographic seeds, and post-quantum ML-KEM key material —
each issue carrying a signed, offline-verifiable provenance receipt.

Monorepo layout: `api/` (this document — FastAPI service), `web/` (Next.js explainer + demo),
`shared/` (docs, spikes), `claude/` (epic build plans). The web app is a thin client over the
API; everything substantive happens here.

> **Honest framing, stated once and meant everywhere.** QRNG does not "defeat quantum
> attackers." Raw QRNG bits are *never served*. They are entropy that **seeds a standards
> HMAC-DRBG** (NIST SP 800-90A). Every byte this API returns — `/random`, `/dice`, `/v1/seed`,
> ML-KEM seeds — is DRBG output. The quantum part is the *entropy source*; any quantum
> *resistance* comes from ML-KEM-768 (FIPS 203), not from the randomness being "quantum."

---

## 1. Architecture at a glance

```
             ┌──────────── admin (X-Admin-Token) ────────────┐
             │                                                │
   QRNG .txt │  POST /admin/ingest                            │  POST /admin/keys
  (0/1 bits) ▼                                                ▼  POST /admin/keys/revoke
        ┌─────────────┐   AES-256-GCM    ┌───────────────────────────────┐
        │ pool.parse  │ ───────────────▶ │  Postgres (Neon)              │
        │ + encrypt   │                  │   entropy_pool  (ciphertext)  │
        └─────────────┘                  │   drbg_root     (ciphertext)  │
                                         │   api_keys / usage_log /      │
                                         │   issue_log                   │
                                         └───────────────┬───────────────┘
                                                         │ decrypt slice on reseed
                                                         ▼
   client                    ┌───────────────────────────────────────┐
  ─────────▶  entropy gate   │  keyed_drbg.output(n)                  │
  request     (503 if low)   │   root_key  ← reseeded from pool       │
             + rate limit ──▶│   counter   ← Redis atomic INCR        │──▶ HMAC-DRBG(SHA-256)
             + API key       │   HMAC-DRBG(root_key, counter) → bytes │      = served bytes
                             └───────────────────────────────────────┘
                                                         │
                             ┌───────────────────────────┴───────────┐
                             │  Redis (Upstash)                       │
                             │   drbg:counter   (output uniqueness)   │
                             │   rl:* / quota:* / anon:* (throttling) │
                             └────────────────────────────────────────┘
```

- **Stateless / serverless.** Each request opens a Postgres connection and closes it (`db.connect`);
  there is no long-lived pool object. DRBG state is never read-modify-written per request — see §4.
- **Two datastores, two different jobs** — see §3.
- **CORS** is locked to the origins in `WEB_ORIGIN` (comma-separated).
- Every response carries an **`X-Quantum-Entropy: healthy|degraded`** header (added by middleware
  in `main.py`).

Source map (`api/qeaas/`):

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, all route handlers, CORS, entropy header middleware |
| `generation.py` | The single served-randomness choke point + provenance metadata builder |
| `keyed_drbg.py` | Serverless-safe DRBG wrapper: reseed schedule, Redis-counter mixing |
| `drbg.py` | Pure NIST SP 800-90A HMAC-DRBG (SHA-256) |
| `pool.py` | Entropy pool: parse `0/1`, AES-256-GCM encrypt/decrypt, HKDF sub-keys, `burn()` |
| `db.py` | Parameterized psycopg helpers for all five tables |
| `redis_client.py` | Lazy Upstash client: atomic counter + rate-limit ops |
| `gate.py` | Low-entropy gate (`entropy_level`, `require_entropy` dependency) |
| `auth.py` | Admin-token guard, API-key hashing + validation |
| `ratelimit.py` | Per-IP / per-key rate limits, anon daily ceiling, per-key quota |
| `dice.py` | Rejection-sampled dice (no modulo bias) |
| `kem.py` | QRNG-seeded ML-KEM-768 keygen + encapsulation |
| `receipts.py` | Ed25519 receipt signing + verification |
| `errors.py` | Flat `{"error": "<slug>"}` envelope for every failure |
| `schemas.py` | Pydantic request/response models |

---

## 2. The randomness pipeline (what fires, in order)

Every served byte flows through **one choke point**, `generation.random_bytes(n)` →
`keyed_drbg.output(n)`. Nothing bypasses it.

**A. Ingest (admin, offline of the request path).**
`POST /admin/ingest` → `pool.ingest_bits_bytes()` → `pool.parse_bits_bytes()` packs the `0/1`
text MSB-first into bytes (discarding a trailing partial byte, rejecting any non-`0/1` char) →
`pool.encrypt_chunk()` AES-256-GCM-encrypts it → `db.insert_pool_chunk()` stores
`(ciphertext, nonce, tag, plaintext_len, source_label)` in **`entropy_pool`**. Plaintext never
touches disk; the upload buffer is `burn()`-ed.

**B. Serve (per request).** `keyed_drbg.output(n)`:
1. `maybe_reseed()` — loads the warm root-key cache (`_load_cache`), bootstrapping the root key
   from the pool on very first use (`_bootstrap_root_key`). If the reseed schedule is due (§4),
   `pool.pull_reseed_material(32)` decrypts the next unconsumed 32-byte slice from `entropy_pool`,
   encrypts it as the new `drbg_root` row, advances `consumed_offset`, and `burn()`s the plaintext.
2. `redis_client.incr_counter()` — atomic `INCR drbg:counter`, returns a **globally unique** integer.
3. A fresh `HmacDrbg` is instantiated with the decrypted `root_key` and `generate(n, additional =
   counter.to_bytes(8) + additional)` is called — the counter guarantees two concurrent requests
   can never produce identical output even with identical root key.
4. `db.bump_outputs_since_reseed()` increments the reseed odometer.

**C. Wrap (per endpoint).** `generation.new_issue_meta(size)` mints a `request_id` (uuid4), reads
`entropy_epoch` (= `drbg_root.reseed_counter`), timestamps, and calls `receipts.sign(...)` to
produce the Ed25519 receipt. Keyed endpoints then write `db.insert_usage_log()` (abuse spotting)
and `db.insert_issue_log()` (metadata-only provenance — **no output bytes are ever stored**).

See the deep-dive comment at the end of this file / in the chat analysis for the exact call graph.

---

## 3. Why two databases

They protect against **completely different failure modes** and have opposite consistency needs.

### Postgres (Neon) — the durable secret store & audit ledger

Holds everything that **must survive** and must be **transactional & durable**. Five tables:

| Table | Holds | Notes |
|---|---|---|
| `entropy_pool` | AES-256-GCM ciphertext of QRNG bits + `nonce`, `tag`, `plaintext_len`, `consumed_offset`, `source_label` | The vault. No plaintext-bytes column exists. `consumed_offset` tracks how much of each chunk has been spent. |
| `drbg_root` | AES-256-GCM ciphertext of the current DRBG root seed + `reseed_counter`, `outputs_since_reseed`, `rotated_at` | The live DRBG key, rotated ("reseeded") from the pool on schedule. `reseed_counter` == `entropy_epoch` in receipts and `drbg_reseeds` in `/health`. |
| `api_keys` | `key_hash` (HMAC-SHA256, peppered), `owner`, `tier`, `daily_quota_bytes`, `revoked`, `created_at` | Plaintext keys never stored. Read fresh every request so revocation is instant. |
| `usage_log` | `(ts, principal, endpoint, nbytes)` | Abuse-spotting ledger for keyed issues. Anon `/random`/`/dice` are **not** logged here. |
| `issue_log` | `(request_id, principal, endpoint, size, epoch_id, ts)` | Metadata-only provenance. **No output-bytes column exists, ever** — verify provenance, not the secret. |

Durability matters: lose the pool ciphertext or the root key and the service can no longer prove
provenance or reseed. Postgres is ACID; this is where correctness lives.

### Redis (Upstash) — the ephemeral atomic counter & throttle

Holds **only fast, disposable, atomically-mutated counters** that would be a correctness hazard
in Postgres under serverless concurrency:

| Key | Purpose | Op |
|---|---|---|
| `drbg:counter` | **Output uniqueness.** Monotonic integer mixed into every DRBG call so two concurrent serverless invocations can't emit the same bytes. | `INCR` |
| `rl:ip:{ip}:{minute}` | Per-IP rate limit (anon routes) | `INCR` + `EXPIRE 60` |
| `rl:key:{hash}:{minute}` | Per-key rate limit | `INCR` + `EXPIRE 60` |
| `anon:daily:{day}` | Global anon output ceiling (5 MB/day) | `INCRBY` + `EXPIRE`, `DECRBY` on refund |
| `quota:key:{hash}:{day}` | Per-key daily byte quota | `INCRBY` + `EXPIRE`, `DECRBY` on refund |

Why not put these in Postgres? On stateless serverless you cannot safely read-modify-write shared
state per request — two concurrent requests would race. Redis `INCR`/`INCRBY` are **atomic**, so
there is no read-modify-write. These values are *meant* to expire (per-minute, per-day) and losing
them is harmless — throttling **fails open** on a Redis outage (logs a warning, allows the request),
because the reseed-frequency floor (§4) still guarantees the pool can't be drained.

**One-line summary:** Postgres = durable secrets + audit that must be correct forever; Redis =
ephemeral atomic counters that must be fast and race-free but are disposable.

---

## 4. The DRBG & bit-drain protection

- **HMAC-DRBG (SHA-256)**, NIST SP 800-90A §10.1.2 (`drbg.py`). Not thread-safe — each request gets
  its own instance.
- **Serverless-safe wrapper** (`keyed_drbg.py`): `output(n) = HMAC-DRBG(root_key, INCR(drbg:counter), n)`.
- **Reseed schedule.** `root_key` rotates from the pool on whichever fires first:
  - a fixed **15-minute** interval (`RESEED_INTERVAL_SECONDS`), **or**
  - an output count ≥ `RESEED_OUTPUT_LIMIT` (100 000) **but only if** ≥ `RESEED_MIN_INTERVAL_SECONDS`
    (5 minutes) has elapsed.
  Each reseed pulls `RESEED_PULL_BYTES` (32) from the pool.
- **Bit-drain is impossible via traffic.** Served bytes are always DRBG output, never raw pool bits,
  and the 5-minute floor means no request volume can rotate the key faster than wall-clock time.
  Pool drain is a function of *time*, never *traffic*.
- **Low-entropy gate.** Below `THRESHOLD` (64 KiB) of unconsumed pool bytes, `/health` reports
  `degraded` and all gated routes `503 low_quantum_entropy` (`gate.require_entropy`).

---

## 5. Cryptographic key hierarchy

One env-held `MASTER_KEY` (256-bit hex). `pool.derive_subkey(name)` (HKDF-SHA256, RFC 5869
one-block Expand) derives exactly four named sub-keys — there are no other secrets:

```
MASTER_KEY  (env / KMS only — never written to Postgres)
  └── HKDF-SHA256
       ├── "pool-encryption-key"       → entropy_pool  AES-256-GCM
       ├── "drbg-root-encryption-key"  → drbg_root.root_key AES-256-GCM
       ├── "api-key-pepper"            → API-key hashing  (HMAC-SHA256)
       └── "receipt-signing-key"       → Ed25519 receipt signing seed
```

AES-256-GCM is authenticated: a flipped ciphertext byte fails the tag check and decryption raises —
the service fails **closed** on tampered storage. Sensitive plaintext (decrypted slices, the warm
root-key cache, upload buffers) is held in `bytearray` and best-effort `burn()`-ed after use (CPython
cannot *guarantee* zeroization; serverless teardown keeps in-process secrets short-lived by design).

---

## 6. Authentication

| Mechanism | Header | Applies to |
|---|---|---|
| **None (anonymous)** | — | `/health`, `/random`, `/dice`, `/v1/verify`, `/v1/pubkey` |
| **API key** | `X-API-Key: <plaintext>` | `/v1/random/bytes`, `/v1/seed`, `/v1/kem/*` |
| **Admin token** | `X-Admin-Token: <token>` | `/admin/*` |

- API keys: `hash_api_key(key) = HMAC-SHA256(pepper, key)`; only the hash is stored. `require_api_key`
  reads the row fresh every request, so `revoked = true` takes effect immediately. Missing header →
  `401 missing_api_key`; unknown/revoked → `401 invalid_api_key`.
- Admin token: constant-time compared (`hmac.compare_digest`) against `ADMIN_TOKEN`. Wrong/missing →
  `401 unauthorized`.

---

## 7. Rate limits, quotas, tiers

All counters are atomic Redis ops; **fail open** on a Redis error.

- **Anon per-IP:** 60 req/min on `/random` and `/dice` (`ANON_IP_PER_MIN`).
- **Anon global daily:** 5 MB/day output ceiling on `/random` (`ANON_DAILY_BYTES`).
- **Per-key** (`/v1/*`), tier-driven:

  | Tier | Daily quota | Rate limit |
  |---|---|---|
  | `default` | 256 KB/day | 120 req/min |
  | `iot` | 10 MB/day | 600 req/min |
  | `trusted` | 500 MB/day | 1 200 req/min |

  A key's explicit `daily_quota_bytes` overrides the tier default; `NULL` falls back to it. Rate is
  checked before quota (cheaper to reject). An over-quota request's bytes are **refunded** (`DECRBY`)
  so a rejection never burns quota it didn't use.
- Every `429` carries a `Retry-After` header (seconds until the window resets).

---

## 8. Error envelope

Every failure returns a flat JSON body: `{"error": "<slug>"}` (see `errors.py`). Common slugs:

| Status | Slug | Meaning |
|---|---|---|
| 401 | `unauthorized` / `missing_api_key` / `invalid_api_key` | auth failure |
| 404 | `not_found` | e.g. revoke of an unknown key hash |
| 413 | `file_too_large` | ingest upload > 10 MB |
| 422 | `bad_request` | validation / malformed input (also FastAPI validation errors) |
| 429 | `rate_limited` / `daily_limit_reached` / `quota_exceeded` | throttled (has `Retry-After`) |
| 503 | `low_quantum_entropy` | pool below 64 KiB, gated route blocked |
| 500 | `dice_sampling_failed` | rejection sampling exhausted its draw cap (extremely unlikely) |

---

## 9. Endpoint reference

### `GET /health` — anonymous
Liveness + pool/DRBG status. Never gated.
```jsonc
{ "status": "ok", "quantum_entropy_level": "healthy",  // or "degraded"
  "pool_bytes_remaining": 699000, "drbg_reseeds": 3, "uptime": 1234.5 }
```
Fires: `db.get_root_key`, `db.pool_bytes_remaining`, `gate.entropy_level`.

### `GET /random?bytes=<1..64>` — anonymous, ungated
DRBG-derived random bytes, base64. Survives a `degraded` pool. Rate-limited per IP + anon daily.
```jsonc
{ "bytes": 32, "format": "base64", "data": "<base64>" }
```
Fires: `ratelimit.check_ip_rate` → `ratelimit.check_anon_daily` → `generation.random_bytes`.
Errors: `422` (bytes out of range), `429 rate_limited` / `daily_limit_reached`.

### `POST /dice` — anonymous, ungated
Rejection-sampled dice (no modulo bias). Rate-limited per IP.
Request: `{ "sides": 2..100 (default 6), "count": 1..6 (default 1) }`
```jsonc
{ "sides": 6, "count": 2, "rolls": [3, 6], "format": "base64",
  "bytes_used": "<base64>", "bytes_count": 2 }
```
`bytes_used` / `bytes_count` echo **every DRBG byte drawn** for the roll — accepted *and* rejected —
so the web dice player's "bytes behind this roll" toggle is literal. Still DRBG output, never raw
QRNG bits. Fires: `ratelimit.check_ip_rate` → `dice.roll` (loops `keyed_drbg.output(1)`).
Errors: `422` (out of range), `429`, `500 dice_sampling_failed`.

### `GET /v1/random/bytes?size=<32..4096>&format=<hex|base64>` — API key, gated
Canonical developer endpoint. Per-key rate limit + daily quota, then usage + issue logs.
```jsonc
{ "request_id": "…", "format": "hex", "data": "…",
  "entropy_epoch": 3, "timestamp": "2026-…Z", "receipt": "qeaas1.<payload>.<sig>" }
```
Fires: `require_entropy` (gate) → `require_api_key` → `ratelimit.enforce_key` →
`generation.issue_v1` (→ `random_bytes` + `new_issue_meta` + `receipts.sign`) →
`db.insert_usage_log` + `db.insert_issue_log`.
Errors: `401`, `429 rate_limited`/`quota_exceeded`, `503 low_quantum_entropy`, `422`.

### `GET /v1/seed?bytes=<32..4096>&format=<hex|base64>` — API key, gated
Alias of `/v1/random/bytes` — shares the exact same service function so the two cannot drift. Same
response shape, same errors. (Only the query-param name differs: `bytes` vs `size`.)

### `POST /v1/verify` — anonymous, per-IP rate-limited
Verify **provenance, not the secret**. Request: `{ "request_id"?: str, "receipt"?: str }` (at least
one required — else `422`).
- With a `receipt`: signature is cryptographically verified; response resolves `size`,
  `entropy_epoch`, `timestamp`, and the pool's `qrng_source_labels`.
- With only a `request_id`: plain `issue_log` lookup (the `note` says so honestly).
- Tampered/forged receipt → `verified: false`, `provenance: null`.
```jsonc
{ "request_id": "…", "verified": true,
  "provenance": { "size": 64, "entropy_epoch": 3, "timestamp": "…",
                  "qrng_source_labels": ["fez", "marrakesh"] },
  "note": "receipt signature verified cryptographically" }
```
Fires: `ratelimit.check_ip_rate` → `receipts.verify` (→ `receipts.verify_receipt` and/or
`db.get_issue_log`, `db.get_pool_source_labels`). **Never an oracle** — it never accepts or compares
an output value.

### `GET /v1/pubkey` — anonymous
Published Ed25519 receipt-signing public key, for external **offline** verification.
```jsonc
{ "algorithm": "Ed25519", "format": "base64", "public_key": "<base64 32-byte raw>" }
```

### `POST /v1/kem/keypair` — API key, gated
QRNG-seeded **ML-KEM-768** (FIPS 203) keygen. Request: `{ "include_secret_key"?: false }`.
`public_key` (`ek`) always returned; `secret_key` (`dk`) only in the demo flow, with a loud
"demo only" note (real keygen happens client-side; the secret key never leaves the holder).
```jsonc
{ "request_id": "…", "algorithm": "ML-KEM-768", "format": "base64",
  "public_key": "<ek base64>", "secret_key": null,
  "entropy_epoch": 3, "timestamp": "…", "receipt": "…", "note": null }
```
Fires: gate → `require_api_key` → `ratelimit.enforce_key` → `kem.generate_keypair`
(`generation.random_bytes(64)` → `ML_KEM_768.key_derive`) → `new_issue_meta` → usage/issue logs.

### `POST /v1/kem/encapsulate` — API key, gated
Encapsulate against a supplied `public_key`. Request:
`{ "public_key": "<ek base64>", "include_shared_secret"?: false }`.
`ciphertext` always returned; `shared_secret` + an illustrative HKDF-derived `demo_key` only with
`include_shared_secret`. There is **no server-side decapsulate route** — decapsulation is
client-side, on the holder of `dk`.
```jsonc
{ "request_id": "…", "algorithm": "ML-KEM-768", "format": "base64",
  "ciphertext": "<base64>", "shared_secret": null, "demo_key": null,
  "entropy_epoch": 3, "timestamp": "…", "receipt": "…", "note": null }
```
Fires: gate → `require_api_key` → `ratelimit.enforce_key` → `kem.encapsulate`
(`generation.random_bytes(32)` → `ML_KEM_768._encaps_internal`) → `new_issue_meta` → logs.
Malformed/wrong-length `ek` → `422 bad_request`.
> `kyber-py` is educational and **not constant-time** — correct for a thesis demo, not production
> (which would use `liboqs` on a persistent host).

### `POST /admin/ingest` — admin token
Multipart `.txt` upload of `0`/`1` characters (≤ 10 MB) → refills the pool. Parses in memory,
encrypts, stores; **no plaintext ever touches disk**; upload buffer is burned.
```jsonc
{ "ingested": true, "bytes_added": 87500, "pool_bytes_remaining": 786500 }
```
Fires: `require_admin` → `pool.ingest_bits_bytes` (→ `parse_bits_bytes` → `encrypt_chunk` →
`db.insert_pool_chunk`) → `pool.burn`. Errors: `401`, `413 file_too_large`, `422` (non-`.txt` or
non-`0/1` content).

### `POST /admin/keys` — admin token
Mint an API key (same logic as `scripts/mint_key.py`). The plaintext key is returned **once**.
Request: `{ "owner": str, "tier"?: "default", "daily_quota_bytes"?: int|null }`.
```jsonc
{ "api_key": "<plaintext — shown once>", "owner": "devtest",
  "tier": "default", "daily_quota_bytes": null }
```
Fires: `require_admin` → `secrets.token_urlsafe(32)` → `auth.hash_api_key` → `db.insert_api_key`.

### `POST /admin/keys/revoke` — admin token
Instant revocation. Request: `{ "key_hash": str }`.
```jsonc
{ "key_hash": "…", "revoked": true }
```
Fires: `require_admin` → `db.revoke_api_key`. Unknown hash → `404 not_found`.

---

## 10. Local development

```bash
cd api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # fill DATABASE_URL, REDIS_URL, MASTER_KEY, ADMIN_TOKEN
```

Every route touches Postgres and most touch Redis — with empty `.env` values every request 500s.
For a disposable local backend (Docker Postgres + Redis, auto-applies all SQL migrations):

```bash
eval "$(./scripts/dev_db_up.sh --print-env)"    # starts qeaas-pg + qeaas-redis, exports env
uvicorn main:app --reload --port 8000 --env-file .env
```

Seed the pool (any `0/1` text exercises the pipeline locally — real deploys ingest actual QRNG output):

```bash
python3 -c "import random; random.seed(1); open('/tmp/bits.txt','w').write(''.join(random.choice('01') for _ in range(700000)))"
python scripts/ingest_bits.py /tmp/bits.txt seed
python -m scripts.mint_key --owner devtest --tier default    # prints the plaintext key once
uvicorn main:app --port 8000
```

Smoke test:

```bash
curl -s localhost:8000/health
curl -s "localhost:8000/random?bytes=32"
curl -s -X POST localhost:8000/dice -H 'content-type: application/json' -d '{"sides":6,"count":2}'
curl -s -H "X-API-Key: <key>" "localhost:8000/v1/random/bytes?size=64&format=hex"
open localhost:8000/docs     # interactive Swagger UI, every route typed
```

Tear down: `pkill -f "uvicorn main:app" && ./scripts/dev_db_down.sh`.

### Environment variables

| Key | Purpose |
|---|---|
| `DATABASE_URL` | Neon **pooled** Postgres connection string |
| `REDIS_URL` | Upstash `rediss://` (TLS) connection string |
| `MASTER_KEY` | 256-bit hex (`secrets.token_hex(32)`) — root of the sub-key hierarchy (§5) |
| `ADMIN_TOKEN` | Bearer token for `/admin/*` (`secrets.token_urlsafe(32)`) |
| `WEB_ORIGIN` | Comma-separated CORS-allowed origins (default `http://localhost:3000`) |

Rate limits, quotas, tiers, and reseed timing are **module constants** (`ratelimit.py`,
`keyed_drbg.py`), not env vars.

### Operational scripts (`api/scripts/`)

| Script | Does |
|---|---|
| `ingest_bits.py` | Parse + encrypt + store a `0/1` `.txt` into the pool |
| `mint_key.py` / `revoke_key.py` | CLI key lifecycle (mirrors the admin routes) |
| `kem_roundtrip.py` / `kem_handshake.py` | Prove `keygen → encaps → decaps` recovers the same shared secret against the live API |
| `scan_persistence.py` | Read-only invariant scan: no plaintext-sensitive columns/values persisted |
| `dev_db_up.sh` / `dev_db_down.sh` | Disposable Docker Postgres + Redis for local dev |

---

## 11. Deployment (summary)

Production is **two separate Vercel projects** (`qeaas-api` → `qrng-eaas/api`, `qeaas-web` →
`qrng-eaas/web`), not one — `GET /dice` (web page) vs `POST /dice` (API) collide on one domain and
path-based rewrites can't route by HTTP method. `qrng-eaas/api/vercel.json` pins the Python 3.13
runtime and rewrites every path to `main.py`. Provision Neon (run `sql/001…005` in order), Upstash
(regional, `rediss://` TCP URL), then set per-project env vars (§10). Full runbook, troubleshooting,
and the EPIC 7–11 write-ups (seed-quality report, networking demo, provenance, secure-storage burn
lifecycle, theming) live in `claude/plans/` and `shared/docs/`.
