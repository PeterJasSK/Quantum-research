# Feature Plan — EPIC 2: Public API surface

**Status:** Complete
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 2 `[MUST]`
**Interpretation of "part 2":** EPIC 2. "Part 1" was EPIC 1 (entropy core), now **Complete**
(`feature-epic1-entropy-core.md`). EPIC 0 (scaffold + ML-KEM spike) is done. The next `[MUST]`
in build order is the HTTP surface that exposes the EPIC 1 engine: clean, documented,
Pydantic-typed endpoints with a consistent error envelope and CORS, rendered by FastAPI's
auto-OpenAPI at `/docs`.

> **No tests (project directive).** This plan does **not** plan, write, or maintain automated
> tests, and `/implement-feature` will not run or create any. Verification is manual only
> (`/docs`, `curl`, the running app). Existing EPIC 1 tests under `api/tests/` are left as-is and
> out of scope here.

> **Note on process:** this repo has no GitHub issues, no `tasks/plans/` tree, and no
> `_plan-template.md`. The global `/plan-feature` template (GitHub issues, Doctrine, PSR-12,
> councils) does not apply. This plan follows the shape established by
> `feature-epic1-entropy-core.md` and the project's real conventions (Python 3.13, FastAPI,
> `from __future__ import annotations`, full type hints, pure-Python deps, no raw SQL string
> interpolation, honest QRNG framing).

> **Developer decisions folded in (§11):** (Q1) **flat** error envelope `{"error": "<slug>"}`;
> (Q2) **real API-key hash-validation + revocation pulled forward** into EPIC 2 — but per-key
> quota / rate-limiting / `429` stay in EPIC 3; (Q3) populate `entropy_epoch` now, `receipt`
> deferred to EPIC 9; (Q4) `POST /admin/keys` deferred to EPIC 3 (a local `mint_key.py` CLI seeds
> dev keys meanwhile); (Q5) `/admin/ingest` is a real **multipart `.txt` upload, ≤ 10 MB**;
> (Q6) dice `sides` **2–100** (adjustable), `count` **1–6** dice per throw.

---

## 1. Context & goal

Put a clean HTTP surface on the EPIC 1 engine. The engine is done and ready to call:

- `qeaas.keyed_drbg.output(n, additional=b"") -> bytes` — serverless-safe DRBG bytes (Redis
  counter + Neon root_key + reseed). **This is the one source of served randomness.**
- `qeaas.gate.entropy_level()` / `require_entropy()` — the low-entropy gate + FastAPI dependency.
- `qeaas.pool.ingest_bits_file(path, source_label)` / `parse_bits_file(path)` — parse `0/1` txt →
  encrypt → store a pool chunk.
- `qeaas.pool.derive_subkey(name)` — HKDF-SHA256 subkey from `MASTER_KEY` (reused as the API-key
  pepper: `derive_subkey("api-key-pepper")`).
- `qeaas.db.*` — parameterized psycopg helpers.

EPIC 2 adds routes, request/response schemas, the error envelope, CORS, and — per Q2 — the
**`api_keys` table + hash-based key validation** so `/v1/random/bytes` is genuinely authenticated.
It does **not** add per-key quota/rate-limiting (EPIC 3), ML-KEM bodies (EPIC 4), or signed
receipts / provenance resolution (EPIC 9); those stay clearly-marked seams the owning epic replaces
— the same pull-forward-the-minimum discipline EPIC 1 used with EPIC 10.

Repeat the honest framing in docstrings: **raw QRNG bits are never served; every byte returned is
DRBG-derived** (decision #2). QRNG supplies entropy that seeds a standards DRBG; it does not
"defeat quantum attackers."

### What already exists (integration points)
- `api/main.py` — FastAPI app `"Quantum Entropy-as-a-Service"`; routes: `GET /health` (full body),
  `GET /v1/seed` **stub** (gated, `{"stub": true}`), `POST /v1/kem/keypair` **stub** (gated);
  `X-Quantum-Entropy` response-header middleware. EPIC 2 replaces the `/v1/seed` stub with the real
  alias and adds the remaining routes. `/v1/kem/keypair` stays a stub (EPIC 4).
- `api/qeaas/keyed_drbg.py` — `output()`, reseed constants. No change.
- `api/qeaas/gate.py` — `entropy_level()`, `require_entropy()`. Reused as the premium-route gate.
- `api/qeaas/pool.py` — `ingest_bits_file()`, `parse_bits_file()`, `derive_subkey()`. Reused.
- `api/qeaas/db.py` — DB helpers. EPIC 2 adds `api_keys` helpers alongside.
- `api/scripts/ingest_bits.py` — CLI precedent for the new `mint_key.py`.
- **Legacy rejection-sampling reference:** `BC/bakalarska-praca-main/quantum_rng/rng/utils/utils.py:115`
  `generate_numbers(bitstream, min_val, max_val)` — the modulo-bias-free algorithm S2.1 says to
  reuse (`bits_needed = ceil(log2(n))`, reject `>= n`). **Port** its logic; do not import from `BC/`.

---

## 2. Acceptance criteria (from EPIC 2 stories S2.1/S2.2 + "Done when", verbatim intent)

| AC | Requirement (build plan wording) | Covered by |
|----|----------------------------------|------------|
| AC-1 | `GET /health` → `{status, quantum_entropy_level, pool_bytes_remaining, drbg_reseeds, uptime}` | `api/main.py:54-63` wraps the unchanged fields in `schemas.HealthResponse`. Verified: `curl /health` → 200 with all five fields. |
| AC-2 | `GET /random?bytes=N` → DRBG bytes (base64). **Anon**, capped small (`N ≤ 64`). Powers dice. | `api/main.py:66-73` (`random_endpoint`) + `schemas.RandomResponse`. Ungated — verified healthy *and* degraded pool both return 200. Verified: `bytes=64` → 200; `bytes=65` → `422`. |
| AC-3 | `POST /dice` `{sides, count}` → rolls; uses `/random` internally; **rejection sampling** to avoid modulo bias. | `api/qeaas/dice.py:20-38` (`roll()`, ports `generate_numbers`, draws via `keyed_drbg.output`) + `api/main.py:75-80` + `DiceRequest`/`DiceResponse`. Verified: `{sides:6,count:6}` → 6 rolls in `1..6`; `count:7` → `422`. |
| AC-4 | `GET /v1/random/bytes?size=N&format=hex\|base64` → `{request_id, format, data, entropy_epoch, timestamp, receipt}`. **API key required**, `32 ≤ N ≤ 4096`, quota-metered. **Canonical** dev endpoint. | `api/main.py:86-96` + `schemas.V1RandomBytesResponse` + **real** `auth.require_api_key` (`api/qeaas/auth.py:31-36`, peppered-hash lookup + revoked check, Q2). Verified against a real Postgres/Redis: no key → `401 missing_api_key`; valid key → `200` with all six fields (`receipt: null`); revoked key → `401 invalid_api_key`; `size=31` → `422`. Per-key **quota metering deferred to EPIC 3**. |
| AC-5 | `GET /v1/seed?bytes=N` → **alias** of `/v1/random/bytes` (same engine, same limits). | `api/main.py:97-104` (`seed`) calls the same `_issue_v1`/`generation.issue_v1` as AC-4, replacing the EPIC 1 stub. Verified: `curl /v1/seed?bytes=64` with a valid key → 200, same shape as AC-4. |
| AC-6 | `POST /v1/verify` `{request_id \| receipt}` → signed provenance metadata. **Not** a value-confirmation oracle. | `api/main.py:106-114` + `VerifyRequest`/`VerifyResponse`; returns an unsigned provenance stub (real signing = EPIC 9, Q3). Verified: `{"request_id":"abc"}` → 200 stub body; `{}` → `422`. |
| AC-7 | `POST /admin/ingest` → upload fresh `0/1` bits file to refill the pool (**admin token**). | `api/main.py:117-145` (admin-guarded via `auth.require_admin`) → real multipart `.txt` upload ≤ 10 MB → `pool.parse_bits_file`/`pool.ingest_bits_file` (Q5). Verified: wrong token → `401`; small valid `.txt` → `200` with `pool_bytes_remaining` increased; non-`0/1` content → `422`; > 10 MB file → `413`. |
| AC-8 | `POST /admin/keys` → mint an API key (**admin token**). | **Deferred to EPIC 3** (Q4). `api/sql/002_api_keys.sql` (table) + `auth.require_admin` + `api/scripts/mint_key.py` ship now to seed dev keys; verified end-to-end (`python -m scripts.mint_key --owner devtest` produced a working key). HTTP mint route lands in EPIC 3. |
| AC-9 | Pydantic models for **every** request/response. | `api/qeaas/schemas.py` (`HealthResponse`, `RandomResponse`, `DiceRequest`/`DiceResponse`, `V1RandomBytesResponse`, `VerifyRequest`/`VerifyResponse`, `AdminIngestResponse`). |
| AC-10 | Consistent error envelope. | `api/qeaas/errors.py` — **flat** `{"error": "<slug>"}` (Q1) via `ApiError`/`HTTPException`/`RequestValidationError` handlers, matching the existing gate detail. Verified every error case above returned this shape. |
| AC-11 | CORS for the web origin. | `api/main.py:32-39`, `CORSMiddleware` with origins from `WEB_ORIGIN` env (default `http://localhost:3000`). Verified: `OPTIONS /random` preflight returns `Access-Control-Allow-Origin: http://localhost:3000`. |
| AC-12 | `/docs` renders (FastAPI auto-OpenAPI). | Verified: `GET /docs` → 200, `GET /openapi.json` → 200 listing every new path; all routes fully typed. |
| AC-13 | Error/edge cases return correct codes: bad `bytes`/`size`, missing key, over-quota. | Bad size/format → `422`; missing/invalid/revoked key → `401` (verified above); degraded pool → `503` (pre-existing `require_entropy`, unchanged); admin `/admin/ingest` bad token → `401`, oversize → `413`; over-quota → **EPIC 3**. |

---

## 3. Scope

### In scope
- All EPIC 2 **routes**: `GET /random`, `POST /dice`, `GET /v1/random/bytes`, `GET /v1/seed` (alias),
  `POST /v1/verify` (provenance stub), `POST /admin/ingest` (multipart upload).
- **Pydantic schemas** for every request/response (`qeaas/schemas.py`).
- **Flat error envelope** `{"error": "<slug>"}` + FastAPI exception handlers (`qeaas/errors.py`).
- **CORS** middleware for the web origin (`WEB_ORIGIN` env, localhost default).
- `qeaas/dice.py` — rejection-sampling roll built on `keyed_drbg.output()` (ports `generate_numbers`).
- **API-key authentication, pulled forward (Q2):** `api_keys` table (`002_api_keys.sql`),
  `db.insert_api_key` / `db.get_api_key_by_hash`, and `auth.require_api_key` doing a **real**
  peppered-hash lookup + `revoked` check (401 on missing/unknown/revoked).
- `api/scripts/mint_key.py` — local admin CLI to create a dev API key (prints plaintext once, stores
  hash only) so hash-validation is usable before the EPIC 3 mint endpoint exists.
- `auth.require_admin` (functional, constant-time `ADMIN_TOKEN` compare).
- Wrapping the existing `/health` body in `HealthResponse` without changing its fields.

### Out of scope (deferred to their epics — do not implement here)
- **Automated tests of any kind** (project directive). No test files, no test fixtures, no test runs.
- **Per-key daily quota, rate limiting, and the over-quota `429`** → EPIC 3. `api_keys.daily_quota_bytes`
  column exists (so EPIC 3 needs no migration) but is **not enforced** in EPIC 2.
- **`POST /admin/keys` (HTTP mint)** → EPIC 3 (Q4). The table + CLI exist; the route does not.
- **Signed receipts + `entropy_epoch` provenance resolution** → EPIC 9. `/v1/verify` returns an
  unsigned provenance **stub**; `receipt` in `/v1/random/bytes` is `null` (Q3).
- **ML-KEM bodies** (`/v1/kem/keypair`, `/v1/kem/encapsulate`) → EPIC 4. Existing keypair stub
  untouched; `/v1/kem/encapsulate` not added here.
- **Live Neon/Upstash + Vercel deploy** → EPIC 6.
- **Public rate limiting on `/random` & `/dice`** → EPIC 3 S3.1.

---

## 4. Endpoint contracts (concrete)

Error envelope (AC-10, Q1): every error body is **flat** `{"error": "<slug>"}` — the exact shape the
gate already returns (`{"error": "low_quantum_entropy"}`). Exception handlers normalize
`HTTPException`/`ApiError`/validation errors to this shape.

| Route | Auth | Gated? | Request | Success (200) | Error cases |
|-------|------|--------|---------|---------------|-------------|
| `GET /health` | none | no | — | `HealthResponse` (unchanged fields) | — |
| `GET /random?bytes=N` | none | **no** | query `bytes`, default 32, `1 ≤ N ≤ 64` | `RandomResponse{bytes, format:"base64", data}` | `N` out of range → `422` (`{"error":"bad_request"}`) |
| `POST /dice` | none | **no** | `DiceRequest{sides:int, count:int}` | `DiceResponse{sides, count, rolls:list[int]}` | bad `sides`/`count` → `422` |
| `GET /v1/random/bytes?size=N&format=` | **API key (real)** | **yes** | `size` (`32 ≤ N ≤ 4096`), `format` in {`hex`,`base64`}, default `hex` | `V1RandomBytesResponse{request_id, format, data, entropy_epoch, timestamp, receipt}` | missing/invalid/revoked key → `401`; bad `size`/`format` → `422`; degraded → `503`; over-quota → **EPIC 3** |
| `GET /v1/seed?bytes=N` | **API key (real)** | **yes** | alias — `bytes`→`size`, same bounds | same as `/v1/random/bytes` | same |
| `POST /v1/verify` | none | no | `VerifyRequest{request_id?: str, receipt?: str}` (≥1 required) | `VerifyResponse{request_id, verified, provenance, note}` — **stub** | neither field → `422` |
| `POST /admin/ingest` | **admin token** | no | `multipart/form-data`: `file` (`.txt`, `0/1` only, **≤ 10 MB**), optional `source_label` | `AdminIngestResponse{ingested, bytes_added, pool_bytes_remaining}` | missing/bad token → `401`; > 10 MB → `413`; non-`0/1` / non-`.txt` → `422` |

Notes:
- `entropy_epoch` in `V1RandomBytesResponse` is populated **now** from `drbg_root.reseed_counter`
  (`db.get_root_key().reseed_counter`) — the value `/health` reports as `drbg_reseeds` (Q3).
  `receipt` is reserved and returns `null` in EPIC 2 (real signing = EPIC 9).
- `request_id` = `uuid.uuid4().hex`. `timestamp` = ISO-8601 UTC (`datetime.now(timezone.utc)`).
- `/v1/seed` and `/v1/random/bytes` **share one service function**; the alias just maps `bytes`→`size`
  so it can never drift (AC-5).

### API-key model (Q2, pulled forward)
- Table `api_keys` (build-plan data model): `key_hash text PK`, `owner text`, `tier text default
  'default'`, `daily_quota_bytes bigint`, `revoked boolean default false`, `created_at timestamptz`.
- **Storage rule:** never store the plaintext key. `key_hash = hmac_sha256(pepper, key)` where
  `pepper = pool.derive_subkey("api-key-pepper")`. `mint_key.py` generates a key with
  `secrets.token_urlsafe(32)`, prints it **once**, stores only the hash.
- `require_api_key`: read `X-API-Key`; 401 if absent/empty; compute hash; `db.get_api_key_by_hash`;
  401 if not found or `revoked`; else return the row (owner/tier available to handlers). **No quota
  check** — that's EPIC 3.

---

## 5. Design decisions carried from the epic (do not re-litigate)
- Pure-Python deps only. **One new runtime dep:** `python-multipart` (pure-Python) for the
  `/admin/ingest` `UploadFile` (Q5). Everything else is stdlib (`base64`, `uuid`, `datetime`,
  `secrets`, `hmac`) + the existing `qeaas` engine.
- Raw QRNG bits are never served; every served byte is `keyed_drbg.output()`-derived (decision #2).
- Serverless-safe: no per-request DRBG state; `output()` already handles counter/reseed.
- Keep `main.py` route handlers **thin** — Pydantic parse/validate, delegate to `qeaas` functions,
  return a schema. No business logic (bit-packing, sampling, auth, hashing) in `main.py`.
- No raw SQL string interpolation; every `api_keys`/pool query parameterized in `db.py`.

---

## 6. File plan (concrete paths)

All new Python: `from __future__ import annotations`, PEP 8, full type hints, module docstrings
repeating the honest framing where relevant. **No test files** are created (project directive).

| File | Change |
|------|--------|
| `api/qeaas/schemas.py` | **New.** Pydantic models (AC-9): `HealthResponse`, `RandomResponse`, `DiceRequest` (`sides` `Field(ge=2, le=100)`, `count` `Field(ge=1, le=6)` — Q6), `DiceResponse`, `V1RandomBytesResponse`, `VerifyRequest` (validator requiring ≥1 of `request_id`/`receipt`), `VerifyResponse`, `AdminIngestResponse`. `Format = Literal["hex","base64"]`. |
| `api/qeaas/errors.py` | **New.** `ApiError(Exception)` carrying `status_code` + `code` (slug); `register_error_handlers(app)` for `ApiError`, `HTTPException` (map `detail` → `{"error": <slug>}`, preserving the gate's `low_quantum_entropy`), and `RequestValidationError` (→ `422` `{"error":"bad_request"}`). **Flat** envelope (Q1). |
| `api/qeaas/dice.py` | **New.** `roll(sides: int, count: int) -> list[int]` (AC-3): rejection sampling ported from `generate_numbers` — `bits_needed = ceil(log2(sides))`; draw DRBG bytes via `keyed_drbg.output()`, walk the bit string, accept `v < sides`, map to `1..sides`; loop pulling more bytes until `count` rolls collected, with a max-draw `CAP` guard. Docstring credits the legacy algorithm + anti-modulo-bias reason. |
| `api/qeaas/generation.py` | **New.** `random_bytes(n: int) -> bytes` (single served-randomness choke point over `keyed_drbg.output`) and `issue_v1(size: int, fmt: str) -> dict` building `request_id/format/data/entropy_epoch/timestamp/receipt` (`entropy_epoch` from `db.get_root_key()`; `receipt=None` — Q3). Keeps handlers thin. |
| `api/qeaas/auth.py` | **New.** `require_admin(x_admin_token: str = Header(None))` → `ApiError(401,"unauthorized")` unless `hmac.compare_digest` with `os.environ["ADMIN_TOKEN"]`. `require_api_key(x_api_key: str = Header(None)) -> db.ApiKeyRow` → **real** (Q2): 401 `missing_api_key` if absent; hash via `hmac_sha256(derive_subkey("api-key-pepper"), key)`; `db.get_api_key_by_hash`; 401 `invalid_api_key` if not found/`revoked`; else return the row. `hash_api_key(key: str) -> str` helper shared with `mint_key.py`. **No quota** (EPIC 3). |
| `api/main.py` | **Edit.** (1) `CORSMiddleware` (origins from `WEB_ORIGIN`, comma-split; default `http://localhost:3000`) — AC-11. (2) `register_error_handlers(app)` — AC-10. (3) Wrap `/health` in `HealthResponse` — AC-1. (4) `GET /random` (anon, ungated) — AC-2. (5) `POST /dice` (anon) → `dice.roll` — AC-3. (6) `GET /v1/random/bytes` (`Depends(require_api_key)`, `Depends(require_entropy)`) → `generation.issue_v1` — AC-4/AC-13. (7) Replace `/v1/seed` **stub** with the real alias (same deps, `bytes`→`size`) — AC-5. (8) `POST /v1/verify` → provenance stub — AC-6. (9) `POST /admin/ingest` (`Depends(require_admin)`, `UploadFile`) — AC-7. **Leave `/v1/kem/keypair` stub untouched** (EPIC 4). Handlers thin. |
| `api/qeaas/db.py` | **Edit.** Add `@dataclass ApiKeyRow(key_hash, owner, tier, daily_quota_bytes, revoked, created_at)`, `insert_api_key(key_hash, owner, tier, daily_quota_bytes)`, `get_api_key_by_hash(key_hash) -> ApiKeyRow | None`. Parameterized queries only. |
| `api/sql/002_api_keys.sql` | **New.** `CREATE TABLE IF NOT EXISTS api_keys (key_hash text PRIMARY KEY, owner text NOT NULL, tier text NOT NULL DEFAULT 'default', daily_quota_bytes bigint, revoked boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now())`. |
| `api/scripts/mint_key.py` | **New.** CLI: `python -m scripts.mint_key --owner <name> [--tier default] [--quota <bytes>]` → `secrets.token_urlsafe(32)`, `auth.hash_api_key`, `db.insert_api_key`, print the plaintext key **once**. Mirrors `ingest_bits.py`. (Local dev-key seeding until the EPIC 3 mint route lands.) |
| `api/.env.example` | **Edit.** Add `WEB_ORIGIN=http://localhost:3000` (comma-separated origins for CORS). Clarify `ADMIN_TOKEN` now guards `/admin/ingest`. |
| `api/requirements.txt` | **Edit.** Add `python-multipart` (pure-Python, Q5), pinned. |

**No business logic in `main.py`** — handlers validate via Pydantic and delegate to `qeaas`.

---

## 7. Dice algorithm detail (AC-3, ported from `generate_numbers`; Q6 bounds)

```
n = sides                                 # 2 ≤ sides ≤ 100
bits_needed = ceil(log2(n))               # d6 -> 3 bits, d20 -> 5, d100 -> 7
rolls = []                                # count: 1 ≤ count ≤ 6 dice per throw
draws = 0
while len(rolls) < count and draws < CAP:
    chunk = keyed_drbg.output(k) -> bit string; draws += k
    for each bits_needed-wide window:
        v = int(window, 2)
        if v < n: rolls.append(v + 1)     # map 0..n-1 -> 1..n
        if len(rolls) == count: break
return rolls
```

- Rejecting `v >= n` removes modulo bias (the legacy comment). Do **not** use `% sides`.
- Bytes come from `keyed_drbg.output()` — dice are quantum-seeded like everything else and stay
  working when the pool is `degraded` (ungated).
- `CAP` (e.g. `count * 64` byte-draws) prevents an unbounded loop; on overflow raise
  `ApiError(500,"dice_sampling_failed")` — practically never hit, but explicit.

---

## 8. Verification (manual — no automated tests)

Per the project directive there are **no automated tests**. After implementation, verify by hand:

- `uvicorn main:app` locally; open `/docs` and confirm every route renders with typed schemas (AC-12).
- `GET /openapi.json` → 200 listing every new path.
- `curl` each route for the happy path and the edge cases in §4:
  - `/random?bytes=64` → base64; `bytes=65` → `422`.
  - `POST /dice {sides:6,count:6}` → 6 rolls in `1..6`; `count:7` → `422`.
  - `/v1/random/bytes` with a `mint_key.py`-issued key → 200 with all six fields (`receipt` null);
    no key → `401`; a `revoked` key → `401`; `size=31` → `422`.
  - `/admin/ingest` with the admin token + a small `0/1` `.txt` → pool grows; wrong token → `401`;
    a > 10 MB file → `413`.
- Confirm every error body is the flat `{"error": "<slug>"}` envelope.

### Note on existing EPIC 1 tests
`api/tests/test_gate.py` asserts `/v1/seed` returns `{"stub": true}`. EPIC 2 makes `/v1/seed` the real
key-guarded alias, so that assertion no longer matches the code. Per the no-tests directive the plan
does **not** update or run it; treat `api/tests/` as unmaintained legacy. (If the developer later
wants the EPIC 1 suite kept green, that is a separate task outside this plan.)

---

## 11. Open questions — RESOLVED

- **Q1 — Error envelope → flat `{"error": "<slug>"}`.** Matches the existing gate detail; no human
  message field. Exception handlers normalize everything to this shape.
- **Q2 — API-key depth → hash-validate now, quota later.** EPIC 2 ships the `api_keys` table +
  peppered-hash validation + `revoked` check (real 401s). Per-key daily quota, rate limiting, and
  the over-quota `429` remain **EPIC 3**; the `daily_quota_bytes` column exists but is unenforced.
- **Q3 — Receipts → `entropy_epoch` now, `receipt` deferred.** `entropy_epoch` = `reseed_counter`
  (already available). `receipt` returns `null`; `/v1/verify` is an unsigned provenance stub. Real
  signing/resolution = **EPIC 9**.
- **Q4 — `POST /admin/keys` → deferred to EPIC 3.** Table + `require_admin` + `mint_key.py` CLI ship
  now so keys can be created for dev; the HTTP mint route lands in EPIC 3.
- **Q5 — `/admin/ingest` → multipart `.txt` upload, ≤ 10 MB.** Real `UploadFile`; adds
  `python-multipart`. Over-size → `413`; non-`0/1`/non-`.txt` → `422`.
- **Q6 — Dice bounds → `sides` 2–100, `count` 1–6.** `sides` adjustable/custom up to 100 (min 2 —
  a 1-sided die is degenerate and breaks `log2`); up to 6 dice per throw.

---

## 12. Definition of done (EPIC 2 "Done when")
- [x] All routes work locally: `/random`, `/dice`, `/v1/random/bytes`, `/v1/seed` (alias),
      `/v1/verify` (stub), `/admin/ingest` (multipart); `/health` wrapped in its schema.
- [x] `/docs` renders every route with typed schemas; `GET /openapi.json` → 200 (AC-12).
- [x] Edge cases return correct codes: bad `size`/`format` → `422`; missing/invalid/revoked key →
      `401`; degraded pool → `503`; bad admin token → `401`; > 10 MB upload → `413` (AC-13).
- [x] `api_keys` table + peppered-hash validation live; `mint_key.py` creates a working dev key;
      quota enforcement explicitly left to EPIC 3.
- [x] Every request/response is a Pydantic model; every error uses the flat envelope (AC-9/10).
- [x] CORS allows the configured web origin (AC-11).
- [x] Raw QRNG bits are never served — all output flows through `keyed_drbg.output()`.
- [x] Manual verification (§8) done; **no automated tests written** (project directive).

---

## 13. Post-Implementation

Built exactly per plan: `qeaas/schemas.py`, `errors.py`, `dice.py`, `generation.py`, `auth.py`
(all new); `main.py` and `qeaas/db.py` edited additively; `sql/002_api_keys.sql` and
`scripts/mint_key.py` new; `.env.example`/`requirements.txt` updated with `WEB_ORIGIN` and
`python-multipart`.

Manual verification (§8) was run against a real ephemeral Postgres + Redis (Docker containers,
`postgres:16-alpine` / `redis:7-alpine`, removed afterward) rather than against Neon/Upstash, since
no `.env` with live credentials exists in this environment. Every route and edge case in §4/§8 was
exercised with `curl` and confirmed against a live DB — see §2 AC table for the exact commands/codes.
No deviations from the plan. `api/tests/test_gate.py` now fails against the real `/v1/seed` (expected,
called out in the plan itself; left untouched per the no-tests directive).
