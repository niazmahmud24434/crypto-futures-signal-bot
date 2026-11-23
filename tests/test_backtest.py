from datetime import UTC, datetime

import pandas as pd

from crypto_signal_bot.backtest import evaluate_signal, summarize
from crypto_signal_bot.models import Side, Signal


def _signal() -> Signal:
    return Signal(
        pair="BTCUSDT",
        side=Side.LONG,
        timeframe="15m/1h",
        created_at=datetime.now(UTC),
        entry_low=100,
        entry_high=100,
        stop_loss=98,
        take_profit_1=104,
        take_profit_2=108,
        score=3,
        reasons=("test", "test", "test"),
    )


def test_stop_is_checked_before_target() -> None:
    future = pd.DataFrame({"high": [105], "low": [97], "close": [100]})
    outcome = evaluate_signal(_signal(), future)
    assert outcome.result == "stop"
    assert outcome.r_multiple == -1


def test_summary_includes_timeouts_and_loss_streak() -> None:
    signal = _signal()
    outcomes = [
        evaluate_signal(signal, pd.DataFrame({"high": [105], "low": [99], "close": [104]})),
        evaluate_signal(signal, pd.DataFrame({"high": [99], "low": [97], "close": [98]})),
        evaluate_signal(signal, pd.DataFrame({"high": [100], "low": [99], "close": [99]})),
    ]
    stats = summarize(outcomes)
    assert stats.trades == 3
    assert stats.wins == 1
    assert stats.losses == 1
    assert stats.timeouts == 1
