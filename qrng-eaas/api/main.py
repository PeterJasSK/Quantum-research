from __future__ import annotations

import base64
import binascii
import os
import secrets
import time

from fastapi import Depends, FastAPI, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from qeaas import db, dice, generation, kem, ratelimit, receipts
from qeaas.auth import hash_api_key, require_admin, require_api_key
from qeaas.errors import ApiError, register_error_handlers
from qeaas.gate import entropy_level, prime_cache, require_entropy
from qeaas.pool import burn, ingest_bits_bytes
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
    KemEncapsulateRequest,
    KemEncapsulateResponse,
    KemKeypairRequest,
    KemKeypairResponse,
    PubkeyResponse,
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
    pool_bytes = db.pool_bytes_remaining()
    return HealthResponse(
        status="ok",
        quantum_entropy_level=prime_cache(pool_bytes),
        pool_bytes_remaining=pool_bytes,
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
    """AC-3: rejection-sampled dice rolls, ungated. AC-1: per-IP rate limit.

    EPIC 5 Q2: echoes every DRBG byte drawn for the roll (accepted + rejected)
    so the web dice player's "bytes behind this roll" toggle is literal.
    """
    ratelimit.check_ip_rate(ratelimit.client_ip(request))
    rolls, drawn = dice.roll(body.sides, body.count)
    return DiceResponse(
        sides=body.sides,
        count=body.count,
        rolls=rolls,
        format="base64",
        bytes_used=base64.b64encode(drawn).decode("ascii"),
        bytes_count=len(drawn),
    )


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
    db.insert_issue_log(
        response.request_id, key.key_hash, "/v1/random/bytes", size, response.entropy_epoch
    )
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
    db.insert_issue_log(
        response.request_id, key.key_hash, "/v1/seed", bytes, response.entropy_epoch
    )
    return response


@app.post("/v1/verify")
def verify(request: Request, body: VerifyRequest) -> VerifyResponse:
    """AC-4/5/6: verify provenance, not the secret. Anon, but per-IP rate-limited (Decision 6)."""
    ratelimit.check_ip_rate(ratelimit.client_ip(request))
    verified, provenance, note = receipts.verify(body.request_id, body.receipt)
    return VerifyResponse(
        request_id=body.request_id, verified=verified, provenance=provenance, note=note
    )


@app.get("/v1/pubkey")
def pubkey() -> PubkeyResponse:
    """AC-1: published Ed25519 receipt-signing public key for external offline verification."""
    return PubkeyResponse(
        algorithm="Ed25519", format="base64", public_key=receipts.public_key_b64()
    )


@app.post("/admin/ingest", dependencies=[Depends(require_admin)])
async def admin_ingest(file: UploadFile) -> AdminIngestResponse:
    """AC-7, Q5: multipart `.txt` upload (`0`/`1` only), <= 10 MB, refills the pool."""
    if not file.filename or not file.filename.endswith(".txt"):
        raise ApiError(422, "bad_request")

    upload = bytearray(await file.read())
    if len(upload) > MAX_INGEST_BYTES:
        burn(upload)
        raise ApiError(413, "file_too_large")

    try:
        bytes_added = ingest_bits_bytes(bytes(upload), file.filename)
    except ValueError:
        raise ApiError(422, "bad_request")
    finally:
        burn(upload)

    return AdminIngestResponse(
        ingested=True,
        bytes_added=bytes_added,
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


_DEMO_SECRET_KEY_NOTE = (
    "demo only -- in production the keypair is generated client-side and the "
    "secret key never leaves the holder"
)
_DEMO_SHARED_SECRET_NOTE = (
    "demo only -- decapsulation happens client-side on the holder of the "
    "secret key; this response is for local round-trip verification"
)


@app.post(
    "/v1/kem/keypair",
    dependencies=[Depends(require_entropy)],
)
def kem_keypair(
    body: KemKeypairRequest,
    key: db.ApiKeyRow = Depends(require_api_key),
) -> KemKeypairResponse:
    """AC-1/2/3/7: QRNG-seeded ML-KEM-768 keygen. `ek` always; `dk` demo-only."""
    ratelimit.enforce_key(key, kem.KEYGEN_QUOTA_COST)
    ek, dk = kem.generate_keypair()
    meta = generation.new_issue_meta(kem.KEYGEN_SEED_BYTES)
    response = KemKeypairResponse(
        **meta,
        algorithm=kem.ALGORITHM,
        format="base64",
        public_key=base64.b64encode(ek).decode("ascii"),
        secret_key=base64.b64encode(dk).decode("ascii")
        if body.include_secret_key
        else None,
        note=_DEMO_SECRET_KEY_NOTE if body.include_secret_key else None,
    )
    db.insert_usage_log(key.key_hash, "/v1/kem/keypair", kem.KEYGEN_SEED_BYTES)
    db.insert_issue_log(
        response.request_id,
        key.key_hash,
        "/v1/kem/keypair",
        kem.KEYGEN_SEED_BYTES,
        response.entropy_epoch,
    )
    return response


@app.post(
    "/v1/kem/encapsulate",
    dependencies=[Depends(require_entropy)],
)
def kem_encapsulate(
    body: KemEncapsulateRequest,
    key: db.ApiKeyRow = Depends(require_api_key),
) -> KemEncapsulateResponse:
    """AC-4/7: QRNG-seeded encapsulation against a supplied `ek`."""
    ratelimit.enforce_key(key, kem.ENCAPS_QUOTA_COST)
    try:
        ek = base64.b64decode(body.public_key, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(422, "bad_request")
    shared_secret, ciphertext = kem.encapsulate(ek)
    meta = generation.new_issue_meta(kem.ENCAPS_SEED_BYTES)
    response = KemEncapsulateResponse(
        **meta,
        algorithm=kem.ALGORITHM,
        format="base64",
        ciphertext=base64.b64encode(ciphertext).decode("ascii"),
        shared_secret=base64.b64encode(shared_secret).decode("ascii")
        if body.include_shared_secret
        else None,
        demo_key=base64.b64encode(kem.derive_demo_key(shared_secret)).decode("ascii")
        if body.include_shared_secret
        else None,
        note=_DEMO_SHARED_SECRET_NOTE if body.include_shared_secret else None,
    )
    db.insert_usage_log(key.key_hash, "/v1/kem/encapsulate", kem.ENCAPS_SEED_BYTES)
    db.insert_issue_log(
        response.request_id,
        key.key_hash,
        "/v1/kem/encapsulate",
        kem.ENCAPS_SEED_BYTES,
        response.entropy_epoch,
    )
    return response
