# Plan 1 — Testbed scaffolding & the salt-in-hash spike

**Epic:** [ECMP Collision DoS](../epic-ecmp-collision-dos.md) · **Source EPIC 0** · **Priority:** `[MUST]`
**Status:** Approved · **Depends on:** none (first plan) · **Gates:** P2, P3, P4

 sudo mn -c                                                                                                                                                                                                                                                        
  cd /home/peter/PycharmProjects/Quantum-research/TargetedDosColisionsAndRNGAngle                                                                                                                                                                                   
  sudo .venv/bin/python3 testbed/topology/run_topo.py                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                    
  Then in the CLI:                                                                                                                                                                                                                                                  
  attacker tcpdump -i attacker-eth0 -n -c 10 arp > /tmp/attacker_arp.log 2>&1 &                                                                                                                                                                                     
  bg tcpdump -i bg-eth0 -n -c 10 arp > /tmp/bg_arp.log 2>&1 &                                                                                                                                                                                                       
  attacker ping -c1 bg                                                                                                                                                                                                                                              
  sh sleep 1                                                                                                                                                                                                                                                        
  sh cat /tmp/attacker_arp.log                                                                                                                                                                                                                                      
  sh cat /tmp/bg_arp.log                                                                                                                                                                                                                                            
  exit              

> Pick up with `/plan-feature plans/plan-1-testbed-scaffolding.md`. Read epic §3.4 (simulation is sufficient),
> §3.5 (frozen interfaces), §5 (mechanism), §7 (order) first.
> **No GitHub issue** — this project plans from the epic + source build plan, not from a tracker.
> **No automated tests** (project directive) — verification is manual, described in §Manual verification.

## Goal
A running Mininet/OVS/Ryu ECMP topology whose salt is **provably part of the path-selection hash**. This plan
de-risks the whole epic: if the salt does not enter the hash, nothing downstream works. It also **freezes two
decisions every later plan inherits** — the ECMP mechanism (native OVS vs controller-side) and the repo layout /
`hash_core` factoring — so P2–P6 build on a fixed foundation.

## Context (why this is P1, and what it must not do)
- The epic is an **attack paper** (epic §3.1). P1 builds only the stage: topology up, traffic spreads across N
  links, salt provably steers the hash. No salt *sources*, no attacker, no defences — those are P2/P3/P4.
- The single risky unknown is **S0.2**: does our salt actually change the egress link? Everything downstream
  (attacker collision-crafting, rotation defence, the five experiments) assumes yes. Prove it **first**, before
  writing the full topology, so a negative result costs a spike and not the epic.
- Q1 decision (epic §8, resolved): the topology must **leave room for a cheap second victim on a different link**
  so the fabric-wide blast-radius run is a low-cost bolt-on later. P1 does not build the second victim; it just
  does not hard-code a single-victim assumption (N links, port list, victim set are config, not literals).

## Do this first — the S0.2 spike
The one risky unknown. Prove that changing the salt re-maps a fixed 5-tuple to a different link **before** building
the full topology.

- Bring up a **minimal** OVS switch with `N=4` egress ports (no hosts/Mininet niceties yet — `ovs-vsctl` +
  `ovs-ofctl` by hand or a 20-line script is enough).
- Attempt the **native path first**: an OpenFlow `select` group with `N` buckets over the egress ports; inspect
  whether the OVS version lets the salt/seed enter the hash (`ovs-ofctl -O OpenFlow15 dump-groups`, check
  `selection_method`/`fields`). Most stock OVS builds hash the 5-tuple but **do not expose an operator-settable
  salt seed** — verify on this box, do not assume.
- If native cannot take our salt (expected — see §Decision D1), confirm the **controller-side fallback** works:
  Ryu computes `hash(5-tuple + salt) mod N` and installs an exact-match flow rule pinning that 5-tuple to the
  chosen output port. This is what the rest of the epic almost certainly runs on.
- **10-line check** (`testbed/spike/salt_remap_check.py`): pick one fixed 5-tuple, compute the egress port under
  `salt_A`, then under `salt_B`, assert the two differ, print both. This is the epic's de-risking gate.

## Decision D1 — ECMP mechanism: native OVS vs controller-side *(frozen here; P2–P6 inherit)*
The salt in this epic is a **value we mint and rotate** (PRNG/CSPRNG/QRNG bytes, P2). Stock OVS ECMP hashes the
5-tuple with an internal key you cannot set to "these 32 QRNG bytes," so native hashing cannot carry our salt.
**Recommendation: controller-side ECMP** — Ryu owns `hash(5-tuple + salt) mod N` (the `hash_core`) and installs the
resulting output port as an exact-match flow rule. This gives us (a) an operator-settable, rotatable salt, (b) the
**exact same `hash_core` the attacker (P3) and JS demo (P6) must share** (epic §3.5), and (c) full observability of
the mapping. The spike may still find a native path; if so, note it, but the epic's shared-hash requirement
(§3.5, §4) strongly favours controller-side regardless. **The spike result records the final decision in this file
before P2 starts.**

**D1 outcome (recorded 2026-07-24):** confirmed on this box — OVS 3.3.4, `dump-groups` on a 4-bucket `select` group
shows no `selection_method`/`fields` line, i.e. the default 5-tuple hash with no operator-settable salt/seed
field. Native OVS cannot take our salt. **Decision: controller-side ECMP** (os_ken/Ryu computes
`hash(5-tuple + salt) mod N` via `hash_core.ecmp_link`, installs exact-match flow rules) — implemented in
`testbed/controller/ecmp_controller.py`. P2–P6 inherit this.

## Acceptance criteria (verbatim from `ECMP_COLLISION_DOS_BUILD_PLAN.md`)
- [ ] **AC-1** Mininet script: attacker host, victim host, background-traffic host, OVS switch, **N parallel links** (default 4) to an egress/spine.
- [ ] **AC-2** Ryu app installs ECMP group/multipath rules so traffic spreads by `hash(5-tuple + salt) mod N`.
- [ ] **AC-3** Prove that changing the salt re-maps a fixed 5-tuple to a different link. If OVS won't take a salt into its native hash, fall back to a Ryu-computed `hash(5-tuple+salt)` that writes the output link into the flow rule (controller-side ECMP).
- [ ] **AC-4** 10-line check: same 5-tuple, two salts → two different egress links.
- **Done when:** the topology boots, traffic distributes across N links, and flipping the salt provably re-maps flows.

## File plan
No testbed code exists yet — everything below is **new**. Python 3, PEP 8, type hints on all public functions;
Ryu app follows the standard `RyuApp` structure. All paths relative to `TargetedDosColisionsAndRNGAngle/`.

| File | Purpose | Notes |
|------|---------|-------|
| `testbed/hash_core.py` | **The frozen `link = hash(5tuple, salt) mod N` core.** Pure function, no Mininet/Ryu imports. `def ecmp_link(five_tuple: FiveTuple, salt: bytes, n_links: int) -> int`. | AC-2/AC-3. **Factorable** — P2 lifts this unchanged into the shared module (epic §3.5, §4); attacker (P3) and JS demo (P6) consume it. Keep it dependency-free so it imports anywhere. |
| `testbed/types.py` | `FiveTuple` dataclass (`src_ip, dst_ip, src_port, dst_port, proto`) + canonical byte serialisation used by `hash_core`. | Serialisation order is load-bearing for JS↔Python parity (P2); fix it here. |
| `testbed/config.py` | Testbed constants: `N_LINKS = 4`, egress port list, host/IP/MAC map, the **static P1 salt** (a hardcoded placeholder — real sources are P2), controller listen addr. | Keep victim set and link count as data, not literals (Q1 headroom). |
| `testbed/topology/ecmp_topo.py` | Mininet `Topo`: attacker host, victim host, bg-traffic host, one OVS switch, **N parallel links** to a spine/egress node. | AC-1. Reads `N_LINKS`/port map from `config.py`. Second-victim slot left cheap to add (Q1). |
| `testbed/topology/run_topo.py` | Launcher: build the net, start OVS in OpenFlow15 mode, point it at the Ryu controller, drop into Mininet CLI. | Manual-verification entry point. |
| `testbed/controller/ecmp_controller.py` | Ryu `RyuApp`: on packet-in / flow setup, call `hash_core.ecmp_link(...)` with the active (static, P1) salt and install an exact-match flow rule to the chosen egress port. Log every 5-tuple→port decision. | AC-2/AC-3. Controller-side ECMP per D1. Salt is static in P1; P2 makes it a source + rotatable. |
| `testbed/spike/salt_remap_check.py` | The **10-line S0.2 check**: fixed 5-tuple, two salts → assert two different ports, print both. | AC-4. Runs standalone (imports only `hash_core`), no topology needed. |
| `testbed/README.md` | How to boot the topo, run the spike, and drive traffic to see the spread. Prereqs (Mininet, OVS ≥ the verified version, Ryu). | The manual-verification runbook. |
| `TargetedDosColisionsAndRNGAngle/requirements.txt` | `ryu` (+ pin), plus a note that Mininet/OVS are system packages (`apt install mininet openvswitch-switch`), not pip. | First code in this project → establish it here. |

## Manual verification (no automated tests — project directive)
1. **Spike (AC-4), run this first:** `python3 testbed/spike/salt_remap_check.py` → prints the same 5-tuple's egress
   port under two salts and asserts they differ. Non-zero exit / equal ports = the epic's core assumption is broken;
   stop and reconsider before building further.
2. **Topology boots (AC-1):** `sudo python3 testbed/topology/run_topo.py` → Mininet CLI opens; `net` and `links`
   show attacker/victim/bg hosts, the OVS switch, and 4 parallel links to the spine.
3. **Traffic spreads across N links (Done-when):** from the CLI, generate a handful of distinct flows
   (e.g. `attacker ping` / `iperf` with varying source ports, or `hping3`), then read OVS port counters
   (`ovs-ofctl -O OpenFlow15 dump-ports <switch>`) and confirm traffic lands on more than one egress port.
4. **Salt provably re-maps flows (AC-3):** with the topology up, change the static salt in `config.py` (or via a
   controller reload), re-send the *same* fixed 5-tuple, and confirm from the controller log + port counters that it
   now egresses a **different** link. This is AC-3 end-to-end on the live testbed (the spike proves it in isolation).

## Tech
Mininet + Open vSwitch (real packets, real ECMP hashing), Ryu controller (Python) computes the salted hash and
installs flow rules. OpenFlow 1.5 (`select` groups exist if native is viable; controller-side path uses
exact-match flows). Topology mirrors the epic build-plan diagram: attacker + bg host + victim → OVS → N=4 links →
spine → victim.

## Out of scope
- Salt **sources** (`prng`/`csprng`/`qrng`) and **rotation** — **P2**. P1's salt is a static hardcoded placeholder.
- The precision/volumetric **attacker** — **P3**.
- **Defences** (rate-limit, throttle) and the **five metrics collectors / CSV** — **P4**.
- The **second victim / blast-radius** run — future bolt-on (Q1); P1 only leaves topology headroom for it.
- JS mirror of `hash_core` and shared **test vectors** — **P2** (P1 just keeps `hash_core` factorable & pure).

## Risks
- **Salt doesn't enter OVS native hash** → the S0.2 spike catches it up front; controller-side ECMP (D1) is the
  fallback and, per §3.5, the likely default anyway.
- **`hash_core` not cleanly factorable** → if it accretes Ryu/Mininet imports, P2 can't lift it and P3/P6 can't share
  it (silent demo drift, epic §3.3). Mitigation: `hash_core.py` and `types.py` import nothing from Ryu/Mininet.
- **Serialisation ambiguity** in the 5-tuple→bytes step → will bite JS↔Python parity in P2. Mitigation: fix a single
  canonical byte order in `types.py` now and document it.

## Progress / resume point (2026-07-24, paused mid-implementation)

**Status: in progress, not done.** Paused to come back to later — pick up at "Next step" below.

**Done:**
- Layer 1 (pure Python, no system deps) — `testbed/hash_core.py`, `types.py`, `config.py`,
  `spike/salt_remap_check.py`. Spike passes: `python3 testbed/spike/salt_remap_check.py` → PASS,
  different links for different salts. AC-4 satisfied.
- System deps installed: `mininet` + `openvswitch-switch` (apt), OVS 3.3.4. `ryu` pip install is
  broken on modern setuptools (dead upstream since 2021) — switched to **os-ken** (OpenStack's
  maintained fork, same `OSKenApp`/`RyuApp` API, `import os_ken`). Venv rebuilt on system Python
  3.12 (`/usr/bin/python3`) with `--system-site-packages` so it can see the apt-installed
  `mininet` module — the original Anaconda-Python venv couldn't.
- D1 native-OVS check run on this box: `dump-groups` on a 4-bucket `select` group shows no
  `selection_method`/`fields` — confirms native OVS can't take our salt. **Decision: controller-side
  ECMP**, recorded above in the D1 section.
- `os-ken` ships no `os-ken-manager` console script (library-only package for OpenStack Neutron) —
  wrote `testbed/controller/run_controller.py`, a ~15-line standalone launcher.
- Topology redesigned mid-build: initially put victim directly on the leaf switch (s1), which made
  the N egress links a dead end (nothing exercises the hash for victim-bound traffic). Epic §92-93's
  diagram (`attacker + bg → OVS(s1) → N links → spine(s2) → victim`) says victim sits *behind* the
  spine — fixed: `attacker`/`bg` attach to `s1` (leaf), `victim` attaches to `s2` (spine), N links
  join `s1`↔`s2`. `config.py` now derives `LOCAL_PORTS`/`EGRESS_PORTS`/`LOCAL_IP_TO_PORT`/`REMOTE_IPS`
  from `HOSTS[...]["location"]` so topology and controller agree on port numbers without duplicating
  the mapping.
- Controller (`ecmp_controller.py`) rewritten: only `s1` (`LEAF_DPID`) runs ECMP/controller logic;
  `s2` (spine) gets a single `actions=NORMAL` flow so OVS's own L2 learning handles delivery to/from
  victim — no controller-side logic needed there. `s1` distinguishes local-leaf destinations
  (direct port, no hashing) from spine-bound destinations (`ecmp_link` hash over `EGRESS_PORTS`).
  Also fixed: original `_extract_five_tuple` only handled TCP/UDP — `ping` (ICMP) was silently
  dropped; added an ICMP branch (ports 0/0).
- Discovered and partially fixed an **L2 broadcast-storm bug**: the 4 parallel `s1`↔`s2` links are a
  multigraph (no STP), so naively flooding ARP out every port loops forever. Fix in place: local-origin
  broadcast floods to (other local ports + exactly one designated uplink, `EGRESS_PORTS[0]`);
  spine-origin broadcast only goes to local ports, never back out to the spine.

**Not yet done / open problem:**
- `attacker ping bg` and `attacker ping victim` still fail with instant "Destination Host
  Unreachable" even after the storm-direction fix, and OVS port counters on `s1` still showed
  ~85 rx pkts on every spine-facing port over a ~29s window — i.e. the storm fix did not
  visibly change behaviour yet, or there's a second loop source not yet identified (candidates:
  `s2`'s own `NORMAL` flood also fanning out the other 3 uplinks in a way that isn't fully broken by
  `s1`'s side of the fix; leftover host-side periodic broadcast traffic; or the fix simply hadn't been
  tested on a clean environment yet).
- Ran `sudo mn -c` + `sudo ovs-vsctl del-br br0` (removed the never-cleaned-up scratch bridge from
  the D1 native-OVS check) to rule out stale state. **Have not yet re-run the storm-fix test on this
  clean state** — that's the next step.
- **Next step:** re-run the controller + topology from the clean state, and instead of inferring from
  `ping`'s output, use `tcpdump -i <host>-eth0 -n arp` on `attacker` and `bg` during a ping to see
  directly whether the ARP request leaves attacker's interface and whether a reply comes back — this
  will show whether the remaining problem is in `s1`'s flood logic, `s2`'s `NORMAL` bridging, or
  something else. Once ARP resolves and ping works, re-run manual verification steps 3–4 (traffic
  spread across links, AC-3 live salt re-map) and mark AC-1/AC-2/AC-3 as covered.
- Not started: recording the exact `ovs-vsctl --version` output into `testbed/README.md`'s prereqs
  section in the precise format OQ-2 asked for (currently inlined into the README manually — fine,
  but double check it matches before closing out this plan).

## Notes for `/plan-feature` (downstream)
- `hash_core.py` is the seed of the epic's frozen `hash_core` (epic §4). P2 lifts it into the shared module and adds
  the JS mirror + test vectors — do not let P1 bury it inside the controller.
- Record the **D1 outcome** (native vs controller-side) in this file once the spike runs; P2–P6 inherit it verbatim.

## Open questions — RESOLVED (2026-07-24, all defaults accepted)
- **OQ-1 — Repo layout for testbed code. RESOLVED:** adopt the proposed layout — a top-level `testbed/` package
  (under `TargetedDosColisionsAndRNGAngle/`) with `topology/`, `controller/`, `spike/`, and shared
  `hash_core.py`/`types.py` at its root. P2's shared module lifts from `testbed/hash_core.py`.
- **OQ-2 — OVS / OpenFlow version to target. RESOLVED:** target whatever `ovs-vsctl --version` reports on the build
  box, OpenFlow 1.5; record the exact version in `testbed/README.md` when the spike runs, for reproducibility.
- **OQ-3 — D1 (controller-side ECMP) as default. RESOLVED:** yes. Proceed assuming controller-side ECMP; native OVS
  is a spike-only check we most likely discard. The spike records the final D1 outcome in this file before P2.
