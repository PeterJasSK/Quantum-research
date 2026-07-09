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
