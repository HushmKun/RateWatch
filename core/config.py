from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import TRACKED_PAIRS


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./ratewatch.db"
    redis_url: str = "redis://localhost:6379/0"

    openexchange_app_id: str = ""
    currencyapi_key: str = ""

    poll_interval_seconds: int = 30
    poll_concurrency_limit: int = 20

    ttl_map: dict[str, int] = Field(
        default_factory=lambda: {
            "CRYPTO": 10,
            "MAJOR": 30,
            "MINOR": 60,
            "EXOTIC": 300,
        }
    )

    outlier_std_threshold: float = 2.0
    min_sources_required: int = 2
    source_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "ecb": 1.0,
            "frankfurter": 0.9,
            "openexchange": 0.85,
            "currencyapi": 0.85,
        }
    )

    tracked_pairs: list[str] = Field(default_factory=lambda: TRACKED_PAIRS.copy())

    api_prefix: str = "/api"
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
