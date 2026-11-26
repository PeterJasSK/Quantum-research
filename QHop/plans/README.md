# QHop — plans and sources

Project name: **QHop** (game + thesis). Paper title will differ (working: "Which noise kills the quantum MCMC
advantage, and when it starts biasing the samples").

Core idea: quantum-enhanced MCMC (Layden et al., Nature 2023) as a map-generation race. The quantum proposal *hops*
between valleys; classical local moves get stuck. Science: noise-type-resolved threshold ε\*, T1-induced proposal
asymmetry and sample bias, coherent vs dephased control on IBM Heron (Ferguson–Wallden open question).

## Files
| File | What |
|---|---|
| `study-idea-qh-18-quantum-leap-map-game.md` | main idea: game, visualization, bounds test protocol |
| `study-idea-qh-15-qemcmc-noise-threshold.md` | ε\* threshold study (measurement core) |
| `study-idea-qh-17-quantum-proposed-tumour-CLOSED.md` | closed: no quantum point inside the lungs (history) |
| `demo-quantum-leap-race.html` | playable prototype (exact browser simulation); published at https://claude.ai/artifact/LLtRPYSLYdJRGPEQ6C7rgd (private) |
| `re-dossier-02-quantum-enhanced-mcmc.md` | own Layden reproduction (k 0.250 / 1.017 / 0.939 vs 0.264 / 0.94 / 0.948) |
| `papers/` | source PDFs (copied from QuantumPhantoms relatedPapers) |
| `reading.txt` | reading order with a short note per paper |

## Papers
Saved in `papers/`:
- Layden et al. 2023, Quantum-enhanced MCMC, Nature — https://arxiv.org/abs/2203.12497
- Ferguson & Wallden 2025, coarse-grained QeMCMC (open question on noise) — https://arxiv.org/abs/2405.04247
- Heese 2024 (IEEE CG&A), Quantum Wave Function Collapse — **prior art for quantum map generation, read before claiming novelty**
- Wootton (3 papers) 2020–2021, quantum procedural generation and Quantum Blur — prior art for quantum game maps
- Aaronson 2015, Read the fine print — honesty frame for speedup claims

Not saved yet (download):
- Orfi & Sels 2024, why the advantage needs the intermediate regime — https://arxiv.org/abs/2408.07881
- Marshall et al. 2026, QeMCMC optimisation at 117 variables on IBM — https://arxiv.org/abs/2602.06171
- Christmann et al. 2024, quantum-inspired classical proposals (verify ID) — https://arxiv.org/abs/2411.17821

Note: the PDFs here are not gitignored (unlike `QuantumPhantoms/plans/relatedPapers/papers/`); add
`QHop/plans/papers/` to `.gitignore` before committing if they should stay local.

## Next
`/plan-epic` for QHop. First experiment: add depolarizing and T1 noise to the simulator and compare curves.
