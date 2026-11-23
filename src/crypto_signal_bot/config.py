"""Validated application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings; exchange trading credentials are excluded by design."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: int = 9282726837
    binance_futures_base_url: str = "https://fapi.binance.com"
    request_timeout_seconds: float = 20.0
    request_pause_seconds: float = 0.15
    min_signal_score: int = 3
    entry_timeframe: str = "15m"
    confirmation_timeframe: str = "1h"

    pairs: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "TAOUSDT", "LINKUSDT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
