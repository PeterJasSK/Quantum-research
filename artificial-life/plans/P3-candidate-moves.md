# P3 — Candidate moves (the "potential moves" menu)

**Owning epic:** `plans/epic-qalife-darwinian-richness.md` (§9 P3) · **Stage:** P3 (late-stage, exploratory)
**Status:** **Candidate menu — nothing here is locked.** Ideas to be *evaluated*, not a build spec.
**Opened:** 2026-09-09 · **Author:** Claude (Opus), from developer brainstorming.

> **What this file is.** P3 is deliberately exploratory (epic §9: "this is what we explore, not a
> rigid spec"). This is the running list of *potential* richness investigations — each written up
> enough to judge, honestly costed against the quantum signature, and marked **not started**. When
> the P2 decision gate (AC-P2.4) opens, we pick from here on P2 evidence; entries can be dropped,
> merged, or reshaped. Add freely; commit to nothing until the gate.

> **The rule every entry is judged by (CD-3/CD-4).** The witness `⟨X^⊗W⟩` is the *only* quantum
> claim. Any biology that a classical agent-sim reproduces (competition counts, who-survives,
> population size) is **plumbing dressed as life** — it can enrich the demo but adds no quantum
> content, and usually *costs* witness. So each move is scored on two axes, kept separate:
> **(1) biological richness** added, and **(2) witness survival** — the W/G at which the certified
> signature crosses into classical (measured against `research/baseline_P1/`). The result of P3 is
> that trade-off curve, not "the most alive-looking demo." A move that kills the witness is not a
> failure — *where* and *why* it dies is the datapoint (AC-P3.2).

## How to read each entry

- **Idea** — the biological process, in plain terms.
- **Encoding** — how it maps to gates/qubits (grounded in `code/qalife.py` where primitives exist).
- **Quantum vs classical (honesty)** — what part carries a real witness claim vs what's diagonal plumbing.
- **Expected witness cost** — best honest guess at how hard it bites the signature on Heron-r2, and why.
- **Measured against** — the baseline/observable it's scored on.
- **Prereqs / status** — what must land first; always starts **NOT STARTED — candidate**.

---

## M1 — Adaptive measured selection (`death_mode='selection'`)

*The epic's best-specified entry point (QDEP §6.5) — listed here for completeness; already named in epic §9.*

- **Idea.** Replace scripted aging (`age = steps − k`) with **earned** survival: mid-circuit measure
  the phenotype ("lifetime" observable); individuals below threshold are reset/removed via conditional
  feed-forward. Death becomes a fitness verdict, not a birth-order script.
- **Encoding.** New `death_mode='selection'` plug-in operator on the model file (CD-1): `qc.measure`
  the phenotype qubit mid-circuit, `with qc.if_test(...)` → `reset`/`X` the individual. Reuses the
  dynamic-circuit / feed-forward pattern already in the file (`_teleport_cx`, :121).
- **Quantum vs classical.** The selection *decision* is classical (a threshold on a measured value).
  The quantum claim stays the genotype-line witness. Selection's interest is that it perturbs the
  GHZ via measurement back-action.
- **Expected witness cost.** **Heavy.** Mid-circuit measurement is the dominant error channel on this
  chip (it is why teleport-routing lost twice). The witness is expected to bite hard — *that bite is
  the measurement, not a bug* (epic §6). Report against `kept_fraction`.
- **Measured against.** `baseline_P1` ideal + hardware witness vs W/G, k=2/k=3 gate.
- **Prereqs / status.** P2 gate open. **NOT STARTED — candidate (highest-specified).**

## M2 — Energy-transfer competition ("the strong eat the weak")

- **Idea.** Two lineages that meet **fight over a shared resource**: the weaker (more aged, closer to
  the `|0⟩` dark state = less excitation) loses; the stronger absorbs its "energy" to keep replicating.
  Carrying-capacity dynamics — winner monopolizes or the two coexist below a resource ceiling.
- **Encoding.** "Energy" = qubit excitation (amplitude). Aging already leaks excitation to a bath
  (`apply_aging_damping`, :86). Model the fight as a **controlled amplitude transfer** between the two
  competitors' phenotype (or a resource-ancilla) qubits — a partial-SWAP / beam-splitter gate
  `√SWAP`-like coupling that moves amplitude from the low-excitation (weak) qubit into the high one.
  Optionally gate it on a measured fitness readout (→ merges with M1).
- **Quantum vs classical.** ⚠ **This is where the honesty knife falls.** Resource competition,
  who-wins, population bookkeeping = **pure classical Darwinism** (a laptop Lotka-Volterra sim does it
  trivially). It makes the life far more *complete* but adds **zero** quantum content on its own. The
  only way it earns a quantum claim is if the *coherent* amplitude exchange keeps the competitors
  entangled — i.e. the fight leaves an off-diagonal signature the witness can see. Whether it does is
  the open question; default expectation is it mostly shows up diagonally (classical).
- **Expected witness cost.** Medium-heavy if the transfer is coherent (extra 2q coupling + possible
  feed-forward); severe if it needs mid-circuit measurement to decide the winner.
- **Measured against.** Witness vs separable null at matched W/G, plus a classical-surrogate check
  (CD-4): if a matched classical energy-competition sim reproduces the population outcome within kσ,
  the population dynamics are declared plumbing and only any residual witness carries the claim.
- **Prereqs / status.** Needs M3 (multiple lineages) to have opponents. **NOT STARTED — candidate.**

## M3 — Multiple competing lineages (break the single line)

- **Idea.** Today the population is **one** line (`k` = child of `k−1`) → one GHZ. Real selection needs
  **several** lineages that coexist and compete: multiple founders, each seeding its own genealogy;
  only one survives, or several coexist, by Darwinian rules.
- **Encoding.** Multiple founder `Ry(π/2)` seeds → several independent CNOT-clone trees (several GHZs)
  laid on disjoint qubit blocks. Spatial/2D topology from the epic menu (§9). Each tree measured with
  its own per-lineage witness; competition operators (M2/M4) couple them.
- **Quantum vs classical.** Per-lineage witness = genuine quantum claim per tree. *Which* lineage wins
  = classical. Interesting quantum question: does inter-lineage coupling create entanglement *between*
  trees (a joint witness across lineages), or just classical correlation?
- **Expected witness cost.** Neutral for isolated trees (just more qubits — scale is cheap, epic §6);
  the cost comes from whatever coupling M2/M4 adds.
- **Measured against.** Per-lineage witness vs baseline; optional cross-lineage joint witness.
- **Prereqs / status.** Enables M2 and M4. **NOT STARTED — candidate (structural prereq).**

## M4 — Teleport-routed inter-lineage fight (SWAP-vs-teleport, under the witness)

- **Idea.** Lineages that "meet" needn't be physical neighbours on the chip — realize the competition
  interaction between **distant** trees via a **teleported gate** so they fight at constant circuit
  depth instead of a long SWAP ladder. Optionally let **QRNG choose the fight-partners** (certified
  stochastic mating/competition, CD-6).
- **Encoding.** Primitives already in the model (CD-10): `_teleport_cx` (:121), `apply_interaction_
  teleport` (:142) — a SWAP as 3 teleported CNOTs over a shared corridor (`+2 ancillas/bond`, a `tel`
  feed-forward register). A/B it against the plain SWAP ladder `_swap_cx` (:111). QRNG picks the bond
  graph — **fixed per circuit**, not per shot (else the witness average is ill-defined).
- **Quantum vs classical.** The routing choice is a hardware-efficiency question, not a new biology.
  The claim is still the witness; this move asks *which routing preserves it better at scale*.
- **Expected witness cost.** **Probably a loss on 2026 hardware — honestly.** Teleport trades
  SWAP-depth for **mid-circuit measurement + feed-forward**, the worst channel on Heron-r2; teleport-
  routing is **already refuted twice** on this chip (readout err ≫ 2q err → the advantage inverts). BUT
  both refutations were on the *old diagonal C(g) metric*; **under the witness it is untested** — and
  the epic P3 menu lists exactly this ("teleport-vs-SWAP re-examined under the witness observable",
  §9). Prediction: teleport loses; *where and by how much* is the datapoint; flips to a win only if a
  future chip gets cheap mid-circuit measurement. Not "not physically connected" — still needs a
  pre-shared Bell pair (physically distributed) + classical wires; it saves *data-qubit routing*, and
  costs *more* qubits, not fewer.
- **Measured against.** Witness vs W at matched biology, SWAP arm vs teleport arm, reported with
  `kept_fraction` and depth.
- **Prereqs / status.** Needs M3 (distant lineages to route between). **NOT STARTED — candidate.**

## M5 — QRNG-driven stochastic biology (cheap add-on)

- **Idea.** Use the certified QRNG stream (already the mutation source, CD-6) to also drive *which*
  individuals interact, mutate hardest, or are selected — genuine environmental stochasticity with a
  certified-entropy receipt, not a PRNG stand-in.
- **Encoding.** Draw control-flow choices (partner graph, mutation targets) from `qrng_client.py` at
  circuit-build time. Record provenance per run (the deferred `meta.entropy_provenance` field, epic §4).
- **Quantum vs classical.** The randomness *source* is certified-quantum (a provenance claim, not a
  computational-advantage claim). Does **not** by itself touch the witness — it's a control choice.
- **Expected witness cost.** ~None directly; cost lives in whatever operator it gates (M1/M2/M4).
- **Measured against.** N/A for the witness; scored on provenance completeness (CD-6) + entropy receipt.
- **Prereqs / status.** Trivial to bolt onto any move; **NOT STARTED — candidate (enabler).**

## M6 — Quantum-random environment (external conditions that affect survival)

- **Idea.** Selection isn't only internal (age, fights) — the **world** presses on the population. Add
  an **environment**: fluctuating conditions (resource abundance, hazard/harshness, "temperature")
  drawn from the certified QRNG stream that modulate who survives. A harsh draw culls the weak harder;
  a rich draw lets more coexist. Carrying capacity becomes environment-dependent, not fixed. Ties the
  whole thing to a changing world instead of a static script.
- **Encoding.** Two flavours, keep them distinct:
  - **(a) Environment as a classical control field** — QRNG draws a per-generation (or per-region)
    parameter that sets the aging rate `gamma`/`delta`, the `ALIVE_THRESH`, or a resource-bath fill
    level; those feed the existing death operators (`apply_aging_damping`, :86). Cheap, no extra
    coherent qubits. Environment **fixed per circuit** (drawn once, held across the 8192 shots) — a
    per-shot-random world makes the witness average ill-defined (same caveat as M4).
  - **(b) Environment as a quantum bath register** — a shared environment ancilla block the population
    couples to (beyond the single damping bath), carrying its own state. System–environment coupling.
- **Quantum vs classical (honesty).** ⚠ **Flavour (a) is pure classical selection pressure** — a laptop
  applies a fluctuating death rate trivially; the QRNG only buys a *provenance* claim on the world's
  randomness (like M5), **not** quantum content. Flavour (b) is the only quantum-interesting version,
  and it cuts the wrong way: **coupling the population to an environment is literally the decoherence
  channel.** Environment = the thing that measures/damps the system = the witness's executioner. The
  one subtle upside: if system+environment stay jointly coherent, an *extended* witness across
  system+bath could survive where the reduced-system witness dies — worth a look, low odds on this chip.
- **Expected witness cost.** **(a):** none directly (it's diagonal); cost lives in the death operator it
  tunes. **(b):** **severe and monotone** — more environment coupling → more damping → faster witness
  death. Honest prior: environment is a signature-killer; the value is charting *how fast* different
  environmental regimes extinguish it.
- **Measured against.** Witness vs separable null across QRNG-drawn environmental regimes (e.g. sweep
  harshness), each vs `baseline_P1`; plus a classical-surrogate check — if a matched classical
  fluctuating-death sim reproduces the survival statistics within kσ, the environment is declared
  plumbing (CD-4) and only any residual/extended witness carries the claim. Record the QRNG receipt
  per regime (CD-6, the deferred `meta.entropy_provenance`).
- **Prereqs / status.** Pairs with M2 (resource competition) and M3 (multiple lineages under one
  shared world); M5 supplies the certified entropy. **NOT STARTED — candidate.**

---

## Evaluation checklist (apply to any move before it graduates from candidate → P3 plan)

1. **Two-axis score stated?** biological richness added AND witness-survival cost, kept separate.
2. **Classical surrogate identified?** what a laptop reproduces (the plumbing) vs the residual witness claim (CD-4).
3. **Measured against `baseline_P1`?** ideal + hardware witness vs separable null at matched W/G, k=2/k=3.
4. **Plug-in, not a fork?** implemented on the model file as an operator/topology (CD-1); `--selftest` coverage where a closed form exists.
5. **Honest expected outcome recorded** *before* running — including "expected to kill the witness, and that's the datapoint."
6. **Fits the P4 phase diagram?** yields a richness-vs-survival point (AC-P4.1) and, if it earns a headline, an honest scale/certification framing (AC-P4.3) — never a speedup claim.

## Combination sketch (the developer's full vision, for reference — NOT committed)

M3 (multiple lineages) + M2 (energy-transfer competition) + M4 (teleport-routed, QRNG-chosen fights)
+ M1 (measured selection) + M6 (quantum-random environment pressing on all of them) → *"multiple
quantum organisms competing over energy under a fluctuating world, weaker consumed by stronger,
ending in coexistence or a monopoly, shown in a web demo (P4, AC-P4.3)."* Honest headline if
built: **"the most complete Darwinian quantum life that still carries a certified witness on 2026
hardware — and the exact boundary where each added process (competition, selection, long-range fight)
extinguishes the signature."** The demo shows the **frontier**, not a miracle. Expect the witness to be
low or dead once all four stack — that collapse *is* the finding.


## Ideas that are in the original rersearch paper to improve the QC artificial life  DO NOT CHANGE THIS IS SOURCE OF THROUGHT
## link to the paper  https://pmc.ncbi.nlm.nih.gov/articles/PMC6172259/#Abs1
## link to wiki https://en.wikipedia.org/wiki/Quantum_artificial_life

Regarding the emergence of complexity, the route towards the scalability of our quantum algorithm is intrinsically
related to the inclusion of more degrees of freedom in the description of quantum living units. 
These may be introduced by simply increasing the number of qubits, and making them part of the updated genotype and phenotype.
A part of the dynamics would be adapted by repeating the partial cloning processes and extending the dissipation to the new phenotype qubits. 
Another part of the dynamics would deal with the properties introduced by the new degrees of freedom. 
In the same way as the genotype in the current model rules the individual-environment and inter-individual interactions, 
additional observables in the genotype would enable the exploration of more characteristics: different self-replication rates, 
independent lifetime and interaction role, or capacity to displace along the associated Hilbert space, all of them encoded in the genotype. 
An alternative is to encode the information in quantum states of higher dimensions. 
The general result of partial quantum cloning to qudits of any dimension makes this family of hypothetical models feasible, 
conditional to the availability of high dimensional entangling operations.

A different question is the scalability of the current model without including any modification. 
Notice that, in our protocol, the information about the lifetime and the predator-prey character 
is classical and encoded in the mean value 〈σz〉 of the phenotype and the genotype of the individual, respectively. 
Therefore, this partial dynamics can be predicted with a simpler classical analogue. However, 
the full quantum description of our protocol allows one to retrieve the connections between the quantum living units, 
linked through entanglement, which is a useful complement that is absent in the classical analogue. 
In other words, the extra free parameters available in the superposition and entanglement of quantum states are used for describing questions regarding the collective dynamics of individuals, and this is precisely the new source of complex behavior our algorithm is able to create. In this sense, the complexity of our quantum algorithm may only be reached by a larger quantum computer, currently being built in academic institutions and companies. This might yield unexpectedly interesting outcomes but, at the same time, will increase the sensitivity to decoherence during the self-replication process.

This experimental realization of the proposed quantum algorithm represents the consolidation of the theoretical 
framework of quantum artificial life. The improvement in scalable quantum computers will soon allow us for more accurate 
quantum emulations with growing complexity towards quantum supremacy, even considering spatial variables for the individuals 
and a mechanism for tracing out death living units. These future developments should lead towards an autonomous character of the set of individuals, 
i.e., the evolution will be an intrinsic property of the system, and the desired behavior will emerge without following the instructions 
of a previously designed quantum algorithm. In this context, the system would be transformed into an intelligent source of quantum complexity 
whose evolutionary plot for a large number of individuals may not be predicted classically and, consequently, 
has the capacity to produce unexpected results when scaled up. An interesting question to address is to establish the relation existing 
between the parameters defining the fundamental processes of the model, and the emergent multiqubit quantum state. Along these lines, 
and following the frame of artificial life oriented genetic algorithms37, we speculate about the idea of channeling this complexity 
to encode optimization problems by tuning the self-replication, mutation and dissipation rates that define the evolution. Furthermore, 
recent advances in quantum machine learning constitute a promising material to work with in the study of algorithms combining the properties of both fields,
pursuing the design of intelligent and replicating quantum agents. Therefore, the creation of these quantum living units and their possible 
applications are expected to have deep implications in the community of quantum simulation and quantum computing in a variety of quantum platforms.

All in all, the experiments presented here entail the validation of quantum artificial life in the lab and, in particular,
in cloud quantum computers as that of IBM. Still another interesting step would be the development of autonomous quantum devices following the 
theoretical and experimental results in quantum cellular automata38–42. Our quantum individuals are driven by an adaptation effort along the 
lines of a quantum Darwinian evolution, which effectively transfer the quantum information through generations of larger multiqubit entangled states. 
We believe that the presented results and vision, both in theory and experiments, should hoist this innovative research line as one of the leading 
banners in the future of quantum technologies.