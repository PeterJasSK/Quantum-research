# Net Idea 5 — Entangled Load Balancer: do real Heron Bell pairs cut ECMP collisions below what shared randomness can?

**Tag: QUANTUM · net · effort: medium · QC: yes (small: 2-qubit Bell rounds, 0–2 CZ)**

## Pitch
Two switches must pick paths for flows without talking to each other. Classically the best they can do is shared
randomness; theory (HotNets 2025, UT Austin; Quantum Internet Alliance "quantum-enhanced load balancing" use card;
a 2026 PRA two-server routing paper) says shared entanglement beats every communication-free classical strategy
for some throughput functions. Nobody has fed *measured hardware* correlations into a real load-balancing simulator
and read the downstream number. We do exactly that: CHSH-grade Bell rounds from ibm_fez (S ≈ 2.73, already
repeatable) drive the path choice inside the existing ECMP collision engine, and we measure tail flow-completion
time and collision rate against the best classical coordinator.

**Paper strength score: 72/100** — first hardware-sourced instance of a 2025 theory claim, with a downstream
network metric and a built-in honesty gate; docked because entanglement is generated on one chip, not distributed
between two real switches, and the gain may sit inside the noise of the classical optimum.

## How it becomes a study
**Research question:** Does a load balancer driven by real Heron Bell correlations reach lower collision / tail
latency than the optimal communication-free classical strategy on the same traffic?

**Hypothesis:** With S ≈ 2.7 the measured win rate of the coordination game stays above the classical bound, and
that surplus shows up as a measurable reduction of p99 flow-completion time on an ECMP fabric under bursty
traffic; below a threshold S\* the gain vanishes.

**Method:** Cast the two-switch path choice as a nonlocal game (CHSH or magic-square family, as in the cited
proposals). Generate Bell rounds on ibm_fez / marrakesh with per-round random settings. Replay the outcome stream as
the path-choice oracle in the `TargetedDosColisionsAndRNGAngle/` ECMP simulator. Sweep S by mixing in classical
noise to get the gain-vs-S curve and its threshold S\*.

**Baseline:** (1) independent hashing (today's ECMP), (2) best shared-randomness strategy (computed exactly for the
game), (3) ideal Tsirelson correlations (the upper bound), (4) a classical-twin stream with the same marginals.

**Metrics:** game win rate vs classical bound (σ); collision rate; p50/p99 flow-completion time; throughput under
the convex throughput function; threshold S\* where gain → 0.

**Novel contribution:** The first measured downstream networking gain from hardware entanglement, plus the
threshold S\* a future quantum network link must deliver for the gain to exist.

## THE VISUALIZATION
Split fabric: left, classical coordinators collide on a hot link (it glows red); right, entangled coordinators
spread flows. A slider for S (2.0 → 2.83) moves both the hardware point and the p99 bar; the gain dies at S\*.

## Connection to what already exists
- ECMP engine + web: `TargetedDosColisionsAndRNGAngle/` (the attack paper becomes the defence paper's testbed).
- CHSH gate: QuantumPhantoms RUNLOG (S = 2.71–2.77 on 11 runs), letter C certificate code.
- Distinct from net-1/net-4: those use *randomness* against an attacker; this uses *correlation* for coordination.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** clean measured gain above shared randomness, S\* sits below today's hardware, a short paper at QCE27 or
HotNets with a striking figure.
**Bear:** the advantage in the theory papers is a few percent and needs a specific convex throughput function; on
realistic traffic it disappears into variance.
**Likely:** a real but small gain on the game, a smaller gain on p99, a sharp S\* threshold.
**Value if null:** S\* is still the number a quantum-network engineer needs ("links below S\* are useless for
coordination"), and the replay harness becomes the benchmark for later networked entanglement.

## Thesis — IEEE short paper (6–8 pp, double-column)
**Central question:** does hardware entanglement measurably improve distributed load balancing?
**Single defended claim:** measured Heron correlations beat the optimal communication-free classical coordinator
on game win rate by kσ, and translate to an X % p99 reduction above threshold S\*.
**Why it fits 6–8 pp:** one game, one simulator, one sweep, one figure.
**Target venue:** IEEE QCE 2027 (Quantum Networking / Applications), or HotNets / ACM SIGCOMM workshops.
**Compelling-study likelihood: 72/100.**

Citation check needed: HotNets 2025 quantum load-balancing paper (cs.utexas.edu/~vijay/papers/hotnets25-quantum.pdf),
QIA use card, PRA 2026 "entanglement-assisted routing" (10.1103/3328-dwtb), MAC nonlocal paper 2304.10792.
