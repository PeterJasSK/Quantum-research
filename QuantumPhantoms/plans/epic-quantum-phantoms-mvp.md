# Epic: Quantum Phantoms / Quantum Synthetic Cultures (QSC) — MVP web demo (3 steps + 1 optional)

**Slug:** quantum-phantoms-mvp
**Features:** F1–F3 core, F4 optional (4 total)
**Author:** Claude (Opus)
**Date:** 2026-10-26
**Status:** Approved

*Resolved defaults (2026-10-26): web render = self-contained static page (no backend); cohort size = 12 tiles; slug = `quantum-phantoms-mvp`; F4 stays optional/deferred (build after F3 ships).*

---

## 1. Why this epic exists (Vision & Context)

**Context / Assignment.** Build the first, deliberately-simple MVP of the Siemens-8 study (full plan: `QuantumPhantoms/plans/siemens-8-certified-quantum-virtual-cohorts.md`). The MVP is a **web-hosted render of a grid of real lung-CT slices, each carrying a nodule whose parameters were rolled on real IBM quantum hardware, with a CHSH value stamped on every tile** proving the roll was genuinely quantum. It exists to show the "wow" fast — a page that looks like a real synthetic-cohort dataset viewer whose data provably came from a quantum computer. It is **not** the full pipeline: no signing, no ledger, no audit, no ML training, no phantom/CT-physics simulation.

Two names (both honest, see full plan header): **Quantum Synthetic Cultures (QSC)** for Siemens/management, **Quantum Phantoms** for the thesis/academic venue.

**User outcome.**
- *Peter (builder/researcher):* an end-to-end classical+quantum pipeline producing a shareable web demo, structured so quantum methods are swappable behind one seam.
- *Jan / Siemens management:* a one-glance artifact — realistic CT scans a quantum computer generated, with a physics certificate, "nobody chose these tumors."
- *Science / thesis audience:* the first on-screen hint of the living-process arm (one quantum cell division), seeding the 10–15-year scaling story.

**Delivery strategy.** Three sequential, demonstrable steps — **F1** rolls certified tumor parameters on quantum hardware, **F2** turns them into labeled synthetic CT images, **F3** renders the cohort as the web demo. Each step is independently testable (F1 outputs params+CHSH, F2 outputs images, F3 outputs the page). **F4 is optional**: it upgrades the single-division "hint" into a real QALife Mode-A evolutionary loop with a per-generation entanglement witness — the first real living-process arm — and is built only if the MVP lands and time allows.

**Honest scope label (carried on the page):** tumor *parameters* are sampled from certified-quantum measurement; the *image* is a classical rendering. No claim that quantum makes a better or non-classical tumor — the claim is **Tier 1 provenance** only. (See full plan §4, §5.4.)

---

## 2. Steps in this Epic (Milestones)

| ID | Step / Feature | Title | Status | Summary |
|----|----------------|-------|--------|---------|
| F1 | Quantum roll | Rulebook → circuit → certified params | open | The quantum core: published lung-nodule stats → `Ry` angles; ~10-qubit circuit = nodule-property qubits + one quantum division (P1 hint) + one CHSH pair; run on `AerSimulator` (dev) and one `ibm_heron` job (demo); decode bits → tumor params + per-shot/job CHSH value. Exposes the `Sampler` seam. |
| F2 | Lesion → CT image | Decode params → 3D lesion → insert into real CT | open | Decode each param set → 3D lesion blob; image-domain insertion into a real LIDC/LUNA16 lung-CT slice with matched noise. Sibling-pair tiles (from the division) placed as related lesions. Output: labeled synthetic CT tiles. No phantom, no CT-physics sim. |
| F3 | Web demo | Cohort grid web render | open | Self-contained web page: cohort grid of CT tiles, per-tile decoded parameters, per-tile CHSH stamp, sibling-pair lineage badge ("gen 1 of ∞"), cohort-vs-rulebook strip (a histogram). **This is the MVP.** |
| F4 | *(optional)* QALife loop | Mode-A living-process arm | open | Turn the one-division hint into a real evolutionary loop: 2→4 cells over 2–3 generations, division + fate quantum, fitness/selection classical, **within-generation entanglement witness** per generation. Feeds an evolved lineage into F2/F3. The first honest living-process deliverable (full plan §5.2.5). |

---

## 3. Cross-Cutting Decisions (Global Architecture)

**Tech stack.**
- **Quantum / generation / imaging:** Python + Qiskit. `AerSimulator` for all development (free, instant); exactly **one** real `ibm_heron` job supplies the CHSH value and bits shown in the demo.
- **Web render:** self-contained **static** page (data + PNG tiles baked from one pipeline run; no live QPU calls from the browser). Hostable anywhere. Keep it a single deployable artifact — no backend required for the MVP.
- **No signing, no ledger, no database, no ML training, no CT-physics simulator, no phantom anatomy** in this epic (all deferred to the full plan).

**Architecture pattern — the one seam that matters.** All generation sits behind a `Sampler` interface and (where relevant) a `Certifier` interface:
```python
class Sampler(Protocol):
    def draw(self, rulebook: Rulebook) -> list[TumorParams]: ...
# implementations: PRNGSampler (baseline), QRNGSampler (F1), QALifeSampler (F4)
```
F2 and F3 must be **blind** to which sampler produced the params. This is what makes quantum methods swappable and what lets F4 drop in without touching the render.

**Separation of concerns.** The quantum device rolls the *life story* (params / trace); classical code *renders* it into a lesion and image. Never run the whole tumor on a QPU. Every quantum feature must have a job (full plan §5).

**Validation / honesty gates.** Each tile and the page header carry the honest label (params quantum, image classical). Do not claim non-classical tumors (§5.4). The CHSH value shown is the **real-hardware** value (sim is noiseless and misleads).

**Conventions.** This is a research study, following the repo's study workflow: **no GitHub issues, no test suite** (consistent with the other quantum studies). Plans live in `QuantumPhantoms/plans/`. Per-step detail comes from `/plan-feature`, not from this epic.

---

## 4. Shared Data Model Evolution

| Entity | Introduced In | Consumed By | Notes (Purpose) |
|--------|---------------|-------------|-----------------|
| `Rulebook` | F1 | F1, F3 | Published lung-nodule stats (size bands, type, margin, lobe + correlations) → circuit angles; also the reference for F3's cohort-vs-rulebook strip. |
| `QuantumRun` | F1 | F2, F3 | One job's result: raw bits, backend name, short job id, CHSH value, shot indices. |
| `TumorParams` | F1 | F2, F3, F4 | Decoded per-tumor: size, type, margin, lobe, `lineage_id`, `generation`. The `Sampler` output contract. |
| `Lesion` | F2 | F2, F3 | 3D blob derived from `TumorParams`. |
| `CohortTile` | F2 | F3 | Real CT slice + inserted lesion + label + provenance stamp; one grid cell. |
| `Generation` / `Lineage` | F4 | F4, F2, F3 | Evolutionary trace: clones per generation with survival/fitness; extends `lineage_id`/`generation` beyond the single division. |

---

## 5. State Changes / Workflows

* **Tumor (F1→F3):** `rolled (quantum bits)` → `decoded (TumorParams)` → `rendered (Lesion)` → `inserted (CohortTile)` → `displayed (grid)`.
* **Sibling pair (F1 division, P1):** `parent genotype` → `controlled-copy + Ry(θ_mut)` → `{daughter A, daughter B}` correlated by shared ancestry → two adjacent tiles with a lineage badge.
* **Cell, optional F4 Mode-A loop:** `born (prep)` → `measured (decode genotype/phenotype)` → fitness → `{survive → seed next generation | die}`; repeat for 2–3 generations. Per generation, record the entanglement witness before measurement collapses it.

---

## 6. Environment Specifics & Constraints

- **Quantum hardware access.** `ibm_heron` via IBM Quantum; development must not depend on it — `AerSimulator` is the default, one real job is the demo artifact. CHSH on real Heron ≈ 1.9–2.6 (noiseless sim gives ~2.83; use the real value on the page).
- **Data.** Real lung CT from public LIDC-IDRI / LUNA16 (TCIA). Rulebook stats from **published, citable** sources only (Fleischner / LIDC aggregates) — never fit to a private patient dataset (keeps it non-QML; full plan §2.3).
- **Coherence budget.** F1–F3 are shallow / constant-depth by construction. F4 Mode-A is measure-and-restart (constant depth per job) specifically to survive the coherence wall; deep coherent genealogy (Mode B) is **out of scope** — physically blocked on Heron today (see memory `qdep-setup-bug-fix`).
- **AI-generation honesty constraints.** Page must state params-quantum / image-classical; must not imply quantum imaging or a non-classical tumor; privacy framing ("modeled on no real patient") must stay accurate (image-domain insertion uses real public CT backgrounds — lesion is synthetic, background is a real public scan; word the claim about the *lesion/cohort selection*, not the background).
- **Framing for Siemens.** Lead with data credibility, not cryptography/security (Jan's rejected vocabulary; memory `siemens-thesis-healthcare-pivot`).

---

## 7. Implementation Order (Dependency Graph)

```text
F1 ─► F2 ─► F3  (the MVP)
 │
 └─► F4 (optional) ──► re-feeds F2/F3 render
```

- **F1 → F2 → F3** strictly sequential; each is a testable deliverable. F3 is the shippable MVP.
- **F4** depends only on F1 (the quantum core + `Sampler` seam) and reuses F2/F3 unchanged. Build it after F3 ships, only if the MVP lands and time allows. It is the bridge to the full living-process arm in the parent plan (§5.2.5).

---

*Parent plan:* `QuantumPhantoms/plans/siemens-8-certified-quantum-virtual-cohorts.md` (full study, Sections 1–13).
*Next:* run `/plan-feature` on F1 to detail the quantum-roll step.
