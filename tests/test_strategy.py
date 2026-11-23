import numpy as np
import pandas as pd

from crypto_signal_bot.models import Side
from crypto_signal_bot.strategy import build_signal


def _candles(start: float, count: int = 100, slope: float = 1.0) -> pd.DataFrame:
    close = start + np.arange(count) * slope
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": [200.0] * count,
        }
    )


def test_bullish_alignment_can_create_long_signal() -> None:
    signal = build_signal("BTCUSDT", _candles(100), _candles(100), min_score=3)
    assert signal is not None
    assert signal.side is Side.LONG
    assert signal.stop_loss < signal.entry_low < signal.take_profit_1
