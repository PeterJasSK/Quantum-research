"""S3.1/S3.2/S3.3 throttling policy: per-IP and per-key fixed-window rate
limits, a global anon daily output ceiling, and per-key daily byte quotas.

All counters are atomic Redis ops (`INCR`/`INCRBY`/`EXPIRE`/`DECRBY`) -- no
read-modify-write, serverless-safe, matching the DRBG-counter pattern
(`qeaas.redis_client.incr_counter`).

This module bounds *served DRBG output volume* only. It is deliberately
decoupled from QRNG pool consumption: served bytes are always DRBG-derived
(`qeaas.keyed_drbg.output`), so hammering these limits never pulls the pool
faster -- the pool is protected separately by the reseed-frequency floor in
`qeaas.keyed_drbg` (AC-6/AC-7/AC-12).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request

from qeaas import db, redis_client
from qeaas.errors import ApiError

logger = logging.getLogger(__name__)

ANON_IP_PER_MIN = 60
ANON_DAILY_BYTES = 5 * 1024 * 1024

TIER_QUOTAS: dict[str, int] = {
    "default": 262_144,
    "iot": 10_485_760,
    "trusted": 524_288_000,
}

TIER_RATE_LIMITS: dict[str, int] = {
    "default": 120,
    "iot": 600,
    "trusted": 1_200,
}

DEFAULT_TIER = "default"


def client_ip(request: Request) -> str:
    """Leftmost `X-Forwarded-For` entry (Vercel-fronted), else the socket peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _seconds_until_next_minute() -> int:
    now = datetime.now(timezone.utc)
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    return max(1, int((next_minute - now).total_seconds()))


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((tomorrow - now).total_seconds()))


def _quota_for(row: db.ApiKeyRow) -> int:
    if row.daily_quota_bytes is not None:
        return row.daily_quota_bytes
    return TIER_QUOTAS.get(row.tier, TIER_QUOTAS[DEFAULT_TIER])


def _rate_for(row: db.ApiKeyRow) -> int:
    return TIER_RATE_LIMITS.get(row.tier, TIER_RATE_LIMITS[DEFAULT_TIER])


def _check_rate(key: str, limit: int) -> None:
    """Q6: fail-open on a Redis error -- the reseed floor still protects the pool."""
    try:
        count = redis_client.incr_expire(key, ttl=60)
    except Exception:
        logger.warning("ratelimit: Redis unavailable, failing open for %s", key)
        return
    if count > limit:
        raise ApiError(
            429,
            "rate_limited",
            headers={"Retry-After": str(_seconds_until_next_minute())},
        )


def _check_daily(key: str, nbytes: int, ceiling: int, over_limit_code: str) -> None:
    """Q6: fail-open on a Redis error -- the reseed floor still protects the pool."""
    ttl = _seconds_until_utc_midnight()
    try:
        total = redis_client.incrby_expire(key, nbytes, ttl)
    except Exception:
        logger.warning("ratelimit: Redis unavailable, failing open for %s", key)
        return
    if total > ceiling:
        try:
            redis_client.decrby(key, nbytes)
        except Exception:
            pass
        raise ApiError(
            429, over_limit_code, headers={"Retry-After": str(ttl)}
        )


def check_ip_rate(ip: str) -> None:
    """AC-1: 60 req/min/IP fixed window on `/random` and `/dice`."""
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    _check_rate(f"rl:ip:{ip}:{bucket}", ANON_IP_PER_MIN)


def check_anon_daily(nbytes: int) -> None:
    """AC-2: global daily output ceiling for anon `/random`."""
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    _check_daily(f"anon:daily:{day}", nbytes, ANON_DAILY_BYTES, "daily_limit_reached")


def enforce_key(row: db.ApiKeyRow, size: int) -> None:
    """AC-4: per-key rate limit, then per-key daily quota (rate is cheaper to reject)."""
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    _check_rate(f"rl:key:{row.key_hash}:{bucket}", _rate_for(row))

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    _check_daily(
        f"quota:key:{row.key_hash}:{day}", size, _quota_for(row), "quota_exceeded"
    )
