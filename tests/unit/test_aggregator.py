from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from core.aggregator import Aggregator
from sources.base import BaseSource, RateResult


class FakeSource(BaseSource):
    def __init__(self, name: str, rates: dict[str, str], *, fail: bool = False):
        super().__init__()
        self.name = name
        self._rates = rates
        self._fail = fail

    async def fetch(self, pairs: list[str]) -> list[RateResult]:
        if self._fail:
            raise RuntimeError(f"{self.name} failure")
        now = datetime.now(UTC)
        return [
            RateResult(
                pair=pair,
                rate=Decimal(self._rates[pair]),
                source=self.name,
                fetched_at=now,
                ok=True,
            )
            for pair in pairs
        ]


@pytest.mark.asyncio
async def test_aggregator_uses_remaining_sources_on_failure(test_settings):
    sources = [
        FakeSource("ecb", {"USD/EUR": "0.9000"}),
        FakeSource("frankfurter", {"USD/EUR": "0.8998"}),
        FakeSource("openexchange", {"USD/EUR": "0.9010"}, fail=True),
    ]
    aggregator = Aggregator(sources=sources, settings=test_settings)
    result = await aggregator.aggregate(["USD/EUR"])
    normalized = result["USD/EUR"]
    assert normalized.rate is not None
    assert normalized.source_count == 2


@pytest.mark.asyncio
async def test_aggregator_marks_unavailable_if_all_fail(test_settings):
    sources = [
        FakeSource("ecb", {"USD/EUR": "0.9000"}, fail=True),
        FakeSource("frankfurter", {"USD/EUR": "0.8998"}, fail=True),
    ]
    aggregator = Aggregator(sources=sources, settings=test_settings)
    result = await aggregator.aggregate(["USD/EUR"])
    normalized = result["USD/EUR"]
    assert normalized.confidence == "unavailable"
    assert normalized.rate is None
