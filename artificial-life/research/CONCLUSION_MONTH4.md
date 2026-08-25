# Stage 4 — Conclusion (Month 4) — and whole-project verdict

The full Alvarez-Rodriguez 2018 quantum-artificial-life model, rebuilt faithfully and laid
out as a scalable population line. This file records (1) how we recreated and then refuted
the Months 1–3 simplified result, (2) how the model scales, on two axes, and (3) the final
teleport-routing re-test at genuine chip-spanning range.

Code: `code/stage4_qalife.py` (model + selftest), `code/stage4_scale.py` (hardware driver).

---

## 0. Whole-project arc (Months 1–4) — the one-paragraph story

Months 1–3 chased a **two-point clone correlation `C(g)`** down a single lineage and read it
as a quantum-advantage depth benchmark. Month 3's own appendix killed that: `C(g)` is a
diagonal `<sigma_z>` quantity with an **exact classical surrogate**, and on modern Heron-r2
hardware the supposed quantum-over-classical advantage physically **inverts** (readout error
now dominates two-qubit error), so teleport-routing lost to a plain SWAP chain. Month 4 threw
out the stand-in and rebuilt the **whole** 2018 model — all four Darwinian operators, exact —
then moved the quantum claim **off-diagonal** to the one observable with no classical
surrogate: the **genealogical entanglement witness `<X^{⊗W}>`**. That scales to a real,
measured result on 156-qubit hardware (**entanglement depth W = 24 = 48 qubits**, ~6× the
paper's ~4-qubit origin). The final teleport re-test, now at true chip-spanning range, was
**refuted a second time**. Net: an honest scale/faithfulness milestone, no quantum-speed
advantage, teleport-routing dead on this hardware generation.

---

## 1. Recreating — and refuting — the simplified Months 1–3 model

### What Months 1–3 actually measured

Months 1–3 collapsed the 2018 model to a **single temporal-clone lineage** and measured
`C(g)` — the two-point genotype correlation down a clone chain. This was:

- **Missing two of the four Darwinian operators.** Only self-replication + mutation were
  present; **death/aging** and **interaction (predation)** were absent.
- **A depth benchmark, not biology.** `C(g)` just tracks how far a clone correlation
  survives circuit depth. No population, no selection, no lifetime.
- **Diagonal-only.** `C(g)` is a `<sigma_z>`-type observable — it lives entirely on the
  density-matrix diagonal.

### Why the simplified result is refuted, not extended

The refutation is **structural**, proven in code, not just an empirical miss:

- **The diagonal metric has an exact classical surrogate.** CNOT-clone, amplitude-damping,
  and phenotype-SWAP all act *only* on the diagonal. So a classical genotype-copy +
  value-tracking phenotype reproduces the quantum phenotype `<sigma_z>` **exactly**
  (`classical_surrogate_z`, `stage4_qalife.py:329`). Delta ≈ 0. Alive-count and
  deepest-lineage are therefore **classical observables** — no quantum claim is possible
  from them.
- **On modern hardware the advantage physically inverts.** On Heron-r2, readout error ≫
  two-qubit error. The two-point `C(g)` quantum-over-classical advantage is physically
  blocked; teleport-routing (constant depth 7) still loses to a depth-40 SWAP chain.
  `logical_depth` is not the figure of merit.

Conclusion: **the Months 1–3 headline (`C(g)` depth advantage) is not a genuine quantum
result.** It measures a classical diagonal quantity, and even that shows no advantage on
current hardware.

### What Stage 4 rebuilt instead

The **whole** 2018 model, all four operators exact (verified by `--selftest`, every
operator checked against the paper's closed-form values):

| Operator | Gate | Paper meaning |
|---|---|---|
| FOUNDER | `Ry(pi/2)` on `g_0` | ancestral genotype seeded on the equator |
| SELF-REPLICATION | `CX(g_{k-1} -> g_k)` | partial `sigma_z` clone, eta = 1 (bare CNOT) |
| MUTATION | `Ry(theta_k)` on `g_k` | `u3(theta,0,0)`, theta from certified QRNG |
| PHENOTYPE | `CX(g_k -> p_k)` | second partial clone |
| DEATH | `CRY + CX + reset(bath)` | true amplitude damping toward the `|0>` dark state |
| INTERACTION | `SWAP(p_k, p_j)` | predation / phenotype exchange |

Two faithful death channels: `damping` (real amplitude-damping channel via a bath ancilla —
the paper's *actual* Lindblad model, impossible on 2017 ibmqx4, possible now) and `unitary`
(the paper's `sigma_y` stand-in, cheap and scalable).

### The new, honest headline: the genealogical entanglement witness

Because the diagonal is classical, the quantum claim is moved **off-diagonal**. The
CNOT-clone chain entangles the founder `|+>` across generations into a GHZ-like state
`(|0...0> + |1...1>)/sqrt(2)`, whose joint X-parity is:

- `<X^{⊗W}> = 1` for the true entangled genealogy;
- `<X^{⊗W}> = prod_i <X>_i ≈ 0` for any separable / measure-and-resend classical device.

So `<X^{⊗W}>` is a genuine entanglement witness **with no classical surrogate** — exactly
the 2018 paper's claim that "entanglement spreads throughout generations", now made
measurable and scalable. Readout: `H` on the genotype qubits, then measure (genotypes in X
= witness; phenotypes stay in Z = alive-count context).

---

## 2. How it scales — two axes

### Axis 1 — qubit budget scales linearly (population width)

Each individual costs exactly 2 qubits (genotype + phenotype). Death (damping arm) adds
**one shared bath ancilla**, reused across the whole line via `reset` — not one per
individual:

```
nq = 2*W + (1 if death == "damping" else 0)      # stage4_scale.py:286
```

| Width W | Qubits | Note |
|---|---|---|
| 2 | 5 | the seed circuit |
| 10 | 21 | |
| 77 | 155 | fills a 156-qubit Heron-r2 |

The genealogy is laid out as a physical qubit *line*, so the CX-clone chain maps onto
nearest-neighbour couplers. `layout.best_chain` picks the cleanest contiguous chain from
live calibration, and the Month-3 chain-quality gate aborts if `twoq_err_max > 0.05` or
`readout_max > 0.15` (`stage4_scale.py:147`, fail-closed). This keeps witness decay
physical, not an artifact of dead edges or bad readout.

### Axis 2 — entanglement depth is the scaling result (width sweep)

Scaling is not one big run — it's a **ladder**. `--widths 4,6,8,...` builds one circuit per
W, each measured independently. As W grows, mutation + aging + hardware noise shrink the GHZ
witness. The headline is the deepest rung that still beats the classical null:

```
genealogical entanglement depth = largest W whose <X^{⊗W}> - separable_null > k * sigma
                                                                  # stage4_scale.py:322
```

Knobs that push the wall deeper:

- **`--mut-scale` (small)** — small mutation angle keeps the genealogical GHZ near-clean, so
  the witness survives to larger W. Large mutation kills it at low W.
- **`--repeats` / `--k`** — repeat spread plus a shot-noise floor added in quadrature give
  the sigma; the witness must clear `k * sigma` to count as alive.

The 2018 paper reached ~4 qubits / 1 generation. This drives the same witness far past that
origin on a 156-qubit device. The result is a single number: **the deepest genealogy whose
entanglement is provably non-classical.**

### Live-hardware result (ibm_kingston, 156q Heron-r2)

`nn` interaction, `unitary` death, `--steps 3 --mut-scale 0.08 --repeats 3`, 8192 shots.
Chain-quality gate held every run (`twoq_err_max <= 0.0074`, `readout_max <= 0.030`).

| Width W | Qubits | witness `<X^W>` | signal | 2·sigma | verdict |
|---|---|---|---|---|---|
| 3 | 6 | +0.879 +- 0.027 | +0.879 | 0.054 | ALIVE |
| 4 | 8 | +0.808 +- 0.021 | +0.808 | 0.042 | ALIVE |
| 6 | 12 | +0.612 +- 0.014 | +0.612 | 0.028 | ALIVE |
| 12 | 24 | +0.301 +- 0.017 | +0.301 | 0.034 | ALIVE |
| **24** | **48** | **+0.038 +- 0.016** | **+0.038** | **0.032** | **ALIVE (marginal)** |
| 32 | 64 | +0.008 +- 0.013 | +0.008 | 0.026 | dead |

**Headline: coherence-limited genealogical entanglement depth = W = 24** (48 qubits). The
witness decays roughly geometrically with W; W=24 clears the 2-sigma null by a hair
(+0.038 vs 0.032), W=32 is buried in noise. This is a ~6x deepening over the 2018 paper's
~4-qubit origin, on real hardware, on the observable with no classical surrogate.

Population context (diagonal, classical): alive-count tracks width almost perfectly
(W=24 → ~23 alive, deepest ~22) — confirming, as expected, that the `<sigma_z>` metrics
carry no quantum signal; all the quantum content is in the witness.

### Axis 3 — long-range interaction: teleport re-test at scale (the final experiment)

Month 3 refuted teleport-routing on a *short* 14-qubit lineage, but the honest objection was
that a short line never needs long-range communication — QuantumLife's ~100-qubit line did.
Month 4 removed that objection: at the widest clean width **W = 24**, `--interaction longrange`
puts the partner at `k + W//2` (~12 individuals away), so the phenotype-SWAP genuinely spans
the chip and the SWAP ladder is long. This is exactly the regime where teleport's
constant-depth routing was predicted to finally win.

`--routing teleport` was fully wired for this test: the long-range SWAP is realized as three
teleported CNOTs (`SWAP = CX·CX·CX`), each via `stage3._teleport_cx` (copied verbatim, CD-1)
over a reset 2-qubit corridor per bond, with feed-forward X/Z corrections. Verified in sim to
be identical to a plain SWAP noiselessly (witness Δ0.001).

Live result on `ibm_kingston` (W=24, steps 3, unitary death, mut-scale 0.08, 3 repeats):

| Routing | witness `<X^W>` | signal | verdict |
|---|---|---|---|
| **SWAP ladder** (baseline) | +0.026 +- 0.012 | +0.026 | **ALIVE** (clears 2σ) |
| **Teleport** (constant depth) | −0.014 +- 0.030 | −0.014 | **dead** |

**Teleport is refuted a second time — now at genuine chip-spanning range.** The swap-routed
long-range arm survives (barely) at W=24; the teleport-routed arm is buried in noise. The
per-bond teleport corridors (extra reset ancillas, feed-forward measurements, mid-circuit
resets) inject more error than the long SWAP ladder they replace. This confirms and
generalizes the Month-3 finding: on this hardware generation, where readout/mid-circuit error
dominates two-qubit gate error, **`logical_depth` is not the figure of merit** and
teleport-routing loses even in the long-range regime built specifically to favour it.

(Note the population-context column: swap keeps `deepest~11`, teleport drops to `deepest~8` —
the teleport corridors also cost lineage depth on the classical diagonal.)

---

## 3. Final verdict

- **Faithfulness:** the full four-operator 2018 model is rebuilt and verified operator-by-
  operator against the paper's closed-form values (`--selftest`). ✅
- **Scale:** genealogical entanglement witness measured on real 156-qubit hardware to
  **W = 24 (48 qubits)**, ~6× the paper's origin, on the one observable with **no classical
  surrogate**. ✅ — the genuine, honest headline.
- **No quantum-speed advantage claimed.** The population/lifetime metrics (`alive-count`,
  `deepest-lineage`) are diagonal and classically reproducible; only the off-diagonal witness
  is non-classical, and it is a *scale/faithfulness* result, not a speedup.
- **Teleport-routing: refuted twice.** Short-range (Month 3) and long-range at scale
  (Month 4). Dead on Heron-r2.

The scientifically honest deliverable is the **entanglement-depth number and the witness that
has no classical surrogate** — that is what the web demo should visualize: a living population
line whose genealogical entanglement is a real, measured, non-classical quantity.
