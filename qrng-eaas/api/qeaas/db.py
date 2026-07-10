"""Thin, parameterized psycopg helpers for the entropy_pool / drbg_root tables.

Serverless: open a connection per invocation, close it -- no long-lived pool
object. Every query is parameterized; no raw string-built SQL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

import psycopg


def connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


@dataclass
class RootKeyRow:
    id: int
    root_key: bytes
    reseed_counter: int
    outputs_since_reseed: int
    rotated_at: datetime


@dataclass
class PoolChunk:
    id: int
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    offset_in_chunk: int


@dataclass
class ApiKeyRow:
    key_hash: str
    owner: str
    tier: str
    daily_quota_bytes: int | None
    revoked: bool
    created_at: datetime


def get_root_key() -> RootKeyRow | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, root_key, reseed_counter, outputs_since_reseed, rotated_at "
            "FROM drbg_root ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row is None:
            return None
        return RootKeyRow(*row)


def save_root_key(root_key: bytes, reseed_counter: int, outputs_since_reseed: int) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO drbg_root (root_key, reseed_counter, outputs_since_reseed, rotated_at) "
            "VALUES (%s, %s, %s, now())",
            (root_key, reseed_counter, outputs_since_reseed),
        )
        conn.commit()


def bump_outputs_since_reseed(root_id: int) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE drbg_root SET outputs_since_reseed = outputs_since_reseed + 1 WHERE id = %s",
            (root_id,),
        )
        conn.commit()


def pool_bytes_remaining() -> int:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(plaintext_len - consumed_offset), 0) FROM entropy_pool"
        )
        (remaining,) = cur.fetchone()
        return int(remaining)


def insert_pool_chunk(
    ciphertext: bytes, nonce: bytes, tag: bytes, plaintext_len: int, source_label: str
) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO entropy_pool (ciphertext, nonce, tag, plaintext_len, source_label) "
            "VALUES (%s, %s, %s, %s, %s)",
            (ciphertext, nonce, tag, plaintext_len, source_label),
        )
        conn.commit()


def next_unconsumed_chunk(n: int) -> PoolChunk | None:
    """Oldest chunk with at least `n` unconsumed plaintext bytes remaining."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, ciphertext, nonce, tag, consumed_offset FROM entropy_pool "
            "WHERE plaintext_len - consumed_offset >= %s ORDER BY id ASC LIMIT 1",
            (n,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        chunk_id, ciphertext, nonce, tag, consumed_offset = row
        return PoolChunk(chunk_id, ciphertext, nonce, tag, consumed_offset)


def advance_consumed_offset(chunk_id: int, new_offset: int) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE entropy_pool SET consumed_offset = %s WHERE id = %s",
            (new_offset, chunk_id),
        )
        conn.commit()


def insert_api_key(
    key_hash: str, owner: str, tier: str, daily_quota_bytes: int | None
) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO api_keys (key_hash, owner, tier, daily_quota_bytes) "
            "VALUES (%s, %s, %s, %s)",
            (key_hash, owner, tier, daily_quota_bytes),
        )
        conn.commit()


def get_api_key_by_hash(key_hash: str) -> ApiKeyRow | None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT key_hash, owner, tier, daily_quota_bytes, revoked, created_at "
            "FROM api_keys WHERE key_hash = %s",
            (key_hash,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return ApiKeyRow(*row)


def get_api_key_hashes_by_owner(owner: str) -> list[str]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT key_hash FROM api_keys WHERE owner = %s", (owner,))
        return [key_hash for (key_hash,) in cur.fetchall()]


def revoke_api_key(key_hash: str) -> bool:
    """AC-8: revocation is instant -- `require_api_key` reads this row fresh every request."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE api_keys SET revoked = true WHERE key_hash = %s", (key_hash,)
        )
        conn.commit()
        return cur.rowcount == 1


def insert_usage_log(principal: str, endpoint: str, nbytes: int) -> None:
    """AC-8: abuse-spotting log, written for keyed issues (Q7)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO usage_log (principal, endpoint, nbytes) VALUES (%s, %s, %s)",
            (principal, endpoint, nbytes),
        )
        conn.commit()
