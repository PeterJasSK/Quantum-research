# Viz Idea 3 — DNS Poison Race: How Many Entropy Bits Stop a Cache Poisoner?

**Tag: NON-QUANTUM · viz · effort: medium · networking, transport/DNS layer**

## Pitch
A DNS resolver accepts a forged answer only if the attacker guesses the 16-bit transaction ID **and**
the source port before the real reply lands. Randomize both well and the off-path attacker must win a
race across a ~2³² space; randomize them badly (predictable PRNG, fixed port, or the SAD-DNS
side-channel that leaks the port) and the window collapses to something forgeable. Build a resolver
race simulator, sweep the *effective entropy* of the TXID+port draw across sources
(fixed-port / weak-PRNG / CSPRNG / QRNG), and animate the poisoning race: attacker floods guesses
while the legitimate answer flies back — who arrives first, and how often. One graph: poisoning
success vs entropy bits, with a cliff.

**Paper strength score: 80/100.** A real, cited, still-live threat (Kaminsky 2008; SAD DNS
2020–2021 revived it by leaking the port), a sharp single-variable question, and a hard measurable
(poisoning probability). Same honest portfolio thesis: CSPRNG suffices for the *statistics*, the
real failures are provenance/state (fixed ports, predictable PRNG, side-channel leakage) — QRNG adds
certified unpredictability, not magic. Different layer from the ECMP paper, so no overlap.

## How it becomes a study
**Research question:** *How does the effective entropy of DNS transaction-ID + source-port selection
determine an off-path attacker's cache-poisoning success rate, and where is the security cliff?*

**Hypothesis:** Poisoning success falls off exponentially with effective entropy bits; the dominant
real-world risk is not weak statistics but entropy *reduction* — fixed ports and side-channel port
leakage (SAD DNS) — which no amount of source quality fixes.

**Method:** Discrete-event resolver/attacker simulator (arrival races, retransmit timers, birthday
amplification via multiple in-flight queries). Pluggable TXID+port source: fixed-port,
weak-PRNG (LCG / predictable seed), CSPRNG (`/dev/urandom`), QRNG (QEaaS bytes). Model the SAD-DNS
port-leak as an entropy-reduction knob. Sweep effective bits and attacker send-rate.

**Metrics:**
- Poisoning success probability vs effective entropy bits (headline cliff graph)
- Expected forgery packets / time-to-poison at fixed entropy
- Birthday-attack amplification factor (parallel queries) vs entropy
- Sensitivity to port-leak (SAD-DNS): success vs bits-of-port-leaked

## THE VISUALIZATION (the star)
- **The poison race**: split timeline — attacker's forged-answer stream sprays guesses at the
  resolver while the authoritative reply races back; a hit lights the cache red (poisoned) or green
  (legit wins first). Replayable per source.
- **Entropy cliff**: animated curve drawing itself as the entropy slider drops — flat-safe, then a
  sudden fall to near-certain poisoning. The whole thesis in one motion.
- **SAD-DNS reveal**: toggle the side-channel port leak and watch the safe CSPRNG curve collapse —
  shows provenance/state beats raw source quality.
- **Guess-space heatmap**: TXID × port grid, attacker coverage filling in over time vs the single
  correct cell. Self-contained HTML/Canvas — same delivery pattern as the ECMP web demo.

## Connection to what I already did
- Reuses the pluggable-seed-backend design (PRNG/CSPRNG/QRNG) and the "provenance not magic" thesis
  from `TargetedDosColisionsAndRNGAngle`, one layer up — no overlap with the shipped ECMP web demo.
- QRNG arm sourced from the **QEaaS API** (no new QC runs); CSPRNG from `os.urandom`, PRNG seeded.
- Sibling to `viz-5-gossip-overlay-resilience` and the `net-1` unpredictability-primitive umbrella.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** *How does the effective entropy of DNS TXID + source-port selection set an
off-path cache-poisoning success rate, and does entropy reduction (fixed ports, SAD-DNS port leak)
matter more than the randomness source itself?*

**Single defended claim:** Poisoning probability is governed by *effective* entropy bits, not the
generator brand; the exploitable failures are structural entropy loss (fixed port, predictable
PRNG, side-channel leakage), and QRNG's role is certified provenance of the draw, not a lower
poisoning rate versus CSPRNG.

**Why it fits 6–8 pp:** one simulator, one swept variable (effective bits), four source arms + a
SAD-DNS knob, one headline cliff figure + a race animation. Cited threat, sharp result, no hardware.

**Target venue:** IEEE Communications Letters, IEEE Transactions on Network and Service Management,
or an IEEE security workshop.

**Compelling-study likelihood: 80/100** — real cited threat kept alive by SAD-DNS, single crisp
measurable with a dramatic cliff, and a memorable race visual. Strongest standalone networking paper
of the visualization set alongside `viz-5`.
