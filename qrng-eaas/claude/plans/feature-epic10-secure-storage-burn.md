# Feature Plan — EPIC 10: Secure storage & the entropy "burn" lifecycle

**Status:** Complete (2026-07-13) — §11 resolved: **Q1 = encrypt the root key** (stronger option);
Q2-Q6 = accepted defaults. Implemented and manually verified.
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 10 `[MUST]` (build plan lines 278-301)
**Interpretation of "epic10":** EPIC 10 of the build plan (*Secure storage & the entropy "burn"
lifecycle*). This project has **no GitHub issues** — the "ticket" is the EPIC 10 section of the build
plan (lines 278-301) plus the cross-cutting data model (lines 308-322). EPICS 0-9 are Complete.

> **This is a completion / hardening / verification epic, not a greenfield one.** The build plan
> ordered EPIC 10 "wired in from the start" (line 337), and the EPIC 1 plan
> (`feature-epic1-entropy-core.md:66-78`) **deliberately pulled the minimum slice forward** so the
> pool "is not born storing plaintext": AES-256-GCM pool encryption, HKDF sub-key derivation, and
> best-effort `burn()` all already ship (`pool.py`). The EPIC 1 plan then named exactly what it
> **deferred to "EPIC 10 proper"** (line 77): the `receipt-signing-key` sub-key (since delivered by
> EPIC 9), the `api-key-pepper` sub-key (since delivered by EPIC 3), and **"a DB-wide plaintext
> scan."** That scan is the one unbuilt deliverable left. This plan (a) **audits** each EPIC 10 AC
> against the shipped code and states where it is already met, (b) **builds** the missing
> persistence-invariant scan (S10.4), (c) **closes two concrete burn-lifecycle gaps** in the ingest
> path, and (d) **documents** the master-key hierarchy and the honest zeroization caveat.

> **No automated tests in this plan.** Per the project directive: production code + manual
> verification only — no pytest files, no "Testing approach" section, no AC-to-test mapping. The
> existing EPIC 1 crypto unit tests (`api/tests/test_pool_crypto.py`) are untouched. The new
> `scripts/scan_persistence.py` is an **operational verification script** (run by hand / in a
> runbook), not a test suite — it is the literal artifact S10.4/AC-7 asks for. Verification is manual
> (§6): run the scan against a seeded DB, tamper a ciphertext byte and confirm detection, confirm the
> pool is unreadable without `MASTER_KEY`, and grep the DB/logs for plaintext secrets.

---

## 1. Context & goal

**Goal (build plan line 279-282):** the large preloaded QRNG dataset lives **encrypted at rest**;
keys derive from a quantum-entropy master key; raw bits and seeds are **burned** (best-effort
zeroized) after use; **only ciphertext persists**.

The build plan frames a "daily lifecycle" (collect 256 bits → master key → burn → persist
ciphertext, lines 283-288). In **this serverless architecture** that maps to: a 256-bit
`MASTER_KEY` held **only** in the environment (Vercel env / KMS), HKDF-derived named sub-keys, a
preloaded QRNG pool stored as GCM ciphertext, plaintext decrypted only in-memory to reseed the DRBG
and then zeroized, and a scan that proves nothing plaintext-sensitive was persisted. The plan is
honest about Python's zeroization limits and leans on serverless teardown (build plan line 297).

Four stories (build plan lines 289-299):
- **S10.1 — Master key management.** 256-bit quantum master key lives **only** as a secret
  (env/KMS), **never** in the DB next to the ciphertext it protects; HKDF-SHA256 derives named
  sub-keys `pool-encryption-key`, `receipt-signing-key`, `api-key-pepper`.
- **S10.2 — Encrypt the pool at rest.** Pool stored as **AES-256-GCM** ciphertext (nonce + tag per
  chunk) in Neon; plaintext bits **never** written to disk/DB. On reseed, decrypt only the needed
  chunk in memory, use it, then burn it.
- **S10.3 — The "burn" (best-effort zeroization).** Hold sensitive material in `bytearray`,
  overwrite with zeros after use, drop references promptly. **Honesty caveat:** Python can't
  guarantee zeroization (immutable `bytes`, GC, copies) — best-effort, helped by `bytearray`
  overwrites for long-lived material and serverless teardown; document, don't overclaim.
- **S10.4 — Persistence rule.** Invariant check: grep the DB/logs — **no** plaintext QRNG bytes, no
  plaintext master/seed, ever. Only ciphertext + metadata.

### What already exists — the shipped EPIC 10 slice (audit these; do not re-implement)
- **Master key (S10.1a)** — `pool.derive_subkey` reads `MASTER_KEY` from the environment only
  (`pool.py:26`, `bytes.fromhex(os.environ["MASTER_KEY"])`). **No table stores it** — confirmed by
  reading `db.py` (only `root_key`/`ciphertext`/`api_keys`/log columns are written; grep in §6
  proves it). `.env.example:5-14` documents it as a hex 256-bit secret, env-only, never in Neon.
- **HKDF sub-keys (S10.1b)** — `pool.derive_subkey(name) -> bytes` (`pool.py:24-28`, RFC 5869
  one-block Expand, stdlib `hmac`/`hashlib`). All three named sub-keys the build plan lists exist:
  `"pool-encryption-key"` (`pool.py:33`), `"api-key-pepper"` (`auth.py`, EPIC 3),
  `"receipt-signing-key"` (`receipts.py`, EPIC 9). **All three ride the one `MASTER_KEY` — no
  sibling secrets.**
- **Encrypt at rest (S10.2a)** — `pool.encrypt_chunk` / `pool.decrypt_chunk` (`pool.py:31-45`,
  AES-256-GCM via `pycryptodome`, fresh 12-byte nonce + 16-byte tag per chunk). `entropy_pool`
  stores `ciphertext bytea, nonce bytea, tag bytea, plaintext_len, consumed_offset, source_label`
  (`sql/001_entropy_core.sql`) — **no plaintext-bytes column.** GCM tamper detection is intrinsic:
  `decrypt_and_verify` raises `ValueError` on a bad tag (`pool.py:44`).
- **Decrypt-use-burn on reseed (S10.2b / S10.3a)** — `pool.pull_reseed_material` decrypts only the
  needed slice, advances `consumed_offset`, and `burn()`s the decrypted plaintext (`pool.py:85-95`).
  `keyed_drbg._bootstrap_root_key` / `maybe_reseed` `burn()` the pulled `material` after saving the
  root key (`keyed_drbg.py:38-41, 74-81`). `burn(bytearray)` overwrites in place (`pool.py:48-51`).

### What is missing or weak — the delta this epic delivers
1. **No persistence-invariant scan (S10.4 / AC-7).** Nothing in `api/scripts/` inspects the DB/logs
   for plaintext secrets. This is the marquee deferred item (EPIC 1 plan line 77). **New
   `scripts/scan_persistence.py`.**
2. **Ingest writes raw QRNG bits to a plaintext temp file on disk (S10.2a / AC-3 gap).**
   `admin_ingest` (`main.py:183-194`) does `tempfile.NamedTemporaryFile(delete=False)` → writes the
   uploaded `0/1` bits to disk, parses the file **twice** (`parse_bits_file` then `ingest_bits_file`
   re-reads it), then `unlink`s (no overwrite). "Plaintext bits never written to disk" is violated.
   `ingest_bits.py` (dev CLI) legitimately reads a file the operator already has; the **HTTP ingest
   path** should parse from the in-memory upload, never touching disk. **Fix in `pool.py` +
   `main.py`.**
3. **Ingest sensitive buffers are unburned immutable `bytes` (S10.3a gap).** `content` (raw bits),
   `plaintext` (packed bytes) in `admin_ingest`, and `raw`/`bits`/`packed` inside `parse_bits_file`
   are immutable `bytes`/`str` — not zeroized. Best-effort burn where feasible (wrap the packed
   plaintext + upload bytes in `bytearray`, burn after insert); document the immutable-`str` residue.
4. **No honesty caveat / master-key-hierarchy doc for EPIC 10 (S10.3b / AC-6).** The README has no
   EPIC 10 section; the zeroization limitation is only in code comments. **New README section.**
5. **(Open — Q1) `drbg_root.root_key` is stored plaintext in Neon.** `save_root_key` inserts the raw
   32-byte seed (`db.py:70-77`, `sql/001`). It is a *derived, rotating* seed (not the master key, not
   raw QRNG bits), and the EPIC 1 plan already pre-decided to **document it as a best-effort
   limitation justified by serverless teardown** (`feature-epic1-entropy-core.md:95-96`). S10.4 says
   "no plaintext … seed … ever," so the scan must take an explicit, documented stance. See Q1.
6. **Warm-cache root key & DRBG working state are not burned (S10.3a, minor).** `keyed_drbg._cache`
   holds `root_key` as immutable `bytes` (`keyed_drbg.py:52-58`) and `HmacDrbg._k/_v` hold working
   state — neither is zeroized. Optional best-effort tightening; see Decision 3.
7. **Migration-apply gap (ops).** `scripts/dev_db_up.sh` applies only `001-003`, not even the shipped
   `004_provenance.sql`. Any **new** EPIC 10 migration (only under Q1=encrypt) must be wired into that
   script and the prod apply process, and `004` should be added while we're there. See §5 / Q1.

**Explicitly noted, deliberately NOT changed by this epic (see Q5/Q6):** the hand-rolled one-block
`derive_subkey` (`pool.py:24-28`) is a sound HMAC-based PRF KDF; swapping it to library HKDF would
re-derive **every** sub-key and invalidate the already-encrypted pool, the api-key hashes, and the
receipt key — a breaking migration, out of scope (Q5). The non-atomic `consumed_offset`
read-then-update (`db.py:110-131`) is a concurrency/double-issue concern that belongs to the
entropy-core/anti-drain epics, not secure-storage (Q6).

---

## 2. Acceptance criteria

AC-1..AC-8 are the build plan's EPIC 10 stories + "Done when" (lines 289-301), verbatim intent. No
AC is a test — see the banner; verification is manual (§6). "Met by" states the current status
(**already shipped** = audit only; **this epic** = new work here).

| AC | Source (verbatim intent) | Met by |
|----|--------------------------|--------|
| **AC-1** | S10.1: "The 256-bit quantum master key lives **only** as a secret (Vercel env / KMS) — **never** in the DB next to the ciphertext it protects." | ✅ `pool.py:26` reads `os.environ["MASTER_KEY"]`; no table stores it. Proved by `scripts/scan_persistence.py:145-150` (`check_pool_ciphertext` asserts the master-key bytes never appear in `entropy_pool.ciphertext`) and the README hierarchy doc (`README.md` "Secure storage & the burn lifecycle (EPIC 10)"). Manually verified: `SELECT ... WHERE encode(ciphertext,'hex') LIKE '%'\|\|MASTER_KEY` → 0 rows. |
| **AC-2** | S10.1: "HKDF-SHA256 derives named sub-keys: `pool-encryption-key`, `receipt-signing-key`, `api-key-pepper`." | ✅ `pool.derive_subkey` (`pool.py:24-28`); `pool-encryption-key` (`pool.py:33`), `api-key-pepper` (`auth.py:22`), `receipt-signing-key` (`receipts.py:29`), and the new fourth sub-key `drbg-root-encryption-key` (`pool.py:103`). Documented in `README.md` hierarchy diagram. |
| **AC-3** | S10.2: "Store the QRNG pool as **AES-256-GCM** ciphertext (nonce + tag per chunk) in Neon; plaintext bits are **never** written to disk/DB." | ✅ Ciphertext-at-rest: `pool.encrypt_chunk` (`pool.py:31-37`), `sql/001_entropy_core.sql`. Disk gap closed: `main.py:172-188` (`admin_ingest`) no longer uses `tempfile`/`NamedTemporaryFile` — it wraps the upload in a `bytearray` and calls `pool.ingest_bits_bytes` (`pool.py:85-93`), which parses via `parse_bits_bytes` (`pool.py:54-77`) entirely in memory. Manually verified: no ingest-created temp file appeared in `$TMPDIR` after `POST /admin/ingest`. |
| **AC-4** | S10.2: "On reseed, decrypt only the needed chunk in memory, use it, then burn it." | ✅ `pool.pull_reseed_material` (`pool.py:118-128`) + `keyed_drbg.maybe_reseed` burn (`keyed_drbg.py:77-98`). Manually verified round-trip + burn (§6 Phase 3). |
| **AC-5** | S10.3: "Hold sensitive material in `bytearray`, overwrite with zeros after use; drop references promptly." | ✅ Reseed path: `bytearray` + `burn` (`pool.py:118-128`). Ingest path: `main.py:179` wraps the upload in a `bytearray`, `burn()`s it in a `finally` (`main.py:187`); `parse_bits_bytes` packs into a local `bytearray` and burns it before returning (`pool.py:69-77`). Warm-cache root key held as `bytearray` and burned on forced reload (`keyed_drbg.py:45-50`), closing gap 6. Immutable-`str`/`bytes` residue documented in the README caveat (§4 Decision 3). |
| **AC-6** | S10.3: "**Honesty caveat:** Python can't guarantee zeroization … best-effort … lean on serverless teardown. Document this limitation; don't overclaim." | ✅ `README.md` "## Secure storage & the burn lifecycle (EPIC 10)" — "Honesty caveat: best-effort, not guaranteed, zeroization" bullet states the CPython limitation and mitigations explicitly. |
| **AC-7** | S10.4: "**Invariant test:** grep the DB/logs — no plaintext QRNG bytes, no plaintext master/seed, ever. Only ciphertext + metadata." | ✅ New `api/scripts/scan_persistence.py` (`check_schema_columns`, `check_pool_ciphertext`, `check_root_key`, `check_logs`, `main`) — read-only, PASS/FAIL table, exits non-zero on any violation. Q1=encrypt: `check_root_key` (`scan_persistence.py:163-186`) asserts `drbg_root.root_key` is GCM-ciphertext-shaped (nonce/tag present, 12/16 bytes, 32-byte ciphertext) — no allow-with-note branch. Manually verified: clean DB → all PASS, exit 0; `leak_test(bits text)` table → FAIL naming the table, exit 1. |
| **AC-8** | Done when: "the pool is unreadable at rest without the env-held master key; decrypt→use→zeroize works; GCM tampering is detected; and a scan confirms no plaintext secrets are persisted." | ✅ Manually verified end-to-end (§6): (a) wrong `MASTER_KEY` → `pool.pull_reseed_material` raises `ValueError: MAC check failed`; (b) reseed round-trips (`pull_reseed_material(32)` → 32 bytes) then `burn()` zeroizes the buffer; (c) flipped ciphertext byte → `decrypt_chunk` raises `ValueError`; (d) `scan_persistence.py` exits 0 on a clean DB. `drbg_root` bootstrap/reseed via a live `/v1/random/bytes` call confirmed the root key is stored as 32-byte ciphertext with nonce/tag. |

---

## 3. Scope

### In scope
- **Backend — persistence-invariant scan (S10.4/AC-7):** new `api/scripts/scan_persistence.py` —
  read-only, connects via `db.connect()`, inspects `information_schema` + row samples across every
  table for plaintext QRNG bytes / master key / plaintext seeds, checks the log tables carry no
  bytes/value columns, and exits non-zero with a report on any violation.
- **Backend — close the ingest disk/burn gaps (S10.2a/S10.3a, AC-3/AC-5):** add
  `pool.parse_bits_bytes(raw: bytes) -> bytes` (the existing `parse_bits_file` becomes a thin wrapper
  that reads the file then delegates) and `pool.ingest_bits_bytes(raw: bytes, source_label) -> None`;
  rewrite `main.py::admin_ingest` to parse the in-memory upload (no temp file) and best-effort
  `burn()` the upload/packed buffers.
- **Docs — master-key hierarchy + burn honesty caveat (S10.1b/S10.3b, AC-2/AC-6):** new
  `qrng-eaas/README.md` "## Secure storage & the burn lifecycle (EPIC 10)" section; a one-line
  pointer to `scripts/scan_persistence.py` in the runbook; a `.env.example` cross-reference.
- **Encrypt `drbg_root.root_key` at rest (Q1 = RESOLVED: encrypt):** new
  `drbg-root-encryption-key` HKDF sub-key; `sql/005_root_key_encryption.sql` adds `nonce`/`tag`;
  `keyed_drbg` encrypts before save and decrypts into the warm cache; the scan asserts ciphertext.
  Files in §5 (now active, not conditional). This also closes the warm-cache burn gap (gap 6).

### Out of scope (already satisfied or deferred)
- **Re-implementing pool encryption / HKDF / `burn()`** — shipped in EPIC 1 (`pool.py`); this epic
  audits and documents it, it does not rewrite it.
- **The `receipt-signing-key` and `api-key-pepper` sub-keys** — delivered by EPICs 9 and 3
  respectively; only *documented* here as part of the hierarchy.
- **A dedicated `entropy_epoch` reseed-history table** (data-model line 314) — deferred by EPIC 9
  (Q2 there); EPIC 10 does not add it.
- **KMS integration / envelope encryption / key rotation for `MASTER_KEY` itself** — the build plan
  scopes the master key to "Vercel env / KMS" as a single secret; rotating it (re-encrypting the
  pool under a new master) is a production hardening beyond this thesis epic. Note it in the README
  as future work, do not build it.
- **Guaranteed (not best-effort) zeroization** — impossible in CPython; explicitly out of scope and
  documented as such (AC-6).
- **Changing DRBG/reseed cadence, KEM, verify, or any EPIC 1-9 behaviour** beyond the two ingest
  functions and (if Q1=encrypt) the root-key read/write path.
- **Automated tests** — per the no-tests directive.

---

## 4. Key decisions

### Decision 1 — the S10.4 invariant is a standalone read-only ops script, `scripts/scan_persistence.py`
S10.4/AC-7 asks for an "invariant test: grep the DB/logs." Implement it as a **runnable operational
script** (not a pytest), matching the existing `scripts/` convention (`mint_key.py`,
`ingest_bits.py`). It:
1. Connects with `db.connect()` (env `DATABASE_URL`), **read-only** (only `SELECT` /
   `information_schema`; no writes).
2. **Schema invariant** — enumerate every user table's columns from
   `information_schema.columns`; assert the sensitive tables carry **only** the expected columns:
   `entropy_pool` exposes `ciphertext/nonce/tag/plaintext_len/consumed_offset/source_label/...` and
   **no** column whose name matches `plaintext|bits|raw|seed|data|value|output|secret` **and** holds
   pool bytes; `issue_log`/`usage_log` carry metadata only (no bytes/value/data/output column). Any
   unexpected sensitive-looking `bytea`/`text` column → FAIL with the column named.
3. **Content invariant** — sample `entropy_pool.ciphertext`, assert it does **not** contain the
   known pool plaintext (can't, by construction — GCM) and is high-entropy; assert no row's
   `ciphertext`/any text column equals or contains the `MASTER_KEY` bytes or a decrypted-pool prefix.
   Assert `drbg_root.root_key` handling per Q1 (default: allowed-with-note; encrypt: assert it is
   ciphertext-shaped, not a bare 32-byte seed).
4. **Log invariant** — if a log file path is provided (`--log-file`) or discoverable, grep it for the
   `MASTER_KEY` value and for long `0/1` QRNG-looking runs; FAIL on a hit.
5. Print a per-check PASS/FAIL table; **exit 0 only if every check passes** (usable in a runbook /
   CI gate later). All SQL parameterized or built from `information_schema`-returned identifiers
   validated against an allow-list (no user-supplied string interpolation) — mirrors `db.py`'s
   no-raw-SQL rule. Business logic stays in the script's functions; `db.py` gains only tiny read
   helpers if needed (e.g. `list_table_columns()`), keeping raw inspection out of route code.

### Decision 2 — HTTP ingest parses the in-memory upload; no plaintext bits touch disk (AC-3)
Refactor `pool.parse_bits_file(path)` to read the file and delegate to a new
`pool.parse_bits_bytes(raw: bytes) -> bytes` (the actual strip/validate/pack logic; the file variant
stays for the dev CLI `ingest_bits.py`, which reads a file the operator already holds). Add
`pool.ingest_bits_bytes(raw: bytes, source_label: str) -> None` = `parse_bits_bytes` → `encrypt_chunk`
→ `db.insert_pool_chunk`. Rewrite `main.py::admin_ingest` to call `ingest_bits_bytes(content,
file.filename)` directly on the already-read upload — **delete** the `tempfile.NamedTemporaryFile`
block and the redundant second parse. Result: the uploaded `0/1` bits are validated, packed, and
encrypted entirely in memory; only GCM ciphertext is written. (`bytes_added` for the response comes
from the returned packed length.)

### Decision 3 — best-effort burn on the ingest path; document the immutable-`str` residue (AC-5)
In `admin_ingest`, wrap the upload in a `bytearray` and `pool.burn()` it in a `finally` after
insert; have `ingest_bits_bytes` return the packed length and `burn()` its own packed `bytearray`
before returning. The genuinely un-zeroizable pieces — the immutable `bytes` from `await file.read()`
and the intermediate `str` of `0/1` chars in `parse_bits_bytes` — are called out in the README caveat
(AC-6) rather than pretended away. This mirrors the honest posture already in `keyed_drbg`'s comments
and build plan line 297. (Packing directly from `bytes` into a `bytearray` avoids one large `str`
where practical; a full bit-level rewrite to avoid the `str` entirely is optional polish, noted but
not required.)

**Optional tightening (gap 6):** burn the warm-cache `root_key` before it is replaced on a forced
reload in `keyed_drbg._load_cache` (hold it as a `bytearray` in `_cache`, `burn()` the old one on
`force=True`). The DRBG `_k/_v` working state and the immutable `bytes` root key are left as-is with a
documented caveat — chasing every transient copy has diminishing returns against CPython's guarantees
and serverless teardown already bounds their lifetime. This is a *best-effort* nicety, not required to
close any AC; include it only if it stays small and doesn't touch the `output()` hot path semantics.

### Decision 4 — GCM tamper detection is asserted, not re-built (AC-8)
`decrypt_chunk` already raises `ValueError` on a bad tag (`pool.py:44`). AC-8's "GCM tampering is
detected" is verified manually (§6: flip a ciphertext byte in a copy of a row, call `decrypt_chunk`,
observe the raise). No code change unless §6 shows the raise surfaces as an ugly `500` on the reseed
path — if so, wrap the reseed pull to log and re-raise a clear operational error (still fails
closed). Default: no change; the current fail-closed behaviour is correct.

### Decision 5 — README EPIC 10 section is the home of the honesty caveat + hierarchy (AC-2/AC-6)
Add "## Secure storage & the burn lifecycle (EPIC 10)" to `qrng-eaas/README.md`: (a) the master-key
hierarchy diagram — `MASTER_KEY` (env only) → HKDF → `pool-encryption-key` / `receipt-signing-key` /
`api-key-pepper`; (b) encrypt-at-rest (AES-256-GCM per chunk, only ciphertext persists); (c) the
decrypt→use→burn reseed lifecycle; (d) **the explicit honesty caveat** — CPython cannot guarantee
zeroization (immutable `bytes`, GC copies, no `mlock`); mitigations are `bytearray` overwrites for
long-lived material and serverless teardown destroying the instance after each request; **we do not
overclaim**; (e) how to run `scripts/scan_persistence.py` and what PASS means; (f) `MASTER_KEY`
rotation noted as future work (out of scope). Honest framing consistent with the rest of the project
("entropy, not quantum-resistance").

### Decision 6 (Q1 — RESOLVED: encrypt) — `drbg_root.root_key` is encrypted at rest
**Chosen (2026-07-13): the stronger option.** Encrypt `root_key` at rest with a new
`derive_subkey("drbg-root-encryption-key")` sub-key (AES-256-GCM), so S10.4 ("no plaintext … seed …
ever") holds **literally** and the scan asserts the column is ciphertext. This makes
`drbg-root-encryption-key` the **fourth** named HKDF sub-key off `MASTER_KEY` (beside
`pool-encryption-key`/`receipt-signing-key`/`api-key-pepper`) — document it in the README hierarchy.
Implementation:
- `sql/005_root_key_encryption.sql` adds `nonce bytea` + `tag bytea` to `drbg_root`; `root_key` now
  holds ciphertext.
- `keyed_drbg._bootstrap_root_key` / `maybe_reseed` encrypt the pulled seed **before**
  `save_root_key`, and `burn()` the plaintext material as they already do.
- `db.save_root_key` stores `(ciphertext, nonce, tag, …)`; `RootKeyRow` + `db.get_root_key` return
  all three; `keyed_drbg._load_cache` decrypts into the warm cache (holding the plaintext root as a
  `bytearray`) and `burn()`s the previous one on a `force=True` reload — this also closes gap 6 for
  the cache.
- The scan's `check_root_key` asserts `drbg_root.root_key` is GCM-ciphertext-shaped (has a matching
  `nonce`/`tag`, high-entropy, not a bare 32-byte seed) → **PASS as ciphertext**, no allow-with-note.

Reuse `encrypt_chunk`/`decrypt_chunk` with the new sub-key (add thin `encrypt_root_key`/
`decrypt_root_key` wrappers in `pool.py` only if it improves clarity). The bootstrap must handle the
one-time migration of an existing plaintext row: on load, if a legacy row has empty `nonce`/`tag`,
re-encrypt it in place on first read (or require a fresh reseed) — see §6 Phase 3b and the
troubleshooting row. No change to the `output()` hot-path semantics.

---

## 5. File plan (concrete paths)

All new/edited Python: `from __future__ import annotations`, PEP 8, **strict full type hints** (every
param + return annotated), module docstring. **No raw string-built SQL** — every query parameterized;
`information_schema` identifiers validated against an allow-list before use. **No business logic in
`main.py` route bodies** — parsing/encryption stays in `pool.py`, DB reads in `db.py`, scan logic in
the script's own functions.

### Backend — core delta (all Q1 options)
| File | Change |
|------|--------|
| `qrng-eaas/api/scripts/scan_persistence.py` | **New.** The S10.4 invariant scan (Decision 1). `from qeaas import db, pool`; read-only. Functions: `check_schema_columns() -> list[Violation]`, `check_pool_ciphertext() -> list[Violation]`, `check_root_key() -> list[Violation]` (Q1-aware), `check_logs(log_file: str | None) -> list[Violation]`, `main() -> int`. `argparse` for optional `--log-file` and `--database-url` (defaults to env). Prints a PASS/FAIL table; `sys.exit(1)` on any violation. No writes, no plaintext printed (report row ids/column names, never bytes). |
| `qrng-eaas/api/qeaas/pool.py` | **Edit.** Add `parse_bits_bytes(raw: bytes) -> bytes` (move the strip/validate/pack body of `parse_bits_file` here; pack into a local `bytearray`, `burn` it before returning `bytes(packed)`). `parse_bits_file(path)` becomes `return parse_bits_bytes(Path(path).read_text().encode())` (or reads text then delegates). Add `ingest_bits_bytes(raw: bytes, source_label: str = "") -> int` = parse → `encrypt_chunk` → `db.insert_pool_chunk`, returns packed byte count. `ingest_bits_file` delegates to `ingest_bits_bytes`. Keep signatures backward-compatible for `scripts/ingest_bits.py`. |
| `qrng-eaas/api/main.py` | **Edit.** Rewrite `admin_ingest` (`main.py:173-200`): after the `.txt`/size guards, `content = bytearray(await file.read())`; `try: bytes_added = ingest_bits_bytes(bytes(content), file.filename) except ValueError: raise ApiError(422, "bad_request") finally: pool.burn(content)`. **Delete** the `tempfile.NamedTemporaryFile` block, the `tmp_path.unlink`, and the redundant `parse_bits_file` pre-parse. Drop the now-unused `tempfile`/`Path`/`parse_bits_file` imports if nothing else uses them (grep first — `parse_bits_file` may still be imported for the CLI; keep the import only if used in `main.py`). Response unchanged (`bytes_added`, `pool_bytes_remaining`). |
| `qrng-eaas/api/qeaas/db.py` | **Edit (only if the scan needs it).** Optionally add `list_table_columns() -> dict[str, list[str]]` (reads `information_schema.columns` for the connection's schema) so the scan's schema check is a parameterized `db.py` helper rather than inline SQL. If the scan can do this self-contained with parameterized SQL, skip this edit. |

### Docs / config (all Q1 options)
| File | Change |
|------|--------|
| `qrng-eaas/README.md` | **Edit.** Add "## Secure storage & the burn lifecycle (EPIC 10)" (Decision 5): master-key hierarchy, encrypt-at-rest, decrypt→use→burn, the honesty caveat, how to run `scripts/scan_persistence.py`, `MASTER_KEY`-rotation-as-future-work. Add a one-line runbook step: run the scan after ingest/deploy. |
| `qrng-eaas/api/.env.example` | **Edit.** One comment line under `MASTER_KEY`: point at `scripts/scan_persistence.py` as the persistence-invariant check (no new var). |

### Backend — encrypt the root key at rest (Q1 = RESOLVED: encrypt)
| File | Change |
|------|--------|
| `qrng-eaas/api/sql/005_root_key_encryption.sql` | **New.** Add `nonce bytea` + `tag bytea` columns to `drbg_root` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`); the existing `root_key` column now holds ciphertext. Header comment: root seed encrypted at rest under `drbg-root-encryption-key`. |
| `qrng-eaas/api/qeaas/pool.py` | **Edit.** No new primitive needed — reuse `encrypt_chunk`/`decrypt_chunk` with `derive_subkey("drbg-root-encryption-key")`; add thin `encrypt_root_key(seed: bytes) -> tuple[bytes,bytes,bytes]` / `decrypt_root_key(ct: bytes, nonce: bytes, tag: bytes) -> bytearray` wrappers for clarity. (Also the ingest refactor from Decision 2/3, above.) |
| `qrng-eaas/api/qeaas/db.py` | **Edit.** `save_root_key(ciphertext, nonce, tag, reseed_counter, outputs_since_reseed)`; `RootKeyRow` gains `nonce`/`tag`; `get_root_key` selects all three. (Plus the optional `list_table_columns()` scan helper, above.) |
| `qrng-eaas/api/qeaas/keyed_drbg.py` | **Edit.** `_bootstrap_root_key`/`maybe_reseed` `encrypt_root_key(material)` before `save_root_key`; `_load_cache` `decrypt_root_key(...)` into the warm cache, holding the plaintext root as a `bytearray` and `burn()`ing the previous one on `force=True` reload (closes gap 6). Legacy-row migration: if a loaded row has empty `nonce`/`tag`, treat it as legacy plaintext and re-save it encrypted on first read (or force a fresh reseed) — see Decision 6 / §6 Phase 3b. |
| `qrng-eaas/api/scripts/dev_db_up.sh` | **Edit.** The apply loop currently runs only `001-003` — add `004_provenance.sql` **and** `005_root_key_encryption.sql` so a fresh dev DB matches prod. |

**No changes** (all options) to `qeaas/drbg.py`, `qeaas/kem.py`, `qeaas/gate.py`, `qeaas/auth.py`,
`qeaas/receipts.py`, `qeaas/ratelimit.py`, `qeaas/redis_client.py`, `qeaas/schemas.py`,
`qeaas/generation.py`, `qeaas/dice.py`, `api/requirements.txt` (no new deps — `pycryptodome` already
pinned), `sql/001-004`, `api/tests/*`, or any `web/*` file. (EPIC 10 is backend + docs only; the web
app has no secure-storage surface.)

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — running service with a seeded, encrypted pool
Bring up local Postgres+Redis (`bash api/scripts/dev_db_up.sh`) with `MASTER_KEY` (64 hex chars),
`ADMIN_TOKEN`, `DATABASE_URL`, `REDIS_URL` set. Seed the pool from a `0/1` `.txt`
(`python api/scripts/ingest_bits.py <file>` or `POST /admin/ingest`). Confirm `GET /health` →
`"status":"ok"` with `pool_bytes_remaining > 0`.

### Phase 1 — ingest no longer touches disk (AC-3, AC-5)
Apply the `pool.py` + `main.py` edits. Then:
```bash
# ingest via HTTP; while it runs, confirm no plaintext .txt appears in the temp dir
curl -s -X POST http://localhost:8000/admin/ingest -H "X-Admin-Token: $ADMIN_TOKEN" \
  -F 'file=@sample_bits.txt' | jq .          # -> {ingested:true, bytes_added:N, pool_bytes_remaining:...}
ls -la "${TMPDIR:-/tmp}" | grep -i '\.txt$'  # -> no leftover ingest temp file (block removed)
```
Confirm the row landed as ciphertext:
```bash
psql "$DATABASE_URL" -c "SELECT id, octet_length(ciphertext), octet_length(nonce), octet_length(tag), plaintext_len, source_label FROM entropy_pool ORDER BY id DESC LIMIT 1;"
# nonce=12, tag=16, ciphertext length = plaintext_len; NO plaintext column exists
```

### Phase 2 — pool is unreadable without MASTER_KEY (AC-8a)
```bash
# with the real key, a reseed pull round-trips:
python -c "import os; from qeaas import pool; print(len(pool.pull_reseed_material(32)))"   # -> 32
# wrong/absent key -> GCM auth fails (fails closed):
MASTER_KEY=$(python -c "import secrets;print(secrets.token_hex(32))") \
  python -c "from qeaas import pool; pool.pull_reseed_material(32)"   # -> ValueError (MAC check failed)
```

### Phase 3 — decrypt→use→zeroize + GCM tamper detection (AC-4, AC-5, AC-8b/c)
```bash
python - <<'PY'
from qeaas import pool, db
row = db.next_unconsumed_chunk(16)
pt = pool.decrypt_chunk(row.ciphertext, row.nonce, row.tag)   # bytearray
assert isinstance(pt, bytearray)
pool.burn(pt); assert set(pt) == {0}                          # zeroized in place
# tamper: flip one ciphertext byte -> tag verify raises
bad = bytearray(row.ciphertext); bad[0] ^= 0x01
try:
    pool.decrypt_chunk(bytes(bad), row.nonce, row.tag); print("FAIL: no raise")
except ValueError: print("OK: GCM tamper detected")
PY
```

### Phase 3b — root key encrypted at rest (Q1 = encrypt; AC-1, AC-7)
Apply `sql/005_root_key_encryption.sql`, add the `drbg-root-encryption-key` path, then:
```bash
# force a reseed (or bootstrap) and confirm the stored root_key is ciphertext, with nonce+tag:
psql "$DATABASE_URL" -c "SELECT id, octet_length(root_key), octet_length(nonce), octet_length(tag), reseed_counter FROM drbg_root ORDER BY id DESC LIMIT 1;"
# nonce=12, tag=16, root_key is 32-byte ciphertext (not a bare readable seed)
# the DRBG still works end-to-end (decrypt into warm cache succeeds):
curl -s "http://localhost:8000/v1/random/bytes?size=32&format=hex" -H "X-API-Key: <key>" | jq .data   # non-empty
# wrong drbg-root-encryption-key (i.e. wrong MASTER_KEY) -> load fails closed (ValueError)
```
If a **legacy plaintext** `drbg_root` row exists from before this migration, confirm the bootstrap
re-encrypts it on first read (or forces a fresh reseed) rather than crashing — see Decision 6.

### Phase 4 — the persistence-invariant scan (AC-7, AC-8d)
Write `scripts/scan_persistence.py`, then:
```bash
python api/scripts/scan_persistence.py --log-file /path/to/uvicorn.log
# -> per-check table, every row PASS, exit 0:
#    entropy_pool: only ciphertext/nonce/tag/meta columns ....... PASS
#    entropy_pool.ciphertext: high-entropy, no plaintext match ... PASS
#    issue_log/usage_log: metadata only (no bytes column) ........ PASS
#    drbg_root.root_key: GCM ciphertext (nonce+tag present) ...... PASS
#    logs: no MASTER_KEY / no 0/1 QRNG runs ..................... PASS
echo $?    # 0
```
Negative check — prove the scan actually catches a violation (throwaway DB):
```bash
psql "$DATABASE_URL" -c "CREATE TABLE leak_test (bits text); INSERT INTO leak_test VALUES ('0101...');"
python api/scripts/scan_persistence.py; echo $?   # -> reports leak_test, exit 1
psql "$DATABASE_URL" -c "DROP TABLE leak_test;"
```

### Phase 5 — master key absent from DB & logs (AC-1)
```bash
# MASTER_KEY value must appear nowhere in the DB:
psql "$DATABASE_URL" -c "SELECT count(*) FROM entropy_pool WHERE encode(ciphertext,'hex') LIKE '%'||'$MASTER_KEY'||'%';"  # 0
grep -R "$MASTER_KEY" api/ 2>/dev/null || echo "OK: master key not in source/logs"
```
(The scan automates these in Phase 4; this is the manual cross-check.)

### Phase 6 — docs + final "Done when" pass
Add the README EPIC 10 section and `.env.example` note. Re-read the "Done when" clauses (build plan
line 301): pool unreadable without the env master key (Phase 2 ✓), decrypt→use→zeroize works
(Phase 3 ✓), GCM tampering detected (Phase 3 ✓), scan confirms no plaintext secrets persisted
(Phase 4 ✓). Confirm the README caveat states the zeroization limitation honestly (AC-6).

---

## 7. Design decisions carried from the epic / codebase (do not re-litigate)
- **Master-key hierarchy** — one `MASTER_KEY` in env only; HKDF-SHA256 derives every sub-key
  (`pool-encryption-key`/`receipt-signing-key`/`api-key-pepper`); it is **never** in Neon (build plan
  lines 290-291, 319; `pool.py:24-28`).
- **Pool is born encrypted** — AES-256-GCM per chunk, only ciphertext persists; plaintext decrypted
  only in memory to reseed, then burned (build plan lines 292-297; `pool.py`, EPIC 1 plan Q1).
- **Best-effort, not guaranteed, zeroization** — CPython can't guarantee it; `bytearray` overwrites +
  serverless teardown are the honest mitigations; **don't overclaim** (build plan line 297).
- **No new dependency** — AES-GCM/HKDF via already-pinned `pycryptodome`; **never** add
  `cryptography`/`pynacl` (pure-Python-wheel rule, build plan line 32).
- **No raw string SQL** — every query parameterized; the scan builds identifiers only from
  `information_schema` against an allow-list (`db.py` convention).
- **Fail closed** — GCM tag failure raises and blocks use; a degraded pool already returns `503` on
  premium endpoints (EPIC 1 gate) — unchanged here.
- **`entropy_epoch` = `drbg_root.reseed_counter`** — unchanged; EPIC 10 does not add the reseed-history
  table (EPIC 9 Q2).

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: MAC check failed` on every reseed | `MASTER_KEY` differs from the one the pool was ingested under | Pool ciphertext is bound to the master key; re-ingest under the current `MASTER_KEY`, or restore the original key. This is the AC-8 "unreadable without the key" property working as intended. |
| `admin_ingest` 422 `bad_request` on a valid-looking file | file has a `bits:` prefix or non-`0/1` chars | The contract is **plain `0/1` only** (EPIC 1, `parse_bits_bytes`); strip any prefix/header before upload. |
| Scan reports a `drbg_root.root_key` violation | Q1 default (allow-with-note) not wired, or Q1=encrypt not applied | Align the scan's `check_root_key` with the chosen Q1 option (allow-with-note vs assert-ciphertext). |
| Scan exits 0 but a plaintext column exists | column name not in the sensitive-name regex | Widen the regex / add the table to the explicit allow-list; prefer failing closed on unknown `bytea`/`text` columns in sensitive tables. |
| Leftover `*.txt` in temp dir after ingest | the `tempfile` block wasn't removed | Confirm `admin_ingest` now calls `ingest_bits_bytes(content, ...)` with no `NamedTemporaryFile`. |
| `KeyError: 'MASTER_KEY'` | env var unset in the API process | Set `MASTER_KEY` (dev: `.env`/`dev_db_up.sh`; prod: Vercel env). |
| `relation "drbg_root" has no column "nonce"` (Q1=encrypt) | `005_root_key_encryption.sql` not applied | `dev_db_up.sh` historically applies only `001-003`; apply `004`+`005` by hand (`psql -f`) and add them to the script (§5). |

## 11. Open questions — RESOLVED (developer, 2026-07-13)

**Q1 — `drbg_root.root_key` at rest → RESOLVED: ENCRYPT (stronger option).** Encrypt it under a new
`drbg-root-encryption-key` HKDF sub-key (AES-256-GCM); `sql/005` adds `nonce`/`tag`; `keyed_drbg`
encrypts before save and decrypts into the warm cache; the scan asserts ciphertext. S10.4 holds
literally. This also closes the warm-cache burn gap (gap 6). Full spec: §4 Decision 6, §5.

**Q2 — Log-scan scope → RESOLVED: `--log-file` only** (explicit, portable). README notes: also
eyeball the Vercel log stream for the master-key value after deploy.

**Q3 — Scan as a deploy gate → RESOLVED: hand-run script + a runbook line** in the README; CI wiring
is noted future work (no CI config added now).

**Q4 — `MASTER_KEY` rotation → RESOLVED: document as future work** (out of scope; no build).

**Q5 — Hand-rolled `derive_subkey` → RESOLVED: leave unchanged**, documented in the README as a
deliberate, audited HMAC-based KDF. (The new `drbg-root-encryption-key` rides this same
`derive_subkey`, consistent with the other three sub-keys.)

**Q6 — `consumed_offset` concurrency → RESOLVED: out of scope for EPIC 10** — noted as a follow-up
for the entropy-core/anti-abuse epics (`UPDATE ... RETURNING` under a row lock).

---

## 12. Summary for the developer

EPIC 10's crypto core (env-only master key, HKDF sub-keys, AES-256-GCM pool-at-rest, decrypt→use→burn
on reseed) **already shipped** in EPIC 1 by design — this epic **audits** those ACs, then delivers the
three genuinely-deferred pieces: the **S10.4 persistence-invariant scan** (`scripts/scan_persistence.py`),
**two ingest burn-lifecycle fixes** (no plaintext bits to disk; best-effort burn of upload buffers),
and the **honesty documentation** (master-key hierarchy + the "can't guarantee zeroization" caveat).
Plus, per the approved **Q1 = encrypt**, `drbg_root.root_key` is now **encrypted at rest** under a new
`drbg-root-encryption-key` HKDF sub-key (`sql/005`, `keyed_drbg`/`db`/`pool` edits), removing the last
plaintext seed so S10.4 holds literally and closing the warm-cache burn gap. No new dependencies, no
web changes, no automated tests. Q2-Q6 took their proposed defaults (log scan = `--log-file` only;
hand-run scan + runbook line; master-key rotation = future work; `derive_subkey` unchanged;
`consumed_offset` concurrency deferred).

## 13. Post-implementation notes

Built exactly per §5 File plan — no scope surprises during implementation. Manually verified end-to-end
against a local `dev_db_up.sh` stack (Postgres + Redis, migrations 001-005 applied): HTTP ingest leaves
no temp file and lands as GCM ciphertext; wrong `MASTER_KEY` fails closed on reseed; decrypt→use→burn
zeroizes in place; a flipped ciphertext byte is rejected; a live `/v1/random/bytes` call bootstrapped
`drbg_root` and the stored root key is 32-byte ciphertext with nonce/tag; `scan_persistence.py` exits 0
on a clean DB and exits 1 (naming the table) against a planted `leak_test(bits text)` table.

Follow-ups noted, not built (all pre-agreed out of scope): `MASTER_KEY` rotation/KMS envelope
encryption; a dedicated `entropy_epoch` history table; `consumed_offset` concurrency hardening; CI
wiring for the scan (currently a hand-run runbook step). `dev_db_up.sh` previously skipped
`004_provenance.sql` entirely — fixed alongside adding `005_root_key_encryption.sql` so a fresh dev DB
now matches prod.
