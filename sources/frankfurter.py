from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from sources.base import (
    BaseSource,
    build_results_from_usd_rates,
    currencies_required_for_pairs,
)
from sources.http import request_with_retries


class FrankfurterSource(BaseSource):
    name = "frankfurter"
    url = "https://api.frankfurter.app/latest"

    def __init__(self, client: httpx.AsyncClient):
        super().__init__()
        self.client = client

    async def fetch(self, pairs: list[str]):
        async def do_fetch():
            required = sorted(currencies_required_for_pairs(pairs) - {"USD"})
            params = {"from": "USD", "to": ",".join(required)} if required else {"from": "USD"}
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
