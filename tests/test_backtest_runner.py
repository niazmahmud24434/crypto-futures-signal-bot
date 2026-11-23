import pandas as pd

from conftest import FIXED_NOW, make_candles
from crypto_signal_bot.backtest_runner import RegimeTimeline, replay_pair
from crypto_signal_bot.config import Settings
from crypto_signal_bot.context import MarketRegime


def _settings() -> Settings:
    return Settings(request_pause_seconds=0, top_volume_limit=0, limit_entries=False)


def test_rising_market_replays_long_trades_only() -> None:
    entry = make_candles(count=300, slope=0.5, interval="15m")
    confirmation = make_candles(count=120, slope=1.0, interval="1h")
    result = replay_pair("BTCUSDT", entry, confirmation, _settings())
    assert result.trades
    assert all(trade.signal.side.value == "LONG" for trade in result.trades)
    assert result.stats.trades == len(result.trades)
    assert {trade.outcome.result for trade in result.trades} <= {"target", "stop", "timeout"}


def test_falling_market_replays_short_trades_only() -> None:
    entry = make_candles(count=300, start=400.0, slope=-0.5, interval="15m")
    confirmation = make_candles(count=120, start=400.0, slope=-1.0, interval="1h")
    result = replay_pair("BTCUSDT", entry, confirmation, _settings())
    assert result.trades
    assert all(trade.signal.side.value == "SHORT" for trade in result.trades)


def test_trades_are_spaced_by_the_live_cooldown() -> None:
    entry = make_candles(count=300, slope=0.5, interval="15m")
    confirmation = make_candles(count=120, slope=1.0, interval="1h")
    result = replay_pair("BTCUSDT", entry, confirmation, _settings())
    anchors = [trade.signal.candle_open_time for trade in result.trades]
    assert all(left is not None for left in anchors)
    gaps = [
        (later - earlier).total_seconds() / 60
        for earlier, later in zip(anchors, anchors[1:], strict=False)
    ]
    assert all(gap >= 180 for gap in gaps)


def test_regime_timeline_only_answers_after_warmup() -> None:
    timeline = RegimeTimeline(
        make_candles(count=200, interval="1h"), make_candles(count=200, interval="4h")
    )
    current = timeline.at(FIXED_NOW)
    assert current is not None
    assert current.regime is MarketRegime.UP
    assert timeline.at(FIXED_NOW - pd.Timedelta(days=30)) is None
    assert sum(timeline.counts().values()) == len(timeline)
