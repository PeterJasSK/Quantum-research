# Study Ideas

One folder for all candidate studies. Finished ideas move to `complete/` (renamed `DONE-*`).

## 🔨 Building next
- `qdep-1-coherence-depth-genealogy.md` — coherence depth `g*` of an inherited-entanglement genealogy (quantum artificial life, reproduce 2018 → g* vs classical surrogate → break the SWAP ceiling)
- `qh-13-np-problems-teleport-routing.md` — first teleport-routed QAOA on real hardware; dense-QUBO NP-hard problems as the teleport-routing target zone

## 🎓 Master's thesis candidates (new 2026-08-30 — thesis-scale, one per strategic direction)
Each is the **de-risked pivot** of a raw thesis pitch whose naive version is a trap (documented inside). Ranked build-first: thesis-1 > thesis-3 > thesis-2.

[//]: # (- `thesis-1-swap-routed-quantum-virus.md` — graduate the approved Stone-Wall virus epic &#40;P0 proven on metal&#41; to thesis: cross-block transmission-witness decay curve + certify it's entanglement; teleport = negative control. **80/100 · want-to-do 5/5 · effort high · QC yes** — safest + most uniquely owned.)
- `thesis-3-certified-entropy-provenance.md` — certified min-entropy + signed provenance under device imperfection (NOT "unbreakable encryption" — OTP already is). Builds on BC + ErrorDetectionVSRawBits + qrng-eaas. **74/100 · want-to-do 4/5 · effort medium · QC partial (stored bits)** — lowest null-risk, biggest asset reuse.
- `thesis-4-obscure-np-query-advantage.md` — **a systematic map of where the provable quadratic quantum query advantage (Dürr–Høyer/Grover, BBBV-optimal) survives the best-classical baseline vs collapses to brute-force-only**, across 5 forgotten 1970s NP-complete problems (Betweenness, Numerical Matching, Quadratic Congruences, Kernel, MinLA). NOT "I verified advantage" (overclaim) and NOT a hardware race — advantage proven by oracle-count in sim; qualifiers locked (query model / over brute force / quadratic / not wall-clock). **76/100 · want-to-do 4/5 · effort medium · QC sim-first, optional hw feasibility arm** — real work = the per-problem best-classical exponent.
- `thesis-5-critical-quantum-life.md` — "life you can poke": Darwinian quantum population self-organizes to the edge of chaos (σ≈1, avalanche α≈1.5) under DishBrain closed-loop feedback, recovers after between-runs pokes, certified quantum by entanglement witness; yoked control must fail. **77/100 · want-to-do 5/5 · effort high · QC yes (sim-first draft → hw thesis)** — max wow + ownership; a discovery bet, honesty-gated.

## Active — networking / RNG
- `net-1-unpredictability-as-network-primitive.md` — umbrella: 3 attacker games + boot-entropy fix
- `net-2-boot-entropy-fix.md` — Q-EaaS cures weak keys on headless devices (score 84, highest)
- `net-4-mtd-sdn-hopping.md` — moving-target defence, predictable hop schedule

## Active — quantum hardware
- `qh-2-temporal-drift-stability.md` — does QRNG quality survive recalibration cycles?
- `qh-3-minimum-extraction-budget.md` — cheapest extractor to pass NIST on Heron r2

### Heron r2 new-gen features (new 2026-08-16 — algorithm-on-hardware, not QRNG)
Each exploits a Heron r2 capability the repo has never used, and measures a downstream number.
- `qh-4-fractional-gate-depth-dividend.md` — do native `RZZ(θ)` fractional gates buy fidelity or only depth? Knee shift on the walk circuit. **70/100 · want-to-do 4/5 · effort low-medium · QC yes**
- `qh-5-dynamic-circuit-crossover.md` — at what N does measurement-feedforward beat the unitary ladder for long-range GHZ? **74/100 · want-to-do 4/5 · effort medium · QC yes**
- `qh-6-mitigation-vs-detection-roi.md` — ZNE+DD vs Bell-pair post-selection, accuracy-per-cost head-to-head. **72/100 · want-to-do 3/5 · effort high · QC yes**

### Textbook algorithms → real Heron r2 (new 2026-08-16 — inspired by `QuantumAlgorithmsExplained/`, not derivative of built work)
Take a lesson from the simulator-only algorithm tour to hardware and measure where the quantum promise degrades.
- `qh-7-grover-advantage-cliff.md` — search size where Heron r2 Grover drops below random guessing. **75/100 · want-to-do 4/5 · effort medium · QC yes**
- `qh-8-qpe-effective-bits.md` — how many eigenphase bits Heron r2 resolves before the noise floor. **72/100 · want-to-do 3/5 · effort medium-high · QC yes**
- `qh-9-bernstein-vazirani-string-length.md` — longest string read in one BV query before a bit flips (cheapest to build). **68/100 · want-to-do 4/5 · effort low · QC yes**

### Teleport-routed long-range gates (new 2026-08-17 — from the QuantumTree teleport result, art stripped)
The teleport iteration showed a constant-depth teleported bond keeps a crosstalk-immune long-range correlation the depth-31 SWAP equivalent loses. These turn that into standalone, citable NISQ-compilation / device-characterization results (sim-first, minimal QC).
- `qh-10-teleport-vs-swap-routing-benchmark.md` — measured crossover distance `d*` where teleported routing beats a SWAP ladder in fidelity-per-depth. **76/100 · want-to-do 4/5 · effort medium · QC yes (sim-first)**
- `qh-11-entanglement-reach-device-metric.md` — cheap per-device metric `R`: how far a teleported bond stays alive, tracked across calibration drift. **72/100 · want-to-do 4/5 · effort low-medium · QC yes (light)**
- `qh-12-swap-depth-sign-inversion.md` — sign anomaly RESOLVED (teleport faithful, SWAP wrong); reframed to: at what routing depth does SWAP *invert* a correlation's sign, not just shrink it? **74/100 · want-to-do 4/5 · effort low-medium · QC sim-first, small confirm**
- `qh-13-np-problems-teleport-routing.md` — maps every NP-hard problem by QUBO density × heavy-hex hardware status; dense-and-unclaimed = teleport-routing target zone. Flagship: fully-connected Number Partitioning (SK) QAOA — first teleport-routed QAOA on real hardware (prior art is sim-only). **78/100 · want-to-do 4/5 · effort medium-high · QC sim-first, hardware confirm**

### QDEP — quantum artificial life / inherited entanglement (new 2026-08-18 — carved from `QDEP_Living_Genealogies.md`)
Sharp single-claim spines cut from the Living Genealogies spec. Temporal (cross-generational) axis, distinct from QuantumLife's spatial `c(d)`.
- `qdep-1-coherence-depth-genealogy.md` — how many generations of coherent inheritance beat a matched classical measure-and-resend surrogate before the gap closes (the number `g*`)? **75/100 · want-to-do 4/5 · effort medium-high · QC yes (sim-first)**

## Active — visualization-first (new 2026-07-29)
Heavy graphics potential, in the spirit of the 3-body + load-balancing visuals. Each carries a
`## Thesis — IEEE short paper (6–8 pp)` block: one compelling central question, one defended claim,
one headline figure. Target = short double-column IEEE format.

| File | QC? | The visual | Likelihood | Want-to-do (me) |
|------|-----|-----------|-----------|-----------------|
| `viz-6-quantum-rescue-proof-of-concept.md` | **QC** | textbook-QPE dots scatter, dynamic-QPE dots snap onto the exact curve | **70/100** — POC reframe: the *hardware rescue* is the point, not the molecule | **3/5** — high effort, real QPE-depth risk (taper H2 + VQE fallback) |
| `viz-7-chsh-beat-the-bound.md` | **QC** | win-rate needle parks above the classical S=2 line; per-coupler quantumness heatmap | **72/100** — smallest honest "classically impossible" win; near-guaranteed to work | **5/5** — 2 qubits, cheap, ~90% works |
| `viz-9-teleport-grown-tree.md` | **QC** | split canvas: chain grows blobby local clusters, teleport bonds echo a parent's character into a far branch | **EXECUTED 2026-08-17 ✓ win** — teleport faithful (correct sign, constant depth), SWAP wrong-signed floor; crosstalk confound closed | spun out qh-10/11/12 |
| `viz-10-entropy-with-proof.md` | **QC** | live CHSH needle stamps each bit-block "certified"; sabotage the source and the badge dies in real time | **73/100** — self-certifying entropy; clean break from prior "trust us it's quantum" QRNG work | **4/5** — small circuit, trustless demo, DI-overclaim care needed |
| `viz-8-quantum-randomness-beacon.md` | non-QC (uses served QRNG) | live signed beacon ticks; click any past pulse and re-verify it yourself | **76/100** — works & useful *now*; extends qrng-eaas; provenance is the novelty | **4/5** — deployable today, no hardware fragility |
| `viz-3-dns-poison-race.md` | non-QC | poison race, entropy cliff, SAD-DNS reveal | **80/100** — cited live threat, dramatic cliff | **5/5** — probably done first; strong visual, relevant, real answer findable |
| `viz-5-gossip-overlay-resilience.md` | non-QC | infection wavefront, eclipse goes dark | **78/100** — hottest topic, cited threat, cleanest curve | **3/5** — feels derivative of ECMP, but probably done last |
| `viz-2-quantum-galton-board.md` | **QC** | horns melting under noise, depth slider | **75/100** — hardware-backed, unambiguous knee | **2/5** — waiting on getting back into IBM accounts |
| `viz-4-randomness-texture-atlas.md` | non-QC | percolation/DLA/Turing/Ising gallery | **70/100** — strong hook + honest diagnostic | **4/5** — simple enough; beats the endless statistics randomness tests usually spit out |
| `viz-1-three-body-quantum-perturbation.md` | **QC** | divergence fan, phase-space ribbons | **68/100** — stunning but null-result risk | **4/5** — seems easy; most quantum heavy-lifting already done |

Likelihood = publishability. Want-to-do = my own appetite to build it (1–5).
2 quantum (viz-1, viz-2), 3 non-quantum (viz-3, viz-4, viz-5).
QRNG arms of all non-QC ideas source entropy from the **QEaaS API** — no new QC runs.

**Read as:** viz-3 + viz-5 are the safest standalone networking short papers; viz-2 is the safest
QC one; viz-4 is a strong diagnostic; viz-1 is the highest-visual/highest-risk bet.

*(viz-3 load-balancing-heat-theatre removed 2026-07-29 — already shipped as the ECMP web demo in
`TargetedDosColisionsAndRNGAngle/web/`; replaced by the DNS poison-race study.)*

## Complete
- `complete/DONE-calibration-guided-high-yield-qrng.md` → built as `CalibrationGuidedHighYieldQRNG/`
- `complete/DONE-ecmp-collision-dos.md` → built as `TargetedDosColisionsAndRNGAngle/`
