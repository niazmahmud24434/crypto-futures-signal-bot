from datetime import UTC, datetime

from crypto_signal_bot.models import Side, Signal
from crypto_signal_bot.telegram import format_signal


def test_signal_message_is_manual_only() -> None:
    signal = Signal(
        pair="BTCUSDT",
        side=Side.LONG,
        timeframe="15m/1h",
        created_at=datetime.now(UTC),
        entry_low=100,
        entry_high=101,
        stop_loss=98,
        take_profit_1=104,
        take_profit_2=108,
        score=4,
        reasons=("EMA alignment", "MACD confirmation", "1h trend"),
    )
    message = format_signal(signal)
    assert "BTCUSDT" in message
    assert "Manual trade only" in message
    assert "no order was placed" in message
