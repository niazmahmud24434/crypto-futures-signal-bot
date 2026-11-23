"""Read-only Binance USDⓈ-M Futures public market-data client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd

INTERVAL_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "8h": 480,
    "12h": 720,
    "1d": 1440,
}

KLINE_COLUMNS = [
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


class BinanceDataError(RuntimeError):
    """Raised when public market data cannot be trusted or retrieved."""


def interval_minutes(interval: str) -> int:
    try:
        return INTERVAL_MINUTES[interval]
    except KeyError as exc:
        raise ValueError(f"unsupported interval: {interval}") from exc


def frame_from_klines(raw: list[list[object]]) -> pd.DataFrame:
    frame = pd.DataFrame(raw, columns=KLINE_COLUMNS)
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
    return frame


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
        return frame_from_klines(raw)

    def klines_history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
        pause_seconds: float = 0.15,
    ) -> pd.DataFrame:
        """Page historical klines forward from ``start`` to ``end``.

        Binance caps a response at 1500 candles, so multi-week 15m history needs
        several requests. Rows are de-duplicated and sorted by open time.
        """

        minutes = interval_minutes(interval)
        stop = end or datetime.now(UTC)
        cursor = start.astimezone(UTC)
        frames: list[pd.DataFrame] = []
        while cursor < stop:
            raw = self._get(
                "/fapi/v1/klines",
                {
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "startTime": int(cursor.timestamp() * 1000),
                    "endTime": int(stop.timestamp() * 1000),
                    "limit": 1500,
                },
            )
            if not isinstance(raw, list) or not raw:
                break
            chunk = frame_from_klines(raw)
            frames.append(chunk)
            last_open = chunk.iloc[-1]["open_time"].to_pydatetime()
            if last_open <= cursor:
                break
            cursor = last_open + timedelta(minutes=minutes)
            if len(raw) < 1500:
                break
            time.sleep(pause_seconds)
        if not frames:
            return frame_from_klines([])
        combined = (
            pd.concat(frames, ignore_index=True)
            .drop_duplicates(subset="open_time")
            .sort_values("open_time")
            .reset_index(drop=True)
        )
        return combined

    def ticker_24h(self) -> list[dict[str, object]]:
        raw = self._get("/fapi/v1/ticker/24hr")
        if not isinstance(raw, list):
            raise BinanceDataError("Binance returned an unexpected ticker response")
        return [item for item in raw if isinstance(item, dict)]

    def exchange_info(self) -> dict[str, dict[str, object]]:
        """Symbol metadata, including the authoritative underlying asset class."""

        raw = self._get("/fapi/v1/exchangeInfo")
        if not isinstance(raw, dict) or not isinstance(raw.get("symbols"), list):
            raise BinanceDataError("Binance returned an unexpected exchange-info response")
        return {
            str(item.get("symbol")): item
            for item in raw["symbols"]
            if isinstance(item, dict) and item.get("symbol")
        }

    def crypto_usdt_perpetuals(self) -> set[str]:
        """Tradable crypto USDT perpetuals, excluding tokenized TradFi products.

        Binance tags crypto contracts with ``underlyingType: COIN``. Tokenized
        equities and commodities use ``TRADIFI_PERPETUAL`` contracts with
        ``EQUITY``, ``COMMODITY`` or ``INDEX`` underlyings, so filtering on the
        published metadata is safer than maintaining a name blacklist.
        """

        return {
            symbol
            for symbol, item in self.exchange_info().items()
            if str(item.get("contractType")) == "PERPETUAL"
            and str(item.get("quoteAsset")) == "USDT"
            and str(item.get("status")) == "TRADING"
            and str(item.get("underlyingType", "COIN")) == "COIN"
        }

    def top_usdt_pairs(
        self,
        limit: int = 20,
        excluded_bases: tuple[str, ...] = (),
        crypto_only: bool = True,
    ) -> list[str]:
        """Choose liquid USDT perpetuals without any private account access."""

        allowed: set[str] | None = None
        if crypto_only:
            try:
                allowed = self.crypto_usdt_perpetuals()
            except BinanceDataError:
                allowed = None

        excluded = {base.upper() for base in excluded_bases}
        pairs: list[tuple[str, float]] = []
        for item in self.ticker_24h():
            symbol = str(item.get("symbol", ""))
            if not symbol.endswith("USDT"):
                continue
            if symbol[:-4] in excluded:
                continue
            if allowed is not None and symbol not in allowed:
                continue
            try:
                quote_volume = float(item.get("quoteVolume", 0))  # type: ignore[arg-type]
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
