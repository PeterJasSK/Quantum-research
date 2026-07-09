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
