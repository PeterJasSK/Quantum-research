# PJ1 arena — static correctness argument

Ticket **PJ1** (epic P3, `artificial-life/plans/feature-PJ1-two-organism-collision.md`). Verification is
static (`--selftest` + `--dump-circuit`) + sim, no test framework (CD-7). This file records the
static-correctness argument; the sim/HW results are in `CONCLUSION.html`.

## What the arena is

Two germ/soma organisms on one shared track. Each organism = a **contiguous germ block** (W qubits, the
clean GHZ genealogy carrying the witness — unchanged PJ0 discipline) + a **unary body track** (`track`
qubits, one excitation = the body's location, OQ-1) + `traits` idle qubits (rung-5 hook, built as nothing).
Bodies are quantum walkers (nearest-neighbour `rxx+ryy` hopping). Where they overlap, a coherent `rxx+ryy`
**exchange** entangles them — interaction emerges from co-location, never `if(contact)`.

Three arms: `none` (walk only, control), `soma_soma` (body↔body exchange; germ untouched),
`germ_routed` (the same exchange routed through a germ qubit — the cross-organism kill-switch).

## The five static checks (`python code/pj_qalife.py --arena --selftest`)

All green at W∈{2,4,12}, track∈{5,7}:

```
(i)   Static Test 1 per organism : soma_soma/none body↔germ DISJOINT; germ_routed MIXED
(ii)  ordering (rung 0)          : both germ lines built before any body gate  (gene_first=True)
(iii) witness readout isolation  : H on both germ lines only (H(germ)=2W, H(body)=0); bodies stay Z
(iv)  no classical branch        : fully-unitary collision (no c_if / measure / reset on the body path)
(v)   structural diff            : pass_through == soma_soma minus the collision layer
                                    (extra rxx+ryy == frame·2·track; all other gates identical)
SELFTEST PASS
```

Full output: `circuits/_arena_selftest.txt`.

## The argument, per acceptance criterion

- **AC-PJ1.1 (arena substrate).** `build_arena` places two germ/soma organisms as adjacent segments
  (`arena_base` tiling); each germ line is the clean W-individual GHZ chain. Static Test 1 holds
  **per organism** for `soma_soma`/`none` — check (i).
- **AC-PJ1.4 (emergent, not coded).** The collision is a coherent operator applied unconditionally at the
  shared sites: check (iv) shows **no** measurement-conditioned gate / measure / reset on the body path.
  The `pass_through` (`none`) build is exactly `soma_soma` minus the collision layer — check (v),
  `arena_coupling_report`. In sim, `none` contact-entropy = **0.0 at every frame** while `soma_soma`
  starts at 0.0 (t=0) and rises to ~1.5 bits only as the bodies co-locate — the "emergent, not
  `if(contact)`" evidence (see `CONCLUSION.html`).
- **AC-PJ1.5 (A/B kill-switch).** `germ_routed` routes the exchange through `germ_q(1,0)`; check (i) shows
  it **violates** per-organism Static Test 1 (organism-0 body coupled to a germ qubit), and the measured
  joint witness collapses relative to `soma_soma` at matched settings.
- **AC-PJ1.8 (selective DD on both germ lines).** `schedule_arena_selective_dd`
  (`code/pj1_run_arena.py`) pads DD (`[X,X]`) on the genotype physical qubits of **both** organisms only
  (bodies DD-free), via `arena_witness_qubits`. It re-implements PJ0's pass because PJ0's
  `schedule_with_selective_dd` derives its DD target internally from `pj.witness_qubits(width, has_bath)`
  (PJ0 layout, one organism) and cannot target the arena's two germ lines under the arena layout without
  editing `pj_run_qalife.py` (forbidden, Q5). Verified by inspecting the scheduled HW circuit.

## Byte-stability (Q5, §3)

`qalife.py`, `run_qalife.py`, `pj_run_qalife.py` are **not** edited. PJ0's `build_germsoma` and the
`organisms=1` path are untouched; `python code/pj_qalife.py --selftest` (PJ0) stays green. PJ1 is added as
new functions in `pj_qalife.py` + the new driver `pj1_run_arena.py` + `analysis/pj1_render.py`.
