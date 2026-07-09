"""AC-13, Q2: admin-token guard and real API-key hash-validation.

Never store a plaintext API key: `key_hash = hmac_sha256(pepper, key)` where the
pepper is HKDF-derived from `MASTER_KEY` (`pool.derive_subkey("api-key-pepper")`).
No per-key quota check here -- quota enforcement is EPIC 3.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Header

from qeaas import db
from qeaas.errors import ApiError
from qeaas.pool import derive_subkey


def hash_api_key(key: str) -> str:
    pepper = derive_subkey("api-key-pepper")
    return hmac.new(pepper, key.encode("utf-8"), hashlib.sha256).hexdigest()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.environ["ADMIN_TOKEN"]
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise ApiError(401, "unauthorized")


def require_api_key(x_api_key: str | None = Header(default=None)) -> db.ApiKeyRow:
    if not x_api_key:
        raise ApiError(401, "missing_api_key")
    row = db.get_api_key_by_hash(hash_api_key(x_api_key))
    if row is None or row.revoked:
        raise ApiError(401, "invalid_api_key")
    return row
