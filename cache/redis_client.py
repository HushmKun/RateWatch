from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

from redis.asyncio import Redis

from core.config import Settings
from core.constants import classify_pair, split_pair
from core.normalizer import NormalizedRate


_redis_pool: Redis | None = None


def rate_key(pair: str) -> str:
    base, target = split_pair(pair)
    return f"rate:{base}:{target}"


def rate_lock_key(pair: str) -> str:
    base, target = split_pair(pair)
    return f"rate:{base}:{target}:lock"


def get_ttl_for_pair(pair: str, settings: Settings) -> int:
    category = classify_pair(pair)
    return settings.ttl_map[category]


def _serialize_rate(rate: NormalizedRate) -> str:
    return json.dumps(
        {
            "pair": rate.pair,
            "rate": str(rate.rate) if rate.rate is not None else None,
            "source_count": rate.source_count,
            "confidence": rate.confidence,
            "normalized_at": rate.normalized_at.isoformat(),
            "sources_used": rate.sources_used,
        }
    )


def _deserialize_rate(payload: str) -> NormalizedRate:
    data = json.loads(payload)
    normalized_at = datetime.fromisoformat(data["normalized_at"])
    if normalized_at.tzinfo is None:
        normalized_at = normalized_at.replace(tzinfo=UTC)
    else:
        normalized_at = normalized_at.astimezone(UTC)
    return NormalizedRate(
        pair=data["pair"],
        rate=Decimal(data["rate"]) if data["rate"] is not None else None,
        source_count=int(data["source_count"]),
        confidence=data["confidence"],
        normalized_at=normalized_at,
        sources_used=list(data["sources_used"]),
    )


async def init_redis_pool(settings: Settings) -> None:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis_pool() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


def get_redis_pool() -> Redis:
    if _redis_pool is None:
        raise RuntimeError("Redis pool is not initialized.")
    return _redis_pool


async def get_redis() -> Redis:
    return get_redis_pool()


async def get_cached_rate(redis: Redis, pair: str) -> NormalizedRate | None:
    payload = await redis.get(rate_key(pair))
    if payload is None:
        return None
    return _deserialize_rate(payload)


async def set_cached_rate(redis: Redis, rate: NormalizedRate, ttl_seconds: int) -> None:
    await redis.set(rate_key(rate.pair), _serialize_rate(rate), ex=ttl_seconds)


async def mget_cached_rates(redis: Redis, pairs: list[str]) -> dict[str, NormalizedRate | None]:
    keys = [rate_key(pair) for pair in pairs]
    payloads = await redis.mget(keys)
    parsed: dict[str, NormalizedRate | None] = {}
    for pair, payload in zip(pairs, payloads, strict=True):
        parsed[pair] = _deserialize_rate(payload) if payload else None
    return parsed


async def get_or_fetch_rate(
    redis: Redis,
    pair: str,
    settings: Settings,
    fetcher: Callable[[str], Awaitable[NormalizedRate | None]],
) -> NormalizedRate | None:
    cached = await get_cached_rate(redis, pair)
    if cached is not None:
        return cached

    lock_acquired = await redis.set(rate_lock_key(pair), "1", nx=True, ex=10)
    if not lock_acquired:
        await asyncio.sleep(0.2)
        return await get_cached_rate(redis, pair)

    try:
        rate = await fetcher(pair)
        if rate is None:
            return None
        ttl = get_ttl_for_pair(pair, settings)
        await set_cached_rate(redis, rate, ttl)
        return rate
    finally:
        await redis.delete(rate_lock_key(pair))


async def write_source_health(redis: Redis, statuses: list[dict[str, object]]) -> None:
    payload = {
        status["name"]: {
            "ok": status["healthy"],
            "last_checked": datetime.now(UTC).isoformat(),
        }
        for status in statuses
    }
    await redis.set("sources:health", json.dumps(payload), ex=60)
