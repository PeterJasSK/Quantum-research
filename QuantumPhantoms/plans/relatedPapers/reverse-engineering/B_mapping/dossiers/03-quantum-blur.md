# #03 — Quantum blur (Wootton)

**Letter:** B ([`B_mapping`](../README.md)) · **Priority:** ★ · **Kind:** quantum · **Papers:** B04, B05 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Wootton's quantum blur [B04, B05] loads an image or height map as the amplitudes of an n-qubit state (pixel coordinates are the bitstring of the basis state), applies a small rotation to every qubit, and reads the output probabilities as the blurred map. Rx(θ) on each qubit moves amplitude between basis states that differ in one bit, so mass spreads along the Hamming graph of the coordinate bits. It is a simulation trick; the output is a probability vector, which a real device could only estimate by many shots.

## Equations

```text
|ψ⟩ = Σ_x √(h(x) / Σh) |x⟩ ,  x = bitstring of the coordinates
U = ⊗_i Rx(θ) ,  Rx(θ) = [[cos θ/2, −i sin θ/2], [−i sin θ/2, cos θ/2]]
blurred(x) = |⟨x|U|ψ⟩|² · Σh
```

## Parameters

| Parameter | Value | Source |
|---|---|---|
| θ | 0.1π, 0.25π, 0.5π | ours (paper sweeps θ) |
| Coordinate mapping | plain binary, axes concatenated | ours — [B04, B05] PDFs not re-read for the exact mapping **(verify)** |
| Baseline | `scipy.ndimage.gaussian_filter`, σ chosen to maximise correlation | plan |

## Paper's claimed result

Qualitative only: smoothed images/height maps for increasing rotation angle. No published number.

## Our reproduction (number + figure)

`python -m B_mapping.repro.wootton_blur`, **simulated: ideal** (statevector). Correlation of the quantum blur with its best-matching Gaussian:

| θ | 2-D 16×16 height map | 3-D 8×8×8 sphere (9 qubits) |
|---|---|---|
| 0.10π | r = 0.967 (σ = 0.38) | r = 0.993 (σ = 0.88) |
| 0.25π | r = 0.12 | r = −0.16 |
| 0.50π | r = −0.44 | r = −0.26 |

Figure: [`figures/quantum_blur_vs_gaussian.png`](../figures/quantum_blur_vs_gaussian.png).

## Adaptation

3-D: one 8×8×8 sphere shape seed blurred at three θ, with the Gaussian at matched σ. For small θ the quantum blur *is* a Gaussian-like smoothing (r ≥ 0.97). For larger θ it moves mass between coordinates that differ in high bits, i.e. far apart in space, and is no longer a spatial blur at all.

## Verdict

**Rejected** as a shape-variation option: where it behaves like a blur, a classical Gaussian reproduces it (r up to 0.99); where it differs, it produces non-local, non-physical scrambles of the coordinate bits. No quantum advantage, no claim level. Use `gaussian_filter` for seed-shape variation.

## What to reuse next

Nothing for the pipeline. `blur.py` stays as the dissection and baseline comparison.
