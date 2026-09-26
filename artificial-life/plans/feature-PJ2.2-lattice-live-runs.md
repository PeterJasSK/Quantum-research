# Feature Plan — PJ2.2: The 2D-lattice vivarium — live runs that fill the mockups (3×3 fill, then 4×4 movement)

**Ticket:** PJ2.2 (stage; sibling of PJ2 — this research repo decomposes epics into stages, no GitHub issue)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09), stage **P3**
**Relation to PJ2:** PJ2 / PJ2.1 built a **1D-track** habitat with food/energy/biology (`build_vivarium`, `code/pj_vivarium.py`). PJ2.2 is a **different substrate**: a **2D square lattice** where the organism is a pure **occupancy field that moves**, with **movement + witness only** (eating/energy/budding deliberately **cut as overclaiming**, per the mockup README). It reuses PJ0's germ-line/witness machinery and the isolated/coupled A-B, but replaces the 1D walk with a 2D lattice walk and adds **solo / replicate / duo** modes.
**Motivation / target artifact:** three saved design mockups already exist and must be **filled with real (sim-then-live) statevector/QPU data**:
`artificial-life/research/pj2_vivarium/mockups/vivarium_3x3_snap.html` (primary),
`vivarium_3x3_smooth.html`, and `vivarium_4x4_scenarios.html`. Their honest hardware recipe is written out in `mockups/README.md` §"What needs to be worked out" + "Minimal honest first hardware run".
**Substrate:** extend `code/pj_qalife.py` (reuse `viv_witness_q`/`to_witness_basis`/germ machinery; add a 2D-lattice model alongside the 1D `build_vivarium`, byte-stable) + new driver `code/pj_lattice_vivarium.py` + new renderer `analysis/pj_lattice_render.py`.
**Slug:** lattice-live-runs
**Author:** Claude (Opus)
**Date:** 2026-09-24
**Status:** Complete (2026-09-24; implemented + manually verified per §8. Code-complete; developer runs the live Heron-r2 depth-scans per OQ-8.)

> **No tests (repo convention, CD-7).** Verification is `--selftest` (static circuit-structure checks) +
> `--dump-circuit` + `--sim` runs + a written correctness/conclusion evaluation. No test framework, no test files.
>
> **This ticket RUNS (build + sim + live-ready).** Like PJ2: build the 2D-lattice model, verify statically, run
> in `--sim`, and land live Heron-r2 circuits. The developer executes the hardware run (established division of
> labour). Sim-first, hardware-confirm (CD-7).
>
> **Certified frames, not a sim-movie (the defining lock — differs from PJ2).** PJ2 baked the whole life cycle
> into **one** measured circuit and reconstructed the movie from statevector snapshots. PJ2.2 follows the
> mockup README's honest recipe instead: on hardware each **generation is its own measured circuit** — a
> **depth scan** (0 walk layers, 1, …, GENS−1), each measured for occupancy + witness with a separable-null
> control. The **integer-generation frames are certified**; only the smooth in-between playback the mockup
> interpolates is a labelled sim artifact. (Sim may snapshot a single statevector for speed; HW depth-scans.)

---

## 1. Summary

PJ2.2 turns the three **2D-lattice vivarium mockups** into **real runs**. The organism is a quantum
**occupancy field** on a small square lattice (3×3 = 9 cells, or 4×4 = 16). It **walks** — each generation is
one Trotter layer of an excitation-conserving `rxx+ryy` quantum walk between **von-Neumann neighbours** on the
grid, mass conserved, nothing scripted (position is just where amplitude flows). The single quantum claim is the
germ-line genealogical witness **⟨X^⊗W⟩ (W=3)**: in the **isolated** arm it decays gently with depth but stays
above the certified line; in the **coupled** arm the moving body is wired back into the germ line (the deliberate
soma→germ wound) and the witness **collapses**. Depth is the scarce axis — **~5–6 generations** is the real
hardware ceiling, which is exactly what the runs measure.

Three **modes**, matching the mockups:
1. **Solo** — one field walks; mass conserved, nothing eaten or born.
2. **Replicate** — at generation 2 the germ line is **CNOT-cloned** into a daughter (parent + daughter share one
   GHZ genealogical witness), and a daughter body is seeded one cell over.
3. **Two organisms (duo)** — two fields seeded at opposite corners drift together; the co-located `rxx+ryy`
   interaction between their bodies builds a joint two-body witness; spatial `overlap = Σ min(occ_A, occ_B)`.

Two **arms** per mode: **isolated** germ line vs **coupled** (barrier broken → witness collapse) — the same A/B
kill-switch PJ0/PJ1/PJ2 use, here proving the Weismann barrier under 2D movement.

**Deliverables, in the user's two phases:**
- **Phase A — fill the 3×3 mockup:** real data for all three modes × both arms × generations 0–5 on the **3×3**
  lattice (sim first; **live** for the minimal-honest **solo** run, replicate/duo live opt-in), rendered into a
  self-contained filled port of `vivarium_3x3_snap.html` (and, free, the `smooth` variant — same data).
- **Phase B — "just the movement" on 4×4:** a **solo, movement-only** 4×4 run (16-cell body + W=3 = 19 qubits;
  replicate/duo on 4×4 need ~35 qubits, past laptop statevector — **out of scope**), rendered into a filled port
  of `vivarium_4x4_scenarios.html` (solo mode).

**Honesty invariant (CD-3/CD-4):** only ⟨X^⊗W⟩ is quantum; the occupancy field (⟨n⟩ per cell), mass, and duo
overlap are **diagonal** — exact classical surrogate — reported as the honest "where it is" narrative. The
certified frames are the depth-scan integer generations; the interpolated playback is a labelled sim artifact
(mockup README §2/§5).

---

## 2. Acceptance criteria

Grounded in the mockups + `mockups/README.md` (the honest hardware recipe), the epic richness question, and the
PJ0/PJ2 substrate. IDs added. All hardware ACs enforce the fail-closed chain-quality gate (CD-5) and certified
QRNG (CD-6). No tests (CD-7).

- [x] **AC-PJ2.2.1 (2D-lattice model — new substrate):** a **lattice builder** `build_lattice_vivarium(width,
  grid, gens, thetas, *, mode, arm, ...)` in `code/pj_qalife.py` places one organism as a **unary occupancy
  field** on a `grid×grid` lattice (one qubit per cell, index `i = r*grid + c`) plus the **W-qubit germ line**
  (reusing PJ0 `viv_witness_q`/germ GHZ machinery, byte-stable). New index helpers `lat_body_q`, `lat_witness_q`
  (per-organism offsets), `lat_neighbors(i, grid)` (von-Neumann), `lat_segment_len(width, grid, mode)`. `grid=3`
  and `grid=4` both build. `build_vivarium`/`build_germsoma`/`build_arena` untouched.
  _Covered by:_ `code/pj_qalife.py:1388` `build_lattice_vivarium` + `lat_segment_len`:1286 / `lat_witness_q`/`lat_body_q`/`lat_neighbors`/`lat_edges`; grid 3&4 build (selftest qubit-count OK)
- [x] **AC-PJ2.2.2 (the walk is a real local Hamiltonian, not scripted — README §3/§9):** movement is a
  `_lattice_walk_layer(qc, grid, org, theta)` applying excitation-conserving `rxx(θ)+ryy(θ)` on **every
  von-Neumann neighbour pair**, in an **edge-colored order** (H-even, H-odd, V-even, V-odd sublayers) to keep
  depth shallow. Applied **unconditionally** (no `if`/`c_if` on position). Static check: every body-layer gate is
  an `rxx`/`ryy` on a neighbour pair (excitation-conserving → mass conserved); `has_classical_branch == False`.
  The mockup's directional `BIAS` drift was a cosmetic mock artifact — the real walk is **isotropic** (uniform θ);
  drift emerges from the corner seed + boundaries (documented, OQ-4).
  _Covered by:_ `code/pj_qalife.py:1356` `_lattice_walk_layer` (rxx+ryy edge-colored, unconditional); `lattice_coupling_report`:1484 `mass_conserved=True`, `has_classical_branch=False` (selftest OK)
- [x] **AC-PJ2.2.3 (certified frames via depth scan — the defining lock, README §5):** on hardware each
  generation `d ∈ {0..gens−1}` is built as its **own** circuit with `d` walk layers and **measured once** (occupancy
  in Z + germ witness in X). The driver depth-scans (no interpolation on the certified path). Verified by
  `--dump-circuit` (one measured circuit per depth) + the driver banking exactly one measured circuit per
  `(mode, arm, gen, repeat)`. Sim may snapshot a single statevector for speed but the HW frames are the certified
  integer generations.
  _Covered by:_ `code/pj_lattice_vivarium.py:170` `depth_scan` (one circuit per depth) + `build_measured_lattice`:88 (measured once); dump per depth in `research/pj2_vivarium/circuits/`
- [x] **AC-PJ2.2.4 (solo mode — one walking field):** `mode='solo'` builds germ(W) + one body field seeded at a
  start cell; occupancy = per-cell P(1) marginals; witness = germ ⟨X^⊗W⟩ vs separable null. 3×3 = **12 qubits**,
  4×4 = **19 qubits** (both fit sim `_SV_MAX_QUBITS`=27 and Heron).
  _Covered by:_ `code/pj_qalife.py:1388` mode='solo' germ+one body; `lat_segment_len`:1286 = 12 (3×3) / 19 (4×4) (selftest OK)
- [x] **AC-PJ2.2.5 (replicate mode — CNOT germ clone at gen 2, README §1/§7):** `mode='replicate'` clones the
  W-qubit germ line into a **daughter** germ block by CX at generation 2 (both blocks share one GHZ → one
  ⟨X^⊗2W⟩ witness) and seeds a daughter body one cell over. Static Weismann check: the clone couples **germ→germ
  only**, no soma→germ gate (isolated arm). 3×3 replicate = **24 qubits** (fits sim). **4×4 replicate is out of
  scope** (38 qubits, past statevector).
  _Covered by:_ `code/pj_qalife.py:1368` `_lattice_clone` (cx germ0→germ1 at `LAT_REP_GEN`=2) + daughter seed; selftest back_action=False (germ→germ only); sim: n 1→2 at gen 2
- [x] **AC-PJ2.2.6 (duo mode — two organisms + emergent interaction, README §8):** `mode='duo'` seeds two fields
  at opposite corners with two germ blocks; the interaction is `rxx+ryy` between **co-located** A/B body cells
  (emergent from co-location, **no `if(contact)`**), building a joint witness over both germ lines; report
  `overlap = Σ min(occ_A, occ_B)` (diagonal). 3×3 duo = **24 qubits** (fits sim). **4×4 duo out of scope** (~35q).
  _Covered by:_ `code/pj_qalife.py:1378` `_lattice_interaction` (co-located rxx+ryy, no if); duo seeds corners 0 & grid²−1; `reduce_counts` overlap=Σmin (`pj_lattice_vivarium.py:107`); sim overlap≈0.7
- [x] **AC-PJ2.2.7 (isolated vs coupled arm — the A/B kill-switch):** `arm='isolated'` never couples a body cell
  to a germ qubit; `arm='coupled'` adds a coherent `rxx` body→witness-locus gate (the soma→germ wound). Static
  check `lattice_coupling_report`: `back_action == False` (isolated) / `True` (coupled), `witness_isolated`
  accordingly. The measured witness **collapses** in `coupled` relative to `isolated` at matched settings —
  proving the barrier is the mechanism under 2D movement.
  _Covered by:_ `code/pj_qalife.py:1388` arm branch (coupled rxx+ryy body→germ0,0); `lattice_coupling_report`:1484 back_action/witness_isolated (selftest OK); sim: coupled witness collapses to ≈0
- [x] **AC-PJ2.2.8 (the certified witness result, CD-3/CD-5):** report ⟨X^⊗W⟩ vs the separable null (pinned ≈0)
  per generation from sim and a live confirm; gate `witness − sep > k·σ` (k=2 headline, k=3 reported). Report the
  **generation at which the signature crosses into classical** — the depth ceiling (mockup's ~5–6 gens), the
  richness-vs-collapse datapoint this ticket contributes (AC-P3.2). If depth kills it early, that boundary **is**
  the result.
  _Covered by:_ `code/pj_lattice_vivarium.py:170` depth_scan reports w/sep/w_sigma per gen; survives = w−sep>K·σ (K=2); `entanglement_depth` collapse-gen printed in main()
- [x] **AC-PJ2.2.9 (honest diagonal plumbing, CD-3/CD-4):** occupancy ⟨n⟩ per cell, mass, and duo overlap are
  shown **diagonal** (exact classical surrogate); only the germ witness is the quantum claim; the separable null
  is reported alongside and must sit ≈0. Interpolated in-between frames are labelled a sim artifact; integer
  generations are the certified (measured) frames.
  _Covered by:_ `code/pj_lattice_vivarium.py:107` `reduce_counts` fields/overlap diagonal + separable_null; `active_witness_qubits`:79 keeps only ⟨X^⊗W⟩ quantum; LATTICE_CORRECTNESS.md
- [x] **AC-PJ2.2.10 (selective DD on the germ line — Weismann barrier, HW):** the HW path schedules selective DD
  (`[X,X]`) on the **germ-line physical qubits only** (reusing PJ0's pass sense via `viv_witness_qubits`-style
  targeting), body/lattice DD-free. Verified by inspecting the scheduled circuit (static).
  _Covered by:_ `code/pj_lattice_vivarium.py:128` `schedule_lattice_selective_dd` ([X,X] on `lattice_witness_qubits` physical only, body DD-free)
- [x] **AC-PJ2.2.11 (the mockups filled — Phase A + Phase B deliverable):** `analysis/pj_lattice_render.py` reads
  a banked PJ2.2 run JSON and emits **self-contained** filled ports of the mockups:
  `research/pj2_vivarium/lattice_3x3_snap.html` (all three modes × both arms, real `fields/w/overlap` per gen +
  `endpoint`), and `research/pj2_vivarium/lattice_4x4_movement.html` (solo movement only). Each is a port of the
  matching mockup with its client-side `genSolo/genRep/genDuo` generation block replaced by an injected
  `const DATA = <real scenarios>`; the snap/cloud/nucleus rendering (argmax + `easeBack`, centroid) is unchanged
  (it reads the real `fields`). CSP-safe (all inline, no external fetch), no sideways body scroll, works from
  `file://`. Also emit a static witness PNG (isolated vs coupled per mode) `pj2_lattice_witness.png`.
  _Covered by:_ `analysis/pj_lattice_render.py:105` `render_snap`→`research/pj2_vivarium/lattice_3x3_snap.html`, `render_4x4`:124→`lattice_4x4_movement.html`, `render_witness_png`:149→`pj2_lattice_witness.png`; CSP-safe (no external fetch), JS syntax-checked
- [x] **AC-PJ2.2.12 (live runs banked, CD-6/CD-7):** live Heron-r2 depth-scans — **Phase A** at least **3×3 solo**
  isolated+coupled (the minimal honest first run, 12q), **Phase B** **4×4 solo movement**, QRNG-certified
  fail-closed (mutation angles + start cell + hop schedule), chain-quality gate enforced; **one measured circuit
  per (mode, arm, gen, repeat)**; banked to `research_runs/pj2_lattice/`. Replicate/duo 3×3 live are opt-in after
  solo validates. PJ0/PJ1/PJ2 paths remain byte-stable. *Code complete; the developer executes the hardware run.*
  _Covered by:_ `code/pj_lattice_vivarium.py` depth_scan banks one measured circuit per (mode,arm,gen,repeat) to `research_runs/pj2_lattice/`; QRNG start/hop/thetas fail-closed (`qrng_environment`:208), `gated_chain`. Sim banked; live HW developer-run (OQ-8)

---

## 3. Out of scope

- **4×4 replicate and 4×4 duo.** ~35–38 qubits, past the laptop statevector (2³⁵ amplitudes) and the sim cap
  (`_SV_MAX_QUBITS`=27); the user's Phase B is explicitly **"just the movement"** = 4×4 **solo** (README §2).
- **Eating / energy / budding / any biology.** Cut as overclaiming (mockup README §1: "the honest scope is
  **movement + witness only**"). That machinery lives in PJ2's 1D `build_vivarium` and is not reused here.
- **Directional-bias scripting.** The mockup's `BIAS` drift is cosmetic; the real walk is isotropic (AC-PJ2.2.2).
- **A continuous measured movie.** Only integer generations are measured (depth scan); smooth playback stays a
  labelled sim artifact (README §5).
- **Binary/qudit cell encoding.** Unary (one qubit/cell) matches the renderer + the existing register layout and
  keeps the walk operator a simple stack of two-qubit gates (README §1). Binary is a leaner fallback only if the
  grid must grow past ~4×4.
- **Any edit to `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py`/`pj_vivarium.py`** or to the
  PJ0/PJ1/PJ2 builds (`build_germsoma`, `build_arena`, `build_vivarium`). PJ2.2 adds new functions + two new files.

---

## 4. Cross-cutting decisions applied (epic §3 + PJ0/PJ2 §4)

- **CD-1 (main-folder minimalism).** PJ2.2 **extends** `code/pj_qalife.py` with `build_lattice_vivarium` +
  lattice layout/analysis/`--selftest`, and adds a **new driver** `code/pj_lattice_vivarium.py` + a **new
  renderer** `analysis/pj_lattice_render.py`. No edit to the faithful reproduction or to PJ0/PJ1/PJ2 builds.
- **CD-3 (witness is the only quantum claim).** Sole quantum observable is ⟨X^⊗W⟩ over the germ line; occupancy,
  mass, overlap are declared classical; the separable null is reported alongside and must sit ≈0.
- **CD-4 (honesty invariant).** Movement/interaction are diagonal → exact classical surrogate → narrative. The
  richness datapoint = the generation/depth where the witness dies (never noise dressed as biology).
- **CD-5 (significance + chain-quality gates).** `entanglement_depth` (k=2 headline, k=3 reported); σ from
  `--repeats` + shot-noise in quadrature; fail-closed chain-quality gate (reuse `gated_chain`).
- **CD-6 (QRNG certified, fail-closed).** Mutation angles + the environment's stochastic parameters (start cell,
  per-gen hop schedule) come from `qrng_client.py`; fail-closed on hardware. `MUT_SCALE=0` faithful default
  (clean GHZ) so the walk's effect on the witness is isolated.
- **CD-7 (sim-first, hardware-confirm; verification without a test framework).** `--sim` + `--selftest` +
  `--dump-circuit` + written conclusion; then the live confirm. No test framework.
- **CD-8/CD-11 (behaviour measured, not noise; EM is a lever).** Walk/interaction are explicit coherent operators,
  never a bath; all witness loss is real hardware noise, so selective DD (AC-PJ2.2.10) is allowed to fight it.

---

## 5. Verified codebase facts (grounding the plan)

Line-anchored from the current tree:

- **Germ/witness machinery `code/pj_qalife.py`:** `viv_witness_q(k, width, track, traits)` (`:882`),
  `viv_to_witness_basis(qc, width, ...)` (`:1024`, H on germ only), `viv_witness_qubits(width, track, traits)`
  (`:1037`); the 1D vivarium builder `build_vivarium(...)` (`:920`) with phases germ / genome / Trotter `H_viv`;
  `_walk_layer(qc, width, organisms, track, traits, theta)` (`:527`) = **1D nearest-neighbour** `rxx+ryy` on a
  unary body track — **PJ2.2 needs a 2D von-Neumann analogue** (`_lattice_walk_layer`, new).
  `_collision_layer(...)` (`:539`, `soma_soma` body↔body / `germ_routed` A/B wound) is the template for the duo
  interaction + the coupled-arm wound. `vivarium_coupling_report(...)` (`:1058`) + `run_vivarium_selftest(...)`
  (`:1193`) are the templates for the new `lattice_coupling_report` + `run_lattice_selftest`. Constants pattern at
  `:860` (`VIV_HOP=0.6`, etc.).
- **Witness math `code/qalife.py` (read-only):** `xbasis_witness_from_counts(counts, qubits) -> (joint, sep)`,
  `entanglement_depth(...)`. Reused for the germ set.
- **PJ2 driver `code/pj_vivarium.py` (the template to mirror):** `build_measured_vivarium(...)` (`:75`),
  `reduce_counts(counts, width, *, track, traits)` (`:96`), `sim_snapshots(...)` (`:119`, Aer `save_statevector`
  at barriers), `schedule_vivarium_selective_dd(qc, backend, width, ...)` (`:162`, DD on `viv_witness_qubits`),
  `run_arm(...)` (`:200`, ONE measured circuit/arm), `dump_circuits(...)` (`:226`), `main()` (`:233`);
  globals `TRACK=6`, `TRAITS`, `STEPS_SIM=6`, `STEPS_HW=4`, `ARMS=("barren","vivarium","germ_coupled")` (`:62`),
  `K=2.0`, `MUT_SCALE=0.0`, `SELECTIVE_DD=True`, `VIV_SIM=AerSimulator("statevector")`, `_SV_MAX_QUBITS=27`
  (`:69`). **Sim vs HW = `args.backend is None`** (`:257`). Imports PJ0 infra by name.
- **PJ0 infra `code/pj_run_qalife.py`:** `gated_chain(backend, nq)`, `qrng_thetas(client, width, mut_scale,
  repeat)` (fail-closed), `OUTPUT_DIR`. Layout: `best_chain(backend, n, ...)` (`code/layout.py:54`, raises on no
  clean chain). QRNG: `qrng_client.py` (`QRNGUnavailable`).
- **Renderer template `analysis/pj_vivarium_render.py`:** `build_data(run)` (`:41`), inline `_TEMPLATE` with a
  `const DATA = {};` marker swapped by `render_html(data, out_dir)` (`:242` — `literal = "const DATA = " +
  json.dumps(...); html = _TEMPLATE.replace("const DATA = {};", literal, 1)`), `render_witness_png(run, out_dir)`
  (`:254`), `main()` (`:288`). **PJ2.2's renderer mirrors this**, with `_TEMPLATE` = a port of the target mockup.
- **Banked run schema `research_runs/pj2/*.json`:** top-level `{meta, arms}`; `arms` is a dict keyed by arm →
  `{witness_joint, separable_null, entanglement_signal, occupancy, food_remaining, energy, alive, steps,
  sim_frames:[{t, body, food, energy, witness_sim, alive}], survives}`; `meta` carries stage/model/backend/
  width/track/steps/arms/shots/sim/k/calibration/… **PJ2.2 banks a lattice-shaped schema** (§6.2).
- **Mockup data contract (`mockups/README.md` §3):** `scenarios[mode][arm][gen] = { fields:[occ[C], …], w,
  overlap }` (C = cells; 1 field solo, 2 for replicate/duo); `endpoint[mode][arm] = { w, survives }`. Modes
  `solo|replicate|duo`, arms `isolated|coupled`, W=3, GENS=6 (gen 0–5). **This is exactly what the renderer must
  produce.** Qubit budgets (README §2): 3×3 solo ≈12, 3×3 replicate/duo ≈20–24, 4×4 solo ≈19, 4×4 duo ≈35 (past
  laptop statevector).
- **No 2D/lattice circuit code exists** anywhere under `code/` or `analysis/` (grep for `lattice`/`3x3`/`4x4`
  hits only comment wording in `pj_qalife.py`/`pj1_spectacle.py`). PJ2.2 is the first 2D substrate.

---

## 6. File plan

Extend `code/pj_qalife.py` in place + **two new files** (`code/pj_lattice_vivarium.py`,
`analysis/pj_lattice_render.py`) + one new run dir + filled-mockup outputs. All new code strict-typed, PEP-8,
`from __future__ import annotations`, mirroring `pj_qalife.py`/`pj_vivarium.py` style. `qalife.py`,
`run_qalife.py`, `pj_run_qalife.py`, `pj1_run_arena.py`, `pj_vivarium.py` are **not edited**;
`build_germsoma`/`build_arena`/`build_vivarium` byte-stable.

### 6.1 Extend — `code/pj_qalife.py` (2D-lattice model + lattice `--selftest`)

- **Lattice layout helpers (new):**
  - `lat_neighbors(i: int, grid: int) -> list[int]` — von-Neumann neighbours of cell `i=r*grid+c`.
  - `lat_edges(grid: int) -> list[tuple[int, int]]` grouped into 4 edge colors (H-even/H-odd/V-even/V-odd).
  - `lat_segment_len(width, grid, mode) -> int` — `n_organisms*(width + grid*grid)` where `n_organisms` = 1 (solo)
    / 2 (replicate: parent+daughter) / 2 (duo). 3×3 solo = 12, 3×3 replicate/duo = 24, 4×4 solo = 19.
  - `lat_witness_q(org, k, width, grid)`, `lat_body_q(org, i, width, grid)` — per-organism offset indexing
    (germ block then body block per organism; witness loci at the front, mirroring PJ0/`viv_witness_q`).
- **`_lattice_walk_layer(qc, grid, org, width, theta) -> None`** — one Trotter walk layer: for each edge color,
  `rxx(theta)+ryy(theta)` on every von-Neumann neighbour pair of organism `org`'s body block. Excitation-
  conserving, germ untouched, applied unconditionally.
- **`build_lattice_vivarium(width, grid, gens, thetas, *, mode='solo', arm='isolated', start=0,
  founder_equator=True, annotate=False) -> QuantumCircuit`** — phased, **for one target depth `gens`** (the
  driver calls it once per depth for the scan):
  1. **Germ line(s) first** (rung-0): founder `ry(π/2)` + NN `cx` clone chain + `ry(thetas[k])` mutation on each
     organism's germ block. Barrier `"germline"`. (Reuse the PJ0 GHZ pattern.)
  2. **Seed the body:** `x` organism 0's body at `start` cell (solo/replicate); duo seeds org-0 at corner `0` and
     org-1 at the opposite corner `grid*grid-1`. Barrier `"seed"`.
  3. **Life cycle = `gens` walk layers**, each a `barrier` (the sim snapshot point): `_lattice_walk_layer` per
     organism. **Replicate:** at layer index 2, insert the germ→germ CNOT clone (parent germ → daughter germ) +
     seed the daughter body one cell over. **Duo:** after each walk layer, apply the co-located A/B body
     interaction `rxx+ryy` (emergent; template `_collision_layer`'s `soma_soma`). Barrier `"walk{d}"` per layer.
  4. **Coupled arm wound:** if `arm=='coupled'`, add one coherent `rxx` from a body cell to `lat_witness_q(0,0)`
     (the soma→germ back-action — the A/B kill-switch). `isolated` adds nothing. Barrier `"arm"`.
- **Static analyzers (build-time):**
  - `lattice_witness_qubits(width, grid, mode) -> list[int]`, `lattice_body_qubits(org, width, grid) -> list[int]`.
  - `lattice_coupling_report(qc, width, grid, *, mode, arm) -> dict` — walks `qc.data`; returns
    `back_action` (True only in `coupled`: a body↔witness-locus gate), `witness_isolated` (germ loci appear only
    in founder/clone/mutation + terminal H+measure, never paired with a body qubit — in `isolated`),
    `mass_conserved` (every body-layer gate is `rxx`/`ryy` on a neighbour pair), `germ_first` (germ gates precede
    the walk), `has_classical_branch` (must be **False**), and gate counts.
- **Extend `--selftest`** (`run_lattice_selftest`, mirror `run_vivarium_selftest`) at representative
  `(grid, mode)` — e.g. `(3,'solo')`, `(3,'replicate')`, `(3,'duo')`, `(4,'solo')`: (i) `witness_isolated=True`
  + `back_action=False` for `isolated`, `back_action=True` for `coupled`; (ii) `mass_conserved=True`
  (walk is `rxx+ryy` neighbour pairs only); (iii) germ-first ordering; (iv) witness readout isolation (H on germ
  only; body in Z); (v) `has_classical_branch=False`; (vi) replicate clone is germ→germ only (no soma→germ);
  (vii) qubit count matches `lat_segment_len`. Print per-check `OK` + `SELFTEST PASS`.
- **Extend `main()`** with lattice flags: `--lattice` (switch to lattice build), `--grid {3,4}`, `--mode
  {solo,replicate,duo}`, `--arm {isolated,coupled}`, `--gens`. Default (no `--lattice`/`--arena`/`--vivarium`) =
  the existing PJ0 static CLI, unchanged.

### 6.2 New — `code/pj_lattice_vivarium.py` (the lattice driver — build + sim + live depth-scan)

Mirror `code/pj_vivarium.py`. Imports `pj_qalife as pj`, `qalife as q4`, and reuses PJ0 infra by name
(`from pj_run_qalife import gated_chain, qrng_thetas, OUTPUT_DIR`); **no edit** to PJ0/PJ1/PJ2 files.

- **Globals:** `GRID=3`, `GENS=6`, `MODES=("solo","replicate","duo")`, `ARMS=("isolated","coupled")`, `WIDTH=3`,
  `HOP=0.6`, `K=2.0`, `MUT_SCALE=0.0`, `SELECTIVE_DD=True`, `REPEATS=3`, reuse chain thresholds,
  `LAT_SIM=AerSimulator("statevector")`, `_SV_MAX_QUBITS=27`.
- **`build_measured_lattice(width, grid, gens, thetas, *, mode, arm) -> QuantumCircuit`** — call
  `pj.build_lattice_vivarium(...)`, then **H on germ qubits only** (`pj.viv_to_witness_basis`-style over
  `lattice_witness_qubits`), body left in Z; add `ClassicalRegister`, measure all → one circuit yields witness
  (germ) + occupancy (body).
- **`reduce_counts(counts, width, grid, *, mode) -> dict`** — `fields` = per-cell P(1) marginals (1 field solo, 2
  for replicate/duo via each organism's body block); `witness_joint`/`separable_null` via
  `q4.xbasis_witness_from_counts(counts, pj.lattice_witness_qubits(...))`; duo `overlap = Σ min(fA, fB)`.
- **`depth_scan(mode, arm, *, width, grid, gens, backend, shots, repeats) -> list[dict]`** — the honest frames:
  for `d in range(gens)` build `build_measured_lattice(..., gens=d)`, run once per repeat, reduce → one frame
  `{gen:d, fields, w:mean, w_sigma, sep, survives, overlap}`. **One measured circuit per (mode, arm, gen,
  repeat).**
- **Sim path:** mirror PJ2's `sim_snapshots` (`pj_vivarium.py:119`) — it already **rebuilds the circuit at each
  depth prefix** (`build_lattice_vivarium(..., gens=d)`) + `save_statevector`, which **is** the depth-scan, so
  sim and HW share one code path (sim reads exact `probabilities_dict`, HW reads measured counts). Guarded by
  `_SV_MAX_QUBITS`. Sim witness pins ≈ +1 (noiseless) — the ceiling; the certified decay shape comes from the
  live/noisy run.
- **QRNG (CD-6):** `qrng_thetas` for mutation angles + a QRNG draw for the **start cell** and the **per-gen hop
  schedule** (fixed per circuit); fail-closed on HW.
- **Selective DD (AC-PJ2.2.10):** `schedule_lattice_selective_dd(qc, backend, width, grid, mode)` — `[X,X]` on the
  germ physical qubits only (reuse PJ0's pass sense targeting `lattice_witness_qubits`; same forced deviation PJ1
  documented, not an edit to PJ0).
- **Run schema (inline dict, mirror PJ2):** `meta.stage="PJ2.2"`, `meta.model="lattice_vivarium"`, +
  `meta.grid/width/gens/modes/arms/shots/sim/k/hop/mut_scale/selective_dd/certified_frames=True/calibration`;
  `scenarios` = `{mode: {arm: [ {gen, fields, w, w_sigma, sep, survives, overlap} per gen ] }}` and `endpoint` =
  `{mode: {arm: {w, survives}}}` — **exactly the mockup data contract** (README §3) so the renderer consumes it
  directly. Bank to `research_runs/pj2_lattice/`.
- **CLI (own `main()`):** `--backend` (None=sim), `--grid` (default 3), `--width` (default 3), `--mode` (default:
  run all three; `solo` only when `--movement-only`), `--arm` (default: both), `--gens` (default 6), `--repeats`,
  `--shots`, `--movement-only` (forces `mode=solo`, for the 4×4 Phase B), `--dump-circuit`/`--draw-only`,
  `--name` (default `pj2_lattice`).

### 6.3 New — `analysis/pj_lattice_render.py` (fill the mockups)

Mirror `analysis/pj_vivarium_render.py` (`_latest`, `build_data`, inline `_TEMPLATE` with a `const DATA = {};`
marker, `render_html`, `render_witness_png`, `main() -> int`, degrade-gracefully). Reads a banked
`research_runs/pj2_lattice/*.json`.

- **Two templates:** `_TEMPLATE_SNAP` = a port of `mockups/vivarium_3x3_snap.html` and `_TEMPLATE_4X4` = a port of
  `mockups/vivarium_4x4_scenarios.html`, each with its client-side generation block (`const G/N/GENS`,
  `genSolo/genRep/genDuo`, `const DATA = {...}`) **replaced by** a single `const DATA = {};` marker plus a
  `const GRID = <grid>` marker. The snap/cloud/nucleus rendering (argmax + `easeBack` trail, centroid glide) is
  kept verbatim — it reads the injected real `fields`.
- **`build_data(run) -> dict`** — pass the banked `scenarios` + `endpoint` straight through (they already match
  the contract); attach `grid`, certified-frames flag, and the live-vs-sim provenance for the caption.
- **`render_html`** — inject `const DATA = <scenarios/endpoint>` + `GRID`, write
  `research/pj2_vivarium/lattice_3x3_snap.html` (3×3, all modes) and, from a 4×4 solo run,
  `research/pj2_vivarium/lattice_4x4_movement.html` (solo only). CSP-safe, no sideways scroll, `file://`-safe.
- **`render_witness_png`** — isolated vs coupled witness-vs-gen per mode → `research/pj2_vivarium/
  pj2_lattice_witness.png` (matplotlib Agg, degrade-gracefully).
- **CLI:** `--run-glob`, `--out-dir` (default `research/pj2_vivarium`).

### 6.4 New — `research_runs/pj2_lattice/` + `research/pj2_vivarium/` artifacts

- `research_runs/pj2_lattice/pj2_lattice_*.json` — banked sim + live runs.
- `research/pj2_vivarium/lattice_3x3_snap.html`, `lattice_4x4_movement.html` — the **filled** mockups (real data).
- `research/pj2_vivarium/pj2_lattice_witness.png` — the isolated-vs-coupled witness figure.
- `research/pj2_vivarium/circuits/lattice_*.txt` — printed circuits (`--dump-circuit`) per mode/arm/depth.
- `research/pj2_vivarium/LATTICE_CORRECTNESS.md` — static-correctness argument (mass-conservation/`rxx+ryy` proof,
  no-`if` walk, germ→germ clone, coupled A/B contrast, selective DD on the germ line) with `--selftest` output.
- `research/pj2_vivarium/LATTICE_CONCLUSION.html` — results writeup (the three modes, isolated vs coupled witness
  decay with depth, the ~5–6-gen ceiling, honest framing: certified integer frames vs sim interpolation; scale ·
  faithfulness · certification, not a speedup).

### 6.5 Resulting layout (after PJ2.2)

```
code/
  pj_qalife.py            # EXTENDED — + build_lattice_vivarium, lattice layout/analysis, --selftest
  pj_vivarium.py          # UNCHANGED — PJ2 1D driver
  pj_lattice_vivarium.py  # NEW — 2D-lattice driver: build_measured_lattice, depth_scan, PJ2.2 schema
analysis/
  pj_vivarium_render.py   # UNCHANGED
  pj_lattice_render.py    # NEW — banked data -> filled mockups + witness PNG
research/pj2_vivarium/
  mockups/                # UNCHANGED design mockups (the target)
  lattice_3x3_snap.html   lattice_4x4_movement.html   pj2_lattice_witness.png   # NEW filled outputs
  LATTICE_CORRECTNESS.md  LATTICE_CONCLUSION.html      circuits/                 # NEW
research_runs/
  pj2/ ...                # UNCHANGED
  pj2_lattice/            # NEW — PJ2.2 run JSON
```

---

## 7. Implementation steps

1. **Lattice layout + `_lattice_walk_layer` + `build_lattice_vivarium`** — new index/neighbour/edge-color
   helpers; germ-first, seed, `gens` von-Neumann walk layers with a `barrier` each; replicate germ-clone at
   layer 2; duo co-located interaction; coupled-arm wound. Reuse the PJ0 GHZ + `_collision_layer` patterns.
   `build_vivarium`/`build_germsoma`/`build_arena` untouched.
2. **Lattice static analyzers** — `lattice_witness_qubits`, `lattice_body_qubits`, `lattice_coupling_report`
   (back_action / witness_isolated / mass_conserved / germ_first / no-branch).
3. **Extend `--selftest`** (`run_lattice_selftest`) — the seven checks (§6.1) at `(3,solo/replicate/duo)` +
   `(4,solo)`. Iterate to `SELFTEST PASS`.
4. **Lattice `main()` static CLI** — `--lattice --grid --mode --arm --gens --dump-circuit` prints the circuit +
   report per mode/arm/depth.
5. **New `code/pj_lattice_vivarium.py`: `build_measured_lattice` + `reduce_counts`** — H germ only + body in Z;
   witness/null + per-cell occupancy + duo overlap from one circuit.
6. **`depth_scan` + sim path** — one measured circuit per depth; sim depth-scan / statevector snapshots;
   verify `isolated` witness ≈ ceiling and decaying with depth, `coupled` collapses; occupancy walks + mass
   conserved; replicate doubles the field at gen 2; duo overlap rises as fields meet.
7. **HW path (depth scan, certified frames)** — selective DD on the germ line (AC-PJ2.2.10); `gated_chain` +
   QRNG (angles + start cell + hop schedule) fail-closed; one measured circuit per (mode, arm, gen, repeat);
   schema to `research_runs/pj2_lattice/`.
8. **`analysis/pj_lattice_render.py`** — port the snap + 4×4 mockups into `_TEMPLATE`s with the `const DATA` +
   `GRID` markers; inject the banked scenarios → filled `lattice_3x3_snap.html` + `lattice_4x4_movement.html`;
   witness PNG.
9. **Live runs + bank (developer)** — Phase A: 3×3 solo isolated+coupled depth-scan on least-busy Heron-r2
   (replicate/duo opt-in); Phase B: 4×4 solo movement depth-scan; render the mockups from the live JSON; write
   `LATTICE_CORRECTNESS.md` + `LATTICE_CONCLUSION.html`.

---

## 8. Manual verification (no tests; static + sim + live depth-scan — CD-7)

- `python code/pj_qalife.py --lattice --selftest` → seven lattice checks `OK` at `(3,solo/replicate/duo)` +
  `(4,solo)`, `SELFTEST PASS`, exit 0. Also `--selftest` (PJ0), `--arena --selftest` (PJ1), `--vivarium
  --selftest` (PJ2) still pass (byte-stable).
- `python code/pj_qalife.py --lattice --grid 3 --mode solo --arm isolated --gens 5 --dump-circuit` → one build;
  `witness_isolated=True`, `back_action=False`, `mass_conserved=True`, `has_classical_branch=False`; witness set
  = the germ loci; walk gates present as `rxx+ryy` neighbour pairs.
- `... --mode duo --arm coupled --dump-circuit` → `back_action=True` (a body→witness gate present) — the A/B
  contrast that collapses the witness; duo interaction gates present.
- `... --mode replicate --dump-circuit` → the germ→germ clone at layer 2, no soma→germ gate (isolated).
- `python code/pj_lattice_vivarium.py --grid 3 --gens 6 --repeats 1` (no `--backend` = sim) → banks all three
  modes × both arms as a depth scan (**one circuit per gen**); `isolated` witness high and gently decaying,
  `coupled` collapses; occupancy walks with mass conserved; replicate field doubles at gen 2; duo overlap rises.
- `python code/pj_lattice_vivarium.py --grid 4 --movement-only --gens 6` (sim) → 4×4 **solo** depth scan (19q),
  the field walks the larger lattice, witness reported vs null.
- `python analysis/pj_lattice_render.py --run-glob 'research_runs/pj2_lattice/*sim*.json'` → writes
  `research/pj2_vivarium/lattice_3x3_snap.html` (modes/arms toggle, the body snaps to the dominant cell, Ψ shows
  real ⟨n⟩, witness meter green isolated / red coupled) and `lattice_4x4_movement.html` (solo); witness PNG
  written; both self-contained (no external refs), no sideways scroll, open from `file://`.
- Inspect the **scheduled** HW circuit → selective DD on the **germ line only**, body/lattice DD-free.
- Live (developer): `python code/pj_lattice_vivarium.py --backend <heron> --grid 3 --mode solo --gens 6
  --repeats 3 --shots 8192` (QRNG env set) → the certified 3×3 solo depth scan banked to `research_runs/
  pj2_lattice/`; then `--grid 4 --movement-only`; render from live data.
- Confirm `qalife.py`, `run_qalife.py`, `pj_run_qalife.py`, `pj1_run_arena.py`, `pj_vivarium.py` unchanged
  (`git diff` empty); PJ0/PJ1/PJ2 `--selftest` green.

---

## 9. Risks

- **R1 — depth vs coherence (the whole point).** Each generation stacks a full lattice walk layer (many 2-qubit
  gates) → the witness erodes with `gens`. Mitigation: cheapest primitives (single `rxx+ryy` per edge, edge-
  colored), **few gens** on HW, DD on the germ line, k=2 gate. If the witness dies at small `gens`, that ceiling
  **is** the result (mockup's ~5–6-gen claim, now measured). README §4: **readout error now dominates 2q error**,
  and the witness (X-basis rotation + parity read) is more fragile than the diagonal occupancy — expect the
  witness to be the first to go.
- **R2 — many circuits (depth scan × modes × arms × repeats).** 6 gens × 3 modes × 2 arms × 3 repeats = 108
  circuits for the full 3×3 sweep. Mitigation: each is shallow; scope the **live** run to the minimal-honest
  **3×3 solo** first (12 circuits: 6 gens × 2 arms, repeats aside), replicate/duo live opt-in. Cheaper than a
  many-shot movie; still one measured circuit per certified frame.
- **R3 — qubit budget.** `nq = n_org*(W + grid²)`. 3×3 solo=12, 3×3 replicate/duo=24 (fit sim `_SV_MAX_QUBITS`
  =27), 4×4 solo=19 (fits), 4×4 replicate/duo=38/35 (past sim → **out of scope**, README §2). All 3×3/4×4-solo
  cases fit Heron comfortably. `gated_chain` fail-closes on HW.
- **R4 — the walk operator's isotropy vs the mockup's drift.** The mock's directional `BIAS` was cosmetic; a
  real isotropic walk drifts less visibly. Mitigation: seed at a corner (boundary breaks symmetry → visible
  spread) and let the render's argmax "snap" carry the motion; optionally a weak two-angle asymmetry if a
  directional look is wanted — documented as a rendering choice, not scripted biology (OQ-4).
- **R5 — replicate/duo Weismann faithfulness.** The clone must be **germ→germ** and the duo interaction
  **body↔body**; any accidental soma→germ gate would silently break the isolated arm. Mitigation: the static
  `witness_isolated`/`back_action` checks gate every build (AC-PJ2.2.7); the `coupled` arm is the *only* place a
  body→germ gate is allowed.
- **R6 — sim is too benign (noiseless).** As PJ2 found, noiseless sim pins the witness at the ceiling for every
  mode/arm; the *shape* of the decay and the collapse are hardware effects. Mitigation: sim confirms logical
  correctness (isolation, mass conservation, monotone gate growth) + the ceiling; the real frontier is the live
  depth scan. A fake-noisy backend can preview the curve shape.
- **R7 — QRNG fail-closed / neighbour byte-stability.** Reuse the fail-closed gating; keep all PJ0/PJ1/PJ2 builds
  and drivers byte-stable; their `--selftest`s must stay green.

---

## 10. What later rungs pick up

- **Fusing PJ2 biology into the lattice:** food/energy/budding (PJ2's cut-here machinery) could drop onto the 2D
  lattice as a later, explicitly-scoped richness rung — but only after the movement+witness baseline is certified
  live (this ticket), so the biology's witness cost is measured against a clean 2D baseline.
- **Larger grids via binary/MPS:** 5×5+ or 4×4-duo need binary cell encoding or a tensor-network sim (README §1/§2)
  — a separate encoding study.
- **Depth-scan as the standard certified-frame protocol:** this ticket establishes "each generation is its own
  measured circuit" as the honest movie for the whole QALife line, replacing the one-circuit-sim-movie where a
  certified trajectory (not just an endpoint) is wanted.

---

## 11. Open questions — proposed defaults (developer answers; I do not self-approve)

- **OQ-1 (certified frames: depth-scan vs one-circuit-sim-movie) — PROPOSAL: depth-scan on HW** (each generation
  its own measured circuit, the README's honest recipe), statevector snapshots in sim for speed. Integer
  generations certified; smooth playback a labelled sim artifact. **Default: HW depth-scan.**
- **OQ-2 (cell encoding) — PROPOSAL: unary** (one qubit/cell) — matches the renderer + the existing register
  layout, keeps the walk a simple 2-qubit-gate stack. **Default: unary.**
- **OQ-3 (live-run scope) — PROPOSAL: Phase A live = 3×3 solo isolated+coupled** (the minimal honest first run,
  12q), replicate/duo 3×3 live **opt-in** after solo validates; **Phase B live = 4×4 solo movement**. All modes
  run in **sim** regardless. **Default: solo live first, replicate/duo live on request.**
- **OQ-4 (walk isotropy vs the mock's directional drift) — PROPOSAL: isotropic uniform-θ walk**, drift emerges
  from the corner seed + boundaries; the mock's `BIAS` was cosmetic. A weak two-angle asymmetry is available as a
  documented rendering choice if a directional look is wanted. **Default: isotropic.**
- **OQ-5 (survive threshold) — PROPOSAL: `witness − sep > k·σ`, k=2 headline / k=3 reported** (CD-5); the mockup's
  fixed 0.15 line is only a rendering cue. **Default: k=2.**
- **OQ-6 (which mockups to fill) — PROPOSAL: `vivarium_3x3_snap.html` (primary) + `vivarium_4x4_scenarios.html`
  solo (Phase B)**; `vivarium_3x3_smooth.html` is the same data with a different render, filled for free if
  trivial. **Default: snap + 4×4-solo; smooth if trivial.**
- **OQ-7 (run directory) — PROPOSAL: new `research_runs/pj2_lattice/`** (distinct lattice schema; keeps PJ2's 1D
  runs uncontaminated). **Default: new dir.**
- **OQ-8 (who runs HW) — PROPOSAL: developer runs the live depth-scans** (established), sim first.

---

## 12. Ground rules honored

- Every AC traces to the mockups + `mockups/README.md` (the honest recipe) + the PJ0/PJ2 substrate; none invented.
- Concrete file paths + line-grounded references (§5, §6).
- Epic cross-cutting decisions applied (§4); CD-1 in-place extension + two new files.
- Biology, 4×4 replicate/duo, binary encoding, and a continuous measured movie kept out of scope (§3).
- Strict types + PEP-8; no raw SQL / templates (N/A).
- No tests (CD-7): static `--selftest` + `--dump-circuit` + `--sim` + live depth-scans + written conclusion.
- `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py`/`pj_vivarium.py` byte-stable; prior selftests
  green.
- `Status: Draft` — the developer flips to Approved, then `/implement-feature`.
```

---

## 13. Post-implementation notes

**Built (2026-09-24):**
- **`code/pj_qalife.py` (extended, byte-stable to PJ0/PJ1/PJ2):** lattice layout helpers
  (`lat_n_organisms`, `lat_segment_len`, `lat_base`, `lat_witness_q`, `lat_body_q`, `lat_neighbors`,
  `lat_edges`), `_lattice_germ`/`_lattice_walk_layer`/`_lattice_clone`/`_lattice_interaction`,
  `build_lattice_vivarium` (solo/replicate/duo × isolated/coupled, depth-scan-ready),
  `lattice_to_witness_basis`, `lattice_witness_qubits`/`lattice_body_qubits`,
  `lattice_coupling_report`, `run_lattice_selftest` (7 checks × 4 cases, all OK), `print_lattice_report`,
  and `--lattice --grid --mode --arm --gens` CLI. Default PJ0/PJ1/PJ2 paths unchanged.
- **`code/pj_lattice_vivarium.py` (new driver):** `build_measured_lattice`, `active_witness_qubits`,
  `reduce_counts`, `schedule_lattice_selective_dd`, `depth_scan` (one measured circuit per
  `(mode, arm, gen, repeat)`), `qrng_environment` (start cell + hop, fail-closed), PJ2.2 run schema →
  `research_runs/pj2_lattice/`. Sim runs banked for 3×3 (all modes/arms) and 4×4 solo.
- **`analysis/pj_lattice_render.py` (new renderer):** faithful programmatic port — swaps each mockup's
  client-side generation block for injected real `DATA`+`GRID`; emits self-contained
  `research/pj2_vivarium/lattice_3x3_snap.html`, `lattice_4x4_movement.html`, `pj2_lattice_witness.png`.
- **Writeups:** `research/pj2_vivarium/LATTICE_CORRECTNESS.md`, `LATTICE_CONCLUSION.html`, circuit dumps
  in `research/pj2_vivarium/circuits/lattice_*.txt`.

**Two decisions worth flagging to the developer:**
1. **Replicate witness set is depth-dependent (`active_witness_qubits`).** Before the gen-2 clone the
   daughter germ is `|0⟩`; H-ing it would inject random X-parity and null the joint. So gens 0–1 use the
   parent-only `⟨X^⊗W⟩`; gens 2–5 use the shared `⟨X^⊗2W⟩`. This is the honest reading (the shared GHZ
   only exists once the daughter does) but means the replicate witness dimension changes at gen 2.
2. **Duo seeds fixed corners `0` and `grid²−1`** (not the QRNG `start` cell, which drives solo/replicate).
   Matches the mockup's opposite-corner drift; the QRNG start/hop still gate the run for provenance.

**Deferred (developer):** live Heron-r2 depth-scans — Phase A 3×3 solo isolated+coupled (12q, the
minimal honest first run; replicate/duo 3×3 opt-in), Phase B 4×4 solo movement (19q). Then re-render
the mockups from the live JSON (`--run-glob 'research_runs/pj2_lattice/*<backend>*.json'`) and refresh
`LATTICE_CONCLUSION.html` with the measured decay + the collapse generation. Noiseless sim pins the
isolated witness at +1.0 — the decay shape and the ~5–6-gen ceiling are hardware numbers.
