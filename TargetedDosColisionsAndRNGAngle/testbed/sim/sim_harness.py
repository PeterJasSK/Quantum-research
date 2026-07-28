"""Per-cell flow-level driver (plan-10 §2) -- the root-free, deterministic
replacement for the deleted Mininet `experiments/harness.py`.

For each `ExperimentCell` (imported unchanged from `experiments/matrix.py`):
1. mint the salt schedule with the *real* `salt_source` and log every event
   with the *real* `rotation_log` writer (so provenance/handoff is
   byte-identical to the live controller's);
2. resolve the attacker's salt for real -- `full` uses the logged salt,
   `partial` runs the *real* `SeedBruteForcer` (real CPU, real elapsed),
   `blind` gets none;
3. craft for real with the *real* `CollisionCrafter`;
4. drive the flow-level transport model (`transport.py`) over the run;
5. feed the *real* `MetricsCollector` the per-poll samples, which writes the
   per-poll CSV + `*.summary.csv` via the *real* `CsvWriter`.

The only new mechanism is the transport model; the hash, crafter, seed
brute-forcer, salt sources, defence policy, and metrics collector are all
imported and run unchanged (epic §3.5).
"""
from __future__ import annotations

import datetime
import json
import random
from dataclasses import dataclass
from pathlib import Path

from testbed import config
from testbed.analysis.rotation_threshold import analytical_t_bf
from testbed.attacker.collision import CollisionCrafter
from testbed.attacker.flows import random_five_tuples
from testbed.attacker.knowledge import resolve_salt
from testbed.attacker.oracle import LocalOracle
from testbed.controller.defences import DefencePolicy
from testbed.experiments.matrix import ExperimentCell
from testbed.hash_core import ecmp_link
from testbed.metrics.collector import MetricsCollector
from testbed.metrics.csv_writer import CsvWriter
from testbed.metrics.run_context import RunContext
from testbed.salt.rotation_log import append_event
from testbed.salt.sources import SaltResult, salt_source
from testbed.sim import transport
from testbed.sim.victim_model import VictimModel
from testbed.types import FiveTuple

_VICTIM_IP = config.HOSTS["victim"]["ip"]
_PROTO = 6
_DST_PORT = 80
# Twelve probes at N_LINKS=4 -> ~4^-12 (~6e-8) false-positive rate per
# candidate seed, so the brute-force recovers the *true* anchor seed before
# any probe-equivalent false positive over the ~60k-seed search to it.
_PROBES = [
    FiveTuple(src_ip="10.0.0.1", dst_ip=_VICTIM_IP, src_port=port, dst_port=_DST_PORT, proto=_PROTO)
    for port in range(50000, 50012)
]

# Memoise the (identical) exp5 / weak-PRNG-anchor reconstruction so the sweep
# does not repeat the same brute-force seven times.
_RECON_MEMO: dict[tuple[bytes, int, int], object] = {}


@dataclass(frozen=True)
class CellResult:
    cell: ExperimentCell
    run_record: dict | None
    summary: dict | None
    passed: bool | None  # None = no PASS/FAIL classification (exp4d/exp5)
    reason: str


def _iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).isoformat()


def _weak_prng_anchor_salt() -> bytes:
    """The weak-PRNG salt the partial attacker reconstructs (plan-10 OQ10-1
    decision). Draw 0 of `random.Random(SIM_RECON_TARGET_SEED)` -- mirrors
    `salt.sources._prng_source`'s primitive exactly (this is the attacker's
    *target* salt, i.e. test input; the mechanism under test is `ecmp_link`
    via the oracle, which is untouched). The seed sits mid-space so the real
    brute-force does enough work for a stable per-attempt `t_try`."""
    return random.Random(config.SIM_RECON_TARGET_SEED).randbytes(config.SALT_SIZE)


def _mint_schedule(cell: ExperimentCell, log_path: Path) -> tuple[list[SaltResult], dict | None]:
    """Mint the salt(s) for the run with the real source and log each event.
    Returns the minted `SaltResult`s (one per epoch) and the first qrng
    provenance (if any) for the replay export."""
    if log_path.exists():
        log_path.unlink()  # idempotent re-run
    interval = cell.rotation_interval
    if interval and interval > 0:
        n_epochs = int(config.RUN_DURATION_SECONDS / interval) + 1
        epoch_starts = [i * interval for i in range(n_epochs)]
    else:
        epoch_starts = [0.0]

    results: list[SaltResult] = []
    provenance: dict | None = None
    prev = b""
    for t0 in epoch_starts:
        res = salt_source(cell.salt_kind)  # real mint (qrng -> live draw)
        append_event(
            log_path,
            timestamp=_iso(t0),
            old_salt=prev,
            new_salt=res.salt,
            interval=interval,
            kind=cell.salt_kind,
        )
        prev = res.salt
        results.append(res)
        if cell.salt_kind == "qrng" and provenance is None:
            p = res.provenance
            provenance = {
                "request_id": p.request_id,
                "entropy_epoch": p.entropy_epoch,
                "timestamp": p.timestamp,
                "size": p.byte_count,
                "endpoint": p.endpoint,
                "receipt": p.receipt,
            }
    return results, provenance


def _reconstruct(cell: ExperimentCell, first_scheduled_salt: bytes):
    """Run the real reconstruction for the cell's knowledge level. Returns a
    `Reconstruction`."""
    if cell.knowledge_level == "full":
        return resolve_salt("full", known_salt=first_scheduled_salt)
    if cell.knowledge_level == "partial":
        # Weak-PRNG anchor for exp5 and any prng-salted partial cell (the only
        # regime where reconstruction is possible); the real csprng/qrng salt
        # for the defended partial cells (brute-force honestly fails).
        if cell.experiment == "exp5" or cell.salt_kind == "prng":
            oracle_salt = _weak_prng_anchor_salt()
        else:
            oracle_salt = first_scheduled_salt
        bits = config.PRNG_SEED_SPACE_BITS
        memo_key = (oracle_salt, bits, 1)
        if memo_key in _RECON_MEMO:
            return _RECON_MEMO[memo_key]
        result = resolve_salt(
            "partial",
            oracle=LocalOracle(oracle_salt, config.N_LINKS),
            probes=_PROBES,
            seed_space_bits=bits,
            draw_window=1,
            n_links=config.N_LINKS,
        )
        _RECON_MEMO[memo_key] = result
        return result
    return resolve_salt("blind")


def _build_offered_flows(cell: ExperimentCell, craft_salt: bytes | None) -> list[transport.OfferedFlow]:
    """Build the attacker's sustained offered flows at the stated operating
    point (plan-10 §3). Precision crafts PER SOURCE (the crafter iterates
    src_ip outer, so one craft(count) call would pile all flows on the first
    source); volumetric is one high-rate source; blind / failed-reconstruction
    uses uncrafted tuples that disperse."""
    if cell.attack_mode is None:
        return []  # exp4d clean background: no attacker

    per_flow_bps = config.PRECISION_PER_FLOW_PPS * config.PACKET_SIZE_BYTES * 8
    volumetric_bps = config.VOLUMETRIC_PPS * config.PACKET_SIZE_BYTES * 8

    if craft_salt is None:
        # blind, or a partial reconstruction that failed -> uncrafted tuples.
        count = config.PRECISION_FLOWS_PER_SOURCE * len(config.ATTACK_SOURCE_IPS)
        tuples = random_five_tuples(count, dst_ip=_VICTIM_IP, proto=_PROTO)
        return [transport.OfferedFlow(ft, per_flow_bps) for ft in tuples]

    if cell.attack_mode == "volumetric":
        crafter = CollisionCrafter(salt=craft_salt, target_link=cell.target_link, n_links=config.N_LINKS)
        crafted = crafter.craft(
            1,
            dst_ip=_VICTIM_IP,
            proto=_PROTO,
            src_ip_pool=[config.ATTACK_SOURCE_IPS[0]],
            src_port_range=range(1024, 65535),
            dst_port=_DST_PORT,
        )
        return [transport.OfferedFlow(ft, volumetric_bps) for ft in crafted]

    # precision: craft per source so the load spreads across compliant sources.
    crafter = CollisionCrafter(salt=craft_salt, target_link=cell.target_link, n_links=config.N_LINKS)
    flows: list[transport.OfferedFlow] = []
    for src_ip in config.ATTACK_SOURCE_IPS:
        crafted = crafter.craft(
            config.PRECISION_FLOWS_PER_SOURCE,
            dst_ip=_VICTIM_IP,
            proto=_PROTO,
            src_ip_pool=[src_ip],
            src_port_range=range(1024, 65535),
            dst_port=_DST_PORT,
        )
        flows.extend(transport.OfferedFlow(ft, per_flow_bps) for ft in crafted)
    return flows


def _concentration_gate(cell: ExperimentCell, *, recon_found: bool, t_bf: float):
    """Return `is_concentrated(t) -> bool`: whether the attacker's crafted set
    collides on the target link at time `t` (plan-10 §1/§2 acquisition model).

    - full + no rotation: the static salt is known -> always concentrated.
    - full + rotation (csprng/qrng): the salt is unpredictable and re-minted
      every interval -> the attacker can never hold the current salt -> never.
    - partial: only once reconstruction completes (`t >= t_bf`) AND the
      defender rotates slower than reconstruction (`interval > t_bf`, or no
      rotation). A failed reconstruction (csprng/qrng) never concentrates.
    - blind / clean-background: never.
    """
    level = cell.knowledge_level
    if cell.attack_mode is None or level == "blind":
        return lambda t: False
    if level == "full":
        if cell.rotation_interval and cell.rotation_interval > 0:
            return lambda t: False
        return lambda t: True
    # partial
    if not recon_found:
        return lambda t: False
    reconstructs_in_time = (not cell.rotation_interval) or cell.rotation_interval > t_bf
    if not reconstructs_in_time:
        return lambda t: False
    return lambda t: t >= t_bf


def run_cell(cell: ExperimentCell) -> CellResult:
    csv_path = Path(cell.csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".csv", ".summary.csv", ".record.json"):
        p = csv_path.with_suffix(suffix)
        if p.exists():
            p.unlink()

    # 1. Salt schedule + provenance (qrng may be unavailable -> skip).
    try:
        schedule, qrng_provenance = _mint_schedule(cell, csv_path.with_suffix(".rotation_events.jsonl"))
    except Exception as exc:  # noqa: BLE001 -- any mint failure is a skip, never a fake
        return CellResult(
            cell=cell,
            run_record=None,
            summary=None,
            passed=None,
            reason=f"skipped-with-reason: salt source {cell.salt_kind!r} unavailable ({exc})",
        )

    first_salt = schedule[0].salt

    # 2. Resolve the attacker's salt for real. 3. Craft for real.
    reconstruction = _reconstruct(cell, first_salt)
    recon_found = reconstruction.salt is not None
    craft_salt: bytes | None
    if cell.attack_mode is None or cell.knowledge_level == "blind":
        craft_salt = None
    elif recon_found:
        craft_salt = reconstruction.salt
    else:
        craft_salt = None  # partial reconstruction failed -> disperse like blind
    offered = _build_offered_flows(cell, craft_salt)

    # Internal-consistency guard (plan-10 MV step 8): when the attacker holds
    # the salt, the crafted set must genuinely collide on the target link
    # under the real hash -- otherwise "concentrated" would be a lie.
    if craft_salt is not None and cell.attack_mode == "precision":
        for flow in offered:
            assert ecmp_link(flow.five_tuple, craft_salt, config.N_LINKS) == cell.target_link, (
                "crafted flow does not collide on the target link under the real hash"
            )

    # Analytical reconstruction time (weak-PRNG anchor) -> concentration gate.
    t_bf = 0.0
    if recon_found and reconstruction.attempts > 0:
        t_try = reconstruction.elapsed_seconds / reconstruction.attempts
        t_bf = analytical_t_bf(config.PRNG_SEED_SPACE_BITS, t_try)
    is_concentrated = _concentration_gate(cell, recon_found=recon_found, t_bf=t_bf)

    # 4/5. Drive transport + feed the real collector.
    policy = DefencePolicy(
        throttle_max_connections=config.THROTTLE_MAX_CONNECTIONS,
        throttle_window_seconds=config.THROTTLE_WINDOW_SECONDS,
    )
    surviving, defence = transport.apply_defences(
        offered,
        enabled=cell.defences_enabled,
        rate_limit_kbps=config.RATE_LIMIT_KBPS,
        policy=policy,
        now=0.0,
    )

    victim = VictimModel(
        link_capacity_mbps=config.LINK_CAPACITY_MBPS,
        victim_demand_mbps=config.VICTIM_DEMAND_MBPS,
    )
    run_context = RunContext(
        knowledge_level=cell.knowledge_level,
        attack_mode=cell.attack_mode or "na",
        csv_path=str(csv_path),
        start_time=0.0,
    )
    collector = MetricsCollector(
        egress_ports=config.EGRESS_PORTS,
        target_link=cell.target_link,
        link_capacity_mbps=config.LINK_CAPACITY_MBPS,
        saturation_utilisation=config.SATURATION_UTILISATION,
        run_context=run_context,
        salt_source_tag=cell.salt_kind,
        rotation_interval=cell.rotation_interval,
        csv_writer=CsvWriter(str(csv_path), config.N_LINKS),
        victim_mbps_reader=victim.current_mbps,
    )

    poll = config.PORT_STATS_POLL_INTERVAL_SECONDS
    n_polls = int(round(config.RUN_DURATION_SECONDS / poll))
    capacity_bps = config.LINK_CAPACITY_MBPS * 1_000_000
    cum_bytes = {port: 0.0 for port in config.EGRESS_PORTS}
    cum_pkts = {port: 0.0 for port in config.EGRESS_PORTS}

    for i in range(n_polls + 1):
        t = i * poll
        link_bytes_per_sec = transport.per_link_bytes_per_sec(
            surviving,
            concentrated=is_concentrated(t),
            target_link=cell.target_link,
            n_links=config.N_LINKS,
            link_capacity_bps=capacity_bps,
        )
        dt = poll if i > 0 else 0.0
        samples: list[tuple[int, int, int, float]] = []
        for li, port in enumerate(config.EGRESS_PORTS):
            cum_bytes[port] += link_bytes_per_sec[li] * dt
            cum_pkts[port] += (link_bytes_per_sec[li] * dt) / config.PACKET_SIZE_BYTES
            samples.append((port, int(cum_bytes[port]), int(cum_pkts[port]), t))
        target_attacker_mbps = link_bytes_per_sec[cell.target_link] * 8 / 1_000_000
        victim.update(target_attacker_mbps)
        collector.on_port_stats(samples, tracked_flows=len(surviving))

    # Run record (graphs.py reads `reconstruction` for the Exp 5 t_try anchor).
    run_record = {
        "level": cell.knowledge_level,
        "mode": cell.attack_mode or "na",
        "target_link": cell.target_link,
        "salt_source": cell.salt_kind,
        "sources_used": sorted({f.src_ip for f in offered}),
        "flows_offered": len(offered),
        "flows_surviving": len(surviving),
        "defence_fired": defence.fired,
        "metered_sources": list(defence.metered_sources),
        "throttled_sources": list(defence.throttled_sources),
        "reconstruction": {
            "attempts": reconstruction.attempts,
            "elapsed_seconds": reconstruction.elapsed_seconds,
        },
    }
    if qrng_provenance is not None:
        run_record["qrng_provenance"] = qrng_provenance
    csv_path.with_suffix(".record.json").write_text(json.dumps(run_record, indent=2))

    summary = {
        "saturated": collector.saturated,
        "min_victim_mbps": collector.min_victim_mbps,
        "final_jains_index": collector.final_jains_index,
        "time_to_saturation_s": collector.time_to_saturation_s,
    }

    if cell.expected_saturated is None:
        passed: bool | None = None
        reason = "data-only (no PASS/FAIL expectation)"
    else:
        passed = collector.saturated == cell.expected_saturated
        reason = (
            f"saturated={collector.saturated} expected={cell.expected_saturated}; "
            f"min_victim={collector.min_victim_mbps}; defence_fired={defence.fired}"
        )

    return CellResult(cell=cell, run_record=run_record, summary=summary, passed=passed, reason=reason)
