"""AC-12: AES-256-GCM round-trip, tamper detection, and buffer burn."""

from __future__ import annotations

import pytest

from qeaas.pool import burn, decrypt_chunk, encrypt_chunk


def test_encrypt_decrypt_round_trip() -> None:
    plaintext = b"quantum-derived entropy chunk" * 4
    ciphertext, nonce, tag = encrypt_chunk(plaintext)

    assert ciphertext != plaintext
    assert len(nonce) == 12
    assert len(tag) == 16

    recovered = decrypt_chunk(ciphertext, nonce, tag)
    assert bytes(recovered) == plaintext


def test_tampered_ciphertext_raises() -> None:
    plaintext = b"some pool bytes"
    ciphertext, nonce, tag = encrypt_chunk(plaintext)

    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF

    with pytest.raises(ValueError):
        decrypt_chunk(bytes(tampered), nonce, tag)


def test_burn_zeroes_buffer() -> None:
    buf = bytearray(b"sensitive-material")
    burn(buf)
    assert buf == bytearray(len(buf))
