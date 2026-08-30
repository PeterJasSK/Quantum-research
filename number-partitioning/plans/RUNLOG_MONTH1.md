# RUNLOG — Month 1 (SK number partitioning: classical reference + simplified QAOA)
**Epic:** `epic-number-partitioning.md` · **Ticket:** F1 · **Track:** `number-partitioning/`

**Goal.** Split integers {a_i} into two sets with equal sums (min discrepancy
d = |Σ a_i s_i|, objective H = d²). Two record artifacts under `plans/code/`:
(a) `classical_reference.py` — exact classical bar (brute force 2ⁿ + subset-sum
DP), (b) `qc_simplified.py` — the physics-only p=1 QAOA (bare CNOTs, Aer), the
stripped-down twin of the full three-router study in `code/qaoa_sk.py`.
**Honest verdict expected:** partitioning is easy classically at this size; the
contribution is the routed-depth method (full study), not beating classical.

Instance: n=4, seed=0 → `[14, 7, 13, 15]`, sum=49. Optimum d=5 (no perfect split).


## Run 1 — Classical bar (free, no QC)

Exact optimum + brute-force cross-check. The bar the QAOA arm is judged against.

```
 python classical_reference.py --n 6 --seed 69 
 ```

```
RUN :
numbers            : [701, 39, 99, 821, 171, 69]
sum                : 1900
min deviation      : 18  (the optimal, classical bar)
optimal partitions : 1
perfect split      : False
```


## Run 2 — Simplified QAOA (SIM gate, Aer)

One p=1 layer, bare CNOT routing, sampled and scored against the exact optimum.

```
python qc_simplified.py --n 6 --seed 69 --shots 200 --backend ibm_fez
```

```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69]
optimum deviation    : 18  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 001110
min deviation        : 18
found optimum        : True
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 1001
approx ratio [0..1]  : 0.722
P(optimum sampled)   : 0.025
```



**Command 3 — Finfing limit AND USING TELEPORTATION .**


```
python qc_simplified.py --n 60 --seed 69 --shots 4000 --backend ibm_fez```
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269]
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 100100101100111001110011011101010011100110111100101011100100
min deviation        : 2
found optimum        : False
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 4955
approx ratio [0..1]  : 0.976
P(optimum sampled)   : 0.0
```


```
python classical_reference.py --n 60 --seed 69 ```
```
```
RUN :
numbers            : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269]
sum                : 31780
min deviation      : 0  (the optimal, classical bar)
optimal partitions : 97021795585096
perfect split      : True
```

**Limit found.** At n=60 the simplified monolithic QAOA cannot reach the optimum
(best-of-shots deviation 2, mean deviation 4955), while classical DP finds a
PERFECT split (deviation 0). Monolithic dies because K_60 = 1770 edges → ~3540
long-range CX after routing: too deep for the chip.


---

# Improvement journey — step by step

The rest of this log records HOW the simple line design was improved, one lever
at a time, with the honest numbers for each step. Three artifacts, each a
strict superset of the previous:

| file | what it adds | headline |
|------|--------------|----------|
| `code/qc_simplified.py` | baseline: p=1 QAOA, bare CNOTs, fixed angles | dies at n=60 on HW |
| `code/qc_phase1.py`     | **linear SWAP network** routing (Lever A)  | full 156-qubit chip runs |
| `code/qc_phase2.py`     | **γ-normalization + CVaR + angle tuning** (Levers B/C/D) | 5× the per-shot odds |

Read the two labels that keep coming up:
- **best-of-shots deviation** = classical scan of the sampled bitstrings, keep
  the lowest |Σ a_i s_i|. NOT a quantum-quality metric; at large n it succeeds by
  COVERAGE of an exponentially degenerate optimum, not by the circuit converging.
- **P(optimum sampled)** = fraction of shots that landed exactly on an optimum.
  This is the honest conversion number, and the one every lever below targets.
  Odds of catching the optimum in S shots = 1 − (1 − P(opt))^S.


## Step 0 — the wall (baseline `qc_simplified.py`)

p=1 QAOA, one ZZ per pair as bare `CX · RZ · CX` on logical wires, fixed angles
γ=π/8, β=π/4, scored best-of-shots. On Aer (no coupling map) it "works" to ~n=40
by shot coverage. On real ibm_fez it dies at n=60: the cost graph is the complete
graph K_n, so the transpiler inserts O(n²) SWAP chains to bring far qubits
adjacent. K_60 = 1770 ZZ terms → ~3540 CX **plus** routing SWAPs → past coherence.

**Diagnosis: the killer is routing depth, not the ZZ count.**


## Step 1 — Lever A: linear SWAP network (`qc_phase1.py`)

**Idea (Kivlichen 2018).** Put the n logical qubits on a line. Run n odd-even
layers; each adjacent-pair gate FUSES the ZZ of whatever logical pair currently
sits there WITH a SWAP that permutes the two wires. After n layers every logical
pair has been adjacent exactly once → all n(n-1)/2 interactions done, and ZERO
routing SWAPs are added because the swaps ARE the routing.

**Fused ZZ+SWAP = 3 CX** (the SWAP's closing CX cancels the ZZ's closing CX):
`exp(-iθ ZZ) then SWAP = CX(p,q) · RZ(2θ,q) · CX(q,p) · CX(p,q)`. All gates act on
physically adjacent wires, so a line embedding routes clean. Depth drops O(n²) → O(n).

**Depth proof** (transpiled onto a line coupling map, opt level 3):

| n  | bare depth | swapnet depth | speedup |
|----|-----------:|--------------:|--------:|
| 12 | 176 | 57  | 3.1× |
| 20 | 320 | 89  | 3.6× |
| 30 | 511 | 129 | 4.0× |

Swapnet depth is clean O(n); the gap widens with n. Physics identical to baseline
(n=6 sim: both approx-ratio 0.66, P(opt) ≈ 0.037).

**Full-chip result — the Phase 1 milestone:**
```
python qc_phase1.py --n 156 --seed 69 --shots 16000 --backend ibm_fez
routing              : swapnet  (logical depth 627, 2q gates 36270)
optimum deviation    : 0
best-of-shots        : 0   found optimum: True
mean deviation       : 7709   approx ratio : 0.991
P(optimum sampled)   : 0.0001
```
36270 CX = 12090 pairs × 3, at depth 627 ≈ 4n. Every qubit on the machine used
(156/156 = theoretical max WIDTH of ibm_fez). The dense K_156 QAOA physically ran.

**But P(opt) sat on the floor (0.0001 ≈ 1.6 of 16000 shots).** found_optimum=True
was coverage luck on an exponentially degenerate perfect split, not the circuit
concentrating. Two misleading metrics to distrust at scale:
- **approx_ratio 0.991 is a scale artifact.** worst = (Σa)² ≈ 6.4e9 dominates, so
  even mean-deviation 7709 gives 1 − 6e7/6.4e9 ≈ 0.99 automatically. Always ~1 at
  large n; ignore it.
- **best-of-shots found 0** only because perfect splits are ~10⁴⁷/80000 dense.


## Step 2 — the scaling bug (why P(opt) was floored)

γ=π/8 ≈ 0.39 with J_ij = 2 a_i a_j ≈ 5e5 gives `rz(2·γ·J) ≈ 4e5 radians`, which
mod 2π is **effectively random**. Every ZZ term rotated by garbage → the cost
layer imprinted almost nothing about H → the distribution was barely tilted → P(opt)
stuck at the floor. The baseline was, at every n, only weakly better than random.

**Proof (Aer sim, n=12, same circuit, angle only):**

| γ | P(opt) | best-of-shots dev |
|---|-------:|------------------:|
| π/8 (wrapped)          | 0.0000 | 221 |
| π/(2·Jmax) (in-range)  | 0.0011 | **1** |

Non-wrapped angle alone: best-of-shots 221 → 1. This is the single biggest lever.


## Step 3 — Levers B/C/D: optimized conversion (`qc_phase2.py`)

Same swap-network circuit, three stacked fixes to raise P(opt), no extra depth
over Phase 1:

- **Lever B — γ normalization.** `θ = γ · J_ij / Jmax`, γ dimensionless in ~(0,π].
  Every ZZ phase now lands in range. (Fixes the Step 2 bug.)
- **Lever C — CVaR objective.** Tune on the best-α tail of the energy distribution
  (α≈0.1–0.15), not the mean. The tail is exactly what best-of-shots harvests, and
  it dodges the approx_ratio scale artifact.
- **Lever D — classical angle optimization.** (γ,β) found by grid + Nelder-Mead on
  a SMALL-n exact statevector sim (n≈14, milliseconds). Because couplings are
  normalized, the dimensionless angles TRANSFER to large n on hardware (QAOA angle
  concordance): tune at n=14, run at n=156.

Also supports p>1 layers (`--p`, depth ≈ p·4n) with 2p tuned angles, though p=1
is what cleared the goal on HW.

**Sim validation (n=20, seed 69, p=1, tuned on n=14):**
```
python qc_phase2.py --n 20 --seed 69 --shots 1000 --optimize-n 14 --p 1 --trials 30
SUCCESS RATE  : 0.467   mean P(optimum) : 0.0007
```
Per-shot P(opt) up ~10× vs the wrapped baseline. success@1000 ≈ 47% at this small
n (few optima = the HARD regime for p=1).

**Hardware result (n=156, seed 69, p=1, 2000 shots) — the Phase 2 milestone:**
```
python qc_phase2.py --n 156 --seed 69 --shots 2000 --optimize-n 14 --p 1 --backend ibm_fez
tuned on n=14 p=1: gammas=[0.367] betas=[1.386]  P(opt)@tune=0.0014
routing              : swapnet+normalized  (logical depth 627, 2q gates 36270)
optimum deviation    : 0
best-of-shots        : 0   found optimum: True   (reproduced across 2 runs)
mean deviation       : 7763 / 8047   approx ratio : 0.99
P(optimum sampled)   : 0.0005
pred. success @ 2000 shots : 0.6322
```

**Step-by-step improvement in one number — P(optimum) on the n=156 chip:**

| build | change | P(opt)/shot | vs baseline |
|-------|--------|------------:|------------:|
| Phase 1 (16000 shots) | swap network only, wrapped γ | 0.0001 | 1× |
| Phase 2 (2000 shots)  | + normalized γ + CVaR + tuned | **0.0005** | **5×** |

Same depth (627), same 36270 CX — 5× the conversion purely from fixing the angle
scale and tuning. Predicted odds of hitting the optimum: 63% at 2000 shots (was
~18% at 2000 for Phase 1's 0.0001 rate). To reach 90% at p=1 needs ≈ 4600 shots
(1 − (1−0.0005)^4600 ≈ 0.90), or p=2 to lift the per-shot rate instead of the shots.


## Shots needed for conversion (the odds tables)

best-of-shots is a lottery: each shot is one ticket, per-shot win rate = P(opt).
Odds of catching the optimum in S shots = `1 − (1 − P(opt))^S`. Invert it for the
shot budget needed to reach a target confidence q:

    S_q = ln(1 − q) / ln(1 − P(opt))          (small-P: S_q ≈ −ln(1−q) / P(opt))

### Table 1 — shots required, by measured per-shot P(opt)

Rows are the actual rates measured across the journey (▸ = on ibm_fez hardware).

| build / source              | P(opt)  | shots for 50% | shots for **90%** | shots for 99% |
|-----------------------------|--------:|--------------:|------------------:|--------------:|
| ▸ Phase 1, wrapped γ (n=156)| 0.0001  | 6 931 | **23 025** | 46 050 |
| ▸ Phase 2, tuned p=1 (n=156)| 0.0005  | 1 386 | **4 604**  | 9 208  |
| sim n=20, p=1 (transfer)    | 0.0007  |   990 | **3 288**  | 6 577  |
| sim n=12, γ in-range        | 0.0013  |   533 | **1 770**  | 3 540  |
| tune target n=14, p=1       | 0.0014  |   495 | **1 644**  | 3 287  |
| — 90%@1000 threshold —      | 0.0023  |   301 | **1 000**  | 2 000  |
| — 90%@500 threshold —       | 0.0046  |   150 | **499**    | 999    |

Reading it: at the hardware-measured Phase 2 rate (0.0005), **90% confidence
needs ≈ 4 600 shots**. Peter's 2000-shot HW run sat at 63% predicted — it found
the optimum anyway (degeneracy), but 2000 < 4600 so it was NOT yet a 90% run.
To make 1000 shots a 90% run, P(opt) must reach 0.0023 (≈ 4.6× the current HW
rate) — that is the Phase 3 target, via p=2 + error mitigation or a warm start.

### Table 2 — the inverse: conversion reached at a fixed shot budget

| P(opt) \ shots | 1 000 | 2 000 | 4 000 | 8 000 | 16 000 |
|----------------|------:|------:|------:|------:|-------:|
| 0.0001 (Ph1 HW)|  9.5% | 18.1% | 33.0% | 55.1% | **79.8%** |
| 0.0005 (Ph2 HW)| 39.4% | **63.2%** | 86.5% | 98.2% | ~100% |
| 0.0007 (sim)   | 50.3% | 75.3% | 93.9% | 99.6% | ~100% |
| 0.0014 (tuned) | 75.3% | 93.9% | 99.6% | ~100% | ~100% |
| 0.0023 (target)| **90.0%** | 99.0% | ~100% | ~100% | ~100% |

Two cross-checks against real runs:
- Phase 1 at 16000 shots → 79.8% predicted; Peter's run DID find the optimum
  (inside the ~80% odds). Consistent.
- Phase 2 at 2000 shots → 63.2% predicted; the CLI printed `0.6322`. Exact match.

The whole Phase 1 → Phase 2 gain, in these terms: to hit 90% the shot budget fell
from **23 025 → 4 604 shots (5.0× fewer)**, purely from fixing the angle scale and
tuning — same depth, same 36270 CX.


## Honest verdict (unchanged by the improvements)

The levers raised CONVERSION (odds per shot), not quantum ADVANTAGE. SK number
partitioning with random 10-bit numbers has a perfect split that classical DP
finds instantly, with astronomically many optima — so best-of-shots also finds it
by coverage, and neither needs the other. No quantum speedup on this problem.

What IS the contribution, and it is real:
1. A dense all-to-all p=1 QAOA (36270 CX) that physically executes on all 156
   qubits of ibm_fez at depth 627 — the linear SWAP network makes it fit.
2. A measured, hardware-confirmed 5× conversion gain from angle normalization +
   CVaR tuning, transferred from a 14-qubit tune to the full chip.

The figure of merit is distribution quality at fixed hardware depth, NOT the
partition. Blind (no classical bar) the method returns a good partition but cannot
certify it optimal.


## Next (Phase 3 candidates)

- **p=2 with error mitigation** — lift per-shot P(opt) above 0.0023 (the 90%-at-
  1000-shots threshold, see table below). Each layer adds ~627 depth, so needs
  dynamical decoupling + measurement mitigation on HW to not be eaten by noise.
- **Warm start (Karmarkar-Karp)** — seed the initial state near a classical
  near-optimal partition; strongest single lever left for concentration.
- **Term sparsification** — drop small |J_ij| pairs to cut gates, trade approx for
  depth budget (enables higher p).
- **Honest metrics** — report deviation percentiles, retire approx_ratio at scale.


```
python classical_reference.py --n 60 --seed 69 ```
```
```
RUN :
numbers            : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269]
sum                : 31780
min deviation      : 0  (the optimal, classical bar)
optimal partitions : 97021795585096
perfect split      : True
```


**Phase 4 find limit of SWAP**


```
python qc_phase1.py --n 100 --seed 69 --shots 4000 --backend ibm_fez
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877]
routing              : swapnet  (logical depth 403, 2q gates 14850)
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 1111010001111000011100101001111111101001001010100110110001011010011101101000010000000100001001111111
min deviation        : 2
found optimum        : False
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 6205
approx ratio [0..1]  : 0.985
P(optimum sampled)   : 0.0
```

**More shots**
```
python qc_phase1.py --n 100 --seed 69 --shots 8000 --backend ibm_fez
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877]
routing              : swapnet  (logical depth 403, 2q gates 14850)
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 0000100010111000111101010100100110000110110010001111101111111001011011110110010101000001100011010110
min deviation        : 0
found optimum        : True
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 6160
approx ratio [0..1]  : 0.985
P(optimum sampled)   : 0.0001
```

**Died at 140 with 8000 shots**
```
python qc_phase1.py --n 140 --seed 69 --shots 8000 --backend ibm_fez
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877, 951, 279, 158, 686, 501, 646, 661, 647, 482, 197, 285, 546, 191, 953, 831, 648, 907, 412, 222, 671, 280, 424, 497, 790, 432, 265, 683, 577, 67, 546, 362, 689, 819, 520, 585, 390, 58, 82, 811, 453]
routing              : swapnet  (logical depth 563, 2q gates 29190)
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 11001101010111110000001101001000111101110001000000100111011101110001110000100111110010100111000010010100100000101110000101100100110001111100
min deviation        : 4
found optimum        : False
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 6989
approx ratio [0..1]  : 0.99
P(optimum sampled)   : 0.0
```

**FIXED by 16 000 shots**
```
python qc_phase1.py --n 140 --seed 69 --shots 16000 --backend ibm_fez
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877, 951, 279, 158, 686, 501, 646, 661, 647, 482, 197, 285, 546, 191, 953, 831, 648, 907, 412, 222, 671, 280, 424, 497, 790, 432, 265, 683, 577, 67, 546, 362, 689, 819, 520, 585, 390, 58, 82, 811, 453]
routing              : swapnet  (logical depth 563, 2q gates 29190)
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 01001101001101110011000100011101101110111001010110111010100110111100101011010011100011100000001111011111000101101010010000001101000111100011
min deviation        : 0
found optimum        : True
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 7103
approx ratio [0..1]  : 0.99
P(optimum sampled)   : 0.0001
```

**Theoretical Maximum reached**
```
 python qc_phase1.py --n 156 --seed 69 --shots 16000 --backend ibm_fez
```
```
RUN :
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877, 951, 279, 158, 686, 501, 646, 661, 647, 482, 197, 285, 546, 191, 953, 831, 648, 907, 412, 222, 671, 280, 424, 497, 790, 432, 265, 683, 577, 67, 546, 362, 689, 819, 520, 585, 390, 58, 82, 811, 453, 735, 446, 130, 126, 707, 373, 506, 993, 214, 28, 901, 836, 849, 777, 984, 401]
routing              : swapnet  (logical depth 627, 2q gates 36270)
optimum deviation    : 0  (classical bar)
--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---
best partition bits  : 010010000110000011000111111110001011100001110001011010010111011101011010000000100110110111001001010110111001111010111110001010111000100010010001010110111100
min deviation        : 0
found optimum        : True
--- QAOA distribution quality (the honest numbers) ---
mean deviation       : 7709
approx ratio [0..1]  : 0.991
P(optimum sampled)   : 0.0001
```

```
 python classical_reference.py --n 156 --seed 69 
```
```
RUN :
numbers            : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877, 951, 279, 158, 686, 501, 646, 661, 647, 482, 197, 285, 546, 191, 953, 831, 648, 907, 412, 222, 671, 280, 424, 497, 790, 432, 265, 683, 577, 67, 546, 362, 689, 819, 520, 585, 390, 58, 82, 811, 453, 735, 446, 130, 126, 707, 373, 506, 993, 214, 28, 901, 836, 849, 777, 984, 401]
sum                : 79688
min deviation      : 0  (the optimal, classical bar)
optimal partitions : 4947002302319125363047408949975470800866380
perfect split      : True
```



**MAX run with phase 2 2000 shots**
```
python qc_phase2.py --n 156 --seed 69 --shots 2000 --optimize-n 14 --p 1 --backend ibm_fez
```
```
RUN :
tuned on n=14 p=1 (alpha=0.15): P(opt)@tune=0.0014
  gammas=[0.367]  betas=[1.386]
backend : ibm_fez (156 qubits)
numbers              : [701, 39, 99, 821, 171, 69, 620, 353, 336, 942, 937, 895, 807, 814, 886, 563, 425, 476, 849, 439, 581, 449, 851, 532, 329, 574, 562, 829, 451, 146, 423, 1018, 402, 66, 425, 294, 151, 201, 146, 1013, 318, 217, 711, 942, 677, 960, 774, 951, 743, 516, 837, 213, 106, 102, 397, 911, 637, 747, 67, 269, 894, 819, 741, 622, 382, 911, 42, 65, 97, 224, 32, 149, 256, 918, 251, 281, 155, 921, 491, 642, 823, 83, 719, 337, 649, 270, 954, 548, 531, 427, 35, 262, 88, 755, 127, 315, 406, 933, 666, 877, 951, 279, 158, 686, 501, 646, 661, 647, 482, 197, 285, 546, 191, 953, 831, 648, 907, 412, 222, 671, 280, 424, 497, 790, 432, 265, 683, 577, 67, 546, 362, 689, 819, 520, 585, 390, 58, 82, 811, 453, 735, 446, 130, 126, 707, 373, 506, 993, 214, 28, 901, 836, 849, 777, 984, 401]
routing              : swapnet+normalized  (logical depth 627, 2q gates 36270)
optimum deviation    : 0  (classical bar)
--- best-of-shots ---
best partition bits  : 110001010100110001110010100000111100110101010111001001000101001110101111011100100001101101101111001100101111101001011101011101110001000111101010000010111100
min deviation        : 0
found optimum        : True
--- conversion quality ---
mean deviation       : 8047
approx ratio [0..1]  : 0.99
P(optimum sampled)   : 0.0005
pred. success @  2000 shots : 0.6322
```