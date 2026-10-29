# D — Quantum growth: certified quantum generations + honest simulability

> Letter folder `D_quantum_growth/` of the Quantum Phantoms reverse-engineering epic ([epic](../epic-reverse-engineering.md)).
> Markdown is the source of truth; `python -m shared.site.build` renders it to `site/D_quantum_growth/index.html`.
> Target states live only in [`status.json`](status.json) (lifecycle: listed → dissected → reproduced → adapted → integrated | rejected).

## Purpose

<!-- What this pipeline stage does, in one paragraph, and what it hands to the next letter. -->
The non-classical part of growth. D-2: one-job dynamic-circuit lineage (mid-circuit measure, feed-forward, reset, hidden CHSH rounds). D-5: quantum causal-state model of a division-timing/fate process with measured memory advantage C_q < C_μ (the headline). D-3: heavy-hex Goldilocks QCA tissue patch whose snapshot becomes E's initial shape. A belief-propagation adversary runs on every circuit. D-4 (#10) is out of scope.

## Targets and their status

<!-- One row per target; the state column mirrors status.json (status.json wins on conflict). -->
| # | Target | Priority | Kind | State |
|---|---|---|---|---|
| #6 | [Quantum causal-state (memory-efficient) process models (Gu; Elliott; Wu; Palsson; Ghafari)](dossiers/06-quantum-causal-states.md) | ★★★ | quantum | adapted |
| #7 | [Goldilocks quantum cellular automata (Hillberry; Jones; Farrelly)](dossiers/07-goldilocks-qca.md) | ★★★ | quantum | adapted |
| #8 | [Dynamic-circuit feed-forward (Bäumer; Córcoles)](dossiers/08-dynamic-circuit-feedforward.md) | ★★★ | quantum | dissected |
| #9 | [Belief-propagation simulator of heavy-hex circuits (Tindall)](dossiers/09-bp-heavy-hex-adversary.md) | ★★ | classical | dissected |
| #10 | [Measurement-induced entanglement transition (Koh)](dossiers/10-measurement-induced-transition.md) | ★ | quantum | rejected (out of scope) |

## Inputs (contract files)

<!-- Contracts consumed, with the stub to use until the upstream letter exists (shared/stubs/). -->
- `tumor_draw` — stub: [`shared/stubs/tumor_draw/tumor_draw.json`](../shared/stubs/tumor_draw/tumor_draw.json) · schema: [`tumor_draw.schema.json`](../shared/contracts/tumor_draw.schema.json)
- `certificate` — stub: [`shared/stubs/certificate/certificate.json`](../shared/stubs/certificate/certificate.json) · schema: [`certificate.schema.json`](../shared/contracts/certificate.schema.json)
- `compiled_circuit` — stub: [`shared/stubs/compiled_circuit/compiled_circuit.json`](../shared/stubs/compiled_circuit/compiled_circuit.json) · schema: [`compiled_circuit.schema.json`](../shared/contracts/compiled_circuit.schema.json)

## Outputs (contract files)

<!-- Contracts produced; every output must pass `python -m shared.validate <file>`. -->
- `witness_record` — schema: [`witness_record.schema.json`](../shared/contracts/witness_record.schema.json) · stub example: [`shared/stubs/witness_record/witness_record.json`](../shared/stubs/witness_record/witness_record.json)
- `memory_advantage_record` — schema: [`memory_advantage_record.schema.json`](../shared/contracts/memory_advantage_record.schema.json) · stub example: [`shared/stubs/memory_advantage_record/memory_advantage_record.json`](../shared/stubs/memory_advantage_record/memory_advantage_record.json)
- `simulability_report` — schema: [`simulability_report.schema.json`](../shared/contracts/simulability_report.schema.json) · stub example: [`shared/stubs/simulability_report/simulability_report.json`](../shared/stubs/simulability_report/simulability_report.json)
- `quantum_lineage` — schema: [`quantum_lineage.schema.json`](../shared/contracts/quantum_lineage.schema.json) · stub example: [`shared/stubs/quantum_lineage/quantum_lineage.json`](../shared/stubs/quantum_lineage/quantum_lineage.json)
- `seed_shape` — schema: [`seed_shape.schema.json`](../shared/contracts/seed_shape.schema.json) · stub example: [`shared/stubs/seed_shape/seed_shape.json`](../shared/stubs/seed_shape/seed_shape.json)
- `quantum_job_record` — schema: [`quantum_job_record.schema.json`](../shared/contracts/quantum_job_record.schema.json) · stub example: [`shared/stubs/quantum_job_record/quantum_job_record.json`](../shared/stubs/quantum_job_record/quantum_job_record.json)

## How to run (sim commands)

All commands run from `reverse-engineering/` (python: conda base). Every quantum number is labelled "simulated: ideal" or "simulated: Heron-class noise (FakeMarrakesh)"; runs go to `D_quantum_growth/runs/<ts>-<tag>/` (gitignored) via `shared.runrecord`. Defaults for the three inputs are the `shared/stubs` files; override with `--tumor-draw`, `--certificate`, `--compiled-circuit`.

```bash
# whole hand-off in one run (lineage -> q-machine -> QCA -> seed shape -> BP adversary)
python -m D_quantum_growth.src.grow --mode ideal            # ~30 min, BP chi=16 on the QCA dominates
python -m D_quantum_growth.src.grow --mode heron            # ~45 min (noisy Aer, 12-qubit hexagon for the QCA)
python -m D_quantum_growth.src.grow --mode heron --dd       # DD lever on the lineage idle windows
python -m D_quantum_growth.src.grow --mode ideal --chsh-settings classical   # debug: S <= 2 -> rejected, exit 3
python -m D_quantum_growth.src.grow --mode ideal --certificate <fail cert>   # exit 2, "draw rejected"

# stages alone
python -m D_quantum_growth.src.lineage --mode ideal|heron [--dd] [--shots N]
python -m D_quantum_growth.src.memory_advantage --mode ideal|heron
python -m D_quantum_growth.src.qca --mode ideal|heron
python -m D_quantum_growth.src.bp --run D_quantum_growth/runs/<run_dir>

# reproductions
python -m D_quantum_growth.repro.causal_states_repro        # Gu + Wu, analytic
python -m D_quantum_growth.repro.jones_t6                   # T6, L = 11/15/17/23 ideal, L = 11 Heron
python -m D_quantum_growth.repro.baumer_long_range          # dynamic vs unitary Bell pair, n = 2..12
python -m D_quantum_growth.repro.tindall_kicked_ising       # proof-of-concept sweep (chi 2/4/8)
python -m D_quantum_growth.src.figures --ideal <run> --heron <run> [--lineage-heron <run> --heron-dd <run>]

# hand-off check to E (read-only use of E; delete E's run afterwards)
python -m E_classical_growth.src.grow --seed-shape D_quantum_growth/runs/<run>/seed_shape.json
```

A `grow` run writes `quantum_job_record_{lineage,qmachine,qca}.json`, `quantum_lineage.json`, `witness_record_{lineage,qca}.json`, `memory_advantage_record.json`, `simulability_report.json`, `seed_shape.json` + `seed_shape.npz`, `run.json`, the counts files and letter-local sidecars (`*_detail.json`). All contract files pass `python -m shared.validate`. Outputs are deterministic for a given certificate and mode (job ids are derived from the seed; checked byte-for-byte on the lineage and q-machine stages, ideal mode, two runs; the QCA and BP stages use the same construction but were not re-run twice).

## Reproduced result vs. paper

| Target | Paper | Ours | Agreement |
|---|---|---|---|
| #6 Gu perturbed coin [D06] | C_q < 0.5 (p > 0.2), < 0.1 (p > 0.4) | 0.4690 at p = 0.2, 0.0815 at p = 0.4 | analytic match |
| #6 Wu PMD [D16] | D_μ = log₂ N, D_q ≤ 1, statistically exact | n_causal = N, D_q = 1, survival error ≤ 2.2·10⁻¹⁶ (N = 2…16) | analytic match |
| #7 Jones T6 clustering, L = 17 [D14 Fig. 3] | ≈ 0.09 / 0.19 / 0.26 / 0.30 / 0.31 at t = 2/4/6/8/10 (figure reading, ±0.03) | 0.089 / 0.193 / 0.261 / 0.308 / 0.307; O(t) conserved to 2.5·10⁻¹⁴ | within reading tolerance (max 0.008); plan's ±0.02 not testable from a figure |
| #8 Bäumer long-range Bell pair [HW05] | dynamic beats unitary for chains ≳ 10 (CNOT teleportation) | ideal: F = 1.000 at all n ✓. Heron-class noise: no crossover up to n = 12 (n = 10: unitary 0.902 vs dynamic 0.890) | **not matched**; suspect readout ≫ 2q error, no feed-forward latency |
| #9 Tindall kicked Ising [HW04] | exact agreement for < 6 steps | BP vs exact light-cone: 5.7·10⁻³ (θ = π/4) and 4.3·10⁻² (θ = 1.0) at χ = 8, falling with χ | **proof of concept only**, not matched at χ ≤ 8 |

D-2 lineage (4 000 shots, one job):

| Sim mode | S_chsh | ⟨XX⟩+⟨ZZ⟩ per generation (> 1) | passed |
|---|---|---|---|
| simulated: ideal | 2.867 ± 0.033 | 1.54 – 1.76 | yes |
| simulated: Heron-class noise (FakeMarrakesh) | 2.602 ± 0.038 | 1.40 – 1.62 | yes |
| simulated: Heron-class noise, DD off / on (20 000 shots) | 2.660 ± 0.016 / 2.645 ± 0.017 | mean 1.4696 / 1.4669 (diff −0.0027 ± 0.0060) | **no measured effect** |

D-5 memory advantage (N = 8 division timer, L = 10, C_μ = 1.799, C_q theory 0.0640):

| Sim mode | d_KL quantum | d_KL 1-bit classical (same samples) | C_q measured | passed |
|---|---|---|---|---|
| simulated: ideal | 0.00192 | 0.00315 | 0.0627 ± 0.0054 | yes |
| simulated: Heron-class noise (FakeMarrakesh) | 0.00189 | 0.00315 | 0.1743 ± 0.0048 | yes |

The sampling floor is 0.00184; the exact 1-bit classical d_KL is 0.00136 (below the floor), so the advantage is small for this weakly modulated process.

D-3 QCA (t_max = 10, 4 000 shots):

| Sim mode | patch | SWAPs | best negativity | witness | seed shape |
|---|---|---|---|---|---|
| simulated: ideal | 21 qubits | 376 | 0.0167 ± 0.0055 (3.04σ) | passed (borderline) | 301 voxels, L1 |
| simulated: Heron-class noise (FakeMarrakesh) | 12-qubit hexagon | 0 | 0 (decohered) | **failed** | 90 voxels, **L0** |

BP adversary (`simulability_report`): smallest χ with fidelity_vs_sim ≥ 0.99 is 2 for the lineage blocks and the q-machine step (tiny circuits) and **none ≤ 16** for the QCA circuits (21-qubit patch 0.80 / 0.83 / 0.88 / 0.90 at χ = 2/4/8/16; hexagon saturates ≈ 0.96).

Figures: [`baumer_fidelity_vs_distance`](figures/baumer_fidelity_vs_distance.png), [`gu_perturbed_coin`](figures/gu_perturbed_coin.png), [`wu_pmd_memory`](figures/wu_pmd_memory.png), [`cellcycle_memory_advantage`](figures/cellcycle_memory_advantage.png), [`lineage_witness`](figures/lineage_witness.png), [`jones_t6_population`](figures/jones_t6_population.png), [`jones_t6_network`](figures/jones_t6_network.png), [`qca_snapshot_2d`](figures/qca_snapshot_2d.png), [`qca_mi_network`](figures/qca_mi_network.png), [`tindall_magnetisation`](figures/tindall_magnetisation.png), [`simulability`](figures/simulability.png).

## Claim level and honesty notes

L1 (lineage witness; QCA witness only where it passes) and L1′ (memory advantage). **Never L2 / L3**; nothing here is "classically impossible" or "quantum biology". Everything is simulation; the in-job CHSH is "certification-ready, not certified (simulated)".

- **Lineage (L1).** Fate is read from the pair's joint outcome in the coin's basis, never from a single-qubit Z phase dial. Fate-rotation angles are illustrative constants, not fitted biology. The test mask lives only in the job record.
- **Memory advantage (L1′).** Wu's exact 1-qubit model; the measured advantage over a 1-bit classical model is real but small (details in dossier #6). C_q(measured) < C_μ is nearly automatic for a qubit.
- **QCA (L1 / L0).** The ideal 21-qubit witness passes at 3.04σ for the best of 22 edges with no look-elsewhere correction: weak. The Heron-noise hexagon fails, so its seed shape carries claim L0 ("MI structure only, no L1"). The exact "one neighbour" rule is not SWAP-free on the full patch (376 SWAPs); the odd-parity shortcut differs by up to 0.57 in population and was not used. The Heron QCA is a 12-qubit hexagon, not the 21-qubit patch (Aer cost).
- **Dynamic-circuit crossover not reproduced** (#8) and **DD has no measured effect**. XY4 DD is not available on this target, so X–X echoes are inserted by hand into explicit idle windows.
- **BP (#9).** BP is a classical approximation; "smallest χ ≥ 0.99" is the measured simulability number. The Tindall reproduction is a proof of concept (χ ≤ 8).
- **Seeds and hidden choices** come from the certificate seed via `shared.seedhash`; no MVP or QALife/QDEP code is imported.


## Pipeline readiness

<!-- readiness: prototype -->

D runs standalone, but the hand-off from B is not real: `grow --tumor-draw` only records the draw as an upstream
reference, and the lineage uses fixed fate angles (`PHI0, DPHI = 0.5, 0.35`) with the parent in |1⟩
(`src/lineage.py:26, 135`), so every chain tumour gets the same founder. Under Heron-class noise the QCA witness fails
(seed shape L0) while `witness_record` still says L1 (CCR-D4). D's BP adversary cannot take B's circuits (probe
`runs/20261029-185947-probe-gaps`: `--circuit` missing, `--run` required).

**Weak links**

| Weak link | Kind | Why it limits reliability | Evidence | To strengthen |
|---|---|---|---|---|
| Founder ignores B's draw | integration | the quantum growth is the same for every drawn tumour: D is wired, not integrated | `lineage.py:26, 135`; runner check `_post_grow_q` | founder preset from draw `type × margin`, lineage seed from `shape_seed_hex` (plan AC-8) |
| QCA witness fails under Heron | component | the seed shape E grows from carries L0 only | D-3 table: negativity 0 (decohered), witness failed | smaller patch, DD, or ideal-only L1 with the Heron result as the honest bound |
| Ideal QCA witness 3.04σ, best of 22 edges | assumption | no look-elsewhere correction; weak even when it passes | D-3 table | Bonferroni / pre-registered edge |
| BP adversary not reusable | gap | B's circuits have no simulability number | probe `D.bp_b` | `bp --circuit <compiled_circuit.json>` |
| Witness `claim_level` const L1 | contract | a failed witness is still labelled L1 | CCR-D4 | allow L0 on fail |
| Memory advantage small | component | d_KL 0.00189 vs 0.00315 at a sampling floor of 0.00184 | D-5 table | a more strongly modulated process |

**Used as-is in the chain?** Runs with the chain's flags, but the draw does not influence it; not integrated in substance. Full gap list: [INT](../INT_integration/README.md); whole chain: [index](../index.html).


## Future

Shared, pipeline-wide context (end goal, digital-twin path, cross-letter risks) lives once in the
[whole-pipeline Future](../future.md). This section covers only what this letter adds. Every claim carries a label:
<span class="chip evidence">evidence-based</span> (a number in this repo or a cited paper), <span class="chip extrapolation">extrapolation</span> (a reasoned step beyond the evidence),
<span class="chip speculative">speculative</span> (possible, not supported yet).

### 1. Aim of the paper(s)

- **[D06] Gu et al. ("Occam's quantum razor"):** quantum models of stochastic processes can need **less memory**
  than the best classical model.
- **[D07] Palsson, [D08] Ghafari:** experimental demonstrations of that memory advantage (photonic).
- **[D16] Wu:** quantum dimensionality reduction for stochastic simulation; **[D17] Elliott:** memory-efficient tracking.
- **[D13] Hillberry, [D14] Jones, [D03] Farrelly:** "Goldilocks" quantum cellular automata, simple local rules that
  produce complex, entangled dynamics, run on hardware.
- **[HW05] Bäumer:** dynamic circuits (measure mid-circuit, then feed forward). **[HW04] Tindall:** a classical
  belief-propagation (BP) simulator that reproduces such hardware experiments.

Why it matters: these papers ask where a quantum description of a growth-like process is *genuinely more compact*,
and BP checks honestly whether a classical simulator does just as well.

### 2. Contribution

- Analytic matches: Gu's perturbed coin (C_q 0.4690 at p = 0.2) and Wu's PMD (D_q = 1). <span class="chip evidence">evidence-based</span>
- Jones T6 clustering within figure-reading tolerance (max deviation 0.008). <span class="chip evidence">evidence-based</span>
- Lineage witness that survives Heron-class noise: S_chsh 2.602 ± 0.038, ⟨XX⟩+⟨ZZ⟩ 1.40–1.62 (L1). <span class="chip evidence">evidence-based</span>
- Memory advantage: C_q measured 0.1743 against C_μ 1.799 under Heron noise. The distortion gap is small
  (d_KL 0.00189 vs 0.00315, floor 0.00184) (L1′). <span class="chip evidence">evidence-based</span>
- The QCA witness passes ideal (3.04σ) and **fails** under Heron noise (L0). BP finds none ≤ χ 16 for the 21-qubit
  QCA. Bäumer's crossover is **not** reproduced. <span class="chip evidence">evidence-based</span>

### 3. Role in cancer detection

**Honest position:** D gives **no direct detection benefit** today. <span class="chip evidence">evidence-based</span> Its possible end goal is indirect:
compact stochastic models of cell fate and division timing that make large virtual-cohort simulation cheaper, and
seed shapes that E grows from. Clinical relevance would require fitting these models to real cell or imaging data,
which nobody has done. <span class="chip speculative">speculative</span>

### 4. Beyond lungs

- **Process-agnostic.** The memory-advantage framework applies to any stochastic process: cell-cycle timing, immune
  dynamics, switching between drug-sensitive and resistant states. <span class="chip extrapolation">extrapolation</span>
- **Classical competitors.** Tensor-network solvers of the chemical master equation [D09–D12] are the baseline any
  biological use must beat. <span class="chip evidence">evidence-based</span>

### 5. Long-term vision: toward a digital twin

<div class="callout speculative">

<span class="chip speculative">speculative</span> A twin is many coupled stochastic processes tracked over time. If the memory advantage holds for *complex*
processes, quantum process models could store patient-state histories more compactly [D17]. Path:
(1) 1-qubit models with small advantage (now) → (2) multi-qubit models of realistic cell-cycle data →
(3) coupled process models inside a twin. Step 2 has no evidence yet.

</div>

### 6. Predictions

**5 years**
*Assumptions:* noisy devices; shallow heavy-hex circuits that BP simulates.
- Small blocks keep their witness under Heron noise (lineage S 2.602); large QCA patches do not. <span class="chip evidence">evidence-based</span>
- Shallow circuits are BP-simulable at small χ (lineage χ = 2), so no classical-hardness claim is made. <span class="chip evidence">evidence-based</span>
- Memory advantage is shown on hardware for 1–2-qubit process models (photonic precedent [D07, D08]). <span class="chip extrapolation">extrapolation</span>

**10 years**
*Assumptions:* tens of logical qubits; fast mid-circuit feed-forward.
- QCA patches move beyond BP's reach. (No χ ≤ 16 at 21 qubits is a hint, not a proof.) <span class="chip extrapolation">extrapolation</span>
- Multi-qubit causal-state models are fitted to measured cell-cycle statistics. <span class="chip extrapolation">extrapolation</span>

<div class="callout speculative">

**15 years**
*Assumptions:* fault-tolerant hardware.
- <span class="chip speculative">speculative</span> Quantum simulation of large stochastic tissue models in regimes where classical tensor methods fail would
  be a claim-level-L2 result, and fault tolerance is what would make it testable. Whether biology needs those
  regimes is itself an open question.

</div>

### 7. Risks and obstacles

| Risk | Kind | Why it matters | Mitigation |
|---|---|---|---|
| Classical simulability | technical | BP or tensor networks may match any shallow circuit | BP number next to every claim |
| Witness fragility | technical | QCA witness fails under Heron noise | smaller patches; error mitigation |
| Illustrative parameters | validation | fate angles are constants, not fitted to biology | fit to cell-tracking data before any biological claim |
| Overclaiming | regulatory | "quantum" in a medical context invites unfounded readings | claim ladder L0–L3 on every number |
| Draw not wired | technical | D ignores B's tumour (INT finding) | founder from draw (plan AC-8) |

## References (paper codes)

<!-- Codes refer to ../../papers/<code>_*.pdf (gitignored, local only). -->
[D03], [D06], [D07], [D08], [D13], [D14], [D15], [D16], [D17], [HW04], [HW05], [HW06] — PDFs in `../../papers/` (local only). Full context: [`../reverse-engineering-targets.md`](../reverse-engineering-targets.md).

## Contract change requests

<!-- Never edit shared/. Record needed contract changes here (contract, field, why, local workaround);
     INT applies them in one place. -->
- **CCR-D1: `quantum_job_record`, multi-circuit jobs.** *Need:* the q-machine job runs 3 tomography circuits and the QCA job 20, but the record has one `transpiled_hash` and one counts dict. *Request:* optional `transpiled_hashes[]` (as CCR-C1). *Local workaround:* `transpiled_hash` = sha256(canonical_json([per-circuit hashes])); counts are merged in a `counts_file` with a binary circuit-index prefix ("00 0101…").
- **CCR-D2: `memory_advantage_record`, distortion field.** *Need:* `passed` depends on d_KL, but there is no field for it. *Request:* add `d_kl_bits_per_symbol` (quantum and best classical baseline). *Local workaround:* values in `process_description` and the sidecar `memory_advantage_detail.json`.
- **CCR-D3: `witness_record`, CHSH block.** *Need:* the lineage S_chsh (value, stderr, n test samples). *Request:* optional `chsh` block (plan Q7a). *Local workaround:* `S_chsh` as an observable `{value, stderr}`.
- **CCR-D4: `witness_record.claim_level` is const `L1`.** A failed QCA witness still says L1 with `passed: false`; only `seed_shape.claim_level` can be L0. *Request:* allow L0 when `passed` is false, or leave as is and document.
- **CCR-D5: `quantum_job_record.fake_backend` const `FakeMarrakesh`** blocks job records for repro-only geometry (Eagle for #9); those scripts write no job record (plan Q7b).
- **CCR-D6: `quantum_lineage.fate` is an array per generation.** One entry per generation is emitted here; the schema suggests one entry per cell/pair. Clarify.
- **CCR-D7: `witness_record.mi_network` indices.** `nodes` are strings (physical qubit ids) and `edges[].i, j` index into `nodes`; the schema does not say which. Clarify.
