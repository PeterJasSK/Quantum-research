"""AC-9, AC-10, AC-11, AC-13: the low-entropy gate end-to-end via the FastAPI app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from qeaas import db
from main import app

client = TestClient(app)


def _set_pool_bytes(monkeypatch, remaining: int) -> None:
    monkeypatch.setattr(db, "pool_bytes_remaining", lambda: remaining)
    monkeypatch.setattr(db, "get_root_key", lambda: None)


def test_degraded_when_pool_low(monkeypatch) -> None:
    _set_pool_bytes(monkeypatch, remaining=100)  # below THRESHOLD (64 KiB)

    health = client.get("/health")
    assert health.json()["quantum_entropy_level"] == "degraded"
    assert health.headers["X-Quantum-Entropy"] == "degraded"

    seed = client.get("/v1/seed")
    assert seed.status_code == 503
    assert seed.json()["detail"] == {"error": "low_quantum_entropy"}


def test_healthy_after_refill(monkeypatch) -> None:
    _set_pool_bytes(monkeypatch, remaining=1024 * 1024)  # well above THRESHOLD

    health = client.get("/health")
    assert health.json()["quantum_entropy_level"] == "healthy"
    assert health.headers["X-Quantum-Entropy"] == "healthy"

    seed = client.get("/v1/seed")
    assert seed.status_code == 200
    assert seed.json() == {"stub": True}


def test_header_present_on_every_response(monkeypatch) -> None:
    _set_pool_bytes(monkeypatch, remaining=1024 * 1024)
    response = client.get("/health")
    assert "X-Quantum-Entropy" in response.headers
