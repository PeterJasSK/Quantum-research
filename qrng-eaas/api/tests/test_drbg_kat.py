"""AC-1, AC-2: HmacDrbg output matches NIST CAVP HMAC_DRBG SHA-256 KAT vectors."""

from __future__ import annotations

import json
from pathlib import Path

from qeaas.drbg import HmacDrbg

VECTORS_PATH = Path(__file__).parent / "vectors" / "hmac_drbg_sha256.json"


def _load_vectors() -> list[dict]:
    return json.loads(VECTORS_PATH.read_text())


def test_kat_vectors() -> None:
    vectors = _load_vectors()
    assert len(vectors) >= 10

    for vector in vectors:
        entropy_input = bytes.fromhex(vector["entropy_input"])
        nonce = bytes.fromhex(vector["nonce"])
        personalization = bytes.fromhex(vector["personalization_string"])
        additional_1 = bytes.fromhex(vector["additional_input_1"])
        additional_2 = bytes.fromhex(vector["additional_input_2"])
        expected = bytes.fromhex(vector["returned_bits"])

        drbg = HmacDrbg()
        drbg.instantiate(entropy_input + nonce, personalization)

        if vector["reseed"]:
            entropy_input_reseed = bytes.fromhex(vector["entropy_input_reseed"])
            additional_input_reseed = bytes.fromhex(vector["additional_input_reseed"])
            drbg.reseed(entropy_input_reseed, additional_input_reseed)

        drbg.generate(len(expected), additional_1)
        actual = drbg.generate(len(expected), additional_2)

        assert actual == expected, f"COUNT={vector['count']} reseed={vector['reseed']} mismatch"
