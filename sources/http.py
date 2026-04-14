from __future__ import annotations

import asyncio

import httpx

from core.config import Settings


_http_client: httpx.AsyncClient | None = None


async def get_http_client(settings: Settings) -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=5.0,
            limits=httpx.Limits(max_connections=50),
            headers={"User-Agent": "RateWatch/1.0"},
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    attempts = 3
    backoff_seconds = 0.5
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code >= 500 and attempt < attempts:
                await asyncio.sleep(backoff_seconds)
                continue
            response.raise_for_status()
            return response
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            should_retry = isinstance(exc, httpx.RequestError) or (
                isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500
            )
            if should_retry and attempt < attempts:
                last_error = exc
                await asyncio.sleep(backoff_seconds)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Request retries exhausted.")
