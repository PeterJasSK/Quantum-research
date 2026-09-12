# PJ0 Germ/Soma Split — Static Correctness Evaluation

**Stage:** PJ0 (epic `qalife-darwinian-richness`, stage P3) · **Date:** 2026-09-12
**Verification (CD-7 / OQ-4):** STATIC only — `--selftest` circuit-structure assertions +
`--dump-circuit` printing + this written argument. **No Aer/statevector sim, no hardware run**
in this ticket. The witness-vs-W sweeps and the matched-W-vs-P2-damping comparison are the
developer's to run later; this document proves the circuit-building code is *structurally*
correct.

Code: `code/pj_qalife.py` (model + `--selftest`), `code/pj_run_qalife.py` (driver, run wiring
dormant). The faithful reproduction (`code/qalife.py`, `code/run_qalife.py`) is **byte-stable**
(Q1) — `pj_qalife.py` imports `qalife` read-only for pure helpers only.

---

## The wound PJ0 fixes

P2 collapsed the damping ceiling to W\* ∈ [4,8). Cause: the faithful damping arm entangles the
mortal phenotype to the immortal genotype (`cx(g,p)`, `qalife.py:139`) then dissipates it — so
body-death irreversibly decoheres the gene-witness. PJ0 severs that coupling: the germ line
(genotype, GHZ, carries the witness) is built fully *before* any death (rung 0), the soma
(phenotype) expresses the trait as a **separable diagonal** state (no `cx(g,p)`) and dies **in
isolation** on qubits disjoint from the germ line (rung 1), with death mechanism as a parameter
(rung 2). The quantum claim stays the **genotype-only** witness ⟨X^W⟩ (CD-3).

---

## Static Test 1 — the honesty anchor (AC-PJ0.1, I4)

**Claim:** in the built circuit, **no gate has both a genotype qubit and a soma
(phenotype/bath) qubit in its operands** → soma death is qubit-disjoint from the germ line and
cannot touch the witness.

**Proof:** `germsoma_coupling_report` walks `qc.data`, classifies every gate's operands against
the germ set `{geno_q}` and soma set `{pheno_q, soma_bath_q}` (barriers/delays excluded — not
couplings), and flags any mixing gate. Result, from the printed circuits:

| build | soma_death | Static Test 1 (disjoint) | evidence |
|-------|-----------|--------------------------|----------|
| separable | natural | **YES** | `circuits/W{2,4,12}_natural.txt` |
| separable | local_damping | **YES** | `circuits/W{2,4,12}_local_damping.txt` |
| separable | none (control) | **YES** | `circuits/W4_none_control.txt` |
| **entangled (A/B)** | natural | **NO** — mixing `cx [g,p]` | `circuits/W4_entangled_AB.txt` |

The separable germ/soma layout keeps germ block `g_k = 0..W-1` and soma block `p_k = W..2W-1`
(bath `2W..3W-1` in local_damping) physically separate; the only gate that ever mixes them is
the deliberate `phenotype='entangled'` A/B mode (`cx [0,4],[1,5],[2,6],[3,7]` at W4), which
exists only to demonstrate the wound. `--selftest` asserts YES for all three non-entangled modes
at W ∈ {2,4,12} and NO for entangled.

---

## Gene-first ordering — rung 0 (AC-PJ0.1 check ii)

Every germ-block gate (founder / clone `cx` / mutation `ry`) precedes every soma-block gate in
`qc.data`: the germ line is fully passed before any death. Verified structurally
(`gene_first=YES` in every non-entangled report; `--selftest` check ii). The two-phase build in
`build_germsoma` makes this structural — Phase 1 builds the entire germ line, a `"germline"`
barrier, then Phase 2 the soma. (In the *measured* circuit the readout-basis `H` on genotypes
lands after the soma phase — that is readout, not gene-passing; the ordering report is therefore
computed on the bare biology build.)

## Witness-readout isolation (AC-PJ0.1 check iii, CD-3)

`to_witness_basis` applies `H` to genotype qubits only (separable soma stays diagonal in Z,
excluded from the witness). `--selftest` check iii: `H(geno)=W, H(soma)=0` at W ∈ {2,4,12}. The
entangled A/B mode additionally H's phenotypes (they then carry half the GHZ) — the honest
consequence of restoring the coupling.

## Separable ⟨σz⟩ closed form — rung 1 (AC-PJ0.1 check iv, AC-PJ0.4)

The soma `ry` angle equals `max(0, acos(_z_geno_chain[k]) − delta·age)` exactly — the same
product-state expression the faithful unitary arm uses (`qalife.py:135-137`). `--selftest` check
iv: `max|cos(ry) − z_closed_form| = 0.00e+00` at all tested widths. This is why a separable
diagonal phenotype is a **faithful** expression of the (classical, by the paper's text) trait,
not a cheat (CD-4).

## Entangled A/B contrast (AC-PJ0.4, check v)

`phenotype='entangled'` re-introduces `cx(g,p)` (fails Static Test 1) **while carrying the same
soma `ry` angle** as the separable build (`same_ry_angle=True` in `--selftest` check v). So both
builds set the identical diagonal soma expression by construction; the entanglement the damping
model paid for is **gratuitous** — it buys no extra biology, it only costs the witness. Shown by
the circuit diff (`W4_entangled_AB.txt` vs `W4_natural.txt`) and the closed-form angle, not by a
run.

---

## Rung 2 — natural decoherence + selective DD (AC-PJ0.2, AC-PJ0.3)

Built and statically evaluable in the driver (`pj_run_qalife.py --schedule-report`, needs
`--backend` for real gate timing — no submission is made):

- **Selective DD (AC-PJ0.3, the physical Weismann barrier):** `schedule_with_selective_dd`
  transpiles (opt-3), maps genotype virtual qubits to physical via the final layout, and pads
  `PadDynamicalDecoupling` (XX) on the **genotype physical qubits only**. The report counts DD
  X-gates per qubit and asserts `DD on soma = 0` (phenotypes DD-free).
- **Natural-decay aging clock (AC-PJ0.2, bounded not rigid — Q6):** `aging_order_deviation`
  ranks somas by summed `delay` idle on the scheduled circuit vs their birth rank (individual k,
  oldest first) and reports `max_deviation` in generations. Aging need **not** be monotone —
  small irregularity (a grandparent soma outliving a grandchild) is a lifelike feature; the gate
  is only on scale: `max_deviation ≤ AGING_ORDER_TOL` (default 2). If exceeded → targeted delays
  on outliers, or fall back to `local_damping` (rigid controlled rate). `soma_death` is a
  parameter: `natural` (gate, no bath → leaner 2W segment) and `local_damping` (reference,
  +bath) are both coded and selectable.

---

## Soma-death parameterization (AC-PJ0.5)

- **natural** — death rate = hardware **T1**; drifts run-to-run (report a **T1 band**, min–max
  over calibration snapshots, not a point). Realized via per-soma `delay` scaled by age + the
  no-bath layout. Not tunable — that is the honest cost.
- **local_damping** — controlled rate `g_eff(age, γ) = 1 − (1−γ)^age` via a phenotype-scoped
  bath (the damping arm with `cx(g,p)` removed). Reproducible reference the natural arm is
  compared to.

The driver JSON schema carries `soma_death`, `phenotype`, `selective_dd`, `kept_fraction`,
`meta.calibration`, `meta.t1_band`, `witness_soma_on`/`witness_soma_off` — present so the
developer's later runs bank uniformly (all `None` here; nothing is executed).

---

## What the developer runs next (out of scope here — Q3/Q4)

- witness ⟨X^W⟩ vs W sweep at any W (W12 anchor) on the longest low-error Heron-r2 chain,
  separable-null overlaid (must sit ≈0);
- matched-W germ/soma vs the P2 damping arm — does severing `cx(g,p)` push W\* back past [4,8)?
- soma-on / soma-off witness pairing (the hardware analogue of Static Test 1);
- the T1 band and kept-fraction under selective DD.

The driver emits the schema + comparison hooks; it banks no run data in this ticket.

---

## Reproduce

```
cd artificial-life/code
python pj_qalife.py --selftest                                  # 5 static checks, W{2,4,12}
python pj_qalife.py --width 12 --steps 6 --dump-circuit         # circuit + correctness report
python pj_qalife.py --width 4 --steps 4 --phenotype entangled --dump-circuit   # A/B contrast
python pj_run_qalife.py --dump-circuit --widths 12 --steps 6    # measured build (never submits)
python pj_run_qalife.py --schedule-report --widths 12 --backend <heron>  # rung-2 (timing only)
```

Printed circuits are banked under `circuits/`; `selftest_output.txt` is the `--selftest` run.
```
git diff --stat code/qalife.py code/run_qalife.py   # empty — reproduction byte-stable (Q1)
```
