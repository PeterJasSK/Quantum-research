# Idea — QeMCMC on LABS: does a quantum proposal need fewer steps to find and sample good binary codes, how does the saving scale with code length, and where does noise kill it?

**Tag: QUANTUM · QHop · effort: high · QC: yes (ideal simulation arm + small IBM Heron calibration arm) · civil use only (sponsor: Inovačné centrum Košického kraja)**
Drafted 2026-11-21, revised 2026-11-21 after the QHop applied review `QHop/plans/qmcmc-applied-review.txt`
(row B4-15; Sections 7, 9, 11; experiments D1–D9, red team E1–E3). Every number quoted from the review is ideal
(noiseless) simulation unless marked otherwise.

---

## 1. The idea in plain words

**The problem.** A radar, sonar or ultrasound transmitter sends a short pattern of signs, e.g. `+ + + − − + −`
(a *code*), and looks for its echo. A good code gives one sharp peak where the object is and almost nothing elsewhere.
The small leftover peaks (*sidelobes*) are ghost echoes. **LABS** (Low Autocorrelation Binary Sequences) is the
problem of finding codes with the smallest sidelobes. Energy of a code s ∈ {±1}^N: E(s) = Σ_k C_k(s)², with
C_k = Σ_i s_i s_{i+k}. There are 2^N codes; the landscape is glassy ("golf course"): many fairly good codes far apart,
and flipping one sign at a time gets stuck. The best codes are known up to N = 66, so answers can be checked exactly.

**MCMC** is a random walk over codes: propose a change, keep it if better, keep it sometimes if worse (temperature T).
At **low temperature** it concentrates on the best codes, and that is where single-flip walks get trapped.

**QeMCMC** (quantum-enhanced MCMC, Layden et al. 2023) changes only the *proposal*: a quantum computer proposes a
whole new code, biased towards good codes even far from the current one; a classical computer accepts or rejects it
with the Metropolis rule. The samples stay correct because the check is classical. Noise only slows the chain, if
circuits are twirled and palindromic (T1 and readout noise otherwise bias it; review D3, V12).

**What we measure.** *How many energy evaluations each method needs* (to reach the optimal code, and per new
independent low-temperature code) as code length N grows. If the quantum count grows with a smaller exponent than the
best classical method, the saving grows with N. Two curves follow: the code length where the quantum computer would
pay off in time (n\*), and the code length where noise erases the saving (n_fail), as a function of hardware error.

**Why this is the right continuation.** It answers the open questions named in the original papers: P1 (how the
speedup and growing noise combine at larger n is "currently unknown"; no parallel-tempering baseline), P2 ("level and
types of noise under which we maintain the quantum scaling advantage is an important open question"), and Layden's
call for an engineering application with hard, well-defined step counts compared against classical.

**Why low temperature, and what that means for the application.** The review found a step advantage ONLY at low
temperature: none at high T (0.9–1.3x vs the best classical mixture, D1) and parity with exact cluster moves at medium T
(E1). So the study runs at low T: finding and sampling the best codes. Car-radar "every car draws its own code" needs
*variety*, i.e. higher T, where no advantage was measured. Car radar, sonar and ultrasound are therefore the
**motivation** (why good codes matter), not the claim. Whether a fairness claim can be made at all is decided by Gate 0.

One sentence: *the quantum computer proposes bold jumps between good codes, a classical computer checks them, and we
measure whether this saves steps at low temperature, how the saving scales with code length, and at which hardware
error rate it disappears.*

---

## 2. Research question, hypothesis, contribution

**Research question (unchanged).** For fair sampling of low-sidelobe binary codes (LABS energy, fixed temperature),
does the number of energy evaluations per independent good code scale with a smaller exponent for QeMCMC than for the
best classical samplers, and what hardware error rate keeps that exponent difference alive up to practical code lengths?

**Hypothesis.** At low temperature (below the LABS glass crossover found in Gate 0), the ideal QeMCMC step count grows
with a smaller exponent than tuned parallel tempering (Δk > 0). Support so far is indirect: on SK at fixed n = 12–14, one
quantum step is worth 8–18 classical flips against tuned PT at low T (review D2), and the low-T SK gap exponent is
0.35 vs 0.82 for the best classical mixture (D1, n ≤ 11). **The exponent on LABS is unmeasured.** On hardware, the
saving shrinks as S_noisy ≈ 1 + (S_ideal − 1)·F^a with F the circuit fidelity and a ≈ 1 (D3), so n_fail is set by
circuit depth.

**Novel contribution (ordered by strength; prior art checked 2026-11-21, repeat before writing):**
1. First comparison of QeMCMC against **tuned parallel tempering** on **fitted step exponents with confidence
   intervals** (P1 excluded PT; P2 used local/uniform only; Ferguson & Wallden 2026 count proposals but fit no exponent).
2. The **noise-failure curve** n_fail(ε): the code length at which the step saving disappears as a function of
   two-qubit error, from a noise model anchored by hardware tomography — the measurement P2 names as open.
3. Both turned into code lengths: **n\*** (break-even in time) and **n_fail** (noise), plotted on one figure with CIs.
4. QeMCMC with an exact accept step on LABS (weakest alone: quantum-for-LABS is an active area; see Section 6).

---

## 3. Metrics (hard numbers, not the spectral gap)

All costs are counted in **energy evaluations** (one Metropolis accept/reject = one evaluation, for every method;
parallel-tempering replicas and swaps counted in full).

| Metric | Definition | Engineering meaning |
|---|---|---|
| N_code(N) | energy evaluations per new independent code with peak sidelobe ≤ target, at fixed T (from IAT and burn-in: t_eq + 2·τ·Var/ε²) | cost of issuing one good code |
| TV(N, steps) | total-variation distance of the sampled code distribution to the exact Boltzmann distribution (exact enumeration up to N ≈ 24) | is the sampler correct? |
| P_collision | Σ p(s)² = 2^(−H₂), H₂ = collision (Rényi-2) entropy of the sampled distribution vs exact | chance two independent users draw the same code (secondary; meaningful only if Gate 0 passes) |
| k_method | fit N_code(N) ≈ c·2^(k·N), bootstrap 95 % CI, split fits (low half vs high half of the N range) | scaling of cost with code length |
| Δk, n\* | k_classical − k_quantum; crossover length for S\* from IBM latency | from which code length quantum pays off |
| ε_req / n_fail | 2q error at which the noisy saving reaches 1; code length where it does at today's error | how good hardware must become |
| TTS99 | evaluations to hit the optimal code with 99 % probability | comparability with the LABS optimisation literature (memetic tabu 1.34^N) |

---

## 4. Method

### 4.1 Gates (run in this order; each can stop the project or change its claim)

| Gate | What | Cost | Pass rule | If it fails |
|---|---|---|---|---|
| **G0 Temperature** | Exact thermodynamics for LABS N = 8–24 (2^24 energies enumerable): specific-heat peak, overlap distribution, temperature where the single-flip gap collapses → T_glass(N). Also T_code: the T at which sampled codes meet a target merit factor / peak sidelobe with a useful fraction. | 2–3 CPU days | the study T is below T_glass (LOW) for N ≥ 12 | if LABS shows no low-T trapping at these N: stop. If T_code is MEDIUM/HIGH: drop P_collision and every fairness claim; keep the low-T scaling study only |
| **G1 Step gain exists** | Exact gaps N ≤ 12–14 at the G0 low temperature: QeMCMC vs best classical (tuned local+uniform mixture, exact 2–4-spin block heat-bath, tuned PT by IAT) | ~2 CPU days | median S ≥ 1.5 vs the best classical at N = 12–14 | stop: "no LABS step gain vs strong classical moves" (E3 found ties at SK n = 6–8 against small block heat-bath) |
| **G2 Not just classical** | Tensor-network (MPS/TEBD) emulation of the same proposal, bond dimension χ ≤ 8 (Christmann et al. 2025); decohered control | ~2 CPU days | quantum beats MPS χ ≤ 8 by ≥ 1.5x and the decohered control by ≥ 2x | label the result QUANTUM-INSPIRED ONLY |
| **G3 Scaling** | IAT / TTS99 runs N = 8 … 18–20 (Section 4.2), fit Δk with CI | 1–2 CPU weeks, unloaded machine | 95 % CI of Δk(ideal) excludes 0 | report "per-step advantage does not scale on LABS" (still the paper) |
| **G4 Hardware bias** | Tomography N ≤ 6–8, bare vs V12 fixes (Section 4.3) | ~$126–500 QPU | V12 removes the measured bias within error | report as hardware failure of the sampler |

### 4.2 Simulation arm (ideal, exact ground truth) — the core

- **Sizes.** Exact spectral gaps N ≤ 14 (full proposal matrix); IAT and TTS99 by direct simulation N = 8 … 18–20.
  N = 22–24 is out of reach for chains (quantum proposals cost 0.65 s at n = 16 and 3.2 s at n = 18 on a loaded
  machine, D2; N = 24 would be minutes per proposal). Exact enumeration (2^24) is still used for G0 thermodynamics and
  TV checks.
- **Machine.** Unloaded; at most 2 processes per run family (the review lost runs to a 73-process overload).
- **Samplers (classical side, all mandatory):**
  single-flip Metropolis; **tuned parallel tempering** (ladder re-spaced to 20–30 % swap acceptance, D2 code);
  **exact small-block heat-bath** (2–4 spins, the move that tied QeMCMC at SK n = 6–8, E3); **random-restart greedy /
  memetic tabu** (TTS only); **rejection / random-restart sampling** of codes below a merit-factor threshold (only for the
  fairness metric, if G0 passes); **MPS/TEBD proposal χ ≤ 8** (G2).
- **Samplers (quantum side):** QeMCMC with the full 4-body LABS energy in the proposal (Layden parameters, plus a small
  γ, t grid reported in full — oracle tuning gained only 1.2–1.6x in D1); optional adiabatic-dressed proposal
  (Hsieh–Orfi–Sels); **Kale–Basu transverse-field quench** as a non-chain arm (if the reference verifies, Section 6).
  Side arm only: 2-body surrogate in the proposal, true energy in the accept (exact by review G1, but approximate-model
  and native-coupling proposals lost to classical methods using the same information in D5, E2, E3).
- **Proposal simulation.** Statevector by Chebyshev propagation (reuse `QHop/experiments/qmcmc/D2-pt-quantum-move/ckern.c`)
  with the LABS energy as the diagonal; decohered control from `common/qmc.py`.
- **SK control arm.** Same pipeline on SK at n = 12–20 (review Section 11 "LOW-T scaling"), so results connect to P1/P2.

### 4.3 Hardware arm (IBM Heron) — calibration, not advantage

Gate cost per Trotter step, all-to-all CNOT count (own count):

| N | 2-body terms | 4-body terms | CNOT / step |
|---|---|---|---|
| 6 | 6 | 7 | 54 |
| 8 | 12 | 22 | 156 |
| 12 | 30 | 95 | 630 |
| 16 | 56 | 252 | 1 624 |

Trotter steps needed grow with evolution time (D4 on SK: r ≈ 5 / 17 / 43 / 86 at t = 2 / 6 / 12 / 20 for TVD 0.05).
Rough fidelity before real transpilation (routing ×1.5 with a swap network, D4; ε = 2e-3): N = 6, t = 2 → ~400 CNOT,
F ≈ 0.45; N = 8, t = 2 → ~1 200 CNOT, F ≈ 0.1; at t = 6 both fall below 0.1. **Replace these with real transpilation
(D4 pipeline) before any QPU booking.**

- **N ≤ 6 (8 if fidelity allows): full proposal tomography** over all start states (K0 pipeline), exact convergence
  computed offline. Three circuit variants: bare; Pauli twirl + palindromic schedule; + readout flip sandwich (review
  V12). Cost ~$126 at n = 8 (E3), ~$100–500 total with repeats.
- **What it measures:** proposal asymmetry, stationary bias (plain vs fixed), and the fidelity F that anchors the noise
  law S_noisy ≈ 1 + (S_ideal − 1)·F^a.
- **Not done:** live sequential chains at N = 10–16. At today's fidelity the proposal there is close to uniform, so they
  would measure noise collapse, not advantage (D3: calibrated Heron noise removes the n = 6 gain; E3: a 1 000-step live
  chain is uninterpretable at $1.6k–4.8k).
- Dry runs first (2–3 min, small per-circuit sizes), same convention as earlier projects.

### 4.4 Analysis

- k per method with bootstrap 95 % CI and split fits; Δk vs tuned PT, vs block heat-bath, vs MPS proposal.
- **n\*** = log2(S\*/S(n₀))/Δk + n₀ with S\* = quantum step time / classical step time (IBM optimistic 2 s, realistic
  3 s; classical ~10–100 ns per LABS evaluation, incremental O(N)). Reported with its CI propagated from Δk, plus the
  warning that exponents fitted on small N were unstable in the review except at low T (D1).
- **n_fail(ε)** from the noise law with N_2q(N) from transpilation (dense problems grew as ~n^2.5 in D4; LABS 4-body
  grows faster, ~N^3 terms).
- **One figure:** n\* and n_fail(ε) vs two-qubit error. If the two curves do not overlap at any reachable ε, that is the
  result: the step saving is real in ideal simulation but cannot be cashed in before fault tolerance.

### 4.5 Demo (mechanism only)

N = 64 code, classical chain over all 64 bits, quantum **lens** proposing moves on a 10–12-bit block with the rest
frozen as an effective field (same lens as the QHop game). Runs on a simulator and, batched, on IBM; samples stay correct.
**Labelled "demonstration of the mechanism, no advantage":** a group move is at most 2x better per step than exact
classical heat-bath on the same block (review G4, proved and red-teamed), and a 12-bit block costs ~4 000 classical
evaluations (microseconds). A full N = 64 quantum proposal is impossible: 2^64 amplitudes to simulate, and millions of
two-qubit gates on hardware (F ≈ 0).

---

## 5. Other application ideas (same method, same math)

| # | Idea | Why it matters | Fit |
|---|---|---|---|
| 1 | **Radar / sonar pulse codes (motivation)** | good codes remove ghost echoes | LABS energy directly; low-T = best codes |
| 2 | Car radar interference (many cars, uncoordinated code choice) | fairness of random code choice | **only if Gate 0 shows the needed T is LOW**; otherwise drop — variety lives at higher T where no advantage was measured, and random-restart sampling is the fair baseline |
| 3 | Medical ultrasound coded excitation (multi-transmit code sets, auto- + cross-correlation energy; 2 codes × N = 10 = 20 spins) | ghost echoes along depth | optional chapter; health link (UPJŠ medical faculty / Košice university hospital); a fixed best set often suffices, so sampling need is weak; prior art to check |
| 4 | Ultrasonic non-destructive testing of steel and welds (coded excitation) | better signal at safe power | regional-industry demo; same weakness as #3 |
| 5 | Expensive-energy variant: score codes by full imaging / EM simulation (seconds per call) | steps = wall-clock directly | side arm only; review D5/E2: classical delayed acceptance on the same surrogate matches at n ≤ 10 |

Civil only: no low-probability-of-intercept or other defence framing anywhere (title, abstract, citations).

---

## 6. Closest references and how we must beat each

| # | Reference | What they did | What they did NOT do | How we beat / use it |
|---|---|---|---|---|
| 1 | Layden et al., Nature 619, 282 (2023), arXiv:2203.12497 | QeMCMC; spectral gap exponent k_q ≈ 0.26 vs ≈ 0.95 (local/uniform), SK, n ≤ 10; hardware n = 8–10 run offline | no steps/IAT/wall-clock metric; no parallel tempering (excluded); no application | same proposal, but hard step metric, tuned PT baseline, real problem, noise-failure curve |
| 2 | Ferguson & Wallden, PRR 7, 013231 (2025), arXiv:2405.04247 | coarse-grained QeMCMC with √n qubits; gap exponents n ≤ 10 | baselines local/uniform only; noise named "important open question" | answer the noise question with n_fail(ε) on a real problem; note the review's 2x block heat-bath bound on group moves |
| 3 | Ferguson & Wallden, arXiv:2602.01353 (2026) | QeSA / QePT on SK; **effort N_0.99 counted in proposals** (closest metric to ours) | n ≤ 10; SA and plain PT only; **no exponent fitted** ("form of scaling not clear"); optimisation, not sampling | N up to 18–20, tuned PT + block heat-bath + MPS adversary, fitted Δk with CI |
| 4 | Kale & Basu, arXiv:2611.19301 (Nov 2026) — **NOT verified by the review team; check it exists and what it claims before citing** | LABS / Bernasconi; transverse-field quench from deep local minima; escape yield per energy evaluation 12–35× vs tabu, N = 20–30 (GPU statevector) | not a Markov chain (no accept step); "constant-factor improvement", no exponent; no PT baseline | include their quench as an arm; compare chain vs quench on scaling; closest competitor, scoop risk |
| 5 | Shaydulin et al., Science Advances (2024), arXiv:2308.02342 | QAOA on LABS, noiseless sim to N = 40; TTS scaling 1.46^N, with quantum minimum finding 1.21^N vs memetic tabu 1.34^N | optimisation only, fault-tolerant assumption for QMF | report TTS99 exponent of QeMCMC next to these numbers; main claim is step scaling of a chain vs PT |
| 6 | Christmann, Ivashkov, Chiurco, Mazzola, PRA 111, 042615 (2025), arXiv:2411.17821 | MPS/TEBD classical emulation of the proposal keeps k ≈ 0.23 up to n = 9 | baselines local/uniform; T = 1 SK only | **mandatory adversary (Gate G2)**; if it matches, the result is quantum-inspired only |
| 7 | Orfi & Sels, arXiv:2403.03087 and arXiv:2408.07881 (2024) | bounds: no generic advantage; advantage needs fine-tuned, non-ergodic quench | no application, no hardware | use to choose γ, t; test whether LABS lies in the good regime |
| 8 | Hsieh, Orfi, Sels, arXiv:2603.28076 (2026) | adiabatic dressing improves gap scaling (SK k 0.61 → 0.12–0.15) | gap only, ED n ≤ 12 | optional stronger proposal arm; measure if the gain survives in steps |
| 9 | Marshall et al. (IBM), arXiv:2602.06171 (2026) | largest hardware QeMCMC (+ warm-start QAOA + PT), MIS up to 117 qubits | weak baselines; CPLEX solves the instances; optimisation | strong baselines; hardware used for calibration, not claimed advantage |
| 10 | Mazumder & Towe, arXiv:2607.09893 (2026) | effective-sample-size ratio vs Gibbs/block Gibbs/PT on small MRFs; PT closes the gap; no wall-clock advantage | not Layden QeMCMC | methodological precedent for ESS vs PT; cite as the honest-benchmark standard we follow |
| 11 | Incudini & Mazzola, arXiv:2607.22818 (2026) | fault-tolerant quantum walk with the Layden proposal; crossover vs CPU/GPU estimated | NISQ QeMCMC called a "quantum-assisted classical chain" | our n\* / n_fail is the NISQ-chain counterpart of their fault-tolerant crossover |
| 12 | Bošković, Brglez, Brest, arXiv:1406.5301; Packebusch & Mertens, J. Phys. A 49, 165001 (2016) (verify) | classical LABS solvers, runtime predictions; optimal codes up to N = 66 | sampling not studied | classical ground truth and solver scaling for TTS |
| 13 | Quantum-seeded memetic tabu on LABS, arXiv:2511.04553 (preprint) | quantum seeds for MTS, ~1.24^N | not a chain, no PT baseline | cite; reduces novelty of "quantum for LABS", not of the step-exponent comparison |
| 14 | Automotive radar interference / PMCW literature (to collect, civil sources only) | interference mitigation, code assignment | quantum sampling | grounds the motivation; only needed for the fairness claim if Gate 0 passes |

Full notes on most of these: `QHop/experiments/qmcmc/_reports/A3-literature.txt`. Before writing, repeat targeted
searches: "QeMCMC LABS", "Bernasconi quantum MCMC", "quantum-enhanced parallel tempering autocorrelation", and verify
Kale & Basu.

---

## 7. Connection to what already exists

- Review and all D/E experiments: `QHop/plans/qmcmc-applied-review.txt`, `QHop/experiments/qmcmc/`.
- Harness: `QHop/experiments/qmcmc/common/qmc.py`; Chebyshev statevector proposals + PT: `D2-pt-quantum-move/`
  (`ckern.c`, `d2lib.py`).
- Gap exponents (SK, LOW: Layden 0.35 vs best mixture 0.82): `D1-temperature-map/`; IAT step advantage vs tuned PT
  (LOW 8–18 at n = 12–14): `D2-pt-quantum-move/`.
- Strong small-move baselines (block heat-bath ties at n = 6–8): `E3-redteam-hardware/`; 2x group-move bound:
  `D7-quantum-inspired-cg/`, `E2-redteam-costmodel/`.
- Noise law and symmetry fixes (V12, G1, G2): `D3-noise/`, `B7-checks/`; transpilation cost and r(t): `D4-compilation/`;
  hardware tomography costs: `E3-redteam-hardware/`.
- Fake backends / job helpers: `QuantumPhantoms/code/common/`.

---

## 8. Sponsor angle (Inovačné centrum Košického kraja)

Civil, regional, university–industry: better radar, sonar and ultrasound codes; Slovak automotive and medical-imaging
links; optional health chapter (ultrasound) and industry demo (steel NDT). Pitch line: *"How many computer operations
does it take to find the best radar codes? We measure whether a quantum computer reduces that count, how the saving
grows with code length, and how good quantum hardware must become for it to pay off — with calibration runs on real
IBM quantum computers and a live 64-bit demonstration of the method."* A regional partner (TUKE radio/automotive
electronics group, or an automotive supplier) strengthens the case — to be confirmed; ICKK's current priority list was
not found online.

---

## 9. Venue and timeline

IEEE Quantum Week (QCE) 2027 technical paper (applications / algorithms track); poster or workshop paper as fallback.
2027 deadlines not yet published (2025: abstract 24 Mar, paper 31 Mar) → plan for mid-March 2027.

| Weeks | Work |
|---|---|
| 1 | G0 temperature gate; prior-art re-check (Kale & Basu) |
| 2 | G1 exact gaps N ≤ 14 vs strong classical; G2 MPS adversary |
| 3–5 | G3 scaling runs N = 8 … 18–20 (unloaded machine), SK control arm |
| 5–6 | transpilation (D4 pipeline), hardware tomography N ≤ 6–8 (G4) |
| 7 | noise law fit, n\* / n_fail figure, demo |
| 8 | writing; arXiv preprint before submission (scoop risk: Kale & Basu, Ferguson & Wallden are active) |

## 10. Bull / Bear / Likely / Value if null

**Bull:** G0–G2 pass; Δk > 0 vs tuned PT with a CI excluding 0; quantum beats the MPS adversary; tomography confirms the
noise law and V12 removes the bias; a clean n\* / n_fail figure. Strong QCE paper.
**Bear:** LABS at reachable N shows ties with small block heat-bath (G1 fails) or the MPS proposal matches (G2), so the
result is classical or quantum-inspired.
**Likely:** a positive Δk in ideal simulation with a wide CI; n\* in the tens to ~100 while n_fail at today's error is
below 10, i.e. the curves do not overlap before fault tolerance; V12 removes the measured bias.
**Value if null:** "on a real engineering problem, with a hard step metric and strong baselines, the per-step quantum
advantage does not scale (or is reproduced classically) — and here is the hardware requirement if it ever should" —
exactly the evaluation the QeMCMC line has been missing.

 Najlepší prípad. Všetky úvodné kontroly prejdú. Kvantový počítač potrebuje menej krokov ako najlepšia bežná klasická metóda a táto úspora rastie s dĺžkou kódu. Neporazí ho ani šikovná klasická napodobenina kvantového výpočtu. Merania na skutočnom kvantovom  
  počítači potvrdia, ako šum uberá z výhody, a naše opravy odstránia skreslenie výsledkov. Vyjde z toho čistý obrázok: od akej dĺžky kódu by sa kvantový počítač oplatil a aký kvalitný hardvér na to treba. To je silný článok na konferenciu.                     
                                                                                                                                                                                                                                                                    
  Najhorší prípad. Pri dĺžkach kódov, ktoré vieme odsimulovať, vyjde kvantový návrh len narovnako s jednoduchým klasickým trikom, ktorý naraz poprehadzuje pár znamienok. Alebo ho klasická napodobenina kvantového výpočtu dobehne. Výsledok by potom bol: „dá sa  
  to urobiť aj bez kvantového počítača“.                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                    
  Najpravdepodobnejší výsledok. V ideálnej simulácii bez šumu kvantový návrh ušetrí kroky, ale s veľkou neistotou. Aby sa oplatil aj časovo, potreboval by dosť dlhé kódy. Dnešný šum však výhodu zničí už pri veľmi krátkych kódoch. Tieto dve hranice sa nestretnú
  skôr, než budú existovať kvantové počítače s opravou chýb. Naše opravy pritom skreslenie zo šumu odstránia.                                                                                                                                                       
                                                                                                                                                                                                                                                                    
  Prečo má zmysel aj neúspech. Aj keby výhoda nerástla s dĺžkou kódu alebo ju dokázal napodobniť bežný počítač, vieme povedať: „Na skutočnom inžinierskom probléme, poctivo merané a proti najsilnejším klasickým metódam, kvantová výhoda nerastie. A takto dobrý  
  by musel byť hardvér, aby raz rástla.“ Presne takéto poctivé zhodnotenie v tejto oblasti doteraz chýba.****
