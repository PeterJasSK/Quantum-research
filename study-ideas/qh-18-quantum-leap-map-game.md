# QH Idea 18 — Quantum Leap: a map-generation game that shows *why* a quantum proposal makes MCMC take fewer steps, and proves the reason is interference

**Tag: QUANTUM · qh · viz · effort: medium-high · QC: yes (exact browser sim ≤ 14 q + stored Heron runs) · master's thesis**

## Pitch
Quantum-enhanced MCMC (Layden et al., Nature 2023) proposes moves by letting a quantum state evolve for a short time
under the problem energy plus a mixing term. The amplitude spreads to configurations that are **far away but at
similar energy** — across energy barriers, without walking over them — so the proposed jump is both large and likely
accepted. Local moves must climb the barrier; uniform random jumps are far but usually land on a hill and are
rejected. The game makes this visible: the player's map is stuck in one valley, and they can walk, teleport, or take a
**quantum leap**, watching the amplitude cloud flow through the barrier and light up the other valleys. A
**"decohere" switch** replaces the quantum evolution with the classical random walk of the same generator: the cloud
then diffuses, lands on hills, and the advantage disappears. That switch is also the study: the same control is run on
Heron (dephasing inserted between Trotter steps), isolating coherence as the cause of the step advantage.

**Paper strength score: 70/100** — explains a Nature-line result visually with a falsifiable mechanism test on
hardware, strong figure, real thesis-sized engineering; docked because the advantage is per step, not wall-clock
(classical makes ~10⁴× more proposals per second), sizes are small, and a null on hardware is plausible.

## Map shape and the quantum lens
- The world is a large map (hundreds of tiles) drawn on the chip's coupling graph. Heavy-hex read as a game map:
  degree-3 nodes = rooms / towns, degree-2 nodes = corridors / roads, hexagons = blocks of the world. Square-lattice
  skin for IBM Nighthawk (native 4-cycles, easier frustration) if access exists (unverified).
- A classical local Metropolis chain generates the whole map continuously.
- The quantum part acts on one **lens**: a 12-tile hexagon block (one heavy-hex cell = 12 qubits, 4,096 configs), the
  size that is exact in the browser and cheap on Heron. The player drops the lens on a region that is stuck; the
  landscape panel shows that block; the leap rewrites the block in one accepted step (block / coarse-grained QeMCMC).
- Preset levels have stored Heron proposal matrices for their lens blocks; free play uses the exact simulator.

## What the player sees (one screen)
- **Left: the map.** Tiles on Heron's heavy-hex graph (one tile = one qubit), rules learned from an example map the
  player paints. Mixed rules → frustrated world with several distinct good maps (valleys).
- **Right: the landscape.** Every configuration as a dot: x = Hamming distance from the current map, y = energy.
  Valleys are clusters at low energy.
- **Three moves:**
  - *Walk* (local flip): dot moves one step, climbs the hill, mostly rejected.
  - *Teleport* (uniform): lands anywhere, almost always high energy, rejected.
  - *Quantum leap*: animated amplitude cloud |ψ(t)|² over the dots. Interference fringes; amplitude appears in distant
    low-energy valleys at roughly the same height. Measure → land there → accepted.
- **Two knobs the player tunes (the game mechanic):** evolution time t and mixing weight γ. Too short = a local walk;
  too long = scrambled = uniform teleport; the sweet spot in between (Orfi–Sels intermediate regime) is the skill.
- **Decohere switch:** same generator, no interference → diffusive cloud, advantage gone.
- **Noise slider:** ideal → Heron r3 → r2 → worse; watch the cloud blur and the step count rise (ε\*).
- **Honest panel:** steps to escape the valley for each move, and proposals per second (quantum loses on time).
- **Hardware mode:** overlay of proposal distributions measured on Heron (replayed from stored jobs) vs ideal.

Goal of a level: reach a different valley (a genuinely new map) in the fewest steps. Bots play local, uniform and
quantum with tuned knobs; the player tries to beat them.

## How it becomes a study
**Research question:** Is the step advantage of the quantum proposal on frustrated heavy-hex maps caused by coherent
interference — i.e. does it vanish when the same generator is applied incoherently — and does it survive on Heron?

**Hypothesis:** For frustrated rule sets, the coherent proposal gives a larger spectral gap than local, uniform and
the decohered control; on Heron the gap lies between ideal and decohered, and approaches decohered as error grows.

**Method:**
- Maps n = 8–14 tiles: exact state vector (browser and Python); full proposal matrix → exact Metropolis gap.
- Hardware, n ≤ 12: estimate the proposal matrix on Heron for three circuits — coherent quench, the same quench with
  random Z (dephasing) inserted between Trotter steps (decohered control), and the uniform proposal.
- Proposal asymmetry from T1 noise, measured from the matrix; Hastings correction or reject rule (formal angle with
  Korečko).
- Frustration sweep (fraction of mixed-sign rules) and noise sweep (gate folding, calibration tiers) → maps of where
  the advantage lives.

**Baselines:** local single-flip; uniform; decohered same-generator walk; parallel tempering; tensor-network proposal
(χ ≤ 8) where feasible; **exact classical block heat-bath** (enumerate all 2^n lens configs, sample exactly) — the
ceiling, which wins outright at n = 12 (4,096 states, microseconds).

**Comparison the game must show (lens-size slider):** ideal gap scaling δ ∝ 2^(−kn) with k_quantum 0.264,
k_local 0.94, k_uniform 0.948 (Layden; reproduced in RE B as 0.250 / 1.017 / 0.939). At n = 12 that is ~300–600×
fewer steps than local / uniform; exact enumeration still wins. As n grows, enumeration costs 2^n, local steps
~2^(1.0n), quantum steps ~2^(0.26n) with a polynomial circuit → the crossover against every classical method lies
at block sizes enumeration cannot reach (n ≳ 40), where Heron coherence is the open question. Measured hardware
points are plotted on the same axes.

**Metrics:** spectral gap δ and steps-to-new-valley per proposal; coherent − decohered gap difference; proposal
asymmetry; ε\*; proposals per second (reported, not hidden).

**Novel contribution:** a direct, hardware-measured test that the QeMCMC step advantage comes from interference
(coherent vs decohered same-generator control), delivered as an interactive game anyone can play.

## THE VISUALIZATION — "Two generators race" (revised 2026-11-19)
Same rules, same start map, same step budget; classical local Metropolis on the left, quantum-proposal Metropolis on
the right, running live.
- **Current map** per lane (big), and a **film strip** of every new distinct map accepted.
- **Coverage map** per lane: all 4,096 lens configurations as a 64 × 64 pixel grid; a pixel lights when the chain
  visits it, coloured by its valley (basin of attraction, precomputed by steepest descent). Classical lights one
  colour patch around the start; quantum lights patches of many colours. This is the main picture.
- **Counters:** steps, acceptance %, distinct maps, **distinct valleys found** (of the total that exist), mean tiles
  changed per accepted move.
- **Curves vs steps:** valleys found (both lanes, dashed line = total), and total-variation distance of the sampled
  distribution to the exact one — the real mixing metric. "Distinct configurations" alone can be gamed (a hot chain
  visits many), so valleys + TVD at the same temperature are the honest pair.
- **Toggles:** decohere (right lane becomes the incoherent same-generator walk), noise slider, hardware replay
  (proposals sampled from the measured Heron matrix), and a ghost **exact enumeration** lane as the ceiling.
- Proposal is exact in the browser: second-order Trotter of H = (1−γ)H_prob + γΣX on 4,096 amplitudes (symmetric
  A·B·A product → symmetric proposal, Metropolis valid).

Fallback single frame for the paper: the two coverage maps side by side after the same number of steps.

## Bounds test protocol (2026-11-19)
1. Reproduce first: Layden SK k-exponents (RE B already has 0.250 / 1.017 / 0.939 vs 0.264 / 0.94 / 0.948).
2. Metric: exact spectral gap δ of the Metropolis matrix built from the proposal matrix Q (n ≤ 12); fit
   ⟨δ⟩ ∝ 2^(−kn) over n = 6…12, 50–100 instances per n, bootstrap CI. Families: SK (comparability) and frustrated
   ±J on heavy-hex (hardware-native).
3. Noise types, one at a time, swept in strength: depolarizing, dephasing, amplitude damping (T1), readout
   (asymmetric 1→0), coherent over-rotation. Density matrix for n ≤ 10, trajectories for 12.
4. Per noise type: k(ε), ε\* where k_quantum = k_best classical; asymmetry ‖Q − Qᵀ‖; bias = TVD(π_noisy, Boltzmann)
   with plain Metropolis vs Metropolis–Hastings using the measured Q.
5. Baselines: local, uniform, decohered same generator, parallel tempering / cluster (empirical τ_int).
6. Randomness control arm: accept step and classical proposals fed by PRNG vs QRNG bits (C pool) — expected null,
   shows the advantage is not randomness quality.
7. Hardware (n ≤ 8–10, Heron r2, r3 if access): Q per basis state, coherent vs dephased circuit, measured
   asymmetry; place points on the simulated ε axis via calibration data; repeats on two days / two backends.
8. Fix metrics, instances and thresholds before the first hardware job.

## Connection to what already exists
- `artificial-life/web/` interactive quantum visualisation (first interactive quantum-alife viz) — same craft.
- QuantumPhantoms RE letter B-5 QeMCMC reproduction (none at 6 spins, 1.5× at 8) — starting code and sizes.
- qh-15 (ε\* threshold) and qh-17 (closed: no point inside the lungs) — this is where the QeMCMC line moved.
- edu-1 honest lab — sibling (falsification teaching); this one teaches a mechanism.

## Prior work (check before planning)
Layden 2023 (Nature, 2203.12497); Orfi–Sels 2024 (2408.07881, why the intermediate regime); Ferguson–Wallden 2025
(2405.04247); Marshall 2026 (2602.06171); Wootton ~2020 quantum procedural generation for games (verify venue);
Wave Function Collapse (classical). No known work tests coherent vs decohered same-generator proposals on hardware,
or presents QeMCMC as a game — verify.

## Bull case / Bear case / Likely outcome / Value if null
**Bull:** clear coherent > decohered gap in sim and on Heron at n ≤ 12; game is fun and used in teaching; QCE27 paper.
**Bear:** on hardware the coherent and decohered gaps are indistinguishable at these sizes.
**Likely:** strong in sim, partial on hardware (coherent above decohered at the smallest maps, merging as n grows).
**Value if null:** "on today's hardware the interference that drives QeMCMC is already washed out at n = X" is a
measured, visual statement of exactly where the method stands — and the game still teaches the mechanism.

## Thesis — master's thesis + IEEE short paper (6–8 pp)
**Central question:** why does a quantum proposal need fewer MCMC steps, and does that reason survive on hardware?
**Single defended claim:** the step advantage is caused by interference: it disappears under the decohered control,
measured on Heron at n ≤ 12.
**Thesis chapters:** 1 exact simulator + game engine (engineering) · 2 maps from examples on heavy-hex · 3 coherent
vs decohered on hardware + asymmetry · 4 honest verdict (per step vs wall clock).
**Target venue:** IEEE QCE 2027 (Applications or Education/Outreach); IEEE Conference on Games as alternative.
**Compelling-study likelihood: 70/100.**
