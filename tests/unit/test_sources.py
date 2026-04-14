from __future__ import annotations

from decimal import Decimal

from sources.ecb import _parse_ecb_rates_to_usd


def test_ecb_xml_parser_converts_to_usd_base():
    xml = """
    <Envelope>
      <Cube>
        <Cube time="2026-01-15">
          <Cube currency="USD" rate="1.1000" />
          <Cube currency="GBP" rate="0.8500" />
          <Cube currency="JPY" rate="160.0000" />
        </Cube>
      </Cube>
    </Envelope>
    """
    usd_rates = _parse_ecb_rates_to_usd(xml)
    assert usd_rates["USD"] == Decimal("1")
    assert usd_rates["EUR"] == Decimal("0.90909091")
    assert usd_rates["GBP"] == Decimal("0.77272727")
