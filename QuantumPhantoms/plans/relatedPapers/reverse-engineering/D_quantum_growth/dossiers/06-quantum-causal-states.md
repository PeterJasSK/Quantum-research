# #06 — Quantum causal-state (memory-efficient) process models (Gu; Elliott; Wu; Palsson; Ghafari)

**Letter:** D ([`D_quantum_growth`](../README.md)) · **Priority:** ★★★ · **Kind:** quantum · **Papers:** D06, D17, D16, D07, D08 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

<!-- The method in plain words: what problem it solves, the core idea. -->
A stochastic process has a **causal-state** model: the minimal classical memory that predicts its future (statistical complexity C_μ, topological D_μ = log₂ #states). Gu et al. [D06] showed a quantum model whose memory states are non-orthogonal can store less, C_q = S(ρ) < C_μ. Wu et al. [D16] proved that for the **periodically modulated decay (PMD)** renewal family a *single qubit* (D_q ≤ 1) models the process exactly for every period N, while D_μ = log₂ N grows. D17 gives the general theory. D-5 uses this on a cell-cycle division timer: run the 1-qubit-memory model as a dynamic circuit and measure the advantage.

## Equations

<!-- The equations we re-implement, with symbols defined. -->
```text
Renewal process, survival Φ(n):      P(two ticks ≥ n steps apart) = Φ(n)
PMD (Wu Eq. 1):                      Φ(n) = Γⁿ (1 − V sin²(nθ)),   θ = π/N
Causal states:                       j = zeros since last tick (mod N); hazard h_j = 1 − Φ(j+1)/Φ(j)
C_μ = H(π),  D_μ = log₂ #states      π = stationary distribution
Quantum model (D16 SM S1):           A₀ = (1/η)[[1, α(e^{iφ}−1)],[0, e^{iφ}]],  A₁ = ζ|σ₀⟩⟨w|,  φ = 2π/N
                                     |σ_n⟩ ∝ A₀ⁿ|σ₀⟩ = β₀|Z₀⟩ + β₁ e^{inφ}|Z₁⟩
                                     Γ = 1/η², V = 4αβ₀β₁, (β₀+αβ₁)² + β₁² = 1, η² = 1 + g/2 + ½√(g²+4g), g = 4α² sin²(φ/2)
C_q = S(ρ),  ρ = Σ π_n |σ_n⟩⟨σ_n|,  D_q = log₂ rank{|σ_n⟩}
Gu perturbed coin:                   |S₀⟩ = √(1−p)|0⟩+√p|1⟩, |S₁⟩ = √p|0⟩+√(1−p)|1⟩, C_q = H₂((1+2√(p(1−p)))/2), C_μ = 1
Circuit:                             U|s⟩|0⟩ = A₀|s⟩|0⟩ + A₁|s⟩|1⟩ (isometry completed to 4×4 unitary); per step U → measure output → reset
d_KL = (1/L) D(P_sim ‖ P_exact) in bits/symbol
```

## Parameters

<!-- Every parameter with its published value/range and source (paper code, section, table). -->
- Cell-cycle division timer: **N = 8, Γ = 0.5, V = 0.4**, L = 10 steps, initial memory |σ₀⟩ (just after a tick). Source: Wu Fig. 5a uses Γ = 0.5, V = 0.4, N = 3…8 (experiment Γ 0.49–0.64, N 3–8, V = 0.4, L = 2). Described as "a division-timer process of PMD form", **not fitted tumor biology** (plan Q3).
- 40 000 shots per tomography variant (Z / X / Y memory readout), one Aer job per mode; word statistics from the Z variant only (see honesty note).
- 1-bit classical baseline: 2-state edge-emitting HMM, 24 L-BFGS-B multi-starts seeded from the certificate seed.

## Paper's claimed result

<!-- The single published number or figure we will reproduce, with exact reference. -->
[D06] prints: C_q < 0.5 for p > 0.2 and C_q < 0.1 for p > 0.4 (perturbed coin). [D16]: for any PMD process a statistically exact quantum model with D_q ≤ 1 exists while D_μ = log₂ N; experiments with distortion below 10⁻² bits/symbol, below the best 1-bit classical model, at L = 2. D16 prints no table of C_q values.

## Our reproduction (number + figure)

<!-- Our number vs the paper's, agreement, figure in ../figures/, run id. Quantum: label the sim mode. -->
Analytic (figures `gu_perturbed_coin.png`, `wu_pmd_memory.png`; `python -m D_quantum_growth.repro.causal_states_repro`, label "analytic: exact theory"):

| quantity | paper | ours |
|---|---|---|
| Gu C_q(p=0.2) < 0.5 | printed | 0.4690 |
| Gu C_q(p=0.4) < 0.1 | printed | 0.0815 |
| Wu D_μ = log₂ N, N = 2…16 | printed | exact (n_causal = N for all N) |
| Wu D_q ≤ 1 qubit, any N | printed | D_q = 1 for all N = 2…16; survival error ≤ 2.2·10⁻¹⁶ |

Simulated q-machine (`python -m D_quantum_growth.src.memory_advantage --mode ideal|heron`; runs `20261029-112717-grow-ideal`, `20261029-112719-grow-heron`; figure `cellcycle_memory_advantage.png`). C_μ = 1.799 bits, C_q (theory) = 0.0640:

| mode | d_KL quantum (bits/sym) | d_KL best 1-bit classical (same sample count) | C_q measured | memory fidelity | passed |
|---|---|---|---|---|---|
| simulated: ideal | 0.00192 | 0.00315 (exact 0.00136) | 0.0627 ± 0.0054 | 0.99998 | yes |
| simulated: Heron-class noise (FakeMarrakesh) | 0.00189 | 0.00315 | 0.1743 ± 0.0048 | 0.9943 | yes |

The KL sampling floor at 40 000 samples is ≈ 0.00184 bits/symbol, so the quantum d_KL is **at the floor in both modes**; Heron noise shows up in the memory state (C_q 0.064 → 0.174), not in the output statistics.

## Adaptation

<!-- How it is adapted to lungs, 3-D, certification and our contracts. -->
The PMD process is used as a cell-cycle division timer (N = 8 steps per cycle). The 1-qubit model becomes a 2-qubit unitary (memory + output), compiled to the FakeMarrakesh CZ basis, 10 steps in one dynamic circuit (mid-circuit measure of the output, reset), three tomography variants in one job. Output: `memory_advantage_record` (claim L1′), `n_qubits = 1`. `passed` = C_q(measured) < C_μ **and** d_KL < 10⁻² **and** d_KL < best 1-bit classical.

**Honesty notes.**
- With Γ = 0.5, V = 0.4 the modulation is weak: the best exact 1-bit classical model already reaches d_KL = 0.00136, *below* the sampling floor. The comparison "quantum < classical" is therefore made at the same sample count (0.00192 vs 0.00315) and is resolved only because the classical model's distortion is real while the quantum model's excess is sampling noise. A stronger-correlation process would show a larger gap. [D-5] caution: the advantage needs strong correlations; low-correlation processes are compressed classically too.
- C_q(measured) < C_μ is essentially guaranteed for a qubit (≤ 1 bit < 1.80); the informative number is C_q(measured) vs theory (0.0627 ideal, 0.174 Heron).
- The three tomography circuits share one simulator seed, so their word samples are copies of each other; word statistics use the Z variant only.
- `memory_advantage_record` has no d_KL field: the values are in `process_description` and the sidecar `memory_advantage_detail.json` (CCR-D2).

## Verdict

<!-- integrated | rejected (with reason). Claim level for quantum targets. -->
**adapted**, claim level **L1′** (simulated, both modes). Published statements matched (Gu inequalities, Wu D_μ/D_q). Quantum model exact with one qubit; measured advantage over a 1-bit classical model is small for this weakly modulated process and is stated as such. Never L2.

## What to reuse next

<!-- Pointers for downstream letters / INT. -->
`causal_states.py` (renewal machine, Gram fixed point, Wu Kraus model, isometry → unitary, best classical HMM) is reusable for any survival function, e.g. a process built from E's calibrated hazard (plan Q3 alternative: may land in a low-correlation regime). INT: wire E's division hazard into `pmd_survival` and rerun.
