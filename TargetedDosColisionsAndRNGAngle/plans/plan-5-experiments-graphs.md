# Plan 5 — The five experiments & the two key graphs

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 4** · **Priority:** `[MUST]`
**Status:** Draft · **Depends on:** P2, P3, P4 · **Gates:** P6 (Tier B replay), P7

> Pick up with `/plan-feature plans/plan-5-experiments-graphs.md`. Read epic §3.2 (the QRNG null result is
> *measured* here) and §4 (CSV) first.

## Goal
Execute the experiment matrix and produce the paper's **two key graphs**. The five experiments form a complete
argument: here is the standard defence (Exp 1), here is why it fails (Exp 2–3), here is what works (Exp 4), and
here is the actionable knob (Exp 5).

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] **Exp 1 — baseline works vs volumetric:** Rate-limit + throttle ON, naive flood → flood degraded, no saturation, victim protected. *(proves defences are real)*
- [ ] **Exp 2 — precision evades rate limiting:** Same rate limit, precision attacker across compliant sources → target link saturates, victim collapses, limiter never fires.
- [ ] **Exp 3 — precision evades throttling:** Same throttling, 5-tuples varied across many valid-looking flows → saturation, victim collapses, throttle never fires.
- [ ] **Exp 4 — salt rotation defeats the attacker:** Full attacker vs three configs: weak PRNG no rotation (**attack succeeds**), CSPRNG+rotation (**fails**), QRNG+rotation (**fails, identical → null result**). Measure Jain + victim throughput under attack AND clean background (rotation must be cost-free when no attack).
- [ ] **Exp 5 — rotation frequency curve:** Partial attacker; sweep rotation interval slow→fast; measure time-to-saturation + packets-to-saturation → threshold curve mapping to seed-space brute-force time (derive analytically, confirm empirically).
- [ ] Graph 1: **attacker success vs salt source × knowledge level**. Graph 2: **rotation-frequency threshold curve**.
- **Done when:** all five experiments produce the expected results into CSV, and both key graphs render from that data.

## Focus notes
- **Exp 4 is where the QRNG null result is proven on purpose** (epic §3.2): QRNG+rotation ≡ CSPRNG+rotation. Also
  prove rotation is **cost-free under clean background traffic** — all three sources give identical fair
  distribution when there is no attack.
- **Exp 5 turns advice into a specification**: the threshold maps to the attacker's seed-space brute-force time
  (from P3). Derive it analytically, confirm empirically. Output: "rotate faster than N seconds given seed space S."
- Analysis in Python (`pandas` / `matplotlib`). Reads the P4 run-tagged CSV.
- Open decision Q3/Q4 (epic §8): whether all 3×3 (source × knowledge) conditions are run, or a subset.

## Out of scope
The paper prose (P7); the interactive/animated visuals (P6). This plan produces *data + two static graphs*.
