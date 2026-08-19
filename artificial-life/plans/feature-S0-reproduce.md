# Feature Plan — S0: Reproduce (`stage0_reproduce.py`)

**Status:** Complete
**Epic:** `artificial-life/plans/epic-qdep-coherence-depth-genealogy.md` (Status: **Approved**)
**Stage ID:** S0 (first of 5; no dependency — gates S1)
**Artifact:** `artificial-life/code/stage0_reproduce.py`
**Source specs:** `qdep-1-coherence-depth-genealogy.md` (Stage 0), `QDEP_Living_Genealogies.md` (§5, §6.1, §9, §10)
**Borrows from:** `QuantumLife/code/sim_ideal_sign.py`, `QuantumLife/code/genome.py`, `QuantumLife/code/research_qtree_teleport.py`
**Author:** Claude (Opus) · **Date:** 2026-08-19

> No GitHub issue — this study uses stage IDs, not tickets (project convention).
> No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

S0 is the toolchain-proving checkpoint. Rebuild the Alvarez-Rodriguez et al. (2018) single-lineage
"quantum biomimetic" result with the **exact** operators, run it on a noiseless statevector simulator,
and show the phenotype "lifetime" observable `⟨σ_z⟩_p` decays across generations in agreement with the
ideal model (M1). No correlation metric, no surrogate arm, no QRNG, no hardware — those are S1+.

This stage fixes three things the rest of the epic depends on and must not re-derive:
1. The mutation operator `M(θ)` and the approximate-clone unitary `U_M(θ)`.
2. The **genotype→phenotype ancilla map** that produces the trait observable `⟨σ_z⟩_p` (CD-3, Q3).
3. The `research_runs/*.json` output shape for `meta.arm="ideal"` (§4 of epic).

### What already exists (integration points)
- `QuantumLife/code/sim_ideal_sign.py` — the noiseless-reference pattern to copy: `AerSimulator(method="statevector")`,
  a `pipeline_common` stub so the file imports without backend access (lines 10–15), a `unit_test()` doing
  L1-distance logical-equivalence checks (tol `0.03`), and a per-generation loop (`ideal_sign`).
- `QuantumLife/code/research_qtree_teleport.py` — `OUTPUT_DIR = ../research_runs` (line 114), `timestamp()`
  via `pipeline_common`, `build_env` (unused here), argparse conventions in `main()`.
- `QuantumLife/code/genome.py` — `GENOME_SPEC` / `decode_slot` bit-decode contract (borrow only if the
  genotype encoding is reused; S0's minimal register does not need the 6-bit slot layout — see §3).
- `artificial-life/code/` — **does not exist yet**; S0 creates it. `artificial-life/.env` holds `QEAAS_API_KEY`
  (unused in S0; S1+ only).

---

## 2. Acceptance criteria

Verbatim from epic §10 (which quotes `qdep-1` Stage 0 and `QDEP` §9/§10). IDs added.

- **AC-S0.1** (verbatim, `qdep-1`): "Rebuild the 2018 single-lineage result with the *exact* operators from
  the paper/wiki: `M(θ)` mutation, `U_M(θ)` imperfect clone, `⟨σ_z⟩_p` lifetime. Success = the noiseless-sim
  agreement the 2018 work reported."
  **Covered by** `stage0_reproduce.py:200` (`unit_test`) — run output: worst L1(M_gate)=0.0000, worst L1(U_M)=0.0000, both `< 0.03`, both printed "equivalent".
- **AC-S0.2** (verbatim, `QDEP` §9): "Fidelity vs. ideal model per generation (the 2018 work reported close
  agreement at small scale — reproduce that first)."
  **Covered by** `stage0_reproduce.py:247` (`ideal_lifetime` per-gen fidelity) — every generation `fidelity_vs_ideal ≥ 0.9905` and `|diff| ≤ 3·stderr` [ok] for all 6 gens.
- **AC-S0.3** (epic §10): "the `⟨σ_z⟩_p` phenotype shows the expected exponential 'lifetime' decay across
  generations in noiseless sim."
  **Covered by** `stage0_reproduce.py:262` (`ideal_lifetime` decay + ratio print) — `trait_sigmaz` monotone 1.000→0.764 across gens 0–5; successive ratios 0.928/0.964/0.953/0.977/0.917 ≈ constant η=0.9.

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New dir `artificial-life/code/` + new file `stage0_reproduce.py`.
- `M(θ)` mutation gate, `U_M(θ)` approximate-clone unitary, genotype→phenotype ancilla map, `⟨σ_z⟩_p` readout.
- A `unit_test()` verifying `M(θ)` and `U_M(θ)` against their defined matrices (L1 / operator-fidelity, copied
  pattern from `sim_ideal_sign.unit_test`).
- An `ideal_lifetime(gens)` that runs the single lineage on the statevector sim and reports `⟨σ_z⟩_p` +
  per-generation fidelity-vs-ideal.
- One `run.json` per invocation with `meta.arm="ideal"` and the §4 fields.
- CLI: `--generations --shots --seed --name` (`--sim` defaults true; S0 is sim-only).

### Out of scope (deferred to their stages)
- Temporal correlation `C(g)`, surrogate/measure-and-resend arm, g\* — **S1**.
- Scaling G, ideal-clone confound sweep, error bars over `--repeats` — **S2**.
- Teleport / SWAP routing, `logical_depth` comparison, `Δg*` — **S3**.
- Figures, paper, honesty-invariant aggregation — **S4**.
- QRNG / Q-EaaS certified entropy (CD-7 wires it from **S1**; S0 stays on `random.seed`).
- Hardware run on Heron r2 (S0 is `--sim` only; no `pipeline_common.connect` call).
- Death, interaction, population > 1, feed-forward selection (CD-8 — absent, not stubbed).

---

## 4. Data model — `run.json` (subset written by S0)

Written to `OUTPUT_DIR = ../research_runs` (relative to `artificial-life/code/`, i.e.
`artificial-life/research_runs/`), name `<name>_sim_seed<K>_<ts>_run.json` (mirrors QuantumLife;
`ts = timestamp()`, which returns `"sim"` under the stub — acceptable for S0, real timestamp on hardware stages).

```jsonc
{
  "meta": {
    "project": "artificial-life",
    "study": "coherence-depth-genealogy",   // §4 new study tag
    "arm": "ideal",                          // §4 — S0 is ideal-only
    "backend": "sim", "sim": true,
    "timestamp": "sim", "seed": <K>,
    "generations": <G>, "shots": <S>,
    "operators": { "M_theta": "[[cosθ,sinθ],[sinθ,-cosθ]]", "U_M": "<clone-spec, §7>" },
    "calibration": null                      // §4 reused verbatim (no backend in S0)
  },
  "generations": [
    {
      "gen": 0,
      "trait_sigmaz": <float>,               // §4 new — ⟨σ_z⟩_p this generation
      "fidelity_vs_ideal": <float>,          // §4 new — sim vs closed-form ideal
      "shots": <S>
    }
    // ... one per generation
  ]
}
```

- Field names `meta.study`, `meta.arm`, `generations[].trait_sigmaz`, `generations[].fidelity_vs_ideal` are
  the epic §4 contract — do not rename; S1/S4 consume them.
- No `correlation_temporal`, no `per_generation`, no `gstar`, no `meta.entropy_provenance` in S0 (later stages).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **CD-1** Copy, don't import — copy the `sim_ideal_sign.py` statevector + `pipeline_common`-stub pattern and
  any genome decode helper into `stage0_reproduce.py` with provenance comments (`# ported from QuantumLife/code/<file>`).
- **CD-2** `pipeline_common` stays external — add the `sys.path` hook / stub even though S0 never calls a backend,
  for parity with S1+ (matches `sim_ideal_sign.py` lines 10–15).
- **CD-3** Trait = **phenotype** `⟨σ_z⟩_p` via the genotype→phenotype ancilla map (QDEP §5). S0 **fixes** this map.
- **CD-8** Minimal build — single linear lineage, one observable, population = 1, no death/interaction/teleport.
  Code paths absent, not stubbed.
- **CD-9** Sim-first — S0 is the pure-sim floor of this discipline; no hardware branch at all.

---

## 6. File plan (concrete paths)

All Python: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`
(QuantumLife idiom). No raw SQL (N/A). No business logic in any non-existent template. One new file.

### `artificial-life/code/stage0_reproduce.py` (new)

Structure, top to bottom:

1. **Module docstring** — what S0 proves; provenance note (ported from `sim_ideal_sign.py`).
2. **Imports + `pipeline_common` stub** — copy `sim_ideal_sign.py` lines 5–15 verbatim (stub `connect`/
   `run_sampler`/`qpu_seconds`, `timestamp = lambda: "sim"`, `sys.path.insert`). `import numpy as np`, `math`,
   `json`, `os`, `argparse`, `functools`, `random`. `from qiskit import QuantumCircuit, QuantumRegister,
   ClassicalRegister, transpile`; `from qiskit_aer import AerSimulator`. `SIM = AerSimulator(method="statevector")`.
3. **`OUTPUT_DIR`** — `os.path.normpath(os.path.join(_HERE, "..", "research_runs"))` (copy line 114 idiom).
4. **Operators (§7):**
   - `def m_gate(theta: float) -> qiskit.circuit.Gate` — builds `M(θ) = [[cosθ,sinθ],[sinθ,−cosθ]]` via
     `UnitaryGate`, asserts unitarity.
   - `def apply_clone(qc, parent, ancilla, theta) -> None` — the approximate-clone `U_M(θ)` (§7 spec):
     fixed entangling unitary, parent genotype → fresh ancilla.
   - `def phenotype_map(qc, genotype, pheno_ancilla) -> None` — genotype→phenotype ancilla map (CD-3, §7);
     `⟨σ_z⟩` on `pheno_ancilla` is the trait.
5. **`def unit_test() -> None`** — copy the L1/fidelity-equivalence pattern from `sim_ideal_sign.unit_test`
   (grid of θ, tol `0.03`): assert `m_gate(θ)` matches the paper matrix and `U_M` reproduces the expected
   partial-copy expectation values. Prints PASS/FAIL per operator.
6. **`def ideal_sigmaz(theta_seq: list[float]) -> list[float]`** — closed-form / exact-statevector ideal
   `⟨σ_z⟩_p` per generation, no shot noise (the reference the sampled run is scored against).
7. **`def build_generation(gen: int, theta: float) -> QuantumCircuit`** — one generation's circuit: genotype
   prep, `U_M` clone into next-gen ancilla, `phenotype_map`, measure phenotype ancilla. Single lineage (CD-8).
8. **`def ideal_lifetime(args) -> dict`** — the run loop over `range(args.generations)`: build → statevector
   sample (`SIM.run(transpile(qc, SIM), shots=args.shots)`) → estimate `⟨σ_z⟩_p` from counts → compute
   `fidelity_vs_ideal` against `ideal_sigmaz` → append `{gen, trait_sigmaz, fidelity_vs_ideal, shots}`. Advance
   the genotype angle per the 2018 protocol (`M(θ)` mutation between generations; θ schedule from `random.seed(args.seed)`).
   Returns the `run.json` dict (§4).
9. **`def write_run(run: dict, args) -> str`** — `os.makedirs(OUTPUT_DIR, exist_ok=True)`, dump to
   `<name>_sim_seed<seed>_<ts>_run.json` (copy the QuantumLife writer path idiom, lines 514–517).
10. **`def main() -> None`** — argparse (`--generations` default 6, `--shots` default 4096, `--seed` default 100,
    `--name` default `qdep_s0`, `--sim` default `True`). Runs `unit_test()` first (gate), then `ideal_lifetime`,
    prints per-gen `⟨σ_z⟩_p` + fidelity, writes run.json, prints its path.
11. **`if __name__ == "__main__": main()`**.

No other files. `artificial-life/research_runs/` is created on first run by `os.makedirs`.

---

## 7. Operators & the phenotype map (the physics S0 must fix)

These are the load-bearing definitions; §11 flags the ones needing developer sign-off.

- **Mutation `M(θ)`** — fully specified by the spec: real symmetric involution
  `M(θ) = [[cosθ, sinθ], [sinθ, −cosθ]]` (a reflection; `M(θ)² = I`). Single-qubit gate on the offspring genotype.
  θ per generation from `random.seed(args.seed)` in S0 (certified Q-EaaS replaces this from S1, CD-7).
- **Approximate clone `U_M(θ)`** — spec says only "fixed entangling unitary, parent genotype → fresh ancilla,
  no-cloning ⇒ variation" (QDEP §6.1). Proposed concrete form (§11 Q1): the 2018 biomimetic 1→2 partial-clone —
  a `Ry(φ)` on the fresh ancilla followed by `CX(parent → ancilla)` (a controlled partial copy), φ fixed so the
  ancilla inherits `⟨σ_z⟩` at a fixed contraction factor `η<1` per generation (this is what produces the
  exponential lifetime decay of AC-S0.3). The exact 2018 UQCM angle is the thing to confirm.
- **Genotype→phenotype map** — spec (QDEP §5): "phenotype derived from the genotype through interaction with an
  ancilla; its expectation value is the trait." Proposed (§11 Q2): a fixed `CX(genotype → pheno_ancilla)` after a
  fixed `Ry` basis rotation, so `⟨σ_z⟩` on the phenotype ancilla tracks the genotype's `⟨σ_z⟩` — the "lifetime."
- **Lifetime decay (AC-S0.3)** — with `η<1` per-generation contraction from `U_M`, `⟨σ_z⟩_p(g) ≈ η^g · ⟨σ_z⟩_p(0)`:
  monotone exponential decay `ideal_sigmaz` predicts and the sampled run must match within M1 tolerance.

**M1 agreement tolerance (the S0 gate)** — proposed (§11 Q3): per-generation
`|trait_sigmaz_sampled − ideal_sigmaz| ≤ 3·shot_stderr` **and** operator `unit_test()` L1 `< 0.03` (the
`sim_ideal_sign.py` tolerance). Both must pass for S0 to gate S1.

---

## 8. Manual verification (no automated tests)

Run from `artificial-life/code/`:

```bash
cd artificial-life/code
python stage0_reproduce.py --generations 6 --shots 4096 --seed 100 --name qdep_s0
```

- **AC-S0.1** — `unit_test()` prints `M(θ) == matrix (equivalent)` and `U_M == partial-clone (equivalent)` with
  worst-case L1 `< 0.03`. If either DIFFERS, S0 fails — do not proceed to S1.
- **AC-S0.2** — stdout per-gen table shows `fidelity_vs_ideal ≥ ~0.99` at every generation; `run.json`
  `generations[].fidelity_vs_ideal` confirms.
- **AC-S0.3** — per-gen `⟨σ_z⟩_p` is monotone-decreasing and fits `η^g·⟨σ_z⟩_p(0)` (eyeball the printed curve;
  ratio of successive gens ≈ constant `η`).
- **Schema check** — `python -c "import json;d=json.load(open('<path>'));print(d['meta']['study'],d['meta']['arm'],
  len(d['generations']),d['generations'][0].keys())"` shows `coherence-depth-genealogy ideal 6` and keys
  `gen, trait_sigmaz, fidelity_vs_ideal, shots`.
- **Determinism** — same `--seed` reproduces the same θ schedule and (within shot noise) the same trait curve.

---

## 9. Out-of-context risks / notes

- `timestamp()` under the `pipeline_common` stub returns the literal `"sim"`, so repeat runs at the same seed
  **overwrite** the same filename. Acceptable for S0 (single ideal run per seed); S1+ run on hardware with the
  real `timestamp()`. If multiple S0 runs must coexist, vary `--name` or `--seed`.
- Statevector sim of a single genotype+ancilla+phenotype register per generation is tiny (≤ ~3 qubits/gen,
  and generations are sampled sequentially, not held simultaneously) — no qubit-budget concern at S0.
- `qiskit` / `qiskit_aer` must be importable in the env; the QuantumLife files already rely on them, so the
  project env has them. No new dependency.

---

## 10. Ground rules honored

- Every AC (S0.1–S0.3) quoted verbatim from the epic / `qdep-1` / `QDEP` and mapped to a §8 manual check.
- Every file path in §6 is concrete; one new file + one new dir.
- Epic cross-cutting decisions (CD-1,2,3,8,9) adopted without re-arguing; CD-7 (QRNG) correctly deferred to S1.
- No tests, no test files, no test-impact section (project directive).
- Strict typing + PSR-equivalent Python idioms (type hints, `from __future__ import annotations`); no raw SQL.

---

## 11. Resolved decisions

- **Q1 — `U_M(θ)` exact form. RESOLVED (developer, 2026-08-19):** accept the **fixed-η stand-in** as S0's "exact
  operator" — 2018 biomimetic 1→2 partial clone = fixed `Ry(φ)` on fresh ancilla + `CX(parent→ancilla)`, φ set
  for per-generation contraction `η≈0.9`, yielding the exponential lifetime decay of AC-S0.3. No need to chase
  the exact 2018 Alvarez-Rodriguez UQCM angle.
- **Q2 (default accepted on approval) — genotype→phenotype ancilla map exact gate.** **Proposed default:** fixed `Ry(basis)` + `CX(genotype→
  pheno_ancilla)`, `⟨σ_z⟩` on the phenotype ancilla = trait. *Accept, or specify a different fixed map from the
  QDEP wiki?* (This map is frozen here and reused unchanged by S1–S4, so it matters.)
- **Q3 (default accepted on approval) — M1 gate tolerance.** per-gen `|sampled − ideal| ≤ 3·shot_stderr` AND operator
  `unit_test()` L1 `< 0.03`. *Accept these thresholds as the S0→S1 gate?*
- **Q4 (default accepted on approval) — mutation angle magnitude / schedule for S0.** Default: small random θ per generation from
  `random.seed(args.seed)`, magnitude `~0.1 rad` (QDEP "small random angle"). *Fix a specific mutation-rate
  default, or leave as a `--mut-scale` CLI knob (default 0.1)?* **Implemented as `--mut-scale` (default 0.1),
  drawn `random.uniform(0, mut_scale)` — positive magnitude so the σ_x-mixing term stays same-signed and the
  lifetime decay is monotone (see §13).**

---

## 12. Post-implementation

**Built:** one new file `artificial-life/code/stage0_reproduce.py` + new dir `artificial-life/research_runs/`
(created on first run). Sim-only (statevector `AerSimulator`; no backend, no `pipeline_common.connect`). Runs
`unit_test()` as a hard gate, then the single-lineage `ideal_lifetime` loop, writes one `run.json` (§4 shape,
`meta.arm="ideal"`).

**Verified (sim only)** — `python stage0_reproduce.py --generations 6 --shots 4096 --seed 100`:
- AC-S0.1 — `unit_test`: worst L1 = 0.0000 for both `M(θ)` and `U_M`, `< 0.03`.
- AC-S0.2 — per-gen `fidelity_vs_ideal ∈ [0.9905, 0.9998]`; all `|sampled−ideal| ≤ 3·shot_stderr`.
- AC-S0.3 — `trait_sigmaz` monotone 1.000→0.764; successive ratios ≈ η=0.9.
- Schema — `run.json`: `meta.study=coherence-depth-genealogy`, `meta.arm=ideal`, `meta.backend=sim`,
  `meta.sim=true`, 6 generations, gen keys `{gen, trait_sigmaz, fidelity_vs_ideal, shots}`.

**Physics decisions frozen for S1–S4 (do not re-derive):**
- `ETA=0.9` ⇒ `PHI=acos(0.9)`; clone contraction `⟨σ_z⟩_offspring = η·⟨σ_z⟩_parent`.
- `PHENO_BASIS=0.0` ⇒ phenotype ancilla `⟨σ_z⟩` exactly tracks the final genotype (Q2 default).
- Mutation schedule: `random.uniform(0, mut_scale)`, `mut_scale=0.1` (Q4).
- Ideal reference is the **exact statevector** `⟨σ_z⟩` (no shot noise); `fidelity_vs_ideal = 1 − |sampled−ideal|/2`.

**Follow-ups for the developer:**
- `apply_clone(qc, parent, ancilla, phi=PHI)` matches the plan's `apply_clone(qc, parent, ancilla, theta)`
  signature but the third arg is the fixed clone angle `phi`, not a mutation θ (mutation is the separate
  `m_gate`). Intentional per Q1 (fixed-η stand-in); flagged so S1 wires the certified-QRNG angle into
  `m_gate`, not the clone.
- `timestamp()` under the stub returns `"sim"`, so repeat runs at the same `--seed`/`--name` overwrite the
  same `research_runs/*_run.json` (plan §9). Vary `--name`/`--seed` to keep multiple S0 runs.
- Lineage circuit grows to `gen+2` qubits (8 at gen 6) — trivially fine for statevector; noted because it is
  a growing-chain rebuild, not the ≤3-qubit sequential reuse §9 sketched. No qubit-budget concern at S0.
```
