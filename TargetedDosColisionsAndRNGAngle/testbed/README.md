# ECMP testbed (Plan 1 — scaffolding & the S0.2 spike)

## Prereqs

- Mininet + Open vSwitch (system packages):
  `sudo apt install mininet openvswitch-switch`
- `os-ken` (maintained fork of Ryu — plain `ryu` fails to install on modern
  setuptools; see `../requirements.txt`):
  `python3 -m venv .venv && .venv/bin/pip install -r ../requirements.txt`
- OVS / OpenFlow version on this box: `ovs-vsctl (Open vSwitch) 3.3.4`, DB
  Schema 8.5.1 (Ubuntu noble-updates package `openvswitch-switch`), OpenFlow 1.5
  supported (`-O OpenFlow15` on `ovs-ofctl`).

## D1 decision record (native OVS vs controller-side ECMP)

**Controller-side ECMP**, per epic decision D1 — Ryu/os_ken computes
`hash(5-tuple + salt) mod N` (`testbed/hash_core.py`) and installs an
exact-match flow rule pinning each observed 5-tuple to the chosen egress
port. `<TODO: after running the native-OVS check with ovs-ofctl, note here
whether this box's OVS build exposes an operator-settable hash seed, or
confirms the expected controller-side fallback.>`

## 1. Run the spike first (AC-4)

No topology needed — pure Python, imports only `hash_core`/`types`:

```
python3 testbed/spike/salt_remap_check.py
```

Expected: prints the same 5-tuple's egress port under two salts, asserts
they differ, exits 0. Non-zero exit / equal ports means the epic's core
assumption is broken — stop before building further.

## 2. Boot the topology (AC-1)

```
.venv/bin/python3 testbed/controller/run_controller.py &
sudo .venv/bin/python3 testbed/topology/run_topo.py
```

(os-ken ships no `os-ken-manager` console script — it's a library for OpenStack
Neutron, not a standalone controller like `ryu-manager` was. `run_controller.py`
is a ~15-line launcher that loads `os_ken.controller.ofp_handler` +
`ecmp_controller` the same way `ryu-manager` did.)

The Mininet CLI opens; `net` and `links` should show `attacker`, `victim`,
`bg` hosts, the OVS switch `s1`, and `N_LINKS` (default 4) parallel links to
`spine`.

## 3. Traffic spreads across N links (Done-when)

From the Mininet CLI, generate a handful of distinct flows (varying source
ports), e.g.:

```
mininet> attacker ping -c1 victim
mininet> attacker iperf -c victim -p 5001 &
```

Then read OVS port counters:

```
ovs-ofctl -O OpenFlow15 dump-ports s1
```

Confirm traffic lands on more than one egress port.

## 4. Salt provably re-maps flows (AC-3)

With the topology up, change `STATIC_SALT` in `testbed/config.py`, restart
the controller, re-send the *same* fixed 5-tuple, and confirm from the
controller log + port counters that it now egresses a **different** link.

## 5. Salt engine — sources, rotation, JS↔Python parity (Plan 2)

### Salt sources (AC-2)

Select via `SALT_KIND` env var: `prng` (default) | `csprng` | `qrng`.

- `prng` — weak, reconstructable: `random.Random(PRNG_SEED)` (default seed
  `0`), sequential draws. This is deliberately the attacker's brute-force
  target (P3) — do not use it for anything except demonstrating the attack.
- `csprng` — `secrets.token_bytes`.
- `qrng` — the hosted Q-EaaS service (below).

```
SALT_KIND=csprng .venv/bin/python3 testbed/controller/run_controller.py &
```

### QRNG source setup (Appendix A)

1. Mint an API key (needs `ADMIN_TOKEN`, run from `qrng-eaas/api/`):
   ```
   python -m scripts.mint_key --owner ecmp-dos-testbed --tier default
   ```
2. Export the key (never commit it):
   ```
   export QEAAS_API_KEY=<the minted key>
   export QEAAS_BASE_URL=https://api.qeaas.eu   # default, can omit
   ```
3. Run with `SALT_KIND=qrng`. Provenance (`request_id`, `entropy_epoch`,
   `timestamp`, `receipt`) is logged on every salt fetch.
4. Quick smoke check without the testbed:
   ```
   .venv/bin/python3 -c "from testbed.salt import salt_source; print(salt_source('qrng'))"
   ```

### Rotation (AC-3, AC-4)

`ROTATION_INTERVAL_SECONDS` (default `0` = off) makes the controller rotate
`active_salt` on a timer (`os_ken.lib.hub.spawn` green thread) and reinstall
every tracked ECMP flow under the new salt. `ECMPController.rotate_salt()` is
also callable manually (e.g. from a demo / REPL against a running
controller instance).

```
SALT_KIND=csprng ROTATION_INTERVAL_SECONDS=5 .venv/bin/python3 testbed/controller/run_controller.py &
```

Rotation events are appended as JSON lines to `ROTATION_LOG_PATH` (default
`rotation_events.jsonl`): `{timestamp, old_salt, new_salt, interval, kind}`.

**Atomic mechanism**: the controller tries an OpenFlow bundle
(`OFPBundleCtrlMsg` OPEN → `OFPBundleAddMsg` DELETE+ADD per tracked flow →
COMMIT) first. If no `COMMIT_REPLY` arrives within 2s, or an
`OFPET_BUNDLE_FAILED` error is received, it falls back permanently (for the
life of the controller process) to delete-and-lazy-re-resolve: all tracked
ECMP flows are deleted and the next packet-in per 5-tuple re-resolves under
the new salt (brief controller round-trip, no packet drop). `rotate_salt()`
logs which mechanism was used each time. **`<TODO: record here which
mechanism this box's OVS/OF1.5 build actually uses, once verified live —
see manual verification step 4 below.>`**

### JS↔Python hash parity (AC-5)

```
python3 testbed/vectors/gen_vectors.py     # regenerate hash_vectors.json from Python (source of truth)
python3 testbed/vectors/check_parity.py    # recompute every vector via Node running ecmp_hash.js
```

`check_parity.py` exits `0` and prints `PASS: N/N vectors agree`, or exits
non-zero and prints every mismatching vector. `testbed/vectors/ecmp_hash.js`
is the canonical JS mirror the P6 demo imports directly — do not fork it.
Requires `node` on `PATH` (only needed to run the parity checker, not the
testbed itself).

## Running the attacker (Plan 3)

`testbed/attacker/` is the "new attacker" (epic §3.1): it damages by
mathematical placement, not by any behaviour a source-watching defence can
observe. Three knowledge levels (`full` | `partial` | `blind`), two traffic
modes (`volumetric` | `precision`).

### Offline check (no Mininet/root)

```
.venv/bin/python3 testbed/attacker/collision_check.py
```

Confirms: every crafted "collision" 5-tuple actually hashes to the target
link under the real `ecmp_link`; the blind fallback spreads ~uniformly
across links; the partial attacker's `SeedBruteForcer` recovers a known
seed. Non-zero exit on any of the three.

### Live traffic (needs Mininet + OVS + root)

Boot the P1 topology + P2 controller (`SALT_KIND=prng`, rotation off), then
from the `attacker` host:

```
# Volumetric control (AC-3) -- single fixed flow, high rate:
sudo .venv/bin/python3 testbed/attacker/run_attack.py \
    --level full --mode volumetric --salt <controller active_salt hex>

# Precision, full knowledge (AC-4):
sudo .venv/bin/python3 testbed/attacker/run_attack.py \
    --level full --mode precision --salt <controller active_salt hex>

# Precision, partial knowledge -- brute-forces the weak-PRNG seed space,
# validated against a placement oracle built from the true salt
# (simulates the congestion/timing side channel, epic §3.1/P7):
sudo .venv/bin/python3 testbed/attacker/run_attack.py \
    --level partial --mode precision --oracle-salt <controller active_salt hex> \
    --seed-space-bits 16 --draw-window 4

# Blind (expected-failure baseline):
sudo .venv/bin/python3 testbed/attacker/run_attack.py --level blind --mode precision
```

Each run prints a JSON run-record (`{level, mode, target_link,
salt_source, sources_used, flows_sent, reconstruction}`) — P4/P5 consume
this shape directly, no reshaping. `sources_used` should show the spoofed
`ATTACK_SOURCE_IPS` pool for `precision`; confirm via `ovs-ofctl -O
OpenFlow15 dump-ports s1` that the target link's counters climb while no
single source exceeds `PRECISION_PER_SOURCE_PPS`.

The **spoof pool needs root/netns** to send arbitrary `src_ip`s from the
single `attacker` host (scapy). If OVS/Mininet drops spoofed-source packets
(RPF/anti-spoof), that's a P1 topology escalation (OQ-3), not a P3 fix.

## Running with defences + metrics (Plan 4)

`testbed/controller/defences.py` (per-source rate-limit meter + connection
throttle) and `testbed/metrics/` (the five metrics → run-tagged CSV) are the
baseline defences that must *stop the volumetric flood but fail against
precision* (epic §3.1). Everything below is gated on `DEFENCES_ENABLED`
(default off) — the OFF path is byte-for-byte today's controller behaviour.

### Offline check (no Mininet/root)

```
.venv/bin/python3 testbed/metrics/metrics_check.py
```

Confirms: per-link utilisation / `max_link_util` match a hand-computed
delta-over-capacity calculation; `jains_index([0,0,0,0])==1.0`,
`jains_index([1,1,1,1])==1.0`, `jains_index([4,0,0,0])==0.25`; and
time/packets/flows-to-saturation latch on the correct poll of a rising
series. Non-zero exit on any mismatch.

### Threshold defaults (frozen, `testbed/config.py`)

`RATE_LIMIT_KBPS=1000` and `THROTTLE_MAX_CONNECTIONS=20` (per
`THROTTLE_WINDOW_SECONDS=5`) sit an order of magnitude above one precision
source (`PRECISION_PER_SOURCE_PPS=5`) and well under one volumetric source
(`VOLUMETRIC_PPS=1000`). These are **not re-tuned per experiment** — a
moving threshold would make "precision evades / volumetric caught"
unfalsifiable (plan-4 Design). `THROTTLE_ACTION=drop` (default) installs a
priority-20 drop flow past the limit; `deprioritise` instead reinstalls the
ECMP flow at priority 1.

### Live run (needs Mininet + OVS + root)

```
DEFENCES_ENABLED=1 SALT_KIND=prng .venv/bin/python3 testbed/controller/run_controller.py &
sudo .venv/bin/python3 testbed/topology/run_topo.py
```

From the `attacker` host, drive a volumetric flood and confirm:

```
ovs-ofctl -O OpenFlow15 dump-meters s1     # per-source meter, capped ~RATE_LIMIT_KBPS
ovs-ofctl -O OpenFlow15 dump-flows s1      # priority-20 drop flow once THROTTLE_MAX_CONNECTIONS is exceeded
```

...and that a precision run (`--mode precision`, spread across
`ATTACK_SOURCE_IPS`) never trips either — no drop flow, no meter overflow,
per source.

`METRICS_CSV_PATH` (default `metrics.csv`) fills with one row per poll
(`PORT_STATS_POLL_INTERVAL_SECONDS`, default 0.5s), tagged
`(salt_source, knowledge_level, rotation_interval, attack_mode)`;
`knowledge_level`/`attack_mode` come from the `KNOWLEDGE_LEVEL`/`ATTACK_MODE`
env vars (default `"na"`) since the controller can't infer them. A
`*.summary.csv` sidecar next to it holds one always-current row with
`time_to_saturation_s`, `packets_to_saturation`, `flows_to_saturation`,
`final_jains_index`, `min_victim_mbps`, `saturated`.

## Running the experiment matrix + rendering graphs (Plan 5)

`testbed/experiments/` orchestrates the five experiments (AC-1-5) by driving
the frozen P2/P3/P4 pieces unchanged; `testbed/analysis/` reads the P4 CSVs
and renders the paper's two key graphs (AC-6, AC-7). P5 adds no new
mechanism -- see the plan for the full matrix.

### Prerequisites

- Everything P1-P4 need (Mininet, OVS, root, `os-ken`, `scapy`).
- `pandas`/`matplotlib` for `testbed/analysis/` (added to `requirements.txt`
  -- not needed on the live testbed host itself).
- `iperf3` for victim throughput (as in Plan 4).
- `QEAAS_API_KEY` in env for the `qrng` cells (Exp 4c, Exp 4d, the qrng
  Graph 1 column) -- see the Q-EaaS setup above.

### Offline check (no Mininet/root)

```
.venv/bin/python3 testbed/analysis/analysis_check.py
```

Confirms: `attacker_succeeded` classifies success/fail/healthy-victim rows
correctly; `rotation_threshold` recovers a planted crossover and computes
`T_bf`; `graphs.py` renders both figures to a temp dir. Non-zero exit on any
mismatch.

### Live runs (needs Mininet + OVS + root)

```
sudo .venv/bin/python3 testbed/experiments/run_experiments.py --exp 1
sudo .venv/bin/python3 testbed/experiments/run_experiments.py --exp all
```

`--exp {1,2,3,4,5,all}` selects cells from `testbed/experiments/matrix.py`
(the whole matrix is data, inspectable there without running it). Each cell
prints a PASS/FAIL against its expected summary result, then (unless
`--no-graphs`) the collected CSVs are handed to `testbed/analysis/graphs.py`,
producing `results/graph1_*.{png,svg}` and `results/graph2_*.{png,svg}`.

Per-cell CSVs land under `results/<exp>/<cell_id>.csv` (+ `.summary.csv`
sidecar, + `.record.json` for the attacker run-record) so no cell overwrites
another. Raw per-cell CSVs are gitignored (OQ-5) -- regenerate them by
re-running `run_experiments.py`; only the two figures and the Q4 replay
subset (three-scene runs + one QRNG provenance run + the full Exp 5 sweep,
**blind skipped**) are committed, for P6 Tier B replay and P7's write-up.

Victim throughput (AC-6) needs `iperf3` running out-of-band — start a
server on `victim` and a client on `bg` (see `testbed/metrics/
victim_throughput.py`'s `run_server`/`run_client`, or run `iperf3` directly
with `--json-stream` to `VICTIM_THROUGHPUT_PATH`, default
`victim_throughput.jsonl`); if `iperf3` isn't installed, `victim_mbps` is
written empty rather than crashing the run.
