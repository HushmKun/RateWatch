from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from core.config import Settings
from sources.base import BaseSource, build_results_from_usd_rates
from sources.http import request_with_retries


class OpenExchangeSource(BaseSource):
    name = "openexchange"
    url = "https://openexchangerates.org/api/latest.json"

    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        super().__init__()
        self.client = client
        self.settings = settings

    async def fetch(self, pairs: list[str]):
        async def do_fetch():
            if not self.settings.openexchange_app_id:
                raise RuntimeError("openexchange_app_id is not configured.")

            params = {"app_id": self.settings.openexchange_app_id}
            response = await request_with_retries(self.client, self.url, params=params)
            payload = response.json()
            fetched_at = datetime.now(UTC)
            usd_rates = {"USD": Decimal("1")}
            for currency, rate in payload.get("rates", {}).items():
                usd_rates[currency] = Decimal(str(rate))
            return build_results_from_usd_rates(
                source_name=self.name,
                pairs=pairs,
                usd_rates=usd_rates,
                fetched_at=fetched_at,
            )

        return await self._wrap_fetch(pairs, do_fetch)
