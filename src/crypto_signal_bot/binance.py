"""Read-only Binance USDⓈ-M Futures public market-data client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pandas as pd


class BinanceDataError(RuntimeError):
    """Raised when public market data cannot be trusted or retrieved."""


@dataclass(frozen=True, slots=True)
class BinancePublicClient:
    base_url: str = "https://fapi.binance.com"
    timeout_seconds: float = 20.0

    def _get(self, path: str, params: dict[str, object] | None = None) -> object:
        try:
            response = httpx.get(
                f"{self.base_url.rstrip('/')}{path}",
                params=params,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "crypto-futures-signal-bot/0.1"},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BinanceDataError(f"Binance public data request failed: {path}") from exc

    def klines(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        """Return closed and forming candles; callers must drop the last row."""

        if not 1 <= limit <= 1500:
            raise ValueError("limit must be between 1 and 1500")
        raw = self._get(
            "/fapi/v1/klines", {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        )
        if not isinstance(raw, list):
            raise BinanceDataError("Binance returned an unexpected kline response")
        columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trade_count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ]
        frame = pd.DataFrame(raw, columns=columns)
        for column in ("open", "high", "low", "close", "volume"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
        frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
        return frame

    def ticker_24h(self) -> list[dict[str, object]]:
        raw = self._get("/fapi/v1/ticker/24hr")
        if not isinstance(raw, list):
            raise BinanceDataError("Binance returned an unexpected ticker response")
        return [item for item in raw if isinstance(item, dict)]

    def top_usdt_pairs(self, limit: int = 20) -> list[str]:
        """Choose liquid USDT perpetuals without any private account access."""

        pairs: list[tuple[str, float]] = []
        for item in self.ticker_24h():
            symbol = str(item.get("symbol", ""))
            if not symbol.endswith("USDT") or not bool(item.get("symbol")):
                continue
            try:
                quote_volume = float(item.get("quoteVolume", 0))
            except (TypeError, ValueError):
                continue
            pairs.append((symbol, quote_volume))
        return [
            symbol for symbol, _ in sorted(pairs, key=lambda pair: pair[1], reverse=True)[:limit]
        ]


def drop_forming_candle(frame: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    """Keep only candles whose close time has passed."""

    current = now or datetime.now(UTC)
    return frame.loc[frame["close_time"] <= current].copy()
