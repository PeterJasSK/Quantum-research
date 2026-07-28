# ECMP salt-collision DoS testbed

> **All results in this study are flow-level-simulation-derived.** This is a
> **preliminary flow-level study**: a deterministic, root-free simulator
> (`testbed/sim/`) drives the *real, frozen* mechanism — the SHA-256 hash core,
> the collision crafter, the seed-space brute-forcer, the three salt sources
> (including the live QRNG endpoint), the defence policy, and the metrics
> collector — and models **only** the packet transport (offered load → per-link
> byte counters over time). The direct next step is a **bare-metal
> implementation** of the same stack (see `plans/plan-10-*.md`). The Mininet /
> Open vSwitch / os-ken / scapy / iperf3 live path was removed (plan-10): it was
> environment-fragile and never completed a run; nothing in the results depends
> on it.

## Prereqs

Root-free, cross-platform. Only:

- Python 3.10+ with `pandas` + `matplotlib` (for `testbed/analysis/` graph
  rendering): `python3 -m venv .venv && .venv/bin/pip install -r ../requirements.txt`
- `QEAAS_API_KEY` in the environment for the `qrng` cells (Exp 4c, Exp 4d qrng,
  the qrng Graph 1 column) — see *QRNG source setup* below. Without it, those
  cells are recorded **skipped-with-reason**, never faked.
- `node` on `PATH` **only** to run the JS↔Python hash-parity checker (not the
  sim itself).

No Mininet, no Open vSwitch, no os-ken, no scapy, no root, no iperf3.

## Run the flow-level simulation (plan-10)

`testbed/sim/run_sim.py` is the entry point — the root-free replacement for the
deleted Mininet `run_experiments.py`:

```
python3 testbed/sim/run_sim.py --exp 1        # one experiment
python3 testbed/sim/run_sim.py --exp all      # full matrix + graphs + replay subset
python3 testbed/sim/run_sim.py --exp 5 --no-graphs --no-replay
```

`--exp {1,2,3,4,5,all}` selects the same cells from `testbed/experiments/matrix.py`
(the whole matrix is data, inspectable there without running it). Each cell
prints `PASS`/`FAIL`/`DATA`/`SKIP` against its expected summary result; then
(unless `--no-graphs`) the produced CSVs are handed to the unchanged
`testbed/analysis/graphs.py`, rendering `results/graph1_*.{png,svg}` and
`results/graph2_*.{png,svg}`; and (unless `--no-replay`) the P6 Tier-B replay
subset is written to `web/public/replay/*.json`.

Per-cell CSVs land under `results/<exp>/<cell_id>.csv` (+ `.summary.csv`
sidecar, + `.record.json` run-record, + `.rotation_events.jsonl` salt log) so no
cell overwrites another. Raw per-cell CSVs are gitignored (OQ-5); only the two
figures and the Q4 replay subset (three-scene runs + one QRNG provenance run +
the full Exp 5 sweep, **blind skipped**) are committed. Runs are deterministic
and reproducible bit-for-bit for a fixed `PRNG_SEED` (the only intentional
non-determinism is the live QRNG draw and the wall-clock reconstruction timing
of the Exp 5 partial attacker).

### What the sim models (plan-10 §1–§4)

- **Offered flows** come from the real `CollisionCrafter.craft` (precision,
  crafted per source), a single high-rate source (volumetric), or the real
  `random_five_tuples` (blind).
- **Defences** are the real `DefencePolicy`: a source over
  `THROTTLE_MAX_CONNECTIONS` in the window is dropped; a source over
  `RATE_LIMIT_KBPS` is metered. Frozen P4 thresholds, never re-tuned.
- **Placement** is the real `ecmp_link`: when the attacker holds the active
  salt its set concentrates on the target link, otherwise it disperses.
- **Victim throughput** is the fair share of residual target-link capacity
  after the attacker's surviving load (replaces the deleted iperf3 reader).
- **Utilisation / Jain / saturation / summary** are the real `MetricsCollector`,
  fed the exact `(port_no, tx_bytes, tx_packets, t)` sample shape it accepts.

The attack's stated operating point (auditable arithmetic, not hidden
assumptions) lives in `testbed/config.py`'s P10 block: `PACKET_SIZE_BYTES`,
`PRECISION_PER_FLOW_PPS`, `PRECISION_FLOWS_PER_SOURCE`, and the weak-PRNG
reconstruction anchor (`SIM_RECON_SEED_SPACE_BITS`, `SIM_RECON_TARGET_SEED`).

## Offline correctness gates (no root, no network)

The correctness of this study rests on these gates plus the manual verification
in `plans/plan-10-*.md`, not on any live data plane:

```
python3 testbed/spike/salt_remap_check.py       # salt provably enters the hash (P1)
python3 testbed/attacker/collision_check.py      # crafted sets collide; blind spreads; seed recovered (P3)
python3 testbed/metrics/metrics_check.py          # util/Jain/saturation/polarization maths (P4/P8)
python3 testbed/analysis/analysis_check.py        # success predicate, rotation threshold, graph render (P5)
python3 testbed/topology/polarization_check.py    # fat-tree hash-polarization mechanism (P8, offline)
```

Each exits `0` on success, non-zero (with a diagnostic) on any mismatch.

## Salt engine — sources, rotation, parity (Plan 2)

### Salt sources

`salt_source(kind)` yields one of `prng` | `csprng` | `qrng`:

- `prng` — weak, reconstructable: `random.Random(PRNG_SEED)` (default seed `0`),
  sequential draws. Deliberately the attacker's brute-force target — never a
  real defence.
- `csprng` — `secrets.token_bytes`.
- `qrng` — the hosted Q-EaaS service (below).

```
python3 -c "from testbed.salt import salt_source; print(salt_source('csprng'))"
```

Rotation is driven by the sim harness: for a cell with `rotation_interval > 0`
it mints a fresh salt every interval across the run and logs each event
(`{timestamp, old_salt, new_salt, interval, kind}`) via the real
`testbed/salt/rotation_log.py`, byte-identical to what the removed live
controller wrote.

### QRNG source setup

1. Mint an API key for the number-generation endpoint and store it (never
   commit it). This repo reads it from a gitignored `.env`:
   ```
   echo 'QEAAS_API_KEY=<the minted key>' > .env    # .env is gitignored
   ```
   or export it: `export QEAAS_API_KEY=<key>`. `QEAAS_BASE_URL` defaults to
   `https://api.qeaas.eu`.
2. Run the sim with the key in the environment:
   ```
   set -a && . ./.env && set +a && python3 testbed/sim/run_sim.py --exp 4
   ```
3. Provenance (`request_id`, `entropy_epoch`, `timestamp`, `receipt`) from the
   keyed `GET /v1/random/bytes` route is captured into the qrng cell's
   `.record.json` and exported to `web/public/replay/qrng-provenance.json`. If
   the endpoint is unavailable (e.g. `503`, or a server-side error), the qrng
   cells are recorded **skipped-with-reason** and the provenance placeholder is
   left in place — never a faked receipt.

### JS↔Python hash parity (AC-5)

```
python3 testbed/vectors/gen_vectors.py     # regenerate hash_vectors.json (Python is source of truth)
python3 testbed/vectors/check_parity.py    # recompute every vector via Node running ecmp_hash.js
```

`check_parity.py` exits `0` and prints `PASS: N/N vectors agree`, or non-zero
with every mismatch. `testbed/vectors/ecmp_hash.js` is the canonical JS mirror
the P6 demo imports directly — do not fork it. Needs `node` on `PATH`.

## Load-balancing entropy: fat-tree hash polarization (Plan 8)

A **second, attack-free** argument: a bad PRNG salt reused fabric-wide causes
systematic congestion (ECMP hash polarization) with zero attacker; CSPRNG/QRNG
salt spreads traffic evenly. This study is entirely offline
(`testbed/topology/fabric.py` + `polarization_check.py` above); its Mininet
launcher was removed with the rest of the live path (plan-10). `FATTREE_K`
(default `4`) sizes `fabric.py`'s `build_fattree()`. See
`../plans/plan-8-load-balancing-entropy.md` for the mechanism and design record.
