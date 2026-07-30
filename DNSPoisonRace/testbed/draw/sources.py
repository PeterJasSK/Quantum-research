"""Frozen draw-source interface (epic §3.5/§4, AC-2). `fixed` | `prng` |
`csprng` | `qrng`, all returning the same P1-frozen `Draw` shape so
`sim/race.py` stays source-agnostic.

`qrng` and `csprng` draw exactly `txid_bits + port_bits` bits from their
respective full-entropy source and split identically (high bits -> txid, low
bits -> port, matching `Draw`'s canonical field order) -- this is what keeps
the honest null result honest (epic §3.2): neither arm gets an entropy
advantage over the other, only `DrawProvenance.detail`'s receipt differs.
"""
from __future__ import annotations

import binascii
import random
import secrets
from typing import Literal

from testbed import config
from testbed.types import Draw, DrawProvenance

from .qrng_client import QRNGClient

DrawKind = Literal["fixed", "prng", "csprng", "qrng"]

# Module-level weak PRNG state (epic §9 P2, AC-2.3): stateful sequential
# draws from `random.Random(PRNG_SEED)`, reseeded only if `PRNG_SEED`
# changes -- mirrors the ECMP twin's `_prng_source` exactly. Two callers in
# the same process share this sequence state; reseed `PRNG_SEED` between arms
# if independent draws are required (P3/P4/P5).
_prng_rng: random.Random | None = None
_prng_seed: int | None = None
_prng_draw_index: int = 0


def draw_source(
    kind: DrawKind,
    *,
    txid_bits: int = config.TXID_BITS,
    port_bits: int = config.PORT_BITS,
) -> Draw:
    """Mint one `Draw(txid, port, provenance)` from the named source."""
    if kind == "fixed":
        return _fixed_draw(txid_bits)
    if kind == "prng":
        return _prng_draw(txid_bits, port_bits)
    if kind == "csprng":
        return _csprng_draw(txid_bits, port_bits)
    if kind == "qrng":
        return _qrng_draw(txid_bits, port_bits)
    raise ValueError(f"unknown draw kind: {kind!r}")


def _split_high_low(value: int, low_bits: int) -> tuple[int, int]:
    """Split `value` into (high bits, low `low_bits` bits) -- the canonical
    txid/port split for any source that draws one combined-width integer."""
    return value >> low_bits, value & ((1 << low_bits) - 1)


def _fixed_draw(txid_bits: int) -> Draw:
    """Pre-2008 deployment model (epic §6a): TXID is randomised, port is
    pinned to `config.FIXED_PORT` -- no port entropy at all."""
    txid = secrets.randbits(txid_bits)
    return Draw(
        txid=txid,
        port=config.FIXED_PORT,
        provenance=DrawProvenance(
            kind="fixed",
            detail={
                "txid_source": "secrets.randbits",
                "port_source": "fixed",
                "fixed_port": str(config.FIXED_PORT),
            },
        ),
    )


def _prng_draw(txid_bits: int, port_bits: int) -> Draw:
    """Deliberately weak, reproducible source (epic §9 P2, AC-2.3): the
    source P3's brute-force / birthday-amplified attacker is expected to
    actually beat."""
    global _prng_rng, _prng_seed, _prng_draw_index
    if _prng_rng is None or _prng_seed != config.PRNG_SEED:
        _prng_rng = random.Random(config.PRNG_SEED)
        _prng_seed = config.PRNG_SEED
        _prng_draw_index = 0

    value = _prng_rng.getrandbits(txid_bits + port_bits)
    txid, port = _split_high_low(value, port_bits)
    draw_index = _prng_draw_index
    _prng_draw_index += 1

    return Draw(
        txid=txid,
        port=port,
        provenance=DrawProvenance(
            kind="prng",
            detail={"seed": str(config.PRNG_SEED), "draw_index": str(draw_index)},
        ),
    )


def _csprng_draw(txid_bits: int, port_bits: int) -> Draw:
    """Full-entropy source (epic §3.2): must match `qrng`'s bit-width and
    quality exactly so P5's sweep shows no spurious advantage either way."""
    txid = secrets.randbits(txid_bits)
    port = secrets.randbits(port_bits)
    return Draw(
        txid=txid,
        port=port,
        provenance=DrawProvenance(
            kind="csprng",
            detail={"source": "secrets.randbits"},
        ),
    )


def _qrng_draw(txid_bits: int, port_bits: int) -> Draw:
    """Full-entropy source drawn from the hosted Q-EaaS service (epic
    Appendix A.1/A.2) -- no new QC runs, just the existing
    `/v1/random/bytes` endpoint."""
    if not config.QEAAS_API_KEY:
        raise RuntimeError("QEAAS_API_KEY is not set -- required for the qrng draw source")

    total_bits = txid_bits + port_bits
    byte_count = (total_bits + 7) // 8

    client = QRNGClient(config.QEAAS_BASE_URL, config.QEAAS_API_KEY)
    response = client.fetch(size=byte_count, fmt="hex")
    raw = binascii.unhexlify(response.data)
    value = int.from_bytes(raw, "big") >> (byte_count * 8 - total_bits)
    txid, port = _split_high_low(value, port_bits)

    return Draw(
        txid=txid,
        port=port,
        provenance=DrawProvenance(
            kind="qrng",
            detail={
                "request_id": response.request_id,
                "entropy_epoch": str(response.entropy_epoch),
                "timestamp": response.timestamp,
                "receipt": response.receipt or "",
                "endpoint": f"{config.QEAAS_BASE_URL}/v1/random/bytes",
            },
        ),
    )
