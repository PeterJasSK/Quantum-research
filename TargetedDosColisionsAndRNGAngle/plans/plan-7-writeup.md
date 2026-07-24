# Plan 7 — Write-up: the attack + mitigation paper

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 6** · **Priority:** `[MUST]`
**Status:** Draft · **Depends on:** P5 (graphs) · related-work can be drafted in parallel

> Pick up with `/plan-feature plans/plan-7-writeup.md`. Read epic §3.1 (locked framing), §3.2 (QRNG null result +
> practical angle), §3.4 (scale caveat), §6 (threat model) first.

## Goal
The attack + mitigation paper. It tells one argument: **a new attacker class that occupies the gap between rate
limiting and throttling → a mechanism-level defence (salt rotation) → a quantified rotation-frequency
specification**, with both key graphs and honest framing throughout.

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] Structure: new attacker class (evades rate-limit + throttle) → mechanism-level defence (salt rotation) → rotation-frequency specification. Both key graphs included.
- [ ] State the QRNG null result explicitly; state the scale caveat (ratios are scale-invariant, absolute numbers are context).
- [ ] Target venues: ACM ANCS, IEEE ICNP, IFIP Networking.
- **Done when:** the paper tells the complete argument with both graphs and honest framing.

## Framing rules (from the epic — non-negotiable)
- **Attack paper, not quantum paper** (§3.1). Lead with the DoS-defence-gap positioning. The attacker is defined
  by *what it evades* (Experiments 1–3), not just how it works.
- **QRNG null result stated plainly** (§3.2): QRNG buys nothing over CSPRNG *in this threat model*. Keep the
  practical QRNG angle — attestable entropy **provenance** (signed receipt, entropy epoch) and product
  demonstration — in a separate "practical deployment" note, never mixed into the attack-outcome claim.
- **Scale caveat honest** (§3.4): absolute time-to-saturation is lower on real 10G silicon; the findings are
  scale-invariant ratios. An optional single hardware-confirmation run pre-empts the reviewer's scale objection.
- **Multi-tenant cloud is the primary scenario** (§6); name microservices / SD-WAN / 5G core as secondary relevance.

## Content the paper must carry
- Both key graphs from P5 (attacker-success-vs-source; rotation-frequency threshold curve).
- The Experiment 5 specification: "rotate faster than N seconds given seed space S."
- The ECMP-specific property linking new-place to new-solution (§6): controller-managed salt = fabric-wide single
  point of failure, so controller-level rotation is a fabric-wide fix.
- A pointer to the P6 web demo as reproducibility artefact.

## Positioning & related work — load-bearing (epic §10 novelty scan)
The scan verdict: novel **only with careful positioning** — do NOT claim we invented single-bucket hash-flooding or
keyed-hash defence. Mandatory moves:
- **Early "distinction" paragraph** against the two reviewer-killers: **RSS secret key** (MS NDIS / Linux
  `scaling.txt` — same attack+defence shape at the NIC RX-queue) and **single-shard flooding** (Nguyen & Thai,
  arXiv 2007.08600 / IEEE TDSC 2022). Own them up front — see epic §10 table for the exact differentiators.
- **One-line mechanism delta from Crossfire (S&P 2013) / Coremelt (ESORICS 2009)** in the intro: *single attacker +
  deterministic hash placement + one link, no botnet.* Adopt their "target link / legitimate-indistinguishable"
  vocabulary so reviewers place us correctly.
- **Reframe the defence contribution** to the fresh parts: **rotation-cadence vs salt-reconstruction-time** timing
  analysis + **QRNG calibration-ceiling null result** — not "we propose salt rotation" (known).
- **Soften the gap claim**: "first *ECMP-specific articulation* of the source-detection-immunity that
  Crossfire/Coremelt/LDDoS established," not "no prior attack has this property."
- **Baselines to cite/measure against, not reinvent:** SipHash (keyed-hash baseline), SPIFFY/CoDef (reroute-based
  link-flood defences to contrast rekeying against), Crosby & Wallach (HashDoS ancestor).
- **Position within Moving-Target Defence** (sibling `study-ideas/Networking/4-mtd-sdn-hopping.md`): salt rotation is
  MTD on the ECMP hash → cite MTD lit (ACM MTD Workshop @ CCS, IEEE CNS); note the shared testbed enables a follow-on
  MTD hopping study as **future work**. Frame the epic as one game in the **unpredictability-as-primitive** umbrella
  (sibling `1-unpredictability-as-network-primitive.md`).
- **Verify-before-cite:** arXiv 2508.19283 (2025 DoS taxonomy) + some PDF-only slides were not body-verified (§10 caveat).

## Open decisions (epic §8)
- **Q5 — RESOLVED:** pre-build novelty scan done (epic §10). Full related-work section still written after P5.
- Q1: whether the controller-managed-salt point is measured (P5) or stays qualitative (write-up only) — **resolved
  qualitative for v1** (epic §8 Q1); keep as the fabric-wide-single-point-of-failure argument.

## Out of scope
Everything upstream (P1–P6). This plan is the paper.
