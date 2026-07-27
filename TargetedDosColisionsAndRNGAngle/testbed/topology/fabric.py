"""Pure-data k=4 (Al-Fares) fat-tree model (plan-8). No Mininet/Ryu import --
this is the shared source of truth for the offline `polarization_check.py`
gate, the (heavier) live `FABRIC_MODE` controller, and the TS mirror
`web/lib/fabric.ts`. Reuses `hash_core.ecmp_link` unchanged (D8-parity).

Topology (k=4): `core_count = (k/2)**2` core switches, `k` pods, each pod has
`k/2` aggregation + `k/2` edge switches, each edge switch has `k/2` hosts --
4 core, 4 pods x (2 agg + 2 edge) = 16 switches, 20 switches total, 16 hosts.

Routing (D8-seed): a flow's egress at each switch is
`ecmp_link(five_tuple, salt, fanout)`. Only the **upward** hops are hashed
(edge->agg, agg->core), each using that switch's own per-switch salt (the
entropy knob). Downward (core->agg->edge->host) is deterministic by
destination pod/edge index, matching real ECMP fat-tree behaviour -- there is
nothing to hash once you know the destination subnet.

Honest-mechanism note (frozen in the plan): for k=4, `agg_per_pod == k // 2
== core_per_group`, so when an edge switch and its chosen aggregation switch
share the *same* salt (the fabric-wide-identical-prng case), both hops hash
the identical `sha256(five_tuple + salt)` digest against the *same* modulus
-- the two hop choices become perfectly correlated (`index2 == index1`
always), collapsing traffic onto a diagonal subset of core switches. This is
the polarization the offline check measures; it needs no attacker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from testbed.hash_core import ecmp_link
from testbed.salt.sources import salt_source
from testbed.types import FiveTuple


@dataclass(frozen=True)
class Fabric:
    k: int
    pods: int
    agg_per_pod: int
    edge_per_pod: int
    hosts_per_edge: int
    core_per_group: int
    core_count: int
    edge_switches: list[str] = field(default_factory=list)
    agg_switches: list[str] = field(default_factory=list)
    core_switches: list[str] = field(default_factory=list)
    all_switches: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    ip_to_host: dict[str, str] = field(default_factory=dict)
    host_to_ip: dict[str, str] = field(default_factory=dict)
    host_edge: dict[str, str] = field(default_factory=dict)
    edge_pod: dict[str, int] = field(default_factory=dict)
    agg_pod: dict[str, int] = field(default_factory=dict)
    agg_local_index: dict[str, int] = field(default_factory=dict)
    link_ids: list[str] = field(default_factory=list)


def _edge_name(pod: int, edge: int) -> str:
    return f"pod{pod}edge{edge}"


def _agg_name(pod: int, agg: int) -> str:
    return f"pod{pod}agg{agg}"


def _core_name(core: int) -> str:
    return f"core{core}"


def _host_name(pod: int, edge: int, host: int) -> str:
    return f"pod{pod}edge{edge}host{host}"


def _host_ip(pod: int, edge: int, host: int) -> str:
    return f"10.{pod}.{edge}.{host + 1}"


def _link_id(a: str, b: str) -> str:
    """Canonical (direction-independent) id for the single physical link
    between `a` and `b` -- a flow may traverse it upward or downward but it
    is the same link either way."""
    return "-".join(sorted((a, b)))


def build_fattree(k: int = 4) -> Fabric:
    """Canonical Al-Fares k-ary fat-tree: `pods = k`, `agg_per_pod = edge_per_pod
    = hosts_per_edge = core_per_group = k // 2`, `core_count = (k // 2) ** 2`."""
    half = k // 2
    edge_switches: list[str] = []
    agg_switches: list[str] = []
    core_switches: list[str] = [_core_name(c) for c in range(half * half)]
    all_switches: list[str] = list(core_switches)
    hosts: list[str] = []
    ip_to_host: dict[str, str] = {}
    host_to_ip: dict[str, str] = {}
    host_edge: dict[str, str] = {}
    edge_pod: dict[str, int] = {}
    agg_pod: dict[str, int] = {}
    agg_local_index: dict[str, int] = {}
    link_ids: list[str] = []

    for pod in range(k):
        for agg in range(half):
            agg_id = _agg_name(pod, agg)
            agg_switches.append(agg_id)
            all_switches.append(agg_id)
            agg_pod[agg_id] = pod
            agg_local_index[agg_id] = agg
        for edge in range(half):
            edge_id = _edge_name(pod, edge)
            edge_switches.append(edge_id)
            all_switches.append(edge_id)
            edge_pod[edge_id] = pod
            for agg in range(half):
                link_ids.append(_link_id(edge_id, _agg_name(pod, agg)))
            for host in range(half):
                host_id = _host_name(pod, edge, host)
                ip = _host_ip(pod, edge, host)
                hosts.append(host_id)
                ip_to_host[ip] = host_id
                host_to_ip[host_id] = ip
                host_edge[host_id] = edge_id
        for agg in range(half):
            agg_id = _agg_name(pod, agg)
            group_start = agg * half
            for core in range(group_start, group_start + half):
                link_ids.append(_link_id(agg_id, _core_name(core)))

    return Fabric(
        k=k,
        pods=k,
        agg_per_pod=half,
        edge_per_pod=half,
        hosts_per_edge=half,
        core_per_group=half,
        core_count=half * half,
        edge_switches=edge_switches,
        agg_switches=agg_switches,
        core_switches=core_switches,
        all_switches=all_switches,
        hosts=hosts,
        ip_to_host=ip_to_host,
        host_to_ip=host_to_ip,
        host_edge=host_edge,
        edge_pod=edge_pod,
        agg_pod=agg_pod,
        agg_local_index=agg_local_index,
        link_ids=link_ids,
    )


def fabric_salts(kind: str, fabric: Fabric) -> dict[str, bytes]:
    """Per-switch salt keyed by dpid/switch-id (D8-seed). `prng` -> one
    identical salt fabric-wide (models a same-image-same-seed deployment
    collapsing to a single seed everywhere -- OQ8-2); `csprng`/`qrng` ->
    an independent draw per switch."""
    if kind == "prng":
        shared = salt_source("prng").salt
        return {switch_id: shared for switch_id in fabric.all_switches}
    return {switch_id: salt_source(kind).salt for switch_id in fabric.all_switches}


def route(fabric: Fabric, salts: dict[str, bytes], five_tuple: FiveTuple) -> list[str]:
    """Walk src-edge -> (hashed) agg -> [same pod: straight to dst-edge |
    different pod: (hashed) core -> (deterministic) dst-agg -> (deterministic)
    dst-edge]. Returns the ordered link ids traversed. If src and dst share an
    edge switch, no hop is hashed (direct edge-host delivery) -- returns an
    empty list. Same-pod, different-edge traffic never detours through core
    (an aggregation switch reaches every edge switch in its own pod
    directly) -- mirrors real fat-tree behaviour and `next_hop()`'s per-switch
    decomposition exactly."""
    src_edge = fabric.host_edge[fabric.ip_to_host[five_tuple.src_ip]]
    dst_edge = fabric.host_edge[fabric.ip_to_host[five_tuple.dst_ip]]
    if src_edge == dst_edge:
        return []

    src_pod = fabric.edge_pod[src_edge]
    dst_pod = fabric.edge_pod[dst_edge]

    agg_choice = ecmp_link(five_tuple, salts[src_edge], fabric.agg_per_pod)
    src_agg = _agg_name(src_pod, agg_choice)

    if src_pod == dst_pod:
        return [_link_id(src_edge, src_agg), _link_id(src_agg, dst_edge)]

    core_choice = ecmp_link(five_tuple, salts[src_agg], fabric.core_per_group)
    core_id = _core_name(agg_choice * fabric.core_per_group + core_choice)

    dst_agg = _agg_name(dst_pod, agg_choice)

    return [
        _link_id(src_edge, src_agg),
        _link_id(src_agg, core_id),
        _link_id(core_id, dst_agg),
        _link_id(dst_agg, dst_edge),
    ]


def link_load(fabric: Fabric, salts: dict[str, bytes], flows: Sequence[FiveTuple]) -> list[int]:
    """Per-link flow counts over `flows`, ordered to match `fabric.link_ids`."""
    counts = {link_id: 0 for link_id in fabric.link_ids}
    for five_tuple in flows:
        for link_id in route(fabric, salts, five_tuple):
            counts[link_id] += 1
    return [counts[link_id] for link_id in fabric.link_ids]


def fabric_ports(fabric: Fabric) -> dict[str, dict[str, int]]:
    """Per-switch `{neighbor_id: port_no}`, port numbers assigned in the same
    link-creation order `fattree_topo.py`'s `build()` uses (inter-switch
    links from `fabric.link_ids`, then one host link per host in
    `fabric.hosts` order) so this matches Mininet's own port numbering."""
    ports: dict[str, dict[str, int]] = {switch_id: {} for switch_id in fabric.all_switches}
    counters: dict[str, int] = {switch_id: 0 for switch_id in fabric.all_switches}

    for link_id in fabric.link_ids:
        switch_a, switch_b = link_id.split("-")
        counters[switch_a] += 1
        ports[switch_a][switch_b] = counters[switch_a]
        counters[switch_b] += 1
        ports[switch_b][switch_a] = counters[switch_b]

    for host_id in fabric.hosts:
        edge_id = fabric.host_edge[host_id]
        counters[edge_id] += 1
        ports[edge_id][host_id] = counters[edge_id]

    return ports


def next_hop(fabric: Fabric, salts: dict[str, bytes], switch_id: str, five_tuple: FiveTuple) -> str:
    """The next-hop switch or host id for `five_tuple` arriving at `switch_id`
    (fabric-mode controller's per-switch decision -- the distributed
    decomposition of `route()`'s whole-path walk). Upward hops (edge->agg,
    agg->core) are hashed under `switch_id`'s own salt; downward hops are
    deterministic by destination pod/edge, matching `route()` exactly."""
    dst_host = fabric.ip_to_host[five_tuple.dst_ip]
    dst_edge = fabric.host_edge[dst_host]
    dst_pod = fabric.edge_pod[dst_edge]

    if switch_id in fabric.edge_switches:
        if switch_id == dst_edge:
            return dst_host
        pod = fabric.edge_pod[switch_id]
        agg_choice = ecmp_link(five_tuple, salts[switch_id], fabric.agg_per_pod)
        return _agg_name(pod, agg_choice)

    if switch_id in fabric.agg_switches:
        pod = fabric.agg_pod[switch_id]
        if pod == dst_pod:
            return dst_edge
        agg_local = fabric.agg_local_index[switch_id]
        core_choice = ecmp_link(five_tuple, salts[switch_id], fabric.core_per_group)
        return _core_name(agg_local * fabric.core_per_group + core_choice)

    # Core: deterministic to the agg in dst_pod belonging to this core's group.
    core_index = int(switch_id.removeprefix("core"))
    group = core_index // fabric.core_per_group
    return _agg_name(dst_pod, group)
