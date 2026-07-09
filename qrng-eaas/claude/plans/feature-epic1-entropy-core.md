# Feature Plan — EPIC 1: Entropy core (DRBG + pool + gate)

**Status:** Complete
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 1 `[MUST]`
**Interpretation of "part 1":** EPIC 1. EPIC 0 (repo layout, pure-Python `requirements.txt`,
`vercel.json`, the S0.2 ML-KEM spike) is already done and verified — the spike prints
`OK: DRBG(64) -> ML-KEM-768.key_derive is deterministic; encaps/decaps round-trips.` The next
`[MUST]` is the entropy engine, and `api/main.py` is still an 8-line `/health` stub.

---

## 1. Context & goal

Build the randomness engine that stretches finite QRNG bits into effectively-unlimited output
and knows when it is running low. This is the foundation every downstream epic (2 API surface,
3 anti-abuse, 4 ML-KEM, 9 receipts) draws from.

The serverless-safety pattern is fixed by the build plan (Locked decision + Architecture §):

> On stateless serverless you cannot safely read-modify-write DRBG state per request (two
> concurrent requests could reuse state → identical output). Instead keep a **monotonic counter**
> in Redis (atomic `INCR`) and compute `output(n) = HMAC-DRBG(root_key, counter_value, n)`. The
> `root_key` is rotated ("reseeded") from the QRNG pool periodically.

Repeat the honest framing in code comments and docstrings: **QRNG supplies entropy that seeds a
standards DRBG; it does not "defeat quantum attackers."**

### What already exists (integration points)
- `api/main.py` — FastAPI app titled "Quantum Entropy-as-a-Service", one route `GET /health → {"status":"ok"}`. EPIC 1 replaces the health body and adds the engine modules behind it.
- `api/requirements.txt` — pure-Python: `fastapi`, `psycopg[binary]`, `redis`, `python-dotenv`, `kyber-py`, `uvicorn`, `pydantic`. DRBG + HKDF are stdlib `hmac`/`hashlib`; **one new runtime dep** — `pycryptodome` for AES-256-GCM (confirmed, Q2).
- `api/.env.example` — `DATABASE_URL`, `REDIS_URL`, `MASTER_KEY`, `ADMIN_TOKEN` (already the right keys).
- `shared/spikes/mlkem_seed_spike.py` — `placeholder_drbg_generate(seed, n)` is a stand-in; EPIC 1's real `HmacDrbg.generate` supersedes it (do not delete the spike; it documents the wiring).
- **QRNG input format (confirmed):** the pool is seeded from a plain `.txt` file containing **only** the characters `0` and `1`, nothing else — **no `bits:` prefix**, no whitespace/newlines assumed meaningful, no headers. `ingest_bits.py` reads the file, strips any stray whitespace/newlines, validates every remaining char is `0`/`1`, packs 8 bits → 1 byte (MSB-first; a trailing partial byte of < 8 bits is discarded), then encrypts. (The existing `ErrorDetectionVSRawBits/qrng_output/*_processed.txt` files carry a `bits:` prefix — that is a *different*, legacy format and is **not** the input contract here.)

---

## 2. Acceptance criteria (from EPIC 1 "Done when" + story checkboxes, verbatim intent)

| AC | Covered by |
|----|------------|
| AC-1 | `api/qeaas/drbg.py:17-70` (`HmacDrbg.instantiate/reseed/generate`, stdlib `hmac`/`hashlib` only) |
| AC-2 | `api/tests/test_drbg_kat.py:1-38` passing against real NIST CAVP vectors in `api/tests/vectors/hmac_drbg_sha256.json` (5 no-reseed + 5 with-reseed cases, no PR) |
| AC-3 | `api/qeaas/keyed_drbg.py:67-77` (`output()`: `incr_counter()` then `HmacDrbg.generate` mixing the counter as additional input) |
| AC-4 | `api/qeaas/keyed_drbg.py:35-49` (`_load_cache`: module-level `_cache` dict, refreshed on reseed) |
| AC-5 | `api/tests/test_keyed_drbg.py:31-35` (`test_distinct_counters_give_distinct_output`) |
| AC-6 | `api/sql/001_entropy_core.sql:5-13`, `api/qeaas/pool.py:87-96` (`pull_reseed_material` is the only read path) |
| AC-7 | `api/qeaas/keyed_drbg.py:52-64` (`maybe_reseed`, T/K/counter constants) |
| AC-8 | `api/tests/test_reseed.py:44-51` (`test_reseed_advances_offset_and_shrinks_pool`) |
| AC-9 | `api/qeaas/gate.py:13-15` (`entropy_level`), `api/tests/test_gate.py:16-24` |
| AC-10 | `api/qeaas/gate.py:18-20` (`require_entropy`), `api/main.py:31-37` (gated stub routes), `api/tests/test_gate.py:24-25` |
| AC-11 | `api/main.py:14-18` (`add_entropy_header` middleware), `api/tests/test_gate.py:41-44` |
| AC-12 | `api/qeaas/pool.py:20-45` (`derive_subkey`, `encrypt_chunk`/`decrypt_chunk` via `pycryptodome` GCM), `api/tests/test_pool_crypto.py` |
| AC-13 | `api/tests/test_gate.py:27-36` (`test_healthy_after_refill`) |
| AC-14 | `api/qeaas/pool.py:53-73` (`parse_bits_file`), `api/tests/test_ingest.py` |

---

## 3. Scope

### In scope
- `HmacDrbg` core (SP 800-90A) + KAT tests.
- Keyed-DRBG serverless wrapper (Redis counter + Neon root_key + warm cache).
- `entropy_pool` + `drbg_root` tables, a SQL bootstrap script, and the reseed policy.
- Low-entropy gate: `/health` body, the `X-Quantum-Entropy` header on all responses, and a
  reusable `require_entropy()` dependency that stubbed premium routes use to return 503.
- AES-256-GCM encryption of pool chunks at rest + HKDF sub-key derivation + best-effort burn
  (minimum slice of EPIC 10 needed so the pool is not born storing plaintext — see §11 Q1).
- A local pool-ingest helper (parse `bits:` files → bytes → encrypted chunks) sufficient to seed
  a dev pool and to test reseed. **Not** the public `POST /admin/ingest` endpoint.

### Out of scope (deferred to their epics)
- Public/keyed HTTP endpoints `/random`, `/dice`, `/v1/random/bytes`, `/v1/seed`, `/v1/kem/*`,
  `/admin/*` beyond the stubs needed to prove the gate (EPIC 2, 3, 4).
- Rate limiting, API keys, quotas (EPIC 3).
- Receipts / `/v1/verify` and `entropy_epoch` provenance queries (EPIC 9) — but create the
  `drbg_root.reseed_counter` field EPIC 9 will read.
- Full EPIC 10 lifecycle (`receipt-signing-key`, `api-key-pepper` sub-keys, DB-wide plaintext
  scan). Only `pool-encryption-key` + pool encryption are pulled forward here.
- Neon/Upstash provisioning and Vercel deploy (EPIC 6).

---

## 4. Data model (Neon) — subset built in this ticket

Matches the build plan's cross-cutting data model. `bytea` columns, no plaintext.

| Table | Columns (this ticket) |
|-------|----------------------|
| `entropy_pool` | `id serial pk`, `ciphertext bytea`, `nonce bytea(12)`, `tag bytea(16)`, `plaintext_len int`, `consumed_offset int default 0`, `source_label text`, `uploaded_at timestamptz default now()` |
| `drbg_root` | `id serial pk`, `root_key bytea` (the current 32-byte seed material, itself decrypted-in-memory only), `reseed_counter int default 0`, `outputs_since_reseed int default 0`, `rotated_at timestamptz default now()` |

Notes:
- `entropy_pool` stores QRNG bytes as **GCM ciphertext per chunk** (AC-12). `consumed_offset`
  tracks plaintext bytes consumed within the decrypted stream.
- `drbg_root.root_key` holds the active seed. Because it derives from burned pool bytes and is
  itself sensitive, it is short-lived by serverless teardown; document the limitation (EPIC 10
  honesty caveat). It is **not** the `MASTER_KEY` (that stays in env only).
- **Redis:** `drbg:counter` (INCR, AC-3). Reseed-interval bookkeeping lives in `drbg_root`
  (`outputs_since_reseed`, `rotated_at`) to survive cold starts.
- All DB access via **psycopg (DBAL-style parameterized queries)** — **no raw string-built SQL**,
  no ORM.

---

## 5. Design decisions carried from the epic (do not re-litigate)
- Pure-Python deps only (no native wheels beyond `psycopg[binary]`/`kyber-py` already vetted).
- Neon **pooled** connection string via `DATABASE_URL`; open a connection per invocation, close it
  (serverless — no long-lived pool object).
- Raw QRNG bits are **never served**; the pool feeds reseed only.
- Honest framing repeated in module docstrings.

---

## 6. File plan (concrete paths)

All new Python: `from __future__ import annotations`, PEP 8, full type hints, module docstrings.
Directory `api/qeaas/` is a new package importable from `api/main.py`.

| File | Change |
|------|--------|
| `api/qeaas/__init__.py` | **New.** Empty package marker. |
| `api/qeaas/drbg.py` | **New.** `HmacDrbg` class: `instantiate(seed, personalization=b"")`, `reseed(seed, additional=b"")`, `generate(n, additional=b"")`, private `_update(provided_data)`. State `_K`, `_V` as `bytearray`. SP 800-90A SHA-256. Docstring cites the standard + honest framing. |
| `api/qeaas/pool.py` | **New.** `encrypt_chunk(plaintext: bytes) -> tuple[bytes,bytes,bytes]` (ct,nonce,tag), `decrypt_chunk(ct,nonce,tag) -> bytearray`, `derive_subkey(name: str) -> bytes` (HKDF-SHA256 from `MASTER_KEY`, stdlib `hmac`/`hashlib`), `burn(buf: bytearray) -> None` (zeroize). AES-256-GCM via `pycryptodome` (`Crypto.Cipher.AES`, mode `MODE_GCM`, fresh 12-byte nonce/chunk). `parse_bits_file(path) -> bytes` (AC-14: read, strip whitespace, validate 0/1-only, pack MSB-first, drop trailing partial byte), `ingest_bits_file(path) -> None` (parse → chunk → encrypt → insert), `pull_reseed_material(n=32) -> bytearray` (decrypt from `consumed_offset`, advance it, burn). |
| `api/qeaas/keyed_drbg.py` | **New.** `output(n: int) -> bytes` = load cached `root_key` → `INCR drbg:counter` → seed a per-call `HmacDrbg` with `root_key` and mix the counter via `additional_input`, `generate(n)`. `maybe_reseed()` enforces the T/K/reseed-counter interval (AC-7), calls `pool.pull_reseed_material`, `drbg.reseed`, updates `drbg_root`, refreshes the module cache. Thresholds/intervals as module constants. |
| `api/qeaas/db.py` | **New.** Thin psycopg helpers: `connect()`, `get_root_key()`, `save_root_key(...)`, `pool_bytes_remaining() -> int`, `advance_consumed_offset(...)`. Parameterized queries only. |
| `api/qeaas/redis_client.py` | **New.** `incr_counter() -> int` on `drbg:counter`; lazy singleton client from `REDIS_URL`. |
| `api/qeaas/gate.py` | **New.** `entropy_level() -> Literal["healthy","degraded"]` (compares `pool_bytes_remaining()` to `THRESHOLD`), `require_entropy()` FastAPI dependency raising `HTTPException(503, {"error":"low_quantum_entropy"})` when degraded. |
| `api/main.py` | **Edit.** Expand `GET /health` to `{status, quantum_entropy_level, pool_bytes_remaining, drbg_reseeds, uptime}`. Add middleware setting `X-Quantum-Entropy` on every response (AC-11). Add two **gated stub** routes `GET /v1/seed` and `POST /v1/kem/keypair` that depend on `require_entropy()` and otherwise return `{"stub": true}` — they exist only to prove AC-10 and will be fleshed out in EPIC 2/4. |
| `api/sql/001_entropy_core.sql` | **New.** `CREATE TABLE IF NOT EXISTS entropy_pool ...` + `drbg_root ...` (§4). |
| `api/scripts/ingest_bits.py` | **New.** CLI wrapper around `pool.ingest_bits_file`: takes a path to a plain `0`/`1` `.txt` file (AC-14) and seeds a local dev pool. |
| `api/tests/__init__.py` | **New.** |
| `api/tests/vectors/hmac_drbg_sha256.json` | **New.** Extracted NIST CAVP KAT vectors (SHA-256, no PR). |
| `api/tests/test_drbg_kat.py` | **New.** AC-1, AC-2 — run every vector, assert exact match. |
| `api/tests/test_keyed_drbg.py` | **New.** AC-3, AC-5 — mock Redis `INCR`, assert distinct counters → distinct output; assert deterministic for fixed (root_key, counter). |
| `api/tests/test_pool_crypto.py` | **New.** AC-12 — encrypt→decrypt round-trip; GCM tamper (flip a ciphertext byte) raises; `burn` zeroes the buffer. |
| `api/tests/test_ingest.py` | **New.** AC-14 — plain `0`/`1` file parses; whitespace/newlines stripped; a non-`0/1` char is rejected; MSB-first packing correct; trailing < 8-bit remainder dropped. |
| `api/tests/test_reseed.py` | **New.** AC-7, AC-8 — reseed advances `consumed_offset` and increments `reseed_counter`; `pool_bytes_remaining` drops. |
| `api/tests/test_gate.py` | **New.** AC-9, AC-10, AC-11, AC-13 — with a fake low pool `/health` is `degraded`, stubbed `/v1/seed` returns 503, header present; refill → `healthy`. |
| `api/requirements.txt` | **Edit.** Add `pycryptodome` (Q2, pure-Python AES-GCM), pinned. Add `pytest` to a new `api/requirements-dev.txt`. |
| `api/.env.example` | **Edit.** Add inline comments documenting each var's role for EPIC 1 (`MASTER_KEY` = 256-bit quantum master, hex-encoded). |

**No business logic in `main.py`** — routes call `qeaas` functions only. **No raw SQL string
interpolation** — every query parameterized in `db.py`.

---

## 7. Reseed / gate constants (resolved — see §11 Q4; tune in EPIC 6/7)
- `THRESHOLD` = 64 KiB pool bytes remaining → `degraded` below.
- Reseed interval: `T = 15 min` OR `K = 100_000` outputs OR `reseed_counter` step every reseed
  (whichever first).
- Reseed pulls `32` bytes (256-bit) from the pool per reseed (AES-256 gold standard, matches
  EPIC 10 lifecycle step 1).
- All four are named constants in `api/qeaas/keyed_drbg.py`.

### Daily QRNG drain budget (the anti-raid property, quantified)
Daily raw-QRNG cost = (reseeds that day) × 256 bits. Reseeds/day = whichever trigger fires more
often: the 15-min clock (**96/day max**, and only when warm) or one per **100,000** outputs.
Crossover: `96 × 100,000 = 9.6M outputs/day` — below that the clock dominates and drain is **flat
regardless of traffic**.

| Scenario | Reseeds/day | Raw QRNG/day |
|---|---|---|
| Idle (no traffic) | ~0 | ~0 |
| Any traffic ≤ ~9.6M outputs/day | 96 (time cap) | **24,576 bits = 3,072 B ≈ 3 KiB** |
| ~100M outputs/day (extreme) | ~1,000 | 256,000 bits = 32 KiB |

Pool longevity at the steady ~3 KiB/day (down to the 64 KiB `degraded` gate): **1 MB ≈ 330 days,
10 MB ≈ 9 years, 100 MB ≈ 90 years.** Traffic volume barely moves the needle — this is the
concrete form of EPIC 3 S3.3's "no one can raid my bits." Shortening `T` or raising the reseed pull
increases drain (and freshness); both are the tunable constants above.

---

## 8. Testing approach
- Framework: `pytest` (dev-only dep). Run: `api/venv/bin/python -m pytest api/tests -q`.
- DRBG/pool tests are pure and hermetic (no Neon/Redis).
- Keyed-DRBG, reseed, and gate tests **mock** `redis_client` and `db` (monkeypatch) so no live
  Neon/Upstash is needed — matches "in-memory first" from the Day-1 schedule.
- KAT vectors are the correctness anchor: if AC-2 fails, the DRBG is wrong — fix before anything else.

## 10a. Test impact (existing suites)
- **No existing test suite** in `qrng-eaas/` (`api/tests/` is created here; `web/` has none touching
  the API). `shared/spikes/mlkem_seed_spike.py` is a standalone script, not a pytest test, and is
  unaffected — it keeps its own `placeholder_drbg_generate`.
- The root repo (`ErrorDetectionVSRawBits/qrng_compare.py`) is unrelated and untouched.
- Prediction: **no existing tests break** — this ticket only adds files and expands the `/health`
  body + adds a response header, and there is currently no test asserting the old `{"status":"ok"}`.

---

## 11. Resolved decisions & remaining notes

**Q1 — Pull EPIC 10 pool-encryption forward? → RESOLVED: YES.** The pool is born encrypted
(AES-256-GCM, `pool-encryption-key` via HKDF), reflected in AC-12. Rest of EPIC 10 stays deferred.

**Q2 — AES-256-GCM library? → RESOLVED: `pycryptodome`.** Pure-Python, `Crypto.Cipher.AES` GCM.
Added to `requirements.txt`. **Implementer note:** confirm its wheel builds on the Vercel Python
runtime (an S0.3-style check) — if it ever fails there, fall back to `cryptography` and accept the
compiled wheel. Not blocking for local EPIC 1 work.

**Q3 — `root_key` / reseed material size? → RESOLVED: 32 bytes (256-bit).** Matches AES-256 and the
EPIC 10 "256 bits = gold standard"; valid SP 800-90A SHA-256 seed length.

**Q4 — `THRESHOLD` and reseed interval — the two knobs, explained.**
They control different things and are decoupled from request volume (that's the anti-raid property):

- **`THRESHOLD` (low-water mark on the pool → the gate).** When `pool_bytes_remaining < THRESHOLD`,
  health goes `degraded` and premium endpoints 503 while dice keeps running. Too high = premium API
  down while entropy is still plentiful; too low = risk emptying the pool between health checks.
  **Resolved value: 64 KiB.** At 32 B/reseed that's ~2,000 reseeds of warning below the line — ample
  time to run `ingest_bits.py` and refill. Revisit in EPIC 6/7 once the real preloaded pool size is
  known.
- **Reseed interval (how often `root_key` rotates from the pool).** SP 800-90A reseed cadence, so a
  single seed's exposure is bounded and fresh QRNG keeps flowing. Fires on **whichever is first**:
  - **T = 15 min** — bounds staleness on a quiet service.
  - **K = 100,000 outputs** — bounds seed exposure on a busy service (well under the SHA-256 DRBG's
    2⁴⁸ reseed ceiling).
  - **`reseed_counter`** — monotonic, primarily for provenance (EPIC 9 reads it).
- **Why traffic can't drain the pool:** a flood spins the Redis `drbg:counter` (`INCR`), not the
  pool. Pool draw is capped by the *clock* (≤ 32 B every 15 min), not by request count — the
  "no one can raid my bits" guarantee (EPIC 3 S3.3).
- **Resolved:** `THRESHOLD = 64 KiB`, `T = 15 min`, `K = 100,000`, reseed pull = 32 B. All four are
  named constants in `keyed_drbg.py` so EPIC 6/7 can tune without touching logic.

**Q5 — Plan + package location? → RESOLVED: as placed.** Plan in `qrng-eaas/claude/plans/`, engine
package `api/qeaas/`.

**Input contract (added per developer):** raw QRNG input is a `.txt` file containing **only** `0`
and `1` characters — no `bits:` prefix, no other content. See AC-14 and `parse_bits_file`.

---

## 13. Post-Implementation

Built exactly per §6 File Plan: `api/qeaas/{drbg,pool,keyed_drbg,db,redis_client,gate}.py`,
`api/main.py` expanded (health body + `X-Quantum-Entropy` middleware + two gated stubs),
`api/sql/001_entropy_core.sql`, `api/scripts/ingest_bits.py`, and the full `api/tests/` suite
(15 tests, all passing — `venv/bin/python -m pytest api/tests -q`). KAT vectors were fetched from
the NIST CAVP `HMAC_DRBG.rsp` corpus (`drbgvectors_no_reseed` and `drbgvectors_pr_false`,
SHA-256, `PredictionResistance = False`) — the exploration step found no existing vector file in
the repo, so 10 real vectors (5 no-reseed, 5 with-reseed) were transcribed into
`api/tests/vectors/hmac_drbg_sha256.json`.

Follow-ups for the developer:
- `pycryptodome`, `pytest`, and `httpx` (TestClient dep) were installed into `api/venv`; also added
  `pycryptodome` to `requirements.txt` and created `api/requirements-dev.txt` (`pytest`, `httpx`)
  pinned to the installed versions.
- `db.py`/`keyed_drbg.py` assume a single active `drbg_root` row and a single-chunk-at-a-time pool
  read (`pull_reseed_material` doesn't span chunk boundaries) — fine at this scale; revisit if pool
  chunk sizing in EPIC 6/7 makes 32-byte reseeds straddle chunk edges.
- No live Neon/Upstash was exercised — all DB/Redis interaction is monkeypatched in tests, matching
  the plan's "in-memory first" approach. Wiring against real Neon/Upstash is EPIC 6.
- Confirm `pycryptodome`'s wheel builds on the Vercel Python 3.13 runtime before deploy (Q2's
  open item — not blocking for this ticket).
