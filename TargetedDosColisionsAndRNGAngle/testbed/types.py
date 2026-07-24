"""Shared 5-tuple type and its canonical byte serialisation.

Serialisation order is load-bearing: P2's JS mirror must produce identical
bytes for identical field values, or hash_core's output will silently drift
between the Python testbed and the JS demo.
"""
from __future__ import annotations

import socket
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class FiveTuple:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: int  # IP protocol number, e.g. 6 = TCP, 17 = UDP

    def to_bytes(self) -> bytes:
        """Canonical byte encoding: src_ip, dst_ip (4 bytes each, network order),
        src_port, dst_port (2 bytes each, big-endian), proto (1 byte)."""
        return (
            socket.inet_aton(self.src_ip)
            + socket.inet_aton(self.dst_ip)
            + struct.pack("!HH", self.src_port, self.dst_port)
            + struct.pack("!B", self.proto)
        )
