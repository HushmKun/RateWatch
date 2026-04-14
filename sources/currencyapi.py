from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from core.config import Settings
from sources.base import BaseSource, build_results_from_usd_rates
from sources.http import request_with_retries


class CurrencyApiSource(BaseSource):
    name = "currencyapi"
    url = "https://api.currencyapi.com/v3/latest"

    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        super().__init__()
        self.client = client
        self.settings = settings

    async def fetch(self, pairs: list[str]):
        async def do_fetch():
            if not self.settings.currencyapi_key:
                raise RuntimeError("currencyapi_key is not configured.")

            headers = {"apikey": self.settings.currencyapi_key}
            params = {"base_currency": "USD"}
            response = await request_with_retries(
                self.client,
                self.url,
                params=params,
                headers=headers,
            )
            payload = response.json()
            fetched_at = datetime.now(UTC)
            usd_rates = {"USD": Decimal("1")}
            for currency, data in payload.get("data", {}).items():
                value = data.get("value")
                if value is not None:
                    usd_rates[currency] = Decimal(str(value))
            return build_results_from_usd_rates(
                source_name=self.name,
                pairs=pairs,
                usd_rates=usd_rates,
                fetched_at=fetched_at,
            )

        return await self._wrap_fetch(pairs, do_fetch)
