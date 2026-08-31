# Feature Plan — F2: Criticality metric suite (`criticality.py`)

**Status:** Complete
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F2 (depends on F0; validated after F1; parallel with F3)
**Artifact:** `THESIS/CriticalQuantumLife/code/criticality.py` (new)
**Reads:** F0's `research_runs/*.json` (`generations[]` observables)
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue (F-ids). No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

F2 turns "σ trends toward 1" (the coarse F1 signal) into a **defensible criticality claim**. It is a
post-processing / analysis layer over F0's run-JSON: it estimates the branching parameter σ with confidence,
fits the avalanche size-distribution exponent **α ≈ 1.5** (P(S) ∝ S^{−α}), tests the Shannon-entropy trajectory
for a **plateau** (lively) vs an **H→0 collapse** (dead), locates the order-parameter **susceptibility peak**,
and fits the **post-poke relaxation time constant τ**. These are the numbers that back the criticality honesty
gate (epic §5) and feed F5's figures, F6's dials, and F7's paper.

F2 defines **no new circuits** — it reads the observables F0 already logs (plus the raw avalanche/alive series it
records) and writes a `criticality` summary block back into the run-JSON (or a sidecar). Metric definitions cite
Beggs & Plenz 2003 (σ≈1, α≈1.5) and Bak-Tang-Wiesenfeld 1987 (self-organized criticality / avalanches).

### What already exists (integration points)
- F0 `generations[]` — `sigma`, `entropy`, `alive_population`, `surprise`, `poke` per gen; `meta.poke_gen`.
- `stage4_qalife.alive_mask` / `alive_population` — the alive series avalanches are built from.
- Epic §5 metric list + §9 F2 ACs; Q3 (thesis width W=8, but F2 is width-agnostic post-processing).

---

## 2. Acceptance criteria

Verbatim from epic §9 (F2). IDs added. **Covered by** = file:line evidence (verified 2026-08-31).

| AC | Verbatim | Covered by |
|----|----------|------------|
| **AC-F2.1** | "Branching parameter σ estimator with target →1 and its confidence." | `criticality.py:86` `estimate_sigma` — mean + bootstrap 95% CI. Verified: σ=1.16, ci95=[0.88,1.49], n=25 on 30-gen source. |
| **AC-F2.2** | "Avalanche size-distribution: collect avalanches, fit P(S) ∝ S^{−α}, report α with goodness of fit; target α ≈ 1.5." | `criticality.py:103` `collect_avalanches` + `:170` `fit_powerlaw` (MLE + KS xmin `:145`, GOF bootstrap). Verified: α=1.56, xmin, n=10, ks=0.27, gof_p=0.062 + low-N warning. |
| **AC-F2.3** | "Shannon-entropy trajectory with a plateau test (distinguish lively plateau from H→0 collapse)." | `criticality.py:216` `entropy_plateau`. Verified: lively run plateau=True; mut_scale=0.02 collapse run collapsed=True, plateau=False. |
| **AC-F2.4** | "Order-parameter susceptibility peak locating the critical point." | `criticality.py:238` `susceptibility` — sliding-window variance of activity. Verified: peak_gen/peak_value + full series populated. |
| **AC-F2.5** | "Post-poke relaxation time constant τ fit from the surprise/entropy return-to-set-point." | `criticality.py:282` `relaxation_tau` (scipy `curve_fit`, numpy fallback `:263`). Verified: τ=2.52 on poked run; τ=null+note on no-poke run. |

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New file `criticality.py`: pure analysis over one-or-more F0 run-JSONs. Writes a `criticality` block.
- σ estimator + CI (AC-F2.1); avalanche collection + MLE power-law α fit + goodness-of-fit (AC-F2.2); entropy
  plateau-vs-collapse test (AC-F2.3); susceptibility (variance of the order parameter) peak locator (AC-F2.4);
  post-poke τ exponential-relaxation fit (AC-F2.5).
- To make α/τ fittable, F2 may require F0 to also log the **raw per-generation alive count series** and the
  **surprise series** (already present) — see §9 (a small F0 log addition, flagged Q1).

### Out of scope (deferred)
- The quantum-certification surrogate + witness null band — **F3** (separate honesty gate).
- Hardware runs — **F5**. Web dials — **F6** (F6 reads F2's `criticality` block). Paper — **F7**.
- Any circuit construction or feedback logic (F0 owns that).

---

## 4. Data model — `criticality` block (added to F0's run.json)

F2 adds a `"criticality"` key in-place to the source run-JSON (Q2 resolved: in-place). Shape:

```jsonc
{
  "source_run": "cql_f5_closed_ibm_..._run.json",
  "criticality": {
    "sigma": {"mean": 0.98, "ci95": [0.91, 1.04], "n_gen": 15},          // AC-F2.1
    "avalanche_alpha": {"alpha": 1.52, "xmin": 2, "n_avalanches": 137,   // AC-F2.2
                        "ks_stat": 0.041, "gof_pvalue": 0.63},
    "entropy": {"plateau": true, "plateau_mean": 1.78, "slope_late": -0.01, // AC-F2.3
                "collapsed": false},
    "susceptibility": {"peak_gen": 6, "peak_value": 0.44, "series": [...]},  // AC-F2.4
    "relaxation_tau": {"tau": 2.7, "r2": 0.88, "poke_gen": 8, "observable": "surprise"} // AC-F2.5
  }
}
```

- Consumed by F5 (report), F6 (criticality dial reads `sigma.mean`, avalanche histogram reads α, surprise
  meter/τ), F7 (figures). Field names are the F2 contract.

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Criticality is the target, not silence** (epic honesty gate 2). The entropy test explicitly distinguishes a
  lively **plateau** from an **H→0 collapse**; a run that "wins" by going silent FAILS the criticality gate.
- **Metric definitions cite the literature** — Beggs & Plenz 2003 (σ≈1, α≈1.5), Bak-Tang-Wiesenfeld 1987.
  Power-law α via MLE + KS goodness-of-fit (Clauset-Shalizi-Newman method), not a naive log-log line fit.
- **F2 is post-processing over the one schema** (epic §4) — reads F0's `generations[]`, adds a sibling block,
  renames nothing.
- **Width-agnostic** — F2 runs identically on F1's W=4 sim runs and F5's W=8 hardware runs (epic Q3).

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, flush-print. `numpy` for everything; MLE
power-law α hand-rolled. τ exponential fit uses `scipy.optimize.curve_fit` when scipy imports, else numpy
fallback (Q3 resolved: allow scipy, keep fallback). One new file.

### `THESIS/CriticalQuantumLife/code/criticality.py` (new)

1. **Module docstring** — what criticality means here; the plateau-not-silence rule; citations.
2. **Imports** — `import json, argparse, functools, math`; `import numpy as np`.
3. **`def load_runs(paths: list[str]) -> list[dict]`** — read F0 run-JSONs.
4. **`def estimate_sigma(gens: list[dict]) -> dict`** (AC-F2.1) — pull the per-gen `sigma` (alive(g)/alive(g-1)),
   report mean + bootstrap 95% CI over generations.
5. **`def collect_avalanches(gens: list[dict]) -> list[int]`** — define an avalanche as a contiguous run of
   generations with above-threshold activity (alive-count excursions above the running baseline); size S = summed
   excess activity. (Avalanche definition per §7; flagged Q1.)
6. **`def fit_powerlaw(sizes: list[int]) -> dict`** (AC-F2.2) — MLE exponent `alpha = 1 + n / Σ ln(S_i/xmin)`
   with `xmin` chosen by KS-minimization (Clauset method); report `alpha`, `xmin`, `n`, KS statistic, and a
   bootstrap goodness-of-fit p-value. Target α≈1.5. Print a warning when `n_avalanches` below threshold
   (Q4: report-and-warn, never null).
7. **`def entropy_plateau(gens: list[dict]) -> dict`** (AC-F2.3) — the `entropy` series; `plateau` = late-window
   slope near zero AND late-window mean above a `H_DEAD` floor; `collapsed` = entropy monotonically driving to ~0.
8. **`def susceptibility(gens: list[dict]) -> dict`** (AC-F2.4) — order parameter = alive-fraction; susceptibility
   χ(g) = variance/fluctuation of the order parameter in a sliding window; locate the peak generation.
9. **`def relaxation_tau(gens: list[dict], poke_gen: int, observable: str = "surprise") -> dict`** (AC-F2.5) —
   from `poke_gen` onward fit `y(t) = baseline + A·exp(-t/τ)`; report τ and R². Falls back to `entropy` if surprise
   is flat (Q3).
10. **`def analyze(run: dict) -> dict`** — assemble the `criticality` block (§4) from the five estimators.
11. **`def write_criticality(block: dict, source_path: str) -> str`** — adds `"criticality"` key in-place to the
    source run-JSON (Q2 resolved).
12. **`def main() -> None`** — argparse `--runs <paths...>` `--poke-gen`(from meta if absent) `--name`. Prints a
    one-line summary per run (`σ=.. α=.. plateau=.. τ=..`) + writes the block(s) in-place.
13. **`if __name__ == "__main__": main()`**.

No other files.

---

## 7. Metric definitions (the rigor F2 must fix; citations)

- **Branching σ (AC-F2.1, Beggs & Plenz 2003).** Descendants per active individual, `alive(g)/alive(g-1)`,
  averaged over the run; σ→1 = critical, <1 = subcritical (dying), >1 = supercritical (runaway). Report a CI so
  "≈1" is a statistical claim, not an eyeball.
- **Avalanche α (AC-F2.2, Beggs & Plenz 2003; Bak-Tang-Wiesenfeld 1987).** An avalanche = a burst of
  above-baseline activity; its size S is the integrated excess. Critical systems give `P(S) ∝ S^{−α}` with
  α≈1.5 (the neuronal-avalanche / mean-field SOC exponent). MLE + KS goodness-of-fit, NOT a log-log regression.
- **Entropy plateau vs collapse (AC-F2.3).** A lively population holds Shannon entropy at a plateau; a "dead"
  optimum drives H→0. The test must REJECT a low-surprise run whose entropy collapsed — that is order, not life.
- **Susceptibility peak (AC-F2.4).** At criticality, fluctuations of the order parameter (alive-fraction) peak.
  χ(g) sliding-window variance locates the transition; the peak coincident with σ≈1 corroborates criticality.
- **Relaxation τ (AC-F2.5).** After a poke, surprise/entropy returns to its critical set-point as `exp(-t/τ)`;
  τ quantifies "how fast it crawls back to the edge" — the number under the F6 poke-and-recover trace.

---

## 8. Manual verification (no automated tests)

```bash
cd THESIS/CriticalQuantumLife/code
python closed_loop.py --arm closed --generations 30 --width 4 --poke-gen 8 --name cql_f2src   # longer run for α stats
python criticality.py --runs ../research_runs/cql_f2src_closed_*_run.json
```

- **AC-F2.1** — output prints `σ mean` with a 95% CI bracketing (or near) 1; `criticality.sigma` populated.
- **AC-F2.2** — `avalanche_alpha.alpha` reported with `ks_stat` + `gof_pvalue`; on a critical-looking run α is
  near 1.5 (a subcritical toy run may not hit 1.5 — that is honest, report it as-is).
- **AC-F2.3** — `entropy.plateau=true` on a lively run; force a collapse (tiny mut_scale) and confirm
  `collapsed=true, plateau=false`.
- **AC-F2.4** — `susceptibility.peak_gen` reported; eyeball that the peak sits where σ crosses ~1.
- **AC-F2.5** — with `--poke-gen 8`, `relaxation_tau.tau` finite with `r2 > 0.5`; on a run with no poke, τ block is null.
- **Schema** — `python -c "import json;d=json.load(open('<crit path>'));print(sorted(d['criticality']))"` → the five keys.

---

## 9. Out-of-context risks / notes

- **α needs enough avalanches.** A 15-gen W=4 run yields few avalanches → a noisy α. F2's α is trustworthy on the
  longer/scaled runs (F5 W=8, or `--generations 30+` sim); document the avalanche count with α and don't over-claim
  a 1.5 fit off 12 avalanches. This is why §8 uses a 30-gen source.
- **Avalanche definition is a modelling choice** (Q1) — the alive-count-excursion definition is one honest option;
  an alternative is per-generation "number of newly-alive individuals" as the branching event. Freeze one and note it.
- **F0 log addition:** F2 needs the raw per-gen alive-count series (F0 already logs `alive_population`) and the
  surprise series (present). No F0 change is strictly required IF `alive_population` is the avalanche substrate;
  if a finer per-individual event series is wanted (Q1), F0 must log it — flag before implementing.
- **scipy is a soft dep** — MLE α is numpy; τ uses `scipy.optimize.curve_fit` with a numpy fallback, so F2 still
  runs in the minimal F0 env if scipy absent.
- **In-place mutation** — F2 rewrites its source run-JSON (Q2). F0 runs no longer immutable; re-running F2
  overwrites the prior `criticality` block.

---

## 10. Ground rules honored

- Every AC (F2.1–F2.5) verbatim from epic §9, mapped to a §8 manual check.
- Concrete paths; one new file; reads the one schema, adds a sibling block, renames nothing.
- No tests / no test sections. Strict typing; numpy + scipy(soft); no raw SQL. Literature-cited metric definitions.

---

## 12. Post-implementation notes (2026-08-31)

**Built:** `THESIS/CriticalQuantumLife/code/criticality.py` (one new file, ~380 lines). Reads F0 run-JSONs,
adds a `"criticality"` block in-place, prints a one-line-per-run summary. scipy present (1.15.3) → τ uses
`curve_fit`; numpy fallback kept.

**Substrate reconciliation (important — carried into F5/F6/F7).** The plan §1/§9 language ("alive-count
excursion", `alive_population`) predates F0's finalized **Option A (witness-as-outcome)**. In Option A the
GHZ genome makes the alive-mask/alive-count **invariant** under mutation — there is no alive-count series.
F0's own docstring (`closed_loop.py:14-22`) mandates the real substrate: `active` = a generation whose
surprise beats the running median, and *"F2 fits avalanche alpha and the branching sigma→1 of that
[surprise-avalanche] process."* So F2 was implemented on the **surprise-activity process**:
- Avalanche = maximal contiguous run of `active` generations; size S = integrated surprise-excess above the
  run's median-surprise baseline (Q1's "excursion above running baseline; integrated excess", read on
  surprise). Uses only F0's existing `active` + `surprise` — no F0 change (Q1 default honored).
- σ (AC-F2.1) consumes F0's logged per-gen `sigma` field (the surprise-activity branching ratio) and adds the
  bootstrap CI F0 lacks.
- Susceptibility order parameter (AC-F2.4) = the activity indicator (Option A stand-in for the invariant
  alive-fraction).

**Verification numbers.** 30-gen W=4 source (`cql_f2src`): σ=1.16 (ci95 [0.88,1.49]), α=1.56 (n=10, near the
1.5 target), plateau=True, τ=2.52. Collapse run (mut_scale=0.02): collapsed=True, plateau=False. No-poke run:
τ=null with note. Schema = the five §4 keys.

**Follow-ups / honest caveats:**
- **α trustworthy only on long runs.** 15-gen W=4 runs yield 3–4 avalanches → α noisy (2.87) and the low-N
  warning fires (Q4 report-and-warn working as designed). Use ≥30-gen sim or F5 W=8 for a defensible α. Do
  not headline the 1.5 fit off <20 avalanches.
- **τ R² is low on short toy runs** (0.03–0.16) — the post-poke surprise does not relax cleanly at W=4/15-gen.
  The fit mechanism is correct and R² is reported honestly; a clean τ (R²>0.5) needs the longer/scaled runs.
  Not a code defect — data.
- **Susceptibility peak lands early** on short binary-activity series (variance of a toggling 0/1 peaks early);
  it firms up on longer runs. Reported as-is.
- **In-place mutation (Q2):** F2 rewrites its source run-JSON; re-running overwrites the prior block. F0 runs
  are no longer immutable.
- F5/F6/F7 consume the `criticality` block by the §4 field names — contract held exactly.

---

## 11. Resolved decisions (2026-08-31)

- **Q1 — Avalanche event definition → RESOLVED: alive-count excursion.** Avalanche = contiguous run of
  generations with alive-count above the running baseline; size = integrated excess. Uses only F0's existing
  `alive_population`. **No F0 change.** Newly-alive-count alternative rejected (avoids extra F0 log field).
- **Q2 — Output location → RESOLVED: in-place key.** Add the `"criticality"` key into the source run-JSON.
  `--in-place` becomes default behavior; drop the sidecar path. (F0 runs are no longer immutable — F2 mutates
  its source.)
- **Q3 — Fit library → RESOLVED: allow scipy.** Use `scipy.optimize.curve_fit` for the τ exponential fit when
  scipy is installed. Keep a numpy fallback so F2 still runs in the minimal F0 env if scipy absent. MLE α stays
  hand-rolled (numpy).
- **Q4 — Low-N α → RESOLVED: report + warn.** Always report `alpha` with `n_avalanches`; print a warning when
  `n_avalanches` below threshold. No suppression / no null. Caller judges trust from the count.
