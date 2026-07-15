# Idea 4 — Moving-Target Defence in SDN: If They Predict the Hop, They Never Lose You

## Pitch
Moving-target defence (MTD) rotates internal addresses and ports to hide assets. If the hop schedule
is PRNG-predictable, an attacker re-synchronizes and keeps tracking the target. A QRNG schedule is
unpredictable. Measure attacker hit-rate and time-to-track. Directly tests an active hot research
area (MTD) that almost always assumes "good randomness" and never checks the source — you fill the
gap the subfield left open.

**Paper strength score: 70/100** — fits an active subarea (MTD), which helps acceptance. Docked
because the likely result is "CSPRNG suffices," weakening the quantum angle. Good for a workshop,
harder for a main conference.

## How it becomes a study

**Research question:** How does the predictability of the address/port hop schedule affect an
attacker's ability to re-acquire a target under moving-target defence?

**Hypothesis:** A PRNG hop schedule is recoverable and trackable by the attacker; a TRNG schedule is not.

**Method:** An SDN controller rotates internal addresses according to the three randomness sources.
The attacker models the sequence (e.g. grid scanning + prediction) and tries to re-acquire the target
after each hop. Measure success.

**Baseline:** Predictable rotation (counter / weak PRNG) vs CSPRNG.

**Metrics:**
- Target re-acquisition success rate
- Time-to-re-track after a hop
- Scan coverage area needed to find the target
- Number of hops survived before the attacker locks on
- Controller overhead introduced by the rotation

**Novel contribution:** MTD literature almost always assumes "good randomness" and never isolates
the effect of the source — a direct gap.

**Target venues:** ACM MTD Workshop (co-located with CCS), IEEE CNS, NDSS workshop.

**Main weakness:** Same as the ECMP idea — CSPRNG probably suffices, so the result may be "the source
does not matter if it is cryptographically strong." That is still a publishable negative result, but
less exciting.

## High-level 5 steps to the goal
1. Build an SDN topology with a controller that rotates internal addresses/ports from a configurable source.
2. Implement the attacker: sequence modeling + prediction + re-acquisition logic.
3. Instrument hit-rate, time-to-track, and scan-coverage collectors.
4. Run the attacker against each hop-schedule source (PRNG/CSPRNG/QRNG) and knowledge level.
5. Compare tracking success across sources and write up, framed within the MTD subarea.

## Hardware

Reuses the same SDN bench as idea 3 — build once, run both studies.

### Minimalist setup (cheapest that still counts)
- 1 Linux box with Open vSwitch = the SDN switch doing address/port rotation.
- 1 server — Ryu controller running the MTD hop logic + reachable Q-EaaS API.
- 2 hosts — protected target (behind the rotating address) and attacker.

### Maximalist setup (impressive)
- Hardware OpenFlow switch(es) + ONOS controller doing the rotation at real forwarding speed.
- A small fleet of protected services (several SBCs) so the attacker must track many moving targets.
- Dedicated capture appliance on a port-mirror for precise, hardware-timestamped packet logs.
- Q-EaaS API feeding the QRNG hop schedule live, with a provenance dashboard.

### How to connect it physically
- Target service → switch. Its externally-visible address/port is rewritten by the controller on a schedule.
- Attacker host → same switch (or a leaf away) so all its scan/probe traffic crosses the rotation point.
- Controller → switch management port; controller holds the current hop mapping.
- Port-mirror of the attacker-facing port → capture NIC, so you log exactly what the attacker could observe.

### What you actually do with it
1. Controller rotates the target's address/port on an interval, driven by the chosen source.
2. Attacker continuously scans + tries to predict the next address from observed history.
3. Log every attacker probe and whether it hit the live target after each hop.
4. Compute hit-rate and time-to-re-track per source.
5. Swap source (predictable counter / weak PRNG / CSPRNG / QRNG), repeat, compare.

### Can it be done fully virtually?
**Yes.** Address/port rotation and the attacker's prediction are pure control-plane logic; Mininet
reproduces them faithfully. The scientific result does not depend on physical timing.

### Credibility impact of going virtual
**Low.** The finding is about predictability of the schedule, not link physics, so emulation is
honest and defensible. The only gain from hardware is realistic rotation latency and forwarding
overhead (a secondary metric). Virtual-only is acceptable for this one; hardware is a nice-to-have,
not a credibility requirement.
