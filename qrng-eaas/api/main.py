from __future__ import annotations

import base64
import os
import secrets
import tempfile
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from qeaas import db, dice, generation, ratelimit
from qeaas.auth import hash_api_key, require_admin, require_api_key
from qeaas.errors import ApiError, register_error_handlers
from qeaas.gate import entropy_level, require_entropy
from qeaas.pool import ingest_bits_file, parse_bits_file
from qeaas.schemas import (
    AdminIngestResponse,
    AdminKeyRequest,
    AdminKeyResponse,
    AdminRevokeRequest,
    AdminRevokeResponse,
    DiceRequest,
    DiceResponse,
    Format,
    HealthResponse,
    RandomResponse,
    V1RandomBytesResponse,
    VerifyRequest,
    VerifyResponse,
)

app = FastAPI(title="Quantum Entropy-as-a-Service")
_started_at = time.time()

_web_origins = [
    o.strip() for o in os.environ.get("WEB_ORIGIN", "http://localhost:3000").split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_web_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

MAX_INGEST_BYTES = 10 * 1024 * 1024


@app.middleware("http")
async def add_entropy_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Quantum-Entropy"] = entropy_level()
    return response


@app.get("/health")
def health() -> HealthResponse:
    root = db.get_root_key()
    return HealthResponse(
        status="ok",
        quantum_entropy_level=entropy_level(),
        pool_bytes_remaining=db.pool_bytes_remaining(),
        drbg_reseeds=root.reseed_counter if root else 0,
        uptime=time.time() - _started_at,
    )


@app.get("/random")
def random_endpoint(
    request: Request, bytes: int = Query(default=32, ge=1, le=64)
) -> RandomResponse:
    """AC-2: anonymous, ungated -- dice must survive a `degraded` pool.

    AC-1/AC-2: per-IP rate limit, then the global anon daily output ceiling.
    """
    ip = ratelimit.client_ip(request)
    ratelimit.check_ip_rate(ip)
    ratelimit.check_anon_daily(bytes)
    data = generation.random_bytes(bytes)
    return RandomResponse(
        bytes=bytes, format="base64", data=base64.b64encode(data).decode("ascii")
    )


@app.post("/dice")
def dice_endpoint(request: Request, body: DiceRequest) -> DiceResponse:
    """AC-3: rejection-sampled dice rolls, ungated. AC-1: per-IP rate limit."""
    ratelimit.check_ip_rate(ratelimit.client_ip(request))
    rolls = dice.roll(body.sides, body.count)
    return DiceResponse(sides=body.sides, count=body.count, rolls=rolls)


def _issue_v1(size: int, fmt: str) -> V1RandomBytesResponse:
    return V1RandomBytesResponse(**generation.issue_v1(size, fmt))


@app.get(
    "/v1/random/bytes",
    dependencies=[Depends(require_entropy)],
)
def v1_random_bytes(
    size: int = Query(ge=32, le=4096),
    format: Format = "hex",
    key: db.ApiKeyRow = Depends(require_api_key),
) -> V1RandomBytesResponse:
    """AC-4: canonical dev endpoint. Per-key rate limit + daily quota, then usage log."""
    ratelimit.enforce_key(key, size)
    response = _issue_v1(size, format)
    db.insert_usage_log(key.key_hash, "/v1/random/bytes", size)
    return response


@app.get(
    "/v1/seed",
    dependencies=[Depends(require_entropy)],
)
def seed(
    bytes: int = Query(ge=32, le=4096),
    format: Format = "hex",
    key: db.ApiKeyRow = Depends(require_api_key),
) -> V1RandomBytesResponse:
    """AC-5: alias of `/v1/random/bytes` -- shares the same service function so it cannot drift."""
    ratelimit.enforce_key(key, bytes)
    response = _issue_v1(bytes, format)
    db.insert_usage_log(key.key_hash, "/v1/seed", bytes)
    return response


@app.post("/v1/verify")
def verify(body: VerifyRequest) -> VerifyResponse:
    """AC-6: unsigned provenance stub. Not a value-confirmation oracle. Real signing = EPIC 9."""
    return VerifyResponse(
        request_id=body.request_id,
        verified=False,
        provenance=None,
        note="provenance verification is not yet implemented (EPIC 9)",
    )


@app.post("/admin/ingest", dependencies=[Depends(require_admin)])
async def admin_ingest(file: UploadFile) -> AdminIngestResponse:
    """AC-7, Q5: multipart `.txt` upload (`0`/`1` only), <= 10 MB, refills the pool."""
    if not file.filename or not file.filename.endswith(".txt"):
        raise ApiError(422, "bad_request")

    content = await file.read()
    if len(content) > MAX_INGEST_BYTES:
        raise ApiError(413, "file_too_large")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        try:
            plaintext = parse_bits_file(tmp_path)
        except ValueError:
            raise ApiError(422, "bad_request")
        ingest_bits_file(tmp_path, file.filename)
    finally:
        tmp_path.unlink(missing_ok=True)

    return AdminIngestResponse(
        ingested=True,
        bytes_added=len(plaintext),
        pool_bytes_remaining=db.pool_bytes_remaining(),
    )


@app.post("/admin/keys", dependencies=[Depends(require_admin)])
def admin_mint_key(body: AdminKeyRequest) -> AdminKeyResponse:
    """AC-9: HTTP mint route (EPIC 2 Q4 carry-over); same logic as `scripts/mint_key.py`."""
    key = secrets.token_urlsafe(32)
    db.insert_api_key(hash_api_key(key), body.owner, body.tier, body.daily_quota_bytes)
    return AdminKeyResponse(
        api_key=key,
        owner=body.owner,
        tier=body.tier,
        daily_quota_bytes=body.daily_quota_bytes,
    )


@app.post("/admin/keys/revoke", dependencies=[Depends(require_admin)])
def admin_revoke_key(body: AdminRevokeRequest) -> AdminRevokeResponse:
    """AC-8: instant revocation -- `require_api_key` reads the row fresh every request."""
    revoked = db.revoke_api_key(body.key_hash)
    if not revoked:
        raise ApiError(404, "not_found")
    return AdminRevokeResponse(key_hash=body.key_hash, revoked=True)


@app.post("/v1/kem/keypair", dependencies=[Depends(require_entropy)])
def kem_keypair_stub() -> dict[str, bool]:
    return {"stub": True}
