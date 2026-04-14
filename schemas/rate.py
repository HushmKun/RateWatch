from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.constants import PAIR_REGEX

Confidence = Literal["high", "medium", "low", "unavailable"]


class RatePoint(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: float})

    pair: str = Field(pattern=PAIR_REGEX)
    rate: float
    confidence: Confidence
    source_count: int
    cached_at: datetime
    ttl_remaining_s: int


class RatesResponse(BaseModel):
    base: str
    rates: list[RatePoint]
    generated_at: datetime
