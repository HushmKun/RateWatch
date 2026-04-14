from __future__ import annotations

from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cache.redis_client import (
    get_redis_pool,
    get_ttl_for_pair,
    set_cached_rate,
    write_source_health,
)
from core.aggregator import Aggregator
from core.config import Settings
from db.crud import insert_snapshots
from db.models import RateSnapshot
from db.partitions import ensure_partition


class PollScheduler:
    def __init__(
        self,
        settings: Settings,
        aggregator: Aggregator,
        session_factory: async_sessionmaker,
        engine: AsyncEngine,
    ):
        self.settings = settings
        self.aggregator = aggregator
        self.session_factory = session_factory
        self.engine = engine
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self.scheduler.add_job(
            self.poll_all_pairs,
            trigger="interval",
            seconds=self.settings.poll_interval_seconds,
            id="poll_all_pairs",
            max_instances=1,
        )
        self.scheduler.add_job(
            self.create_next_month_partition,
            trigger="cron",
            day=1,
            hour=0,
            minute=5,
            id="create_next_month_partition",
            max_instances=1,
        )
        self.scheduler.add_job(
            self.publish_source_health,
            trigger="interval",
            seconds=60,
            id="publish_source_health",
            max_instances=1,
        )
        self.scheduler.start()
        self._started = True

    def shutdown(self) -> None:
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    async def poll_all_pairs(self) -> None:
        pairs = self.settings.tracked_pairs
        aggregated = await self.aggregator.aggregate(pairs)
        redis = get_redis_pool()

        snapshots: list[RateSnapshot] = []
        for pair, rate in aggregated.items():
            if rate.rate is None:
                continue
            ttl = get_ttl_for_pair(pair, self.settings)
            await set_cached_rate(redis, rate, ttl)
            snapshots.append(
                RateSnapshot(
                    pair=pair,
                    rate=rate.rate,
                    source_count=rate.source_count,
                    confidence=rate.confidence,
                    sources_used=rate.sources_used,
                    recorded_at=rate.normalized_at,
                )
            )

        if snapshots:
            async with self.session_factory() as session:
                await insert_snapshots(session, snapshots)
        await write_source_health(redis, self.aggregator.get_source_statuses())

    async def publish_source_health(self) -> None:
        redis = get_redis_pool()
        await write_source_health(redis, self.aggregator.get_source_statuses())

    async def create_next_month_partition(self) -> None:
        now = datetime.now(UTC).replace(day=1)
        next_month = now + timedelta(days=32)
        async with self.engine.begin() as conn:
            await ensure_partition(next_month.year, next_month.month, conn)
