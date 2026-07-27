"""Controller-side ECMP (decision D1).

s1 (leaf, dpid=LEAF_DPID) is the only switch this hashes: on packet-in for
IP traffic bound for a spine-attached host, it computes
hash(5-tuple + salt) mod N via the shared hash_core and installs an
exact-match flow pinning that 5-tuple to the chosen egress port. IP traffic
bound for a leaf-local host (attacker/bg) is delivered directly, no hashing
-- multipath only exists between s1 and the spine. ARP/broadcast is flooded
so hosts can resolve each other at all.

s2 (spine) needs no ECMP logic of its own -- it gets a single ``NORMAL``
flow so OVS's own L2 learning delivers everything (this is the only
practical way to make the return path work without duplicating a learning
switch here).

Uses os_ken (the maintained fork of Ryu -- see requirements.txt for why
plain `ryu` isn't used). OSKenApp plays the same role as ryu.base.app_manager.RyuApp.
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from os_ken.base.app_manager import OSKenApp
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.lib.packet import arp, ether_types, ethernet, icmp, ipv4, packet, tcp, udp
from os_ken.ofproto import ofproto_v1_5

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.config import (  # noqa: E402
    DEFENCES_ENABLED,
    EGRESS_PORTS,
    FABRIC_MODE,
    FATTREE_K,
    LEAF_DPID,
    LINK_CAPACITY_MBPS,
    LOCAL_IP_TO_PORT,
    LOCAL_PORTS,
    METRICS_CSV_PATH,
    N_LINKS,
    PORT_STATS_POLL_INTERVAL_SECONDS,
    RATE_LIMIT_BURST_KB,
    RATE_LIMIT_KBPS,
    REMOTE_IPS,
    ROTATION_INTERVAL_SECONDS,
    ROTATION_LOG_PATH,
    SALT_KIND,
    SATURATION_UTILISATION,
    TARGET_LINK,
    THROTTLE_ACTION,
    THROTTLE_MAX_CONNECTIONS,
    THROTTLE_WINDOW_SECONDS,
    VICTIM_THROUGHPUT_PATH,
)
from testbed.controller.defences import DefencePolicy  # noqa: E402
from testbed.hash_core import ecmp_link  # noqa: E402
from testbed.metrics import MetricsCollector, RunContext  # noqa: E402
from testbed.metrics.csv_writer import CsvWriter  # noqa: E402
from testbed.metrics.victim_throughput import latest_mbps  # noqa: E402
from testbed.salt import salt_source  # noqa: E402
from testbed.salt.rotation_log import append_event  # noqa: E402
from testbed.topology.fabric import build_fattree, fabric_ports, fabric_salts, next_hop  # noqa: E402
from testbed.types import FiveTuple  # noqa: E402

LOG = logging.getLogger(__name__)

# Bundle commit timeout (rotate_salt gives up on the atomic path and falls
# back to delete-and-lazy-re-resolve if no reply arrives -- see OQ-1).
_BUNDLE_COMMIT_TIMEOUT_SECONDS = 2.0


class ECMPController(OSKenApp):
    OFP_VERSIONS = [ofproto_v1_5.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.salt_kind = SALT_KIND
        self.active_salt = salt_source(self.salt_kind).salt  # rotatable (P2); static in P1

        # P5 OQ-1: log the initial minted salt as a rotation event
        # (old_salt=b"") so salt_handoff.py has one uniform "latest new_salt"
        # read for every cell, including prng-no-rotation.
        append_event(
            ROTATION_LOG_PATH,
            timestamp=datetime.now(timezone.utc).isoformat(),
            old_salt=b"",
            new_salt=self.active_salt,
            interval=ROTATION_INTERVAL_SECONDS,
            kind=self.salt_kind,
        )

        self._leaf_datapath = None
        self._ecmp_flows: set[FiveTuple] = set()

        # Plan-8 fabric mode (AC-2): every fat-tree switch hashes its own
        # upward fan-out under its own salt, gated so the OFF path above
        # stays byte-for-byte P1-P5 behaviour. Rotation stays single-leaf-only
        # (no attacker in this scenario -- see plan-8 Codebase integration).
        self._fabric = build_fattree(FATTREE_K) if FABRIC_MODE else None
        self._fabric_ports = fabric_ports(self._fabric) if FABRIC_MODE else None
        self._fabric_salts = fabric_salts(self.salt_kind, self._fabric) if FABRIC_MODE else None
        self._switch_id_by_dpid = (
            {i + 1: switch_id for i, switch_id in enumerate(self._fabric.all_switches)}
            if FABRIC_MODE
            else None
        )
        self._fabric_datapaths: dict[int, object] = {}
        self._fabric_flows: dict[int, set[FiveTuple]] = {}

        # P4 (AC-1/AC-2): defences are gated on DEFENCES_ENABLED so the OFF
        # path stays byte-for-byte today's behaviour. Meter/drop-flow
        # install state lives here (live-datapath bookkeeping); the
        # counting/id-assignment policy lives in DefencePolicy.
        self.defence_policy = (
            DefencePolicy(
                throttle_max_connections=THROTTLE_MAX_CONNECTIONS,
                throttle_window_seconds=THROTTLE_WINDOW_SECONDS,
            )
            if DEFENCES_ENABLED
            else None
        )
        self._meters_installed: set[str] = set()
        self._throttle_drops_installed: set[str] = set()
        self._metrics_collector: MetricsCollector | None = None

        # OQ-1: try an OpenFlow bundle first (true atomic); fall back to
        # delete-and-lazy-re-resolve if the OVS/OF1.5 build rejects bundles.
        # `None` = not yet tried; set to False the first time a bundle fails.
        self._bundle_supported: bool | None = None
        self._bundle_id_counter = 0
        self._bundle_waiters: dict[int, hub.Event] = {}
        self._bundle_results: dict[int, bool] = {}

        if ROTATION_INTERVAL_SECONDS > 0:
            hub.spawn(self._rotation_loop)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if FABRIC_MODE:
            # Every fat-tree switch is a hasher -- no blanket NORMAL shortcut;
            # all get table-miss->CONTROLLER (plan-8 AC-2).
            self._fabric_datapaths[datapath.id] = datapath
            match = parser.OFPMatch()
            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
            self._add_flow(datapath, priority=0, match=match, actions=actions)
            return

        if datapath.id != LEAF_DPID:
            # Spine (and anything else): plain L2 bridge, no controller
            # involvement needed -- this is what makes the return path and
            # ARP delivery to the spine-attached victim work.
            match = parser.OFPMatch()
            actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self._add_flow(datapath, priority=0, match=match, actions=actions)
            return

        self._leaf_datapath = datapath

        # Leaf: table-miss sends unmatched packets to the controller.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, priority=0, match=match, actions=actions)

        if DEFENCES_ENABLED and self._metrics_collector is None:
            self._metrics_collector = self._build_metrics_collector()
            hub.spawn(self._port_stats_poll_loop)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath

        if FABRIC_MODE:
            self._fabric_packet_in(msg, datapath)
            return

        if datapath.id != LEAF_DPID:
            return  # spine handles itself via NORMAL, shouldn't punt here

        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        if eth.ethertype != ether_types.ETH_TYPE_IP:
            # ARP and anything else non-IP: flood so hosts can resolve
            # each other. No flow installed -- broadcast/ARP is infrequent
            # enough that punting every time is fine at this scale.
            #
            # The N leaf<->spine links are a multigraph (parallel edges
            # between the same two switches) -- naive FLOOD-out-every-port
            # loops (frame bounces s1<->s2 across the other N-1 links
            # forever, no STP here). So: local-origin broadcast goes to
            # the other local ports *plus exactly one* designated uplink;
            # spine-origin broadcast only goes to local ports, never back
            # out to the spine.
            if in_port in LOCAL_PORTS:
                out_ports = [p for p in LOCAL_PORTS if p != in_port] + [EGRESS_PORTS[0]]
            else:
                out_ports = [p for p in LOCAL_PORTS if p != in_port]
            if out_ports:
                self._output_to(datapath, msg, in_port, out_ports)
            return

        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is None:
            return

        five_tuple = self._extract_five_tuple(pkt, ip)
        if five_tuple is None:
            return

        priority = 10
        meter_id = None

        if five_tuple.dst_ip in LOCAL_IP_TO_PORT:
            out_port = LOCAL_IP_TO_PORT[five_tuple.dst_ip]
            LOG.info("5-tuple %s -> local port %d", five_tuple, out_port)
        elif five_tuple.dst_ip in REMOTE_IPS:
            if self.defence_policy is not None:
                decision = self.defence_policy.note_flow(five_tuple.src_ip, five_tuple, time.time())
                throttled = decision.over_limit or self.defence_policy.is_throttled(five_tuple.src_ip)
                if throttled:
                    self._install_throttle_drop(datapath, five_tuple.src_ip)
                    if THROTTLE_ACTION == "drop":
                        # AC-2: subsequent new flows from this source are
                        # dropped -- no ECMP flow, no packet-out this time either.
                        return
                    priority = 1  # "deprioritise": still ECMP-routed, but loses to normal priority-10 flows
                meter_id = self._ensure_meter(datapath, five_tuple.src_ip)

            link_index = ecmp_link(five_tuple, self.active_salt, N_LINKS)
            out_port = EGRESS_PORTS[link_index]
            self._ecmp_flows.add(five_tuple)
            LOG.info("5-tuple %s -> link %d (port %d)", five_tuple, link_index, out_port)
        else:
            return  # unknown destination, drop

        match = self._match_for(parser, five_tuple)
        actions = [parser.OFPActionOutput(out_port)]
        self._add_flow(datapath, priority=priority, match=match, actions=actions, meter_id=meter_id)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None,
        )
        datapath.send_msg(out)

    def _fabric_packet_in(self, msg, datapath) -> None:
        """Plan-8 AC-2: packet-in from any fabric dpid. Picks the next hop via
        the shared `fabric.next_hop()` (hashed upward under this switch's own
        salt, deterministic downward) and installs a pinning flow, same
        discipline as the single-leaf path but per-dpid.

        ARP/broadcast: routed deterministically along the same `next_hop()`
        path as a synthetic zero-port five-tuple rather than flooded -- a
        fat-tree is a multigraph of redundant paths, so naive multi-port
        flooding loops (plan-8 Risks: "Multi-switch L2/ARP in Mininet").
        Unresolvable destinations (unknown IP) are dropped, not flooded.
        """
        switch_id = self._switch_id_by_dpid.get(datapath.id)
        if switch_id is None:
            return

        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        install_flow = eth.ethertype == ether_types.ETH_TYPE_IP
        if install_flow:
            ip = pkt.get_protocol(ipv4.ipv4)
            if ip is None:
                return
            five_tuple = self._extract_five_tuple(pkt, ip)
        else:
            arp_pkt = pkt.get_protocol(arp.arp)
            if arp_pkt is None or arp_pkt.dst_ip not in self._fabric.ip_to_host:
                return
            five_tuple = FiveTuple(arp_pkt.src_ip, arp_pkt.dst_ip, 0, 0, 0)

        if five_tuple is None or five_tuple.dst_ip not in self._fabric.ip_to_host:
            return

        next_id = next_hop(self._fabric, self._fabric_salts, switch_id, five_tuple)
        out_port = self._fabric_ports[switch_id].get(next_id)
        if out_port is None:
            return

        actions = [parser.OFPActionOutput(out_port)]
        if install_flow:
            # ARP gets a one-off packet-out only (no flow) -- it is rare
            # enough to punt every time, and a five-tuple-shaped match would
            # over-match unrelated ARP traffic through the same in_port.
            self._add_flow(datapath, priority=10, match=self._match_for(parser, five_tuple), actions=actions)
            self._fabric_flows.setdefault(datapath.id, set()).add(five_tuple)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None,
        )
        datapath.send_msg(out)

    def _rotation_loop(self):
        """os_ken green-thread timer (OQ-5): rotate every `ROTATION_INTERVAL_SECONDS`,
        regardless of traffic (epic s8 Q2: per-time-interval)."""
        while True:
            hub.sleep(ROTATION_INTERVAL_SECONDS)
            self.rotate_salt()

    def rotate_salt(self) -> None:
        """Mint a fresh salt and atomically reinstall the tracked ECMP flows
        under it (AC-3, AC-4). Callable from the timer or manually (OQ-5)."""
        old_salt = self.active_salt
        new_salt = salt_source(self.salt_kind).salt

        datapath = self._leaf_datapath
        if datapath is not None and self._ecmp_flows:
            remapped = {
                five_tuple: EGRESS_PORTS[ecmp_link(five_tuple, new_salt, N_LINKS)]
                for five_tuple in self._ecmp_flows
            }
            rotated_atomically = False
            if self._bundle_supported is not False:
                rotated_atomically = self._rotate_via_bundle(datapath, remapped)
                if not rotated_atomically:
                    self._bundle_supported = False
                    LOG.info("rotate_salt: bundle unsupported, falling back to delete-and-re-resolve")
            if not rotated_atomically:
                self._rotate_via_delete_and_reresolve(datapath)

        self.active_salt = new_salt
        append_event(
            ROTATION_LOG_PATH,
            timestamp=datetime.now(timezone.utc).isoformat(),
            old_salt=old_salt,
            new_salt=new_salt,
            interval=ROTATION_INTERVAL_SECONDS,
            kind=self.salt_kind,
        )
        LOG.info(
            "rotate_salt: %s -> %s (kind=%s, mechanism=%s)",
            old_salt.hex(),
            new_salt.hex(),
            self.salt_kind,
            "bundle" if self._bundle_supported else "delete-and-re-resolve",
        )

    def _rotate_via_bundle(self, datapath, remapped: dict[FiveTuple, int]) -> bool:
        """Atomic swap via an OpenFlow bundle: DELETE the tracked ECMP flows +
        ADD their recomputed replacements, committed as one unit (OQ-1)."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self._bundle_id_counter += 1
        bundle_id = self._bundle_id_counter
        waiter = hub.Event()
        self._bundle_waiters[bundle_id] = waiter

        try:
            datapath.send_msg(
                parser.OFPBundleCtrlMsg(
                    datapath, bundle_id=bundle_id, type_=ofproto.OFPBCT_OPEN_REQUEST, flags=ofproto.OFPBF_ATOMIC
                )
            )
            for five_tuple, out_port in remapped.items():
                match = self._match_for(parser, five_tuple)
                delete_mod = parser.OFPFlowMod(
                    datapath=datapath,
                    command=ofproto.OFPFC_DELETE_STRICT,
                    priority=10,
                    match=match,
                    out_port=ofproto.OFPP_ANY,
                    out_group=ofproto.OFPG_ANY,
                )
                add_mod = parser.OFPFlowMod(
                    datapath=datapath,
                    command=ofproto.OFPFC_ADD,
                    priority=10,
                    match=match,
                    instructions=[
                        parser.OFPInstructionActions(
                            ofproto.OFPIT_APPLY_ACTIONS, [parser.OFPActionOutput(out_port)]
                        )
                    ],
                )
                for mod in (delete_mod, add_mod):
                    datapath.send_msg(
                        parser.OFPBundleAddMsg(datapath, bundle_id, ofproto.OFPBF_ATOMIC, mod, [])
                    )
            datapath.send_msg(
                parser.OFPBundleCtrlMsg(
                    datapath, bundle_id=bundle_id, type_=ofproto.OFPBCT_COMMIT_REQUEST, flags=ofproto.OFPBF_ATOMIC
                )
            )

            waiter.wait(timeout=_BUNDLE_COMMIT_TIMEOUT_SECONDS)
            success = self._bundle_results.pop(bundle_id, False)
        finally:
            self._bundle_waiters.pop(bundle_id, None)

        return success

    def _rotate_via_delete_and_reresolve(self, datapath) -> None:
        """Fallback (OQ-1): delete all tracked ECMP flows and clear the set; the
        next packet-in per 5-tuple lazily re-resolves under the new salt. Brief
        controller round-trip, no packet drop, no correctness gap."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        for five_tuple in self._ecmp_flows:
            match = self._match_for(parser, five_tuple)
            mod = parser.OFPFlowMod(
                datapath=datapath,
                command=ofproto.OFPFC_DELETE_STRICT,
                priority=10,
                match=match,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
            )
            datapath.send_msg(mod)
        self._ecmp_flows.clear()

    @staticmethod
    def _match_for(parser, five_tuple: FiveTuple):
        return parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=five_tuple.src_ip,
            ipv4_dst=five_tuple.dst_ip,
            ip_proto=five_tuple.proto,
        )

    @set_ev_cls(ofp_event.EventOFPBundleCtrlMsg, MAIN_DISPATCHER)
    def bundle_ctrl_handler(self, ev):
        msg = ev.msg
        if msg.type == msg.datapath.ofproto.OFPBCT_COMMIT_REPLY:
            self._bundle_results[msg.bundle_id] = True
            waiter = self._bundle_waiters.get(msg.bundle_id)
            if waiter is not None:
                waiter.set()

    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def error_msg_handler(self, ev):
        msg = ev.msg
        ofproto = msg.datapath.ofproto
        LOG.warning("OFPErrorMsg: type=%s code=%s", msg.type, msg.code)
        if msg.type == ofproto.OFPET_BUNDLE_FAILED:
            for bundle_id, waiter in list(self._bundle_waiters.items()):
                self._bundle_results[bundle_id] = False
                waiter.set()

    @staticmethod
    def _output_to(datapath, msg, in_port, out_ports):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        actions = [parser.OFPActionOutput(p) for p in out_ports]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None,
        )
        datapath.send_msg(out)

    @staticmethod
    def _extract_five_tuple(pkt: packet.Packet, ip: ipv4.ipv4) -> FiveTuple | None:
        tcp_hdr = pkt.get_protocol(tcp.tcp)
        if tcp_hdr is not None:
            return FiveTuple(ip.src, ip.dst, tcp_hdr.src_port, tcp_hdr.dst_port, ip.proto)
        udp_hdr = pkt.get_protocol(udp.udp)
        if udp_hdr is not None:
            return FiveTuple(ip.src, ip.dst, udp_hdr.src_port, udp_hdr.dst_port, ip.proto)
        icmp_hdr = pkt.get_protocol(icmp.icmp)
        if icmp_hdr is not None:
            # ICMP has no ports; use 0/0 so it still hashes deterministically.
            return FiveTuple(ip.src, ip.dst, 0, 0, ip.proto)
        return None

    @staticmethod
    def _add_flow(datapath, priority, match, actions, meter_id=None):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if meter_id is not None:
            inst.append(parser.OFPInstructionMeter(meter_id))
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    def _ensure_meter(self, datapath, src_ip: str) -> int:
        """AC-1: install a per-source `OFPMeterMod` once (idempotent via
        `_meters_installed`); return the stable meter id to reference from
        the flow's instructions."""
        meter_id = self.defence_policy.meter_id_for(src_ip)
        if src_ip not in self._meters_installed:
            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto
            band = parser.OFPMeterBandDrop(rate=RATE_LIMIT_KBPS, burst_size=RATE_LIMIT_BURST_KB)
            mod = parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,
                meter_id=meter_id,
                bands=[band],
            )
            datapath.send_msg(mod)
            self._meters_installed.add(src_ip)
        return meter_id

    def _install_throttle_drop(self, datapath, src_ip: str) -> None:
        """AC-2: priority-20 drop flow matching `src_ip`, so subsequent new
        flows from an over-limit source are dropped at the switch without
        reaching the controller again (default THROTTLE_ACTION="drop", OQ-5)."""
        if src_ip in self._throttle_drops_installed:
            return
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip)
        self._add_flow(datapath, priority=20, match=match, actions=[])
        self._throttle_drops_installed.add(src_ip)

    def _build_metrics_collector(self) -> MetricsCollector:
        run_context = RunContext.from_env()
        csv_writer = CsvWriter(run_context.csv_path, N_LINKS)
        return MetricsCollector(
            egress_ports=EGRESS_PORTS,
            target_link=TARGET_LINK,
            link_capacity_mbps=LINK_CAPACITY_MBPS,
            saturation_utilisation=SATURATION_UTILISATION,
            run_context=run_context,
            salt_source_tag=self.salt_kind,
            rotation_interval=ROTATION_INTERVAL_SECONDS,
            csv_writer=csv_writer,
            victim_mbps_reader=lambda: latest_mbps(VICTIM_THROUGHPUT_PATH),
        )

    def _port_stats_poll_loop(self):
        """Mirrors `_rotation_loop`'s `hub.spawn` pattern: poll port stats
        on a timer once the leaf datapath is up (AC-4/5/6/7)."""
        while True:
            hub.sleep(PORT_STATS_POLL_INTERVAL_SECONDS)
            self._request_port_stats()

    def _request_port_stats(self) -> None:
        datapath = self._leaf_datapath
        if datapath is None:
            return
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        datapath.send_msg(parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY))

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        if self._metrics_collector is None:
            return
        now = time.time()
        samples = [(stat.port_no, stat.tx_bytes, stat.tx_packets, now) for stat in ev.msg.body]
        self._metrics_collector.on_port_stats(samples, tracked_flows=len(self._ecmp_flows))
