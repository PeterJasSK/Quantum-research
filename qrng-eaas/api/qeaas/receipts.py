"""EPIC 9: Ed25519 receipt signing/verification.

Verify provenance, not the secret: the receipt signs issue *metadata*
(request_id, size, entropy_epoch, timestamp) -- never the output value.
The signing key is `derive_subkey("receipt-signing-key")`, HKDF-derived from
`MASTER_KEY` (same hierarchy as `pool-encryption-key`/`api-key-pepper`); it
lives only in env, never in the DB.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from functools import lru_cache

from Crypto.PublicKey import ECC
from Crypto.PublicKey.ECC import EccKey
from Crypto.Signature import eddsa

from qeaas import db
from qeaas.pool import derive_subkey

_VERSION = "qeaas1"


@lru_cache(maxsize=1)
def _signing_key() -> EccKey:
    return ECC.construct(curve="Ed25519", seed=derive_subkey("receipt-signing-key"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _canonical_payload(
    request_id: str, size: int, entropy_epoch: int, timestamp: datetime
) -> bytes:
    payload = {
        "rid": request_id,
        "sz": size,
        "epoch": entropy_epoch,
        "ts": timestamp.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def public_key_b64() -> str:
    """Raw 32-byte Ed25519 public key, base64-encoded, for external verification."""
    raw = _signing_key().public_key().export_key(format="raw")
    return base64.b64encode(raw).decode("ascii")


def sign(request_id: str, size: int, entropy_epoch: int, timestamp: datetime) -> str:
    """AC-2: sign `(request_id, size, entropy_epoch, timestamp)` into a compact receipt token."""
    payload = _canonical_payload(request_id, size, entropy_epoch, timestamp)
    signature = eddsa.new(_signing_key(), "rfc8032").sign(payload)
    return f"{_VERSION}.{_b64url_encode(payload)}.{_b64url_encode(signature)}"


def verify_receipt(token: str) -> dict[str, object] | None:
    """AC-5: verify a receipt token. Never raises -- returns `None` on any failure."""
    try:
        version, payload_b64, sig_b64 = token.split(".")
        if version != _VERSION:
            return None
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
        eddsa.new(_signing_key().public_key(), "rfc8032").verify(payload_bytes, signature)
        payload: dict[str, object] = json.loads(payload_bytes)
        return payload
    except (ValueError, KeyError, TypeError):
        return None


def verify(
    request_id: str | None, receipt: str | None
) -> tuple[bool, dict[str, object] | None, str]:
    """AC-4, Decision 4: resolve provenance from a receipt (signature-verified) and/or a
    request_id (issue_log lookup). Returns `(verified, provenance, note)`.
    """
    if receipt is not None:
        payload = verify_receipt(receipt)
        if payload is None:
            return False, None, "receipt signature is invalid or the token is malformed"
        if request_id is not None and payload.get("rid") != request_id:
            return False, None, "receipt does not match the supplied request_id"
        provenance = {
            "request_id": payload.get("rid"),
            "size": payload.get("sz"),
            "entropy_epoch": payload.get("epoch"),
            "timestamp": payload.get("ts"),
            "qrng_source_labels": db.get_pool_source_labels(),
        }
        return True, provenance, "receipt signature verified cryptographically"

    if request_id is not None:
        row = db.get_issue_log(request_id)
        if row is None:
            return False, None, "no issue log entry found for this request_id"
        provenance = {
            "request_id": row.request_id,
            "size": row.size,
            "endpoint": row.endpoint,
            "entropy_epoch": row.epoch_id,
            "timestamp": row.ts.isoformat(),
            "qrng_source_labels": db.get_pool_source_labels(),
        }
        return True, provenance, "resolved via issue log lookup, not a signature check"

    return False, None, "one of request_id or receipt is required"
