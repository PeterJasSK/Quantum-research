# Quantum Entropy-as-a-Service (Q-EaaS) — Build Plan

**One-line goal:** turn the QRNG bits you already collected into a small, free, hard-to-drain
web service that (1) hands out **quantum-seeded randomness & cryptographic seeds**, and
(2) **demonstrates a networking use** by seeding **ML-KEM (Kyber, post-quantum) key material** —
fronted by a phone-friendly web app with an explainer and a live dice player.

> **Framing (read once, repeat in the write-up):** QRNG does **not** "defeat quantum attackers."
> It supplies high-quality **entropy** that *seeds* a standards DRBG, which in turn seeds
> post-quantum algorithms (ML-KEM) and ephemeral session keys. The quantum part is the
> *entropy source*; the quantum *resistance* comes from ML-KEM. Say it exactly like that.

---

## Locked decisions (from Q&A)

| # | Decision |
|---|----------|
| 1 | New app. **Standalone FastAPI** backend + **Next.js (App Router) + Tailwind** web app, one Vercel project. |
| 2 | Public output is **DRBG-derived seeds / bytes only**. **Raw QRNG bits are never served** — they only reseed the DRBG internally. |
| 3 | **Dice / public** endpoints: anonymous + rate-limited. **Developer API**: requires an **API key** (per-user quota + revocable). |
| 4 | Consumer demo = **ML-KEM / Kyber** keypair, seeded from the QRNG→DRBG chain (pure-Python `kyber-py`). |
| 5 | Hosting starts on **Vercel free tier** (+ free Neon Postgres + free Upstash Redis for state). Revisit if limits bite. |
| 6 | Entropy runs low → **real gate**: `/health` reports `degraded`, premium (seed/KEM) endpoints return `503` until refilled; dice keeps working from the DRBG. |
| 7 | Canonical developer entropy endpoint is **`GET /v1/random/bytes`** (`/v1/seed` becomes an alias). Add **`POST /v1/verify`** scoped to **provenance/receipt verification only** — never a value-confirmation oracle. |
| 8 | Preloaded QRNG data is **encrypted at rest** with a quantum-derived master key; raw bits & seeds are **burned (best-effort zeroized)** after use; only ciphertext persists (see EPIC 10). |
| 9 | Reuse the **visual identity** of the old Django project (Orbitron font, deep-navy neon-cyan aesthetic) as design tokens — the *look*, not the literal CSS (see "Design system"). |

## Tech stack

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind, deployed on Vercel. Client components use `fetch()` — **no page reloads**, results swap in via React state. Mobile-first.
- **Backend:** FastAPI (Python) as Vercel serverless functions (ASGI). Keep `requirements.txt` **pure-Python wheels only**.
- **State (external, because serverless is stateless):**
  - **Neon Postgres** (free) — entropy pool, API keys, usage log, DRBG root-key rotation history. Use the **pooled** connection string.
  - **Upstash Redis** (free) — atomic counters for rate limits, per-key daily quota (TTL keys), the DRBG output counter.
- **Crypto:** `kyber-py` (ML-KEM / FIPS 203, pure Python) for the KEM; HMAC-DRBG (SP 800-90A) hand-rolled with `hmac`/`hashlib` (pure stdlib).
- **Validation:** your existing `qrng_compare.py` battery, reused to prove seed quality vs `/dev/urandom`.

> **Verify before relying on free tiers:** confirm current Vercel / Neon / Upstash free-tier limits at build time — they change.

## Design system (visual identity carried over)

Keep the **aesthetic and palette** of the old project — futuristic, dark, neon-cyan glow — but
re-express it as Tailwind tokens / CSS variables in the new app rather than porting the raw CSS.

```
Font:        Orbitron (Google Fonts), 400/600/700
Background:  radial-gradient(circle at center, #060c1f, #01040b)   /* deep navy → near-black */
Text:        #e3f6ff  (pale cyan-white)
Heading:     #7ad9ff  with glow  text-shadow: 0 0 10px #00aaff
Accent/link: #4dcfff
Primary:     #00aaff  (hover #0077cc)     buttons = rounded "pills" (radius ~30px), glow shadow
Borders:     rgba(0,170,255,0.35)         panels use backdrop-filter: blur + faint inner glow
```

- [ ] Define these as Tailwind `theme.extend.colors` + a couple of utility classes (`.glow`, `.pill`, `.panel`) so components inherit the look automatically.
- [ ] Mobile menu / sticky header vibe preserved; **do not** copy the Django CSS verbatim — tokens only.

---

## Architecture (serverless-safe)

```
 Your IBM QRNG runs  ──►  processed *.txt (bits:...)  ──►  [Admin ingest]  ──►  Neon: entropy_pool (raw bytes, private)
                                                                                        │  (pulled ONLY to reseed)
                                                                                        ▼
                                          root_key rotation  ◄──  HMAC-DRBG reseed  ◄────┘
                                                   │
                       Upstash: atomic counter ────┼───────────────┐
                                                   ▼               ▼
                                         DRBG.generate(n) = HMAC-DRBG(root_key, counter, n)     ← stateless-safe
                                                   │
        ┌──────────────────────────────┬──────────┴───────────┬───────────────────────────┐
        ▼                              ▼                       ▼                            ▼
  GET /random (dice, anon)   GET /v1/random/bytes (key)   POST /v1/kem/keypair (key)   GET /health (gate)
        │                              │                       │
        ▼                              ▼                       ▼
   Next.js dice player          developer clients        ML-KEM keygen seeded by DRBG  ──► networking demo
```

**Why the "keyed DRBG + atomic counter" pattern:** on stateless serverless you cannot safely
read-modify-write a classic DRBG state on every request (two concurrent requests could reuse the
same state → identical output = catastrophic). Instead keep only a **monotonic counter** in Redis
(atomic `INCR`) and compute output as `HMAC-DRBG(root_key, counter_value, n_bytes)`. The `root_key`
is rotated ("reseeded") from the QRNG pool periodically. Only `INCR` needs to be atomic, which Redis
guarantees natively.

---

# EPICS

Each epic has a **Goal**, **Stories** (with task checkboxes), and **Acceptance criteria (Done when…)**.
Priority tags: `[MUST]` core to the two deliverables, `[SHOULD]` strongly wanted, `[COULD]` stretch.

---

## EPIC 0 — Project scaffolding & spikes `[MUST]`

**Goal:** a running monorepo skeleton and the one risky unknown resolved before real work starts.

- **S0.1 Repo layout**
  - [ ] Create repo: `/web` (Next.js), `/api` (FastAPI), `/shared` (docs, diagrams), root `vercel.json`.
  - [ ] `api/requirements.txt` with **pure-Python** deps only (`fastapi`, `kyber-py`, `redis`, `psycopg[binary]` or `asyncpg`, `python-dotenv`).
  - [ ] Local dev: `uvicorn` for API, `next dev` for web; `.env.local` for secrets.
- **S0.2 SPIKE — ML-KEM randomness injection** *(do this first; it de-risks EPIC 4)*
  - [ ] Confirm how to feed **our** bytes into `kyber-py` keygen (randomness hook / seed). If not clean, fall back to the `mlkem` package which accepts `randomness=f(int)->bytes`.
  - [ ] Write a 10-line script: `DRBG.generate(64)` → ML-KEM-768 `keygen()` → assert deterministic output for a fixed seed. **This is the whole project's core wiring.**
- **S0.3 SPIKE — Vercel build sanity**
  - [ ] Deploy a hello-world Next.js + FastAPI to Vercel; confirm the Python function builds with the real `requirements.txt` (catch native-wheel failures early).

**Done when:** the skeleton deploys to Vercel, and a local script proves QRNG-DRBG bytes drive ML-KEM keygen deterministically.

---

## EPIC 1 — Entropy core (DRBG + pool + gate) `[MUST]`

**Goal:** a correct, testable randomness engine that stretches finite QRNG bits into effectively
unlimited output and knows when it's running low.

- **S1.1 HMAC-DRBG (SP 800-90A)**
  - [ ] Implement `instantiate(seed)`, `reseed(seed)`, `generate(n)` with `hmac`+`hashlib` (SHA-256).
  - [ ] Unit-test against published **HMAC-DRBG KAT vectors** (must match exactly).
- **S1.2 Keyed-DRBG serverless wrapper**
  - [ ] `output(n)` = `HMAC-DRBG(root_key, INCR(counter), n)`; counter from Upstash (atomic).
  - [ ] Load `root_key` from Neon; cache in the warm function instance.
- **S1.3 Entropy pool + reseed policy**
  - [ ] Neon table `entropy_pool` holds raw QRNG bytes + `consumed_offset` (bytes never leave except to reseed).
  - [ ] Reseed `root_key` from the pool every **T minutes OR K outputs OR reseed_counter limit** (SP 800-90A interval); advance `consumed_offset`.
- **S1.4 Low-entropy gate (decision #6)**
  - [ ] `pool_remaining < THRESHOLD` → status `degraded`; block `/v1/seed` & `/v1/kem/*` with `503 {"error":"low_quantum_entropy"}`; add header `X-Quantum-Entropy: degraded` to all responses; dice/`/random` keep serving from current DRBG.

**Done when:** DRBG passes KATs; output is unique across concurrent calls; reseed advances the pool; the gate flips to `degraded` under threshold and back after refill.

---

## EPIC 2 — Public API surface `[MUST]`

**Goal:** clean, documented endpoints (FastAPI auto-OpenAPI at `/docs`).

- **S2.1 Endpoints**
  - [ ] `GET /health` → `{status, quantum_entropy_level, pool_bytes_remaining, drbg_reseeds, uptime}`.
  - [ ] `GET /random?bytes=N` → DRBG bytes (base64). **Anon**, capped small (e.g. `N ≤ 64`). Powers dice.
  - [ ] `POST /dice` `{sides, count}` → rolls (uses `/random` internally; rejection sampling — reuse your `generate_numbers` logic to avoid modulo bias).
  - [ ] `GET /v1/random/bytes?size=N&format=hex|base64` → `{request_id, format, data, entropy_epoch, timestamp, receipt}`. **API key required**, `32 ≤ N ≤ 4096`, quota-metered. **Canonical** developer entropy endpoint.
  - [ ] `GET /v1/seed?bytes=N` → **alias** of `/v1/random/bytes` (kept for compatibility; same engine, same limits).
  - [ ] `POST /v1/verify` `{request_id | receipt}` → signed provenance metadata (see EPIC 9). **Not** a value-confirmation oracle.
  - [ ] `POST /admin/ingest` → upload fresh `bits:` file to refill the pool (admin token).
  - [ ] `POST /admin/keys` → mint an API key (admin token).
- **S2.2 Schemas & errors**
  - [ ] Pydantic models for every request/response; consistent error envelope; CORS for the web origin.

**Done when:** all endpoints work locally, `/docs` renders, and error/edge cases (bad `bytes`, missing key, over-quota) return correct codes.

---

## EPIC 3 — Anti-abuse: "no one can raid my bits" `[MUST]`

**Goal:** anonymous fun stays cheap and bounded; the real API is keyed, quota'd, revocable.

- **S3.1 Public rate limiting (dice / `/random`)**
  - [ ] Per-IP sliding window in Upstash: e.g. **60 req/min/IP**, `bytes ≤ 64/req`.
  - [ ] **Global daily ceiling** for anon output (e.g. 5 MB/day) → over-limit returns `429`.
- **S3.2 API keys (developer / IoT)**
  - [ ] `api_keys` table: store **hash** of key (never plaintext), `owner`, `tier`, `daily_quota_bytes`, `revoked`.
  - [ ] Middleware: validate `X-API-Key`, enforce per-key daily quota via Upstash TTL counter, per-key rate limit.
  - [ ] Tiers: `default` (small daily quota) vs `iot`/`trusted` (higher) — matches the IoT story.
- **S3.3 Bit-drain protection (the actual worry)**
  - [ ] Because output is DRBG-derived, huge request volume costs **near-zero QRNG bits** (reseed pulls are tiny & time-boxed). Document this as the core anti-raid property.
  - [ ] Cap reseed frequency so even unlimited traffic can't accelerate pool drain.
  - [ ] Usage log (`usage_log`) for spotting abuse; ability to revoke a key instantly.

**Done when:** hammering `/random` hits `429` not the pool; an over-quota API key is refused; a revoked key stops working immediately; pool drain is decoupled from request volume.

---

## EPIC 4 — ML-KEM consumer (the crypto payload) `[MUST]`

**Goal:** demonstrate quantum entropy seeding **post-quantum** key material.

- **S4.1 QRNG-seeded keygen**
  - [ ] `POST /v1/kem/keypair` (API key) → generate **ML-KEM-768** `(ek, dk)` using `DRBG.generate(64)` as the randomness. Return `ek` (public) always; return `dk` only for the demo flow with a loud "demo only — real keygen happens client-side" note.
  - [ ] Respect the low-entropy gate (503 when degraded).
- **S4.2 Encapsulation (for the networking demo)**
  - [ ] `POST /v1/kem/encapsulate` `{ek}` → `{ciphertext}` (+ optionally a KDF-derived demo key). Decapsulation happens on the holder of `dk`.
- **S4.3 Honesty & correctness**
  - [ ] README note: `kyber-py` is **educational / not constant-time** — correct for a thesis demo, not production. For production, swap to `liboqs` on a persistent host.
  - [ ] Test: `keygen → encaps → decaps` round-trips to the same shared secret.

**Done when:** an API client can obtain a QRNG-seeded ML-KEM keypair and complete a working encaps/decaps round-trip.

---

## EPIC 5 — Web app: explainer + dice (phone-first, no reload) `[MUST]`

**Goal:** a page that explains everything and lets you play dice with quantum-seeded numbers,
smooth on a phone, never reloading on submit.

- **S5.1 Explainer**
  - [ ] Sections: "What is a QRNG", the pipeline diagram (quantum bits → DRBG → seeds/keys), "How to use the API" (with an example `curl` + API-key note), and the honest crypto framing.
  - [ ] Live **`/health` widget**: green "Quantum entropy: healthy" / amber "degraded" badge.
- **S5.2 Dice player**
  - [ ] Controls: dice type (d6/d20/custom sides) + count; big **Roll** button.
  - [ ] On roll: `fetch('/dice')`, `preventDefault`, update React state → **no page refresh**; show result with a short animation.
  - [ ] "Show the quantum bytes behind this roll" toggle (transparency + teaching).
- **S5.3 Phone-friendliness**
  - [ ] Mobile-first Tailwind; large tap targets; one-handed layout; `viewport` meta; test at ~380px width; loading/disabled states so double-taps don't double-fire.

**Done when:** on a phone, rolling dice updates in place without reload, the health badge reflects real status, and the explainer makes the system self-describing.

---

## EPIC 6 — Persistence & deployment `[MUST]`

**Goal:** everything runs on the free stack, wired to external state.

- **S6.1 Datastores**
  - [ ] Provision Neon (pooled URL) + Upstash; create tables/keys; store creds as Vercel env vars.
- **S6.2 Deploy**
  - [ ] Next.js + FastAPI in one Vercel project (Services); confirm cold-start latency is acceptable; keep ML-KEM-768 (keygen ~tens of ms << 10s timeout).
  - [ ] Smoke-test every endpoint on the deployed URL from your phone.

**Done when:** the public URL serves the web app and all endpoints, with state surviving across serverless invocations.

---

## EPIC 7 — Validation: prove the seeds are good `[SHOULD]`

**Goal:** quantitative evidence, reusing what you already built.

- **S7.1 Seed-quality report**
  - [ ] Pull ~1–2 MB from `/v1/seed`, save as a `bits:` file, run **`qrng_compare.py`** against `/dev/urandom` (and optionally a raw QRNG sample) → bias / NIST / next-bit / Markov / dieharder.
  - [ ] Include the PDF in the thesis appendix: "DRBG output is statistically indistinguishable from OS CSPRNG, and is quantum-seeded."
- **S7.2 Service tests**
  - [ ] Unit: DRBG KATs, rate-limit, quota, gate flip. Integration: end-to-end key round-trip.

**Done when:** a report shows the served seeds pass the battery, and core logic has automated tests.

---

## EPIC 8 — Networking demonstration & write-up `[MUST]`

**Goal:** show *where* quantum entropy plugs into networking — the "second thing."

- **S8.1 Working handshake demo**
  - [ ] Script/endpoint with two roles: **Server** holds a QRNG-seeded ML-KEM keypair; **Client** encapsulates to `ek` → shared secret; both derive an AES-GCM key and exchange one encrypted message.
  - [ ] Log that keygen/encaps randomness came from the QRNG→DRBG chain.
- **S8.2 Mapping to real networking (from your notes, framed honestly)**
  - [ ] Short doc: **ephemeral TLS/VPN keys** (forward secrecy), **WireGuard ephemeral keys**, **SDN control-plane seeding / moving-target**, **ECMP hash salt** (break load-balancer collisions), **IoT seed distribution** (central quantum entropy → weak-RNG edge devices via API-key tiers).
  - [ ] For each: one sentence on what QRNG entropy contributes and its honest scope (entropy, not magic).

**Done when:** a reproducible demo derives a shared secret from QRNG-seeded ML-KEM, and the doc maps it to concrete networking use cases.

---

## EPIC 9 — Provenance & verification (receipts, `/v1/verify`) `[SHOULD]`

**Goal:** let users trust an issued value's origin **without** ever storing the value or turning the
service into a secret-confirming oracle.

**Principle:** verify **provenance, not the secret**. Every generating response ships a signed
*receipt* over its metadata; `/v1/verify` re-checks that signature and resolves the entropy epoch.
The output bytes themselves are **never** persisted.

- **S9.1 Server signing key**
  - [ ] Ed25519 (or HMAC-SHA256) signing key, derived via HKDF from the master (EPIC 10) or its own secret env var; public key published for client-side verification.
- **S9.2 Receipts on every issue**
  - [ ] On `/v1/random/bytes` and `/v1/kem/*`, attach `receipt = sign(request_id, size, entropy_epoch, timestamp)`. Log `request_id → (epoch, size, ts)` in Neon (metadata only, **no bytes**).
- **S9.3 `POST /v1/verify`**
  - [ ] Input `{request_id}` and/or `{receipt}` → return signed metadata: when generated, which **QRNG batch/epoch** seeded it, and receipt validity. Tampered/forged receipts fail.
  - [ ] Optional: if the caller returns the value **together with its receipt**, confirm the receipt is authentic — still without the service having stored the value.
- **S9.4 Web "Verify a receipt" box**
  - [ ] Small form on the explainer page: paste `request_id`/receipt → show provenance. Reinforces trust, phone-friendly.

**Done when:** an issued value's receipt verifies and resolves to a real QRNG batch; a forged receipt is rejected; no output bytes are stored anywhere.

---

## EPIC 10 — Secure storage & the entropy "burn" lifecycle `[MUST]`

**Goal:** the large preloaded QRNG dataset lives **encrypted at rest**; keys derive from quantum
entropy; raw bits and seeds are **burned** after use; only ciphertext persists.

**The daily lifecycle (as specified):**
1. **Collect** 256 bits of quantum entropy — the "gold standard" for AES-256.
2. **Seed creation:** use the 256 bits as the **master key** (or via HKDF for multiple sub-keys).
3. **The burn:** immediately overwrite the memory holding the raw 256 bits; after the day's crypto is done, zero out the memory holding the master seed.
4. **Persist:** store only the **encrypted** data.

- **S10.1 Master key management**
  - [ ] The 256-bit quantum master key lives **only** as a secret (Vercel env / KMS) — **never** in the DB next to the ciphertext it protects.
  - [ ] HKDF-SHA256 derives named sub-keys: `pool-encryption-key`, `receipt-signing-key`, `api-key-pepper`.
- **S10.2 Encrypt the preloaded pool at rest**
  - [ ] Store the QRNG pool as **AES-256-GCM** ciphertext (nonce + tag per chunk) in Neon; plaintext bits are **never** written to disk/DB.
  - [ ] On reseed, decrypt only the needed chunk in memory, use it, then burn it.
- **S10.3 The "burn" (best-effort zeroization)**
  - [ ] Hold sensitive material in `bytearray`, overwrite with zeros after use; drop references promptly.
  - [ ] **Honesty caveat:** Python can't guarantee zeroization (immutable `bytes`, GC, copies) — this is best-effort. Two things help here: use `bytearray` overwrites for anything long-lived, and lean on **serverless teardown** (Vercel destroys the function instance after the request, so in-process secrets are short-lived by design). Document this limitation; don't overclaim.
- **S10.4 Persistence rule**
  - [ ] Invariant test: grep the DB/logs — no plaintext QRNG bytes, no plaintext master/seed, ever. Only ciphertext + metadata.

**Done when:** the pool is unreadable at rest without the env-held master key; decrypt→use→zeroize works; GCM tampering is detected; and a scan confirms no plaintext secrets are persisted.


---

# Cross-cutting

## Data model (Neon)

| Table | Key fields |
|-------|-----------|
| `entropy_pool` | `id, ciphertext (bytea, AES-256-GCM), nonce, tag, consumed_offset, source_label, uploaded_at` |
| `drbg_root` | `id, root_key (secret ref), reseed_counter, outputs_since_reseed, rotated_at` |
| `entropy_epoch` | `epoch_id, qrng_source_label, reseed_counter, started_at`  *(metadata only — powers `/v1/verify`)* |
| `api_keys` | `key_hash, owner, tier, daily_quota_bytes, revoked, created_at` |
| `issue_log` | `request_id, principal, endpoint, size, epoch_id, ts`  *(no output bytes)* |
| `usage_log` | `ts, principal (ip/key_hash), endpoint, bytes` |

**Secrets (env / KMS, never in DB):** `MASTER_KEY` (256-bit quantum), from which HKDF derives the
pool-encryption key, receipt-signing key, and API-key pepper.

**Upstash (Redis):** `drbg:counter` (INCR), `rl:ip:{ip}` (window), `quota:key:{hash}:{yyyymmdd}` (TTL).

## Risks & mitigations

- **ML-KEM randomness injection unclear** → SPIKE S0.2 first; fallback to `mlkem` package (`randomness=` param).
- **Native wheels break Vercel build** → keep deps pure-Python; verify in S0.3.
- **Serverless statelessness / races** → keyed-DRBG + atomic counter (EPIC 1).
- **Postgres connection storms from serverless** → Neon pooled connection string.
- **Free-tier limits** → verify current Vercel/Neon/Upstash quotas; if exceeded, move API to Render/Fly (decision #5 revisit).
- **Crypto misrepresentation** → repeat the "entropy, not quantum-resistance" framing everywhere.

## 2-day schedule

**Day 1 — make it work locally**
1. S0.1–S0.3 scaffolding + spikes (resolve ML-KEM wiring). *(morning)*
2. EPIC 1 DRBG + pool + gate, with KAT tests; **EPIC 10** encrypt-at-rest + burn wired into the pool from the start. *(midday)*
3. EPIC 2 endpoints locally (incl. `/v1/random/bytes`); EPIC 3 rate-limit/keys (in-memory first). *(afternoon)*
4. EPIC 5 web app skeleton + dice working locally, **design tokens** (Orbitron/neon) applied. *(evening)*

**Day 2 — make it real & tell the story**
5. EPIC 6 wire Neon + Upstash, deploy to Vercel, phone smoke-test. *(morning)*
6. EPIC 4 ML-KEM endpoint + round-trip; **EPIC 9** receipts + `/v1/verify`. *(midday)*
7. EPIC 8 networking demo + mapping doc. *(afternoon)*
8. EPIC 7 seed-quality report; polish explainer, health badge, verify box, docs. *(evening)*

## Definition of Done (whole project)

- [ ] Public URL: phone-friendly web app (old project's neon aesthetic) with explainer + no-reload dice + verify box.
- [ ] `/random` (anon, rate-limited) and `/v1/random/bytes` (API key, quota'd, `/v1/seed` alias) live; raw QRNG bits never exposed.
- [ ] Bit-drain decoupled from traffic; keys revocable; low-entropy gate real.
- [ ] Preloaded pool encrypted at rest with quantum-derived master key; burn lifecycle in place; no plaintext secrets persisted.
- [ ] Every issued value carries a signed receipt; `/v1/verify` resolves provenance without storing outputs.
- [ ] QRNG-seeded ML-KEM keypair + working encaps/decaps round-trip.
- [ ] Networking demo derives a shared secret from QRNG-seeded keys + honest mapping doc.
- [ ] Seed-quality PDF from `qrng_compare.py` attached.

## Stretch `[COULD]`
- [ ] X25519/WireGuard ephemeral key alongside ML-KEM (classic contrast).
- [ ] Signed "entropy certificate" (hash of QRNG batch + run metadata) for provenance.
- [ ] Prometheus-style `/metrics`; simple admin dashboard for pool level & key usage.
