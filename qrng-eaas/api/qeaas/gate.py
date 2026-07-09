"""Low-entropy gate: reports pool health and blocks premium routes when the
pool is running low, so the DRBG never reseeds from an exhausted pool."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

from qeaas import db
from qeaas.keyed_drbg import THRESHOLD


def entropy_level() -> Literal["healthy", "degraded"]:
    """AC-9: below `THRESHOLD` pool bytes remaining, health is 'degraded'."""
    return "degraded" if db.pool_bytes_remaining() < THRESHOLD else "healthy"


def require_entropy() -> None:
    """AC-10: FastAPI dependency that 503s premium routes while degraded."""
    if entropy_level() == "degraded":
        raise HTTPException(status_code=503, detail={"error": "low_quantum_entropy"})
