# Feature Plan — EPIC 9: Provenance & verification (receipts, `/v1/verify`)

**Status:** Complete (2026-07-13) — §11 resolved; §12 API-usage expansion added on developer request; implemented and manually verified per §6
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 9 `[SHOULD]`
**Interpretation of "epic 9":** EPIC 9 of the build plan (Provenance & verification). This project
has **no GitHub issues** — the "ticket" is the EPIC 9 section of the build plan (lines 255-274) plus
the cross-cutting data model (lines 308-322). EPICS 1-8 and EPIC 10 are Complete. The pieces this
epic completes are already stubbed/reserved in the codebase:
- `generation.new_issue_meta()` returns `receipt: None` with a docstring pointing to EPIC 9
  (`generation.py:22-35`).
- Every issue schema carries a `receipt: str | None = None` field (`schemas.py:47,108,126`).
- `POST /v1/verify` exists as an **unsigned stub** returning `verified=False` /
  `note="…not yet implemented (EPIC 9)"` (`main.py:148-156`).
- EPIC 10 already ships the master-key → sub-key machinery this epic's signing key rides on:
  `pool.derive_subkey(name)` (HKDF-SHA256 from `MASTER_KEY`, `pool.py:24-28`), already used to
  derive `"api-key-pepper"` (`auth.py:22`) and `"pool-encryption-key"` (`pool.py:33`). The build
  plan names the third sub-key **`receipt-signing-key`** (build plan line 291) — this epic derives
  exactly that.

> **No automated tests in this plan.** Per the project directive: production code + manual
> verification only — no pytest/component test files, no "Testing approach" section, no AC-to-test
> mapping. Existing EPIC 1-10 unit coverage is untouched. Verification is manual (§6): mint a key,
> issue a value, read its `receipt`, `POST /v1/verify` it, tamper one byte and confirm rejection,
> grep the DB to confirm no output bytes were stored, and run the web verify box.

---

## 1. Context & goal

Let a user **trust an issued value's origin without the service ever storing the value** or turning
into a secret-confirming oracle. **Principle (verbatim, build plan line 260-262): verify
provenance, not the secret.** Every *generating* response ships a **signed receipt** over its
metadata; `/v1/verify` re-checks that signature and resolves the entropy epoch. The output bytes
themselves are **never persisted**.

Four stories:
- **S9.1 — Server signing key.** An **Ed25519** signing key derived via HKDF from the EPIC 10
  master (`derive_subkey("receipt-signing-key")`); its public key is **published** for client-side
  verification.
- **S9.2 — Receipts on every issue.** On `/v1/random/bytes`, `/v1/seed`, `/v1/kem/keypair`,
  `/v1/kem/encapsulate`, attach `receipt = sign(request_id, size, entropy_epoch, timestamp)`, and
  log `request_id → (epoch, size, ts)` in Neon (**metadata only, no bytes**).
- **S9.3 — `POST /v1/verify`.** Input `{request_id}` and/or `{receipt}` → return signed metadata:
  when generated, which QRNG batch/epoch seeded it, and receipt validity. Tampered/forged receipts
  fail.
- **S9.4 — Web "Verify a receipt" box.** A small form on the explainer page: paste
  `request_id`/receipt → show provenance. Phone-friendly.

### What already exists — backend integration points
- **Sub-key derivation** `qeaas/pool.py:24-28` — `derive_subkey(name: str) -> bytes` returns a
  deterministic 32-byte HKDF-SHA256 sub-key of `MASTER_KEY` (stdlib `hmac`/`hashlib`, RFC 5869
  one-block Expand). **The Ed25519 seed is `derive_subkey("receipt-signing-key")`** — 32 bytes,
  exactly an Ed25519 seed. **No new env var** (rides `MASTER_KEY`, like the pepper).
- **Crypto library** — `pycryptodome==3.23.0` is already pinned (`requirements.txt`). It provides
  Ed25519 with **no new dependency**: `from Crypto.PublicKey import ECC` →
  `ECC.construct(curve="Ed25519", seed=<32B>)`; `from Crypto.Signature import eddsa` →
  `eddsa.new(key, "rfc8032").sign(msg)` / `.verify(msg, sig)`; raw 32-byte public key via
  `key.public_key().export_key(format="raw")`. **Verified working in `api/venv`** (sign → 64-byte
  sig; raw pubkey export OK). Never add `cryptography` or `pynacl` (native-wheel ban, build plan
  line 32).
- **Issue metadata** `qeaas/generation.py:22-42` — `new_issue_meta()` builds
  `{request_id (uuid4 hex), entropy_epoch (=drbg_root.reseed_counter), timestamp (tz-aware UTC),
  receipt: None}`; `issue_v1(size, fmt)` wraps it for `/v1/random/bytes` + `/v1/seed`. **This is the
  single choke point where the receipt gets signed in.**
- **Issue routes** `qeaas/main.py` — the four generating routes and where each already calls
  `db.insert_usage_log(principal, endpoint, size)`: `/v1/random/bytes` (`main.py:120-129`, logs
  `size`), `/v1/seed` (`main.py:136-145`, logs `bytes`), `/v1/kem/keypair` (`main.py:225-244`, logs
  `kem.KEYGEN_SEED_BYTES`), `/v1/kem/encapsulate` (`main.py:251-277`, logs `kem.ENCAPS_SEED_BYTES`).
  **`insert_issue_log(...)` goes right next to each `insert_usage_log(...)`.** KEM routes build meta
  via `generation.new_issue_meta()` inline (`main.py:232,262`); `issue_v1` builds it internally.
- **`POST /v1/verify`** `main.py:148-156` — unsigned stub, no auth, `VerifyRequest`/`VerifyResponse`
  schemas already exist (`schemas.py:50-65`): request requires **at least one** of
  `request_id`/`receipt` (`model_validator`, `schemas.py:54-58`); response is
  `{request_id, verified, provenance: dict|None, note}`. **This epic replaces the stub body; the
  schemas need no shape change** (provenance is a free-form `dict`).
- **DB helpers** `qeaas/db.py` — parameterized psycopg, connection-per-call, no raw string SQL. The
  pattern to mirror is `insert_usage_log` (`db.py:165-172`) and the `ApiKeyRow` dataclass +
  `get_api_key_by_hash` reader (`db.py:39-46,136-146`). **New `insert_issue_log` / `get_issue_log` /
  `get_pool_source_labels` land here.**
- **Migrations** `api/sql/00N_*.sql` — plain `CREATE TABLE IF NOT EXISTS`, applied in numeric order
  by `scripts/dev_db_up.sh`. `entropy_pool` has a `source_label` column (`sql/001_entropy_core.sql`).
  **Neither `issue_log` nor `entropy_epoch` exists yet** (only `entropy_pool`, `drbg_root`,
  `api_keys`, `usage_log`). This epic adds `sql/004_provenance.sql`.
- **Error envelope** `qeaas/errors.py` — `ApiError(status, slug)` → `{"error": slug}`;
  `RequestValidationError` → `422 {"error":"bad_request"}` (so a body with neither field auto-422s).
- **Anon-endpoint rate-limit** `qeaas/ratelimit.py` — `client_ip(request)` + `check_ip_rate(ip)`
  (per-IP sliding window), used by `/random` and `/dice` (`main.py:84-85,100`). `/v1/verify` is anon
  and stays anon; it gets the same per-IP guard (Decision 6).

### What already exists — web integration points (Next 16.2.10 App Router, React 19, Tailwind v4)
> `qrng-eaas/web/AGENTS.md`: "This is NOT the Next.js you know — read `node_modules/next/dist/docs/`
> before writing code." The verify box is a **client component + anon fetch**, no route handler
> needed (unlike EPIC 8's keyed KEM proxy) — `/v1/verify` takes no API key.

- **Anon fetch pattern** `web/lib/api.ts` — `API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api"`;
  `requestJson<T>(path, init?)` prepends `API_BASE` and throws typed `ApiError(slug)` on non-2xx.
  `getHealth()`/`rollDice()` go **browser-direct** to FastAPI via `API_BASE` (CORS-allowed). **The
  verify box uses this same `requestJson` path** (`/v1/verify` is anon — no key, no proxy, unlike the
  KEM helpers which use `requestJsonSameOrigin`). New `verifyReceipt()` helper + `VerifyResult` type
  go here.
- **Interactive-component pattern** `web/components/DicePlayer.tsx` — `"use client"`; `useState` for
  `result`/`loading`/`error`; submit handler `event.preventDefault()` → `if (loading) return` →
  `try/await helper/setResult` → `catch/setError(messageFor(err))` → `finally/setLoading(false)`;
  result swaps in via state (no reload); framer-motion reveal; `disabled={loading}`; backend slugs →
  friendly copy via `ERROR_MESSAGES` + `messageFor()`. **Mirror this for the verify box.**
- **Explainer page** `web/app/page.tsx` composes sections (`WhatIsQrng`, `PipelineDiagram`,
  `ApiUsage`, `CryptoFraming`) from `components/sections/`. **The verify box is a new section added
  here** (Decision 5). Section pattern: `components/sections/ApiUsage.tsx` — `.panel` cards,
  `<pre className="overflow-x-auto text-xs text-accent">` for code, tokens only.
- **Design tokens** `web/app/globals.css` (Tailwind v4 `@theme`/`@utility`): `bg-deep`, `bg`, `text`,
  `heading`, `accent`, `primary`/hover, `border`; utilities `.glow`, `.pill`, `.panel`; Orbitron
  font. **No Button/Badge/Input primitives — compose inline** like `DicePlayer.tsx`.
- **EPIC 5 locked frontend rules** — no page reload; native `fetch` (never `axios`); fetch/typing in
  `lib/api.ts` not JSX; strict TS, no `any`; `"use client"` on interactive components; mobile-first,
  tap targets ≥44px, works at ~380px, loading/disabled states; tokens only; typed `ApiError` from
  the backend slug surfaced inline; **read Next 16 docs before coding**.

---

## 2. Acceptance criteria

AC-1..AC-8 are the build plan's EPIC 9 stories + "Done when" (lines 255-274), verbatim intent. No AC
is a test — see the banner. Verification is manual (§6).

| AC | Source (verbatim intent) | Met by |
|----|--------------------------|--------|
| **AC-1** | S9.1: "Ed25519 … signing key, derived via HKDF from the master (EPIC 10) … ; public key published for client-side verification." | `qeaas/receipts.py:28` (`_signing_key()` seeded from `derive_subkey("receipt-signing-key")`), `:53` (`public_key_b64()`); `main.py:165-170` (`GET /v1/pubkey` → `PubkeyResponse`). Verified live: `GET /v1/pubkey` → `{"algorithm":"Ed25519","format":"base64","public_key":"<44 b64 chars>"}`. |
| **AC-2** | S9.2: "On `/v1/random/bytes` and `/v1/kem/*`, attach `receipt = sign(request_id, size, entropy_epoch, timestamp)`." | `qeaas/generation.py:22-39` (`new_issue_meta(size)` calls `receipts.sign(...)` at line 37); `main.py:232` (`/v1/kem/keypair`), `main.py:262` (`/v1/kem/encapsulate`) pass their real seed-byte sizes. Verified live: non-null `receipt` on `/v1/random/bytes`, `/v1/seed`, `/v1/kem/keypair`, `/v1/kem/encapsulate`. |
| **AC-3** | S9.2: "Log `request_id → (epoch, size, ts)` in Neon (metadata only, **no bytes**)." | `sql/004_provenance.sql` (`issue_log` table); `qeaas/db.py:185-196` (`insert_issue_log`); called at `main.py:130` (`/v1/random/bytes`), `:149` (`/v1/seed`), `:258` (`/v1/kem/keypair`), `:298` (`/v1/kem/encapsulate`). Verified live: `SELECT` over `issue_log` returns the logged row with matching `size`/`epoch_id`. |
| **AC-4** | S9.3: `POST /v1/verify` input `{request_id}` and/or `{receipt}` → return signed metadata: when generated, which QRNG batch/epoch seeded it, and receipt validity. | `main.py:155-163` (`verify()` calls `receipts.verify(...)` at `qeaas/receipts.py:81-113`). Verified live: receipt-verify resolves `entropy_epoch`+`qrng_source_labels`; request_id-only resolves via `issue_log` lookup with an honest note. |
| **AC-5** | S9.3: "Tampered/forged receipts **fail**." | `qeaas/receipts.py:66-79` (`verify_receipt` returns `None` on any signature/format failure, never raises). Verified live: a byte-flipped receipt → `verified:false`, `provenance:null`. |
| **AC-6** | S9.3 (optional): "if the caller returns the value **together with its receipt**, confirm the receipt is authentic — still without the service having stored the value." | `qeaas/receipts.py:81-113` (`verify()` docstring + design: signs/verifies metadata only); no `value` field exists on `VerifyRequest` (`schemas.py:50-52`). |
| **AC-7** | S9.4: "Small form on the explainer page: paste `request_id`/receipt → show provenance. … phone-friendly." | `web/components/sections/VerifyReceipt.tsx:29-133` (`"use client"`, mirrors `DicePlayer.tsx`); composed at `web/app/page.tsx:47` (between `ApiUsage` and `CryptoFraming`). Verified: SSR HTML includes "Verify a receipt"; `tsc --noEmit`, `eslint`, and `next build` all pass clean. |
| **AC-8** | Done when: "an issued value's receipt verifies and resolves to a real QRNG batch; a forged receipt is rejected; **no output bytes are stored anywhere**." | §6 manual pass (below): a real receipt verified and resolved to `qrng_source_labels: ["seed"]`; a tampered receipt was rejected; `information_schema.columns` on `issue_log` shows only `request_id, principal, endpoint, size, epoch_id, ts` — no bytes/value/data column. |
| **AC-9** | **Developer request (2026-07-13):** the main-page API-usage explanation is **expanded** to (a) document **every** public/keyed/admin request the service exposes, (b) a **"Getting started with the API"** walkthrough (mint/receive a key → first authenticated call), and (c) a **"Rules of usage"** block at the end (rate limits, quotas, tiers, the low-entropy gate, and the never-served-raw-bits / not-an-oracle principles). Exact content is specified in **§12**. | `web/components/sections/ApiUsage.tsx:15-153` (`GROUPS`, all 4 groups/11 endpoints), `:198-215` (Getting started), `:245-282` (Rules of usage). Verified: SSR HTML includes all three headings; `tsc`/`eslint`/`next build` pass. |

---

## 3. Scope

### In scope
- **Backend — signing (S9.1):** new module `qeaas/receipts.py` (Ed25519 sign/verify + compact
  receipt token codec + published raw public key), keyed off `derive_subkey("receipt-signing-key")`.
- **Backend — publish public key (S9.1):** new `GET /v1/pubkey` route + `PubkeyResponse` schema.
- **Backend — receipts on issue (S9.2):** `generation.new_issue_meta(size)` signs the receipt;
  `generation.issue_v1(size, fmt)` and the two KEM routes pass the correct `size`.
- **Backend — issue log (S9.2/AC-3):** `sql/004_provenance.sql` (`issue_log`); `db.insert_issue_log`,
  `db.get_issue_log`, `db.get_pool_source_labels`, `IssueLogRow` dataclass; four `insert_issue_log`
  calls in `main.py`.
- **Backend — verify (S9.3):** rewrite `POST /v1/verify` (via a `receipts.verify(request_id, receipt)`
  service function) + per-IP rate limit; enrich the `provenance` dict (schema shape unchanged).
- **Web — verify box (S9.4):** `verifyReceipt()` + `VerifyResult` in `lib/api.ts`; new
  `components/sections/VerifyReceipt.tsx`; composed into `app/page.tsx`.
- **Web — expanded API-usage section (AC-9, developer request):** rewrite
  `components/sections/ApiUsage.tsx` to document **every** endpoint + a getting-started walkthrough +
  a rules-of-usage block (full content spec in §12).
- **Config/docs:** `api/.env.example` note that `receipt-signing-key` derives from `MASTER_KEY`
  (no new var); a short "## Provenance & verification (EPIC 9)" README section.

### Out of scope (deferred or already satisfied)
- **A dedicated `entropy_epoch` reseed-history table** (build plan data-model line 314). Populating
  it means hooking the DRBG reseed path (`keyed_drbg.py`), which EPICS 1/10 own; **deferred** (Q2).
  Provenance resolves the epoch from the value already in every issue (`entropy_epoch` =
  `drbg_root.reseed_counter`) plus the pool's `source_label`(s) — a real QRNG batch (AC-8) — without
  touching reseed internals.
- **Value-confirmation / value binding.** By principle `/v1/verify` is **not** an oracle; the
  receipt signs metadata only, so no `value` field is added and no value is ever stored or compared
  (AC-6). This is a deliberate non-feature.
- **Authenticating `/v1/verify` or `/v1/pubkey`.** Both are public (the web box is anon, and a
  published public key is public by definition), consistent with `/health`/`/random`.
- **Client-side (in-browser) signature verification** using the published Ed25519 key. The web box
  submits to `/v1/verify` (server verifies); doing the Ed25519 check in JS would need a new npm
  crypto dep. Publishing the key (AC-1) enables *external* clients to verify offline; the app itself
  does not (Q3).
- **Signing anon `/random`/`/dice` output.** S9.2 scopes receipts to the keyed developer/KEM issues;
  anon dice output is not receipted (no `request_id` is surfaced there today).
- **Changing `VerifyRequest`/`VerifyResponse` shapes**, `entropy_epoch` semantics, reseed logic, or
  any EPIC 1-8/10 behaviour.
- **Automated tests** — per the no-tests directive.
- **Stretch `[COULD]`** "signed entropy certificate (hash of QRNG batch + run metadata)" (build plan
  line 360) — related but a separate deliverable; not this epic.

---

## 4. Key decisions

### Decision 1 — Ed25519 via pycryptodome, seeded from `derive_subkey("receipt-signing-key")` (no new dep, no new env var)
S9.1 offers "Ed25519 (or HMAC-SHA256)" and explicitly wants a **published public key for client-side
verification** — that asymmetry is the point (anyone can verify, only the service can sign), so
Ed25519 is the honest reading. It costs **nothing new**: `pycryptodome` is already pinned and
provides Ed25519 (verified in `api/venv`), and the 32-byte `derive_subkey("receipt-signing-key")`
output is exactly an Ed25519 seed — the third named sub-key from build plan line 291, alongside the
already-shipped `pool-encryption-key`/`api-key-pepper`. So **no `cryptography`/`pynacl`, no new
`MASTER_KEY`-sibling env var.** The signing key object is derived once and cached at module scope
(warm-instance reuse, like other modules). HMAC-SHA256 is the fallback (Q1) but loses the published-
public-key property.

### Decision 2 — compact self-verifying receipt token: `qeaas1.<b64url(payload)>.<b64url(sig)>`
The receipt must let `/v1/verify` check authenticity **without a DB lookup** (so a forged receipt
fails on signature, not on absence). Format: a version tag `qeaas1`, then base64url of a **canonical
JSON payload** `{"rid":<request_id>,"sz":<size>,"epoch":<entropy_epoch>,"ts":<iso8601-utc>}`
(sorted keys, compact separators — deterministic bytes), then base64url of the Ed25519 signature over
those exact payload bytes. `sign(request_id, size, entropy_epoch, timestamp)` (AC-2) builds and signs
it; `verify_receipt(token)` splits on `.`, checks the version tag, decodes, verifies the signature
over the re-encoded canonical payload, and returns the payload dict or `None`. This is a JWS-shaped
token without pulling a JWT library.

### Decision 3 — `issue_log` stores metadata only; `size` per endpoint matches `usage_log`
`sql/004_provenance.sql` creates `issue_log (request_id text PRIMARY KEY, principal text, endpoint
text, size bigint, epoch_id bigint, ts timestamptz DEFAULT now())` — **no bytes/value column exists**,
enforcing AC-8 structurally. `db.insert_issue_log(request_id, principal, endpoint, size, epoch_id)`
is called beside each existing `insert_usage_log`, with the **same `size`** already logged there:
`size` for `/v1/random/bytes`, `bytes` for `/v1/seed`, `kem.KEYGEN_SEED_BYTES` for keypair,
`kem.ENCAPS_SEED_BYTES` for encapsulate — so the signed `size` and the logged `size` agree (Q6).
`principal` is `key.key_hash` (keyed endpoints only, matching `usage_log`).

### Decision 4 — `/v1/verify` resolves provenance two ways; "verified" means what it honestly can
Rewrite the stub via `receipts.verify(request_id, receipt)`:
- **`receipt` present** → `verify_receipt(token)`: on success `verified:true` and
  `provenance = {request_id, size, entropy_epoch, timestamp}` from the *signed* payload, enriched
  with `qrng_source_labels` (from `db.get_pool_source_labels()`) so it "resolves to a real QRNG
  batch" (AC-8); on failure `verified:false`, `provenance:null` (AC-5).
- **`request_id` only** → `db.get_issue_log(request_id)`: if found, `verified:true`,
  `provenance = {request_id, size, endpoint, entropy_epoch, timestamp, qrng_source_labels}` from the
  log; if absent, `verified:false`, `provenance:null`. The `note` states plainly that request-id-only
  resolution is a **log lookup**, not a cryptographic check — only a supplied `receipt` is
  signature-verified.
- **Both** → verify the receipt (authoritative), and if the decoded `rid` ≠ `request_id`, treat as a
  mismatch (`verified:false`).

The `entropy_epoch` semantics are unchanged (`= drbg_root.reseed_counter`); resolution adds the pool
`source_label`(s) as the concrete "QRNG batch." No `entropy_epoch` table (Decision/Q2).

### Decision 5 — web verify box is an anon client component section on the explainer page
S9.4 says "on the explainer page." Add `components/sections/VerifyReceipt.tsx` (`"use client"`,
mirroring `DicePlayer.tsx`) and compose it into `app/page.tsx` (e.g. after `ApiUsage`, before
`CryptoFraming`). One textarea (accepts a full receipt token **or** a bare `request_id`), a `.pill`
**Verify** button, and a result `.panel` showing `verified` (✓/✗ pill), the resolved epoch, QRNG
batch label(s), timestamp, and size. Because `/v1/verify` is anon, it uses the existing browser-
direct `requestJson` path (no route-handler proxy — that was EPIC 8's keyed-KEM concern only). Sends
`{receipt}` when the input looks like a token (contains `.` / the `qeaas1.` prefix), else
`{request_id}`. Backend slugs → friendly copy via an `ERROR_MESSAGES` map.

### Decision 6 — `/v1/verify` stays anonymous but gains a per-IP rate limit
Keep it keyless so the web box works without a key (as it does today), but add
`ratelimit.check_ip_rate(ratelimit.client_ip(request))` (the same guard `/random`/`/dice` use) so the
public verify endpoint can't be hammered. It consumes **no** entropy and stores nothing, so this is
pure abuse-hygiene, not an entropy gate — `/v1/verify` is deliberately **not** behind
`require_entropy` (verification must work even when the pool is degraded).

---

## 5. File plan (concrete paths)

All new Python: `from __future__ import annotations`, PSR-equivalent PEP 8, **strict full type hints**
(every param + return annotated), module docstring. **No raw string-built SQL** — every query
parameterized, mirroring `db.py`. **No business logic in `main.py` route bodies or in Twig/JSX** —
signing lives in `receipts.py`, DB access in `db.py`, verification orchestration in
`receipts.verify(...)`; routes only wire dependencies → service call → schema. All new TS: strict
types (no `any`), `"use client"` on the interactive component, fetch/typing in `lib/api.ts` not JSX.

### Backend
| File | Change |
|------|--------|
| `qrng-eaas/api/qeaas/receipts.py` | **New.** `from Crypto.PublicKey import ECC`, `from Crypto.Signature import eddsa`; `from qeaas.pool import derive_subkey`; `from qeaas import db`. Module-cached `_signing_key()` → `ECC.construct(curve="Ed25519", seed=derive_subkey("receipt-signing-key"))`. `public_key_b64() -> str` (raw 32-byte pubkey, base64). `sign(request_id: str, size: int, entropy_epoch: int, timestamp: datetime) -> str` → canonical payload (sorted-key compact JSON, ISO-8601 UTC `timestamp`) → `qeaas1.<b64url(payload)>.<b64url(eddsa.new(key,"rfc8032").sign(payload))>` (Decision 2). `verify_receipt(token: str) -> dict[str, object] | None` → split/validate version tag, b64url-decode, `eddsa…verify(payload, sig)`, return payload dict or `None` on any failure (never raises to the caller — AC-5). `verify(request_id: str | None, receipt: str | None) -> tuple[bool, dict[str, object] | None, str]` (the `(verified, provenance, note)` per Decision 4; enriches with `db.get_pool_source_labels()`). Base64url helpers inline (`base64.urlsafe_b64encode`/`decode`, strip padding). |
| `qrng-eaas/api/qeaas/generation.py` | **Edit.** `new_issue_meta(size: int) -> dict[str, object]`: build `request_id`/`entropy_epoch`/`timestamp` as today, then `receipt = receipts.sign(request_id, size, entropy_epoch, timestamp)` (import `from qeaas import receipts`; no import cycle — `receipts` imports `pool`+`db`, not `generation`). `issue_v1(size, fmt)` already has `size` → passes it through. Update the docstring: EPIC 9 receipts are now populated, not `None`. |
| `qrng-eaas/api/qeaas/db.py` | **Edit.** Add `@dataclass IssueLogRow(request_id, principal, endpoint, size, epoch_id, ts)`; `insert_issue_log(request_id: str, principal: str, endpoint: str, size: int, epoch_id: int) -> None` (parameterized INSERT, mirrors `insert_usage_log`); `get_issue_log(request_id: str) -> IssueLogRow | None`; `get_pool_source_labels() -> list[str]` (`SELECT DISTINCT source_label FROM entropy_pool WHERE source_label IS NOT NULL ORDER BY source_label`). |
| `qrng-eaas/api/qeaas/schemas.py` | **Edit.** Add `PubkeyResponse(algorithm: Literal["Ed25519"], format: Literal["base64"], public_key: str)`. `VerifyRequest`/`VerifyResponse` **unchanged** (provenance stays a free-form `dict[str, object] | None`). |
| `qrng-eaas/api/main.py` | **Edit.** (1) Rewrite `verify()` body (`main.py:148-156`): add `request: Request` param, `ratelimit.check_ip_rate(ratelimit.client_ip(request))` (Decision 6), call `verified, provenance, note = receipts.verify(body.request_id, body.receipt)`, return `VerifyResponse(request_id=body.request_id, verified=verified, provenance=provenance, note=note)`. (2) Add `GET /v1/pubkey` → `PubkeyResponse(algorithm="Ed25519", format="base64", public_key=receipts.public_key_b64())` (anon, no gate). (3) KEM routes: change `generation.new_issue_meta()` (`main.py:232,262`) → `generation.new_issue_meta(kem.KEYGEN_SEED_BYTES)` / `(kem.ENCAPS_SEED_BYTES)`; after building each response add `db.insert_issue_log(response.request_id, key.key_hash, "<endpoint>", <size>, response.entropy_epoch)`. (4) `/v1/random/bytes` + `/v1/seed`: after `_issue_v1(...)`, add `db.insert_issue_log(response.request_id, key.key_hash, "<endpoint>", <size|bytes>, response.entropy_epoch)`. Import `receipts`. |
| `qrng-eaas/api/sql/004_provenance.sql` | **New.** `CREATE TABLE IF NOT EXISTS issue_log (request_id text PRIMARY KEY, principal text NOT NULL, endpoint text NOT NULL, size bigint NOT NULL DEFAULT 0, epoch_id bigint NOT NULL DEFAULT 0, ts timestamptz NOT NULL DEFAULT now());` + `CREATE INDEX IF NOT EXISTS issue_log_ts ON issue_log (ts);`. Header comment: metadata only — **no output bytes ever** (AC-8). |
| `qrng-eaas/api/.env.example` | **Edit.** One comment line under `MASTER_KEY`: the EPIC 9 receipt-signing key is `HKDF("receipt-signing-key")` of `MASTER_KEY` (no separate var). |

### Web
| File | Change |
|------|--------|
| `qrng-eaas/web/lib/api.ts` | **Edit.** Add `interface VerifyResult { request_id: string \| null; verified: boolean; provenance: Record<string, unknown> \| null; note: string; }` and `verifyReceipt(input: { receipt?: string; request_id?: string }): Promise<VerifyResult>` → `requestJson<VerifyResult>("/v1/verify", { method: "POST", headers: {"content-type":"application/json"}, body: JSON.stringify(input) })` (browser-direct anon path — **not** `requestJsonSameOrigin`). |
| `qrng-eaas/web/components/sections/VerifyReceipt.tsx` | **New. `"use client"`.** Mirror `DicePlayer.tsx`: `useState` for `input`/`result: VerifyResult \| null`/`loading`/`error`; submit `preventDefault` → `if(loading)return` → decide `{receipt}` vs `{request_id}` by whether the trimmed input contains `.`/starts with `qeaas1.` → `await verifyReceipt(...)` → `setResult` → `catch messageFor` → `finally`. Render inside a `.panel`: a `<textarea>` (label "Paste a receipt or request ID", `min-h` for tap comfort), a `.pill` **Verify** button `disabled={loading}`, and a framer-motion result panel — ✓/✗ verified pill, then provenance rows (epoch, QRNG batch label(s), timestamp, size) or the honest note when unverified. `ERROR_MESSAGES` map (`rate_limited` → "Too many checks — try again in a moment."; `bad_request` → "Enter a receipt token or a request ID."). Mobile-first, tap ≥44px, ~380px, no reload. |
| `qrng-eaas/web/app/page.tsx` | **Edit.** Import `VerifyReceipt`; render it as a section (after `<ApiUsage/>` within the `#api` area or a new `#verify` block, before `<CryptoFraming/>`). |
| `qrng-eaas/web/components/sections/ApiUsage.tsx` | **Rewrite (AC-9, §12).** Server component (no client interactivity), tokens only, still under `<section id="api">`. Three parts: **(1) Endpoint reference** — replace the 3-snippet `SNIPPETS` array with a fuller structure grouped **Public (anon)** / **Developer (API key)** / **Provenance** / **Admin**, each entry: method+path, one-line purpose, params, auth, and a `curl` in the existing `<pre className="overflow-x-auto text-xs text-accent"><code>` card. Cover **all** of `main.py`: `GET /health`, `GET /random`, `POST /dice`, `GET /v1/random/bytes`, `GET /v1/seed`, `POST /v1/kem/keypair`, `POST /v1/kem/encapsulate`, `POST /v1/verify`, `GET /v1/pubkey`, `POST /admin/keys`, `POST /admin/keys/revoke`, `POST /admin/ingest`. **(2) "Getting started"** — a short ordered walkthrough (get a key from the admin → set `X-API-Key` → first `/v1/random/bytes` call → read the `receipt` → verify it). **(3) "Rules of usage"** — a `.panel` at the end listing the real limits from `qeaas/ratelimit.py` + the invariants. Verbatim content in §12. Keep the existing intro paragraph's honest framing; extend it. Long code blocks scroll inside their card (`overflow-x-auto`), page never scrolls sideways. Mobile-first, ~380px. |

### Docs
| File | Change |
|------|--------|
| `qrng-eaas/README.md` | **Edit.** Append "## Provenance & verification (EPIC 9)": every keyed/KEM issue returns a signed `receipt`; `POST /v1/verify {request_id\|receipt}` resolves provenance (never the value); `GET /v1/pubkey` publishes the Ed25519 key; the signing key derives from `MASTER_KEY` (no new secret); the web "Verify a receipt" box; and the honest line — verify **provenance, not the secret**; no output bytes are stored. |

**No changes** to `qeaas/keyed_drbg.py`, `qeaas/drbg.py`, `qeaas/pool.py`, `qeaas/kem.py`,
`qeaas/gate.py`, `qeaas/ratelimit.py` (only *called*), `qeaas/auth.py`, `qeaas/dice.py`,
`api/requirements.txt`, `sql/001-003`, `api/tests/*`, `web/next.config.ts`, `web/package.json`, or
`web/app/api/*`.

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — running service
Bring up local Postgres+Redis (`bash api/scripts/dev_db_up.sh`) with `MASTER_KEY`/`ADMIN_TOKEN`/
`DATABASE_URL`/`REDIS_URL` set (per README/EPIC 6), seed the pool, `uvicorn`. Confirm `GET /health`
→ `"status":"ok"`, not degraded. Mint a key: `POST /admin/keys` (`X-Admin-Token`) → copy the plaintext.

### Phase 1 — signing + receipts (S9.1/S9.2: AC-1, AC-2, AC-3)
Write `sql/004_provenance.sql` and apply it (re-run `dev_db_up.sh` or `psql -f`). Write
`qeaas/receipts.py`, edit `generation.py`, `db.py`, `schemas.py`, `main.py`. Then:
```bash
# a signed receipt now rides every keyed issue
curl -s "http://localhost:8000/v1/random/bytes?size=32&format=hex" -H "X-API-Key: <key>" | jq .receipt
# -> "qeaas1.<...>.<...>"  (not null)
# published public key
curl -s http://localhost:8000/v1/pubkey | jq .
# -> {"algorithm":"Ed25519","format":"base64","public_key":"<44 base64 chars>"}
# metadata logged, NO bytes column:
psql "$DATABASE_URL" -c "\d issue_log"          # columns: request_id, principal, endpoint, size, epoch_id, ts  (no bytes)
psql "$DATABASE_URL" -c "SELECT request_id, endpoint, size, epoch_id FROM issue_log ORDER BY ts DESC LIMIT 3;"
```
Repeat the receipt check for `/v1/seed`, `POST /v1/kem/keypair`, `POST /v1/kem/encapsulate` — each
response's `receipt` is non-null.

### Phase 2 — verify (S9.3: AC-4, AC-5, AC-6)
```bash
R=$(curl -s "http://localhost:8000/v1/random/bytes?size=64&format=hex" -H "X-API-Key: <key>")
RID=$(echo "$R" | jq -r .request_id);  RCPT=$(echo "$R" | jq -r .receipt)
# verify by receipt -> verified:true, provenance resolves epoch + a real QRNG batch label
curl -s -X POST http://localhost:8000/v1/verify -H 'content-type: application/json' \
  -d "{\"receipt\":\"$RCPT\"}" | jq .
# verify by request_id -> verified:true from the issue_log lookup (note says "log lookup, not signature")
curl -s -X POST http://localhost:8000/v1/verify -H 'content-type: application/json' \
  -d "{\"request_id\":\"$RID\"}" | jq .
# TAMPER: flip one char in the receipt -> verified:false, provenance:null (AC-5)
curl -s -X POST http://localhost:8000/v1/verify -H 'content-type: application/json' \
  -d "{\"receipt\":\"${RCPT}X\"}" | jq '.verified, .provenance'   # false, null
# empty body -> 422 {"error":"bad_request"} (schema model_validator)
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8000/v1/verify \
  -H 'content-type: application/json' -d '{}'                      # 422
```
Confirm the `provenance` from the valid checks contains `entropy_epoch` and a `qrng_source_labels`
entry that matches a real pool `source_label` (AC-8's "real QRNG batch"). AC-6: note in the response
(and README) that verifying the receipt confirms metadata authenticity without any value being sent
or stored.

### Phase 3 — no bytes stored anywhere (AC-8 invariant)
```bash
psql "$DATABASE_URL" -c "SELECT column_name FROM information_schema.columns WHERE table_name='issue_log';"
# assert: no 'data'/'bytes'/'value'/'output' column exists
```
Cross-check that only `issue_log`/`usage_log` metadata + `entropy_pool` **ciphertext** are persisted —
no plaintext output bytes (consistent with EPIC 10's DB-scan invariant).

### Phase 4 — web verify box (S9.4: AC-7)
Add the `lib/api.ts` helper, `VerifyReceipt.tsx`, and the `app/page.tsx` section. `npm run dev`, open
the home page:
- Paste the `RCPT` from Phase 2 → **Verify** → confirm the result panel fills in **with no reload**:
  ✓ verified, resolved epoch, QRNG batch label, timestamp.
- Paste the bare `RID` → verified from the log lookup.
- Paste a tampered/garbage token → ✗ with the honest note, no crash.
- Test at desktop **and** ~380px; confirm the button disables while in flight and a `rate_limited`
  429 shows the friendly message.

Then rewrite `ApiUsage.tsx` per §12 (AC-9) and reload the home page:
- Confirm the expanded section renders all four endpoint groups (Public / Developer / Provenance /
  Admin) covering every `main.py` route, the "Getting started" walkthrough, and the "Rules of usage"
  panel with the real limits (60/min anon, 5 MiB/day anon; default/iot/trusted quotas).
- Copy one documented `curl` verbatim and run it against the local service — it must work as printed.
- At ~380px, confirm long `curl` blocks scroll **inside their card** and the page never scrolls
  sideways.

### Phase 5 — README + final "Done when" pass
Append the README section. Then re-run Phase 2 from a clean shell: a fresh issue's receipt verifies
and resolves to a real batch, a forged receipt is rejected, and Phase 3 confirms no output bytes are
stored — the three "Done when" clauses (build plan line 274).

---

## 7. Design decisions carried from the epic / codebase (do not re-litigate)
- **Verify provenance, not the secret** — `/v1/verify` is never a value-confirmation oracle; the
  receipt signs metadata only; output bytes are never persisted (build plan lines 260-269, 274).
- **Master-key hierarchy** — the receipt-signing key is `derive_subkey("receipt-signing-key")` off
  `MASTER_KEY`, the third named sub-key beside the shipped `pool-encryption-key`/`api-key-pepper`
  (build plan line 291; `pool.py:24-28`, `auth.py:22`). It lives only in env, never in the DB.
- **`entropy_epoch` = `drbg_root.reseed_counter`** — the value already stamped on every issue
  (`generation.py:29-34`); this epic resolves it to a QRNG batch via pool `source_label`, it does not
  redefine the epoch.
- **No new dependency** — Ed25519 via already-pinned `pycryptodome`; **never** `cryptography`/
  `pynacl` (pure-Python-wheel rule, build plan line 32). Web uses native `fetch` (no `axios`, no JS
  crypto lib).
- **Flat error envelope** `{"error": slug}` and `422 bad_request` on a body failing the
  `VerifyRequest` validator (`errors.py`, `schemas.py:54-58`).
- **EPIC 5 frontend rules** — no reload; `fetch` not axios; fetch/typing in `lib/api.ts`; strict TS
  no `any`; `"use client"`; mobile-first, tap ≥44px, ~380px; tokens only (`.glow/.pill/.panel`);
  typed `ApiError` from the backend slug surfaced inline; **read Next 16 docs before coding**.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `receipt` is `null` on issue responses | `generation.new_issue_meta` still returns `None`, or a route didn't switch to `new_issue_meta(size)` | Confirm all four issue paths call the signing `new_issue_meta(size)`; check `receipts.sign` isn't swallowing an exception. |
| `KeyError: 'MASTER_KEY'` on first sign/verify | Env var unset in the API process | Set `MASTER_KEY` (dev: `dev_db_up.sh`/`.env`; prod: Vercel env), same var EPIC 10 already needs. |
| Valid receipt reports `verified:false` | Canonical payload bytes differ between sign and verify (key order / separators / timestamp format) | Sign and verify must serialize the payload **identically** (sorted keys, compact separators, same ISO-8601 UTC string) — verify decodes and re-encodes with the same function. |
| `/v1/pubkey` 500 | `export_key(format="raw")` shape or `ECC.construct(curve="Ed25519", seed=…)` seed length ≠ 32 | `derive_subkey` returns 32 bytes; confirm pycryptodome ≥ 3.23 (pinned) supports Ed25519 raw export. |
| `POST /v1/verify` → 422 unexpectedly | Body has neither `request_id` nor `receipt` | The `VerifyRequest` validator requires at least one — send one field. |
| `issue_log` insert fails on duplicate `request_id` | Extremely unlikely uuid4 collision, or a retried request reusing an id | `request_id` is PK; a genuine retry should mint a fresh id (it does — `uuid4` per `new_issue_meta`). |
| Web box CORS error to `/v1/verify` | `WEB_ORIGIN` doesn't include the web origin | Add the web origin to `WEB_ORIGIN` (same as `/health`/`/dice`); `/v1/verify` uses the same CORS. |
| `429 rate_limited` from `/v1/verify` in testing | Per-IP verify rate limit (Decision 6) tripped | Expected under hammering; wait out the window. It is **not** an entropy gate — verify works even when the pool is degraded. |

---

## 9. Post-Implementation

Built exactly per plan, no deviations. New `qeaas/receipts.py` (Ed25519 sign/verify + compact
receipt token codec), `sql/004_provenance.sql` (`issue_log`), `db.py`/`schemas.py`/`main.py` edits,
and the two web components — all as scoped in §5.

**Manual verification (§6), against a throwaway Docker Postgres+Redis, fresh containers:**
- Phase 0: `/health` → `healthy`, key minted via `/admin/keys`.
- Phase 1: all four issue routes (`/v1/random/bytes`, `/v1/seed`, `/v1/kem/keypair`,
  `/v1/kem/encapsulate`) returned non-null `receipt`; `GET /v1/pubkey` published the Ed25519 key;
  `issue_log` has exactly `request_id, principal, endpoint, size, epoch_id, ts` (no bytes column)
  and rows matched the issued `size`/`entropy_epoch`.
- Phase 2: receipt-verify → `verified:true`, resolved `entropy_epoch`+`qrng_source_labels:["seed"]`;
  request_id-only → `verified:true` via honest log-lookup note; a tampered (byte-flipped) receipt →
  `verified:false`/`provenance:null`; an empty body → `422 {"error":"bad_request"}`.
- Phase 3: `information_schema.columns` on `issue_log` confirmed no bytes/value/data/output column.
- Phase 4: `npm run build`, `tsc --noEmit`, and `eslint` all pass clean; the Next dev server serves
  the home page with all three new sections present in the SSR HTML ("Verify a receipt", "How to
  use the API", "Getting started with the API", "Rules of usage"); CORS preflight on `/v1/verify`
  allows the `localhost:3000` origin the client component fetches from.
- Phase 5: README's EPIC 9 section added; the stale "provenance stub" `curl` example (from before
  this epic) was updated to the real receipt-based flow, and the one-time-provisioning /
  production-runbook sections were updated to include `004_provenance.sql` and `GET /v1/pubkey`.

**Known gap:** no browser-automation tool was available in this session, so the verify box's
client-side interactivity (paste → Verify → result panel, tamper handling, ~380px layout) was not
literally click-tested in a live browser. It was verified indirectly: SSR renders the section, the
component mirrors `DicePlayer.tsx`'s proven state-machine pattern exactly, `tsc`/`eslint`/`next
build` all pass, and the `/v1/verify` endpoint it calls was independently confirmed correct via
curl. A developer should do one real click-through pass before considering AC-7 fully closed.

---

## 11. Open questions — RESOLVED (developer: "yes to all defaults", 2026-07-13)

**Q1 — Signature scheme → RESOLVED: Ed25519** (pycryptodome, no new dep), keeping the published-
public-key / client-side-verification property S9.1 asks for.

**Q2 — Dedicated `entropy_epoch` table → RESOLVED: skip it this epic.** Resolve provenance from the
issue's `entropy_epoch` (`= drbg_root.reseed_counter`) + the pool's `source_label`(s); the richer
per-epoch reseed-history table is a deferred follow-up (no `keyed_drbg` reseed changes here).

**Q3 — Web box verification → RESOLVED: submit to `/v1/verify`** (server verifies; no new npm crypto
dep). `/v1/pubkey` still publishes the key for external offline verification.

**Q4 — Verify-box placement → RESOLVED: a section on the explainer home page** (after `ApiUsage`,
before `CryptoFraming`), not its own route.

**Q5 — Publish pubkey → RESOLVED: dedicated `GET /v1/pubkey`** (not folded into `/health`).

**Q6 — KEM receipt `size` → RESOLVED: the seed-byte cost already logged to `usage_log`**
(`KEYGEN_SEED_BYTES`=64 for keypair, `ENCAPS_SEED_BYTES`=32 for encapsulate), so signed and logged
sizes agree.

---

## 12. API-usage section content spec (AC-9)

Concrete content for the `ApiUsage.tsx` rewrite (§5). All paths/params match `main.py`; all limits
match `qeaas/ratelimit.py`. Base URL below is written as `<base>` — the implementer uses the real
deployed URL (or the README's placeholder style). Keep every `curl` inside an `overflow-x-auto` card.

### 12.1 Intro paragraph (extend the existing honest framing)
Keep the current opening ("Every response is DRBG-derived — raw QRNG bits are never served…") and add:
the anonymous endpoints need no key and are rate-limited; developer endpoints need an `X-API-Key`
minted by an admin and are quota-metered per tier; every developer/KEM issue returns a **signed
receipt** you can check at `POST /v1/verify` without the value ever being stored; admin endpoints
need an `X-Admin-Token`.

### 12.2 Endpoint reference (group → entries)

**Public (anonymous, rate-limited, no key)**
| Method + path | Purpose | Params / body | Notes |
|---|---|---|---|
| `GET /health` | Liveness + entropy status | — | `{status, quantum_entropy_level, pool_bytes_remaining, drbg_reseeds, uptime}` |
| `GET /random?bytes=N` | Small DRBG byte draw (powers dice) | `bytes` 1–64 (default 32) | base64; anon daily ceiling applies |
| `POST /dice` | Rejection-sampled dice rolls | `{"sides":2–100, "count":1–6}` | echoes the DRBG bytes drawn |

**Developer (require `X-API-Key`, quota-metered)**
| Method + path | Purpose | Params / body | Notes |
|---|---|---|---|
| `GET /v1/random/bytes?size=N&format=hex\|base64` | **Canonical** dev entropy | `size` 32–4096, `format` (default `hex`) | returns `request_id, data, entropy_epoch, timestamp, receipt` |
| `GET /v1/seed?bytes=N&format=hex\|base64` | Alias of the above | `bytes` 32–4096, `format` | same engine/limits (compat) |
| `POST /v1/kem/keypair` | QRNG-seeded ML-KEM-768 keypair | `{"include_secret_key": bool}` | `public_key` always; `secret_key` demo-only |
| `POST /v1/kem/encapsulate` | Encapsulate to an `ek` | `{"public_key": b64, "include_shared_secret": bool}` | `ciphertext` always; `shared_secret`/`demo_key` demo-only |

**Provenance (anonymous)**
| Method + path | Purpose | Params / body | Notes |
|---|---|---|---|
| `POST /v1/verify` | Verify a receipt / resolve a request | `{"request_id": str}` and/or `{"receipt": str}` | `{request_id, verified, provenance, note}`; **not** a value oracle |
| `GET /v1/pubkey` | Published Ed25519 receipt-signing key | — | `{algorithm:"Ed25519", format:"base64", public_key}` |

**Admin (require `X-Admin-Token`)**
| Method + path | Purpose | Params / body | Notes |
|---|---|---|---|
| `POST /admin/keys` | Mint an API key | `{"owner", "tier"?, "daily_quota_bytes"?}` | returns the plaintext key **once** |
| `POST /admin/keys/revoke` | Revoke a key (instant) | `{"key_hash"}` | takes effect on the next request |
| `POST /admin/ingest` | Refill the entropy pool | multipart `.txt` of `0`/`1`, ≤10 MB | AES-256-GCM encrypted at rest |

Each entry renders a `curl`, e.g.:
```
curl -s "<base>/v1/random/bytes?size=32&format=hex" -H "X-API-Key: <your-key>"
curl -s -X POST <base>/v1/verify -H 'content-type: application/json' -d '{"receipt":"qeaas1...."}'
curl -s <base>/v1/pubkey
```

### 12.3 "Getting started with the API" (ordered walkthrough)
1. **Get a key** — an admin mints one (`POST /admin/keys` with your `owner`/`tier`); the plaintext
   key is shown **once**, store it securely (the server keeps only a hash).
2. **Authenticate** — send it as the `X-API-Key` header on every developer/KEM call.
3. **First call** — `GET /v1/random/bytes?size=32&format=hex` → you get `data` plus provenance
   (`request_id`, `entropy_epoch`, `timestamp`, `receipt`).
4. **Check provenance** — `POST /v1/verify {"receipt": "<the receipt>"}` → `verified:true` and the
   QRNG batch/epoch it came from. The value itself is never stored or echoed.
5. **Watch your limits** — `GET /health` shows entropy status; over-quota/over-rate calls return
   `429`; a degraded pool returns `503` on developer/KEM endpoints (dice keeps working).

### 12.4 "Rules of usage" (final `.panel`, numbers from `qeaas/ratelimit.py`)
- **Anonymous:** 60 requests/min per IP; `/random` capped at 64 bytes/request; global anon output
  ceiling **5 MiB/day** (`daily_limit_reached` `429` over it).
- **API-key tiers (per-key rate → daily byte quota):** `default` 120/min → **256 KiB/day**;
  `iot` 600/min → **10 MiB/day**; `trusted` 1200/min → **500 MiB/day**. A per-key
  `daily_quota_bytes` override wins over the tier default. Over-rate → `rate_limited`; over-quota →
  `quota_exceeded` (both `429`, with `Retry-After`).
- **Low-entropy gate:** when the pool is degraded, developer/KEM endpoints return
  `503 low_quantum_entropy`; anon dice/`/random` keep serving from the current DRBG.
- **Invariants:** raw QRNG bits are **never** served (all output is DRBG-derived); revocation is
  instant; `/v1/verify` proves **provenance, not the secret** — it never stores or confirms a value.
- **Error envelope:** every error is `{"error": "<slug>"}` (`bad_request` 422, `missing_api_key`/
  `invalid_api_key`/`unauthorized` 401, `rate_limited`/`daily_limit_reached`/`quota_exceeded` 429,
  `low_quantum_entropy` 503, `file_too_large` 413, `not_found` 404).
