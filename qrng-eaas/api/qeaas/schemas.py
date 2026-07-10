"""AC-9: Pydantic models for every EPIC 2 request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Format = Literal["hex", "base64"]


class HealthResponse(BaseModel):
    status: str
    quantum_entropy_level: Literal["healthy", "degraded"]
    pool_bytes_remaining: int
    drbg_reseeds: int
    uptime: float


class RandomResponse(BaseModel):
    bytes: int
    format: Literal["base64"]
    data: str


class DiceRequest(BaseModel):
    sides: int = Field(default=6, ge=2, le=100)
    count: int = Field(default=1, ge=1, le=6)


class DiceResponse(BaseModel):
    sides: int
    count: int
    rolls: list[int]


class V1RandomBytesResponse(BaseModel):
    request_id: str
    format: Format
    data: str
    entropy_epoch: int
    timestamp: datetime
    receipt: str | None = None


class VerifyRequest(BaseModel):
    request_id: str | None = None
    receipt: str | None = None

    @model_validator(mode="after")
    def _require_one(self) -> "VerifyRequest":
        if not self.request_id and not self.receipt:
            raise ValueError("one of request_id or receipt is required")
        return self


class VerifyResponse(BaseModel):
    request_id: str | None
    verified: bool
    provenance: dict[str, object] | None
    note: str


class AdminIngestResponse(BaseModel):
    ingested: bool
    bytes_added: int
    pool_bytes_remaining: int


class AdminKeyRequest(BaseModel):
    owner: str
    tier: str = "default"
    daily_quota_bytes: int | None = None


class AdminKeyResponse(BaseModel):
    api_key: str
    owner: str
    tier: str
    daily_quota_bytes: int | None


class AdminRevokeRequest(BaseModel):
    key_hash: str


class AdminRevokeResponse(BaseModel):
    key_hash: str
    revoked: bool


class KemKeypairRequest(BaseModel):
    include_secret_key: bool = False


class KemKeypairResponse(BaseModel):
    request_id: str
    algorithm: Literal["ML-KEM-768"]
    format: Literal["base64"]
    public_key: str
    secret_key: str | None = None
    entropy_epoch: int
    timestamp: datetime
    receipt: str | None = None
    note: str | None = None


class KemEncapsulateRequest(BaseModel):
    public_key: str
    include_shared_secret: bool = False


class KemEncapsulateResponse(BaseModel):
    request_id: str
    algorithm: Literal["ML-KEM-768"]
    format: Literal["base64"]
    ciphertext: str
    shared_secret: str | None = None
    demo_key: str | None = None
    entropy_epoch: int
    timestamp: datetime
    receipt: str | None = None
    note: str | None = None
