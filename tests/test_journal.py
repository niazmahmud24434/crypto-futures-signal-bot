from datetime import UTC, datetime

from crypto_signal_bot.journal import SignalJournal
from crypto_signal_bot.models import Side, Signal


def test_journal_deduplicates_same_signal(tmp_path) -> None:
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
        score=3,
        reasons=("EMA", "RSI", "1h"),
    )
    journal = SignalJournal(tmp_path / "signals.sqlite3")
    assert journal.record(signal) is True
    assert journal.record(signal) is False
