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
from datetime import datetime, timezone
from pathlib import Path

from os_ken.base.app_manager import OSKenApp
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.lib.packet import ether_types, ethernet, icmp, ipv4, packet, tcp, udp
from os_ken.ofproto import ofproto_v1_5

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from testbed.config import (  # noqa: E402
    EGRESS_PORTS,
    LEAF_DPID,
    LOCAL_IP_TO_PORT,
    LOCAL_PORTS,
    N_LINKS,
    REMOTE_IPS,
    ROTATION_INTERVAL_SECONDS,
    ROTATION_LOG_PATH,
    SALT_KIND,
)
from testbed.hash_core import ecmp_link  # noqa: E402
from testbed.salt import salt_source  # noqa: E402
from testbed.salt.rotation_log import append_event  # noqa: E402
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
        self._leaf_datapath = None
        self._ecmp_flows: set[FiveTuple] = set()

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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
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

        if five_tuple.dst_ip in LOCAL_IP_TO_PORT:
            out_port = LOCAL_IP_TO_PORT[five_tuple.dst_ip]
            LOG.info("5-tuple %s -> local port %d", five_tuple, out_port)
        elif five_tuple.dst_ip in REMOTE_IPS:
            link_index = ecmp_link(five_tuple, self.active_salt, N_LINKS)
            out_port = EGRESS_PORTS[link_index]
            self._ecmp_flows.add(five_tuple)
            LOG.info("5-tuple %s -> link %d (port %d)", five_tuple, link_index, out_port)
        else:
            return  # unknown destination, drop

        match = self._match_for(parser, five_tuple)
        actions = [parser.OFPActionOutput(out_port)]
        self._add_flow(datapath, priority=10, match=match, actions=actions)

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
    def _add_flow(datapath, priority, match, actions):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
