# VIZ Idea 10 — Entropy With Proof: teleportation byproduct bits that certify their own quantum randomness

**Tag: QUANTUM · viz · effort: medium**

## Pitch
The repo's prior QRNG work (`qrng-eaas`, `ErrorDetectionVSRawBits`,
`CalibrationGuidedHighYieldQRNG`) all end at "here are bits that pass the health tests —
trust us they're quantum." This flips that: a teleportation run emits **two Bell-measurement
bits that are Born-random**, and the *same* run — if the Bell pair genuinely violates CHSH —
**certifies** that those bits are quantum, not classically predictable. Entropy that carries
a live per-batch proof of its own quantumness (device-independent-*flavoured*), turning
"trust us" into "here is the CHSH receipt for this block." Not another QRNG — a
**self-certifying** one.
**Paper strength score: 73/100** — genuinely differentiates from the repo's earlier QRNG
studies and lands in a respected area (DI-QRNG); docked for the overclaim trap (a same-chip
test is not loophole-free) and a possibly small certified-bit rate.

## How it becomes a study
**Research question:** Can a teleportation protocol on Heron r2 act as a self-certifying
entropy source — where a co-measured CHSH witness bounds the min-entropy of the output bits —
and what certified-bit rate does the hardware actually yield?
**Hypothesis:** Interleaving CHSH witness rounds with teleport-byproduct extraction produces
bits with a CHSH-certified min-entropy floor > 0 at a measurable rate, a guarantee an
unwitnessed QRNG cannot make.
**Method:** Run teleport circuits and harvest the 2 Bell-measurement bits per teleport as raw
output; interleave CHSH rounds on the same coupler to estimate S; map S → a min-entropy bound
(Pironio-style DI-randomness relation — **needs a citation check**); apply a randomness
extractor; report certified rate vs raw rate. Frame honestly as **CHSH-witnessed /
semi-device-independent**, not loophole-free DI.
**Baseline:** the repo's existing served QRNG (health-tested but *not* self-certified) and a
classical CSPRNG — the honest controls showing exactly what the certificate adds.
**Metrics:** CHSH `S`, certified min-entropy per bit, certified bits/sec, extractor yield,
NIST pass (necessary, not sufficient), and the gap between certified and raw rate.
**Novel contribution:** entropy whose quantumness is *proven by the run that produced it* — a
live, per-batch certificate rather than a provenance signature or a "we ran it on a QPU"
claim.

## THE VISUALIZATION
A bit-stream ticking out in blocks; above it a **live CHSH needle**. While `S > 2` each block
gets a green **"certified"** stamp and the certified-bit counter climbs. A slider lets the
visitor **sabotage the source** (drift `S` toward 2): the needle drops, the badge turns red,
and the certified rate visibly collapses to zero — the proof failing in real time. Beside it,
a classical QRNG lane that *can never earn the badge*. The proof is the show: the visitor
watches certification live and watches it die when the physics is faked.

## Connection to what already exists
Replaces the weaker `viz-8-quantum-randomness-beacon` angle (which signs/hash-chains *served*
bits — a provenance layer) with an **intrinsic** certificate. Reuses the QRNG health-test
tradition of `ErrorDetectionVSRawBits/` and `CalibrationGuidedHighYieldQRNG/`; the CHSH
machinery from `QuantumAlgorithmsExplained/code/11_chsh.py` and the `viz-7-chsh-beat-the-bound`
idea; and the teleport primitive from `QuantumAlgorithmsExplained/code/04_teleportation.py`.
Distinct from `viz-8`: signing served bits proves *who/when*, CHSH-certification proves
*that they are quantum*.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Cleanly escapes the "been there, done that" QRNG rut — the certificate is the new
thing. DI-QRNG is a live, respected research area. The "hack it and watch certification
collapse" interaction is a rare *trustless* demo. Small circuit: two qubits + a teleport.
**Bear:** True device-independence requires a loophole-free Bell test and high `S`; a
same-chip Heron r2 test is not loophole-free, so the claim must be scoped to
"CHSH-witnessed / self-testing-flavoured" or it overclaims. The certified rate may be tiny
after the min-entropy bound and extractor.
**Likely outcome:** A modest but nonzero certified-bit rate with a live CHSH receipt, framed
honestly as semi-device-independent, plus a compelling figure.
**Value if null:** If Heron r2's `S` is too low/noisy to certify positive min-entropy, that
is a concrete, publishable statement about the feasibility of self-certifying QRNG on current
hardware — and the demo still teaches the concept.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Can teleportation byproduct bits be certified quantum-random by a
co-measured CHSH witness on real hardware?
**Single defended claim:** A CHSH witness interleaved with teleport extraction yields bits
with a certified min-entropy floor an unwitnessed QRNG cannot claim.
**Why it fits 6–8 pp:** one protocol, one witness→entropy mapping, two baselines
(served QRNG / CSPRNG), one certified-rate metric, one live-certificate figure.
**Target venue:** IEEE Security & Privacy (systems/demo) / IEEE Access.
**Compelling-study likelihood: 73/100** — strong concept and a clean differentiator from
prior QRNG work; ceiling set by the loophole/overclaim boundary and achievable certified rate.
**Citation check needed:** the S → min-entropy relation (Pironio et al. 2010, DI randomness)
— confirm the exact bound before it goes in the paper.
