from datetime import UTC, datetime

from crypto_signal_bot.context import MarketContext, MarketRegime
from crypto_signal_bot.models import Side, Signal
from crypto_signal_bot.telegram import format_signal, to_plain


def _signal() -> Signal:
    return Signal(
        pair="BTCUSDT",
        side=Side.LONG,
        timeframe="15m entry / 1h confirmation",
        created_at=datetime.now(UTC),
        entry_low=100,
        entry_high=101,
        stop_loss=98,
        take_profit_1=104,
        take_profit_2=108,
        score=4,
        reasons=("EMA alignment", "MACD confirmation", "1h trend"),
        market_regime="UP",
    )


def test_signal_message_is_manual_only() -> None:
    message = format_signal(_signal())
    assert "BTCUSDT" in message
    assert "Manual trade only" in message
    assert "no order was placed" in message


def test_signal_starts_with_market_header_and_shows_percentages() -> None:
    market = MarketContext(MarketRegime.UP, 85, "1h/4h", ("BTC EMA alignment bullish",))
    plain = to_plain(format_signal(_signal(), market))
    assert plain.startswith("🟢 CRYPTO LONG SIGNAL")
    assert "MARKET: UP" in plain
    assert "Confidence: 85%" in plain
    assert "STOP-LOSS: 98.0000 USDT (-2.49%)" in plain
    assert "TP1: 104.0000 USDT (+3.48%)" in plain
    assert "Invalidation:" in plain
    assert "Not financial advice" in plain
