# QDEP — Quantum Darwinian Evolution Protocol
### v2: *Living Genealogies* — merging the Quantum Tree with quantum artificial life

**Author / Project Lead:** Peter Jaš (CNL, Technical University of Košice)
**Status:** Design specification (pre-implementation)
**Builds on:** Quantum Tree (IBM Heron) · Q-EaaS (QRNG) · Alvarez-Rodriguez et al. quantum artificial life (2018)

---

## 0. One-line summary

Take the published quantum-artificial-life protocol (self-replication, mutation, interaction, death, with entanglement inherited across generations) and run it as a *population* on modern dynamic-circuit hardware, using the Quantum Tree as the physical genealogy that records lineage — then test whether inherited entanglement makes the population's evolution reproducibly harder for a classical surrogate to imitate.

---

## 1. What this replaces, and why

The earlier QDEP draft described a 102-qubit "genome" evolving under "hardware noise as selection pressure." Two problems made that hard to defend:

1. **Noise is not a fitness function.** Decoherence acts on states by physical susceptibility, not by any problem-relevant fitness, and it is neither controllable nor reproducible. It can be an *object of study* (does noise bias evolution?) but not the selection mechanism.
2. **Measuring fitness collapses the superposition.** You cannot evaluate a superposed population and silently keep the good ones; measurement gives you one sample.

This version fixes both by grounding the biology in an existing, working protocol and by making selection an explicit, measured operation rather than a metaphor.

---

## 2. Foundations it builds on

**(A) Quantum artificial life — "the wiki system."**
Alvarez-Rodriguez, Sanz, Lamata & Solano, *Quantum Artificial Life in an IBM Quantum Computer*, Scientific Reports 8:14793 (2018), arXiv:1711.09442. First experimental realization of a quantum-artificial-life algorithm on IBM ibmqx4. It encodes four life-like behaviors — self-replication, mutation, interaction between individuals, and death — as a "biomimetic" quantum protocol, and entanglement is inherited through generations via a genealogical network. It ran on only a handful of qubits as a proof of principle.

**(B) Quantum Tree — the genealogy substrate.**
A branching structure grown on real IBM Heron hardware where measured bits dictate branching. In this project the tree stops being a standalone artwork and becomes the *genealogical network itself*: each branch is a reproduction event, each node an individual, and the tree topology is the lineage of the evolving population.

**(C) Q-EaaS — the mutation entropy source.**
Certified QRNG bits with signed provenance receipts. Used to seed mutation operators, so every mutation is traceable to a verifiable entropy source rather than a pseudo-random generator.

---

## 3. Naming note (read before publishing)

"Darwinian" is appropriate — the 2018 work is explicitly framed around Darwin's evolution. But avoid the exact phrase **"Quantum Darwinism"**: that already denotes Zurek's theory of how classical objectivity emerges from redundant environmental encoding (einselection), which is a *different* subject. Use "quantum Darwinian evolution," "quantum artificial life," or "quantum evolutionary computation" to prevent confusion with reviewers.

---

## 4. Maturity ledger (what's real vs. proposed)

Keeping these honestly separated is what will make the project credible.

**Demonstrated in prior published work:**
- Self-replication, mutation, interaction, death on a quantum computer (small scale).
- Entanglement inherited across a few generations.

**Engineering-ready today (available on current IBM hardware):**
- Mid-circuit measurement and conditional feed-forward (dynamic circuits, Qiskit Runtime).
- Approximate quantum cloning for the replication step.
- Certified QRNG-driven mutation (Q-EaaS).
- Long-range entangling operations in constant *circuit depth* via ancilla + measurement + feed-forward (see §6.4 for the honest caveats).

**Proposed / speculative (the research contribution):**
- Scaling the population well beyond a handful of qubits while keeping inherited entanglement meaningful.
- A rigorous, reproducible demonstration that entangled genealogies evolve in a way a defined classical surrogate cannot match.

---

## 5. The individual: genotype and phenotype

Following the biomimetic model, each individual is a small register:

- **Genotype qubit(s):** the heritable state, e.g. a single-qubit state parameterized by an angle. This is what gets passed on.
- **Phenotype qubit(s):** derived from the genotype through an interaction with an ancilla; its expectation value plays the role of an observable "trait" and encodes the individual's expected lifetime.

Genotype → phenotype is a fixed map; reproduction copies (approximately) the genotype, not the phenotype — mirroring biology, where offspring inherit genes, not acquired traits.

---

## 6. Operators

### 6.1 Self-replication (respecting no-cloning)
Exact copying of an unknown genotype is forbidden by the no-cloning theorem. Replication is therefore an **approximate quantum cloning** step: the parent genotype interacts (via a fixed entangling unitary) with a fresh ancilla so that the ancilla ends up carrying a partial copy — enough for expectation values of the trait to be inherited, not a perfect duplicate. This is the same route the 2018 experiment used, and it is a feature, not a bug: imperfect copying is where variation enters.

### 6.2 Mutation
A single-qubit rotation of small random angle applied to the offspring genotype. The angle is drawn from **Q-EaaS certified entropy**, so mutation is (a) genuinely random and (b) auditable via the provenance receipt. Mutation rate is a tunable parameter of the run.

### 6.3 Interaction between individuals
A two-qubit gate between two individuals' genotypes/phenotypes, letting the state of one influence another — the substrate for competition/cooperation dynamics. This is where non-local connectivity matters, because interacting individuals may live on physically distant qubits.

### 6.4 Non-local interaction via teleported gates — honest version
To let distant individuals interact without long SWAP chains, use entanglement-assisted / measurement-based gate teleportation. The accurate framing:

- A long-range entangling gate **can** be applied in *constant circuit depth* using an ancilla chain plus mid-circuit measurement and classical feed-forward.
- This is **not free**: it trades depth for **width** (extra ancilla qubits) and for **classical feed-forward latency**, and the entangling resource still has to be created (on a monolithic chip, preparing the Bell/GHZ resource itself consumes two-qubit gates across the same limited connectivity).
- So the correct claim is *"constant-depth long-range interaction at the cost of ancillas and classical latency,"* **not** "instant, free bypass of the bottleneck." The real payoff is keeping genealogies coherent across **deeper** generational circuits than a SWAP-based routing would allow.

### 6.5 Death
Selection is explicit and measured: a mid-circuit measurement of the phenotype (the "lifetime" observable) determines survival; individuals below threshold are reset/removed via conditional feed-forward. Because this is a real measurement, there is no pretense of free superposition-wide selection — each generation is sampled, and statistics are built over many shots and runs.

---

## 7. The evolutionary loop

1. **Seed** an initial population of individuals (genotype + phenotype registers).
2. **Express** phenotypes from genotypes.
3. **Interact** selected pairs (local gates where adjacent; teleported gates where distant, §6.4).
4. **Select / die**: mid-circuit measure phenotype lifetimes; cull below threshold via feed-forward.
5. **Replicate**: survivors undergo approximate cloning into fresh ancillas → offspring genotypes.
6. **Mutate**: apply Q-EaaS-seeded rotations to offspring.
7. **Record lineage**: log the parent→offspring edge as a new branch of the Quantum Tree, tagged with the entanglement diagnostics of that generation.
8. Repeat for as many generations as coherence budget allows; export the genealogy.

The Quantum Tree is the output of steps 5–7: the lineage network *is* the tree, grown by selection rather than by passive branching.

---

## 8. The core falsifiable experiment

This is the scientific spine — the one clean, hard-to-argue-with result the whole project should aim at.

**Question:** Does inherited entanglement across generations make the population's evolution reproducibly harder for a classical surrogate to reproduce than an equivalent non-entangled process?

**Quantum arm:** Run the loop with genuine hardware entanglement preserved across generations (teleported interactions, coherent replication).

**Classical surrogate (control) — define it precisely so the comparison is fair:**
- Same population size, same generation count, same mutation rate/schedule, same selection thresholds, same random seeds from the *same* Q-EaaS stream.
- Replace every coherent inheritance/interaction with a **measure-and-resend** step: measure the parent's trait, send classical bits, re-prepare a separable state from those bits.
- This produces a fully separable, classically-simulable analog of the identical evolutionary schedule.

**Observable to compare:** a chosen population statistic that is sensitive to inherited correlations — e.g. cross-generational correlation of phenotype observables, or a multi-individual entanglement witness / genealogical correlation metric — as a function of generation number.

**Outcomes:**
- **Positive result:** the quantum arm shows correlations the matched classical surrogate provably cannot reproduce, and the gap survives realistic noise. Publishable.
- **Negative result:** noise washes out the difference and the surrogate matches within error bars. **This is still valuable** — it quantifies exactly how much coherence current hardware can carry through a genealogy, which nobody has cleanly measured.

Either way you get a defensible number, which is worth far more than a broad framing.

---

## 9. Metrics & success criteria

- **Fidelity vs. ideal model** per generation (the 2018 work reported close agreement at small scale — reproduce that first).
- **Inherited-correlation / entanglement metric** vs. generation, quantum arm vs. classical surrogate.
- **Coherence depth:** maximum number of generations before the quantum/classical gap closes to within error.
- **Population scale reached** at fixed gap significance.
- **Entropy provenance:** every mutation traceable to a signed Q-EaaS receipt.

**Falsification condition:** if, at every accessible scale and generation count, the classical surrogate reproduces the chosen metric within statistical error, the "entanglement makes evolution classically-inimitable on this hardware" claim is falsified for the current generation of devices — report it as such.

---

## 10. Scaling plan (be realistic about 102 qubits)

- **Stage 0 — Reproduce.** Rebuild the 2018 single-lineage result on current hardware. Confirms the toolchain.
- **Stage 1 — Population.** A handful of individuals over a few generations with explicit measured selection.
- **Stage 2 — Genealogy.** Wire lineage logging into the Quantum Tree; add the classical surrogate and run the §8 comparison at small scale.
- **Stage 3 — Non-local.** Introduce teleported interactions (§6.4) to extend generational depth.
- **Stage 4 — Scale-out.** Push population/qubit count upward (tens → ~102) *only as coherence allows.*

Honest caveat on 102 qubits: each individual, its ancillae, and each generation consume qubits and depth quickly, and NISQ noise attacks precisely the inherited entanglement the experiment depends on. "102 qubits" should be a ceiling to grow toward while measuring where the signal dies — not an assumed starting point. The interesting result may well appear at far fewer qubits.

---

## 11. Risks & open questions

- **Noise-limited genealogies:** inherited entanglement is fragile; the coherent-generation budget may be very small on today's devices.
- **Metric choice:** the entanglement/correlation metric must be both hardware-estimable (few measurement settings) and genuinely classically-hard to fake — these pull in opposite directions.
- **Teleportation overhead:** ancilla cost and classical-latency of feed-forward may erase the depth savings in practice; needs benchmarking, not assumption.
- **Selection semantics:** measured selection is honest but sample-inefficient; many shots per generation are required for stable statistics.
- **Interpretation:** "no classical device can predict this evolution" is a strong claim; the §8 surrogate is what turns it from a slogan into a measurement.

---

## 12. References

1. U. Alvarez-Rodriguez, M. Sanz, L. Lamata, E. Solano. *Quantum Artificial Life in an IBM Quantum Computer.* Scientific Reports 8, 14793 (2018). DOI: 10.1038/s41598-018-33125-3 · arXiv:1711.09442.
2. Wikipedia: *Quantum artificial life.*
3. D. Gottesman, I. L. Chuang. *Demonstrating the viability of universal quantum computation using teleportation and single-qubit operations.* Nature 402, 390 (1999). (Gate teleportation.)
4. No-cloning theorem; approximate quantum cloning (background for §6.1).
5. W. H. Zurek. *Quantum Darwinism.* Nature Physics 5, 181 (2009). (Cited only to disambiguate the name — see §3.)
6. Project pages: Quantum Tree, Q-EaaS — https://peterjas.sk/

---

*Version 2.0 — Living Genealogies. Supersedes the earlier "noise-as-fitness" QDEP draft.*
