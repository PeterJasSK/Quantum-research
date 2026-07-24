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
from pathlib import Path

from os_ken.base.app_manager import OSKenApp
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
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
    STATIC_SALT,
)
from testbed.hash_core import ecmp_link  # noqa: E402
from testbed.types import FiveTuple  # noqa: E402

LOG = logging.getLogger(__name__)


class ECMPController(OSKenApp):
    OFP_VERSIONS = [ofproto_v1_5.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_salt = STATIC_SALT  # static in P1; P2 makes this rotatable

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
            LOG.info("5-tuple %s -> link %d (port %d)", five_tuple, link_index, out_port)
        else:
            return  # unknown destination, drop

        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=five_tuple.src_ip,
            ipv4_dst=five_tuple.dst_ip,
            ip_proto=five_tuple.proto,
        )
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
