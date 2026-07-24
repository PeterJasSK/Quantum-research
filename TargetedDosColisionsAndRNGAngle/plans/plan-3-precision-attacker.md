# Plan 3 — Precision collision attacker & knowledge levels

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 2** · **Priority:** `[MUST]`
**Status:** Draft · **Depends on:** P2 · **Gates:** P4 (needs the volumetric flood), P5

> Pick up with `/plan-feature plans/plan-3-precision-attacker.md`. Read epic §3.1 (the new-attack framing —
> this plan makes it real) and §6 (threat model) first.

## Goal
The precision collision attacker plus the naive volumetric control. This is the **"new attacker"** the whole
epic is built to characterise: structurally invisible to rate limiting and throttling because it damages by
*mathematical placement*, not by any behaviour a source-watching defence can observe (epic §3.1).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] Given salt (or a guessed seed space) + target link, enumerate 5-tuples that hash to that link. Vary source ports / destination combos so each flow looks distinct.
- [ ] **Full:** salt known → craft exact collision set. **Partial:** algorithm known, brute-force seed space → derive salt. **Blind:** no salt info (expected failure baseline).
- [ ] **Volumetric control:** single source, no 5-tuple variation, high rate.
- [ ] **Precision:** collision set spread across multiple compliant sources / many distinct flows, each below defence thresholds.
- **Done when:** the full-knowledge attacker drives crafted flows onto one target link; the partial attacker reconstructs the salt by brute force; the volumetric mode floods naively for the control.

## Hard constraint — use the real hash
Import `hash_core` from P2. The attacker must compute collisions against the **exact** hash the controller uses —
never a re-implemented copy. A drift here silently invalidates every experiment.

## Focus notes
- The attacker's defining property is **evasion of source-based detection**. Precision mode must keep every
  individual source under the P4 rate-limit and throttle thresholds — that's what makes Experiments 2–3 land.
- **Partial-knowledge brute force** targets the weak-PRNG seed space (from P2). The brute-force *time* is the
  x-axis anchor for the Experiment 5 rotation-frequency curve — instrument it so P5 can read reconstruction time.
- Open decision Q3 (epic §8): keep partial vs full as separate conditions, or collapse.
- Traffic generation: `scapy` / `hping3` / `iperf`.

## Out of scope
The defences it evades (P4); running the experiment matrix (P5). This plan delivers a *working attacker with three
knowledge levels + a volumetric control*, not the experiments that exercise it.
