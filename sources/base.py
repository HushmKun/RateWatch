from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

from core.constants import split_pair


@dataclass
class RateResult:
    pair: str
    rate: Decimal
    source: str
    fetched_at: datetime
    ok: bool
    error: str | None = None


class BaseSource(ABC):
    name: str

    def __init__(self) -> None:
        self._is_healthy = False
        self._last_fetched_at: datetime | None = None
        self._pairs_served = 0
        self._avg_response_ms = 0.0

    @abstractmethod
    async def fetch(self, pairs: list[str]) -> list[RateResult]:
        raise NotImplementedError

    @property
    def is_healthy(self) -> bool:
        return self._is_healthy

    def _mark_cycle(self, results: list[RateResult], duration_ms: float) -> None:
        self._is_healthy = any(result.ok for result in results)
        self._last_fetched_at = datetime.now(UTC)
        self._pairs_served = sum(1 for result in results if result.ok)
        self._avg_response_ms = duration_ms

    def status(self) -> dict[str, object]:
        return {
            "name": self.name,
            "healthy": self._is_healthy,
            "last_fetched_at": self._last_fetched_at,
            "pairs_served": self._pairs_served,
            "avg_response_ms": round(self._avg_response_ms, 2),
        }

    async def _wrap_fetch(
        self,
        pairs: list[str],
        fetch_fn: Callable[[], Awaitable[list[RateResult]]],
    ) -> list[RateResult]:
        start = perf_counter()
        try:
            results = await fetch_fn()
        except Exception as exc:
            results = failure_results_for_pairs(
                source_name=self.name,
                pairs=pairs,
                error=str(exc),
                fetched_at=datetime.now(UTC),
            )
        duration_ms = (perf_counter() - start) * 1000
        self._mark_cycle(results, duration_ms)
        return results


def failure_results_for_pairs(
    source_name: str,
    pairs: list[str],
    error: str,
    fetched_at: datetime,
) -> list[RateResult]:
    return [
        RateResult(
            pair=pair,
            rate=Decimal("0"),
            source=source_name,
            fetched_at=fetched_at,
            ok=False,
            error=error,
        )
        for pair in pairs
    ]


def currencies_required_for_pairs(pairs: list[str]) -> set[str]:
    currencies: set[str] = set()
    for pair in pairs:
        base, target = split_pair(pair)
        currencies.add(base)
        currencies.add(target)
    return currencies


def build_results_from_usd_rates(
    source_name: str,
    pairs: list[str],
    usd_rates: dict[str, Decimal],
    fetched_at: datetime,
) -> list[RateResult]:
    results: list[RateResult] = []
    for pair in pairs:
        base, target = split_pair(pair)
        usd_to_base = usd_rates.get(base)
        usd_to_target = usd_rates.get(target)
        if usd_to_base is None or usd_to_target is None or usd_to_base <= 0:
            results.append(
                RateResult(
                    pair=pair,
                    rate=Decimal("0"),
                    source=source_name,
                    fetched_at=fetched_at,
                    ok=False,
                    error=f"Missing conversion leg(s): {base} or {target}",
                )
            )
            continue
        rate = (usd_to_target / usd_to_base).quantize(Decimal("0.00000001"))
        results.append(
            RateResult(
                pair=pair,
                rate=rate,
                source=source_name,
                fetched_at=fetched_at,
                ok=True,
            )
        )
    return results
