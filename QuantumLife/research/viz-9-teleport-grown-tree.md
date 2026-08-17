# VIZ Idea 9 — Teleport-Grown Tree: can teleportation buy longer-range genome correlation at lower qubit cost than a SWAP-free chain?

**Tag: QUANTUM · viz · effort: medium**

## Pitch
`QuantumLife`/QuantumTree already grows a real 108-qubit tree on Heron r2 every generation,
and it already produced a *real* correlation signature (L2 hardware `c(1)=-0.077`, z≈-10 vs
the classical surrogate). But that correlation is **nearest-neighbour only** and — the study
admits it — **cannot yet be told apart from coherent-error/crosstalk**. This idea bolts a
**teleport-wired long-range bond** and **mid-circuit qubit recycling** onto the existing
pipeline: entangle a branch-slot with a *distant* slot via a Bell pair + mid-circuit measure
+ classical feedforward, so a parent branch's character echoes in a far descendant — real
tree hierarchy, not a 1-D string — and emit the 18 slots from a *small reused qubit block*
instead of 108 flat qubits. Crosstalk only couples physical neighbours, so any correlation
at teleport-distance is a signature crosstalk **cannot** fake.
**Paper strength score: 75/100** — reuses a working pipeline and a real prior result, and
directly attacks a confound the parent study already flagged; docked for teleport-link
fidelity risk on NISQ (feedforward latency + measurement error may swamp the long-range
signal).

## How it becomes a study
**Research question:** Does teleporting entangling bonds across the register produce
long-range genome correlation `C(d)` at chain-distances where the SWAP-free brick-wall
chain gives ~0 — at equal-or-lower depth and qubit count?
**Hypothesis:** The teleport-route yields `|c(d)| > noise` at target distances beyond
nearest-neighbour where the chain route collapses to zero, and because those qubits are
never physically adjacent, crosstalk cannot reproduce it.
**Method:** Extend `code/research_qtree.py` / `research_qtree_brickwall.py` with (a) a
*teleport-bond* variant that entangles slot *i* with a distant slot *j* through a Bell pair
+ mid-circuit measurement + feedforward X/Z correction (dynamic circuit), and (b) a
*qubit-recycling* variant that emits the 18 slots in rounds from a small block using
measure+reset. Sweep bond distance. Hold shots/generations/environment schedule fixed.
**Baseline:** the existing brick-wall nearest-neighbour chain, the classical `--sim`
surrogate (null), and a SWAP-ladder long-range bond (the depth-costly honest alternative
teleportation is meant to beat).
**Metrics:** `|c(d)|` at target distances, integrated `ξ` (with the study's caveat that
sign-alternation cancels — report `|c(1)|`, `|c(2)|`, and the far-`d` term explicitly),
z vs surrogate, circuit depth, qubit count, and measured teleport-link fidelity. The
headline is **presence of long-range `C(d)` that survives above the SWAP-route at equal
depth** — the crosstalk-immune signature.
**Novel contribution:** teleportation used as *both* the confound-killer (long-range
correlation crosstalk cannot fake) and the complexity-reducer (fewer qubits, lower depth)
for a hardware-grown generative structure.

## THE VISUALIZATION
A split canvas. **Left:** the tree grown on the SWAP-free chain — blobby *local* clustering,
neighbours resemble neighbours, no reach. **Right:** the same tree grown with teleport
bonds — a parent branch's "character packet" visibly **teleports across the canvas** and a
distant branch snaps to match it: genuine hierarchy appears where the chain could never
reach. A toggle drops in **qubit recycling** — the same tree regrows with far fewer qubits
lit on the chip map. One screen carries the thesis: *hierarchy shows up exactly where a 1-D
chain can't put it, and it costs fewer qubits.*

## Connection to what already exists
Direct extension of `QuantumLife/code/research_qtree.py` and `research_qtree_brickwall.py`,
and of the `C(d)` metric defined in `QuantumLife/research/STUDY_ENTANGLEMENT_CORRELATION.md`
(this study answers the "NOT proven: entanglement specifically" open item in that doc's
conclusion). The teleport primitive already exists as a simulator lesson in
`QuantumAlgorithmsExplained/code/04_teleportation.py` — this takes it to hardware with a
purpose. Sits beside `qh-5-dynamic-circuit-crossover` (feedforward vs unitary ladder for
long-range GHZ) but asks a different question: not "when does feedforward win for GHZ prep"
but "does a teleported bond leave a crosstalk-immune long-range correlation in a running
generative circuit."

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** Reuses a working 108-qubit pipeline and a real, already-significant result — low
build risk. Long-range correlation is *crosstalk-immune*, so a positive result finally earns
the entanglement claim the parent study couldn't. The dual left/right visual is striking and
the qubit-recycling toggle makes the "less complexity" story literal. Product payoff: a
richer tree from fewer qubits.
**Bear:** On Heron r2 the teleport link costs a Bell pair + mid-circuit measure + feedforward
latency; that added noise may swamp the long-range signal, giving no crossover over the SWAP
route. Feedforward-conditioned gates may also be slow enough that the depth advantage shrinks.
**Likely outcome:** A crossover distance where teleport `C(d)` clears both the vanishing
chain term and the noisier SWAP route — a modest but real long-range signal with a clean
figure and an honest fidelity budget.
**Value if null:** If teleportation cannot produce long-range `C(d)` above noise, that bounds
how much genuine long-range entanglement Heron r2 sustains — a concrete NISQ capability
number — and it confirms QuantumTree's correlation is inherently local, which itself informs
the crosstalk-vs-entanglement debate the parent study left open.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** Can teleport-wired bonds give a hardware-grown generative circuit
long-range correlation that a SWAP-free chain cannot, at lower depth and qubit count?
**Single defended claim:** A teleported bond produces measurable long-range genome
correlation `C(d)` that neighbour-only crosstalk cannot explain, at equal-or-lower cost than
the SWAP route.
**Why it fits 6–8 pp:** one existing pipeline, one added primitive, three baselines (chain /
SWAP / surrogate), one correlation metric, one split-canvas figure.
**Target venue:** IEEE Quantum Week (QCE) / IEEE Access.
**Compelling-study likelihood: 75/100** — reuses a working system and a real prior result and
resolves a stated confound; ceiling set by teleport-link fidelity on current hardware.
