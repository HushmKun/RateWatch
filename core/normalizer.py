from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from statistics import mean, stdev
from typing import Literal

from core.config import Settings
from sources.base import RateResult

Confidence = Literal["high", "medium", "low", "unavailable"]


@dataclass
class NormalizedRate:
    pair: str
    rate: Decimal | None
    source_count: int
    confidence: Confidence
    normalized_at: datetime
    sources_used: list[str]


def normalize_pair_results(
    pair: str,
    results: list[RateResult],
    settings: Settings,
) -> NormalizedRate:
    valid = [result for result in results if result.ok]
    if not valid:
        return NormalizedRate(
            pair=pair,
            rate=None,
            source_count=0,
            confidence="unavailable",
            normalized_at=datetime.now(UTC),
            sources_used=[],
        )

    dropped_outliers = 0
    filtered = valid
    if len(valid) >= 3:
        float_rates = [float(result.rate) for result in valid]
        deviation = stdev(float_rates)
        if deviation > 0:
            avg = mean(float_rates)
            threshold = settings.outlier_std_threshold
            filtered = [
                result
                for result in valid
                if abs(float(result.rate) - avg) < (threshold * deviation)
            ]
            dropped_outliers = len(valid) - len(filtered)

    if not filtered:
        return NormalizedRate(
            pair=pair,
            rate=None,
            source_count=0,
            confidence="unavailable",
            normalized_at=datetime.now(UTC),
            sources_used=[],
        )

    numerator = Decimal("0")
    denominator = Decimal("0")
    for result in filtered:
        weight = Decimal(str(settings.source_weights.get(result.source, 1.0)))
        numerator += result.rate * weight
        denominator += weight
    normalized_rate = (numerator / denominator).quantize(Decimal("0.00000001"))

    if len(filtered) < settings.min_sources_required:
        confidence: Confidence = "low"
    elif dropped_outliers > 0:
        confidence = "medium"
    else:
        confidence = "high"

    return NormalizedRate(
        pair=pair,
        rate=normalized_rate,
        source_count=len(filtered),
        confidence=confidence,
        normalized_at=max(result.fetched_at for result in filtered),
        sources_used=sorted({result.source for result in filtered}),
    )
