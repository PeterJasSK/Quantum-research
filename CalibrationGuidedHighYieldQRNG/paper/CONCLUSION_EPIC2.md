# Conclusion — EPIC 2 (Band-stratified evaluation)

**Status: preliminary pilot, not a validated result. Current design is a failed shot-budget
allocation, not a failed hypothesis — the calibration→yield signal showed up anyway, on data too
thin to trust.**

---

## 1. What was actually measured

Three bands of 5 qubits each (best/next/worst by a 100-shot run-time calibration ranking), Stage B
mid-circuit measure-reset sweep at depths 1/2/4/8, `shots_per_depth=20000`. Stage A quality
re-fit on a separate 65000-shot whole-chip run (R²=0.4842).

| Test | Result | n behind it |
|---|---|---|
| Spearman(predicted_quality, usable_depth) | rho=0.646, p=0.009 | 15 qubits |
| Kruskal-Wallis usable_depth across bands | H=7.11, p=0.029, monotone best≥next≥worst | 5 qubits/band |
| Per-qubit-per-depth NIST/next-bit/Markov battery | ran clean, verdicts computed | 20k–160k bits/stream |
| Worst-band harvested PDF stream | thin | 20,000 bits total (1 of 5 qubits contributed) |

Full detail: `Plans/feature-epic2-band-stratified-evaluation.md` §2, `results/bands_ibm_marrakesh_bands_*.json`.

## 2. Why this is "preliminary," not "confirmed"

- **15 qubits total, 5 per band** is a small-n pilot by any standard. The signal is directionally
  consistent (monotone order held on usable_depth and min-entropy at two depths) — that's the
  strongest evidence here, because it's a repeated qualitative pattern, not a fragile p-value.
- **20k–160k bits per Stage-B stream** is below the textbook NIST SP800-22 recommendation
  (~1,000,000 bits/test). The battery ran and produced verdicts — it did not run out of bits — but
  the verdicts carry less statistical weight per stream than the headline numbers imply at a
  glance.
- **The real miss:** shot budget was not sized against the question being asked. 5 qubits × 4
  depths × 20000 shots spends the free-tier budget breadth-first (many depths, few qubits) when
  the actual question — "does mid-circuit harvest depth beat a wider shallow harvest at equal bit
  cost" — needed a budget sized depth-first on fewer, better qubits. That's a design error, not a
  hardware or hypothesis failure.

## 3. Bottom line, stated plainly

This project, as designed, did not answer its central usability question: *is Heron r2's
mid-circuit measure-reset feature worth using over just reading out more (well-chosen) qubits
once?* The data collected can't isolate that, because best-band, next-band, and worst-band all ran
the *same* depth sweep — there is no same-bit-budget comparison between "many qubits, depth 1" and
"few best qubits, depth 4/8" anywhere in this dataset. Call EPIC 2 a preliminary indication with a
promising direction, not a working QRNG recipe yet.

---

## 4. Next study — the comparison that actually answers the question

**Research question:** at a fixed bit budget, does calibration-guided *deep* harvest on few
best-qubits beat calibration-guided *wide* harvest at depth-1 on many qubits? This is the real
"is the mid-circuit feature worth it" test — EPIC 2 never ran it.

### Design
Two arms, same total bit budget, same device/calibration snapshot:

| Arm | Qubits | Depth | Shots | Bits |
|---|---|---|---|---|
| **A — wide/shallow** | most/all healthy qubits from the 65000-shot Stage-A ranking (e.g. top ~100–156 by quality, exclude flagged) | 1 | sized so `n_qubits × shots = target_bits` | target_bits |
| **B — narrow/deep** | hand-picked top-5 (or top-N) qubits by the *same* 65000-shot predictor (not the noisy 100-shot ranking EPIC 2 was stuck with) | 4 and 8 (two sub-arms) | sized so `n_qubits × depth × shots = target_bits` | target_bits |

Pick `target_bits` from the free-tier `quantum_seconds` budget actually remaining, then solve
backward for shots per arm — budget the study around the answer, not around convenience.

### What each arm's result would indicate
- **A wins (wide/shallow ≥ narrow/deep bits/quantum-second, same quality battery pass rate):**
  mid-circuit reset isn't earning its keep on this device generation — the honest-failure result,
  stated cleanly, with a specific number behind it (ratio, not vibes).
  What could be done with it: usability write-up value — clearly means readout more qubits once instead of investing engineering effort in this
- **B wins:** the mid-circuit feature is worth the qubit-selection overhead — the real, specific
  "is it worth it" headline this study set out to produce. What could be done with it: this study would answer a specific relevant question, and would give a specific number/gain for Heron r2 usage in QRNG applications. Could motivate this to be tested on other devices ike (IBM Kingston or Fez) or applications
- **Wash (within noise):** still a usable result — "no detectable advantage either way at this bit
  budget on this device," which is a smaller, more defensible claim than the current
  best-vs-worst framing.

### Why this requires less bits than EPIC 2, not more
EPIC 2 spent 15×4=60 stream-evaluations to get an *indication*. This design needs only 3
stream-evaluations (arm A, arm B-depth4, arm B-depth8) at the *same total bit budget already
spent*, because the budget is pooled per arm instead of split thin across 5 qubits × 4 depths ×
3 bands. Same or less quantum time, one specific answer instead of five indicative ones.

### Prerequisites before running
- Fix qubit selection to the 65000-shot predictor from the start (D-E2.2's problem — freezing
  bands from a 100-shot ranking — should not repeat).
- Decide `target_bits` from the actual remaining free-tier budget before submitting, not after.
- No new evaluation code needed — reuse `eval_common.evaluate_stream` /
  `evaluate_stage_a.fit_predictor` unchanged; only the circuit submission (arm sizing) is new.
