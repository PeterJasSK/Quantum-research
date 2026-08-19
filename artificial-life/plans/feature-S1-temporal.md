# Feature Plan — S1: Port + temporal C(g) + surrogate (`stage1_temporal.py`)

**Status:** Complete
**Epic:** `artificial-life/plans/epic-qdep-coherence-depth-genealogy.md` (Status: **Approved**)
**Stage ID:** S1 (second of 5; depends on **S0**, gates S2)
**Artifact:** `artificial-life/code/stage1_temporal.py`
**Source specs:** `qdep-1-coherence-depth-genealogy.md` (Stage 1, §Metrics), `QDEP_Living_Genealogies.md` (§8 surrogate, §9)
**Borrows from:** `QuantumLife/code/research_qtree.py` (`two_point_correlation`, `run_sim`, `run_once`, `main` aggregation), `research_qtree_teleport.py` (dynamic-circuit `run_hw`, `if_test` feed-forward pattern), `layout.py` (`best_chain`), `sim_ideal_sign.py` (statevector stub pattern); QRNG client from `TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py`
**Reuses (do not re-derive):** the frozen S0 operators/physics in `artificial-life/code/stage0_reproduce.py` — `m_gate`, `apply_clone`, `phenotype_map`, `ETA`, `PHI`, `PHENO_BASIS` — **copied verbatim** into `stage1_temporal.py` with provenance comments (Q1 resolved: copy, strict CD-1 parity)
**Author:** Claude (Opus) · **Date:** 2026-08-19

> No GitHub issue — this study uses stage IDs, not tickets (project convention).
> No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

S1 re-aims the **trusted** QuantumLife correlation machinery from spatial `c(d)` (across qubits, one
generation) to this study's **temporal** `C(g)` (across generations, one lineage) — same math, orthogonal
axis (CD-3). It adds the matched **measure-and-resend** classical surrogate arm (CD-4) and banks a
**small-scale g\*** (M3) in `--sim`, then confirms on Heron r2. It wires the certified Q-EaaS entropy
stream for mutation angles from here on (CD-7).

**The one structural difference S1 introduces vs QuantumLife.** QuantumLife builds *one circuit per
generation*; each shot yields an `n`-qubit chain bitstring and `two_point_correlation` correlates qubit `i`
with qubit `i+d` *within a shot*. S1 builds *one dynamic circuit for the whole lineage*; each shot descends
the single lineage and **mid-circuit-measures the phenotype trait `T_g` once per generation** into a
classical register of width `G+1` (Q2 resolved: one lineage per shot, feed-forward-capable dynamic circuit).
A shot's record is therefore `T₀T₁…T_G`, and the correlation is between generation 0 and generation g
*across shots*. The connected-correlation arithmetic is copied verbatim; only the axis meaning changes.

### What already exists (integration points)
- `artificial-life/code/stage0_reproduce.py` — **frozen** operators + physics S1 imports/copies: `m_gate(θ)`
  mutation, `apply_clone(qc, parent, ancilla, phi=PHI)` (U_M, `η=cos φ=0.9` contraction), `phenotype_map(qc,
  genotype, pheno_ancilla)` (`PHENO_BASIS=0.0`), and `_z_expectation_statevector`. S1 reuses these unchanged
  (CD-1: copy into `stage1_temporal.py` with provenance comments, or import from the sibling S0 module — see §11 Q1).
- `QuantumLife/code/research_qtree.py`:
  - `two_point_correlation(fields, n, dmax) -> {"C","c","C0","xi","dmax"}` @188 — connected correlation of a
    list of shot bitstrings; the exact function S1 re-indexes (§7).
  - `run_sim(theta, kick, env, n, shots, spec) -> (list[str], 0.0)` @235 — the independent-qubit surrogate
    producer S1 adapts to measure-and-resend.
  - `run_once` @271 (`--sim` vs `run_hw` dispatch) and `main` @345 (argparse, repeats/aggregation loop,
    summary.json writer) — the harness skeleton S1 copies.
  - `field_stats` @178, `next_belief` @221 — helpers (belief-update reused for the mutation-schedule bookkeeping).
- `QuantumLife/code/research_qtree_teleport.py` — the **dynamic-circuit** `run_hw`/`build_circuit` that
  declares a `ClassicalRegister` and reads mid-circuit measurements + `if_test` feed-forward (`_teleport_cx`
  @201). S1 copies the dynamic-circuit register/readout scaffolding (not the teleport bond — that's S3).
- `QuantumLife/code/layout.py` — `best_chain(backend, n) -> (chain, stats)` @53, SWAP-free low-error chain.
- `TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py` — `QRNGClient(base_url, api_key)`,
  `fetch(*, size=32, fmt="hex") -> QRNGResponse{request_id, format, data, entropy_epoch, timestamp, receipt}`,
  `QRNGUnavailable`, 401/429(`Retry-After`)/503 handling. Copy verbatim into `artificial-life/code/qrng_client.py`.
- `artificial-life/.env` — holds `QEAAS_API_KEY` (present). Q-EaaS **base URL** = `https://api.qeaas.eu/`
  (Q5 resolved) — resolve order: `--qrng-url` → env `QEAAS_API_URL` → the `https://api.qeaas.eu/` default;
  no localhost fallback.
- `pipeline_common` lives in `CalibrationGuidedHighYieldQRNG/code` (CD-2). sys.path idiom (from
  `artificial-life/code/`): `os.path.normpath(os.path.join(_HERE, "..", "..", "CalibrationGuidedHighYieldQRNG",
  "code"))` then `from pipeline_common import connect, run_sampler, timestamp`.

---

## 2. Acceptance criteria

Verbatim from epic §11 (which quotes `qdep-1` Stage 1 and `QDEP` §8/§9). IDs added; each maps to a §8 manual check.

- **AC-S1.1** (verbatim, `qdep-1`): "Reuse the growth engine, the `--sim` classical surrogate harness, and
  the Heron-r2 layout pipeline — but *re-aim* the correlation tooling from QuantumLife's **spatial** `c(d)`
  (across qubits, one generation) to this study's **temporal** `C(g)` (across generations, one lineage). Same
  trusted machinery, orthogonal axis. Add the measure-and-resend surrogate arm and run the g\* comparison at
  small scale."
- **AC-S1.2** (verbatim, `QDEP` §8 surrogate): "Same population size, same generation count, same mutation
  rate/schedule, same selection thresholds, same random seeds from the *same* Q-EaaS stream. Replace every
  coherent inheritance/interaction with a **measure-and-resend** step: measure the parent's trait, send
  classical bits, re-prepare a separable state from those bits."
- **AC-S1.3** (epic §11): "`C(g)` computed for both arms with error bands from `--repeats`; g\* (M3, k=2 and
  k=3) reported."

**AC coverage (verified against running code):**

| AC | Covered by | Evidence |
|---|---|---|
| AC-S1.1 | `stage1_temporal.py:151` `temporal_correlation` (spatial→temporal re-aim, anchored T₀); `:237` `build_lineage_quantum` (one dynamic lineage, mid-circuit readout) | Sim run: quantum `c(g)` non-flat `1.0,0.96,0.86,0.73,…,0.41`; `correlation_temporal.c[0]==1.0`; `len(C)==G+1==9`; consumes per-shot `G+1`-bit records. |
| AC-S1.2 | `stage1_temporal.py:290` `run_classical_surrogate` (measure-and-resend, η-contraction via classical bit, Q3); `:189` `_mutation_schedule` (shared Q-EaaS stream both arms) | Both arms' `run.json` share identical `entropy_provenance` `request_id`+`angle_rad` sequence (verified `qids==cids and qang==cang`); `meta.arm` = `quantum` vs `classical`. |
| AC-S1.3 | `stage1_temporal.py:421` `compute_gstar` (CD-5, g≥1 domain); `main` aggregation `:544–581` (`per_generation[].C_g_mean/std`, `gstar`) | `summary.json`: `gstar={"k2":1,"k3":1}` integers; `per_generation[g].C_g_mean/std` for both arms; stdout prints `g* (k=2) = 1  g* (k=3) = 1`. |
| CD-7 fail-closed | `qrng_client.py` `QRNGUnavailable`; `main:511` (missing key abort), `:530` (fetch abort) | Missing `QEAAS_API_KEY` → abort exit 1; unreachable URL → `QRNGUnavailable` abort exit 1. No PRNG fallback. |

---

## 3. Scope

### In scope
- New file `artificial-life/code/stage1_temporal.py`; new file `artificial-life/code/qrng_client.py` (copied).
- `temporal_correlation(traits_by_shot, G)` — `two_point_correlation` re-indexed to generation g (§7).
- **Quantum arm:** one dynamic lineage circuit, G+1 generations, mid-circuit phenotype readout per generation
  into a `ClassicalRegister(G+1)`; coherent `apply_clone` inheritance (S0's U_M).
- **Classical surrogate arm:** measure-and-resend — per generation measure parent trait → classical bit →
  re-prepare a separable child from that bit, then mutate (AC-S1.2). `--sim` classical producer + a matched
  separable circuit path for hardware.
- **Certified Q-EaaS mutation stream (CD-7):** `qrng_client.py`, per-generation mutation angle from fetched
  bytes, `meta.entropy_provenance` receipt log, **fail-closed** on `QRNGUnavailable`. Both arms consume the
  **same** byte stream at matched positions (CD-4).
- Small-scale **g\*** (M3, k=2 and k=3) with σ from `--repeats`; `correlation_temporal` per run,
  `per_generation[].C_g_mean/std` + `gstar` in summary.json.
- `--sim` fix-first path and a Heron-r2 `run_hw` dynamic-circuit confirm (`best_chain` layout).
- CLI: `--generations --shots --seed --repeats --backend --name --sim --arm {quantum,classical,both}
  --corr-gmax --k --mut-scale --qrng-url`.

### Out of scope (deferred to their stages)
- Scaling G toward the coherence ceiling, the ideal-clone confound sweep as a first-class arm, `--gmax`/`--width` — **S2**.
  (S1 *may* emit a single ideal-arm run for cross-check, but the confound curve M4 and its error bars are S2.)
- Teleport / SWAP routing, `logical_depth` comparison, `Δg*`, `bond_correlations` — **S3**.
- THE figure, IEEE paper, honesty-invariant aggregation across all stages — **S4**.
- Death, interaction, population > 1, selection thresholds as an active operator (CD-8 — absent, not stubbed;
  AC-S1.2's "same selection thresholds" is vacuous here since the minimal build has no selection).

---

## 4. Data model — `run.json` / `summary.json` (S1 fields)

Written to `OUTPUT_DIR = ../research_runs` (relative to `artificial-life/code/`). Names mirror QuantumLife:
`<name>_<backend|sim>_seed<K>_<ts>_run.json` per (arm, repeat); `<name>_<backend|sim>_<ts>_summary.json`
once per invocation (`ts = timestamp()`, `"sim"` under the stub).

**run.json** (one per arm × repeat) — extends the S0 shape:
```jsonc
{
  "meta": {
    "project": "artificial-life",
    "study": "coherence-depth-genealogy",     // §4 study tag
    "arm": "quantum" | "classical" | "ideal", // §4 — names the inheritance channel
    "backend": "sim" | "<hw name>", "sim": true|false,
    "timestamp": "<ts>", "seed": <K>,
    "generations": <G>, "shots": <S>, "mut_scale": <float>, "corr_gmax": <int>,
    "operators": { "M_theta": "...", "U_M": "..." },   // reused from S0 specs
    "entropy_provenance": [                    // §4 CD-7 — one entry per mutation
      { "gen": <g>, "source": "qeaas",
        "request_id": "<id>", "receipt": "<sig|null>",
        "entropy_epoch": <int>, "timestamp": "<iso>",
        "angle_rad": <float> }
    ],
    "calibration": <read_snapshot|null>        // §4 reused verbatim (null in sim)
  },
  "generations": [                             // per-generation phenotype trait (reused S0 field)
    { "gen": <g>, "trait_sigmaz": <float>, "shots": <S> }
  ],
  "correlation_temporal": {                    // §4 — two_point_correlation re-indexed by g
    "C": [<C(0)>, <C(1)>, ...],                //   connected correlation ⟨T₀T_g⟩−⟨T₀⟩⟨T_g⟩
    "c": [1.0, <C(1)/C(0)>, ...],              //   normalized C(g)/C(0)
    "C0": <float>,
    "gmax": <int>
  }
}
```

**summary.json** (once per invocation) — the g\* result:
```jsonc
{
  "meta": { "project":"artificial-life", "study":"coherence-depth-genealogy",
            "backend":"sim|<hw>", "sim":true|false, "base_seed":<K>, "repeats":<R>,
            "generations":<G>, "shots":<S>, "corr_gmax":<int>, "k":<int>,
            "run_files":[ ... ] },
  "per_generation": [                          // §4 — mean±σ over repeats, per arm
    { "gen":<g>,
      "C_g_mean": { "quantum":<f>, "classical":<f> },
      "C_g_std":  { "quantum":<f>, "classical":<f> } }
  ],
  "gstar": { "k2": <int>, "k3": <int> }        // §4 headline (M3)
}
```

Field names `meta.arm`, `meta.entropy_provenance`, `correlation_temporal.{C,c,C0}`,
`per_generation[].C_g_mean/std`, `gstar` are the epic §4 contract — do not rename; S2/S4 consume them.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **CD-1** Copy, don't import — copy QuantumLife helpers into `stage1_temporal.py`, the QRNG client into
  `qrng_client.py`, **and the S0 operators** (`m_gate`, `apply_clone`, `phenotype_map`, `ETA`, `PHI`,
  `PHENO_BASIS`, `_z_expectation_statevector`) verbatim into `stage1_temporal.py`, all with `# ported from …`
  provenance comments (Q1 resolved: copy — strict CD-1 parity, no `from stage0_reproduce import`).
- **CD-2** `pipeline_common` stays external — add the `sys.path.insert` hook to `CalibrationGuidedHighYieldQRNG/code`;
  under `--sim` the stub pattern (from `sim_ideal_sign.py`) keeps the file importable without backend access.
- **CD-3** Temporal axis is the whole novelty — reuse connected-correlation math verbatim, index by generation g.
  `C(g) = ⟨T₀T_g⟩ − ⟨T₀⟩⟨T_g⟩`, normalized `C(g)/C(0)`; `T` = phenotype `⟨σ_z⟩_p` via the S0 ancilla map;
  `T₀,T_g` read per shot via mid-circuit measurement down one lineage.
- **CD-4** Two matched arms, one schedule — hold fixed: population = 1, G, mutation-angle schedule, the **same**
  Q-EaaS byte stream/positions, measurement settings, shot budget. Swap only the inheritance channel. Repeat `r`
  uses `seed = base_seed + r` in *both* arms.
- **CD-5** g\* = `max g s.t. |C_q(g) − C_cl(g)| > k·σ`, k=2 headline (k=3 reported); σ from `--repeats`.
- **CD-7** Certified Q-EaaS from S1 — mutation angles from fetched bytes, receipts logged, **fail-closed** on
  `QRNGUnavailable` (never silent PRNG fallback, else M7 provenance is a lie).
- **CD-8** Minimal build — single linear lineage, one observable, population = 1, no death/interaction/teleport.
  Code paths absent, not stubbed.
- **CD-9** Sim-first — fix the pipeline in `--sim`, then confirm on Heron r2 with the same `run_once`/`--sim` branch.

---

## 6. File plan (concrete paths)

Python idioms: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`.
No raw SQL (N/A). No business logic in templates (N/A). Two new files.

### `artificial-life/code/qrng_client.py` (new — copied verbatim, CD-1)
- Copy `TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py` byte-for-byte; add a top provenance
  comment `# ported from TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py (CD-7)`.
- Provides `QRNGClient(base_url, api_key)`, `fetch(*, size, fmt="hex") -> QRNGResponse`, `QRNGUnavailable`,
  `QRNGResponse{request_id, format, data, entropy_epoch, timestamp, receipt}`, and the 401/429/503 retry policy.

### `artificial-life/code/stage1_temporal.py` (new)
Structure, top to bottom:

1. **Module docstring** — what S1 proves (temporal C(g), surrogate arm, small-scale g\*); provenance notes
   (ported from `research_qtree.py`, `research_qtree_teleport.py`, `sim_ideal_sign.py`); the CD-3 axis re-aim.
2. **Imports + dual path setup** —
   - `pipeline_common` real import via `sys.path.insert(0, <…/CalibrationGuidedHighYieldQRNG/code>)`
     (`from pipeline_common import connect, run_sampler, timestamp`), guarded so `--sim` still works if the
     backend layer is absent (fall back to the `sim_ideal_sign.py` stub — copy lines that register the stub in
     `sys.modules` **before** the import).
   - `from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile`; `from qiskit_aer import AerSimulator`.
   - S0 physics **copied verbatim** (Q1 resolved: copy, not import) — `m_theta_matrix`, `m_gate`,
     `apply_clone`, `phenotype_map`, `_z_expectation_statevector`, and constants `ETA=0.9`, `PHI=acos(ETA)`,
     `PHENO_BASIS=0.0`, `UNIT_TOL=0.03` — each with `# ported from QuantumLife-adjacent stage0_reproduce.py` comments.
   - `from qrng_client import QRNGClient, QRNGUnavailable`.
   - `SIM = AerSimulator(method="statevector")`; `_HERE`, `OUTPUT_DIR = normpath(_HERE/"../research_runs")`.
   - `load_dotenv`-free env read: `QEAAS_API_KEY = os.environ.get("QEAAS_API_KEY")`, `QEAAS_API_URL` /
     `--qrng-url` (§11 Q5); read `artificial-life/.env` with a tiny parser if the var isn't already exported.
3. **`temporal_correlation(traits_by_shot: list[str], gmax: int) -> dict` (§7)** — ported from
   `two_point_correlation`, re-indexed to generation g. Each element of `traits_by_shot` is a `G+1`-bit string
   `T₀…T_G`. Returns `{"C","c","C0","gmax"}`.
4. **`_mutation_schedule(client, generations, seed) -> tuple[list[float], list[dict]]`** — draw one mutation
   angle per generation from `client.fetch(size=…, fmt="hex")` bytes (§7 byte→angle map), building the shared
   angle list **and** the `entropy_provenance` records (request_id/receipt/entropy_epoch/timestamp/angle). Both
   arms consume this **same** list (CD-4). Fail-closed: let `QRNGUnavailable` propagate (abort the run).
5. **Quantum arm — `build_lineage_quantum(theta_seq, G) -> QuantumCircuit`** — one dynamic circuit:
   `QuantumRegister` for the genotype chain + one fresh phenotype ancilla per generation, `ClassicalRegister
   c(G+1)`. Per generation g: `apply_clone(parent→child)` (S0 U_M), `m_gate(theta_seq[g])` on child,
   `phenotype_map(child, pheno_g)`, `qc.measure(pheno_g, c[g])`. Feed-forward not required for S1 readout (it
   enters at S3 teleport); the dynamic-circuit register scaffolding is copied from the teleport-fork `run_hw`.
   (Ancilla-budget note in §9.)
6. **Classical surrogate — `run_classical_surrogate(theta_seq, G, shots, seed) -> list[str]`** — measure-and-resend
   (AC-S1.2), adapted from `run_sim`: per shot, walk the lineage classically — measure parent trait → classical
   bit → re-prepare a **separable** child biased by that bit, apply the same mutation angle, read `T_g`. Produces
   `shots` bitstrings `T₀…T_G`. Separable by construction (this is the null the quantum arm must beat). §11 Q3
   fixes the exact re-prep rule.
7. **Ideal cross-check (optional, single run) — `run_ideal(theta_seq, G) -> list[float]`** — exact-statevector
   `⟨σ_z⟩_p` per generation from the S0 `_z_expectation_statevector` for a `meta.arm="ideal"` sanity run
   (full confound *curve* is S2; here it is a one-off cross-check only).
8. **`sample_quantum_arm(qc, shots, args, backend, qubit_list) -> list[str]`** — dispatch: `--sim` →
   `SIM.run(transpile(qc, SIM), shots).result().get_counts()` expanded to per-shot `T₀…T_G` strings; hardware →
   `run_hw`-style dynamic path (copy teleport-fork: `generate_preset_pass_manager(opt_level=3, initial_layout=
   qubit_list)`, `run_sampler`, read the `c` register, bit-reversal `s[::-1]`).
9. **`run_once(args, seed, arm, client, backend, backend_name, calib, qubit_list) -> tuple[dict, str]`** —
   copy the `research_qtree.run_once` skeleton: seed, build the shared `theta_seq` + provenance from `client`,
   run the requested arm, compute per-generation `trait_sigmaz` and `temporal_correlation`, assemble the §4
   run.json, write it, return `(run_dict, path)`.
10. **`compute_gstar(per_gen_Cq, per_gen_Ccl, sigma, k) -> int`** — CD-5: `max g` where
    `|C_q(g) − C_cl(g)| > k·σ(g)`, else `1`. Called for k=2 and k=3.
11. **`main()`** — argparse (§ CLI below). Dispatch: if not `--sim` → `backend = connect(args.backend)`,
    `backend_name`, `calib = read_snapshot(backend)`, `qubit_list = best_chain(backend, n)[0]`; else sim
    qubit list. Construct `QRNGClient(qrng_url, QEAAS_API_KEY)` (abort if key/url missing). Loop
    `r in range(repeats)` × `arm in arms`: `run_once`. Aggregate per-generation `C(g)` mean/σ per arm across
    repeats (copy `research_qtree.main` aggregation), compute g\* (k=2, k=3), write summary.json, print the
    g\* line + per-arm `C(g)` table. **Fail-closed:** on `QRNGUnavailable`, print the abort reason and
    `raise SystemExit(1)` — do not fall back to PRNG.
12. **`if __name__ == "__main__": main()`**.

CLI (`main`):
| flag | type | default | note |
|---|---|---|---|
| `--generations` | int | 8 | lineage depth G (small scale for S1) |
| `--shots` | int | 4096 | per arm per repeat (§11 Q4) |
| `--seed` | int | 100 | base; repeat r uses seed+r (both arms) |
| `--repeats` | int | 5 | σ for g\* (CD-5) |
| `--backend` | str | None | Heron r2 auto-select when not `--sim` |
| `--sim` | BooleanOptionalAction | True | sim-first (CD-9) |
| `--arm` | {quantum,classical,both} | both | which inheritance channel(s) |
| `--corr-gmax` | int | =generations | max g for C(g) |
| `--k` | int | 2 | σ multiplier (k=3 always also reported) |
| `--mut-scale` | float | 0.1 | max mutation angle (matches S0 default) |
| `--qrng-url` | str | env `QEAAS_API_URL`, else `https://api.qeaas.eu/` | Q-EaaS base URL (Q5 resolved); no localhost default |
| `--name` | str | qdep_s1 | output tag |

No other files. `research_runs/` already exists (S0 created it).

---

## 7. The physics/maths S1 fixes (the load-bearing detail)

- **Temporal correlation (CD-3).** Copy `two_point_correlation`'s connected-correlation arithmetic. Input
  matrix `M` has one **row per shot** and one **column per generation** (`G+1` cols), so `M[:,g]` is the
  measured phenotype bit at generation g across shots. Compute `p = M.mean(axis=0)` (per-generation P(bit=1)),
  `C0 = mean(p*(1−p))` **or** the anchored `C(0)=Var(T₀)` (§11 Q2), and
  `C(g) = ⟨T₀ T_g⟩ − ⟨T₀⟩⟨T_g⟩` **anchored at generation 0** (per the CD-3 formula), i.e.
  `joint = (M[:,0]*M[:,g]).mean(); C(g)=joint − p[0]*p[g]`. Return `{"C","c","C0","gmax"}` with `c(g)=C(g)/C(0)`.
  *Note:* QuantumLife's version averages over all start positions `i` (`M[:,:n−d]*M[:,d:]`); the temporal study
  anchors at `T₀` (§11 Q2 — anchored is the proposed default because CD-3 writes `⟨T₀T_g⟩` explicitly). The
  normalized `c(g)` is invariant to the affine `⟨σ_z⟩=1−2·bit` rescaling, so bit-based correlation is faithful.
- **Trait per shot.** `T_g ∈ {0,1}` is the mid-circuit measurement outcome of the generation-g phenotype
  ancilla (S0 `phenotype_map`, `PHENO_BASIS=0`). A shot's record is the concatenation `T₀T₁…T_G`.
- **Quantum inheritance channel.** Coherent `apply_clone` (S0 U_M, `η=0.9` contraction) genotype→child, then
  `m_gate(θ_g)` mutation. The lineage stays coherent between clone steps; each generation's phenotype is read by
  a **fresh** ancilla so the readout schedule is identical for both arms (fairness — see §9).
- **Classical (measure-and-resend) channel.** Per generation: measure parent trait → classical bit → re-prepare
  a **separable** child state biased by that bit (§11 Q3 default: prepare child in `Ry` set so `⟨σ_z⟩_child =
  η·(1−2·bit)`, i.e. the *same* η-contraction but through a classically-communicated bit, no entanglement),
  then apply `m_gate(θ_g)`. This is separable by construction and is the honest null: it propagates classical
  Markov correlation that decays faster than the coherent arm — the gap is g\* (M3).
- **Byte→angle map (CD-7).** Fetch **once per repeat** for the whole schedule: `resp = client.fetch(size=32,
  fmt="hex")` (API constraint `32 ≤ size ≤ 4096`, else 422 — §12), decode `resp.data` hex to bytes, and derive
  one angle per generation from a disjoint byte slice: for generation g take 4 bytes → unsigned int `u`,
  `θ_g = mut_scale · (u / 2**32)` (uniform in `[0, mut_scale)`, matching S0's `random.uniform(0, mut_scale)`
  magnitude so the lifetime decay stays monotone). `size=32` covers up to 8 generations from one fetch; if
  `4·(G+1) > size`, fetch additional 32-byte blocks and concatenate. Log `request_id / receipt / entropy_epoch
  / timestamp / θ_g` per generation (`receipt` may be `null` — store as-is, opaque dotted token when present).
  Both arms index the **same** `theta_seq` from the **same** fetch (CD-4).
- **g\* (CD-5).** Aggregate `C(g)` mean±σ over `--repeats` per arm; `g* = max g : |C_q(g)−C_cl(g)| > k·σ(g)`,
  reported for k=2 (headline) and k=3. If the surrogate matches within k·σ at every g, `g*=1` (falsification,
  still reported — epic §5).

---

## 8. Manual verification (no automated tests)

Run from `artificial-life/code/` (sim-first, CD-9):

```bash
cd artificial-life/code
# sim, both arms, small scale
python stage1_temporal.py --generations 8 --shots 4096 --seed 100 --repeats 5 --arm both --name qdep_s1
# hardware confirm (after sim is clean)
python stage1_temporal.py --generations 6 --shots 4096 --seed 100 --repeats 3 --no-sim --backend '' --name qdep_s1_hw
```

- **AC-S1.1 (temporal re-aim)** — stdout prints a `C(g)` table for the quantum arm that is *non-flat* (temporal
  correlation exists), and `correlation_temporal.c[0]==1.0`. Confirm `temporal_correlation` consumes per-shot
  `G+1`-bit records (not per-generation circuits) — inspect one `run.json`'s `correlation_temporal.C` length `== G+1`.
- **AC-S1.2 (surrogate)** — the classical arm's `C(g)` decays to within noise of 0 faster than the quantum arm;
  both arms' `run.json` show the **same** `meta.entropy_provenance` `request_id`/`angle_rad` sequence (matched
  schedule). `meta.arm` is `"quantum"` vs `"classical"` on the two files.
- **AC-S1.3 (g\*)** — summary.json has `gstar.k2` and `gstar.k3` integers ≥ 1 and `per_generation[].C_g_mean/std`
  for both arms; stdout prints `g* (k=2) = N, g* (k=3) = M`.
- **CD-7 fail-closed** — with `QEAAS_API_KEY` unset (or url unreachable), the run **aborts** with a
  `QRNGUnavailable` message and exit 1; it never silently uses PRNG. Verify by unsetting the key once.
- **Schema check** — `python -c "import json;d=json.load(open('<run>'));print(d['meta']['arm'],
  d['correlation_temporal'].keys(), len(d['correlation_temporal']['C']), len(d['meta']['entropy_provenance']))"`
  → arm, `C/c/C0/gmax`, `G+1`, and one provenance record per generation.
- **Determinism** — same `--seed` with the QRNG **mocked/cached** reproduces the same `theta_seq` positions and
  (within shot noise) the same `C(g)` curve. (Live QRNG is non-deterministic by design — the *provenance*, not
  the value, is what's reproducible; note this in the run.)

---

## 9. Out-of-context risks / notes

- **Mid-circuit measurement disturbs the lineage.** `phenotype_map` CX-couples genotype→pheno ancilla, so
  measuring the pheno ancilla partially projects the genotype's Z component each generation. This is inherent to
  the resolved method (Q2: one lineage per shot, mid-circuit readout). It is **matched across both arms** (same
  readout schedule), so the g\* comparison stays fair (honesty invariant). Flagged because it caps the absolute
  `C(g)` magnitude — if the quantum arm's C(g) collapses to the surrogate's immediately, revisit whether a
  weaker (non-CX) phenotype coupling is needed before S2 scale-up (§11 Q3 touches this).
- **Ancilla/qubit budget.** One fresh phenotype ancilla per generation + the genotype chain ⇒ ~`2·(G+1)`
  qubits for the dynamic quantum circuit at depth G. Fine for statevector sim at S1's small G (≤8); on Heron r2,
  `best_chain` must find a chain long enough — keep S1's hardware G small (≤6) and let S2 push the ceiling.
- **QRNG request volume.** One `fetch` per generation per run; `repeats × generations × arms`(sharing the same
  stream ⇒ fetch once per (repeat, generation), not per arm). At S1 scale this is tiny; the copied client's
  429 `Retry-After` handling covers bursts. Cache the per-repeat `theta_seq` so both arms reuse it (CD-4) rather
  than double-fetching.
- **`timestamp()` under the stub returns `"sim"`** — repeat sim runs at the same `--seed`/`--name` overwrite the
  same filename (per-arm names differ by arm suffix). Vary `--name`/`--seed` to keep multiple sim runs; hardware
  runs use the real `timestamp()`.
- **Bit-reversal on hardware.** The teleport-fork `run_hw` reverses sampled bitstrings (`s[::-1]`); ensure the
  `c[g]` register ordering maps generation g → the correct column of the temporal matrix after reversal.
- No new pip dependency — `qiskit`, `qiskit_aer`, `numpy` already in the env; `qrng_client.py` uses stdlib `urllib`.

---

## 10. Ground rules honored

- Every AC (S1.1–S1.3) quoted verbatim from the epic / `qdep-1` / `QDEP` and mapped to a §8 manual check.
- Every file path in §6 is concrete; two new files, no edits outside `artificial-life/code/`.
- Epic cross-cutting decisions (CD-1..CD-9) adopted without re-arguing; CD-7 fail-closed and CD-3 axis re-aim called out.
- No tests, no test files, no test-impact section (project directive). Verification is manual (§8).
- Strict typing + Python idioms (`from __future__ import annotations`, full hints); no raw SQL.

---

## 11. Resolved decisions (developer, 2026-08-19)

- **Q1 — Reuse S0 operators: RESOLVED → COPY.** Copy `m_theta_matrix`, `m_gate`, `apply_clone`,
  `phenotype_map`, `_z_expectation_statevector` and constants `ETA/PHI/PHENO_BASIS/UNIT_TOL` verbatim into
  `stage1_temporal.py` with `# ported from stage0_reproduce.py` comments. Strict CD-1 parity — **no**
  `from stage0_reproduce import`. Drift risk accepted (the S0 physics is frozen; §12 gate re-checks it).
- **Q2 — Temporal correlation: RESOLVED → anchored at T₀** (default accepted). `C(g)=⟨T₀T_g⟩−⟨T₀⟩⟨T_g⟩`,
  `C(0)=Var(T₀)`, matching the CD-3 formula literally.
- **Q3 — Measure-and-resend re-prep: RESOLVED → η-contraction via classical bit** (default accepted). Child
  re-prepared separably so `⟨σ_z⟩_child = η·(1−2·bit)`, then `m_gate(θ_g)`. Arms matched on everything except
  coherence. Same CX phenotype map both arms (resolves the §9 fairness concern).
- **Q4 — Shot budget: RESOLVED → `--shots 4096`, `--repeats 5`** (default accepted). S2 re-tunes for scale.
- **Q5 — Q-EaaS base URL: RESOLVED → `https://api.qeaas.eu/`.** Resolve order `--qrng-url` → env
  `QEAAS_API_URL` → `https://api.qeaas.eu/` default. `QEAAS_API_KEY` from env/`.env`. No localhost fallback;
  fail-closed on missing key / `QRNGUnavailable` (CD-7). *(API contract vs `qrng-eaas/` docs verified — see §12.)*
- **Q6 — Ideal arm in S1: RESOLVED → off by default** (default accepted). S1 runs quantum + classical; the
  `run_ideal` cross-check (§6.7) is behind `--arm ideal`. Confound *curve* (M4) is S2.

---

## 12. Q-EaaS API contract — verified against `qrng-eaas/` docs

Confirmed the copied `qrng_client.py` matches the production service (sources: `qrng-eaas/api/qeaas/schemas.py`,
`api/main.py`, `api/qeaas/auth.py`, `api/qeaas/receipts.py`, `README.md`, `claude/plans/feature-epic2-public-api.md`):

- **Endpoint/method** — `GET /v1/random/bytes?size=<n>&format=<hex|base64>`. ✅ matches client.
- **`size` constraint** — `32 ≤ size ≤ 4096`; out of range → **422**. ⚠️ client must use `size ≥ 32` (§7 fixed to 32).
- **Auth** — header `X-API-Key: <plaintext>`; missing → 401 `missing_api_key`, bad → 401 `invalid_api_key`. ✅
- **Response** — `{request_id, format, data, entropy_epoch, timestamp (ISO-8601), receipt}`. ✅ all six names match.
- **`receipt` is nullable** — Ed25519-signed dotted token `V.b64url(payload).b64url(sig)` when present, else
  `null`. ⚠️ store as opaque string, never assume non-null (`entropy_provenance[].receipt` may be `null`).
- **Base URL** — `https://api.qeaas.eu` (Q5). `/v1` prefix for keyed endpoints. ✅
- **Errors** — 401 / 429 (`rate_limited`|`quota_exceeded`, always with `Retry-After`) / 503
  (`low_quantum_entropy`) / 422. Copied client's 401/429-`Retry-After`/503 retry policy matches. ✅
- Optional: `POST /v1/verify` (by `request_id` and/or `receipt`) exists for independent receipt verification —
  **not** needed by S1 (we only log receipts); note it for S4 provenance-audit if desired.

**No contract mismatch.** Only client-side action: use `size ≥ 32` and treat `receipt` as nullable.

---

## 13. After approval

Once answered/approved, run `/implement-feature artificial-life/plans/feature-S1-temporal.md`.
S1 gate before S2: a clean small-scale g\* in `--sim` (AC-S1.3) with the surrogate arm demonstrably below the
quantum arm, and the certified Q-EaaS provenance logged fail-closed (CD-7, M7).

---

## 14. Post-implementation notes

**Built.** Two new files, `--sim`-verified end-to-end against the **live** Q-EaaS service
(`https://api.qeaas.eu/`, real Ed25519 receipts logged):
- `artificial-life/code/qrng_client.py` — verbatim copy of the salt-testbed client (CD-1).
- `artificial-life/code/stage1_temporal.py` — temporal `C(g)` (anchored at T₀, Q2), one
  dynamic lineage circuit with per-generation mid-circuit readout, measure-and-resend
  classical surrogate (η-contraction via classical bit, Q3), optional ideal cross-check
  arm, certified Q-EaaS mutation schedule (fail-closed, CD-7), g\* (k=2/k=3), run/summary
  writers on the epic §4 contract.

**Deviations / notes for the developer:**
1. **`pipeline_common` location (plan §1 vs reality).** The plan's sys.path idiom pointed at
   `CalibrationGuidedHighYieldQRNG/code`, but `pipeline_common.py` only lives at
   `.../old/code/`. Used the teleport fork's probe (`code` → `old/code` → `new/code`) plus a
   stub fallback (ported from `sim_ideal_sign.py`) so `--sim` stays importable without the
   backend layer. No scope change; superset of the plan's intent.
2. **g\* domain fixed to g≥1.** `compute_gstar` excludes g=0 (that is `C(0)=Var(T₀)`, the
   normalisation anchor — raw variances differ between arms by construction). The plan's
   stated floor of `g*=1` (§7) is only self-consistent with a domain starting at generation 1.
3. **Empirical result at S1 scale = falsification (`g*=1`).** The two arms track each other
   closely (`C_q(g) ≈ C_cl(g)` within k·σ at every g≥1). This is the §9 risk materialising:
   the CX phenotype map mid-circuit-measured every generation partially projects the coherent
   genotype, collapsing the quantum arm toward the separable surrogate. The plan (§5/§7)
   explicitly accommodates falsification as a valid, reported outcome. **Follow-up for S2:**
   before scaling G, revisit whether a weaker (non-CX) phenotype coupling is needed so the
   coherent arm can outrun the surrogate (§9 flags this exact concern).
4. **Live QRNG non-determinism.** Each repeat draws fresh entropy; the *provenance* (not the
   angle value) is what reproduces. A repeat can legitimately draw θ₀≈0 → `Var(T₀)=0` →
   an all-zero `C(g)` row (seen at seed 104); handled gracefully (`C0≤1e-12 → c=0`), included
   in the mean/σ aggregation.
5. **No hardware run performed.** Sim-first gate (CD-9) is clean; the Heron-r2 `--no-sim`
   confirm (plan §8 second command) is left for the developer to run against a live backend.
