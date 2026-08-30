# Feature Plan — P1: Build the virus (swap-routed) (`stage5_virus.py`)

**Status:** Draft
**Epic:** `artificial-life/plans/virus/epic-stonewall-virus.md` (Status: **Approved — pivoted swap-routed 2026-08-26**)
**Phase ID:** P1 (second of 4; depends on **P0 = Complete**; pivoted to swap-routed by the P0 kill-gate result)
**Artifact:** `artificial-life/code/stage5_virus.py`
**Source spec:** epic §9 P1 brief + §3 (CD-1..CD-6) + §4 (genome/qubit budget) + §5 (observable B) + §8 (Q2, Q6)
**Borrows from (copy, don't import — CD-1):**
- `artificial-life/code/stage5_fliptest.py` (P0) — `_swap_cx`, `_teleport_cx`, `x_parity`,
  `xbasis_witness_from_counts`, `_x_string_op`, the connected-GHZ witness (`⟨X^⊗2W⟩ − ⟨X^⊗W⟩_A·⟨X^⊗W⟩_B`),
  `gated_chain`, `run_counts`, `qrng_thetas`, `_read_env_key`, the run/JSON/CLI skeleton
- `artificial-life/code/stage4_qalife.py` — `apply_self_replication` (clone `cx`), `apply_mutation` (`ry`),
  `apply_phenotype_clone`, `apply_aging_damping`/unitary aging, `alive_population`, `deepest_surviving_lineage`,
  `selftest()` discipline
- `artificial-life/code/layout.py` — `best_chain` (live-calibration SWAP-free chain + gate stats)
- `artificial-life/code/qrng_client.py` — `QRNGClient`, `QRNGUnavailable` (certified fail-closed; unchanged)

**Author:** Claude (Opus) · **Date:** 2026-08-26

> No GitHub issue — phase IDs, not tickets (per [[qrng-eaas-plan-workflow]]).
> No tests (project directive): production code + `--selftest` (closed-form operator checks) + manual verification.
> **Pivot note:** P0 refuted the teleport-flip on `ibm_kingston` (3 runs, verdict STOP: teleport loses to swap at
> every separation because mid-circuit-measurement cost ≫ 2q cost on readout-dominated Heron-r2). P1 is therefore
> **swap-routed**; teleport is retained only as an optional, clearly-labelled negative baseline arm (CD-5 pivoted).

---

## 1. Context & goal

P0 stripped the virus to a single cross-block transmission bond and proved two things on metal: (1) the teleport
routing arm loses — the epic's original D headline is dead; (2) the **connected-GHZ cross-block transmission
witness works swap-routed** (signal 0.215 @ d=2, 0.060 @ d=48, per-block headroom ~0.45). P1 builds the full virus
on top of that surviving result: a real 3-locus genome, static Darwinian selection, three disjoint W12 stone-wall
blocks, and a **swap-routed** chain infection A→B→C — the vehicle whose cross-block genome coherence P2 will measure
vs distance (the pivoted headline B).

P1 is a **build + self-test** phase: it produces the runnable model and proves every operator against closed-form
values (`--selftest`, M4 discipline). The multi-generation run, the distance-decay sweep, and the 2D environment
grid are **P2** (`stage5_run.py`).

### What already exists (integration anchors — concrete)
- `stage5_fliptest.py` (P0) supplies the swap primitive (`_swap_cx`), the connected-GHZ witness machinery
  (`x_parity`, `xbasis_witness_from_counts`, `_x_string_op`), the fail-closed chain gate (`gated_chain` returning
  `(qubit_list, qstats)`), the sim/hardware dispatch with heralded-teleport handling (`run_counts`), certified QRNG
  with provenance (`qrng_thetas`), and the results-dict/`--verify` conventions. Copy verbatim (CD-1).
- `stage4_qalife.py` supplies the Darwinian operators (clone `cx`, mutation `ry`, phenotype clone, aging), the
  alive-count/deepest-lineage classical readouts, and the `selftest()` structure.

---

## 2. Acceptance criteria

Verbatim from epic §9 (P1 brief, pivoted). Each maps to a §8 manual check.

- **AC-P1.1** (verbatim): "Genome `[q_witness, b1, b2]` implemented; witness locus entangled, classical loci in Z (CD-2)."
- **AC-P1.2** (verbatim): "Static fitness `f(b1,b2)` (Q2) computed into 1 ancilla, measured, replication feed-forwarded (CD-3)."
- **AC-P1.3** (verbatim): "Three W12 blocks laid out on 144 qubits, per-block chain-quality gate (CD-6)."
- **AC-P1.4** (verbatim): "Chain infection A→B→C wired **swap-routed** (`_swap_cx`); a teleport arm retained as an
  optional, clearly-labelled negative baseline only (CD-5, pivoted)."
- **AC-P1.5** (verbatim): "Connected-GHZ cross-block transmission witness reused verbatim from P0 (`⟨X^⊗2W⟩ −
  per-block product`); the bonded two-point is not used (identically 0 for GHZ — P0 finding)."
- **AC-P1.6** (verbatim): "`--selftest` verifies every operator against closed-form values (mirror the M4 selftest discipline)."

**AC coverage (each mapped to a §8 manual check):** *(filled with file:line evidence at implementation — see §12).*

| AC | Covered by | §8 check |
|---|---|---|
| AC-P1.1 | `genome_layout` (4 qubits/individual: `q_witness`, `b1`, `b2`, `pheno`); `q_witness` seeded on the equator + clone-chained (entangled), `b1/b2` prepared in Z (`x` per genome bit, no superposition). | §8-A: `--selftest` asserts `q_witness` GHZ (`⟨X^⊗⟩=1` ideal) and `b1/b2` diagonal (`⟨Z⟩=±1`, `⟨X⟩=0`). |
| AC-P1.2 | `apply_selection(qc, b1, b2, anc, creg)` — compute `f=(b1==b2)` into `anc` (CCX/CX pattern), mid-measure `anc`, `if_test`-gate the replication (CD-3, Q2). | §8-B: `--selftest` checks the truth table (b1=b2 → replicate; b1≠b2 → not) on all 4 genomes. |
| AC-P1.3 | `three_block_layout` splits one gated chain into A/B/C W12 slices with stone-wall spacers; `gated_chain` per block region (CD-6, fail-closed). | §8-C: hardware run aborts on a bad block chain; run.json records per-block `chain_stats`. |
| AC-P1.4 | `apply_infection(qc, src_witness, dst_witness, routing)` — `swap` → `_swap_cx` (headline); `teleport` → `_teleport_cx` (baseline, off by default, labelled). | §8-D: `--routing swap` (default) chain-infects A→B→C via `_swap_cx`; `--routing teleport` runs the labelled baseline. |
| AC-P1.5 | connected-GHZ witness copied from P0 over the `q_witness` loci across blocks; `--witness-span bond` guarded/deprecated (identically 0). | §8-E: `--selftest` ideal cross-block witness = 1.0; bonded two-point = 0.0 (documented). |
| AC-P1.6 | `selftest()` — each operator vs closed form; exit non-zero on any mismatch. | §8-F: `python stage5_virus.py --selftest` → all PASS, exit 0. |

---

## 3. Scope

### In scope
- New file `artificial-life/code/stage5_virus.py`. Copies P0's swap primitive + witness + skeleton and
  `stage4_qalife.py`'s Darwinian operators (CD-1, with `# ported from …` provenance). **No edits to existing files.**
- **3-locus genome + phenotype (CD-2).** Individual = 4 qubits `[q_witness, b1, b2, pheno]`. `q_witness` = the one
  entangled locus (equatorial founder + clone chain = the genealogy GHZ, the transmission witness). `b1,b2` =
  classical Z-basis fitness bits (prepared with `x`, never put in superposition — genome-internal entanglement OFF).
  `pheno` = lifetime qubit for the alive-count narrative.
- **Static 1-ancilla Darwinian selection (CD-3, Q2).** `f(b1,b2) = survive iff b1==b2` computed into one shared
  fitness ancilla, mid-circuit measured, feed-forward gating replication. Reused via `reset` across individuals.
  Static (not coevolving). Measure only the ancilla, not all loci (budget: G=3 + 1-ancilla ≈ 9 gens vs 6).
- **Three disjoint W12 stone-wall blocks (§4).** 144 data qubits (+ selection/corridor ancillas, reused) on 156q
  `ibm_kingston`, three contiguous chains separated by stone-wall spacers, gated per block (CD-6).
- **Swap-routed chain infection A→B→C (CD-5, pivoted).** Cross-block bond = `_swap_cx` on the `q_witness` loci
  (A_tail→B_head, B_tail→C_head). Optional `--routing teleport` negative-baseline arm (off by default, labelled).
- **Connected-GHZ cross-block transmission witness (B, from P0).** `⟨X^⊗⟩ − per-block product` over the
  `q_witness` loci spanning blocks. `=1` connected, `→0` classical infector (CD-4). Bonded two-point NOT used.
- **`--selftest` (CD-1 / AC-P1.6).** Every operator (genome prep, clone, mutation, selection truth table, infection,
  witness ideal) checked against closed-form values; exit non-zero on mismatch.
- **Certified fail-closed QRNG (CD-7).** `qrng_thetas` for mutation angles, receipts logged, fail-closed on HW.
- CLI mirrors P0 + adds `--blocks` (default 3), `--generations` (default 1 — P1 is one generation of the built
  model; the ~9-gen run is P2), `--routing {swap,teleport}` (default swap), `--selftest`.

### Out of scope (deferred)
- The multi-generation (~9-gen) run, the transmission-witness-vs-distance decay sweep, the 2D environment grid —
  **P2** (`stage5_run.py`).
- Web demo, `CONCLUSION_MONTH5.md`, aggregation — **P3**.
- Coevolving/dynamic fitness (static only, CD-3). Genome-internal entanglement (option E, OFF, CD-2).
- The teleport headline (refuted, P0) — teleport is a labelled baseline only.
- Re-deriving the witness math / swap primitive / QRNG client / chain gate — frozen upstream, copied verbatim (CD-1).

---

## 4. Data model — `run.json` (P1 fields)

Written to `OUTPUT_DIR = ../research_runs`, `json.dump(..., indent=2, default=str)`; filename
`f"{args.name}_virus_{backend_name}_{tag}.json"`.

```jsonc
{
  "meta": {
    "stage": 5, "phase": "P1", "model": "stonewall_virus",
    "backend": "sim|<hw>", "sim": true|false,
    "width": 12, "blocks": 3, "generations": 1,
    "genome": ["q_witness", "b1", "b2"], "phenotype": true,
    "routing": "swap",                         // headline; "teleport" = labelled baseline
    "fitness": "survive_iff_b1_eq_b2",         // Q2
    "shots": 8192, "repeats": 3, "k": 2.0,
    "max_twoq_err": 0.05, "max_readout_err": 0.15,
    "mut_scale": 0.10, "qrng_url": "...",
    "entropy_provenance": [ { "request_id": "...", "receipt": "..." } ],
    "selftest": "pass|null"
  },
  "blocks": [
    { "id": "A", "chain": [ ... ], "chain_stats": {"twoq_err_max": <f>, "readout_max": <f>},
      "per_block_witness": <f> } , ...
  ],
  "cross_block_witness": {
    "A_B": { "witness_joint_mean": <f>, "separable_mean": <f>, "signal_mean": <f>,
             "signal_sigma": <f>, "clears_2sigma": <bool> },
    "B_C": { ... }
  },
  "population": {                              // classical narrative (CD-4), not the headline
    "alive_mean": <f>, "deepest_lineage_mean": <f>
  }
}
```

---

## 5. Design decisions carried from the epic (do not re-litigate)
- **CD-1** Copy, don't import — copy P0's swap+witness+skeleton and S4's operators with `# ported from …` comments.
- **CD-2** Genome = `[q_witness, b1, b2]` + phenotype; only `q_witness` entangled; `b1,b2` classical Z; option E OFF.
- **CD-3** Selection = 1 fitness ancilla, static, `survive iff b1==b2`, mid-measure + feed-forward, ancilla reused.
- **CD-4** One claim — connected-GHZ cross-block transmission witness (B). Population = narrative only.
- **CD-5 (pivoted)** Infection = **swap-routed** (`_swap_cx`); teleport = optional negative baseline only.
- **CD-6** Per-block chain-quality gate, fail-closed.
- **CD-7** Certified QRNG mutation angles, receipts logged, fail-closed on hardware.
- **Q2** Fitness `f(b1,b2) = survive iff b1==b2` (50% pressure). **Q6** Pivot to swap-routed (P0 result).

---

## 6. File plan (concrete paths)

`from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`. One new file.

### `artificial-life/code/stage5_virus.py` (new)
1. **Module docstring** — what P1 builds (swap-routed 3-block virus, 3-locus genome, static selection), the pivot
   note (teleport refuted in P0), the honesty note (only the connected-GHZ witness is the quantum claim), provenance.
2. **Imports + dual-path setup** — copy P0's header (`SIM = AerSimulator(method="statevector")` for unitary arms;
   `density_matrix` only if a damping phenotype arm is added — default unitary), `pipeline_common` probe, QRNG.
3. **Ported primitives (CD-1):** `_swap_cx`, `_teleport_cx`, `x_parity`, `xbasis_witness_from_counts`, `_x_string_op`
   from P0; `apply_self_replication`, `apply_mutation`, `apply_phenotype_clone`, aging, `alive_population`,
   `deepest_surviving_lineage` from `stage4_qalife.py`.
4. **`genome_layout(width, blocks)`** — index helpers: for individual `i` in block `b`, return
   `(q_witness, b1, b2, pheno)` physical indices along the gated chain, with stone-wall spacers between blocks.
5. **`apply_selection(qc, b1, b2, anc, cbit)`** — `f=(b1==b2)` into `anc` (e.g. `cx(b1,anc); cx(b2,anc); x(anc)` →
   `anc=1 iff b1==b2`), `measure(anc, cbit)`, `with qc.if_test((cbit,1)): <replicate>`, then `reset(anc)`. New op.
6. **`build_genome(qc, individual, theta, genome_bits)`** — `ry(pi/2, q_witness)` founder (or clone from parent),
   `apply_mutation(q_witness, theta)`; `x` on `b1`/`b2` per `genome_bits` (classical prep). `apply_phenotype_clone`.
7. **`apply_infection(qc, src_witness, dst_witness, routing, tel=None)`** — `swap` → `_swap_cx`; `teleport` →
   `_teleport_cx` (+ corridor, labelled baseline).
8. **`build_virus(width, blocks, generations, routing, thetas, genome_bits) -> QuantumCircuit`** — per block: build
   the W12 genealogy over `q_witness` (founder + clone chain), classical genome bits, phenotype, selection-gated
   replication; then swap-routed chain infection A→B→C on the `q_witness` loci; X-basis witness readout on
   `q_witness` loci, Z readout on phenotypes.
9. **`witness_ideal_virus(width, blocks, span)`** — noiseless connected-GHZ witness over `q_witness` loci (reuse P0
   `witness_ideal_crossblock` pattern) = 1.0 ideal.
10. **`selftest() -> bool`** — genome prep (`q_witness` GHZ; `b1/b2` diagonal), clone (`⟨Z⟩` copy), mutation angle,
    selection truth table (all 4 genomes), infection (swap ≡ teleport logical map on noiseless sim), witness ideal.
11. **`run_virus(...)` + `main()`** — copy P0's `run_arm`/`main` shape; argparse mirrors P0 + `--blocks`,
    `--generations`, `--routing {swap,teleport}`, `--selftest`. Write §4 JSON. Add `--verify` (reuse P0's pattern).
12. **`if __name__ == "__main__": main()`**.

---

## 7. The physics/maths P1 fixes (load-bearing)
- **Only `q_witness` is quantum.** The cross-block witness lives on the `q_witness` genealogy GHZ; `b1,b2` are
  classical Z bits (selection richness without witness cost, CD-2). The connected-GHZ witness form from P0
  (`⟨X^⊗⟩ − per-block product`) is mandatory — the bonded two-point is identically 0 for a GHZ (P0 finding).
- **Selection is genuinely non-trivial (not plumbing).** Mid-circuit measuring the fitness ancilla + feed-forward
  is a real dynamic-circuit operation; but it acts on the *classical* `b1,b2` (diagonal), so it does not carry the
  quantum claim (CD-4). Budget: measuring 1 ancilla (not all loci) preserves ~9-gen depth for P2.
- **Swap-routed infection is the headline path (pivoted).** P0 proved `_swap_cx` carries the witness on Heron-r2
  where `_teleport_cx` does not (readout ≫ 2q). Chain A→B→C = two swap-routed bonds on the `q_witness` loci.
- **Δ(routing)=0 on noiseless sim.** swap and teleport are the same logical map → identical ideal witness
  (selftest checks this); the routing difference is a hardware decoherence effect (teleport loses on metal, P0).

---

## 8. Manual verification (no automated tests; `--selftest` + manual)
```bash
cd artificial-life/code
# A–F) operator self-tests (closed form) — MUST pass before any hardware run
python stage5_virus.py --selftest
# sim smoke: swap-routed 3-block single-generation witness + population
python stage5_virus.py --sim --width 3 --blocks 3 --routing swap --shots 8192 --repeats 3 --name p1_sim
# hardware build check: swap-routed 3-block on ibm_kingston
python stage5_virus.py --no-sim --backend ibm_kingston --width 12 --blocks 3 --routing swap \
    --shots 8192 --repeats 3 --name p1_hw
```
- **§8-A..F** — `--selftest` prints each operator PASS/FAIL and exits 0 only if all pass (AC-P1.1/1.2/1.5/1.6).
- **§8-C** — hardware run aborts fail-closed on a bad block chain; run.json records per-block `chain_stats` (AC-P1.3).
- **§8-D** — default `--routing swap` chain-infects A→B→C via `_swap_cx`; `--routing teleport` runs the labelled
  baseline (AC-P1.4).
- **Cross-block witness** — sim: `cross_block_witness.A_B/B_C signal ≈ 1` (connected GHZ); HW: positive, clears 2σ.
- **Provenance (CD-7)** — `meta.entropy_provenance` carries real receipts; unset `QEAAS_API_KEY` → abort on HW.

---

## 9. Out-of-context risks / notes
- **Selection depth cost.** Mid-measure + feed-forward per individual adds depth; keep the ancilla reused via
  `reset`, measure only the fitness ancilla (CD-3). Watch the death wall (T_eff≈24) — that's P2's budget concern.
- **`q_witness` GHZ fragility at 3×W12.** The connected witness is a high-weight parity (P0 lesson); swap-routed it
  survived at 2×W12/d48. Three blocks add a second bond — expect further decay (that decay curve is P2's headline).
- **Teleport baseline is off by default.** Do not let it creep back as a headline — P0 refuted it (CD-5 pivoted).
- **No new pip dependency;** dynamic-circuit `if_test` runs on `qiskit-aer` statevector (as in P0/S3).

---

## 10. Ground rules honored
- Every AC quoted verbatim from epic §9 (pivoted) and mapped to a §8 check.
- One new file; no edits outside `artificial-life/code/`. Epic CDs + Q2/Q6 adopted without re-arguing.
- The quantum claim is the connected-GHZ witness only; population = narrative (CD-4). Swap-routed headline (pivoted).
- No tests; `--selftest` + manual verification. Strict typing + Python idioms; no raw SQL.

---

## 11. Resolved decisions (developer, 2026-08-26 — all proposed defaults accepted)
- [x] **Q-P1.1 — Phenotype death channel: RESOLVED → unitary aging** (statevector, cheap). P1 is a build phase; the
  damping bath (`density_matrix`) belongs to P2's environment γ-sweep.
- [x] **Q-P1.2 — Cross-block witness span for 3 blocks: RESOLVED → per-bond (A|B, B|C) pairwise.** Feeds the P2
  distance-decay curve cleanly; full A|B|C 3-block parity is noisier and off by default.
- [x] **Q-P1.3 — Founder per block: RESOLVED → seed block A only; B/C founders arrive via infection.** So the
  cross-block witness measures genuine transmission (matching P0).

---

## 12. After approval
Once §11 is resolved and the plan approved, run `/implement-feature artificial-life/plans/virus/feature-P1-virus.md`.
Gate before P2: a clean `--selftest` (all operators PASS) + a sim smoke run showing swap-routed cross-block witness
≈ 1, then the hardware build check with per-block gates fail-closed (CD-6/CD-7).

---

## 13. Post-implementation notes
*(filled at implementation.)*
