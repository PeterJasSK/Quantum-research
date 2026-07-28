# Plan 7 — Write-up: the attack + mitigation paper

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 6** · **Priority:** `[MUST]`
**Status:** Data-complete via simulation (plan-10) — S0–S11 written into `thesis.tex`; S5/S6 filled with real
numbers and both figures embedded from the plan-10 flow-level simulation (P5's live run was superseded by
plan-10). Remaining: local `pdflatex` compile (MV item 1, no toolchain here) and, if the Q-EaaS provenance
endpoint recovers, the QRNG null-result cell (currently skipped-with-reason). **Depends on:** P5/P10 (both key
graphs) · related-work drafted in parallel per plan

> Pick up with `/plan-feature plans/plan-7-writeup.md`. Read epic §3.1 (locked framing), §3.2 (QRNG null result +
> practical angle), §3.4 (scale caveat), §6 (threat model), and §10 (novelty scan) first.
> **No automated tests** (project directive). This plan's deliverable is a LaTeX document; verification is the
> §Manual verification checklist (compiles clean; every claim traces to a figure/CSV; every citation body-verified).

## Goal
The attack + mitigation paper. It tells one argument: **a new attacker class that occupies the gap between rate
limiting and throttling → a mechanism-level defence (salt rotation) → a quantified rotation-frequency
specification**, with both key graphs and honest framing throughout. The paper doubles as the top-level narrative
that the testbed (P1–P5) and web demo (P6) exist to support.

## Deliverable — the paper written INTO `thesis/thesis.tex`, in place *(D-target, frozen)*
Per the developer's decision (2026-07-27): **use `TargetedDosColisionsAndRNGAngle/thesis/thesis.tex` as the exact
format template and write the ECMP paper into that same file, in place.** Do **not** create a new `.tex` file.

Critical fact the implementer must know: **`thesis.tex` currently holds a *different* paper** — the QRNG
"Bell-pair vs Hadamard cost–quality" study. This plan **replaces that content** with the ECMP Collision DoS paper,
**reusing its LaTeX scaffolding and house style verbatim** so the new paper is a drop-in sibling in the same format.
Reuse exactly, adapt only the content:
- `\documentclass[conference]{IEEEtran}` + the whole preamble/package set (`cite`, `amsmath`, `algorithmic`/
  `algorithm`, `graphicx`, `subcaption`, `booktabs`, `multirow`, `url`, `hyperref` with the same `hypersetup`).
- The author block unchanged: **Peter Jaš, Department of Computers and Informatics, Technical University of Košice**
  (same `\IEEEauthorblockN/A`). Update only `\title` and the keywords.
- The section skeleton and IEEEtran idioms: `\begin{abstract}`, `\begin{IEEEkeywords}`, `\section{Introduction}`
  with `\subsection*{Research Question}` / `\subsection*{Objectives}` / `\subsection*{Contributions}`, then
  Background → Methodology → Implementation (with `algorithm`/`algorithmic` blocks) → Results (`booktabs` tables +
  `figure`/`includegraphics`) → Discussion → Conclusion → `\section*{Acknowledgment}` → `\begin{thebibliography}`.
- The same table/figure/algorithm formatting idioms (`\toprule/\midrule/\bottomrule`, `[H]`/`[t]` placement,
  `\label{tab:..}`/`\ref`, `\includegraphics[width=0.95\linewidth]{...}`).

Note while editing: the current `thesis.tex` has two pre-existing corruptions from the old paper — a garbled block
around its lines 198–211 and a stray `\bibitem` embedded inside a table cell near line 400. Since this plan
**overwrites the body** with the ECMP paper, write clean content in their place; do not carry the corruption over.

### Decision D-figures — figures are P5 outputs, dropped into `thesis/` as PNG *(frozen here)*
The two key graphs are produced by P5's `testbed/analysis/graphs.py` at:
- **Graph 1** (attacker success × salt source × knowledge level): `results/graph1_success_matrix.png` / `.svg`
- **Graph 2** (rotation-frequency threshold curve): `results/graph2_rotation_threshold.png` / `.svg`

IEEEtran `\includegraphics` in `thesis.tex` references bare filenames in the same directory (e.g. `topology.png`,
`fig_segbias_fez.png`). So P7 **copies P5's `.png` outputs into `thesis/`** as `graph1_success_matrix.png` and
`graph2_rotation_threshold.png` and `\includegraphics` them by bare name. The paper **references** these files; it
does **not** re-plot from CSV — a caption/data change goes in P5's `graphs.py`, re-rendered, re-copied (mirrors P6's
no-drift discipline). Every numeric claim in the prose must trace to a P5 `results/*.summary.csv` /
`*.record.json` row (see §Manual verification).

## Framing rules (from the epic — non-negotiable)
- **Attack paper, not quantum paper** (§3.1). Lead with the DoS-defence-gap positioning. The attacker is defined
  by *what it evades* (Experiments 1–3), not just how it works.
- **QRNG null result stated plainly** (§3.2): QRNG buys nothing over CSPRNG *in this threat model*. Keep the
  practical QRNG angle — attestable entropy **provenance** (signed receipt, entropy epoch) and product
  demonstration — in a separate "practical deployment" note, never mixed into the attack-outcome claim.
- **Emphasis directive (2026-07-27, from the demo refactor):** the null result stays stated (scientific honesty is
  non-negotiable), but it should read as a **footnote/aside, not a heavy focus**. Lead the practical framing with
  **QEaaS viability** — per-switch quantum entropy delivered as a service, each draw carrying an attestable signed
  provenance receipt (entropy epoch, request id, source): auditable randomness a CSPRNG cannot provide. Concretely:
  do *not* headline "CSPRNG is sufficient"; state it once as a footnote and spend the practical-deployment note on
  provenance/attestation/audit + the QEaaS product (the P6 web demo is now framed this way — cite it as the
  reproducibility + product artefact). This is a framing/emphasis change only; no claim changes.
- **Finished-study voice with hardware as a concept** (Q3 decision, 2026-07-27): although the testbed work is a
  **preliminary/simulation study**, the paper is **written in the confident, completed voice of `thesis.tex`** — the
  QRNG paper reads as a finished study with a definite verdict, and this paper matches that register: state the
  findings as established results, not as work-in-progress. The one honesty valve is the **scale/hardware caveat**:
  present the real-hardware ("in metal") 10G confirmation as a **described concept / stated future direction**, not
  a completed run — the ratios are scale-invariant, so the simulation stands on its own and the metal run is framed
  as the concept that would close the absolute-numbers gap. Do not claim the hardware run was done.
- **Scale caveat honest** (§3.4): absolute time-to-saturation is lower on real 10G silicon; the findings are
  scale-invariant ratios. The optional single hardware-confirmation run is named as the **concept** that pre-empts
  the reviewer's scale objection (per Q3), not as executed work.
- **Multi-tenant cloud is the primary scenario** (§6); name microservices / SD-WAN / 5G core as secondary relevance.

## Paper structure — mapped onto the `thesis.tex` IEEEtran skeleton
Write these sections into `thesis.tex`, in this order, reusing the template's exact sectioning idioms. The § IDs are
for tracking; the LaTeX section titles are in the middle column.

| § | LaTeX section (mirror thesis.tex) | Must carry | Governed by |
|---|-----------------------------------|-----------|-------------|
| S0 | `\title{…}` + `\begin{abstract}` + `\begin{IEEEkeywords}` | New ECMP title; abstract stating attacker-in-the-gap → salt-rotation → cadence spec; keywords (ECMP, link-flooding DoS, salt rotation, moving-target defence, SDN, QRNG provenance). Author block unchanged. | §3.1, AC-3 |
| S1 | `\section{Introduction}` (+ `\subsection*{Research Question}`, `\subsection*{Objectives}`, `\subsection*{Contributions}`) | The gap between rate-limiting and throttling; the one-line mechanism delta from Crossfire/Coremelt (**single attacker + deterministic hash placement + one link, no botnet**); RQ/objectives/contributions in the thesis.tex idiom. | §3.1, §10 |
| S2 | `\section{Background and Threat Model}` | ECMP salt `link = hash(5tuple, salt) mod N`; predictable salt → craftable collision set on one egress link; salt lifecycle/rotation state (epic §5); multi-tenant-cloud primary scenario, secondary SD-WAN/microservices/5G. | §3.5, §5, §6 |
| S3 | `\section{Research Methodology}` (Experimental Design / Testbed / Attacker / Metrics subsections) | Mininet/OVS/Ryu testbed; three knowledge levels (full = upper bound, partial+Exp5 = realistic, blind = failure baseline); precision vs volumetric; the five metrics; run-tagging `(salt_source, knowledge_level, rotation_interval, attack_mode)`; **scale/hardware caveat as concept** here. | §3.4, §4, §8 Q3 |
| S4 | `\section{Implementation}` (with `algorithm` blocks) | The shared `hash_core`; `salt_source(kind)` prng/csprng/qrng; the collision crafter; rotation-as-controller-knob — expressed as `algorithm`/`algorithmic` pseudocode like thesis.tex's Alg. blocks. | §3.5 |
| S5 | `\section{Experimental Results}` (`booktabs` tables + `figure`s) | **Graph 1** (`graph1_success_matrix.png`) + **Graph 2** (`graph2_rotation_threshold.png`); Exp 1–3 evasion; Exp 4 rotation cost-free-when-no-attack incl. legitimate-flow reordering secondary metric (§8 Q2); the QRNG **null result** stated once here as an aside. | §3.2, AC-1/2, D-figures |
| S6 | `\section{The Rotation-Frequency Specification}` | "Rotate faster than N seconds given seed space S" — analytic curve mapped to seed-space brute-force time, confirmed empirically (Exp 5). The paper's actionable output. | §8 Q2, AC-1 |
| S7 | `\section{Discussion}` (subsections incl. Practical Deployment) | Answer the RQ; fabric-wide single-point-of-failure/repair (§6, qualitative per §8 Q1); **Practical Deployment note leads with QEaaS viability** (provenance/attestation/audit), null-result as a one-line footnote; cite P6 demo. | §3.2, §6, 2026-07-27 emphasis |
| S8 | `\section{Related Work}` (may sit before Discussion per venue norm) | The load-bearing distinctions — see §Positioning below. Full section written after P5 (§8 Q5); §10 novelty scan is the anchor. | §10 |
| S9 | `\section{Discussion} → Limitations & Future Work` subsections | Scale caveat recap + hardware "in metal" run **as concept/future** (Q3); MTD follow-on (address/port hopping on the same testbed); place epic in the unpredictability-as-primitive umbrella. | §3.4, §8 Q1, §10 |
| S10 | `\section{Conclusion}` | Restate attacker-in-the-gap → mechanism-level defence → cadence spec, in the finished-study voice. | §3.1 |
| S11 | `\section*{Acknowledgment}` + `\begin{thebibliography}{00}` | Keep the Acknowledgment idiom; body-verified `\bibitem`s only; verify-before-cite items flagged (§Positioning). | §10, AC-3 |

## Content the paper must carry (checklist against structure)
- Both key graphs from P5 (S5): `graph1_success_matrix.png`, `graph2_rotation_threshold.png` (D-figures).
- The Experiment 5 specification: "rotate faster than N seconds given seed space S" (S6).
- The ECMP-specific property linking new-place to new-solution (S7): controller-managed salt = fabric-wide single
  point of failure, so controller-level rotation is a fabric-wide fix.
- The QRNG null result **and** the QEaaS-viability practical note, correctly weighted (S5 aside + S7 lead).
- The scale caveat + hardware-as-concept (S3/S9) — ratios scale-invariant, absolute numbers context, metal run = concept.
- A pointer to the P6 web demo as reproducibility + product artefact (S7).

## Positioning & related work — load-bearing (epic §10 novelty scan)
The scan verdict: novel **only with careful positioning** — do NOT claim we invented single-bucket hash-flooding or
keyed-hash defence. Mandatory moves (land in S1 intro + S8 related work):
- **Early "distinction" paragraph** (in S1) against the two reviewer-killers: **RSS secret key** (MS NDIS / Linux
  `scaling.txt` — same attack+defence shape at the NIC RX-queue) and **single-shard flooding** (Nguyen & Thai,
  arXiv 2007.08600 / IEEE TDSC 2022). Own them up front — see epic §10 table for the exact differentiators.
- **One-line mechanism delta from Crossfire (S&P 2013) / Coremelt (ESORICS 2009)** in the intro: *single attacker +
  deterministic hash placement + one link, no botnet.* Adopt their "target link / legitimate-indistinguishable"
  vocabulary so reviewers place us correctly.
- **Reframe the defence contribution** to the fresh parts: **rotation-cadence vs salt-reconstruction-time** timing
  analysis + **QRNG calibration-ceiling null result** — not "we propose salt rotation" (known).
- **Soften the gap claim**: "first *ECMP-specific articulation* of the source-detection-immunity that
  Crossfire/Coremelt/LDDoS established," not "no prior attack has this property."
- **Baselines to cite/measure against, not reinvent:** SipHash (keyed-hash baseline), SPIFFY/CoDef (reroute-based
  link-flood defences to contrast rekeying against), Crosby & Wallach (HashDoS ancestor).
- **Position within Moving-Target Defence** (sibling `../study-ideas/Networking/4-mtd-sdn-hopping.md`): salt rotation
  is MTD on the ECMP hash → cite MTD lit (ACM MTD Workshop @ CCS, IEEE CNS); note the shared testbed enables a
  follow-on MTD hopping study as **future work** (S9). Frame the epic as one game in the
  **unpredictability-as-primitive** umbrella (sibling `../study-ideas/Networking/1-unpredictability-as-network-primitive.md`).
- **Verify-before-cite:** arXiv 2508.19283 (2025 DoS taxonomy), the "Depth Charge" source, and some PDF-only slides
  were **not** body-verified by the scan (§10 caveat) — confirm each by body text before it enters the
  `thebibliography`, or drop it.

## File plan
All paths relative to `TargetedDosColisionsAndRNGAngle/`. The deliverable is one edited-in-place `.tex`; no new `.tex`.

| File | Action | Notes |
|------|--------|-------|
| `thesis/thesis.tex` | **Edit in place** — replace the QRNG paper body with the ECMP paper (S0–S11), keeping the IEEEtran preamble, author block, and house style verbatim (D-target). | The deliverable. No new `.tex` (developer decision). |
| `thesis/graph1_success_matrix.png` | **Copy** from `results/graph1_success_matrix.png` (P5). | D-figures — `\includegraphics{graph1_success_matrix.png}`. |
| `thesis/graph2_rotation_threshold.png` | **Copy** from `results/graph2_rotation_threshold.png` (P5). | D-figures. |

No `paper/` directory, no Markdown deliverable — superseded by the D-target decision to write into `thesis.tex`.

## Dependencies on other plans (real status, 2026-07-27)
- **P5 (HARD — both graphs; Draft, not yet produced):** `results/graph1_success_matrix.png` and
  `results/graph2_rotation_threshold.png` come from `testbed/analysis/graphs.py`, which **exists** but P5 has not
  yet run the experiment matrix that feeds it (no `results/` outputs on disk). **The paper's Results (S5), the
  cadence spec (S6), and both figures are blocked on P5 producing real data.** S1–S3 and S8 (framing, threat model,
  methodology, related work) can be drafted now in parallel (§8 Q5). Do not invent numbers — a section that needs
  P5 data stays a stub with a `% TODO(P5)` LaTeX comment until the CSVs/figures exist.
- **P6 (soft — reproducibility artefact; Tier A complete):** cite the web demo (S7) as the browser-reproducible
  argument + QEaaS product surface. Point at its README / GitHub Pages URL once published.
- **Epic §10 (anchor, exists):** the novelty scan is the pre-built positioning source for S8.
- **Q-EaaS provenance (for S7):** the receipt/epoch/request-id field shapes come from P2's `SaltProvenance` (already
  landed) and the recorded record P6 displays — describe the fields, do not re-derive them here.

## Manual verification (no automated tests)
1. **Compiles clean:** `pdflatex thesis/thesis.tex` (twice, for refs) produces a PDF with no unresolved
   `\ref`/`\cite`, no missing-figure errors, in the IEEEtran conference format.
2. **Structure (AC-1):** the PDF contains, in order, the new-attacker section (S3) defined by what it evades (S5),
   the mechanism-level defence (S5), and the rotation-frequency spec (S6); both figures appear in S5. Read
   top-to-bottom and confirm the single argument holds without gaps.
3. **Both graphs render (AC-1, D-figures):** `thesis/graph1_success_matrix.png` and `graph2_rotation_threshold.png`
   are present, `\includegraphics` resolves them, and they match the current `results/` outputs (re-copy after any
   P5 re-render).
4. **Every numeric claim traces to data:** for each number/ratio in S5/S6, open the cited `results/*.summary.csv`
   or `*.record.json` row and confirm it. No claim without a backing row while P5 data exists; `% TODO(P5)` markers
   remain where it does not.
5. **QRNG framing weight (AC-2, emphasis directive):** the null result appears exactly once as a footnote/aside in
   S5; S7's Practical Deployment note leads with QEaaS viability + provenance/attestation and does **not** headline
   "CSPRNG is sufficient".
6. **Finished-study voice + hardware-as-concept (Q3):** the prose reads as a completed study with a definite verdict
   (matching thesis.tex's register); the 10G "in metal" run is described as a **concept/future direction**, never as
   executed work.
7. **Scale caveat present (AC-2):** S3 states ratios are scale-invariant, absolute numbers context.
8. **Positioning moves present (§10):** S1 carries the RSS-secret-key + single-shard-flooding distinction paragraph
   and the one-line Crossfire/Coremelt delta; S8 reframes the defence contribution to cadence-vs-reconstruction +
   QRNG null; the gap claim is softened to "first ECMP-specific articulation".
9. **Citations body-verified (§10 caveat):** every `\bibitem` is confirmed against its body text; the
   verify-before-cite items (arXiv 2508.19283, Depth Charge, PDF-only slides) are either confirmed or absent.
10. **Venues named (AC-3):** the title/front-matter or a submission note names ACM ANCS / IEEE ICNP / IFIP
    Networking; the IEEEtran conference class already fits IEEE ICNP.

## Out of scope
Everything upstream (P1–P6). This plan is the paper. Not in scope: producing the experiment data or figures (P5),
the interactive demo (P6), and a *new* `.tex` file (write into `thesis.tex` in place — D-target).

## Risks
- **Overwriting the wrong content:** `thesis.tex` holds the *QRNG* paper. Confirm with the developer that replacing
  it is intended (it is, per the 2026-07-27 decision) and, if the QRNG paper must be preserved, that a copy exists
  elsewhere before the body is overwritten. Keep the preamble/author block/style; replace only the paper body.
- **P5 data not ready** → the load-bearing Results/spec/figures block. Mitigation: draft S1–S3/S8 now; gate
  S5/S6/figures behind explicit `% TODO(P5)` markers; never fabricate numbers to unblock prose.
- **QRNG framing reads as motivated reasoning** → follow the 2026-07-27 directive exactly: null result once as a
  footnote, practical note leads with provenance/attestation, never "quantum stops the attack better" (§3.2).
- **Finished-study voice overclaims the hardware** → keep the "in metal" 10G run explicitly a concept/future
  direction (Q3); the confident register applies to the *simulation* findings (scale-invariant ratios), not to
  unrun hardware.
- **Reviewer-killer prior art** (RSS secret key, single-shard flooding) → own them in S1 up front; claim the ECMP
  instantiation + cadence defence + QRNG null, not the raw pattern (§10).
- **Citing unverified sources** → the §10 verify-before-cite list must be body-checked before the bibliography.
- **Figure drift from P5** → never re-plot in the paper; copy P5's `results/*.png` and re-copy after any re-render
  (D-figures).

## Open decisions — RESOLVED (2026-07-27, developer)
- **OQ-1 — format/target. [RESOLVED: LaTeX into `thesis.tex` in place.]** Use `thesis/thesis.tex` as the exact
  IEEEtran format template; write the ECMP paper into that file, overwriting the QRNG paper body, reusing preamble/
  author block/house style verbatim. **No new `.tex` file.** (D-target)
- **OQ-2 — one paper or split. [RESOLVED: single paper.]** One document in `thesis.tex`; do not split into per-section files.
- **OQ-3 — preliminary vs finished framing + hardware run. [RESOLVED: finished-study voice; hardware = concept.]**
  Write in the confident, completed register of thesis.tex and state findings as established; present the real-metal
  10G confirmation only as a **stated concept/future direction**, not executed work (leans on scale-invariant ratios).

## Resolved (epic §8, inherited)
- **Q5 — RESOLVED:** pre-build novelty scan done (epic §10). Full related-work section (S8) still written after P5.
- **Q1 — RESOLVED qualitative for v1:** the controller-managed-salt fabric-wide-single-point-of-failure argument
  stays qualitative (S7/S9), not a new measured experiment.
- **Q2 — RESOLVED:** rotation unit = per-time-interval; S5 reports the Exp 4 legitimate-flow reordering secondary
  metric; S6's x-axis is time.
- **Q3 (epic) — RESOLVED:** full/partial/blind kept separate; S3 states full = upper bound, partial+Exp5 =
  realistic, blind = failure baseline.

## Post-implementation

Written directly into `thesis/thesis.tex` (in place, per D-target), reusing the QRNG paper's IEEEtran preamble,
author block, and house style verbatim. New content: `\title`, abstract, keywords; S1 Introduction (mechanism
delta from Crossfire/Coremelt, RQ/objectives/contributions); S2 Background and Threat Model (ECMP hash, salt
lifecycle diagram, controller-managed-salt fabric-wide property, primary/secondary deployment scenarios); S3
Research Methodology (testbed topology, Exp 1-5 defined, five metrics, success predicate, scale caveat); S4
Implementation (`Algorithm` blocks for the shared hash core and controller rotation loop, matching
`testbed/hash_core.py::ecmp_link` and `testbed/controller/ecmp_controller.py::rotate_salt` respectively; salt
sources per `testbed/salt/sources.py`; collision crafter per `testbed/attacker/collision.py`; brute-force
reconstruction per `testbed/attacker/reconstruct.py`; defences per `testbed/controller/defences.py`); S5
Experimental Results (stub, `% TODO(P5)`); S6 Rotation-Frequency Specification (the $T_{bf} = S/2r$ derivation
and the $T_{rot} < T_{bf}$ cadence rule stated as the actionable spec; empirical confirmation stubbed
`% TODO(P5)`); S7 Discussion (RQ answer framed as an expectation pending P5, controller-managed-salt blast-radius
argument stated qualitatively, Practical Deployment note leading with QEaaS provenance/attestation and the null
result stated once as a footnote per the 2026-07-27 emphasis directive, positioning paragraph against RSS secret
key / single-shard flooding / Crossfire-Coremelt, MTD framing); S9 Limitations & Future Work (scale caveat +
hardware-as-concept per Q3, blast-radius as future work, MTD/unpredictability-umbrella future work); S10
Conclusion; S11 Acknowledgment + bibliography (8 body-verified `\bibitem`s: Crossfire, Coremelt, RSS secret key,
single-shard flooding, SipHash, SPIFFY, CoDef, Crosby & Wallach — the epic §10 "reviewer-killer" and "build on"
lists; none of the §10 verify-before-cite-and-unconfirmed items — arXiv 2508.19283, "Depth Charge", PDF-only
slides — were cited).

**Blocked on P5, left as `% TODO(P5)` per the epic risk mitigation (never fabricate numbers):** S5 Experimental
Results tables/prose, both figures (`graph1_success_matrix.png`, `graph2_rotation_threshold.png` — not copied,
since `results/` does not exist on disk; confirmed via `ls results/` and via P5's own Post-implementation note
that the five live experiments were not executed, only the offline analysis path), and the Exp 5 empirical
confirmation of the rotation-frequency threshold in S6.

**Manual verification status:**
1. **Compiles clean** — **still not verified locally**: no LaTeX toolchain (`pdflatex`/`tectonic`) is installed
   in this environment (plan-10 re-checked). Verified statically after the plan-10 S5/S6 fills: no `\ref` target
   without a `\label`, no `\cite` key without a `\bibitem`, no leftover `TODO(P5)`/placeholder, both embedded
   figure files present in `thesis/`. **Developer must run `pdflatex thesis/thesis.tex` (twice) locally before
   treating this as compile-confirmed.**
2. **Structure (AC-1)** — new-attacker section (S3/S4) → mechanism defence (S4/S7) → rotation-frequency spec
   (S6) present in order; both figures stubbed with `% TODO(P5)`, not fabricated.
3. **Both graphs render** — **confirmed (via plan-10 simulation)**: `results/graph1_success_matrix.{png,svg}` and
   `results/graph2_rotation_threshold.{png,svg}` render from `testbed/analysis/graphs.py`, and both PNGs are copied
   into `thesis/` and embedded (`thesis/thesis.tex` Fig.\ `fig:graph1` in §Experimental Results, Fig.\ `fig:graph2`
   in §The Rotation-Frequency Specification).
4. **Numeric claims trace to data** — **confirmed (via plan-10 simulation)**: S5's `booktabs` results table
   (`thesis/thesis.tex` `tab:results`) and S6's empirical crossover ($10$\,s vs analytical $T_{\mathrm{bf}}\approx
   14.8$\,s) each trace to a `results/*.summary.csv` row (e.g. `results/exp2/exp2_precision_vs_ratelimit.summary.csv`,
   `results/exp4/exp4b_csprng_rotation.summary.csv`, `results/exp5/*.summary.csv`). The QRNG cell is honestly marked
   skipped-with-reason (endpoint unavailable), not fabricated.
5. **QRNG framing weight (AC-2)** — null result stated once in S5 stub prose and once as a one-line footnote
   opening §Practical Deployment (S7); Practical Deployment leads with QEaaS provenance/attestation, does not
   headline "CSPRNG is sufficient" — `thesis/thesis.tex:` §"Practical Deployment: QRNG-as-a-Service Viability".
6. **Finished-study voice + hardware-as-concept (Q3)** — prose throughout (S1-S4, S7, S10) states findings in
   completed-study register; the 10G "in metal" run is named as a concept/future direction only
   (§Limitations, §Future Work) and never as executed work.
7. **Scale caveat present (AC-2)** — stated in S3 (`\subsection*{Scale Caveat}`) and recapped in §Limitations.
8. **Positioning moves present (§10)** — S1 carries the one-line Crossfire/Coremelt mechanism delta; §Positioning
   Against Adjacent Work (S7) carries the RSS-secret-key and single-shard-flooding distinction paragraph, the
   gap-claim softened to "first ECMP-specific articulation," and the MTD/unpredictability-umbrella framing.
9. **Citations body-verified** — the 8 cited works are the epic §10 pre-verified reviewer-killer/build-on list;
   the explicitly-unverified items from that scan were not cited.
10. **Venues named (AC-3)** — **confirmed**: a submission note naming ACM ANCS / IEEE ICNP / IFIP Networking is
    present in the Conclusion (`thesis/thesis.tex`, final sentence of §Conclusion).

**Follow-ups for the developer:**
- ~~Run P5's live testbed matrix~~ — **done via plan-10** (`python testbed/sim/run_sim.py --exp all`): S5/S6
  filled, both PNGs copied into `thesis/`.
- Install a LaTeX toolchain and compile (`pdflatex thesis/thesis.tex` twice) to confirm no `\ref`/`\cite` or
  layout errors beyond the static checks — still outstanding (no toolchain in the plan-10 environment).
- ~~Add the AC-3 venue-naming note~~ — **done** (Conclusion submission note).
- If the Q-EaaS keyed provenance endpoint recovers, re-run the QRNG cells to replace the skipped-with-reason
  entry with the measured 4b≡4c null result and the real receipt: `set -a && . ./.env && set +a && python
  testbed/sim/run_sim.py --exp 4` then `python testbed/sim/replay_export.py`.
