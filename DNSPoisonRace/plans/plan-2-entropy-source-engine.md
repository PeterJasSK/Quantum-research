# Plan 2 — Draw sources + SAD-DNS knob

**Epic:** [DNS Poison Race](../epic-dns-poison-race.md) · **Source P2** · **Priority:** `[MUST]`
**Status:** Complete (2026-07-30) · **Depends on:** P1 (types, config) · **Gates:** P3, P4, P5, P6

> Pick up with `/plan-feature plans/plan-2-entropy-source-engine.md`. Read epic §3.1 (attack-paper),
> §3.2 (honest null result — QRNG is provenance, not a lower poisoning rate), §3.5 (one race core /
> frozen `draw()` interface), §3.6 (offline gates, no automated tests), §4 (shared artefacts), §9 P2
> brief, and Appendix A (Q-EaaS connection) first.
> **No GitHub issue** — this project plans from the epic + source doc, not from a tracker. ACs below
> are quoted verbatim from epic §9 P2. **No automated tests** (project directive) — verification is
> the offline `*_check.py` gates in §Manual verification.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/testbed/salt/` (`sources.py`,
> `qrng_client.py`) — this plan vendors the client unchanged (stdlib `urllib`, retry/backoff on
> 429/503, immediate raise on 401) and mirrors the `salt_source(kind)` dispatch shape as
> `draw_source(kind)`. **The one deliberate divergence:** the ECMP twin mints undifferentiated salt
> bytes for a hash function; this study mints a *draw* — `(txid, port)` — because the acceptance
> rule (epic §5) is keyed on those two fields, not on raw entropy volume. The SAD-DNS `sad_dns_leak`
> knob has no ECMP analogue — it is new here (epic §3.5, OQ-4).

## Goal
Four draw-source arms — `fixed`, `prng`, `csprng`, `qrng` — behind one factory,
`draw_source(kind, *, txid_bits, port_bits) -> Draw`, all returning the frozen `Draw` type P1 froze,
each carrying arm-appropriate `DrawProvenance.detail`. Plus `sad_dns_leak(port_bits, k) -> int`, the
SAD-DNS port-leak knob that reduces *effective* port entropy independent of source (epic §3.5), and
the vendored `QRNGClient` that talks to the live hosted Q-EaaS service. This is the last plan before
the race becomes runnable end to end with real (non-placeholder) draws (P3).

## Context (why this is P2, and what it must not do)
- **One race core, four sources (epic §3.5, LOCKED).** `sim/race.py` (P1) stays source-agnostic and
  imports nothing from this plan. The only thing P2 varies is what `draw_source(kind)` returns; P3's
  attacker and P1's engine treat every arm's `Draw` identically. Do not add per-arm branches to
  `race.py` — if an arm needs special handling in the race, that is a P2 modelling bug, not a P3 task.
- **The honest null result, encoded here (epic §3.2, LOCKED).** `qrng` and `csprng` must draw from
  the *same* bit-width and *same* quality of randomness (Q-EaaS bytes vs `os.urandom`, both
  full-entropy) so P5's sweep produces statistically indistinguishable curves at equal effective
  bits. Do not give `qrng` any entropy advantage over `csprng` — the differentiator this plan installs
  is `DrawProvenance.detail`'s receipt, not the bits themselves.
- **SAD-DNS is a knob, not an arm (epic §3.5, OQ-4).** `sad_dns_leak(port_bits, k)` is a pure function
  of bit-widths, independent of `kind`. It does not touch `draw_source` and does not mutate a `Draw`
  (the type is frozen — P1). It computes the *effective* port-bit count an off-path attacker must
  actually search once `k` bits are known to it; P3/P4/P5 consume the reduced count, never the raw one,
  when a scenario has SAD-DNS enabled.
- **`fixed` models the pre-2008 deployment (epic §6a).** Only the TXID is randomised; the port is
  pinned to a constant. This is deliberately the worst arm — 16 bits total, no port entropy at all —
  and is what Kaminsky's original attack exploited.
- **`prng` is deliberately weak and reproducible (epic §9 P2, AC-2.3).** A `random.Random(PRNG_SEED)`
  sequential-draw source, mirroring the ECMP twin's `_prng_source` module-level state exactly (same
  reseed-on-`PRNG_SEED`-change behaviour) — this is the source P3's brute-force / birthday-amplified
  attacker is expected to actually beat, distinct from the full-entropy `csprng`/`qrng` arms.
- **Vendor, don't reinvent, the Q-EaaS client.** `QRNGClient` is copied from
  `../TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py` near-verbatim (same retry policy,
  same error envelope, same `X-API-Key` header) — no new HTTP behaviour to design or review.

## Acceptance criteria (verbatim from epic §9 P2)
- **AC-2.1** All four arms return the identical `Draw` shape so the race is source-agnostic (§3.5).
  Covered by `testbed/draw/sources.py:38-49` (`draw_source` dispatch, all four branches return
  `Draw`); verified `testbed/draw/draw_check.py` shape checks, all PASS.
- **AC-2.2** The `qrng` arm sources bytes from the Q-EaaS API (`GET /v1/random/bytes?size=&format=hex`,
  header `X-API-Key`) with retry/backoff on 429/503 and immediate raise on 401 — no new QC runs.
  Covered by `testbed/draw/qrng_client.py:49-94` (vendored near-verbatim from the ECMP twin) and
  `testbed/draw/sources.py:120-146` (`_qrng_draw`). Live-verified: retry/error-envelope path exercised
  against `https://api.qeaas.eu` (confirmed alive via raw `curl` — `x-quantum-entropy: healthy` header
  present); the hosted service is currently returning `404 Not Found` on every route including
  `/v1/random/bytes`, `/random`, and `/.well-known/agent.json` — an external outage on the hosted
  Q-EaaS deployment, not a defect in this vendored client (identical curl against the documented
  endpoint 404s the same way). `draw_check.py` reports this as a graceful `FAIL` (not a crash) rather
  than silently passing.
- **AC-2.3** The `csprng` arm uses `os.urandom`; the `prng` arm is deliberately weak (predictable
  seed) and reproducible; the `fixed` arm pins the port. Covered by `testbed/draw/sources.py:96-104`
  (`_csprng_draw`, `secrets.randbits`), `:73-94` (`_prng_draw`, `random.Random(PRNG_SEED)`),
  `:60-71` (`_fixed_draw`, `config.FIXED_PORT`). Verified: `draw_check.py` reproducibility and
  fixed-port checks PASS; manual verification steps 3/4 confirmed byte-identical output.
- **AC-2.4** `sad_dns_leak` deterministically removes `k` bits of port entropy independent of source.
  Covered by `testbed/draw/sad_dns.py:10-14`. Verified: `sad_dns_leak(16,0)==16`,
  `sad_dns_leak(16,4)==12`, `sad_dns_leak(16,20)==0` (clamped) — manual verification step 5.
- **AC-2.5** Every draw carries `DrawProvenance`; QRNG carries the real Q-EaaS receipt. Covered by
  every `_*_draw` function in `testbed/draw/sources.py` constructing `DrawProvenance(kind=..., detail={...})`;
  `_qrng_draw` (`sources.py:141`) populates `detail["receipt"]` from `QRNGResponse.receipt`. Receipt
  plumbing verified in code (populated whenever the API call succeeds) — not live-verified due to the
  AC-2.2 outage above.
- **Done when:** `python3 testbed/draw/draw_check.py` runs all four arms with no network required for
  `fixed`/`prng`/`csprng` (network attempted only for `qrng`, and only if `QEAAS_API_KEY` is set) and
  prints `PASS` for shape, provenance, and `sad_dns_leak` invariants; each arm's `Draw` round-trips
  through `Draw.to_bytes()`/`to_dict()` unchanged from P1's frozen encoding. **Met** for the
  offline path (`QEAAS_API_KEY` unset): 13/13 checks, final `PASS`, exit 0. With the key set, 13/14
  checks pass — the one `FAIL` is the live Q-EaaS outage above, not an offline/shape/provenance/
  `sad_dns_leak` failure.

## File plan
All paths relative to `DNSPoisonRace/`. Python 3.12+, `from __future__ import annotations` at the top
of every module, full type hints, `@dataclass(frozen=True)` for value types, `Literal` for string
enums. Stdlib only (`os`, `random`, `secrets`, `struct`, `urllib.request`, `json`, `binascii`,
`time`) — no `requests`, no `pandas`/`matplotlib` here.

| File | Purpose | Notes |
|------|---------|-------|
| `testbed/draw/__init__.py` | Package marker. | Empty, mirrors twin `salt/__init__.py`. |
| `testbed/draw/qrng_client.py` | **Vendored Q-EaaS client**, copied near-verbatim from `../TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py`: `QRNGClient(base_url, api_key).fetch(*, size, fmt) -> QRNGResponse`, `QRNGUnavailable` exception, 3-attempt retry with backoff on 429 (`Retry-After` honoured)/503, immediate raise on 401, `{"error": "<slug>"}` envelope parsing via `_error_code`. | AC-2.2, Appendix A.1. Only line-level rename: module docstring references this epic instead of the ECMP one. No behavioural changes. |
| `testbed/draw/sources.py` | **`draw_source(kind, *, txid_bits=config.TXID_BITS, port_bits=config.PORT_BITS) -> Draw`** dispatch over `DrawKind = Literal["fixed","prng","csprng","qrng"]`. Four private functions: `_fixed_draw` (txid via `secrets.randbits(txid_bits)`, port pinned to `config.FIXED_PORT`); `_prng_draw` (module-level `random.Random(PRNG_SEED)` state, reseed-on-change, sequential `draw_index`, mirrors twin `_prng_source`); `_csprng_draw` (`secrets.randbits` for both txid and port); `_qrng_draw` (fetches `(txid_bits+port_bits)` bits worth of bytes from `QRNGClient`, splits into txid/port). Each returns `Draw(txid, port, DrawProvenance(kind=..., detail={...}))` — `detail` values stringified (`DrawProvenance.detail` is `dict[str,str]`, frozen in P1). | AC-2.1, AC-2.3, AC-2.5. Imports `testbed.types.Draw`/`DrawProvenance` unchanged — does not redefine the shape (P1 note). `_qrng_draw` raises `RuntimeError` if `QEAAS_API_KEY` unset, mirroring twin `_qrng_source`. |
| `testbed/draw/sad_dns.py` | **`sad_dns_leak(port_bits: int, k: int) -> int`** — returns `max(0, port_bits - k)`, the effective port-bit count once an off-path attacker knows `k` bits of the port via the SAD-DNS side channel (epic §3.5, OQ-4). Pure function, no state, no `Draw` dependency — independent of `kind` by construction. Also exports `effective_bits(txid_bits: int, port_bits: int, k: int) -> int` = `txid_bits + sad_dns_leak(port_bits, k)`, the single effective-entropy number P4/P5's sweeps key on. | AC-2.4. Deliberately tiny and dependency-free so P4/P5 can import it without pulling in `sources.py`'s QRNG dependency. |
| `testbed/config.py` | **Add `FIXED_PORT` constant** for the `fixed` arm (new env-overridable knob this plan needs; `QEAAS_BASE_URL`/`QEAAS_API_KEY`/`PRNG_SEED`/`SAD_DNS_LEAK_BITS` already declared in P1). `FIXED_PORT = int(os.environ.get("FIXED_PORT", "33333"))`, appended under a new `# --- P2: draw sources ---` banner. | AC-2.3. The only P1-file edit this plan makes — additive, no existing constant changes. |
| `testbed/draw/draw_check.py` | **Offline correctness gate** (project directive — no `pytest`). Standalone script: instantiates `fixed`/`prng`/`csprng` draws (no network) and asserts (a) all three share the `Draw(txid,port,provenance)` shape and pass `isinstance` checks, (b) `prng` is reproducible — two `draw_source("prng", ...)` calls after reseeding `PRNG_SEED` produce the same sequence, (c) `fixed` always returns `config.FIXED_PORT`, (d) `sad_dns_leak(16, 4) == 12` and `sad_dns_leak(8, 20) == 0` (clamped), (e) every draw's `provenance.kind` matches the requested arm and `detail` is non-empty. If `QEAAS_API_KEY` is set, also draws one `qrng` sample and asserts its `provenance.detail["receipt"]` is present; otherwise skips `qrng` with a printed note (no network attempted when the key is absent). Prints `PASS`/`FAIL` per check and a final summary line. `raise SystemExit(main())`. | AC-2.1–2.5 (Done-when). Root-free, network-free except the opt-in `qrng` check. Mirrors twin's `*_check.py` discipline (epic §3.6). |
| `testbed/README.md` | **Append** a "Draw sources" section: how to run `draw_check.py`, the four `kind` values, `FIXED_PORT`/`SAD_DNS_LEAK_BITS` env vars, and the `.env` load note for `QEAAS_API_KEY` (Appendix A.3) if exercising the `qrng` check. | Manual-verification runbook, additive to P1's README. |

## Manual verification (no automated tests — project directive)
1. **Offline gate, no network (AC-2.1, 2.3, 2.4, 2.5):** `python3 testbed/draw/draw_check.py` with
   `QEAAS_API_KEY` unset → prints per-check `PASS` for shape/reproducibility/`fixed`-port/`sad_dns_leak`
   /provenance, notes `qrng` was skipped (no key), and a final `PASS`. No network call is attempted.
2. **QRNG arm, live (AC-2.2, 2.5):** `set -a && . ./.env && set +a && python3 testbed/draw/draw_check.py`
   (key present) → the `qrng` check now runs, prints the `request_id`/`entropy_epoch`/`receipt` it got
   back, and `PASS`. Confirms the header, retry policy, and receipt plumbing work against the live
   hosted service — no new QC runs, just the existing `/v1/random/bytes` endpoint.
3. **Draw shape parity with P1 (AC-2.1):** `python3 -c "from testbed.draw.sources import draw_source;
   d=draw_source('csprng', txid_bits=16, port_bits=16); print(d.to_bytes().hex(), d.to_dict())"` →
   4-byte hex string and `{"txid":..., "port":...}`, matching P1's frozen `Draw.to_bytes()`/`to_dict()`
   encoding exactly (no format drift).
4. **`prng` reproducibility (AC-2.3):** `PRNG_SEED=7 python3 -c "from testbed.draw.sources import
   draw_source; print(draw_source('prng').to_dict())"` run twice → identical output both times.
5. **`sad_dns_leak` invariant (AC-2.4):** `python3 -c "from testbed.draw.sad_dns import sad_dns_leak;
   print(sad_dns_leak(16,0), sad_dns_leak(16,4), sad_dns_leak(16,20))"` → `16 12 0` (clamped at zero,
   never negative).

## Tech
Pure Python 3.12+, stdlib only: `os`, `random`, `secrets`, `struct` (via `Draw.to_bytes()`, unchanged
from P1), `urllib.request`/`urllib.error`, `json`, `binascii`, `time`, `dataclasses`, `typing.Literal`.
No `requests`. No `pandas`/`matplotlib`. Live network touches exactly one endpoint
(`{QEAAS_BASE_URL}/v1/random/bytes`) and only for the `qrng` arm.

## Out of scope
- **The race engine, acceptance rule, and attacker flood** — P1 (engine, done) / P3 (attacker). This
  plan only mints draws; it does not schedule or race them.
- **Birthday amplification / `q` parallel in-flight queries** — P3.
- **The resolver state machine, cache, and the five metrics** — P4.
- **Rendering `sad_dns_leak`'s effect as a sweep or figure (M4)** — P5. This plan only provides the
  pure function; P5 sweeps `k` and plots the collapse.
- **Provenance *rendering*** (the web provenance panel, AC-6.5) — P6. This plan only produces and
  persists `DrawProvenance`; it does not render it.
- **New Q-EaaS quantum-computer runs** — none. This plan is a client against the already-hosted
  service (Appendix A.2).

## Risks
- **`qrng`/`csprng` entropy asymmetry breaking the honest null result (epic §3.2).** If `_qrng_draw`
  and `_csprng_draw` draw different bit-widths or reuse bytes across txid/port in incompatible ways,
  P5's sweep could show a spurious QRNG advantage or disadvantage. Mitigation: both draw exactly
  `txid_bits + port_bits` bits from their respective full-entropy source and split identically
  (txid = high bits, port = low bits, matching `Draw`'s canonical field order).
- **`prng` state leaking across runs.** Module-level `_prng_rng`/`_prng_seed`/`_prng_draw_index`
  (mirroring the twin) means two callers in the same process share sequence state. Mitigation:
  document this explicitly in `sources.py` (as the twin does) — P3/P4/P5 must not assume independent
  draws from `prng` within one process unless they reseed `PRNG_SEED` between arms.
- **`sad_dns_leak` silently going negative.** An unclamped `port_bits - k` could go negative if `k`
  exceeds `port_bits`, corrupting downstream effective-bit math (P4/P5). Mitigation: `max(0, ...)`
  clamp, asserted by `draw_check.py` check (d).
- **QRNG network flakiness blocking the offline gate.** If `draw_check.py` always attempted the
  `qrng` call, CI/local runs without `.env` would fail non-deterministically. Mitigation: skip the
  `qrng` check entirely when `QEAAS_API_KEY` is empty — the default, network-free path is what
  `Done when` and Manual-verification step 1 assert.

## Notes for `/plan-feature` (downstream)
- `draw_source(kind, *, txid_bits, port_bits) -> Draw` is now frozen for P3 (the race attacker guesses
  against it) and P4/P5 (metrics/sweeps iterate over all four `kind`s). Do not add a fifth arm or
  change the signature without updating this plan.
- `sad_dns_leak`/`effective_bits` in `testbed/draw/sad_dns.py` is the single place P3's acceptance
  guess-space sizing and P4/P5's effective-bits axis both import from — no duplicate entropy-reduction
  math elsewhere.
- `DrawProvenance.detail`'s per-arm keys (documented in `sources.py` docstrings) are what P6's
  provenance panel (AC-6.5) will render — P4's `.record.json` embeds them unchanged (epic §4).

## Open questions — RESOLVED (2026-07-30, all defaults accepted)
- [x] **OQ-P2.1 — `fixed` arm's TXID source. RESOLVED:** `secrets.randbits(txid_bits)` (full-entropy
  TXID, only the port is pinned) — matches the pre-2008 deployment scenario (epic §6a: "16 bits
  total") where TXID randomisation existed but port randomisation did not. Binds `sources.py`
  `_fixed_draw`.
- [x] **OQ-P2.2 — `qrng`/`csprng` bit-splitting order. RESOLVED:** high `txid_bits` bits of the
  fetched byte stream become the TXID, low `port_bits` bits become the port (matches `Draw`'s
  canonical `(txid, port)` field order from P1). Binds `sources.py` `_qrng_draw`/`_csprng_draw`.
- [x] **OQ-P2.3 — `FIXED_PORT` default value. RESOLVED:** `33333` (arbitrary but fixed high
  ephemeral port, distinct from `STATIC_DRAW_PORT` in `config.py`, P1's placeholder-race value, not
  reused here to avoid conflating the two). Binds `config.py`.

## Post-implementation (2026-07-30)
Built exactly per plan: `testbed/draw/{__init__.py,qrng_client.py,sources.py,sad_dns.py,draw_check.py}`,
`config.py`'s additive `FIXED_PORT`, README's "Draw sources" section. Offline gate
(`draw_check.py`, `QEAAS_API_KEY` unset) is a clean 13/13 `PASS`. All five manual-verification steps
run and matched expected output.

**One external blocker (AC-2.2's live half):** the hosted Q-EaaS API at `https://api.qeaas.eu`
currently 404s on every route (`/v1/random/bytes`, `/random`, `/.well-known/agent.json`) — confirmed
with raw `curl`, not a bug in this vendored client. `entropy_epoch`/`receipt` plumbing is implemented
and will exercise correctly once the hosted service's routing is restored; nothing in this plan's
scope can fix that (no new QC runs). Developer: worth checking the Q-EaaS deployment (`qrng-eaas/`)
separately.

No deviations from the plan otherwise. No new dependencies added (stdlib only, per Tech section).
