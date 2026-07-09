"""AC-7, AC-8: reseed advances consumed_offset / reseed_counter and shrinks the pool."""

from __future__ import annotations

from datetime import datetime

import qeaas.keyed_drbg as keyed_drbg
from qeaas import db, pool


class FakeStore:
    def __init__(self, plaintext: bytes) -> None:
        ciphertext, nonce, tag = pool.encrypt_chunk(plaintext)
        self.chunk = {
            "id": 1,
            "ciphertext": ciphertext,
            "nonce": nonce,
            "tag": tag,
            "plaintext_len": len(plaintext),
            "consumed_offset": 0,
        }
        self.root = {"id": 1, "reseed_counter": 0, "outputs_since_reseed": 0}

    def pool_bytes_remaining(self) -> int:
        return self.chunk["plaintext_len"] - self.chunk["consumed_offset"]

    def next_unconsumed_chunk(self, n: int):
        c = self.chunk
        if c["plaintext_len"] - c["consumed_offset"] < n:
            return None
        return db.PoolChunk(c["id"], c["ciphertext"], c["nonce"], c["tag"], c["consumed_offset"])

    def advance_consumed_offset(self, chunk_id: int, new_offset: int) -> None:
        self.chunk["consumed_offset"] = new_offset

    def get_root_key(self):
        return db.RootKeyRow(
            id=self.root["id"],
            root_key=b"\x00" * 32,
            reseed_counter=self.root["reseed_counter"],
            outputs_since_reseed=self.root["outputs_since_reseed"],
            rotated_at=datetime.fromtimestamp(0),  # forces the T-minute reseed trigger
        )

    def save_root_key(self, root_key: bytes, reseed_counter: int, outputs_since_reseed: int) -> None:
        self.root["reseed_counter"] = reseed_counter
        self.root["outputs_since_reseed"] = outputs_since_reseed


def test_reseed_advances_offset_and_shrinks_pool(monkeypatch) -> None:
    store = FakeStore(plaintext=b"\x42" * 1024)
    monkeypatch.setattr(keyed_drbg, "_cache", None)
    monkeypatch.setattr(db, "get_root_key", store.get_root_key)
    monkeypatch.setattr(db, "save_root_key", store.save_root_key)
    monkeypatch.setattr(db, "next_unconsumed_chunk", store.next_unconsumed_chunk)
    monkeypatch.setattr(db, "advance_consumed_offset", store.advance_consumed_offset)

    before_remaining = store.pool_bytes_remaining()

    keyed_drbg.maybe_reseed()

    assert store.chunk["consumed_offset"] == keyed_drbg.RESEED_PULL_BYTES
    assert store.root["reseed_counter"] == 1
    assert store.pool_bytes_remaining() == before_remaining - keyed_drbg.RESEED_PULL_BYTES
