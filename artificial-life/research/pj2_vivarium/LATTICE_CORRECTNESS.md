# PJ2.2 — 2D-lattice vivarium: static correctness argument

**Ticket:** PJ2.2 (stage P3 of `epic-qalife-darwinian-richness`) · **Substrate:** `code/pj_qalife.py`
(`build_lattice_vivarium`) + driver `code/pj_lattice_vivarium.py` + renderer
`analysis/pj_lattice_render.py`. **Verification:** static (`--selftest` / `--dump-circuit`) + `--sim`
depth-scans + this note (CD-7; no test framework).

The organism is a **unary occupancy field** on a `grid×grid` square lattice (one qubit per cell,
`i = r*grid + c`) plus a **W-qubit germ line** (the GHZ genealogy carrying `⟨X^⊗W⟩`). Per organism:
`[germ(W) | body(grid²)]`, contiguous. Qubit budgets (`lat_segment_len`): 3×3 solo = **12**, 3×3
replicate/duo = **24**, 4×4 solo = **19** (all ≤ sim cap 27 and comfortable on Heron). 4×4
replicate/duo = 38/35 — **out of scope** (past laptop statevector; the driver fail-closes).

## The five structural claims (all checked by `--selftest`, all `OK`)

1. **The walk is a real local Hamiltonian, not scripted (mass conserved).** Movement is
   `_lattice_walk_layer`: excitation-conserving `rxx(θ)+ryy(θ)` on every von-Neumann neighbour pair,
   in edge-colored order (H-even / H-odd / V-even / V-odd → each color a depth-1 layer of
   non-overlapping 2-qubit gates). Applied **unconditionally** — no `if`/`c_if` on position; the germ
   is untouched. Static check: every body-touching multi-qubit gate is `rxx`/`ryy` (the seed `x` is
   the only 1-qubit body gate) ⇒ `mass_conserved = True`. Sim confirms mass = 1.0 per organism at
   every generation while the dominant cell walks (e.g. 3×3 solo dom-cell `5→1→3`).

2. **Isolated germ line vs coupled wound (the A/B kill-switch).** `arm='isolated'` never couples a
   body cell to a germ qubit; `arm='coupled'` adds one coherent `rxx+ryy` from the centre body cell to
   `lat_witness_q(0,0)` — the soma→germ back-action. Static `lattice_coupling_report`:
   `back_action = False` (isolated) / `True` (coupled); `witness_isolated = True` (isolated) /
   `False` (coupled). Sim: the germ witness pins at the ceiling in `isolated` and **collapses to ≈0**
   in `coupled`, for all three modes.

3. **Replicate clones germ→germ only (Weismann-faithful).** At generation `LAT_REP_GEN = 2`,
   `_lattice_clone` applies `cx(germ(0,k) → germ(1,k))` for each `k` (parent → daughter, one shared
   GHZ) and seeds a daughter body one cell over. The clone pairs **witness with witness**, so
   `witness_isolated` stays `True` and `back_action` stays `False` in the isolated arm — no accidental
   soma→germ gate. Sim: `n` fields = 1 for gens 0–1, then **2** from gen 2 (daughter mass 0 → 1.0).
   *The witness set is parent-only before the clone* (`active_witness_qubits`): H-ing the still-`|0⟩`
   daughter germ would inject random X-parity and null the joint — the honest reading is that the
   shared `⟨X^⊗2W⟩` only exists once the daughter does.

4. **Duo builds a joint witness from co-located interaction (no `if(contact)`).** Two independent
   founders at opposite corners (cells `0` and `grid²−1`); after each walk layer `_lattice_interaction`
   applies `rxx+ryy` between co-located A/B body cells. It only acts where both bodies have amplitude,
   so contact **emerges** from co-location. Reported `overlap = Σ min(occ_A, occ_B)` (diagonal). Sim:
   overlap rises from 0 as the fields drift together (≈0.7 by gen 1).

5. **Certified frames via a depth scan (no classical branch, germ-first, X-readout on germ only).**
   Each generation `d` is its **own** circuit with `d` walk layers, measured once (occupancy in Z,
   germ in X). `has_classical_branch = False` (fully unitary — no measure/reset/condition mid-circuit);
   `germ_first = True` (the germ line precedes the body); the X-basis rotation is `H` on the germ loci
   **only** (`H(witness)=W·n_org, H(other)=0`). The integer generations are the certified frames; the
   smooth in-between playback the renderer interpolates is a **labelled sim artifact** (mockup README
   §5). On hardware the driver banks exactly one measured circuit per `(mode, arm, gen, repeat)` with
   selective DD on the germ physical qubits only (`schedule_lattice_selective_dd`).

## `--selftest` output (`python code/pj_qalife.py --lattice --selftest`)

Seven checks × four `(grid, mode)` cases — `(3,solo)`, `(3,replicate)`, `(3,duo)`, `(4,solo)` — all `OK`:

```
  [OK ] A/B kill-switch (isolated no back-action; coupled breaks it)
  [OK ] witness loci isolated (isolated arm) but not coupled
  [OK ] mass conserved (walk = rxx+ryy neighbour pairs)
  [OK ] ordering: germ line built before the body (rung 0)
  [OK ] witness readout: H on germ loci only
  [OK ] no classical branch (fully unitary walk)
  [OK ] qubit count == lat_segment_len(width, grid, mode)

SELFTEST PASS
```

Byte-stability: `git diff` on `qalife.py`, `run_qalife.py`, `pj_run_qalife.py`, `pj1_run_arena.py`,
`pj_vivarium.py` is empty; PJ0 / PJ1 / PJ2 `--selftest` remain green. Circuit dumps per
mode/arm/depth are in `circuits/lattice_*.txt`.

## Honesty invariant (CD-3/CD-4)

Only `⟨X^⊗W⟩` over the germ line is the quantum claim. The occupancy field (`⟨n⟩` per cell), mass,
and duo overlap are **diagonal** — an exact classical surrogate — reported as the honest "where it is"
narrative. The separable null is reported alongside and sits ≈0 in sim. Noiseless sim pins the
isolated witness at the ceiling (`+1.0`) for every mode/arm — the *shape* of the decay with depth and
the ~5–6-generation ceiling are **hardware** effects the live depth-scan measures (R6).
