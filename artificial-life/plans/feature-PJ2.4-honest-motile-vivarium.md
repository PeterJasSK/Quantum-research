# feature-PJ2.4 — Honest motile vivarium (2018-faithful life that also moves)

**Status:** Approved (2026-09-27)
**Epic:** qalife-darwinian-richness (PJ2.x line; successor to PJ2.2 movement-only lattice/line)
**Driver of record:** `code/1D_alive.py` (movement) + `code/pj_qalife.py` (`line_*`, `build_line_vivarium`)

---

## 1. Why (the honesty verdict this fixes)

The current `1D_alive` / `build_line_vivarium` is an excitation-conserving quantum walk + a germ GHZ
X-parity witness — **movement + heredity only**. Reviewed honestly, the moving organism on screen
**cannot** be called "quantum artificial life":

1. **The motion shown is classically reproducible.** Body occupancy `⟨n_i⟩` is a Z-basis population;
   a classical random walk gives the same bars. No quantum signature is displayed or measured in the
   dynamics.
2. **No life is acting.** Solo movement has no reproduction, selection, metabolism, or death — a
   single diffusing field is not alive even in the loose ALife sense.
3. **The one quantum number is single-basis.** `⟨X^⊗W⟩` vs the product null excludes independent
   classical fields but NOT a classically-correlated mixture (coin over |+…+⟩/|−…−⟩), because the germ
   is measured in one basis only. Not a rigorous entanglement certificate.

**Goal of PJ2.4:** a small-scale organism that **moves in space** AND has **reproduction, selection,
metabolism, and death genuinely acting**, faithful to the Alvarez-Rodriguez 2018 QAL model, so the
label "quantum artificial life" is earned rather than dressed on.

## 2. Decisions (locked with the developer)

- **D1 — Death = 2018 UNITARY aging, NOT amplitude damping.** Damping was tested and is worse in every
  way on hardware (and is a refuted design in this project's history). Reuse `qalife.py`'s
  `death="unitary"` mechanism: aliveness is a rotation angle that ages toward the dark |0⟩ state; no
  bath ancilla, no reset, no mid-circuit measurement. Death genuinely acts (the aged individual goes
  dark) and stays hardware-friendly. This is the "faithful death design" of record.
- **D2 — Minimal scale.** 1 founder that reproduces into a 2nd individual; short line (L≈4). Target
  ≤ ~15 usable germ+body qubits so it runs clean on Heron. Every process must be individually visible.
- **D3 — Witness certification is a SWITCH.** `--certify xonly|ghz2`. `xonly` = today's single-basis
  `⟨X^⊗W⟩` (fast, weak). `ghz2` = add the Z-sector setting so the genealogy is a real entanglement
  certificate. Ship both; if `ghz2` collapses the witness on hardware, a weak-but-honest claim beats a
  broken one — but we will have measured it, not assumed it.

## 3. What already exists (reuse, do not reinvent)

Mapped from `qalife.py` (2018 base) and `pj_qalife.py` (`viv_*`, `line_*`):

| Life process | Existing mechanism to reuse | file:line | Unitary? |
|---|---|---|---|
| Reproduction | genotype CNOT clone (`cx(geno k-1 → k)`) + metabolism-gated bud `ccx(energy,body→neighbor)` | `qalife.py:129`, `pj_qalife.py:990` | yes |
| Mutation | `ry(thetas[k])` on genotype | `qalife.py:130` | yes |
| Expression / birth | gene→soma `cx(gene_ROLE → body_0)` | `pj_qalife.py:965` | yes |
| Movement | `rxx(θ)+ryy(θ)` NN quantum walk on body cells (`_line_walk_layer`) | `pj_qalife.py:1727` | yes |
| Metabolism (eat) | `ccx(body,food→energy)` + consume `cx(energy→food)` | `pj_qalife.py:987` | yes |
| Death (FAITHFUL) | **unitary aging** `ry(aged)`, angle → 0 = dark = dead | `qalife.py:133-137` | yes |
| Selection | revive the fed `cx(energy→body/vitality)`; hard `mcx(all energy→fit)` | `pj_qalife.py:1004,1016` | yes |
| Entanglement witness | germ GHZ + `xbasis_witness_from_counts` (X-parity vs product null) | `qalife.py:217` | observable |

The **only genuinely new work** is: (a) marrying the walk (movement) to the aging life-cycle on a
per-individual **position field**, and (b) the 2-basis GHZ witness option. Everything else is wiring
existing, tested gates in a faithful order.

## 4. Architecture — `build_motile_vivarium`

New builder in `pj_qalife.py`, alongside `build_line_vivarium` (which stays byte-stable). One
individual = **genotype rung** (germ, GHZ lineage — carries the witness) + **position field** (unary
occupancy over L cells — the body that walks) + **vitality** (aliveness that ages → death). Food is a
small fixed lattice; energy accumulates on eat.

### Per-individual qubit layout (contiguous block, individual `o`)
```
[ genotype rung g_o | vitality v_o | body cells b_o[0..L-1] | energy e_o ]
```
- genotype `g_o`: 1 qubit/individual → the GHZ lineage (witness set = all `g_o`).
- vitality `v_o`: 1 qubit/individual → 2018 phenotype aliveness; ages toward |0⟩ (death).
- body `b_o[i]`: L unary cells → position field that walks.
- energy `e_o`: 1 qubit → "ate this generation" accumulator.

Founder = individual 0; individual 1 is BORN by reproduction (not pre-allocated as alive — its block
exists but stays dark until the parent buds).

### The honest life cycle (one generation `d`, gate order)
1. **Germline (once, up front):** founder `ry(π/2)` on `g_0`; mutation `ry(θ_0)`. Weismann barrier:
   genotypes built before any body gate; no gate ever couples `g_o` to a body/vitality qubit in the
   isolated arm.
2. **Express / birth:** `cx(g_0 → v_0)` (genotype expresses vitality), seed body `x(b_0[start])`.
3. **Walk (movement):** `_line_walk_layer` on `b_o` — the excitation-conserving quantum walk.
4. **Metabolism:** at each food site `s`: `ccx(b_o[s], food[s] → e_o)` (eat), `cx(e_o → food[s])`
   (consume).
5. **Aging / DEATH (unitary, D1):** rotate vitality toward dark by the age-dependent angle
   (`ry(−δ·age)` style, the `death="unitary"` aging), THEN **revive the fed**: `cx(e_o → v_o)` — a fed
   individual resets its aging; a starved one goes dark. Selection EMERGES (no measurement).
6. **Reproduction (metabolism-gated):** if fed, at gen = `REP_GEN`: clone genotype `cx(g_0 → g_1)`
   (2018 UC + heredity), express daughter `cx(g_1 → v_1)`, seed daughter body one cell over
   `ccx(e_0, b_0[s] → b_1[s+1])`. The 2nd individual is BORN, at a position, from having eaten.
7. **(coupled arm only)** soma→germ wound: `rxx+ryy(b_0[c], g_0)` — the A/B control that must collapse
   the witness (proves the isolated witness is load-bearing).

### Observables banked per certified frame (depth scan, as today)
- **Position fields** `⟨n_i⟩` per individual (the moving bars) — from body Z marginals.
- **Alive/dead** per individual — vitality `⟨σz⟩` vs `ALIVE_THRESH` (`alive_population`,
  `deepest_surviving_lineage`, `qalife.py:192,197`). This is what makes death/selection *visible*.
- **Energy / ate** — `e_o` marginal.
- **Witness** — `xonly`: `⟨X^⊗W⟩` vs product null (today). `ghz2`: add the Z-sector (below).

## 5. Witness certification switch (D3)

`--certify xonly` (default, current behavior) vs `--certify ghz2`:

- `ghz2` banks **two measurement settings** per frame (two circuits): the existing X-basis parity
  AND a Z-basis genotype readout for the `⟨Z_i Z_j⟩` correlations. Combine into the standard GHZ
  witness `F = ½(⟨X^⊗W⟩ + all-Z-correlations)`-style bound so a classically-correlated mixture is
  excluded. Report `certified_entangled: bool` in meta.
- Cost: doubles the germ circuits per frame (bodies unaffected). Acceptable at minimal scale.
- Honesty outcome recorded either way: if `ghz2` drops the certificate below threshold on hardware,
  the run says so — a weak honest claim, not a broken one.

## 6. Files to touch

- `code/pj_qalife.py` — NEW: `build_motile_vivarium` + `motile_*` layout/observable helpers +
  `_motile_selftest`/`run_motile_selftest` (static structural checks) + `print_motile_report`. Reuse
  `_line_walk_layer`, `xbasis_witness_from_counts`, the viv eat/bud gates, the `death="unitary"`
  aging. **`build_line_vivarium` and all `line_*` stay byte-stable.**
- `code/1D_alive.py` — add `--model line|motile` (default `line` for back-compat), `--certify`,
  `--individuals`, `--food` (sites); when `motile`, run the new depth-scan that also banks
  alive/energy; extend meta (`model`, `alive`, `energy`, `certify`, `certified_entangled`).
- `analysis/line_render.py` + `mockups/line_scenarios.html` — render the new signals: dead individuals
  fade/greyed, food sites marked, energy pip, a "born" pulse when the daughter appears, alive-count in
  the HUD. Keep the existing bars/poke.
- `plans/` — this file.

## 7. Acceptance criteria / honesty gates

- **AC1** All four processes provably ACT in one sim run at minimal scale: (a) reproduction — a 2nd
  individual appears only after the parent eats; (b) metabolism — energy fires only on body+food
  co-location; (c) death — an unfed individual's vitality `⟨σz⟩` crosses to dark; (d) selection — fed
  survives, starved dies (`deepest_surviving_lineage` reflects it).
- **AC2** Movement still real — the surviving individual's position field walks across the line (as
  PJ2.2).
- **AC3** Faithful death is UNITARY (static test: no `reset`, no mid-circuit `measure`, no bath in the
  motile circuit); death enters only as the age-dependent aging angle. (D1)
- **AC4** Weismann barrier intact in the isolated arm (static test: no gate couples a genotype qubit
  to a body/vitality qubit); coupled arm demonstrably collapses the witness.
- **AC5** `--certify ghz2` produces a defensible entanglement certificate on sim (excludes the
  classical mixture); the hardware result is banked and reported honestly whatever it is.
- **AC6** Fits the qubit budget: minimal scale ≤ ~15 qubits (report `motile_segment_len`).
- **AC7** No overclaim in copy: the page/README states exactly which parts are certified quantum
  (genealogy witness) vs classical-visualizable (position field), and that life processes are acting.

## 8. Qubit budget (minimal, D2)

Per individual = `1 (geno) + 1 (vitality) + L (body) + 1 (energy)` = `L+3`. Two individuals + shared
food lattice `F`: `motile_segment_len = 2·(L+3) + F`. With **L=4, F=2** → `2·7 + 2 = 16` (tight;
drop to L=3 → 14, or fold energy into a shared 1-qubit for 13). Founder-only frames (before the bud)
use half. Sim cap 27 fine; Heron target met at L=3–4.

## 9. Phases / tickets

- **[DONE] M0 — model skeleton (sim):** `build_motile_vivarium` + `motile_*` helpers +
  `motile_segment_len` + `run_motile_selftest` (AC3/AC4/AC6). `pj_qalife.py`.
- **[DONE] M1 — death + selection acting:** unitary CLAMPED aging on vitality + revive-the-fed; banks
  alive/energy. Barren run: alive `1.0→0.77→0.29→0→0` (dies, stays dead); fed founder lives (AC1c/d, AC2).
- **[DONE] M2 — reproduction acting:** metabolism-gated bud (geno clone + daughter body seed);
  daughter born at gen3 only after the parent ate (AC1a/b).
- **[DONE] M3 — witness switch:** `--certify xonly|ghz2`; 2-basis GHZ certificate (`⟨XX⟩+⟨ZZ⟩>1`);
  sim `certified=True` from the birth gen (AC5).
- **[DONE] M4 — driver + web:** `1D_alive.py --model motile` + meta; `line_render.render_motile` →
  `motile_life.html` with dead-fade / food diamonds / born pulse / alive-count + honest header+footer
  (AC7). Node smoke 0 failures; line + standalone pages regression-clean.
- **[DONE] M5 — hardware run (ibm_marrakesh, 2026-09-27):** minimal config, ghz2. **The 2-basis
  certificate SURVIVED** (`⟨X^W⟩≈0.98`, `⟨ZZ⟩≈0.98`, `⟨XX⟩+⟨ZZ⟩≈1.96>1`, certified gens 3–5).
  Reproduction (daughter born gen3), death/aging (founder declines), and succession all read on
  hardware. Writeup: `research/pj2_vivarium/MOTILE_CONCLUSION.md`.

**Status:** M0–M5 COMPLETE (2026-09-27). On hardware, with ghz2, a certified-quantum genealogy carries
heredity while reproduction/metabolism/selection/death act — "quantum artificial life" earned for the
run. Model/driver/renderer additive; `build_line_vivarium`, `2D_alive`, line page stay byte-stable.
Follow-ups (optional): germ selective-DD in the motile path; tune founder feeding robustness.

## 10. Verification

- **Static (no sim):** `run_motile_selftest` — unitary-death check (no reset/measure/bath), Weismann
  isolation, mass/excitation bookkeeping, qubit-count == `motile_segment_len`, born-after-eat ordering.
- **Sim:** depth scan showing the four processes acting (the AC1 table printed per gen), position walk,
  witness under `xonly` vs `ghz2`.
- **Node smoke:** render the filled page headless (as the `line_*` renderer is already tested) — all
  modes/frames, 0 failures; dead/born/food markers draw.
- **Hardware:** minimal Heron run; compare `xonly` vs `ghz2` witness; report honestly.

## 11. Out of scope

- Large populations / long lines (this is the honest MINIMAL demonstrator).
- Amplitude-damping death (rejected, D1).
- 2D lattice motile (1D first; lattice is a later port if this holds).
- Changing `build_line_vivarium` / `2D_alive` (byte-stable; PJ2.4 is additive).
