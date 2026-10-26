# Siemens Idea 8 — Certified Quantum Virtual Cohorts: procedurally generated tumors that nobody chose, with a signed receipt for every virtual patient

**Project name (Siemens / management):** **Quantum Synthetic Cultures — QSC** · *quantum-grown virtual tumors for AI validation, modeled on no real patient.*
**Thesis name (academic / science venue):** **Quantum Phantoms** · *"phantom" is the native imaging term for a synthetic test body with no real original — it invites the right question in a science room.*
*(Honest caveat: both names carry the living-process vision — the MVP only rolls tumors + one division; the full "culture" that grows is step 1 → Section 5.2.5.)*

**Tag: QUANTUM · siemens · effort: medium-high · NO QML**

*(Merges the useful core of `siemens-2` (synthetic imaging data) with the QRNG/certification stack from `qrng-eaas`, and borrows the training-free philosophy of `siemens-6`. Replaces the QML-flavoured parts of `siemens-2`.)*

---

## 1. The concept in one paragraph

A quantum circuit on IBM hardware rolls virtual tumors — and, at full scale, whole virtual patients — from hand-written rules based on published clinical statistics. In the same hardware job, a CHSH test certifies that the outcomes came from genuine quantum measurement. Every generated tumor gets a signed receipt (seed, job ID, calibration snapshot, CHSH value, decoded parameters, code version). Classical tools then insert the tumor into a computational phantom and simulate a CT scan, producing labeled images for training and testing AI detectors such as AI-Rad Companion Chest CT. Anyone can later verify every image: where it came from, that the certificate is valid, and that the whole cohort matches the declared rulebook.

**The one-sentence pitch:** *Classical computers can make fake tumors; only quantum can prove that nobody — including us — picked which ones.*

---

## 2. How it works

### 2.1 Pipeline

| Step | What happens | Who | Quantum? |
|---|---|---|---|
| 1. Rulebook → gate angles | Published nodule statistics (size bands, type, margin, lobe frequencies, correlations) are converted analytically into `Ry` and controlled-`Ry` angles | **You** | Design |
| 2. Quantum job | Tumor/patient qubits + CHSH certificate pairs run in the same job on IBM Heron | **You** | Yes |
| 3. Decode | Measured bits → tumor parameters → 3D lesion shape | **You** | No |
| 4. Sign | Hash + Ed25519 signature + append-only ledger (reuses `qrng-eaas`) | **You** | No |
| 5. Insert and scan | Lesion inserted into a phantom (XCAT); CT simulated (DukeSim / open alternative) | Existing tools | No |
| 6. Verify and audit | Third party checks signature, CHSH > 2, regenerates lesion, audits cohort vs rulebook | **You** | No |
| 7. Use | AI training and testing | Siemens | No |

### 2.2 How a tumor is generated in the circuit

One measurement shot = one tumor. Qubits are grouped into registers, each deciding one property:

- **Size (2 qubits):** four size bands. `Ry` angles set so each band's probability equals its published frequency.
- **Type (2 qubits):** solid / part-solid / ground-glass / calcified. Controlled by the size qubits, so type depends on size as in real data (quantum Bayesian-network style).
- **Margin (2 qubits):** smooth / lobulated / spiculated, conditioned on type.
- **Location (3 qubits):** lung lobe (5 of 8 codes used; remaining codes discarded or remapped).
- **Shape detail (a few qubits after Hadamard):** raw random bits that seed the classical surface deformation.

Roughly 12–14 qubits per tumor plus 2 CHSH qubits.

### 2.3 Why this is NOT quantum machine learning

The test is whether the quantum circuit is trained on data. Here it is not:

- Gate angles are **computed by hand from published clinical numbers**, never optimized against a patient dataset.
- No patient image ever enters the quantum circuit.
- The only ML is downstream (Siemens training a classical detector on the images), outside this pipeline.

**Grey zone to avoid:** do not fit angles to statistics extracted from a private patient dataset. Use published, citable numbers only.

**Side benefit:** because no patient scans go into the generator, it cannot memorize or copy a patient. The memorization problem documented for diffusion models (37.2% of patient data memorized, 68.7% of synthetic samples identified as copies — Dar et al., *Nat. Biomed. Eng.* 2025) disappears at the generation step by design.

### 2.4 Richer tumors — complexity from processes, not qubit count

**This project does not chase a 100-qubit patient.** The richness comes from *composing biological processes* (division, mutation, fate choice, selection, growth) in a hybrid loop that reuses quantum state across a few qubits — not from widening the register. A handful of qubits run through many generations and process steps produces a far more complex tumor than one wide one-shot circuit, and it stays inside the coherence budget current hardware actually has. The emergence is in the *dynamics*, not the width.

Rule: **every quantum feature must have a job.** Features that earn a qubit:

| Feature | Qubits | Job it does |
|---|---|---|
| Patient context (age band, smoking, emphysema) | few | Conditions nodule distributions; real nodules are correlated within a patient |
| Follow-up growth via dynamic circuits | few | Baseline measured mid-circuit, feed-forward sets growth for a later scan; matches AI-Rad Companion's prior-comparison feature |
| CHSH certificate pairs | 2 | Certificate placed beside the generation register |
| Living-process loop (§5.2.5) | ~16–28 | Division/mutation/fate run across generations; **the main source of complexity** |

Build by adding *processes*, not qubits: single nodule (~14 q) → living-process loop (§5.2.5, ~16 q Mode A) → more generations and richer fate rules. Measure cohort drift and the entanglement witness at each step.

---

## 2.5 MVP — first web demo (build this first)

**One line:** a web page showing a grid of real lung-CT slices, each carrying a nodule whose parameters were rolled on real IBM quantum hardware, with a CHSH value stamped on every tile proving the roll was genuinely quantum.

This is the smallest thing that still produces the "wow": a page that looks like a real synthetic-cohort dataset viewer, where the data provably came from a quantum computer. It is deliberately *not* the full pipeline — it exists to show potential fast.

### What the MVP includes

- **Quantum (the minimum that carries a real claim):** a small circuit (~10 qubits) = nodule-property qubits + **one quantum division** (the QALife hint, below) + **one CHSH pair in the same job**, run once on `ibm_heron`. Development runs on `AerSimulator` (free, instant); a single real-hardware job supplies the CHSH value shown in the demo. The honest claim is Tier 1 — *certified-unchosen provenance*: the tumor parameters were sampled from certified quantum measurement, and CHSH > 2 is evidence the measurement was genuinely quantum.
- **Rulebook:** lung-nodule size bands (plus lobe) from published Fleischner / LIDC statistics, converted to `Ry` angles. No training, no patient data (stays non-QML, §2.3).
- **Lesion + image:** decode bits → 3D blob → image-domain insertion into a real LIDC/LUNA16 lung-CT slice with matched noise. **No phantom, no CT physics simulator** — the fully-open fallback path (§10, Path A).
- **Web render:** a static web page (self-contained) displaying the cohort grid, per-tile decoded parameters, per-tile CHSH stamp, and a cohort-vs-rulebook strip (a histogram — no audit/ledger code).

### The QALife hint (the seed of what's coming — in the MVP)

The MVP must not look like a dead end. It carries the smallest possible taste of the living-process arm (§5.2.5): **one quantum division (P1, minimal).** Most grid tiles are independent single nodules, but a few are rendered as **sibling pairs** rolled from one division event:

- A parent carries a genotype qubit (which also drives some nodule properties).
- Division = controlled-copy onto a fresh ancilla plus a small `Ry(θ_mut)`.
- Measuring yields two daughter nodules whose properties are **correlated by shared ancestry** — not two independent PRNG draws.

Visually: two related lesions with a lineage badge. The page copy teases the rest: *"generation 1 — full clonal evolution is the next step."* This is ~2 extra qubits, one division, no selection, no loop. It exists purely to prove the architecture grows into a living tumor, and to put "what's to come" on screen from day one.

```
  ┌── sibling pair, gen 1 ──┐
  │  ▒▓██▓▒      ▒▓█▓▒       │   parent → ⎇ division → 2 daughters
  │  ██◉██       █◉█         │   8.2mm solid | 7.4mm solid
  │  ▒▓██▓▒      ▒▓█▓▒       │   ⎇ shared quantum ancestry
  └─────────────────────────┘   "gen 1 of ∞ — clonal evolution next"
```

### Next step after the MVP — QALife loop, limited capacity

Once the MVP lands, the first real arm is the **§5.2.5 living-process loop in Mode A, at smallest scale** — turning the one-division hint into an actual evolutionary process:

- 2 → 4 cells over 2–3 generations (measure-and-restart, constant depth — survives the coherence wall).
- Quantum per generation: P1 (division + mutation) and P2 (fate superposition + commitment); classical host does fitness, kills losers, seeds the next generation from survivors.
- Headline measurement: the **within-generation entanglement witness** per generation (⟨σz⟩ is classical — need the off-diagonal), plus cohort drift vs rulebook.
- Qubit budget ≈ 16 q + witness/CHSH pairs (§5.2.5 Mode A peak).

This is the honest deliverable thesis arm. Mode B (coherent genealogy) and its measured collapse curve come after, as the frontier result. The MVP's single division is deliberately the first step on that exact path.

### What the MVP deliberately cuts

Ed25519 signing, append-only ledger, formal cohort audit, ML detector training, phantom anatomy, CT physics simulation, the **full** QALife loop (multi-generation Mode A, and Mode A/B collapse study), contextuality, self-testing, randomness expansion, QAE. All of these are later work (Sections 5, 11). The MVP keeps exactly one division as a teaser; everything beyond one generation is deferred. The MVP's single job is: *quantum rolled these tumors, here is the Bell-value proof, here is the cohort — and here is the first cell division of a tumor that will learn to evolve.*

### Mockup — the MVP grid (the page)

```
╔══════════════════════════════════════════════════════════════╗
║  QUANTUM VIRTUAL COHORT · 12 tumors · ibm_heron · CHSH 2.38 avg ║
╠════════╤════════╤════════╤════════╤════════╤════════╤═════════╣
║ ▒▓██▓▒ │ ░▒▓▓▒░ │ ▒████▒ │ ░▓██▓░ │ ▒▓▓▓▒  │ ░████░ │  ...    ║
║ ██◉██  │ ▓▓◉▓▓  │ █◉███  │ ██◉█   │ ▓◉▓▓   │ ███◉█  │         ║
║ ▒▓██▓▒ │ ░▒▓▓▒░ │ ▒████▒ │ ░▓██▓░ │ ▒▓▓▓▒  │ ░████░ │         ║
║ 8mm sol│ 4mm GGO│12mm sol│ 6mm ps │ 5mm GGO│ 9mm sol│         ║
║ RUL    │ LLL    │ RML    │ LUL    │ RLL    │ RUL    │         ║
╠════════╧════════╧════════╧════════╧════════╧════════╧═════════╣
║ COHORT vs RULEBOOK           QUANTUM                           ║
║ size dist  ▇▅▃▂ matches ✓    every nodule: CHSH > 2            ║
║ type mix   solid 58% GGO 25% each rolled on real hardware     ║
║ nobody chose this cohort — the distribution came from physics  ║
╚══════════════════════════════════════════════════════════════╝
```

### Mockup — single-tile detail (click / hover zoom)

```
╔══════════════════════════════════════════════════════════════╗
║  CERTIFIED QUANTUM VIRTUAL TUMOR            ibm_heron · job a3f1 ║
╠════════════════════════════════════╦═════════════════════════╣
║                                    ║  DECODED FROM QUBITS      ║
║        ░░▒▒▒▓▓▓▓▓▒▒░░              ║  ───────────────────────  ║
║      ░▒▓▓████████████▓▒░           ║  size      8.2 mm         ║
║     ▒▓███████████████████▒         ║  type      solid          ║
║    ▒▓████████  ◉ ███████▓▒  ← nodule  margin    spiculated     ║
║    ▒▓███████████████████▓▒         ║  lobe      right upper    ║
║     ▒▓█████████████████▓▒          ║                           ║
║      ░▒▓████████████▓▒░            ║  QUANTUM CERTIFICATE      ║
║        ░░▒▓▓▓▓▓▓▒▒░░               ║  ───────────────────────  ║
║                                    ║  CHSH   2.41  ████████░░  ║
║     real LIDC lung CT              ║  classical max: 2.00 ─────║
║     + quantum-rolled nodule        ║  shot   #137              ║
║                                    ║  ✓ genuine quantum roll   ║
╠════════════════════════════════════╩═════════════════════════╣
║  Classical computers can fake tumors. Only quantum proves      ║
║  nobody — including us — picked this one.                       ║
╚══════════════════════════════════════════════════════════════╝
```

### MVP build sketch

| File | Role |
|---|---|
| `rulebook.py` | size bands (+ lobe) → `Ry` angles from published stats |
| `circuit.py` | ~10-qubit circuit: nodule qubits + 1 quantum division (P1 hint) + 1 CHSH pair, same job |
| `lineage.py` | one division: controlled-copy + `Ry(θ_mut)` → correlated daughter |
| `run.py` | `AerSimulator` for dev; one real `ibm_heron` job for the demo |
| `lesion.py` + `insert.py` | decode bits → blob → image-domain insert into LIDC/LUNA16 slice |
| `render` (web) | self-contained page: cohort grid + per-tile params + CHSH stamp + rulebook strip |

**Honest label on the page:** tumor *parameters* are sampled from certified-quantum measurement; the *image* is a classical rendering. No claim that quantum makes a better or non-classical tumor (§5.4 trap) — the claim is provenance only.

**Why it is the right MVP:** reuses the proven classical pipeline (§3, item 5), needs one cheap QPU job, produces a shareable artifact that reads as a real dataset viewer, and leaves every heavier arm (signing, audit, living-process, Bell test rounds) as a clean next step behind the same `Sampler` seam.

---

## 3. Why it could work

1. **Virtual imaging trials are going mainstream and want standards.** The AAPM TG387 framework names credibility, reproducibility and accessibility as the core requirements. Signed receipts directly serve reproducibility and credibility.
2. **Regulators already accept simulated evidence.** FDA's VICTRE trial (2,986 in-silico patients) concluded in-silico imaging trials can be a viable source of regulatory evidence. When fake patients count as evidence, proving where they came from matters.
3. **The FDA itself flags cohort-selection bias.** Badano et al. (2023) discuss the potential for study bias from selecting specific patient distributions. A certified unchosen draw is a direct answer.
4. **Certified quantum randomness is now real infrastructure.** NIST/CU Boulder's CURBy beacon (Nature 2025) and the JPMorgan/Quantinuum certified-randomness demonstration (Nature 2025) both exist — but neither is applied to medical simulation. Open ground.
5. **The pipeline is already proven classically.** Duke's Virtual Lung Screening Trial (174 digital twins, 512 procedural nodules, 1,044 simulated CT scans) shows that procedural tumors + physics simulation produce useful AI training data. You replace one step and add certification.
6. **Direct Siemens fit.** DukeSim has been validated against the Siemens NAEOTOM Alpha photon-counting CT; AI-Rad Companion Chest CT detects lung nodules and compares them with priors.
7. **You already own most of the stack.** CHSH certification (measured ~1.96 on `ibm_marrakesh`), dynamic circuits, best-chain qubit selection, Ed25519 receipts, audit ledger, teleport routing.

---

## 4. Why quantum — and the honest limits

**Classical CAN:** generate tumors from a rulebook (X-Lesions does). A 14-qubit circuit is easy to simulate. Never claim quantum makes *better* tumors.

**Classical CANNOT:** prove nobody chose the tumors. A pseudo-random generator is deterministic; whoever picks the seed knows every tumor in advance and could try seeds until the cohort favors their scanner ("seed shopping"). Quantum outcomes are unpredictable even to the operator, and CHSH > 2 in the same job is evidence they came from quantum measurement, not a prepared list.

**Strongest objection:** "Commit-then-reveal plus a public beacon blocks seed shopping classically." Partly true — and you should use commit-then-reveal anyway (publish rulebook + code hash before the job). Quantum adds certification that the randomness is unpredictable even to its producer, without trusting a beacon operator.

**Own limit:** a single IBM chip is not loophole-free; you trust the hardware. Mixing in a CURBy pulse (loophole-free Bell test) closes most of the gap.

---

## 5. Improving quantum dependency

**Goal:** make quantum hardware hard to replace, not just make the pitch sound quantum. In the base design the quantum computer only supplies randomness, so a reviewer can swap it for any certified beacon. Each upgrade below gives the hardware an additional job. **Test for every feature: does it add a job classical cannot do, or only a quantum label?**

### 5.1 Core upgrades (in the thesis)

**Upgrade 1 — Hidden test rounds (certify the tumor bits themselves).**
In the base design the CHSH pair sits *beside* the tumor qubits, so a sceptic can ask how we know the tumor qubits were quantum. Fix, as in device-independent randomness protocols:
- Every shot uses the same entangled qubits.
- A secret random choice, made after the circuit is fixed, decides whether each shot is a **test round** (measured in CHSH bases) or a **generation round** (measured normally, decoded into a tumor).
- The device cannot know which rounds will be tested. Passing test rounds (CHSH > 2) certifies the generation rounds, because faking tumor bits would also require faking the tests.
- Needs no time race, so it works despite IBM queue latency.

**Upgrade 2 — Randomness expansion seeded by CURBy.**
Hidden test rounds need randomness to choose which rounds are tests (chicken-and-egg). Expansion protocols take a small trusted seed and output more certified randomness than they consume. CURBy (loophole-free Bell test) seeds the protocol; IBM expands it into enough certified bits for thousands of tumors. Closes the gap in Upgrade 1 cheaply.

**Upgrade 3 — Contextuality as a second, independent certificate.**
CHSH assumes two separated parties, which on one chip is not physically true. Contextuality tests (e.g. KCBS) show non-classicality within a single system through sequential measurements, with no separation story. Two different non-classical signatures (Bell + contextuality) are much harder to dismiss than one, and contextuality is the more honest fit for single-chip hardware.

**Upgrade 4 — Self-testing from CHSH data.**
Near-maximal CHSH values (Tsirelson bound ≈ 2.83) certify not only randomness but *which* state and measurements the device used. The receipt can state "the device behaved as claimed during this job". On noisy Heron only robust self-testing bounds are reachable; how tight they are is a measurable result. Uses data already collected.

**Upgrade 5 — Amplitude-estimation cohort audit (merges `siemens-1`).**
Instead of checking cohort statistics ("are 12% of nodules ground-glass?") by counting samples, wrap the generator in a quantum amplitude estimation (QAE) circuit and estimate the probability with quadratically fewer circuit calls. The quantum computer then both *generates* and *audits* the cohort. Inherits the measured QAE noise floor (IonQ Forte-1, 2026: error saturates at (2–5)×10⁻²) — showing where that floor hits for cohort auditing joins the two strongest ideas into one thesis.

### 5.2 Stretch upgrades (separate chapter if time allows)

- **Quantum-walk tumor growth.** Grow the tumor surface as a quantum walk: linear (ballistic) spread vs classical √t diffusion, interference fronts and arm-like features resembling spiculation, with an interference signature checkable in other bases. Extends QuantumGaltonBoard and `siemens-6`. Present as a *shape primitive*, not a biological model; test plausibility with detectors or radiologists.
- **Interference as a control knob.** Circuits with identical per-property frequencies can produce different cross-property correlations depending only on phases — one physical "phase dial" controls e.g. how strongly spiculation correlates with size while published frequencies stay fixed.
- **Logical (error-corrected) qubits.** Re-run the smallest patient on encoded qubits when IBM offers them and show cohort drift shrinking: "noise bias at N physical qubits, eliminated at M logical qubits" — the concrete 10-year scaling number.

### 5.2.5 Living-process tumor via a QALife hybrid loop (the core quantum arm)

This is the heart of the quantum contribution. The base design rolls a *static* tumor in one shot; this arm grows the tumor as a **living evolutionary process** run on quantum hardware, reusing the quantum-artificial-life stack (motile vivarium, Darwinian richness, germ/soma, coherence-depth genealogy). A tumor is the single best biomedical fit for Darwinian QALife because a tumor *is* an evolving clonal population — mutation, selection, proliferation, apoptosis, heterogeneity, motility.

**Complexity emerges from processes, not qubit count.** The central design bet: a few qubits cycled through many generations and process steps, carrying quantum state forward, produce a tumor whose complexity *emerges from the dynamics*. No 100-qubit register, no supercomputer-scale hardness claim — the interesting behaviour comes from *composing* biological processes on a modest, coherence-affordable number of qubits. This is what keeps the arm buildable and what makes it honest.

**Design rule:** do not run a whole tumor on a QPU. Put on quantum only the few processes with no honest classical substitute; a classical host loop does everything else (fitness, resource/hypoxia field, spatial placement, meshing, CT). The quantum device rolls the *life story*; classical *renders* it into a lesion. The tumor is literally **built from the quantum evolutionary trace** by hybrid jobs.

**The clonal-evolution map.** Every process already exists as a QALife primitive:

| Tumor process | QALife primitive | Quantum op |
|---|---|---|
| Cell = genotype/phenotype | organism qubit/register | state prep |
| Proliferation | QALife replication (partial unitary copy) | controlled copy |
| Mutation | QALife mutation | `Ry(θ_mut)` |
| Apoptosis / cell death | QALife death | damping / decoherence |
| Clonal selection under resource limit | Darwinian-richness selection | fitness-weighted survival (classical) |
| Metastasis / motility | motile vivarium | moving organism |
| Heterogeneity | population richness | superposition across clones |
| Microenvironment / hypoxia | environment coupling | open-system channel (classical field) |

**The three processes that earn quantum (and only these).** The tumor is a classical object (see §5.4 trap). What runs as quantum is the generative *process*:

- **P1 — Division with mutation (entangling copy).** Cell = 1 genotype qubit; division = controlled-copy onto a fresh ancilla plus a small `Ry(θ_mut)`. Daughters emerge *correlated by shared ancestry*, not as independent PRNG draws. Job: certified-unchosen mutation + genuine daughter correlation.
- **P2 — Fate superposition + commitment (the only truly non-classical dynamics).** Each cell carries 1 phenotype qubit in superposition over fates (proliferative ↔ quiescent ↔ necrotic); a **phase dial** biases interference before measurement commits the fate. At *fixed marginal frequencies*, phase changes cross-fate correlations (the interference knob of §5.2). No classical sampler reproduces this. Strongest quantum claim in the living-process arm.
- **P3 — Lineage entanglement across generations (the hardness carrier).** Daughters stay entangled with the parent register instead of being measured; the joint distribution over the family tree is the classically-hard object. This is the prize — and the blocked one (see the wall below).

Everything else stays classical. No quantum label without a job.

**The hybrid loop — two modes; the contrast is the result.**

*Mode A — measure-and-restart (buildable now, shallow, constant depth):*
```
gen g:   quantum job → prep N cell-qubits (P1 + P2) → measure all
host:    decode genotype/phenotype → apply fitness → kill losers →
         compute next-gen angles from survivors → place in space
gen g+1: new quantum job seeded by survivors
```
Constant depth per job, so it survives the coherence-depth wall. But measuring each generation destroys cross-generation entanglement — honest label: *quantum within a generation, classical genealogy.*

*Mode B — coherent genealogy (the hard regime, deep):* grow the whole tree in one long circuit, daughters unmeasured until the end, P3 keeping lineage entangled. The entangled tree is the real advantage target, but depth grows with generations — **exactly the regime our own `C(g)` coherence-depth-genealogy run showed collapses on Heron-r2** (correlation dies with depth, quantum>classical physically blocked on two-point `C(g)`, advantage inverts because readout error ≫ two-qubit error). The study runs both modes and **measures where Mode B collapses to Mode A** — that collapse point, on Heron, is the headline number, obtained with the existing `C(g)` methodology.

**How hybrid jobs build the tumor.** The quantum trace is a list of `(genotype, phenotype, lineage_id, generation)` clones. Classical assembly: clone → spatial sub-region of the lesion; phenotype → local density/texture (solid / ground-glass / necrotic core); lineage → spatial contiguity (siblings adjacent); generation → growth snapshot. **Baseline = early generation, follow-up = late generation** — a free longitudinal pair that feeds AI-Rad Companion's prior-comparison feature. The assembled lesion goes into the phantom and the CT simulator as in the base pipeline.

**Sub-study spec (separate chapter).**
- *Research question:* Can a hybrid loop run a tumor's few core evolutionary processes on quantum — certified-unchosen trajectory, entanglement witness per generation — and how many coherent generations can Mode B hold before collapsing to the Mode A (classical-genealogy) limit on Heron?
- *Falsifiable hypothesis:* the within-generation entanglement witness survives on Heron through ≥G generations in Mode A; Mode B `C(g)` collapses to the Mode-A level beyond a measurable generation/depth threshold.
- *Metrics:* entanglement witness per generation (headline — ⟨σz⟩ is classical, need the off-diagonal); `C(g)` vs depth, Mode A vs B, and the collapse point; interference-knob result (vary phase, show correlation shift at fixed marginals); cohort drift vs rulebook; CHSH per job.
- *Qubit budget:* 2 q/cell (genotype + phenotype), 2→4→8 cells over 3 generations. Mode A peak ≈ 16 q + witness/CHSH pairs; Mode B ≈ 28 q + entangling depth (the collapse run). Sits naturally above the base 14-qubit single nodule.

**The honest wall.** Mode B is gated on logical (error-corrected) qubits — our own coherence-depth data already proves deep coherent genealogy is physically blocked on current Heron. So Mode A is the deliverable thesis arm; the Mode B collapse curve is an honest measurement of the gap; logical-qubit Mode B is the §5.3 future, now **quantified by a measured collapse number instead of hand-waved**. This is the concrete 10-year scaling story in biological form.

**Two traps specific to this arm.** (1) Death-as-decoherence is a scientifically neat narration, but it is the error channel — we do not engineer it; narrate apoptosis as environment-driven, do not claim it as designed dynamics. (2) Realism cliff: a ~10-parameter evolving blob reads as a toy to oncologists (bear case §7.4, worse in motion) — present it as a *process primitive*, validated only for drift/witness behaviour, not biological fidelity.

### 5.3 Future work (10-year section)

- **Blind quantum computing.** Hide the computation from the provider so it cannot distinguish test rounds from generation rounds even in principle. Requires a client that sends individual qubits — not possible with cloud QPUs today.
- **Networked quantum processors.** A true loophole-free Bell certificate needs two separated devices; linked processors on IBM's roadmap would bring the certificate to CURBy's standard.

### 5.4 Traps to avoid

- **"Non-classical tumors" via entangled properties.** Read in one basis, any output is a classical distribution; non-classicality appears only across bases, which has no medical meaning. Real tumors are classical objects — certify the *process*, not the tumors.
- **No-cloning / quantum money to protect the dataset.** Qubits decohere in microseconds; the dataset is classical files protected by classical signatures.
- **Teleportation without a job.** Only for long-range gates (vs SWAP routing) or chip-spanning certificate pairs.

### 5.5 Resulting quantum jobs

| Job | Feature | Classical replacement? |
|---|---|---|
| Generate | Hand-encoded circuit | Yes (tumor content) — not claimed as quantum value |
| Live the process | Hybrid division/mutation/fate loop (§5.2.5) | Partly — within-generation entanglement + interference knob have no classical sampler |
| Certify (Bell) | Hidden CHSH test rounds + self-testing | No (only another quantum device) |
| Certify (single system) | Contextuality test | No |
| Expand randomness | CURBy-seeded expansion | No |
| Audit cohort | QAE | Yes, but with quadratically more samples |

Replacing the quantum hardware now means replacing five of six jobs, not one.

### 5.6 Effect on "quantum seen as essential"

| Design | Estimate |
|---|---|
| Base (CHSH pair beside tumor qubits) | ~20–30% |
| + Upgrade 1 (hidden test rounds) | ~40–50% |
| + §5.2.5 living-process arm (within-generation entanglement + interference knob give the hardware a dynamical job) | ~50–60% |
| + Upgrades 2–5 (expansion, contextuality, self-testing, QAE audit) | ~55–60% |

The ceiling stays below 100% because the remaining question — *does certification matter clinically?* — is answered by Siemens or a regulator, not by physics.

**Recommended scope for the thesis:** the §5.2.5 living-process arm (Mode A build + Mode B collapse curve) plus Upgrade 1 as core; Upgrades 2–5 and quantum-walk shapes as the stretch chapter; 5.3 as future work.

---

## 6. Bull case

- First application of certified quantum randomness to virtual imaging trials — a clean, ownable "first".
- Addresses a regulator-named risk (cohort-selection bias) with a mechanism no classical method fully matches.
- Generator cannot memorize patients by construction — a cleaner privacy story than any learned generator.
- Directly useful Siemens artifacts: labeled nodule cohorts, multi-nodule patients, baseline/follow-up pairs for prior-comparison testing.
- Reuses almost everything you have built; low QPU cost (a few qubits, Mode A constant depth).
- Scales naturally to Jan's 10-year framing by *deepening the process* — more generations and richer biology on a modest qubit count, not a 100-qubit chip. Complexity emerges from the dynamics; better hardware just buys more coherent generations.

## 7. Bear case

1. **"Why quantum" is thin** — commit-then-reveal + public beacon does most of the work classically.
2. **Certificate rests on trust** — single-chip CHSH is not loophole-free.
3. **Solves an unreported problem** — risk flagged, but no documented seed-cheating case in virtual trials.
4. **Simple tumors** — ~10 hand-written parameters look cruder than X-Lesions; quantum adds no realism.
5. **Noise biases the cohort** — you could certify a biased cohort, worse than an uncertified correct one.
6. **Sounds like security** — signatures and certificates are Jan's rejected vocabulary. Lead with data credibility, not crypto.
7. **Tool access** — XCAT/DukeSim may need a Duke collaboration.

**Likely outcome:** the pipeline works end to end; the noise-bias-vs-patient-complexity curve is a genuine result; the "why quantum" answer is honest but modest.

**Value if null:** a working certified virtual-cohort pipeline plus a measured noise-bias map is still a publishable methods paper and a reusable tool.

---

## 8. Where it wins

- **Regulatory submissions** using virtual trials, where a sponsor must show it did not cherry-pick virtual patients.
- **Independent benchmarking** of AI detectors across vendors: a neutral, certified test cohort no vendor could have tuned against.
- **Shared synthetic datasets** where recipients need proof the data is synthetic and traceable, not leaked patient scans.
- **Longitudinal test sets** (baseline + follow-up with known true growth) for prior-comparison features.

It does **not** win on image realism, speed, or volume — classical tools are better there and the pitch must not compete on them.

---

## 9. Probability it will be useful

Judgment-call estimates, not measurements:

| Outcome | Estimate | Reasoning |
|---|---|---|
| Thesis delivers a working pipeline + publishable result | **~70%** | Every component exists or is built; main risk is tool access, which has fallbacks |
| Noise-bias scaling curve is a meaningful result | **~65%** | Drift will exist and grow with depth; measuring it is straightforward |
| Siemens finds the certified-cohort concept worth funding | **~35–45%** | Fits virtual-trial and AI-testing needs; depends on framing as data credibility, not security |
| Reviewers accept quantum as essential, not decorative (base design) | **~20–30%** | The commit-then-reveal objection is strong; CURBy mixing + same-job certification help |
| Reviewers accept quantum as essential (with Section 5 upgrades) | **~50–60%** | Hidden test rounds, the living-process dynamical job, a second certificate type and QAE audit give the hardware several irreplaceable roles |
| Living-process arm (§5.2.5): Mode A hybrid loop delivers a witness-per-generation + measured Mode-B collapse curve | **~55%** | Mode A is constant-depth and reuses the QALife + `C(g)` stack; the collapse is the result, not a failure |
| Living-process arm shows coherent genealogy (Mode B) beating classical on Heron *today* | **~5%** | Our own `C(g)` data shows deep genealogy is physically blocked pre-logical-qubits |

---

## 10. Technology dependencies — and how it still works without each

| Dependency | Role | If unavailable | Impact |
|---|---|---|---|
| **IBM quantum hardware** | Steps 1–2 | Run the same circuit on a simulator for development; for certification use CURBy or another certified source; for a fully classical baseline use a commit-then-reveal PRNG | Pipeline fully works; the quantum certificate weakens or moves to an external beacon |
| **Low noise / coherence depth** | Coherent genealogy (Mode B), more generations | Run Mode A (measure-and-restart, constant depth); complexity still emerges from composing processes | Classical genealogy instead of coherent; certification unchanged |
| **Dynamic circuits** | Follow-ups, feed-forward growth | Generate follow-up growth in a second job conditioned classically on the first | Higher depth, same outputs |
| **XCAT phantoms** | Virtual patient anatomy | Duke has publicly shared an XCAT-3.0 phantom library; otherwise insert lesions into public lung CT scans (image-based insertion) or use open anthropomorphic phantoms | Less control over anatomy, still realistic backgrounds |
| **DukeSim** | CT physics simulation | Open-source CT simulators and reconstruction toolkits (e.g. XCIST, ASTRA, TIGRE); or image-domain insertion with matched noise | Loses Siemens-scanner-specific fidelity |
| **CURBy beacon** | Loophole-free randomness mix-in | IBM CHSH alone (trusted hardware) or NIST's classical beacon for the commit-then-reveal step | Weaker trust model, still auditable |
| **Siemens data / products** | Downstream use | Evaluate with public open-source nodule detectors | Same evidence of usefulness, no product tie |

**Key point:** the pipeline's value does not depend on any single technology. Even fully classical — PRNG + commit-then-reveal + signed receipts + open simulator — it produces reproducible, auditable virtual cohorts. Quantum hardware adds what classical cannot: randomness certified unpredictable even to the operator, plus a living evolutionary process whose within-generation entanglement and interference knob have no classical sampler. Tumor complexity grows by *adding processes and generations* on a modest qubit count, not by widening the register — so better hardware extends how many coherent generations are reachable (Mode A → Mode B) without changing the architecture. That is the 10-year scaling story: deeper life, not wider chips.

---

## 11. Study design (thesis format)

**Research question:** Can a training-free quantum hybrid loop run a tumor's core evolutionary processes (division, mutation, fate choice) to grow a clinically-parameterized virtual tumor whose trajectory is certified unchosen — and how many coherent generations can the hardware hold before the living process collapses to a classical genealogy?

**Hypothesis (falsifiable):** Single-nodule and Mode-A living-process cohorts match the declared rulebook within statistical tolerance on Heron, and the within-generation entanglement witness survives through ≥G generations; Mode-B coherent genealogy `C(g)` collapses to the Mode-A level beyond a measurable generation/depth threshold.

**Method:** encode rulebook → run hybrid living-process loop (Mode A, then Mode B) on statevector, noisy sim, Heron → decode clone trace → sign → assemble lesion + insert and simulate CT → verify → audit.

**Baseline:** classical PRNG + commit-then-reveal generating the same cohort from the same rulebook; and a fully classical evolutionary loop for the living-process arm.

**Metrics:** chi-square / total-variation distance of cohort vs rulebook; entanglement witness per generation; `C(g)` vs depth (Mode A vs B) and the collapse point; interference-knob correlation shift at fixed marginals; CHSH value per job; verifier pass rate; detector performance on generated images (sanity check).

**Novel contribution:** first certified-randomness, living-process virtual-tumor generator — complexity emerging from composed quantum processes on a modest qubit count — with a measured coherent-generation collapse curve.

**Venue:** IEEE QCE short paper; SPIE Medical Imaging (Physics of Medical Imaging) for the virtual-trial angle.

---

## 12. Groups to approach

**Virtual imaging trials**
- **Duke University — Center for Virtual Imaging Trials** (Ehsan Samei, Ehsan Abadi, W. Paul Segars). XCAT, DukeSim, X-Lesions; validated against the Siemens NAEOTOM Alpha; Siemens co-authors. *Best fit.* https://cvit.duke.edu/
- **US FDA — Division of Imaging, Diagnostics and Software Reliability** (Aldo Badano, Miguel Lago, Andreu Badal). VICTRE; cohort-bias concern. https://github.com/DIDSR/VICTRE
- **University of Pennsylvania** (Andrew Maidment) and **Lund University** (Predrag Bakic). OpenVCT; algorithmically generated breast phantoms — same philosophy as hand-encoded generation.
- **KU Leuven** (Hilde Bosmans). Co-author of AAPM TG234 breast virtual-trial standards.

**Certified quantum randomness**
- **NIST Boulder / CU Boulder** (Krister Shalm, Emanuel Knill, Gautam Kavuri, Jasper Palfree). CURBy beacon + Twine traceability protocol. https://random.colorado.edu/
- **UT Austin** (Scott Aaronson) with **JPMorganChase / Quantinuum / Oak Ridge** (Marco Pistoia). Certified randomness on trapped ions.

**Quantum generative / sampling methodology**
- **QC Ware** (Alejandro Perdomo-Ortiz) — generalization of quantum generative models; relevant if you ever add learned components.
- **CERN openlab** — quantum sampling of detector physics on IBM hardware (precedent for `siemens-6`).

---

## 13. References

**Virtual imaging trials and phantoms**
1. Abadi E. et al., "Virtual clinical trials in medical imaging: a review," *J. Med. Imaging* 7(4), 042805 (2020).
2. AAPM TG387, "Toward widespread use of virtual trials in medical imaging innovation and regulatory science," *Med. Phys.* 51(12):9394–9404 (2024).
3. Badano A. et al., "The stochastic digital human is now enrolling for in silico imaging trials — methods and tools for generating digital cohorts," arXiv:2301.08719 (2023).
4. Badano A. et al., "Evaluation of digital breast tomosynthesis as replacement of full-field digital mammography using an in silico imaging trial" (VICTRE), *JAMA Netw. Open* 1(7):e185474 (2018).
5. "SYN-LUNGS: Towards simulating lung nodules with anatomy-informed digital twins for AI training," arXiv:2502.21187 (2025).
6. "In silico modeling of a clinical photon-counting CT system: verification and validation," *Med. Phys.* 52 (2025) — DukeSim for NAEOTOM Alpha.
7. Abadi E. et al., "A framework for realistic virtual clinical trials in photon counting computed tomography," *Proc. SPIE* 10948 (2019).
8. Abadi E. et al., "DukeSim: a realistic, rapid, and scanner-specific simulation framework in computed tomography," *IEEE Trans. Med. Imaging*.
9. "XCAT-3.0: A comprehensive library of personalized digital twins derived from CT scans," arXiv:2405.11133 (2024).
10. "Virtual NLST: towards replicating National Lung Screening Trial," *Proc. SPIE* 12925 (2024).
11. Bakic P. et al., "AAPM Task Group 234 report: Virtual tools for the evaluation of new 3D/4D breast imaging systems."
12. Pokrajac D., Maidment A., Bakic P., "Optimized generation of high resolution breast anthropomorphic software phantoms," *Med. Phys.* (2012).

**Certified randomness**
13. Kavuri G. et al. (NIST / CU Boulder), traceable Bell-test randomness beacon (CURBy), *Nature* (2025).
14. Liu M. et al., "Certified randomness using a trapped-ion quantum processor," *Nature* 640, 343–348 (2025).

**Motivation and honesty checks**
15. Dar S. et al., "Unconditional latent diffusion models memorize patient imaging data," *Nat. Biomed. Eng.* (2025).
16. Akbar M. U. et al., "Beware of diffusion models for synthesizing medical images — a comparison with GANs in terms of memorizing brain MRI and chest x-ray images," arXiv:2305.07644.
17. "Selection of random number generators in GATE Monte Carlo toolkit," *Nucl. Instrum. Methods A* (2020) — randomness quality does not change simulation results.
18. Raj S., Mathur N., Perdomo-Ortiz A., "'Train classical, deploy quantum' requires rethinking generalization," arXiv:2608.31117 (2026).
19. Gili K. et al., "Do quantum circuit Born machines generalize?" *Quantum Sci. Technol.* 8, 035021 (2023).

**Siemens context**
20. Siemens Healthineers, "AI-Rad Companion Chest CT — Features, Data, and Algorithms" whitepaper (lung nodule detection, correlation with priors).

**Quantum certification methods (Section 5) — verify details before citing**
21. Pironio S. et al., "Random numbers certified by Bell's theorem," *Nature* 464, 1021–1024 (2010).
22. Vazirani U., Vidick T., "Certifiable quantum dice — or, testable exponential randomness expansion," *STOC* (2012).
23. Klyachko A. et al., "Simple test for hidden variables in spin-1 systems" (KCBS contextuality inequality), *Phys. Rev. Lett.* 101, 020403 (2008).
24. Šupić I., Bowles J., "Self-testing of quantum systems: a review," *Quantum* 4, 337 (2020).
25. Lal A. et al., "Maximum-likelihood amplitude estimation for quantum Monte Carlo integration on trapped-ion hardware," arXiv:2609.25992 (2026).
