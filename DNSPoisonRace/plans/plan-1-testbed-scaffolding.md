# Plan 1 — Testbed scaffolding & config

**Epic:** [DNS Poison Race](../epic-dns-poison-race.md) · **Source P1** · **Priority:** `[MUST]`
**Status:** Complete (2026-07-30) · **Depends on:** none (first plan) · **Gates:** P2, P3, P4

> Pick up with `/plan-feature plans/plan-1-testbed-scaffolding.md`. Read epic §3.4 (simulated is
> sufficient), §3.5 (one race core / frozen `draw()` interface), §3.6 (offline gates, no unit tests),
> §4 (shared artefacts / frozen types), §5 (resolver race state machine), §7 (order) first.
> **No GitHub issue** — this project plans from the epic + source doc (`plans/viz-3-dns-poison-race.md`),
> not from a tracker. ACs below are quoted verbatim from epic §9 P1 (which derives them from the source).
> **No automated tests** (project directive) — verification is the offline gates in §Manual verification.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/testbed/` — mirror its layout, `config.py`
> env-constant style, `types.py` frozen-dataclass style, `vectors/` source-of-truth pattern, and
> `*_check.py` / `run_sim.py` run discipline. Every convention here has a working precedent one
> directory over. **The one deliberate divergence:** the ECMP twin is *flow-level*; this study is a
> genuine **discrete-event** simulator (epic §4 `sim/race.py`, event queue + virtual clock) because
> the thesis is a timing race — forged answer vs authoritative reply (epic §5).

## Goal
A root-free, network-free Python package skeleton that can run **one DNS resolution race end to end**:
resolver opens a window with a (placeholder) draw, an authoritative reply and a stub forged answer are
scheduled on a virtual clock, and the engine returns a terminal outcome (`POISONED` / `RESOLVED-LEGIT`).
This plan de-risks nothing exotic — the physics is simple — but it **freezes three things every later
plan inherits**: (1) `config.py` as the single environment source-of-truth, (2) the `Draw` /
`DrawProvenance` / race-outcome **types** and the `draw(txid_bits, port_bits) -> Draw` and race-engine
interfaces (epic §3.5, §4), and (3) the `vectors/race_vectors.json` schema that is the Python source of
truth for the P6 JS↔Python parity gate (epic §3.6). Get these fixed and P2–P6 build on a stable base.

## Context (why this is P1, and what it must not do)
- The epic is an **attack paper about effective entropy** (epic §3.1). P1 builds only the stage: a
  discrete-event engine that races a legit reply against a forged answer under a full `(TXID, port)`
  acceptance rule (epic §5). **No draw sources** (fixed/prng/csprng/qrng), **no SAD-DNS knob**, **no
  real attacker flood**, **no metrics** — those are P2/P3/P4. P1's draw is a static hardcoded
  placeholder and its "attacker" is a one-shot stub, exactly as the ECMP twin's P1 used a static salt.
- **One race core, decided here (epic §3.5, LOCKED).** There is a single engine. The only thing later
  plans vary is the `draw()` source (P2) and the SAD-DNS `k` knob (P2). P1 must not let per-arm or
  per-attacker logic leak into the engine — keep `sim/race.py` source-agnostic and import nothing from
  P2/P3/P4.
- **Frozen interfaces (epic §4, AC-1.3).** `Draw`, `DrawProvenance`, and the race-outcome enum live in
  `testbed/types.py` as frozen dataclasses / `Literal`s and are documented for P2/P3 before P2 starts.
  Serialisation order in any `to_bytes`/JSON form is **load-bearing for JS parity** (P6) — fix it now.
- **Stdlib only for the core.** The engine, types, and config import stdlib only (`heapq`, `os`,
  `dataclasses`, `json`, `hashlib`). `pandas`/`matplotlib` are confined to `analysis/` (P5); `urllib`
  QRNG client is P2; Node is only for the P6 parity gate. Establish `requirements.txt` here.

## Frozen decision D1 — discrete-event, not flow-level *(frozen here; P2–P6 inherit)*
The ECMP twin models steady-state offered load (flow-level) because its thesis is *link saturation*.
This study's thesis is a **timing race between two arrivals** (epic §5): a forged answer is accepted iff
it matches the draw **and** arrives before the authoritative reply. That is inherently event-ordered, so
P1 builds a real discrete-event core: a `heapq` priority queue keyed by virtual time, a monotonic
virtual clock, and `Event` records. Retransmit timers and `q` parallel in-flight windows (birthday
amplification, epic §5) drop in naturally as scheduled events in P3. **Decision: discrete-event engine
in `sim/event_queue.py` + `sim/race.py`.** Recorded here; P3–P6 inherit it verbatim.

## Acceptance criteria (verbatim from epic §9 P1)
- [x] **AC-1.1** A root-free, network-free `sim/` package runs a trivial one-query race end to end.
  `testbed/sim/race.py:20` (`run_race`), driven by `testbed/sim/run_sim.py:24` (`run_one`); verified
  `python3 testbed/sim/run_sim.py --smoke` prints `PASS`.
- [x] **AC-1.2** `config.py` reads `QEAAS_BASE_URL` (default `https://api.qeaas.eu`), `QEAAS_API_KEY`
  (default empty), `PRNG_SEED`, and sweep parameters from the environment only.
  `testbed/config.py:24-25` (`QEAAS_BASE_URL`/`QEAAS_API_KEY`), `testbed/config.py:27` (`PRNG_SEED`),
  `testbed/config.py:30-40` (sweep params); verified via the env-override command in §Manual
  verification step 2.
- [x] **AC-1.3** The `Draw` type and race-engine interfaces are frozen and documented for P2/P3.
  `testbed/types.py:24-35` (`Draw`), `testbed/types.py:19-21` (`DrawProvenance`),
  `testbed/types.py:13` (`RaceOutcome`); verified `FrozenInstanceError` on mutation (§Manual
  verification step 4). Race-engine interface: `testbed/sim/race.py:20` (`run_race` signature).
- **Done when:** `python3 testbed/sim/run_sim.py --smoke` runs a single race to a terminal outcome with
  no network and no root and prints `PASS`; `config.py` values are all env-overridable; `types.py`
  freezes `Draw`/`DrawProvenance`/the outcome enum; and `vectors/race_vectors.json` regenerates
  deterministically from the Python engine.

## File plan
No testbed code exists yet — everything below is **new**. Python 3.12+, PSR-equivalent PEP 8 + strict
typing: `from __future__ import annotations` at the top of **every** module (twin-universal), full type
hints on all public functions, `@dataclass(frozen=True)` for value types, `Literal` for string enums. No
raw network, no root, no `pandas`/`matplotlib` in the core. All paths relative to `DNSPoisonRace/`.

| File | Purpose | Notes |
|------|---------|-------|
| `testbed/__init__.py` | Package marker. | Empty, mirrors twin. |
| `testbed/config.py` | **Single env source-of-truth.** Module-level constants grouped by `# --- Pn ---` banners, `int/float(os.environ.get("KEY","default"))` idiom (twin `config.py:14-95`). P1 block: `TXID_BITS=16`, `PORT_BITS=int(os.environ.get("PORT_BITS","16"))` (OQ-1), `RTT_SECONDS`, `RETRANSMIT_SECONDS`, `PARALLEL_QUERIES=1`, `STATIC_DRAW` placeholder (txid,port). Env block: `QEAAS_BASE_URL` (default `https://api.qeaas.eu`), `QEAAS_API_KEY` (default `""`), `PRNG_SEED=int(...,"0")`. Sweep block (for P5, defined now per AC-1.2): `EFF_BITS_MIN=8`, `EFF_BITS_MAX=32`, `EFF_BITS_STEP=1` (OQ-2), `TRIALS_PER_CELL=10000` (OQ-2), `SEND_RATE_PPS` sweep list (OQ-3), `SAD_DNS_LEAK_BITS=0` (OQ-4). | AC-1.2. API key **env-only**, never committed/printed/logged (Appendix A.3). Later-plan keys are *declared* here as env-overridable constants so `config.py` stays the one place; the values are consumed by P2–P5. |
| `testbed/types.py` | **Frozen shared types.** `@dataclass(frozen=True) class Draw(txid:int, port:int, provenance:DrawProvenance)`; `@dataclass(frozen=True) class DrawProvenance(kind:str, detail:dict[str,str])` **base shape** (P2 fills per-arm payloads: QRNG receipt / PRNG seed+index / CSPRNG note); `RaceOutcome = Literal["poisoned","resolved_legit","window_closed"]`; `@dataclass(frozen=True) class Event(time:float, seq:int, kind:str, payload)` for the queue. Canonical `Draw.to_bytes()` / JSON key order fixed and documented. | AC-1.3. **Load-bearing for JS parity (P6)** — fix serialisation order now. Imports stdlib only so it imports anywhere (P2/P3/P6). |
| `testbed/sim/__init__.py` | Package marker. | Empty. |
| `testbed/sim/event_queue.py` | **The discrete-event core.** `heapq`-backed priority queue keyed by `(time, seq)` (monotonic `seq` counter breaks ties deterministically and avoids comparing `Event` payloads); `push(event)`, `pop() -> Event`, `empty()`; a `Clock` exposing `now: float` advanced only by `pop`. Pure, stdlib only. | D1. Reusable by P3 (retransmit timers, `q` parallel windows) unchanged. |
| `testbed/sim/race.py` | **Race-engine skeleton.** `run_race(draw: Draw, forged_guess, rtt, send_schedule, seed) -> RaceResult` implementing the epic §5 acceptance rule: WINDOW-OPEN → schedule authoritative reply at `rtt`, schedule forged answer(s), first accepted arrival wins; return `RaceOutcome` + timing. P1 uses `config.STATIC_DRAW` and a one-shot stub forged guess (real flood is P3). Source-agnostic — no P2/P3 imports. | AC-1.1. Epic §4 lists this as `P1/P3`: P1 = skeleton + single race; P3 = attacker flood + birthday amplification. `RaceResult` frozen dataclass (`outcome`, `t_outcome`, `forged_packets`). |
| `testbed/sim/run_sim.py` | **CLI entry point / smoke driver.** `#!/usr/bin/env python3`, `argparse` `--smoke` (one race), `--trials N`. Bootstraps repo root on `sys.path`, imports `config`/`types`/`race`, runs the race(s), prints per-run outcome and a final `PASS`/`FAIL`. Ends `raise SystemExit(main())`. "Requires no root, no network." | AC-1.1 (Done-when). Mirrors twin `sim/run_sim.py` structure. |
| `testbed/vectors/gen_race_vectors.py` | Generate `race_vectors.json` from the Python race engine (**source of truth**). Standalone, imports only `types`/`sim/race`/`config`; inserts repo root on `sys.path`; deterministic (seeded). Emits a small set of fully-specified race scenarios. | Epic §4 (`vectors/race_vectors.json` introduced by P1). Seeds the P6 parity gate. `raise SystemExit(main())`. |
| `testbed/vectors/race_vectors.json` | The emitted vectors. Each: `{seed, txid, port, eff_bits, rtt, retransmit, send_schedule, parallel_queries, outcome, forged_packets, t_outcome}`. | Epic §3.6/§4. Python is source-of-truth; P6 JS vendors this and must reproduce every `outcome`. Schema frozen here (see OQ-3). |
| `testbed/README.md` | Runbook: how to run the smoke race, regenerate vectors, and the env vars `config.py` honours. Python version, "no root / no network for the core", `.env` loading note (`set -a && . ./.env && set +a`, Appendix A.3). | The manual-verification runbook. |
| `DNSPoisonRace/requirements.txt` | First code in the project → establish it. `pandas` + `matplotlib` (analysis/P5 only), comment that the core is stdlib-only, the QRNG client is `urllib` (P2, no `requests`), and Node is only for the P6 parity gate (not pip). | Mirrors twin `requirements.txt` intent (no `pyproject.toml`). |

## Manual verification (no automated tests — project directive)
1. **Smoke race (AC-1.1), run first:** `python3 testbed/sim/run_sim.py --smoke` → prints a single
   race's terminal outcome (`resolved_legit` under the placeholder draw, since the stub forged guess is
   a lone packet against a full-entropy draw) and a final `PASS`. Runs with **no network and as a
   non-root user** — confirm by running under an unprivileged shell / with networking down.
2. **Config is env-only (AC-1.2):** `PORT_BITS=11 EFF_BITS_MAX=20 python3 -c "import testbed.config as c;
   print(c.PORT_BITS, c.EFF_BITS_MAX, c.QEAAS_BASE_URL, repr(c.QEAAS_API_KEY))"` → prints `11 20
   https://api.qeaas.eu ''`. Confirms every value reads from the environment with the documented
   defaults and the API key defaults empty and is never hardcoded.
3. **Vectors regenerate deterministically (AC-1.3):** `python3 testbed/vectors/gen_race_vectors.py`
   twice → `git diff testbed/vectors/race_vectors.json` is empty on the second run (byte-identical).
   Proves the engine is deterministic from a seed and the vector schema is stable for the P6 parity gate.
4. **Types are frozen (AC-1.3):** `python3 -c "from testbed.types import Draw; d=Draw(1,2,None)"` then
   attempt `d.txid = 9` → raises `FrozenInstanceError`. Confirms `Draw`/`DrawProvenance` immutability.

## Tech
Pure Python 3.12+, stdlib only for the core (`heapq`, `dataclasses`, `os`, `json`, `hashlib`, `argparse`).
Discrete-event simulation: a `heapq` priority queue over `(virtual_time, seq)` with a monotonic
tie-break counter, a virtual clock advanced only on `pop`. Deterministic from a seed (no wall-clock, no
`random` without a seed). No Mininet/OVS/os-ken/scapy — this study never touches real packets or root
(epic §3.4). `pandas`/`matplotlib` enter only in P5's `analysis/`; Node enters only in P6's parity gate.

## Out of scope
- **Draw sources** (`fixed`/`prng`/`csprng`/`qrng`), the **`sad_dns_leak(port_bits,k)` knob**, the
  **`QRNGClient`**, and real `DrawProvenance` payloads — **P2**. P1's draw is `config.STATIC_DRAW`; P1's
  `DrawProvenance` is the empty base shape.
- The **off-path attacker flood**, retransmit-driven **birthday amplification**, and configurable
  send-rate/RTT sweeps as a *running attack* — **P3**. P1 has a one-shot stub forged answer only.
- The **resolver state machine, cache, the five metrics, and run-tagged CSV / `.record.json`** — **P4**.
- **Experiments, the two headline figures, and replay-JSON export** — **P5**.
- **The web spectacle** and the JS mirror of the race logic — **P6** (P1 only freezes the
  `race_vectors.json` schema the parity gate consumes).

## Risks
- **Non-deterministic event ordering** → equal-time events comparing `Event` payloads would raise or
  reorder unpredictably, breaking JS parity. Mitigation: order the heap by `(time, seq)` with a
  monotonic `seq`; never let the payload participate in comparison. Fixed in `event_queue.py` now.
- **Serialisation drift** between the P1 `race_vectors.json` schema and the P6 JS reader → silent parity
  failures late. Mitigation: freeze the vector field set and key order here and document it in
  `types.py` + `README.md`; P6 vendors the file unchanged.
- **`Draw`/`DrawProvenance` split leaks into the engine** → if `race.py` reaches into provenance detail,
  P2's four arms can't stay source-agnostic (epic §3.5). Mitigation: `race.py` treats `Draw` as opaque
  `(txid, port)` for acceptance and never inspects `provenance`.
- **Config sprawl** → later-plan constants scattered across modules instead of `config.py`. Mitigation:
  declare all env-overridable knobs (even P2–P5 ones) in `config.py` now; other modules import them.

## Notes for `/plan-feature` (downstream)
- `types.py` is the seed of the epic's frozen `Draw`/`DrawProvenance` (epic §4). P2 fills the per-arm
  provenance payloads and adds `draw_source(kind)`; it must **not** redefine the `Draw` shape.
- `sim/event_queue.py` + `sim/race.py` are the single race core (epic §3.5). P3 adds the attacker flood,
  retransmit timers, and `q` parallel windows **as scheduled events on the existing queue** — no new
  engine.
- Record the **D1 outcome** (discrete-event) is already fixed above; P3–P6 inherit it.

## Post-implementation (2026-07-30)
Built exactly as scoped: `testbed/config.py` (env single-source), `testbed/types.py` (frozen
`Draw`/`DrawProvenance`/`RaceOutcome`/`Event`), `testbed/sim/event_queue.py` (heapq + `Clock`),
`testbed/sim/race.py` (`run_race`/`RaceResult`), `testbed/sim/run_sim.py` (`--smoke`/`--trials`
CLI), `testbed/vectors/gen_race_vectors.py` + `race_vectors.json` (4 seeded scenarios),
`testbed/README.md`, `DNSPoisonRace/requirements.txt`. All four manual-verification steps pass
(smoke `PASS`, env-override output byte-identical to spec, vectors byte-identical on regen,
`FrozenInstanceError` on mutation). No deviations from the plan. Nothing deferred — P2 can start
against `types.py`/`config.py`/`sim/race.py` as frozen.

## Open questions — RESOLVED (2026-07-30, all defaults accepted)
- **OQ-P1.1 — Where do `Draw` / `DrawProvenance` live? RESOLVED:** define both frozen dataclasses in
  P1 `testbed/types.py` (the *shape*); `DrawProvenance.detail` is an empty `dict` in P1. P2 introduces
  the `draw_source` factory that *produces* them and fills the per-arm detail. Mirrors the twin
  (`FiveTuple` in P1 `types.py`, salt provenance in P2 `salt/sources.py`). Binds P1 (`types.py`), P2.
- **OQ-P1.2 — Virtual-clock unit. RESOLVED:** `float` seconds; `RTT_SECONDS`/`RETRANSMIT_SECONDS`/
  `SEND_RATE_PPS` are real units. Deterministic tie-breaking via the monotonic `seq` counter in
  `event_queue.py`. Binds P1 (`config.py`, `event_queue.py`), P3.
- **OQ-P1.3 — `race_vectors.json` field set. RESOLVED:** `{seed, txid, port, eff_bits, rtt, retransmit,
  send_schedule, parallel_queries, outcome, forged_packets, t_outcome}`. Schema frozen here; P6 vendors
  it unchanged. Binds P1 (`gen_race_vectors.py`), P6 (parity gate).
- **OQ-P1.4 — Plan-file naming. RESOLVED:** `plans/plan-1-testbed-scaffolding.md` (matches epic §2's
  table and the twin), not the generic `tasks/plans/feature-<num>-<slug>.md` — no issue tracker. On
  record; no action.
