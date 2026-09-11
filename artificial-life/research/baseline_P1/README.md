# P1 — Reconstruction baseline (the fixed clean-witness reference)

**Stage:** P1 (epic `plans/epic-qalife-darwinian-richness.md`) · **Banked:** 2026-09-09 ·
**Status:** immutable P1 reference (AC-P1.3).

This directory is the **canonical clean-witness baseline** every P3+ richness run is judged
against. It banks the genealogical entanglement witness `<X^{otimes W}>` of the exact
Alvarez-Rodriguez 2018 four-operator model — the *only* quantum claim in this project (CD-3) —
as three series: the noiseless **ideal**, the live **hardware** confirm, and the **separable
null** (`prod_i <X_i>`) that a classical measure-and-resend device gives.

## What is here

| File | What it is |
|------|-----------|
| `baseline_P1.json` | the banked dataset (schema below) |
| `baseline_P1_witness_vs_W.png` | witness vs genealogy width W — ideal saturating, hardware decaying, separable band on ~0 |
| `baseline_P1_witness_vs_gen.png` | exact ideal witness vs generation depth at W=12 |
| `README.md` | this file |

## Headline numbers

**Ideal (exact statevector, mut_scale=0.08 modeled mutation)** — saturates high, never decays:

| W | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 |
|---|---|---|---|---|---|---|----|----|
| ideal `<X^{otimes W}>` | 0.993 | 0.974 | 0.959 | 0.943 | 0.937 | 0.910 | 0.904 | 0.879 |

separable null across all ideal widths: `~1e-20` down to `~1e-190` (machine-zero).

**Hardware (`ibm_kingston`, Heron-r2, nn / unitary death, steps 3, k=2)** — the real ceiling:

| W | 3 | 4 | 6 | 12 | 24 | 32 |
|---|---|---|---|----|----|----|
| witness | +0.879 | +0.808 | +0.612 | **+0.301** | **+0.038** | +0.008 |
| ±1σ | 0.027 | 0.021 | 0.014 | 0.017 | 0.016 | 0.013 |
| survives k=2 | ✓ | ✓ | ✓ | ✓ | **✓** | ✗ |
| survives k=3 | ✓ | ✓ | ✓ | ✓ | **✗** | ✗ |

**Entanglement depth = W=24 = 48 qubits** (marginal-ALIVE at k=2, dies at k=3), ~6× the paper's
~4-qubit origin. W=32 is buried in noise (dead). Separable null across all hardware widths
`<= 1.9e-06` — the CD-3 gate (`separable_null_max` < 0.05) passes with ~5 orders of margin.

## Honesty framing (CD-4)

- The **ideal** curve saturates near ~0.9–0.99 because it is **noiseless** — the small droop is
  the *modeled* mutation (Ry(θ), θ ~ mut_scale·U(0,π)), **not** decoherence. The exact statevector
  cannot find the ceiling; **the ceiling is the hardware number** (W=24).
- The witness is the **sole** quantum claim. Every diagonal metric (alive-count, deepest-lineage,
  phenotype `<σ_z>`) has an exact classical surrogate and carries **no** quantum claim.
- The ideal uses the same `_sim_thetas(W, seed=100, mut_scale=0.08)` angles as the modeled biology
  (R4), so it is the honest baseline the richness runs share — **not** a mutation-free clean GHZ
  (which would read exactly 1.0). P3 must use this same thetas convention to compare like-for-like.

## Hardware provenance (CD-6)

Reused (not freshly run — OQ-1 default, "NO QC RUN") banked Month-4 `ibm_kingston` unitary/nn runs:

- `qalife_m4p2_nn_unitary_ibm_kingston_20260825-090118.json` (W=3,4)
- `qalife_m4p2_nn_unitary_ibm_kingston_20260825-090633.json` (W=6,12,32)
- `qalife_m4p2_nn_unitary_ibm_kingston_20260825-090905.json` (W=24)

QRNG entropy provenance is tracked here **by source-run filename** — the driver `meta` does not yet
persist `entropy_provenance` (epic §4 field deferred to P2, when fresh live runs are produced).

## Regenerate

From `artificial-life/`:

```
python analysis/plot_baseline.py
```

Bare invocation reproduces this exact baseline (ideal widths `2,3,4,5,6,8,10,12`, W_gen=12,
steps=3, mut_scale=0.08, seed=100, k=2, the `ibm_kingston` nn/unitary glob). The script fails
closed (exit non-zero, nothing archived) if the separable null is not ~0 (CD-3).

## JSON schema (`baseline_P1.json`)

```
meta: {stage, model, interaction, death, steps, mut_scale, seed, k,
       ideal_method, sim_widths, hw_source_runs, hw_backend}
witness_vs_W:
  W:               [exact-ideal widths]
  ideal:           [exact final-depth <X^{otimes W}>]
  ideal_separable: [exact product null, ~0]
  hardware: {W, witness, sigma, separable, survives_k2, survives_k3}
witness_vs_gen: {W_fixed, gen:[0..W-1], ideal:[per-depth exact witness]}
separable_null_max: <max |separable| across ideal+hardware, gated < 0.05>
```

Note: `witness_vs_gen.gen` is the genealogy depth index g (the line grown to width g+1), the
native axis of `qalife.witness_ideal_by_gen`; g=0 is the founder line and reads ~0.999.
