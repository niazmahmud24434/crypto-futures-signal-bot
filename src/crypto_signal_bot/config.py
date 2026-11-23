"""Validated application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings; exchange trading credentials are excluded by design."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: int = 9282726837
    telegram_allow_other_chats: bool = False

    binance_futures_base_url: str = "https://fapi.binance.com"
    request_timeout_seconds: float = 20.0
    request_pause_seconds: float = 0.15

    min_signal_score: int = 3
    entry_timeframe: str = "15m"
    confirmation_timeframe: str = "1h"
    regime_timeframe: str = "4h"
    max_candle_age_bars: int = 3

    block_counter_trend: bool = True
    signal_cooldown_minutes: int = 180
    top_volume_limit: int = 20
    crypto_only_universe: bool = True

    journal_path: Path = Path("data/signals.sqlite3")
    report_directory: Path = Path("reports")

    backtest_forward_bars: int = 96
    time_machine_days: int = 30

    pairs: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "TAOUSDT", "LINKUSDT")
    excluded_top_volume_bases: tuple[str, ...] = (
        "NVDA",
        "SOXL",
        "SOXS",
        "XAU",
        "XAG",
        "QQQ",
        "SPX",
        "SPY",
        "MU",
        "ANT",
        "CL",
        "SPCX",
        "SKHYNIX",
        "SKHY",
        "KORU",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
