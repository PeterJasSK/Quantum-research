# PJ2.4 — Motile vivarium: what is (and isn't) "quantum artificial life"

**Model:** `pj_qalife.build_motile_vivarium` · **Driver:** `1D_alive.py --model motile` ·
**Renderer:** `analysis/line_render.py` → `research/pj2_vivarium/motile_life.html`

A minimal, honest organism that **moves in space** while **reproduction, selection, metabolism, and
death genuinely act** — faithful to the Alvarez-Rodriguez 2018 QAL model. This replaces the PJ2.2
movement-only claim, which was a quantum walk in ALife clothing.

## What each life process is (and that it acts)

Per individual = **genotype** (germ GHZ rung — heredity + witness) + **vitality** (2018 phenotype
aliveness) + **body** (unary field of L cells that walks) + **energy**. Food is a fixed habitat.

| Process | Gate | Acts (sim-verified) |
|---|---|---|
| Movement | `rxx+ryy` walk on body cells | body field travels the chain |
| Metabolism | `ccx(body,food→energy)` + consume | energy fires only on body∩food co-location |
| Reproduction | `cx(g0→g1)` clone + `ccx(energy,body→neighbour)` bud | daughter born **only after the parent ate** (gen = rep_gen) |
| Death | **unitary aging** `ry(−min(π, δ·age))` (clamped) | barren run: alive `1.0→0.77→0.29→0.006→0` and **stays dead** |
| Selection | `cry(δ·age, energy→vitality)` revive-the-fed | fed survives, starved dies — no measurement |
| Mutation | `ry(θ)` on genotype | 2018 spontaneous mutation |
| Heredity/witness | germ GHZ, `⟨X^⊗W⟩` (+ Z-sector under ghz2) | daughter inherits the lineage |

**Death is UNITARY** (faithful 2018 `death="unitary"`, damping rejected as worse): no reset, no
mid-circuit measurement, no bath. Verified monotone (no resurrection) after clamping.

## What is certified quantum — and what is not

- **Certified quantum:** the germ-line genealogy witness. `--certify ghz2` banks **two bases**
  (X-parity + Z-sector ⟨Z_iZ_j⟩) → a real GHZ/Bell certificate that **excludes classically-correlated
  mixtures** (separable bound ⟨XX⟩+⟨ZZ⟩ ≤ 1; sim gives 2.0 → certified). `--certify xonly` is
  single-basis X-parity: weaker, but honest.
- **Classically visualisable:** the moving body occupancy (the bars) is a Z-basis population — a
  classical random walk reproduces it. **The quantum claim is the genealogy, not the motion.** The
  page says so explicitly.

So: the moving organism can honestly be called quantum artificial life **iff** run with `ghz2` and the
certificate survives on hardware — because then a genuinely-entangled genealogy is doing the heredity
while real life processes act. Under `xonly` the honest label is "a 2018-faithful living organism whose
genealogy shows quantum-consistent multipartite correlation."

## How to run

```
# sim, life + reproduction + selection, 2-basis certificate:
python code/1D_alive.py --model motile --organisms 2 --length 4 --gens 6 --food 1,3 --certify ghz2
# barren (death acts):
python code/1D_alive.py --model motile --organisms 1 --length 4 --gens 6 --food ''
# static structural checks (unitary death, Weismann, budget):
python code/pj_qalife.py --motile --selftest
# render:
python analysis/line_render.py --run-glob 'research_runs/pj2_motile/*sim*.json'
```

## Sim results (minimal scale, org=2, L=4, food=1,3, ghz2)

- witness `⟨X^W⟩` = 1.0 (noiseless sim); zz = 1.0 after the clone; **certified = True** from the birth gen.
- alive/born: founder lives; **daughter born at gen3** and survives when fed.
- barren: founder ages to death by gen3 and stays dead.
- budget: 16 qubits (org2/L4), 14 (org2/L3), 9 (org1/L4) — Heron-fits.

## Hardware (M5 — DONE, ibm_marrakesh, 2026-09-27)

Minimal config (org=2, L=4, gens=6, food=1,3, ghz2, 8192 shots) on `ibm_marrakesh` (Heron):

- **The 2-basis certificate SURVIVED.** `⟨X^W⟩ ≈ 0.98`, `⟨ZZ⟩ ≈ 0.98` → `⟨XX⟩+⟨ZZ⟩ ≈ 1.96 > 1`,
  `certified = True` for gens 3–5. A genuine entanglement certificate on real hardware — a classically
  correlated mixture is excluded. **The genealogy is certified quantum, measured not assumed.**
- **Reproduction acts:** daughter body appears at gen3 (`born → 2`), body1 `[0, 0.24, 0.26, 0.16]`.
- **Death/aging acts:** founder vitality declines `0.99 → 0.81 → 0.55 → 0.40 → 0.46` under partial
  feeding; the daughter is born alive (`1.0 → 0.82 → 0.51`) — a generational **succession** (alive-count
  reads 1 as the founder hands off to the daughter, not a headcount bug).
- **Honest caveat:** founder feeding is marginal under noise (energy ≈ 0.4), so it half-survives rather
  than thriving — real hardware behaviour, tunable via more food / higher hop / more shots. A pre-birth
  readout artifact on the idle daughter qubit is now masked in `reduce_motile`.

Verdict: with `ghz2` on hardware, a **certified-quantum genealogy** carries the heredity while
reproduction/metabolism/selection/death act — so "quantum artificial life" is earned for this run.

Run: `research_runs/pj2_motile/pj2_line_org2L4_ibm_marrakesh_20260927-180920.json`.

```
python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 --gens 6 \
    --food 1,3 --certify ghz2 --shots 8192
```

## EM1 — germ dynamical decoupling (PJ2.5), the first mitigation lever

The M5 hardware result above was obtained with **no dynamical decoupling on the motile path** — the
driver ran its circuits through a plain `optimization_level=3` transpile (`_run_counts_simple`), while
only the sibling *line* path had germ-selective DD wired. PJ2.5 (epic **CD-11 / EM1**) closes that gap:
germ-selective DD is now applied to the motile organism too, as an explicit, switchable, **measured**
lever rather than a hardcoded global.

- `--dd {off,x2,xy4}` (default `x2`) selects the DD sequence; it pads only the **idle germ (witness)
  physical qubits** — body / vitality / energy stay DD-free (the Weismann barrier). DD is pure pulse
  suppression, **not** post-selection → `kept_fraction = 1`, so the witness stays an *unconditional*
  claim (raw, not conditioned on GHZ-looking shots).
- `--dd-ab` banks an A/B comparison per generation — the same circuit measured DD-off **and** DD-on —
  recording `witness_dd_off` / `witness_dd_on` (and `zz_dd_off` / `zz_dd_on`) side by side, plus a
  summary `delta_witness` and `delta_certified_gens`. EM1's honesty rule: the raw and mitigated
  witnesses are reported together, never the mitigated one alone.

**Sim A/B (org=2, L=4, gens=6, food=1,3, ghz2, 8192 shots).** DD-off and DD-on give identical
witnesses (`delta_witness = 0.000`, certified gens 3 → 3) — the correct noiseless result, since DD is
the identity in the absence of noise. This confirms the DD pass does not perturb the logical circuit.
Run: `research_runs/pj2_motile/pj2_line_org2L4_statevector_sim_sim.json`.

**Hardware A/B — PENDING.** The headline datapoint is a single `ibm_marrakesh` A/B at the exact M5
config; `ΔW*` (how far DD moves `⟨X^W⟩`, `⟨ZZ⟩`, and the certified-gen count) will be recorded here
against the no-DD M5 baseline above, honestly whatever the sign:

```
python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 --gens 6 \
    --food 1,3 --certify ghz2 --shots 8192 --dd-ab --dd x2
```
