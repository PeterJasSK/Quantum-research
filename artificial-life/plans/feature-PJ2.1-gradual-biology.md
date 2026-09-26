# Feature Plan — PJ2.1: Gradual biology dial — titrate richness against a live witness

**Ticket:** PJ2.1 (stage; refactor/extension of PJ2 — this research repo decomposes epics into stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09), stage **P3**
**Refactors:** `artificial-life/plans/feature-PJ2-solo-vivarium.md` (Status: **Complete**) — same organism, now with a gradual on-ramp
**Motivation:** the first live W12 run (`research_runs/pj2/pj2_vivarium_ibm_kingston_20260923-093000.json`) showed the biology is **all-or-nothing**: idle habitat kept the witness at **+0.732** (certified alive at W=12), the full life cycle collapsed it to **−0.058** (dead). We need to turn biology on **gradually** and find how much richness the witness survives.
**Substrate:** `code/pj_qalife.py` (`build_vivarium`) + `code/pj_vivarium.py` (driver) + `analysis/pj_vivarium_render.py`.
**Slug:** gradual-biology
**Author:** Claude (Opus)
**Date:** 2026-09-23
**Status:** Draft

> **No tests (repo convention, CD-7).** Verification is `--selftest` + `--dump-circuit` + `--sim` + a
> written conclusion. No test framework.
>
> **This ticket RUNS (build + sim + live-ready).** The developer executes the hardware sweep (OQ-4 from PJ2).

---

## 1. Summary

PJ2 proved the organism works but showed the biology is a **cliff**: on `ibm_kingston` the clean germ
genealogy is certified at **W=12 (+0.732)** with an *idle* body, yet switching the whole life cycle on
collapses the witness to the null (**−0.058**). Crucially, `barren` and `vivarium` are the **same circuit
at the same depth** (differing only by the food seed) and are **identical in noiseless sim (+1.000 each)**
— so the collapse is **physical**: an *active* soma decoheres the neighbouring germ line via crosstalk /
scheduling, even behind a perfect *logical* Weismann barrier. Depth is not the killer; **activity is**.

PJ2.1 refactors the vivarium so biology turns on **gradually**, and adds the controls needed to attribute
the collapse and push the frontier out, so we can **add some biology and keep the witness alive** (the
genealogical entanglement — the "entropy" — does not die):

1. **A continuous intensity dial `λ ∈ [0,1]`** scaling every biological gate angle (forage / eat / bud /
   death). `λ=0` → all bio gates become identity → pure germ (witness at its ceiling); `λ=1` → full PJ2
   biology. Gentle biology = less activity = less crosstalk = a witness that survives.
2. **An operator ladder `--bio-level 0..6`** — enable biological processes one at a time (germ-only →
   +forage → +eat → +bud → +death/revive → +state-dependent motility → +hard-select). "Add some biology"
   literally = raise the level by one and re-measure the witness.
3. **A germ↔soma physical buffer `--buffer B`** — idle spacer qubits between the germ block and the soma,
   increasing physical distance to cut spectator-ZZ crosstalk onto the germ line (the mitigation lever).
4. **A shared fixed layout across all sweep points** (`--fixed-layout`) and **repeats** (`--repeats`) — the
   two confounds flagged in the PJ2 live read: right now each arm is transpiled independently (the germ can
   land on different physical qubits) and N=1 (shot-noise σ only). Pinning one layout isolates the biology
   from layout luck; repeats give real error bars.

**Deliverable:** the **richness-vs-witness curve** — witness vs `bio-level` (and vs `λ`) at fixed W, on one
pinned clean chain with error bars — locating the **maximum biology that still carries a certified witness**
(`witness − null > k·σ`). That crossing point is the epic's richness-vs-collapse datapoint (AC-P3.2), now
measured as a smooth frontier instead of a cliff.

**Backward compatible:** the PJ2 defaults (`bio_level=MAX`, `λ=1`, `buffer=0`, per-arm transpile) reproduce
the current `build_vivarium` byte-for-byte in behaviour; the new knobs are additive.

---

## 2. Acceptance criteria

Grounded in the PJ2 substrate, the epic richness question (§1), and the PJ2 live-run read. IDs added. All
hardware ACs enforce the chain-quality gate (CD-5) and certified QRNG (CD-6). No tests (CD-7).

- [ ] **AC-PJ2.1.1 (continuous intensity dial):** `build_vivarium` takes `intensity: float = 1.0`; every
  biological gate angle (forage `rxx/ryy`, the energy-controlled hop, eat, bud, death `cry`) is scaled by
  `λ`. At `λ=0` all biological gates reduce to identity (the germ line is untouched → witness at its
  noiseless ceiling); at `λ=1` the circuit is the current PJ2 build. Verified by `--dump-circuit` (angles
  scale) + a sim monotonicity check (witness non-increasing as λ rises in the presence of a noise model).
  Eat/bud become **partial** controlled rotations (`RX(λ·π).control(2)`) so consumption/reproduction turn
  on smoothly rather than as a hard Toffoli.
- [ ] **AC-PJ2.1.2 (operator ladder):** `build_vivarium` takes `bio_level: int` (0..6) enabling processes
  cumulatively — **0** germ only (idle body), **1** +forage, **2** +eat, **3** +bud, **4** +death/revive,
  **5** +state-dependent (energy-controlled) motility, **6** +`hard_select`. `--bio-level` on both CLIs.
  Static check (`vivarium_coupling_report`): the gate set grows monotonically with level; `back_action`
  stays False at every level (the barrier holds as biology is added); `expression` stays True from level 0.
- [ ] **AC-PJ2.1.3 (germ↔soma buffer):** `build_vivarium` takes `buffer: int = 0` inserting `buffer` idle
  spacer qubits between the germ block and the soma registers (updating the layout helpers + `viv_segment_len`).
  Static check: the buffer qubits carry no gates; the witness set and Static-Test isolation are unchanged;
  `viv_segment_len` grows by `buffer`.
- [ ] **AC-PJ2.1.4 (shared fixed layout across sweep points):** the driver can transpile **once** (the
  richest point) and **reuse that `initial_layout`** for every sweep point, so the germ loci occupy the
  **same physical qubits** at every biology level/intensity. `--fixed-layout` (default on for sweeps). The
  banked run records the pinned physical germ qubits in `meta`.
- [ ] **AC-PJ2.1.5 (repeats + error bars):** the driver takes `--repeats R` (default 3 for sweeps); each
  point's witness is reported as mean ± σ over repeats with the shot-noise floor added in quadrature (CD-5);
  `survives` ⇔ `witness − null > k·σ`.
- [ ] **AC-PJ2.1.6 (the richness-vs-witness sweep — THE result):** a `--bio-sweep` mode runs `bio_level`
  0..N (and/or `--intensity-scan` over λ) at fixed W on one pinned chain with repeats, banking witness +
  null + signal + survives per point. Reports the **max bio_level (and max λ) with the witness still ALIVE**
  (`> k·σ`) — the frontier. Sim first, then live.
- [ ] **AC-PJ2.1.7 (buffer/DD mitigation quantified):** report the witness at a fixed nontrivial bio_level
  for `buffer ∈ {0, 2, 4}` (and DD on/off), showing how much physical separation buys back — the honest
  "how far can we push the frontier out" number (CD-11 spirit: mitigation before declaring the ceiling).
- [ ] **AC-PJ2.1.8 (honest attribution):** because barren/vivarium are logically identical on the germ loci
  (noiseless sim = +1.000 at every level), the writeup states plainly that the witness decay across levels
  is a **physical crosstalk/scheduling effect**, not a logical one; the fixed-layout + repeats controls are
  what license attributing the curve to biology rather than layout luck (the two PJ2 confounds, closed).
- [ ] **AC-PJ2.1.9 (spectacle + curve):** `analysis/pj_vivarium_render.py` gains a **richness-vs-witness**
  figure (witness vs bio_level with error bars, the survive/collapse line at `k·σ`), and the solo-vivarium
  demo gains a biology-level slider driving the sim frames. Self-contained, CSP-safe.
- [ ] **AC-PJ2.1.10 (backward compatible + byte-stable neighbours):** PJ2 defaults (`bio_level=MAX`,
  `intensity=1`, `buffer=0`) reproduce the current PJ2 behaviour; PJ0/PJ1 `--selftest` stay green;
  `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py` byte-stable. Live sweep banked to
  `research_runs/pj2/` — **developer runs the hardware** (OQ-4).

---

## 3. Out of scope

- **New biological operators.** PJ2.1 titrates the *existing* PJ2 processes; no new biology (later P3 rungs).
- **Multi-organism / arena.** Single organism (PJ2 scope); the arena is PJ1.
- **Error mitigation beyond DD + buffer + fixed layout** (ZNE, readout mitigation, PEC) — the P3-candidate
  EM ladder is a separate lever; buffer/DD/fixed-layout are the crosstalk-specific ones this ticket needs.
- **Changing the witness observable / the honesty invariant** (CD-3/CD-4 unchanged).
- **Any edit to `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py`** or to PJ0/PJ1 builds.
  PJ2.1 refactors `build_vivarium` + `pj_vivarium.py` + the renderer only.

---

## 4. Cross-cutting decisions applied (epic §3 + PJ2 §4)

- **CD-1** — extends `pj_qalife.py` (`build_vivarium`) + `pj_vivarium.py`; no new fork, no edit to the
  faithful reproduction or PJ0/PJ1.
- **CD-3/CD-4** — `⟨X^⊗W⟩` vs the null is still the only claim; the whole richness-vs-witness curve is the
  measured frontier; body/energy/food/population stay diagonal narrative. λ=0 must give the null≈0 + the
  witness ceiling.
- **CD-5** — `k·σ` survive gate, σ from repeats + shot noise in quadrature; fail-closed chain gate.
- **CD-6** — QRNG certified, fail-closed on hardware; `MUT_SCALE=0` faithful.
- **CD-7** — sim-first + `--selftest` + `--dump-circuit`; no test framework.
- **CD-8/CD-11** — every rung is an explicit measured process (never noise dressed as biology); buffer/DD are
  honest mitigation levers reported against their cost (extra qubits / depth), tried before declaring the
  frontier.

---

## 5. Verified codebase facts (grounding the plan)

Current PJ2 code (post-implementation):
- **Model `code/pj_qalife.py`:** `build_vivarium` (`:920`) — phases germ / genome+expression / Trotter
  `H_viv` (forage `rxx+ryy` + energy-controlled `RXXGate(...).control(1)` / eat `ccx`+`cx` / bud `ccx`) /
  death `cry`+`cx` + revive `cx`. Layout helpers `viv_witness_q`/`viv_gene_q`/`viv_body_q`/`viv_food_q`/
  `viv_energy_q`/`viv_bath_q`/`viv_fit_q`; `viv_segment_len` = `W + traits + 3·track + n_food (+1 hard)`.
  `vivarium_coupling_report` (`:1058`) returns `expression`/`back_action`/`witness_isolated`/
  `selection_diagonal`/`has_classical_branch`; `run_vivarium_selftest` (`:1193`) 7 checks. Constants
  `VIV_FOOD_SITES=(2,4)`, `VIV_HOP=0.6`, `VIV_STARVE=0.6`, `VIV_TRAITS=3`, `GENE_ROLE/REPL/LIFE`.
- **Driver `code/pj_vivarium.py`:** `build_measured_vivarium` (`:75`), `reduce_counts` (`:96`),
  `sim_snapshots` (`:119`, Aer `save_statevector`), `schedule_vivarium_selective_dd` (`:162`, DD on
  `viv_witness_qubits`), `run_arm` (`:200`, ONE measured circuit/arm), inline PJ2 schema →
  `research_runs/pj2/`. Sim vs HW = `args.backend is None`; `_SV_MAX_QUBITS=27`. Imports PJ0 infra by name.
- **Renderer `analysis/pj_vivarium_render.py`:** `build_data` (`:41`), `render_html` (`:242`, inline
  template, `const DATA` swap), `render_witness_png` (`:254`).
- **First live run (the motivation):** `ibm_kingston`, W12/track6/steps4, chain twoq_err_max 0.0076 /
  readout_max 0.0178; barren witness **+0.732 SURVIVES**, vivarium **−0.058 at-null**, germ_coupled
  **−0.006 at-null**; sim gives all three at ceiling (+1.000). Confounds: per-arm transpile, N=1.

---

## 6. File plan

Extend `code/pj_qalife.py` + `code/pj_vivarium.py` + `analysis/pj_vivarium_render.py`. All new code
strict-typed, PEP-8, `from __future__ import annotations`. PJ0/PJ1 + the faithful reproduction untouched.

### 6.1 `code/pj_qalife.py` — parameterize `build_vivarium` (dial + ladder + buffer)

- **Signature additions:** `intensity: float = 1.0`, `bio_level: int = _VIV_MAX_LEVEL`, `buffer: int = 0`.
  Add `_VIV_MAX_LEVEL = 6` and a `_VIV_RUNGS` mapping (level → which of forage/eat/bud/death/state-motility/
  hard_select is on). `bio_level` enables rungs cumulatively; `intensity` scales all bio angles.
- **Layout:** thread `buffer` into the soma offsets — `viv_body_q`/`viv_food_q`/`viv_energy_q`/`viv_bath_q`/
  `viv_fit_q` shift by `+buffer`; `viv_segment_len(..., buffer=0)` adds `buffer`. Witness/gene indices
  unchanged (germ + genes stay at the front; buffer sits between genes and body).
- **Intensity scaling:** forage `rxx(λ·hop)/ryy(λ·hop)`; energy-hop control gate angle `λ·hop`; **eat/bud**
  become partial: `RXGate(λ·π).control(2)` on `[body, food, energy]` / `[energy, body, neighbour]` (Toffoli
  at λ=1, identity at λ=0) + the `cx` food-consume gated the same way; death `cry(2·asin(√(λ·g)))`. Guard
  λ=0 → skip the gate entirely (exact identity, so the germ is provably untouched).
- **`bio_level` gating:** wrap each life-cycle block in `if level >= rung`. Level 0 builds germ + genome +
  expression + the idle body placement only (no life cycle) — the "germ-only, idle body" baseline that the
  PJ2 live run showed sits at +0.732.
- **`vivarium_coupling_report`:** extend to accept `buffer`; assert buffer qubits are gate-free
  (`buffer_idle=True`). Selftest gains: (viii) `back_action=False` at every `bio_level`; (ix) λ=0 build has
  no gate on any soma qubit (pure germ); (x) buffer qubits idle.
- **CLI (`--vivarium`):** add `--bio-level`, `--intensity`, `--buffer`. Defaults reproduce PJ2.

### 6.2 `code/pj_vivarium.py` — fixed layout, repeats, and the sweep

- **Globals:** `REPEATS=3`, `BIO_MAX=6`, `INTENSITY_POINTS=(0.0,0.25,0.5,0.75,1.0)`, `BUFFER=0`.
- **`build_measured_vivarium`:** thread `bio_level`, `intensity`, `buffer`.
- **Fixed shared layout:** `pin_layout(backend, width, track, traits, buffer)` — transpile the **richest**
  circuit (`bio_level=MAX, λ=1`) once with opt-3, read `final_index_layout()`, and transpile every sweep
  point with that `initial_layout` (via a small pass or `transpile(..., initial_layout=...)`), then apply
  `schedule_vivarium_selective_dd` on the pinned germ physical qubits. Records the pinned germ qubits in
  `meta.pinned_germ_physical`.
- **`--repeats R`:** loop each measured point R times; aggregate witness mean/σ (+ shot-noise in quadrature).
- **`--bio-sweep`:** for `level in 0..BIO_MAX` (optionally also `--intensity-scan` over `INTENSITY_POINTS`),
  build → (fixed layout) → run R repeats → witness ± σ + survives; print the curve and the **max level/λ
  that still SURVIVES**. Bank schema `sweep: [{bio_level, intensity, buffer, witness_mean, witness_sigma,
  null_mean, signal, survives, alive}]` + `meta` (pinned layout, repeats, chain calib).
- **`--buffer-scan`:** at a fixed mid bio_level, sweep `buffer ∈ {0,2,4}` (and DD on/off) → the mitigation
  table (AC-PJ2.1.7).
- **CLI:** `--bio-level`, `--intensity`, `--buffer`, `--bio-sweep`, `--intensity-scan`, `--buffer-scan`,
  `--repeats`, `--fixed-layout/--no-fixed-layout`. Single-point runs keep the PJ2 3-arm behaviour.

### 6.3 `analysis/pj_vivarium_render.py` — the frontier figure + level slider

- **`render_frontier_png`:** witness vs `bio_level` with error bars, the `k·σ` survive line, and (if scanned)
  a witness-vs-λ panel → `research/pj2_vivarium/pj2_richness_frontier.png`.
- **Demo:** add a biology-level control to the spectacle so the viewer sees the body do more as the level
  rises and the witness meter approach the collapse line. Consumes the `sweep` block; self-contained.

### 6.4 `research/pj2_vivarium/` — updated artifacts

- `pj2_richness_frontier.png`, updated `index.html`, updated `CONCLUSION.html` (the frontier + the honest
  physical-attribution note), `CORRECTNESS.md` (the three new selftest checks).

---

## 7. Implementation steps

1. Parameterize `build_vivarium` (`intensity`, `bio_level`, `buffer`) with exact-identity guards at λ=0 and
   per-rung gating; thread `buffer` through the layout helpers + `viv_segment_len`.
2. Extend `vivarium_coupling_report` + `--selftest` (checks viii/ix/x: barrier-holds-at-every-level,
   λ=0-is-pure-germ, buffer-idle). Iterate to `SELFTEST PASS`.
3. `--dump-circuit` at a few `(bio_level, λ, buffer)` to eyeball the ladder + scaled angles.
4. Driver: `pin_layout` + fixed-layout transpile path; `--repeats`; `build_measured_vivarium` threading.
5. `--bio-sweep` (+ `--intensity-scan`, `--buffer-scan`); the sweep schema + the "max surviving level" print.
6. Sim the sweep (small W, noise model or statevector for the ceiling; a fake-noisy backend for the curve
   shape) → confirm λ=0/level-0 sits at the ceiling and the witness falls monotonically as biology rises.
7. Renderer: frontier PNG + demo level slider.
8. Live sweep on `ibm_kingston` (developer): fixed layout, repeats, `--bio-sweep` at W12 → the real frontier
   + the buffer-scan mitigation table; write `CONCLUSION.html`.

---

## 8. Manual verification (no tests; static + sim + one live sweep — CD-7)

- `python code/pj_qalife.py --vivarium --selftest` → all PJ2 checks + viii/ix/x green at W{2,4,12};
  PJ0 (`--selftest`) and PJ1 (`--arena --selftest`) still pass.
- `python code/pj_qalife.py --vivarium --width 4 --track 6 --bio-level 0 --dump-circuit` → **no gate on any
  soma qubit** (pure germ); `--bio-level 2 --intensity 0.5 --dump-circuit` → forage+eat present, angles
  halved; `--buffer 4 --dump-circuit` → 4 idle spacer qubits, witness set unchanged.
- `python code/pj_vivarium.py --bio-sweep --width 4 --track 5 --repeats 3` (sim) → witness vs level with σ;
  level 0 at ceiling; prints the max surviving level.
- `python code/pj_vivarium.py --buffer-scan --width 4 --track 5 --bio-level 3` (sim) → witness vs buffer.
- `python analysis/pj_vivarium_render.py --run-glob 'research_runs/pj2/*sweep*sim*.json'` → frontier PNG +
  demo with the level slider; self-contained (no external refs).
- Confirm `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py` unchanged (`git diff` empty).
- Live (developer): `python code/pj_vivarium.py --backend ibm_kingston --bio-sweep --width 12 --track 6
  --repeats 3 --fixed-layout --shots 8192` → the real richness-vs-witness frontier banked; then the
  buffer-scan; render + `CONCLUSION.html`.

---

## 9. Risks

- **R1 — even level 1 may kill the witness at W12.** If any body activity crosstalks the germ hard, the
  frontier is at level 0. Mitigations: `--buffer`/DD (AC-PJ2.1.7), lower `--intensity` (λ<1 gentle biology),
  smaller W for headroom. **Honest fallback:** "the frontier is level 0 / λ≈0 at W=12 on this chip" is a
  real, reportable result — the whole point is to *measure* where it dies.
- **R2 — fixed layout may not fit the richest circuit's routing at every level.** The pinned `initial_layout`
  is sized for the richest point; leaner levels use a subset — fine (idle qubits). If routing differs,
  document that the germ physical qubits are held constant (the thing that matters for attribution).
- **R3 — partial eat/bud (`RX(λπ).control(2)`) changes the diagonal story vs the Toffoli.** Acceptable:
  eat/bud are diagonal narrative (CD-4); only the *witness* is the claim, and λ=1 must equal PJ2 (Toffoli).
  Guard: at λ=1 `RX(π).control(2)` ≡ CCX up to a global/relative phase that does not touch the germ witness.
- **R4 — qubit budget with buffer.** `nq = W + traits + buffer + 3·track + n_food`. W12/track6/buffer4 = 39;
  still under the ~107 clean chain. `gated_chain` fail-closes.
- **R5 — sim can't show crosstalk (noiseless).** The *shape* of the frontier is a hardware effect; sim
  confirms only the logical monotonicity (λ↑/level↑ ⇒ more gates) and the λ=0 ceiling. Use a fake-noisy
  backend for a qualitative curve; the real frontier is the live sweep (as PJ2 established, sim is too benign).
- **R6 — backward-compat regressions.** PJ2 defaults must reproduce current behaviour; keep the PJ2 selftest
  green and diff a `bio_level=MAX,λ=1,buffer=0` build against the pre-refactor build.

---

## 10. Open questions — proposed defaults (developer answers; I do not self-approve)

- **OQ-1 (primary sweep axis) — PROPOSAL: the operator ladder `bio-level` is primary; `intensity λ` is the
  secondary fine dial.** The ladder answers "which biological process breaks the witness"; λ answers "how
  gently can that process run and still survive". Default: `--bio-sweep` over levels; `--intensity-scan`
  opt-in. **Default: ladder primary, λ secondary.**
- **OQ-2 (partial eat/bud encoding) — PROPOSAL: `RX(λ·π).control(2)`** (smooth Toffoli), λ=1 ≡ PJ2. Keep the
  hard `ccx` as the λ=1 special case for an exact PJ2 match if the phase matters. **Default: controlled-RX.**
- **OQ-3 (buffer default) — PROPOSAL: `buffer=0` default; sweep {0,2,4} in `--buffer-scan`.** Buffer costs
  qubits, so off by default; the scan quantifies the crosstalk mitigation. **Default: 0, scan on request.**
- **OQ-4 (who runs HW) — PROPOSAL: developer runs the live sweep** (as PJ2), sim first. W12/track6, repeats 3.
- **OQ-5 (repeats) — PROPOSAL: 3 for sweeps** (error bars without burning QC); single-point runs default 1.
- **OQ-6 (fixed layout default) — PROPOSAL: ON for sweeps, OFF for single-point 3-arm runs** (so PJ2's
  original arm behaviour is unchanged). **Default: `--fixed-layout` implied by `--bio-sweep`.**

---

## 11. Ground rules honored

- Every AC traces to the PJ2 substrate + the live-run read + the epic richness question; none invented.
- Concrete file paths + line-grounded references (§5, §6).
- Epic cross-cutting decisions applied (§4); CD-1 in-place extension.
- New operators, arena, and heavier EM kept out of scope (§3); the refactor is additive + backward-compatible.
- Strict types + PEP-8; no raw SQL / templates (N/A).
- No tests (CD-7): static `--selftest` + `--dump-circuit` + `--sim` + one live sweep + written conclusion.
- `qalife.py`/`run_qalife.py`/`pj_run_qalife.py`/`pj1_run_arena.py` byte-stable; PJ0/PJ1 selftests green.
- `Status: Draft` — the developer flips to Approved, then `/implement-feature`.
```
