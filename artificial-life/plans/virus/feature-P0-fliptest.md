# Feature Plan — P0: Flip-test kill-gate (`stage5_fliptest.py`)

**Status:** Complete
**Epic:** `artificial-life/plans/virus/epic-stonewall-virus.md` (Status: **Approved**)
**Phase ID:** P0 (first of 4; depends on nothing; **gates** P1–P3 as a real kill-gate)
**Artifact:** `artificial-life/code/stage5_fliptest.py`
**Source spec:** epic §9 P0 brief + §3 (CD-1..CD-6) + §5 (observables B, D) + §8 (Q1, Q4)
**Borrows from (copy, don't import — CD-1):**
- `artificial-life/code/stage3_teleport.py` — `_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True)` @330, `_swap_cx(qc, lo, hi)` @315 (constant-depth vs SWAP-ladder long-range CNOT)
- `artificial-life/code/stage4_qalife.py` — `apply_self_replication` (clone `cx`, exact ⟨Z⟩ copy), `xbasis_witness_from_counts(counts, qubits) -> (joint, sep)`, `_x_string_op`, witness-ideal (`SparsePauliOp`/`Statevector`) machinery, `_z_expectation`, `selftest()` discipline
- `artificial-life/code/stage4_scale.py` — the whole run/JSON/CLI skeleton: `gated_chain(backend, nq, args)`, `run_counts(qc, shots, args, backend, qubit_list)`, `qrng_thetas`, backend dispatch, results-dict/filename convention
- `artificial-life/code/layout.py` — `best_chain(backend, n, time_budget=40.0) -> (qubit_list, stats)` (live-calibration SWAP-free chain + `stats["twoq_err_max"]`/`stats["readout_max"]`)
- `artificial-life/code/qrng_client.py` — `QRNGClient`, `QRNGUnavailable` (certified fail-closed; unchanged)

**Author:** Claude (Opus) · **Date:** 2026-08-26

> No GitHub issue — this study uses phase IDs, not tickets (project convention, per [[qrng-eaas-plan-workflow]]).
> No tests (project directive): production code + manual verification only (§8).

---

## 1. Context & goal

QALife Month-4 measured the genealogical entanglement witness `⟨X^⊗W⟩` out to **W24 / 48 qubits** on
`ibm_kingston`, and there teleport-routing **lost twice**: on one long fragile line (witness ~0.03, no headroom) a
constant-depth teleport bond could not beat a plain SWAP ladder — the many-body witness was already too fragile to
absorb teleport's mid-circuit-measurement error (see [[qdep-setup-bug-fix]], [[qalife-month4-full-model]]).

The stone-wall thesis (epic §1): teleport should **win** across **many small healthy blocks** (W12, per-block
witness ~0.30, ample headroom) separated by **wide stone walls** (inter-block separation ≫ the ~8-qubit per-bond
gate-count crossover `d*`). The M4 loss was a *headroom* failure, not a *distance* failure.

**P0 is the cheapest experiment that can kill the epic.** It strips the virus down to the bare cross-block
transmission bond: two W12 blocks, one generation, one infection bond A→B, measured cross-block transmission
witness under **swap-routed** vs **teleport-routed** infection, over a **block-separation d-sweep** (Q4). If
teleport does not clear the 2σ null while swap stays buried, at some separation, the epic's quantum headline (D) is
dead and P1–P3 must be re-scoped **before any further build** (epic §7 step 1).

P0 deliberately carries **no genome, no selection, no second generation, no third block** — those are P1/P2
(epic §9 P0 "Out of scope"). The only quantum object here is the transmission bond's coherence across the wall.

### What already exists (integration anchors — concrete)

- `stage4_scale.py` is the skeleton copied wholesale (CD-1): `gated_chain` (CD-6 fail-closed chain gate),
  `run_counts` (sim/hardware dispatch, `SIM.run(transpile(...))` vs `generate_preset_pass_manager(opt=3)` + `pm.run`
  + `run_sampler`), `qrng_thetas` (32-byte hex blocks → angles, fail-closed), backend selection
  (`connect(args.backend)` vs `backend=None`, `backend_name="…_sim"`), results-dict + `json.dump(indent=2,
  default=str)` to `OUTPUT_DIR = ../research_runs`, `_read_env_key`.
- `stage3_teleport.py::_teleport_cx` @330 — Bell pair + two mid-circuit measures + optional feed-forward `if_test`
  on `tel[2k]`,`tel[2k+1]`; `feedforward=False` = heralded (post-select `tel==00`). Callers `qc.reset([a1,a2])`
  between chained CNOTs. `_swap_cx` @315 — `~2·(hi−lo)` SWAPs, O(distance) depth, identity permutation, no ancilla.
- `stage4_qalife.py::xbasis_witness_from_counts(counts, qubits) -> (joint, sep)` — `joint = ⟨∏ X_i⟩`,
  `sep = ∏⟨X_i⟩`; bit read little-endian `s = 1 − 2·(bits[-(q+1)]=="1")`. `apply_self_replication(qc, parent, child)`
  = clone `cx`. Witness-ideal via `_x_string_op(nq, qubits)` (label index `nq−1−q`) + `Statevector`.
- `layout.best_chain(backend, n)` — returns `(qubit_list, stats)`; **raises `RuntimeError`** if no length-`n`
  SWAP-free chain. `stats` carries `twoq_err_max`, `readout_max`, `twoq_err_mean`, `sx_max`, `dead_avoided`.

---

## 2. Acceptance criteria

Verbatim from epic §9 (P0 brief). IDs preserved; each maps to a §8 manual check.

- **AC-P0.1** (verbatim): "Two W12 blocks built on disjoint `best_chain` regions; chain-quality gate passes per
  block (CD-6)."
- **AC-P0.2** (verbatim): "Cross-block witness measured for both swap-routed and teleport-routed infection arms."
- **AC-P0.3** (verbatim): "Run over a block-separation d-sweep (adjacent = teleport-predicted-lose control, far =
  predicted-win) (Q4); verdict reported against the 2σ null; **strict flip** required — teleport clears 2σ while
  swap is buried (Q1)."
- **AC-P0.4** (verbatim): "Noiseless-sim check: swap and teleport arms agree with each other and with the ideal GHZ
  witness (=1)."

**AC coverage (each mapped to a §8 manual check):**

| AC | Covered by | §8 check |
|---|---|---|
| AC-P0.1 | `gated_chain` (`stage5_fliptest.py:217`, returns `(qubit_list, qstats)`, aborts exit 1 on bad chain / `best_chain` `RuntimeError`) selects one SWAP-free chain `L = 2·W + d` per d; block A = `chain[0:W]`, wall = `chain[W:W+d]`, block B = `chain[W+d:2W+d]`. Whole-chain gate bounds each block (CD-6, Q-P0.2); `chain_stats` echoed per block (`stage5_fliptest.py:578-586`). Standalone per-block `<X^W>` headroom sanity on each block's real qubits via `run_block_witness` (`stage5_fliptest.py:329`) → `per_block_witness` (~0.30 hw, 1.0 sim — verified `A=B=1.0`). | §8-A: hardware run aborts fail-closed when a block's chain is bad; run.json records per-block `twoq_err_max`/`readout_max`, the passed thresholds, and `per_block_witness`. |
| AC-P0.2 | Two matched arms per d — `swap` (`_swap_cx`) and `teleport` (`_teleport_cx`) route the single A→B infection CX in `build_flip_circuit` (`stage5_fliptest.py:242`); identical schedule/shots otherwise. Cross-block witness in `run_arm` (`stage5_fliptest.py:416`); arm dict written at `stage5_fliptest.py:587`. | §8-B: `summary["dsweep"][i]["arms"]` has both `swap` and `teleport` with `witness_joint_mean`, `separable_mean`, `signal_mean`, `signal_sigma`, `logical_depth`, `ancillas` — verified (`arm keys ['swap','teleport']`). |
| AC-P0.3 | d-sweep over `--separations` (default `2,48`: adjacent `d=2` control + far `d=48`); per arm per d: `signal = joint − sep`, `sigma` over `--repeats` + shot-noise floor; `clears_2sigma = signal_mean > k·sigma` (`stage5_fliptest.py:452`); `strict_flip = teleport.clears_2sigma and not swap.clears_2sigma` (`stage5_fliptest.py:591`); verdict = PASS iff any far-d strict_flip (`stage5_fliptest.py:606`). | §8-C: at `d=2` (control) `strict_flip` False; at far `d`, `strict_flip` True ⟹ **PASS**; else **STOP**. Verdict printed + in `summary["kill_gate"]` — verified control/far booleans + STOP on noiseless sim. |
| AC-P0.4 | Reduced-width noiseless statevector run: both routings are the same logical map ⟹ identical `signal` within shot noise (verified swap≈teleport=+1.000), and the ideal cross-block witness (`witness_ideal_crossblock`, `stage5_fliptest.py:341`) = 1.0 via `Statevector` + `_x_string_op`. | §8-D: `--sim --width 3 --separations 2,4 --routing both` → swap ≈ teleport `signal`; `witness_ideal == 1.000000000`; **Δ(signal) = 0 by construction** on noiseless sim (verified). |

---

## 3. Scope

### In scope
- New file `artificial-life/code/stage5_fliptest.py`. Copies `stage4_scale.py`'s run/JSON/CLI skeleton + the two
  routing primitives + the witness machinery, then adds the two-block flip experiment. **No edits to any existing
  file.**
- **Two W12 blocks on one gated chain, split by a stone wall.** `gated_chain(backend, L=2·W+d, args)` per d; block
  A = first `W`, stone wall = middle `d` (idle spacer qubits = the "unused couplers"), block B = last `W`. This
  yields disjoint blocks **and** makes the block separation `d` the natural sweep variable (AC-P0.3).
- **Per-block intra-block genealogy.** Each block = a clone chain: founder `ry(pi/2, block[0])`, then
  `apply_self_replication(block[i-1], block[i])` for `i=1..W-1` (within-block GHZ; per-block witness ~0.30 = the
  headroom the thesis needs). **One generation only** (no mutation schedule applied to genealogy depth here;
  QRNG angles are fetched for provenance parity but the founder/clone chain is the M4 W-witness prefix).
- **One cross-block infection bond A→B**, routed by `--routing`:
  - `swap` — `_swap_cx(qc, lo=A_tail, hi=B_head)` across the `d`-wide wall (O(distance) SWAP ladder).
  - `teleport` — `_teleport_cx(qc, ctrl=A_tail, tgt=B_head, a1, a2, tel, k, feedforward=True)` (2 corridor
    ancillas placed in the stone wall; constant depth; `tel` ClassicalRegister width `2`).
  - `both` (default) — run both matched arms so the flip falls out at each d.
  where `A_tail = chain[W-1]` (last locus of A) and `B_head = chain[W+d]` (founder of B). The infection CX seeds
  B's founder **coherently** from A so the transmitted genealogy is one connected GHZ across the wall (a
  measure-and-resend infector would collapse it → `signal ≈ 0`, the honesty invariant, CD-4).
- **Cross-block transmission witness B (epic §5).** `xbasis_witness_from_counts(counts, [A_tail, B_head])` →
  `(joint, sep)`; `signal = joint − sep` = the connected cross-block coherence across the bond. `=1` (ideal) for a
  genuinely entangled transmitted genealogy, `≈0` for any classical infector. (Span defaults to the bonded pair;
  `--witness-span` can widen it — see §11 Q-P0.1.)
- **d-sweep (AC-P0.3, Q4).** `--separations` (default `1,48`): adjacent `d=1` = teleport-predicted-lose negative
  control; far `d=48` = teleport-predicted-win. The d-sweep is the flip proof.
- **Strict-flip verdict (AC-P0.3, Q1).** Per arm per d: 2σ-null clearance; `strict_flip = teleport clears ∧ swap
  buried`. Kill-gate PASS iff strict flip at ≥1 far separation.
- **Noiseless-sim validation (AC-P0.4).** Reduced `--width` statevector run: swap ≡ teleport (identical logical
  map, Δsignal=0 by construction) and ideal cross-block GHZ witness = 1. Guarded by `--sv-max-qubits` (default 26).
- **Certified fail-closed QRNG (CD-7 parity).** `qrng_thetas` fetched (receipts logged); fail-closed on
  `QRNGUnavailable`. Angles carried for provenance parity with M4 even though P0's one-generation genealogy uses
  the fixed founder/clone prefix (documented, not silently unused).
- **Honesty rails (CD-4).** Only `signal = joint − sep` is the quantum claim. Any diagonal ⟨σz⟩ / alive-count is
  **absent** in P0 (no phenotype/selection) — nothing to mislabel.
- CLI mirrors `stage4_scale.py` + adds: `--separations`, `--routing {swap,teleport,both}`, `--witness-span`,
  `--sv-max-qubits`, `--herald`.

### Out of scope (deferred to later phases — epic §9 P0 "Out of scope")
- **Genome** (`[q_witness, b1, b2]`), **selection** (1-ancilla fitness), **>1 generation**, **3rd block C**, and
  the **chain infection A→B→C** — all **P1** (`stage5_virus.py`). P0 has G=1 witness locus per individual only.
- The multi-generation run, the 2D environment sweep (damping γ × mutation), the phase diagram — **P2**
  (`stage5_run.py`).
- The web demo, `CONCLUSION_MONTH5.md`, cross-phase aggregation — **P3**.
- **Density/damping arm.** P0 is unitary-only (statevector sim); no amplitude-damping bath, no `DensityMatrix` sim.
- Re-deriving the witness math, the routing primitives, the QRNG client, the chain gate — frozen upstream, copied
  verbatim (CD-1).

---

## 4. Data model — `run.json` / `summary.json` (P0 fields)

Written to `OUTPUT_DIR = ../research_runs` (i.e. `artificial-life/research_runs/`; created if absent),
`json.dump(..., indent=2, default=str)`. Filename convention mirrors `stage4_scale.py`:

- Per-run (one per arm × repeat × d): appended to `meta.run_files`.
- Summary: `f"{args.name}_fliptest_{backend_name}_{tag}.json"` where
  `tag = timestamp() if not args.sim else "sim"` (copied idiom).

```jsonc
{
  "meta": {
    "stage": 5, "phase": "P0", "model": "stonewall_virus_fliptest",
    "backend": "sim|<hw>", "sim": true|false,
    "width": <W>,                       // individuals per block (12 on hw)
    "blocks": 2, "generations": 1,
    "separations": [1, 48],             // the d-sweep (Q4)
    "routing": "both",
    "witness_span": "bond",             // "bond" (2 loci) | "full" (2W)
    "shots": <S>, "repeats": <R>, "k": 2.0,
    "herald": false,
    "max_twoq_err": 0.05, "max_readout_err": 0.15,
    "mut_scale": <f>, "qrng_url": "<url>",
    "entropy_provenance": [ { "request_id": "...", "receipt": "..." } ],  // CD-7 parity
    "run_files": [ ... ]
  },
  "dsweep": [
    { "d": <int>,
      "chain": [ <phys qubits, length 2W+d> ],
      "chain_stats": { "block_a": {"twoq_err_max": <f>, "readout_max": <f>},
                       "block_b": {"twoq_err_max": <f>, "readout_max": <f>} },
      "per_block_witness": { "block_a": <f>, "block_b": <f> },   // intra-block ⟨X^⊗W⟩ sanity (~0.30 hw)
      "arms": {
        "swap":     { "witness_joint_mean": <f>, "separable_mean": <f>,
                      "signal_mean": <f>, "signal_sigma": <f>,
                      "clears_2sigma": <bool>, "logical_depth": <int>, "ancillas": 0 },
        "teleport": { "witness_joint_mean": <f>, "separable_mean": <f>,
                      "signal_mean": <f>, "signal_sigma": <f>,
                      "clears_2sigma": <bool>, "logical_depth": <int>, "ancillas": 2,
                      "herald_frac": <f|null> }
      },
      "strict_flip": <bool>,            // teleport.clears_2sigma AND NOT swap.clears_2sigma
      "control": <bool>                 // true for the adjacent (d=1) predicted-lose point
    }
  ],
  "witness_ideal": <f|null>,            // noiseless statevector cross-block GHZ witness (=1); null on hw
  "kill_gate": {
    "flip_at": [ <far d values with strict_flip> ],
    "verdict": "PASS" | "STOP",         // PASS iff any far-d strict_flip
    "note": "PASS → proceed to P1; STOP → re-scope epic headline (D) before build (epic §7)."
  }
}
```

`signal_sigma` = quadrature of the per-repeat std and the shot-noise floor `1/sqrt(shots)` (mirror
`stage4_scale.py`'s `ws = sqrt(std^2 + 1/shots)`). `logical_depth = qc.depth()` per arm (teleport ≈ constant, swap
∝ `d`) — the D-crossover evidence carried into P3.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **CD-1** Copy, don't import — copy `stage4_scale.py`'s skeleton, `stage4_qalife.py`'s witness/operator helpers,
  and `stage3_teleport.py`'s `_swap_cx`/`_teleport_cx` verbatim into `stage5_fliptest.py` with `# ported from …`
  provenance comments. No `from stage4_scale import …`.
- **CD-4** Two observables, one claim — cross-block `signal = joint − sep` (B) + the teleport-vs-swap crossover (D)
  are the quantum headline (no classical surrogate). P0 has no population/alive-count (no phenotype), so there is
  nothing diagonal to mislabel; keep it that way.
- **CD-5** Infection bond = the cross-block CX; swap arm = SWAP ladder, teleport arm = teleported CX (the
  `SWAP = 3× teleport-CX` corridor pattern is P1's chain-infection concern; P0's single bond is one teleported CX).
- **CD-6** Chain-quality gate, fail-closed — `gated_chain` per d; whole-chain gate bounds each block (conservative
  ⟹ per-block pass). Abort exit 1 on gate fail or `best_chain` `RuntimeError`.
- **CD-7** Certified QRNG — `qrng_thetas` fetched, receipts logged, **fail-closed** on `QRNGUnavailable`; no PRNG
  fallback on hardware (sim may use `q4._sim_thetas`, clearly labelled).
- **Q1** Flip metric = **STRICT** — pass only if teleport clears 2σ *while* swap is buried; any weaker
  teleport>swap margin does **not** count (AC-P0.3).
- **Q4** Block separation = **both** — adjacent (control) *and* far (predicted win); the d-sweep is the flip proof.

---

## 6. File plan (concrete paths)

Python idioms: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`.
No raw SQL (N/A). **One new file, no edits elsewhere.**

### `artificial-life/code/stage5_fliptest.py` (new)

1. **Module docstring** — what P0 proves (the stone-wall teleport-flip on the minimal 2-block × W12 × 1-generation
   transmission bond, swap vs teleport, d-sweep, strict-flip kill-gate); the honesty note (Δsignal=0 on noiseless
   sim by construction — swap/teleport are the same logical map; the flip is a *decoherence* effect on hardware);
   provenance (ported from `stage4_scale.py`, `stage4_qalife.py`, `stage3_teleport.py`).
2. **Imports + dual-path setup** — copy `stage4_scale.py`'s header verbatim: qiskit + `qiskit_aer.AerSimulator`,
   `SIM = AerSimulator(method="statevector")` (P0 is unitary-only — statevector, **not** density_matrix),
   `generate_preset_pass_manager`, the `pipeline_common` sys.path probe + stub (`connect`, `run_sampler`,
   `timestamp`), `OUTPUT_DIR = Path(__file__).parent.parent / "research_runs"`, `QEAAS_URL_DEFAULT`,
   `from qrng_client import QRNGClient, QRNGUnavailable`, `_read_env_key`.
3. **Routing primitives — ported (CD-1):** `_swap_cx(qc, lo, hi)` and
   `_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True)` copied verbatim from `stage3_teleport.py`
   (`# ported from stage3_teleport.py`).
4. **Witness helpers — ported (CD-1):** `xbasis_witness_from_counts(counts, qubits)`, `_x_string_op(nq, qubits)`,
   `_z_expectation` copied verbatim from `stage4_qalife.py` (`# ported from stage4_qalife.py`).
5. **`qrng_thetas(client, n, mut_scale, repeat)` + `gated_chain(backend, nq, args)`** — copied verbatim from
   `stage4_scale.py` (fail-closed QRNG; fail-closed chain gate). `gated_chain` returns `(qubit_list, qstats)`.
6. **`build_flip_circuit(width, d, routing, feedforward, thetas) -> tuple[QuantumCircuit, int]`** — the P0 core:
   - Allocate `QuantumRegister(2*width + d, "q")` (block A = `q[0:width]`, wall = `q[width:width+d]`,
     block B = `q[width+d:2*width+d]`), a `ClassicalRegister(2*width, "c")` for the data measurements, and (teleport
     only) `ClassicalRegister(2, "tel")`.
   - Build block A genealogy: `qc.ry(pi/2, A[0])`; `apply_self_replication(qc, A[i-1], A[i])` for `i=1..width-1`.
   - **Infection bond A→B** (`A_tail = A[width-1]`, `B_head = B[0] = q[width+d]`):
     `swap` → `_swap_cx(qc, lo=A_tail, hi=B_head)`; `teleport` → pick `a1,a2` from the wall
     (`q[width], q[width+1]`), `_teleport_cx(qc, A_tail, B_head, a1, a2, tel, k=0, feedforward)`, then
     `qc.reset([a1,a2])`.
   - Build block B genealogy seeded from `B_head`: `apply_self_replication(qc, B[j-1], B[j])` for `j=1..width-1`
     (B's founder is now the coherently-transmitted A locus ⟹ one connected GHZ across the wall).
   - X-basis rotation for the witness: `qc.h(qb)` on every data locus in A∪B (mirror `stage4_scale.build_measured`),
     then measure the `2*width` data loci into `c`.
   - Return `(qc, qc.depth())` (depth = the D-crossover evidence).
7. **`witness_ideal_crossblock(width, d, span_qubits) -> float`** — noiseless cross-block GHZ witness via
   `_x_string_op` + `Statevector` on the routing-independent logical circuit (no measurement, no routing ancillas),
   for AC-P0.4. Returns 1.0 for the connected GHZ (bond span) ideally.
8. **`run_arm(width, d, routing, args, backend, qubit_list, thetas) -> dict`** — build via `build_flip_circuit`,
   dispatch via a copied `run_counts(qc, shots, args, backend, qubit_list)` (sim: `SIM.run(transpile(...))`;
   hardware: `generate_preset_pass_manager(opt=3, initial_layout=…)` + `pm.run` + `run_sampler`; collapse
   `"<c> <tel>"` keys onto `c`; heralded post-select `tel==00` when `--herald`). Compute `(joint, sep)` via
   `xbasis_witness_from_counts` over the witness-span loci (bonded pair by default). Aggregate over `--repeats`:
   `signal_mean`, `signal_sigma` (quadrature + shot-noise floor), `clears_2sigma`, `logical_depth`, `ancillas`,
   `herald_frac`. Also compute the intra-block per-block witness (`per_block_witness`) as the AC-P0.1 sanity.
9. **`main()`** — copy `stage4_scale.py`'s `main` and adapt:
   - argparse (mirror S4 + P0 additions): `--sim/--no-sim` (`set_defaults(sim=True)`), `--backend`, `--width`
     (default 12; sim runs override small, e.g. 3), `--separations` (default `"1,48"`), `--routing
     {swap,teleport,both}` (default `both`), `--witness-span {bond,full}` (default `bond`), `--shots` (8192),
     `--repeats` (3), `--k` (2.0), `--mut-scale` (0.10), `--max-twoq-err` (0.05), `--max-readout-err` (0.15),
     `--allow-bad-chain`, `--sv-max-qubits` (26), `--herald` (default False), `--qrng-url`, `--name`
     (default `stonewall_p0`).
   - backend: `if not args.sim: backend = connect(args.backend); backend_name = backend.name` else
     `backend = None; backend_name = "statevector_sim"`.
   - QRNG: `api_key = _read_env_key("QEAAS_API_KEY")`; abort exit 1 if missing; `client = QRNGClient(url, key)`;
     `client.health()` must be ok; else abort (sim may fall back to `q4._sim_thetas` with a printed label).
   - **sv guard:** on `--sim`, if `2*width + max(separations) > args.sv_max_qubits` abort with a clear message
     (reduce `--width`/`--separations`). Hardware path skips the guard (156q).
   - d-sweep loop: for each `d` in `separations`: `L = 2*width + d`; hardware → `qubit_list, qstats =
     gated_chain(backend, L, args)`; sim → `qubit_list = list(range(L)), qstats = {}`. For each routing in the arm
     set (`both` → `["swap","teleport"]`), call `run_arm`. Compute `strict_flip`, `control = (d == min(separations))`.
   - kill-gate: `far = [d for d in separations if d != min(separations)]`; `flip_at = [d for d in far if
     dsweep[d].strict_flip]`; `verdict = "PASS" if flip_at else "STOP"`. Print the verdict banner.
   - AC-P0.4: on `--sim`, compute `witness_ideal` via `witness_ideal_crossblock` and assert-print it ≈ 1.0.
   - Write summary JSON (§4 shape) to `OUTPUT_DIR`.
10. **`if __name__ == "__main__": main()`**.

CLI additions over the copied `stage4_scale.py` flags:

| flag | type | default | note |
|---|---|---|---|
| `--separations` | str | `1,48` | comma list of block separations `d` (the d-sweep, Q4); first = adjacent control |
| `--routing` | {swap,teleport,both} | both | how the A→B infection CX is routed; `both` = matched flip pair |
| `--witness-span` | {bond,full} | bond | witness loci: bonded pair (`A_tail,B_head`) or full 2W span (Q-P0.1) |
| `--sv-max-qubits` | int | 26 | noiseless-sim qubit cap; abort if the block×2+d layout exceeds it |
| `--herald` | flag | False | teleport-only heralded post-select `tel==00` (small-scale noise-filter cross-check) |

No other files. `research_runs/` created on first write if absent.

---

## 7. The physics/maths P0 fixes (the load-bearing detail)

- **What is routed, and only that.** The two arms are byte-identical except the single infection CX(A_tail→B_head):
  `swap` spends `~2·d` SWAPs (O(distance)); `teleport` spends a constant-depth Bell pair + 2 mid-circuit measures +
  feed-forward. Everything else (both block genealogies, the H rotations, the data measurement) is shared. This is
  the matched comparison the flip demands.
- **Why the flip is a decoherence effect (central honesty point, carried from S3).** `_swap_cx` and `_teleport_cx`
  implement the **same logical** CNOT. On a noiseless statevector they yield identical states ⟹ identical `signal`
  ⟹ **Δsignal = 0 by construction** (AC-P0.4). The difference is *depth*, and depth only converts to a witness gap
  under **decoherence** — i.e. on `ibm_kingston`. Therefore the noiseless `--sim` run validates the pipeline + the
  `logical_depth` split only; the **flip signal lives on hardware**. Do **not** report the sim's Δsignal=0 as a null.
- **Why the stone-wall flips the M4 verdict.** M4 measured one W24 witness (~0.03, no headroom) so teleport's
  mid-measure error sat on top of an already-dead signal and lost. P0's per-block W12 witness (~0.30) has headroom,
  and the *cross-block* observable is the **connected two-point** across the bond — not a 24-fold product — so it is
  not re-entering the fragile many-body regime. The routing acts on one bond whose coherence the connected witness
  reads directly. At small `d` (control) teleport's fixed ancilla/mid-measure overhead exceeds the ~`2·d` swap
  depth ⟹ teleport predicted to lose; at large `d` (≫ the ~8-qubit crossover `d*`) swap's O(distance) depth
  decoheres the bond while teleport stays constant ⟹ teleport predicted to win = the flip.
- **The strict-flip metric (Q1, AC-P0.3).** Per arm per d: `signal = joint − sep`, `sigma` over repeats +
  shot-noise floor. `clears_2sigma = signal_mean > 2·sigma`. `strict_flip(d) = teleport.clears_2sigma ∧ ¬
  swap.clears_2sigma`. Kill-gate PASS iff `strict_flip` at ≥1 far `d`. A merely-larger teleport signal that does
  not bury swap is **not** a flip (do not weaken this to salvage a PASS).
- **Connected witness kills the classical surrogate (CD-4).** `joint = ⟨X_{A_tail} X_{B_head}⟩`,
  `sep = ⟨X_{A_tail}⟩⟨X_{B_head}⟩`; a measure-and-resend infector collapses the bond in Z ⟹ `joint → sep` ⟹
  `signal → 0`. So `signal > 0` is genuine cross-block quantum coherence, no classical fake.
- **Qubit budget & the sv guard.** Hardware: `L = 2·W + d = 24 + d`; at far `d≈48`, `L≈72` (+2 teleport ancillas)
  — fits 156q `ibm_kingston` comfortably, with the two blocks + wall disjoint by construction. Noiseless
  statevector caps at `--sv-max-qubits` (26) ⟹ AC-P0.4 runs at small `--width` (e.g. `W=3`, `d≤4`). Abort clearly
  when the sim budget blows; never OOM.
- **Heralded teleport statistics.** With feed-forward (default) any d is fine. `--herald` post-selects `tel==00`;
  with one teleport bond kept fraction ≈ 0.25 — usable, recorded as `herald_frac`. Herald is a small-scale
  noise-filter cross-check, not the headline path (feed-forward is).
- **Entropy provenance (CD-7).** `qrng_thetas` fetched once, receipts logged into `meta.entropy_provenance`,
  fail-closed on `QRNGUnavailable`. P0's one-generation genealogy uses the fixed `ry(pi/2)` founder + clone-chain
  prefix; the fetched angles are carried for parity/provenance with M4 and are documented as such (not silently
  unused).

---

## 8. Manual verification (no automated tests)

Run from `artificial-life/code/` (sim-first):

```bash
cd artificial-life/code
# A) noiseless sim: pipeline + logical_depth split + AC-P0.4 (Δsignal=0 by construction, witness_ideal=1)
python stage5_fliptest.py --sim --width 3 --separations 2,4 --routing both \
    --shots 8192 --repeats 3 --name p0_sim
# B) hardware flip-test: the real d-sweep on ibm_kingston (the kill-gate)
python stage5_fliptest.py --no-sim --backend '' --width 12 --separations 2,48 --routing both \
    --shots 8192 --repeats 3 --name p0_hw
# C) herald cross-check (teleport-only noise filter), small
python stage5_fliptest.py --no-sim --backend '' --width 12 --separations 48 --routing teleport \
    --herald --shots 8192 --repeats 3 --name p0_herald
```


***RUNS***

(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage5_fliptest.py --sim --width 3 --separations 2,4 --routing both --shots 8192 --repeats 3 --name p0_sim 
Q-EaaS  : https://api.qeaas.eu/  health: ok
=== Stage 5 / P0 flip-test: width=3 separations=[2, 4] routing=both on statevector_sim ===
  d=  2 per-block <X^W> headroom: A=+1.000 B=+1.000
  d=  2 swap     : signal=+1.000+-0.011  depth=  10  CLEARS 2sigma
  d=  2 teleport : signal=+1.000+-0.011  depth=  12  CLEARS 2sigma
  d=  4 per-block <X^W> headroom: A=+1.000 B=+1.000
  d=  4 swap     : signal=+1.000+-0.011  depth=  14  CLEARS 2sigma
  d=  4 teleport : signal=+1.000+-0.011  depth=  12  CLEARS 2sigma
  witness_ideal (noiseless cross-block GHZ, span=full): 1.000000000  (AC-P0.4 expects 1.0)

============================================================
  KILL-GATE VERDICT: STOP   (strict flip at far d: none)
  STOP is a real, honorable outcome (epic §7). Do NOT loosen the strict metric,
  fish with --repeats, or cherry-pick a d to manufacture a PASS.
  (sim: Delta(signal)=0 between arms is BY CONSTRUCTION -- swap/teleport are the
   same logical map. The flip signal lives on HARDWARE, not here.)
============================================================
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/p0_sim_fliptest_statevector_sim_sim.json



(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage5_fliptest.py --no-sim --backend 'ibm_kingston' --width 12 --separations 2,48 --routing both  --shots 8192 --repeats 3 --name p0_hw
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 5 / P0 flip-test: width=12 separations=[2, 48] routing=both on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00178, 'twoq_err_max': 0.00277, 'readout_max': 0.04785, 'sx_max': 0.000944}
  job 1: da7cvc60ukec73835290 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7cversq5js73bjq440 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7cvhjsq5js73bjq46g (8,192 shots) ... done (qpu 4.00s)
  job 1: da7cvn6sidac73af7c9g (8,192 shots) ... done (qpu 4.00s)
  job 1: da7cvs3sq5js73bjq4h0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7cvvesidac73af7ch0 (8,192 shots) ... done (qpu 4.00s)
  d=  2 per-block <X^W> headroom: A=+0.443 B=+0.501
  job 1: da7d07s6l22c73dnebog (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d0e60ukec73835390 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d0jm0ukec738353f0 (8,192 shots) ... done (qpu 4.00s)
  d=  2 swap     : signal=+0.215+-0.019  depth=  28  CLEARS 2sigma
  job 1: da7d0ojsq5js73bjq5c0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d0tc6l22c73dnech0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d12bsq5js73bjq5ng (8,192 shots) ... done (qpu 4.00s)
  d=  2 teleport : signal=+0.058+-0.012  depth=  29  CLEARS 2sigma
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00203, 'twoq_err_max': 0.00741, 'readout_max': 0.04785, 'sx_max': 0.000944}
  job 1: da7d1es6l22c73dned80 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d1hu0ukec738354i0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d1l3sq5js73bjq6e0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d1nusidac73af7edg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d1qusidac73af7em0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d1tmsidac73af7evg (8,192 shots) ... done (qpu 4.00s)
  d= 48 per-block <X^W> headroom: A=+0.447 B=+0.558
  job 1: da7d22jsq5js73bjq7gg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d28k6l22c73dnef30 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d2dusidac73af7g50 (8,192 shots) ... done (qpu 4.00s)
  d= 48 swap     : signal=+0.060+-0.015  depth= 111  CLEARS 2sigma
  job 1: da7d2ijsq5js73bjq8qg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d2nm0ukec738357e0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d2sm0ukec738357u0 (8,192 shots) ... done (qpu 4.00s)
  d= 48 teleport : signal=+0.029+-0.017  depth=  29  buried

============================================================
  KILL-GATE VERDICT: STOP   (strict flip at far d: none)
  STOP is a real, honorable outcome (epic §7). Do NOT loosen the strict metric,
  fish with --repeats, or cherry-pick a d to manufacture a PASS.
============================================================
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/p0_hw_fliptest_ibm_kingston_20260826-134356.json

(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage5_fliptest.py --no-sim --backend ibm_kingston --width 12 --separations 48 --routing teleport --herald --shots 8192 --repeats 3 --name p0_herald
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 5 / P0 flip-test: width=12 separations=[48] routing=teleport on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00203, 'twoq_err_max': 0.00741, 'readout_max': 0.04785, 'sx_max': 0.000944}
  job 1: da7d64msidac73af7omg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d67msidac73af7oug (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d6absq5js73bjqhn0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d6cusidac73af7pcg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d6frsq5js73bjqi5g (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d6iusidac73af7pq0 (8,192 shots) ... done (qpu 4.00s)
  d= 48 per-block <X^W> headroom: A=+0.463 B=+0.548
  job 1: da7d6ok6l22c73dneqmg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d6tm0ukec73835i10 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7d72k6l22c73dner80 (8,192 shots) ... done (qpu 4.00s)
  d= 48 teleport : signal=+0.000+-0.011  depth=  29  buried

============================================================
  KILL-GATE VERDICT: STOP   (strict flip at far d: none)
  STOP is a real, honorable outcome (epic §7). Do NOT loosen the strict metric,
  fish with --repeats, or cherry-pick a d to manufacture a PASS.
============================================================
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/p0_herald_fliptest_ibm_kingston_20260826-135254.json

(base) peter@home:~/PycharmProjects/Quantum-research/artificial-life/code$ python stage5_fliptest.py --no-sim --backend ibm_kingston --width 12 --separations 4,24,48 --routing swap --shots 8192 --repeats 1 --name p0_swapverify 
Q-EaaS  : https://api.qeaas.eu/  health: ok
Backend : ibm_kingston  (156 qubits)
=== Stage 5 / P0 flip-test: width=12 separations=[4, 24, 48] routing=swap on ibm_kingston ===
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00183, 'twoq_err_max': 0.00366, 'readout_max': 0.04028, 'sx_max': 0.000666}
  job 1: da7ddj46l22c73dnf21g (8,192 shots) ... done (qpu 4.00s)
  job 1: da7ddls6l22c73dnf25g (8,192 shots) ... done (qpu 4.00s)
  d=  4 per-block <X^W> headroom: A=+0.546 B=+0.625
  job 1: da7ddrs6l22c73dnf2d0 (8,192 shots) ... done (qpu 4.00s)
  d=  4 swap     : signal=-0.130+-0.011  depth=  30  buried
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00218, 'twoq_err_max': 0.00741, 'readout_max': 0.04028, 'sx_max': 0.001023}
  job 1: da7de8k6l22c73dnf2q0 (8,192 shots) ... done (qpu 4.00s)
  job 1: da7deb6sidac73af8230 (8,192 shots) ... done (qpu 4.00s)
  d= 24 per-block <X^W> headroom: A=+0.641 B=+0.315
  job 1: da7defrsq5js73bjqr50 (8,192 shots) ... done (qpu 4.00s)
  d= 24 swap     : signal=+0.014+-0.011  depth=  63  buried
Auto qubit chain (live calib): {'dead_avoided': [112, 113, 121, 146], 'twoq_err_mean': 0.00203, 'twoq_err_max': 0.00741, 'readout_max': 0.04785, 'sx_max': 0.000944}
  job 1: da7desk6l22c73dnf3dg (8,192 shots) ... done (qpu 4.00s)
  job 1: da7devbsq5js73bjqrm0 (8,192 shots) ... done (qpu 4.00s)
  d= 48 per-block <X^W> headroom: A=+0.442 B=+0.551
  job 1: da7df4esidac73af82r0 (8,192 shots) ... done (qpu 4.00s)
  d= 48 swap     : signal=+0.021+-0.011  depth= 111  buried

============================================================
  KILL-GATE VERDICT: STOP   (strict flip at far d: none)
  STOP is a real, honorable outcome (epic §7). Do NOT loosen the strict metric,
  fish with --repeats, or cherry-pick a d to manufacture a PASS.
============================================================
  -> /home/peter/PycharmProjects/Quantum-research/artificial-life/research_runs/p0_swapverify_fliptest_ibm_kingston_20260826-141005.json


- **§8-A — AC-P0.1 (chain gate)** — in (B), each d's `chain` is a length-`2W+d` SWAP-free chain; `chain_stats` for
  both blocks present; a bad chain aborts exit 1 (`[P0 ABORT] chain-quality gate failed …`). Confirm block A and
  block B qubit ranges are disjoint (they are, by the `[0:W]` / `[W+d:2W+d]` split). `per_block_witness` ~0.30 on
  hardware (the headroom the thesis needs).
- **§8-B — AC-P0.2 (both arms)** — `summary["dsweep"][i]["arms"]` has `swap` and `teleport`, each with
  `witness_joint_mean`, `separable_mean`, `signal_mean`, `signal_sigma`, `logical_depth`; teleport `ancillas == 2`,
  swap `ancillas == 0`; `logical_depth(swap)` grows with `d`, `logical_depth(teleport)` ~flat (the D evidence).
- **§8-C — AC-P0.3 (strict flip + verdict)** — at `d=2` (control): `strict_flip == false` and `control == true`
  (teleport predicted to lose). At far `d=48`: `strict_flip == true` ⟹ `kill_gate.verdict == "PASS"`. If no far d
  flips, `verdict == "STOP"` — print it loudly; the epic headline (D) must be re-scoped before P1 (epic §7). Verify
  strictness: a run where teleport>swap but swap still clears 2σ must **not** be reported as a flip.
- **§8-D — AC-P0.4 (noiseless agreement)** — in (A), `swap` and `teleport` `signal_mean` agree within shot noise
  (Δsignal=0 by construction — state it), and `witness_ideal == 1.0` to 1e-9. If they disagree, the routing
  primitives were copied wrong — fix before touching hardware.
- **Provenance (CD-7)** — `meta.entropy_provenance` carries real `request_id`/`receipt`; unset `QEAAS_API_KEY` →
  abort exit 1 with `QRNGUnavailable`, no PRNG fallback on the hardware path.
- **Schema check** —
  `python -c "import json,glob;d=json.load(open(sorted(glob.glob('../research_runs/p0_hw*'))[-1]));print(d['kill_gate']['verdict'], [x['strict_flip'] for x in d['dsweep']], d['dsweep'][-1]['arms'].keys())"`
  → verdict present, `strict_flip` per d, arm keys `swap`+`teleport`.
- **Herald guard** — (C) prints the expected kept fraction (~0.25) and records `herald_frac`; confirm it does not
  silently proceed on empty post-selection.

---

## 9. Out-of-context risks / notes

- **Δsignal=0 on noiseless sim is expected, not a null.** The most likely misread. Swap and teleport are the same
  logical map; only decoherence separates them. Label the `--sim` agreement "by construction"; source the flip from
  hardware. Do **not** report sim Δsignal=0 as the kill-gate answer.
- **STOP is a real, honorable outcome.** If teleport does not clear 2σ while swap is buried at any far d, the
  kill-gate says STOP — that is the epic working as designed (epic §7). Do **not** loosen the strict metric (Q1),
  widen `--repeats` to fish for significance, or cherry-pick a d to manufacture a PASS.
- **Per-block gate is conservative-but-correct.** `best_chain` returns one aggregate `stats`; P0 gates on the
  whole `2W+d` chain, which upper-bounds each block's max errors ⟹ each block passes when the whole does. If a
  developer wants literally-per-block thresholds, recompute max errors over each block's edge slice from the raw
  pull — noted as optional (Q-P0.2), not required for AC-P0.1.
- **Connected two-point vs full-span witness.** Default witness span is the bonded pair (`--witness-span bond`) to
  keep the cross-block observable out of the fragile many-body regime. `--witness-span full` (2W product) is
  available for comparison but is expected to be noisy on hardware (the M4 W24 lesson) — see Q-P0.1.
- **Teleport ancilla/mid-measure overhead can erase the win at small d.** Expected — that is exactly why `d=1` is
  the negative control. The flip is a *large-d* claim; a teleport loss at `d=1` is a PASS-consistent control, not a
  failure.
- **`best_chain` may raise for long chains.** A SWAP-free length-`2W+d` chain may not exist at far d on the chosen
  backend → `RuntimeError`. `gated_chain` already aborts exit 1 with a clear message; suggest a smaller far `d` in
  the abort text.
- **Dynamic-circuit support on statevector sim.** `_teleport_cx` uses mid-circuit `measure` + `if_test`
  feed-forward. `stage4_qalife`/`stage3_teleport` already run these on `qiskit-aer` statevector; confirm the
  installed version executes `if_test`. No new pip dependency expected (`qiskit`, `qiskit_aer`, `numpy`,
  `pipeline_common`, `qrng_client` all present).
- **`tel` bit order.** The heralded post-select mask reads `tel` **not** reversed (the `c` register is reversed);
  carry the `"<c> <tel>"` key split from `stage4_scale.run_counts` exactly or the herald filter is wrong.
- No new pip dependency; `qrng_client.py` uses stdlib `urllib`.

---

## 10. Ground rules honored

- Every AC (P0.1–P0.4) quoted **verbatim** from epic §9 and mapped to a §8 manual check.
- Every file path in §6 is concrete; **one new file**, no edits outside `artificial-life/code/`.
- Epic cross-cutting decisions (CD-1, CD-4, CD-5, CD-6, CD-7) and resolutions (Q1, Q4) adopted without re-arguing.
- The flip is **measured on hardware, not asserted**; Δsignal=0-on-noiseless-sim disclosed as by-construction; the
  ancilla/latency cost recorded (honesty invariant, CD-4).
- No tests, no test files, no test-impact section (project directive). Verification is manual (§8).
- Strict typing + Python idioms (`from __future__ import annotations`, full hints, `flush=True` print); no raw SQL.

---

## 11. Resolved decisions (developer, 2026-08-26 — all proposed defaults accepted)

- **Q-P0.1 — Cross-block witness span: RE-RESOLVED at implementation (2026-08-26) → `--witness-span full` = the
  CONNECTED-GHZ witness `signal = ⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B`.** The originally-resolved bonded two-point
  ⟨X_{A_tail} X_{B_head}⟩ − ⟨X_{A_tail}⟩⟨X_{B_head}⟩ is **identically zero** for the GHZ genealogy (a GHZ has NO
  low-weight off-diagonal signal — any X-string lighter than the full 2W set maps GHZ out of its support → 0). Both
  the intact and the broken bond read 0, so it can never show the flip. Verified empirically (`witness_ideal(bond)
  = 0.0`; sim signal ≈ 0 on both arms). The genuine, classical-surrogate-free witness is the full 2W parity minus
  the **per-block** product: = 1 for one connected genealogy across the wall, = 0 for two separate healthy blocks,
  → 0 for a measure-and-resend infector (CD-4 holds). This IS a 2W-body parity (re-enters the fragile regime the
  original bond resolution tried to avoid) — but that is exactly the epic's headroom test (2×W12 per-block ~0.30 vs
  the dead single W24 line). Developer-approved 2026-08-26. `--witness-span bond` retained as a degenerate
  diagnostic (records the known-zero two-point for comparison), off by default.
- **Q-P0.2 — Gate granularity: RESOLVED → whole-chain gate.** Gate on the whole `2W+d` chain; conservative ⟹ each
  block passes (max over the union bounds each block). Per-block raw-calibration recompute is optional, not
  required for AC-P0.1. (Additionally, a standalone per-block `<X^W>` headroom sanity is measured on each block's
  real physical qubits and recorded as `per_block_witness`.)
- **Q-P0.3 — Far-separation value: RE-RESOLVED at implementation (2026-08-26) → `--separations 2,48`.** The
  originally-resolved `d=1` control cannot host the teleport arm: `_teleport_cx` (copied verbatim, CD-1) needs a
  **2-qubit corridor** flanking the wall (`a1` next to A_tail, `a2` next to B_head; S3 placement), i.e. wall width
  `d ≥ 2`. At `d=1` the plan's own literal `a1,a2 = q[W],q[W+1]` puts `a2 = B_head`. Developer-approved 2026-08-26:
  control = `d=2` (smallest wall that hosts the corridor; teleport still predicted to LOSE there — overhead >
  ~2·d swap depth — so a valid teleport-predicted-lose negative control). Far `d=48` unchanged (`L=72` fits 156q).
  A `<2` separation with `--routing teleport`/`both` aborts exit 2 with a clear message.
- **Q-P0.4 — Repeats on hardware: RESOLVED → `--repeats 3`** (matches `stage4_scale.py`).

---

## 12. After approval

Once the open questions are answered and the plan approved, run
`/implement-feature artificial-life/plans/virus/feature-P0-fliptest.md`.
P0 gate before P1: a clean `--sim` run proving the pipeline + `logical_depth` split + AC-P0.4 (Δsignal=0 by
construction, `witness_ideal`=1), then the hardware d-sweep with the strict-flip verdict recorded fail-closed
(CD-6/CD-7). **If `kill_gate.verdict == "STOP"`, do not proceed to P1** — the epic headline (D) is refuted and must
be re-scoped (epic §7). Only a `PASS` (strict flip at ≥1 far separation) unlocks `/plan-feature P1`.

---

## 13. Post-implementation notes (2026-08-26)

**Built:** one new file `artificial-life/code/stage5_fliptest.py` (no edits to any existing file). It ports the
routing primitives (`_swap_cx`, `_teleport_cx` from `stage3_teleport.py`), the witness helpers
(`xbasis_witness_from_counts`, `_x_string_op`, `apply_self_replication`, `_sim_thetas` from `stage4_qalife.py`),
and the run/JSON/CLI skeleton (`qrng_thetas`, `gated_chain`, `run_counts`, `_read_env_key` from `stage4_scale.py`)
— all with `# ported from …` provenance (CD-1). Adds the two-block flip circuit, the connected-GHZ cross-block
witness, the strict-flip kill-gate, the noiseless `witness_ideal` check, standalone per-block headroom, certified
fail-closed QRNG with provenance receipts, and the `--separations/--routing/--witness-span/--sv-max-qubits/--herald`
CLI.

**Two developer-approved deviations from the approved plan (both surfaced, not silent):**

1. **Witness redesign (Q-P0.1).** The plan's resolved headline — the bonded two-point ⟨X_{A_tail} X_{B_head}⟩ — is
   **identically zero for a GHZ genealogy** (proved empirically: `witness_ideal(bond)=0`, sim signal≈0 both arms). A
   GHZ has no low-weight off-diagonal witness. Replaced with the connected-GHZ witness `⟨X^⊗2W⟩ −
   ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B` (=1 connected / 0 separate / →0 for a classical infector; CD-4 intact). `--witness-span full`
   is now the default headline; `bond` retained as a degenerate diagnostic. **Consequence for the epic:** the working
   witness is a 2W-body parity — the fragile many-body regime. P0's job is exactly to test on hardware whether
   teleport preserves it where swap doesn't, resting on the per-block-headroom thesis (2×W12 ~0.30). If the hardware
   d-sweep returns STOP, the honest read is that GHZ-genealogy cross-block coherence has no light witness and the
   epic's D headline (and possibly the genealogy state structure) needs a rethink before P1.

2. **Control separation `d=1`→`d=2` (Q-P0.3).** The verbatim-copied `_teleport_cx` needs a 2-qubit corridor
   flanking the wall (S3 placement `a1=A_tail+1`, `a2=B_head−1`), i.e. `d≥2`. `d=1` cannot host it. Default
   `--separations` is now `2,48`; `d=2` is the teleport-predicted-lose control. `d<2` with a teleport arm aborts
   exit 2.

**Verified (sim-first, §8):** `python stage5_fliptest.py --sim --width 3 --separations 2,4 --routing both` →
per-block `<X^W>` A=B=1.000, swap≈teleport signal=+1.000 (Δ=0 by construction), `witness_ideal=1.000000000`,
`logical_depth` split (swap 10→14 with d, teleport flat 12), 12 QRNG receipts in `entropy_provenance`, verdict STOP
(correct on noiseless sim — the flip is a hardware decoherence effect). Guards verified: teleport `d=1` aborts;
swap-only `d=1` runs; `--herald` records `herald_frac≈0.25`; `bond` diagnostic reads ~0. JSON schema matches §4.

**Not run (developer's kill-gate):** the real hardware d-sweep (§8-B) on `ibm_kingston` and the herald hardware
cross-check (§8-C) — need live backend + `QEAAS_API_KEY`. Those produce the actual PASS/STOP verdict that gates P1.

**Follow-ups for the developer:**
- Run the hardware d-sweep; if STOP, see deviation 1 above before re-scoping (epic §7).
- `run_counts` hardware path assumes `run_sampler` returns per-shot classical strings with `c` leftmost when a
  `tel` register is present (the herald split relies on this, matching `stage4_scale`'s convention). Confirm against
  the live `pipeline_common.run_sampler` before trusting `herald_frac` on hardware.
- No new pip dependency; `--selftest` is a P1 concern (not in P0 scope).
