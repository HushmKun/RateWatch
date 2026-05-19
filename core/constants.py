from __future__ import annotations

from typing import Literal


CRYPTO_CURRENCIES = {"BTC", "ETH", "XRP", "SOL", "DOGE"}
MAJOR_CURRENCIES = {"EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"}
MINOR_CURRENCIES = {
    "SEK",
    "NOK",
    "DKK",
    "SGD",
    "HKD",
    "MXN",
    "PLN",
    "CZK",
    "HUF",
    "KRW",
    "THB",
    "MYR",
    "PHP",
    "BRL",
    "ZAR",
    "TRY",
    "EGP",
    "CNY",
    "INR",
    "IDR",
}
TRACKED_PAIRS = [
    "USD/EGP",
    "USD/EUR",
    "USD/GBP",
    "USD/JPY",
    "USD/CHF",
    "USD/CAD",
    "USD/AUD",
    "USD/NZD",
    "USD/MXN",
    "USD/BRL",
    "USD/CNY",
    "USD/INR",
    "USD/KRW",
    "USD/SGD",
    "USD/HKD",
    "USD/SEK",
    "USD/NOK",
    "USD/DKK",
    "USD/PLN",
    "USD/CZK",
    "USD/HUF",
    "USD/ZAR",
    "USD/TRY",
    "USD/THB",
    "USD/IDR",
    "USD/MYR",
    "USD/PHP",
    "EUR/GBP",
    "EUR/JPY",
    "EUR/CHF",
    "GBP/JPY",
    "EUR/AUD",
]
PAIR_REGEX = r"^[A-Z]{3}/[A-Z]{3}$"


def normalize_currency(currency: str) -> str:
    return currency.strip().upper()


def normalize_pair(pair: str) -> str:
    base, target = pair.split("/")
    return f"{normalize_currency(base)}/{normalize_currency(target)}"


def split_pair(pair: str) -> tuple[str, str]:
    normalized = normalize_pair(pair)
    base, target = normalized.split("/")
    return base, target


def classify_pair(pair: str) -> Literal["CRYPTO", "MAJOR", "MINOR", "EXOTIC"]:
    base, target = split_pair(pair)
    currencies = {base, target}
    if currencies & CRYPTO_CURRENCIES:
        return "CRYPTO"
    if currencies <= (MAJOR_CURRENCIES | {"USD"}):
        return "MAJOR"
    if currencies <= (MINOR_CURRENCIES | MAJOR_CURRENCIES | {"USD"}):
        return "MINOR"
    return "EXOTIC"
