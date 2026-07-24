# Plan 2 — Salt engine: PRNG/CSPRNG/QRNG sources, rotation, JS↔Python parity

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 1** · **Priority:** `[MUST]`
**Status:** Draft · **Depends on:** P1 · **Gates:** P3, P4, P5, P6

> Pick up with `/plan-feature plans/plan-2-salt-engine-sources-rotation.md`. Read epic §3.2 (QRNG role),
> §3.5 (frozen interfaces), §4 (shared artefacts), and **Appendix A (Q-EaaS runbook)** first.
> **This plan integrates the existing Q-EaaS QRNG service and is where the API key is minted.**

## Goal
One hash+salt engine, three interchangeable salt sources, rotation as a controller knob, and the shared JS/Python
test vectors that stop the demo drifting from the real code. These signatures are **frozen here** and consumed
unchanged by P3–P6 (epic §3.5).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] `link = hash(5tuple, salt) mod N`; single Python implementation used by controller and attacker.
- [ ] `salt_source(kind)`: `prng` (weak, fixed/guessable seed) | `csprng` (`secrets`) | `qrng` (Q-EaaS `GET /v1/random/bytes`, show provenance: timestamp, byte count, endpoint).
- [ ] Controller rotates the active salt every `interval` (configurable, minutes → sub-second); reinstalls group rules atomically; logs each rotation event + new salt.
- [ ] Rotation is a no-op for correctness — legitimate flows just redistribute fairly.
- [ ] Shared test vectors: identical `(5tuple, salt) → link` in Python and JS. CI/asserts fail if they drift.
- **Done when:** all three sources feed the same hash; rotation reinstalls a fresh mapping live; JS and Python agree on every vector.

## The QRNG source — the user's "practical QRNG use" (epic §3.2)
The `qrng` kind calls the existing service:
```
GET /v1/random/bytes?size=32&format=hex     Header: X-API-Key: <key>
→ { request_id, format, data, entropy_epoch, timestamp, receipt }
```
- Record and expose the **provenance** (`request_id`, `entropy_epoch`, `timestamp`, Ed25519 `receipt`, endpoint) —
  this is the attestable-entropy value the demo (P6) and paper (P7) surface. Honest framing: provenance/attestation,
  **not** "stops the attack better" (null result is real — epic §3.2).
- **No Python client for this endpoint exists in the repo** — write a thin one. Handle `503 low_quantum_entropy`
  (entropy gate), `429` (`Retry-After`, quota/rate), `401` (auth) — degrade or retry, never crash the controller.
- **Mint the API key** — Appendix A.2: `python -m scripts.mint_key --owner ecmp-dos-testbed --tier default`
  (or `POST /admin/keys` with `X-Admin-Token`). **Resolved (epic §8 Q6):** the project owner holds `ADMIN_TOKEN`
  and mints the key; rate/quota is a non-issue, so **point the `qrng` source at hosted `https://api.qeaas.eu`**
  (both demo and sweeps), with local `localhost:8000` as an optional offline fallback. `default` tier is ample.

## Conventions
- `csprng` → `secrets.token_bytes`. `prng` → `random` with a fixed/known seed (the attacker's brute-force target).
- Rotation must be **atomic** (reinstall group rules without a correctness gap) and log `{ts, old, new, interval}`.
- **Rotation unit = per-time-interval** (epic §8 Q2, resolved): rotate every `interval` regardless of traffic.
  Preserve ECMP flow-affinity where possible; the reordering cost to in-flight legitimate flows is measured as an
  Exp 4 secondary metric (P5).

## Out of scope
Consuming the sources in the experiment matrix (P5); the visual provenance display (P6); brute-forcing the PRNG
seed (that's the attacker, P3).

## Risks
- **JS/Python hash drift** → shared test vectors, asserted in CI (an AC here).
- **Q-EaaS unreachable / entropy-gated mid-run** → client fallback + clear logging; document the behaviour so
  experiments record which source actually served each salt.
