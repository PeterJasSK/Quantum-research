# Idea 1 — Unpredictability as a Network Primitive

## Pitch
One testbed, three attacker games (ECMP flooding, moving-target address hopping, sampling-window
evasion) plus a boot-entropy fix. Swap PRNG / CSPRNG / QRNG as the seed backend and measure who
breaks. The full arc from thesis to paper: first bust the hype, then land one real fix. The novelty
is honesty — reporting where QRNG *loses* (crypto games, where CSPRNG ties) is what makes reviewers
believe the one place it *wins*.

**Paper strength score: 78/100** — strong, honest, publishable. Docked for breadth: a conference
wants one thing deep, not five things shallow. Better suited to a journal or the dissertation
umbrella than a single conference paper.

## How it becomes a study

**Research question:** When does the *source* of randomness (PRNG vs CSPRNG vs QRNG) measurably
change a networking outcome, and when does it not?

**Hypothesis:** Randomness *quality* saturates at CSPRNG; QRNG adds measurable value only where the
real issue is *provenance and state management*, not statistics.

**Method:** A single emulated testbed (Containernet / Mininet) with a pluggable seed backend
exposing three sources. Each of the three attacker games below runs as a controlled experiment
against a CSPRNG baseline.

**Baseline:** CSPRNG (`/dev/urandom`) as the gold standard to measure against.

**Metrics (the full set across all sub-experiments):**
- Attacker success rate (per game)
- Link-load variance and max-link utilization (ECMP game)
- Jain's fairness index across parallel links
- Victim-flow throughput
- Attacker re-acquisition / time-to-track a target (MTD game)
- Scan coverage area (MTD game)
- Sampling-evasion success rate and congestion-estimate bias/variance vs ground truth (sampling game)
- Min-entropy of generated keys (bits)
- Duplicate / colliding key count across N cold boots (boot-entropy fix)
- Controller / collector overhead introduced by each source

**Novel contribution:** A systematic map of where the randomness source matters and where it does
not, across multiple networking mechanisms — no one has published this cross-mechanism comparison.

**Target venues:** IEEE CNSM, IEEE NOMS, ACM SOSR.

**Main weakness:** Scope. A reviewer will say "too much, too shallow." Risk that no single part is
deep enough for a conference slot.

## High-level 5 steps to the goal
1. Build the Containernet/Mininet topology with a pluggable seed backend (PRNG / CSPRNG / QRNG-from-API).
2. Implement the three attacker scripts (ECMP flooding, MTD tracking, sampling evasion) + metric collectors.
3. Build the cold-boot entropy harness for the positive-result fix.
4. Run all experiments across the three sources and attacker knowledge levels; tabulate wins and losses.
5. Write up honest negative results first, then the boot-entropy fix as the payoff.

## Hardware

This is the union of ideas 2 + 3 + 4 on one bench. If you have the gear for those, you have it for this.

### Minimalist setup (cheapest that still counts)
- 1 server/workstation — runs the SDN controller (Ryu) + the Q-EaaS API.
- 1 OpenFlow-capable switch (or a Linux box with 3+ NICs running Open vSwitch).
- 3 Raspberry Pi / SBC — one attacker, one victim, one headless boot-entropy target.
- 1 managed switch with a port-mirror for capture.

### Maximalist setup (impressive)
- Rack: SDN controller cluster (3 servers, ONOS in HA) + dedicated API server.
- 2–3 hardware OpenFlow switches wired in a multi-path (leaf-spine) topology so ECMP has real parallel links.
- Hardware traffic generator (Ixia / Spirent) for line-rate, citable throughput numbers.
- 5–8 SBCs / headless boxes as the device fleet (boot-entropy) + attacker + victims.
- A real QRNG appliance or your quantum job pipeline feeding the API, shown live on a dashboard.

### How to connect it physically
- Controller server → switch management port (OpenFlow control channel, separate VLAN from data).
- Switch data ports → leaf-spine fabric: victim and attacker hang off different leaf switches so their
  traffic must cross the multi-path core (that's where ECMP/MTD decisions happen).
- Boot-entropy SBCs → an access switch, plus a switched PDU (or manual power) so you can force cold boots.
- Capture switch port-mirror → a collector NIC on the controller server.
- Q-EaaS API reachable from every device over the management VLAN.

### What you actually do with it
Run all three attacker games back-to-back on the same fabric, then the cold-boot campaign on the SBC
fleet. One physical setup, four datasets, one honest cross-mechanism paper.

### Can it be done fully virtually?
**Partly.** Games 3/4/5 run fine in Mininet/Containernet. The boot-entropy fix does NOT — see idea 2.
So a pure-virtual version of this combined study is incomplete: it can show the negative results but
not the one positive result that is the payoff.

### Credibility impact of going virtual
**High cost.** The combined paper's whole selling point is the honest arc ending in a real fix. Drop
the hardware and you drop the payoff — you are left with "randomness source rarely matters," a weaker,
mostly-negative paper. Keep at least the boot-entropy part on real hardware.
