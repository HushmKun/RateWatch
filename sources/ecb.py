from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from xml.etree import ElementTree

import httpx

from sources.base import BaseSource, build_results_from_usd_rates
from sources.http import request_with_retries


class EcbSource(BaseSource):
    name = "ecb"
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

    def __init__(self, client: httpx.AsyncClient):
        super().__init__()
        self.client = client

    async def fetch(self, pairs: list[str]):
        async def do_fetch():
            response = await request_with_retries(self.client, self.url)
            fetched_at = datetime.now(UTC)
            usd_rates = _parse_ecb_rates_to_usd(response.text)
            return build_results_from_usd_rates(
                source_name=self.name,
                pairs=pairs,
                usd_rates=usd_rates,
                fetched_at=fetched_at,
            )

        return await self._wrap_fetch(pairs, do_fetch)


def _parse_ecb_rates_to_usd(xml_text: str) -> dict[str, Decimal]:
    root = ElementTree.fromstring(xml_text)
    rates_from_eur: dict[str, Decimal] = {"EUR": Decimal("1")}
    for cube in root.findall(".//{*}Cube[@currency][@rate]"):
        currency = cube.attrib["currency"]
        rate = cube.attrib["rate"]
        rates_from_eur[currency] = Decimal(rate)

    eur_to_usd = rates_from_eur.get("USD")
    if eur_to_usd is None or eur_to_usd <= 0:
        raise RuntimeError("ECB feed does not provide EUR/USD leg.")

    usd_rates: dict[str, Decimal] = {"USD": Decimal("1")}
    for currency, eur_to_currency in rates_from_eur.items():
        usd_rates[currency] = (eur_to_currency / eur_to_usd).quantize(Decimal("0.00000001"))
    return usd_rates
