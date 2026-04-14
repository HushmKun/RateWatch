from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.v1.router import router as v1_router
from cache.redis_client import close_redis_pool, init_redis_pool
from core.aggregator import Aggregator
from core.config import get_settings
from core.errors import (
    INVALID_PAIR_FORMAT,
    RateWatchError,
    format_error_response,
)
from core.scheduler import PollScheduler
from core.services import Services
from db.models import Base
from db.partitions import ensure_current_and_next_partitions
from db.session import (
    dispose_db_engine,
    get_engine,
    get_session_factory,
    init_db_engine,
)
from sources.currencyapi import CurrencyApiSource
from sources.ecb import EcbSource
from sources.frankfurter import FrankfurterSource
from sources.http import close_http_client, get_http_client
from sources.openexchange import OpenExchangeSource


logger = logging.getLogger("ratewatch")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_redis_pool(settings)
    await init_db_engine(settings)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_current_and_next_partitions(conn)

    http_client = await get_http_client(settings)
    sources = [
        EcbSource(http_client),
        FrankfurterSource(http_client),
        OpenExchangeSource(http_client, settings),
        CurrencyApiSource(http_client, settings),
    ]
    aggregator = Aggregator(sources=sources, settings=settings)
    scheduler = PollScheduler(
        settings=settings,
        aggregator=aggregator,
        session_factory=get_session_factory(),
        engine=engine,
    )
    scheduler.start()
    app.state.services = Services(
        settings=settings,
        aggregator=aggregator,
        scheduler=scheduler,
    )

    try:
        yield
    finally:
        scheduler.shutdown()
        await close_http_client()
        await close_redis_pool()
        await dispose_db_engine()


app = FastAPI(title="RateWatch", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(v1_router, prefix=f"{settings.api_prefix}/v1")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.exception("%s %s -> 500 (%.2fms)", request.method, request.url.path, elapsed_ms)
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(RateWatchError)
async def ratewatch_error_handler(_: Request, exc: RateWatchError):
    return format_error_response(exc)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return format_error_response(INVALID_PAIR_FORMAT.with_message(str(exc)))


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
