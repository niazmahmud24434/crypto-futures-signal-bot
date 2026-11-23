"""Multi-timeframe, confirmation-based signal strategy."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from .indicators import add_indicators
from .models import Side, Signal


def _latest(frame: pd.DataFrame) -> pd.Series:
    if len(frame) < 60:
        raise ValueError("at least 60 candles are required for EMA 50 and confirmation")
    return frame.iloc[-1]


def build_signal(
    pair: str,
    entry_candles: pd.DataFrame,
    confirmation_candles: pd.DataFrame,
    min_score: int = 3,
) -> Signal | None:
    """Build a signal from closed 15m candles and closed 1h confirmation candles."""

    entry = _latest(add_indicators(entry_candles))
    confirm = _latest(add_indicators(confirmation_candles))
    atr = float(entry["atr_14"])
    if pd.isna(atr) or atr <= 0:
        return None

    long_reasons: list[str] = []
    short_reasons: list[str] = []
    if entry["ema_9"] > entry["ema_21"] > entry["ema_50"]:
        long_reasons.append("15m EMA 9/21/50 bullish alignment")
    if entry["ema_9"] < entry["ema_21"] < entry["ema_50"]:
        short_reasons.append("15m EMA 9/21/50 bearish alignment")
    if entry["rsi_14"] >= 50:
        long_reasons.append("15m RSI above 50")
    if entry["rsi_14"] <= 50:
        short_reasons.append("15m RSI below 50")
    if entry["macd_hist"] > 0:
        long_reasons.append("15m MACD histogram positive")
    if entry["macd_hist"] < 0:
        short_reasons.append("15m MACD histogram negative")
    if entry["volume_ratio"] >= 1:
        long_reasons.append("15m volume at or above 20-candle average")
        short_reasons.append("15m volume at or above 20-candle average")
    if confirm["ema_9"] > confirm["ema_21"] > confirm["ema_50"]:
        long_reasons.append("1h trend confirmation bullish")
    if confirm["ema_9"] < confirm["ema_21"] < confirm["ema_50"]:
        short_reasons.append("1h trend confirmation bearish")

    if len(long_reasons) >= min_score and len(long_reasons) > len(short_reasons):
        side, reasons = Side.LONG, tuple(long_reasons)
        entry_price = float(entry["close"])
        stop = entry_price - 1.5 * atr
        tp1, tp2 = entry_price + 1.5 * atr, entry_price + 3 * atr
    elif len(short_reasons) >= min_score and len(short_reasons) > len(long_reasons):
        side, reasons = Side.SHORT, tuple(short_reasons)
        entry_price = float(entry["close"])
        stop = entry_price + 1.5 * atr
        tp1, tp2 = entry_price - 1.5 * atr, entry_price - 3 * atr
    else:
        return None

    return Signal(
        pair=pair.upper(),
        side=side,
        timeframe="15m/1h",
        created_at=datetime.now(UTC),
        entry_low=entry_price - 0.25 * atr,
        entry_high=entry_price + 0.25 * atr,
        stop_loss=stop,
        take_profit_1=tp1,
        take_profit_2=tp2,
        score=len(reasons),
        reasons=reasons,
    )
