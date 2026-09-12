# PJ0 — Design decision: `natural` + `separable` is the setup going forward

**Date:** 2026-09-12
**Status:** DECIDED. This is the substrate PJ1 (arena) extends.
**Backend:** ibm_kingston, W4, S4, shots=8192, repeats=1, MUT_SCALE=0 (clean GHZ).
**Decision:** headline arm = `soma_death=natural`, `phenotype=separable`.
`local_damping` kept as the rigid-rate **reference/fallback** arm only.

This file records *why* the four candidate designs were run, what the live
hardware said, and why `natural`+`separable` was chosen as the going-forward
setup. Data is the 2×2 factorial (soma_death × phenotype) below.

---

## The 4 designs (live hardware, ibm_kingston, W4/S4)

The 2×2 factorial: soma-death mechanism × phenotype coupling.

| soma_death       | phenotype   | joint witness ⟨X^⊗4⟩ | separable null | alive | run file |
|------------------|-------------|----------------------|----------------|-------|----------|
| **natural**      | **separable** | **0.899**          | ~-2.5e-09      | 2.0   | `pj_0.0_LIVE_W4_S4_natural_separable_ibm_kingston_20260912-203122.json` |
| local_damping    | separable   | 0.768                | ~5.8e-08       | 3.0   | `pj_1.1_LIVE_damping_seperable_local_damping_separable_ibm_kingston_20260912-205115.json` |
| natural          | entangled   | 0.120 ⟵ collapsed    | ~-8.4e-14      | null  | `pj_1.1_LIVE_natural_entangled_natural_entangled_ibm_kingston_20260912-204435.json` |
| local_damping    | entangled   | 0.079 ⟵ collapsed    | ~1.3e-15       | null  | `pj_1.1_LIVE_Damping_entangled_local_damping_entangled_ibm_kingston_20260912-203902.json` |

(`survives` flag in the JSONs = `signal > K*sigma` — a beats-the-null test,
NOT a strength test. The entangled arms "survive" that weak test at 0.08/0.12
but are collapsed relative to 0.899. Headline should key on strength, not the
nonzero flag.)

**Reading the table:**
- **Phenotype axis decides everything.** `separable` keeps the witness alive
  (0.77–0.90). `entangled` collapses it (0.08, 0.12). That is the P2 diagnosis
  confirmed live: `cx(g,p)` coupling + soma death irreversibly decoheres the
  gene-witness. Severing it rescues the witness.
- **Within separable, natural beats damping:** 0.899 vs 0.768 (~12σ, sigma≈0.011).

---

## The four circuit designs — per-individual schematics

Each design differs only in *how the soma is wired* and *how it dies*. Below is one
individual `k` (germ qubit `g_k`, soma qubit `p_k`, and — damping only — a bath
qubit `b_k`). The germ line is always the same clean GHZ ladder; the whole decision
is what the soma does to it. (Full W4 circuits: `research_runs/pj/*_circuit_w4_s4_*.txt`.)

Legend: `[clone]` = `cx(g_{k-1},g_k)` self-replication · `Ry(θ)` = mutation ·
`Ry(aged)` = separable diagonal trait · `●─X` = CX · `H,M` = X-basis witness readout.

### 1. natural + separable  — THE WINNER  (2 qubits/individual, no bath)
```
g_k: ─[clone]─Ry(θ_k)────────────────────────────●──H──M   ← germ line (GHZ witness)
p_k: ─Ry(aged)──────────── idle ⇒ real T1 decay ─────────M   ← soma (classical trait)
```
Germ and soma **never share a gate.** Soma just idles and dies by real hardware T1.
No `cx(g,p)`, no bath, no engineered dissipation. Leanest possible.

### 2. local_damping + separable  (3 qubits/individual, +bath)
```
g_k: ─[clone]─Ry(θ_k)──────────────────────────────────●──H──M
p_k: ─Ry(aged)──────────●───────────────X──────────────────M
                        │ cry(g_eff)     │ cx
b_k: ───────────────────X────────────────●───────────────    ← bath, discarded
```
Germ still safe (no `cx(g,p)`), but death is **faked** with an extra bath qubit +
`cry` + `cx`. Costs +1 qubit and 2 extra 2-qubit gates per individual, for a rigid
tunable death rate. More machinery, none of it quantum-claim.

### 3. natural + entangled  (2 qubits/individual)  — witness collapses
```
g_k: ─[clone]─Ry(θ_k)──●───────────────────────────H──M
                       │ cx(g,p)  ← the P2 wound restored
p_k: ─Ry(aged)─────────X──── idle ⇒ T1 decay ───────H──M
```
The `cx(g,p)` couples the mortal soma to the immortal germ. When the soma decays,
that back-action **decoheres the gene-witness.** Witness 0.90 → 0.12.

### 4. local_damping + entangled  (3 qubits/individual)  — worst
```
g_k: ─[clone]─Ry(θ_k)──●──────────────────────────H──M
                       │ cx(g,p)
p_k: ─Ry(aged)─────────X──●───────────X───────────H──M
                          │ cry        │ cx
b_k: ─────────────────────X────────────●──────────
```
Both wounds at once: soma coupled to germ **and** dissipated through a bath — the
exact P2 death channel. Witness 0.08 (floor).

---

## Why natural + separable won on EVERY axis — not just entanglement

The witness is the headline, but natural+separable also dominates on qubit cost,
gate/error budget, faithfulness, and — decisively — scalability. Only reproducibility
goes to damping.


| axis | **natural+sep** | local_damping+sep | natural+ent | local_damping+ent |
|---|---|---|---|---|
| witness ⟨X^⊗4⟩ (live) | **0.899** | 0.768 | 0.120 | 0.079 |
| qubits / individual | **2** | 3 | 2 | 3 |
| 2-qubit gates / individual | **1** (clone) | 3 (clone+cry+cx) | 2 (clone+cx_gp) | 4 |
| germ↔soma coupled? | **no** | no | yes | yes |
| bath qubit? | **no** | yes | no | yes |
| death = real physics (T1)? | **yes** | no (engineered) | yes | no (engineered) |
| max width on 107-clean-chain | **~53** (2W) | ~35 (3W) | ~53 | ~35 |
| tunable/rigid death rate? | no (T1 drifts) | **yes** | no | yes |

**1. Fewer 2-qubit gates = less error = higher witness (same width).** natural+sep
carries one 2-qubit gate per individual (the clone). Damping adds `cry`+`cx` per
individual; entangled adds `cx(g,p)`. On hardware, 2-qubit gates are the dominant
error source, so the leanest circuit reads the strongest witness even before any
biology argument — which is exactly what 0.899 > 0.768 shows.

**2. Qubit cost is the scalability lever — this is WHY W50 was reachable.** natural
has no bath: **2 qubits/individual vs 3** for damping. On `ibm_kingston`'s longest
clean SWAP-free chain (107 qubits), that is **~53 individuals for natural vs ~35 for
damping.** The W54 qubit-count wall (`research_runs/pj/pj_1.2_LIVE_LIMIT_w54LIMITFOUND.txt`,
needs 108 clean, chain maxed at 107) is a *natural-mode* wall at 2W. Damping would
have hit its own wall ~1.5× sooner. Leanness is not cosmetic — it directly bought the
scale result (see `PJ0_CONCLUSION.html`).

**3. Faithfulness — the stated goal.** natural death = real hardware T1 relaxation
toward |0⟩. No injected bath, no `cry` operator simulating decay. Damping fabricates
death with an ancilla + controlled rotation. The trait is classical by the 2018
paper's own text, so a diagonal soma dying by real physics is the *honest* model;
the engineered bath is a simulation of one.

**4. The only thing damping wins: reproducibility.** natural's rate = hardware T1,
which drifts run-to-run and is not tunable. Damping's `gamma` is a controllable,
reproducible knob. That is the sole reason `local_damping` is kept — as a rigid-rate
**reference/fallback** arm to quantify T1-drift risk, not as the headline.

**Verdict:** natural+separable Pareto-dominates on witness, qubit cost, gate/error
budget, and faithfulness. Damping wins only reproducibility. Given the stated goal
(a faithful model that still survives at scale), the choice is unambiguous.

---

## Why the disconnected soma is correct (not "no quantum part")

Inspecting the natural+separable circuit (`circuits/` + the run's draw):

- **Genotype q_0–q_3 (germ line) = fully connected — THIS is the quantum.**
  founder `Ry(π/2)` on q_0, then CX cascade q_0■→q_1, q_1■→q_2, q_2■→q_3 =
  GHZ chain; all four get `H` before measure → X-basis witness `⟨X^⊗4⟩` = 0.899.
  Four qubits genuinely entangled. Real quantum.
- **Soma q_4–q_7 = one `Ry` each, no CX, no bath — disconnected by design.**
  This is the Weismann barrier built physically. The soma is *supposed* to be
  severed.

The quantum claim was ALWAYS genotype-only (CD-3). The trait (alive/dead) is
**classical in the 2018 paper's own text**. A diagonal, disconnected soma is a
*faithful* expression, not a cheat.

**Why "damping looks more connected" is a trap.** Damping adds
`cry(pheno,bath)` + `cx(bath,pheno)`. Looks busier, but those gates are
soma-internal (pheno↔bath) — they add nothing to the quantum claim (genotype),
they only (1) fake T1 decay with an artificial bath qubit, and (2) add
gates+qubits = more error = lower witness. Natural throws that machinery away
and lets real hardware T1 kill the soma.

**The A/B is the proof it is not backwards.** Connect the soma to the gene
(`entangled` = restore `cx(g,p)`) → witness collapses 0.90 → 0.12. So "more
connections to the gene" kills the quantum. Connecting the soma (what feels
"more quantum") is exactly what destroys it.

---

## Why natural + separable is the going-forward setup

### Faithful to the original — YES
- Genotype GHZ witness `⟨X^⊗W⟩` = the 2018 quantum claim, untouched.
- Soma diagonal/classical = the paper's own text. Separable ≠ cheat.
- Natural death = real hardware T1. No artificial bath, no invented `cry`
  machinery. Physics does the dying. More faithful than damping, not less.

### Better design — YES
- Higher witness (0.899 vs 0.768).
- Leaner segment (2W vs 3W, no bath) → more organisms per chain → scales to the
  PJ1 arena.
- Fewer gates = less error.
- Weismann barrier built physically (soma severed), proven by the A/B collapse.

### Defensible for the thesis — YES
The 2×2 factorial IS the argument: phenotype coupling is the kill switch,
separable is the rescue, hardware-confirmed. Falsifiable, clean. The obvious
challenge — "isn't the severed soma just fluff?" — is answered by the A/B:
connect it and the witness collapses 0.90 → 0.12. Severing is the mechanism,
not laziness.

`local_damping` is retained as the **rigid-rate reference/fallback** arm: it
gives a controllable, reproducible death rate (tunable `gamma`), which natural
does not (natural rate = hardware T1, drifts run-to-run). It is the hedge, not
the headline.

---

## Open holes to close before write-up (do NOT claim these yet)

1. **N=1, W4 only, single calibration snapshot.** 0.899 is one snapshot; natural
   death = T1, drifts run-to-run. Need repeats + a reported T1 band, and the
   **W sweep** — the real thesis question is "does severing `cx(g,p)` push W\*
   past P2's [4,8)?" W4 alone does not answer it. If natural's T1 drift makes it
   non-reproducible across the sweep, fall back to `local_damping`. Decide from
   the sweep, not from W4.
2. **`calibration:null`, `t1_band:null` in every run.** The aging-order-deviation
   gate (AC-PJ0.2) and selective-DD placement (AC-PJ0.3) were never actually
   measured — the circuits were unscheduled (no `--backend` timing). Natural's
   "irregular-but-bounded lifespan" claim is unverified. Backend-scheduled runs
   must populate `calibration`/`t1_band`/aging-order before that claim is made.

---

## Follow-ups (the developer's next runs)

- Witness `⟨X^⊗W⟩` vs W sweep (does severing push W\* past [4,8)?).
- Repeats + T1 band for natural (drift characterization).
- Backend-scheduled runs → populate aging-order deviation + selective-DD check.
- matched-W natural germ/soma vs P2 damping comparison.
- PJ1 arena extends the organism-offset layout with natural+separable as the
  per-organism substrate.
