# Feature D-SCALE — Quantum growth at 40 / 100 / 120 qubits: plug-and-play decoherence-surviving circuit families, a survive-vs-simulable map, quantum seed shapes for the F5 grower, and a hardware runbook

**Epic:** [epic-quantum-phantoms-mvp.md](epic-quantum-phantoms-mvp.md) (Approved). **The epic has no D-SCALE row yet**; the developer adds it (Q1). The feature builds **on top of F5** ([feature-F5-re-realism.md](feature-F5-re-realism.md), Complete 2026-10-31). It is also the "L2 frontier" rung of P3 ([publication-plan-3-papers.md](publication-plan-3-papers.md) §4).
**Feature ID:** D-SCALE
**Author:** Claude (Opus)
**Date:** 2026-10-31
**Status:** Approved (developer, 2026-10-31; answers folded into §8; re-mapped from the RE folder into the MVP the same day, per Q12 and Q14)

> **Stack locked.** Python 3.13 (conda base `/home/peter/anaconda3/bin/python3`). Pinned in `requirements.txt`: qiskit 2.3.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy, scipy, scikit-image, SimpleITK. networkx 3.4 and matplotlib are in the base env. **No new dependency** (Q5). The installed runtime already ships `FakeNighthawk` (120 q), `FakeBoston` / `FakePittsburgh` (Heron r3) and `FakeKingston` / `FakeMarrakesh` (Heron r2).
>
> **Core directive.**
> - **Location.** New MVP package `code/dscale/`, run from `code/` with `python -m dscale.<module>`. The needed pieces of RE letter D (`plans/relatedPapers/reverse-engineering/D_quantum_growth/`, unchanged since `2609cbe`) are **copied frozen**, listed in `code/dscale/PORTED.md`, and never imported. Ideas from `artificial-life/` and `QuantumLife/` are re-derived; their hardware numbers are cited, their code is not used.
> - **Hook-in.** D-SCALE reads an F1/F4 run (`cohort_params.json` + `quantum_run.json`) and writes `research_runs/<run>/dscale/`. F5's `imaging` then grows each nodule from its **quantum seed shape** instead of the fixed Ø 2 mm ball. F3 shows an optional D-SCALE panel. Both changes are additive: a run without `dscale/` renders byte-identically.
> - **Hard rules.**
>   - **Nothing is ever submitted to a QPU.** No submission code exists; hardware lives only in a runbook for Peter (Q3/Q4).
>   - **Every run during implementation is a smoke run capped at 20 minutes wall-clock**, enforced in code (Q6). Full sweeps go into the runbook.
>   - First-run defaults: 4,000 shots, at most 15 repeats per result (Q9).
>   - Work on `main` (Q14). No commit unless Peter asks.
>   - No automated tests: manual verification only.

---

## 1. Why (Step Goal)

**Before (MVP after F5).**
- **D in the MVP is only F4 Mode-A.** It is optional, ≤ 20 q, measure-and-restart, and its witness is flat at W ≈ 1.91 on Aer. Its single-qubit fate dial is a classical biased coin (`f4_qalife/loop.py:_fate_prep`). It feeds only parameters: README "F4 feeds only parameters, does not drive E growth".
- **F5 ignores the quantum layer when growing.** It grows every nodule from the same 2 mm ball: `imaging/growth.py:112 seed_ball`, called at `:274`, a PORTED.md decision. **The quantum layer never shapes a tumour.**
- **RE letter D exists but is small.**
  - Lineage: ≤ 8 q, dynamic circuit; BP reproduces it at bond dimension χ = 2.
  - Memory model: 1-qubit, with a gap below the sampling floor.
  - QCA:
    - the exact rule needs C³-H, which costs **376 routing SWAPs**;
    - the witness fails under Heron noise, so its seed shape is L0;
    - BP does not reach 0.99 up to χ = 16 on the 21-q patch.
- **The 108-qubit plan has no design.** `future.md` lists four conditions an L2 attempt must meet.

**What the sibling projects and the literature already proved on real hardware** (cited as evidence; no code imported):

| Lesson | Measured evidence | Source |
|---|---|---|
| A lean unitary GHZ spine survives to 100 q | ⟨X^⊗W⟩ = +0.058 at W = 50 (100 q), 3σ. Decay ≈ 0.94 per GHZ qubit (mut 0, DD x2; several settings changed at once) | `artificial-life/research/pj0_germsoma/PJ0_CONCLUSION.html:163-169` |
| Heavier biology decays faster | 2018 model, ibm_kingston 2026-08-25: W12 +0.301; W24 +0.038 ± 0.016 (alive at 2σ only); W32 +0.008 (dead). Decay ≈ 0.861 | `artificial-life/research/CONCLUSION_MONTH4.md:147-154` |
| Read out only at the end | Deferred readout c(1) ≈ 0.84 vs per-generation readout ≈ 0.10 | `artificial-life/research/RUNLOG_MONTH3.md:69,89,119,139` |
| Dynamic / teleport routing loses on Heron r2 | Lost 3 of 4 live comparisons (readout ≫ 2q error). Bäumer: unitary GHZ keeps GME to 17 q with DD; dynamic only to 6 | RUNLOG_MONTH3, stone-wall epic; RE paper HW05 §III |
| Never couple the certified register to active qubits | Separable soma +0.899 vs entangled `cx(g,p)` +0.120. Idle body +0.732 vs active body −0.058 next to a W = 12 germ | `PJ0_CONCLUSION.html:194-197`; `artificial-life/plans/feature-PJ2.1-gradual-biology.md:22-27` |
| Unitary aging, not damping | Unitary W* = 24 vs damping W* = 9 | `artificial-life/research/P2_CONCLUSION.html:145-148` |
| The founder needs variance | Without an equator founder, C(g ≥ 1) ≈ 0 | RUNLOG_MONTH2/3 |
| Our 48-q ceiling is a method limit, not a hardware limit | IBM "Big cats": 100-q GHZ F = 0.55(3) on ibm_kingston, 0.70(4) on ibm_kobe; **120-q F = 0.56(3) on ibm_aachen**. Recipe: BFS tree of depth 18, 8 end-measured parity checks, 28 % of shots kept, DD, TREX/M3 | arXiv 2510.09520 |
| Width alone does not beat BP | BP error ~exp(−c·l), with l = smallest loop: heavy-hex 12, square lattice 4 (inferred). At fixed χ the error falls with more hexagons. The hard window is non-Clifford θ_h ∈ [π/8, 3π/8] at depth beyond ~6–20 steps | RE paper HW04 Methods, Fig. 2d, 4 |
| QCA without multi-control gates | Jones: T6 = **two CH gates per site** (because H² = 1). 1-D networks decohere at fixed depth t ≈ 10, independent of L | RE paper D14 Fig. 1c, 2–4 |

**After.**
1. **`code/dscale/`.** Four plug-and-play circuit families behind one interface. Each family has a **40, 100 and 120-qubit preset** (Q2: all three versions) and passes coded survival laws:
   - `ghz-spine`: certified clonal genealogy as a Big-Cats GHZ tree with a separable, draw-driven soma (L1 via GME);
   - `ch-qca`: single-control Goldilocks QCA, SWAP-free on heavy-hex and on Nighthawk's square lattice (L1 at shallow depth; the frontier family);
   - `pmd-bank`: re-tuned, deferred-measurement causal-state machines in parallel (L1′, gap above the floor);
   - `kicked-ising`: Kim/Tindall anchor for calibration.

   A **composite** puts spine + QCA + PMD on one chip with physical buffers.
2. **A survival kit.** Calibration pruning, allocation with buffers, lints, a Pauli-twirled noise model for stabilizer simulation at 120 q, Clifford twins, TREX-lite and k·σ ladders.
3. **A survive-vs-simulable map** per budget and target. Each cell is classified `dead`, `alive_bp_easy` or `alive_bp_hard`. The `alive_bp_hard` cells are the **Goldilocks zone**, the only honest meaning of "closer to quantum advantage" here. An empty zone is a reported result.
4. **The quantum layer shapes the tumour.** Per tile, a QCA snapshot driven by the tile's draw becomes the 3-D seed that F5's grower starts from. The tile records the seed source and claim level. F3 gets a D-SCALE panel with the claims, the map and the verdict.
5. **A runbook for Peter.** Full simulation sweeps, plus hardware packs (ISA circuits, shot plans, QPU-time estimates) for the machines ranked in §4.

---

## 2. Acceptance Criteria

**Survival kit**

- [ ] **AC-1** (D-SCALE.1): a target registry exposes every simulation target.
  → `code/dscale/targets.py`: `TARGETS` holds:
    - `marrakesh` (FakeMarrakesh, default noisy mode);
    - `kingston` (back-test against QALife data);
    - `boston` (Heron r3, 40/100 proxy);
    - `nighthawk` (120 q, 10×12 grid, 218 couplers);
    - `helios-class`: generic all-to-all 98 q from the Helios datasheet (2q 7.9e-4, 1q 2.5e-5, readout p(1|0) 8.1e-4 / p(0|1) 1.6e-4, memory error 1e-3 per layer).

    `get(name)` returns graph, per-qubit/edge errors, readout p01/p10, T1/T2, durations, a calibration snapshot (props sha256, last_update_date, runtime version) and a label.
  → `python -m dscale.targets --show` prints n_qubits, edges, degree histogram, and median/p90 2q and readout errors. Checked 2026-10-31:
    - Nighthawk 120 q / 218 edges / degrees {2: 4, 3: 36, 4: 80} / 2q 0.0027 / readout 0.0049;
    - Boston 2q 0.0013 / readout 0.0051;
    - Marrakesh: 26 couplers with error ≥ 0.99.
- [ ] **AC-2** (D-SCALE.2): regions are allocated from calibration, with pruning, physical buffers and no artificial width wall.
  → `code/dscale/allocate.py` (re-derives the QALife `best_chain` idea).
  → Pruning: drop qubits with readout > 0.06 or sx ≥ 0.5, and edges with 2q > 0.02 (Nighthawk-RCS rule, arXiv 2609.28657).
  → Builders:
    - `path(n)`: branch-and-bound, cost e2q + 0.5·(ro + sx of both ends), time box 40 s;
    - `bfs_tree(n, root)`: minimum-depth spanning tree;
    - `patch(n)`: connected, grown from the centre by lowest cost;
    - `composite(budget, target, recipe)`: disjoint regions at graph distance ≥ 2 (≥ 1 idle buffer qubit).
  → Only the qubits a region uses are gated. This fixes PJ0's "107-qubit wall": its gate checked a 2W chain when only the W germ qubits needed one.
  → Writes `allocation.json`. Exit 4 with the largest feasible size when a request cannot be met.
- [ ] **AC-3** (D-SCALE.3): every circuit passes the survival lints before it is simulated or packed.
  → `code/dscale/lint.py: lint(circuit, regions, family)`; a violation aborts with exit 5, unless the family declares an A/B control arm. Each rule carries its evidence as a code comment.
    1. No mid-circuit `measure` / `reset` / `if_else`. Parity-check ancillas are read at the end.
    2. Any quantum claim uses ≥ 2 bases.
    3. No 2q gate links a certified region to another region, and a buffer separates them.
    4. The founder / root starts on the equator.
    5. Spine rotations satisfy |θ| ≤ 0.1.
    6. At most 2 two-qubit gates per certified spine qubit.
    7. 0 routing SWAPs on `ch-qca` / `kicked-ising`.
- [ ] **AC-4** (D-SCALE.4): a Pauli-twirled noise model allows noisy simulation of Clifford circuits at 120 q, and it is checked against the full model.
  → `code/dscale/pauli_noise.py`:
    - `noise_model(target)`:
      - per-edge 2q depolarizing and per-gate 1q depolarizing errors;
      - asymmetric readout;
      - idle Pauli twirl from T1/T2, p_x = p_y = (1 − e^{−t/T1})/4 and p_z = (1 − e^{−t/T2})/2 − p_x, applied by a pass that turns each scheduled `delay` into an appended `pauli_error`.
    - `run(...)` on `AerSimulator(method="stabilizer")`.
    - `clifford_twin(circuit)`: swaps each non-Clifford gate for the family's declared Clifford stand-in **with the same CZ skeleton** (CH → CY).
  → `python -m dscale.validate_noise --pauli --smoke`: compares the Pauli model with `AerSimulator.from_backend(Fake<Target>)` on identical transpiled circuits:
    - ghz-spine at N ∈ {6, 12, 20};
    - the ch-qca twin, and the real ch-qca circuit, at 12–20 sites.
  → Pass: |Δ| ≤ max(0.03, 2σ). If it fails, every Pauli/twin verdict above 24 q is labelled `unvalidated`.
- [ ] **AC-5** (D-SCALE.5): the survival predictor is back-tested against real hardware numbers.
  → `python -m dscale.validate_noise --backtest --smoke` rebuilds (re-derived) three published setups and simulates them with the Pauli model on `kingston` and `marrakesh`:
    - the QALife 2018 ladder W = 3…32;
    - the PJ0 lean ladder W = 6…50;
    - the Big Cats 100-q and 120-q recipe.
  → It prints predicted vs measured, and the fitted decay vs 0.861 / 0.940.
  → This is a **report, not a gate**: calibration drift is expected. Figure `dscale/figures/hw_backtest.png` inside the run dir.
- [ ] **AC-6** (D-SCALE.6): one implementation of witnesses and significance serves all families.
  → `code/dscale/witness_scale.py`:
    - `dfe_ghz`: direct fidelity estimation, F = (1/m)·Σ⟨S_k⟩ over m = 40 stabilizers drawn uniformly from the GHZ group. GME iff F − 0.5 > 2σ (Q8).
    - `ghz2`: ⟨X^⊗N⟩ + mean adjacent ⟨ZZ⟩ > 1.
    - `trex_lite`: divide by ∏(1 − p01 − p10) and propagate σ.
    - `echo_fidelity`: return probability after U^t U^{−t}.
    - `pair_negativity`: on pre-registered edges with Bonferroni correction (uses the copied `dscale/tomography.py`).
    - `alive(v, σ, k)`: σ = √(repeat spread² + 1/shots); k = 2 headline, k = 3 reported.
- [ ] **AC-7** (D-SCALE.7): every CLI respects the 20-minute test cap and the first-run sampling caps.
  → `code/dscale/budget.py`: a `Deadline(max_minutes)` checked between jobs and sweep cells.
    - `--max-minutes` defaults to **20**. When it is reached: stop launching work, write all partial results with `truncated: true`, exit 0, and print what was skipped.
    - `--max-minutes 0` (unlimited) is accepted only together with `--full`, which is used only in the runbook.
  → `--shots` defaults to **4000** and `--repeats` to **15**. Values above 4000 / 15 are refused without `--full` (Q9: unlimited later, capped for first runs).

**Circuit families (plug-and-play)**

- [ ] **AC-8** (D-SCALE.8): the family interface, the registry and three budget presets per family exist.
  → `code/dscale/families/__init__.py`:
    - `FAMILIES = {"ghz-spine", "ch-qca", "pmd-bank", "kicked-ising"}`, plus `RECIPES = {"composite"}`;
    - each family exposes `PRESETS = {40: {...}, 100: {...}, 120: {...}}` (Q2: all three versions) and `region_request`, `build(region, params, draw)`, `clifford_twin`, `witness`, `bp_circuits` and `PARAM_GRID`.
  → `python -m dscale.families --list` prints each family's claim level, its witness and the three presets (catalogue in §4).
- [ ] **AC-9** (D-SCALE.9): `ghz-spine`, a certified clonal genealogy built on the survival laws.
  → `code/dscale/families/ghz_spine.py`.
  → Spine:
    - `bfs_tree(N)` with an `H` root and one CX per tree edge in BFS order;
    - `--spines k` adds independent subclone trees.
  → Parity checks (Big Cats): ancilla `a` gets `CX(i→a)` and `CX(j→a)` on a Z_iZ_j stabilizer, is **measured at the end**, and the shot is post-selected on a = 0. The kept fraction is recorded.
  → Soma: leaf qubits with **no gate from the spine**. Each gets `Ry(θ_fate)`, with θ taken from a cited illustrative `type × margin` table of the tile's draw (Q11). Soma Z bits give per-cell fates (claim L0; the classical surrogate is stated).
  → DD (X–X) on spine idle windows in heron mode. It is recorded, and it is inert in the Pauli model (stated).
  → Circuits per job: 2 ghz2 + 40 DFE stabilizers + 1 soma Z.
  → Width ladder N ∈ {6, 12, 24, 36, 48, 64, 92, 112}, capped by the preset.
  → Simulation by mode:
    - ideal = stabilizer;
    - heron = `AerSimulator.from_backend(FakeMarrakesh, method="matrix_product_state")` (bond dimension 2);
    - `pauli:<target>` = AC-4.
  → Claim: L1 (GME) only. It is a stabilizer state with BP χ = 2, so it is **never L2**.
- [ ] **AC-10** (D-SCALE.10): `ch-qca` runs a single-control Goldilocks QCA natively on heavy-hex and on the square lattice.
  → `code/dscale/families/ch_qca.py`. Rule: for every neighbour k, apply CV(k → j) with V = H.
    - Degree-2 sites: **exact T6** (D14).
    - Degree-3/4 sites: the **parity-Goldilocks rule** (activate iff the number of active neighbours is odd), a named new rule (Q7). `--rule v3` (V³ = 1) is sim-only.
  → Circuit structure:
    - bipartite Floquet;
    - edge-colouring layers: 3 colours on heavy-hex, 4 on the square lattice;
    - CH = `Ry(π/4)·CZ·Ry(−π/4)`.
  → Initial condition: centre + k extra sites, k = clip(round(size_mm / 4), 0, 6), with positions from `derive_seed(tile geometry seed, "DS-qca-init")` (Q11).
  → Dial α: V(α) = exp(−iα·n̂·σ) with n̂ = (x+z)/√2. The Clifford twin is CY with the same CZ skeleton.
  → Circuits per job:
    - Z snapshots for t = 0…t_max;
    - 9 bipartite settings at t_w ≤ 3 on pre-registered edges;
    - echoes U^t U^{−t}.
  → After transpiling the 40/100/120 presets on `marrakesh`, `boston` and `nighthawk`, it prints **SWAPs: 0**. This removes RE D-3's 376 SWAPs.
  → Seed regions for imaging (simulable per tile):
    - 21-site two-hexagon patch in ideal mode;
    - 12-site hexagon in heron mode.
- [ ] **AC-11** (D-SCALE.11): `pmd-bank` puts the L1′ gap above the sampling floor using deferred-measurement q-machines.
  → `code/dscale/families/pmd_bank.py`.
  → Re-tune. The process is Φ(n) = Γⁿ(1 − V·sin²(nπ/N)), searched over:
    - V ∈ {0.4, 0.6, 0.8, 0.95}, Γ ∈ {0.5, 0.7, 0.85}, N ∈ {8, 16, 32}, L ∈ {6, 8, 10}.

    It maximises [d_KL(best k-bit classical) − d_KL(quantum)] / floor, where:
    - floor = (2^L − 1)/(2·n·L·ln 2);
    - n = shots × repeats (4,000 × 15 = 60,000 at first-run caps);
    - the classical staircase uses k = 1 … log₂N − 1 (copied `dscale/causal_states.py`).
  → Deferred machine:
    - memory + L fresh outputs along `path(L+1)`;
    - each step is a merged U·SWAP (≤ 3 CZ), so the memory walks along the path;
    - all outputs are measured at the end.
  → Control arm: the copied mid-circuit D-5 builder, declared to the lint.
  → Bank: K = 3 / 8 / 10 machines on disjoint, buffered paths in one job, simulated per machine (crosstalk not modelled, Q13).
  → Pass rule: d_KL(q) < 10⁻², d_KL(q) < every staircase model with fewer than log₂N bits, and gap > 3× floor.
- [ ] **AC-12** (D-SCALE.12): the `kicked-ising` anchor calibrates the predictor and BP against published numbers.
  → `code/dscale/families/kicked_ising.py`: Kim's U(θ_h) on any target graph, starting all-up.
  → Clifford points θ_h ∈ {0, π/2}: stabilizer-exact against the Pauli model at full width.
  → Sweep at 5 / 20 steps: the BP χ-gap |O(χ) − O(2χ)| on heavy-hex (`marrakesh`) vs square (`nighthawk`). This tests "4-cycles hurt BP more"; it stays inferred until measured.

**Hardness, map and orchestration**

- [ ] **AC-13** (D-SCALE.13): a frozen BP copy runs fast enough for 120 q, and every circuit gets a simulability number.
  → `code/dscale/bp.py` is copied from RE `src/bp.py` @ `2609cbe`. `apply_2q` QR-reduces each site tensor before the SVD: (2χ)×(2χ) instead of (2χ^{d−1})×(2χ^{d−1}).
  → Equivalence check: a 12-q hexagon QCA (t = 4) at χ ∈ {2, 4, 8} gives the same observables to 1e-10 in both versions. The RE side runs from the RE folder by CLI or subprocess (read-only use, no import).
  → χ ∈ {2, 4, 8} at ≥ 100 q; {2, 4, 8, 16} at ≤ 40 q. Every cell stays under the AC-7 deadline; a cell that hits it records `bp: timeout`.
  → Reference, best available first:
    1. stabilizer-exact;
    2. light-cone-exact statevector (≤ 25 q);
    3. otherwise χ-convergence only, labelled.
- [ ] **AC-14** (D-SCALE.14): the survive-vs-simulable map.
  → `python -m dscale.survival --budget 40|100|120 --target boston|nighthawk|marrakesh|kingston|helios-class [--families …] [--smoke]` sweeps `PARAM_GRID` (width ladder, cycles t, angle α).
  → Writes `survival_map.json` and the figures `survival_map_<budget>_<target>.png` and `bp_frontier.png`.
  → Cell classes: `dead`, `alive_bp_easy` (BP ≥ 0.99 at some χ ≤ χ_max), `alive_bp_hard` (BP < 0.99 at χ_max, or χ-gap > 0.01). The Goldilocks zone is printed, or printed as "empty".
  → Survival metrics:
    - spine: F_dfe;
    - QCA: echo fidelity, plus negativity wherever full noise is simulable (≤ 24 q);
    - PMD: the AC-11 rule;
    - anchor: magnetisation at the Clifford points.
  → Noisy verdicts above 24 q for non-Clifford circuits are labelled `predicted (Clifford twin, Pauli-twirled <target>)`. AC-4 decides whether they count as `validated`.
  → `--smoke` runs the first cells of each family's grid until the deadline. Full maps belong to the runbook.
- [ ] **AC-15** (D-SCALE.15): one MVP orchestrator adds D-SCALE to any F1/F4 run.
  → `python -m dscale.run --run research_runs/<run> --budget 40|100|120 --mode ideal|heron [--recipe composite|ghz-spine|ch-qca|pmd-bank] [--target marrakesh] [--smoke]`. It reads `cohort_params.json` + `quantum_run.json`, sampler-blind (epic §3).
  → Per tile, it derives seeds with `imaging.seedhash.tile_seeds(run_key, shot_index, generation, raw_bits)`, the same function F5 uses.
  → Writes `research_runs/<run>/dscale/`:
    - `dscale_run.json` (`DScaleRun`, §5);
    - `allocation.json`;
    - `scale_detail.json`;
    - `seed_shapes.npz` (one 3-D uint8 occupancy per `tile_id`, 0.5 mm = `params_lung.json` `lattice_mm`; lifted with the copied `dscale/seedlift.py`);
    - `circuits/*.qasm`;
    - `figures/`.
  → Each family emits its claim into `DScaleRun.claims` with label, value, σ, passed and claim level.
  → It refuses (exit 6) to write into a run directory that contains git-tracked files. `research_runs/` is not ignored, and old runs such as `qalife_aer_20261026-182256` and `grow_aer_*` are committed.
- [ ] **AC-16** (D-SCALE.16): F5's grower starts from the quantum seed shape when one exists.
  → `code/imaging/growth.py`: `grow(..., seed_mask: np.ndarray | None = None)`.
    - When given, the mask is centred on the environment centre, intersected with `~hard & ~soft`, and used instead of `seed_ball`.
    - If the intersection is empty, it falls back to the ball and logs it.
    - `summary["seed_source"]` and `summary["seed_cells"]` are recorded.
  → `code/imaging/frames.py:render_tumor` passes the mask through.
  → `code/imaging/build_tiles.py` loads `<run>/dscale/seed_shapes.npz` when it exists (`--no-dscale` ignores it) and sets the new optional `CohortTile` fields:
    - `seed_source`: `"ball"` or `"dscale:ch-qca:<region>"`;
    - `dscale`: `{family, claim_level, witness_passed}`.

    `tiles.json` gets a top-level `dscale` block copied from `dscale_run.json`.
  → Without `dscale/`, outputs are **byte-identical** to F5 (`seed_ball` path unchanged). Calcified tiles keep the procedural path.
  → `code/imaging/PORTED.md` notes the seed-hook change next to `growth.py`. The PORTED entry "Ø 2 mm ball seed instead of D's seed shape" becomes "ball by default, D-SCALE seed when present".
- [ ] **AC-17** (D-SCALE.17): F3 shows an optional D-SCALE panel.
  → `code/f3_web/build_web.py` + `web_template.html` render a "Quantum growth (D-SCALE)" section when `tiles.json` has a `dscale` block:
    - budget, target, sim label;
    - one row per claim (L1 GME F ± σ, L1′ gap/floor, QCA witness verdict);
    - the Goldilocks-zone verdict;
    - the embedded survival-map PNG;
    - the honest label: "simulated; the seed shape is a quantum snapshot; growth and image are classical; no classical-hardness claim".
  → Tiles show a seed-source badge in the modal.
  → Without a `dscale` block the page is unchanged.
- [ ] **AC-18** (D-SCALE.18): the draw changes the quantum job, and the same inputs reproduce byte-identically.
  → Two F1 runs with different draws give different soma angles, QCA initial sets and transpiled hashes.
  → The same run processed twice gives identical `seed_shapes.npz` and `dscale_run.json`, apart from timestamps. All seeds come from `imaging.seedhash.derive_seed` with `"DS-*"` labels.

**Runbook, hardware pack and docs**

- [ ] **AC-19** (D-SCALE.19): hardware packs and the runbook exist, and nothing submits.
  → `python -m dscale.hw_pack --budget 40|100|120 --backend <name> [--from-map survival_map.json]` writes `research_runs/<run>/dscale/hwpack-<budget>-<backend>/`:
    - `manifest.json`: backend, families, regions, circuits, shots (repeats × (k/w)², capped as in AC-7 unless `--full`), estimated QPU seconds (shots × (duration + 250 µs)), mitigation (DD X–X on certified idles, readout twirling + TREX, gate twirling), and the calibration-gate thresholds to re-check at submit time;
    - `circuits/*.qasm`, transpiled to the matching fake target as a stand-in ISA.
  → `code/dscale/RUNBOOK_DSCALE.md` (Peter only) has two parts:
    - **(A) full simulation sweeps:** survival maps for all three budgets, back-tests and the PMD re-tune at `--full`, with expected runtimes;
    - **(B) hardware:**
      - the pre-saved `QiskitRuntimeService()` account, never a token;
      - re-transpile against the live backend and re-check calibration;
      - a SamplerV2 snippet;
      - order 40 → 100 → 120;
      - label results `hardware: <backend>, job <id>`;
      - where to record them.
  → `grep -rn "SamplerV2\|EstimatorV2\|\.run(" code/dscale/hw_pack.py` finds nothing that submits.
- [ ] **AC-20** (D-SCALE.20): the docs are updated.
  → `code/README.md`: a D-SCALE section (commands, outputs, the smoke cap, the runbook pointer).
  → `code/dscale/PORTED.md`: the copied RE D files with what was kept and what changed.
  → `QuantumPhantoms/README.md`: the D row's MVP column, the MVP features table (D-SCALE), the hardware ranking (§4) and the changelog line (live-document rule).
  → The epic edits for the developer (Q1/Q2) are listed in §9.

---

## 3. Out of Scope (Postponed)

- **Submitting hardware jobs.** There is no code path for it; the runbook part B is Peter's (hard rule, Q3/Q4).
- **Running full sweeps during implementation.** Only `--smoke` runs of ≤ 20 min each; the full maps are runbook part A (Q4/Q6).
- **"Quantum inheritance": a Kretschmer-style unconditional memory separation** (arXiv 2509.07255; 12 q on H1-1; ≥ 62 classical bits provably needed). This is the strongest advantage-type route. It goes to **follow-up D-SCALE-2** (Q10) and is listed in README Future.
- **Dynamic-circuit families at scale** (constant-depth GHZ, teleport routing). They are refuted on Heron r2; F4 and RE D-2 stay as they are.
- **ZNE / PEA / PEC.** Listed as runtime options in the hardware pack only.
- **Crosstalk / spectator-ZZ modelling.** The composite is simulated per region (Q13); buffers are the mitigation.
- **Seed shapes from regions above 24 sites.** Larger regions appear in the map and the hardware packs only; their snapshots need hardware.
- **Changes to F4** (`f4_qalife/`, including the fate-dial flaw) and to the RE tree. The QR speed-up lives in the MVP copy; feeding it back to RE is optional later.
- **Editing the epic.** The developer adds the row and amends §6 (§9 lists the text).
- **Any L2 claim.** "Classically impossible" / "quantum-only" wording stays forbidden; the map is the deliverable.

---

## 4. Technical Decisions

**Circuit catalogue: the three versions per family** (preset defaults; the allocator fits them to the pruned graph):

| Family | Circuit | Survival laws used | Witness → claim | Hardness | 40 q | 100 q | 120 q |
|---|---|---|---|---|---|---|---|
| `ghz-spine` | BFS GHZ tree, H root, 1 CX per edge, end-measured parity checks, separable draw-driven soma | unitary; terminal readout; equator founder; 1 CX per certified qubit; germ/soma split; DD | DFE F > 0.5 (GME) + ghz2 → **L1** | stabilizer, BP χ = 2: none | spine 30 + 2 checks + 8 soma | spine 84 + 8 checks + 8 soma (Big Cats scale) | spine 112 + 8 checks on 156-q Heron; on Nighthawk 108 + 8 + 4 |
| `ch-qca` | single-control Goldilocks QCA, bipartite Floquet, edge-colour CZ layers, draw-driven start, echo + 9-setting tomography | native edges only (0 SWAPs); shallow witness depth; terminal readout; pre-registered edges | Bonferroni negativity → **L1** (≤ 24 q in noisy sim, hardware above) | non-Clifford; depth + angle + short loops: **the frontier family** | 40-site heavy-hex patch / 5×8 square | 100-site patch | full 10×12 Nighthawk: **headline frontier run** |
| `pmd-bank` | K deferred 1-memory q-machines, memory walks by merged U·SWAP | no reset or mid-circuit readout; short paths; isolated machines | gap > 3× floor vs classical staircase → **L1′** | 2-q blocks, never L2 | K = 3 | K = 8 | K = 10 |
| `kicked-ising` | Kim Floquet RZZ(π/2) + RX(θ_h) on the full graph | native edges; Clifford checkpoints | magnetisation at Clifford points (calibration) | known BP territory; heavy-hex vs square | 40 | 100 | 120 (nighthawk) |
| composite | spine + QCA + PMD in one circuit with buffers | all of the above | three claims under one job id | — | spine 14 + 2, QCA 12, PMD 1 | spine 48 + 4, QCA 30, PMD 1 | Nighthawk: rows 0–3 spine, row 4 buffer, rows 5–9 QCA |

**Expected outcome per budget** (the map confirms or refutes each line):
- **40.** L1 GME on the spine and L1′ above the floor are realistic. The QCA witness should be alive only at t ≤ ~3. Everything at this budget is classically simulable.
- **100.** L1 at Big-Cats scale is realistic. The spine is still a stabilizer state, so no hardness.
- **120.** The only credible alive ∩ BP-hard candidate: `ch-qca` on the square lattice at mid angle and few cycles. It is likely narrow or empty.

**Hardware ranking** (web survey 2026-10-31; "(unverified)" = secondary sources only; for the runbook):

| Budget | Sim proxy | 1st choice (real) | Alternatives | Access for a student | Why |
|---|---|---|---|---|---|
| 40 | `boston`, `nighthawk` 5×8 | Heron r3: ibm_boston (2q ≈ 2.15e-3 over 100 q), or **ibm_aachen (EU; Heron r3 since 2026-03)** (unverified) | Quantinuum Helios 98 q (2q 99.921 %, best physics, institutional access only); IQM Emerald 54 q (EU, Braket, $0.0016/shot, lower fidelity); Nighthawk r2 ibm_phoenix | IBM Open Plan 10 min/month (kingston open since 2026-05, unverified); IBM Quantum Credits via supervisor; EuroHPC Quantum Access Pilot (≤ 54 q, cut-offs 1 Nov / 1 Dec 2026, via supervisor) | GHZ scale proven on Heron; slack for pruning |
| 100 | `boston`, `kingston` | Heron r3 (boston / pittsburgh / aachen) | Nighthawk r1/r2; Helios (≤ 98 q, if access) | PAYG $96/min, Flex $72/min, or Credits | Big Cats: 100-q GHZ F = 0.55–0.70 on Heron |
| 120 | `nighthawk` (square), `marrakesh` (spine) | **Nighthawk r2 ibm_phoenix** for `ch-qca` (5,000-gate budget, CZ ≈ 1.9e-3, readout ≈ 8e-3); **Heron r3** for `ghz-spine` (156 q leaves slack) | Nighthawk r1 ibm_berlin (EU, Premium/Flex early access) | Premium/Flex today; Open Plan access to Nighthawk unclear (unverified) | only the square lattice gives 4-loops natively; 120-q GHZ is certified only on Heron |
| — | not recommended | Google Willow (no access), IonQ Tempo (no public 100-q cloud), Rigetti Cepheus 108 q (2q 99.1 %, too low), neutral atoms (no student-accessible gate model with mid-circuit measurement) | | | |

| Component | Choice / Implementation |
|---|---|
| Package | `code/dscale/` (new), run as `python -m dscale.<module>` from `code/`. Subpackage `dscale/families/`. |
| Frozen copies (PORTED.md) | From RE D @ `2609cbe`: `src/bp.py` → `dscale/bp.py` (+ QR reduction); `src/witness.py` → `dscale/tomography.py`; `src/causal_states.py` → `dscale/causal_states.py`; `src/seed_shape.py` `lift` + `src/heavyhex.py` layout/axis helpers → `dscale/seedlift.py` (generalised to any planar graph); the mid-circuit q-machine builder from `src/memory_advantage.py` → control arm in `pmd_bank.py`. |
| Seeds | `imaging.seedhash` (`derive_seed`, `rng`, `tile_seeds`), MVP-internal. Every simulator/transpile seed and hidden choice uses a `"DS-*"` label. |
| Simulation modes | `ideal` (stabilizer / statevector ≤ 28 q / MPS); `heron` (`AerSimulator.from_backend(FakeMarrakesh)`, MPS for spines); `pauli:<target>` (AC-4); `twin:<target>`. |
| Labels | `simulated: ideal`, `simulated: Heron-class noise (FakeMarrakesh)`, `simulated: Pauli-twirled <Target> noise (stabilizer)`, `predicted (Clifford twin, Pauli-twirled <Target>)`. The MVP has no schema enum, so no contract change requests are needed. |
| Caps | `--max-minutes 20` default (Q6); `--shots 4000`, `--repeats 15` defaults and caps (Q9); `--full` lifts them (runbook only). |
| Witnesses | DFE (m = 40) + ghz2; Bonferroni negativity + echo; d_KL staircase; k = 2 headline, k = 3 reported (Q8). |
| Readout correction | TREX-lite. No M3 (not installed); populations stay raw. |
| BP | Frozen copy + QR reduction; χ ≤ 8 at ≥ 100 q, ≤ 16 at ≤ 40 q; deadline-bounded. |
| QCA rule on degree > 2 | Parity-Goldilocks, a named new rule (Q7); `--rule v3` sim-only. |
| Imaging hook | Optional `seed_mask` in `growth.grow`; ball stays the default; byte-identical without `dscale/`. |
| Figures | matplotlib PNGs in `research_runs/<run>/dscale/figures/`, with the sim label in each title. |

**Conventions & Notes:**
*   Adopt epic §3 verbatim. The `Sampler` seam is unchanged: D-SCALE is a post-roll stage that F2/F5 consume as an **optional file**, so imaging stays sampler-blind. Params stay quantum and the image classical, and the page says so.
*   **Survival laws are code.** `lint.py` runs on every circuit (AC-3).
*   **Entanglement ≠ hardness.** README and page keep "survives (L1/L1′)" and "BP-hard (frontier)" in separate columns. GHZ and PMD never appear in the frontier column.
*   **No look-elsewhere.** `PARAM_GRID` (edges, angles, depths) is fixed and hashed into `scale_detail.json` before any run.
*   **Scope change (Q2).** Deep coherent genealogy (epic §6 "Mode B out of scope") is **in scope** for `ghz-spine`, on the evidence of PJ0 W50 and Big Cats 100/120 q. Every family ships all three budget versions.

---

## 5. Data Model (Additions/Modifications)

No database. JSON + NPZ files in the run directory, plus dataclasses in `code/common/datamodel.py`.

```text
[New Entity — code/common/datamodel.py]
DScaleRun                                   # research_runs/<run>/dscale/dscale_run.json
  budget          int                       40 | 100 | 120
  target          str                       marrakesh | kingston | boston | nighthawk | helios-class
  mode            str                       ideal | heron | pauli:<t> | twin:<t>
  sim_label       str
  recipe          str                       composite | ghz-spine | ch-qca | pmd-bank | kicked-ising
  claims          list[dict]                [{family, claim_level, witness, value, sigma, k, passed, label}]
  goldilocks      dict                      {cells: [...], empty: bool, ref_kinds: [...]}
  seed_shapes     str                       "seed_shapes.npz" (keys = tile_id) | ""
  allocation_ref  str                       "allocation.json"
  param_grid_sha256 str
  shots           int                       default 4000
  repeats         int                       default 15 (cap)
  truncated       bool                      deadline hit (20-min cap)
  run_key         str                       same run key F5 uses for tile_seeds

[Existing Entity — Modifying] CohortTile   (optional fields, omitted when unset, like the F5 fields)
  seed_source     str                       "ball" | "dscale:ch-qca:<region>"
  dscale          dict                      {family, claim_level, witness_passed}
  # _F5_OPTIONAL gains these two names, so old tiles serialise unchanged

[Existing file — Modifying] tiles.json
  dscale          dict (optional)           copy of dscale_run.json for the F3 panel

[New files — research_runs/<run>/dscale/]
allocation.json        target, budget, calibration_snapshot, pruned{qubits, edges, thresholds},
                       regions{name: {family, qubits, edges, role: certified|active|soma|check|buffer}},
                       min_region_distance (>= 2), lint[{rule, ok, detail}]
scale_detail.json      per family: ghz_spine{N, depth, n_checks, kept_fraction, F_dfe, F_sigma, ghz2, gme},
                       ch_qca{sites, rule, alpha, t_w, swaps, negativity_edges[{i, j, N, sigma, p_bonf}], echo[{t, F, sigma}]},
                       pmd_bank{process{V, Gamma, N, L}, floor, machines[{k, d_kl_q, d_kl_classical{k_bits: v}, gap_over_floor, passed}]},
                       references[{circuit_sha256, kind: stabilizer-exact|light-cone-exact|chi-convergence, value}]
survival_map.json      cells[{family, n_qubits, depth_or_t, alpha, sim_label, metric, value, sigma, k, alive,
                       bp{chi_max, fidelity_vs_ref, ref_kind, chi_gap}, regime, validated}], goldilocks_zone[idx], truncated
noise_validation.json  pauli_vs_full[...], twin_vs_real[...], backtest[{source, n, measured, predicted}]
seed_shapes.npz        {tile_id: uint8 3-D occupancy at 0.5 mm}
circuits/*.qasm        OpenQASM 3 of every circuit run (sha256 in scale_detail)
hwpack-<budget>-<backend>/manifest.json + circuits/*.qasm
figures/*.png
```

Migration: none. Old runs and old `tiles.json` load unchanged (`CohortTile.from_dict` ignores unknown keys; new fields default to `None` / `{}`).

---

## 6. File Plan (Concrete Changes)

All paths relative to `QuantumPhantoms/`.

| Action | Path | Change / Note |
|--------|------|---------------|
| New | `code/dscale/__init__.py` | Package marker. |
| New | `code/dscale/PORTED.md` | Copied RE D files @ `2609cbe`: what was kept and what changed (mirror `code/imaging/PORTED.md`). |
| New | `code/dscale/budget.py` | `Deadline`, the shot/repeat caps, `--full` gate (AC-7). |
| New | `code/dscale/targets.py` | Target registry + `--show` (AC-1). |
| New | `code/dscale/allocate.py` | Pruning, `path`, `bfs_tree`, `patch`, `composite`, `allocation.json` (AC-2). |
| New | `code/dscale/lint.py` | Seven survival lints (AC-3). |
| New | `code/dscale/pauli_noise.py` | Pauli-twirled model, delay → Pauli pass, stabilizer runner, `clifford_twin` (AC-4). |
| New | `code/dscale/validate_noise.py` | `--pauli`, `--backtest` (AC-4, AC-5). |
| New | `code/dscale/witness_scale.py` | DFE, ghz2, TREX-lite, echo, Bonferroni negativity, k·σ (AC-6). |
| New | `code/dscale/tomography.py` | Frozen copy of RE `src/witness.py` (seeds via `imaging.seedhash`). |
| New | `code/dscale/causal_states.py` | Frozen copy of RE `src/causal_states.py`. |
| New | `code/dscale/seedlift.py` | Frozen copy of RE `seed_shape.lift` + layout/axis helpers, generalised to square and heavy-hex graphs. |
| New | `code/dscale/bp.py` | Frozen copy of RE `src/bp.py` + QR-reduced `apply_2q`; run-dir report writer dropped (AC-13). |
| New | `code/dscale/families/__init__.py` | Interface, registry, `PRESETS` 40/100/120, `--list` (AC-8). |
| New | `code/dscale/families/ghz_spine.py` | AC-9. |
| New | `code/dscale/families/ch_qca.py` | AC-10. |
| New | `code/dscale/families/pmd_bank.py` | AC-11 (includes the copied mid-circuit control-arm builder). |
| New | `code/dscale/families/kicked_ising.py` | AC-12. |
| New | `code/dscale/survival.py` | Sweep, BP calls, classification, map + figures (AC-13, AC-14). |
| New | `code/dscale/run.py` | MVP orchestrator over an F1/F4 run (AC-15, AC-18). |
| New | `code/dscale/hw_pack.py` | Hardware pack builder; no submission (AC-19). |
| New | `code/dscale/RUNBOOK_DSCALE.md` | Part A full sim sweeps; part B hardware, Peter only (AC-19). |
| Modify | `code/common/datamodel.py` | `DScaleRun`; `CohortTile.seed_source`, `CohortTile.dscale`; extend `_F5_OPTIONAL` (§5). |
| Modify | `code/imaging/growth.py` | `grow(..., seed_mask=None)`; summary `seed_source`, `seed_cells` (AC-16). |
| Modify | `code/imaging/frames.py` | `render_tumor(..., seed_mask=None)` pass-through (AC-16). |
| Modify | `code/imaging/build_tiles.py` | Load `dscale/seed_shapes.npz`, `--no-dscale`, new tile fields, `tiles.json` `dscale` block (AC-16). |
| Modify | `code/imaging/PORTED.md` | Note the seed hook on `growth.py` (AC-16). |
| Modify | `code/f3_web/build_web.py` | Embed the `dscale` block + survival-map PNG (AC-17). |
| Modify | `code/f3_web/web_template.html` | Optional "Quantum growth (D-SCALE)" section + modal seed badge (AC-17). |
| Modify | `code/README.md` | D-SCALE section and layout entry (AC-20). |
| Modify | `README.md` | Progress (D row, MVP features), hardware ranking, changelog (AC-20). |
| Modify | `plans/feature-D-SCALE-decoherence-surviving-circuits.md` | Tick ACs, §9 notes. |

---

## 7. Manual Verification (No Tests)

Run from `code/`. Each step is a smoke run that the AC-7 deadline stops at 20 min or less.

- [ ] **Setup:** run `python -m f1_quantum.run --backend aer --tiles 12 --pairs 2`. Expected: a new untracked `research_runs/qrng_aer_<ts>/`.
- [ ] **Verify AC-1:** run `python -m dscale.targets --show`. Expected: 5 targets; Nighthawk 120 / 218 / {2: 4, 3: 36, 4: 80}; Boston 2q ≈ 0.0013.
- [ ] **Verify AC-2:** run `python -m dscale.allocate --target nighthawk --budget 120 --recipe composite`. Expected: regions with min distance ≥ 2, the pruned list and an allocation figure. Then request an oversized spine. Expected: exit 4 with the largest feasible size.
- [ ] **Verify AC-3:** run `python -m dscale.lint --selftest`. Expected: an injected mid-circuit measure and an injected spine→soma gate give 2 violations and exit 5; the clean build prints all 7 rules `ok`.
- [ ] **Verify AC-4:** run `python -m dscale.validate_noise --pauli --smoke`. Expected: a Δ table within max(0.03, 2σ), or an explicit `unvalidated` flag, plus the twin-vs-real class match.
- [ ] **Verify AC-5:** run `python -m dscale.validate_noise --backtest --smoke`. Expected: predicted vs measured for QALife, PJ0 and Big Cats (as many points as fit in 20 min), the fitted decay, and the figure.
- [ ] **Verify AC-6:** run ghz-spine N = 12 ideal. Expected: F_dfe ≈ 1.000 and ghz2 ≈ 2.000. Then run it Pauli-noisy with TREX-lite on. Expected: the corrected value moves toward ideal and σ grows.
- [ ] **Verify AC-7:** run any CLI with `--max-minutes 1` on a big grid. Expected: it stops near 1 min with `truncated: true`. `--shots 10000` without `--full` is refused.
- [ ] **Verify AC-8:** run `python -m dscale.families --list`. Expected: 4 families plus the composite, each with its 40/100/120 presets.
- [ ] **Verify AC-9:** run `python -m dscale.families.ghz_spine --budget 40 --target marrakesh --mode heron --smoke`. Expected: depth ≈ tree depth, the kept fraction, F_dfe ± σ and a GME verdict. Then run `--budget 120 --mode pauli:boston --smoke`. Expected: ladder points up to the deadline.
- [ ] **Verify AC-10:** run `python -m dscale.families.ch_qca --budget 40|100|120 --target boston|nighthawk --print-swaps`. Expected: `SWAPs: 0` for all of them. Then run the 21-site ideal circuit. Expected: Bonferroni negativity on the pre-registered edges and a seed occupancy.
- [ ] **Verify AC-11:** run `python -m dscale.families.pmd_bank --retune --smoke`. Expected: the chosen (V, Γ, N, L), gap/floor ≥ 3 and the staircase. Then run `--budget 40 --mode heron --smoke`. Expected: d_KL and `passed` per machine, next to the mid-circuit control arm.
- [ ] **Verify AC-12:** run `python -m dscale.families.kicked_ising --theta 0 pi/2 --steps 5 --target marrakesh nighthawk --smoke`. Expected: the Clifford-point exact vs Pauli comparison and the BP χ-gap on heavy-hex vs square.
- [ ] **Verify AC-13:** run the 12-q hexagon BP equivalence: the MVP copy vs the RE CLI (run from the RE folder). Expected: identical to 1e-10 at χ ∈ {2, 4, 8}, and the copy faster.
- [ ] **Verify AC-14:** run `python -m dscale.survival --budget 120 --target nighthawk --smoke`. Expected: a partial `survival_map.json` with classified cells, the Goldilocks verdict (or "empty") and figures. Repeat for 40 / 100 on `boston`.
- [ ] **Verify AC-15:** run `python -m dscale.run --run ../research_runs/<new run> --budget 40 --mode ideal --smoke`. Expected: `dscale/` contains `dscale_run.json`, `allocation.json`, `scale_detail.json`, `seed_shapes.npz` with 12 keys, circuits and figures. Pointing it at `research_runs/qalife_aer_20261026-182256` (tracked) exits 6.
- [ ] **Verify AC-16:** run `python -m imaging.build_tiles --run ../research_runs/<new run>`, which takes about 4–11 min. Expected: grown tiles carry `seed_source: dscale:ch-qca:…`, and `diag` shows `seed_cells`. Then run with `--no-dscale` on a copy. Expected: PNGs byte-identical to a plain F5 render (sha256 equal).
- [ ] **Verify AC-17:** run `python -m f3_web.build_web --run ../research_runs/<new run>` and open `web/index.html`. Expected: the D-SCALE panel (claims, map, honest label) and the seed badge in the modal. Then build from an older run without `dscale`. Expected: the page is unchanged.
- [ ] **Verify AC-18:** run `dscale.run` twice on the same run. Expected: equal sha256 for `seed_shapes.npz` and for `dscale_run.json` minus timestamps. Then run it on a second F1 run (different draw). Expected: different QCA initial sets and transpiled hashes.
- [ ] **Verify AC-19:** run `python -m dscale.hw_pack --budget 40 --backend ibm_boston --from-map …`. Expected: the manifest, the QASM files and a QPU-seconds estimate; `grep` finds no submission call. `RUNBOOK_DSCALE.md` has parts A and B.
- [ ] **Verify AC-20:** both READMEs carry the D-SCALE sections, and `code/dscale/PORTED.md` lists every copied file. `git status` shows no change under `plans/relatedPapers/reverse-engineering/`.
- [ ] **Edge cases:**
  - A calcified tile keeps the procedural path and `seed_source` stays unset.
  - A seed mask that falls entirely outside the lung at a site falls back to the ball and is logged.
  - A budget whose map finds no alive non-Clifford cell gets the page text "Goldilocks zone empty", with no wording that implies advantage.

---

## 8. Open Questions

- [x] **Q1: Feature ID and the epic row.** *Resolved (developer):* yes, `D-SCALE`. The developer adds the epic row (suggested text in §9).
- [x] **Q2: Coherent genealogy and the size limits.** *Resolved (developer):* "make all 3 versions; this is not out of scope, change scope". Every family and the composite ship 40 / 100 / 120 presets. Deep coherent genealogy (`ghz-spine`) is in scope; the epic §6 line is amended by the developer (§9).
- [x] **Q3: Hardware.** *Resolved (developer, with Q4):* never run anything on hardware. A runbook only; no submission code.
- [x] **Q4: Simulation targets.** *Resolved (developer):* yes: `marrakesh`, `kingston`, `boston`, `nighthawk`, `helios-class`. "You never run anything but create run book" is read as: the implementer runs only `--smoke` checks (Q6 cap), never full sweeps or hardware; the full runs are in `RUNBOOK_DSCALE.md` parts A and B.
- [x] **Q5: New installs.** *Resolved (developer):* none.
- [x] **Q6: Run-time limit.** *Resolved (developer):* nothing runs more than 20 minutes during testing. Enforced by `Deadline` (AC-7); BP χ caps as proposed.
- [x] **Q7: QCA rule on degree-3/4 sites.** *Resolved (developer):* parity-Goldilocks, a named new rule; `--rule v3` optional.
- [x] **Q8: Thresholds.** *Resolved (developer):* k = 2 headline, k = 3 reported; GME iff F − 0.5 > 2σ; Bonferroni p < 0.05; echo alive above the random band by 2σ.
- [x] **Q9: Shots.** *Resolved (developer):* unlimited later. For first runs: 4,000 shots and at most 15 repeats per result (AC-7 defaults and caps).
- [x] **Q10: Quantum inheritance (Kretschmer-style).** *Resolved (developer):* follow-up D-SCALE-2.
- [x] **Q11: Draw → circuit mapping.** *Resolved (developer):* soma θ_fate from the `type × margin` table; QCA extra sites k = clip(round(size_mm / 4), 0, 6) at seed-chosen positions; spine width from the budget; PMD process from the re-tune. None of this is fitted biology.
- [x] **Q12: Integration.** *Resolved (developer):* implement in the **MVP structure and code**, on top of F5. The package is `code/dscale/`; RE D pieces are copied frozen (PORTED.md); the imaging seed hook and the F3 panel are added.
- [x] **Q13: Composite simulation.** *Resolved (developer):* per region; crosstalk is not modelled (stated).
- [x] **Q14: Where to implement.** *Resolved (developer):* `main`. F5 is also uncommitted on `main`; no commit unless Peter asks.

---

## 9. Post-Implementation Notes

**Epic edits for the developer (not made by this plan):**
- §2 new row: `| D-SCALE | Quantum growth at scale | 40/100/120-q decoherence-surviving families + survive-vs-simulable map + quantum seed shapes for F5 + hardware runbook | open | Builds on F5. code/dscale/; ghz-spine (L1 GME), ch-qca (frontier, seeds the F5 grower), pmd-bank (L1′), kicked-ising anchor; Pauli-twirled 120-q simulation; Goldilocks-zone map; runbook only, no QPU jobs. Plan: feature-D-SCALE-decoherence-surviving-circuits.md. |`
- §6 "Coherence budget": replace "deep coherent genealogy (Mode B) is out of scope" with "deep coherent genealogy is in scope for D-SCALE `ghz-spine` (unitary, terminal readout; evidence PJ0 W50, IBM Big Cats 100/120 q)".
- §7: `F5 ─► D-SCALE (seed shapes into imaging, panel into F3)`.

[Implementation notes filled after implementation.]
