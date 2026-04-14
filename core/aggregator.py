from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from core.config import Settings
from core.normalizer import NormalizedRate, normalize_pair_results
from sources.base import BaseSource, RateResult, failure_results_for_pairs


class Aggregator:
    def __init__(self, sources: list[BaseSource], settings: Settings):
        self.sources = sources
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.poll_concurrency_limit)

    async def aggregate(self, pairs: list[str]) -> dict[str, NormalizedRate]:
        if not pairs:
            return {}

        grouped: dict[str, list[RateResult]] = defaultdict(list)
        for pair in pairs:
            grouped[pair] = []

        async def fetch_one(source: BaseSource) -> list[RateResult]:
            async with self._semaphore:
                try:
                    return await source.fetch(pairs)
                except Exception as exc:
                    now = datetime.now(UTC)
                    return failure_results_for_pairs(
                        source_name=source.name,
                        pairs=pairs,
                        error=str(exc),
                        fetched_at=now,
                    )

        results_by_source = await asyncio.gather(*(fetch_one(source) for source in self.sources))
        for source_results in results_by_source:
            for result in source_results:
                grouped[result.pair].append(result)

        return {
            pair: normalize_pair_results(pair=pair, results=pair_results, settings=self.settings)
            for pair, pair_results in grouped.items()
        }

    def get_source_statuses(self) -> list[dict[str, Any]]:
        return [source.status() for source in self.sources]
