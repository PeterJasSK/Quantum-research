# Feature Plan — F0: Closed-loop engine + core observable suite (`closed_loop.py`)

**Status:** Complete
**Epic:** `THESIS/CriticalQuantumLife/plans/epic-critical-quantum-life.md` (Status: **Approved**)
**Ticket ID:** F0 (first of 8; no dependency — gates F1–F5)
**Artifact:** `THESIS/CriticalQuantumLife/code/closed_loop.py` (new)
**Forks:** `artificial-life/code/stage4_qalife.py` (genome + witness), `qrng_client.py`, `layout.py`
**Mirrors:** `THESIS/CriticalQuantumLife/proof_of_concept/quantum_life.py` (per-gen closed-loop shape)
**Author:** Claude (Opus) · **Date:** 2026-08-31

> No GitHub issue — this study uses F-ids, not tickets (repo directive).
> No tests (project directive): production code + manual verification only.

---

## 1. Context & goal

F0 is the shared spine of the whole epic. It forks the recreated 2018 quantum-artificial-life
engine (`stage4_qalife.py`) into a **closed-loop** engine: each generation the population measures
its own outcome, gets feedback **contingent** on that outcome (predictable when the outcome was
expected, high-entropy QRNG-seeded when it was surprising), then selects / reproduces / mutates.
It also ships the **yoked-control** runner (same stimulation, feedback scrambled) and the
**observable logger** that writes the one run-JSON schema every other ticket (F1–F7) reads.

F0 imports the genome primitives and the `⟨X^⊗W⟩` witness from `stage4_qalife.py` — it does **not**
re-derive them (epic CD "reuse the engine; do not rewrite it"). New code = the closed loop, the
yoked control, the surprise/σ/entropy observables, and the JSON writer.

F0 fixes three things the rest of the epic depends on and must not re-decide:
1. The **run-JSON schema** (`meta` + `generations[]` core fields) — §4.
2. The **closed-loop feedback contract** (what "outcome", "expected", "surprising", "feedback" mean) — §7.
3. The **yoked-control definition** (same stimulation sequence, feedback decoupled from outcome) — §7.

### What already exists (integration points)
- `artificial-life/code/stage4_qalife.py` — genome = 2 qubits/individual (`geno_q(k)=2k`,
  `pheno_q(k)=2k+1`; circuit width `2*width + (1 if damping)`). Reused: `build_population(...)`,
  `apply_mutation(qc, geno, theta)` (Ry on genotype), `apply_self_replication`, `apply_phenotype_clone`,
  `apply_interaction`, `phenotype_z_from_counts(counts, width)`, `alive_mask`, `alive_population`,
  `xbasis_witness_from_counts(counts, qubits) -> (joint, separable)`, `entanglement_depth`,
  `classical_surrogate_z`, `_sim_thetas(width, seed, mut_scale)`, `_z_expectation`.
- `artificial-life/code/qrng_client.py` — `QRNGClient(base_url, api_key)`, `.health() -> QRNGHealth`
  (`.status == "ok"`), `.fetch(size=32, fmt="hex") -> QRNGResponse`, `QRNGUnavailable`. Block-fetch
  idiom (from `stage4_scale.qrng_thetas`): pull 32-byte hex blocks until `4*width` bytes,
  `theta_k = mut_scale*pi*(u32/2**32)` from disjoint 4-byte big-endian slices.
- `proof_of_concept/quantum_life.py` — the per-generation closed loop to mirror: rebuild the genome
  circuit each generation with an updated `mutation`, measure, apply contingent selection, log.
- `stage5_fliptest.py` — the `kill_gate` / `verify_run(path)` verdict idiom F1 will reuse (F0 only
  writes the observables the gate reads).

---

## 2. Acceptance criteria

Verbatim from epic §9 (F0). IDs added.

- **AC-F0.1** (verbatim): "Fork the encode/reproduce/mutate population from `stage4_qalife.py`
  (import, do not rewrite the genome primitives or the `⟨X^⊗W⟩` witness)."
  → **Covered by** `code/closed_loop.py:57` (`import stage4_qalife as q4`); genome via
  `q4.build_population` (`closed_loop.py:195`), witness via `q4.xbasis_witness_from_counts` (`closed_loop.py:135`).
  No genome/witness reimplementation.
- **AC-F0.2** (verbatim): "Closed loop per generation: measure outcome → predictable (deterministic)
  feedback on 'expected' outcomes, high-entropy (QRNG via `qrng_client.py`, PRNG fallback) feedback on
  surprising ones → select → reproduce → mutate."
  → **Covered by** `run_closed_loop` (`closed_loop.py:256`): per-gen measure→witness→surprise→contingent
  `mut_scale` feedback (`closed_loop.py:288`, tighten ×0.7 / explore full per Q3); mutate/reproduce inside
  `q4.build_population`. (Option A: no marginal selection — GHZ marginals frozen; feedback acts on `mut_scale`.)
- **AC-F0.3** (verbatim): "Surprise proxy = negative log-likelihood of the observed outcome under the
  population's running outcome distribution; logged per generation."
  → **Covered by** `surprise_nll` (`closed_loop.py:152`); logged as `generations[].surprise` (`_row`, `closed_loop.py:230`).
- **AC-F0.4** (verbatim): "Yoked-control runner: identical stimulation sequence, feedback scrambled /
  non-contingent; runnable alongside the closed loop from the same instance."
  → **Covered by** `run_yoked` (`closed_loop.py:298`): replays the closed arm's `stimulation` mut_scale
  multiset, seed-shuffled + decoupled (`closed_loop.py:305`); `main --arm both` runs both from one instance (`closed_loop.py:398`).
- **AC-F0.5** (verbatim): "Observable logger writes the shared `research_runs/*.json` schema
  (per-generation surprise, σ, entropy, witness, poke events, arm=closed|yoked|surrogate, backend, seed)."
  → **Covered by** `_meta`/`_row`/`write_run` (`closed_loop.py:209`/`:230`/`:339`); verified keys
  `active,entropy,gen,outcome,poke,shots,sigma,surprise,witness_joint,witness_separable,witness_sigma,witness_signal`.
- **AC-F0.6** (verbatim): "Generation count and genome width W are CLI/function parameters; generations
  default to ≈15."
  → **Covered by** argparse `--generations` default 15 (`closed_loop.py:368`), `--width` default 4 (`closed_loop.py:369`).

Each AC maps to a manual check in §8.

---

## 3. Scope

### In scope
- New dir `THESIS/CriticalQuantumLife/code/` + new file `closed_loop.py`.
- Closed-loop runner (per-generation contingent feedback), yoked-control runner, surprise/σ/entropy
  observables, `⟨X^⊗W⟩` witness readout (imported), the shared run-JSON writer.
- Sim (Aer) path only in F0 (`--sim` default true). QRNG entropy source with PRNG fallback.
- CLI: `--generations --width --shots --seed --name --arm --mut-scale --sim/--no-sim --qrng-url`.

### Out of scope (deferred to their tickets)
- The three-gate GO/no-go verdict + `verify_run` — **F1** (F0 only emits the observables it reads).
- Avalanche α power-law fit, entropy-plateau test, susceptibility peak, post-poke τ — **F2**.
- Classical measure-and-resend surrogate + null band certification — **F3** (F0 writes the raw
  witness per gen; F3 adds the surrogate arm + `certification` block).
- Interactive `poke()` API + inter-batch state persistence — **F4** (F0 accepts a `poke_gen`
  scripted-poke param for F1's use, but exposes no interactive/persistent session).
- Hardware submission — **F5**. Web — **F6**. Paper — **F7**.

---

## 4. Data model — `run.json` (the epic-wide schema; F0 defines it)

Written to `OUTPUT_DIR = ../research_runs` (i.e. `THESIS/CriticalQuantumLife/research_runs/`), name
`<name>_<arm>_<backend>_seed<seed>_<ts>_run.json`. **This is the one schema every arm (closed, yoked,
surrogate, hardware) and every consumer (F1 gate, F2 metrics, F3 cert, F6 web, F7 paper) shares.**
F0 writes `meta` + `generations[]`; later tickets ADD sibling blocks (`criticality`, `certification`,
`kill_gate`) — they never rename F0's fields.

```jsonc
{
  "meta": {
    "project": "critical-quantum-life",
    "study": "critical-quantum-life",
    "arm": "closed",                    // "closed" | "yoked" | "surrogate"
    "backend": "sim",                   // "sim" | "<ibm_backend>"
    "sim": true,
    "timestamp": "sim",                 // timestamp() ("sim" under stub, real on HW)
    "seed": 100,
    "width": 4,                         // genome width W (individuals)
    "generations": 15,
    "shots": 4096,
    "mut_scale": 0.10,
    "poke_gen": null,                   // scripted poke generation (F1 sets, e.g. 8), else null
    "entropy_source": "prng",           // "qrng" | "prng"
    "entropy_provenance": [],           // [{request_id, receipt}, ...] when QRNG used (F5)
    "calibration": null                 // null on sim; live 2q/readout err on HW (F5)
  },
  "generations": [
    {
      "gen": 0,
      "outcome": "6",                   // discretized witness bin (the OBSERVED outcome; Option A)
      "surprise": 1.732,                // AC-F0.3 neg-log-likelihood of the observed witness-bin
      "witness_joint": 0.87,            // ⟨X^⊗W⟩ joint  (from xbasis_witness_from_counts)
      "witness_separable": 0.01,        // separable product (F3 leans on this; F0 records it)
      "witness_signal": 0.86,           // joint - separable  (the ORDER PARAMETER, Option A)
      "witness_sigma": 0.016,           // sqrt(1/shots) shot-floor null band (F3 does the full band)
      "entropy": 1.81,                  // Shannon entropy of the running witness-bin distribution
      "active": true,                   // surprise above running median (avalanche substrate for F2)
      "sigma": 0.95,                    // COARSE branching of the surprise-activity process (→1 target)
      "poke": false,                    // was this generation poked
      "shots": 4096
    }
    // ... one per generation
  ]
}
```

**Option A (developer-selected) — witness-as-outcome.** The stage4 quantum genome is a GHZ genealogy
(founder `|+>` + CNOT chain), which the `⟨X^⊗W⟩` witness requires. A GHZ's single-qubit marginals are
maximally mixed, so local mutation `Ry(θ)` leaves every single-qubit observable (phenotype ⟨σz⟩,
alive-mask, alive-count) **invariant** — information lives only in the **joint witness** (verified against
the engine). So F0's outcome is the **discretized witness** (as the POC did: it keyed feedback on the
witness scalar), NOT an alive-mask. Consequences the schema encodes:
- `outcome` = witness bin; `surprise = -log P(bin)` under the running bin-distribution.
- **Order parameter** = `witness_signal` (not an alive-count).
- **Criticality** is **avalanche criticality of the surprise process** (Beggs & Plenz): `active` = a
  generation whose surprise exceeds the running median; F2 collects avalanches of `active` runs and fits
  α≈1.5; `sigma` is the branching of that activity (→1 = critical). F0 logs a coarse running `sigma`;
  F2 supersedes it. (F1/F2 plans carry the old alive-count σ wording — reconcile them to this when built;
  see §12.)

- Field names `meta.arm`, `generations[].outcome|surprise|witness_signal|entropy|active|sigma|poke` are
  the epic §4 contract — do not rename; F1–F7 consume them.
- `sigma` at gen 0 is `null` (no prior activity window).

---

## 5. Design decisions carried from the epic (do not re-litigate)

- **Three honesty gates are law.** F0 produces the *raw material* for all three: surprise (adaptation
  gate), σ/entropy (criticality gate), witness_signal (quantum gate). F0 does not itself judge them
  (that is F1/F2/F3) but every observable must be present and honestly logged.
- **Default ~15 generations, parametrized** (epic CD, supersedes POC's 30). `--generations` default 15.
- **Reuse the engine; do not rewrite.** Import `stage4_qalife` genome + witness; PRNG fallback labelled.
- **Sim-first.** F0 is the pure-sim floor; `--sim` defaults true, no hardware branch wired in F0
  (F5 adds it). The Aer method mirrors `stage4_scale` (`density_matrix`) so noise can be layered later.
- **QRNG feed via existing `qrng_client.py`,** block-fetch idiom from `stage4_scale.qrng_thetas`;
  fail-closed only on hardware (N/A in F0), PRNG (`_sim_thetas`) labelled on sim.
- **One run-JSON schema** (§4) — F0 owns it; later tickets extend, never rename.

---

## 6. File plan (concrete paths)

Python: `from __future__ import annotations`, full type hints, `print = functools.partial(print, flush=True)`
(QuantumLife idiom). No raw SQL (N/A). One new file + one new dir.

### `THESIS/CriticalQuantumLife/code/closed_loop.py` (new)

Structure, top to bottom:

1. **Module docstring** — what the closed loop is; provenance note (forks `stage4_qalife.py`, mirrors
   `proof_of_concept/quantum_life.py`); the three-gates-are-law reminder.
2. **Imports + path hooks** — `import os, sys, json, math, argparse, functools, random`; `import numpy as np`;
   `_HERE = os.path.dirname(__file__)`; `_AL = os.path.normpath(os.path.join(_HERE, "..","..","..","artificial-life","code"))`;
   `sys.path.insert(0, _AL)`; `import stage4_qalife as q4`; `from qrng_client import QRNGClient, QRNGUnavailable`;
   `import layout`. `from qiskit import transpile`; `from qiskit_aer import AerSimulator`;
   `SIM = AerSimulator(method="density_matrix")`. `OUTPUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "research_runs"))`.
   `def timestamp() -> str: return "sim"` stub (F5 swaps in `pipeline_common.timestamp`).
3. **`def _read_env_key(name: str) -> str | None`** — port verbatim from `stage4_scale.py` (scans `../.env`, `./.env`).
4. **Entropy source:**
   - `def make_client(args) -> QRNGClient | None` — return `None` on `--sim` (PRNG); else build client from
     `QEAAS_API_KEY`/`QEAAS_API_URL` (fail-closed on missing key / non-`"ok"` health). F0 is sim → returns `None`.
   - `def draw_thetas(client, width, mut_scale, repeat, provenance) -> list[float]` — QRNG block-fetch
     (`client.fetch(size=32, fmt="hex")`, `theta_k = mut_scale*pi*(u32/2**32)`, append `{request_id, receipt}`
     to `provenance`) when `client is not None`, else `q4._sim_thetas(width, 1000*repeat+width, mut_scale)`
     (labelled `[F0] sim entropy fallback`).
5. **Outcome / distribution / surprise (§7) — Option A, witness-as-outcome:**
   - `def witness_gen(counts, geno_qubits, shots) -> tuple[float,float,float]` — call
     `q4.xbasis_witness_from_counts(counts, geno_qubits)`; return `(joint, separable, sqrt(1.0/shots))`
     (shot-floor null band; F3 does the full band). X-basis: genotype qubits H-rotated before Z-readout.
   - `def outcome_key(witness_signal: float, nbins: int) -> str` — discretize `witness_signal` into `nbins`
     over `[-1, 1]` → the observed **outcome** (Option A). Deterministic.
   - `def update_running_dist(dist: dict[str,float], key: str, decay: float) -> None` — exponential running
     frequency of witness-bin outcomes (decay 0.8 per Q2), the "running outcome distribution".
   - `def surprise_nll(dist: dict[str,float], key: str) -> float` — `-log(P(key))` with Laplace smoothing
     (AC-F0.3). Higher = more surprising.
   - `def is_surprising(surprise: float, recent: list[float]) -> bool` — surprise above the running median
     of recent surprises (Q2).
6. **Observables:**
   - `def pop_entropy(dist: dict[str,float]) -> float` — Shannon entropy of the running witness-bin distribution.
   - `def running_sigma(active_window: list[bool]) -> float | None` — COARSE branching of the surprise-activity
     process: ratio of `active` counts across the two halves of a sliding window (→1 = critical). None until the
     window fills. F2 supersedes with the rigorous avalanche σ.
7. **Circuit builder:**
   - `def build_generation(width, steps, thetas, poke, death, interaction, delta, gamma) -> QuantumCircuit` — one
     generation's genealogy via `q4.build_population(width, steps, thetas, interaction, death=death,
     founder_equator=True, delta=delta, gamma=gamma, measure=False)` (founder `|+>` ⇒ the GHZ the witness needs),
     then `qc.h(geno_qubits)` (X-basis for the witness) + `qc.measure_all()`. `poke=True` adds an extra
     `ry(pi/2)` on `geno_q(0)` before the H (the POC coherence scramble → witness dips). `steps` fixed = `width`
     internally (aging gradient along the line; not a CLI knob).
8. **Runners:**
   - `def run_closed_loop(args, client, backend=None) -> dict` — the loop over `range(args.generations)`:
     build → run (`SIM.run(transpile(qc, SIM), shots)`) → `outcome_key` → `surprise_nll` → **contingent
     feedback** (predictable deterministic thetas if expected; `draw_thetas` high-entropy if surprising) →
     record the stimulation event → select (alive-mask) → next-gen thetas → log the `generations[]` row.
     Records a `stimulation[]` trace (per-gen `{expected: bool, thetas, feedback_kind}`) for the yoked arm.
     Applies the scripted poke at `args.poke_gen` when set. Returns the `run.json` dict (`meta.arm="closed"`).
   - `def run_yoked(args, stimulation, client) -> dict` — replays the **same stimulation sequence** recorded
     by `run_closed_loop`, but the feedback is **decoupled from the measured outcome** (shuffled /
     non-contingent per §7). Same observables logged; `meta.arm="yoked"`. Runnable from the same instance
     (AC-F0.4): `run_both(args)` calls closed then yoked with the shared sequence.
9. **`def write_run(run: dict, args) -> str`** — `os.makedirs(OUTPUT_DIR, exist_ok=True)`; dump
   `<name>_<arm>_<backend>_seed<seed>_<ts>_run.json`, `json.dump(run, f, indent=2, default=str)`.
10. **`def main() -> None`** — argparse (§ below); dispatch on `--arm` (`closed` | `yoked` | `both`); print the
    per-gen table (`gen surprise σ entropy witness_signal alive`); write run(s); print path(s).
11. **`if __name__ == "__main__": main()`**.

**CLI (AC-F0.6):** `--generations`(15) `--width`(4) `--shots`(4096) `--seed`(100) `--name`("cql_f0")
`--arm`{closed,yoked,both}(both) `--mut-scale`(0.10) `--poke-gen`(int|None, default None) `--death`{unitary,damping}(damping)
`--interaction`{none,nn}(nn) `--nbins`(10) `--sim/--no-sim`(BooleanOptionalAction, default True) `--qrng-url`(default `QEAAS_URL_DEFAULT`).
(`--death` default **damping**, not unitary: under Option A the outcome is the witness, which mutation
degrades regardless of the death channel; damping keeps the phenotype entangled for the most faithful GHZ.)

No other files. `research_runs/` created on first run by `os.makedirs`.

---

## 7. The closed-loop contract (the mechanics F0 must fix)

Load-bearing definitions (Option A — witness-as-outcome; developer-selected after the GHZ-marginal finding, §12).

- **Outcome (per generation).** The **discretized witness** — `witness_signal = joint - separable` from
  `q4.xbasis_witness_from_counts` over the genotype qubits, binned into `nbins` over `[-1,1]` → a key like
  `"6"`. This is what the POC keyed feedback on; it is the ONLY genome observable mutation moves under the GHZ.
- **Running outcome distribution.** Exponentially-decayed frequency table over witness-bin keys
  (`update_running_dist`, decay 0.8, Q2). Laplace-smoothed so unseen bins have nonzero prob.
- **Surprise proxy (AC-F0.3).** `surprise = -log P(observed_bin)` under that running distribution. Expected to
  **fall** across generations under closed loop (the loop tightens mutation → the GHZ stabilizes → the witness
  bin becomes predictable), **not** under yoked.
- **Expected vs surprising.** Q2: this generation is "surprising" if its `surprise` exceeds the running
  **median** surprise; else "expected".
- **Contingent feedback (AC-F0.2, Q3).** Expected → **predictable** feedback: tighten, `mut_scale *= 0.7`
  (floored) → smaller next-gen mutation → cleaner GHZ. Surprising → **high-entropy** feedback: reset
  `mut_scale` to full (`args.mut_scale`) and draw fresh thetas from `draw_thetas` (QRNG on HW, labelled PRNG on
  sim). DishBrain contingency: predictable feedback when you predicted, noise when you were surprised.
- **Mutate / reproduce.** Each generation draws `thetas = draw_thetas(width, mut_scale, repeat=gen)`, builds the
  genealogy (`apply_self_replication` chain + `apply_mutation` Ry per genotype, all inside `q4.build_population`).
  There is no marginal "selection" step (GHZ marginals are frozen — §12); selection acts through the feedback on
  `mut_scale`, which is what actually reorganizes the population's witness distribution.
- **Criticality substrate (Option A).** `active` = a generation whose surprise exceeds the running median;
  runs of `active` generations are the avalanches F2 fits to α≈1.5, and their branching is the `sigma`→1 signal.
  F0 logs `active` + a coarse running `sigma`; F1 reads the σ trend, F2 does the rigorous avalanche fit.
- **Scripted poke (F1 only).** When `--poke-gen g` is set, at generation `g` invert the expected/surprising
  split AND add an extra `ry(pi/2)` on `geno_q(0)` (the POC coherence scramble → witness dips → surprise spikes).
  The **interactive** poke is F4; F0 exposes only the scripted hook for F1's gate.
- **Yoked control (AC-F0.4, Q5).** The closed loop records its `stimulation[]` sequence (the ordered
  `mut_scale`/feedback-kind events it actually applied). The yoked arm replays **the same multiset** of those
  events in a **seed-shuffled order, decoupled from its own outcomes** — same stimulation energy, zero
  contingency → its surprise should NOT fall. That gap is the adaptation gate.

---

## 8. Manual verification (no automated tests)

Run from `THESIS/CriticalQuantumLife/code/`:

```bash
cd THESIS/CriticalQuantumLife/code
python closed_loop.py --arm both --generations 15 --width 4 --seed 100 --name cql_f0
```

- **AC-F0.1** — grep the source: genome/witness come from `import stage4_qalife as q4`; no local reimplementation
  of `xbasis_witness_from_counts` / `build_population` / `apply_mutation`.
- **AC-F0.2** — the per-gen stdout table shows the `feedback_kind` column alternating `predictable`/`high-entropy`
  tracking the expected/surprising split; run.json `stimulation[]` (or the closed arm's gen rows) confirm contingency.
- **AC-F0.3** — `generations[].surprise` present every gen; closed-arm surprise trends downward (eyeball; the
  formal gate is F1). `python -c "import json;d=json.load(open('<closed path>'));print([round(g['surprise'],2) for g in d['generations']])"`.
- **AC-F0.4** — two files written (`_closed_` and `_yoked_`); yoked surprise does NOT trend down the way closed does.
- **AC-F0.5** — schema check: `python -c "import json;d=json.load(open('<path>'));m=d['meta'];print(m['arm'],m['backend'],m['seed'],len(d['generations']),sorted(d['generations'][0]))"`
  → prints `closed sim 100 15` and keys `alive_population, entropy, gen, poke, shots, sigma, surprise, witness_joint, witness_separable, witness_signal, witness_sigma`.
- **AC-F0.6** — `--generations 8 --width 6` produces 8 gens over W=6; defaults (no flags) give 15 gens / W=4.
- **Determinism** — same `--seed` reproduces the same trait/surprise curve within shot noise.

---

## 9. Out-of-context risks / notes

- `timestamp()` stub returns `"sim"`, so repeat runs at the same `--seed`/`--name`/`--arm` overwrite the same
  file. Acceptable for F0; vary `--name`/`--seed` to keep multiple runs. F5 swaps in the real `pipeline_common.timestamp`.
- The genotype-qubit indices passed to `xbasis_witness_from_counts` are indices into the **measured classical
  register**, not physical qubits — mirror `stage4_scale.build_measured`'s classical-bit ordering exactly or the
  witness silently reads the wrong bits.
- Circuit width = `2*W (+1 if death=="damping")`; W=4 → 8–9 qubits, trivial for `density_matrix` Aer. Scaling W
  is F5's concern, not F0's.
- The running-distribution decay and the expected/surprising threshold (Q2) are the two knobs that decide whether
  the closed–yoked gap appears at all; F1 is the gate that proves the defaults work at toy scale — if F1 shows no
  gap, revisit these before spending hardware.

---

## 10. Ground rules honored

- Every AC (F0.1–F0.6) quoted verbatim from epic §9 and mapped to a §8 manual check.
- Every file path in §6 concrete; one new file + one new dir.
- Epic cross-cutting decisions adopted without re-arguing (reuse engine, 15-gen default, one schema, sim-first, QRNG feed).
- No tests, no test files, no test-impact section (project directive).
- Strict typing + `from __future__ import annotations`; no raw SQL.

---

## 11. Open questions

- **Q1 — Outcome definition. RESOLVED (developer) → SUPERSEDED by Option A (developer, §12).** Original pick was
  the alive-mask bitstring, but the alive-mask (and every single-qubit observable) is **frozen** under the GHZ
  founder the witness requires (verified against the engine, §12). Outcome is now the **discretized witness**
  (`witness_signal` binned into `nbins`); `surprise = -log P(bin)`. The POC keyed feedback on the witness exactly
  this way. σ/criticality move to the surprise-avalanche process (§4, §7). Reused by F1/F2 (which must reconcile
  their alive-count σ wording — §12).
- **Q2 — Expected/surprising split + running-distribution memory. RESOLVED (developer):** "surprising" = surprise
  **above the running median**; running outcome distribution = exponential decay **0.8**, Laplace-smoothed.
- **Q3 — Predictable-vs-high-entropy feedback magnitudes. RESOLVED (developer):** predictable (expected outcome)
  = `mut_scale *= 0.7` (POC tightening); high-entropy (surprising outcome) = fresh `draw_thetas` at full
  `mut_scale`. Two hardcoded constants, matches the working POC.
- **Q4 — Aer method. RESOLVED (developer):** `AerSimulator(method="density_matrix")` (matches `stage4_scale`;
  lets F5 layer a `noise_model` on the same code path).
- **Q5 — Yoked scramble. RESOLVED (developer):** yoked **replays the same feedback multiset** the closed arm
  applied, **seed-shuffled and decoupled from outcomes** (same stimulation energy, zero contingency).

---

## 12. Post-implementation

**Built:** one new file `code/closed_loop.py` + dir `research_runs/` (created on first run). Sim-only
(`AerSimulator(method="density_matrix")`; no backend / no `pipeline_common`). Imports the stage4 genome +
`⟨X^⊗W⟩` witness (no reimplementation). `--arm both` runs the closed loop then the yoked control from one
instance and prints the early-late surprise drop for each. All six F0 ACs verified (see §2 file:line evidence);
run-JSON schema written with the §4 keys.

**Physics decisions frozen during implementation (load-bearing — downstream must honor):**
- **Option A — witness-as-outcome (developer-selected mid-implement).** The genome is a GHZ genealogy; its
  single-qubit marginals are maximally mixed, so mutation `Ry(θ)` leaves phenotype ⟨σz⟩ / alive-mask / σ
  **invariant** — verified against the engine (alive-mask identical across `mut_scale` 0→1.5 under
  `founder_equator=True`). Information lives only in the **joint witness**, so the outcome is the discretized
  witness (as the POC did). This superseded approved Q1 (alive-mask). See §4/§7.
- **`--death` default = `unitary`, NOT the plan's original `damping`.** Under `damping`, `apply_phenotype_clone`
  (CX geno→pheno) entangles each genotype with its phenotype; measuring/damping the phenotype **decoheres the
  genotype X-parity → witness ≈ 0** (measured: `+0.001` at every `mut_scale`). Under `unitary` the phenotype is
  prepared separately, the genotype stays a clean GHZ, and the witness responds to mutation cleanly (measured:
  `+1.000` at θ=0 → `+0.889` at 0.2 → `+0.431` at 0.5 → `-0.193` at 1.0). `unitary` is required for Option A.
- **`steps = width`** internally in `build_generation` (aging gradient along the line; not a CLI knob).
- **`DEFAULT_MUT = 0.60`** (explore/"full" mutation scale) — tuned so the witness spans a usable range across
  bins; the plan's original `0.10` leaves the witness pinned near 1 (no dynamics). `nbins=10` over `[-1,1]`.

**Follow-ups the developer must know (honest flags):**
- **The single-seed adaptation gap is weak and sign-inconsistent** (measured across seeds 1/42/100/7/2024:
  gap = −0.05, +0.18, −0.44, +0.40, −0.17). **Root cause:** the approved **Q2 median-split** structurally pins
  ~50% of generations as "surprising" (the loop cannot drive every gen below its own running median), so it never
  cleanly converges — muddying both the adaptation gap and the poke dip. **This is F1's to resolve** (F1 owns the
  adaptation gate + `ADAPT_MIN` + signal windows): options are seed-averaging, or a non-median "surprising"
  threshold anchored to a decaying high-water mark / absolute floor the loop *can* beat (would revisit Q2), or
  accept an honest NO-GO. F0 is faithful to the locked Q2; it does not override it. **F1 must address this before
  hardware.**
- **F1/F2 σ wording.** Those plans still describe branching σ as `alive(g)/alive(g-1)` (an alive-count process),
  which is frozen under Option A. When F1/F2 are implemented, reconcile σ/avalanches to the **surprise-activity**
  process F0 logs (`generations[].active` + coarse `generations[].sigma`; F2 fits avalanche α on `active` runs).
  Not edited here (implement-feature edits only the F0 plan).
- **Engine hooks still owed to F3/F4** (unchanged from the plan): F3 wants a `surrogate=True` branch in
  `run_closed_loop`; F4 wants `run_closed_loop(..., resume_state=None)` + `meta.poke_events` list. F0 currently
  exposes a single scripted `--poke-gen` and a `stimulation` sibling in the closed run-JSON (which F4 can consume).
- `timestamp()` stub returns `"sim"` → repeat runs at the same `--name`/`--seed`/`--arm` overwrite. Vary `--name`.
