"""AC-3, Q6: dice rolls via rejection sampling, avoiding modulo bias.

Ports the algorithm from the legacy `generate_numbers` (BC/bakalarska-praca-main/
quantum_rng/rng/utils/utils.py:115): draw `bits_needed = ceil(log2(sides))`-wide
windows of DRBG bits and reject any value >= sides, instead of `% sides`, which
would bias low outcomes whenever sides does not evenly divide 2**bits_needed.

Bytes are drawn from `keyed_drbg.output()` -- dice are quantum-seeded like every
other served value and stay working while the pool is `degraded` (this route is
ungated).

EPIC 5 Q2: every drawn byte (accepted *and* rejected) is returned alongside the
rolls, so `/dice` can echo the full, honest provenance of the roll. These are
DRBG output, same as every other served value -- raw QRNG bits are never served
(decision #2).
"""

from __future__ import annotations

import math

from qeaas.errors import ApiError
from qeaas.keyed_drbg import output

CAP_DRAWS_PER_ROLL = 64


def roll(sides: int, count: int) -> tuple[list[int], bytes]:
    bits_needed = math.ceil(math.log2(sides))
    rolls: list[int] = []
    drawn = bytearray()
    draws = 0
    max_draws = count * CAP_DRAWS_PER_ROLL

    while len(rolls) < count and draws < max_draws:
        (byte,) = output(1)
        drawn.append(byte)
        draws += 1
        value = byte >> (8 - bits_needed)
        if value < sides:
            rolls.append(value + 1)

    if len(rolls) < count:
        raise ApiError(500, "dice_sampling_failed")

    return rolls, bytes(drawn)
