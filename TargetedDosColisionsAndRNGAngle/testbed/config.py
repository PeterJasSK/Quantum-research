"""Testbed constants.

Topology (epic diagram): attacker + bg attach to the leaf switch (s1); N
parallel links run from leaf to the spine switch (s2); victim attaches to
the spine. The ECMP hash on s1 picks which of the N links carries traffic
toward the spine/victim -- this is what makes hashing observable at all
(a victim attached directly to s1, with nothing beyond the spine, would
never actually need multipath selection to be reached).

Victim set and link count are data, not literals (epic Q1 headroom: a second
victim on a different link must be a cheap config change -- add another
entry with location="spine" and a topology link, not a rewrite).
"""
from __future__ import annotations

N_LINKS = 4

LEAF_DPID = 1  # Mininet derives dpid 1 from switch name "s1"
SPINE_DPID = 2  # dpid 2 from "s2"

# host name -> {ip, mac, location}. location "leaf" = attached to s1 directly;
# "spine" = attached to s2, reached from s1 only via the N hashed links.
HOSTS = {
    "attacker": {"ip": "10.0.0.1", "mac": "00:00:00:00:00:01", "location": "leaf"},
    "bg": {"ip": "10.0.0.3", "mac": "00:00:00:00:00:03", "location": "leaf"},
    "victim": {"ip": "10.0.0.2", "mac": "00:00:00:00:00:02", "location": "spine"},
}

_LEAF_HOSTS = [name for name, h in HOSTS.items() if h["location"] == "leaf"]
_SPINE_HOSTS = [name for name, h in HOSTS.items() if h["location"] == "spine"]

# Port numbers on s1: leaf-attached hosts get the first ports (in HOSTS
# iteration order -- ecmp_topo.py must add links in this same order), then
# the N egress links to the spine occupy the remaining ports.
LEAF_LOCAL_PORTS = {name: i + 1 for i, name in enumerate(_LEAF_HOSTS)}
LOCAL_PORTS = list(LEAF_LOCAL_PORTS.values())
EGRESS_PORTS = list(
    range(len(_LEAF_HOSTS) + 1, len(_LEAF_HOSTS) + 1 + N_LINKS)
)

# dst IP -> local s1 port, for hosts s1 can deliver to directly (no hashing).
LOCAL_IP_TO_PORT = {HOSTS[name]["ip"]: LEAF_LOCAL_PORTS[name] for name in _LEAF_HOSTS}

# IPs reachable only via the spine -- these go through ecmp_link() on s1.
REMOTE_IPS = {HOSTS[name]["ip"] for name in _SPINE_HOSTS}

# P1's salt is a static hardcoded placeholder. Real sources (prng/csprng/qrng)
# and rotation are P2 — do not build them here.
STATIC_SALT = b"p1-static-placeholder-salt-do-not-use-in-p2"

CONTROLLER_LISTEN_ADDR = "127.0.0.1"
CONTROLLER_LISTEN_PORT = 6653  # standard OpenFlow port
