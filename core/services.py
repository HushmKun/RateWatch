from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from core.aggregator import Aggregator
from core.config import Settings
from core.scheduler import PollScheduler


@dataclass
class Services:
    settings: Settings
    aggregator: Aggregator
    scheduler: PollScheduler


def get_services(request: Request) -> Services:
    services: Services | None = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Application services are not initialized.")
    return services
