from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from core.services import Services, get_services
from schemas.sources import SourceStatus, SourcesResponse


router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse)
async def get_sources(
    services: Annotated[Services, Depends(get_services)],
) -> SourcesResponse:
    source_statuses = [SourceStatus(**status) for status in services.aggregator.get_source_statuses()]
    healthy_count = sum(1 for status in source_statuses if status.healthy)
    return SourcesResponse(
        sources=source_statuses,
        healthy_count=healthy_count,
        total_count=len(source_statuses),
    )
