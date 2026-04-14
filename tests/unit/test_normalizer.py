from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from core.normalizer import normalize_pair_results
from sources.base import RateResult


def make_result(pair: str, source: str, rate: str, *, ok: bool = True) -> RateResult:
    return RateResult(
        pair=pair,
        source=source,
        rate=Decimal(rate) if ok else Decimal("0"),
        fetched_at=datetime.now(UTC),
        ok=ok,
        error=None if ok else "failed",
    )


def test_normalizer_high_confidence(test_settings):
    results = [
        make_result("USD/EUR", "ecb", "0.9000"),
        make_result("USD/EUR", "frankfurter", "0.9001"),
        make_result("USD/EUR", "openexchange", "0.8998"),
    ]
    normalized = normalize_pair_results("USD/EUR", results, test_settings)
    assert normalized.confidence == "high"
    assert normalized.source_count == 3
    assert normalized.rate is not None


def test_normalizer_drops_outlier(test_settings):
    results = [
        make_result("USD/EUR", "ecb", "0.9000"),
        make_result("USD/EUR", "frankfurter", "0.9002"),
        make_result("USD/EUR", "openexchange", "0.8999"),
        make_result("USD/EUR", "currencyapi", "0.9001"),
        make_result("USD/EUR", "sourcex", "0.9000"),
        make_result("USD/EUR", "sourcey", "1.5000"),
    ]
    normalized = normalize_pair_results("USD/EUR", results, test_settings)
    assert normalized.confidence == "medium"
    assert normalized.source_count == 5


def test_normalizer_low_confidence(test_settings):
    results = [make_result("USD/EUR", "ecb", "0.9000")]
    normalized = normalize_pair_results("USD/EUR", results, test_settings)
    assert normalized.confidence == "low"
    assert normalized.source_count == 1


def test_normalizer_unavailable(test_settings):
    results = [make_result("USD/EUR", "ecb", "0", ok=False)]
    normalized = normalize_pair_results("USD/EUR", results, test_settings)
    assert normalized.confidence == "unavailable"
    assert normalized.rate is None
