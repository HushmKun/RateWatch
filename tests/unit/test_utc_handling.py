from __future__ import annotations

from datetime import UTC, datetime

from cache.redis_client import _deserialize_rate
from db.crud import _coerce_bucket


def test_coerce_bucket_normalizes_offset_datetime_to_utc():
    bucket = _coerce_bucket("2026-01-01T03:15:00+02:00")
    assert bucket == datetime(2026, 1, 1, 1, 15, tzinfo=UTC)


def test_deserialize_rate_normalizes_timestamp_to_utc():
    rate = _deserialize_rate(
        '{"pair":"USD/EUR","rate":"0.9","source_count":2,"confidence":"high","normalized_at":"2026-01-01T03:15:00+02:00","sources_used":["ecb","frankfurter"]}'
    )
    assert rate.normalized_at == datetime(2026, 1, 1, 1, 15, tzinfo=UTC)
