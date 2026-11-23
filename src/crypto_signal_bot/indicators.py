"""Pure pandas indicator calculations used by the signal engine."""

import pandas as pd


def add_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with EMA, RSI, MACD, ATR, and volume features."""

    frame = candles.copy()
    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    frame["ema_9"] = close.ewm(span=9, adjust=False).mean()
    frame["ema_21"] = close.ewm(span=21, adjust=False).mean()
    frame["ema_50"] = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    relative_strength = gain / loss.replace(0, float("nan"))
    frame["rsi_14"] = (100 - (100 / (1 + relative_strength))).fillna(100.0)

    macd_fast = close.ewm(span=12, adjust=False).mean()
    macd_slow = close.ewm(span=26, adjust=False).mean()
    frame["macd"] = macd_fast - macd_slow
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()
    frame["macd_hist"] = frame["macd"] - frame["macd_signal"]

    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    frame["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    frame["volume_sma_20"] = frame["volume"].rolling(20).mean()
    frame["volume_ratio"] = frame["volume"] / frame["volume_sma_20"]
    return frame
