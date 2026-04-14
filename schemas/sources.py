from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SourceStatus(BaseModel):
    name: str
    healthy: bool
    last_fetched_at: datetime | None
    pairs_served: int
    avg_response_ms: float


class SourcesResponse(BaseModel):
    sources: list[SourceStatus]
    healthy_count: int
    total_count: int
