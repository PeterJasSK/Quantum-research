from __future__ import annotations

import base64
import os
import tempfile
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from qeaas import db, dice, generation
from qeaas.auth import require_admin, require_api_key
from qeaas.errors import ApiError, register_error_handlers
from qeaas.gate import entropy_level, require_entropy
from qeaas.pool import ingest_bits_file, parse_bits_file
from qeaas.schemas import (
    AdminIngestResponse,
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
def random_endpoint(bytes: int = Query(default=32, ge=1, le=64)) -> RandomResponse:
    """AC-2: anonymous, ungated -- dice must survive a `degraded` pool."""
    data = generation.random_bytes(bytes)
    return RandomResponse(
        bytes=bytes, format="base64", data=base64.b64encode(data).decode("ascii")
    )


@app.post("/dice")
def dice_endpoint(body: DiceRequest) -> DiceResponse:
    """AC-3: rejection-sampled dice rolls, ungated."""
    rolls = dice.roll(body.sides, body.count)
    return DiceResponse(sides=body.sides, count=body.count, rolls=rolls)


def _issue_v1(size: int, fmt: str) -> V1RandomBytesResponse:
    return V1RandomBytesResponse(**generation.issue_v1(size, fmt))


@app.get(
    "/v1/random/bytes",
    dependencies=[Depends(require_api_key), Depends(require_entropy)],
)
def v1_random_bytes(
    size: int = Query(ge=32, le=4096), format: Format = "hex"
) -> V1RandomBytesResponse:
    """AC-4: canonical dev endpoint. Real API-key hash validation; no quota check (EPIC 3)."""
    return _issue_v1(size, format)


@app.get(
    "/v1/seed",
    dependencies=[Depends(require_api_key), Depends(require_entropy)],
)
def seed(bytes: int = Query(ge=32, le=4096), format: Format = "hex") -> V1RandomBytesResponse:
    """AC-5: alias of `/v1/random/bytes` -- shares the same service function so it cannot drift."""
    return _issue_v1(bytes, format)


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


@app.post("/v1/kem/keypair", dependencies=[Depends(require_entropy)])
def kem_keypair_stub() -> dict[str, bool]:
    return {"stub": True}
