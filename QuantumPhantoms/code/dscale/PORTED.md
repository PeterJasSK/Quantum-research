# Code copied from the reverse-engineering (RE) pipeline (D-SCALE)

D-SCALE uses a **frozen copy** of part of RE letter D (`D_quantum_growth/`), taken at commit `2609cbe` (plan
`feature-D-SCALE-decoherence-surviving-circuits.md`, Q12). The MVP never imports the RE tree. Fixes made in RE do
**not** reach this copy automatically: to sync, diff the RE source against the file here and re-apply the changes
listed below.

RE root: `QuantumPhantoms/plans/relatedPapers/reverse-engineering/`. All `shared.*` imports were replaced by
`imaging.seedhash` (same `derive_seed` / `rng` signatures, itself a copy of `shared/seedhash.py`). Every seed label
was renamed to a `"DS-*"` label (AC-18).

| MVP file | Copied from (RE @ 2609cbe) | Kept | Changed / dropped |
|---|---|---|---|
| `bp.py` | `D_quantum_growth/src/bp.py` | `BPTN` (gates, BP, gauge, `expect_1`, `expect_2`), `gates_of`, `interaction_graph`, `simulate`, `observables`, `exact_observables`, `fidelity_vs_sim`, `CHIS`, `_sv_observables`, `smallest_chi` | **`apply_2q` QR-reduces each site tensor before the SVD**: the "rest" legs are factored as Q R, the gate and the truncated SVD act on R (size (2 r_i) x (2 r_j), r <= 2 chi) and Q is multiplied back, so the truncated state is the same; measured identical to 1e-14 on the 12-q hexagon QCA (chi 2/4/8) and **104x faster** on a degree-4 square patch (kicked Ising 4x4, chi 8: 0.35 s vs 36 s). Dropped the run-dir adversary (`adversary_circuits`, `reference_observables`, `run_adversary`, `write_report`, `main`); added `equivalence`, `speed`, `main --equivalence` (AC-13 check: runs the RE side read-only in a subprocess from the RE folder and compares on the identical transpiled circuit, passed as QPY). |
| `tomography.py` | `D_quantum_growth/src/witness.py` | `corr`, `boot_se`, `chsh_S`, `tomo_pair`, `nearest_physical`, `negativity`, `vn_entropy`, `mutual_information`, `PAULI` | `rng` from `imaging.seedhash`; default bootstrap label `D-bootstrap` -> `DS-bootstrap` |
| `causal_states.py` | `D_quantum_growth/src/causal_states.py` | everything (`pmd_*`, `renewal_machine`, `stationary`, `classical_complexity`, `wu_model`, `wu_check`, `wu_cq`, `kraus_unitary`, `exact_words`, `hmm_words`, `kl_bits`, `best_classical_fixed_memory`, ...) | `rng` from `imaging.seedhash`; baseline label `D5-baseline` -> `DS-pmd-baseline` |
| `seedlift.py` | `D_quantum_growth/src/seed_shape.py` (`to_voxel_units`, `lift`, `PITCH_MM`, `TUBE`) + `D_quantum_growth/src/heavyhex.py` (`patch`, `_describe`, `layout`, `principal_axis`) | the lift (solid of revolution about the principal axis, tube radius 1.2 voxels, closing, centre component) and the two-cell / hexagon heavy-hex patch with its dodecagon layout | generalised to any planar graph: `patch(g, kind)` takes the coupling graph (RE: FakeMarrakesh only); added `square_coords`, `square_patch` (Nighthawk 12 x 10 grid, q = 10 r + c), `patch_dict` (any bipartite region, Kamada-Kawai fallback layout), `seed_patch` (21-site ideal / 12-site noisy seed regions, AC-10). Dropped `write` (RE contracts) and `heavyhex.coupling_graph` / `path` (D-SCALE uses `dscale.allocate`). |
| `families/pmd_bank.py` (`control_arm`) | `D_quantum_growth/src/memory_advantage.py` `build` | the mid-circuit q-machine (ry init, per step U -> measure output -> reset, Z / X / Y memory readout) | used only as the declared A/B control arm next to the deferred machine (lint rule 1 tolerated); placed on the first two qubits of the machine's path |

MVP-only (re-derived, not copied): `budget.py`, `targets.py`, `allocate.py` (re-derives the QALife `best_chain`
idea from `artificial-life/`; no code imported), `lint.py`, `pauli_noise.py`, `validate_noise.py` (QALife / PJ0 /
Big Cats setups re-derived from their written descriptions), `witness_scale.py`, `families/` (`ghz_spine`, `ch_qca`
with the parity-Goldilocks rule, `pmd_bank` deferred machine, `kicked_ising`), `survival.py`, `run.py`,
`hw_pack.py`.
