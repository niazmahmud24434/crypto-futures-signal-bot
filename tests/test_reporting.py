from crypto_signal_bot.context import MarketContext, MarketRegime
from crypto_signal_bot.reporting import format_report
from crypto_signal_bot.scanner import PairScan, ScanReport
from crypto_signal_bot.telegram import to_plain


def test_empty_report_explicitly_says_hold() -> None:
    report = ScanReport(
        MarketContext(MarketRegime.HOLD, 50, "1h/4h", ("Mixed",)),
        (PairScan("BTCUSDT", None, ()),),
    )
    text = format_report(report)
    assert "MARKET: HOLD" in text
    assert "HOLD / WAIT" in text
    assert "Scanned: 1 pairs" in text


def test_report_starts_with_market_header_and_counts_filters() -> None:
    report = ScanReport(
        MarketContext(MarketRegime.UP, 80, "1h/4h", ("BTC EMA alignment bullish",)),
        (
            PairScan("ETHUSDT", None, (), blocked="counter-trend short against market UP"),
            PairScan("SOLUSDT", None, (), error="SOLUSDT 15m: last closed candle is stale"),
        ),
    )
    plain = to_plain(format_report(report))
    assert plain.startswith("MARKET: UP")
    assert "filtered: 1" in plain
    assert "data errors: 1" in plain
    assert "counter-trend" in plain
