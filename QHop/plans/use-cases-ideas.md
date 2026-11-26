# QHop — real-life use cases (fewer steps, showable, n ≤ 12)

Status: **in progress (2026-11-19)**. Six domain agents are running exact configurations; results get filled in
below as they come back. All numbers are `simulated: ideal` (exact state vector, no noise) unless marked otherwise.

## Criterion
- Must work **today**: n ≤ 12 binary variables (or a 10–12-variable lens of a bigger model, Ferguson–Wallden
  coarse-graining), sparse enough couplings for a Trotter circuit on Heron heavy-hex.
- Must take **fewer chain steps** than the classical proposals (local single flip, uniform jump). It does **not**
  have to beat the best classical method in wall-clock (exact enumeration wins at n ≤ 12, and classical makes ~10⁴×
  more proposals per second).
- Must be **showable**: a picture or demo that someone outside physics understands. Better than a toy tile-map game.
- Mechanism check: the quantum gap must also beat the **decohered** control (same generator, interference removed),
  otherwise the gain is not quantum.

## Method (shared harness)
Script: `/tmp/claude-1000/-home-peter-PycharmProjects-Quantum-research/e9ded90a-1a04-4064-85b7-837fe9d96c4f/scratchpad/qhop_harness.py`
(session scratchpad; copy into `QHop/` before it is lost if it should be kept). Built on RE B
`QuantumPhantoms/plans/relatedPapers/reverse-engineering/B_mapping/src/qemcmc.py`.

- Proposal Q(s′|s) = mean over (γ, t) of |⟨s′|e^(−iHt)|s⟩|², H = (1−γ)·α·diag(E) + γ·ΣX, α = √n / std(E),
  γ ~ U[0.25, 0.6], t ~ U[2, 20], m = 16 draws. Works for any binary energy vector, not only Ising.
- Decohered control: same H, Z-dephasing after every dt = 0.25 slice (T = |e^(−iH dt)|², composed t/dt times).
- Metrics per proposal: spectral gap of the Metropolis matrix; acceptance; mean bits flipped; exact expected steps
  to leave the starting valley (basins by steepest descent); TVD to Boltzmann after 10 / 100 / 1000 steps.
- Runtime: n = 8 ≈ 3 s, n = 10 ≈ 20–40 s, n = 12 = minutes.

### Calibration: SK spin glass (seed = n, T = 1)
| n | valleys | gap q / local | gap q / best classical | gap q / decohered | steps to leave valley q / local / uniform |
|---|---|---|---|---|---|
| 8 | 4 | 29.3 | 6.1 | 4.6 | 5.3 / 66.5 / 182.3 |
| 10 | 7 | 40.1 | 11.3 | 11.3 | 26.3 / 154.3 / 382.3 |

Matches the Layden trend (quantum gap decays far slower than local / uniform). One instance per n: calibration,
not a result.

## Domains under test
| # | Domain | Configurations being tried | Result |
|---|---|---|---|
| 1 | Meteorology | multi-site rain occurrence (autologistic / Ising weather generator, real station data, summer vs winter); compound extreme events (drought, flood coincidence) at low T or conditioned; 3×4 convective-cell / frost lens | pending |
| 2 | Maps (beyond game) | urban land-use zoning lens; redistricting ensembles (GerryChain-style, used in US courts); WFC-rule terrain / level layouts; antenna coverage | pending |
| 3 | Medicine — genomics | TCGA driver-mutation co-occurrence / mutual exclusivity Ising (virtual-patient genotypes); binarised protein Potts / HP lattice protein; resistance-gene or drug-synergy Ising | pending |
| 4 | Medicine — brain / clinical | fMRI energy-landscape analysis (Watanabe / Ezaki: basins = brain states); neuron-population max-ent Ising (Schneidman); symptom / comorbidity networks (IsingFit); MRF segmentation lens as easy contrast | pending |
| 5 | Materials / chemistry | alloy and Li/vacancy ordering (cluster expansion ECIs); triangular / kagome / spin-ice patches; adsorbates on catalyst surfaces; proton / H-bond ice rules | pending |
| 6 | Infrastructure / finance / ecology / social | grid cascading outages (IEEE 14-bus); credit default contagion; species co-occurrence; roll-call voting blocs; wildfire lens | pending |

Per configuration each agent reports: n, nonzero couplings (CZ estimate), heavy-hex fit, gap ratio vs local / best
classical / decohered, steps-to-leave-valley ratio, T sweep, ≥ 5 instances (median + spread), what "fewer steps"
means for a domain user, and a demo idea. Agent results files: `scratchpad/agents/<domain>/results.md`.

## Ranked use cases
(filled when the agents finish)

## Honesty notes
- Per step only. Exact enumeration (2^12 = 4,096 states) and strong classical samplers (parallel tempering,
  cluster moves) still win in time at these sizes.
- Tuning (γ, t) or T per instance favours quantum; every tuned value is reported.
- Ideal simulation only. RE B found the noisy (FakeMarrakesh) proposal at n = 6 asymmetric (|Q − Qᵀ| / Q = 0.135)
  and its larger gap came from noise flattening the proposal toward uniform, not from quantum; hardware value is
  open (qh-15 ε\* study).
