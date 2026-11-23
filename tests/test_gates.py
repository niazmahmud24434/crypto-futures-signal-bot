from crypto_signal_bot.context import (
    MarketRegime,
    pattern_bias,
    pattern_conflicts,
    pattern_label,
)

BULLISH = ("bullish_engulfing",)
BEARISH = ("bearish_engulfing",)


def test_pattern_bias_is_directional() -> None:
    assert pattern_bias(BULLISH) == 1
    assert pattern_bias(BEARISH) == -1
    assert pattern_bias(("doji",)) == 0
    assert pattern_bias(()) == 0


def test_conflict_detection_blocks_opposing_candles() -> None:
    assert pattern_conflicts(BEARISH, "LONG") is True
    assert pattern_conflicts(BULLISH, "SHORT") is True
    assert pattern_conflicts(BULLISH, "LONG") is False
    assert pattern_conflicts(("doji",), "LONG") is False


def test_pattern_label_reports_verdict() -> None:
    assert pattern_label(BULLISH, "LONG").endswith("(aligned)")
    assert pattern_label(BEARISH, "LONG").endswith("(conflicting)")
    assert "neutral" in pattern_label(("doji",), "LONG")


def test_hold_regime_needs_extra_confirmation() -> None:
    from datetime import UTC, datetime

    from crypto_signal_bot.config import Settings
    from crypto_signal_bot.context import MarketContext
    from crypto_signal_bot.models import Side, Signal
    from crypto_signal_bot.scanner import _gate

    signal = Signal(
        pair="ETHUSDT",
        side=Side.LONG,
        timeframe="15m entry / 1h confirmation",
        created_at=datetime.now(UTC),
        entry_low=100,
        entry_high=101,
        stop_loss=98,
        take_profit_1=104,
        take_profit_2=108,
        score=3,
        reasons=("EMA", "RSI", "MACD"),
    )
    hold = MarketContext(MarketRegime.HOLD, 50, "1h/4h", ("mixed",))
    settings = Settings(min_signal_score=3)
    assert _gate(signal, hold, settings) == "market HOLD needs one extra confirmation"
