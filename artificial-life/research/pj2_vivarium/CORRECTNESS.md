# PJ2 solo-vivarium — static correctness evaluation

Ticket: `plans/feature-PJ2-solo-vivarium.md` (stage P3, epic `qalife-darwinian-richness`).
Verification per CD-7: static `--selftest` + `--dump-circuit` + `--sim` (no test framework). The live
W12 Heron-r2 run is the developer's (OQ-4); everything below is static + statevector sim.

## The organism (one thing, not two)

A single proto-viral organism whose genome has two co-inherited parts:
- **witness loci** (`viv_witness_q`, the W-generation GHZ germ line) — the certified quantum heredity `⟨X^⊗W⟩`;
- **classical genes** (`viv_gene_q`: role/repl/life) — diagonal trait bits, read to **express** the body.

Plus a mortal **soma**: a unary **body** walker on a `track`-site habitat, a **food** lattice, an
**energy** accumulator, a per-site **death bath**, and (only under `--hard-select`) one fitness ancilla.

Layout at W3/track5 (from `--dump-circuit`): witness `0..2` | genes `3..5` | body `6..10` |
food `11..15` | energy `16..17` | bath `18..22`.

## The asymmetric Weismann barrier (the faithfulness point)

Not total germ⊥soma disjointness (that would be two separate things). Directional:
- **germ→soma expression is PRESENT** — the classical genes drive the body (a diagonal
  `cx(gene_role → body)` gate; motility gene sets the hop). The paper's gene→body information is itself
  classical (⟨σz⟩-encoded), so classical/diagonal expression is faithful.
- **soma→germ back-action is FORBIDDEN** — no coherent gate couples a **witness locus** to the mortal
  body; the walking/eating/dying body cannot decohere the certified genealogy.

`vivarium_coupling_report` (static walk of `qc.data`) certifies this: `expression=True`,
`back_action=False`, `witness_isolated=True` for `barren`/`vivarium`; `back_action=True` for the
`germ_coupled` A/B arm.

## Survival of the fittest is EMERGENT, not scripted

The whole life cycle is a Trotterised evolution of one fixed local `H_viv`:
- **H_forage** — nearest-neighbour `rxx+ryy` quantum-walk hop (hop scaled by the motility gene; one
  energy-controlled hop = state-dependent foraging);
- **H_eat** — `ccx(body,food → energy)+cx` consumption that fires **only where body and food coincide**
  (emergent co-location, no `if(ate)`);
- **H_bud** — `ccx(energy,body → neighbour)` reproduction powered by having eaten;
- **death + revive** — every body ages toward `|0⟩` via a bath (amplitude damping = the paper's
  dissipation / trace-out of dead units), then the **fed are revived** — the fittest survive.
No mid-circuit measurement, no feed-forward, no classical branch (`has_classical_branch=False`).

## `--selftest` result (static, no execution)

`python code/pj_qalife.py --vivarium --selftest` → **SELFTEST PASS** at W∈{2,4,12}, seven checks each:

1. asymmetric barrier — expression yes; back-action no; `germ_coupled` breaks it. **OK**
2. witness loci isolated in `vivarium`/`barren`, not in `germ_coupled`. **OK**
3. germ line built before the life cycle (rung-0 ordering). **OK**
4. witness readout: H on the witness loci only (body/food/energy/genes stay Z). **OK**
5. no classical branch (fully unitary life cycle). **OK**
6. selection laws touch no witness locus (diagonal). **OK**
7. `barren` == `vivarium` **minus the food seed** — identical circuit law, only the seed differs
   (`extra_x_seed = n_food`). The "alive, not on rails" proof: behaviour comes from the seed, not the code. **OK**

PJ0 (`--selftest`) and PJ1 (`--arena --selftest`) remain green; `qalife.py`, `run_qalife.py`,
`pj_run_qalife.py`, `pj1_run_arena.py` are byte-stable (`git status` clean on those files).

## Sim result (statevector, W3/track5/steps5) — see `CONCLUSION.html`

| arm | witness ⟨X^⊗3⟩ | population (alive) | food left | verdict |
|-----|---------------|--------------------|-----------|---------|
| barren       | +1.000 | 0.41 | 0.00 | witness survives; body starves |
| vivarium     | +1.000 | 0.87 | 1.64 | witness survives; **fed body thrives** |
| germ_coupled | +0.006 | 1.23 | 1.63 | **witness collapses** (barrier broken) |

The emergent contrast: `vivarium` population (0.87) ≈ 2× `barren` (0.41) — the fed survive — while the
germ witness stays certified (+1.000) and only the deliberately-miswired `germ_coupled` arm collapses it.
Circuits per arm: `circuits/vivarium_W3_track5_{barren,vivarium,germ_coupled}.txt`.
