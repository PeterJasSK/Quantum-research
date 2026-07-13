# Feature Plan — EPIC 8: Networking demonstration & write-up

**Status:** Complete (implemented + manually verified 2026-07-13)
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 8 `[MUST]`
**Interpretation of "epic 8":** EPIC 8. EPICS 1–7 are Complete (entropy core, public API,
anti-abuse, ML-KEM consumer, web app, deployment, seed-quality validation). EPIC 4 already ships
the two KEM endpoints this epic drives (`POST /v1/kem/keypair`, `POST /v1/kem/encapsulate`), the
QRNG→DRBG randomness chain (`qeaas.generation.random_bytes`), and a single-actor round-trip script
(`api/scripts/kem_roundtrip.py`). EPIC 4 **explicitly deferred** the full handshake demo to here
(`feature-epic4-mlkem-consumer.md` lines 115-117).

> **Scope note — front-end is IN scope (developer request, 2026-07-13).** The build plan's EPIC 8
> literally says "Script/endpoint" (S8.1) + "Short doc" (S8.2). The developer has asked that **the
> demo be visible in the web front end**, not only as a CLI script. This plan therefore covers
> **three** deliverables: (a) the reproducible CLI handshake demo (S8.1, the rigorous artifact),
> (b) an **interactive web page** that visualizes the same QRNG-seeded ML-KEM → AES-GCM handshake
> live in the browser (the developer's added requirement), and (c) the networking-mapping write-up
> (S8.2), surfaced both as a committed doc and on the demo page. ACs AC-8/AC-9 below are this
> added front-end requirement, marked as an extension beyond the build plan's literal text.

> **No automated tests in this plan.** Per the current project directive: production/demo code + a
> written doc + manual verification only — no pytest/component/e2e test files, no "Testing
> approach" section, no AC-to-test mapping. Verification is manual: **run the CLI script and read
> its output**, **open the demo page in a browser (desktop + ~380px) and run the handshake**, and
> **read the doc**. Existing KEM/DRBG unit coverage from EPICS 1–4 is untouched.

---

## 1. Context & goal

Deliver the build plan's "second thing": show **where quantum entropy plugs into networking**, and
(per the developer's request) make that demonstration **visible and runnable in the web app**.

- **S8.1 — CLI handshake demo (rigorous, reproducible).** Two roles: a **Server** holding a
  **QRNG-seeded ML-KEM-768** keypair, a **Client** that encapsulates to `ek` → shared secret; both
  derive an **AES-GCM** key and exchange one encrypted message; the Server independently
  decapsulates to prove both parties agree on the shared secret. Logs that keygen and encaps
  randomness came from the QRNG→DRBG chain.
- **Front-end demo (developer request).** A web page/section that drives the **real** KEM endpoints
  through a **server-side proxy** (so the API key never reaches the browser) and visualizes each
  step live, no page reload: Server keygen (QRNG-seeded, with provenance shown) → Client
  encapsulate (QRNG-seeded, provenance shown) → derive the AES-GCM key → encrypt/decrypt one
  message **in the browser via Web Crypto**.
- **S8.2 — honest mapping doc.** The five networking use cases (ephemeral TLS/VPN keys, WireGuard
  ephemeral keys, SDN control-plane / moving-target, ECMP hash salt, IoT seed distribution), one
  honest sentence each — committed as a doc **and** surfaced on the demo page.

### What already exists — backend integration points
- **KEM service module** `qrng-eaas/api/qeaas/kem.py`:
  - `generate_keypair() -> tuple[bytes, bytes]` (`kem.py:47-51`) — `seed = generation.random_bytes(64)`
    then `ek, dk = ML_KEM_768.key_derive(seed)`. **Keygen randomness is QRNG→DRBG.**
  - `encapsulate(ek: bytes) -> tuple[bytes, bytes]` (`kem.py:54-67`) — `m = generation.random_bytes(32)`
    then `shared_secret, ciphertext = ML_KEM_768._encaps_internal(ek, m)` (**encaps randomness also
    QRNG→DRBG**). Return **order: `(shared_secret, ciphertext)`**.
  - `derive_demo_key(shared_secret) -> bytes` (`kem.py:70-76`) — `HKDF(shared_secret, 32, b"", SHA256)`
    → 32-byte AES-GCM key; docstring: "purely illustrative of the key EPIC 8's networking demo will
    derive." **This is exactly the derivation both demos use.**
- **KEM endpoints** `qrng-eaas/api/main.py`:
  - `POST /v1/kem/keypair` (`main.py:221-244`) — `public_key` (base64 `ek`) always; `secret_key`
    (base64 `dk`) + loud demo `note` (`_DEMO_SECRET_KEY_NOTE`, `main.py:211-214`) only when body
    `include_secret_key: true`.
  - `POST /v1/kem/encapsulate` (`main.py:247-277`) — decodes `public_key` (base64) → `422` on bad
    input; `ciphertext` always; `shared_secret` + `demo_key` (=`base64(kem.derive_demo_key(ss))`,
    `main.py:271`) + note (`_DEMO_SHARED_SECRET_NOTE`, `main.py:215-218`) only when
    `include_shared_secret: true`.
  - Both routes: `Depends(require_api_key)` (reads `X-API-Key`; missing→401 `missing_api_key`,
    unknown→401 `invalid_api_key`, `auth.py:32-37`), `Depends(require_entropy)` (→`503
    low_quantum_entropy` when degraded), `ratelimit.enforce_key`, `db.insert_usage_log`. Every
    response carries `generation.new_issue_meta()` → `{request_id, entropy_epoch, timestamp,
    receipt: null}` — the provenance evidence for AC-3.
- **CLI analogue** `api/scripts/kem_roundtrip.py` — stdlib-`urllib` HTTP client (imports **only**
  `kyber_py`, no `qeaas`): POST keypair (`include_secret_key`), POST encapsulate
  (`include_shared_secret`), local `ML_KEM_768.decaps(dk, ct)`, assert `== shared_secret`. **Gap
  vs S8.1:** no AES-GCM key derivation, no encrypted-message exchange, no two-role framing, no
  provenance logging. Env `API_KEY`, `--base-url` (default `http://localhost:8000`, env `API_BASE`).
- **AES-GCM in code** `api/qeaas/pool.py:37-46` — **pycryptodome** (`from Crypto.Cipher import AES`;
  `AES.new(key, AES.MODE_GCM, nonce=os.urandom(12), mac_len=16)`; `encrypt_and_digest` /
  `decrypt_and_verify`). **HKDF** `from Crypto.Protocol.KDF import HKDF` (`kem.py:26,76`).
- **`api/requirements.txt`** — `kyber-py==1.2.0`, `pycryptodome==3.23.0` already present. **No new
  Python dep**; never add `cryptography`.
- **`api/scripts/` convention** — `#!/usr/bin/env python`, docstring w/ `Usage:` block,
  `from __future__ import annotations`, `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`,
  `argparse(description=__doc__)`. Run `python -m scripts.<name>` from `api/`.

### What already exists — web integration points (Next.js 16.2.10 App Router, React 19, Tailwind v4)
> `qrng-eaas/web/AGENTS.md`: "This is NOT the Next.js you know — read `node_modules/next/dist/docs/`
> before writing code." The implementer **must** read the Next 16 route-handler + client-component
> docs before writing the proxy/component below; conventions differ from older Next.

- **Structure** — `app/layout.tsx` (Header + `<main>` + Footer), `app/page.tsx` (explainer home,
  composes sections), `app/dice/page.tsx` (dedicated interactive route — **the precedent for the
  demo page**). Components in `components/` and `components/sections/`. Data-fetch helpers in
  `lib/api.ts`. `next.config.ts` is **empty** (no rewrites/proxy). Path alias `@/*`.
- **Client-fetch pattern** (mirror this) — `components/DicePlayer.tsx`: `"use client"` first line;
  imports typed helper from `@/lib/api`; `useState` for `result`/`loading`/`error`; submit handler
  `event.preventDefault()` → guard `if (loading) return` → `try/await helper/setResult` →
  `catch/setError(messageFor(err))` → `finally/setLoading(false)`; result swaps in via state (no
  reload); framer-motion for the reveal; button `disabled={loading}`. Backend error slugs → friendly
  copy via an `ERROR_MESSAGES` map + `messageFor()`.
- **API base + fetch wrapper** `lib/api.ts` — `export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api"`;
  `requestJson<T>(path, init?)` prepends `API_BASE`, throws `ApiError(slug)` on non-2xx by parsing
  `{"error":"<slug>"}`. Existing helpers `getHealth()`, `rollDice(sides,count)`. **New KEM helpers
  go here.**
- **API-key handling (the crux)** — the browser currently sends **no** credentials and there is
  **no** proxy: `/health`, `/dice`, `/random` go **directly** browser→FastAPI via
  `NEXT_PUBLIC_API_BASE` relying on CORS. The KEM routes need `X-API-Key`. **There is no existing
  server-side route handler / server action / proxy to reuse** (no `route.ts` anywhere;
  `next.config.ts` empty). So a keyed KEM call **cannot** be made the browser-direct way without
  leaking the key → **a new Next route-handler proxy is required** (Decision 2).
- **FastAPI CORS** (`api/main.py:42-50`) — `CORSMiddleware`, `allow_origins` from `WEB_ORIGIN`
  (default `http://localhost:3000`), `allow_headers=["*"]`. A same-origin Next proxy route sidesteps
  CORS entirely for the keyed calls.
- **Design tokens** `app/globals.css` (Tailwind v4 `@theme`/`@utility`, no config file): colors
  `bg-deep #01040b`, `bg #060c1f`, `text #e3f6ff`, `heading #7ad9ff`, `accent #4dcfff`, `primary
  #00aaff`/hover `#0077cc`, `border rgba(0,170,255,0.35)`; utilities `.glow`, `.pill`, `.panel`;
  Orbitron font via `next/font/google`. **No Button/Badge/CodeBlock primitives** — compose inline
  like `ApiUsage.tsx` (`<pre className="overflow-x-auto text-xs text-accent"><code>…`) and
  `HealthBadge.tsx` (inline status pill styles).
- **`web/package.json`** — `next 16.2.10`, `react 19.2.4`, `framer-motion`, `clsx`, `react-icons`;
  `axios` installed but **forbidden** (EPIC 5 mandate: use native `fetch`). **No client-side crypto
  lib** — use the browser-native **Web Crypto API** (`crypto.subtle`) for AES-GCM; base64 via
  `atob`/`Uint8Array`. There is **no JS ML-KEM library** (see Decision 4 / Q4).
- **EPIC 5 locked frontend rules** (`feature-epic5-web-app.md`) — no page reload; native `fetch`
  not axios; fetch/typing in `lib/api.ts` not JSX; strict TS no `any`; `"use client"`; mobile-first,
  tap targets ≥44px, works at ~380px, disabled/loading states; tokens only; typed `ApiError` from
  backend slug, surfaced inline; read Next 16 docs first.

---

## 2. Acceptance criteria

AC-1..AC-7 are the build plan's EPIC 8 text (lines 240-251), verbatim intent. AC-8/AC-9 are the
developer's front-end requirement (2026-07-13), marked as an extension.

| AC | Source (verbatim intent) | Covered by |
|----|--------------------------|------------|
| **AC-1** | S8.1: "two roles: **Server** holds a QRNG-seeded ML-KEM keypair; **Client** encapsulates to `ek` → shared secret." — The CLI demo obtains a **QRNG-seeded ML-KEM-768** keypair (Server, keeps `dk`) and the Client encapsulates to `ek` → shared secret. | `api/scripts/kem_handshake.py:106-124` (`run_demo`; `Server`/`Client` classes at `:77-104`); manually verified — run produced `[Server] keygen` / `[Client] encapsulate` log lines. |
| **AC-2** | S8.1: "both derive an **AES-GCM** key and exchange one encrypted message." — Both roles derive the same AES-256-GCM key from the shared secret via `HKDF(shared_secret,32,b"",SHA256)` (identical to `kem.derive_demo_key`); one message is encrypted by one role and decrypted+authenticated by the other. | `api/scripts/kem_handshake.py:66-67` (`_derive_key`), `:87-92`/`:101-103` (`Server.encrypt`/`Client.decrypt`), `:142-143` (encrypt→decrypt call); verified: CLI run printed `OK: Client decrypted Server message: 'hello from the QRNG-seeded ML-KEM demo'`. Browser side: `web/components/KemHandshakeDemo.tsx:101-108` (import demo_key as AES-GCM key), `:124-146` (`onExchangeSubmit` encrypt→decrypt); verified via Node `webcrypto` against a live `demo_key`/`shared_secret` pair — round-trip recovered the exact plaintext. |
| **AC-3** | S8.1: "**Log** that keygen/encaps randomness came from the QRNG→DRBG chain." — Both the CLI script and the web page surface, for the keygen **and** the encaps step, the service provenance (`request_id`, `entropy_epoch`) and state plainly the randomness is QRNG-seeded DRBG output. | `api/scripts/kem_handshake.py:70-72` (`_log_provenance`, called at `:110` and `:121`); verified CLI output shows `request_id=...` `entropy_epoch=0` for both steps. `web/components/KemHandshakeDemo.tsx:174-183` (keygen step, "QRNG-seeded" pill + `request_id`/`entropy_epoch`), `:193-207` (encaps step same). |
| **AC-4** | Done when: "a **reproducible** demo derives a shared secret from QRNG-seeded ML-KEM." — The CLI script runs end-to-end against the running service and asserts Server local `ML_KEM_768.decaps(dk,ct)` equals the Client shared secret; prints a clear PASS. | `api/scripts/kem_handshake.py:134-139` (`server.decapsulate` + assert), `:146` (`print("PASS")`); verified by two independent runs against a live local service — both printed `PASS` with a different `request_id`/message each time (reproducibility). |
| **AC-5** | S8.2: use cases "**ephemeral TLS/VPN keys** (forward secrecy), **WireGuard ephemeral keys**, **SDN control-plane seeding / moving-target**, **ECMP hash salt**, **IoT seed distribution**." — A committed doc covers all five. | `shared/docs/networking-demo.md` §"Mapping to networking" (all five use cases, each its own bullet). |
| **AC-6** | S8.2: "For each: **one sentence** on what QRNG entropy contributes and its **honest scope** (entropy, not magic)." — Each use case has one honest sentence; the doc repeats the "entropy, not quantum-resistance" framing (matching `kem.py:3-7` / README EPIC 4). | `shared/docs/networking-demo.md` §"Honest framing" + one-sentence-per-use-case in §"Mapping to networking". |
| **AC-7** | Done when: "the doc **maps it to concrete networking use cases**." — The doc explicitly ties the demo (QRNG-seeded ML-KEM → AES-GCM channel) to the five use cases. | `shared/docs/networking-demo.md`, closing paragraph of §"Mapping to networking" ("The demo above ... is the concrete mechanism behind all five ..."). |
| **AC-8** | **Developer request:** the handshake demo is **visible and runnable in the web front end** — an interactive page/section where the user triggers the QRNG-seeded ML-KEM handshake and sees each step (Server keygen, Client encapsulate, key derivation, AES-GCM encrypt→decrypt) update **in place with no page reload**, matching the dice-player UX. | `web/app/demo/page.tsx:1-23` (dedicated route), `web/components/KemHandshakeDemo.tsx:64` onward (`"use client"` state machine, no reload, steps 1-4); manually verified: `GET /demo` → 200, `POST /api/kem/keypair`/`encapsulate` observed in dev server log on button click. |
| **AC-9** | **Developer request:** the five networking use-case mappings (AC-5) are also **surfaced on the demo page**, so the mapping is visible in the app, not only in the committed doc. | `web/components/sections/NetworkingUseCases.tsx:1-46`, composed in `web/app/demo/page.tsx:22`; verified page HTML contains the section heading and all five use-case titles. |

No test AC — see the banner. Verification is §6 (run the script, run the page, read the doc).

---

## 3. Scope

### In scope
- **Backend/CLI:** a new `api/scripts/kem_handshake.py` — two-role Server/Client handshake driving
  the existing KEM endpoints, AES-GCM message exchange, local decaps verification, QRNG-provenance
  logging.
- **Web proxy:** new Next 16 App Router **route handlers** `web/app/api/kem/keypair/route.ts` and
  `web/app/api/kem/encapsulate/route.ts` that inject a **server-only** API key and forward to
  FastAPI. New server-only env var `KEM_DEMO_API_KEY` + server-side FastAPI origin `API_ORIGIN`.
- **Web client:** new typed KEM helpers in `web/lib/api.ts`; a new `"use client"` component
  `web/components/KemHandshakeDemo.tsx`; a new dedicated route `web/app/demo/page.tsx` (mirroring
  `app/dice/page.tsx`); a nav link in `web/components/Header.tsx`.
- **Web content:** the five use-case mappings rendered on the demo page (AC-9) — reuse of a new
  section component `web/components/sections/NetworkingUseCases.tsx`.
- **Doc:** `qrng-eaas/shared/docs/networking-demo.md` (S8.2) + a short README pointer section.
- **Config/runbook:** mint a dedicated demo API key (`iot` tier) and record how to set
  `KEM_DEMO_API_KEY`/`API_ORIGIN` locally and on Vercel.

### Out of scope (deferred or already satisfied)
- **New FastAPI route** — the two KEM endpoints already exist; the demos drive them. No change to
  `api/main.py`, `qeaas/kem.py`, `qeaas/schemas.py`, `api/sql/*`, `api/requirements.txt`.
- **Server-side decapsulate route** — EPIC 4 locked "decaps happens on the `dk` holder." The CLI
  demo decaps locally; the web demo does **not** decaps in the browser (Decision 4).
- **A JS ML-KEM library in the web app** — the browser demo visualizes the real service's QRNG-seeded
  ML-KEM and performs the **AES-GCM** step natively; it does **not** re-run ML-KEM math client-side
  (would need a new npm crypto dep). Independent both-parties decaps agreement is proven by the CLI
  script (AC-4). Adding a JS ML-KEM lib for full in-browser verification is Q4 (deferred by default).
- **New Python/JS runtime deps** — CLI uses already-present `kyber-py`+pycryptodome; web uses
  native `fetch`/Web Crypto (no `cryptography`, no `axios`, no crypto npm package).
- **Automated tests** — per the no-tests directive.
- **Stretch `[COULD]`** items (X25519/WireGuard classic keypair, signed entropy certificate,
  `/metrics`) — the WireGuard *mapping sentence* is in scope (S8.2); an X25519 implementation is not.
- **EPIC 9 receipts** — the demos read the already-present `entropy_epoch`/`request_id` for logging
  (AC-3); they do not implement signed receipts (`receipt` stays `null`; EPIC 9 has no plan yet).
- **Vercel same-origin rewrites for `/health` & `/dice`** — EPIC 5/6 concern; unchanged. This plan
  only adds the `/api/kem/*` route handlers (same-origin by construction).

---

## 4. Key decisions

### Decision 1 — CLI demo: one script playing both roles, driving the live endpoints (extend `kem_roundtrip.py`, no `qeaas` import)
`api/scripts/kem_handshake.py` models a `Server` (holds `dk`) and a `Client` (holds encaps output),
driving the real endpoints for the two QRNG-seeded randomness ops — the honest, reproducible reading
of S8.1 (keygen + encaps randomness genuinely from the deployed QRNG→DRBG chain, exactly as EPIC 7
validated against the live deployment). Extends the proven pattern: stdlib `urllib`, `argparse`,
`API_KEY` env, `--base-url` (default `http://localhost:8000`, override to
`https://quantum-research-api.vercel.app`); imports only `kyber_py` + pycryptodome, **not** `qeaas`
(no local Postgres/Redis needed). AES-GCM via pycryptodome (`pool.py:37-46` pattern); AES key via
inline `HKDF(shared_secret,32,b"",SHA256)` (formula cited from `kem.py:70-76`), asserted equal to
the service-returned `demo_key`. Server decapsulates locally (`ML_KEM_768.decaps(dk,ct)`), asserts
`== shared_secret` (AC-4). Server encrypts one message → Client `decrypt_and_verify` (AC-2). Prints
per-role QRNG provenance (AC-3) and the loud "demo only" note.

### Decision 2 — web keyed calls go through a Next route-handler proxy with a SERVER-ONLY key (never `NEXT_PUBLIC_*`)
The browser must never see the API key. Add two Next 16 App Router route handlers,
`web/app/api/kem/keypair/route.ts` and `web/app/api/kem/encapsulate/route.ts`, each an async `POST`
handler that: reads `process.env.KEM_DEMO_API_KEY` (server-only) and `process.env.API_ORIGIN`
(server-side FastAPI base — dev `http://localhost:8000`, prod
`https://quantum-research-api.vercel.app`); forwards the JSON body to the corresponding FastAPI KEM
endpoint with header `X-API-Key: <KEM_DEMO_API_KEY>`; relays FastAPI's status + JSON back verbatim
(so the client sees the same `{"error":"<slug>"}` envelope, including `503 low_quantum_entropy` and
`429`). The client component fetches these **same-origin** `/api/kem/*` paths (no key, no CORS). The
exact route-handler export signature (`export async function POST(request: Request)` returning a
`Response`/`NextResponse`) **must be confirmed against `node_modules/next/dist/docs/` for Next 16**
before writing (AGENTS.md). If `KEM_DEMO_API_KEY` is unset, the handler returns a clear
`{"error":"demo_key_not_configured"}` 500 so the UI can show a friendly setup message rather than a
blank failure.

### Decision 3 — dedicated `iot`-tier demo API key; the browser demo requests `include_shared_secret` but NOT `include_secret_key`
Mint one dedicated key (`POST /admin/keys`, `owner:"networking-demo"`, tier `iot` — 10 MiB/day, far
beyond the ~2 keyed calls per run) via the pattern in `claude/prod_seed/mint_prod_key.sh`; store its
plaintext as `KEM_DEMO_API_KEY` (local `.env.local` and Vercel env). The **web** demo calls keypair
**without** `include_secret_key` (the browser never fetches `dk` — reinforcing "the secret key never
leaves the holder"; the browser doesn't decapsulate, so it doesn't need `dk`), and encapsulate
**with** `include_shared_secret: true` (the browser needs the shared secret + `demo_key` to run the
AES-GCM step; display the loud `_DEMO_SHARED_SECRET_NOTE`). The **CLI** demo, being the rigorous
artifact, does request `include_secret_key` so it can locally decapsulate and prove agreement (AC-4).

### Decision 4 — the browser demo visualizes the real QRNG-seeded ML-KEM and does the AES-GCM exchange natively; it does not re-run ML-KEM in JS
No JS ML-KEM library exists in the app and adding one is deferred (Q4). The web flow: (1) Server
keygen via proxy → show truncated `ek` + provenance; (2) Client encapsulate via proxy → show
`ciphertext` + `shared_secret`(demo) + `demo_key` + provenance; (3) **browser** imports `demo_key`
(base64→bytes) as an AES-GCM key via `crypto.subtle.importKey`, and — as a teaching check —
independently recomputes `HKDF-SHA256` over the shared secret via `crypto.subtle` and shows it
matches the service `demo_key` (**note the empty-salt interop detail** between pycryptodome
`HKDF(...,b"",...)` and Web Crypto HKDF must be verified at implementation time; if it mismatches,
fall back to using the service `demo_key` directly and drop the "matches" line — the demo is not
blocked on it); (4) **browser** AES-GCM `encrypt` then `decrypt` of a user-entered message via
`crypto.subtle`, showing ciphertext/nonce and the recovered plaintext (AC-2/AC-8). Honesty callouts
on the page: the AES **key** is QRNG-seeded (via ML-KEM shared secret) but the 12-byte GCM **nonce**
is a standard browser CSPRNG value; the both-parties decapsulation-agreement is proven rigorously by
the **CLI** demo (link to run it), because independent in-browser ML-KEM decaps would need a JS
ML-KEM dependency (Q4).

### Decision 5 — dedicated `/demo` route (mirror `app/dice/page.tsx`); mapping use cases as a section on that page
The interactive demo is multi-step like the dice player, so it gets its own route
`web/app/demo/page.tsx` (metadata export, intro, back-link, then `<KemHandshakeDemo/>`), and a
`{ href: "/demo", label: "Demo" }` entry added to `NAV_LINKS` in `Header.tsx`. The five use-case
mappings (AC-9) render below the interactive demo on the same page via
`components/sections/NetworkingUseCases.tsx` (server component, `.panel` cards like `ApiUsage.tsx`).

### Decision 6 — S8.2 doc at `shared/docs/networking-demo.md` + README pointer (single source, page summarizes it)
The substantive write-up is `qrng-eaas/shared/docs/networking-demo.md` (the build plan designates
`/shared` for docs; creates the `docs/` subdir), committed as the thesis-referenceable artifact. The
demo page's `NetworkingUseCases` section restates the five mappings concisely (AC-9) and links to the
full doc — the doc remains the canonical source (avoid divergence: keep the page copy short and
point to the doc for detail). A short "## Networking demonstration (EPIC 8)" README section gives the
CLI run command + the `/demo` page URL + doc link (EPIC 4/6/7 README pattern).

---

## 5. File plan (concrete paths)

All new Python: `from __future__ import annotations`, PEP 8, full type hints, module docstring with
`Usage:`. All new TS: strict types (no `any`), `"use client"` where interactive, fetch/typing in
`lib/api.ts` not JSX. No raw SQL anywhere (neither demo touches the DB directly). No business logic
in the route page — the interactive logic lives in the client component + `lib/api.ts`.

### Backend / CLI
| File | Change |
|------|--------|
| `qrng-eaas/api/scripts/kem_handshake.py` | **New.** Stdlib-`urllib` HTTP client; imports `from kyber_py.ml_kem import ML_KEM_768`, `from Crypto.Protocol.KDF import HKDF`, `from Crypto.Hash import SHA256`, `from Crypto.Cipher import AES`; **no `qeaas` import**. CLI (argparse, `description=__doc__`): `--base-url` (default `http://localhost:8000`, env `API_BASE`), `API_KEY` from env, optional `--message`. `Server` helper (holds `ek`/`dk`; `decapsulate(ct)`, `encrypt(msg)`), `Client` helper (holds `shared_secret`/`ciphertext`; `decrypt(nonce,ct,tag)`), `run_demo()`. Flow per Decision 1: POST keypair `{"include_secret_key":true}` → log Server keygen provenance, keep `ek`/`dk`; POST encapsulate `{"public_key":ek,"include_shared_secret":true}` → log Client encaps provenance, keep `ciphertext`/`shared_secret`; assert local `derive_key(ss)==b64decode(resp["demo_key"])`; Server local `decaps(dk,ct)` assert `==ss`; both derive key, Server AES-GCM-encrypts (`nonce=os.urandom(12)`, `mac_len=16`), Client `decrypt_and_verify`; print multi-line PASS. Errors mirror `kem_roundtrip.py` (print `resp["error"]`; `503 low_quantum_entropy` → abort with a clear message; missing `API_KEY` → usage exit). |

### Web — proxy (server-side)
| File | Change |
|------|--------|
| `qrng-eaas/web/app/api/kem/keypair/route.ts` | **New.** Next 16 route handler: `export async function POST(request: Request)`. Reads `KEM_DEMO_API_KEY` + `API_ORIGIN` (server-only). If key unset → 500 `{"error":"demo_key_not_configured"}`. Else forwards the parsed JSON body to `${API_ORIGIN}/v1/kem/keypair` with `X-API-Key`; relays upstream status + JSON verbatim. Confirm exact signature against Next 16 docs first. |
| `qrng-eaas/web/app/api/kem/encapsulate/route.ts` | **New.** Same shape, forwarding to `${API_ORIGIN}/v1/kem/encapsulate`. |
| `qrng-eaas/web/.env.local` | **Edit.** Add `KEM_DEMO_API_KEY=<minted iot key>` and `API_ORIGIN=http://localhost:8000` (server-only — **not** `NEXT_PUBLIC_*`). Document that both must also be set as Vercel env vars for prod (`API_ORIGIN=https://quantum-research-api.vercel.app`). |

### Web — client
| File | Change |
|------|--------|
| `qrng-eaas/web/lib/api.ts` | **Edit.** Add typed interfaces (`KemKeypair`, `KemEncapsulation` with `ciphertext`,`shared_secret`,`demo_key`, provenance fields) and helpers `kemKeypair(): Promise<KemKeypair>` (POST same-origin `/api/kem/keypair`, `{}` body) and `kemEncapsulate(publicKey: string): Promise<KemEncapsulation>` (POST `/api/kem/encapsulate`, `{public_key, include_shared_secret:true}`). Reuse the `requestJson`/`ApiError` slug pattern. Add small base64↔`Uint8Array` helpers if not present. |
| `qrng-eaas/web/components/KemHandshakeDemo.tsx` | **New. `"use client"`.** The interactive component (mirror `DicePlayer.tsx` state/UX). Steps rendered as `.panel` cards that fill in as the handshake progresses (framer-motion reveal, no reload): (1) "Run handshake" `.pill` button (`disabled` while running); (2) Server keygen — calls `kemKeypair()`, shows truncated `ek` + `request_id`/`entropy_epoch` + "QRNG-seeded" badge; (3) Client encapsulate — `kemEncapsulate(ek)`, shows truncated `ciphertext`/`shared_secret`/`demo_key` + provenance + the demo-only note; (4) derive AES key — `crypto.subtle.importKey("raw", b64(demo_key), {name:"AES-GCM"}, false, ["encrypt","decrypt"])`, plus the optional Web Crypto HKDF "matches service demo_key" teaching check (Decision 4); (5) message exchange — a small text input (default demo string), on submit `crypto.subtle.encrypt({name:"AES-GCM", iv:getRandomValues(12)}, key, msgBytes)` then `decrypt` → show ciphertext(hex, `overflow-x-auto`) and recovered plaintext == input. Backend slugs → friendly copy via an `ERROR_MESSAGES` map (`low_quantum_entropy` → "Quantum entropy is degraded — the demo is temporarily unavailable"; `demo_key_not_configured` → setup hint). Mobile-first, tap targets ≥44px. |
| `qrng-eaas/web/app/demo/page.tsx` | **New.** Mirror `app/dice/page.tsx`: `metadata` export, hero/intro `<p>` explaining the QRNG→ML-KEM→AES-GCM handshake, back-link, `<KemHandshakeDemo/>`, then `<NetworkingUseCases/>` (AC-9). |
| `qrng-eaas/web/components/sections/NetworkingUseCases.tsx` | **New** (server component). `.panel` cards (like `ApiUsage.tsx`) listing the five use cases (AC-9), each with its one honest sentence; a link to `shared/docs/networking-demo.md` (or the repo path) for the full write-up. |
| `qrng-eaas/web/components/Header.tsx` | **Edit.** Add `{ href: "/demo", label: "Demo" }` to `NAV_LINKS`. |

### Doc
| File | Change |
|------|--------|
| `qrng-eaas/shared/docs/networking-demo.md` | **New (committed).** (a) **What the demo shows** — the S8.1/web flow (QRNG→DRBG → ML-KEM-768 keygen/encaps → shared secret → HKDF → AES-GCM message), the CLI run command, and the `/demo` page URL. (b) **Honest framing** — "entropy, not quantum-resistance" (matching `kem.py:3-7`/README EPIC 4): QRNG supplies entropy seeding a standards DRBG which seeds ML-KEM (FIPS 203); the quantum part is the entropy source, the resistance is ML-KEM; `kyber-py` educational/not constant-time; the GCM nonce is standard CSPRNG. (c) **Mapping to networking** — the five use cases (AC-5) each with one honest sentence (AC-6): ephemeral TLS/VPN keys (forward secrecy), WireGuard ephemeral keys, SDN control-plane / moving-target defence, ECMP hash salt, IoT seed distribution (central quantum entropy → weak-RNG edge devices via API-key tiers). |
| `qrng-eaas/shared/docs/` | **New directory** (implicit). |
| `qrng-eaas/README.md` | **Edit.** Append "## Networking demonstration (EPIC 8)": one-line summary, the CLI `API_KEY=… python -m scripts.kem_handshake --base-url …` command (local + deployed), the `/demo` page URL, how to mint + set `KEM_DEMO_API_KEY`/`API_ORIGIN`, and a link to `shared/docs/networking-demo.md`. |

**No changes** to `api/main.py`, `api/qeaas/*`, `api/sql/*`, `api/requirements.txt`, `api/tests/*`,
`web/next.config.ts`, `web/package.json`, or `.gitignore`.

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — running service + dedicated demo key
Bring up a service (local `bash api/scripts/dev_db_up.sh` + seed pool + `uvicorn`, per README; or
the deployed URL). Confirm `GET /health` → `"status":"ok"` and entropy **not** degraded. Mint the
dedicated key (Decision 3):
```bash
curl -s -X POST <base>/admin/keys -H "X-Admin-Token: <ADMIN_TOKEN>" \
  -H 'content-type: application/json' -d '{"owner":"networking-demo","tier":"iot"}'
# copy the plaintext api_key from the response (shown once)
```

### Phase 1 — CLI demo (S8.1: AC-1..AC-4)
Write `api/scripts/kem_handshake.py` (Decision 1 / §5). Run:
```bash
cd qrng-eaas/api
API_KEY=<key> python -m scripts.kem_handshake --base-url http://localhost:8000
# or: --base-url https://quantum-research-api.vercel.app
```
Confirm output order: Server keygen provenance → Client encaps provenance → "local demo_key matches
service demo_key" → "server-decaps shared secret == client shared secret (32B)" → "Client decrypted
Server message: <plaintext>" → **PASS**. Any assertion failure or `503 low_quantum_entropy` → stop
and investigate (§8); do not weaken an assertion to force a pass.

### Phase 2 — web proxy route handlers (Decision 2)
Read `node_modules/next/dist/docs/` for the Next 16 route-handler API first. Write
`app/api/kem/keypair/route.ts` and `app/api/kem/encapsulate/route.ts`. Set `KEM_DEMO_API_KEY` +
`API_ORIGIN` in `web/.env.local`. Smoke-test the proxy in isolation:
```bash
cd qrng-eaas/web && npm run dev
curl -s -X POST http://localhost:3000/api/kem/keypair -H 'content-type: application/json' -d '{}'
# expect the FastAPI KemKeypairResponse relayed verbatim (public_key + issue meta), NO key echoed
```

### Phase 3 — web client (AC-8, AC-3, AC-2)
Add the `lib/api.ts` helpers, write `KemHandshakeDemo.tsx`, `app/demo/page.tsx`,
`NetworkingUseCases.tsx`, and the `Header.tsx` nav entry. `npm run dev`, open `/demo`:
- Click **Run handshake**: confirm each step card fills in with no page reload; the two provenance
  epochs (keygen, encaps) are shown and labelled QRNG-seeded (AC-3).
- The AES key derives; the "matches service demo_key" check shows ✓ (or is dropped per Decision 4).
- Enter a message, submit: confirm ciphertext appears and the decrypted plaintext equals the input
  (AC-2/AC-8).
- Test at desktop **and** ~380px width; confirm the run button disables while in flight; confirm a
  degraded-pool `503` shows the friendly message, not a blank/crash.

### Phase 4 — S8.2 doc + page mappings (AC-5..AC-7, AC-9)
Write `shared/docs/networking-demo.md` (Decision 6 / §5), reusing the honest-framing wording from
`kem.py:3-7`/README EPIC 4. Fill `NetworkingUseCases.tsx` with the five mappings + link to the doc.
Confirm on `/demo` all five appear below the interactive demo (AC-9).

### Phase 5 — README pointer + final read (the "Done when" check)
Append the README section (§5). Then:
- Re-run Phase 1 once from a clean shell (reproducibility, AC-4).
- Re-open `/demo` from a fresh load and run the full handshake (AC-8).
- Read `networking-demo.md` end to end: five use cases (AC-5), one honest sentence each (AC-6),
  honest framing present, demo tied to the use cases (AC-7).

---

## 7. Design decisions carried from the epic (do not re-litigate)
- **ML-KEM-768** (FIPS 203); keygen seed `random_bytes(64)`, encaps randomness `random_bytes(32)`
  via `_encaps_internal` → **both** QRNG→DRBG (`feature-epic4-mlkem-consumer.md`; `kem.py:47-67`).
- `dk`/`shared_secret` are **demo-only** disclosures behind explicit flags with a loud note; in
  production they never leave the holder (`main.py:211-218`). The web demo deliberately never
  fetches `dk` (Decision 3).
- No server-side decapsulate route (EPIC 4 locked); the `dk` holder decapsulates (CLI does it).
- **Raw QRNG bits are never served** — both demos consume only DRBG-derived output via the KEM
  endpoints (build plan Locked decision #2).
- Honest framing everywhere: QRNG = entropy source, ML-KEM = the quantum resistance; `kyber-py`
  educational / not constant-time (`kem.py:3-7`).
- **No new deps** — Python: already-present `kyber-py`+pycryptodome; web: native `fetch`+Web Crypto
  (no `cryptography`, no `axios`, no crypto npm).
- **EPIC 5 frontend rules** — no reload; `fetch` not axios; fetch/typing in `lib/api.ts`; strict TS
  no `any`; `"use client"`; mobile-first, tap ≥44px, ~380px; tokens only (`.glow/.pill/.panel`);
  typed `ApiError` from backend slug surfaced inline; **read Next 16 docs before coding**.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| CLI/web aborts with `503 low_quantum_entropy` | Target pool is `degraded` (gate is real) | Check `/health`; run against a healthy service / refill the pool (EPIC 1/6). Never disable the gate. |
| Web `/api/kem/*` returns `demo_key_not_configured` | `KEM_DEMO_API_KEY` unset in the Next server env | Set it in `web/.env.local` (and Vercel env); restart `npm run dev`. |
| Web proxy returns `401 missing_api_key`/`invalid_api_key` | Key not forwarded, or revoked/unknown | Confirm the route handler sends `X-API-Key`; confirm the minted key isn't revoked/over-quota. |
| API key visible in browser devtools/network | A keyed call was made browser-direct instead of via the proxy | All KEM calls must go to same-origin `/api/kem/*`; the key lives only in the server-only env var (Decision 2). |
| `422 bad_request` on encapsulate | `ek` not round-tripped as base64 / wrong length (`EK_BYTES=1184`) | Send `public_key` exactly as returned by keypair; don't re-encode decoded bytes. |
| Browser-derived HKDF key != service `demo_key` | Empty-salt HKDF interop difference (pycryptodome vs Web Crypto) | Verify empty-salt handling; if it genuinely differs, use the service `demo_key` directly and drop the "matches" line (Decision 4) — the AES exchange still works. |
| `crypto.subtle` is `undefined` | Page served over insecure origin (Web Crypto needs a secure context) | Use `localhost` (a secure context) in dev and HTTPS in prod; don't test over a plain-HTTP LAN IP. |
| CLI `decaps` != client shared secret | Wrong keypair, or bytes not base64-decoded before `decaps` | Use the same `ek`/`dk` pair; base64-decode `ciphertext`/`dk` to raw bytes first. |
| `AES.MODE_GCM`/HKDF import error (CLI) | Wrong venv / `cryptography` used by mistake | Activate `api/venv`; use `from Crypto.…` (pycryptodome), never `cryptography`. |
| Next route handler build error | Wrong Next 16 handler signature | Re-check `node_modules/next/dist/docs/` for the exact `POST` export shape (AGENTS.md). |

---

## 9. Post-Implementation

Built exactly per plan, no deviations. Notable results from manual verification:

- **HKDF empty-salt interop (Decision 4) resolved: matches.** Verified with Node's
  `crypto.webcrypto.subtle` (spec-compliant Web Crypto, same engine browsers use)
  against a live service `shared_secret`/`demo_key` pair: `HKDF-SHA256` with
  `salt=new Uint8Array(0), info=new Uint8Array(0)` produced bytes identical to the
  service's `demo_key`. The component's "✓ matches" line (Decision 4) will render, not
  the fallback branch — pycryptodome's `HKDF(ss,32,b"",SHA256)` and Web Crypto's
  empty-salt/empty-info HKDF agree.
- **CLI demo (`kem_handshake.py`)** ran twice against a local disposable Postgres+Redis
  stack, each producing a distinct `request_id`/`entropy_epoch` and a clean `PASS`
  (reproducibility, AC-4).
- **Proxy routes** smoke-tested directly with `curl`: `POST /api/kem/keypair` and
  `POST /api/kem/encapsulate` relay FastAPI's response verbatim, `secret_key` stays
  `null` (the browser call never sends `include_secret_key`), and the API key never
  appears in the response.
- **Browser verification caveat:** no headless/interactive browser was available in
  this environment to literally click through `/demo`. Verified instead: (1) the page
  returns `200` and contains the expected UI text server-side; (2) the dev server log
  shows the proxy POSTs firing (confirming the client component's fetch calls work);
  (3) the exact crypto operations the component runs client-side (HKDF derivation,
  AES-GCM encrypt→decrypt) were independently exercised via Node's Web Crypto
  implementation against real service output, with correct results. The developer
  should still do one real-browser pass (desktop + ~380px) before treating AC-8's UX
  polish (button disabled state, mobile layout) as fully confirmed.
- **Follow-ups (deferred, matches Q4/out-of-scope):** no JS ML-KEM library was added;
  independent decaps agreement is proven only by the CLI. `KEM_DEMO_API_KEY` was
  minted locally (`owner=networking-demo`, tier `iot`) and set in `web/.env.local`
  only — it still needs to be minted against the **prod** API and set in the Vercel
  env for `qeaas-web` before the deployed `/demo` page will work end-to-end.

---

## 10. Open questions — RESOLVED (developer: "yes to all defaults", 2026-07-13)

**Q1 — Web layout? → RESOLVED: dedicated `/demo` route.** `app/demo/page.tsx` + a `NAV_LINKS`
entry, mirroring `app/dice/page.tsx`.

**Q2 — S8.2 doc location? → RESOLVED: standalone `shared/docs/networking-demo.md` (canonical) +
README pointer + a concise five-mapping section on the `/demo` page (AC-9) that links to the doc.**

**Q3 — Keep both CLI script and web demo? → RESOLVED: yes, both.** The CLI script is the rigorous
reproducible artifact that independently verifies both parties agree on the shared secret (AC-4);
the web page is the visible interactive demo.

**Q4 — Add a JS ML-KEM library for in-browser decaps? → RESOLVED: no (deferred).** The web app
stays dependency-light; the CLI proves independent agreement, and the browser still runs a genuine
live AES-GCM exchange with the QRNG-seeded key. Can be revisited as its own ticket later.

**Q5 — Message direction? → RESOLVED: Server → Client** (Server encrypts, Client decrypts).

**Q6 — `KEM_DEMO_API_KEY` provisioning? → RESOLVED: mint a new dedicated `owner:"networking-demo"`
`iot`-tier key**, set as `KEM_DEMO_API_KEY` in `web/.env.local` + Vercel env.
