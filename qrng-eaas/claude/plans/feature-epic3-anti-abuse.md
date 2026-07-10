# Feature Plan — EPIC 3: Anti-abuse ("no one can raid my bits")

**Status:** Complete — implemented and manually verified against a throwaway Postgres/Redis backend
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 3 `[MUST]`
**Interpretation of "part 3":** EPIC 3. The git history uses *part* and *epic* interchangeably
("par0 and part 1" = EPIC 0 + EPIC 1; "epic 2" = EPIC 2), and EPIC 2 is the most recent completed
work (`feature-epic2-public-api.md`, **Complete**). The next `[MUST]` in build order is EPIC 3 —
the anti-abuse layer: keep anonymous fun cheap and bounded, make the developer API keyed / quota'd /
revocable, and prove the QRNG pool cannot be drained by request volume.

> **No tests (project directive).** This plan does **not** plan, write, or maintain automated tests,
> and `/implement-feature` will not run or create any. Verification is manual only (`curl`, the
> running app, `redis-cli`, `psql`). The unmaintained legacy suite under `api/tests/` is out of scope.

> **Note on process:** this repo has no GitHub issues, no `tasks/plans/` tree, and no
> `_plan-template.md`. The global `/plan-feature` template (GitHub issues, Doctrine, PSR-12,
> councils) does not apply. This plan follows the shape established by
> `feature-epic2-public-api.md` and the project's real conventions (Python 3.13, FastAPI,
> `from __future__ import annotations`, full type hints, pure-Python deps, no raw SQL string
> interpolation, thin handlers, honest QRNG framing).

---

## 1. Context & goal

EPIC 2 shipped the HTTP surface with **authentication but no throttling**: `/random` and `/dice`
are anonymous and unbounded; `/v1/random/bytes` + `/v1/seed` validate an API key (peppered-hash
lookup + `revoked` check) but enforce **no quota and no rate limit**; `api_keys.daily_quota_bytes`
exists as an unenforced column. EPIC 3 closes those seams and delivers the "no one can raid my bits"
guarantee.

Three defences, matching the three stories:

- **S3.1 — public throttling.** Per-IP rate limit + a global daily output ceiling on the anonymous
  `/random` and `/dice` endpoints, backed by atomic Upstash counters. Over-limit → `429`.
- **S3.2 — keyed developer API.** Per-key daily quota (bytes) and per-key rate limit, both via
  Upstash TTL counters, with **tiers** (`default` small, `iot`/`trusted` higher). The HTTP mint route
  `POST /admin/keys` (deferred from EPIC 2 Q4) lands here alongside the existing `mint_key.py` CLI.
- **S3.3 — bit-drain protection (the actual worry).** Document that DRBG-derived output costs
  near-zero QRNG bits; **cap reseed frequency with a hard time floor** so unlimited traffic cannot
  accelerate pool drain; log keyed usage for abuse spotting; make revocation instant.

The engine and surface are done and reused unchanged except where noted:
- `qeaas.keyed_drbg.output()` / `maybe_reseed()` — served-randomness + reseed policy (EPIC 3 adds a
  reseed-frequency floor here — AC-7).
- `qeaas.gate.require_entropy()` — the `503` low-entropy gate; unchanged, still guards premium routes.
- `qeaas.auth.require_api_key()` — peppered-hash validation + `revoked` check; unchanged (auth only).
- `qeaas.redis_client` — atomic Upstash primitives (EPIC 3 adds `INCR/INCRBY … EXPIRE` helpers).
- `qeaas.db` — parameterized psycopg helpers (EPIC 3 adds `usage_log` + `revoke_api_key`).

Repeat the honest framing in docstrings/docs: raw QRNG bits are **never** served; every byte is
DRBG-derived (decision #2). QRNG supplies entropy that seeds a standards DRBG — it does not "defeat
quantum attackers." The anti-raid property follows directly: because served bytes are DRBG output,
request volume is decoupled from pool consumption (AC-6).

### What already exists (integration points)
- `api/main.py` — routes from EPIC 2. `/random` (anon, `bytes` `le=64`), `/dice` (anon), the keyed
  `/v1/random/bytes` + `/v1/seed`, admin `/admin/ingest`. EPIC 3 wraps throttling around the anon
  and keyed routes and adds the admin key routes. Handlers stay thin.
- `api/qeaas/redis_client.py:21` — `incr_counter()` (the DRBG counter) + private `_get_client()`.
  EPIC 3 adds generic atomic helpers on the same client.
- `api/qeaas/keyed_drbg.py:55` — `maybe_reseed()` currently fires on `elapsed >= RESEED_INTERVAL`
  **OR** `outputs_since_reseed >= RESEED_OUTPUT_LIMIT`. The output-limit branch means heavy traffic
  reseeds sooner → pulls pool bytes sooner. AC-7 adds a **minimum interval floor** so the output
  branch cannot fire early.
- `api/qeaas/auth.py:32` — `require_api_key()` returns the `db.ApiKeyRow` (owner/tier/quota).
  EPIC 3 handlers take that row (`Depends`) and apply rate/quota via the new `ratelimit` module.
- `api/qeaas/db.py:124` — `insert_api_key`, `get_api_key_by_hash` (returns `revoked`). EPIC 3 adds
  `revoke_api_key` + `insert_usage_log`.
- `api/sql/002_api_keys.sql` — `api_keys` table (already has `tier`, `daily_quota_bytes`, `revoked`);
  **no migration needed**. EPIC 3 adds `003_usage_log.sql`.
- `api/scripts/mint_key.py` — mint CLI; precedent for the new `revoke_key.py` CLI.

---

## 2. Acceptance criteria (from EPIC 3 stories S3.1/S3.2/S3.3 + "Done when", verbatim intent)

| AC | Requirement (build plan wording) | How it is met | Covered by |
|----|----------------------------------|----------------|------------|
| AC-1 | S3.1 — Per-IP sliding window on `/random` & `/dice`: **60 req/min/IP**, `bytes ≤ 64/req`. | New `ratelimit.check_ip_rate(ip)` — atomic fixed-60s-window counter `rl:ip:{ip}:{minute}` (Q1); over → `429 rate_limited`. `bytes ≤ 64` already enforced by the EPIC 2 `Query(le=64)` on `/random`. | `api/qeaas/ratelimit.py:112` (`check_ip_rate`), called at `api/main.py:75` (`/random`) and `api/main.py:90` (`/dice`); manually verified (60→429 flood, §8). |
| AC-2 | S3.1 — **Global daily ceiling** for anon output (e.g. **5 MB/day**) → `429`. | New `ratelimit.check_anon_daily(nbytes)` — atomic `INCRBY anon:daily:{yyyymmdd}` with TTL; over the ceiling → refund + `429 daily_limit_reached`. Counts bytes served by `/random` (Q5). | `api/qeaas/ratelimit.py:118` (`check_anon_daily`), called at `api/main.py:76`; manually verified with a temporarily-lowered ceiling (200 B) — 3rd request over → `429 daily_limit_reached`, refunded counter held at 192. |
| AC-3 | S3.2 — `api_keys` table stores **hash** of key, `owner`, `tier`, `daily_quota_bytes`, `revoked`. | Already shipped in EPIC 2 (`sql/002_api_keys.sql`, `db.insert_api_key`, peppered-hash storage). No change. | `api/sql/002_api_keys.sql:3` (unchanged). |
| AC-4 | S3.2 — Middleware: validate `X-API-Key`, enforce **per-key daily quota** via Upstash TTL counter, **per-key rate limit**. | Validation exists (`auth.require_api_key`). EPIC 3 adds `ratelimit.enforce_key(row, size)` — per-key rate window `rl:key:{hash}:{minute}` + daily quota `quota:key:{hash}:{yyyymmdd}` (INCRBY size, refund + `429` if over), called by `/v1/random/bytes` and `/v1/seed`. | `api/qeaas/ratelimit.py:124` (`enforce_key`), called at `api/main.py:105` and `api/main.py:121`; manually verified — quota=100 key: 2nd 64-byte request → `429 quota_exceeded`; 122 rapid requests on default tier (120/min) → `429 rate_limited`. |
| AC-5 | S3.2 — Tiers: `default` (small daily quota) vs `iot`/`trusted` (higher). | `ratelimit.TIER_QUOTAS` + `TIER_RATE_LIMITS` maps. A row's explicit `daily_quota_bytes` wins; `NULL` falls back to the tier default (Q3). Unknown tier → treated as `default`. | `api/qeaas/ratelimit.py:30` (`TIER_QUOTAS`), `:36` (`TIER_RATE_LIMITS`), `:69` (`_quota_for`), `:75` (`_rate_for`); manually verified an `iot`-tier key with `NULL` `daily_quota_bytes` resolves to the 10 MB default (`psql` row check). |
| AC-6 | S3.3 — Output is DRBG-derived → huge volume costs near-zero QRNG bits; **document** as the core anti-raid property. | Doc section in `qrng-eaas/README.md` + `ratelimit.py` module docstring: served bytes = `keyed_drbg.output()`, so pool consumption is driven only by the time-boxed reseed, never by request count. | `qrng-eaas/README.md` "Anti-abuse & bit-drain (EPIC 3)" section; `api/qeaas/ratelimit.py:1-13` module docstring. |
| AC-7 | S3.3 — **Cap reseed frequency** so even unlimited traffic can't accelerate pool drain. | `keyed_drbg.py`: add `RESEED_MIN_INTERVAL_SECONDS` floor; `maybe_reseed()` will not rotate (even when `outputs_since_reseed >= RESEED_OUTPUT_LIMIT`) until at least the floor has elapsed since the last rotation. Drain becomes a function of wall-clock, not traffic. | `api/qeaas/keyed_drbg.py:32` (`RESEED_MIN_INTERVAL_SECONDS`), `:58-64` (`maybe_reseed` gating); manually verified with floor=20s/limit=5: 8 rapid outputs at elapsed<20s → `drbg_reseeds` stayed `0`; same key after floor elapsed → `drbg_reseeds` → `1`. |
| AC-8 | S3.3 — `usage_log` for spotting abuse; ability to **revoke a key instantly**. | New `sql/003_usage_log.sql` + `db.insert_usage_log(principal, endpoint, bytes)` written on keyed issues (Q7). Revocation: `db.revoke_api_key(key_hash)` via `POST /admin/keys/revoke` **and** `revoke_key.py` CLI; effect is immediate because `require_api_key` reads the row fresh from Neon every request (no caching). | `api/sql/003_usage_log.sql`; `api/qeaas/db.py:159` (`insert_usage_log`), `:149` (`revoke_api_key`); `api/main.py:186` (`/admin/keys/revoke`); `api/scripts/revoke_key.py`; manually verified — `usage_log` row appeared after a keyed issue, revoke → next request `401 invalid_api_key`, `revoke_key.py --owner` also confirmed. |
| AC-9 | EPIC 2 Q4 carry-over — `POST /admin/keys` HTTP mint route (admin token). | `main.py` `POST /admin/keys` (`Depends(require_admin)`) → `secrets.token_urlsafe(32)` → `auth.hash_api_key` → `db.insert_api_key` → returns the plaintext key **once**. Same logic as `mint_key.py`. | `api/main.py:173-183`; manually verified — mint returns a working plaintext key; bad `X-Admin-Token` → `401 unauthorized`. |
| AC-10 | "Done when": hammering `/random` hits `429`, **not the pool**. | Verified: a loop past the per-IP window returns `429`; `pool_bytes_remaining` in `/health` is unchanged across the flood (output is DRBG-derived + reseed floor). | Manually verified: 62-request flood → 60×`200` then 2×`429 rate_limited` with `Retry-After`; `pool_bytes_remaining` unchanged before/after (87468→87468, only the one-time bootstrap pull earlier). |
| AC-11 | "Done when": an over-quota API key is refused; a **revoked key stops working immediately**. | Verified: consume past the key's daily quota → `429 quota_exceeded`; revoke the key → the very next request → `401 invalid_api_key`. | Manually verified (see AC-4/AC-8 evidence above). |
| AC-12 | "Done when": pool drain is **decoupled from request volume**. | Verified: sustained traffic for > `RESEED_OUTPUT_LIMIT` outputs within the floor window does **not** trigger an extra reseed / pool pull (AC-7); pool draws only on the fixed schedule. | Manually verified (see AC-7 evidence above): pool pulled exactly `RESEED_PULL_BYTES` once, only after the floor elapsed. |

---

## 3. Scope

### In scope (backend / `api/` only)
- **Public throttling (S3.1):** per-IP fixed-window rate limit + global daily anon output ceiling on
  `/random` and `/dice`; both `429` on over-limit with a `Retry-After` header.
- **Keyed throttling (S3.2):** per-key rate limit + per-key daily quota (bytes) on `/v1/random/bytes`
  and `/v1/seed`; tier-driven defaults (`default` / `iot` / `trusted`).
- **New `qeaas/ratelimit.py`** policy module: tier tables, IP/key rate checks, anon daily ceiling,
  per-key quota consumption, and a `client_ip(request)` helper (Vercel `X-Forwarded-For` aware).
- **New atomic Redis primitives** in `qeaas/redis_client.py` (`incr_expire`, `incrby_expire`, `decrby`).
- **Reseed-frequency floor (S3.3, AC-7)** in `qeaas/keyed_drbg.py`.
- **`usage_log`** (S3.3): `sql/003_usage_log.sql` + `db.insert_usage_log`, written for keyed issues.
- **Revocation (S3.3):** `db.revoke_api_key`, `POST /admin/keys/revoke`, `scripts/revoke_key.py`.
- **`POST /admin/keys`** HTTP mint route (EPIC 2 Q4 carry-over).
- **Pydantic schemas** for the two new admin routes + a `429` in the error envelope.
- **Docs:** anti-raid / bit-drain section in `qrng-eaas/README.md` (AC-6).

### Out of scope (deferred to their epics — do not implement here)
- **Automated tests of any kind** (project directive).
- **ML-KEM bodies** (`/v1/kem/keypair`, `/v1/kem/encapsulate`) → EPIC 4. The keypair stub is left
  untouched and **not** quota-wrapped here (it takes no API key yet); throttling it is EPIC 4's job.
- **Signed receipts + `entropy_epoch` provenance / `issue_log`** → EPIC 9. EPIC 3 writes `usage_log`
  (abuse metadata) only; it does **not** touch `issue_log` or receipts.
- **Live Neon/Upstash + Vercel deploy** and real client-IP verification behind Vercel's proxy → EPIC 6
  (EPIC 3 reads `X-Forwarded-For` defensively; the deploy proves it end-to-end).
- **Web-side `429` UX** (friendly "slow down" states, retry banners) → EPIC 5 polish.
- **Admin dashboard for key usage / pool level** → Stretch `[COULD]`.
- **Changing EPIC 1/2 behaviour** beyond the reseed floor and the added throttle calls.

---

## 4. Endpoint & throttle contracts (concrete)

Error envelope unchanged (flat `{"error": "<slug>"}`, EPIC 2 §4). EPIC 3 adds `429` slugs. Every
`429` response carries a `Retry-After` header (seconds).

| Route | Auth | New EPIC 3 checks (in order) | New error cases |
|-------|------|------------------------------|-----------------|
| `GET /random?bytes=N` | none | `check_ip_rate(ip)` → `check_anon_daily(N)` | over IP window → `429 rate_limited`; over daily ceiling → `429 daily_limit_reached` |
| `POST /dice` | none | `check_ip_rate(ip)` | over IP window → `429 rate_limited` |
| `GET /v1/random/bytes?size=N` | API key | `enforce_key(row, N)` = per-key rate → per-key daily quota; then issue + `insert_usage_log` | over key rate → `429 rate_limited`; over daily quota → `429 quota_exceeded` |
| `GET /v1/seed?bytes=N` | API key | same as `/v1/random/bytes` (alias, `bytes`→`size`) | same |
| `POST /admin/keys` | admin token | — | bad token → `401 unauthorized` (existing) |
| `POST /admin/keys/revoke` | admin token | — | bad token → `401`; unknown `key_hash` → `404 not_found` |

Ordering rationale: rate limit before quota (a flood is cheaper to reject on a per-minute counter than
on the daily quota INCRBY). Both run **after** `require_api_key` (auth) and **after** `require_entropy`
(the `503` gate stays first for premium routes, matching EPIC 2).

### Redis keys (Upstash) — extends the build-plan data model
| Key | Op | TTL | Purpose |
|-----|----|----|---------|
| `drbg:counter` | `INCR` | none | existing DRBG output counter (unchanged) |
| `rl:ip:{ip}:{yyyymmddHHMM}` | `INCR` + `EXPIRE 60` | 60 s | per-IP fixed-minute window (S3.1) |
| `rl:key:{hash}:{yyyymmddHHMM}` | `INCR` + `EXPIRE 60` | 60 s | per-key fixed-minute window (S3.2) |
| `anon:daily:{yyyymmdd}` | `INCRBY N` + `EXPIRE` | to next UTC midnight | global anon output ceiling (S3.1) |
| `quota:key:{hash}:{yyyymmdd}` | `INCRBY N` + `EXPIRE` | to next UTC midnight | per-key daily byte quota (S3.2) |

The minute/day buckets are computed from `datetime.now(timezone.utc)` in Python. Fixed-window (not a
sorted-set sliding window) keeps every check a single atomic `INCR`/`INCRBY` — serverless-safe and
race-free, the same discipline as the DRBG counter (Q1). Over-limit on a byte counter **refunds**
(`DECRBY N`) before raising so a rejected request does not permanently consume quota.

### Tier defaults (S3.2, AC-5 — Q3/Q4 resolved)
| Tier | `daily_quota_bytes` default | per-key rate limit |
|------|-----------------------------|--------------------|
| `default` | 256 KB/day (`262_144`) | 120 req/min |
| `iot` | 10 MB/day (`10_485_760`) | 600 req/min |
| `trusted` | 500 MB/day (`524_288_000`) | 1_200 req/min |

A row's explicit `daily_quota_bytes` (set at mint time) overrides the tier default; `NULL` → tier
default. Anon (`/random`) global ceiling = **5 MB/day**; per-IP = **60 req/min**.

---

## 5. Design decisions carried from the epic (do not re-litigate)
- Pure-Python deps only — **no new runtime dependency** (uses the existing `redis` client, `psycopg`,
  and stdlib `datetime`/`secrets`/`hmac`).
- Serverless-safe throttling: only atomic Redis ops (`INCR`/`INCRBY`/`EXPIRE`/`DECRBY`); no
  read-modify-write, no in-process state (matches the keyed-DRBG counter pattern).
- Raw QRNG bits are never served; throttling bounds **DRBG output volume**, and the reseed floor
  bounds pool drain — the two are deliberately decoupled (AC-6/AC-12, decision #6/#3).
- Keep `main.py` handlers **thin**: they call `ratelimit.*` / `auth.*` / `generation.*` / `db.*` and
  return a schema. No counter arithmetic, tier logic, IP parsing, or hashing in `main.py` or Twig-like
  layers.
- No raw SQL string interpolation; `usage_log` and `revoke` queries are parameterized in `db.py`.
- Honest framing repeated in the new module docstrings and the README anti-raid section.
- Fail-open vs fail-closed on Redis outage: **fail-open** for anon throttling (availability of the toy
  dice matters more than a hard cap; the reseed floor still protects the pool) and **fail-closed is
  not required** — but see Q6; default is fail-open with a logged warning.

---

## 6. File plan (concrete paths)

All new/edited Python: `from __future__ import annotations`, PEP 8, full type hints, module docstrings
repeating the honest framing where relevant. **No test files** are created (project directive).

| File | Change |
|------|--------|
| `api/qeaas/ratelimit.py` | **New.** Policy module. Constants: `ANON_IP_PER_MIN=60`, `ANON_DAILY_BYTES=5*1024*1024`, `TIER_QUOTAS`/`TIER_RATE_LIMITS` maps (§4). Functions: `client_ip(request) -> str` (leftmost `X-Forwarded-For`, else `request.client.host`, else `"unknown"`); `check_ip_rate(ip) -> None`; `check_anon_daily(nbytes) -> None`; `enforce_key(row: db.ApiKeyRow, size: int) -> None` (per-key rate then quota, using `_quota_for(row)`/`_rate_for(row)` off the tier maps); `_quota_for`/`_rate_for` helpers. All over-limit paths raise `ApiError(429, <slug>)` after refunding byte counters. Uses `redis_client` primitives + `datetime.now(timezone.utc)` for bucket keys + `_seconds_until_utc_midnight()` for daily TTL. Docstring documents the anti-raid property (AC-6). |
| `api/qeaas/redis_client.py` | **Edit.** Add generic atomic helpers on the shared client: `incr_expire(key: str, ttl: int) -> int` (INCR; set EXPIRE only when the returned count is 1), `incrby_expire(key: str, amount: int, ttl: int) -> int`, `decrby(key: str, amount: int) -> int`. Keep `incr_counter`/`COUNTER_KEY` unchanged. |
| `api/qeaas/keyed_drbg.py` | **Edit (AC-7).** Add `RESEED_MIN_INTERVAL_SECONDS` (e.g. `5 * 60`). In `maybe_reseed()`, gate the `outputs_since_reseed >= RESEED_OUTPUT_LIMIT` branch behind `elapsed >= RESEED_MIN_INTERVAL_SECONDS` (the plain interval branch already implies wall-clock). Net: reseed fires on `elapsed >= RESEED_INTERVAL_SECONDS`, **or** (`outputs_since_reseed >= RESEED_OUTPUT_LIMIT` **and** `elapsed >= RESEED_MIN_INTERVAL_SECONDS`). Update the module docstring to state traffic cannot accelerate drain. |
| `api/qeaas/db.py` | **Edit.** Add `revoke_api_key(key_hash: str) -> bool` (parameterized `UPDATE api_keys SET revoked = true WHERE key_hash = %s`; return `cur.rowcount == 1`) and `insert_usage_log(principal: str, endpoint: str, nbytes: int) -> None` (parameterized INSERT into `usage_log`). No other changes. |
| `api/sql/003_usage_log.sql` | **New.** `CREATE TABLE IF NOT EXISTS usage_log (id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), principal text NOT NULL, endpoint text NOT NULL, nbytes bigint NOT NULL DEFAULT 0);` + an index `CREATE INDEX IF NOT EXISTS usage_log_principal_ts ON usage_log (principal, ts);`. Matches the build-plan `usage_log` (ts, principal, endpoint, bytes); `principal` = client IP for anon or `key_hash` for keyed. |
| `api/qeaas/schemas.py` | **Edit.** Add `AdminKeyRequest{owner: str, tier: str = "default", daily_quota_bytes: int | None = None}`, `AdminKeyResponse{api_key: str, owner: str, tier: str, daily_quota_bytes: int | None}`, `AdminRevokeRequest{key_hash: str}`, `AdminRevokeResponse{key_hash: str, revoked: bool}`. |
| `api/main.py` | **Edit.** (1) `/random`: inject `Request`; `ratelimit.check_ip_rate(ratelimit.client_ip(request))` then `ratelimit.check_anon_daily(bytes)` before generating. (2) `/dice`: inject `Request`; `check_ip_rate(...)`. (3) `/v1/random/bytes` + `/v1/seed`: change `Depends(require_api_key)` from a bare dependency to a **named param** `key: db.ApiKeyRow = Depends(require_api_key)`; call `ratelimit.enforce_key(key, size)` before `_issue_v1`, then `db.insert_usage_log(key.key_hash, "/v1/random/bytes", size)` after. (4) `POST /admin/keys` (`Depends(require_admin)`, `AdminKeyRequest`) → mint + return `AdminKeyResponse`. (5) `POST /admin/keys/revoke` (`Depends(require_admin)`, `AdminRevokeRequest`) → `db.revoke_api_key`; `404 not_found` if it returned `False`. Handlers stay thin; **leave `/v1/kem/keypair` stub untouched** (EPIC 4). |
| `api/scripts/revoke_key.py` | **New.** CLI mirroring `mint_key.py`: `python -m scripts.revoke_key --owner <name>` (look up + revoke all of an owner's keys) **or** `--key-hash <hash>`; prints how many rows were revoked. Convenience for local/ops revocation alongside the admin route. |
| `api/qeaas/errors.py` | **No change.** `429` flows through the existing `ApiError` handler; `Retry-After` is set by the raiser (see Q2/§7). |
| `qrng-eaas/README.md` | **Edit.** Add an "Anti-abuse & bit-drain" section (AC-6): the three defences, the Redis key table, tier defaults, and the honest anti-raid statement (DRBG output → volume decoupled from pool; reseed floor caps drain). |
| `api/.env.example` | **Edit (optional).** If limits are made env-overridable (Q4), document them; otherwise add a one-line comment pointing at the `ratelimit.py` constants. Default: constants live in `ratelimit.py` like the `keyed_drbg` reseed constants — no new env vars. |

**No business logic in `main.py`** — handlers validate via Pydantic/`Depends` and delegate.

---

## 7. Rate-limit / quota algorithm detail

**Per-IP / per-key rate window (fixed 60 s bucket):**
```
bucket = now_utc.strftime("%Y%m%d%H%M")          # minute granularity
key    = f"rl:ip:{ip}:{bucket}"                  # or rl:key:{hash}:{bucket}
count  = redis_client.incr_expire(key, ttl=60)   # INCR; EXPIRE 60 only when count == 1
if count > limit:
    raise ApiError(429, "rate_limited")           # + Retry-After: seconds to next minute
```

**Global anon ceiling / per-key daily quota (byte counter):**
```
day    = now_utc.strftime("%Y%m%d")
key    = f"anon:daily:{day}"                      # or quota:key:{hash}:{day}
ttl    = seconds_until_utc_midnight()
total  = redis_client.incrby_expire(key, nbytes, ttl)   # INCRBY; EXPIRE on first write
if total > ceiling:
    redis_client.decrby(key, nbytes)              # refund — a rejected request keeps quota
    raise ApiError(429, "daily_limit_reached")     # or "quota_exceeded" for keys; + Retry-After
```

- `Retry-After`: for a minute window, seconds until the next minute boundary; for a daily counter,
  `seconds_until_utc_midnight()`. Set on the `429` `JSONResponse` (see Q2 for where the header is
  attached — proposed: `ApiError` gains an optional `headers` field so the existing handler emits it).
- Every counter check is one atomic Redis call; no read-then-write races on stateless serverless.
- `bytes ≤ 64/req` on `/random` (S3.1) is already enforced by the EPIC 2 `Query(le=64)` — no new code.
- Reseed floor (AC-7) is orthogonal to these counters: it lives in `keyed_drbg.maybe_reseed()` and
  ensures the *pool* is untouched by volume even if a caller somehow saturates the DRBG counters.

---

## 8. Verification (manual — no automated tests)

Per the project directive there are **no automated tests**. Verify by hand against an ephemeral
Postgres + Redis (Docker `postgres:16-alpine` / `redis:7-alpine`, as EPIC 2 did) with `MASTER_KEY`,
`ADMIN_TOKEN`, `DATABASE_URL`, `REDIS_URL` set, schema applied (`001`,`002`,`003`), pool seeded:

- **AC-1 / AC-10:** loop `curl 'localhost:8000/random?bytes=64'` > 60×/min from one IP → first 60 → `200`,
  then `429 {"error":"rate_limited"}` with `Retry-After`. Compare `/health` `pool_bytes_remaining`
  before/after the flood → **unchanged** (429 hits Redis, not the pool).
- **AC-2:** temporarily lower `ANON_DAILY_BYTES`; pull enough anon bytes to exceed it →
  `429 {"error":"daily_limit_reached"}`; `redis-cli GET anon:daily:<today>` shows it did not exceed
  the ceiling after the refund.
- **AC-4 / AC-11 (quota):** mint a key with a tiny `--quota`; pull past it via `/v1/random/bytes` →
  `429 {"error":"quota_exceeded"}`. Mint an `iot`-tier key with `NULL` quota → confirm it uses the
  50 MB tier default.
- **AC-4 (key rate):** exceed the per-key per-minute limit → `429 {"error":"rate_limited"}`.
- **AC-11 (revoke):** `POST /admin/keys/revoke {key_hash}` (or `revoke_key.py`) → the very next
  `/v1/random/bytes` with that key → `401 {"error":"invalid_api_key"}`. Also confirm
  `POST /admin/keys` mints a working key returned once in plaintext, and a bad admin token → `401`.
- **AC-5:** `psql` the minted rows to confirm tier + quota; hit each tier's limit.
- **AC-7 / AC-12:** set `RESEED_OUTPUT_LIMIT` low and `RESEED_MIN_INTERVAL_SECONDS` high; drive many
  outputs quickly → confirm `drbg_root` gains **no** new row (no reseed / no pool pull) until the floor
  elapses; `entropy_pool` `consumed_offset` unchanged during the burst.
- **AC-8:** after keyed requests, `SELECT * FROM usage_log` shows one row per issue with the right
  `principal`/`endpoint`/`nbytes`.
- **AC-6:** README section renders and states the anti-raid property.
- Confirm every new error body is the flat `{"error":"<slug>"}` envelope with `Retry-After` on 429s.

---

## 9. Definition of done (EPIC 3 "Done when")
- [x] Hammering `/random`/`/dice` from one IP returns `429`, and the QRNG pool is untouched (AC-1/10).
- [x] Anon output past the global daily ceiling returns `429` (AC-2).
- [x] An over-quota API key is refused `429`; a revoked key fails `401` on its very next request
      (AC-4/AC-11).
- [x] Tiers `default`/`iot`/`trusted` resolve the right quota + rate limit; explicit `daily_quota_bytes`
      overrides the tier default (AC-5).
- [x] Reseed cannot be accelerated by traffic — pool drain is a function of wall-clock only (AC-7/12).
- [x] `usage_log` records keyed issues; `POST /admin/keys` mints and `POST /admin/keys/revoke` /
      `revoke_key.py` revoke (AC-8/AC-9).
- [x] All throttling uses only atomic Redis ops; handlers stay thin; raw QRNG bits never served.
- [x] README anti-raid section written (AC-6); manual verification (§8) done; **no tests written**.

---

## 11. Open questions — RESOLVED

All defaults accepted; Q3's two lower tiers shrunk per developer instruction.

- **Q1 — Rate-limit algorithm → fixed 60 s window.** `INCR` a per-minute bucket key + `EXPIRE 60`:
  a single atomic op, serverless-safe, matching the DRBG-counter pattern. No sorted-set sliding window.
- **Q2 — `Retry-After` on 429s → `ApiError.headers`.** `ApiError` gains an optional
  `headers: dict[str, str] | None`; the existing `errors.py` handler passes it to
  `JSONResponse(headers=...)`. Flat envelope preserved.
- **Q3 — Tier quotas → lower tiers shrunk.** `default`=**256 KB/day** (`262_144`),
  `iot`=**10 MB/day** (`10_485_760`), `trusted`=500 MB/day (`524_288_000`). A row's explicit
  `daily_quota_bytes` overrides; `NULL` → tier default; unknown tier → `default`. Anon global ceiling
  = 5 MB/day.
- **Q4 — Per-key rate limits + config location → accepted.** `default`=120, `iot`=600,
  `trusted`=1200 req/min; anon per-IP=60 req/min. All limits are **module constants in `ratelimit.py`**
  (like the `keyed_drbg` reseed constants) — no new env vars.
- **Q5 — Anon daily ceiling scope → `/random` bytes only.** `/dice` is per-IP rate-limited but not
  byte-metered (negligible internal draw).
- **Q6 — Redis outage → fail-open everywhere.** On a Redis error, log a warning and allow the request;
  the reseed floor still guarantees the pool can't be drained.
- **Q7 — `usage_log` scope → keyed issues + admin mint/revoke only.** High-volume anon `/random`/`/dice`
  are **not** logged to Neon (anon abuse is visible via the Redis counters).

---

## 12. Post-Implementation

Built exactly per plan, no deviations from the file plan or the resolved §11 decisions.

- New `api/qeaas/ratelimit.py`: `client_ip`, `check_ip_rate`, `check_anon_daily`, `enforce_key`,
  `_quota_for`/`_rate_for`, tier tables, all atomic Redis ops with fail-open + logged warning on
  Redis errors (Q6).
- `api/qeaas/redis_client.py`: added `incr_expire`, `incrby_expire`, `decrby`.
- `api/qeaas/keyed_drbg.py`: added `RESEED_MIN_INTERVAL_SECONDS` floor gating the output-limit
  reseed branch; docstring updated.
- `api/qeaas/db.py`: added `revoke_api_key`, `insert_usage_log`, and
  `get_api_key_hashes_by_owner` (the latter needed by `revoke_key.py --owner`, implied by the
  file plan's own description of that script but not separately called out — added as the
  minimal parameterized helper to support it, consistent with "no raw SQL in scripts").
- `api/sql/003_usage_log.sql`: new `usage_log` table + index.
- `api/qeaas/schemas.py`: `AdminKeyRequest`/`AdminKeyResponse`/`AdminRevokeRequest`/`AdminRevokeResponse`.
- `api/qeaas/errors.py`: `ApiError` gained an optional `headers` field (Q2), passed through to
  `JSONResponse` so `429`s carry `Retry-After`.
- `api/main.py`: `/random` and `/dice` now rate-limit by IP; `/random` also enforces the anon
  daily ceiling; `/v1/random/bytes` and `/v1/seed` take the API-key row as a named `Depends`
  param, call `enforce_key`, then `insert_usage_log`; added `POST /admin/keys` and
  `POST /admin/keys/revoke`. `/v1/kem/keypair` left untouched (EPIC 4).
- `api/scripts/revoke_key.py`: new CLI, `--owner` or `--key-hash`.
- `qrng-eaas/README.md`: new "Anti-abuse & bit-drain (EPIC 3)" section; updated the mint-key and
  revoke-key walkthrough steps and the edge-case table with the new `429`/`404` cases.
- `api/scripts/dev_db_up.sh`: now also applies `sql/003_usage_log.sql` (needed for §8 verification
  against `001`+`002`+`003`; not in the original file plan table but required infrastructure for
  the plan's own verification steps).
- `api/.env.example`: one-line comment pointing at `ratelimit.py` constants (no new env vars).

**Manual verification performed** (throwaway `postgres:16-alpine` / `redis:7-alpine` via
`scripts/dev_db_up.sh`, real app via `uvicorn`): every item in §8 was driven end-to-end, including
temporarily lowering `ANON_DAILY_BYTES` and the reseed constants to force the over-limit and
reseed-floor paths within a short test window, then reverting them before hand-back. No automated
tests were written or run.

**Follow-ups for the developer:**
- No test suite exists for this module by design (project directive). If EPIC 6's live
  Neon/Upstash deploy surfaces different real-world IP header behavior behind Vercel's proxy,
  `ratelimit.client_ip` may need revisiting — it currently trusts the leftmost `X-Forwarded-For`
  entry unconditionally, which is fine for this epic's scope but is exactly the concern EPIC 6
  flagged as out of scope here.
- `iot`/`trusted` tier keys were only exercised for tier-resolution (NULL quota → default) and
  rate-limit accounting; a full 10 MB / 500 MB daily-quota flood was not run (impractical
  locally) — the code path is identical to the `default`-tier quota test that was run to
  exhaustion, so this is a coverage note, not a gap in confidence.
