# Feature Plan — R0: Refactor & backlog

**Ticket:** R0 (stage, not a GitHub issue — this research repo decomposes epics into sequential stages)
**Owning epic:** `artificial-life/plans/epic-qalife-darwinian-richness.md` (Status: **Approved** 2026-09-09)
**Slug:** refactor-backlog
**Author:** Claude (Opus)
**Date:** 2026-09-09
**Status:** Complete (implemented + manually verified 2026-09-09; OQ-1, OQ-2 approved)

> **No tests (repo convention, CD-7).** Verification is `--selftest` (operators vs paper
> closed-forms) + manual sim runs. No test framework, no test files.

---

## 1. Summary

R0 is a **pure reorganization** of `artificial-life/code/`. Today the folder holds 9 `.py`
files (5004 LOC) tangled by the verbatim-copy convention: two infra files, the canonical
Month-4 reproduction (model + driver, misleadingly prefixed `stage4_`), and five files from
now-refuted or other-epic lines. R0 makes the main folder hold **only** infra + the exact
reproduction, archives everything else to `code/backlog/` with an index, renames the
reproduction to drop the misleading `stage4_` prefix, and proves the reproduction still runs
identically after the move.

No new physics, no new operator, no hardware run. The **only** non-mechanical edit is fixing
one import line after the rename. Everything else is `git mv` + an index file + doc-comment
touch-ups.

This unblocks P1 (reconstruction baseline) by giving Phase-2 richness operators a clean
model file to plug into (CD-1).

---

## 2. Acceptance criteria (verbatim from epic §9)

- [x] **AC-R0.1:** main `code/` contains exactly the two infra files and the reproduction
  module(s); every other `.py` is moved (not copied) to `code/backlog/`.
  **Covered:** `code/` = `layout.py`, `qrng_client.py`, `qalife.py`, `run_qalife.py`;
  `code/backlog/` = the five archived `.py`. All moves are git `R` (rename, not copy).
- [x] **AC-R0.2:** `code/backlog/README.md` indexes each archived file — original name, role tag
  (refuted-C(g) / refuted-teleport / other-epic), verdict, and what supersedes it (pointing
  at the reproduction module or the relevant conclusion/runlog).
  **Covered:** `code/backlog/README.md` — index table (5 rows) + rename pointer + CD-9 header.
- [x] **AC-R0.3:** reproduction still runs — `--selftest` passes (all four operators verified vs
  the paper's closed-form values) and a small `--sim` run reproduces the Month-4 baseline
  witness within noise.
  **Covered:** `python qalife.py --selftest` → `SELFTEST PASS` (exit 0, all 4 operators + witness);
  `python qalife.py --sim --width 4 --steps 6 --seed 100` → output **byte-identical** to the
  pre-move capture (same alive counts, same pheno ⟨σ_z⟩). Driver sweep
  `run_qalife.py --sim --widths 3,4 …` → `W=4 ALIVE`, sep-null = 0.000.
- [x] **AC-R0.4:** pure move + import-fixup — no change to model/driver logic; the single real
  cross-file import is updated if renamed (CD-2).
  **Covered:** only functional edit = `run_qalife.py:44` `import stage4_qalife as q4` →
  `import qalife as q4`. Doc-comment touch-ups (OQ-2 approved) are text-only. No logic touched
  — proven by the byte-identical sim output.

**Conventions (epic §9):** `git mv` to preserve history; keep provenance comments in archived
files intact.

**Out of scope (epic §9):** any new physics, any new operator, any hardware run.

---

## 3. Out of scope

- Any P1+ science: banking the clean-witness reference dataset/figure is **P1**, not R0.
  R0 only proves the reproduction still *runs*; it does not produce a new banked baseline.
- Editing model/driver **logic** — no refactor of functions, no signature changes, no
  operator changes. Renames + one import fix + doc-comment text only.
- Touching `layout.py` / `qrng_client.py` internals (they stay verbatim).
- Making the five archived files runnable-in-place (CD-9: backlog is reference-only; their
  `sys.path`/sibling-copy assumptions may break after the move — that is accepted).
- Updating other-epic / backlog **plan docs** that reference the old filenames by path (see
  §11 OQ-1 — proposed: leave them, add a rename pointer in `backlog/README.md`).

---

## 4. Cross-cutting decisions applied (from epic §3)

| ID | Applied here |
|----|--------------|
| CD-1 | After R0, `code/` = `layout.py`, `qrng_client.py`, `qalife.py` (model), `run_qalife.py` (driver). Two-file reproduction (Q1). |
| CD-2 | Drop `stage4_` prefix: `stage4_qalife.py`→`qalife.py`, `stage4_scale.py`→`run_qalife.py`; fix the one import. |
| CD-9 | `backlog/README.md` records name→role→verdict→superseded-by; archived files are reference-only, not guaranteed runnable in place. |
| CD-10 | `_swap_cx`/`_teleport_cx` stay text-copied inside `qalife.py` (already are; not touched). |
| CD-7 | `--selftest` is the verification mechanism; no separate test framework added. |
| Q3 | `stage5_fliptest.py` archived to the **same** `code/backlog/` (no separate `virus/` sub-area); index note points to its home epic `plans/virus/`. |

---

## 5. Verified codebase facts (grounding the plan)

Confirmed by inspection on 2026-09-09:

- **Single functional cross-file import:** `stage4_scale.py:44` — `import stage4_qalife as q4`.
  Grep across `code/*.py` for `import stage[0-9]` returns exactly this one line. This is the
  **only** code edit beyond `git mv` (AC-R0.4).
- **Model is self-contained:** `stage4_qalife.py` imports only stdlib (`argparse`, `functools`,
  `json`, `math`, `os`, `random`, `typing`) + `numpy` + `qiskit`. No sibling imports. It stands
  alone as the honesty anchor (`--selftest` at line 453; `main()` at 532; `__main__` at 597).
- **Driver deps stay resolvable:** `stage4_scale.py` imports `stage4_qalife` (→ renamed),
  `qrng_client` (stays in `code/`), `layout.best_chain` (stays), and `pipeline_common`
  (resolved via existing `sys.path` shim at lines 60/67 — **not** a `code/` sibling, unaffected
  by the move).
- **Rename does NOT affect run output naming:** the `--name` defaults are run-tag strings
  (`qalife_s4_sim` in model, `qalife_m4` in driver), and `OUTPUT_DIR` is
  `../research_runs` via `__file__` — none reference the module filename. Renaming the files
  leaves `research_runs/` naming untouched.
- **Stale doc-comments after rename:** both files name the old filenames in their module
  docstrings / usage examples (`stage4_qalife.py:8,33,37,38`; `stage4_scale.py:2,4,23,24,25`)
  and one comment (`stage4_qalife.py:524` "in stage4_scale"). These are prose, not code — see
  §6 for the doc-comment touch-up (allowed under "import-fixup", keeps docs truthful).
- **Provenance headers present** in all five archive targets (each opens with a
  `"""Stage N (…)"""` docstring stating its role) — enough to write the index verdicts without
  guessing.
- **`code/` is git-clean** (not in the working-tree status), so `git mv` applies cleanly and
  preserves history.

---

## 6. File plan

All paths under `artificial-life/code/`. Use `git mv` for every move (AC-R0.1 convention).

### 6.1 Renames (reproduction module — CD-2)

| From | To | Edit beyond `git mv` |
|------|----|----------------------|
| `stage4_qalife.py` | `qalife.py` | Doc-comment touch-up only (§6.4). No logic change. |
| `stage4_scale.py` | `run_qalife.py` | Fix `import stage4_qalife as q4` → `import qalife as q4` (line 44). Doc-comment touch-up (§6.4). No logic change. |

### 6.2 Moves to `code/backlog/` (archive — CD-9)

| From | To | Role tag | Verdict / superseded-by |
|------|----|----------|-------------------------|
| `stage0_reproduce.py` | `backlog/stage0_reproduce.py` | refuted-C(g) | Simplified C(g) precursor. Superseded by `qalife.py` (the exact reproduction); C(g) line refuted (see `research/CONCLUSION_MONTH4.md`, memory `qdep-setup-bug-fix`). |
| `stage1_temporal.py` | `backlog/stage1_temporal.py` | refuted-C(g) | Temporal C(g) + measure-and-resend surrogate. Same refutation. |
| `stage2_scale.py` | `backlog/stage2_scale.py` | refuted-C(g) | C(g) scale sweep. Same refutation. |
| `stage3_teleport.py` | `backlog/stage3_teleport.py` | refuted-teleport | Teleport-routing; refuted twice on Heron-r2 (advantage inverts: readout-err ≫ 2q-err). Source of `_swap_cx`/`_teleport_cx` (now text-copied into `qalife.py`, CD-10). |
| `stage5_fliptest.py` | `backlog/stage5_fliptest.py` | other-epic | Stone-wall-virus epic Phase-0 kill-gate; a **different study** — home epic `artificial-life/plans/virus/epic-stonewall-virus.md`. Not part of this reproduction. |

`__pycache__/` is left as-is (git-ignored build artifact; not moved).

### 6.3 New file — `code/backlog/README.md` (AC-R0.2)

Index table with columns: **Original name · Role · Verdict · Superseded by**, one row per
archived file (content = the §6.2 table, prose-expanded). Plus:

- A header stating CD-9: these are **reference-only**, not guaranteed runnable in place; to
  resurrect one, fix its `sys.path`/sibling-copy assumptions deliberately.
- A **rename pointer** note (per §11 OQ-1 proposed default): "The Month-4 reproduction was
  renamed R0: `stage4_qalife.py` → `../qalife.py`, `stage4_scale.py` → `../run_qalife.py`.
  Backlog/other-epic plan docs that reference the old paths (`plans/virus/*`,
  `plans/OLD_feature-M4-web-demo.md`) still name the pre-rename files."

### 6.4 Doc-comment touch-ups (truthful docs; no logic — AC-R0.4)

Text-only edits inside the two renamed files so their own docstrings/usage examples name the
new files (a file whose `Usage:` block says `python stage4_qalife.py` after rename is simply
wrong). No code, no signatures, no behavior:

- `qalife.py`: docstring/self-references `stage4_qalife.py`→`qalife.py`, `stage4_scale.py`→
  `run_qalife.py` (lines ~8, 33, 37, 38, 524).
- `run_qalife.py`: docstring/usage `stage4_scale.py`→`run_qalife.py`, `stage4_qalife.py`→
  `qalife.py` (lines ~2, 4, 23, 24, 25).

These are in scope as part of "import-fixup" (keeping the module's own docs consistent with
its name). Provenance comments **inside archived files** are left intact (AC-R0.1 convention) —
only the two *reproduction* files get doc touch-ups.

### 6.5 Resulting layout (matches epic §5 "After")

```
code/
  layout.py                 # infra (unchanged)
  qrng_client.py            # infra (unchanged)
  qalife.py                 # was stage4_qalife.py — model + --selftest + witness
  run_qalife.py             # was stage4_scale.py — Heron-r2 driver (import fixed)
  backlog/
    README.md
    stage0_reproduce.py  stage1_temporal.py  stage2_scale.py
    stage3_teleport.py   stage5_fliptest.py
```

---

## 7. Implementation steps

1. **Capture pre-move baseline** (so "pure move" is provable). From `code/`, with a fixed seed:
   - `python stage4_qalife.py --selftest` → capture exit code + output.
   - `python stage4_qalife.py --sim --width 4 --steps 6 --seed 100` → capture the witness /
     separable-null print.
   Save both to the scratchpad for a post-move diff.
2. **Create backlog dir + move the five** with `git mv` (§6.2). Include `__pycache__` **not**.
3. **Rename the reproduction pair** with `git mv` (§6.1).
4. **Fix the one import:** `run_qalife.py` — `import stage4_qalife as q4` → `import qalife as q4`.
5. **Doc-comment touch-ups** (§6.4) in `qalife.py` and `run_qalife.py`.
6. **Write `backlog/README.md`** (§6.3).
7. **Verify** (§8) — selftest green + sim run byte-identical (modulo the filename in headers)
   to the step-1 capture; driver imports cleanly.

---

## 8. Manual verification (no tests — CD-7)

Run from `artificial-life/code/` after the move:

- **AC-R0.3a — selftest green:**
  `python qalife.py --selftest` → exit 0, all four operators (self-replication `CX`, mutation
  `Ry(θ)`, death amplitude-damping, interaction `SWAP`) report PASS vs the paper closed-forms.
- **AC-R0.3b — reproduction unchanged in sim:**
  `python qalife.py --sim --width 4 --steps 6 --seed 100` → witness clearly above the
  separable null (≈0); the printed numbers match the pre-move step-1 capture for the same seed
  (deterministic → identical, proving pure-move).
- **AC-R0.4 — driver still imports:**
  `python run_qalife.py --sim --widths 3,4 --steps 4 --interaction nn --death unitary` runs
  without `ModuleNotFoundError` (exercises the fixed `import qalife as q4` and the
  `q4.*` call sites at `run_qalife.py:98,101,103,123,218,270,315-322,340`). A short sim sweep
  is enough — no hardware (`--no-sim`) run (out of scope).
- **AC-R0.1 — folder shape:** `ls code/*.py` → exactly `layout.py qrng_client.py qalife.py
  run_qalife.py`; `ls code/backlog/*.py` → the five archived files.
- **AC-R0.2 — index present:** `code/backlog/README.md` exists with a row per archived file.
- **History preserved:** `git log --follow code/qalife.py` shows the pre-rename history.

If AC-R0.3b diverges from the pre-move capture, the move was **not** pure — stop and diff,
do not "fix forward."

---

## 9. Risks

- **R1 — hidden filename string dependency.** Mitigated: verified `--name` defaults and
  `OUTPUT_DIR` do not reference module filenames (§5); the only functional reference is the
  one import.
- **R2 — other-epic plans point at old paths** (`plans/virus/*`, `OLD_feature-M4-web-demo.md`).
  Not code (won't break execution); handled by the rename pointer in `backlog/README.md`
  (§6.3) rather than editing separate-epic docs. See §11 OQ-1.
- **R3 — `pipeline_common` resolution.** The driver resolves it via a `sys.path` shim, not a
  `code/` sibling — unaffected by the move. Confirmed present at `run_qalife.py:60,67`.

---

## 10. What P1 picks up next

R0 hands P1 a clean two-file reproduction + indexed backlog. P1 then banks the canonical
clean-witness reference (`⟨X^⊗W⟩` vs W/G with the separable null ≈0) — the fixed baseline
every richness run is judged against. R0 deliberately does **not** bank that dataset.

---

## 11. Open questions

**OQ-1 (proposed default — adopt unless the developer objects):** Other-epic / backlog plan
docs reference the old filenames by path — `plans/virus/epic-stonewall-virus.md`,
`plans/virus/feature-P0-fliptest.md`, `plans/OLD_feature-M4-web-demo.md`. These are planning
docs for deferred/other work, not code imports, so renaming does not break execution.
**Proposal:** leave those docs unchanged and add a one-line rename pointer to
`backlog/README.md` (§6.3). Editing separate-epic plans is out of R0's refactor scope.

**OQ-2 (proposed default — yes):** Update the two reproduction files' own docstring/usage
examples to the new filenames (§6.4), since a `Usage: python stage4_qalife.py` line becomes
false after rename. This is text-only, no logic. **Proposal:** yes — a module that misnames
itself in its own docs is a latent trap for P1+. (If the developer wants AC-R0.4 read
ultra-strictly as "import line only", these touch-ups can be dropped, leaving stale usage
examples.)

**Resolution (2026-09-09): both approved.** OQ-1 → other-epic plan docs left unchanged; rename
pointer added to `backlog/README.md`. OQ-2 → doc-comment touch-ups applied to `qalife.py`
(lines 8, 33, 37, 38, 524) and `run_qalife.py` (lines 4, 23, 24).

---

## 13. Post-implementation notes

**Built:** pure R0 refactor. `git mv` archived the five non-reproduction files to
`code/backlog/`, renamed the reproduction pair (`stage4_qalife.py`→`qalife.py`,
`stage4_scale.py`→`run_qalife.py`), fixed the single cross-file import, applied the approved
doc-comment touch-ups, and added `code/backlog/README.md` (index + rename pointer). No physics,
no operators, no hardware.

**Verified:** `--selftest` PASS; sim run byte-identical to the pre-move capture (deterministic
seed 100) → move is provably pure; driver imports and runs a short sim sweep (`W=4 ALIVE`,
sep-null 0.000).

**Follow-ups for the developer:**
- Changes are **staged** (`git mv` + edits) but **not committed** — commit when ready.
  Suggested message below.
- `git log --follow code/qalife.py` will only trace history through the rename **after** the
  commit lands (the rename is currently uncommitted); rename tracking is preserved (git `R`).
- Other-epic plan docs (`plans/virus/*`, `plans/OLD_feature-M4-web-demo.md`) still name the old
  filenames by design (OQ-1) — the `backlog/README.md` rename pointer covers this.
- Next stage: **P1** (reconstruction baseline) — bank the canonical clean-witness reference on
  this now-clean two-file reproduction. R0 deliberately did not bank that dataset.

---

## 12. Ground rules honored

- Every AC (R0.1–R0.4) is copied verbatim from epic §9 and mapped to a file-plan item + a
  manual-verification step.
- Concrete paths only; the single code edit (the import) and its line are named.
- No tests planned (CD-7); verification is `--selftest` + manual sim diff.
- Move-only + one import fix + truthful doc touch-ups; nothing refuted is destroyed (CD-9).
- No new physics / operator / hardware run (epic §9 out-of-scope respected).
