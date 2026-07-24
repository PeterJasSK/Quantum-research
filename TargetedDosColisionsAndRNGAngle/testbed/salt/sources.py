"""Frozen salt-source interface (epic ss3.5 / ss4, AC-2): `prng` | `csprng` |
`qrng`, all feeding the same `hash_core.ecmp_link` unchanged. Dependency-free
except the QRNG client's HTTP call."""
from __future__ import annotations

import binascii
import random
import secrets
from dataclasses import dataclass
from typing import Literal

from testbed.config import PRNG_SEED, QEAAS_API_KEY, QEAAS_BASE_URL, SALT_SIZE

from .qrng_client import QRNGClient

SaltKind = Literal["prng", "csprng", "qrng"]

# Module-level weak PRNG state (OQ-2): stateful sequential draws from
# `random.Random(PRNG_SEED)`, reseeded only if `PRNG_SEED` changes. This is
# the deliberately-reconstructable source -- P3's brute-force target.
_prng_rng: random.Random | None = None
_prng_seed: int | None = None
_prng_draw_index: int = 0


@dataclass(frozen=True)
class SaltProvenance:
    """Source-tagged provenance (epic s4). Fields populated depend on `kind`:
    `prng` -> seed/draw_index; `csprng`/`qrng` -> source_note or the Q-EaaS
    record. Always populated so P5/P6 can tag every run honestly."""

    kind: SaltKind
    byte_count: int
    source_note: str | None = None
    seed: int | None = None
    draw_index: int | None = None
    request_id: str | None = None
    entropy_epoch: int | None = None
    timestamp: str | None = None
    receipt: str | None = None
    endpoint: str | None = None


@dataclass(frozen=True)
class SaltResult:
    salt: bytes
    kind: SaltKind
    provenance: SaltProvenance


def salt_source(kind: SaltKind, *, size: int = SALT_SIZE) -> SaltResult:
    """Mint `size` bytes of salt from the named source, with provenance."""
    if kind == "prng":
        return _prng_source(size)
    if kind == "csprng":
        return _csprng_source(size)
    if kind == "qrng":
        return _qrng_source(size)
    raise ValueError(f"unknown salt kind: {kind!r}")


def _prng_source(size: int) -> SaltResult:
    global _prng_rng, _prng_seed, _prng_draw_index
    if _prng_rng is None or _prng_seed != PRNG_SEED:
        _prng_rng = random.Random(PRNG_SEED)
        _prng_seed = PRNG_SEED
        _prng_draw_index = 0

    salt = _prng_rng.randbytes(size)
    draw_index = _prng_draw_index
    _prng_draw_index += 1

    return SaltResult(
        salt=salt,
        kind="prng",
        provenance=SaltProvenance(
            kind="prng",
            byte_count=size,
            seed=PRNG_SEED,
            draw_index=draw_index,
        ),
    )


def _csprng_source(size: int) -> SaltResult:
    salt = secrets.token_bytes(size)
    return SaltResult(
        salt=salt,
        kind="csprng",
        provenance=SaltProvenance(
            kind="csprng",
            byte_count=size,
            source_note="secrets.token_bytes",
        ),
    )


def _qrng_source(size: int) -> SaltResult:
    if not QEAAS_API_KEY:
        raise RuntimeError("QEAAS_API_KEY is not set -- required for the qrng salt source")

    client = QRNGClient(QEAAS_BASE_URL, QEAAS_API_KEY)
    response = client.fetch(size=size, fmt="hex")
    salt = binascii.unhexlify(response.data)

    return SaltResult(
        salt=salt,
        kind="qrng",
        provenance=SaltProvenance(
            kind="qrng",
            byte_count=size,
            request_id=response.request_id,
            entropy_epoch=response.entropy_epoch,
            timestamp=response.timestamp,
            receipt=response.receipt,
            endpoint=f"{QEAAS_BASE_URL}/v1/random/bytes",
        ),
    )
