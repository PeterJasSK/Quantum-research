"""Lazy Upstash Redis client -- backs the serverless-safe output counter (AC-3)."""

from __future__ import annotations

import os

import redis

_client: redis.Redis | None = None

COUNTER_KEY = "drbg:counter"


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(os.environ["REDIS_URL"])
    return _client


def incr_counter() -> int:
    """Atomically increment and return `drbg:counter`."""
    return _get_client().incr(COUNTER_KEY)


def incr_expire(key: str, ttl: int) -> int:
    """INCR `key`; set EXPIRE only on the first increment (count == 1) so an
    existing TTL is never reset by a later hit within the same window."""
    client = _get_client()
    count = client.incr(key)
    if count == 1:
        client.expire(key, ttl)
    return count


def incrby_expire(key: str, amount: int, ttl: int) -> int:
    """INCRBY `key` by `amount`; set EXPIRE only on the first write."""
    client = _get_client()
    total = client.incrby(key, amount)
    if total == amount:
        client.expire(key, ttl)
    return total


def decrby(key: str, amount: int) -> int:
    """Refund a byte counter (e.g. after an over-limit rejection)."""
    return _get_client().decrby(key, amount)
