# Critical Quantum Life — the leap: ranked candidate directions
**AI CHAT claude --resume cb55c4e5-2545-4267-a2b7-8748630e3ac0**

**Purpose.** Turn CriticalQuantumLife from "another quantum-artificial-life demo" into a result with a real-world use case that is a genuine generational leap. This doc collects the literature findings, ranks eight candidate directions against explicit criteria, and gives a concrete "how to improve" for each. It is decision input for F7 (thesis framing) and any F8+ build.

Date: 2026-08-31. Author-facing strategy note; numbers below are from the Run-1 hardware result (`plans/F5-runlog.md`, `research_runs/cql_f5_report.json`) and the cited literature.

---

## 0. TL;DR

> **DECISION (see §9): build the "Quantum Canary" — an entanglement-native, always-on QPU health monitor.** It is the only direction that is shippable now, needs no unmet gate (it uses the witness that *passed* and treats σ=0.44 homeostasis as a feature), has no prior art, has a real buyer (quantum-cloud ops), and reuses the whole engine + spectacle. The science lanes below stay open for later; the Canary is the foundation they sit on.


- **Recommended thesis (#1):** reframe the whole apparatus as a **certified, self-organizing test of whether the "edge-of-chaos" advantage in quantum reservoir computing (QRC) is genuinely quantum or merely classical feedback instability** — a question the field's own leaders (Kobayashi & Motome, *PRL* 2025) explicitly flagged as open. CriticalQuantumLife is the *only* apparatus that can answer it, because it already has the three instruments the decomposition requires: a closed feedback loop (reaches the edge), a **yoked control** (isolates the classical-feedback edge), and an **entanglement witness with no classical surrogate** (certifies the quantum edge).
- **Its product face (#2):** the same machinery is the **first quantum self-organized-critical reservoir** — one that auto-tunes to its own edge of chaos instead of being hand-tuned per chip per calibration. That is a recognized, unsolved pain in a market that is actively commercializing (QCi is selling reservoir computers now).
- **Safest high-defensibility thesis (#3):** a **"quantum DishBrain"** — the first experimental active-inference / self-organized-criticality testbed on a *fully observable* quantum substrate. Honest even if it never beats classical, because the contribution is the instrument, not a speed claim.
- **Kill:** the "certified-quantum randomness/liveness beacon" idea. An entanglement witness is not cryptographic proof-of-quantumness; certified randomness needs a *classically hard* sampling task (RCS + XEB, certified on Frontier). The witness `⟨X^⊗W⟩` for a GHZ is trivially classical to predict. Do not ship this claim.

---

## 1. What counts as a "leap" here (scoring criteria)

Every quantum-artificial-life result to date — the 2018 origin, QuantumLife (spatial C(d)), artificial-life (genealogical witness, W=24), and CriticalQuantumLife so far — is honest but ends at "cool behavior on a QPU." A leap must **do a job** a real user would pay for or a field genuinely needs. Candidates are scored on:

| Dimension | Weight | Question |
|---|---|---|
| Novelty | 25% | Is the intersection empty in the literature? |
| Real-world teeth | 25% | Is there a user/market/decision that changes? |
| Defensibility | 20% | Honest under review; survives without a speed claim you can't make |
| Feasibility (current assets) | 20% | Buildable from the existing engine + one QC allocation |
| Apparatus fit | 10% | Does the existing closed-loop/yoked/witness rig map directly? |

---

## 2. Literature landscape (what exists, what is empty)

**Quantum reservoir computing (QRC) — hot, hardware-real, commercializing.**
- Optimal QRC performance sits at the **edge of many-body quantum chaos** — diagnosed by the spectral form factor (SFF) ramp-plateau and RMT level-spacing ratio; shown for SYK4 (chaotic) vs SYK2 (integrable); performance peaks at the chaotic boundary, but only for sufficiently long input intervals Δt_in. (Kobayashi & Motome, *PRL* 2025, arXiv:2506.17547.)
- **Feedback-driven QRC** re-injects single-qubit measurement outcomes `⟨Z_i⟩_k` to restore fading memory; three phases by feedback strength a_fb — stable/confined, an intermediate peak, and unstable limit-cycle where memory capacity `C_Σ → 0`. Hardware-efficient shallow entanglers with **l ≈ 7–10 layers** match Haar-random expressivity; **l = 1 underperforms**. (Kobayashi, Fujii et al., arXiv:2406.15783.)
- **The open question this thesis targets:** the same authors state the earlier feedback-QRC edge peak *"appears predominantly due to classical instabilities in feedback connections, rather than intrinsically quantum phenomena,"* while Martínez-Peña et al. found a genuinely quantum peak near the ergodic–localization transition. **Whether the edge advantage is classical or quantum is unsettled.**
- **Role of entanglement:** not strictly necessary (separable-state reservoirs work), but **optimal performance occurs at moderate, non-zero entanglement** (Kerr-oscillator QRC, arXiv:2508.11175). So entanglement is a *tuning knob*, not a binary — exactly what a certified, controllable witness is for.
- **Hardware QRC is established:** NARMA on IBM devices, repeated-measurement QRC on superconducting hardware, gate-based multivariate forecasting on NISQ (arXiv:2510.13634), non-unital noise as a resource (arXiv:2409.07886).
- **Commercial reality:** Quantum Computing Inc. sells reservoir computers (EmuCore shipped to a major automaker; photonic Neurawave at SC25; $750M financing). McKinsey calls 2026 a "commercial tipping point." The market for "reservoir computing that works and is trustworthy" is live.

**Self-organized criticality (SOC) / self-tuning to the edge — proven classically, empty quantum.**
- Classical self-tuning to criticality is established and valuable: P-CRITICAL (local unsupervised reservoir auto-tuning), synaptic-plasticity self-tuning critical networks, E-I-balance self-adaptation with up to **+130% memory-capacity gains**; autonomous systems reach steady states that beat any hand-tuned dynamics ("edge of ergodicity breaking," arXiv:2604.15669).
- **No prior work does this for a quantum reservoir.** The quantum self-organized-critical reservoir is an empty gap.

**Certified randomness — real but requires classical hardness (rules out the beacon idea).**
- Certified quantum randomness (Quantinuum/JPMorgan/ORNL/ANL/UT-Austin, *Nature* 2025, s41586-025-08737-1): Random Circuit Sampling + cross-entropy benchmarking, **71,313 certified bits**, certified against Frontier-scale classical compute. The certificate rests on the *classical intractability* of the sampling task. An entanglement witness is not that.

**Entanglement-depth benchmarking — crowded.**
- GHZ-prep metric ("largest genuine multipartite GHZ"), entanglement-based volumetric benchmark (arXiv:2209.00678), EU Quantum Flagship KPIs (arXiv:2512.19653), entanglement characterized on up to 414 qubits, 32-qubit GHZ at mitigated fidelity 0.519 on IBM Eagle. A "genealogical entanglement depth" is at best an incremental variant.

**Quantum metrology with GHZ — crowded, strong incumbents.**
- GHZ is *the* canonical entanglement-enhanced sensing resource; adaptive Bayesian GHZ atomic clocks; variational GHZ sensing (VISTA, "GHZ is all you need," arXiv:2605.04203). Darwinian self-tuning adds little over existing variational optimization.

**Quantum active inference / free-energy — theory exists, no experiment.**
- FEP formalized for generic quantum systems (Fields & Friston, arXiv:2112.15242); DishBrain is the biological proof that closed-loop free-energy minimization produces learning (Kagan et al. 2022). No experimental *quantum* DishBrain exists.

**Quantum open-ended evolution — empty, speculative.**
- Rich classical field (novelty search, quality-diversity, Lenia, foundation-model-guided ALife, arXiv:2412.17799). "No substantial recent work combines quantum computing with open-ended evolution." High novelty, low near-term feasibility.

---

## 3. Ranked candidates

Weighted score out of 5.0. Higher is better.

| # | Direction | Novelty | Teeth | Defens. | Feas. | Fit | **Score** |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **1** | **Certified classical-vs-quantum *edge* decomposition in QRC** | 5 | 4 | 5 | 4 | 5 | **4.55** |
| **2** | **Self-tuning quantum SOC reservoir (auto-calibration)** | 5 | 5 | 4 | 3 | 4 | **4.25** |
| **3** | **Quantum DishBrain (active-inference / criticality testbed)** | 4 | 3 | 5 | 5 | 5 | **4.20** |
| 4 | Genealogical / dynamic-circuit entanglement-depth benchmark | 2 | 3 | 4 | 5 | 4 | 3.30 |
| 5 | Evolved error mitigation / DFS discovery (moonshot) | 5 | 5 | 2 | 1 | 3 | 3.20 |
| 6 | Quantum open-ended evolution / novelty search (moonshot) | 5 | 2 | 2 | 1 | 3 | 2.75 |
| 7 | Adaptive GHZ quantum metrology / self-calibrating sensor | 2 | 4 | 3 | 2 | 3 | 2.75 |
| ✗ | Certified-quantum randomness / liveness beacon | — | — | 1 | — | — | **REJECT** |

Candidates 1 and 2 share one apparatus and one build: **do #1 and #2 falls out for free.** #3 is the fallback if the QC allocation is too small to reach the edge — it needs no speed claim.

---

## 4. Candidate detail + how to improve

### #1 — Certified classical-vs-quantum *edge* decomposition in QRC  ★ recommended flagship

**Claim (one line).** A certified, self-organizing test on real quantum hardware of whether the edge-of-chaos advantage in QRC is genuinely quantum — separating the classical-feedback edge (isolated by the yoked control) from the entanglement-certified quantum edge (`⟨X^⊗W⟩` above a classical null).

**Why it's a leap.** It answers a live, contested question posed by the field's own leaders, and CriticalQuantumLife is the only rig with all three needed instruments (closed loop / yoked / witness) on real hardware. Everyone else hand-tunes on simulators and argues interpretation.

**Experiment.** Drive the environment with standard temporal benchmarks (short-term memory capacity `C_Σ = Σ_d R²_d`, d_max=25; and NARMA-n). Produce three curves:
1. **Edge peak on hardware** — capacity peaks as the loop self-tunes toward σ≈1 (first *self-organized* version of the hand-tuned result).
2. **Contingency test** — closed-loop peak survives; yoked peak does not (or differs) → quantifies the *classical-feedback* share.
3. **Certification knockout** — capacity tracks the certified witness; decohere the entanglement (measure-and-resend / damping) and the edge peak collapses to the classical floor → quantifies the *quantum* share.

**How to improve / de-risk.**
- Compute the field's own edge diagnostics — **spectral form factor + level-spacing ratio** — alongside branching σ, so results are directly comparable to arXiv:2506.17547.
- Report capacity with the field's metric (`C_Σ`, NARMA-NRMSE), not a bespoke surprise proxy, so reviewers can place it.
- Pre-register the decomposition (classical share + quantum share = total edge advantage) so a null result is still publishable.

**Verdict.** Highest score. This is the thesis.

### #2 — Self-tuning quantum SOC reservoir (auto-calibration)  ★ product face of #1

**Claim.** The first quantum reservoir that self-organizes to its own edge of chaos, instead of being hand-tuned per chip and per calibration drift.

**Why it's a leap + teeth.** Tuning a reservoir to the edge "relies on costly trial-and-error" (acknowledged pain); classical self-tuning gives +130% capacity but no quantum version exists; and reservoir computing is commercializing now (QCi). A reservoir that finds its own optimal regime is the deployable version — and the same yoked+witness protocol becomes a **QRC certification/audit**: "prove your quantum reservoir's advantage is quantum, not classical feedback in a quantum costume." As QRC is sold, that audit is a real need.

**How to improve.**
- Frame the free-energy/Darwinian loop explicitly as the auto-tuner; show it converges to the σ≈1 set-point from both the frozen and chaotic sides (robustness).
- Demonstrate re-tuning after induced drift (change device calibration / inject noise) — the deployable story.

**Verdict.** Do #1's experiment; this is its applied narrative. Package as a second paper or the thesis's "impact" chapter.

### #3 — Quantum DishBrain (active-inference / criticality testbed)  ★ safest defensible thesis

**Claim.** The first experimental realization of active inference / self-organized criticality on a *fully observable* quantum substrate — a clean testbed for theories (FEP, SOC, edge-of-chaos) that biology can only probe indirectly.

**Why it's defensible.** The contribution is the instrument and the measurement, not a speed advantage — so it survives even if quantum never beats classical here. FEP↔quantum is already formalized (arXiv:2112.15242); DishBrain proved the biological case; nobody has built the quantum analog. Uses the existing apparatus as-is.

**How to improve.**
- Lead with what a QPU gives that neurons can't: full state tomography / exact observables / a perfect yoked control — turn "fully observable substrate" into concrete measurements biology cannot make.
- Keep the three honesty gates as the paper's spine.

**Verdict.** Best fallback; lower market teeth, highest safety. If the QC budget can't reach the edge for #1, pivot here without wasted work.

### #4 — Genealogical / dynamic-circuit entanglement-depth benchmark

**Claim.** A single unforgeable number per chip — generations of entangled inheritance that survive before a classical null catches up — stressing entangle + inherit + mid-circuit-measure + feed-forward + readout together.

**Why only medium.** Entanglement/GHZ benchmarks and dynamic-circuit benchmarks already exist. The genealogical/dynamic combination is a real but *incremental* twist, not a leap.

**How to improve.** Position strictly as a **dynamic-circuit** benchmark (the under-served axis), report against existing dynamic-circuit benchmarking methods, and show it discriminates devices that Quantum Volume ranks equally. Good as a secondary figure inside #1, weak as a standalone thesis.

### #5 — Evolved error mitigation / decoherence-free-subspace discovery (moonshot)

**Claim.** Selection for high witness = selection for coherence-protecting genome configurations → the population *discovers* decoherence-free encodings / error mitigation on its own.

**Why moonshot.** Enormous payoff and novelty, but high risk: it must actually find non-trivial protected subspaces on NISQ hardware, which may not happen at reachable W and generation budgets. Low current feasibility.

**How to improve / de-risk.** Prototype in simulation with a known DFS (e.g. collective-dephasing) and check the loop rediscovers it before any hardware claim. Keep it as a "future work / evidence-of-direction" section, not the main claim.

### #6 — Quantum open-ended evolution / novelty search (moonshot)

**Claim.** First open-ended / novelty-search evolutionary system on a quantum substrate; possibly foundation-model-guided novelty (as in classical ALife 2024–25).

**Why moonshot.** Empty gap (high novelty) but speculative and hard to make falsifiable — open-endedness metrics are contested even classically. Low feasibility, low near-term teeth.

**How to improve.** Only pursue after #1/#2 land; borrow a concrete open-endedness metric (behavioral novelty in a defined space) so it's measurable.

### #7 — Adaptive GHZ quantum metrology / self-calibrating sensor

**Claim.** A "living" GHZ population that self-organizes to maintain large entangled probe states for Heisenberg-limited sensing.

**Why low.** The space is crowded with strong incumbents and variational GHZ sensing (VISTA) already covers the "optimize the probe" idea; the Darwinian layer adds little. Feasibility on NISQ (large-GHZ sensing) is hard.

**How to improve.** Only compelling if the evolutionary loop demonstrably beats variational optimization at maintaining probe entanglement under drift — a high bar. Not recommended.

### ✗ — Certified-quantum randomness / liveness beacon (REJECTED)

**Why dead.** Certified randomness requires a classically hard task (RCS + XEB, certified on Frontier; *Nature* 2025). `⟨X^⊗W⟩` for a GHZ is trivially classically predictable — an entanglement witness certifies entanglement under trust assumptions, not cryptographic proof-of-quantumness. Do not make a "beacon" or "unforgeable randomness" claim. (The witness remains valuable as a *benchmark/audit* signal, not as a randomness certificate.)

---

## 5. Recommended path (do this)

1. **Adopt #1 as the F7 thesis framing.** Rewrite the headline from "certified quantum life" to "a certified, self-organizing test of the quantum edge in reservoir computing." Keep the three honesty gates.
2. **Fix the three technical forks (mandatory for the QRC claim):**
   - **Expressivity:** a bare GHZ genealogy is too shallow (l=1 underperforms). Use a **brick-wall entangler, l ≈ 7–10 layers** for the reservoir dynamics — the QuantumLife ancestor already prototyped brick-wall. Keep the GHZ witness as the *certification* layer on top.
   - **Readout:** single-qubit marginals are invariant on GHZ (F0 finding), so single-qubit `⟨Z_i⟩` readout is degenerate. A brick-wall reservoir restores informative single-qubit readout; additionally emit **k-body correlators** `{⟨Z_iZ_j⟩, ⟨X_iX_j⟩, …}` from the same shots for a rich feature vector.
   - **Operating point:** σ=0.44 is the *stable/under-driven* phase, not a failure — it is the diagnosis. Reach the edge with hotter mutation, higher feedback gain, and more generations than the 16-gen Run-1 budget allowed.
3. **Add the field's metrics:** spectral form factor + level-spacing ratio (edge diagnosis) and `C_Σ` / NARMA-NRMSE (capacity), so the work is directly comparable and citable.
4. **Run the three-curve experiment** (edge peak / contingency / certification knockout) on hardware; pre-register the classical-vs-quantum decomposition so a null is still a result.
5. **Fallback:** if the QC allocation can't reach the edge, ship **#3 (quantum DishBrain testbed)** — no speed claim required, same apparatus, still novel.
6. **Park** #5/#6 as future-work sections; **drop** the beacon claim entirely.

---

## 6. Sources

- Kobayashi & Motome, *Edge of Many-Body Quantum Chaos in QRC*, PRL 2025 — arXiv:2506.17547
- Kobayashi, Fujii et al., *Feedback-driven QRC for time-series analysis* — arXiv:2406.15783
- *Role of Entanglement in QRC with coupled Kerr oscillators* — arXiv:2508.11175
- Martínez-Peña et al., dynamical-phase / ergodic-localization QRC (cited within 2506.17547)
- *Certified randomness using a trapped-ion quantum processor*, Nature 2025 — s41586-025-08737-1
- Fields & Friston, *A free energy principle for generic quantum systems* — arXiv:2112.15242
- Kagan et al., *In vitro neurons learn (DishBrain)*, Neuron 2022
- Self-tuning-to-criticality (classical): P-CRITICAL; E-I-balance self-adaptation (Nat. Commun. 2025); edge of ergodicity breaking — arXiv:2604.15669
- Entanglement-based volumetric benchmark — arXiv:2209.00678; EU Flagship KPIs — arXiv:2512.19653
- Variational GHZ sensing (VISTA) — arXiv:2605.04203
- Gate-based QRC forecasting on NISQ — arXiv:2510.13634; non-unital noise as QRC resource — arXiv:2409.07886
- QCi reservoir-computing commercialization (EmuCore/Neurawave); McKinsey Quantum Technology Monitor 2026
- Foundation-model-guided ALife — arXiv:2412.17799
- Alvarez-Rodriguez et al., *Quantum Artificial Life in an IBM Quantum Computer*, Sci. Rep. 2018 — arXiv:1711.09442

---

## 7. Part B — totally different (non-computing) real-world directions

Section 3 optimized for a *scientific* leap (compute something, beat a control). But the reusable assets — an entanglement signature with no classical surrogate, a closed loop that reacts to perturbation, a self-organizing lineage, QRNG-seeded feedback — also fit domains that are not "computing" at all: **operations/observability, security, verification, networking.** These are often *more* directly implementable in the real world because the bar is "be sensitive and always-on," not "beat a classical algorithm."

**Reframing the axes.** There are two different questions, and they have different winners:
- *Best scientific thesis contribution* → **#1 in §3 (certified quantum-vs-classical edge in QRC).**
- *Best directly-implementable real-world product* → **B1 below (the entanglement canary).**

They don't compete — one is the paper, the other is the product. Both run on the same engine.

### Landscape (Part B)
- **QPU observability is commercializing.** Quantum Resource Management Interface (QRMI) exposes device/job metrics (coherence, calibration drift, per-job fidelity) via standard stacks — Prometheus, InfluxDB, Grafana. Operators want to "track QPU health in real time, detect degradation, schedule maintenance." Continuous-benchmarking dashboards and drift trackers exist (Sandia "Detecting and tracking drift in QIPs"; a USPTO drift-compensation patent). **But every existing tool is passive/scheduled (randomized benchmarking, Hahn echo, known-answer circuits) and reports only 1-/2-qubit gate fidelity and coherence — none continuously monitor entanglement-genealogy or dynamic-circuit (mid-circuit-measurement + feed-forward + reset) health.** That is the gap.
- **Quantum PUFs are real but material/optical** (single-photon emitters in AlN nanocrystals, quantum-dot FRET, optical scattering), 2025-active. A *gate-model* quantum PUF has known possibility/impossibility results (Quantum 2021). No-cloning underpins the security.
- **Cloud-verification / anti-spoofing is a deep cryptographic field** (Mahadev's "cryptographic leash," Verifiable Blind Quantum Computing, trap-based verification) whose explicit goal is "make sure a real quantum computer is running instead of a classical simulation." Rigorous but heavy.
- **Quantum-network entanglement verification is mature and photonic** (deployed QKD 325 h / 50 km; scalable network entanglement certification; measurement-device-independent CV witnesses; GME as the network-quality indicator; 81% fidelity threshold for QKD).

### Part B candidates, scored (same rubric as §3)

| # | Direction | Novelty | Teeth | Defens. | Feas. | Fit | **Score** |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **B1** | **Entanglement / dynamic-circuit health "canary" (QPU observability)** | 4 | 5 | 5 | 5 | 5 | **4.70** |
| B2 | Cloud-run attestation / SLA check ("did I get real entangling HW?") | 3 | 4 | 3 | 4 | 4 | 3.50 |
| B3 | Behavioral quantum PUF / device fingerprint (anti-counterfeiting) | 3 | 4 | 3 | 4 | 4 | 3.50 |
| B4 | Live entanglement monitor for quantum-network links / repeaters | 3 | 4 | 4 | 2 | 3 | 3.20 |

**B1 outscores every §3 candidate on real-world implementability (4.70).** If the question is "how do we ship this to the real world," B1 is the answer.

### B1 — the entanglement canary (deep dive) ★ recommended real-world implementation

**What it is.** A small certified-quantum organism that lives on a handful of otherwise-idle qubits of a production QPU and runs continuously. Its homeostasis *is* the health signal:
- **Witness `⟨X^⊗W⟩` above the classical null** = the device can still create and inherit genuine entanglement. When it sags, entanglement quality is degrading — a signal no gate-fidelity dashboard reports.
- **Surprise spike / failure to re-cohere after a "poke"** = anomaly / drift / tamper. The active-inference loop is already an anomaly detector: surprise = deviation from the learned baseline.
- **Criticality set-point (σ)** = homeostatic target. Here σ≈0.44 stable homeostasis is a *feature*, not a failure — a health monitor wants a steady set-point it can watch for departures.
- **Yoked control** = the built-in baseline that separates "the world changed" from "the monitor drifted."
- It specifically exercises **dynamic-circuit primitives** (mid-circuit measurement, feed-forward, reset/reuse) that are the frontier of NISQ and are *not* covered by RB / coherence dashboards.

**Why it's a leap, not a feature.** Current QPU observability answers "are the gates good?" The canary answers "can this machine still do entangled, dynamic-circuit work *right now*, and has anything changed?" — a higher-level, workload-shaped, continuously-updated health signal that maps onto what users actually run. First entanglement-native, always-on QPU health monitor.

**How to implement it in the real world (concrete):**
1. **Footprint.** Run the existing closed-loop engine at small W (4–8) on a spare qubit chain; one short circuit per cycle, cheap enough to interleave with the provider's calibration cadence or a user's idle time.
2. **Signals out.** Emit per-cycle metrics — `witness_margin`, `surprise`, `sigma`, `adaptation_gap`, `avalanche_rate`, plus the raw chain-quality gate (2q err, readout err) already in `hardware_batches.py` — as Prometheus/OpenMetrics text. This slots directly into the QRMI → Prometheus → Grafana stack that quantum-cloud ops already use.
3. **Dashboard.** A Grafana panel (or the existing web spectacle, wired to `research_runs/`) showing the living witness heartbeat + a drift/anomaly timeline. The spectacle you already built *is* the ops dashboard.
4. **Alerting.** Threshold on witness dropping below the null band for N cycles, or surprise exceeding the yoked baseline by k·σ → page an operator / auto-trigger recalibration (there is already a drift-compensation patent to hand off to).
5. **Validation experiment (thesis-grade and honest):** inject known drift (detune a qubit, raise readout error, force a stale calibration) and show the canary's witness/surprise flags it **earlier or more specifically** than standard RB / gate-fidelity tracking — especially for entanglement- and dynamic-circuit-specific faults those miss. No speed claim, no classical-hardness assumption: the contribution is *sensitivity and coverage*, which is exactly what a monitor is judged on.

**How to improve / de-risk.** Benchmark head-to-head against RB and coherence-time trackers on a menu of injected faults; report where the canary wins (entanglement collapse, mid-circuit-measurement degradation, feed-forward latency faults) and where it doesn't (single-qubit T1 that RB already catches) — an honest coverage map is more credible than "it catches everything."

**Note on the spectacle.** The `web/spectacle.html` you have doubles as the B1 product surface: the "poke" becomes "inject drift," the heartbeat becomes the live health trace, the yoked ghost becomes the baseline. Minimal rework to turn the demo into an ops console.

### B2/B3/B4 (brief)
- **B2 — cloud-run attestation.** A cheap "was my job actually run on entangling hardware, not silently downgraded or simulated?" check under the measure-and-resend threat model. Weaker than cryptographic VBQC, but complementary as an SLA/telemetry signal. Folds into B1's metric stream.
- **B3 — behavioral qPUF.** The device-specific witness-decay + error-profile signature as a *dynamic* hardware fingerprint. Novel twist (a live, evolving PUF) but the qPUF field is crowded and has impossibility caveats; treat as a security side-result, not the main claim.
- **B4 — quantum-network entanglement monitor.** Conceptually strong (a self-organizing link-entanglement canary) but the QKD/network verification field is mature, photonic, and device-independent; porting a gate-model organism to a photonic link is a real research project, not a near-term implementation. Park.

### Recommendation update
- **Ship B1 (entanglement canary) as the real-world implementation** — highest implementability, real market, honest, reuses the engine and the spectacle. This is the answer to "how do we put this to real-world use."
- **Keep §3 #1 (QRC edge decomposition) as the scientific thesis** — the deep, novel, citable contribution.
- Do B1's telemetry and §3-#1's science on the same runs: the canary's metric stream *is* the reservoir's state readout. One engine, two deliverables — one product, one paper.

### Part B sources
- Quantum Resource Management Interface (QRMI); QPU telemetry via Prometheus/InfluxDB/Grafana (SC'25 HPC-QC workshop, ACM 3731599.3767549)
- Sandia, *Detecting and tracking drift in quantum information processors* (Nat. Commun.); USPTO 11,710,058 drift-compensation patent
- Continuous benchmarking dashboards for QPUs (HPCKP; QIR/MIT benchmarking)
- Quantum PUF 2025: single-photon emitters in AlN (Adv. Funct. Mater.); quantum-dot FRET OPUF (Commun. Mater.); *Quantum PUFs: possibilities and impossibilities* (Quantum 2021)
- Verifiable quantum cloud: Mahadev cryptographic leash; Verifiable Blind Quantum Computing; experimental cryptographic verification on IBM cloud (S209592732030534X)
- Quantum-network entanglement certification: scalable network certification (arXiv:2601.07427); MDI-CV entanglement witnesses; deployed QKD 325 h/50 km (arXiv:2511.02578)

---

## 8. Part C — prior-art verdict + the "useful quantum simulation" lane

Two questions drove this section: (1) has any of the above ever actually been done? and (2) is there a *useful quantum simulation* home for this project? The answers reshape the recommendation.

### 8.1 Prior-art verdict (has it been done?)

| Idea | Ever done? | Verdict |
|---|---|---|
| Quantum artificial life as a *real-world application* (not a demo) | **No.** Post-2018 it "remains largely theoretical and exploratory"; no substantial follow-up applications 2019–2023. | Gap still open — the whole premise holds. |
| Quantum ALife / living organism as a **hardware health monitor** (B1) | **No prior art found.** | B1 is novel. |
| Self-tuning **quantum** reservoir to the edge of chaos (§3 #1/#2) | **No** (classical only: P-CRITICAL, E-I balance). | Still open. |
| **Feedback / measurement-induced criticality on a QPU** (the physics under CriticalQuantumLife's criticality gate) | **YES — heavily, 2024–2026, by better-resourced groups.** IBM "Order from chaos" (100 qubits, MIPT + control transition); 2512.07966 (30-qubit absorbing-state, directed-percolation, z=1.58). | The **bare transition is scooped.** But see below. |
| **Self-ORGANIZED** criticality (self-tuned, no parameter sweep) in a feedback QPU circuit | **Not found — appears open** (all hardware results *externally tune* the measurement rate p to locate the critical point; SOC on gate-model hardware via an adaptive rule is not among them). *Verify against latest literature before claiming.* | The differentiated gap. |

**The crux.** Everyone who has reached criticality on a QPU did it by **fine-tuning a knob** (measurement rate p: 0.10→0.35→0.45 in 2512.07966). Self-organized criticality is, by definition (Bak–Tang–Wiesenfeld), reaching the critical point **without fine-tuning**, via an adaptive dynamics — which is exactly what CriticalQuantumLife's Darwinian/free-energy loop is supposed to be. So the project's *only* defensible physics niche is the **self-organized** (self-tuned) critical point, not the transition itself.

**Honest caveat that governs everything.** CriticalQuantumLife has **not yet** self-organized to criticality — Run-1 gave σ=0.44 (subcritical); the criticality gate *failed*. The differentiator (SOC) is precisely the unmet gate. Until the loop is shown to drive itself to σ≈1 on hardware, the SOC claim is aspirational, not demonstrated.

### 8.2 The useful-quantum-simulation landscape

- **Mainstream useful QS = chemistry & materials, and it is not this project's lane.** 2025 utility-scale results: Quantinuum chemistry at classically-frustrating scale; spin-wave spectra of chromium tri-halides outside linear response ("utility achievable even without quantum advantage"); strongly-correlated materials, high-Tc, catalysts (Nature Phys. s41567-024-02738-z; JPCL utility-scale chemistry). CriticalQuantumLife is not a chemistry simulator; don't force it here.
- **The project's real useful-QS home is non-equilibrium / monitored-circuit / open-system physics:** absorbing-state transitions (directed percolation), measurement-induced entanglement transitions, driven-dissipative self-organized criticality. These are genuinely hard classically (the frontier papers fall back on tDMRG/MPS that break down in the volume-law regime) and are a hot, funded, IBM-tier subfield of useful quantum simulation. CriticalQuantumLife's Lindblad "death" channel is also literally open-system dissipative-dynamics simulation.

### 8.3 New candidate — C1: self-organized absorbing-state criticality in a feedback circuit

**Claim.** Where recent hardware experiments observe measurement-*induced* criticality by externally tuning the measurement rate across the directed-percolation transition, CriticalQuantumLife uses an adaptive **Darwinian / free-energy feedback rule** that makes the processor **self-organize** to that same absorbing-state critical point — the first *self-tuned* (rather than fine-tuned) critical point in a feedback quantum circuit on hardware — with the critical state certified by an entanglement-inheritance witness.

**Score (same rubric):** Novelty 4 · Teeth 3 · Defensibility 3 · Feasibility 3 · Fit 5 → **3.55.**
- **Fit is maximal:** the existing criticality suite (branching σ→1, avalanche α≈1.5, absorbing-"dead" vs chaos) *is* the directed-percolation order parameter — the project already measures the right quantity in the field's own language.
- **Novelty is real** (self-organized vs measurement-induced) but the field is crowded and moving fast.
- **Defensibility/feasibility are the risk:** (a) it requires actually reaching σ≈1, which failed at Run-1; (b) it is scale-disadvantaged — IBM already did the *tuned* version at 100 qubits with far better fidelity and even ran a quantum-vs-classical certification. CriticalQuantumLife cannot win on scale; it can only win on *self-organization + evolutionary feedback rule + biological interpretation*.

**How to improve / de-risk.**
- Adopt the field's exact order parameter and universality analysis (single-seed initial state, local occupation ⟨n_i(t)⟩, sub-ballistic spreading exponent z, finite-size scaling in the control parameter) so results are directly comparable to 2512.07966 / 2509.18259.
- Prove the loop *self-organizes* (reaches criticality from both the frozen and chaotic sides without a hand-set p) — that is the entire contribution; a single subcritical run does not establish it.
- Lean on the differentiators the big groups don't have: an **evolutionary/active-inference feedback rule** (vs simple conditional reset) and an **entanglement-inheritance witness** as the certificate. Position explicitly as "self-organized counterpart to the tuned transitions," citing them up front.

### 8.4 Updated recommendation — three lanes, one engine

The project now has three coherent, non-competing framings; pick by what you want the thesis to *be*:

| Lane | Best candidate | What it is | Main risk |
|---|---|---|---|
| **Product / ops** | **B1 — entanglement canary** | Ship it: continuous entanglement/dynamic-circuit health monitor for QPUs | least scientific novelty |
| **Applied science** | **§3 #1 — QRC edge decomposition** | Answer the field's open "is the edge quantum?" question | must fix expressivity/readout (§5) |
| **Fundamental physics** | **C1 — self-organized absorbing-state criticality** | First *self-tuned* critical point in a feedback QPU circuit | scooped on the bare transition; SOC not yet achieved; scale-disadvantaged |

All three share the same closed-loop + yoked + witness engine and the same `research_runs/` stream — the shared invariant across all of them is **self-organization + an entanglement/quantum-vs-classical certificate + a biological feedback rule**. Recommended sequencing: **B1 first** (lowest risk, real-world, shippable, and it *needs* no unmet gate), then decide between the QRC-edge paper and the SOC-physics paper based on whether Run-2 can be funded to actually reach σ≈1 (if yes → C1 is the higher-prestige swing; if no → §3 #1 or B1's audit framing is the safe landing).

### Part C sources
- IBM Research, *Order from chaos with adaptive circuits on quantum hardware* — arXiv:2509.18259 (100 qubits, MIPT + control-induced transition, quantum-vs-classical certification)
- *Measurement- and Feedback-Driven Non-Equilibrium Phase Transitions on a Quantum Processor* — arXiv:2512.07966 / PRL 2c1p-8vx9 (30-qubit absorbing-state, directed percolation, z=1.58; 8-qubit entanglement transition)
- *Observation of feedback-directed quantum dynamics in large-scale quantum processors* — arXiv:2604.11900
- *Universality of stochastic control of quantum chaos with measurement and feedback* — arXiv:2506.10067
- *Absorbing state phase transitions beyond directed percolation in dissipative quantum state preparation* — arXiv:2410.00819 (PRR)
- Self-organized criticality observed in a controllable atomic system (Köln, 2020)
- Useful QS mainstream: programmable molecule/material simulation (Nat. Phys. s41567-024-02738-z); utility-scale quantum computational chemistry (JPCL); Quantinuum scalable chemistry 2025
- Quantum ALife has no post-2018 real-world application (AZoQuantum; *QML & quantum biomimetics: a perspective*, arXiv:2004.12076)

---

## 9. FINAL PICK — one winner: the Quantum Canary (B1)

After all the search and scoring, the decision is not close once it is filtered through the project's real constraints. **Go build the entanglement health monitor — the "Quantum Canary." B1.**

### 9.1 The pick in one paragraph

A **quantum smoke-alarm.** A tiny certified-quantum organism lives on a spare corner of a production quantum chip and keeps a steady heartbeat for as long as the machine can still make real, inherited entanglement and run measure-and-react (dynamic) circuits. When the machine starts to degrade, the heartbeat spikes and the alarm fires — **earlier and more specifically than today's tools, because it watches the exact quantum behaviors today's tools ignore.** It ships as a small metrics exporter that plugs into the monitoring dashboards quantum-cloud operators already run.

### 9.2 Why it is the best — in simple terms

1. **It works with what you already proved.** Your quantum gate *passed* — the entanglement witness `⟨X^⊗W⟩` above the classical null is exactly the live health signal a monitor needs. You don't have to fix anything to start.
2. **It turns your failure into a feature.** σ=0.44 was a failed *criticality* gate — but a health monitor *wants* a steady set-point to watch for departures. Homeostasis is the product, not a bug. Every other lane needs you to reach σ≈1 (which you failed, with no budget to retry). This one doesn't.
3. **Nobody has done it.** Quantum artificial life has had no real-world application since 2018; using a living quantum organism as a hardware monitor has no prior art. You are not racing IBM here (they own the *tuned criticality* physics; you would lose on scale). You own this.
4. **There is a real, growing market with an obvious buyer.** Quantum computers are becoming cloud utilities; utilities need health monitoring. The observability stack already exists (QRMI → Prometheus → Grafana) and operators explicitly want to "track QPU health in real time, detect degradation, schedule maintenance." Buyers: quantum-cloud providers and the people who rent time on them.
5. **It fills a genuine blind spot.** Every existing monitor (randomized benchmarking, Hahn echo, coherence dashboards) is *passive, scheduled,* and only sees **1- and 2-qubit gate fidelity + coherence**. **None continuously watch entanglement quality or dynamic-circuit health (mid-circuit measurement, feed-forward, reset/reuse)** — the primitives that modern workloads and error correction depend on, and that fail in ways gate fidelity misses. The Canary is entanglement-native and always-on.
6. **It is honest under any review.** No speed claim, no classical-hardness assumption, no unmet gate. The contribution is **sensitivity and coverage** — precisely what a monitor is judged on. It stands even if quantum never beats classical anywhere.
7. **It reuses everything you built.** Engine, the **yoked control** (= the baseline that separates "the machine changed" from "the monitor drifted"), the **witness** (= health signal), the **poke** (= inject-a-fault test), and the **spectacle** (= the live dashboard). Minimal new code, fast to a result.

### 9.3 What the application actually is

An **entanglement-native, always-on QPU health-and-anomaly monitor**, delivered as:
- a lightweight process that runs the closed-loop engine at small W (4–8) on a spare qubit chain, one short circuit per cycle;
- a **Prometheus/OpenMetrics exporter** emitting per-cycle `witness_margin`, `surprise`, `sigma`, `adaptation_gap`, `avalanche_rate`, and the raw chain-quality numbers already computed in `hardware_batches.py`;
- a **Grafana panel** (or the existing `web/spectacle.html`, wired to `research_runs/`) showing the living heartbeat + a drift/anomaly timeline;
- an **alert rule**: witness below the classical-null band for N cycles, or surprise exceeding the yoked baseline by k·σ → page an operator / trigger recalibration.

The poke becomes "inject drift," the heartbeat becomes the health trace, the yoked ghost becomes the baseline. The demo you already have *is* the product surface.

### 9.4 Why it is a great study — and adoptable to something useful

The study is a clean, honest, falsifiable systems result: **build the monitor, then prove it catches faults that standard tools miss.**

- **The experiment.** Inject known faults on real hardware — detune a qubit, raise readout error, force a stale calibration, degrade mid-circuit-measurement fidelity, add feed-forward latency — and measure whether the Canary's witness/surprise flags each one **earlier or more specifically** than randomized benchmarking and coherence-time tracking.
- **The deliverable.** A **coverage map**: where the Canary wins (entanglement collapse, dynamic-circuit degradation — the blind spots), where it ties (single-qubit T1 that RB already catches), and its detection latency vs the incumbents. An honest coverage map is more credible and more useful than "it catches everything."
- **Why it's adoptable.** It drops straight into the monitoring stack that IBM Quantum, AWS Braket, and Azure Quantum-style operators already use. It is a telemetry *component*, not a moonshot: a Prometheus exporter + a Grafana dashboard + an alert rule. A provider can adopt it as an entanglement-and-dynamic-circuit health probe without changing anything else.
- **It compounds.** The Canary's metric stream is the same state readout the science lanes need. Choosing B1 does not close the door on the QRC-edge paper (§3 #1) or the SOC-physics paper (C1) — it builds the foundation they both sit on and buys time to fund the runs that reach σ≈1. B2 (SLA attestation) and B3 (device fingerprint) also fall out of the same metric stream.

### 9.5 Honest downside (and why it still wins)

B1 is an **engineering + validation** contribution more than a physics *discovery*; its scientific novelty is lower than a phase-transition paper. But: (a) a fault-injection coverage study vs RB is a legitimate, publishable systems/benchmarking result; (b) it is the *only* lane that is shippable now, needs no unmet gate, is un-scooped, and has a named buyer; and (c) it keeps the higher-prestige science lanes open for later. For a solo thesis with a partial hardware result and no remaining QC budget, "shippable, honest, novel, and adoptable" beats "prestigious but blocked."

### 9.6 Where to go next — the immediate step

1. Write **B1 as a feature plan** (call it `feature-F8-quantum-canary.md`): the metrics exporter, the fault-injection harness, the coverage-map experiment, the alert rule, acceptance criteria.
2. Build the **Prometheus exporter** around the existing engine (small W, spare chain) — no new physics, just wire `research_runs/` metrics to an OpenMetrics endpoint.
3. Build the **fault-injection harness** and run the coverage study (some of it in simulation with injected noise; a small hardware confirmation when budget allows).
4. **Rewire `web/spectacle.html`** into the ops console: poke → "inject drift," heartbeat → live health trace, gates → live status, add a drift/anomaly timeline.
5. Frame the thesis (F7) around it: *the first entanglement-native, always-on health monitor for quantum processors — validated by fault-injection to catch entanglement and dynamic-circuit failures that gate-fidelity benchmarking misses.*

**One line to remember:** everyone else is trying to make quantum life *do* something clever; the win is to make it *watch* something valuable — the health of the quantum machine it lives on.

---

## 10. The 2-hour experiment — one idea waiting to be tested: the Quantum Sandpile

The Canary (§9) is the *product*. This is the *swing* — one clean, decisive experiment that tests a real, published-but-unrealized prediction, fits ~2 hours of IBM Heron time, and is uniquely yours because it *is* self-organization. If you get one hardware window, run this.

### 10.1 The prediction that is waiting to be tested

- **1998 theory:** Dickman, Muñoz, Vespignani & Zapperi proved that **self-organized criticality is an absorbing-state phase transition** (directed-percolation class) that a system reaches **on its own** through one mechanism: **slow drive + fast dissipation.** Drive the system a little *only when it goes quiet*, let the fast dynamics relax it toward the absorbing (dead) state, and the feedback loop **self-tunes the system to the critical point with no fine-tuning.** (cond-mat/9712115; recipe restated for feedback systems in Frontiers Phys. 8:333, 2020.)
- **Dec-2025 hardware:** arXiv:2512.07966 observed **exactly that absorbing-state / directed-percolation transition on a superconducting QPU** (30 qubits, z=1.58) — **but by hand-tuning the measurement rate p** (p = 0.10 → 0.35 → 0.45). IBM's 2509.18259 does the same by tuning, at 100 qubits.
- **The gap:** nobody has added the **drive-when-quiet feedback loop** to make a quantum processor **self-organize** to that critical point instead of being tuned to it. The tuned transition is done; the **self-tuned ("self-organized") version is untested.** That self-tuning is the entire identity of this project.

### 10.2 The experiment — "Quantum Sandpile"

Turn the monitored circuit into a sandpile: grains = quanta of activity, toppling = measurement-induced relaxation, the pile self-organizes to the critical slope.

**Per time-step, on a W≈20–30 qubit chain (match 2512.07966's 30-qubit scale):**
1. **Spread (unitary layer).** One brick-wall layer of 2-qubit entangling gates — activity spreads to neighbors.
2. **Dissipate (measurement + feed-forward).** Measure each site mid-circuit; conditionally reset toward |0⟩ (the absorbing/"dead" state). This is the fast relaxation.
3. **Drive-when-quiet (the SOC trick).** Read global activity A = number of non-|0⟩ sites from the mid-circuit record. **If A = 0 (the pile has gone flat / everyone died), inject exactly one "grain"** — a feed-forward X or Ry on one random site. **Otherwise, do nothing.** This conditional slow drive is what self-tunes the system to criticality; it is the one thing the tuned experiments do *not* have.
4. Repeat for T steps; log the activity time-series.

**No measurement rate is set by hand.** The system chooses its own operating point.

### 10.3 What you measure (your existing suite is exactly right)

- **Activity density self-parks** at the directed-percolation critical density (not full, not zero).
- **Avalanches** (contiguous active runs between quiescences) follow a power law P(S) ∝ S^{−α} with **α ≈ 1.5**, and branching **σ → 1** — your F2 metrics *are* the DP order parameter, in the field's own language.
- **Certification layer (your signature, nobody else's):** at the self-organized steady state, measure the **genealogical entanglement witness** across the active cluster and show it sits **above the classical measure-and-resend null** — the self-organized critical state is genuinely quantum.
- **The control that proves "self-organized":** run a **yoked drive** — inject grains at the *same average rate* but at *random times regardless of quiescence*. Prediction: the drive-**when-quiet** rule self-tunes to criticality; the yoked random drive does **not**. That single contrast is the whole claim.

### 10.4 Why this is the right 2-hour bet

- **Decisive.** Binary outcome: either the activity self-parks at criticality with DP avalanche scaling under the drive-when-quiet rule (and not under the yoked control), or it doesn't. One figure settles it.
- **Feasible in the budget.** W≈20–30, shallow per-step depth, a few hundred–low-thousands of executions — comfortably inside ~2 h of Heron.
- **It repairs your Run-1 failure by design.** Run-1 landed at σ=0.44 because it tried to *hand-set* a mutation/feedback level and hope for criticality. **SOC removes the fine-tuning problem** — the drive-when-quiet loop is *built* to converge to the critical point. Reaching criticality stops being luck and becomes the expected behavior. This is the single most important reason to run it.
- **It is uniquely yours.** The big groups did the *tuned* transition with better hardware; the *self-organized* counterpart matches your identity, needs only your existing feed-forward + activity-readout + selection machinery, and is first-of-its-kind.
- **The headline if it works:** *first self-organized (self-tuned) absorbing-state critical point on a quantum processor — reached without fine-tuning, certified quantum.* That is a genuine, citable physics result, not a demo.

### 10.5 Honest risk + mitigation

- **Risk:** NISQ noise adds uncontrolled dissipation that could push the pile subcritical (toward the absorbing/dead phase), as in Run-1. **Mitigation:** small W to keep depth low; the SOC loop *self-corrects* (if it dies, it re-seeds; if it saturates, dissipation wins) so it is more robust than open-loop tuning; sweep the grain size / relaxation strength lightly if the self-organized density sits off-critical.
- **Risk:** the entanglement witness at the critical density may be weak. **Mitigation:** report it as margin-above-null (your existing certification), and lead the physics claim with the avalanche/DP result, the witness as the quantum-certification layer.

### 10.6 Relationship to the Canary

Do the **Canary (§9)** as the shippable product and thesis backbone; keep the **Quantum Sandpile** as the one hardware swing if you get a real Heron window — it is the highest-prestige, decisive, uniquely-yours physics result reachable in ~2 hours, and it directly fixes the criticality gate that Run-1 missed. They share the same engine; the sandpile is just the closed-loop engine run with a drive-when-quiet rule and DP-style analysis.

### 10.7 Budget tiers — what the Sandpile buys with 10 / 30 / 180 minutes

**Can 10 minutes do it? Yes — as a go/no-go, not the full claim.** The Sandpile splits cleanly into a *cheap binary* and *expensive rigor*:
- **Cheap (10–30 min):** does the activity self-park at a nonzero steady density, and does the **drive-when-quiet** rule differ from the **yoked-drive** control? That is the existence-of-self-organization result — a real yes/no.
- **Expensive (up to 180 min):** the *directed-percolation* certification — avalanche exponent α, dynamic exponent z=1.58, order-parameter finite-size scaling across several widths, error mitigation, multiple seeds. This is what upgrades "it self-organizes" to "it self-organizes to a *certified DP critical point*."

| QPU budget | What you run | What you can claim | What you can't yet | Grade |
|---|---|---|---|---|
| **10 min** (proof-of-principle) | 1 width (W≈12–16); T-sweep of ~3 values; **closed-loop + 2–3 yoked points**; ~4096 shots; ~6–10 circuits | "Under drive-when-quiet the activity self-organizes to a **nonzero steady density**, and the yoked control does not." Existence + the decisive contrast. | No clean avalanche power-law (too few avalanches), no exponents, no finite-size scaling, weak witness statistics. | Go/no-go; internal figure |
| **30 min** (decisive, one size) | W≈20–30; T long enough for steady state; **full closed vs yoked**; **avalanche distribution + branching σ + witness certification** at the self-organized point; 8192 shots; 2–3 seeds; ~30–50 circuits | "At a fixed size, the processor **self-organizes to criticality** (σ→1, avalanche power law α≈1.5), **only** under drive-when-quiet, and the critical state is **certified quantum** (witness > null)." | Universality class not pinned (needs scaling across sizes); exponents have single-size error bars; limited error mitigation. | Letter-grade headline |
| **180 min** (full paper) | **3 widths** (W≈12/20/30) for **finite-size scaling**; T-sweep; **closed / yoked / classical-surrogate**; grain-size + relaxation-strength robustness sweep; 8192 shots; ~5 seeds; **error mitigation** (TREX readout + ZNE); ~150–250 circuits | "The self-organized critical point is in the **directed-percolation universality class** (extracted α, z=1.58, order-parameter β via finite-size scaling), reached without fine-tuning, certified quantum, robust to grain/relaxation choices, and beats both classical controls." | — (this is the complete result) | PRL / PRX-grade |

**The trade-off in one line:** the *binary* claim (self-organizes + beats yoked) is cheap and fits 10–30 min; every extra minute after that buys **rigor** (exponents → universality class → error-mitigated robustness), not a different conclusion. Run 10 min first as a go/no-go; only spend the 180 min if the cheap tier says yes.

**Caveats on the numbers.** These are **QPU-execution-time** estimates, not wall-clock (device queue can add hours on top). Dynamic circuits are slower per shot than static ones — each time-step carries a mid-circuit measurement + real-time feed-forward (~hundreds of ns to µs latency each), so a T=60–100 trajectory costs more per shot than a plain circuit; circuit counts above assume that overhead. Treat the tiers as orders of magnitude to plan against, and calibrate against one small timed job before committing a full allocation.

### Section 10 sources
- Dickman, Muñoz, Vespignani, Zapperi, *Self-organized criticality as an absorbing-state phase transition* — cond-mat/9712115
- *Feedback Mechanisms for Self-Organization to the Edge of a Phase Transition* — Front. Phys. 8:333 (2020)
- *Measurement- and Feedback-Driven Non-Equilibrium Phase Transitions on a Quantum Processor* — arXiv:2512.07966 / PRL 2c1p-8vx9 (tuned DP transition, the baseline to beat by self-organizing)
- *Concomitant Entanglement and Control Criticality Driven by Collective Measurements* — PRX Quantum 6, 010351
- IBM, *Order from chaos with adaptive circuits on quantum hardware* — arXiv:2509.18259

---

## 11. Project Wiki — how it all works, in detail, + next steps

A single reference you can read top-to-bottom. It links every study, defines every term, walks the engine one operation at a time, and ends with an ordered next-steps checklist. When something is defined elsewhere in this doc, it is cross-linked by section number.

### 11.1 Map of the studies (the lineage)

Three sibling projects share one toolchain and one honesty rule; each fixed the previous one's flaw. Read them in order.

| Study | Repo path | Axis | Core claim | Result | Fatal flaw it exposed | Fed into |
|---|---|---|---|---|---|---|
| **QuantumLife** ("Quantum Tree") | [`../../QuantumLife`](../../QuantumLife) | **Spatial** — correlation across qubits in one generation | An entangling layer imprints a spatial correlation `C(d)` a classical L-system can't fake | On `ibm_kingston`, hardware `c(1) = −0.077`, z ≈ −10 vs both nulls; teleport bond `−0.116` (d=12) vs SWAP `−0.002` | The serial entangler is ~800 deep → correlation is **confounded with decoherence**; could **not earn the word "entanglement"** | artificial-life |
| **artificial-life** ("QDEP") | [`../../artificial-life`](../../artificial-life) | **Temporal → genealogical** — inheritance down a lineage | `C(g)` is classically fakeable, so move the claim **off-diagonal** to the GHZ witness `⟨X^⊗W⟩` with no classical surrogate | Witness by width: W3 = +0.879, W6 = +0.612, W12 = +0.301, **W24 = +0.038 (48 qubits, marginal ALIVE)**, W32 = dead. Teleport routing **refuted** on Heron | No **speed** advantage; only the off-diagonal witness is non-classical; `logical_depth` is not the figure of merit | CriticalQuantumLife |
| **CriticalQuantumLife** (this project) | [`../`](../) | **Closed-loop + criticality + interactive + certified** | A contingently-fed quantum population minimizes surprise toward a critical set-point, recovers from a poke, and holds the witness above null | **PARTIAL, 2/3 gates**: Quantum ✅, Adaptation ✅ (weak), Criticality ❌ (σ=0.44). See [§11.5](#115-current-status-run-1-numbers) | Criticality gate failed; the "life" has no real-world use yet | **This doc** → Canary + Sandpile |

Sibling infrastructure (not ALife but reused): the QRNG entropy service `qrng_client.py`, the `layout.best_chain` low-error qubit-path picker, and the IBM submission pipeline all originate in the `CalibrationGuidedHighYieldQRNG` project.

Origin paper for all of it: **Alvarez-Rodriguez, Sanz, Lamata, Solano, *Quantum Artificial Life in an IBM Quantum Computer*, Sci. Rep. 8:14793 (2018)** — arXiv:1711.09442. Four Darwinian behaviors (self-replication, mutation, interaction, death) on ~4 qubits of `ibmqx4`.

### 11.2 Glossary (every term, plainly)

- **Genotype / phenotype.** Each individual = 2 qubits: a *genotype* (heritable, copied forward) and a *phenotype* (its expressed state, set from the genotype + environment). From the 2018 model.
- **GHZ genealogy.** The genome qubits are entangled into a GHZ-type state: a founder in `|+⟩` plus a CNOT chain, so all genome qubits share one joint entangled state that is *inherited* across generations.
- **Entanglement witness `⟨X^⊗W⟩`.** The expectation of Pauli-X on *every* genome qubit at once. For a true GHZ it → +1; for any separable/classical population it → `∏⟨X⟩_i ≈ 0`. **The one quantity with no classical surrogate** — the load-bearing "this is really quantum" signal.
- **Classical surrogate / measure-and-resend.** A matched control that runs the identical mutate/select/reproduce loop but measures and re-prepares (destroying entanglement). It defines what a classical device *could* fake.
- **Null band `k/√shots`.** The statistical noise floor of the surrogate's witness (k = 3). At 8192 shots ≈ ±0.033; at 4096 shots ≈ ±0.047. A witness **above the band** is certified non-classical.
- **Yoked control.** The adaptation baseline: same stimulation multiset as the closed loop, but feedback **scrambled / non-contingent**. Separates "the population learned" from "the population just moved."
- **Closed loop (contingent feedback).** Predicted outcomes get predictable feedback; surprising outcomes get high-entropy (QRNG-seeded) feedback. Per the Free Energy Principle the population reorganizes to minimize its own surprise (active inference / DishBrain analogy).
- **Option A / "witness-as-outcome."** A load-bearing F0 discovery: because the GHZ's single-qubit marginals are maximally mixed, **every single-qubit observable is invariant** under local mutation — information lives *only* in the joint witness. So the per-generation "outcome" is the discretized `witness_signal = joint − separable`, binned into `nbins = 10` over [−1, 1].
- **Surprise proxy.** `−log P(bin)`: the negative log-likelihood of the observed witness-bin under an exponentially-decayed (decay 0.8, Laplace-smoothed) running distribution. High surprise = unexpected outcome.
- **Branching σ.** The branching ratio of the surprise-activity process; **σ = 1 is the critical point** (each active generation triggers on average one more). σ < 1 = subcritical/frozen; σ > 1 = supercritical/chaotic.
- **Avalanche α.** Avalanches = contiguous runs of above-median-surprise generations; their size distribution `P(S) ∝ S^{−α}`; **α ≈ 1.5** is the critical (Beggs–Plenz / mean-field) signature.
- **Entropy plateau.** A lively system's outcome entropy stays high (plateau); a dead one collapses to 0.
- **Relaxation τ.** After a poke, how fast surprise decays back to baseline. Degenerate if there's no clean decay.
- **Poke.** A human/scheduled perturbation mid-run. Three kinds ([§11.4](#114-the-interactive-layer-pokes-f4)): `flip_expected`, `inject_stimulus`, `alter_selection`.
- **Death (Lindblad vs unitary).** The 2018 aging channel is amplitude damping (a real Lindblad dissipator). On this engine, **damping decoheres the witness to ≈0**, so runs use `--death=unitary` (a σ_y stand-in) to keep the witness alive.
- **Absorbing state / directed percolation (DP).** The "dead"/quiescent configuration the dynamics can fall into and never leave; the transition into it (as a rate is tuned) is in the **directed-percolation** universality class. Central to the Sandpile ([§11.8](#118-study-b-the-quantum-sandpile-the-2-hour-science-swing)).
- **MIPT.** Measurement-induced phase transition: monitored circuits switch between volume-law and area-law entanglement as the measurement rate crosses a critical value.
- **SOC.** Self-organized criticality: a system reaches the critical point **by itself**, with no fine-tuning, via slow-drive + fast-dissipation feedback (Bak–Tang–Wiesenfeld; Dickman et al.).

### 11.3 The engine — one generation, operation by operation

Code: [`../code/closed_loop.py`](../code/closed_loop.py) (F0 engine, forks `../../artificial-life/code/stage4_qalife.py`). Load-bearing defaults: `--death=unitary`, `DEFAULT_MUT = 0.60`, `nbins = 10`. Each generation `k` runs one real circuit on hardware (or Aer for drafts):

1. **Founder.** Genome qubit 0 ← `Ry(π/2)` → `|+⟩`. (Seeds the GHZ.)
2. **Self-replication.** `CX(g_{k−1} → g_k)`: copy the previous genome into the new one — this is the CNOT chain that grows the GHZ across the lineage. (No-cloning ⇒ the copy is imperfect ⇒ built-in variation.)
3. **Mutation.** `Ry(θ_k)` on the new genome, `θ_k` drawn from the **certified QRNG** stream (`qrng_client.py`, fail-closed). This is the only non-Clifford knob and the main variation source; `mut_scale` sets its spread.
4. **Phenotype.** `CX(g_k → p_k)`: express the genotype into its phenotype qubit.
5. **Interaction (predation).** `SWAP(p_k, p_j)` between phenotypes that share a grid cell — exchanges expressed state; gives short-lived individuals an advantage (2018 predator-prey dynamic).
6. **Death.** `unitary` σ_y stand-in (default) or the full amplitude-damping Lindblad (`CRY + CX + reset(bath)`) — ages/removes individuals.
7. **Readout.** 8192 shots. Compute the **joint** `⟨X^⊗W⟩` and the **separable** `∏⟨X⟩_i`; `witness_signal = joint − separable`.
8. **Outcome + surprise.** Bin `witness_signal` into 10 bins; `surprise = −log P(bin)` under the decayed running distribution.
9. **Feedback (contingency).** Low surprise → predictable feedback; high surprise → QRNG-seeded high-entropy feedback. In the **yoked** arm this mapping is scrambled.
10. **Persist + advance.** Save population genomes, running distribution, generation counter, RNG state, resume args ([`../code/session.py`](../code/session.py)); go to `k+1`.

Data written per generation to [`../research_runs/`](../research_runs) as JSON (counts, witness, surprise, chain-quality) plus the per-generation QPY circuit (`cql_f5_batch{0,1}_{closed,yoked}_gen*.qpy`).

### 11.4 The interactive layer — pokes (F4)

Code: [`../code/session.py`](../code/session.py). A `poke()` changes the system mid-session; state persists across hardware batches so a session truly continues.
- `flip_expected` — invert the contingency (which outcomes count as "expected"). *Demo default.*
- `inject_stimulus` — `Ry(π/2)` coherence scramble on the founder → witness dips → surprise spikes. **This is the kind used in the F5 hardware run**, fired once between batch 0 and batch 1 (poke_gen = 8).
- `alter_selection` — scale explore-pressure baseline (factor 2.0).

### 11.5 Current status (Run-1 numbers)

Backend `ibm_kingston` (156-qubit Heron r2), session `sess_caec0e51`, seed 100, W=6, mut_scale=0.30, 2 batches × 8 gen = 16 gen, poke_gen=8, 8192 shots. Live calibration at emit: 2q err max 0.0058, readout max 0.0192, physical chain `[26,25,37,45,46,47,48,49,38,29,30,31]`. Full log: [`F5-runlog.md`](F5-runlog.md); report: [`../research_runs/cql_f5_report.json`](../research_runs/cql_f5_report.json).

| Metric | Value | Gate |
|---|---|---|
| `adaptation_gap.gap` | **+0.161** (closed drop 0.375, yoked drop 0.214) | ✅ weak |
| `certification.certified` / `frac_above_band` | **true** / **0.938** (15/16; margin mean **+0.338**, min −0.034, band ±0.033) | ✅ |
| `criticality.sigma.mean` | **0.438** (ci95 [0.19, 0.75]) | ❌ subcritical |
| `criticality.avalanche_alpha` | **None** (too few avalanches at 16 gen) | ❌ |
| `relaxation_tau.tau` | **34740** (r² 0.54, degenerate) | ❌ |

**Verdict: certified-quantum + adaptive, NOT critical.** Run-2 (`--seed 200`) not executed — QC budget exhausted.

### 11.6 The three honesty gates (the law)

Epic rule: no "alive/lively/learning" claim in code, web, or paper unless traced to a **passed** gate. Defined in [`epic-critical-quantum-life.md`](epic-critical-quantum-life.md); thresholds in [`../code/draft_gate.py`](../code/draft_gate.py) (F1: `ADAPT_MIN = 0.15` nats, `SIGMA_DEAD = 0.3`, poke relax 50%/4 gen).

1. **Adaptation gate** — closed surprise falls where yoked does not. *Refuted if* no gap. **Status: ✅ weak (+0.161).**
2. **Criticality gate** — settles at σ≈1, α≈1.5, entropy plateau. *Refuted if* H→0 (dead) or chaos. **Status: ❌ (σ=0.44). ← the Sandpile fixes this.**
3. **Quantum gate** — `⟨X^⊗W⟩` above the classical null. *Refuted if* witness ≤ band. **Status: ✅ (15/16, +0.338). ← the Canary uses this.**

### 11.7 Study A — the Canary (the shippable product)

Full rationale: [§9](#9-final-pick--one-winner-the-quantum-canary-b1). One-line: an **entanglement-native, always-on QPU health monitor**. It needs **no unmet gate** — it runs on the quantum gate that already passed and treats σ=0.44 homeostasis as a feature.

**How it works, in detail:**
- **Probe.** The F0 engine at small W (4–8) on a spare qubit chain, one short circuit per cycle, interleaved with the provider's calibration cadence or user idle time.
- **Signals.** Each cycle emit `witness_margin`, `surprise`, `sigma`, `adaptation_gap`, `avalanche_rate`, plus the raw chain-quality (`twoq_err`, `readout_err`) already computed in [`../code/hardware_batches.py`](../code/hardware_batches.py), as **Prometheus/OpenMetrics** text.
- **Dashboard.** A Grafana panel, or [`../web/spectacle.html`](../web/spectacle.html) wired to [`../research_runs/`](../research_runs): the living heartbeat + a drift/anomaly timeline. (The poke → "inject drift"; the yoked ghost → the baseline.)
- **Alert.** Witness below the null band for N cycles, or surprise exceeding the yoked baseline by k·σ → page / trigger recalibration.
- **The study (validation).** Inject known faults on hardware — detune a qubit, raise readout error, force a stale calibration, degrade mid-circuit-measurement fidelity, add feed-forward latency — and show the Canary flags each **earlier or more specifically** than randomized benchmarking + coherence tracking. Deliverable = a **coverage map** (where it wins: entanglement collapse, dynamic-circuit faults; where it ties: single-qubit T1).
- **Why it's honest:** no speed claim, no classical-hardness assumption; judged on sensitivity + coverage.
- **File to write:** `feature-F8-quantum-canary.md` (exporter, fault-injection harness, coverage experiment, alert rule, acceptance criteria).

### 11.8 Study B — the Quantum Sandpile (the 2-hour science swing)

Full rationale: [§10](#10-the-2-hour-experiment--one-idea-waiting-to-be-tested-the-quantum-sandpile). One-line: **self-organize a monitored circuit to its own absorbing-state (directed-percolation) critical point** — the self-tuned counterpart to the *hand-tuned* transition of arXiv:2512.07966. **This is the study that fixes the failed criticality gate**, because SOC reaches criticality *by design* instead of by luck.

**The mechanism (Dickman et al. 1998): SOC = absorbing-state transition + slow-drive/fast-dissipation.** Per time-step on a W≈20–30 chain:
1. **Spread** — one brick-wall layer of 2-qubit entangling gates (activity spreads to neighbors).
2. **Dissipate** — mid-circuit measure each site + feed-forward conditional reset toward `|0⟩` (the absorbing/"dead" state). This is the fast relaxation.
3. **Drive-when-quiet (the SOC trick)** — read global activity `A` = number of non-`|0⟩` sites from the mid-circuit record; **if `A = 0`, inject exactly one "grain"** (feed-forward `X`/`Ry` on one random site); **else do nothing.** No measurement rate is set by hand — the system chooses its own operating point.
4. Repeat for T steps; log the activity time-series.

**Readouts (your F2 suite is exactly the DP order parameter):** activity density self-parks at the critical density; avalanches `P(S) ∝ S^{−α}` with α ≈ 1.5; branching σ → 1. **Certify** with the genealogical witness above the classical null → the self-organized critical state is genuinely quantum. **Control:** a **yoked drive** (same average grain rate, injected at *random* times regardless of quiescence) should **not** self-tune — that single contrast is the whole claim.

- **Decisive & 2-hour-feasible:** binary outcome; W≈20–30, shallow depth, a few hundred–thousand executions.
- **Headline if it works:** *first self-organized (self-tuned) absorbing-state critical point on a quantum processor, certified quantum.*
- **File to write:** `feature-F9-quantum-sandpile.md` (per-step circuit builder, drive-when-quiet feed-forward, DP finite-size analysis, yoked-drive control, acceptance criteria).

### 11.9 How the two combine into one full thesis

Title: *Self-Organized Certified Quantum Life — from an entanglement-inheritance certificate to a self-tuning critical monitor of quantum hardware.* One engine, three chapters, each closing one gate:

- **Ch. 1 — The certificate (done).** Engine + witness `⟨X^⊗W⟩` above the null on hardware ([§11.3](#113-the-engine--one-generation-operation-by-operation), [§11.5](#115-current-status-run-1-numbers)). *Closes the quantum gate.*
- **Ch. 2 — Self-organization (Sandpile, [§11.8](#118-study-b-the-quantum-sandpile-the-2-hour-science-swing)).** Drive-when-quiet + dissipation self-tunes the processor to the DP critical point; certified quantum; proven by the yoked-drive control. *Closes the criticality gate — the physics contribution.*
- **Ch. 3 — The application (Canary, [§11.7](#117-study-a--the-canary-the-shippable-product)).** The same certified, self-organizing apparatus deployed as an always-on entanglement + dynamic-circuit health monitor; validated by fault-injection. *The impact chapter.*
- **Spine:** the three honesty gates ([§11.6](#116-the-three-honesty-gates-the-law)) as method; the failed Run-1 reported honestly, then *resolved* by Ch. 2.

The discovery and the application run on the **same code**: the Sandpile's self-organizing loop *is* the Canary's monitoring loop; the witness that certifies the critical state *is* the health signal.

### 11.10 Next steps — ordered checklist

1. **Decide the thesis frame** = the three-chapter arc ([§11.9](#119-how-the-two-combine-into-one-full-thesis)). Fold into a new `feature-F7-thesis.md` (currently F7 has no plan file).
2. **Write `feature-F8-quantum-canary.md`** — the shippable product; lowest risk, no unmet gate. Start here.
3. **Build the Canary exporter** — wrap the F0 engine (small W, spare chain) with a Prometheus/OpenMetrics endpoint sourced from [`../research_runs/`](../research_runs) metrics. No new physics.
4. **Build the fault-injection harness + run the coverage study** — mostly in Aer with injected noise; a small hardware confirmation when budget allows.
5. **Rewire [`../web/spectacle.html`](../web/spectacle.html) into the ops console** — poke → "inject drift", heartbeat → live health trace, add the drift/anomaly timeline.
6. **Write `feature-F9-quantum-sandpile.md`** and, when a ~2-hour Heron window is available, **run the Sandpile** — the decisive science swing that closes the criticality gate.
7. **Fix the reservoir technical forks if pursuing the QRC lane later** ([§5](#5-recommended-path-do-this)): brick-wall entangler l≈7–10, k-body correlator readout, add SFF/level-spacing + `C_Σ`/NARMA metrics.

### 11.11 Index — all links

**Plans:** [epic](epic-critical-quantum-life.md) · [thesis-5](thesis-5-critical-quantum-life.md) · [F0](feature-F0-closed-loop-engine.md) · [F1](feature-F1-draft-gate.md) · [F3](feature-F3-certify.md) · [F5 runlog](F5-runlog.md) · this doc.
**Code:** [closed_loop.py](../code/closed_loop.py) · [draft_gate.py](../code/draft_gate.py) · [criticality.py](../code/criticality.py) · [certify.py](../code/certify.py) · [session.py](../code/session.py) · [hardware_batches.py](../code/hardware_batches.py) · [submit_batch.py](../code/submit_batch.py) · [run_research.py](../code/run_research.py).
**Web:** [spectacle.html](../web/spectacle.html) · [concept_mockups.html](../web/concept_mockups.html).
**Data:** [research_runs/](../research_runs).
**Predecessors:** [artificial-life](../../artificial-life) · [QuantumLife](../../QuantumLife).
**Key external:** 2018 origin arXiv:1711.09442 · tuned DP transition arXiv:2512.07966 · IBM adaptive circuits arXiv:2509.18259 · SOC-as-absorbing-state cond-mat/9712115 · QRC edge arXiv:2506.17547 · feedback QRC arXiv:2406.15783.
