# Field 4: Quantum Scaling Laws for AI
### 10. Does expressivity via entanglement actually improve AI models as it scales?

## Honest framing (the gap)

This is **not** applying a known QC-improves-AI technique at bigger scale —
no such established technique exists. There is no well-documented mechanism
showing "more qubits → measurably better AI" on real tasks. What exists is
one contested theoretical claim plus mixed small-scale evidence.

The one plausible mechanism: a **parameterized quantum circuit (PQC)**
embedded as a layer in a classical network encodes data into qubit angles,
entangles it, and measures out — the state lives in a 2ⁿ-dimensional space,
so in principle it can represent feature correlations a classical layer
would need exponentially more parameters to match. This is the
**expressivity-via-entanglement** argument. It's mathematically real in the
abstract, but:
- nobody has shown real datasets actually need that kind of representation,
- quantum kernel methods (a close cousin) have a rigorous provable advantage
  only for engineered, adversarial datasets, not real-world data,
- a growing "dequantization" literature shows classical methods matching
  quantum methods on most practical data,
- serious researchers in the field (Schuld & Killoran) have argued quantum
  advantage may not even be the right question for QML.

So idea 10 is really: **test whether the expressivity-via-entanglement
theory shows up empirically as circuit resources grow**, using PQC layers as
the concrete testable instance of that theory — not "prove QC makes AI
better," which nothing currently justifies claiming in advance.

## Setup

- Fix one task/architecture. Vary only the PQC layer: qubit count (4→40,
  Qaptiva's exact-simulation range) and circuit depth, separately.
- Metric: task accuracy/loss, plus expressivity/entanglement diagnostics
  (these track the *mechanism*, not just the outcome).
- Fit a scaling curve with confidence intervals — many repeated runs per
  point, since small-qubit variance is high.
- **Phase 2, if signal appears:** extend the qubit-count axis onto real
  hardware (IBM Fez, 156-qubit Heron r2) to see if any simulated gain
  survives real noise. Note: IBM's own QML work on Fez tops out around ~50
  usable qubits for trainable circuits — physical qubit count ≠ usable
  qubit count. This phase needs separate IBM Quantum access, not just Perun
  time.

## Bull case

If entanglement/expressivity climbs with qubit count *and* task performance
climbs with it too, that's real evidence for the one mechanism theory
actually offers — a curve, not an anecdote. Very little honest empirical
work has tested this claim directly rather than assuming it.

## Bear case

- Range is far too narrow (4–40 qubits) to trust extrapolation — nowhere
  near the orders-of-magnitude range that made classical scaling laws
  convincing.
- Barren plateaus: gradients often vanish as qubits/depth increase, so the
  curve could bend the wrong way — already observed for the depth axis in
  recent literature.
- Noiseless simulation results may not transfer to noisy real hardware,
  where things generally get worse with scale, not better.
- Most prior QML studies never rigorously established scaling behavior at
  all — easy to mistake noise for a trend without careful confidence
  intervals.

## Likely outcome

Mixed, not clean: expressivity/entanglement probably does rise with qubit
count (reasonably well supported already), but task performance likely
flattens or gets noisy — especially with depth. A confidently-extrapolatable
clean trend is the least likely outcome.

## Value if null

High. It would separate "the mechanism is real but current circuit designs
don't exploit it" from "the mechanism doesn't help on real data" — a
genuinely open, useful distinction either way, and a rare rigorous test of a
claim usually asserted rather than measured.