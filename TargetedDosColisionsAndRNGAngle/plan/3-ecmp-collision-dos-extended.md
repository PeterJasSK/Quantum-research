# Idea 3 — ECMP Collision DoS: Predict the Salt, Melt the Link

## Pitch
Load balancers hash the 5-tuple to pick a path. A predictable hash salt (weak PRNG) lets an attacker
craft 5-tuples that all collide on a single link — a targeted denial of service. With a CSPRNG or
QRNG salt the attack fails. Measure link-load variance and victim throughput. The cleanest single
measurable result of all the ideas: one graph tells the whole story — attacker success versus the
randomness source. Cheap to build, hard to argue with. Best if you want a fast publishable win.

**Paper strength score: 72/100** — clean, measurable, one nice graph. Docked for a weak link to
quantum: CSPRNG alone suffices, so the contribution is "predictable salt is bad," not "quantum
helps." Frame it as an attack paper, not a QRNG paper. A good standalone paper, just not a "quantum" one.

## How it becomes a study

**Research question:** Does a predictable ECMP hash salt enable targeted single-link flooding, and
does an unpredictable salt prevent it?

**Hypothesis:** An attacker who knows or guesses the salt can craft 5-tuples that collide on one
link; with a CSPRNG/QRNG salt the attack fails.

**Method:** An SDN topology with ECMP (multiple parallel links). The attacker operates at three
levels of salt knowledge. Generate flows and measure how they distribute across links.

**Baseline:** Random CSPRNG salt; and a static / no-salt configuration.

**Metrics:**
- Maximum link utilization
- Load variance across links (Jain's fairness index)
- Victim-flow throughput under attack
- Number of attacker packets/flows needed to cause congestion
- Time-to-saturation of the targeted link

**Novel contribution:** An algorithmic-complexity attack on ECMP hashing — under-explored; most work
targets hash-table collisions, not load-balancing collisions.

**Target venues:** ACM ANCS, IEEE ICNP, IFIP Networking.

**Main weakness:** QRNG is not required here — CSPRNG is enough. The contribution is "predictable
salt is bad," not "quantum helps." Must be framed as an attack, with QRNG as one of three sources.

## High-level 5 steps to the goal
1. Build an SDN/ECMP topology with multiple parallel links and a configurable hash salt (PRNG/CSPRNG/QRNG).
2. Implement the salt-prediction attacker at three knowledge levels + a 5-tuple collision crafter.
3. Instrument per-link load, victim throughput, and time-to-saturation collectors.
4. Run the attack against each salt source and knowledge level; record when the link melts.
5. Produce the attacker-success-vs-source graph and write it up as an attack + mitigation paper.

## Hardware

The attack is about real link saturation, so real switches make it far more convincing.

### Minimalist setup (cheapest that still counts)
- 1 Linux box with 4+ NICs running Open vSwitch as the ECMP switch (software, but real packets).
- 1 server — runs the Ryu controller that sets the hash salt.
- 2 hosts (PCs or SBCs) — attacker and victim.
- Gigabit links so a single link can actually be saturated by a modest attacker.

### Maximalist setup (impressive)
- 2–3 hardware OpenFlow switches in a leaf-spine fabric = genuine multiple physical parallel paths.
- ONOS controller on a dedicated server.
- Hardware traffic generator (Ixia / Spirent) for line-rate background + attack traffic → citable numbers.
- 10G+ links so results scale to data-center-realistic speeds, not toy gigabit.
- Q-EaaS API server feeding the QRNG salt live.

### How to connect it physically
- Attacker host → leaf switch A. Victim host → leaf switch B. Different leaves on purpose.
- Leaf A ↔ spine ↔ Leaf B via 2–4 parallel links = the ECMP paths under test.
- Controller → switches' management ports over a separate control VLAN.
- Traffic generator → extra leaf ports to fill the fabric with realistic background load.
- Read per-link counters directly off the switches (OpenFlow port stats / SNMP).

### What you actually do with it
1. Set the hash salt from the chosen source (PRNG with known seed / CSPRNG / QRNG).
2. Attacker (knowing/guessing the salt) crafts 5-tuples all hashing to the same egress link.
3. Push that flood; watch one physical link hit 100% while others sit idle.
4. Measure victim throughput collapse and packets-needed-to-saturate.
5. Swap salt source, repeat; plot attacker success vs source.

### Can it be done fully virtually?
**Yes, cleanly.** Mininet + Open vSwitch reproduces ECMP hashing and flow collisions faithfully; the
hash algorithm and salt logic are identical to hardware. A virtual result is scientifically valid here.

### Credibility impact of going virtual
**Low-to-moderate.** The mechanism is honest in emulation, so the finding stands. What you lose is
scale realism — a reviewer may ask "does this hold at 10G on real silicon?" Hardware (even one real
switch, or a traffic-generator run) closes that gap. Virtual is fine for the core result; add one
hardware confirmation run to pre-empt the scale critique.

---

## Why this describes a genuinely new attacker

The original pitch frames this as a precision attack versus a volumetric one. That framing is
correct but incomplete. The stronger and more specific claim is this:

**This attacker is specifically shaped to be invisible to the two defences that stop every other
DoS attacker: rate limiting and throttling.**

Rate limiting caps how much bandwidth a single source can consume. It fails here because the
precision attacker does not need to send a lot of traffic — only traffic that lands on the right
link. No individual source exceeds any threshold. The rate limiter never fires.

Throttling drops or deprioritises a source after too many connections or requests. It fails here
because the attacker varies their 5-tuples deliberately — many different source/destination
combinations, all crafted to hash to the same bucket. From the throttle's perspective this looks
like organic traffic diversity from many different sources. There is no single source to throttle.

This means the attacker does not just happen to evade these defences incidentally — the attack is
structurally immune to source-based detection because there is no anomalous source. The damage is
done by mathematical placement, not by any behaviour that a source-watching defence can observe.

That is a new attacker class in a precise sense: one that occupies the gap between rate limiting
and throttling, the two tools that define current DoS defence practice.

---

## What the new solution is and why it is categorically different

Salt rotation with a CSPRNG or QRNG source is not a better rate limiter or a smarter throttle.
It operates at a completely different layer:

- Rate limiting and throttling act on **traffic behaviour** — they watch what flows are doing
  and respond after the fact.
- Salt rotation acts on **the hash function itself** — it changes the mapping that the attacker's
  pre-computed collisions depend on, before any traffic is evaluated.

A packet crafted to collide on link 2 under salt A lands on link 3 under salt B. The attacker's
work is invalidated at the moment of rotation, not detected and blocked — invalidated. This means
the defence has no false-positive problem (legitimate traffic redistributes fairly across links,
Jain's index stays high) and no detection latency (there is nothing to detect; the attack simply
stops working).

The rotation frequency is the tunable parameter. The attacker needs time to reconstruct the new
salt and recompute a collision set. If rotation happens faster than that reconstruction window,
the attack cannot sustain saturation regardless of attacker knowledge level. This gives operators
a concrete, measurable knob tied directly to the attacker's computational constraints.

QRNG's role here is as a calibration ceiling: it shows what happens when the salt is provably
non-reconstructable by any means, not just computationally hard. It does not improve on CSPRNG
in practice, but it closes the theoretical gap and provides a reference point for what "perfect
randomness" buys you — which turns out to be identical outcomes to CSPRNG in this threat model,
and that null result is itself a finding worth stating.

---

## Specific experiments required to demonstrate the new attacker and new solution

These experiments are designed to be run on the simulated Mininet/OVS topology. The simulation
is sufficient to demonstrate feasibility — the mechanism (hash function, salt, bucket selection,
link utilisation) is identical in emulation. The goal is not to prove scale but to prove the
mechanism is real and the defence works.

### Experiment 1 — Baseline: standard defences work against a volumetric attacker

**Purpose:** Establish that rate limiting and throttling are correctly configured and effective
against a naive flood. This is the control condition. Without it, a reviewer cannot distinguish
"our attacker evades defences" from "the defences were misconfigured."

**Setup:** Enable per-source rate limiting and per-source connection throttling on the OVS/Ryu
topology. Launch a naive volumetric flood (same source IP, no 5-tuple variation, high packet
rate) toward the victim.

**Expected result:** The flood is stopped or heavily degraded by the active defences. Link
utilisation does not reach saturation. Victim throughput is protected.

**What this proves:** The defences are real and working. Their subsequent failure against the
precision attacker is meaningful.

---

### Experiment 2 — The precision attacker evades rate limiting

**Purpose:** Show that the collision-based attacker causes link saturation while staying below
the rate-limiting threshold on every individual source.

**Setup:** Same rate limiting active as Experiment 1. Launch the full-knowledge precision
attacker (salt known, 5-tuples crafted to collide on target link) with per-source traffic capped
at the same threshold used in Experiment 1 — but spread across multiple attacker sources, each
individually compliant.

**Expected result:** Target link reaches saturation. Victim throughput collapses. No individual
source exceeds the rate limit. The rate limiter does not fire on any source.

**What this proves:** Rate limiting is structurally insufficient against this attacker. The
defence cannot be tuned to catch it without also blocking legitimate traffic, because there is
no per-source anomaly to catch.

---

### Experiment 3 — The precision attacker evades throttling

**Purpose:** Show that the collision-based attacker causes link saturation while no individual
flow triggers throttling rules.

**Setup:** Same throttling active as Experiment 1. Launch the full-knowledge attacker with
5-tuples varied across many source ports and destination combinations — all crafted to collide
on the target link, but each individually a distinct, valid-looking flow.

**Expected result:** Target link reaches saturation. Victim throughput collapses. No individual
flow crosses the throttling threshold. The throttle does not fire on any flow.

**What this proves:** Throttling is structurally insufficient against this attacker for the same
reason as rate limiting — there is no anomalous source or flow to throttle.

---

### Experiment 4 — Salt rotation defeats the attacker, rate limiting and throttling do not need to

**Purpose:** Show that salt rotation is sufficient on its own to defeat the precision attacker,
and that it does so with zero cost to legitimate traffic.

**Setup:** Run the full-knowledge attacker against three configurations in sequence:
- No salt rotation, weak PRNG salt (attack succeeds — replicating the original result)
- Salt rotation active, CSPRNG source (attack fails — attacker cannot maintain collision set)
- Salt rotation active, QRNG source (attack fails — same outcome, different entropy source)

Measure Jain's fairness index and victim throughput in each configuration under both attack
traffic and clean background traffic.

**Expected result:** Under weak PRNG, saturation occurs quickly. Under CSPRNG/QRNG rotation,
links stay fair and victim throughput is unaffected regardless of how long the attacker runs.
Under background traffic only (no attack), all three salt configurations produce identical fair
distribution — rotation has no cost in the non-attack case.

**What this proves:** Salt rotation defeats the attacker at the mechanism level, not the
behaviour level. It also proves the defence is operationally neutral — it does not degrade
legitimate traffic.

---

### Experiment 5 — Rotation frequency curve

**Purpose:** Quantify the relationship between salt rotation frequency and attacker success.
This produces the paper's second key graph alongside the attacker-success-vs-source graph.

**Setup:** Fix the attacker at partial knowledge level (knows algorithm, guesses seed space).
Vary the rotation interval from very slow (minutes) to very fast (seconds or sub-second).
Measure time-to-saturation and packets-needed-to-saturate at each rotation interval.

**Expected result:** A curve showing that below a threshold rotation frequency the attacker
can sustain saturation; above that threshold the attack fails entirely. The threshold maps
directly to how long it takes the attacker to brute-force the seed space — a number that can
be derived analytically and then confirmed empirically.

**What this proves:** Operators have a concrete, principled knob. Rotate faster than your PRNG's
seed space can be exhausted in, and the attack fails. The graph gives a specific number, not a
vague recommendation.

---

### Why a simulated network is sufficient for all five experiments

The five experiments are designed to demonstrate mechanism, not scale. The questions being
answered are:

- Does the attack evade rate limiting and throttling? (Yes/No — mechanism question)
- Does salt rotation defeat the attack? (Yes/No — mechanism question)
- What is the rotation frequency threshold? (A ratio — mechanism question)

None of these questions require 10G links or real ASIC hardware to answer, because none of
them depend on absolute throughput numbers. They depend only on the hash function behaving
correctly (which OVS guarantees) and on rate limiting/throttling being faithfully modelled
(which Mininet/OVS Ryu flow rules do correctly).

The one scale caveat to acknowledge honestly in the paper: the absolute time-to-saturation
numbers will be lower on real 10G hardware than on a simulated gigabit topology. But the
*relative* numbers — precision attacker versus volumetric attacker, weak PRNG versus CSPRNG
rotation — are scale-invariant ratios. Those are the findings. The absolute numbers are context.

---

## How these experiments strengthen the paper

### From 72/100 to a stronger paper

The original score of 72/100 was docked primarily for a weak link to quantum and a finding
that "predictable salt is bad" is not novel enough on its own. The five experiments above
address the underlying structural weaknesses, not just add more data:

**The contribution is no longer just "predictable salt is bad."**
It is now: "this attack class is structurally immune to the two defences that define current
DoS practice, and here is a mechanism-level defence that closes the gap, with empirical
characterisation of the parameters that matter."

**The QRNG framing becomes honest.**
QRNG is no longer a solution presented as necessary — it is a calibration ceiling that proves
CSPRNG is sufficient and gives a principled answer to "how much unpredictability do you
actually need?" The null result (QRNG buys nothing over CSPRNG here) is worth stating
explicitly, and honest null results are well-regarded in measurement papers.

**The attacker is now defined by what it evades, not just how it works.**
Experiments 1–3 create the logical structure the paper needs: here is the standard defence,
here is why it fails, here is what does work. That is a complete argument, not just a
demonstration.

**The rotation frequency curve is a citable, actionable result.**
A graph showing the exact rotation interval at which the attack fails — anchored to the
attacker's reconstruction time — gives practitioners something to implement. "Use CSPRNG"
is advice; "rotate faster than N seconds given seed space S" is a specification.

### What this changes about the paper's identity

The paper shifts from:

> A measurement of ECMP hash-salt predictability as an attack vector

To:

> A characterisation of a new attacker class that occupies the gap between rate limiting and
> throttling, with an empirical demonstration of a mechanism-level defence and a quantified
> rotation-frequency specification for practitioners

That is a stronger venue pitch, a cleaner related-work position, and a more defensible
contribution statement. The simulated topology is sufficient to support all of it.

---

## Animated web demonstration — how it shows all of this

The web demonstration has one job: make the logical structure of the five experiments visible
to someone who has not read the paper. It does this in three scenes shown in sequence.

### Scene 1 — Standard defences working (Experiment 1 context)

The viewer sees the topology: attacker, switch, four parallel links, victim. A naive flood
launches — many packets from one source. The rate limiter fires visually (a red indicator on
the attacker node). The links stay balanced. The victim throughput bar stays healthy. The
viewer understands: standard defences work against standard attackers.

### Scene 2 — The precision attacker evading both defences (Experiments 2 and 3)

The attacker mode switches to "precision." The rate limiter indicator stays green — no
individual source is over threshold. The throttle indicator stays green — no individual flow
is suspicious. But one link bar climbs steadily to red while the others stay idle. The victim
throughput bar collapses. The viewer sees the gap: everything looks fine to the defences,
but the victim is being hit anyway.

The salt value is shown on screen — a predictable, repeating number under weak PRNG. The
viewer can see why the attacker knew where to aim.

### Scene 3 — Salt rotation defeating the attack (Experiment 4 and 5 context)

The salt source switches to CSPRNG with rotation active. The same attacker script runs. The
link bars scatter randomly — no single link climbs. A rotation event fires (visible on screen
as the salt value changing to a new opaque number) and the attacker's previously crafted
5-tuples disperse. The victim throughput bar stays healthy. The rate limiter and throttle
were never needed.

A rotation frequency slider lets the viewer slow the rotation down until the attacker
re-establishes saturation, then speed it back up until saturation collapses — showing the
threshold curve from Experiment 5 as a live interactive result rather than a static graph.

When QRNG is selected the page shows the entropy source provenance — timestamp, byte count,
API endpoint — making the distinction between CSPRNG and QRNG visible without overstating it.

### Why this structure makes the paper stronger

The animated demo is not supplementary material — it is the paper's argument made visual.
A reviewer or conference attendee who watches the three scenes understands the contribution
before reading a word of the paper. The demo also serves as a reproducibility artefact:
because the JS hash and salt functions are identical to the Python ones in the testbed,
anyone can verify the mechanism in a browser without running the full Mininet stack.

The demo is planned in two tiers as described in the companion planning document:
Tier A (browser-only, immediate) for talks and the paper supplementary site, and Tier B
(connected to the real testbed via WebSocket) for live demonstrations where the numbers on
screen are real OpenFlow port-stat counters from OVS, not simulated values.
