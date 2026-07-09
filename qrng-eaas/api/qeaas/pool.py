"""Entropy pool: encrypted-at-rest QRNG bytes, decrypted only to reseed the DRBG.

Raw QRNG bits are entropy that seeds a standards DRBG (see `qeaas.drbg`); they
are never served directly and never stored in plaintext (AC-12). The pool's
encryption key is HKDF-derived from `MASTER_KEY`, not the master key itself.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from Crypto.Cipher import AES

from qeaas import db

_NONCE_LEN = 12
_TAG_LEN = 16
_HKDF_HASH = hashlib.sha256


def derive_subkey(name: str) -> bytes:
    """HKDF-SHA256 sub-key derivation from `MASTER_KEY` (RFC 5869, one-block Expand)."""
    master_key = bytes.fromhex(os.environ["MASTER_KEY"])
    prk = hmac.new(b"", master_key, _HKDF_HASH).digest()
    return hmac.new(prk, name.encode("utf-8") + b"\x01", _HKDF_HASH).digest()


def encrypt_chunk(plaintext: bytes) -> tuple[bytes, bytes, bytes]:
    """Encrypt a pool chunk with AES-256-GCM. Returns (ciphertext, nonce, tag)."""
    key = derive_subkey("pool-encryption-key")
    nonce = os.urandom(_NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=_TAG_LEN)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return ciphertext, nonce, tag


def decrypt_chunk(ciphertext: bytes, nonce: bytes, tag: bytes) -> bytearray:
    """Decrypt a pool chunk. Raises `ValueError` if the tag doesn't verify (tampered)."""
    key = derive_subkey("pool-encryption-key")
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=_TAG_LEN)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return bytearray(plaintext)


def burn(buf: bytearray) -> None:
    """Best-effort zeroization of a sensitive buffer in place."""
    for i in range(len(buf)):
        buf[i] = 0


def parse_bits_file(path: str | Path) -> bytes:
    """AC-14: parse a `.txt` file of only `0`/`1` characters into packed bytes.

    Stray whitespace/newlines are stripped. Any other character is rejected.
    Bits are packed MSB-first, 8 bits -> 1 byte; a trailing partial byte
    (< 8 bits) is discarded.
    """
    raw = Path(path).read_text()
    bits = "".join(raw.split())

    invalid = set(bits) - {"0", "1"}
    if invalid:
        raise ValueError(f"bits file contains non-0/1 characters: {sorted(invalid)!r}")

    usable_len = (len(bits) // 8) * 8
    packed = bytearray(usable_len // 8)
    for i in range(0, usable_len, 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | (1 if bit == "1" else 0)
        packed[i // 8] = byte
    return bytes(packed)


def ingest_bits_file(path: str | Path, source_label: str = "") -> None:
    """Parse, encrypt, and store a QRNG `.txt` file as a new pool chunk."""
    plaintext = parse_bits_file(path)
    ciphertext, nonce, tag = encrypt_chunk(plaintext)
    db.insert_pool_chunk(ciphertext, nonce, tag, len(plaintext), source_label)


def pull_reseed_material(n: int = 32) -> bytearray:
    """Decrypt and return the next `n` unconsumed plaintext bytes, advancing the offset."""
    chunk = db.next_unconsumed_chunk(n)
    if chunk is None:
        raise RuntimeError("entropy pool exhausted: no unconsumed bytes remain")

    plaintext = decrypt_chunk(chunk.ciphertext, chunk.nonce, chunk.tag)
    material = bytearray(plaintext[chunk.offset_in_chunk : chunk.offset_in_chunk + n])
    db.advance_consumed_offset(chunk.id, chunk.offset_in_chunk + n)
    burn(plaintext)
    return material
