"""AC-2, AC-4, AC-5: single served-randomness choke point.

Raw QRNG bits are never served; every byte returned here is DRBG-derived via
`keyed_drbg.output()`. QRNG only seeds a standards DRBG -- it does not "defeat
quantum attackers" on its own.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from qeaas import db
from qeaas.keyed_drbg import output


def random_bytes(n: int) -> bytes:
    return output(n)


def issue_v1(size: int, fmt: str) -> dict[str, object]:
    """AC-4, AC-5, Q3: build the `/v1/random/bytes` (and `/v1/seed` alias) body.

    `entropy_epoch` is populated now from `drbg_root.reseed_counter` (the same
    value `/health` reports as `drbg_reseeds`). `receipt` is reserved for the
    signed-provenance work in EPIC 9 and is `null` here.
    """
    data = random_bytes(size)
    encoded = data.hex() if fmt == "hex" else base64.b64encode(data).decode("ascii")
    root = db.get_root_key()
    return {
        "request_id": uuid.uuid4().hex,
        "format": fmt,
        "data": encoded,
        "entropy_epoch": root.reseed_counter if root else 0,
        "timestamp": datetime.now(timezone.utc),
        "receipt": None,
    }
