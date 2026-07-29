# Study Ideas

One folder for all candidate studies. Finished ideas move to `complete/` (renamed `DONE-*`).

## Active — networking / RNG
- `net-1-unpredictability-as-network-primitive.md` — umbrella: 3 attacker games + boot-entropy fix
- `net-2-boot-entropy-fix.md` — Q-EaaS cures weak keys on headless devices (score 84, highest)
- `net-4-mtd-sdn-hopping.md` — moving-target defence, predictable hop schedule

## Active — quantum hardware
- `qh-2-temporal-drift-stability.md` — does QRNG quality survive recalibration cycles?
- `qh-3-minimum-extraction-budget.md` — cheapest extractor to pass NIST on Heron r2

## Active — visualization-first (new 2026-07-29)
Heavy graphics potential, in the spirit of the 3-body + load-balancing visuals. Each carries a
`## Thesis — IEEE short paper (6–8 pp)` block: one compelling central question, one defended claim,
one headline figure. Target = short double-column IEEE format.

| File | QC? | The visual | Likelihood | Want-to-do (me) |
|------|-----|-----------|-----------|-----------------|
| `viz-3-dns-poison-race.md` | non-QC | poison race, entropy cliff, SAD-DNS reveal | **80/100** — cited live threat, dramatic cliff | **5/5** — probably done first; strong visual, relevant, real answer findable |
| `viz-5-gossip-overlay-resilience.md` | non-QC | infection wavefront, eclipse goes dark | **78/100** — hottest topic, cited threat, cleanest curve | **3/5** — feels derivative of ECMP, but probably done last |
| `viz-2-quantum-galton-board.md` | **QC** | horns melting under noise, depth slider | **75/100** — hardware-backed, unambiguous knee | **2/5** — waiting on getting back into IBM accounts |
| `viz-4-randomness-texture-atlas.md` | non-QC | percolation/DLA/Turing/Ising gallery | **70/100** — strong hook + honest diagnostic | **4/5** — simple enough; beats the endless statistics randomness tests usually spit out |
| `viz-1-three-body-quantum-perturbation.md` | **QC** | divergence fan, phase-space ribbons | **68/100** — stunning but null-result risk | **4/5** — seems easy; most quantum heavy-lifting already done |

Likelihood = publishability. Want-to-do = my own appetite to build it (1–5).
2 quantum (viz-1, viz-2), 3 non-quantum (viz-3, viz-4, viz-5).
QRNG arms of all non-QC ideas source entropy from the **QEaaS API** — no new QC runs.

**Read as:** viz-3 + viz-5 are the safest standalone networking short papers; viz-2 is the safest
QC one; viz-4 is a strong diagnostic; viz-1 is the highest-visual/highest-risk bet.

*(viz-3 load-balancing-heat-theatre removed 2026-07-29 — already shipped as the ECMP web demo in
`TargetedDosColisionsAndRNGAngle/web/`; replaced by the DNS poison-race study.)*

## Complete
- `complete/DONE-calibration-guided-high-yield-qrng.md` → built as `CalibrationGuidedHighYieldQRNG/`
- `complete/DONE-ecmp-collision-dos.md` → built as `TargetedDosColisionsAndRNGAngle/`
