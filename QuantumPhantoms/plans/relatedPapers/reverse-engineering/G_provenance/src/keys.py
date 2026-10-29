"""Demo Ed25519 signing key and the pinned trust list (AC-2).

    python -m G_provenance.src.keys init

The private key lives in G_provenance/runs/keys/ (gitignored). A signature is accepted only if its
public key is listed in trusted_keys.json; the stub key sha256(b"qp-re-stub-key") is never trusted.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from shared import RE_ROOT

KEYS_DIR = RE_ROOT / "G_provenance" / "runs" / "keys"
KEY_FILE = "signing_key.pem"
TRUST_FILE = "trusted_keys.json"


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def key_id(public_raw: bytes) -> str:
    return hashlib.sha256(public_raw).hexdigest()[:16]


def public_b64(key: Ed25519PrivateKey) -> str:
    return base64.b64encode(_raw_public(key)).decode()


def init_keys(keys_dir: Path = KEYS_DIR) -> Path:
    key_path = keys_dir / KEY_FILE
    if key_path.exists():
        raise FileExistsError(f"{key_path} exists; refusing to overwrite")
    keys_dir.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    key_path.chmod(0o600)
    entry = {"key_id": key_id(_raw_public(key)), "public_key_b64": public_b64(key),
             "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "note": "demo key, not a PKI"}
    (keys_dir / TRUST_FILE).write_text(json.dumps([entry], indent=2) + "\n")
    return key_path


def load_signer(keys_dir: Path = KEYS_DIR) -> Ed25519PrivateKey:
    key_path = keys_dir / KEY_FILE
    if not key_path.is_file():
        raise FileNotFoundError(f"{key_path} missing; run: python -m G_provenance.src.keys init")
    return serialization.load_pem_private_key(key_path.read_bytes(), password=None)


def trusted_public_keys(keys_dir: Path = KEYS_DIR) -> set[str]:
    f = keys_dir / TRUST_FILE
    if not f.is_file():
        return set()
    return {e["public_key_b64"] for e in json.loads(f.read_text())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("init",))
    ap.parse_args(argv)
    try:
        p = init_keys()
    except FileExistsError as e:
        print(e)
        return 1
    print(f"wrote {p.relative_to(RE_ROOT)} and {TRUST_FILE} (key_id {key_id(_raw_public(load_signer()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
