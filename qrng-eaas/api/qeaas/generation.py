"""AC-2, AC-4, AC-5: single served-randomness choke point.

Raw QRNG bits are never served; every byte returned here is DRBG-derived via
`keyed_drbg.output()`. QRNG only seeds a standards DRBG -- it does not "defeat
quantum attackers" on its own.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from qeaas import db, receipts
from qeaas.keyed_drbg import output


def random_bytes(n: int) -> bytes:
    return output(n)


def new_issue_meta(size: int) -> dict[str, object]:
    """AC-2, AC-8 (EPIC 4/9): provenance metadata shared by `issue_v1` and `kem`.

    `entropy_epoch` is populated from `drbg_root.reseed_counter` (the same
    value `/health` reports as `drbg_reseeds`). `receipt` is a signed Ed25519
    token over `(request_id, size, entropy_epoch, timestamp)` (EPIC 9).
    """
    root = db.get_root_key()
    request_id = uuid.uuid4().hex
    entropy_epoch = root.reseed_counter if root else 0
    timestamp = datetime.now(timezone.utc)
    return {
        "request_id": request_id,
        "entropy_epoch": entropy_epoch,
        "timestamp": timestamp,
        "receipt": receipts.sign(request_id, size, entropy_epoch, timestamp),
    }


def issue_v1(size: int, fmt: str) -> dict[str, object]:
    """AC-4, AC-5, Q3: build the `/v1/random/bytes` (and `/v1/seed` alias) body."""
    data = random_bytes(size)
    encoded = data.hex() if fmt == "hex" else base64.b64encode(data).decode("ascii")
    return {**new_issue_meta(size), "format": fmt, "data": encoded}
