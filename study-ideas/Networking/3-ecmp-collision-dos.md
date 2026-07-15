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
