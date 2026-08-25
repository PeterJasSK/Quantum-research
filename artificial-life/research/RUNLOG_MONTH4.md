# RUNLOG — Month 4 (QDEP / Quantum Artificial Life) — THE FULL 2018 MODEL, AT SCALE

**Mission (2026-08-25).** Depth-benchmarking a single clone chain has no scientific value (Month 3
Appendix). Teleport died only because a 14-qubit lineage is too short to need long-range communication —
QuantumLife's ~100-qubit line *did* need it. So Month 4 changes target:

1. **Recreate the FULL Alvarez-Rodriguez 2018 model** — all four biomimetic operators
   (self-replication, mutation, interaction between individuals, death), faithful to the paper, not the
   reduced single-lineage stand-in the QDEP line collapsed to.
2. **Scale it to the largest healthy line/population a 156-qubit Heron-r2 sustains** — a genuine
   population of individuals evolving under the full cycle, in the spirit of QuantumLife.
3. **Then, and only then, re-test teleport** — the long-range *interaction* between distant individuals
   is where constant-depth routing may finally beat the SWAP ladder, because now the interactions
   genuinely span the chip.

**Headline (both reported).** (a) **alive-population** = individuals whose phenotype ⟨σz⟩ is still above
the alive-threshold after T life-cycle steps; (b) **deepest surviving lineage** = the longest continuous
genealogical line still alive. On 156-qubit `ibm_marrakesh`.

**Honesty (carried from Month 3).** Scale/application milestone, not new physics, not quantum advantage.
The classical surrogate arm is run alongside so every "life" claim has its separable null.

```
cd artificial-life/code
```

---

## The EXACT 2018 operators (from Alvarez-Rodriguez, Sanz, Lamata, Solano, Sci. Rep. 8:14793, 2018)

Each **individual = 2 qubits**: a **genotype** g and a **phenotype** p. Genotype carries inherited info
(⟨σz⟩); phenotype's ⟨σz⟩ is the lifetime/"alive" observable, degraded by aging.

| operator | EXACT 2018 gate | note |
|----------|-----------------|------|
| **self-replication** | `CNOT` partial σz-clone, applied **twice**: g_parent→g_child (blank), then g_child→p_child (blank) | exact ⟨σz⟩ copy, **η=1, NO contraction** (the QDEP `eta=0.9` was a stand-in; drop it) |
| **mutation** | `u3(θ,0,0) = Ry(θ)` on the genotype | θ from the certified QRNG stream (CD-7) |
| **death / aging** | dissipation toward the `\|0⟩` dark state, implemented as a sequence of small σy rotations `Ry(δ)` per time step on the phenotype (paper: `u3(π/8,0,0)`); Lindblad `σ=\|0⟩⟨1\|` | death = phenotype reaches dark state (⟨σz⟩→+1 i.e. \|0⟩) |
| **interaction** `U_I` | **SWAP of the two phenotype qubits** of the interacting pair | each individual's phenotype ends reflecting the *opposite* genotype (predation/exchange), exactly the paper's Table-1 map |

Faithfulness check we must reproduce in sim before any QC:
* self-replication: after CNOT, `⟨σz⟩_child == ⟨σz⟩_parent` (exact) — precursor `cos θ|0⟩+sin θ|1⟩` → `cos θ|00⟩+sin θ|11⟩`.
* interaction: from `|g1 p1 g2 p2⟩`, `U_I` sends `|0011⟩→|0110⟩`, `|1100⟩→|1001⟩` (phenotype SWAP); the paper's amplitudes must match.
* aging: `⟨σx⟩` decays as `cos θ1 cos θ2 …` per applied `Ry(δ)` step (paper Eq. 1-2).

---

## The scaled circuit (Month 4 design)

A **line of individuals** where the line *is* the genealogy (unifies population + lineage depth):

* individual `k` occupies 2 qubits `(g_k, p_k)`; a length-`W` population = `2W` qubits (≈65 on 156 after
  dead-qubit avoidance via the Month-3 `layout.best_chain` + chain-quality gate).
* build order per individual `k`:
  1. **self-replication** — `CNOT(g_{k-1} → g_k)` clones the parent genotype into blank `g_k`
     (`k=0` founder seeded on the equator via `Ry(π/2)` so ⟨σz⟩ actually varies, the Month-3 fix);
  2. **mutation** — `Ry(θ_k)` on `g_k`, `θ_k` from QRNG;
  3. **phenotype** — `CNOT(g_k → p_k)` (the second partial clone);
  4. **aging** — `Ry(δ · age_k)` on `p_k`, `age_k` = steps since birth → older individuals drift to the
     dark state (death);
  5. **interaction** — `U_I` = `SWAP(p_k, p_j)` with a partner `j`:
     * **`--interaction nn`** — `j = k−1` (adjacent, no routing),
     * **`--interaction longrange`** — `j` a distant individual (SWAP ladder *or* teleport routes it),
     * **`--interaction both`** — run both arms, compare (this is the teleport re-test at scale).
* **readout** — terminal `⟨σz⟩` on every phenotype (defer-readout: one measurement round, the Month-3
  lesson that mid-circuit measure is the worst channel).

**Metrics** from the terminal phenotype ⟨σz⟩ vector:
* **alive-population** = `#{k : ⟨σz⟩_{p_k} < alive_thresh}` (alive = not yet at the |0⟩ dark state);
* **deepest surviving lineage** = largest `k*` such that individuals `0..k*` are all still alive
  (the unbroken genealogical line);
* **classical surrogate** = measure-and-resend null, same as S1/S3, for the honest baseline.

---

## Two new files

* **`stage4_qalife.py`** — the full model + sim. Self-contained operators (CD-1: copied, not imported),
  `build_population(...)` that lays out the line and applies the 5-step life-cycle, statevector
  `unit_test()` that verifies each operator against the paper's exact values, and a `--sim` CLI that
  emits a `research_runs/*.json` in the established shape. **Nothing hits hardware until unit_test passes.**
* **`stage4_scale.py`** — the hardware driver. Reuses `stage4_qalife.build_population`, the Month-3
  `layout.best_chain` + `--max-twoq-err/--max-readout-err/--allow-bad-chain` gate, `QRNGClient`, and the
  `pipeline_common` connect/sampler. Packs the max population on the pinned backend, runs T life-cycle
  steps, `--interaction {nn,longrange,both}`, `--routing {swap,teleport}` on the long-range arm, and
  reports both headline metrics + the classical surrogate.

---

## The entanglement witness (the QUANTUM headline) — added after Phase-1 sim

The phenotype ⟨σz⟩ alive-count is a **classical** observable: CNOT-copy, amplitude-damping, and
phenotype-SWAP all act only on the diagonal, so a death-matched classical surrogate reproduces
alive-count / deepest-lineage **exactly** (verified: quantum alive == classical alive on both arms). A
population of ⟨σz⟩ traits on a quantum chip = a classical cellular automaton. **Not** quantum life.

The genuinely quantum signal is the **genealogical entanglement witness** `⟨σx^{⊗W}⟩` over the genotype
line. The CNOT-clone chain spreads the founder `|+⟩` into a GHZ `(|0…0⟩+|1…1⟩)/√2` across generations;
`⟨X^{⊗W}⟩ = 1` for GHZ, while any separable / measure-and-resend state factorizes to `∏⟨X⟩_i ≈ 0`. So the
joint X-parity has **no classical surrogate** — exactly the paper's "entanglement spreads throughout
generations". **Headline = genealogical entanglement depth**: the largest width W whose witness beats the
separable null by k·σ. This is the real improvement over the 2018 base (~4 qubits / 1 generation).

## PHASE 1 — build + sim-verify (no QC) — DONE 2026-08-25

1. `python stage4_qalife.py --selftest` — **PASS**: all four operators vs the paper (self-replication
   CNOT copies ⟨σz⟩ exactly η=1; interaction U_I swaps phenotypes so each reflects the opposite genotype;
   aging→|0⟩ dark state monotone for BOTH unitary and true-amplitude-damping death; witness =1 on a clean
   GHZ genealogy and joint==product on a separable state).
2. `python stage4_scale.py --sim --widths 2,3,4,5,6 --steps 3 --interaction nn --death unitary` —
   witness ≈ 0.93–0.97 at every width, separable null = 0.000, entanglement depth **saturates at the max
   width tested** (noiseless). Like Month-3 depth, **sim can't find the ceiling — it is a hardware number.**
3. **Key finding — the death arm splits the headline:**
   * **unitary death** (product-state phenotype) keeps the genotype line a clean GHZ → witness survives
     deep → this is the arm that carries the **entanglement-depth headline**.
   * **damping death** (faithful Lindblad dissipation on a CNOT-entangled phenotype) **self-decoheres the
     witness even in noiseless sim** (≈0.000): cloning+dissipating the phenotype effectively measures the
     genotype in Z, collapsing the X-coherence. This reproduces the paper's own observation that ⟨σx^{⊗4}⟩
     decays under dissipation. So the damping arm is the **faithful population-dynamics arm** (alive-count),
     the unitary arm is the **entanglement arm**. Both are honest; they measure different things.
4. Sanity: large `--steps` (aging) kills the whole line (alive→0); small `--mut-scale` keeps the witness
   high (mutation = small variation), confirming the operating knobs.

## PHASE 2 — scale on hardware (pinned marrakesh, gated chain)

The ceiling is a **hardware** number (sim saturates). Push width; find the largest W whose genealogical
entanglement witness still beats the classical null = the headline entanglement depth. Chain-quality gate
(dead-edge / bad-readout abort) is built in — Month-3 lesson, so no run reports a chain-limited ceiling.

0. **step 0 — smallest paper-faithful model, 1 repeat, circuit exposed.** The 2-individual model
   (the paper's minimal interaction experiment): FOUNDER + SELF-REPLICATION + MUTATION + PHENOTYPE +
   DEATH(true amplitude damping) + INTERACTION, all four operators visible as labeled gate blocks.
   `--dump-circuit` prints + saves the annotated diagram + QASM so every Darwinian quality can be read off
   the circuit; then it runs 1 repeat on hardware. (Witness reads ~0 on the damping arm by construction —
   step 0 is for circuit analysis + confirming the model runs, not the witness headline.)
```
python stage4_scale.py --no-sim --backend ibm_marrakesh --widths 2 --steps 2 --interaction nn --death damping --mut-scale 0.08 --repeats 1 --dump-circuit --name qalife_m4p2s0
```
   5 qubits (g0,p0,g1,p1 + shared bath). Add `--draw-only` to inspect the circuit WITHOUT submitting.


1. **small live sanity** — confirm the full model runs on chip and the gate holds:
```
python stage4_scale.py --no-sim --backend ibm_kingston --widths 3,4 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
```

**RUN**  (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 3,4 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[3, 4] steps=3 interaction=nn death=unitary on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00172, 'twoq_err_max': 0.00199, 'readout_max': 0.01099, 'sx_max': 0.000448}
  job 1: da6jqq46l22c73dme940 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jqu46l22c73dme98g (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jr1u0ukec73825l9g (8,192 shots) ... done (qpu 4.00s)
  W= 3  witness<X^W>=+0.879+-0.027  sep=-0.000  signal=+0.879  ALIVE  | pop alive~2.0/3 deepest~1.0
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00164, 'twoq_err_max': 0.00199, 'readout_max': 0.01099, 'sx_max': 0.000448}
  job 1: da6jr5bsq5js73biqs40 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jr96sidac73ae8htg (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jrd6sidac73ae8i1g (8,192 shots) ... done (qpu 4.00s)
  W= 4  witness<X^W>=+0.808+-0.021  sep=+0.000  signal=+0.808  ALIVE  | pop alive~3.0/4 deepest~2.0

  HEADLINE genealogical entanglement depth: W=4 (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p2_nn_unitary_ibm_kingston_20260825-090118.json



2. **push width (entanglement depth)** — grow the widths until the witness signal drops below k·σ; that W
   is the coherence-limited genealogical entanglement depth (2·W qubits; W≈65 fits 156):
```
python stage4_scale.py --no-sim --backend ibm_kingston --widths 6,12,32 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
```

**RUN** : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 6,12,32 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[6, 12, 32] steps=3 interaction=nn death=unitary on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00173, 'twoq_err_max': 0.00241, 'readout_max': 0.01343, 'sx_max': 0.000497}
  job 1: da6js0esidac73ae8io0 (8,192 shots) ... done (qpu 0.00s)
  job 1: da6js4bsq5js73biqt80 (8,192 shots) ... done (qpu 0.00s)
  job 1: da6js7usidac73ae8ivg (8,192 shots) ... done (qpu 0.00s)
  W= 6  witness<X^W>=+0.612+-0.014  sep=-0.000  signal=+0.612  ALIVE  | pop alive~5.0/6 deepest~4.0
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00175, 'twoq_err_max': 0.00285, 'readout_max': 0.02954, 'sx_max': 0.000738}
  job 1: da6jsck6l22c73dmeas0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jshk6l22c73dmeb10 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jsmc6l22c73dmeb60 (8,192 shots) ... done (qpu 4.00s)
  W=12  witness<X^W>=+0.301+-0.017  sep=+0.000  signal=+0.301  ALIVE  | pop alive~11.0/12 deepest~10.0
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00232, 'twoq_err_max': 0.00743, 'readout_max': 0.0271, 'sx_max': 0.001055}
  job 1: da6jt7esidac73ae8k0g (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jtejsq5js73biqui0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jtlrsq5js73biquog (8,192 shots) ... done (qpu 4.00s)
  W=32  witness<X^W>=+0.008+-0.013  sep=-0.000  signal=+0.008  dead   | pop alive~32.0/32 deepest~31.0

  HEADLINE genealogical entanglement depth: W=12 (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p2_nn_unitary_ibm_kingston_20260825-090633.json


````
python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
````
**RUN** : (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction nn --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p2
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[24] steps=3 interaction=nn death=unitary on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00201, 'twoq_err_max': 0.00491, 'readout_max': 0.0271, 'sx_max': 0.001055}
  job 1: da6juks6l22c73dmed70 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jur46l22c73dmede0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6jv1jsq5js73bir09g (8,192 shots) ... done (qpu 4.00s)
  W=24  witness<X^W>=+0.038+-0.016  sep=-0.000  signal=+0.038  ALIVE  | pop alive~23.0/24 deepest~22.0

  HEADLINE genealogical entanglement depth: W=24 (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p2_nn_unitary_ibm_kingston_20260825-090905.json


   Watch the chain line each run; if the gate aborts, marrakesh drifted — wait for recal or pin another
   clean backend. Headline = the deepest surviving W.

**CONCLUSION (width sweep, `ibm_kingston`, nn / unitary, steps 3, mut-scale 0.08, 3 repeats).** Witness
decays roughly geometrically with W: W3 +0.879, W4 +0.808, W6 +0.612, W12 +0.301, **W24 +0.038 (marginal,
signal just clears 2σ≈0.032)**, W32 +0.008 (dead). **Coherence-limited genealogical entanglement depth =
W = 24 (48 qubits)** — the widest clean width. ~6× past the 2018 paper's ~4-qubit / 1-generation origin,
on the observable with no classical surrogate. W=24 is the operating width for steps 3-4 below.

3. **population arm (context)** — the faithful-death alive-count / deepest-lineage, same widths,
   `--death damping` (witness ≈0 here by construction — this arm is for the population figure, not the
   quantum claim).
```
python stage4_scale.py --no-sim --backend ibm_kingston --widths 6,12,24 --steps 3 --interaction nn --death damping --mut-scale 0.08 --repeats 3 --name qalife_m4p3_pop
```
(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 6,12,24 --steps 3 --interaction nn --death damping --mut-scale 0.08 --repeats 3 --name qalife_m4p3_pop
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[6, 12, 24] steps=3 interaction=nn death=damping on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00171, 'twoq_err_max': 0.00247, 'readout_max': 0.0144, 'sx_max': 0.000448}
  job 1: da6k3grsq5js73bir6q0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6k3ljsq5js73bir710 (8,192 shots) ... done (qpu 4.00s)
  job 1: da6k3p3sq5js73bir7ag (8,192 shots) ... done (qpu 4.00s)
  W= 6  witness<X^W>=+0.009+-0.012  sep=+0.000  signal=+0.009  dead   | pop alive~6.0/6 deepest~5.0
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00175, 'twoq_err_max': 0.00285, 'readout_max': 0.02954, 'sx_max': 0.000738}

(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 12,24 --steps 3 --interaction nn --death damping --mut-scale 0.08 --repeats 3 --name qalife_m4p3_pop
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[12, 24] steps=3 interaction=nn death=damping on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00175, 'twoq_err_max': 0.00285, 'readout_max': 0.02954, 'sx_max': 0.000738}
  job 1: da6kdvesidac73ae9ahg (8,192 shots) ... done (qpu 4.00s)
  job 1: da6kedrsq5js73birkqg (8,192 shots) ... done (qpu 4.00s)
  job 1: da6keiu0ukec73826f0g (8,192 shots) ... done (qpu 4.00s)
  W=12  witness<X^W>=-0.002+-0.015  sep=+0.000  signal=-0.002  dead   | pop alive~12.0/12 deepest~11.0
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.002, 'twoq_err_max': 0.00491, 'readout_max': 0.0271, 'sx_max': 0.001055}
  job 1: da6kes6sidac73ae9bhg (8,192 shots) ... done (qpu 4.00s)
  job 1: da6kf260ukec73826fig (8,192 shots) ... done (qpu 4.00s)
  job 1: da6kf83sq5js73birlo0 (8,192 shots) ... done (qpu 4.00s)
  W=24  witness<X^W>=-0.011+-0.015  sep=+0.000  signal=-0.011  dead   | pop alive~24.0/24 deepest~23.0

  HEADLINE genealogical entanglement depth: none survived (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p3_pop_nn_damping_ibm_kingston_20260825-094338.json


4. **teleport re-test at scale (Phase 2b)** — at the widest clean W, `--interaction longrange` with
   `--routing swap` vs `--routing teleport`. **Now** the interaction genuinely spans the chip (partner =
   k+W//2, ~W qubits away), so the SWAP ladder is long and teleport's constant-depth routing may finally
   win — the Month-3 prediction that teleport needs true long range.

   **`--routing teleport` now WIRED** (2026-08-25). The long-range phenotype SWAP is realized as three
   teleported CNOTs (`SWAP = CX·CX·CX`), each routed via `_teleport_cx` (copied verbatim from
   `stage3_teleport.py` into `stage4_qalife.py`, CD-1) over a 2-qubit corridor per bond that is reset
   between CNOTs; feed-forward X/Z corrections make it a valid SWAP for all outcomes. Adds `2·(W//2)`
   corridor ancillas + a `tel` feed-forward register; genotype/phenotype qubit indices are unchanged, so
   the witness/pz readout is untouched. `run_sampler` reads only the named `c` register (tel ignored — the
   feed-forward path needs no post-selection). Verified in sim: teleport ≡ plain SWAP noiselessly
   (witness Δ0.001, pz identical). NB: the quality gate still sizes a `2W`-qubit clean chain; the corridor
   ancillas exceed it, so `opt_level=3` free-routes the full circuit (initial-layout pin skipped, stage3
   precedent).
```
# swap-routed baseline (runs today)
python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction longrange --routing swap --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p4_swap
````
**RUN** (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction longrange --routing swap --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p4_swap
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[24] steps=3 interaction=longrange death=unitary on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00201, 'twoq_err_max': 0.00491, 'readout_max': 0.0271, 'sx_max': 0.001055}
  job 1: da6kg2c6l22c73dmf51g (8,192 shots) ... done (qpu 4.00s)
  job 1: da6kg8c6l22c73dmf59g (8,192 shots) ... done (qpu 4.00s)
  job 1: da6kgds6l22c73dmf5ig (8,192 shots) ... done (qpu 4.00s)
  W=24  witness<X^W>=+0.026+-0.012  sep=+0.000  signal=+0.026  ALIVE  | pop alive~23.0/24 deepest~11.0

  HEADLINE genealogical entanglement depth: W=24 (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p4_swap_longrange_unitary_ibm_kingston_20260825-094609.json

```
# teleport-routed (WIRE --routing teleport FIRST: reuse stage3._teleport_cx)
python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction longrange --routing teleport --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p4_teleport
```

**RUN**: (base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage4_scale.py --no-sim --backend ibm_kingston --widths 24 --steps 3 --interaction longrange --routing teleport --death unitary --mut-scale 0.08 --repeats 3 --name qalife_m4p4_teleport
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 4 SCALE: widths=[24] steps=3 interaction=longrange death=unitary on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00201, 'twoq_err_max': 0.00491, 'readout_max': 0.0271, 'sx_max': 0.001055}
  job 1: da6kh4esidac73ae9drg (8,192 shots) ... done (qpu 6.00s)
  job 1: da6khe6sidac73ae9e70 (8,192 shots) ... done (qpu 6.00s)
  job 1: da6khtrsq5js73biroj0 (8,192 shots) ... done (qpu 6.00s)
  W=24  witness<X^W>=-0.014+-0.030  sep=-0.000  signal=-0.014  dead   | pop alive~23.3/24 deepest~8.0

  HEADLINE genealogical entanglement depth: none survived (deepest width whose witness beats the classical null by 2.0sigma)
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/qalife_m4p4_teleport_longrange_unitary_ibm_kingston_20260825-094922.json



## PHASE 3 — web demo + preprint

Same as Month-3 Phase 3, but the visual is a living **population line** over time (birth, aging,
interaction, death) with the measured alive-count and deepest-lineage overlaid — QuantumLife-style, every
number a real measurement.
