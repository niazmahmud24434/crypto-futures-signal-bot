"""Multi-timeframe, confirmation-based signal strategy."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from .indicators import add_indicators
from .models import Side, Signal

#: Risk model, expressed in ATR multiples. Entry zone is centred on the close.
STOP_ATR = 1.3
TP1_ATR = 2.0
TP2_ATR = 4.0

#: Sanity bounds for ATR as a fraction of price, to reject broken or thin data.
MIN_ATR_FRACTION = 0.0002
MAX_ATR_FRACTION = 0.20


def _latest(frame: pd.DataFrame) -> pd.Series:
    if len(frame) < 60:
        raise ValueError("at least 60 candles are required for EMA 50 and confirmation")
    return frame.iloc[-1]


def _candle_time(row: pd.Series) -> datetime | None:
    value = row.get("open_time")
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return None


def _directional_reasons(entry: pd.Series, confirm: pd.Series) -> tuple[list[str], list[str]]:
    long_reasons: list[str] = []
    short_reasons: list[str] = []

    if entry["ema_9"] > entry["ema_21"] > entry["ema_50"]:
        long_reasons.append("15m EMA 9/21/50 bullish alignment")
    if entry["ema_9"] < entry["ema_21"] < entry["ema_50"]:
        short_reasons.append("15m EMA 9/21/50 bearish alignment")

    if entry["rsi_14"] >= 55:
        long_reasons.append(f"15m RSI {entry['rsi_14']:.1f} supports upside")
    if entry["rsi_14"] <= 45:
        short_reasons.append(f"15m RSI {entry['rsi_14']:.1f} supports downside")

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

    return long_reasons, short_reasons


def build_signal(
    pair: str,
    entry_candles: pd.DataFrame,
    confirmation_candles: pd.DataFrame,
    min_score: int = 3,
    market_regime: str = "HOLD",
) -> Signal | None:
    """Build a signal from closed 15m candles and closed 1h confirmation candles.

    Candles are supplied by the caller and are never re-requested here, so the
    same function serves live scanning and historical backtests without drift.
    """

    entry = _latest(add_indicators(entry_candles))
    confirm = _latest(add_indicators(confirmation_candles))

    atr = float(entry["atr_14"])
    price = float(entry["close"])
    if pd.isna(atr) or atr <= 0 or price <= 0:
        return None
    if not MIN_ATR_FRACTION * price <= atr <= MAX_ATR_FRACTION * price:
        return None

    long_reasons, short_reasons = _directional_reasons(entry, confirm)

    if len(long_reasons) >= min_score and len(long_reasons) > len(short_reasons):
        side, reasons = Side.LONG, tuple(long_reasons)
        stop = price - STOP_ATR * atr
        tp1, tp2 = price + TP1_ATR * atr, price + TP2_ATR * atr
    elif len(short_reasons) >= min_score and len(short_reasons) > len(long_reasons):
        side, reasons = Side.SHORT, tuple(short_reasons)
        stop = price + STOP_ATR * atr
        tp1, tp2 = price - TP1_ATR * atr, price - TP2_ATR * atr
    else:
        return None

    created_at = datetime.now(UTC)
    return Signal(
        pair=pair.upper(),
        side=side,
        timeframe="15m entry / 1h confirmation",
        created_at=created_at,
        entry_low=price - 0.25 * atr,
        entry_high=price + 0.25 * atr,
        stop_loss=stop,
        take_profit_1=tp1,
        take_profit_2=tp2,
        score=len(reasons),
        reasons=reasons,
        candle_open_time=_candle_time(entry),
        market_regime=str(market_regime),
    )
