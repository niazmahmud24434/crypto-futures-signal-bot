"""Read-only scanner orchestration for configured Binance Futures pairs."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .binance import BinancePublicClient, drop_forming_candle
from .config import Settings
from .context import MarketContext, candlestick_patterns, market_context
from .models import Signal
from .strategy import build_signal


@dataclass(frozen=True, slots=True)
class PairScan:
    pair: str
    signal: Signal | None
    patterns: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ScanReport:
    market: MarketContext
    pairs: tuple[PairScan, ...]


def _closed(
    client: BinancePublicClient, pair: str, interval: str, limit: int = 250
) -> pd.DataFrame:
    return drop_forming_candle(client.klines(pair, interval, limit))


def scan_pair(client: BinancePublicClient, pair: str, settings: Settings) -> PairScan:
    """Scan one pair and convert data errors into an auditable result."""

    try:
        entry = _closed(client, pair, settings.entry_timeframe)
        confirmation = _closed(client, pair, settings.confirmation_timeframe)
        signal = build_signal(pair, entry, confirmation, settings.min_signal_score)
        return PairScan(pair, signal, candlestick_patterns(entry))
    except Exception as exc:  # noqa: BLE001 - scanner must report per-pair failures
        return PairScan(pair, None, (), str(exc))


def scan(client: BinancePublicClient, settings: Settings) -> ScanReport:
    """Build a report, keeping the market context separate from pair results."""

    btc_confirmation = _closed(client, "BTCUSDT", settings.confirmation_timeframe)
    market = market_context(btc_confirmation)
    pairs = list(settings.pairs)
    for pair in client.top_usdt_pairs(limit=20):
        if pair not in pairs:
            pairs.append(pair)
    results = tuple(scan_pair(client, pair, settings) for pair in pairs)
    return ScanReport(market, results)
