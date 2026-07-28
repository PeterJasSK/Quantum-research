"""The one new mechanism (plan-10 §1): a pure, deterministic flow-level
transport model.

Given a set of offered flows (each a real `FiveTuple` at a sustained rate)
and the real defence policy, it produces per-egress-link byte rates. It
imports the real `ecmp_link` and drives the real `DefencePolicy`; it never
re-implements the hash, the crafter, or the defences. No scapy, no OpenFlow,
no root -- the model that replaces Mininet/OVS transport.

Placement rule (the honest mechanism, computed by the real hash):
- **concentrated** -- the attacker holds the *current* salt (static known
  salt, or an in-time reconstruction), so its crafted set collides on the
  target link by construction (verified against the real hash in
  `sim_harness`). All surviving load lands on the target link.
- **dispersed** -- the attacker's set is invalid for the active salt (an
  unpredictable csprng/qrng rotation, or a reconstruction the rotation
  outran). The flows land wherever the *real* current hash sends them,
  modelled by hashing each surviving flow under a salt the attacker did not
  craft for (`DISPERSAL_SALT`) -> ~uniform spread across links.

The model carries the load the real components produce; it cannot flip a
saturation/evasion outcome the real hash + policy did not (plan-10 Risks).
"""
from __future__ import annotations

from dataclasses import dataclass

from testbed.controller.defences import DefencePolicy
from testbed.hash_core import ecmp_link
from testbed.types import FiveTuple

# A fixed salt the attacker never crafted for: hashing a crafted collision
# set under it reproduces the "invalidated by rotation" dispersal via the
# real hash, deterministically (independent of the craft salt, so an epoch
# whose active salt happens to equal the craft salt cannot leak concentration
# into the dispersed branch). 32 bytes to match SALT_SIZE.
DISPERSAL_SALT = b"plan10-dispersal-salt-independent!"[:32].ljust(32, b"\x00")


@dataclass(frozen=True)
class OfferedFlow:
    """One sustained attacker flow: a real 5-tuple offered at `offered_bps`."""

    five_tuple: FiveTuple
    offered_bps: float

    @property
    def src_ip(self) -> str:
        return self.five_tuple.src_ip


@dataclass(frozen=True)
class DefenceReport:
    """What the real defence policy did to the offered load this run."""

    metered_sources: tuple[str, ...]
    throttled_sources: tuple[str, ...]

    @property
    def fired(self) -> bool:
        return bool(self.metered_sources) or bool(self.throttled_sources)


def apply_defences(
    flows: list[OfferedFlow],
    *,
    enabled: bool,
    rate_limit_kbps: int,
    policy: DefencePolicy,
    now: float,
) -> tuple[list[OfferedFlow], DefenceReport]:
    """Run the real `DefencePolicy` over the offered flows (plan-10 §1).

    Throttle: a source whose distinct-flow count exceeds
    `THROTTLE_MAX_CONNECTIONS` in the window has *all* its flows dropped (the
    `drop` action). Meter: a source whose aggregate offered rate exceeds
    `RATE_LIMIT_KBPS` is capped to it (its flows scaled down proportionally).
    Frozen P4 thresholds are used unchanged -- the model never re-tunes them.
    """
    # Note every flow with the real policy (dedups on the 5-tuple flow key).
    for flow in flows:
        policy.note_flow(flow.src_ip, flow.five_tuple, now)

    if not enabled:
        return flows, DefenceReport(metered_sources=(), throttled_sources=())

    rate_limit_bps = rate_limit_kbps * 1000.0
    per_source_bps: dict[str, float] = {}
    for flow in flows:
        per_source_bps[flow.src_ip] = per_source_bps.get(flow.src_ip, 0.0) + flow.offered_bps

    throttled = tuple(sorted(s for s in per_source_bps if policy.is_throttled(s)))
    metered = tuple(
        sorted(s for s, bps in per_source_bps.items() if bps > rate_limit_bps and s not in throttled)
    )

    surviving: list[OfferedFlow] = []
    for flow in flows:
        if flow.src_ip in throttled:
            continue  # throttle action = drop
        total = per_source_bps[flow.src_ip]
        if flow.src_ip in metered and total > 0:
            scaled = flow.offered_bps * (rate_limit_bps / total)
            surviving.append(OfferedFlow(flow.five_tuple, scaled))
        else:
            surviving.append(flow)

    return surviving, DefenceReport(metered_sources=metered, throttled_sources=throttled)


def per_link_bytes_per_sec(
    flows: list[OfferedFlow],
    *,
    concentrated: bool,
    target_link: int,
    n_links: int,
    link_capacity_bps: float,
) -> list[float]:
    """Per-egress-link offered load in bytes/sec, capped at link capacity.

    `concentrated` -> all surviving load on the target link (the crafted set
    collides there under the salt the attacker holds). Otherwise -> hash each
    flow under `DISPERSAL_SALT` via the real `ecmp_link` (invalidated set
    spreads ~uniformly)."""
    load_bps = [0.0] * n_links
    if concentrated:
        for flow in flows:
            load_bps[target_link] += flow.offered_bps
    else:
        for flow in flows:
            link = ecmp_link(flow.five_tuple, DISPERSAL_SALT, n_links)
            load_bps[link] += flow.offered_bps
    cap = link_capacity_bps
    return [min(bps, cap) / 8.0 for bps in load_bps]
