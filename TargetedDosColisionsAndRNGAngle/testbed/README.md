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
