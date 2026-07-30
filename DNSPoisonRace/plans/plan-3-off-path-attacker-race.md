# Plan 3 — Off-path attacker & poison race

**Epic:** [DNS Poison Race](../epic-dns-poison-race.md) · **Source P3** · **Priority:** `[MUST]`
**Status:** Complete (2026-07-30, implemented and manually verified) · **Depends on:** P1 (engine, types, config), P2 (draw sources, `sad_dns`) · **Gates:** P4

> Pick up with `/plan-feature plans/plan-3-off-path-attacker-race.md`. Read epic §3.1 (attack-paper —
> this plan makes the race real), §3.4 (simulated is sufficient — no packets, no root), §3.5 (one race
> core / frozen `draw()` interface P3 imports and never re-implements), §3.6 (offline gates, no automated
> tests), §4 (shared artefacts — `sim/race.py` is co-owned by **P1/P3**; `vectors/race_vectors.json`
> schema is frozen by P1), §5 (the resolver race state machine this plan animates), §6 (threat model —
> off-path attacker), §9 P3 brief first.
> **No GitHub issue** — this project plans from the epic + source doc (`plans/viz-3-dns-poison-race.md`),
> not from a tracker. ACs below are quoted verbatim from epic §9 P3. **No automated tests** (project
> directive) — verification is the offline `attack_check.py` gate in §Manual verification.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/testbed/attacker/`
> (`collision.py`, `knowledge.py`, `attack.py`, `run_attack.py`, `collision_check.py`) — this plan
> mirrors that package's shape: a **dependency-free attacker package** (stdlib only, no scapy, no root),
> a single `run_*` orchestrator, a CLI runner, and a standalone `*_check.py` correctness gate.
> **The deliberate divergences from the twin:** the twin's attacker crafts *real packets* (scapy) that
> land on an ECMP link by *mathematical placement*; this study's attacker is **off-path** (epic §6) — it
> cannot observe the resolver's outbound draw, so it **guesses** `(TXID, port)` and **races** the
> authoritative reply on the **discrete-event queue** P1 froze (epic §5). There is **no network layer
> here at all** (epic §3.4) — the "flood" is scheduled events on the virtual clock, not packets.

## Goal
Turn the P1 skeleton race into a **real off-path poison race**: an attacker that floods forged answers
guessing `(TXID, port)` at a configurable send-rate while the authoritative reply flies back, with
**retransmit timers** (a fresh draw each retransmit round) and **birthday amplification** via `q`
parallel in-flight queries (epic §5). This is the plan where the epic's headline mechanism becomes
**runnable end to end** with the real P2 draws. P3 delivers:

1. the **off-path guess model** (`attacker/guessing.py`) — the attacker searches the *effective*
   guess-space (size `2^effective_bits`, with SAD-DNS-leaked bits pinned, per P2's `sad_dns`), drawing
   distinct guesses in a seeded, **JS-portable** pseudo-random order;
2. the **flood builder** (`attacker/flood.py`) — turns a send-rate + window into scheduled forged-send
   times, each assigned a guess;
3. the **engine extension** (`sim/race.py` `run_attack_race`) — schedules `q` parallel windows,
   authoritative replies, retransmit-driven fresh draws, and the forged flood as events on the frozen
   `EventQueue`, applying the epic §5 acceptance rule;
4. the **orchestrator** (`attacker/attack.py` `run_poison_race`) — the single entry point P4 calls per
   sweep cell: mint a draw via P2's `draw_source(kind)`, apply the SAD-DNS `k` knob, build the flood, run
   the race, return a structured `PoisonRaceResult` carrying the outcome, timing, forged-packet count,
   effective guess-space, and the draw's `DrawProvenance` (M5);
5. the **CLI runner** (`attacker/run_attack.py`) and the **offline gate** (`attacker/attack_check.py`);
6. **real flood scenarios** appended to `vectors/race_vectors.json` (via `gen_race_vectors.py`) that fill
   the P1-reserved `send_schedule` / `parallel_queries` / `retransmit` fields with genuine attack data —
   the P6 JS↔Python parity gate's source of truth (AC-3.4).

P3 does **not** aggregate metrics or write the run-tagged CSV / `.record.json` — that is **P4**. P3
emits one `PoisonRaceResult` per race; P4 loops it over cells and computes M1–M5.

## Context — what P1/P2 froze that P3 imports (never re-implements)
P1 and P2 are **Complete**. P3 consumes these exact artefacts and leaves the frozen ones untouched
(epic §3.5 — the attacker must race against the *real* draw and the *real* engine, or every experiment
is silently invalid):

- `testbed/sim/event_queue.py` — `EventQueue.push(time, kind, payload)` / `pop() -> Event` / `empty()`
  and its `Clock`. **The single discrete-event core (epic §3.5, D1).** P3 schedules every window,
  authoritative reply, retransmit, and forged send as events on this queue — **no new engine, no
  wall-clock, no `sleep`.** The `(time, seq)` ordering and monotonic `seq` tie-break stay exactly as P1
  fixed them (load-bearing for JS parity).
- `testbed/sim/race.py` — `run_race(draw, forged_guess, rtt, send_schedule, seed) -> RaceResult` and
  `RaceResult(outcome, t_outcome, forged_packets)`. **P1's single-guess skeleton stays untouched** (still
  used by the smoke driver and P1's 4 non-flood vectors). P3 **adds** `run_attack_race(...)` and
  `AttackRaceResult` alongside it (epic §4: `sim/race.py` is co-owned by P1/P3), and factors the epic §5
  acceptance test into a shared `_accepts(guess, draw)` helper so the two paths cannot drift.
- `testbed/types.py` — `Draw(txid, port, provenance)`, `DrawProvenance(kind, detail)`, `RaceOutcome`
  (`"poisoned"|"resolved_legit"|"window_closed"`), `Event`. **Frozen (AC-1.3).** P3 emits and races
  `Draw` instances; it does **not** redefine the shape or add fields. `Draw.to_bytes()`/`to_dict()` key
  order is untouched.
- `testbed/draw/sources.py` — `draw_source(kind, *, txid_bits, port_bits) -> Draw` over
  `DrawKind = "fixed"|"prng"|"csprng"|"qrng"`. **P3's orchestrator mints the true draw through this
  factory** — one draw per outbound query and one fresh draw per retransmit round. The **module-level
  weak-PRNG state** (`_prng_rng`/`_prng_seed`/`_prng_draw_index`) means successive `prng` draws in one
  process share sequence state (documented in `sources.py`) — P3 relies on this for the `prng` arm's
  sequential retransmit draws and must **not** assume independent `prng` draws without reseeding.
- `testbed/draw/sad_dns.py` — `sad_dns_leak(port_bits, k) -> int` and
  `effective_bits(txid_bits, port_bits, k) -> int`. **The single source of the attacker's guess-space
  size.** P3 imports `effective_bits` to size the search; it never re-derives the entropy-reduction math
  (epic §3.5, P2 note).
- `testbed/config.py` — `TXID_BITS`, `PORT_BITS`, `RTT_SECONDS`, `RETRANSMIT_SECONDS`,
  `PARALLEL_QUERIES`, `SEND_RATE_PPS`, `SAD_DNS_LEAK_BITS`, `PRNG_SEED`, `FIXED_PORT`. **Already declared
  (P1/P2).** P3 adds only the small `# --- P3 ---` block below; it does not change existing constants.

## Hard constraint — race the real draw and the real engine
`run_poison_race` mints its draw through `draw_source(kind)` and sizes the search through
`effective_bits(...)`; the race runs on the frozen `EventQueue` with the epic §5 acceptance rule. Never
re-implement the draw, the entropy-reduction knob, or the event core inside the attacker — a drift there
makes the attack look like it beats a draw the resolver never made, silently invalidating P4/P5's M1–M4.

## The off-path model (why this attacker guesses, not places)
The twin's attacker is *on-path enough* to place flows by computing the ECMP hash. This attacker is
**off-path** (epic §6): it cannot see the resolver's outbound `(TXID, port)`, so it **sprays guesses**
and hopes one matches a still-open window before the authoritative reply closes it. Three facts drive
the design:

- **Acceptance is a race, not just a match (epic §5).** A forged answer poisons iff its guess equals an
  open window's draw **and** it arrives strictly before that window's authoritative reply. A correct
  guess that arrives after the reply loses.
- **SAD-DNS shrinks the space the attacker must cover, not the draw.** With `k` leaked port bits the
  attacker fixes those bits and searches only `effective_bits = txid_bits + (port_bits − k)`. This is the
  P2 `sad_dns` knob consumed here (epic §3.5, OQ-4); the true draw is unchanged.
- **Birthday amplification is `q` targets in one space (epic §5).** `q` parallel in-flight queries each
  open an independent window with its own draw; one forged spray covers all of them, so per-round success
  rises roughly like `q × coverage`. Retransmit adds *more* fresh targets over time (Kaminsky's
  amplification). This is M3.

### Effective-index encoding (the guess-space the attacker actually searches)
The attacker searches at the **effective-index** level: an integer in `[0, 2^effective_bits)` that encodes
exactly the `(TXID, port)` bits still unknown to the attacker (the leaked `k` port bits are pinned to the
draw's true values, since SAD-DNS hands them over). `effective_index(draw, port_bits, k)` maps a true
`Draw` to its target index; a guess index equal to the target index is **by construction** equivalent to
the guessed `(TXID, port)` matching the draw on every searched bit — i.e. the epic §5 / AC-3.1 acceptance
rule, made tractable and JS-reproducible. `run_attack_race` compares indices (`_accepts`); the vector
schema still records the concrete `txid`/`port` of the target for display and cross-checking. See OQ-P3.1.

## Acceptance criteria (verbatim from epic §9 P3)
- **AC-3.1** A forged answer is accepted iff its guessed `(TXID, port)` equals the draw and it arrives
  before the authoritative reply (§5 acceptance rule).
  **Covered by:** `testbed/sim/race.py:60-64` (`_accepts`) and `testbed/sim/race.py:130-135`
  (`run_attack_race` forged-event handling — poisons only when guess index equals an open window's
  target index **and** `event.time < window_t_auth[wid]`). `testbed/attacker/attack_check.py` check (a)
  forces a guess equal to the draw and asserts `poisoned` at the send time; check (b) forces every guess
  unequal and asserts `resolved_legit`, plus a direct `_accepts` timing assertion (a correct guess
  arriving after the reply loses). Verified: `python3 testbed/attacker/attack_check.py` -> 8/8 PASS.
- **AC-3.2** Attacker send-rate, authoritative RTT, and retransmit timer are configurable.
  **Covered by:** `testbed/attacker/flood.py` (`attack_window_span`, `forged_send_times`);
  `testbed/attacker/attack.py:39-50` (`run_poison_race` params `send_rate_pps`/`rtt`/`retransmit`
  defaulting to `config.ATTACKER_SEND_RATE_PPS`/`config.RTT_SECONDS`/`config.RETRANSMIT_SECONDS`).
  `attack_check.py` check (c) asserts poison count non-decreasing in send-rate (verified: low=0, high=12
  over 500 trials); check (d) deterministically shows a retransmit round turning `resolved_legit` into
  `poisoned`, never the reverse. Manually verified: `run_attack.py --port-bits 16 -k 16` (eff_bits=16) ->
  poison_rate=0.0300, vs `-k 0` (eff_bits=32) -> poison_rate=0.0000, same send-rate — the cliff direction.
- **AC-3.3** Parallel in-flight queries multiply per-round success (birthday amplification, M3).
  **Covered by:** `testbed/sim/race.py:105-110` (`run_attack_race` opens one window per `(query, round)`
  pair, all sharing the single forged flood). `attack_check.py` check (e) asserts empirical success at
  `q=8` exceeds `q=1` at a fixed cell (verified: q1=2, q8=8 over 500 trials). Manually verified:
  `run_attack.py --parallel 1` -> poison_rate=0.0333 (10/300) vs `--parallel 8` ->
  poison_rate=0.2467 (74/300), same eff_bits/send-rate — M3 factor ≈ 7.4.
- **AC-3.4** Race outcomes are reproducible from a seed and emit the vectors P6/parity consume.
  **Covered by:** `testbed/attacker/portable_prng.py` (`splitmix64`/`bounded`) — the sole source of
  reproducible randomness (guess order, RTT jitter, parity-vector targets); no `random.Random`/
  `os.urandom` in that path. `testbed/vectors/gen_race_vectors.py` (`FLOOD_SCENARIOS` + `_flood_vector`
  adapter, lines 26-42/45-124) appends 3 flood scenarios filling the P1-frozen `send_schedule` /
  `parallel_queries` / `retransmit` fields (7 vectors total). `attack_check.py` check (f) asserts two
  same-seed `run_poison_race("prng", ...)` calls (module state reset) are byte-identical, and that
  `generate()` is idempotent. Manually verified: `run_attack.py --kind csprng --seed 123` run twice ->
  byte-identical output; `gen_race_vectors.py` run twice -> `race_vectors.json` byte-identical.
- **Done when:** `python3 testbed/attacker/attack_check.py` runs all six checks with **no network and no
  root** and prints a final `PASS`; `python3 testbed/attacker/run_attack.py --kind csprng --trials 1000`
  reports a plausible poison rate that rises as `--eff-bits` falls, `--send-rate` rises, and `--parallel`
  rises; and `gen_race_vectors.py` regenerates `race_vectors.json` deterministically with the new flood
  scenarios present.

## The race, as events on the frozen queue (epic §5)
`run_attack_race` builds one `EventQueue` and schedules, for each of the `q` parallel queries:

- a **window-open** at `t = 0` carrying a fresh `Draw` (its target index);
- an **authoritative** event at `t = rtt` (jittered per query via the portable PRNG so replies don't all
  land on the same tick — `rtt ± jitter`, `seed`-derived, deterministic);
- a **retransmit** event at each `n × retransmit` while the window is still open and the authoritative
  reply has not yet arrived, which **opens a new window with a fresh draw** (a fresh target index) —
  Kaminsky amplification (OQ-P3.4);

and, across the whole open span, the **forged flood**: `floor(send_rate_pps × span)` forged-send events at
evenly spaced times, each carrying the next guess index from the seeded `GuessStream` (distinct guesses,
no replacement within a search round — OQ-P3.2).

The engine pops events in `(time, seq)` order and applies `_accepts`:

- **forged** at time `t`, guess `g`: poison iff any currently-open window `w` has `target_index[w] == g`
  and `t < t_authoritative[w]`; return `AttackRaceResult("poisoned", t, forged_packets, poisoned_window)`.
- **authoritative** for window `w`: mark `w` closed. When **all** `q` windows have closed with no poison,
  return `("resolved_legit", t_last_auth, forged_packets, None)`.
- **retransmit** for window `w`: if `w` still open, open a new window `w'` with a fresh draw (extends the
  attack surface); schedule `w'`'s authoritative + next retransmit.

`window_closed` is returned only if the flood and all timers drain without any authoritative arrival
(defensive; not expected under normal params).

## Interfaces exposed to P4/P5 (freeze — downstream imports, does not redefine)
- `run_poison_race(kind, *, txid_bits, port_bits, k, send_rate_pps, rtt, retransmit, parallel_queries,
  seed) -> PoisonRaceResult` — the single entry point P4 calls per sweep cell.
- `PoisonRaceResult` (frozen dataclass):
  `{kind, outcome, t_outcome, forged_packets, effective_bits, parallel_queries, send_rate_pps, k,
  poisoned_window, provenance}` where `provenance` is the draw's `DrawProvenance` (M5 — carries the QRNG
  receipt for `kind="qrng"`, the PRNG seed+index for `prng`, the source note for `csprng`). P3 **does not**
  own any CSV; P4's collectors read these fields into the run-tagged CSV + `.record.json` (epic §4).
- `sim/race.py` `run_attack_race(...)` / `AttackRaceResult` — the engine P4 may call directly for
  fine-grained instrumentation, and the function the P6 JS mirror must reproduce.
- `attacker/portable_prng.py` `splitmix64(state) -> (value, next_state)` — the **parity contract**: P6's
  JS vendors this algorithm verbatim (BigInt) to reproduce guess order and vector targets.

## File plan
All paths relative to `DNSPoisonRace/`. New unless marked **edit**. Python 3.12+,
`from __future__ import annotations` at the top of **every** module, full type hints on all public
functions, `@dataclass(frozen=True)` for value/result types, `Literal` for string enums. **Stdlib only**
(`dataclasses`, `typing`, `argparse`, `os`, `sys`, `json`, `pathlib`) — **no scapy, no sockets, no root,
no network** (epic §3.4); `pandas`/`matplotlib` stay out (P5's `analysis/`). The attacker package is
dependency-free so `attack_check.py` runs in any environment (mirrors the twin's dependency-free
`collision.py`/`knowledge.py`).

| File | Purpose | AC | Notes |
|------|---------|----|-------|
| `testbed/attacker/__init__.py` | Package marker; re-export `run_poison_race`, `PoisonRaceResult`. | — | New package, sibling of `testbed/draw/` and `testbed/sim/`. |
| `testbed/attacker/portable_prng.py` | **JS-portable deterministic PRNG.** `splitmix64(state: int) -> tuple[int, int]` (returns `(value, next_state)`, 64-bit masked) and `bounded(state, n) -> tuple[int, int]` (unbiased index in `[0, n)`). Pure, stdlib only, no floats in the core step. | AC-3.4 | The parity contract (OQ-P3.3). Chosen because it is a handful of integer ops trivially mirrored in JS with `BigInt`. Documented as "P6 vendors this verbatim". |
| `testbed/attacker/guessing.py` | **Off-path guess model.** `effective_index(draw: Draw, port_bits: int, k: int) -> int` (encodes the searched `(TXID, port)` bits, leaked `k` port bits pinned); `guess_space_size(txid_bits, port_bits, k) -> int` = `2 ** effective_bits(...)` (imports P2's `effective_bits`); `GuessStream(space_size, state)` yielding **distinct** effective-index guesses in seeded portable-PRNG order (no replacement within a round via a lazily-materialised shuffle when `space_size` is small, or rejection sampling with a seen-set bounded by the packet budget when large — OQ-P3.2). | AC-3.1, AC-3.4 | Imports `testbed.draw.sad_dns.effective_bits` and `testbed.types.Draw` — never re-derives entropy math. |
| `testbed/attacker/flood.py` | **Flood builder.** `forged_send_times(span: float, send_rate_pps: int) -> list[float]` — `floor(span × send_rate_pps)` evenly spaced times in `(0, span)`; pairs each with the next `GuessStream` guess in `run_attack_race`. `attack_window_span(rtt, retransmit, parallel_queries) -> float` — how long the flood runs given timers. | AC-3.2 | Pure timing math; no events here (the engine schedules). |
| `testbed/sim/race.py` | **edit** — add `run_attack_race(windows_spec, guess_stream, send_rate_pps, rtt, retransmit, parallel_queries, seed) -> AttackRaceResult` and `@dataclass(frozen=True) AttackRaceResult(outcome, t_outcome, forged_packets, poisoned_window)`. **Factor the epic §5 acceptance test into `_accepts(guess_index, target_index, event_time, t_authoritative) -> bool`** used by the new path (and documented as the canonical rule P1's `run_race` also embodies). P1's `run_race`/`RaceResult` stay **unchanged**. | AC-3.1, AC-3.3 | Engine only — source-agnostic, takes draws/guesses as data (epic §3.5). No `draw`/`attacker` imports beyond `types`. |
| `testbed/attacker/attack.py` | **Orchestrator.** `run_poison_race(kind, *, txid_bits=config.TXID_BITS, port_bits=config.PORT_BITS, k=config.SAD_DNS_LEAK_BITS, send_rate_pps=config.ATTACKER_SEND_RATE_PPS, rtt=config.RTT_SECONDS, retransmit=config.RETRANSMIT_SECONDS, parallel_queries=config.PARALLEL_QUERIES, seed) -> PoisonRaceResult`: mint `q` (+retransmit) draws via `draw_source(kind)`, compute each target index via `effective_index`, build the `GuessStream` + flood, run `run_attack_race`, wrap the result with `effective_bits`, `send_rate_pps`, `k`, and the **first window's** `DrawProvenance` (M5). `@dataclass(frozen=True) PoisonRaceResult(...)`. | AC-3.1–3.4 | The one place `draw_source` + `sad_dns` + engine meet. Carries provenance for P4's M5. |
| `testbed/attacker/run_attack.py` | **CLI runner.** `#!/usr/bin/env python3`, argparse `--kind {fixed,prng,csprng,qrng}`, `--eff-bits`/`--port-bits`/`-k`, `--send-rate`, `--rtt`, `--retransmit`, `--parallel`, `--trials N`, `--seed`. Bootstraps repo root on `sys.path`. Runs `--trials` races, prints per-trial outcome and a final poison-rate summary + `PASS`/`FAIL`. Root-free, network-free (network only if `--kind qrng` and `QEAAS_API_KEY` set). Ends `raise SystemExit(main())`. | AC-3.2, AC-3.3 | Mirrors P1's `run_sim.py` and the twin's `run_attack.py` structure. |
| `testbed/attacker/attack_check.py` | **Offline correctness gate** (project directive — no `pytest`). Standalone; asserts (a) a forced-equal guess poisons at its send time; (b) a forced-unequal guess never poisons (and a correct guess arriving after `rtt` loses — timing); (c) poison count monotonic non-decreasing in send-rate; (d) a retransmit round opens an extra fresh-draw window; (e) success rate at `q>1` exceeds `q=1` at a fixed cell (M3 amplification `>1`); (f) two same-seed `run_poison_race` calls are byte-identical and `gen_race_vectors.py` is idempotent. Prints `PASS`/`FAIL` per check + a final summary. `raise SystemExit(main())`. | AC-3.1–3.4 (Done-when) | Root-free, network-free (no `qrng` in the gate — uses `csprng`/`fixed`/`prng`). Mirrors twin `collision_check.py`. |
| `testbed/vectors/gen_race_vectors.py` | **edit** — append a `FLOOD_SCENARIOS` block driven through `run_attack_race` (via a thin adapter that derives targets + guesses from the portable PRNG so JS reproduces), emitting the **same P1-frozen schema** with real `send_schedule` (the flood times), real `parallel_queries` (`q`), real `retransmit`, and the flood `outcome`/`forged_packets`/`t_outcome`. P1's 4 non-flood scenarios stay unchanged and first. | AC-3.4 | **Schema is frozen (P1 OQ-P1.3)** — no new fields; the flood's determinism is carried by `seed` + the recorded times, reproduced in JS via `portable_prng`. |
| `testbed/config.py` | **edit** — add a `# --- P3: off-path attacker ---` block: `ATTACKER_SEND_RATE_PPS = int(os.environ.get("ATTACKER_SEND_RATE_PPS", "10000"))` (single-race/CLI default, distinct from P5's `SEND_RATE_PPS` sweep list), `RTT_JITTER_FRAC = float(os.environ.get("RTT_JITTER_FRAC", "0.1"))` (authoritative-arrival jitter as a fraction of `rtt`), `MAX_RETRANSMITS = int(os.environ.get("MAX_RETRANSMITS", "3"))` (bound on retransmit rounds per query). | AC-3.2 | Additive only; no existing constant changes (`RTT_SECONDS`/`RETRANSMIT_SECONDS`/`PARALLEL_QUERIES`/`SAD_DNS_LEAK_BITS` already declared P1/P2). |
| `testbed/README.md` | **edit** — append a "Running the poison race" section: `attack_check.py`, `run_attack.py` flags, the four `--kind` arms, the off-path/no-root/no-network note, and the portable-PRNG parity contract for P6. | — | Extends the P1/P2 runbook. |

## Manual verification (no automated tests — project directive)
Run from `DNSPoisonRace/`. All steps need **no root and no network** (step 6 is opt-in and touches the
QRNG endpoint only).

1. **Offline gate (AC-3.1–3.4), run first:** `python3 testbed/attacker/attack_check.py` → prints per-check
   `PASS` for acceptance-rule (a/b), send-rate monotonicity (c), retransmit-adds-window (d), birthday
   amplification (e), and seed reproducibility + vector idempotence (f), then a final `PASS`. No network,
   non-root.
2. **Cliff direction (AC-3.2):** `python3 testbed/attacker/run_attack.py --kind csprng --eff-bits 12
   --send-rate 100000 --trials 2000` then again with `--eff-bits 28` → the 12-bit run reports a **much
   higher** poison rate than the 28-bit run (the entropy cliff, in miniature — the full sweep is P5).
3. **Send-rate axis (AC-3.2):** same cell, `--send-rate 1000` vs `--send-rate 100000` → poison rate is
   non-decreasing with send-rate.
4. **Birthday amplification (AC-3.3):** `--parallel 1` vs `--parallel 8` at a fixed
   `--eff-bits`/`--send-rate` → the `--parallel 8` poison rate is materially higher (M3 factor `> 1`).
5. **Seed reproducibility (AC-3.4):** `python3 testbed/attacker/run_attack.py --kind csprng --trials 5
   --seed 123` run twice → byte-identical per-trial output both times.
6. **Vectors regenerate deterministically (AC-3.4):** `python3 testbed/vectors/gen_race_vectors.py` twice
   → `git diff testbed/vectors/race_vectors.json` empty on the second run; the file now contains the P1
   non-flood scenarios **and** the new flood scenarios with populated `send_schedule` / `parallel_queries`
   / `retransmit`.
7. **QRNG provenance carried (M5, opt-in, AC-3.1 path):** `set -a && . ./.env && set +a && python3
   testbed/attacker/run_attack.py --kind qrng --trials 1 --seed 1` → the printed `PoisonRaceResult`
   provenance carries the Q-EaaS `receipt` (subject to the live Q-EaaS outage flagged in P2's
   Post-implementation — a graceful `FAIL`/skip, not a crash, when the endpoint 404s).

## Tech
Pure Python 3.12+, **stdlib only** (`dataclasses`, `typing`, `argparse`, `os`, `sys`, `json`, `pathlib`).
Discrete-event race on P1's frozen `EventQueue` — a `heapq` over `(virtual_time, seq)`, virtual clock,
**no wall-clock, no `sleep`, no `random`/`os.urandom` in the reproducible path** (guess order and
parity-vector targets come from the portable splitmix64 seeded by `seed`; the true sweep draws come from
P2's `draw_source`). **No scapy, no sockets, no Mininet, no root, no real packets** — the "flood" is
scheduled events (epic §3.4). `pandas`/`matplotlib` enter only in P5; Node only in P6's parity gate.

## Out of scope
- **The five metrics, their aggregation, and the run-tagged CSV / `.record.json`** — **P4**. P3 emits one
  `PoisonRaceResult` per race; it does not compute M1–M5 curves or write CSV.
- **The experiment matrix, the two headline figures, and the replay-JSON export** — **P5**. P3 provides
  the per-cell primitive P5 sweeps.
- **The web spectacle and the JS mirror of `run_attack_race`** — **P6** (P3 only freezes the
  `portable_prng` parity contract and appends the flood vectors P6 reproduces).
- **The IEEE paper** — **P7**.
- **Any change to `sim/event_queue.py`, `types.py`, `draw/sources.py`, `draw/sad_dns.py`, or P1's
  `run_race`/`RaceResult`** — frozen upstream (epic §3.5); changing them breaks every downstream plan.
- **New Q-EaaS quantum-computer runs** — none. P3 consumes P2's client only when `--kind qrng` is asked
  for (Appendix A.2).
- **On-path attackers, DNSSEC, query-name 0x20, DoT/DoH, multi-upstream** — out of the study's scope
  (epic §6); they are P7 threats-to-validity, not modelled here.

## Risks
- **Attacker/engine drift from the real draw (epic §3.5).** If `run_poison_race` guessed against a
  re-implemented draw or re-derived the entropy-reduction math, M1–M4 would measure a fiction. Mitigation:
  mint via `draw_source`, size via `effective_bits`, race on `EventQueue`; `attack_check.py` (a) asserts a
  guess *equal to the minted draw* poisons.
- **Two acceptance rules diverging** — a second acceptance implementation in `run_attack_race` could drift
  from P1's `run_race`, breaking JS parity late. Mitigation: factor `_accepts` and document it as the one
  canonical epic §5 rule both paths obey; the flood vectors (which P6 must reproduce) exercise it.
- **Non-portable randomness breaking parity (AC-3.4).** `random.Random`/`os.urandom` in the reproducible
  path cannot be mirrored in JS, so P6's parity gate would fail. Mitigation: **all** reproducible
  randomness (guess order + vector targets) flows through `portable_prng.splitmix64`; the true sweep draws
  (P2 sources, non-portable by design) are used only in P4/P5's *aggregate* statistics, never in a vector
  P6 must reproduce.
- **Guess-space blow-up.** At `effective_bits = 32` a full no-replacement shuffle is `2^32` entries —
  intractable. Mitigation: the flood only ever sends `floor(send_rate × span)` packets (thousands, not
  billions); `GuessStream` materialises **only** that many distinct guesses (rejection sampling with a
  bounded seen-set), never the whole space (OQ-P3.2). `attack_check.py` runs at small `eff-bits` where the
  behaviour is checkable.
- **`prng` shared-state surprises.** P2's `prng` arm shares module-level sequence state across draws in one
  process; a retransmit round's "fresh" `prng` draw is the *next* predictable value, not independent.
  Mitigation: this is **correct and intended** for the `prng` arm (its retransmit draws *are* predictable —
  the weak-source story); documented in `attack.py`, and flagged for P5/P7 framing (the weak-PRNG
  retransmit subtlety, twin OQ-2 analogue).

## Notes for `/plan-feature` and `/implement-feature` (downstream)
- Import `draw_source`, `effective_bits`, `EventQueue`, `Draw`/`DrawProvenance`/`RaceOutcome` from
  `testbed` **verbatim** — the attacker must race the real draw on the real engine (epic §3.5).
- Keep the whole `attacker/` package **dependency-free** (stdlib only, no scapy/root/network) so
  `attack_check.py` runs anywhere, exactly as P2's `draw_check.py` and the twin's `collision_check.py` do.
- `run_poison_race(...) -> PoisonRaceResult` and its field set are **frozen for P4** (P4 reads them into
  the CSV + `.record.json` without reshaping) — do not change the signature or drop `provenance` (M5).
- `portable_prng.splitmix64` is the **parity contract for P6** — its exact integer steps are what the JS
  mirror vendors; treat it as load-bearing, not a helper.
- The `race_vectors.json` **schema stays frozen (P1 OQ-P1.3)** — P3 fills the reserved fields, it does not
  add columns.

## Open questions — RESOLVED (2026-07-30, all defaults accepted)
- [x] **OQ-P3.1 — Acceptance granularity: full `(TXID, port)` tuple vs effective-index. RESOLVED (default):** compare at the **effective-index** level — an integer in `[0, 2^effective_bits)`
  encoding the searched bits with the SAD-DNS-leaked `k` port bits pinned to the draw's true values. This
  is provably equivalent to the literal AC-3.1 `(TXID, port)` match on every searched bit, and is the only
  formulation that keeps SAD-DNS entropy-reduction, birthday amplification, and JS parity all tractable.
  The vector schema still records the concrete target `txid`/`port` for display/cross-check. *Binds
  `sim/race.py`, `guessing.py`, `gen_race_vectors.py`.*
- [x] **OQ-P3.2 — Attacker guessing strategy: no-replacement vs with-replacement. RESOLVED (default):** **no replacement within a search round** (the attacker doesn't waste a spray on a
  guess it already tried), reset per retransmit round; realised by rejection sampling with a seen-set
  bounded by the packet budget (never materialising the whole space). This gives the clean coverage /
  birthday math the thesis wants. The "real UDP floods can repeat" caveat is a P7 threat-to-validity.
  *Binds `guessing.py`, `flood.py`.*
- [x] **OQ-P3.3 — Portable PRNG choice for the parity path. RESOLVED (default):** **splitmix64** (a handful of 64-bit integer ops, trivially mirrored in JS with
  `BigInt`), seeded by `seed`, used for guess order, `rtt` jitter, and parity-vector target indices. Not
  Python's `random`/`os.urandom` (unreproducible in JS). *Binds `portable_prng.py`, `sim/race.py` vector
  path, P6.*
- [x] **OQ-P3.4 — Retransmit as birthday amplification. RESOLVED (default):** **yes** — each retransmit round (up to `config.MAX_RETRANSMITS`) opens a **fresh
  draw** window that the ongoing flood can also hit, modelling the resolver resending with a new source
  port/TXID (Kaminsky amplification); the original window's authoritative reply still races. For the `prng`
  arm the "fresh" draw is the *next predictable* value (Risk above) — correct and intended, flagged for
  P5/P7. *Binds `sim/race.py`, `attack.py`, `config.MAX_RETRANSMITS`.*
- [x] **OQ-P3.5 — Where the flood engine lives. RESOLVED (default):** `run_attack_race` goes in **`sim/race.py`** (epic §4 co-owns it P1/P3); the
  `attacker/` package only *builds its inputs* (guesses, flood times, draws) and *wraps its output*
  (`PoisonRaceResult`). Keeps the engine source-agnostic (epic §3.5). *On record; no scope change.*

## Post-implementation (2026-07-30)

Built exactly the file plan's package: `attacker/portable_prng.py` (splitmix64/`bounded`),
`attacker/guessing.py` (`effective_index`, `guess_space_size`, `GuessStream`), `attacker/flood.py`
(pure timing math), `sim/race.py` additions (`_accepts`, `AttackRaceResult`, `run_attack_race`),
`attacker/attack.py` (`run_poison_race`/`PoisonRaceResult`), `attacker/run_attack.py` (CLI),
`attacker/attack_check.py` (offline gate, 8 checks across the 6 ACs), and `vectors/gen_race_vectors.py`
edits (3 new `FLOOD_SCENARIOS`, 7 vectors total, byte-idempotent). `config.py` got the `# --- P3 ---`
block (`ATTACKER_SEND_RATE_PPS`, `RTT_JITTER_FRAC`, `MAX_RETRANSMITS`) exactly as specced.

**Design decisions not fully spelled out in the plan, resolved during implementation:**
- **`run_attack_race`'s `rtt`/`retransmit`/`parallel_queries`/`seed` params are accepted but unused**
  (`del`'d), mirroring P1's `run_race` unused `seed`. All timing (window opens, jitter, authoritative
  arrivals) is precomputed by `attacker/attack.py` into `windows_spec` before the engine runs, keeping
  `sim/race.py` free of any `attacker`-package import (the plan's explicit constraint) while still
  honouring the portable-PRNG jitter contract (computed by the caller, which *can* import
  `portable_prng`).
- **Retransmit windows are scheduled unconditionally** at `round_index * retransmit`, not conditioned on
  "is the previous window still open" — simpler, deterministic, and matches OQ-P3.4's resolved default;
  the conditional-cancel nuance is a real-resolver detail out of scope per epic §3.4's simulated-is-
  sufficient caveat.
- **`resolved_legit` requires *every* scheduled window (including all retransmit rounds) to close**, not
  just the original — a minor simplification flagged here for P4/P5/P7 framing.

**Performance note for P4/P5 (sweep authors):** the engine pre-builds the entire forged flood as heap
entries before running (`forged_count = int(max_t_authoritative * send_rate_pps)`). At default
`RETRANSMIT_SECONDS=0.5`/`MAX_RETRANSMITS=3`, `max_t_authoritative` reaches ~1.5s, so at
`send_rate_pps=100000` a single trial pushes ~150k heap events; ~2000 such trials is minutes, not
seconds, in pure Python. P4/P5's sweeps (`TRIALS_PER_CELL=10000` default) should budget accordingly, or
prefer smaller `RETRANSMIT_SECONDS`/`MAX_RETRANSMITS` for the high-send-rate/high-trial cells. This did
not block P3's own verification (kept trial counts to 300-2000 with time-boxed parameters throughout).

**Manual verification results (all steps from §Manual verification above):**
1. `attack_check.py` — 8/8 checks PASS.
2. Cliff direction — eff_bits=16 -> poison_rate=0.0300 (9/300); eff_bits=32 -> 0.0000 (0/300).
3. Send-rate axis — covered by check (c) (low=0, high=12 over 500 trials) and the cliff-direction run
   above (both used a fixed send-rate; the monotonic-in-send-rate property is the offline-gate's job).
4. Birthday amplification — `--parallel 1` -> 0.0333 (10/300); `--parallel 8` -> 0.2467 (74/300).
5. Seed reproducibility — `--kind csprng --seed 123` run twice, byte-identical stdout (5 trials, all
   `resolved_legit` at the default eff_bits=32 — csprng's real (non-reproducible) draw value never
   surfaces in the printed fields unless a poisoning actually occurs, so this held on both runs; the
   *guaranteed* reproducibility path is `kind="prng"` with module-state reset, exercised in check (f)).
6. Vectors regenerate deterministically — `gen_race_vectors.py` run twice, `race_vectors.json`
   byte-identical (7 vectors: 4 P1 non-flood + 3 new flood scenarios).
7. QRNG provenance — not exercised (opt-in, requires live `QEAAS_API_KEY`); left to the developer per
   the plan's note about the live Q-EaaS outage.

No deviations from the frozen P1/P2 interfaces; no new dependencies added.
