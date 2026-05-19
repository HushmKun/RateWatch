from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.constants import PAIR_REGEX


class HistoryPoint(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: float})

    timestamp: datetime
    rate: float
    confidence: str


class TrendStats(BaseModel):
    open: float
    close: float
    high: float
    low: float
    change_pct: float


class HistoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    pair: str = Field(pattern=PAIR_REGEX)
    interval: Literal["raw", "hourly", "daily"]
    from_: datetime = Field(alias="from")
    to: datetime
    data_points: int
    data: list[HistoryPoint]
    trend: TrendStats
