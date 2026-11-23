import numpy as np
import pandas as pd

from crypto_signal_bot.config import Settings
from crypto_signal_bot.scanner import scan_pair


class FakeClient:
    def klines(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        close = 100 + np.arange(100, dtype=float)
        return pd.DataFrame(
            {
                "open_time": pd.date_range("2026-01-01", periods=100, freq="15min", tz="UTC"),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": [200.0] * 100,
                "close_time": pd.date_range(
                    "2026-01-01 00:14", periods=100, freq="15min", tz="UTC"
                ),
            }
        )


def test_scanner_reports_pair_without_private_credentials() -> None:
    result = scan_pair(FakeClient(), "BTCUSDT", Settings())
    assert result.error is None
    assert result.signal is not None
