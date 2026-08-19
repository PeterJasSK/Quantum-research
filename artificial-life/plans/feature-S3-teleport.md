# Feature Plan — S3: Break the SWAP ceiling (`stage3_teleport.py`)

**Status:** Complete
**Epic:** `artificial-life/plans/epic-qdep-coherence-depth-genealogy.md` (Status: **Approved**)
**Stage ID:** S3 (fourth of 5; depends on **S2**, gates S4)
**Artifact:** `artificial-life/code/stage3_teleport.py`
**Source specs:** `qdep-1-coherence-depth-genealogy.md` (Stage 3 "Break the SWAP ceiling", Bull/Bear/Value-if-null), `QDEP_Living_Genealogies.md` (§6.3 interaction, §6.4 teleported gates — honest version, §11 teleportation overhead)
**Borrows from:**
- `artificial-life/code/stage2_scale.py` (verbatim: `temporal_correlation`, `_mutation_schedule`, `apply_clone`, `phenotype_map`, `build_lineage_quantum`, `run_classical_surrogate`, `sample_quantum_arm`, `run_ideal_correlation`, `run_once`, `compute_gstar`, `_aggregate_per_generation`, `_read_env_key`, the G-sweep `main`, run/summary writers, the `--sv-max-qubits` guard, CLI)
- `artificial-life/code/stage0_reproduce.py` (frozen operators/constants `ETA`, `PHI`, `PHENO_BASIS`, `m_gate`, `apply_clone`)
- `QuantumLife/code/research_qtree_teleport.py` (`_teleport_cx` @201, `resolve_bonds` @166, `bond_correlations` @327, the teleport `run_hw` @415 that reads both `c` and `tel` registers, `--bond-dist`/`--anchors`/`--herald` argparse @559)
- `QuantumLife/code/research_qtree_swaplr.py` (`_swap_cx` @173, the O(distance) SWAP-ladder baseline, `~SWAPs/gen` depth print @491)
- `artificial-life/code/qrng_client.py` (certified Q-EaaS, unchanged)

**Reuses (do not re-derive):** the frozen S0 physics and the S1/S2 temporal machinery — `temporal_correlation` anchored at T₀, the one-dynamic-lineage circuit with mid-circuit trait readout, the measure-and-resend surrogate, the certified fail-closed Q-EaaS schedule, `compute_gstar` on the g≥1 domain, the ideal-clone confound curve (M4), and the G-sweep aggregation — **copied verbatim** into `stage3_teleport.py` with provenance comments (CD-1 parity). S3 changes exactly one thing: **how the inheritance (clone) bond's CX is routed on the chip** — SWAP ladder vs teleported constant-depth CNOT.

**Author:** Claude (Opus) · **Date:** 2026-08-19

> No GitHub issue — this study uses stage IDs, not tickets (project convention).
> No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

S2 banked (or is banking) **g\*** with error bars and the ideal-clone confound curve. S3 asks the follow-on
question the epic reserved for last: **does teleport-routing the inheritance bond buy coherent generations that
SWAP-routing cannot, on the same chip?**

The mechanism (qdep-1 Stage 3, QDEP §6.4): a long-range entangling gate routed by a **SWAP ladder** costs depth
that *grows with the routed distance* — and that depth is spent out of exactly the coherence budget `g*` measures.
Replace the SWAP ladder with a **teleported CNOT** (one Bell pair + two mid-circuit measures + classical
feed-forward) and the gate lands at **constant depth**, at the honest cost of ancilla qubits and feed-forward
latency (QDEP §6.4, AC-S3.3). If teleport-routing keeps the lineage coherent across deeper generational circuits,
the coherent-generation budget rises: the headline is **Δg\*** = `g*(teleport) − g*(swap)` at matched settings (M5),
evidenced by `logical_depth` per routing (M6) — teleport ≈ constant, swap ∝ routed distance.

S3 is the **temporal re-aim of QuantumLife's teleport-vs-SWAP fork** (`research_qtree_teleport.py` /
`research_qtree_swaplr.py`): there the long-range bond joined two *spatially distant qubits within one generation*;
here it routes the *inheritance bond between consecutive generations* of one lineage. Same two trusted primitives
(`_teleport_cx`, `_swap_cx`), orthogonal axis.

**The one honest asymmetry S3 must state up front (see §7, §9).** Δg\* is a **decoherence effect**. On a *noiseless*
statevector, a SWAP ladder and a teleported CNOT are logically identical maps, so they produce **identical** `C(g)`
and **Δg\* = 0 by construction**. The noiseless `--sim` run therefore validates the *pipeline* and the *logical_depth*
claim (M6) only; the Δg\* *signal* (M5) requires either real Heron-r2 hardware or a noisy simulator
(`--noise-model`, §6/§11 Q7). This mirrors S2's "ideal ≡ quantum under `--sim`" caveat and must be carried into S4.

### What already exists (integration points — concrete anchors)

- `artificial-life/code/stage2_scale.py` — the S3 base, copied verbatim (CD-1):
  - `build_lineage_quantum(theta_seq, n_slots, pheno_coupling) -> QuantumCircuit` @269 — the one dynamic lineage
    circuit. Per gen g: `apply_clone(parent=g-1, ancilla=g)` (= `Ry(PHI, child)` + **`CX(g-1 -> g)`** @135–141),
    `m_gate(theta_g)`, `phenotype_map` (Q1 coupling), mid-circuit `measure` into `c[g]`. **S3 routes the clone's
    `CX(g-1 -> g)` @141** and nothing else.
  - `sample_quantum_arm(qc, shots, args, backend, qubit_list, force_sim) -> list[str]` @297 — `--sim` statevector
    vs hardware dispatch; reads only the `c` register (@322 `[s[::-1] for s in raw_meas]`). S3 extends the hardware
    path to also read the `tel` register when `routing="teleport"` + `--herald`.
  - `run_classical_surrogate` @329, `run_ideal_correlation` @401, `temporal_correlation` @180, `_mutation_schedule`
    @219, `compute_gstar` @514, `_aggregate_per_generation` @534, `run_once` @432, `main` G-sweep @588,
    `--sv-max-qubits` guard @634 — all reused; S3 threads `routing`, `bond_dist`, `anchors`, `herald`.
- `QuantumLife/code/research_qtree_teleport.py`:
  - `_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True)` @201 — constant-depth long-range
    `CNOT(ctrl->tgt)` via one Bell pair + two mid-circuit measures + feed-forward `if_test` on `tel[2k]`,`tel[2k+1]`
    (verbatim body @215–227). `feedforward=False` = heralded (post-select `tel==00`). **No literal "depth 9" exists
    anywhere in the file** — it documents only "constant depth" (see §9 honesty note).
  - `resolve_bonds(anchors, dist, n_slots)` @166; `bond_correlations(fields, n, bonds, sb)` @327 (direct connected
    correlation of the two bonded qubits); teleport `run_hw(..., want_tel)` @415 reading `c` **and** `tel`
    (`res[0].data.tel.get_bitstrings()`, tel **not** reversed, @436–437); `--bond-dist`/`--anchors`/`--herald` @559.
  - Ancilla count `n_anc = 2*len(bonds)` and `logical_depth = qc.depth()` recorded in `run_once` @462.
- `QuantumLife/code/research_qtree_swaplr.py`:
  - `_swap_cx(qc, lo, hi)` @173 — SWAP ladder `CNOT(lo->hi)`, `lo<hi`, ~`2*(hi-lo)` SWAPs, O(distance) depth
    (verbatim body @179–183); `~SWAPs/gen = sum(2*abs(sj-si)*slot_bits)` print @491.
- `artificial-life/code/qrng_client.py` — `QRNGClient(base_url, api_key)`, `fetch(*, size=32, fmt="hex")`,
  `QRNGUnavailable`. Reused verbatim.
- `QuantumLife/code/layout.py` — `best_chain(backend, n)` @52 (SWAP-free length-n low-error chain; **raises**
  `RuntimeError` if none exists), `_pull` @25. S3's strided/ancilla layout needs a **longer** chain than S2 (§7);
  the teleport arm leaves `initial_layout` unpinned so opt-3 routes the ancillas (mirrors teleport `run_hw`).

---

## 2. Acceptance criteria

Verbatim from epic §13 (which quotes `qdep-1` Stage 3 and QDEP §6.4). IDs added; each maps to a §8 manual check.

- **AC-S3.1** (verbatim, `qdep-1`): "Interacting distant individuals via a SWAP ladder costs depth that *grows
  with chain distance* — and that depth eats exactly the coherence budget g\* depends on... Swap in the teleported
  long-range bond... a faithful long-range CNOT at **constant depth 9**, crosstalk-immune: distance no longer taxes
  depth, so lineages can go deeper / wider than SWAP permits *on the same chip*."
- **AC-S3.2** (verbatim, `qdep-1`): "Attempted only after g\* is banked at small scale — Stage 3's claim is
  measured as **Δg\*** = extra coherent generations bought by teleport routing over the matched SWAP-routed lineage."
- **AC-S3.3** (verbatim, QDEP §6.4 honesty): "the correct claim is *'constant-depth long-range interaction at the
  cost of ancillas and classical latency,'* **not** 'instant, free bypass of the bottleneck.'"

**AC coverage (each mapped to a §8 manual check):**

| AC | Covered by | §8 check |
|---|---|---|
| AC-S3.1 | `_swap_cx` @ (ported) routes the clone CX with O(bond_dist) SWAPs; `_teleport_cx` routes it at constant depth. `meta.logical_depth = qc.depth()` recorded per routing per G. | §8-A: for a fixed G, `logical_depth(swap)` grows ∝ `bond_dist` while `logical_depth(teleport)` stays ~flat; swap grows with G, teleport ~constant. |
| AC-S3.2 | Two matched quantum arms (`quantum_swap`, `quantum_teleport`) at each G, identical seed/schedule/shots/pheno-coupling; `compute_gstar` per routing vs the shared classical surrogate; `delta_gstar = gstar_teleport − gstar_swap`. Requires S2's g\* first (gate). | §8-B: `summary.sweep[i].delta_gstar` present and integer at each G; hardware/noisy run shows `gstar_teleport ≥ gstar_swap` (Δg\* ≥ 0) or a stated null. |
| AC-S3.3 | `meta.ancillas = 2*num_routed_bonds`, `meta.feedforward_latency = "classical, per teleport bond"` recorded; feed-forward is the default (not heralded); the honesty caveat is written into run.json `meta.routing_cost` and the §8 output. | §8-C: run.json for the teleport arm carries non-zero `ancillas` + the `routing_cost` note; the printed summary states the ancilla/latency cost, never "free bypass". |

---

## 3. Scope

### In scope
- New file `artificial-life/code/stage3_teleport.py` (copies S2 wholesale, then adds routing). No edits to S0/S1/S2.
- **Routed inheritance bond.** The clone `CX(g-1 -> g)` inside `apply_clone` is emitted via `--routing`:
  `swap` (`_swap_cx`, O(distance) baseline), `teleport` (`_teleport_cx`, constant depth + 2 ancillas/bond),
  or `both` (default — run both matched arms so Δg\* falls out).
- **`--bond-dist` = physical routing span** of each routed inheritance bond, and **`--anchors` = which generation
  bonds are routed** long-range (default `all`; a subset for cheaper runs). Q5 resolution, §11.
- **Δg\* (M5).** `gstar_teleport − gstar_swap` at each G, each vs the shared classical surrogate; error bars over
  `--repeats`. Top-level + per-G `delta_gstar` in summary.json (epic §4 field).
- **`logical_depth` (M6).** `qc.depth()` per routing per G in run.json (epic §4 field); teleport ~constant, swap ∝ span.
- **Honest cost accounting (AC-S3.3).** `ancillas`, feed-forward latency, and the "not a free bypass" caveat
  recorded in run.json and printed.
- **Carried forward from S2 unchanged:** the classical surrogate + ideal-clone confound curve (M4) at each G, the
  tunable `--pheno-coupling` (Q1), the certified fail-closed Q-EaaS schedule (M7, CD-7), the G-sweep + g\* error
  bars, the `--sv-max-qubits` guard.
- **Optional heralded teleport** (`--herald`): drop feed-forward, post-select `tel==00` (valid noise filter) —
  small-scale cross-check only (kept fraction ~`0.25**num_bonds`, §7/§9).
- **`--noise-model`** (proposed, §11 Q7): run the sim on a noisy Aer backend so a Δg\* signal appears without QPU.
- CLI extends S2: adds `--routing --bond-dist --anchors --herald --noise-model` (S2's flags unchanged).

### Out of scope (deferred / whole-epic scope)
- THE figure, the IEEE paper, the cross-stage honesty-invariant aggregation — **S4** (S3 emits Δg\*/`logical_depth`
  numbers S4 plots).
- ~102-qubit scale-out, death, interaction between *co-existing distinct individuals*, population dynamics,
  selection as an active operator — whole-epic scope (CD-8; absent, not stubbed). S3's "long-range" object is the
  inheritance bond between consecutive generations of **one** lineage, not two co-existing individuals.
- Re-deriving operators / correlation math / surrogate / g\* rule / confound curve — frozen in S0/S1/S2, copied
  verbatim (CD-1).
- A literal "depth 9" assertion — S3 **measures** `qc.depth()` and reports the observed constant, not the
  narrative's "9" (§9 honesty note).

---

## 4. Data model — `run.json` / `summary.json` (S3 fields)

Written to `OUTPUT_DIR = ../research_runs`. run.json is the S2 shape (one per arm × repeat × G), with additive
`meta` fields and a new `meta.arm` value space for the two routed quantum arms:

- `meta.arm ∈ {"quantum_swap", "quantum_teleport", "classical", "ideal"}` — S3 splits S2's `"quantum"` into the two
  routings (the epic §4 `meta.arm` contract remains "names the inheritance channel"; S3 names the *routing* of it).
- `meta.routing ∈ {"swap", "teleport"}` — set on the two quantum arms (absent/`null` on classical/ideal).
- `meta.bond_dist: <int>` — physical routing span of each routed inheritance bond.
- `meta.anchors: <str>` — which generation bonds were routed long-range (`"all"` or a list).
- `meta.logical_depth: <int>` — `qc.depth()` of this run's lineage circuit (M6; epic §4 field, introduced by S3).
- `meta.ancillas: <int>` — `2 * num_routed_bonds` for teleport, `0` for swap (AC-S3.3 honesty).
- `meta.herald: <bool>` and `meta.herald_frac: <float>` — teleport-only; `herald_frac = kept/total` when heralded.
- `meta.routing_cost: <str>` — the AC-S3.3 caveat string ("constant-depth long-range interaction at the cost of
  ancillas and classical feed-forward latency; not a free bypass").
- `meta.noise_model: <str|null>` — the noisy Aer backend used (Q7), or `null` for noiseless/hardware.

run.json path (extends S2 with the routing token): `f"{name}_{arm}_G{G}_{backend}_seed{seed}_{ts}_run.json"`
(the `arm` token already carries `_swap`/`_teleport`, so no separate routing token is needed).

**summary.json** — extends the S2 `sweep` array with the S3 headline:

```jsonc
{
  "meta": {
    "project": "artificial-life", "study": "coherence-depth-genealogy",
    "backend": "sim|<hw>", "sim": true|false, "base_seed": <K>, "repeats": <R>,
    "gmin": <int>, "gmax": <int>, "shots": <S>, "k": <int>,
    "pheno_coupling": <float>, "bond_dist": <int>, "anchors": <str>,
    "routing": "both", "herald": <bool>, "noise_model": <str|null>, "run_files": [ ... ]
  },
  "sweep": [
    { "G": <int>,
      "per_generation": [
        { "gen": <g>,
          "C_g_mean": { "quantum_swap": <f>, "quantum_teleport": <f>, "classical": <f>, "ideal": <f> },
          "C_g_std":  { "quantum_swap": <f>, "quantum_teleport": <f>, "classical": <f>, "ideal": <f> } }
      ],
      "gstar": { "swap": {"k2": <int|null>, "k3": <int|null>},
                 "teleport": {"k2": <int|null>, "k3": <int|null>} },
      "delta_gstar": { "k2": <int|null>, "k3": <int|null> },   // teleport − swap (M5, epic §4)
      "logical_depth": { "swap": <int>, "teleport": <int> } }   // mean over repeats (M6)
  ],
  "per_generation": [ ... ],                    // largest-G sweep entry (S4 back-compat)
  "gstar": { "swap": {...}, "teleport": {...} },
  "delta_gstar": { "k2": <int|null>, "k3": <int|null> }         // headline Δg* at largest G
}
```

Field names `meta.arm`, `meta.entropy_provenance`, `correlation_temporal.{C,c,C0}`, `per_generation[].C_g_mean/std`,
`gstar`, `logical_depth`, `delta_gstar` are the epic §4 contract — **do not rename**; S4 consumes them. The new
`meta.routing`/`bond_dist`/`anchors`/`ancillas`/`herald`/`routing_cost`/`noise_model` fields and the split
`quantum_swap`/`quantum_teleport` arm keys are S3 additions (superset, not a break).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **CD-1** Copy, don't import — copy S2's machinery + S0 operators + the two QuantumLife routing primitives verbatim
  into `stage3_teleport.py` with `# ported from …` comments. No `from stage2_scale import`.
- **CD-2** `pipeline_common` stays external — copy S2's probe idiom; `old/code` resolves; stub keeps `--sim` importable.
- **CD-3** Temporal axis — reuse `temporal_correlation` unchanged; `T` = phenotype `⟨σ_z⟩_p`, anchored at T₀.
- **CD-4** Two matched arms, one schedule — for S3 the *matched pair* is the two routings: hold fixed across
  `quantum_swap` and `quantum_teleport` the population = 1, G, the **same** Q-EaaS `theta_seq` slice, pheno-coupling,
  measurement settings, shots, and `bond_dist`/`anchors`. Swap **only** the routing of the clone CX. Repeat `r`
  uses `seed+r` in every arm. The classical surrogate and ideal arm are routing-independent and shared.
- **CD-5** g\* = `max g≥1 : |C_q(g)−C_cl(g)| > k·σ(g)`, k=2 headline (k=3 reported); σ from `--repeats`. Computed
  once per routing; `Δg* = gstar_teleport − gstar_swap` (M5).
- **CD-6** Cloning-confound control mandatory — the ideal noiseless `C(g)` curve reported alongside both routed
  quantum arms at every G (carried from S2, first-class).
- **CD-7** Certified Q-EaaS — mutation angles from fetched bytes, receipts logged, **fail-closed** on `QRNGUnavailable`.
- **CD-8** Minimal build — single linear lineage, one observable, population = 1; **no** death/interaction between
  distinct individuals/selection. Teleport is introduced **here and only here** (S3), as the routing of the
  inheritance bond — not as inter-individual interaction. Code paths for population/death stay absent, not stubbed.
- **CD-9** Sim-first — fix the pipeline + the `logical_depth` claim in `--sim`, then get the Δg\* signal on a noisy
  backend (Q7) and/or confirm on Heron r2 at the identified coherent G.

---

## 6. File plan (concrete paths)

Python idioms: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`.
No raw SQL (N/A). One new file.

### `artificial-life/code/stage3_teleport.py` (new)

Copy `stage2_scale.py` top-to-bottom, then apply the S3 deltas. Structure:

1. **Module docstring** — what S3 proves (Δg\* from teleport-vs-SWAP routing of the inheritance bond, `logical_depth`
   evidence, honest ancilla/latency cost); the decoherence-only caveat (Δg\*=0 on noiseless sim); provenance notes
   (ported from `stage2_scale.py`, `research_qtree_teleport.py`, `research_qtree_swaplr.py`).
2. **Imports + dual-path setup** — copy S2's `pipeline_common` probe + stub, qiskit imports (add nothing new;
   `if_test`/dynamic circuits are core qiskit), `SIM = AerSimulator(method="statevector")`, `OUTPUT_DIR`,
   `QEAAS_URL_DEFAULT`, frozen constants, `from qrng_client import …`. For Q7 add an optional noisy-backend factory
   (`AerSimulator.from_backend(Fake…)` — imported lazily so `--noise-model` unset keeps the statevector path).
3. **Operators** — copy S2's `m_theta_matrix`, `m_gate`, `apply_clone`, `phenotype_map`, `_z_expectation_statevector`
   verbatim. **`apply_clone` gains routing** (delta below).
4. **`temporal_correlation`, `_mutation_schedule`, `run_classical_surrogate`, `run_ideal_correlation`,
   `compute_gstar`, `_aggregate_per_generation`, `_read_env_key`** — copy S2 verbatim.
5. **Routing primitives — ported (CD-1):**
   - `_swap_cx(qc, lo, hi) -> None` — copy `research_qtree_swaplr.py:173` verbatim (`# ported from …`).
   - `_teleport_cx(qc, ctrl, tgt, a1, a2, tel, k, feedforward=True) -> None` — copy
     `research_qtree_teleport.py:201` verbatim (`# ported from …`).
   - `resolve_bonds(anchors, n_slots) -> list[int]` — **temporal adaptation** of the ported helper: return the set
     of generations `g` (1 ≤ g ≤ n_slots-1) whose clone bond is routed long-range. `"all"` → `range(1, n_slots)`;
     a comma list → those generations (clamped to `[1, n_slots-1]`). Keep a provenance comment; note the semantic
     re-aim from "(slot, slot+dist) spatial pairs" to "which generation bonds are routed".
6. **`apply_clone_routed(qc, parent, ancilla, bond_dist, routing, corridor, tel, k, feedforward) -> int`** — the S3
   core delta. Wraps S2's `apply_clone`: emit `Ry(PHI, ancilla)` (local, unchanged), then route the parity CX:
   - `routing == "swap"`: `_swap_cx(qc, lo=parent, hi=ancilla)` where `parent`/`ancilla` are `bond_dist` apart in
     circuit-index space (the intervening `corridor` qubits are idle spacers the ladder traverses).
   - `routing == "teleport"`: `_teleport_cx(qc, ctrl=parent, tgt=ancilla, a1=corridor[0], a2=corridor[1], tel, k,
     feedforward)` (2 ancillas per bond; constant depth).
   - `routing == "direct"` (bond_dist ≤ 1 or generation not in the routed set): plain `qc.cx(parent, ancilla)` — the
     S2 baseline, so `bond_dist=1` reproduces S2 byte-for-byte and is the sanity control.
   Returns the running teleport-bond counter `k` (advanced only when a teleport bond is emitted).
7. **`build_lineage_routed(theta_seq, n_slots, pheno_coupling, bond_dist, routing, anchors) -> tuple[QuantumCircuit,
   int, int]`** — copy `build_lineage_quantum` @269 and swap the clone step for `apply_clone_routed`. Allocate the
   registers so consecutive genotype qubits are `bond_dist` apart (strided genotype spine + spacer/ancilla corridor
   qubits + one phenotype ancilla per gen + a `tel` classical register of width `2*num_teleport_bonds` when routing
   is teleport). Return `(qc, logical_depth=qc.depth(), num_teleport_bonds)`. At `bond_dist=1` / `routing="direct"`
   the circuit is byte-identical to S2's `build_lineage_quantum`.
8. **`sample_quantum_arm(qc, shots, args, backend, qubit_list, force_sim, want_tel) -> list[str]`** — copy S2 @297;
   two extensions: (a) the `--sim` path optionally targets the noisy Aer backend (Q7) instead of the statevector
   `SIM` when `args.noise_model` is set and `force_sim` is False; (b) the hardware path reads the `tel` register too
   when `want_tel` (heralded teleport) — mirror teleport `run_hw` @415 (`res[0].data.tel.get_bitstrings()`, tel
   **not** reversed) and return `(fields, tel)`; keep the `c`-only return when `want_tel` is False. Heralded
   post-selection (keep shots with `set(t) <= {"0"}`) applied here or in `run_once` (mirror teleport `run_once` @476).
9. **`run_once(args, seed, arm, G, theta_seq_full, provenance_full, backend, backend_name, calib, qubit_list)`** —
   copy S2 @432; branch the two routed quantum arms through `build_lineage_routed(..., routing=…)` +
   `sample_quantum_arm(..., want_tel=args.herald and routing=="teleport")`; classical/ideal arms unchanged. Record
   `meta.routing`, `meta.bond_dist`, `meta.anchors`, `meta.logical_depth`, `meta.ancillas` (`2*num_teleport_bonds`),
   `meta.herald`/`meta.herald_frac`, `meta.routing_cost`, `meta.noise_model` (§4). Write run.json with the routed
   `arm` token.
10. **`main()`** — copy S2 @588 and:
    - argparse: add `--routing {swap,teleport,both}` (default `both`), `--bond-dist` (default 3),
      `--anchors` (default `all`), `--herald` (default False), `--noise-model` (default None). Keep S2's flags.
    - arms: when `--routing both` → `["quantum_swap", "quantum_teleport", "classical", "ideal"]`; a single routing →
      `["quantum_<routing>", "classical", "ideal"]`.
    - qubit budget: the strided layout needs `bond_dist·G` genotype-spine slots + phenotype ancillas + teleport
      ancillas — recompute `n_q` accordingly and reuse the `--sv-max-qubits` guard (§7, §9). `best_chain(backend,
      n_q)` for hardware; teleport arm leaves `initial_layout` unpinned (opt-3 routes ancillas, per teleport `run_hw`).
    - sweep loop: identical to S2, but aggregate per routing and emit `delta_gstar = gstar_teleport − gstar_swap`
      and `logical_depth = {swap, teleport}` (mean over repeats) into each `sweep[]` entry and at top level.
    - herald guard: warn when `0.25**num_teleport_bonds * shots < 200` surviving shots (mirror teleport `main` @627).
11. **`if __name__ == "__main__": main()`**.

CLI (`main`) — S2 flags unchanged; S3 adds:

| flag | type | default | note |
|---|---|---|---|
| `--routing` | {swap,teleport,both} | both | how the clone CX is routed; `both` runs the matched pair for Δg\* |
| `--bond-dist` | int | 3 | physical routing span of each routed inheritance bond (1 = S2 baseline) |
| `--anchors` | str | all | which generation bonds are routed long-range (`all` or a comma list) (Q5) |
| `--herald` | flag | False | teleport-only heralded post-selection (`tel==00`); small-scale noise filter (§9) |
| `--noise-model` | str | None | noisy Aer backend (e.g. a Fake Heron) so `--sim` shows a Δg\* signal (Q7) |

No other files. `research_runs/` already exists.

---

## 7. The physics/maths S3 fixes (the load-bearing detail)

- **What is routed, and only that.** The lineage's inheritance is `apply_clone(parent=g-1, ancilla=g)` = a local
  `Ry(PHI, child)` followed by the parity `CX(g-1 -> g)` (S2 @135–141). S3 routes **only that CX** across a physical
  span `bond_dist`; the `Ry`, the mutation `m_gate`, and the (local) `phenotype_map`+measure are untouched. So the
  swap and teleport arms are the identical experiment save for the routing of one gate per routed generation — the
  matched comparison CD-4 demands.
- **Why Δg\* is a decoherence effect (the central honesty point).** `_swap_cx` and `_teleport_cx` implement the
  **same logical** `CNOT(ctrl->tgt)`. On a noiseless statevector they yield identical states, so identical `C(g)`
  and **Δg\* = 0 by construction**. The difference is *depth*: swap spends ~`2·bond_dist` SWAPs (O(distance)),
  teleport spends a constant-depth Bell-pair + 2 measures + feed-forward. Depth only converts to a `C(g)` gap under
  **decoherence** — i.e. on hardware or a noisy sim. Therefore:
  - **Noiseless `--sim`** validates: circuits build, both routings produce valid `C(g)`, and
    `logical_depth(swap) ∝ bond_dist·G` while `logical_depth(teleport) ≈ const` (M6, AC-S3.1). Δg\* here is 0 — **by
    construction, not a null result** (state this in S4, mirroring S2's ideal≡quantum note).
  - **Noisy sim (`--noise-model`) or Heron r2** validates the actual **Δg\*** (M5): the SWAP arm decoheres faster
    (more gates), its `g*` drops below teleport's, and `Δg* = gstar_teleport − gstar_swap > 0` is the extra coherent
    generations bought by constant-depth routing.
- **The "constant depth 9" quote vs the ported primitive (AC-S3.1).** The AC (and the QDEP narrative) says
  "constant depth **9**". The ported `_teleport_cx` documents only "**constant depth**" — **there is no literal 9 in
  the code** (survey-confirmed). The "9" traces to QuantumLife's viz-9 figure, not a code invariant. S3 does **not**
  assert 9: it **measures** `qc.depth()` for both routings and reports the observed constant for teleport against the
  distance-growing number for swap. If the developer wants the literal-9 framing, S3 can additionally report the
  per-bond teleport sub-depth, but the headline is the measured curve (§9).
- **Δg\* aggregation (M5, AC-S3.2).** At each G, over `--repeats`: aggregate `C(g)` mean±σ for `quantum_swap`,
  `quantum_teleport`, `classical`, `ideal`; `gstar_swap = compute_gstar(C_swap, C_classical, σ, k)`,
  `gstar_teleport = compute_gstar(C_teleport, C_classical, σ, k)` (**same** classical surrogate — routing-independent),
  `delta_gstar = gstar_teleport − gstar_swap`. Expected shapes: (a) Δg\* > 0 — teleport buys coherent generations
  (Bull); (b) Δg\* ≈ 0 even on hardware — routing depth is not the binding constraint at these G/bond_dist, or the
  ancilla/latency overhead of teleport eats its depth saving (QDEP §11, a real reported null). Both are publishable.
- **Qubit budget & the `--sv-max-qubits` guard.** The strided genotype spine spans ~`bond_dist·G` slots; add one
  phenotype ancilla per gen and 2 teleport ancillas per routed bond. This is **much** heavier than S2's `2·(G+1)`.
  Noiseless statevector is capped (`--sv-max-qubits`, default 26) → S3 sim runs stay at small G and small bond_dist
  (e.g. G≤4, bond_dist≤3). The Δg\* signal comes from `--noise-model` (which can also be MPS/`--sv-max-qubits`-bound)
  or from a single small-G hardware confirm. Reuse the S2 guard and abort with a clear message when the budget blows.
- **Heralded teleport statistics (§9).** With feed-forward (default) there is no post-selection — any G is fine.
  With `--herald`, the kept fraction is ~`0.25**num_teleport_bonds`; since `anchors="all"` routes every generation,
  `num_teleport_bonds = G`, so herald kept ~`4^-G` — usable only at tiny G or with a small `--anchors` subset. Herald
  is therefore a **small-scale noise-filter cross-check**, not the headline path.
- **Entropy provenance (M7, CD-7) unchanged.** `_mutation_schedule` fetches the certified Q-EaaS bytes once per
  repeat, sliced per G; both routings + classical + ideal share the identical `theta_seq`/receipt slice at matched
  (G, repeat). Fail-closed on `QRNGUnavailable`.

---

## 8. Manual verification (no automated tests)

Run from `artificial-life/code/` (sim-first, CD-9):

```bash
cd artificial-life/code
# A) noiseless sim: pipeline + logical_depth claim (Δg*=0 by construction here)
python stage3_teleport.py --gmin 2 --gmax 4 --bond-dist 3 --routing both \
    --shots 4096 --seed 100 --repeats 4 --name qdep_s3_sim
# B) noisy sim: the Δg* signal without QPU (Q7)
python stage3_teleport.py --gmin 2 --gmax 4 --bond-dist 3 --routing both \
    --noise-model fake_heron --shots 4096 --seed 100 --repeats 4 --name qdep_s3_noisy
# C) hardware confirm at the coherent G the noisy sweep identifies (single G, conserve QPU)
python stage3_teleport.py --gmin 4 --gmax 4 --bond-dist 3 --routing both \
    --no-sim --backend '' --shots 8192 --seed 100 --repeats 4 --name qdep_s3_hw
# D) S2 parity sanity: bond_dist 1 must reproduce S2's quantum arm
python stage3_teleport.py --gmin 2 --gmax 4 --bond-dist 1 --routing teleport \
    --shots 4096 --seed 100 --repeats 2 --name qdep_s3_parity
```

- **§8-A — AC-S3.1 (`logical_depth`)** — in run (A), `meta.logical_depth` for `quantum_swap` grows with `bond_dist`
  and with G; for `quantum_teleport` it stays ~flat across G. `summary.sweep[i].logical_depth.{swap,teleport}`
  present at every G; swap ≫ teleport at bond_dist 3.
- **§8-B — AC-S3.2 (Δg\*)** — `summary.sweep[i].delta_gstar.{k2,k3}` present and integer at each G, and top-level
  `delta_gstar` = largest-G entry. In (A) Δg\* = 0 (noiseless, by construction — confirm the two `C(g)` curves
  coincide). In (B)/(C) `gstar_teleport ≥ gstar_swap` (Δg\* ≥ 0) or a stated null with error bars.
- **§8-C — AC-S3.3 (honest cost)** — the `quantum_teleport` run.json carries `meta.ancillas == 2*num_bonds > 0`,
  `meta.routing_cost` = the "not a free bypass" string, and (if `--herald`) `meta.herald_frac`; the `quantum_swap`
  run.json has `meta.ancillas == 0`. The printed summary states the ancilla + feed-forward-latency cost explicitly.
- **§8-D — S2 parity** — run (D) at `--bond-dist 1` must produce a `quantum_teleport` `C(g)` curve matching S2's
  `quantum` arm within shot noise at the same seed (the routing collapses to a plain `cx`; `logical_depth` matches
  S2). Confirms S3 added routing without perturbing the physics.
- **Provenance (M7)** — all arms at a given (G, repeat) share the same `request_id`/`angle_rad` slice; unset
  `QEAAS_API_KEY` → abort exit 1 with `QRNGUnavailable`, no PRNG fallback (carried from S2).
- **Schema check** — `python -c "import json;d=json.load(open('<summary>'));print(d['delta_gstar'],
    d['sweep'][0]['logical_depth'], d['sweep'][0]['per_generation'][0]['C_g_mean'].keys())"` → `delta_gstar`
  present, `logical_depth` has swap+teleport, arm keys include `quantum_swap`/`quantum_teleport`/`classical`/`ideal`.
- **Herald guard** — `--herald --gmax 3 --anchors all` prints the expected kept fraction (~`0.25**G`) and warns when
  surviving shots < 200; confirm it does not silently proceed on empty post-selection.

---

## 9. Out-of-context risks / notes

- **Δg\* = 0 on noiseless sim is expected, not a null.** The most likely misread of S3. Swap and teleport are the
  same logical map; only decoherence separates them. The plan and S4 must label the `--sim` overlap "by construction"
  and source Δg\* from `--noise-model`/hardware (§7). Do **not** report the sim Δg\*=0 as the study's answer.
- **"Constant depth 9" is a narrative number, not a code invariant.** The AC quotes "constant depth 9"; the ported
  `_teleport_cx` says only "constant depth" and contains no 9. S3 measures `qc.depth()` and reports the observed
  constant — do not hard-code or assert 9 (honesty invariant, AC-S3.3 / AC-S4.3).
- **Qubit-budget blow-up.** The strided routed spine (`~bond_dist·G` + ancillas) far exceeds S2's `2·(G+1)`. The
  `--sv-max-qubits` guard bounds the noiseless-sim sweep to small G/bond_dist; large-G / large-bond_dist runs need
  hardware or a memory-bounded noisy method (MPS). Guard must abort with a clear message, never OOM the box.
- **Teleport ancilla/latency can erase the depth saving (QDEP §11, AC-S3.3).** If preparing the Bell pair and paying
  feed-forward latency costs as much coherence as the SWAP depth it removes, Δg\* ≈ 0 on hardware — a **real,
  reportable** result (Value-if-null spirit). Do not tune bond_dist/anchors to manufacture a positive Δg\*.
- **Heralded teleport dies at scale.** kept ~`4^-num_bonds`; with `anchors="all"`, `num_bonds=G` → unusable past
  tiny G. Feed-forward (default) is the honest dynamic-circuit path; herald is a small-scale cross-check only.
- **`--anchors all` vs a subset (Q5, §11).** Routing every generation bond is the truest "depth eats the whole budget"
  story but is the heaviest. A small `--anchors` subset (route a few generation bonds) is the cheaper, herald-viable
  variant and the closer analogue of QuantumLife's `--anchors 0,3,6`. Default `all`; subset available. See Q5.
- **`tel` register bit order.** teleport `run_hw` reverses `c` but **not** `tel` (survey-confirmed @436–437). Carry
  that exactly when reading heralded outcomes, or the post-selection mask is wrong.
- **`best_chain` may raise.** For the long strided spine, a SWAP-free length-`n_q` chain may not exist on the chosen
  backend → `RuntimeError`. Catch and report (suggest a smaller bond_dist/G), don't crash opaquely.
- **Dynamic-circuit support on statevector sim.** S1/S2 already use mid-circuit `measure`; S3 adds `if_test`
  feed-forward. Confirm the installed `qiskit-aer` statevector method executes `if_test` (recent versions do); if
  not, fall back to the noisy Aer backend for the teleport arm and note it. No new pip dependency expected.
- No new pip dependency — `qiskit`, `qiskit_aer`, `numpy` in env; a Fake-backend noise model uses `qiskit_ibm_runtime`/
  `qiskit_aer` already present. `qrng_client.py` uses stdlib `urllib`.

---

## 10. Ground rules honored

- Every AC (S3.1–S3.3) quoted verbatim from the epic / `qdep-1` / QDEP §6.4 and mapped to a §8 manual check.
- Every file path in §6 is concrete; one new file, no edits outside `artificial-life/code/`.
- Epic cross-cutting decisions (CD-1..CD-9) adopted without re-arguing; teleport enters only at S3 (CD-8),
  confound curve + fail-closed Q-EaaS carried forward (CD-6/CD-7).
- The "constant depth 9" narrative is **measured, not asserted**; Δg\*=0-on-noiseless-sim is disclosed as
  by-construction; the ancilla/latency cost is recorded (AC-S3.3 honesty invariant, AC-S4.3).
- No tests, no test files, no test-impact section (project directive). Verification is manual (§8).
- Strict typing + Python idioms (`from __future__ import annotations`, full hints); no raw SQL.

---

## 11. Resolved decisions (developer, 2026-08-19 — all proposed defaults accepted)

- **Q5 — Routed-bond geometry: RESOLVED → `--anchors all`, `--bond-dist 3`.** Route **every** consecutive-generation
  clone bond across `bond_dist=3`, each via `--routing`. Truest "routing depth eats the whole coherence budget"
  mapping; swap depth grows ∝ `bond_dist·G`. Genotype qubits strided by `bond_dist`, intervening qubits idle spacers
  (swap) / teleport ancillas occupy. A small `--anchors` subset remains available as the cheaper, herald-viable
  variant, off by default.
- **Q6 — Shot/repeat budget: RESOLVED → `--shots 8192`, `--repeats 8`** (match S2; teleport's extra mid-circuit
  measures widen σ, so no smaller).
- **Q7 — Δg\* signal source: RESOLVED → noisy-sim arm accepted.** Add `--noise-model` targeting a Fake-Heron Aer
  backend (`AerSimulator.from_backend(...)`) so a Δg\* signal appears in sim without QPU; keep a single small-G
  Heron-r2 confirm for the paper. Noiseless `--sim` stays the pipeline + `logical_depth` check (Δg\*=0 by
  construction, §7).
- **Q8 — arm encoding: RESOLVED → dual encoding accepted.** Split `meta.arm` into
  `quantum_swap`/`quantum_teleport` **and** carry `meta.routing`, preserving the epic §4 `meta.arm` contract and
  giving S4 either handle.

---

## 12. Q-EaaS API contract

Unchanged from S2 §12: `GET /v1/random/bytes?size=&format=`, `X-API-Key` header, `32 ≤ size ≤ 4096`, response
`{request_id, format, data, entropy_epoch, timestamp, receipt}` with nullable `receipt`, 401/429(`Retry-After`)/
503/422 handling. S3 reuses the copied `qrng_client.py` verbatim; no client-side change.

---

## 13. After approval

Once the open questions are answered and the plan approved, run
`/implement-feature artificial-life/plans/feature-S3-teleport.md`.
S3 gate before S4: a clean `--sim` sweep proving the pipeline + the `logical_depth` split (M6, teleport ~constant vs
swap ∝ distance), a Δg\* measured on a noisy backend and/or a single Heron-r2 confirm (M5) with error bars **and its
honest ancilla/latency caveat recorded** (AC-S3.3), and the certified Q-EaaS provenance logged fail-closed (CD-7, M7).
Whatever Δg\* comes out — including Δg\* ≈ 0 (teleport overhead cancels the depth saving) — is the publishable result
(QDEP §11, honesty invariant AC-S4.3); do **not** tune `bond_dist`/`anchors`/routing to manufacture a positive Δg\*.
S4 (THE figure + IEEE paper) aggregates S0–S3 only after Δg\* is banked.
