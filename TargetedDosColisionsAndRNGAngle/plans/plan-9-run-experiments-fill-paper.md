# Plan 9 — Run the live experiment matrix and fill the paper's `% TODO(P5)` blocks

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source:** new (post-P7, closes P5's live-run gap)
· **Priority:** `[MUST]`
**Status:** Superseded by plan-10 (2026-07-27). Deliverable A (the **live Mininet run**) was abandoned as the
results source — `plans/investigation-1.md` established the scapy/ARP hang and the broader env fragility, so the
Mininet/OVS/os-ken/scapy/iperf3 path was **deleted** (plan-10 File plan). Deliverables B (figures into `thesis/`),
C (`% TODO(P5)` fills + honesty reframe), and D (P6 Tier-B replay subset) are **fulfilled by plan-10** via a
deterministic flow-level simulator (`testbed/sim/`) over the real frozen mechanism. This plan is retained only as
history; execute `plans/plan-10-flow-level-simulation-results.md`, not this one. · **Depends on:** P2/P3/P4
(Complete, frozen), P5 (code Complete, live run not executed), P7 (its `% TODO(P5)` blocks — now filled by plan-10).
**Gates:** the plan-7 Manual Verification items 1, 3, 4, 10 are closed by plan-10 instead.

> Pick up with `/plan-feature plans/plan-9-run-experiments-fill-paper.md` after approval, or straight into
> `/implement-feature` once approved. Read `plans/plan-5-experiments-graphs.md` in full first — this plan drives
> the harness P5 already built, it does not rebuild anything. Then read `thesis/thesis.tex`'s S5/S6 stubs and the
> `% TODO(P5)` comments verbatim so the fill-in matches the surrounding prose register.
> **No automated tests** (project directive). Correctness is `testbed/analysis/analysis_check.py` (already
> exists, already passes) plus running plan-5's own Manual Verification steps 2–6 for real, this time against a
> live Mininet/OVS/controller stack instead of skipping them for lack of a root sandbox.

## Goal
Unblock the paper. Everything needed to produce real experimental data already exists in code
(`testbed/experiments/`, `testbed/analysis/`) — it has simply never been run end-to-end, because the P5
implementation session had no root/Mininet sandbox available. This plan (1) runs it, (2) copies the two
resulting figures into `thesis/`, and (3) rewrites `thesis/thesis.tex`'s S5 (Experimental Results), the empirical
half of S6 (Rotation-Frequency Specification), and the two commented-out figure blocks with real numbers traced
to the produced CSVs — nothing here re-derives or re-tunes the frozen hash/salt/defence/metrics mechanism.

## Non-negotiable ground rule (from the epic's own risk list, inherited here)
**Never fabricate a number.** If a cell fails to run cleanly (teardown leakage, a `503`/`429` that outlives the
qrng client's retry budget, a borderline saturation classification), that cell is re-run or explicitly marked
`skipped-with-reason` in the CSV and in the paper prose — it is never estimated, interpolated, or invented to
make S5/S6 look complete.

## Deliverable A — the live experiment run (environment, not code)
Run from `TargetedDosColisionsAndRNGAngle/`, on a host with root and a working Mininet + Open vSwitch install
(this sandbox has neither — confirmed during P7's implementation; this plan's execution step must happen on a
suitable host, not here):

1. `python testbed/analysis/analysis_check.py` first — confirms the offline analysis path is still clean before
   spending a live run on top of a broken analysis layer (it already passes per P5's Post-implementation note;
   re-run here only to catch drift since then).
2. `python testbed/experiments/run_experiments.py --exp 1` through `--exp 5`, then `--exp all` for the full
   matrix + both graphs, exactly as specified in plan-5's §Manual verification steps 2–6. `QEAAS_API_KEY` must be
   set in env for the Exp 4c/4d qrng cells (epic §8 Q6 — hosted `api.qeaas.eu`; `default` tier quota is ample).
3. Confirm per plan-5 step 6: `results/graph1_success_matrix.{png,svg}`, `results/graph2_rotation_threshold.{png,svg}`
   render from live data, and the Q4 replay subset (three-scene + QRNG + full rotation-interval sweep, blind
   skipped) exists under `RESULTS_DIR` for P6 Tier B.
4. If any cell needs a re-run (borderline saturation classification, a crashed qrng cell, Mininet teardown
   leakage into the next cell), re-run that cell per plan-5's own risk mitigations before treating the CSVs as
   final — do not patch around a bad cell in the paper prose.

## Deliverable B — figures into `thesis/`
Copy (do not re-plot, per epic §D-figures — a caption/data change means re-rendering `graphs.py` and re-copying,
never redrawing in the paper):
- `results/graph1_success_matrix.png` → `thesis/graph1_success_matrix.png`
- `results/graph2_rotation_threshold.png` → `thesis/graph2_rotation_threshold.png`

## Deliverable C — fill `thesis/thesis.tex`'s three `% TODO(P5)` blocks
All three blocks are already located and marked in the current file; this plan replaces each with real content,
not new sections:

1. **§Experimental Results (S5)** — currently a placeholder paragraph plus a commented-out Graph 1 figure. Replace
   with: a `booktabs` table (or short set of tables) reporting, per matrix cell, `saturated`, `min_victim_mbps`,
   Jain's index, and whether the defence fired, for Exp 1–4; state Exp 4's null result numerically (csprng vs
   qrng cells' Jain/throughput "numerically indistinguishable within noise" — quote the actual delta); uncomment
   and finalize the Graph 1 figure + caption against the real rendered PNG.
2. **§Rotation-Frequency Specification (S6), empirical half** — the analytic $T_{bf}=S/2r$ derivation already in
   the file stays untouched (frozen prose); append the Exp 5 empirical confirmation: measured
   `elapsed_seconds`/`attempts` from `reconstruct.py`'s `BruteForceResult`, the measured crossover rotation
   interval, and how closely it tracks the analytical $T_{bf}$ for the seed space actually in use. Uncomment and
   finalize the Graph 2 figure + caption against the real rendered PNG.
3. **Every numeric claim added in S5/S6 must cite its source row** — per plan-7's Manual Verification item 4,
   each number traces to a specific `results/*.summary.csv` or `*.record.json` row; keep that traceability
   implicit in precise, specific wording (e.g. "Exp 4b/4c: Jain 0.9x vs 0.9y") rather than vague ranges, so a
   reader can find the row.

## Deliverable D — close plan-7's remaining Manual Verification items
- **Item 1 (compiles clean):** this plan's implementer must have `pdflatex` (or `tectonic`) available — this
  sandbox does not. Run `pdflatex thesis/thesis.tex` twice and confirm no unresolved `\ref`/`\cite`, no
  missing-figure errors, in IEEEtran conference format.
- **Item 3 (both graphs render):** confirmed by Deliverable B once real PNGs exist in `thesis/`.
- **Item 4 (numeric traceability):** confirmed by Deliverable C's per-number sourcing.
- **Item 10 (venues named):** add a short submission-target note (title-page or a footnote) naming ACM ANCS /
  IEEE ICNP / IFIP Networking — currently absent from the draft; this was flagged as an open follow-up in P7's
  Post-implementation notes and is in scope here since it is a one-line addition, not new content.

## File plan
| File | Action | Notes |
|------|--------|-------|
| `results/graph1_success_matrix.{png,svg}` | **Create** (via live run) | Deliverable A. |
| `results/graph2_rotation_threshold.{png,svg}` | **Create** (via live run) | Deliverable A. |
| `results/**/*.summary.csv`, `*.record.json` | **Create** (via live run) | Gitignored per P5 OQ-5 — not committed, regenerable via `run_experiments.py`. |
| `thesis/graph1_success_matrix.png` | **Create** (copy from `results/`) | Deliverable B. |
| `thesis/graph2_rotation_threshold.png` | **Create** (copy from `results/`) | Deliverable B. |
| `thesis/thesis.tex` | **Edit** — fill the three `% TODO(P5)` blocks (S5, S6 empirical half, both figure blocks) + add the venue-naming note. | Deliverable C/D. No other section touched. |
| `plans/plan-7-writeup.md` | **Edit** — flip Manual Verification items 1/3/4/10 to confirmed with file:line evidence; update Status line to reflect the paper is now data-complete. | Housekeeping, mirrors how P5's own Post-implementation section was written. |

## Manual verification (no automated tests — project directive)
1. `python testbed/analysis/analysis_check.py` exits 0 (offline path still clean).
2. `run_experiments.py --exp 1` through `--exp 5` each produce a summary row matching plan-5's own §Manual
   verification expectations (Exp 1 defences fire on the flood; Exp 2–3 precision attacker saturates without
   tripping either defence; Exp 4a succeeds while 4b/4c fail and are numerically close; Exp 5's crossover tracks
   the analytical bound).
3. `results/graph1_*.svg` and `results/graph2_*.svg` exist and visually match the expected shapes described in
   plan-5 (3×3 grid with the null result visible; threshold curve with both thresholds marked).
4. `thesis/graph1_success_matrix.png` and `thesis/graph2_rotation_threshold.png` exist and `\includegraphics`
   resolves them.
5. `pdflatex thesis/thesis.tex` (twice) produces a clean PDF, no unresolved refs/cites, no missing-figure errors.
6. Every number added to S5/S6 is checked against its source CSV/JSON row by hand.
7. Re-read plan-7's Manual Verification checklist top to bottom and confirm items 1, 3, 4, 10 now pass.

## Out of scope
- Any change to `hash_core`, salt sourcing, rotation, the attacker, the defences, or the metrics collector/CSV
  schema — all frozen upstream (P2/P3/P4), consumed unchanged here exactly as P5 consumed them.
- Re-tuning P4's defence thresholds or re-deriving a new success predicate — P5's `success.py` definitions are
  reused unchanged.
- Any prose change to thesis.tex sections other than S5, S6's empirical half, the two figure blocks, and the
  one-line venue-naming addition — S1–S4, S7–S11 are frozen prose from P7 and are not touched.
- The Q1 fabric-wide multi-victim blast-radius measurement, the physical 10G hardware confirmation run, and any
  other P7 "Future Work" item — all explicitly out of scope for both P5 and P7, and stay out of scope here.
- P6 Tier B wiring — this plan produces the replay-subset data P6 Tier B would read, but does not touch P6's
  front-end or WebSocket layer.

## Risks
- **No root/Mininet sandbox in this environment.** Confirmed during P7's implementation. Deliverable A must run
  on a host with Mininet/OVS and root — flag this to the developer before starting; do not attempt to fake or
  simulate live results in an environment that cannot run the real testbed.
- **QRNG live dependency (Exp 4c/4d).** Inherited from P5's own risk list — a `503 low_quantum_entropy` or `429`
  mid-sweep could still occur; the P2 client already degrades/retries, and a qrng cell that never gets
  provenance is marked skipped-with-reason, never silently gapped or faked.
- **Mininet teardown leakage between cells.** Inherited from P5 — idempotent `mn -c` + controller SIGTERM before
  each cell; re-run a poisoned cell rather than accept its numbers.
- **Borderline saturation classification.** Inherited from P5 — flag borderline cells for re-run rather than
  silently recording a jittery result.
- **thesis.tex drift while this plan is in flight.** If the developer edits S1–S4/S7–S11 in parallel with this
  plan's S5/S6 work, the two edits could conflict. Mitigation: this plan touches only S5, S6's empirical
  paragraph, the two figure blocks, and one venue-naming line — a small, mergeable diff.

## Open questions — RESOLVED (2026-07-27, developer)
- [x] **OQ9-1 — where does Deliverable A actually run?** **RESOLVED: (a).** Developer runs the live experiment
  matrix (Deliverable A) on their own machine/lab host with root/Mininet/OVS, hands the resulting `results/` +
  figures back; Deliverable B/C/D (copy figures, fill thesis.tex, close P7's verification items) proceed from
  that handoff.
- [x] **OQ9-2 — venue-naming placement.** **RESOLVED: (b).** A one-line "Submission" remark near the Conclusion
  names ACM ANCS / IEEE ICNP / IFIP Networking — least disruptive to the IEEEtran title block.
- [x] **OQ9-3 — commit the raw per-cell CSVs, or only the two figures + replay subset?** **RESOLVED: no** — follow
  the existing P5 OQ-5 rule unchanged (gitignore raw CSVs, commit figures + Q4 replay subset only). Not reopened.
