#!/usr/bin/env python
"""EPIC 8 (S8.1): two-role QRNG-seeded ML-KEM handshake -> AES-GCM message exchange.

Models a **Server** (holds `dk`, decapsulates, encrypts) and a **Client**
(encapsulates, decrypts) driving the live `/v1/kem/*` endpoints. Both keygen
and encaps randomness come from the deployed QRNG->DRBG chain -- this script
logs the provenance (`request_id`, `entropy_epoch`) for each. The Server
independently decapsulates locally (the server never runs a decaps oracle --
decapsulation happens on the holder of `dk`) and asserts agreement with the
Client's shared secret, then both derive the same AES-GCM key and exchange
one encrypted message.

Usage:
    API_KEY=<key> python -m scripts.kem_handshake [--base-url http://localhost:8000] [--message TEXT]

Extends `scripts/kem_roundtrip.py` (keygen -> encaps -> decaps round-trip)
with the AES-GCM derivation + message exchange + provenance logging that
EPIC 4 deferred to this ticket.
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

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from kyber_py.ml_kem import ML_KEM_768

_DEFAULT_MESSAGE = "hello from the QRNG-seeded ML-KEM demo"


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
        payload = exc.read().decode()
        try:
            slug = json.loads(payload).get("error")
        except json.JSONDecodeError:
            slug = None
        if slug == "low_quantum_entropy":
            raise SystemExit(
                f"{path} failed: 503 low_quantum_entropy -- the target pool is "
                "degraded; check /health and refill it (never disable the gate)"
            )
        raise SystemExit(f"{path} failed: {exc.code} {payload}")


def _derive_key(shared_secret: bytes) -> bytes:
    return HKDF(shared_secret, 32, b"", SHA256)


def _log_provenance(role: str, step: str, meta: dict[str, object]) -> None:
    print(
        f"[{role}] {step}: request_id={meta['request_id']} "
        f"entropy_epoch={meta['entropy_epoch']} (QRNG-seeded DRBG output)"
    )


class Server:
    """Holds `dk`; decapsulates and encrypts the message."""

    def __init__(self, ek: str, dk: bytes) -> None:
        self.ek = ek
        self.dk = dk

    def decapsulate(self, ciphertext: bytes) -> bytes:
        return ML_KEM_768.decaps(self.dk, ciphertext)

    def encrypt(self, key: bytes, message: bytes) -> tuple[bytes, bytes, bytes]:
        nonce = os.urandom(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
        ciphertext, tag = cipher.encrypt_and_digest(message)
        return nonce, ciphertext, tag


class Client:
    """Holds the encapsulation output; decrypts the Server's message."""

    def __init__(self, shared_secret: bytes, ciphertext: bytes) -> None:
        self.shared_secret = shared_secret
        self.ciphertext = ciphertext

    def decrypt(self, key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
        return cipher.decrypt_and_verify(ciphertext, tag)


def run_demo(base_url: str, api_key: str, message: str) -> None:
    keypair_resp = _post(
        base_url, "/v1/kem/keypair", api_key, {"include_secret_key": True}
    )
    _log_provenance("Server", "keygen", keypair_resp)
    ek = keypair_resp["public_key"]
    dk = base64.b64decode(keypair_resp["secret_key"])
    server = Server(ek, dk)

    encaps_resp = _post(
        base_url,
        "/v1/kem/encapsulate",
        api_key,
        {"public_key": ek, "include_shared_secret": True},
    )
    _log_provenance("Client", "encapsulate", encaps_resp)
    ciphertext = base64.b64decode(encaps_resp["ciphertext"])
    shared_secret = base64.b64decode(encaps_resp["shared_secret"])
    service_demo_key = base64.b64decode(encaps_resp["demo_key"])
    client = Client(shared_secret, ciphertext)

    local_demo_key = _derive_key(shared_secret)
    if local_demo_key != service_demo_key:
        raise SystemExit(
            "MISMATCH: locally derived demo_key does not match the service's demo_key"
        )
    print("OK: local demo_key matches service demo_key")

    recovered_secret = server.decapsulate(client.ciphertext)
    if recovered_secret != client.shared_secret:
        raise SystemExit(
            "MISMATCH: server-decapsulated shared secret does not match the "
            "client's shared secret"
        )
    print(f"OK: server-decaps shared secret == client shared secret ({len(recovered_secret)}B)")

    nonce, ct, tag = server.encrypt(local_demo_key, message.encode("utf-8"))
    plaintext = client.decrypt(local_demo_key, nonce, ct, tag)
    print(f"OK: Client decrypted Server message: {plaintext.decode('utf-8')!r}")

    print("PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("API_BASE", "http://localhost:8000"))
    parser.add_argument("--message", default=_DEFAULT_MESSAGE)
    args = parser.parse_args()

    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise SystemExit("set API_KEY to a minted key (see scripts/mint_key.py)")

    run_demo(args.base_url, api_key, args.message)


if __name__ == "__main__":
    main()
