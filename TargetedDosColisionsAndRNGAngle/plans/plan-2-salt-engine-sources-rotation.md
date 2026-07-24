# Plan 2 — Salt engine: PRNG/CSPRNG/QRNG sources, rotation, JS↔Python parity

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 1** · **Priority:** `[MUST]`
**Status:** Complete · **Depends on:** P1 (topology + confirmed controller-side hash path) · **Gates:** P3, P4, P5, P6

> Pick up with `/plan-feature plans/plan-2-salt-engine-sources-rotation.md`. Read epic §3.2 (QRNG role),
> §3.5 (frozen interfaces), §4 (shared artefacts), §5 (salt lifecycle), and **Appendix A (Q-EaaS runbook)** first.
> **This plan integrates the existing Q-EaaS QRNG service and is where the API key is minted.**
> **No GitHub issue** — planned from the epic + source build plan.
> **No automated tests** (project directive) — verification is manual, described in §Manual verification. The
> JS↔Python "assert on drift" AC is satisfied by a standalone **checker script** (like P1's `salt_remap_check.py`
> spike), not a test suite.

## Goal
One hash+salt engine, three interchangeable salt sources, rotation as a controller knob, and the shared JS/Python
test vectors that stop the demo drifting from the real code. The `hash_core` (P1) is reused **unchanged**; the new
surface is the salt-source interface, the QRNG client, controller-driven rotation, and the parity vectors. These
signatures are **frozen here** and consumed unchanged by P3–P6 (epic §3.5).

## Context — what P1 already froze, and what P2 must not touch
P1 landed the controller-side ECMP testbed and **decision D1** (native OVS cannot carry our salt → Ryu/os_ken owns
`hash(5-tuple + salt) mod N` and installs exact-match flow rules). P2 builds directly on these P1 artefacts and
leaves them alone:

- `testbed/hash_core.py` — `ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int`. **Frozen, reused
  unchanged.** Do not fork or reimplement it; P3 (attacker) and P6 (JS mirror) consume this exact function (epic §3.5).
- `testbed/types.py` — `FiveTuple` + `to_bytes()` (canonical order: `inet_aton(src_ip) + inet_aton(dst_ip) +
  struct.pack("!HH", src_port, dst_port) + struct.pack("!B", proto)`). **Load-bearing for JS parity** — the JS
  mirror must reproduce these exact bytes. Do not change the serialisation.
- `testbed/config.py` — `N_LINKS = 4`, `EGRESS_PORTS`, `LOCAL_IP_TO_PORT`, `REMOTE_IPS`, `STATIC_SALT`,
  `CONTROLLER_LISTEN_ADDR/PORT`. P2 **adds** salt-engine config here; the `STATIC_SALT` placeholder stays only as a
  default when rotation/sources are disabled.
- `testbed/controller/ecmp_controller.py` — `ECMPController(OSKenApp)` with `self.active_salt = STATIC_SALT`,
  computes `ecmp_link(...)` on packet-in and installs a priority-10 exact-match flow via `self._add_flow(...)`.
  **P2 makes `active_salt` come from a source and become rotatable** — this is the one P1 file P2 edits.

> **D1 consequence for rotation (important):** because ECMP is controller-side exact-match — **not** OVS `select`
> groups — the build plan's phrase "reinstalls group **rules** atomically" means *the installed exact-match ECMP
> flows*, not OVS group buckets. The controller lazily installs one flow per observed 5-tuple bound for a
> `REMOTE_IPS` destination; on rotation those flows are stale and must be re-resolved under the new salt. See
> §Rotation design for the atomic mechanism.

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`, EPIC 1)
- **AC-1** — `link = hash(5tuple, salt) mod N`; single Python implementation used by controller and attacker.
  **Covered by:** `testbed/hash_core.py:14-17` (unchanged, reused verbatim), imported by
  `testbed/controller/ecmp_controller.py:149,185` and `testbed/vectors/gen_vectors.py:53`.
- **AC-2** — `salt_source(kind)`: `prng` (weak, fixed/guessable seed) | `csprng` (`secrets`) | `qrng` (Q-EaaS
  `GET /v1/random/bytes`, show provenance: timestamp, byte count, endpoint).
  **Covered by:** `testbed/salt/sources.py:52-107` (dispatch + all three sources), provenance in
  `testbed/salt/sources.py:33-46`. QRNG client `testbed/salt/qrng_client.py` — manually verified live against
  `https://api.qeaas.eu` (invalid key → `QRNGUnavailable("invalid_api_key")`; unreachable host → retried 3x then
  `QRNGUnavailable`, no crash).
- **AC-3** — Controller rotates the active salt every `interval` (configurable, minutes → sub-second); reinstalls
  group rules atomically; logs each rotation event + new salt.
  **Covered by:** `testbed/controller/ecmp_controller.py:76-77` (timer, `hub.spawn`), `:169-212` (`rotate_salt` +
  loop), `:214-267` (bundle path), rotation log `testbed/salt/rotation_log.py:12-30`.
- **AC-4** — Rotation is a no-op for correctness — legitimate flows just redistribute fairly.
  **Covered by:** `testbed/controller/ecmp_controller.py:269-286` (`_rotate_via_delete_and_reresolve`: deletes
  and lets packet-in lazily re-resolve, never drops). Live traffic confirmation (Mininet + root) is a manual step
  not run in this session — see Post-implementation notes.
- **AC-5** — Shared test vectors: identical `(5tuple, salt) → link` in Python and JS. CI/asserts fail if they drift.
  **Covered by:** `testbed/vectors/gen_vectors.py`, `testbed/vectors/ecmp_hash.js`, `testbed/vectors/check_parity.py`.
  Manually verified: `check_parity.py` → `PASS: 28/28 vectors agree`; deliberately broke `ecmp_hash.js` (flipped
  `src_port`/`dst_port` in the byte encoding) → checker printed all 14 resulting mismatches and exited non-zero,
  then the file was restored and re-verified clean.
- **Done when:** all three sources feed the same hash; rotation reinstalls a fresh mapping live; JS and Python agree
  on every vector.

## Frozen interfaces (epic §3.5 / §4 — consumed unchanged by P3–P6)
These signatures are the contract. Freeze them exactly; downstream plans import, they do not redefine.

```python
# testbed/hash_core.py — REUSED FROM P1, unchanged
def ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int: ...

# testbed/salt/sources.py — NEW (AC-2)
SaltKind = Literal["prng", "csprng", "qrng"]

@dataclass(frozen=True)
class SaltResult:
    salt: bytes                 # the salt bytes fed to ecmp_link
    kind: SaltKind
    provenance: SaltProvenance  # source-tagged provenance (see below)

def salt_source(kind: SaltKind, *, size: int = 32) -> SaltResult:
    """Mint `size` bytes of salt from the named source, with provenance."""
```

`SaltProvenance` is a dataclass carrying the fields the demo (P6) and paper (P7) display. For `qrng` it holds the
real Q-EaaS record `{request_id, entropy_epoch, timestamp, receipt, endpoint, byte_count}`; for `prng`/`csprng` it
holds `{source_note, byte_count}` (and, for `prng`, the seed + draw index so the value is honestly reconstructable —
that is the brute-force target for P3). Provenance is always populated so P5/P6 can tag every run by the source that
actually served the salt (epic §4 run-tagged CSV).

**Rotation event log** (epic §4 artefact, consumed by P5, P6): one JSON object per rotation —
`{"timestamp": <utc iso8601>, "old_salt": <hex>, "new_salt": <hex>, "interval": <seconds>, "kind": <SaltKind>}` —
appended to a rotation log file **and** emitted via `LOG.info` so a P5 replay can reconstruct the salt timeline.

**Shared hash test-vector format** (epic §4 artefact, consumed by P6 + parity checker): a JSON array of
`{"five_tuple": {"src_ip","dst_ip","src_port","dst_port","proto"}, "salt_hex": <hex>, "n_links": <int>,
"link": <int>}`. Python `hash_core` is the source of truth; the JSON is generated from it and the JS mirror must
reproduce every `link`.

## Rotation design (AC-3, AC-4) — atomic under controller-side exact-match
Rotation lives in the controller (`ECMPController`). Resolved epic §8 Q2: **rotation unit = per-time-interval**
(rotate every `interval` regardless of traffic).

1. **Track installed ECMP flows.** The controller keeps `self._ecmp_flows: set[FiveTuple]` — every 5-tuple for
   which it installed a priority-10 exact-match ECMP flow (the `REMOTE_IPS` branch). Leaf-local flows are not
   tracked (they never depend on the salt).
2. **Timer.** On start, if `ROTATION_INTERVAL_SECONDS` is set (> 0), spawn a rotation greenlet via os_ken
   `hub.spawn` that loops `hub.sleep(interval)` → `self.rotate_salt()`. If unset/`0`, rotation is disabled and the
   controller behaves exactly like P1 (static salt) — this preserves P1 boot behaviour.
3. **`rotate_salt()`** (also callable manually / from the demo, see OQ-5):
   - `new = salt_source(self.salt_kind)`; capture `old = self.active_salt`.
   - Recompute the egress port for every tracked 5-tuple under `new.salt`.
   - Push the swap **atomically** using an OpenFlow **bundle** (`OFPBundleCtrlMsg` OPEN → `OFPFlowMod` DELETE of the
     tracked ECMP flows + ADD of their recomputed replacements → COMMIT). A bundle commits as a unit, so there is no
     window where a tracked flow is missing. **Fallback** if the OVS/OF1.5 build rejects bundles (verify in the
     spike step of manual verification): delete all priority-10 ECMP flows, clear `self._ecmp_flows`, and let the
     next packet-in lazily re-resolve under the new salt — a brief controller round-trip, no packet drop, no
     correctness gap. Record which mechanism is used in `testbed/README.md`.
   - Set `self.active_salt = new.salt`; append the rotation event log entry (§Frozen interfaces).
4. **Flow-affinity (Q2 note).** Rotating mid-flow reshuffles in-flight legitimate flows across links. P2 preserves
   affinity where it cheaply can (bundle keeps the swap instantaneous), but the reordering *cost* to legitimate
   traffic is not measured here — that is an Exp 4 secondary metric owned by P5. P2 only guarantees **correctness**:
   after rotation every flow still reaches its destination (AC-4), just possibly via a different link.

**AC-4 in this model:** legitimate traffic to `REMOTE_IPS` is delivered by whichever egress link the current salt
selects; rotation changes *which* link, never *whether* it is delivered. No flow is dropped, so a clean background
run shows flows simply redistributing (Jain's index stays high — measured in P5). This is the correctness invariant
from epic §5.

## The QRNG source — the user's "practical QRNG use" (epic §3.2, Appendix A)
The `qrng` kind calls the existing service (schema verified against `qrng-eaas/api/`):
```
GET /v1/random/bytes?size=32&format=hex        Header: X-API-Key: <key>
→ V1RandomBytesResponse { request_id, format, data, entropy_epoch, timestamp, receipt }
```
- `data` is the hex salt; `receipt` is an Ed25519-signed token (nullable in the schema — handle `None`);
  `entropy_epoch` is the DRBG reseed counter. Record all of `{request_id, entropy_epoch, timestamp, receipt,
  endpoint, byte_count}` into `SaltProvenance` — this is the attestable-entropy value P6/P7 surface. Honest framing:
  provenance/attestation, **not** "stops the attack better" (the null result is real — epic §3.2).
- **No Python client for this endpoint exists in the repo** — write a thin one (`testbed/salt/qrng_client.py`).
  Handle `401 missing/invalid_api_key` (auth — fail loudly, misconfiguration), `429` (honour `Retry-After`,
  quota/rate), `503 low_quantum_entropy` (entropy gate — retry with backoff). On retry exhaustion raise a typed
  `QRNGUnavailable`; the caller (salt engine / controller) decides fallback and **logs which source actually served
  the salt** so experiments record it honestly (epic §3.2, Risk below). Never crash the controller.
- **Mint the API key** — Appendix A.2: `python -m scripts.mint_key --owner ecmp-dos-testbed --tier default`
  (run from `qrng-eaas/api/`), or `POST /admin/keys` with `X-Admin-Token`. **Resolved (epic §8 Q6):** the project
  owner holds `ADMIN_TOKEN` and mints the key; rate/quota is a non-issue, so **point the `qrng` source at hosted
  `https://api.qeaas.eu`** (both demo and sweeps), with local `http://localhost:8000` as an optional offline
  fallback. `default` tier (256 KB/day) is ample — a 32-byte salt every few seconds is far under quota.
- The key is read at runtime from env `QEAAS_API_KEY`; the base URL from `QEAAS_BASE_URL` (default
  `https://api.qeaas.eu`). **Never commit the key** (epic Appendix A.4).

## Conventions
- `csprng` → `secrets.token_bytes(size)`. `qrng` → the client above.
- `prng` → weak, **reconstructable**: a module-level `random.Random` seeded from `PRNG_SEED` (a small, guessable
  seed space — the attacker's brute-force target in P3), drawing successive `size`-byte salts. The seed + draw index
  are recorded in provenance so the value is honestly reproducible. Keep the seed space small enough that P3's
  brute-force is tractable (see OQ-2).
- Rotation must be **atomic** (§Rotation design) and log `{ts, old, new, interval, kind}`.
- Strict typing + PEP 8, matching P1: `from __future__ import annotations`, full type hints on public functions,
  dependency-free `hash_core`/`types` kept importable anywhere.
- All DB/state access — none here; the only external I/O is the QRNG HTTP call and the rotation log file.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. New unless marked **edit**.

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/salt/__init__.py` | Package marker; re-export `salt_source`, `SaltResult`, `SaltKind`. | AC-2 | New package. |
| `testbed/salt/sources.py` | `salt_source(kind, *, size=32) -> SaltResult`; `SaltResult`, `SaltProvenance`, `SaltKind`. Dispatches to prng/csprng/qrng. | AC-2 | The frozen source interface (§3.5). Dependency-free except the QRNG client. |
| `testbed/salt/qrng_client.py` | Thin Q-EaaS client: `QRNGClient(base_url, api_key).fetch(size=32, fmt="hex") -> QRNGResponse`. Handles 401/429/503; typed `QRNGUnavailable`. | AC-2 | Mirrors the README curl example; `urllib`/`requests` (see Tech). Reads no secrets itself — caller passes them. |
| `testbed/config.py` | **edit** — add `SALT_KIND` (default `"prng"`), `ROTATION_INTERVAL_SECONDS` (default `0` = off), `PRNG_SEED`, `SALT_SIZE = 32`, `QEAAS_BASE_URL`/`QEAAS_API_KEY` (from env), `ROTATION_LOG_PATH`. Keep `STATIC_SALT` as the disabled-rotation default. | AC-3 | Knobs as data, not literals. |
| `testbed/controller/ecmp_controller.py` | **edit** — seed `self.active_salt` from `salt_source(SALT_KIND)`; track `self._ecmp_flows`; add `rotate_salt()` + `hub.spawn` timer when `ROTATION_INTERVAL_SECONDS > 0`; write rotation event log. | AC-3, AC-4 | The one P1 file P2 changes. Static-salt path preserved when rotation off. |
| `testbed/salt/rotation_log.py` | Append-only rotation event writer + reader (JSON lines), format per §Frozen interfaces. | AC-3 | Small helper so P5 can replay the salt timeline. |
| `testbed/vectors/gen_vectors.py` | Generate `hash_vectors.json` from Python `hash_core` (source of truth): a spread of 5-tuples × several salts × `N_LINKS`. | AC-5 | Standalone script, imports only `hash_core`/`types`. |
| `testbed/vectors/hash_vectors.json` | The generated shared vectors (committed artefact). | AC-5 | Consumed by P6 + the parity checker (epic §4). |
| `testbed/vectors/ecmp_hash.js` | **JS mirror** of `FiveTuple.to_bytes` + `ecmp_link` (SubtleCrypto SHA-256, 4-byte IPs, big-endian ports, first-8-bytes-as-uint64 via `BigInt`, `mod n_links`). Async. | AC-5 | The canonical JS the P6 demo imports — one copy, no drift. |
| `testbed/vectors/check_parity.py` | Standalone checker: load `hash_vectors.json`, recompute each `link` via Node running `ecmp_hash.js`, **exit non-zero on any mismatch** and print the offending vector. | AC-5 | The "asserts fail on drift" AC, framed as a manual checker like P1's spike (no test suite — project directive). |
| `testbed/README.md` | **edit** — add: how to select a salt source, mint/point the QRNG key, run a rotation demo, and run `check_parity.py`. Record the rotation atomic mechanism actually used (bundle vs delete-and-reresolve). | — | Extends P1's runbook. |
| `requirements.txt` | **edit** — add the HTTP client if `requests` is chosen over stdlib `urllib` (see Tech). Note Node is needed only to run the parity checker. | — | Keep the os-ken note from P1. |

## Manual verification (no automated tests — project directive)
Run from `TargetedDosColisionsAndRNGAngle/`.

1. **AC-2 sources** — a scratch REPL / one-off script:
   `salt_source("csprng")` returns 32 random bytes with `source_note` provenance; two calls differ.
   `salt_source("prng")` with a fixed `PRNG_SEED` is reproducible across process restarts (same seed → same
   sequence) and provenance records seed + draw index.
   `salt_source("qrng")` (with `QEAAS_API_KEY` set, base `https://api.qeaas.eu`) returns 32 bytes and provenance
   with a real `request_id`, `entropy_epoch`, `timestamp`, `receipt`. Confirm against the README curl example.
2. **QRNG failure handling** — point `QEAAS_BASE_URL` at an unreachable host (or use an invalid key): the client
   raises `QRNGUnavailable` / surfaces `401`, the caller logs it and does **not** crash. If a live `503
   low_quantum_entropy` cannot be reproduced, confirm the retry/backoff path by unit-poking the client with a
   stubbed response — described in the README, not committed as a test.
3. **AC-1 shared hash** — boot the P1 topology + controller with `SALT_KIND="prng"`, `ROTATION_INTERVAL_SECONDS=0`;
   confirm traffic to `REMOTE_IPS` still spreads across the N links exactly as in P1 (the source-fed salt is just a
   different constant, same `ecmp_link`).
4. **AC-3 rotation live** — set `ROTATION_INTERVAL_SECONDS=5`, `SALT_KIND="csprng"`; drive a steady flow from
   `attacker`/`bg` to a spine host; watch the controller log emit a rotation event every ~5 s and the flow's egress
   port change after a rotation. Confirm the rotation log file has one well-formed JSON line per event with
   `old_salt`/`new_salt` differing.
5. **AC-4 no-op correctness** — during step 4, confirm `attacker ping <spine host>` and an `iperf` flow keep working
   across rotations (no sustained loss); pings continue, just possibly re-pathed. (Quantified fairness is P5, not
   here — here we only confirm nothing breaks.)
6. **AC-5 parity** — `python testbed/vectors/gen_vectors.py` regenerates `hash_vectors.json`; then
   `python testbed/vectors/check_parity.py` runs the JS mirror over every vector and exits `0` with "N/N vectors
   agree". Deliberately break `ecmp_hash.js` (e.g. flip endianness) and confirm the checker exits non-zero and names
   the first mismatch — proving it actually catches drift.

## Tech
- Python 3, os_ken (Ryu fork) for the controller — same as P1.
- QRNG client: prefer **stdlib `urllib.request`** to avoid a new dependency; if retry/`Retry-After` handling gets
  awkward, add `requests` to `requirements.txt` (decide in OQ-3’s sibling — keep it stdlib if reasonable).
- JS mirror uses **SubtleCrypto** (`crypto.subtle.digest("SHA-256", …)`) so it runs unchanged in the P6 browser
  demo; the parity checker runs the same file under **Node** (`node`), which exposes `crypto.subtle`.
- os_ken `hub.spawn` / `hub.sleep` for the rotation timer (green-thread friendly inside the controller event loop).

## Out of scope
- Consuming the sources in the experiment matrix, and measuring rotation reordering/fairness cost (P5).
- The visual provenance display / the live demo (P6) — P2 only produces the JS mirror + vectors P6 imports.
- Brute-forcing the PRNG seed, the collision crafter, knowledge levels (P3).
- The defences (rate-limit/throttle) and metrics CSV (P4).
- Any change to `hash_core.ecmp_link` or `FiveTuple.to_bytes` (frozen by P1 — changing them breaks every downstream
  plan).

## Risks
- **JS/Python hash drift** (AC-5) → the whole demo silently lies. Mitigated by the parity checker over generated
  vectors; the serialisation (`to_bytes`) and the first-8-bytes-big-endian-`% N` step are the exact drift points to
  watch (BigInt vs Python int, IP byte order, port endianness).
- **Atomic rotation mechanism** → if OF1.5 bundles are unsupported on this OVS build, the delete-and-re-resolve
  fallback introduces a sub-millisecond controller round-trip per stale flow (not a drop). Verify bundle support in
  manual step 4 and record the choice.
- **Q-EaaS unreachable / entropy-gated mid-run** → client fallback + explicit logging of the source that actually
  served each salt, so P5 experiment tags are honest (epic §3.2). Never crash the controller.
- **Weak-PRNG seed space too large** → P3's brute-force (partial-knowledge attacker) becomes intractable and Exp 5
  loses meaning. Keep `PRNG_SEED` in a small, documented space (OQ-2).

## Open questions — RESOLVED (2026-07-24, all defaults accepted)
Epic-wide questions resolved (epic §8 all ticked). P2-implementation specifics, now decided:

- [x] **OQ-1 (atomic mechanism).** **RESOLVED:** try an OpenFlow bundle first (true atomic, preserves affinity
  best); fall back to delete-and-lazy-re-resolve if the OVS/OF1.5 build rejects bundles; record which is used in the
  README. Verified during manual step 4.
- [x] **OQ-2 (weak-PRNG model + seed space).** **RESOLVED:** stateful sequential draws from `random.Random(PRNG_SEED)`
  over a **32-bit seed space**, successive `size`-byte draws, draw index in provenance. The seed is P3's
  brute-force target — small enough to be tractable, honest as a "weak PRNG."
- [x] **OQ-3 (HTTP dependency).** **RESOLVED:** stdlib `urllib.request` (no new dependency); only add `requests` if
  `Retry-After`/backoff handling proves clumsy in implementation.
- [x] **OQ-4 (secret handling at runtime).** **RESOLVED:** `QEAAS_API_KEY` lives in an environment variable only,
  read by config, never committed (epic Appendix A.4). README documents the `export QEAAS_API_KEY=…` step.
- [x] **OQ-5 (manual rotation trigger).** **RESOLVED:** expose `rotate_salt()` for manual/demo invocation in
  addition to the timer; the P6 rotation slider and manual verification both call it, the timer calls the same
  method.

## Notes for `/implement-feature` (downstream)
- Reuse `hash_core.ecmp_link` and `FiveTuple` **verbatim** — do not copy or re-implement (epic §3.5).
- The frozen signatures in §Frozen interfaces are the contract P3–P6 import against; keep them stable.
- P6 imports `testbed/vectors/ecmp_hash.js` and `hash_vectors.json` directly — treat them as a published artefact.
- Mint the `ecmp-dos-testbed` key during setup (Appendix A.2) and export `QEAAS_API_KEY` before running the `qrng`
  source; the hosted `https://api.qeaas.eu` is the default target.

## §13 Post-Implementation

Built the full P2 file plan: `testbed/salt/` package (`sources.py`, `qrng_client.py`, `rotation_log.py`,
`__init__.py`), `testbed/vectors/` (`gen_vectors.py`, `hash_vectors.json`, `ecmp_hash.js`, `check_parity.py`),
edits to `testbed/config.py` and `testbed/controller/ecmp_controller.py`, and `testbed/README.md` / `requirements.txt`
notes. `hash_core.ecmp_link`/`FiveTuple` untouched.

**Verified this session (no Mininet/root available in this environment):**
- `salt_source("prng"|"csprng"|"qrng")` all import and run; `prng` is sequential/reproducible per `PRNG_SEED`,
  `csprng` differs every call.
- QRNG client hit the **live hosted** `https://api.qeaas.eu`: an invalid key correctly raises
  `QRNGUnavailable("...invalid_api_key...")`; an unreachable host retries 3x with backoff then raises
  `QRNGUnavailable`, never crashing. Could not exercise a real `429`/`503` without a valid minted key — the
  retry/backoff code paths for those are implemented per the plan but unexercised live.
- `check_parity.py` (Node driver inlined via `node -e` in the script, not a separate file) ran end-to-end:
  `gen_vectors.py` produced 28 vectors, `check_parity.py` reported **28/28 agree**; deliberately swapping
  `src_port`/`dst_port` in `ecmp_hash.js`'s byte encoding made it report 14 mismatches and exit non-zero, then
  the file was restored and re-verified clean.

**Not verified (needs the real testbed environment — Mininet + OVS + root, not available in this session):**
- AC-3 live rotation (controller log emitting rotation events on a timer, egress port changing).
- AC-4 no-drop confirmation under real traffic during rotation.
- Whether this box's OVS/OF1.5 build actually accepts OpenFlow bundles or falls back to delete-and-re-resolve —
  the README has a `<TODO>` marker at that spot for whoever runs step 4 live to fill in.
- Bundle-vs-fallback event wiring (`bundle_ctrl_handler` / `error_msg_handler`) is implemented against the real
  os_ken `ofproto_v1_5` API (constants/signatures checked directly against the installed package) but has not
  seen a live OpenFlow switch.

**Deviations from the plan:** none in scope or interfaces. One implementation-detail deviation from the literal
file plan: the Node driver for `check_parity.py` is inlined as a string in that script (`node -e`) rather than a
separate `.js` file, since the plan's file list didn't include one and this avoids adding an unplanned file.
