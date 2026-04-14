from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RateSnapshot

HistoryInterval = Literal["raw", "hourly", "daily"]


@dataclass
class HistoryRecord:
    timestamp: datetime
    rate: Decimal
    confidence: str


async def insert_snapshots(session: AsyncSession, snapshots: list[RateSnapshot]) -> None:
    if not snapshots:
        return
    session.add_all(snapshots)
    await session.commit()


async def get_rate_history(
    session: AsyncSession,
    pair: str,
    from_dt: datetime,
    to_dt: datetime,
    interval: HistoryInterval = "raw",
    limit: int = 1000,
) -> list[HistoryRecord]:
    if interval == "raw":
        statement = (
            select(RateSnapshot)
            .where(
                RateSnapshot.pair == pair,
                RateSnapshot.recorded_at >= from_dt,
                RateSnapshot.recorded_at <= to_dt,
            )
            .order_by(RateSnapshot.recorded_at.asc())
            .limit(limit)
        )
        result = await session.scalars(statement)
        return [
            HistoryRecord(
                timestamp=_ensure_utc(row.recorded_at),
                rate=row.rate,
                confidence=row.confidence,
            )
            for row in result.all()
        ]

    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    bucket = _bucket_expression(interval, dialect)
    statement = (
        select(
            bucket.label("bucket"),
            func.avg(RateSnapshot.rate).label("avg_rate"),
        )
        .where(
            RateSnapshot.pair == pair,
            RateSnapshot.recorded_at >= from_dt,
            RateSnapshot.recorded_at <= to_dt,
        )
        .group_by(bucket)
        .order_by(bucket.asc())
        .limit(limit)
    )
    result = await session.execute(statement)
    rows: list[HistoryRecord] = []
    for bucket_value, avg_rate in result.all():
        rows.append(
            HistoryRecord(
                timestamp=_coerce_bucket(bucket_value),
                rate=Decimal(str(avg_rate)),
                confidence="aggregated",
            )
        )
    return rows


def _bucket_expression(interval: HistoryInterval, dialect: str):
    if dialect == "postgresql":
        trunc = "hour" if interval == "hourly" else "day"
        return func.date_trunc(trunc, RateSnapshot.recorded_at)
    if interval == "hourly":
        return cast(func.strftime("%Y-%m-%d %H:00:00", RateSnapshot.recorded_at), String)
    return cast(func.strftime("%Y-%m-%d 00:00:00", RateSnapshot.recorded_at), String)


def _coerce_bucket(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return _ensure_utc(value)
    parsed = datetime.fromisoformat(value)
    return _ensure_utc(parsed)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
