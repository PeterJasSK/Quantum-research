#!/usr/bin/env python
"""AC-6: prove `keygen -> encaps -> decaps` round-trips against the running API.

Fetches a QRNG-seeded ML-KEM-768 keypair and an encapsulation from the live
`/v1/kem/*` endpoints, then decapsulates *locally* (the server never runs a
decaps oracle -- decapsulation happens on the holder of `dk`, per Q3) and
asserts the recovered shared secret matches the one the server returned.

Usage:
    API_KEY=<key> python -m scripts.kem_roundtrip [--base-url http://localhost:8000]

Mirrors `shared/spikes/mlkem_seed_spike.py`, but exercises the live endpoints
instead of calling `kyber_py` directly for keygen/encaps.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kyber_py.ml_kem import ML_KEM_768


def _post(base_url: str, path: str, api_key: str, body: dict[str, object]) -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode("ascii"),
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(request) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{path} failed: {exc.code} {exc.read().decode()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("API_BASE", "http://localhost:8000"))
    args = parser.parse_args()

    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise SystemExit("set API_KEY to a minted key (see scripts/mint_key.py)")

    keypair = _post(
        args.base_url, "/v1/kem/keypair", api_key, {"include_secret_key": True}
    )
    dk = base64.b64decode(keypair["secret_key"])
    ek = keypair["public_key"]

    encapsulation = _post(
        args.base_url,
        "/v1/kem/encapsulate",
        api_key,
        {"public_key": ek, "include_shared_secret": True},
    )
    ciphertext = base64.b64decode(encapsulation["ciphertext"])
    shared_secret = base64.b64decode(encapsulation["shared_secret"])

    recovered = ML_KEM_768.decaps(dk, ciphertext)
    if recovered != shared_secret:
        raise SystemExit(
            "MISMATCH: locally decapsulated shared secret does not match the "
            "server's shared secret"
        )

    print(f"OK: QRNG-seeded ML-KEM-768 keypair round-trips (ss={len(recovered)}B)")


if __name__ == "__main__":
    main()
