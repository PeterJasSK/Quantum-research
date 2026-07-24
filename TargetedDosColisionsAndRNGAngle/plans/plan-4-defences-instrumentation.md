# Plan 4 — Baseline defences & instrumentation

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 3** · **Priority:** `[MUST]`
**Status:** Draft · **Depends on:** P1, P3 · **Gates:** P5, P6 (Tier B)

> Pick up with `/plan-feature plans/plan-4-defences-instrumentation.md`. Read epic §3.1 (why these defences
> must fail) and §4 (metrics + CSV schema) first.

## Goal
The two baseline defences that **must stop the volumetric flood but fail against the precision attacker** —
rate limiting and throttling — plus the five metrics collectors that prove it, all writing to a run-tagged CSV.
Without a defence that provably fires on the flood, "our attacker evades defences" is indistinguishable from
"the defences were misconfigured" (epic §3.1).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] Per-source **rate limiting** (bandwidth cap per source).
- [ ] Per-source **connection throttling** (drop/deprioritise after N connections/requests).
- [ ] Both must visibly stop the volumetric flood (verified in Experiment 1).
- [ ] Per-link utilisation (OpenFlow port-stats poll) + **max link utilisation**.
- [ ] **Jain's fairness index** across links.
- [ ] **Victim throughput** under attack (`iperf`).
- [ ] **Time-to-saturation** and **packets/flows-to-saturation** of the target link.
- **Done when:** defences drop the naive flood; all five metrics log to CSV per run, timestamped and tagged by (salt source, knowledge level, rotation interval, attack mode).

## The five metrics (epic §4)
| Metric | Purpose |
|--------|---------|
| Max link utilisation | Did the target link saturate? |
| Jain's fairness index | Fair spread vs single-link concentration |
| Victim throughput (`iperf`) | User-visible damage |
| Time-to-saturation | Rotation-frequency curve axis (P5 Exp 5) |
| Packets/flows-to-saturation | Attacker cost |

**CSV tagging (mandatory):** every row tagged `(salt_source, knowledge_level, rotation_interval, attack_mode)` +
timestamp. P5 and P6-TierB read this file; a missing tag breaks their filtering.

## Conventions
Defences as Ryu flow rules; collectors poll OpenFlow port-stats. Tune the rate-limit / throttle thresholds so the
**volumetric flood is clearly stopped** — those exact thresholds are then reused unchanged in Experiments 2–3 where
the precision attacker stays under them.

## Out of scope
Rotation (P2 owns it); the QRNG source (P2); running the experiment matrix (P5). This plan delivers *defences that
fire on the flood* + *five collectors → CSV*, not the experiments.
