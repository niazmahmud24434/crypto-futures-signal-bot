"""Shared deterministic fixtures for offline tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

FIXED_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

INTERVAL_MINUTES = {"15m": 15, "1h": 60, "4h": 240}


def make_candles(
    count: int = 200,
    start: float = 100.0,
    slope: float = 0.5,
    interval: str = "15m",
    end: datetime = FIXED_NOW,
) -> pd.DataFrame:
    """Build closed candles that end one bar before ``end``."""

    minutes = INTERVAL_MINUTES[interval]
    close = start + np.arange(count, dtype=float) * slope
    span = np.maximum(np.abs(slope) * 0.6, np.abs(close) * 0.002)
    open_time = [end - timedelta(minutes=minutes * (count - index)) for index in range(count)]
    return pd.DataFrame(
        {
            "open_time": pd.to_datetime(open_time, utc=True),
            "open": close,
            "high": close + span,
            "low": close - span,
            "close": close,
            "volume": [200.0] * count,
            "close_time": pd.to_datetime(open_time, utc=True)
            + pd.Timedelta(minutes=minutes)
            - pd.Timedelta(milliseconds=1),
        }
    )


class FakeBinance:
    """Deterministic public-data stand-in; it has no account or order surface."""

    def __init__(
        self,
        slopes: dict[str, float] | None = None,
        default_slope: float = 0.5,
        now: datetime = FIXED_NOW,
    ) -> None:
        self.slopes = slopes or {}
        self.default_slope = default_slope
        self.now = now
        self.calls: list[tuple[str, str]] = []

    def klines(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        self.calls.append((symbol, interval))
        slope = self.slopes.get(symbol.upper(), self.default_slope)
        start = 100.0 if slope >= 0 else 400.0
        return make_candles(
            count=min(limit, 200), start=start, slope=slope, interval=interval, end=self.now
        )

    def klines_history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
        pause_seconds: float | None = None,
    ) -> pd.DataFrame:
        minutes = INTERVAL_MINUTES[interval]
        stop = end or self.now
        count = max(60, int((stop - start).total_seconds() // 60 // minutes))
        slope = self.slopes.get(symbol.upper(), self.default_slope)
        origin = 100.0 if slope >= 0 else 100.0 + abs(slope) * count
        return make_candles(count=count, start=origin, slope=slope, interval=interval, end=stop)

    def top_usdt_pairs(self, limit: int = 20, excluded_bases: tuple[str, ...] = ()) -> list[str]:
        return []
