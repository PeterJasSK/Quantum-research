# #12 — High-performance CA (Poleszczuk–Enderling)

**Letter:** E ([`E_classical_growth`](../README.md)) · **Priority:** ★ · **Kind:** classical · **Papers:** E03 · **State:** see [`status.json`](../status.json)

> Dossier for one reverse-engineering target. Update it in the same change as the target's state in `status.json`.
> Equations: Unicode inline or fenced `text` blocks (no MathJax; the site is offline).

## Concept

Poleszczuk & Enderling (Appl. Math. 2014, arXiv:1309.6015) [E03] is an implementation paper about how to make agent-based tumor cellular automata fast enough for millions of cells. The model is a 2-D/3-D lattice with cancer stem cells (immortal, unlimited divisions) and non-stem cells (limited proliferation potential ρ, death rate α, migration µ). Cells need a vacant neighbour to divide or migrate, and they are updated in random order once per day. The contribution is the data structures:
- the lattice stored as a **flattened 1-D array**, so the neighbours of index i are i ± fixed strides (cache-friendly);
- a separate **list of the cells** (agents), iterated in random order, instead of scanning the whole lattice;
- a **dynamically growing domain**: the lattice is reallocated only when the tumor approaches the border;
- a lookup of vacant neighbours, with the right structure chosen by tumor density (dense vs diffusive).

## Equations

There is no new growth law. The update per step (one day) for each cell, in random order:

```text
if no vacant Moore neighbour: quiescent (no action)
else, with probability p_div · Δt:  divide into a random vacant neighbour
        stem cell:  symmetric with probability p_s, otherwise asymmetric (one stem + one non-stem, ρ = ρmax)
        non-stem:   ρ ← ρ − 1;  ρ = 0 → cell dies
     else with probability µ · Δt: migrate to a random vacant neighbour
non-stem cells die spontaneously with rate α
```

## Parameters

| Parameter | Meaning | Note |
|---|---|---|
| cct | cell-cycle time (≈ 1 day) | sets p_div per step |
| ρmax | proliferation capacity of non-stem cells | E03 §2 |
| p_s | symmetric stem-division probability | E03 §2 |
| α, µ | spontaneous death, migration | E03 §2 |
| p = 0.99 / 0.5 | "dense" vs "diffusive" occupancy cases used for the data-structure comparison | E03 §3 |

## Paper's claimed result

Simulation speed and memory for populations of millions of cells on a desktop PC, for the different data structures (E03 §3–4). The result is an engineering benchmark, not a biological number.

## Our reproduction (number + figure)

Not reproduced (★, read only; plan Q9). At nodule scale the lung lattice holds ≤ 10⁶ voxels (a 30 mm nodule at 0.5 mm is ≈ 2 × 10⁵ cells), and one `grow` run takes seconds (stub S001: about 520 simulated days in ~3 s). There is no performance problem to benchmark against.

## Adaptation

These ideas are used in `src/engine.py`, without a reproduction:
- **Flattened, padded 1-D lattice.** Neighbour offsets are fixed integer strides. The padding is a hard barrier, so no bounds checks are needed.
- **Active-cell list.** Only proliferating voxels (`np.flatnonzero(state == 1)`) are iterated, in a seeded random order, not the whole box.
- **Bounding-box work.** Distance transform, edge detection and contact counts run on the tumor's bounding box (+2 voxels), not on the full lattice.

The growing domain is not used: E sizes the box up front from the drawn size and the expected follow-up growth, and logs `touched_box_edge` if the tumor reaches it (false in all runs so far).

## Verdict

**dissected.** The ideas are documented and partly used. A reproduction is not needed at nodule scale, so the state is left non-terminal: cohort-scale work (thousands of tumors, or whole-lobe lattices) may advance it later.

## What to reuse next

- If **H** cohorts or a whole-lung lattice make `grow` slow, port the inner division loop of `engine.py` to a compiled kernel. Numba is not installed, so this needs a dependency decision. Add E03's growing domain at the same time.
- The density-dependent choice of vacant-neighbour structure (E03 §3) matters for diffusive (ground-glass-like) growth, if F/H ever need a sparse, lepidic cell pattern.
