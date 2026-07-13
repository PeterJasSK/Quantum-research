# Feature Plan — EPIC 7: Validation (prove the seeds are good)

**Status:** Complete
**Owning plan:** `qrng-eaas/claude/QRNG_EaaS_BUILD_PLAN.md` → EPIC 7 `[SHOULD]`
**Interpretation of "epic7":** EPIC 7. EPICS 1–6 are Complete (entropy core, public API,
anti-abuse, ML-KEM, web app, and — per `feature-epic6-deployment.md` §10 — the file-level prep
for deployment; the live Vercel/Neon/Upstash resources now exist and are exercised in
`qrng-eaas/claude/prod_seed/` via `mint_prod_key.sh` / `smoke_test.sh` against
`https://quantum-research-api.vercel.app`).

> **No automated tests in this plan.** The build plan's EPIC 7 has two stories: **S7.1** (a
> statistical seed-quality report) and **S7.2** ("Unit: DRBG KATs, rate-limit, quota, gate flip.
> Integration: end-to-end key round-trip"). Per current project directive, this plan does **not**
> author S7.2 — no new pytest files, no "Testing approach" section, no test-to-AC mapping. S7.2's
> unit coverage already exists as a **side effect** of EPICS 1–4 (`api/tests/test_drbg_kat.py`,
> `test_reseed.py`, `test_gate.py`, `test_keyed_drbg.py`, `test_pool_crypto.py`, `test_ingest.py` —
> confirmed present, see §3 Out of scope) — nothing new is planned or required here. This plan
> covers **S7.1 only**: pull real service output, run the existing statistical battery against it,
> produce the PDF. Verification is manual (run the script, inspect the PDF), not a test suite.

---

## 1. Context & goal

Produce quantitative evidence that the bytes the deployed service actually serves are
statistically indistinguishable from the OS CSPRNG, and that they are demonstrably
**quantum-seeded** (not a hardcoded/predictable stream) — the build plan's exact ask:

> Pull ~1–2 MB from `/v1/seed`, save as a `bits:` file, run `qrng_compare.py` against
> `/dev/urandom` … Include the PDF in the thesis appendix.

### What already exists (integration points)
- `ErrorDetectionVSRawBits/qrng_compare.py` — the statistical battery (bias, NIST SP 800-22,
  next-bit ML predictability, Markov dependency), already built and used elsewhere in this repo
  for raw QRNG batches. Takes exactly **two** `bits:`-prefixed `.txt` files (`load_bits`,
  `qrng_compare.py:326-337`: strips an optional `bits:` prefix, validates every remaining char is
  `0`/`1`) and writes one PDF (`qrng_compare.py FILE1 FILE2 -o report.pdf`). **Unmodified by this
  plan** — it is a generic two-stream comparator; feeding it new files needs no code change.
- `qrng-eaas/api/main.py:132-145` (`GET /v1/seed`) — keyed, capped `32 ≤ bytes ≤ 4096` per call
  (`Query(ge=32, le=4096)`), so pulling 1–2 MB means **hundreds of paginated calls**, not one
  request. Each call is metered against the calling key's daily quota
  (`api/qeaas/ratelimit.py` `TIER_QUOTAS`: `default` = 256 KiB/day — **too small** for a 1–2 MB
  pull in one day; `iot` = 10 MiB/day, `trusted` = 500 MiB/day) and per-key rate limit
  (`TIER_RATE_LIMITS`: `default` 120/min, well above what a sequential pull script needs).
- `qrng-eaas/claude/prod_seed/mint_prod_key.sh` — mints a **`default`**-tier key for smoke
  testing only (256 KiB/day); **not reused here** because it can't cover a 1–2 MB pull without
  multi-day throttling (§4 Decision 1 mints a dedicated key instead).
- `qrng-eaas/claude/prod_seed/smoke_test.sh` — shows the exact `curl` shape already proven to
  work against the live deployment (`https://quantum-research-api.vercel.app`), reused as the
  template for the new pull script's HTTP calls.
- `qrng-eaas/api/scripts/` — existing CLI convention (`ingest_bits.py`, `mint_key.py`,
  `revoke_key.py`, `kem_roundtrip.py`): a plain `argparse` script under `api/scripts/`, run with
  `venv/bin/python`, importing `qeaas.*` only when it needs local DB/Redis access directly. This
  ticket's script instead talks to the **deployed** API over HTTP (like `smoke_test.sh`), so it
  does not import `qeaas` at all — no local Postgres/Redis dependency.
- `api/requirements.txt` is **pure-Python, Vercel-deployable** deps only (confirmed EPIC 1 §5 /
  EPIC 6 troubleshooting). `qrng_compare.py`'s own dependencies — `nistrng`, `scikit-learn`,
  `matplotlib`, `numpy` — are **not** in `api/requirements.txt` and must **never** be added there;
  they only ever run locally, never inside the deployed FastAPI function (§4 Decision 2).
- `qrng-eaas/.gitignore` already excludes `claude/prod_seed/` as "regenerable … not source" —
  this plan follows the same pattern for the large raw sample files it generates (§4 Decision 3).

---

## 2. Acceptance criteria (from EPIC 7 "Done when" + S7.1, verbatim intent)

| AC | Source | Covered by |
|----|--------|------------|
| AC-1 | S7.1: "Pull ~1–2 MB from `/v1/seed`" — a script pages through `GET /v1/seed` against the live deployment and assembles a `bits:`-prefixed sample file of that size. | `qrng-eaas/claude/validation/pull_seed_sample.py:63-86` — paged 384×4096-byte calls against `https://quantum-research-api.vercel.app/v1/seed`, produced `samples/service_sample.txt` (1,572,864 bytes / 12,582,912 bits). Confirmed run: "Wrote 1572864 bytes (12582912 bits) ... in 384 calls." ✅ |
| AC-2 | S7.1: "save as a `bits:` file" — output format matches exactly what `qrng_compare.py`'s `load_bits` expects (optional `bits:` prefix, then only `0`/`1` characters). | `pull_seed_sample.py:23-26` (`_bytes_to_bits_file`), verified against `ErrorDetectionVSRawBits/qrng_compare.py:326-337` (`load_bits`): `samples/service_sample.txt` starts with `bits:`, has exactly 12,582,912 trailing chars, all in `{0,1}`. ✅ |
| AC-3 | S7.1: "run `qrng_compare.py` against `/dev/urandom`" — a same-size baseline sample is drawn from the OS CSPRNG (`os.urandom`) and saved in the identical `bits:` format. | `qrng-eaas/claude/validation/pull_urandom_sample.py:20-27` — `os.urandom(1572864)` written to `samples/urandom_sample.txt` via the same `_bytes_to_bits_file` helper. ✅ |
| AC-4 | S7.1: "battery" — `qrng_compare.py <service_sample> <urandom_sample> -o <report>.pdf` runs to completion and produces one PDF covering bias / NIST SP 800-22 / next-bit / Markov for both streams. | `qrng-eaas/claude/validation/seed_quality_report.pdf` (12 pages, generated via unmodified `ErrorDetectionVSRawBits/qrng_compare.py`), console output confirmed all four sections ran for both raw+whitened streams of both files. ✅ |
| AC-5 | Done when: "a report shows the served seeds pass the battery" — the PDF is generated from **live, deployed** service output (not a local dev stub), so it is evidence about the actual production `/v1/seed` endpoint. | Pulled from `https://quantum-research-api.vercel.app` (confirmed `/health` → `"status":"ok"` immediately before the pull) using a freshly minted `iot`-tier key (`owner: "seed-quality-report"`), not a local dev server. `seed_quality_report.pdf`: service_sample raw — bias 0.0001, NIST pass rate 1.00 (68/68), next-bit PASS (AUC 0.5007), Markov PASS (0.0006 max excess) — statistically indistinguishable from urandom_sample raw (bias 0.0002, NIST 1.00, next-bit PASS 0.5000, Markov PASS 0.0000). ✅ |
| AC-6 | Build plan: "Include the PDF in the thesis appendix" — the PDF lands at a stable, committed repo path so it can be referenced from the write-up. | `qrng-eaas/claude/validation/seed_quality_report.pdf` (untracked, ready to `git add`; committed path matches §5 file plan exactly). ✅ |

S7.2 ("Unit … Integration … tests") is **not** an AC of this plan — see the banner above and §3.

---

## 3. Scope

### In scope
- A script that pages `GET /v1/seed` against the deployed API with a dedicated API key,
  assembles ~1–2 MB of bytes, converts to a `bits:`-prefixed text file.
- A companion path that draws the same number of bytes from `os.urandom` (Python's interface to
  the OS CSPRNG — `/dev/urandom` on Linux) into the same file format, as the comparison baseline.
- Minting one new, dedicated API key with a quota large enough to cover the pull in one run
  (§4 Decision 1) — a one-off `curl`/script step, not new application code.
- Running the existing, unmodified `ErrorDetectionVSRawBits/qrng_compare.py` against the two
  files to produce the PDF.
- A short runbook (in this plan's §6, condensed into `qrng-eaas/README.md`) so the report is
  reproducible later (e.g. after a future reseed or pool refill) without re-deriving the steps.
- A local-only, non-deployed requirements file for the report tooling (§4 Decision 2).

### Out of scope (deferred or already satisfied elsewhere)
- **S7.2 automated tests** — out of scope per the no-new-tests project directive (banner above).
  The unit coverage S7.2 describes already exists from earlier epics:
  `api/tests/test_drbg_kat.py` (DRBG KATs), `test_reseed.py` (reseed), `test_gate.py` (gate flip),
  `test_keyed_drbg.py`, `test_pool_crypto.py`, `test_ingest.py` — confirmed present on disk. An
  end-to-end "key round-trip" integration test is **not** present and is **not** added here; if
  it's wanted later it needs its own ticket (the no-tests directive would need to be lifted for
  that ticket specifically).
- Any change to `qrng_compare.py` itself, to `/v1/seed`/`/v1/random/bytes`, to rate limiting, or
  to the entropy pool/gate — this ticket is read-only against the deployed service.
- Re-running/refreshing `qrng-eaas/claude/prod_seed/`'s existing production seeding or smoke
  test — those already succeeded per EPIC 6; this ticket only adds a **new**, separate API key
  for report pulls so it never competes with or exhausts the smoke-test key's quota.
- Dieharder — the build plan's own comment in `qrng_compare.py` already removed it ("~10M bits is
  far too little for it to be meaningful"); a 1–2 MB pull is smaller still, so it stays out.
- Publishing/hosting the PDF anywhere outside the repo (e.g. no upload to an external site).

---

## 4. Key decisions

### Decision 1 — mint a dedicated, higher-quota API key for this pull; don't reuse the smoke-test key
`mint_prod_key.sh` mints a `default`-tier key (`TIER_QUOTAS["default"] = 262_144` bytes/day —
256 KiB), which cannot serve a 1–2 MB pull in a single day without hitting `429 quota_exceeded`
partway through and forcing a multi-day script (worse reproducibility, and it would eat into the
same key's headroom that `smoke_test.sh` relies on). Mint a **new** key at **`iot`** tier
(`10_485_760` bytes/day — 10 MiB, comfortably covers a 2 MB pull with room for a re-run the same
day) via the existing `POST /admin/keys` route, following the exact pattern already proven in
`mint_prod_key.sh` (§6 Phase 1). Labeled `owner: "seed-quality-report"` so its purpose and quota
are self-documenting in the `api_keys` table. Not `trusted` (500 MiB) — no need to over-provision
a one-off validation pull.

### Decision 2 — `qrng_compare.py`'s dependencies are local-only, never added to `api/requirements.txt`
`nistrng`, `scikit-learn`, `matplotlib`, `numpy` are heavyweight / partially native-wheel
dependencies that have no business inside the deployed serverless function (confirmed pure-Python
constraint from EPIC 0/1/6). They are pinned in a **new**, separate file
(`qrng-eaas/claude/validation/requirements-report.txt`) installed into a throwaway local venv (or
the repo-root `ErrorDetectionVSRawBits` environment, if the developer already has one — see §6
Phase 0) — never into `api/venv` or `api/requirements.txt`.

### Decision 3 — sample files are regenerable scratch data (gitignored); the PDF is the committed deliverable
The two ~1–2 MB `bits:` sample files are large, regenerable, and contain no information beyond
"some DRBG bytes from one date" — same category as `claude/prod_seed/`'s existing gitignored
scratch files. They live under a new `qrng-eaas/claude/validation/samples/` directory, gitignored
(§7). The **PDF report** is the actual thesis-appendix artifact the build plan asks to keep, so it
is committed at `qrng-eaas/claude/validation/seed_quality_report.pdf` (small binary, meaningful on
its own, not regenerable byte-for-byte since a re-pull draws fresh DRBG output — so the committed
PDF is a point-in-time record, not something to silently overwrite on every re-run without
regenerating it deliberately).

### Decision 4 — sample size and where the "1–2 MB" comes from
`GET /v1/seed?bytes=<32..4096>&format=hex` — use the max per-call size (`4096` bytes) to minimize
round-trips: **384 calls** → 1,572,864 bytes (~1.5 MB), inside the build plan's "1–2 MB" target and
inside the new `iot`-tier key's 10 MiB/day quota with headroom for a retry. Use `format=hex` (not
`base64`) so decoding to raw bytes in the pull script is a single `bytes.fromhex(...)` call, no
padding edge cases.

---

## 5. File plan (concrete paths)

All new Python: `from __future__ import annotations`, PEP 8, full type hints, module docstring.

| File | Change |
|------|--------|
| `qrng-eaas/claude/validation/pull_seed_sample.py` | **New.** Standalone script (no `qeaas` import — talks to the deployed API over HTTP only, mirrors `smoke_test.sh`'s call shape). CLI: `--api-base URL --api-key KEY --total-bytes N --chunk-size 4096 --out PATH`. Loop: `GET {api_base}/v1/seed?bytes={chunk_size}&format=hex` with header `X-API-Key`, `bytes.fromhex(response["data"])`, accumulate until `total_bytes` reached; on `503` (`low_quantum_entropy`) abort immediately with a clear message (the gate is real — don't silently keep retrying against a degraded pool); on `429` (`quota_exceeded`/rate limit) back off and retry once, then abort with the exact response body. Converts the accumulated bytes to a bit string (`format(byte, "08b")` per byte, MSB-first, joined) prefixed with `bits:` and writes to `--out`. |
| `qrng-eaas/claude/validation/pull_urandom_sample.py` | **New.** Much simpler companion: `--total-bytes N --out PATH` → `os.urandom(total_bytes)` → same `bits:`-prefixed bit-string conversion (shared logic factored into a tiny `_bytes_to_bits_file(data: bytes, out: Path) -> None` helper imported by both scripts to avoid duplicating the packing logic). |
| `qrng-eaas/claude/validation/requirements-report.txt` | **New.** Pins `nistrng`, `scikit-learn`, `matplotlib`, `numpy` at whatever versions `ErrorDetectionVSRawBits/qrng_compare.py`'s own environment already uses (check its actual installed versions at implementation time; pin exactly, don't guess). Explicit header comment: "local-only — never install into `api/venv`, never add to `api/requirements.txt` (Vercel serverless constraint)." |
| `qrng-eaas/claude/validation/samples/` | **New directory**, gitignored (§7). Holds `service_sample.txt` and `urandom_sample.txt` after running the two pull scripts. |
| `qrng-eaas/claude/validation/seed_quality_report.pdf` | **New, committed.** Output of `qrng_compare.py samples/service_sample.txt samples/urandom_sample.txt -o seed_quality_report.pdf` (§6 Phase 3). |
| `qrng-eaas/.gitignore` | **Edit.** Add `claude/validation/samples/` (mirrors the existing `claude/prod_seed/` entry, same rationale comment). |
| `qrng-eaas/README.md` | **Edit.** Add a "## Seed-quality report (EPIC 7)" section: how to mint the report key, run the two pull scripts, run `qrng_compare.py`, and where the committed PDF lives — condensed from §6 below. |

No changes to `api/main.py`, `api/qeaas/*`, `api/sql/*`, `api/requirements.txt`, or
`ErrorDetectionVSRawBits/qrng_compare.py` — this ticket only adds new, self-contained scripts and
one gitignore line.

---

## 6. Step-by-step (manual — no automated tests)

### Phase 0 — local tooling for the report only
```bash
cd qrng-eaas/claude/validation
python3 -m venv .report-venv
source .report-venv/bin/activate
pip install -r requirements-report.txt
```
This venv is throwaway/local, separate from `api/venv` (Decision 2) — do not reuse `api/venv`.

### Phase 1 — mint the dedicated report API key (Decision 1)
```bash
curl -s -X POST https://quantum-research-api.vercel.app/admin/keys \
  -H "X-Admin-Token: <the real ADMIN_TOKEN, from the same source as mint_prod_key.sh>" \
  -H 'content-type: application/json' \
  -d '{"owner":"seed-quality-report","tier":"iot"}'
# copy the plaintext key from the response -- shown once
```
Confirm `/health` on the live deployment currently reports `"healthy"` before pulling — a
`degraded` pool means Phase 2 will 503 immediately and there's nothing to fix on this side.

### Phase 2 — pull the two samples
```bash
mkdir -p samples
python3 pull_seed_sample.py \
  --api-base https://quantum-research-api.vercel.app \
  --api-key <key from Phase 1> \
  --total-bytes 1572864 \
  --out samples/service_sample.txt

python3 pull_urandom_sample.py \
  --total-bytes 1572864 \
  --out samples/urandom_sample.txt
```
Expect both files to start with `bits:` followed by exactly `1572864 * 8 = 12,582,912` `0`/`1`
characters. Quick sanity check:
```bash
python3 -c "s=open('samples/service_sample.txt').read(); print(s[:20], len(s)-5)"
```

### Phase 3 — run the battery and produce the PDF
```bash
source .report-venv/bin/activate
python3 ../../../ErrorDetectionVSRawBits/qrng_compare.py \
  samples/service_sample.txt samples/urandom_sample.txt \
  -o seed_quality_report.pdf
```
Watch the console output for each stream's reported bias and battery pass/fail before opening the
PDF — a NIST-battery failure or a bias far from `0.5` on the **service** stream would mean
something upstream (pool/DRBG) is broken and is worth chasing before trusting the PDF.

### Phase 4 — read the PDF (this is the actual "Done when" check)
Open `seed_quality_report.pdf` and confirm, for the **service** stream (raw and whitened):
- Bias close to 0.5 across the 20 splits.
- NIST SP 800-22 battery passes across the 5 partitions.
- Next-bit ML predictability near chance (no window predicts meaningfully above 50%).
- Markov dependency shows no meaningful order-N structure.
…and that these are **statistically indistinguishable** from the `/dev/urandom` stream's own
results (the comparison is the point — a service stream that quietly looks *better or worse* than
the OS CSPRNG baseline is equally worth investigating).

If all of the above hold, AC-1 through AC-6 are satisfied and the PDF is ready to reference in the
thesis appendix as-is.

---

## 7. Design decisions carried from the epic (do not re-litigate)
- Raw QRNG bits are never served — this ticket only ever touches `/v1/seed`'s DRBG-derived output,
  never the entropy pool directly (build plan Locked decision #2, unchanged).
- Pull volume here (1.5 MB) is trivial against the `iot` tier's 10 MiB/day quota and, per EPIC 1's
  drain-budget analysis, costs **zero extra raw QRNG bits** — served bytes are DRBG output, pool
  draw is decoupled from request volume (EPIC 3 S3.3, EPIC 1 §7).
- `api/requirements.txt` pure-Python/Vercel-deployable constraint is never relaxed for this ticket
  (Decision 2).

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pull script aborts immediately with a `503 low_quantum_entropy` | Live pool is `degraded` | Check `/health`; if genuinely low, this is an EPIC 1/6 pool-refill matter, not something to work around here — wait for a refill, don't shrink the sample size to dodge the gate. |
| Pull script aborts with `429 quota_exceeded` partway through | `--total-bytes` exceeds the `iot` key's remaining daily 10 MiB, or the key was reused across multiple report runs same day | Wait for the daily quota window to reset (UTC day boundary, per `ratelimit.py`'s `quota:key:{hash}:{yyyymmdd}` key), or mint a second dedicated key for a same-day re-run. |
| `qrng_compare.py` exits early citing a missing tool | `requirements-report.txt` wasn't installed into the active venv, or the wrong venv is active | Re-check `source .report-venv/bin/activate` was run in the same shell before invoking the script (`require_tools()` in `qrng_compare.py` fails loudly and names the missing package). |
| `load_bits` raises "contains non 0/1 characters" | A pull script bug wrote something other than `0`/`1` after the `bits:` prefix (e.g. a stray newline mid-string, or hex leaked into the file instead of the converted bit string) | Inspect the file's first/last 20 characters and its total length against `total_bytes * 8`; fix the packing helper, don't hand-edit the generated file. |

---

## 9. Post-Implementation

Built exactly as planned, with one correction surfaced during foreground exploration: the
plan's Decision 2 file-plan entry for `requirements-report.txt` listed `nistrng` as a dependency,
but `qrng_compare.py`'s NIST SP 800-22 battery is actually implemented in a local pure-Python
module (`nist_pure.py`) with no import of the `nistrng` package — it is unused. Pinned only
`numpy==2.1.3`, `matplotlib==3.10.0`, `scikit-learn==1.6.1` (versions confirmed via `pip show`
against this repo's existing `ErrorDetectionVSRawBits` environment), with a comment noting why
`nistrng` was dropped.

`pull_seed_sample.py` uses stdlib `urllib.request` rather than the third-party `requests`
library — the plan didn't call for a new HTTP dependency and none exists elsewhere in this repo,
so stdlib keeps the script dependency-free (consistent with "does not import `qeaas` at all").
Error handling keys off `response["error"]` (not `"detail"`) and the admin-mint plaintext key is
under `response["api_key"]` — both confirmed against the live `qeaas/errors.py` flat error
envelope and `AdminKeyResponse` schema during exploration.

Ran the real Phase 0–4 sequence against the live deployment: minted a dedicated `iot`-tier key
(`owner: "seed-quality-report"`), pulled 1,572,864 bytes via 384 sequential calls (~330s wall
time — each call carries a Vercel round-trip, so the pull script needs several minutes, not
seconds), drew the equal-size `os.urandom` baseline, and ran `qrng_compare.py` unmodified. All
four streams (service raw/whitened, urandom raw/whitened) passed NIST SP 800-22, next-bit ML,
and Markov dependency checks, with bias indistinguishable between service and urandom — see §2
AC-5 for the numbers.

No follow-ups required. The committed PDF is a one-time snapshot per Decision 4/Q4 — a future
re-run after a pool refill is a deliberate separate commit, not scheduled here.

---

## 10. Open questions — RESOLVED

**Q1 — Sample size? → RESOLVED: `1,572,864` bytes (1.5 MB, 384 × 4096-byte calls).**
Comfortably inside the build plan's "~1–2 MB" range, round arithmetic, leaves headroom under the
`iot` key's 10 MiB/day quota for a same-day re-run if the first PDF looks off.

**Q2 — Retry behavior on `429`s? → RESOLVED: retry transient per-minute rate-limit 429s (short
back-off), abort loudly on daily-quota-exhaustion 429s (no retry/sleep-until-tomorrow).**
Retrying rate limits is just defensive (a sequential 384-call loop won't realistically hit
`TIER_RATE_LIMITS["iot"] = 600/min`); quota exhaustion should surface immediately rather than
silently stalling — re-run tomorrow or mint a second key.

**Q3 — `requirements-report.txt` version pins? → RESOLVED: pin to whatever versions already
work for `qrng_compare.py` in this repo today** (check via `pip freeze` in whatever environment
last ran it successfully). This is validation tooling, not a product dependency — matching
known-working versions removes a variable.

**Q4 — Is the committed PDF regenerated on every rerun? → RESOLVED: no — one-time snapshot,
committed as-is.** A fresher report later (e.g. after a future pool refill) is a deliberate
manual re-run and a new commit, not something this plan schedules or automates.
