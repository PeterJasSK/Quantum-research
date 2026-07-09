from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Request

from qeaas import db
from qeaas.gate import entropy_level, require_entropy

app = FastAPI(title="Quantum Entropy-as-a-Service")

_started_at = time.time()


@app.middleware("http")
async def add_entropy_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Quantum-Entropy"] = entropy_level()
    return response


@app.get("/health")
def health() -> dict[str, object]:
    root = db.get_root_key()
    return {
        "status": "ok",
        "quantum_entropy_level": entropy_level(),
        "pool_bytes_remaining": db.pool_bytes_remaining(),
        "drbg_reseeds": root.reseed_counter if root else 0,
        "uptime": time.time() - _started_at,
    }


@app.get("/v1/seed", dependencies=[Depends(require_entropy)])
def seed_stub() -> dict[str, bool]:
    return {"stub": True}


@app.post("/v1/kem/keypair", dependencies=[Depends(require_entropy)])
def kem_keypair_stub() -> dict[str, bool]:
    return {"stub": True}
