from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import normalize_pair
from core.errors import (
    HISTORY_RANGE_TOO_LARGE,
    INVALID_PAIR_FORMAT,
    PAIR_NOT_FOUND,
    RateWatchError,
)
from core.services import Services, get_services
from db.crud import get_rate_history
from db.session import get_session
from schemas.history import HistoryPoint, HistoryResponse, TrendStats


router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{pair:path}", response_model=HistoryResponse)
async def get_history(
    pair: str,
    services: Annotated[Services, Depends(get_services)],
    session: Annotated[AsyncSession, Depends(get_session)],
    from_dt: Annotated[datetime | None, Query(alias="from")] = None,
    to_dt: datetime | None = None,
    interval: Literal["raw", "hourly", "daily"] = "hourly",
    limit: int = Query(default=500, ge=1, le=5000),
) -> HistoryResponse:
    try:
        pair = normalize_pair(pair)
    except ValueError as exc:
        raise RateWatchError(INVALID_PAIR_FORMAT) from exc
    if pair not in services.settings.tracked_pairs:
        raise RateWatchError(PAIR_NOT_FOUND.with_message(f"Currency pair {pair} is not tracked."))

    now = datetime.now(UTC)
    resolved_to = _as_utc(to_dt) if to_dt is not None else now
    resolved_from = _as_utc(from_dt) if from_dt is not None else (resolved_to - timedelta(hours=24))

    if resolved_from >= resolved_to:
        raise RateWatchError(
            HISTORY_RANGE_TOO_LARGE.with_message("The `from` datetime must be earlier than `to`.")
        )
    if (resolved_to - resolved_from) > timedelta(days=90):
        raise RateWatchError(HISTORY_RANGE_TOO_LARGE)

    history = await get_rate_history(
        session=session,
        pair=pair,
        from_dt=resolved_from,
        to_dt=resolved_to,
        interval=interval,
        limit=limit,
    )

    points = [
        HistoryPoint(
            timestamp=row.timestamp,
            rate=float(row.rate),
            confidence=row.confidence,
        )
        for row in history
    ]

    if not points:
        trend = TrendStats(open=0.0, close=0.0, high=0.0, low=0.0, change_pct=0.0)
    else:
        rates = [point.rate for point in points]
        open_rate = rates[0]
        close_rate = rates[-1]
        trend = TrendStats(
            open=open_rate,
            close=close_rate,
            high=max(rates),
            low=min(rates),
            change_pct=((close_rate - open_rate) / open_rate * 100) if open_rate else 0.0,
        )

    return HistoryResponse(
        pair=pair,
        interval=interval,
        from_=resolved_from,
        to=resolved_to,
        data_points=len(points),
        data=points,
        trend=trend,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
