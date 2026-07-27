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

import os

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

# P1's salt is a static hardcoded placeholder, kept as the default when
# rotation/sources are disabled.
STATIC_SALT = b"p1-static-placeholder-salt-do-not-use-in-p2"

CONTROLLER_LISTEN_ADDR = "127.0.0.1"
CONTROLLER_LISTEN_PORT = 6653  # standard OpenFlow port

# --- P2: salt engine config (AC-2, AC-3) ---

SALT_SIZE = 32
SALT_KIND = os.environ.get("SALT_KIND", "prng")  # "prng" | "csprng" | "qrng"
ROTATION_INTERVAL_SECONDS = float(os.environ.get("ROTATION_INTERVAL_SECONDS", "0"))  # 0 = off

# Weak-PRNG seed space (OQ-2): 32-bit, small enough for P3's brute-force to
# be tractable, honest as a "weak PRNG".
PRNG_SEED = int(os.environ.get("PRNG_SEED", "0"))

# Q-EaaS connection (epic Appendix A.3/A.4): key from env only, never
# committed. Hosted endpoint is the default target (epic s8 Q6).
QEAAS_BASE_URL = os.environ.get("QEAAS_BASE_URL", "https://api.qeaas.eu")
QEAAS_API_KEY = os.environ.get("QEAAS_API_KEY", "")

ROTATION_LOG_PATH = os.environ.get("ROTATION_LOG_PATH", "rotation_events.jsonl")

# --- P3: attacker config (AC-1-4) ---

# Index into EGRESS_PORTS the precision attacker targets (OQ-4). A
# realistic run instead reads the victim's current link from a
# PlacementOracle probe and overrides this default.
TARGET_LINK = int(os.environ.get("TARGET_LINK", "0"))

# Spoof pool for the precision attacker's "multiple compliant sources"
# (OQ-3) -- src-IP spoofing from the single `attacker` host, no topology
# change.
ATTACK_SOURCE_IPS = [f"10.0.0.{i}" for i in range(100, 116)]

# Per-source send rate caps (AC-3/AC-4): precision stays under the P4
# defence thresholds per spoofed source; volumetric floods a single fixed
# flow at a naively high rate.
PRECISION_PER_SOURCE_PPS = int(os.environ.get("PRECISION_PER_SOURCE_PPS", "5"))
VOLUMETRIC_PPS = int(os.environ.get("VOLUMETRIC_PPS", "1000"))

# Weak-PRNG brute-force bounds the partial attacker searches (OQ-2): the
# P2-frozen 32-bit seed space, re-searched per rotation, at a bounded
# draw-index window.
PRNG_SEED_SPACE_BITS = int(os.environ.get("PRNG_SEED_SPACE_BITS", "32"))
BRUTEFORCE_DRAW_WINDOW = int(os.environ.get("BRUTEFORCE_DRAW_WINDOW", "4"))

# --- P4: defence/metrics config (AC-1-7) ---

# Off by default so P3's existing runs and the "defences off" experiment
# cells are unaffected (plan-4 Design "Toggle"). When off, packet_in_handler
# is byte-for-byte today's behaviour.
DEFENCES_ENABLED = os.environ.get("DEFENCES_ENABLED", "0") == "1"

# Per-source rate limit (AC-1, OpenFlow meter, OFPMF_KBPS). Tuned with an
# order-of-magnitude margin on both sides of PRECISION_PER_SOURCE_PPS=5 (~40
# kbps at ~1000B packets) and VOLUMETRIC_PPS=1000 single-source (~8000
# kbps): 1000 kbps sits an order of magnitude above one precision source and
# well under one volumetric source. Frozen once verified live (plan-4
# "Threshold tuning") -- do not re-tune per experiment.
RATE_LIMIT_KBPS = int(os.environ.get("RATE_LIMIT_KBPS", "1000"))
RATE_LIMIT_BURST_KB = int(os.environ.get("RATE_LIMIT_BURST_KB", "100"))

# Per-source connection throttle (AC-2): new-flow count over a sliding
# window. Same margin logic as the rate limit above.
THROTTLE_MAX_CONNECTIONS = int(os.environ.get("THROTTLE_MAX_CONNECTIONS", "20"))
THROTTLE_WINDOW_SECONDS = float(os.environ.get("THROTTLE_WINDOW_SECONDS", "5"))
THROTTLE_ACTION = os.environ.get("THROTTLE_ACTION", "drop")  # "drop" | "deprioritise" (OQ-5)

# Instrumentation (AC-4/5/6/7).
PORT_STATS_POLL_INTERVAL_SECONDS = float(os.environ.get("PORT_STATS_POLL_INTERVAL_SECONDS", "0.5"))
# Must match the P1 topology's TCLink bandwidth for each egress link (OQ-3
# single source of truth) -- if the topology sets no `bw`, pin one there too.
LINK_CAPACITY_MBPS = float(os.environ.get("LINK_CAPACITY_MBPS", "10"))
SATURATION_UTILISATION = float(os.environ.get("SATURATION_UTILISATION", "0.9"))
METRICS_CSV_PATH = os.environ.get("METRICS_CSV_PATH", "metrics.csv")
# Rolling JSON-lines file `victim_throughput.py` writes to and the collector
# reads from (AC-6); out-of-band, not read via the OpenFlow channel.
VICTIM_THROUGHPUT_PATH = os.environ.get("VICTIM_THROUGHPUT_PATH", "victim_throughput.jsonl")

# --- P8: fat-tree / load-balancing entropy config ---

# Fat-tree fan-out (Al-Fares k=4: 4 core, 4 pods x (2 agg + 2 edge), 2 hosts
# per edge -> 16 hosts, 20 switches). Leaf-spine/other k out of scope (plan-8).
FATTREE_K = int(os.environ.get("FATTREE_K", "4"))

# Off by default so P1-P5's single-leaf topology/controller stay byte-for-byte
# unchanged (same toggle discipline as DEFENCES_ENABLED). On: every fabric
# switch hashes its own upward fan-out under a per-dpid salt (plan-8 AC-2).
FABRIC_MODE = os.environ.get("FABRIC_MODE", "0") == "1"

# --- P5: experiment orchestrator + analysis config (AC-1-7) ---

# Single source of truth for the matrix (plan-5 Config additions).
KNOWLEDGE_LEVELS = ("full", "partial", "blind")
SALT_SOURCES = ("prng", "csprng", "qrng")

# How long each live cell runs before teardown (harness.py).
RUN_DURATION_SECONDS = float(os.environ.get("RUN_DURATION_SECONDS", "30"))

# Exp 5 rotation sweep (OQ-4): log-spaced, slow->fast, straddling the
# analytical T_bf derived from PRNG_SEED_SPACE_BITS/BRUTEFORCE_DRAW_WINDOW.
ROTATION_SWEEP_INTERVALS = [60.0, 30.0, 10.0, 5.0, 2.0, 1.0, 0.5]

# Success predicate threshold (OQ-2): attacker_succeeded requires
# min_victim_mbps to drop to/under this, on top of saturated=True.
VICTIM_COLLAPSE_MBPS = float(os.environ.get("VICTIM_COLLAPSE_MBPS", "1.0"))

RESULTS_DIR = os.environ.get("RESULTS_DIR", "results")
GRAPH1_PATH = os.environ.get("GRAPH1_PATH", os.path.join(RESULTS_DIR, "graph1_success_matrix"))
GRAPH2_PATH = os.environ.get("GRAPH2_PATH", os.path.join(RESULTS_DIR, "graph2_rotation_threshold"))
