# F5 Hardware Study — Run Log

**Driver:** `THESIS/CriticalQuantumLife/code/run_research.py` (calls `hardware_batches.py` + `submit_batch.py`)
**Backend:** `ibm_kingston` · **Session:** `sess_caec0e51` (seed 100 + name `cql_f5`, deterministic)
**Config:** W=6, mut_scale=0.30, 2 batches × 8 generations, poke `inject_stimulus` at the boundary.

Run from:
```bash
cd /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/code
```

Before a fresh study, clear half-finished artifacts so the report never double-counts:
```bash
rm -f ../research_runs/cql_f5_*_run.json ../research_runs/sess_caec0e51_*state.json ../research_runs/cql_f5_report.json
```

---

## What both runs do

Both commands are the **same study** — Run 2 just spells out the defaults Run 1 uses implicitly. Either one
executes all F5 steps end to end, unattended:

```
for batch b in 0, 1:
    emit b      both arms (closed + yoked): 8 QPY circuits + a submit bundle each, with the
                fail-closed calibration gate (2q err ≤ 0.05, readout err ≤ 0.15)      [hardware_batches emit]
    submit b    run each QPY on ibm_kingston (8192 shots) -> per-gen counts JSON       [submit_batch]
    ingest b    counts -> observables run-JSON (witness, surprise, sigma, entropy)
                + persisted inherited state for the next batch                          [hardware_batches ingest]
    if b == 0:  poke inject_stimulus (scrambles the founder on batch 1's first circuit) [hardware_batches poke]
report          adaptation gap + criticality (F2) + tau + witness certification (F3)    [hardware_batches report]
```

- **16 generations total** (2 batches × 8), one continuous population threaded by `session_id`.
- **Two arms every batch:** `closed` (real contingent feedback) and `yoked` (scrambled feedback control).
  The gap between them is the proof of adaptation.
- **The poke** happens once, between batch 0 and batch 1 — a surprise spike you should see relax over batch 1.
- Produces `research_runs/cql_f5_report.json` at the end.

### Read the report
- `adaptation_gap.gap` **> 0** → learning (closed beats yoked). *AC-F5.3*
- `certification.certification.certified` **true** (`frac_above_band ≥ 0.8`) → witness above the classical
  surrogate null (null derived from the hardware closed-arm shots). *AC-F5.4*
- `criticality.sigma.mean` **→ 1** → edge of chaos. `alpha` is *indicative* (16 gens < F2's 30-gen floor).
- `relaxation_tau.tau` at `poke_gen=8` → poke-and-recover time constant.

> Honest-negative caveat: hardware readout + 2q error pulls the witness down. If `certified` comes back
> `false` on real hardware, that is the width/noise budget at which it dies — report it, do not inflate W.

---

## RUN 1 — defaults

```bash
python run_research.py --backend ibm_kingston
```

Identical to Run 2 (defaults: `--width 6 --mut-scale 0.30 --batches 2 --generations 8 --shots 8192 --poke inject_stimulus`).

**Output:**

```
<PASTE RUN 1 TERMINAL OUTPUT HERE>



(base) peter@home:~/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/code$ python run_research.py --backend ibm_kingston
=== F5 study sess_caec0e51: backend=ibm_kingston W=6 mut_scale=0.3 batches=2x8gens poke=inject_stimulus ===

>>> [emit b0] /home/peter/anaconda3/bin/python hardware_batches.py emit --backend ibm_kingston --batch 0 --arm both --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[emit] arm=closed batch=0 backend=ibm_kingston: 8 QPY circuits + bundle written
       chain=[26, 25, 37, 45, 46, 47, 48, 49, 38, 29, 30, 31]  cal(twoq_max=0.0058 readout_max=0.0192 gated=True)
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_closed_ibm_kingston_submit.json
  MANUAL: submit each QPY on QC by hand, save per-gen counts JSON, then:
    python hardware_batches.py ingest --bundle cql_f5_batch0_closed_ibm_kingston_submit.json --counts <gen0.json> <gen1.json> ...
[emit] arm=yoked batch=0 backend=ibm_kingston: 8 QPY circuits + bundle written
       chain=[26, 25, 37, 45, 46, 47, 48, 49, 38, 29, 30, 31]  cal(twoq_max=0.0058 readout_max=0.0192 gated=True)
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_yoked_ibm_kingston_submit.json
  MANUAL: submit each QPY on QC by hand, save per-gen counts JSON, then:
    python hardware_batches.py ingest --bundle cql_f5_batch0_yoked_ibm_kingston_submit.json --counts <gen0.json> <gen1.json> ...

>>> [submit b0 closed] /home/peter/anaconda3/bin/python submit_batch.py --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_closed_ibm_kingston_submit.json --shots 8192 --out-prefix /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen
=== submit closed batch 0 on ibm_kingston: 8 circuits x 8192 shots ===
  gen 0: submitting cql_f5_batch0_closed_gen0.qpy ...
    job daaq2ghl216s739ojkh0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen0.json  (723 distinct bitstrings)
  gen 1: submitting cql_f5_batch0_closed_gen1.qpy ...
    job daaq3kb4clkc73fi0p3g -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen1.json  (735 distinct bitstrings)
  gen 2: submitting cql_f5_batch0_closed_gen2.qpy ...
    job daaq3mjvpcac73dcrl70 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen2.json  (737 distinct bitstrings)
  gen 3: submitting cql_f5_batch0_closed_gen3.qpy ...
    job daaq3oj4clkc73fi0pcg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen3.json  (735 distinct bitstrings)
  gen 4: submitting cql_f5_batch0_closed_gen4.qpy ...
    job daaq3qurrl7c7385tmhg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen4.json  (710 distinct bitstrings)
  gen 5: submitting cql_f5_batch0_closed_gen5.qpy ...
    job daaq3t3vpcac73dcrlfg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen5.json  (710 distinct bitstrings)
  gen 6: submitting cql_f5_batch0_closed_gen6.qpy ...
    job daaq3v3vpcac73dcrli0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen6.json  (683 distinct bitstrings)
  gen 7: submitting cql_f5_batch0_closed_gen7.qpy ...
    job daaq4134clkc73fi0pq0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen7.json  (727 distinct bitstrings)

  DONE. Ingest with:
    python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_closed_ibm_kingston_submit.json \
      --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen7.json \
      --width 6 --shots 8192 --name cql_f5

>>> [ingest b0 closed] /home/peter/anaconda3/bin/python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_closed_ibm_kingston_submit.json --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_closed_gen7.json --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[ingest] arm=closed batch=0: 8 gens -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_closed_ibm_kingston_b0_20260831-174725_run.json
  -> state /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_closed_state.json

>>> [submit b0 yoked] /home/peter/anaconda3/bin/python submit_batch.py --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_yoked_ibm_kingston_submit.json --shots 8192 --out-prefix /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen
=== submit yoked batch 0 on ibm_kingston: 8 circuits x 8192 shots ===
  gen 0: submitting cql_f5_batch0_yoked_gen0.qpy ...
    job daaq44pl216s739ojmu0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen0.json  (694 distinct bitstrings)
  gen 1: submitting cql_f5_batch0_yoked_gen1.qpy ...
    job daaq471l216s739ojn10 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen1.json  (702 distinct bitstrings)
  gen 2: submitting cql_f5_batch0_yoked_gen2.qpy ...
    job daaq49bvpcac73dcrlv0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen2.json  (686 distinct bitstrings)
  gen 3: submitting cql_f5_batch0_yoked_gen3.qpy ...
    job daaq4bhl216s739ojn70 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen3.json  (710 distinct bitstrings)
  gen 4: submitting cql_f5_batch0_yoked_gen4.qpy ...
    job daaq4dj4clkc73fi0q7g -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen4.json  (735 distinct bitstrings)
  gen 5: submitting cql_f5_batch0_yoked_gen5.qpy ...
    job daaq4g1l216s739ojnd0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen5.json  (735 distinct bitstrings)
  gen 6: submitting cql_f5_batch0_yoked_gen6.qpy ...
    job daaq4i9l216s739ojngg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen6.json  (754 distinct bitstrings)
  gen 7: submitting cql_f5_batch0_yoked_gen7.qpy ...
    job daaq4khl216s739ojnk0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen7.json  (721 distinct bitstrings)

  DONE. Ingest with:
    python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_yoked_ibm_kingston_submit.json \
      --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen7.json \
      --width 6 --shots 8192 --name cql_f5

>>> [ingest b0 yoked] /home/peter/anaconda3/bin/python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch0_yoked_ibm_kingston_submit.json --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b0_yoked_gen7.json --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[ingest] arm=yoked batch=0: 8 gens -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_yoked_ibm_kingston_b0_20260831-174843_run.json
  -> state /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_yoked_state.json

>>> [poke after b0] /home/peter/anaconda3/bin/python hardware_batches.py poke --session sess_caec0e51 --poke inject_stimulus --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[poke] queued inject_stimulus onto 2 arm state(s) for sess_caec0e51
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_closed_state.json
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_yoked_state.json

>>> [emit b1] /home/peter/anaconda3/bin/python hardware_batches.py emit --backend ibm_kingston --batch 1 --arm both --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[emit] arm=closed batch=1 backend=ibm_kingston: 8 QPY circuits + bundle written
       chain=[26, 25, 37, 45, 46, 47, 48, 49, 38, 29, 30, 31]  cal(twoq_max=0.0058 readout_max=0.0192 gated=True)
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_closed_ibm_kingston_submit.json
  MANUAL: submit each QPY on QC by hand, save per-gen counts JSON, then:
    python hardware_batches.py ingest --bundle cql_f5_batch1_closed_ibm_kingston_submit.json --counts <gen0.json> <gen1.json> ...
[emit] arm=yoked batch=1 backend=ibm_kingston: 8 QPY circuits + bundle written
       chain=[26, 25, 37, 45, 46, 47, 48, 49, 38, 29, 30, 31]  cal(twoq_max=0.0058 readout_max=0.0192 gated=True)
  -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_yoked_ibm_kingston_submit.json
  MANUAL: submit each QPY on QC by hand, save per-gen counts JSON, then:
    python hardware_batches.py ingest --bundle cql_f5_batch1_yoked_ibm_kingston_submit.json --counts <gen0.json> <gen1.json> ...

>>> [submit b1 closed] /home/peter/anaconda3/bin/python submit_batch.py --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_closed_ibm_kingston_submit.json --shots 8192 --out-prefix /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen
=== submit closed batch 1 on ibm_kingston: 8 circuits x 8192 shots ===
  gen 8: submitting cql_f5_batch1_closed_gen8.qpy ...
    job daaq5cjvpcac73dcrnl0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen0.json  (700 distinct bitstrings)
  gen 9: submitting cql_f5_batch1_closed_gen9.qpy ...
    job daaq5f3vpcac73dcrno0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen1.json  (704 distinct bitstrings)
  gen 10: submitting cql_f5_batch1_closed_gen10.qpy ...
    job daaq5h1l216s739ojp20 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen2.json  (711 distinct bitstrings)
  gen 11: submitting cql_f5_batch1_closed_gen11.qpy ...
    job daaq5j1l216s739ojp50 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen3.json  (692 distinct bitstrings)
  gen 12: submitting cql_f5_batch1_closed_gen12.qpy ...
    job daaq5lbvpcac73dcrnv0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen4.json  (728 distinct bitstrings)
  gen 13: submitting cql_f5_batch1_closed_gen13.qpy ...
    job daaq5njvpcac73dcro20 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen5.json  (711 distinct bitstrings)
  gen 14: submitting cql_f5_batch1_closed_gen14.qpy ...
    job daaq5purrl7c7385tpeg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen6.json  (734 distinct bitstrings)
  gen 15: submitting cql_f5_batch1_closed_gen15.qpy ...
    job daaq5rpl216s739ojpgg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen7.json  (723 distinct bitstrings)

  DONE. Ingest with:
    python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_closed_ibm_kingston_submit.json \
      --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen7.json \
      --width 6 --shots 8192 --name cql_f5

>>> [ingest b1 closed] /home/peter/anaconda3/bin/python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_closed_ibm_kingston_submit.json --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_closed_gen7.json --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[ingest] arm=closed batch=1: 8 gens -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_closed_ibm_kingston_b1_20260831-175120_run.json
  -> state /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_closed_state.json

>>> [submit b1 yoked] /home/peter/anaconda3/bin/python submit_batch.py --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_yoked_ibm_kingston_submit.json --shots 8192 --out-prefix /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen
=== submit yoked batch 1 on ibm_kingston: 8 circuits x 8192 shots ===
  gen 8: submitting cql_f5_batch1_yoked_gen8.qpy ...
    job daaq5vmrrl7c7385tpl0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen0.json  (713 distinct bitstrings)
  gen 9: submitting cql_f5_batch1_yoked_gen9.qpy ...
    job daaq61urrl7c7385tpng -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen1.json  (705 distinct bitstrings)
  gen 10: submitting cql_f5_batch1_yoked_gen10.qpy ...
    job daaq646rrl7c7385tprg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen2.json  (710 distinct bitstrings)
  gen 11: submitting cql_f5_batch1_yoked_gen11.qpy ...
    job daaq67mrrl7c7385tq4g -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen3.json  (725 distinct bitstrings)
  gen 12: submitting cql_f5_batch1_yoked_gen12.qpy ...
    job daaq69pl216s739ojq40 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen4.json  (719 distinct bitstrings)
  gen 13: submitting cql_f5_batch1_yoked_gen13.qpy ...
    job daaq6c34clkc73fi0t60 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen5.json  (710 distinct bitstrings)
  gen 14: submitting cql_f5_batch1_yoked_gen14.qpy ...
    job daaq6e9l216s739ojqa0 -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen6.json  (718 distinct bitstrings)
  gen 15: submitting cql_f5_batch1_yoked_gen15.qpy ...
    job daaq6ghl216s739ojqcg -> waiting
    -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen7.json  (731 distinct bitstrings)

  DONE. Ingest with:
    python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_yoked_ibm_kingston_submit.json \
      --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen7.json \
      --width 6 --shots 8192 --name cql_f5

>>> [ingest b1 yoked] /home/peter/anaconda3/bin/python hardware_batches.py ingest --bundle /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_batch1_yoked_ibm_kingston_submit.json --counts /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen0.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen1.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen2.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen3.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen4.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen5.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen6.json /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/b1_yoked_gen7.json --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[ingest] arm=yoked batch=1: 8 gens -> /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_yoked_ibm_kingston_b1_20260831-175257_run.json
  -> state /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/sess_caec0e51_yoked_state.json

>>> [report] /home/peter/anaconda3/bin/python hardware_batches.py report --session sess_caec0e51 --width 6 --mut-scale 0.3 --shots 8192 --seed 100 --name cql_f5
[report] session sess_caec0e51: backend=ibm_kingston width=6  closed_batches=2 yoked_batches=2
  -> report /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_report.json

=== DONE. Report: /home/peter/PycharmProjects/Quantum-research/THESIS/CriticalQuantumLife/research_runs/cql_f5_report.json ===
  Read: adaptation_gap.gap (>0 = learning), certification.certified (witness above null),
        criticality.sigma.mean (->1), relaxation_tau.tau (poke recovery).
```

**Report numbers (`cql_f5_report.json`) — ibm_kingston, W=6, 16 gens, poke_gen=8:**

| field | value | pass? |
|---|---|---|
| `adaptation_gap.gap` | **+0.161** (closed_drop 0.375, yoked_drop 0.214) | ✅ > 0 (weak) |
| `certification…certified` | **true** | ✅ |
| `certification…frac_above_band` | **0.938** (15/16 above null; margin_mean +0.338, min −0.034) | ✅ ≥ 0.8 |
| `criticality.sigma.mean` | **0.438** (ci95 [0.19, 0.75]) | ❌ subcritical, not → 1 |
| `criticality.avalanche_alpha` | `None` (too few avalanches to fit) | ❌ |
| `relaxation_tau.tau` | 34740 (r²=0.54) — degenerate, no clean decay | ❌ inconclusive |

## RUN 1 — EVALUATION (final; no QC budget remaining)

**Verdict: PARTIAL — certified-quantum + adaptive, NOT critical.** Two of the three honesty gates pass.

- **Quantum gate ✅ (strong, the headline).** The `⟨X^⊗W⟩` genealogical witness certified **above** the classical
  measure-and-resend surrogate null on **real hardware** — 15/16 generations above the ±0.033 band, mean margin
  **+0.338**. The single dip is gen 8 (the poke). The entanglement genealogy survived NISQ readout+2q error at
  W=6. This is the novel, hardest claim and it held on ibm_kingston.
- **Adaptation gate ✅ (weak).** Closed surprise fell more than yoked (gap +0.161), so contingent feedback did
  more than scrambled feedback — but yoked also fell (0.214), so the contrast is modest, not clean.
- **Criticality gate ❌.** σ≈0.44 is **subcritical** (ordered/tending-frozen), not the edge of chaos (σ→1). α could
  not be fit (too few avalanches at 16 gens); the τ fit is degenerate (r²=0.54). The population did **not**
  self-organize to criticality this run.

**Why criticality missed:** mut_scale=0.30 was tuned for GO on *noiseless sim* (σ≈0.955 there). On hardware,
readout+2q noise plus the short 16-generation budget pushed the avalanche branching subcritical (σ 0.44), and 16
gens is below F2's α floor so the power-law never had the statistics. The sim→hardware transfer held on the
**quantum** axis but not the **criticality** axis.

**Thesis framing (F7, AC-F7.4 honest-negative):** the certified-quantum aliveness is demonstrated on hardware;
criticality is an honest negative at this width/noise/length budget — it needs more generations and/or a hotter
mut_scale, which this QC allocation did not cover. Do not inflate. The quantum certification is the real,
defensible hardware result.

Notes:
```
16/16 jobs on ibm_kingston completed (8 closed + 8 yoked, batch 0) + batch 1; calibration at emit:
twoq_max=0.0058, readout_max=0.0192, gated=True, chain=[26,25,37,45,46,47,48,49,38,29,30,31].
Run completed end-to-end unattended (no aborted steps). Budget exhausted — Run 2 not executed.
```

---

## RUN 2 — explicit knobs (same study, re-run or a second seed)

```bash
python run_research.py --backend ibm_kingston --width 6 --mut-scale 0.30 --batches 2 --generations 8 --shots 8192 --poke inject_stimulus
```

To make it a genuinely independent second run (not overwrite Run 1), change the identity, e.g.
`--seed 200` or `--name cql_f5b` (a new `session_id`, its own report). Otherwise it re-runs the same session.

**Output:**

```
<PASTE RUN 2 TERMINAL OUTPUT HERE>




```

**Report numbers:**

| field | value | pass? |
|---|---|---|
| `adaptation_gap.gap` | | > 0 ? |
| `certification…certified` | | true ? |
| `certification…frac_above_band` | | ≥ 0.8 ? |
| `criticality.sigma.mean` | | → 1 ? |
| `relaxation_tau.tau` | | finite ? |

Notes:
```
<observations>


```

---

## Recovery / gotchas

- **Study died mid-way** (queue timeout): re-run the same command with `--start-batch 1` to skip batch 0
  (already ingested — its run-JSONs are on disk).
- **Ingest each batch/arm once.** A second ingest of the same batch = duplicate "batch 0" = doubled report.
  Delete the offending `*_run.json` and redo.
- **Session id is stable** (seed + name). Reusing it continues the same population; change `--seed`/`--name`
  for a fresh one.
- The report scopes to the newest closed run's `(backend, width)`, so stale sim / other-width runs never
  merge into the figure.
