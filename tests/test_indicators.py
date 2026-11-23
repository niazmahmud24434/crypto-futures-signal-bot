import pandas as pd

from crypto_signal_bot.indicators import add_indicators


def test_indicators_add_expected_columns() -> None:
    candles = pd.DataFrame(
        {
            "open": range(1, 81),
            "high": range(2, 82),
            "low": range(1, 81),
            "close": range(1, 81),
            "volume": [100.0] * 80,
        }
    )
    result = add_indicators(candles)
    for column in ("ema_9", "ema_21", "ema_50", "rsi_14", "macd_hist", "atr_14", "volume_ratio"):
        assert column in result
    assert len(result) == len(candles)
