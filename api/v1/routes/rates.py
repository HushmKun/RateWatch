from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from cache.redis_client import (
    get_or_fetch_rate,
    get_redis,
    get_ttl_for_pair,
    mget_cached_rates,
    rate_key,
    set_cached_rate,
)
from core.constants import normalize_currency, normalize_pair
from core.errors import INVALID_PAIR_FORMAT, PAIR_NOT_FOUND, RATE_UNAVAILABLE, RateWatchError
from core.services import Services, get_services
from schemas.rate import RatePoint, RatesResponse


router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("/{base}", response_model=RatesResponse)
async def get_rates_for_base(
    base: str,
    services: Annotated[Services, Depends(get_services)],
    redis: Annotated[Redis, Depends(get_redis)],
    targets: Annotated[list[str] | None, Query()] = None,
) -> RatesResponse:
    base = normalize_currency(base)
    tracked_pairs = set(services.settings.tracked_pairs)

    if targets:
        requested_pairs: list[str] = []
        for target in targets:
            try:
                requested_pairs.append(normalize_pair(f"{base}/{target}"))
            except ValueError as exc:
                raise RateWatchError(INVALID_PAIR_FORMAT) from exc
    else:
        requested_pairs = [pair for pair in services.settings.tracked_pairs if pair.startswith(f"{base}/")]

    unknown = [pair for pair in requested_pairs if pair not in tracked_pairs]
    if unknown:
        raise RateWatchError(
            PAIR_NOT_FOUND.with_message(f"Currency pair {unknown[0]} is not tracked.")
        )

    cached = await mget_cached_rates(redis, requested_pairs)
    missing = [pair for pair, value in cached.items() if value is None]
    if missing:
        aggregated = await services.aggregator.aggregate(missing)
        for pair, normalized in aggregated.items():
            cached[pair] = normalized
            if normalized.rate is not None:
                ttl = get_ttl_for_pair(pair, services.settings)
                await set_cached_rate(redis, normalized, ttl)

    points: list[RatePoint] = []
    for pair in requested_pairs:
        normalized = cached.get(pair)
        if normalized is None or normalized.rate is None:
            continue
        ttl_remaining = await redis.ttl(rate_key(pair))
        points.append(
            RatePoint(
                pair=pair,
                rate=float(normalized.rate),
                confidence=normalized.confidence,
                source_count=normalized.source_count,
                cached_at=normalized.normalized_at,
                ttl_remaining_s=max(ttl_remaining, 0),
            )
        )

    if not points:
        raise RateWatchError(RATE_UNAVAILABLE)

    return RatesResponse(base=base, rates=points, generated_at=datetime.now(UTC))


@router.get("/{base}/{target}", response_model=RatePoint)
async def get_single_rate(
    base: str,
    target: str,
    services: Annotated[Services, Depends(get_services)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> RatePoint:
    try:
        pair = normalize_pair(f"{base}/{target}")
    except ValueError as exc:
        raise RateWatchError(INVALID_PAIR_FORMAT) from exc
    if pair not in services.settings.tracked_pairs:
        raise RateWatchError(PAIR_NOT_FOUND.with_message(f"Currency pair {pair} is not tracked."))

    async def fetch_pair(requested_pair: str):
        aggregated = await services.aggregator.aggregate([requested_pair])
        return aggregated.get(requested_pair)

    normalized = await get_or_fetch_rate(
        redis=redis,
        pair=pair,
        settings=services.settings,
        fetcher=fetch_pair,
    )
    if normalized is None or normalized.rate is None:
        raise RateWatchError(RATE_UNAVAILABLE.with_message(f"Rate for {pair} is unavailable."))

    ttl_remaining = await redis.ttl(rate_key(pair))
    return RatePoint(
        pair=pair,
        rate=float(normalized.rate),
        confidence=normalized.confidence,
        source_count=normalized.source_count,
        cached_at=normalized.normalized_at,
        ttl_remaining_s=max(ttl_remaining, 0),
    )
