# Epic: DNS Poison Race — How Many Entropy Bits Stop a Cache Poisoner?

**Slug:** dns-poison-race
**Plans:** Plan 1–Plan 7 (7 plans)
**Author:** Claude (Opus)
**Date:** 2026-07-30
**Status:** Approved (2026-07-30, all open questions resolved)

> **Source material:** `plans/viz-3-dns-poison-race.md` (the study idea, hypothesis, method,
> metrics, visualization spec, and IEEE short-paper pitch). This epic operationalises that
> pitch into pickup-ready plans; it does not override it. Where the source and this epic
> disagree, the source wins and the conflict is raised in §8.
>
> **Structural twin:** `../TargetedDosColisionsAndRNGAngle/` (the shipped ECMP-collision-DoS
> study). This epic deliberately mirrors that project's layout, its "attack-paper not
> quantum-paper" framing, its offline correctness-gate testing discipline, and its live
> Q-EaaS QRNG wiring. Read `../TargetedDosColisionsAndRNGAngle/epic-ecmp-collision-dos.md`
> alongside this document — every convention here has a working precedent one directory over.
>
> **Authoring convention:** planned with `/plan-epic`, specialised per unit of work with
> `/plan-feature` (the same epic→plan workflow used in `qrng-eaas/claude/`). Per project
> directive there are **no automated test suites** — verification is offline correctness
> gates, a root-free simulator, and a JS↔Python parity check (see §3.6 and the per-plan
> "Verification" notes).

---

## 1. Why this epic exists

A recursive DNS resolver will accept an off-path attacker's forged answer only if the forged
packet reproduces the *entire* draw the resolver randomised for the outbound query — classically
the 16-bit transaction ID (TXID), and, since RFC 5452, also the UDP source port — before the real
authoritative reply arrives and closes the window. Randomise both from a good source and the
off-path attacker must win a race across a space near 2³²; randomise them badly (a fixed source
port, a predictable PRNG, or the SAD-DNS side channel that *leaks* the port) and that space
collapses to something an attacker can flood in seconds. Kaminsky (2008) weaponised the small
classical window; SAD-DNS (2020–2021) revived the whole class by leaking the port that RFC 5452
was supposed to protect. The threat is real, cited, and still live.

This epic builds a discrete-event resolver/attacker simulator that turns that story into a single
defended measurement: **poisoning success probability as a function of the *effective* entropy of
the TXID+port draw**, swept across four randomness sources (fixed-port, weak-PRNG, CSPRNG, QRNG)
with a SAD-DNS port-leak knob that reduces effective entropy independently of source quality. The
headline is one graph with a cliff — flat-safe at high entropy, near-certain poisoning once the
effective bits fall below the attacker's flood budget — plus a replayable race animation that
shows *why* the cliff is where it is.

The honest thesis is the same portfolio thesis carried from the ECMP study: for the *statistics*
of this race a CSPRNG is already sufficient; the exploitable failures are **structural entropy
loss** (fixed port, predictable PRNG, side-channel leakage), not the brand of the generator. The
QRNG arm's contribution is **certified, offline-verifiable provenance of the draw** — an attestable
receipt that a CSPRNG cannot produce — not a lower poisoning rate. The user-visible outcome is a
self-contained interactive web demo (the spectacle) plus a 6–8 page IEEE short paper.

## 2. Plans in this epic

| ID | Plan file | Title | Delivers | Priority |
|----|-----------|-------|----------|----------|
| P1 | `plans/plan-1-testbed-scaffolding.md` | Testbed scaffolding & config | Package skeleton, `config.py` env single-source, discrete-event core, types, parity-vector seed | `[MUST]` |
| P2 | `plans/plan-2-entropy-source-engine.md` | Draw sources + SAD-DNS knob | TXID+port draw, four source arms, QRNG QEaaS client, port-leak entropy-reduction knob, provenance | `[MUST]` |
| P3 | `plans/plan-3-off-path-attacker-race.md` | Off-path attacker & poison race | Forged-answer flood vs authoritative reply race, retransmit timers, birthday amplification | `[MUST]` |
| P4 | `plans/plan-4-resolver-model-metrics.md` | Resolver/victim model & instrumentation | Resolver state, cache, the five metrics, run-tagged CSV output | `[MUST]` |
| P5 | `plans/plan-5-experiments-graphs.md` | Experiments & headline figures | Bits×send-rate sweeps, the entropy-cliff figure, the SAD-DNS collapse figure | `[MUST]` |
| P6 | `plans/plan-6-web-demo.md` | The web spectacle | Static-export canvas demo: poison race, self-drawing cliff, SAD-DNS reveal, guess-space heatmap, provenance panel | `[MUST]` |
| P7 | `plans/plan-7-writeup.md` | IEEE short paper | `thesis/` LaTeX, the two figures wired in, positioning | `[SHOULD]` |

The `ID` column (P1…P7) is referenced from the rest of this document and from each
`/plan-feature` output. IDs match the ECMP study's `P#` / `AC-#` / `OQ-#` scheme.

## 3. Cross-cutting decisions

Decisions made once for the whole epic. Every `/plan-feature` invocation must respect these and
must not re-litigate them.

- **§3.1 — Attack-paper, not quantum-paper (LOCKED).** The defended claim is about DNS cache
  poisoning and effective entropy. The randomness source is an *independent variable*, not the
  thesis. QRNG appears as one of four arms and as a provenance mechanism, never as "the fix".
  This mirrors ECMP epic §3.1.

- **§3.2 — QRNG-EaaS role + the honest null result (LOCKED).** The expected and *intended* result
  is that CSPRNG and QRNG produce statistically indistinguishable poisoning curves at equal
  effective bits. QRNG's differentiator is the signed, offline-verifiable Q-EaaS provenance
  receipt attached to the draw (attestable unpredictability), not a lower success rate. Do not
  frame QRNG as reducing poisoning. See ECMP epic §3.2 and Appendix A.

- **§3.3 — The visualization is a first-class deliverable (LOCKED).** P6 is not a nice-to-have.
  The spectacle carries the thesis: the entropy cliff drawing itself, the CSPRNG curve collapsing
  when SAD-DNS is toggled, and the race that shows who arrives first. It must be as polished as
  `../TargetedDosColisionsAndRNGAngle/web/` (canvas animation, hundreds of in-flight packets,
  live readouts, dark mode, static export). Faithfulness is enforced by the parity gate (§3.6).

- **§3.4 — Simulated is sufficient (LOCKED, with caveat).** A discrete-event model of one
  recursive resolver, one authoritative path, and one off-path attacker is enough to defend the
  claim; no live BIND/Unbound instance and no packet capture are required. The caveat — real
  resolvers add query-name 0x20 encoding, multiple upstreams, and rate limits — is stated as a
  threat-to-validity in P7, not engineered away.

- **§3.5 — One race core / four sources / one SAD-DNS knob, decided in P2 (LOCKED).** There is a
  single discrete-event race engine (P1/P3). The only thing that varies across arms is the
  `draw(txid_bits, port_bits) -> (txid, port, provenance)` source (P2). Effective entropy is
  controlled by two orthogonal knobs: the source's real randomness quality, and the SAD-DNS
  *port-leak* knob that deterministically removes `k` bits of port entropy regardless of source.
  No arm gets its own bespoke race logic.

- **§3.6 — Testing = offline gates + root-free sim + parity, no unit-test suite (LOCKED).**
  Per project directive (same as ECMP and `qrng-eaas`), there is no `pytest` suite. Correctness is
  established by: (a) standalone offline `*_check.py` scripts that assert invariants with no
  network and no root; (b) a root-free simulator CLI (`sim/run_sim.py`) that prints per-cell
  PASS/FAIL; (c) a JS↔Python parity gate that proves the browser race/hit logic matches the Python
  source of truth before `next build` runs. "How it will be tested" everywhere in this epic means
  these three mechanisms, not automated tests.

## 4. Shared artefacts & data model

Artefacts more than one plan touches. Introduced once, consumed unchanged downstream (frozen
interfaces, ECMP epic §4 style).

| Artefact | Introduced by | Consumed by | Notes |
|----------|---------------|-------------|-------|
| `testbed/config.py` (env single-source) | P1 | all | `QEAAS_BASE_URL`, `QEAAS_API_KEY`, `PRNG_SEED`, sweep ranges, RNG seeds — mirrors ECMP `testbed/config.py:68-69` |
| `Draw` type `(txid:int, port:int, provenance:DrawProvenance)` | P2 | P3, P4, P6 | frozen dataclass; identical shape across all four arms |
| `draw_source(kind)` dispatch `fixed\|prng\|csprng\|qrng` | P2 | P3, P4, P5 | one factory, four arms; mirrors ECMP `salt/sources.py` |
| `sad_dns_leak(port_bits, k)` entropy-reduction knob | P2 | P3, P4, P5, P6 | removes `k` bits of port entropy; independent of source |
| `QRNGClient` (stdlib `urllib`, `X-API-Key`) | P2 | P2 | vendored pattern from ECMP `salt/qrng_client.py`; `/v1/random/bytes` |
| `DrawProvenance` (`request_id`, `entropy_epoch`, `receipt`, `endpoint`) | P2 | P4, P6 | QRNG cells carry the real Q-EaaS receipt; PRNG carries `seed`+`draw_index`; CSPRNG carries `source_note` |
| Discrete-event race engine (`sim/race.py`) | P1/P3 | P4, P5 | arrival races, retransmit timers, parallel in-flight queries |
| Race-hit test vectors (`vectors/race_vectors.json`) | P1 | P3, P6, parity gate | Python is source of truth; JS is vendored copy |
| Run-tagged metrics CSV (`results/exp{N}/*.csv` + `.record.json`) | P4 | P5, P6 | per-run context tag; QRNG receipt embedded in `.record.json` |
| Replay export JSON (`web/public/replay/*.json`) | P5 | P6 | scenes + sweeps + `qrng-provenance.json` |

**The five metrics** (from source §Metrics — the measurables this epic must produce):

| ID | Metric | Definition | Owner |
|----|--------|------------|-------|
| M1 | Poisoning success probability vs effective entropy bits | P(cache poisoned before legit reply) over trials, swept over effective bits | P4/P5 (headline cliff) |
| M2 | Expected forgery packets / time-to-poison at fixed entropy | mean forged packets and wall-time until first accepted forgery | P4/P5 |
| M3 | Birthday-attack amplification factor | success gain from `q` parallel in-flight queries vs single query, per bits | P4/P5 |
| M4 | Sensitivity to port-leak (SAD-DNS) | success vs bits-of-port-leaked at a fixed source | P4/P5 (collapse figure) |
| M5 | Draw provenance record | per-arm provenance (QRNG receipt / PRNG seed+index / CSPRNG note) | P2/P4 |

## 5. The mechanism under test — the resolver race state machine

The domain's substitute for a status workflow (ECMP epic §5 style). One outbound query's lifecycle:

```
                 resolver sends query with draw=(TXID, port)
                              │
                              ▼
                      [WINDOW OPEN]  ── retransmit timer fires ──▶ [RETRANSMIT] (new draw, birthday amplification)
                       │        │
   forged answer      │        │      authoritative reply arrives
   matches (TXID,port)│        │      (matches by construction)
   AND arrives first  │        │
                       ▼        ▼
                  [POISONED]  [RESOLVED-LEGIT]  ── cache TTL ──▶ [WINDOW CLOSED]
                   (red)          (green)
```

- **WINDOW OPEN**: the resolver is waiting; an accepted answer must match the full `(TXID, port)`
  draw. Attacker sprays forged answers guessing the draw.
- **Acceptance rule**: a forged packet is accepted iff its guessed `(TXID, port)` equals the draw
  *and* it arrives before the authoritative reply. Effective entropy = `txid_bits + port_bits - k`
  (k = SAD-DNS leaked port bits).
- **RETRANSMIT / birthday amplification**: multiple in-flight queries for the same name multiply
  the attacker's chance per flood round (the Kaminsky amplification) — modelled as `q` concurrent
  WINDOW-OPEN states sharing the flood.
- **POISONED (red) vs RESOLVED-LEGIT (green)**: terminal states the race animation lights up.

## 6. Threat model & deployment scenarios

- **Attacker**: off-path (cannot observe the resolver's outbound packets), can flood the resolver
  with forged answers at a bounded send-rate, can trigger resolutions for a chosen name.
- **In scope**: TXID + source-port randomisation, the SAD-DNS port-leak side channel as an
  entropy-reduction knob, birthday amplification via parallel queries, retransmit timing.
- **Out of scope (stated, not engineered away — see §3.4)**: on-path attackers, DNSSEC validation,
  query-name 0x20 encoding, DNS-over-TLS/HTTPS, and multi-upstream selection. These become
  threats-to-validity in P7.
- **Deployment scenarios modelled**: (a) legacy fixed-port resolver (16 bits total — the
  pre-2008 world); (b) RFC 5452 port-randomised resolver (up to ~32 bits); (c) RFC 5452 resolver
  under SAD-DNS port leak (32 − k bits); each crossed with the four sources.

## 7. Implementation order

1. **P1** (scaffolding) — gates everything; freezes `config.py`, the `Draw` type, and the race
   engine skeleton + vectors.
2. **P2** (sources) — depends on P1's types; freezes the four arms + SAD-DNS knob + QRNG client.
3. **P3** (attacker/race) — depends on P1 engine + P2 draws; the race becomes runnable.
4. **P4** (resolver/metrics) — depends on P3; produces the five metrics as CSV.
5. **P5** (experiments/graphs) — depends on P4; runs the sweeps, renders the two figures, exports
   replay JSON.
6. **P6** (web) — depends on P2 vectors (parity) + P5 replay JSON; the spectacle.
7. **P7** (writeup) — depends on P5 figures; can start once P5 lands.

P6 can begin its Tier-A (pure-JS sim) shell as soon as P2 vectors exist, before P5 replay data is
final — same two-tier pattern as the ECMP web demo.

## 8. Open questions (epic-wide) — RESOLVED (2026-07-30, developer: "yes to all")

- [x] **OQ-1 — TXID+port bit budget.** **Decision:** parameterise `port_bits` in `config.py`,
  default 16, and sweep; document the OS ephemeral-range (~11–16 bit) caveat in P7. Binds P1
  (`config.py`), P2 (draw), P5 (sweep), P7 (caveat).
- [x] **OQ-2 — Effective-entropy sweep granularity.** **Decision:** sweep 8→32 effective bits in
  1-bit steps, ≥10⁴ trials/cell (mirror ECMP cell counts). Binds P5 (matrix), P4 (trial count).
- [x] **OQ-3 — Attacker send-rate axis.** **Decision:** sweep send-rate as the M3/birthday axis
  (2-D heatmap); hold it fixed for the 1-D headline cliff (M1). Binds P4 (M3), P5 (matrix).
- [x] **OQ-4 — SAD-DNS leak model.** **Decision:** exact `k`-bit port-entropy reduction knob for
  the clean cliff-collapse story; note the real side channel is noisier as a threat-to-validity in
  P7. Binds P2 (`sad_dns_leak`), P5 (M4 sweep), P7.
- [x] **OQ-5 — Q-EaaS key provenance.** **Decision:** live Q-EaaS call during the P5 export step
  captures the real receipt, frozen into `web/public/replay/qrng-provenance.json`; key read from
  `DNSPoisonRace/.env` (already gitignored, never in context/browser). Binds P2, P5, P6, Appendix A.
- [x] **OQ-6 — Web hosting subpath.** **Decision:** GitHub Pages subpath via the
  `NEXT_PUBLIC_BASE_PATH` static-export pattern (clone ECMP `web/next.config.ts`). Binds P6.

All resolved; decisions folded into the relevant plans' briefs above and into §3 where they lock
cross-cutting behaviour.

## 9. Per-plan briefs

Acceptance criteria below are **derived from `plans/viz-3-dns-poison-race.md`** (§Method, §Metrics,
§THE VISUALIZATION, §Thesis) — there is no upstream issue tracker to quote verbatim (see §3 of the
generic `/plan-epic` template; this project uses source docs, not GitHub issues). Each AC cites the
source section it comes from so it stays traceable, not invented.

### P1 — Testbed scaffolding & config
- **Delivers:** the `testbed/` package skeleton, `config.py` as the single env source-of-truth,
  the discrete-event simulation core (event queue, virtual clock), shared `types.py`, and the
  seed of `vectors/race_vectors.json`.
- **Acceptance criteria (derived from source §Method):**
  - AC-1.1 A root-free, network-free `sim/` package runs a trivial one-query race end to end.
  - AC-1.2 `config.py` reads `QEAAS_BASE_URL` (default `https://api.qeaas.eu`), `QEAAS_API_KEY`
    (default empty), `PRNG_SEED`, and sweep parameters from the environment only.
  - AC-1.3 The `Draw` type and race-engine interfaces are frozen and documented for P2/P3.
- **Depends on:** none. **Gates:** P2, P3, P4.
- **Conventions to follow:** mirror `../TargetedDosColisionsAndRNGAngle/testbed/config.py` and
  `sim/` layout; stdlib only for the core (pandas/matplotlib confined to `analysis/`).
- **Out of scope:** the draw sources (P2), the attacker (P3).

### P2 — Draw sources + SAD-DNS knob
- **Delivers:** `draw_source(kind)` with four arms — `fixed` (fixed port, 16-bit TXID only),
  `prng` (weak LCG / 32-bit-seeded `random.Random`), `csprng` (`os.urandom`/`secrets`), `qrng`
  (Q-EaaS bytes) — plus `sad_dns_leak(port_bits, k)` and the `QRNGClient`.
- **Acceptance criteria (derived from source §Method, §Connection):**
  - AC-2.1 All four arms return the identical `Draw` shape so the race is source-agnostic (§3.5).
  - AC-2.2 The `qrng` arm sources bytes from the Q-EaaS API (`GET /v1/random/bytes?size=&format=hex`,
    header `X-API-Key`) with retry/backoff on 429/503 and immediate raise on 401 — no new QC runs.
  - AC-2.3 The `csprng` arm uses `os.urandom`; the `prng` arm is deliberately weak (predictable
    seed) and reproducible; the `fixed` arm pins the port.
  - AC-2.4 `sad_dns_leak` deterministically removes `k` bits of port entropy independent of source.
  - AC-2.5 Every draw carries `DrawProvenance`; QRNG carries the real Q-EaaS receipt.
- **Depends on:** P1. **Gates:** P3, P4, P5, P6.
- **Conventions to follow:** vendor the client pattern from
  `../TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py` and the arm dispatch from
  `salt/sources.py` (stdlib `urllib`, no `requests`). See Appendix A.
- **Out of scope:** the race itself; provenance *rendering* (P6).

### P3 — Off-path attacker & poison race
- **Delivers:** the discrete-event race — off-path attacker flooding forged answers guessing
  `(TXID, port)` while the authoritative reply flies back — with retransmit timers and birthday
  amplification via `q` parallel in-flight queries.
- **Acceptance criteria (derived from source §Method, §THE VISUALIZATION "poison race"):**
  - AC-3.1 A forged answer is accepted iff its guessed `(TXID, port)` equals the draw and it
    arrives before the authoritative reply (§5 acceptance rule).
  - AC-3.2 Attacker send-rate, authoritative RTT, and retransmit timer are configurable.
  - AC-3.3 Parallel in-flight queries multiply per-round success (birthday amplification, M3).
  - AC-3.4 Race outcomes are reproducible from a seed and emit the vectors P6/parity consume.
- **Depends on:** P1 (engine), P2 (draws). **Gates:** P4.
- **Out of scope:** metric aggregation (P4), figures (P5).

### P4 — Resolver/victim model & instrumentation
- **Delivers:** the resolver state machine (§5), a cache, and the five-metric collector writing
  run-tagged CSV + `.record.json` (with the QRNG receipt embedded).
- **Acceptance criteria (derived from source §Metrics):**
  - AC-4.1 M1 poisoning success probability per (source, effective-bits) cell.
  - AC-4.2 M2 expected forgery packets and time-to-poison at fixed entropy.
  - AC-4.3 M3 birthday amplification factor vs parallel-query count.
  - AC-4.4 M4 success vs bits-of-port-leaked (SAD-DNS sensitivity).
  - AC-4.5 M5 per-cell provenance record persisted to `.record.json`.
- **Depends on:** P3. **Gates:** P5, P6.
- **Out of scope:** rendering figures (P5), the web viz (P6).

### P5 — Experiments & headline figures
- **Delivers:** the experiment matrix (as data), the sweeps, the two headline figures, and the
  replay-JSON export for P6.
- **Acceptance criteria (derived from source §Metrics, §THE VISUALIZATION "entropy cliff"):**
  - AC-5.1 The bits×source sweep renders the **entropy-cliff** figure (M1) — flat-safe then a
    sharp fall to near-certain poisoning.
  - AC-5.2 The SAD-DNS knob sweep renders the **collapse** figure (M4) — the CSPRNG curve falling
    as `k` rises.
  - AC-5.3 A live Q-EaaS call captures the real provenance receipt, frozen into
    `web/public/replay/qrng-provenance.json` (OQ-5).
  - AC-5.4 Replay scenes + sweeps exported to `web/public/replay/*.json`.
- **Depends on:** P4. **Gates:** P6, P7.
- **Conventions to follow:** mirror ECMP `experiments/matrix.py`, `analysis/graphs.py`,
  `sim/replay_export.py`.
- **Out of scope:** the paper prose (P7).

### P6 — The web spectacle
- **Delivers:** the static-export Next.js interactive visualization — the star of the epic.
- **Acceptance criteria (derived verbatim from source §THE VISUALIZATION):**
  - AC-6.1 **The poison race** — a split timeline where the attacker's forged-answer stream sprays
    guesses at the resolver while the authoritative reply races back; a hit lights the cache red
    (poisoned) or green (legit wins first). Replayable per source.
  - AC-6.2 **Entropy cliff** — an animated curve drawing itself as the entropy slider drops:
    flat-safe, then a sudden fall to near-certain poisoning.
  - AC-6.3 **SAD-DNS reveal** — a toggle for the side-channel port leak that visibly collapses the
    safe CSPRNG curve (provenance/state beats raw source quality).
  - AC-6.4 **Guess-space heatmap** — a TXID×port grid with attacker coverage filling in over time
    vs the single correct cell.
  - AC-6.5 A **provenance panel** rendering the QRNG Q-EaaS receipt (mirror ECMP `ProvenancePanel`).
  - AC-6.6 Self-contained static HTML/Canvas, dark mode, `output: "export"`; the build is **gated
    on JS↔Python race-logic parity** (§3.6) — the browser must reproduce the Python race outcomes.
- **Depends on:** P2 (parity vectors), P5 (replay JSON). **Gates:** none.
- **Conventions to follow:** clone the stack and discipline of
  `../TargetedDosColisionsAndRNGAngle/web/` — Next 16 App Router, Tailwind v4, hand-rolled canvas +
  `requestAnimationFrame` (no animation lib), `next-themes`, vendored parity gate
  (`scripts/check-parity.mjs`, `scripts/vendor-*.mjs`), replay JSON in `public/replay/`.
- **Out of scope:** any server-side key handling — the web app renders a *recorded* receipt only;
  the `QEAAS_API_KEY` never reaches the browser (mirror ECMP `web/lib/qeaas.ts` placeholder →
  export-time real receipt).

### P7 — IEEE short paper
- **Delivers:** `thesis/thesis.tex` (6–8 pp, double-column) with the two figures wired in and the
  positioning against prior work.
- **Acceptance criteria (derived from source §Thesis):**
  - AC-7.1 States the single defended claim: poisoning probability is governed by *effective*
    entropy bits, not the generator brand; the exploitable failures are structural entropy loss.
  - AC-7.2 Includes the entropy-cliff figure (headline) and the SAD-DNS collapse figure.
  - AC-7.3 Frames QRNG as certified provenance, not a lower poisoning rate (§3.2).
  - AC-7.4 States the §6 out-of-scope items as threats to validity.
- **Depends on:** P5. **Out of scope:** new experiments (all data comes from P5).

## 10. Related work & positioning (novelty scan — 2026-07-30)

**Must cite and distinguish:**
- **Kaminsky (2008)** — the classical cache-poisoning race and birthday amplification. This epic
  *quantifies* the entropy cliff his attack implies, across sources.
- **SAD-DNS (Man et al., CCS 2020; follow-ups 2021)** — the side channel that leaks the source
  port. Modelled here as the §3.5 entropy-reduction knob; the SAD-DNS reveal (AC-6.3) is the
  demo's dramatic beat.
- **RFC 5452 (2009)** — source-port randomisation as the mitigation. This epic measures exactly
  how much its port bits are worth, and what SAD-DNS takes back.
- **DNS-0x20 (Dagon et al., 2008)** — query-name case encoding as *additional* entropy;
  explicitly out of scope (§6), cited as a threat-to-validity so a reviewer knows it was considered.

**Builds on / internal prior work:**
- `../TargetedDosColisionsAndRNGAngle/` (ECMP collision DoS) — reuses the pluggable-source design
  (PRNG/CSPRNG/QRNG), the "provenance not magic" thesis, and the offline-gate testing discipline,
  one network layer up (transport/DNS vs load-balancing). No overlap with the shipped ECMP web demo.
- `study-ideas/net-1-unpredictability-as-network-primitive.md` (the umbrella) and
  `study-ideas/viz-5-gossip-overlay-resilience.md` (sibling) — this is one instance of the
  unpredictability-primitive family.

**Framing adjustment:** avoid any "quantum stops DNS poisoning" claim — the null result (§3.2) is
the honest and more defensible position and must survive into P7.

## Appendix A — QRNG-EaaS connection & key-mint runbook

Mirror of `../TargetedDosColisionsAndRNGAngle/` Appendix A. The QRNG arm consumes the **live hosted
Q-EaaS service**; it does not run new quantum hardware.

- **A.1 — Endpoint.** `GET {QEAAS_BASE_URL}/v1/random/bytes?size=<n>&format=hex`, authenticated
  with header `X-API-Key: <key>`. Response is a JSON envelope carrying `request_id`, `format`,
  `data`, `entropy_epoch`, `timestamp`, `receipt`. 401 = auth misconfig (raise immediately);
  429 honours `Retry-After`; 503 (`low_quantum_entropy`) backs off and retries.
- **A.2 — Base URL.** `QEAAS_BASE_URL` defaults to `https://api.qeaas.eu` (the hosted service —
  same default as the ECMP study). Override via environment only.
- **A.3 — Key.** `QEAAS_API_KEY` is read from the environment (from `DNSPoisonRace/.env`, already
  present and gitignored). It is **never** read into an agent's context, printed, logged, or
  committed. Load it for a run with `set -a && . ./.env && set +a`.
- **A.4 — Security note.** The key stays server/CLI-side (the P5 export step). The web app (P6)
  ships only the *recorded* provenance receipt — the key never reaches the browser. This is the
  same posture as ECMP `web/lib/qeaas.ts` (placeholder replaced at export by the real receipt).
- **A.5 — Provenance is the point.** The QRNG arm exists to attach an offline-verifiable receipt to
  the draw, not to lower the poisoning rate (§3.2). Expect the QRNG and CSPRNG cliffs to coincide.
