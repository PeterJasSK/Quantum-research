# How this is a study — the P2 + PJ0 body of work as an informatics thesis

**Scope of this document.** This is not a results file. It is the framing document: it argues
*why the two conclusion pages* (`research/P2_CONCLUSION.html`, `research/pj0_germsoma/PJ0_CONCLUSION.html`)
**already constitute a coherent study**, states precisely **what was reproduced and why**, argues **why
the germ/soma result is a genuine quantum-design contribution and not a biology label on a physics
experiment**, fixes the framing as an **informatics thesis at its core**, and lists **what is still missing
to make it a defensible study / publishable paper**.

Read alongside: `research/pj0_germsoma/DESIGN-DECISION.md` (the four-design decision),
`plans/feature-PJ0-germsoma-split.md` (the build), `plans/epic-qalife-darwinian-richness.md` (the epic).

---

## 1. One-sentence thesis

> **A domain-faithful refactor of a quantum circuit — separating the mortal, measured subsystem from
> the coherent certified register, as dictated by a real biological principle (the Weismann barrier) —
> removes a decoherence channel and moves the model's hardware ceiling from an entanglement wall to a
> qubit-count wall.**

Everything below defends that sentence and lists what is needed to prove it to a paper standard.

---

## 2. What kind of study this is — INFORMATICS at the core

This is deliberately framed as a **computer-science / informatics** thesis, not a physics or biology one.
The object of study is a **quantum circuit design** and the **empirical, measured consequence of a design
change** on real hardware. That is architecture + measurement — the core of applied informatics.

- **Subject:** the mapping of a domain model onto qubits — i.e. *circuit architecture* — and how that
  mapping determines a measurable figure of merit (entanglement-witness retention per qubit).
- **Method:** the standard empirical-CS loop — (1) reproduce a reference implementation, (2) locate its
  failure mode by **static circuit analysis** (walking `qc.data`, no execution), (3) redesign the circuit,
  (4) prove the redesign — not a confound — causes the improvement via an **ablation** (the 2×2 factorial),
  (5) characterize the new **resource ceiling** on hardware.
- **Contribution class:** a **circuit-architecture pattern** ("isolate the lossy/measured subsystem from
  the certified register") shown to act as decoherence mitigation, plus its measured scaling behaviour.

The biology is the **specification** the circuit implements, not the contribution. The contribution is how
faithfully implementing that specification *is itself* the optimization. See §5.

---

## 3. Part A — the reproduction (P2): what, why, how

### What was reproduced
The Alvarez-Rodriguez et al. (2018) "Artificial Life in Quantum Technologies" four-operator genealogy:
self-replication (`cx` clone), mutation (`Ry(θ)`), interaction, and death — and its single non-classical
observable, the **genealogical entanglement witness** `⟨X^⊗W⟩` over the genotype register, with the
classical **separable null** `∏ᵢ⟨Xᵢ⟩` as the control.

### Why reproduce it (three reasons, all methodological)
1. **Baseline.** A design improvement is meaningless without the un-improved reference measured on the same
   hardware, same witness, same gates.
2. **Honesty anchor.** The reproduction (`code/qalife.py`, left byte-stable) fixes the exact 2018 model so
   the novelty cannot be an accidental change of the model. Every later claim is *relative to* this frozen
   reference.
3. **Locating the failure mode.** The reproduction is what exposed the wound: P2 drove the faithful
   amplitude-damping death channel to its ceiling and found the witness collapses at **W\*=9 = 19 qubits**
   (width) and **5 generations** (depth). That collapse is the problem the thesis then solves.

### How it was done
Live on 156-qubit Heron-r2 (`ibm_kingston`), three axes — unitary genealogy (W\*=24=48 qubits, ~6× the
paper's ~4-qubit origin), damping-width (W\*=9), damping-depth (5 generations) — each with a fail-closed
chain-quality gate (abort if 2-qubit error > 0.05 or readout > 0.15) so decay is device physics, not a
broken edge. Result: **every ceiling of the pre-existing design located, not bracketed** — i.e. the
reference is fully characterized, which is the precondition for claiming an improvement over it.

**Diagnosis (the pivot).** The collapse is mechanical: the faithful death operator applies `cx(g,p)` —
entangling the mortal phenotype (soma) to the immortal genotype (germ) — then dissipates the phenotype.
So **body-death irreversibly decoheres the gene-witness.** This is a *circuit-structure* fault, found by
*circuit analysis*, and it is the hinge of the whole thesis.

---

## 4. Part B — the novelty (PJ0): the germ/soma circuit redesign

### The change
Implement the **Weismann barrier** as circuit architecture: the germ line (genotype) carries the GHZ
witness and stays coherent; the soma (phenotype) expresses the trait as a **separable diagonal state** and
dies **in isolation** — `natural` T1 relaxation, no bath, and critically **no `cx(g,p)`**. The soma-to-germ
coupling is severed, so soma death is qubit-disjoint from the witness and cannot touch it. Verified
statically (no gate mixes a germ qubit with a soma qubit — "Static Test 1") before any run.

### The evidence (two experiments)
1. **Ablation — the 2×2 factorial (W=4).** soma-death (natural vs local_damping) × phenotype coupling
   (separable vs entangled). Result: the **phenotype coupling is the kill switch** — separable keeps the
   witness alive (0.77–0.90), re-entangling it collapses it (0.08–0.12). This proves the *design change*,
   not a confound, causes the effect. `natural+separable` wins (0.899) and is the leanest/most faithful arm.
2. **Scaling — the width sweep.** `natural+separable` stays certified at **k=3σ through W=50 = 100 qubits**,
   and the run halted at **W=54 not because the witness died but because the chip ran out of clean qubits**
   (needs a SWAP-free chain of 108; longest clean chain = 107). **The limiting resource flipped from
   entanglement to machine size.**

### Why this is a genuine quantum-design contribution — not "biology relabelled"
This is the section an examiner will press. Four independent design axes improve, measured on hardware
(see `DESIGN-DECISION.md` Table 1b), and every one is a *computing/engineering* quantity:

1. **Fewer 2-qubit gates → higher witness at equal width.** natural+separable has one 2-qubit gate per
   individual (the clone); the damping/entangled arms add `cry`/`cx`. Two-qubit gates dominate NISQ error,
   so the leaner circuit reads a stronger witness (0.899 > 0.768) — a pure circuit-cost effect.
2. **Lower qubit cost → higher scale.** natural has no bath: **2 qubits/individual vs 3**. On the
   107-qubit clean chain that is ~53 individuals vs ~35. **This is why W=50 was reachable at all** — the
   scaling result is a direct consequence of the architecture, not luck.
3. **A decoherence channel removed by construction.** Severing `cx(g,p)` deletes an entangling+dissipative
   path, provably (static disjointness) before running. This is design-time correctness, not post-hoc
   tuning.
4. **The failure mode and the fix are both circuit-structural** — found by static analysis, fixed by
   layout. Nothing here is a biology metaphor; it is a graph property of the circuit.

**So the biology is not decoration — it is the source of the optimization.** The Weismann barrier is a real
biological principle (germ line immortal, soma disposable, information flows germ→soma only). Mapping it
faithfully to qubits *forces* the exact separation (mortal/measured subsystem apart from coherent register)
that removes the decoherence channel. **Sound biology and good quantum engineering coincide** — the
domain-faithful design *is* the better design. That coincidence is the intellectual claim, and it is
falsifiable: the entangled arm (biologically wrong — soma feeding back into germ) is measurably worse.

### The general informatics lesson (portable beyond biology)
> **How a domain model is mapped onto qubits sets its coherence ceiling; isolating any lossy or measured
> subsystem from the certified register is a decoherence-mitigation pattern.** The germ/soma model is one
> instance; the pattern generalizes to any quantum program with a "disposable" or mid-circuit-measured
> register.

That sentence is the transferable contribution — the thing a CS reader takes away even if they never touch
quantum biology.

---

## 5. Why the biology is sound (not just claimed)

- The model is a **published, peer-reviewed** quantum-biology framework (Alvarez-Rodriguez 2018),
  reproduced byte-faithfully — not invented here.
- The **Weismann barrier** (1892) is a foundational, uncontested principle of biology: the germ line is
  the continuous heritable lineage; the soma is mortal; acquired somatic changes do not flow back to the
  germ line. The circuit enforces exactly this: information flows germ→soma (the `Ry(aged)` trait
  expression driven by the genotype value), never soma→germ (no `cx(g,p)`).
- The honesty invariant (CD-4): the trait (alive/dead) is **classical in the 2018 paper's own text**, so a
  diagonal, separable soma is a *faithful* expression, not a shortcut to protect the witness. The A/B makes
  this an experiment (entangled soma is available and measured), not an assertion.
- The sole certified quantum claim is the **genotype-only** witness `⟨X^⊗W⟩`; every diagonal quantity
  (alive-count, lineage depth, phenotype ⟨σz⟩) has an exact classical surrogate and carries no quantum
  claim (CD-3). This is the discipline that keeps the biology honest.

---

## 6. Claims ladder — what is defensible at today's evidence

State claims at the level the data supports; do not climb higher without the runs in §7.

| Claim | Supported now? | Needs |
|---|---|---|
| The 2018 model's faithful death channel collapses the witness (W\*=9, 5 gen) | **Yes** (P2, located) | — |
| The collapse is caused by soma→germ coupling (`cx(g,p)`) | **Yes** (2×2 ablation, live) | — |
| Severing the coupling (germ/soma) rescues the witness | **Yes** (0.90 vs 0.12) | — |
| natural+separable is the best of the four designs | **Yes** (Pareto, live) | — |
| Certified entanglement present to 100 qubits | **Partly** — beats null at k=3σ | pin the *entanglement class* (§7.1) |
| The design certifies **genuine W-partite** entanglement at scale | **NOT yet** | depth-metric per width (§7.1) |
| The hardware limit is qubit count, not decoherence | **Suggestive** (W54 abort) | repeats + push past W54 (§7.2) |
| natural is reproducible / the aging model works | **NOT yet** | scheduled runs, T1 band (§7.4) |

---

## 7. What is missing — the work plan to become a defensible study / paper

Ordered by how hard a reviewer hits it. Each has an acceptance criterion.

### 7.1 Pin what the witness certifies at scale — THE crux
`⟨X^⊗W⟩ = 0.058` at W=50 beats the separable null, but "beats a product-state null" is weaker than
"certifies W-partite genuine multipartite entanglement (GME)." Report the **entanglement-depth metric**
(k=2 headline, k=3, and higher) **per width**, and state exactly the certified class at each W. If W=50
only certifies depth-2 (pairwise), the honest claim is "depth-k entanglement to 100 qubits," not "100-qubit
entanglement." *Acceptance:* a table of certified depth vs W with the GME bound stated and cited.

### 7.2 Repeats + error bars — statistical hardening
Everything is currently **N=1** per width; the non-monotonic points (W=16 at 0.30, W=28 at 0.36) are
uncontrolled run-to-run variance. *Acceptance:* ≥3–5 repeats per width across distinct calibration cycles;
report mean ± band; the ceiling stated as a band, not a point.

### 7.3 Isolate the confound — pure-width vs combined
The PJ0 sweep scales depth with width (steps ≈ W/2), so it measures a *combined* width+depth ceiling.
*Acceptance:* one fixed-steps width sweep and one fixed-width depth sweep, so width and depth ceilings are
separately attributable (as P2 already did for the damping arm).

### 7.4 Measure the design features that are currently only coded
The runs carried `calibration:null` / `t1_band:null` — the **natural aging clock, selective DD, and the
AGING_ORDER_TOL bound** (headline features of the design) were never executed. *Acceptance:* backend-
scheduled runs that populate aging-order deviation + confirm DD lands on germ qubits only; report a T1
band. If not measured, **drop these from the claims.**

### 7.5 Positioning vs prior large-entanglement work
Large GHZ states (100+ qubits) already exist in the literature (e.g. Mooney et al. 2021, IBM). The qubit
count alone is **not** the novelty. *Acceptance:* a related-work section that stakes the claim on the
**decoherence-mechanism / domain-faithful-architecture** result, not the scale number, and cites the
existing GHZ-at-scale results honestly.

### 7.6 Cross-backend / robustness (nice-to-have for a paper)
All data is single-backend (`ibm_kingston`). *Acceptance:* one replication of the headline factorial + a
couple of widths on a second backend, to show the effect is not a device artifact.

---

## 8. Suggested thesis structure (informatics framing)

1. **Introduction** — quantum circuit design as the object; the domain-faithful-mapping thesis (§1).
2. **Background** — the 2018 model, the entanglement witness, NISQ error model, the Weismann barrier as a
   spec; related work on large-scale entanglement (§7.5).
3. **Methodology** — reproduce → static-analyze → redesign → ablate → scale; the honesty invariants (CD-3/4).
4. **Reproduction & failure-mode analysis (P2)** — three axes, located ceilings, the `cx(g,p)` diagnosis (§3).
5. **The germ/soma redesign (PJ0)** — architecture, static correctness, the four designs (§4, DESIGN-DECISION).
6. **Results** — the 2×2 ablation + the width sweep + the qubit-count wall; certification analysis (§7.1).
7. **Discussion** — the portable pattern (§4 lesson), threats to validity (§7), the honest scope (§9).
8. **Conclusion & future work** — PJ1 arena (multi-lineage joint witness).

---

## 9. Scope guard — what NOT to claim

- **Not a quantum speedup.** No classical algorithm is being beaten. The contribution is
  scale · faithfulness · certification of a design change. Say so plainly (CD-4).
- **Not "100-qubit entanglement" unqualified** — only the certified depth class (§7.1).
- **Not a biology discovery.** The biology is the specification; the contribution is the circuit
  architecture and its measured behaviour.
- **Not a solved reproducibility story** until §7.2 and §7.4 are done.

---

## 10. Bottom line

The two conclusion pages already contain the spine of a defensible **masters thesis**: a faithful
reproduction, a circuit-structural diagnosis, a domain-motivated redesign, a controlled ablation proving
causation, and a hardware scaling result with an honest ceiling. What stands between "defensible masters"
and "publishable paper" is not new ideas — it is **statistical hardening (§7.2), confound isolation (§7.3),
one sharp certification statement about what the witness proves at scale (§7.1), measuring the aging/DD
features (§7.4), and honest positioning (§7.5).** Close those five and this is a paper.
