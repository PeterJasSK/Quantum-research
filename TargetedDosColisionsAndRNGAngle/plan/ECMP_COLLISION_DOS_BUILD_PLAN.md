# ECMP Collision DoS — Build Plan

**One-line goal:** build a simulated Mininet/OVS/Ryu ECMP testbed with a swappable hash-salt source
(weak PRNG / CSPRNG / QRNG) and salt rotation, run the **five experiments** that prove a precision
collision attacker evades rate-limiting and throttling while **salt rotation** defeats it, and ship a
three-scene web demo — producing an attack + mitigation paper.

> **Framing (read once, repeat in the write-up):** this is an **attack paper, not a quantum paper**.
> CSPRNG alone defeats the attack; QRNG is a **calibration ceiling** — it proves what "provably
> non-reconstructable salt" buys you, which is *identical* to CSPRNG in this threat model. That null
> result is a stated finding, not a gap. The contribution is: a new attacker class that occupies the
> gap between rate-limiting and throttling, plus a mechanism-level defence (salt rotation) with a
> quantified rotation-frequency specification.

---

## Locked decisions (from the study docs)

| # | Decision |
|---|----------|
| 1 | Topology is **simulated** — Mininet + Open vSwitch, Ryu controller. Sufficient for all five experiments (they are mechanism, not scale, questions). |
| 2 | ECMP path selection = `hash(5-tuple + salt) mod N_links`. Salt source is **configurable**: weak PRNG (known seed), CSPRNG, QRNG (from Q-EaaS API). |
| 3 | Attacker operates at **three knowledge levels**: full (salt known), partial (algorithm known, seed-space guessed), blind. |
| 4 | **Salt rotation** is the defence under test; rotation interval is the key tunable. Rate-limiting + throttling are the *baseline* defences shown to fail. |
| 5 | Primary threat model in the write-up = **multi-tenant cloud fabric** (most pervasive ECMP, victim has no fabric visibility). |
| 6 | QRNG salt is pulled from the existing **Q-EaaS `GET /v1/random/bytes`** endpoint; only used to show provenance, not to claim superiority over CSPRNG. |
| 7 | Web demo in **two tiers**: Tier A browser-only (immediate), Tier B WebSocket to the live testbed (later). JS hash + Python hash tested against shared vectors so they never drift. |

## Tech stack

- **Testbed:** Mininet + Open vSwitch (real packets, real ECMP hashing), Ryu controller (Python) sets/rotates the salt via flow rules.
- **Salt sources:** `random` (weak PRNG, fixed seed) / `secrets` (CSPRNG) / Q-EaaS QRNG API. One `salt_source(kind) -> bytes` interface.
- **Attacker:** Python — 5-tuple collision crafter + traffic generator (`scapy`/`hping3`/`iperf` for load), volumetric and precision modes.
- **Instrumentation:** OpenFlow port-stat pollers (per-link utilisation), `iperf` victim throughput, time-to-saturation + packets-to-saturation collectors → CSV.
- **Analysis:** Python (`pandas`/`matplotlib`) — Jain's fairness index, the two key graphs.
- **Web demo:** static HTML + JS (Tier A); thin WebSocket layer on the Ryu controller pushing real port-stat counters (Tier B).

> **Verify before relying on it:** OVS must expose the ECMP hash fields you expect (`select` group buckets / `multipath` action). Confirm the salt actually enters the hash on your OVS version in EPIC 0.

---

## Architecture (simulated testbed)

```
                         Ryu controller  ──sets/rotates──►  salt (PRNG | CSPRNG | QRNG)
                              │                                     │
                              ▼                                     ▼
  attacker host ─┐      ┌───────────────┐   link0 ─┐        hash(5-tuple + salt) mod N
                 ├────► │  OVS  (ECMP)  │   link1 ─┼──► spine ──► victim host
  bg-traffic ────┘      └───────────────┘   link2 ─┘                ▲
                              │             link3                    │
                     OpenFlow port-stats ──► collectors ──► CSV ──► graphs / WebSocket ──► web demo
```

**Why simulation is sufficient:** the hash function, salt, bucket selection, and rate-limit/throttle
flow rules are identical in emulation. Findings are **scale-invariant ratios** (precision vs volumetric,
weak PRNG vs rotating CSPRNG). Only *absolute* time-to-saturation differs on 10G silicon — state that
caveat honestly; the ratios are the result.

---

# EPICS

Each epic has a **Goal**, **Stories** (task checkboxes), and **Done when…**.
Priority: `[MUST]` core to the five experiments, `[SHOULD]` strengthens the paper, `[COULD]` stretch.

---

## EPIC 0 — Testbed scaffolding & the one risky spike `[MUST]`

**Goal:** a running Mininet/OVS/Ryu ECMP topology whose salt is provably part of the path-selection hash.

- **S0.1 Topology**
  - [ ] Mininet script: attacker host, victim host, background-traffic host, OVS switch, **N parallel links** (default 4) to an egress/spine.
  - [ ] Ryu app installs ECMP group/multipath rules so traffic spreads by `hash(5-tuple + salt) mod N`.
- **S0.2 SPIKE — salt actually enters the hash** *(do first; de-risks everything)*
  - [ ] Prove that changing the salt re-maps a fixed 5-tuple to a different link. If OVS won't take a salt into its native hash, fall back to a Ryu-computed `hash(5-tuple+salt)` that writes the output link into the flow rule (controller-side ECMP).
  - [ ] 10-line check: same 5-tuple, two salts → two different egress links.

**Done when:** the topology boots, traffic distributes across N links, and flipping the salt provably re-maps flows.

---

## EPIC 1 — Salt sources, hash core & rotation `[MUST]`

**Goal:** one hash + salt engine, three interchangeable sources, and rotation as a controller knob.

- **S1.1 Hash + salt interface**
  - [ ] `link = hash(5tuple, salt) mod N`; single Python implementation used by controller and attacker.
  - [ ] `salt_source(kind)`: `prng` (weak, fixed/guessable seed) | `csprng` (`secrets`) | `qrng` (Q-EaaS `GET /v1/random/bytes`, show provenance: timestamp, byte count, endpoint).
- **S1.2 Salt rotation**
  - [ ] Controller rotates the active salt every `interval` (configurable, minutes → sub-second); reinstalls group rules atomically; logs each rotation event + new salt.
  - [ ] Rotation is a no-op for correctness — legitimate flows just redistribute fairly.
- **S1.3 JS ↔ Python parity** *(for the web demo)*
  - [ ] Shared test vectors: identical `(5tuple, salt) → link` in Python and JS. CI/asserts fail if they drift.

**Done when:** all three sources feed the same hash; rotation reinstalls a fresh mapping live; JS and Python agree on every vector.

---

## EPIC 2 — Attacker: collision crafter + knowledge levels `[MUST]`

**Goal:** the precision attacker, plus the naive volumetric control.

- **S2.1 Collision crafter**
  - [ ] Given salt (or a guessed seed space) + target link, enumerate 5-tuples that hash to that link. Vary source ports / destination combos so each flow looks distinct.
- **S2.2 Knowledge levels**
  - [ ] **Full:** salt known → craft exact collision set. **Partial:** algorithm known, brute-force seed space → derive salt. **Blind:** no salt info (expected failure baseline).
- **S2.3 Traffic modes**
  - [ ] **Volumetric control:** single source, no 5-tuple variation, high rate.
  - [ ] **Precision:** collision set spread across multiple compliant sources / many distinct flows, each below defence thresholds.

**Done when:** the full-knowledge attacker drives crafted flows onto one target link; the partial attacker reconstructs the salt by brute force; the volumetric mode floods naively for the control.

---

## EPIC 3 — Defences & instrumentation `[MUST]`

**Goal:** the baseline defences that must fail, and the collectors that prove it.

- **S3.1 Baseline defences (Ryu flow rules)**
  - [ ] Per-source **rate limiting** (bandwidth cap per source).
  - [ ] Per-source **connection throttling** (drop/deprioritise after N connections/requests).
  - [ ] Both must visibly stop the volumetric flood (verified in Experiment 1).
- **S3.2 Metrics collectors → CSV**
  - [ ] Per-link utilisation (OpenFlow port-stats poll) + **max link utilisation**.
  - [ ] **Jain's fairness index** across links.
  - [ ] **Victim throughput** under attack (`iperf`).
  - [ ] **Time-to-saturation** and **packets/flows-to-saturation** of the target link.

**Done when:** defences drop the naive flood; all five metrics log to CSV per run, timestamped and tagged by (salt source, knowledge level, rotation interval, attack mode).

---

## EPIC 4 — Run the five experiments & produce the graphs `[MUST]`

**Goal:** execute the experiment matrix and generate the paper's two key graphs.

- **S4.1 Experiment 1 — baseline defences work vs volumetric**
  - [ ] Rate-limit + throttle ON, naive flood → flood degraded, no saturation, victim protected. *(proves defences are real)*
- **S4.2 Experiment 2 — precision evades rate limiting**
  - [ ] Same rate limit, precision attacker across compliant sources → target link saturates, victim collapses, limiter never fires.
- **S4.3 Experiment 3 — precision evades throttling**
  - [ ] Same throttling, 5-tuples varied across many valid-looking flows → saturation, victim collapses, throttle never fires.
- **S4.4 Experiment 4 — salt rotation defeats the attacker**
  - [ ] Full attacker vs three configs: weak PRNG no rotation (**attack succeeds**), CSPRNG+rotation (**fails**), QRNG+rotation (**fails, identical → null result**). Measure Jain + victim throughput under attack AND clean background (rotation must be cost-free when no attack).
- **S4.5 Experiment 5 — rotation frequency curve**
  - [ ] Partial attacker; sweep rotation interval slow→fast; measure time-to-saturation + packets-to-saturation → threshold curve mapping to seed-space brute-force time (derive analytically, confirm empirically).
- **S4.6 Graphs**
  - [ ] Graph 1: **attacker success vs salt source × knowledge level**. Graph 2: **rotation-frequency threshold curve**.

**Done when:** all five experiments produce the expected results into CSV, and both key graphs render from that data.

---

## EPIC 5 — Web demonstration `[SHOULD]`

**Goal:** make the five-experiment argument visible in three scenes.

- **S5.1 Tier A — browser-only**
  - [ ] Static HTML page, all salt/hash/bucket logic in JS (mirrors Python, shares EPIC 1 vectors). Topology view: attacker, switch, 4 links, victim.
  - [ ] **Scene 1** naive flood → rate-limiter fires (red on attacker), links balanced, victim healthy.
  - [ ] **Scene 2** precision mode → limiter/throttle stay green, one link climbs to red, victim collapses; predictable weak-PRNG salt shown on screen.
  - [ ] **Scene 3** CSPRNG + rotation → links scatter, rotation event visibly disperses the crafted 5-tuples, victim stays healthy; **rotation-frequency slider** re-establishes/collapses saturation live (Experiment 5 interactive). QRNG selection shows entropy provenance without overstating.
- **S5.2 Tier B — connected to the testbed** `[COULD]`
  - [ ] Same front-end; link bars + victim numbers driven by **real OVS port-stat counters** over WebSocket from the Ryu controller. Sub-modes: live + replay (recorded sweep, no live infra needed for talks).

**Done when:** Tier A runs the three scenes offline on GitHub Pages; (stretch) Tier B shows real counters live or on replay.

---

## EPIC 6 — Write-up `[MUST]`

**Goal:** the attack + mitigation paper.

- **S6.1 Paper**
  - [ ] Structure: new attacker class (evades rate-limit + throttle) → mechanism-level defence (salt rotation) → rotation-frequency specification. Both key graphs included.
  - [ ] State the QRNG null result explicitly; state the scale caveat (ratios are scale-invariant, absolute numbers are context).
  - [ ] Target venues: ACM ANCS, IEEE ICNP, IFIP Networking.

**Done when:** the paper tells the complete argument with both graphs and honest framing.

---

# Cross-cutting

## Metrics (every run tagged: salt source, knowledge level, rotation interval, attack mode)

| Metric | Purpose |
|--------|---------|
| Max link utilisation | Did the target link saturate? |
| Jain's fairness index | Fair spread vs single-link concentration |
| Victim throughput | User-visible damage |
| Time-to-saturation | Rotation-frequency curve axis |
| Packets/flows-to-saturation | Attacker cost |

## Key decisions & reasoning (quick reference)

| Decision | Reasoning |
|---|---|
| Attack paper, not quantum paper | CSPRNG alone defeats the attack |
| QRNG = calibration ceiling, not solution | Honest null result; pre-empts "why quantum?" |
| Add rate-limit + throttle experiments | Closes gap between "new attacker" claim and evidence |
| Simulated topology sufficient | All experiments are mechanism, not scale, questions |
| Rotation frequency = key parameter | Turns "use CSPRNG" advice into a practitioner spec |
| Three scenes, Tier A first | Argument visible before the paper is read; Tier A ships immediately |
| JS + Python hash tested together | Demo never silently drifts from the real implementation |
| Multi-tenant cloud primary scenario | Most plausible threat model; strongest venue pitch |

## Risks & mitigations

- **Salt doesn't enter OVS native hash** → SPIKE S0.2 first; fallback to controller-side ECMP.
- **JS/Python hash drift** → shared test vectors, asserted (S1.3).
- **"Why not just hardware?"** → state scale caveat; ratios are scale-invariant; one optional hardware confirmation run pre-empts it.
- **QRNG framing reads as motivated reasoning** → keep it as calibration ceiling everywhere; null result is the point.

## Open questions (from the study — resolve before/while running)

- [ ] Does SDN controller-managed salt (single point of failure for the whole fabric) change the solution space enough to measure?
- [ ] Rotation unit: per-flow, per-epoch, or per-time-interval?
- [ ] Collapse partial vs full knowledge into one condition, or keep separate?
- [ ] Does the Tier B replay dataset need all 3×3 (source × knowledge) conditions, or a subset?

## Definition of Done (whole project)

- [ ] Mininet/OVS/Ryu ECMP testbed with swappable PRNG/CSPRNG/QRNG salt + live rotation.
- [ ] Precision collision attacker (three knowledge levels) + volumetric control.
- [ ] Rate-limit + throttle baseline defences that stop the volumetric flood.
- [ ] All five experiments run into CSV; both key graphs render.
- [ ] Tier A web demo shows the three scenes offline.
- [ ] Paper drafted: new attacker class → salt-rotation defence → rotation-frequency spec, with QRNG null result stated.
