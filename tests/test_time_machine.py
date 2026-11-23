from conftest import FIXED_NOW, FakeBinance
from crypto_signal_bot.config import Settings
from crypto_signal_bot.time_machine import (
    format_time_machine_markdown,
    format_time_machine_message,
    run_time_machine,
)


def _settings() -> Settings:
    return Settings(
        request_pause_seconds=0,
        top_volume_limit=0,
        time_machine_days=3,
        pairs=("BTCUSDT",),
        signal_cooldown_minutes=60,
        limit_entries=False,
    )


def test_time_machine_replays_and_charges_costs() -> None:
    report = run_time_machine(FakeBinance(), _settings(), days=3, now=FIXED_NOW)
    assert report.results
    assert report.trades
    assert report.gross_stats.trades == len(report.trades)
    assert report.net_stats.average_r < report.gross_stats.average_r
    assert report.candidates >= report.gross_stats.trades


def test_time_machine_markdown_states_limits() -> None:
    report = run_time_machine(FakeBinance(), _settings(), days=3, now=FIXED_NOW)
    markdown = format_time_machine_markdown(report)
    assert "# Crypto Time Machine" in markdown
    assert "not a forecast" in markdown
    assert "funding payments are not included" in markdown
    assert "Net average R" in markdown


def test_compact_message_is_telegram_safe() -> None:
    report = run_time_machine(FakeBinance(), _settings(), days=3, now=FIXED_NOW)
    message = format_time_machine_message(report)
    assert "CRYPTO TIME MACHINE" in message
    assert "Not financial advice" in message
