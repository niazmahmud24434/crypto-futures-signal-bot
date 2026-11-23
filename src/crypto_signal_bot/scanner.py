"""Read-only scanner orchestration for Binance USDT perpetual futures."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pandas as pd

from .binance import BinanceDataError, BinancePublicClient, drop_forming_candle
from .config import Settings
from .context import (
    MarketContext,
    MarketRegime,
    candlestick_patterns,
    market_context,
    pattern_conflicts,
    pattern_label,
)
from .models import Side, Signal
from .strategy import build_signal

_INTERVAL_MINUTES: dict[str, int] = {
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


@dataclass(frozen=True, slots=True)
class PairScan:
    pair: str
    signal: Signal | None
    patterns: tuple[str, ...]
    blocked: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ScanReport:
    market: MarketContext
    pairs: tuple[PairScan, ...]

    @property
    def signals(self) -> tuple[PairScan, ...]:
        return tuple(item for item in self.pairs if item.signal is not None)

    @property
    def blocked(self) -> tuple[PairScan, ...]:
        return tuple(item for item in self.pairs if item.blocked is not None)

    @property
    def errors(self) -> tuple[PairScan, ...]:
        return tuple(item for item in self.pairs if item.error is not None)


def _closed(
    client: BinancePublicClient,
    pair: str,
    interval: str,
    max_age_bars: int = 3,
    limit: int = 250,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Return closed candles, rejecting stale or empty responses."""

    frame = drop_forming_candle(client.klines(pair, interval, limit), now=now)
    if len(frame) < 60:
        raise BinanceDataError(f"{pair} {interval}: not enough closed candles")
    minutes = _INTERVAL_MINUTES.get(interval)
    if minutes is not None:
        last_close = frame.iloc[-1]["close_time"]
        current = now or datetime.now(UTC)
        if last_close.tzinfo is None:
            last_close = last_close.tz_localize(UTC)
        age_minutes = (current - last_close.to_pydatetime()).total_seconds() / 60
        if age_minutes > minutes * max_age_bars:
            raise BinanceDataError(f"{pair} {interval}: last closed candle is stale")
    return frame


def _gate(signal: Signal, market: MarketContext | None, settings: Settings) -> str | None:
    """Return a human-readable block reason, or None when the idea may alert."""

    if market is None:
        return None
    if settings.block_counter_trend:
        if market.regime is MarketRegime.UP and signal.side is Side.SHORT:
            return f"counter-trend short against market {market.regime.value}"
        if market.regime is MarketRegime.DOWN and signal.side is Side.LONG:
            return f"counter-trend long against market {market.regime.value}"
    if market.regime is MarketRegime.HOLD and signal.score < settings.min_signal_score + 1:
        return "market HOLD needs one extra confirmation"
    return None


def scan_pair(
    client: BinancePublicClient,
    pair: str,
    settings: Settings,
    market: MarketContext | None = None,
    now: datetime | None = None,
) -> PairScan:
    """Scan one pair and convert data errors into an auditable result."""

    try:
        entry = _closed(
            client, pair, settings.entry_timeframe, settings.max_candle_age_bars, now=now
        )
        confirmation = _closed(
            client, pair, settings.confirmation_timeframe, settings.max_candle_age_bars, now=now
        )
        patterns = candlestick_patterns(entry)
        signal = build_signal(
            pair,
            entry,
            confirmation,
            settings.min_signal_score,
            market_regime=market.regime.value if market else "HOLD",
        )
    except Exception as exc:  # noqa: BLE001 - scanner must report per-pair failures
        return PairScan(pair, None, (), error=str(exc))

    if signal is None:
        return PairScan(pair, None, patterns)

    blocked = _gate(signal, market, settings)
    if blocked:
        return PairScan(pair, None, patterns, blocked=blocked)

    if pattern_conflicts(patterns, signal.side.value):
        return PairScan(
            pair,
            None,
            patterns,
            blocked=f"candlestick conflict: {', '.join(patterns)}",
        )

    if patterns and pattern_label(patterns, signal.side.value).endswith("(aligned)"):
        signal = replace(
            signal,
            reasons=(*signal.reasons, f"Candlestick double-check: {', '.join(patterns)}"),
            patterns=patterns,
        )
    else:
        signal = replace(signal, patterns=patterns)
    return PairScan(pair, signal, patterns)


def scan(
    client: BinancePublicClient,
    settings: Settings,
    now: datetime | None = None,
) -> ScanReport:
    """Build a report, keeping the market context separate from pair results."""

    btc_1h = _closed(
        client, "BTCUSDT", settings.confirmation_timeframe, settings.max_candle_age_bars, now=now
    )
    btc_4h = None
    if settings.regime_timeframe:
        try:
            btc_4h = _closed(
                client, "BTCUSDT", settings.regime_timeframe, settings.max_candle_age_bars, now=now
            )
        except BinanceDataError:
            btc_4h = None
    market = market_context(btc_1h, btc_4h)

    pairs = list(settings.pairs)
    if settings.top_volume_limit > 0:
        try:
            discovered = client.top_usdt_pairs(
                limit=settings.top_volume_limit,
                excluded_bases=settings.excluded_top_volume_bases,
                crypto_only=settings.crypto_only_universe,
            )
        except BinanceDataError:
            discovered = []
        for pair in discovered:
            if pair not in pairs:
                pairs.append(pair)

    results: list[PairScan] = []
    for pair in pairs:
        results.append(scan_pair(client, pair, settings, market, now=now))
        time.sleep(settings.request_pause_seconds)
    return ScanReport(market, tuple(results))
