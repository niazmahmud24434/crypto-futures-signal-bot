import pandas as pd
import pytest

from conftest import FIXED_NOW, FakeBinance, make_candles
from crypto_signal_bot.config import Settings
from crypto_signal_bot.context import MarketRegime, market_context
from crypto_signal_bot.scanner import scan, scan_pair


def test_scanner_reports_pair_without_private_credentials() -> None:
    settings = Settings(pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0)
    result = scan_pair(FakeBinance(), "BTCUSDT", settings, now=FIXED_NOW)
    assert result.error is None
    assert result.signal is not None
    assert result.signal.pair == "BTCUSDT"
    assert result.signal.candle_open_time is not None


def test_stale_candles_are_rejected() -> None:
    settings = Settings(pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0)
    stale_now = FIXED_NOW + pd.Timedelta(days=2)
    result = scan_pair(FakeBinance(), "BTCUSDT", settings, now=stale_now)
    assert result.signal is None
    assert result.error is not None
    assert "stale" in result.error


def test_counter_trend_short_is_blocked_when_market_is_up() -> None:
    settings = Settings(pairs=("BTCUSDT", "ETHUSDT"), request_pause_seconds=0, top_volume_limit=0)
    client = FakeBinance(slopes={"BTCUSDT": 0.5, "ETHUSDT": -0.5})
    market = market_context(make_candles(interval="1h"), make_candles(interval="4h"))
    assert market.regime is MarketRegime.UP
    result = scan_pair(client, "ETHUSDT", settings, market=market, now=FIXED_NOW)
    assert result.signal is None
    assert result.blocked is not None
    assert "counter-trend" in result.blocked


def test_full_scan_runs_with_market_header_first() -> None:
    settings = Settings(pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0)
    report = scan(FakeBinance(), settings, now=FIXED_NOW)
    assert report.market.regime is MarketRegime.UP
    assert report.signals


@pytest.mark.parametrize("regime", ["UP", "DOWN", "HOLD"])
def test_market_regime_values_are_stable(regime: str) -> None:
    assert MarketRegime(regime).value == regime
