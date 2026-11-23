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


#: Directional weight of each independently implemented pattern. Patterns are a
#: double-check layer only; no pattern can create a signal on its own.
PATTERN_BIAS: dict[str, int] = {
    "hammer": 1,
    "bullish_engulfing": 1,
    "morning_star_candidate": 1,
    "shooting_star": -1,
    "bearish_engulfing": -1,
    "evening_star_candidate": -1,
    "doji": 0,
}


def _evidence(frame: pd.DataFrame, label: str) -> tuple[int, int, list[str]]:
    """Return bullish and bearish evidence counts for one closed-candle frame."""

    row = frame.iloc[-1]
    bullish = bearish = 0
    reasons: list[str] = []
    if row["ema_9"] > row["ema_21"] > row["ema_50"]:
        bullish += 1
        reasons.append(f"BTC {label} EMA alignment bullish")
    elif row["ema_9"] < row["ema_21"] < row["ema_50"]:
        bearish += 1
        reasons.append(f"BTC {label} EMA alignment bearish")
    if row["macd_hist"] > 0:
        bullish += 1
        reasons.append(f"BTC {label} MACD positive")
    elif row["macd_hist"] < 0:
        bearish += 1
        reasons.append(f"BTC {label} MACD negative")
    if row["rsi_14"] >= 55:
        bullish += 1
        reasons.append(f"BTC {label} RSI supports upside")
    elif row["rsi_14"] <= 45:
        bearish += 1
        reasons.append(f"BTC {label} RSI supports downside")
    return bullish, bearish, reasons


def market_context(
    btc_candles: pd.DataFrame,
    btc_candles_4h: pd.DataFrame | None = None,
    timeframe: str = "1h/4h",
    *,
    prepared: bool = False,
) -> MarketContext:
    """Classify the broad BTC regime from closed 1h and, when supplied, 4h candles.

    The regime describes measured conditions. It is not a forecast, and it never
    replaces the pair-level confirmation checks. ``prepared=True`` skips indicator
    calculation; the caller must have run :func:`add_indicators` already.
    """

    frame_1h = btc_candles if prepared else add_indicators(btc_candles)
    if len(frame_1h) < 60:
        return MarketContext(
            MarketRegime.HOLD, 0, timeframe, ("Insufficient closed 1h BTC candles",)
        )

    bullish_1h, bearish_1h, reasons = _evidence(frame_1h, "1h")

    frame_4h = None
    if btc_candles_4h is not None:
        frame_4h = btc_candles_4h if prepared else add_indicators(btc_candles_4h)
    if frame_4h is None or len(frame_4h) < 60:
        reasons.append("4h trend unavailable; regime uses 1h only")
        score = max(bullish_1h, bearish_1h)
        if bullish_1h >= 2 and bullish_1h > bearish_1h:
            return MarketContext(
                MarketRegime.UP, min(90, 45 + score * 15), timeframe, tuple(reasons)
            )
        if bearish_1h >= 2 and bearish_1h > bullish_1h:
            return MarketContext(
                MarketRegime.DOWN, min(90, 45 + score * 15), timeframe, tuple(reasons)
            )
        return MarketContext(
            MarketRegime.HOLD, 50, timeframe, tuple(reasons) or ("Mixed market evidence",)
        )

    bullish_4h, bearish_4h, reasons_4h = _evidence(frame_4h, "4h")
    reasons.extend(reasons_4h)

    if bullish_1h >= 2 and bullish_4h >= 2 and bullish_1h > bearish_1h and bullish_4h > bearish_4h:
        confidence = min(95, 40 + (bullish_1h + bullish_4h) * 10)
        return MarketContext(MarketRegime.UP, confidence, timeframe, tuple(reasons))
    if bearish_1h >= 2 and bearish_4h >= 2 and bearish_1h > bullish_1h and bearish_4h > bullish_4h:
        confidence = min(95, 40 + (bearish_1h + bearish_4h) * 10)
        return MarketContext(MarketRegime.DOWN, confidence, timeframe, tuple(reasons))
    reasons.append("BTC 1h and 4h trends do not agree")
    return MarketContext(MarketRegime.HOLD, 50, timeframe, tuple(reasons))


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


def pattern_bias(patterns: tuple[str, ...]) -> int:
    """Sum directional pattern weights; zero means neutral or no patterns."""

    return sum(PATTERN_BIAS.get(pattern, 0) for pattern in patterns)


def pattern_conflicts(patterns: tuple[str, ...], side: str) -> bool:
    """Return True when closed-candle patterns oppose the requested side."""

    bias = pattern_bias(patterns)
    if str(side).upper() == "LONG":
        return bias < 0
    return bias > 0


def pattern_label(patterns: tuple[str, ...], side: str) -> str:
    """Human-readable pattern verdict used in the confirmation section."""

    bias = pattern_bias(patterns)
    if not patterns:
        return "no classic pattern on the last closed candle"
    aligned = (str(side).upper() == "LONG" and bias > 0) or (
        str(side).upper() == "SHORT" and bias < 0
    )
    verdict = "aligned" if aligned else "neutral" if bias == 0 else "conflicting"
    return f"{', '.join(patterns)} ({verdict})"
