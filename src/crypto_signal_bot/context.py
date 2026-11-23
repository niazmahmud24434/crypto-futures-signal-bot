"""Broader market regime and closed-candle confirmation rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from .indicators import add_indicators


class MarketRegime(StrEnum):
    UP = "UP"
    HOLD = "HOLD"
    DOWN = "DOWN"


@dataclass(frozen=True, slots=True)
class MarketContext:
    regime: MarketRegime
    confidence: int
    timeframe: str
    reasons: tuple[str, ...]


def market_context(btc_candles: pd.DataFrame, timeframe: str = "1h/4h") -> MarketContext:
    """Classify the broad BTC regime using closed-candle trend and participation."""

    frame = add_indicators(btc_candles)
    if len(frame) < 60:
        return MarketContext(MarketRegime.HOLD, 0, timeframe, ("Insufficient closed BTC candles",))
    row = frame.iloc[-1]
    bullish = 0
    bearish = 0
    reasons: list[str] = []
    if row["ema_9"] > row["ema_21"] > row["ema_50"]:
        bullish += 1
        reasons.append("BTC EMA alignment bullish")
    elif row["ema_9"] < row["ema_21"] < row["ema_50"]:
        bearish += 1
        reasons.append("BTC EMA alignment bearish")
    if row["macd_hist"] > 0:
        bullish += 1
        reasons.append("BTC MACD positive")
    elif row["macd_hist"] < 0:
        bearish += 1
        reasons.append("BTC MACD negative")
    if row["rsi_14"] >= 55:
        bullish += 1
        reasons.append("BTC RSI supports upside")
    elif row["rsi_14"] <= 45:
        bearish += 1
        reasons.append("BTC RSI supports downside")
    if row["volume_ratio"] >= 1:
        reasons.append("BTC volume is not below its average")
    score = max(bullish, bearish)
    if bullish >= 2 and bullish > bearish:
        return MarketContext(MarketRegime.UP, min(95, 50 + score * 15), timeframe, tuple(reasons))
    if bearish >= 2 and bearish > bullish:
        return MarketContext(MarketRegime.DOWN, min(95, 50 + score * 15), timeframe, tuple(reasons))
    return MarketContext(
        MarketRegime.HOLD, 50, timeframe, tuple(reasons) or ("Mixed market evidence",)
    )


def candlestick_patterns(candles: pd.DataFrame) -> tuple[str, ...]:
    """Identify objective patterns on the last closed candles.

    These are original rule implementations; they are confirmation features,
    not standalone trade recommendations.
    """

    if len(candles) < 3:
        return ()
    previous = candles.iloc[-2]
    current = candles.iloc[-1]
    prior = candles.iloc[-3]
    body = abs(float(current["close"]) - float(current["open"]))
    candle_range = float(current["high"]) - float(current["low"])
    if candle_range <= 0:
        return ()
    upper_wick = float(current["high"]) - max(float(current["open"]), float(current["close"]))
    lower_wick = min(float(current["open"]), float(current["close"])) - float(current["low"])
    patterns: list[str] = []
    previous_body_high = max(float(previous["open"]), float(previous["close"]))
    previous_body_low = min(float(previous["open"]), float(previous["close"]))
    previous_body = abs(float(previous["close"]) - float(previous["open"]))
    current_body_high = max(float(current["open"]), float(current["close"]))
    current_body_low = min(float(current["open"]), float(current["close"]))
    previous_bearish = float(previous["close"]) < float(previous["open"])
    previous_bullish = float(previous["close"]) > float(previous["open"])
    current_bullish = float(current["close"]) > float(current["open"])
    current_bearish = float(current["close"]) < float(current["open"])
    if lower_wick >= max(body * 2, candle_range * 0.45) and upper_wick <= candle_range * 0.2:
        patterns.append("hammer")
    if upper_wick >= max(body * 2, candle_range * 0.45) and lower_wick <= candle_range * 0.2:
        patterns.append("shooting_star")
    if (
        previous_bearish
        and current_bullish
        and current_body_low <= previous_body_low
        and current_body_high >= previous_body_high
    ):
        patterns.append("bullish_engulfing")
    if (
        previous_bullish
        and current_bearish
        and current_body_low <= previous_body_low
        and current_body_high >= previous_body_high
    ):
        patterns.append("bearish_engulfing")
    if body <= candle_range * 0.1:
        patterns.append("doji")
    prior_bearish = float(prior["close"]) < float(prior["open"])
    prior_bullish = float(prior["close"]) > float(prior["open"])
    if (
        prior_bearish
        and previous_body <= abs(float(prior["close"]) - float(prior["open"])) * 0.6
        and current_bullish
    ):
        patterns.append("morning_star_candidate")
    if (
        prior_bullish
        and previous_body <= abs(float(prior["close"]) - float(prior["open"])) * 0.6
        and current_bearish
    ):
        patterns.append("evening_star_candidate")
    return tuple(patterns)
