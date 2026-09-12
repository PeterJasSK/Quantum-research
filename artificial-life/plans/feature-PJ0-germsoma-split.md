# Feature Plan — PJ0: Germ/soma split (Weismann barrier) — the first new biology

**Ticket:** PJ0 (stage, not a GitHub issue — this research repo decomposes epics into stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09), stage **P3** (richness investigations)
**Candidate source:** `artificial-life/plans/P3-candidate-movess.md` §"PJ0 · Germ/soma split" + "PJ0 · build plan, deliverables & acceptance" + ladder rungs 0–2 + "PJ · the sim tests" (Test 1)
**Slug:** germsoma-split
**Author:** Claude (Opus)
**Date:** 2026-09-12
**Status:** Complete

> **No tests (repo convention, CD-7).** Verification is `--selftest` (static circuit-structure
> checks) + `--dump-circuit` printing + a written static-correctness evaluation. No test framework,
> no test files.
>
> **No simulation, no hardware runs in this ticket (developer-directed, OQ-4).** PJ0 delivers
> **correct circuit-building code** whose design is proven by **static code evaluation + printing and
> evaluating circuit correctness** — NOT by Aer/statevector sim and NOT by live runs. The actual W
> sweeps (any width) are run by the developer later, outside this ticket.

---

## 1. Summary

PJ0 builds the **first new biology** in the artificial-life program: a single-lineage **germ/soma
organism** that implements the Weismann barrier — the genotype is the *immortal germ line* (carries
the entanglement witness, kept coherent), the phenotype is the *mortal soma* (expresses the trait,
then dies **in isolation** so its death costs the germ-line witness ~zero). It fixes the exact wound
P2 exposed: the faithful damping model entangles the mortal phenotype to the immortal genotype
(`cx(g,p)`) then dissipates it, so **body-death irreversibly decoheres the gene-witness** (that is why
the damping ceiling collapsed to W\* ∈ [4,8)). PJ0 severs that coupling.

**Developer directive (baked into this plan):** unlike every other P3 move (which CD-1 makes a plug-in
operator on the faithful `qalife.py`), PJ0 is built as a **separate experimental circuit pair** —
new files **`code/pj_qalife.py`** (model) + **`code/pj_run_qalife.py`** (driver). The faithful
reproduction (`qalife.py`/`run_qalife.py`) is left **untouched**. PJ0's file pair is the substrate the
whole PJ line (PJ1 arena: competition, multiple lineages, joint witness) will extend later — so it is
structured for that future from the start, while building **only** the single-organism germ/soma here.

Three engineering moves (P3-candidate §"The fix (Idea A)"), realized as ladder **rungs 0–2**:

1. **Rung 0 — pass the gene first.** Build the entire germ-line GHZ chain (all clones + mutations)
   **before any death**. In the new file this is structural: genotype block built fully, then soma block.
2. **Rung 1 — express the trait separably + kill the body in isolation.** Set the phenotype's ⟨σz⟩ from
   the genotype value as a **separable** diagonal state (no `cx(g,p)` back-action, reuse the unitary
   arm's `ry(aged)`), then apply a **phenotype-only** soma death. **Static Test 1** (the sim-Test-1
   premise, proven statically): the built circuit contains **no gate coupling any soma qubit
   (phenotype/bath) to any genotype qubit**, so soma death shares no qubit with the germ line and cannot
   touch the genotype witness. THE gate on the whole premise — verified by circuit-structure inspection,
   not by a statevector run.
3. **Rung 2 (the acceptance gate, Q6) — natural decoherence + selective DD.** Soma dies by its own T1
   decay toward `|0⟩` (no operator, no bath); apply **dynamical decoupling to the genotype qubits only**
   (Weismann's barrier built physically). The aging clock is **deliberately not forced rigid** — the
   scheduler's natural idle pattern produces **irregular** lifespans (a grandparent soma may outlive a
   grandchild), which is *more alive*, not a bug. What must be bounded is the **scale** of that
   irregularity (Q6): PJ0 statically measures the aging-order deviation from the scheduled circuit; small
   deviation is accepted as a feature; only if it blows past a studied tolerance does it get pulled back
   (targeted delays) or **cut to `local_damping`** (rigid controlled decay). **Soma death is a
   parameter** — `natural` (lively, irregular, the gate) and `local_damping` (rigid, controlled rate,
   +bath, reference/fallback) are both coded and selectable.

The certified quantum claim stays the **genotype-only** witness `⟨X^⊗W⟩` (soma qubits are honestly
diagonal, excluded from the witness). **Width W is a free CLI parameter** — W12 is the anchor/default
(12 individuals, safely inside the proven-alive unitary regime, P2: W\*=24), but the code must build a
correct circuit at **any** W the developer later runs, including deeper (OQ-3). This ticket proves the
design is correct at representative widths by static evaluation + circuit printing; it runs neither sim
nor hardware.

**PJ1 is explicitly out of scope** (§3) but the file pair is designed to admit it (rungs 3–6).

---

## 2. Acceptance criteria (from P3-candidate-movess.md §"PJ0 · build plan, deliverables & acceptance")

Copied from the candidate doc's acceptance list (a)–(f) and deliverables (1)–(6); IDs added.

All ACs are met by **static code evaluation + printed/evaluated circuits** — no sim, no hardware (OQ-4).

- [x] **AC-PJ0.1 (deliverable 1 + acceptance a, THE gate):** germ/soma model implemented in
  `code/pj_qalife.py` with `--selftest` green, where selftest is a set of **static circuit-structure
  assertions** (§6.1). Central check — **Static Test 1**: in the built `QuantumCircuit`, **no gate has
  both a genotype qubit and a soma (phenotype/bath) qubit in its operands** (soma death is qubit-disjoint
  from the germ line → cannot touch the witness, I4). Proven by walking `qc.data`, not by a statevector.
  **Covered by** `code/pj_qalife.py:114` (`build_germsoma`, two-phase), `:245` (`germsoma_coupling_report`
  walks `qc.data`), `:335` (`--selftest` check i), `:408` (`run_selftest`); `SELFTEST PASS` at W{2,4,12},
  `circuits/selftest_output.txt`.
- [x] **AC-PJ0.2 (acceptance b, I5) — HARD, BOUNDED not rigid (Q6):** statically compute the **aging-order
  deviation** from the `natural` scheduled circuit — for each soma, the shift between its realized idle
  rank (idle-time order) and its birth rank, in generations; report `max_deviation` + the per-soma table.
  Aging need **not** be monotone — small irregularity (grandparent outliving grandchild) is accepted as
  lifelike. Gate: `max_deviation ≤ AGING_ORDER_TOL` (studied parameter, proposed default **2
  generations**). If exceeded → pull outliers back with **targeted** delays (bounded, not full rigidity)
  or **fall back to `local_damping`** (rigid, age = controlled parameter, satisfies any tolerance). All
  static — read the scheduling analysis, do not run. **Covered by** `code/pj_qalife.py:287`
  (`aging_order_deviation`), `code/pj_run_qalife.py:61` (`AGING_ORDER_TOL=2`), `:193` (`schedule_report`
  gate on `max_deviation`).
- [x] **AC-PJ0.3 (acceptance c, deliverable 5, I6) — HARD:** selective DD verified by inspecting the
  **scheduled** circuit — DD sequences land on **genotype (germ-line) qubits only**, phenotype qubits
  **DD-free** (the physical Weismann barrier). Static check. **Covered by** `code/pj_run_qalife.py:122`
  (`schedule_with_selective_dd`, `PadDynamicalDecoupling(qubits=germ_physical)`), `:193`
  (`schedule_report` asserts `DD on soma = 0`).
- [x] **AC-PJ0.4 (acceptance d, deliverable 6, I7):** separable-phenotype faithfulness documented **and**
  the entangled-phenotype A/B proven **statically** — the `phenotype='entangled'` build re-introduces
  `cx(g,p)` (so it violates Static Test 1 and would cost the witness), while both builds set the **same**
  diagonal soma ⟨σz⟩ by construction (same `ry(aged)` angle). Shown by circuit diff + the closed-form
  angle, not by a run. **Covered by** `code/pj_qalife.py:173` (entangled `cx(g,p)` branch), `:225`
  (`soma_z_closed_form`), `:377` (`--selftest` check v: fails Static Test 1, same `ry` angle);
  `circuits/W4_entangled_AB.txt` (mixing `cx [g,p]`) vs `circuits/W4_natural.txt`.
- [x] **AC-PJ0.5 (acceptance e, I8):** soma-death parameterization documented for **both** modes —
  natural-decay (gate) reported as a **T1 band** (min–max over calibration snapshots; drifts run-to-run,
  I8) via the per-soma `delay`/T1 knob; local-damping (reference) as a **controlled rate** `g_eff(age,γ)`.
  `meta.calibration`/`meta.t1_band` fields present in the driver's JSON schema for the developer's runs.
  **Covered by** `code/pj_qalife.py:114` (`soma_death` param, `local_damping` `g_eff` branch),
  `code/pj_run_qalife.py:260` (`_run_schema` with `meta.calibration`/`meta.t1_band`, `:270`);
  `CORRECTNESS.md` §"Soma-death parameterization".
- [x] **AC-PJ0.6 (deliverable 2):** Static Test 1 result recorded as a **written correctness evaluation**
  (`research/pj0_germsoma/CORRECTNESS.md`) with the printed circuits and the qubit-disjointness argument.
  **Covered by** `research/pj0_germsoma/CORRECTNESS.md` + `research/pj0_germsoma/circuits/*.txt`
  (W{2,4,12} × {natural, local_damping}, W4 entangled A/B, W4 none control, selftest output).
- [x] **AC-PJ0.7 (deliverable 3 + 4, acceptance f — design-level, no run):** `code/pj_run_qalife.py` builds
  a transpile-ready, chain-quality-gated, measured germ/soma circuit at **any W** (W12 anchor) on the
  longest low-error chain with genotype/soma blocks physically separated (I4); correctness shown via
  `--dump-circuit`/`--draw-only` + scheduled-circuit inspection. The actual witness-vs-W runs and the
  matched-W-vs-P2-damping comparison are the developer's to run later (Q3) — the driver emits the schema
  + comparison hooks, but banks no run data in this ticket. **Covered by** `code/pj_run_qalife.py:103`
  (`build_measured_germsoma`, H genotype only), `:239` (`gated_chain` fail-closed CD-5), `:122` (opt-3
  transpile + schedule), `:153` (`dump_circuit`, never submits), `:260` (`_run_schema` comparison hooks).

---

## 3. Out of scope

- **The entire PJ1 arena (ladder rungs 3–6):** multiple lineages (L≥2), coherent energy-transfer
  competition, differential (gated-clone) reproduction, the joint cross-lineage witness, QRNG-chosen
  encounters, the P4 web-demo feed. PJ0 is single-lineage only. The file pair is *structured* to admit
  these later (§6) but **none are built here**.
- **PJ2 (multi-run classical-stitched ages)** and **PM-series / M-series** moves.
- **Work-package EM as a standalone deliverable.** PJ0 pulls in *selective DD* (EM1, targeted) as the
  physical germ/soma barrier; the broader EM stack (readout mitigation, ZNE, parity post-selection) and
  the W=5/W=6 damping-W\* run are a separate parallel work-package, not PJ0.
- **Teleport / entanglement-swap routing** — DEAD (P3-candidate I9), not touched.
- **Any change to the faithful `qalife.py` / `run_qalife.py`.** PJ0 is a separate file pair; the
  reproduction stays byte-stable.

---

## 4. Cross-cutting decisions applied (from epic §3)

- **CD-1 (main-folder minimalism) — deliberate, developer-directed deviation.** CD-1 says new richness
  goes in as a *plug-in operator* on `qalife.py`, keeping `code/` at exactly four files. The developer
  directs PJ0 as a **separate `pj_qalife.py` + `pj_run_qalife.py` pair** instead — a conscious
  experimental fork so the honesty-anchor reproduction is never perturbed and PJ gets its own extensible
  substrate. This plan honors the directive and records the resolution in OQ-1. **`qalife.py` is not
  modified in any way (Q1).** `pj_qalife.py` may `import qalife as q4` and call its **pure helpers**
  (witness math `xbasis_witness_from_counts`/`entanglement_depth`, `_z_geno_chain`, the `AGING_DELTA`/
  `DAMP_GAMMA`/`ALIVE_THRESH` constants) as a read-only library — zero edits to `qalife.py`. The two new
  files sit in `code/` beside the reproduction; the germ/soma **build** logic (layout, two-phase build,
  soma death) is written fresh in `pj_qalife.py`, not by editing the reproduction.
- **CD-3 (witness is the only quantum claim).** PJ0's sole quantum observable is the **genotype-only**
  `⟨X^⊗W⟩`; the separable phenotype ⟨σz⟩ is declared classical plumbing. The separable null is reported
  alongside and must sit ≈0.
- **CD-4 (honesty invariant).** The trait (alive/dead) is classical by the paper's own text, so a
  separable diagonal phenotype is a *faithful* expression, not a cheat (I7). The A/B (AC-PJ0.4) makes
  this an experiment, not an assertion.
- **CD-5 (significance + chain-quality gates).** Reuse `entanglement_depth` (k=2 headline, k=3 reported)
  and the fail-closed chain-quality gate on hardware.
- **CD-6 (QRNG certified, fail-closed).** Hardware mutation angles from `qrng_client.py`, fail-closed;
  PJ0 runs faithful (MUT_SCALE=0, clean GHZ) so the germ/soma effect is isolated (OQ-5).
- **CD-7 (verification without a test framework) — no sim in this ticket (Q4).** Verification is static:
  `--selftest` (circuit-structure assertions) + `--dump-circuit` printing + the written correctness
  evaluation. No Aer/statevector sim, no hardware run here (the developer runs the sweeps later).

---

## 5. Verified codebase facts (grounding the plan)

Read from `code/qalife.py` and `code/run_qalife.py` (line numbers current as of 2026-09-12):

- **Layout is index-mapping functions:** `geno_q(k)=2k` (`qalife.py:60`), `pheno_q(k)=2k+1` (`:64`),
  `bath_q(width,k)=2W+k` (`:68`) — genotype/phenotype **interleaved** stride-2, one fresh bath per
  individual (never reset → no dynamic circuit).
- **Genotype chain + mutation:** founder `ry(π/2)` on `g_0`, then `cx(g_{k-1},g_k)` clone +
  `ry(theta_k)` mutation (`build_population`, `qalife.py:121–130`).
- **Unitary (separable) phenotype:** `angle0=acos(z_geno[k])`, `aged=max(0, angle0−delta·age)`,
  `ry(aged, p)` — a product-state phenotype driven toward `|0>` by aging (`qalife.py:133–137`). **This
  is exactly the separable diagonal soma PJ0 reuses.**
- **Damping arm (the wound):** `cx(g,p)` (`:139`, the entangling coupling PJ0 **drops**) then
  `g_eff=1−(1−gamma)^age`, `cry(2·asin√g_eff, p, bath)`, `cx(bath, p)` (`:143–147`). **PJ0's local-soma
  death is this arm with the `cx(g,p)` at :139 removed and the bath attached to the phenotype only.**
- **Analytic genotype ⟨σz⟩:** `_z_geno_chain(width, thetas, founder_equator)` (`qalife.py:87`) — reused
  to prepare the separable phenotype and for the classical surrogate.
- **Witness math:** `xbasis_witness_from_counts(counts, qubits)` (`qalife.py:217`) returns
  `(joint, separable)` over an **arbitrary qubit list** — so PJ0 passes genotype qubits only.
  `entanglement_depth` (`:239`), `classical_surrogate_z` (`:251`).
- **Driver measurement:** `build_measured` (`run_qalife.py:100`) applies `H` to genotype qubits (→ X
  basis = witness); the damping arm additionally H's phenotypes (they carry half the GHZ). **PJ0's
  separable phenotype does NOT carry the GHZ → H genotypes only.**
- **Hardware plumbing to reuse:** `gated_chain` (chain-quality gate, `run_qalife.py:152`),
  `qrng_thetas` (`:81`), sampler dispatch + counts assembly (`:276–287`), `connect`/`run_sampler` via
  `pipeline_common`, `layout.best_chain`.
- **No plotting infra** in `code/` (P1 built `analysis/plot_baseline.py`); PJ0 reuses that analysis
  pattern for its banked dataset.

---

## 6. File plan

Two new files in `code/` (developer-directed pair, CD-1 deviation) + one correctness-evaluation
directory. All new code is **strict-typed, PEP-8**, `from __future__ import annotations`, mirroring
`qalife.py` style. `qalife.py` and `run_qalife.py` are **not edited** (Q1).

### 6.1 New — `code/pj_qalife.py` (the germ/soma model + `--selftest`)

Self-contained model file, mirroring `qalife.py`'s structure. Imports qiskit + stdlib; reuses
`qalife.py` **only** for pure helpers (`xbasis_witness_from_counts`, `entanglement_depth`,
`_z_geno_chain`, `AGING_DELTA`, `DAMP_GAMMA`, `ALIVE_THRESH`) via `import qalife as q4`.

**Layout — SEPARATE blocks, organism-offset parameterized (OQ-2 option B + PJ1 scaling hook):**
Layout is a function of an **organism index `o`** (PJ0 builds `o=0` only; PJ1 loops `o=0..L-1`):
- `segment_len(width, has_bath) = 2*width + (width if has_bath else 0)` — one organism's qubit span:
  germ (W) + soma (W) [+ bath (W) only in local-damping mode]. Natural-decay mode has **no bath** →
  segment is `2W` (leaner → more organisms per chain).
- `organism_base(o, width, has_bath) = o * segment_len(width, has_bath)`.
- `geno_q(o, k) = organism_base(o,…) + k` — germ block, **contiguous** `base..base+W-1`. Gene-passing
  clone `cx(geno_q(o,k-1), geno_q(o,k))` is a **nearest-neighbor** gate down this contiguous chain — the
  clean GHZ ladder the witness reads (better than interleaved, which routes the clone around a soma qubit).
- `pheno_q(o, k) = organism_base(o,…) + width + k` — soma block, physically apart from the germ line.
- `soma_bath_q(o, k) = organism_base(o,…) + 2*width + k` — soma bath (local-damping mode only).
- Rationale: separate blocks minimize the crosstalk path body-death could bleed into the germ line (I4);
  contiguous germ block keeps gene-passing nearest-neighbor. Only the entangled-phenotype A/B mode
  re-introduces a (now long-range) `cx(g,p)`.
- **PJ1 hook (not built here):** organisms tile as adjacent segments; a resource qubit + boundary
  coherent-coupling (partial-SWAP between neighbors) is where competition lands. PJ0 leaves a
  `# PJ1: resource qubit + boundary coupling here` marker + the offset functions, builds none of it.

**`build_germsoma(width, steps, thetas, *, phenotype='separable', soma_death='natural',
founder_equator=True, delta=AGING_DELTA, gamma=DAMP_GAMMA, organisms=1, annotate=False)
-> QuantumCircuit`** — two-phase build (this **is** rung 0, structurally). `organisms=1` here (PJ0);
the `o` loop is the PJ1 hook. `soma_death` **defaults to `natural`** (the acceptance gate, Q6); the loops
below run per organism `o` (only `o=0` for PJ0):
- **Phase 1 — pass the gene first (germ line, fully, before any death):** loop `k`: founder
  `ry(π/2, geno_q(o,0))` (if `founder_equator`), else `cx(geno_q(o,k-1), geno_q(o,k))` (nearest-neighbor
  on the contiguous germ block); then `ry(thetas[k], geno_q(o,k))` mutation. Barrier `"germline"`.
- **Phase 2 — express + kill the soma (isolated):** loop `k`, `age = max(0, steps-k)`:
  - `phenotype='separable'` (default): reuse the unitary-arm math — `z=_z_geno_chain(...)[k]`,
    `angle0=acos(z)`, `aged=max(0, angle0−delta·age)`, `ry(aged, pheno_q(o,k))`. No `cx(g,p)`.
  - `phenotype='entangled'` (I7 A/B mode): `cx(geno_q(o,k), pheno_q(o,k))` first (restores the wound),
    then the same soma death — used only to *demonstrate* it costs the witness.
  - Soma death on the phenotype qubit **only**:
    - `soma_death='natural'` (**default / acceptance gate, Q6**): emit **no** operator (T1 idle is the
      death); the aging clock is realized in the driver via per-soma `delay` scaled by `age` + selective
      DD on the germ line (rung 2, I5/I6). No bath qubits → leaner segment (`2W`).
    - `soma_death='local_damping'` (**kept as coded reference/fallback**): if `age>0`,
      `g_eff=1−(1−gamma)^age`, `cry(2·asin√g_eff, pheno_q(o,k), soma_bath_q(o,k))`,
      `cx(soma_bath_q(o,k), pheno_q(o,k))` — the damping arm **with `cx(g,p)` removed**, bath scoped to
      the phenotype. Controlled rate, reproducible; the reference the natural arm is compared to.
    - `soma_death='none'`: no death — the **control arm** for Static Test 1 (`ry(angle0, p)`, age ignored).
  - Barrier `"soma{o},{k}"`.
- **No interaction sweep, no competition** (single organism). The organism `o` loop + the boundary
  resource/coupling marker (§6.1 layout) are the documented PJ1 extension points — arena added without a
  rewrite, but **not** implemented (§3).

**Observables / helpers (build-time + static analysis; no execution):**
- `witness_qubits(width, organisms=1) -> list[int]` → `[geno_q(o,k) for o in range(organisms) for k in
  range(width)]` (genotype-only; the soma is diagonal, CD-3). PJ0: `o=0`. This is the set the developer's
  later runs feed to `xbasis_witness_from_counts`.
- `soma_z_closed_form(width, steps, thetas) -> list[float]` — the separable soma ⟨σz⟩ per individual from
  `_z_geno_chain` + aging (closed form; used by `--selftest` check (iv) and the A/B ⟨σz⟩-equality claim).
- `aging_order_deviation(scheduled_qc, width, organisms=1) -> dict` — static aging-clock analyzer: from
  the **scheduled** circuit's per-soma idle durations, returns each soma's realized-idle-rank, its
  birth-rank, the per-soma shift, and `max_deviation` (generations). Feeds AC-PJ0.2's bounded gate — no
  execution, reads the scheduling analysis.
- `germsoma_coupling_report(qc, width) -> dict` — the static analyzer: walks `qc.data`, returns
  geno/soma qubit-disjointness (Static Test 1), gate ordering, witness-qubit set, per-operator gate
  counts. Drives `--selftest` and the printed correctness report. **No statevector helper** — PJ0 does
  not compute witness values; the developer's runs do.

**`--selftest` (CD-7 verification — STATIC circuit-structure checks, no sim):** walk the built
`QuantumCircuit.data` and assert, at representative W (e.g. 2, 4, 12) —
(i) **Static Test 1 (the honesty anchor):** no instruction's qubit operands mix a genotype qubit with a
soma (phenotype/bath) qubit, for `soma_death ∈ {local_damping, natural, none}` — soma death is
qubit-disjoint from the germ line;
(ii) **ordering (rung 0):** every genotype-block gate (founder/`cx`/mutation) precedes every soma-block
gate in `qc.data` — the gene is fully passed before any death;
(iii) **witness readout isolation:** in the measured build, `H` is applied to genotype qubits only
(separable mode) — soma qubits never enter the witness qubit set;
(iv) **separable ⟨σz⟩ closed form:** the soma `ry` angle equals `max(0, acos(_z_geno_chain[k]) −
delta·age)` (matches the unitary arm exactly), asserted against the recomputed value;
(v) **entangled A/B contrast:** `phenotype='entangled'` DOES contain a `cx(g,p)` (so it fails check (i))
while carrying the **same** soma `ry` angle as (iv) — proving the entanglement is gratuitous.
Print per-check `OK` + `SELFTEST PASS`, exit 0/1 like `qalife.py`. All checks are structural — they read
the circuit, they do not execute it.

**`main()` (static-eval CLI, no sim):** `--width --steps --soma-death --phenotype --seed --selftest
--dump-circuit`. Default action builds the germ/soma circuit at the given W and **prints** it (text
draw) with a gate→Darwinian-operator legend, plus a **static correctness report**: qubit-block map,
Static-Test-1 result (geno/soma disjoint? yes/no), ordering check, witness-qubit set, gate counts,
separable ⟨σz⟩ per individual (closed form). No statevector, no counts, no `research_runs/` run JSON —
it evaluates and prints the design's correctness.

### 6.2 New — `code/pj_run_qalife.py` (the germ/soma hardware driver — build + evaluate, no run here)

Mirror `run_qalife.py` structure. `qalife.py`/`run_qalife.py` are not edited (Q1); `pj_run_qalife.py`
imports `pj_qalife`, `qalife` (pure helpers), and the same infra `run_qalife.py` uses (`pipeline_common`
connect/run_sampler, `layout.best_chain`, `qrng_client`). Module globals: `INTERACTION="none"`,
`REPEATS`, `K=2.0`, `MUT_SCALE=0.0` (Q5), chain-quality thresholds, plus new `SOMA_DEATH="natural"`
(Q6 gate; `local_damping` selectable as reference), `AGING_ORDER_TOL=2` (studied bound on aging-order
deviation, Q6), `PHENOTYPE`, `SELECTIVE_DD=True` flags. **Width is a CLI param — any W (Q3), W12 default.**

The run path (sampler submission) is **wired but not exercised in this ticket** — the developer runs the
sweeps later (Q4). What this ticket delivers and evaluates statically:

- **`build_measured_germsoma(width, steps, thetas, soma_death, phenotype, annotate=False)`** — build via
  `pj_qalife.build_germsoma`, then `H` on **genotype qubits only** (separable soma stays in Z;
  entangled A/B mode H's phenotypes too), add `ClassicalRegister`, measure. Correctness shown by
  `--dump-circuit`.
- **Transpile-readiness + chain-quality gate:** reuse `gated_chain` (fail-closed CD-5) and the
  opt-3 preset pass manager so the built circuit is submit-ready at any W; evaluated by printing the
  transpiled circuit, **not** by submitting.
- **Selective DD (rung 2, I6, AC-PJ0.3) — HARD:** after layout/routing, insert `PadDynamicalDecoupling`
  (XY4/`XX`) **targeted at the genotype physical qubits**; leave phenotype qubits unpadded. If the stock
  pass is not granular enough, a small custom scheduling pass on the genotype register alone. **Verify by
  inspecting the scheduled circuit** that phenotype qubits are DD-free (dump + static check).
- **Natural-decay clock (rung 2, I5, AC-PJ0.2) — HARD, bounded not rigid (Q6):** for
  `soma_death='natural'`, **do not force strict monotone** — let the scheduler's natural idle pattern
  stand (irregular lifespans are the lively feature). Compute the **aging-order deviation** statically
  from the scheduled circuit (per-soma realized-idle-rank vs birth-rank, in generations) via
  `aging_order_deviation(scheduled_qc, width)`; gate on `max_deviation ≤ AGING_ORDER_TOL` (module global,
  default 2). Only if exceeded, insert **targeted** `delay` on the outlier somas to pull them back inside
  tolerance, or fall back to `local_damping`. Minimal forced delay → minimal germ-line idle → smaller
  witness cost than rigid enforcement (§9). Static check — no run.
- **Layout constraint (I4):** ensure `best_chain` maps the genotype block and soma block to physically
  separated regions; add barrier/placement guards so the transpiler cannot recouple them; print the
  chosen physical mapping.
- **`--dump-circuit` / `--draw-only`** parity with `run_qalife.py:dump_circuit`, with a germ/soma
  gate→operator legend (founder / self-replication / mutation / separable-phenotype / isolated-soma-death
  / selective-DD) — the primary correctness-evaluation surface.
- **Run wiring (dormant):** witness qubits = `pj_qalife.witness_qubits(W)`; JSON schema extended with
  `soma_death`, `phenotype`, `selective_dd`, `kept_fraction`, `meta.calibration`, `meta.t1_band`,
  `witness_soma_on`/`witness_soma_off` — present so the developer's later runs bank uniformly. The
  soma-on / soma-off pairing (the hardware analogue of Static Test 1) is coded as a run option, left for
  the developer to execute.

### 6.3 New — `research/pj0_germsoma/CORRECTNESS.md` (the static-correctness evaluation)

No run dataset, no figure (nothing is executed — Q4). Instead a written evaluation:

- The **printed circuits** (`--dump-circuit` text) for representative widths (e.g. W2, W4, W12), each
  soma_death mode, and the entangled A/B — saved as `.txt` under `research/pj0_germsoma/circuits/`.
- The **static-correctness argument**: Static Test 1 (geno/soma qubit-disjoint), gene-first ordering,
  witness-qubit isolation (H on genotype only), separable ⟨σz⟩ closed form, the A/B contrast, selective
  DD on genotype only, natural-decay aging-order monotonicity — each with the concrete evidence
  (`--selftest` output, scheduled-circuit excerpts).
- A note on what the developer runs next (witness-vs-W sweep, matched-W-vs-P2-damping comparison) and the
  JSON fields the driver will bank.

### 6.4 Resulting layout (after PJ0)

```
code/
  layout.py  qrng_client.py        # infra (unchanged)
  qalife.py  run_qalife.py         # faithful reproduction (UNCHANGED — byte-stable)
  pj_qalife.py                     # NEW — germ/soma model + static --selftest
  pj_run_qalife.py                 # NEW — germ/soma driver (build + evaluate; run wiring dormant)
  backlog/ ...
research/
  baseline_P1/ ...                 # P1 reference (unchanged)
  pj0_germsoma/                    # NEW
    CORRECTNESS.md                 #   the static-correctness evaluation
    circuits/                      #   printed circuits (--dump-circuit .txt) per W / mode
```

---

## 7. Implementation steps

1. **`pj_qalife.py` — layout + two-phase `build_germsoma`** (rung 0 + rung 1 separable core). Genotype
   block first, soma block second; `phenotype='separable'`, `soma_death` in
   `{local_damping, natural, none}`. `qalife.py` imported read-only (Q1).
2. **Static helpers** — `witness_qubits`, `soma_z_closed_form`, `germsoma_coupling_report` (the circuit
   analyzer). No statevector helper (Q4).
3. **`--selftest`** — the five static circuit-structure checks in §6.1 (incl. Static Test 1). Iterate
   until `SELFTEST PASS`.
4. **`pj_qalife.main()` static-eval CLI** — build at W2/W4/W12, `--dump-circuit`, print the correctness
   report (disjointness, ordering, witness set, closed-form ⟨σz⟩). No sim (AC-PJ0.1, .6).
5. **Entangled-phenotype A/B** (`phenotype='entangled'`) — static contrast: the build contains `cx(g,p)`
   (fails Static Test 1) while carrying the same soma `ry` angle (AC-PJ0.4).
6. **`pj_run_qalife.py`** — `build_measured_germsoma` (H genotypes only), chain-quality gate + opt-3
   transpile so the circuit is submit-ready at any W; `--dump-circuit` legend. Run wiring present but not
   executed (Q4).
7. **Selective DD** (rung 2, AC-PJ0.3, HARD) — targeted `PadDynamicalDecoupling` on genotype qubits; dump
   the **scheduled** circuit, statically confirm phenotype DD-free.
8. **Natural-decay clock** (rung 2, AC-PJ0.2, HARD — the gate, Q6) — `aging_order_deviation` on the
   scheduled circuit; accept irregular aging within `AGING_ORDER_TOL` (default 2 gen), targeted delays or
   `local_damping` fallback only if exceeded. `local_damping` kept as coded reference arm.
9. **Bank the correctness evaluation** — printed circuits → `research/pj0_germsoma/circuits/`, the
   argument → `CORRECTNESS.md`; document soma-death parameterization / T1-band knob (AC-PJ0.5, .7).

---

## 8. Manual verification (no tests, no sim, no hardware — CD-7 / Q4; all static)

- `python code/pj_qalife.py --selftest` → all five structural checks `OK`, `SELFTEST PASS`, exit 0
  (run for both `natural` and `local_damping`).
- `python code/pj_qalife.py --width 12 --steps 6 --dump-circuit` (default `soma_death=natural`) → prints
  the circuit + correctness report: geno/soma **qubit-disjoint = yes** (Static Test 1), gene-first
  ordering, contiguous germ block (nearest-neighbor clones), witness set = genotype qubits only,
  per-individual separable ⟨σz⟩. No bath qubits present (natural).
- `python code/pj_qalife.py --width 4 --steps 4 --phenotype entangled --dump-circuit` → report shows
  `cx(g,p)` present (disjoint = **no**) with the **same** ⟨σz⟩ angles (A/B contrast).
- `python code/pj_run_qalife.py --dump-circuit --draw-only --widths 12 --steps 6` → annotated germ/soma
  circuit; genotype/soma blocks separated; transpile-ready.
- Inspect the **scheduled** circuit output → selective DD on **genotype qubits only**, phenotype DD-free
  (I6); `aging_order_deviation` reports `max_deviation ≤ AGING_ORDER_TOL` (I5, irregular-but-bounded).
  Read `qc.data` / the scheduling analysis — do not execute.
- Confirm `qalife.py` and `run_qalife.py` are unchanged (`git diff` empty for both).

---

## 9. Risks

- **I4 leakage.** A stray gate / transpiler recoupling bleeds body-death onto the witness → Static Test 1
  fails at build time (the analyzer flags a geno/soma-mixing gate). Mitigations: separate genotype/soma
  blocks, barriers/placement guards, inspect the transpiled circuit. Caught statically here; the physical
  crosstalk residual is the developer's run to measure later.
- **I5 aging-order scramble (natural arm = the gate, Q6) — bounded, not eliminated.** Scheduler sets idle
  by gate placement, not build order → aging order is irregular. **Small irregularity is wanted** (more
  alive). Risk is only a *large* scramble (e.g. a 6-generation inversion). Mitigation: measure
  `max_deviation` statically, gate on `AGING_ORDER_TOL` (default 2 gen); targeted delays on outliers, or
  cut to `local_damping` (rigid). The tolerance value itself is a **studied parameter** — the developer
  tunes it from the measured deviation vs W.
- **Natural-decay drift (I8) + delay-induced witness cost (Q6).** Natural death rate = hardware T1,
  drifts run-to-run (report a T1 band, not a point) and is not tunable; the aging `delay`s add idle on the
  germ line → witness dephasing that selective DD only partly cancels. Accepted trade for the honest/
  leaner (no-bath, 2W) version; `local_damping` reference quantifies the gap.
- **I6 DD granularity** — stock pass pads all idle qubits. Mitigation: targeted pass / custom pass;
  verify in the scheduled circuit (static).
- **No-sim risk.** Static checks prove the design is *structurally* correct (qubit-disjoint, ordered,
  isolated witness, monotone aging, DD-on-germ-only) but cannot show the *numerical* witness value — that
  is intentional (Q4); the developer's runs produce the witness-vs-W numbers at whatever W they pick (Q3).
- **CD-1 deviation** — a second file pair diverges from main-folder minimalism; mitigated by leaving the
  reproduction untouched and importing `qalife.py` as a library (OQ-1).

---

## 10. What PJ1 picks up next

L (arena size) is read off the qubits one PJ0 organism needs to keep its witness (from the developer's
later runs). PJ1 (rungs 3–6) tiles L germ/soma organisms as adjacent W12 segments, adds coherent
energy-transfer competition + differential reproduction under QRNG-chosen encounters, and measures the
**joint cross-lineage witness**. `pj_qalife.py`'s block-loop extension point (§6.1) is where it lands —
this ticket keeps the file shaped to admit it without a rewrite.

---

## 11. Open questions

All resolved in developer review 2026-09-12 (Q1–Q6).

- **OQ-1 (CD-1 deviation) — RESOLVED (Q1).** Separate `code/pj_qalife.py` + `code/pj_run_qalife.py` pair;
  `qalife.py`/`run_qalife.py` **not modified in any way** — fully separated. `pj_qalife.py` may `import
  qalife` read-only for pure helpers; germ/soma build logic written fresh.
- **OQ-2 (layout) — RESOLVED (Q2, option B + offset).** Separate germ/soma blocks, **organism-offset
  parameterized** (`geno_q(o,k)`/`pheno_q(o,k)` off `organism_base(o)`). Contiguous germ block →
  gene-passing clone is nearest-neighbor; separate soma block → I4 isolation; the `o` offset is the PJ1
  horizontal-scaling hook (tile adjacent segments). PJ0 builds `o=0` only. Natural-decay (Q6) drops the
  bath → segment = `2W`, leaner → more organisms per chain.
- **OQ-3 (width / comparison) — RESOLVED (Q3).** Width is a free CLI param at any W (W12 anchor/default);
  deeper is better. **The developer runs the sweeps and picks W** — the code must build correct circuits
  at any W. No fixed matched-W comparison hardcoded; the driver emits the comparison hooks only.
- **OQ-4 (sim / hardware) — RESOLVED (Q4).** **No sim, no hardware run in this ticket.** PJ0 delivers
  correct circuit-building code proven by **static code evaluation + printed/evaluated circuit
  correctness**. Sim Test 1 becomes **Static Test 1** (qubit-disjointness by circuit inspection). Runs
  are the developer's, later.
- **OQ-5 (mutation strength) — RESOLVED (Q5).** Keep `MUT_SCALE=0` (faithful 2018, clean GHZ witness).
- **OQ-6 (rung 2 scope) — RESOLVED (Q6).** Soma death is a **parameter** — `natural` (gate) and
  `local_damping` (rigid reference/fallback) both coded. Rung 2 natural-decay + selective DD is the
  acceptance gate. Aging order is **bounded, not rigid**: irregular lifespans are a lifelike feature; only
  the *scale* is gated — `max_deviation ≤ AGING_ORDER_TOL` (studied, default 2 gen), else targeted delays
  or cut to `local_damping`. Accepted downsides: T1 drift → report a band (I8); death rate not tunable in
  the natural arm (the reference arm gives the controllable rate); any forced delay adds germ-line idle →
  witness cost, minimized by keeping enforcement targeted + selective DD. `AGING_ORDER_TOL` is itself a
  study output — tune from measured deviation vs W.

---

## 12. Ground rules honored

- Every AC traces to `P3-candidate-movess.md`'s PJ0 acceptance list (a)–(f) + deliverables (1)–(6); none
  invented.
- Concrete file paths and line-grounded source-of-copy references throughout (§5, §6).
- Epic cross-cutting decisions applied (§4); the one deliberate deviation (CD-1) is flagged, not hidden.
- PJ1 / PM / M / EM-stack work kept out of scope (§3); the file pair is structured for PJ1 without
  building it.
- Strict types + PEP-8 stated for all new code; no raw SQL / templates (N/A here).
- No tests (CD-7): verification is static `--selftest` + `--dump-circuit` printing + written correctness
  evaluation. No sim, no hardware run in this ticket (Q4).
- `qalife.py` / `run_qalife.py` left byte-stable (Q1).
- `Status: Draft` — the developer flips to Approved.

---

## 13. Post-implementation notes

**Built (2026-09-12).** Two new files + one correctness directory; faithful reproduction
byte-stable (`git diff` empty for `code/qalife.py`, `code/run_qalife.py`).

- `code/pj_qalife.py` — germ/soma model + static `--selftest`. Two-phase `build_germsoma`
  (germ line fully, then isolated soma), organism-offset layout (PJ1 hook, PJ0 builds `o=0`),
  `phenotype ∈ {separable, entangled}`, `soma_death ∈ {natural, local_damping, none}`, static
  analyzers (`germsoma_coupling_report`, `aging_order_deviation`, `soma_z_closed_form`,
  `witness_qubits`). `--selftest` runs 5 structural checks at W{2,4,12} → **SELFTEST PASS**.
- `code/pj_run_qalife.py` — germ/soma driver, **build + evaluate statically**; live sampler path
  **dormant** (OQ-4). `build_measured_germsoma` (H genotype-only), fail-closed `gated_chain`,
  opt-3 transpile, `schedule_with_selective_dd` (DD on germ-line physical qubits only),
  `schedule_report` (DD placement + aging-order deviation), dormant `_run_schema`.
- `research/pj0_germsoma/CORRECTNESS.md` + `circuits/*.txt` — the written static-correctness
  evaluation with printed circuits.

**Verified manually (no tests/sim/hardware — CD-7/Q4):**
- `python pj_qalife.py --selftest` → 5 checks OK at W{2,4,12}, `SELFTEST PASS`, exit 0.
- `--dump-circuit` (model + driver) → Static Test 1 = YES (separable/natural/local_damping/none),
  gene-first ordering = YES, witness = genotype-only; entangled A/B → Static Test 1 = NO with
  mixing `cx [g,p]` and identical `ry` angles.
- `pj_run_qalife.py --dump-circuit` exits 0 without submitting (draw-only implied);
  `--run` refuses (dormant, exit 2). `pyflakes` clean, `py_compile` OK.

**Two implementation notes for the developer:**
1. **Ordering check runs on the bare biology build, not the measured circuit.** The witness-basis
   `H` on genotypes legitimately lands after the soma phase, so `germsoma_coupling_report` on the
   *measured* circuit reports `gene_first=NO`. `dump_circuit` therefore computes the rung-0/Static-
   Test-1 report on the pre-readout `build_germsoma` (the biology). Static Test 1 (disjointness) is
   unaffected by readout H (single-qubit).
2. **`--schedule-report` needs `--backend` for real gate timing** (no submission is made). Without
   a backend the circuit is unscheduled → no `delay`s → aging-order deviation is trivially 0. The
   selective-DD and aging-order numbers are only meaningful once scheduled against a real target;
   this is the developer's to run when picking W.

**Follow-ups (out of scope, for the developer's later runs):** witness ⟨X^W⟩ vs W sweep;
matched-W germ/soma vs P2 damping (does severing `cx(g,p)` push W\* past [4,8)?); soma-on/soma-off
witness pairing; T1 band + kept-fraction under selective DD; tune `AGING_ORDER_TOL` from measured
deviation vs W. PJ1 arena extends the organism-offset layout (§10).
