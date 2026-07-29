# Viz Idea 5 — Gossip Overlay Resilience: Randomized Peer Selection Under Attack

**Tag: NON-QUANTUM · viz · effort: medium · networking sibling to the ECMP work**

## Pitch
Peer-to-peer systems (gossip/epidemic dissemination, blockchain relay, DHT overlays) survive because
each node picks random peers to talk to. If that peer-selection PRNG is predictable, an adversary can
**eclipse** a node — surround it with attacker peers and cut it off, or steer the gossip wavefront to
partition the network. Simulate epidemic dissemination on a randomized overlay, run an eclipse /
partition attacker against predictable vs unpredictable peer selection, and animate the infection
wavefront being throttled and then healed. It is the ECMP story moved up the stack: same
"predictable randomness is an attack surface" thesis, a new and hot domain (P2P / blockchain).

**Paper strength score: 76/100.** Eclipse attacks are a live, cited problem (Bitcoin/Ethereum P2P);
the "does the *quality* of the peer-selection source change eclipse difficulty" angle is
under-examined and measurable. Honest expected result mirrors the portfolio: CSPRNG suffices for
statistics, the real fix is unpredictable+authenticated selection state — QRNG contributes
provenance. Frame as an attack + defense paper, strong graph-animation payload.

## How it becomes a study
**Research question:** How does the predictability of randomized peer selection affect an
adversary's cost to eclipse a target node or partition a gossip overlay?

**Hypothesis:** Attacker success falls sharply from PRNG → CSPRNG and saturates there; the residual
win comes from unpredictable + authenticated selection, not raw entropy volume.

**Method:** Simulated overlay (n=10²–10⁴ nodes) with pluggable peer-selection source. Epidemic
(SI/SIR) dissemination. Attacker games: eclipse a target, partition the graph, delay global
coverage. CSPRNG baseline; predictable-PRNG and QRNG arms.

**Metrics:**
- Eclipse success probability + attacker peers needed vs target
- Time-to-full-dissemination (coverage 99%) under attack
- Largest-connected-component fraction after partition attempt
- Message overhead / redundancy at fixed reliability

## THE VISUALIZATION (the star)
- **Infection wavefront**: force-directed graph, color spreads node-to-node; watch coverage race
  across the topology.
- **The eclipse**: attacker nodes creep in around a target and its neighborhood goes dark while the
  rest stays lit — predictable-source run; then the unpredictable run refuses to eclipse.
- **Partition slider**: raise attacker budget and watch the giant component crack, with the
  largest-component gauge tracking live.
- **A/B wavefront race**: predictable vs unpredictable, same seed of infection, same clock.
- D3 / force-graph, self-contained HTML — same delivery pattern as viz-3.

## Connection to what I already did
- Direct sibling of `TargetedDosColisionsAndRNGAngle` and the `net-1` unpredictability-primitive
  umbrella: same thesis, higher layer, fresh attack surface.
- Reuses the pluggable-seed-backend design (PRNG/CSPRNG/QRNG) from the ECMP testbed.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** *How does the predictability of randomized peer selection change an
adversary's cost to eclipse a target node or partition a gossip overlay?*

**Single defended claim:** Eclipse cost jumps sharply PRNG→CSPRNG and saturates; the residual
defense is unpredictable + authenticated selection *state*, so entropy provenance — not volume —
sets the security floor.

**Why it fits 6–8 pp:** one overlay simulator, pluggable source, two attacker games (eclipse,
partition), one headline figure (wavefront race / eclipse-goes-dark) + attacker-cost curve. Maps to
a cited, active threat (Bitcoin/Ethereum P2P eclipse) — reviewers already care.

**Target venue:** IEEE Transactions on Network and Service Management, IEEE Communications Letters,
or an IEEE security workshop.

**Compelling-study likelihood: 78/100** — hottest topic of the five, cited real-world threat,
clean measurable attacker-cost curve, strong animation. Highest standalone-publishability of the
new visualization ideas.
