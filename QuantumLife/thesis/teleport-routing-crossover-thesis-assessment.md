# Thesis Assessment — The Teleport-vs-SWAP Long-Range Routing Crossover

**Status:** Assessment / pre-study scoping (NOT yet a committed study)
**Date:** 2026-09-08
**Author:** Claude (Opus), with Peter
**Source material:**
- `QuantumLife/research/conclusion_teleportation_longrange.md` (the hardware result)
- `QuantumLife/code/research_qtree_teleport.py` (teleport arm)
- `QuantumLife/code/research_qtree_swaplr.py` (SWAP baseline arm)
- QDEP memory (`qdep-setup-bug-fix`): the *contradicting* Heron-r2 refutation
- Provisional literature anchor: IBM dynamic-circuit long-range entanglement work
  (Bäumer et al., *Efficient Long-Range Entanglement using Dynamic Circuits*, ~2023) — **must be
  verified before any novelty claim** (see §11).

> **Purpose of this document.** Decide, honestly, whether the strongest empirical thing produced in
> the QuantumLife program — a real-hardware head-to-head between a constant-*logical*-depth teleported
> long-range CNOT and an O(distance) SWAP-ladder CNOT — can become a defensible thesis study, and if
> so, *which* claim is real, which is novel, and which is textbook measurement of something already
> proven. Written to survive its own bear case.

---

## 0. TL;DR

- **What is real and strong:** we have *real hardware data on both sides of a contradiction*. On
  `ibm_marrakesh` the teleport arm produced a reproducible, significance-tested long-range correlation
  (−0.065, 4/4 seeds, p<0.05, zero overlap vs SWAP) at **logical** depth 9 where the depth-31 SWAP
  ladder washed out. On Heron-r2 (QDEP), the *same* teleport-routing idea was **REFUTED** — constant
  logical depth still lost to a depth-40 SWAP, because readout error ≫ 2q error inverts the advantage.
- **The candidate "law"** — *teleport beats SWAP iff `SWAP_depth(d)·ε_2q > teleport_readout_cost·ε_readout`*
  — is **half-real and not new.** Half-real because it **omits the Bell-pair distribution cost**, which
  is itself O(d)·ε_2q on a nearest-neighbour chip and is the term that actually decides the outcome.
  Not new because the dynamic-circuit-vs-SWAP readout/2q tradeoff is published (IBM et al.).
- **What could still be a study:** *not* the principle, but an **empirical crossover map** — measure,
  across distance and across backends with live calibration, where constant-depth teleport routing
  wins vs loses for a **correlation-preservation** observable, reconcile our own WIN (marrakesh) and
  REFUTATION (Heron-r2), and test whether a corrected crossover model **predicts** the winner from the
  live `ε_readout/ε_2q` ratio. That is a measurement/characterization contribution, hardware-first,
  falsifiable — workshop-to-short-paper tier, honest, and it is more of a *result* than any of the
  program's frameworks.
- **Honest ceiling:** this is a device-characterization / compiler-heuristic study, **not** new
  physics and **not** a quantum-advantage claim. Its value is a clean, calibration-aware, reproducible
  answer to a real compiler question ("teleport-route or SWAP-route this gate on *this* device
  today?"), plus the reconciliation of two of our own contradictory runs.

---

## 1. What we actually measured (the ground truth, exact numbers)

### 1.1 The circuit under test
`research_qtree_teleport.py` applies a **long-range CNOT via gate teleportation** between the *angle*
qubit of two distant genome slots:
```
H(a1); CX(a1,a2)          # Bell pair spanning the register
CX(q_i, a1); measure a1   # inject control parity, teleport
if m1: X(a2)              # feed-forward (or herald: post-select tel==00)
CX(a2, q_j)              # a2 acts as control next to target
H(a2); measure a2
if m2: Z(q_i)            # feed-forward
```
Logically `CX(q_i, q_j)` at **constant logical depth**, with q_i and q_j **never physical neighbours**
— so any measured correlation at their separation cannot be local crosstalk. The headline metric is
the connected two-point correlation at the two bonded qubits, normalised by C0: **`bond c(d)`**.

Baseline: `research_qtree_swaplr.py` — the *same logical* CX via an O(distance) SWAP chain (verified
no index bug; `_swap_cx`), depth-31 at d=12.
Null: `--sim --herald` — no entanglement, must give `c(d)≈0`.

### 1.2 The marrakesh result (the WIN) — from `conclusion_teleportation_longrange.md`
Backend `ibm_marrakesh` (156-qubit Heron r2), 102-qubit register (17 slots × 6 bits).

| arm | depth (logical) | mean `c(d)` at d=12 | evidence |
|---|---|---|---|
| teleport heralded | 9 | **−0.116** (single 16384-shot) → **−0.065** (4-seed mean) | 4/4 seeds negative |
| teleport feed-forward | 14 | −0.075 | 10/11 gens negative → **not a heralding artifact** |
| SWAP ladder | 31 | **+0.040** (4-seed mean) | 4/4 seeds positive |
| classical null | 9 | −0.001 | on floor |

- **Matched repeats (4 seeds, 4096 shots):** teleport all-negative, SWAP all-positive, **zero
  overlap**, paired **p<0.05 (≈0.01)**. Statistically significant *difference*.
- **Distance:** signal at d=12, **noise** at d=36 (mean +0.030, sign flips 4×) → a real
  **decoherence-vs-distance crossover between d=12 and d=36 on marrakesh**.
- **Noiseless-sim resolution (§0 of the conclusion):** exact statevector sim proved (a) `_teleport_cx`
  IS a logical CNOT (L1 ≤ 0.018 vs plain CX), and (b) the *ideal* bond sign is **negative** (−0.29 at
  d=12). So teleport hardware (−0.065) matches the ideal sign; SWAP (+0.040) is the **wrong-signed,
  depth-decohered** arm. In *this* framing teleport is the faithful implementation.

### 1.3 The Heron-r2 result (the REFUTATION) — from QDEP memory
> "teleport routing **REFUTED** on Heron-r2 even with full QuantumLife setup (defer-readout+herald,
> constant depth 7 **still loses to depth-40 swap**); advantage **INVERTS** on modern HW (readout-err
> ≫ 2q-err); **logical_depth not the routing figure of merit**; quantum>classical physically blocked
> on two-point C(g)."

Same idea, opposite verdict. **This contradiction is the single most scientifically interesting thing
in the whole program**, and reconciling it is the study (§8).

### 1.4 What the measurement is honestly worth, as-is
Per the conclusion's own §7 bottom line: a clean hardware head-to-head + a novel *application*
(hardware entanglement driving an evolving-genome tree), **suitable as an arXiv note / workshop /
outreach artifact — NOT a novel-physics claim.** That verdict is correct and stands.

---

## 2. The candidate claim, stated precisely

The one-line "law" proposed in conversation:

> **Teleport routing beats SWAP iff `SWAP_depth(d)·ε_2q > (teleport's extra readout cost)·ε_readout`.**

This is the object under assessment. Is it *real* (physically correct)? Is it *new*? §3 and §4 answer.

---

## 3. The corrected physics — why the one-liner is incomplete (the load-bearing correction)

The inequality treats teleport's two-qubit-gate cost as ≈0 (constant depth). **That is only true of
*logical* depth.** The honest error budget on a nearest-neighbour-coupled chip:

**SWAP long-range CNOT at distance d:**
- ~3(d−1) two-qubit gates (each SWAP = 3 CX) + a final CX. Leading incoherent error ≈ **3d·ε_2q**,
  plus idle decoherence over its O(d) depth. Genuinely O(d).

**Teleport long-range CNOT:**
- Constant *logical* ops + 2 mid-circuit measurements + feed-forward. Extra readout ≈ **2·ε_readout**.
- **BUT the Bell pair `CX(a1,a2)` must span distance d.** On a NN chip a1 and a2 are far apart, so that
  single logical CX **transpiles back into O(d) SWAPs** — cost ≈ **3d·ε_2q, the same order as the SWAP
  ladder.** This is the term the one-liner drops.

So the honest comparison is:
```
teleport_error ≈ (Bell-pair distribution: ~3d·ε_2q)  +  2·ε_readout   [+ feed-forward, idle]
swap_error     ≈ (~3d·ε_2q)                                            [+ idle over larger depth]
```
Consequences:
- If the Bell pair is distributed by an ordinary SWAP chain, **teleport has no 2q saving and only adds
  readout → teleport strictly loses.** This is exactly QDEP's REFUTATION and exactly why
  "logical_depth is not the routing figure of merit."
- Teleport can win **only** when the Bell pair is distributed *more cheaply than a SWAP chain*:
  pre-shared / heralded Bell pairs, entanglement swapping done in parallel or offline, distillation, or
  native long-range couplers. None of these is what the naive `cx(a1,a2)` does.
- The marrakesh WIN is therefore **not cleanly a routing-cost win.** Plausible real causes:
  (i) herald post-selection filtered the noisy branches (a *noise filter*, not a routing saving);
  (ii) the observable is a *correlation* `c(d)`, not gate fidelity — different noise sensitivity;
  (iii) marrakesh at run time had `ε_2q` structure where the transpiled Bell-pair path was luckier than
  the full SWAP ladder; (iv) the SWAP arm's depth-31 idle decoherence dominated. The sign anomaly
  (§4b of the conclusion) is a symptom that the "win" is confounded, not a clean routing result.

**Corrected inequality (honest form):**
> Teleport beats SWAP iff
> `[swap 2q cost − teleport-Bell-pair 2q cost]·ε_2q  +  [swap idle − teleport idle decoherence]
>   >  (teleport extra readout)·ε_readout`.
> On a plain NN chip with a naively-routed Bell pair the first bracket ≈ 0, so the readout term
> dominates and **teleport loses** — the modern-HW inversion. Teleport wins only when the Bell pair
> is distributed by something cheaper than SWAP routing, and/or the observable/post-selection favours
> the shallower-logical circuit.

The *spirit* (a crossover set by the readout-vs-2q balance) is right. The *written form* is wrong
because its decisive term is missing.

---

## 4. Novelty dissection — textbook vs possibly-new

### 4.1 Textbook / already proven (do NOT claim as novel)
- **Gate teleportation of a CNOT** (Bell pair + measurement + feed-forward) — Gottesman–Chuang; standard.
- **Long-range CNOT / GHZ via dynamic circuits** (measurement + feed-forward beats unitary routing for
  long range) — demonstrated on IBM hardware (Bäumer et al.–style dynamic long-range entanglement work,
  ~2023). Directly covers the teleport-vs-SWAP comparison.
- **The readout-vs-2q-error tradeoff deciding which routing wins** — this is the analysis in that same
  dynamic-circuit line of work; "measurement overhead vs gate overhead" is the known crossover.
- **Constant-logical-depth long-range gates** — the whole point of measurement-based / lattice-surgery
  routing; known.
- **That NISQ two-point correlations decohere with distance** — expected, not a discovery (our d=12
  signal / d=36 noise is a *device-specific number*, not a new phenomenon).

### 4.2 Possibly-new (narrow, empirical, must be checked against §4.1)
- **A calibration-driven crossover map for a *correlation-preservation* observable**, rather than gate
  fidelity or Bell-state fidelity. The published work measures fidelity of the long-range gate/state;
  measuring the *preserved two-point correlation `c(d)`* of an application circuit, and mapping where
  teleport-routing preserves it vs where SWAP does, across distance, may not be published in that exact
  form. **Weak novelty — likely a re-measurement in a new observable, not a new principle.**
- **The explicit reconciliation of a WIN and a REFUTATION on two Heron devices via the live
  `ε_readout/ε_2q` ratio** — i.e. showing our own two contradictory experiments are two points on one
  predicted crossover surface, and that the *corrected* model predicts the winner from live
  calibration. If the published work states the tradeoff qualitatively but does not give a *predictive,
  calibration-parameterised* winner-selector validated across devices, that predictive selector could
  be a small genuine contribution. **Contingent on the literature check.**
- **A compiler heuristic:** "choose teleport-route vs SWAP-route per gate from live calibration and
  distance," with a measured decision boundary `d*(ε_readout/ε_2q)`. Practically useful; novelty
  depends on whether existing transpilers already encode this.

### 4.3 Firmly NOT a contribution
- Any "quantum life / evolving tree" framing as *physics*. It is a nice application skin; strip it for
  a physics study. (Keep it only for an outreach artifact.)
- Any quantum-advantage / classical-hardness claim. There is none here.
- "Teleport is more stable than SWAP" — the conclusion's §6c explicitly shows this is **false**
  (teleport scatters *more* per-generation: std 0.097 vs 0.060).

---

## 5. Bull case (why this could be a real, worthwhile study)

1. **Hardware-first with real data already in hand — on both sides.** Unlike the program's frameworks
   (NP map = counting; sandpile = dead sim; canary = infra), this is an *experiment* that measured
   nature, has error bars, and already produced a significant effect **and** a significant
   counter-result. A study that starts from a real contradiction in your own runs has the best possible
   motivation.
2. **Falsifiable and can-fail.** The corrected crossover model makes a sharp prediction: from a
   device's live `ε_readout/ε_2q` and the distance d, it predicts the winner. Run a *third* backend and
   it is right or wrong. That is a real experiment, not a tautology (contrast the NP map / F9).
3. **Reconciles a genuine paradox.** "Teleport beats SWAP" (marrakesh) vs "teleport loses to SWAP"
   (Heron-r2 QDEP) looks like a mistake; showing it is a *regime boundary* governed by one measurable
   ratio turns an embarrassment into the headline. Reviewers reward "we explain why our own results
   disagreed."
4. **Practically useful.** "Teleport-route or SWAP-route this long-range gate on this device today?" is
   a live compiler question. A measured, calibration-aware decision boundary is usable, not just
   pretty.
5. **Rigor scaffolding already exists.** Both arms are built and validated; the noiseless-sim ideal
   reference is done; herald/feed-forward artifact control is done; matched-repeat significance is
   done. A distance × backend sweep is *incremental*, not a new build.
6. **Ties the program together.** `d*` (the crossover distance) is exactly the **calibration-driven
   routing figure of merit** — the honest, grounded version of the "teleport-canary" idea that opened
   this whole line of work, now backed by real data instead of a composite index.

---

## 6. Bear case (why it might not be worth a thesis, stated at full strength)

1. **The principle is textbook (§4.1).** The dynamic-circuit-vs-SWAP readout/2q tradeoff is published
   (IBM et al.). A referee who knows that line of work reads the crossover claim as "re-measuring a
   known tradeoff in a cuter observable." Novelty of *observable* ≠ novelty of *result*.
2. **The headline inequality was wrong (§3).** The originally-proposed "law" omitted the Bell-pair
   distribution term — the term that decides the outcome. A study built on a corrected version of your
   own initially-incorrect heuristic is fragile; a reviewer notices the correction *is* the known
   physics.
3. **The marrakesh "win" is confounded.** It is entangled with herald post-selection (a noise filter,
   not a routing saving), a sign anomaly, and a correlation observable rather than fidelity. It may not
   survive as a clean "teleport routing wins" datapoint once the Bell-pair cost and post-selection are
   controlled. If the controlled re-run erases the win, the whole crossover story loses its positive
   pole.
4. **Tiny effect, big noise.** |c(d)| ≈ 0.065, gen-to-gen scatter ±0.1, calibration drift between
   submissions. Extracting a *crossover surface* from a signal this small across multiple devices needs
   a lot of shots/repeats and may just produce error bars that swallow the boundary.
5. **Device-characterization ≠ thesis-grade novelty.** Even done perfectly, this is a measurement/
   compiler-heuristic note. The value ceiling is "clean characterization + honest reconciliation," not
   a new algorithm, new physics, or an advantage. Same disease as the NP map, milder: safe, finishable,
   low ceiling.
6. **Reproducibility is calibration-bound.** The result depends on live calibration that changes daily;
   `d*` on marrakesh-Tuesday may differ from marrakesh-Friday. A crossover boundary that moves with the
   weather is honest but weakens "a figure of merit."
7. **Cost to make it decisive is real QC.** A distance sweep (d=12,18,24,30,36) × ≥3 backends × matched
   repeats × enough shots to beat ±0.1 scatter is a non-trivial QC budget, on a study whose ceiling is
   a characterization note. Opportunity cost vs the finished NP map is real.
8. **The application skin is dead weight.** The genome-tree framing adds nothing to the physics and
   invites "why is this dressed as artificial life?" You must strip it, which means the *program's*
   identity (QuantumLife) is not what gets published — a bare routing benchmark is.

---

## 7. What we measured vs what we can claim (the honesty ledger)

| Measured (real) | Claimable now | NOT claimable |
|---|---|---|
| teleport `c(d)`=−0.065, 4/4 seeds, p<0.05 vs null, d=12 marrakesh | "a reproducible, crosstalk-immune long-range correlation at constant logical depth 9, not a heralding artifact" | "teleport reproduces the SWAP CX at lower *physical* cost" (Bell-pair term unaccounted) |
| teleport ≠ SWAP, opposite sign, zero overlap, p<0.05 | "the two implementations give significantly different long-range correlations on this device" | "teleport is the better router" (device-specific; inverts on Heron-r2) |
| noiseless sim: ideal sign negative; teleport matches, SWAP wrong-signed | "teleport is the faithful arm *in this framing/observable*" | "teleport is more stable" (false — it scatters more) |
| d=12 signal, d=36 noise (marrakesh) | "a decoherence-vs-distance crossover between 12 and 36 qubits on marrakesh at run-time calibration" | "a universal crossover distance" (calibration-bound) |
| QDEP: teleport loses to SWAP on Heron-r2 (readout-dominated) | "the routing advantage inverts when ε_readout ≫ ε_2q" | any single-device universal winner |

---

## 8. How it becomes a study (the design)

**Working title:** *Teleport-vs-SWAP long-range routing on superconducting hardware: a
calibration-driven crossover, and the reconciliation of a win and a refutation.*

**Central question (falsifiable):** Does a corrected crossover model — accounting for Bell-pair
distribution cost, gate error `ε_2q`, readout error `ε_readout`, and distance d — **predict**, from a
device's *live* calibration, whether a constant-logical-depth teleported long-range CNOT preserves an
application's two-point correlation better than an O(distance) SWAP ladder?

**Single defended claim (target):** *"Which long-range router wins is set by the live `ε_readout/ε_2q`
ratio and the distance; a corrected cost model predicts the winner on a held-out backend, reconciling
our marrakesh win with our Heron-r2 refutation as two points on one crossover surface."*

**Arms / controls (all already built):**
- teleport (heralded) · teleport (feed-forward) · SWAP ladder · classical null · noiseless-sim ideal.

**Design:**
1. **Distance sweep** d ∈ {12,18,24,30,36}, both arms, matched seeds/shots — draw the `c(d)` decay
   curve per arm (the figure a preprint needs; the conclusion §6 flags this as the missing piece).
2. **Transpile-honest cost accounting:** for each d, record the **post-transpilation physical** 2q-gate
   count and depth of BOTH arms (including the teleport Bell-pair routing) — kill the logical-depth
   illusion; report physical cost, not logical (directly answers QDEP's "logical_depth is not the
   figure of merit").
3. **Cross-backend:** ≥3 backends spanning the `ε_readout/ε_2q` ratio (a 2q-dominated one like the
   marrakesh-at-run-time regime, a readout-dominated one like the QDEP Heron-r2 regime, and a third
   *held-out* device to test prediction). Record live calibration per submission.
4. **Corrected model fit:** fit the §3 honest cost model; extract the decision boundary
   `d*(ε_readout/ε_2q)`. **Predict** the winner on the held-out device *before* running it, then run
   and score the prediction. (This is the can-fail step.)
5. **Confound controls:** separate herald-as-noise-filter from routing-cost by comparing heralded vs
   feed-forward at matched physical cost; verify the win is not purely post-selection.
6. **Observable robustness:** report both the application correlation `c(d)` AND a clean Bell-state /
   gate fidelity for the bare long-range CNOT, so the result is not tied to the genome-tree observable.

**Deliverables:** the `c(d)`-vs-d curves per arm per backend; the physical-cost table; the
`d*(ε_readout/ε_2q)` boundary; the held-out prediction score; one figure = the crossover surface with
marrakesh-WIN and Heron-r2-REFUTATION plotted as two points on it.

**Strip the skin:** publish as a routing benchmark. Keep the genome-tree only as an outreach demo / the
application that motivated the observable.

---

## 9. Falsifiable predictions (what would kill it, what would confirm it)

- **Confirm:** on a held-out backend, the corrected model predicts the winner from live calibration;
  physical-cost accounting shows teleport wins only where `[swap 2q + idle] − [Bell-pair 2q + readout]`
  is positive; the marrakesh and Heron-r2 points sit on the fitted surface.
- **Kill:** the "win" evaporates once Bell-pair cost is charged honestly and herald post-selection is
  controlled (i.e. teleport never beats SWAP at matched physical cost) → then the honest result is the
  *negative* ("constant logical depth is an illusion; teleport routing does not beat SWAP for this
  observable on NN hardware") — which is still a clean, publishable negative and vindicates QDEP.
- **Kill (weaker):** the crossover boundary is so calibration-noisy that `d*` has no predictive power →
  the "figure of merit" claim dies; only the descriptive curves survive.

Note: **both a confirm and a kill are publishable** — that is the mark of a real study (unlike F9).

---

## 10. How it fits the wider program

- **Directly reconciles two of your own records** (this conclusion vs QDEP memory) — the strongest
  internal motivation available.
- **Is the grounded form of the "teleport-canary" idea** (`d*` = calibration-driven routing health
  metric) that opened this conversation — but backed by a real measured quantity instead of a composite
  index, so it dodges the F9 bear case entirely.
- **Complements the NP thesis's honesty stance:** the NP map says "quantum advantage is rare / NISQ
  loses wall-clock"; this study says "and here, concretely, is when even a *routing* primitive's
  advantage inverts on real hardware, and how to predict it." Same claim-discipline spine.
- **Uses the QuantumLife engine as the application** without resting any physics claim on it.

---

## 11. Next step BEFORE committing (mandatory)

The entire novelty question hinges on the published dynamic-circuit long-range entanglement literature.
Do **not** build until this is checked:

1. **Literature check (deep research / web):** find the IBM (and others') dynamic-circuit long-range
   CNOT/GHZ papers; determine exactly what they claim about the teleport-vs-SWAP readout/2q tradeoff.
   Specifically: do they already give a **predictive, calibration-parameterised winner-selector
   validated across devices**, or only a qualitative "dynamic wins for long range" + a fidelity
   demonstration? The gap (if any) is the only novelty.
2. **Zero-QC honesty pass:** rebuild both arms at d∈{12,18,24,30,36}, transpile to a real backend
   coupling map, and print the **post-transpilation physical** 2q count + depth for both — including the
   teleport Bell-pair routing. If teleport's physical 2q cost is ≈ SWAP's, the "constant depth"
   advantage is already dead on paper and the study reduces to the honest negative (still worth writing,
   but know it up front). This costs no QC and decides the framing.
3. **Only then** decide: (a) predictive-crossover study (if the literature gap and the physical-cost
   sim both survive), or (b) honest-negative note ("logical-depth advantage is an artifact; teleport
   routing does not beat SWAP for this observable on NN hardware — corroborating QDEP"), or (c) shelve.

---

## 12. Verdict

**The measurement is the strongest empirical asset in the QuantumLife program** — real hardware, real
controls, real significance, and a real internal contradiction to resolve. **The proposed one-line law
is not the contribution:** it is half-real (omits Bell-pair cost) and not new (published tradeoff).
**The defensible study is the empirical, calibration-driven crossover map that reconciles the win and
the refutation and tests a corrected predictive model on a held-out device** — hardware-first,
can-fail, useful, honest, but with a **device-characterization ceiling**, not a novel-physics or
advantage ceiling.

Recommended: run the **zero-QC physical-cost sim + the literature check first** (§11). If teleport's
transpiled physical cost is not actually constant (likely), the honest deliverable is the *negative*
that vindicates QDEP — which is a cleaner, sharper result than the confounded "win," and cheaper to
land. Either way, decide the framing from the free evidence before spending a single QC second.
