from datetime import timedelta

from conftest import FIXED_NOW, FakeBinance
from crypto_signal_bot.config import Settings
from crypto_signal_bot.journal import SignalJournal
from crypto_signal_bot.pipeline import run_once


def test_first_run_delivers_and_records(tmp_path) -> None:
    settings = Settings(pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0)
    journal = SignalJournal(tmp_path / "signals.sqlite3")
    result = run_once(FakeBinance(), settings, journal, now=FIXED_NOW)
    assert len(result.delivered) == 1
    assert "MARKET:" in result.text
    assert journal.summary().total == 1


def test_second_run_suppresses_the_same_candle(tmp_path) -> None:
    settings = Settings(pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0)
    journal = SignalJournal(tmp_path / "signals.sqlite3")
    run_once(FakeBinance(), settings, journal, now=FIXED_NOW)
    second = run_once(FakeBinance(), settings, journal, now=FIXED_NOW + timedelta(minutes=15))
    assert second.delivered == ()
    assert len(second.suppressed) == 1
    assert journal.summary().total == 1


def test_cooldown_expires_after_the_window(tmp_path) -> None:
    settings = Settings(
        pairs=("BTCUSDT",), request_pause_seconds=0, top_volume_limit=0, signal_cooldown_minutes=60
    )
    journal = SignalJournal(tmp_path / "signals.sqlite3")
    run_once(FakeBinance(), settings, journal, now=FIXED_NOW)
    later = FIXED_NOW + timedelta(minutes=120)
    client = FakeBinance(now=later)
    result = run_once(client, settings, journal, now=later)
    # A new candle exists, so the same trend can alert again after the cooldown.
    assert len(result.delivered) == 1
