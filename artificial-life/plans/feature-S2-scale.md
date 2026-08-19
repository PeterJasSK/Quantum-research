# Feature Plan — S2: Scale big, not noise (`stage2_scale.py`)

**Status:** Complete
**Epic:** `artificial-life/plans/epic-qdep-coherence-depth-genealogy.md` (Status: **Approved**)
**Stage ID:** S2 (third of 5; depends on **S1**, gates S3)
**Artifact:** `artificial-life/code/stage2_scale.py`
**Source specs:** `qdep-1-coherence-depth-genealogy.md` (Stage 2, §Metrics, Bull/Bear/Value-if-null), `QDEP_Living_Genealogies.md` (§1 "noise is not a fitness function", §8, §11)
**Borrows from:** `artificial-life/code/stage1_temporal.py` (`temporal_correlation`, `_mutation_schedule`, `build_lineage_quantum`, `run_classical_surrogate`, `sample_quantum_arm`, `run_ideal`, `run_once`, `compute_gstar`, `main` repeats/aggregation loop, run/summary writers, CLI), `stage0_reproduce.py` (frozen operators/constants), `QuantumLife/code/research_qtree.py` (`main` per-generation mean/std aggregation, summary writer), `QuantumLife/code/sim_ideal_sign.py` (statevector ideal-reference pattern), `qrng_client.py`
**Reuses (do not re-derive):** the frozen S0 physics (`m_gate`, `apply_clone`, `phenotype_map`, `_z_expectation_statevector`, `ETA=0.9`, `PHI=acos(ETA)`, `PHENO_BASIS=0.0`) and the S1 temporal machinery (`temporal_correlation` anchored at T₀, the one-dynamic-lineage circuit, the measure-and-resend surrogate, the certified Q-EaaS schedule, `compute_gstar` on the g≥1 domain) — **copied verbatim** into `stage2_scale.py` with provenance comments (CD-1 parity)
**Author:** Claude (Opus) · **Date:** 2026-08-19

> No GitHub issue — this study uses stage IDs, not tickets (project convention).
> No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

S1 banked a small-scale g\* pipeline and, at G≈8, came out **g\* = 1** (falsification): the coherent
quantum arm tracked the separable measure-and-resend surrogate within k·σ at every g≥1. The S1
post-implementation notes name the cause precisely — the CX phenotype map, mid-circuit-measured **every**
generation, partially projects the coherent genotype, collapsing the quantum arm toward the surrogate — and
flag it as the thing S2 must confront *before* scaling.

S2 therefore has two jobs, in order:

1. **Confront the S1 collapse (the back-action confound).** Give the coherent arm a fair chance to outrun the
   surrogate by making the per-generation phenotype coupling **tunable** (Q1), so the mid-circuit readout can
   be a weak peek instead of a full projection. This is legitimate and honest: the surrogate is *defined* to
   fully measure-and-resend each generation; if the quantum arm can carry cross-generational correlation while
   only weakly reading the trait, *that* is the advantage the study is trying to measure. If even a weak-coupling
   quantum arm cannot beat the surrogate at any G, S2 reports g\* = 1 as a hard coherence-budget number
   (epic §5 / `qdep-1` Value-if-null) — a real, publishable result, not a failure.
2. **Scale G to find the ceiling.** Sweep generations G up to `--gmax`, tracking at each G where the
   quantum-vs-classical gap dies, with the **ideal-clone confound curve mandatory** (M4, AC-S2.2): a noiseless
   exact-clone `C(g)` run alongside so approximate-cloning decay is separated from hardware decoherence. The
   output is the paper's core number: **g\* with honest error bars**, plus the confound curve that says how much
   of any decay is cloning vs decoherence.

Governing rule (QDEP §1, AC-S2.1): **noise is not a fitness function.** Selection stays an explicit *measured*
op (vacuous in the minimal build — population = 1, no selection), every mutation stays tied to a signed Q-EaaS
receipt (M7), and "bigger" means *more coherent generations under control*, never more entropy dressed as biology.

**The one structural difference S2 introduces vs S1.** S1 runs a single G per invocation. S2 **sweeps** G
across `[--gmin … --gmax]` in one invocation, computing g\*(G) at each point, and promotes the **ideal arm to a
first-class confound curve** (M4) with the same repeats/error-bar treatment as the two hardware arms. It also
exposes `--pheno-coupling` (Q1) and `--width` (Q4, off by default). Everything else — operators, correlation
math, surrogate, Q-EaaS schedule, g\* rule — is the S1 code, copied verbatim.

### What already exists (integration points — concrete anchors)

- `artificial-life/code/stage1_temporal.py` — **frozen** functions S2 copies verbatim (CD-1):
  - `temporal_correlation(traits_by_shot, gmax) -> {"C","c","C0","gmax"}` @151 — connected `C(g)=⟨T₀T_g⟩−⟨T₀⟩⟨T_g⟩`
    anchored at T₀, `c(g)=C(g)/C(0)`. Reused **unchanged**.
  - `_mutation_schedule(client, n_slots, mut_scale) -> (theta_seq, provenance)` @189 — Q-EaaS byte→angle
    (`θ_g = mut_scale·u32/2³²`), one provenance dict per gen, fail-closed on `QRNGUnavailable`. Reused; S2
    fetches once for `gmax` and **slices** per G (§7).
  - `build_lineage_quantum(theta_seq, n_slots) -> QuantumCircuit` @237 — one dynamic circuit: `q[n_slots]`,
    `p[n_slots]`, `c[n_slots]`; per gen `apply_clone`+`m_gate`+`phenotype_map`+mid-circuit `measure`. S2 adds the
    `--pheno-coupling` knob here (Q1, §6/§7).
  - `sample_quantum_arm(qc, shots, args, backend, qubit_list) -> list[str]` @263 — `--sim` (statevector) vs
    hardware (`generate_preset_pass_manager(opt_level=3, initial_layout=…)` + `run_sampler`) dispatch, returns
    per-shot `T₀…T_G`. Reused; S2 forces the sim path for the ideal arm (§7).
  - `run_classical_surrogate(theta_seq, n_slots, shots, seed) -> list[str]` @290 — Markov-order-1
    measure-and-resend null (`z_pre=η·(1−2·prev)`, `z_after=cos2θ·z_pre+sin2θ·x_pre`). Reused **unchanged**.
  - `run_ideal(theta_seq, n_slots) -> list[float]` @340 — exact-statevector `⟨σ_z⟩_p` per gen. S2 **extends**
    this to a full ideal `C(g)` curve (§6/§7) for the M4 confound control.
  - `run_once(args, seed, arm, theta_seq, provenance, backend, backend_name, calib, qubit_list) -> (run, path)`
    @355 — one arm × one seed; writes run.json (§4 shape @387–406). Reused; S2 threads `G`/`pheno_coupling`.
  - `compute_gstar(per_gen_Cq, per_gen_Ccl, sigma, k) -> int` @421 — `max g≥1 : |C_q−C_cl|>k·σ`, floor 1. Reused **unchanged**.
  - `_read_env_key(name) -> str|None` @440; `main()` @458; CLI @459–478; repeats+aggregation @516–582.
- `artificial-life/code/stage0_reproduce.py` — frozen operators/constants @70–160 (`ETA`@75, `PHI`@76,
  `PHENO_BASIS`@77, `m_gate`@93, `apply_clone`@101, `phenotype_map`@111, `_z_expectation_statevector`@151).
- `artificial-life/code/qrng_client.py` — `QRNGClient(base_url, api_key)`@43, `fetch(*, size=32, fmt="hex")
  -> QRNGResponse{request_id, format, data, entropy_epoch, timestamp, receipt}`@50, `QRNGUnavailable`@29.
- `QuantumLife/code/research_qtree.py` — `main()` per-gen mean/std-over-repeats aggregation @406–424 and
  summary writer @426–445 (the idiom S1 already ports; S2 extends it to a per-G sweep).
- `QuantumLife/code/sim_ideal_sign.py` — statevector ideal-reference (`AerSimulator(method="statevector")`@20,
  `pipeline_common` stub @5–15, ideal loop `ideal_sign`@92). The M4 confound-curve pattern.
- **`pipeline_common` real path** (S1 post-note confirmed): `CalibrationGuidedHighYieldQRNG/old/code/pipeline_common.py`.
  Copy S1's probe idiom @61–83 verbatim (walks `("code","old/code","new/code")`, stub fallback keeps `--sim` importable).
- `artificial-life/.env` — `QEAAS_API_KEY` present. Q-EaaS base URL `https://api.qeaas.eu/` (resolve order
  `--qrng-url` → env `QEAAS_API_URL` → default; no localhost fallback).

---

## 2. Acceptance criteria

Verbatim from epic §12 (which quotes `qdep-1` Stage 2 and §Metrics). IDs added; each maps to a §8 manual check.

- **AC-S2.1** (verbatim, `qdep-1`): "Grow G (generations) and lineage width toward the QDEP ceiling **only as
  coherence allows**, tracking where the quantum-vs-classical gap dies. The governing rule (QDEP §1): *noise is
  not a fitness function.* Every scale-up keeps selection an explicit **measured** operation and every mutation
  tied to a signed Q-EaaS receipt."
- **AC-S2.2** (verbatim, `qdep-1` Metrics): "Cloning-fidelity confound control: report the ideal-clone `C(g)`
  from a noiseless sim so approximate-cloning decay is separated from hardware decoherence."
- **AC-S2.3** (verbatim, `qdep-1` Metrics): "Entropy provenance: every mutation traceable to a signed Q-EaaS receipt."
- **AC-S2.4** (epic §12): "g\* (M3) reported with mean±σ over `--repeats`, at each G, quantum vs surrogate vs ideal."

**AC coverage (verified — file:line evidence):**

| AC | Covered by | §8 check — result |
|---|---|---|
| AC-S2.1 ✅ | G-sweep in `main` `stage2_scale.py:690` (`for G in range(gmin, gmax+1)`); nested-schedule slice `theta_seq_full[:G+1]` at `stage2_scale.py:438`; selection absent (CD-8, population=1, no fitness/selection path present); mutation from certified Q-EaaS `_mutation_schedule` `stage2_scale.py:219` | PASS — stdout prints one `g*(G)` row per G (verify run: G2/G3/G4); every run.json carries `meta.entropy_provenance`; G2 `request_id`s are exact prefix of G4 (same seed) — nested schedule confirmed. |
| AC-S2.2 ✅ | ideal arm promoted to first-class curve — `run_ideal_correlation` `stage2_scale.py:401` (noiseless exact-clone `C(g)`); forced onto SIM via `force_sim` `stage2_scale.py:299` + routing `stage2_scale.py:451`; ideal always in `arms` `stage2_scale.py:642` | PASS — summary `sweep[i].per_generation[g].C_g_mean` has `"ideal"` key at every G; ideal run.json `meta.backend=="sim"`, `meta.sim==true` even under `--no-sim`; ideal `correlation_temporal.C` non-empty. |
| AC-S2.3 ✅ | reused `_mutation_schedule` `stage2_scale.py:219`; fail-closed aborts at `stage2_scale.py:647` (missing key) and `stage2_scale.py:682` (`QRNGUnavailable`) | PASS — all arms at a given (G,seed) share identical `angle_rad`/`request_id` slice (verified quantum vs classical G2 seed100); missing `QEAAS_API_KEY` → abort exit 1, no PRNG (observed). |
| AC-S2.4 ✅ | per-G aggregation `_aggregate_per_generation` `stage2_scale.py:534` (mean/std over repeats, quantum+classical+ideal) + `compute_gstar` `stage2_scale.py:514` per G; `sweep[]` `stage2_scale.py:736` + top-level `gstar` = largest-G entry | PASS — `sweep[i].gstar.{k2,k3}` integers per G; `sweep[i].per_generation[g].C_g_mean/std` carries all three arm keys; top-level `gstar` = `sweep[-1]` (G=gmax). |

---

## 3. Scope

### In scope
- New file `artificial-life/code/stage2_scale.py` (copies S1 wholesale, then extends). No edits to S0/S1 files.
- **G sweep:** `--gmin … --gmax` in one invocation; g\*(G) at each G; error bars from `--repeats`.
- **Ideal-clone confound curve (M4, AC-S2.2):** `arm="ideal"` promoted to a full `C(g)` curve via
  `run_ideal_correlation` (noiseless exact-clone circuit sampled on the statevector sim, `temporal_correlation`
  applied identically). Forced onto `SIM` even when `--no-sim`, so a hardware run reports quantum (decohered),
  classical (surrogate), **and** ideal (no-decoherence) side by side.
- **Tunable phenotype coupling (Q1):** `--pheno-coupling ∈ (0,1]` scales the genotype→phenotype readout strength
  in `build_lineage_quantum` so the mid-circuit peek can be weak (reduce cumulative back-action). Matched across
  arms where applicable (§7). Default and sweep behaviour set by Q1 resolution.
- **Entropy provenance carried forward (M7, AC-S2.3):** reuse `_mutation_schedule`, fetch once for `gmax`, slice
  per G; log receipts; fail-closed on `QRNGUnavailable`.
- **g\* with error bars:** `compute_gstar` (k=2 headline, k=3 reported) at each G; per-arm per-gen mean±σ.
- `--sim` fix-first sweep; Heron-r2 `run_hw` confirm at the largest coherent G the sim sweep identifies.
- CLI extends S1: adds `--gmin --gmax --width --pheno-coupling` (plus S1's flags unchanged).

### Out of scope (deferred to their stages)
- Teleport / SWAP routing, `logical_depth`, `Δg*`, `bond_correlations`, `--bond-dist`/`--anchors` — **S3**.
- THE figure, IEEE paper, honesty-invariant aggregation across all stages — **S4** (S2 emits the numbers S4 plots).
- ~102-qubit scale-out, death, interaction, population dynamics, selection as an active operator — whole-epic
  scope (CD-8; absent, not stubbed). `--width` provides *parallel independent* lineages only (tighter σ), not interaction.
- Re-deriving operators / correlation math / surrogate / g\* rule — frozen in S0/S1, copied verbatim (CD-1).

---

## 4. Data model — `run.json` / `summary.json` (S2 fields)

Written to `OUTPUT_DIR = ../research_runs`. run.json is **unchanged from S1 §4** (one per arm × repeat × G),
with two additive `meta` fields:

- `meta.pheno_coupling: <float>` — the Q1 readout-strength knob for this run (1.0 = S1's full CX projection).
- `meta.generations` already carries this run's G (varies across the sweep).

run.json path (extends S1 to disambiguate G): `f"{name}_{arm}_G{G}_{backend}_seed{seed}_{ts}_run.json"`.

**summary.json** (once per invocation) — extends S1 with a **sweep** array; the epic §4 contract fields
(`per_generation[].C_g_mean/std`, `gstar`) are preserved at top level for the **largest G** so S4 keeps working:

```jsonc
{
  "meta": {
    "project": "artificial-life", "study": "coherence-depth-genealogy",
    "backend": "sim|<hw>", "sim": true|false, "base_seed": <K>, "repeats": <R>,
    "gmin": <int>, "gmax": <int>, "shots": <S>, "corr_gmax": <int>, "k": <int>,
    "pheno_coupling": <float>, "width": <int>, "run_files": [ ... ]
  },
  "sweep": [                                   // S2 new — one entry per G in [gmin..gmax]
    { "G": <int>,
      "per_generation": [                      // §4 contract shape, now with an "ideal" arm key
        { "gen": <g>,
          "C_g_mean": { "quantum": <f>, "classical": <f>, "ideal": <f> },
          "C_g_std":  { "quantum": <f>, "classical": <f>, "ideal": <f> } }
      ],
      "gstar": { "k2": <int|null>, "k3": <int|null> } }
  ],
  "per_generation": [ ... ],                   // §4 contract — the largest-G sweep entry, verbatim
  "gstar": { "k2": <int|null>, "k3": <int|null> }  // §4 headline — largest-G g* (M3)
}
```

Field names `meta.arm`, `meta.entropy_provenance`, `correlation_temporal.{C,c,C0}`, `per_generation[].C_g_mean/std`,
`gstar` are the epic §4 contract — **do not rename**; S4 consumes them. `sweep`, `meta.pheno_coupling`,
`meta.width`, the `"ideal"` arm key, and the `G{G}` filename token are S2 additions (superset, not a break).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **CD-1** Copy, don't import — copy the S1 machinery and S0 operators verbatim into `stage2_scale.py` with
  `# ported from stage1_temporal.py` / `# ported from stage0_reproduce.py` comments. No `from stage1_temporal import`.
- **CD-2** `pipeline_common` stays external — copy S1's probe idiom (@61–83); `old/code` is the resolving path;
  stub fallback keeps `--sim` importable.
- **CD-3** Temporal axis — reuse `temporal_correlation` unchanged; `T` = phenotype `⟨σ_z⟩_p`, anchored at T₀.
- **CD-4** Two matched arms, one schedule — hold fixed across arms: population = 1, G, the **same** Q-EaaS
  `theta_seq` slice, measurement settings, shots. Swap only the inheritance channel. Repeat `r` uses `seed+r` in
  every arm. The ideal arm shares the same `theta_seq`.
- **CD-5** g\* = `max g≥1 : |C_q(g)−C_cl(g)| > k·σ(g)`, k=2 headline (k=3 reported); σ from `--repeats`.
- **CD-6** Cloning-confound control mandatory — the ideal noiseless `C(g)` curve reported alongside every
  hardware `C_q(g)` (this stage makes it first-class, M4).
- **CD-7** Certified Q-EaaS — mutation angles from fetched bytes, receipts logged, **fail-closed** on `QRNGUnavailable`.
- **CD-8** Minimal build — single linear lineage, one observable, population = 1, no death/interaction/teleport/selection.
  `--width` adds *parallel independent* lineages for σ only, never interaction. Code paths absent, not stubbed.
- **CD-9** Sim-first — fix the sweep in `--sim`, then confirm on Heron r2 at the identified coherent G.

---

## 6. File plan (concrete paths)

Python idioms: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`.
No raw SQL (N/A). One new file.

### `artificial-life/code/stage2_scale.py` (new)

Copy S1 top-to-bottom, then apply the S2 deltas. Structure:

1. **Module docstring** — what S2 proves (G-sweep g\*, ideal-clone confound curve M4, tunable phenotype coupling,
   entropy provenance at scale); provenance notes (ported from `stage1_temporal.py`, `stage0_reproduce.py`,
   `sim_ideal_sign.py`, `research_qtree.py`).
2. **Imports + dual-path setup** — copy S1 @37–100 verbatim: `pipeline_common` probe + stub fallback,
   qiskit imports, `SIM = AerSimulator(method="statevector")`, `OUTPUT_DIR`, `QEAAS_URL_DEFAULT`,
   frozen constants (`ETA/PHI/PHENO_BASIS/UNIT_TOL`, `M_THETA_SPEC/U_M_SPEC`), `from qrng_client import …`.
3. **Operators** — copy S1 @106–148 verbatim (`m_theta_matrix`, `m_gate`, `apply_clone`, `phenotype_map`,
   `_z_expectation_statevector`).
4. **`temporal_correlation`** — copy S1 @151 verbatim.
5. **`_mutation_schedule`** — copy S1 @189 verbatim.
6. **`build_lineage_quantum(theta_seq, n_slots, pheno_coupling=1.0) -> QuantumCircuit`** — copy S1 @237 and add
   the Q1 knob: `phenotype_map` gains a coupling scale so the mid-circuit readout can be weak (§7). At
   `pheno_coupling=1.0` the circuit is byte-identical to S1's. (If Q1 resolves to per-g two-point circuits, add
   `build_two_point(theta_seq, g) -> QuantumCircuit` instead/as well — see §11 Q1.)
7. **`run_classical_surrogate`** — copy S1 @290 verbatim.
8. **`sample_quantum_arm(qc, shots, args, backend, qubit_list, force_sim=False) -> list[str]`** — copy S1 @263;
   add `force_sim` so the ideal arm always uses the statevector path even under `--no-sim` (M4).
9. **`run_ideal_correlation(theta_seq, n_slots, shots, pheno_coupling) -> tuple[list[float], dict]`** — S2's
   promotion of S1's `run_ideal` (@340): build the **same** `build_lineage_quantum` circuit, sample it on `SIM`
   (`force_sim=True`) with `shots`, compute per-gen `trait_sigmaz` **and** the full `temporal_correlation` C(g).
   This is the noiseless exact-clone confound curve (M4, AC-S2.2). Keep the old per-gen `run_ideal` @340 as a
   thin wrapper for the S1-style sanity print.
10. **`run_once(args, seed, arm, G, theta_seq_full, provenance_full, backend, backend_name, calib, qubit_list)
    -> (run, path)`** — copy S1 @355; thread `G` and slice `theta_seq = theta_seq_full[:G+1]`,
    `provenance = provenance_full[:G+1]`; route `arm=="ideal"` through `run_ideal_correlation`; write run.json
    with `meta.pheno_coupling` and the `G{G}` filename token (§4).
11. **`compute_gstar`** — copy S1 @421 verbatim.
12. **`_read_env_key`** — copy S1 @440 verbatim.
13. **`_aggregate_per_generation(corr_by_arm, n_slots, stat_arms) -> (per_generation, gstar)`** — factor S1's
    inline aggregation (@534–560) into a helper so the sweep can call it per G. Per arm `mat = np.array(C-lists)`
    shape `(repeats × n_slots)`, `mean/std(ddof=0)` over axis 0; per-gen `{"gen","C_g_mean":{arm:…},"C_g_std":{arm:…}}`;
    `sigma[g]=sqrt(std_q²+std_cl²)`; `gstar={"k2":compute_gstar(…,2),"k3":compute_gstar(…,3)}` (or `{None,None}`
    if quantum+classical not both present). Aggregation over the **raw C(g)** arrays (matches S1).
14. **`main()`** — copy S1 @458 and add the sweep. Order:
    - argparse (§ CLI below).
    - Fail-closed QRNG: require `QEAAS_API_KEY` (env or `../.env`), else `SystemExit(1)`; build `QRNGClient`.
    - Backend dispatch (copy S1 @496–514): `n_slots_max = gmax+1`, `n_q = 2·n_slots_max` (largest chain needed);
      hardware → `connect`, `read_snapshot`, `best_chain(backend, n_q)`; sim → `qubit_list = range(n_q)`.
    - **Fetch the full schedule once:** `theta_full, prov_full = _mutation_schedule(client, n_slots_max, mut_scale)`
      **per repeat** (`seed=base_seed+r`); slice per G so smaller-G schedules are prefixes (CD-4, §7). Abort on `QRNGUnavailable`.
    - **Sweep loop** `for G in range(gmin, gmax+1)`: `n_slots=G+1`; for `r in range(repeats)`, for `arm in arms`
      (`quantum`, `classical`, and `ideal` — ideal always included for M4): `run_once(...)`, collect
      `corr_by_arm[arm].append(run["correlation_temporal"]["C"])`. Then `_aggregate_per_generation` → append
      `{"G", "per_generation", "gstar"}` to `sweep`. Print one `g*(G)` row.
    - summary.json: `sweep` + top-level `per_generation`/`gstar` = the `G==gmax` entry (§4). Print the sweep table
      and the headline g\*(gmax).
15. **`if __name__ == "__main__": main()`**.

CLI (`main`) — S1 flags unchanged, S2 adds the last four:

| flag | type | default | note |
|---|---|---|---|
| `--gmin` | int | 2 | smallest G in the sweep (≥2 so g≥1 domain is non-trivial) |
| `--gmax` | int | 16 | largest G — the SWAP-routed ceiling to probe (Q6/§7) |
| `--width` | int | 1 | parallel **independent** lineages for tighter σ (Q4; off/1 by default) |
| `--pheno-coupling` | float | see Q1 | genotype→phenotype readout strength ∈ (0,1] (Q1) |
| `--shots` | int | 8192 | per arm per repeat per G (Q6 — larger than S1's 4096 for stable σ at scale) |
| `--seed` | int | 100 | base; repeat r uses seed+r (all arms) |
| `--repeats` | int | 8 | σ for g\* (Q6 — larger than S1's 5 for tighter error bars) |
| `--backend` | str | None | Heron r2 auto-select when not `--sim` |
| `--sim` | BooleanOptionalAction | True | sim-first (CD-9) |
| `--arm` | {quantum,classical,both,ideal} | both | ideal is always run for M4 regardless (see §7) |
| `--corr-gmax` | int | =G | max g for C(g), per G |
| `--k` | int | 2 | σ multiplier (k=3 always also reported) |
| `--mut-scale` | float | 0.1 | max mutation angle (matches S0/S1) |
| `--qrng-url` | str | env `QEAAS_API_URL` else `https://api.qeaas.eu/` | Q-EaaS base URL; no localhost default |
| `--name` | str | qdep_s2 | output tag |

No other files. `research_runs/` already exists.

---

## 7. The physics/maths S2 fixes (the load-bearing detail)

- **Ideal-clone confound curve (M4, AC-S2.2) — the key S2 addition.** Under `--sim`, S1's quantum arm is
  *already* the noiseless exact-clone (statevector sampling has shot noise but **no decoherence**), so on a pure
  sim run quantum ≡ ideal. The confound control only bites on **hardware**: there the quantum arm decoheres while
  the ideal arm is the *same circuit* forced onto `SIM` (`force_sim=True`). Reporting both at each G separates
  approximate-cloning decay (present in ideal) from hardware decoherence (the quantum−ideal gap). S2 therefore
  runs the ideal arm **always**, even for `--no-sim`. Its C(g) is computed by the identical `temporal_correlation`
  on statevector-sampled `T₀…T_G` records — apples-to-apples with the hardware arms.
- **Nested schedule across the sweep (CD-4).** Fetch one `theta_full` of length `gmax+1` per repeat, then for a
  given G use `theta_full[:G+1]`. Smaller-G lineages are exact prefixes of larger-G ones, so the sweep is a single
  coherent experiment (a G=4 run is the first 4 generations of the G=16 run), and provenance is logged once per
  (repeat, generation), sliced — not re-fetched per G. Both/all arms at a given (G, repeat) share the identical slice.
- **Tunable phenotype coupling (Q1) — the S1-collapse fix.** S1's `phenotype_map` is a full `CX(genotype→pheno)`;
  measuring `pheno` each generation fully projects the genotype's Z component, so the coherent lineage is
  re-collapsed every step and cannot outrun the surrogate (this is exactly why S1 got g\*=1). S2 scales the
  coupling: replace the bare `CX` with a **controlled partial rotation** of strength `α=pheno_coupling` (e.g.
  `CRY(α·π)` / a partial-CX), so `α→1` recovers S1's full projection and `α<1` reads the trait weakly, leaving
  more genotype coherence to carry to the next generation. The readout `T_g` is still a `{0,1}` bit but a weaker
  peek — its `⟨σ_z⟩` estimate has more variance, hence Q6's larger `--shots`. **Honesty:** this is fair because
  the surrogate is *defined* to fully measure-and-resend each generation; a quantum arm that carries correlation
  under weak readout is a genuine advantage, not a tuned-in artefact. It is **not** matched to the surrogate's
  readout (the surrogate's full measurement is its defining classicality) — this asymmetry is the physics, and it
  must be stated plainly in S4. See §11 Q1 for the alternative (per-g two-point circuits) and the recommended default.
- **g\*(G) sweep (M3/AC-S2.4).** At each G, aggregate C(g) mean±σ over `--repeats` per arm, then
  `g*(G) = max g≥1 : |C_q(g)−C_cl(g)| > k·σ(g)`. Plot g\* vs G (S4). Expected shapes: (a) g\* grows then
  plateaus at the coherence ceiling; (b) g\* pins at 1 for all G → falsification, reported as the hard
  coherent-generation budget (epic §5, `qdep-1` Value-if-null). The **ideal** curve tells which: if ideal g\* > 1
  but hardware g\* = 1, decoherence is the ceiling; if ideal g\* = 1 too, approximate cloning alone kills the gap.
- **Qubit budget at scale.** The dynamic circuit uses `2·(G+1)` qubits (genotype chain + one fresh pheno ancilla
  per gen). At `gmax=16` that is 34 qubits — fine for Heron r2's chain via `best_chain(backend, 2·(gmax+1))`, and
  borderline-heavy but feasible for statevector sim (34 qubits ≈ 2³⁴ amplitudes → **too big for statevector**).
  See §9 — the sim sweep must cap G where statevector stays tractable (~28–30 qubits, i.e. G≤~14) or drop to a
  lighter sim method for the top of the sweep; `--gmax` default 16 is the *hardware* ceiling, sim caps lower (§9, Q6).
- **Entropy provenance at scale (M7, AC-S2.3).** `_mutation_schedule` fetches 32-byte Q-EaaS blocks until
  `4·(gmax+1)` bytes; each generation's angle + `request_id`/`receipt`/`entropy_epoch`/`timestamp` logged into
  `meta.entropy_provenance` (sliced per G). Fail-closed: `QRNGUnavailable` aborts the whole sweep (never PRNG).
  Request volume: one schedule per repeat (shared across G-slices and arms), so `--repeats` fetches total —
  the copied client's 429 `Retry-After` covers bursts.

---

## 8. Manual verification (no automated tests)

Run from `artificial-life/code/` (sim-first, CD-9):

```bash
cd artificial-life/code
# sim sweep, all three arms, small→mid scale
python stage2_scale.py --gmin 2 --gmax 12 --shots 8192 --seed 100 --repeats 8 --arm both --name qdep_s2
# hardware confirm at the coherent G the sim sweep identifies (example G=8)
python stage2_scale.py --gmin 8 --gmax 8 --shots 8192 --seed 100 --repeats 4 --no-sim --backend '' --name qdep_s2_hw
```

- **AC-S2.1 (scale, no noise-as-fitness)** — stdout prints one `g*(G)` row per G across `[gmin..gmax]`; each
  run.json carries `meta.entropy_provenance`; grep the source confirms no selection / fitness-from-noise path
  (population = 1, CD-8). `theta_full[:G+1]` slicing verified: a G=4 run.json's `entropy_provenance` `request_id`
  sequence is the prefix of the G=8 run's (same repeat).
- **AC-S2.2 (confound curve)** — summary `sweep[i].per_generation[g].C_g_mean` has a `"ideal"` key at every G;
  under `--sim` ideal ≈ quantum (no decoherence); on the `--no-sim` run the ideal curve sits **above** the
  quantum curve (the gap = hardware decoherence). Confirm the ideal arm ran on SIM even with `--no-sim`
  (`meta.arm=="ideal"` run.json has `meta.backend` reflecting the forced-sim path).
- **AC-S2.3 (provenance)** — all arms at a given (G, repeat) share the same `request_id`/`angle_rad` slice;
  unset `QEAAS_API_KEY` → abort exit 1 with `QRNGUnavailable`, no PRNG fallback.
- **AC-S2.4 (g\* with error bars)** — `sweep[i].gstar.{k2,k3}` integers (or null on falsification) at each G;
  `sweep[i].per_generation[g].C_g_std` present for quantum/classical/ideal; stdout prints the g\*(G) sweep table
  and the headline `g* (k=2) = N` at G=gmax.
- **Q1 effect check** — run `--gmax 8 --pheno-coupling 1.0` (S1 parity, expect g\*≈1) vs `--pheno-coupling 0.3`
  (weak peek); confirm the weak-coupling quantum arm's `C(g)` decays slower and, if the effect is real, g\* > 1.
  (If g\* stays 1 at all couplings and all G → falsification, still a valid reported result.)
- **Schema check** — `python -c "import json;d=json.load(open('<summary>'));print(len(d['sweep']),
  d['sweep'][0]['per_generation'][0]['C_g_mean'].keys(), d['gstar'])"` → sweep length = `gmax−gmin+1`, arm keys
  include `ideal`, top-level `gstar` present.
- **Determinism** — same `--seed` with QRNG cached/mocked reproduces the `theta_full` positions and (within shot
  noise) the same sweep curves. Live QRNG is non-deterministic by design (provenance reproduces, not the value).

---

## 9. Out-of-context risks / notes

- **Statevector sim ceiling.** `2·(G+1)` qubits ⇒ `gmax=16` needs 34 qubits, which **exceeds** practical
  statevector memory (~28–30 qubits). The sim sweep must cap G (default keep the sim run to `--gmax ≤ 12`, i.e.
  ≤26 qubits) or the top of the sweep needs a lighter method (`matrix_product_state`) — flag for Q6. The
  *hardware* `--gmax` can go higher (chain-limited, not amplitude-limited). Do **not** let a 34-qubit statevector
  allocation OOM the box; guard with an explicit G cap + a clear error when `2·(G+1) > --sv-max-qubits`.
- **The S1 collapse may persist (Value-if-null).** If the weak-coupling knob does not open a gap at any G, S2's
  result is g\* = 1 — a hard coherence-budget number. This is the epic's explicitly-accepted null (§5,
  `qdep-1` Value-if-null / Bear case) and is publishable. The plan must not tune the surrogate or the coupling to
  manufacture a gap — the honesty invariant (AC-S4.3) governs. Q1 records the coupling used so S4 reports it honestly.
- **Ideal ≡ quantum under `--sim`.** On a pure sim run the confound curve and the quantum arm coincide (both
  noiseless); the confound control only *separates* anything on hardware. Reviewers must not read the sim-run
  overlap as "no decoherence effect" — it is by construction. State this in S4.
- **Q-EaaS request volume / quota.** One schedule fetch per repeat (shared across all G-slices and arms). At
  `--repeats 8` that is 8 schedules; the copied client's 429 `Retry-After` handles bursts. At large `gmax` a
  single schedule needs `4·(gmax+1)` bytes ⇒ multiple 32-byte blocks (still one logical schedule).
- **`--width` σ vs qubits.** `--width>1` runs parallel independent lineages to tighten σ, multiplying the qubit
  count by `width` — only turn it on if the single-lineage σ cannot resolve g\* (Q4). Off (=1) by default.
- **`timestamp()` under the stub returns `"sim"`** — the `G{G}` filename token now disambiguates sweep runs at
  the same seed/name, but repeated sim invocations at the same `--seed`/`--name`/`--gmax` still overwrite. Vary
  `--name`/`--seed` to keep multiple sim sweeps.
- **Bit-reversal on hardware** — reuse S1's `sample_quantum_arm` reversal (`s[::-1]`); ensure `c[g]` → correct
  temporal-matrix column after reversal (already handled in S1, carried verbatim).
- No new pip dependency — `qiskit`, `qiskit_aer`, `numpy` in env; `qrng_client.py` uses stdlib `urllib`.

---

## 10. Ground rules honored

- Every AC (S2.1–S2.4) quoted verbatim from the epic / `qdep-1` and mapped to a §8 manual check.
- Every file path in §6 is concrete; one new file, no edits outside `artificial-life/code/`.
- Epic cross-cutting decisions (CD-1..CD-9) adopted without re-arguing; CD-6 confound-curve made first-class,
  CD-7 fail-closed carried forward, CD-8 selection/interaction absent-not-stubbed.
- No tests, no test files, no test-impact section (project directive). Verification is manual (§8).
- Strict typing + Python idioms (`from __future__ import annotations`, full hints); no raw SQL.

---

## 11. Resolved decisions (developer, 2026-08-19 — all proposed defaults accepted)

- **Q1 — Phenotype-coupling strategy: RESOLVED → (A) tunable weak coupling.** Ship `--pheno-coupling α`
  (`phenotype_map` = controlled partial rotation, `α=1` recovers S1's full projection), default **0.5** (weak
  peek), with a `--pheno-coupling 1.0` control run for S1 parity. Keeps the S1 single-lineage circuit structure
  (epic Q2) and directly tests the S1 post-note hypothesis. **(B) per-g two-point circuits** held as a deferred
  fallback only if (A) still pins g\*=1 at every G and every α.
- **Q6 — Shot/repeat budget + sim G-cap: RESOLVED → defaults accepted.** `--shots 8192`, `--repeats 8`, sim
  sweep capped at `--gmax 12` (≤26 qubits statevector; guard errors when `2·(G+1) > --sv-max-qubits`), hardware
  sweep free to go higher.
- **Q7 — `--gmax` + hardware ceiling: RESOLVED → defaults accepted.** Sim default `--gmax 12`; the hardware
  confirm targets a **single** G at the coherent ceiling the sim sweep identifies (conserve QPU), not the whole sweep.
- **Q8 — summary contract: RESOLVED → defaults accepted.** Keep top-level `per_generation`/`gstar` = the
  largest-G sweep entry (S4 back-compat) and add the full `sweep[]`. S4 may later switch to reading `sweep[]`
  directly; noted as an S4 plan input, no change to the epic §4 contract now.

---

## 12. Q-EaaS API contract

Unchanged from S1 §12 (verified against `qrng-eaas/` docs): `GET /v1/random/bytes?size=&format=`, `X-API-Key`
header, `32 ≤ size ≤ 4096`, response `{request_id, format, data, entropy_epoch, timestamp, receipt}` with
nullable `receipt`, 401/429(`Retry-After`)/503/422 handling. S2 reuses the copied `qrng_client.py` verbatim;
no client-side change. (Optional `POST /v1/verify` still unused — note for S4 provenance audit.)

---

## 13. After approval

Once the open questions are answered and the plan approved, run
`/implement-feature artificial-life/plans/feature-S2-scale.md`.
S2 gate before S3: a clean `--sim` G-sweep with the ideal-clone confound curve reported at every G, g\* banked
with error bars (the paper's core number — whatever its value, including g\*=1), and the certified Q-EaaS
provenance logged fail-closed (CD-7, M7). S3 (teleport vs SWAP, Δg\*) starts only after g\* is banked.

---

## 13b. Post-implementation notes (2026-08-19)

**What was built.** One new file `artificial-life/code/stage2_scale.py` — S1 copied verbatim (CD-1), then
extended with the four S2 deltas: (1) a **G-sweep** (`--gmin..--gmax`) in one invocation, g\*(G) per G; (2) the
**ideal-clone confound curve first-class** (M4) — `run_ideal_correlation` builds the *same* lineage circuit and
samples it noiselessly (`force_sim`) even under `--no-sim`, and the `ideal` arm is always run; (3) the **tunable
phenotype coupling** (Q1) — `phenotype_map` gains `pheno_coupling`, `α=1.0` byte-identical to S1's full `CX`,
`α<1` a `CRY(α·π)` weak peek (default 0.5); (4) `--width` parallel independent lineages for tighter σ (Q4).
Schedule fetched once per repeat for `gmax` and **sliced** per G (CD-4) so smaller-G lineages are exact prefixes.
No edits to S0/S1 files. No new pip dependency.

**Manually verified (sim, live Q-EaaS).** A `--gmin 2 --gmax 4 --repeats 2` smoke sweep exercised every path:
per-G g\* rows printed, ideal arm present at every G with non-empty `C(g)` and `meta.backend=="sim"`, provenance
nesting confirmed (G2 `request_id`s prefix G4's), all arms share the identical angle slice at matched (G,seed),
`--sv-max-qubits` guard aborts at `gmax=13` (28 q > 26), `α=1.0` emits `cx`/`α=0.5` emits `cry`, and the
missing-key fail-closed abort exits 1 with no PRNG fallback. Smoke artifacts removed.

**Deviations from the plan (surfaced, none silent).**
- `run_ideal_correlation` takes `args` (+ `gmax`, `width`) rather than the plan's `(theta_seq, n_slots, shots,
  pheno_coupling)` signature — it needs `args` to reuse `sample_quantum_arm`'s dispatch with `force_sim=True`.
  Same behaviour, cleaner reuse.
- **`--width` implemented as independent-lineage *sample pooling*** (runs `width` independent lineages —
  fresh sim RNG / offset surrogate seeds — and pools their per-shot records) rather than one wide circuit that
  multiplies the qubit count (plan §7). Rationale: identical purpose (tighter σ from more independent samples),
  off by default (=1), and it avoids the statevector blow-up the plan itself flags as a §9 risk. If a future run
  needs *interacting* parallel lineages, that is a different (out-of-scope, CD-8) build.
- Default `--gmax = 12` (not the §6 table's 16): the §11 Q6/Q7 resolution caps the **sim** sweep at 12 (≤26
  statevector qubits), and `--sim` is the default; a default of 16 would auto-abort on the sv-qubit guard. 16
  remains reachable as the *hardware* ceiling via `--gmax 16 --no-sim --sv-max-qubits …` at a single G.

**For the developer.**
- The M4 confound curve requires statevector for the ideal arm **at every G, even on `--no-sim`** — so the
  sv-qubit guard bounds the whole sweep (hardware included). The §8 hardware confirm (single G≈8, 18 q) is well
  inside the ceiling; a hardware run at very large G cannot produce the mandatory ideal curve on this box.
- The plan-mandated real sim sweep (`--gmax 12 --shots 8192 --repeats 8`) fetches 8 live Q-EaaS schedules and is
  the heavy run to bank the headline g\* before S3 — not run here (would consume real QPU/quota budget and network);
  the smoke sweep proved the pipeline. Run it when ready to bank the number.
- Whatever g\* comes out — including g\*=1 at every G/α — is the publishable result (epic §5 Value-if-null); do
  **not** tune `--pheno-coupling` or the surrogate to manufacture a gap (honesty invariant AC-S4.3).
