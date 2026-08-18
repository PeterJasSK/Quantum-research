# QH Idea 12 — Depth Inverts the Answer: at what routing depth does a SWAP-routed long-range gate flip the sign of a correlation observable?

**Tag: QUANTUM · qh · effort: low-medium**

> **Reframed 2026-08-17.** The original version asked whether a teleported gate diverges
> from its SWAP twin (the "sign anomaly"). That is now **resolved** (`viz-9`,
> `conclusion_teleportation_longrange.md` §0, `code/sim_ideal_sign.py`): the ideal bond sign
> is **negative**, the teleport circuit is a logical CNOT, teleport hardware reproduces the
> correct sign, and the **SWAP ladder is the arm that fails** — its depth-31 routing
> decoheres the correlation to a floor whose residual reads the *wrong* sign. This idea keeps
> the genuinely useful piece: characterize *how depth turns a correct-signed long-range
> correlation into a wrong-signed one*, as a caution for SWAP-routed compilation.

## Pitch
A correctness result nobody expects from "just routing": on `ibm_marrakesh`, the SWAP-routed
implementation of a long-range CNOT did not merely *attenuate* the ideal (negative) bond
correlation — at depth 31 it **inverted its sign** to a drift-dependent positive floor, while
the constant-depth teleported implementation kept the correct sign. Decoherence alone shrinks
a correlation toward zero; a **sign flip** means the deep routing injects a systematic, not
just noise. This study maps the effect: sweep routing depth (SWAP distance) and find the
threshold where sign-integrity breaks, i.e. where a compiler's routing choice silently
changes the *answer*, not just the fidelity.
**Paper strength score: 74/100** — a concrete, surprising, citable caution for NISQ
compilation (routing can flip an observable's sign), cheap to produce, and anchored by an
already-resolved ground truth. Docked because the cleanest demonstration is one gate on one
backend; generality needs the depth sweep + a second device.

## How it becomes a study
**Research question:** As SWAP-routing depth grows with distance, at what depth does the
measured sign of a long-range correlation observable diverge from its exact ideal — and is
the crossover predicted by the accumulated two-qubit-gate error along the route?
**Hypothesis:** Below a depth threshold the SWAP-routed correlation keeps the correct
(negative) sign; above it, decoherence + coherent routing error drive it through zero to a
wrong-signed floor. The threshold scales inversely with the per-gate error rate.
**Method:** Fix the ideal with an exact noiseless simulation of the direct-CX bond
(`code/sim_ideal_sign.py`, already gives negative). Then, for SWAP distances `d = 6…36`
(depth ~15…85) and the constant-depth teleport at matched distance: (1) **noisy Aer** with a
depolarizing model scaled to live calibration → locate the sign-flip depth in simulation;
(2) a small **hardware** confirm at 2–3 distances. Read `c(d)` at the bonded qubits; the
teleport arm is the constant-depth control that should keep the sign throughout.
**Baseline:** the exact noiseless ideal (correct sign, no noise) and the constant-depth
teleport arm (empirically sign-faithful).
**Metrics:** sign and magnitude of `c(d)` vs routing depth for SWAP; the sign-flip depth
threshold; correlation of the threshold with cumulative 2q-gate error; teleport's
sign-integrity across the same distances.
**Novel contribution:** evidence that SWAP-routing depth can **invert**, not just degrade, a
correlation observable — so routing depth is a *correctness* concern, not only a fidelity
one — with a measured depth threshold and the constant-depth teleport that avoids it.

## Connection to what already exists
Resolves and absorbs the sign anomaly from `viz-9` /
`QuantumLife/research/conclusion_teleportation_longrange.md` §0/§4b, reusing
`code/sim_ideal_sign.py`, `_swap_cx`, `_teleport_cx`, and the `bond_correlations` metric.
Complements `qh-10` (routing benchmark: cost/fidelity crossover) by adding the
*sign-integrity* axis, and `qh-11` (entanglement reach) by explaining what "dead at d=36"
actually looks like (a sign-inverted floor, not just zero).

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** The ground truth is already established, the decisive sim is written, and the
finding — "routing depth can flip the sign of your answer" — is a crisp, memorable caution a
compiler audience will cite. The teleport arm gives a clean constant-depth control in the
same figure.
**Bear:** The sign flip may be partly a marrakesh-calibration artifact; on a better-calibrated
chip SWAP might merely attenuate to zero without inverting, weakening "inversion" to "loss".
Still publishable, less striking.
**Likely outcome:** A depth threshold in the noisy model (somewhere between the depth-9
teleport and depth-31 SWAP) where SWAP's sign becomes unreliable, confirmed at one or two
hardware distances, with teleport sign-faithful throughout.
**Value if null:** If SWAP only attenuates (never inverts) once calibration is good, the
honest result is "the marrakesh inversion was a device/drift artifact" — which itself
corrects this project's record and bounds when SWAP-routing sign is trustworthy.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Can SWAP-routing depth invert the sign of a long-range correlation
observable, and at what depth? **Single defended claim:** deep SWAP routing can flip a
correlation's sign (not just shrink it), so routing depth is a correctness concern; a
constant-depth teleported gate preserves the correct sign. **Why it fits 6–8 pp:** one exact
ideal, one depth sweep (sim + small hardware), one "sign vs depth" figure with the teleport
control. **Target venue:** IEEE Quantum Week (QCE) / quantum-software reliability track.
**Compelling-study likelihood: 74/100.**
