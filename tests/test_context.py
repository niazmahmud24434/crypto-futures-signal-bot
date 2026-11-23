import numpy as np
import pandas as pd

from crypto_signal_bot.context import MarketRegime, candlestick_patterns, market_context


def _trend(count: int = 100, slope: float = 1.0) -> pd.DataFrame:
    close = 100 + np.arange(count) * slope
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": [200.0] * count,
        }
    )


def test_btc_rising_trend_is_up() -> None:
    result = market_context(_trend())
    assert result.regime is MarketRegime.UP
    assert result.confidence > 50


def test_bullish_engulfing_is_detected() -> None:
    frame = pd.DataFrame(
        {
            "open": [102, 101, 99],
            "high": [103, 102, 105],
            "low": [99, 98, 98],
            "close": [100, 99, 104],
            "volume": [100, 100, 200],
        }
    )
    assert "bullish_engulfing" in candlestick_patterns(frame)
