# RUNLOG — Quantum Artificial Life, Phase 2 (the PJ line)

> **Live document.** Append as runs land. Newest work goes at the bottom of each section; the
> roadmap and the comparison tables at the end are kept current. One row per decisive run — keep
> the exploratory noise in `research_runs/`, bank only the runs that *decided* something here.

**Scope.** The Phase-2 "Darwinian richness vs the quantum signature" epic and its PJ feature line.
The one quantum claim throughout is the genealogical entanglement witness `⟨X^⊗W⟩` (+ the `ghz2`
Z-sector `⟨ZZ⟩`) — every diagonal quantity (alive-count, position field, lifetime) is classically
reproducible by construction and is *not* the claim.

**Legend.** ✅ landed / certified · ⚠️ honest-but-weak · ❌ refuted · ⏳ pending · 🔭 planned.
**Hardware.** IBM Heron-r2: `ibm_kingston`, `ibm_marrakesh` (156-qubit). Chain-quality gate is
fail-closed (abort if 2q-err > 0.05 or readout > 0.15). QRNG entropy (Q-EaaS) fail-closed on hardware.

---

## 1. How to add an entry

1. Run the command; note the written `research_runs/.../*.json` path.
2. Add a row to the right table (§4/§5) with: date, backend, config, the decisive number, verdict.
3. If it changes the story, update §3 (timeline), §6 (roadmap), or §7 (comparisons).
4. Keep it honest: record the raw witness, not just the mitigated one; say what collapsed.

---

## 2. One-line state (update me)

**As of 2026-10-19:** PJ2.4 motile organism is the flagship — a 2018-faithful life that moves, with a
`ghz2` GHZ certificate that **survived** on `ibm_marrakesh` (`⟨XX⟩+⟨ZZ⟩ ≈ 1.96 > 1`). PJ2.5 (germ
dynamical-decoupling, the first error-mitigation lever) is **implemented and sim-verified**; its
decisive hardware A/B is **pending** (§5).

---

## 3. Timeline (how it went down)

| When | Stage | What happened | Verdict |
|------|-------|---------------|---------|
| 2026-08 (early) | QDEP (OLD) | Coherence-depth `C(g)` framing: generation where coherent inheritance beats measure-and-resend. Rig bug fixed 2026-08-19. | ❌ `C(g)` is a diagonal `⟨σz⟩` quantity with an *exact* classical surrogate; on Heron-r2 the advantage physically inverts (readout-err ≫ 2q-err). |
| Months 1–4 | Reframe | Teleport-routing tried as the advantage vehicle. | ❌ Refuted **twice** on-chip (mid-circuit readout is the dominant error). |
| Month 4 | Rebuild | Threw out the stand-in; rebuilt the **whole** Alvarez-Rodriguez 2018 model (all four operators, verified operator-by-operator) and moved the claim **off-diagonal** to the witness `⟨X^⊗W⟩`. | ✅ Real measured signature. |
| 2026-09-09 | P1 | Reconstruction baseline: re-anchor the exact 2018 four-operator model on clean code; bank the clean-witness reference vs the ≈0 separable null. | ✅ Honesty anchor set. |
| 2026-09-11 | **P2** | Scale ceiling on live `ibm_kingston`: unitary genealogy **W\*=24 = 48 qubits** (~6× the paper's ~4-qubit origin; W=32 dead). Faithful **amplitude-damping death** certified k=3σ through W=4, collapsed by W=8 → damping W\* ∈ [4,8). | ✅ Unitary scale proven; ⚠️ damping is worse in every way (the hinge diagnosis). |
| 2026-09-12 | **PJ0** | Germ/soma split (Weismann barrier) — the **first new biology**. Severs the 2018 `cx(g,p)` that entangled mortal body to immortal gene (the exact wound that collapsed damping). Genotype never touches body. | ✅ Quantum-design contribution; witness carried by germ only. |
| 2026-09-13 | **PJ1** | Two-organism collision / arena; solo + main-event runs on `ibm_kingston`. | ✅ Multi-organism tiling works. |
| 2026-09-23 | **PJ2 / PJ2.1** | Solo vivarium + gradual biology on `ibm_kingston`. | ✅ Vivarium primitives land. |
| 2026-09-25–26 | **PJ2.2** | Lattice (3×3) + 1D line live runs — movement via excitation-conserving quantum walk. `ibm_kingston`. | ⚠️ Movement + heredity only; the motion is classically reproducible — "a quantum walk in ALife clothing." |
| — | PJ2.3 | Labeled hardcore lattice. | ❌ Bad move; removed from the repo. |
| 2026-09-27 | **PJ2.4** | Honest motile vivarium (M0–M5): a minimal organism that **moves** AND has reproduction / metabolism / selection / **unitary-aging death** genuinely acting. `--certify ghz2` two-basis GHZ certificate. Hardware: `ibm_marrakesh`. | ✅ Certificate **survived** (`⟨X^W⟩≈0.98`, `⟨ZZ⟩≈0.98`, `⟨XX⟩+⟨ZZ⟩≈1.96`, certified gens 3–5); daughter born gen3; death/succession read. ⚠️ Founder feeding marginal (energy≈0.4). |
| 2026-10-19 | **PJ2.5** | Germ dynamical-decoupling (EM1 / CD-11, first mitigation lever) wired into the motile path — which was running **with DD off**. Made DD a measured, switchable lever (`--dd`, `--dd-ab`). Sim-verified. | ✅ Implemented (sim: DD-off ≡ DD-on, noiseless-neutral, delta 0). ⏳ Hardware A/B pending (§5). |

---

## 4. Banked decisive runs (history)

| Date | Stage | Backend | Config | Decisive number | Verdict | Run file |
|------|-------|---------|--------|-----------------|---------|----------|
| 2026-09-11 | P2 | ibm_kingston | unitary genealogy W sweep | W\*=24 (k=2σ) | ✅ | `research_runs/originalP2/3.1-FINAL-*.json` |
| 2026-09-11 | P2 | ibm_kingston | damping death, W2–W8 | W\* ∈ [4,8) | ⚠️ | `research_runs/originalP2/3.9-PUSHING-LIMIT-W*.json` |
| 2026-09-27 | PJ2.4 M5 | ibm_marrakesh | org2 L4 gens6 food1,3 ghz2 8192 (no DD) | `⟨XX⟩+⟨ZZ⟩≈1.96`, certified gens 3–5 | ✅ | `research_runs/pj2_motile/pj2_line_org2L4_ibm_marrakesh_20260927-180920.json` |
| 2026-10-19 | PJ2.5 | statevector_sim | org2 L4 gens6 food1,3 ghz2 x2 --dd-ab | `delta_witness=0.000`, certified 3→3 | ✅ (noiseless-neutral control) | `research_runs/pj2_motile/pj2_line_org2L4_statevector_sim_sim.json` |

---

## 5. Decisive hardware runs — PJ2.5 (queued, ~1 min QPU each)

Each is trimmed to ~1 min: `ghz2` (2 settings) × `gens 5` × A/B (×2) ≈ 16–20 circuits at 4096 shots,
single arm. Baseline for the delta is the in-run DD-off pass; the 2026-09-27 M5 (no-DD) is the
historical reference.

```bash
# 1 — HEADLINE ΔW*: does germ-DD (x2) lift the witness vs no-DD, at the M5 geometry?
python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 \
    --gens 5 --food 1,3 --certify ghz2 --arm isolated --dd-ab --dd x2 --shots 4096

# 2 — SEQUENCE SHOOTOUT: is XY4 better than X2 on this chip?
python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 \
    --gens 5 --food 1,3 --certify ghz2 --arm isolated --dd-ab --dd xy4 --shots 4096

# 3 — BARRIER CONTROL: DD must NOT manufacture a witness on the collapsed coupled arm
python code/1D_alive.py --backend ibm_marrakesh --model motile --organisms 2 --length 4 \
    --gens 5 --food 1,3 --certify ghz2 --arm coupled --dd x2 --shots 4096
```

| # | What it decides | Pass criterion | Result | Run file |
|---|-----------------|----------------|--------|----------|
| 1 | Does DD lift `⟨X^W⟩` / `⟨ZZ⟩` vs no-DD? | `delta_witness > 0` with `kept_fraction=1` | ⏳ | _fill on land_ |
| 2 | X2 vs XY4 — which sequence wins? | larger `delta_witness`; adopt winner as `DD_DEFAULT` | ⏳ | _fill on land_ |
| 3 | Does DD fake a witness where it must collapse? | coupled arm stays **un**certified even with DD on | ⏳ | _fill on land_ |

---

## 6. Roadmap (detailed, expandable)

Scoring is two-axis and kept separate: **biological richness added** vs **witness-survival cost**.
Source menu: `plans/P3-candidate-movess.md`. Each item starts as a candidate; graduates to a
`feature-*.md` plan before it runs.

| Order | Item | Owning plan / source | Status | What it buys |
|-------|------|----------------------|--------|--------------|
| now | **PJ2.5 hardware A/B** | `plans/feature-PJ2.5-*.md` | ⏳ | First measured ΔW\* for the DD lever; the §5 runs. |
| next | **Founder feeding tune** | PJ2.4 follow-up | 🔭 | Fix energy≈0.4 half-starve → organism thrives (clean P4 datapoint). |
| then | **EM2 readout mitigation** | EM work-package | 🔭 | Counts-native, post-process; push W\* further. Report vs kept_fraction. |
| then | **EM3 Pauli twirling** | EM work-package | 🔭 | Randomized compiling on the CNOT-clone chain. |
| structural | **M3 multiple lineages** | `P3-candidate-movess.md:120` | 🔭 | Several GHZ trees → the gate that unlocks all competition (M2/M4/flagship). |
| biology | **M1 adaptive selection** | `P3-candidate-movess.md:78` | 🔭 | Earned survival via mid-circuit measure + feed-forward. Expected heavy witness bite — *that bite is the datapoint*. |
| biology | **2D motile port** | PJ2.4 "later port" | 🔭 | Motile life-cycle on the `2D_alive` lattice; spatial richness datapoint. |
| synth | **P4 phase diagram + write-up** | epic §P4 | 🔭 | Richness-vs-survival phase diagram: per added process, the W/gen where the certificate dies. |

Deferred / refuted (do not revisit without new hardware): standalone teleport-routing (❌ twice),
amplitude-damping death (⚠️ worse than unitary), coherence-depth `C(g)` (❌ classical surrogate).

---

## 7. Comparison — 2018 paper vs current flagship

### 7.1 Model

| Dimension | Alvarez-Rodriguez 2018 | Current flagship (PJ2.4 + PJ2.5) |
|-----------|------------------------|----------------------------------|
| Individual | ~2 qubits (genotype + phenotype) | `[genotype | vitality | body cells | energy]` per individual |
| Scale | ~4 qubits, 1–2 individuals | up to **W=24 = 48 qubits** genealogy; motile org2/L4 ≈ 16 qubits |
| Operators | 4: self-replication, mutation, interaction, aging/death | same 4 **kept faithful**, + metabolism, feeding-selection, spatial reproduction |
| Space / movement | none | unary position field + excitation-conserving quantum walk |
| Metabolism | none | energy qubit; `ccx(body,food→energy)` + consume |
| Selection | emergent from death only | feeding-gated `cry(energy→vitality)` — fed lives, starved dies |
| Reproduction | unconditional, placeless CNOT | metabolism-gated **and** spatial (daughter born after eating, one cell over) |
| Death | aging + dissipation | **unitary aging** (damping proven worse, rejected) |
| Germ/soma | entangled (`cx(g,p)`) | **Weismann barrier** — genotype never touches body |
| Quantum claim | *asserted* | **measured + certified** on hardware (witness + `ghz2` GHZ certificate) |
| Mitigation | — | germ-selective DD (PJ2.5), `kept_fraction=1` (unconditional) |
| Platform | theory / small sim | live IBM Heron-r2 |

### 7.2 The headline numbers

| Metric | 2018 | Current |
|--------|------|---------|
| Entanglement-depth witness | not measured | `⟨X^W⟩≈0.98` on hardware |
| Two-basis certificate | — | `⟨XX⟩+⟨ZZ⟩≈1.96 > 1` (separable bound 1) → certified gens 3–5 |
| Max certified width | ~4-qubit origin | W\*=24 = 48 qubits (unitary) |
| Life processes acting | 4 (abstract) | 4 + space + metabolism + feeding-selection + spatial birth |

### 7.3 One-line verdict

2018 **claimed** quantum artificial life on ~4 abstract qubits, read classically. This project
**certified** it on real hardware, gave the organism a body that lives and moves in space, and is now
measuring exactly how much Darwinian richness survives before the quantum signature collapses — with
PJ2.5 adding the first honest lever (dynamical decoupling) to push that boundary outward.
