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
