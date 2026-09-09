# `code/backlog/` — archived reference files

**Reference-only (CD-9).** These files are kept for provenance and to be mined for patterns.
They are **not guaranteed runnable in place** — after the R0 move their `sys.path` / sibling
copy assumptions may break. To resurrect one, reference it and fix its paths deliberately.

The live `code/` folder now holds only infra (`layout.py`, `qrng_client.py`) + the exact
Month-4 reproduction: model `../qalife.py` + hardware driver `../run_qalife.py`.

## Rename pointer (R0)

The Month-4 reproduction was renamed in R0 to drop the misleading `stage4_` prefix
(it was never "stage 4" of a real staged program — it is the canonical model + driver):

- `stage4_qalife.py` → `../qalife.py`
- `stage4_scale.py`  → `../run_qalife.py`

Backlog / other-epic **planning docs** still name the pre-rename files — notably
`plans/virus/epic-stonewall-virus.md`, `plans/virus/feature-P0-fliptest.md`, and
`plans/OLD_feature-M4-web-demo.md`. Those are separate-epic planning documents (not code
imports); they were intentionally left unchanged in R0. Read them against the rename above.

## Index

| Original name | Role | Verdict | Superseded by |
|---------------|------|---------|---------------|
| `stage0_reproduce.py` | refuted-C(g) | Toolchain-proving reproduction of the 2018 model collapsed to a single temporal clone lineage measuring `C(g)`. The `C(g)` framing was refuted: it is a diagonal `⟨σ_z⟩` quantity with an exact classical surrogate. | `../qalife.py` (exact 4-operator reproduction); verdict in `research/CONCLUSION_MONTH4.md`. |
| `stage1_temporal.py` | refuted-C(g) | Temporal `c(d)` → `C(g)` machinery + measure-and-resend surrogate. Same refutation — the metric carries no non-classical content. | `../qalife.py`; `research/CONCLUSION_MONTH4.md`. |
| `stage2_scale.py` | refuted-C(g) | Scale sweep of the `C(g)` line on hardware. Same refutation; on Heron-r2 the supposed advantage physically inverts (readout error dominates two-qubit error). | `../qalife.py` + `../run_qalife.py` (the faithful-model scale axis, P2); `research/CONCLUSION_MONTH4.md`. |
| `stage3_teleport.py` | refuted-teleport | Teleport-routing to beat the SWAP depth ceiling. Refuted twice on Heron-r2 (constant-depth teleport still loses to depth-40 SWAP; mid-circuit readout is the dominant error channel). Source of `_swap_cx` / `_teleport_cx`, now **text-copied** into `../qalife.py` (CD-10). | `../qalife.py` (routing primitives live there for gated long-range richness); `research/CONCLUSION_MONTH4.md`, `research/RUNLOG_MONTH3.md`. |
| `stage5_fliptest.py` | other-epic | Stone-wall-virus epic **Phase-0** teleport-flip kill-gate — a **different study**, not part of this reproduction. | Home epic `../../plans/virus/epic-stonewall-virus.md` (+ `plans/virus/feature-P0-fliptest.md`). |
