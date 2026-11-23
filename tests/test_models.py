from datetime import UTC, datetime

from crypto_signal_bot.models import Side, Signal


def _signal(side: Side) -> Signal:
    return Signal(
        pair="BTCUSDT",
        side=side,
        timeframe="15m entry / 1h confirmation",
        created_at=datetime.now(UTC),
        entry_low=100,
        entry_high=100,
        stop_loss=98 if side is Side.LONG else 102,
        take_profit_1=103 if side is Side.LONG else 97,
        take_profit_2=106 if side is Side.LONG else 94,
        score=4,
        reasons=("test",),
    )


def test_long_percentages_are_signed_from_entry() -> None:
    signal = _signal(Side.LONG)
    assert signal.stop_percent == -2.0
    assert signal.take_profit_1_percent == 3.0
    assert signal.risk_reward_tp1 == 1.5
    assert signal.risk_reward_tp2 == 3.0


def test_short_percentages_invert_price_direction() -> None:
    signal = _signal(Side.SHORT)
    assert signal.stop_percent == -2.0
    assert signal.take_profit_1_percent == 3.0
    assert signal.risk_reward_tp1 == 1.5
