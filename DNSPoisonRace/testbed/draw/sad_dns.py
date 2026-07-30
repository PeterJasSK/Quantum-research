"""SAD-DNS port-leak knob (epic §3.5, OQ-4).

Pure, stateless, dependency-free -- no `Draw` import, no `kind` awareness --
so P4/P5's effective-bits axis can import this without pulling in
`sources.py`'s QRNG/HTTP dependency.
"""
from __future__ import annotations


def sad_dns_leak(port_bits: int, k: int) -> int:
    """Effective port-bit count once an off-path attacker knows `k` bits of
    the port via the SAD-DNS side channel. Clamped at zero -- `k` exceeding
    `port_bits` never goes negative."""
    return max(0, port_bits - k)


def effective_bits(txid_bits: int, port_bits: int, k: int) -> int:
    """Total effective guess-space bits: full TXID entropy plus whatever port
    entropy SAD-DNS hasn't leaked. The single number P4/P5's sweeps key on."""
    return txid_bits + sad_dns_leak(port_bits, k)
