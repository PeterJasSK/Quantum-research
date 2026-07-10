# Feature Plan — EPIC 4: ML-KEM consumer (the crypto payload)

**Status:** Complete — §11 resolved (all defaults accepted; Q5 amended: quota cost is a configurable constant, settable to `0` for a free/quota-exempt service)
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 4 `[MUST]`
**Interpretation of "part 4":** EPIC 4. The git history uses *part* and *epic* interchangeably
("par0 and part 1" = EPIC 0 + EPIC 1; "epic 2" = EPIC 2; "feature 3 epic protection" = EPIC 3).
EPIC 3 (`feature-epic3-anti-abuse.md`, **Complete**) is the most recent finished work, so the next
`[MUST]` in build order is EPIC 4 — turn the two `/v1/kem/*` stubs into a working, QRNG-seeded
**ML-KEM-768** (FIPS 203, post-quantum) keypair + encapsulation surface. This is *the crypto
payload*: it demonstrates quantum entropy seeding post-quantum key material.

> **No tests (project directive).** This plan does **not** plan, write, or maintain automated tests,
> and `/implement-feature` will not run or create any. Verification is manual only (`curl`, the
> running app, a small round-trip script, `psql`, `redis-cli`). The unmaintained legacy suite under
> `api/tests/` is out of scope; `shared/spikes/mlkem_seed_spike.py` already proved the core wiring.

> **Note on process:** this repo has no GitHub issues, no `tasks/plans/` tree, and no
> `_plan-template.md`. The global `/plan-feature` template (GitHub issues, Doctrine, PSR-12,
> councils) does not apply. This plan follows the shape established by
> `feature-epic3-anti-abuse.md` and the project's real conventions (Python 3.13, FastAPI,
> `from __future__ import annotations`, full type hints, pure-Python deps only, no raw SQL string
> interpolation, thin `main.py` handlers that delegate to `qeaas.*` service modules, honest QRNG
> framing repeated in docstrings/docs).

---

## 1. Context & goal

**Goal (build plan):** demonstrate quantum entropy seeding **post-quantum** key material. An API
client obtains a QRNG-seeded **ML-KEM-768** keypair and can complete a working **encaps/decaps
round-trip**.

Everything EPIC 4 needs already exists and is reused unchanged except where noted:

- **The wiring is proven.** `shared/spikes/mlkem_seed_spike.py` (S0.2) established the exact call
  sequence against the installed `kyber-py==1.2.0`: `ML_KEM_768.key_derive(seed: 64B) -> (ek, dk)`
  is deterministic for a fixed seed; `encaps(ek) -> (shared_secret, ciphertext)`;
  `decaps(dk, ciphertext) -> shared_secret` round-trips. **No fallback to the `mlkem` package is
  needed** (build-plan risk retired). Verified sizes: `ek`=1184 B, `dk`=2400 B, `ciphertext`=1088 B,
  `shared_secret`=32 B.
- **Served randomness choke point.** `qeaas.generation.random_bytes(n)` → `keyed_drbg.output(n)` is
  the single place served bytes come from. EPIC 4 draws its ML-KEM seed material through this same
  path, so the honest framing holds: raw QRNG bits are never used directly; the seed is DRBG output
  reseeded from the QRNG pool (decision #2).
- **Low-entropy gate.** `qeaas.gate.require_entropy` already guards both stubs; premium KEM routes
  keep it (503 `low_quantum_entropy` while `degraded`), per S4.1.
- **API keys + throttling.** `qeaas.auth.require_api_key` (peppered-hash validate + `revoked` check)
  and `qeaas.ratelimit.enforce_key(row, size)` (per-key rate + daily quota) are done in EPIC 3. EPIC 4
  wires the KEM routes into them exactly as `/v1/random/bytes` does — this is the throttling EPIC 3
  explicitly deferred ("throttling it is EPIC 4's job").
- **Usage log.** `qeaas.db.insert_usage_log(principal, endpoint, nbytes)` records keyed issues.

### What already exists (integration points)
- `api/main.py:195` — `POST /v1/kem/keypair` **stub** (`dependencies=[Depends(require_entropy)]`,
  returns `{"stub": True}`, takes no API key, no throttle). EPIC 4 replaces its body and adds the
  API-key + throttle wiring. There is **no** encapsulate route yet — EPIC 4 adds it.
- `api/qeaas/generation.py:18` — `random_bytes(n)` (seed source) and `:22` `issue_v1(...)` (builds
  `request_id`/`entropy_epoch`/`timestamp`/`receipt` metadata). EPIC 4 reuses the seed source and the
  same metadata shape (factored into a tiny shared helper to avoid drift).
- `api/qeaas/keyed_drbg.py:84` — `output(n)`; ML-KEM seed = `output(64)` for keygen, `output(32)` for
  encapsulation randomness. Untouched.
- `api/qeaas/gate.py:19` — `require_entropy`; unchanged, still guards `/v1/kem/*`.
- `api/qeaas/auth.py` — `require_api_key` returns the `db.ApiKeyRow`; used as a named `Depends` param
  exactly like `/v1/random/bytes` (`main.py:107`).
- `api/qeaas/ratelimit.py:124` — `enforce_key(row, size)`; called with the seed-byte cost.
- `api/qeaas/db.py` — `insert_usage_log`, `get_root_key` (for `entropy_epoch`). Unchanged.
- `api/qeaas/schemas.py` — Pydantic models; EPIC 4 adds the KEM request/response models.
- `api/requirements.txt:8` — `kyber-py==1.2.0` **already pinned**; `pycryptodome==3.23.0` present
  (used for the optional HKDF demo-key derivation). **No new runtime dependency.**

Repeat the honest framing in the new docstrings and README section: the quantum part is the
**entropy source** (QRNG → DRBG → 64-byte seed); the quantum **resistance** comes from ML-KEM.
`kyber-py` is educational and **not constant-time** — correct for a thesis demo, not production
(S4.3).

---

## 2. Acceptance criteria (from EPIC 4 stories S4.1/S4.2/S4.3 + "Done when", verbatim intent)

| AC | Requirement (build plan wording) | How it is met | Covered by |
|----|----------------------------------|----------------|------------|
| AC-1 | S4.1 — `POST /v1/kem/keypair` (**API key**) generates **ML-KEM-768** `(ek, dk)` using `DRBG.generate(64)` as the randomness. | New `kem.generate_keypair()` → `ML_KEM_768.key_derive(generation.random_bytes(64))`. Route requires an API key (`Depends(require_api_key)`) + throttle (`enforce_key(key, 64)`). Verified manually: `public_key` decodes to exactly 1184 bytes; two calls return distinct keypairs. | `api/qeaas/kem.py:41-46` (`generate_keypair`); `api/main.py:210-233` (`POST /v1/kem/keypair`). |
| AC-2 | S4.1 — Return `ek` (public) **always**; return `dk` only for the demo flow with a **loud "demo only — real keygen happens client-side" note**. | Request `KemKeypairRequest{include_secret_key: bool = False}`. `public_key` always present; `secret_key` present only when `include_secret_key` is true, and then `note` carries the loud demo-only warning. Verified manually: default call → `secret_key: null`, `note: null`; `include_secret_key:true` → `secret_key` decodes to 2400 bytes, `note` present. | `api/qeaas/schemas.py:93-102` (`KemKeypairRequest`/`KemKeypairResponse`); `api/main.py:214-233`. |
| AC-3 | S4.1 — Respect the low-entropy gate (**503** when degraded). | Route keeps `dependencies=[Depends(require_entropy)]` (as the stub already had) → `503 low_quantum_entropy` while the pool is degraded. Encapsulate route gets the same dependency. Verified manually: draining the pool below `THRESHOLD` (64 KiB) made both `/v1/kem/*` return `503 {"error":"low_quantum_entropy"}` while `/random` kept serving `200`; refilling restored `200`. | `api/main.py:210-213,236-239` (both `/v1/kem/*` routes); `api/qeaas/gate.py:19` (unchanged). |
| AC-4 | S4.2 — `POST /v1/kem/encapsulate` `{ek}` → `{ciphertext}` (+ **optionally** a KDF-derived demo key). Decapsulation happens on the holder of `dk`. | New `kem.encapsulate(ek)` → `ML_KEM_768._encaps_internal(ek, generation.random_bytes(32))` returns `(shared_secret, ciphertext)`; response always includes `ciphertext`; `shared_secret` + optional HKDF `demo_key` included behind the demo note. **No decapsulate endpoint** — decaps stays client-side (Q3). Verified manually: `ciphertext` decodes to 1088 bytes; with `include_shared_secret:true`, `shared_secret`/`demo_key` each decode to 32 bytes and `note` is present; without the flag both are `null`; a malformed/wrong-length `public_key` → `422 {"error":"bad_request"}`. | `api/qeaas/kem.py:49-77` (`encapsulate`, `derive_demo_key`); `api/main.py:236-267` (`POST /v1/kem/encapsulate`); `api/qeaas/schemas.py:105-119`. |
| AC-5 | S4.3 — README note: `kyber-py` is **educational / not constant-time**; for production swap to `liboqs` on a persistent host. | New "ML-KEM consumer (EPIC 4)" section in `qrng-eaas/README.md` states this verbatim-in-spirit, plus the honest "entropy, not quantum-resistance" framing and `curl` examples. Verified `/docs` and `/openapi.json` render the two typed KEM routes (no longer `{stub:true}`). | `qrng-eaas/README.md:205-256`. |
| AC-6 | S4.3 / "Done when" — `keygen → encaps → decaps` round-trips to the same shared secret; an API client can obtain a keypair and complete the round-trip. | `api/scripts/kem_roundtrip.py`: calls the running API for a keypair (with `include_secret_key`) and an encapsulation, then does `ML_KEM_768.decaps(dk, ciphertext)` **locally** and asserts it equals the returned `shared_secret`. Exercises the endpoints end-to-end without adding a server-side decaps oracle. Verified manually: ran against a live local instance, printed `OK: QRNG-seeded ML-KEM-768 keypair round-trips (ss=32B)`. | `api/scripts/kem_roundtrip.py`; manual run (§8). |
| AC-7 | Throttling EPIC 3 deferred to EPIC 4 ("throttling it is EPIC 4's job"). | Both `/v1/kem/*` routes take the API-key row as a named `Depends` param and call `ratelimit.enforce_key(key, <quota_cost>)` before generating, then `db.insert_usage_log(key.key_hash, endpoint, <seed_bytes>)`. `<quota_cost>` is the configurable `kem.KEYGEN_QUOTA_COST` / `kem.ENCAPS_QUOTA_COST` (default = seed bytes 64/32; **set to `0` → free/quota-exempt**, rate limit still applies). Over rate → `429 rate_limited`; over quota → `429 quota_exceeded`. Verified manually: no `X-API-Key` → `401 missing_api_key`; bogus key → `401 invalid_api_key`; a key minted with `--quota 50` → first keypair call `429 {"error":"quota_exceeded"}`; `usage_log` rows show `/v1/kem/keypair` (`nbytes=64`) and `/v1/kem/encapsulate` (`nbytes=32`) only for successful (non-quota-rejected) calls. | `api/main.py:219,232,245,266` (both routes); `api/qeaas/kem.py:37-39` (cost constants). |
| AC-8 | Consistency — KEM issues carry the same provenance metadata scaffold as `/v1/random/bytes` (`request_id`, `entropy_epoch`, `timestamp`, `receipt=null` until EPIC 9). | `generation.new_issue_meta()` (small helper factored out of `issue_v1`) supplies `request_id`/`entropy_epoch`/`timestamp`; `receipt` stays `null` (EPIC 9 signs it). | `api/qeaas/generation.py:22-33`; `api/qeaas/kem.py` (`main.py` spreads `**generation.new_issue_meta()` into both KEM responses). |

---

## 3. Scope

### In scope (backend / `api/` only)
- **New `qeaas/kem.py`** service module: `generate_keypair()`, `encapsulate(ek)`, `derive_demo_key(ss)`,
  the algorithm constant (`ML-KEM-768`) and seed-size constants (`KEYGEN_SEED_BYTES=64`,
  `ENCAPS_SEED_BYTES=32`), input validation (`ek` length / `kyber-py` `ValueError` → `422 bad_request`).
  All key material seeded via `generation.random_bytes(...)`.
- **`POST /v1/kem/keypair`** — replace the stub with the real, API-keyed, throttled, gated route
  (S4.1, AC-1/2/3/7).
- **`POST /v1/kem/encapsulate`** — new API-keyed, throttled, gated route (S4.2, AC-4/7).
- **Pydantic schemas** for both routes (`KemKeypairRequest/Response`, `KemEncapsulateRequest/Response`).
- **Tiny refactor** in `qeaas/generation.py`: extract `new_issue_meta()` (used by both `issue_v1` and
  `kem`) so provenance metadata cannot drift between endpoints (AC-8).
- **`api/scripts/kem_roundtrip.py`** — demo / manual-verification script (stdlib `urllib` + `kyber_py`),
  proves the end-to-end round-trip (AC-6).
- **Docs:** ML-KEM consumer section in `qrng-eaas/README.md` (AC-5) with the honesty caveat + `curl`.

### Out of scope (deferred to their epics — do not implement here)
- **Automated tests of any kind** (project directive).
- **`POST /v1/kem/decapsulate` server endpoint.** The build plan says decapsulation "happens on the
  holder of `dk`" (client-side). EPIC 4 verifies the round-trip with a local decaps in the script; it
  does **not** turn the server into a decaps oracle (Q3).
- **The full networking handshake demo** (Server holds keypair, Client encapsulates, both derive an
  AES-GCM session key and exchange an encrypted message) → **EPIC 8**. EPIC 4 stops at
  keypair + encapsulate + a round-trip check; it does not build the two-role AES-GCM message exchange.
- **Signed receipts / `entropy_epoch` provenance resolution / `issue_log`** → EPIC 9. EPIC 4 emits
  `receipt: null` and reuses the metadata scaffold only.
- **X25519 / WireGuard classical-contrast keypair** → Stretch `[COULD]`.
- **Changing EPIC 1/2/3 behaviour** beyond adding the two throttled KEM routes and the
  `new_issue_meta()` extraction.
- **Web UI for KEM** (a "generate a PQ keypair" panel) — not in EPIC 5's brief; not built here.

---

## 4. Endpoint contracts (concrete)

Error envelope unchanged (flat `{"error": "<slug>"}`, EPIC 2 §4; `429`s carry `Retry-After` from
EPIC 3). All KEM blobs are **base64** (Q1) — binary keys, so base64 not hex; each response states
`"format": "base64"`. Both routes: `require_entropy` (503 gate) **then** `require_api_key` (auth)
**then** `enforce_key` (throttle) **then** generate — the same ordering as `/v1/random/bytes`.

| Route | Auth | Body | Success `200` | New error cases |
|-------|------|------|---------------|-----------------|
| `POST /v1/kem/keypair` | API key + gate | `{"include_secret_key": bool = false}` | `{request_id, algorithm:"ML-KEM-768", format:"base64", public_key, secret_key?: str, entropy_epoch, timestamp, receipt:null, note?: str}` | degraded → `503 low_quantum_entropy`; bad/missing key → `401 invalid_api_key`; over rate → `429 rate_limited`; over quota → `429 quota_exceeded` |
| `POST /v1/kem/encapsulate` | API key + gate | `{"public_key": str (base64 ek), "include_shared_secret": bool = false}` | `{request_id, algorithm:"ML-KEM-768", format:"base64", ciphertext, shared_secret?: str, demo_key?: str, entropy_epoch, timestamp, receipt:null, note?: str}` | malformed / wrong-length `ek` → `422 bad_request`; plus the `503`/`401`/`429` cases above |

Notes:
- **`secret_key` (dk)** is present **only** when `include_secret_key` is true; then `note` = the loud
  `"demo only — in production the keypair is generated client-side and the secret key never leaves the
  holder"` (AC-2).
- **`shared_secret` / `demo_key`** on encapsulate are present **only** when `include_shared_secret` is
  true (default false). The encapsulator legitimately knows the shared secret, but gating it behind a
  flag keeps the default response a pure `{ciphertext}` and makes the demo intent explicit (Q4).
  `demo_key` = HKDF-SHA256(shared_secret) → 32-byte AES-GCM-shaped key, purely illustrative of what
  EPIC 8 will do with it.
- Quota cost charged to `enforce_key` = `kem.KEYGEN_QUOTA_COST` / `kem.ENCAPS_QUOTA_COST`, which
  **default to the seed bytes drawn** (64 keypair / 32 encapsulate) so KEM calls are quota-metered like
  any other DRBG draw, but can be **set to `0`** to run KEM as a free/quota-exempt service — the per-key
  **rate limit still applies** in either case, and `usage_log` still records the real seed bytes (Q5).

---

## 5. Design decisions carried from the epic (do not re-litigate)
- **Seed all ML-KEM randomness from the QRNG→DRBG chain.** Keygen seed = `generation.random_bytes(64)`
  (the 64-byte `d‖z` FIPS-203 input `key_derive` expects). Encapsulation message `m` =
  `generation.random_bytes(32)` fed via `ML_KEM_768._encaps_internal(ek, m)` so the *encapsulation* is
  also QRNG-seeded, not `os.urandom` — this is the honest, whole-story framing (Q2). Depends on the
  pinned `kyber-py==1.2.0` internal method; the dependency and pin are documented in `kem.py`.
- **Pure-Python only, no new dependency** — `kyber-py` and `pycryptodome` are already pinned.
- **Served bytes are DRBG-derived, never raw pool bits** (decision #2). The KEM seed is DRBG output;
  the pool is only ever consumed by the time-boxed reseed (EPIC 1/3). KEM volume cannot drain the pool.
- **Gate first, then auth, then throttle** — identical ordering to `/v1/random/bytes` (EPIC 2/3).
- **Thin `main.py` handlers.** All ML-KEM calls, encoding, HKDF, and validation live in `qeaas/kem.py`;
  handlers validate via Pydantic/`Depends`, call `kem.*` + `ratelimit.*` + `db.*`, return a schema. No
  crypto, base64, or `kyber_py` imports in `main.py`.
- **No raw SQL** — the only DB touch is the existing parameterized `db.insert_usage_log` /
  `db.get_root_key`. No new tables or migrations (KEM outputs are not persisted; EPIC 9 owns `issue_log`).
- **Honesty caveat repeated** — `kyber-py` is educational / not constant-time; production → `liboqs`
  on a persistent host (S4.3, AC-5), stated in `kem.py` docstring and the README.

---

## 6. File plan (concrete paths)

All new/edited Python: `from __future__ import annotations`, PEP 8, full type hints, module docstrings
repeating the honest framing where relevant. **No test files** are created (project directive).

| File | Change |
|------|--------|
| `api/qeaas/kem.py` | **New.** ML-KEM-768 service module. Constants: `ALGORITHM = "ML-KEM-768"`, `KEYGEN_SEED_BYTES = 64`, `ENCAPS_SEED_BYTES = 32`, `EK_BYTES = 1184`, plus the **configurable quota-cost knobs** `KEYGEN_QUOTA_COST = KEYGEN_SEED_BYTES` and `ENCAPS_QUOTA_COST = ENCAPS_SEED_BYTES` (docstring: "set either to `0` to run that KEM endpoint as a free, quota-exempt service — the per-key rate limit still applies"). Functions: `generate_keypair() -> tuple[bytes, bytes]` = `ML_KEM_768.key_derive(generation.random_bytes(KEYGEN_SEED_BYTES))`; `encapsulate(ek: bytes) -> tuple[bytes, bytes]` = validate `len(ek) == EK_BYTES` (else `ApiError(422, "bad_request")`), then `ML_KEM_768._encaps_internal(ek, generation.random_bytes(ENCAPS_SEED_BYTES))` wrapped in `try/except (ValueError, ...)` → `ApiError(422, "bad_request")`, returns `(shared_secret, ciphertext)`; `derive_demo_key(shared_secret: bytes) -> bytes` = HKDF-SHA256 (via `Crypto.Protocol.KDF.HKDF` from `pycryptodome`) → 32 bytes. Module docstring: honest framing + the `_encaps_internal` / `kyber-py==1.2.0` pin note. Imports `ML_KEM_768` from `kyber_py.ml_kem`, `generation`, `ApiError`. |
| `api/qeaas/generation.py` | **Edit (AC-8).** Extract `new_issue_meta() -> dict[str, object]` returning `{request_id: uuid4().hex, entropy_epoch: <drbg_root.reseed_counter or 0>, timestamp: now(utc), receipt: None}`; have `issue_v1` call it and add `format`/`data`. No behaviour change to `issue_v1`; `kem`-route builders reuse `new_issue_meta()`. |
| `api/qeaas/schemas.py` | **Edit.** Add `KemKeypairRequest{include_secret_key: bool = False}`; `KemKeypairResponse{request_id: str, algorithm: Literal["ML-KEM-768"], format: Literal["base64"], public_key: str, secret_key: str | None = None, entropy_epoch: int, timestamp: datetime, receipt: str | None = None, note: str | None = None}`; `KemEncapsulateRequest{public_key: str, include_shared_secret: bool = False}`; `KemEncapsulateResponse{request_id: str, algorithm: Literal["ML-KEM-768"], format: Literal["base64"], ciphertext: str, shared_secret: str | None = None, demo_key: str | None = None, entropy_epoch: int, timestamp: datetime, receipt: str | None = None, note: str | None = None}`. |
| `api/main.py` | **Edit.** (1) Replace `kem_keypair_stub` (`:195`) with real `POST /v1/kem/keypair` (`dependencies=[Depends(require_entropy)]`, body `KemKeypairRequest`, `key: db.ApiKeyRow = Depends(require_api_key)`): `ratelimit.enforce_key(key, kem.KEYGEN_QUOTA_COST)` → `ek, dk = kem.generate_keypair()` → build `KemKeypairResponse` from `generation.new_issue_meta()` + base64 `ek` (+ base64 `dk` and the loud note iff `include_secret_key`) → `db.insert_usage_log(key.key_hash, "/v1/kem/keypair", kem.KEYGEN_SEED_BYTES)`. (2) New `POST /v1/kem/encapsulate` (same deps + key param, body `KemEncapsulateRequest`): `ratelimit.enforce_key(key, kem.ENCAPS_QUOTA_COST)` → decode `public_key` base64 (`binascii.Error` → `ApiError(422,"bad_request")`) → `ss, ct = kem.encapsulate(ek)` → build `KemEncapsulateResponse` (base64 `ct`; base64 `ss` + `demo_key` + note iff `include_shared_secret`) → `db.insert_usage_log(key.key_hash, "/v1/kem/encapsulate", kem.ENCAPS_SEED_BYTES)`. Add `kem` to the `from qeaas import ...` line and the new schema imports. Handlers stay thin. |
| `api/scripts/kem_roundtrip.py` | **New (AC-6).** Stdlib `urllib.request` + `kyber_py`. Reads `API_BASE` (default `http://localhost:8000`), `API_KEY` (env). POSTs `/v1/kem/keypair {include_secret_key:true}`, POSTs `/v1/kem/encapsulate {public_key:ek, include_shared_secret:true}`, then locally `ML_KEM_768.decaps(base64decode(dk), base64decode(ct))` and asserts it equals `base64decode(shared_secret)`. Prints `OK: QRNG-seeded ML-KEM-768 keypair round-trips (ss=32B)` or the mismatch. Mirrors `shared/spikes/mlkem_seed_spike.py`, but through the live endpoints. |
| `qrng-eaas/README.md` | **Edit (AC-5).** New "ML-KEM consumer (EPIC 4)" section: the two endpoints + `curl` examples (mint a key, POST keypair, POST encapsulate), the honest framing (QRNG = entropy source seeding ML-KEM; ML-KEM = the quantum resistance), and the caveat (`kyber-py` educational / not constant-time → `liboqs` for production). Point at `scripts/kem_roundtrip.py`. Update the endpoint list so `/v1/kem/*` are no longer "stub". |
| `api/requirements.txt` | **No change.** `kyber-py==1.2.0` and `pycryptodome==3.23.0` already present. |
| `api/qeaas/gate.py`, `auth.py`, `ratelimit.py`, `keyed_drbg.py`, `db.py`, `errors.py` | **No change.** Reused as-is. |

**No business logic in `main.py`** — handlers delegate to `kem.*` / `ratelimit.*` / `generation.*` / `db.*`.

---

## 7. Algorithm detail (the core wiring)

**Keygen (S4.1):**
```
seed   = generation.random_bytes(64)         # QRNG→DRBG output, the FIPS-203 d‖z input
ek, dk = ML_KEM_768.key_derive(seed)         # deterministic in seed (proven by S0.2 spike)
# ek (1184B) returned always; dk (2400B) only when include_secret_key, with the demo-only note
```

**Encapsulate (S4.2):**
```
m       = generation.random_bytes(32)        # QRNG→DRBG output, the encapsulation message
ss, ct  = ML_KEM_768._encaps_internal(ek, m) # ss=32B shared secret, ct=1088B ciphertext
demo_key = HKDF-SHA256(ss)                    # optional, 32B — illustrative of EPIC 8's AES-GCM key
# ct returned always; ss + demo_key only when include_shared_secret
```

**Decapsulate (verification only — client-side, NOT an endpoint):**
```
ss2 = ML_KEM_768.decaps(dk, ct)              # done by the dk holder / kem_roundtrip.py
assert ss2 == ss                             # round-trip proof (AC-6)
```

- `key_derive` and `_encaps_internal` are the deterministic, seed-injecting entry points confirmed
  against `kyber-py==1.2.0` (§ the S0.2 spike + a live signature check). `_encaps_internal` is a
  private method; `kem.py` documents this and the version pin so a `kyber-py` bump is a conscious
  decision, not a silent break.
- All randomness enters through `generation.random_bytes` → `keyed_drbg.output` → the reseeded
  `root_key`. Two concurrent keypair requests get distinct seeds (distinct Redis DRBG counters), so
  distinct keypairs — the same serverless-safety guarantee as `/random`.
- Base64 encode/decode at the `main.py` boundary only; `kem.py` deals in raw `bytes`.

---

## 8. Verification (manual — no automated tests)

Per the project directive there are **no automated tests**. Verify by hand against an ephemeral
Postgres + Redis (Docker `postgres:16-alpine` / `redis:7-alpine`, as prior epics did) via
`scripts/dev_db_up.sh` with `MASTER_KEY`, `ADMIN_TOKEN`, `DATABASE_URL`, `REDIS_URL` set, schema
applied (`001`,`002`,`003`), pool seeded, app run with `uvicorn`:

- **Setup:** mint a key — `POST /admin/keys {"owner":"kem-demo"}` (or `scripts/mint_key.py`) → capture
  the plaintext key.
- **AC-1/AC-2 (keypair):** `curl -XPOST localhost:8000/v1/kem/keypair -H "X-API-Key: $K" -H
  'content-type: application/json' -d '{}'` → `200` with `public_key` (~1580 base64 chars ≈ 1184 B),
  **no** `secret_key`, `note` null, `algorithm:"ML-KEM-768"`. Repeat with `{"include_secret_key":true}`
  → `secret_key` present (~3200 chars ≈ 2400 B) and the loud demo-only `note`. Two calls → different
  `public_key` (distinct DRBG seeds).
- **AC-4 (encapsulate):** feed the returned `public_key` → `curl -XPOST .../v1/kem/encapsulate -H
  "X-API-Key: $K" -d '{"public_key":"<ek>","include_shared_secret":true}'` → `200` with `ciphertext`
  (~1450 chars ≈ 1088 B), `shared_secret` (44 chars = 32 B), `demo_key` (44 chars). Without the flag →
  only `ciphertext`. Malformed `public_key` (truncated / not base64) → `422 {"error":"bad_request"}`.
- **AC-6 (round-trip):** `API_KEY=$K api/venv/bin/python api/scripts/kem_roundtrip.py` →
  `OK: QRNG-seeded ML-KEM-768 keypair round-trips`. (It fetches keypair+dk, encapsulates, decaps
  locally, asserts the shared secret matches.)
- **AC-3 (gate):** drain / lower the pool below `THRESHOLD` (or temporarily raise `THRESHOLD`) so
  `/health` reports `degraded` → both `/v1/kem/*` return `503 {"error":"low_quantum_entropy"}`; refill
  → `200` again. `/random` keeps working throughout (dice unaffected).
- **AC-7 (auth + throttle):** no / bad `X-API-Key` → `401 {"error":"invalid_api_key"}`. Mint a key with
  a tiny `--quota` and hammer `/v1/kem/keypair` → `429 {"error":"quota_exceeded"}`; exceed the per-key
  per-minute rate → `429 {"error":"rate_limited"}` with `Retry-After`. `SELECT endpoint, nbytes FROM
  usage_log` shows `/v1/kem/keypair` rows (`nbytes=64`) and `/v1/kem/encapsulate` rows (`nbytes=32`).
- **AC-5:** README ML-KEM section renders with the honesty caveat + working `curl`; `/docs` shows the
  two KEM routes with the new schemas (no longer `{stub:true}`).
- Confirm every error body is the flat `{"error":"<slug>"}` envelope.

---

## 9. Definition of done (EPIC 4 "Done when")
- [x] `POST /v1/kem/keypair` (API-keyed, gated, throttled) returns a **QRNG-seeded ML-KEM-768**
      `public_key` always, and `secret_key` only in the demo flow with a loud note (AC-1/2/3/7).
- [x] `POST /v1/kem/encapsulate` returns a `ciphertext` for a supplied `ek`, optionally the
      `shared_secret` + HKDF `demo_key`; malformed `ek` → `422` (AC-4).
- [x] `keygen → encaps → decaps` round-trips to the same shared secret, provable end-to-end via
      `scripts/kem_roundtrip.py` against the running API (AC-6).
- [x] The low-entropy gate 503s both KEM routes while degraded; API key required; over-quota/over-rate
      → `429`; `usage_log` records the issues (AC-3/7).
- [x] README states the honesty caveat (educational / not constant-time → `liboqs` in production) and
      the "entropy, not quantum-resistance" framing (AC-5).
- [x] Handlers stay thin; all ML-KEM/crypto lives in `qeaas/kem.py`; no new dependency; raw QRNG bits
      never served; **no tests written**.

---

## 11. Open questions — RESOLVED

All defaults accepted (developer: "yes to all"). Q5 amended: the quota cost is a configurable
constant, settable to `0` for a free/quota-exempt service.

- **Q1 — KEM blob encoding → base64 (accepted).** ML-KEM keys/ciphertexts are binary blobs; base64 is
  ~⅓ smaller than hex and is the conventional wire form. All KEM responses fix `"format":"base64"`; no
  per-request `format` param (unlike `/v1/random/bytes`, where hex is the human-readable default).
  *Alternative: also accept `format=hex`. Proposed: base64 only, to keep the KEM surface simple.*
- **Q2 — Seed encapsulation randomness from our DRBG via `_encaps_internal` (accepted).** Use `_encaps_internal(ek, generation.random_bytes(32))` so the
  encapsulation is *also* QRNG-seeded — the honest whole-story framing the thesis wants — and document
  the private-method dependency + the `kyber-py==1.2.0` pin in `kem.py`. *Alternative: call the public
  `encaps(ek)` (uses `os.urandom`), which is more robust to library upgrades but makes the
  encapsulation randomness non-QRNG. If you prefer robustness over the framing, say so.*
- **Q3 — No server-side `POST /v1/kem/decapsulate` (accepted).** The build plan says decaps "happens on
  the holder of `dk`"; EPIC 4 verifies the round-trip with a **local** decaps in `kem_roundtrip.py`,
  avoiding a server-side decaps oracle. *Alternative: add a demo-only decapsulate endpoint for
  convenience. Proposed: no — keep it client-side per the build plan; EPIC 8 owns the full handshake.*
- **Q4 — `shared_secret`/`demo_key` on encapsulate gated behind `include_shared_secret` (default
  false) (accepted).** Default response is a pure `{ciphertext}`; the demo flow opts in to see the
  shared secret + HKDF key. *Alternative: always return the shared secret (the encapsulator knows it
  anyway). Proposed: gate it, so the default surface stays minimal and the demo intent is explicit.*
- **Q5 — Quota cost = configurable constant, default seed bytes, `0` = free service (accepted +
  amended).** `kem.KEYGEN_QUOTA_COST` / `kem.ENCAPS_QUOTA_COST` default to the seed bytes drawn (64 /
  32), so KEM is quota-metered like any DRBG draw. **Set either to `0`** and that endpoint becomes
  free / quota-exempt: `enforce_key(row, 0)` charges nothing to the daily byte quota (never trips
  `quota_exceeded`) while the **per-key rate limit still applies** as abuse protection, and
  `usage_log` still records the real seed bytes for visibility. No new env var — the knobs are module
  constants in `kem.py` alongside the reseed constants in `keyed_drbg.py` (same convention).
- **Q6 — `demo_key` KDF = HKDF-SHA256 via `pycryptodome` (already a dep) (accepted).** Purely
  illustrative of the AES-GCM key EPIC 8 will derive. *Alternative: drop `demo_key` entirely in EPIC 4
  and introduce it in EPIC 8. Proposed: include it (it's one line) so the encapsulate response already
  shows the "what you'd do next" shape, but it is optional and behind the same flag as `shared_secret`.*

---

## 12. Post-Implementation

Built exactly per this plan; no deviations from §6/§11. Worked directly on `main` (developer's
call — the repo has no branch-naming convention; EPICs 2/3 were also committed straight to
main).

Verified end-to-end manually (no automated tests, per project directive) against disposable
Docker Postgres + Redis (`scripts/dev_db_up.sh`), a seeded entropy pool, and a live `uvicorn`
instance: keypair sizes (`ek`=1184B, `dk`=2400B), encapsulate sizes (`ciphertext`=1088B,
`shared_secret`/`demo_key`=32B each), field gating on both `include_secret_key` and
`include_shared_secret`, malformed-`ek` → `422`, the low-entropy gate flipping both KEM routes
to `503` and back, missing/bad API key → `401`, an over-quota key → `429 quota_exceeded`,
`usage_log` rows for successful issues only, distinct keypairs across calls, and the full
`kem_roundtrip.py` script succeeding against the live API.

No follow-ups beyond what the plan already deferred to later epics (EPIC 8 networking demo,
EPIC 9 receipts/`/v1/verify`).
