# #02 — Quantum-enhanced MCMC (Layden; Ferguson–Wallden)

**Letter:** B ([`B_mapping`](../README.md)) · **Priority:** ★★ · **Kind:** quantum · **Papers:** B11, B12 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Metropolis–Hastings needs a proposal distribution Q(s′|s). Layden et al. [B11] propose with a quantum evolution: prepare the basis state |s⟩, evolve under a Hamiltonian that mixes the problem energy with a transverse field, measure, and use the outcome s′ as the proposal. Because the evolution is unitary and real-symmetric, Q is symmetric, so ordinary Metropolis acceptance still leaves the Boltzmann distribution exactly stationary: the sampler is correct for any (γ, t); only the mixing speed changes. Ferguson–Wallden [B12] coarse-grain the proposal; noted here, not built.

## Equations

```text
Energy        E(s) = −Σ_{i<j} J_ij s_i s_j − Σ_i h_i s_i ,  s_i = ±1
Hamiltonian   H = (1 − γ)·α·H_prob + γ·H_mix ,  H_prob = diag E ,  H_mix = Σ_i X_i
              α = √n / √(Σ J² + Σ h²) ,  γ ~ U[0.25, 0.6] ,  t ~ U[2, 20]
Proposal      Q(s′|s) = mean over M draws (γ, t) of |⟨s′| e^(−iHt) |s⟩|²   (symmetric)
Acceptance    P(s→s′) = Q(s′|s)·min(1, π(s′)/π(s)) ,  π ∝ e^(−E/T)
Gap           δ = 1 − |λ₂(P)| ;   ⟨δ⟩ ∝ 2^(−k n)
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| γ range, t range | U[0.25, 0.6], U[2, 20] | [B11] |
| Instances | SK (J, h ~ N(0,1)), n = 3…8, 100 per n, M = 64 draws, T = 1 | ours (paper uses more/larger) |
| Baselines | local single-spin flip; uniform proposal | [B11] |
| Trotter (Heron arm) | 2nd order, 2 steps per unit t, grid (γ,t) ∈ {0.3,0.5}×{2,6} | plan Q8 |

## Paper's claimed result

Spectral-gap scaling exponents (⟨δ⟩ ∝ 2^(−kn)): k_quantum = 0.264(4), k_local = 0.94(4), k_uniform = 0.948(7) [B11].

## Our reproduction (number + figure)

`python -m B_mapping.repro.layden`, **simulated: ideal** (exact `eigh`, no sampling error):

| | ours | paper | tolerance | |
|---|---|---|---|---|
| k_quantum | 0.250 | 0.264 | ±0.08 | match |
| k_local | 1.017 | 0.94 | ±0.15 | match |
| k_uniform | 0.939 | 0.948 | ±0.15 | match |

Figure: [`figures/layden_gap_scaling.png`](../figures/layden_gap_scaling.png). The quantum proposal's gap decays about four times more slowly per spin than local or uniform proposals — **in ideal exact simulation, n ≤ 8**.

## Adaptation

Tumor-in-anatomy energy (`tumor_energy.py`): spins are voxels of a coarse patch at the site (s = +1 tumor); h_i from the anatomy masks — vessel proximity attracts (+), pleura proximity repels (−), plus a size term; J > 0 nearest-neighbour compactness. Every coefficient is a named parameter in `tumor_energy.PARAMS`, recorded in each run's `qemcmc_result.json`. Command: `python -m B_mapping.src.qemcmc --tumor --mode ideal|heron [--patch z,y,x]`.

Spectral gap δ at site S001, 8 mm tumor, stub masks (`qemcmc_result.json` in the runs):

| Patch | Arm | δ quantum | δ local | δ uniform |
|---|---|---|---|---|
| 2×2×2 (8 spins) | **simulated: ideal**, M = 64 draws | 0.0180 | 0.0121 | 0.0084 |
| 2×3×1 (6 spins) | **simulated: ideal**, M = 64 draws | 0.0392 | 0.0379 | 0.0469 |
| 2×3×1 (6 spins) | **simulated: ideal**, 4-point grid | 0.0397 | — | — |
| 2×3×1 (6 spins) | **simulated: Heron-class noise (FakeMarrakesh)**, noisy Q | 0.0536 | — | — |

Heron arm: 256 Trotter circuits (64 input states × 4 grid points, 1024 shots, mean depth 885, mean 359 CZ). The noisy proposal matrix is **not symmetric** (mean |Q − Qᵀ| / mean Q = 0.135) and differs from the ideal grid Q by TVD 0.21, so Metropolis no longer leaves the target exactly stationary; the larger noisy gap (0.054 > 0.040) is noise flattening the proposal toward uniform, not a quantum benefit. The 8-spin Heron run was abandoned after > 1 h and replaced by the planned 6-spin patch.

Caveat: with the stub masks, h is nearly constant over the patch (≈ −0.10, pleura term dominates), so the landscape is almost flat and the three proposals are hard to separate at n = 6. At n = 8 the quantum gap is 1.5× the local one.

## Verdict

**Adapted**, no claim level. Claim: a correct sampler with quantum proposals; any speedup is ideal-simulation only and vanishes under Heron-class noise at these depths. Classical baselines (local, uniform) are reported next to every quantum number.

## What to reuse next

- `qemcmc.quantum_Q`, `mh_matrix`, `spectral_gap` for any small Ising target; A's real masks give a non-flat landscape.
- The noisy-Q asymmetry number is the honest figure of merit for hardware-style proposals.
- Coarse-grained QeMCMC [B12]: unbuilt.
