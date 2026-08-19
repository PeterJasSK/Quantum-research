# ported from TargetedDosColisionsAndRNGAngle/testbed/salt/qrng_client.py (CD-7)
"""Thin client for the Q-EaaS developer entropy endpoint (epic Appendix A.1).

No Python client for `GET /v1/random/bytes` exists elsewhere in the repo, so
this is a standalone implementation using stdlib `urllib.request` (OQ-3:
`requests` only if retry/backoff proves clumsy here -- it does not). Error
envelope verified against `qrng-eaas/api/qeaas/errors.py`:
`{"error": "<slug>"}`, with a `Retry-After` header on 429.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

Format = Literal["hex", "base64"]

# Retry policy: only 503 (entropy gate -- transient, pool may recover) and
# 429 (rate/quota -- honour Retry-After) are retried. 401 is a
# misconfiguration and fails loudly on the first attempt (epic ss"The QRNG
# source").
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 1.0


class QRNGUnavailable(Exception):
    """Raised when the Q-EaaS endpoint could not serve entropy after retrying."""


@dataclass(frozen=True)
class QRNGResponse:
    request_id: str
    format: Format
    data: str  # hex or base64 salt bytes, per `format`
    entropy_epoch: int
    timestamp: str
    receipt: str | None


class QRNGClient:
    """`GET /v1/random/bytes` client (epic Appendix A.1)."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def fetch(self, *, size: int = 32, fmt: Format = "hex") -> QRNGResponse:
        """Fetch `size` bytes of entropy with provenance. Raises `QRNGUnavailable`
        on retry exhaustion; 401 raises immediately (auth misconfiguration)."""
        url = f"{self._base_url}/v1/random/bytes?size={size}&format={fmt}"
        request = urllib.request.Request(
            url, headers={"X-API-Key": self._api_key}, method="GET"
        )

        last_error: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(request, timeout=10) as resp:
                    body = json.loads(resp.read())
                    return QRNGResponse(
                        request_id=body["request_id"],
                        format=body["format"],
                        data=body["data"],
                        entropy_epoch=body["entropy_epoch"],
                        timestamp=body["timestamp"],
                        receipt=body.get("receipt"),
                    )
            except urllib.error.HTTPError as exc:
                code = _error_code(exc)
                if exc.code == 401:
                    raise QRNGUnavailable(f"auth failed ({code}) -- check QEAAS_API_KEY") from exc
                if exc.code == 429:
                    last_error = exc
                    retry_after = float(exc.headers.get("Retry-After", _BACKOFF_SECONDS))
                    if attempt < _MAX_ATTEMPTS:
                        time.sleep(retry_after)
                    continue
                if exc.code == 503:
                    last_error = exc
                    if attempt < _MAX_ATTEMPTS:
                        time.sleep(_BACKOFF_SECONDS * attempt)
                    continue
                raise QRNGUnavailable(f"unexpected status {exc.code} ({code})") from exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(_BACKOFF_SECONDS * attempt)
                continue

        raise QRNGUnavailable(
            f"Q-EaaS unavailable after {_MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error


def _error_code(exc: urllib.error.HTTPError) -> str:
    """Best-effort extraction of the `{"error": "<slug>"}` envelope's slug."""
    try:
        return json.loads(exc.read())["error"]
    except Exception:
        return "unknown"
