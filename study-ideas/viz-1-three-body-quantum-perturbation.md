# Viz Idea 1 — Three-Body Quantum Perturbation: Where Chaos Meets the Quantum Coin

**Tag: QUANTUM · viz-flagship · effort: medium-high**

## Pitch
The gravitational three-body problem is the poster child of deterministic chaos: two nearly
identical starts diverge exponentially. Now make the *nudge* quantum. Seed the initial-condition
jitter (and optional mid-flight micro-kicks) from real QRNG hardware, and compare the resulting
trajectory ensembles against PRNG- and CSPRNG-seeded jitter of identical magnitude. The physics is
century-old and gorgeous; the twist is provenance — does the *source* of the perturbation change the
*shape* of the divergence, or only its label?

**Paper strength score: 74/100.** The honest answer is likely "the statistics of a good source are
indistinguishable in the ensemble spread" — which is itself the publishable point: chaos amplifies
any unpredictable seed equally, so QRNG buys **auditable provenance of the nudge**, not faster
divergence. That reframing (same story as the ECMP paper) is what makes it defensible. Docked
because the null result must be sold well; rescued by being the most visually striking artifact in
the whole portfolio.

## How it becomes a study
**Research question:** Does the entropy *source* of an initial perturbation measurably change the
divergence statistics of a chaotic three-body ensemble, or does chaos wash the source out?

**Hypothesis:** Beyond CSPRNG quality the ensemble Lyapunov spectrum saturates; QRNG adds
*certified* unpredictability of the perturbation, not different dynamics.

**Method:** Fixed figure-eight / Pythagorean initial configuration. Draw N=10³–10⁴ perturbation
vectors of fixed norm ε from each source (PRNG / CSPRNG / QRNG). Integrate with a symplectic /
high-order adaptive integrator (IAS15-style) to a fixed horizon. Repeat across ε decades.

**Metrics:**
- Finite-time maximal Lyapunov exponent (ensemble mean + distribution)
- Time-to-ejection / first close-encounter distribution
- Phase-space spread (covariance volume) vs time
- KS / energy-distance tests between source ensembles (the real hypothesis test)
- Symplectic energy-drift audit (integrator sanity)

## THE VISUALIZATION (the star)
- **Divergence fan**: a single seed explodes into a translucent bundle of orbits; the bundle blooms
  from a thread into a cloud — one animation communicates chaos instantly.
- **Phase-space ribbons**: 3D trails with time-colored velocity, WebGL (Three.js), scrubbable.
- **Lyapunov weather map**: heatmap of divergence rate over the ε × time plane, one panel per source.
- **Source A/B/C triptych**: same figure, three sources side by side — the "spot the difference"
  panel that carries the null-result argument.
- Export: MP4 orbit reels + interactive HTML (reuses the QuantumLife `web/` pattern).

## Connection to what I already did
- Consumes the QRNG hardware pipeline (`qrng_bell_pairs.py`) and the quality battery — the
  perturbation stream is exactly the entropy product of the thesis.
- Fills the empty `ThreeBodyQuantumPerturbation/` project folder already in the repo.
- Same "provenance not magic" thesis as `TargetedDosColisionsAndRNGAngle` — portfolio coherence.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** *Does the entropy source of an initial perturbation alter the divergence
statistics of a chaotic three-body ensemble, or does deterministic chaos render every unpredictable
source equivalent?*

**Single defended claim:** Beyond CSPRNG quality the ensemble Lyapunov spectrum is statistically
indistinguishable across sources; therefore QRNG's contribution to chaotic seeding is *certifiable
provenance of the nudge*, not different dynamics.

**Why it fits 6–8 pp:** one integrator + one fixed configuration, three source arms, one headline
figure (the divergence fan / source triptych), 2–3 metrics (FT-Lyapunov, ejection-time KS test).
A single crisp null-plus-reframe contribution — the archetypal short-paper shape.

**Target venue:** IEEE Access / IEEE Transactions on Computational Social Systems (viz angle) or a
physics-of-computation letter; also a strong dissertation chapter.

**Compelling-study likelihood: 68/100** — visually unforgettable and technically clean, but the
result is a null unless the provenance reframing is sold hard. High reward, real reviewer risk.
