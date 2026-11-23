from datetime import UTC, datetime

import pandas as pd

from crypto_signal_bot.backtest import (
    evaluate_bracket_signal,
    evaluate_limit_signal,
    evaluate_signal,
    summarize,
)
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


def test_limit_entry_needs_the_published_zone() -> None:
    future = pd.DataFrame({"high": [103, 103], "low": [100.5, 100.5], "close": [102, 102]})
    assert evaluate_limit_signal(_signal(), future, max_wait_bars=2) is None


def test_limit_entry_fills_then_targets() -> None:
    future = pd.DataFrame({"high": [100.5, 105], "low": [99.5, 101], "close": [100, 104]})
    outcome = evaluate_limit_signal(_signal(), future)
    assert outcome is not None
    assert outcome.result == "target"
    assert outcome.entry == 100
    assert outcome.risk == 2


def test_limit_entry_same_bar_stop_is_conservative() -> None:
    future = pd.DataFrame({"high": [101], "low": [97], "close": [98]})
    outcome = evaluate_limit_signal(_signal(), future)
    assert outcome is not None
    assert outcome.result == "stop"
    assert outcome.r_multiple == -1


def test_bracket_banks_half_at_tp1_then_runs_to_tp2() -> None:
    future = pd.DataFrame({"high": [104.5, 108.5], "low": [100.5, 101], "close": [104, 108]})
    outcome = evaluate_bracket_signal(_signal(), future)
    assert outcome is not None
    assert outcome.result == "target"
    assert outcome.r_multiple == 3.0


def test_bracket_keeps_the_banked_half_when_price_returns_to_entry() -> None:
    future = pd.DataFrame({"high": [104.5, 100.2], "low": [100.5, 99.0], "close": [104, 99.5]})
    outcome = evaluate_bracket_signal(_signal(), future)
    assert outcome is not None
    assert outcome.result == "tp1_secured"
    assert outcome.r_multiple == 1.0


def test_bracket_stop_before_tp1_is_a_full_loss() -> None:
    future = pd.DataFrame({"high": [101], "low": [97], "close": [98]})
    outcome = evaluate_bracket_signal(_signal(), future)
    assert outcome is not None
    assert outcome.result == "stop"
    assert outcome.r_multiple == -1


def test_bracket_limit_entry_requires_a_zone_touch() -> None:
    future = pd.DataFrame({"high": [104, 104], "low": [103, 103], "close": [104, 104]})
    assert evaluate_bracket_signal(_signal(), future, entry_mode="limit", max_wait_bars=2) is None
